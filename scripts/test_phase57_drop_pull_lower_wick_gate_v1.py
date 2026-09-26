import unittest
from scripts import phase57_drop_pull_lower_wick_gate_v1 as trial


def minute(minute, delay, lower=False, breakout=False):
    signals = {
        name: {"trigger": False} for name in (
            "CONTINUATION", "BREAKOUT", "COMPRESSION_EXPANSION",
            "HIGHER_LOW", "LOWER_WICK", "RECLAIM"
        )
    }
    signals["LOWER_WICK"]["trigger"] = lower
    signals["BREAKOUT"]["trigger"] = breakout
    return {"minute": minute, "delay": delay, "signals": signals}


class LowerWickGateTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"buyStates": ["RISE", "SHARP_RISE", "REBOUND"]}

    def test_breakout_alone_does_not_trigger_target(self):
        rows = [minute(600, 0), minute(601, 1, breakout=True), minute(602, 2)]
        states = [{"asOf": 600, "state": "DROP"}]
        got = trial._intent_with_lower_wick_gate("o", rows, states, self.policy)
        self.assertIsNone(got["intentMinute"])

    def test_lower_wick_triggers_target(self):
        rows = [minute(600, 0), minute(601, 1), minute(602, 2, lower=True)]
        states = [{"asOf": 600, "state": "PULLBACK"}]
        got = trial._intent_with_lower_wick_gate("o", rows, states, self.policy)
        self.assertEqual(got["intentMinute"], 602)
        self.assertEqual(got["intentReason"], "SIGNAL_TRIGGER")
        self.assertEqual(got["triggerSignals"], ["LOWER_WICK"])

    def test_state_transition_still_triggers_target(self):
        rows = [minute(600, 0), minute(605, 5)]
        states = [{"asOf": 600, "state": "DROP"}, {"asOf": 605, "state": "REBOUND"}]
        got = trial._intent_with_lower_wick_gate("o", rows, states, self.policy)
        self.assertEqual(got["intentMinute"], 605)
        self.assertEqual(got["intentReason"], "STATE_TRANSITION_BUY")

    def test_tie_preserves_signal_priority(self):
        rows = [minute(600, 0), minute(605, 5, lower=True)]
        states = [{"asOf": 600, "state": "DROP"}, {"asOf": 605, "state": "REBOUND"}]
        got = trial._intent_with_lower_wick_gate("o", rows, states, self.policy)
        self.assertEqual(got["intentReason"], "SIGNAL_TRIGGER")
        self.assertEqual(got["triggerSources"], ["SIGNAL_TRIGGER", "STATE_TRANSITION_BUY"])


if __name__ == "__main__":
    unittest.main()
