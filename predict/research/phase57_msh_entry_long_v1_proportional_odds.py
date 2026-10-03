"""Minimal proportional-odds reference model for MSH-Entry LONG v1.

This module implements exactly one five-class cumulative-logit model:

    logit(P(Y <= k | x)) = theta[k] - x @ beta,  k = 0, 1, 2, 3

The optimized objective is SUM negative log likelihood plus
``l2_lambda / 2 * ||beta||^2``.  Cutpoints are never penalized.  It is a
research-only reference implementation; it contains no trading, threshold
selection, feature engineering, imputation, class weighting, or fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


MODEL_VERSION = "phase57-msh-entry-long-v1-proportional-odds-v1"
MODEL_FAMILY = "PROPORTIONAL_ODDS_ORDINAL_LOGISTIC_REGRESSION"
ORDERED_CLASSES = (0, 1, 2, 3, 4)
DEFAULT_L2_LAMBDA = 1.0
DEFAULT_MAXITER = 2_000
DEFAULT_FTOL = 1e-12
DEFAULT_GTOL = 1e-8
DEFAULT_CUTPOINT_EPSILON = 1e-8
PROBABILITY_TOLERANCE = 1e-12


class FitFailedError(RuntimeError):
    """Raised when a fit cannot produce a valid fail-closed artifact."""

    def __init__(self, message: str, diagnostics: dict[str, Any]):
        super().__init__(message)
        self.diagnostics = diagnostics


@dataclass(frozen=True)
class SolverContract:
    method: str = "L-BFGS-B"
    maxiter: int = DEFAULT_MAXITER
    ftol: float = DEFAULT_FTOL
    gtol: float = DEFAULT_GTOL

    def validate(self) -> None:
        if self.method != "L-BFGS-B":
            raise ValueError("only L-BFGS-B is allowed")
        if not isinstance(self.maxiter, int) or self.maxiter < 0:
            raise ValueError("maxiter must be an integer >= 0")
        if not np.isfinite(self.ftol) or self.ftol <= 0:
            raise ValueError("ftol must be finite and > 0")
        if not np.isfinite(self.gtol) or self.gtol <= 0:
            raise ValueError("gtol must be finite and > 0")


def _require_finite_matrix(X: Any, expected_features: int | None = None) -> np.ndarray:
    matrix = np.asarray(X, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError("X must be a non-empty two-dimensional matrix")
    if expected_features is not None and matrix.shape[1] != expected_features:
        raise ValueError(
            f"X has {matrix.shape[1]} features; expected {expected_features}"
        )
    if not np.isfinite(matrix).all():
        raise ValueError("X contains NaN or Inf")
    return matrix


def _require_five_classes(y: Any, n_rows: int) -> np.ndarray:
    labels = np.asarray(y)
    if labels.ndim != 1 or labels.shape[0] != n_rows:
        raise ValueError("y must be one-dimensional and aligned with X")
    if not np.issubdtype(labels.dtype, np.number):
        raise ValueError("y must contain numeric class labels 0 through 4")
    numeric = labels.astype(np.float64)
    if not np.isfinite(numeric).all() or not np.equal(numeric, np.floor(numeric)).all():
        raise ValueError("y must contain finite integer class labels")
    integer = numeric.astype(np.int64)
    observed = tuple(int(value) for value in np.unique(integer))
    if observed != ORDERED_CLASSES:
        raise ValueError(
            f"all ordered classes {ORDERED_CLASSES} are required; observed {observed}"
        )
    return integer


def _softplus(value: np.ndarray) -> np.ndarray:
    return np.logaddexp(0.0, value)


def _inverse_softplus(value: np.ndarray) -> np.ndarray:
    if np.any(value <= 0) or not np.isfinite(value).all():
        raise ValueError("inverse softplus requires finite positive values")
    # value + log(1-exp(-value)) remains stable for both small and large value.
    return value + np.log(-np.expm1(-value))


def _log_sigmoid(value: np.ndarray) -> np.ndarray:
    return -np.logaddexp(0.0, -value)


def _log_one_minus_exp(negative_value: np.ndarray) -> np.ndarray:
    """Stable log(1-exp(x)) for finite x < 0."""
    value = np.asarray(negative_value, dtype=np.float64)
    if np.any(value >= 0) or not np.isfinite(value).all():
        raise FloatingPointError("log1mexp requires finite values below zero")
    split = -np.log(2.0)
    return np.where(
        value < split,
        np.log1p(-np.exp(value)),
        np.log(-np.expm1(value)),
    )


def _unpack_cutpoints(
    raw_cutpoints: np.ndarray,
    epsilon: float,
) -> tuple[np.ndarray, np.ndarray]:
    raw = np.asarray(raw_cutpoints, dtype=np.float64)
    if raw.shape != (4,) or not np.isfinite(raw).all():
        raise ValueError("raw cutpoint parameters must be four finite values")
    increments = _softplus(raw[1:]) + epsilon
    theta = np.empty(4, dtype=np.float64)
    theta[0] = raw[0]
    theta[1:] = raw[0] + np.cumsum(increments)
    derivatives = expit(raw[1:])
    if not np.isfinite(theta).all() or not np.all(np.diff(theta) > 0):
        raise FloatingPointError("cutpoint transformation failed strict ordering")
    return theta, derivatives


def _initial_raw_cutpoints(labels: np.ndarray, epsilon: float) -> np.ndarray:
    counts = np.bincount(labels, minlength=5).astype(np.float64)
    cumulative = np.cumsum(counts)[:-1] / labels.size
    if np.any(cumulative <= 0) or np.any(cumulative >= 1):
        raise ValueError("class-frequency cutpoint initialization is not finite")
    theta = np.log(cumulative) - np.log1p(-cumulative)
    gaps_without_epsilon = np.diff(theta) - epsilon
    if np.any(gaps_without_epsilon <= 0):
        raise ValueError("class-frequency cutpoints are too close for the contract epsilon")
    return np.concatenate((theta[:1], _inverse_softplus(gaps_without_epsilon)))


def _log_class_probabilities(z: np.ndarray, labels: np.ndarray) -> np.ndarray:
    log_probability = np.empty(labels.shape[0], dtype=np.float64)
    mask_zero = labels == 0
    mask_four = labels == 4
    log_probability[mask_zero] = _log_sigmoid(z[mask_zero, 0])
    log_probability[mask_four] = _log_sigmoid(-z[mask_four, 3])
    for klass in (1, 2, 3):
        mask = labels == klass
        lower = z[mask, klass - 1]
        upper = z[mask, klass]
        log_probability[mask] = (
            _log_sigmoid(upper)
            + _log_sigmoid(-lower)
            + _log_one_minus_exp(lower - upper)
        )
    if not np.isfinite(log_probability).all():
        raise FloatingPointError("non-finite class log probability")
    return log_probability


def _objective_and_gradient(
    parameters: np.ndarray,
    X_standardized: np.ndarray,
    labels: np.ndarray,
    l2_lambda: float,
    cutpoint_epsilon: float,
) -> tuple[float, np.ndarray]:
    n_features = X_standardized.shape[1]
    beta = parameters[:n_features]
    raw_cutpoints = parameters[n_features:]
    theta, increment_derivatives = _unpack_cutpoints(
        raw_cutpoints,
        cutpoint_epsilon,
    )
    eta = X_standardized @ beta
    z = theta[None, :] - eta[:, None]
    log_probability = _log_class_probabilities(z, labels)

    nll = -float(np.sum(log_probability))
    penalty = 0.5 * l2_lambda * float(beta @ beta)
    objective = nll + penalty

    log_pdf = _log_sigmoid(z) + _log_sigmoid(-z)
    gradient_eta = np.zeros(labels.shape[0], dtype=np.float64)
    gradient_theta = np.zeros(4, dtype=np.float64)

    mask_zero = labels == 0
    ratio_upper = np.exp(log_pdf[mask_zero, 0] - log_probability[mask_zero])
    gradient_eta[mask_zero] = ratio_upper
    gradient_theta[0] -= float(np.sum(ratio_upper))

    mask_four = labels == 4
    ratio_lower = np.exp(log_pdf[mask_four, 3] - log_probability[mask_four])
    gradient_eta[mask_four] = -ratio_lower
    gradient_theta[3] += float(np.sum(ratio_lower))

    for klass in (1, 2, 3):
        mask = labels == klass
        log_p = log_probability[mask]
        lower_ratio = np.exp(log_pdf[mask, klass - 1] - log_p)
        upper_ratio = np.exp(log_pdf[mask, klass] - log_p)
        gradient_eta[mask] = upper_ratio - lower_ratio
        gradient_theta[klass - 1] += float(np.sum(lower_ratio))
        gradient_theta[klass] -= float(np.sum(upper_ratio))

    gradient_beta = X_standardized.T @ gradient_eta + l2_lambda * beta
    gradient_raw = np.empty(4, dtype=np.float64)
    gradient_raw[0] = float(np.sum(gradient_theta))
    for index in range(1, 4):
        gradient_raw[index] = (
            increment_derivatives[index - 1]
            * float(np.sum(gradient_theta[index:]))
        )
    gradient = np.concatenate((gradient_beta, gradient_raw))
    if not np.isfinite(objective) or not np.isfinite(gradient).all():
        raise FloatingPointError("objective or gradient became NaN/Inf")
    return objective, gradient


class ProportionalOddsOrdinalLogit:
    """One deterministic five-class proportional-odds logit model."""

    def __init__(
        self,
        *,
        l2_lambda: float = DEFAULT_L2_LAMBDA,
        solver: SolverContract | None = None,
        cutpoint_epsilon: float = DEFAULT_CUTPOINT_EPSILON,
    ) -> None:
        if not np.isfinite(l2_lambda) or l2_lambda < 0:
            raise ValueError("l2_lambda must be finite and >= 0")
        if not np.isfinite(cutpoint_epsilon) or cutpoint_epsilon <= 0:
            raise ValueError("cutpoint_epsilon must be finite and > 0")
        self.l2_lambda = float(l2_lambda)
        self.solver = solver or SolverContract()
        self.solver.validate()
        self.cutpoint_epsilon = float(cutpoint_epsilon)
        self.last_fit_diagnostics: dict[str, Any] | None = None
        self._is_fitted = False

    def fit(
        self,
        X: Any,
        y: Any,
        *,
        feature_order: Sequence[str],
    ) -> "ProportionalOddsOrdinalLogit":
        matrix = _require_finite_matrix(X)
        labels = _require_five_classes(y, matrix.shape[0])
        names = tuple(str(name) for name in feature_order)
        if len(names) != matrix.shape[1] or len(set(names)) != len(names):
            raise ValueError("feature_order must contain one unique name per X column")
        if any(not name for name in names):
            raise ValueError("feature_order cannot contain blank names")

        mean = np.mean(matrix, axis=0, dtype=np.float64)
        std = np.std(matrix, axis=0, ddof=0, dtype=np.float64)
        if not np.isfinite(mean).all() or not np.isfinite(std).all():
            raise ValueError("training-prefix scaler is non-finite")
        if np.any(std <= 0):
            raise ValueError("zero-variance feature is prohibited")
        standardized = (matrix - mean) / std

        initial = np.concatenate(
            (
                np.zeros(matrix.shape[1], dtype=np.float64),
                _initial_raw_cutpoints(labels, self.cutpoint_epsilon),
            )
        )

        def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
            return _objective_and_gradient(
                parameters,
                standardized,
                labels,
                self.l2_lambda,
                self.cutpoint_epsilon,
            )

        result = minimize(
            objective,
            initial,
            method=self.solver.method,
            jac=True,
            options={
                "maxiter": self.solver.maxiter,
                "ftol": self.solver.ftol,
                "gtol": self.solver.gtol,
            },
        )
        diagnostics = {
            "method": self.solver.method,
            "maxiter": self.solver.maxiter,
            "ftol": self.solver.ftol,
            "gtol": self.solver.gtol,
            "success": bool(result.success),
            "status": int(result.status),
            "message": str(result.message),
            "nit": int(result.nit),
            "nfev": int(result.nfev),
            "njev": int(result.njev) if result.njev is not None else None,
            "objective": float(result.fun),
        }
        self.last_fit_diagnostics = diagnostics
        if not result.success:
            raise FitFailedError("optimizer did not converge", diagnostics)
        if not np.isfinite(result.x).all() or not np.isfinite(result.fun):
            raise FitFailedError("optimizer returned non-finite output", diagnostics)

        beta = np.asarray(result.x[: matrix.shape[1]], dtype=np.float64)
        cutpoints, _ = _unpack_cutpoints(
            np.asarray(result.x[matrix.shape[1] :], dtype=np.float64),
            self.cutpoint_epsilon,
        )
        if not np.all(np.diff(cutpoints) > 0):
            raise FitFailedError("cutpoints are not strictly ordered", diagnostics)

        self.beta_ = beta
        self.cutpoints_ = cutpoints
        self.scaler_mean_ = mean
        self.scaler_std_ = std
        self.feature_order_ = names
        self._is_fitted = True
        try:
            probabilities = self.predict_proba(matrix)
        except (ValueError, FloatingPointError) as error:
            self._is_fitted = False
            raise FitFailedError(
                f"post-fit probability validation failed: {error}", diagnostics
            ) from error
        if probabilities.shape != (matrix.shape[0], 5):
            self._is_fitted = False
            raise FitFailedError("post-fit probability shape is invalid", diagnostics)
        return self

    def _require_fitted(self) -> None:
        if not self._is_fitted:
            raise RuntimeError("model is not fitted")

    def predict_proba(self, X: Any) -> np.ndarray:
        self._require_fitted()
        matrix = _require_finite_matrix(X, len(self.feature_order_))
        standardized = (matrix - self.scaler_mean_) / self.scaler_std_
        eta = standardized @ self.beta_
        cumulative = expit(self.cutpoints_[None, :] - eta[:, None])
        probabilities = np.column_stack(
            (
                cumulative[:, 0],
                cumulative[:, 1] - cumulative[:, 0],
                cumulative[:, 2] - cumulative[:, 1],
                cumulative[:, 3] - cumulative[:, 2],
                1.0 - cumulative[:, 3],
            )
        )
        if not np.isfinite(probabilities).all():
            raise FloatingPointError("predicted probabilities contain NaN/Inf")
        if np.any(probabilities < 0):
            raise FloatingPointError("predicted probabilities became negative")
        row_sum_error = np.max(np.abs(np.sum(probabilities, axis=1) - 1.0))
        if row_sum_error > PROBABILITY_TOLERANCE:
            raise FloatingPointError(
                f"probability row sum error {row_sum_error} exceeds tolerance"
            )
        return probabilities

    def decision_score(self, X: Any) -> np.ndarray:
        probabilities = self.predict_proba(X)
        score = probabilities @ np.arange(5, dtype=np.float64)
        if np.any(score < -PROBABILITY_TOLERANCE) or np.any(
            score > 4.0 + PROBABILITY_TOLERANCE
        ):
            raise FloatingPointError("expected ordinal level is outside [0,4]")
        return score

    def to_artifact(self) -> dict[str, Any]:
        self._require_fitted()
        return {
            "schemaVersion": 1,
            "modelVersion": MODEL_VERSION,
            "modelFamily": MODEL_FAMILY,
            "link": "LOGIT",
            "classes": list(ORDERED_CLASSES),
            "parameterization": {
                "equation": "logit(P(Y<=k|x))=theta[k]-x@beta",
                "cutpointOrdering": "theta0=a0; theta[k]=theta[k-1]+softplus(delta[k])+epsilon",
                "cutpointEpsilon": self.cutpoint_epsilon,
            },
            "beta": self.beta_.tolist(),
            "cutpoints": self.cutpoints_.tolist(),
            "featureOrder": list(self.feature_order_),
            "scaler": {
                "fitScope": "TRAINING_PREFIX_ONLY",
                "ddof": 0,
                "mean": self.scaler_mean_.tolist(),
                "std": self.scaler_std_.tolist(),
                "zeroStdPolicy": "FIT_FAILED",
            },
            "regularization": {
                "type": "L2_SLOPES_ONLY",
                "lambda": self.l2_lambda,
                "objective": "SUM_NLL+lambda/2*||beta||^2",
                "cutpointsPenalized": False,
            },
            "solver": dict(self.last_fit_diagnostics or {}),
            "decisionScore": {
                "formula": "E[L]=0*P0+1*P1+2*P2+3*P3+4*P4",
                "range": [0.0, 4.0],
            },
            "safety": {
                "executionAllowed": False,
                "brokerWriteAllowed": False,
                "excelOrderWriteAllowed": False,
                "rssOrderFunctionAllowed": False,
                "liveTradingAllowed": False,
                "paperTradingAllowed": False,
                "automaticPromotionAllowed": False,
                "productionUpdateAllowed": False,
                "transmitted": False,
                "shortAllowed": False,
                "marginAllowed": False,
                "leverageAllowed": False,
            },
        }

    @classmethod
    def from_artifact(cls, artifact: dict[str, Any]) -> "ProportionalOddsOrdinalLogit":
        if artifact.get("schemaVersion") != 1:
            raise ValueError("unsupported artifact schema")
        if artifact.get("modelVersion") != MODEL_VERSION:
            raise ValueError("unexpected model version")
        if artifact.get("modelFamily") != MODEL_FAMILY:
            raise ValueError("unexpected model family")
        if artifact.get("link") != "LOGIT":
            raise ValueError("artifact link semantics changed")
        if tuple(artifact.get("classes", ())) != ORDERED_CLASSES:
            raise ValueError("artifact class semantics are not 0 through 4")
        regularization = artifact.get("regularization", {})
        if regularization.get("type") != "L2_SLOPES_ONLY" or regularization.get(
            "cutpointsPenalized"
        ) is not False:
            raise ValueError("artifact regularization semantics changed")
        if regularization.get("objective") != "SUM_NLL+lambda/2*||beta||^2":
            raise ValueError("artifact objective semantics changed")
        parameterization = artifact.get("parameterization", {})
        if (
            parameterization.get("equation")
            != "logit(P(Y<=k|x))=theta[k]-x@beta"
        ):
            raise ValueError("artifact model equation changed")
        scaler = artifact.get("scaler", {})
        if (
            scaler.get("fitScope") != "TRAINING_PREFIX_ONLY"
            or scaler.get("ddof") != 0
            or scaler.get("zeroStdPolicy") != "FIT_FAILED"
        ):
            raise ValueError("artifact scaler contract changed")
        decision_score = artifact.get("decisionScore", {})
        if (
            decision_score.get("formula")
            != "E[L]=0*P0+1*P1+2*P2+3*P3+4*P4"
            or decision_score.get("range") != [0.0, 4.0]
        ):
            raise ValueError("artifact decision-score contract changed")
        safety = artifact.get("safety", {})
        if not safety or any(value is not False for value in safety.values()):
            raise ValueError("artifact safety contract is not fail-closed")
        model = cls(
            l2_lambda=float(regularization["lambda"]),
            solver=SolverContract(
                method=str(artifact["solver"]["method"]),
                maxiter=int(artifact["solver"]["maxiter"]),
                ftol=float(artifact["solver"]["ftol"]),
                gtol=float(artifact["solver"]["gtol"]),
            ),
            cutpoint_epsilon=float(parameterization["cutpointEpsilon"]),
        )
        beta = np.asarray(artifact["beta"], dtype=np.float64)
        cutpoints = np.asarray(artifact["cutpoints"], dtype=np.float64)
        mean = np.asarray(scaler["mean"], dtype=np.float64)
        std = np.asarray(scaler["std"], dtype=np.float64)
        names = tuple(str(name) for name in artifact["featureOrder"])
        if beta.ndim != 1 or beta.size == 0:
            raise ValueError("artifact beta is invalid")
        if cutpoints.shape != (4,) or not np.all(np.diff(cutpoints) > 0):
            raise ValueError("artifact cutpoints are invalid")
        if mean.shape != beta.shape or std.shape != beta.shape or np.any(std <= 0):
            raise ValueError("artifact scaler is invalid")
        if len(names) != beta.size or len(set(names)) != len(names):
            raise ValueError("artifact feature order is invalid")
        if not np.isfinite(np.concatenate((beta, cutpoints, mean, std))).all():
            raise ValueError("artifact parameters contain NaN/Inf")
        solver_diagnostics = dict(artifact["solver"])
        if solver_diagnostics.get("success") is not True:
            raise ValueError("artifact does not contain a successful fit")
        if not np.isfinite(float(solver_diagnostics.get("objective", np.nan))):
            raise ValueError("artifact objective is not finite")
        model.beta_ = beta
        model.cutpoints_ = cutpoints
        model.scaler_mean_ = mean
        model.scaler_std_ = std
        model.feature_order_ = names
        model.last_fit_diagnostics = solver_diagnostics
        model._is_fitted = True
        return model

    def save_json(self, path: str | Path) -> None:
        payload = json.dumps(
            self.to_artifact(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        Path(path).write_text(payload + "\n", encoding="utf-8")

    @classmethod
    def load_json(cls, path: str | Path) -> "ProportionalOddsOrdinalLogit":
        artifact = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_artifact(artifact)


__all__ = [
    "DEFAULT_CUTPOINT_EPSILON",
    "DEFAULT_FTOL",
    "DEFAULT_GTOL",
    "DEFAULT_L2_LAMBDA",
    "DEFAULT_MAXITER",
    "FitFailedError",
    "MODEL_FAMILY",
    "MODEL_VERSION",
    "ORDERED_CLASSES",
    "PROBABILITY_TOLERANCE",
    "ProportionalOddsOrdinalLogit",
    "SolverContract",
]
