#!/usr/bin/env python3
"""Audit case4's same-actor ENABLE/FINISH dependency against full exploration."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path

from audit_online_por import run as audit_online
from run_cycle_barriers import ROOT, compile_run, export_json, generate, prepare_full_control


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True)
    model = ROOT.parent / 'ARIA/benchmarks/case4.rebeca'
    os.environ.update(ARIA_PRUNE='1', ARIA_EXPORT='1')
    export_json(model, model.stem)

    modes = ('aria_ast', 'aria_json')
    for mode in modes:
        generate(model, model.stem, mode, output / mode)
    prepare_full_control(output / 'aria_ast', output / 'full')
    with ThreadPoolExecutor(max_workers=2) as pool:
        def execute(mode):
            flags = ['-DEXPORT_STATE_SPACE']
            if mode != 'full':
                flags.append('-DPOR_DIAGNOSTICS')
            report = compile_run(output / mode, flags)
            if report['result'] != 'satisfied':
                raise ValueError((mode, report))
            print(mode, report, flush=True)

        list(pool.map(execute, ('full', *modes)))

    for mode in modes:
        audit = audit_online(output / 'full', output / mode, model, output / (mode + '.json'))
        if not audit['outcomes'].get('reduced'):
            raise ValueError(f'{mode}: dependency regression must still exercise reduction')


if __name__ == '__main__':
    main()
