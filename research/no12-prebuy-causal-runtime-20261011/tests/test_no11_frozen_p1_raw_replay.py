"""Synthetic complete-watch replay tests; no private originals or model fitting.

Exercise causal decisions and comparison independence, including a small
orchestrated replay whose saved references cannot provide scorer inputs.
"""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import gzip
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np


TOOLS = Path(__file__).resolve().parents[1] / "tools"
SPEC = importlib.util.spec_from_file_location("p1_raw_replay_under_test", TOOLS / "no11_frozen_p1_raw_replay.py")
RAW = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(TOOLS))
try:
    SPEC.loader.exec_module(RAW)
finally:
    sys.path.pop(0)


DAY_A, DAY_B = "2025-06-02", "2025-06-03"


def watch(symbol, day=DAY_A, canonical=True):
    return {"watch_key": day + "|" + symbol, "session": day,
            "symbol": symbol, "canonical": canonical}


def timestamp(minute, day=DAY_A):
    return f"{day}T{minute // 60:02d}:{minute % 60:02d}:00+09:00"


def grid_row(record, minute, watch_index=0):
    row = dict(record)
    row.update(watch_index=watch_index, intent_minute=minute,
               intent_timestamp=timestamp(minute, record["session"]),
               feature_max_timestamp=timestamp(minute, record["session"]),
               closed_raw_start=minute - 1)
    return row


def expected_row(record, first, decisions):
    return dict(record, family="P1", policy="Q70", first_intent=first,
                scoring_decisions=decisions)


class Files(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write_rows(self, name, rows):
        path = self.root / name
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, allow_nan=False) + "\n")
        return path

    def write_object(self, name, value):
        path = self.root / name
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            json.dump(value, stream, allow_nan=False)
        return path


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.watches = [watch("NONCANONICAL", "2026-10-23", False),
                        watch("EMPTY"), watch("A_FIRST"), watch("A_LATER"),
                        watch("B_FIRST", DAY_B), watch("B_LATER", DAY_B)]
        self.ranges = np.array([[0, 2], [2, 2], [2, 5], [5, 7], [7, 11], [11, 12]])
        self.sessions = {1: {DAY_A}, 2: {DAY_B}}

    def test_selection_cannot_read_outcomes_and_preserves_original_order(self):
        class NoOutcomeReads(dict):
            allowed = {"watch_key", "session", "symbol", "canonical"}

            def __getitem__(self, key):
                if key not in self.allowed:
                    raise AssertionError("OUTCOME_FIELD_READ_DURING_SELECTION")
                return super().__getitem__(key)

            def get(self, key, default=None):
                if key not in self.allowed:
                    raise AssertionError("OUTCOME_FIELD_READ_DURING_SELECTION")
                return super().get(key, default)

        protected = [NoOutcomeReads(w, score=object(), target=object(), first_intent=object())
                     for w in self.watches]
        selected = RAW.select_watches(protected, self.ranges, self.sessions)
        self.assertEqual([x["watch_index"] for x in selected], [2, 4])
        self.assertEqual([(x["lo"], x["hi"]) for x in selected], [(2, 5), (7, 11)])
        again = RAW.select_watches(protected, self.ranges, dict(reversed(list(self.sessions.items()))))
        self.assertEqual([x["watch_index"] for x in again], [2, 4])
        twice = RAW.select_watches(protected, self.ranges, self.sessions, per_fold=2)
        self.assertEqual([x["watch_index"] for x in twice], [2, 3, 4, 5])

    def test_unknown_2026_canonical_session_cannot_get_a_frozen_fold(self):
        self.watches[-1] = watch("LIVE", "2026-10-23")
        # Earlier watches already satisfy the requested sample. An unknown
        # canonical session later in the input must still be rejected.
        with self.assertRaisesRegex(ValueError, "CANONICAL_SESSION_OUTSIDE_FROZEN_SPLIT"):
            RAW.select_watches(self.watches, self.ranges, self.sessions)

    def test_no_partial_fold_sample_and_no_overlapping_session_dispatch(self):
        with self.assertRaisesRegex(ValueError, "WHOLE_WATCH_SAMPLE_INCOMPLETE"):
            RAW.select_watches(self.watches, self.ranges, self.sessions, per_fold=3)
        with self.assertRaisesRegex(ValueError, "SAVED_TEST_SESSIONS_OVERLAP"):
            RAW.select_watches(self.watches, self.ranges, {1: {DAY_A}, 2: {DAY_A, DAY_B}})

    def test_range_gap_or_overlap_cannot_select_partial_watch_rows(self):
        for start in (1, 3):
            ranges = self.ranges.copy()
            ranges[2, 0] = start
            with self.subTest(start=start):
                with self.assertRaisesRegex(ValueError, "WATCH_RANGES_NOT_CONTIGUOUS"):
                    RAW.select_watches(self.watches, ranges, self.sessions)


class GridAndDecisionTests(Files):
    def setUp(self):
        super().setUp()
        self.watch = watch("A")
        self.item = {"watch_index": 2, "watch": self.watch, "lo": 10, "hi": 14, "fold": 1}
        self.grid = [grid_row(self.watch, minute, 2) for minute in range(600, 604)]
        self.sessions = {1: {DAY_A}}

    def derive(self, scores, grid=None):
        return RAW.derive_first_intent(self.item, self.grid if grid is None else grid,
                                      scores, .5, self.sessions)

    def test_whole_grid_selection_retains_rows_after_first_possible_cross(self):
        prefix = [grid_row(watch("IGNORED"), 500, 0)] * 10
        path = self.write_rows("grid.gz", prefix + self.grid + [grid_row(watch("TAIL"), 700, 3)])
        actual = RAW.selected_grid(path, [self.item])
        self.assertEqual(actual[2], self.grid)
        truncated = self.write_rows("short-grid.gz", prefix + self.grid[:-1])
        with self.assertRaisesRegex(ValueError, "WHOLE_WATCH_GRID_COVERAGE_INCOMPLETE"):
            RAW.selected_grid(truncated, [self.item])

    def test_selected_grid_rejects_other_watch_at_an_expected_position(self):
        rows = [grid_row(watch("IGNORED"), 500, 0)] * 10 + deepcopy(self.grid)
        rows[12]["symbol"] = "OTHER"
        path = self.write_rows("wrong-watch.gz", rows)
        with self.assertRaisesRegex(ValueError, "SELECTED_GRID_WATCH_MISMATCH"):
            RAW.selected_grid(path, [self.item])

    def test_threshold_equality_enters_and_first_cross_locks_later_decisions(self):
        below = np.nextafter(.5, -np.inf)
        result = self.derive([below, .5, .9, .5])
        self.assertEqual(result["scoring_decisions"], 2)
        self.assertEqual(result["rows_after_lock"], 2)
        self.assertEqual(result["first_intent"], {
            "row_index": 11, "fold": 1, "intent_timestamp": timestamp(601),
            "score": .5, "threshold": .5,
        })

    def test_no_cross_consumes_the_complete_watch(self):
        result = self.derive([.1, .2, .49, np.nextafter(.5, -np.inf)])
        self.assertIsNone(result["first_intent"])
        self.assertEqual(result["scoring_decisions"], 4)
        self.assertEqual(result["rows_after_lock"], 0)

    def test_missing_post_lock_row_or_score_never_counts_as_complete_replay(self):
        for grid, scores in ((self.grid[:-1], [.9] * 3), (self.grid, [.9] * 3)):
            with self.subTest(grid_rows=len(grid), scores=len(scores)):
                with self.assertRaisesRegex(ValueError, "WHOLE_WATCH_DECISION_COVERAGE_INCOMPLETE"):
                    self.derive(scores, grid)

    def test_causality_and_strict_chronology_are_enforced_even_after_lock(self):
        changes = [
            ({"feature_max_timestamp": timestamp(604)}, "GRID_NOT_CAUSAL_OR_CHRONOLOGICAL"),
            ({"intent_timestamp": timestamp(602), "feature_max_timestamp": timestamp(602)},
             "GRID_NOT_CAUSAL_OR_CHRONOLOGICAL"),
            ({"intent_timestamp": timestamp(601), "feature_max_timestamp": timestamp(601)},
             "GRID_NOT_CAUSAL_OR_CHRONOLOGICAL"),
            ({"intent_timestamp": timestamp(603, DAY_B), "feature_max_timestamp": timestamp(603, DAY_B)},
             "GRID_NOT_CAUSAL_OR_CHRONOLOGICAL"),
            ({"intent_timestamp": timestamp(603)[:-6]}, "GRID_CLOCK_WITHOUT_TIMEZONE"),
            ({"closed_raw_start": 603}, "GRID_BAR_END_MISMATCH"),
        ]
        for change, error in changes:
            with self.subTest(error=error, change=change):
                grid = deepcopy(self.grid)
                grid[-1].update(change)
                with self.assertRaisesRegex(ValueError, error):
                    self.derive([.9] * 4, grid)

    def test_invalid_post_lock_score_is_not_silently_skipped(self):
        for bad in (float("nan"), float("inf"), -.01, 1.01):
            with self.subTest(score=bad):
                with self.assertRaisesRegex(ValueError, "SCORE_INVALID"):
                    self.derive([.9, .9, .9, bad])

    def test_decision_boundary_rejects_2026_and_wrong_fold_mapping(self):
        for change in ({"fold": 2}, {"watch": watch("A", "2026-10-23")}):
            item = dict(self.item, **change)
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, "SESSION_OUTSIDE_FROZEN_SPLIT"):
                    RAW.derive_first_intent(item, self.grid, [.9] * 4, .5, self.sessions)


class ComparisonTests(Files):
    def setUp(self):
        super().setUp()
        self.a, self.b = watch("A"), watch("B")
        self.first = {"row_index": 1, "fold": 1, "intent_timestamp": timestamp(601),
                      "score": .5, "threshold": .5}
        self.actual = {
            self.a["watch_key"]: {"session": DAY_A, "symbol": "A", "scoring_decisions": 2,
                                  "first_intent": dict(self.first), "rows_after_lock": 1},
            self.b["watch_key"]: {"session": DAY_A, "symbol": "B", "scoring_decisions": 3,
                                  "first_intent": None, "rows_after_lock": 0},
        }
        self.expected = [expected_row(self.a, dict(self.first), 2), expected_row(self.b, None, 3)]

    def compare(self, expected):
        return RAW.compare_first_intents(self.write_rows("expected.gz", expected), self.actual)

    def test_aggregate_comparison_counts_actual_decisions_and_ignores_other_scopes(self):
        unrelated = [expected_row(watch("UNSELECTED"), None, 99),
                     dict(self.expected[0], family="P0", first_intent="unused"),
                     dict(self.expected[0], policy="Q80", first_intent="unused")]
        result = self.compare(self.expected + unrelated)
        self.assertTrue(result["parityPassed"])
        self.assertEqual(result["comparedWatches"], 2)
        self.assertEqual((result["firstIntents"], result["noIntents"]), (1, 1))
        self.assertEqual(result["scoringDecisions"], 5)
        self.assertEqual(result["rowsAfterFirstIntentLock"], 1)
        for private_value in (DAY_A, self.a["watch_key"], "UNSELECTED"):
            self.assertNotIn(private_value, json.dumps(result))

    def test_changed_expected_intent_cannot_replace_an_actual_decision(self):
        actual_before = deepcopy(self.actual)
        expected = deepcopy(self.expected)
        expected[0]["scoring_decisions"] = 3
        expected[0]["first_intent"].update(row_index=2, intent_timestamp=timestamp(602), score=.9)
        result = self.compare(expected)
        self.assertFalse(result["parityPassed"])
        for field in ("scoringDecisions", "row_index", "intent_timestamp", "score"):
            self.assertEqual(result["mismatches"][field], 1)
        self.assertEqual(self.actual, actual_before)
        self.assertEqual(result["scoringDecisions"], 5)

    def test_missing_duplicate_identity_and_presence_errors_prevent_parity(self):
        wrong = deepcopy(self.expected[0])
        wrong.update(symbol="OTHER", first_intent=None)
        result = self.compare([wrong, deepcopy(wrong)])
        self.assertFalse(result["parityPassed"])
        for field in ("missingExpectedWatch", "duplicateExpectedWatch", "watchIdentity", "firstIntentPresence"):
            self.assertEqual(result["mismatches"][field], 1)


class ReplayBoundaryTests(Files):
    def setUp(self):
        super().setUp()
        self.watches = [watch("A"), watch("B", DAY_B)]
        self.ranges = np.array([[0, 3], [3, 6]], dtype=np.int64)
        self.grid = [grid_row(w, minute, wi) for wi, w in enumerate(self.watches)
                     for minute in range(600, 603)]
        self.events, self.rebuilt, self.decisions = [], {}, {}
        self.truncate_meta = False
        self.numeric = np.zeros((6, 148), dtype=np.float64)
        self.numeric[:, 0] = [.1, .5, .8, .1, .2, .3]
        self.categories = np.zeros((6, 15), dtype=np.int32)
        thresholds = dict(zip(RAW.core.POLICIES, [.5, .6, .7, .8]))
        self.spec = {"source": b"SYNTHETIC_SOURCE_NOT_EXECUTED",
                     "test_sessions": {1: {DAY_A}, 2: {DAY_B}},
                     "calibration": {fold: {"thresholds": dict(thresholds)} for fold in (1, 2)}}
        self.paths = {
            "base": {
                "WATCH_RECORDS.jsonl.gz": self.write_rows("watches.gz", self.watches),
                "PERSISTENT_GRID.jsonl.gz": self.write_rows("grid.gz", self.grid),
                "PRIVATE_INPUTS/features_numeric.npy": self.root / "numeric.npy",
                "PRIVATE_INPUTS/features_categories.npy": self.root / "categories.npy",
            },
            "corrected": {
                "PRIVATE_INPUTS/oof_P1.npz": self.root / "oracle.npz",
                "FIRST_INTENTS_PRIVATE.jsonl.gz": self.root / "first-intents.gz",
            },
        }
        raw = {w["watch_key"]: {"synthetic_watch": w["watch_key"]} for w in self.watches}
        self.raw_paths = {"watch_ranges": self.root / "ranges.npy",
                          "raw_paths": self.write_object("raw.gz", raw),
                          "source_tokens": self.write_object("tokens.gz", raw)}
        score = self.numeric[:, 0].copy()
        self.oracle = {"row_indices": np.arange(6), "fold": np.repeat([1, 2], 3),
                       "predictions": np.column_stack([score, 2 * score, 3 * score]),
                       "percentiles": np.column_stack([score, score, score]), "score": score,
                       "thresholds": np.tile([.5, .6, .7, .8], (6, 1))}
        first = {"row_index": 1, "fold": 1, "intent_timestamp": timestamp(601),
                 "score": .5, "threshold": .5}
        self.expected = [expected_row(self.watches[0], first, 2), expected_row(self.watches[1], None, 3)]
        self.write_rows("first-intents.gz", self.expected)
        self.report = RAW.new_report(1)

    def run_synthetic(self):
        owner = self
        actual_derive, original_json_lines = RAW.derive_first_intent, RAW.json_lines

        class ComparisonReference:
            def __init__(self, values, name):
                self.values, self.name = values, name
                self.shape, self.dtype = values.shape, values.dtype

            def __len__(self):
                return len(self.values)

            def __getitem__(self, selected):
                key = owner.watches[selected.start // 3]["watch_key"]
                owner.assertIn(key, owner.decisions, "Saved feature values read before actual decision")
                owner.events.append((self.name, key))
                return self.values[selected]

        refs = {
            self.raw_paths["watch_ranges"]: self.ranges,
            self.paths["base"]["PRIVATE_INPUTS/features_numeric.npy"]: ComparisonReference(self.numeric, "reference_numeric"),
            self.paths["base"]["PRIVATE_INPUTS/features_categories.npy"]: ComparisonReference(self.categories, "reference_categories"),
        }

        def load_array(path, **kwargs):
            owner.assertIs(kwargs.get("allow_pickle"), False)
            return refs[path]

        def rebuild(runtime, record, raw, tokens, watch_index):
            key = record["watch_key"]
            owner.assertEqual(raw["synthetic_watch"], key)
            owner.assertEqual(tokens["synthetic_watch"], key)
            lo, hi = map(int, owner.ranges[watch_index])
            numeric = owner.numeric[lo:hi].copy()
            named = np.full((hi - lo, 15), "known", dtype=object)
            meta = [{"intent_minute": row["intent_minute"]} for row in owner.grid[lo:hi]]
            if owner.truncate_meta:
                meta.pop()
            owner.rebuilt[key] = (numeric, named)
            owner.events.append(("rebuilt", key))
            return watch_index, numeric, named, meta, {"source_status": "SYNTHETIC", "kernel_steps": 3}

        class InferenceOnlyFold:
            def __init__(self, fold, *_):
                self.key = owner.watches[fold - 1]["watch_key"]
                self.calibration = owner.spec["calibration"][fold]

            def encode_named_categories(self, named):
                return np.zeros(named.shape, dtype=np.int32), [0] * 15

            def score_named_batch(self, numeric, named):
                owner.assertIs(numeric, owner.rebuilt[self.key][0])
                owner.assertIs(named, owner.rebuilt[self.key][1])
                owner.events.append(("score", self.key))
                score = numeric[:, 0].copy()
                return np.column_stack([score, 2 * score, 3 * score]), np.column_stack([score] * 3), score

        def derive(item, *args):
            key = item["watch"]["watch_key"]
            result = actual_derive(item, *args)
            owner.decisions[key] = deepcopy(result)
            owner.events.append(("decision", key))
            return result

        def load_oracle(*args):
            owner.assertEqual(len(owner.decisions), 2, "OOF opened before every actual decision")
            owner.events.append(("open_oracle", None))
            return deepcopy(owner.oracle)

        def json_lines(path):
            if path == owner.paths["corrected"]["FIRST_INTENTS_PRIVATE.jsonl.gz"]:
                owner.assertEqual(len(owner.decisions), 2, "Expected intents opened before all decisions")
                owner.events.append(("open_expected_intents", None))
            yield from original_json_lines(path)

        with ExitStack() as stack:
            stack.enter_context(redirect_stdout(io.StringIO()))
            stack.enter_context(mock.patch.object(np, "load", side_effect=load_array))
            stack.enter_context(mock.patch.object(RAW.features, "load_feature_runtime", return_value=object()))
            stack.enter_context(mock.patch.object(RAW.features, "verify_saved_compact_overlap", return_value={"bars": 3}))
            stack.enter_context(mock.patch.object(RAW.features, "compute_watch_features", side_effect=rebuild))
            stack.enter_context(mock.patch.object(RAW.core, "inference_primitives", return_value=(None, None)))
            stack.enter_context(mock.patch.object(RAW.core, "FrozenP1Fold", InferenceOnlyFold))
            stack.enter_context(mock.patch.object(RAW.core, "load_oracle", side_effect=load_oracle))
            stack.enter_context(mock.patch.object(RAW, "derive_first_intent", side_effect=derive))
            stack.enter_context(mock.patch.object(RAW, "json_lines", side_effect=json_lines))
            fit = stack.enter_context(mock.patch("sklearn.ensemble.HistGradientBoostingRegressor.fit",
                                                  side_effect=AssertionError("MODEL_FIT_FORBIDDEN")))
            RAW.run_replay(self.spec, self.paths, self.raw_paths, 1, self.report)
            fit.assert_not_called()

    def test_raw_features_feed_scorer_and_references_open_after_all_decisions(self):
        self.run_synthetic()
        self.assertTrue(self.report["selectedWholeWatchFirstIntentParityPassed"])
        self.assertEqual(self.report["scoredRows"], 6)
        self.assertEqual(self.report["firstIntentParity"]["scoringDecisions"], 5)
        self.assertEqual(self.report["firstIntentParity"]["rowsAfterFirstIntentLock"], 1)
        oracle_open = self.events.index(("open_oracle", None))
        expected_open = self.events.index(("open_expected_intents", None))
        for record in self.watches:
            key = record["watch_key"]
            self.assertLess(self.events.index(("score", key)), self.events.index(("decision", key)))
            self.assertLess(self.events.index(("decision", key)), self.events.index(("reference_numeric", key)))
            self.assertLess(self.events.index(("decision", key)), oracle_open)
        self.assertLess(oracle_open, expected_open)

    def test_poisoned_oof_cannot_provide_scores_or_move_first_cross(self):
        self.oracle["score"][0] = .9
        with self.assertRaisesRegex(ValueError, "ORIGINAL_SCORE_PARITY_FAILED"):
            self.run_synthetic()
        first = self.decisions[self.watches[0]["watch_key"]]["first_intent"]
        self.assertEqual(first["row_index"], 1)
        self.assertEqual(first["score"], .5)
        self.assertFalse(self.report["scoreParityPassed"])
        self.assertGreater(self.report["scoreParity"]["fourPolicyDecisionMismatches"], 0)
        self.assertNotIn(("open_expected_intents", None), self.events)

    def test_changed_expected_first_cross_blocks_pass_without_changing_actual(self):
        self.expected[0]["first_intent"].update(row_index=2, intent_timestamp=timestamp(602), score=.8)
        self.expected[0]["scoring_decisions"] = 3
        self.write_rows("first-intents.gz", self.expected)
        with self.assertRaisesRegex(ValueError, "ORIGINAL_SELECTED_FIRST_INTENT_PARITY_FAILED"):
            self.run_synthetic()
        self.assertEqual(self.decisions[self.watches[0]["watch_key"]]["first_intent"]["row_index"], 1)
        self.assertEqual(self.report["firstIntentParity"]["mismatches"]["row_index"], 1)
        self.assertFalse(self.report["selectedWholeWatchFirstIntentParityPassed"])

    def test_incomplete_rebuilt_clock_metadata_blocks_complete_watch_claim(self):
        self.truncate_meta = True
        with self.assertRaisesRegex(ValueError, "REBUILT_(WATCH_RANGE|GRID_CLOCK)_MISMATCH"):
            self.run_synthetic()
        self.assertFalse(self.report["selectedWholeWatchFirstIntentParityPassed"])
        self.assertNotIn(("open_oracle", None), self.events)


if __name__ == "__main__":
    unittest.main()
