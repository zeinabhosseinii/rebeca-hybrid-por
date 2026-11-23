#!/usr/bin/env python3
"""Opt-in generated-C++ property filter experiment; production generator unchanged."""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
from run_quiescence_models import ROOT,command
from benchmark_scaling import copy_without_por
from compare_model_suite import sample,digest
from experiment_ast_property_representatives import derive

SOURCE_SHA='e8e0a20c1af6af94fb02c59ff7ad2f9b33a84dd6b55872ee3b5cb89135a325f6'
ANCHOR='bool candidateIsFull = isPorCandidateFull(candidate, currentTime, highestPriority);'

def patch(source,destination,metadata,model,property_file,force_refusal=False):
 destination.mkdir()
 for f in source.iterdir():
  if f.suffix in ('.cpp','.h'):shutil.copyfile(f,destination/f.name)
 supported=(metadata.get('source_sha256')==digest(model)==SOURCE_SHA and metadata.get('property_sha256')==digest(property_file) and not force_refusal and derive(metadata) is not None)
 init=(destination/'AbstractTimedRebecaAnalyzer.cpp').read_text()
 actors=re.findall(r'(\w+)Actor\*\s+_ref_\w+\s*=\s*new\s+\w+Actor\(maxRebecID\+\+,\s*"([^"]+)"',init)
 if len(actors)!=4 and digest(model)==SOURCE_SHA:raise ValueError('Unexpected actor layout')
 reads,writes=derive(metadata) if supported else (set(),{})
 allowed={};max_id=0
 for cls,name in actors:
  messages={int(mid):label for mid,label in re.findall(r'messageNames\[(\d+)\]\s*=\s*\(char\*\)"([^"]+)"',(destination/(cls+'Actor.cpp')).read_text()) if int(mid)>0}
  for mid,label in messages.items():
   max_id=max(max_id,mid);act=(name,label);allowed[(name,mid)]=supported and act in writes and not(writes[act]&reads)
 if not actors or not max_id:raise ValueError('Missing native identity mapping')
 table=',\n'.join('{'+','.join('true' if allowed.get((name,i),False) else 'false' for i in range(max_id+1))+'}' for cls,name in actors)
 insertion='''
                // EXPERIMENT ONLY: preserve native C1/proviso and reject visible partial candidates.
                static const bool propertyInvisible[%d][%d] = {%s};
                bool propertyCandidateAllowed = candidateIsFull;
                if (!propertyCandidateAllowed) {
                    propertyCandidateAllowed = true;
                    for (size_t pi = 0; pi < candidate.alternatives.size(); ++pi) {
                        int pm = (unsigned char)rebecs[r]->messageQueue[candidate.alternatives[pi]];
                        if (pm <= 0 || pm > %d || !propertyInvisible[r][pm]) propertyCandidateAllowed = false;
                    }
                }
                if (!propertyCandidateAllowed) {
#ifdef POR_DIAGNOSTICS
                    cerr << "POR_PROPERTY_REJECT state=" << current.state->stateID << " actor=" << rebecs[r]->getName() << endl;
#endif
                    continue;
                }
'''%(len(actors),max_id+1,table,max_id)
 cpp=destination/'TimedModelChecker.cpp';text=cpp.read_text()
 if text.count(ANCHOR)!=1:raise ValueError('Candidate insertion point changed')
 cpp.write_text(text.replace(ANCHOR,ANCHOR+insertion))
 changed=[f.name for f in source.iterdir() if f.suffix in ('.cpp','.h') and f.read_bytes()!=(destination/f.name).read_bytes()]
 if changed!=['TimedModelChecker.cpp']:raise ValueError(('Unexpected generated mutations',changed))
 return {'metadata_accepted':supported,'default_partial_permission':False,'changed_files':changed,'actor_order':[name for cls,name in actors],
 'invisible_actions':[[name,mid] for (name,mid),safe in allowed.items() if safe]}

def native_run(directory):
 command(['g++','-std=c++11','-pthread','-O2','-DEXPORT_STATE_SPACE','-DPOR_DIAGNOSTICS',*[p.name for p in sorted(directory.glob('*.cpp'))],'-o','execute'],directory,directory/'compile.log')
 result=sample(directory,0,30);result['native_executable_sha256']=digest(directory/'execute');result['checker_sha256']=digest(directory/'TimedModelChecker.cpp');tree=ET.parse(directory/'report-0.xml').getroot();result['message']=tree.findtext('checked-property/message')
 result['property_rejections']=sum(line.startswith('POR_PROPERTY_REJECT ') for line in (directory/'errors-0.log').read_text().splitlines())
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
 if out.exists():p.error('Choose fresh output')
 out.mkdir(parents=True);classes=out/'classes';classes.mkdir();jar=ROOT/'target/rmc-2.14.jar';model=ROOT/'tests/fixtures/CellRegisterObserved.rebeca'
 command(['javac','-cp',jar,'-d',classes,ROOT/'tests/AssertionObservationAudit.java',ROOT/'tests/PropertyEffectAstAudit.java'],ROOT,out/'compile-ast.log')
 result={'experimental_generated_cpp_only':True,'production_generator_changed':False,'full_graph_required_online':False,'online_dependency_and_proviso_unchanged':True,'source_sha256':digest(model),'rmc_jar_sha256':digest(jar),'metadata_extractor_sha256':digest(ROOT/'tests/PropertyEffectAstAudit.java'),'cases':{}}
 for prop in (model.with_suffix('.property'),ROOT/'tests/fixtures/CellRegisterObservedBounds.property'):
  case=out/prop.stem;case.mkdir();metadata_path=case/'metadata.json'
  command(['java','-cp',str(jar)+os.pathsep+str(classes),'PropertyEffectAstAudit',model,prop,metadata_path],ROOT,case/'ast.log');metadata=json.loads(metadata_path.read_text())
  generated=case/'original';generated.mkdir()
  command(['java','-jar',jar,'-s',model,'-p',prop,'--aria','-e','TIMED_REBECA','-v','2.3','-o',generated],ROOT,generated/'generate.log')
  for name in ('experimental','refused_metadata'):
   info=patch(generated,case/name,metadata,model,prop,name=='refused_metadata');(case/(name+'.patch.json')).write_text(json.dumps(info,indent=2)+'\n')
  control=case/'control';control.mkdir();copy_without_por(generated,control)
  rows={}
  for name in ('control','original','experimental','refused_metadata'):
   r=native_run(case/name);expected='assertion failed' if prop==model.with_suffix('.property') else 'satisfied'
   if r['result']!=expected or expected=='assertion failed' and (r['message']!='NoEarlyStore' or not r['trace_states']):raise ValueError((name,'Native property outcome mismatch',r))
   rows[name]=r;print(prop.stem,name,r['result'],r['states'],r['transitions'],'filtered',r['property_rejections'],flush=True)
  result['cases'][prop.stem]={'metadata':metadata,'patches':{name:json.loads((case/(name+'.patch.json')).read_text()) for name in ('experimental','refused_metadata')},'modes':rows}
  (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
 from audit_online_property_filter import audit
 result['healthy_graph_audit']=audit(out/'CellRegisterObservedBounds')
 result['all_expected_outcomes']=True;(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS: generated-C++ online filter experiment; no production integration',out)
if __name__=='__main__':main()
