from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from scipy.special import expit


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    ROOT
    / "predict"
    / "research"
    / "phase57_msh_entry_long_v1_proportional_odds.py"
)
SPEC = importlib.util.spec_from_file_location("phase57_proportional_odds", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
po = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = po
SPEC.loader.exec_module(po)


def make_synthetic(n_rows: int = 600) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(570157)
    X = rng.normal(size=(n_rows, 2))
    latent = 1.25 * X[:, 0] - 0.85 * X[:, 1] + rng.logistic(
        loc=0.0,
        scale=0.75,
        size=n_rows,
    )
    y = np.digitize(latent, [-1.15, -0.25, 0.60, 1.45]).astype(np.int64)
    if tuple(np.unique(y)) != (0, 1, 2, 3, 4):
        raise AssertionError("synthetic fixture did not contain all five classes")
    return X, y


def independent_objective(
    model: po.ProportionalOddsOrdinalLogit,
    X: np.ndarray,
    y: np.ndarray,
) -> tuple[float, float, float]:
    standardized = (X - model.scaler_mean_) / model.scaler_std_
    eta = standardized @ model.beta_
    cumulative = expit(model.cutpoints_[None, :] - eta[:, None])
    probability = np.column_stack(
        [
            cumulative[:, 0],
            cumulative[:, 1] - cumulative[:, 0],
            cumulative[:, 2] - cumulative[:, 1],
            cumulative[:, 3] - cumulative[:, 2],
            1.0 - cumulative[:, 3],
        ]
    )
    observed = probability[np.arange(y.size), y]
    if np.any(observed <= 0):
        raise AssertionError("independent reference probability underflowed")
    nll = -float(np.sum(np.log(observed)))
    penalty = 0.5 * model.l2_lambda * float(model.beta_ @ model.beta_)
    return nll, penalty, nll + penalty


class ProportionalOddsSyntheticAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.X, cls.y = make_synthetic()
        cls.feature_order = ("frozenSelectorRidgeScore", "frozenSelectorRidgeRank")
        cls.model = po.ProportionalOddsOrdinalLogit(l2_lambda=1.0).fit(
            cls.X,
            cls.y,
            feature_order=cls.feature_order,
        )
        cls.unregularized = po.ProportionalOddsOrdinalLogit(l2_lambda=0.0).fit(
            cls.X,
            cls.y,
            feature_order=cls.feature_order,
        )
        cls.repeat = po.ProportionalOddsOrdinalLogit(l2_lambda=1.0).fit(
            cls.X,
            cls.y,
            feature_order=cls.feature_order,
        )

    def test_01_five_class_fit_succeeds(self) -> None:
        self.assertTrue(self.model.last_fit_diagnostics["success"])
        self.assertEqual(self.model.to_artifact()["classes"], [0, 1, 2, 3, 4])

    def test_02_four_cutpoints_are_strictly_ordered(self) -> None:
        self.assertEqual(self.model.cutpoints_.shape, (4,))
        self.assertTrue(np.all(np.diff(self.model.cutpoints_) > 0))

    def test_03_parameters_are_finite(self) -> None:
        self.assertTrue(np.isfinite(self.model.beta_).all())
        self.assertTrue(np.isfinite(self.model.cutpoints_).all())

    def test_04_probabilities_are_finite(self) -> None:
        self.assertTrue(np.isfinite(self.model.predict_proba(self.X)).all())

    def test_05_probabilities_are_nonnegative(self) -> None:
        self.assertTrue(np.all(self.model.predict_proba(self.X) >= 0))

    def test_06_probability_rows_sum_to_one(self) -> None:
        row_sums = np.sum(self.model.predict_proba(self.X), axis=1)
        np.testing.assert_allclose(row_sums, 1.0, rtol=0.0, atol=1e-12)

    def test_07_expected_level_moves_monotonically_with_latent_direction(self) -> None:
        direction = np.array([1.25, -0.85], dtype=np.float64)
        direction /= np.linalg.norm(direction)
        grid = np.linspace(-3.0, 3.0, 101)[:, None] * direction[None, :]
        score = self.model.decision_score(grid)
        self.assertTrue(np.all(np.diff(score) > 0))
        self.assertGreaterEqual(float(score.min()), 0.0)
        self.assertLessEqual(float(score.max()), 4.0)

    def test_08_fixed_slope_only_l2_shrinks_beta_norm(self) -> None:
        self.assertLess(
            float(np.linalg.norm(self.model.beta_)),
            float(np.linalg.norm(self.unregularized.beta_)),
        )

    def test_09_cutpoints_do_not_enter_penalty(self) -> None:
        standardized = (self.X - self.model.scaler_mean_) / self.model.scaler_std_
        labels = self.y
        beta = np.array([0.35, -0.22], dtype=np.float64)
        raw_a = np.array([-0.9, 0.1, 0.4, 0.8], dtype=np.float64)
        raw_b = np.array([1.7, -0.8, 1.1, -0.3], dtype=np.float64)
        expected_penalty = 0.5 * float(beta @ beta)
        for raw in (raw_a, raw_b):
            parameters = np.concatenate((beta, raw))
            objective_zero, _ = po._objective_and_gradient(
                parameters, standardized, labels, 0.0, 1e-8
            )
            objective_one, _ = po._objective_and_gradient(
                parameters, standardized, labels, 1.0, 1e-8
            )
            self.assertAlmostEqual(
                objective_one - objective_zero,
                expected_penalty,
                delta=1e-10,
            )

    def test_10_analytic_gradient_matches_central_finite_difference(self) -> None:
        X = np.array(
            [
                [-1.3, 0.2],
                [-0.9, -0.4],
                [-0.2, 1.1],
                [0.1, -1.0],
                [0.8, 0.3],
                [1.4, -0.7],
                [-0.6, 0.8],
                [0.5, -0.2],
                [1.1, 0.9],
                [-1.1, -0.9],
            ],
            dtype=np.float64,
        )
        y = np.array([0, 0, 1, 1, 2, 2, 3, 3, 4, 4], dtype=np.int64)
        parameters = np.array([0.3, -0.2, -1.0, 0.1, 0.3, 0.7], dtype=np.float64)
        _, analytic = po._objective_and_gradient(parameters, X, y, 1.0, 1e-8)
        step = 1e-6
        numeric = np.empty_like(parameters)
        for index in range(parameters.size):
            upper = parameters.copy()
            lower = parameters.copy()
            upper[index] += step
            lower[index] -= step
            upper_value, _ = po._objective_and_gradient(upper, X, y, 1.0, 1e-8)
            lower_value, _ = po._objective_and_gradient(lower, X, y, 1.0, 1e-8)
            numeric[index] = (upper_value - lower_value) / (2.0 * step)
        absolute_error = float(np.max(np.abs(analytic - numeric)))
        relative_error = float(
            np.max(np.abs(analytic - numeric) / np.maximum(1.0, np.abs(numeric)))
        )
        self.assertLessEqual(absolute_error, 2e-5)
        self.assertLessEqual(relative_error, 2e-5)

    def test_11_repeated_fit_is_deterministic(self) -> None:
        np.testing.assert_allclose(self.model.beta_, self.repeat.beta_, rtol=0, atol=1e-12)
        np.testing.assert_allclose(
            self.model.cutpoints_, self.repeat.cutpoints_, rtol=0, atol=1e-12
        )
        self.assertAlmostEqual(
            self.model.last_fit_diagnostics["objective"],
            self.repeat.last_fit_diagnostics["objective"],
            delta=1e-12,
        )
        np.testing.assert_allclose(
            self.model.predict_proba(self.X),
            self.repeat.predict_proba(self.X),
            rtol=0,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            self.model.decision_score(self.X),
            self.repeat.decision_score(self.X),
            rtol=0,
            atol=1e-12,
        )
        self.assertEqual(
            self.model.last_fit_diagnostics["status"],
            self.repeat.last_fit_diagnostics["status"],
        )

    def test_12_serialization_reload_preserves_prediction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "synthetic-model.json"
            self.model.save_json(artifact_path)
            reloaded = po.ProportionalOddsOrdinalLogit.load_json(artifact_path)
            np.testing.assert_array_equal(
                self.model.predict_proba(self.X), reloaded.predict_proba(self.X)
            )
            np.testing.assert_array_equal(
                self.model.decision_score(self.X), reloaded.decision_score(self.X)
            )

    def test_13_class_semantics_are_exactly_zero_through_four(self) -> None:
        artifact = self.model.to_artifact()
        self.assertEqual(artifact["classes"], [0, 1, 2, 3, 4])
        self.assertEqual(artifact["link"], "LOGIT")
        self.assertEqual(
            artifact["parameterization"]["equation"],
            "logit(P(Y<=k|x))=theta[k]-x@beta",
        )

    def test_14_convergence_failure_is_fail_closed(self) -> None:
        failed = po.ProportionalOddsOrdinalLogit(
            l2_lambda=1.0,
            solver=po.SolverContract(maxiter=0),
        )
        with self.assertRaises(po.FitFailedError) as context:
            failed.fit(self.X, self.y, feature_order=self.feature_order)
        self.assertFalse(context.exception.diagnostics["success"])
        with self.assertRaises(RuntimeError):
            failed.to_artifact()

    def test_15_nan_and_inf_inputs_are_rejected(self) -> None:
        for invalid_value in (np.nan, np.inf, -np.inf):
            invalid = self.X.copy()
            invalid[0, 0] = invalid_value
            with self.assertRaises(ValueError):
                po.ProportionalOddsOrdinalLogit().fit(
                    invalid,
                    self.y,
                    feature_order=self.feature_order,
                )
            with self.assertRaises(ValueError):
                self.model.predict_proba(invalid)

    def test_16_missing_class_is_rejected_without_remapping(self) -> None:
        mask = self.y != 3
        with self.assertRaisesRegex(ValueError, "all ordered classes"):
            po.ProportionalOddsOrdinalLogit().fit(
                self.X[mask],
                self.y[mask],
                feature_order=self.feature_order,
            )

    def test_17_independent_objective_recalculation_matches_solver(self) -> None:
        nll, penalty, total = independent_objective(self.model, self.X, self.y)
        self.assertGreater(nll, 0)
        self.assertGreater(penalty, 0)
        self.assertAlmostEqual(
            total,
            self.model.last_fit_diagnostics["objective"],
            delta=1e-8,
        )

    def test_18_artifact_is_fail_closed_and_has_no_unsafe_switch(self) -> None:
        artifact = self.model.to_artifact()
        self.assertEqual(
            artifact["regularization"]["objective"],
            "SUM_NLL+lambda/2*||beta||^2",
        )
        self.assertFalse(artifact["regularization"]["cutpointsPenalized"])
        self.assertEqual(artifact["scaler"]["fitScope"], "TRAINING_PREFIX_ONLY")
        self.assertEqual(artifact["scaler"]["zeroStdPolicy"], "FIT_FAILED")
        self.assertTrue(artifact["solver"]["success"])
        self.assertTrue(all(value is False for value in artifact["safety"].values()))
        payload = json.dumps(artifact).lower()
        self.assertNotIn("short model", payload)
        self.assertNotIn("fallback", payload)
        unsafe = json.loads(json.dumps(artifact))
        unsafe["safety"]["executionAllowed"] = True
        with self.assertRaisesRegex(ValueError, "safety"):
            po.ProportionalOddsOrdinalLogit.from_artifact(unsafe)


if __name__ == "__main__":
    unittest.main()
