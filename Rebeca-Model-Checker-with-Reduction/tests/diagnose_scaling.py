#!/usr/bin/env python3
"""Separate native diagnostics/legacy control; never use diagnostic wall time as benchmark."""
import argparse,collections,json,re,shutil
from pathlib import Path
from run_cycle_barriers import ROOT,compile_run

def summarize(directory):
    events=collections.Counter();proofs=collections.Counter();actors=collections.Counter();outcomes=collections.Counter();blocks=collections.Counter()
    full_candidates=0;states=set();witnesses=collections.Counter();alternatives=collections.Counter();trial_actions=collections.Counter()
    for line in (directory/'errors.log').open():
        if not line.startswith('POR_'):continue
        kind=line.split()[0];events[kind]+=1
        f=dict(x.split('=',1) for x in line.split()[1:] if '=' in x)
        if kind=='POR_STATE':states.add(f['state'])
        if kind=='POR_PROVISO_WITNESS':witnesses[f.get('reason','unknown')]+=1
        if kind=='POR_REPRESENTATIVE':alternatives[f.get('alternatives','unknown')]+=1
        if kind=='POR_ALTERNATIVE' and f.get('phase')=='trial':trial_actions[f.get('actor','?')+'.'+f.get('action','?')]+=1
        if kind=='POR_BLOCK':blocks[f.get('actor','?')+' <- '+f.get('blocker','?')]+=1
        if kind=='POR_TRIAL' and f.get('accepted')=='1':
            proofs[f.get('proof','unknown')]+=1;actors[f.get('actor','unknown')]+=1
            if f.get('exhaustive')=='1':full_candidates+=1;outcomes['full_candidate']+=1
            else:outcomes['reduced']+=1
        if kind=='POR_FULL':outcomes['full_fallback']+=1
    if sum(outcomes.values())!=len(states):raise ValueError('Incomplete/duplicated decision trace')
    return {'closed_successor_witnesses':dict(witnesses),'candidate_alternative_counts':dict(alternatives),'trial_actions':dict(trial_actions),'por_logged_states':len(states),'outcomes':dict(outcomes),'accepted_proofs':dict(proofs),
            'accepted_actors':dict(actors),'event_counts':dict(events),'blocker_counts':dict(blocks)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True,help='Generated dynamic source directory from scaling benchmark')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--controls',nargs='+',choices=['current','legacy_proviso','no_closed_barriers','normalized_full'],default=['current','legacy_proviso','no_closed_barriers','normalized_full'])
    a=p.parse_args();out=a.output.resolve()
    if out.exists():p.error('Choose fresh output directory')
    out.mkdir(parents=True);result={'diagnostic_only':True,'timings_not_benchmarked':True,'controls':{}}
    for name in a.controls:
        extra=['-DPOR_LEGACY_PROVISO'] if name=='legacy_proviso' else []
        dst=out/name;dst.mkdir()
        for f in a.source.resolve().iterdir():
            if f.suffix in ('.cpp','.h'):shutil.copyfile(f,dst/f.name)
        if not (dst/'TimedModelChecker.cpp').exists():raise ValueError('Missing generated checker')
        if name=='normalized_full':
            path=dst/'Config.h';text,count=re.subn(r'^\s*#\s*define\s+PO\s*$', '// diagnostic normalized full',path.read_text(),flags=re.M)
            if count!=1:raise ValueError('Expected one PO definition')
            path.write_text(text)
        if name=='no_closed_barriers':
            path=dst/'TimedModelChecker.cpp';text,count=re.subn(r'return true && _porResultState->porFullExpanded;', 'return false; // diagnostic closed-barrier ablation only',path.read_text())
            if count!=1:raise ValueError('Expected one enabled closed-barrier return')
            path.write_text(text)
        report=compile_run(dst,['-DPOR_DIAGNOSTICS',*extra])
        if report['result']!='satisfied':raise ValueError(('Healthy instance failed',report))
        counts=summarize(dst)
        if name!='normalized_full' and counts['por_logged_states']!=report['states']:raise ValueError('Report/diagnostic state mismatch')
        result['controls'][name]={**report,**counts}
        (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
        print(name,result['controls'][name],flush=True)
    print('PASS: completed diagnostic traces and satisfied native controls; not a new semantic proof')

if __name__=='__main__':main()
