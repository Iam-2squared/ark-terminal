"""Offline, evaluator-only Entry Location Study. No trading/model/EXIT imports."""
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/evidence/phase57-entry-location-study'
EVENTS = 'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz'
PATHS = 'docs/evidence/phase57-msh-entry-long-v2-development/paths.json.gz'
TRANSFER = 'docs/evidence/phase57-long-only-current-entry-transfer-v1-events.ndjson.gz'
SELECTOR = 'predict/research/phase57-long-only-frozen-selector-v1.json'
ANCHOR_SHA = '985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121'
POLICIES = ['IMMEDIATE', 'WAIT5', 'WAIT10', 'DIP_CLOSE_FALLBACK10', 'OBSERVE5_DELAY_DIP10']
LEVELS = [1, 2, 3, 5]
JST = dt.timezone(dt.timedelta(hours=9))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def read(path):
    raw = (ROOT / path).read_bytes()
    if str(path).endswith('.gz'): raw = gzip.decompress(raw)
    return [json.loads(x) for x in raw.splitlines() if x] if 'ndjson' in str(path) else json.loads(raw)


def write(path, obj):
    raw = (json.dumps(obj, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':'))+'\n').encode()
    if str(path).endswith('.gz'): raw = gzip.compress(raw, mtime=0)
    with path.open('xb') as f: f.write(raw)


def minute(stamp):
    t = dt.datetime.fromisoformat(stamp.replace('Z', '+00:00')).astimezone(JST)
    assert t.second == 0 and t.microsecond == 0
    return t.hour*60+t.minute


def quantile(values, p):
    if not values: return None
    a = sorted(values); i = (len(a)-1)*p; lo = math.floor(i); hi = math.ceil(i)
    return a[lo] + (a[hi]-a[lo])*(i-lo)


def distribution(values):
    a = [x for x in values if x is not None]
    return {'n':len(a), 'mean':statistics.mean(a) if a else None,
            **{key:quantile(a,p) for key,p in [('p05',.05),('p10',.1),('p25',.25),('median',.5),('p75',.75),('p90',.9),('p95',.95)]},
            'ES95':statistics.mean(sorted(a)[-max(1, math.ceil(.05*len(a))):]) if a else None,
            'min':min(a) if a else None, 'max':max(a) if a else None,
            'positiveRate':sum(x>0 for x in a)/len(a) if a else None,
            'negativeRate':sum(x<0 for x in a)/len(a) if a else None,
            'zeroRate':sum(x==0 for x in a)/len(a) if a else None}


def valid(bar):
    return (bar is not None and not bar['missing']
            and all(isinstance(bar.get(k),(int,float)) and not isinstance(bar[k],bool)
                    and math.isfinite(bar[k]) and bar[k]>0 for k in ('o','h','l','c')))


def absolute_path(event):
    out = {}
    for b in event['future']:
        m = minute(b['start'])
        assert m not in out and minute(b['end']) == m+5
        assert b['start'][:10] == event['sessionDate']
        row = dict(b)
        if not b['missing']:
            for key in ('o','h','l','c'): row[key] = event['decisionPrice']*(1+b[key]/100)
            assert valid(row) and row['l'] <= min(row['o'],row['c'])+1e-9 and row['h']+1e-9 >= max(row['o'],row['c'])
        out[m] = row
    return out


def segment_end(m, end):
    if 540 <= m < 690: return 690
    if 750 <= m < end: return end
    return None


def choose_delay(policy, decision_price, closed_prefix):
    """Only first completed CLOSE may select a conditional delay; no path argument."""
    if policy in POLICIES[:3]: return {'IMMEDIATE':0,'WAIT5':5,'WAIT10':10}[policy]
    if len(closed_prefix)!=1 or closed_prefix[0] is None: return None
    dip = closed_prefix[0] < decision_price
    if policy == 'DIP_CLOSE_FALLBACK10': return 5 if dip else 10
    if policy == 'OBSERVE5_DELAY_DIP10': return 10 if dip else 5
    raise ValueError('UNKNOWN_POLICY')


def entry_reference(policy, event, bars):
    m = event['entryMinute']; boundary = segment_end(m,event['sessionEndMinute'])
    if boundary is None: return {'status':'EXPIRED_BOUNDARY','delay':None,'price':None}
    first = bars.get(m)
    delay = choose_delay(policy,event['decisionPrice'],[first['c'] if valid(first) else None])
    if delay is None: return {'status':'UNKNOWN_FIRST_CLOSE','delay':None,'price':None}
    if m+delay >= boundary: return {'status':'EXPIRED_BOUNDARY','delay':delay,'price':None}
    b = bars.get(m+delay)
    if not valid(b): return {'status':'UNKNOWN_REFERENCE_OPEN','delay':delay,'price':None}
    return {'status':'REFERENCE_OPEN','delay':delay,'price':b['o']}


def window(bars, start, end, buy, allow_lunch=False):
    if buy is None: return {'status':'UNKNOWN_ENTRY','upside':None,'downside':None}
    grid = [m for m in range(start,end,5) if not allow_lunch or not 690<=m<750]
    if not grid: return {'status':'EMPTY_HORIZON','upside':None,'downside':None}
    observed = [bars[m] for m in grid if valid(bars.get(m))]
    high = max((b['h'] for b in observed),default=None)
    low = min((b['l'] for b in observed),default=None)
    complete = len(observed)==len(grid)
    up = max(0.,100*(high/buy-1)) if high is not None else None
    down = max(0.,100*(1-low/buy)) if low is not None else None
    return {'status':'COMPLETE' if complete else 'UNKNOWN_INCOMPLETE', 'expectedBars':len(grid),'observedBars':len(observed),
            'upside':up if complete else None,'downside':down if complete else None,
            'observedUpsideLowerBound':up,'observedDownsideLowerBound':down,
            'highSignedPct':100*(high/buy-1) if complete else None,
            'lowSignedPct':100*(low/buy-1) if complete else None,
            'fullUnderlyingMinuteCount':complete and all(b.get('observedMinutes')==5 for b in observed)}


def evaluate_anchor(event, segment):
    bars = absolute_path(event); m=event['entryMinute']; end=event['sessionEndMinute']
    first=bars.get(m); first_valid=valid(first) and segment_end(m,end) is not None
    primary=window(bars,m,m+60,event['decisionPrice'])['status']=='COMPLETE' and segment_end(m,end) is not None and m+60<=segment_end(m,end)
    census=window(bars,m,end,event['decisionPrice'],True)
    policies={}
    for policy in POLICIES:
        e=entry_reference(policy,event,bars); price=e['price']; start=m+(e['delay'] or 0)
        # Fixed wall-clock horizons never cross lunch or the saved regular-session boundary.
        windows={}
        for n in [5,10,15,30,60]:
            bound=segment_end(start,end)
            windows[str(n)] = window(bars,start,start+n,price) if bound is not None and start+n<=bound else {'status':'UNKNOWN_SESSION_BOUNDARY','upside':None,'downside':None}
        e.update(windows=windows,common60=window(bars,start,m+60,price) if primary else {'status':'UNKNOWN_PRIMARY_PANEL','upside':None,'downside':None},
                 savedSession=window(bars,start,end,price,True),decisionPriceShiftPct=100*(price/event['decisionPrice']-1) if price else None)
        policies[policy]=e
    immediate=policies['IMMEDIATE']
    for e in policies.values():
        e['buyImprovementPct']=100*(1-e['price']/immediate['price']) if e['price'] and immediate['price'] else None
        e['latePricePenaltyPct']=-e['buyImprovementPct'] if e['buyImprovementPct'] is not None else None
        u=immediate['common60']['upside'];v=e['common60']['upside']
        e['remainingUpsideLostPP']=u-v if u is not None and v is not None else None
    return {'eventId':event['selectorEventId'],'symbol':event['symbol'],'sessionDate':event['sessionDate'],
            'decisionTimestamp':event['decisionTimestamp'],'decisionPrice':event['decisionPrice'],
            'timeOfDay':f'{m//60:02}:{m%60:02}','segment':segment,'segmentPIT':'DATED_MASTER_RELEASE_CLOCK_UNPROVEN_DIAGNOSTIC_ONLY',
            'primary60':primary,'firstClosedDip':first['c']<event['decisionPrice'] if first_valid else None,
            'firstCloseUp1':first['c']>=event['decisionPrice']*1.01 if first_valid else None,
            'firstHighTouch3':first['h']>=event['decisionPrice']*1.03 if first_valid else None,
            'censusSavedSession':census,'policies':policies}


def capture(rows, policy, horizon='common60'):
    out={}
    for k in LEVELS:
        winners=[r for r in rows if r['policies']['IMMEDIATE'][horizon]['upside'] is not None and r['policies']['IMMEDIATE'][horizon]['upside']>=k]
        observed=[r for r in winners if r['policies'][policy][horizon]['upside'] is not None]
        hits=sum(r['policies'][policy][horizon]['upside']>=k for r in observed)
        out[str(k)]={'baseline':len(winners),'hits':hits,'unknown':len(winners)-len(observed),
                     'lower':hits/len(winners) if winners else None,'upper':(hits+len(winners)-len(observed))/len(winners) if winners else None}
    return out


def summarize(rows):
    out={'n':len(rows),'symbols':len({r['symbol'] for r in rows}),'sessions':len({r['sessionDate'] for r in rows}),'policies':{}}
    for p in POLICIES:
        rs=[r['policies'][p] for r in rows];d={}
        for key in ['buyImprovementPct','latePricePenaltyPct','decisionPriceShiftPct','remainingUpsideLostPP']:
            d[key]=distribution([r[key] for r in rs])
        d['states']=dict(collections.Counter(r['status'] for r in rs));d['capture']=capture(rows,p)
        d['windows']={str(n):{key:distribution([r['windows'][str(n)][key] for r in rs]) for key in ['upside','downside']} for n in [5,10,15,30,60]}
        d['downside30Counts']={str(k):sum(r['windows']['30']['downside'] is not None and r['windows']['30']['downside']>=k for r in rs) for k in [1,2,5,10]}
        d['common60']={key:distribution([r['common60'][key] for r in rs]) for key in ['upside','downside']}
        d['savedSession']={key:distribution([r['savedSession'].get(key) for r in rs]) for key in ['upside','downside','observedUpsideLowerBound','observedDownsideLowerBound']}
        d['savedSessionCapture']=capture(rows,p,'savedSession')
        # Paired 2D fixed bins, not an optimized ratio/target.
        cells=collections.Counter()
        for x in rs:
            u=x['windows']['30']['upside'];a=x['windows']['30']['downside']
            if u is not None and a is not None:
                cells[f'U{sum(u>=k for k in [1,2,3,5])}_D{sum(a>=k for k in [1,2,5,10])}']+=1
        d['efficiency30Joint']=dict(cells)
        paired=[]
        for r in rows:
            x=r['policies'][p]['windows']['30'];b=r['policies']['IMMEDIATE']['windows']['30']
            if all(x[k] is not None and b[k] is not None for k in ['upside','downside']):paired.append((x,b))
        d['balanceVsImmediate']={'n':len(paired),'bothNonworse':sum(x['upside']>=b['upside'] and x['downside']<=b['downside'] for x,b in paired),
            'riskBetterUpsideWorse':sum(x['downside']<b['downside'] and x['upside']<b['upside'] for x,b in paired),
            'bothWorse':sum(x['downside']>b['downside'] and x['upside']<b['upside'] for x,b in paired)}
        # Is a cheaper delayed purchase followed by another adverse excursion?
        cheaper=[x for x in rs if x['buyImprovementPct'] is not None and x['buyImprovementPct']>0]
        d['cheaperThenFurtherDown']={'nCheaper':len(cheaper),'D30':distribution([x['windows']['30']['downside'] for x in cheaper]),
             'counts':{str(k):sum(x['windows']['30']['downside'] is not None and x['windows']['30']['downside']>=k for x in cheaper) for k in [1,2,5,10]}}
        out['policies'][p]=d
    return out


def run():
    protocol=read(BASE/'protocol.json')
    for path,expected in protocol['sourcePins'].items(): assert sha(path)==expected,path
    events=read(EVENTS);paths=read(PATHS);transfer={r['selectorEventId']:r for r in read(TRANSFER)}
    first={}
    for e in sorted(events,key=lambda r:(r['decisionTimestamp'],r['symbol'])):first.setdefault((e['sessionDate'],e['symbol']),e)
    anchors=sorted(first.values(),key=lambda r:(r['decisionTimestamp'],r['symbol']))
    ids=sorted(r['selectorEventId'] for r in anchors)
    assert len(events)==3800 and len(ids)==2743 and hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest()==ANCHOR_SHA
    pm={r['selectorEventId']:r for r in paths['events']}
    assert set(pm)=={e['selectorEventId'] for e in events}
    ledger=[]
    for a in anchors:
        e=pm[a['selectorEventId']]
        assert e['decisionPrice']==a['decisionPrice'] and e['direction']=='LONG'
        ledger.append(evaluate_anchor(e,transfer[a['selectorEventId']].get('segment','UNKNOWN')))
    panel=[r for r in ledger if r['primary60']];assert len(panel)==878
    assert sum(r['firstClosedDip'] for r in panel)==328
    all60=[r for r in ledger if all(r['policies'][p]['windows']['60']['status']=='COMPLETE' for p in POLICIES)]
    allSession=[r for r in ledger if all(r['policies'][p]['savedSession']['status']=='COMPLETE' for p in POLICIES)]
    cohorts={'ALL':panel,'FIRST_CLOSED_DIP':[r for r in panel if r['firstClosedDip']],
             'NO_FIRST_CLOSED_DIP':[r for r in panel if not r['firstClosedDip']],
             'FIRST_CLOSE_UP1':[r for r in panel if r['firstCloseUp1']],
             'FIRST_HIGH_TOUCH3':[r for r in panel if r['firstHighTouch3']]}
    for k in [3,5]:cohorts['COMMON60_WINNER'+str(k)]=[r for r in panel if r['policies']['IMMEDIATE']['common60']['upside']>=k]
    cohorts['COMMON60_NON1_OBSERVED']=[r for r in panel if r['policies']['IMMEDIATE']['common60']['upside']<1]
    dates=sorted({r['sessionDate'] for r in ledger});assert len(dates)==76
    chronology={str(i+1):summarize([r for r in panel if r['sessionDate'] in dates[i*19:(i+1)*19]]) for i in range(4)}
    symbols=collections.Counter(r['symbol'] for r in panel)
    bysymbol={s:{'n':n,'wait5MeanBuy':statistics.mean(r['policies']['WAIT5']['buyImprovementPct'] for r in panel if r['symbol']==s),
                   'wait5D30Difference':statistics.mean(r['policies']['WAIT5']['windows']['30']['downside']-r['policies']['IMMEDIATE']['windows']['30']['downside'] for r in panel if r['symbol']==s)} for s,n in sorted(symbols.items())}
    top=[s for s,n in sorted(symbols.items(),key=lambda x:(-x[1],x[0]))[:3]]
    sensitivity={'removeTop1Count':summarize([r for r in panel if r['symbol'] not in top[:1]]),
                 'removeTop3Count':summarize([r for r in panel if r['symbol'] not in top]),
                 'fullUnderlying5MinuteCount':summarize([r for r in panel if r['policies']['IMMEDIATE']['common60']['fullUnderlyingMinuteCount']])}
    result={'status':'ENTRY_LOCATION_STUDY_COMPLETE','protocolSHA':sha(BASE/'protocol.json'),'anchorSHA':ANCHOR_SHA,
            'coverage':{'events':3800,'anchors':2743,'sessions':76,'primary':len(panel),'entryPlus60Paired':len(all60),'savedSessionPaired':len(allSession),
              'primaryExcluded':len(ledger)-len(panel),'dates':[dates[0],dates[-1]],
              'fullLedgerEntryStates':{p:dict(collections.Counter(r['policies'][p]['status'] for r in ledger)) for p in POLICIES},
              'fullLedgerDip':dict(collections.Counter(str(r['firstClosedDip']) for r in ledger)),
              'censusHits':{str(k):sum(r['censusSavedSession'].get('observedUpsideLowerBound') is not None and r['censusSavedSession']['observedUpsideLowerBound']>=k for r in ledger) for k in LEVELS}},
            'cohorts':{name:summarize(rs) for name,rs in cohorts.items()},
            'entryPlus60Paired':summarize(all60),'savedSessionPaired':summarize(allSession),
            'timeOfDay':{t:summarize([r for r in panel if r['timeOfDay']==t]) for t in sorted({r['timeOfDay'] for r in panel})},
            'segmentDiagnosticNotPITCertified':{s:summarize([r for r in panel if r['segment']==s]) for s in sorted({r['segment'] for r in panel})},
            'chronology':chronology,'symbolSensitivity':sensitivity,'symbols':bysymbol,'top3CountSymbols':top,
            'countHHI':sum((n/len(panel))**2 for n in symbols.values()),
            'safety':protocol['safety'],'counters':protocol['zeroCounters']}
    # Reproduce only location statistics from the old report, never EXIT net/PF gates.
    expected={'IMMEDIATE':(267,123,2.12584),'WAIT5':(192,86,2.04490),
              'DIP_CLOSE_FALLBACK10':(174,78,1.98348),'OBSERVE5_DELAY_DIP10':(186,86,2.03945)}
    for p,(n3,n5,d30) in expected.items():
        sm=result['cohorts']['ALL']['policies'][p]
        assert sm['capture']['3']['hits']==n3 and sm['capture']['5']['hits']==n5,p
        assert abs(sm['windows']['30']['downside']['mean']-d30)<.00001,p
    assert result['coverage']['censusHits']=={'1':2055,'2':1619,'3':1212,'5':609}
    write(BASE/'ledger.json.gz',ledger);write(BASE/'result.json.gz',result)
    print(json.dumps({'status':result['status'],'coverage':result['coverage'],'oldLocationParity':'PASS'}))


if __name__=='__main__':run()
