"""FIT-only preprocessing and the three fixed estimator families."""
import math
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier, ExtraTreesClassifier
from sign_io import read

TRANSFORM_VERSION = "FIT_ONLY_ZERO_MISSING_INDICATORS_STANDARDIZATION_UNKNOWN_V1"

def estimator(family, config):
    spec = config["families"][family]
    cls = {"L": LogisticRegression, "H": HistGradientBoostingClassifier, "E": ExtraTreesClassifier}[family]
    kwargs = dict(spec["parameters"])
    if family == "H":
        kwargs["categorical_features"] = None
    # In sklearn1.8 the L2 objective is the l1_ratio=0 default. Keep and freeze
    # all other version-resolved defaults rather than upgrading the environment.
    return cls(**kwargs)

def fit_preprocessing(fit, numeric, categorical):
    v, missing = numeric_matrix(fit, numeric)
    x = np.hstack([v, missing])
    mean = x.mean(axis=0); scale = x.std(axis=0)
    scale[scale == 0] = 1
    vocabulary = {k: sorted({category(r["categorical"].get(k)) for r in fit} | {"UNKNOWN"}) for k in categorical}
    return {"numeric": numeric, "categorical": categorical, "mean": mean.tolist(), "scale": scale.tolist(),
            "vocabulary": vocabulary, "transform_version": TRANSFORM_VERSION, "fit_entry_ids": [r["entry_id"] for r in fit]}

def category(value):
    return "UNKNOWN" if value is None else str(value)

def numeric_matrix(data, numeric):
    v = np.zeros((len(data), len(numeric)), dtype=np.float64)
    missing = np.zeros_like(v)
    for i, r in enumerate(data):
        for j, k in enumerate(numeric):
            value = r["numeric"].get(k)
            if value is None or not math.isfinite(float(value)):
                missing[i, j] = 1
            else:
                v[i, j] = float(value)
    return v, missing

def transform(data, prep):
    v, missing = numeric_matrix(data, prep["numeric"])
    x = (np.hstack([v, missing]) - np.array(prep["mean"])) / np.array(prep["scale"])
    columns = [x]
    for k in prep["categorical"]:
        vocab = prep["vocabulary"][k]; index = {value: i for i, value in enumerate(vocab)}
        a = np.zeros((len(data), len(vocab)), dtype=np.float64)
        for i, r in enumerate(data):
            value = category(r["categorical"].get(k))
            a[i, index.get(value, index["UNKNOWN"])] = 1
        columns.append(a)
    return np.hstack(columns)

