"""Development v1 causal valuation accounting around the frozen v0 portfolio.

All Entry/rank/EXIT decisions are inherited unchanged. Last-observed marks are
accounting references only; they can never confirm a terminal EXIT or free cash.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import json
import math
from decimal import Decimal
from pathlib import Path

from scripts import phase57_cash_capital_r34 as cash
from scripts import phase57_cash_portfolio_r37 as sized
from scripts import phase57_development_integrated_v0 as v0

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/evidence/phase57-comprehensive-exit-v1/DEVELOPMENT_INTEGRATED_V1_PRECOMMIT.json"
PROTOCOL_SHA256 = "cb4ad1f28471cf26c1ddd50453445323f132410d7a7e34cabffdcfaa8c56ad71"
V0_SCORECARD_SHA256 = "c11d846809755d8d36193f2d7988a1fdc238e08292d97517787799b763757ca3"
SAFETY = dict(cash.SAFETY)


def contract():
    v0.require(v0.digest(PROTOCOL) == PROTOCOL_SHA256, "V1_PRE_PERFORMANCE_PROTOCOL_IDENTITY")
    x = json.loads(PROTOCOL.read_text())
    v0.require(x["status"] == "FROZEN_BEFORE_V1_PORTFOLIO_REPLAY_OR_V1_PERFORMANCE", "V1_NOT_FROZEN")
    v0.require(x["frozenInputs"]["v0SourceSha256"] ==
               v0.digest(ROOT / "scripts/phase57_development_integrated_v0.py"), "V0_SOURCE_DRIFT")
    v0.require(x["scope"]["capacities"] == [3, 4, 5] and
               len(x["valuationOptions"]) == 1 and
               x["valuationOptions"][0]["id"] == "SAME_SEGMENT_LAST_COMPLETED_TRADE_ASOF_V1",
               "V1_OPTION_SPACE_CHANGED")
    v0.require(x["safety"] == SAFETY and len(SAFETY) == 9 and
               not any(SAFETY.values()), "SAFETY9")
    return x


def segment(minute):
    if 540 <= minute <= 690:
        return (540, 690)
    if 750 <= minute <= 930:
        return (750, 930)
    return None


def observed_mark(raw, session, symbol, minute, entry_minute, entry_session):
    """A source-stamped mark; never a future bar, fill, or across-boundary carry."""
    if session != entry_session:
        return None
    bounds = segment(minute)
    if bounds is None:
        return None
    day = raw.get(session + "|" + symbol)
    if day is None:
        return None
    if minute == 930 and 930 in day:
        bar = day[930]
        v0.require(all(float(x) == float(bar[1]) for x in bar[1:5]), "NOT_SINGLE_PRICE_AUCTION")
        value = float(bar[1])
        origin, known, source = 930, 930, "RAW_SINGLE_PRICE_TERMINAL_AUCTION_MARK"
    else:
        # Entry OPEN was observable at the actual frozen fill; it remains a
        # within-segment reference until a later completed bar supersedes it.
        completed = [m for m in day if bounds[0] <= m < 930 and
                     m >= entry_minute and m + 1 <= minute]
        if completed:
            origin = max(completed)
            known = origin + 1
            value = float(day[origin][4])
            source = "RAW_LAST_COMPLETED_CLOSE_SAME_SEGMENT"
        elif bounds[0] <= entry_minute <= bounds[1] and entry_minute in day:
            origin, known, value, source = (entry_minute, entry_minute,
                                            float(day[entry_minute][1]),
                                            "RAW_ENTRY_OPEN_ASOF")
        else:
            return None
    v0.require(math.isfinite(value) and value > 0 and
               entry_minute <= known <= minute and bounds[0] <= known <= bounds[1],
               "INVALID_ASOF_MARK")
    return {"timestamp": v0.minute_stamp(session, known),
            "knownAt": v0.minute_stamp(session, known), "price": value,
            "source": source, "sourceMinute": origin,
            "staleMinutes": minute - known}


def core_mark(mark):
    return {k: mark[k] for k in ("timestamp", "knownAt", "price")}


class AsOfCensoredCashBook(v0.CensoredCashBook):
    """R34 invariants and R37 sizing with explicitly stamped segment as-of marks."""

    def snapshot(self, now, marks=None):
        when = cash.stamp(now)
        v0.require(self.last_now is None or when >= self.last_now, "SNAPSHOT_BEFORE_LEDGER")
        marks = {} if marks is None else marks
        v0.require(set(marks) <= set(self.positions), "MARK_FOR_UNOWNED_POSITION")
        exposure = Decimal(0)
        unrealized = Decimal(0)
        complete = True
        for eid, p in self.positions.items():
            mark = marks.get(eid)
            if mark is None:
                complete = False
                continue
            v0.require(set(mark) == {"timestamp", "knownAt", "price"}, "MARK_ALLOWLIST_MISMATCH")
            source_time, known = cash.stamp(mark["timestamp"]), cash.stamp(mark["knownAt"])
            entered = cash.stamp(p["entryTimestamp"])
            v0.require(entered <= source_time == known <= when, "FUTURE_OR_PRE_ENTRY_MARK")
            v0.require(known.date() == when.date() and
                       segment(known.hour*60 + known.minute) ==
                       segment(when.hour*60 + when.minute) is not None,
                       "CROSS_SEGMENT_OR_SESSION_STALE_MARK")
            v0.require(entered.date() == when.date(), "UNCERTIFIED_CROSS_SESSION_MARK")
            notional = cash.number(mark["price"], positive=True) * p["quantity"]
            exposure += notional
            unrealized += notional - p["cost"]
        self._invariants()
        equity = self.cash + exposure if complete else None
        return {"cashJpy": str(self.cash),
                "lockedPurchaseCostJpy": str(sum(
                    (p["cost"] for p in self.positions.values()), Decimal(0))),
                "realizedPnlJpy": str(self.realized),
                "unrealizedPnlJpy": str(unrealized) if complete else None,
                "positions": cash._wire(self.positions),
                "grossExposureJpy": str(exposure) if complete else None,
                "equityJpy": str(equity) if equity is not None else None,
                "grossExposureRatio": str(exposure/equity) if equity and equity > 0 else None,
                "borrowedCashJpy": "0", "capacity": self.capacity, "safety": SAFETY}


def mark_or_reason(raw, session, minute, eid, position, entry_meta):
    prior = cash.stamp(position["entryTimestamp"])
    if prior.date().isoformat() != session:
        return None, "UNCERTIFIED_OVERNIGHT_CORPORATE_ACTION_AND_NO_CROSS_SESSION_MARK"
    if segment(minute) is None:
        return None, "OUTSIDE_CONTINUOUS_SEGMENT"
    mark = observed_mark(raw, session, position["symbol"], minute,
                         entry_meta[eid]["entryMinute"], session)
    if mark is None:
        return None, ("NO_CROSS_LUNCH_MARK" if
                      segment(prior.hour*60+prior.minute) != segment(minute) else
                      "NO_OWNED_SAME_SEGMENT_OBSERVED_PRICE")
    return mark, None


def replay(arm, capacity, cohort, intents, terminal, raw):
    """No evaluator reference in decisions, marks, allocation or ledger."""
    v0.require(arm in v0.ARMS and capacity in v0.CAPACITIES, "VARIANT_ALLOWLIST")
    portfolio = sized.SizedCashPortfolio(capacity)
    portfolio.book = AsOfCensoredCashBook(capacity)
    by_event = collections.defaultdict(list)
    for intent in intents:
        when = cash.stamp(intent["timestamp"])
        by_event[(when.date().isoformat(), when.hour*60+when.minute)].append(intent)
    for group in by_event.values():
        group.sort(key=v0.event_priority)
    events, snapshots, funded, closed, unresolved, missing = [], [], {}, [], set(), []
    positions_meta, last_observed = {}, {}
    for session in cohort["sessions"]:
        minutes = sorted({540, 930} | {m for d, m in by_event if d == session})
        for minute in minutes:
            stamp = v0.minute_stamp(session, minute)
            outgoing = []
            if minute == 930:
                for eid in sorted(portfolio.book.positions):
                    t = terminal.get(eid)
                    if t is None or t["session"] != session:
                        continue
                    outgoing.append({"entryId": eid, "timestamp": stamp,
                                     "knownAt": stamp, "price": t["exitPrice"],
                                     "confirmed": t["exitPrice"] is not None})
            departing = {x["entryId"] for x in outgoing if x["confirmed"]}
            marks, missing_reasons = {}, {}
            for eid, position in sorted(portfolio.book.positions.items()):
                if eid in departing:
                    continue
                mark, reason = mark_or_reason(raw, session, minute, eid,
                                              position, positions_meta)
                if mark is not None:
                    marks[eid] = mark
                    last_observed[eid] = mark
                else:
                    missing_reasons[eid] = reason
            batch = portfolio.step(
                stamp, entry_intents=by_event.get((session, minute), ()),
                exits=outgoing, marks={eid: core_mark(x) for eid, x in marks.items()})
            for event in batch["ledger"]["events"]:
                if event["kind"] != "EXIT":
                    continue
                eid = event["entryId"]
                if event["status"] == "CLOSED":
                    meta = positions_meta[eid]
                    pnl, cost = Decimal(event["realizedPnlJpy"]), Decimal(meta["notionalJpy"])
                    closed.append({**meta, "exitTimestamp": stamp,
                                   "realizedPnlJpy": str(pnl),
                                   "netReturnPct": str(pnl / cost * 100),
                                   "sellCostJpy": str(event["sellCostJpy"]),
                                   "holdingWallMinutes": int(
                                       (cash.stamp(stamp)-cash.stamp(meta["entryTimestamp"]))
                                       .total_seconds()/60)})
                elif event["status"] == "UNRESOLVED_NO_CASH_RELEASE":
                    unresolved.add(eid)
            for x in batch["sizing"]:
                if x["status"] != "SIZED":
                    continue
                intent = next(i for i in by_event[(session, minute)] if i["entryId"] == x["entryId"])
                meta = {"entryId": x["entryId"], "symbol": x["symbol"],
                        "session": session, "entryTimestamp": stamp,
                        "entryMinute": minute,
                        "effectiveEntryPrice": str(intent["effectiveEntryPrice"]),
                        "rank": x["rank"], "quantity": x["quantity"],
                        "notionalJpy": str(x["costJpy"])}
                positions_meta[x["entryId"]] = meta
                funded[x["entryId"]] = meta
                mark = observed_mark(raw, session, x["symbol"], minute, minute, session)
                if mark is not None:
                    marks[x["entryId"]] = mark
                    last_observed[x["entryId"]] = mark
                else:
                    missing_reasons[x["entryId"]] = "ENTRY_RAW_OPEN_NOT_OBSERVED"
            core = {eid: core_mark(x) for eid, x in marks.items()}
            snap = portfolio.book.snapshot(stamp, core)
            open_details = []
            for eid, position in sorted(portfolio.book.positions.items()):
                item = marks.get(eid)
                market = None if item is None else str(
                    cash.number(item["price"], positive=True)*position["quantity"])
                unreal = None if market is None else str(Decimal(market)-position["cost"])
                open_details.append({
                    "entryId": eid, "symbol": position["symbol"],
                    "entryTimestamp": position["entryTimestamp"],
                    "quantity": position["quantity"], "costBasisJpy": str(position["cost"]),
                    "unresolvedExit": position["unresolved"],
                    "markPrice": None if item is None else item["price"],
                    "markSource": None if item is None else item["source"],
                    "markTimestamp": None if item is None else item["timestamp"],
                    "markKnownAt": None if item is None else item["knownAt"],
                    "sourceBarMinute": None if item is None else item["sourceMinute"],
                    "staleMinutes": None if item is None else item["staleMinutes"],
                    "markedNotionalJpy": market, "unrealizedPnlJpy": unreal,
                    "missingReason": missing_reasons.get(eid)})
                if item is None:
                    missing.append({
                        "variant": arm + "_MAX" + str(capacity),
                        "timestamp": stamp, "entryId": eid, "symbol": position["symbol"],
                        "quantity": position["quantity"], "costBasisJpy": str(position["cost"]),
                        "entryTimestamp": position["entryTimestamp"],
                        "rawReferenceKey": session + "|" + position["symbol"],
                        "rawKeyAllowlisted": session + "|" + position["symbol"] in raw,
                        "requiredSegment": segment(minute),
                        "lastObservedKnownAt": (last_observed[eid]["knownAt"]
                                                if eid in last_observed else None),
                        "lastObservedSource": (last_observed[eid]["source"]
                                               if eid in last_observed else None),
                        "reason": missing_reasons[eid],
                        "unresolvedExit": position["unresolved"]})
            snapshots.append({
                "session": session, "minute": minute, "timestamp": stamp,
                "cashJpy": snap["cashJpy"], "realizedPnlJpy": snap["realizedPnlJpy"],
                "unrealizedPnlJpy": snap["unrealizedPnlJpy"],
                "equityJpy": snap["equityJpy"],
                "equityValid": snap["equityJpy"] is not None,
                "grossExposureJpy": snap["grossExposureJpy"],
                "utilization": snap["grossExposureRatio"],
                "openCount": len(portfolio.book.positions),
                "unresolvedCount": sum(p["unresolved"] for p in portfolio.book.positions.values()),
                "capacity": capacity, "positions": open_details})
            events.append({"session": session, "minute": minute, "sizing": batch["sizing"],
                           "exitEvents": [e for e in batch["ledger"]["events"] if e["kind"] == "EXIT"],
                           "cashJpy": batch["ledger"]["cashJpy"],
                           "postEventEquityJpy": snap["equityJpy"]})
    v0.require(all(Decimal(x["cashJpy"]) >= 0 and x["openCount"] <= capacity
                   for x in snapshots), "CASH_OR_CAPACITY_INVARIANT")
    v0.require(len(unresolved) == len(portfolio.book.positions) and
               all(x["unresolved"] for x in portfolio.book.positions.values()),
               "OPEN_NOT_CENSORED_AT_END")
    return {"arm": arm, "capacity": capacity, "events": events, "snapshots": snapshots,
            "missingReferences": missing, "funded": funded, "closed": closed,
            "unresolvedEntryIds": sorted(unresolved),
            "endOpenEntryIds": sorted(portfolio.book.positions),
            "finalCashJpy": str(portfolio.book.cash), "safety": SAFETY}


def curve(result):
    out, peak = [], None
    for row in result["snapshots"]:
        val = None if row["equityJpy"] is None else float(row["equityJpy"])
        if val is None:
            peak, drawdown = None, None
        else:
            peak = max(peak or 1000000, val)
            drawdown = 100*(val/peak-1)
        out.append({"timestamp": row["timestamp"], "equityJpy": row["equityJpy"],
                    "cashJpy": row["cashJpy"],
                    "grossExposureJpy": row["grossExposureJpy"],
                    "utilization": row["utilization"], "drawdownPct": drawdown,
                    "equityValid": row["equityValid"]})
    return out


def card(result, evaluation, cohort):
    base = v0.scorecard(result, evaluation, cohort)
    snaps = result["snapshots"]
    valid_all = all(x["equityValid"] for x in snaps)
    if not valid_all:
        base["fullPeriodMaxDrawdownPct"] = None
        base["partialKnownSnapshotDrawdownPct"] = None
    base["unrealizedPnlJpy"] = snaps[-1]["unrealizedPnlJpy"]
    base["finalMarkedEquityJpy"] = snaps[-1]["equityJpy"]
    base["finalEquityJpy"] = (snaps[-1]["equityJpy"] if valid_all
                               and not result["endOpenEntryIds"] else None)
    base["portfolioReturnPct"] = (100*(float(base["finalEquityJpy"])/1000000-1)
                                  if base["finalEquityJpy"] is not None else None)
    base["markAccounting"] = "ASOF_WITHIN_SAME_SEGMENT_ONLY_NOT_EXECUTION"
    base["validEventCount"] = sum(x["equityValid"] for x in snaps)
    base["valuationEventCoverage"] = base["validEventCount"]/len(snaps)
    base["missingReferenceCount"] = len(result["missingReferences"])
    base["allScheduledEventsPriced"] = valid_all
    base["equityCurveCompleteness"] = "FULL" if valid_all else "PARTIAL_WITH_EXPLICIT_NULL_GAPS"
    base["finalExitSelected"] = False
    return base


def run(ledger_path, r1_path, raw_path):
    contract()
    cohort, intents, evaluation, terminal, raw = v0.load_sources(
        ledger_path, r1_path, raw_path)
    variants = {}
    for arm in v0.ARMS:
        for capacity in v0.CAPACITIES:
            name = arm + "_MAX" + str(capacity)
            ledger = replay(arm, capacity, cohort, intents[arm], terminal[arm], raw)
            variants[name] = {"card": card(ledger, evaluation[arm], cohort),
                              "ledger": ledger, "curve": curve(ledger)}
    paired = {str(n): v0.paired_by_opportunity(
        variants[v0.IM+"_MAX"+str(n)]["ledger"],
        variants[v0.R1+"_MAX"+str(n)]["ledger"],
        evaluation[v0.IM], evaluation[v0.R1]) for n in v0.CAPACITIES}
    return {"schema": "phase57-development-integrated-v1-result-v1",
            "protocolSha256": PROTOCOL_SHA256, "v0EnrichmentAuditedScorecardSha256": V0_SCORECARD_SHA256,
            "developmentSessions": cohort["sessions"],
            "exitStatus": "BENCHMARK_NOT_FINAL_EXIT", "variants": variants,
            "paired": paired, "modelFits": 0, "providerRequests": 0,
            "protectedPartitionsOpened": 0, "safety": SAFETY}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark-ledger", type=Path, required=True)
    ap.add_argument("--benchmark-ledger-b", type=Path)
    ap.add_argument("--r1-records", type=Path, required=True)
    ap.add_argument("--raw-path", type=Path, default=v0.ROOT /
                    "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--preflight-only", action="store_true")
    a = ap.parse_args()
    v0.require(not a.out.exists(), "APPEND_ONLY_OUTPUT_ALREADY_EXISTS")
    protocol = contract()
    if a.benchmark_ledger_b is not None:
        v0.require(v0.digest(a.benchmark_ledger)==v0.digest(a.benchmark_ledger_b),
                   "FROZEN_BENCHMARK_AB_MISMATCH")
    if a.preflight_only:
        cohort, intents, _, _, raw = v0.load_sources(a.benchmark_ledger, a.r1_records, a.raw_path)
        receipt = {"schema": "phase57-development-integrated-v1-preperformance-receipt",
                   "protocolSha256": PROTOCOL_SHA256,
                   "frozenEntryDualFreeze": protocol["frozenInputs"]["entryDualFreezeCommit"],
                   "entryFills": {arm: len(intents[arm]) for arm in v0.ARMS},
                   "sessions": len(cohort["sessions"]),
                   "allowlistedRawDecoded": len(raw),
                   "outsideRawPayloadSkippedBeforeDecode": cohort["rawPayloadsSkippedBeforeJsonDecode"],
                   "modelFits": 0, "portfolioReplays": 0,
                   "performanceInspected": False,
                   "providerRequests": 0, "protectedPartitionsOpened": 0,
                   "safety": SAFETY}
        a.out.write_bytes(v0.canonical(receipt))
        print(json.dumps(receipt, sort_keys=True))
        return
    result = run(a.benchmark_ledger, a.r1_records, a.raw_path)
    with a.out.open("wb") as stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as gz:
            gz.write(v0.canonical(result))
    print(json.dumps({"status": "DEVELOPMENT_BENCHMARK_ONLY",
                      "protocolSha256": PROTOCOL_SHA256,
                      "resultSha256": v0.digest(a.out),
                      "variants": {name: {"coverage": value["card"]["valuationEventCoverage"],
                                          "returnPct": value["card"]["portfolioReturnPct"]}
                                   for name, value in result["variants"].items()},
                      "safety": SAFETY}, sort_keys=True))


if __name__ == "__main__":
    main()
