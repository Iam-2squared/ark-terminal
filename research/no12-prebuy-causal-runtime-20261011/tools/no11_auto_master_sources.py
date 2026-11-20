"""Selected-only JPX source acquisition. No AI, Excel, broker or order calls.

Current TSE search supplies product/segment/sector. The latest official
ex-rights workbook is a conservative exclusion list, not a universal corporate
history certificate. Any listed near-term event is excluded; unknown source
format, old publication, or attention information cannot clear a security.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import hashlib
import io
import json
import re
import time
import unicodedata

JST = timezone(timedelta(hours=9))
INDEX = 'https://www.jpx.co.jp/listing/others/ex-rights/index.html'
SEARCH = 'https://www2.jpx.co.jp/tseHpFront/StockSearch.do?method=topsearch&topSearchStr='
SEGMENTS = {'プライム': 'PRIME', 'スタンダード': 'STANDARD', 'グロース': 'GROWTH'}
SECTORS = frozenset('水産・農林業 鉱業 建設業 食料品 繊維製品 パルプ・紙 化学 医薬品 石油・石炭製品 ゴム製品 ガラス・土石製品 鉄鋼 非鉄金属 金属製品 機械 電気機器 輸送用機器 精密機器 その他製品 電気・ガス業 陸運業 海運業 空運業 倉庫・運輸関連業 情報・通信業 卸売業 小売業 銀行業 証券、商品先物取引業 保険業 その他金融業 不動産業 サービス業'.split())
SYMBOL = re.compile(r'^[0-9A-Z]{4}\.T$')
POLICY = 'JPX_CURRENT_COMMON_EQUITY_AND_NEAR_TERM_RIGHTS_EXCLUSION_V1'


def need(ok, code):
    if not ok:
        raise ValueError('NO11_AUTO_MASTER_' + code)


def stamp():
    return datetime.now(JST).isoformat(timespec='milliseconds')


def normalized(value):
    return ''.join(unicodedata.normalize('NFKC', str(value)).split())


def source_url(url):
    p = urlsplit(url)
    need(p.scheme == 'https' and p.hostname in ('www.jpx.co.jp', 'www2.jpx.co.jp')
         and p.port in (None, 443) and not p.username and not p.password, 'OFFICIAL_SOURCE_URL')
    if p.hostname == 'www2.jpx.co.jp':
        need(p.path == '/tseHpFront/StockSearch.do', 'OFFICIAL_SEARCH_PATH')
    else:
        need(p.path.startswith('/listing/others/ex-rights/'), 'OFFICIAL_RIGHTS_PATH')
    return url


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        source_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, cache):
    source_url(url)
    opener = build_opener(OfficialRedirect())
    req = Request(url, headers={'User-Agent': 'ArkTerminal-selected-master/1.0',
                               'Cache-Control': 'no-cache'})
    with opener.open(req, timeout=25) as response:
        source_url(response.geturl())
        raw = response.read(8_000_001)
        need(0 < len(raw) <= 8_000_000, 'OFFICIAL_SOURCE_SIZE')
    sha = hashlib.sha256(raw).hexdigest()
    path = Path(cache) / (sha + '.source')
    if path.exists():
        need(path.is_file() and not path.is_symlink() and path.read_bytes() == raw,
             'CACHED_SOURCE_CHANGED')
    else:
        with path.open('xb') as stream:
            stream.write(raw)
    return raw, {'url': url, 'sha256': sha, 'capturedAtJst': stamp(), 'size': len(raw)}


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.links, self.row, self.cell = [], [], None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])

    def handle_data(self, value):
        if self.cell is not None:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.row is not None and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def parse_company(html, symbol):
    need(type(symbol) is str and SYMBOL.fullmatch(symbol), 'SYMBOL')
    parser = Tables()
    parser.feed(html)
    need(any([normalized(c) for c in r[:4]] == ['コード', '銘柄名', '市場区分', '業種分類']
             for r in parser.rows), 'JPX_COMPANY_HEADER_CHANGED')
    # JPX ordinary share code is four-character security code + zero.
    rows = [r for r in parser.rows if r and normalized(r[0]) == symbol[:4] + '0']
    if not rows:
        return {'symbol': symbol, 'eligible': False, 'reason': 'NO_CURRENT_ORDINARY_LISTING'}
    need(len(rows) == 1 and len(rows[0]) >= 6, 'JPX_COMPANY_IDENTITY_AMBIGUOUS')
    row = rows[0]
    segment, sector = normalized(row[2]), normalized(row[3])
    if segment not in SEGMENTS or sector not in SECTORS or normalized(row[5]):
        return {'symbol': symbol, 'eligible': False,
                'reason': 'NON_DOMESTIC_EQUITY_OR_LISTING_ATTENTION'}
    return {'symbol': symbol, 'eligible': True, 'segment': SEGMENTS[segment],
            'sector': sector, 'listedName': row[1], 'reason': 'CURRENT_JPX_ORDINARY_EQUITY'}


def rights_link(html, prior, target, today):
    parser = Tables()
    parser.feed(html)
    items = []
    for href in parser.links:
        url = urljoin(INDEX, href)
        match = re.search(r'/([0-9]{8})\.xls$', url)
        if match:
            source_url(url)
            day = datetime.strptime(match[1], '%Y%m%d').date()
            if day <= date.fromisoformat(today):
                items.append((day.isoformat(), url))
    need(bool(items), 'JPX_RIGHTS_INDEX_CHANGED')
    published, url = max(items)
    need(prior <= published <= today and date.fromisoformat(target) <=
         date.fromisoformat(published) + timedelta(days=12), 'JPX_RIGHTS_PUBLICATION_STALE')
    return published, url


def parse_rights_rows(sheets):
    """Parse complete tabular code column, never infer no events from bad format."""
    codes, recognised = set(), 0
    for rows in sheets:
        header = None
        for index, row in enumerate(rows[:20]):
            labels = [normalized(v) for v in row]
            matches = [i for i, v in enumerate(labels) if v in ('コード', '銘柄コード')]
            if len(matches) == 1:
                header = (index, matches[0])
                break
        if header is None:
            continue
        recognised += 1
        start, column = header
        for row in rows[start + 1:]:
            if len(row) <= column:
                continue
            value = row[column]
            if type(value) in (int, float) and float(value).is_integer():
                value = str(int(value))
            token = normalized(value)
            if not token:
                continue
            # Ignore only clearly labelled footnotes; unknown code-like cells block.
            if token.startswith(('※', '注', '備考')):
                continue
            need(re.fullmatch(r'[0-9A-Z]{4,5}', token) is not None, 'JPX_RIGHTS_CODE_FORMAT')
            if len(token) == 4:
                codes.add(token + '.T')
            elif token.endswith('0'):
                codes.add(token[:4] + '.T')
    need(recognised >= 1, 'JPX_RIGHTS_HEADER_CHANGED')
    return sorted(codes)


def parse_rights(raw):
    import xlrd
    need(raw.startswith(bytes.fromhex('D0CF11E0A1B11AE1')), 'JPX_RIGHTS_NOT_XLS')
    book = xlrd.open_workbook(file_contents=raw, on_demand=True, logfile=io.StringIO())
    try:
        need(1 <= book.nsheets <= 12, 'JPX_RIGHTS_SHEET_COUNT')
        sheets = []
        for sheet in book.sheets():
            need(sheet.nrows <= 10000 and sheet.ncols <= 80, 'JPX_RIGHTS_TABLE_SIZE')
            sheets.append([sheet.row_values(i) for i in range(sheet.nrows)])
        return parse_rights_rows(sheets)
    finally:
        book.release_resources()


def collect(symbols, prior, session, output_root, clock=stamp):
    need(1 <= len(symbols) <= 50 and len(set(symbols)) == len(symbols) and
         all(type(s) is str and SYMBOL.fullmatch(s) for s in symbols), 'SELECTED_SCOPE')
    today = clock()[:10]
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    need(not root.is_symlink() and root.is_dir(), 'SOURCE_CACHE_PATH')
    index, index_receipt = fetch(INDEX, root)
    published, url = rights_link(index.decode('utf-8-sig'), prior, session, today)
    raw, rights_receipt = fetch(url, root)
    blocked = set(parse_rights(raw))
    rows, documents = [], [index_receipt, rights_receipt]
    for symbol in symbols:
        html, receipt = fetch(SEARCH + symbol[:4], root)
        row = parse_company(html.decode('utf-8-sig'), symbol)
        row['listingSourceSha256'] = receipt['sha256']
        row['nearTermRightsEventListed'] = symbol in blocked
        if symbol in blocked:
            row.update(eligible=False, reason='JPX_NEAR_TERM_RIGHTS_EVENT_EXCLUDED')
        rows.append(row)
        documents.append(receipt)
        time.sleep(0.15)
    return {'schemaId': 'ARK_NO11_AUTOMATIC_SELECTED_PUBLIC_SOURCES_V1',
            'sessionDate': session, 'previousSession': prior, 'observedAtJst': clock(),
            'policy': POLICY, 'rightsPublishedOn': published,
            'rightsExclusionScope': 'ALL_EVENTS_IN_LATEST_PUBLISHED_NEAR_TERM_LIST',
            'selectedSymbols': symbols, 'rows': rows, 'documents': documents,
            'aiUsed': False, 'humanReviewFabricated': False,
            'sourceIsNotOrderApproval': True, 'productionReady': False,
            'orderTransmission': False}
