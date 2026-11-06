#!/usr/bin/env python3
"""Serve the ORIGINAL rich No.1.1 UI with the NEW verified Shadow observer.

The source UI/overlay are byte-for-byte pinned copies of integration/no1-1-msii
and are served only over loopback. The data is never demo or fabricated:
verified read-only RSS account snapshots feed the original Home/Positions/
Orders pages, and the original Shadow simulator receipts feed an additive
Shadow section. No Excel COM, broker, order writes, or model fits here.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlsplit

import ark_shadow_ui as original

CLASSIC = Path(__file__).resolve().parent / "classic"
READ_MODEL_SCHEMA = "ARK_TERMINAL_UI_READ_MODEL_V1"
MUTATIONS = ("orderSubmit", "orderCancel", "killSwitchChange", "strategyEdit",
             "brokerWrite", "excelOrderWrite", "rssOrderFunction")
MAX_CLASSIC_FILE = 500_000
OLD_HANDLER = original.Handler


def classic_asset(name: str) -> bytes:
    """Only fixed known assets, never any URL-supplied file path."""
    if name not in ("index.html", "ark-readonly-overlay.js",
                    "ark-shadow-classic-bridge.js"):
        raise ValueError("CLASSIC_ASSET_NOT_ALLOWED")
    path = CLASSIC / name
    if not path.is_file() or path.is_symlink():
        raise ValueError("CLASSIC_ASSET_UNAVAILABLE")
    if not (0 < path.stat().st_size <= MAX_CLASSIC_FILE):
        raise ValueError("CLASSIC_ASSET_SIZE")
    return path.read_bytes()


def classic_document():
    source = classic_asset("index.html").decode("utf-8-sig")
    if ('id="root"' not in source or
            source.lower().count("</head>") != 1 or
            source.lower().count("</body>") != 1 or
            '<script src="/ark-readonly-overlay.js"' in source):
        raise ValueError("ORIGINAL_CLASSIC_UI_LAYOUT_UNEXPECTED")

    # Never flash the historical React demo before the read-only overlay hides
    # its demo contents. Restore visibility only when the overlay is mounted.
    head = '<style id="ark-classic-preload">#root{visibility:hidden!important}</style>'
    source = source.replace("</head>", head + "</head>", 1)
    scripts = ('<script src="/ark-readonly-overlay.js" defer></script>'
               '<script src="/ark-shadow-classic-bridge.js" defer></script>')
    source = source.replace("</body>", scripts + "</body>", 1)

    # The bundled historical UI has inline compiled React JS. Allow *only* its
    # exact source-hash, not arbitrary injected scripts or remote script URLs.
    inline_scripts = re.findall(
        r"<script([^>]*)>(.*?)</script\s*>", source, flags=re.I | re.S)
    script_hashes = [
        "'sha256-" + base64.b64encode(
            hashlib.sha256(content.encode("utf-8")).digest()).decode("ascii") + "'"
        for attributes, content in inline_scripts
        if content.strip() and not re.search(r"\bsrc\s*=", attributes, re.I)
    ]
    if not script_hashes or len(script_hashes) > 4:
        raise ValueError("ORIGINAL_CLASSIC_SCRIPT_SET_UNEXPECTED")
    csp = ("default-src 'none'; script-src 'self' " + " ".join(script_hashes) +
           "; script-src-attr 'none'; style-src 'self' 'unsafe-inline'; "
           "style-src-attr 'unsafe-inline'; img-src 'self' data:; "
           "font-src 'self' data:; connect-src 'self'; "
           "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
    return source.encode("utf-8"), csp


def numeric(value):
    """Only finite, safe JSON display numbers; no invented missing values."""
    n = original.number(value)
    if n is None or abs(n) >= 9_000_000_000_000_000:
        return None
    result = float(n)
    return result if math.isfinite(result) else None


def account_read_model(status):
    """Project ONLY a fresh verified account RSS snapshot into original UI.

    The old UI is not permitted to show fabricated test/demo positions or old
    account amounts. Shadow simulator data remains separate in /api/status.
    """
    if (not isinstance(status, dict) or
            status.get("schemaId") != "ARK_SHADOW_LOCAL_DASHBOARD_V1" or
            status.get("orderTransmission") is not False):
        return None
    a = status.get("account")
    if not isinstance(a, dict) or a.get("status") != "OBSERVED":
        return None
    when = original.timestamp(a.get("asOf"))
    if when is None or not original.fresh(a.get("asOf"), 90):
        return None
    rows = a.get("positions")
    executions = a.get("executions")
    orders = a.get("orders")
    if not isinstance(rows, list) or not isinstance(executions, list) or not isinstance(orders, list):
        return None

    positions = []
    for p in rows:
        if not isinstance(p, dict) or not original.SYMBOL.fullmatch(str(p.get("symbol", ""))):
            continue
        positions.append({
            "symbol": p["symbol"],
            "name": p["symbol"],
            "quantity": original.safe_int(p.get("quantity")),
            "marketValue": numeric(p.get("marketValue")),
            "unrealizedPnl": numeric(p.get("unrealizedPnl")),
            "ownership": "UNKNOWN",
            "accountType": "RSS_UNVERIFIED_CATEGORY",
        })
    actual_orders = []
    for o in orders:
        if not isinstance(o, dict):
            continue
        actual_orders.append({
            "symbol": str(o.get("symbol", ""))[:8],
            "status": str(o.get("status", ""))[:30],
            "quantity": original.safe_int(o.get("quantity")),
            "orderNumber": None,
            "filledQuantity": None,
        })
    actual_executions = []
    for e in executions:
        if not isinstance(e, dict):
            continue
        actual_executions.append({
            "symbol": str(e.get("symbol", ""))[:8],
            "side": str(e.get("side", ""))[:12],
            "quantity": original.safe_int(e.get("quantity")),
            "price": numeric(e.get("price")),
            "executionDate": e.get("at"),
        })

    mutation = {key: False for key in MUTATIONS}
    age = max(0.0, (original.now() - when).total_seconds())
    return {
        "schemaId": READ_MODEL_SCHEMA,
        "readOnly": True,
        "generatedAt": original.now().isoformat(timespec="seconds"),
        "source": {
            "schemaValid": True,
            "sourceMode": "NEW_SHADOW_ACCOUNT_READONLY_RSS_OBSERVER",
            "freshness": {
                "state": "FRESH", "timestamp": a["asOf"],
                "ageSeconds": age,
            },
            "positionsTruncated": (a.get("positionCount") != len(rows)),
            "actualPositionCount": a.get("positionCount"),
            "ownershipCertified": False,
            "shadowTotalsMixedIntoRealAccount": False,
        },
        "home": {
            "buyingPower": numeric(a.get("buyingPower")),
            "buyingPowerState": "RSS_OBSERVED_NOT_CASH",
            "activeIntent": None,
            "activeIntentLineage": None,
        },
        "positions": positions,
        "orders": actual_orders,
        "executions": actual_executions,
        "selector": {"state": "NOT_ATTACHED_TO_ORIGINAL_UI_READ_MODEL"},
        "performance": {"state": "NO_CERTIFIED_LIVE_PERFORMANCE"},
        "safety": {"state": "LOCKED"},
        "system": {
            "health": "ACCOUNT_OBSERVED_SHADOW_SEPARATE",
            "tradeReadiness": "BLOCKED",
            "ownership": {"state": "NOT_VERIFIED"},
            "reconciliation": {"state": "NOT_VERIFIED"},
            "pipeline": {"state": "NO_BROKER_ORDER_CAPABILITY"},
            "runtimeSafety": {"state": "LOCKED", "killSwitchLatched": True},
        },
        "mutationCapabilities": mutation,
        "localBridge": {
            "readOnly": True,
            "loopbackOnly": True,
            "refresh": {"enabled": True, "running": False, "lastError": None},
            "mutationCapabilities": mutation,
        },
    }


class ClassicHandler(OLD_HANDLER):
    def _safe_send(self, code, body, mime, csp=None):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Ark-Read-Only", "true")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", csp or
                         "default-src 'none'; script-src 'self'; "
                         "style-src 'self'; connect-src 'self'; "
                         "base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _local_origin(self):
        port = self.server.server_port
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        host = self.headers.get("Host")
        origin = self.headers.get("Origin")
        return host in allowed and (
            origin is None or origin in {f"http://{host}"}
        )

    def do_GET(self):
        if not self._local_origin():
            return self._safe_send(HTTPStatus.FORBIDDEN, b"Forbidden",
                                   "text/plain; charset=utf-8")
        path = urlsplit(self.path).path
        try:
            if path in ("/", "/index.html"):
                document, csp = classic_document()
                return self._safe_send(200, document, "text/html; charset=utf-8", csp)
            if path == "/ark-readonly-overlay.js":
                return self._safe_send(200, classic_asset("ark-readonly-overlay.js"),
                                       "text/javascript; charset=utf-8")
            if path == "/ark-shadow-classic-bridge.js":
                return self._safe_send(200, classic_asset("ark-shadow-classic-bridge.js"),
                                       "text/javascript; charset=utf-8")
            if path == "/api/ui-read-model":
                data = account_read_model(original.build_status(self.server.config))
                if data is None:
                    response = {"ok": False, "readOnly": True,
                                "code": "CURRENT_RSS_ACCOUNT_MODEL_NOT_OBSERVED",
                                "message": "No current verified account RSS snapshot"}
                    return self._safe_send(HTTPStatus.SERVICE_UNAVAILABLE,
                        json.dumps(response).encode("utf-8"), "application/json; charset=utf-8")
                payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                return self._safe_send(200, payload, "application/json; charset=utf-8")
            if path == "/api/classic-health":
                response = {"schemaId": "ARK_SHADOW_CLASSIC_UI_V1", "status": "READ_ONLY",
                            "sessionDate": self.server.config.session,
                            "orderTransmission": False}
                return self._safe_send(200, json.dumps(response).encode("utf-8"),
                                       "application/json; charset=utf-8")
            if path == "/console":
                return self._safe_send(200, (original.BASE / "index.html").read_bytes(),
                                       "text/html; charset=utf-8",
                                       "default-src 'none'; script-src 'self'; "
                                       "style-src 'self'; connect-src 'self'; "
                                       "img-src 'self'; base-uri 'none'; form-action 'none'")
            return super().do_GET()
        except (OSError, ValueError, UnicodeError):
            return self._safe_send(HTTPStatus.SERVICE_UNAVAILABLE,
                b'{"ok":false,"readOnly":true,"code":"CLASSIC_READ_ONLY_SOURCE_UNAVAILABLE"}',
                "application/json; charset=utf-8")


if __name__ == "__main__":
    # Reuse the original proven account/SQLite read-only server, exactly one
    # localhost service; never run an old UI server/Excel COM process in parallel.
    classic_document()
    original.Handler = ClassicHandler
    original.main()
