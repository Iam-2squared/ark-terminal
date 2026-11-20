#!/usr/bin/env python3
"""Ark Terminal 2.0 LIVE-only local read model.

A strictly READ-ONLY HTTP UI for the EXISTING No.1.1 real broker ledger.
This module never opens Excel, invokes RSS, loads Shadow/synthetic ledgers,
sets operator approval, or controls BUY/SELL/STOP. The approved frozen UI
prototype is NOT modified. The companion HTML uses its approved stylesheet.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

JST = timezone(timedelta(hours=9))
POINTER = "ARK_NO11_RECEIVED_ACTIVE_RUN_V1"
CONTRACT = "ARK_NO11_RECEIVED_RUN_CONTRACT_V1"
BROKER = "ARK_NO11_BROKER_EXECUTION_REPORT_V1"
LEDGER = "ARK_NO11_BROKER_EXECUTION_LEDGER_SNAPSHOT_V1"
DAY = re.compile(r"^20\d\d-\d\d-\d\d$")
RUN = re.compile(r"^session-20\d\d-\d\d-\d\d-[a-f0-9]{32}$")
SYMBOL = re.compile(r"^[0-9A-Z]{4}\.T$")
MONEY = re.compile(r"^-?\d+(?:\.\d{1,6})?$")
MAX_JSON = 4_000_000


def now_jst():
    return datetime.now(JST)


def read_json(path, limit=MAX_JSON):
    if path.is_symlink() or not path.is_file():
        return None
    size = path.stat().st_size
    if not 2 <= size <= limit:
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        return obj if isinstance(obj, dict) else None
    except (OSError, ValueError, UnicodeError):
        return None


def checksum(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def unseal(path, schema, session):
    obj = read_json(path, 1_000_000)
    if not obj or obj.get("schemaId") != schema or obj.get("sessionDate") != session:
        return None
    body = dict(obj)
    sha = body.pop("sha256", None)
    if body.get("orderTransmission") is not False or body.get("productionReady") is not False:
        return None
    return body if isinstance(sha, str) and sha == checksum(body) else None


def finite_money(value):
    return value if type(value) is str and MONEY.fullmatch(value) else None


def nonnegative_int(value):
    return value if type(value) is int and 0 <= value <= 10_000_000 else None


def timestamp(value):
    if not isinstance(value, str) or len(value) > 48:
        return None
    try:
        result = datetime.fromisoformat(value)
        return result if result.utcoffset() == timedelta(hours=9) else None
    except (TypeError, ValueError, OverflowError):
        return None


def symbol(value):
    return value if type(value) is str and SYMBOL.fullmatch(value) else None


def clean_status(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Z0-9_]{1,70}", value) else "UNKNOWN"


def empty(session, status):
    return {"schemaId": "ARK_NO11_UI2_LIVE_ONLY_READ_MODEL_V1",
            "sessionDate": session, "status": status,
            "asOf": None, "realBrokerReportObserved": False,
            "realOrderAccepted": None, "realOrderFilled": None,
            "liveConfigurationSeen": False, "sourceCurrent": False,
            "buyingPowerVerified": False, "securitiesOnlyCashReviewed": False,
            "entryHalted": None, "haltReasons": [],
            "positionCount": None, "cashJpy": None,
            "availableCashJpy": None, "reservedCashJpy": None,
            "newBuysAllowed": False, "orders": [], "positions": [],
            "selectorIntents": [], "performanceVerified": False,
            "unresolvedCommandCount": None, "simulatedDataIncluded": False,
            "uiCanPlaceOrders": False, "uiCanStopEngine": False}


def project(report, session, clock=None):
    """Never turn a configured transport into proof of an accepted/filled order."""
    result = empty(session, "INVALID_REAL_ONLY_REPORT")
    if not isinstance(report, dict) or report.get("schemaId") != BROKER:
        return result
    if (report.get("sessionDate") != session or report.get("mode") != "LIVE"
            or report.get("evidenceMode") != "BROKER_OBSERVATION"
            or report.get("orderTransmission") is not True
            or report.get("realFillsAppliedToShadow") is not False):
        return result
    ledger = report.get("ledger")
    if (not isinstance(ledger, dict) or ledger.get("schemaId") != LEDGER
            or ledger.get("sessionDate") != session
            or ledger.get("evidenceMode") != "BROKER_OBSERVATION"
            or ledger.get("orderTransmission") is not False
            or ledger.get("productionReady") is not False):
        return result
    at = timestamp(report.get("evaluatedAtJst"))
    moment = clock or now_jst()
    if moment.date().isoformat() != session or at is None:
        return empty(session, "SESSION_OR_TIMESTAMP_MISMATCH")
    age = (moment - at).total_seconds()
    if not -5 <= age <= 90:
        return empty(session, "BROKER_REPORT_STALE")
    result.update(status="BROKER_REPORT_OBSERVED",
                  asOf=report["evaluatedAtJst"], realBrokerReportObserved=True,
                  liveConfigurationSeen=True, sourceCurrent=report.get("sourceCurrent") is True,
                  buyingPowerVerified=report.get("buyingPowerRefreshVerified") is True,
                  securitiesOnlyCashReviewed=report.get("securitiesOnlyOpeningCashReviewed") is True,
                  entryHalted=report.get("entryPipelineHalted") is True,
                  newBuysAllowed=(ledger.get("newBuysAllowed") is True
                                  and report.get("entryPipelineHalted") is False
                                  and report.get("sourceCurrent") is True
                                  and report.get("buyingPowerRefreshVerified") is True),
                  haltReasons=[clean_status(x) for x in report.get("entryHaltReasons", [])[:8]
                               if isinstance(x, str)] if type(report.get("entryHaltReasons")) is list else [])
    positions = ledger.get("positions")
    orders = ledger.get("orders")
    commands = ledger.get("commands")
    if (not isinstance(positions, dict) or not isinstance(orders, dict)
            or not isinstance(commands, dict)
            or len(positions) > 500 or len(orders) > 5000 or len(commands) > 5000):
        return empty(session, "LEDGER_SHAPE_INVALID")
    result["unresolvedCommandCount"] = len(ledger.get("unresolvedCommands", [])) if type(ledger.get("unresolvedCommands")) is list else None
    active = []
    for v in positions.values():
        if not isinstance(v, dict):
            return empty(session, "POSITION_SHAPE_INVALID")
        q = nonnegative_int(v.get("quantity"))
        if q is None:
            return empty(session, "POSITION_QUANTITY_INVALID")
        if q and symbol(v.get("symbol")):
            active.append({"symbol": v["symbol"], "quantity": q,
                           "knownCostJpy": finite_money(v.get("knownCostJpy"))
                           if v.get("costComplete") is True else None,
                           "fillTimeVerified": v.get("fillTimeVerified") is True})
        elif q:
            return empty(session, "POSITION_SYMBOL_INVALID")
    if len(active) > 3 or result["positionCount"] not in (None,):
        return empty(session, "MAX3_ARK_POSITION_CONFLICT")
    if ledger.get("positionCount") != len(active):
        return empty(session, "POSITION_COUNT_MISMATCH")
    result["positions"] = active
    result["positionCount"] = len(active)
    for v in orders.values():
        if not isinstance(v, dict) or not symbol(v.get("symbol")):
            return empty(session, "ORDER_SHAPE_INVALID")
        quantity = nonnegative_int(v.get("quantity"))
        cumulative = nonnegative_int(v.get("cumulativeQuantity"))
        if (quantity is None or cumulative is None or quantity < cumulative
                or v.get("side") not in ("BUY", "SELL")):
            return empty(session, "ORDER_QUANTITY_INVALID")
        number = v.get("brokerOrderNumber")
        if number is not None and (type(number) is not str or not re.fullmatch(r"[0-9]{1,32}", number)):
            return empty(session, "ORDER_NUMBER_INVALID")
        result["orders"].append({"symbol": v["symbol"], "side": v["side"],
                                 "quantity": quantity, "filledQuantity": cumulative,
                                 "phase": clean_status(v.get("phase")),
                                 "brokerOrderNumber": number,
                                 "receivedByBroker": number is not None})
    result["orders"] = result["orders"][-100:]
    if result["securitiesOnlyCashReviewed"]:
        result["cashJpy"] = finite_money(ledger.get("cashJpy"))
        result["availableCashJpy"] = finite_money(ledger.get("availableCashJpy"))
        result["reservedCashJpy"] = finite_money(ledger.get("reservedCashJpy"))
    capital = report.get("capital")
    if result["sourceCurrent"] and isinstance(capital, dict) and isinstance(capital.get("intents"), list):
        for v in capital["intents"][:50]:
            if isinstance(v, dict) and symbol(v.get("symbol")) and v.get("side") in ("BUY", "SELL"):
                q = nonnegative_int(v.get("quantity"))
                if q is not None and q > 0:
                    result["selectorIntents"].append({"symbol": v["symbol"], "side": v["side"],
                                                      "quantity": q})
    # No synthetic equity curve, demo score, paper fills, inferred P&L,
    # account total-assets estimate, or manual order/kill buttons.
    return result


def read_model(private_root, session, clock=None):
    if (clock or now_jst()).date().isoformat() != session:
        return empty(session, "NOT_CURRENT_SESSION")
    root = Path(os.path.abspath(str(private_root)))
    pointer = unseal(root / ("received-session-" + session + ".active.json"), POINTER, session)
    if pointer is None:
        return empty(session, "WAITING_FOR_ACTIVE_REAL_RUN")
    dirname = pointer.get("runRoot")
    if not isinstance(dirname, str) or not Path(dirname).is_absolute():
        return empty(session, "ACTIVE_RUN_IDENTITY_INVALID")
    run = Path(os.path.abspath(dirname))
    if (run.parent != root or RUN.fullmatch(run.name) is None or
            run.name.split("-")[1:4] != session.split("-")):
        return empty(session, "ACTIVE_RUN_IDENTITY_INVALID")
    if run.is_symlink() or not run.is_dir() or (run / "inference").is_symlink():
        return empty(session, "ACTIVE_RUN_IDENTITY_INVALID")
    contract = unseal(run / "run-contract.json", CONTRACT, session)
    if (contract is None or contract.get("runRoot") != str(run)
            or checksum(contract) != pointer.get("contractSha256")
            or not isinstance(contract.get("extras"), dict)
            or not isinstance(contract["extras"].get("brokerExecutionConfig"), dict)):
        return empty(session, "ACTIVE_RUN_CONTRACT_INVALID")
    report = read_json(run / "inference" / "broker-execution-latest-report.json")
    if report is None:
        return empty(session, "WAITING_FOR_REAL_BROKER_REPORT")
    return project(report, session, clock)


class Handler(BaseHTTPRequestHandler):
    def send(self, status, payload, content_type):
        data = payload if isinstance(payload, bytes) else payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.client_address[0] != "127.0.0.1":
            return self.send(403, "LOCAL_ONLY", "text/plain; charset=utf-8")
        if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
            return self.send(403, "HOST_BLOCKED", "text/plain; charset=utf-8")
        route = urlsplit(self.path).path
        if route == "/":
            return self.send(200, self.server.document, "text/html; charset=utf-8")
        if route == "/api/live":
            status = read_model(self.server.private_root, self.server.session)
            return self.send(200, json.dumps(status, ensure_ascii=False, separators=(",", ":")),
                             "application/json; charset=utf-8")
        return self.send(404, "NOT_FOUND", "text/plain; charset=utf-8")

    def do_POST(self):
        return self.send(405, "READ_ONLY", "text/plain; charset=utf-8")

    def do_PUT(self):
        return self.send(405, "READ_ONLY", "text/plain; charset=utf-8")

    def do_DELETE(self):
        return self.send(405, "READ_ONLY", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        return


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=False)
    parser.add_argument("--private-root", type=Path)
    parser.add_argument("--document", type=Path)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--token")
    parser.add_argument("--offline-selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.offline_selftest:
        session = now_jst().date().isoformat()
        assert empty(session, "WAITING")["simulatedDataIncluded"] is False
        assert project({}, session)["realBrokerReportObserved"] is False
        assert not hasattr(Handler, "do_trade")
        print("NO11_UI2_LIVE_ONLY_SELFTEST=PASS_NO_SHADOW_NO_ORDERS")
        return 0
    session = args.session
    if (not isinstance(session, str) or DAY.fullmatch(session) is None
            or session != now_jst().date().isoformat()
            or args.private_root is None or args.document is None or args.ready_file is None
            or not isinstance(args.token, str) or not re.fullmatch(r"[a-f0-9]{32}", args.token)):
        raise ValueError("NO11_UI2_LIVE_STARTUP_CONTRACT")
    root = args.private_root.absolute()
    if (not root.is_dir() or root.is_symlink() or args.document.is_symlink()
            or not args.document.is_file() or args.document.stat().st_size > 150_000):
        raise ValueError("NO11_UI2_LIVE_INPUTS")
    document = args.document.read_bytes()
    if (b"ARK TERMINAL 2.0" not in document or
            b"/api/live" not in document or b"SHADOW PORTFOLIO" in document):
        raise ValueError("NO11_UI2_LIVE_UI_IDENTITY")
    ready = args.ready_file.absolute()
    if ready.parent.is_symlink() or not ready.parent.is_dir() or ready.exists():
        raise ValueError("NO11_UI2_LIVE_READY_IDENTITY")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.private_root = root
    server.session = session
    server.document = document
    server.daemon_threads = True
    receipt = {"schemaId": "ARK_NO11_UI2_LIVE_ONLY_READY_V1", "sessionDate": session,
               "token": args.token, "pid": os.getpid(),
               "url": "http://127.0.0.1:" + str(server.server_port) + "/",
               "readOnly": True, "realOrderPermissionNotGrantedByUI": True}
    with ready.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, separators=(",", ":"))
        stream.write("\n")
    print("NO11_UI2_LIVE_ONLY_SERVER=BOUND_LOOPBACK_READONLY", flush=True)
    server.serve_forever(poll_interval=0.5)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, AssertionError) as error:
        print("NO11_UI2_LIVE=BLOCKED|" +
              (str(error) if str(error).startswith("NO11_UI2_LIVE_")
               else "NO11_UI2_LIVE_RUNTIME_FAILURE"), file=sys.stderr)
        sys.exit(2)
