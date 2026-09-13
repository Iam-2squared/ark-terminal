"""Read only the dedicated, hash-pinned offline XLSX fixture; never attaches to Excel."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def inspect_fixture(file: Path, *, pin=True):
    payload = file.read_bytes()
    identity = hashlib.sha256(payload).hexdigest()
    if pin:
        expected = (ROOT / 'tools/templates/ArkParityOffline.xlsx.sha256').read_text().split()[0]
        require(identity == expected, 'UNAPPROVED_WORKBOOK_REAL_DATA_LOCKED')
    mapping = json.loads((ROOT / 'tools/phase57-parity-field-map.json').read_text(encoding='utf-8'))
    with zipfile.ZipFile(file) as z:
        require(len(z.namelist()) == len(set(z.namelist())), 'DUPLICATE_ZIP_MEMBER')
        require(sum(x.file_size for x in z.infolist()) < 20_000_000, 'WORKBOOK_TOO_LARGE')
        for name in z.namelist():
            require(not any(x in name.lower() for x in ['vbaproject', 'externallink', 'connections.xml', 'embeddings/', 'querytables/']), 'ACTIVE_WORKBOOK_CONTENT_FORBIDDEN')
            if name.endswith('.rels'):
                for relation in ET.fromstring(z.read(name)):
                    require(relation.get('TargetMode') != 'External', 'EXTERNAL_RELATION_FORBIDDEN')
            if name.startswith('xl/worksheets/') and name.endswith('.xml'):
                tree = ET.fromstring(z.read(name))
                require(not tree.findall('.//s:f', NS), 'ALL_ACTIVE_FORMULAS_FORBIDDEN')
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        relationships = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        sheets = ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet', NS)
        require([s.get('name') for s in sheets] == mapping['sheets'], 'WRONG_OR_ORDER_ENABLED_WORKBOOK')
        result = {}
        for sheet in sheets:
            target = relationships[sheet.get(REL)]
            member = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            tree = ET.fromstring(z.read(member))
            rows = []
            for row in tree.findall('s:sheetData/s:row', NS):
                cells = {}
                for c in row.findall('s:c', NS):
                    value = c.find('s:v', NS)
                    kind = c.get('t')
                    require(kind != 'e', 'RSS_CELL_ERROR')
                    if kind == 's':
                        value = shared[int(value.text)]
                    elif kind == 'inlineStr':
                        value = ''.join(c.find('s:is', NS).itertext())
                    elif value is None:
                        value = None
                    elif kind == 'b':
                        value = value.text == '1'
                    elif kind in (None, 'n'):
                        value = float(value.text)
                    else:
                        value = value.text
                    col = ''.join(ch for ch in c.get('r') if ch.isalpha())
                    idx = 0
                    for ch in col:
                        idx = idx * 26 + ord(ch) - 64
                    cells[idx-1] = value
                rows.append([cells.get(i) for i in range(max(cells, default=-1)+1)])
            result[sheet.get('name')] = rows
    config = dict(result['ARK_CONFIG'][1:])
    require(config['mode'] == 'OFFLINE_FIXTURE_ONLY' and config['realCaptureEnabled'] is False, 'REAL_CAPTURE_LOCKED')
    rows = result[mapping['chart']['sheet']]
    require(rows[0] == mapping['chart']['columns'], 'FIELD_MAP_MISMATCH')
    records = []
    for row in rows[1:]:
        require(len(row) == len(rows[0]) and all(x is not None for x in row), 'PARTIAL_EXCEL_READ')
        record = dict(zip(rows[0], row))
        for key in ('captureAt', 'availableAt'):
            value = record[key]
            require(isinstance(value, str) and value.startswith('UTC ') and value.endswith('Z'), 'EXPLICIT_UTC_TEXT_REQUIRED')
            record[key] = value[4:]
        records.append(record)
    return {'schemaId': mapping['schemaId'], 'workbookSha256': identity, 'mode': config['mode'], 'sourceClass': 'SYNTHETIC_TRANSPORT_TEST', 'bars': records}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workbook', type=Path, default=ROOT/'tools/templates/ArkParityOffline.xlsx')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    packet = inspect_fixture(args.workbook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(packet, f, ensure_ascii=False)
        f.write('\n')
    print('OFFLINE_XLSX_READ_PASS; Excel COM/MSII not contacted')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(1)
