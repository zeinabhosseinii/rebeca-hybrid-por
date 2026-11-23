import unittest
from action_por_reference import Graph
from experiment_property_representatives import search,property_spec

A=('a','A');B=('b','B');P=('actor','field')
def make(edges):
 g=Graph();g.initial='s'
 for s,a,t in edges:g.add(s,a,t)
 g.observations={s:0 for s in g.edges}
 return g
class PropertyRepresentatives(unittest.TestCase):
 def test_visible_write_refused_even_if_observation_equal(self):
  g=make([('s',A,'s')]);r=search(g,{'s':True},{P},writes={A:{P}})
  self.assertEqual(r['candidate_trials'][0]['reason'],'property_visible_write');self.assertTrue(r['decisions'][0]['full'])
 def test_unknown_effects_fall_back(self):
  g=make([('s',A,'s')]);r=search(g,{'s':True},set(),writes={})
  self.assertEqual(r['candidate_trials'][0]['reason'],'unknown_effects');self.assertTrue(r['strong_cycle_passed'])
 def test_self_cycle_proviso_refused(self):
  g=make([('s',A,'s')]);r=search(g,{'s':True},set(),writes={A:set()})
  self.assertEqual(r['candidate_trials'][0]['reason'],'proviso_rejected');self.assertTrue(r['strong_cycle_passed'])
 def test_first_assertion_stops_before_other_edges(self):
  g=make([('s',A,'bad'),('s',B,'later'),('bad',B,'later')]);truth={s:s!='bad' for s in g.edges}
  r=search(g,truth,{P},writes={A:{P},B:{P}})
  self.assertEqual(r['result'],'assertion failed');self.assertEqual(r['explored_edges'],1);self.assertEqual(r['discovered_states'],2);self.assertEqual(r['expanded_states'],1);self.assertIsNone(r['strong_cycle_passed'])
 def test_deadlock_really_stops(self):
  g=make([('s',A,'end')]);r=search(g,{'s':True,'end':True},set(),writes={A:set()})
  self.assertEqual(r['result'],'deadlock');self.assertEqual(len(r['counterexample']),1)
 def test_dependency_failure_falls_back(self):
  g=make([('s',A,'a'),('s',B,'b'),('a',B,'x'),('b',A,'y')]);truth={s:True for s in g.edges}
  r=search(g,truth,{P},writes={A:set(),B:{P}})
  self.assertEqual(r['candidate_trials'][0]['reason'],'diamond_failed');self.assertTrue(r['decisions'][0]['full'])
 def test_unsupported_property_rejected(self):
  with self.assertRaises(ValueError):property_spec('uninterpreted')
if __name__=='__main__':unittest.main()
