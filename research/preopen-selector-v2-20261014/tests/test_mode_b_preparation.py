"""Independent small counts; no market originals or market authority."""
import copy
from datetime import date
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ark_selector_v2.census import census_diagnostics
from ark_selector_v2.contracts import Candle, feature_names
from ark_selector_v2.labels import label
from ark_selector_v2.native import NativeRows
from ark_selector_v2.exact_math import V2Error


class ModeBPreparation(unittest.TestCase):
    def fixture(self):
        days = ["2030-01-02", "2030-01-03"]
        records = [{"session": days[0], "canonical_symbol": s, "market": "PRIME"} for s in ("0001", "0002", "0003")]
        layers = {k: copy.deepcopy(records) for k in ("master", "price", "g0")}
        layers["g1"] = copy.deepcopy(records[1:]); layers["g2"] = copy.deepcopy(records[1:])
        rows = [r | {"values": {n: None for n in feature_names()}} for r in layers["g2"]]
        rows[0]["values"][feature_names()[0]] = 0.0
        teachers = {(days[0], "0001", "PRIME"): label(Candle.from_values(date(2030,1,2),100,106,99,103,100,10000)),
                    (days[0], "0002", "PRIME"): label(Candle.from_values(date(2030,1,2),100,106,95,102,100,10000))}
        return NativeRows("FIT", days, rows, {}, layers), teachers

    def test_b01_layer_winners_losers_unknown(self):
        r,t = self.fixture(); d = census_diagnostics(r,t)
        self.assertEqual(d["stages"]["master"]["clean_winner"]["5"], 1)
        self.assertEqual(d["stages"]["g2"]["raw_winner"]["5"], 1)
        self.assertEqual(d["stages"]["g2"]["clean_winner"]["5"], 0)
        self.assertEqual(d["stages"]["g2"]["raw_loser"], {"3":1,"5":1})
        self.assertEqual(d["stages"]["g2"]["unknownN"], 1)
        self.assertEqual(d["teacher_support_counts_before_admission"]["risk"]["2"], {"rows":1,"days":1,"symbols":1})
        self.assertEqual(d["teacher_support_counts_before_admission"]["opportunity_r0"]["5"]["rows"],0)

    def test_b02_big_winner_exclusion_baselines(self):
        r,t = self.fixture(); d = census_diagnostics(r,t)
        for base in ("master","price","g0"):
            self.assertEqual(d["big_winner_exclusions"][base]["clean_winner"]["5"]["missed_rate"], 1)

    def test_b03_feature_zero_observed_missing_not_zero(self):
        r,t = self.fixture(); f = census_diagnostics(r,t)["features"]
        self.assertEqual(len(f),95)
        self.assertEqual(f[feature_names()[0]]["observed_rate"], .5)
        self.assertEqual(f[feature_names()[1]]["missingN"], 2)

    def test_b04_oracle_calendar_denominator_and_cal_not_optimized(self):
        r,t = self.fixture(); t[(r.sessions[0],"0002","PRIME")] = t[(r.sessions[0],"0001","PRIME")]
        self.assertEqual(census_diagnostics(r,t)["fit_oracle_upper"], {"3":.5,"5":.5})
        r.role="CAL"; self.assertIsNone(census_diagnostics(r,t)["fit_oracle_upper"])

    def test_b05_evaluation_role_rejected(self):
        r,t = self.fixture(); r.role="VALIDATION"
        with self.assertRaisesRegex(V2Error,"FIT_CAL_ONLY"):census_diagnostics(r,t)

    def test_b06_teacher_date_leak_rejected(self):
        r,t = self.fixture(); t[("2030-02-01","0001","PRIME")] = next(iter(t.values()))
        with self.assertRaisesRegex(V2Error,"ROLE_LEAK"):census_diagnostics(r,t)

    def test_b07_empty_denominators_none_and_no_fit(self):
        r,t = self.fixture(); r.rows=[];r.layers={k:[] for k in r.layers}
        with patch("sklearn.ensemble.HistGradientBoostingClassifier.fit",side_effect=AssertionError("fit")):
            d=census_diagnostics(r,t)
        self.assertIsNone(d["big_winner_exclusions"]["g0"]["raw_winner"]["5"]["missed_rate"])
        self.assertIsNone(d["features"][feature_names()[0]]["missing_rate"])
        self.assertEqual(d["fit_oracle_upper"],{"3":0,"5":0})

    def test_b08_support_block_preserves_private_diagnostics_and_zero_fit(self):
        from ark_selector_v2.native_fixture import fixture_authority, request_for
        from ark_selector_v2.orchestration import dispatch, Store
        with tempfile.TemporaryDirectory(prefix="ark-v2-census-block-") as directory:
            a,m = fixture_authority(Path(directory)/"factory")
            with patch("ark_selector_v2.orchestration.teacher_support",side_effect=V2Error("BLOCKED_INSUFFICIENT_TEACHER_SUPPORT")), patch("sklearn.ensemble.HistGradientBoostingClassifier.fit") as fit:
                with self.assertRaisesRegex(V2Error,"INSUFFICIENT_TEACHER_SUPPORT"):
                    dispatch("census",request_for(a,m,"B"),authority=a)
                fit.assert_not_called()
            d=Store(a).get("census-diagnostics-FIT.json")
            self.assertEqual(d["stages"]["g2"]["N"],720)
            failure=Store(a).get("failure-census-FIT_CAL.json")
            self.assertTrue(failure["access"])
            self.assertFalse(any(x["purpose"] in {"VALIDATION_TEACHER","FINAL_TEACHER"} for x in failure["access"]))
            self.assertNotIn("census.json",a.artifact_pins)


if __name__ == "__main__": unittest.main()
