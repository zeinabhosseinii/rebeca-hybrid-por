#!/usr/bin/env python3
"""Check that an independently live actor cannot conceal a reachable queue overflow."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import xml.etree.ElementTree as ET

from run_cycle_barriers import ROOT, compile_run, export_json, generate, prepare_full_control


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True)
    original = ROOT.parent / 'ARIA/benchmarks/DataAggregation.rebeca'
    source = original.read_text()
    heartbeat = """reactiveclass Heartbeat(2) {
    Heartbeat() { self.Beat(); }
    msgsrv Beat() { self.Beat(); }
}

main {
    Heartbeat pulse():();"""
    if source.count('main {') != 1:
        raise ValueError('Expected exactly one main block')
    model = output / 'DataAggregationNoDeadlock.rebeca'
    model.write_text(source.replace('main {', heartbeat))
    os.environ.update(ARIA_PRUNE='1', ARIA_EXPORT='1')
    export_json(model, model.stem)
    for mode in ('aria_ast', 'aria_json'):
        generate(model, model.stem, mode, output / mode)
    prepare_full_control(output / 'aria_ast', output / 'full')

    def check(mode):
        folder = output / mode
        result = compile_run(folder, ['-DPOR_DIAGNOSTICS'])
        report = ET.parse(folder / 'report.xml').getroot()
        if result['result'] != 'queue overflow' or not report.findall('counter-example-trace/state'):
            raise ValueError((mode, 'Expected queue overflow with a trace', result))
        edge = report.find("counter-example-trace/transition[@destination='queue overflow']")
        action = None if edge is None else edge.find('messageserver')
        if action is None or action.get('title') != 'COLLECT':
            raise ValueError((mode, 'Expected the Collector send to overflow'))
        queue = report.findall(
            f"counter-example-trace/state[@id='{edge.get('source')}']"
            "/rebec[@name='Repository']/queue/message"
        )
        if len(queue) != 3 or any('store' not in (item.text or '').lower() for item in queue):
            raise ValueError((mode, 'Expected a full Repository queue', queue))
        print(mode, result, flush=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(check, ('full', 'aria_ast', 'aria_json')))


if __name__ == '__main__':
    main()
