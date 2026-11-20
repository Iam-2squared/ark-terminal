"""Independent source projection and vector/event recalculation, one use only.

Never imports anatomy.py or its row outputs. Recomputes from frozen Entry and
allowlisted source path values, then compares the saved summaries.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

DIR = Path(__file__).resolve().parent
REPO = DIR.parents[3]
MS = (0.5, 1, 2, 3, 5, 7, 10)
NEXT = {1:(2,3,5,10),2:(3,5,10),3:(5,7,10),5:(7,10),7:(10,)}
FLOOR = {1:0,2:1.5,3:2.5}
SCHEDULE = tuple(range(540,690))+tuple(range(750,925))


def hash_file(p):
    with open(p,'rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def publish(name,data):
    p=DIR/name
    if p.exists():
        raise FileExistsError(p)
    p.write_text(json.dumps(data,sort_keys=True,ensure_ascii=False,allow_nan=False,
                            separators=(',',':'))+'\n')


def get_inputs():
    manifest=json.loads((DIR/'SOURCE_MANIFEST.json').read_text())
    pins=manifest['pins']
    for name,pin in pins.items():
        p=REPO/pin['path']
        assert p.stat().st_size==pin['bytes'] and hash_file(p)==pin['sha256'],name
    allow=json.loads((REPO/pins['entryAllowlist']['path']).read_text())
    lookup=defaultdict(dict)
    with gzip.open(REPO/pins['phaseAAccounting']['path'],'rt') as stream:
        for line in stream:
            item=json.loads(line)
            if item['world']=='ALL_100':
                lookup[item['arm']][item['entryId']]=item
    for a in ('IM','R1'):
        assert set(lookup[a])==set(allow[a])
    with zipfile.ZipFile(REPO/pins['integrationZip']['path']) as z:
        funded={a:set(json.loads(gzip.decompress(z.read(
            f'{a}_V3_B_R50_A_ledger.json.gz')))['funded']) for a in ('IM','R1')}
    # Unlike the main top-level scanner, find exact serialized ID keys and decode
    # only those JSON values. No out-of-scope member is parsed or materialized.
    required={x['opportunityId'] for arm in lookup.values() for x in arm.values()}
    blob=gzip.decompress((REPO/pins['rawPath']['path']).read_bytes()).decode()
    expr=re.compile(r'"(20\d\d-\d\d-\d\d\|[A-Z0-9]+)"\s*:\s*\{')
    dec=json.JSONDecoder()
    prices={}
    for match in expr.finditer(blob):
        key=match.group(1)
        if key not in required:
            continue
        assert key not in prices,key
        obj,_=dec.raw_decode(blob,match.end()-1)
        assert isinstance(obj,dict) and isinstance(obj.get('today'),list)
        prices[key]=obj['today']
    assert set(prices)==required,(len(prices),len(required))
    return lookup,funded,prices


def valid(x,t,last=False):
    if not isinstance(x,list) or len(x)!=7 or x[0]!=t:
        return False
    if any(type(y) not in (int,float) or not math.isfinite(y) for y in x):
        return False
    _,o,h,l,c,v,value=x
    return o>0 and l>0 and l<=min(o,c)<=max(o,c)<=h and v>=0 and value>=0 and (
        not last or o==h==l==c)


def to_record(e,raw,funded,arm):
    starts=[m for m in SCHEDULE if m>=e['entryMinute']]
    vals={}; duplicate=set()
    for row in raw:
        if isinstance(row,list) and row and type(row[0])==int:
            if row[0] in vals:
                duplicate.add(row[0])
            vals[row[0]]=row
    good=all(m in vals and m not in duplicate and valid(vals[m],m) for m in starts)
    auction=930 in vals and 930 not in duplicate and valid(vals[930],930,True)
    complete=good and auction and type(e['entryPrice']) in (int,float) and e['entryPrice']>0
    if not complete:
        return {'arm':arm,'funded':funded,'complete':False}
    allbars=[vals[m] for m in starts]+[vals[930]]
    price=e['entryPrice']
    return {'arm':arm,'funded':funded,'complete':True,'entryId':e['entryId'],
            'high':np.array([100*(v[2]/price-1) for v in allbars]),
            'low':np.array([100*(v[3]/price-1) for v in allbars]),
            'close':np.array([100*(v[4]/price-1) for v in allbars])}


def quant(v,adverse='high'):
    if not v:
        return {'n':0,'p10':None,'p25':None,'median':None,'p75':None,
                'p90':None,'worst':None}
    q=np.quantile(np.array(v,dtype=float),[.1,.25,.5,.75,.9])
    return dict(zip(('p10','p25','median','p75','p90'),map(float,q)))|{
        'n':len(v),'worst':max(v) if adverse=='high' else min(v)}


def event_data(r):
    h,l,c=r['high'],r['low'],r['close']
    first={m:(int(np.flatnonzero(h>=m)[0]) if np.any(h>=m) else None) for m in MS}
    r['first']=first
    r['peak']=float(max(h))
    r['highTouch']={m:first[m] is not None for m in MS}
    r['closeTouch']={m:bool(np.any(c[:-1]>=m)) for m in MS}
    r['weak']={}
    for t in (-.5,-1):
        hits=np.flatnonzero(l<=t)
        i=int(hits[0]) if len(hits) else None
        o=first[1]
        before=i is not None and (o is None or i<o)
        r['weak'][t]={'reached':i is not None,'before':before,
            'same':i is not None and i==o,
            'later':{target:(before and h[i]<target and bool(np.any(h[i+1:]>=target)))
                     for target in (1,2,3,5,10)},
            'ambiguous':{target:(before and h[i]>=target) for target in (1,2,3,5,10)}}
    r['pairs']={}
    for m,targets in NEXT.items():
        anchor=first[m]
        if anchor is None:
            continue
        for t in targets:
            same=bool(h[anchor]>=t)
            future=np.flatnonzero(h[anchor+1:]>=t) if not same else []
            goal=anchor+1+int(future[0]) if len(future) else None
            end=goal if goal is not None else len(h)
            sub=l[anchor+1:end]
            minimum=float(min(sub)) if len(sub) else None
            dd=[]
            for i in range(anchor+1,end):
                dd.append(float(max(h[anchor:i])-l[i]))
            f=FLOOR.get(m)
            touches=(np.flatnonzero(l[anchor+1:]<=f)+anchor+1) if f is not None else []
            first_floor=int(touches[0]) if len(touches) else None
            if same: cross='SAME_ANCHOR_BAR_HIGHER'
            elif goal is None: cross='NO_LATER_HIGHER'
            elif first_floor is None or first_floor>goal: cross='NO_CROSS'
            elif first_floor==goal: cross='SAME_BAR_AMBIGUOUS'
            else: cross='DEFINITE_CROSS'
            r['pairs'][m,t]={'simultaneous':same,'reached':goal is not None,
                            'minimum':minimum,'giveback':max(dd) if dd else None,
                            'cross':cross}
    return r


def same(a,b):
    if a is None or b is None:
        return a is b
    if isinstance(a,(float,int)) and isinstance(b,(float,int)):
        return math.isclose(a,b,rel_tol=0,abs_tol=1e-9)
    return a==b


def compare(actual,expected,path,mismatches):
    if isinstance(expected,dict):
        if not isinstance(actual,dict):
            mismatches.append((path,'NOT_DICTIONARY'))
            return
        for k,v in expected.items():
            compare(actual.get(k),v,path+'.'+str(k),mismatches)
    elif not same(actual,expected):
        mismatches.append((path,{'saved':actual,'recalculated':expected}))


def audit():
    started=DIR/'INDEPENDENT_RUN_STARTED.json'
    if started.exists() or (DIR/'INDEPENDENT_AUDIT.json').exists():
        raise ValueError('INDEPENDENT_BUDGET_USED')
    if not (DIR/'ENTRY_HIGH_ANATOMY.json').exists():
        raise ValueError('MAIN_NOT_SAVED')
    publish('INDEPENDENT_RUN_STARTED.json',{'atJst':datetime.now(timezone(timedelta(hours=9))).isoformat(),
           'independent_anatomy_recalculation':1})
    entries,funded,prices=get_inputs()
    records=[]
    for arm in ('IM','R1'):
        for eid in sorted(entries[arm]):
            e=entries[arm][eid]
            record=to_record(e,prices[e['opportunityId']],eid in funded[arm],arm)
            records.append(event_data(record) if record['complete'] else record)
    saved={name:json.loads((DIR/name).read_text()) for name in (
        'ENTRY_HIGH_ANATOMY.json','INITIAL_WEAKNESS_ANATOMY.json',
        'MILESTONE_PULLBACK_ANATOMY.json','OPERATOR_FLOOR_DIAGNOSTIC.json')}
    mismatches=[]; samples={}
    for a in ('IM','R1'):
        for scope in ('ALL','FUNDED'):
            key=a+':'+scope
            cohort=[r for r in records if r['arm']==a and (scope=='ALL' or r['funded'])]
            full=[r for r in cohort if r['complete']]
            expected={'totalN':len(cohort),'pathKnownN':len(full),'unknownN':len(cohort)-len(full),
                      'entryHighMeanPct':float(np.mean([r['peak'] for r in full])) if full else None,
                      'entryHighMedianPct':float(np.median([r['peak'] for r in full])) if full else None,
                      'entryHighDistribution':quant([r['peak'] for r in full]),
                      'highMilestoneReached':{str(m):sum(r['highTouch'][m] for r in full) for m in MS},
                      'closeMilestoneReached':{str(m):sum(r['closeTouch'][m] for r in full) for m in MS}}
            compare(saved['ENTRY_HIGH_ANATOMY.json'][key],expected,key+'.entry',mismatches)
            for t in (-.5,-1):
                wr=[r['weak'][t] for r in full]
                before=[r for r in wr if r['before']]
                summary={'reachedN':sum(r['reached'] for r in wr),'beforePlus1N':len(before),
                         'sameBarPlus1AmbiguousN':sum(r['same'] for r in wr),
                         'laterWinnerN':{str(z):sum(r['later'][z] for r in before)
                                         for z in (1,2,3,5,10)},
                         'sameAdverseBarAmbiguousN':{str(z):sum(r['ambiguous'][z] for r in before)
                                                     for z in (1,2,3,5,10)}}
                compare(saved['INITIAL_WEAKNESS_ANATOMY.json'][key][str(t)],summary,
                        key+f'.weak.{t}',mismatches)
            for m,targets in NEXT.items():
                anchored=[r for r in full if r['first'][m] is not None]
                for t in targets:
                    ps=[r['pairs'][m,t] for r in anchored]
                    winners=[p for p in ps if p['reached']]
                    summary={'anchorReachedN':len(anchored),'laterHigherReachedN':len(winners),
                             'laterHigherNotReachedN':sum(not p['reached'] and not p['simultaneous'] for p in ps),
                             'sameAnchorBarHigherN':sum(p['simultaneous'] for p in ps),
                             'minimumReturnBeforeTarget':quant([p['minimum'] for p in winners
                                                               if p['minimum'] is not None],'low'),
                             'maxGivebackPp':quant([p['giveback'] for p in winners
                                                   if p['giveback'] is not None])}
                    compare(saved['MILESTONE_PULLBACK_ANATOMY.json'][key][str(m)][str(t)],summary,
                            key+f'.pull.{m}.{t}',mismatches)
                    if m in FLOOR:
                        floor_summary={'laterWinnerN':len(winners),
                            'definiteCrossBeforeWinnerN':sum(p['cross']=='DEFINITE_CROSS' for p in ps),
                            'sameBarOrderAmbiguousN':sum(p['cross']=='SAME_BAR_AMBIGUOUS' for p in ps),
                            'noCrossN':sum(p['cross']=='NO_CROSS' for p in ps),
                            'sameAnchorBarHigherN':sum(p['cross']=='SAME_ANCHOR_BAR_HIGHER' for p in ps)}
                        compare(saved['OPERATOR_FLOOR_DIAGNOSTIC.json'][key][str(m)]['targets'][str(t)],
                                floor_summary,key+f'.floor.{m}.{t}',mismatches)
            samples[key]={'totalN':len(cohort),'pathKnownN':len(full),
                          'entryHighMedianPct':expected['entryHighMedianPct']}
    result={'status':'PASS' if not mismatches else 'FAIL',
            'independentRecalculationN':1,'sharedInputSourceOnly':True,
            'separateParser':'exact serialized ID regex plus per-value JSONDecoder; no main code imported',
            'separateAggregation':'NumPy array first-passage and independent ordered loops',
            'sourceHash':hash_file(REPO/json.loads((DIR/'SOURCE_MANIFEST.json').read_text())['pins']['rawPath']['path']),
            'samples':samples,'mismatchN':len(mismatches),'mismatches':mismatches[:60],
            'newFit':0,'newPolicyReplay':0,'newProviderRequest':0}
    publish('INDEPENDENT_AUDIT.json',result)
    print(json.dumps({'status':result['status'],'mismatchN':len(mismatches),'samples':samples}))


if __name__=='__main__':
    audit()
