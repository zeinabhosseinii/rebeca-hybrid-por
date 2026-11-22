#!/usr/bin/env python3
"""Finite full-graph reference for action-level persistent sets, not an online RMC.
No static priorities or dependence classes are assumed. Missing/failed semantic
checks cause full expansion. Read ACTION_POR_REFERENCE.md before interpreting counts.
"""
import argparse
from collections import Counter, defaultdict, deque
from pathlib import Path
import json
import hashlib
import re
import xml.etree.ElementTree as ET

class Graph:
    def __init__(self):
        self.edges = defaultdict(lambda: defaultdict(set))
        self.observations = {}
        self.initial = None

    def add(self, source, action, target):
        self.edges[source][action].add(target)
        self.edges[target]

    def certify(self, state, action):
        """Check persistence and relational diamonds over ALL paths avoiding action."""
        pending = [state]
        visited = set()
        while pending:
            v = pending.pop()
            if v in visited:
                continue
            visited.add(v)
            selected = self.edges[v].get(action, set())
            if not selected:
                return False, {'reason': 'selected_disabled', 'state': v}
            if any(self.observations[v] != self.observations[t] for t in selected):
                return False, {'reason': 'property_visible', 'state': v}
            for other, targets in self.edges[v].items():
                if other == action:
                    continue
                # Both orders must remain enabled on EVERY nondeterministic branch.
                if any(not self.edges[t].get(other) for t in selected):
                    return False, {'reason': 'other_disabled', 'state': v, 'other': other}
                if any(not self.edges[t].get(action) for t in targets):
                    return False, {'reason': 'selected_disabled_after_other', 'state': v, 'other': other}
                left = set().union(*(self.edges[t][other] for t in selected))
                right = set().union(*(self.edges[t][action] for t in targets))
                if left != right:
                    return False, {'reason': 'diamond_failed', 'state': v, 'other': other}
                pending.extend(targets)
        return True, {'reason': 'verified', 'avoidance_states': len(visited)}

    def reduce(self):
        opened = {self.initial}
        closed = set()
        pending = deque([self.initial])
        selected_sets = {}
        diagnostics = Counter()
        decisions = []
        while pending:
            state = pending.popleft()
            opened.remove(state)
            chosen = None
            for action in sorted(self.edges[state]):
                certified, evidence = self.certify(state, action)
                decisions.append(dict(state=state, action=action, certified=certified, evidence=evidence))
                if not certified:
                    diagnostics[evidence['reason']] += 1
                    continue
                # Conservative BFS cycle proviso: every successor is new or open.
                # Current state is not Open for this purpose.
                if any(t == state or t in closed for t in self.edges[state][action]):
                    diagnostics['proviso_reject'] += 1
                    decisions[-1]['proviso'] = 'rejected'
                    continue
                decisions[-1]['proviso'] = 'accepted'
                chosen = action
                break
            actions = self.edges[state] if chosen is None else {chosen: self.edges[state][chosen]}
            selected_sets[state] = list(actions)
            diagnostics['full' if chosen is None else 'singleton'] += 1
            closed.add(state)
            for action, targets in actions.items():
                for target in sorted(targets):
                    if target not in closed and target not in opened:
                        opened.add(target)
                        pending.append(target)
        return selected_sets, dict(diagnostics), decisions


def read_full_graph(statespace, report):
    result = ET.parse(report).getroot()
    if result.findtext('checked-property/result') != 'satisfied':
        raise ValueError('Reference requires a completed satisfied run; first-error traces are incomplete')
    if result.findtext('checked-property/type') != 'Reachability':
        raise ValueError('Only reachability observations are supported by this reference')
    config = statespace.parent / 'Config.h'
    initialization = statespace.parent / 'AbstractTimedRebecaAnalyzer.cpp'
    if not config.exists() or not initialization.exists():
        raise ValueError('Generated Config.h and analyzer sources are required to audit the input mode')
    if re.search(r'^\s*#\s*define\s+(?:PO|SYMM)\b', config.read_text(), re.M):
        raise ValueError('Input must be generated without POR or symmetry reduction')
    priorities = re.findall(r'->setPriority\((\d+)\)', initialization.read_text())
    if len(set(priorities)) > 1:
        raise ValueError('Unequal actor priorities are not a full unprioritized reference')
    for actor in statespace.parent.glob('*Actor.cpp'):
        assignments = re.findall(r'messagePriorities\[\d+\]\s*=\s*([^;]+);', actor.read_text())
        if len(set(assignments)) > 1:
            raise ValueError(f'{actor.name}: unequal message priorities are not supported')
    system = ET.parse(statespace).getroot()
    if system.tag != 'transitionsystem':
        raise ValueError('Expected an exported transition system')
    graph = Graph()
    states = system.findall('state')
    if not states:
        raise ValueError('No exported states')
    for state in states:
        sid = state.get('id')
        if sid in graph.observations:
            raise ValueError('Duplicate state IDs')
        graph.edges[sid]
        graph.observations[sid] = state.get('atomicpropositions', '')
    graph.initial = states[0].get('id')
    if int(result.findtext('system-info/reached-states')) != len(states):
        raise ValueError('Export/report state count mismatch (or unsupported time bundles)')
    for edge in system.findall('transition'):
        if edge.get('shift', '0') != '0' or edge.get('executionTime', '0') != '0':
            raise ValueError('This reference supports only zero-time, zero-shift FTTS graphs')
        message = edge.find('messageserver')
        source, target = edge.get('source'), edge.get('destination')
        if message is None or source not in graph.observations or target not in graph.observations:
            raise ValueError('Incomplete or unlabeled exported transition')
        action = (message.get('owner'), message.get('title'))
        if not all(action):
            raise ValueError('Missing action identity')
        graph.add(source, action, target)
    return graph


def run(statespace, report, output):
    graph = read_full_graph(statespace, report)
    selected, counts, decisions = graph.reduce()
    same_actor = []
    for state, actions in selected.items():
        if len(actions) == 1 and sum(a[0] == actions[0][0] for a in graph.edges[state]) > 1:
            same_actor.append(dict(state=state, selected=actions[0]))
    data = dict(reference_only=True, online_generator_changed=False,
                full_graph_sha256=hashlib.sha256(statespace.read_bytes()).hexdigest(),
                full_states=len(graph.edges), reduced_states=len(selected),
                reduced_edges=sum(len(graph.edges[s][a]) for s, actions in selected.items() for a in actions),
                same_actor_choices=same_actor, diagnostics=counts,
                selected_sets=[dict(state=s, actions=a) for s, a in selected.items()],
                decisions=decisions)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({k:v for k,v in data.items() if k not in ('decisions','selected_sets')},indent=2))
    print(f'Reference report: {output}')
    return data

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--statespace', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.statespace.resolve(), args.report.resolve(), args.output.resolve())
