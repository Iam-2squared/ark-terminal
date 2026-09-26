"""G input admission only: project authorized raw Daily from existing encrypted archives.
No provider call, State labels, signals, model, trading, or protected-body extraction.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
BASE = 'docs/evidence/phase57-five-minute-state-reference-v1'
CENSUS = 'docs/evidence/phase57-entry-timing-signal-census-v1/protocol.json'
SUB = 'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate'
CALENDAR = 'docs/evidence/phase57-behavior-expansion-v1/probe-v2/calendar.json'
PINS = {
    CENSUS: '6b02b3088dd8ea7f8ce53112bc276df442bae3ce0716b8139c92733be4de2994',
    SUB + '/opportunities.json.gz': '1138960e489c3403e49f502a7ff7ab1fa1e9ef205910d2d018f2bb938df813ea',
    SUB + '/source-ledger.json': '5463256720a5276a86c49043b6ceb27a0c42907a5f63354425cc251588d18e96',
}
FIELDS = ('Date', 'Code', 'O', 'H', 'L', 'C', 'Vo', 'Va', 'AdjFactor', 'ExRT')
SAFETY = {k: False for k in ('executionAllowed', 'brokerWriteAllowed',
    'excelOrderWriteAllowed', 'rssOrderFunctionAllowed', 'liveTradingAllowed',
    'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted')}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def encoded(obj):
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode()


def project_page(raw, day, codes, expected):
    if digest(raw) != expected:
        raise ValueError('RAW_DAILY_HASH_MISMATCH')
    pages = json.loads(raw)
    if not isinstance(pages, list):
        raise ValueError('PAGE_LIST_CONTRACT')
    rows, seen, page_hashes = {}, set(), []
    for page in pages:
        text = page['responseText']
        if digest(text.encode()) != page['responseSha256']:
            raise ValueError('RESPONSE_HASH_MISMATCH')
        page_hashes.append(page['responseSha256'])
        for row in json.loads(text)['data']:
            if row.get('Date') != day or row.get('Code') in seen:
                raise ValueError('DAILY_DATE_OR_DUPLICATE')
            seen.add(row['Code'])
            if row['Code'] in codes:
                z = {k: row.get(k) for k in FIELDS}
                z['sourceFieldsPresent'] = [k for k in FIELDS if k in row]
                z['sourcePageSHA256'] = page['responseSha256']
                z['sourceFileSHA256'] = expected
                z['actionScreen'] = 'FLAGGED' if (
                    row.get('AdjFactor') not in [None, 1, 1., '1', '1.0'] or
                    row.get('ExRT') not in [None, '', 0, '0']) else 'CLEAR_UNDER_SAVED_SOURCE_RULE'
                z['priceColumns'] = 'RAW_O_H_L_C_NOT_ADJUSTED_COLUMNS'
                rows[day+'|'+row['Code']] = z
    return rows, {'day': day, 'sha256': expected, 'pageSHA256': page_hashes,
                  'pageN': len(pages), 'selectedSymbolN': len(rows), 'requestedSymbolN': len(codes)}


def consume(stream, needed, allowed, pins, rows, ledger):
    stats = collections.Counter()
    with tarfile.open(fileobj=stream, mode='r|gz') as tf:
        for member in tf:
            parts = PurePosixPath(member.name).parts
            dates = [v for v in parts if len(v) == 10 and v[4] == '-' and v[7] == '-']
            if len(dates) != 1 or dates[0] not in allowed or dates[0] not in needed \
                    or not parts or parts[-1] != 'daily-pages.json':
                stats['skippedMembers'] += 1
                continue
            day = dates[0]
            if not member.isfile() or '..' in parts or member.name.startswith('/') or member.size > 100_000_000:
                raise ValueError('UNSAFE_SELECTED_TAR_MEMBER')
            if (day, 'daily') not in pins:
                raise ValueError('UNPINNED_DAILY')
            with tf.extractfile(member) as f:
                raw = f.read()
            found, item = project_page(raw, day, needed[day], pins[day, 'daily'])
            for key, value in found.items():
                if key in rows and rows[key] != value:
                    raise ValueError('CONFLICTING_SOURCE_ROW')
                rows[key] = value
            if day in ledger and ledger[day] != item:
                raise ValueError('CONFLICTING_SOURCE_FILE')
            ledger[day] = item
            stats['selectedMembers'] += 1
    return dict(stats)


def self_test():
    day = '2025-06-02'
    body = encoded({'data': [{'Date': day, 'Code': 'SYNTHETIC', 'O': 100, 'H': 101,
                             'L': 99, 'C': 100, 'Vo': 1, 'Va': 100, 'AdjFactor': 1}]})
    page = encoded([{'responseText': body.decode(), 'responseSha256': digest(body)}])
    result, _ = project_page(page, day, {'SYNTHETIC'}, digest(page))
    assert result[day+'|SYNTHETIC']['actionScreen'] == 'CLEAR_UNDER_SAVED_SOURCE_RULE'
    mem = io.BytesIO()
    with tarfile.open(fileobj=mem, mode='w:gz') as tf:
        for name, data in [('raw/'+day+'/daily-pages.json', page),
                           ('raw/2099-01-01/daily-pages.json', b'NOT_JSON_PROTECTED_PLACEHOLDER'),
                           ('raw/'+day+'/minute-pages.json', b'NOT_JSON_UNREQUESTED')]:
            item = tarfile.TarInfo(name); item.size = len(data); tf.addfile(item, io.BytesIO(data))
    mem.seek(0); rows, ledger = {}, {}
    stats = consume(mem, {day: {'SYNTHETIC'}}, {day}, {(day, 'daily'): digest(page)}, rows, ledger)
    assert stats == {'selectedMembers': 1, 'skippedMembers': 2}
    assert len(rows) == 1 and list(ledger) == [day]
    try:
        project_page(page, day, {'SYNTHETIC'}, '0'*64)
    except ValueError as exc:
        assert str(exc) == 'RAW_DAILY_HASH_MISMATCH'
    else:
        raise AssertionError('HASH_GUARD_FAILED')
    print('input projection synthetic guards PASS; no market labels')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--archives'); ap.add_argument('--output'); ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        self_test(); return
    if not args.archives or not args.output:
        ap.error('--archives and --output required')
    out = Path(args.output)
    if out.exists():
        raise ValueError('OUTPUT_EXISTS')
    for path, value in PINS.items():
        if digest((ROOT/path).read_bytes()) != value:
            raise ValueError('SOURCE_CHANGED:'+path)
    protocol = read(ROOT/CENSUS); ids = set(protocol['opportunityIds'])
    assert len(ids) == len(protocol['opportunityIds']) == 2155
    assert protocol['safety'] == SAFETY
    allowed = set(protocol['developmentSessions']); assert len(allowed) == 144
    calendar = sorted(r['Date'] for r in read(ROOT/CALENDAR)['data'] if r['HolDiv'] == '1')
    assert len(calendar) == len(set(calendar))
    opps = [o for o in read(ROOT/(SUB+'/opportunities.json.gz')) if o['id'] in ids]
    assert len(opps) == 2155 and {o['id'] for o in opps} == ids
    cohort, needed = [], collections.defaultdict(set)
    for o in sorted(opps, key=lambda o: o['id']):
        day, code, origin = o['session'], o['symbol'], o['origin']
        assert day in allowed and origin['symbol'] == code and origin['sessionDate'] == day
        ix = calendar.index(day); assert ix >= 5
        dates = calendar[ix-5:ix]
        cohort.append({'id': o['id'], 'session': day, 'symbol': code,
                       'decisionTimestamp': origin['decisionTimestamp'], 'decisionPrice': origin['decisionPrice'],
                       'previousSession': calendar[ix-1], 'dailyDates': dates})
        for d in [day]+dates:
            if d in allowed:
                needed[d].add(code)
    pins = {(z['session'], z['kind']): z['sha256'] for z in read(ROOT/(SUB+'/source-ledger.json'))}
    rows, ledger, receipts = {}, {}, []
    archives = sorted(Path(args.archives).rglob('*.tar.gz.enc'))
    if not archives:
        raise ValueError('NO_EXISTING_ARCHIVES')
    for archive in archives:
        expected = archive.with_name(archive.name+'.sha256').read_text().split()[0]
        if digest(archive.read_bytes()) != expected:
            raise ValueError('ENCRYPTED_ARCHIVE_HASH')
        proc = subprocess.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','200000',
                                 '-pass','env:JQUANTS_API_KEY','-in',str(archive)],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            stats = consume(proc.stdout, needed, allowed, pins, rows, ledger)
            while proc.stdout.read(1024*1024):
                pass
        finally:
            proc.stdout.close(); ret = proc.wait()
        if ret:
            raise ValueError('DECRYPT_FAILED_NO_SECRET_OUTPUT')
        receipts.append({'encryptedArchiveSHA256': expected, **stats})
    out.mkdir(parents=True, exist_ok=False)
    projection = {'rows': rows, 'sourceLedger': [ledger[d] for d in sorted(ledger)],
                  'requested': {d: sorted(codes) for d,codes in sorted(needed.items())},
                  'cohort': cohort, 'tradingCalendar': calendar, 'authorizedDevelopment': sorted(allowed)}
    raw = encoded(projection); (out/'daily-projection.json.gz').write_bytes(gzip.compress(raw, mtime=0))
    metadata = {'recordedAtJST': dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),
                'executionHead': os.environ.get('G_HEAD'), 'scope': 'G_INPUT_PROJECTION_ONLY',
                'cohortN': len(cohort), 'cohortIdsSHA256': digest(encoded(sorted(ids))),
                'dailyRowN': len(rows), 'readDailyDates': sorted(ledger),
                'missingDailyFiles': sorted(set(needed)-set(ledger)),
                'sourcePins': PINS, 'calendarSHA256': digest((ROOT/CALENDAR).read_bytes()),
                'receipts': receipts, 'projectionSHA256': digest((out/'daily-projection.json.gz').read_bytes()),
                'uncompressedSHA256': digest(raw), 'safety': SAFETY,
                'providerRequests': 0, 'protectedDataOpened': 0, 'stateRowsGenerated': 0,
                'secretValuesRecorded': False, 'fullRawPagesPublished': False}
    (out/'metadata.json').write_bytes(encoded(metadata))
    print(json.dumps({k:metadata[k] for k in ('scope','cohortN','dailyRowN','missingDailyFiles','providerRequests','protectedDataOpened','stateRowsGenerated')}))


if __name__ == '__main__':
    main()
