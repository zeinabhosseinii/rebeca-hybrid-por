#!/usr/bin/env python3
"""Audit executed online POR diagnostics, without changing exploration."""
import argparse
import json
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET


def audit(directory):
    report = ET.parse(directory / 'report.xml').getroot()
    states = {}
    for line in (directory / 'errors.log').read_text().splitlines():
        if not line.startswith('POR_'):
            continue
        parts = line.split()
        fields = dict(p.split('=', 1) for p in parts[1:] if '=' in p)
        if 'state' not in fields:
            continue
        row = states.setdefault(fields['state'], {'events': [], 'outcome': None})
        row['events'].append({'event': parts[0], **fields})
        if parts[0] == 'POR_FULL':
            row['outcome'] = 'full'
        if parts[0] == 'POR_TRIAL' and fields['accepted'] == '1':
            row['outcome'] = 'reduced'
    if not states or any(r['outcome'] is None for r in states.values()):
        raise ValueError(f'{directory}: missing/incomplete diagnostics')
    for row in states.values():
        blocked = any(e['event'] == 'POR_BLOCK' for e in row['events'])
        proviso = any(e['event'] == 'POR_PROVISO_REJECT' for e in row['events'])
        row['full_reason'] = (('dependency_and_proviso' if blocked and proviso else
                              'dependency' if blocked else 'proviso' if proviso else
                              'no_accepted_candidate') if row['outcome'] == 'full' else None)
    result = report.findtext('checked-property/result')
    reached = int(report.findtext('system-info/reached-states'))
    if result == 'satisfied' and len(states) != reached:
        raise ValueError(f'{directory}: {len(states)} decisions for {reached} states')
    return {'result': result, 'states_count': reached,
            'transitions': int(report.findtext('system-info/reached-transitions')),
            'summary': dict(Counter(r['outcome'] for r in states.values())),
            'full_reasons': dict(Counter(r['full_reason'] for r in states.values() if r['full_reason'])),
            'states': states}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directories', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, default=Path('tmp/LoadBalancerSmall_decisions.json'))
    args = parser.parse_args()
    data = {d.name: audit(d) for d in args.directories}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + '\n')
    md = ['# Online POR decisions', '', 'State IDs are run-local. All events are preserved in JSON.', '']
    for name, run in data.items():
        print(name, run['result'], run['states_count'], run['transitions'], run['summary'], run['full_reasons'])
        md += [f'## {name}', '', '| State | Outcome | Accepted actor | Dependency blockers | Closed successors |', '|---|---|---|---|---|']
        for sid, row in run['states'].items():
            accepted, blockers, closed = [], [], []
            for e in row['events']:
                if e['event'] == 'POR_BLOCK':
                    blockers.append(f"{e['actor']}:{e['msg']} <- {e['blocker']}:{e['blockerMsg']} (head {e.get('blockerHead', 'unrecorded')})")
                if e['event'] == 'POR_PROVISO_REJECT':
                    closed.append(f"{e['actor']} -> {e['closedSuccessor']}")
                if e['event'] == 'POR_TRIAL' and e['accepted'] == '1':
                    accepted.append(e['actor'])
            md.append(f"| {sid} | {row['outcome']} | {', '.join(accepted)} | {'; '.join(blockers)} | {'; '.join(closed)} |")
    args.output.with_suffix('.md').write_text('\n'.join(md) + '\n')
    print(args.output.resolve())


if __name__ == '__main__':
    main()
