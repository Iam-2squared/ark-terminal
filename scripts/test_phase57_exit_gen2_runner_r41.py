"""Synthetic-only fit accounting, information boundaries and exact replay tests."""
from __future__ import annotations

from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning

from scripts import phase57_exit_gen2_runner_r41 as runner
from scripts import phase57_exit_gen2_runtime_r41 as runtime


class SyntheticClassifier:
    fits = 0

    def fit(self, x, y, sample_weight):
        type(self).fits += 1
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, x):
        return np.tile([0.6, 0.4], (len(x), 1))


class WarningClassifier(SyntheticClassifier):
    def fit(self, x, y, sample_weight):
        warnings.warn("synthetic nonconvergence", ConvergenceWarning)


class PoisonTargets:
    def __getitem__(self, key):
        raise AssertionError("future training target accessed during replay")


def fit_data():
    protocol = runtime.load_protocol()
    sessions = sorted({s for f in protocol["split"]["folds"] for k in ("train", "purge", "score") for s in f[k]})
    rows = [(s, a, ((s * 2 + a) * 4 + e), now, e) for s in range(len(sessions))
            for a in range(2) for e in range(4) for now in (541, 542, 543, 544, 925)]
    ns = len(rows)
    times = np.array([r[3] for r in rows])
    targets = np.array([[r[4] % 2, (r[4] + (r[3] % 2)) % 2] for r in rows], dtype=np.float32)
    targets[times == 925] = np.nan
    return SimpleNamespace(session_names=sessions,
        sessions=np.array([r[0] for r in rows]), arms=np.array([r[1] for r in rows]),
        entries=np.array([r[2] for r in rows]), now=times, fresh=np.ones(ns, dtype=bool),
        entry_ids=[str(i) for i in range(len(sessions) * 2 * 4)],
        categorical=np.zeros((ns, 1), dtype=np.int16), numeric=np.zeros((ns, 2), dtype=np.float32),
        pattern=np.zeros((ns, 2), dtype=np.float32), targets=targets,
        categorical_names=["state"], numeric_names=["x", "y"], pattern_names=["a", "b"])


def replay_data(*, missing_open=False, missing_terminal=False, complete=True):
    day = "2025-07-03"
    eid = day + "|TEST|540"
    oid = day + "|TEST"
    rows = [[540, 100, 101, 99, 100, 1, 100], [542, 103, 104, 102, 103, 1, 103],
            [924, 102, 103, 101, 102, 1, 102]]
    if not missing_open:
        rows.append([541, 100, 200, 99, 102, 1, 100])
    if not missing_terminal:
        rows.append([930, 102, 102, 102, 102, 1, 102])
    rows.sort()
    entry = {"session": day, "entryId": eid, "opportunity": oid, "entryMinute": 540, "price": 100.0}
    return SimpleNamespace(session_names=[day], sessions=np.zeros(3, dtype=int),
        arms=np.zeros(3, dtype=int), entries=np.zeros(3, dtype=int), now=np.array([541, 542, 925]),
        fresh=np.array([True, True, False]), entry_ids=["IMMEDIATE::" + eid],
        entry_rows={"IMMEDIATE::" + eid: entry}, raw={oid: {"today": rows}},
        opportunity_records={oid: {}}, targets=PoisonTargets(),
        numeric_names=["position.observedRunningHigh", "position.peakConfirmedAt", "position.fullOwnedPrefix"],
        numeric=np.array([[101, 541, int(complete)], [101, 541, int(complete)],
                          [104, 543, int(complete)]], dtype=np.float32))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.protocol = runtime.load_protocol()

    def test_all_sixteen_support_slices_and_independent_head_masks(self):
        data = fit_data()
        idx = int(np.flatnonzero((data.now == 541) & (data.arms == 0))[0])
        data.targets[idx, 0] = np.nan
        slices, report = runner.support_slices(data, self.protocol)
        self.assertEqual(len(slices), 16)
        continuation = next(x for x in slices if x[0]["fold"] == 1 and x[1] == "IMMEDIATE" and x[2] == 0)
        failure = next(x for x in slices if x[0]["fold"] == 1 and x[1] == "IMMEDIATE" and x[2] == 1)
        self.assertNotIn(idx, continuation[3])
        self.assertIn(idx, failure[3])
        self.assertEqual(report[0]["trainRows"] + 1, report[1]["trainRows"])

    def test_unsupported_last_arm_head_blocks_every_fit(self):
        data = fit_data()
        data.targets[data.arms == 1, 1] = np.nan
        with tempfile.TemporaryDirectory() as d, mock.patch.object(runner, "build_model") as build:
            with self.assertRaisesRegex(ValueError, "CLASS_SUPPORT"):
                runner.fit_predictions(data, Path(d), self.protocol)
            build.assert_not_called()
            self.assertFalse((Path(d) / "models").exists())

    def test_missing_class_or_insufficient_rows_never_fallback(self):
        data = fit_data()
        data.targets[np.isfinite(data.targets)] = 0
        with self.assertRaisesRegex(ValueError, "CLASS_SUPPORT"):
            runner.support_slices(data, self.protocol)
        protocol = copy.deepcopy(self.protocol)
        protocol["supportGate"]["minimumRowsPerFoldArmHead"] = 10**9
        with self.assertRaisesRegex(ValueError, "INSUFFICIENT_TRAIN_ROWS"):
            runner.support_slices(fit_data(), protocol)

    def test_terminal_target_or_duplicate_score_session_is_rejected(self):
        data = fit_data(); data.targets[data.now == 925, 0] = 1
        with self.assertRaisesRegex(ValueError, "TERMINAL_TARGET"):
            runner.support_slices(data, self.protocol)
        protocol = copy.deepcopy(self.protocol)
        protocol["split"]["folds"][1]["score"][0] = protocol["split"]["folds"][0]["score"][0]
        with self.assertRaisesRegex(ValueError, "OVERLAP|DUPLICATE_SCORE_SESSION"):
            runner.support_slices(fit_data(), protocol)

    @staticmethod
    def transform(data, train, score, include_pattern, dense, ridge):
        return np.ones((len(train), 2)), np.ones((len(score), 2)), None, None, None

    def test_exactly_64_fits_immutable_oof_925_nan_saved_bundles_and_no_rerun(self):
        SyntheticClassifier.fits = 0
        data = fit_data()
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()) as log, \
             mock.patch.object(runner, "build_model", side_effect=lambda _: SyntheticClassifier()), \
             mock.patch.object(runner.r36, "_fit_preprocess", side_effect=self.transform):
            out = Path(d)
            predictions, receipt = runner.fit_predictions(data, out, self.protocol)
            self.assertEqual(SyntheticClassifier.fits, 64)
            self.assertEqual(receipt["modelFits"], 64)
            self.assertEqual(len(list((out / "models").glob("*.joblib"))), 64)
            self.assertEqual(log.getvalue().count("FITTING_STARTED"), 1)
            for values in predictions.values():
                self.assertTrue(np.isnan(values[data.now == 925]).all())
                self.assertTrue(np.isnan(values[data.sessions == 0]).all())
            journal = [json.loads(line) for line in (out / "fit-progress.jsonl").read_text().splitlines()]
            self.assertEqual(len(journal), 128)
            with self.assertRaisesRegex(ValueError, "ONE_SHOT"):
                runner.fit_predictions(data, out, self.protocol)
            self.assertEqual(SyntheticClassifier.fits, 64)

    def test_convergence_warning_is_hard_failure_without_prediction_receipt(self):
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()), \
             mock.patch.object(runner, "build_model", return_value=WarningClassifier()), \
             mock.patch.object(runner.r36, "_fit_preprocess", side_effect=self.transform):
            with self.assertRaises(ConvergenceWarning):
                runner.fit_predictions(fit_data(), Path(d), self.protocol)
            self.assertFalse((Path(d) / "fit-receipt.json").exists())
            self.assertFalse((Path(d) / "oof-predictions.npz").exists())

    def test_estimators_match_all_frozen_parameters(self):
        for spec in self.protocol["predictionSpecs"]:
            model = runner.build_model(spec)
            for key, value in spec["parameters"].items():
                self.assertEqual(model.get_params()[key], value)

    def test_synthetic_model_preprocessor_integration_for_both_families(self):
        data = fit_data()
        train = np.flatnonzero((data.sessions < 2) & (data.now != 925))
        score = np.flatnonzero((data.sessions == 2) & (data.now != 925))
        for spec in self.protocol["predictionSpecs"]:
            dense = spec["family"] == "HGB"
            x, predicted_x, _, _, _ = runner.r36._fit_preprocess(
                data, train, score, spec["featureSet"].endswith("PATTERN187"), dense, not dense)
            model = runner.build_model(spec)
            with warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                model.fit(x, data.targets[train, 0], sample_weight=runner.r36.weights_for(data, train))
            values = model.predict_proba(predicted_x)
            self.assertEqual(model.classes_.tolist(), [0, 1])
            self.assertTrue(np.isfinite(values).all())
            self.assertTrue(np.allclose(values.sum(axis=1), 1))

    def test_preprocessor_uses_only_head_training_rows(self):
        data = fit_data()
        train, score = np.array([0, 1]), np.array([2])
        data.numeric[train] = [[1, np.nan], [3, np.nan]]
        data.numeric[score] = [[10000, 777]]
        data.categorical[train] = 0; data.categorical[score] = 99
        _, transformed, encoder, imputer, _ = runner.r36._fit_preprocess(data, train, score, False, False, True)
        self.assertEqual(imputer.statistics_.tolist(), [2.0, 0.0])
        self.assertEqual(encoder.categories_[0].tolist(), [0])
        self.assertEqual(transformed.shape[0], 1)

    def test_replay_never_reads_targets_and_exit_candle_high_is_not_owned(self):
        data = replay_data()
        scores = np.array([[0.2, 0.8], [0.9, 0.1], [np.nan, np.nan]], dtype=np.float32)
        rows = runner.replay_candidate(data, scores, self.protocol["candidates"][0], self.protocol)
        self.assertEqual(rows[0]["exitMinute"], 541)
        self.assertAlmostEqual(rows[0]["metrics"]["ownedPeakGivebackPp"], 1.0)
        self.assertGreater(rows[0]["earlyExitOpportunityCostPp"], 50)
        data.raw[next(iter(data.raw))]["today"][1][2] = 1000
        changed = runner.replay_candidate(data, scores, self.protocol["candidates"][0], self.protocol)
        self.assertEqual(changed[0]["exitMinute"], rows[0]["exitMinute"])
        self.assertEqual(changed[0]["exitPrice"], rows[0]["exitPrice"])
        self.assertEqual(changed[0]["metrics"]["ownedPeakGivebackPp"], 1.0)

    def test_incomplete_owned_prefix_is_null_after_scalar_transport(self):
        data = replay_data(complete=False)
        rows = runner.replay_candidate(data, np.tile([0.2, 0.8], (3, 1)),
                                       self.protocol["candidates"][0], self.protocol)
        self.assertIsNone(rows[0]["metrics"]["ownedPeakGivebackPp"])
        self.assertIsInstance(runner.position(data, 0)["observedRunningHigh"], float)

    def test_missing_open_does_not_queue_and_terminal_bypasses_missing_scores(self):
        data = replay_data(missing_open=True)
        rows = runner.replay_candidate(data, np.array([[0.2, 0.8], [0.9, 0.1], [np.nan, np.nan]]),
                                       self.protocol["candidates"][0], self.protocol)
        self.assertEqual(rows[0]["missingOrdinaryReferences"], 1)
        self.assertEqual(rows[0]["exitMinute"], 930)
        self.assertEqual(rows[0]["exitKind"], "FORCED_TERMINAL")
        self.assertEqual(rows[0]["decisionNow"], 925)

    def test_missing_terminal_unresolved_without_fabricated_return(self):
        data = replay_data(missing_terminal=True)
        rows = runner.replay_candidate(data, np.full((3, 2), np.nan),
                                       self.protocol["candidates"][0], self.protocol)
        self.assertEqual(rows[0]["exitStatus"], "UNRESOLVED_TERMINAL_EXIT")
        self.assertIsNone(rows[0]["exitMinute"])
        self.assertIsNone(rows[0]["netReturnPctBySellCost"]["0.05"])

    def test_replay_ab_uses_saved_scores_no_fit_or_scorecard_and_exact_16_policies(self):
        data = replay_data()
        with tempfile.TemporaryDirectory() as d, mock.patch.object(runner, "build_model") as model, \
             mock.patch.object(runner.r36, "full_scorecard", create=True) as scorecard:
            out = Path(d)
            predictions = {s["specId"]: np.array([[0.2, 0.8], [0.2, 0.8], [np.nan, np.nan]])
                           for s in self.protocol["predictionSpecs"]}
            np.savez_compressed(out / "oof-predictions.npz", **predictions)
            receipt = runner.replay_ab(data, out, self.protocol,
                {"predictionSha256": runner.sha(out / "oof-predictions.npz")})
            self.assertTrue(receipt["runABByteIdentical"])
            self.assertEqual(receipt["candidatePoliciesReplayed"], 16)
            self.assertEqual(len(receipt["ledgerHashes"]), 17)
            self.assertIsNone(receipt["selection"])
            model.assert_not_called(); scorecard.assert_not_called()
            with self.assertRaisesRegex(ValueError, "SAVED_PREDICTION_HASH"):
                runner.replay_ab(data, out, self.protocol, {"predictionSha256": "bad"})

    def test_fit_cache_hash_mismatch_precedes_pickle_or_model_access(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(runner.preflight, "source_manifest", return_value={}), \
             mock.patch.object(runner.pickle, "load") as deserialize, mock.patch.object(runner, "fit_predictions") as fit:
            out = Path(d); cache = out / "cache.pkl"; cache.write_bytes(b"corrupt")
            (out / "protocol.json").write_bytes(runtime.PROTOCOL_PATH.read_bytes())
            runner.write_json(out / "prepare-receipt.json", {"executionHead": "synthetic", "sourceSha256": {},
                "protocolSha256": runner.sha(runtime.PROTOCOL_PATH), "dependencies": {},
                "preparedCacheSha256": "incorrect", "preparedDataHashes": {}})
            with self.assertRaisesRegex(ValueError, "PREPARED_CACHE_HASH_MISMATCH"):
                runner.fit_replay(out, cache, self.protocol, "synthetic", {})
            deserialize.assert_not_called(); fit.assert_not_called()

    def test_partial_failures_are_append_only(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            first = runner.partial_failure(out, "prepare", ValueError("first"))
            original = first.read_bytes()
            second = runner.partial_failure(out, "fit-replay", ValueError("second"))
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
