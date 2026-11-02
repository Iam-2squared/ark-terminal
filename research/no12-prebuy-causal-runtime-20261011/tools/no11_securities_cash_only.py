"""Fail-closed, securities-account-only opening funds boundary for No.1.1.

This is a *human-reviewed brokerage-summary observation*, NOT an RSS cash
balance or a machine certification of the screenshot.  Live session funding
is impossible from the bank-inclusive RSS buying-power value alone.  The
existing ledger still accounts for actual Ark broker fills and reservations;
a fresh RSS bound and unchanged operator-approved session remain independent
requirements for every live BUY.
"""
from __future__ import annotations

import hashlib
import re

import no11_broker_execution_ledger as ledger

SCHEMA = 'ARK_NO11_SECURITIES_ONLY_OPENING_CASH_V1'
AUTO = 'AUTO_SECURITIES_ACCOUNT_CASH_ONLY'
SOURCE = 'MSII_DOMESTIC_SUMMARY_RAKUTEN_SECURITIES_BUYING_POWER'
LABEL = '楽天証券買付可能額'
TICKS_PER_SECOND = ledger.TICKS_PER_SECOND
KEYS = frozenset({
    'schemaId', 'sessionDate', 'account', 'source',
    'displayedField', 'securitiesAvailableJpy',
    'sourceCapturedAtJst', 'operatorReviewedAtJst',
    'sourceDocumentPath', 'sourceDocumentSha256',
    'bankBridgeExcluded', 'autoSweepDisabledConfirmed',
    'marginAndCreditExcluded', 'operatorReviewed'
})


def need(condition, reason):
    if not condition:
        raise ValueError('NO11_SECURITIES_CASH_' + reason)


def verify_opening_evidence(value, *, session, account, now_jst,
                            document_bytes, require_fresh=True):
    """Return a pinned allocation; never use RSS buying power as its source.

    This verification cannot inspect the content of a screenshot: the human
    must check the exact displayed field and disabled auto-sweep. The SHA-256
    only proves that the reviewed local source document has not changed.
    """
    need(type(value) is dict and set(value) == KEYS, 'EVIDENCE_SCHEMA_OR_FIELDS')
    need(value['schemaId'] == SCHEMA and value['sessionDate'] == session
         and value['account'] == account, 'SESSION_OR_ACCOUNT')
    need(value['source'] == SOURCE and value['displayedField'] == LABEL,
         'SECURITIES_ONLY_SOURCE')
    need(value['bankBridgeExcluded'] is True
         and value['autoSweepDisabledConfirmed'] is True
         and value['marginAndCreditExcluded'] is True
         and value['operatorReviewed'] is True, 'SCOPE_NOT_CONFIRMED')
    amount = value['securitiesAvailableJpy']
    need(type(amount) is str and re.fullmatch(r'(?:0|[1-9][0-9]{0,13})', amount)
         is not None, 'SECURITIES_AMOUNT_FORMAT')
    ledger.money(amount)
    path = value['sourceDocumentPath']
    need(type(path) is str and bool(path) and not any(ord(c) < 32 for c in path)
         and path.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')),
         'SOURCE_DOCUMENT_TYPE')
    digest = value['sourceDocumentSha256']
    need(type(digest) is str and re.fullmatch(r'[a-f0-9]{64}', digest) is not None,
         'DOCUMENT_SHA256')
    need(type(document_bytes) is bytes and
         100 <= len(document_bytes) <= 10_000_000 and
         hashlib.sha256(document_bytes).hexdigest() == digest,
         'SOURCE_DOCUMENT_CHANGED_OR_MISSING')
    # Both source observation and operator review must belong to this
    # session. A same-day immutable proof survives a process restart, but
    # the very first ledger creation requires a freshly reviewed source.
    observed = ledger.instant(value['sourceCapturedAtJst'], session)
    reviewed = ledger.instant(value['operatorReviewedAtJst'], session)
    now = ledger.instant(now_jst, session)
    need(observed <= reviewed <= now, 'FUTURE_OR_REVERSED_EVIDENCE_CLOCK')
    need(reviewed - observed <= 15 * 60 * TICKS_PER_SECOND,
         'REVIEW_TOO_LATE_FOR_SOURCE')
    if require_fresh:
        need(now - reviewed <= 15 * 60 * TICKS_PER_SECOND,
             'OPENING_EVIDENCE_STALE')
    return {
        'allocatedCashJpy': amount,
        'sourceDocumentSha256': digest,
        'basis': 'HUMAN_REVIEWED_SECURITIES_ONLY_NOT_MACHINE_CERTIFIED',
        'bankBridgeExcluded': True,
        'autoSweepDisabledConfirmed': True,
        'orderTransmission': False
    }
