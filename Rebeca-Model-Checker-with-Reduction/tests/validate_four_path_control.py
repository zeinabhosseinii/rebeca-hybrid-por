#!/usr/bin/env python3
"""Adversarial check on a completed small four-path audit, without native re-runs."""
import argparse,shutil,tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
from benchmark_scaling import MODES,copy_without_por,finite_audit

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,required=True);a=p.parse_args()
case=a.case.resolve();models=list(case.glob('Scale_*.rebeca'))
if len(models)!=1:raise ValueError('Expected one generated model')
with tempfile.TemporaryDirectory() as root:
    root=Path(root);copy=root/'copy';copy.mkdir()
    copy_without_por(case/'dynamic',copy)
    for f in copy.iterdir():
        if f.read_bytes()!=(case/'dynamic_no_por'/f.name).read_bytes():raise ValueError('Recorded native control differs from exact copy')
    bad=root/'bad';bad.mkdir();source=root/'bad_source';source.mkdir()
    for f in (case/'dynamic').iterdir():
        if f.suffix in ('.cpp','.h'):shutil.copyfile(f,source/f.name)
    with (source/'Config.h').open('ab') as out:out.write(b'\n#define PO\n')
    try:copy_without_por(source,bad)
    except ValueError as error:
        if 'exactly one' not in str(error):raise
    else:raise ValueError('Duplicate PO macro accepted')
    corrupted=root/'corrupted';corrupted.mkdir();model=corrupted/models[0].name;shutil.copyfile(models[0],model)
    for mode in MODES:
        dst=corrupted/mode;dst.mkdir()
        for f in (case/mode).iterdir():
            if f.suffix in ('.cpp','.h') or f.name in ('statespace.xml','report-0.xml'):shutil.copyfile(f,dst/f.name)
    path=corrupted/'dynamic_no_por/statespace.xml';tree=ET.parse(path);transition=tree.getroot().find('transition')
    if transition is None:raise ValueError('No branch to test')
    tree.getroot().remove(transition);tree.write(path)
    try:finite_audit(corrupted,model)
    except ValueError as error:
        if 'PO-disabled control omitted' not in str(error) and 'C0 mismatch' not in str(error):raise
    else:raise ValueError('Missing full-control branch was accepted')
print('PASS: exact native copy, duplicate macro rejected, missing full-control branch rejected')
