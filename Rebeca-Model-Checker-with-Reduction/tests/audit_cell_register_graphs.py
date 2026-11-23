#!/usr/bin/env python3
"""Exact finite-model comparison of full and same-generated PO-off Cell graphs."""
import argparse,collections,hashlib,json,re,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

SOURCE_SHA='88b73b2cc8caf2bd6441024fd3afeef17b5d3d1e5e9fde1b25717b734bafcae0'
MODES=('full','static','dynamic','dynamic_no_por')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def signature(state,ordered=False,keep_sender=False):
 actors=[]
 for actor in state.findall('rebec'):
  if actor.findtext('now')!='0':raise ValueError('Nonzero actor time')
  variables=tuple(sorted((v.get('name'),v.get('type'),v.text) for v in actor.findall('statevariables/variable')))
  queue=[]
  for m in actor.findall('queue/message'):
   if m.get('arrival')!='0' or m.get('deadline')!='infinity':raise ValueError('Timed message unsupported')
   queue.append((tuple(sorted((k,v) for k,v in m.attrib.items() if keep_sender or k!='sender')),''.join(m.itertext()).strip()))
  actors.append((actor.get('name'),variables,tuple(queue if ordered else sorted(queue,key=repr)),actor.findtext('now')))
 return state.get('atomicpropositions',''),tuple(sorted(actors))
def graph(directory):
 report=ET.parse(directory/'report-graph.xml').getroot()
 if report.findtext('checked-property/result')!='satisfied':raise ValueError('Incomplete/erroneous run')
 tree=ET.parse(directory/'statespace-graph.xml').getroot()
 states={s.get('id'):s for s in tree.findall('state')};edges=collections.defaultdict(lambda:collections.defaultdict(set))
 if len(states)!=int(report.findtext('system-info/reached-states')):raise ValueError('Report/export mismatch')
 for e in tree.findall('transition'):
  if e.get('executionTime')!='0' or e.get('shift')!='0':raise ValueError('Nonzero transition time')
  action=e.find('messageserver')
  if action is None or e.get('source') not in states or e.get('destination') not in states:raise ValueError('Incomplete transition')
  edges[e.get('source')][(action.get('owner'),action.get('title'))].add(e.get('destination'))
 return states,edges

def quotient(states,edges):
 sigs={i:signature(s) for i,s in states.items()};relation={}
 for i in states:
  outcomes={a:frozenset(sigs[t] for t in ts) for a,ts in edges[i].items()}
  if sigs[i] in relation and relation[sigs[i]]!=outcomes:raise ValueError('Projected aliases have different action outcomes')
  relation[sigs[i]]=outcomes
 return sigs,relation

def audit(case):
 model=case/'CellRegisterBounds.rebeca'
 if sha(model)!=SOURCE_SHA:raise ValueError('Audit restricted to reviewed exact healthy source')
 code=re.sub(r'/\*.*?\*/|//[^\n]*','',model.read_text(),flags=re.S)
 if re.search(r'\bsender\b',code):raise ValueError('Sender-sensitive source')
 data={m:graph(case/m) for m in MODES}
 full,control=data['full'],data['dynamic_no_por'];fs,fr=quotient(*full);cs,cr=quotient(*control)
 if fs[next(iter(full[0]))]!=cs[next(iter(control[0]))]:raise ValueError('Initial mismatch')
 if fr!=cr:raise ValueError('Full/PO-off projected transition systems differ')
 ordered_full={signature(s,True) for s in full[0].values()}
 extra=[{'id':i,'state':ET.tostring(s,encoding='unicode')} for i,s in control[0].items() if signature(s,True) not in ordered_full]
 groups=collections.defaultdict(list)
 for i,sig in cs.items():groups[sig].append(i)
 return {'finite_exact_model_only':True,'source_sha256':sha(model),'full_control_projected_graph_equal':True,
         'all_alias_successors_checked':True,'initial_state_equal':True,'parameters_types_values_and_multiplicities_retained':True,
         'projection':{'unused_sender_ignored':True,'zero_time_queue_order_ignored':True},
         'modes':{m:{'raw_states':len(s),'unique_edges':sum(len(ts) for a in e.values() for ts in a.values()),
          'strict_sender_order_states':len({signature(x,True,True) for x in s.values()}),
          'ordered_sender_projected_states':len({signature(x,True) for x in s.values()}),
          'multiset_projected_states':len({signature(x) for x in s.values()}),
          'graph_sha256':sha(case/m/'statespace-graph.xml'),'report_sha256':sha(case/m/'report-graph.xml')} for m,(s,e) in data.items()},
         'control_alias_groups':[ids for ids in groups.values() if len(ids)>1],
         'control_ordered_states_absent_from_full':extra,
         'scope':'Complete finite healthy full/control graphs only; no general generator theorem or static/dynamic POR certificate.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--export-native',action='store_true');a=p.parse_args();case=a.case.resolve()
 if a.export_native:
  for mode in MODES:
   d=case/mode
   with (d/'compile-graph.log').open('w') as log:subprocess.run(['g++','-std=c++11','-pthread','-O2','-DEXPORT_STATE_SPACE',*[x.name for x in sorted(d.glob('*.cpp'))],'-o','execute-graph'],cwd=d,stdout=log,stderr=log,check=True,timeout=180)
   with (d/'report-graph.xml').open('w') as report,(d/'errors-graph.log').open('w') as err:subprocess.run(['./execute-graph','-x','statespace-graph.xml'],cwd=d,stdout=report,stderr=err,check=True,timeout=30)
 result=audit(case);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
