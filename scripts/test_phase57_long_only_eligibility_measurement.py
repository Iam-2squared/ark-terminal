#!/usr/bin/env python3
"""Synthetic tests for pre-ranking eligibility; no Development input or fit."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

BASE_PATH = Path(__file__).with_name("run_phase57_long_only_corrected_measurement.py")
BASE_SPEC = importlib.util.spec_from_file_location("run_phase57_long_only_corrected_measurement", BASE_PATH)
BASE = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(BASE)
import sys
sys.modules["run_phase57_long_only_corrected_measurement"] = BASE

PATH = Path(__file__).with_name("run_phase57_long_only_eligibility_measurement.py")
SPEC = importlib.util.spec_from_file_location("eligibility", PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def row(symbol, time="09:30", score=1, valid=1, hit3=0, hit5=0, segment="PRIME", liquidity="HIGH"):
    result = {column: 0.0 for column in BASE.NUMERIC}
    result.update({
        "sessionDate": "2024-01-10",
        "symbol": str(symbol),
        "decisionTimeJst": time,
        "partition": "DEVELOPMENT_A",
        "sourceGroup": "L1",
        "segment": segment,
        "liquidityBucket": liquidity,
        "decisionPriceKind": "LATEST_ACCEPTED_MINUTE_CLOSE" if valid else "NONE",
        "corrected30EndpointKind": "CONTINUOUS_5M_CLOSE" if valid else "NONE",
        "firstCloseHitKind2": "NONE",
        "firstCloseHitKind3": "NONE",
        "firstCloseHitKind5": "NONE",
        "decisionPrice": 100 if valid else np.nan,
        "decisionPriceValid": valid,
        "referenceAgeMin": 0 if valid else 20,
        "corrected30Evaluable": valid,
        "corrected30ReturnBps": 100 if valid else np.nan,
        "mfe30Pct": 3 if valid else np.nan,
        "mae30Pct": -1 if valid else np.nan,
        "sessionMfePct": 6 if valid else np.nan,
        "sessionMaePct": -1 if valid else np.nan,
        "savedV1Score": score,
        "futureBarCount": 10 if valid else 0,
        "highOpportunity2": max(hit3, hit5),
        "highOpportunity3": max(hit3, hit5),
        "highOpportunity5": hit5,
        "closeOpportunity2": max(hit3, hit5),
        "closeOpportunity3": max(hit3, hit5),
        "closeOpportunity5": hit5,
        "auctionCloseOpportunity2": 0,
        "auctionCloseOpportunity3": 0,
        "auctionCloseOpportunity5": 0,
    })
    return result


class EligibilityTests(unittest.TestCase):
    def test_freshness_is_applied_before_ranking(self):
        rows = [row("STALE", score=999, valid=0)]
        rows += [row(str(index), score=100-index, valid=1, hit3=1) for index in range(8)]
        frame = BASE.prepare(pd.DataFrame(rows))
        eligible, selected = MOD.select_top5_after_eligibility(frame)
        self.assertNotIn("STALE", eligible.symbol.tolist())
        self.assertEqual(selected.symbol.tolist(), ["0", "1", "2", "3", "4"])
        self.assertTrue(selected.decisionPriceValid.eq(1).all())

    def test_random_expectation_uses_only_eligible_timestamp_universe(self):
        rows = [row("stale", score=999, valid=0, hit3=0)]
        rows += [row(str(index), score=100-index, hit3=1 if index < 2 else 0) for index in range(10)]
        rows += [row(f"b{index}", time="10:00", score=100-index, hit3=1 if index < 10 else 0) for index in range(20)]
        frame = BASE.prepare(pd.DataFrame(rows))
        eligible, selected = MOD.select_top5_after_eligibility(frame)
        metric = BASE.opportunity_metrics(eligible, selected, "highOpportunity", 3)
        self.assertAlmostEqual(metric["randomExpectedHits"], 3.5)
        self.assertAlmostEqual(metric["recallLift"], 2)

    def test_future_path_does_not_change_causal_selection(self):
        rows = [row(str(index), score=100-index, valid=1, hit3=1) for index in range(6)]
        rows[0]["futureBarCount"] = 0
        rows[0]["corrected30Evaluable"] = 0
        rows[0]["corrected30ReturnBps"] = np.nan
        rows[0]["mfe30Pct"] = np.nan
        rows[0]["mae30Pct"] = np.nan
        rows[0]["sessionMfePct"] = np.nan
        rows[0]["sessionMaePct"] = np.nan
        frame = BASE.prepare(pd.DataFrame(rows))
        eligible, selected = MOD.select_top5_after_eligibility(frame)
        self.assertIn("0", selected.symbol.tolist())
        coverage = MOD.evaluation_coverage(eligible, selected)["selectedTop5"]
        self.assertEqual(coverage["unavailableReasons"]["NO_FUTURE_CONTINUOUS_5M_FOR_HIGH"], 1)

    def test_report_is_aggregate_and_fit_free(self):
        frame = BASE.prepare(pd.DataFrame([row("1", hit3=1), row("2")]))
        manifest = {"model": {"artifactSha256": "x"}, "files": [], "sessionAudits": [], "_sha256": "input"}
        report = MOD.make_report(frame, manifest, "contract")
        encoded = __import__("json").dumps(report, allow_nan=False)
        self.assertNotIn('"symbol"', encoded)
        self.assertEqual(report["safety"]["fitCalls"], 0)
        self.assertEqual(report["scopes"]["FULL_SAVED_DEVELOPMENT"]["ridgeTop5"]["selectedEvents"], 2)


if __name__ == "__main__":
    unittest.main()
