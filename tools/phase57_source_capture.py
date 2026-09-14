"""Read an already-open dedicated Excel workbook. Never writes to Excel.

Same GetActiveObject/Range.Value2 transport as the existing Phase58 readers.
No inherited newest-row-drop/finality assumption. Only source diagnostics.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

SHEETS = {'ARK_CONFIG', 'ARK_MARKET', 'ARK_CHART_5M', 'ARK_TICKS', 'ARK_INDEX', 'ARK_HEALTH'}
FIELDS = ['slot', 'generation', 'symbol', 'sourceCode', 'sourceDate', 'sourceTime', 'open', 'high', 'low', 'close', 'volume', 'marketTimestamp', 'currentPrice', 'bestBid', 'bestAsk']
SAFETY = {k: False for k in ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted']}

def require(ok, reason):
    if not ok: raise ValueError(reason)

def validate_config(config):
    require(config.get('schemaId') == 'ARK_SOURCE_CAPTURE_CONFIG_V1', 'CONFIG_SCHEMA_MISMATCH')
    require(config.get('mode') == 'SOURCE_SEMANTICS_ONLY', 'SOURCE_ONLY_REQUIRED')
    require(config.get('safety') == SAFETY, 'SAFETY_FLAGS_REQUIRED')
    require(Path(config.get('workbookPath', '')).suffix.lower() == '.xlsx', 'DEDICATED_XLSX_REQUIRED')
    require(isinstance(config.get('workbookVersion'), str) and config['workbookVersion'], 'VERSION_REQUIRED')
    require(isinstance(config.get('sourceIdentity'), str) and config['sourceIdentity'], 'SOURCE_IDENTITY_REQUIRED')
    require(config.get('sheet') == 'ARK_CHART_5M', 'SOURCE_SHEET_REQUIRED')
    require(re.fullmatch(r'[A-Z]{1,3}[1-9][0-9]{0,3}:[A-Z]{1,3}[1-9][0-9]{0,3}', config.get('range', '')) is not None, 'BOUNDED_RANGE_REQUIRED')
    require(config.get('fields') == FIELDS, 'FIELD_MAP_MISMATCH')
    require(config.get('versionCell') == 'B1', 'VERSION_CELL_MISMATCH')

def safe_value(value):
    if value is None or isinstance(value, (str, bool, int)): return value
    if isinstance(value, float): return value if math.isfinite(value) else 'NONFINITE_CELL'
    if isinstance(value, datetime): return value.isoformat()
    return str(value)

def matrix(value):
    require(isinstance(value, (tuple, list)), 'RANGE_MATRIX_REQUIRED')
    return [[safe_value(v) for v in row] for row in value]

def read_snapshot(workbook, config):
    # Reject foreign/order sheets by NAME before reading any cells on them.
    names = [workbook.Worksheets(i).Name for i in range(1, workbook.Worksheets.Count + 1)]
    require(set(names).issubset(SHEETS) and {'ARK_CONFIG','ARK_CHART_5M'}.issubset(names), 'WRONG_OR_ORDER_ENABLED_WORKBOOK')
    require(str(workbook.FullName).casefold() == str(config['workbookPath']).casefold(), 'WRONG_WORKBOOK')
    require(workbook.HasVBProject is False, 'MACRO_WORKBOOK_FORBIDDEN')
    require(workbook.Connections.Count == 0, 'EXTERNAL_CONNECTION_FORBIDDEN')
    require(workbook.LinkSources(1) is None, 'EXTERNAL_WORKBOOK_LINK_FORBIDDEN')
    require(workbook.Names.Count == 0, 'DEFINED_NAMES_REQUIRE_REVIEW')
    for name in names:
        used = workbook.Worksheets(name).UsedRange
        require(used.Count <= 100000, 'WORKBOOK_RANGE_TOO_LARGE')
        values = used.Formula
        if not isinstance(values, (tuple, list)): values = ((values,),)
        for row in values:
            for value in row:
                if not isinstance(value, str) or not value.startswith('='): continue
                # Direct official read functions only. No IF, trigger, DDE or nested UDF.
                require(re.fullmatch(r'=\s*(?:_xlfn\.)?(?:RssChart|RssMarket|RssTickList)\([^()\r\n]*\)', value, re.I) is not None, 'FORMULA_NOT_READ_ALLOWLIST')
                require('!' not in value and '[' not in value and '|' not in value, 'EXTERNAL_FORMULA_REFERENCE')
    require(workbook.Worksheets('ARK_CONFIG').Range(config['versionCell']).Value2 == config['workbookVersion'], 'WORKBOOK_VERSION_MISMATCH')
    sheet = workbook.Worksheets(config['sheet'])
    before = matrix(sheet.Range(config['range']).Value2)
    after = matrix(sheet.Range(config['range']).Value2)
    # Equality does NOT establish atomicy/finality; keep both raw snapshots in evidence.
    return before, after

def packet_from_rows(rows, config, capture_id, timestamp, partial=False):
    result=[]
    for row in rows:
        if all(v is None or v == '' for v in row): continue
        require(len(row) == len(FIELDS), 'PARTIAL_ROW')
        record=dict(zip(FIELDS,row))
        record['cellErrors']=[field for field,v in record.items() if isinstance(v,str) and v.startswith('#')]
        result.append(record)
    return {'mode':'SOURCE_SEMANTICS_ONLY','sourceClass':'REAL_SOURCE_DIAGNOSTIC','sourceIdentity':config['sourceIdentity'],
      'workbookIdentity':config['workbookPath'],'workbookVersion':config['workbookVersion'],
      'fieldMapSha256':hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),
      'captureId':capture_id,'captureTimestamp':timestamp,'sessionDate':datetime.fromisoformat(timestamp.replace('Z','+00:00')).astimezone(timezone(timedelta(hours=9))).date().isoformat(),
      'connected':False,'workbookHealthy':True,'partialRead':partial,'rows':result,
      'error':'MSII_CONNECTION_UNVERIFIED'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=60)
    args=parser.parse_args()
    config=json.loads(args.config.read_text(encoding='utf-8-sig'));validate_config(config)
    require(1<=args.seconds<=28800,'INVALID_CAPTURE_DURATION')
    today=datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    require(today<'2026-10-22','FUTURE_OOS_LOCKED')
    import win32com.client
    # Attach only; never launch Excel, open a file, refresh, calculate, or save.
    excel=win32com.client.GetActiveObject('Excel.Application')
    args.output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();count=0
    with (args.output/'capture.jsonl').open('x',encoding='utf-8') as output, (args.output/'raw-reads.jsonl').open('x',encoding='utf-8') as raw:
        while time.monotonic()-started<args.seconds:
            stamp=datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z');count+=1
            require(datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(timezone(timedelta(hours=9))).date().isoformat() == today,'SESSION_BOUNDARY_STOP')
            try:
                matches=[excel.Workbooks(i) for i in range(1,excel.Workbooks.Count+1) if str(excel.Workbooks(i).FullName).casefold()==config['workbookPath'].casefold()]
                require(len(matches)==1,'WORKBOOK_NOT_OPEN')
                before,after=read_snapshot(matches[0],config)
                ended=datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
                raw.write(json.dumps({'captureId':str(count),'readStartedAt':stamp,'readEndedAt':ended,'before':before,'after':after},ensure_ascii=False)+'\n');raw.flush();os.fsync(raw.fileno())
                stamp=ended
                packet=packet_from_rows(after,config,str(count),stamp,before!=after)
            except Exception as error:
                packet=packet_from_rows([],config,str(count),stamp,True)
                packet.update(workbookHealthy=False,error=str(error))
            output.write(json.dumps(packet,ensure_ascii=False)+'\n');output.flush();os.fsync(output.fileno())
            time.sleep(1)
    print(json.dumps({'status':'SOURCE_CAPTURE_ONLY','captures':count,'strategyCalculated':False,'msiiConnection':'UNVERIFIED','output':str(args.output)}))

if __name__=='__main__': main()
