#!/usr/bin/env python3
"""Compiler-AST mutation checks and fail-closed consumer checks."""
import argparse,json,os,subprocess
from pathlib import Path
from run_quiescence_models import ROOT,command
from experiment_ast_property_representatives import derive,run,evaluate

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);classes=out/'classes';classes.mkdir();jar=ROOT/'target/rmc-2.14.jar'
 command(['javac','-cp',jar,'-d',classes,ROOT/'tests/AssertionObservationAudit.java',ROOT/'tests/PropertyEffectAstAudit.java'],ROOT,out/'compile.log')
 model=(ROOT/'tests/fixtures/CellRegisterObserved.rebeca').read_text();prop=(ROOT/'tests/fixtures/CellRegisterObserved.property').read_text()
 cases=[('baseline',model,prop,True),('renamed_field',model.replace('sent','finished'),prop.replace('sent','finished'),True),
 ('different_instance',model,prop.replace('worker2.sent','worker1.sent'),True),
 ('extra_branch_write',model.replace('sent = true;','sent = true; if (id == 1) { id = 2; }'),prop,True),
 ('timed_send',model.replace('cell.store(id);','cell.store(id) after(1);'),prop,False),
 ('array_field',model.replace('byte id;','byte id; int[2] slots;'),prop,False),
 ('loop',model.replace('sent = true;','sent = true; while (false) { id = id; }'),prop,False),
 ('increment',model.replace('sent = true;','sent = true; id++;'),prop,False),
 ('local_declaration',model.replace('sent = true;','sent = true; int local = 0;'),prop,False),
 ('property_arithmetic',model,prop.replace('cell.value == 1','cell.value + 1 == 2'),False),
 ('property_alias',model,'property { define { early = cell.value == 1; } Assertion { NoEarlyStore: !early; } }\n',False),
 ('multiple_assertions',model,prop.replace('NoEarlyStore:', 'Other: cell.value <= 2; NoEarlyStore:'),False),
 ('main_nondeterminism',model.replace('worker1(cell):(1)','worker1(cell):(?(1,2))'),prop,False)]
 rows=[]
 for name,text,property_text,expected in cases:
  folder=out/name;folder.mkdir();source=folder/'model.rebeca';source.write_text(text);property_file=folder/'model.property';property_file.write_text(property_text);output=folder/'metadata.json'
  command(['java','-cp',str(jar)+os.pathsep+str(classes),'PropertyEffectAstAudit',source,property_file,output],ROOT,folder/'compiler.log')
  r=json.loads(output.read_text());assert r['metadata_supported']==expected,(name,r)
  if not expected:
   assert derive(r) is None
   # Unsupported predicates must NOT be evaluated as true. A full checker must be used instead.
   refused=run(Path('/unused-full-graph'),r);assert refused['status']=='unsupported_not_checked' and not refused['reduction_enabled']
  if name=='baseline':
   assert {tuple(x) for x in r['property_reads']}=={('cell','Cell.value'),('worker2','Worker.sent')}
   methods={tuple(x['action']):x for x in r['actions']}
   assert methods[('worker1','WRITEVALUE')]['sends']==[['cell','STORE']]
   assert methods[('worker2','WRITEVALUE')]['writes']==[['worker2','Worker.sent']]
  if name=='renamed_field':assert ['worker2','Worker.finished'] in r['property_reads']
  if name=='different_instance':assert ['worker1','Worker.sent'] in r['property_reads'] and ['worker2','Worker.sent'] not in r['property_reads']
  if name=='extra_branch_write':assert ['worker2','Worker.id'] in next(x['writes'] for x in r['actions'] if x['action']==['worker2','WRITEVALUE'])
  rows.append({'case':name,'metadata_supported':expected,'reason':r.get('reason'),'unknown_actions':[x.get('reason') for x in r.get('actions',[]) if not x.get('complete')]});print(name,expected,flush=True)
 try:evaluate({'kind':'opaque'},{});raise AssertionError('Opaque predicate accepted')
 except ValueError:pass
 (out/'summary.json').write_text(json.dumps({'cases':rows,'all_passed':True,'unsupported_consumer_reduction_disabled':True,'unknown_predicate_ir_refused':True},indent=2)+'\n')
 print('PASS: 13 compiler-AST cases and fail-closed consumer behavior')
if __name__=='__main__':main()
