"""Durable Capital decision provenance; never authorizes or retries an order.

Used by the source-pinned operational-hardening transform. Keep the original
same-minute/90-second rule, allocator, consumed IDs and submit_intents boundary.
Each new batch gets an immutable ledger EVENT payload with its actual evaluation
clock and disposition. Existing consumed IDs without an audit remain historical
unknowns; do not reconstruct, reprice, or submit them.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re

SCHEMA = 'ARK_NO11_CAPITAL_DECISION_AUDIT_V1'
PREFIX = 'capital.decision.'
LATEST = 'capital.decision.latest'


def _safe_reason(error):
    code = str(error)
    return code if re.fullmatch(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]{1,180}', code) else 'UNCLASSIFIED_REDACTED'


def _record(service, rows, fresh_ids, at, result, error, time_api):
    fresh_ids = set(fresh_ids)
    allocations = {r['entry_id']: r for r in (result or {}).get('allocations', [])}
    rejections = {r['entry_id']: r['reason'] for r in (result or {}).get('rejected', [])}
    intents = {r['entryId']: r for r in (result or {}).get('intents', [])}
    candidates = []
    now = time_api.timestamp(at, service.session)
    for row in rows:
        key = row['candidateId']
        decision = time_api.timestamp(row['decisionAtJst'], service.session)
        age = (now - decision).total_seconds()
        same_minute = time_api.minute(decision) == time_api.minute(now)
        quantity = None
        rejection = None
        if key not in fresh_ids:
            reason = 'SKIPPED_MINUTE_BOUNDARY' if not same_minute else 'SKIPPED_AGE_LIMIT'
        elif error is not None:
            reason = 'CAPITAL_CALCULATION_FAILED'
        elif row.get('admission') is False:
            reason = 'H235_NOT_ADMITTED'
        elif key in rejections:
            reason, rejection = 'CAPITAL_REJECTED', str(rejections[key])
            if not re.fullmatch(r'[A-Z0-9_]{1,160}', rejection):
                rejection = 'UNCLASSIFIED_REDACTED'
        elif key in allocations:
            quantity = allocations[key]['quantity']
            reason = ('ALLOCATED_ZERO_QUANTITY' if quantity == 0 else
                      'BUY_INTENT_CREATED' if key in intents else 'ALLOCATION_WITHOUT_INTENT')
        else:
            reason = 'CAPITAL_RESULT_NOT_EXPLAINED'
        candidates.append({
            'candidateId': key, 'candidateSha256': time_api.digest(row),
            'h235Admitted': row.get('admission'), 'decisionAtJst': row['decisionAtJst'],
            'capitalEvaluatedAtJst': at, 'ageSeconds': age,
            'sameMinute': same_minute, 'within90Seconds': 0 <= age <= 90,
            'eligibleForCapital': key in fresh_ids, 'disposition': reason,
            'rejectionReason': rejection, 'quantity': quantity,
            'orderSubmittedByAudit': False,
        })
    record = {
        'schemaId': SCHEMA, 'sessionDate': service.session, 'evaluatedAtJst': at,
        'candidates': candidates, 'capitalResult': deepcopy(result),
        'errorCode': _safe_reason(error) if error is not None else None,
        'sourceIsHistoricalReconstruction': False,
        'orderTransmission': False, 'orderAcceptanceConfirmed': False,
    }
    key = PREFIX + time_api.digest([service.session, at, [(r['candidateId'], time_api.digest(r)) for r in rows]])
    old = service.book.source_checkpoint(key)
    if old is not None and old != record:
        raise ValueError('NO11_CAPITAL_AUDIT_EVENT_CHANGED')
    # Ledger events preserve the record even when the latest pointer changes.
    service.book.checkpoint_source(key, record, at)
    service.book.checkpoint_source(LATEST, {'auditKey': key, 'auditSha256': time_api.digest(record),
                                          'evaluatedAtJst': at, 'orderTransmission': False}, at)
    return record


def fund_with_audit(service, batch, quotes, at, *, time_api, decisions, require):
    """Same native decision/send semantics, plus fail-closed pre-send evidence."""
    require(type(batch) is dict and type(batch.get('results')) is list, 'H235_BATCH')
    consumed = service.book.source_checkpoint('capital.consumed') or {}
    changed, fresh, new = dict(consumed), [], []
    seen = set()
    for row in batch['results']:
        key, sha = row.get('candidateId'), time_api.digest(row)
        require(type(key) is str and bool(key), 'CANDIDATE_ID')
        require(key not in seen, 'CANDIDATE_DUPLICATE')
        seen.add(key)
        require(key not in consumed or consumed[key] == sha, 'CANDIDATE_CHANGED')
        if key not in consumed:
            decision = time_api.timestamp(row.get('decisionAtJst'), service.session)
            now = time_api.timestamp(at, service.session)
            require(decision <= now, 'CANDIDATE_FROM_FUTURE')
            if time_api.minute(decision) == time_api.minute(now) and (now - decision).total_seconds() <= 90:
                fresh.append(row)
            changed[key] = sha
            new.append(row)
    if not fresh:
        if changed != consumed:
            _record(service, new, [], at, None, None, time_api)
            service.book.checkpoint_source('capital.consumed', changed, at)
        return None
    try:
        result = decisions.calculate_capital(dict(batch, results=fresh), service._capital_input(quotes, at), service.arrival)
    except Exception as error:
        _record(service, new, [r['candidateId'] for r in fresh], at, None, error, time_api)
        raise
    _record(service, new, [r['candidateId'] for r in fresh], at, result, None, time_api)
    service.book.checkpoint_source('capital.consumed', changed, at)
    service.last_decision = result
    # This remains the original physical boundary, with all native checks.
    service.submit_intents(result['intents'], service.clock())
    return result


def audit_summary(book):
    """A hint for reports, not an order-permission input or a broker receipt."""
    value = book.source_checkpoint(LATEST)
    return deepcopy(value) if value is not None else {
        'status': 'NO_AUDIT_RECORDED', 'historicalReasonsReconstructed': False,
        'orderTransmission': False,
    }
