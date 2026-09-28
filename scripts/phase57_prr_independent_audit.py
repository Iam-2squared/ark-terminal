"""Independent PRR receipt checks, deliberately not importing PRR implementation."""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "docs/evidence/phase57-potential-rank-routed-exit"
A = ROOT / "docs/evidence/phase57-checkpoint-certified-guard-exit"
PRE = "809c75a42a8c4538fd198091aa23bd77ff28b693aa2ce4279a3aa2baeda0e20a"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def gzrows(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(s) for s in f]


def check(ok, issue):
    if not ok:
        raise AssertionError(issue)


def audit():
    check(digest(E / "CYCLE_PRECOMMIT.json") == PRE, "PRECOMMIT")
    rank = json.loads((E / "RANK_REPRODUCTION.json").read_text())
    feasibility = json.loads((E / "ROUTE_FEASIBILITY.json").read_text())
    rr = gzrows(E / "ROUTE_DECISIONS.jsonl.gz")
    old = gzrows(A / "POTENTIAL_OOF.jsonl.gz")
    ids = [(r["arm"], r["entryId"]) for r in rr]
    prev = {(r["arm"], r["entryId"]): r for r in old}
    check(len(ids) == len(set(ids)) == len(prev) == 1614 and set(ids) == set(prev), "OOF_IDS")
    check(digest(A / "POTENTIAL_OOF.jsonl.gz") ==
          "e51a7fe46806231b826af59028eb1a14184786c43554258fe8fc7524498caabd",
          "OOF_SOURCE_SHA")
    check(rank["estimatorFitsAttempted"] == 6 and
          [f["fold"] for f in rank["folds"]] == [3, 4, 5], "FIT_TOPOLOGY")
    gates = {}
    for r in rr:
        old_r = prev[(r["arm"], r["entryId"])]
        check(abs(old_r["teacherUpsidePct"] - r["teacherUpsidePct"]) <= 1e-12,
              "TEACHER_ROW")
        check(old_r["featureRow"] == r["featureRow"] and
              old_r["session"] == r["session"], "FEATURE_ROW")
        for h in (5, 10):
            check(abs(r[f"probability{h}DiagnosticOnly"] - old_r[f"probability{h}"])
                  <= 1e-10, "SAVED_OOF_PROB")
            check(r[f"low{h}"] == (r[f"score{h}"] < r[f"medianTrain{h}"]),
                  "STRICT_TRAIN_MEDIAN")
        expected = ("DEFENSIVE_ELIGIBLE" if r["low5"] and r["low10"]
                    else "CONTROL_DEFAULT")
        check(r["routeDecision"] == expected, "AND_ROUTE")
    route_counts = {a: dict(Counter(r["routeDecision"] for r in rr if
                    r["arm"] == a)) for a in ("IM", "R1")}
    check(sum(route_counts["IM"].values()) == 819 and
          sum(route_counts["R1"].values()) == 795, "ROUTE_CENSUS")
    gates["rank"] = "PASS"
    gates["route"] = feasibility["status"]
    receipt = {"schema": "phase57-prr-independent-audit-v1",
               "precommitSha256": PRE, "rankRowIdentity": "PASS",
               "rawScoreMedianAndRule": "PASS", "fitCount": 6,
               "routeCounts": route_counts, "gates": gates,
               "previousProbabilitySkill": {"5": "POTENTIAL_SKILL_FAIL",
                                             "10": "POTENTIAL_SKILL_FAIL"}}
    if (E / "LAYER_A_RESULT.json").exists():
        primary = json.loads((E / "LAYER_A_RESULT.json").read_text())
        all_result = json.loads((E / "ALL_ENTRY_RESULT.json").read_text())
        joined = gzrows(E / "LAYER_A_ENTRY_ROWS.jsonl.gz")
        check(len(joined) == 1614, "JOIN_COUNT")
        d = {(r["arm"], r["entryId"]): r["routeDecision"] for r in rr}
        check(all(x["routeDecision"] == d[(x["arm"], x["entryId"])]
                  for x in joined), "JOIN_ROUTE")
        primary_rows = [x for x in joined if x["primary"]]
        check(len(primary_rows) == 111, "FUNDED_COUNT")
        exact = {}
        for arm in ("IM", "R1"):
            for h in (5, 10):
                subset = [x for x in primary_rows if x["arm"] == arm
                          and x["postEntryUpsidePct"] >= h]
                known = [x for x in subset if x["controlPnlJpy"] is not None and
                         x["routedPnlJpy"] is not None]
                delta = sum((Decimal(x["routedPnlJpy"]) -
                             Decimal(x["controlPnlJpy"]) for x in known), Decimal(0))
                reported = primary["winner"][f"{arm}>={h}"]
                check(len(known) == reported["knownPairedN"] and
                      delta == Decimal(reported["pairedDeltaJpy"]), "WINNER_R34")
                exact[f"{arm}>={h}"] = {"entryN": len(subset),
                                      "knownPairedN": len(known),
                                      "deltaJpy": str(delta)}
            subset = [x for x in primary_rows if x["arm"] == arm and
                      x["routeDecision"] == "DEFENSIVE_ELIGIBLE"]
            known = [x for x in subset if x["controlPnlJpy"] is not None and
                     x["routedPnlJpy"] is not None]
            delta = sum((Decimal(x["routedPnlJpy"]) -
                         Decimal(x["controlPnlJpy"]) for x in known), Decimal(0))
            check(delta == Decimal(primary["defensiveRoute"][arm]["pairedDeltaJpy"]),
                  "DEFENSIVE_R34")
            exact[f"{arm}:defensive"] = {"entryN": len(subset),
                                         "knownPairedN": len(known),
                                         "deltaJpy": str(delta)}
        check(all_result["byArm"]["IM"]["entryN"] == 819 and
              all_result["byArm"]["R1"]["entryN"] == 795, "ALL_ENTRY")
        standalone = gzrows(E / "ALL_ENTRY_ENTRY_ROWS.jsonl.gz")
        check(len(standalone) == 1614 and all(x["quantity"] == 100 for x in standalone),
              "STANDALONE_100_SHARE")
        for x in standalone:
            price = x["ccmgExitPrice"] if x["routeDecision"] == "DEFENSIVE_ELIGIBLE" else x["controlExitPrice"]
            independent = (None if price is None else
                           Decimal(str(price)) * 100 * Decimal("0.9995") -
                           Decimal(str(x["entryPrice"])) * 100)
            check((independent is None and x["routedPnlJpy"] is None) or
                  (independent is not None and independent == Decimal(x["routedPnlJpy"])),
                  "STANDALONE_SELL_COST")
        for arm in ("IM", "R1"):
            for h in (5, 10):
                cohort = [x for x in standalone if x["arm"] == arm and
                          x["postEntryUpsidePct"] >= h and x["pairedDeltaJpy"] is not None]
                value = sum((Decimal(x["pairedDeltaJpy"]) for x in cohort), Decimal(0))
                reported = all_result["winner"][f"{arm}>={h}"]
                check(value == Decimal(reported["pairedDeltaJpy"]) and
                      len(cohort) == reported["knownPairedN"], "STANDALONE_WINNER")
        receipt["exactPrimary"] = exact
        receipt["allEntry100Share"] = "PASS"
        receipt["gates"]["layerA"] = primary["gates"]
        receipt["gates"]["allEntry"] = [all_result["winnerGate"],
                                         all_result["defensiveValueGate"]]
    receipt["status"] = "PASS"
    (E / "INDEPENDENT_AUDIT.json").write_text(
        json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                   allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "gates": receipt["gates"]}))


if __name__ == "__main__":
    audit()
