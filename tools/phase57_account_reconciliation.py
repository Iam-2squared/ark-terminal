"""Fail-closed reconciliation for MarketSpeed II account READ ONLY snapshots.

No broker/Excel/RSS write path exists here. Reconciliation can only attest or
block; it never repairs account state automatically.
"""
from __future__ import annotations

from datetime import datetime, timezone

SAFETY = {
    "executionAllowed": False,
    "brokerWriteAllowed": False,
    "excelOrderWriteAllowed": False,
    "rssOrderFunctionAllowed": False,
    "liveTradingAllowed": False,
    "paperTradingAllowed": False,
    "automaticPromotionAllowed": False,
    "productionUpdateAllowed": False,
    "transmitted": False,
}


def _text(value):
    return str(value or "").strip()


def _symbol(value):
    raw = _text(value).upper()
    if not raw:
        return ""
    if raw.endswith(".T"):
        return raw
    if raw.isdigit():
        return f"{raw}.T"
    return raw


def _parse_time(value):
    text = _text(value)
    if not text:
        raise ValueError("ACCOUNT_SNAPSHOT_CAPTURED_AT_REQUIRED")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("ACCOUNT_SNAPSHOT_CAPTURED_AT_MUST_BE_ABSOLUTE")
    return parsed.astimezone(timezone.utc)


def reconcile_account_snapshot(snapshot, ark_positions=None, *, now=None, max_age_seconds=30):
    blockers = []
    if not isinstance(snapshot, dict):
        raise TypeError("ACCOUNT_SNAPSHOT_OBJECT_REQUIRED")
    if snapshot.get("schemaId") != "ARK_ACCOUNT_READONLY_SNAPSHOT_V2":
        blockers.append("ACCOUNT_SNAPSHOT_SCHEMA_MISMATCH")
    if snapshot.get("source") != "MARKETSPEED_II_RSS" or snapshot.get("mode") != "READ_ONLY":
        blockers.append("ACCOUNT_SOURCE_NOT_READ_ONLY_MSII")

    safety = snapshot.get("safety") or {}
    for key, expected in SAFETY.items():
        if safety.get(key) is not expected:
            blockers.append(f"UNSAFE_ACCOUNT_SNAPSHOT:{key}")

    captured = _parse_time(snapshot.get("capturedAt"))
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("RECONCILIATION_NOW_MUST_BE_ABSOLUTE")
    age = (current.astimezone(timezone.utc) - captured).total_seconds()
    if age < -1:
        blockers.append("ACCOUNT_SNAPSHOT_FROM_FUTURE")
    if age > max_age_seconds:
        blockers.append("ACCOUNT_SNAPSHOT_STALE")

    broker = {}
    for row in snapshot.get("positions") or []:
        symbol = _symbol(row.get("symbol"))
        quantity = row.get("quantity")
        if not symbol:
            blockers.append("BROKER_POSITION_IDENTITY_UNRESOLVED")
            continue
        if quantity is None:
            blockers.append(f"BROKER_POSITION_QUANTITY_MISSING:{symbol}")
            continue
        if symbol in broker:
            blockers.append(f"BROKER_POSITION_DUPLICATE:{symbol}")
            continue
        broker[symbol] = float(quantity)

    for order in snapshot.get("orders") or []:
        number = _text(order.get("orderNumber"))
        symbol = _symbol(order.get("symbol"))
        status = _text(order.get("status")).upper()
        quantity = order.get("quantity")
        filled = order.get("filledQty")
        if not number:
            blockers.append("BROKER_ORDER_IDENTITY_UNRESOLVED")
        if not symbol:
            blockers.append(f"BROKER_ORDER_SYMBOL_UNRESOLVED:{number or 'UNKNOWN'}")
        if quantity is not None and filled is not None and 0 < float(filled) < float(quantity):
            blockers.append(f"BROKER_PARTIAL_FILL:{number or 'UNKNOWN'}")
        if status in {"UNKNOWN", "不明"}:
            blockers.append(f"BROKER_ORDER_STATUS_UNKNOWN:{number or 'UNKNOWN'}")

    ark = {}
    for row in ark_positions or []:
        symbol = _symbol(row.get("symbol"))
        if not symbol:
            blockers.append("ARK_POSITION_IDENTITY_UNRESOLVED")
            continue
        quantity = row.get("quantity")
        if quantity is None:
            blockers.append(f"ARK_POSITION_QUANTITY_MISSING:{symbol}")
            continue
        ark[symbol] = ark.get(symbol, 0.0) + float(quantity)

    for symbol in sorted(set(broker) | set(ark)):
        if symbol not in ark:
            blockers.append(f"UNKNOWN_BROKER_POSITION:{symbol}")
        elif symbol not in broker:
            blockers.append(f"BROKER_POSITION_MISSING:{symbol}")
        elif broker[symbol] != ark[symbol]:
            blockers.append(f"POSITION_QUANTITY_MISMATCH:{symbol}:{ark[symbol]}!={broker[symbol]}")

    blockers = list(dict.fromkeys(blockers))
    passed = not blockers
    return {
        "schemaId": "ARK_ACCOUNT_RECONCILIATION_V1",
        "status": "RECONCILIATION_PASS" if passed else "RECONCILIATION_BLOCKED",
        "armAllowed": False,
        "reconciliationMatched": passed,
        "blockers": blockers,
        "brokerPositionCount": len(broker),
        "arkPositionCount": len(ark),
        "snapshotAgeSeconds": age,
        "safety": dict(SAFETY),
    }
