#!/usr/bin/env python3
"""Native four-mode assertion controls; no change to the production reducer."""
import argparse,json,os,platform,re
from pathlib import Path
import xml.etree.ElementTree as ET
from scaling_models import make_model
from benchmark_scaling import MODES,copy_without_por
from compare_model_suite import body,digest
from run_quiescence_models import ROOT,command
from run_cycle_barriers import compile_run

def property_model(fault=False):
    text=make_model('shared',2)
    lines=[]
    for line in text.splitlines():
        assertion=None
        if line.startswith(' msgsrv Tick()'):assertion='assertion(cycle >= 0 && cycle < 3);'
        if line.startswith(' msgsrv Step'):assertion='assertion(count >= 0 && count < 3);'
        if line.startswith(' msgsrv Finish'):assertion='assertion(done >= 0 && done < 2);'
        if assertion:
            prefix,end=line.rsplit(' }',1);line=prefix+' '+assertion+' }'+end
        lines.append(line)
    result='\n'.join(lines)+'\n'
    if fault:
        start=result.index('reactiveclass Worker1(');end=result.index('reactiveclass Hub(',start)
        segment=result[start:end]
        if segment.count('cycle=cycle+1;')!=1:raise ValueError('Unexpected model structure')
        result=result[:start]+segment.replace('cycle=cycle+1;','cycle=cycle+1; assertion(cycle != 2);')+result[end:]
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--export-healthy',action='store_true');a=p.parse_args()
    out=a.output.resolve()
    if out.exists():p.error('Choose a fresh output directory')
    out.mkdir(parents=True);os.environ['ARIA_PRUNE']='1';os.environ['ARIA_EXPORT']='1'
    summary={'platform':platform.platform(),'rmc_jar_sha256':digest(ROOT/'target/rmc-2.14.jar'),
             'aria_jar_sha256':digest(ROOT.parent/'ARIA/target/erdg-tool-0.1.0.jar'),'diagnostic_only':True,'timings_not_benchmarked':True,'cases':{}}
    def save():(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    try:
        for name,fault,expected in [('ScalePropertyHealthy',False,'satisfied'),('ScalePropertyFault',True,'assertion failed')]:
            case=out/name;case.mkdir();model=case/(name+'.rebeca');model.write_text(property_model(fault))
            export=ROOT.parent/'ARIA/output'/(name+'_pruned');annotated=export/(name+'_annotated.rebeca');annotated.unlink(missing_ok=True)
            command(['java','-jar',ROOT.parent/'ARIA/target/erdg-tool-0.1.0.jar','file',model],ROOT.parent/'ARIA',case/'aria.log')
            if not annotated.exists() or body(annotated.read_text())!=body(model.read_text()):raise ValueError('Annotated assertion bodies differ')
            (case/'annotated.rebeca').write_bytes(annotated.read_bytes())
            summary['cases'][name]={'expected':expected,'source_sha256':digest(model),'modes':{}};save()
            for mode in MODES:
                d=case/mode;d.mkdir()
                if mode=='dynamic_no_por':copy_without_por(case/'dynamic',d)
                else:
                    args=['java','-jar',ROOT/'target/rmc-2.14.jar','-s',annotated if mode=='static' else model,'-e','TIMED_REBECA','-v','2.3','-o',d]
                    if mode=='dynamic':args+=['--aria']
                    command(args,ROOT,d/'generate.log')
                report=compile_run(d,['-DPOR_DIAGNOSTICS']+(['-DEXPORT_STATE_SPACE'] if a.export_healthy and not fault else []))
                xml=ET.parse(d/'report.xml').getroot();trace=len(xml.findall('counter-example-trace/state'))
                if report['result']!=expected or (fault and trace==0):raise ValueError(('Unexpected result or missing error trace',name,mode,report,trace))
                match=re.search(r'return (true|false) && _porResultState->porFullExpanded;', (d/'TimedModelChecker.cpp').read_text())
                log=(d/'errors.log').read_text()
                if fault:
                    message=xml.findtext('checked-property/message')
                    # Detection is evidenced by the actual error report/trace,
                    # not an invented count target or resumed complete search.
                    if not message:raise ValueError('Missing assertion diagnostic')
                    failures=[e for e in xml.findall('counter-example-trace/transition') if e.get('destination')=='assertion failed']
                    if not any(e.find('messageserver') is not None and e.find('messageserver').get('owner')=='W1' and e.find('messageserver').get('title')=='TICK' for e in failures):
                        raise ValueError('Trace does not identify injected W1.Tick fault')
                result={**report,'trace_states':trace,'complete_space':expected=='satisfied',
                        'generated_closed_barrier_gate':match[1]=='true' if match else None,
                        'full_barrier_events':sum(l.startswith('POR_FULL_BARRIER ') for l in log.splitlines())}
                if fault:result['injected_fault_edge_verified']={'actor':'W1','action':'TICK'}
                summary['cases'][name]['modes'][mode]=result;save();print(name,mode,result,flush=True)
        summary['all_expected_outcomes']=True;save()
    except Exception as error:summary['execution_failure']=str(error);save();raise
    print('PASS: bounded assertions satisfied and deliberate fault stopped with trace in all four modes')

if __name__=='__main__':main()
