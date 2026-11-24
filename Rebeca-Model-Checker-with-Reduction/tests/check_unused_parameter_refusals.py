#!/usr/bin/env python3
"""Accept fixed payload use; reject multiple payloads, forwarding and computation."""
import argparse,json,os
from pathlib import Path
from run_quiescence_models import ROOT,command
from validate_unused_parameters import variants

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);classes=out/'classes';classes.mkdir();jar=ROOT/'target/rmc-2.14.jar'
 command(['javac','-cp',jar,'-d',classes,ROOT/'tests/PropertyEffectAstAudit.java'],ROOT,out/'compile.log')
 _,source,prop,_,_=variants()[0]
 tests=[('unread_literal',source,True),('different_literals',source.replace('PrimarySrc.Dispatch(7);','PrimarySrc.Dispatch(9);',1),False),('guard_read',source.replace('Cycle > 2','Cycle > ignored',1),True),('assertion_read',source.replace('Cycle = Cycle + 1;','assertion(ignored == 7); Cycle = Cycle + 1;',1),True),('forwarded_payload',source.replace('Relay.Forward();','self.Dispatch(ignored); Relay.Forward();',1),False),('computed_payload',source.replace('.Dispatch(7)', '.Dispatch(3 + 4)'),False)]
 rows=[]
 for name,text,expected in tests:
  d=out/name;d.mkdir();model=d/'model.rebeca';model.write_text(text);property_file=d/'model.property';property_file.write_text(prop)
  command(['java','-cp',str(jar)+os.pathsep+str(classes),'PropertyEffectAstAudit',model,property_file,d/'metadata.json'],ROOT,d/'compile.log');m=json.loads((d/'metadata.json').read_text());assert m.get('nullary_queue_certified',False)==expected,(name,m)
  rows.append({'case':name,'certified':expected,'reason':m.get('nullary_queue_refusal')})
 (out/'summary.json').write_text(json.dumps({'all_passed':True,'cases':rows},indent=2)+'\n');print('PASS: fixed payload use and unsupported-payload refusals')
if __name__=='__main__':main()
