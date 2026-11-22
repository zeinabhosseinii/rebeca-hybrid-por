#!/usr/bin/env python3
"""Explain actual representatives, proof category, branches and proviso witnesses."""
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def audit(directory):
    report=ET.parse(directory/'report.xml').getroot()
    result=report.findtext('checked-property/result')
    rows={};current=None;active=None
    for line in (directory/'errors.log').read_text().splitlines():
        parts=line.split()
        if not parts or not parts[0].startswith('POR_'):continue
        kind=parts[0];e=dict(x.split('=',1) for x in parts[1:] if '=' in x)
        if kind=='POR_STATE':
            if e['state'] in rows:raise ValueError('Repeated expansion')
            current=e['state'];rows[current]={'representatives':[],'outcome':None,'actor_candidates':[],'dependency_blocks':[],'quiescent_exclusions':[]};active=None
        if kind not in ('POR_REPRESENTATIVE','POR_ALTERNATIVE','POR_PROVISO_REJECT','POR_TRIAL','POR_FULL','POR_CANDIDATE','POR_BLOCK','POR_QUIESCENT_SKIP'):continue
        if e.get('state')!=current:raise ValueError('Out-of-order representative event')
        row=rows[current]
        if kind in ('POR_CANDIDATE','POR_BLOCK','POR_QUIESCENT_SKIP'):
            field={'POR_CANDIDATE':'actor_candidates','POR_BLOCK':'dependency_blocks','POR_QUIESCENT_SKIP':'quiescent_exclusions'}[kind]
            row[field].append(e)
        elif kind=='POR_REPRESENTATIVE':
            if active is not None:raise ValueError('Unfinished trial')
            if e['scope'] not in ('action','actor_union'):raise ValueError('Unknown scope')
            if (int(e['msg'])>0)!=(e['scope']=='action'):raise ValueError('Scope/message mismatch')
            active={**e,'executed':[],'closed_successors':[],'accepted':None}
            row['representatives'].append(active)
        elif kind=='POR_ALTERNATIVE' and e['phase']=='trial':
            if active is None or e['actor']!=active['actor']:raise ValueError('Unmatched action execution')
            if active['scope']=='action' and e['msg']!=active['msg']:raise ValueError('Wrong message executed')
            active['executed'].append(e)
        elif kind=='POR_PROVISO_REJECT':
            if active is None:raise ValueError('Unmatched proviso rejection')
            active['closed_successors'].append(e['closedSuccessor'])
        elif kind=='POR_TRIAL':
            if active is None:raise ValueError('Missing representative identity')
            for field in ('actor','scope','msg','proof'):
                if e[field]!=active[field]:raise ValueError('Trial identity changed')
            if e.get('exhaustive','0')!=active.get('exhaustive','0'):raise ValueError('Exhaustive identity changed')
            if not active['executed']:raise ValueError('Empty trial')
            accepted=e['accepted']=='1'
            if accepted==bool(active['closed_successors']):raise ValueError('Proviso/outcome mismatch')
            active['accepted']=accepted
            if accepted:
                if row['outcome'] is not None:raise ValueError('Repeated accepted outcome')
                row['outcome']='full_candidate' if active.get('exhaustive')=='1' else 'reduced'
            active=None
        elif kind=='POR_FULL':
            if active is not None or row['outcome'] is not None:raise ValueError('Invalid full fallback')
            row['outcome']='full'
    if not rows:raise ValueError('Missing current representative diagnostics')
    unfinished=[s for s,r in rows.items() if r['outcome'] is None]
    if unfinished:
        if result=='satisfied' or unfinished!=[current] or not report.findall('counter-example-trace/state'):
            raise ValueError('Incomplete decisions')
        rows[current]['outcome']='stopped_on_first_error'
    if result=='satisfied' and len(rows)!=int(report.findtext('system-info/reached-states')):
        raise ValueError('State/decision count mismatch')
    accepted=[c for r in rows.values() for c in r['representatives'] if c['accepted']]
    return {'result':result,'expanded_states':len(rows),
            'outcomes':dict(Counter(r['outcome'] for r in rows.values())),
            'accepted_scopes':dict(Counter(c['scope'] for c in accepted)),
            'accepted_proofs':dict(Counter(c['proof'] for c in accepted)), 'states':rows}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directories',nargs='+',type=Path)
    p.add_argument('--output',type=Path,default=Path('tmp/action_candidate_decisions.json'))
    a=p.parse_args();names=[d.name for d in a.directories]
    data={(str(d) if names.count(d.name)>1 else d.name):audit(d) for d in a.directories}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(data,indent=2)+'\n')
    for name,r in data.items():print(name,{k:v for k,v in r.items() if k!='states'})
