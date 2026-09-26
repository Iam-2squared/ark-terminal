"""Frozen R45 three-authority runtime. No labels, raw paths, model or evaluator.

Each call consumes only current scores and the exact causal fact envelope.
R45 semantics/thresholds/candidates are not modified by this implementation.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import math

PROTOCOL_PATH = Path(__file__).resolve().parents[1] / 'docs/evidence/phase57-comprehensive-exit-v1/GEN3_PRECOMMIT_R45.json'
PROTOCOL_SHA256 = 'e7b38e7e6aaf909926852467152fffef2532f58f960a95e6f2d18efd66f5d1b5'
PRECOMMIT_SHA = '98345947c14ffd40c6283ce4e9be33139989b609'
HEADS = ('CONTINUATION', 'PROTECTION', 'DETERIORATION')
ENDPOINTS = (*range(541, 691), *range(751, 926))
EPOCH = {v: i for i, v in enumerate(ENDPOINTS)}
STATES = frozenset(('RISE','SHARP_RISE','REBOUND','DROP','PULLBACK','RANGE','SHARP_DROP','DROP_STOP','RISE_STOP'))
SIGNALS = ('CONTINUATION','BREAKOUT','COMPRESSION_EXPANSION','HIGHER_LOW','LOWER_WICK','RECLAIM')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


@lru_cache(maxsize=1)
def _protocol():
    raw = PROTOCOL_PATH.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PROTOCOL_SHA256, 'R45_PROTOCOL_HASH')
    p = json.loads(raw)
    require(p['generation'] == 3 and len(p['candidates']) == 4, 'R45_GRID')
    require(p['execution']['expectedModelFitCount'] == 24, 'R45_FITS')
    require(tuple(x['name'] for x in p['labels']['heads']) == HEADS, 'R45_HEADS')
    require(len(p['features']['decisionFactFields']) == 21, 'R45_FACTS')
    return p


def load_protocol():
    return json.loads(json.dumps(_protocol()))


def adjacent(previous, now):
    return previous in EPOCH and EPOCH[now] == EPOCH[previous] + 1


def validate_facts(envelope):
    require(isinstance(envelope, dict) and set(envelope) == {'now','maxKnownAt','maxBarEnd','fresh','values'}, 'R45_FACT_ENVELOPE_ALLOWLIST')
    now = envelope['now']
    require(type(now) is int and now in EPOCH, 'R45_EXACT_NOW')
    for name in ('maxKnownAt','maxBarEnd'):
        t = envelope[name]
        require(t is None or (type(t) is int and t <= now), 'R45_FUTURE_SOURCE_' + name)
    require(type(envelope['fresh']) is bool, 'R45_FRESH_BOOLEAN')
    values = envelope['values']
    require(isinstance(values, dict) and set(values) == set(_protocol()['features']['decisionFactFields']), 'R45_FACT_ALLOWLIST')
    require(all(v is None or finite(v) for v in values.values()), 'R45_INVALID_FACT_VALUE')
    for name in ('higherHigh','higherLow','lowerHigh','lowerLow','stateRecovery','failedRecovery','newPeak'):
        require(values[name] in (None, 0, 1), 'R45_BINARY_FACT_' + name)
    for name in ('signalTrueN','signalFalseN','signalUnknownN','signalLossN','signalRecoveryN','weakRun'):
        value = values[name]
        require(value is None or (type(value) is int and 0 <= value <= (10 if name == 'weakRun' else 6)), 'R45_COUNT_' + name)
    if not envelope['fresh']:
        require(all(values[k] is None for k in ('currentReturnPct','certifiedMfePct','certifiedGivebackPp')), 'R45_STALE_CERTIFICATE')
    return values


@dataclass(frozen=True)
class Memory:
    lastNow: int | None = None
    armed: bool = False
    dCount: int = 0
    pCount: int = 0
    neutralCount: int = 0
    probationRemaining: int = 0
    mode: str = 'OBSERVE'


def intent(scores, facts, memory, candidate):
    """Pure causal state transition; D overrides P, and C never vetoes them."""
    p = _protocol()['policy']
    require(candidate in _protocol()['candidates'], 'R45_UNREGISTERED_CANDIDATE')
    require(type(memory) is Memory, 'R45_MEMORY_TYPE')
    v = validate_facts(facts); now = facts['now']
    require(memory.lastNow is None or now > memory.lastNow, 'R45_NONMONOTONIC_NOW')
    m = replace(memory, lastNow=now)
    if memory.lastNow is not None and not adjacent(memory.lastNow, now):
        m = replace(m, dCount=0, pCount=0, neutralCount=0, probationRemaining=0)
    def result(action, authority, state):
        return {'action': action, 'authority': authority, 'state': asdict(state)}
    if now == 925:
        return result('FORCE_TERMINAL','FORCE_TERMINAL', replace(m, mode='TERMINAL'))
    valid = isinstance(scores, (list,tuple)) and len(scores) == 3 and all(finite(x) and 0 <= x <= 1 for x in scores)
    if not facts['fresh'] or not valid:
        m = replace(m, dCount=0, pCount=0, neutralCount=0,
                    mode='PROTECT' if m.armed else 'OBSERVE')
        return result('HOLD','MISSING_HOLD',m)
    ge = lambda key, threshold: finite(v[key]) and v[key] >= threshold
    lt = lambda key, threshold: finite(v[key]) and v[key] < threshold
    eq = lambda key: v[key] == 1
    c, protection, d = scores
    strong = p['scoreStrong']; required = p['confirmationFreshCheckpoints']
    m = replace(m, armed=m.armed or ge('certifiedMfePct', p['profitArmMfePp']))
    new_peak = eq('newPeak') and finite(v['certifiedMfePct'])
    if new_peak:
        m = replace(m, pCount=0, probationRemaining=0)
    recovery = ((eq('stateRecovery') or ge('signalRecoveryN', 1))
                and finite(v['momentum5Pct']) and v['momentum5Pct'] > 0
                and ge('signalTrueN', p['bullishTrueMinimum']))
    if m.armed and not new_peak and recovery and candidate['protectionMode'] == 'RECOVERY_PROBATION':
        m = replace(m, probationRemaining=p['recoveryProbationFreshCheckpoints'], pCount=0)
    bad_signals = ge('signalFalseN',p['signalFalseMinimum']) or ge('signalLossN',p['signalLossMinimum'])
    if candidate['deteriorationMode'] == 'MULTI_EVIDENCE':
        structure = ge('weakRun',p['weakRunMinimum']) or (eq('lowerHigh') and eq('lowerLow'))
    else:
        structure = eq('failedRecovery') or ge('weakRun',p['sustainedWeakRunMinimum'])
    d_ok = d >= strong and structure and lt('momentum5Pct',0) and bad_signals
    neutral = c < strong and d < strong and (not m.armed or protection < strong)
    nc = m.neutralCount + 1 if neutral else 0
    n_ok = (nc >= p['neutralFreshCheckpoints'] and ge('barsHeld',p['neutralHeldActiveBars'])
            and finite(v['currentReturnPct']) and v['currentReturnPct'] <= 0
            and ge('weakRun',p['sustainedWeakRunMinimum']) and lt('momentum5Pct',0)
            and ge('signalFalseN',p['signalFalseMinimum']))
    dc = m.dCount + 1 if d_ok or n_ok else 0
    p_ok = (m.armed and ge('certifiedGivebackPp',p['profitGivebackPp'])
            and ge('timeSincePeak',p['profitPeakAgeActiveBars']) and protection >= strong
            and (ge('weakRun',p['weakRunMinimum']) or (ge('signalLossN',1) and lt('momentum5Pct',0))))
    suppressed = m.probationRemaining > 0 or new_peak
    pc = m.pCount + 1 if p_ok and not suppressed else 0
    remaining = max(0,m.probationRemaining-1)
    m = replace(m,dCount=dc,pCount=pc,neutralCount=nc,probationRemaining=remaining,
                mode='PROBATION' if remaining else 'PROTECT' if m.armed else 'OBSERVE')
    if dc >= required:
        return result('EXIT_INTENT','DETERIORATION' if d_ok else 'NEUTRAL_DETERIORATION',m)
    if pc >= required:
        return result('EXIT_INTENT','PROTECTION',m)
    alive = c >= strong and ge('momentum5Pct',0) and (ge('signalTrueN',1) or eq('stateRecovery'))
    return result('HOLD','CONTINUATION' if alive else 'OBSERVE',m)
