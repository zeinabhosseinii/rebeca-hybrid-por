#!/usr/bin/env python3
"""Use typed compiler-AST metadata in the separate finite-graph POR experiment."""
import argparse,json,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
from action_por_reference import Graph,read_full_graph
from experiment_property_representatives import search,values,digest,build
from run_quiescence_models import ROOT,command

def convert(text,kind):
 if kind=='boolean':
  if text not in ('true','false'):raise ValueError('Invalid boolean graph observation')
  return text=='true'
 if kind not in ('int','short','byte'):raise ValueError('Unsupported observation type')
 return int(text)
def evaluate(node,state):
 kind=node['kind']
 if kind=='field':return convert(state[tuple(node['key'])],node['type'])
 if kind=='literal':return convert(node['value'],node['type'])
 if kind=='unary' and node['op']=='!':return not evaluate(node['operand'],state)
 if kind=='binary':
  op=node['op'];left=evaluate(node['left'],state)
  if op=='&&':return left and evaluate(node['right'],state)
  if op=='||':return left or evaluate(node['right'],state)
  right=evaluate(node['right'],state)
  if op=='==':return left==right
  if op=='!=':return left!=right
  if op=='<':return left<right
  if op=='<=':return left<=right
  if op=='>':return left>right
  if op=='>=':return left>=right
 raise ValueError('Unsupported predicate IR; no property outcome claimed')

def derive(metadata):
 if not metadata.get('metadata_supported'):return None
 reads={tuple(x) for x in metadata['property_reads']};writes={}
 for row in metadata['actions']:
  if not row.get('complete'):return None
  key=tuple(row['action'])
  if key in writes:raise ValueError('Ambiguous action identity')
  writes[key]={tuple(x) for x in row['writes']}
 return reads,writes

def run(full,metadata):
 if not metadata.get('metadata_supported'):return {'status':'unsupported_not_checked','reduction_enabled':False,'reason':metadata.get('reason')}
 provenance=json.loads((full/'provenance.json').read_text())
 if provenance['model_sha256']!=metadata['source_sha256']:raise ValueError('Graph and AST source differ')
 raw=read_full_graph(full/'statespace.xml',full/'report.xml');tree=ET.parse(full/'statespace.xml').getroot();state_values={s.get('id'):values(s) for s in tree.findall('state')};reads,writes=derive(metadata)
 missing={act for actions in raw.edges.values() for act in actions}-writes.keys()
 if missing:raise ValueError('Graph actions lack AST effects')
 raw.observations={s:tuple((k,fields[k]) for k in sorted(reads)) for s,fields in state_values.items()}
 truth={s:evaluate(metadata['predicate'],fields) for s,fields in state_values.items()}
 baseline=search(raw,truth,reads,False,writes);reduced=search(raw,truth,reads,True,writes)
 if baseline['result']!=reduced['result']:raise ValueError('AST-based property preservation mismatch')
 if reduced['result']=='satisfied' and reduced['strong_cycle_passed'] is not True:raise ValueError('Cycle certificate failed')
 return {'status':'checked','reduction_enabled':True,'full':baseline,'property_aware':reduced,'property_reads':metadata['property_reads']}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--full',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--build-full',action='store_true');a=p.parse_args();out=a.output.resolve()
 if out.exists():p.error('Choose fresh output')
 out.mkdir(parents=True);classes=out/'classes';classes.mkdir();jar=ROOT/'target/rmc-2.14.jar'
 if a.build_full:build(a.full.resolve(),ROOT/'tests/fixtures/CellRegisterObserved.rebeca')
 command(['javac','-cp',jar,'-d',classes,ROOT/'tests/AssertionObservationAudit.java',ROOT/'tests/PropertyEffectAstAudit.java'],ROOT,out/'compile-metadata.log')
 model=ROOT/'tests/fixtures/CellRegisterObserved.rebeca';result={'reference_only':True,'online_generator_changed':False,'manual_effects_used':False,'manual_predicate_used':False,'full_graph_required':True,'source_sha256':digest(model),'full_graph_sha256':digest(a.full/'statespace.xml'),'metadata_java_sha256':digest(ROOT/'tests/PropertyEffectAstAudit.java'),'properties':{}}
 for prop in (model.with_suffix('.property'),ROOT/'tests/fixtures/CellRegisterObservedBounds.property'):
  path=out/(prop.stem+'.metadata.json')
  command(['java','-cp',str(jar)+__import__('os').pathsep+str(classes),'PropertyEffectAstAudit',model,prop,path],ROOT,out/(prop.stem+'.log'))
  metadata=json.loads(path.read_text());r=run(a.full,metadata)
  if r['status']!='checked':raise ValueError('Expected fixture metadata rejected: '+str(r))
  name=metadata['property_name'];expected='assertion failed' if prop==model.with_suffix('.property') else 'satisfied'
  if r['property_aware']['result']!=expected:raise ValueError('Fixture outcome changed')
  result['properties'][name]={'metadata':metadata,**r}
  print(name,r['property_aware']['result'],r['property_aware']['discovered_states'],r['property_aware']['explored_edges'],flush=True)
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS: typed-AST effects and property IR, no online change',out)
if __name__=='__main__':main()
