#!/usr/bin/env python3
"""Audit the actual generated C++ matrices, without modifying model-checker behavior."""
from pathlib import Path
import argparse
import csv
import itertools
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def read_run(directory):
    sources = {p.name: p.read_text() for p in directory.glob('*.cpp')}
    combined = '\n'.join(sources.values())
    declaration = re.search(r'sdiPairs\s*\[REBEC_COUNT\]\[(\d+)\]\[REBEC_COUNT\]\[\1\]\s*=\s*\{(.*?)\};', combined, re.S)
    if not declaration:
        raise ValueError(f'{directory}: generated sdiPairs initializer not found')
    width = int(declaration[1])
    values = [x == 'true' for x in re.findall(r'\b(?:true|false)\b', declaration[2])]
    actors = re.findall(r'new\s+(\w+)Actor\s*\(\s*maxRebecID\+\+\s*,\s*"([^"]+)"', combined)
    if not actors or len(values) != len(actors)**2 * width**2:
        raise ValueError(f'{directory}: matrix size or actor inventory mismatch ({len(values)}, {len(actors)}, {width})')
    labels = {}
    for actor_id, (cls, instance) in enumerate(actors):
        code = sources.get(cls + 'Actor.cpp', '')
        ids = dict(re.findall(r'^\s*#define\s+(\w+)\s+(\d+)\s*$', code, re.M))
        for method, msg_id in ids.items():
            msg_id = int(msg_id)
            if 0 < msg_id < width:
                labels[(actor_id, msg_id)] = instance + '.' + method
    matrix = dict(zip(itertools.product(range(len(actors)), range(width), range(len(actors)), range(width)), values))
    start = combined.find('bool TimedModelChecker::areActiveActionsSafe')
    end = combined.find('void TimedModelChecker::printCounterExampleTransition', start)
    safety = combined[start:end]
    order = re.search(r'_por_order\[\]\s*=\s*\{([^}]+)\}', combined)
    order_ids = [int(x) for x in re.findall(r'\d+', order[1])] if order else list(range(len(actors)))
    report = ET.parse(directory/'report.xml').getroot()
    return dict(matrix=matrix, actors=actors, labels=labels, width=width, safety=safety,
                order=[actors[i][1] for i in order_ids],
                result=report.findtext('checked-property/result'),
                states=report.findtext('system-info/reached-states'),
                transitions=report.findtext('system-info/reached-transitions'))

def audit(base):
    runs={name:read_run(base/('LoadBalancerSmall_'+name)) for name in ('aria_ast','aria_json')}
    outdir=base/'LoadBalancerSmall_audit';outdir.mkdir(exist_ok=True)
    for name,r in runs.items():
        print(f"{name}: {r['result']}, states={r['states']}, transitions={r['transitions']}, order={r['order']}")
        print(f"  global-ID-check={'jMsgId <' in r['safety']}; queue-head-check={'rebecs[j]->messageQueue[0]' in r['safety']}")
        (outdir/(name+'_safety.cpp.txt')).write_text(r['safety'])
        with (outdir/(name+'_matrix.csv')).open('w') as f:
            writer=csv.writer(f);writer.writerow(['left','right','dependent','left_valid','right_valid'])
            for (i,mi,j,mj),value in r['matrix'].items():
                if not mi or not mj or i==j:continue
                left=r['labels'].get((i,mi),r['actors'][i][1]+f'.UNUSED_{mi}')
                right=r['labels'].get((j,mj),r['actors'][j][1]+f'.UNUSED_{mj}')
                writer.writerow([left,right,value,(i,mi) in r['labels'],(j,mj) in r['labels']])
        for action,label in sorted(r['labels'].items()):
            i,mi=action
            valid=[];unused=[]
            for j,(_,inst) in enumerate(r['actors']):
                if i==j:continue
                for mj in range(1,r['width']):
                    if r['matrix'][i,mi,j,mj]:
                        name2=r['labels'].get((j,mj))
                        (valid if name2 else unused).append(name2 or inst+f'.UNUSED_{mj}')
            print(f'  {label}: real blockers={valid}; unused-ID blockers={unused}')
    a,b=runs.values()
    if a['actors']!=b['actors'] or a['width']!=b['width']:
        raise ValueError('Runs use different actor inventory or matrix dimensions')
    print('Matrix differences (AST -> JSON):')
    for key,av in a['matrix'].items():
        bv=b['matrix'][key];i,mi,j,mj=key
        if av!=bv and mi and mj and i<j:
            left=a['labels'].get((i,mi),a['actors'][i][1]+f'.UNUSED_{mi}')
            right=a['labels'].get((j,mj),a['actors'][j][1]+f'.UNUSED_{mj}')
            print(f'  {left} <-> {right}: {av} -> {bv}')
    static=base/'LoadBalancerSmall_static'/'AbstractTimedRebecaAnalyzer.cpp'
    if static.exists():
        lines=static.read_text().splitlines()
        print('Static-priority initialization (generated C++):')
        for i,line in enumerate(lines):
            if 'new ' in line and 'Actor(' in line or 'setPriority(' in line:
                print('\n'.join(lines[max(0,i-1):i+4]))
    print(f'Audit files: {outdir}')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',type=Path,default=ROOT/'tmp')
    audit(parser.parse_args().base)
