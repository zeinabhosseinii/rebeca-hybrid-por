#!/usr/bin/env python3
"""Finite sufficient persistent-set/cycle checks; refusals are NOT implementation bugs."""
import argparse,json,collections
from pathlib import Path
from audit_cell_register_graphs import audit,graph,quotient,signature,sha
from audit_both_reductions import every_cycle_has_full_state

def certify(edges,start,chosen):
 pending=[start];seen=set()
 while pending:
  v=pending.pop()
  if v in seen:continue
  seen.add(v)
  if any(not edges[v].get(a) for a in chosen):return False,{'reason':'chosen_disabled','state':v}
  for other,targets in edges[v].items():
   if other in chosen:continue
   for act in chosen:
    selected=edges[v][act]
    if any(not edges[t].get(other) for t in selected) or any(not edges[t].get(act) for t in targets):return False,{'reason':'disabled_in_commutation','state':v,'selected':act,'other':other}
    left=set().union(*(edges[t][other] for t in selected));right=set().union(*(edges[t][act] for t in targets))
    if left!=right:return False,{'reason':'relational_diamond_failed','state':v,'selected':act,'other':other,'selected_then_other':sorted(left),'other_then_selected':sorted(right)}
   pending.extend(targets)
 return True,{'reason':'verified','avoidance_states':len(seen)}

def run(case):
 equivalence=audit(case) # pins exact assertion-bearing healthy model and validates full/control aliases
 states,edges=graph(case/'full');fs,relations=quotient(states,edges);inv={sig:i for i,sig in fs.items()}
 full={inv[sig]:{a:{inv[t] for t in ts} for a,ts in rel.items()} for sig,rel in relations.items()}
 result={'finite_exact_healthy_model_only':True,'source_sha256':equivalence['source_sha256'],
  'full_control_equivalence_rechecked':True,'sufficient_test_only':True,
  'assertion_scope':'All reachable full states satisfy 0 <= Cell.value <= 2; this checks only the exact stored-value safety property, not arbitrary properties.', 'modes':{}}
 for x in states.values():
  values=[int(v.text) for v in x.findall('rebec/statevariables/variable') if v.get('name')=='Cell.value']
  if len(values)!=1 or not 0<=values[0]<=2:raise ValueError('Healthy full graph violates safety observation')
 for mode in ('static','dynamic'):
  ss,ee=graph(case/mode);mapping={i:inv[signature(x)] for i,x in ss.items()};fully=set();records=[];c0=True;outcomes=True
  if mapping[next(iter(ss))]!=inv[fs[next(iter(states))]]:raise ValueError('Initial mismatch')
  for i in ss:
   actual={a:{mapping[t] for t in ts} for a,ts in ee[i].items()};original=full[mapping[i]]
   c0 &= bool(actual)==bool(original)
   outcomes &= all(original.get(a)==targets for a,targets in actual.items())
   if actual==original:fully.add(i);continue
   ok,evidence=certify(full,mapping[i],set(actual))
   records.append({'state':i,'full_state':mapping[i],'selected':sorted(actual),'certified':ok,'evidence':evidence})
  cycle=every_cycle_has_full_state(ss,ee,fully)
  result['modes'][mode]={'raw_states':len(ss),'c0':c0,'retained_action_outcomes_match':outcomes,'semantically_full_raw_states':len(fully),
   'strong_cycle_passed':cycle,'partial_choices':records,'sufficient_certificate_passed':c0 and outcomes and cycle and all(r['certified'] for r in records),
   'interpretation':'A rejected sufficient certificate is inconclusive about general correctness; do not call it a proved defect.'}
 result['witness_full_states']={i:str(fs[i]) for d in result['modes'].values() for r in d['partial_choices'] if not r['certified'] for i in [r['evidence']['state']]}
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=run(a.case);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
 for m,d in r['modes'].items():print(m,{k:v for k,v in d.items() if k not in ('partial_choices','interpretation')})
 if not r['modes']['dynamic']['sufficient_certificate_passed']:raise SystemExit('Dynamic certificate failed: inspect evidence')
 print('Dynamic finite certificate passed; static status recorded without forcing success')
if __name__=='__main__':main()
