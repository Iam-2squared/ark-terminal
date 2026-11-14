#!/usr/bin/env python3
"""Validate existing genuine 2026-11-02 24-stock RSS receipt against yesterday's
pinned handoff and save an UNREVIEWED field worklist. No Excel, RSS formulas,
broker, master creation, review attestation, cash or order authorization.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys

SESSION = '2026-11-02'
PREVIOUS = '2026-10-30'
EXPECTED = frozenset((
    '3753.T','4478.T','2002.T','8163.T','5273.T','2810.T',
    '1914.T','7678.T','9245.T','2705.T','9900.T','7581.T',
    '4733.T','8070.T','2004.T','4502.T','4565.T','4544.T',
    '7083.T','6532.T','7821.T','219A.T','8923.T','3023.T',
))
SECTIONS = {'東証P','東証Ｐ','東証S','東証Ｓ','東証G','東証Ｇ'}

def require(ok: bool, code: str):
    if not ok:
        raise ValueError('NO11_NOV02_SAVED_REFERENCE_' + code)

def source(path: Path, prefix: str):
    require(path.is_absolute() and path.is_file(), 'SOURCE_MISSING')
    require(not path.is_symlink() and not any(x.is_symlink() for x in path.parents),
            'UNSAFE_SOURCE_PATH')
    raw = path.read_bytes()
    require(200 <= len(raw) <= 1_000_000, 'SOURCE_SIZE')
    sha = hashlib.sha256(raw).hexdigest()
    require(path.name == f'{prefix}-{sha}.json', 'SOURCE_HASH_NAME_MISMATCH')
    obj = json.loads(raw.decode('utf-8-sig'))
    require(type(obj) is dict, 'SOURCE_NOT_OBJECT')
    return obj, sha

def instant(s):
    require(type(s) is str, 'MISSING_CAPTURE_CLOCK')
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        raise ValueError('NO11_NOV02_SAVED_REFERENCE_CAPTURE_CLOCK_INVALID') from None
    require(d.tzinfo is not None and d.utcoffset() == timedelta(hours=9),
            'CAPTURE_CLOCK_NOT_JST')
    return d

def positive(value):
    return (type(value) in (int,float) and math.isfinite(value)
            and 0 < value <= 1_000_000_000)

def verify(handoff, rss):
    require(handoff.get('schemaId') == 'ARK_NO11_NOV02_SOURCE_ONLY_HANDOFF_V1'
            and handoff.get('sessionDate') == SESSION
            and handoff.get('previousSession') == PREVIOUS
            and handoff.get('capturedMinuteArchiveCount') == 24
            and handoff.get('tradingAuthorized') is False
            and handoff.get('orderTransmission') is False,
            'PINNED_HANDOFF_INVALID')
    symbols = handoff.get('selectedSymbols')
    require(type(symbols) is list and len(symbols) == 24
            and len(set(symbols)) == 24 and set(symbols) == EXPECTED,
            'PINNED_24_CHANGED')
    require(rss.get('schemaId') == 'ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1'
            and rss.get('source') == 'RssMarket_SELECTED_REFERENCE_READONLY'
            and rss.get('sessionDate') == SESSION
            and rss.get('chartPlanSha256') == handoff.get('chartPlanSha256')
            and rss.get('selectedSymbols') == symbols
            and rss.get('readOnly') is True
            and rss.get('productionReady') is False
            and rss.get('orderTransmission') is False,
            'GENUINE_RSS_RECEIPT_NOT_MATCHED')
    t0,t1=instant(rss.get('capturedAtJst')),instant(rss.get('completedAtJst'))
    require(t0.date().isoformat() == SESSION and
            0 <= (t1-t0).total_seconds() < 30 and t1.date().isoformat() == SESSION,
            'CAPTURE_CLOCK_OR_DURATION')
    rows = rss.get('rows')
    require(type(rows) is list and len(rows)==24
            and all(type(r) is dict and r.get('symbol') == symbols[i]
                    for i,r in enumerate(rows)),
            'ACTUAL_24_ROWS_MISMATCH')
    worklist=[]
    for r in rows:
        ok = (r.get('marketCode')=='T' and
              r.get('marketDate')==SESSION and
              r.get('previousDate')==PREVIOUS and
              r.get('marketSection') in SECTIONS and
              r.get('lotShares')==100 and
              positive(r.get('previousClose')) and
              positive(r.get('dayBasePrice')))
        worklist.append({
            'Symbol':r['symbol'],
            'RssFields':'OBSERVED_NOT_INDEPENDENTLY_REVIEWED' if ok
                else 'MISSING_OR_DIFFERENT',
            'PreviousClose':str(r.get('previousClose')),
            'DayBasePrice':str(r.get('dayBasePrice')),
            'MarketSection':str(r.get('marketSection')),
            'LotShares':str(r.get('lotShares')),
            'ExRightsRaw':str(r.get('exRightsDateRaw','')),
            'ExDividendRaw':str(r.get('exDividendDateRaw','')),
            'CorporateActionsCleared':'NOT_REVIEWED',
            'PriceBasisVerified':'NOT_REVIEWED',
            'CommonEquitySameDay':'NOT_REVIEWED',
        })
    return worklist

def write_output(dest:Path,obj:dict):
    require(dest.is_absolute() and dest.is_dir()
            and not dest.is_symlink()
            and not any(x.is_symlink() for x in dest.parents),
            'OUTPUT_DIRECTORY_MISSING_OR_UNSAFE')
    raw = (json.dumps(obj,ensure_ascii=False,allow_nan=False,
                      separators=(',',':'))+'\n').encode('utf-8')
    sha=hashlib.sha256(raw).hexdigest()
    path=dest / f'day-reference-unreviewed-{sha}.json'
    require(not path.is_symlink(),'OUTPUT_SYMLINK')
    if path.exists():
        require(path.read_bytes() == raw,'OUTPUT_COLLISION')
    else:
        with path.open('xb') as f:
            f.write(raw)
            f.flush()
    return path

def selftest():
    symbols=sorted(EXPECTED)
    handoff={'schemaId':'ARK_NO11_NOV02_SOURCE_ONLY_HANDOFF_V1',
             'sessionDate':SESSION,'previousSession':PREVIOUS,
             'capturedMinuteArchiveCount':24,'selectedSymbols':symbols,
             'chartPlanSha256':'f'*64,'orderTransmission':False,
             'tradingAuthorized':False}
    rows=[{'symbol':sym,'marketCode':'T','marketDate':SESSION,
           'previousDate':PREVIOUS,'marketSection':'東証P',
           'lotShares':100,'previousClose':1000.0,'dayBasePrice':1000.0}
          for sym in symbols]
    rss={'schemaId':'ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1',
         'source':'RssMarket_SELECTED_REFERENCE_READONLY',
         'sessionDate':SESSION,'chartPlanSha256':'f'*64,
         'selectedSymbols':symbols,'readOnly':True,
         'productionReady':False,'orderTransmission':False,'rows':rows,
         'capturedAtJst':'2026-11-02T12:25:00.000+09:00',
         'completedAtJst':'2026-11-02T12:25:05.000+09:00'}
    result=verify(handoff,rss)
    require(len(result)==24 and all(x['RssFields'] ==
            'OBSERVED_NOT_INDEPENDENTLY_REVIEWED' for x in result),
            'SELFTEST_VERIFIED_24')
    rows[5]['previousDate']='2026-10-29'
    result=verify(handoff,rss)
    require(result[5]['RssFields']=='MISSING_OR_DIFFERENT',
            'SELFTEST_REJECTED_BROKEN_DATE')
    rss['orderTransmission']=True
    try: verify(handoff,rss)
    except ValueError: pass
    else: raise ValueError('NO11_NOV02_SAVED_REFERENCE_SELFTEST_ORDER_ON_ACCEPTED')
    print('NO11_NOV02_SAVED_REFERENCE_OFFLINE_SELFTEST=PASS')
    print('ORDER_TRANSMISSION=False')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--offline-selftest',action='store_true')
    p.add_argument('--reference',type=Path)
    p.add_argument('--handoff',type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.offline_selftest:
        selftest()
        return
    require(all((a.reference,a.handoff,a.output)),'ARGUMENTS_REQUIRED')
    today=datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    require(today==SESSION,'ACTUAL_SESSION_ONLY')
    handoff,h_sha=source(a.handoff,'morning-handoff')
    rss,r_sha=source(a.reference,'session-reference')
    rows=verify(handoff,rss)
    count=sum(r['RssFields']=='OBSERVED_NOT_INDEPENDENTLY_REVIEWED' for r in rows)
    obj={'schemaId':'ARK_NO11_NOV02_RSS_REFERENCE_WORKLIST_UNREVIEWED_V1',
         'sessionDate':SESSION,'chartPlanSha256':handoff['chartPlanSha256'],
         'rssReferenceFile':str(a.reference),'rssReferenceSha256':r_sha,
         'sourceHandoffSha256':h_sha,'selectedCount':24,
         'fieldsObservedCount':count,
         'missingOrDifferentCount':24-count,
         'independentSecurityReviewPerformed':False,
         'datedMasterCreated':False,
         'productionReady':False,'orderTransmission':False,'rows':rows}
    target=write_output(a.output,obj)
    print('NO11_NOV02_REFERENCE_SAVED_HASH_AND_SCOPE=PASS')
    print('NO11_NOV02_REFERENCE_ROWS=24')
    print(f'NO11_NOV02_RSS_FIELDS_OBSERVED={count}')
    print(f'NO11_NOV02_RSS_FIELDS_MISSING_OR_DIFFERENT={24-count}')
    print('NO11_NOV02_RSS_REVIEW_WORKLIST='+str(target))
    print('NO11_NOV02_RSS_SECURITY_REVIEW=NOT_INDEPENDENTLY_CLEARED')
    print('ORDER_TRANSMISSION=False')

if __name__ == '__main__':
    try: main()
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
        msg=str(exc)
        if not re.fullmatch('NO11_NOV02_SAVED_REFERENCE_[A-Z0-9_]+',msg):
            msg='NO11_NOV02_SAVED_REFERENCE_UNVERIFIED_PRIVATE_SOURCE'
        print('NO11_NOV02_SAVED_REFERENCE=BLOCKED|'+msg,file=sys.stderr)
        print('ORDER_TRANSMISSION=False')
        raise SystemExit(2)
