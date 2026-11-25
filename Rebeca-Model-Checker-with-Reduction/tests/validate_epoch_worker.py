#!/usr/bin/env python3
"""Check the counted worker epoch certificate and audit generated FTTS graphs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from action_por_reference import read_full_graph
from audit_hub_alternatives import export
from audit_online_por import verify
from run_cycle_barriers import compile_run, generate, prepare_full_control
from scaling_models import make_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True)
    for workers in (2, 3):
        case = output / f'independent_{workers}'
        case.mkdir()
        model = case / 'epoch.rebeca'
        model.write_text(make_model('independent', workers))
        dynamic = case / 'dynamic'
        full = case / 'full'
        generate(model, model.stem, 'aria_ast', dynamic)
        prepare_full_control(dynamic, full)
        for name, text in {
            'early_restart': model.read_text().replace(f'done=={workers}', f'done=={workers - 1}'),
            'small_queue': model.read_text().replace(f'Hub({workers + 1})', f'Hub({workers})'),
            'shared': make_model('shared', workers),
        }.items():
            source = case / (name + '.rebeca')
            source.write_text(text)
            generate(source, source.stem, 'aria_ast', case / name)
            checker = (case / name / 'TimedModelChecker.cpp').read_text()
            if 'epoch_worker' in checker:
                raise ValueError(f'{name}: unsafe protocol was certified')
        with ThreadPoolExecutor(max_workers=2) as pool:
            complete, reduced = pool.map(
                lambda folder: compile_run(folder, ['-DEXPORT_STATE_SPACE', '-DPOR_DIAGNOSTICS']),
                (full, dynamic),
            )
        if complete['result'] != 'satisfied' or reduced['result'] != 'satisfied':
            raise ValueError((complete, reduced))
        g = read_full_graph(full / 'statespace.xml', full / 'report.xml')
        _, signatures, _ = export(full)
        _, online, edges = export(dynamic)
        inverse = {signature: state for state, signature in signatures.items()}
        events = []
        for line in (dynamic / 'errors.log').read_text().splitlines():
            if line.startswith('POR_'):
                kind, *fields = line.split()
                events.append(dict(event=kind, **dict(field.split('=', 1) for field in fields if '=' in field)))
        verify(g, {state: inverse[signature] for state, signature in online.items()}, edges, events)
        if not any(e.get('event') == 'POR_TRIAL' and e.get('proof') == 'epoch_worker'
                   and e.get('accepted') == '1' for e in events):
            raise ValueError('Expected an accepted worker epoch choice')
        if reduced['states'] >= complete['states']:
            raise ValueError('Expected fewer states with the epoch certificate')
        print(workers, complete, reduced, flush=True)


if __name__ == '__main__':
    main()
