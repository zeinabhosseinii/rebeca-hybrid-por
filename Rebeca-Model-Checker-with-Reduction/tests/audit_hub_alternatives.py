#!/usr/bin/env python3
"""Model-specific finite-graph audit of Hub choices, not an online reduction rule."""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from action_por_reference import read_full_graph

A = ('Hub', 'RECEIVESECONDARY')
B = ('Hub', 'RECEIVEPRIMARY')


def signature(state):
    """Full exported local state/time/ordered queues, ignoring unused sender only."""
    actors = []
    for r in state.findall('rebec'):
        variables = tuple(sorted((v.get('name'), v.get('type'), v.text) for v in r.findall('statevariables/variable')))
        queue = tuple((tuple(sorted((k, v) for k, v in msg.attrib.items() if k != 'sender')),
                       ''.join(msg.itertext()).strip()) for msg in r.findall('queue/message'))
        actors.append((r.get('name'), variables, queue, r.findtext('now')))
    return state.get('atomicpropositions', ''), tuple(sorted(actors))


def export(directory):
    report = ET.parse(directory / 'report.xml').getroot()
    if report.findtext('checked-property/result') != 'satisfied':
        raise ValueError(f'{directory}: incomplete first-error run')
    system = ET.parse(directory / 'statespace.xml').getroot()
    states = {s.get('id'): s for s in system.findall('state')}
    sigs = {sid: signature(s) for sid, s in states.items()}
    if len(states) != int(report.findtext('system-info/reached-states')):
        raise ValueError('state/report mismatch')
    if len(set(sigs.values())) != len(states):
        raise ValueError('non-unique state signatures after sender projection')
    edges = {}
    for e in system.findall('transition'):
        m = e.find('messageserver')
        if m is None: raise ValueError('unlabeled edge')
        action = (m.get('owner'), m.get('title'))
        edges.setdefault(e.get('source'), {}).setdefault(action, set()).add(e.get('destination'))
    return states, sigs, edges


def avoidance(graph, state, action):
    pending = deque([state]); parents = {state: None}; steps = []
    while pending:
        v = pending.popleft()
        for other, targets in sorted(graph.edges[v].items()):
            if other == action: continue
            for target in sorted(targets):
                steps.append({'source': v, 'action': other, 'target': target})
                if target not in parents:
                    parents[target] = (v, other); pending.append(target)
    return {'states': sorted(parents), 'transitions': steps}


def run(base, scheduling, model, output):
    # Sender projection is justified only for this exact supplied benchmark.
    if hashlib.sha256(model.read_bytes()).hexdigest() != 'fbd2dbefff81ef86df52c961ba93784f8f5f3ff4bea7a2e9cf9c842ae579108b':
        raise ValueError('Audit is restricted to the exact supplied LoadBalancerSmall benchmark')
    text = model.read_text()
    code = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    if re.search(r'\bsender\b', code):
        raise ValueError('sender-sensitive models cannot use this signature projection')
    if 'reactiveclass LoadBalancerHub' not in code:
        raise ValueError('This is a LoadBalancer-specific audit')
    full = base / 'LoadBalancerSmall_reference_full'
    graph = read_full_graph(full / 'statespace.xml', full / 'report.xml')
    full_states, full_sigs, _ = export(full)
    by_signature = {sig: sid for sid, sig in full_sigs.items()}
    dynamic = scheduling / 'dynamic_original'; static = scheduling / 'static_original'
    ds, dsignatures, de = export(dynamic)
    ss, ssignatures, se = export(static)
    # Compare state contents, never equal-looking state IDs from separate runs.
    sets = {name: set(sigs.values()) for name, sigs in [('dynamic', dsignatures), ('static', ssignatures)]}
    if not (sets['dynamic'] | sets['static']).issubset(set(full_sigs.values())):
        raise ValueError('reduced exports contain states absent from the full reference')
    branches = []
    for sid in ds:
        actions = de.get(sid, {})
        if A not in actions or B not in actions: continue
        fid = by_signature[dsignatures[sid]]
        diamonds = {}
        certificates = {}
        for selected, other in ((A, B), (B, A)):
            selected_targets = graph.edges[fid][selected]
            other_targets = graph.edges[fid][other]
            left = set().union(*(graph.edges[t].get(other, set()) for t in selected_targets))
            right = set().union(*(graph.edges[t].get(selected, set()) for t in other_targets))
            diamonds[' then '.join([selected[1], other[1]])] = sorted(left)
            if not left or left != right: raise ValueError('Hub immediate diamond fails')
            ok, evidence = graph.certify(fid, selected)
            certificates[selected[1]] = {'certified': ok, 'evidence': evidence,
                                         'avoidance': avoidance(graph, fid, selected)}
        matching_static = [i for i, sig in ssignatures.items() if sig == dsignatures[sid]]
        branches.append({'dynamic_state': sid, 'full_state': fid,
                         'dynamic_choices': {a[1]: sorted(actions[a]) for a in (A, B)},
                         'same_content_static_states': matching_static,
                         'static_choices': {i: [list(a) for a in se.get(i, {})] for i in matching_static},
                         'diamonds': diamonds, 'certificates': certificates})
    full_hub_branches = []
    for fid in full_states:
        if A not in graph.edges[fid] or B not in graph.edges[fid]: continue
        full_hub_branches.append({'full_state': fid,
            'present_in_dynamic': full_sigs[fid] in sets['dynamic'],
            'present_in_static': full_sigs[fid] in sets['static'],
            'certificates': {a[1]: {'certified': graph.certify(fid, a)[0],
                                   'evidence': graph.certify(fid, a)[1],
                                   'avoidance': avoidance(graph, fid, a)} for a in (A, B)}})
    online_hub_queues = []
    for sid, state in ds.items():
        queue = state.findall("rebec[@name='Hub']/queue/message")
        if len(queue) > 1:
            online_hub_queues.append({'state': sid, 'messages': [m.text for m in queue]})
    initial = next(iter(ds)); static_initial = next(iter(ss))
    # Find first equal-content state with differing exported action sets along common actions.
    q = deque([(initial, static_initial, [])]); seen = set(); divergence = None
    sinverse = {sig: sid for sid, sig in ssignatures.items()}
    while q:
        d, s, path = q.popleft()
        if (d, s) in seen: continue
        seen.add((d, s))
        da, sa = set(de.get(d, {})), set(se.get(s, {}))
        if da != sa:
            divergence = {'dynamic_state': d, 'static_state': s, 'common_prefix': path,
                          'dynamic_actions': sorted(da), 'static_actions': sorted(sa)}
            break
        for action in sorted(da):
            for target in sorted(de[d][action]):
                partner = sinverse.get(dsignatures[target])
                if partner is not None and partner in se[s][action]:
                    q.append((target, partner, path + [action]))
    diagnostics = []
    for line in (dynamic / 'errors.log').read_text().splitlines():
        if line.startswith(('POR_ALTERNATIVE ', 'POR_PROVISO_REJECT ', 'POR_FULL ', 'POR_EQUIVALENT_SKIP ', 'POR_TRIAL ')):
            fields = dict(part.split('=', 1) for part in line.split()[1:] if '=' in part)
            diagnostics.append({'event': line.split()[0], **fields})
    data = {'diagnostic_only': True, 'online_reduction_changed': False,
            'model_sha256': hashlib.sha256(model.read_bytes()).hexdigest(),
            'full_graph_sha256': hashlib.sha256((full / 'statespace.xml').read_bytes()).hexdigest(),
            'full_states': len(full_states), 'dynamic_states': len(ds), 'static_states': len(ss),
            'state_set_comparison': {'shared': len(sets['dynamic'] & sets['static']),
                                     'dynamic_only': len(sets['dynamic'] - sets['static']),
                                     'static_only': len(sets['static'] - sets['dynamic'])},
            'first_policy_divergence': divergence, 'hub_branches': branches,
            'full_hub_branches': full_hub_branches, 'online_multi_message_hub_queues': online_hub_queues,
            'online_execution_diagnostics': diagnostics,
            'policy_controls': json.loads((scheduling / 'summary.json').read_text())}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + '\n')
    md = ['# Hub alternative audit', '', 'Finite-graph diagnostics, not an online certificate.', '',
          '| Experiment | States | Transitions | Result |', '|---|---:|---:|---|']
    for row in data['policy_controls']:
        md.append(f"| {row['experiment']} | {row['states']} | {row['transitions']} | {row['result']} |")
    md += ['', 'State-set comparison: ' + str(data['state_set_comparison']), '',
           'First policy divergence: `' + json.dumps(divergence) + '`', '',
           '| Dynamic state | Full-reference state | Choices | Full-graph persistence tests |', '|---|---|---|---|']
    for b in branches:
        checks = '; '.join(f"{name}: {c['evidence']}" for name, c in b['certificates'].items())
        md.append(f"| {b['dynamic_state']} | {b['full_state']} | both Hub handlers | {checks} |")
    md += ['', f'Distinct online Hub branches: {len(branches)}. Full-graph distinct Hub states: {len(full_hub_branches)}.',
           'Online multi-message Hub queues: `' + json.dumps(online_hub_queues) + '`', '', 'JSON retains both-order diamond destinations and every action-avoiding continuation.',
           'Different schedules and proviso encounters interact; counts are not an additive decomposition.',
           'Matching the offline reference state count does not establish graph equivalence.']
    output.with_suffix('.md').write_text('\n'.join(md) + '\n')
    print(json.dumps({k: data[k] for k in ('dynamic_states','static_states','state_set_comparison','first_policy_divergence')},indent=2))
    print(f'Hub branches audited: {len(branches)}; evidence: {output}')
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument('--base', type=Path, default=root / 'tmp')
    parser.add_argument('--scheduling', type=Path, default=root / 'tmp/LoadBalancerSmall_post_quiescence_scheduling')
    parser.add_argument('--model', type=Path, default=root.parent / 'ARIA/benchmarks/LoadBalancerSmall.rebeca')
    parser.add_argument('--output', type=Path, default=root / 'tmp/LoadBalancerSmall_hub_audit.json')
    args = parser.parse_args()
    run(args.base, args.scheduling, args.model, args.output)
