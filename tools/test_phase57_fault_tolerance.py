import unittest

from phase57_fault_tolerance import RuntimeSafetyState, bounded_com_read


class FaultToleranceTests(unittest.TestCase):
    def test_single_com_busy_is_retryable_and_recovers(self):
        state = RuntimeSafetyState(max_com_retries=3)
        calls = {"n": 0}
        def read():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("RPC_E_CALL_REJECTED 0x80010001")
            return "ok"
        self.assertEqual(bounded_com_read(read, state), "ok")
        self.assertFalse(state.kill_switch_latched)
        self.assertEqual(state.com_retry_count, 0)

    def test_com_retry_exhaustion_latches_kill_switch(self):
        state = RuntimeSafetyState(max_com_retries=2)
        def read():
            raise RuntimeError("RPC_E_CALL_REJECTED")
        with self.assertRaisesRegex(RuntimeError, "EXCEL_COM_RETRY_EXHAUSTED"):
            bounded_com_read(read, state)
        self.assertTrue(state.kill_switch_latched)
        self.assertIn("EXCEL_COM_RETRY_EXHAUSTED", state.faults)

    def test_critical_faults_latch(self):
        for fault in (
            "RSS_DISCONNECTED", "ACCOUNT_SNAPSHOT_STALE", "RECONCILIATION_MISMATCH",
            "UNKNOWN_ORDER", "PARTIAL_FILL", "RESTART_STATE_UNVERIFIED",
            "DUPLICATE_OR_REPLAY", "FINALIZED_BAR_REVISED",
        ):
            state = RuntimeSafetyState()
            out = state.observe_fault(fault)
            self.assertTrue(out["killSwitchLatched"], fault)
            self.assertFalse(out["newIntentAllowed"])
            self.assertFalse(out["transmitted"])

    def test_reset_without_clean_health_check_stays_latched(self):
        state = RuntimeSafetyState()
        state.observe_fault("RSS_DISCONNECTED")
        out = state.explicit_reset(health_check_passed=False)
        self.assertTrue(out["killSwitchLatched"])
        self.assertIn("RESET_HEALTH_CHECK_FAILED", out["faults"])

    def test_explicit_reset_with_health_check_clears_latch(self):
        state = RuntimeSafetyState()
        state.observe_fault("RSS_DISCONNECTED")
        out = state.explicit_reset(health_check_passed=True)
        self.assertFalse(out["killSwitchLatched"])
        self.assertEqual(out["faults"], [])
        self.assertFalse(out["executionAllowed"])
        self.assertFalse(out["newIntentAllowed"])

    def test_unknown_fault_fails_closed(self):
        state = RuntimeSafetyState()
        out = state.observe_fault("something-new")
        self.assertTrue(out["killSwitchLatched"])
        self.assertTrue(out["faults"][0].startswith("UNKNOWN_FAULT:"))


if __name__ == "__main__":
    unittest.main()
