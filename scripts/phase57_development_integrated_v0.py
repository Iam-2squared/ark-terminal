"""Frozen Entry + causal cash/rank + terminal-hold benchmark, Development only.

The evaluator is downstream of `replay`: no bucket, future High, terminal
outcome, or realized return is provided to allocation or sizing.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import statistics
from decimal import Decimal
from pathlib import Path

from scripts import phase57_cash_capital_r34 as cash
from scripts import phase57_cash_portfolio_r37 as sized

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/phase57-comprehensive-exit-v1"
IM = "IMMEDIATE"
R1 = "ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF"
ARMS = (IM, R1)
CAPACITIES = (3, 4, 5)
BENCHMARK_HASH = "770f02612cdd97ed2420f14a2fe6ab6ed1f50a96f222afa9b3c376982c8ea476"
RAW_HASH = "37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b"
PROTOCOL_V1_HASH = "c2f946f2031c6bda9f86c6eac7cbd5873b9b1fd10631cb8f8ee3174d9930d35d"
PROTOCOL_V2_HASH = "9b345b3e73214eea0c58caa9509ea0bff8dc6e3c57a9cff646a02566bf4d8fc0"
SAFETY = dict(cash.SAFETY)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode()


def minute_stamp(session, minute):
    return f"{session}T{minute // 60:02d}:{minute % 60:02d}:00+09:00"


def event_priority(x):
    return (x["newEligibleRank"], -x["savedV1Score"], x["symbol"], x["entryId"])


def structural_value_end(text, i):
    """Skip a JSON value without decoding its possibly out-of-scope payload."""
    quote=False; escaped=False; stack=[]
    while i<len(text):
        c=text[i]
        if quote:
            if escaped: escaped=False
            elif c=="\\": escaped=True
            elif c=='"': quote=False
        elif c=='"': quote=True
        elif c in "{[": stack.append(c)
        elif c in "}]":
            if not stack: break
            opener=stack.pop()
            require((opener,c) in (("{","}"),("[","]")),"JSON_UNBALANCED")
        elif c=="," and not stack: break
        i+=1
    require(not quote and not stack,"JSON_UNTERMINATED")
    return i


def frozen_origin_projection(path, expected_sha, allowed_ids):
    """Exact R35 scalar projection; avoid R35's unrelated chart/ML import graph."""
    require(digest(path) == expected_sha, "FROZEN_SELECTOR_ORIGIN_HASH")
    text=gzip.decompress(Path(path).read_bytes()).decode("utf-8")
    decoder=json.JSONDecoder()
    def whitespace(i):
        while i<len(text) and text[i].isspace(): i+=1
        return i
    i=whitespace(0)
    require(text[i]=="[","ORIGINS_NOT_ARRAY")
    i+=1
    result={}
    seen=set()
    while True:
        i=whitespace(i)
        if text[i]=="]":
            require(whitespace(i+1)==len(text),"ORIGINS_TRAILING_DATA")
            break
        start=i
        end=structural_value_end(text,start)
        obj=text[start:end]
        require(obj.startswith("{") and obj.endswith("}"),"ORIGIN_ELEMENT_NOT_OBJECT")
        j=1; oid=None; origin=None
        while j<len(obj)-1:
            while obj[j].isspace() or obj[j]==",": j+=1
            key,j=decoder.raw_decode(obj,j)
            require(isinstance(key,str),"ORIGIN_KEY")
            while obj[j].isspace(): j+=1
            require(obj[j]==":","ORIGIN_COLON")
            j+=1
            while obj[j].isspace(): j+=1
            stop=structural_value_end(obj,j)
            if key=="id":
                oid=decoder.raw_decode(obj,j)[0]
                require(isinstance(oid,str) and oid not in seen,"DUPLICATE_ORIGIN_ID")
                seen.add(oid)
            elif key=="origin" and oid in allowed_ids:
                origin=decoder.raw_decode(obj,j)[0]
            j=stop
        if oid in allowed_ids:
            require(isinstance(origin,dict),"ALLOWED_ORIGIN_MISSING")
            stamp=dt.datetime.fromisoformat(origin["decisionTimestamp"])
            rank=origin["newEligibleRank"]
            score=origin["savedV1Score"]
            require(stamp.tzinfo is not None and type(rank) is int and rank > 0
                    and isinstance(score,(float,int)) and not isinstance(score,bool)
                    and math.isfinite(score) and oid not in result,
                    "FROZEN_ORIGIN_R35_VALIDITY")
            result[oid]={"newEligibleRank":rank,"savedV1Score":float(score),
                         "rankKnownAtMinute":stamp.hour*60+stamp.minute,
                         "rankKnownAtSession":stamp.date().isoformat()}
        i=whitespace(end)
        require(text[i] in ",]","ORIGIN_ARRAY_SEPARATOR")
        if text[i]==",": i+=1
    require(len(seen)==5375 and set(result)==set(allowed_ids),
            "FROZEN_SELECTOR_ALLOWLIST_INCOMPLETE")
    return result


def frozen_entry_projection(path, arm, expected_sha):
    require(digest(path) == expected_sha,"FROZEN_ENTRY_SOURCE_HASH:"+arm)
    with gzip.open(path,"rt") as stream:
        source=json.load(stream)
    require(len(source)==2155,"FROZEN_ENTRY_POPULATION:"+arm)
    result=[]
    seen=set()
    for row in source:
        opportunity=row["opportunity"]
        require(opportunity not in seen and opportunity==row["session"]+"|"+row["symbol"],
                "FROZEN_ENTRY_IDENTITY:"+arm)
        seen.add(opportunity)
        entry_id=row["entryId"]
        if entry_id is None:
            require(row["entryMinute"] is None and row["price"] is None,"NO_ENTRY_FILL")
        else:
            require(entry_id==opportunity+"|"+str(row["entryMinute"])
                    and isinstance(row["price"],(float,int)) and not isinstance(row["price"],bool)
                    and math.isfinite(row["price"]) and row["price"]>0,"FROZEN_ENTRY_FILL")
        result.append({"opportunity":opportunity,"session":row["session"],
                       "symbol":row["symbol"],"entryId":entry_id,
                       "entryMinute":row["entryMinute"],"effectiveEntryPrice":row["price"]})
    return result


def allowlisted_raw_paths(path, allowed_keys):
    """Project top-level JSON members before decoding their raw-path payload.

    The source is a single JSON object. A small structural scanner skips each
    non-allowlisted value without json.loads/raw_decode of that value; only
    the already-frozen Entry Opportunity allowlist is materialized.
    """
    text=gzip.decompress(Path(path).read_bytes()).decode("utf-8")
    decoder=json.JSONDecoder()
    n=len(text)
    def whitespace(i):
        while i<n and text[i].isspace(): i+=1
        return i
    i=whitespace(0)
    require(i<n and text[i]=="{","RAW_JSON_NOT_OBJECT")
    i+=1; projected={}; seen=set(); skipped=0
    while True:
        i=whitespace(i)
        if i<n and text[i]=="}":
            i=whitespace(i+1)
            require(i==n,"RAW_JSON_TRAILING_DATA")
            break
        key,j=decoder.raw_decode(text,i)
        require(isinstance(key,str) and key not in seen,"RAW_KEY_INVALID_OR_DUPLICATE")
        seen.add(key)
        j=whitespace(j)
        require(j<n and text[j]==":","RAW_JSON_COLON")
        start=whitespace(j+1)
        if key in allowed_keys:
            value,end=decoder.raw_decode(text,start)
            require(isinstance(value,dict) and isinstance(value.get("today"),list),
                    "RAW_ALLOWED_VALUE_SCHEMA")
            minutes=[int(row[0]) for row in value["today"]]
            require(len(minutes)==len(set(minutes)),"RAW_DUPLICATE_MINUTE")
            projected[key]={int(row[0]):row for row in value["today"]}
            i=end
        else:
            skipped+=1
            i=structural_value_end(text,start)
        i=whitespace(i)
        require(i<n and text[i] in ",}","RAW_JSON_SEPARATOR")
        if text[i]==",": i+=1
    require(set(projected)==set(allowed_keys),"RAW_ALLOWLIST_INCOMPLETE")
    return projected,skipped


def load_contract():
    p1 = EVIDENCE / "DEVELOPMENT_INTEGRATED_V0_PRECOMMIT.json"
    p2 = EVIDENCE / "DEVELOPMENT_INTEGRATED_V0_PRECOMMIT_V2.json"
    require(digest(p1) == PROTOCOL_V1_HASH and digest(p2) == PROTOCOL_V2_HASH,
            "PRE_PERFORMANCE_PROTOCOL_IDENTITY")
    a, b = json.loads(p1.read_text()), json.loads(p2.read_text())
    require(a["status"].startswith("FROZEN_BEFORE") and
            b["status"].startswith("CONTROLLING_CORRECTION_FROZEN_BEFORE"),
            "NOT_PRECOMMITTED")
    require(a["safety"] == SAFETY and not any(SAFETY.values()), "SAFETY9")
    require(tuple(a["allocation"]["capacities"]) == CAPACITIES, "CAPACITY_SPACE")
    return a, b


def load_sources(ledger_path, r1_path, raw_path):
    contract, correction = load_contract()
    require(digest(ledger_path) == BENCHMARK_HASH, "BENCHMARK_LEDGER_HASH")
    require(digest(raw_path) == RAW_HASH, "RAW_PATH_HASH")
    immediate_path = ROOT / "docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/baseline-immediate-records.json.gz"
    full = {
        IM: frozen_entry_projection(immediate_path, IM, contract["inputPins"]["immediateRecordSha256"]),
        R1: frozen_entry_projection(Path(r1_path), R1, contract["inputPins"]["r1RecordSha256"]),
    }
    allowed_origins={row["opportunity"] for row in full[IM]}
    require(allowed_origins=={row["opportunity"] for row in full[R1]},"ENTRY_COHORT_MISMATCH")
    origin = frozen_origin_projection(ROOT / contract["inputPins"]["selectorOriginPath"],
                                      contract["inputPins"]["selectorOriginSha256"],
                                      allowed_origins)
    entries_by_arm = {arm: {r["entryId"]: r for r in records if r["entryId"]}
                      for arm, records in full.items()}
    expected_sessions = correction["controllingEvaluationCohort"]["sessions"]
    expected_counts = correction["controllingEvaluationCohort"]["fillsByArm"]
    intents = {arm: [] for arm in ARMS}
    evaluation = {arm: {} for arm in ARMS}
    terminal = {arm: {} for arm in ARMS}
    with gzip.open(ledger_path, "rt") as stream:
        for line in stream:
            row = json.loads(line)
            arm = row["entryArm"]
            require(arm in ARMS and row["candidateId"] == "R50_B_FAILED_RECOVERY",
                    "BENCHMARK_CANDIDATE_ID")
            require(row["exitKind"] == "FORCED_TERMINAL" and
                    row["authority"] == "FORCE_TERMINAL", "BENCHMARK_NON_TERMINAL")
            entry_id = row["entryId"]
            entry = entries_by_arm[arm].get(entry_id)
            require(entry is not None and row["session"] in expected_sessions,
                    "ENTRY_NOT_IN_FROZEN_EVALUATION_WINDOW")
            require(row["opportunity"] == entry["opportunity"] and
                    row["entryMinute"] == entry["entryMinute"] and
                    math.isclose(float(row["entryPrice"]), float(entry["effectiveEntryPrice"]),
                                 rel_tol=0, abs_tol=1e-7), "BENCHMARK_ENTRY_NOT_FROZEN")
            require(entry_id not in evaluation[arm], "DUPLICATE_FROZEN_ENTRY")
            rank = origin[entry["opportunity"]]
            known = rank["rankKnownAtMinute"]
            require(rank["rankKnownAtSession"] == entry["session"] and
                    known <= entry["entryMinute"], "FUTURE_RANK")
            # This strict allowlist is the only object passed to the allocator.
            intents[arm].append({
                "entryId": entry_id, "symbol": entry["symbol"],
                "timestamp": minute_stamp(entry["session"], entry["entryMinute"]),
                "entryKnownAt": minute_stamp(entry["session"], entry["entryMinute"]),
                "effectiveEntryPrice": entry["effectiveEntryPrice"],
                "newEligibleRank": rank["newEligibleRank"],
                "savedV1Score": rank["savedV1Score"],
                "rankKnownAt": minute_stamp(entry["session"], known),
                "side": "LONG", "account": "CASH"})
            # Evaluator fields are quarantined; never referenced from replay().
            metrics = row["metrics"]
            evaluation[arm][entry_id] = {
                "opportunity": entry["opportunity"], "session": entry["session"],
                "symbol": entry["symbol"], "entryMinute": entry["entryMinute"],
                "postUpsidePct": metrics["entryToPostEntryHighPct"],
                "canonicalBucket": metrics["canonicalBucket"],
                "terminalCapturePct": metrics["postEntryUpsideCapturePct"],
            }
            terminal[arm][entry_id] = {
                "session": row["session"], "exitMinute": row["exitMinute"],
                "exitPrice": row["exitPrice"], "exitKind": row["exitKind"]}
    require({arm: len(intents[arm]) for arm in ARMS} == expected_counts,
            "BENCHMARK_ENTRY_COHORT_COUNT")
    require(sorted({v["session"] for arm in ARMS for v in evaluation[arm].values()})
            == expected_sessions, "BENCHMARK_SESSION_COHORT")
    require(all(len(rows) == 2155 for rows in full.values()), "ENTRY_FULL_POPULATION")
    allowed_raw={v["opportunity"] for arm in ARMS for v in evaluation[arm].values()}
    raw,skipped=allowlisted_raw_paths(raw_path,allowed_raw)
    require(len(raw)==len(allowed_raw) and skipped==5375-len(allowed_raw),
            "RAW_ALLOWLIST_SCOPE_MISMATCH")
    for arm in ARMS:
        for eid, t in terminal[arm].items():
            auction = raw[evaluation[arm][eid]["opportunity"]].get(930)
            if t["exitPrice"] is None:
                require(t["exitMinute"] is None and auction is None, "MISSING_AUCTION_MISMATCH")
            else:
                require(t["exitMinute"] == 930 and auction is not None and
                        all(float(v) == float(auction[1]) for v in auction[1:5]) and
                        math.isclose(float(t["exitPrice"]), float(auction[1]), abs_tol=1e-8),
                        "BENCHMARK_AUCTION_IDENTITY")
    cohort=dict(correction["controllingEvaluationCohort"])
    cohort["allowlistedOriginPayloadsDecoded"]=len(origin)
    cohort["originPayloadsSkippedBeforeJsonDecode"]=5375-len(origin)
    cohort["allowlistedRawPayloadsDecoded"]=len(raw)
    cohort["rawPayloadsSkippedBeforeJsonDecode"]=skipped
    return cohort, intents, evaluation, terminal, raw


class CensoredCashBook(cash.CashBook):
    """R34 cash accounting, with benchmark-only overnight unresolved lock.

    R34 intentionally fails closed across an open overnight position. A missing
    terminal auction is a real unresolved state, not a liquidating fill; this
    subclass preserves cash/positions/invariants while allowing only unresolved
    positions to remain locked across the next session boundary.
    """
    def step(self, now, entries=(), exits=()):
        when = cash.stamp(now)
        if self.last_now is not None and when.date() > self.last_now.date() and self.positions:
            require(all(p["unresolved"] for p in self.positions.values()),
                    "OVERNIGHT_ONLY_FOR_CENSORED_TERMINAL")
            require(when > self.last_now, "OVERNIGHT_CLOCK_REVERSED")
            self.last_now = None  # bypass R34's no-overnight precondition only
        return super().step(now, entries=entries, exits=exits)


def fresh_mark(raw, session, symbol, minute, entry_id, *, newly_entered=False):
    day = raw.get(session + "|" + symbol)
    if day is None:
        return None
    if minute == 930:
        bar = day.get(930)
        price = None if bar is None else float(bar[1])
    elif newly_entered:
        bar = day.get(minute)
        price = None if bar is None else float(bar[1])
    else:
        # The bar [minute-1, minute) must exist exactly and already be closed.
        bar = day.get(minute - 1)
        price = None if bar is None else float(bar[4])
    if price is None:
        return None
    require(math.isfinite(price) and price > 0, "INVALID_FRESH_MARK")
    stamp = minute_stamp(session, minute)
    return {"timestamp": stamp, "knownAt": stamp, "price": price}


def replay(arm, capacity, cohort, intents, terminal, raw):
    """No access to evaluation outcomes: decisions use only allowed intent/marks."""
    require(arm in ARMS and capacity in CAPACITIES, "VARIANT_ALLOWLIST")
    portfolio = sized.SizedCashPortfolio(capacity)
    portfolio.book = CensoredCashBook(capacity)
    by_event = collections.defaultdict(list)
    for intent in intents:
        when = cash.stamp(intent["timestamp"])
        by_event[(when.date().isoformat(), when.hour * 60 + when.minute)].append(intent)
    for event in by_event.values():
        event.sort(key=event_priority)
    events, snapshots, funded, closed, unresolved = [], [], {}, [], set()
    positions_meta = {}
    for session in cohort["sessions"]:
        minutes = sorted({540, 930} | {m for day, m in by_event if day == session})
        for minute in minutes:
            stamp = minute_stamp(session, minute)
            outgoing = []
            if minute == 930:
                for eid in sorted(portfolio.book.positions):
                    t = terminal.get(eid)
                    if t is None or t["session"] != session:
                        continue  # older censored position has no fictional release
                    confirmed = t["exitPrice"] is not None
                    outgoing.append({"entryId": eid, "timestamp": stamp,
                                     "knownAt": stamp, "price": t["exitPrice"],
                                     "confirmed": confirmed})
            departing = {x["entryId"] for x in outgoing if x["confirmed"]}
            old_marks = {}
            for eid, held in portfolio.book.positions.items():
                if eid not in departing:
                    mark = fresh_mark(raw, session, held["symbol"], minute, eid)
                    if mark is not None:
                        old_marks[eid] = mark
            batch = portfolio.step(stamp, entry_intents=by_event.get((session, minute), ()),
                                   exits=outgoing, marks=old_marks)
            for x in batch["ledger"]["events"]:
                if x["kind"] != "EXIT":
                    continue
                if x["status"] == "CLOSED":
                    meta = positions_meta[x["entryId"]]
                    cost = Decimal(meta["notionalJpy"])
                    pnl = Decimal(x["realizedPnlJpy"])
                    closed.append({**meta, "exitTimestamp": stamp,
                                   "realizedPnlJpy": str(pnl),
                                   "netReturnPct": str(pnl / cost * 100),
                                   "sellCostJpy": str(x["sellCostJpy"]),
                                   "holdingWallMinutes": int((cash.stamp(stamp) -
                                       cash.stamp(meta["entryTimestamp"])).total_seconds() / 60)})
                elif x["status"] == "UNRESOLVED_NO_CASH_RELEASE":
                    unresolved.add(x["entryId"])
            for x in batch["sizing"]:
                if x["status"] != "SIZED":
                    continue
                intent = next(i for i in by_event[(session, minute)] if i["entryId"] == x["entryId"])
                meta = {"entryId": x["entryId"], "symbol": x["symbol"],
                        "session": session, "entryTimestamp": stamp,
                        "effectiveEntryPrice": str(intent["effectiveEntryPrice"]),
                        "rank": x["rank"], "quantity": x["quantity"],
                        "notionalJpy": str(x["costJpy"])}
                positions_meta[x["entryId"]] = meta
                funded[x["entryId"]] = meta
            marks = dict(old_marks)
            for x in batch["sizing"]:
                if x["status"] == "SIZED":
                    mark = fresh_mark(raw, session, x["symbol"], minute, x["entryId"],
                                      newly_entered=True)
                    if mark is not None:
                        marks[x["entryId"]] = mark
            snapshot = portfolio.book.snapshot(stamp, marks)
            snapshots.append({"session": session, "minute": minute, "timestamp": stamp,
                              "equityJpy": snapshot["equityJpy"],
                              "grossExposureJpy": snapshot["grossExposureJpy"],
                              "cashJpy": snapshot["cashJpy"],
                              "openCount": len(portfolio.book.positions)})
            events.append({"session": session, "minute": minute, "sizing": batch["sizing"],
                           "exitEvents": [e for e in batch["ledger"]["events"] if e["kind"] == "EXIT"],
                           "cashJpy": batch["ledger"]["cashJpy"],
                           "postEventEquityJpy": snapshot["equityJpy"]})
    require(not any(x["equityJpy"] is not None and Decimal(x["cashJpy"]) < 0
                    for x in snapshots), "NEGATIVE_CASH")
    require(all(x["openCount"] <= capacity for x in snapshots), "CAPACITY_OVERFLOW")
    return {"arm": arm, "capacity": capacity, "events": events,
            "snapshots": snapshots, "funded": funded, "closed": closed,
            "unresolvedEntryIds": sorted(unresolved),
            "endOpenEntryIds": sorted(portfolio.book.positions),
            "finalCashJpy": str(portfolio.book.cash), "safety": SAFETY}


def bucket(item, kind):
    if kind == "POST_ENTRY_UPSIDE_GE5":
        value = item["postUpsidePct"]
        return value is not None and value >= 5
    require(kind == "CANONICAL_L2H_GE5", "UNKNOWN_BUCKET")
    return item["canonicalBucket"] == ">=5%"


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    offset = fraction * (len(ordered) - 1)
    lo, hi = math.floor(offset), math.ceil(offset)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (offset - lo)


def concentration(items, key):
    counts = collections.Counter(x[key] for x in items)
    return {"n": len(items), "distinct": len(counts),
            "topShare": max(counts.values()) / len(items) if items else None,
            "top": counts.most_common(5)}


def enrichment(arm, intents, evaluation, cohort):
    """Evaluator-only, after frozen causal ordering; never an allocation input."""
    require(len(intents) == cohort["fillsByArm"][arm], "ENRICHMENT_COHORT")
    batches = collections.defaultdict(list)
    for x in intents:
        batches[x["timestamp"]].append(x)
    for group in batches.values():
        group.sort(key=event_priority)
    all_ids = {x["entryId"] for x in intents}
    primary = {eid for eid in all_ids if bucket(evaluation[eid], "POST_ENTRY_UPSIDE_GE5")}
    secondary = {eid for eid in all_ids if bucket(evaluation[eid], "CANONICAL_L2H_GE5")}
    require(len(primary) == cohort["primaryPostEntryUpsideGe5ByArm"][arm]
            and len(secondary) == cohort["secondaryCanonicalL2hGe5ByArm"][arm],
            "FROZEN_SUPPORT_IDENTITY")
    output = {"entryArm": arm, "totalCandidates": len(intents), "eventBatches": len(batches),
              "simultaneousFourPlusEvents": sum(len(v) >= 4 for v in batches.values()),
              "primarySupport": len(primary), "secondarySupport": len(secondary), "top": {}}
    for top_n in (1, 3, 5):
        selected = [x for group in batches.values() for x in group[:top_n]]
        ids = {x["entryId"] for x in selected}
        upsides = [evaluation[eid]["postUpsidePct"] for eid in ids
                   if evaluation[eid]["postUpsidePct"] is not None]
        session_counts = collections.Counter(x["timestamp"][:10] for x in selected)
        session_hits = collections.Counter(evaluation[eid]["session"] for eid in ids & primary)
        n, hit, canon = len(ids), len(ids & primary), len(ids & secondary)
        baseline = len(primary) / len(intents)
        output["top"][str(top_n)] = {
            "selected": n, "primaryHits": hit, "hitRate": hit/n if n else None,
            "baselineHitRate": baseline,
            "enrichmentMultiple": (hit/n)/baseline if n and baseline else None,
            "primaryReach": hit/len(primary), "primaryMiss": len(primary)-hit,
            "primaryMissRate": (len(primary)-hit)/len(primary),
            "canonicalHits": canon, "canonicalReach": canon/len(secondary),
            "upsideMeanPct": statistics.fmean(upsides) if upsides else None,
            "upsideMedianPct": statistics.median(upsides) if upsides else None,
            "upsideP25Pct": percentile(upsides,.25),
            "upsideP75Pct": percentile(upsides,.75),
            "upsideP90Pct": percentile(upsides,.9),
            "upsideGe7_5Rate": sum(v >= 7.5 for v in upsides)/n if n else None,
            "upsideGe10Rate": sum(v >= 10 for v in upsides)/n if n else None,
            "missingUpsideN": n-len(upsides),
            "sessionHitRates": {s: {"selected": session_counts[s], "hits": session_hits[s],
                                   "rate": session_hits[s]/session_counts[s] if session_counts[s] else None}
                                for s in cohort["sessions"]},
            "symbolConcentration": concentration(selected, "symbol"),
            "sessionConcentration": concentration(
                [{"session": x["timestamp"][:10]} for x in selected], "session")}
    output["fourPlusBatches"] = [{"timestamp": stamp, "candidates": len(group),
                                   "orderedEntryIds": [x["entryId"] for x in group],
                                   "topThreePrimaryHits": sum(x["entryId"] in primary for x in group[:3]),
                                   "belowTopThreePrimaryHits": sum(x["entryId"] in primary for x in group[3:])}
                                  for stamp, group in sorted(batches.items()) if len(group) >= 4]
    output["evaluatorOnly"] = True
    return output


def scorecard(result, evaluation, cohort):
    """Post-replay-only descriptive benchmark; no SELECT or Final EXIT label."""
    snaps = result["snapshots"]
    closed = result["closed"]
    events = result["events"]
    pnls = [float(x["realizedPnlJpy"]) for x in closed]
    nets = [float(x["netReturnPct"]) for x in closed]
    wins, losses = [v for v in pnls if v > 0], [v for v in pnls if v < 0]
    costs = [float(x["notionalJpy"]) for x in result["funded"].values()]
    known = [x for x in snaps if x["equityJpy"] is not None]
    equity = [float(x["equityJpy"]) for x in known]
    complete = len(known) == len(snaps)
    peak = 1000000.0
    dd = 0.0
    for val in equity:
        peak = max(peak, val)
        dd = min(dd, 100*(val/peak-1))
    time_weight, util_sum, util80, total_duration = 0, 0.0, 0, 0
    for x, y in zip(snaps, snaps[1:]):
        if x["session"] != y["session"]:
            continue
        duration = y["minute"] - x["minute"]
        total_duration += duration
        if x["equityJpy"] is None or y["equityJpy"] is None:
            continue
        equity_now = float(x["equityJpy"])
        utilization = float(x["grossExposureJpy"])/equity_now if equity_now > 0 else 0
        time_weight += duration
        util_sum += duration * utilization
        util80 += duration * (utilization >= .8)
    funded = result["funded"]
    funded_ids = set(funded)
    closed_by_id = {x["entryId"]: x for x in closed}
    attribution = {}
    for kind in ("POST_ENTRY_UPSIDE_GE5", "CANONICAL_L2H_GE5"):
        available = {eid for eid, x in evaluation.items() if bucket(x, kind)}
        reached = sorted(funded_ids & available)
        funded_capital = sum(float(funded[eid]["notionalJpy"]) for eid in reached)
        captures = [evaluation[eid]["terminalCapturePct"] for eid in reached
                    if eid in closed_by_id and evaluation[eid]["terminalCapturePct"] is not None]
        attribution[kind] = {"available": len(available), "funded": len(reached),
                             "missed": len(available)-len(reached),
                             "reachRate": len(reached)/len(available) if available else None,
                             "missRate": 1-len(reached)/len(available) if available else None,
                             "capitalJpy": funded_capital,
                             "shareOfInvestedCapital": funded_capital/sum(costs) if costs else None,
                             "realizedNetJpy": sum(float(closed_by_id[eid]["realizedPnlJpy"])
                                                   for eid in reached if eid in closed_by_id),
                             "meanTerminalCapturePct": statistics.fmean(captures) if captures else None,
                             "unresolvedFunded": sum(eid not in closed_by_id for eid in reached),
                             "fedBackToCapital": False}
    rejected = collections.Counter(x["reason"] for event in events for x in event["sizing"]
                                   if x["status"] == "REJECTED")
    four_plus = []
    for event in events:
        if len(event["sizing"]) < 4:
            continue
        accepts = [x for x in event["sizing"] if x["status"] == "SIZED"]
        refusals = [x for x in event["sizing"] if x["status"] != "SIZED"]
        four_plus.append({"timestamp": minute_stamp(event["session"], event["minute"]),
                          "accepted": [x["entryId"] for x in accepts],
                          "rejected": [{"entryId": x["entryId"], "reason": x["reason"]}
                                       for x in refusals],
                          "acceptedPrimaryHitsEvaluatorOnly": sum(bucket(evaluation[x["entryId"]],
                              "POST_ENTRY_UPSIDE_GE5") for x in accepts),
                          "rejectedPrimaryHitsEvaluatorOnly": sum(bucket(evaluation[x["entryId"]],
                              "POST_ENTRY_UPSIDE_GE5") for x in refusals)})
    end_open = len(result["endOpenEntryIds"])
    final = float(snaps[-1]["equityJpy"]) if snaps[-1]["equityJpy"] is not None and not end_open else None
    return {
        "entryArm": result["arm"], "capacity": result["capacity"],
        "exitStatus": "BENCHMARK_NOT_FINAL_EXIT", "developmentSubsetOnly": True,
        "initialCashJpy": 1000000, "finalCashJpy": result["finalCashJpy"],
        "finalEquityJpy": final, "portfolioReturnPct": 100*(final/1000000-1) if final is not None else None,
        "fullPeriodMaxDrawdownPct": dd if complete else None,
        "partialKnownSnapshotDrawdownPct": dd if not complete else None,
        "realizedPnlJpy": sum(pnls), "profitFactor": sum(wins)/-sum(losses) if losses else None,
        "winRate": len(wins)/len(pnls) if pnls else None,
        "averageWinJpy": statistics.fmean(wins) if wins else None,
        "averageLossJpy": statistics.fmean(losses) if losses else None,
        "p05TradeNetPct": percentile(nets,.05), "p10TradeNetPct": percentile(nets,.1),
        "worstTradeNetPct": min(nets) if nets else None,
        "entries": len(funded), "exits": len(closed), "unresolved": len(result["unresolvedEntryIds"]),
        "censoredEndOpen": end_open,
        "capacityRejects": rejected.get("MAX_CONCURRENT_SYMBOLS",0),
        "insufficientCashRejects": rejected.get("NO_100_SHARE_LOT_WITHIN_TARGET_AND_CASH",0)
                                   + rejected.get("INSUFFICIENT_AVAILABLE_CASH",0),
        "otherRejectReasons": dict(rejected),
        "turnoverJpy": sum(costs)+sum(float(x["notionalJpy"])+float(x["realizedPnlJpy"])
                                      for x in closed),
        "averageHoldingWallMinutes": statistics.fmean(x["holdingWallMinutes"] for x in closed)
                                     if closed else None,
        "capitalLockMeanKnownJpy": statistics.fmean(float(x["grossExposureJpy"])
                                                     for x in known) if known else None,
        "eventMeanUtilization": statistics.fmean(float(x["grossExposureJpy"])/float(x["equityJpy"])
                                                   for x in known if float(x["equityJpy"])>0)
                                 if known else None,
        "timeWeightedUtilizationCovered": util_sum/time_weight if time_weight else None,
        "timeShareUtilizationAtLeast80Covered": util80/time_weight if time_weight else None,
        "pricedMinutes": time_weight, "totalScheduledWindowMinutes": total_duration,
        "pricedMinuteCoverage": time_weight/total_duration if total_duration else None,
        "completeMarkedEvents": len(known), "allEvents": len(snaps),
        "minimumCashJpy": min(float(x["cashJpy"]) for x in snaps),
        "maximumGrossExposureKnownJpy": max(float(x["grossExposureJpy"]) for x in known)
                                        if known else None,
        "averageGrossExposureKnownJpy": statistics.fmean(float(x["grossExposureJpy"])
                                                          for x in known) if known else None,
        "symbolConcentration": concentration(list(funded.values()), "symbol"),
        "sessionConcentration": concentration(list(funded.values()), "session"),
        "topContributorsJpy": collections.Counter({k: sum(float(x["realizedPnlJpy"])
            for x in closed if x["symbol"] == k) for k in {x["symbol"] for x in closed}}).most_common(10),
        "fourPlusEventAttribution": four_plus,
        "attributionEvaluatorOnly": attribution,
        "noFinalExitClaim": True, "notFreshOrLiveEstimate": True, "safety": SAFETY,
    }


def paired_by_opportunity(im, r1, eval_im, eval_r1):
    im_candidates = {x["opportunity"]: eid for eid,x in eval_im.items()}
    r1_candidates = {x["opportunity"]: eid for eid,x in eval_r1.items()}
    common = sorted(set(im_candidates) & set(r1_candidates))
    pairs = []
    c_im = {x["entryId"]: x for x in im["closed"]}
    c_r1 = {x["entryId"]: x for x in r1["closed"]}
    for opportunity in common:
        a,b = im_candidates[opportunity],r1_candidates[opportunity]
        if a not in im["funded"] or b not in r1["funded"]:
            continue
        x,y=im["funded"][a],r1["funded"][b]
        pairs.append({"opportunity":opportunity,"imEntryMinute":eval_im[a]["entryMinute"],
                      "r1EntryMinute":eval_r1[b]["entryMinute"],
                      "imPrice":x["effectiveEntryPrice"],"r1Price":y["effectiveEntryPrice"],
                      "imRank":x["rank"],"r1Rank":y["rank"],
                      "imAllocationJpy":x["notionalJpy"],"r1AllocationJpy":y["notionalJpy"],
                      "imNetPct":c_im[a]["netReturnPct"] if a in c_im else None,
                      "r1NetPct":c_r1[b]["netReturnPct"] if b in c_r1 else None,
                      "imCapitalLockWallMinutes":c_im[a]["holdingWallMinutes"] if a in c_im else None,
                      "r1CapitalLockWallMinutes":c_r1[b]["holdingWallMinutes"] if b in c_r1 else None,
                      "imRemainingUpsideEvaluatorOnly":eval_im[a]["postUpsidePct"],
                      "r1RemainingUpsideEvaluatorOnly":eval_r1[b]["postUpsidePct"]})
    return {"commonCandidateOpportunities":len(common),"commonFundedOpportunities":len(pairs),
            "pairedFunded":pairs,"evaluatorFieldsNeverCapitalInput":True}


def run(ledger_path,r1_path,raw_path):
    cohort, intents, evaluation, terminal, raw = load_sources(ledger_path,r1_path,raw_path)
    enrich = {arm: enrichment(arm,intents[arm],evaluation[arm],cohort) for arm in ARMS}
    variants={}
    for arm in ARMS:
        for n in CAPACITIES:
            ledger=replay(arm,n,cohort,intents[arm],terminal[arm],raw)
            card=scorecard(ledger,evaluation[arm],cohort)
            variants[arm+"_MAX"+str(n)]={"card":card,"ledger":ledger}
    pairs={str(n):paired_by_opportunity(variants[IM+"_MAX"+str(n)]["ledger"],
             variants[R1+"_MAX"+str(n)]["ledger"],evaluation[IM],evaluation[R1])
           for n in CAPACITIES}
    return {"schema":"phase57-development-integrated-v0-result-v1",
            "protocolV1Sha256":PROTOCOL_V1_HASH,"controllingProtocolV2Sha256":PROTOCOL_V2_HASH,
            "sourceLedgerSha256":BENCHMARK_HASH,"exitStatus":"BENCHMARK_NOT_FINAL_EXIT",
            "developmentSubsetOnly":True,"cohortSessions":cohort["sessions"],
            "enrichment":enrich,"variants":variants,"paired":pairs,
            "providerRequests":0,"protectedPartitionsOpened":0,"safety":SAFETY}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--benchmark-ledger",type=Path,required=True)
    ap.add_argument("--r1-records",type=Path,required=True)
    ap.add_argument("--raw-path",type=Path,default=ROOT/
        "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz")
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--benchmark-ledger-b",type=Path)
    args=ap.parse_args()
    require(not args.out.exists(),"APPEND_ONLY_OUTPUT_ALREADY_EXISTS")
    if args.benchmark_ledger_b is not None:
        require(digest(args.benchmark_ledger)==digest(args.benchmark_ledger_b),
                "BENCHMARK_RUN_AB_MISMATCH")
    if args.preflight_only:
        cohort,intents,_,_,_=load_sources(args.benchmark_ledger,args.r1_records,args.raw_path)
        receipt={"schema":"phase57-development-integrated-v0-preperformance-ci-receipt",
                 "protocolSha256":PROTOCOL_V2_HASH,"benchmarkLedgerSha256":BENCHMARK_HASH,
                 "entryArms":{arm:len(intents[arm]) for arm in ARMS},
                 "sessions":len(cohort["sessions"]),"modelFits":0,
                 "allowlistedOriginPayloadsDecoded":cohort["allowlistedOriginPayloadsDecoded"],
                 "originPayloadsSkippedBeforeJsonDecode":cohort["originPayloadsSkippedBeforeJsonDecode"],
                 "allowlistedRawPayloadsDecoded":cohort["allowlistedRawPayloadsDecoded"],
                 "rawPayloadsSkippedBeforeJsonDecode":cohort["rawPayloadsSkippedBeforeJsonDecode"],
                 "earlierLocalPreflightDecodedOutsideAllowlist":4225,
                 "candidatePerformanceInspected":0,"portfolioReplays":0,
                 "providerRequests":0,"protectedPartitionsOpened":0,"safety":SAFETY}
        args.out.write_bytes(canonical(receipt))
        print(json.dumps(receipt,sort_keys=True))
        return
    output=run(args.benchmark_ledger,args.r1_records,args.raw_path)
    encoded=canonical(output)
    with args.out.open("wb") as handle:
        with gzip.GzipFile(filename="",fileobj=handle,mode="wb",mtime=0) as gz:
            gz.write(encoded)
    print(json.dumps({"status":"DEVELOPMENT_BENCHMARK_ONLY","outputSha256":digest(args.out),
                      "protocolSha256":PROTOCOL_V2_HASH,
                      "variants":{k:v["card"]["portfolioReturnPct"] for k,v in output["variants"].items()},
                      "safety":SAFETY},sort_keys=True))


if __name__=="__main__":
    main()
