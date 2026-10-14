"""Exact RAW-price arithmetic; binary floats are not original price values."""
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Iterable


class V2Error(ValueError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def rational(value: object) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float):
        raise V2Error("NON_EXACT_OR_BOOLEAN_ORIGINAL_NUMBER")
    if isinstance(value, Fraction):
        return value
    if not isinstance(value, (str, int, Decimal)):
        raise V2Error("INVALID_ORIGINAL_NUMBER")
    try:
        dec = Decimal(value)
    except (InvalidOperation, ValueError):
        raise V2Error("INVALID_ORIGINAL_NUMBER") from None
    if not dec.is_finite():
        raise V2Error("NONFINITE_ORIGINAL_NUMBER")
    return Fraction(dec)


def median(values: Iterable[Fraction]) -> Fraction:
    xs = sorted(values)
    if not xs:
        raise V2Error("EMPTY_MEDIAN")
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def percent(a: Fraction, b: Fraction) -> Fraction:
    if b <= 0:
        raise V2Error("NONPOSITIVE_PRICE_DENOMINATOR")
    return 100 * (a / b - 1)


def sma(closes: list[Fraction], n: int, lag: int = 0) -> Fraction:
    end = len(closes) - lag
    if n < 1 or lag < 0 or end < n:
        raise V2Error("UNKNOWN_REQUIRED_HISTORY")
    return sum(closes[end - n:end], Fraction()) / n


def wilder(values: list[Fraction], period: int = 14) -> Fraction:
    if len(values) < period or any(x < 0 for x in values):
        raise V2Error("INVALID_WILDER_SERIES")
    value = sum(values[:period], Fraction()) / period
    for x in values[period:]:
        value = ((period - 1) * value + x) / period
    return value
