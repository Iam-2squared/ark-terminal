"""Bounded Chart50 adapter around the unchanged 20-row synthetic V5 bridge.

This is not a new allocation policy. Each native pass carries the previously
admitted rows (including zero-lot rows) in their original order and adds only
new rows, so its input never exceeds the original bridge's limit. Every pass
uses the SAME initial cash/equity/exposure; only the final full-set allocation
is returned. No reservations, fills or external side effects occur here.
"""
from __future__ import annotations

from copy import deepcopy
import no11_capital_v5_crlf_safe_synthetic as native

MAX_CANDIDATES = 50
NATIVE_BATCH_LIMIT = 20


def require(ok, code):
    if not ok:
        raise ValueError('NO11_V5_BATCH_' + code)


def run_request(request):
    require(type(request) is dict, 'REQUEST_OBJECT_REQUIRED')
    rows = request.get('preorderedCandidates')
    require(type(rows) is list and len(rows) <= MAX_CANDIDATES, 'CAPACITY_EXCEEDED')
    # The previously supported path is exactly the existing native call.
    if len(rows) <= NATIVE_BATCH_LIMIT:
        return native.run_request(request)

    # No truncation and no duplicate identity hidden across window boundaries.
    # Reuse the original symbol normalization, never a different definition.
    bridge = native.load_original_bridge()
    ids, symbols = set(), set()
    for row in rows:
        require(type(row) is dict, 'CANDIDATE_INVALID')
        identity = row.get('entry_id')
        require(type(identity) is str and identity and identity not in ids,
                'DUPLICATE_OR_INVALID_ENTRY_ID')
        code = bridge.symbol(row.get('brokerSymbol'), 'CANDIDATE_SYMBOL_INVALID')
        require(code not in symbols, 'DUPLICATE_SYMBOL')
        ids.add(identity)
        symbols.add(code)

    source = deepcopy(request)
    rows = source['preorderedCandidates']
    carry, rejected, cursor = [], [], 0
    while cursor < len(rows):
        count = NATIVE_BATCH_LIMIT - len(carry)
        require(1 <= count <= NATIVE_BATCH_LIMIT, 'CARRY_CAPACITY_INVALID')
        window = carry + rows[cursor:cursor + count]
        prior_ids = [row['entry_id'] for row in carry]
        current = dict(source, preorderedCandidates=window)
        result = native.run_request(current)
        require(result.get('status') == 'SYNTHETIC_SHADOW_ONLY'
                and result.get('orderAllowed') is False
                and result.get('transmitted') is False
                and result.get('productionReady') is False, 'NATIVE_NOT_SHADOW')
        admitted_ids = [row['entry_id'] for row in result['allocations']]
        require(admitted_ids[:len(prior_ids)] == prior_ids
                and len(admitted_ids) <= 3
                and result['admittedCount'] == len(admitted_ids),
                'NATIVE_ADMISSION_NOT_PREFIX_STABLE')
        by_id = {row['entry_id']: row for row in window}
        require(all(identity in by_id for identity in admitted_ids), 'NATIVE_UNKNOWN_ID')
        carry = [by_id[identity] for identity in admitted_ids]
        # A zero-lot admission still occupies the original one-shot decision
        # slot. Filtering it here would silently change the Frozen strategy.
        rejected.extend(result['rejected'])
        cursor += count

    handled = [row['entry_id'] for row in carry] + [row['entry_id'] for row in rejected]
    require(len(handled) == len(rows) and len(set(handled)) == len(rows)
            and set(handled) == ids, 'CANDIDATE_NOT_ACCOUNTED_FOR')
    result['rejected'] = rejected
    return result
