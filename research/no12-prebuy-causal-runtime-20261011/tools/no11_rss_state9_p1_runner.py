#!/usr/bin/env python3
"""Received RSS minute feed -> unchanged RC2/Path/P1 features -> F5/Q70 shadow.

Local deterministic consumer, not an Excel collector or an order writer.
RC2 retains its scheduled-bar integer clock. PC receipt times gate the outer
stream and are never backdated to bar close or called broker timestamps.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

import no11_frozen_p1_feature_runtime as features
import no11_p1_forward_shadow as forward

PREVIOUS_SCHEMA = "ARK_NO11_RSS_P1_PREVIOUS_CONTEXT_V1"
VA_SOURCE = "RSS_MARKET_CUMULATIVE_60S_ESTIMATE_NOT_VENDOR_MINUTE_VA"
KERNEL_SOURCE = "RSS_CHART_LOCAL_RECEIPT_LOGICAL_BAR_CLOCK"
SOURCE_KIND = "RSS_CUMULATIVE_PROXY"


def need(ok, code):
    if not ok:
        raise ValueError("P1_RSS_" + code)


def minute(value):
    need(type(value) is str and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value), "BAR_CLOCK_INVALID")
    return int(value[:2]) * 60 + int(value[3:])


def stamp(day, m):
    return day + f"T{m // 60:02d}:{m % 60:02d}:00+09:00"


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_prices(row, require_va=True):
    need(all(number(row.get(k)) for k in ("O", "H", "L", "C", "Vo")), "NONNUMERIC_OHLCV")
    need(0 < row["L"] <= min(row["O"], row["C"]) <= max(row["O"], row["C"]) <= row["H"]
         and row["Vo"] >= 0 and int(row["Vo"]) == row["Vo"], "INVALID_OHLCV")
    if require_va or row.get("Va") is not None:
        need(number(row.get("Va")) and row["Va"] >= 0 and
             ((row["Vo"] == 0) == (row["Va"] == 0)), "INVALID_OR_MISSING_VA")


def previous_cash_session(repo, day):
    """Use the shipped dated calendar, not an assumed weekday calendar."""
    calendar = (Path(repo) / "research/no12-prebuy-causal-runtime-20261011/runtime/jpx_cash_calendar_2026_2027.mjs").as_uri()
    script = ("import {isJpxCashTradingDay,previousJpxCashTradingDays} from " + json.dumps(calendar) + ";"
              "const d=process.argv[1];if(!isJpxCashTradingDay(d))process.exit(2);"
              "console.log(previousJpxCashTradingDays(d,1)[0]);")
    result = subprocess.run(["node", "--input-type=module", "-e", script, day],
                            capture_output=True, text=True, timeout=15, check=False)
    need(result.returncode == 0, "DATED_CASH_CALENDAR_FAILED")
    prior = result.stdout.strip()
    forward.day(prior)
    need(prior < day, "PREVIOUS_SESSION_INVALID")
    return prior


def read_json(path, limit=100_000_000):
    path = Path(path).absolute()
    need(path.is_file() and not path.is_symlink() and
         not any(p.is_symlink() for p in path.parents) and 0 < path.stat().st_size <= limit,
         "PRIVATE_INPUT_INVALID")
    data = path.read_bytes()
    return json.loads(data.decode("utf-8-sig")), hashlib.sha256(data).hexdigest()


class ObservedStateStream:
    """Original normalization, exact RC2 engine and original P1 Path/history."""
    def __init__(self, runtime, session, code, context, previous_session):
        self.runtime, self.session, self.code = runtime, session, code
        self.key = session + "|" + code
        need(isinstance(context, dict) and context.get("previousSession") == previous_session
             and context.get("priceBasis") == "COMPARABLE_RAW"
             and context.get("corporateActionsCleared") is True, "PREVIOUS_BASIS_REQUIRED")
        self.previous_known = forward.clock(context.get("knownAtJst"), session)
        rows = context.get("rows")
        need(isinstance(rows, list) and 2 <= len(rows) <= 400, "PREVIOUS_MINUTES_REQUIRED")
        previous_tokens, self.previous_activity = [], []
        seen = set()
        prior_schedule = set(runtime.namespace["scheduled_minutes"](previous_session))
        for row in rows:
            need(row.get("Code") == code and row.get("Date") == previous_session, "PREVIOUS_ROW_IDENTITY")
            m = minute(row.get("Time"))
            need(m + 1 in prior_schedule and m not in seen, "PREVIOUS_ROW_CLOCK_OR_DUPLICATE")
            seen.add(m)
            validate_prices(row, require_va=False)
            previous_tokens.append({"Date": previous_session, "Time": row["Time"],
                                    **{k: str(row[k]) for k in ("O", "H", "L", "C")},
                                    "_source": {"kind": "RSS_OBSERVED_PREVIOUS_PRICE_NOT_JQUANTS",
                                                "rowSha256": forward.digest(row)}})
            # Missing previous-day Va stays missing, never close*volume or zero.
            if row.get("Va") is not None:
                self.previous_activity.append([m] + [row[k] for k in ("O", "H", "L", "C", "Vo", "Va")])
        previous_tokens.sort(key=lambda r: r["Time"])
        self.previous_activity.sort(key=lambda r: r[0])
        a = runtime.namespace["normalize80"].generate(previous_tokens, [])
        b = runtime.namespace["normalize120"].regenerate(previous_tokens, [])
        need(a["U"] == b["U"] and a["P_ref"] == b["P_ref"], "PREVIOUS_NORMALIZATION_UNSTABLE")
        self.base = a
        self.engine = runtime.Engine(runtime.profile)
        self.state_features = features.StateFeatureStream(runtime, session, self.key)
        self.schedule = list(runtime.namespace["scheduled_minutes"](session))
        self.regular = set(runtime.namespace["regular_starts"](session))
        self.cursor = 0
        self.cache = {}
        self.today = []
        self.first_am = self.first_pm = None
        self.last_received = None
        self.missing_ticks = self.accepted_ticks = 0
        self.last_state = None

    def coordinate(self, price):
        token = str(price)
        if token not in self.cache:
            values = []
            for precision in (80, 120):
                with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN,
                                          Emin=-999999, Emax=999999)):
                    value = (Decimal(token).ln() - Decimal(self.base["P_ref"]).ln()) / Decimal(self.base["U"])
                    values.append(format(value.quantize(Decimal("1e-24")), "f"))
            need(values[0] == values[1], "COORDINATE_UNSTABLE")
            self.cache[token] = values[0]
        return self.cache[token]

    def push(self, row):
        m = minute(row["Time"])
        end = m + 1
        received = forward.clock(row["knownAtJst"], self.session)
        need(self.previous_known <= received and
             (self.last_received is None or received >= self.last_received), "RECEIPT_CLOCK_REVERSED")
        need(self.cursor < len(self.schedule) and end >= self.schedule[self.cursor]
             and end in self.schedule, "LATE_OR_REVISED_BAR")
        while self.schedule[self.cursor] < end:
            missing_end = self.schedule[self.cursor]
            t = missing_end - 540
            state = self.engine.step(t, None, self.key)
            self.state_features.push(state, {"scheduled_t": t, "bar_end": stamp(self.session, missing_end),
                                            "row_status": "RSS_NO_USABLE_CLOSED_BAR_AT_LOCAL_PROCESSING"})
            self.cursor += 1
            self.missing_ticks += 1
        if m < 690 and self.first_am is None:
            self.first_am = m
        if 750 <= m < 925 and self.first_pm is None:
            self.first_pm = m
        auction = ("TERMINAL_AUCTION_MINUTE" if m in (690, 930) else
                   "OPENING_MIXED_MINUTE" if m in (self.first_am, self.first_pm) else "CONTINUOUS")
        t = end - 540
        # Integer logical kernel clock, not a PC/exchange receipt timestamp.
        token = {"t": t, "known_at": t, "source": KERNEL_SOURCE, "auction": auction,
                 **{k.lower(): self.coordinate(row[k]) for k in ("O", "H", "L", "C")}}
        state = self.engine.step(t, token, self.key)
        sf = self.state_features.push(state, {"scheduled_t": t, "bar_end": stamp(self.session, end),
                                             "row_status": "RSS_LOCAL_RECEIVED_CLOSED_APPROX_VA"})
        self.cursor += 1
        self.accepted_ticks += int(state["numeric_status"] == "ACCEPTED")
        self.last_received, self.last_state = received, state
        if m in self.regular:
            self.today.append([m] + [row[k] for k in ("O", "H", "L", "C", "Vo", "Va")])
        return sf, state


def consume_received_feed(runtime, p1, feed, selector_envelopes, previous_context,
                          *, previous_session, through):
    """Consume full prefixes in actual local receipt order. No orders.

    Persisted Watch data must not leak later refreshes into an earlier replay.
    Rebuild the causal Watch prefix from received Selector envelopes instead.
    """
    day = p1.session
    cutoff = forward.clock(through, day)
    receipt = feed.get("receipt", {})
    proxy = receipt.get("proxyReceipt", {})
    rows = feed.get("rows")
    need(receipt.get("schemaId") == "ARK_NO11_RSS_CHART50_OFFLINE_JOIN_V1" and
         receipt.get("sessionDate") == day and receipt.get("productionReady") is False and
         receipt.get("orderTransmission") is False and proxy.get("schemaId") ==
         "ARK_NO11_RSS_MARKET_APPROX_MINUTE_VA_SHADOW_V1" and
         proxy.get("nativeExactMinuteVaCertified") is False and
         proxy.get("orderTransmission") is False and isinstance(rows, list), "IMPORTED_FEED_CONTRACT")
    selected = proxy.get("selectedSymbols")
    need(isinstance(selected, list) and 1 <= len(selected) <= 50 and
         len(set(selected)) == len(selected), "SELECTED_SYMBOLS_INVALID")
    for code in selected:
        forward.symbol(code)
    need(previous_context.get("schemaId") == PREVIOUS_SCHEMA and
         previous_context.get("sessionDate") == day and
         previous_context.get("previousSession") == previous_session and
         previous_context.get("orderTransmission") is False and
         isinstance(previous_context.get("symbols"), dict), "PREVIOUS_CONTEXT_CONTRACT")
    need(receipt.get("approximateMinuteVaRows") == proxy.get("validOneMinuteProxyRows") == len(rows),
         "IMPORTED_FEED_ROW_COUNT")
    events, seen_rows = [], set()
    for row in rows:
        need(isinstance(row, dict) and row.get("Code") in selected and row.get("Date") == day and
             row.get("vaProvenance") == VA_SOURCE, "MINUTE_SOURCE_IDENTITY")
        m = minute(row.get("Time"))
        validate_prices(row)
        seen = forward.clock(row.get("knownAtJst"), day)
        close = forward.clock(stamp(day, m + 1), day)
        need(close <= seen <= cutoff, "UNCLOSED_OR_FUTURE_RECEIPT")
        key = (row["Code"], m)
        need(key not in seen_rows, "DUPLICATE_MINUTE")
        seen_rows.add(key)
        events.append((seen, 1, m, row["Code"], row))
    need(isinstance(selector_envelopes, list), "SELECTOR_RECEIPTS_REQUIRED")
    for envelope in selector_envelopes:
        need(isinstance(envelope, dict) and envelope.get("kind") == "selector", "SELECTOR_RECEIPT_INVALID")
        result = envelope.get("payload", {})
        seen = forward.clock(envelope.get("receivedAtJst"), day)
        decision = forward.clock(result.get("decisionTimestamp"), day)
        need(decision <= seen <= cutoff and all(e.get("symbol") in selected for e in result.get("watchEvents", [])),
             "SELECTOR_RECEIPT_OR_UNIVERSE_INVALID")
        events.append((seen, 0, 0, "", envelope))
    events.sort(key=lambda e: e[:4])
    contexts_hash = forward.digest(previous_context)
    with p1.db:
        p1.db.execute("INSERT OR IGNORE INTO metadata VALUES ('rss_previous_context',?)", (contexts_hash,))
        saved = p1.db.execute("SELECT value FROM metadata WHERE key='rss_previous_context'").fetchone()[0]
        need(saved == contexts_hash, "PREVIOUS_CONTEXT_CHANGED_ON_RESTART")
        p1.db.execute("CREATE TABLE IF NOT EXISTS rss_minute_inputs (source_key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL)")
        for row in rows:
            key = row["Code"] + "|" + row["Time"]
            fingerprint = forward.digest(row)
            old = p1.db.execute("SELECT fingerprint FROM rss_minute_inputs WHERE source_key=?", (key,)).fetchone()
            need(old is None or old[0] == fingerprint, "MINUTE_CHANGED_ON_RESTART")
            p1.db.execute("INSERT OR IGNORE INTO rss_minute_inputs VALUES (?,?)", (key, fingerprint))
    streams, blocked, watches, latest = {}, {}, {}, {}
    selector_seen, evaluated_here = set(), set()
    counts, statuses = Counter(), Counter()

    def evaluate_latest(code, evaluated_at):
        if code not in watches or code not in latest:
            return
        payload, sf = latest[code]
        stream = streams[code]
        watch = watches[code]
        m = minute(payload["Time"])
        identity = (code, m)
        if identity in evaluated_here or m + 1 < watch["selector_minute"] or m not in stream.regular:
            return
        observed = forward.clock(evaluated_at, day)
        if (observed - forward.clock(stamp(day, m + 1), day)).total_seconds() > 90:
            counts["staleCurrentBarsSkipped"] += 1
            return
        source_status = ("RSS_PROXY_PREVIOUS_ACTIVITY_PRESENT" if stream.previous_activity else
                         "RSS_PROXY_PREVIOUS_OHLC_ONLY_ACTIVITY_MISSING")
        event = forward.assemble_feature_event(
            runtime, watch, code, stream.today, stream.previous_activity, sf,
            bar_end=stamp(day, m + 1), evaluated_at=evaluated_at,
            feature_known_at=evaluated_at, state_known_at=payload["knownAtJst"],
            source_kind=SOURCE_KIND, source_status=source_status)
        result = p1.evaluate(event)
        evaluated_here.add(identity)
        counts["p1FeatureRows"] += 1
        statuses[result["status"]] += 1
        counts["idempotentDecisions"] += int(result["idempotentReplay"])

    for observed, kind, _, code, payload in events:
        if kind == 0:
            envelope = payload
            payload = envelope["payload"]
            p1.register_selector(payload)
            counts["selectorEvents"] += len(payload["watchEvents"])
            for event in payload["watchEvents"]:
                eid, code = event["selectorEventId"], event["symbol"]
                if eid in selector_seen:
                    continue
                selector_seen.add(eid)
                decision = forward.clock(event["decisionTimestamp"], day)
                dm = decision.hour * 60 + decision.minute
                newly_active = code not in watches
                if newly_active:
                    need(event["watchEventType"] == "WATCH_FIRST_SELECTION", "COMPLETE_SELECTOR_PREFIX_REQUIRED")
                    watches[code] = {"watch_key": day + "|" + code, "session": day,
                                     "selector_minute": dm, "selector_price": event["decisionPrice"],
                                     "refresh_minutes": []}
                else:
                    need(event["watchEventType"] == "WATCH_REFRESH", "SELECTOR_PREFIX_CONFLICT")
                    watches[code]["refresh_minutes"].append(dm)
                # Same-clock closed bar may arrive just BEFORE the first Selector.
                # Evaluate it after registration, without waiting another minute.
                if newly_active and code in latest and minute(latest[code][0]["Time"]) + 1 == dm:
                    evaluate_latest(code, envelope["receivedAtJst"])
            continue
        counts["receivedMinuteRows"] += 1
        if code in blocked:
            continue
        if code not in streams:
            context = previous_context["symbols"].get(code)
            try:
                streams[code] = ObservedStateStream(runtime, day, code, context, previous_session)
            except (ValueError, KeyError, TypeError):
                blocked[code] = "PREVIOUS_NORMALIZATION_SOURCE_UNAVAILABLE"
                continue
        sf, state = streams[code].push(payload)
        latest[code] = (payload, sf)
        counts["state9Rows"] += 1
        evaluate_latest(code, payload["knownAtJst"])
    return {"schemaId": "ARK_NO11_RSS_STATE9_P1_RECEIVED_STREAM_SUMMARY_V1",
            "sessionDate": day, "throughJst": through,
            "processingScope": "LOCAL_RECEIPT_ORDER_REPLAY_NOT_LIVE_SERVICE",
            "counts": dict(counts), "decisionStatusCounts": dict(statuses),
            "blockedSymbolCounts": dict(Counter(blocked.values())),
            "state9Symbols": len(streams), "missingScheduledStateTicks": sum(s.missing_ticks for s in streams.values()),
            "acceptedStateTicks": sum(s.accepted_ticks for s in streams.values()),
            "logicalKernelClockIsNotReceiptClock": True, "nativeExactMinuteVaCertified": False,
            "previousContextSha256": contexts_hash,
            "inputSha256": forward.digest([feed, selector_envelopes, previous_context]),
            "p1Session": p1.summary(),
            "privateModelsExecuted": p1.scorer.model_kind == "ORIGINAL_CORRECTED_P1_F5",
            "newFits": 0, "capitalExecuted": False, "exitExecuted": False,
            "brokerOrders": 0, "productionReady": False, "orderTransmission": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True)
    parser.add_argument("--through", required=True)
    parser.add_argument("--minute-feed", required=True, type=Path)
    parser.add_argument("--selector-events", required=True, type=Path)
    parser.add_argument("--previous-context", required=True, type=Path)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    args = parser.parse_args(argv)
    root = args.private_root.absolute()
    need(root != forward.REPO and forward.REPO not in root.parents and not root.is_symlink()
         and not any(p.is_symlink() for p in root.parents), "PRIVATE_OUTPUT_REQUIRED")
    feed, _ = read_json(args.minute_feed)
    selectors, _ = read_json(args.selector_events, 10_000_000)
    previous, _ = read_json(args.previous_context, 20_000_000)
    prior = previous_cash_session(forward.REPO, args.session)
    runtime = features.load_feature_runtime(forward.REPO)
    scorer = forward.FrozenP1Scorer(args.runtime_root, forward.REPO, args.session)
    engine = forward.ForwardP1Session(root / ("p1-shadow-" + args.session + ".sqlite"), scorer)
    try:
        summary = consume_received_feed(runtime, engine, feed, selectors, previous,
                                        previous_session=prior, through=args.through)
        encoded = (forward.dumps(summary) + "\n").encode("utf-8")
        output = root / ("rss-state9-p1-" + hashlib.sha256(encoded).hexdigest()[:16] + ".json")
        if output.exists():
            need(not output.is_symlink() and output.read_bytes() == encoded, "OUTPUT_CONFLICT")
        else:
            with output.open("xb") as handle:
                handle.write(encoded)
        print(forward.dumps(summary))
        print("NO11_RSS_STATE9_P1_PRIVATE_REPORT=" + str(output))
        print("ORDER_TRANSMISSION=False")
    finally:
        engine.close()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        text = str(exc)
        print(text if re.fullmatch(r"(?:P1_RSS|P1_FORWARD)_[A-Z0-9_]+", text) else "P1_RSS_INPUT_OR_RUNTIME_ERROR")
        raise SystemExit(2)
