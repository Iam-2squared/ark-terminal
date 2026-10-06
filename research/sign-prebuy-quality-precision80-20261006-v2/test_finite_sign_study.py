"""Synthetic causal/selection checks. No sklearn estimator.fit is called."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
from finite_sign_study import (QS, CANDIDATES, StageLabels, FiniteStudy, check_features,
    preprocess_fit, transform, threshold_info, metrics, select_pair, session_ci,
    midnight, verify_precommit, estimator)


def feature(key="2025-06-01|S", x=1., y=None, cat="a"):
    return {"entry_id": key, "session": key.split("|")[0], "intent_minute": 600,
            "supported": True, "input_asof": key.split("|")[0]+"T10:00:00+09:00",
            "numeric": {"x": x, "y": y}, "categorical": {"cat": cat}}


class FiniteSignChecks(unittest.TestCase):
    def test_fit_only_statistics_missing_and_unknown(self):
        spec = {"numeric": ["x", "y"], "categorical": ["cat"]}
        fit = [feature(x=1), feature(key="2025-06-02|S", x=3, cat=None)]
        prep = preprocess_fit(fit, spec, True)
        self.assertEqual(prep["median"], [2., 0.])
        before = json.dumps(prep, sort_keys=True)
        matrix = transform([feature(x=999999, cat="UNSEEN")], prep)
        self.assertEqual(matrix[0, -len(prep["vocabulary"]["cat"])+prep["vocabulary"]["cat"].index("UNKNOWN")], 1)
        self.assertEqual(before, json.dumps(prep, sort_keys=True))
        self.assertFalse(np.isnan(matrix).any())

    def test_intent_boundary_and_magnitude_fields_blocked(self):
        reps = {"BASE": {"numeric": ["x", "y"], "categorical": ["cat"]}}
        good = feature()
        check_features([good], reps)
        bad = feature()
        bad["input_asof"] = "2025-06-01T10:00:01+09:00"
        with self.assertRaisesRegex(ValueError, "INPUT_AFTER_INTENT"):
            check_features([bad], reps)
        with self.assertRaisesRegex(ValueError, "FORBIDDEN_FEATURE"):
            check_features([], {"BASE": {"numeric": ["future_return"], "categorical": []}})

    def test_stage_reader_skips_other_signs_and_enforces_maturity(self):
        with TemporaryDirectory() as folder:
            p = Path(folder)/"labels.jsonl"
            p.write_text('\n'.join(json.dumps(r) for r in [
                {"entry_id": "2025-06-01|A", "sign": "PLUS", "matured_at": "2025-06-01T15:31:00+09:00"},
                {"entry_id": "2025-06-01|B", "sign": "MINUS", "matured_at": "2025-06-02T00:00:00+09:00"},
                {"entry_id": "2025-06-20|A", "sign": "OUTSIDE_STAGE_POISON", "pnl": 999},
            ]))
            reader = StageLabels(p)
            result = reader.read(["2025-06-01"], "FIT", midnight("2025-06-02"))
            self.assertEqual(set(result), {"2025-06-01|A"})
            self.assertEqual(reader.access[0]["sessions"], ["2025-06-01"])
            with self.assertRaisesRegex(ValueError, "LABEL_MAGNITUDE"):
                reader.read(["2025-06-20"], "FORBIDDEN_TEST")

    def test_cal_quantile_ties_and_qualification(self):
        rows = [{"session": f"2025-06-0{i%5+1}", "sign": "PLUS" if i < 50 else "MINUS",
                 "score": .9 if i < 50 else .1} for i in range(100)]
        result = threshold_info(rows, .5)
        self.assertEqual(result["tau"], .5)
        self.assertTrue(result["qualified"])
        self.assertEqual(result["pass_N"], 50)
        self.assertEqual(threshold_info(rows, .85)["pass_N"], 50)
        for r in rows:
            r["score"] = .7
        self.assertFalse(threshold_info(rows, .5)["qualified"])
        self.assertFalse(threshold_info([], .5)["qualified"])

    def test_original_teacher_schema_is_stage_normalized_without_amounts(self):
        with TemporaryDirectory() as folder:
            p = Path(folder)/"labels.jsonl"
            original = {"entry_id": "2025-06-01|A", "session": "2025-06-01",
                        "sign_status": "EXACT_ZERO", "y_plus": None,
                        "label_maturity": "2025-06-01T15:31:00+09:00", "source_hash": "a"*64}
            later = {"entry_id": "2025-06-20|A", "session": "2025-06-20",
                     "sign_status": "FUTURE_POISON", "y_plus": "FUTURE_POISON"}
            p.write_text(json.dumps(original)+"\n"+json.dumps(later)+"\n")
            out = StageLabels(p).read(["2025-06-01"], "FIT", midnight("2025-06-02"))
            self.assertEqual(out[original["entry_id"]]["sign"], "ZERO")
            self.assertNotIn("source_hash", out[original["entry_id"]])
            original.update(sign_status="PLUS", y_plus=0)
            p.write_text(json.dumps(original)+"\n")
            with self.assertRaisesRegex(ValueError, "ORIGINAL_SIGN_DIRECTION"):
                StageLabels(p).read(["2025-06-01"], "FIT")

    def test_zero_unknown_abstain_are_separate_and_rejection_not_accuracy(self):
        labels = {str(i): {"sign": s} for i, s in enumerate(["PLUS", "MINUS", "ZERO", "UNKNOWN"])}
        rows = [{"entry_id": str(i), "session": "2025-06-01", "score": None, "pass": False} for i in range(4)]
        filt, binary = metrics(rows, labels), metrics(rows, labels, "binary")
        self.assertEqual(filt["FN"], 1)
        self.assertEqual(filt["TN"], 1)
        self.assertIsNone(filt["PLUS_precision"])
        self.assertEqual(binary["known_N"], 0)
        self.assertIsNone(binary["accuracy"])
        self.assertEqual(filt["status_counts"]["ZERO"], 1)
        self.assertEqual(filt["status_counts"]["UNKNOWN"], 1)
        self.assertEqual(filt["status_counts"]["ABSTAIN_N"], 4)
        with self.assertRaisesRegex(ValueError, "LABEL_JOIN_MISSING_NOT_UNKNOWN"):
            metrics(rows, {})

    def test_legacy_execution_eligibility_is_not_input_support(self):
        reps = {"BASE": {"numeric": ["x", "y"], "categorical": ["cat"]}}
        row = feature()
        row["execution_eligible"] = False
        check_features([row], reps)
        self.assertTrue(row["supported"])
        row["supported"] = False
        row["input_asof"] = None
        check_features([row], reps)

    def test_fixed_pair_selection_and_cal_block_gate(self):
        def aggregate(name, q, tp=80, fp=20, fn=80, tn=320, qualified=3):
            return {"candidate": name, "q": q, "qualified_CAL_blocks": qualified,
                    "filter": {"TP": tp, "FP": fp, "FN": fn, "TN": tn,
                               "PLUS_precision": tp/(tp+fp), "PLUS_retention": tp/(tp+fn),
                               "known_pass_N": tp+fp, "pass_sessions_N": 8,
                               "known_pass_fraction": (tp+fp)/(tp+fp+fn+tn)}}
        first = aggregate(CANDIDATES[0][0], QS[0])
        second = aggregate(CANDIDATES[1][0], QS[1])
        self.assertEqual(select_pair([second, first]), first)
        self.assertIsNone(select_pair([aggregate(CANDIDATES[0][0], .5, qualified=2)]))
        self.assertEqual(select_pair([first, aggregate(CANDIDATES[1][0], .5, tp=84, fp=16, fn=56)] ) ["candidate"], CANDIDATES[1][0])

    def test_precommit_blocks_before_any_fitting(self):
        with self.assertRaisesRegex(ValueError, "FROZEN_PRECOMMIT"):
            verify_precommit({"frozen": False}, {}, "a", "b", "c", "d")

    def test_confirmation_requires_external_actual_get_before_trial(self):
        with TemporaryDirectory() as folder:
            study = object.__new__(FiniteStudy)
            study.private = Path(folder)
            study.precommit = "synthetic"
            (study.private/"PAIR_LOCK.json").write_text(json.dumps({"candidate": CANDIDATES[0][0],
                    "q": .5, "config_sha256": "synthetic"}))
            study.trial = lambda *args: self.fail("confirmation fit reached")
            with self.assertRaisesRegex(ValueError, "ACTUAL_GET_REQUIRED"):
                study.run_confirmation({"actual_get_verified": False})

    def test_transform_failure_does_not_count_an_estimator_fit(self):
        with TemporaryDirectory() as folder:
            study = object.__new__(FiniteStudy)
            dates = [f"2025-06-{i:02d}" for i in range(1, 11)]
            study.rows = [feature(key=f"{day}|S{j}") for day in dates for j in range(10)]
            targets = {r["entry_id"]: {"sign": "PLUS" if i%2 else "MINUS", "matured_at": r["session"]+"T15:31:00+09:00"}
                       for i, r in enumerate(study.rows)}
            class FakeLabels:
                def read(self, sessions, purpose, before=None):
                    return {k: v for k, v in targets.items() if k.split("|")[0] in sessions}
            study.labels = FakeLabels()
            study.private = Path(folder)
            study.ledger_path = study.private/"FIT_LEDGER.json"
            study.ledger = {"actual_model_fit_calls": 0, "preprocessing_fits": 0, "attempts": []}
            study.config = {"representations": {"BASE": {"numeric": ["x", "y"], "categorical": ["cat"]}},
                            "resolved_parameters": {"LOGISTIC": estimator("LOGISTIC").get_params()}, "versions": {}}
            block = {"block": 1, "FIT": dates, "CAL": ["2025-06-11"], "TEST": ["2025-06-12"]}
            with patch("finite_sign_study.transform", side_effect=ValueError("synthetic transform failure")):
                with self.assertRaisesRegex(ValueError, "synthetic transform failure"):
                    study.trial(CANDIDATES[0], block, "DISCOVERY")
            self.assertEqual(study.ledger["actual_model_fit_calls"], 0)

    def test_no_qualified_discovery_does_not_read_confirmation(self):
        class FakeLabels:
            def __init__(self): self.access = []
            def read(self, sessions, purpose, before=None):
                self.access.append({"purpose": purpose})
                if "CONFIRMATION" in purpose: raise AssertionError("confirmation opened")
                return {"2025-06-01|A": {"sign": "MINUS"}}
        with TemporaryDirectory() as folder:
            study = object.__new__(FiniteStudy)
            study.private = Path(folder)/"private"
            study.public = Path(folder)/"public"
            study.precommit = "synthetic"
            study.labels = FakeLabels()
            study.ledger = {"actual_model_fit_calls": 0}
            study.config = {"blocks": [{"block": i, "TEST": ["2025-06-01"]} for i in range(1, 9)]}
            def fake_trial(candidate, block, phase):
                self.assertEqual(phase, "DISCOVERY")
                return {"candidate": candidate[0], "block": block["block"],
                        "thresholds": [{"qualified": False} for _ in QS],
                        "predictions": [{"entry_id": "2025-06-01|A", "session": "2025-06-01",
                                         "score": .1, "actions": {str(q): False for q in QS}}]}
            study.trial = fake_trial
            study.run()
            result = json.loads((study.public/"RESULT.json").read_text())
            self.assertEqual(result["confirmation_signs_graded"], 0)
            self.assertEqual(result["ledger"]["actual_model_fit_calls"], 0)

    def test_bootstrap_is_fixed_session_resampling_without_fit(self):
        rows = [{"entry_id": str(i), "session": f"2025-06-0{i%3+1}", "score": .8, "pass": True}
                for i in range(6)]
        labels = {str(i): {"sign": "PLUS" if i%2 == 0 else "MINUS"} for i in range(6)}
        self.assertEqual(session_ci(rows, labels), session_ci(rows, labels))


if __name__ == "__main__":
    unittest.main()
