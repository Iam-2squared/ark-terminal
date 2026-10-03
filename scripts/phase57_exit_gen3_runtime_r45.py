"""Frozen R45 three-authority decision boundary; no labels or execution prices."""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

from scripts.phase57_exit_execution_contract_v1 import continuous_minutes

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / 'docs/evidence/phase57-comprehensive-exit-v1/GEN3_PRECOMMIT_R45.json'
PROTOCOL_SHA256 = 'e7b38e7e6aaf909926852467152fffef2532f58f960a95e6f2d18efd66f5d1b5'
PRECOMMIT_SHA = '98345947c14ffd40c6283ce4e9be33139989b609'
HEADS = ('CONTINUATION', 'PROTECTION', 'DETERIORATION')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


@lru_cache(maxsize=1)
def _protocol():
    raw = PROTOCOL_PATH.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PROTOCOL_SHA256, 'R45_PROTOCOL_HASH')
    p = json.loads(raw)
    require(p['execution']['expectedModelFitCount'] == 24 and len(p['candidates']) == 4,
            'R45_FINITE_BUDGET')
    require(tuple(h['name'] for h in p['labels']['heads']) == HEADS, 'R45_HEAD_ORDER')
    require(len(set(c['candidateId'] for c in p['candidates'])) == 4, 'R45_CANDIDATE_IDS')
    return p


def load_protocol():
    return deepcopy(_protocol())


@lru_cache(maxsize=128)
def endpoints(day):
    return tuple(s + 1 for s in continuous_minutes(day))


@lru_cache(maxsize=128)
def endpoint_index(day):
    return {t: i for i, t in enumerate(endpoints(day))}


def adjacent(day, previous, now):
    ix = endpoint_index(day)
    return previous in ix and now in ix and ix[now] == ix[previous] + 1


def initial_state():
    return {'lastNow': None, 'armed': False, 'dCount': 0, 'pCount': 0,
            'neutralCount': 0, 'probation': 0}


def validate_facts(envelope):
    require(type(envelope) is dict and set(envelope) ==
            {'now', 'maxKnownAt', 'maxBarEnd', 'fresh', 'values'}, 'R45_FACT_ENVELOPE')
    now = envelope['now']
    require(type(now) is int and type(envelope['fresh']) is bool, 'R45_FACT_TYPES')
    for field in ('maxKnownAt', 'maxBarEnd'):
        require(type(envelope[field]) is int and 0 <= envelope[field] <= now, 'R45_FUTURE_FACT')
    values = envelope['values']
    require(type(values) is dict and set(values) == set(_protocol()['features']['decisionFactFields']),
            'R45_EXACT_FACT_ALLOWLIST')
    require(all(v is None or finite(v) for v in values.values()), 'R45_NONFINITE_FACT')
    return values


def intent(day, envelope, scores, previous_state, candidate):
    """State transition is pure; missing references cannot create queued orders."""
    p = _protocol(); q = p['policy']; values = validate_facts(envelope)
    now = envelope['now']
    require(now in endpoint_index(day), 'R45_NOT_ENDPOINT')
    require(candidate in p['candidates'], 'R45_UNREGISTERED_POLICY')
    require(type(previous_state) is dict and set(previous_state) == set(initial_state()),
            'R45_STATE_KEYS')
    s = deepcopy(previous_state)
    require(type(s['armed']) is bool, 'R45_ARMED_TYPE')
    require(all(type(s[k]) is int and s[k] >= 0 for k in
                ('dCount', 'pCount', 'neutralCount', 'probation')), 'R45_COUNTER_TYPES')
    last = s['lastNow']
    require(last is None or (type(last) is int and last in endpoint_index(day) and last < now),
            'R45_NONMONOTONE_NOW')
    if last is not None and not adjacent(day, last, now):
        s.update(dCount=0, pCount=0, neutralCount=0, probation=0)
    s['lastNow'] = now
    if now == 925:
        return {'action': 'FORCE_TERMINAL', 'authority': 'FORCE_TERMINAL', 'state': s}
    valid = (type(scores) in (list, tuple) and len(scores) == 3 and
             all(finite(v) and 0 <= v <= 1 for v in scores))
    if not envelope['fresh'] or not valid:
        s.update(dCount=0, pCount=0, neutralCount=0)
        return {'action': 'HOLD', 'authority': 'MISSING_HOLD', 'state': s}
    c, protection, d = scores
    def ge(key, bound):
        return finite(values[key]) and values[key] >= bound
    def le(key, bound):
        return finite(values[key]) and values[key] <= bound
    def lt(key, bound):
        return finite(values[key]) and values[key] < bound
    def positive(key):
        return finite(values[key]) and values[key] > 0
    s['armed'] = s['armed'] or ge('certifiedMfePct', q['profitArmMfePp'])
    recovery = ((values['stateRecovery'] == 1 or ge('signalRecoveryN', 1))
                and positive('momentum5Pct') and ge('signalTrueN', q['bullishTrueMinimum']))
    if values['newPeak'] == 1:
        s.update(pCount=0, probation=0)
    elif candidate['protectionMode'] == 'RECOVERY_PROBATION' and s['armed'] and recovery:
        s.update(pCount=0, probation=q['recoveryProbationFreshCheckpoints'])
    weak = (ge('weakRun', q['weakRunMinimum']) or
            (values['lowerHigh'] == 1 and values['lowerLow'] == 1))
    if candidate['deteriorationMode'] == 'FAILED_RECOVERY':
        weak = values['failedRecovery'] == 1 or ge('weakRun', q['sustainedWeakRunMinimum'])
    signal_bad = ge('signalFalseN', q['signalFalseMinimum']) or ge('signalLossN', q['signalLossMinimum'])
    d_ok = d >= q['scoreStrong'] and weak and lt('momentum5Pct', 0) and signal_bad
    neutral = c < q['scoreStrong'] and d < q['scoreStrong'] and (not s['armed'] or protection < q['scoreStrong'])
    s['neutralCount'] = s['neutralCount'] + 1 if neutral else 0
    neutral_bad = (s['neutralCount'] >= q['neutralFreshCheckpoints'] and
                   ge('barsHeld', q['neutralHeldActiveBars']) and le('currentReturnPct', 0) and
                   ge('weakRun', q['sustainedWeakRunMinimum']) and lt('momentum5Pct', 0) and
                   ge('signalFalseN', q['signalFalseMinimum']))
    s['dCount'] = s['dCount'] + 1 if d_ok or neutral_bad else 0
    p_ok = (s['armed'] and ge('certifiedGivebackPp', q['profitGivebackPp']) and
            ge('timeSincePeak', q['profitPeakAgeActiveBars']) and protection >= q['scoreStrong'] and
            (ge('weakRun', q['weakRunMinimum']) or
             (ge('signalLossN', q['signalLossMinimum']) and lt('momentum5Pct', 0))))
    p_ok = p_ok and s['probation'] == 0 and values['newPeak'] != 1
    s['pCount'] = s['pCount'] + 1 if p_ok else 0
    if s['dCount'] >= q['confirmationFreshCheckpoints']:
        action, authority = 'EXIT_INTENT', 'DETERIORATION' if d_ok else 'NEUTRAL_DETERIORATION'
    elif s['pCount'] >= q['confirmationFreshCheckpoints']:
        action, authority = 'EXIT_INTENT', 'PROTECTION'
    elif (c >= q['scoreStrong'] and ge('momentum5Pct', 0) and
          (ge('signalTrueN', q['bullishTrueMinimum']) or values['stateRecovery'] == 1)):
        action, authority = 'HOLD', 'CONTINUATION'
    else:
        action, authority = 'HOLD', 'OBSERVE'
    s['probation'] = max(0, s['probation'] - 1)
    return {'action': action, 'authority': authority, 'state': s}
