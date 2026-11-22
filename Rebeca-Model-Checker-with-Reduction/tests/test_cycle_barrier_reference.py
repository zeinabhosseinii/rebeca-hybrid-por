#!/usr/bin/env python3
import unittest
from action_por_reference import Graph
from cycle_barrier_reference import reduce_with_barriers
from audit_both_reductions import every_cycle_has_full_state
A=('R','A');B=('S','B')
def graph(edges,observations=None):
 g=Graph();g.initial='0'
 for s,a,t in edges:g.add(s,a,t)
 g.observations={s:(observations or {}).get(s,'') for s in g.edges};return g

class Barriers(unittest.TestCase):
 def example(self):
  return graph([('0',A,'1'),('0',B,'0'),('1',A,'1'),('1',B,'4'),('1',B,'3'),
   ('4',A,'3'),('4',B,'0'),('4',B,'2'),('3',A,'0'),('3',B,'3'),
   ('2',A,'0'),('2',B,'3'),('2',B,'2')])
 def test_closed_completed_full_state_can_be_used(self):
  g=self.example();selected,counts,decisions=reduce_with_barriers(g)
  self.assertTrue(any(d['accepted'] and not d['exhaustive'] and d['closed_full_targets'] for d in decisions))
  full={s for s,a in selected.items() if set(a)==set(g.edges[s])}
  edges={s:{a:g.edges[s][a] for a in actions} for s,actions in selected.items()}
  self.assertTrue(every_cycle_has_full_state(set(selected),edges,full))
 def test_current_state_is_not_a_completed_barrier(self):
  g=graph([('0',A,'0'),('0',B,'1'),('1',A,'1')],{'1':'error'})
  selected,counts,_=reduce_with_barriers(g)
  self.assertEqual(set(selected['0']),{A,B});self.assertIn('1',selected)
 def test_all_nondeterministic_successors_must_pass(self):
  g=self.example();g.add('3',A,'3')
  _,_,decisions=reduce_with_barriers(g)
  matching=[d for d in decisions if d['state']=='3' and d['action']==A]
  self.assertTrue(matching);self.assertFalse(matching[0]['accepted'])
 def test_exhaustive_self_loop_is_not_reduction(self):
  selected,counts,_=reduce_with_barriers(graph([('0',A,'0')]))
  self.assertEqual(selected['0'],[A]);self.assertEqual(counts['full'],1)

if __name__=='__main__':unittest.main()
