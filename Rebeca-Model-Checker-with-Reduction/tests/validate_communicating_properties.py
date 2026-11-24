#!/usr/bin/env python3
import argparse,json,os,re
from pathlib import Path
from communicating_property_models import cases
from run_quiescence_models import ROOT,command
from benchmark_scaling import copy_without_por
from experiment_online_property_filter import native_run
from compare_model_suite import digest
from audit_actor_local_graphs import audit,load

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);classes=out/'classes';classes.mkdir();jar=ROOT/'target/rmc-2.14.jar';command(['javac','-cp',jar,'-d',classes,ROOT/'tests/PropertyEffectAstAudit.java'],ROOT,out/'compile-metadata.log');summary={'communicating_models':True,'rmc_jar_sha256':digest(jar),'cases':{}}
 for name,text,property_text,expected,certified in cases():
  case=out/name;case.mkdir();source=case/'model.rebeca';prop=case/'model.property';source.write_text(text);prop.write_text(property_text)
  command(['java','-cp',str(jar)+os.pathsep+str(classes),'PropertyEffectAstAudit',source,prop,case/'metadata.json'],ROOT,case/'metadata.log');metadata=json.loads((case/'metadata.json').read_text())
  if metadata['nullary_queue_certified']!=certified or certified and metadata['token_bound']!=(3 if name.startswith('three_token_') else 2):raise ValueError((name,'Wrong queue certificate',metadata))
  filtered=case/'filtered';command(['java','-jar',jar,'-s',source,'-p',prop,'--aria','--aria-property-filter','-e','TIMED_REBECA','-v','2.3','-o',filtered],ROOT,case/'generate.log')
  if ('nullary_queue_closure' in (filtered/'TimedModelChecker.cpp').read_text())!=certified:raise ValueError('Wrong native proof path')
  control=case/'control';control.mkdir();copy_without_por(filtered,control);modes={}
  for mode in ('control','filtered'):
   r=native_run(case/mode)
   if r['result']!=expected or expected!='satisfied' and r['trace_states']<1:raise ValueError((name,mode,'Wrong first-error outcome',r))
   diagnostics=(case/mode/'errors-0.log').read_text().splitlines()
   r['queue_dependency_rejections']=sum(line.startswith('POR_QUEUE_BLOCK ') for line in diagnostics)
   r['queue_payload_rejections']=sum(line.startswith('POR_PAYLOAD_BLOCK ') for line in diagnostics)
   modes[mode]=r;print(name,mode,r['result'],r['states'],r['transitions'],flush=True)
  if name=='shared_hub_field' and metadata.get('commuting_scalar_pairs',0)<1:raise ValueError('Identical scalar update certificate was not used')
  row={'source_sha256':digest(source),'certificate':metadata['nullary_queue_certified'],'token_bound':metadata.get('token_bound'),'refusal':metadata.get('nullary_queue_refusal'),'modes':modes}
  if expected=='satisfied':row['graph_audit']=audit(case)
  if name=='three_token_union' and not any(len(c['actions'])>1 for c in row['graph_audit']['partial_certificates']):raise ValueError('Mixed Hub union was not exercised')
  if name=='read_write_hub' and modes['filtered']['queue_dependency_rejections']==0:raise ValueError('Future conflicting Hub handler was not exercised')
  if name=='different_constants_same_syntax' and (metadata.get('commuting_scalar_pairs',0)!=0 or modes['filtered']['queue_dependency_rejections']==0):raise ValueError('Different parameter constants must not trigger scalar equivalence')
  if name in {'different_unread_payloads','three_token_mixed_payloads'}:
   _,_,edges=load(control,True)
   payloads={action[2] for rel in edges.values() for action in rel
             if action[:2]==('PrimarySrc','DISPATCH')}
   if len(payloads)<2 or not modes['filtered']['queue_payload_rejections']:
    raise ValueError((name,'Distinct payload identities or runtime fallback missing'))
  if name=='three_token_mixed_payloads':
   if not any(sum(action[:2]==('PrimarySrc','DISPATCH') for action in rel)>=2 for rel in edges.values()):
    raise ValueError('No state with two distinct Dispatch payloads enabled')
  if name=='mutual_variable_payload_fallback':
   diagnostics=(filtered/'errors-0.log').read_text().splitlines()
   blocked={line.split()[1] for line in diagnostics if line.startswith('POR_PAYLOAD_BLOCK ')}
   full={line.split()[1] for line in diagnostics if line.startswith('POR_FULL ')}
   if not blocked & full:
    raise ValueError('Expected full expansion after a variable-payload rejection')
  summary['cases'][name]=row;(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 summary['native_executions']=2*len(summary['cases']);summary['all_passed']=True;(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('PASS: supplied communicating LoadBalancer, renamed/mutant models, native errors and finite semantic audits')
if __name__=='__main__':main()
