#!/usr/bin/env python3
"""Weekly security identity cache and daily, automatic entry-only checks.

The weekly cache is NOT a stale dated master with its date replaced. Prices,
trading dates and exception observations must come from the actual session.
An excluded symbol never becomes a SELL instruction; held-position EXIT is
outside this module. No broker, COM, model, fitting or order side effects.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

WEEKLY = 'ARK_NO11_WEEKLY_SECURITY_MASTER_V1'
CHANGES = 'ARK_NO11_SESSION_SECURITY_CHANGES_V1'
ADMISSION = 'ARK_NO11_WEEKLY_SESSION_ADMISSION_V1'
MASTER = 'ARK_NO11_DATED_MASTER_RECEIPT_V1'
BASIS = 'AUTOMATED_WEEKLY_METADATA_AND_SESSION_CHECKS_V1'
REQUIRED_FEEDS = frozenset({'supervision', 'delisting', 'suspension', 'rights', 'transfers'})
SEGMENTS = {'東証P': 'PRIME', '東証Ｐ': 'PRIME', '東証S': 'STANDARD',
            '東証Ｓ': 'STANDARD', '東証G': 'GROWTH', '東証Ｇ': 'GROWTH'}
SYMBOL = re.compile(r'[0-9A-Z]{4}\.T')
SHA = re.compile(r'[a-f0-9]{64}')
JST = timezone(timedelta(hours=9))


def need(ok, code):
    if not ok:
        raise ValueError('NO11_WEEKLY_SECURITY_' + code)


def instant(value):
    need(type(value) is str, 'CLOCK_TYPE')
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError('NO11_WEEKLY_SECURITY_CLOCK_FORMAT') from None
    need(result.utcoffset() == timedelta(hours=9), 'CLOCK_NOT_JST')
    return result


def day(value):
    need(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'DAY_FORMAT')
    return date.fromisoformat(value)


def week_bounds(session):
    current = day(session)
    monday = current - timedelta(days=current.weekday())
    return monday.isoformat(), (monday + timedelta(days=4)).isoformat()


def positive(value):
    if type(value) not in (int, float):
        return False
    try:
        n = Decimal(str(value))
        return n.is_finite() and 0 < n <= Decimal('1000000000')
    except InvalidOperation:
        return False


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, allow_nan=False,
        sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def indexed(rows):
    need(type(rows) is list and len(rows) <= 7000, 'ROWS')
    result = {}
    for row in rows:
        need(type(row) is dict and type(row.get('symbol')) is str and
             SYMBOL.fullmatch(row['symbol']) and row['symbol'] not in result,
             'SYMBOL_OR_DUPLICATE')
        result[row['symbol']] = row
    return result


def make_weekly(*, week_start, known_at, metadata_asof, rows, source_sha256):
    first = day(week_start)
    need(first.weekday() == 0, 'WEEK_START_NOT_MONDAY')
    at = instant(known_at)
    source_day = day(metadata_asof)
    need(source_day <= at.date() and 0 <= (at.date() - source_day).days <= 62,
         'METADATA_STALE_OR_FUTURE')
    # Friday/weekend pre-staging is allowed, not future fabricated observations.
    need(first - timedelta(days=3) <= at.date() <= first + timedelta(days=4),
         'REFRESH_OUTSIDE_WEEK_WINDOW')
    need(type(source_sha256) is str and SHA.fullmatch(source_sha256), 'SOURCE_SHA')
    members = indexed(rows)
    normalized = []
    for symbol, row in members.items():
        ordinary = row.get('commonEquity') is True
        normalized.append({'symbol': symbol, 'commonEquity': ordinary,
            'segment': row.get('segment'), 'sector': row.get('sector'),
            'sourceDocumentSha256': [source_sha256]})
    body = {'schemaId': WEEKLY, 'weekStart': week_start,
        'validThrough': (first + timedelta(days=4)).isoformat(),
        'knownAtJst': known_at, 'metadataAsOf': metadata_asof,
        'sourceDocumentSha256': source_sha256, 'rows': normalized,
        'refreshCadence': 'ONCE_PER_TRADING_WEEK',
        'humanDailyReviewRequired': False,
        'dailyPriceOrActionClearanceIncluded': False,
        'productionReady': False, 'orderTransmission': False}
    return dict(body, contentSha256=digest(body))


def verify_weekly(value, session, now):
    need(type(value) is dict and value.get('schemaId') == WEEKLY and
         value.get('orderTransmission') is False and value.get('productionReady') is False,
         'WEEKLY_CONTRACT')
    checksum = value.get('contentSha256')
    body = {k: v for k, v in value.items() if k != 'contentSha256'}
    need(checksum == digest(body), 'WEEKLY_HASH')
    expected_start, expected_end = week_bounds(session)
    need(value.get('weekStart') == expected_start and value.get('validThrough') == expected_end
         and expected_start <= session <= expected_end, 'WRONG_OR_EXPIRED_WEEK')
    need(instant(value['knownAtJst']) <= instant(now), 'WEEKLY_KNOWN_IN_FUTURE')
    need(0 <= (day(session) - day(value['metadataAsOf'])).days <= 62,
         'METADATA_TOO_OLD')
    return indexed(value['rows'])


def verify_changes(value, session, now):
    need(type(value) is dict and value.get('schemaId') == CHANGES and
         value.get('sessionDate') == session and value.get('readOnly') is True and
         value.get('orderTransmission') is False, 'SESSION_CHANGES_CONTRACT')
    at, observed = instant(now), instant(value.get('observedAtJst'))
    need(observed.date().isoformat() == session and
         0 <= (at - observed).total_seconds() <= 300, 'SESSION_CHANGES_STALE')
    coverage = value.get('coverage')
    need(type(coverage) is dict and set(coverage) == REQUIRED_FEEDS,
         'CHANGE_FEED_COVERAGE')
    for kind, item in coverage.items():
        need(type(item) is dict and item.get('status') == 'PARSED' and
             type(item.get('sourceSha256')) is str and SHA.fullmatch(item['sourceSha256'])
             and item.get('sourceUrl', '').startswith('https://www.jpx.co.jp/'),
             'CHANGE_FEED_UNAVAILABLE_' + kind.upper())
    rows = value.get('blocked')
    need(type(rows) is list and len(rows) <= 20000, 'CHANGE_ROWS')
    result = {}
    for row in rows:
        need(type(row) is dict and type(row.get('symbol')) is str and
             SYMBOL.fullmatch(row['symbol']) and row.get('kind') in REQUIRED_FEEDS,
             'CHANGE_ROW_INVALID')
        result.setdefault(row['symbol'], set()).add(row['kind'])
    return result


def action_date(value):
    # RSS may return a serial date through Value2, or its numeric string.
    if value is None or str(value).strip() in ('', '-', '－', '---'):
        return None
    text = str(value).strip()
    for fmt in ('%Y/%m/%d', '%Y-%m-%d', '%Y%m%d'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    try:
        serial = Decimal(text)
        if serial.is_finite() and serial == int(serial) and 30000 <= serial <= 80000:
            return date(1899, 12, 30) + timedelta(days=int(serial))
    except (ValueError, InvalidOperation, OverflowError):
        pass
    raise ValueError('NO11_WEEKLY_SECURITY_ACTION_DATE_UNKNOWN')


def admit(*, weekly, reference, changes, session, previous_session, now,
          selected, protected=()):
    at = instant(now)
    need(at.date().isoformat() == session and day(previous_session) < day(session),
         'SESSION_OR_PREVIOUS_DAY')
    need(type(selected) is list and 1 <= len(selected) <= 50 and
         len(set(selected)) == len(selected) and all(SYMBOL.fullmatch(s) for s in selected),
         'SELECTED_SCOPE')
    need(all(type(s) is str and SYMBOL.fullmatch(s) for s in protected), 'PROTECTED_SCOPE')
    metadata = verify_weekly(weekly, session, now)
    blocks = verify_changes(changes, session, now)
    need(reference.get('schemaId') == 'ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1' and
         reference.get('sessionDate') == session and reference.get('readOnly') is True and
         reference.get('orderTransmission') is False and
         reference.get('source') == 'RssMarket_SELECTED_REFERENCE_READONLY' and
         reference.get('selectedSymbols') == selected, 'REFERENCE_CONTRACT')
    begin = instant(reference.get('capturedAtJst'))
    end = instant(reference.get('completedAtJst'))
    need(begin.date().isoformat() == session and end.date().isoformat() == session and
         begin <= end <= at and (end - begin).total_seconds() < 30 and
         (at - end).total_seconds() <= 300, 'REFERENCE_STALE_OR_CLOCK')
    prices = indexed(reference.get('rows'))
    need(set(prices) == set(selected), 'REFERENCE_SCOPE')
    accepted, rejected, master_rows = [], {}, []
    for symbol in selected:
        reasons = []
        meta, quote = metadata.get(symbol), prices[symbol]
        if meta is None:
            reasons.append('NOT_IN_WEEKLY_MASTER')
        elif not (meta.get('commonEquity') is True and
                  meta.get('segment') in ('PRIME', 'STANDARD', 'GROWTH') and
                  type(meta.get('sector')) is str and bool(meta['sector'].strip())):
            reasons.append('NOT_VERIFIED_DOMESTIC_ORDINARY_EQUITY')
        if symbol in blocks:
            reasons.extend('JPX_' + kind.upper() for kind in sorted(blocks[symbol]))
        if quote.get('marketCode') != 'T' or quote.get('lotShares') != 100:
            reasons.append('MARKET_OR_LOT')
        if quote.get('marketDate') != session or quote.get('previousDate') != previous_session:
            reasons.append('RSS_SESSION_DATE')
        if meta and SEGMENTS.get(quote.get('marketSection')) != meta.get('segment'):
            reasons.append('SEGMENT_CHANGED_OR_UNKNOWN')
        if not (positive(quote.get('previousClose')) and positive(quote.get('dayBasePrice'))):
            reasons.append('PRICE_UNAVAILABLE')
        elif Decimal(str(quote['previousClose'])) != Decimal(str(quote['dayBasePrice'])):
            # Conservative: do not auto-adjust a split/ex-rights reference.
            reasons.append('PRICE_BASIS_DIFFERENCE')
        for key in ('exRightsDateRaw', 'exDividendDateRaw', 'interimExDividendDateRaw'):
            if key not in quote:
                reasons.append('ACTION_FIELD_MISSING')
                continue
            try:
                ex = action_date(quote[key])
                if ex is not None and day(previous_session) < ex <= day(session):
                    reasons.append('CURRENT_EX_DATE')
            except ValueError:
                reasons.append('ACTION_DATE_UNPARSED')
        if reasons:
            rejected[symbol] = sorted(set(reasons))
            continue
        accepted.append(symbol)
        master_rows.append({'symbol': symbol, 'asOfSession': session,
            'segment': meta['segment'], 'sector': meta['sector'],
            'rawPreviousClose': quote['previousClose'], 'commonEquity': True,
            'corporateActionsCleared': True, 'priceBasisVerified': True})
    master = {'schemaId': MASTER, 'sessionDate': session, 'knownAtJst': now,
        'rows': master_rows, 'weeklyMasterSha256': weekly['contentSha256'],
        'referenceSourceSha256': digest(reference), 'securityEvidenceSha256': digest(changes),
        'corporateActionReviewSource': BASIS,
        'independentHumanSameDayReviewPerformed': False,
        'automatedPolicyChecksPassed': True,
        'sourceCoverage': sorted(REQUIRED_FEEDS),
        'rssFieldTimestampCertified': False, 'productionReady': False,
        'orderTransmission': False}
    result = {'schemaId': ADMISSION, 'sessionDate': session, 'knownAtJst': now,
        'weeklyMasterSha256': weekly['contentSha256'],
        'requestedSymbols': selected, 'admittedEntrySymbols': accepted,
        'excludedEntrySymbols': rejected, 'protectedExitSymbols': list(protected),
        'scopeMustBeRebuiltBeforeRuntime': accepted != selected,
        'newBuyAllowed': bool(accepted), 'modelOrExitChanged': False,
        'productionReady': False, 'orderTransmission': False}
    return result, master


def load(path):
    p = Path(path)
    need(p.is_absolute() and p.is_file() and not p.is_symlink() and
         0 < p.stat().st_size <= 25000000, 'PRIVATE_INPUT')
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(root, prefix, value):
    folder = Path(root)
    need(folder.is_absolute() and folder.is_dir() and not folder.is_symlink(), 'OUTPUT')
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8')
    sha = hashlib.sha256(data).hexdigest()
    target = folder / (prefix + '-' + sha + '.json')
    need(not target.is_symlink(), 'OUTPUT_SYMLINK')
    if target.exists():
        need(target.read_bytes() == data, 'OUTPUT_CONFLICT')
    else:
        with target.open('xb') as f:
            f.write(data)
            f.flush()
    return target


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('weekly', 'reference', 'changes', 'scope', 'output'):
        p.add_argument('--' + name, required=True, type=Path)
    a = p.parse_args()
    scope = load(a.scope)
    now = datetime.now(JST).isoformat(timespec='milliseconds')
    result, master = admit(weekly=load(a.weekly), reference=load(a.reference),
        changes=load(a.changes), session=scope['sessionDate'],
        previous_session=scope['previousSession'], now=now,
        selected=scope['selectedSymbols'], protected=scope.get('protectedExitSymbols', []))
    print('NO11_WEEKLY_ADMISSION=' + str(save(a.output, 'weekly-admission', result)))
    print('NO11_AUTOMATIC_DATED_MASTER=' + str(save(a.output, 'dated-master', master)))
    print('NO11_WEEKLY_ADMITTED=' + str(len(result['admittedEntrySymbols'])))
    print('NO11_WEEKLY_EXCLUDED=' + str(len(result['excludedEntrySymbols'])))
    print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    main()
