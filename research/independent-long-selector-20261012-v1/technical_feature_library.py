"""PIT technical feature library for J-Quants daily and continuous minute OHLCV.

Every output is causal and calculation-only. Missing observations stay None.
No source download, feature selection by future outcome, model fitting, or orders.
"""
from __future__ import annotations

import math
import statistics
from collections import Counter
from typing import Any

# User-approved DAILY moving-average lines, and no others.
# The indicator lookbacks below are NOT additional moving-average lines.
DAILY_PERIODS = (5, 15, 25, 75)
MINUTE_PERIODS = (5, 15, 30, 60)
CROSSOVER_PAIRS = ((5, 15), (5, 25), (5, 75),
                   (15, 25), (15, 75), (25, 75))
OSCILLATOR_PERIODS = (14,)
MA_FAMILIES = ("sma", "ema")
from preopen_feature_policy import (VERSION as REGISTRY_VERSION, indicator_parameters,
                                    scope, LATEST_NAMES, OSCILLATOR_NAMES)
OHLCV_FIELDS = ("open", "high", "low", "close", "volume", "turnover")


def _avg(xs):
    return sum(xs) / len(xs) if xs else None


def _pct(x, ref):
    return 100.0 * (x / ref - 1.0) if x is not None and ref is not None and ref > 0 else None


def _ema(xs, n):
    if len(xs) < n:
        return None
    out = _avg(xs[:n])
    for x in xs[n:]:
        out += (x - out) * (2.0 / (n + 1.0))
    return out


def _ema_trace(xs, n):
    if len(xs) < n:
        return []
    result = [_avg(xs[:n])]
    for x in xs[n:]:
        result.append(result[-1] + (x - result[-1]) * (2.0 / (n + 1.0)))
    return result


def _rsi(xs, n):
    if len(xs) < n + 1:
        return None
    dif = [xs[i] - xs[i - 1] for i in range(1, len(xs))]
    gains = _wilder([max(x, 0) for x in dif], n)[-1]
    losses = _wilder([max(-x, 0) for x in dif], n)[-1]
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    return 100.0 * gains / (gains + losses)


def _atr(bars, n):
    if len(bars) < n + 1:
        return None
    truths = []
    for i in range(1, len(bars)):
        b, prev = bars[i], bars[i - 1]
        truths.append(max(
            b["high"] - b["low"],
            abs(b["high"] - prev["close"]),
            abs(b["low"] - prev["close"]),
        ))
    return _wilder(truths, n)[-1]


def _wilder(values, n):
    if len(values) < n:
        return []
    out = [_avg(values[:n])]
    for value in values[n:]:
        out.append(out[-1] + (value-out[-1])/n)
    return out


def _efficiency(values):
    if len(values) < 2:
        return None
    dist = sum(abs(values[i] - values[i - 1]) for i in range(1, len(values)))
    return abs(values[-1] - values[0]) / dist if dist else 0.0


def _moneyflow(bars, n):
    if len(bars) < n + 1:
        return None
    pos = neg = 0.0
    for i in range(len(bars) - n, len(bars)):
        current, previous = bars[i], bars[i - 1]
        tp = (current["high"] + current["low"] + current["close"]) / 3
        pt = (previous["high"] + previous["low"] + previous["close"]) / 3
        flow = tp * current["volume"]
        if tp > pt:
            pos += flow
        elif tp < pt:
            neg += flow
    if neg == 0:
        return 100.0 if pos > 0 else 50.0
    return 100 * pos / (pos + neg)


def _williams(bars, n):
    if len(bars) < n:
        return None
    h = max(b["high"] for b in bars[-n:])
    l = min(b["low"] for b in bars[-n:])
    return -100.0 * (h - bars[-1]["close"]) / (h - l) if h > l else -50.0


def _stochastic(bars, n):
    w = _williams(bars, n)
    return 100.0 + w if w is not None else None


def _cci(bars, n):
    if len(bars) < n:
        return None
    typical = [(b["high"] + b["low"] + b["close"]) / 3 for b in bars[-n:]]
    avg = _avg(typical)
    dev = _avg([abs(x - avg) for x in typical])
    return (typical[-1] - avg) / (0.015 * dev) if dev else 0.0


def _cmf(bars, n):
    if len(bars) < n:
        return None
    subset = bars[-n:]
    volume = sum(b["volume"] for b in subset)
    if volume <= 0:
        return None
    accum = 0.0
    for b in subset:
        r = b["high"] - b["low"]
        accum += ((2 * b["close"] - b["high"] - b["low"]) / r
                  if r else 0.0) * b["volume"]
    return accum / volume


def _adx(bars, n):
    if len(bars) < n * 2 + 1:
        return None, None, None
    tr, p_dm, m_dm = [], [], []
    for i in range(1, len(bars)):
        b, p = bars[i], bars[i - 1]
        rise, fall = b["high"] - p["high"], p["low"] - b["low"]
        p_dm.append(rise if rise > fall and rise > 0 else 0.0)
        m_dm.append(fall if fall > rise and fall > 0 else 0.0)
        tr.append(max(b["high"] - b["low"],
                      abs(b["high"] - p["close"]),
                      abs(b["low"] - p["close"])))
    smoothed = zip(_wilder(tr,n),_wilder(p_dm,n),_wilder(m_dm,n))
    dx = []
    for total, plus, minus in smoothed:
        pdi = 100*plus/total if total > 0 else 0.0
        mdi = 100*minus/total if total > 0 else 0.0
        dx.append(100*abs(pdi-mdi)/(pdi+mdi) if pdi+mdi else 0.0)
    return _wilder(dx,n)[-1], pdi, mdi


def _max_drawdown(values):
    if not values:
        return None
    peak = values[0]
    dd = 0.0
    for x in values:
        peak = max(peak, x)
        if peak > 0:
            dd = min(dd, 100.0 * (x / peak - 1))
    return dd


def _obv_delta(bars, n):
    if len(bars) < n + 1:
        return None
    base = bars[-(n + 1):]
    direction_vol = sum((1 if base[i]["close"] > base[i-1]["close"]
                         else -1 if base[i]["close"] < base[i-1]["close"] else 0)
                        * base[i]["volume"] for i in range(1, len(base)))
    total = sum(b["volume"] for b in base[1:])
    return direction_vol / total if total > 0 else None


def _volume_price_trend(bars, n):
    if len(bars) < n + 1:
        return None
    base = bars[-(n + 1):]
    vol = sum(b["volume"] for b in base[1:])
    if not vol:
        return None
    score = sum(b["volume"] * ((b["close"] / p["close"]) - 1)
                for p, b in zip(base[:-1], base[1:]) if p["close"] > 0)
    return score / vol


def _signed_returns(closes, n):
    if len(closes) < n + 1:
        return None
    subset = closes[-(n + 1):]
    return [math.log(subset[i] / subset[i - 1]) for i in range(1, len(subset))]


def _safe_z(x, values):
    sd = statistics.pstdev(values) if len(values) >= 2 else 0.0
    return (x - _avg(values)) / sd if sd > 0 else 0.0


def feature_registry(prefix: str, periods=DAILY_PERIODS, *,
                     signal_periods=None):
    """Exact MA durations and fixed parameters per indicator and time scale."""
    wanted = MINUTE_PERIODS if scope(prefix) == "minute" else (
        () if scope(prefix) in ("week", "month") else DAILY_PERIODS)
    if tuple(periods) != wanted:
        raise ValueError("UNAPPROVED_MOVING_AVERAGE_PERIODS_OR_TIMEFRAME")
    if signal_periods is not None:
        raise ValueError("NON_MA_PERIOD_GRID_NOT_SUPPORTED")
    names = set()
    for n in periods:
        for name in ("sma_close_distance_pct", "sma_slope_pct",
                     "ema_close_distance_pct", "ema_slope_pct"):
            names.add(f"{prefix}_{name}_{n}")
    for indicator, horizons in indicator_parameters(prefix).items():
        names.update(f"{prefix}_{indicator}_{n}" for n in horizons)
    for a, b in CROSSOVER_PAIRS:
        if a in periods and b in periods:
            names.add(f"{prefix}_sma_cross_{a}_{b}_pct")
            names.add(f"{prefix}_ema_cross_{a}_{b}_pct")
    special = LATEST_NAMES + (() if scope(prefix) in ("week", "month") else OSCILLATOR_NAMES)
    names.update(f"{prefix}_{name}" for name in special)
    if prefix in ("preopen_daily", "daily_full"):
        names.update({
            f"{prefix}_prior_day_volume_spike_vs_20d",
            f"{prefix}_prior_day_turnover_spike_vs_20d",
            f"{prefix}_prior_day_price_impact_20d_per_100m_jpy",
        })
    return tuple(sorted(names))


def build_ohlcv_features(bars: list[dict[str, Any]], *,
                         prefix: str, reference_price: float | None,
                         periods=DAILY_PERIODS,
                         signal_periods=None) -> dict[str, float | None]:
    """All bars must already be validated, causally available, ordered, comparable.

    Cross-source reference_price should be None if adjustment parity is not proven.
    No assumed bar continuity or missing-bar filling occurs here.
    """
    result: dict[str, float | None] = {
        k: None for k in feature_registry(prefix, periods,
                                         signal_periods=signal_periods)
    }
    if not bars:
        return result
    O = [float(b["open"]) for b in bars]
    H = [float(b["high"]) for b in bars]
    L = [float(b["low"]) for b in bars]
    C = [float(b["close"]) for b in bars]
    V = [float(b["volume"]) for b in bars]
    # Do not treat missing trading value as zero: volume/price indicators can
    # still be calculated, but turnover-based indicators become None.
    T = [float(b["turnover"]) if b.get("turnover") is not None else None
         for b in bars]
    base = C[-1]
    if any(not math.isfinite(x) or x <= 0 for xs in (O, H, L, C) for x in xs):
        raise ValueError("INVALID_OHLC")
    if any(v < 0 or not math.isfinite(v) for xs in (V, T) for v in xs if v is not None):
        raise ValueError("INVALID_VOLUME_VALUE")
    p = prefix
    result[f"{p}_latest_body_pct"] = _pct(C[-1], O[-1])
    result[f"{p}_latest_upper_wick_pct"] = 100 * (H[-1] - max(O[-1], C[-1])) / C[-1]
    result[f"{p}_latest_lower_wick_pct"] = 100 * (min(O[-1], C[-1]) - L[-1]) / C[-1]
    result[f"{p}_latest_clv"] = ((2*C[-1] - H[-1] - L[-1]) / (H[-1] - L[-1])
                                 if H[-1] > L[-1] else 0.0)
    result[f"{p}_latest_gap_pct"] = _pct(O[-1], C[-2]) if len(C) >= 2 else None
    result[f"{p}_latest_volume"] = V[-1]
    result[f"{p}_latest_turnover"] = T[-1]
    result[f"{p}_total_volume"] = sum(V)
    result[f"{p}_total_turnover"] = sum(T) if all(t is not None for t in T) else None
    smas, emas = {}, {}
    for n in periods:
        m = _avg(C[-n:]) if len(C) >= n else None
        e = _ema(C, n)
        smas[n], emas[n] = m, e
        result[f"{p}_sma_close_distance_pct_{n}"] = _pct(
            reference_price if reference_price is not None else base, m)
        result[f"{p}_ema_close_distance_pct_{n}"] = _pct(
            reference_price if reference_price is not None else base, e)
        result[f"{p}_sma_slope_pct_{n}"] = (
            _pct(m, _avg(C[-(n + 1):-1])) if m is not None and len(C) >= n + 1
            else None)
        old_ema = _ema(C[:-1], n) if len(C) > n else None
        result[f"{p}_ema_slope_pct_{n}"] = _pct(e, old_ema)

    parameters = indicator_parameters(prefix)
    for n in sorted({n for values in parameters.values() for n in values}):
        if len(C) < n:
            continue
        segment = bars[-n:]
        window_high, window_low = max(H[-n:]), min(L[-n:])
        vol_avg = _avg(V[-n:])
        turn_avg = _avg(T[-n:]) if all(t is not None for t in T[-n:]) else None
        logrets = _signed_returns(C, n)
        calculations = {
            "return_pct": lambda: _pct(base, C[-n-1]) if len(C) > n else None,
            "high_break_pct": lambda: _pct(base, window_high),
            "low_buffer_pct": lambda: _pct(base, window_low),
            "range_position": lambda: ((base-window_low)/(window_high-window_low)
                                        if window_high > window_low else 0.5),
            "volume_ratio": lambda: V[-1]/vol_avg if vol_avg > 0 else None,
            "turnover_ratio": lambda: T[-1]/turn_avg if T[-1] is not None and
                turn_avg is not None and turn_avg > 0 else None,
            "volume_zscore": lambda: _safe_z(V[-1], V[-n:]),
            "turnover_zscore": lambda: _safe_z(T[-1], T[-n:]) if turn_avg is not None else None,
            "max_drawdown_pct": lambda: _max_drawdown(C[-n:]),
            "up_candle_ratio": lambda: sum(b["close"] > b["open"] for b in segment)/n,
            "close_location_avg": lambda: _avg([(b["close"]-b["low"])/(b["high"]-b["low"])
                if b["high"] > b["low"] else 0.5 for b in segment]),
            "range_avg_pct": lambda: 100*_avg([(b["high"]-b["low"])/b["close"] for b in segment]),
            "bollinger_z": lambda: _safe_z(base, C[-n:]),
            "bollinger_width_pct": lambda: 400*statistics.pstdev(C[-n:])/_avg(C[-n:]),
            "donchian_high_gap_pct": lambda: _pct(base, max(H[-n-1:-1])) if len(C) > n else None,
            "donchian_low_gap_pct": lambda: _pct(base, min(L[-n-1:-1])) if len(C) > n else None,
            "stochastic_k": lambda: _stochastic(bars, n),
            "cci": lambda: _cci(bars, n), "cmf": lambda: _cmf(bars, n),
            "rsi": lambda: _rsi(C, n),
            "atr_pct": lambda: (100*atr/base if (atr := _atr(bars, n)) is not None else None),
            "mfi": lambda: _moneyflow(bars, n), "obv_delta": lambda: _obv_delta(bars, n),
            "volume_price_trend": lambda: _volume_price_trend(bars, n),
            "up_close_ratio": lambda: sum(C[i] > C[i-1] for i in range(len(C)-n+1,len(C)))/(n-1)
                if n >= 2 else None,
            "efficiency": lambda: _efficiency(C[-n-1:]) if len(C) > n else None,
            "realized_vol_pct": lambda: 100*statistics.pstdev(logrets) if logrets else None,
            "downside_vol_pct": lambda: 100*math.sqrt(sum(min(x,0)**2 for x in logrets)/len(logrets))
                if logrets else None,
        }
        for indicator, horizons in parameters.items():
            if n in horizons:
                result[f"{p}_{indicator}_{n}"] = calculations[indicator]()
    for a,b in CROSSOVER_PAIRS:
        if a not in periods or b not in periods:
            continue
        result[f"{p}_sma_cross_{a}_{b}_pct"] = (
            _pct(smas[a],smas[b]) if a in smas and b in smas else None
        )
        result[f"{p}_ema_cross_{a}_{b}_pct"] = (
            _pct(emas[a],emas[b]) if a in emas and b in emas else None
        )
    if scope(prefix) not in ("week", "month"):
        fast,slow = _ema(C,12),_ema(C,26)
        macd_trace=[]
        if len(C)>=26:
            # Use 26-consecutive prefix to seed EMA tracks, then compute 9-period MACD signal.
            fast_trace, slow_trace = _ema_trace(C,12), _ema_trace(C,26)
            macd_trace = [f-s for f,s in zip(fast_trace[14:],slow_trace)]
        macd = fast-slow if fast is not None and slow is not None else None
        signal = _ema(macd_trace,9)
        result[f"{p}_macd_12_26_pct"] = 100 * macd/base if macd is not None else None
        result[f"{p}_macd_signal9_pct"] = 100 * signal/base if signal is not None else None
        result[f"{p}_macd_hist9_pct"] = 100 * (macd-signal)/base if signal is not None else None
        adx,pdi,mdi = _adx(bars,14)
        result[f"{p}_adx14"] = adx
        result[f"{p}_plus_di14"] = pdi
        result[f"{p}_minus_di14"] = mdi
        if len(bars) >= 9:
            tenkan = (max(H[-9:])+min(L[-9:]))/2
            result[f"{p}_ichimoku_tenkan9_pct"] = _pct(base,tenkan)
        else:
            tenkan=None
        if len(bars) >= 26:
            kijun = (max(H[-26:])+min(L[-26:]))/2
            result[f"{p}_ichimoku_kijun26_pct"] = _pct(base,kijun)
        else:
            kijun=None
        if tenkan is not None and kijun is not None:
            result[f"{p}_ichimoku_cloud_a_pct"] = _pct(base,(tenkan+kijun)/2)
            result[f"{p}_ichimoku_tenkan_vs_kijun_pct"] = _pct(tenkan,kijun)
        if len(bars) >= 52:
            span_b = (max(H[-52:])+min(L[-52:]))/2
            result[f"{p}_ichimoku_cloud_b52_pct"] = _pct(base,span_b)
        # Ichimoku spans are calculated at as-of, not forward/back-shifted to leak data.
    # Day-before volume/value anomaly uses older 20 sessions only as baseline.
    if prefix in ("preopen_daily", "daily_full") and len(bars) >= 21:
        prior_vol = [float(b["volume"]) for b in bars[-21:-1]]
        prior_turn = T[-21:-1]
        ref_vol = statistics.median(prior_vol)
        ref_turn = statistics.median(prior_turn) if all(v is not None for v in prior_turn) else None
        result[f"{p}_prior_day_volume_spike_vs_20d"] = (
            V[-1] / ref_vol if ref_vol > 0 else None)
        result[f"{p}_prior_day_turnover_spike_vs_20d"] = (
            T[-1] / ref_turn if T[-1] is not None and ref_turn is not None and ref_turn > 0 else None)
        impact = []
        for i in range(len(C) - 20, len(C)):
            if i >= 1 and T[i] is not None and T[i] > 0 and C[i-1] > 0:
                impact.append(abs(C[i] / C[i-1] - 1) * 100.0e8 / T[i])
        if len(impact) == 20:
            result[f"{p}_prior_day_price_impact_20d_per_100m_jpy"] = _avg(impact)
    for k,v in result.items():
        if v is not None and not math.isfinite(v):
            raise ValueError(f"NONFINITE_INDICATOR:{k}")
    return result
