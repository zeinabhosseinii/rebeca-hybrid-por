#!/usr/bin/env python3
"""Exact-model offline property-aware POR experiment; full graph required, no online change."""
import argparse,collections,hashlib,json,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
from action_por_reference import Graph,read_full_graph
from audit_both_reductions import every_cycle_has_full_state
from run_quiescence_models import ROOT,command

MODEL_SHA='e8e0a20c1af6af94fb02c59ff7ad2f9b33a84dd6b55872ee3b5cb89135a325f6'
PROPERTY_SHA='0036336cc8d2dcff564aedc3651c4e4084ed6f8eab031aae41a3b2790995947a'
# Hand-reviewed write effects for the exact pinned source, not a general extractor.
WRITES={('starter','STARTWORKERS'):set(),('cell','KEEPALIVE'):set(),('cell','STORE'):{('cell','Cell.value')},
 ('worker1','WRITEVALUE'):{('worker1','Worker.sent')},('worker2','WRITEVALUE'):{('worker2','Worker.sent')}}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def values(state):
 return {(r.get('name'),v.get('name')):v.text for r in state.findall('rebec') for v in r.findall('statevariables/variable')}
def property_spec(name):
 if name=='NoEarlyStore':return {('cell','Cell.value'),('worker2','Worker.sent')},lambda v:not(v[('cell','Cell.value')]=='1' and v[('worker2','Worker.sent')]=='false')
 if name=='StoredBounds':return {('cell','Cell.value')},lambda v:0<=int(v[('cell','Cell.value')])<=2
 raise ValueError('Unsupported property: no predicate interpretation, no result claimed')

def search(graph,truth,reads,reduced=True,writes=WRITES):
 initial=graph.initial;queue=collections.deque([initial]);opened={initial};closed=set();parents={initial:None};edges=collections.defaultdict(lambda:collections.defaultdict(set));full=set();decisions=[];trials=[];expanded=[];steps=0
 def finish(outcome,bad=None):
  trace=[];v=bad
  while v is not None:
   parent=parents[v]
   if parent is None:break
   s,a=parent;trace.append({'source':s,'action':a,'target':v});v=s
  trace.reverse()
  complete=outcome=='satisfied'
  return {'result':outcome,'discovered_states':len(parents),'expanded_states':len(expanded),'explored_edges':steps,'counterexample':trace,
   'decisions':decisions,'candidate_trials':trials,'complete_reduced_graph':complete,
   'strong_cycle_passed':every_cycle_has_full_state(parents,edges,full) if complete else None,
   'no_processing_after_first_error':True}
 if not truth[initial]:return finish('assertion failed',initial)
 while queue:
  s=queue.popleft();opened.remove(s);chosen=None
  if not graph.edges[s]:return finish('deadlock',s)
  if reduced:
   for act,targets in sorted(graph.edges[s].items()):
    if act not in writes:trials.append({'state':s,'action':act,'reason':'unknown_effects'});continue
    if writes[act]&reads:trials.append({'state':s,'action':act,'reason':'property_visible_write'});continue
    ok,evidence=graph.certify(s,act)
    if not ok:trials.append({'state':s,'action':act,**evidence});continue
    if any(t==s or t in closed for t in targets):trials.append({'state':s,'action':act,'reason':'proviso_rejected'});continue
    chosen=act;trials.append({'state':s,'action':act,'reason':'accepted','dependency_evidence':evidence});break
  actions=graph.edges[s] if chosen is None else {chosen:graph.edges[s][chosen]}
  semantic_full=actions==graph.edges[s]
  decisions.append({'state':s,'selected':sorted(actions),'full':semantic_full});expanded.append(s)
  for act,targets in sorted(actions.items()):
   for t in sorted(targets):
    steps+=1;edges[s][act].add(t)
    if t not in parents:parents[t]=(s,act)
    if not truth[t]:return finish('assertion failed',t)
    if t not in closed and t not in opened and t!=s:opened.add(t);queue.append(t)
  # Only mark a full vertex after every selected edge has been processed.
  if semantic_full:full.add(s)
  closed.add(s)
 return finish('satisfied')

def build(directory,model):
 if directory.exists():raise ValueError('Full export output must be fresh')
 directory.mkdir(parents=True)
 command(['java','-jar',ROOT/'target/rmc-2.14.jar','-s',model,'-e','TIMED_REBECA','-v','2.3','-o',directory],ROOT,directory/'generate.log')
 command(['g++','-std=c++11','-pthread','-O2','-DEXPORT_STATE_SPACE',*[p.name for p in sorted(directory.glob('*.cpp'))],'-o','execute'],directory,directory/'compile.log')
 with (directory/'report.xml').open('w') as report,(directory/'errors.log').open('w') as error:subprocess.run(['./execute'],cwd=directory,stdout=report,stderr=error,check=True,timeout=30)
 # NoEarlyStore deliberately omitted ONLY for complete offline graph construction.
 # Its checker below stops at its first violation; native property-aware path is separate.
 (directory/'provenance.json').write_text(json.dumps({'model_sha256':digest(model),'rmc_jar_sha256':digest(ROOT/'target/rmc-2.14.jar'),'external_property_omitted_for_reference_only':True},indent=2)+'\n')

def run(directory):
 model=ROOT/'tests/fixtures/CellRegisterObserved.rebeca';prop=model.with_suffix('.property')
 if digest(model)!=MODEL_SHA or digest(prop)!=PROPERTY_SHA:raise ValueError('Review changed model/property before using effects or observations')
 provenance=json.loads((directory/'provenance.json').read_text())
 if provenance['model_sha256']!=MODEL_SHA or not provenance['external_property_omitted_for_reference_only']:raise ValueError('Unreviewed graph provenance')
 raw=read_full_graph(directory/'statespace.xml',directory/'report.xml');tree=ET.parse(directory/'statespace.xml').getroot();states={s.get('id'):s for s in tree.findall('state')};v={s:values(x) for s,x in states.items()}
 result={'reference_only':True,'online_generator_changed':False,'static_export_changed':False,'full_graph_required':True,'source_sha256':MODEL_SHA,'property_sha256':PROPERTY_SHA,'provenance':provenance,'full_graph_sha256':digest(directory/'statespace.xml'),'full_states':len(states),'hand_reviewed_effects_exact_model_only':True,'properties':{}}
 for name in ('NoEarlyStore','StoredBounds'):
  reads,predicate=property_spec(name);g=Graph();g.initial=raw.initial;g.edges=raw.edges;g.observations={s:tuple((key,v[s][key]) for key in sorted(reads)) for s in states};truth={s:predicate(fields) for s,fields in v.items()}
  full=search(g,truth,reads,False);reduced=search(g,truth,reads,True)
  if full['result']!=reduced['result']:raise ValueError('Property result mismatch')
  if name=='NoEarlyStore' and (full['result']!='assertion failed' or not reduced['counterexample']):raise ValueError('Lost violation')
  if name=='StoredBounds' and (full['result']!='satisfied' or reduced['strong_cycle_passed'] is not True):raise ValueError('Healthy/cycle check failed')
  result['properties'][name]={'reads':[list(x) for x in sorted(reads)],'full':full,'property_aware':reduced}
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--full',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--build-full',action='store_true');a=p.parse_args();full=a.full.resolve()
 if a.build_full:build(full,ROOT/'tests/fixtures/CellRegisterObserved.rebeca')
 result=run(full);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
 for name,item in result['properties'].items():
  for mode in ('full','property_aware'):
   x=item[mode];print(name,mode,x['result'],'states',x['discovered_states'],'edges',x['explored_edges'],'cycle',x['strong_cycle_passed'])
 print('PASS: finite offline experiment; production conservative export unchanged')
if __name__=='__main__':main()
