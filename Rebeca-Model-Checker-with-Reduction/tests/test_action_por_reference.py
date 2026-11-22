#!/usr/bin/env python3
import tempfile
from pathlib import Path
import unittest
from action_por_reference import Graph, read_full_graph

A=('Hub','A'); B=('Hub','B'); C=('Worker','C')
def graph(edges, obs=None):
    result=Graph();result.initial='0'
    for s,a,t in edges:result.add(s,a,t)
    result.observations={s:(obs or {}).get(s,'') for s in result.edges}
    return result

def reachable_observations(g, selected):
    return {g.observations[s] for s in selected}

class ReferenceTest(unittest.TestCase):
    def test_distinct_same_actor_commute(self):
        g=graph([('0',A,'1'),('0',B,'2'),('1',B,'3'),('2',A,'3')])
        self.assertTrue(g.certify('0',A)[0])
        selected,counts,_=g.reduce()
        self.assertEqual(selected['0'],[A]);self.assertEqual(len(selected),3)
        self.assertIn('3',selected) # terminal observation is not silently removed
        self.assertEqual(reachable_observations(g,selected),set(g.observations.values()))

    def test_future_interference_is_not_a_local_diamond(self):
        g=graph([('0',A,'1'),('0',B,'2'),('1',B,'3'),('2',A,'3'),
                 ('2',C,'4'),('3',C,'5'),('4',A,'6')])
        ok,witness=g.certify('0',A)
        self.assertFalse(ok);self.assertEqual(witness['state'],'2')
        self.assertEqual(witness['reason'],'diamond_failed')

    def test_enabling_effects_reject(self):
        g=graph([('0',A,'1'),('0',B,'2'),('2',A,'3')])
        self.assertEqual(g.certify('0',A)[1]['reason'],'other_disabled')
        g=graph([('0',A,'1'),('0',B,'2'),('1',B,'3')])
        self.assertEqual(g.certify('0',A)[1]['reason'],'selected_disabled_after_other')

    def test_nondeterministic_diamonds_cover_every_branch(self):
        g=graph([('0',A,'1'),('0',A,'2'),('0',B,'3'),('1',B,'4'),
                 ('2',B,'5'),('3',A,'4'),('3',A,'5')])
        self.assertTrue(g.certify('0',A)[0])
        del g.edges['2'][B]
        self.assertFalse(g.certify('0',A)[0])

    def test_property_visibility_rejects(self):
        g=graph([('0',A,'1')],{'1':'assertion_failure'})
        self.assertEqual(g.certify('0',A)[1]['reason'],'property_visible')
        selected,_,_=g.reduce();self.assertIn('1',selected)

    def test_proviso_prevents_invisible_loop_starvation(self):
        g=graph([('0',A,'0'),('0',B,'1'),('1',A,'1')],{'1':'error'})
        self.assertTrue(g.certify('0',A)[0])
        selected,counts,_=g.reduce()
        self.assertEqual(set(selected['0']),{A,B});self.assertIn('1',selected)
        self.assertGreater(counts['proviso_reject'],0)

    def test_incomplete_or_reduced_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);space=root/'statespace.xml';report=root/'report.xml'
            (root/'Config.h').write_text('#define PO\n')
            (root/'AbstractTimedRebecaAnalyzer.cpp').write_text('')
            report.write_text('<model-checking-report><checked-property><result>satisfied</result><type>Reachability</type></checked-property><system-info><reached-states>1</reached-states></system-info></model-checking-report>')
            space.write_text('<transitionsystem><state id="0"/></transitionsystem>')
            with self.assertRaisesRegex(ValueError,'without POR'):read_full_graph(space,report)
            (root/'Config.h').write_text('')
            self.assertEqual(len(read_full_graph(space,report).edges),1)
            report.write_text(report.read_text().replace('satisfied','deadlock'))
            with self.assertRaisesRegex(ValueError,'incomplete'):read_full_graph(space,report)

if __name__=='__main__':unittest.main()
