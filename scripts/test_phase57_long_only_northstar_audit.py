#!/usr/bin/env python3
"""Synthetic checks only: no Development data and no model fitting."""
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd


PATH = Path(__file__).with_name("run_phase57_long_only_northstar_audit.py")
SPEC = importlib.util.spec_from_file_location("northstar", PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def sample_row(symbol, time="09:30", score=1, upside=6, **updates):
    row = {column: 0.0 for column in AUDIT.NUMERIC}
    row.update({"sessionDate": "2024-01-10", "symbol": str(symbol), "decisionTimeJst": time,
                "sourceGroup": "L1", "partition": "DEVELOPMENT_A", "segment": "PRIME",
                "liquidityBucket": "HIGH", "decisionVolatilityPct": 1.0,
                "currentReturnPct": 0.5, "legacyEligible": 1, "y30Bps": 100,
                "strict30Bps": 100, "strict30FreshBps": 100,
                "legacyReferencePrice": 100, "referencePrice": 100, "referenceValid": 1,
                "horizonMinutes": 30, "futureMfePct": upside, "trueMaePct": -1,
                "futureMinuteCount": 60, "savedV1Score": score,
                "timeTo5Min": 20 if upside >= 5 else np.nan})
    for t in [1, 2, 3, 5]:
        row[f"futureOpportunity{t}"] = int(upside >= t)
    row.update(updates)
    return row


def frame(rows):
    return AUDIT.prepare_rows(pd.DataFrame(rows))


class NorthStarTests(unittest.TestCase):
    def test_missing_target_is_not_zero_or_eligible(self):
        df = frame([sample_row("1", y30Bps=np.nan, legacyEligible=0)])
        self.assertEqual(len(AUDIT.select_top5(df)[0]), 0)
        comparison = AUDIT.label_comparison(df)
        self.assertEqual(comparison["commonFiniteRows"], 0)
        self.assertIsNone(comparison["pearson"])
        self.assertIsNone(AUDIT.distribution([np.nan])["mean"])
        with self.assertRaisesRegex(ValueError, "Legacy eligibility"):
            frame([sample_row("1", y30Bps=np.nan, legacyEligible=1)])

    def test_random_recall_is_timestamp_capacity_weighted(self):
        # t1: N=10,O=2; t2:N=20,O=10. K=5 at each timestamp.
        rows = [sample_row(str(i), score=100 - i, upside=6 if i < 2 else 0) for i in range(10)]
        rows += [sample_row(str(i), time="10:00", score=100 - i, upside=6 if i < 10 else 0) for i in range(20)]
        policy, selected = AUDIT.select_top5(frame(rows))
        metrics = AUDIT.capacity_metrics(policy, selected)["opportunities"]["5"]
        self.assertAlmostEqual(metrics["randomExpectedHits"], 3.5)
        self.assertAlmostEqual(metrics["randomExpectedRecallPct"], 100 * 3.5 / 12)
        self.assertNotAlmostEqual(metrics["randomExpectedRecallPct"], 100 * 10 / 12)
        self.assertAlmostEqual(metrics["actualRecallPct"], 100 * 7 / 12)
        self.assertAlmostEqual(metrics["recallLift"], 2)
        self.assertAlmostEqual(metrics["capacityMatchedRandomExpectedScorablePrecisionPct"], 35)

    def test_stale_selected_rows_not_replaced_or_known_negatives(self):
        rows = [sample_row(str(i), score=100-i, upside=6) for i in range(10)]
        rows[0].update(referenceValid=0, referenceAgeMin=25, futureMfePct=np.nan)
        df = frame(rows)
        policy, selected = AUDIT.select_top5(df)
        self.assertEqual(selected.symbol.tolist(), ["0", "1", "2", "3", "4"])
        m = AUDIT.capacity_metrics(policy, selected)
        self.assertEqual(m["selectedEvents"], 5)
        self.assertEqual(m["scorableSelectedEvents"], 4)
        self.assertEqual(m["opportunities"]["5"]["precisionAt5Pct"], 100)
        self.assertEqual(m["opportunities"]["5"]["hitsOverAllSelectedLowerBoundPct"], 80)
        self.assertEqual(m["opportunities"]["5"]["randomExpectedHits"], 4.5)

    def test_daily_uses_first_detection_not_best_later_outcome(self):
        df = frame([sample_row("1", upside=0), sample_row("1", time="10:00", upside=10)])
        policy, selected = AUDIT.select_top5(df)
        daily = AUDIT.daily_diagnostic(policy, selected)
        self.assertEqual(daily["distinctSymbolDays"], 1)
        self.assertEqual(daily["future5DistinctHits"], 0)
        self.assertEqual(daily["repeatSelectionsPerSymbolDay"]["mean"], 1)
        self.assertEqual(daily["medianFirstDetectionMinutesAfter0900"], 30)

    def test_exact_matching_deterministic_and_no_replacement(self):
        rows = [sample_row("o1"), sample_row("o2"), sample_row("c1", upside=0),
                sample_row("excluded", upside=0, segment="GROWTH")]
        df = frame(rows)
        o, c, ao, ac = AUDIT.matched_indices(df)
        self.assertEqual(len(o), 1)
        self.assertEqual(len(c), len(set(c)))
        self.assertEqual(len(ao), 2)
        self.assertEqual(df.loc[c[0], "symbol"], "c1")
        shuffled = frame(list(reversed(rows)))
        so, sc, _, _ = AUDIT.matched_indices(shuffled)
        self.assertEqual(df.loc[o[0], "symbol"], shuffled.loc[so[0], "symbol"])
        self.assertEqual(df.loc[c[0], "symbol"], shuffled.loc[sc[0], "symbol"])

    def test_overlap_constants_and_signed_effect(self):
        equal = AUDIT.effect_and_overlap([1, 1], [1, 1])
        self.assertEqual(equal["distributionOverlap"], 1)
        self.assertEqual(equal["standardizedMeanDifference"], 0)
        shifted = AUDIT.effect_and_overlap([2, 3, 4], [0, 1, 2])
        self.assertGreater(shifted["standardizedMeanDifference"], 0)
        self.assertGreaterEqual(shifted["distributionOverlap"], 0)
        self.assertLessEqual(shifted["distributionOverlap"], 1)
        binary = AUDIT.effect_and_overlap([0, 1], [0, 0])
        self.assertEqual(binary["histogramBins"], 2)
        self.assertEqual(binary["distributionOverlap"], .5)

    def test_mae_clips_positive_values(self):
        df = frame([sample_row("1", rawMae30Pct=2, trueMae30Pct=0),
                    sample_row("2", rawMae30Pct=-2, trueMae30Pct=-2)])
        result = AUDIT.mae_summary(df, "rawMae30Pct", "trueMae30Pct")
        self.assertEqual(result["rawMeanPct"], 0)
        self.assertEqual(result["trueMeanPct"], -1)
        self.assertEqual(result["positiveRawMaeRows"], 1)

    def test_missing_score_does_not_shrink_universe(self):
        df = frame([sample_row("1", score=np.nan)])
        self.assertEqual(AUDIT.selection_audit(df)["status"], "UNAVAILABLE")

    def test_price_comparison_flag_avoids_percentage_roundoff(self):
        df = frame([sample_row("1", upside=4.999999999999, futureOpportunity5=1)])
        result = AUDIT.outcome_summary(df)
        self.assertEqual(result["futureOpportunity"]["5"]["count"], 1)

    def test_alignment_horizon_comparison_uses_identical_rows(self):
        df = frame([
            sample_row("1", y30Bps=300, strict30Bps=200, strict30FreshBps=150),
            sample_row("2", y30Bps=100, strict30Bps=50, strict30FreshBps=np.nan),
            sample_row("3", y30Bps=900, strict30Bps=np.nan),
            sample_row("4", y30Bps=np.nan, legacyEligible=0, strict30Bps=800),
            sample_row("5", referenceValid=0, futureMfePct=np.nan),
        ])
        result = AUDIT.target_alignment(df)
        common = result["commonLegacyStrictAlignment"]
        self.assertEqual(common["commonEvaluableRows"], 2)
        self.assertEqual(common["alignments"]["y30Bps"]["commonEvaluableRows"], 2)
        self.assertEqual(common["alignments"]["strict30Bps"]["commonEvaluableRows"], 2)
        fresh = result["commonLegacyStrictFreshAlignment"]
        self.assertEqual(fresh["commonEvaluableRows"], 1)
        self.assertTrue(all(a["commonEvaluableRows"] == 1 for a in fresh["alignments"].values()))

    def test_full_report_json_safe_and_model_identity_explicit(self):
        df = frame([sample_row("1"), sample_row("2", upside=0)])
        report = AUDIT.make_report(df, {"model": {"name": "V1_SAVED_CD_REFIT"}}, "test-contract")
        encoded = json.dumps(report, allow_nan=False)
        self.assertNotIn('"symbol":', encoded)
        self.assertIn("UNAVAILABLE", encoded)
        self.assertFalse(report["safety"]["fitOrRefitPerformed"])
        self.assertEqual(report["contractCommit"], "test-contract")
        self.assertIn("AB_OUTSIDE_CD_FIT_DIAGNOSTIC", report["scopes"])


if __name__ == "__main__":
    unittest.main()
