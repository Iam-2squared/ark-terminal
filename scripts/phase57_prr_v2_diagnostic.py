"""Development-only numerical mismatch receipt; exactly two fold-3 fits."""
from __future__ import annotations

import contextlib
import gzip
import hashlib
import io
import json
import locale
import math
import os
import platform
import sys
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.stats import kendalltau, rankdata, spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import threadpoolctl

from scripts import phase57_entry_all_material_r1_train as frozen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/phase57-prr-numerical-recovery"
OLD = ROOT / "docs/evidence/phase57-checkpoint-certified-guard-exit"
PREFIT = ROOT / "artifacts/all-material-r1/prefit"
PRE = "e57cd148f20b93633504994c67eeb28c4c97ac1f1334f54e7d10793e4442feb9"
PINS = {
    OLD / "POTENTIAL_FIT_PROTOCOL.json": "80fc1699457dfa725e032548f643241359468e0243ddc2671d4d0894d562e9bd",
    OLD / "POTENTIAL_OOF.jsonl.gz": "e51a7fe46806231b826af59028eb1a14184786c43554258fe8fc7524498caabd",
    OLD / "POTENTIAL_TEACHER_ROWS.jsonl.gz": "c6fa75eb3d3abfc65ebe56ee5fe219f8c8154221c7fe79f610d6904dab691057",
    PREFIT / "features.npy": "54bf771f6a090eb3e8035f7ee433ca1fbd617c165d77955ab71054b4e259a3fe",
    PREFIT / "feature-names.json": "57040ed4cb0cc008c3b2b33b32ae71d721c755a2e8a3ffa0455941c83bbd4275",
    PREFIT / "rows.json": "54f7dbb8bd0c9f8974ccccb7a949c0b7ebf0bbe46581be7778f1607f9d9d8cb6",
    PREFIT / "folds.json": "3342c68cc8a1987e11dda6f6c07757a47ff43d1e7f7f1506cb2e1ca0b3b41021",
}


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(x):
    if isinstance(x, np.ndarray):
        x = np.ascontiguousarray(x).tobytes()
    elif not isinstance(x, bytes):
        x = json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(x).hexdigest()


def encoded(x):
    return (json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                       allow_nan=False) + "\n").encode()


def write(name, value):
    (OUT / name).write_bytes(encoded(value))


def read_gz(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]


def gzwrite(name, values):
    (OUT / name).write_bytes(gzip.compress(b"".join(encoded(x) for x in values), mtime=0))


def cpu_model():
    f = Path("/proc/cpuinfo")
    if f.exists():
        for line in f.read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor()


def environment():
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        np.show_config()
    result = {
        "schema": "phase57-prr-v2-environment-audit-v1",
        "os": platform.platform(), "arch": platform.machine(), "cpu": cpu_model(),
        "pythonVersion": sys.version, "pythonExecutable": sys.executable,
        "packages": {"numpy": np.__version__, "scipy": scipy.__version__,
                     "scikitLearn": sklearn.__version__, "joblib": joblib.__version__,
                     "threadpoolctl": threadpoolctl.__version__, "pandas": pd.__version__},
        "numpyShowConfig": stream.getvalue(), "threadpoolInfo": threadpoolctl.threadpool_info(),
        "threadEnvironment": {k: os.environ.get(k) for k in
                              ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                               "NUMEXPR_NUM_THREADS", "PYTHONHASHSEED")},
        "locale": locale.setlocale(locale.LC_ALL), "timezone": list(time.tzname),
        "firstDiagnosticEnvironment": True, "providerRequests": 0,
        "restrictedPartitionsOpened": 0
    }
    result["environmentSha256"] = digest(result)
    write("ENVIRONMENT_AUDIT.json", result)
    return result


def preflight():
    require(sha_file(OUT / "CYCLE_PRECOMMIT.json") == PRE, "PRECOMMIT_DRIFT")
    actual = {str(path.relative_to(ROOT)): sha_file(path) for path in PINS}
    write("SOURCE_LINEAGE.json", {"schema": "phase57-prr-v2-source-lineage-v1",
          "status": "PASS" if all(actual[str(p.relative_to(ROOT))] == wanted
                                for p, wanted in PINS.items()) else "NUMERIC_SOURCE_LINEAGE_ABORT",
          "actualSha256": actual,
          "expectedSha256": {str(p.relative_to(ROOT)): h for p, h in PINS.items()}})
    require(all(actual[str(p.relative_to(ROOT))] == wanted for p, wanted in PINS.items()),
            "NUMERIC_SOURCE_LINEAGE_ABORT")
    protocol = json.loads((OLD / "POTENTIAL_FIT_PROTOCOL.json").read_text())
    require(protocol["model"] == {
        "heads": [5, 10], "family": "LogisticRegression", "penalty": "l2", "C": 1.0,
        "solver": "liblinear", "max_iter": 1000, "tol": .0001, "class_weight": None,
        "random_state": 570926}, "MODEL_LINEAGE_ABORT")


def fold_rows(fold_id):
    observed = read_gz(OLD / "POTENTIAL_TEACHER_ROWS.jsonl.gz")
    saved = {(r["arm"], r["entryId"]): r
             for r in read_gz(OLD / "POTENTIAL_OOF.jsonl.gz")}
    folds = json.loads((PREFIT / "folds.json").read_text())
    fold = next(f for f in folds if f["id"] == fold_id)
    rows = [r for r in observed if r["teacherUpsidePct"] is not None]
    train = [r for r in rows if r["session"] in set(fold["train"])]
    test = [r for r in rows if r["session"] in set(fold["test"]) and r["pinnedTest"]]
    require(len(train) == 1522 and len(test) == 114 and len(saved) == 1614,
            "FOLD3_IDENTITY_ABORT")
    require(all((r["arm"], r["entryId"]) in saved and
                r["featureRow"] == saved[(r["arm"], r["entryId"])]["featureRow"] and
                abs(r["teacherUpsidePct"] -
                    saved[(r["arm"], r["entryId"])]["teacherUpsidePct"]) <= 1e-12
                for r in test), "FOLD3_LABEL_IDENTITY_ABORT")
    return fold, train, test, saved


def inversion_rate(saved, rerun):
    n = len(saved)
    bad = 0
    comparable = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = np.sign(saved[i] - saved[j]), np.sign(rerun[i] - rerun[j])
            if a and b:
                comparable += 1
                bad += a != b
    return None if not comparable else bad / comparable


def compare(head, test, saved, scores, probs):
    old = np.asarray([saved[(r["arm"], r["entryId"])][f"probability{head}"]
                      for r in test], dtype=float)
    y = np.asarray([r["teacherUpsidePct"] >= head for r in test], dtype=int)
    srank, nrank = rankdata(old, method="average"), rankdata(scores, method="average")
    result = []
    for i, r in enumerate(test):
        p = float(old[i])
        logit = None if p <= 0 or p >= 1 else math.log(p) - math.log1p(-p)
        result.append({"entryId": r["entryId"], "arm": r["arm"],
            "session": r["session"], "fold": 3, "head": head,
            "savedProbability": p, "rerunProbability": float(probs[i]),
            "absoluteProbabilityDiff": float(abs(probs[i] - p)),
            "savedImpliedLogit": logit,
            "savedImpliedLogitNullReason": "SAVED_PROBABILITY_0_OR_1" if logit is None else None,
            "rerunDecisionScore": float(scores[i]),
            "absoluteScoreDiff": None if logit is None else float(abs(scores[i] - logit)),
            "savedRankWithinTestFold": float(srank[i]),
            "rerunRankWithinTestFold": float(nrank[i])})
    diffs = np.asarray([r["absoluteProbabilityDiff"] for r in result])
    idx = int(np.argmax(diffs))
    first = next((r for r in result if r["absoluteProbabilityDiff"] > 1e-10), None)
    return result, {"head": head, "n": len(result),
        "maxAbsDiff": float(diffs.max()), "meanAbsDiff": float(diffs.mean()),
        "medianAbsDiff": float(np.median(diffs)),
        "q95AbsDiff": float(np.quantile(diffs, .95)),
        "q99AbsDiff": float(np.quantile(diffs, .99)),
        "countsAbove": {str(t): int((diffs > t).sum())
                        for t in (1e-12, 1e-10, 1e-8, 1e-6)},
        "spearman": float(spearmanr(old, scores).statistic),
        "kendallTau": float(kendalltau(old, scores).statistic),
        "orderInversionRate": inversion_rate(old, scores),
        "savedAuc": float(roc_auc_score(y, old)),
        "rerunAuc": float(roc_auc_score(y, probs)),
        "aucDelta": float(roc_auc_score(y, probs) - roc_auc_score(y, old)),
        "firstMismatch": first, "maxMismatch": result[idx]}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    env = environment()
    preflight()
    fold, train, test, saved = fold_rows(3)
    X = np.load(PREFIT / "features.npy", mmap_mode="r")
    require(X.shape == (149900, 566), "FEATURE_SHAPE_ABORT")
    raw_train, raw_test = (np.asarray(X[[r["featureRow"] for r in rr]])
                           for rr in (train, test))
    pp = frozen.fit_preprocessor(raw_train)
    xt, xv = frozen.transform(raw_train, pp), frozen.transform(raw_test, pp)
    base = {"featureArraySha256": PINS[PREFIT / "features.npy"],
        "featureNamesSha256": PINS[PREFIT / "feature-names.json"],
        "rowsSha256": PINS[PREFIT / "rows.json"], "foldsSha256": PINS[PREFIT / "folds.json"],
        "teacherSha256": PINS[OLD / "POTENTIAL_TEACHER_ROWS.jsonl.gz"],
        "trainIdSequenceSha256": digest([(r["arm"], r["entryId"]) for r in train]),
        "testIdSequenceSha256": digest([(r["arm"], r["entryId"]) for r in test]),
        "trainRowOrderSha256": digest([r["featureRow"] for r in train]),
        "testRowOrderSha256": digest([r["featureRow"] for r in test]),
        "xShape": list(X.shape), "rawDtype": str(raw_train.dtype),
        "trainSessions": sorted({r["session"] for r in train}),
        "testSessions": sorted({r["session"] for r in test}),
        "preprocessing": {"nanmedianSha256": digest(pp["median"]),
            "meanSha256": digest(pp["mean"]), "stdSha256": digest(pp["scale"]),
            "indicatorSchemaSha256": digest({"columns": pp["columns"], "appendNonfinite": True}),
            "transformedTrainSha256": digest(xt), "transformedTestSha256": digest(xv),
            "transformedTrainShape": list(xt.shape), "transformedTestShape": list(xv.shape),
            "trainContiguous": bool(xt.flags.c_contiguous),
            "testContiguous": bool(xv.flags.c_contiguous)}}
    receipts, all_rows, summaries = [], [], []
    for head in (5, 10):
        y = np.asarray([r["teacherUpsidePct"] >= head for r in train], dtype=int)
        require(set(y) == {0, 1}, "UNTRAINABLE_HEAD")
        model = LogisticRegression(penalty="l2", C=1., solver="liblinear",
                                   max_iter=1000, tol=.0001, class_weight=None,
                                   random_state=570926)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model.fit(xt, y)
        tr_score, te_score = model.decision_function(xt), model.decision_function(xv)
        tr_prob, te_prob = model.predict_proba(xt)[:, 1], model.predict_proba(xv)[:, 1]
        compared, summary = compare(head, test, saved, te_score, te_prob)
        all_rows.extend(compared)
        summaries.append(summary)
        receipts.append({"fold": 3, "head": head, "trainN": len(train), "testN": len(test),
            "trainPositive": int(y.sum()), "trainNegative": int(len(y) - y.sum()),
            "coefSha256": digest(model.coef_), "interceptSha256": digest(model.intercept_),
            "coefSummary": {"min": float(model.coef_.min()), "max": float(model.coef_.max()),
                            "l2Norm": float(np.linalg.norm(model.coef_))},
            "intercept": model.intercept_.tolist(), "nIter": model.n_iter_.tolist(),
            "warnings": [str(w.message) for w in caught],
            "trainScoreSha256": digest(tr_score), "testScoreSha256": digest(te_score),
            "trainProbabilitySha256": digest(tr_prob),
            "testProbabilitySha256": digest(te_prob),
            "trainMedianScore": float(np.median(tr_score))})
    gzwrite("DIAGNOSTIC_MISMATCH_ROWS.jsonl.gz", all_rows)
    write("MISMATCH_DIAGNOSTIC.json", {
        "schema": "phase57-prr-v2-mismatch-diagnostic-v1",
        "status": "OLD_OOF_EXACT_REPRODUCTION_PASS" if
                  all(x["countsAbove"]["1e-10"] == 0 for x in summaries) else
                  "OLD_OOF_EXACT_REPRODUCTION_FAIL",
        "previousCycleStatusUnchanged": "RANK_REPRODUCTION_FAIL",
        "environmentSha256": env["environmentSha256"], "precommitSha256": PRE,
        "fitAttempts": 2, "sourceAndDataset": base, "models": receipts,
        "headSummary": summaries, "diagnosticRowsN": len(all_rows),
        "diagnosticRowsSha256": sha_file(OUT / "DIAGNOSTIC_MISMATCH_ROWS.jsonl.gz"),
        "noEconomicsInspected": True, "providerRequests": 0, "restrictedPartitionsOpened": 0})
    print(json.dumps({"status": "DIAGNOSTIC_SAVED", "fitAttempts": 2,
          "firstMismatch": [x["firstMismatch"] for x in summaries]}))


if __name__ == "__main__":
    run()
