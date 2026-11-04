#!/usr/bin/env python3
"""Single-pass, read-only manual broker/ledger continuation review.

Supports zero OR nonzero attributed positions/orders without assuming that
manual checking authorizes new purchases, creates a broker ACK, or clears a
stop/ledger marker. A collector restart requires a separate approved supervisor.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote

JST = timezone(timedelta(hours=9))
SHA = re.compile(r"[a-f0-9]{64}\Z")
DAY = re.compile(r"20\d\d-\d\d-\d\d\Z")
PHASES = {
    "ACKNOWLEDGED": {"執行待ち", "執行中", "受付", "待機中"},
    "PARTIAL": {"出来有", "取消中（出来有）"},
    "FILLED": {"約定"},
    "CANCELLED": {"取消済（出来無）", "取消済（出来有）"},
    "EXPIRED": {"出来ず（出来無）", "出来ず（出来有）"},
}


def need(ok: bool, reason: str):
    if not ok:
        raise ValueError("NO11_RECONNECT_" + reason)


def num(v):
    need(type(v) in (int, float) and float(v).is_integer() and 0 <= v <= 1_000_000_000,
         "BROKER_INTEGER_REQUIRED")
    return int(v)


def symbol(v):
    need(type(v) is str and re.fullmatch(r"(?:[0-9A-Z]{4}|[0-9A-Z]{5})(?:\.T)?", v) is not None,
         "BROKER_SYMBOL")
    s = v.split(".")[0]
    return s[:-1] if len(s) == 5 and s.endswith("0") else s


def date_jst(v):
    need(type(v) is str, "BROKER_CLOCK")
    dt = datetime.fromisoformat(v)
    need(dt.utcoffset() == timedelta(hours=9), "BROKER_CLOCK_JST")
    return dt


def observation_ok(fresh, session: str, now: datetime):
    need(type(fresh) is dict and fresh.get("status") == "OBSERVED" and
         fresh.get("readOnly") is True and fresh.get("orderTransmission") is False,
         "SOURCE_NOT_READONLY_OBSERVED")
    ext = fresh.get("brokerObservation")
    need(type(ext) is dict and ext.get("schemaId") == "ARK_NO11_BROKER_OBSERVATION_V1"
         and ext.get("status") == "OBSERVED" and
         ext.get("completeTables") is True and
         ext.get("sameSnapshotVerified") is True and
         ext.get("rowsTruncated") is False and
         ext.get("orderTransmission") is False,
         "TABLES_NOT_COMPLETE")
    finished = date_jst(ext.get("captureCompletedAt"))
    need(finished.date().isoformat() == session and
         now.date().isoformat() == session and
         0 <= (now - finished).total_seconds() <= 90,
         "BROKER_SOURCE_NOT_FRESH")
    account = fresh.get("snapshot")
    need(type(account) is dict, "ACCOUNT_MISSING")
    for key in ("orders", "executions", "positions"):
        need(type(account.get(key)) is list and type(ext.get(key)) is list,
             "BROKER_TABLE_SHAPE")
        # This is additionally verified by the original Excel double-read
        # collector. An exact parsed representation is required again here.
        def normalize(items):
            return json.dumps(items, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        need(normalize(account[key]) == normalize(ext[key]), "BROKER_SNAPSHOT_CHANGED")
    return ext


def assess(ledger, fresh, session: str, *, manual_confirmed=False, now=None):
    now = now or datetime.now(JST)
    base = {"schemaId": "ARK_NO11_MANUAL_RECONNECT_REVIEW_V1",
            "sessionDate": session, "collectorRestartCandidate": False,
            "newBuyAuthorized": False, "tradeRetried": False,
            "haltMarkerCleared": False, "orderResendAllowed": False,
            "ledgerModified": False, "orderTransmission": False}
    try:
        need(type(session) is str and DAY.fullmatch(session) is not None,
             "SESSION_DATE")
        need(now.utcoffset() == timedelta(hours=9) and now.date().isoformat() == session,
             "REVIEW_NOT_TODAY")
        need(type(ledger) is dict and ledger.get("sessionDate") == session and
             type(ledger.get("orders")) is dict and
             type(ledger.get("positions")) is dict and
             type(ledger.get("commands")) is dict, "LEDGER_SCOPE")
        ext = observation_ok(fresh, session, now)
        orders = ledger["orders"]
        positions = ledger["positions"]
        commands = ledger["commands"]
        # Never auto-resend an unacknowledged or pre-dispatch command.
        for c in commands.values():
            need(type(c) is dict and type(c.get("command")) is dict,
                 "COMMAND_SHAPE")
            need(c.get("state") not in {"IN_FLIGHT", "RETURNED", "UNKNOWN", "PREPARED"}
                 or c.get("brokerObserved") is True and c.get("state") != "PREPARED",
                 "COMMAND_NOT_RESOLVED")
        broker_by_number = {}
        for row in ext["orders"]:
            need(type(row) is dict and type(row.get("orderNumber")) is str and
                 re.fullmatch(r"[1-9]\d{0,31}", row["orderNumber"]),
                 "BROKER_ORDER_ID")
            need(row["orderNumber"] not in broker_by_number, "DUPLICATE_BROKER_ORDER")
            broker_by_number[row["orderNumber"]] = row
        rss_by_id = {}
        for row in ext["idRows"]:
            need(type(row) is dict and type(row.get("rssOrderId")) is int,
                 "RSS_ROW_SHAPE")
            need(row["rssOrderId"] not in rss_by_id, "DUPLICATE_RSS_ID")
            rss_by_id[row["rssOrderId"]] = row
        seen_numbers = set()
        execution_need = {}
        ark_symbols = set()
        for o in orders.values():
            need(type(o) is dict and o.get("phase") != "UNKNOWN",
                 "UNKNOWN_ORDER")
            phase = o.get("phase")
            if phase == "LOCAL_WITHDRAWN":
                need(o.get("brokerOrderNumber") is None and
                     o.get("cumulativeQuantity") == 0, "LOCAL_WITHDRAW_CONFLICT")
                continue
            need(phase in PHASES, "ORDER_PHASE_UNSETTLED")
            number = o.get("brokerOrderNumber")
            need(type(number) is str and re.fullmatch(r"[1-9]\d{0,31}", number) and
                 number not in seen_numbers, "LEDGER_ORDER_NOT_BOUND")
            seen_numbers.add(number)
            need(number in broker_by_number, "BROKER_ORDER_MISSING")
            observed = broker_by_number[number]
            side = "買付" if o.get("side") == "BUY" else "売付"
            sym = symbol(o.get("symbol"))
            ark_symbols.add(sym)
            need(o.get("side") in ("BUY", "SELL") and
                 symbol(observed.get("symbol")) == sym and
                 observed.get("account") == o.get("account") and
                 observed.get("side") == side and observed.get("trade") == "現物" and
                 num(observed.get("quantity")) == o.get("quantity") and
                 num(observed.get("filledQty")) == o.get("cumulativeQuantity") and
                 observed.get("status") in PHASES[phase],
                 "ORDER_NOT_MATCHED")
            rss = rss_by_id.get(o.get("rssOrderId"))
            need(rss is not None and rss.get("orderNumber") == number,
                 "RSS_ID_TO_ORDER_UNVERIFIED")
            if o["cumulativeQuantity"] > 0:
                k = (sym, o.get("account"), side)
                execution_need[k] = execution_need.get(k, 0) + o["cumulativeQuantity"]
        for r in ext["orders"]:
            if (r["orderNumber"] not in seen_numbers and
                r.get("status") not in {"約定", "取消済（出来無）",
                                       "取消済（出来有）", "出来ず（出来無）", "出来ず（出来有）"}):
                need(False, "EXTERNAL_ACTIVE_ORDER_NEEDS_REVIEW")
        sums = {}
        for row in ext["executions"]:
            need(type(row) is dict, "EXECUTION_SHAPE")
            key = (symbol(row.get("symbol")), row.get("account"), row.get("side"))
            sums[key] = sums.get(key, 0) + num(row.get("quantity"))
        for k, q in execution_need.items():
            need(sums.get(k) == q, "EXECUTION_QUANTITY_MISMATCH")
        broker_pos = {}
        for p in ext["positions"]:
            need(type(p) is dict, "BROKER_POSITION_SHAPE")
            key = (symbol(p.get("symbol")), p.get("account"))
            broker_pos[key] = broker_pos.get(key, 0) + num(p.get("quantity"))
        owned = {}
        for p in positions.values():
            need(type(p) is dict and type(p.get("quantity")) is int and
                 p["quantity"] >= 0, "OWNED_POSITION_SHAPE")
            if p["quantity"] == 0:
                continue
            key = (symbol(p.get("symbol")), p.get("account"))
            owned[key] = owned.get(key, 0) + p["quantity"]
            ark_symbols.add(key[0])
        need(len(owned) <= 3, "MAX3_EXPOSURE")
        for k, qty in owned.items():
            need(broker_pos.get(k) == qty, "ARK_POSITION_QUANTITY_MISMATCH")
        # A same-symbol manual holding cannot be silently attributed to ARK.
        for k, qty in broker_pos.items():
            if k[0] in ark_symbols:
                need(k in owned and qty == owned[k], "MANUAL_HOLDING_OVERLAP")
        result = {**base, "reason": "BROKER_AND_LEDGER_MATCH",
                  "matchedOrders": len(seen_numbers),
                  "matchedArkPositions": len(owned),
                  "manualConfirmationRequired": not bool(manual_confirmed),
                  "state": "MANUAL_CONFIRMATION_REQUIRED" if not manual_confirmed
                           else "COLLECTOR_RESTART_REVIEW_ELIGIBLE"}
        # Audit can attest observed broker/ledger equality, not collector
        # closure, process ownership, restored EXIT, renewed market data,
        # discretionary new-buy permission or actual restart.
        result["collectorRestartCandidate"] = bool(manual_confirmed)
        result["exitManagementMustRemainAvailable"] = bool(owned)
        return result
    except (ValueError, KeyError, TypeError, OverflowError) as e:
        message = str(e)
        reason = message if re.fullmatch(r"NO11_RECONNECT_[A-Z0-9_]+", message) else "NO11_RECONNECT_UNVERIFIED_INPUT"
        return {**base, "state": "BLOCKED",
                "reason": reason, "manualConfirmationRequired": True}


def ledger_readonly(db: Path, engine: Path):
    # Exactly one local state record; never creates missing SQLite files,
    # alters order events or opens the engine's writable ledger class.
    db = Path(db).resolve(strict=True)
    need(db.suffix == ".sqlite" and db.name.startswith("broker-execution-"),
         "LEDGER_FILE_NAME")
    ledger_src = Path(engine) / "tools" / "no11_broker_execution_ledger.py"
    need(ledger_src.is_file(), "LEDGER_VALIDATOR_MISSING")
    spec = importlib.util.spec_from_file_location("ark_no11_ledger_hash_only", ledger_src)
    need(spec is not None and spec.loader is not None, "LEDGER_VALIDATOR_IMPORT")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    uri = "file:" + quote(db.as_posix(), safe="/:") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=3)
    try:
        con.execute("PRAGMA query_only = ON")
        rows = con.execute("SELECT body,sha FROM broker_state WHERE singleton=1").fetchall()
        need(len(rows) == 1, "LEDGER_DB_STATE_MISSING")
        body, sha = rows[0]
        obj = json.loads(body)
        need(type(obj) is dict and SHA.fullmatch(sha) and m.digest(obj) == sha,
             "LEDGER_DB_SHA")
        return obj
    finally:
        con.close()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger-db", type=Path, required=True)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--manual-confirmed", action="store_true")
    args = parser.parse_args(argv)
    base = {"schemaId": "ARK_NO11_MANUAL_RECONNECT_REVIEW_V1",
            "state": "BLOCKED", "reason": "SOURCE_UNVERIFIED",
            "collectorRestartCandidate": False, "newBuyAuthorized": False,
            "orderResendAllowed": False, "orderTransmission": False}
    try:
        raw = args.observation.read_bytes()
        need(0 < len(raw) < 25_000_000 and not args.observation.is_symlink(),
             "OBSERVATION_FILE")
        fresh = json.loads(raw.decode("utf-8-sig"))
        led = ledger_readonly(args.ledger_db, args.engine)
        result = assess(led, fresh, args.session, manual_confirmed=args.manual_confirmed)
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error):
        result = base
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["state"] in ("MANUAL_CONFIRMATION_REQUIRED", "COLLECTOR_RESTART_REVIEW_ELIGIBLE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
