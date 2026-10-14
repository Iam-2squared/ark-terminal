"""The 51 registered daily features, with finite seeded histories."""
from __future__ import annotations
from datetime import date
from fractions import Fraction as F
import math
from .contracts import Candle, FeatureFrame
from .exact_math import V2Error, median, sma, wilder
from .gates import atr_pre


def ema(closes: list[F], n: int) -> list[F | None]:
    out: list[F | None] = [None] * len(closes)
    if len(closes) < n:
        return out
    value = sum(closes[:n], F()) / n
    out[n-1] = value
    alpha = F(2, n+1)
    for i in range(n, len(closes)):
        value = alpha*closes[i] + (1-alpha)*value
        out[i] = value
    return out


def daily_features(history: list[Candle], t: date) -> FeatureFrame:
    # Ignore future records before value parsing; an ingress adapter still rejects
    # a D/future descriptor, while this pure as-of calculation is poison-invariant.
    rows = [r for r in history if r.session <= t]
    if rows and rows[-1].session != t:
        rows = []
    if rows:
        suffix = rows[-1].comparable_suffix
        start = len(rows)-1
        while start > 0 and rows[start-1].comparable_suffix == suffix:
            start -= 1
        rows = rows[start:]
    for r in rows:
        r.validate()
        if r.basis != "RAW" or r.units != ("JPY", "SHARES", "JPY"):
            raise V2Error("RAW_BASIS_OR_UNITS_NOT_VERIFIED")
    cs = [r.close for r in rows]
    out = FeatureFrame()
    atr = atr_pre(rows)

    def close_tail(n: int) -> list[F] | None:
        tail = cs[-n:]
        return [v for v in tail if v is not None] if len(tail) == n and all(v is not None for v in tail) else None

    def candles(n: int) -> list[Candle] | None:
        tail = rows[-n:]
        return tail if len(tail) == n and all(r.close is not None for r in tail) else None

    def ratio(a: F | float | None, b: F | float | None) -> F | float | None:
        return None if a is None or b is None or b == 0 else a/b

    def pct(a: F | None, b: F | None) -> F | None:
        return None if a is None or b is None or b <= 0 else 100*(a/b-1)

    def wick(row: Candle, upper: bool = True) -> F | None:
        o, h, l, c = row.open, row.high, row.low, row.close
        if o is None or h is None or l is None or c is None or h == l:
            return None
        return (h-max(o,c))/(h-l) if upper else (min(o,c)-l)/(h-l)

    c = rows[-1].close if rows else None
    seeded = close_tail(150)
    for n in (5, 15, 25, 75):
        h = 3 if n == 5 else 15 if n == 75 else 5
        tail = close_tail(n)
        s = sma(tail,n) if tail else None
        p1 = close_tail(n+1)
        ph = close_tail(n+h)
        p3 = close_tail(n+3)
        en = ema(seeded,n)[-1] if seeded else None
        out.put(f"v2_sma_distance_{n}", pct(c,s))
        out.put(f"v2_sma_slope1_atr_{n}", ratio(sma(p1,n)-sma(p1,n,1),atr) if p1 else None,
                "ZERO_ATR" if atr == 0 else "UNKNOWN_REQUIRED_HISTORY")
        out.put(f"v2_sma_slopeH_atr_{n}", ratio(sma(ph,n)-sma(ph,n,h),h*atr if atr is not None else None) if ph else None)
        out.put(f"v2_ema_distance_{n}",pct(c,en),"UNKNOWN_FIXED_150_CLOSE_HISTORY")
        out.put(f"v2_sma_up_fraction3_{n}", F(sum(p3[-1-j] > p3[-1-j-n] for j in range(3)),3) if p3 else None)
    for n in (1,5,15,25,60):
        tail = close_tail(n+1)
        out.put(f"v2_return_{n}d",pct(tail[-1],tail[0]) if tail else None)
    for n in (20,60):
        candle_tail = candles(n+1)
        prior = candle_tail[:-1] if candle_tail else []
        highs = [r.high for r in prior]
        lows = [r.low for r in prior]
        out.put(f"v2_prior_high_gap_{n}",pct(c,max(x for x in highs if x is not None)) if prior and all(x is not None for x in highs) else None)
        out.put(f"v2_prior_low_buffer_{n}",pct(c,min(x for x in lows if x is not None)) if prior and all(x is not None for x in lows) else None)
    tail10 = candles(10)
    out.put("v2_block_high_lift5",pct(max(r.high for r in tail10[5:] if r.high is not None),max(r.high for r in tail10[:5] if r.high is not None)) if tail10 else None)
    out.put("v2_block_low_lift5",pct(min(r.low for r in tail10[5:] if r.low is not None),min(r.low for r in tail10[:5] if r.low is not None)) if tail10 else None)
    now = rows[-1] if rows else None
    prev = cs[-2] if len(cs)>1 else None
    out.put("v2_candle_body",pct(c,now.open) if now else None)
    out.put("v2_candle_range",ratio(100*(now.high-now.low),prev) if now and now.high is not None and now.low is not None else None)
    out.put("v2_close_location",ratio(now.close-now.low,now.high-now.low) if now and now.close is not None and now.low is not None and now.high is not None else None,"ZERO_CANDLE_RANGE")
    out.put("v2_upper_wick_ratio",wick(now) if now else None,"ZERO_CANDLE_RANGE")
    out.put("v2_lower_wick_ratio",wick(now,False) if now else None,"ZERO_CANDLE_RANGE")
    out.put("v2_atr_pre_pct",ratio(100*atr,prev) if atr is not None else None)
    p20 = close_tail(21)
    logreturns = [math.log(float(b/a)) for a,b in zip(p20[:-1],p20[1:])] if p20 else []
    out.put("v2_downside_vol20",100*math.sqrt(sum(min(x,0)**2 for x in logreturns)/20) if logreturns else None)
    if p20:
        path = sum((abs(b-a) for a,b in zip(p20[:-1],p20[1:])),F())
        efficiency = abs(p20[-1]-p20[0])/path if path else F(0)
    else:
        efficiency = None
    out.put("v2_price_efficiency20",efficiency)
    last5 = candles(5)
    ws = [wick(r) for r in last5] if last5 else []
    out.put("v2_mean_upper_wick5",sum((x for x in ws if x is not None),F())/5 if ws and all(x is not None for x in ws) else None,"UNDEFINED_WICK_IN_5_SESSION_WINDOW")
    last20 = candles(20)
    out.put("v2_up_candle_fraction20",F(sum(r.close > r.open for r in last20 if r.close is not None and r.open is not None),20) if last20 else None)
    line = signal = None
    if seeded:
        e12,e26 = ema(seeded,12),ema(seeded,26)
        macd = [a-b for a,b in zip(e12,e26) if a is not None and b is not None]
        line = macd[-1]
        signal = ema(macd,9)[-1]
    line_pct = ratio(100*line,c) if line is not None else None
    signal_pct = ratio(100*signal,c) if signal is not None else None
    out.put("v2_macd_line_pct",line_pct,"UNKNOWN_FIXED_150_CLOSE_HISTORY")
    out.put("v2_macd_signal_pct",signal_pct,"UNKNOWN_FIXED_150_CLOSE_HISTORY")
    out.put("v2_macd_histogram_pct",line_pct-signal_pct if line_pct is not None and signal_pct is not None else None)
    p75 = close_tail(76)
    rsi = None
    if p75:
        changes = [b-a for a,b in zip(p75[:-1],p75[1:])]
        gain=wilder([max(F(0),x) for x in changes])
        loss=wilder([max(F(0),-x) for x in changes])
        rsi=F(50) if gain==loss==0 else F(100) if loss==0 else F(0) if gain==0 else 100*gain/(gain+loss)
    out.put("v2_rsi14",rsi)
    va20=[r.turnover for r in rows[-20:]]
    valid20=len(va20)==20 and all(x is not None for x in va20)
    vat=now.turnover if now else None
    med20=median([x for x in va20 if x is not None]) if valid20 else None
    out.put("v2_log_turnover_t",math.log1p(float(vat)) if vat is not None else None,"UNKNOWN_TURNOVER")
    out.put("v2_log_median_turnover20",math.log1p(float(med20)) if med20 is not None else None)
    for attr,name in (("turnover","turnover"),("volume","volume")):
        values=[getattr(r,attr) for r in rows[-21:-1]]
        med=median([x for x in values if x is not None]) if len(values)==20 and all(x is not None for x in values) else None
        out.put(f"v2_{name}_spike",ratio(getattr(now,attr),med) if now else None,"ZERO_OR_UNKNOWN_PRIOR_ACTIVITY")
    amihud=None
    if p20 and valid20 and all(x is not None and x>0 for x in va20):
        amihud=sum((abs(b/a-1)/(v/F(100000000)) for a,b,v in zip(p20[:-1],p20[1:],va20) if v is not None),F())/20
    out.put("v2_amihud20_scaled",amihud,"ZERO_OR_UNKNOWN_TURNOVER_IN_WINDOW")
    b20=min(vat,med20) if vat is not None and med20 is not None else None
    out.put("v2_reference_capacity_share",ratio(F(1000000),b20),"ZERO_OR_UNKNOWN_CAPACITY")
    out.metadata["daily_history_closes"]=len(rows)
    return out
