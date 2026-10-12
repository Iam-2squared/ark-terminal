"""Independent multi-head Selector candidate. Fit is explicit, never automatic.

No network clients, provider access, broker functions, order generation, trading,
or implicit loading of existing Ark models. sklearn/numpy loaded only at fit time.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from selector_core import ContractError, _event_key, select_top5

UP_THRESHOLDS = (1, 2, 3, 4, 5)
RISK_THRESHOLDS = (1, 2, 3, 5)
HEADS = (
    "up1", "up2", "up3", "up4", "up5",
    "signed_high_negative", "mae1", "mae2", "mae3", "mae5",
)
# Candidate formula fixed as a testable hypothesis, NOT known-optimal weights.
DOWNSIDE_PENALTY_MULTIPLIER = 2.0
MODEL_CONFIG = {
    "family": "HistGradientBoostingClassifier",
    "learning_rate": 0.05,
    "max_leaf_nodes": 15,
    "min_samples_leaf": 40,
    "max_iter": 120,
    "l2_regularization": 10.0,
    "early_stopping": False,
    "random_state": 20261012,
}


def split_sessions(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    """60% FIT, 20% SELECT, remaining REPORT: contiguous session groups.

    These are DEVELOPMENT sub-blocks, not OOS. No row from a session crosses
    partitions. No future outcome is examined to establish this split.
    """
    sessions = sorted({r["session"] for r in rows})
    if len(sessions) < 15:
        raise ContractError("INSUFFICIENT_DEVELOPMENT_SESSIONS")
    if any(not isinstance(d, str) or len(d) != 10 for d in sessions):
        raise ContractError("INVALID_SESSION_DATE")
    a = (len(sessions) * 60) // 100
    b = (len(sessions) * 80) // 100
    return {"fit": sessions[:a], "select": sessions[a:b], "report": sessions[b:]}


def authorize_research(authorization: dict[str, Any]) -> None:
    """Explicit local human/data gate; never treats mere file presence as a grant."""
    mode = authorization.get("mode")
    if mode == "SYNTHETIC":
        return
    if mode != "DEVELOPMENT_AUTHORIZED":
        raise ContractError("DATA_USE_NOT_AUTHORIZED")
    required = (
        "entitlementCurrent", "rawDerivativeUseAllowed",
        "partitionManifestVerified", "nonGitPrivateCacheConfirmed",
        "historicalOutcomeExposureAcknowledged",
    )
    if not all(authorization.get(k) is True for k in required):
        raise ContractError("ENTITLEMENT_OR_PARTITION_GATE_BLOCKED")
    if not authorization.get("partitionManifestSha256"):
        raise ContractError("PARTITION_MANIFEST_REQUIRED")
    if not authorization.get("exposureLedgerId"):
        raise ContractError("EXPOSURE_LEDGER_REQUIRED")


def _head_targets(signed_high: float, mae: float) -> dict[str, int]:
    if not math.isfinite(signed_high) or not math.isfinite(mae) or mae > 0:
        raise ContractError("INVALID_TEACHER_VALUES")
    out = {f"up{t}": int(signed_high >= t) for t in UP_THRESHOLDS}
    out["signed_high_negative"] = int(signed_high < 0)
    out.update({f"mae{t}": int(mae <= -t) for t in RISK_THRESHOLDS})
    return out


def _matrix(rows: list[dict[str, Any]], columns: list[str]):
    import numpy as np
    return np.asarray(
        [[(float(r["features"][k]) if r["features"].get(k) is not None
           else math.nan) for k in columns] for r in rows],
        dtype=float,
    )


@dataclass
class TrainedSelector:
    models: dict[str, Any]
    feature_names: tuple[str, ...]
    fit_sessions: tuple[str, ...]
    feature_schema_sha256: str
    fit_population_n: int
    missing_teacher_n: int

    def score_rows(self, feature_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Outputs only predecision score and head estimates, never labels."""
        if not feature_rows:
            return []
        for row in feature_rows:
            if any(k.startswith(("future", "label", "outcome")) for k in row):
                raise ContractError("FUTURE_IN_MODEL_SCORING")
            if row["session"] in self.fit_sessions:
                # In-fit output is permitted for engineering only, but not test claims.
                pass
            if row.get("assetType") != "JPX_CASH_EQUITY":
                raise ContractError("NONCASH_SYMBOL")
        X = _matrix(feature_rows, list(self.feature_names))
        probs = {}
        for head, clf in self.models.items():
            indices = list(clf.classes_)
            if 1 not in indices:
                raise ContractError("DEGENERATE_FITTED_HEAD")
            probs[head] = clf.predict_proba(X)[:, indices.index(1)]
        scored = []
        for i, r in enumerate(feature_rows):
            # Cumulative up odds approximate a threshold-integral of upside.
            upside = sum(0.01 * t * float(probs[f"up{t}"][i])
                         for t in UP_THRESHOLDS)
            downside = (
                0.02 * float(probs["signed_high_negative"][i])
                + sum(0.01 * t * float(probs[f"mae{t}"][i])
                      for t in RISK_THRESHOLDS)
            )
            score = 100.0 * (upside - DOWNSIDE_PENALTY_MULTIPLIER * downside)
            out = {k: r[k] for k in (
                "session", "decisionTime", "symbol", "assetType",
                "decisionPrice", "eligibleUniverseHash", "priceBasis"
            )}
            out["score"] = score
            out["researchOnlyUncalibratedHeadEstimates"] = {
                k: float(probs[k][i]) for k in HEADS
            }
            scored.append(out)
        return scored

    def rank_groups(self, feature_rows: list[dict[str, Any]]
                    ) -> list[dict[str, Any]]:
        scored = self.score_rows(feature_rows)
        groups = defaultdict(list)
        for r in scored:
            groups[(r["session"], r["decisionTime"])].append(r)
        chosen = []
        for group in sorted(groups):
            chosen.extend(select_top5(groups[group]))
        return chosen


def fit_candidate(feature_rows: list[dict[str, Any]],
                  evaluator_labels: dict[tuple[str, str, str], dict[str, float]],
                  authorization: dict[str, Any]) -> tuple[TrainedSelector, dict[str, list[str]]]:
    """Fit on FIT Development sessions only; SELECT and REPORT remain unopened here.

    Labels are passed separately, never injected into the scoring feature objects.
    This function neither selects a hyperparameter nor reports OOS skill.
    """
    authorize_research(authorization)
    splits = split_sessions(feature_rows)
    fit_dates = set(splits["fit"])
    fit_rows = []
    targets = []
    known_ids = set()
    unknown_count = 0
    for row in feature_rows:
        if any(key.startswith(("future", "label", "outcome")) for key in row):
            raise ContractError("OUTCOME_IN_FEATURE_ROW")
        if row["session"] not in fit_dates:
            continue
        key = _event_key(row)
        if key in known_ids:
            raise ContractError("DUPLICATE_FIT_ROW")
        known_ids.add(key)
        target = evaluator_labels.get(key)
        if not target or target.get("signedHighPct") is None or target.get("maePct") is None:
            unknown_count += 1
            continue
        targets.append(_head_targets(float(target["signedHighPct"]),
                                     float(target["maePct"])))
        fit_rows.append(row)
    if len(fit_rows) < 100:
        raise ContractError("INSUFFICIENT_FIT_ROWS")
    feature_names = tuple(sorted(set().union(*(r["features"] for r in fit_rows))))
    if not feature_names:
        raise ContractError("EMPTY_FEATURE_SCHEMA")
    serialized = json.dumps(feature_names, ensure_ascii=False, separators=(",", ":"))
    schema_sha = hashlib.sha256(serialized.encode()).hexdigest()
    X = _matrix(fit_rows, list(feature_names))
    if not math.isfinite(float(X[~__import__("numpy").isnan(X)].sum())):
        raise ContractError("NONFINITE_FEATURE_MATRIX")
    from sklearn.ensemble import HistGradientBoostingClassifier

    models = {}
    for head in HEADS:
        y = [t[head] for t in targets]
        if set(y) != {0, 1}:
            raise ContractError(f"HEAD_ONE_CLASS:{head}")
        clf = HistGradientBoostingClassifier(**MODEL_CONFIG)
        clf.fit(X, y)
        models[head] = clf
    return (TrainedSelector(
        models=models, feature_names=feature_names,
        fit_sessions=tuple(splits["fit"]),
        feature_schema_sha256=schema_sha,
        fit_population_n=len(fit_rows),
        missing_teacher_n=unknown_count,
    ), splits)
