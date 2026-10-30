#!/usr/bin/env python3
"""Ark No.1.1 local Shadow dashboard. Observation only; never starts trading.

Reads ONLY explicitly selected local launcher/account files and original
read-only Shadow receipts and SQLite ledger. No RSS, Excel, broker operations,
mutations, remote endpoints, or secrets. Bound to 127.0.0.1 only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
import sys
import threading
import time
import webbrowser
from urllib.parse import urlsplit

JST = timezone(timedelta(hours=9))
BASE = Path(__file__).resolve().parent
SYMBOL = re.compile(r"^[0-9A-Z]{4,5}(?:\.T)?$")
SESSION = re.compile(r"^20\d{2}-\d{2}-\d{2}$")
LAUNCH_SCHEMA = "ARK_SHADOW_ONECLICK_LAUNCH_STATUS_V1"
ACCOUNT_SCHEMA = "ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1"
REPORT_SCHEMA = "ARK_NO11_CONTINUOUS_RECEIVED_SHADOW_V1"
PORTFOLIO_SCHEMA = "ARK_NO11_DURABLE_SHADOW_PORTFOLIO_SUMMARY_V1"
MAX_RECEIPT = 2_000_000
MAX_LEDGER_BYTES = 64_000_000


def now() -> datetime:
    return datetime.now(tz=JST)


def number(value):
    """Only real observed, finite nonnegative numeric values, never inferred."""
    try:
        if isinstance(value, bool) or value is None:
            return None
        item = Decimal(str(value))
        if not item.is_finite():
            return None
        return item
    except (InvalidOperation, ValueError, TypeError):
        return None


def safe_int(value):
    return value if type(value) is int and 0 <= value <= 10_000_000 else None


def public_amount(value):
    item = number(value)
    return str(item) if item is not None else None


def timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else None
    except ValueError:
        return None


def fresh(value, max_age: int):
    parsed = timestamp(value)
    return bool(parsed and -30 <= (now() - parsed).total_seconds() <= max_age)


def read_json(file: Path, size=MAX_RECEIPT):
    try:
        if file.is_symlink() or not file.is_file() or file.stat().st_size > size:
            return None
        if file.stat().st_size < 2:
            return None
        data = json.loads(file.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else None
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None


def account_view(file: Path):
    result = dict(status="UNAVAILABLE", asOf=None, buyingPower=None,
                  marketValue=None, unrealizedPnl=None, totalAssets=None,
                  positionCount=None, positions=[], executions=[], orders=[])
    data = read_json(file)
    if not data or data.get("schemaId") != ACCOUNT_SCHEMA or data.get("readOnly") is not True or data.get("orderTransmission") is not False:
        return result
    if data.get("status") != "OBSERVED":
        result["status"] = "BLOCKED"
        return result
    snap = data.get("snapshot")
    if not isinstance(snap, dict) or snap.get("schemaId") != "ARK_ACCOUNT_READONLY_SNAPSHOT_V2":
        return result
    when = snap.get("captureCompletedAt")
    result["asOf"] = when if timestamp(when) else None
    if not fresh(when, 90):
        result["status"] = "STALE"
        return result
    buying = number(snap.get("buyingPower"))
    if buying is None or buying < 0:
        return result
    positions = snap.get("positions")
    executions = snap.get("executions")
    orders = snap.get("orders")
    if not all(isinstance(x, list) for x in (positions, executions, orders)):
        return result
    result["status"] = "OBSERVED"
    result["buyingPower"] = str(buying)
    result["positionCount"] = len(positions)
    visible = []
    mv_total, pnl_total = Decimal("0"), Decimal("0")
    mv_ok = pnl_ok = True
    for pos in positions[:100]:
        if not isinstance(pos, dict):
            continue
        symbol = str(pos.get("symbol", ""))[:8]
        if not SYMBOL.fullmatch(symbol):
            continue
        mv, pnl = number(pos.get("marketValue")), number(pos.get("unrealizedPnl"))
        qty = safe_int(pos.get("quantity"))
        if qty is None:
            continue
        mv_ok &= mv is not None
        pnl_ok &= pnl is not None
        if mv is not None:
            mv_total += mv
        if pnl is not None:
            pnl_total += pnl
        visible.append({"symbol": symbol, "quantity": qty,
                        "marketValue": public_amount(mv),
                        "unrealizedPnl": public_amount(pnl)})
    result["positions"] = visible[:25]
    result["marketValue"] = str(mv_total) if mv_ok and len(visible) == len(positions) else None
    result["unrealizedPnl"] = str(pnl_total) if pnl_ok and len(visible) == len(positions) else None
    # RSS buying power is NOT cash. RSS does not certify total brokerage equity.
    result["totalAssets"] = None
    recent = []
    for entry in executions[-30:]:
        if not isinstance(entry, dict):
            continue
        sym = str(entry.get("symbol", ""))[:8]
        if not SYMBOL.fullmatch(sym):
            continue
        recent.append({"symbol":sym, "side":str(entry.get("side",""))[:12],
                       "quantity":safe_int(entry.get("quantity")),
                       "price":public_amount(entry.get("price")),
                       "at":str(entry.get("executionDate",""))[:26]})
    result["executions"] = recent[-12:][::-1]
    result["orders"] = [{"symbol":str(o.get("symbol",""))[:8],
                         "status":str(o.get("status",""))[:30],
                         "quantity":safe_int(o.get("quantity"))}
                        for o in orders[-12:] if isinstance(o,dict)
                        and SYMBOL.fullmatch(str(o.get("symbol",""))[:8])]
    return result


def ledger_view(dbfile: Path, session: str):
    result = dict(status="UNAVAILABLE", cash=None, equity=None, exposure=None,
                  positionCount=None, buyIntents=None, sellIntents=None,
                  fills=[], positions=[], blocked=None, asOf=None)
    try:
        if dbfile.is_symlink() or not dbfile.is_file() or dbfile.stat().st_size > MAX_LEDGER_BYTES:
            return result
        # mode=ro + query_only, never PRAGMA journal_mode/WAL changes.
        uri = dbfile.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=0.5)
        try:
            conn.execute("PRAGMA query_only=ON")
            row = conn.execute("SELECT body FROM portfolio WHERE singleton=1").fetchone()
        finally:
            conn.close()
        state = json.loads(row[0])
        if (state.get("session") != session or
            state.get("productionReady") is not False or
            state.get("orderTransmission") is not False or
            not isinstance(state.get("positions"), dict) or
            not isinstance(state.get("orders"), dict)):
            return result
        cash = number(state.get("cash"))
        if cash is None or cash < 0:
            return result
        result["cash"] = str(cash)
        result["status"] = "OBSERVED_SIMULATOR_LEDGER"
        result["blocked"] = bool(state.get("reconciliationBlocked"))
        active_positions = []
        exposure = Decimal("0")
        every_mark_fresh = True
        for p in state["positions"].values():
            if not isinstance(p, dict):
                return dict(result, status="INVALID_LEDGER")
            qty = safe_int(p.get("quantity"))
            mark = number(p.get("mark"))
            sym = str(p.get("symbol", ""))[:8]
            if qty is None or qty == 0 or mark is None or not SYMBOL.fullmatch(sym):
                return dict(result, status="INVALID_LEDGER")
            mark_at = p.get("markKnownAt")
            every_mark_fresh &= fresh(mark_at, 180)
            exposure += qty * mark
            active_positions.append({"symbol":sym, "quantity":qty,
                                     "mark":str(mark),
                                     "marketValue":str(qty * mark),
                                     "markAsOf":mark_at})
        result["positions"] = active_positions
        result["positionCount"] = len(active_positions)
        result["exposure"] = str(exposure) if every_mark_fresh else None
        result["equity"] = str(cash + exposure) if every_mark_fresh else None
        result["asOf"] = state.get("clock")
        orders = []
        for o in state["orders"].values():
            if not isinstance(o, dict) or o.get("simulatedOnly") is not True:
                continue
            symbol = str(o.get("symbol",""))[:8]
            if not SYMBOL.fullmatch(symbol) or o.get("side") not in ("BUY","SELL"):
                continue
            orders.append({"symbol":symbol, "side":o["side"],
                           "status":str(o.get("status",""))[:25],
                           "quantity":safe_int(o.get("quantity")),
                           "filled":safe_int(o.get("filled")),
                           "at":str(o.get("createdAt",""))[:35],
                           "reason":str(o.get("reason",""))[:50],
                           "simulatedOnly":True})
        orders.sort(key=lambda x:x["at"],reverse=True)
        result["fills"] = orders[:30]
        result["buyIntents"] = sum(x["side"] == "BUY" for x in orders)
        result["sellIntents"] = sum(x["side"] == "SELL" for x in orders)
        return result
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, AttributeError):
        return result


def shadow_view(root: Path | None, session: str):
    result = dict(status="NOT_STARTED", updatedAt=None, pipeline=None,
                  portfolio=ledger_view(Path("/__ark_missing__"), session),
                  message="No verified Shadow output for this session")
    if root is None or not root.is_dir() or root.is_symlink():
        return result
    # Only the pinned date; never fall back to yesterday's sim totals.
    try:
        candidates = []
        for d in root.glob("session-" + session + "-*"):
            if d.is_dir() and not d.is_symlink():
                report = d / "inference" / "pipeline-latest-report.json"
                if report.is_file() and not report.is_symlink():
                    candidates.append((report.stat().st_mtime, d, report))
        if not candidates:
            return result
        _, folder, report = max(candidates, key=lambda x:x[0])
        payload = read_json(report)
        if not payload or payload.get("schemaId") != REPORT_SCHEMA or payload.get("productionReady") is not False:
            result["status"] = "INVALID_REPORT"
            return result
        if payload.get("shadowPortfolio") is not None:
            s = payload["shadowPortfolio"]
            if not isinstance(s,dict) or s.get("schemaId") != PORTFOLIO_SCHEMA or s.get("orderTransmission") is not False:
                result["status"] = "INVALID_PORTFOLIO_REPORT"
                return result
        stamp = payload.get("actualCompletedAtJst")
        result["updatedAt"] = stamp if timestamp(stamp) else None
        result["status"] = "OBSERVED" if fresh(stamp,120) else "STALE"
        result["pipeline"] = {
            "shadowExitConnected": payload.get("originalExitShadowConnected") is True,
            "entryHalted": bool(isinstance(payload.get("shadowPortfolio"),dict) and
                                payload["shadowPortfolio"].get("entryPipelineHalted") is True),
            "brokerOrders": 0,
            "ordersEnabled": False,
        }
        if payload.get("shadowPortfolio") is not None:
            result["portfolio"] = ledger_view(
                folder / "inference" / ("portfolio-shadow-" + session + ".sqlite"), session)
        result["message"] = "Historical read-only Shadow receipt; not broker-confirmed"
        return result
    except (OSError, ValueError):
        result["status"] = "UNREADABLE"
        return result


def select_account(primary: Path, secondary: Path | None):
    first = account_view(primary)
    if secondary is None or secondary == primary:
        return first
    second = account_view(secondary)
    candidates = [x for x in (first, second) if x["status"] == "OBSERVED"]
    if candidates:
        return max(candidates, key=lambda x: timestamp(x["asOf"]) or
                   datetime.min.replace(tzinfo=JST))
    if first["status"] == "STALE" or second["status"] == "STALE":
        return first if first["status"] == "STALE" else second
    return first


def launcher_view(file: Path):
    status = read_json(file, 250_000)
    if not status or status.get("schemaId") != LAUNCH_SCHEMA or status.get("orderTransmission") is not False:
        return {"status":"UNAVAILABLE","steps":{},"message":"Launcher status not verified"}
    steps = status.get("steps")
    return {"status": str(status.get("status", "UNKNOWN"))[:32],
            "steps": {str(k)[:32]:str(v)[:80] for k,v in steps.items()}
            if isinstance(steps,dict) else {},
            "message":str(status.get("message",""))[:180],
            "updatedAt":status.get("updatedAtJst")}


def build_status(config):
    return {
        "schemaId":"ARK_SHADOW_LOCAL_DASHBOARD_V1",
        "sessionDate":config.session,
        "updatedAtJst":now().isoformat(timespec="seconds"),
        "mode":"LOCAL_OBSERVATION_ONLY",
        "orderTransmission":False,
        "brokerOrdersAuthorized":False,
        "launcher":launcher_view(config.launch_status_file),
        "account":select_account(config.account_file, config.account_secondary_file),
        "shadow":shadow_view(config.shadow_root,config.session),
        "disclaimer":"Real account totals unavailable unless confirmed by RSS. Paper-only ledger values never imply broker orders."
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ArkShadowReadOnly/1"
    sys_version = ""
    def log_message(self, fmt, *args):
        return # No account data or request query can leak to console logs.

    def send(self, code, body, mime):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        host = self.headers.get("Host","")
        if host not in (f"127.0.0.1:{self.server.server_port}",
                        f"localhost:{self.server.server_port}"):
            return self.send(403,b"Forbidden", "text/plain; charset=utf-8")
        name = urlsplit(self.path).path
        if name == "/":
            return self.send(200, (BASE/"index.html").read_bytes(), "text/html; charset=utf-8")
        if name == "/static/app.css":
            return self.send(200, (BASE/"app.css").read_bytes(), "text/css; charset=utf-8")
        if name == "/static/app.js":
            return self.send(200, (BASE/"app.js").read_bytes(), "text/javascript; charset=utf-8")
        if name == "/api/health":
            health = json.dumps({"status":"READ_ONLY","sessionDate":self.server.config.session,
                                 "orderTransmission":False}).encode("utf-8")
            return self.send(200,health,"application/json; charset=utf-8")
        if name == "/api/status":
            result = json.dumps(build_status(self.server.config), ensure_ascii=False, separators=(",",":")).encode("utf-8")
            return self.send(200,result,"application/json; charset=utf-8")
        return self.send(404,b"Not found","text/plain; charset=utf-8")

    def do_POST(self):
        return self.send(405,b"Read only","text/plain; charset=utf-8")
    do_PUT = do_PATCH = do_DELETE = do_POST


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port",type=int,default=8768)
    parser.add_argument("--session",required=True)
    parser.add_argument("--launch-status-file",type=Path,required=True)
    parser.add_argument("--account-file",type=Path,required=True)
    parser.add_argument("--account-secondary-file",type=Path)
    parser.add_argument("--shadow-root",type=Path)
    parser.add_argument("--open-browser",action="store_true")
    args = parser.parse_args(argv)
    if not SESSION.fullmatch(args.session) or not 1024 <= args.port <= 65535:
        parser.error("Invalid date or port")
    for p in (args.launch_status_file,args.account_file,args.account_secondary_file,args.shadow_root):
        if p is not None and not p.is_absolute():
            parser.error("Only absolute private data paths are accepted")
    args.launch_status_file = args.launch_status_file.resolve()
    args.account_file = args.account_file.resolve()
    args.account_secondary_file = args.account_secondary_file.resolve() if args.account_secondary_file else None
    args.shadow_root = args.shadow_root.resolve() if args.shadow_root else None
    server = ThreadingHTTPServer(("127.0.0.1",args.port),Handler)
    server.daemon_threads = True
    server.config = args
    print("ARK_SHADOW_LOCAL_URL=http://127.0.0.1:%s/" % args.port,flush=True)
    print("ARK_SHADOW_ORDER_TRANSMISSION=False",flush=True)
    if args.open_browser:
        threading.Timer(0.5,lambda:webbrowser.open("http://127.0.0.1:%s/" % args.port)).start()
    # A prior-date session may never be reused the next trading morning.
    def end_at_jst_day_rollover():
        while now().date().isoformat() == args.session:
            time.sleep(20)
        server.shutdown()
    threading.Thread(target=end_at_jst_day_rollover, daemon=True).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
