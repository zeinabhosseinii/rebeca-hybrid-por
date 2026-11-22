#!/usr/bin/env python3
"""Probe real exported guard references, then reject corrupt provenance and hashes."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--classpath',required=True)
a=p.parse_args()
model=root.parent/'ARIA/benchmarks/SlotGuard.rebeca'
source=root.parent/'ARIA/output/SlotGuard_pruned/SlotGuard_conditional.json'
data=json.loads(source.read_text())
output=root/'tmp/SlotGuard_cond_guard_audit.json'
def audit(path,destination,ok):
    r=subprocess.run(['java','-cp',a.classpath,'AriaGuardAudit',str(path),str(model),str(destination)],text=True,capture_output=True)
    if (r.returncode==0)!=ok:raise AssertionError(r.stdout+r.stderr)
    return r
print(audit(source,output,True).stdout.strip())
report=json.loads(output.read_text())
assert report['conditionalPairs']==6
assert report['uniqueReferencesPerPairTotal']==48 and report['unknownUnboundGuardProbes']==48
assert all(p['dependencyRetained'] and not p['stabilityProven'] for p in report['pairs'])
assert all(any('sender' in reason for reason in p['exporterUnknowns']) for p in report['pairs'])
assert all(any('FlyTime' in reason for reason in p['exporterUnknowns']) for p in report['pairs'])
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp)
    for kind in ('index','method','source_hash','action','handler'):
        broken=copy.deepcopy(data)
        pair=next(p for p in broken['actionDependencies'] if p['class']=='COND')
        reason=pair['reasons'][0]
        if kind=='index':reason['leftSend']['accessIndex']=99999
        if kind=='method':reason['leftSend']['messageServer']='MissingHandler'
        if kind=='source_hash':broken['sourceSha256']='0'*64
        if kind=='action':reason['leftSend']['instance']='Beta'
        if kind=='handler':reason['leftAccess']['messageServer']='Tick'
        path=tmp/(kind+'.json');path.write_text(json.dumps(broken))
        audit(path,tmp/(kind+'-report.json'),False)
print('PASS: real SlotGuard provenance, 6 retained pairs, 48 UNKNOWN probes; bad references/hash/handler rejected')
