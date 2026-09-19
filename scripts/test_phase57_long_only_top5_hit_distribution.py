#!/usr/bin/env python3
"""Synthetic tests for aggregate Top5 hit distributions; no fit or Development data."""
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


def load_module(name, filename):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[name] = module
    return module


BASE = load_module("run_phase57_long_only_corrected_measurement", "run_phase57_long_only_corrected_measurement.py")
ELIGIBILITY = load_module("run_phase57_long_only_eligibility_measurement", "run_phase57_long_only_eligibility_measurement.py")
MOD = load_module("top5_hit_distribution", "run_phase57_long_only_top5_hit_distribution.py")


def row(symbol, time="09:30", score=1, high=0, close=0, valid=1):
    result = {column: 0.0 for column in BASE.NUMERIC}
    result.update({
        "sessionDate": "2024-01-10",
        "symbol": str(symbol),
        "decisionTimeJst": time,
        "partition": "DEVELOPMENT_A",
        "sourceGroup": "L1",
        "segment": "PRIME",
        "liquidityBucket": "HIGH",
        "decisionPriceKind": "LATEST_ACCEPTED_MINUTE_CLOSE" if valid else "NONE",
        "corrected30EndpointKind": "CONTINUOUS_5M_CLOSE" if valid else "NONE",
        "firstCloseHitKind1": "NONE",
        "firstCloseHitKind2": "NONE",
        "firstCloseHitKind3": "NONE",
        "firstCloseHitKind5": "NONE",
        "decisionPrice": 100 if valid else np.nan,
        "decisionPriceValid": valid,
        "referenceAgeMin": 0 if valid else 20,
        "corrected30Evaluable": valid,
        "corrected30ReturnBps": 100 if valid else np.nan,
        "mfe30Pct": max(high, 0) if valid else np.nan,
        "mae30Pct": -1 if valid else np.nan,
        "sessionMfePct": max(high, 0) if valid else np.nan,
        "sessionMaePct": -1 if valid else np.nan,
        "savedV1Score": score,
        "futureBarCount": 10 if valid else 0,
    })
    for level in MOD.THRESHOLDS:
        high_hit = int(high >= level)
        close_hit = int(close >= level)
        result[f"highOpportunity{level}"] = high_hit
        result[f"closeOpportunity{level}"] = close_hit
        result[f"auctionCloseOpportunity{level}"] = 0
        result[f"timeToHigh{level}Min"] = 5 * level if high_hit else np.nan
        result[f"timeToClose{level}Min"] = 10 * level if close_hit else np.nan
    return result


class HitDistributionTests(unittest.TestCase):
    def frame(self):
        rows = [row(f"a{i}", score=100-i, high=5 if i < 3 else 0, close=3 if i < 2 else 0) for i in range(8)]
        rows += [row(f"b{i}", time="10:00", score=100-i, high=1 if i < 1 else 0, close=1 if i < 1 else 0) for i in range(8)]
        return BASE.prepare(pd.DataFrame(rows))

    def test_distribution_counts_each_decision(self):
        frame = self.frame()
        _, selected = ELIGIBILITY.select_top5_after_eligibility(frame)
        result = MOD.hit_distribution(selected, "highOpportunity", 3)
        self.assertEqual(result["decisions"], 2)
        self.assertEqual(result["distribution"]["0"]["decisionCount"], 1)
        self.assertEqual(result["distribution"]["3"]["decisionCount"], 1)
        self.assertEqual(result["meanHitsPerTop5"], 1.5)
        self.assertEqual(result["probabilityPct"]["GE1"], 50)

    def test_repeat_symbol_is_counted_at_each_decision(self):
        rows = [row("REPEAT", time=time, score=100, high=5, close=5) for time in ["09:30", "10:00"]]
        for time in ["09:30", "10:00"]:
            rows += [row(f"{time}-{i}", time=time, score=90-i) for i in range(5)]
        frame = BASE.prepare(pd.DataFrame(rows))
        _, selected = ELIGIBILITY.select_top5_after_eligibility(frame)
        result = MOD.hit_distribution(selected, "highOpportunity", 5)
        self.assertEqual(result["distribution"]["1"]["decisionCount"], 2)

    def test_close_confirmation_is_separate(self):
        frame = self.frame()
        universe, selected = ELIGIBILITY.select_top5_after_eligibility(frame)
        high = BASE.opportunity_metrics(universe, selected, "highOpportunity", 3)
        close = BASE.opportunity_metrics(universe, selected, "closeOpportunity", 3)
        self.assertEqual(high["selectedHits"], 3)
        self.assertEqual(close["selectedHits"], 2)

    def test_report_is_aggregate_and_fit_free(self):
        rows = []
        for time in sum(MOD.TIME_GROUPS.values(), []):
            rows += [row(f"{time}-{index}", time=time, score=100-index, high=5 if index < 2 else 0, close=3 if index < 1 else 0)
                     for index in range(6)]
        frame = BASE.prepare(pd.DataFrame(rows))
        manifest = {
            "contractId": BASE.CONTRACT,
            "model": {"artifactSha256": "saved"},
            "files": [],
            "sessionAudits": [],
            "_sha256": "input",
        }
        report = MOD.make_report(frame, manifest, "contract")
        encoded = __import__("json").dumps(report, allow_nan=False)
        self.assertNotIn('"symbol"', encoded)
        self.assertEqual(report["safety"]["fitCalls"], 0)
        self.assertEqual(report["dataAudit"]["top5SelectionEvents"], 50)


if __name__ == "__main__":
    unittest.main()
