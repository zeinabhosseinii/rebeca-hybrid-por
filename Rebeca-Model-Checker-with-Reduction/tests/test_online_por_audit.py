#!/usr/bin/env python3
"""Adversarial checks: outcome agreement must not hide unsound online choices."""
import copy
import unittest
from action_por_reference import Graph
from audit_online_por import verify

A=('A','Run');B=('B','Run')


def sample():
    g=Graph();g.initial='s'
    for s,a,t in [('s',A,'x'),('s',B,'y'),('x',B,'z'),('y',A,'z')]:g.add(s,a,t)
    g.observations={s:'' for s in g.edges}
    mapping={'1_0':'s','2_0':'x','3_0':'z'}
    edges={'1_0':{A:{'2_0'}},'2_0':{B:{'3_0'}},'3_0':{}}
    events=[{'event':'POR_STATE','state':'1'}, {'event':'POR_TRIAL','state':'1','actor':'A','accepted':'1'},
            {'event':'POR_STATE','state':'2'}, {'event':'POR_TRIAL','state':'2','actor':'B','accepted':'1'},
            {'event':'POR_STATE','state':'3'}, {'event':'POR_FULL','state':'3'}]
    return g,mapping,edges,events


class OnlineAudit(unittest.TestCase):
    def test_valid_persistent_reduction(self):
        r=verify(*sample());self.assertEqual(r['outcomes'],{'reduced':2,'full':1})
    def test_noncommuting_orders_rejected(self):
        g,m,e,log=sample();g.edges['y'][A]={'w'};g.edges['w'];g.observations['w']=''
        with self.assertRaisesRegex(ValueError,'diamond'):verify(g,m,e,log)
    def test_hidden_nondeterministic_successor_rejected(self):
        g,m,e,log=sample();g.add('s',A,'w');g.add('w',B,'z');g.observations['w']=''
        with self.assertRaisesRegex(ValueError,'nondeterministic'):verify(g,m,e,log)
    def test_accepted_self_loop_rejected(self):
        g,m,e,log=sample();g.add('z',A,'z');e['3_0']={A:{'3_0'}}
        log[-1]={'event':'POR_TRIAL','state':'3','actor':'A','accepted':'1'}
        with self.assertRaisesRegex(ValueError,'proviso'):verify(g,m,e,log)
    def test_fake_closed_witness_rejected(self):
        g,m,e,log=sample()
        log.insert(1,{'event':'POR_PROVISO_REJECT','state':'1','actor':'A','closedSuccessor':'2'})
        with self.assertRaisesRegex(ValueError,'not closed'):verify(g,m,e,log)
    def test_full_fallback_cannot_drop_enabled_action(self):
        g,m,e,log=sample();log[1]={'event':'POR_FULL','state':'1'}
        with self.assertRaisesRegex(ValueError,'full expansion lost'):verify(g,m,e,log)
    def test_fabricated_transition_rejected(self):
        g,m,e,log=sample();e['1_0'][B]={'2_0'}
        with self.assertRaisesRegex(ValueError,'fabricated'):verify(g,m,e,log)
    def test_premature_barrier_rejected(self):
        g,m,e,log=sample();log.insert(2,{'event':'POR_FULL_BARRIER','state':'1'})
        with self.assertRaisesRegex(ValueError,'premature'):verify(g,m,e,log)
    def test_false_exhaustive_flag_rejected(self):
        g,m,e,log=sample();log[1]['exhaustive']='1'
        with self.assertRaisesRegex(ValueError,'exhaustive'):verify(g,m,e,log)
    def test_exhaustive_self_loop_is_safe(self):
        g=Graph();g.initial='s';g.add('s',A,'s');g.observations={'s':''}
        r=verify(g,{'1_0':'s'},{'1_0':{A:{'1_0'}}},[
          {'event':'POR_STATE','state':'1'},
          {'event':'POR_TRIAL','state':'1','actor':'A','accepted':'1','exhaustive':'1'},
          {'event':'POR_FULL_BARRIER','state':'1'}])
        self.assertEqual(r['outcomes'],{'full_candidate':1})
    def test_exhaustive_actor_union_checks_every_handler(self):
        g=Graph();g.initial='s';other=('A','Other')
        g.add('s',A,'s');g.add('s',other,'s');g.observations={'s':''}
        events=[{'event':'POR_STATE','state':'1'},
                {'event':'POR_TRIAL','state':'1','actor':'A','accepted':'1','exhaustive':'1'},
                {'event':'POR_FULL_BARRIER','state':'1'}]
        edges={'1_0':{A:{'1_0'},other:{'1_0'}}}
        r=verify(g,{'1_0':'s'},edges,events)
        self.assertEqual(r['outcomes'],{'full_candidate':1})
        del edges['1_0'][other]
        with self.assertRaisesRegex(ValueError,'lost a nondeterministic successor'):
            verify(g,{'1_0':'s'},edges,events)

    def test_closed_completed_full_barrier(self):
        g=Graph();g.initial='0'
        for s,a,t in [('0',A,'1'),('0',B,'0'),('1',A,'1'),('1',B,'4'),('1',B,'3'),
          ('4',A,'3'),('4',B,'0'),('4',B,'2'),('3',A,'0'),('3',B,'3'),
          ('2',A,'0'),('2',B,'3'),('2',B,'2')]:g.add(s,a,t)
        g.observations={s:'' for s in g.edges}
        from cycle_barrier_reference import reduce_with_barriers
        choices,_,_=reduce_with_barriers(g)
        ids={s:str(int(s)+1)+'_0' for s in g.edges};m={v:k for k,v in ids.items()}
        edges={ids[s]:{a:{ids[t] for t in g.edges[s][a]} for a in choices[s]} for s in choices}
        log=[]
        for s,actions in choices.items():
            sid=ids[s].split('_')[0];log.append({'event':'POR_STATE','state':sid})
            if set(actions)==set(g.edges[s]):
                log.extend([{'event':'POR_FULL','state':sid},{'event':'POR_FULL_BARRIER','state':sid}])
            else:log.append({'event':'POR_TRIAL','state':sid,'actor':actions[0][0],'accepted':'1'})
        self.assertEqual(verify(g,m,edges,log)['outcomes'],{'full':3,'reduced':2})
    def test_truncated_trace_rejected(self):
        g,m,e,log=sample()
        with self.assertRaisesRegex(ValueError,'incomplete'):verify(g,m,e,log[:-1])


if __name__=='__main__':unittest.main()
