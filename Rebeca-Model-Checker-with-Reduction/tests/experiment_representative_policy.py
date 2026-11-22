#!/usr/bin/env python3
"""Preference-only experiments on copied native sources, with semantic audits.
No generated priorities, dependency checks or proviso conditions are changed.
"""
import json,re,shutil,sys
from pathlib import Path
import xml.etree.ElementTree as ET
from run_cycle_barriers import ROOT,compile_run
from audit_online_por import run as semantic_audit

OUT=ROOT/'tmp/RepresentativePolicy'

def prepare(src,dst,policy):
    dst.mkdir(parents=True,exist_ok=True)
    for old in dst.iterdir():
        if old.suffix in ('.cpp','.h'):old.unlink()
    for f in src.iterdir():
        if f.suffix in ('.cpp','.h'):shutil.copyfile(f,dst/f.name)
    p=dst/'TimedModelChecker.cpp';s=p.read_text()
    match=re.search(r'static const int _por_order\[\] = \{([^}]+)\};',s)
    if not match:raise ValueError('Expected configured preference order')
    order=[int(x.strip()) for x in match[1].split(',')]
    if sorted(order)!=list(range(len(order))):raise ValueError('Not a permutation')
    if policy=='reverse':order.reverse()
    elif policy=='static_actor_preference':
        # Benchmark-specific controlled experiment. These are iteration ranks,
        # never actor/message priorities or an independence certificate.
        if len(order)!=6:raise ValueError('Six-actor benchmark required')
        order=[3,4,1,2,0,5]
    elif policy!='original':raise ValueError(policy)
    replacement='static const int _por_order[] = {'+', '.join(map(str,order))+'};'
    modified=s[:match.start()]+replacement+s[match.end():]
    # The only permitted native mutation is this order declaration.
    if modified.replace(replacement,match[0],1)!=s:raise ValueError('Unexpected mutation')
    p.write_text(modified)
    return order

def main():
    results={}
    cases=[('LoadBalancerSmall',ROOT.parent/'ARIA/benchmarks/LoadBalancerSmall.rebeca'),
           ('QuiescenceResend',ROOT/'tests/fixtures/QuiescenceResend.rebeca')]
    for name,model in cases:
        base=ROOT/'tmp/CycleBarriers'/name;results[name]={}
        for policy in ('original','static_actor_preference','reverse'):
            d=OUT/name/policy;order=prepare(base/'aria_ast',d,policy)
            report=compile_run(d,['-DPOR_DIAGNOSTICS','-DEXPORT_STATE_SPACE'])
            if report['result']!='satisfied':raise ValueError((name,policy,report))
            audit=semantic_audit(base/'full',d,model,d/'semantic.json')
            results[name][policy]={**report,'order':order,'semantic_audit':'passed',
                                    'core_full_vertices':audit['core_full_vertices']}
            print(name,policy,results[name][policy],flush=True)
    # Change the preference on first-error cases as well; do not export an
    # incomplete first-error run as if it were a complete reachable graph.
    for name,expected in [('CyclePendingAssertion','assertion failed'),
                          ('QuiescenceTerminates','deadlock'),('QuiescenceAssertion','assertion failed')]:
        parent='CycleBarriers' if name=='CyclePendingAssertion' else 'QuiescenceModels'
        src=ROOT/'tmp'/parent/name/'aria_ast'
        if not src.exists():src=ROOT/'tmp'/parent/(name+'_aria_ast')
        d=OUT/name/'reverse';order=prepare(src,d,'reverse')
        report=compile_run(d,['-DPOR_DIAGNOSTICS'])
        trace=ET.parse(d/'report.xml').getroot().findall('counter-example-trace/state')
        if report['result']!=expected or not trace:raise ValueError(('First error hidden',name,report))
        # Another order may expose the assertion before the loop closes.
        # Record coverage rather than requiring that traversal to close a loop.
        results[name]={'reverse':{**report,'trace_states':len(trace),'order':order,
                                   'proviso_rejection_exercised':'POR_PROVISO_REJECT' in (d/'errors.log').read_text()}}
        print(name,results[name],flush=True)
    (OUT/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
    print('PASS: preference-only mutations, positive semantic/cycle audits, first-error stopping')

if __name__=='__main__':main()
