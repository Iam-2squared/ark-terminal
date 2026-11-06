"""Causal R45 facts from R35 observations and exact, already closed bars only."""
from __future__ import annotations
from bisect import bisect_left
from collections import deque
from functools import lru_cache

from scripts.phase57_exit_execution_contract_v1 import continuous_minutes
from scripts.phase57_exit_gen3_runtime_r45 import _protocol, adjacent, finite, require, endpoint_index

SIGNALS = ('CONTINUATION', 'BREAKOUT', 'COMPRESSION_EXPANSION', 'HIGHER_LOW', 'LOWER_WICK', 'RECLAIM')
STATES = frozenset(('RISE', 'SHARP_RISE', 'REBOUND', 'DROP', 'PULLBACK', 'RANGE',
                    'SHARP_DROP', 'DROP_STOP', 'RISE_STOP'))


@lru_cache(maxsize=128)
def schedule(day):
    return continuous_minutes(day)


def calendar_features(day, now):
    require(now in endpoint_index(day), 'R45_CALENDAR_ENDPOINT')
    remaining = len(schedule(day)) - bisect_left(schedule(day), now)
    return [remaining, min(_protocol()['labels']['maximumActiveBars'], remaining)]


def _ohlc(row):
    if row is None or len(row) != 7 or not all(finite(x) and x > 0 for x in row[1:5]):
        return False
    return row[2] >= max(row[1], row[4]) and row[3] <= min(row[1], row[4]) and row[2] >= row[3]


def price_facts(day, now, closed_rows):
    """Reject future rows; never inspect the execution candle or search missing bars."""
    index = {}
    for row in closed_rows:
        require(type(row) in (list, tuple) and len(row) == 7, 'R45_CLOSED_ROW_WIDTH')
        t = row[0]
        require(type(t) in (int, float) and finite(t) and int(t) == t and
                t < now and t + 1 <= now, 'R45_UNCLOSED_ROW')
        require(int(t) not in index, 'R45_DUPLICATE_CLOSED_ROW')
        index[int(t)] = row
    starts = schedule(day)
    pos = bisect_left(starts, now)
    required = starts[max(0, pos - 5):pos]
    selected = [index.get(t) for t in required]
    out = dict.fromkeys(('momentum5Pct', 'range5Pct', 'volume5', 'higherHigh', 'higherLow',
                         'lowerHigh', 'lowerLow'))
    if len(selected) == 5:
        if all(_ohlc(r) for r in selected):
            out['momentum5Pct'] = 100 * (selected[-1][4] / selected[0][4] - 1)
            out['range5Pct'] = 100 * (max(r[2] for r in selected) / min(r[3] for r in selected) - 1)
        if all(r is not None and finite(r[5]) and r[5] >= 0 for r in selected):
            out['volume5'] = sum(r[5] for r in selected)
    if len(selected) >= 2 and all(_ohlc(r) for r in selected[-2:]):
        before, current = selected[-2:]
        out.update(higherHigh=int(current[2] > before[2]), higherLow=int(current[3] > before[3]),
                   lowerHigh=int(current[2] < before[2]), lowerLow=int(current[3] < before[3]))
    return out


class FactEncoder:
    """One instance per Entry/arm. No cross-position or future observation state."""
    def __init__(self, day, identity):
        self.day = day
        self.identity = identity
        self.last_now = None
        self.last_fresh = False
        self.states = deque(maxlen=3)
        self.signals = None
        self.weak_run = 0
        self.certified_peak = None

    def encode(self, row, closed_rows):
        p = _protocol(); q = p['policy']
        require(set(row) == {'session', 'identity', 'fresh', 'categorical', 'numeric'}, 'R45_CORE_FIELDS')
        require(row['session'] == self.day and tuple(row['identity'][:2]) == tuple(self.identity),
                'R45_FACT_IDENTITY')
        now = row['identity'][2]
        require(type(now) is int and now in endpoint_index(self.day), 'R45_FACT_ENDPOINT')
        require(self.last_now is None or self.last_now < now, 'R45_FACT_ORDER')
        require(type(row['fresh']) is bool, 'R45_FRESH_BOOLEAN')
        require(len(row['categorical']) == 21 and len(row['numeric']) == 83, 'R45_CORE_WIDTH')
        cat = dict(zip(p['features']['categorical'], row['categorical']))
        nums = dict(zip(p['features']['baseNumeric'], row['numeric']))
        require(all(type(x) is str for x in cat.values()), 'R45_CATEGORY_TYPE')
        require(all(x is None or finite(x) for x in nums.values()), 'R45_NUMERIC_TYPE')
        for key in ('position.lastObservedClosedAt', 'position.peakConfirmedAt'):
            require(nums[key] is None or nums[key] <= now, 'R45_FUTURE_POSITION')
        fresh = row['fresh']
        consecutive = fresh and self.last_fresh and adjacent(self.day, self.last_now, now)
        if not consecutive:
            self.states.clear(); self.signals = None; self.weak_run = 0
        state = cat['currentState.state']
        previous_state = self.states[-1] if self.states else None
        tri = [cat['signal.' + name + '.currentTriState'] for name in SIGNALS]
        require(all(v in ('TRUE', 'FALSE', 'UNKNOWN') for v in tri), 'R45_SIGNAL_TRISTATE')
        values = dict.fromkeys(p['features']['decisionFactFields'])
        values.update(price_facts(self.day, now, closed_rows))
        values['barsHeld'] = nums['position.activeMinutesHeld']
        values['timeSincePeak'] = nums['position.activeMinutesSincePeakConfirmation']
        if fresh:
            require(nums['position.freshClosedPrice'] == 1 and finite(nums['position.lastObservedClose'])
                    and nums['position.lastObservedClose'] > 0 and nums['position.lastObservedClosedAt'] == now,
                    'R45_FRESH_WITHOUT_CLOSE')
            values['currentReturnPct'] = nums['position.currentReturnPct']
            complete = nums['position.fullOwnedPrefix'] == 1
            if complete:
                values['certifiedMfePct'] = nums['position.completePrefixMfePct']
                values['certifiedGivebackPp'] = nums['position.observedPeakGivebackPp']
                peak = nums['position.observedRunningHigh']
                values['newPeak'] = int(finite(peak) and
                    (self.certified_peak is None or peak > self.certified_peak))
                if finite(peak):
                    self.certified_peak = peak if self.certified_peak is None else max(peak, self.certified_peak)
            if state in STATES:
                self.weak_run = min(q['weakRunCap'], self.weak_run + 1) if state in q['weakStates'] else 0
                self.states.append(state)
            else:
                self.weak_run = 0; self.states.clear()
            values['weakRun'] = self.weak_run
            if previous_state is not None and state in STATES:
                values['stateRecovery'] = int(previous_state in q['recoveryFromStates'] and state in q['recoveryToStates'])
            if len(self.states) == 3:
                a, b, c = self.states
                values['failedRecovery'] = int(
                    (a in q['weakStates'] and b in q['recoveryToStates'] and c in q['weakStates']) or
                    (a in ('RISE', 'SHARP_RISE') and b in q['weakStates'] and c in q['weakStates']))
            values.update(signalTrueN=tri.count('TRUE'), signalFalseN=tri.count('FALSE'),
                          signalUnknownN=tri.count('UNKNOWN'))
            if self.signals is not None:
                values['signalLossN'] = sum(a == 'TRUE' and b == 'FALSE' for a, b in zip(self.signals, tri))
                values['signalRecoveryN'] = sum(a == 'FALSE' and b == 'TRUE' for a, b in zip(self.signals, tri))
            self.signals = tri
        else:
            self.states.clear(); self.signals = None; self.weak_run = 0
        self.last_now = now; self.last_fresh = fresh
        return {'now': now, 'maxKnownAt': now, 'maxBarEnd': now, 'fresh': fresh, 'values': values}
