#!/usr/bin/env python3
"""Finite C0/C1/observation/cycle audit for BOTH static and dynamic LoadBalancer exports."""
from pathlib import Path
import argparse,collections,hashlib,json
from action_por_reference import read_full_graph
from audit_hub_alternatives import export


def every_cycle_has_full_state(states,edges,expanded_fully):
    partial=set(states)-expanded_fully
    adjacency={s:{t for ts in edges.get(s,{}).values() for t in ts if t in partial} for s in partial}
    indegree={s:0 for s in partial}
    for targets in adjacency.values():
        for t in targets:indegree[t]+=1
    queue=collections.deque(s for s,d in indegree.items() if d==0);removed=0
    while queue:
        s=queue.popleft();removed+=1
        for t in adjacency[s]:
            indegree[t]-=1
            if indegree[t]==0:queue.append(t)
    return removed==len(partial)


def audit(full,directory):
    graph=read_full_graph(full/'statespace.xml',full/'report.xml')
    _,fs,_=export(full);inverse={signature:s for s,signature in fs.items()}
    states,signatures,edges=export(directory)
    if any(signature not in inverse for signature in signatures.values()):raise ValueError('Unknown projected state')
    mapping={s:inverse[signature] for s,signature in signatures.items()}
    if mapping[next(iter(states))]!=graph.initial:raise ValueError('Initial states differ')
    expanded_fully=set();certificates=[]
    for s in states:
        projected={a:{mapping[t] for t in ts} for a,ts in edges.get(s,{}).items()}
        original=dict(graph.edges[mapping[s]])
        if bool(original)!=bool(projected):raise ValueError(f'C0 failed at {s}')
        for a,targets in projected.items():
            if original.get(a)!=targets:raise ValueError(f'Changed action outcomes at {s}: {a}')
            ok,evidence=graph.certify(mapping[s],a)
            if not ok:raise ValueError(f'Action not certified at {s}: {a}: {evidence}')
            certificates.append({'state':s,'full_state':mapping[s],'action':a,**evidence})
        if projected==original:expanded_fully.add(s)
    # Every cycle must pass a semantically full expansion, regardless of the
    # implementation's diagnostic reduced/full label. Remove full vertices;
    # the remaining graph must be acyclic. This is a sufficient strong proviso.
    partial=set(states)-expanded_fully
    if not every_cycle_has_full_state(states,edges,expanded_fully):
        raise ValueError('Strong cycle certificate failed; not a proof of an implementation bug')
    return {'states':len(states),'action_certificates':len(certificates),
            'semantically_full_vertices':len(expanded_fully),'partial_vertices':len(partial),
            'cycle_without_full_expansion':False,'certificates':certificates}


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--full',type=Path,default=root/'tmp/LoadBalancerSmall_reference_full')
    p.add_argument('--scheduling',type=Path,default=root/'tmp/LoadBalancerSmall_action_candidate_scheduling')
    p.add_argument('--output',type=Path,default=root/'tmp/LoadBalancerSmall_both_reductions.json')
    a=p.parse_args()
    model=root.parent/'ARIA/benchmarks/LoadBalancerSmall.rebeca'
    digest=hashlib.sha256(model.read_bytes()).hexdigest()
    if digest!='fbd2dbefff81ef86df52c961ba93784f8f5f3ff4bea7a2e9cf9c842ae579108b':raise ValueError('Sender projection is benchmark-specific')
    result={'finite_model_only':True,'source_sha256':digest,'full_graph_required':True,
            'static':audit(a.full,a.scheduling/'static_original'),
            'dynamic':audit(a.full,a.scheduling/'dynamic_original')}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    for mode in ('static','dynamic'):print(mode,{k:v for k,v in result[mode].items() if k!='certificates'})
    print('PASS: both finite reductions satisfy the sufficient semantic and strong-cycle checks; no general generator proof')
