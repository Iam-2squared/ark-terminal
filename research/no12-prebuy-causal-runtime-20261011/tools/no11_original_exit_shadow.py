"""Original Structural EXIT v3 + first-observed SHARP_DROP, orders disabled.

The original dataclasses execute unchanged after source-byte verification.
Only the outer PC-receipt clock and position-fill boundary are adapted. This
module never consults future market rows or invents an execution/fill.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import sys
from types import ModuleType

import no11_h235_asof_forward_shadow as h235

BASE = h235.ROOT / 'research/state9-structural-exit-v3-local-guard-20261003'
PINS = {
    'frozen_v2_lifecycle.py': 'c3a5842bc444f682ce7aa74dc2aaafe3555bb485',
    'local_guard.py': '9fd6aa0b1fa28c4cc6b286aa2ace3e61c3ae4d2d',
}
_CACHE = None


def need(ok, code):
    if not ok:
        raise ValueError('NO11_EXIT_' + code)


def load_original_exit():
    global _CACHE
    sources = {name: h235.pin_public(BASE / name, sha) for name, sha in PINS.items()}
    if _CACHE is not None:
        return _CACHE
    base = ModuleType('_no11_pinned_structural_v2')
    sys.modules[base.__name__] = base
    exec(compile(sources['frozen_v2_lifecycle.py'], '<pinned structural v2>', 'exec'), base.__dict__)
    guard = ModuleType('_no11_pinned_structural_v3')
    guard.__dict__.update(Lifecycle=base.Lifecycle, valid=base.valid, connected=base.connected)
    sys.modules[guard.__name__] = guard
    tree = ast.parse(sources['local_guard.py'])
    imports = [n for n in tree.body if isinstance(n, ast.ImportFrom) and n.module == 'frozen_v2_lifecycle']
    need(len(imports) == 1 and [n.name for n in imports[0].names] == ['Lifecycle', 'valid', 'connected'],
         'ORIGINAL_IMPORT_CHANGED')
    # Dependency name isolation only; all original decision nodes are retained.
    tree.body = [n for n in tree.body if n not in imports]
    exec(compile(ast.fix_missing_locations(tree), '<pinned structural v3>', 'exec'), guard.__dict__)
    _CACHE = (guard.GuardedLifecycle, base.valid)
    return _CACHE


def decide_received_exit(*, session, entry_at, trace, evaluated_at):
    """Replay position-local prefix; return an INTENT, never a filled position.

    A fill at hh:mm:ss>0 cannot act on the earlier closed hh:mm candle. The first
    eligible structural checkpoint is ceil(fill minute). SHARP_DROP must be
    strictly later than the actual fill instant, not an additional bar later.
    """
    entry = h235.timestamp(entry_at, session)
    through = h235.timestamp(evaluated_at, session)
    need(entry <= through and isinstance(trace, list) and len(trace) <= 400,
         'POSITION_CLOCK_OR_TRACE_INVALID')
    start = h235.minute(entry) + int(entry.second != 0 or entry.microsecond != 0)
    GuardedLifecycle, valid = load_original_exit()
    life = GuardedLifecycle(start, 920)
    prior, prior_seen = None, None
    intent = None
    seen_count = 0
    for source in trace:
        need(isinstance(source, dict) and isinstance(source.get('state'), dict)
             and isinstance(source.get('path'), dict) and isinstance(source.get('path_events'), list),
             'STATE_TRACE_REQUIRED')
        t = source.get('bar_end_minute')
        need(h235.eligible_closed_minute(t) and (prior is None or t > prior),
             'TRACE_ORDER_INVALID')
        at = session + 'T%02d:%02d:00+09:00' % divmod(t, 60)
        end = h235.timestamp(at, session)
        known = h235.timestamp(source.get('knownAtJst'), session)
        need(end <= known <= through and (prior_seen is None or known >= prior_seen),
             'UNRECEIVED_OR_FUTURE_STATE')
        need(source['state'].get('as_of') == t - 540
             and source['path'].get('scheduled_t') == t - 540
             and source['path'].get('bar_end') == at, 'TRACE_CLOCK_MISMATCH')
        prior, prior_seen = t, known
        row = deepcopy(source)
        row['slot'] = {'bar_end': at}
        if t < start:
            life.prefix(row)
            continue
        if t >= 920:
            break
        original_intent, _ = life.observe(row)
        seen_count += 1
        if original_intent is not None:
            intent = dict(original_intent, sourceKnownAtJst=source['knownAtJst'])
            break
        if end > entry and valid(row) and row['path']['Primary_or_null'] == 'SHARP_DROP':
            intent = {'reason': 'SHARP_DROP_FIRST_OBSERVED', 'minute': t,
                      'timestamp': at, 'sourceKnownAtJst': source['knownAtJst']}
            break
    if intent is None and h235.minute(through) >= 920:
        intent = {'reason': 'EOD_1520', 'minute': 920,
                  'timestamp': session + 'T15:20:00+09:00',
                  'sourceKnownAtJst': evaluated_at}
    return {'schemaId': 'ARK_NO11_ORIGINAL_EXIT_RECEIVED_SHADOW_V1',
            'sessionDate': session, 'positionEntryAtJst': entry_at,
            'evaluatedAtJst': evaluated_at, 'intent': intent,
            'originalStructuralV3Executed': True, 'sourceBlobPins': PINS,
            'observedPositionCheckpoints': seen_count,
            'observationSuspended': life.base.suspended,
            'originalHistoricalFillReplay': False,
            'productionReady': False, 'orderTransmission': False}
