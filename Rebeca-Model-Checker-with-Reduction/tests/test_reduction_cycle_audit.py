#!/usr/bin/env python3
import unittest
from audit_both_reductions import every_cycle_has_full_state

class Cycles(unittest.TestCase):
    def test_partial_cycle_rejected(self):
        e={'a':{'x':{'b'}},'b':{'y':{'a'}}}
        self.assertFalse(every_cycle_has_full_state({'a','b'},e,set()))
    def test_full_vertex_on_cycle(self):
        e={'a':{'x':{'b'}},'b':{'y':{'a'}}}
        self.assertTrue(every_cycle_has_full_state({'a','b'},e,{'b'}))
    def test_unrelated_full_vertex_does_not_rescue_partial_cycle(self):
        e={'a':{'x':{'a'}},'b':{'y':{'a'}}}
        self.assertFalse(every_cycle_has_full_state({'a','b'},e,{'b'}))
    def test_acyclic_partial_graph(self):
        self.assertTrue(every_cycle_has_full_state({'a','b'},{'a':{'x':{'b'}},'b':{}},set()))

if __name__=='__main__':unittest.main()
