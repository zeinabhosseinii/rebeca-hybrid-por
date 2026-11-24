#!/usr/bin/env python3
"""Repeated native runs after semantic audits; no diagnostics/export in timed binaries."""
import argparse,json,platform,random,shutil,statistics
from pathlib import Path
from compare_model_suite import digest,sample
from run_quiescence_models import ROOT,command

def main():
 p=argparse.ArgumentParser();p.add_argument('--validation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--repeats',type=int,default=5);a=p.parse_args()
 if a.repeats<3:p.error('At least three repeats')
 valid=a.validation.resolve();evidence=json.loads((valid/'summary.json').read_text());assert evidence['all_passed'];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 names=[n for n in evidence['cases'] if n.startswith('load_period_')];runs={};paths={}
 for name in names:
  row=evidence['cases'][name];assert row['graph_audit']['strong_cycle_passed'] and row['graph_audit']['retained_outcomes_match']
  for mode in ('control','filtered'):
   src=valid/name/mode;d=out/name/mode;d.mkdir(parents=True)
   for f in src.iterdir():
    if f.suffix in ('.cpp','.h'):shutil.copyfile(f,d/f.name)
   command(['g++','-std=c++11','-pthread','-O2',*[f.name for f in sorted(d.glob('*.cpp'))],'-o','execute'],d,d/'compile.log')
   warm=sample(d,0,60);assert (warm['result'],warm['states'],warm['transitions'])==(row['modes'][mode]['result'],row['modes'][mode]['states'],row['modes'][mode]['transitions'])
   paths[(name,mode)]=d;runs[(name,mode)]=[]
 jobs=[(n,m,k) for n,m in paths for k in range(1,a.repeats+1)];random.Random(20261124).shuffle(jobs)
 for name,mode,k in jobs:
  s=sample(paths[(name,mode)],k,60);ref=evidence['cases'][name]['modes'][mode];assert (s['result'],s['states'],s['transitions'])==(ref['result'],ref['states'],ref['transitions']);runs[(name,mode)].append(s)
 result={'all_passed':True,'system':platform.platform(),'repeats':a.repeats,'warmups_per_binary':1,'random_seed':20261124,'diagnostics':False,'export':False,'validation_sha256':digest(valid/'summary.json'),'cases':{}}
 for name in names:
  rows={}
  for mode in ('control','filtered'):
   ss=runs[(name,mode)];wall=[s['native_wall_seconds'] for s in ss];rss=[s['peak_rss_kib'] for s in ss]
   rows[mode]={'states':ss[0]['states'],'transitions':ss[0]['transitions'],'result':ss[0]['result'],'native_executable_sha256':digest(paths[(name,mode)]/'execute'),'wall_seconds':{'median':statistics.median(wall),'min':min(wall),'max':max(wall)},'peak_rss_kib_median':statistics.median(rss),'solver_estimated_bytes':ss[0]['solver_estimated_bytes'],'samples':ss}
  rows['state_reduction_percent']=100*(1-rows['filtered']['states']/rows['control']['states']);result['cases'][name]=rows;print(name,rows['control']['states'],rows['filtered']['states'],rows['state_reduction_percent'],flush=True)
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS: balanced repeated native measurements with exact outcome/count checks')
if __name__=='__main__':main()
