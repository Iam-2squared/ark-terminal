"""Precommitted cash-LONG Capital contracts. Future outcomes are separate arguments."""
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
from statistics import median
import math

POLICY = "CAPITAL_FUNDING_CONDITIONAL_EXECUTION_ADMISSION_V1"
LOT = 100
BUY_FACTOR = Decimal("1.0005")
SELL_FACTOR = Decimal("0.9995")

def timestamp(value):
    return datetime.fromisoformat(value)

def minute(value):
    t = timestamp(value)
    return t.hour * 60 + t.minute

def candidate_runtime(row):
    """Explicit allowlist: no execution evidence, future labels or later State."""
    intent = row.get("first_intent") or {}
    score = intent.get("score")
    valid = isinstance(score, (int, float)) and math.isfinite(score) and 0 <= score <= 1
    return {"entry_id": row["watch_key"], "session": row["session"],
            "symbol": row["symbol"], "entry_timestamp": row["fill_timestamp"],
            "entry_effective_price": str(row["fill_price"]),
            "score": float(score) if valid else None,
            "eligible": minute(row["fill_timestamp"]) < 920,
            "cutoff_reason": None if minute(row["fill_timestamp"]) < 920 else "CAPITAL_EOD_ENTRY_CUTOFF"}

def liquidity_capacity(entry_session, prior_sessions, rows):
    """Require exact20 immediately prior trading dates; no prior1 substitution."""
    expected = list(prior_sessions)[-20:]
    if len(expected) != 20 or len(set(expected)) != 20 or any(d >= entry_session for d in expected):
        return None
    by_date = {}
    for r in rows:
        d, value = r.get("Date"), r.get("Va")
        if d not in expected or value is None:
            continue
        try:
            v = Decimal(str(value))
            known_date = r.get("known_session", d)
            if v.is_finite() and v > 0 and known_date < entry_session:
                if d in by_date and by_date[d] != v:
                    return None
                by_date[d] = v
        except Exception:
            continue
    if set(by_date) != set(expected):
        return None
    return median(by_date[d] for d in expected) * Decimal("0.01")

def quantity(runtime, target, cash, equity_cap, liquidity):
    if not runtime["eligible"]:
        return 0, "CAPITAL_EOD_ENTRY_CUTOFF"
    if runtime["score"] is None:
        return 0, "CAPITAL_SCORE_INPUT_UNKNOWN"
    if liquidity is None:
        return 0, "CAPITAL_LIQUIDITY_INPUT_UNKNOWN"
    p = Decimal(runtime["entry_effective_price"])
    if not p.is_finite() or p <= 0:
        return 0, "CAPITAL_PRICE_INPUT_INVALID"
    lim = min(Decimal(str(target)), Decimal(str(cash)), Decimal(str(equity_cap)), Decimal(str(liquidity)))
    q = int((lim / (p * LOT)).to_integral_value(rounding=ROUND_FLOOR)) * LOT
    if q <= 0:
        reason = "CAPITAL_SKIP_LIQUIDITY" if Decimal(str(liquidity)) < p * LOT else "CAPITAL_LOT_OR_CASH_CONSTRAINED"
        return 0, reason
    return q, None

def eod_intent(position, limit_flag=None):
    """The decision is made without any execution/price suffix argument."""
    if position.get("quantity", 0) <= 0 or position.get("closed", False):
        return None
    session = position["session"]
    if position.get("side", "LONG") != "LONG" or position.get("margin", False):
        raise ValueError("cash LONG required")
    cutoff = session + "T15:20:00+09:00"
    confirmed = bool(limit_flag and limit_flag.get("status") == "UPPER_LIMIT_CONFIRMED"
                     and limit_flag.get("authoritative") is True
                     and limit_flag.get("observed_at") and limit_flag.get("known_at")
                     and timestamp(limit_flag["known_at"]) <= timestamp(cutoff)
                     and timestamp(limit_flag["observed_at"]) <= timestamp(cutoff)
                     and limit_flag.get("session") == session)
    return {"policy_id": "LIMIT_UP_HOLD_TO_CLOSING_AUCTION_V1" if confirmed else "EOD_LIQUIDATION_1520_SOR_MARKET_V1",
            "intent_timestamp": session + ("T15:25:00+09:00" if confirmed else "T15:20:00+09:00"),
            "side": "SELL", "quantity": position["quantity"], "sor": not confirmed,
            "order_type": "MARKET", "condition": "DAY", "transmitted": False,
            "limit_up_status": "CONFIRMED" if confirmed else "UNKNOWN_NORMAL_ROUTE"}

def execution_outcome(intent, regular, auction):
    if intent is None:
        return None
    sources = []
    if intent["sor"]:
        sources = [r for r in regular if 920 <= minute(r["timestamp"]) < 925
                   and timestamp(r["timestamp"]) >= timestamp(intent["intent_timestamp"])
                   and Decimal(str(r.get("Open", 0))) > 0 and Decimal(str(r.get("Volume", 0))) > 0
                   and r.get("lineage")]
    source = min(sources, key=lambda r: r["timestamp"]) if sources else None
    source_type = "REGULAR_OPEN" if source else None
    if source is None and auction and minute(auction["timestamp"]) == 930 and auction.get("valid_exact_auction") is True and auction.get("lineage"):
        if Decimal(str(auction.get("Open", 0))) > 0 and Decimal(str(auction.get("Volume", 0))) > 0:
            source, source_type = auction, "EXACT_CLOSING_AUCTION"
    if source is None:
        return {"status": "POSITION_MEASUREMENT_BLOCKED", "effective_price": None,
                "cash_release": Decimal(0), "cash_release_timestamp": None, "pnl": None,
                "reason": "LIMIT_UP_EOD_UNEXECUTED_FAIL_CLOSED" if not intent["sor"] else "EOD_UNEXECUTED_FAIL_CLOSED"}
    effective = Decimal(str(source["Open"])) * SELL_FACTOR
    return {"status": "REFERENCE_FILLED", "source_type": source_type, "effective_price": effective,
            "cash_release": effective * intent["quantity"],
            "cash_release_timestamp": source["assumed_available_at"], "commission": Decimal(0),
            "actual_arrival": "UNKNOWN", "live_full_fill_certified": False}

def accounting(buy, sell, q):
    debit, credit = Decimal(str(buy)) * q, Decimal(str(sell)) * q
    return {"debit": debit, "credit": credit, "pnl": credit - debit, "commission": Decimal(0)}

def rank_prefix(score, entry_timestamp, state_events):
    # Contract canary feature snapshot, not a fitted State-aware score or human ordinal.
    known = [e for e in state_events if timestamp(e["known_at"]) <= timestamp(entry_timestamp)
             and timestamp(e["observed_at"]) <= timestamp(entry_timestamp)]
    known.sort(key=lambda e: (e["known_at"], e["observed_at"]))
    return score, tuple(e["primary"] for e in known)
