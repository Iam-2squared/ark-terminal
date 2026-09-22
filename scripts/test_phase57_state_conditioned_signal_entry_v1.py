"""Dedicated invariants for Phase57 State-Conditioned Signal Entry v1."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase57_state_conditioned_signal_entry_v1 as entry  # noqa: E402


EVIDENCE = ROOT / "docs/evidence/phase57-state-conditioned-signal-entry-v1"
MEASUREMENT = EVIDENCE / "measurement"
POLICY = EVIDENCE / "POLICY_LOCK.json"
POLICY_SHA256 = "794a1ff0c1dd43a145b6cc0c990572c5f343042db1a86523d7d457c0fcdfa3d3"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def causal_row(value, *, minute=600, through=599):
    return {
        "minute": minute,
        "computedThroughBarStart": through,
        "context": {"returnPct": {"5": value}},
    }


class DecisionUnitTests(unittest.TestCase):
    def test_sign_mapping_is_fixed(self):
        self.assertEqual(entry.estimate_state(causal_row(0.01)), "UP")
        self.assertEqual(entry.estimate_state(causal_row(-0.01)), "DOWN")
        self.assertEqual(entry.estimate_state(causal_row(0.0)), "NEUTRAL")
        self.assertEqual(entry.estimate_state(causal_row(None)), "UNKNOWN")

    def test_missing_is_preserved_not_coerced_false(self):
        self.assertEqual(entry.estimate_state(causal_row(None)), "UNKNOWN")
        self.assertNotEqual(entry.estimate_state(causal_row(None)), "DOWN")
        self.assertNotEqual(entry.estimate_state(causal_row(None)), "NEUTRAL")

    def test_current_or_future_bar_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "FUTURE_OR_UNCLOSED_BAR"):
            entry.estimate_state(causal_row(1.0, minute=600, through=600))
        with self.assertRaisesRegex(ValueError, "FUTURE_OR_UNCLOSED_BAR"):
            entry.estimate_state(causal_row(1.0, minute=600, through=601))

    def test_every_forbidden_payload_key_is_rejected(self):
        for field in entry.FORBIDDEN_DECISION_TOKENS:
            row = causal_row(1.0)
            row[field] = None
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "FORBIDDEN_DECISION_PAYLOAD"):
                    entry.estimate_state(row)

    def test_policy_routes_each_state_to_prelocked_arm(self):
        policy = json.loads(POLICY.read_text())
        expected = {
            "UP": ("A", "BUY_NOW"),
            "DOWN": ("D", "WAIT_RECOVERY_SIGNAL"),
            "NEUTRAL": ("C", "WAIT_UPWARD_TRANSITION_SIGNAL"),
            "UNKNOWN": ("E", "WAIT_ANY_EXISTING_SIGNAL"),
        }
        values = {"UP": 1.0, "DOWN": -1.0, "NEUTRAL": 0.0, "UNKNOWN": None}
        for state, value in values.items():
            selected = entry.select_policy_arm(causal_row(value), policy)
            with self.subTest(state=state):
                self.assertEqual(selected["state"], state)
                self.assertEqual((selected["sourceArm"], selected["action"]), expected[state])

    def test_deterministic_gzip_encoding(self):
        with tempfile.TemporaryDirectory() as temp:
            left = Path(temp) / "left.json.gz"
            right = Path(temp) / "right.json.gz"
            value = [{"z": 1, "a": [3, 2, 1]}]
            entry.write_gzip_json(left, value)
            entry.write_gzip_json(right, value)
            self.assertEqual(left.read_bytes(), right.read_bytes())


class LockedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text())
        cls.summary = json.loads((MEASUREMENT / "summary.json").read_text())
        with gzip.open(MEASUREMENT / "entry-records.json.gz", "rt", encoding="utf-8") as fh:
            cls.candidate = json.load(fh)
        with gzip.open(MEASUREMENT / "baseline-immediate-records.json.gz", "rt", encoding="utf-8") as fh:
            cls.immediate = json.load(fh)

    def test_policy_lock_hash_and_safety(self):
        self.assertEqual(digest(POLICY), POLICY_SHA256)
        self.assertEqual(set(self.policy["safety"]), set(entry.SAFETY_KEYS))
        self.assertEqual(len(self.policy["safety"]), 9)
        self.assertTrue(all(value is False for value in self.policy["safety"].values()))
        self.assertEqual(self.policy["providerRequestsAuthorized"], 0)
        self.assertEqual(self.policy["protectedDataOpened"], 0)

    def test_manifest_hashes_every_measurement_file(self):
        manifest = json.loads((MEASUREMENT / "manifest.json").read_text())
        names = sorted(path.name for path in MEASUREMENT.iterdir() if path.name != "manifest.json")
        self.assertEqual(sorted(manifest), names)
        for name, expected in manifest.items():
            with self.subTest(name=name):
                self.assertEqual(digest(MEASUREMENT / name), expected)

    def test_population_and_unknown_are_preserved(self):
        self.assertEqual(len(self.candidate), 2155)
        self.assertEqual(len({row["opportunity"] for row in self.candidate}), 2155)
        counts = {state: 0 for state in entry.STATES}
        for row in self.candidate:
            counts[row["initialState"]] += 1
        self.assertEqual(counts, {"UP": 218, "DOWN": 717, "NEUTRAL": 76, "UNKNOWN": 1144})
        self.assertEqual(sum(not row["entryId"] for row in self.candidate), 298)

    def test_state_arm_assignment_has_no_posthoc_override(self):
        expected = {"UP": "A", "DOWN": "D", "NEUTRAL": "C", "UNKNOWN": "E"}
        for row in self.candidate:
            with self.subTest(opportunity=row["opportunity"]):
                self.assertEqual(row["sourceArm"], expected[row["initialState"]])

    def test_up_buy_now_is_exact_immediate_identity(self):
        fields = ("entryId", "entryMinute", "price", "delay", "intentMinute",
                  "intentReason", "unfilledReason")
        compared = 0
        for baseline, candidate in zip(self.immediate, self.candidate):
            self.assertEqual(baseline["opportunity"], candidate["opportunity"])
            if candidate["initialState"] != "UP":
                continue
            compared += 1
            self.assertTrue(all(baseline[field] == candidate[field] for field in fields))
        self.assertEqual(compared, 218)

    def test_audits_and_old_baseline_parity_pass(self):
        audit = self.summary["lookAheadAudit"]
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["checkpointAssertions"], 377450)
        self.assertEqual(audit["closedBarAssertionsPassed"], 377450)
        self.assertEqual(audit["higherLowPivotBackdatingViolations"], 0)
        self.assertGreater(audit["higherLowPivotTimestampAssertions"], 0)
        self.assertGreater(audit["missingSignalValuesPreserved"], 0)
        self.assertTrue(audit["evaluatorInputsParsedAfterAllDecisions"])
        self.assertFalse(audit["oracleUsedByDecision"])
        self.assertFalse(audit["futureOutcomeUsedByDecision"])
        self.assertFalse(audit["stateV2ReferenceUsedByDecision"])
        self.assertEqual(self.summary["baselineParity"]["status"], "PASS")
        self.assertTrue(all(check["pass"] for check in self.summary["baselineParity"]["checks"]))

    def test_reference_join_and_decision_coverage(self):
        diagnostic = self.summary["stateDiagnostics"]
        self.assertEqual(diagnostic["signalCensusCheckpointPopulation"], 377450)
        self.assertEqual(diagnostic["stateV2ReferenceJoinedCheckpoints"], 77214)
        self.assertEqual(diagnostic["decisionPopulation"], 2155)
        self.assertEqual(sum(diagnostic["estimatorDecisionCounts"].values()), 2155)

    def test_result_safety_and_scope(self):
        self.assertEqual(set(self.summary["safety"]), set(entry.SAFETY_KEYS))
        self.assertTrue(all(value is False for value in self.summary["safety"].values()))
        self.assertEqual(self.summary["providerRequests"], 0)
        self.assertEqual(self.summary["protectedDataOpened"], 0)
        self.assertEqual(self.summary["studyStatus"], "DEVELOPMENT_ENTRY_V1_COMPLETE_NO_PROMOTION")


if __name__ == "__main__":
    unittest.main(verbosity=2)
