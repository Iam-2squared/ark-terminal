"""Independent saved-prediction replay, cash and scorecard audit (zero fit)."""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import math
from decimal import Decimal
from pathlib import Path

from scripts import phase57_exit_persistent_value_r53 as r
from scripts import phase57_exit_continuation_r52 as r52
from scripts import phase57_exit_continuation_r52_cycle2_report as report52
from scripts import phase57_exit_continuation_r52_independent_audit as extra52
from scripts import phase57_capital_exit_integrated as integrated
from scripts import phase57_capital_v3 as v3
from scripts import phase57_development_integrated_v0 as v0


def checked_ledger(ledger, p, score, card, evaluation):
    funded = ledger["funded"]
    closed = ledger["closed"]
    open_ids = ledger["endOpenEntryIds"]
    v0.require(len(funded) == len(closed) + len(open_ids) and
               set(open_ids).isdisjoint(x["entryId"] for x in closed) and
               set(funded) <= set(score), "R53_LEDGER_POSITION_CENSUS")
    v0.require(all(Decimal(row["cashJpy"]) >= 0 and row["openCount"] <= 3
                   for row in ledger["snapshots"]), "R53_CASH_OR_SLOT")
    v0.require(all(int(row["quantity"]) > 0 and int(row["quantity"]) % 100 == 0
                   for row in funded.values()), "R53_100_SHARE_LOT")
    spent = sum((Decimal(funded[e]["notionalJpy"]) for e in open_ids), Decimal(0))
    realized = sum((Decimal(row["realizedPnlJpy"]) for row in closed), Decimal(0))
    end_cash = Decimal(ledger["finalCashJpy"])
    v0.require(abs(end_cash - (Decimal(1000000) + realized - spent)) <
               Decimal("0.000001"), "R53_CASH_PNL_CONSERVATION")
    daily = card["daily"]
    v0.require(len(daily) == 24 and [row["session"] for row in daily] == p["sessions"] and
               all(row["dailyReturn"] is None for row in daily if not row["certified"]),
               "R53_DAILY_DENOMINATOR_OR_NULL")
    complete = card["dailySummary"]["validSessions"] == 24
    v0.require((card["portfolio"]["finalEquityJpy"] is not None) == complete and
               (card["dailySummary"]["geometric"] is not None) == complete,
               "R53_UNCERTIFIED_EQUITY_OR_DAILY")
    if complete:
        equity = Decimal(card["portfolio"]["finalEquityJpy"])
        v0.require(not open_ids and abs(equity - end_cash) < Decimal("0.000001"),
                   "R53_FINAL_CASH_VS_EQUITY")
        geometric = float((equity / Decimal(1000000)) **
                          (Decimal(1) / Decimal(24)) - Decimal(1))
        v0.require(abs(geometric - card["dailySummary"]["geometric"]) < 1e-12,
                   "R53_GEOMETRIC_DAILY_FORMULA")
    kind = r52.classify(ledger)
    v0.require(sum(kind[e] == "Initial" for e in kind) +
               sum(kind[e] == "Replacement" for e in kind) == len(funded),
               "R53_INITIAL_REPLACEMENT_EXCLUSIVE")
    for context in ("Initial", "Replacement", "Combined"):
        scoped = [e for e in funded if context == "Combined" or kind[e] == context]
        buckets = card["buckets"][context]
        v0.require(sum(x["count"] for x in buckets) == len(scoped) and
                   sum((Decimal(x["capitalAllocatedJpy"]) for x in buckets),
                       Decimal(0)) ==
                   sum((Decimal(funded[e]["notionalJpy"]) for e in scoped), Decimal(0)),
                   "R53_BUCKET_N_AND_CAPITAL_CENSUS")
        v0.require(card["quality"][context]["n"] == len(scoped),
                   "R53_QUALITY_DENOMINATOR")
    supplemental = extra52.supplemental(ledger, evaluation, p["sessions"])
    v0.require(supplemental == card["supplemental"] and
               supplemental["activeTradingMinutes"] == 7800 and
               supplemental["validMarkMinutes"] +
               supplemental["invalidMarkMinutes"] == 7800,
               "R53_UTILIZATION_COVERAGE")
    return {"funded": len(funded), "closed": len(closed), "unresolved": len(open_ids),
            "cashMinimumJpy": str(min(Decimal(x["cashJpy"]) for x in
                                      ledger["snapshots"])),
            "certifiedEod": card["dailySummary"]["validSessions"],
            "finalEquityJpy": card["portfolio"]["finalEquityJpy"],
            "invalidMarkMinutes": supplemental["invalidMarkMinutes"]}


def audit(source: Path, prediction: Path, result: Path, receipt: Path):
    p, metadata, arrays, identities, groups, entries, raw, values = r.read_inputs(
        source, prediction)
    manifest = json.loads((result / "manifest.json").read_text())
    v0.require(manifest["protocolSha256"] == r.sha(r.PRECOMMIT) and
               manifest["savedPredictionSha256"] == r.sha(prediction) and
               manifest["newFits"] == 0 and manifest["candidateCount"] == 1 and
               manifest["replayAbIdentical"] and
               manifest["archivedR50ControlByteIdentical"] and
               manifest["safety"] == v0.SAFETY, "R53_MANIFEST_IDENTITY")
    for name, expected in manifest["filesSha256"].items():
        v0.require(r.sha(result / name) == expected, "R53_RESULT_FILE_HASH:" + name)
    _, data, capital_scores, original_r50 = integrated.load_inputs()
    calendars, trace, support = r.calendar(
        p, metadata, arrays, identities, groups, entries, raw, values, original_r50)
    with gzip.open(result / "decision_trace.json.gz", "rt") as stream:
        saved_trace = json.load(stream)
    v0.require(v0.canonical(saved_trace) == v0.canonical(trace),
               "R53_SAVED_OOF_DECISIONS_DIFFER")
    v0.require(json.loads((result / "decision_support.json").read_text()) == support,
               "R53_DECISION_SUPPORT_CHANGED")
    cards = json.loads((result / "scorecard.json").read_text())
    paired = json.loads((result / "paired_layer_a.json").read_text())
    saved_verdict = json.loads((result / "selection.json").read_text())
    _, _, cohort, intents, evaluation, _, raw_execution, _, _, labels = data
    audited = {}
    for arm in v0.ARMS:
        short = "IM" if arm == v0.IM else "R1"
        rank = v3.ranked_intents(
            [x for x in intents[arm] if x["timestamp"][:10] in p["sessions"]],
            capital_scores[arm])
        subset = {**cohort, "sessions": p["sessions"]}
        for name, policy in (("R50_A_CONTROL", original_r50[arm]),
                             (r.NAME, calendars[arm])):
            actual = integrated.replay(arm, 3, subset, rank, raw_execution, policy)
            path = result / (short + "_" + name + "_ledger.json.gz")
            with gzip.open(path, "rt") as stream:
                saved = json.load(stream)
            v0.require(v0.canonical(saved) == v0.canonical(actual),
                       "R53_INDEPENDENT_SAVED_REPLAY_DIFFER:" + short + name)
            audited[short + "_" + name] = checked_ledger(
                saved, p, capital_scores[arm], cards[short][name], evaluation[arm])
            if name == "R50_A_CONTROL":
                v0.require(v0.canonical(saved) ==
                           v0.canonical(r52.archive_control(arm)),
                           "R53_ARCHIVED_CONTROL_DIFFER")
        with gzip.open(result / (short + "_" + r.NAME + "_ledger.json.gz"), "rt") as f:
            candidate = json.load(f)
        with gzip.open(result / (short + "_R50_A_CONTROL_ledger.json.gz"), "rt") as f:
            control = json.load(f)
        v0.require(cards[short][r.NAME]["currencyAttributionVsControl"] ==
                   r52.pnl_delta(control, candidate),
                   "R53_CURRENCY_ATTRIBUTION")
        expected_paired = r.paired_performance(
            r52.layer_a(control, calendars[arm], evaluation[arm]), control)
        v0.require(v0.canonical(paired[short]) == v0.canonical(expected_paired),
                   "R53_PAIRED_WINNER_SCOPE")
    expected = r.gate(p, cards, paired)
    v0.require(v0.canonical(expected) == v0.canonical(saved_verdict),
               "R53_GATE_VERDICT_CHANGED")
    v0.require(saved_verdict["selection"] in
               ("NO_SELECTION_STOP", "SELECT_DEVELOPMENT_ONLY") and
               (saved_verdict["selection"] != "SELECT_DEVELOPMENT_ONLY" or
                all(saved_verdict["checks"].values())),
               "R53_BAD_SELECTION")
    receipt.write_bytes(v0.canonical({
        "schema": "phase57-r53-independent-replay-accounting-audit-v1",
        "status": "PASS", "protocolSha256": r.sha(r.PRECOMMIT),
        "predictionSha256": r.sha(prediction), "newFits": 0,
        "candidateCount": 1, "independentCashLedgerReplays": 4,
        "candidateReplayAbIdentical": manifest["replayAbIdentical"],
        "controlArchivedByteIdentical": True,
        "cards": audited, "verdict": saved_verdict["selection"],
        "providerRequests": 0, "protectedOpened": 0, "safety": v0.SAFETY}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prediction", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    a = parser.parse_args()
    audit(a.source, a.prediction, a.result, a.receipt)


if __name__ == "__main__":
    main()
