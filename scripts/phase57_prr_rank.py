"""Phase57 PRR: frozen OOF rank reproduction and one precommitted Entry route.

Development-only evaluator. It does not trade, acquire market data, refit in a
replay, choose a threshold from results, or confer probability authority.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/phase57-potential-rank-routed-exit"
PRIOR = ROOT / "docs/evidence/phase57-checkpoint-certified-guard-exit"
PREFIT = ROOT / "artifacts/all-material-r1/prefit"
FEATURE_SHA = "54bf771f6a090eb3e8035f7ee433ca1fbd617c165d77955ab71054b4e259a3fe"
PRECOMMIT_SHA = "809c75a42a8c4538fd198091aa23bd77ff28b693aa2ce4279a3aa2baeda0e20a"
PINS = {
    "POTENTIAL_OOF.jsonl.gz": "e51a7fe46806231b826af59028eb1a14184786c43554258fe8fc7524498caabd",
    "POTENTIAL_TEACHER_ROWS.jsonl.gz": "c6fa75eb3d3abfc65ebe56ee5fe219f8c8154221c7fe79f610d6904dab691057",
    "POTENTIAL_FIT_PROTOCOL.json": "80fc1699457dfa725e032548f643241359468e0243ddc2671d4d0894d562e9bd",
    "POTENTIAL_RESULT.json": "e62463b8ffbc0ee606b5e057398903751f926aa41b1a4e9bcdf71088f4ef801b",
    "LAYER_A_ENTRY_ROWS.jsonl.gz": "3d6a3b7494b9fc4cabe686fe998e44a470324c1be7c1e7156779ad6bd60ff8f1",
    "CHECKPOINT_ENTRY_SUMMARY.jsonl.gz": "face5c4d0fee8a6b916db42084d35992e6951c0732945e7a2bd422bdbc2c2b20",
}
PREFIT_PINS = {
    "features.npy": FEATURE_SHA,
    "rows.json": "54f7dbb8bd0c9f8974ccccb7a949c0b7ebf0bbe46581be7778f1607f9d9d8cb6",
    "folds.json": "3342c68cc8a1987e11dda6f6c07757a47ff43d1e7f7f1506cb2e1ca0b3b41021",
    "feature-names.json": "57040ed4cb0cc008c3b2b33b32ae71d721c755a2e8a3ffa0455941c83bbd4275",
}
SAFETY = dict.fromkeys(
    ("executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
     "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
     "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted"), False)


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def encoded(x):
    return (json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                       allow_nan=False) + "\n").encode()


def write(name, data):
    (OUT / name).write_bytes(encoded(data))


def read_gz(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]


def gzip_rows(name, rows):
    (OUT / name).write_bytes(gzip.compress(b"".join(encoded(x) for x in rows), mtime=0))


def low(score, train_median):
    """Strictly below TRAIN median; a tie is Control."""
    return bool(score < train_median)


def route(low5, low10):
    return "DEFENSIVE_ELIGIBLE" if low5 and low10 else "CONTROL_DEFAULT"


def percentile(score, sorted_train_scores):
    return float(np.searchsorted(sorted_train_scores, score, side="left") /
                 len(sorted_train_scores))


def bucket(upside):
    if upside < 1:
        return "<1"
    if upside < 3:
        return "1-3"
    if upside < 5:
        return "3-5"
    if upside < 10:
        return "5-10"
    return ">=10"


def preflight():
    require(sha(OUT / "CYCLE_PRECOMMIT.json") == PRECOMMIT_SHA, "PRECOMMIT_DRIFT")
    for name, digest in PINS.items():
        require(sha(PRIOR / name) == digest, "SOURCE_DRIFT:" + name)
    for name, digest in PREFIT_PINS.items():
        require(sha(PREFIT / name) == digest, "PREFIT_LINEAGE_ABORT:" + name)
    protocol = json.loads((PRIOR / "POTENTIAL_FIT_PROTOCOL.json").read_text())
    require(protocol["model"] == {
        "heads": [5, 10], "family": "LogisticRegression", "penalty": "l2",
        "C": 1.0, "solver": "liblinear", "max_iter": 1000, "tol": .0001,
        "class_weight": None, "random_state": 570926}, "MODEL_LINEAGE_ABORT")
    require(protocol["preprocessing"].startswith("R1 frozen M1:"), "PREPROCESSING_LINEAGE_ABORT")


def reproduce():
    """Fit exactly the six relevant OOF models, collecting TRAIN medians."""
    from scripts import phase57_entry_all_material_r1_train as frozen

    preflight()
    observed = read_gz(PRIOR / "POTENTIAL_TEACHER_ROWS.jsonl.gz")
    saved = read_gz(PRIOR / "POTENTIAL_OOF.jsonl.gz")
    prior = {(x["arm"], x["entryId"]): x for x in saved}
    require(len(prior) == len(saved) == 1614, "PRIOR_OOF_IDENTITY_ABORT")
    folds = json.loads((PREFIT / "folds.json").read_text())
    require(len(folds) == 5, "FOLD_LINEAGE_ABORT")
    X = np.load(PREFIT / "features.npy", mmap_mode="r")
    require(X.shape == (149900, 566), "FEATURE_SHAPE_ABORT")
    rows = [x for x in observed if x["teacherUpsidePct"] is not None]
    result = []
    fit_receipts = []
    fits_attempted = 0
    for fold in folds:
        train_sessions = set(fold["train"])
        test_sessions = set(fold["test"])
        train = [x for x in rows if x["session"] in train_sessions]
        test = [x for x in rows if x["session"] in test_sessions and x["pinnedTest"]]
        if not test:
            continue
        require(fold["id"] in (3, 4, 5), "RANK_REPRODUCTION_LINEAGE_ABORT:extra_fold")
        require(not train_sessions & test_sessions, "TEMPORAL_LEAK_ABORT")
        train_x = np.asarray(X[[x["featureRow"] for x in train]])
        test_x = np.asarray(X[[x["featureRow"] for x in test]])
        pp = frozen.fit_preprocessor(train_x)
        xt = frozen.transform(train_x, pp)
        xv = frozen.transform(test_x, pp)
        heads = {}
        for h in (5, 10):
            y = np.asarray([x["teacherUpsidePct"] >= h for x in train], dtype=int)
            require(len(np.unique(y)) == 2, "UNTRAINABLE_FOLD")
            require(fits_attempted < 6, "FIT_BUDGET_ABORT")
            fits_attempted += 1  # Failed attempts still consume the budget.
            model = LogisticRegression(penalty="l2", C=1., solver="liblinear",
                                       max_iter=1000, tol=.0001, class_weight=None,
                                       random_state=570926)
            model.fit(xt, y)
            train_scores = np.sort(model.decision_function(xt))
            test_scores = model.decision_function(xv)
            test_prob = model.predict_proba(xv)[:, 1]
            heads[h] = (train_scores, test_scores, test_prob)
        for i, x in enumerate(test):
            key = (x["arm"], x["entryId"])
            require(key in prior, "RANK_ROUTE_INTEGRITY_ABORT:unknown_id")
            old = prior[key]
            require(old["featureRow"] == x["featureRow"] and
                    old["session"] == x["session"] and
                    old["pinnedTest"] and
                    abs(old["teacherUpsidePct"] - x["teacherUpsidePct"]) <= 1e-12,
                    "RANK_REPRODUCTION_FAIL:label_or_feature")
            data = {"arm": x["arm"], "entryId": x["entryId"], "session": x["session"],
                    "featureRow": x["featureRow"], "fold": fold["id"],
                    "teacherUpsidePct": x["teacherUpsidePct"]}
            for h in (5, 10):
                scores, tests, probs = heads[h]
                sc, p = float(tests[i]), float(probs[i])
                require(abs(p - old[f"probability{h}"]) <= 1e-10,
                        "RANK_REPRODUCTION_FAIL:probability")
                require(np.isfinite(sc) and np.isfinite(p), "RANK_ROUTE_INTEGRITY_ABORT:nonfinite")
                data[f"score{h}"] = sc
                data[f"medianTrain{h}"] = float(np.median(scores))
                data[f"low{h}"] = low(sc, data[f"medianTrain{h}"])
                data[f"percentile{h}"] = percentile(sc, scores)
                data[f"probability{h}DiagnosticOnly"] = p
                data[f"previousProbability{h}DiagnosticOnly"] = old[f"probability{h}"]
            data["routeDecision"] = route(data["low5"], data["low10"])
            result.append(data)
        fit_receipts.append({"fold": fold["id"], "trainEntries": len(train),
                             "testEntries": len(test), "trainLastSession": max(train_sessions),
                             "testFirstSession": min(test_sessions), "fits": 2})
    result.sort(key=lambda x: (x["arm"], x["entryId"]))
    require(len(result) == 1614 and len({(x["arm"], x["entryId"]) for x in result}) == 1614
            and set(prior) == {(x["arm"], x["entryId"]) for x in result},
            "RANK_ROUTE_INTEGRITY_ABORT:missing_oof")
    require(fits_attempted == 6 and [x["fold"] for x in fit_receipts] == [3, 4, 5] and
            [x["trainEntries"] for x in fit_receipts] == [1522, 2287, 3028] and
            [x["testEntries"] for x in fit_receipts] == [114, 758, 742],
            "RANK_REPRODUCTION_LINEAGE_ABORT:fit_topology")
    previous = json.loads((PRIOR / "POTENTIAL_RESULT.json").read_text())
    for h in (5, 10):
        actual_auc = roc_auc_score([r["teacherUpsidePct"] >= h for r in result],
                                   [r[f"score{h}"] for r in result])
        require(abs(actual_auc - previous["heads"][str(h)]["auc"]) <= 1e-12,
                "RANK_REPRODUCTION_FAIL:AUC")
        by_score = sorted(result, key=lambda x: x[f"score{h}"])
        require(all(a[f"probability{h}DiagnosticOnly"] <= b[f"probability{h}DiagnosticOnly"] + 1e-12
                    for a, b in zip(by_score, by_score[1:])),
                "RANK_REPRODUCTION_FAIL:score_order")
    rep = {"schema": "phase57-prr-rank-reproduction-v1",
           "status": "RANK_REPRODUCTION_PASS",
           "precommitSha256": PRECOMMIT_SHA,
           "frozenFeatureSha256": sha(PREFIT / "features.npy"),
           "savedOofSha256": sha(PRIOR / "POTENTIAL_OOF.jsonl.gz"),
           "entryIdsIdentical": True, "folds": fit_receipts,
           "estimatorFitsAttempted": fits_attempted, "estimatorFitsMax": 6,
           "innerFits": 0, "calibrationFits": 0,
           "maxSavedProbabilityAbsDiff": {str(h): max(abs(r[f"probability{h}DiagnosticOnly"] -
                  r[f"previousProbability{h}DiagnosticOnly"]) for r in result) for h in (5, 10)},
           "auc": {str(h): roc_auc_score([r["teacherUpsidePct"] >= h for r in result],
                 [r[f"score{h}"] for r in result]) for h in (5, 10)},
           "previousProbabilitySkill": {"5": "POTENTIAL_SKILL_FAIL",
                                         "10": "POTENTIAL_SKILL_FAIL"},
           "safety": SAFETY, "providerRequests": 0, "restrictedPartitionsOpened": 0}
    write("RANK_REPRODUCTION.json", rep)
    gzip_rows("ROUTE_DECISIONS.jsonl.gz", result)
    return result


def separation(rows, arm, h):
    subset = [r for r in rows if r["arm"] == arm]
    defensive = [r for r in subset if r["routeDecision"] == "DEFENSIVE_ELIGIBLE"]
    default = [r for r in subset if r["routeDecision"] == "CONTROL_DEFAULT"]
    rate = lambda rr: sum(r["teacherUpsidePct"] >= h for r in rr) / len(rr) if rr else None
    d, c = rate(defensive), rate(default)
    sessions = sorted({r["session"] for r in subset})
    by_session = {s: [r for r in subset if r["session"] == s] for s in sessions}
    rng = np.random.default_rng(570930)
    samples = []
    for _ in range(1999):
        replicated = [r for s in rng.choice(sessions, size=len(sessions))
                      for r in by_session[s]]
        lo = [r for r in replicated if r["routeDecision"] == "DEFENSIVE_ELIGIBLE"]
        hi = [r for r in replicated if r["routeDecision"] == "CONTROL_DEFAULT"]
        if lo and hi:
            samples.append(rate(lo) - rate(hi))
    ci = [float(np.quantile(samples, q)) for q in (.025, .975)] if samples else [None, None]
    return {"arm": arm, "head": h, "defensiveN": len(defensive), "defaultN": len(default),
            "defensiveSessions": len({r["session"] for r in defensive}),
            "defaultSessions": len({r["session"] for r in default}),
            "defensiveRate": d, "defaultRate": c,
            "delta": None if d is None or c is None else d - c,
            "bootstrap": {"seed": 570930, "resamples": 1999, "valid": len(samples),
                          "ci95": ci}}


def anatomy_and_gate(rows):
    deciles, quadrants = {}, {}
    for h in (5, 10):
        for arm in ("IM", "R1", "combined"):
            subset = [r for r in rows if arm == "combined" or r["arm"] == arm]
            for d in range(10):
                part = [r for r in subset if min(9, int(r[f"percentile{h}"] * 10)) == d]
                vals = [r["teacherUpsidePct"] for r in part]
                deciles[f"{arm}:head{h}:{d}"] = {
                    "n": len(part), "sessions": len({r["session"] for r in part}),
                    "im": sum(r["arm"] == "IM" for r in part),
                    "r1": sum(r["arm"] == "R1" for r in part),
                    "actual5Rate": None if not part else sum(v >= 5 for v in vals) / len(part),
                    "actual10Rate": None if not part else sum(v >= 10 for v in vals) / len(part),
                    "medianUpsidePct": None if not part else float(np.median(vals)),
                    "meanUpsidePct": None if not part else float(np.mean(vals))}
    for arm in ("IM", "R1", "combined"):
        subset = [r for r in rows if arm == "combined" or r["arm"] == arm]
        for a in (True, False):
            for b in (True, False):
                part = [r for r in subset if r["low5"] == a and r["low10"] == b]
                quadrants[f"{arm}:{'LOW' if a else 'HIGH'}5:{'LOW' if b else 'HIGH'}10"] = {
                    "n": len(part), "sessions": len({r["session"] for r in part}),
                    "actual5": sum(r["teacherUpsidePct"] >= 5 for r in part),
                    "actual10": sum(r["teacherUpsidePct"] >= 10 for r in part),
                    "upsideBucket": dict(collections.Counter(bucket(r["teacherUpsidePct"])
                                                              for r in part))}
    by_session = {}
    for arm in ("IM", "R1"):
        for session in sorted({r["session"] for r in rows if r["arm"] == arm}):
            part = [r for r in rows if r["arm"] == arm and r["session"] == session]
            lo = [r for r in part if r["routeDecision"] == "DEFENSIVE_ELIGIBLE"]
            hi = [r for r in part if r["routeDecision"] == "CONTROL_DEFAULT"]
            by_session[f"{arm}:{session}"] = {"n": len(part), "defensiveN": len(lo),
                "defensiveShare": len(lo) / len(part),
                **{f"actual{h}{group}": None if not pp else sum(r["teacherUpsidePct"] >= h
                   for r in pp) / len(pp) for h in (5, 10) for group, pp in
                   (("Defensive", lo), ("Default", hi))}}
    write("RANK_ANATOMY.json", {"schema": "phase57-prr-rank-anatomy-v1",
          "deciles": deciles, "quadrants": quadrants, "bySession": by_session,
          "descriptiveOnly": True, "routingRuleUnchanged": True})
    sep = [separation(rows, arm, h) for arm in ("IM", "R1") for h in (5, 10)]
    support = all(x["defensiveN"] >= 50 and x["defensiveSessions"] >= 12 for x in sep)
    direction = all(x["delta"] is not None and x["delta"] < 0 for x in sep)
    separated = all(x["bootstrap"]["ci95"][1] is not None and
                    x["bootstrap"]["ci95"][1] < 0 for x in sep)
    status = ("ROUTE_SUPPORT_NO_GO" if not support else
              "ROUTE_DIRECTION_NO_GO" if not direction else
              "ROUTE_SEPARATION_NO_GO" if not separated else
              "POTENTIAL_RANK_ROUTING_PASS")
    out = {"schema": "phase57-prr-route-feasibility-v1", "status": status,
           "supportPass": support, "directionPass": direction, "separationPass": separated,
           "perArmHead": sep, "candidate": "PRR_CCMG_M50_AND_V1",
           "noProbabilityCalibrationClaim": True, "precommitSha256": PRECOMMIT_SHA}
    write("ROUTE_FEASIBILITY.json", out)
    return status


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = reproduce()
    status = anatomy_and_gate(rows)
    print(json.dumps({"rankReproduction": "PASS", "routeFeasibility": status,
                      "routes": dict(collections.Counter((r["arm"], r["routeDecision"])
                                                         for r in rows))}, default=str))


if __name__ == "__main__":
    main()
