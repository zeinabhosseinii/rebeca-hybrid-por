#!/usr/bin/env python3
import argparse,json,os
from pathlib import Path
from actor_local_models import model,property_text
from run_quiescence_models import ROOT,command

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);classes=out/'classes';classes.mkdir();jar=ROOT/'target/rmc-2.14.jar';command(['javac','-cp',jar,'-d',classes,ROOT/'tests/PropertyEffectAstAudit.java'],ROOT,out/'compile.log')
 local=model(2);cross=model(2,cross=True,terminating=True)
 cases=[('local',local,True),('renamed',local.replace('Node','Counter').replace('value','state'),True),('cross_send',cross,False),('unreachable_cross_send',cross.replace('peer.tick();','if (false) { peer.tick(); } self.tick();'),False),('timed_self_send',local.replace('self.tick();','self.tick() after(1);'),False),('array',local.replace('int value;','int value; int[2] slots;'),False),('increment',local.replace('value = value + 1;','value++;'),False),('loop',local.replace('value = value + 1;','while (false) { value = 0; } value = value + 1;'),False),('annotated',local.replace('msgsrv tick()','@priority(1) msgsrv tick()'),False)]
 rows=[]
 for name,source,expected in cases:
  folder=out/name;folder.mkdir();m=folder/'model.rebeca';p=folder/'model.property';m.write_text(source);p.write_text(property_text().replace('value','state') if name=='renamed' else property_text());r=folder/'metadata.json';command(['java','-cp',str(jar)+os.pathsep+str(classes),'PropertyEffectAstAudit',m,p,r],ROOT,folder/'compile.log');d=json.loads(r.read_text());actual=d.get('actor_local_runtime_certified',False)
  if actual!=expected:raise ValueError((name,d))
  rows.append({'case':name,'certified':actual,'metadata_supported':d['metadata_supported'],'reason':d.get('reason')});print(name,actual,flush=True)
 (out/'summary.json').write_text(json.dumps({'all_passed':True,'cases':rows},indent=2)+'\n')
if __name__=='__main__':main()
