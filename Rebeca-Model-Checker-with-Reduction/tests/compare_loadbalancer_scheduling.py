#!/usr/bin/env python3
"""Controlled schedule-policy experiments on already generated LoadBalancer C++.
Diagnostic only: does not edit the generator or assert that priority pruning is sound.
"""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]

def replace_one(path, pattern, replacement):
    text,count=re.subn(pattern,replacement,path.read_text(),flags=re.M)
    if count!=1:raise ValueError(f'{path}: expected one replacement, got {count}')
    path.write_text(text)

def prepare(base, output, name, source):
    dst=output/name;dst.mkdir(parents=True,exist_ok=True)
    src=base/('LoadBalancerSmall_'+source)
    for old in dst.iterdir():
        if old.suffix in ('.cpp','.h'):old.unlink()
    for item in src.iterdir():
        if item.suffix in ('.cpp','.h'):shutil.copyfile(item,dst/item.name)
    if not (dst/'TimedModelChecker.cpp').exists():raise ValueError(f'Generated sources missing: {src}')
    if name=='dynamic_priority_order':
        replace_one(dst/'TimedModelChecker.cpp',r'_por_order\[\]\s*=\s*\{[^}]*\}',
                    '_por_order[] = {3, 4, 1, 2, 0, 5}')
    elif name=='static_actor_only':
        replace_one(dst/'LoadBalancerHubActor.cpp',r'messagePriorities\[2\] = [^;]+;', 'messagePriorities[2] = 1;')
    elif name=='static_method_only':
        path=dst/'AbstractTimedRebecaAnalyzer.cpp'
        text,count=re.subn(r'->setPriority\(\d+\)','->setPriority(0)',path.read_text())
        if count!=6:raise ValueError('Expected exactly six actor priority assignments')
        path.write_text(text)
    elif name=='dynamic_method_priorities':
        for msg in (1,2):
            replace_one(dst/'LoadBalancerHubActor.cpp',rf'messagePriorities\[{msg}\] = [^;]+;',
                        f'messagePriorities[{msg}] = {msg};')
    return dst

def run(base, output):
    configs=[('dynamic_original','aria_ast'),('static_original','static'),
             ('dynamic_priority_order','aria_ast'),('static_actor_only','static'),
             ('static_method_only','static'),('dynamic_method_priorities','aria_ast')]
    rows=[]
    for name,source in configs:
        dst=prepare(base,output,name,source)
        with (dst/'compile.log').open('w') as log:
            subprocess.run(['g++','-std=c++11','-pthread','-O2','-DPOR_DIAGNOSTICS','-DEXPORT_STATE_SPACE',
                            *[p.name for p in sorted(dst.glob('*.cpp'))],'-o','execute'],cwd=dst,stderr=log,check=True,timeout=120)
        with (dst/'report.xml').open('w') as out,(dst/'errors.log').open('w') as err:
            subprocess.run(['./execute'],cwd=dst,stdout=out,stderr=err,check=True,timeout=60)
        xml=ET.parse(dst/'report.xml').getroot()
        row=dict(experiment=name,states=int(xml.findtext('system-info/reached-states')),
                 transitions=int(xml.findtext('system-info/reached-transitions')),
                 result=xml.findtext('checked-property/result'))
        rows.append(row)
        print(row,flush=True)
    import json
    (output/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('Diagnostic schedules only; satisfied outcomes do not prove general POR correctness.')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',type=Path,default=ROOT/'tmp')
    parser.add_argument('--output',type=Path,default=ROOT/'tmp/LoadBalancerSmall_scheduling')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    run(args.base.resolve(),args.output.resolve())
