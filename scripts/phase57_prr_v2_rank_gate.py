"""Precommitted rank-signal and median-route feasibility after OOF freeze."""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import (average_precision_score, brier_score_loss, log_loss,
                             roc_auc_score)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/phase57-prr-numerical-recovery"


def require(ok, why):
    if not ok:
        raise AssertionError(why)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_gz(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]


def save(name, x):
    (OUT / name).write_text(json.dumps(x, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False, allow_nan=False) + "\n")


def auc(rows, head):
    y = [int(r["teacherUpsidePctEvaluatorOnly"] >= head) for r in rows]
    if len(set(y)) != 2:
        return None
    return float(roc_auc_score(y, [r[f"score{head}"] for r in rows]))


def rank_bootstrap(rows, head):
    sessions = sorted({r["session"] for r in rows})
    by = {s: [r for r in rows if r["session"] == s] for s in sessions}
    rng = np.random.default_rng(570931)
    vals = []
    for _ in range(1999):
        rs = [r for s in rng.choice(sessions, size=len(sessions)) for r in by[s]]
        v = auc(rs, head)
        if v is not None:
            vals.append(v)
    return {"requested": 1999, "valid": len(vals), "seed": 570931,
            "ci95": None if not vals else [float(np.quantile(vals, q))
                                           for q in (.025, .975)]}


def route_bootstrap(rows, arm, head):
    subset = [r for r in rows if r["arm"] == arm]
    sessions = sorted({r["session"] for r in subset})
    by = {s: [r for r in subset if r["session"] == s] for s in sessions}
    rng = np.random.default_rng(570930)
    values = []
    def rate(xs):
        return sum(r["teacherUpsidePctEvaluatorOnly"] >= head for r in xs) / len(xs)
    for _ in range(1999):
        sample = [r for s in rng.choice(sessions, size=len(sessions)) for r in by[s]]
        lo = [r for r in sample if r["routeDecision"] == "DEFENSIVE_ELIGIBLE"]
        hi = [r for r in sample if r["routeDecision"] == "CONTROL_DEFAULT"]
        if lo and hi:
            values.append(rate(lo) - rate(hi))
    lo = [r for r in subset if r["routeDecision"] == "DEFENSIVE_ELIGIBLE"]
    hi = [r for r in subset if r["routeDecision"] == "CONTROL_DEFAULT"]
    return {"arm": arm, "head": head, "defensiveN": len(lo),
            "defaultN": len(hi), "defensiveSessions": len({r["session"] for r in lo}),
            "defaultSessions": len({r["session"] for r in hi}),
            "defensiveRate": None if not lo else rate(lo),
            "defaultRate": None if not hi else rate(hi),
            "delta": None if not lo or not hi else rate(lo) - rate(hi),
            "bootstrap": {"seed": 570930, "requested": 1999, "valid": len(values),
                "ci95": None if not values else
                    [float(np.quantile(values, q)) for q in (.025, .975)]}}


def main():
    freeze = json.loads((OUT / "CANONICAL_OOF_FREEZE.json").read_text())
    stability = json.loads((OUT / "ROUTE_STABILITY.json").read_text())
    require(stability["status"] == "CANONICAL_ROUTE_REPRODUCTION_PASS",
            "ROUTE_STABILITY_HARD_GATE")
    require(sha(OUT / "CANONICAL_OOF.jsonl.gz") ==
            freeze["canonicalOofSha256"] and
            sha(OUT / "ROUTE_DECISIONS.jsonl.gz") ==
            freeze["routeDecisionsSha256"], "CANONICAL_FREEZE_DRIFT")
    rows = read_gz(OUT / "CANONICAL_OOF.jsonl.gz")
    routes = read_gz(OUT / "ROUTE_DECISIONS.jsonl.gz")
    require(len(rows) == len(routes) == 1614, "ROUTE_CENSUS")
    for r, x in zip(rows, routes):
        require((r["arm"], r["entryId"], r["fold"], r["routeDecision"]) ==
                (x["arm"], x["entryId"], x["fold"], x["routeDecision"]),
                "ROUTE_MAPPING")
    fit = json.loads((OUT / "CANONICAL_PASS_A_FIT.json").read_text())
    by_model = {(x["fold"], x["head"]): x for x in fit["models"]}
    for r in rows:
        for head in (5, 10):
            scores = np.sort(np.asarray(by_model[(r["fold"], head)]["trainScores"]))
            r[f"percentile{head}"] = float(np.searchsorted(
                scores, r[f"score{head}"], side="left") / len(scores))
    heads = {}
    for h in (5, 10):
        y = np.asarray([r["teacherUpsidePctEvaluatorOnly"] >= h for r in rows], dtype=int)
        p = np.asarray([r[f"probability{h}DiagnosticOnly"] for r in rows])
        bs = rank_bootstrap(rows, h)
        arms = {a: auc([r for r in rows if r["arm"] == a], h) for a in ("IM", "R1")}
        folds = {str(f): auc([r for r in rows if r["fold"] == f], h)
                 for f in (3, 4, 5)}
        passed = (bs["ci95"] is not None and bs["ci95"][0] > .5 and
                  all(v is not None and v > .5 for v in arms.values()) and
                  all(v is not None and v >= .5 for v in folds.values()))
        heads[str(h)] = {"n": len(rows), "positiveN": int(y.sum()),
            "auc": auc(rows, h), "bootstrap": bs,
            "prAuc": float(average_precision_score(y, p)),
            "brier": float(brier_score_loss(y, p)),
            "logLoss": float(log_loss(y, p)),
            "armAuc": arms, "foldAuc": folds,
            "status": "RANK_SIGNAL_PASS" if passed else "RANK_SIGNAL_FAIL"}
    rank_status = ("RANK_SIGNAL_PASS" if all(x["status"] == "RANK_SIGNAL_PASS"
                   for x in heads.values()) else "RANK_SIGNAL_FAIL")
    save("RANK_SIGNAL.json", {"schema": "phase57-prr-v2-rank-signal-v1",
        "status": rank_status, "heads": heads,
        "previousProbabilitySkill": {"5": "POTENTIAL_SKILL_FAIL",
                                     "10": "POTENTIAL_SKILL_FAIL"},
        "canonicalOofFreezeSha256": sha(OUT / "CANONICAL_OOF_FREEZE.json")})
    deciles, quadrants, sessions = {}, {}, {}
    def upside_bucket(p):
        return "<1" if p < 1 else "1-3" if p < 3 else "3-5" if p < 5 else (
            "5-10" if p < 10 else ">=10")
    for arm in ("IM", "R1", "combined"):
        subset = [r for r in rows if arm == "combined" or r["arm"] == arm]
        for h in (5, 10):
            for i in range(10):
                part = [r for r in subset if min(9, int(r[f"percentile{h}"] * 10)) == i]
                vals = [r["teacherUpsidePctEvaluatorOnly"] for r in part]
                deciles[f"{arm}:head{h}:{i}"] = {"n": len(part),
                    "sessions": len({r["session"] for r in part}),
                    "im": sum(r["arm"] == "IM" for r in part),
                    "r1": sum(r["arm"] == "R1" for r in part),
                    "actual5Rate": None if not part else sum(v >= 5 for v in vals) / len(vals),
                    "actual10Rate": None if not part else sum(v >= 10 for v in vals) / len(vals),
                    "medianUpsidePct": None if not part else float(np.median(vals)),
                    "meanUpsidePct": None if not part else float(np.mean(vals))}
        for low5 in (True, False):
            for low10 in (True, False):
                part = [r for r in subset if r["low5"] == low5 and r["low10"] == low10]
                quadrants[f"{arm}:{'LOW' if low5 else 'HIGH'}5:{'LOW' if low10 else 'HIGH'}10"] = {
                    "n": len(part), "sessions": len({r["session"] for r in part}),
                    "actual5": sum(r["teacherUpsidePctEvaluatorOnly"] >= 5 for r in part),
                    "actual10": sum(r["teacherUpsidePctEvaluatorOnly"] >= 10 for r in part),
                    "upsideBucket": dict(collections.Counter(
                        upside_bucket(r["teacherUpsidePctEvaluatorOnly"]) for r in part))}
    for arm in ("IM", "R1"):
        for s in sorted({r["session"] for r in rows if r["arm"] == arm}):
            part = [r for r in rows if r["arm"] == arm and r["session"] == s]
            lo = [r for r in part if r["routeDecision"] == "DEFENSIVE_ELIGIBLE"]
            hi = [r for r in part if r["routeDecision"] == "CONTROL_DEFAULT"]
            sessions[f"{arm}:{s}"] = {"n": len(part), "defensiveN": len(lo),
                "defensiveShare": len(lo) / len(part),
                **{f"actual{h}{group}": None if not pp else
                   sum(r["teacherUpsidePctEvaluatorOnly"] >= h for r in pp) / len(pp)
                   for h in (5, 10) for group, pp in
                   (("Defensive", lo), ("Default", hi))}}
    save("RANK_ANATOMY.json", {"schema": "phase57-prr-v2-rank-anatomy-v1",
        "deciles": deciles, "quadrants": quadrants, "bySession": sessions,
        "descriptiveOnly": True})
    sep = [route_bootstrap(rows, arm, h) for arm in ("IM", "R1") for h in (5, 10)]
    support = all(x["defensiveN"] >= 50 and x["defensiveSessions"] >= 12 for x in sep)
    direction = all(x["delta"] is not None and x["delta"] < 0 for x in sep)
    separation = all(x["bootstrap"]["ci95"] is not None and
                     x["bootstrap"]["ci95"][1] < 0 for x in sep)
    status = ("NOT_RUN_RANK_SIGNAL_FAIL" if rank_status != "RANK_SIGNAL_PASS" else
              "ROUTE_SUPPORT_NO_GO" if not support else
              "ROUTE_DIRECTION_NO_GO" if not direction else
              "ROUTE_SEPARATION_NO_GO" if not separation else
              "POTENTIAL_RANK_ROUTING_PASS")
    save("ROUTE_FEASIBILITY.json", {
        "schema": "phase57-prr-v2-route-feasibility-v1", "status": status,
        "rankSignalStatus": rank_status, "supportPass": support,
        "directionPass": direction, "separationPass": separation,
        "perArmHead": sep, "candidate": "PRR_CCMG_M50_AND_V2_CANONICAL"})
    print(json.dumps({"rankSignal": rank_status, "routeFeasibility": status,
        "routeN": dict(collections.Counter(r["routeDecision"] for r in rows))}))


if __name__ == "__main__":
    main()
