"""Label-free G0/G1/G2, exact comparisons and complete reason diagnostics."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from fractions import Fraction as F
from typing import Any
from .calendar_phase import ExchangeCalendar
from .contracts import Candle, Identity
from .exact_math import V2Error, median, percent, sma, wilder

REASON_ORDER = ("DATA_ERROR", "UNKNOWN", "PRICE_MIN", "PRICE_LOT",
                "DAMAGE_CC", "DAMAGE_BODY", "DAMAGE_GAP", "DAMAGE_ATR", "CAPACITY")


@dataclass(frozen=True)
class GateResult:
    state: str
    reasons: tuple[str, ...]
    values: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.state == "PASS"

    @property
    def first_reason(self) -> str | None:
        return self.reasons[0] if self.reasons else None


def g0(history: list[Candle], identity: Identity, session: date,
       calendar: ExchangeCalendar, *, master_present: bool = True) -> GateResult:
    if not master_present:
        raise V2Error("DATA_BLOCKED_MASTER_MISSING")
    if not identity.eligible(session):
        return GateResult("REJECT", ("OUTSIDE_SECURITY_UNIVERSE",))
    expected = calendar.history(session, 77)
    t = calendar.previous(session)
    if any(r.session >= session for r in history):
        raise V2Error("CURRENT_OR_FUTURE_DAILY_INPUT")
    dates = [r.session for r in history]
    if dates != sorted(set(dates)):
        raise V2Error("DUPLICATE_OR_UNORDERED_DAILY_IDENTITY")
    for r in history:
        r.validate()
        if r.basis != "RAW" or r.units != ("JPY", "SHARES", "JPY"):
            raise V2Error("RAW_BASIS_OR_UNITS_NOT_VERIFIED")
    if not history or history[-1].session != t:
        return GateResult("UNKNOWN", ("UNKNOWN_PREVIOUS_SESSION",))
    close = history[-1].close
    if close is not None and close <= 75:
        return GateResult("REJECT", ("PRICE_MIN",))
    if len(history) < 77 or tuple(dates[-77:]) != expected:
        return GateResult("UNKNOWN", ("UNKNOWN_REQUIRED_HISTORY",))
    tail = history[-77:]
    suffix = tail[-1].comparable_suffix
    if any(r.comparable_suffix != suffix for r in tail):
        return GateResult("UNKNOWN", ("UNKNOWN_COMPARABLE_RAW_SUFFIX",))
    if any(r.close is None or r.high is None or r.low is None or r.open is None for r in tail):
        return GateResult("UNKNOWN", ("UNKNOWN_REQUIRED_HISTORY",))
    if any(r.volume is None or r.turnover is None for r in tail[-20:]):
        return GateResult("UNKNOWN", ("UNKNOWN_REQUIRED_ACTIVITY",))
    return GateResult("PASS", (), {"required_closes": 77})


def g1(history: list[Candle]) -> GateResult:
    detail: dict[str, Any] = {}
    ups: dict[int, bool | None] = {}
    for n in (5, 15, 25, 75):
        tail = history[-n-1:]
        if len(tail) < n + 1 or any(r.close is None for r in tail):
            ups[n] = None
            detail[str(n)] = {"sma": None, "delta": None, "price_difference": None, "up": None}
            continue
        cs = [r.close for r in tail]
        assert all(c is not None for c in cs)
        closes: list[F] = [c for c in cs if c is not None]
        s = sma(closes, n)
        delta = s - sma(closes, n, 1)
        shortcut = (closes[-1] - closes[-1 - n]) / n
        up = delta > 0 and closes[-1] > s
        cross = closes[-1] > closes[-1-n] and n * closes[-1] > sum(closes[-n:])
        if delta != shortcut or up != cross:
            raise V2Error("EXACT_MA_INDEPENDENT_IDENTITY_FAILED")
        ups[n] = up
        detail[str(n)] = {"sma": s, "delta": delta, "price_difference": closes[-1] - s,
                          "up": up, "slope_sign": (delta > 0) - (delta < 0)}
    axes = {"long": ups[75], "medium": None if ups[25] is None or ups[15] is None
            else ups[25] and ups[15], "short": ups[5]}
    detail["axes"] = axes
    detail["known_non_up_periods"] = [n for n, v in ups.items() if v is False]
    if any(v is None for v in ups.values()):
        return GateResult("UNKNOWN", ("UNKNOWN_REQUIRED_HISTORY",), detail)
    count = sum(v is True for v in axes.values())
    return GateResult("PASS" if count == 3 else "REJECT" if count == 0 else "WAIT",
                      () if count == 3 else ("REJECT_NO_UP_AXIS" if count == 0 else "WAIT_MIXED_TREND",), detail)


def atr_pre(history: list[Candle]) -> F | None:
    if len(history) < 77:
        return None
    rows = history[-77:]
    if len({r.comparable_suffix for r in rows}) != 1:
        return None
    tr = []
    for i in range(1, 76):
        r, prev = rows[i], rows[i-1]
        r.validate()
        if r.high is None or r.low is None or prev.close is None:
            return None
        tr.append(max(r.high-r.low, abs(r.high-prev.close), abs(r.low-prev.close)))
    return wilder(tr, 14)


def g2(history: list[Candle]) -> GateResult:
    reference_cash=F(1000000)
    reasons: list[str] = []
    diagnostics: dict[str, Any] = {}
    if len(history) < 77:
        reasons.append("UNKNOWN")
    for r in history:
        r.validate()
        if r.basis != "RAW" or r.units != ("JPY", "SHARES", "JPY"):
            raise V2Error("RAW_BASIS_OR_UNITS_NOT_VERIFIED")
    if len(history) < 2:
        return GateResult("UNKNOWN", ("UNKNOWN",), {"missing_reason": "UNKNOWN_REQUIRED_HISTORY"})
    now, prev = history[-1], history[-2]
    if now.close is not None:
        if now.close <= 75:
            reasons.append("PRICE_MIN")
        if 100 * now.close > reference_cash:
            reasons.append("PRICE_LOT")
    for name, a, b in (("cc", now.close, prev.close), ("body", now.close, now.open),
                        ("gap", now.open, prev.close)):
        value = None if a is None or b is None else percent(a, b)
        diagnostics["r_" + name + "_pct"] = value
        if value is None:
            reasons.append("UNKNOWN")
        elif value <= -5:
            reasons.append("DAMAGE_" + name.upper())
    atr = atr_pre(history)
    if atr is not None and atr < 0:
        raise V2Error("DATA_INTEGRITY_ERROR_NEGATIVE_ATR")
    loss = None if now.close is None or prev.close is None else max(F(0), prev.close-now.close)
    diagnostics["atr_pre"] = atr
    diagnostics["z_loss"] = None
    if atr is None or loss is None:
        reasons.append("UNKNOWN")
    elif atr == 0:
        if loss > 0:
            reasons.append("DAMAGE_ATR")
            diagnostics["atr_zero_reason"] = "ATR_ZERO_WITH_POSITIVE_DROP"
        else:
            diagnostics["z_loss"] = F(0)
    else:
        diagnostics["z_loss"] = loss / atr
        if loss >= 3 * atr:
            reasons.append("DAMAGE_ATR")
    vas = [r.turnover for r in history[-20:]]
    if len(vas) < 20 or any(x is None for x in vas):
        reasons.append("UNKNOWN")
        diagnostics["b20"] = None
    else:
        known = [x for x in vas if x is not None]
        b20 = min(known[-1], median(known))
        diagnostics["b20"] = b20
        diagnostics["reference_capacity_share"] = reference_cash / b20 if b20 > 0 else None
        if b20 <= 0 or 100 * reference_cash > b20:
            reasons.append("CAPACITY")
    ordered = tuple(r for r in REASON_ORDER if r in reasons)
    state = "UNKNOWN" if "UNKNOWN" in ordered else "REJECT" if ordered else "PASS"
    return GateResult(state, ordered, diagnostics)
