import sys,json,argparse
from pathlib import Path
from experiment_online_property_filter import patch,native_run
from benchmark_scaling import copy_without_por
from run_quiescence_models import ROOT,command
parser=argparse.ArgumentParser(description='Native terminating negative control for the experimental online property filter');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);model=out/'CellObservedTerminates.rebeca';model.write_text((ROOT/'tests/fixtures/CellRegisterObserved.rebeca').read_text().replace('self.keepAlive();',''))
prop=ROOT/'tests/fixtures/CellRegisterObservedBounds.property';original=out/'original';original.mkdir();command(['java','-jar',ROOT/'target/rmc-2.14.jar','-s',model,'-p',prop,'--aria','-e','TIMED_REBECA','-v','2.3','-o',original],ROOT,out/'generate.log')
metadata={};info=patch(original,out/'experimental',metadata,model,prop);assert not info['metadata_accepted']
control=out/'control';control.mkdir();copy_without_por(original,control)
rows={}
for mode in ('control','experimental'):
 r=native_run(out/mode);assert r['result']=='deadlock' and r['trace_states']>0;rows[mode]=r;print(mode,r['result'],r['states'],r['transitions'])
(out/'summary.json').write_text(json.dumps({'source_changed_only_for_terminating_negative_control':True,'patch':info,'modes':rows},indent=2)+'\n')
