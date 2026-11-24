#!/usr/bin/env python3
"""Regenerate previously executed programs and compare every native source byte."""
import argparse,json
from pathlib import Path
from run_quiescence_models import ROOT,command
from compare_model_suite import digest

def main():
 p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--shared-reference',type=Path,required=True);p.add_argument('--default-reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);result={'jar_sha256':digest(ROOT/'target/rmc-2.14.jar'),'byte_identical_cases':[]}
 for case in sorted(a.reference.resolve().iterdir()):
  if not (case/'filtered/TimedModelChecker.cpp').exists():continue
  reference=a.shared_reference.resolve()/'filtered' if case.name=='shared_hub_field' else case/'filtered'
  d=out/case.name;command(['java','-jar',ROOT/'target/rmc-2.14.jar','-s',case/'model.rebeca','-p',case/'model.property','--aria','--aria-property-filter','-e','TIMED_REBECA','-v','2.3','-o',d],ROOT,out/(case.name+'.log'))
  files=[f for f in d.iterdir() if f.suffix in ('.cpp','.h')];assert files
  assert {f.name for f in files}=={f.name for f in reference.iterdir() if f.suffix in ('.cpp','.h')}
  assert all(f.read_bytes()==(reference/f.name).read_bytes() for f in files),case.name
  result['byte_identical_cases'].append(case.name)
 model=ROOT/'tests/fixtures/CellRegisterObserved.rebeca';d=out/'default';command(['java','-jar',ROOT/'target/rmc-2.14.jar','-s',model,'-p',model.with_suffix('.property'),'--aria','-e','TIMED_REBECA','-v','2.3','-o',d],ROOT,out/'default.log')
 assert all(f.read_bytes()==(a.default_reference.resolve()/f.name).read_bytes() for f in d.iterdir() if f.suffix in ('.cpp','.h'))
 result['default_generation_byte_identical']=True;result['all_passed']=True;(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS: previous native sources and default generation byte-identical')
if __name__=='__main__':main()
