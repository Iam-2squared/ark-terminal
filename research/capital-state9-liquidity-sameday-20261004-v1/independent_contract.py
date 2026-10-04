"""Independent reconstruction: intentionally no primary module import."""
from datetime import datetime
from decimal import Decimal

def runtime_oracle(row):
    t = datetime.fromisoformat(row["fill_timestamp"])
    allowed = (t.hour, t.minute, t.second) < (15, 20, 0)
    s = (row.get("first_intent") or {}).get("score")
    if not isinstance(s, (float, int)) or not 0 <= s <= 1:
        s = None
    return {"entry_id": row["watch_key"], "session": row["session"], "symbol": row["symbol"],
            "entry_timestamp": row["fill_timestamp"], "entry_effective_price": str(row["fill_price"]),
            "score": s, "eligible": allowed,
            "cutoff_reason": None if allowed else "CAPITAL_EOD_ENTRY_CUTOFF"}

def capacity_oracle(date, calendar, records):
    required = tuple(calendar[-20:])
    if len(required) != 20 or len(set(required)) != 20 or max(required) >= date:
        return None
    values = []
    for day in required:
        candidates = [Decimal(str(x["Va"])) for x in records if x.get("Date") == day
                      and x.get("known_session", day) < date and x.get("Va") is not None]
        candidates = [v for v in candidates if v.is_finite() and v > 0]
        if not candidates or len(set(candidates)) != 1:
            return None
        values.append(candidates[0])
    values.sort()
    return (values[9] + values[10]) / Decimal(200)

def quantity_oracle(r, target, cash, cap, liq):
    if not r["eligible"]:
        return 0, "CAPITAL_EOD_ENTRY_CUTOFF"
    if r["score"] is None:
        return 0, "CAPITAL_SCORE_INPUT_UNKNOWN"
    if liq is None:
        return 0, "CAPITAL_LIQUIDITY_INPUT_UNKNOWN"
    p = Decimal(r["entry_effective_price"])
    limit = min(Decimal(str(x)) for x in [target, cash, cap, liq])
    count = int(limit // (p * 100)) * 100
    return (count, None) if count > 0 else (0, "CAPITAL_SKIP_LIQUIDITY" if Decimal(str(liq)) < p * 100 else "CAPITAL_LOT_OR_CASH_CONSTRAINED")

def intent_oracle(position, flag=None):
    if position.get("quantity", 0) < 1 or position.get("closed", False):
        return None
    if position.get("side", "LONG") != "LONG" or position.get("margin", False):
        raise ValueError("LONG cash")
    day=position["session"]
    deadline=datetime.fromisoformat(day+"T15:20:00+09:00")
    good=False
    if flag and flag.get("status")=="UPPER_LIMIT_CONFIRMED" and flag.get("authoritative") is True and flag.get("session")==day:
        if flag.get("observed_at") and flag.get("known_at"):
            good=all(datetime.fromisoformat(flag[x])<=deadline for x in ["observed_at","known_at"])
    return {"policy_id":"LIMIT_UP_HOLD_TO_CLOSING_AUCTION_V1" if good else "EOD_LIQUIDATION_1520_SOR_MARKET_V1",
            "intent_timestamp":day+("T15:25:00+09:00" if good else "T15:20:00+09:00"),
            "side":"SELL","quantity":position["quantity"],"sor":not good,"order_type":"MARKET",
            "condition":"DAY","transmitted":False,"limit_up_status":"CONFIRMED" if good else "UNKNOWN_NORMAL_ROUTE"}

def outcome_oracle(order, trades, closing):
    if order is None:return None
    eligible=[]
    if order["sor"]:
        for row in trades:
            t=datetime.fromisoformat(row["timestamp"])
            if (t.hour,t.minute)>=(15,20) and (t.hour,t.minute)<(15,25) and t>=datetime.fromisoformat(order["intent_timestamp"]):
                if Decimal(str(row.get("Open",0)))>0 and Decimal(str(row.get("Volume",0)))>0 and row.get("lineage"):
                    eligible.append(row)
    eligible.sort(key=lambda r:r["timestamp"])
    selected=eligible[0] if eligible else None
    kind="REGULAR_OPEN" if selected else None
    if selected is None and closing:
        t=datetime.fromisoformat(closing["timestamp"])
        if (t.hour,t.minute)==(15,30) and closing.get("valid_exact_auction") is True and closing.get("lineage"):
            if Decimal(str(closing.get("Open",0)))>0 and Decimal(str(closing.get("Volume",0)))>0:
                selected=closing;kind="EXACT_CLOSING_AUCTION"
    if selected is None:
        return {"status":"POSITION_MEASUREMENT_BLOCKED","effective_price":None,"cash_release":Decimal(0),
                "cash_release_timestamp":None,"pnl":None,"reason":"LIMIT_UP_EOD_UNEXECUTED_FAIL_CLOSED" if not order["sor"] else "EOD_UNEXECUTED_FAIL_CLOSED"}
    price=Decimal(str(selected["Open"]))*Decimal("0.9995")
    return {"status":"REFERENCE_FILLED","source_type":kind,"effective_price":price,"cash_release":price*order["quantity"],
            "cash_release_timestamp":selected["assumed_available_at"],"commission":Decimal(0),"actual_arrival":"UNKNOWN","live_full_fill_certified":False}
