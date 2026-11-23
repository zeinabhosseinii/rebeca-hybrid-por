#!/usr/bin/env python3
"""Inductive interval certificate tests; refusals are not model counterexamples."""
import argparse,hashlib,json,os,platform,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
from run_quiescence_models import ROOT
from scaling_models import make_model
from run_cycle_barriers import generate,compile_run

def replace_one(text,before,after):
 if text.count(before)!=1:raise ValueError(('Expected one mutation site',before))
 return text.replace(before,after)

def bounded(n):
 lines=[]
 for line in make_model('shared',n).splitlines():
  check=None
  if line.startswith(' msgsrv Tick()'):check='assertion(cycle >= 0 && cycle < 3);'
  if line.startswith(' msgsrv Step'):check='assertion(count >= 0 && count < 3);'
  if line.startswith(' msgsrv Finish'):check=f'assertion(done >= 0 && done < {n});'
  if check:
   prefix,end=line.rsplit(' }',1);line=prefix+' '+check+' }'+end
  lines.append(line)
 return '\n'.join(lines)+'\n'

def cases():
 healthy=(ROOT/'tests/fixtures/ScalePropertyHealthy.rebeca').read_text()
 hub=' Hub() { done=0; count=0; }'
 return [
 ('healthy',healthy,True,None),
 ('three_workers',bounded(3),True,None),
 ('six_workers',bounded(6),True,None),
 ('renamed_fields',healthy.replace('cycle','phase').replace('count','total').replace('done','finished'),True,None),
 ('other_valid_initial',replace_one(healthy,'Worker0() { cycle=0;','Worker0() { cycle=1;'),True,None),
 ('valid_extra_writer',replace_one(healthy,hub,hub+'\n msgsrv Reset() { count=0; }'),True,None),
 ('equivalent_guard',replace_one(healthy,'if(cycle<3) { H.Step0(); } else { cycle=0; H.Finish0(); }','if(cycle>=3) { cycle=0; H.Finish0(); } else { H.Step0(); }'),True,None),
 ('removed_reset',replace_one(healthy,'cycle=0; H.Finish0();','H.Finish0();'),False,'assertion failed'),
 ('bad_initial',replace_one(healthy,'Worker0() { cycle=0;','Worker0() { cycle=3;'),False,None),
 ('missing_initial',replace_one(healthy,'Worker0() { cycle=0; self.Tick(); }','Worker0() { self.Tick(); }'),False,None),
 ('extra_writer',replace_one(healthy,hub,hub+'\n msgsrv Corrupt() { count=9; }'),False,None),
 ('int32_overflow',replace_one(healthy,'cycle=cycle+1; if(cycle<3) { H.Step0();','cycle=cycle+2147483647; if(cycle<3) { H.Step0();'),False,None),
 ('assert_before_wrap',replace_one(healthy,'cycle=cycle+1; if(cycle<3) { H.Step0();','cycle=cycle+1; assertion(cycle >= 0 && cycle < 3); if(cycle<3) { H.Step0();'),False,None),
 ('unsupported_loop',replace_one(healthy,hub,hub+'\n msgsrv Loop() { while(false) { count=0; } }'),False,None),
 ('tighter_assertion',replace_one(healthy,'H.Finish0(); } assertion(cycle >= 0 && cycle < 3);','H.Finish0(); } assertion(cycle >= 0 && cycle < 2);'),False,'assertion failed'),
 ('existing_fault',(ROOT/'tests/fixtures/ScalePropertyFault.rebeca').read_text(),False,None),
 ('missing_lower_bound',replace_one(healthy,'H.Finish0(); } assertion(cycle >= 0 && cycle < 3);','H.Finish0(); } assertion(cycle < 3);'),False,None),
 ]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--skip-native',action='store_true');a=p.parse_args();out=a.output.resolve()
 if out.exists():p.error('Choose fresh output')
 out.mkdir(parents=True);classes=out/'classes';classes.mkdir();jar=ROOT/'target/rmc-2.14.jar'
 subprocess.run(['javac','-cp',str(jar),'-d',str(classes),str(ROOT/'tests/AssertionObservationAudit.java'),str(ROOT/'tests/CounterInvariantAudit.java')],check=True)
 summary={'platform':platform.platform(),'rmc_jar_sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),
          'verifier_java_sha256':hashlib.sha256((ROOT/'tests/CounterInvariantAudit.java').read_bytes()).hexdigest(),'offline_only':True,'runtime_gate_changed':False,'native_checks_enabled':not a.skip_native,'cases':{}}
 def save():(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 for name,text,expected,native_expected in cases():
  case=out/name;case.mkdir();model=case/(name+'.rebeca');model.write_text(text);report=case/'certificate.json'
  with (case/'audit.log').open('w') as log:
   subprocess.run(['java','-cp',str(jar)+os.pathsep+str(classes),'CounterInvariantAudit',str(model),str(report)],stdout=log,stderr=subprocess.STDOUT,check=True)
  result=json.loads(report.read_text());assert result['all_assertions_invariant']==expected,(name,result)
  assert result['runtime_gate_changed'] is False and result['runtime_observation_compatibility_certified'] is False
  summary['cases'][name]={'expected_certificate':expected,'report':result};save()
  if native_expected and not a.skip_native:
   native=case/'native';generate(model,name,'baseline',native);measurement=compile_run(native)
   xml=ET.parse(native/'report.xml').getroot();trace=xml.findall('counter-example-trace/state')
   assert measurement['result']==native_expected and trace,(name,measurement)
   failures=[e for e in xml.findall('counter-example-trace/transition') if e.get('destination')=='assertion failed']
   assert any(e.find('messageserver') is not None and e.find('messageserver').get('owner')=='W0' and e.find('messageserver').get('title')=='TICK' for e in failures),name
   summary['cases'][name]['native']={**measurement,'trace_states':len(trace),'complete_space':False};save()
  print(name,'certificate=',expected,'reason=',result.get('refusal'),flush=True)
 summary['all_checks_passed']=True;save()
 print('PASS: bounded inductive fragment, mutation refusals and requested native fault checks; runtime unchanged')

if __name__=='__main__':main()
