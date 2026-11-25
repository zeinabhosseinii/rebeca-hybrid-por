#!/usr/bin/env python3
"""Explain the first omitted edge on a shortest witness for each missing state."""
import argparse
from collections import deque
import json
from pathlib import Path

from audit_both_reductions import audit
from audit_hub_alternatives import export
from audit_online_por import run as audit_online
from run_cycle_barriers import ROOT


def witnesses(initial, edges):
    paths = {initial: []}
    pending = deque([initial])
    while pending:
        state = pending.popleft()
        for action, targets in sorted(edges.get(state, {}).items()):
            for target in sorted(targets):
                if target not in paths:
                    paths[target] = paths[state] + [(state, action, target)]
                    pending.append(target)
    return paths


def compare(full, static, dynamic, output):
    model = ROOT.parent / 'ARIA/benchmarks/LoadBalancerSmall.rebeca'
    output.mkdir(parents=True, exist_ok=False)
    online = audit_online(full, dynamic, model, output / 'online-audit.json')
    static_audit = audit(full, static)
    full_states, full_signatures, full_edges = export(full)
    full_ids = {signature: state for state, signature in full_signatures.items()}
    initial = next(iter(full_states))
    relations = {'full': full_edges}
    members = {}
    diagnostics = {}
    for name, directory in [('static', static), ('dynamic', dynamic)]:
        _, signatures, edges = export(directory)
        ids = {state: full_ids[signature] for state, signature in signatures.items()}
        members[name] = set(ids.values())
        relations[name] = {}
        for state, full_id in ids.items():
            actions = edges.get(state, {})
            if name == 'dynamic':
                row = online['decisions'][state]
                selected = {tuple(item['action']) for item in row['certificates']}
                if row['outcome'] == 'reduced':
                    actions = {action: actions[action] for action in selected}
            relations[name][full_id] = {
                action: {ids[target] for target in targets} for action, targets in actions.items()
            }
        if name == 'dynamic':
            for line in (directory / 'errors.log').read_text().splitlines():
                if not line.startswith(('POR_BLOCK ', 'POR_PROVISO_REJECT ', 'POR_TRIAL ', 'POR_FULL ')):
                    continue
                fields = dict(word.split('=', 1) for word in line.split()[1:] if '=' in word)
                full_id = ids[fields['state'] + '_0']
                diagnostics.setdefault(full_id, []).append(line)
    paths = {name: witnesses(initial, edges) for name, edges in relations.items()}
    signatures = {
        state: {'observations': full_signatures[state][0], 'actors': [
            {'actor': actor, 'variables': variables, 'ordered_queue': queue, 'now': now}
            for actor, variables, queue, now in full_signatures[state][1]
        ]} for state in full_states
    }
    result = {'reduced_states': {name: len(ids) for name, ids in members.items()},
              'shared_states': sorted(members['static'] & members['dynamic']),
              'static_full_vertices': static_audit['semantically_full_vertices'],
              'dynamic_selected_full_vertices': online['core_full_vertices'],
              'trial_only_dynamic_states': sorted(members['dynamic'] - paths['dynamic'].keys()),
              'states': signatures, 'different_choices_at_shared_states': []}
    for state in result['shared_states']:
        static_edges = relations['static'].get(state, {})
        dynamic_edges = relations['dynamic'].get(state, {})
        if static_edges != dynamic_edges:
            result['different_choices_at_shared_states'].append({
                'state': state, 'full_enabled': sorted(full_edges[state]),
                'static_selected': sorted(static_edges), 'dynamic_selected': sorted(dynamic_edges),
                'shortest_full_path': paths['full'][state], 'dynamic_diagnostics': diagnostics.get(state, [])
            })
    for kept, omitted in [('static', 'dynamic'), ('dynamic', 'static')]:
        rows = []
        for target in sorted(paths[kept].keys() - members[omitted]):
            path = paths[kept][target]
            src, action, dst = next(
                edge for edge in path
                if edge[2] not in relations[omitted].get(edge[0], {}).get(edge[1], set())
            )
            rows.append({'state': target, 'shortest_witness': path,
                         'first_omitted_edge': (src, action, dst),
                         'omitting_path_selected_at_source': sorted(relations[omitted].get(src, {})),
                         'dynamic_diagnostics_at_source': diagnostics.get(src, [])})
        result[kept + '_only'] = rows
    (output / 'state-differences.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('full', 'static', 'dynamic', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.full, args.static, args.dynamic, args.output)
    print({key: len(result[key]) for key in
           ('shared_states', 'dynamic_only', 'static_only', 'different_choices_at_shared_states')})
