"""Convert a formula-free generic XLSX time-series envelope into frozen-main JSON."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
SHEETS = ['ARK_CONFIG', 'ARK_MASTER', 'ARK_BARS', 'ARK_HEALTH']
MASTER = ['sourceCode', 'symbol', 'sector', 'marketCode', 'productCategory', 'effectiveAt']
BARS = ['captureId', 'symbol', 'timestamp', 'availableAt', 'open', 'high', 'low', 'close', 'volume']
HEALTH = ['captureId', 'timestamp', 'connected', 'workbookHealthy', 'stale', 'rssError', 'sessionEnd']

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def _cell_index(reference):
    result = 0
    for char in ''.join(x for x in reference if x.isalpha()):
        result = result * 26 + ord(char.upper()) - 64
    return result - 1

def _sheets(file: Path):
    payload = file.read_bytes()
    require(file.suffix.lower() == '.xlsx', 'XLSX_REQUIRED')
    with zipfile.ZipFile(file) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'DUPLICATE_ZIP_MEMBER')
        require(sum(item.file_size for item in archive.infolist()) < 50_000_000, 'WORKBOOK_TOO_LARGE')
        for name in names:
            lowered = name.lower()
            require(not any(token in lowered for token in ['vbaproject', 'externallink', 'connections.xml', 'embeddings/', 'querytables/', 'pivotcache']), 'ACTIVE_WORKBOOK_CONTENT_FORBIDDEN')
            if name.endswith('.rels'):
                for relation in ET.fromstring(archive.read(name)):
                    require(relation.get('TargetMode') != 'External', 'EXTERNAL_RELATION_FORBIDDEN')
            if name.startswith('xl/worksheets/') and name.endswith('.xml'):
                require(not ET.fromstring(archive.read(name)).findall('.//s:f', NS), 'ALL_FORMULAS_FORBIDDEN')
        shared = []
        if 'xl/sharedStrings.xml' in names:
            shared = [''.join(item.itertext()) for item in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        relations = {item.get('Id'): item.get('Target') for item in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        sheet_nodes = ET.fromstring(archive.read('xl/workbook.xml')).findall('s:sheets/s:sheet', NS)
        sheet_names = [item.get('name') for item in sheet_nodes]
        require(not any(any(word in name.upper() for word in ['ORDER', 'BROKER', 'ACCOUNT']) for name in sheet_names), 'ORDER_OR_ACCOUNT_SHEET_FORBIDDEN')
        require(sheet_names == SHEETS, 'GENERIC_SHEET_CONTRACT_MISMATCH')
        result = {}
        for sheet in sheet_nodes:
            target = relations[sheet.get(REL)]
            member = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            require(member.startswith('xl/worksheets/') and '..' not in member and member in names, 'INVALID_WORKSHEET_RELATION')
            rows = []
            for row in ET.fromstring(archive.read(member)).findall('s:sheetData/s:row', NS):
                cells = {}
                for cell in row.findall('s:c', NS):
                    kind, value = cell.get('t'), cell.find('s:v', NS)
                    require(kind != 'e', 'CELL_ERROR_FORBIDDEN')
                    if kind == 's': value = shared[int(value.text)]
                    elif kind == 'inlineStr': value = ''.join(cell.find('s:is', NS).itertext())
                    elif value is None: value = None
                    elif kind == 'b': value = value.text == '1'
                    elif kind in (None, 'n'): value = float(value.text)
                    else: value = value.text
                    cells[_cell_index(cell.get('r'))] = value
                rows.append([cells.get(index) for index in range(max(cells, default=-1) + 1)])
            result[sheet.get('name')] = rows
    return payload, result

def _records(rows, columns, label):
    require(rows and rows[0] == columns, f'{label}_HEADER_MISMATCH')
    output = []
    for row in rows[1:]:
        require(len(row) == len(columns) and all(value is not None for value in row), f'{label}_PARTIAL_ROW')
        output.append(dict(zip(columns, row)))
    return output

def _timestamp(value, label):
    require(isinstance(value, str) and (value.endswith('Z') or (len(value) >= 6 and value[-6] in '+-' and value[-3] == ':')), f'{label}_EXPLICIT_TIMESTAMP_REQUIRED')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError(f'{label}_INVALID_TIMESTAMP') from error

def inspect_generic_workbook(file: Path):
    payload, sheets = _sheets(file)
    config_rows = sheets['ARK_CONFIG']
    require(config_rows and config_rows[0] == ['key', 'value'], 'CONFIG_HEADER_MISMATCH')
    config = {}
    for row in config_rows[1:]:
        require(len(row) == 2 and isinstance(row[0], str) and row[0] not in config, 'INVALID_OR_DUPLICATE_CONFIG')
        config[row[0]] = row[1]
    require(config.get('schemaId') == 'ARK_GENERIC_TIMESERIES_V1', 'CONFIG_SCHEMA_MISMATCH')
    require(config.get('mode') == 'LOCAL_SHADOW_RESEARCH_ONLY', 'MODE_NOT_SHADOW_ONLY')
    require(config.get('sourceClass') in ['SYNTHETIC_TRANSPORT_TEST', 'USED_HISTORICAL_FIXTURE'], 'REAL_SOURCE_NOT_ADMITTED')
    require(config.get('actualMarketData') is (config.get('sourceClass') == 'USED_HISTORICAL_FIXTURE'), 'SOURCE_CLASS_DATA_FLAG_MISMATCH')
    require(config.get('universeComplete') is True and config.get('masterComplete') is True, 'DECLARED_COMPLETENESS_REQUIRED')
    master = _records(sheets['ARK_MASTER'], MASTER, 'MASTER')
    bars = _records(sheets['ARK_BARS'], BARS, 'BARS')
    health = _records(sheets['ARK_HEALTH'], HEALTH, 'HEALTH')
    require(master and health, 'MASTER_AND_HEALTH_REQUIRED')
    symbols = set()
    for row in master:
        for key in MASTER: require(isinstance(row[key], str) and row[key], f'MASTER_{key}_REQUIRED')
        require(row['symbol'].endswith('.T') and len(row['symbol']) == 6, 'INVALID_SYMBOL')
        require(row['symbol'] not in symbols, 'DUPLICATE_MASTER_SYMBOL')
        symbols.add(row['symbol']); _timestamp(row['effectiveAt'], 'MASTER_EFFECTIVE_AT')
    capture_ids = set()
    last = None
    for row in health:
        require(isinstance(row['captureId'], str) and row['captureId'] not in capture_ids, 'DUPLICATE_CAPTURE_ID')
        capture_ids.add(row['captureId']); current = _timestamp(row['timestamp'], 'HEALTH_TIMESTAMP')
        require(last is None or current > last, 'NONMONOTONIC_HEALTH_TIMESTAMP'); last = current
        for key in ['connected', 'workbookHealthy', 'stale', 'rssError', 'sessionEnd']: require(isinstance(row[key], bool), f'HEALTH_{key}_BOOLEAN_REQUIRED')
    seen_bars = set()
    for row in bars:
        require(row['captureId'] in capture_ids, 'BAR_CAPTURE_ID_UNKNOWN')
        require(row['symbol'] in symbols, 'BAR_SYMBOL_NOT_IN_MASTER')
        _timestamp(row['timestamp'], 'BAR_TIMESTAMP'); _timestamp(row['availableAt'], 'BAR_AVAILABLE_AT')
        key = (row['symbol'], row['timestamp']); require(key not in seen_bars, 'DUPLICATE_SYMBOL_BAR'); seen_bars.add(key)
        for field in ['open', 'high', 'low', 'close', 'volume']: require(type(row[field]) in (int, float) and math.isfinite(row[field]), f'BAR_{field}_FINITE_REQUIRED')
        require(min(row['open'], row['low'], row['close']) > 0 and row['high'] >= max(row['open'], row['low'], row['close']) and row['low'] <= min(row['open'], row['close']) and row['volume'] >= 0, 'INVALID_OHLCV')
    member_hash = hashlib.sha256(json.dumps(sorted(symbols), separators=(',', ':')).encode()).hexdigest()
    points = []
    for status in health:
        timestamp = status['timestamp']; decision_instant = _timestamp(timestamp, 'HEALTH_TIMESTAMP')
        universe = []
        for item in master:
            prefix = [{key: row[key] for key in ['timestamp', 'availableAt', 'open', 'high', 'low', 'close', 'volume']} for row in bars if row['symbol'] == item['symbol'] and _timestamp(row['availableAt'], 'BAR_AVAILABLE_AT') <= decision_instant]
            prefix.sort(key=lambda row: row['timestamp'])
            universe.append({**item, 'bars': prefix})
        points.append({'schemaId': 'ARK_PHASE57_FROZEN_MAIN_POINT_V1', 'captureId': status['captureId'], 'sessionDate': str(config.get('sessionDate')), 'timestamp': timestamp, 'sourceClass': config['sourceClass'], 'universeComplete': config['universeComplete'], 'masterComplete': config['masterComplete'], 'memberSetSha256': member_hash, 'universe': universe, 'health': {key: status[key] for key in ['connected', 'workbookHealthy', 'stale', 'rssError']}, 'sessionEnd': status['sessionEnd']})
    return {'schemaId': 'ARK_PHASE57_FROZEN_MAIN_PACKET_V1', 'workbookSha256': hashlib.sha256(payload).hexdigest(), 'points': points, 'analogPool': []}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workbook', type=Path, required=True)
    parser.add_argument('--analog-pool', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    packet = inspect_generic_workbook(args.workbook)
    packet['analogPool'] = json.loads(args.analog_pool.read_text(encoding='utf-8'))
    require(isinstance(packet['analogPool'], list) and packet['analogPool'], 'ANALOG_POOL_REQUIRED')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(packet, stream, ensure_ascii=False, separators=(',', ':')); stream.write('\n')
    print('GENERIC_XLSX_SHADOW_PACKET_PASS; formulas, external links, order sheets and real-source modes blocked')

if __name__ == '__main__':
    try: main()
    except Exception as error:
        print(str(error), file=sys.stderr); raise SystemExit(1)
