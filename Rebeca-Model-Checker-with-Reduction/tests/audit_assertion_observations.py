#!/usr/bin/env python3
"""Offline typed-AST diagnostics; no runtime independence certificate produced."""
import argparse,json,os,subprocess
from pathlib import Path
from test_assertion_observation import check
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
 if out.exists():p.error('Choose a fresh output directory')
 out.mkdir(parents=True);classes=out/'classes';classes.mkdir();jar=ROOT/'target/rmc-2.14.jar'
 subprocess.run(['javac','-cp',str(jar),'-d',str(classes),str(ROOT/'tests/AssertionObservationAudit.java')],check=True)
 reports={}
 for tag,source in [('healthy','ScalePropertyHealthy.rebeca'),('fault','ScalePropertyFault.rebeca'),('unsupported','AssertionObservationUnsupported.rebeca')]:
  with (out/(tag+'.log')).open('w') as log:
   subprocess.run(['java','-cp',str(jar)+os.pathsep+str(classes),'AssertionObservationAudit',str(ROOT/'tests/fixtures'/source),str(out/(tag+'.json'))],stdout=log,stderr=subprocess.STDOUT,check=True)
  report=json.loads((out/(tag+'.json')).read_text())
  assert report['runtime_independence_certified'] is False and report['runtime_gate_changed'] is False
  assert report['current_full_barrier_gate']==(tag=='healthy')
  reports[tag]=report
 assert reports['healthy']['traversal_complete'] and reports['fault']['traversal_complete']
 assert len(reports['healthy']['assertions'])==6 and len(reports['fault']['assertions'])==7
 assert all(row['syntax_supported'] for key in ('healthy','fault') for row in reports[key]['assertions'])
 flags=[row['syntax_supported'] for row in reports['unsupported']['assertions']]
 assert flags==[True,False,False,False,False,False,True],flags
 assert any(row['actor_class']=='Hub' and row['local_read_fields']==['count'] and {w['method'] for w in row['potential_runtime_writers']}=={'Step0','Step1'} for row in reports['healthy']['assertions'])
 result={'diagnostic_only':True,'runtime_gate_changed':False,'reports':reports,'counterexample':check()}
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS: typed local footprints, side-effect/time/parameter rejection, and C1 counterexample; runtime certificate remains false')

if __name__=='__main__':main()
