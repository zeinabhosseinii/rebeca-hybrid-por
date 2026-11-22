#!/usr/bin/env python3
"""Diagnostic fixed-order sweep on COPIED C++; no change to the production scheduler."""
from pathlib import Path
import shutil,re,subprocess,itertools,os,json,collections,xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[1]
import hashlib
model=root.parent/'ARIA/benchmarks/LoadBalancerSmall.rebeca'
if hashlib.sha256(model.read_bytes()).hexdigest()!='fbd2dbefff81ef86df52c961ba93784f8f5f3ff4bea7a2e9cf9c842ae579108b':raise ValueError('Benchmark-specific order sweep')
src=root/'tmp/LoadBalancerSmall_aria_ast';dst=root/'tmp/ActionOrderSweep';dst.mkdir(exist_ok=True)
for p in src.iterdir():
 if p.suffix in ('.cpp','.h'):shutil.copyfile(p,dst/p.name)
p=dst/'TimedModelChecker.cpp';s=p.read_text();s='#include <cstdlib>\n'+s
old='static const int _por_order[] = {0, 1, 2, 3, 4, 5};'
assert s.count(old)==1
s=s.replace(old,'''static int _por_order[] = {0, 1, 2, 3, 4, 5};
        static bool orderInitialized = false;
        if (!orderInitialized) {
            const char* order = std::getenv("POR_TEST_ORDER");
            if (order) {
                bool seen[6] = {};
                for (int k=0;k<6;k++) {
                    if (!order[k] || order[k]<'0' || order[k]>'5' || seen[order[k]-'0']) std::abort();
                    seen[order[k]-'0']=true; _por_order[k]=order[k]-'0';
                }
                if (order[6]) std::abort();
            }
            orderInitialized = true;
        }''')
p.write_text(s)
with (dst/'compile.log').open('w') as out:
 subprocess.run(['g++','-std=c++11','-pthread','-O2',*[p.name for p in dst.glob('*.cpp')],'-o','execute'],cwd=dst,stderr=out,check=True)
rows=[]
for order in itertools.permutations(range(6)):
 env=dict(os.environ);env['POR_TEST_ORDER']=''.join(map(str,order))
 result=subprocess.run(['./execute'],cwd=dst,env=env,capture_output=True,text=True,timeout=10,check=True)
 r=E.fromstring(result.stdout);status=r.findtext('checked-property/result')
 if status!='satisfied':raise ValueError((order,status))
 rows.append({'order':order,'states':int(r.findtext('system-info/reached-states')),'transitions':int(r.findtext('system-info/reached-transitions'))})
rows.sort(key=lambda r:(r['states'],r['transitions'],r['order']))
(dst/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
print('best',rows[:4]);print('histogram',dict(sorted(collections.Counter(r['states'] for r in rows).items())))
