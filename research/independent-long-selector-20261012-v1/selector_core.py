"""Independent cash-only Selector research core (no broker/provider/fit side effects).

Inputs are already-authorized, locally mounted as-of snapshots.  In particular,
features and evaluator outcomes MUST arrive through separate entry points.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

DECISION_TIMES = (
    "09:30", "10:00", "10:30", "11:00", "11:30",
    "13:00", "13:30", "14:00", "14:30", "15:00",
)
TOP_K = 5
FRESHNESS_SECONDS = 300
STATES = (
    "RISE_STOP", "RISE", "SHARP_RISE", "PULLBACK", "RANGE",
    "REBOUND", "SHARP_DROP", "DROP", "DROP_STOP",
)
EXTRA_FEATURES = (
    "market_breadth_pct", "sector_breadth_pct", "market_return_pct",
    "sector_return_pct", "sector_relative_strength_pct",
    "relative_volume", "relative_turnover", "spread_bps",
    "market_regime_score", "auction_imbalance",
    "dictionary_volatility", "dictionary_gap_continuation",
    "dictionary_breakout", "dictionary_giveback",
    "dictionary_confidence", "dictionary_drift",
    "state_path_trend_efficiency", "state_path_up_probability",
    "fundamental_earnings_revision", "news_sentiment",
    "orderflow_imbalance",
)
SAFETY = {
    key: False for key in (
        "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
        "rssOrderFunctionAllowed", "liveTradingAllowed",
        "paperTradingAllowed", "automaticPromotionAllowed",
        "productionUpdateAllowed", "transmitted",
    )
}


class ContractError(ValueError):
    """Unsafe, ambiguous, or incomparable input."""


def _time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ContractError("TIMESTAMP_REQUIRED")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ContractError("INVALID_TIMESTAMP") from exc
    if result.utcoffset() != timedelta(hours=9):
        raise ContractError("JST_TIMESTAMP_REQUIRED")
    return result


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{label}:NONNUMERIC")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        raise ContractError(f"{label}:NONFINITE_OR_NONPOSITIVE")
    return result


def _pct(new: float, old: float) -> float:
    return 100.0 * (new / old - 1.0)


def _signed_eval_pct(new: float, old: float) -> float:
    """Decimal arithmetic prevents a true -1.00% from flooring into -2%."""
    return float((Decimal(str(new)) / Decimal(str(old)) - Decimal(1)) * Decimal(100))


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _sma(values: list[float], n: int) -> float | None:
    return _mean(values[-n:]) if len(values) >= n else None


def _ema(values: list[float], n: int) -> float | None:
    if len(values) < n:
        return None
    alpha = 2.0 / (n + 1)
    v = _mean(values[:n])
    for x in values[n:]:
        v = alpha * x + (1.0 - alpha) * v
    return v


def _rsi(values: list[float], n: int = 14) -> float | None:
    if len(values) < n + 1:
        return None
    changes = [values[i] - values[i - 1] for i in range(len(values) - n, len(values))]
    gain = _mean([max(v, 0.0) for v in changes])
    loss = _mean([max(-v, 0.0) for v in changes])
    if loss == 0:
        return 100.0 if gain > 0 else 50.0
    return 100.0 - 100.0 / (1.0 + gain / loss)


def _efficiency(prices: list[float]) -> float | None:
    if len(prices) < 2:
        return None
    travel = sum(abs(prices[i] - prices[i - 1]) for i in range(1, len(prices)))
    return abs(prices[-1] - prices[0]) / travel if travel > 0 else 0.0


def _contiguous_tail(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not bars:
        return []
    tail = [bars[-1]]
    for i in range(len(bars) - 2, -1, -1):
        older = bars[i]
        newer = tail[0]
        if _time(newer["start"]) - _time(older["start"]) != timedelta(minutes=1):
            break
        tail.insert(0, older)
    return tail


def build_features(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Build strictly causal features. Missing data stays None, never 0-filled.

    Required: session, decisionTime, symbol, universeEligible, eligibilityKnownAt,
    corporateActionSafe, minuteBars. Daily/context features are optional but each
    provided observation MUST have an availableAt. Price basis parity is explicit.
    """
    if any(key.startswith(("future", "label", "outcome")) for key in snapshot):
        raise ContractError("FUTURE_INFORMATION_IN_SELECTOR_INPUT")
    session = snapshot["session"]
    dt = _time(snapshot["decisionTime"])
    if dt.date().isoformat() != session or dt.strftime("%H:%M") not in DECISION_TIMES:
        raise ContractError("INVALID_DECISION_TIME")
    if snapshot.get("assetType") != "JPX_CASH_EQUITY":
        raise ContractError("NOT_JPX_CASH_EQUITY")
    if not snapshot.get("universeEligible") or not snapshot.get("corporateActionSafe"):
        raise ContractError("INELIGIBLE_OR_ACTION_UNVERIFIED")
    if _time(snapshot["eligibilityKnownAt"]) > dt:
        raise ContractError("FUTURE_MEMBERSHIP")
    symbol = snapshot["symbol"]
    if not isinstance(symbol, str) or not symbol:
        raise ContractError("SYMBOL_REQUIRED")

    minute = sorted(snapshot["minuteBars"], key=lambda x: x["start"])
    prev_start: datetime | None = None
    for b in minute:
        start, end, available = (_time(b[k]) for k in ("start", "end", "availableAt"))
        if start.date().isoformat() != session or end - start != timedelta(minutes=1):
            raise ContractError("MINUTE_SESSION_OR_DURATION")
        if not start < end <= available <= dt:
            raise ContractError("MINUTE_NOT_CAUSALLY_AVAILABLE")
        if prev_start is not None and start <= prev_start:
            raise ContractError("DUPLICATE_MINUTE")
        prev_start = start
        o, h, l, c = [_number(b[k], k, positive=True) for k in ("open", "high", "low", "close")]
        if not l <= min(o, c) <= max(o, c) <= h:
            raise ContractError("BAD_MINUTE_OHLC")
        _number(b["volume"], "minuteVolume")
        _number(b["turnover"], "minuteTurnover")
        if b["volume"] < 0 or b["turnover"] < 0:
            raise ContractError("NEGATIVE_VOLUME")
    if not minute:
        raise ContractError("NO_CAUSAL_PRICE")
    latest = minute[-1]
    decision_price = float(latest["close"])
    age = (dt - _time(latest["availableAt"])).total_seconds()
    if age < 0 or age > FRESHNESS_SECONDS:
        raise ContractError("STALE_PRICE")

    daily = sorted(snapshot.get("dailyBars", []), key=lambda b: b["session"])
    seen_dates: set[str] = set()
    for b in daily:
        if b["session"] >= session or b["session"] in seen_dates:
            raise ContractError("FUTURE_OR_DUPLICATE_DAILY")
        seen_dates.add(b["session"])
        if _time(b["availableAt"]) > dt:
            raise ContractError("DAILY_NOT_AVAILABLE")
        o, h, l, c = [_number(b[k], k, positive=True) for k in ("open", "high", "low", "close")]
        if not l <= min(o, c) <= max(o, c) <= h:
            raise ContractError("BAD_DAILY_OHLC")
        if _number(b["volume"], "dailyVolume") < 0:
            raise ContractError("NEGATIVE_DAILY_VOLUME")

    features: dict[str, float | None] = {}
    closes = [float(b["close"]) for b in daily] if snapshot.get("dailyContinuityVerified") else []
    parity = bool(snapshot.get("dailyToMinutePriceParityVerified"))
    for n in (2, 3, 5, 7, 10, 12, 15, 20, 25, 30, 50, 60, 75, 90, 100, 120, 150, 200, 250):
        avg = _sma(closes, n)
        features[f"daily_sma{n}_distance_pct"] = _pct(decision_price, avg) if avg and parity else None
        features[f"daily_sma{n}_slope_pct"] = (
            _pct(_mean(closes[-n:]), _mean(closes[-(n + 1):-1]))
            if len(closes) >= n + 1 else None
        )
    for n in (1, 2, 3, 5, 7, 10, 12, 15, 20, 25, 30, 50, 60, 75, 100, 120, 200):
        features[f"daily_return_{n}_pct"] = (
            _pct(closes[-1], closes[-n - 1]) if len(closes) >= n + 1 else None
        )
    features["daily_ema12_vs_ema26_pct"] = (
        _pct(_ema(closes, 12), _ema(closes, 26)) if _ema(closes, 26) else None
    )
    features["daily_rsi14"] = _rsi(closes)
    if len(closes) >= 20:
        m = _mean(closes[-20:])
        st = statistics.pstdev(closes[-20:])
        features["daily_bollinger_z20"] = (closes[-1] - m) / st if st > 0 else 0.0
        features["daily_bollinger_width20_pct"] = 400.0 * st / m
        features["daily_range20_position"] = (
            (closes[-1] - min(closes[-20:])) / (max(closes[-20:]) - min(closes[-20:]))
            if max(closes[-20:]) > min(closes[-20:]) else 0.5
        )
    else:
        for k in ("daily_bollinger_z20", "daily_bollinger_width20_pct", "daily_range20_position"):
            features[k] = None
    if len(daily) >= 15 and snapshot.get("dailyContinuityVerified"):
        ranges = []
        for i in range(-14, 0):
            b = daily[i]
            pc = daily[i - 1]["close"]
            ranges.append(max(b["high"] - b["low"], abs(b["high"] - pc), abs(b["low"] - pc)))
        features["daily_atr14_pct"] = 100 * _mean(ranges) / daily[-1]["close"]
    else:
        features["daily_atr14_pct"] = None

    continuous = _contiguous_tail(minute)
    tape = [float(b["close"]) for b in continuous]
    for n in (1, 3, 5, 10, 15, 20, 25, 30, 45, 60, 90, 120):
        features[f"intraday_momentum_{n}m_pct"] = (
            _pct(tape[-1], tape[-n - 1]) if len(tape) >= n + 1 else None
        )
    for n in (3, 5, 10, 15, 20, 25, 30, 45, 60, 90, 120):
        v = _sma(tape, n)
        features[f"intraday_sma{n}_distance_pct"] = _pct(tape[-1], v) if v else None
        features[f"intraday_efficiency_{n}"] = _efficiency(tape[-n:]) if len(tape) >= n else None
    recent = continuous[-10:]
    features["intraday_upbar_ratio10"] = (
        sum(b["close"] > b["open"] for b in recent) / 10 if len(recent) == 10 else None
    )
    features["intraday_volume_accel5"] = (
        sum(float(b["volume"]) for b in continuous[-5:])
        / sum(float(b["volume"]) for b in continuous[-10:-5])
        if len(continuous) >= 10 and sum(float(b["volume"]) for b in continuous[-10:-5]) > 0
        else None
    )
    latest_o, latest_h, latest_l, latest_c = (
        float(latest[k]) for k in ("open", "high", "low", "close")
    )
    features["latest_candle_body_pct"] = _pct(latest_c, latest_o)
    features["latest_close_location"] = (
        (latest_c - latest_l) / (latest_h - latest_l) if latest_h > latest_l else 0.5
    )
    features["latest_upper_wick_pct"] = 100 * (latest_h - max(latest_o, latest_c)) / latest_c
    features["latest_lower_wick_pct"] = 100 * (min(latest_o, latest_c) - latest_l) / latest_c

    if snapshot.get("intradayCoverageCertified"):
        turnover = sum(float(b["turnover"]) for b in minute)
        volume = sum(float(b["volume"]) for b in minute)
        features["intraday_vwap_distance_pct"] = (
            _pct(decision_price, turnover / volume) if volume > 0 and turnover > 0 else None
        )
        features["intraday_high_distance_pct"] = _pct(decision_price, max(b["high"] for b in minute))
        features["intraday_low_distance_pct"] = _pct(decision_price, min(b["low"] for b in minute))
        features["intraday_trading_value_log"] = math.log1p(turnover)
        features["intraday_volume_log"] = math.log1p(volume)
    else:
        for k in ("intraday_vwap_distance_pct", "intraday_high_distance_pct",
                  "intraday_low_distance_pct", "intraday_trading_value_log",
                  "intraday_volume_log"):
            features[k] = None

    features["opening_gap_pct"] = (
        _pct(float(minute[0]["open"]), closes[-1])
        if closes and parity and snapshot.get("intradayCoverageCertified") else None
    )
    features["prior_high_break_pct"] = (
        _pct(decision_price, daily[-1]["high"]) if daily and parity else None
    )
    features["prior_low_buffer_pct"] = (
        _pct(decision_price, daily[-1]["low"]) if daily and parity else None
    )

    state = snapshot.get("state9")
    if state is not None:
        if _time(state["availableAt"]) > dt or not state.get("pitVerified"):
            raise ContractError("STATE_ASOF_UNVERIFIED")
        if state.get("primary") not in STATES:
            raise ContractError("UNKNOWN_STATE")
    for name in STATES:
        features[f"state9_{name.lower()}"] = (
            float(state["primary"] == name) if state else None
        )

    supplied = snapshot.get("extraAsOf", {})
    for key in supplied:
        if key not in EXTRA_FEATURES:
            raise ContractError("UNREGISTERED_EXTRA_FEATURE")
    for key in EXTRA_FEATURES:
        v = supplied.get(key)
        if v is None:
            features[key] = None
            continue
        if _time(v["availableAt"]) > dt or not v.get("pitVerified"):
            raise ContractError("EXTRA_FEATURE_ASOF_UNVERIFIED")
        features[key] = _number(v["value"], key)

    return {
        "session": session, "decisionTime": snapshot["decisionTime"],
        "symbol": symbol, "securityId": snapshot.get("securityId"),
        "assetType": "JPX_CASH_EQUITY",
        "decisionPrice": decision_price,
        "priceAvailableAt": latest["availableAt"],
        "priceAgeSeconds": age,
        "eligibleUniverseHash": snapshot["eligibleUniverseHash"],
        "priceBasis": snapshot["priceBasis"],
        "features": features,
        "featureN": sum(x is not None for x in features.values()),
        "missingN": sum(x is None for x in features.values()),
    }


def select_top5(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score must be supplied by an independent fitted candidate, never labels."""
    if not rows:
        return []
    group = {
        (r["session"], r["decisionTime"], r["eligibleUniverseHash"], r["priceBasis"])
        for r in rows
    }
    if len(group) != 1:
        raise ContractError("MIXED_DECISION_OR_UNIVERSE")
    symbols: set[str] = set()
    for row in rows:
        if row["symbol"] in symbols:
            raise ContractError("DUPLICATE_SYMBOL")
        symbols.add(row["symbol"])
        if row.get("assetType") != "JPX_CASH_EQUITY":
            raise ContractError("NONCASH_SYMBOL")
        _number(row["decisionPrice"], "decisionPrice", positive=True)
        _number(row["score"], "score")
        if any(k.startswith(("future", "label", "outcome")) for k in row):
            raise ContractError("OUTCOME_IN_SCORING_RECORD")
    return sorted(rows, key=lambda r: (-r["score"], r["symbol"]))[:TOP_K]


def signed_bucket(value: float | None) -> str:
    if value is None:
        return "UNKNOWN"
    value = _number(value, "signedHighPct")
    if value >= 5:
        return ">=5"
    left = math.floor(value)
    return f"{left}..<{left + 1}"


def _event_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return row["session"], row["decisionTime"], row["symbol"]


def evaluate_events(selected: list[dict[str, Any]],
                    future_by_key: dict[tuple[str, str, str], list[dict[str, Any]]]
                    ) -> list[dict[str, Any]]:
    """Evaluation-only: signed future High, never clipped; separate downside Low."""
    outcomes: list[dict[str, Any]] = []
    for row in selected:
        key = _event_key(row)
        dp = _number(row["decisionPrice"], "decisionPrice", positive=True)
        cutoff = _time(row["decisionTime"])
        future = future_by_key.get(key)
        result = {k: row[k] for k in ("session", "decisionTime", "symbol",
                                     "eligibleUniverseHash", "priceBasis")}
        result["signedHighPct"] = None
        result["maePct"] = None
        result["bucket"] = "UNKNOWN"
        result["closeAtLeast3"] = None
        result["closeAtLeast5"] = None
        if future:
            highs, lows, closes = [], [], []
            last_start: datetime | None = None
            for b in future:
                if b.get("kind") != "CONTINUOUS_5M":
                    continue
                start = _time(b["start"])
                end = _time(b["end"])
                available = _time(b["availableAt"])
                if (start.date().isoformat() != row["session"]
                    or start < cutoff or end - start != timedelta(minutes=5)
                    or available < end):
                    raise ContractError("INVALID_FUTURE_BAR")
                if last_start is not None and start <= last_start:
                    raise ContractError("DUPLICATE_FUTURE_BAR")
                last_start = start
                h = _number(b["high"], "futureHigh", positive=True)
                l = _number(b["low"], "futureLow", positive=True)
                c = _number(b["close"], "futureClose", positive=True)
                if l > c or c > h:
                    raise ContractError("BAD_FUTURE_OHLC")
                highs.append(h)
                lows.append(l)
                closes.append(c)
            if highs:
                result["signedHighPct"] = _signed_eval_pct(max(highs), dp)
                result["maePct"] = min(0.0, _signed_eval_pct(min(lows), dp))
                result["bucket"] = signed_bucket(result["signedHighPct"])
                result["closeAtLeast3"] = any(v >= dp * 1.03 for v in closes)
                result["closeAtLeast5"] = any(v >= dp * 1.05 for v in closes)
        outcomes.append(result)
    return outcomes


def summarize(evaluated: list[dict[str, Any]]) -> dict[str, Any]:
    distribution = Counter(row["bucket"] for row in evaluated)
    known = [r for r in evaluated if r["signedHighPct"] is not None]
    n = len(evaluated)
    return {
        "selectedN": n,
        "knownN": len(known),
        "unknownN": n - len(known),
        "exclusiveBucketCounts": dict(sorted(distribution.items(),
                                               key=lambda x: float("-inf") if x[0] == "UNKNOWN"
                                               else float("inf") if x[0] == ">=5"
                                               else int(x[0].split("..")[0]))),
        "exclusiveBucketPctOfKnown": {
            k: (100 * v / len(known) if len(known) else None)
            for k, v in distribution.items() if k != "UNKNOWN"
        },
        "cumulativeHighCounts": {
            str(t): sum(r["signedHighPct"] >= t for r in known)
            for t in (1, 2, 3, 4, 5)
        },
        "downsideCounts": {
            str(t): sum(r["maePct"] <= -t for r in known)
            for t in (1, 2, 3, 5)
        },
        "meanSignedHighPct": _mean([r["signedHighPct"] for r in known]) if known else None,
        "medianSignedHighPct": statistics.median(
            [r["signedHighPct"] for r in known]) if known else None,
    }


def compare_policies(baseline: list[dict[str, Any]],
                     candidate: list[dict[str, Any]],
                     future_by_key: dict[tuple[str, str, str], list[dict[str, Any]]]
                     ) -> dict[str, Any]:
    """Fail closed unless groups, counts and universe/price basis are identical."""
    def groups(rows: list[dict[str, Any]]) -> dict[tuple[str, str], tuple[str, str]]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            grouped[(r["session"], r["decisionTime"])].append(r)
        result = {}
        for key, entries in grouped.items():
            if len(entries) != TOP_K or len({r["symbol"] for r in entries}) != TOP_K:
                raise ContractError("TOP5_CARDINALITY_VIOLATION")
            identities = {(r["eligibleUniverseHash"], r["priceBasis"]) for r in entries}
            if len(identities) != 1:
                raise ContractError("MIXED_GROUP_LINEAGE")
            result[key] = identities.pop()
        return result
    if groups(baseline) != groups(candidate):
        raise ContractError("UNPAIRED_GROUPS_OR_UNIVERSE")
    a = evaluate_events(baseline, future_by_key)
    b = evaluate_events(candidate, future_by_key)
    return {
        "comparison": "DEVELOPMENT_DESCRIPTIVE_ONLY_UNLESS_AUTHORIZED_OOS",
        "baseline": summarize(a),
        "candidate": summarize(b),
        "pairedDecisionN": len(groups(baseline)),
        "maxOnePolicyEventN": len(a),
        "events": {"baseline": a, "candidate": b},
    }
