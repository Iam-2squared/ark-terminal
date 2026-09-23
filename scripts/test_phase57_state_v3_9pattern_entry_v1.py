"""Contract, policy, causality and locked-evidence checks for State v3 Entry."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import random
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import phase57_state_v3_9pattern_entry_v1 as entry  # noqa: E402


EVIDENCE = ROOT / "docs/evidence/phase57-state-v3-9pattern-entry-v1"
POLICY = EVIDENCE / "POLICY_LOCK.json"
MEASUREMENT = EVIDENCE / "measurement"


def bar(minute, close, open_=None):
    open_ = close if open_ is None else open_
    high, low = max(open_, close), min(open_, close)
    return [float(minute), float(open_), float(high), float(low), float(close), 1.0, float(close)]


def flat_previous(price=100.0):
    return [bar(540, price), bar(541, price), bar(542, price)]


def full_recent(values, *, first=590):
    return [bar(first + i, value) for i, value in enumerate(values)]


def classify(today, previous=None, as_of=600):
    return entry.classify_state_v3(
        "2025-06-02", as_of, today,
        flat_previous() if previous is None else previous,
        "2025-05-30",
    )


class ClassifierUnitTests(unittest.TestCase):
    def test_stable_vocabulary_and_partition_examples(self):
        rise = [bar(540, 100, 100), bar(589, 100), bar(599, 100.2)]
        sharp_rise = [bar(540, 100, 100), bar(570, 100)] + full_recent(
            [100, 100, 100, 100, 100, 100, 100.4, 100.8, 101.2, 101.6]
        )
        sharp_drop = [bar(540, 100, 100), bar(570, 100)] + full_recent(
            [100, 100, 100, 100, 100, 100, 99.6, 99.2, 98.8, 98.4]
        )
        rise_stop = [bar(540, 100, 100), bar(550, 100.3), bar(580, 101)] + full_recent([101] * 10)
        drop_stop = [bar(540, 100, 100), bar(550, 99.7), bar(580, 99)] + full_recent([99] * 10)
        pullback = [bar(540, 100, 100), bar(550, 101), bar(580, 102)] + full_recent(
            [102] * 5 + [101.9, 101.8, 101.7, 101.6, 101.5]
        )
        rebound = [bar(540, 100, 100), bar(550, 99), bar(580, 98)] + full_recent(
            [98] * 5 + [98.1, 98.2, 98.3, 98.4, 98.5]
        )
        drop = [bar(540, 100, 100), bar(589, 100), bar(599, 99.8)]
        range_ = [bar(540, 100, 100)] + full_recent([100] * 10)
        examples = {
            "RISE": rise, "SHARP_RISE": sharp_rise, "RISE_STOP": rise_stop,
            "PULLBACK": pullback, "RANGE": range_, "REBOUND": rebound,
            "SHARP_DROP": sharp_drop, "DROP": drop, "DROP_STOP": drop_stop,
        }
        self.assertEqual(set(examples), set(entry.PATTERNS))
        for expected, today in examples.items():
            with self.subTest(expected=expected):
                self.assertEqual(classify(today)["state"], expected)

    def test_reversal_equality_is_full_not_partial(self):
        # E rises 1%; R falls exactly the same log magnitude.
        today = [bar(540, 100, 100), bar(550, 100.5), bar(580, 101)] + full_recent(
            [101] * 5 + [100.8, 100.6, 100.4, 100.2, 100]
        )
        self.assertEqual(classify(today)["state"], "DROP")

    def test_future_or_current_bar_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "FUTURE_OR_UNCLOSED_BAR"):
            classify([bar(540, 100), bar(600, 101)], as_of=600)

    def test_invalid_is_null_not_tenth_state(self):
        result = entry.classify_state_v3("2025-06-02", 600, [], [], None)
        self.assertIsNone(result["state"])
        self.assertEqual(result["stateStatus"], "NOT_COMPUTED")
        self.assertEqual(result["dataQuality"], "INVALID")
        self.assertNotIn("INVALID", entry.PATTERNS)

    def test_sparse_current_path_carries_prior_direction(self):
        previous = [bar(540, 100), bar(541, 100.2), bar(542, 100.4)]
        result = classify([bar(540, 101, 101)], previous=previous)
        self.assertEqual(result["state"], "RISE")
        self.assertEqual(result["dataQuality"], "DEGRADED")
        self.assertEqual(result["confidence"], "LOW")

    def test_total_and_deterministic_on_synthetic_valid_paths(self):
        rng = random.Random(570923)
        for case in range(100):
            price = 100.0
            today = [bar(540, price, price)]
            for minute in range(550, 600):
                if rng.random() < .35:
                    price *= math.exp(rng.uniform(-.004, .004))
                    today.append(bar(minute, price))
            first = classify(today)
            second = classify(today)
            with self.subTest(case=case):
                self.assertIn(first["state"], entry.PATTERNS)
                self.assertEqual(first, second)


class PolicyUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    @staticmethod
    def minute_row(minute, delay, firing=()):
        return {
            "minute": minute,
            "delay": delay,
            "signals": {
                family: {"trigger": family in firing} for family in entry.FAMILIES
            },
        }

    @staticmethod
    def state_row(minute, delay, state):
        return {"asOf": minute, "delay": delay, "state": state}

    def test_buy_and_wait_sets_exactly_partition_nine(self):
        self.assertEqual(tuple(self.policy["buyStates"]), entry.BUY_STATES)
        self.assertEqual(tuple(self.policy["waitStates"]), entry.WAIT_STATES)
        self.assertEqual(set(entry.BUY_STATES) | set(entry.WAIT_STATES), set(entry.PATTERNS))
        self.assertFalse(set(entry.BUY_STATES) & set(entry.WAIT_STATES))

    def test_initial_buy_has_priority_and_preserves_signal_source(self):
        rows = [self.minute_row(600, 0, ("BREAKOUT",))]
        states = [self.state_row(600, 0, "RISE")]
        intent = entry.frozen_intent("x", rows, states, self.policy)
        self.assertEqual(intent["intentReason"], "INITIAL_STATE_BUY")
        self.assertEqual(intent["triggerSources"], ["INITIAL_STATE_BUY", "SIGNAL_TRIGGER"])

    def test_wait_tie_uses_signal_primary_without_time_change(self):
        rows = [
            self.minute_row(600, 0),
            self.minute_row(605, 5, ("RECLAIM",)),
        ]
        states = [
            self.state_row(600, 0, "DROP"),
            self.state_row(605, 5, "REBOUND"),
        ]
        intent = entry.frozen_intent("x", rows, states, self.policy)
        self.assertEqual(intent["intentMinute"], 605)
        self.assertEqual(intent["intentReason"], "SIGNAL_TRIGGER")
        self.assertEqual(intent["triggerSources"], ["SIGNAL_TRIGGER", "STATE_TRANSITION_BUY"])

    def test_signal_can_lead_state_and_state_can_rescue(self):
        base = [self.state_row(600, 0, "DROP"), self.state_row(605, 5, "REBOUND")]
        signal_rows = [self.minute_row(600, 0), self.minute_row(602, 2, ("LOWER_WICK",)), self.minute_row(605, 5)]
        signal = entry.frozen_intent("x", signal_rows, base, self.policy)
        self.assertEqual((signal["intentReason"], signal["intentMinute"]), ("SIGNAL_TRIGGER", 602))
        state_rows = [self.minute_row(600, 0), self.minute_row(605, 5)]
        state = entry.frozen_intent("x", state_rows, base, self.policy)
        self.assertEqual((state["intentReason"], state["intentMinute"]), ("STATE_TRANSITION_BUY", 605))

    def test_no_trigger_means_no_intent_and_no_fallback(self):
        rows = [self.minute_row(600, 0), self.minute_row(605, 5), self.minute_row(610, 10)]
        states = [self.state_row(600, 0, "DROP"), self.state_row(605, 5, "RANGE"), self.state_row(610, 10, "DROP_STOP")]
        intent = entry.frozen_intent("x", rows, states, self.policy)
        self.assertIsNone(intent["intentMinute"])
        self.assertIsNone(intent["intentReason"])
        self.assertFalse(self.policy["fixedTimeFallback"])

    def test_safety_and_scope_lock(self):
        self.assertEqual(len(self.policy["safety"]), 9)
        self.assertTrue(all(value is False for value in self.policy["safety"].values()))
        self.assertEqual(self.policy["providerRequestsAuthorized"], 0)
        self.assertEqual(self.policy["protectedDataOpened"], 0)


class LockedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (MEASUREMENT / "summary.json").exists():
            raise unittest.SkipTest("measurement not frozen yet")
        cls.summary = json.loads((MEASUREMENT / "summary.json").read_text(encoding="utf-8"))
        with gzip.open(MEASUREMENT / "entry-records.json.gz", "rt", encoding="utf-8") as fh:
            cls.records = json.load(fh)

    def test_population_reasons_and_no_fallback(self):
        self.assertEqual(len(self.records), 2155)
        self.assertEqual(len({row["opportunity"] for row in self.records}), 2155)
        self.assertEqual(sum(self.summary["state"]["t0Counts"].values()), 2155)
        self.assertEqual(sum(self.summary["triggers"]["finalEntryReason"].values()), 2155)
        self.assertNotIn("FALLBACK", self.summary["triggers"]["causalIntentReason"])

    def test_manifest_and_deterministic_artifacts(self):
        manifest = json.loads((MEASUREMENT / "manifest.json").read_text(encoding="utf-8"))
        actual = sorted(path.name for path in MEASUREMENT.iterdir() if path.name != "manifest.json")
        self.assertEqual(sorted(manifest), actual)
        for name, expected in manifest.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((MEASUREMENT / name).read_bytes()).hexdigest(), expected)

    def test_namespace_manifest_when_frozen(self):
        manifest_path = EVIDENCE / "MANIFEST.json"
        if not manifest_path.exists():
            self.skipTest("namespace manifest not frozen yet")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(manifest["population"], 2155)
        for relative, expected in manifest["files"].items():
            with self.subTest(relative=relative):
                self.assertEqual(
                    hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
                    expected,
                )

    def test_causality_baseline_identity_and_safety(self):
        self.assertEqual(self.summary["lookAheadAudit"]["status"], "PASS")
        self.assertEqual(self.summary["baselineParity"]["status"], "PASS")
        self.assertEqual(self.summary["initialBuyImmediateIdentityAudit"]["status"], "PASS")
        self.assertEqual(self.summary["providerRequests"], 0)
        self.assertEqual(self.summary["protectedDataOpened"], 0)
        self.assertTrue(all(value is False for value in self.summary["safety"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
