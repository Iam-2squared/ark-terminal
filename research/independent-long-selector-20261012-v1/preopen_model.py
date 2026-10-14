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
        for key in ("sourceManifestVerified", "existingSealsReconciled", "reuseBasisConfirmed", "privateInputsOnly"):
            if plan.get(key) is not True:
                raise PreopenError("MARKET_INPUT_GATE:" + key)
        if not (plan.get("preopenRefreshCoverageVerified") is True or
                (plan.get("featureSourceCoverageVerified") is True
                 and plan.get("liveReadiness") == "NOT_CERTIFIED")):
            raise PreopenError("MARKET_INPUT_GATE:featureSourceCoverageVerified")
        if not plan.get("sourceManifestSha256") or not plan.get("exposureLedgerSha256"):
            raise PreopenError("SOURCE_AND_EXPOSURE_MANIFEST_REQUIRED")
    for name, rows in populations.items():
        if name not in sets or {r["session"] for r in rows} != sets[name]:
            raise PreopenError("POPULATION_SESSION_MANIFEST_MISMATCH")
        keys = [row_key(r) for r in rows]
        if len(keys) != len(set(keys)):
            raise PreopenError("DUPLICATE_LEARNING_IDENTITY")
        for row in rows:
            if plan["mode"] == "SYNTHETIC" and row.get("sampleKind") != "SYNTHETIC":
                raise PreopenError("REAL_ROW_IN_SYNTHETIC_BYPASS")
            if plan["mode"] == "AUTHORIZED_DEVELOPMENT" and row.get("sampleKind") == "SYNTHETIC":
                raise PreopenError("SYNTHETIC_ROW_IN_MARKET_PLAN")
            validate_feature_row(row)
            if row.get("missingRequiredSources"):
                raise PreopenError("REQUIRED_NATIVE_SOURCE_MISSING_BEFORE_FIT")


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
    # Avoid a second full Python list-of-lists copy at native market scale.
    out = np.empty((len(rows), len(names)), dtype=np.float64)
    for i, row in enumerate(rows):
        f = row["features"]
        out[i] = (f.vector(names) if hasattr(f, "vector") else
                  [float(f[k]) if f[k] is not None else np.nan for k in names])
    return out


def _logit(p):
    import numpy as np
    p = np.clip(p, 1e-8, 1-1e-8)
    return np.log(p/(1-p)).reshape(-1, 1)


def probability_diagnostics(probabilities, teachers):
    """Fixed ten equal-width ECE bins; descriptive, never column/model choice."""
    import numpy as np
    if not teachers:
        return {"status":"NOT_MEASURED","labelN":0}
    result={}
    for h in HEADS:
        p=np.asarray(probabilities[h],dtype=np.float64)
        y=np.asarray([r[h] for r in teachers],dtype=np.float64)
        if p.shape!=y.shape or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
            raise PreopenError("INVALID_PROBABILITY_DIAGNOSTIC_INPUT")
        indexes=np.minimum((p*10).astype(int),9)
        bins=[];ece=0.0
        for i in range(10):
            mask=indexes==i;n=int(mask.sum())
            mean=float(p[mask].mean()) if n else None
            observed=float(y[mask].mean()) if n else None
            if n:ece+=n/len(y)*abs(mean-observed)
            bins.append({"left":i/10,"right":(i+1)/10,"rightInclusive":i==9,
                         "N":n,"meanProbability":mean,"observedRate":observed})
        q=np.clip(p,1e-15,1-1e-15)
        result[h]={"N":len(y),"positiveN":int(y.sum()),"brier":float(np.mean((p-y)**2)),
                   "logLoss":float(np.mean(-y*np.log(q)-(1-y)*np.log1p(-q))),
                   "ece10":ece,"bins":bins}
    return {"status":"MEASURED_DESCRIPTIVE","labelN":len(teachers),
            "binPolicy":"TEN_EQUAL_WIDTH_PROBABILITY_BINS_FIXED_BEFORE_FIT","heads":result,
            "absoluteProbabilityCertified":False}


@dataclass
class PreopenModel:
    models: dict[str, Any]
    calibrators: dict[str, Any]
    all_columns: tuple[str, ...]
    used_columns: tuple[str, ...]
    receipt: dict

    def probabilities(self, rows: list[dict]) -> dict[tuple[str, str], dict]:
        import numpy as np
        from preopen_feature_policy import policy_hash
        if self.receipt.get("featurePolicyHash") != policy_hash():
            raise PreopenError("MODEL_FEATURE_POLICY_DRIFT")
        if not rows:
            return {}
        for r in rows:
            validate_feature_row(r)
            if self.receipt["mode"] == "SYNTHETIC" and r.get("sampleKind") != "SYNTHETIC":
                raise PreopenError("REAL_ROW_WITH_SYNTHETIC_MODEL")
            if self.receipt["mode"] == "AUTHORIZED_DEVELOPMENT" and r.get("sampleKind") == "SYNTHETIC":
                raise PreopenError("SYNTHETIC_ROW_WITH_MARKET_MODEL")
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
        return {row_key(row): {
            **{f"up{k}": float(u[i,j]) for j,k in enumerate(UP)},
            **{f"down{k}": float(d[i,j]) for j,k in enumerate(DOWN)},
            "close_negative": float(p["close_negative"][i])}
            for i,row in enumerate(rows)}

    def score(self, rows: list[dict]) -> dict[tuple[str, str], float]:
        return {key: sum(p[f"up{k}"] for k in UP)
                - 2*sum(p[f"down{k}"] for k in DOWN) - p["close_negative"]
                for key,p in self.probabilities(rows).items()}

    def watchlist(self, rows: list[dict]) -> dict:
        probabilities = self.probabilities(rows)
        scores = {key: sum(p[f"up{k}"] for k in UP)
                  - 2*sum(p[f"down{k}"] for k in DOWN) - p["close_negative"]
                  for key,p in probabilities.items()}
        watch = make_watchlist(rows, scores)
        for item in watch["items"]:
            item["headProbabilities"] = probabilities[row_key(item)]
            item["calibration"] = "SEPARATE_LOGISTIC_LOGIT_THEN_MIN_ENVELOPE"
        watch["watchlistHash"] = digest({k:v for k,v in watch.items() if k != "watchlistHash"})
        return watch


def train_preopen_model(fit_rows: list[dict], fit_labels: dict,
                        calibration_rows: list[dict], calibration_labels: dict,
                        plan: dict, *, execution_event=None) -> PreopenModel:
    """At most ten head fits and ten calibration fits; no threshold/model search.

    The future Report block is never consumed by this function. All checks that
    can fail from schema, missingness or class support run before the first fit.
    """
    validate_plan(plan, {"fit": fit_rows, "calibration": calibration_rows})
    if not fit_rows or not calibration_rows:
        raise PreopenError("EMPTY_LEARNING_PARTITION")
    all_names = tuple(sorted(fit_rows[0]["features"]))
    if any(tuple(sorted(r["features"])) != all_names
           for group in (fit_rows, calibration_rows) for r in group):
        raise PreopenError("INCONSISTENT_LEARNING_FEATURE_SCHEMA")
    known_fit, fit_y, unknown_fit = _join(fit_rows, fit_labels)
    known_cal, cal_y, unknown_cal = _join(calibration_rows, calibration_labels)
    if len(known_fit) < 40 or len(known_cal) < 20:
        raise PreopenError("INSUFFICIENT_ENGINEERING_FIT_SUPPORT")
    for h in HEADS:
        if {r[h] for r in fit_y} != {0, 1} or {r[h] for r in cal_y} != {0, 1}:
            raise PreopenError("HEAD_CLASS_SUPPORT_MISSING:" + h)
    # Row availability and all-missing/constant decisions use FIT only. Never
    # choose columns from calibration or Report support.
    reasons = {}
    for k in all_names:
        first, observed, variable = None, 0, False
        for r in known_fit:
            value = r["features"][k]
            if value is None:
                continue
            if observed and value != first:
                variable = True
            elif not observed:
                first = value
            observed += 1
        reasons[k] = ("ALL_MISSING_IN_FIT" if not observed else
                      "CONSTANT_IN_FIT" if not variable else None)
    names = tuple(k for k in all_names if reasons[k] is None)
    if not names:
        raise PreopenError("ALL_TRAINING_FEATURES_UNAVAILABLE")
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    import sklearn
    import numpy as np
    from threadpoolctl import threadpool_limits
    # HGB consumes float64 matrices and creates histogram/bin working arrays.
    # This conservative guard uses actual admitted dimensions, never shrinks the
    # population or chooses columns from Report to fit the current machine.
    estimate = 2*(len(known_fit)+len(known_cal))*len(names)*8 + len(known_fit)*len(names)*3 + 256*1024**2
    try:
        mem = dict(line.split(":",1) for line in Path("/proc/meminfo").read_text().splitlines())
        available = int(mem["MemAvailable"].strip().split()[0])*1024
        cgroup = Path("/sys/fs/cgroup/memory.max")
        current = Path("/sys/fs/cgroup/memory.current")
        if cgroup.exists() and cgroup.read_text().strip().isdigit():
            available = min(available,int(cgroup.read_text())-int(current.read_text()))
        if estimate > available*0.8:
            raise PreopenError("ADMITTED_MATRIX_EXCEEDS_CONSERVATIVE_MEMORY_BUDGET")
    except (OSError, KeyError):
        available = None
    X, C = matrix(known_fit, names), matrix(known_cal, names)
    models, calibrators = {}, {}
    raw_calibration, calibrated_calibration = {}, {}
    with threadpool_limits(limits=1):
        for h in HEADS:
            if execution_event: execution_event("BASE_ESTIMATOR_START",h)
            estimator = HistGradientBoostingClassifier(**MODEL_CONFIG)
            estimator.fit(X, [y[h] for y in fit_y])
            if execution_event: execution_event("BASE_ESTIMATOR_COMPLETE",h)
            calibration = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
            if execution_event: execution_event("CALIBRATION_START",h)
            raw_calibration[h]=estimator.predict_proba(C)[:, 1]
            calibration.fit(_logit(raw_calibration[h]), [y[h] for y in cal_y])
            if execution_event: execution_event("CALIBRATION_COMPLETE",h)
            models[h], calibrators[h] = estimator, calibration
            calibrated_calibration[h]=calibration.predict_proba(_logit(raw_calibration[h]))[:,1]
    final_calibration=dict(calibrated_calibration)
    for heads in ([f"up{k}" for k in UP],[f"down{k}" for k in DOWN]):
        final=np.minimum.accumulate(np.column_stack([calibrated_calibration[h] for h in heads]),axis=1)
        for j,h in enumerate(heads):final_calibration[h]=final[:,j]
    receipt = {"schema": "ARK_PREOPEN_TRAINING_RECEIPT_V1", "contract": CONTRACT,
               "labelId": LABEL, "mode": plan["mode"], "planHash": digest(plan),
               "featureSchemaHash": digest(all_names), "usedFeatureSchemaHash": digest(names),
               "fitRowHash": digest([(row_key(r),r["featureHash"]) for r in fit_rows]),
               "calibrationRowHash": digest([(row_key(r),r["featureHash"]) for r in calibration_rows]),
               "fitN": len(known_fit), "fitUnknownLabelN": unknown_fit,
               "calibrationN": len(known_cal), "calibrationUnknownLabelN": unknown_cal,
               "registeredFeatureN": len(all_names), "usedFeatureN": len(names),
               "memoryPreflight": {"estimatedPeakBytes":estimate,"availableBytes":available,
                                   "nativeScaleMeasured":False},
               "allMissingFitColumns": [k for k,v in reasons.items() if v == "ALL_MISSING_IN_FIT"],
               "constantFitColumns": [k for k,v in reasons.items() if v == "CONSTANT_IN_FIT"],
               "fitColumnExclusionReasons": {k:v for k,v in reasons.items() if v},
               "lastFitSession": max(plan["splits"]["fit"]),
               "lastCalibrationSession": max(plan["splits"]["calibration"]),
               "headEstimatorFits": 10, "calibrationFits": 10,
               "classSupport": {"fit": {h: {str(c): sum(y[h] == c for y in fit_y) for c in (0,1)} for h in HEADS},
                                "calibration": {h: {str(c): sum(y[h] == c for y in cal_y) for c in (0,1)} for h in HEADS}},
               "marketFits": 10 if plan["mode"] == "AUTHORIZED_DEVELOPMENT" else 0,
               "syntheticFits": 10 if plan["mode"] == "SYNTHETIC" else 0,
               "sklearnVersion": sklearn.__version__, "numpyVersion": np.__version__,
               "rankIsExpectedReturn": False, "productionReady": False,
               "calibrationDiagnostics":{
                   "rawBaseProbabilities":probability_diagnostics(raw_calibration,cal_y),
                   "separateCalibratorsBeforeEnvelope":probability_diagnostics(calibrated_calibration,cal_y),
                   "finalAfterMinEnvelope":probability_diagnostics(final_calibration,cal_y),
                   "sameCalibrationLabelsUsedToFitCalibrators":True,
                   "heldOutGeneralizationAssessment":False},
               "reportConsumedByFit": False, "executionAllowed": False,
               "monotonicity": "MIN_ENVELOPE_AFTER_SEPARATE_CALIBRATION"}
    from preopen_feature_policy import policy_hash
    receipt["featurePolicyHash"] = policy_hash()
    from preopen_feature_policy import source_code_hash
    receipt["codeHash"] = source_code_hash()
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


def load_private_model(directory: str | Path, *, private_root: str | Path,
                       expected_model_sha256: str, expected_schema_sha256: str) -> PreopenModel:
    """Hashes must come from an independently trusted private receipt.

    Hashing an untrusted pickle does not make it safe. Callers must restrict this
    entry point to their own trusted artifact; never accept uploaded joblib code.
    """
    import hashlib
    import joblib
    root = Path(private_root).resolve()
    model_dir = Path(directory).resolve()
    if not model_dir.is_relative_to(root):
        raise PreopenError("MODEL_OUTSIDE_EXPLICIT_PRIVATE_ROOT")
    file = (model_dir / "preopen_model.joblib").resolve()
    receipt_file = (model_dir / "receipt.json").resolve()
    if not file.is_relative_to(root) or not receipt_file.is_relative_to(root):
        raise PreopenError("MODEL_SYMLINK_OUTSIDE_PRIVATE_ROOT")
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    from preopen_feature_policy import policy_hash
    if receipt.get("featurePolicyHash") != policy_hash():
        raise PreopenError("TRUSTED_MODEL_FEATURE_POLICY_DRIFT")
    from preopen_feature_policy import source_code_hash
    if receipt.get("codeHash") != source_code_hash():
        raise PreopenError("TRUSTED_MODEL_CODE_DRIFT")
    if (hashlib.sha256(file.read_bytes()).hexdigest() != expected_model_sha256
            or receipt.get("modelFileSha256") != expected_model_sha256
            or receipt.get("featureSchemaHash") != expected_schema_sha256
            or receipt.get("trustedLocalObjectsOnly") is not True):
        raise PreopenError("TRUSTED_MODEL_HASH_OR_SCHEMA_MISMATCH")
    model = joblib.load(file)
    if not isinstance(model, PreopenModel) or digest(model.all_columns) != expected_schema_sha256:
        raise PreopenError("LOADED_MODEL_TYPE_OR_SCHEMA_MISMATCH")
    if set(model.models) != set(HEADS) or set(model.calibrators) != set(HEADS):
        raise PreopenError("LOADED_MODEL_HEAD_CONTRACT_MISMATCH")
    if model.receipt != {k:v for k,v in receipt.items()
                         if k not in ("modelFileSha256", "trustedLocalObjectsOnly")}:
        raise PreopenError("LOADED_MODEL_RECEIPT_MISMATCH")
    return model
