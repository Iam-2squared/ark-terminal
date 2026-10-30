"""Named category inference boundaries; no original model is fitted or changed.

The pinned original transform and percentile function are exercised with an
explicit synthetic vocabulary, saved preprocessor state and inference-only
heads. Historical model parity is covered by the separate private replay.
"""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

import numpy as np


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/no11_frozen_p1_score_replay.py"
MODULE_SPEC = importlib.util.spec_from_file_location("p1_named_inputs_under_test", MODULE_PATH)
REPLAY = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(REPLAY)
CONTRACTS = REPLAY.load_contracts()
PREPROCESSOR, PERCENTILE = REPLAY.inference_primitives(CONTRACTS["source"], np)


class NamedCategoryTests(unittest.TestCase):
    def setUp(self):
        self.fold = REPLAY.FrozenP1Fold.__new__(REPLAY.FrozenP1Fold)
        self.fold.np = np
        self.fold.vocab = [
            ["JQuants", "__MISSING__", "__UNKNOWN_HISTORY__", "__FORMAL_NULL__",
             f"fold_unseen_{j}"] + [f"extra_{j}_{k}" for k in range(j % 3)]
            for j in range(15)
        ]
        self.fold.prep = PREPROCESSOR()
        self.fold.prep.median = np.arange(148, dtype=np.float64) + 10
        self.fold.prep.known = [[0, 1, 2, 3] for _ in range(15)]
        self.fold.prep.training_rows = 4
        self.fold.percentile = PERCENTILE
        width = 296 + 15 * 5
        self.fold.models = []
        for head in range(3):
            # Distinct fixed projections make category-routing mistakes visible
            # in predictions without constructing or fitting a learned model.
            weights = np.arange(1, width + 1, dtype=np.float64) / (head + 1)
            model = mock.Mock()
            model.predict = mock.Mock(side_effect=lambda matrix, w=weights: matrix @ w)
            model.fit = mock.Mock(side_effect=AssertionError("MODEL_FIT_FORBIDDEN"))
            self.fold.models.append(model)
        self.fold.references = [np.arange(0., 20000., .5) for _ in range(3)]
        self.assertFalse(hasattr(self.fold.prep, "fit"))
        self.fit_guard = mock.patch(
            "sklearn.ensemble.HistGradientBoostingRegressor.fit",
            side_effect=AssertionError("ESTIMATOR_FIT_FORBIDDEN"))
        self.real_fit = self.fit_guard.start()
        self.addCleanup(self.fit_guard.stop)

    def tearDown(self):
        self.real_fit.assert_not_called()
        for model in self.fold.models:
            model.fit.assert_not_called()

    @staticmethod
    def names(rows=1):
        return np.full((rows, 15), "JQuants", dtype=object)

    @staticmethod
    def numeric(rows=1):
        return np.zeros((rows, 148), dtype=np.float64)

    def assert_no_prediction(self):
        for model in self.fold.models:
            model.predict.assert_not_called()

    def test_known_named_matches_original_integer_path_exactly(self):
        codes = np.asarray([[i % 5 for _ in range(15)] for i in range(5)], dtype=np.int32)
        names = [[self.fold.vocab[j][int(code)] for j, code in enumerate(row)]
                 for row in codes]
        numeric = self.numeric(5)
        numeric[1, 0] = np.nan
        numeric[2, 1] = np.inf
        numeric[3, 2] = -np.inf
        encoded, unknown_counts = self.fold.encode_named_categories(names)
        self.assertEqual(encoded.dtype, np.dtype(np.int32))
        np.testing.assert_array_equal(encoded, codes)
        self.assertEqual(unknown_counts, [0] * 15)
        coded = self.fold.score_batch(numeric, codes)
        named = self.fold.score_named_batch(numeric, names)
        for expected, actual in zip(coded, named):
            np.testing.assert_array_equal(actual, expected)

    def test_new_source_label_uses_existing_fold_unknown_not_missing(self):
        names = self.names(3)
        names[:, 0] = ["RSS", "__MISSING__", "JQuants"]
        codes, counts = self.fold.encode_named_categories(names)
        self.assertEqual(codes[:, 0].tolist(), [len(self.fold.vocab[0]), 1, 0])
        self.assertEqual(counts, [1] + [0] * 14)
        pred, _, _ = self.fold.score_named_batch(self.numeric(3), names)
        matrix = self.fold.models[0].predict.call_args.args[0]
        np.testing.assert_array_equal(matrix[:, 296:301], [
            [0, 0, 0, 0, 1],  # Fold's existing unseen bucket.
            [0, 1, 0, 0, 0],  # Original semantic MISSING.
            [1, 0, 0, 0, 0],  # Original source label.
        ])
        self.assertEqual(len(set(pred[:, 0])), 3)
        self.assertEqual(names[:, 0].tolist(), ["RSS", "__MISSING__", "JQuants"])

    def test_semantic_missing_unknown_history_and_null_remain_distinct(self):
        labels = ["__MISSING__", "__UNKNOWN_HISTORY__", "__FORMAL_NULL__",
                  "fold_unseen_0", "new-unobserved-label"]
        names = self.names(len(labels))
        names[:, 0] = labels
        codes, counts = self.fold.encode_named_categories(names)
        np.testing.assert_array_equal(codes[:, 0], [1, 2, 3, 4, 5])
        self.assertEqual(counts, [1] + [0] * 14)
        self.fold.score_named_batch(self.numeric(len(labels)), names)
        matrix = self.fold.models[0].predict.call_args.args[0]
        np.testing.assert_array_equal(matrix[:, 296:301], [
            [0, 1, 0, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 1, 0],
            [0, 0, 0, 0, 1], [0, 0, 0, 0, 1],
        ])

    def test_exact_strings_are_not_normalized_or_substituted(self):
        labels = ["JQuants", "jquants", " JQuants", "JQuants ", "", "RSS", "未知"]
        names = self.names(len(labels))
        names[:, 0] = labels
        names[0, 1] = "fold_unseen_0"  # Known only in another column.
        codes, counts = self.fold.encode_named_categories(names)
        np.testing.assert_array_equal(codes[:, 0], [0] + [5] * 6)
        self.assertEqual(codes[0, 1], len(self.fold.vocab[1]))
        self.assertEqual(counts, [6, 1] + [0] * 13)

    def test_unicode_ndarray_and_python_string_cells_are_accepted(self):
        names = np.full((2, 15), "__UNKNOWN_HISTORY__", dtype="U32")
        codes, counts = self.fold.encode_named_categories(names)
        np.testing.assert_array_equal(codes, np.full((2, 15), 2, dtype=np.int32))
        self.assertEqual(counts, [0] * 15)
        self.fold.score_named_batch(self.numeric(2), names)

    def test_per_column_sentinel_and_unknown_counts_are_deterministic(self):
        names = self.names(4)
        names[0, :] = "RSS"
        names[1, :] = "different-new-label"
        names[2, :] = "RSS"
        first, counts = self.fold.encode_named_categories(names)
        second, second_counts = self.fold.encode_named_categories(names.tolist())
        np.testing.assert_array_equal(first, second)
        for j in range(15):
            np.testing.assert_array_equal(first[:, j], [len(self.fold.vocab[j])] * 3 + [0])
        self.assertEqual(counts, [3] * 15)
        self.assertEqual(second_counts, counts)

    def test_external_integer_path_still_rejects_named_sentinel(self):
        names = self.names()
        names[0, 7] = "RSS"
        codes, _ = self.fold.encode_named_categories(names)
        with self.assertRaisesRegex(ValueError, "P1_CATEGORY_CODE_OUTSIDE_FROZEN_VOCAB"):
            self.fold.score_batch(self.numeric(), codes)
        self.assert_no_prediction()
        self.fold.score_named_batch(self.numeric(), names)
        for bad in (-1, len(self.fold.vocab[7]) + 1):
            codes[0, 7] = bad
            with self.assertRaisesRegex(ValueError, "P1_CATEGORY_CODE_OUTSIDE_FROZEN_VOCAB"):
                self.fold.score_batch(self.numeric(), codes)

    def test_non_string_cells_rejected_without_string_coercion(self):
        class CoercionTrap:
            def __str__(self):
                raise AssertionError("IMPLICIT_STRING_COERCION_FORBIDDEN")

        for value in (None, 0, True, 1.5, float("nan"), b"RSS", {}, [], CoercionTrap()):
            with self.subTest(value_type=type(value).__name__):
                names = self.names()
                names[0, 0] = value
                with self.assertRaisesRegex(ValueError, "P1_NAMED_CATEGORY_CELL_NOT_STRING"):
                    self.fold.score_named_batch(self.numeric(), names)
        self.assert_no_prediction()

    def test_bad_category_shapes_rejected_before_prediction(self):
        bad_inputs = [
            None, "JQuants", ["JQuants"] * 15,
            [["JQuants"] * 14], [["JQuants"] * 16],
            np.full((1, 15, 1), "JQuants"),
            [["JQuants"] * 15, ["JQuants"] * 14],
        ]
        for names in bad_inputs:
            with self.subTest(input_type=type(names).__name__):
                with self.assertRaisesRegex(ValueError, "P1_NAMED_CATEGORY_MATRIX_SHAPE"):
                    self.fold.score_named_batch(self.numeric(), names)
        self.assert_no_prediction()

    def test_bad_numeric_shape_or_row_pairing_rejected_before_prediction(self):
        bad_inputs = [None, [], np.zeros(148), np.zeros((1, 147)), np.zeros((1, 149)),
                      np.zeros((1, 148, 1)), np.zeros((2, 148))]
        for numeric in bad_inputs:
            with self.subTest(shape=getattr(numeric, "shape", None)):
                with self.assertRaisesRegex(ValueError, "P1_FEATURE_MATRIX_SHAPE"):
                    self.fold.score_named_batch(numeric, self.names())
        self.assert_no_prediction()

    def test_vocab_preprocessor_references_and_inputs_unchanged_without_fit(self):
        names = self.names(2)
        names[0, :] = "RSS"
        numeric = self.numeric(2)
        numeric[1, 147] = np.nan
        numeric_before, names_before = numeric.copy(), names.copy()
        vocab_before = copy.deepcopy(self.fold.vocab)
        prep_before = copy.deepcopy(vars(self.fold.prep))
        references_before = [ref.copy() for ref in self.fold.references]
        for _ in range(2):
            self.fold.encode_named_categories(names)
            self.fold.score_named_batch(numeric, names)
        self.assertEqual(self.fold.vocab, vocab_before)
        self.assertEqual(set(vars(self.fold.prep)), set(prep_before))
        np.testing.assert_array_equal(self.fold.prep.median, prep_before["median"])
        self.assertEqual(self.fold.prep.known, prep_before["known"])
        self.assertEqual(self.fold.prep.training_rows, prep_before["training_rows"])
        for actual, expected in zip(self.fold.references, references_before):
            np.testing.assert_array_equal(actual, expected)
        np.testing.assert_array_equal(numeric, numeric_before)
        np.testing.assert_array_equal(names, names_before)


if __name__ == "__main__":
    unittest.main()
