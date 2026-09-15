"""G9 cash-only unlock-candidate contract.

This gate can only issue a short-lived candidate token. It cannot transmit,
write Excel, call RSS, enable margin, or enable short selling.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib

SAFETY = {
    "executionAllowed": False,
    "brokerWriteAllowed": False,
    "excelOrderWriteAllowed": False,
    "rssOrderFunctionAllowed": False,
    "liveTradingAllowed": False,
    "paperTradingAllowed": False,
    "marginTradingAllowed": False,
    "shortSellingAllowed": False,
    "marginFallbackAllowed": False,
    "transmitted": False,
}


def build_cash_only_unlock_candidate(
    *, reconciliation, runtime_safety, draft, buying_power, estimated_notional,
    daily_realized_pnl, human_approval_id, approval_expires_at, now=None,
    used_approval_ids=(), max_order_notional=100_000, max_daily_loss=10_000,
):
    blockers = []
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("NOW_MUST_BE_ABSOLUTE")
    current = current.astimezone(timezone.utc)

    if reconciliation.get("status") != "RECONCILIATION_PASS" or reconciliation.get("blockers"):
        blockers.append("FRESH_RECONCILIATION_REQUIRED")
    age = reconciliation.get("snapshotAgeSeconds")
    if age is None or age < 0 or age > 30:
        blockers.append("RECONCILIATION_TOO_OLD")

    if runtime_safety.get("killSwitchLatched") is not False or runtime_safety.get("faults"):
        blockers.append("KILL_SWITCH_OR_FAULT_PRESENT")

    intent = draft.get("intent") or {}
    if draft.get("function") != "RssStockOrder": blockers.append("CASH_ORDER_FUNCTION_REQUIRED")
    if intent.get("direction") != "LONG": blockers.append("LONG_ONLY")
    if intent.get("side") not in {"BUY", "SELL"}: blockers.append("CASH_SIDE_REQUIRED")
    if intent.get("positionEffect") == "OPEN" and intent.get("side") != "BUY": blockers.append("CASH_OPEN_BUY_ONLY")
    if intent.get("positionEffect") == "CLOSE" and intent.get("side") != "SELL": blockers.append("CASH_CLOSE_SELL_ONLY")
    if draft.get("trigger") != 0 or draft.get("transmitted") is not False:
        blockers.append("DRYRUN_LOCK_REQUIRED")
    if draft.get("excelWritePerformed") is not False or draft.get("rssCallPerformed") is not False:
        blockers.append("NO_IO_DRYRUN_REQUIRED")

    qty = intent.get("quantity")
    if not isinstance(qty, int) or qty <= 0 or qty % 100:
        blockers.append("CASH_LOT_REQUIRED")
    if not isinstance(estimated_notional, (int, float)) or estimated_notional <= 0:
        blockers.append("ORDER_NOTIONAL_REQUIRED")
    elif estimated_notional > max_order_notional:
        blockers.append("ORDER_NOTIONAL_CAP_EXCEEDED")
    if intent.get("side") == "BUY" and (not isinstance(buying_power, (int, float)) or buying_power < estimated_notional):
        blockers.append("INSUFFICIENT_CASH")
    if not isinstance(daily_realized_pnl, (int, float)) or daily_realized_pnl <= -abs(max_daily_loss):
        blockers.append("DAILY_LOSS_LIMIT_REACHED")

    approval = str(human_approval_id or "").strip()
    if not approval:
        blockers.append("HUMAN_APPROVAL_REQUIRED")
    if approval in set(used_approval_ids):
        blockers.append("APPROVAL_REPLAYED")
    try:
        expiry = datetime.fromisoformat(str(approval_expires_at).replace("Z", "+00:00")).astimezone(timezone.utc)
        if expiry <= current:
            blockers.append("APPROVAL_EXPIRED")
        if (expiry - current).total_seconds() > 300:
            blockers.append("APPROVAL_TTL_TOO_LONG")
    except Exception:
        blockers.append("APPROVAL_EXPIRY_INVALID")

    blockers = list(dict.fromkeys(blockers))
    eligible = not blockers
    material = f"{approval}|{intent.get('symbol')}|{intent.get('side')}|{qty}|{estimated_notional}|{current.isoformat()}"
    token = hashlib.sha256(material.encode()).hexdigest() if eligible else None
    return {
        "schemaId": "ARK_CASH_ONLY_UNLOCK_CANDIDATE_V1",
        "eligible": eligible,
        "candidateToken": token,
        "blockers": blockers,
        "cashOnly": True,
        "marginAllowed": False,
        "shortSellingAllowed": False,
        "oneShotApproval": approval or None,
        "safety": dict(SAFETY),
    }
