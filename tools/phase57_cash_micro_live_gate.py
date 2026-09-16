"""G10 cash-only micro-live preflight.

Produces the final preflight envelope while transmission remains disabled. The
only supported product is cash equity LONG via RssStockOrder. Margin and short
selling have no path through this module.
"""
from __future__ import annotations


def build_micro_live_preflight(*, unlock_candidate, draft, ark_managed_positions=None, open_order_count=0):
    blockers=[]
    if not unlock_candidate.get("eligible") or not unlock_candidate.get("candidateToken"):
        blockers.append("G9_UNLOCK_CANDIDATE_REQUIRED")
    if unlock_candidate.get("cashOnly") is not True:
        blockers.append("CASH_ONLY_REQUIRED")
    if unlock_candidate.get("marginAllowed") is not False:
        blockers.append("MARGIN_MUST_BE_DISABLED")
    if unlock_candidate.get("shortSellingAllowed") is not False:
        blockers.append("SHORT_SELLING_MUST_BE_DISABLED")

    if draft.get("function") != "RssStockOrder":
        blockers.append("RSS_STOCK_ORDER_ONLY")
    intent=draft.get("intent") or {}
    if intent.get("direction") != "LONG": blockers.append("LONG_ONLY")
    side=intent.get("side"); effect=intent.get("positionEffect")
    if effect == "OPEN" and side != "BUY": blockers.append("OPEN_BUY_ONLY")
    if effect == "CLOSE" and side != "SELL": blockers.append("CLOSE_SELL_ONLY")
    if draft.get("trigger") != 0 or draft.get("transmitted") is not False:
        blockers.append("TRANSMISSION_MUST_REMAIN_LOCKED")
    if open_order_count != 0:
        blockers.append("ONE_ORDER_AT_A_TIME")

    positions={}
    for row in ark_managed_positions or []:
        symbol=str(row.get("symbol") or "").upper()
        qty=row.get("quantity")
        if symbol and isinstance(qty,(int,float)):
            positions[symbol]=positions.get(symbol,0)+qty
    if effect == "CLOSE" and side == "SELL":
        held=positions.get(str(intent.get("symbol") or "").upper(),0)
        qty=intent.get("quantity")
        if not isinstance(qty,int) or qty <= 0 or qty > held:
            blockers.append("SELL_EXCEEDS_ARK_MANAGED_POSITION")

    forbidden=("RssMarginOpenOrder","RssMarginCloseOrder")
    formula=str(draft.get("formulaDraft") or "")
    if any(x in formula for x in forbidden):
        blockers.append("MARGIN_FUNCTION_PRESENT")

    blockers=list(dict.fromkeys(blockers))
    ready=not blockers
    return {
        "schemaId":"ARK_CASH_MICRO_LIVE_PREFLIGHT_V1",
        "readyForPhysicalUnlock":ready,
        "candidateToken":unlock_candidate.get("candidateToken") if ready else None,
        "blockers":blockers,
        "cashOnly":True,
        "marginAllowed":False,
        "shortSellingAllowed":False,
        "physicalUnlock":"MARKETSPEED_EXCEL_ORDER_ENABLE_REQUIRED",
        "executionAllowed":False,
        "transmitted":False,
        "rssCallPerformed":False,
        "excelOrderWritePerformed":False,
    }
