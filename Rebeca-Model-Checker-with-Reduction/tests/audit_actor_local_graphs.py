#!/usr/bin/env python3
"""Complete finite graph audit for AST-certified actor-local product examples."""
import argparse,collections,json
from pathlib import Path
import xml.etree.ElementTree as ET
from audit_cell_register_graphs import signature
from action_por_reference import Graph,read_full_graph
from audit_both_reductions import every_cycle_has_full_state
from experiment_property_representatives import values
from experiment_ast_property_representatives import evaluate
from compare_model_suite import digest

def need(ok,message):
 if not ok:raise ValueError(message)
def load(d):
 t=ET.parse(d/'statespace.xml').getroot();report=ET.parse(d/'report-0.xml').getroot();need(report.findtext('checked-property/result')=='satisfied','Complete healthy graph required');ss={s.get('id'):s for s in t.findall('state')};need(len(ss)==int(report.findtext('system-info/reached-states')),'Report mismatch');sg={i:signature(s) for i,s in ss.items()};ee=collections.defaultdict(lambda:collections.defaultdict(set))
 for edge in t.findall('transition'):
  need(edge.get('shift')=='0' and edge.get('executionTime')=='0','Timed edge unsupported');a=edge.find('messageserver');ee[edge.get('source')][(a.get('owner'),a.get('title'))].add(edge.get('destination'))
 return ss,sg,ee

def audit(case):
 meta=json.loads((case/'metadata.json').read_text());need(meta['source_sha256']==digest(case/'model.rebeca') and meta['property_sha256']==digest(case/'model.property'),'Metadata/source mismatch');need(meta['metadata_supported'],'Incomplete effects')
 read_full_graph(case/'control/statespace.xml',case/'control/report-0.xml');ss,sg,ee=load(case/'control');inv={sig:i for i,sig in sg.items()};g=Graph();g.initial=inv[sg[next(iter(ss))]];reads=[tuple(k) for k in meta['property_reads']];relations={}
 for i,s in ss.items():
  q=inv[sg[i]];v=values(s);need(evaluate(meta['predicate'],v),'False healthy observation');g.observations[q]=tuple(v[k] for k in reads)
  rel={a:{inv[sg[t]] for t in targets} for a,targets in ee[i].items()};need(q not in relations or relations[q]==rel,'Projected aliases have different outcomes');relations[q]=rel
 for q,rel in relations.items():
  g.edges[q]
  for a,targets in rel.items():
   for t in targets:g.add(q,a,t)
 states,sigs,exported_edges=load(case/'filtered')
 # Export includes executions from rejected trials. Certify the FINAL chosen actor set,
 # and separately validate/count every exported trial edge against the full reference.
 decisions={}
 for line in (case/'filtered/errors-0.log').read_text().splitlines():
  if not line.startswith(('POR_TRIAL ','POR_FULL ')):continue
  fields=dict(word.split('=',1) for word in line.split()[1:] if '=' in word)
  if line.startswith('POR_FULL ') or fields.get('accepted')=='1':
   key=fields['state'];need(key not in decisions,'Duplicate final decision');decisions[key]=None if line.startswith('POR_FULL ') else fields['actor']
 edges={}
 for state in states:
  key=state.split('_')[0];need(key in decisions,'Missing final native decision');chosen=decisions[key]
  edges[state]={a:ts for a,ts in exported_edges[state].items() if chosen is None or a[0]==chosen}
 mp={s:inv[sig] for s,sig in sigs.items()};need(mp[next(iter(states))]==g.initial,'Initial state mismatch');full=set();certificates=[]
 for s in states:
  for a,ts in exported_edges[s].items():need({mp[t] for t in ts}<=g.edges[mp[s]].get(a,set()),'Invalid exported trial edge')
  rel={a:{mp[t] for t in ts} for a,ts in edges[s].items()};original=dict(g.edges[mp[s]])
  need(bool(rel)==bool(original),'C0 mismatch');need(all(original.get(a)==ts for a,ts in rel.items()),'Changed retained outcomes')
  if rel==original:full.add(s)
  else:
   for a in rel:
    ok,evidence=g.certify(mp[s],a);need(ok,str(evidence));certificates.append({'state':s,'action':a,'evidence':evidence})
 need(every_cycle_has_full_state(states,edges,full),'Strong cycle condition failed')
 return {'control_states':len(ss),'filtered_states':len(states),'control_unique_edges':sum(len(ts) for actions in ee.values() for ts in actions.values()),'filtered_exported_unique_edges':sum(len(ts) for actions in exported_edges.values() for ts in actions.values()),'filtered_selected_unique_edges':sum(len(ts) for actions in edges.values() for ts in actions.values()),'full_vertices':len(full),'partial_certificates':certificates,'strong_cycle_passed':True,'retained_outcomes_match':True,'c0':True,'all_control_aliases_checked':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--case',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=audit(a.case);a.output.write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k!='partial_certificates'})
