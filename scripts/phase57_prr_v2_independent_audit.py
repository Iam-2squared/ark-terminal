"""Independent fixed-route and R34 economic audit; no estimator or replay calls."""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "docs/evidence/phase57-prr-numerical-recovery"
SOURCE = ROOT / "inputs/prr-prior/phase57-checkpoint-certified-guard-exit/LAYER_A_ENTRY_ROWS.jsonl.gz"
SOURCE_HASH = "3d6a3b7494b9fc4cabe686fe998e44a470324c1be7c1e7156779ad6bd60ff8f1"
ZERO = Decimal(0)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with gzip.open(path, "rt") as stream:
        for line in stream:
            yield json.loads(line)


def exact(condition, text):
    if not condition:
        raise AssertionError(text)


def independent_reprice(row, use_ccmg):
    price = row["candidateExitPrice"] if use_ccmg else row["controlExitPrice"]
    if price is None:
        return None
    proceeds = Decimal(str(price)) * Decimal(100) * Decimal("0.9995")
    paid = Decimal(str(row["entryPrice"])) * Decimal(100)
    return proceeds - paid


def paired_delta(source_rows, route_by_key, arm, primary_only, minimum=None,
                 defensive_only=False, upside_lt5=False):
    population = [r for r in source_rows if r["arm"] == arm and
                  (not primary_only or r["primary"]) and
                  (minimum is None or r["postEntryUpsidePct"] >= minimum) and
                  (not upside_lt5 or r["postEntryUpsidePct"] < 5) and
                  (not defensive_only or route_by_key[(arm, r["entryId"])][
                      "routeDecision"] == "DEFENSIVE_ELIGIBLE")]
    amounts = []
    for r in population:
        route = route_by_key[(arm, r["entryId"])]["routeDecision"]
        if primary_only:
            control = None if r["controlPnlJpy"] is None else Decimal(str(r["controlPnlJpy"]))
            chosen = r["candidatePnlJpy"] if route == "DEFENSIVE_ELIGIBLE" else r["controlPnlJpy"]
            chosen = None if chosen is None else Decimal(str(chosen))
        else:
            control = independent_reprice(r, False)
            chosen = independent_reprice(r, route == "DEFENSIVE_ELIGIBLE")
        if control is not None and chosen is not None:
            amounts.append(chosen - control)
    return {"entryN": len(population), "knownPairedN": len(amounts),
            "defensiveN": sum(route_by_key[(arm, r["entryId"])]["routeDecision"] ==
                              "DEFENSIVE_ELIGIBLE" for r in population),
            "pairedDeltaJpy": str(sum(amounts, ZERO))}


def main():
    freeze = json.loads((E / "CANONICAL_OOF_FREEZE.json").read_text())
    stability = json.loads((E / "ROUTE_STABILITY.json").read_text())
    fit = json.loads((E / "FIT_ATTEMPTS.json").read_text())
    a = json.loads((E / "CANONICAL_PASS_A_FIT.json").read_text())
    b = json.loads((E / "CANONICAL_PASS_B_FIT.json").read_text())
    route_rows = list(rows(E / "ROUTE_DECISIONS.jsonl.gz"))
    oof_rows = list(rows(E / "CANONICAL_OOF.jsonl.gz"))
    source_rows = list(rows(SOURCE))
    primary = json.loads((E / "LAYER_A_RESULT.json").read_text())
    broad = json.loads((E / "ALL_ENTRY_RESULT.json").read_text())

    exact(sha(SOURCE) == SOURCE_HASH, "archived R34 source hash")
    for filename, key in (("CANONICAL_OOF.jsonl.gz", "canonicalOofSha256"),
                          ("ROUTE_DECISIONS.jsonl.gz", "routeDecisionsSha256"),
                          ("CANONICAL_PASS_A_FIT.json", "passAFitReceiptSha256"),
                          ("CANONICAL_PASS_B_FIT.json", "passBFitReceiptSha256")):
        exact(sha(E / filename) == freeze[key], "frozen hash " + filename)
    exact(stability["status"] == "CANONICAL_ROUTE_REPRODUCTION_PASS" and
          stability["routeMismatchN"] == 0, "stability receipt")
    exact(fit["totalAttempted"] == 14 and len(fit["canonical"]) == 12,
          "estimator attempt budget")
    exact(len(a["models"]) == len(b["models"]) == 6, "model census")
    models = {(m["fold"], m["head"]): m for m in a["models"]}
    other = {(m["fold"], m["head"]): m for m in b["models"]}
    for key in models:
        m, n = models[key], other[key]
        exact(m["preprocessing"] == n["preprocessing"] and
              m["coefSha256"] == n["coefSha256"] and
              m["interceptSha256"] == n["interceptSha256"] and
              m["trainScoreSha256"] == n["trainScoreSha256"] and
              m["testScoreSha256"] == n["testScoreSha256"] and
              m["trainMedianScore"] == n["trainMedianScore"],
              "independent model hash/median pair " + str(key))
    exact(len(route_rows) == len(oof_rows) == len(source_rows) == 1614,
          "entry census")
    route_by_key = {(r["arm"], r["entryId"]): r for r in route_rows}
    source_by_key = {(r["arm"], r["entryId"]): r for r in source_rows}
    exact(len(route_by_key) == len(source_by_key) == 1614, "distinct entry IDs")
    for r in oof_rows:
        key = (r["arm"], r["entryId"])
        q = route_by_key[key]
        exact(r["fold"] == q["fold"] and r["session"] == q["session"] ==
              source_by_key[key]["session"], "fold/session identity")
        flags = []
        for head in (5, 10):
            score = q[f"score{head}"]
            median = models[(q["fold"], head)]["trainMedianScore"]
            exact(score == r[f"score{head}"] and median == q[f"medianTrain{head}"],
                  "score/median identity")
            flags.append(score < median)
            exact(flags[-1] == q[f"low{head}"], "strict train median routing")
        derived = "DEFENSIVE_ELIGIBLE" if all(flags) else "CONTROL_DEFAULT"
        exact(q["routeDecision"] == derived, "independent route conjunction")
    counts = {arm: dict(Counter(r["routeDecision"] for r in route_rows
                                if r["arm"] == arm)) for arm in ("IM", "R1")}
    checks = {}
    for population, report in (("primary", primary), ("allEntry", broad)):
        for arm in ("IM", "R1"):
            for head in (None, 5, 10):
                independent = paired_delta(source_rows, route_by_key, arm,
                                           population == "primary", head)
                reported = (report["perArmOverall" if population == "primary"
                                   else "byArm"][arm] if head is None else
                            report["winner"][f"{arm}>={head}"])
                label = f"{population}:{arm}:{'overall' if head is None else '>='+str(head)}"
                exact(independent["entryN"] == reported["entryN"] and
                      independent["knownPairedN"] == reported["knownPairedN"] and
                      independent["defensiveN"] == reported["defensiveRouteN"] and
                      Decimal(independent["pairedDeltaJpy"]) ==
                      Decimal(reported["pairedDeltaJpy"]), "independent PnL " + label)
                checks[label] = independent
            for key, opts in (("defensiveRoute", {"defensive_only": True}),
                              ("lowUpsideLt5", {"upside_lt5": True})):
                independent = paired_delta(source_rows, route_by_key, arm,
                                           population == "primary", **opts)
                reported = report[key][arm]
                label = f"{population}:{arm}:{key}"
                exact(independent["entryN"] == reported["entryN"] and
                      independent["knownPairedN"] == reported["knownPairedN"] and
                      Decimal(independent["pairedDeltaJpy"]) ==
                      Decimal(reported["pairedDeltaJpy"]), "independent PnL " + label)
                checks[label] = independent
    exact(Decimal(checks["allEntry:R1:>=5"]["pairedDeltaJpy"]) < 0 and
          Decimal(checks["allEntry:R1:>=10"]["pairedDeltaJpy"]) < 0,
          "winner hard failure")
    exact(broad["winnerGate"] == "ALL_ENTRY_WINNER_REGRESSION" and
          broad["defensiveValueGate"] == "ALL_ENTRY_DEFENSIVE_VALUE_FAIL",
          "hard gate statuses")
    output = {"schema": "phase57-prr-v2-independent-audit-v1", "status": "PASS",
        "sourceAndEnvironmentHash": {"archiveR34": sha(SOURCE),
            "canonicalEnvironment": freeze["environmentSha256"],
            "canonicalOof": freeze["canonicalOofSha256"],
            "routeDecisions": freeze["routeDecisionsSha256"]},
        "independentRouteN": counts, "folds": [3, 4, 5],
        "modelAndPreprocessingHashesVerified": 6,
        "strictTrainMedianRoutesVerified": 1614,
        "economicChecks": checks, "estimatorFitAttempts": 14,
        "integratedReplayInvocations": 0,
        "allEntryGate": [broad["winnerGate"], broad["defensiveValueGate"]],
        "selection": None, "adaptiveDevelopmentOnly": True,
        "productionReady": False, "providerRequests": 0,
        "restrictedPartitionsOpened": 0, "orders": 0, "mainMerges": 0}
    (E / "INDEPENDENT_AUDIT.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "routeN": counts,
                      "allEntryGate": output["allEntryGate"]}))


if __name__ == "__main__":
    main()
