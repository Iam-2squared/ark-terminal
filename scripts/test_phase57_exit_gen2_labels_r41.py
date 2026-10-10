"""Synthetic horizon, missingness and event semantics; no historical fitting."""
import math
import unittest

from scripts.phase57_exit_execution_contract_v1 import continuous_minutes
from scripts.phase57_exit_gen2_labels_r41 import event_labels, index_raw_rows


DAY = "2025-05-30"
SCHEDULE = continuous_minutes(DAY)


def rows_for(now, *, opening=100.0, high=100.5, low=99.5):
    return [[m, opening, high, low, opening, 1, 1] for m in SCHEDULE if m >= now]


class EventLabelsTest(unittest.TestCase):
    def labels(self, now=600, rows=None):
        return event_labels(now, SCHEDULE, rows_for(now) if rows is None else rows)

    def test_complete_negative_labels_with_distinct_horizons(self):
        value = self.labels()
        self.assertEqual(value["targets"], {"CONTINUATION": 0, "FAILURE": 0})
        self.assertEqual(value["horizonBars"], {"CONTINUATION": 60, "FAILURE": 15})
        self.assertEqual(value["labelKnownAt"], {"CONTINUATION": 660, "FAILURE": 615})

    def test_exact_thresholds_and_same_bar_both_events(self):
        rows = rows_for(600)
        rows[0][2:4] = [101.0, 99.25]
        value = self.labels(rows=rows)
        self.assertEqual(value["targets"], {"CONTINUATION": 1, "FAILURE": 1})
        self.assertFalse(value["intrabarHitOrderInferred"])

    def test_head_specific_masks_do_not_intersect(self):
        rows = [row for row in rows_for(600) if row[0] != 620]
        value = self.labels(rows=rows)
        self.assertEqual(value["targets"], {"CONTINUATION": None, "FAILURE": 0})
        self.assertEqual(value["available"], {"CONTINUATION": False, "FAILURE": True})
        self.assertIsNone(value["labelKnownAt"]["CONTINUATION"])
        self.assertEqual(value["windowEnd"]["CONTINUATION"], 660)

    def test_early_positive_needs_entire_window(self):
        rows = rows_for(600)
        rows[0][2] = 110
        rows = [row for row in rows if row[0] != 659]
        self.assertIsNone(self.labels(rows=rows)["targets"]["CONTINUATION"])

    def test_complete_negative_also_needs_entire_window(self):
        rows = [row for row in rows_for(600) if row[0] != 614]
        self.assertEqual(self.labels(rows=rows)["targets"], {"CONTINUATION": None, "FAILURE": None})

    def test_exact_anchor_missing_never_searches_forward(self):
        rows = rows_for(600)[1:]
        value = self.labels(rows=rows)
        self.assertEqual(value["referenceMinute"], 600)
        self.assertEqual(set(value["missingReasons"].values()), {"EXACT_ANCHOR_MISSING"})
        self.assertEqual(set(value["targets"].values()), {None})

    def test_invalid_anchor_open_does_not_impute(self):
        for bad in (0, -1, math.nan, math.inf, True, None):
            with self.subTest(bad=bad):
                rows = rows_for(600)
                rows[0][1] = bad
                self.assertEqual(set(self.labels(rows=rows)["missingReasons"].values()),
                                 {"EXACT_ANCHOR_INVALID_OPEN"})

    def test_invalid_ohlc_in_continuation_only_window(self):
        for field, bad in ((2, 99), (3, 101), (4, 102), (1, 101), (2, math.nan), (3, 0)):
            with self.subTest(field=field, bad=bad):
                rows = rows_for(600)
                rows[30][field] = bad
                value = self.labels(rows=rows)
                self.assertIsNone(value["targets"]["CONTINUATION"])
                self.assertEqual(value["targets"]["FAILURE"], 0)
                self.assertEqual(value["missingReasons"]["CONTINUATION"], "TARGET_WINDOW_INVALID_OHLC")

    def test_lunch_uses_scheduled_active_bars(self):
        value = self.labels(now=690)
        self.assertEqual(value["referenceMinute"], 750)
        self.assertEqual(value["horizonBars"], {"CONTINUATION": 60, "FAILURE": 15})
        self.assertEqual(value["labelKnownAt"], {"CONTINUATION": 810, "FAILURE": 765})

    def test_horizon_crosses_lunch_without_counting_break(self):
        value = self.labels(now=689)
        self.assertEqual(value["referenceMinute"], 689)
        self.assertEqual(value["labelKnownAt"], {"CONTINUATION": 809, "FAILURE": 764})

    def test_calendar_shrinks_end_of_session_horizons(self):
        value = self.labels(now=920)
        self.assertEqual(value["horizonBars"], {"CONTINUATION": 5, "FAILURE": 5})
        self.assertEqual(value["labelKnownAt"], {"CONTINUATION": 925, "FAILURE": 925})

    def test_final_continuous_target_is_single_bar(self):
        value = self.labels(now=924)
        self.assertEqual(value["horizonBars"], {"CONTINUATION": 1, "FAILURE": 1})
        self.assertEqual(value["labelKnownAt"], {"CONTINUATION": 925, "FAILURE": 925})

    def test_terminal_decision_has_no_label_even_with_auction(self):
        value = self.labels(now=925, rows=[[930, 100, 100, 100, 100, 1, 1]])
        self.assertIsNone(value["referenceMinute"])
        self.assertEqual(set(value["missingReasons"].values()), {"NO_CONTINUOUS_REFERENCE"})
        self.assertEqual(value["horizonBars"], {"CONTINUATION": 0, "FAILURE": 0})

    def test_auction_never_completes_or_changes_event_window(self):
        rows = rows_for(924) + [[930, 1000, 1000, 1000, 1000, 1, 1]]
        self.assertEqual(self.labels(now=924, rows=rows)["targets"], {"CONTINUATION": 0, "FAILURE": 0})
        self.assertEqual(set(self.labels(now=924, rows=rows[1:])["targets"].values()), {None})

    def test_beyond_horizon_event_is_ignored(self):
        rows = rows_for(600)
        rows[60][2] = 120
        rows[15][3] = 90
        self.assertEqual(self.labels(rows=rows)["targets"], {"CONTINUATION": 0, "FAILURE": 0})

    def test_last_selected_bar_event_is_included(self):
        rows = rows_for(600)
        rows[59][2] = 101
        rows[14][3] = 99.25
        self.assertEqual(self.labels(rows=rows)["targets"], {"CONTINUATION": 1, "FAILURE": 1})

    def test_duplicate_raw_minute_fails_closed(self):
        rows = rows_for(600)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_EXACT_MINUTE"):
            self.labels(rows=rows + [rows[0]])

    def test_invalid_schedule_or_non_endpoint_fails(self):
        for schedule, now in ((SCHEDULE, 700), (SCHEDULE + (930,), 600),
                              (tuple(reversed(SCHEDULE)), 600), ((), 600)):
            with self.subTest(now=now, length=len(schedule)):
                with self.assertRaisesRegex(ValueError, "INVALID_SCHEDULE_OR_DECISION_EPOCH"):
                    event_labels(now, schedule, [])

    def test_preindexed_and_shuffled_raw_paths_equal(self):
        rows = rows_for(600)
        self.assertEqual(event_labels(600, SCHEDULE, rows),
                         event_labels(600, SCHEDULE, indexed_rows=index_raw_rows(list(reversed(rows)))))


if __name__ == "__main__":
    unittest.main()
