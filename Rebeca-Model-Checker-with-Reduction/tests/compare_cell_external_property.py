#!/usr/bin/env python3
"""Regress the static/global-property false negative and conservative property-aware export."""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
from run_quiescence_models import ROOT,command
from compare_model_suite import body,digest,sample
from benchmark_scaling import copy_without_por

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
 if out.exists():p.error('Choose a fresh output directory')
 out.mkdir(parents=True);model=ROOT/'tests/fixtures/CellRegisterObserved.rebeca';prop=model.with_suffix('.property');aria=ROOT.parent/'ARIA';jar=ROOT/'target/rmc-2.14.jar';env=dict(os.environ,ARIA_PRUNE='1',ARIA_EXPORT='1')
 base=(ROOT/'tests/fixtures/CellRegisterBounds.rebeca').read_text();expected=base.replace('byte id;','byte id; boolean sent;').replace('id = workerId;','id = workerId; sent = false;').replace('cell.store(id);','cell.store(id);\n\t\tsent = true;')
 if model.read_text()!=expected:raise ValueError('Unexpected observer instrumentation')
 result={'source_sha256':digest(model),'property_sha256':digest(prop),'rmc_jar_sha256':digest(jar),'aria_jar_sha256':digest(aria/'target/erdg-tool-0.1.0.jar'),'modes':{},'scope':'Exact finite external state-assertion regression, not performance or general POR proof.'}
 for label,extra in [('legacy_static',[]),('property_aware_static',['--property',str(prop)])]:
  target=aria/'output/CellRegisterObserved_pruned/CellRegisterObserved_annotated.rebeca';target.unlink(missing_ok=True)
  with (out/(label+'-aria.log')).open('w') as log:subprocess.run(['java','-jar',str(aria/'target/erdg-tool-0.1.0.jar'),'file',str(model),*extra],cwd=aria,env=env,stdout=log,stderr=log,check=True,timeout=60)
  annotated=out/(label+'.rebeca');shutil.copyfile(target,annotated)
  if body(annotated.read_text())!=body(model.read_text()):raise ValueError('Export changed model body')
 for mode in ('full','legacy_static','dynamic','dynamic_no_por','property_aware_static'):
  d=out/mode;d.mkdir()
  if mode=='dynamic_no_por':copy_without_por(out/'dynamic',d)
  else:
   source=out/(mode+'.rebeca') if 'static' in mode else model
   command(['java','-jar',jar,'-s',source,'-p',prop,'-e','TIMED_REBECA','-v','2.3','-o',d,*(['--aria'] if mode=='dynamic' else [])],ROOT,d/'generate.log')
  if mode=='property_aware_static':
   actors=re.findall(r'->setPriority\((\d+)\)',(d/'AbstractTimedRebecaAnalyzer.cpp').read_text())
   methods=[v.strip() for f in d.glob('*Actor.cpp') for v in re.findall(r'messagePriorities\[\d+\]\s*=\s*([^;]+);',f.read_text())]
   if not actors or set(actors)!={'1'} or not methods or set(methods)!={'1'}:raise ValueError('Property-aware export still restricts scheduling')
  command(['g++','-std=c++11','-pthread','-O2',*[f.name for f in sorted(d.glob('*.cpp'))],'-o','execute'],d,d/'compile.log')
  observation=sample(d,0,30);xml=ET.parse(d/'report-0.xml').getroot();observation['assertion_message']=xml.findtext('checked-property/message')
  expected_result='satisfied' if mode=='legacy_static' else 'assertion failed'
  if observation['result']!=expected_result:raise ValueError((mode,'Unexpected outcome',observation))
  if expected_result=='assertion failed' and (observation['assertion_message']!='NoEarlyStore' or observation['trace_states']<1):raise ValueError('Wrong or missing property counterexample')
  result['modes'][mode]=observation;print(mode,observation['result'],observation['states'],observation['transitions'],flush=True)
  (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
 # The original parameterless CLI and missing/malformed-property handling are explicit.
 for extra in (['--property',str(out/'missing.property')],['--unknown',str(prop)],['--property']):
  check=subprocess.run(['java','-jar',str(aria/'target/erdg-tool-0.1.0.jar'),'file',str(model),*extra],cwd=aria,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  if check.returncode==0:raise ValueError('Invalid option/property was silently accepted')
 result['invalid_property_options_rejected']=True
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS: legacy false negative reproduced; property-aware export detects NoEarlyStore')
if __name__=='__main__':main()
