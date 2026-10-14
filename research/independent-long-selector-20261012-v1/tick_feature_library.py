"""Causal trade-by-trade Tick features from normalized, authorized J-Quants A/B rows.

Trade-price direction is NOT buyer/seller aggressor inference. An absent side
field remains UNKNOWN. No quote or order-book value is fabricated from prints.
"""
from __future__ import annotations

import math
import statistics
from collections import Counter
from datetime import datetime,timedelta
from typing import Any

TICK_FEATURE_VERSION="ARK_INDEPENDENT_TICK_FULL_V1"
TICK_WINDOWS=(1,5,15,30,60)
REQUIRED_TICK_FIELDS=("tradeAt","availableAt","price","quantity")


class TickSourceError(ValueError):
    pass


def tick_registry()->tuple[str,...]:
    out=set()
    for n in TICK_WINDOWS:
        out.update((
            f"tick_trade_count_{n}m",f"tick_volume_{n}m",f"tick_value_{n}m",
            f"tick_vwap_distance_{n}m_pct",
            f"tick_realized_volatility_{n}m",
            f"tick_price_range_{n}m_pct",f"tick_up_tick_ratio_{n}m",
            f"tick_burst_relative_{n}m",f"tick_size_zscore_{n}m",
        ))
    out.update(("tick_avg_trade_size","tick_median_trade_size",
        "tick_p90_trade_size","tick_p99_trade_size",
        "tick_large_trade_fraction","tick_ups_vs_down_ticks",
        "tick_price_change_frequency","tick_price_entropy",
        "tick_realized_volatility","tick_last_trade_age_seconds",
        "tick_trade_interval_mean_seconds","tick_trade_interval_p90_seconds",
        "tick_aggressor_buy_ratio","tick_aggressor_sell_ratio",
        "tick_aggressor_net_volume_ratio",
        "tick_aggressor_net_value_ratio","tick_spread_proxy_bps"))
    return tuple(sorted(out))


def _date(value):
    try:dt=datetime.fromisoformat(value)
    except (ValueError,TypeError) as exc:raise TickSourceError("TICK_BAD_TIMESTAMP") from exc
    if dt.tzinfo is None or dt.utcoffset()!=timedelta(hours=9):
        raise TickSourceError("TICK_JST_REQUIRED")
    return dt


def _pct(x,base):
    return 100*(x/base-1) if base>0 else None


def _quantile(values,q):
    if not values:return None
    v=sorted(values)
    ix=(len(v)-1)*q
    lo=int(ix);hi=min(lo+1,len(v)-1)
    return v[lo]+(v[hi]-v[lo])*(ix-lo)


def _entropy(prices):
    if len(prices)<2:return None
    counts=Counter(1 if prices[i]>prices[i-1]
                   else -1 if prices[i]<prices[i-1] else 0
                   for i in range(1,len(prices)))
    n=sum(counts.values())
    return -sum((v/n)*math.log(v/n) for v in counts.values())/math.log(3)


def compute_tick_features(events:list[dict[str,Any]]|None, *,
                          decision_at:str, decision_price:float,
                          complete_stream_verified:bool,
                          side_semantics_verified:bool=False
                          )->dict[str,float|None]:
    result={name:None for name in tick_registry()}
    if events is None or not complete_stream_verified:
        return result
    now=_date(decision_at)
    if not math.isfinite(decision_price) or decision_price<=0:
        raise TickSourceError("TICK_BAD_DECISION_PRICE")
    observed=[]
    prev=None
    for r in events:
        for name in REQUIRED_TICK_FIELDS:
            if name not in r:raise TickSourceError(f"TICK_MISSING_{name}")
        t=_date(r["tradeAt"])
        known=_date(r["availableAt"])
        if t>known or known>now or t.date()!=now.date():
            raise TickSourceError("TICK_FUTURE_OR_SESSION_MISMATCH")
        if prev is not None and t<prev:
            raise TickSourceError("TICK_NOT_CHRONOLOGICAL")
        prev=t
        price=float(r["price"]);amount=float(r["quantity"])
        if not math.isfinite(price) or not math.isfinite(amount) or price<=0 or amount<=0:
            raise TickSourceError("TICK_BAD_PRICE_OR_QUANTITY")
        value=float(r.get("value",price*amount))
        if not math.isfinite(value) or value<0:
            raise TickSourceError("TICK_BAD_TRADING_VALUE")
        row={"dt":t,"price":price,"quantity":amount,"value":value}
        side=r.get("aggressorSide")
        if side_semantics_verified and side not in ("BUY","SELL",None):
            raise TickSourceError("TICK_INVALID_VERIFIED_AGGRESSOR")
        row["side"]=side if side_semantics_verified else None
        observed.append(row)
    if not observed:
        # Verified complete source and no trades: a valid zero count, not
        # zero-filled returns or an artificial flat price.
        for n in TICK_WINDOWS:
            result[f"tick_trade_count_{n}m"]=0.0
            result[f"tick_volume_{n}m"]=0.0
            result[f"tick_value_{n}m"]=0.0
        return result
    age=(now-observed[-1]["dt"]).total_seconds()
    result["tick_last_trade_age_seconds"]=age
    last=observed[-1]
    recent=[x for x in observed if x["dt"]>now-timedelta(minutes=60)]
    if not recent:
        return result
    prices=[x["price"] for x in recent]
    quantity=[x["quantity"] for x in recent]
    result["tick_avg_trade_size"]=statistics.mean(quantity)
    result["tick_median_trade_size"]=statistics.median(quantity)
    result["tick_p90_trade_size"]=_quantile(quantity,.90)
    result["tick_p99_trade_size"]=_quantile(quantity,.99)
    limit=3*statistics.median(quantity)
    result["tick_large_trade_fraction"]=sum(x>limit for x in quantity)/len(quantity)
    movements=[1 if prices[i]>prices[i-1] else -1 if prices[i]<prices[i-1] else 0
               for i in range(1,len(prices))]
    if movements:
        result["tick_ups_vs_down_ticks"]=sum(movements)/len(movements)
        result["tick_price_change_frequency"]=sum(v!=0 for v in movements)/len(movements)
        result["tick_price_entropy"]=_entropy(prices)
        logret=[math.log(prices[i]/prices[i-1]) for i in range(1,len(prices))]
        result["tick_realized_volatility"]=statistics.pstdev(logret)*100
    if len(recent)>1:
        intervals=[(recent[i]["dt"]-recent[i-1]["dt"]).total_seconds()
                    for i in range(1,len(recent))]
        result["tick_trade_interval_mean_seconds"]=statistics.mean(intervals)
        result["tick_trade_interval_p90_seconds"]=_quantile(intervals,.9)
    if side_semantics_verified:
        sided=[x for x in recent if x["side"] in ("BUY","SELL")]
        if len(sided)==len(recent):
            n=len(recent);nv=sum(x["quantity"] for x in recent)
            vv=sum(x["value"] for x in recent)
            buys=[x for x in recent if x["side"]=="BUY"]
            sells=[x for x in recent if x["side"]=="SELL"]
            result["tick_aggressor_buy_ratio"]=len(buys)/n
            result["tick_aggressor_sell_ratio"]=len(sells)/n
            result["tick_aggressor_net_volume_ratio"]=(
                (sum(x["quantity"] for x in buys)-sum(x["quantity"] for x in sells))/nv if nv else None)
            result["tick_aggressor_net_value_ratio"]=(
                (sum(x["value"] for x in buys)-sum(x["value"] for x in sells))/vv if vv else None)
    # Tick source does not prove bid/ask quotes: spread remains UNKNOWN.
    for n in TICK_WINDOWS:
        window=[x for x in observed if x["dt"]>now-timedelta(minutes=n)]
        older=[x for x in observed
               if now-timedelta(minutes=2*n)<x["dt"]<=now-timedelta(minutes=n)]
        count=len(window)
        result[f"tick_trade_count_{n}m"]=float(count)
        vol=sum(x["quantity"] for x in window)
        value=sum(x["value"] for x in window)
        result[f"tick_volume_{n}m"]=vol
        result[f"tick_value_{n}m"]=value
        if window and vol:
            vwap=value/vol
            result[f"tick_vwap_distance_{n}m_pct"]=_pct(decision_price,vwap)
            highs=max(x["price"] for x in window)
            lows=min(x["price"] for x in window)
            result[f"tick_price_range_{n}m_pct"]=100*(highs-lows)/vwap
            v=[x["price"] for x in window]
            changes=[1 if v[i]>v[i-1] else -1 if v[i]<v[i-1] else 0
                     for i in range(1,len(v))]
            result[f"tick_up_tick_ratio_{n}m"]=(
                sum(x>0 for x in changes)/len(changes) if changes else None)
            lrets=[math.log(v[i]/v[i-1]) for i in range(1,len(v))]
            result[f"tick_realized_volatility_{n}m"]=(
                100*statistics.pstdev(lrets) if lrets else None)
            sizes=[x["quantity"] for x in window]
            sigma=statistics.pstdev(sizes)
            result[f"tick_size_zscore_{n}m"]=(
                (sizes[-1]-statistics.mean(sizes))/sigma if sigma else 0.0)
        if older:
            result[f"tick_burst_relative_{n}m"]=count/len(older)
    for key,v in result.items():
        if v is not None and not math.isfinite(v):
            raise TickSourceError(f"TICK_NONFINITE_FEATURE:{key}")
    return result
