#!/usr/bin/env python3
"""Finite semantic audit of the healthy generated-C++ online property experiment."""
import argparse,collections,json
from pathlib import Path
import xml.etree.ElementTree as ET
from action_por_reference import Graph,read_full_graph
from audit_cell_register_graphs import signature
from audit_both_reductions import every_cycle_has_full_state
from experiment_property_representatives import values,digest
from experiment_ast_property_representatives import evaluate
from run_quiescence_models import ROOT

def require(ok,message):
 if not ok:raise ValueError(message)
def load(directory):
 tree=ET.parse(directory/'statespace.xml').getroot();states={s.get('id'):s for s in tree.findall('state')};sigs={i:signature(s) for i,s in states.items()};edges=collections.defaultdict(lambda:collections.defaultdict(set))
 report=ET.parse(directory/'report-0.xml').getroot();require(report.findtext('checked-property/result')=='satisfied','Incomplete error-prefix graph');require(len(states)==int(report.findtext('system-info/reached-states')),'State/report mismatch')
 for e in tree.findall('transition'):
  require(e.get('executionTime')=='0' and e.get('shift')=='0','Timed edge unsupported');a=e.find('messageserver');edges[e.get('source')][(a.get('owner'),a.get('title'))].add(e.get('destination'))
 return states,sigs,edges

def audit(base):
 meta=json.loads((base/'metadata.json').read_text());require(meta['source_sha256']==digest(ROOT/'tests/fixtures/CellRegisterObserved.rebeca'),'Source mismatch');require(meta['property_sha256']==digest(ROOT/'tests/fixtures/CellRegisterObservedBounds.property'),'Property mismatch')
 control=base/'control';read_full_graph(control/'statespace.xml',control/'report-0.xml')
 states,sigs,edges=load(control);inverse={sig:i for i,sig in sigs.items()};g=Graph();g.initial=inverse[sigs[next(iter(states))]];reads=[tuple(k) for k in meta['property_reads']];relations={}
 for i,s in states.items():
  q=inverse[sigs[i]];v=values(s);require(evaluate(meta['predicate'],v),'Healthy reference observation violated');g.observations[q]=tuple(v[k] for k in reads)
  rel={a:{inverse[sigs[t]] for t in ts} for a,ts in edges[i].items()}
  require(q not in relations or relations[q]==rel,'Control aliases differ in successors');relations[q]=rel
 for q,rel in relations.items():
  g.edges[q]
  for a,ts in rel.items():
   for t in ts:g.add(q,a,t)
 result={}
 for mode in ('original','experimental','refused_metadata'):
  ss,sg,ee=load(base/mode);mapping={i:inverse[sig] for i,sig in sg.items()};fully=set();certs=[];require(mapping[next(iter(ss))]==g.initial,'Initial mismatch')
  for i in ss:
   actual={a:{mapping[t] for t in ts} for a,ts in ee[i].items()};ref=dict(g.edges[mapping[i]])
   require(bool(actual)==bool(ref),'C0 failed');require(all(ref.get(a)==ts for a,ts in actual.items()),'Changed retained action outcomes')
   if actual==ref:fully.add(i)
   else:
    for a in actual:
     ok,evidence=g.certify(mapping[i],a);require(ok,'Dependency/observation certificate refused: '+str(evidence));certs.append({'state':i,'action':a,'evidence':evidence})
  require(every_cycle_has_full_state(ss,ee,fully),'Strong cycle check failed')
  if mode=='refused_metadata':require(len(fully)==len(ss) and set(mapping.values())==set(g.edges),'Refused metadata omitted behavior')
  result[mode]={'states':len(ss),'projected_states':len(set(sg.values())),'full_vertices':len(fully),'partial_certificates':certs,'strong_cycle_passed':True,'retained_outcomes_match':True,'c0':True}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=audit(a.case);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print('PASS: exact healthy finite graphs, including refused metadata full coverage')
