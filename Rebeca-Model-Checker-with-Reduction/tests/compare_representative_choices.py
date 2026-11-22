#!/usr/bin/env python3
"""Compare current dynamic and static choices by model state, never by run-local ID.
Offline evidence for this exact benchmark; does not install a runtime policy.
"""
import argparse,collections,hashlib,json
from pathlib import Path
from audit_hub_alternatives import export
from action_por_reference import read_full_graph
from audit_both_reductions import audit

ROOT=Path(__file__).resolve().parents[1]

def run(full,dynamic,static,output):
    model=ROOT.parent/'ARIA/benchmarks/LoadBalancerSmall.rebeca'
    if hashlib.sha256(model.read_bytes()).hexdigest()!='fbd2dbefff81ef86df52c961ba93784f8f5f3ff4bea7a2e9cf9c842ae579108b':
        raise ValueError('Unreviewed sender projection')
    graph=read_full_graph(full/'statespace.xml',full/'report.xml')
    _,fs,_=export(full);inverse={sig:s for s,sig in fs.items()}
    ds,dsg,de=export(dynamic);ss,ssg,se=export(static)
    si={sig:s for s,sig in ssg.items()}
    pending=collections.deque([(next(iter(ds)),[]) ]);seen=set();first=None
    while pending:
        d,path=pending.popleft()
        if d in seen:continue
        seen.add(d)
        s=si.get(dsg[d])
        if s is None:continue
        if set(de.get(d,{}))!=set(se.get(s,{})):
            fid=inverse[dsg[d]]
            certificates=[]
            for action in sorted(se.get(s,{})):
                ok,evidence=graph.certify(fid,action)
                certificates.append({'action':action,'persistent_diamond_check':ok,'evidence':evidence})
            first={'shared_prefix':path,'dynamic_state':d,'static_state':s,'full_state':fid,
                   'enabled_actions':sorted(graph.edges[fid]),'dynamic_actions':sorted(de.get(d,{})),
                   'static_actions':sorted(se.get(s,{})),'static_action_certificates':certificates,
                   'dynamic_diagnostics':[line for line in (dynamic/'errors.log').read_text().splitlines()
                                          if 'state='+d.split('_')[0]+' ' in line]}
            break
        for action,targets in sorted(de.get(d,{}).items()):
            for t in sorted(targets):
                if dsg[t] in si:pending.append((t,path+[action]))
    if first is None:raise ValueError('No common-prefix choice divergence found')
    result={'finite_model_only':True,'runtime_generator_changed':False,
            'dynamic':audit(full,dynamic),'static':audit(full,static),
            'shared_states':len(set(dsg.values())&set(ssg.values())),
            'dynamic_only_states':len(set(dsg.values())-set(ssg.values())),
            'static_only_states':len(set(ssg.values())-set(dsg.values())),
            'first_divergence':first}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('dynamic','static')},indent=2))
    print('PASS: both graphs pass finite semantic/cycle checks; no online selection rule inferred')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--full',type=Path,default=ROOT/'tmp/CycleBarriers/LoadBalancerSmall/full')
    p.add_argument('--dynamic',type=Path,default=ROOT/'tmp/CycleBarriers/LoadBalancerSmall/aria_ast')
    p.add_argument('--static',type=Path,default=ROOT/'tmp/LoadBalancerSmall_action_candidate_scheduling/static_original')
    p.add_argument('--output',type=Path,default=ROOT/'tmp/LoadBalancerSmall_representative_choices.json')
    a=p.parse_args();run(a.full,a.dynamic,a.static,a.output)
