"""Reference counts must never replace semantic validation."""
import unittest
from run_cycle_barriers import check_result

class CountPolicyTest(unittest.TestCase):
    def test_other_counts_remain_pending(self):
        r=check_result({'result':'satisfied','states':189,'transitions':303},(201,328))
        self.assertFalse(r['matches_reference_counts'])
        self.assertEqual(r['semantic_audit'],'pending')

    def test_matching_counts_also_remain_pending(self):
        r=check_result({'result':'satisfied','states':201,'transitions':328},(201,328))
        self.assertTrue(r['matches_reference_counts'])
        self.assertEqual(r['semantic_audit'],'pending')

    def test_errors_are_not_accepted(self):
        for outcome in ('deadlock','assertion failed','deadline missed'):
            with self.assertRaises(ValueError):
                check_result({'result':outcome,'states':189,'transitions':303},(201,328))

if __name__=='__main__': unittest.main()
