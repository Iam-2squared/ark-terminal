"""Runtime CORE extraction and action mapping for the fixed R25/R33 protocol.

No estimator, label builder or evaluator is imported. This module preserves the
pinned R20 recognition results; it does not reclassify or smooth State/Signals.
Work basis: 87bf068a1dc29a8661c6d60b89141358738cabdd, 2026-09-26 JST.
Next: use these boundaries in the finite trainer/replayer, without new candidates.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

FIT_CONTRACT_SHA256 = 'e360ffe056ad1a848c55ac257b53cfd0d3be422fbe79476c70b4f69c91a12478'
ROOT_FIELDS = frozenset((
    'availabilitySemantics', 'entry', 'entryPolicy', 'entryState',
    'entryToCurrentState', 'history', 'inputMaxBarEnd', 'inputMaxKnownAt',
    'now', 'position', 'recognition', 'schemaVersion',
    'stateDwellObservedActiveMinutes'))
ENDPOINTS = frozenset((*range(541, 691), *range(751, 926)))
ARMS = ('IMMEDIATE', 'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF')
SIGNALS = ('CONTINUATION', 'BREAKOUT', 'COMPRESSION_EXPANSION',
           'HIGHER_LOW', 'LOWER_WICK', 'RECLAIM')


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def tri_state(value) -> str:
    if value is None:
        return 'UNKNOWN'
    require(type(value) is bool, 'SIGNAL_NOT_TRISTATE_BOOLEAN')
    return 'TRUE' if value else 'FALSE'


def _numeric(value):
    if value is None:
        return None
    if type(value) is bool:
        return int(value)
    require(isinstance(value, (int, float)) and math.isfinite(value),
            'NONFINITE_OR_NONNUMERIC_CORE_VALUE')
    return value


def _past(value, now, field):
    if value is not None:
        require(type(value) is int and value <= now, 'FUTURE_OR_INVALID_' + field)


class CoreEncoder:
    """Read a hash-pinned R33 artifact, then project only its exact CORE fields."""

    def __init__(self, contract_path: str | Path):
        raw = Path(contract_path).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == FIT_CONTRACT_SHA256,
                'R33_FIT_CONTRACT_HASH_MISMATCH')
        self.contract = json.loads(raw)
        self.categorical_names = tuple(self.contract['coreEncoding']['categorical'])
        self.numeric_names = tuple(self.contract['coreEncoding']['numeric'])
        require(len(set(self.categorical_names + self.numeric_names)) ==
                len(self.categorical_names) + len(self.numeric_names), 'DUPLICATE_FEATURE')

    def encode(self, row: dict) -> dict:
        require(set(row) == ROOT_FIELDS, 'CORE_ROOT_ALLOWLIST_MISMATCH')
        require(row['schemaVersion'] == 'phase57-exit-checkpoint-r20', 'R20_SCHEMA')
        require(row['entryPolicy'] in ARMS, 'UNFROZEN_ENTRY_ARM')
        now, entry = row['now'], row['entry']
        require(type(now) is int and now in ENDPOINTS, 'EXACT_DECISION_ENDPOINT_REQUIRED')
        require(type(entry['entryMinute']) is int and entry['entryMinute'] < now,
                'CHECKPOINT_NOT_AFTER_ENTRY')
        for name in ('inputMaxBarEnd', 'inputMaxKnownAt'):
            _past(row[name], now, name)
        state = row['recognition']['state']
        for item, cutoff, label in ((row['entryState'], entry['entryMinute'], 'ENTRY_STATE'),
                                     (state, now, 'CURRENT_STATE')):
            require(item['asOf'] == cutoff, label + '_ASOF_DRIFT')
            for name in ('inputCutoff', 'maxSourceBarEnd', 'lastPriceTime'):
                _past(item.get(name), cutoff, label + '_' + name)
            if item.get('maxSourceBarStart') is not None:
                require(item['maxSourceBarStart'] < cutoff, label + '_UNCLOSED_BAR')
        pos = row['position']
        require(type(pos['freshClosedPrice']) is bool and type(pos['fullOwnedPrefix']) is bool,
                'INVALID_POSITION_FLAGS')
        for name in ('lastObservedClosedAt', 'peakConfirmedAt'):
            _past(pos[name], now, name)
        if not pos['freshClosedPrice']:
            require(pos['currentReturnPct'] is None, 'STALE_PRICE_AS_CURRENT_RETURN')
        else:
            require(pos['lastObservedClosedAt'] == now, 'FRESH_CLOSE_TIME_MISMATCH')
        if not pos['fullOwnedPrefix']:
            require(pos['completePrefixMfePct'] is None and pos['completePrefixMaePct'] is None,
                    'INCOMPLETE_PATH_CERTIFIED_EXCURSION')
        values = {}
        for source_name, source in (('entryState', row['entryState']), ('currentState', state)):
            for name in ('state', 'dataQuality', 'confidence'):
                values[source_name + '.' + name] = source.get(name)
            reasons = source.get('reasonCodes') or []
            require(isinstance(reasons, list) and all(isinstance(r, str) for r in reasons),
                    'INVALID_REASON_CODES')
            values[source_name + '.reasonCodesSorted'] = '|'.join(sorted(reasons)) or 'UNKNOWN'
        transition = row['entryToCurrentState']
        if transition is not None:
            require(isinstance(transition, list) and len(transition) == 2
                    and all(isinstance(s, str) for s in transition), 'INVALID_STATE_TRANSITION')
            transition = json.dumps(transition, separators=(',', ':'))
        values['entryToCurrentState'] = transition
        values['stateDwellObservedActiveMinutes'] = row['stateDwellObservedActiveMinutes']
        history = row['history']
        for signal in SIGNALS:
            values[f'signal.{signal}.currentTriState'] = tri_state(
                row['recognition']['signals'][signal]['state'])
            values[f'signal.{signal}.observedTrueToFalseTriState'] = tri_state(
                history['bullishStateDisappeared'][signal])
        for window in (3, 5, 10):
            h = history[str(window)]
            for key in ('stateChanges', 'stateKnown', 'stateKnownAdjacentPairs'):
                values[f'history.{window}.{key}'] = h[key]
            for signal in SIGNALS:
                for key in ('true', 'false', 'unknown'):
                    values[f'history.{window}.signal.{signal}.{key}'] = h['signals'][signal][key]
        values['history.stateRunObservedSamplesCapped10'] = history['stateRunObservedSamplesCapped10']
        for name in self.numeric_names:
            if name.startswith('position.'):
                values[name] = pos[name.split('.', 1)[1]]
        categorical = []
        for name in self.categorical_names:
            value = values[name]
            require(value is None or isinstance(value, str), 'NONSTRING_CATEGORY_' + name)
            categorical.append('UNKNOWN' if value is None else value)
        numeric = [_numeric(values[name]) for name in self.numeric_names]
        # Identity is transport metadata, never added to the design matrix.
        return {'identity': [row['entryPolicy'], entry['entryId'], now],
                'session': entry['session'], 'fresh': pos['freshClosedPrice'],
                'categorical': categorical, 'numeric': numeric}


def exit_intent(predicted_hold_values, fresh: bool, previous_count: int,
                threshold_pp: float, persistence: int) -> dict:
    """R25/R33 action mapping only; no state-only action and no price argument.

    Missing observations/predictions do not advance persistence. A false fresh
    condition resets it. The execution layer resolves a separate exact OPEN.
    """
    require(type(fresh) is bool, 'FRESH_FLAG_MUST_BE_BOOLEAN')
    require(type(previous_count) is int and previous_count >= 0, 'INVALID_PERSISTENCE_COUNT')
    require(type(threshold_pp) in (int, float) and threshold_pp in (0.0, 0.10),
            'UNREGISTERED_THRESHOLD')
    require(type(persistence) is int and persistence in (1, 2), 'UNREGISTERED_PERSISTENCE')
    valid = (isinstance(predicted_hold_values, (list, tuple)) and len(predicted_hold_values) == 3
             and all(type(v) in (int, float) and math.isfinite(v) for v in predicted_hold_values))
    if not fresh or not valid:
        return {'action':'HOLD_NO_ACTION', 'consecutive':previous_count, 'scorePp':None}
    score = max(predicted_hold_values)
    count = previous_count + 1 if score <= threshold_pp else 0
    return {'action':'EXIT_INTENT' if count >= persistence else 'HOLD_NO_ACTION',
            'consecutive':count, 'scorePp':score}
