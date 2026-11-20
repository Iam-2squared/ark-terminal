"""Training-only sampled executable utility. Never imported by decision code."""
from __future__ import annotations
from bisect import bisect_left
import math

HEADS = ('CONTINUATION', 'PROTECTION', 'DETERIORATION')
REASONS = ('AVAILABLE', 'STALE_NOW', 'NO_CONTINUOUS_ANCHOR', 'SHORT_HORIZON',
           'MISSING_REFERENCE', 'INVALID_REFERENCE', 'PROTECTION_NOT_ARMED')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def price(x):
    return type(x) in (int, float) and math.isfinite(x) and x > 0


def index_rows(rows):
    out = {}
    for row in rows:
        require(type(row) in (tuple, list) and len(row) == 7, 'R45_RAW_WIDTH')
        t = row[0]
        require(type(t) in (int, float) and math.isfinite(t) and int(t) == t, 'R45_RAW_TIME')
        require(int(t) not in out, 'R45_DUPLICATE_RAW_TIME')
        out[int(t)] = row
    return out


def reference_plan(now, schedule, contract):
    starts = tuple(schedule)
    require(type(now) is int and now in {s + 1 for s in starts}, 'R45_LABEL_ENDPOINT')
    require(starts == tuple(sorted(set(starts))) and all(type(s) is int and s < 925 for s in starts),
            'R45_LABEL_SCHEDULE')
    future = starts[bisect_left(starts, now):]
    h = min(contract['maximumActiveBars'], len(future))
    if not future:
        return None, (), h, 'NO_CONTINUOUS_ANCHOR'
    if h < contract['minimumActiveBars']:
        return future[0], (), h, 'SHORT_HORIZON'
    offsets = (math.ceil(h / 3), math.ceil(2 * h / 3), h)
    times = tuple(future[k] if k < len(future) else 930 for k in offsets)
    require(len(set(times)) == 3 and all(now < t <= 930 for t in times), 'R45_LABEL_MATURITY')
    return future[0], times, h, None


def utility_labels(now, schedule, rows, entry_price, fresh, certified_mfe, contract):
    require(price(entry_price), 'R45_EFFECTIVE_ENTRY_PRICE')
    require(type(fresh) is bool, 'R45_LABEL_FRESH_TYPE')
    anchor, times, h, reason = reference_plan(now, schedule, contract)
    if not fresh:
        reason = 'STALE_NOW'
    refs = None; utilities = None
    if reason is None:
        refs = []
        for t in (anchor, *times):
            row = rows.get(t)
            if row is None:
                reason = 'MISSING_REFERENCE'; break
            if not price(row[1]) or (t == 930 and
               (not all(price(v) for v in row[1:5]) or max(row[1:5]) != min(row[1:5]))):
                reason = 'INVALID_REFERENCE'; break
            refs.append(float(row[1]))
    targets = [None, None, None]
    reasons = [reason, reason, reason]
    if reason is None:
        utilities = [100 * (v - refs[0]) / entry_price for v in refs[1:]]
        targets[0] = int(utilities[-1] >= contract['continuationMarginPp'] and
                         sum(v > 0 for v in utilities) >= contract['positiveOrNegativeSampleMinimum'])
        targets[2] = int(utilities[-1] <= -contract['deteriorationMarginPp'] and
                         sum(v < 0 for v in utilities) >= contract['positiveOrNegativeSampleMinimum'])
        if type(certified_mfe) in (int, float) and math.isfinite(certified_mfe) and certified_mfe >= 1.0:
            targets[1] = int(utilities[-1] <= -contract['protectionMarginPp'])
        else:
            reasons[1] = 'PROTECTION_NOT_ARMED'
    return {'targets': dict(zip(HEADS, targets)), 'available': [v is not None for v in targets],
            'knownAt': [max(times) if v is not None else None for v in targets],
            'horizonBars': h, 'reasonCodes': [v or 'AVAILABLE' for v in reasons],
            'sampleReferenceMinutes': list(times), 'anchorMinute': anchor,
            'anchorPrice': refs[0] if reason is None else None,
            'futureExecutablePrices': refs[1:] if reason is None else None,
            'futureUtility': utilities}
