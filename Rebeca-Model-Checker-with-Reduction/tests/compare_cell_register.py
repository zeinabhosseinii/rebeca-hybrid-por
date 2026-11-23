#!/usr/bin/env python3
"""Existing case1 shared-register benchmark: explicit safety property and bad client."""
import argparse,csv,hashlib,json,os,platform,random,re,statistics,subprocess,time
from pathlib import Path
import xml.etree.ElementTree as ET
from run_quiescence_models import ROOT,command
from benchmark_scaling import MODES,copy_without_por
from compare_model_suite import body,digest,sample

ORIGINAL_SHA='e2cdaa2e62324289071e398cf251a54c7f34d2065379f23b58c4033a12dc34f7'
def models():
 original=ROOT.parent/'ARIA/benchmarks/case1.rebeca'
 if digest(original)!=ORIGINAL_SHA:raise ValueError('Existing benchmark changed; review adaptation first')
 text=original.read_text();before='value = newValue;'
 if text.count(before)!=1:raise ValueError('Unexpected Store shape')
 healthy=text.replace(before,before+'\n\t\tassertion(value >= 0 && value <= 2);')
 if healthy.count('worker2(cell):(2)')!=1:raise ValueError('Unexpected second client binding')
 return [('CellRegisterBounds',healthy,'satisfied'),('CellRegisterInvalidClient',healthy.replace('worker2(cell):(2)','worker2(cell):(3)'),'assertion failed')]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--repeats',type=int,default=10);p.add_argument('--timeout',type=float,default=30);a=p.parse_args()
 if a.repeats<1 or a.timeout<=0:p.error('Invalid repetitions/timeout')
 out=a.output.resolve()
 if out.exists():p.error('Choose fresh output')
 out.mkdir(parents=True);classes=out/'classes';classes.mkdir();jar=ROOT/'target/rmc-2.14.jar'
 subprocess.run(['javac','-cp',str(jar),'-d',str(classes),*[str(ROOT/'tests'/f) for f in ('AssertionObservationAudit.java','CounterInvariantAudit.java','ApplicationCertificateProbe.java')]],check=True)
 os.environ['ARIA_PRUNE']='1';os.environ['ARIA_EXPORT']='1';rng=random.Random(1729)
 result={'original_benchmark':'ARIA/benchmarks/case1.rebeca','original_sha256':ORIGINAL_SHA,'platform':platform.platform(),
         'rmc_jar_sha256':digest(jar),'aria_jar_sha256':digest(ROOT.parent/'ARIA/target/erdg-tool-0.1.0.jar'),
         'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
         'repeats':a.repeats,'warmups':1,'seed':1729,'diagnostics':False,'graph_export':False,'cases':{}}
 def save():
  (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
  rows=[]
  for name,c in result['cases'].items():
   for mode,d in c['modes'].items():
    ss=[x for x in d.get('samples',[]) if x.get('status')=='completed']
    if not ss:continue
    rows.append({'case':name,'mode':mode,'status':d.get('status'),'result':ss[0]['result'],'states':ss[0]['states'],'transitions':ss[0]['transitions'],
                 'trace_states':ss[0]['trace_states'],'complete_space':ss[0]['result']=='satisfied','measured_samples':len(ss),
                 'median_seconds':statistics.median(x['native_wall_seconds'] for x in ss),
                 'min_seconds':min(x['native_wall_seconds'] for x in ss),'max_seconds':max(x['native_wall_seconds'] for x in ss),
                 'peak_rss_median_kib':statistics.median(x['peak_rss_kib'] for x in ss)})
  if rows:
   with (out/'summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 save()
 try:
  for name,text,expected in models():
   case=out/name;case.mkdir();model=case/(name+'.rebeca');model.write_text(text)
   proof=case/'certificate.json'
   command(['java','-cp',str(jar)+os.pathsep+str(classes),'ApplicationCertificateProbe',model,proof],ROOT,case/'certificate.log')
   certificate=json.loads(proof.read_text())
   if certificate['production_invariant_certificate'] or certificate['structural_barrier_gate']:raise ValueError('Unsupported byte/parameter fragment unexpectedly certified')
   export=ROOT.parent/'ARIA/output'/(name+'_pruned');annotated=export/(name+'_annotated.rebeca');annotated.unlink(missing_ok=True)
   start=time.perf_counter();command(['java','-jar',ROOT.parent/'ARIA/target/erdg-tool-0.1.0.jar','file',model],ROOT.parent/'ARIA',case/'aria.log');aria_seconds=time.perf_counter()-start
   if not annotated.exists() or body(annotated.read_text())!=body(text):raise ValueError('Static export changed assertion/model body')
   (case/'annotated.rebeca').write_bytes(annotated.read_bytes())
   c={'source_sha256':digest(model),'expected':expected,'certificate':certificate,'aria_export_seconds':aria_seconds,'orders':[], 'modes':{}}
   result['cases'][name]=c;save()
   for mode in MODES:
    d=case/mode;d.mkdir();start=time.perf_counter()
    if mode=='dynamic_no_por':copy_without_por(case/'dynamic',d)
    else:
     args=['java','-jar',jar,'-s',annotated if mode=='static' else model,'-e','TIMED_REBECA','-v','2.3','-o',d]
     if mode=='dynamic':args+=['--aria']
     command(args,ROOT,d/'generate.log')
    generation=time.perf_counter()-start
    sources=sorted(d.glob('*.cpp'))
    if not sources:raise ValueError('Missing generated code')
    config=(d/'Config.h').read_text()
    if bool(re.search(r'^\s*#\s*define\s+PO\b',config,re.M))!=(mode=='dynamic') or re.search(r'^\s*#\s*define\s+TTS\b',config,re.M):raise ValueError('Unexpected FTTS/POR mode')
    gate=re.search(r'return (true|false) && _porResultState->porFullExpanded;',(d/'TimedModelChecker.cpp').read_text())
    if mode in ('dynamic','dynamic_no_por') and (not gate or gate[1]!='false'):raise ValueError('Unproved gate unexpectedly enabled')
    start=time.perf_counter();command(['g++','-std=c++11','-pthread','-O2',*[p.name for p in sources],'-o','execute'],d,d/'compile.log')
    c['modes'][mode]={'generated_barrier_gate':False if gate else None,'generation_or_copy_seconds':generation,'compile_seconds':time.perf_counter()-start,'status':'ready','samples':[]};save()
   order=list(MODES);rng.shuffle(order)
   for round_index in range(-1,a.repeats):
    shift=(round_index+1)%len(MODES);rotated=order[shift:]+order[:shift];c['orders'].append({'round':round_index,'modes':rotated})
    for mode in rotated:
     d=c['modes'][mode]
     if d['status']=='timeout':continue
     try:measurement=sample(case/mode,round_index+1,a.timeout)
     except subprocess.TimeoutExpired:d['status']='timeout';d['samples'].append({'status':'timeout','round':round_index});save();continue
     measurement.update(status='completed',round=round_index)
     if measurement['result']=='assertion failed':
      xml=ET.parse(case/mode/f'report-{round_index+1}.xml').getroot()
      failures=[e.find('messageserver') for e in xml.findall('counter-example-trace/transition') if e.get('destination')=='assertion failed']
      measurement['store_fault_edge']=any(e is not None and e.get('owner')=='cell' and e.get('title')=='STORE' for e in failures)
     if round_index<0:d['warmup']=measurement
     else:d['samples'].append(measurement)
     save()
   for mode,d in c['modes'].items():
    if d['status']=='timeout':continue
    all_runs=[d['warmup'],*d['samples']]
    d['stable_counts']=len({(x['result'],x['states'],x['transitions']) for x in all_runs})==1
    d['expected_outcome']=all(x['result']==expected and (expected=='satisfied' or x['trace_states']>0 and x.get('store_fault_edge')) for x in all_runs)
    d['status']='completed' if len(d['samples'])==a.repeats and d['stable_counts'] else 'unstable'
    print(name,mode,d['samples'][0]['result'],d['samples'][0]['states'],d['samples'][0]['transitions'],'expected=',d['expected_outcome'],flush=True)
   save()
  result['all_expected_outcomes']=all(d['status']=='completed' and d['expected_outcome'] for c in result['cases'].values() for d in c['modes'].values());save()
 except Exception as error:result['execution_failure']=str(error);save();raise
 if not result['all_expected_outcomes']:raise SystemExit('Outcome mismatch/timeout recorded; not a successful correctness comparison')
 print('PASS: existing shared-register source, property and injected client fault; not general POR proof',out)

if __name__=='__main__':main()
