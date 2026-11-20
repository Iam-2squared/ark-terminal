"""Frozen P1 contracts, integrity boundaries and synthetic inference tests.

No private original is available here and no estimator is fitted. Synthetic
archives, fake heads and manually constructed constant-tree estimator state
exercise engineering behavior, not historical model/OOF parity.
"""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
import warnings
import zipfile

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/no11_frozen_p1_score_replay.py"
MODULE_SPEC = importlib.util.spec_from_file_location("p1_score_replay_under_test", MODULE_PATH)
REPLAY = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(REPLAY)
CONTRACTS = REPLAY.load_contracts()
PREPROCESSOR, PERCENTILE = REPLAY.inference_primitives(CONTRACTS["source"], np)


def pin_bytes(data):
    return {"bytes": len(data), "sha256": REPLAY.digest(data)}


def synthetic_preprocessor(training_rows=4):
    prep = PREPROCESSOR()
    prep.median = np.arange(148, dtype=np.float64) + 1000
    prep.known = [[0, 2] for _ in range(15)]
    prep.training_rows = training_rows
    return prep


def synthetic_vocabulary():
    return [["zero", "unseen", "two", "another_unseen"] for _ in range(15)]


def constant_estimator(value, width, parameters=None):
    """Assemble inference-only state without calling fit, even on fake data."""
    from sklearn._loss.loss import HalfSquaredError
    from sklearn.ensemble._hist_gradient_boosting.binning import _BinMapper
    from sklearn.ensemble._hist_gradient_boosting.common import PREDICTOR_RECORD_DTYPE
    from sklearn.ensemble._hist_gradient_boosting.predictor import TreePredictor

    model = HistGradientBoostingRegressor(**(parameters or {}))
    model.n_features_in_ = width
    model.n_trees_per_iteration_ = 1
    model._preprocessor = None
    model._is_categorical_remapped = None
    model._baseline_prediction = np.array([[0.0]], dtype=np.float64)
    model._loss = HalfSquaredError()
    mapper = _BinMapper()
    mapper.is_categorical_ = np.zeros(width, dtype=np.uint8)
    mapper.bin_thresholds_ = [np.array([], dtype=np.float64) for _ in range(width)]
    model._bin_mapper = mapper
    nodes = np.zeros(1, dtype=PREDICTOR_RECORD_DTYPE)
    nodes["is_leaf"] = 1
    nodes["count"] = 1
    nodes["value"] = value
    empty_bitsets = np.zeros((0, 8), dtype=np.uint32)
    model._predictors = [[TreePredictor(nodes, empty_bitsets, empty_bitsets.copy())]]
    return model


class TemporaryFiles(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fit_guard = mock.patch.object(
            HistGradientBoostingRegressor, "fit",
            side_effect=AssertionError("ESTIMATOR_FIT_FORBIDDEN"))
        self.fit_guard.start()
        self.addCleanup(self.fit_guard.stop)

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path


class PublicContractTests(TemporaryFiles):
    def test_exact_feature_order_and_corrected_fifteen_model_lineage(self):
        spec = REPLAY.load_contracts()
        contract = json.loads((REPLAY.REPO / REPLAY.CORRECTED_REL
                               / "P1_Q70_ENTRY_CONTRACT.json").read_bytes())
        lineage = json.loads((REPLAY.REPO / REPLAY.CORRECTED_REL
                              / "CORRECTED_OOF_LINEAGE_RECEIPT.json").read_bytes())
        self.assertEqual(spec["feature"]["P1_numeric"],
                         contract["feature_manifest"]["P1_numeric"])
        self.assertEqual(spec["feature"]["P1_categorical"],
                         contract["feature_manifest"]["P1_categorical"])
        self.assertEqual(len(spec["feature"]["P1_numeric"]), 148)
        self.assertEqual(len(spec["feature"]["P1_categorical"]), 15)
        expected_models = {
            f"PRIVATE_MODELS/P1_F{fold}_{head}.pkl"
            for fold in range(1, 6) for head in ("UPSIDE", "QUALITY", "ADVERSE")
        }
        actual_models = {name for name in spec["corrected"]
                         if name.endswith(".pkl") and not name.endswith("_preprocessor.pkl")}
        self.assertEqual(actual_models, expected_models)
        for row in (r for r in lineage["model_lineage"] if r["family"] == "P1"):
            stem = f"PRIVATE_MODELS/P1_F{row['fold']}"
            self.assertEqual(spec["corrected"][stem + "_" + row["head"] + ".pkl"]["sha256"],
                             row["model_sha256"])
            expected = ("UNMODIFIED_ORIGINAL_UPSIDE_REUSE" if row["head"] == "UPSIDE"
                        else "CORRECTED_CALENDAR_Q_D_REFIT")
            self.assertEqual(row["lineage"], expected)
        self.assertEqual(spec["base_archive"]["sha256"],
                         "c0024055e9afa19089318c0f2a281e3fe15d48e10945b752be48e9239235ac15")
        self.assertEqual(spec["corrected_archive"]["sha256"],
                         "0ede654a0a730f78bebeb4fcec1c21503de80c7cb2950d205aaf87e7c79853b7")
        self.assertFalse(any("target" in p.lower() or p.startswith("OOF_")
                             for p in spec["corrected"]))

    def copy_public(self, crlf=False):
        for name in REPLAY.PUBLIC_PINS:
            data = (REPLAY.REPO / name).read_bytes().replace(b"\r\n", b"\n")
            self.write(name, data.replace(b"\n", b"\r\n") if crlf else data)

    def test_public_crlf_checkout_preserves_contract_and_source_pin(self):
        self.copy_public(crlf=True)
        copied = REPLAY.load_contracts(self.root)
        self.assertEqual(copied["source"], CONTRACTS["source"])
        self.assertEqual(copied["corrected"], CONTRACTS["corrected"])

    def test_public_modification_is_rejected(self):
        self.copy_public()
        name = REPLAY.BASE_REL + "/FEATURE_FREEZE.json"
        with (self.root / name).open("ab") as handle:
            handle.write(b" ")
        with self.assertRaisesRegex(ValueError, "P1_PUBLIC_SOURCE_PIN_MISMATCH"):
            REPLAY.load_contracts(self.root)

    def test_order_guard_rejects_same_features_in_a_different_order(self):
        self.copy_public()
        name = REPLAY.BASE_REL + "/FEATURE_FREEZE.json"
        for group in ("P1_numeric", "P1_categorical"):
            with self.subTest(group=group):
                feature = copy.deepcopy(CONTRACTS["feature"])
                feature[group][0], feature[group][1] = feature[group][1], feature[group][0]
                data = json.dumps(feature).encode()
                self.write(name, data)
                # Artificially trust only this fixture's bytes to reach the
                # independent feature-order contract check.
                with mock.patch.dict(REPLAY.PUBLIC_PINS, {name: REPLAY.digest(data)}):
                    with self.assertRaisesRegex(ValueError, "P1_FEATURE_ORDER_MISMATCH"):
                        REPLAY.load_contracts(self.root)


class PrimitiveAndMatrixTests(unittest.TestCase):
    def test_extracted_namespace_has_no_fit_run_or_training_import(self):
        cls, percentile = REPLAY.inference_primitives(CONTRACTS["source"], np)
        self.assertEqual({name for name in cls.__dict__ if not name.startswith("__")},
                         {"transform"})
        self.assertFalse(hasattr(cls, "fit"))
        for name in ("run", "HistGradientBoostingRegressor", "common", "model_oof"):
            self.assertNotIn(name, percentile.__globals__)
        with self.assertRaisesRegex(ValueError, "P1_SCORER_SOURCE_CHANGED"):
            REPLAY.inference_primitives(CONTRACTS["source"] + b"\n", np)

    def test_numeric_148_imputation_flags_and_fifteen_unseen_blocks(self):
        prep = synthetic_preprocessor()
        numeric = np.arange(296, dtype=np.float64).reshape(2, 148)
        numeric[0, 0], numeric[0, 1], numeric[1, 147] = np.nan, np.inf, -np.inf
        categories = np.array([[j % 3 for j in range(15)], [3] * 15], dtype=np.int32)
        original_numeric, original_categories = numeric.copy(), categories.copy()
        matrix = prep.transform(numeric, categories)
        self.assertEqual(matrix.shape, (2, 341))
        self.assertTrue(np.isfinite(matrix).all())
        self.assertEqual(matrix[0, 0], 1000.0)
        self.assertEqual(matrix[0, 1], 1001.0)
        self.assertEqual(matrix[1, 147], 1147.0)
        np.testing.assert_array_equal(matrix[0, 2:148], numeric[0, 2:148])
        np.testing.assert_array_equal(matrix[1, :147], numeric[1, :147])
        expected_flags = np.zeros((2, 148))
        expected_flags[0, :2] = 1
        expected_flags[1, 147] = 1
        np.testing.assert_array_equal(matrix[:, 148:296], expected_flags)
        for j in range(15):
            expected = {0: [1, 0, 0], 1: [0, 0, 1], 2: [0, 1, 0]}[j % 3]
            np.testing.assert_array_equal(matrix[0, 296 + 3*j:299 + 3*j], expected)
            np.testing.assert_array_equal(matrix[1, 296 + 3*j:299 + 3*j], [0, 0, 1])
        np.testing.assert_array_equal(numeric, original_numeric)
        np.testing.assert_array_equal(categories, original_categories)

    def test_midrank_percentiles_keep_ties_and_endpoint_orientation(self):
        values = PERCENTILE(np.array([1., 2., 2., 4.]),
                            np.array([0., 1., 1.5, 2., 3., 4., 5.]))
        np.testing.assert_array_equal(values, [0., .125, .25, .5, .75, .875, 1.])
        self.assertEqual(values.shape, (7,))

    def test_malformed_preprocessor_state_is_rejected(self):
        changes = {
            "extra_state": lambda p: setattr(p, "unexpected", True),
            "numeric_width": lambda p: setattr(p, "median", np.zeros(147)),
            "nonfinite_median": lambda p: p.median.__setitem__(0, np.nan),
            "wrong_training_rows": lambda p: setattr(p, "training_rows", 5),
            "missing_category_block": lambda p: p.known.pop(),
            "empty_known": lambda p: p.known.__setitem__(0, []),
            "unsorted": lambda p: p.known.__setitem__(0, [2, 0]),
            "duplicate": lambda p: p.known.__setitem__(0, [0, 0]),
            "negative": lambda p: p.known.__setitem__(0, [-1]),
            "outside_vocabulary": lambda p: p.known.__setitem__(0, [4]),
            "boolean_code": lambda p: p.known.__setitem__(0, [False]),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                prep = synthetic_preprocessor()
                change(prep)
                with self.assertRaisesRegex(ValueError, "P1_PREPROCESSOR_"):
                    REPLAY.validate_preprocessor(prep, synthetic_vocabulary(), 4, np)
        for values in ([], ["same", "same"], ["zero", 4]):
            with self.subTest(vocabulary=values):
                vocabulary = synthetic_vocabulary()
                vocabulary[0] = values
                with self.assertRaisesRegex(ValueError, "P1_PREPROCESSOR_"):
                    REPLAY.validate_preprocessor(synthetic_preprocessor(), vocabulary, 4, np)

    def fake_fold(self, predictions=None):
        fold = REPLAY.FrozenP1Fold.__new__(REPLAY.FrozenP1Fold)
        fold.np, fold.prep = np, synthetic_preprocessor()
        fold.vocab, fold.percentile = synthetic_vocabulary(), PERCENTILE
        fold.references = [np.array([1., 2., 2., 4.]) for _ in range(3)]
        arrays = predictions or ([1., 2., 4.], [4., 2., 1.], [2., 4., 1.])
        fold.models = [types.SimpleNamespace(predict=mock.Mock(return_value=np.asarray(a)))
                       for a in arrays]
        return fold

    def test_three_heads_adverse_direction_and_one_dimensional_scores(self):
        fold = self.fake_fold()
        pred, pct, scores = fold.score_batch(np.zeros((3, 148)),
                                             np.zeros((3, 15), dtype=np.int32))
        np.testing.assert_array_equal(pred, [[1., 4., 2.], [2., 2., 4.], [4., 1., 1.]])
        np.testing.assert_array_equal(pct, [[.125, .875, .5],
                                          [.5, .5, .875], [.875, .125, .125]])
        np.testing.assert_array_equal(scores, [.5, .375, .625])
        self.assertEqual(scores.shape, (3,))
        np.testing.assert_array_equal(scores >= .5, [True, False, True])
        for model in fold.models:
            self.assertEqual(model.predict.call_args.args[0].shape, (3, 341))
        directional = self.fake_fold(([2., 2.], [2., 2.], [1., 4.]))
        _, _, scores = directional.score_batch(np.zeros((2, 148)),
                                               np.zeros((2, 15), dtype=np.int32))
        self.assertGreater(scores[0], scores[1])

    def test_malformed_categories_and_nonfinite_predictions_are_rejected(self):
        cases = (np.zeros((3, 15), dtype=float),
                 np.full((3, 15), -1, dtype=np.int32),
                 np.full((3, 15), 4, dtype=np.int32),
                 np.zeros((3, 14), dtype=np.int32))
        for categories in cases:
            with self.subTest(shape=categories.shape, dtype=str(categories.dtype)):
                with self.assertRaisesRegex(ValueError, "P1_(FEATURE_MATRIX|CATEGORY_CODE)"):
                    self.fake_fold().score_batch(np.zeros((3, 148)), categories)
        fold = self.fake_fold(([np.nan]*3, [2.]*3, [2.]*3))
        with self.assertRaisesRegex(ValueError, "P1_PREDICTION_NOT_FINITE"):
            fold.score_batch(np.zeros((3, 148)), np.zeros((3, 15), dtype=np.int32))


class ArtifactIntegrityTests(TemporaryFiles):
    def test_hash_tampering_rejected_before_unpickler_construction(self):
        original = pickle.dumps({"harmless": 1})
        path = self.write("synthetic.pkl", original[:-1] + bytes([original[-1] ^ 1]))
        with mock.patch.object(REPLAY, "FrozenArtifactUnpickler") as unpickler:
            unpickler.side_effect = AssertionError("PICKLE_MUST_NOT_RUN")
            with self.assertRaisesRegex(ValueError, "P1_ARTIFACT_HASH_MISMATCH"):
                REPLAY.load_pickle(path, pin_bytes(original), PREPROCESSOR)
            unpickler.assert_not_called()

    def test_size_tampering_rejected_before_unpickler_construction(self):
        original = pickle.dumps({"harmless": 1})
        path = self.write("synthetic.pkl", original + b"extra")
        with mock.patch.object(REPLAY, "FrozenArtifactUnpickler") as unpickler:
            with self.assertRaisesRegex(ValueError, "P1_ARTIFACT_SIZE_MISMATCH"):
                REPLAY.load_pickle(path, pin_bytes(original), PREPROCESSOR)
            unpickler.assert_not_called()

    def test_hash_verified_unknown_pickle_global_is_still_rejected(self):
        data = pickle.dumps(eval, protocol=5)
        path = self.write("synthetic-global.pkl", data)
        with self.assertRaisesRegex(ValueError, "P1_PICKLE_GLOBAL_NOT_ALLOWED:builtins.eval"):
            REPLAY.load_pickle(path, pin_bytes(data), PREPROCESSOR)

    def test_verified_cython_short_loss_alias_resolves_only_squared_error(self):
        from sklearn._loss._loss import CyHalfSquaredError
        # Some saved sklearn pickles record the Cython extension's short
        # module name. This tiny GLOBAL fixture performs no model fitting.
        data = b"c_loss\nCyHalfSquaredError\n."
        path = self.write("synthetic-cython-alias.pkl", data)
        resolved = REPLAY.load_pickle(path, pin_bytes(data), PREPROCESSOR)
        self.assertIs(resolved, CyHalfSquaredError)
        for name in ("CyAbsoluteError", "__dict__", "unrecognized_loss"):
            with self.subTest(name=name):
                data = ("c_loss\n" + name + "\n.").encode()
                path.write_bytes(data)
                with self.assertRaisesRegex(ValueError, "P1_PICKLE_GLOBAL_NOT_ALLOWED"):
                    REPLAY.load_pickle(path, pin_bytes(data), PREPROCESSOR)

    def make_zip(self, scope="base", duplicate=False):
        relative = REPLAY.BASE_REL if scope == "base" else REPLAY.CORRECTED_REL
        name = "PRIVATE_INPUTS/synthetic-allowlisted.bin"
        member = "ark-terminal/" + relative + "/" + name
        data = b"synthetic fixture; not original market data"
        stream = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(member, data)
                archive.writestr("ark-terminal/" + relative + "/model_oof.py", "raise AssertionError()")
                archive.writestr("ark-terminal/" + relative + "/PRIVATE_INPUTS/targets.npy", b"not-read")
                archive.writestr("../../outside.txt", b"not-extracted")
                if duplicate:
                    archive.writestr(member, data)
        archive_bytes = stream.getvalue()
        path = self.write(scope + ".zip", archive_bytes)
        member_pin = pin_bytes(data)
        if scope == "corrected":
            member_pin["archive_path"] = member
        spec = {scope: {name: member_pin}, scope + "_archive": pin_bytes(archive_bytes)}
        return path, spec, name, data

    def test_zip_extracts_only_explicit_allowlist_and_reuses_verified_cache(self):
        for scope in ("base", "corrected"):
            with self.subTest(scope=scope):
                path, spec, name, data = self.make_zip(scope)
                private = self.root / ("private-" + scope)
                result = REPLAY.materialize(path, scope, spec, private)
                self.assertEqual(set(result), {name})
                self.assertEqual(result[name].read_bytes(), data)
                self.assertEqual([p for p in private.rglob("*") if p.is_file()], [result[name]])
                self.assertFalse((self.root / "outside.txt").exists())
                stat = result[name].stat()
                repeated = REPLAY.materialize(path, scope, spec, private)
                self.assertEqual(repeated, result)
                self.assertEqual(repeated[name].stat().st_mtime_ns, stat.st_mtime_ns)

    def test_zip_archive_size_hash_and_duplicate_names_are_rejected(self):
        path, spec, _, _ = self.make_zip()
        wrong_size = copy.deepcopy(spec)
        wrong_size["base_archive"]["bytes"] += 1
        with self.assertRaisesRegex(ValueError, "P1_ARTIFACT_SIZE_MISMATCH"):
            REPLAY.materialize(path, "base", wrong_size, self.root / "bad-size")
        wrong_hash = copy.deepcopy(spec)
        wrong_hash["base_archive"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "P1_ARTIFACT_HASH_MISMATCH"):
            REPLAY.materialize(path, "base", wrong_hash, self.root / "bad-hash")
        path, spec, _, _ = self.make_zip(duplicate=True)
        with self.assertRaisesRegex(ValueError, "P1_DUPLICATE_ZIP_MEMBER"):
            REPLAY.materialize(path, "base", spec, self.root / "duplicate")

    def test_zip_member_size_hash_and_existing_cache_tampering_are_rejected(self):
        path, spec, name, data = self.make_zip()
        wrong_size = copy.deepcopy(spec)
        wrong_size["base"][name]["bytes"] += 1
        with self.assertRaisesRegex(ValueError, "P1_ZIP_MEMBER_SIZE_MISMATCH"):
            REPLAY.materialize(path, "base", wrong_size, self.root / "member-size")
        wrong_hash = copy.deepcopy(spec)
        wrong_hash["base"][name]["sha256"] = "f" * 64
        private = self.root / "member-hash"
        with self.assertRaisesRegex(ValueError, "P1_ZIP_MEMBER_HASH_MISMATCH"):
            REPLAY.materialize(path, "base", wrong_hash, private)
        self.assertFalse(any(p.is_file() for p in private.rglob("*")))
        private = self.root / "cache"
        result = REPLAY.materialize(path, "base", spec, private)
        changed = b"x" + data[1:]
        result[name].write_bytes(changed)
        with self.assertRaisesRegex(ValueError, "P1_ARTIFACT_HASH_MISMATCH"):
            REPLAY.materialize(path, "base", spec, private)
        self.assertEqual(result[name].read_bytes(), changed)

    def test_verify_only_authenticates_artifacts_without_deserializing_or_replaying(self):
        base, base_spec, _, _ = self.make_zip("base")
        corrected, corrected_spec, _, _ = self.make_zip("corrected")
        own_spec = {**base_spec, **corrected_spec}
        for scope in ("base", "corrected"):
            own_spec[scope + "_archive"]["filename"] = scope + ".zip"
        output = io.StringIO()
        private = self.root / "precheck-private"
        with mock.patch.object(REPLAY, "load_contracts", return_value=own_spec):
            with mock.patch.object(REPLAY, "run_replay") as replay:
                with mock.patch.object(REPLAY, "FrozenArtifactUnpickler") as unpickler:
                    with contextlib.redirect_stdout(output):
                        code = REPLAY.main(["--private-root", str(private),
                                            "--base", str(base), "--corrected", str(corrected),
                                            "--verify-only"])
                    replay.assert_not_called()
                    unpickler.assert_not_called()
        self.assertEqual(code, 0)
        self.assertIn("PRECHECK=PASS", output.getvalue())
        self.assertNotIn("REPORT_JSON=", output.getvalue())
        self.assertEqual(list(private.glob("no11-frozen-p1-score-replay-*.json")), [])

    def test_real_sklearn_constant_tree_pickle_load_and_fold_predict_without_fit(self):
        prep = synthetic_preprocessor()
        width = REPLAY.validate_preprocessor(prep, synthetic_vocabulary(), 4, np)
        stem = "PRIVATE_MODELS/P1_F1"
        pins, files = {}, {}

        def save(name, data):
            files[name] = self.write(name, data)
            pins[name] = pin_bytes(data)

        calibration = {"training_score_N": 4, "thresholds": {p: .5 for p in REPLAY.POLICIES}}
        save(stem + "_calibration.json", json.dumps(calibration).encode())
        save("PRIVATE_INPUTS/category_vocabulary.json", json.dumps(synthetic_vocabulary()).encode())
        # Match the old pickle module name without executing/importing its code.
        placeholder = types.ModuleType("model_oof")
        placeholder.TrainPreprocessor = PREPROCESSOR
        with mock.patch.object(PREPROCESSOR, "__module__", "model_oof"):
            with mock.patch.dict(sys.modules, {"model_oof": placeholder}):
                save(stem + "_preprocessor.pkl", pickle.dumps(prep, protocol=5))
        for head, value in zip(REPLAY.HEADS, (.75, .5, .25)):
            model = constant_estimator(value, width, CONTRACTS["model_parameters"])
            save(stem + "_" + head + ".pkl", pickle.dumps(model, protocol=5))
            stream = io.BytesIO()
            np.save(stream, np.array([0., .25, .5, .75]), allow_pickle=False)
            save(stem + "_" + head + "_train_prediction_reference.npy", stream.getvalue())
        own_spec = {"corrected": pins, "calibration": {1: calibration},
                    "model_parameters": CONTRACTS["model_parameters"]}
        fold = REPLAY.FrozenP1Fold(1, own_spec, files, (PREPROCESSOR, PERCENTILE), np)
        self.assertTrue(all(type(model) is HistGradientBoostingRegressor for model in fold.models))
        pred, pct, score = fold.score_batch(np.zeros((2, 148)),
                                            np.zeros((2, 15), dtype=np.int32))
        np.testing.assert_array_equal(pred, [[.75, .5, .25]] * 2)
        np.testing.assert_array_equal(pct, [[.875, .625, .375]] * 2)
        np.testing.assert_allclose(score, [2.125 / 3] * 2, rtol=0, atol=0)


class ReplayControlFlowTests(TemporaryFiles):
    def setUp(self):
        super().setUp()
        x = np.zeros((10, 148), dtype=np.float64)
        x[:, 0] = np.arange(10)
        c = np.zeros((10, 15), dtype=np.int32)
        self.x_path, self.c_path = self.root / "x.npy", self.root / "c.npy"
        np.save(self.x_path, x, allow_pickle=False)
        np.save(self.c_path, c, allow_pickle=False)
        r = np.arange(10, dtype=np.float64)
        self.oracle = {
            "row_indices": np.arange(10), "fold": np.repeat(np.arange(1, 6), 2),
            "predictions": np.column_stack([r, r + 1, r + 2]),
            "percentiles": np.column_stack([r / 10, np.full(10, .5), np.full(10, .5)]),
            "score": (1 + r / 10) / 3,
            "thresholds": np.tile([.5, .6, .7, .8], (10, 1)),
        }
        self.oracle_path = self.root / "oracle.npz"
        self.paths = {
            "base": {"PRIVATE_INPUTS/features_numeric.npy": self.x_path,
                     "PRIVATE_INPUTS/features_categories.npy": self.c_path,
                     "WATCH_RECORDS.jsonl.gz": self.root / "unread-watch.gz",
                     "PERSISTENT_GRID.jsonl.gz": self.root / "unread-grid.gz"},
            "corrected": {"PRIVATE_INPUTS/oof_P1.npz": self.oracle_path,
                          "FIRST_INTENTS_PRIVATE.jsonl.gz": self.root / "unread-intents.gz"},
        }
        self.spec = {"source": CONTRACTS["source"],
                     "calibration": {
                         f: {"thresholds": dict(zip(REPLAY.POLICIES, [.5, .6, .7, .8]))}
                         for f in range(1, 6)},
                     "test_sessions": {f: {f"2025-06-{f:02d}"} for f in range(1, 6)}}
        self.first_cross = types.ModuleType("no11_frozen_p1_first_cross")
        self.first_cross.replay_and_compare = mock.Mock(return_value={"parity_passed": True})

    def run_synthetic_replay(self, sample):
        np.savez(self.oracle_path, **self.oracle)

        class FakeFold:
            def __init__(self, *args):
                pass

            def score_batch(self, numeric, categorical):
                # Predictions come from the newly supplied feature rows. The
                # oracle is never consulted by this fake inference head.
                row = numeric[:, 0]
                pred = np.column_stack([row, row + 1, row + 2])
                pct = np.column_stack([row / 10, np.full(len(row), .5),
                                       np.full(len(row), .5)])
                return pred, pct, (1 + row / 10) / 3

        with mock.patch.object(REPLAY, "OOF_ROWS", 10):
            report = REPLAY.new_report(sample)
            with mock.patch.object(REPLAY, "FrozenP1Fold", FakeFold):
                with mock.patch.dict(sys.modules, {"no11_frozen_p1_first_cross": self.first_cross}):
                    with contextlib.redirect_stdout(io.StringIO()):
                        REPLAY.run_replay(self.spec, self.paths, sample, report)
        return report

    def test_sample_does_not_claim_full_or_first_intent_parity(self):
        report = self.run_synthetic_replay(1)
        self.assertEqual(report["scoredRows"], 5)
        self.assertEqual(report["originalP1ModelsExecuted"], 15)
        self.assertTrue(report["scoreParityPassed"])
        self.assertFalse(report["fullOofReplay"])
        self.assertFalse(report["firstIntentParityPassed"])
        self.assertEqual(report["status"], "ORIGINAL_CORRECTED_P1_SAMPLED_SCORE_REPLAY_PASS")
        self.first_cross.replay_and_compare.assert_not_called()

    def test_full_replay_passes_recomputed_scores_to_first_cross(self):
        report = self.run_synthetic_replay(0)
        self.assertEqual(report["scoredRows"], 10)
        self.assertTrue(report["fullOofReplay"])
        self.assertTrue(report["firstIntentParityPassed"])
        scores = self.first_cross.replay_and_compare.call_args.args[4]
        np.testing.assert_array_equal(scores, (1 + np.arange(10) / 10) / 3)
        self.assertEqual(scores[5], .5)
        self.assertTrue(scores[5] >= .5)
        self.assertEqual(report["status"],
                         "ORIGINAL_CORRECTED_P1_FULL_OOF_SCORE_AND_FIRST_INTENT_REPLAY_PASS")

    def test_nextafter_below_equal_threshold_fails_despite_tiny_numeric_error(self):
        self.oracle["score"][5] = np.nextafter(.5, 0)
        self.assertLess(.5 - self.oracle["score"][5], REPLAY.ATOL)
        with self.assertRaisesRegex(ValueError, "P1_ORIGINAL_SCORE_PARITY_FAILED"):
            self.run_synthetic_replay(0)
        self.first_cross.replay_and_compare.assert_not_called()

    def test_wrong_saved_score_cannot_replace_fresh_model_inference(self):
        self.oracle["score"][0] += .01
        with self.assertRaisesRegex(ValueError, "P1_ORIGINAL_SCORE_PARITY_FAILED"):
            self.run_synthetic_replay(0)
        self.first_cross.replay_and_compare.assert_not_called()

    def test_failed_first_intent_comparison_does_not_certify_full_pass(self):
        self.first_cross.replay_and_compare.return_value = {"parity_passed": False}
        with self.assertRaisesRegex(ValueError, "P1_ORIGINAL_FIRST_INTENT_PARITY_FAILED"):
            self.run_synthetic_replay(0)


class CommandLineTests(TemporaryFiles):
    def run_cli(self, *extra):
        # -S removes site packages: missing-input handling must remain stdlib-only.
        return subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(MODULE_PATH),
             "--private-root", str(self.root / "private"), *extra],
            capture_output=True, text=True, check=False, timeout=30)

    def receipt(self, result):
        lines = [line for line in result.stdout.splitlines() if line.startswith("REPORT_JSON=")]
        self.assertEqual(len(lines), 1, result.stdout + result.stderr)
        path = Path(lines[0].split("=", 1)[1])
        self.assertEqual(path.parent, self.root / "private")
        data = path.read_bytes()
        self.assertEqual(path.name, "no11-frozen-p1-score-replay-" + REPLAY.digest(data)[:16] + ".json")
        return json.loads(data)

    def test_missing_arguments_emit_private_receipt_and_exit_two_without_dependencies(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        report = self.receipt(result)
        self.assertEqual(report["status"], "BLOCKED_PRIVATE_ORIGINAL_ARTIFACTS_MISSING")
        self.assertEqual(report["missingArtifacts"], ["base", "corrected"])
        self.assertEqual(report["newFits"], 0)
        self.assertEqual(report["originalP1ModelsExecuted"], 0)
        for field in ("scoreParityPassed", "firstIntentParityPassed", "fullOofReplay",
                      "productionReady", "orderTransmission", "targetsRead"):
            self.assertIs(report[field], False)

    def test_nonexistent_artifact_paths_emit_blocked_receipt_not_private_paths(self):
        missing = str(self.root / "private-do-not-publish-this-path.zip")
        result = self.run_cli("--base", missing, "--corrected", missing)
        self.assertEqual(result.returncode, 2, result.stderr)
        report = self.receipt(result)
        self.assertEqual(report["status"], "BLOCKED_ORIGINAL_P1_REPLAY")
        self.assertEqual(report["reason"], "P1_FILE_MISSING_OR_SYMLINK")
        self.assertNotIn("private-do-not-publish-this-path", json.dumps(report))
        self.assertFalse(report["privateArtifactsVerified"])

    def test_public_self_test_does_not_execute_private_model(self):
        result = self.run_cli("--self-test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("P1_PRIVATE_MODEL_EXECUTION=False", result.stdout)
        self.assertNotIn("REPORT_JSON=", result.stdout)
        self.assertFalse((self.root / "private").exists())


if __name__ == "__main__":
    unittest.main()
