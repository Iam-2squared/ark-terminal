"""Synthetic checks of causal boundary and distinctions, no market data/model."""

import unittest

from missingness_reasons import (
    BOUNDARY, CLEAR, DENOMINATOR, GAP, HISTORY, INAPPLICABLE, PREVIOUS, UNKNOWN,
    explain_missingness,
)


def bars(begin, end, *, volume=10, value=1000, six_columns=False):
    rows = [[m, 100, 101, 99, 100, volume, value] for m in range(begin, end)]
    return [row[:6] for row in rows] if six_columns else rows


def inspect(name, today=None, previous=None, cutoff=600, **kwargs):
    return explain_missingness("2025-06-27", cutoff,
                               bars(540, cutoff) if today is None else today,
                               bars(540, cutoff) if previous is None else previous,
                               name, previous_day="2025-06-26", **kwargs)


class MissingnessGuardTests(unittest.TestCase):
    def test_complete_window_is_not_feature_recomputation(self):
        result = inspect("p0/w5/return")
        self.assertEqual(result["reason"], CLEAR)
        self.assertFalse(result["expected_null"])
        self.assertFalse(result["evidence"]["new_feature_values_computed"])
        self.assertEqual(result["stored_null_linkage"], "STORED_CELL_NOT_CHECKED")

    def test_internal_gap_does_not_claim_download_failure(self):
        today = [r for r in bars(540, 600) if r[0] != 597]
        result = inspect("p0/w5/return", today=today, observed_is_missing=True)
        self.assertEqual(result["reason"], GAP)
        self.assertEqual(result["findings"][0]["evidence"]["missing_minutes"], [597])
        self.assertEqual(result["findings"][0]["evidence"]["underlying_source_cause"], UNKNOWN)
        self.assertEqual(result["stored_null_linkage"], "COMPATIBLE_NULL_GUARD_ONLY")
        self.assertFalse(result["causal_effect_of_repair_established"])

    def test_short_supplied_prefix_is_distinct_from_internal_gap(self):
        result = inspect("p0/w20/high", today=bars(590, 600))
        self.assertEqual(result["reason"], HISTORY)
        self.assertTrue(result["expected_null"])

    def test_half_session_boundary_cannot_use_am_to_fill_pm_window(self):
        result = inspect("p0/w5/return", today=bars(540, 690) + bars(750, 753), cutoff=753)
        self.assertEqual(result["reason"], BOUNDARY)
        self.assertEqual(result["findings"][0]["evidence"]["half_session_start"], 750)

    def test_am_terminal_boundary_uses_am_phase(self):
        result = inspect("p0/w5/return", today=bars(540, 690), cutoff=690)
        self.assertEqual(result["reason"], CLEAR)

    def test_return_requires_n_plus_one_rows(self):
        today = bars(595, 600)
        self.assertFalse(inspect("p0/w5/return", today=today)["expected_null"])
        result = inspect("p0/return5", today=today)
        self.assertEqual(result["reason"], HISTORY)
        self.assertEqual(result["findings"][0]["evidence"]["required_rows"], 6)

    def test_previous_day_dependency_is_separate(self):
        result = inspect("p0/activity/5/volumeRelativePreviousDay", previous=[])
        self.assertEqual(result["reason"], PREVIOUS)
        self.assertEqual(result["findings"][0]["evidence"]["role"], "previous_day")
        self.assertFalse(inspect("p0/activity/5/volume", previous=[])["expected_null"])

    def test_zero_denominator_but_zero_numerator_is_allowed(self):
        today = bars(540, 600)
        for row in today:
            if 590 <= row[0] < 595:
                row[5] = 0
        result = inspect("p0/activity/5/volumeAcceleration", today=today)
        self.assertEqual(result["reason"], DENOMINATOR)
        for row in today:
            row[5] = 0 if 595 <= row[0] < 600 else 10
        self.assertEqual(inspect("p0/activity/5/volumeAcceleration", today=today)["reason"], CLEAR)

    def test_activity_preceding_window_has_its_own_boundary(self):
        result = inspect("p0/activity/3/volumeAcceleration", today=bars(750, 754), cutoff=754)
        self.assertEqual(result["reason"], BOUNDARY)
        self.assertEqual(result["findings"][0]["evidence"]["role"], "preceding")

    def test_counts_survive_incomplete_windows(self):
        for feature in ("p0/w20/count", "p0/w20/coverage", "p0/activity/5/previousDayRows"):
            result = inspect(feature, today=[], previous=[])
            self.assertEqual(result["reason"], INAPPLICABLE)
            self.assertFalse(result["expected_null"])

    def test_vwap_threshold_and_zero_volume_are_distinct(self):
        low_coverage = inspect("p0/vwapDistancePct", today=bars(590, 600))
        zero_volume = inspect("p0/vwapDistancePct", today=bars(540, 600, volume=0))
        self.assertEqual(low_coverage["reason"], HISTORY)
        self.assertEqual(zero_volume["reason"], DENOMINATOR)
        self.assertFalse(inspect("p0/vwapObservedCoverage", today=[])["expected_null"])

    def test_vwap_exactly_eighty_percent_passes_coverage_guard(self):
        result = inspect("p0/vwapDistancePct", today=bars(552, 600))
        self.assertEqual(result["reason"], CLEAR)

    def test_vwap_slope_checks_lagged_prefix_separately(self):
        # At current t, 48/60=.8; at t-3, 45/57<.8.
        result = inspect("p0/vwapSlope3Pct", today=bars(552, 600))
        self.assertEqual(result["reason"], HISTORY)
        self.assertEqual(result["findings"][0]["evidence"]["role"], "lag3_vwap")

    def test_six_columns_do_not_create_value_from_ohlcv(self):
        today = bars(540, 600, six_columns=True)
        self.assertEqual(inspect("p0/activity/5/volumeAcceleration", today=today)["reason"], CLEAR)
        result = inspect("p0/activity/5/value", today=today)
        self.assertEqual(result["reason"], UNKNOWN)
        self.assertIsNone(result["expected_null"])
        self.assertEqual(result["findings"][0]["evidence"]["required_column"], "Value")

    def test_zero_value_is_null_vwap_distance_but_not_logged_value(self):
        today = bars(540, 600, value=0)
        self.assertEqual(inspect("p0/w5/vwapDistance", today=today)["reason"], DENOMINATOR)
        self.assertEqual(inspect("p0/w5/value", today=today)["reason"], CLEAR)

    def test_zero_current_vwap_numerator_does_not_make_slope_null(self):
        # Current cumulative Value may be zero only if the lagged Value is
        # also zero for nonnegative values, so exercise the guard directly.
        # A slope's current Value is a numerator, unlike distance's divisor.
        from missingness_reasons import _vwap_guards
        rows = bars(540, 600, value=0)
        findings = _vwap_guards(rows, "2025-06-27", 600, "current_vwap",
                               positive_value_required=False)
        self.assertEqual(findings, [])

    def test_malformed_unneeded_previous_input_does_not_change_current_guard(self):
        self.assertEqual(inspect("p0/w5/high", previous=[[1, 2]])["reason"], CLEAR)

    def test_unknown_previous_date_after_extension_is_not_assumed(self):
        result = explain_missingness("2024-11-05", 910, bars(750, 910), bars(750, 910),
                                     "p0/activity/5/volumeRelativePreviousDay")
        self.assertEqual(result["reason"], UNKNOWN)
        self.assertIsNone(result["expected_null"])

    def test_wick_and_compression_use_correct_denominator_slice(self):
        today = bars(540, 600)
        today[-2][5] = 0
        self.assertEqual(inspect("p0/activity/wick/volumeConfirmation", today=today)["reason"], DENOMINATOR)
        self.assertEqual(inspect("p0/activity/compression/volumeContraction", today=today)["reason"], CLEAR)
        for row in today[-11:-6]:
            row[5] = 0
        self.assertEqual(inspect("p0/activity/compression/volumeContraction", today=today)["reason"], DENOMINATOR)

    def test_unclosed_suffix_prices_are_not_inspected(self):
        clean = bars(540, 600)
        poison = [600, "future-open", "future-high", "future-low", "future-close", "future-volume"]
        first = inspect("p0/w5/high", today=clean)
        second = inspect("p0/w5/high", today=clean + [poison])
        self.assertEqual(first["reason"], second["reason"])
        self.assertEqual(first["findings"], second["findings"])
        self.assertEqual(second["evidence"]["today_input"]["excluded_unclosed_rows"], 1)

    def test_invalid_price_row_is_excluded_and_reported_as_gap(self):
        today = bars(540, 600)
        today[-2][3] = -1
        result = inspect("p0/w5/low", today=today)
        self.assertEqual(result["reason"], GAP)
        self.assertEqual(result["evidence"]["today_input"]["rejected_minutes"], [598])

    def test_unsorted_or_duplicate_input_is_not_silently_repaired(self):
        today = bars(540, 600)
        self.assertEqual(inspect("p0/w5/high", today=today + [today[-1]])["reason"], UNKNOWN)
        self.assertEqual(inspect("p0/w5/high", today=list(reversed(today)))["reason"], UNKNOWN)

    def test_previous_date_required_to_exclude_previous_auction_correctly(self):
        # Previous day before the extension ends at 15:00, current at 15:25.
        result = explain_missingness("2024-11-05", 910, bars(750, 910), bars(750, 910),
                                     "p0/activity/5/volumeRelativePreviousDay", previous_day="2024-11-04")
        self.assertEqual(result["reason"], PREVIOUS)
        self.assertEqual(result["evidence"]["previous_input"]["excluded_nonregular_rows"], 10)

    def test_stored_null_and_guard_evidence_remain_separate(self):
        result = inspect("p0/w5/high", observed_is_missing=True)
        self.assertEqual(result["reason"], CLEAR)
        self.assertEqual(result["stored_null_linkage"], "STORED_NULL_UNEXPLAINED")
        result = inspect("p0/w5/high", today=[], observed_is_missing=False)
        self.assertEqual(result["stored_null_linkage"], "GUARD_PRESENT_BUT_STORED_CELL_NON_NULL")

    def test_nonprice_and_unsupported_features_are_not_guessed(self):
        self.assertEqual(inspect("state/stop_count")["reason"], INAPPLICABLE)
        self.assertEqual(inspect("p0/w99/return")["reason"], UNKNOWN)
        self.assertEqual(inspect("p0/priceVsFirstSelectorPct")["reason"], UNKNOWN)

    def test_lunch_and_future_previous_date_are_invalid_audit_context(self):
        self.assertEqual(inspect("p0/w5/high", cutoff=720)["reason"], INAPPLICABLE)
        result = explain_missingness("2025-06-27", 600, [], [], "p0/w5/high", previous_day="2025-06-30")
        self.assertEqual(result["reason"], UNKNOWN)


if __name__ == "__main__":
    unittest.main()
