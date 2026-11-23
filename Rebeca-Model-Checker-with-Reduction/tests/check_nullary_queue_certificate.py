#!/usr/bin/env python3
import argparse,json,os
from pathlib import Path
from run_quiescence_models import ROOT,command
from communicating_property_models import cases,BOUNDS,TRUE

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);classes=out/'classes';classes.mkdir();jar=ROOT/'target/rmc-2.14.jar';command(['javac','-cp',jar,'-d',classes,ROOT/'tests/PropertyEffectAstAudit.java'],ROOT,out/'compile.log')
 load=cases()[0][1]
 peer='reactiveclass Node(8) { knownrebecs { Node peer; } statevars { int value; } Node() { value=0; self.tick(); } msgsrv tick() { peer.tick(); peer.tick(); } } main { Node A(B):(); Node B(A):(); }\n'
 sender=peer.replace('peer.tick(); peer.tick();','if (sender == peer) { value=1; } peer.tick();')
 variants=[('load',load,BOUNDS,True),('renamed_load',cases()[2][1],cases()[2][2],True),('shared_field',cases()[3][1],TRUE,True),('conditional_send',cases()[7][1],BOUNDS,False),('insufficient_margin',cases()[8][1],BOUNDS,False),('repeatable_fanout',peer,TRUE,False),('sender_observation',sender,TRUE,False),('timing',load.replace('Relay.Forward();','Relay.Forward() after(1);',1),BOUNDS,False),('nondeterminism',load.replace('Cycle = Cycle + 1;','Cycle = ?(0,1);',1),BOUNDS,False),('reserved_constructor_parameter',load.replace('PrimarySource() {','PrimarySource(int now) {').replace('PrimarySrc(PrimaryRelay):();','PrimarySrc(PrimaryRelay):(0);'),BOUNDS,False),('message_parameters',(ROOT/'tests/fixtures/CellRegisterObserved.rebeca').read_text(),(ROOT/'tests/fixtures/CellRegisterObserved.property').read_text(),False)]
 rows=[]
 for name,source,prop,expected in variants:
  d=out/name;d.mkdir();model=d/'model.rebeca';model.write_text(source);property_file=d/'model.property';property_file.write_text(prop);meta=d/'metadata.json'
  command(['java','-cp',str(jar)+os.pathsep+str(classes),'PropertyEffectAstAudit',model,property_file,meta],ROOT,d/'compiler.log');r=json.loads(meta.read_text())
  if r.get('nullary_queue_certified',False)!=expected:raise ValueError((name,r))
  if expected and r['token_bound']!=2:raise ValueError('Wrong conservative token budget')
  rows.append({'case':name,'certified':expected,'token_bound':r.get('token_bound'),'refusal':r.get('nullary_queue_refusal',r.get('reason'))});print(name,expected,rows[-1]['refusal'],flush=True)
 (out/'summary.json').write_text(json.dumps({'all_passed':True,'cases':rows},indent=2)+'\n');print('PASS: communicating queue certificate positives and refusal mutations')
if __name__=='__main__':main()
