"""Audit detector regressions, not assertions that Candidate C is valid."""
import unittest
from scripts import audit_phase57_exit_cc_freeze as audit


class FreezeAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ca = audit.module('probe_a', 'scripts/phase57_new_long_exit_candidate_a.py')
        cls.cb = audit.module('probe_b', 'scripts/phase57_new_long_exit_candidate_b.py')

    def bars(self, high=3.5, close=.5):
        return [{'slot': 1, 'missing': False, 'o': 0., 'h': high, 'l': min(0., close), 'c': close},
                {'slot': 2, 'missing': False, 'o': .5, 'h': 4., 'l': .5, 'c': 4.},
                {'slot': 3, 'missing': False, 'o': 4., 'h': 4., 'l': 4., 'c': 4.}]

    def fixed(self):
        return {'exitBar': 3, 'grossPct': 4., 'netPct': 3.95}

    def test_a_does_not_signal_on_first_arm(self):
        self.assertEqual(self.ca.policy(self.bars(), self.fixed())['status'], 'FIXED12_FALLBACK')

    def test_detect_dip_early_first_arm_violation(self):
        bars = self.bars(2.5, -.2)
        result = self.cb.policy(bars, self.fixed())
        self.assertEqual(result['status'], 'EARLY_2_TO_0_EXIT')
        self.assertEqual(audit.ordering_findings(bars, result)[0]['level'], 2)

    def test_detect_dip_mature_first_arm_violation(self):
        bars = self.bars()
        result = self.cb.policy(bars, self.fixed())
        self.assertEqual(result['signalBar'], 1)
        self.assertEqual(audit.ordering_findings(bars, result)[0]['level'], 3)

    def test_detect_stage_upgrade_same_bar(self):
        bars = self.bars(2.5, 1.)
        bars[1].update(h=3.5, c=.5)
        result = self.cb.policy(bars, self.fixed())
        self.assertEqual(result['signalBar'], 2)
        self.assertEqual(audit.ordering_findings(bars, result)[0]['armBar'], 2)

    def test_valid_later_bar_is_not_flagged(self):
        bars = self.bars(3.5, 2.)
        bars[1].update(h=2., c=.5)
        result = self.ca.policy(bars, self.fixed())
        self.assertEqual(result['signalBar'], 2)
        self.assertEqual(audit.ordering_findings(bars, result), [])

    def test_fill_bar_future_is_not_needed_for_signal(self):
        bars = self.bars(3.5, 2.)
        bars[1].update(h=2., c=.5)
        before = self.ca.policy(bars, self.fixed())
        bars[2].update(h=999., l=-999., c=999.)
        self.assertEqual(before, self.ca.policy(bars, self.fixed()))

    def row(self, status='PROTECT_EXIT', gross=.5, first=3):
        return {'first5': first, 'effectiveResult': {'status': status, 'exitBar': 3, 'grossPct': gross}}

    def test_open_exit_cannot_capture_later_high(self):
        self.assertTrue(audit.preserved(self.row(), 5, False))
        self.assertFalse(audit.preserved(self.row(), 5, True))

    def test_gap_open_at_milestone_is_preserved(self):
        self.assertTrue(audit.preserved(self.row(gross=5.), 5, True))

    def test_fixed_close_includes_same_bar_high(self):
        self.assertTrue(audit.preserved(self.row(status='FIXED12_FALLBACK'), 5, True))

    def test_prior_bar_milestone_is_preserved(self):
        self.assertTrue(audit.preserved(self.row(first=2), 5, True))

    def test_future_bar_milestone_is_not_preserved(self):
        self.assertFalse(audit.preserved(self.row(first=4), 5, True))

    def test_empty_metrics_are_explicit(self):
        self.assertEqual(audit.metrics([]), {'n': 0, 'mean': None, 'PF': None, 'p05': None})


if __name__ == '__main__':
    unittest.main()
