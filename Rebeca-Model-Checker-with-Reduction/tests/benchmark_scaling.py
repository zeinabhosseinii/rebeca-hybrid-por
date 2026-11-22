#!/usr/bin/env python3
"""Balanced repeated four-path scaling measurements, with explicit timeouts."""
import argparse,csv,hashlib,json,os,platform,random,re,statistics,subprocess,time,shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from scaling_models import make_model
from run_quiescence_models import ROOT,command
from compare_model_suite import body,digest,sample

MODES=('full','static','dynamic','dynamic_no_por')

def copy_without_por(source,destination):
    """Preserve all native bytes except one PO macro; reject unexpected inputs."""
    files=sorted(p for p in source.iterdir() if p.suffix in ('.cpp','.h'))
    if not files or not (source/'TimedModelChecker.cpp').exists():raise ValueError('Missing dynamic native sources')
    for f in files:shutil.copyfile(f,destination/f.name)
    config=destination/'Config.h';original=config.read_bytes()
    changed,count=re.subn(rb'^[\t ]*#[\t ]*define[\t ]+PO[\t ]*\r?$',
                          b'// benchmark control: PO disabled',original,flags=re.M)
    if count!=1:raise ValueError('Expected exactly one dynamic PO macro')
    config.write_bytes(changed)
    for f in files:
        if f.name!='Config.h' and f.read_bytes()!=(destination/f.name).read_bytes():
            raise ValueError('Unexpected native source difference')
    return {'derived_from':'dynamic','native_change':'one PO macro removed in Config.h',
            'unchanged_native_files':len(files)-1,'original_config_sha256':digest(source/'Config.h'),
            'control_config_sha256':digest(config)}

def prepare(case,family,n,a):
    name=f'Scale_{family}_{n}';model=case/(name+'.rebeca');model.write_text(make_model(family,n))
    export=ROOT.parent/'ARIA/output'/(name+'_pruned')
    annotated=export/(name+'_annotated.rebeca')
    annotated.unlink(missing_ok=True)
    start=time.perf_counter()
    command(['java','-jar',ROOT.parent/'ARIA/target/erdg-tool-0.1.0.jar','file',model],ROOT.parent/'ARIA',case/'aria.log')
    cost={'aria_export_seconds':time.perf_counter()-start,'modes':{}}
    if not annotated.exists() or body(annotated.read_text())!=body(model.read_text()):raise ValueError('Annotation changed bodies or export failed')
    (case/'annotated.rebeca').write_bytes(annotated.read_bytes())
    for mode in MODES:
        d=case/mode;d.mkdir()
        derivation=None
        if mode=='dynamic_no_por':
            start=time.perf_counter();derivation=copy_without_por(case/'dynamic',d)
            generation=0.0;copy_seconds=time.perf_counter()-start
        else:
            args=['java','-jar',ROOT/'target/rmc-2.14.jar','-s',annotated if mode=='static' else model,'-e','TIMED_REBECA','-v','2.3','-o',d]
            if mode=='dynamic':args+=['--aria']
            start=time.perf_counter();command(args,ROOT,d/'generate.log');generation=time.perf_counter()-start
            copy_seconds=0.0
        cpp=sorted(d.glob('*.cpp'))
        if not cpp:raise ValueError('No generated C++')
        config=(d/'Config.h').read_text()
        if bool(re.search(r'^\s*#\s*define\s+PO\b',config,re.M))!=(mode=='dynamic') or re.search(r'^\s*#\s*define\s+TTS\b',config,re.M):
            raise ValueError('Unexpected FTTS/POR configuration')
        start=time.perf_counter()
        flags=['-std=c++11','-pthread','-O2']+(['-DEXPORT_STATE_SPACE'] if a.audit_small else [])
        command(['g++',*flags,*[f.name for f in cpp],'-o','execute'],d,d/'compile.log')
        cost['modes'][mode]={'generation_seconds':generation,'copy_seconds':copy_seconds,'compile_seconds':time.perf_counter()-start}
        if derivation:cost['modes'][mode]['derivation']=derivation
    return model,cost

def finite_audit(case,model):
    # Restricted to exact generated sources without sender/time/properties.
    # This audit is deliberately sufficient, not complete for every safe POR.
    import re
    match=re.fullmatch(r'Scale_(independent|shared)_(\d+)\.rebeca',model.name)
    if not match or model.read_text()!=make_model(match[1],int(match[2])):
        raise ValueError('Audit restricted to exact generated family source')
    from audit_hub_alternatives import signature
    from action_por_reference import Graph,read_full_graph
    from audit_both_reductions import every_cycle_has_full_state
    for mode in MODES:
        (case/mode/'report.xml').write_bytes((case/mode/'report-0.xml').read_bytes())
    def exported(directory):
        tree=ET.parse(directory/'statespace.xml').getroot()
        states={x.get('id'):x for x in tree.findall('state')}
        sigs={}
        for sid,x in states.items():
            atomic,actors=signature(x)
            for actor in x.findall('rebec'):
                if actor.findtext('now')!='0':raise ValueError('Nonzero time unsupported')
                for message in actor.findall('queue/message'):
                    if message.get('arrival')!='0' or message.get('deadline')!='infinity':raise ValueError('Timed queue unsupported')
            sigs[sid]=(atomic,tuple((name,variables,tuple(sorted(queue,key=repr)),now) for name,variables,queue,now in actors))
        edges={}
        for x in tree.findall('transition'):
            act=x.find('messageserver');key=(act.get('owner'),act.get('title'))
            edges.setdefault(x.get('source'),{}).setdefault(key,set()).add(x.get('destination'))
        return states,sigs,edges
    full=case/'full';raw=read_full_graph(full/'statespace.xml',full/'report.xml')
    _,fs,fe=exported(full);inverse={}
    for sid,sig in fs.items():inverse.setdefault(sig,sid)
    # Sender is never read by these exact generated programs. Quotient the
    # full baseline, which can retain multiple sender-only representations.
    q={sid:inverse[sig] for sid,sig in fs.items()};g=Graph();g.initial=q[raw.initial]
    for sid in fs:
        g.edges[q[sid]]
        if q[sid] in g.observations and g.observations[q[sid]]!=raw.observations[sid]:raise ValueError('Sender projection changed observations')
        g.observations[q[sid]]=raw.observations[sid]
    for sid,actions in fe.items():
        for act,targets in actions.items():
            for t in targets:g.add(q[sid],act,q[t])
    for sid in fs:
        actual={act:{q[t] for t in ts} for act,ts in fe.get(sid,{}).items()}
        if actual!=dict(g.edges[q[sid]]):raise ValueError('Sender equivalence has inconsistent successor relation')
    result={}
    for mode in ('static','dynamic','dynamic_no_por'):
        states,sigs,edges=exported(case/mode);mapping={s:inverse[sig] for s,sig in sigs.items()}
        if mapping[next(iter(states))]!=g.initial:raise ValueError('Initial mismatch')
        full_vertices=set();checked=0
        for s in states:
            projected={act:{mapping[t] for t in ts} for act,ts in edges.get(s,{}).items()}
            original=dict(g.edges[mapping[s]])
            if bool(original)!=bool(projected):raise ValueError('C0 mismatch')
            for act,targets in projected.items():
                if original.get(act)!=targets:raise ValueError('Altered/missing action outcomes')
            if mode=='dynamic_no_por' and projected!=original:raise ValueError('PO-disabled control omitted full behavior')
            if projected==original:full_vertices.add(s);continue
            for act in projected:
                ok,evidence=g.certify(mapping[s],act)
                if not ok:raise ValueError(('Persistence/diamond audit failed',mode,s,act,evidence))
                checked+=1
        if mode=='dynamic_no_por' and set(mapping.values())!=set(g.edges):raise ValueError('PO-disabled control lost reachable projected states')
        if not every_cycle_has_full_state(states,edges,full_vertices):raise ValueError('Strong cycle condition failed')
        result[mode]={'states':len(states),'partial_action_certificates':checked,'full_vertices':len(full_vertices),'strong_cycle_passed':True}
    return {'finite_generated_instance_only':True,'unused_sender_projection':True,'equal_time_queue_multiset_projection':True,'full_projection_successor_consistency_checked':True,'model_sha256':digest(model),'modes':result}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--families',nargs='+',choices=['independent','shared'],default=['independent','shared'])
    p.add_argument('--sizes',nargs='+',type=int,help='Override both family size lists')
    p.add_argument('--independent-sizes',nargs='+',type=int,default=[4,6,8])
    p.add_argument('--shared-sizes',nargs='+',type=int,default=[2,4,6])
    p.add_argument('--repeats',type=int,default=10);p.add_argument('--timeout',type=float,default=30)
    p.add_argument('--seed',type=int,default=1729);p.add_argument('--audit-small',action='store_true')
    a=p.parse_args()
    sizes={f:a.sizes or (a.independent_sizes if f=='independent' else a.shared_sizes) for f in a.families}
    if a.repeats<1 or a.timeout<=0 or any(n<1 or n>16 for v in sizes.values() for n in v):p.error('Invalid limits')
    if a.audit_small and max(n for v in sizes.values() for n in v)>3:p.error('Finite graph audit restricted to <=3 workers; do not time exports')
    out=a.output.resolve()
    if out.exists():p.error('Choose a fresh output directory')
    out.mkdir(parents=True);os.environ['ARIA_PRUNE']='1';os.environ['ARIA_EXPORT']='1'
    result={'java':subprocess.run(['java','-version'],capture_output=True,text=True,check=True).stderr.strip(),
            'native_flags':['-std=c++11','-pthread','-O2'],'diagnostics':False,'platform':platform.platform(),'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
            'rmc_jar_sha256':digest(ROOT/'target/rmc-2.14.jar'),'aria_jar_sha256':digest(ROOT.parent/'ARIA/target/erdg-tool-0.1.0.jar'),
            'modes':list(MODES),'schema_version':2,'repeats':a.repeats,'warmups_per_mode':1,'seed':a.seed,'graph_export':a.audit_small,'cases':[]}
    rng=random.Random(a.seed)
    def save():
        (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
        rows=[]
        for c in result['cases']:
            for mode,data in c['modes'].items():
                good=[x for x in data['samples'] if x.get('status')=='completed']
                rows.append({'family':c['family'],'workers':c['workers'],'mode':mode,'status':data['status'],
                             'completed_samples':len(good),'states':good[0]['states'] if good else '',
                             'transitions':good[0]['transitions'] if good else '',
                             'median_seconds':statistics.median(x['native_wall_seconds'] for x in good) if good else '',
                             'min_seconds':min(x['native_wall_seconds'] for x in good) if good else '',
                             'max_seconds':max(x['native_wall_seconds'] for x in good) if good else '',
                             'peak_rss_median_kib':statistics.median(x['peak_rss_kib'] for x in good) if good else ''})
        if rows:
            with (out/'summary.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        contrasts=[]
        definitions=[('representation_control','full','dynamic_no_por'),
                     ('online_por_control','dynamic_no_por','dynamic'),
                     ('static_vs_full_native','full','static'),
                     ('dynamic_vs_full_native','full','dynamic'),
                     ('dynamic_vs_static_native','static','dynamic')]
        for c in result['cases']:
            for label,baseline,target in definitions:
                left=c['modes'][baseline];right=c['modes'][target]
                if left['status']!='completed' or right['status']!='completed':continue
                l=left['samples'];r=right['samples']
                contrasts.append({'family':c['family'],'workers':c['workers'],'comparison':label,
                                  'baseline':baseline,'target':target,
                                  'state_reduction_percent':100*(1-r[0]['states']/l[0]['states']),
                                  'native_median_speed_ratio':statistics.median(x['native_wall_seconds'] for x in l)/statistics.median(x['native_wall_seconds'] for x in r)})
        if contrasts:
            with (out/'comparisons.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(contrasts[0]));w.writeheader();w.writerows(contrasts)

    try:
        for family in a.families:
            for n in sizes[family]:
                case=out/f'{family}_{n}';case.mkdir();model,cost=prepare(case,family,n,a)
                c={'family':family,'workers':n,'source_sha256':digest(model),'preparation':cost,'orders':[],
                   'modes':{m:{'status':'pending','samples':[]} for m in MODES}}
                result['cases'].append(c);save()
                # One warmup and then measured rounds. Rotate one seeded base
                # order to balance positions over groups of four rounds.
                order=list(MODES);rng.shuffle(order)
                for round_index in range(-1,a.repeats):
                    rotated=order[(round_index+1)%len(MODES):]+order[:(round_index+1)%len(MODES)]
                    c['orders'].append({'round':round_index,'modes':rotated})
                    for mode in rotated:
                        data=c['modes'][mode]
                        if data['status']=='timeout':continue
                        try:
                            measured=sample(case/mode,round_index+1,a.timeout)
                        except subprocess.TimeoutExpired:
                            data['status']='timeout';data['samples'].append({'status':'timeout','round':round_index,'limit_seconds':a.timeout});save();continue
                        if measured['result']!='satisfied':raise ValueError(('Healthy-model outcome failed',family,n,mode,measured))
                        measured.update(status='completed',round=round_index)
                        if round_index<0:data['warmup']=measured
                        else:data['samples'].append(measured)
                        data['status']='running';save()
                for mode,data in c['modes'].items():
                    if data['status']!='timeout':
                        ids={(x['states'],x['transitions']) for x in data['samples']}
                        if len(ids)!=1 or ids!={(data['warmup']['states'],data['warmup']['transitions'])} or len(data['samples'])!=a.repeats:raise ValueError('Unstable/incomplete repetitions')
                        data['status']='completed'
                    print(family,n,mode,data['status'],[(x.get('states'),x.get('transitions')) for x in data['samples'][:1]],flush=True)
                if a.audit_small:
                    if any(v['status']!='completed' for v in c['modes'].values()):raise ValueError('Small audit requires completed full reference')
                    # Last exported graph must agree with stable counts; report-0
                    # is warmup, and all runs are required to be satisfied.
                    c['finite_audit']=finite_audit(case,model)
                save()
    except Exception as error:
        result['execution_failure']=str(error);save();raise
    result['execution_finished']=True
    result['all_runs_completed']=all(d['status']=='completed' for c in result['cases'] for d in c['modes'].values());save()
    print('FINISHED; timeout rows are incomplete, not correctness or speedup evidence:',out)
    if not result['all_runs_completed']:raise SystemExit(2)

if __name__=='__main__':main()
