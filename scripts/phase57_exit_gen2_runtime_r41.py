"""Frozen R41 decision boundary: no labels, estimators, raw paths or evaluators.

Implementation follows GitHub precommit 0ba0112fff98cd1d8d864dc1967bbd76095e8d66.
The Failure score is an adverse-excursion proxy, not proven thesis collapse.
"""
from __future__ import annotations

from bisect import bisect_left
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

from scripts.phase57_exit_execution_contract_v1 import continuous_minutes

PROTOCOL_PATH = Path(__file__).resolve().parents[1] / 'docs/evidence/phase57-comprehensive-exit-v1/GEN2_PRECOMMIT_R41.json'
PROTOCOL_SHA256 = '5fdc059936ba31466a7dace520f218353c634e6c8444d20d5ab21069c745deb4'
PRECOMMIT_SHA = '0ba0112fff98cd1d8d864dc1967bbd76095e8d66'
CALENDAR_FIELDS = ('calendar.remainingContinuousBars',
                   'calendar.continuationHorizonBars', 'calendar.failureHorizonBars')
HEADS = ('CONTINUATION', 'FAILURE')
ENDPOINTS = frozenset((*range(541, 691), *range(751, 926)))


def require(condition, message):
    if not condition:
        raise ValueError(message)


@lru_cache(maxsize=1)
def _protocol():
    raw = PROTOCOL_PATH.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PROTOCOL_SHA256, 'R41_PROTOCOL_HASH')
    p = json.loads(raw)
    require(p['execution']['candidateCount'] == len(p['candidates']) == 16, 'R41_GRID_COUNT')
    require(p['execution']['expectedModelFitCount'] == 64, 'R41_FIT_COUNT')
    require(len({c['candidateId'] for c in p['candidates']}) == 16, 'R41_DUPLICATE_ID')
    require(p['features']['calendarFields'] == list(CALENDAR_FIELDS), 'R41_CALENDAR_FIELDS')
    require([h['name'] for h in p['labels']['heads']] == list(HEADS), 'R41_HEAD_ORDER')
    require([h['maximumActiveBars'] for h in p['labels']['heads']] == [60, 15], 'R41_HORIZONS')
    return p


def load_protocol():
    """Return an independent copy; callers cannot mutate the runtime contract."""
    return deepcopy(_protocol())


@lru_cache(maxsize=128)
def _schedule(day):
    return continuous_minutes(day)


def calendar_features(day, now):
    """Calendar-only features. No market row or label availability is accepted."""
    require(type(now) is int and now in ENDPOINTS, 'R41_DECISION_ENDPOINT')
    starts = _schedule(day)
    remaining = len(starts) - bisect_left(starts, now)
    return [remaining, min(60, remaining), min(15, remaining)]


@lru_cache(maxsize=1)
def _candidates():
    return {c['candidateId']: c for c in _protocol()['candidates']}


def intent(scores, fresh, previous_count, candidate, now):
    """Map two current OOF scores to an intent; execution is a separate layer.

    Stale/invalid scores neither advance nor reset fresh persistence. A valid
    false condition resets it. Conflicts always HOLD. No price/PnL/State is read.
    """
    require(type(now) is int and now in ENDPOINTS, 'R41_DECISION_ENDPOINT')
    require(type(fresh) is bool, 'R41_FRESH_BOOLEAN')
    require(type(previous_count) is int and previous_count >= 0, 'R41_PERSISTENCE_COUNT')
    require(isinstance(candidate, dict)
            and candidate.get('candidateId') in _candidates()
            and candidate == _candidates()[candidate['candidateId']], 'R41_UNREGISTERED_POLICY')
    if now == 925:
        return {'action': 'FORCE_TERMINAL', 'consecutive': previous_count}
    valid = (isinstance(scores, (list, tuple)) and len(scores) == 2
             and all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in scores))
    if not fresh or not valid:
        return {'action': 'HOLD', 'consecutive': previous_count}
    continuation, failure = scores
    exit_side = (continuation <= candidate['continuationWeakMax']
                 and failure >= candidate['failureStrongMin'])
    count = previous_count + 1 if exit_side else 0
    return {'action': 'EXIT_INTENT' if count >= candidate['persistenceFreshCheckpoints'] else 'HOLD',
            'consecutive': count}
