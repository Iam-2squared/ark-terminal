"""Post-comparison R2_2 correction: exact binary64 square-root ties-to-even.

Only the second implementation is corrected. Frozen production code and tolerance
are unchanged. R2_1 remains immutable. The two observed decimal double-rounding
failures and their exact rational midpoint proofs are retained separately.
"""
import math
import struct
from decimal import Decimal, localcontext
from fractions import Fraction as F
from spec_engine_r2_1 import Bar, previous_scale, window
from spec_engine_r2_1 import descriptor as original_descriptor


def _even(x: float) -> bool:
    return struct.unpack('>Q', struct.pack('>d', x))[0] % 2 == 0


def sqrt_binary64(value: F) -> float:
    """Round a nonnegative rational's root by exact squared midpoint comparisons."""
    if value < 0:
        raise ValueError('NEGATIVE_VARIANCE')
    if value == 0:
        return 0.0
    with localcontext() as ctx:
        ctx.prec = 100
        guess = float((Decimal(value.numerator) / Decimal(value.denominator)).sqrt())
    if not math.isfinite(guess) or guess == 0:
        raise ValueError('OUTSIDE_FINITE_NORMAL_VARIANCE_SCOPE')
    lower = math.nextafter(guess, -math.inf)
    upper = math.nextafter(guess, math.inf)
    low_mid = (F.from_float(lower) + F.from_float(guess)) / 2
    high_mid = (F.from_float(guess) + F.from_float(upper)) / 2
    if value < low_mid * low_mid or value == low_mid * low_mid and not _even(guess):
        guess = lower
    elif value > high_mid * high_mid or value == high_mid * high_mid and not _even(guess):
        guess = upper
    # Verify nearest rounding mathematically rather than accepting any tolerance.
    lower, upper = math.nextafter(guess, -math.inf), math.nextafter(guess, math.inf)
    a = ((F.from_float(lower) + F.from_float(guess)) / 2) ** 2
    b = ((F.from_float(upper) + F.from_float(guess)) / 2) ** 2
    assert a <= value <= b and (value not in (a, b) or _even(guess)), 'ROUNDING_PROOF_FAILED'
    return guess


def descriptor(bars):
    bs = tuple(bars)
    result = original_descriptor(bs)
    if not result:
        return result
    values = [F.from_float(math.log(float(b.c / a.c))) for a, b in zip(bs, bs[1:])]
    if len(values) >= 2:
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        result['logReturnStdDDOF0'] = sqrt_binary64(variance)
    return result
