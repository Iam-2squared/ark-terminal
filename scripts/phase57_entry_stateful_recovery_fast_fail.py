#!/usr/bin/env python3
"""One-shot Entry-only FAST-FAIL for the frozen stateful recovery contract.

Historical Development / outcome-exposed. No model, provider, EXIT, Capital,
Portfolio, 1m or trading imports. Decisions use only completed 5m prefix data.
Prints one deterministic JSON object; does not write repository files.
"""
import collections
import hashlib
import json
import statistics

from scripts import phase57_entry_location_study as loc

CONTRACT_HEAD = '710034639f269aeaacf5f0e2800b510bdc61c822'
SOURCE_HEAD = 'a0a263ddc6abd83c9dca0b9f4bc2c86b9753b2bb'
ALLOWED = {
    'STATEFUL_ENTRY_RECOVERY_FAST_FAIL_CONTINUE_NOT_VALIDATED',
    'STATEFUL_ENTRY_RECOVERY_FAST_FAIL_KILL',
    'STATEFUL_ENTRY_RECOVERY_FAST_FAIL_INCONCLUSIVE',
    'STATEFUL_ENTRY_RECOVERY_FAST_FAIL_BLOCKED',
}
SAFETY = {k: False for k in (
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed',
    'rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed',
    'automaticPromotionAllowed','productionUpdateAllowed','transmitted')}


def mean(xs):
    xs=[x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def pct_improvement(old,new):
    return 100*(old-new)/old if old not in (None,0) and new is not None else None


def first_anchors():
    events=loc.read(loc.EVENTS)
    first={}
    for e in sorted(events,key=lambda r:(r['decisionTimestamp'],r['symbol'])):
        first.setdefault((e['sessionDate'],e['symbol']),e)
    anchors=sorted(first.values(),key=lambda r:(r['decisionTimestamp'],r['symbol']))
    ids=sorted(r['selectorEventId'] for r in anchors)
    identity=hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest()
    assert len(events)==3800 and len(anchors)==2743 and identity==loc.ANCHOR_SHA
    return anchors,identity


def complete_window(bars,start,minutes,buy,end):
    bound=loc.segment_end(start,end)
    if bound is None or start+minutes>bound:
        return None
    w=loc.window(bars,start,start+minutes,buy)
    return w if w['status']=='COMPLETE' else None


def common60(bars,m,start,buy,end):
    bound=loc.segment_end(m,end)
    if bound is None or m+60>bound or start>=m+60:
        return None
    w=loc.window(bars,start,m+60,buy)
    return w if w['status']=='COMPLETE' else None


def evaluate(event):
    bars=loc.absolute_path(event);m=event['entryMinute'];end=event['sessionEndMinute']
    boundary=loc.segment_end(m,end)
    primary=(boundary is not None and m+60<=boundary and
             loc.window(bars,m,m+60,event['decisionPrice'])['status']=='COMPLETE')
    first=bars.get(m)
    if not primary or not loc.valid(first):
        return {'eventId':event['selectorEventId'],'symbol':event['symbol'],
                'sessionDate':event['sessionDate'],'primary':False,'state':'OUTSIDE_PRIMARY'}
    if not first['c'] < event['decisionPrice']:
        return {'eventId':event['selectorEventId'],'symbol':event['symbol'],
                'sessionDate':event['sessionDate'],'primary':True,'firstDip':False,
                'state':'FIRST_BAR_OBSERVED_CONTINUATION'}
    basebar=bars.get(m+5)
    second=bars.get(m+5)
    fillbar=bars.get(m+10)
    if not loc.valid(basebar):
        return {'eventId':event['selectorEventId'],'symbol':event['symbol'],
                'sessionDate':event['sessionDate'],'primary':True,'firstDip':True,
                'state':'UNKNOWN_DIP_OPEN5'}
    base_price=basebar['o']
    base30=complete_window(bars,m+5,30,base_price,end)
    base60=common60(bars,m,m+5,base_price,end)
    if not loc.valid(second):
        return {'eventId':event['selectorEventId'],'symbol':event['symbol'],
                'sessionDate':event['sessionDate'],'primary':True,'firstDip':True,
                'state':'UNKNOWN_SECOND_BAR','baseline30':base30,'baseline60':base60}
    recovery=second['c']>first['c'] and second['c']>second['o']
    if not recovery:
        return {'eventId':event['selectorEventId'],'symbol':event['symbol'],
                'sessionDate':event['sessionDate'],'primary':True,'firstDip':True,
                'state':'SECONDARY_EXPIRED','recovery':False,
                'baseline30':base30,'baseline60':base60}
    if not loc.valid(fillbar) or m+10>=boundary:
        return {'eventId':event['selectorEventId'],'symbol':event['symbol'],
                'sessionDate':event['sessionDate'],'primary':True,'firstDip':True,
                'state':'UNKNOWN_RECOVERY_OPEN','recovery':True,
                'baseline30':base30,'baseline60':base60}
    price=fillbar['o']
    return {'eventId':event['selectorEventId'],'symbol':event['symbol'],
            'sessionDate':event['sessionDate'],'primary':True,'firstDip':True,
            'state':'RECOVERY_CONFIRMED','recovery':True,
            'baselinePrice':base_price,'challengerPrice':price,
            'buyImprovementVsDip5':100*(1-price/base_price),
            'baseline30':base30,'challenger30':complete_window(bars,m+10,30,price,end),
            'baseline60':base60,'challenger60':common60(bars,m,m+10,price,end)}


def dist(rows,key):
    return loc.distribution([r[key] for r in rows if r.get(key) is not None])


def window_dist(rows,side,key):
    return loc.distribution([r[side][key] for r in rows if r.get(side) is not None and r[side].get(key) is not None])


def capture(rows,level):
    eligible=[r for r in rows if r.get('baseline60') is not None and r.get('challenger60') is not None]
    winners=[r for r in eligible if r['baseline60']['upside']>=level]
    hits=sum(r['challenger60']['upside']>=level for r in winners)
    return {'denominator':len(winners),'hits':hits,'ratio':hits/len(winners) if winners else None}


def deep(rows,side,level):
    a=[r for r in rows if r.get(side) is not None]
    n=sum(r[side]['downside']>=level for r in a)
    return {'n':len(a),'count':n,'rate':n/len(a) if a else None}


def block_metrics(rows):
    dates=sorted({r['sessionDate'] for r in rows})
    blocks=[]
    for i in range(4):
        ds=set(dates[i*19:(i+1)*19])
        rr=[r for r in rows if r['sessionDate'] in ds and r.get('baseline30') and r.get('challenger30')]
        b=mean([r['baseline30']['downside'] for r in rr]);c=mean([r['challenger30']['downside'] for r in rr])
        blocks.append({'block':i+1,'sessions':len(ds),'n':len(rr),'baselineD30':b,'challengerD30':c,
                       'nonWorse':b is not None and c is not None and c<=b})
    return blocks


def run():
    protocol=loc.read(loc.BASE/'protocol.json')
    for path,expected in protocol['sourcePins'].items():
        assert loc.sha(path)==expected,path
    anchors,anchor_sha=first_anchors();paths=loc.read(loc.PATHS)
    pm={r['selectorEventId']:r for r in paths['events']}
    assert set(pm)=={e['selectorEventId'] for e in loc.read(loc.EVENTS)}
    ledger=[evaluate(pm[a['selectorEventId']]) for a in anchors]
    primary=[r for r in ledger if r.get('primary')]
    dips=[r for r in primary if r.get('firstDip')]
    confirmed=[r for r in dips if r['state']=='RECOVERY_CONFIRMED']
    paired=[r for r in confirmed if r.get('baseline30') and r.get('challenger30') and r.get('baseline60') and r.get('challenger60')]
    b30=mean([r['baseline30']['downside'] for r in paired]);c30=mean([r['challenger30']['downside'] for r in paired])
    b60=mean([r['baseline60']['upside'] for r in paired]);c60=mean([r['challenger60']['upside'] for r in paired])
    cap3=capture(paired,3);cap5=capture(paired,5)
    d5b=deep(paired,'baseline30',5);d5c=deep(paired,'challenger30',5)
    blocks=block_metrics(paired);stable=sum(x['nonWorse'] for x in blocks)
    sufficient=(len(paired)>=30 and len({r['symbol'] for r in paired})>=20 and cap3['denominator']>=20)
    gates=None
    if sufficient:
        gates={
            'capture3':cap3['ratio'] is not None and cap3['ratio']>=.90,
            'capture5':True if cap5['denominator']<10 else cap5['ratio']>=.90,
            'meanD30':pct_improvement(b30,c30) is not None and pct_improvement(b30,c30)>=10,
            'es95':window_dist(paired,'challenger30','downside')['ES95']<=window_dist(paired,'baseline30','downside')['ES95'],
            'common60Upside':b60 is not None and c60 is not None and c60>=.90*b60,
            'deep5':d5c['rate']<=d5b['rate'],
            'chronological':stable>=3,
        }
    if not sufficient:
        verdict='STATEFUL_ENTRY_RECOVERY_FAST_FAIL_INCONCLUSIVE'
    elif all(gates.values()):
        verdict='STATEFUL_ENTRY_RECOVERY_FAST_FAIL_CONTINUE_NOT_VALIDATED'
    else:
        verdict='STATEFUL_ENTRY_RECOVERY_FAST_FAIL_KILL'
    assert verdict in ALLOWED
    result={
        'verdict':verdict,'contractHead':CONTRACT_HEAD,'sourceStudyHead':SOURCE_HEAD,
        'dataKind':'HISTORICAL_DEVELOPMENT_OUTCOME_EXPOSED','fullAnchors':len(ledger),
        'primary':len(primary),'firstClosedDip':len(dips),'recoveryConfirmed':len(confirmed),
        'paired':len(paired),'pairedSymbols':len({r['symbol'] for r in paired}),
        'states':dict(collections.Counter(r['state'] for r in ledger)),
        'rule':'after FIRST_CLOSED_DIP, second_close > first_close AND second_close > second_open; then reference next regular 5m OPEN',
        'buyImprovementVsDip5':dist(paired,'buyImprovementVsDip5'),
        'baselineDip5D30':window_dist(paired,'baseline30','downside'),
        'recoveryConfirmD30':window_dist(paired,'challenger30','downside'),
        'meanD30ImprovementPct':pct_improvement(b30,c30),
        'baselineDip5Common60Upside':window_dist(paired,'baseline60','upside'),
        'recoveryConfirmCommon60Upside':window_dist(paired,'challenger60','upside'),
        'common60UpsidePreservation':c60/b60 if b60 not in (None,0) and c60 is not None else None,
        'capture3':cap3,'capture5':cap5,'deepAdverse5Baseline':d5b,'deepAdverse5Challenger':d5c,
        'chronological':blocks,'chronologicalNonWorse':stable,'gates':gates,
        'candidateAccepted':False,'modelFits':0,'modelPredictions':0,'freshAccess':0,'oosAccess':0,
        'providerRequests':0,'minuteResearchRuns':0,'exitEvaluations':0,'capitalEvaluations':0,
        'portfolioEvaluations':0,'mainMerge':False,'safety':SAFETY,
        'anchorIdentitySHA256':anchor_sha,
    }
    print(json.dumps(result,sort_keys=True,separators=(',',':')))


if __name__=='__main__':
    run()
