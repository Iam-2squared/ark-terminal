"""Weekly static metadata plus independently supplied actual-session guard.

This module validates inputs; it does NOT fetch issuer notices, review documents,
certify screenshots, grant order permission, or silently remove Chart50 symbols.
The same weekly file can be reused only for its named Monday-Friday interval.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

SCHEMA = 'ARK_NO11_CLEAN_WEEKLY_SECURITY_V1'
GUARD = 'ARK_NO11_CLEAN_SESSION_GUARD_V1'
LEGACY = 'ARK_NO11_SESSION_SECURITY_EVIDENCE_V1'
SYMBOL = re.compile(r'[0-9A-Z]{4}\.T\Z')
SHA = re.compile(r'[a-f0-9]{64}\Z')


def need(ok, reason):
    if not ok:
        raise ValueError('NO11_CLEAN_WEEKLY_' + reason)


def stamp(value):
    need(type(value) is str and value.endswith('+09:00'), 'JST_REQUIRED')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError('NO11_CLEAN_WEEKLY_TIME_INVALID') from None
    need(parsed.utcoffset() == timedelta(hours=9), 'JST_REQUIRED')
    return parsed


def rows(value):
    need(type(value) is list and 0 < len(value) <= 5000, 'ROWS_REQUIRED')
    indexed = {}
    for row in value:
        need(type(row) is dict and type(row.get('symbol')) is str
             and SYMBOL.fullmatch(row['symbol']) and row['symbol'] not in indexed,
             'SYMBOL_OR_DUPLICATE')
        indexed[row['symbol']] = row
    return indexed


def references(row):
    refs = row.get('sourceDocumentSha256')
    need(type(refs) is list and 0 < len(refs) <= 20
         and len(set(refs)) == len(refs)
         and all(type(s) is str and SHA.fullmatch(s) for s in refs), 'DOCUMENT_REFERENCES')
    return refs


def validate_static(info, evidence, known_at):
    now = stamp(known_at)
    need(type(evidence) is dict and evidence.get('schemaId') == SCHEMA
         and evidence.get('reviewStatus') == 'EXTERNALLY_REVIEWED'
         and evidence.get('productionReady') is False and evidence.get('orderTransmission') is False,
         'REVIEW_REQUIRED')
    try:
        monday = date.fromisoformat(evidence['weekStart'])
        friday = date.fromisoformat(evidence['weekEnd'])
        session = date.fromisoformat(info['sessionDate'])
    except (ValueError, TypeError, KeyError):
        raise ValueError('NO11_CLEAN_WEEKLY_WEEK_INVALID') from None
    need(monday.weekday() == 0 and friday == monday + timedelta(days=4)
         and monday <= session <= friday and session.weekday() < 5, 'OUTSIDE_TARGET_WEEK')
    need(stamp(evidence.get('acquiredAtJst')) <= stamp(evidence.get('knownAtJst')) <= now,
         'ACQUISITION_OR_REVIEW_IN_FUTURE')
    need(now.date() <= session, 'SESSION_ALREADY_PASSED')
    metadata = rows(evidence.get('rows'))
    selected = info.get('selectedSymbols')
    need(type(selected) is list and 0 < len(selected) <= 50
         and len(set(selected)) == len(selected), 'SELECTED_SCOPE')
    for symbol in selected:
        row = metadata.get(symbol)
        need(row is not None, 'SELECTED_REVIEW_MISSING')
        need(row.get('commonEquity') is True and row.get('domesticEquity') is True
             and row.get('listed') is True and type(row.get('lotShares')) is int
             and row['lotShares'] == 100
             and row.get('segment') in ('PRIME', 'STANDARD', 'GROWTH')
             and type(row.get('sector')) is str and 0 < len(row['sector']) <= 100,
             'STATIC_ELIGIBILITY_NOT_CONFIRMED')
        references(row)
    return metadata


def positive(value):
    need(type(value) in (int, float), 'PRICE_TYPE')
    number = Decimal(str(value))
    need(number.is_finite() and 0 < number <= Decimal('1000000000'), 'PRICE_INVALID')
    return number


def assemble(info, reference, evidence, known_at, *, weekly_sha, reference_sha):
    """Read a dated local guard, bind raw hashes, then produce legacy evidence.

Daily guard contents must be populated by a separate independent-review path.
Missing, unreviewed, stale, future or mismatched guards block preparation.
"""
    import no11_received_session_bootstrap as bootstrap
    metadata = validate_static(info, evidence, known_at)
    session = info['sessionDate']
    need(known_at[:10] == session, 'ACTUAL_SESSION_REQUIRED')
    need(type(weekly_sha) is str and SHA.fullmatch(weekly_sha)
         and type(reference_sha) is str and SHA.fullmatch(reference_sha), 'SOURCE_HASH')
    directory = bootstrap.private(evidence.get('dailyGuardDirectory'), True)
    guard, guard_sha = bootstrap.load_json(directory / (session + '.json'), 5000000)
    need(type(guard) is dict and guard.get('schemaId') == GUARD
         and guard.get('sessionDate') == session
         and guard.get('previousSession') == info['previousSession']
         and guard.get('reviewStatus') == 'EXTERNALLY_REVIEWED'
         and guard.get('productionReady') is False and guard.get('orderTransmission') is False,
         'DAILY_GUARD_REQUIRED')
    need(guard.get('weeklyFileSha256') == weekly_sha
         and guard.get('referenceFileSha256') == reference_sha
         and guard.get('chartPlanSha256') == info['chartPlanSha256'], 'DAILY_SOURCE_BINDING')
    reviewed = stamp(guard.get('knownAtJst'))
    need(reviewed.date().isoformat() == session
         and stamp(reference.get('completedAtJst')) <= reviewed <= stamp(known_at),
         'DAILY_REVIEW_TIME')
    prices = rows(reference.get('rows'))
    changes = rows(guard.get('rows'))
    selected = set(info['selectedSymbols'])
    need(set(prices) == selected and selected <= set(changes), 'DAILY_SCOPE')
    out = []
    for symbol in info['selectedSymbols']:
        static, daily, price = metadata[symbol], changes[symbol], prices[symbol]
        need(daily.get('reviewStatus') == 'CLEAR'
             and daily.get('changesReviewed') is True
             and daily.get('tradingSuspended') is False
             and daily.get('corporateActionsCleared') is True
             and daily.get('priceBasisVerified') is True, 'DAILY_REVIEW_NOT_CONFIRMED')
        need(positive(daily.get('reviewedPreviousClose')) == positive(price.get('previousClose')),
             'DAILY_PRICE_MISMATCH')
        refs = sorted(set(references(static) + references(daily)))
        need(len(refs) <= 20, 'TOO_MANY_DOCUMENT_REFERENCES')
        out.append({'symbol': symbol, 'segment': static['segment'], 'sector': static['sector'],
                    'commonEquity': True, 'corporateActionsCleared': True, 'priceBasisVerified': True,
                    'reviewedPreviousClose': daily['reviewedPreviousClose'],
                    'sourceDocumentSha256': refs})
    # Flags above were individually verified; no inference from price equality.
    return {'schemaId': LEGACY, 'validForSession': session, 'knownAtJst': guard['knownAtJst'],
            'reviewStatus': 'EXTERNALLY_REVIEWED', 'rows': out,
            'sourceBindings': {'weeklyFileSha256': weekly_sha, 'dailyGuardFileSha256': guard_sha,
                               'referenceFileSha256': reference_sha},
            'productionReady': False, 'orderTransmission': False}
