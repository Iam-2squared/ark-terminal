#!/usr/bin/env python3
"""2026 RSS observed PRICE opportunity audit (not native Frozen trading).

Post-decision High/Low is evaluator-only and NEVER used in the decision-price
input file. Missing future bars yield UNKNOWN, never a false negative. The
5M proxy cannot certify historical known-at, L0/L1, First Entry, or H2/H3/H5.
No broker, Excel, network, Frozen model fit, or order path.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from math import isfinite
from pathlib import Path
import re
import sys
from uuid import uuid4

sys.dont_write_bytecode=True
SOURCE_RECEIPT_SHA='731a5095e605ad17bf9b6e5f128ac912d6cd7dfe3cec5a3e38cdb4068ee75df8'
MASTER_SHA='22d31026c76dd1a555a2deed2d2b5743004687a239dcc8856b5abeae47782056'
SOURCE_SCHEMA='ARK_NO11_2026_RSS_FROZEN_SELECTOR_SOURCE_GAP_AUDIT_V1'
BAR_SCHEMA='ARK_NO11_2026_RSS_5M_SOURCE_PROXY_NOT_FROZEN_SELECTOR_V1'
REPORT_SCHEMA='ARK_NO11_RSS_2026_OBSERVED_PRICE_ONLY_OUTCOMES_V1'
BARS=337023
ANCHORS=59712
DAYS=('2026-10-01','2026-10-02','2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09','2026-10-13')
CLOCKS=('09:30','10:00','10:30','11:00','11:30','13:00','13:30','14:00','14:30','15:00')
STARTS=tuple(range(540,690,5))+tuple(range(750,925,5))
MISSING=('segmentStandard','segmentGrowth','liquidityLow','liquidityHigh','sectorBreadthPositivePct')
LEVELS=(2,3,5)
MAX_GZIP=256*1024*1024


def ensure(ok,msg):
    if not ok:raise RuntimeError(msg)


def verify_file(p,cap):
    ensure(p.is_file() and not p.is_symlink() and 0<p.stat().st_size<=cap,
           'NO11_PRICE_ONLY_UNSAFE_INPUT:'+p.name)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(1048576),b''):h.update(data)
    return h.hexdigest()


def tick(value):
    ensure(isinstance(value,str) and re.fullmatch(r'\d\d:\d\d',value),
           'NO11_PRICE_ONLY_BAD_CLOCK')
    return int(value[:2])*60+int(value[3:])


def load_symbols(filename):
    verify_file(filename,250000)
    ensure(sha(filename)==MASTER_SHA,'NO11_PRICE_ONLY_ORIGINAL_SYMBOLS_SHA')
    lines=filename.read_text('utf-8-sig').splitlines()
    ensure(len(lines)==4327 and len(set(lines))==4327 and
           all(re.fullmatch(r'[0-9A-Z]{4}\.T',x) for x in lines),
           'NO11_PRICE_ONLY_ORIGINAL_SYMBOLS_COUNT')
    return {s:i for i,s in enumerate(lines)}


def verify_bar(row):
    ensure(row.get('schemaId')==BAR_SCHEMA and row.get('componentOneMinuteRows')==5 and
           row.get('sourceIdentity')=='MARKETSPEED_II_RSS_CHART_1M' and
           row.get('eligibleForFrozenSelectorRuntime') is False and
           row.get('vendorFiveMinuteParityCertified') is False and
           row.get('actualVendorAvailableAtCertified') is False and
           row.get('productionReady') is False and
           row.get('orderTransmission') is False,
           'NO11_PRICE_ONLY_NOT_VERIFIED_5M_BAR')
    sym,day=row['symbol'],row['session']
    ensure(day in DAYS and re.fullmatch(r'[0-9A-Z]{4}\.T',sym),
           'NO11_PRICE_ONLY_UNKNOWN_SYMBOL_OR_SESSION')
    start=tick(row['fiveMinuteWindowStart'])
    ensure(start in STARTS,'NO11_PRICE_ONLY_OUTSIDE_REGULAR')
    end=start+5
    ensure(row.get('lastSourceLabel')==f'{day}T{(end-1)//60:02d}:{(end-1)%60:02d}:00+09:00' and
           row.get('researchAssumedNotBefore')==f'{day}T{end//60:02d}:{end%60:02d}:00+09:00' and
           row.get('syntheticHistoricalAvailabilityRule')=='LAST_LABEL_PLUS_1M',
           'NO11_PRICE_ONLY_PAST_SOURCE_CLOCK_INCONSISTENT')
    o,h,l,c,v=(row.get(k) for k in ('open','high','low','close','volume'))
    ensure(all(type(x) in (float,int) and isfinite(x) for x in (o,h,l,c,v)) and
           o>0 and c>0 and l>0 and l<=min(o,c) and h>=max(o,c) and
           v>=0 and int(v)==v,'NO11_PRICE_ONLY_BAD_OHLCV')
    return sym,day,start


def blank():
    names=['priceAnchors','withFutureObserved','fullFutureWindow']
    for level in LEVELS:
        names.extend((f'highTouch{level}Observed',f'lowTouch{level}Observed',
                      f'highTouch{level}Unknown',f'lowTouch{level}Unknown'))
    return Counter({name:0 for name in names})


def evaluate_group(bars,day,clock):
    """Use bars ending at/before clock for reference, then separate future."""
    t=tick(clock)
    before=[r for r in bars if tick(r['fiveMinuteWindowStart'])+5<=t]
    last=before[-1] if before else None
    if last is None:return None,None
    known=tick(last['fiveMinuteWindowStart'])+5
    if t-known<0 or t-known>5:return None,None
    sym=last['symbol']
    key=f'{day}|{clock}|{sym}'
    price=last['close']
    asof={
      'schemaId':'ARK_NO11_2026_PRICE_ONLY_ASOF_RESEARCH_V1',
      'researchId':key,'symbol':sym,'session':day,
      'decisionClockJst':clock,'observedReferencePrice':price,
      'sourceBarWindow':last['fiveMinuteWindowStart'],
      'researchAssumedSourceClosedAt':last['researchAssumedNotBefore'],
      'observedPriceAgeMin':t-known,
      'frozenSelectorScoreAvailable':False,
      'modelReady':False,'productionReady':False,'orderTransmission':False
    }
    future=[r for r in bars if tick(r['fiveMinuteWindowStart'])>=t]
    required={minute for minute in STARTS if minute>=t}
    got={tick(r['fiveMinuteWindowStart']) for r in future}
    ensure(got<=required,'NO11_PRICE_ONLY_UNEXPECTED_FUTURE_CLOCK')
    complete=got==required
    high=max((r['high'] for r in future),default=None)
    low=min((r['low'] for r in future),default=None)
    high_hits={str(level):(
        True if high is not None and high>=price*(1+level/100)
        else False if complete else None
    ) for level in LEVELS}
    low_hits={str(level):(
        True if low is not None and low<=price*(1-level/100)
        else False if complete else None
    ) for level in LEVELS}
    evaluator={
      'schemaId':'ARK_NO11_2026_PRICE_ONLY_EVALUATOR_FUTURE_V1',
      'researchId':key,'futureComplete5mObserved':len(got),
      'futureComplete5mExpected':len(required),
      'futureWindowFullyObserved':complete,
      'observedMaxFutureHighPct':100*(high/price-1) if high is not None else None,
      'observedMinFutureLowPct':100*(low/price-1) if low is not None else None,
      'highTouchPct':high_hits,'lowTouchPct':low_hits,
      'noObservedHitWithMissingFutureMeansUnknown':True,
      'frozenH2H3H5TeacherCertified':False,
      'productionReady':False,'orderTransmission':False
    }
    return asof,evaluator


def add_stat(c,after):
    c['priceAnchors']+=1
    if after['futureComplete5mObserved']:c['withFutureObserved']+=1
    if after['futureWindowFullyObserved']:c['fullFutureWindow']+=1
    for k in LEVELS:
        tag=str(k)
        if after['highTouchPct'][tag] is True:c[f'highTouch{k}Observed']+=1
        if after['highTouchPct'][tag] is None:c[f'highTouch{k}Unknown']+=1
        if after['lowTouchPct'][tag] is True:c[f'lowTouch{k}Observed']+=1
        if after['lowTouchPct'][tag] is None:c[f'lowTouch{k}Unknown']+=1


def gzip_writer(file):
    return gzip.GzipFile(fileobj=file,filename='',mode='wb',compresslevel=6,mtime=0)


def finalize_private(temp,out,prefix):
    digest=sha(temp)
    name=f'no11-2026-{prefix}-{digest[:16]}.jsonl.gz'
    dest=out/name
    if dest.exists():
        verify_file(dest,MAX_GZIP)
        ensure(sha(dest)==digest,'NO11_PRICE_ONLY_PREEXISTING_PRIVATE_OUTPUT_DIFFERS')
    else:
        import os
        os.link(temp,dest)  # exclusive, never overwrite an archived file
    return name,digest


def main(input_receipt,source_gzip,master,out):
    verify_file(input_receipt,250000)
    ensure(sha(input_receipt)==SOURCE_RECEIPT_SHA,
           'NO11_PRICE_ONLY_RECEIPT_SHA_MISMATCH')
    report=json.loads(input_receipt.read_text('utf-8'))
    ensure(report.get('schemaId')==SOURCE_SCHEMA and
           report.get('status')=='RESEARCH_PRICE_SOURCE_PROXY_CREATED_NOT_NATIVE_SELECTOR' and
           report.get('scope')=='all4327' and
           report.get('completeProvisionalFiveMinuteRows')==BARS and
           tuple(report.get('frozenDecisionClocksJst',[]))==CLOCKS and
           tuple(report.get('nonPriceFrozenFeatureMetadataNotInRssCapture',[]))==MISSING and
           report.get('nativeSelectorRun') is False and
           report.get('nativeFirstEntryRun') is False and
           report.get('nativeState9Run') is False and
           report.get('productionReady') is False and
           report.get('orderTransmission') is False,
           'NO11_PRICE_ONLY_SOURCE_CONTRACT_CHANGED')
    verify_file(source_gzip,MAX_GZIP)
    ensure(source_gzip.name==report['fiveMinuteGzipPrivateFilename'] and
           sha(source_gzip)==report['fiveMinuteGzipSha256'],
           'NO11_PRICE_ONLY_5M_SOURCE_SHA_MISMATCH')
    symbols=load_symbols(master)
    ensure(out.is_dir() and not out.is_symlink(),
           'NO11_PRICE_ONLY_OUTPUT_DIR_INVALID')
    score={day:{clock:blank() for clock in CLOCKS} for day in DAYS}
    bars_by_day=Counter()
    count=0
    group=[]
    old=None
    position=None
    asof_temp=out/('.rss-asof-'+uuid4().hex)
    evaluator_temp=out/('.rss-eval-'+uuid4().hex)
    try:
      with asof_temp.open('xb') as fa,evaluator_temp.open('xb') as fe:
       with gzip_writer(fa) as wa,gzip_writer(fe) as we:
        def flush(batch):
            if not batch:return
            day=batch[0]['session']
            for clock in CLOCKS:
                inp,result=evaluate_group(batch,day,clock)
                if inp is None:continue
                wa.write((json.dumps(inp,separators=(',',':'),sort_keys=True,allow_nan=False)+'\n').encode())
                we.write((json.dumps(result,separators=(',',':'),sort_keys=True,allow_nan=False)+'\n').encode())
                add_stat(score[day][clock],result)
        with gzip.open(source_gzip,'rt',encoding='utf8') as stream:
            for line in stream:
                bar=json.loads(line)
                symbol,day,minute=verify_bar(bar)
                ensure(symbol in symbols,'NO11_PRICE_ONLY_UNKNOWN_MASTER_SYMBOL')
                now=(symbols[symbol],day,minute)
                ensure(position is None or now>position,
                       'NO11_PRICE_ONLY_DUPLICATE_OR_UNSORTED_SOURCE')
                key=(symbol,day)
                if old!=key:
                    flush(group)
                    group=[]
                group.append(bar)
                old=key
                position=now
                bars_by_day[day]+=1
                count+=1
                if count%50000==0:
                    print(f'NO11_PRICE_ONLY_READ={count}/{BARS}',flush=True)
        flush(group)
      ensure(count==BARS and dict(bars_by_day)==report['observedCompleteFiveMinuteRowsBySession'],
             'NO11_PRICE_ONLY_SOURCE_COUNT_MISMATCH')
      for day in DAYS:
          for clock in CLOCKS:
              ensure(score[day][clock]['priceAnchors']==
                     report['provisionalDecisionPriceAvailableSymbolsBySession'][day][clock],
                     'NO11_PRICE_ONLY_SOURCE_PRICE_PARITY:'+day+':'+clock)
      anchors=sum(v['priceAnchors'] for d in score.values() for v in d.values())
      ensure(anchors==ANCHORS,'NO11_PRICE_ONLY_ANCHOR_TOTAL_CHANGED')
      a_name,a_hash=finalize_private(asof_temp,out,'observed-asof')
      e_name,e_hash=finalize_private(evaluator_temp,out,'future-evaluator')
      summary={
        'schemaId':REPORT_SCHEMA,
        'status':'PRICE_ONLY_OBSERVED_FUTURE_NO_FROZEN_SELECTOR',
        'sourceReceiptSha256':SOURCE_RECEIPT_SHA,
        'source5mSha256':report['fiveMinuteGzipSha256'],
        'source5mRows':count,'decisionPriceAnchors':anchors,
        'byDayDecision':{d:{t:dict(score[d][t]) for t in CLOCKS} for d in DAYS},
        'asofOnlyPrivateFilename':a_name,'asofOnlySha256':a_hash,
        'futureEvaluatorPrivateFilename':e_name,'futureEvaluatorSha256':e_hash,
        'futureUnknownNeverConvertedToNegative':True,
        'terminalAuctionsNotIncludedInHighLow':True,
        'frozenSelectorRequiredOtherInputMissing':list(MISSING),
        'nativeSelectorExecuted':False,'firstEntryExecuted':False,
        'nativeState9Executed':False,'new2026FrozenH235TrainingRows':0,
        'modelFitPerformed':False,'productionReady':False,
        'orderTransmission':False
      }
      payload=(json.dumps(summary,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode()
      digest=hashlib.sha256(payload).hexdigest()
      saved=out/f'no11-2026-price-only-observability-{digest[:16]}.json'
      if saved.exists():
          verify_file(saved,100000)
          ensure(sha(saved)==digest,'NO11_PRICE_ONLY_REPORT_CHANGED')
      else:
          with saved.open('xb') as f:f.write(payload)
      print('NO11_2026_PRICE_ONLY_OBSERVABILITY=RESEARCH_PASS')
      print('NO11_2026_OBSERVED_PRICE_ANCHORS='+str(anchors))
      print('NO11_2026_PRICE_ONLY_REPORT='+str(saved))
      print('NO11_NATIVE_SELECTOR_AND_FIRST_ENTRY_EXECUTED=False')
      print('NO11_OFFICIAL_H235_2026_TRAINING_ROWS=0')
      print('ORDER_TRANSMISSION=False')
    finally:
      for temp in (asof_temp,evaluator_temp):
          if temp.exists():temp.unlink()


def offline_test():
    day=DAYS[-1]
    def bar(start,hi=100.2,lo=99.8):
        end=start+5
        return dict(schemaId=BAR_SCHEMA,sourceIdentity='MARKETSPEED_II_RSS_CHART_1M',
            componentOneMinuteRows=5,eligibleForFrozenSelectorRuntime=False,
            vendorFiveMinuteParityCertified=False,actualVendorAvailableAtCertified=False,
            productionReady=False,orderTransmission=False,
            syntheticHistoricalAvailabilityRule='LAST_LABEL_PLUS_1M',
            session=day,symbol='7203.T',
            fiveMinuteWindowStart=f'{start//60:02d}:{start%60:02d}',
            lastSourceLabel=f'{day}T{(end-1)//60:02d}:{(end-1)%60:02d}:00+09:00',
            researchAssumedNotBefore=f'{day}T{end//60:02d}:{end%60:02d}:00+09:00',
            open=100,high=hi,low=lo,close=100,volume=100)
    rows=[bar(565),bar(570,105,96)]
    for x in rows:verify_bar(x)
    past,out=evaluate_group(rows,day,'09:30')
    assert past['observedReferencePrice']==100
    assert out['highTouchPct']['5'] is True and out['lowTouchPct']['3'] is True
    assert out['futureWindowFullyObserved'] is False
    assert evaluate_group(rows,day,'10:00')==(None,None)
    future=[bar(n) for n in (895,900,905,910,915,920)]
    x,y=evaluate_group(future,day,'15:00')
    assert x and y['highTouchPct']['2'] is False and y['futureWindowFullyObserved']
    x,y=evaluate_group(future[:-1],day,'15:00')
    assert x and y['highTouchPct']['2'] is None
    print('NO11_2026_PRICE_ONLY_OFFLINE_SELFTEST=PASS')
    print('ORDER_TRANSMISSION=False')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--offline-self-test',action='store_true')
    p.add_argument('--source-receipt',type=Path)
    p.add_argument('--source-gzip',type=Path)
    p.add_argument('--original-symbols',type=Path)
    p.add_argument('--output-dir',type=Path)
    args=p.parse_args()
    try:
        if args.offline_self_test:offline_test()
        else:
            ensure(all((args.source_receipt,args.source_gzip,args.original_symbols,args.output_dir)),
                   'NO11_PRICE_ONLY_REQUIRED_ARGUMENT_MISSING')
            main(args.source_receipt,args.source_gzip,args.original_symbols,args.output_dir)
    except Exception as e:
        print('NO11_2026_PRICE_ONLY_OBSERVABILITY=BLOCKED:'+str(e),file=sys.stderr)
        print('NO11_PRODUCTION_READY=False',file=sys.stderr)
        print('ORDER_TRANSMISSION=False',file=sys.stderr)
        sys.exit(2)
