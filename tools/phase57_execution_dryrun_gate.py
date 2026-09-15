"""G7 execution dry-run gate.

Consumes an already-passed account reconciliation plus a canonical order intent
and produces an auditable, non-executable RSS draft. It never writes to Excel,
never calls RSS, and trigger/transmission remain locked at zero/false.
"""
from __future__ import annotations

import re

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

_SYMBOL = re.compile(r"^[0-9A-Z]{4}\.T$")


def _required(value, reason):
    if value is None or value == "":
        raise ValueError(reason)
    return value


def build_locked_cash_order_draft(reconciliation, intent, *, order_id, account_type=0, sor=0):
    if not isinstance(reconciliation, dict) or reconciliation.get("status") != "RECONCILIATION_PASS":
        raise ValueError("RECONCILIATION_PASS_REQUIRED")
    if reconciliation.get("blockers"):
        raise ValueError("RECONCILIATION_BLOCKERS_PRESENT")
    if reconciliation.get("reconciliationMatched") is not True:
        raise ValueError("RECONCILIATION_MATCH_REQUIRED")

    symbol = str(_required(intent.get("symbol"), "ORDER_SYMBOL_REQUIRED")).upper()
    if not _SYMBOL.fullmatch(symbol):
        raise ValueError("MSII_TSE_SYMBOL_REQUIRED")
    direction = str(_required(intent.get("direction"), "ORDER_DIRECTION_REQUIRED")).upper()
    side = str(_required(intent.get("side"), "ORDER_SIDE_REQUIRED")).upper()
    effect = str(_required(intent.get("positionEffect"), "POSITION_EFFECT_REQUIRED")).upper()
    order_type = str(_required(intent.get("orderType"), "ORDER_TYPE_REQUIRED")).upper()
    tif = str(_required(intent.get("timeInForce"), "TIME_IN_FORCE_REQUIRED")).upper()
    quantity = intent.get("quantity")

    if direction != "LONG":
        raise ValueError("CASH_SHORT_UNSUPPORTED")
    expected_side = "BUY" if effect == "OPEN" else "SELL"
    if side != expected_side:
        raise ValueError("CASH_LONG_SIDE_MISMATCH")
    if tif != "DAY":
        raise ValueError("MSII_DAY_ONLY")
    if not isinstance(quantity, int) or quantity <= 0 or quantity % 100:
        raise ValueError("MSII_LOT_QUANTITY_REQUIRED")
    if not isinstance(order_id, int) or order_id < 1:
        raise ValueError("MSII_ORDER_ID_REQUIRED")
    if str(account_type) not in set("01234567") or str(sor) not in set("01234567"):
        raise ValueError("MSII_CODE_INVALID")

    limit_price = intent.get("limitPrice")
    if order_type == "MARKET":
        if limit_price is not None:
            raise ValueError("MARKET_LIMIT_PRICE_MUST_BE_NULL")
        price_type, price = "0", ""
    elif order_type == "LIMIT":
        if not isinstance(limit_price, (int, float)) or limit_price <= 0:
            raise ValueError("MSII_LIMIT_PRICE_REQUIRED")
        price_type, price = "1", str(limit_price)
    else:
        raise ValueError("MSII_ORDER_TYPE_REQUIRED")

    side_code = "3" if side == "BUY" else "1"
    # Mirrors the validated execution branch contract, but is intentionally a
    # plain draft string: this module never places it into Excel.
    args = [
        str(order_id), "0", symbol, side_code, "0", str(sor), str(quantity),
        price_type, price, "1", "", str(account_type), "", "", "", "", "0", "", "", "",
    ]
    def excel_arg(value):
        if value != "" and re.fullmatch(r"-?\d+(?:\.\d+)?", value):
            return value
        return '"' + value.replace('"', '""') + '"'

    formula = "=RssStockOrder(" + ",".join(excel_arg(x) for x in args) + ")"
    return {
        "schemaId": "ARK_MSII_EXECUTION_DRYRUN_V1",
        "function": "RssStockOrder",
        "trigger": 0,
        "transmitted": False,
        "executable": False,
        "excelWritePerformed": False,
        "rssCallPerformed": False,
        "formulaDraft": formula,
        "intent": dict(intent),
        "safety": dict(SAFETY),
    }
