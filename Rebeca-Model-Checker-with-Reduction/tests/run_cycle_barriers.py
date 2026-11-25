#!/usr/bin/env python3
"""Native legacy/new proviso controls, full-graph audits and pending-error regression."""
from pathlib import Path
import json,os,re,shutil,subprocess
import xml.etree.ElementTree as ET
from run_quiescence_models import ROOT,command
from audit_online_por import run as semantic_audit

OUT=ROOT/'tmp/CycleBarriers'

def check_result(result, reference_counts):
    """Counts describe one host's traversal, not a correctness certificate."""
    if result['result'] != 'satisfied':
        raise ValueError(('Expected satisfied; semantic audit cannot certify an incomplete run', result))
    measured=(result['states'],result['transitions'])
    return {**result, 'reference_counts':list(reference_counts),
            'matches_reference_counts':measured == tuple(reference_counts),
            'semantic_audit':'pending'}

def checkpoint(results):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'summary.json').write_text(json.dumps(results,indent=2)+'\n')

def compile_run(directory,flags=(),suffix=''):
    executable='execute'+suffix
    command(['g++','-std=c++11','-pthread','-O2',*flags,*[f.name for f in sorted(directory.glob('*.cpp'))],'-o',executable],directory,directory/('compile'+suffix+'.log'))
    with (directory/('report'+suffix+'.xml')).open('w') as out,(directory/('errors'+suffix+'.log')).open('w') as err:
        subprocess.run(['./'+executable],cwd=directory,stdout=out,stderr=err,check=True,timeout=60)
    report=ET.parse(directory/('report'+suffix+'.xml')).getroot()
    return {'result':report.findtext('checked-property/result'),
            'states':int(report.findtext('system-info/reached-states')),
            'transitions':int(report.findtext('system-info/reached-transitions'))}

def generate(model,name,mode,directory):
    directory.mkdir(parents=True,exist_ok=True)
    for old in directory.iterdir():
        if old.suffix in ('.cpp','.h'):old.unlink()
    args=['java','-jar',ROOT/'target/rmc-2.14.jar','-s',model,'-e','TIMED_REBECA','-v','2.3','-o',directory]
    if mode!='baseline':args+=['--aria']
    if mode=='aria_json':args+=['--aria-json',ROOT.parent/'ARIA/output'/(name+'_pruned')/(name+'_conditional.json')]
    command(args,ROOT,directory/'generate.log')
    if not list(directory.glob('*.cpp')):raise ValueError('Generator failed; inspect '+str(directory/'generate.log'))

def export_json(model,name):
    OUT.mkdir(parents=True,exist_ok=True)
    command(['java','-jar',ROOT.parent/'ARIA/target/erdg-tool-0.1.0.jar','file',model],ROOT.parent/'ARIA',OUT/(name+'-aria.log'))

def prepare_full_control(online,full):
    full.mkdir(exist_ok=True)
    for f in online.iterdir():
        if f.suffix in ('.cpp','.h'):shutil.copyfile(f,full/f.name)
    p=full/'Config.h';text,count=re.subn(r'^\s*#\s*define\s+PO\s*$','// full normalized reference',p.read_text(),flags=re.M)
    if count!=1:raise ValueError('Expected one PO macro')
    p.write_text(text)


if __name__=='__main__':
    os.environ['ARIA_PRUNE']='1';os.environ['ARIA_EXPORT']='1'
    results={}
    cases=[('LoadBalancerSmall',ROOT.parent/'ARIA/benchmarks/LoadBalancerSmall.rebeca',(19,20),(27,32)),
           ('QuiescenceResend',ROOT/'tests/fixtures/QuiescenceResend.rebeca',(117,139),(338,720))]
    for name,model,new_counts,legacy_counts in cases:
        export_json(model,name);base=OUT/name;results[name]={}
        for mode in ('aria_ast','aria_json'):
            d=base/mode;generate(model,name,mode,d)
            result=compile_run(d,['-DPOR_DIAGNOSTICS','-DEXPORT_STATE_SPACE'])
            results[name][mode]=check_result(result,new_counts)
            checkpoint(results)
            if not results[name][mode]['matches_reference_counts']:
                print(f'{name} {mode}: counts differ from reference; running full semantic audit',flush=True)
        full=base/'full'
        prepare_full_control(base/'aria_ast',full)
        results[name]['full']=compile_run(full,['-DEXPORT_STATE_SPACE'])
        for mode in ('aria_ast','aria_json'):
            semantic_audit(full,base/mode,model,base/('semantic-'+mode+'.json'))
            results[name][mode]['semantic_audit']='passed'
            checkpoint(results)
        legacy=compile_run(base/'aria_ast',['-DPOR_LEGACY_PROVISO'],'-legacy')
        results[name]['legacy']=check_result(legacy,legacy_counts)
        results[name]['legacy']['semantic_audit']='not_run_performance_control'
        checkpoint(results)
    # Two independent looping actors can otherwise close a genuinely partial cycle.
    name='PartialLoop';model=ROOT/'tests/fixtures'/ (name+'.rebeca')
    base=OUT/name;online=base/'aria_ast';full=base/'full'
    generate(model,name,'aria_ast',online)
    prepare_full_control(online,full)
    results[name]={'aria_ast':compile_run(online,['-DPOR_DIAGNOSTICS','-DEXPORT_STATE_SPACE']),
                   'full':compile_run(full,['-DEXPORT_STATE_SPACE'])}
    cycle=semantic_audit(full,online,model,base/'semantic-aria_ast.json')
    if not cycle['verified_proviso_rejections'] or not cycle['outcomes'].get('full'):
        raise ValueError('No partial cycle rejection and full fallback')
    results[name]['aria_ast']['semantic_audit']='passed'
    checkpoint(results)
    # A loop is partial while a different actor can expose an assertion error.
    name='CyclePendingAssertion';model=ROOT/'tests/fixtures'/ (name+'.rebeca');export_json(model,name)
    results[name]={}
    for mode in ('baseline','aria_ast','aria_json'):
        d=OUT/name/mode;generate(model,name,mode,d);result=compile_run(d,['-DPOR_DIAGNOSTICS'])
        report=ET.parse(d/'report.xml').getroot()
        if result['result']!='assertion failed' or not report.findall('counter-example-trace/state'):
            raise ValueError('Pending error was hidden')
        if mode!='baseline' and 'POR_PROVISO_REJECT' not in (d/'errors.log').read_text():raise ValueError('Partial loop rejection not exercised')
        results[name][mode]=result
    checkpoint(results)
    print('PASS: new/legacy native controls, all selected-core cycle checks, and pending assertion detected')
