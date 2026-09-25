"""R20: observation-only EXIT-NOW substrate. No EXIT policy or order routing.

Receives frozen Entry identity and closed, known observations, never an outcome.
Historical archive availability is explicitly bar-end-proxy, NOT live latency proof.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import io
import json
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

ARMS = ('IMMEDIATE', 'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF')
FAMILIES = ('CONTINUATION', 'BREAKOUT', 'COMPRESSION_EXPANSION',
            'HIGHER_LOW', 'LOWER_WICK', 'RECLAIM')
SAFETY = dict.fromkeys(('executionAllowed', 'brokerWriteAllowed',
    'excelOrderWriteAllowed', 'rssOrderFunctionAllowed', 'liveTradingAllowed',
    'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
    'transmitted'), False)
ENTRY_KEYS = ('opportunity', 'session', 'symbol', 'entryId', 'entryMinute', 'price')
AVAILABILITY = 'HISTORICAL_BAR_END_PROXY_NOT_PROVIDER_PUBLICATION_TIME'


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       allow_nan=False, separators=(',', ':')) + '\n').encode()


def digest(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value) -> None:
    data = encoded(value)
    if str(path).endswith('.gz'):
        data = gzip.compress(data, mtime=0)
    with Path(path).open('xb') as f:
        f.write(data)


def read(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith('.gz') else data)


@lru_cache(maxsize=200)
def regular_minutes(day: str) -> tuple[int, ...]:
    dt.date.fromisoformat(day)
    return tuple(range(540, 690)) + tuple(range(750, 900 if day < '2024-11-05' else 925))


def active_elapsed(day: str, start: int, end: int) -> int:
    require(end >= start, 'REVERSED_TIME')
    return sum(start <= m < end for m in regular_minutes(day))


def half_session(now: int) -> str:
    return 'AM' if now <= 690 else 'PM'


def checkpoint_grid(day: str, entry_minute: int) -> tuple[int, ...]:
    require(entry_minute in regular_minutes(day), 'ENTRY_OUTSIDE_CONTINUOUS_SESSION')
    return tuple(m + 1 for m in regular_minutes(day) if m >= entry_minute)


def entry_envelope(record: dict) -> dict:
    # Only these keys are accessed, even when record contains evaluator labels.
    e = {k: record[k] for k in ENTRY_KEYS}
    require(e['opportunity'] == f"{e['session']}|{e['symbol']}", 'ENTRY_IDENTITY')
    dt.date.fromisoformat(e['session'])
    if e['entryId'] is None:
        require(e['entryMinute'] is None and e['price'] is None, 'NO_ENTRY_WITH_FILL')
    else:
        m = e['entryMinute']
        require(isinstance(m, int) and not isinstance(m, bool), 'ENTRY_MINUTE_TYPE')
        require(m in regular_minutes(e['session']), 'ENTRY_OUTSIDE_CONTINUOUS_SESSION')
        require(e['entryId'] == e['opportunity'] + '|' + str(m), 'ENTRY_IDENTITY')
        require(finite(e['price']) and e['price'] > 0, 'ENTRY_PRICE')
    return e


@dataclass(frozen=True)
class KnownBar:
    start: int
    o: float
    h: float
    l: float
    c: float
    volume: float
    value: float
    known_at: int

    def row(self) -> list:
        return [self.start, self.o, self.h, self.l, self.c, self.volume, self.value]


def closed_prefix(day: str, now: int, records: Iterable) -> tuple[KnownBar, ...]:
    """Filter by bar time/knownAt BEFORE validating candle values in a suffix.

    Raw seven-column archive rows use m+1 proxy. KnownBar inputs can carry a later
    publication time. An unclosed bar remains unavailable even if mis-stamped early.
    """
    allowed = set(regular_minutes(day))
    out = []
    for raw in records:
        if isinstance(raw, KnownBar):
            m, known = raw.start, raw.known_at
        else:
            require(len(raw) == 7, 'RAW_ROW_WIDTH')
            m, known = raw[0], raw[0] + 1
        require(finite(m) and m == int(m), 'BAR_TIME')
        require(finite(known) and known == int(known), 'KNOWN_AT_TIME')
        if m not in allowed or m + 1 > now or known > now:
            continue
        b = raw if isinstance(raw, KnownBar) else KnownBar(int(m), *raw[1:], int(known))
        require(b.known_at >= b.start + 1, 'PUBLICATION_BEFORE_CLOSE')
        require(all(finite(x) and x > 0 for x in (b.o, b.h, b.l, b.c)), 'OHLC_PRICE')
        require(b.l <= min(b.o, b.c) <= max(b.o, b.c) <= b.h, 'OHLC_BOUNDS')
        require(all(finite(x) and x >= 0 for x in (b.volume, b.value)), 'ACTIVITY_VALUE')
        require(not out or out[-1].start < b.start, 'DUPLICATE_OR_UNSORTED_BAR')
        out.append(b)
    return tuple(out)


def validate_prefix(day: str, now: int, prefix: tuple[KnownBar, ...]) -> None:
    require(all(isinstance(b, KnownBar) for b in prefix), 'NOT_KNOWN_BARS')
    require(all(b.start + 1 <= now and b.known_at <= now for b in prefix), 'FUTURE_IN_DECISION')
    require(closed_prefix(day, now, prefix) == prefix, 'NONCANONICAL_PREFIX')


def canonical_recognition(day, now, prefix, previous_day, previous):
    """Use actual canonical producers, without invoking their Entry replays."""
    import numpy as np
    from scripts.phase57_state_v3_9pattern_entry_v1 import classify_state_v3
    from scripts.phase57_entry_timing_signals import detect
    a = np.array([b.row() for b in prefix], dtype=float).reshape(-1, 7)
    pv = np.array([b.row() for b in previous], dtype=float).reshape(-1, 7)
    state = classify_state_v3(day, now, a.tolist(), pv.tolist(), previous_day)
    # Selector price is not present in the six-field frozen envelope. It affects
    # only detector context.selectorMovePct, not any of the six signal booleans.
    signals = detect(day, now, None, a, pv, previous_day)
    signals['context'].pop('selectorMovePct', None)
    return {'state': state, 'signals': signals['signals'],
            'signalContext': signals['context'], 'activity': signals['activity']}


def market_snapshot(day: str, now: int, prefix: tuple[KnownBar, ...],
                    previous_day: str | None, previous: tuple[KnownBar, ...],
                    producer: Callable = canonical_recognition) -> dict:
    validate_prefix(day, now, prefix)
    require(previous_day is None or previous_day < day, 'PREVIOUS_SESSION_NOT_PAST')
    require(not previous or previous_day is not None, 'PREVIOUS_IDENTITY_MISSING')
    if previous_day is not None:
        validate_prefix(previous_day, 1440, previous)
    result = producer(day, now, prefix, previous_day, previous)
    require(set(result['signals']) == set(FAMILIES), 'SIGNAL_FAMILY_MISMATCH')
    for values in result['signals'].values():
        for key in ('state', 'event', 'trigger'):
            require(values[key] is None or type(values[key]) is bool, 'TRISTATE_REQUIRED')
    return result


def position_features(e: dict, now: int, prefix: tuple[KnownBar, ...]) -> dict:
    validate_prefix(e['session'], now, prefix)
    require(e['entryId'] is not None and now > e['entryMinute'], 'NO_OPEN_ENTRY')
    day, start, price = e['session'], e['entryMinute'], e['price']
    owned = [b for b in prefix if b.start >= start]
    expected = active_elapsed(day, start, now)
    require(expected > 0, 'NO_COMPLETED_OWNED_SLOT')
    latest = owned[-1] if owned else None
    fresh = latest is not None and latest.start + 1 == now
    complete = len(owned) == expected
    peak = max(owned, key=lambda b: (b.h, b.start)) if owned else None
    trough = min((b.l for b in owned), default=None)
    ret = lambda p: 100 * (p / price - 1) if p is not None else None
    current = ret(latest.c) if fresh else None
    mfe = max(0., ret(peak.h)) if peak else None
    mae = min(0., ret(trough)) if trough is not None else None
    giveback = 100 * (peak.h - latest.c) / price if peak and fresh else None
    return {'clockMinutesHeld': now - start, 'activeMinutesHeld': expected,
        'observedOwnedBars': len(owned), 'missingOwnedBars': expected - len(owned),
        'fullOwnedPrefix': complete, 'freshClosedPrice': fresh,
        'lastObservedClose': latest.c if latest else None,
        'lastObservedClosedAt': latest.start + 1 if latest else None,
        'currentReturnPct': current, 'observedRunningHigh': peak.h if peak else None,
        'observedRunningLow': trough, 'observedMfePct': mfe, 'observedMaePct': mae,
        'completePrefixMfePct': mfe if complete else None,
        'completePrefixMaePct': mae if complete else None,
        'observedPeakGivebackPp': giveback,
        'peakConfirmedAt': peak.known_at if peak else None,
        'activeMinutesSincePeakConfirmation': active_elapsed(day, peak.known_at, now) if peak else None,
        'pnlSemantics': 'CLOSED_REFERENCE_VS_FROZEN_EFFECTIVE_ENTRY_NOT_REALIZED_NET'}


def summarize_history(rows: list[dict], now: int) -> dict:
    # History is bounded and local-phase. Unknown samples never become FALSE.
    require(not rows or rows[-1]['now'] == now, 'HISTORY_NOT_AT_NOW')
    phase_rows = [r for r in rows if half_session(r['now']) == half_session(now)]
    result = {}
    for w in (3, 5, 10):
        seq = phase_rows[-w:]
        states = [r['state'] for r in seq]
        pairs = [(a, b) for a, b in zip(states, states[1:]) if a is not None and b is not None]
        signals = {}
        for f in FAMILIES:
            values = [r['signals'][f] for r in seq]
            signals[f] = {'true': sum(v is True for v in values),
                          'false': sum(v is False for v in values),
                          'unknown': sum(v is None for v in values)}
        result[str(w)] = {'samples': len(seq), 'stateKnown': sum(s is not None for s in states),
            'stateKnownAdjacentPairs': len(pairs),
            'stateChanges': sum(a != b for a, b in pairs), 'signals': signals}
    current = phase_rows[-1] if phase_rows else None
    previous = phase_rows[-2] if len(phase_rows) > 1 else None
    streak = 0
    if current and current['state'] is not None:
        for r in reversed(phase_rows):
            if r['state'] != current['state']:
                break
            streak += 1
    result['stateRunObservedSamplesCapped10'] = streak if current and current['state'] else None
    result['bullishStateDisappeared'] = {
        f: (previous['signals'][f] is True and current['signals'][f] is False)
        if previous and current and previous['signals'][f] is not None and current['signals'][f] is not None
        else None for f in FAMILIES}
    return result


class PositionObserver:
    """Sequential observer. It has no SELL/HOLD function and cannot place orders."""
    def __init__(self, entry: dict, entry_state: dict | None = None):
        self.entry = entry_envelope(entry)
        self.entry_state = dict(entry_state) if entry_state else None
        self.state_dwell = 0
        self.history = collections.deque(maxlen=10)
        self.next_index = 0
        self.grid = checkpoint_grid(self.entry['session'], self.entry['entryMinute']) if self.entry['entryId'] else ()

    def step(self, now: int, prefix: tuple[KnownBar, ...], recognition: dict) -> dict:
        require(self.next_index < len(self.grid) and now == self.grid[self.next_index], 'CHECKPOINT_ORDER')
        position = position_features(self.entry, now, prefix)
        reliable = position['freshClosedPrice'] and recognition['state']['dataQuality'] == 'OK'
        row = {'now': now, 'state': recognition['state']['state'] if reliable else None,
               'signals': {f: recognition['signals'][f]['state'] if position['freshClosedPrice'] else None for f in FAMILIES}}
        last = self.history[-1] if self.history else None
        contiguous = last is not None and half_session(last['now']) == half_session(now)
        self.state_dwell = (self.state_dwell + 1 if contiguous and last['state'] == row['state'] else 1) if row['state'] is not None else 0
        self.history.append(row)
        self.next_index += 1
        return {'schemaVersion': 'phase57-exit-checkpoint-r20', 'entry': self.entry.copy(),
            'now': now, 'inputMaxBarEnd': prefix[-1].start + 1 if prefix else None,
            'inputMaxKnownAt': max((b.known_at for b in prefix), default=None),
            'availabilitySemantics': AVAILABILITY, 'position': position,
            'recognition': recognition, 'entryState': self.entry_state,
            'entryToCurrentState': [self.entry_state['state'], row['state']]
                if self.entry_state and self.entry_state['dataQuality'] == 'OK' and row['state'] is not None else None,
            'stateDwellObservedActiveMinutes': self.state_dwell if row['state'] else None,
            'history': summarize_history(list(self.history), now)}


def read_allowlisted_paths(path, allowed: set[str]) -> dict:
    """Decode only permitted top-level raw values; quarantined payloads stay opaque.

    Generic archive framing follows the already audited R13 data reader, but this
    module imports no legacy EXIT policy, replay, comparator, threshold or cap.
    """
    text = gzip.decompress(Path(path).read_bytes()).decode('utf-8')
    decoder = json.JSONDecoder()
    tokens = re.compile(r'"(?:[^"\\]|\\.)*"|[{}\[\]]')
    def ws(p):
        while p < len(text) and text[p].isspace():
            p += 1
        return p
    p = ws(0)
    require(p < len(text) and text[p] == '{', 'RAW_NOT_OBJECT')
    p = ws(p + 1)
    seen, selected = set(), {}
    while p < len(text) and text[p] != '}':
        key, p = decoder.raw_decode(text, p)
        require(isinstance(key, str) and key not in seen, 'DUPLICATE_RAW_ID')
        seen.add(key)
        p = ws(p)
        require(p < len(text) and text[p] == ':', 'RAW_SEPARATOR')
        p = ws(p + 1)
        if key in allowed:
            value, p = decoder.raw_decode(text, p)
            require(isinstance(value, dict), 'PATH_NOT_OBJECT')
            selected[key] = value
        else:
            require(p < len(text) and text[p] == '{', 'OPAQUE_VALUE_NOT_OBJECT')
            depth = 0
            for token in tokens.finditer(text, p):
                value = token.group()
                if value in ('{', '['):
                    depth += 1
                elif value in ('}', ']'):
                    depth -= 1
                    if depth == 0:
                        p = token.end()
                        break
            else:
                raise ValueError('UNTERMINATED_OPAQUE_VALUE')
        p = ws(p)
        require(p < len(text), 'RAW_END')
        if text[p] == ',':
            p = ws(p + 1)
            require(p < len(text) and text[p] != '}', 'TRAILING_COMMA')
        else:
            require(text[p] == '}', 'RAW_SEPARATOR')
    require(p < len(text) and text[p] == '}' and not text[p + 1:].strip(), 'RAW_END')
    require(set(selected) == allowed, 'MISSING_ALLOWED_PATH')
    return selected
