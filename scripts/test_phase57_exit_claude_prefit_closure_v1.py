from __future__ import annotations

import unittest

from scripts import phase57_exit_claude_prefit_closure_v1 as closure


class ClaudePrefitClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = closure.synthetic_checks()

    def test_all_r28_findings_have_explicit_disposition_and_close(self):
        findings = self.contract["findings"]
        self.assertEqual(set(findings), {f"F{i:03d}" for i in range(1, 13)})
        self.assertTrue(all(row["closed"] is True for row in findings.values()))
        self.assertEqual(findings["F011"]["disposition"], "REJECT")

    def test_state_is_direct_now_without_state_only_action(self):
        row = self.contract["findings"]["F001"]
        self.assertIn("DIRECT_STRICT_NOW", row["rule"])
        self.assertIn("NO_STATE_ONLY_ACTION", row["rule"])

    def test_signal_unknown_is_third_state_and_not_failure(self):
        row = self.contract["findings"]["F002"]
        self.assertEqual(row["encoding"], ["TRUE", "FALSE", "UNKNOWN"])
        self.assertFalse(row["trueToUnknownIsFailure"])
        self.assertFalse(row["completeSignalFilteringAllowed"])

    def test_incomplete_prefix_cannot_certify_extrema(self):
        row = self.contract["findings"]["F003"]
        self.assertEqual(row["observedExtrema"], "COMPLETED_OWNED_BARS_KNOWN_BY_NOW")
        self.assertIsNone(row["incompleteCertifiedExtrema"])
        self.assertTrue(self.contract["syntheticChecks"]["incompletePrefixCertifiedMetricsNull"])

    def test_pattern_scope_remains_30_blocked_187_finite(self):
        row = self.contract["findings"]["F004"]
        self.assertEqual((row["blockedPatternColumns"], row["finitePatternColumns"]), (30, 187))

    def test_decision_epoch_and_terminal_semantics_are_closed(self):
        self.assertIn("EXACT_COMPLETED_1M_ENDPOINT", self.contract["findings"]["F005"]["decisionEpoch"])
        terminal = self.contract["findings"]["F008"]
        self.assertFalse(terminal["overnight"])
        self.assertEqual(terminal["terminalMissingCensored"], 63)

    def test_buckets_do_not_enter_training_surface(self):
        row = self.contract["findings"]["F006"]
        self.assertIn("EVALUATOR_ONLY", row["bucketUse"])
        self.assertTrue(self.contract["syntheticChecks"]["trainingSurfaceBucketFree"])

    def test_missing_fresh_close_is_not_forward_filled(self):
        self.assertFalse(self.contract["findings"]["F009"]["freshMissingForwardFill"])
        self.assertTrue(self.contract["syntheticChecks"]["missingFreshCloseNotForwardFilled"])

    def test_finite_search_and_registered_thresholds_unchanged(self):
        f10 = self.contract["findings"]["F010"]
        f11 = self.contract["findings"]["F011"]
        self.assertEqual(f10["candidateConfigurations"], 24)
        self.assertFalse(f10["adaptiveExpansion"])
        self.assertEqual(f11["registeredThresholdPp"], [0.0, 0.10])
        self.assertEqual(f11["registeredPersistence"], [1, 2])
        self.assertTrue(self.contract["syntheticChecks"]["probabilityThresholdAbsent"])

    def test_sessions_and_zero_exposure_are_preserved(self):
        self.assertEqual(self.contract["findings"]["F012"]["sessions"], 58)
        self.assertEqual(self.contract["modelFits"], 0)
        self.assertFalse(self.contract["candidatePerformanceInspected"])
        self.assertEqual(self.contract["providerRequests"], 0)
        self.assertEqual(self.contract["protectedPartitionsOpened"], 0)
        self.assertTrue(all(value is False for value in self.contract["safety"].values()))


if __name__ == "__main__":
    unittest.main()
