"""Read an already-open dedicated Excel workbook. Never writes to Excel.

Same GetActiveObject/Range.Value2 transport as the existing Phase58 readers.
No inherited newest-row-drop/finality assumption. Only source diagnostics.
"""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import json
import math
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from phase57_rss_raw import RAW_SHEETS, HEADERS, MARKET, layout, formulas, normalize

SHEETS = {'ARK_CONFIG', 'ARK_MARKET', 'ARK_CHART_5M', 'ARK_TICKS', 'ARK_INDEX', 'ARK_HEALTH'}
FIELDS = ['slot', 'generation', 'symbol', 'sourceCode', 'sourceDate', 'sourceTime', 'open', 'high', 'low', 'close', 'volume', 'marketTimestamp', 'currentPrice', 'bestBid', 'bestAsk']
SAFETY = {k: False for k in ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted']}

def require(ok, reason):
    if not ok: raise ValueError(reason)

def validate_config(config):
    require(config.get('schemaId') in ('ARK_SOURCE_CAPTURE_CONFIG_V1','ARK_RSS_RAW_CONFIG_V1'), 'CONFIG_SCHEMA_MISMATCH')
    require(config.get('mode') == 'SOURCE_SEMANTICS_ONLY', 'SOURCE_ONLY_REQUIRED')
    require(config.get('safety') == SAFETY, 'SAFETY_FLAGS_REQUIRED')
    require(Path(config.get('workbookPath', '')).suffix.lower() == '.xlsx', 'DEDICATED_XLSX_REQUIRED')
    require(isinstance(config.get('workbookVersion'), str) and config['workbookVersion'], 'VERSION_REQUIRED')
    require(isinstance(config.get('sourceIdentity'), str) and config['sourceIdentity'], 'SOURCE_IDENTITY_REQUIRED')
    if config['schemaId'] == 'ARK_RSS_RAW_CONFIG_V1':
        require(config.get('slots') == layout(config.get('symbols',[]),config.get('chartRows',120)), 'RAW_LAYOUT_MISMATCH')
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

def audit_names(names):
    # Exact user-observed Excel compatibility artifact; no aliases or visible names.
    require(names.Count in (0, 1), 'DEFINED_NAMES_REQUIRE_REVIEW')
    if names.Count:
        item = names.Item(1)
        require(item.Name == '_xlfn.SINGLE' and item.Visible is False
                and item.RefersTo == '=#NAME?', 'DEFINED_NAMES_REQUIRE_REVIEW')

def audit_formula_pair(value, value2):
    is_formula = lambda v: isinstance(v, str) and v.startswith('=')
    if not is_formula(value) and not is_formula(value2): return
    require(is_formula(value) and is_formula(value2), 'FORMULA_REPRESENTATION_MISMATCH')
    # Only one top-level implicit-intersection marker in Formula2 is equivalent.
    canonical2 = '=' + value2[2:] if value2.startswith('=@') else value2
    require(value == canonical2, 'FORMULA_REPRESENTATION_MISMATCH')
    require(re.fullmatch(r'=\s*(?:_xlfn\.)?(?:RssChart|RssMarket|RssTickList)\([^()\r\n]*\)', value, re.I) is not None, 'FORMULA_NOT_READ_ALLOWLIST')
    require(not any(c in value for c in ('!', '[', '|', '@')), 'EXTERNAL_FORMULA_REFERENCE')

def audit_workbook(workbook, config):
    # Reject foreign/order sheets by NAME before reading any cells on them.
    names = [workbook.Worksheets(i).Name for i in range(1, workbook.Worksheets.Count + 1)]
    require(set(names).issubset(SHEETS | (RAW_SHEETS if config['schemaId']=='ARK_RSS_RAW_CONFIG_V1' else set())) and {'ARK_CONFIG','ARK_CHART_5M'}.issubset(names), 'WRONG_OR_ORDER_ENABLED_WORKBOOK')
    require(str(workbook.FullName).casefold() == str(config['workbookPath']).casefold(), 'WRONG_WORKBOOK')
    require(workbook.HasVBProject is False, 'MACRO_WORKBOOK_FORBIDDEN')
    require(workbook.Connections.Count == 0, 'EXTERNAL_CONNECTION_FORBIDDEN')
    require(workbook.LinkSources(1) is None, 'EXTERNAL_WORKBOOK_LINK_FORBIDDEN')
    audit_names(workbook.Names)
    for name in names:
        used = workbook.Worksheets(name).UsedRange
        require(used.Count <= (300000 if name in RAW_SHEETS else 100000), 'WORKBOOK_RANGE_TOO_LARGE')
        values, values2 = used.Formula, used.Formula2
        if not isinstance(values, (tuple, list)): values = ((values,),)
        if not isinstance(values2, (tuple, list)): values2 = ((values2,),)
        require(len(values)==len(values2), 'FORMULA_REPRESENTATION_MISMATCH')
        for row, row2 in zip(values, values2):
            require(len(row)==len(row2), 'FORMULA_REPRESENTATION_MISMATCH')
            for value, value2 in zip(row, row2): audit_formula_pair(value, value2)
    require(workbook.Worksheets('ARK_CONFIG').Range(config['versionCell']).Value2 == config['workbookVersion'], 'WORKBOOK_VERSION_MISMATCH')

def read_snapshot(workbook, config, delay=0, sleep=time.sleep, on_read=None):
    def pair(reader):
        before=reader()
        if on_read: on_read('A',before)
        if delay: sleep(delay)
        after=reader()
        if on_read: on_read('B',after)
        return before,after
    audit_workbook(workbook, config)
    names={workbook.Worksheets(i).Name for i in range(1,workbook.Worksheets.Count+1)}
    if config['schemaId']=='ARK_RSS_RAW_CONFIG_V1':
        require(RAW_SHEETS.issubset(names),'RAW_SHEETS_MISSING')
        require(workbook.Date1904 is False,'DATE_SYSTEM_UNSUPPORTED')
        expected = formulas(config['slots'])
        for name in RAW_SHEETS:
            values=workbook.Worksheets(name).UsedRange.Formula
            if not isinstance(values,(tuple,list)): values=((values,),)
            actual=Counter(v for row in values for v in row if isinstance(v,str) and v.startswith('='))
            require(actual==Counter(f for (sheet,_),f in expected.items() if sheet==name),'RAW_FORMULA_SET_MISMATCH')
        for (name,cell),formula in expected.items():
            require(workbook.Worksheets(name).Range(cell).Formula == formula,'RAW_FORMULA_OR_MAPPING_CHANGED')
        require(matrix(workbook.Worksheets('ARK_RAW_MARKET').Range('A1:E1').Value2)==[MARKET], 'RAW_MARKET_HEADER_CHANGED')
        def snapshot():
            output=[]
            for slot in config['slots']:
                chart=workbook.Worksheets('ARK_RAW_CHART')
                require(matrix(chart.Range(slot['header']).Value2)==[HEADERS],'RAW_HEADER_CHANGED')
                output.append({'chartStatus':safe_value(chart.Range(slot['formulaCell']).Value2),'chart':matrix(chart.Range(slot['chart']).Value2),
                    'market':matrix(workbook.Worksheets('ARK_RAW_MARKET').Range(slot['market']).Value2)})
            return output
        return pair(snapshot)
    sheet = workbook.Worksheets(config['sheet'])
    return pair(lambda: matrix(sheet.Range(config['range']).Value2))

def read_consistent_snapshot(workbook, config, emit, attempts=3, delay=0.05, sleep=time.sleep):
    """Bounded read retries. Equality is an atomic candidate, never atomic/finality proof.
    Persist each completed read even if its peer raises; do not retry safety failures.
    """
    require(type(attempts) is int and 1<=attempts<=5 and 0<=delay<=.25,'INVALID_RETRY_POLICY')
    last_error=None
    for attempt in range(1,attempts+1):
        def record(side,value):
            emit({'attempt':attempt,'side':side,'observedAt':datetime.now(timezone.utc).isoformat(),'snapshot':value})
        try:
            before,after=read_snapshot(workbook,config,delay=delay,sleep=sleep,on_read=record)
            matched=before==after
            emit({'attempt':attempt,'atomicCandidate':matched,'atomicityProven':False})
            if matched or attempt==attempts: return before,after,matched
        except ValueError as error:
            emit({'attempt':attempt,'error':str(error),'retryable':False});raise
        except Exception as error:
            last_error=error
            emit({'attempt':attempt,'error':str(error),'retryable':True})
            if attempt<attempts: sleep(delay)
    raise RuntimeError(f'EXCEL_READ_RETRIES_EXHAUSTED: {last_error}')

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
      'connected':None,'workbookHealthy':True,'partialRead':partial,'rows':result,
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
                def emit_read(record):
                    raw.write(json.dumps({'captureId':str(count),'readStartedAt':stamp,**record},ensure_ascii=False)+'\n');raw.flush();os.fsync(raw.fileno())
                before,after,consistent=read_consistent_snapshot(matches[0],config,emit_read)
                ended=datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
                stamp=ended
                rows=normalize(after,config['slots'],today) if config['schemaId']=='ARK_RSS_RAW_CONFIG_V1' else after
                packet=packet_from_rows(rows,config,str(count),stamp,not consistent)
                if not consistent: packet['error']='INCONSISTENT_EXCEL_SNAPSHOT'
                if config['schemaId']=='ARK_RSS_RAW_CONFIG_V1' and any(str(x['chartStatus']).startswith('#') for x in after):
                    packet.update(error='RSS_CHART_FUNCTION_ERROR',workbookHealthy=False)
            except Exception as error:
                packet=packet_from_rows([],config,str(count),stamp,True)
                packet.update(workbookHealthy=False,error=str(error))
            output.write(json.dumps(packet,ensure_ascii=False)+'\n');output.flush();os.fsync(output.fileno())
            time.sleep(1)
    print(json.dumps({'status':'SOURCE_CAPTURE_ONLY','captures':count,'strategyCalculated':False,'msiiConnection':'UNVERIFIED','output':str(args.output)}))

if __name__=='__main__': main()
