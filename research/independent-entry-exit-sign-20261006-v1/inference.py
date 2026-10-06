"""Standalone research inference: no teacher/outcome/account interface."""
from threadpoolctl import threadpool_limits
from sign_model import transform
from sign_policy import filter_action

SNAPSHOT_FIELDS = {"entry_id", "decision_ts", "numeric", "categorical", "availability_status",
                   "feature_as_of", "source_available_at", "valid_from", "transform_version",
                   "source_hash", "max_source_available_at", "feature_schema_hash"}

def load_artifacts(model_path, threshold_path):
    """Load the verified artifacts created by this research cycle."""
    import pickle
    from pathlib import Path
    from sign_io import sha, read
    with Path(model_path).open("rb") as f:
        model = pickle.load(f)
    model["model_hash"] = sha(model_path)
    threshold = read(threshold_path)
    threshold["threshold_hash"] = sha(threshold_path)
    assert threshold["model_hash"] == model["model_hash"]
    return model, threshold

def predict_sign(snapshot, model_artifact, threshold_artifact):
    assert set(snapshot) <= SNAPSHOT_FIELDS, "FORBIDDEN_INFERENCE_FIELD"
    assert snapshot["feature_schema_hash"] == model_artifact["feature_schema_hash"]
    assert threshold_artifact["model_hash"] == model_artifact["model_hash"]
    assert snapshot["transform_version"] == model_artifact["preprocessing"]["transform_version"]
    available = snapshot["availability_status"] == "HISTORICAL_ASSUMED_AVAILABILITY"
    available = available and snapshot["max_source_available_at"] <= snapshot["decision_ts"]
    available = available and snapshot["feature_as_of"] <= snapshot["decision_ts"]
    available = available and snapshot["valid_from"] <= snapshot["decision_ts"]
    numeric = model_artifact["preprocessing"]["numeric"]
    categorical = model_artifact["preprocessing"]["categorical"]
    # The contract accepts schema fields only. Extra learned/market/Capital
    # columns are rejected even when an estimator could silently ignore them.
    assert set(snapshot["numeric"]) == set(numeric)
    assert set(snapshot["categorical"]) == set(categorical)
    probability = None
    if available and model_artifact["model"] is not None:
        x = transform([snapshot], model_artifact["preprocessing"])
        classes = list(model_artifact["model"].classes_)
        assert classes == [0, 1], "SIGN_CLASS_ORDER"
        with threadpool_limits(limits=2):
            probability = float(model_artifact["model"].predict_proba(x)[0, classes.index(1)])
    return {"entry_id": snapshot["entry_id"], "decision_ts": snapshot["decision_ts"], "p_plus": probability,
            "predicted_sign": "ABSTAIN" if probability is None else "PRED_PLUS" if probability >= 0.5 else "PRED_MINUS",
            "filter_action": filter_action(probability, threshold_artifact),
            "availability_status": snapshot["availability_status"] if probability is not None else "ABSTAIN",
            "model_hash": model_artifact["model_hash"], "threshold_hash": threshold_artifact["threshold_hash"],
            "feature_schema_hash": model_artifact["feature_schema_hash"],
            "max_source_available_at": snapshot["max_source_available_at"],
            "fit_cutoff": model_artifact["fit_cutoff"], "cal_cutoff": threshold_artifact["cal_cutoff"],
            "exposure_status": "HISTORICALLY_EXPOSED_DEVELOPMENT"}
