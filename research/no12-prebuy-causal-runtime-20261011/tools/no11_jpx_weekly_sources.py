#!/usr/bin/env python3
"""Public JPX sources for the weekly security policy; no private lists sent.

Metadata is cached once for its trading week. Exceptions are refreshed for
an actual session. A missing/changed table fails closed, never an empty
success. Public pages are not represented as an exhaustive issuer-disclosure
or real-time halt feed. Runtime broker/quote gates remain necessary.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from html.parser import HTMLParser
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import no11_weekly_security_policy as policy

LIST_URL = 'https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xlsx'
SOURCES = {
    'supervision': ('https://www.jpx.co.jp/listing/market-alerts/supervision/index.html', '監理'),
    'delisting': ('https://www.jpx.co.jp/listing/stocks/delisted/index.html', '上場廃止'),
    'suspension': ('https://www.jpx.co.jp/markets/equities/suspended/index.html', '売買停止'),
    'rights': ('https://www.jpx.co.jp/markets/equities/rights/index.html', '調整'),
    'transfers': ('https://www.jpx.co.jp/listing/stocks/transfers/index.html', '市場区分'),
}
HEADERS = ('日付', 'コード', '銘柄名', '市場・商品区分', '33業種コード',
           '33業種区分', '17業種コード', '17業種区分', '規模コード', '規模区分')
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
CATEGORIES = {'プライム(内国株式)': 'PRIME', 'スタンダード(内国株式)': 'STANDARD',
              'グロース(内国株式)': 'GROWTH'}


def need(ok, code):
    if not ok:
        raise ValueError('NO11_JPX_WEEKLY_' + code)


class SameHostRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        origin(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def origin(url):
    parsed = urlparse(url)
    need(parsed.scheme == 'https' and parsed.hostname == 'www.jpx.co.jp' and
         parsed.username is None and parsed.password is None and parsed.port in (None, 443),
         'PUBLIC_ORIGIN_ONLY')


def fetch(url):
    origin(url)
    request = Request(url, headers={'User-Agent': 'ArkTerminal-ReadOnly/1.0',
                                   'Accept-Encoding': 'identity'})
    with build_opener(SameHostRedirect()).open(request, timeout=15) as response:
        origin(response.url)
        need(response.status == 200, 'HTTP_STATUS')
        data = response.read(15000001)
    need(100 <= len(data) <= 15000000, 'HTTP_SIZE')
    return data


def retain(folder, raw, extension='.source'):
    sha = hashlib.sha256(raw).hexdigest()
    path = folder / (sha + extension)
    need(not path.is_symlink(), 'SOURCE_SYMLINK')
    if path.exists():
        need(path.read_bytes() == raw, 'SOURCE_CONFLICT')
    else:
        with path.open('xb') as f:
            f.write(raw)
            f.flush()
    return sha


def parse_workbook(raw):
    need(raw[:4] == b'PK\x03\x04', 'NOT_XLSX')
    with ZipFile(BytesIO(raw)) as z:
        infos = z.infolist()
        need(3 <= len(infos) <= 300 and sum(x.file_size for x in infos) <= 50000000
             and all(x.file_size <= 20000000 for x in infos), 'ZIP_LIMIT')
        names = set(z.namelist())
        need(all(not n.startswith('/') and '..' not in n.split('/') and '\\' not in n
                 for n in names), 'UNSAFE_ZIP')
        need(not any('vba' in n.lower() or 'externallinks/' in n.lower() or
                     'embeddings/' in n.lower() for n in names), 'XLSX_ACTIVE_CONTENT')
        shared = []
        if 'xl/sharedStrings.xml' in names:
            tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
            shared = [''.join(t.text or '' for t in si.iter(NS + 't'))
                      for si in tree.findall(NS + 'si')]
        need(len(shared) < 100000, 'SHARED_STRING_LIMIT')
        tree = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    sheet = tree.find(NS + 'sheetData')
    need(sheet is not None, 'SHEET_DATA_MISSING')
    rows = []
    for row in sheet.findall(NS + 'row'):
        need(len(rows) < 7000, 'ROW_LIMIT')
        cells = {}
        for cell in row.findall(NS + 'c'):
            match = re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]*)', cell.get('r', ''))
            need(match is not None, 'CELL_ADDRESS')
            column = 0
            for letter in match[1]:
                column = column * 26 + ord(letter) - 64
            need(column <= 50, 'COLUMN_LIMIT')
            if column > 10:
                continue
            need(column not in cells, 'DUPLICATE_CELL')
            kind = cell.get('t', 'n')
            if kind == 'inlineStr':
                text = ''.join(t.text or '' for t in cell.iter(NS + 't'))
            else:
                value = cell.find(NS + 'v')
                text = value.text if value is not None and value.text else ''
                if kind == 's':
                    idx = int(text)
                    need(0 <= idx < len(shared), 'STRING_INDEX')
                    text = shared[idx]
                else:
                    need(kind in ('n', 'str'), 'CELL_TYPE')
            cells[column] = text
        if cells:
            rows.append([cells.get(i, '') for i in range(1, 11)])
    header = next((i for i, r in enumerate(rows[:10]) if tuple(r) == HEADERS), None)
    need(header is not None and len(rows) >= 1000, 'JPX_HEADER_OR_COVERAGE')
    dates, securities, seen = set(), [], set()
    for row in rows[header + 1:]:
        asof, code, name, category, _, sector, *_ = row
        if not code and not asof:
            continue
        need(re.fullmatch(r'20[0-9]{6}', asof) and re.fullmatch(r'[0-9A-Z]{4,5}', code)
             and name and category, 'JPX_ROW')
        dates.add(datetime.strptime(asof, '%Y%m%d').date().isoformat())
        if len(code) != 4:
            continue
        symbol = code + '.T'
        need(symbol not in seen, 'DUPLICATE_SECURITY')
        seen.add(symbol)
        normalized = unicodedata.normalize('NFKC', category).replace(' ', '')
        segment = CATEGORIES.get(normalized)
        securities.append({'symbol': symbol, 'commonEquity': segment is not None,
                           'segment': segment, 'sector': sector if segment else None})
    need(len(dates) == 1 and len(securities) >= 3000, 'JPX_MONTH_OR_COUNT')
    return dates.pop(), securities


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.text = []
        self.table_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.table_depth += 1
            if self.table_depth == 1:
                self.table = []
        elif tag == 'tr' and self.table_depth == 1:
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []
        elif tag == 'br' and self.cell is not None:
            self.cell.append(' ')

    def handle_data(self, data):
        self.text.append(data)
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            if self.table is not None:
                self.table.append(self.row)
            self.row = None
        elif tag == 'table':
            if self.table_depth == 1 and self.table is not None:
                self.tables.append(self.table)
                self.table = None
                self.row = None
                self.cell = None
            self.table_depth = max(0, self.table_depth - 1)


def parse_exceptions(kind, raw):
    need(kind in SOURCES, 'SOURCE_KIND')
    text = raw.decode('utf-8-sig', errors='strict')
    parser = Tables()
    parser.feed(text)
    visible = ' '.join(parser.text)
    need(SOURCES[kind][1] in visible, 'PAGE_IDENTITY_' + kind.upper())
    result, matched = set(), 0
    for table in parser.tables:
        column = None
        for row in table:
            headers = [re.sub(r'\s+', '', x) for x in row]
            indices = [i for i, x in enumerate(headers) if x in ('コード', '銘柄コード', '証券コード')]
            if indices:
                need(len(indices) == 1, 'AMBIGUOUS_CODE_HEADER')
                column = indices[0]
                matched += 1
                continue
            if column is None or not row:
                continue
            joined = ' '.join(row)
            if any(marker in joined for marker in ('該当なし', '該当する銘柄はありません', '該当する情報はありません')):
                continue
            need(column < len(row), 'TABLE_SHAPE_' + kind.upper())
            code = row[column].strip()
            need(re.fullmatch(r'[0-9A-Z]{4,5}', code) is not None,
                 'UNPARSED_CODE_' + kind.upper())
            if len(code) == 4:
                # Conservative retention of every issue named in the current
                # page, even a future action. No guessed effective-date filter.
                result.add(code + '.T')
    if matched == 0:
        need(any(marker in visible for marker in ('該当する銘柄はありません', '現在、該当する情報はありません')),
             'TABLE_NOT_FOUND_' + kind.upper())
    return sorted(result)


def cache_root(value):
    folder = Path(value)
    need(folder.is_absolute() and not folder.is_symlink(), 'PRIVATE_CACHE_ROOT')
    for p in folder.parents:
        need(not p.is_symlink(), 'PRIVATE_CACHE_PARENT')
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def refresh_weekly(root, week_start, now, fetcher=fetch):
    root = cache_root(root)
    pointer = root / ('weekly-' + week_start + '.pointer.json')
    if pointer.exists():
        link = policy.load(pointer)
        candidate = root / link['name']
        need(candidate.parent == root and re.fullmatch(r'weekly-master-[a-f0-9]{64}\.json', candidate.name), 'CACHE_POINTER')
        raw = candidate.read_bytes()
        need(hashlib.sha256(raw).hexdigest() == link['sha256'], 'CACHE_HASH')
        record = json.loads(raw.decode('utf-8'))
        need(record.get('weekStart') == week_start and record.get('schemaId') == policy.WEEKLY,
             'CACHE_WEEK')
        return candidate
    raw = fetcher(LIST_URL)
    metadata_asof, rows = parse_workbook(raw)
    source_hash = retain(root, raw)
    value = policy.make_weekly(week_start=week_start, known_at=now,
        metadata_asof=metadata_asof, rows=rows, source_sha256=source_hash)
    destination = policy.save(root, 'weekly-master', value)
    link = {'name': destination.name, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            'orderTransmission': False}
    with pointer.open('x', encoding='utf-8') as f:
        json.dump(link, f)
        f.flush()
    return destination


def refresh_changes(root, session, now, fetcher=fetch):
    root = cache_root(root)
    need(policy.instant(now).date().isoformat() == session, 'ACTUAL_SESSION_REQUIRED')
    coverage, blocked = {}, []
    for kind, (url, _) in SOURCES.items():
        raw = fetcher(url)
        members = parse_exceptions(kind, raw)
        sha = retain(root, raw)
        coverage[kind] = {'status': 'PARSED', 'sourceUrl': url, 'sourceSha256': sha,
                          'parsedSymbolCount': len(members)}
        blocked.extend({'symbol': symbol, 'kind': kind} for symbol in members)
    value = {'schemaId': policy.CHANGES, 'sessionDate': session,
        'observedAtJst': now, 'coverage': coverage, 'blocked': blocked,
        'sourceLimitations': 'PUBLIC_PAGES_NOT_EXHAUSTIVE_ISSUER_OR_REALTIME_HALT_FEED',
        'readOnly': True, 'productionReady': False, 'orderTransmission': False}
    return policy.save(root, 'session-security-changes', value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('weekly', 'session', 'public-source-check'))
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--week-start')
    a = parser.parse_args()
    now = datetime.now(policy.JST)
    stamp = now.isoformat(timespec='milliseconds')
    root = cache_root(a.cache)
    if a.mode in ('weekly', 'public-source-check'):
        target = now.date()
        if target.weekday() >= 5 or (target.weekday() == 4 and now.hour >= 18):
            target += timedelta(days=7 - target.weekday())
        week = a.week_start or policy.week_bounds(target.isoformat())[0]
        print('NO11_WEEKLY_MASTER=' + str(refresh_weekly(root, week, stamp)))
    if a.mode in ('session', 'public-source-check'):
        print('NO11_SESSION_SECURITY_CHANGES=' + str(refresh_changes(root, now.date().isoformat(), stamp)))
    print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    main()
