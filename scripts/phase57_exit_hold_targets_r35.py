"""Training-label-only exact HOLD5/HOLD15/terminal targets under R25/R33.

This module reads future references by design and MUST NOT be imported by the
CORE encoder, prediction path or action mapper. Labels are never imputed.
The caller supplies R24's continuous-minute calendar, not an observed-only clock.
"""
from __future__ import annotations
import math


def hold_targets(now: int, scheduled_starts, raw_rows) -> dict:
    starts = tuple(scheduled_starts)
    if (not starts or starts != tuple(sorted(set(starts)))
            or any(type(s) is not int for s in starts)
            or type(now) is not int or now not in {s + 1 for s in starts}):
        raise ValueError('INVALID_SCHEDULE_OR_DECISION_EPOCH')
    following = [s for s in starts if s >= now]
    exit_start = following[0] if following else None
    refs = {'exitNow': exit_start, 'HOLD5': None, 'HOLD15': None, 'HOLD_TERMINAL': 930}
    if exit_start is not None:
        index = starts.index(exit_start)
        for horizon in (5, 15):
            if index + horizon < len(starts):
                refs[f'HOLD{horizon}'] = starts[index + horizon]
    # Exact-reference index only. Never substitute the next observed quote.
    selected = {r for r in refs.values() if r is not None}
    prices = {}
    for row in raw_rows:
        if len(row) != 7 or type(row[0]) not in (int, float) or not math.isfinite(row[0]):
            raise ValueError('INVALID_RAW_ROW')
        minute = row[0]
        if minute not in selected:
            continue
        if minute in prices:
            raise ValueError('DUPLICATE_EXACT_REFERENCE')
        price = row[1]
        if type(price) not in (int, float) or not math.isfinite(price) or price <= 0:
            raise ValueError('INVALID_EXACT_OPEN')
        if minute == 930 and any(type(p) not in (int, float) or p != price for p in row[1:5]):
            raise ValueError('AUCTION_NOT_SINGLE_PRICE')
        prices[minute] = float(price)
    base = prices.get(exit_start)
    labels, reasons = {}, {}
    for target in ('HOLD5', 'HOLD15', 'HOLD_TERMINAL'):
        future = prices.get(refs[target])
        reason = ('EXIT_NOW_UNAVAILABLE' if base is None else
                  'NO_SCHEDULED_HORIZON_REFERENCE' if refs[target] is None else
                  'EXACT_TARGET_REFERENCE_MISSING' if future is None else None)
        labels[target] = None if reason else 100 * (future / base - 1)
        reasons[target] = reason
    return {'labelSideOnly': True, 'referenceMinutes': refs, 'targetsPp': labels,
            'missingReasons': reasons, 'labelImputation': False}
