#!/usr/bin/env python3
import copy
import unittest

from scripts import phase57_entry_all_material_evaluator_v1 as subject
from scripts import phase57_state_conditioned_signal_entry_v1 as base


def opportunity(index, mfe):
    return {
        "opportunity": f"o{index}",
        "session": f"2026-09-{index:02d}",
        "symbol": f"{1000 + index}.T",
        "selectorPrice": 100.0,
        "selectorOutcome": {"mfeEnd": mfe},
    }


def horizon(mfe=1.0, mae=-0.5, ret=0.2):
    return {"status": "AVAILABLE", "MFE": mfe, "MAE": mae, "returnNet": ret}


def record(index, *, entered=True, candidate_mfe=5.0, pos=0.2, low_pct=0.5,
           remaining_pct=2.0, state="DROP", price=100.5):
    return {
        "opportunity": f"o{index}",
        "session": f"2026-09-{index:02d}",
        "symbol": f"{1000 + index}.T",
        "initialState": state,
        "sourceArm": "TEST",
        "policyAction": "WAIT",
        "stateAtIntent": state,
        "intentSignals": [],
        "intentReason": "SIGNAL" if entered else "NO_ENTRY",
        "intentMinute": f"2026-09-{index:02d}T09:31:00+09:00" if entered else None,
        "entryId": f"e{index}" if entered else None,
        "entryMinute": f"2026-09-{index:02d}T09:32:00+09:00" if entered else None,
        "price": price if entered else None,
        "delay": 2 if entered else None,
        "unfilledReason": None if entered else "NO_SIGNAL",
        "fallbackTargetDelay": None,
        "waitMaxRiseVsImmediatePct": 0.1,
        "quality": {
            "selectorToEntryPrice": 0.5 if entered else None,
            "selectorToEntryPct": 0.5 if entered else None,
            "priceImprovementVsSelectorPct": -0.5 if entered else None,
            "lowToEntryPrice": 0.5 if entered else None,
            "lowToEntryDistancePct": low_pct if entered else None,
            "entryToLaterHighPrice": 2.0 if entered else None,
            "entryToLaterHighRemainingUpsidePct": remaining_pct if entered else None,
            "entryPosition": pos if entered else None,
            "rangeRetentionPct": 50.0 if entered else None,
            "oracleEvaluable": bool(entered),
            "laterHighEvaluable": bool(entered),
        },
        "labels": {
            "30": horizon() if entered else None,
            "60": horizon(1.5, -0.7, 0.3) if entered else None,
            "mfeEnd": candidate_mfe if entered else None,
            "maeEnd": -1.0 if entered else None,
            "returnEnd": 0.4 if entered else None,
            "status": "AVAILABLE" if entered else "NO_ENTRY",
        },
    }


class AllMaterialEvaluatorTests(unittest.TestCase):
    def setUp(self):
        mfes = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
        self.opportunities = [opportunity(i + 1, mfe) for i, mfe in enumerate(mfes)]
        self.records = [
            record(1, candidate_mfe=0.5, pos=0.05, low_pct=0.1),
            record(2, candidate_mfe=1.5, pos=0.10, low_pct=0.2),
            record(3, candidate_mfe=2.5, pos=0.15, low_pct=0.3),
            record(4, candidate_mfe=3.5, pos=0.25, low_pct=0.4),
            record(5, candidate_mfe=3.0, pos=0.50, low_pct=0.5),
            record(6, entered=False),
        ]

    def test_canonical_capture_parity_and_plus4(self):
        extended = subject.capture_extended(self.opportunities, self.records)
        canonical = base.capture(self.opportunities, self.records)
        for level in base.LEVELS:
            self.assertEqual(extended[str(level)], canonical[str(level)])
        self.assertEqual(extended["4"]["selectorWinnerDenominator"], 2)
        self.assertEqual(extended["4"]["captured"], 0)
        self.assertEqual(extended["4"]["noEntry"], 1)
        self.assertEqual(extended["4"]["belowThreshold"], 1)

    def test_threshold_denominators_are_distinct(self):
        panels = subject.upside_threshold_panels(self.opportunities, self.records)
        self.assertEqual([panels[str(k)]["denominator"] for k in subject.LEVELS],
                         [5, 4, 3, 2, 1])

    def test_future_mfe_bucket_boundaries(self):
        buckets = subject.future_mfe_bucket_panels(self.opportunities, self.records)
        self.assertEqual(buckets["lt1"]["denominator"], 1)
        self.assertEqual(buckets["1to2"]["denominator"], 1)
        self.assertEqual(buckets["2to3"]["denominator"], 1)
        self.assertEqual(buckets["3to4"]["denominator"], 1)
        self.assertEqual(buckets["4to5"]["denominator"], 1)
        self.assertEqual(buckets["ge5"]["denominator"], 1)
        self.assertEqual(buckets["missing"]["denominator"], 0)

    def test_position_rates_and_bps(self):
        panel = subject.policy_panel(self.opportunities, self.records)
        self.assertEqual(panel["entryPosition"]["count"], 5)
        self.assertEqual(panel["entryPositionThresholds"]["le10Pct"]["count"], 2)
        self.assertEqual(panel["entryPositionThresholds"]["le15Pct"]["count"], 3)
        self.assertEqual(panel["entryPositionThresholds"]["le25Pct"]["count"], 4)
        self.assertEqual(panel["entryPositionThresholds"]["le50Pct"]["count"], 5)
        self.assertAlmostEqual(panel["lowToEntryDistancePct"]["mean"], 0.3)
        self.assertAlmostEqual(panel["lowToEntryDistanceBps"]["mean"], 30.0)

    def test_evaluate_has_state_and_paired_baseline(self):
        baseline = copy.deepcopy(self.records)
        for row in baseline:
            if row["entryId"]:
                row["price"] += 1.0
                row["quality"]["entryPosition"] += 0.1
                row["quality"]["lowToEntryDistancePct"] += 0.1
        result = subject.evaluate(
            self.opportunities, self.records, "candidate",
            baseline_records=baseline, baseline_name="baseline",
        )
        self.assertTrue(result["evaluatorOnly"])
        self.assertEqual(result["decisionOutputsCreated"], 0)
        self.assertTrue(all(result["canonicalCaptureParity"].values()))
        self.assertIn("DROP", result["byState"])
        self.assertIn("commonCasePaired", result["baselineComparison"])
        self.assertTrue(all(value is False for value in result["safety"].values()))

    def test_id_mismatch_fails_closed(self):
        broken = copy.deepcopy(self.records[:-1])
        with self.assertRaises(AssertionError):
            subject.evaluate(self.opportunities, broken, "broken")


if __name__ == "__main__":
    unittest.main()
