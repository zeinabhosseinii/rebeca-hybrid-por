#!/usr/bin/env python3
"""Check actual online decisions against a completed full graph (finite model only)."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from action_por_reference import read_full_graph
from audit_both_reductions import every_cycle_has_full_state
from audit_hub_alternatives import export
from audit_actor_local_graphs import certify_choices


def verify(graph, mapping, online_edges, events):
    """mapping maps online IDs to full-graph IDs; all nondeterministic targets count."""
    def fail(message):
        raise ValueError(message)
    checked_edges = 0
    for source, actions in online_edges.items():
        for action, targets in actions.items():
            actual = {mapping[t] for t in targets}
            if not actual <= graph.edges[mapping[source]].get(action, set()):
                fail(f'{source}: fabricated transition for {action}')
            checked_edges += len(actual)
    closed = set()
    completed_full = set()
    partial_successors = {}
    acyclic_witnesses = set()
    def reaches(source, destination):
        pending = [source]
        visited = set()
        while pending:
            state = pending.pop()
            if state == destination:
                return True
            if state not in visited:
                visited.add(state)
                pending.extend(partial_successors.get(state, ()))
        return False

    rows = {}
    current = None
    rejected = Counter()
    for event in events:
        kind = event['event']
        if kind == 'POR_STATE':
            source = event['state'] + '_0'
            if source not in mapping or source in rows:
                fail(f'{source}: missing mapping or repeated expansion')
            if current is not None and rows[current]['outcome'] is None:
                fail(f'{current}: no completed online decision')
            if not rows and mapping[source] != graph.initial:
                fail('First expanded state is not the full-graph initial state')
            current = source; closed.add(mapping[source])
            rows[source] = {'outcome': None, 'certificates': [], 'proviso_rejections': []}
        if kind not in ('POR_FULL','POR_TRIAL','POR_PROVISO_REJECT','POR_FULL_BARRIER','POR_PROVISO_WITNESS'):
            continue
        source = event['state'] + '_0'
        if source != current:
            fail(f'{source}: out-of-order event')
        full_source = mapping[source]
        row = rows[source]
        if kind == 'POR_FULL_BARRIER':
            if row['outcome'] not in ('full','full_candidate'):
                fail(f'{source}: premature full barrier')
            actual={a:{mapping[t] for t in ts} for a,ts in online_edges.get(source,{}).items()}
            if actual != dict(graph.edges[full_source]):
                fail(f'{source}: barrier omitted enabled behavior')
            completed_full.add(full_source)
            row['completed_full_barrier']=True
        elif kind == 'POR_PROVISO_WITNESS':
            if event['reason'] != 'acyclic_partial_graph':
                continue
            target = event['target'] + '_0'
            if target not in mapping or mapping[target] not in closed - completed_full:
                fail(f'{source}: acyclic witness target must be closed and partial')
            if not any(action[0] == event['actor'] and target in targets
                       for action, targets in online_edges.get(source, {}).items()):
                fail(f'{source}: acyclic witness is not an exported successor')
            if reaches(mapping[target], full_source):
                fail(f'{source}: accepted back-edge closes a partial-only cycle')
            acyclic_witnesses.add((source, event['actor'], mapping[target]))
        elif kind == 'POR_PROVISO_REJECT':
            target = event['closedSuccessor'] + '_0'
            if target not in mapping or mapping[target] not in closed:
                fail(f'{source}: claimed closed successor is not closed')
            candidates = [a for a in online_edges.get(source, {}) if a[0] == event['actor']]
            if not any(mapping[target] in graph.edges[full_source].get(a,set()) for a in candidates):
                fail(f'{source}: proviso witness is not a successor of this actor')
            rejected[source,event['actor']] += 1
            row['proviso_rejections'].append(event)
        elif kind == 'POR_TRIAL':
            if event['accepted'] == '0':
                if not rejected[source,event['actor']]:
                    fail(f'{source}: rejected trial has no closed-successor witness')
                continue
            if event['accepted'] != '1' or row['outcome'] is not None:
                fail(f'{source}: invalid/repeated accepted trial')
            # Actor-set trial must retain every distinct handler of that actor.
            actions = [a for a in graph.edges[full_source] if a[0] == event['actor']]
            exhaustive = event.get('exhaustive') == '1'
            if not actions:
                fail(f'{source}: accepted trial has no enabled action')
            if exhaustive:
                if set(graph.edges[full_source]) != set(actions):
                    fail(f'{source}: false exhaustive declaration')
            union_certificate = None
            if not exhaustive and len(actions) > 1:
                union_certificate = certify_choices(graph, full_source, set(actions))
            for action in actions:
                if exhaustive:
                    ok, evidence = True, {'reason':'exhaustive_enabled_set'}
                elif union_certificate is not None:
                    ok, evidence = union_certificate
                else:
                    ok, evidence = graph.certify(full_source, action)
                if not ok:
                    fail(f'{source}: persistence/diamond certificate failed: {evidence}')
                full_targets = graph.edges[full_source][action]
                actual = {mapping[t] for t in online_edges.get(source, {}).get(action, set())}
                if not full_targets <= actual:
                    fail(f'{source}: selected action lost a nondeterministic successor')
                if not exhaustive:
                    closed_partial = full_targets & (closed - completed_full)
                    if any((source, event['actor'], target) not in acyclic_witnesses
                           for target in closed_partial):
                        fail(f'{source}: accepted trial violates closed-successor proviso')
                    partial_successors.setdefault(full_source, set()).update(full_targets)
                row['certificates'].append({'action': action, 'full_state': full_source, **evidence})
            row['outcome'] = 'full_candidate' if exhaustive else 'reduced'
        else:
            if row['outcome'] is not None:
                fail(f'{source}: full fallback follows an accepted trial')
            for action, targets in graph.edges[full_source].items():
                actual = {mapping[t] for t in online_edges.get(source, {}).get(action, set())}
                if not targets <= actual:
                    fail(f'{source}: full expansion lost an enabled action/branch')
            row['outcome'] = 'full'
    if set(rows) != set(mapping) or any(r['outcome'] is None for r in rows.values()):
        fail('Missing/incomplete state decisions')
    core={}
    full_vertices=set()
    for s,row in rows.items():
        if row['outcome'] in ('full','full_candidate'):
            core[s]=online_edges.get(s,{})
        else:
            actions=[tuple(c['action']) for c in row['certificates']]
            core[s]={a:online_edges[s][a] for a in actions}
        projected={a:{mapping[t] for t in targets} for a,targets in core[s].items()}
        if projected==dict(graph.edges[mapping[s]]):full_vertices.add(s)
    if not every_cycle_has_full_state(set(rows),core,full_vertices):
        fail('Selected core has a cycle without full expansion')
    return {'checked_states': len(rows), 'checked_exported_edges': checked_edges,
            'core_full_vertices':len(full_vertices),'core_cycle_without_full_expansion':False,
            'outcomes': dict(Counter(r['outcome'] for r in rows.values())),
            'verified_proviso_rejections': sum(rejected.values()),
            'verified_acyclic_witnesses': len(acyclic_witnesses), 'decisions': rows}


def run(full, online, model, output):
    if hashlib.sha256(model.read_bytes()).hexdigest() not in {
        'fbd2dbefff81ef86df52c961ba93784f8f5f3ff4bea7a2e9cf9c842ae579108b',
        'afdfc935b09c8ec0e1643cdcecd6bb6776d46a2774851939b1ebf1ffeeaf7513',
        '0cb73200e664c4632dc12b36d1d66293744e17d4076d5ab94f22c5ff3c2593d3',
        '46f2c9b1fc316d5b85f842fae7d5bfdb1495ed9e082a4760de4e02190bb83774'}:
        raise ValueError('Sender projection is restricted to reviewed fixtures')
    graph = read_full_graph(full/'statespace.xml', full/'report.xml')
    _, fs, _ = export(full)
    inverse = {sig: sid for sid, sig in fs.items()}
    _, online_sigs, edges = export(online)
    if any(sig not in inverse for sig in online_sigs.values()):
        raise ValueError('Online state absent from full graph')
    if any(not sid.endswith('_0') for sid in online_sigs):
        raise ValueError('Only single zero-time bundles are supported')
    mapping = {sid: inverse[sig] for sid, sig in online_sigs.items()}
    events=[]
    for line in (online/'errors.log').read_text().splitlines():
        if line.startswith('POR_'):
            parts=line.split();fields=dict(p.split('=',1) for p in parts[1:] if '=' in p)
            events.append({'event':parts[0],**fields})
    result=verify(graph,mapping,edges,events)
    result.update(finite_model_only=True, full_graph_required=True, online_reduction_changed=False,
                  model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
                  full_graph_sha256=hashlib.sha256((full/'statespace.xml').read_bytes()).hexdigest(),
                  online_graph_sha256=hashlib.sha256((online/'statespace.xml').read_bytes()).hexdigest(),
                  trace_sha256=hashlib.sha256((online/'errors.log').read_bytes()).hexdigest())
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='decisions'},indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    root=Path(__file__).resolve().parents[1]
    p.add_argument('--full',type=Path,default=root/'tmp/LoadBalancerSmall_reference_full')
    p.add_argument('--online',type=Path,default=root/'tmp/LoadBalancerSmall_post_quiescence_scheduling/dynamic_original')
    p.add_argument('--model',type=Path,default=root.parent/'ARIA/benchmarks/LoadBalancerSmall.rebeca')
    p.add_argument('--output',type=Path,default=root/'tmp/LoadBalancerSmall_online_certificate.json')
    a=p.parse_args();run(a.full,a.online,a.model,a.output)
