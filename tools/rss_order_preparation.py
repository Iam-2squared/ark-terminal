from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from json import dumps
from typing import Any, Mapping

ORDER_SHEET_NAME = "ARK_ORDER"
ORDER_TRIGGER_CELL = "B9"
ORDER_TRIGGER_DISABLED = False

ORDER_CELL_MAP: dict[str, str] = {
    "symbol": "B2",
    "side": "B3",
    "quantity": "B4",
    "order_type": "B5",
    "limit_price": "B6",
    "account_type": "B7",
    "execution_condition": "B8",
    "order_trigger": ORDER_TRIGGER_CELL,
}

STATUS_MAP = {
    "待機中": "WAITING",
    "発注ロック中": "LOCKED",
    "接続待ち": "CONNECTION_WAIT",
    "応答待ち": "RESPONSE_WAIT",
    "キャンセル": "CANCELLED",
    "発注済み": "SUBMITTED",
    "入力エラー": "INPUT_ERROR",
    "サーバチェックエラー": "SERVER_CHECK_ERROR",
}


@dataclass(frozen=True)
class PreparationResult:
    status: str
    blockers: tuple[str, ...]
    worksheet: str
    cells: Mapping[str, Any]
    audit_hash: str
    generated_at: str
    safety: Mapping[str, Any]


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def build_order_preparation(input_data: Mapping[str, Any]) -> PreparationResult:
    approval = input_data.get("approval") or {}
    risk = input_data.get("risk") or {}
    kill_switch = input_data.get("killSwitch") or {}
    candidate = input_data.get("candidate") or {}
    blockers: list[str] = []

    if approval.get("status") != "DRY_RUN_READY":
        blockers.append("TWO_STEP_APPROVAL_INCOMPLETE")
    if risk.get("status") != "DRY_RUN_ALLOWED":
        blockers.append("RISK_GOVERNOR_BLOCKED")
    if kill_switch.get("status") != "ARMED":
        blockers.append("KILL_SWITCH_HALTED")
    if not candidate.get("symbol"):
        blockers.append("SYMBOL_MISSING")
    if str(candidate.get("side", "")).upper() not in {"BUY", "SELL"}:
        blockers.append("SIDE_INVALID")
    if int(candidate.get("quantity") or 0) <= 0:
        blockers.append("QUANTITY_INVALID")
    if float(candidate.get("limitPrice") or candidate.get("price") or 0) <= 0:
        blockers.append("PRICE_INVALID")

    cells = {
        ORDER_CELL_MAP["symbol"]: candidate.get("symbol"),
        ORDER_CELL_MAP["side"]: str(candidate.get("side", "")).upper(),
        ORDER_CELL_MAP["quantity"]: int(candidate.get("quantity") or 0),
        ORDER_CELL_MAP["order_type"]: candidate.get("orderType", "LIMIT"),
        ORDER_CELL_MAP["limit_price"]: float(candidate.get("limitPrice") or candidate.get("price") or 0),
        ORDER_CELL_MAP["account_type"]: candidate.get("accountType", "CASH"),
        ORDER_CELL_MAP["execution_condition"]: candidate.get("executionCondition", "DAY"),
        ORDER_TRIGGER_CELL: ORDER_TRIGGER_DISABLED,
    }

    audit_payload = {
        "worksheet": ORDER_SHEET_NAME,
        "cells": cells,
        "approvalHash": approval.get("candidateHash"),
        "mode": "PREPARE_ONLY",
    }
    generated_at = str(input_data.get("generatedAt") or datetime.now(timezone.utc).isoformat())

    return PreparationResult(
        status="BLOCKED" if blockers else "PREPARED_FOR_LOCAL_REVIEW",
        blockers=tuple(blockers),
        worksheet=ORDER_SHEET_NAME,
        cells=cells,
        audit_hash=_canonical_hash(audit_payload),
        generated_at=generated_at,
        safety={
            "mode": "PREPARE_ONLY",
            "excelWriteAllowed": not blockers,
            "orderTriggerWriteAllowed": False,
            "brokerWriteAllowed": False,
            "liveTradingAllowed": False,
            "orderCreationAllowed": False,
            "orderCancellationAllowed": False,
            "orderModificationAllowed": False,
            "humanFinalActionRequired": True,
        },
    )


def write_preparation_to_worksheet(worksheet: Any, result: PreparationResult) -> dict[str, Any]:
    if result.status != "PREPARED_FOR_LOCAL_REVIEW":
        raise ValueError("Blocked preparation cannot be written to Excel.")

    for cell, value in result.cells.items():
        if cell == ORDER_TRIGGER_CELL:
            value = ORDER_TRIGGER_DISABLED
        worksheet.Range(cell).Value = value

    # Defensive second write: even a malformed caller cannot leave the trigger enabled.
    worksheet.Range(ORDER_TRIGGER_CELL).Value = ORDER_TRIGGER_DISABLED
    return {
        "status": "PREVIEW_WRITTEN",
        "worksheet": result.worksheet,
        "writtenCells": len(result.cells),
        "orderTrigger": False,
        "brokerWrites": 0,
        "liveOrders": 0,
    }


def normalize_rss_order_status(raw_status: Any) -> dict[str, Any]:
    raw = str(raw_status or "").strip()
    normalized = STATUS_MAP.get(raw, "UNKNOWN")
    is_error = normalized in {"INPUT_ERROR", "SERVER_CHECK_ERROR", "UNKNOWN"}
    return {
        "raw": raw,
        "status": normalized,
        "terminal": normalized in {"CANCELLED", "SUBMITTED", "INPUT_ERROR", "SERVER_CHECK_ERROR"},
        "error": is_error,
        "readOnly": True,
    }


def evaluate_phase28_activation_gate(input_data: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if int(input_data.get("paperResolved", 0)) < 300:
        blockers.append("PAPER_SAMPLE_TOO_SMALL")
    if int(input_data.get("paperSessions", 0)) < 60:
        blockers.append("PAPER_SESSIONS_TOO_SHORT")
    if float(input_data.get("paperProfitFactor", 0)) < 1.2:
        blockers.append("PAPER_PROFIT_FACTOR_TOO_LOW")
    if float(input_data.get("paperMaxDrawdown", 1)) > 0.10:
        blockers.append("PAPER_DRAWDOWN_TOO_HIGH")
    if int(input_data.get("shadowSessions", 0)) < 60:
        blockers.append("SHADOW_SESSIONS_TOO_SHORT")
    if int(input_data.get("criticalIncidents", 0)) > 0:
        blockers.append("CRITICAL_INCIDENT_PRESENT")
    if input_data.get("killSwitchTestPassed") is not True:
        blockers.append("KILL_SWITCH_TEST_REQUIRED")
    if input_data.get("guardianAndAccountRulesConfirmed") is not True:
        blockers.append("ACCOUNT_RULES_NOT_CONFIRMED")

    return {
        "status": "BLOCKED" if blockers else "READY_FOR_HUMAN_REVIEW",
        "blockers": blockers,
        "automaticActivationAllowed": False,
        "excelOrderTriggerAllowed": False,
        "brokerWriteAllowed": False,
        "liveTradingAllowed": False,
        "nextStep": "HUMAN_REVIEW_ONLY",
    }
