"""Six precommitted causal hypotheses. This module never receives future labels."""
from functools import lru_cache
import numpy as np
from scripts import phase57_entry_pattern_v2 as legacy

ROOT = legacy.ROOT
BASE = ROOT / 'docs/evidence/phase57-entry-timing-signal-census-v1'
FAMILIES = ('CONTINUATION', 'BREAKOUT', 'COMPRESSION_EXPANSION',
            'HIGHER_LOW', 'LOWER_WICK', 'RECLAIM')
EMPTY = np.empty((0, 7))


def verify():
    lock = legacy.read(BASE / 'protocol-lock.json')
    for name, digest in lock['files'].items():
        assert legacy.sha(BASE / name) == digest, name
    p = legacy.read(BASE / 'protocol.json')
    for name, digest in p['pins'].items():
        assert legacy.sha(ROOT / name) == digest, name
    assert len(p['opportunityIds']) == len(set(p['opportunityIds'])) == 2155
    assert all(v is False for v in p['safety'].values())
    assert not p['training'] and not p['dictionary'] and p['holdoutOpened'] == 0
    admission = legacy.f.s.admission.plan()
    assert p['developmentSessions'] == admission['intradayDevelopment']
    assert not set(p['evaluationSessions']) & set(admission['commonHoldout'])
    return p


def pct(x, y):
    return float(100 * (x / y - 1)) if x is not None and y is not None and y > 0 else None


def ratio(x, y):
    return float(x / y) if x is not None and y is not None and y > 0 else None


def tri_or(xs):
    xs = list(xs)
    if any(x is True for x in xs):
        return True
    return None if any(x is None for x in xs) else False


def regular(day, a):
    if not len(a):
        return EMPTY.copy()
    end = 900 if day < '2024-11-05' else 925
    return a[((a[:, 0] >= 540) & (a[:, 0] < 690)) |
             ((a[:, 0] >= 750) & (a[:, 0] < end))]


def phase_start(t):
    return 540 if t <= 690 else 750


def window(a, t, n):
    """Strict contiguous closed bars within this half-session, never imputed."""
    if t - n < phase_start(t):
        return None
    x = a[(a[:, 0] >= t - n) & (a[:, 0] < t)]
    if len(x) != n or not np.array_equal(x[:, 0], np.arange(t - n, t)):
        return None
    return x


def observed_vwap(day, a, t):
    x = a[a[:, 0] < t]
    expected = sum(m < t for m in legacy.minutes(day))
    coverage = len(x) / expected if expected else 0.
    value = ratio(float(x[:, 6].sum()), float(x[:, 5].sum())) if len(x) else None
    return (value if coverage >= .8 else None), coverage


def continuation(day, a, t):
    w = window(a, t, 5)
    vw, _ = observed_vwap(day, a, t)
    prior, _ = observed_vwap(day, a, t - 3)
    if w is None or vw is None or prior is None:
        return None
    return bool(w[-1, 4] > vw and pct(vw, prior) > 0 and
                pct(w[-1, 4], w[-4, 4]) >= .10 and
                pct(w[-1, 4], max(w[:, 2])) >= -.50 and
                np.all(np.diff(w[-3:, 2]) > 0) and
                np.all(np.diff(w[-3:, 3]) > 0))


def wick(a, t):
    w = window(a, t, 4)
    if w is None:
        return None
    z = w[-1]
    spread = z[2] - z[3]
    if spread <= 0:
        return None
    return bool((min(z[1], z[4]) - z[3]) / spread >= .50 and
                (z[4] - z[3]) / spread >= .65 and
                pct(w[-2, 4], w[0, 1]) <= -.20)


def activity(a, previous, t):
    out = {}
    for n in (1, 3, 5, 10):
        cur, pre, hist = window(a, t, n), window(a, t - n, n), window(previous, t, n)
        # Coverage reports actual observed counts even when strict ratios are null.
        for tag, arr, lo, hi in [('current', a, t-n, t), ('preceding', a, t-2*n, t-n),
                                  ('previousDay', previous, t-n, t)]:
            out[f'{n}/{tag}Rows'] = int(np.sum((arr[:, 0] >= max(phase_start(t), lo)) & (arr[:, 0] < hi)))
        for name, col in [('volume', 5), ('value', 6)]:
            c = float(cur[:, col].sum()) if cur is not None else None
            b = float(pre[:, col].sum()) if pre is not None else None
            h = float(hist[:, col].sum()) if hist is not None else None
            out[f'{n}/{name}'] = c
            out[f'{n}/{name}Acceleration'] = ratio(c, b)
            out[f'{n}/{name}RelativePreviousDay'] = ratio(c, h)
    w = window(a, t, 11)
    for name, col in [('volume', 5), ('value', 6)]:
        out[f'compression/{name}Contraction'] = ratio(float(w[5:10, col].sum()), float(w[:5, col].sum())) if w is not None else None
        out[f'expansion/{name}Expansion'] = ratio(float(w[-1, col]), float(w[5:10, col].mean())) if w is not None else None
        z = window(a, t, 2)
        out[f'wick/{name}Confirmation'] = ratio(float(z[-1, col]), float(z[-2, col])) if z is not None else None
    return out


def detect(day, t, selector_price, prefix, previous, previous_day=None):
    """Input contract: ONLY closed today prefix + previous actual session records."""
    assert not len(prefix) or np.max(prefix[:, 0]) < t, 'FUTURE_OR_UNCLOSED_BAR'
    assert not len(prefix) or np.all(np.diff(prefix[:, 0]) > 0), 'DUPLICATE_OR_UNSORTED'
    assert not len(previous) or previous_day is not None and previous_day < day, 'PREVIOUS_DAY_INVALID'
    a = regular(day, prefix)
    pv = regular(previous_day, previous) if previous_day else EMPTY
    # Previous-session identity is validated by caller against trading calendar.
    pair = window(a, t, 2)
    last = window(a, t, 1)
    close = float(last[-1, 4]) if last is not None else None
    vw, coverage = observed_vwap(day, a, t)
    vw3, _ = observed_vwap(day, a, t - 3)
    vw1, _ = observed_vwap(day, a, t - 1)
    pcoverage = len(pv) / len(legacy.minutes(previous_day)) if previous_day else 0.
    pdh = float(max(pv[:, 2])) if len(pv) and pcoverage >= .8 else None
    pdl = float(min(pv[:, 3])) if len(pv) and pcoverage >= .8 else None
    opening = a[(a[:, 0] >= 540) & (a[:, 0] < 555)]
    or_ok = t >= 555 and len(opening) == 15
    orh = float(max(opening[:, 2])) if or_ok else None
    orl = float(min(opening[:, 3])) if or_ok else None
    local = window(a, t - 1, 10)
    localh = float(max(local[:, 2])) if local is not None else None
    def cross(level):
        return bool(pair[-2, 4] <= level < pair[-1, 4]) if pair is not None and level is not None else None
    def above(level):
        return bool(close > level) if close is not None and level is not None else None
    cont = continuation(day, a, t)
    prior_cont = continuation(day, a[a[:, 0] < t-1], t-1) if pair is not None else None
    cont_event = bool(cont and not prior_cont) if cont is not None and prior_cont is not None else None
    break_events = {k: cross(val) for k, val in [('LOCAL10H', localh), ('PDH', pdh), ('ORH', orh)]}
    break_state = tri_or(above(x) for x in [localh, pdh, orh])
    comp_state = comp_event = None
    w = window(a, t, 11)
    if w is not None:
        before, consolidation, z = w[:5], w[5:10], w[-1]
        r0 = float(max(before[:, 2]) - min(before[:, 3]))
        r1 = float(max(consolidation[:, 2]) - min(consolidation[:, 3]))
        rm = float(np.mean(consolidation[:, 2] - consolidation[:, 3]))
        if r0 > 0 and rm > 0:
            comp_state = bool(pct(before[-1, 4], before[0, 1]) >= .20 and r1 / r0 <= .65 and
                              pct(consolidation[-1, 4], max(before[:, 2])) >= -.75)
            comp_event = bool(comp_state and z[4] > max(consolidation[:, 2]) and
                              z[4] > z[1] and (z[2]-z[3]) / rm >= 1.5)
    hl_state = hl_event = None
    pivot_detail = None
    w = window(a, t, 20)
    if w is not None:
        pivots = [i for i in range(1, 19) if w[i, 3] < w[i-1, 3] and w[i, 3] < w[i+1, 3]]
        hl_state = hl_event = False
        if len(pivots) >= 2:
            i, j = pivots[-2:]
            decline = pct(w[i, 3], max(w[:i, 2]))
            setup = w[j, 3] > w[i, 3] and decline <= -.20
            hl_state = bool(setup and w[-1, 4] > w[j, 2])
            hl_event = bool(hl_state and (j == 18 or w[-2, 4] <= w[j, 2] < w[-1, 4]))
            pivot_detail = {'lowBarStart': int(w[j, 0]), 'confirmedAt': int(w[j+1, 0])+1,
                            'earlierLow': float(w[i, 3]), 'laterLow': float(w[j, 3])}
    wick_state = wick(a, t)
    wick_prev = wick(a[a[:, 0] < t-1], t-1)
    wick_event = bool(wick_prev and pair[-1, 4] > pair[-2, 2] and pair[-1, 3] >= pair[-2, 3]) if wick_prev is not None and pair is not None else None
    vwap_reclaim = bool(pair[-2, 4] <= vw1 and pair[-1, 4] > vw) if pair is not None and vw is not None and vw1 is not None else None
    reclaim_events = {'VWAP': vwap_reclaim, 'PDL': cross(pdl), 'ORL': cross(orl)}
    returns = {}
    for n in (1, 3, 5, 10):
        w = window(a, t, n+1)
        returns[str(n)] = pct(w[-1, 4], w[0, 4]) if w is not None else None
    w = window(a, t, 5)
    context = {'returnPct': returns, 'selectorMovePct': pct(close, selector_price),
               'vwapDistancePct': pct(close, vw), 'vwapSlope3Pct': pct(vw, vw3),
               'pullback5Pct': pct(close, max(w[:, 2])) if w is not None else None,
               'precedingDecline3': returns['3'] < 0 if returns['3'] is not None else None,
               'previousBelowVWAP': bool(pair[-2, 4] <= vw1) if pair is not None and vw1 is not None else None,
               'vwapObservedCoverage': coverage, 'previousCoverage': pcoverage,
               'openingRangeComplete': or_ok, 'previousDayAvailable': bool(len(pv)),
               'close': close, 'observedVWAP': vw, 'PDHObserved': pdh, 'PDLObserved': pdl,
               'ORH': orh, 'ORL': orl, 'localResistance': localh}
    signals = {
        'CONTINUATION': {'state': cont, 'event': cont_event},
        'BREAKOUT': {'state': break_state, 'event': tri_or(break_events.values()), 'levels': break_events},
        'COMPRESSION_EXPANSION': {'state': comp_state, 'event': comp_event},
        'HIGHER_LOW': {'state': hl_state, 'event': hl_event, 'pivot': pivot_detail},
        'LOWER_WICK': {'state': wick_state, 'event': wick_event},
        'RECLAIM': {'state': above(vw), 'event': tri_or(reclaim_events.values()), 'levels': reclaim_events},
    }
    for family, item in signals.items():
        item['trigger'] = item['state'] if family == 'CONTINUATION' else item['event']
    return {'minute': int(t), 'barClosedAtJst': '%02d:%02d' % divmod(t, 60),
            'computedThroughBarStart': int(a[-1, 0]) if len(a) else None,
            'newClosedBarObserved': last is not None,
            'signals': signals, 'context': context, 'activity': activity(a, pv, t)}


def comparison_grid(day, start):
    return legacy.clock(day, start)


def census_grid(day, start):
    return sorted(set(t+1 for t in legacy.minutes(day) if t+1 >= start) |
                  set(comparison_grid(day, start)))


def replay(oid, day, start, observations, quote_by_minute, fill_by_minute, arms):
    """Intent depends ONLY on observations. Fill lookup is consulted AFTER attempt."""
    grid = comparison_grid(day, start)
    target = min(10, legacy.elapsed(day, start, grid[-1])) if grid else None
    ans = {}
    for arm, families in arms.items():
        attempts, intent, fill, trigger_at, trigger_reason = [], False, None, None, None
        for t in grid:
            delay = legacy.elapsed(day, start, t)
            signals = observations[t]['signals']
            firing = [name for name in families if name in signals and signals[name]['trigger'] is True]
            if not intent and (arm == 'A' or firing or delay >= target):
                intent = True
                trigger_at = t
                trigger_reason = 'IMMEDIATE' if arm == 'A' else 'SIGNAL' if firing else 'FALLBACK'
            if not intent:
                attempts.append({'minute': t, 'state': 'WAIT', 'firing': firing})
                continue
            item = {'minute': t, 'state': 'BUY_ATTEMPT', 'intentReason': trigger_reason, 'firing': firing}
            if not quote_by_minute.get(t, False):
                item.update(result='UNAVAILABLE_REFERENCE', reason='STALE_OR_MISSING_REFERENCE')
            else:
                price = fill_by_minute.get(t)
                if price is None:
                    item.update(result='UNFILLED', reason='MISSING_SOURCE_UNCLASSIFIED')
                else:
                    item.update(result='FILLED_PROXY', price=price)
                    fill = t
            attempts.append(item)
            if fill is not None:
                break
        buy_attempts = sum(x['state'] == 'BUY_ATTEMPT' for x in attempts)
        reason = None if fill is not None else 'SESSION_BOUNDARY' if not grid else 'RETRY_EXHAUSTED'
        ans[arm] = {'opportunity': oid, 'session': day, 'entryId': oid+'|'+str(fill) if fill is not None else None,
                    'entryMinute': fill, 'price': fill_by_minute.get(fill) if fill is not None else None,
                    'delay': legacy.elapsed(day, start, fill) if fill is not None else None,
                    'intentMinute': trigger_at, 'intentReason': trigger_reason,
                    'fallbackTargetDelay': target, 'attempts': attempts,
                    'buyAttemptCount': buy_attempts, 'retryCount': max(0, buy_attempts-1),
                    'unfilledReason': reason, 'modelRejection': False}
    return ans
