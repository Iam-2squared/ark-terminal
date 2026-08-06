from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

PHASE28_ORDER_BRIDGE_VERSION = "phase28-rss-order-dryrun-v1"

ALLOWED_SIDES = {"BUY", "SELL"}
ALLOWED_ORDER_TYPES = {"LIMIT", "MARKET"}


@dataclass(frozen=True)
class DryRunOrder:
    symbol: str
    side: str
    quantity: int
    order_type: str
    limit_price: float | None
    account_type: str
    execution_condition: str


def _normalize_symbol(value: Any) -> str:
    symbol = str(value or "").strip().upper()
    if symbol.isdigit():
        symbol = f"{symbol}.T"
    if not symbol or not symbol.endswith(".T"):
        raise ValueError("SYMBOL_INVALID")
    return symbol


def _normalize_order(candidate: dict[str, Any]) -> DryRunOrder:
    symbol = _normalize_symbol(candidate.get("symbol"))
    side = str(candidate.get("side") or "").strip().upper()
    order_type = str(candidate.get("orderType") or "LIMIT").strip().upper()
    quantity = int(candidate.get("quantity") or 0)
    raw_price = candidate.get("limitPrice", candidate.get("price"))
    limit_price = None if raw_price in (None, "") else float(raw_price)

    if side not in ALLOWED_SIDES:
        raise ValueError("SIDE_INVALID")
    if order_type not in ALLOWED_ORDER_TYPES:
        raise ValueError("ORDER_TYPE_INVALID")
    if quantity <= 0:
        raise ValueError("QUANTITY_INVALID")
    if order_type == "LIMIT" and (limit_price is None or limit_price <= 0):
        raise ValueError("LIMIT_PRICE_INVALID")

    return DryRunOrder(
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type=order_type,
        limit_price=limit_price if order_type == "LIMIT" else None,
        account_type=str(candidate.get("accountType") or "SPECIFIED").strip().upper(),
        execution_condition=str(candidate.get("executionCondition") or "DAY").strip().upper(),
    )


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_excel_preview(order: DryRunOrder) -> dict[str, Any]:
    """Return the intended order-sheet values without touching Excel."""
    return {
        "sheet": "ARK_ORDER",
        "cells": {
            "B2": order.symbol.removesuffix(".T"),
            "B3": order.side,
            "B4": order.quantity,
            "B5": order.order_type,
            "B6": order.limit_price,
            "B7": order.execution_condition,
            "B8": order.account_type,
            "B9": False,
        },
        "rssFunction": "RssStockOrder",
        "triggerCell": "B9",
        "triggerValue": False,
    }


def build_rss_order_dry_run(
    candidate: dict[str, Any],
    *,
    approval: dict[str, Any] | None = None,
    risk: dict[str, Any] | None = None,
    kill_switch: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    approval = approval or {}
    risk = risk or {}
    kill_switch = kill_switch or {}
    blockers: list[str] = []

    try:
        order = _normalize_order(candidate)
    except (TypeError, ValueError) as exc:
        blockers.append(str(exc))
        order = None

    if approval.get("status") != "DRY_RUN_READY":
        blockers.append("TWO_STEP_APPROVAL_INCOMPLETE")
    if risk.get("status") != "DRY_RUN_ALLOWED":
        blockers.append("RISK_GOVERNOR_BLOCKED")
    if kill_switch.get("status") != "ARMED":
        blockers.append("KILL_SWITCH_HALTED")

    preview = build_excel_preview(order) if order else None
    payload = {
        "version": PHASE28_ORDER_BRIDGE_VERSION,
        "status": "BLOCKED" if blockers else "DRY_RUN_COMPLETED",
        "generatedAt": generated_at or datetime.now(timezone.utc).isoformat(),
        "blockers": sorted(set(blockers)),
        "order": asdict(order) if order else None,
        "excelPreview": preview,
        "sideEffects": {
            "excelWrites": 0,
            "triggerChanges": 0,
            "brokerWrites": 0,
            "liveOrders": 0,
        },
        "safety": {
            "mode": "DRY_RUN_ONLY",
            "localOnly": True,
            "excelWriteAllowed": False,
            "triggerLockedFalse": True,
            "brokerWriteAllowed": False,
            "liveTradingAllowed": False,
            "humanFinalActionRequired": True,
        },
    }
    payload["auditHash"] = _hash_payload(payload)
    return payload
