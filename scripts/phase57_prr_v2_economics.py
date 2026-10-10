"""Canonical V2 PRR route joined to archived R34 Control/CCMG outcomes.

This is a standalone, same-Entry accounting diagnostic, not Capital replay.
No frozen policy is reimplemented or altered here.
"""
from __future__ import annotations

import collections
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import numpy as np

from scripts import phase57_prr_v2_rank_gate as rank

ROOT = Path(__file__).resolve().parents[1]
OUT = rank.OUT
PRIOR = ROOT / "inputs/prr-prior/phase57-checkpoint-certified-guard-exit"
ARCHIVE_SHA = "3d6a3b7494b9fc4cabe686fe998e44a470324c1be7c1e7156779ad6bd60ff8f1"
SAFETY = {key: False for key in ("executionAllowed", "brokerWriteAllowed",
    "excelOrderWriteAllowed", "rssOrderFunctionAllowed", "liveTradingAllowed",
    "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed",
    "transmitted")}


def gzip_rows(name, rows):
    payload = b"".join((json.dumps(r, sort_keys=True, separators=(",", ":"),
                                  ensure_ascii=False, allow_nan=False) + "\n").encode()
                       for r in rows)
    (OUT / name).write_bytes(gzip.compress(payload, mtime=0))


def write(name, data):
    rank.save(name, data)


def read_rows(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]


def dec(x):
    return None if x is None else Decimal(str(x))


def pnl100(entry_price, exit_price):
    if exit_price is None:
        return None
    quantity = Decimal(100)
    return str(dec(exit_price) * quantity * Decimal("0.9995") -
               dec(entry_price) * quantity)


def metrics(rows):
    paired = [x for x in rows if x["controlPnlJpy"] is not None
              and x["routedPnlJpy"] is not None]
    ccmg_paired = [x for x in rows if x["controlPnlJpy"] is not None
                   and x["ccmgPnlJpy"] is not None]
    zero = Decimal(0)
    control = sum((dec(x["controlPnlJpy"]) for x in paired), zero)
    routed = sum((dec(x["routedPnlJpy"]) for x in paired), zero)
    ccmg = sum((dec(x["ccmgPnlJpy"]) for x in paired if x["ccmgPnlJpy"] is not None), zero)
    r54 = sum((dec(x["r54PnlJpy"]) for x in paired if x["r54PnlJpy"] is not None), zero)
    diffs = [dec(x["routedPnlJpy"]) - dec(x["controlPnlJpy"]) for x in paired]
    hold = [int(x["routedExitMinute"]) - int(x["entryMinute"]) for x in rows
            if x.get("routedExitMinute") is not None and
               x.get("entryMinute") is not None]
    return {"entryN": len(rows), "knownPairedN": len(paired),
            "knownCoverage": None if not rows else len(paired) / len(rows),
            "nullCandidateN": sum(x["routedPnlJpy"] is None for x in rows),
            "defensiveRouteN": sum(x["routeDecision"] == "DEFENSIVE_ELIGIBLE" for x in rows),
            "controlDefaultN": sum(x["routeDecision"] == "CONTROL_DEFAULT" for x in rows),
            "controlPnlJpy": str(control), "ccmgPnlJpy": str(ccmg),
            "r54PnlJpy": str(r54), "routedPnlJpy": str(routed),
            "ccmgKnownPairedN": len(ccmg_paired),
            "ccmgControlDeltaJpy": str(sum((dec(x["ccmgPnlJpy"]) -
                dec(x["controlPnlJpy"]) for x in ccmg_paired), zero)),
            "pairedDeltaJpy": str(routed - control),
            "controlMeanJpy": None if not paired else str(control / len(paired)),
            "routedMeanJpy": None if not paired else str(routed / len(paired)),
            "improveN": sum(x > 0 for x in diffs), "equalN": sum(x == 0 for x in diffs),
            "worseN": sum(x < 0 for x in diffs),
            "routedWinRate": None if not paired else sum(dec(x["routedPnlJpy"]) > 0 for x in paired) / len(paired),
            "candidateFirstSellN": sum(x["routeDecision"] == "DEFENSIVE_ELIGIBLE" and
                                       x["terminalReason"] == "CANDIDATE_FIRST" for x in rows),
            "medianObservedHoldMinutes": None if not hold else statistics.median(hold),
            "observedHoldN": len(hold),
            "exitReasonN": dict(collections.Counter(x.get("terminalReason") for x in rows)),
            "initialN": sum(x["initialOrReplacement"] == "Initial" for x in rows),
            "replacementN": sum(x["initialOrReplacement"] == "Replacement" for x in rows)}


def join():
    freeze = json.loads((OUT / "CANONICAL_OOF_FREEZE.json").read_text())
    rank.require(rank.sha(OUT / "CANONICAL_OOF.jsonl.gz") ==
                 freeze["canonicalOofSha256"], "CANONICAL_OOF_DRIFT")
    rank.require(json.loads((OUT / "ROUTE_STABILITY.json").read_text())["status"] ==
                 "CANONICAL_ROUTE_REPRODUCTION_PASS", "ROUTE_STABILITY_ABORT")
    rank.require(json.loads((OUT / "RANK_SIGNAL.json").read_text())["status"] ==
                 "RANK_SIGNAL_PASS", "RANK_GATE_ABORT")
    rank.require(json.loads((OUT / "ROUTE_FEASIBILITY.json").read_text())["status"] ==
                 "POTENTIAL_RANK_ROUTING_PASS", "ROUTE_GATE_ABORT")
    rank.require(rank.sha(PRIOR / "LAYER_A_ENTRY_ROWS.jsonl.gz") ==
                 ARCHIVE_SHA, "ARCHIVED_R34_DRIFT")
    routes = read_rows(OUT / "ROUTE_DECISIONS.jsonl.gz")
    oof = {(r["arm"], r["entryId"]): r for r in
           read_rows(OUT / "CANONICAL_OOF.jsonl.gz")}
    fit = json.loads((OUT / "CANONICAL_PASS_A_FIT.json").read_text())
    train_scores = {(m["fold"], m["head"]): np.sort(m["trainScores"])
                    for m in fit["models"]}
    source = read_rows(PRIOR / "LAYER_A_ENTRY_ROWS.jsonl.gz")
    by_id = {(x["arm"], x["entryId"]): x for x in source}
    rank.require(len(by_id) == len(source) == len(routes) == 1614,
                 "ROUTE_ARCHIVE_IDENTITY_ABORT")
    rows = []
    for r in routes:
        key = r["arm"], r["entryId"]
        rank.require(key in by_id, "ROUTE_ARCHIVE_MISSING_ENTRY")
        old = by_id[key]
        rank.require(old["session"] == r["session"] and
                     abs(old["postEntryUpsidePct"] -
                         oof[key]["teacherUpsidePctEvaluatorOnly"]) <= 1e-12,
                     "EVALUATOR_LABEL_IDENTITY_ABORT")
        defensive = r["routeDecision"] == "DEFENSIVE_ELIGIBLE"
        chosen = old["candidatePnlJpy"] if defensive else old["controlPnlJpy"]
        if not defensive:
            rank.require(chosen == old["controlPnlJpy"], "DEFAULT_CONTROL_IDENTITY_ABORT")
        rows.append({
            "arm": r["arm"], "entryId": r["entryId"], "session": r["session"],
            "fold": r["fold"], "routeDecision": r["routeDecision"],
            "rank5Decile": min(9, int(np.searchsorted(train_scores[(r["fold"], 5)],
                r["score5"], side="left") / len(train_scores[(r["fold"], 5)]) * 10)),
            "rank10Decile": min(9, int(np.searchsorted(train_scores[(r["fold"], 10)],
                r["score10"], side="left") / len(train_scores[(r["fold"], 10)]) * 10)),
            "postEntryUpsidePct": old["postEntryUpsidePct"], "bucket": old["bucket"],
            "entryMinute": old["entryMinute"], "entryPrice": old["entryPrice"],
            "primary": old["primary"],
            "quantity": old["quantity"], "initialOrReplacement": old["initialOrReplacement"],
            "controlPnlJpy": old["controlPnlJpy"],
            "ccmgPnlJpy": old["candidatePnlJpy"], "r54PnlJpy": old["r54PnlJpy"],
            "routedPnlJpy": chosen,
            "pairedDeltaJpy": None if chosen is None or old["controlPnlJpy"] is None
                              else str(dec(chosen) - dec(old["controlPnlJpy"])),
            "controlExitMinute": old["controlExitMinute"],
            "controlExitPrice": old["controlExitPrice"],
            "ccmgExitMinute": old["candidateExitMinute"],
            "ccmgExitPrice": old["candidateExitPrice"],
            "r54ExitPrice": old["r54ExitPrice"],
            "routedExitMinute": old["candidateExitMinute"] if defensive else old["controlExitMinute"],
            "terminalReason": old["terminalReason"] if defensive else "R50_CONTROL_DEFAULT",
            "fillStatus": old["fillStatus"] if defensive else
                          ("R50_CONTROL_CONFIRMED" if old["controlPnlJpy"] is not None
                           else "R50_CONTROL_NULL")})
    rows.sort(key=lambda x: (x["arm"], x["entryId"]))
    gzip_rows("LAYER_A_ENTRY_ROWS.jsonl.gz", rows)
    return rows


def winner_gate(rows, arm, h):
    xs = [r for r in rows if r["arm"] == arm and r["postEntryUpsidePct"] >= h]
    m = metrics(xs)
    m["defensiveWinnerN"] = sum(r["routeDecision"] == "DEFENSIVE_ELIGIBLE" for r in xs)
    m["defaultWinnerN"] = sum(r["routeDecision"] == "CONTROL_DEFAULT" for r in xs)
    m["defensiveRoutedLossJpy"] = str(sum((dec(r["pairedDeltaJpy"]) for r in xs
         if r["routeDecision"] == "DEFENSIVE_ELIGIBLE" and r["pairedDeltaJpy"] is not None),
         Decimal(0)))
    m["defaultExactEquality"] = all(r["pairedDeltaJpy"] == "0" or
                                    dec(r["pairedDeltaJpy"]) == 0 for r in xs
                                    if r["routeDecision"] == "CONTROL_DEFAULT")
    if m["knownCoverage"] is None or m["knownCoverage"] < .8:
        m["gate"] = "WINNER_GATE_UNMEASURABLE"
    elif (dec(m["routedMeanJpy"]) < dec(m["controlMeanJpy"]) or
          dec(m["pairedDeltaJpy"]) < 0):
        m["gate"] = "WINNER_PRESERVATION_FAIL"
    else:
        m["gate"] = "WINNER_PRESERVATION_PASS"
    return m


def summaries(rows):
    primary = [r for r in rows if r["primary"]]
    rank.require(len(primary) == 111 and
                 sum(r["arm"] == "IM" for r in primary) == 79 and
                 sum(r["arm"] == "R1" for r in primary) == 32, "PRIMARY_CENSUS_ABORT")
    overall = {arm: metrics([r for r in primary if r["arm"] == arm]) for arm in ("IM", "R1")}
    winners = {f"{arm}>={h}": winner_gate(primary, arm, h)
               for arm in ("IM", "R1") for h in (5, 10)}
    defensive = {arm: metrics([r for r in primary if r["arm"] == arm and
                  r["routeDecision"] == "DEFENSIVE_ELIGIBLE"]) for arm in ("IM", "R1")}
    low = {arm: metrics([r for r in primary if r["arm"] == arm and
           r["postEntryUpsidePct"] < 5]) for arm in ("IM", "R1")}
    bucket_table = {f"{arm}:{b}": metrics([r for r in primary if r["arm"] == arm and
                    r["bucket"] == b]) for arm in ("IM", "R1")
                    for b in ("<1", "1-3", "3-5", "5-10", ">=10")}
    route_table = {f"{arm}:{route}": metrics([r for r in primary if r["arm"] == arm and
                   r["routeDecision"] == route]) for arm in ("IM", "R1")
                   for route in ("DEFENSIVE_ELIGIBLE", "CONTROL_DEFAULT")}
    deciles = {f"{arm}:head{h}:{d}": metrics([r for r in primary if r["arm"] == arm and
               r[f"rank{h}Decile"] == d]) for arm in ("IM", "R1")
               for h in (5, 10) for d in range(10)}
    coverage = all(m["knownCoverage"] is not None and m["knownCoverage"] >= .8
                   for m in overall.values())
    winner = all(m["gate"] == "WINNER_PRESERVATION_PASS" for m in winners.values())
    value = all(m["knownCoverage"] is not None and m["knownCoverage"] >= .8 and
                dec(m["pairedDeltaJpy"]) > 0 for m in defensive.values())
    low_pass = all(dec(m["pairedDeltaJpy"]) >= 0 for m in low.values()) and any(
               dec(m["pairedDeltaJpy"]) > 0 for m in low.values())
    overall_pass = all(dec(m["pairedDeltaJpy"]) >= 0 for m in overall.values())
    gates = {"measurement": "PASS" if coverage else "LAYER_A_MEASUREMENT_BLOCKED",
             "winner": "WINNER_PRESERVATION_PASS" if winner else
                       ("WINNER_GATE_UNMEASURABLE" if any(m["gate"] ==
                        "WINNER_GATE_UNMEASURABLE" for m in winners.values())
                        else "WINNER_PRESERVATION_FAIL"),
             "defensiveRouteValue": "DEFENSIVE_ROUTE_VALUE_PASS" if value else
                                    "DEFENSIVE_ROUTE_VALUE_FAIL",
             "lowUpside": "PASS" if low_pass else
                          ("NO_DEFENSIVE_ECONOMIC_VALUE" if all(
                           dec(m["pairedDeltaJpy"]) == 0 for m in low.values())
                           else "LOW_UPSIDE_BENEFIT_FAIL"),
             "overall": "PASS" if overall_pass else "PRIMARY_OVERALL_REGRESSION"}
    result = {"schema": "phase57-prr-v2-layer-a-v1", "candidate": "PRR_CCMG_M50_AND_V2_CANONICAL",
              "primaryN": 111, "perArmOverall": overall, "winner": winners,
              "superWinner": {arm: winners[f"{arm}>=10"] for arm in ("IM", "R1")},
              "defensiveRoute": defensive, "lowUpsideLt5": low,
              "byBucket": bucket_table, "byRoute": route_table, "byRankDecile": deciles,
              "gates": gates, "capitalEligibleFromPrimary": all(x == "PASS" or
              x in ("WINNER_PRESERVATION_PASS", "DEFENSIVE_ROUTE_VALUE_PASS")
              for x in gates.values()), "r34ExactDecimal": True,
              "entryRowsSha256": rank.sha(OUT / "LAYER_A_ENTRY_ROWS.jsonl.gz"),
              "safety": SAFETY, "providerRequests": 0,
              "restrictedPartitionsOpened": 0}
    write("LAYER_A_RESULT.json", result)
    return result


def all_entry(rows):
    # The archived row holds funded R34 quantity for the Primary 111. Reprice
    # every Entry at 100 shares so this table is genuinely standalone.
    rows = [{**r, "quantity": 100,
             "controlPnlJpy": pnl100(r["entryPrice"], r["controlExitPrice"]),
             "ccmgPnlJpy": pnl100(r["entryPrice"], r["ccmgExitPrice"]),
             "r54PnlJpy": pnl100(r["entryPrice"], r["r54ExitPrice"]),
             "routedPnlJpy": pnl100(r["entryPrice"], r["ccmgExitPrice"] if
                                    r["routeDecision"] == "DEFENSIVE_ELIGIBLE" else
                                    r["controlExitPrice"])} for r in rows]
    for r in rows:
        r["pairedDeltaJpy"] = (None if r["routedPnlJpy"] is None or
                                r["controlPnlJpy"] is None else
                                str(dec(r["routedPnlJpy"]) - dec(r["controlPnlJpy"])))
    gzip_rows("ALL_ENTRY_ENTRY_ROWS.jsonl.gz", rows)
    arm = {a: metrics([r for r in rows if r["arm"] == a]) for a in ("IM", "R1")}
    rank.require(arm["IM"]["entryN"] == 819 and arm["R1"]["entryN"] == 795,
                 "ALL_ENTRY_CENSUS_ABORT")
    by_bucket = {f"{a}:{b}": metrics([r for r in rows if r["arm"] == a and
                 r["bucket"] == b]) for a in ("IM", "R1")
                 for b in ("<1", "1-3", "3-5", "5-10", ">=10")}
    winners = {f"{a}>={h}": metrics([r for r in rows if r["arm"] == a and
               r["postEntryUpsidePct"] >= h]) for a in ("IM", "R1") for h in (5, 10)}
    low = {a: metrics([r for r in rows if r["arm"] == a and
           r["postEntryUpsidePct"] < 5]) for a in ("IM", "R1")}
    defensive = {a: metrics([r for r in rows if r["arm"] == a and
                 r["routeDecision"] == "DEFENSIVE_ELIGIBLE"]) for a in ("IM", "R1")}
    by_session = {f"{a}:{s}": metrics([r for r in rows if r["arm"] == a and
                  r["session"] == s]) for a in ("IM", "R1")
                  for s in sorted({r["session"] for r in rows if r["arm"] == a})}
    defensive_session = {f"{a}:{s}": metrics([r for r in rows if r["arm"] == a and
                  r["session"] == s and r["routeDecision"] == "DEFENSIVE_ELIGIBLE"])
                  for a in ("IM", "R1")
                  for s in sorted({r["session"] for r in rows if r["arm"] == a})}
    win_pass = all(m["knownPairedN"] and
                   dec(m["routedMeanJpy"]) >= dec(m["controlMeanJpy"]) and
                   dec(m["pairedDeltaJpy"]) >= 0 for m in winners.values())
    val_pass = all(dec(low[a]["pairedDeltaJpy"]) >= 0 and
                   dec(defensive[a]["pairedDeltaJpy"]) > 0 for a in ("IM", "R1"))
    result = {"schema": "phase57-prr-v2-all-entry-standalone-v1",
              "population": "IM819/R1_795, 100-share standalone; not portfolio PnL",
              "byArm": arm, "byBucket": by_bucket, "winner": winners,
              "lowUpsideLt5": low, "defensiveRoute": defensive,
              "bySession": by_session, "defensiveBySession": defensive_session,
              "winnerGate": "PASS" if win_pass else "ALL_ENTRY_WINNER_REGRESSION",
              "defensiveValueGate": "PASS" if val_pass else
                                    "ALL_ENTRY_DEFENSIVE_VALUE_FAIL",
              "nullNotImputed": True, "safety": SAFETY}
    result["entryRowsSha256"] = rank.sha(OUT / "ALL_ENTRY_ENTRY_ROWS.jsonl.gz")
    write("ALL_ENTRY_RESULT.json", result)
    return result


def main():
    rows = join()
    primary = summaries(rows)
    # An economic Primary failure closes the candidate before all-entry.
    eligible = primary["capitalEligibleFromPrimary"]
    broad = all_entry(rows) if eligible else None
    print(json.dumps({"primaryGates": primary["gates"],
                      "allEntryWinner": None if broad is None else broad["winnerGate"],
                      "allEntryValue": None if broad is None else broad["defensiveValueGate"],
                      "primaryRoute": {a: primary["perArmOverall"][a]["defensiveRouteN"]
                                       for a in ("IM", "R1")}}))


if __name__ == "__main__":
    main()
