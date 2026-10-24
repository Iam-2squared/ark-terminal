"""P1 candidate -> genuine original State9 Path trace -> H235 as-of Shadow hook.

Synthetic score stubs only; original 24 private model weights never appear in CI.
"""
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_frozen_p1_feature_runtime as features
import no11_p1_forward_shadow as forward
import no11_rss_state9_p1_runner as bridge
import no11_h235_asof_forward_shadow as h
import test_no11_frozen_p1_rss_state_stream as old


class StubR0:
    def __init__(self, error=None):
        self.policy = h.policy(old.DAY)
        self.original_model_count = 24
        _, _, self.stair, _ = h.original_dependencies()
        self.inputs = []
        self.error = error

    def score(self, event):
        self.inputs.append(event)
        if self.error:
            raise ValueError(self.error)
        return {
            "candidateId": event["candidateId"], "symbol": event["symbol"],
            "entry_timestamp": event["firstIntentAtJst"], "raw_reference": event["referencePrice"],
            "ML": 1.1, "m5": .3, "m3": .4, "m2": .5, "rank": "B",
            "admission": True, "capital_score": 1.1, "selectedBlock": 8,
            "orderTransmission": False, "productionReady": False,
        }


class ReceivedTraceWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = features.load_feature_runtime(forward.REPO)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = root
        self.original = old.RecordingScorer()
        self.p1 = forward.ForwardP1Session(root / "p1.sqlite", self.original)

    def tearDown(self):
        self.p1.close()
        self.temp.cleanup()

    def run_bridge(self, r0):
        return bridge.consume_received_feed(
            self.runtime, self.p1, old.feed(), old.selectors(), old.previous(),
            previous_session=old.PRIOR, through=old.at(580, 0),
            h235=r0, h235_store=self.store)

    def test_original_state_path_stream_reaches_asof_h235_after_p1_first_cross(self):
        r0 = StubR0()
        summary = self.run_bridge(r0)
        self.assertEqual(summary["counts"]["h235R0Candidates"], 1)
        self.assertEqual(summary["h235OriginalModelMembersVerified"], 24)
        self.assertEqual(summary["h235OriginalModelExecutions"], 3)
        self.assertFalse(summary["capitalExecuted"])
        self.assertEqual(len(r0.inputs), 1)
        item = r0.inputs[0]
        self.assertEqual(item["sourceKind"], "RSS_CUMULATIVE_PROXY")
        self.assertLessEqual(item["referenceKnownAtJst"], item["decisionAtJst"])
        self.assertEqual(item["referenceBarEndJst"], item["firstIntentAtJst"])
        self.assertEqual(len(item["stateTrace"]), 31)
        self.assertEqual(item["stateTrace"][-1]["path"]["scheduled_t"], 31)
        self.assertEqual(item["stateTrace"][-1]["state"]["as_of"], 31)
        self.assertEqual(item["stateTrace"][-1]["bar_end_minute"], 571)
        for row in item["stateTrace"]:
            self.assertNotIn("fill_price", row)
            self.assertNotIn("teacher", row)
        saved = list(self.store.glob("h235-asof-*.json"))
        self.assertEqual(len(saved), 1)
        doc = json.loads(saved[0].read_text())
        self.assertEqual(len(doc["results"]), 1)
        self.assertFalse(doc["orderTransmission"])
        self.assertEqual(doc["results"][0]["selectedBlock"], 8)

    def test_scoring_block_only_leaves_locked_p1_without_any_h235_funding(self):
        r0 = StubR0("NO11_H235_FROZEN_ENTRY_STATE_EXCLUDED_OR_UNAVAILABLE")
        summary = self.run_bridge(r0)
        self.assertEqual(summary["counts"]["h235BlockedUnavailableOrExcludedState"], 1)
        self.assertEqual(summary["h235OriginalModelExecutions"], 0)
        self.assertEqual(summary["p1Session"]["firstEntryCandidates"], 1)
        self.assertFalse(summary["capitalExecuted"])
        stored = list(self.store.glob("h235-asof-*.json"))
        self.assertEqual(len(stored), 1)
        self.assertEqual(json.loads(stored[0].read_text())["results"], [])

    def test_unexpected_h235_model_fault_fails_closed_no_rank_is_fabricated(self):
        r0 = StubR0("NO11_H235_MODEL_PREDICTION_NONFINITE")
        with self.assertRaisesRegex(ValueError, "NO11_H235_MODEL_PREDICTION_NONFINITE"):
            self.run_bridge(r0)
        self.assertEqual(list(self.store.glob("h235-asof-*.json")), [])
        self.assertEqual(self.p1.summary()["firstEntryCandidates"], 1)

    def test_idempotent_replay_creates_no_new_rank_file_or_p1_candidate(self):
        r0 = StubR0()
        first = self.run_bridge(r0)
        before = list(self.store.glob("h235-asof-*.json"))
        self.p1.close()
        self.p1 = forward.ForwardP1Session(self.store / "p1.sqlite", self.original)
        second = self.run_bridge(r0)
        after = list(self.store.glob("h235-asof-*.json"))
        self.assertEqual(first["h235PrivateResultSha256"], second["h235PrivateResultSha256"])
        self.assertEqual(before, after)
        self.assertEqual(second["p1Session"]["firstEntryCandidates"], 1)
        self.assertEqual(self.original.calls, 2)


if __name__ == "__main__":
    unittest.main()
