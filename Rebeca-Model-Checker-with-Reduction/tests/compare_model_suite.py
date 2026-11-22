#!/usr/bin/env python3
"""Three-path native measurements; first errors remain terminal, not full graphs."""
import argparse,csv,hashlib,json,os,platform,re,signal,statistics,subprocess,threading,time
from pathlib import Path
import xml.etree.ElementTree as ET
from run_quiescence_models import ROOT,CASES,command

MODELS=[(n,p,e) for n,p,e,_ in CASES]+[('PassiveSendIndependent',ROOT/'tests/fixtures/PassiveSendIndependent.rebeca','deadlock')]

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def body(text):
    text=re.sub(r'^\s*@priority\(\d+\)\s*$','',text,flags=re.M)
    return [line.rstrip() for line in text.splitlines() if line.strip()]

def sample(directory,index,timeout):
    report=directory/f'report-{index}.xml';err=directory/f'errors-{index}.log'
    started=time.perf_counter()
    with report.open('w') as out,err.open('w') as errors:
        process=subprocess.Popen(['./execute'],cwd=directory,stdout=out,stderr=errors,start_new_session=True)
        waited=[]
        def reap():waited.append(os.wait4(process.pid,0))
        waiter=threading.Thread(target=reap);waiter.start();waiter.join(timeout)
        if waiter.is_alive():
            os.killpg(process.pid,signal.SIGKILL);waiter.join()
            process.returncode=os.waitstatus_to_exitcode(waited[0][1])
            raise subprocess.TimeoutExpired(['./execute'],timeout)
        _,status,usage=waited[0];process.returncode=os.waitstatus_to_exitcode(status)
        if process.returncode:raise subprocess.CalledProcessError(process.returncode,['./execute'])
    wall=time.perf_counter()-started
    r=ET.parse(report).getroot()
    peak=usage.ru_maxrss/(1024 if platform.system()=='Darwin' else 1)
    return {'result':r.findtext('checked-property/result'),'property_type':r.findtext('checked-property/type'),
            'property_name':r.findtext('checked-property/name'),
            'states':int(r.findtext('system-info/reached-states')),
            'transitions':int(r.findtext('system-info/reached-transitions')),
            'trace_states':len(r.findall('counter-example-trace/state')),
            'solver_reported_seconds':int(r.findtext('system-info/total-spent-time')),
            'solver_estimated_bytes':int(r.findtext('system-info/consumed-mem')),
            'native_wall_seconds':wall,'peak_rss_kib':peak}

def run_case(name,model,expected,out,repeats,timeout):
    case=out/name;case.mkdir(parents=True)
    forjar=ROOT.parent/'ARIA/target/erdg-tool-0.1.0.jar'
    export_dir=ROOT.parent/'ARIA/output'/(name+'_pruned')
    for stale in (export_dir/(name+'_annotated.rebeca'),export_dir/(name+'_conditional.json')):
        stale.unlink(missing_ok=True)
    started=time.perf_counter()
    command(['java','-jar',forjar,'file',model],ROOT.parent/'ARIA',case/'aria.log')
    aria_seconds=time.perf_counter()-started
    annotated=ROOT.parent/'ARIA/output'/(name+'_pruned')/(name+'_annotated.rebeca')
    if not annotated.exists() or body(annotated.read_text())!=body(model.read_text()):
        raise ValueError('Static export missing or changed model bodies')
    (case/'original.rebeca').write_bytes(model.read_bytes())
    (case/'annotated.rebeca').write_bytes(annotated.read_bytes())
    rows=[]
    for mode in ('full','static','dynamic'):
        d=case/mode;d.mkdir()
        source=annotated if mode=='static' else model
        args=['java','-jar',ROOT/'target/rmc-2.14.jar','-s',source,'-e','TIMED_REBECA','-v','2.3','-o',d]
        if mode=='dynamic':args+=['--aria']
        started=time.perf_counter();command(args,ROOT,d/'generate.log');generation=time.perf_counter()-started
        cpp=sorted(d.glob('*.cpp'))
        if not cpp:raise ValueError('No generated native sources')
        config=(d/'Config.h').read_text()
        por=bool(re.search(r'^\s*#\s*define\s+PO\b',config,re.M))
        if por!=(mode=='dynamic') or re.search(r'^\s*#\s*define\s+TTS\b',config,re.M):
            raise ValueError('Unexpected engine/POR configuration')
        started=time.perf_counter()
        command(['g++','-std=c++11','-pthread','-O2',*[p.name for p in cpp],'-o','execute'],d,d/'compile.log')
        compile_seconds=time.perf_counter()-started
        samples=[sample(d,k,timeout) for k in range(repeats)]
        identities={(s['result'],s['states'],s['transitions']) for s in samples}
        if len(identities)!=1:raise ValueError('Repeated native outcomes/counts are unstable')
        first=samples[0]
        valid=first['result']==expected and (expected=='satisfied' or all(s['trace_states']>0 for s in samples))
        row={'model':name,'mode':mode,'expected_result':expected,'outcome_check':valid,
             'source_sha256':digest(source),'result':first['result'],'property_type':first['property_type'],
             'property_name':first['property_name'],'states':first['states'],'transitions':first['transitions'],
             'complete_space':first['result']=='satisfied','trace_states':first['trace_states'],
             'native_wall_median_seconds':statistics.median(s['native_wall_seconds'] for s in samples),
             'native_wall_min_seconds':min(s['native_wall_seconds'] for s in samples),
             'native_wall_max_seconds':max(s['native_wall_seconds'] for s in samples),
             'peak_rss_median_kib':statistics.median(s['peak_rss_kib'] for s in samples),
             'solver_estimated_bytes':first['solver_estimated_bytes'],'generation_seconds':generation,
             'compile_seconds':compile_seconds,'aria_export_seconds':aria_seconds,'samples':samples}
        rows.append(row)
        (case/(mode+'.json')).write_text(json.dumps(row,indent=2)+'\n')
        print(name,mode,first['result'],first['states'],first['transitions'],'outcome_check',valid,flush=True)
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'tmp/ThreePathSuite')
    p.add_argument('--models',nargs='+',choices=[n for n,_,_ in MODELS])
    p.add_argument('--repeats',type=int,default=3);p.add_argument('--timeout',type=int,default=60)
    a=p.parse_args()
    if a.repeats<1:p.error('repeats must be positive')
    out=a.output.resolve()
    if out.exists():p.error('Output already exists; choose a fresh --output to avoid stale results')
    out.mkdir(parents=True)
    os.environ['ARIA_PRUNE']='1';os.environ['ARIA_EXPORT']='1'
    meta={'implementation_baseline':json.loads((ROOT/'tests/ARIA_BASELINE.json').read_text()),
          'rss_method':'per-native-child os.wait4 ru_maxrss, normalized to KiB',
          'platform':platform.platform(),'machine':platform.machine(),'repeats':a.repeats,
          'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
          'java':subprocess.run(['java','-version'],capture_output=True,text=True,check=True).stderr.strip(),
          'rmc_jar_sha256':digest(ROOT/'target/rmc-2.14.jar'),
          'aria_jar_sha256':digest(ROOT.parent/'ARIA/target/erdg-tool-0.1.0.jar'),
          'native_flags':['-std=c++11','-pthread','-O2'],'diagnostics':False,'graph_export':False,
          'scope':'Outcome and performance comparison, not semantic POR proof','rows':[]}
    def save():
        (out/'summary.json').write_text(json.dumps(meta,indent=2)+'\n')
        rows=meta['rows']
        if rows:
            keys=[k for k in rows[0] if k!='samples']
            with (out/'summary.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:r[k] for k in keys} for r in rows)
        lines=['# Three-path model measurements','','Counts on error runs describe exploration before the first error, not full spaces.',
               'Wall time includes native startup; peak RSS is process memory, solver bytes are an internal estimate.',
               'Tiny models and three repetitions do not support a general performance ranking.','',
               '| Model | Mode | Result | States | Transitions | Complete | Wall median (s) | Peak RSS median (KiB) |',
               '|---|---|---|---:|---:|---|---:|---:|']
        for r in rows:lines.append(f"| {r['model']} | {r['mode']} | {r['result']} | {r['states']} | {r['transitions']} | {r['complete_space']} | {r['native_wall_median_seconds']:.4f} | {r['peak_rss_median_kib']:.0f} |")
        (out/'summary.md').write_text('\n'.join(lines)+'\n')
    save()
    try:
        for n,m,e in MODELS:
            if a.models and n not in a.models:continue
            meta['rows']+=run_case(n,m,e,out,a.repeats,a.timeout);save()
    except Exception as error:
        meta['execution_failure']=str(error);save();raise
    meta['all_outcome_checks_passed']=all(r['outcome_check'] for r in meta['rows']);save()
    if not meta['all_outcome_checks_passed']:raise SystemExit('FAIL: outcome mismatch or missing error trace; inspect summary')
    print('PASS: all expected outcomes and terminal-error traces; no general POR proof',out,flush=True)

if __name__=='__main__':main()
