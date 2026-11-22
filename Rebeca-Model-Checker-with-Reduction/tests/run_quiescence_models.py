#!/usr/bin/env python3
"""Native AST/JSON regressions: future messages, runtime resend and first errors."""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
CASES=[('LoadBalancerSmall', ROOT.parent/'ARIA/benchmarks/LoadBalancerSmall.rebeca','satisfied','used'),
       ('QuiescenceResend', ROOT/'tests/fixtures/QuiescenceResend.rebeca','satisfied','resend'),
       ('QuiescenceFuturePending', ROOT/'tests/fixtures/QuiescenceFuturePending.rebeca','satisfied','pending'),
       ('QuiescenceTerminates', ROOT/'tests/fixtures/QuiescenceTerminates.rebeca','deadlock','used'),
       ('QuiescenceAssertion', ROOT/'tests/fixtures/QuiescenceAssertion.rebeca','assertion failed','disabled')]


def command(args,cwd,log):
    with log.open('w') as out:
        subprocess.run([str(a) for a in args],cwd=cwd,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=180)


def check_result(name,mode,certificate,expected,directory):
    report=ET.parse(directory/'report.xml').getroot()
    result=report.findtext('checked-property/result')
    trace=report.findall('counter-example-trace/state')
    if result!=expected:raise ValueError(f'{name}/{mode}: expected {expected}, got {result}')
    if expected!='satisfied' and not trace:raise ValueError(f'{name}/{mode}: missing first-error trace')
    log=(directory/'errors.log').read_text()
    skips=[line for line in log.splitlines() if line.startswith('POR_QUIESCENT_SKIP')]
    if mode!='baseline':
        generated=(directory/'TimedModelChecker.cpp').read_text()
        match=re.search(r'static const bool neverSent\[.*?=\s*(\{.*?\});',generated,re.S)
        if not match:raise ValueError('Missing generated certificate table')
        table=json.loads(match.group(1).replace('{','[').replace('}',']'))
        # These fixtures retain the reviewed six-instance main order.
        if table[5][1] != (certificate in ('used','pending')):
            raise ValueError(f'{name}/{mode}: unexpected Bootstrapper static certificate')
        bootstrap_skips=[line for line in skips if 'blocker=Bootstrapper ' in line]
        if certificate=='used' and not bootstrap_skips:raise ValueError(f'{name}/{mode}: positive certificate never used')
        if certificate in ('resend','pending') and bootstrap_skips:raise ValueError(f'{name}/{mode}: unsafe Bootstrapper skip')
        if certificate=='pending' and not any('blocker=Bootstrapper ' in line for line in log.splitlines() if line.startswith('POR_BLOCK')):
            raise ValueError(f'{name}/{mode}: pending-message dependency was not exercised')
        if certificate=='disabled' and skips:raise ValueError(f'{name}/{mode}: unknown-call fallback did not disable certificate')
    return {'result':result,'states':int(report.findtext('system-info/reached-states')),
                   'transitions':int(report.findtext('system-info/reached-transitions')),
                   'trace_states':len(trace),'quiescent_skips':len(skips)}


def run_case(name,model,expected,certificate,output):
    destination=output/name;destination.mkdir(parents=True,exist_ok=True)
    command(['java','-jar',ROOT.parent/'ARIA/target/erdg-tool-0.1.0.jar','file',model],ROOT.parent/'ARIA',destination/'aria.log')
    dependency=ROOT.parent/'ARIA/output'/(name+'_pruned')/(name+'_conditional.json')
    if not dependency.exists():raise ValueError(f'No fresh dependency file: {dependency}')
    results={}
    for mode in ('baseline','aria_ast','aria_json'):
        directory=destination/mode;directory.mkdir(exist_ok=True)
        for old in directory.iterdir():
            if old.suffix in ('.cpp','.h'):old.unlink()
        args=['java','-jar',ROOT/'target/rmc-2.14.jar','-s',model,'-e','TIMED_REBECA','-v','2.3','-o',directory]
        if mode!='baseline':args+=['--aria']
        if mode=='aria_json':args+=['--aria-json',dependency]
        command(args,ROOT,directory/'generate.log')
        sources=sorted(directory.glob('*.cpp'))
        if not sources:raise ValueError(f'Generator produced no C++: {directory}')
        command(['g++','-std=c++11','-pthread','-O2','-DPOR_DIAGNOSTICS',*[p.name for p in sources],'-o','execute'],directory,directory/'compile.log')
        with (directory/'report.xml').open('w') as out,(directory/'errors.log').open('w') as err:
            subprocess.run(['./execute'],cwd=directory,stdout=out,stderr=err,check=True,timeout=60)
        results[mode]=check_result(name,mode,certificate,expected,directory)
        print(name,mode,results[mode],flush=True)
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'tmp/QuiescenceModels')
    p.add_argument('--models',nargs='*')
    args=p.parse_args()
    if args.models and set(args.models)-{case[0] for case in CASES}:p.error('Unknown model selection')
    args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=True)
    os.environ['ARIA_PRUNE']='1';os.environ['ARIA_EXPORT']='1'
    results={}
    try:
        for name,model,expected,certificate in CASES:
            if args.models and name not in args.models:continue
            results[name]=run_case(name,model,expected,certificate,args.output)
            (args.output/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
    except Exception:
        print(f'FAILED; inspect fresh logs under {args.output}',flush=True)
        raise
    print('PASS: all requested native outcomes, first-error traces and certificate boundaries agree')
