"""Map G10 output to a non-executable Excel inspection interface.

The adapter returns plain cell values only. Formula text is explicitly marked as
TEXT and must never be written as an Excel formula by consumers.
"""
from __future__ import annotations


def build_locked_excel_interface(*, preflight, draft, buying_power):
    if preflight.get("readyForPhysicalUnlock") is not True:
        raise ValueError("G10_READY_REQUIRED")
    if preflight.get("cashOnly") is not True:
        raise ValueError("CASH_ONLY_REQUIRED")
    if preflight.get("marginAllowed") is not False or preflight.get("shortSellingAllowed") is not False:
        raise ValueError("MARGIN_OR_SHORT_PRESENT")
    if preflight.get("transmitted") is not False or preflight.get("rssCallPerformed") is not False:
        raise ValueError("PREFLIGHT_NOT_LOCKED")
    intent=draft.get("intent") or {}
    formula=str(draft.get("formulaDraft") or "")
    if draft.get("function") != "RssStockOrder" or "RssMargin" in formula:
        raise ValueError("CASH_RSS_STOCK_ORDER_REQUIRED")
    if draft.get("trigger") != 0 or draft.get("transmitted") is not False:
        raise ValueError("DRAFT_NOT_LOCKED")
    return {
        "schemaId":"ARK_LOCKED_EXCEL_INTERFACE_V1",
        "sheet":"ARK_CASH_ORDER_LOCKED",
        "cells":{
            "B3":"LOCKED / NO TRANSMISSION",
            "B4":"CASH ONLY",
            "B5":"DISABLED",
            "B6":"DISABLED",
            "B8":intent.get("symbol"),
            "B9":intent.get("side"),
            "B10":intent.get("quantity"),
            "B11":0,
            "B12":buying_power,
            "B13":formula,
            "B15":"FALSE",
            "B16":"FALSE",
            "B17":"FALSE",
            "B18":"READY FOR MARKETSPEED PHYSICAL UNLOCK",
        },
        "cellTypes":{"B13":"TEXT"},
        "formulaEvaluationAllowed":False,
        "excelOrderWriteAllowed":False,
        "rssCallAllowed":False,
        "transmitted":False,
    }
