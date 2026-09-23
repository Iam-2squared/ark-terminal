import unittest
from unittest.mock import patch

from scripts import phase57_drop_pull_1m_state_recheck_v1 as trial
from scripts import phase57_state_v3_9pattern_entry_v1 as v3


def minute(m, delay, signal=False):
    signals = {
        name: {"trigger": False} for name in (
            "CONTINUATION", "BREAKOUT", "COMPRESSION_EXPANSION",
            "HIGHER_LOW", "LOWER_WICK", "RECLAIM"
        )
    }
    signals["BREAKOUT"]["trigger"] = signal
    return {"minute": m, "delay": delay, "signals": signals}


class OneMinuteRecheckTests(unittest.TestCase):
    def test_classifies_every_available_minute_with_strict_prefix(self):
        rows = [minute(600, 0), minute(601, 1), minute(602, 2)]
        path = {
            "previousSession": "2026-01-01",
            "previous": [[599, 100, 101, 99, 100]],
            "today": [
                [599, 100, 101, 99, 100],
                [600, 100, 101, 99, 100.5],
                [601, 100.5, 102, 100, 101],
                [602, 101, 103, 100, 102],
            ],
        }
        seen = []

        def fake(day, now, prefix, previous, previous_session):
            seen.append((now, [int(x[0]) for x in prefix]))
            return {
                "state": "DROP" if now < 602 else "REBOUND",
                "stateStatus": "CLASSIFIED",
                "dataQuality": "OK",
                "confidence": "HIGH",
                "reasonCodes": [],
                "asOf": now,
                "lastPriceTime": now - 1,
                "maxSourceBarStart": max((int(x[0]) for x in prefix), default=None),
                "maxSourceBarEnd": now,
                "inputCutoff": now,
                "unit": .001,
                "priorDir": -1,
                "recentDir": 1 if now == 602 else -1,
                "priorReturn": -.01,
                "recentReturn": .002 if now == 602 else -.002,
                "recentCoverage": 1.0,
                "recentTransitions": 3,
                "earlierTransitions": 3,
                "contractVersion": "phase57-state-v3-price-shape-step1-v1",
            }

        with patch.object(v3, "classify_state_v3", side_effect=fake):
            checks, violations = trial._classify_target_every_minute(
                "o", "2026-01-02", rows, path
            )
        self.assertEqual([x["delay"] for x in checks], [0, 1, 2])
        self.assertEqual([x["state"] for x in checks], ["DROP", "DROP", "REBOUND"])
        self.assertEqual(violations, 0)
        for now, prefix_starts in seen:
            self.assertTrue(all(start < now for start in prefix_starts))

    def test_one_minute_transition_can_precede_five_minute_checkpoint(self):
        rows = [minute(600, 0), minute(601, 1), minute(602, 2), minute(605, 5)]
        candidate_states = [
            {"asOf": 600, "state": "DROP"},
            {"asOf": 601, "state": "DROP"},
            {"asOf": 602, "state": "REBOUND"},
            {"asOf": 605, "state": "REBOUND"},
        ]
        baseline_states = [
            {"asOf": 600, "state": "DROP"},
            {"asOf": 605, "state": "REBOUND"},
        ]
        policy = {"buyStates": ["RISE", "SHARP_RISE", "REBOUND"]}
        candidate = v3.frozen_intent("o", rows, candidate_states, policy)
        baseline = v3.frozen_intent("o", rows, baseline_states, policy)
        self.assertEqual(candidate["intentMinute"], 602)
        self.assertEqual(candidate["intentReason"], "STATE_TRANSITION_BUY")
        self.assertEqual(baseline["intentMinute"], 605)

    def test_existing_signal_keeps_priority(self):
        rows = [minute(600, 0), minute(601, 1, signal=True)]
        states = [{"asOf": 600, "state": "DROP"}, {"asOf": 601, "state": "REBOUND"}]
        policy = {"buyStates": ["RISE", "SHARP_RISE", "REBOUND"]}
        got = v3.frozen_intent("o", rows, states, policy)
        self.assertEqual(got["intentReason"], "SIGNAL_TRIGGER")
        self.assertEqual(got["triggerSources"], ["SIGNAL_TRIGGER", "STATE_TRANSITION_BUY"])


if __name__ == "__main__":
    unittest.main()
