#!/usr/bin/env python3
import argparse,json,re,os
import xml.etree.ElementTree as ET
from pathlib import Path
from actor_local_models import model,property_text,deferred_error_model
from run_quiescence_models import ROOT,command
from benchmark_scaling import copy_without_por
from experiment_online_property_filter import native_run
from compare_model_suite import digest
from audit_actor_local_graphs import audit

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);rows={};classes=out/'classes';classes.mkdir();jar=ROOT/'target/rmc-2.14.jar'
 command(['javac','-cp',jar,'-d',classes,ROOT/'tests/PropertyEffectAstAudit.java'],ROOT,out/'compile-metadata.log')
 cases=[('healthy2',2,False,False,False,False),('healthy3',3,False,False,False,False),('healthy4',4,False,False,False,False),('global_violation',3,True,False,False,False),('source_assertion',3,False,True,False,False),('deadlock',3,False,False,True,False),('cross_send_refused',2,False,False,True,True),('renamed_product',3,False,False,False,False),('deferred_actor_assertion',3,False,True,False,False)]
 # The cross-send negative retains a fixed number of circulating messages and must use full choices.
 for name,n,bad,fault,terminal,cross in cases:
  case=out/name;case.mkdir();source=case/'model.rebeca';prop=case/'model.property';source.write_text(model(n,fault=fault,terminating=terminal,cross=cross));prop.write_text(property_text(bad=bad))
  if name=='deferred_actor_assertion':source.write_text(deferred_error_model())
  if name=='renamed_product':
   source.write_text(model(3,bound=3).replace('Node','Rotor').replace('value','phase').replace('N0','R0').replace('N1','R1').replace('N2','R2'))
   prop.write_text(property_text(bound=3).replace('value','phase').replace('N0','R0'))
  filtered=case/'filtered'
  command(['java','-jar',ROOT/'target/rmc-2.14.jar','-s',source,'-p',prop,'--aria','--aria-property-filter','-e','TIMED_REBECA','-v','2.3','-o',filtered],ROOT,case/'generate.log')
  text=(filtered/'TimedModelChecker.cpp').read_text();table=re.search(r'static const bool propertyInvisible\[[^;]+;',text)
  if not table or ('true' in table[0])==cross:raise ValueError(('Structural permission mismatch',name))
  command(['java','-cp',str(jar)+os.pathsep+str(classes),'PropertyEffectAstAudit',source,prop,case/'metadata.json'],ROOT,case/'metadata.log')
  metadata=json.loads((case/'metadata.json').read_text())
  if metadata['actor_local_runtime_certified']==cross:raise ValueError('Wrong AST structural certificate')
  row={'source_sha256':digest(source),'partial_permissions_present':not cross}
  control=case/'control';control.mkdir();copy_without_por(filtered,control);modes={}
  for mode in ('control','filtered'):
   r=native_run(case/mode);expected='assertion failed' if bad or fault else 'deadlock' if terminal and not cross else 'satisfied'
   if r['result']!=expected or expected!='satisfied' and not r['trace_states']:raise ValueError((name,mode,r))
   if name=='deferred_actor_assertion':
    tree=ET.parse(case/mode/'report-0.xml').getroot();failures=[edge.find('messageserver') for edge in tree.findall('counter-example-trace/transition') if edge.get('destination')=='assertion failed']
    if not any(message is not None and message.get('owner')=='N2' for message in failures):raise ValueError('Deferred actor N2 error was not reached')
    r['failing_actor_verified']='N2'
   modes[mode]=r;print(name,mode,r['result'],r['states'],r['transitions'],flush=True)
  row['modes']=modes
  if not bad and not fault and (not terminal or cross):row['graph_audit']=audit(case)
  rows[name]=row;(out/'summary.json').write_text(json.dumps({'structural_gate':True,'cases':rows},indent=2)+'\n')
 print('PASS: generic actor-local native family and cross-send refusal')
if __name__=='__main__':main()
