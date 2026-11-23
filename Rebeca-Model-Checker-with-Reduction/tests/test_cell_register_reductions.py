import unittest
from audit_cell_register_reductions import certify
class SetCertificates(unittest.TestCase):
 def test_joint_set_does_not_require_internal_independence(self):
  graph={'s':{'A':{'a'},'B':{'b'}},'a':{},'b':{}}
  self.assertTrue(certify(graph,'s',{'A','B'})[0])
 def test_selected_disabled_later_rejected(self):
  graph={'s':{'A':{'a'},'B':{'b'}},'a':{'B':{'end'}},'b':{},'end':{}}
  self.assertFalse(certify(graph,'s',{'A'})[0])
 def test_nondeterministic_diamond_mismatch_rejected(self):
  graph={'s':{'A':{'a'},'B':{'b'}},'a':{'B':{'x','y'}},'b':{'A':{'x'}},'x':{},'y':{}}
  ok,evidence=certify(graph,'s',{'A'})
  self.assertFalse(ok);self.assertEqual(evidence['reason'],'relational_diamond_failed')
if __name__=='__main__':unittest.main()
