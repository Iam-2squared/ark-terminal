"""Two independent six-fit canonical passes; no economic data access."""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import warnings

import numpy as np
from scipy.stats import kendalltau, rankdata, spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from scripts import phase57_entry_all_material_r1_train as frozen
from scripts import phase57_prr_v2_diagnostic as d

OUT, OLD, PREFIT = d.OUT, d.OLD, d.PREFIT


def snapshot(name, data):
    d.write(name, data)


def started(pass_name):
    path = OUT / "FIT_ATTEMPTS.json"
    receipt = json.loads(path.read_text()) if path.exists() else {
        "schema": "phase57-prr-v2-fit-attempts-v1", "diagnostic": 2,
        "canonical": [], "maximum": 14}
    d.require(len(receipt["canonical"]) < 12, "FIT_BUDGET_ABORT")
    receipt["canonical"].append(pass_name)
    receipt["totalAttempted"] = 2 + len(receipt["canonical"])
    snapshot("FIT_ATTEMPTS.json", receipt)


def fold_data(fold, observed, saved, X):
    tr_s, te_s = set(fold["train"]), set(fold["test"])
    train = [r for r in observed if r["session"] in tr_s]
    test = [r for r in observed if r["session"] in te_s and r["pinnedTest"]]
    d.require(train and test and not tr_s & te_s, "FOLD_SPLIT_ABORT")
    d.require(all((r["arm"], r["entryId"]) in saved and
                  r["featureRow"] == saved[(r["arm"], r["entryId"])]["featureRow"] and
                  abs(r["teacherUpsidePct"] -
                      saved[(r["arm"], r["entryId"])]["teacherUpsidePct"]) <= 1e-12
                  for r in test), "OOF_ENTRY_LABEL_ABORT")
    raw_train = np.asarray(X[[r["featureRow"] for r in train]])
    raw_test = np.asarray(X[[r["featureRow"] for r in test]])
    pp = frozen.fit_preprocessor(raw_train)
    xt, xv = frozen.transform(raw_train, pp), frozen.transform(raw_test, pp)
    pp_receipt = {
        "medianSha256": d.digest(pp["median"]), "meanSha256": d.digest(pp["mean"]),
        "stdSha256": d.digest(pp["scale"]), "indicatorSha256":
            d.digest({"columns": pp["columns"], "appendNonfinite": True}),
        "trainMatrixSha256": d.digest(xt), "testMatrixSha256": d.digest(xv),
        "trainEntryIdSequenceSha256": d.digest([(r["arm"], r["entryId"]) for r in train]),
        "testEntryIdSequenceSha256": d.digest([(r["arm"], r["entryId"]) for r in test]),
        "trainFeatureRowSequenceSha256": d.digest([r["featureRow"] for r in train]),
        "testFeatureRowSequenceSha256": d.digest([r["featureRow"] for r in test])}
    return train, test, xt, xv, pp_receipt


def pass_run(pass_name):
    OUT.mkdir(parents=True, exist_ok=True)
    d.preflight()
    env = d.environment()
    freeze = json.loads((OUT / "CANONICAL_ENVIRONMENT.json").read_text())
    d.require(freeze["status"] == "CANONICAL_ENVIRONMENT_FROZEN",
              "CANONICAL_ENV_NOT_FROZEN")
    d.require(freeze["selectedEnvironmentSha256"] == env["environmentSha256"],
              "CANONICAL_ENVIRONMENT_MISMATCH_ABORT")
    snapshot(f"CANONICAL_RUNTIME_ENV_{pass_name}.json", env)
    X = np.load(PREFIT / "features.npy", mmap_mode="r")
    d.require(X.shape == (149900, 566), "FEATURE_DIMENSION_ABORT")
    observed = [r for r in d.read_gz(OLD / "POTENTIAL_TEACHER_ROWS.jsonl.gz")
                if r["teacherUpsidePct"] is not None]
    saved = {(r["arm"], r["entryId"]): r for r in
             d.read_gz(OLD / "POTENTIAL_OOF.jsonl.gz")}
    folds = [f for f in json.loads((PREFIT / "folds.json").read_text())
             if f["id"] in (3, 4, 5)]
    d.require([f["id"] for f in folds] == [3, 4, 5] and len(saved) == 1614,
              "FOLD_TOPOLOGY_ABORT")
    rows, receipts = [], []
    for fold in folds:
        train, test, xt, xv, pp = fold_data(fold, observed, saved, X)
        d.require(len(train) == {3: 1522, 4: 2287, 5: 3028}[fold["id"]] and
                  len(test) == {3: 114, 4: 758, 5: 742}[fold["id"]],
                  "FOLD_COUNT_ABORT")
        scores = {}
        for head in (5, 10):
            y = np.asarray([r["teacherUpsidePct"] >= head for r in train], dtype=int)
            d.require(set(y) == {0, 1}, "CLASS_COUNT_ABORT")
            started(pass_name)
            model = LogisticRegression(penalty="l2", C=1., solver="liblinear",
                max_iter=1000, tol=.0001, class_weight=None, random_state=570926)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                model.fit(xt, y)
            tr_score, te_score = model.decision_function(xt), model.decision_function(xv)
            te_prob = model.predict_proba(xv)[:, 1]
            median = float(np.median(tr_score))
            scores[head] = (te_score, te_prob, median)
            receipts.append({"fold": fold["id"], "head": head, "trainN": len(train),
                "testN": len(test), "positiveTrainN": int(y.sum()), "preprocessing": pp,
                "coefSha256": d.digest(model.coef_),
                "interceptSha256": d.digest(model.intercept_),
                "coef": model.coef_.tolist(), "intercept": model.intercept_.tolist(),
                "nIter": model.n_iter_.tolist(), "warnings":
                    [str(w.message) for w in caught],
                "trainScoreSha256": d.digest(tr_score),
                "trainScores": tr_score.tolist(),
                "testScoreSha256": d.digest(te_score),
                "trainMedianScore": median,
                "testProbabilitySha256": d.digest(te_prob)})
        for i, r in enumerate(test):
            x = {"arm": r["arm"], "entryId": r["entryId"], "session": r["session"],
                 "fold": fold["id"], "featureRow": r["featureRow"],
                 "teacherUpsidePctEvaluatorOnly": r["teacherUpsidePct"]}
            for head in (5, 10):
                ts, tp, median = scores[head]
                x[f"score{head}"] = float(ts[i])
                x[f"probability{head}DiagnosticOnly"] = float(tp[i])
                x[f"medianTrain{head}"] = median
                x[f"low{head}"] = bool(ts[i] < median)
            x["routeDecision"] = ("DEFENSIVE_ELIGIBLE" if x["low5"] and x["low10"]
                                  else "CONTROL_DEFAULT")
            rows.append(x)
    rows.sort(key=lambda x: (x["arm"], x["entryId"]))
    d.require(len(rows) == len({(r["arm"], r["entryId"]) for r in rows}) == 1614,
              "OOF_CENSUS_ABORT")
    d.gzwrite(f"CANONICAL_PASS_{pass_name}_OOF.jsonl.gz", rows)
    snapshot(f"CANONICAL_PASS_{pass_name}_FIT.json", {
        "schema": "phase57-prr-v2-canonical-pass-v1", "pass": pass_name,
        "environmentSha256": env["environmentSha256"],
        "fitAttempts": 6, "models": receipts,
        "oofSha256": d.sha_file(OUT / f"CANONICAL_PASS_{pass_name}_OOF.jsonl.gz"),
        "sourceSha256": {str(p.relative_to(d.ROOT)): h for p, h in d.PINS.items()}})
    print(json.dumps({"pass": pass_name, "fits": 6, "oofN": len(rows)}))


def mismatch_summary(rows, saved, head):
    rr = [r for r in rows if r["head"] == head]
    diffs = np.asarray([r["absoluteProbabilityDiff"] for r in rr])
    y = np.asarray([r["teacherUpsidePctEvaluatorOnly"] >= head for r in rr])
    old = np.asarray([r["savedProbability"] for r in rr])
    new = np.asarray([r["rerunProbability"] for r in rr])
    inversion = comparable = 0
    for i in range(len(old)):
        s1 = np.sign(old[i] - old[i + 1:])
        s2 = np.sign(new[i] - new[i + 1:])
        valid = (s1 != 0) & (s2 != 0)
        comparable += int(np.sum(valid))
        inversion += int(np.sum(valid & (s1 != s2)))
    return {"head": head, "n": len(rr), "maxAbsDiff": float(diffs.max()),
        "meanAbsDiff": float(diffs.mean()), "medianAbsDiff": float(np.median(diffs)),
        "q95AbsDiff": float(np.quantile(diffs, .95)),
        "q99AbsDiff": float(np.quantile(diffs, .99)),
        "countsAbove": {str(t): int((diffs > t).sum())
                        for t in (1e-12, 1e-10, 1e-8, 1e-6)},
        "spearman": float(spearmanr(old, new).statistic),
        "kendallTau": float(kendalltau(old, new).statistic),
        "orderInversionRate": None if not comparable else inversion / comparable,
        "savedAuc": float(roc_auc_score(y, old)),
        "rerunAuc": float(roc_auc_score(y, new)),
        "aucDelta": float(roc_auc_score(y, new) - roc_auc_score(y, old)),
        "firstMismatch": next((r for r in rr if r["absoluteProbabilityDiff"] > 1e-10), None),
        "maxMismatch": max(rr, key=lambda r: r["absoluteProbabilityDiff"])}


def compare():
    a, b = (d.read_gz(OUT / f"CANONICAL_PASS_{p}_OOF.jsonl.gz") for p in ("A", "B"))
    fa, fb = (json.loads((OUT / f"CANONICAL_PASS_{p}_FIT.json").read_text())
              for p in ("A", "B"))
    d.require(len(a) == len(b) == 1614 and len(fa["models"]) ==
              len(fb["models"]) == 6, "PASS_TOPOLOGY_ABORT")
    model_diffs = []
    for x, y in zip(fa["models"], fb["models"]):
        d.require((x["fold"], x["head"]) == (y["fold"], y["head"]), "PASS_MODEL_ID_ABORT")
        pp_exact = x["preprocessing"] == y["preprocessing"]
        coef = float(np.max(np.abs(np.asarray(x["coef"]) - np.asarray(y["coef"]))))
        intercept = float(np.max(np.abs(np.asarray(x["intercept"]) -
                                        np.asarray(y["intercept"]))))
        median = abs(x["trainMedianScore"] - y["trainMedianScore"])
        train_score_diff = float(np.max(np.abs(np.asarray(x["trainScores"]) -
                                               np.asarray(y["trainScores"]))))
        model_diffs.append({"fold": x["fold"], "head": x["head"],
            "preprocessingHashesExact": pp_exact,
            "coefficientMaxAbsDiff": coef, "interceptMaxAbsDiff": intercept,
            "trainMedianAbsDiff": median,
            "trainScoreSha256Exact": x["trainScoreSha256"] == y["trainScoreSha256"],
            "trainScoreMaxAbsDiff": train_score_diff})
    row_diffs = []
    for x, y in zip(a, b):
        d.require((x["arm"], x["entryId"], x["fold"], x["featureRow"]) ==
                  (y["arm"], y["entryId"], y["fold"], y["featureRow"]),
                  "PASS_ENTRY_IDENTITY_ABORT")
        row_diffs.append({"arm": x["arm"], "entryId": x["entryId"], "fold": x["fold"],
          "score5Abs": abs(x["score5"] - y["score5"]),
          "score10Abs": abs(x["score10"] - y["score10"]),
          "routeMismatch": x["routeDecision"] != y["routeDecision"]})
    ordering = {}
    for fold in (3, 4, 5):
        for h in (5, 10):
            aa = [r for r in a if r["fold"] == fold]
            bb = [r for r in b if r["fold"] == fold]
            ordering[f"{fold}:{h}"] = np.argsort(
                [r[f"score{h}"] for r in aa], kind="mergesort").tolist() == np.argsort(
                [r[f"score{h}"] for r in bb], kind="mergesort").tolist()
    mismatch_n = sum(r["routeMismatch"] for r in row_diffs)
    stable = (mismatch_n == 0 and all(ordering.values()) and
      all(r["preprocessingHashesExact"] and r["trainScoreMaxAbsDiff"] <= 1e-12 and
          r["coefficientMaxAbsDiff"] <= 1e-12 and
          r["interceptMaxAbsDiff"] <= 1e-12 and
          r["trainMedianAbsDiff"] <= 1e-12 for r in model_diffs) and
      all(r["score5Abs"] <= 1e-12 and r["score10Abs"] <= 1e-12 for r in row_diffs))
    snapshot("ROUTE_STABILITY.json", {
      "schema": "phase57-prr-v2-route-stability-v1",
      "status": "CANONICAL_ROUTE_REPRODUCTION_PASS" if stable else
                "CANONICAL_ROUTE_REPRODUCTION_FAIL",
      "passAOOFSha256": fa["oofSha256"], "passBOOFSha256": fb["oofSha256"],
      "byteIdentical": fa["oofSha256"] == fb["oofSha256"],
      "routeMismatchN": mismatch_n,
      "firstRouteMismatch": next((x for x in row_diffs if x["routeMismatch"]), None),
      "maxScore5AbsDiff": max(r["score5Abs"] for r in row_diffs),
      "maxScore10AbsDiff": max(r["score10Abs"] for r in row_diffs),
      "modelDiffs": model_diffs, "orderingIdentityByFoldHead": ordering,
      "numericTolerance": 1e-12, "canonicalFitAttempts": 12,
      "totalFitAttemptsIncludingDiagnostic": 14})
    prior = {(r["arm"], r["entryId"]): r
             for r in d.read_gz(OLD / "POTENTIAL_OOF.jsonl.gz")}
    compared = []
    for fold in (3, 4, 5):
        subset = [r for r in a if r["fold"] == fold]
        for head in (5, 10):
            old = np.asarray([prior[(r["arm"], r["entryId"])][f"probability{head}"]
                              for r in subset], dtype=float)
            new = np.asarray([r[f"score{head}"] for r in subset], dtype=float)
            old_rank, new_rank = rankdata(old, method="average"), rankdata(new, method="average")
            for i, r in enumerate(subset):
                p = float(old[i])
                logit = None if p <= 0 or p >= 1 else math.log(p) - math.log1p(-p)
                q = r[f"probability{head}DiagnosticOnly"]
                compared.append({"arm": r["arm"], "entryId": r["entryId"],
                    "session": r["session"], "fold": fold, "head": head,
                    "teacherUpsidePctEvaluatorOnly": r["teacherUpsidePctEvaluatorOnly"],
                    "savedProbability": p, "rerunProbability": q,
                    "absoluteProbabilityDiff": abs(q - p),
                    "savedImpliedLogit": logit,
                    "savedImpliedLogitNullReason":
                        "SAVED_PROBABILITY_0_OR_1" if logit is None else None,
                    "rerunDecisionScore": float(new[i]),
                    "absoluteScoreDiff": None if logit is None else abs(float(new[i]) - logit),
                    "savedRankWithinTestFold": float(old_rank[i]),
                    "rerunRankWithinTestFold": float(new_rank[i])})
    d.require(len(compared) == 3228, "MISMATCH_CENSUS_ABORT")
    d.gzwrite("MISMATCH_ROWS.jsonl.gz", compared)
    summaries = [mismatch_summary(compared, prior, h) for h in (5, 10)]
    old_status = ("OLD_OOF_EXACT_REPRODUCTION_PASS" if all(
        x["countsAbove"]["1e-10"] == 0 for x in summaries) else
        "OLD_OOF_EXACT_REPRODUCTION_FAIL")
    snapshot("OLD_OOF_COMPARISON.json", {
       "schema": "phase57-prr-v2-old-oof-comparison-v1", "status": old_status,
       "previousClosureStatusUnchanged": "RANK_REPRODUCTION_FAIL",
       "headSummary": summaries, "mismatchRowsN": 3228,
       "mismatchRowsSha256": d.sha_file(OUT / "MISMATCH_ROWS.jsonl.gz")})
    if not stable:
        print(json.dumps({"status": "CANONICAL_ROUTE_REPRODUCTION_FAIL",
                          "routeMismatchN": mismatch_n, "oldOof": old_status}))
        return
    d.gzwrite("CANONICAL_OOF.jsonl.gz", a)
    routes = [{k: r[k] for k in ("arm", "entryId", "session", "fold",
              "score5", "score10", "medianTrain5", "medianTrain10",
              "low5", "low10", "routeDecision")} for r in a]
    d.gzwrite("ROUTE_DECISIONS.jsonl.gz", routes)
    freeze = json.loads((OUT / "CANONICAL_ENVIRONMENT.json").read_text())
    frozen = {"schema": "phase57-prr-v2-canonical-oof-freeze-v1",
      "environmentSha256": freeze["selectedEnvironmentSha256"],
      "passAFitReceiptSha256": d.sha_file(OUT / "CANONICAL_PASS_A_FIT.json"),
      "passBFitReceiptSha256": d.sha_file(OUT / "CANONICAL_PASS_B_FIT.json"),
      "canonicalOofSha256": d.sha_file(OUT / "CANONICAL_OOF.jsonl.gz"),
      "routeDecisionsSha256": d.sha_file(OUT / "ROUTE_DECISIONS.jsonl.gz"),
      "oldOofComparisonStatus": old_status, "fitAttempts": 14,
      "routeMismatchN": 0, "economicOutcomesInspected": False}
    snapshot("CANONICAL_OOF_FREEZE.json", frozen)
    (OUT / "CANONICAL_OOF_FREEZE.sha256").write_text(
        d.sha_file(OUT / "CANONICAL_OOF_FREEZE.json") +
        "  CANONICAL_OOF_FREEZE.json\n")
    print(json.dumps({"status": "CANONICAL_ROUTE_REPRODUCTION_PASS",
          "routeN": dict(collections.Counter(r["routeDecision"] for r in routes)),
          "oldOof": old_status,
          "freezeSha256": d.sha_file(OUT / "CANONICAL_OOF_FREEZE.json")}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass-name", choices=("A", "B"))
    ap.add_argument("--compare", action="store_true")
    args = ap.parse_args()
    d.require(bool(args.pass_name) != args.compare, "MODE")
    if args.compare:
        compare()
    else:
        pass_run(args.pass_name)
