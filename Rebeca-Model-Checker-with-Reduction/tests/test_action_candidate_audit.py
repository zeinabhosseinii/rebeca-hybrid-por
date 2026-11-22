#!/usr/bin/env python3
"""Reject logs that claim an action identity different from what actually ran."""
from pathlib import Path
import tempfile
import unittest
from audit_action_candidates import audit

LOG='''POR_STATE state=1
POR_REPRESENTATIVE state=1 actor=A scope=action msg=1 proof=global_dependency_check alternatives=1
POR_ALTERNATIVE state=1 phase=trial actor=A alternative=0 msg=1 action=RUN
POR_TRIAL state=1 actor=A accepted=1 scope=action msg=1 proof=global_dependency_check
'''
REPORT='<model-checking-report><system-info><reached-states>1</reached-states></system-info><checked-property><result>satisfied</result></checked-property></model-checking-report>'


class Audit(unittest.TestCase):
    def run_log(self,log):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'errors.log').write_text(log);(p/'report.xml').write_text(REPORT)
            return audit(p)
    def test_valid_identity(self):
        self.assertEqual(self.run_log(LOG)['accepted_scopes'],{'action':1})
    def test_wrong_executed_message(self):
        with self.assertRaisesRegex(ValueError,'Wrong message'):
            self.run_log(LOG.replace('alternative=0 msg=1','alternative=0 msg=2'))
    def test_trial_identity_changed(self):
        with self.assertRaisesRegex(ValueError,'identity changed'):
            self.run_log(LOG.replace('accepted=1 scope=action msg=1','accepted=1 scope=action msg=2'))
    def test_false_acceptance_after_proviso_rejection(self):
        altered=LOG.replace('POR_TRIAL','POR_PROVISO_REJECT state=1 actor=A closedSuccessor=1\nPOR_TRIAL')
        with self.assertRaisesRegex(ValueError,'Proviso/outcome'):
            self.run_log(altered)
    def test_missing_identity(self):
        with self.assertRaisesRegex(ValueError,'Unmatched'):
            self.run_log('\n'.join(l for l in LOG.splitlines() if not l.startswith('POR_REPRESENTATIVE')))
    def test_truncation(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            self.run_log('\n'.join(LOG.splitlines()[:-1]))


if __name__=='__main__':unittest.main()
