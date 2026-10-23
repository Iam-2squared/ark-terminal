"""Synthetic, stdlib-only tests for frozen P1/Q70 first-intent replay."""

from array import array
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/no11_frozen_p1_first_cross.py"
SPEC = importlib.util.spec_from_file_location("no11_frozen_p1_first_cross", MODULE_PATH)
FIRST_CROSS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIRST_CROSS)


class FirstCrossTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.watch_path = root / "WATCH_RECORDS.jsonl.gz"
        self.grid_path = root / "PERSISTENT_GRID.jsonl.gz"
        self.intent_path = root / "FIRST_INTENTS_PRIVATE.jsonl.gz"
        self.day = "2025-06-02"
        self.watches = [self.watch("A"), self.watch("B"), self.watch("C", False),
                        self.watch("D")]
        self.grid = [self.grid_row("A", 600), self.grid_row("B", 600),
                     self.grid_row("C", 600, False), self.grid_row("A", 601),
                     self.grid_row("B", 601), self.grid_row("A", 602),
                     self.grid_row("B", 602)]
        self.indices = [0, 1, 3, 4, 5, 6]
        self.scores = [.4, .1, .5, .2, .9, .4]
        self.folds = [1] * len(self.indices)
        selected = {"row_index": 3, "fold": 1,
                    "intent_timestamp": self.timestamp(601), "score": .5,
                    "threshold": .5}
        self.expected = [self.intent("A", selected, 2), self.intent("B", None, 3),
                         self.intent("D", None, 0)]
        self.thresholds = {1: .5}
        self.sessions = {1: {self.day}}

    def timestamp(self, minute):
        return f"{self.day}T{minute // 60:02d}:{minute % 60:02d}:00+09:00"

    def watch(self, symbol, canonical=True):
        return {"watch_key": self.day + "|" + symbol, "session": self.day,
                "symbol": symbol, "canonical": canonical}

    def grid_row(self, symbol, minute, canonical=True):
        row = self.watch(symbol, canonical)
        row.update(row_id=row["watch_key"] + "|" + str(minute),
                   intent_minute=minute, intent_timestamp=self.timestamp(minute),
                   feature_max_timestamp=self.timestamp(minute))
        return row

    def intent(self, symbol, selected, decisions):
        return {"watch_key": self.day + "|" + symbol, "session": self.day,
                "symbol": symbol, "family": "P1", "policy": "Q70",
                "first_intent": selected, "scoring_decisions": decisions,
                "threshold_trace_sha256": "deliberately-not-compared"}

    @staticmethod
    def write(path, rows):
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")

    def run_replay(self):
        self.write(self.watch_path, self.watches)
        self.write(self.grid_path, self.grid)
        self.write(self.intent_path, self.expected)
        return FIRST_CROSS.replay_and_compare(
            self.watch_path, self.grid_path, self.intent_path,
            self.indices, self.scores, self.folds, self.thresholds, self.sessions)

    def test_full_first_cross_equality_lock_and_zero_row_watch(self):
        result = self.run_replay()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["canonical_watch_count"], 3)
        self.assertEqual(result["canonical_grid_row_count"], 6)
        self.assertEqual(result["scoring_decisions"], 5)
        self.assertEqual(result["rows_after_first_intent_lock"], 1)
        self.assertEqual(result["replayed_first_intent_count"], 1)
        self.assertEqual(result["replayed_no_intent_count"], 2)
        self.assertFalse(result["threshold_trace_sha256_compared"])
        self.assertEqual(result["private_rows_returned"], 0)
        self.assertNotIn(self.day, json.dumps(result))

    def test_sized_nonlist_arrays_are_accepted_without_numpy(self):
        self.indices = array("q", self.indices)
        self.scores = array("d", self.scores)
        self.folds = array("i", self.folds)
        self.assertTrue(self.run_replay()["parity_passed"])

    def test_expected_other_families_and_policies_are_ignored(self):
        extra = deepcopy(self.expected[0])
        extra.update(family="P0", first_intent="unused")
        self.expected.append(extra)
        extra = deepcopy(extra)
        extra.update(family="P1", policy="Q80")
        self.expected.append(extra)
        self.assertEqual(self.run_replay()["expected_p1_q70_record_count"], 3)

    def test_expected_is_opened_only_after_grid_is_fully_read(self):
        events = []
        original = FIRST_CROSS._rows

        def tracked(path, label):
            events.append((label, "open"))
            yield from original(path, label)
            events.append((label, "complete"))

        with mock.patch.object(FIRST_CROSS, "_rows", tracked):
            self.assertTrue(self.run_replay()["parity_passed"])
        self.assertLess(events.index(("GRID", "complete")),
                        events.index(("EXPECTED_INTENT", "open")))

    def test_expected_cannot_move_the_replayed_first_cross(self):
        self.expected[0]["first_intent"].update(
            row_index=5, intent_timestamp=self.timestamp(602), score=.9)
        result = self.run_replay()
        self.assertFalse(result["parity_passed"])
        self.assertEqual(result["replayed_first_intent_count"], 1)
        self.assertEqual(result["scoring_decisions"], 5)
        for key in ("row_index", "intent_timestamp", "score"):
            self.assertEqual(result["mismatch_counts"][key], 1)

    def test_tolerance_is_absolute_and_does_not_change_crossing(self):
        self.expected[0]["first_intent"]["score"] += 5e-13
        self.expected[0]["first_intent"]["threshold"] -= 5e-13
        self.assertTrue(self.run_replay()["parity_passed"])
        self.expected[0]["first_intent"]["score"] += 2e-12
        self.assertEqual(self.run_replay()["mismatch_counts"]["score"], 1)
        self.expected[0]["first_intent"]["score"] = .5
        self.scores[2] = .5 - 5e-13
        result = self.run_replay()
        self.assertEqual(result["mismatch_counts"]["row_index"], 1)
        self.assertEqual(result["scoring_decisions"], 6)

    def test_missing_duplicate_and_unexpected_expected_watches(self):
        self.expected.pop()
        self.expected.append(deepcopy(self.expected[0]))
        self.expected.append(self.intent("PRIVATE_SYMBOL_MUST_NOT_LEAK", None, 0))
        result = self.run_replay()
        for key in ("missing_expected_watch", "duplicate_expected_watch",
                    "unexpected_expected_watch"):
            self.assertEqual(result["mismatch_counts"][key], 1)
        self.assertNotIn("PRIVATE_SYMBOL_MUST_NOT_LEAK", json.dumps(result))

    def test_no_threshold_cross_is_compared(self):
        self.expected[0]["first_intent"] = None
        result = self.run_replay()
        self.assertEqual(result["mismatch_counts"]["first_intent_presence"], 1)

    def test_missing_row_after_lock_still_rejects_partial_replay(self):
        for values in (self.indices, self.scores, self.folds):
            values.pop(4)
        with self.assertRaisesRegex(ValueError, "CANONICAL_GRID_COVERAGE_INCOMPLETE"):
            self.run_replay()

    def test_future_feature_is_rejected_even_after_lock(self):
        self.grid[5]["feature_max_timestamp"] = self.timestamp(603)
        with self.assertRaisesRegex(ValueError, "FEATURE_TIMESTAMP_AFTER_INTENT"):
            self.run_replay()

    def test_wrong_fold_session_has_no_automatic_dispatch(self):
        self.sessions = {1: {"2025-06-03"}}
        with self.assertRaisesRegex(ValueError, "ROW_FOLD_TEST_SESSION_MISMATCH"):
            self.run_replay()

    def test_overlap_between_fold_test_sessions_is_rejected(self):
        self.thresholds[2] = .6
        self.sessions[2] = {self.day}
        with self.assertRaisesRegex(ValueError, "INVALID_FOLD_SESSIONS"):
            self.run_replay()

    def test_unordered_or_duplicate_row_indices_are_rejected(self):
        for indices in ([0, 1, 3, 3, 5, 6], [0, 3, 1, 4, 5, 6]):
            with self.subTest(indices=indices):
                self.indices = indices
                with self.assertRaisesRegex(ValueError, "ROW_INDICES_NOT_STRICTLY_INCREASING"):
                    self.run_replay()

    def test_noncanonical_row_cannot_be_scored(self):
        self.indices.insert(2, 2)
        self.scores.insert(2, .8)
        self.folds.insert(2, 1)
        with self.assertRaisesRegex(ValueError, "NONCANONICAL_GRID_ROW_SELECTED"):
            self.run_replay()

    def test_unknown_canonical_watch_is_not_created_from_grid(self):
        self.grid[0]["watch_key"] = self.day + "|PRIVATE_UNKNOWN"
        with self.assertRaisesRegex(ValueError, "GRID_CANONICAL_WATCH_NOT_FOUND") as caught:
            self.run_replay()
        self.assertNotIn("PRIVATE_UNKNOWN", str(caught.exception))

    def test_duplicate_canonical_watch_is_rejected(self):
        self.watches.append(deepcopy(self.watches[0]))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_INVALID_WATCH_IDENTITY"):
            self.run_replay()

    def test_nonfinite_score_is_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                self.scores[0] = value
                with self.assertRaisesRegex(ValueError, "INVALID_ROW_SCORE"):
                    self.run_replay()

    def test_nonchronological_watch_row_is_rejected(self):
        self.grid[5]["intent_timestamp"] = self.timestamp(601)
        self.grid[5]["feature_max_timestamp"] = self.timestamp(601)
        with self.assertRaisesRegex(ValueError, "WATCH_GRID_NOT_STRICTLY_CHRONOLOGICAL"):
            self.run_replay()

    def test_out_of_grid_index_and_array_length_mismatch(self):
        self.indices.append(100)
        self.scores.append(.6)
        self.folds.append(1)
        with self.assertRaisesRegex(ValueError, "ROW_INDEX_OUTSIDE_GRID"):
            self.run_replay()
        self.folds.pop()
        with self.assertRaisesRegex(ValueError, "ROW_ARRAY_LENGTH_MISMATCH"):
            self.run_replay()


if __name__ == "__main__":
    unittest.main()
