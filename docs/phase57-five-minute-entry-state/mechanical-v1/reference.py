"""Mechanical State v1 reference. Pure functions; no files/providers/models/orders.

This is an executable DEFINITION candidate, tested on synthetic bars only.
It is neither an approved market label set nor a measured causal recognizer.
Prices use exact rational arithmetic; serialization retains numerator/denominator.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction as F
import json
import math
from statistics import median, pstdev
from typing import Any, Iterable

VERSION = 'five-minute-state-mechanical-v1'
CYCLE = 5
MIN_SCALE_BLOCKS = 6
SWING_MULTIPLE = F(1)
RANGE_MINUTES = 30
RANGE_MAX_WIDTH = F(2)
RANGE_MAX_EFFICIENCY = F(1, 3)
TOUCH_BAND = F(1, 4)
TOUCH_BLOCKS = 2
CHOP_CHANGES = 2
CHOP_MAX_EFFICIENCY = F(1, 3)
CHOP_MIN_WIDTH = F(1, 2)
EXPANSION = F(3, 2)
COMPRESSION = F(2, 3)
ORACLE_HORIZON = 10
SAFETY = {k: False for k in (
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed',
    'rssOrderFunctionAllowed', 'liveTradingAllowed', 'paperTradingAllowed',
    'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted')}


def q(value: Any) -> F:
    if isinstance(value, bool):
        raise ValueError('BOOLEAN_NUMBER')
    if isinstance(value, F):
        return value
    d = Decimal(str(value))
    if not d.is_finite():
        raise ValueError('NONFINITE_NUMBER')
    return F(d)


@dataclass(frozen=True)
class Bar:
    end: int
    o: F
    h: F
    l: F
    c: F
    volume: F | None = None
    value: F | None = None
    available_at: int | None = None

    def __post_init__(self) -> None:
        if type(self.end) is not int or not 0 < self.end < 1440:
            raise ValueError('BAR_END')
        for name in ('o', 'h', 'l', 'c', 'volume', 'value'):
            if getattr(self, name) is not None:
                object.__setattr__(self, name, q(getattr(self, name)))
        if not 0 < self.l <= min(self.o, self.c) <= max(self.o, self.c) <= self.h:
            raise ValueError('INVALID_OHLC')
        if any(x is not None and x < 0 for x in (self.volume, self.value)):
            raise ValueError('NEGATIVE_ACTIVITY')
        if self.available_at is not None and (
                type(self.available_at) is not int or self.available_at < self.end):
            raise ValueError('INVALID_AVAILABLE_AT')


@dataclass(frozen=True)
class Session:
    day: str
    security: str
    basis: str | None
    ends: tuple[int, ...]
    bars: tuple[Bar, ...]

    def __post_init__(self) -> None:
        date.fromisoformat(self.day)
        validate_schedule(self.ends)
        validate_bars(self.bars)
        if not self.security or any(b.end not in self.ends for b in self.bars):
            raise ValueError('SESSION_CONTRACT')


def validate_schedule(ends: Iterable[int]) -> list[int]:
    es = list(ends)
    if any(type(t) is not int or not 0 < t < 1440 for t in es):
        raise ValueError('INVALID_SCHEDULE')
    if es != sorted(set(es)):
        raise ValueError('DUPLICATE_OR_UNSORTED_SCHEDULE')
    return es


def validate_bars(bars: Iterable[Bar], asof: int | None = None) -> list[Bar]:
    bs = list(bars)
    if any(not isinstance(b, Bar) for b in bs):
        raise ValueError('BAR_TYPE')
    ts = [b.end for b in bs]
    if ts != sorted(set(ts)):
        raise ValueError('DUPLICATE_OR_UNSORTED_BARS')
    if asof is not None and any(b.end > asof or
            (b.available_at is not None and b.available_at > asof) for b in bs):
        raise ValueError('FUTURE_OR_NOT_YET_AVAILABLE')
    return bs


def segments(items: Iterable[Any], time=lambda x: x.end) -> list[list[Any]]:
    out: list[list[Any]] = []
    for x in items:
        if not out or time(x) != time(out[-1][-1]) + 1:
            out.append([])
        out[-1].append(x)
    return out


def grid(start: int, ends: Iterable[int]) -> dict:
    es = validate_schedule(ends)
    future = [e for e in es if e > start]
    return {'checkpoints': [start] + future[4::5],
            'tailEnds': future[len(future) // 5 * 5:]}


def window(bars: Iterable[Bar], ends: Iterable[int], asof: int) -> dict:
    bs = validate_bars(bars, asof)
    schedule = validate_schedule(ends)
    es = [e for e in schedule if e <= asof][-5:]
    if any(b.end not in schedule for b in bs):
        raise ValueError('BAR_OUTSIDE_SCHEDULE')
    found = {b.end: b for b in bs}
    selected = [found[e] for e in es if e in found]
    reasons = []
    if len(es) < 5:
        reasons.append('SHORT_SESSION_HISTORY')
    if any(e not in found for e in es):
        reasons.append('MISSING_SCHEDULED_BAR')
    if len(es) == 5 and es[-1] - es[0] != 4:
        reasons.append('SESSION_BOUNDARY')
    if not es or es[-1] != asof or asof not in found:
        reasons.append('CURRENT_BAR_UNAVAILABLE')
    complete = len(selected) == 5 and not reasons
    return {'expectedEnds': es, 'observedEnds': [b.end for b in selected],
            'missingEnds': [e for e in es if e not in found],
            'status': 'COMPLETE' if complete else 'PARTIAL' if selected else 'UNAVAILABLE',
            'reasons': reasons, 'bars': selected}


def metrics(bars: Iterable[Bar]) -> dict:
    bs = validate_bars(bars)
    if not bs or len(segments(bs)) != 1:
        return {'status': 'NO_CONTIGUOUS_PATH'}
    close_d = [b.c - a.c for a, b in zip(bs, bs[1:])]
    signs = [(v > 0) - (v < 0) for v in close_d if v]
    travel = abs(bs[0].c - bs[0].o) + sum(map(abs, close_d))
    move = bs[-1].c - bs[0].o
    logs = [math.log(float(b.c / a.c)) for a, b in zip(bs, bs[1:])]
    volume = sum(b.volume for b in bs) if all(b.volume is not None for b in bs) else None
    value = sum(b.value for b in bs) if all(b.value is not None for b in bs) else None
    return {'status': 'OBSERVED', 'direction': 'UP' if move > 0 else 'DOWN' if move < 0 else 'UNCHANGED',
            'returnPct': move / bs[0].o * 100, 'width': max(b.h for b in bs) - min(b.l for b in bs),
            'efficiency': abs(move) / travel if travel else None,
            'directionChanges': sum(a != b for a, b in zip(signs, signs[1:])),
            'HH': sum(b.h > a.h for a, b in zip(bs, bs[1:])),
            'HL': sum(b.l > a.l for a, b in zip(bs, bs[1:])),
            'LH': sum(b.h < a.h for a, b in zip(bs, bs[1:])),
            'LL': sum(b.l < a.l for a, b in zip(bs, bs[1:])),
            'logReturnStdDDOF0': pstdev(logs) if len(logs) >= 2 else None,
            'volume': volume, 'value': value,
            'observedVWAP': value / volume if value is not None and volume else None}


def scale_from_previous(previous: Session, day: str, expected_previous: str,
                        security: str, basis: str | None) -> dict:
    if previous.day != expected_previous or previous.day >= day:
        raise ValueError('NOT_ACTUAL_PREVIOUS_SESSION')
    if previous.security != security:
        raise ValueError('SECURITY_MISMATCH')
    if not basis or basis != previous.basis:
        return {'status': 'PRICE_BASIS_UNVERIFIED', 'scale': None, 'blockN': 0}
    found = {b.end: b for b in previous.bars}
    ranges, witnesses = [], []
    for sg in segments(previous.ends, time=lambda x: x):
        prior = None
        for i in range(0, len(sg) - 4, 5):
            stamps = sg[i:i + 5]
            if any(t not in found for t in stamps):
                prior = None
                continue
            block = [found[t] for t in stamps]
            hi, lo = max(b.h for b in block), min(b.l for b in block)
            tr = max(hi - lo, abs(hi - prior), abs(lo - prior)) if prior is not None else hi - lo
            ranges.append(tr)
            witnesses.append(stamps)
            prior = block[-1].c
    value = median(ranges) if len(ranges) >= MIN_SCALE_BLOCKS else None
    status = 'AVAILABLE' if value is not None and value > 0 else 'SCALE_ZERO' if value == 0 else 'SCALE_INSUFFICIENT'
    return {'status': status, 'scale': value if status == 'AVAILABLE' else None,
            'blockN': len(ranges), 'sourceDay': previous.day, 'blockEnds': witnesses,
            'trueRanges': ranges, 'basis': basis}


def pivots(bars: Iterable[Bar], scale: F) -> list[dict]:
    bs = validate_bars(bars)
    s = q(scale) * SWING_MULTIPLE
    if s <= 0:
        raise ValueError('NONPOSITIVE_SCALE')
    out = []
    for sg in segments(bs):
        low = high = sg[0]
        direction = 0
        for b in sg[1:]:
            if direction == 0:
                if b.c < low.c:
                    low = b
                if b.c > high.c:
                    high = b
                if b.c - low.c >= s:
                    p, kind, direction = low, 'LOW', 1
                    high = b
                elif high.c - b.c >= s:
                    p, kind, direction = high, 'HIGH', -1
                    low = b
                else:
                    continue
            elif direction == 1:
                if b.c > high.c:
                    high = b
                if high.c - b.c < s:
                    continue
                p, kind, direction = high, 'HIGH', -1
                low = b
            else:
                if b.c < low.c:
                    low = b
                if b.c - low.c < s:
                    continue
                p, kind, direction = low, 'LOW', 1
                high = b
            out.append({'id': f'{sg[0].end}:{kind}:{p.end}', 'kind': kind,
                        'price': p.c, 'effectiveAt': p.end, 'confirmedAt': b.end,
                        'segment': sg[0].end})
    return out


def range_candidate(bars: Iterable[Bar], scale: F) -> dict | None:
    bs = validate_bars(bars)[-RANGE_MINUTES:]
    s = q(scale)
    if s <= 0:
        raise ValueError('NONPOSITIVE_SCALE')
    if len(bs) != RANGE_MINUTES or len(segments(bs)) != 1:
        return None
    hi, lo = max(b.h for b in bs), min(b.l for b in bs)
    m = metrics(bs)
    if hi == lo or hi - lo > RANGE_MAX_WIDTH * s or (
            m['efficiency'] is not None and m['efficiency'] > RANGE_MAX_EFFICIENCY):
        return None
    blocks = [bs[i:i + 5] for i in range(0, RANGE_MINUTES, 5)]
    top = [i for i, z in enumerate(blocks) if max(b.h for b in z) >= hi - TOUCH_BAND * s]
    bottom = [i for i, z in enumerate(blocks) if min(b.l for b in z) <= lo + TOUCH_BAND * s]
    if min(len(top), len(bottom)) < TOUCH_BLOCKS:
        return None
    return {'id': f'RANGE:{bs[0].end}:{bs[-1].end}', 'upper': hi, 'lower': lo,
            'bornAt': bs[-1].end, 'windowStart': bs[0].end - 1,
            'upperTouchBlocks': top, 'lowerTouchBlocks': bottom}


def attributes(latest: Iterable[Bar], prior: Iterable[Bar], scale: F | None) -> dict:
    bs, ps = validate_bars(latest), validate_bars(prior)
    m, p = metrics(bs), metrics(ps)
    tags, ratios = [], {}
    if len(bs) != 5 or m.get('status') != 'OBSERVED':
        return {'tags': [], 'ratios': {}, 'status': 'LATEST_WINDOW_INSUFFICIENT'}
    eff = m['efficiency']
    if scale is not None and m['directionChanges'] >= CHOP_CHANGES and eff is not None \
            and eff <= CHOP_MAX_EFFICIENCY and m['width'] >= CHOP_MIN_WIDTH * q(scale):
        tags.append('CHOPPINESS')
    comparable = len(ps) == 5 and p.get('status') == 'OBSERVED' and ps[-1].end + 1 == bs[0].end
    for key, label in (('width', 'RANGE'), ('volume', 'VOLUME'), ('value', 'TRADING_VALUE')):
        x, y = m.get(key), p.get(key) if comparable else None
        ratio = x / y if x is not None and y is not None and y > 0 else None
        ratios[key] = ratio
        if ratio is not None:
            if ratio >= EXPANSION:
                tags.append(label + '_EXPANSION')
            elif ratio <= COMPRESSION:
                tags.append(label + '_COMPRESSION')
    return {'status': 'OBSERVED', 'tags': tags, 'ratios': ratios, 'descriptors': m}


def level_events(bars: Iterable[Bar], level: F, level_id: str,
                 set_at: int, start: int, end: int) -> list[dict]:
    bs = validate_bars(bars, end)
    level = q(level)
    if not level_id or level <= 0 or set_at > start:
        raise ValueError('UNFIXED_OR_INVALID_LEVEL')
    out = []
    for sg in segments(bs):
        seen_up = seen_down = False
        for i, b in enumerate(sg):
            if b.end > start:
                types = []
                if i:
                    a = sg[i - 1]
                    if a.c <= level < b.c:
                        types = ['CLOSE_CROSS_UP'] + (['RECLAIM_UP'] if seen_up else [])
                    elif a.c >= level > b.c:
                        types = ['CLOSE_CROSS_DOWN'] + (['RECLAIM_DOWN'] if seen_down else [])
                if b.h > level and b.c <= level:
                    types.append('WICK_ABOVE')
                if b.l < level and b.c >= level:
                    types.append('WICK_BELOW')
                if b.l < level < b.h:
                    types.append('INTRABAR_ORDER_UNRESOLVED')
                out.extend({'kind': k, 'levelId': level_id, 'level': level,
                            'eventAt': b.end, 'levelSetAt': set_at} for k in types)
            seen_up |= b.c > level
            seen_down |= b.c < level
    return out



def vwap_events(prefix: Iterable[Bar], ends: Iterable[int], start: int, asof: int) -> dict:
    """Dynamic, full-prefix VWAP relations; no legacy Signal trigger is used."""
    bs, es = validate_bars(prefix, asof), validate_schedule(ends)
    needed = [e for e in es if e <= asof]
    if [b.end for b in bs] != needed:
        return {'status': 'PARTIAL_OBSERVATION', 'events': []}
    if any(b.volume is None or b.value is None for b in bs):
        return {'status': 'ACTIVITY_UNAVAILABLE', 'events': []}
    vol = value = F(0)
    prev = None
    events = []
    for b in bs:
        vol += b.volume
        value += b.value
        vw = value / vol if vol > 0 else None
        if b.end > start and prev and vw is not None and prev[1] is not None and prev[0].end+1 == b.end:
            a, prior_vw = prev
            kind = 'VWAP_RELATION_CROSS_UP' if a.c <= prior_vw and b.c > vw else \
                   'VWAP_RELATION_CROSS_DOWN' if a.c >= prior_vw and b.c < vw else None
            if kind:
                events.append({'kind': kind, 'eventAt': b.end, 'vwapBefore': prior_vw,
                               'vwapAfter': vw, 'movingReference': True})
        prev = (b, vw)
    return {'status': 'AVAILABLE' if vol > 0 else 'ZERO_VOLUME',
            'vwap': value/vol if vol>0 else None, 'events': events}


def confirmation(event: dict, bars: Iterable[Bar], ends: Iterable[int], cutoff: int) -> dict:
    if event['kind'] not in ('CLOSE_CROSS_UP', 'CLOSE_CROSS_DOWN', 'RECLAIM_UP', 'RECLAIM_DOWN'):
        raise ValueError('NOT_A_CLOSE_CROSS')
    es = [e for e in validate_schedule(ends) if e > event['eventAt']][:2]
    found = {b.end: b for b in validate_bars(bars, cutoff)}
    if len(es) < 2 or es[-1] > cutoff:
        return {'status': 'RIGHT_CENSORED', 'expectedEnds': es}
    if es != [event['eventAt'] + 1, event['eventAt'] + 2]:
        return {'status': 'SESSION_BOUNDARY', 'expectedEnds': es}
    if any(e not in found for e in es):
        return {'status': 'OBSERVATION_INSUFFICIENT', 'expectedEnds': es}
    up = event['kind'] in ('CLOSE_CROSS_UP', 'RECLAIM_UP')
    held = all(found[e].c > event['level'] if up else found[e].c < event['level'] for e in es)
    return {'status': 'HELD_TWO_CLOSES' if held else 'NOT_HELD_TWO_CLOSES', 'confirmedAt': es[-1]}


def _structure(bars: list[Bar], ps: list[dict], scale: F, ends: list[int],
               oracle: bool) -> dict:
    active = local_range = episode = None
    applied, events, seen, used_episodes = [], [], set(), set()
    segment_bars, previous_structure = [], None
    last, segment_start, restructuring = None, None, False
    closed_episodes = set()
    for b in bars:
        if last is None or b.end != last.end + 1:
            if last is not None:
                missing = [e for e in ends if last.end < e < b.end]
                previous_structure = active
                events.append({'kind': 'OBSERVATION_GAP' if missing else 'SCHEDULED_BREAK',
                               'eventAt': b.end, 'fromEnd': last.end})
                if missing:
                    active = local_range = None
                    restructuring = False
            applied, segment_bars, episode = [], [], None
            segment_start = b.end
        segment_bars.append(b)
        applied = [p for p in ps if p['segment'] == segment_start and
                   (p['effectiveAt'] if oracle else p['confirmedAt']) <= b.end]
        if active and active['kind'] in ('UP_STRUCTURE', 'DOWN_STRUCTURE'):
            broken = b.c < active['protected'] if active['kind'] == 'UP_STRUCTURE' else b.c > active['protected']
            if broken:
                events.append({'kind': 'STRUCTURE_INVALIDATED', 'eventAt': b.end, 'parent': active})
                previous_structure, active, restructuring = active, None, True
        if local_range and not local_range['lower'] <= b.c <= local_range['upper']:
            events.append({'kind': 'RANGE_CLOSE_EXIT', 'eventAt': b.end, 'range': local_range})
            if active and active['kind'] == 'RANGE_STRUCTURE':
                previous_structure, active, restructuring = active, None, True
            local_range = None
        tail = applied[-4:]
        if len(tail) == 4:
            sig = tuple(p['id'] for p in tail)
            if sig not in seen:
                seen.add(sig)
                hs, ls = [p for p in tail if p['kind'] == 'HIGH'], [p for p in tail if p['kind'] == 'LOW']
                kind = None
                if len(hs) == len(ls) == 2:
                    if hs[1]['price'] > hs[0]['price'] and ls[1]['price'] > ls[0]['price']:
                        kind, protected = 'UP_STRUCTURE', ls[1]['price']
                    elif hs[1]['price'] < hs[0]['price'] and ls[1]['price'] < ls[0]['price']:
                        kind, protected = 'DOWN_STRUCTURE', hs[1]['price']
                if kind and (b.c >= protected if kind == 'UP_STRUCTURE' else b.c <= protected):
                    active = {'kind': kind, 'protected': protected, 'bornAt': b.end,
                              'pivotIds': list(sig), 'confirmedAt': max(p['confirmedAt'] for p in tail)}
                    restructuring = False
        if local_range is None and len(segment_bars) % 5 == 0:
            local_range = range_candidate(segment_bars, scale)
        if active is None and local_range:
            active = {'kind': 'RANGE_STRUCTURE', 'rangeId': local_range['id'], 'bornAt': b.end,
                      'confirmedAt': b.end}
            restructuring = False
        if len(applied) >= 2 and [p['kind'] for p in applied[-2:]] == ['HIGH', 'LOW']:
            hp, lp = applied[-2:]
            eid = hp['id'] + '>' + lp['id']
            if eid not in used_episodes and hp['price'] > lp['price']:
                used_episodes.add(eid)
                episode = {'id': eid, 'high': hp['price'], 'low': lp['price'],
                           'highAt': hp['effectiveAt'], 'lowAt': lp['effectiveAt'],
                           'confirmedAt': lp['confirmedAt']}
        if episode and episode['id'] not in closed_episodes:
            ekind = 'RECOVERY_COMPLETE' if b.c >= episode['high'] else 'RECOVERY_INVALIDATED' if b.c < episode['low'] else None
            if ekind:
                closed_episodes.add(episode['id'])
                events.append({'kind': ekind, 'eventAt': b.end, 'episodeId': episode['id']})
        last = b
    leg = None
    if applied and last:
        p = applied[-1]
        if p['kind'] == 'LOW' and last.c > p['price']:
            leg = 'UP'
        elif p['kind'] == 'HIGH' and last.c < p['price']:
            leg = 'DOWN'
    phases = []
    fraction = (last.c - episode['low']) / (episode['high'] - episode['low']) if episode and last else None
    recovery = episode is not None and episode['id'] not in closed_episodes and leg == 'UP' and 0 < fraction < 1
    if active:
        kind = active['kind']
        if kind == 'RANGE_STRUCTURE':
            phases.append('BALANCE')
        elif leg:
            aligned = (kind == 'UP_STRUCTURE') == (leg == 'UP')
            if aligned and not (kind == 'UP_STRUCTURE' and recovery):
                phases.append('PROGRESSION')
            elif not aligned:
                phases.append('CORRECTION')
    elif restructuring:
        phases.append('RESTRUCTURING')
    if recovery:
        phases.append('RECOVERY')
    return {'structure': active, 'identificationStatus': 'IDENTIFIED' if active else 'UNRESOLVED_STRUCTURE',
            'phase': phases, 'leg': leg, 'episode': episode, 'recoveredFraction': fraction,
            'localRange': local_range, 'pivots': applied, 'events': events,
            'priorSegmentStructureContext': previous_structure}


def _snapshot(bars: list[Bar], ends: list[int], asof: int, scale: F | None,
              ps: list[dict], oracle: bool) -> dict:
    w = window(bars, ends, asof)
    latest = w.pop('bars')
    out = {'definitionVersion': VERSION, 'asOf': asof, 'observation': w,
           'descriptors': metrics(latest) if w['status'] == 'COMPLETE' else None,
           'availability': 'HISTORICAL_CLOSED_RECONSTRUCTION' if any(b.available_at is None for b in bars)
                           else 'EXPLICIT_AVAILABLE_AT_CHECKED',
           'scope': 'TODAY', 'mode': 'ORACLE_REFERENCE' if oracle else 'CLOSED_PREFIX'}
    if 'CURRENT_BAR_UNAVAILABLE' in w['reasons']:
        out['state'] = {'structure': None, 'phase': [], 'identificationStatus': 'CURRENT_BAR_UNAVAILABLE'}
    elif scale is None:
        out['state'] = {'structure': None, 'phase': [], 'identificationStatus': 'SCALE_UNAVAILABLE'}
    else:
        out['state'] = _structure(bars, ps, q(scale), ends, oracle)
    prior_end = latest[0].end - 1 if latest else asof
    prior = window([b for b in bars if b.end <= prior_end], ends, prior_end)
    out['attributes'] = attributes(latest if w['status'] == 'COMPLETE' else [],
                                   prior['bars'] if prior['status'] == 'COMPLETE' else [], scale)
    return out


def snapshot(prefix: Iterable[Bar], ends: Iterable[int], asof: int, scale: F | None) -> dict:
    """Closed-prefix definition evaluation, never accepts future bars."""
    bs, es = validate_bars(prefix, asof), validate_schedule(ends)
    ps = pivots(bs, scale) if scale is not None else []
    return _snapshot(bs, es, asof, scale, ps, False)


def reference_at(full_same_session: Iterable[Bar], ends: Iterable[int], asof: int,
                 scale: F | None) -> dict:
    """Evaluator-only: bounded future confirms close pivots effective by t."""
    allbars, es = validate_bars(full_same_session), validate_schedule(ends)
    if any(b.end not in es for b in allbars):
        raise ValueError('BAR_OUTSIDE_SCHEDULE')
    future = [e for e in es if e > asof][:ORACLE_HORIZON]
    cutoff = future[-1] if future else asof
    # Immutable caller input; future after the exact horizon cannot affect the label.
    bs = [b for b in allbars if b.end <= cutoff and (b.available_at is None or b.available_at <= cutoff)]
    prefix = [b for b in bs if b.end <= asof and (b.available_at is None or b.available_at <= asof)]
    ps = [p for p in pivots(bs, scale) if p['effectiveAt'] <= asof] if scale is not None else []
    out = _snapshot(prefix, es, asof, scale, ps, True)
    missing = [e for e in future if e not in {b.end for b in bs}]
    out['futureConfirmation'] = {'requestedActiveMinutes': ORACLE_HORIZON, 'cutoff': cutoff,
        'status': 'RIGHT_CENSORED' if len(future) < ORACLE_HORIZON else 'OBSERVATION_INSUFFICIENT' if missing else 'WINDOW_OBSERVED',
        'missingEnds': missing, 'effectivePivotN': len(ps),
        'lateConfirmedPivotN': sum(p['confirmedAt'] > asof for p in ps)}
    return out


def daily_context(day: str, calendar: Iterable[str], daily: Iterable[dict],
                  security: str, basis: str | None) -> dict:
    ds = list(calendar)
    if ds != sorted(set(ds)) or day not in ds:
        raise ValueError('CALENDAR_CONTRACT')
    for d in ds:
        date.fromisoformat(d)
    idx = ds.index(day)
    expected = ds[max(0, idx - 5):idx]
    rows = list(daily)
    if len({r['date'] for r in rows}) != len(rows) or any(r['date'] not in expected for r in rows):
        raise ValueError('DAILY_NOT_EXACT_LAGS')
    usable, reasons = {}, {}
    for r in rows:
        if r['security'] != security:
            raise ValueError('SECURITY_MISMATCH')
        if not basis or r.get('basis') != basis or r.get('actionUnverified', False):
            reasons[r['date']] = 'PRICE_BASIS_UNVERIFIED'
            continue
        try:
            z = Bar(1, r['o'], r['h'], r['l'], r['c'], r.get('volume'), r.get('value'))
        except (ValueError, KeyError):
            reasons[r['date']] = 'INVALID_DAILY'
            continue
        usable[r['date']] = z
    complete = len(expected) == 5 and all(d in usable for d in expected)
    out = {'expectedDates': expected, 'observedDates': sorted(usable), 'complete5': complete,
           'reasons': {d: reasons.get(d, 'MISSING_DAILY') for d in expected if d not in usable},
           'fiveDayDirection': None, 'HH': None, 'HL': None, 'LH': None, 'LL': None}
    if complete:
        z = [usable[d] for d in expected]
        x = z[-1].c - z[0].o
        out['fiveDayDirection'] = 'UP' if x > 0 else 'DOWN' if x < 0 else 'UNCHANGED'
        out['returnOC5Pct'] = x / z[0].o * 100
        out['HH'] = sum(b.h > a.h for a, b in zip(z, z[1:]))
        out['HL'] = sum(b.l > a.l for a, b in zip(z, z[1:]))
        out['LH'] = sum(b.h < a.h for a, b in zip(z, z[1:]))
        out['LL'] = sum(b.l < a.l for a, b in zip(z, z[1:]))
    out['rawDaily'] = {d: vars(z) for d, z in sorted(usable.items())}
    if complete:
        z = [usable[d] for d in expected]
        out['high5'] = max(b.h for b in z)
        out['low5'] = min(b.l for b in z)
        out['meanRangePct'] = sum((b.h-b.l)/b.o*100 for b in z)/5
        out['volume5'] = sum(b.volume for b in z) if all(b.volume is not None for b in z) else None
        out['value5'] = sum(b.value for b in z) if all(b.value is not None for b in z) else None
    if expected and expected[-1] in usable:
        z = usable[expected[-1]]
        out['D1Levels'] = {'high': z.h, 'low': z.l, 'close': z.c}
    return out


def assemble(today: Session, previous: Session | None, calendar: Iterable[str],
             daily: Iterable[dict], asof: int) -> dict:
    """Four-scope integration. Caller must supply today's CLOSED prefix only."""
    ds = list(calendar)
    ctx = daily_context(today.day, ds, daily, today.security, today.basis)
    validate_bars(today.bars, asof)
    i = ds.index(today.day)
    expected_previous = ds[i - 1] if i else None
    scale = scale_from_previous(previous, today.day, expected_previous, today.security, today.basis) \
        if previous is not None else {'status': 'PREVIOUS_CONTEXT_UNAVAILABLE', 'scale': None}
    s = scale['scale']
    prev = None
    if previous is not None and previous.basis == today.basis and today.basis:
        if previous.bars:
            end = previous.ends[-1] if previous.ends else 0
            prev = snapshot(previous.bars, previous.ends, end, s)
            prev['scope'] = 'PREVIOUS_SESSION_END_CONTEXT_ONLY'
            # Reuse today's yesterday-derived scale for THIS historical context only.
            prev['sourceSession'] = previous.day
            prev['observedHigh'] = max(b.h for b in previous.bars)
            prev['observedLow'] = min(b.l for b in previous.bars)
            prev['observedRegularClose'] = previous.bars[-1].c
            pv = [b.volume for b in previous.bars]
            pa = [b.value for b in previous.bars]
            prev['observedVWAP'] = sum(pa)/sum(pv) if all(v is not None for v in pv+pa) and sum(pv)>0 else None
            prev['coverage'] = F(len(previous.bars), len(previous.ends)) if previous.ends else None
            tail = [b for b in previous.bars if b.end in previous.ends[-30:]]
            prev['final30'] = metrics(tail) if len(tail) == 30 else {'status': 'PARTIAL'}
    state = snapshot(today.bars, today.ends, asof, s)
    state['contexts'] = {'recentDaily': ctx, 'previousDay': prev, 'scale': scale}
    state['identity'] = {'security': today.security, 'session': today.day, 'basis': today.basis}
    ww = window(today.bars, today.ends, asof)
    stamps = ww['expectedEnds']
    start = stamps[0]-1 if stamps else asof
    before = [b for b in today.bars if b.end <= start]
    levels = {}
    if prev:
        levels.update(PREVIOUS_OBSERVED_HIGH=prev['observedHigh'], PREVIOUS_OBSERVED_LOW=prev['observedLow'])
    if 'D1Levels' in ctx:
        levels.update({f'PREVIOUS_DAILY_{k.upper()}': v for k,v in ctx['D1Levels'].items()})
    if before:
        levels.update(TODAY_PRIOR_HIGH=max(b.h for b in before), TODAY_PRIOR_LOW=min(b.l for b in before))
    state['levelEvents'] = [e for name,level in sorted(levels.items())
        for e in level_events(today.bars, level, name, start, start, asof)]
    state['levelSnapshotAtWindowStart'] = levels
    state['vwapRelations'] = vwap_events(today.bars, today.ends, start, asof)
    if today.bars:
        v = [b.volume for b in today.bars]
        a = [b.value for b in today.bars]
        state['todayObserved'] = {
            'high': max(b.h for b in today.bars), 'low': min(b.l for b in today.bars),
            'observedVWAP': sum(a)/sum(v) if all(x is not None for x in v+a) and sum(v)>0 else None,
            'observedN':len(today.bars), 'expectedN':sum(e<=asof for e in today.ends)}
    return state


def transition(before: dict, after: dict) -> dict:
    if before['asOf'] >= after['asOf'] or before['scope'] != after['scope']:
        raise ValueError('TRANSITION_IDENTITY')
    if before.get('identity') != after.get('identity'):
        raise ValueError('TRANSITION_IDENTITY')
    a, b = set(before['state'].get('phase', [])), set(after['state'].get('phase', []))
    return {'from': before['asOf'], 'to': after['asOf'], 'addedPhase': sorted(b - a),
            'removedPhase': sorted(a - b), 'isEconomicReversalClaim': False,
            'observabilityAfter': after['observation']['status']}


def canonical(value: Any) -> str:
    def convert(x: Any) -> Any:
        if isinstance(x, F):
            return {'numerator': x.numerator, 'denominator': x.denominator}
        if isinstance(x, dict):
            return {k: convert(v) for k, v in sorted(x.items())}
        if isinstance(x, (list, tuple)):
            return [convert(v) for v in x]
        if isinstance(x, Bar):
            return convert(vars(x))
        return x
    return json.dumps(convert(value), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'
