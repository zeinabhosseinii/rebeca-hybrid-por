#!/usr/bin/env python3
"""Validate generated/native gate behavior; not a performance benchmark."""
import argparse,json,re,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
from run_quiescence_models import ROOT,command
from run_cycle_barriers import generate,compile_run
from compare_model_suite import digest
from benchmark_scaling import finite_audit

def enabled(directory):
 text=(directory/'TimedModelChecker.cpp').read_text()
 match=re.search(r'return (true|false) && _porResultState->porFullExpanded;',text)
 if not match:raise ValueError('Missing gate helper')
 return match[1]=='true'

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--cases',type=Path,required=True);p.add_argument('--properties',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
 if out.exists():p.error('Choose fresh output')
 out.mkdir(parents=True);a.cases=a.cases.resolve();a.properties=a.properties.resolve()
 source=json.loads((a.properties/'summary.json').read_text())
 assert source['all_expected_outcomes'] and source['rmc_jar_sha256']==digest(ROOT/'target/rmc-2.14.jar')
 healthy=a.properties/'ScalePropertyHealthy';fault=a.properties/'ScalePropertyFault'
 assert enabled(healthy/'dynamic') and not enabled(fault/'dynamic')
 assert source['cases']['ScalePropertyHealthy']['modes']['dynamic']['full_barrier_events']>0
 for mode in ('full','static','dynamic','dynamic_no_por'):
  (healthy/mode/'report-0.xml').write_bytes((healthy/mode/'report.xml').read_bytes())
  assert 'assertion(' in (healthy/mode/'Worker0Actor.cpp').read_text()
 result={'runtime_extension':'proved source assertions plus independent zero-time gate',
         'rmc_jar_sha256':digest(ROOT/'target/rmc-2.14.jar'),'healthy_fault_native':source,
         'finite_healthy_audit':finite_audit(healthy,healthy/'ScalePropertyHealthy.rebeca'),'negative_native':{},'excluded_gates':{}}
 for name in ('removed_reset','tighter_assertion'):
  d=out/name;model=a.cases/name/(name+'.rebeca');generate(model,name,'aria_ast',d)
  assert not enabled(d)
  r=compile_run(d,['-DPOR_DIAGNOSTICS']);xml=ET.parse(d/'report.xml').getroot()
  assert r['result']=='assertion failed' and xml.findall('counter-example-trace/state')
  result['negative_native'][name]={**r,'generated_gate':False,'trace_states':len(xml.findall('counter-example-trace/state'))}
 for mode in ('baseline','aria_ast'):
  d=out/('proved_deadlock_'+mode);generate(ROOT/'tests/fixtures/InvariantCertifiedDeadlock.rebeca','InvariantCertifiedDeadlock',mode,d)
  if mode=='aria_ast':assert enabled(d)
  r=compile_run(d,['-DPOR_DIAGNOSTICS']);xml=ET.parse(d/'report.xml').getroot();log=(d/'errors.log').read_text()
  assert r['result']=='deadlock' and xml.findall('counter-example-trace/state') and 'POR_FULL_BARRIER' not in log
  result['negative_native']['proved_deadlock_'+mode]={**r,'trace_states':len(xml.findall('counter-example-trace/state')),'full_barrier_events':0}
 text=(ROOT/'tests/fixtures/ScalePropertyHealthy.rebeca').read_text();timed=out/'Timed.rebeca';timed.write_text(text.replace('H.Step0();','H.Step0() after(0);',1))
 prop=out/'external.property';prop.write_text('property { define { bounded = H.count < 3; } }\n')
 for name,model,extra in [('timed',timed,[]),('symmetry',ROOT/'tests/fixtures/ScalePropertyHealthy.rebeca',['--symm']),('external_property',ROOT/'tests/fixtures/ScalePropertyHealthy.rebeca',['-p',prop])]:
  d=out/name;d.mkdir();command(['java','-jar',ROOT/'target/rmc-2.14.jar','-s',model,'-e','TIMED_REBECA','-v','2.3','--aria','-o',d,*extra],ROOT,d/'generate.log')
  assert not enabled(d);result['excluded_gates'][name]=False
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS: healthy graph, assertions retained, unproved faults, proved-assertion deadlock, excluded gates')

if __name__=='__main__':main()
