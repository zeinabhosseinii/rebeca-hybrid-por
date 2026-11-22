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
    def test_truncated_trace_rejected(self):
        g,m,e,log=sample()
        with self.assertRaisesRegex(ValueError,'incomplete'):verify(g,m,e,log[:-1])


if __name__=='__main__':unittest.main()
