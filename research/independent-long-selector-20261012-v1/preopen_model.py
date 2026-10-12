"""Finite preopen learning recipe. Rank scores are NOT executable expected returns.

Market use requires exact, reconciled Development session lists and mounted
private inputs. A new copy of historical data does not restore freshness.
Only trusted locally produced model objects may be serialized/deserialized.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from preopen_selector import (CONTRACT, LABEL, PreopenConfig, PreopenError,
                              digest, number, row_key, validate_feature_row,
                              make_watchlist)

UP = (1, 2, 3, 4, 5)
DOWN = (1, 2, 3, 5)
HEADS = tuple([f"up{k}" for k in UP] + [f"down{k}" for k in DOWN] + ["close_negative"])
MODEL_CONFIG = dict(learning_rate=0.05, max_leaf_nodes=15, max_iter=120,
                    min_samples_leaf=40, l2_regularization=10.0,
                    early_stopping=False, random_state=20261012)


def validate_plan(plan: dict, populations: dict[str, list[dict]]) -> None:
    if plan.get("contract") != CONTRACT or plan.get("mode") not in ("SYNTHETIC", "AUTHORIZED_DEVELOPMENT"):
        raise PreopenError("PREOPEN_LEARNING_NOT_AUTHORIZED")
    splits = plan.get("splits", {})
    sets = {}
    for key in ("fit", "calibration", "report"):
        ds = splits.get(key)
        if not isinstance(ds, list) or not ds or ds != sorted(set(ds)):
            raise PreopenError("EXPLICIT_ORDERED_SESSION_LISTS_REQUIRED")
        sets[key] = set(ds)
    if not max(sets["fit"]) < min(sets["calibration"]) or not max(sets["calibration"]) < min(sets["report"]):
        raise PreopenError("FIT_CALIBRATION_REPORT_TIME_LEAKAGE")
    protected = set(plan.get("protectedSessions", []))
    if protected.intersection(set.union(*sets.values())):
        raise PreopenError("PROTECTED_SESSION_OVERLAP")
    if plan["mode"] == "AUTHORIZED_DEVELOPMENT":
        for key in ("sourceManifestVerified", "existingSealsReconciled", "reuseBasisConfirmed", "privateInputsOnly", "preopenRefreshCoverageVerified"):
            if plan.get(key) is not True:
                raise PreopenError("MARKET_INPUT_GATE:" + key)
        if not plan.get("sourceManifestSha256") or not plan.get("exposureLedgerSha256"):
            raise PreopenError("SOURCE_AND_EXPOSURE_MANIFEST_REQUIRED")
    for name, rows in populations.items():
        if name not in sets or {r["session"] for r in rows} != sets[name]:
            raise PreopenError("POPULATION_SESSION_MANIFEST_MISMATCH")
        keys = [row_key(r) for r in rows]
        if len(keys) != len(set(keys)):
            raise PreopenError("DUPLICATE_LEARNING_IDENTITY")
        for row in rows:
            validate_feature_row(row)
            if plan["mode"] == "SYNTHETIC" and row.get("sampleKind") != "SYNTHETIC":
                raise PreopenError("REAL_ROW_IN_SYNTHETIC_BYPASS")


def _teacher(row: dict) -> dict[str, int] | None:
    if row.get("labelId") != LABEL:
        raise PreopenError("WRONG_PREOPEN_TEACHER")
    if row.get("status") != "KNOWN":
        return None
    up = number(row["openHighPct"])
    down = number(row["openLowPct"])
    close = number(row["openClosePct"])
    if up < 0 or down > 0 or not down <= close <= up:
        raise PreopenError("INCONSISTENT_PREOPEN_TEACHER")
    # Exact hit predicates were computed from rational raw prices by evaluator.
    if set(row["upHits"]) != {str(k) for k in UP} or set(row["lowHits"]) != {str(k) for k in DOWN}:
        raise PreopenError("INCOMPLETE_TEACHER_HEADS")
    if any(type(v) is not bool for v in list(row["upHits"].values()) + list(row["lowHits"].values())):
        raise PreopenError("NONBOOLEAN_TEACHER_PREDICATE")
    out = {f"up{k}": int(row["upHits"][str(k)]) for k in UP}
    out.update({f"down{k}": int(row["lowHits"][str(k)]) for k in DOWN})
    out["close_negative"] = int(row["closeNegative"])
    return out


def _join(rows: list[dict], labels: dict[tuple[str, str], dict]):
    allowed = {row_key(r) for r in rows}
    if set(labels).difference(allowed):
        raise PreopenError("OUTSIDE_PARTITION_LABELS_PASSED_TO_FIT")
    known, teachers, unknown = [], [], 0
    for r in rows:
        lab = labels.get(row_key(r))
        if lab is not None and row_key(lab) != row_key(r):
            raise PreopenError("TEACHER_IDENTITY_MISMATCH")
        y = _teacher(lab) if lab is not None else None
        if y is None:
            unknown += 1
        else:
            known.append(r)
            teachers.append(y)
    return known, teachers, unknown


def matrix(rows: list[dict], names: tuple[str, ...]):
    import numpy as np
    return np.asarray([[float(r["features"][k]) if r["features"][k] is not None else np.nan
                        for k in names] for r in rows], dtype=float)


def _logit(p):
    import numpy as np
    p = np.clip(p, 1e-8, 1-1e-8)
    return np.log(p/(1-p)).reshape(-1, 1)


@dataclass
class PreopenModel:
    models: dict[str, Any]
    calibrators: dict[str, Any]
    all_columns: tuple[str, ...]
    used_columns: tuple[str, ...]
    receipt: dict

    def score(self, rows: list[dict]) -> dict[tuple[str, str], float]:
        import numpy as np
        if not rows:
            return {}
        for r in rows:
            validate_feature_row(r)
            if tuple(sorted(r["features"])) != self.all_columns:
                raise PreopenError("FIT_LIVE_FEATURE_SCHEMA_MISMATCH")
            if r["session"] <= self.receipt["lastCalibrationSession"]:
                raise PreopenError("IN_FIT_OR_CALIBRATION_NOT_FORWARD_PREDICTION")
        X = matrix(rows, self.used_columns)
        p = {}
        for h in HEADS:
            raw = self.models[h].predict_proba(X)[:, 1]
            p[h] = self.calibrators[h].predict_proba(_logit(raw))[:, 1]
        # Independent cumulative classifiers can cross. This deterministic
        # monotone envelope is part of the preregistered implementation, not
        # certification of absolute probabilities or a new joint probability law.
        u = np.minimum.accumulate(np.column_stack([p[f"up{k}"] for k in UP]), axis=1)
        d = np.minimum.accumulate(np.column_stack([p[f"down{k}"] for k in DOWN]), axis=1)
        values = u.sum(axis=1) - 2*d.sum(axis=1) - p["close_negative"]
        return {row_key(row): float(v) for row, v in zip(rows, values)}

    def watchlist(self, rows: list[dict]) -> dict:
        return make_watchlist(rows, self.score(rows))


def train_preopen_model(fit_rows: list[dict], fit_labels: dict,
                        calibration_rows: list[dict], calibration_labels: dict,
                        plan: dict) -> PreopenModel:
    """At most ten head fits and ten calibration fits; no threshold/model search.

    The future Report block is never consumed by this function. All checks that
    can fail from schema, missingness or class support run before the first fit.
    """
    validate_plan(plan, {"fit": fit_rows, "calibration": calibration_rows})
    if not fit_rows or not calibration_rows:
        raise PreopenError("EMPTY_LEARNING_PARTITION")
    all_names = tuple(sorted(fit_rows[0]["features"]))
    if any(tuple(sorted(r["features"])) != all_names for r in fit_rows+calibration_rows):
        raise PreopenError("INCONSISTENT_LEARNING_FEATURE_SCHEMA")
    known_fit, fit_y, unknown_fit = _join(fit_rows, fit_labels)
    known_cal, cal_y, unknown_cal = _join(calibration_rows, calibration_labels)
    if len(known_fit) < 40 or len(known_cal) < 20:
        raise PreopenError("INSUFFICIENT_ENGINEERING_FIT_SUPPORT")
    for h in HEADS:
        if {r[h] for r in fit_y} != {0, 1} or {r[h] for r in cal_y} != {0, 1}:
            raise PreopenError("HEAD_CLASS_SUPPORT_MISSING:" + h)
    names = tuple(k for k in all_names if any(r["features"][k] is not None for r in known_fit))
    if not names:
        raise PreopenError("ALL_TRAINING_FEATURES_UNAVAILABLE")
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    import sklearn
    import numpy as np
    from threadpoolctl import threadpool_limits
    X, C = matrix(known_fit, names), matrix(known_cal, names)
    models, calibrators = {}, {}
    with threadpool_limits(limits=1):
        for h in HEADS:
            estimator = HistGradientBoostingClassifier(**MODEL_CONFIG)
            estimator.fit(X, [y[h] for y in fit_y])
            calibration = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
            calibration.fit(_logit(estimator.predict_proba(C)[:, 1]), [y[h] for y in cal_y])
            models[h], calibrators[h] = estimator, calibration
    receipt = {"schema": "ARK_PREOPEN_TRAINING_RECEIPT_V1", "contract": CONTRACT,
               "labelId": LABEL, "mode": plan["mode"], "planHash": digest(plan),
               "featureSchemaHash": digest(all_names), "usedFeatureSchemaHash": digest(names),
               "fitRowHash": digest([(row_key(r),r["featureHash"]) for r in fit_rows]),
               "calibrationRowHash": digest([(row_key(r),r["featureHash"]) for r in calibration_rows]),
               "fitN": len(known_fit), "fitUnknownLabelN": unknown_fit,
               "calibrationN": len(known_cal), "calibrationUnknownLabelN": unknown_cal,
               "registeredFeatureN": len(all_names), "usedFeatureN": len(names),
               "allMissingFitColumns": [k for k in all_names if k not in names],
               "lastFitSession": max(plan["splits"]["fit"]),
               "lastCalibrationSession": max(plan["splits"]["calibration"]),
               "headEstimatorFits": 10, "calibrationFits": 10,
               "marketFits": 10 if plan["mode"] == "AUTHORIZED_DEVELOPMENT" else 0,
               "syntheticFits": 10 if plan["mode"] == "SYNTHETIC" else 0,
               "sklearnVersion": sklearn.__version__, "numpyVersion": np.__version__,
               "rankIsExpectedReturn": False, "productionReady": False,
               "reportConsumedByFit": False, "executionAllowed": False,
               "monotonicity": "MIN_ENVELOPE_AFTER_SEPARATE_CALIBRATION"}
    return PreopenModel(models, calibrators, all_names, names, receipt)


def save_private_model(model: PreopenModel, directory: str | Path) -> dict:
    """Save an exclusive new local artifact. Never publishes to public GitHub."""
    import joblib
    import hashlib
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    p = root / "preopen_model.joblib"
    joblib.dump(model, p)
    receipt = {**model.receipt, "modelFileSha256": hashlib.sha256(p.read_bytes()).hexdigest(),
               "trustedLocalObjectsOnly": True}
    (root / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return receipt
