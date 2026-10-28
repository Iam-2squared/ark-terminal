#!/usr/bin/env python3
"""Explicit-opt-in, personal research, Yahoo Finance weekly DAILY source only.

This uses the UNOFFICIAL third-party yfinance client, NOT Yahoo Japan page
scraping and NOT a licensed trading feed. It does not authenticate to any
broker, poll live quotes, retrain Frozen models, change original RSS sources,
or authorize production/real orders. Only use when your data-use rights allow.
No proxies, CAPTCHA bypass, automatic 429 retries, or high concurrency.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

JST = timezone(timedelta(hours=9))
SCHEMA = "ARK_NO11_YAHOO_WEEKLY_HISTORY_OBSERVATION_V1"
SOURCE = "YFINANCE_UNOFFICIAL_PERSONAL_RESEARCH_DAILY"
PIN = "22d31026c76dd1a555a2deed2d2b5743004687a239dcc8856b5abeae47782056"
SYMBOL = re.compile(r"[0-9A-Z]{4}\.T")
ASOF = re.compile(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}")

def need(ok, code):
    if not ok:
        raise ValueError("NO11_YAHOO_" + code)

def stamp():
    return datetime.now(JST).isoformat(timespec="milliseconds")

def private_path(raw, folder=False):
    p = Path(raw).absolute()
    repo = Path(__file__).resolve().parents[3]
    need(p != repo and repo not in p.parents and
         not p.is_symlink() and not any(x.is_symlink() for x in p.parents),
         "PRIVATE_PATH_REQUIRED")
    need(p.is_dir() if folder else p.is_file(), "SOURCE_NOT_PRESENT")
    return p

def original_symbols(source_plan):
    p = private_path(source_plan)
    obj = json.loads(p.read_text("utf-8-sig"))
    need(obj.get("schemaId") == "ARK_NO11_RSS_DAILY_CENSUS_PLAN_V1" and
         obj.get("asOfSession") == "2026-10-26" and
         obj.get("sourceSymbolsSha256") == PIN and
         type(obj.get("symbols")) is list and len(obj["symbols"]) == 4328 and
         len(set(obj["symbols"])) == 4328 and
         all(type(x) is str and SYMBOL.fullmatch(x) for x in obj["symbols"]),
         "ORIGINAL_4328_SYMBOL_PIN_REQUIRED")
    plan_id = obj.get("planId")
    body = {k: v for k, v in obj.items() if k != "planId"}
    content = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    need(plan_id == hashlib.sha256(content.encode()).hexdigest(),
         "ORIGINAL_4328_PLAN_HASH_INVALID")
    return obj["symbols"], plan_id

def decimal(raw, allow_zero=False):
    try:
        value = Decimal(str(raw))
    except (TypeError, ValueError, InvalidOperation):
        return None
    if not value.is_finite() or value < 0 or (not allow_zero and value == 0):
        return None
    text = format(value, "f")
    if len(text) > 96 or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", text):
        return None
    return text

def normalized_rows(rows, asof):
    out, seen = [], set()
    for row in rows:
        session = row.get("session")
        need(type(session) is str and ASOF.fullmatch(session), "ROW_DATE_INVALID")
        try:
            date.fromisoformat(session)
        except ValueError:
            raise ValueError("NO11_YAHOO_ROW_DATE_INVALID") from None
        # Yahoo may send a current incomplete daily bar. Never import it
        # into the frozen weekly prior-close frame.
        if session > asof:
            continue
        need(session not in seen, "DUPLICATE_DAILY_DATE")
        seen.add(session)
        close = decimal(row.get("close"))
        need(close is not None, "CLOSE_INVALID")
        out.append({"session": session, "close": close})
    out.sort(key=lambda x: x["session"])
    return out

def observation(symbol, asof, rows, status, start, finish):
    need(SYMBOL.fullmatch(symbol) and ASOF.fullmatch(asof) and
         status in ("OBSERVED", "UNAVAILABLE"), "OBSERVATION_ARGS_INVALID")
    filtered = normalized_rows(rows, asof) if status == "OBSERVED" else []
    need((status == "OBSERVED") == bool(filtered), "OBSERVATION_STATUS_INVALID")
    return {"schemaId": SCHEMA, "symbol": symbol, "asOfSession": asof,
      "sourceProvider": SOURCE, "sourceInterval": "1d",
      "autoAdjustRequested": False, "usesYahooCloseNotAdjClose": True,
      "corporateActionPriceBasisCertified": False, "splitAdjustmentCertified": False,
      "originalVendorDecimalCertified": False,
      "requestedAtJst": start, "receivedAtJst": finish, "status": status,
      "rows": filtered, "productionReady": False, "orderTransmission": False}

def write_immutable(root, value):
    payload = (json.dumps(value, ensure_ascii=False,
       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    stem = value["symbol"].replace(".", "_")
    dest = root / (stem + "-" + digest + ".json")
    if dest.exists():
        need(dest.read_bytes() == payload and not dest.is_symlink(), "OUTPUT_CONFLICT")
    else:
        with dest.open("xb") as out:
            out.write(payload); out.flush(); os.fsync(out.fileno())
    return dest

def ticker_rows(frame):
    if frame is None or getattr(frame, "empty", True):
        return []
    result = []
    for index, row in frame.iterrows():
        val = row.get("Close")
        if decimal(val) is None:
            continue
        d = index.date().isoformat() if hasattr(index, "date") else str(index)[:10]
        result.append({"session": d, "close": val})
    return result

def fetch_batch(yf, tickers, since, until):
    # yfinance is UNOFFICIAL. No retries on throttling or failed HTTP requests.
    result = yf.download(tickers=tickers, start=since, end=until,
      interval="1d", group_by="ticker", auto_adjust=False,
      back_adjust=False, repair=False, progress=False,
      threads=False, actions=True, timeout=20, multi_level_index=True)
    return result

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--original-plan", required=True)
    ap.add_argument("--asof", required=True)
    ap.add_argument("--private-root", required=True)
    ap.add_argument("--personal-research-terms-acknowledged", action="store_true")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--pause-seconds", type=float, default=5.0)
    args = ap.parse_args(argv)
    need(args.personal_research_terms_acknowledged,
      "UNOFFICIAL_PERSONAL_RESEARCH_RIGHTS_ACKNOWLEDGEMENT_REQUIRED")
    need(ASOF.fullmatch(args.asof), "ASOF_INVALID")
    asof = date.fromisoformat(args.asof)
    now = datetime.now(JST)
    need(asof.weekday() == 4 and
         now >= datetime(asof.year, asof.month, asof.day, 19, tzinfo=JST),
         "FRIDAY_SOURCE_NOT_PUBLISHED_YET")
    need(1 <= args.batch_size <= 32 and 3 <= args.pause_seconds <= 60,
         "BOUNDED_REQUEST_PARAMETERS_REQUIRED")
    symbols, original_id = original_symbols(args.original_plan)
    root = Path(args.private_root).absolute()
    repo = Path(__file__).resolve().parents[3]
    need(root != repo and repo not in root.parents and
         not root.is_symlink() and not any(x.is_symlink() for x in root.parents),
         "PRIVATE_ROOT_REQUIRED")
    root.mkdir(parents=True, exist_ok=True)
    sources = root / ("yahoo-weekly-" + args.asof + "-" + original_id[:16])
    sources.mkdir(exist_ok=True)
    source_dir = sources / "sources"
    source_dir.mkdir(exist_ok=True)
    need(not sources.is_symlink() and not source_dir.is_symlink(),
         "SOURCE_DIRECTORY_LINK")
    # Existing outputs are immutable. Resume only symbols not already present.
    saved = set()
    for item in source_dir.iterdir():
        need(item.is_file() and not item.is_symlink(), "SOURCE_DIR_FOREIGN_FILE")
        m = re.fullmatch(r"([0-9A-Z]{4})_T-([0-9a-f]{64})\.json", item.name)
        need(m is not None and
             hashlib.sha256(item.read_bytes()).hexdigest() == m[2],
             "EXISTING_SOURCE_CORRUPT")
        symbol = m[1] + ".T"
        need(symbol not in saved and symbol in symbols, "DUPLICATE_OR_FOREIGN_SYMBOL")
        saved.add(symbol)
    remaining = [x for x in symbols if x not in saved]
    print("NO11_YAHOO_WEEKLY_RESUMED=" + str(len(saved)) + "/4328", flush=True)
    if not remaining:
        print("NO11_YAHOO_WEEKLY_SOURCE_DIR=" + str(sources))
        print("ORDER_TRANSMISSION=False")
        return
    try:
        import yfinance as yf
    except ImportError as error:
        raise ValueError("NO11_YAHOO_SEPARATE_VENV_YFINANCE_REQUIRED") from error
    start = (asof - timedelta(days=175)).isoformat()
    end = (asof + timedelta(days=1)).isoformat()  # Yahoo end is exclusive
    for start_idx in range(0, len(remaining), args.batch_size):
        batch = remaining[start_idx:start_idx + args.batch_size]
        started = stamp()
        try:
            data = fetch_batch(yf, batch, start, end)
        except Exception as error:
            # Stop on throttling/outage, never mask a rate-limit as UNKNOWN.
            raise ValueError("NO11_YAHOO_VENDOR_FETCH_FAILED_NO_RETRY") from error
        finished = stamp()
        available = {}
        for symbol in batch:
            try:
                frame = data[symbol] if hasattr(data, "__getitem__") else None
                available[symbol] = ticker_rows(frame)
            except (KeyError, TypeError, ValueError):
                available[symbol] = []
        observed = sum(bool(v) for v in available.values())
        need(observed > 0, "VENDOR_ALL_EMPTY_STOP_NO_NEW_RECEIPTS")
        # Preserve source failures as explicit UNKNOWN, NEVER substitute RSS.
        for symbol in batch:
            value = observation(symbol, args.asof, available[symbol],
                "OBSERVED" if available[symbol] else "UNAVAILABLE",
                started, finished)
            write_immutable(source_dir, value)
        print(f"NO11_YAHOO_WEEKLY_PROGRESS={len(saved)+min(len(remaining),start_idx+len(batch))}/4328"
              f"|OBSERVED_IN_BATCH={observed}", flush=True)
        if start_idx + len(batch) < len(remaining):
            time.sleep(args.pause_seconds)
    print("NO11_YAHOO_WEEKLY_SOURCE_DIR=" + str(sources))
    print("NO11_YAHOO_WEEKLY_PRICE_BASIS=CLOSE_SPLIT_ADJUSTMENT_UNCERTIFIED")
    print("NO11_YAHOO_WEEKLY_EXTERNAL_REVIEW=NOT_PERFORMED")
    print("ORDER_TRANSMISSION=False")

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as error:
        code = str(error)
        if not re.fullmatch(r"NO11_YAHOO_[A-Z0-9_]+", code):
            code = "NO11_YAHOO_SOURCE_OR_VENDOR_FAILURE"
        print("NO11_YAHOO_WEEKLY=BLOCKED|" + code, file=sys.stderr)
        print("ORDER_TRANSMISSION=False")
        sys.exit(2)
