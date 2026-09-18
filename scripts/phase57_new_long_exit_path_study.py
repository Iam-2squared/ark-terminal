"""Zero-based saved-price Path Study: observations/labels only, no EXIT actions.

Standard library only. Does not import Entry, EXIT runtime, models or providers.
Every outcome field is separated from the observed completed-bar prefix.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-new-long-exit-path-study-v1'
PRIOR=ROOT/'docs/evidence/phase57-new-long-entry-exit-conditional-v1'
PATHS=ROOT/'docs/evidence/phase57-msh-entry-long-v2-development/paths.json.gz'
HORIZONS=(5,10,15,20,30,45,60)
LEVELS=(1,2,3,5)
DEPTHS=(1,2,3,5)
TYPES=('INITIAL_ENTRY_OPPORTUNITY','DIP_REPRICE_OPPORTUNITY')
ANCHOR_SHA='985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121'
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed',
    'rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed',
    'productionUpdateAllowed','transmitted')}
ZERO={k:0 for k in ('selectorChanges','newEntryChanges','entryTimingResearch','newExitImplementation',
    'existingRuntimeChanges','modelFit','modelPrediction','freshAccess','oosAccess','providerRequests',
    'minuteResearch','capitalTuning','portfolioTuning','entryReplay','exitReplay','mainMerge')}

def read(p):
    p=Path(p);raw=p.read_bytes()
    if p.suffix=='.gz':raw=gzip.decompress(raw)
    return [json.loads(x) for x in raw.splitlines()] if 'ndjson' in p.name else json.loads(raw)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encoded(x):return (json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
def write(p,x):
    b=encoded(x)
    if str(p).endswith('.gz'):b=gzip.compress(b,mtime=0)
    Path(p).write_bytes(b)
def rate(n,d):return {'n':n,'denominator':d,'rate':n/d if d else None}
def quantile(a,p):
    if not a:return None
    s=sorted(a);i=(len(s)-1)*p;lo=math.floor(i);hi=math.ceil(i)
    return s[lo]+(s[hi]-s[lo])*(i-lo)
def dist(a):
    a=[v for v in a if v is not None]
    return {'n':len(a),'mean':statistics.mean(a) if a else None,
        **{k:quantile(a,p) for k,p in [('p05',.05),('p25',.25),('median',.5),('p75',.75),('p95',.95)]},
        'min':min(a) if a else None,'max':max(a) if a else None}
def minute(s):
    t=dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(dt.timezone(dt.timedelta(hours=9)))
    assert t.second==0 and t.microsecond==0
    return t.hour*60+t.minute
def stamp(session,m):return f'{session}T{m//60:02d}:{m%60:02d}:00+09:00'
def valid(b):
    return b is not None and not b.get('missing') and all(isinstance(b.get(k),(int,float))
        and not isinstance(b[k],bool) and math.isfinite(b[k]) for k in ('o','h','l','c'))
def time_of_day(m):
    return '09_10' if 540<=m<600 else '10_1130' if 600<=m<690 else '1230_14' if 750<=m<840 else '14_END' if 840<=m<925 else 'BOUNDARY'

def prepare(op,path):
    if op.get('referenceStatus')!='REFERENCE_OPEN':
        return {'status':op.get('referenceStatus','UNKNOWN_REFERENCE'),'rows':[]}
    ts=op.get('referenceTimestamp') or op['opportunityTimestamp'];start=minute(ts)
    assert dt.datetime.fromisoformat(ts)>=dt.datetime.fromisoformat(op['opportunityTimestamp'])
    assert ts[:10]==path['sessionDate']
    safe_end=900 if path['sessionDate']<'2024-11-05' else 925
    bound=690 if 540<=start<690 else safe_end if 750<=start<safe_end else None
    if bound is None:return {'status':'BOUNDARY_EXPIRED','rows':[]}
    price=op['referencePrice'];assert isinstance(price,(int,float)) and price>0 and math.isfinite(price)
    source={minute(b['start']):b for b in path['future']};assert len(source)==len(path['future'])
    first=source.get(start);assert valid(first)
    assert math.isclose(path['decisionPrice']*(1+first['o']/100),price,rel_tol=1e-12)
    rows=[]
    for i,m in enumerate(range(start,min(start+60,bound),5)):
        src=source.get(m);b={'slot':i+1,'minute':m,'elapsed':m+5-start,
            'start':stamp(path['sessionDate'],m),'end':stamp(path['sessionDate'],m+5),
            'missing':not valid(src),'observedMinutes':src.get('observedMinutes') if src else None}
        if not b['missing']:
            assert minute(src['end'])==m+5
            b.update({k:100*(path['decisionPrice']*(1+src[k]/100)/price-1) for k in ('o','h','l','c')})
            assert b['l']<=min(b['o'],b['c'])+1e-8 and b['h']+1e-8>=max(b['o'],b['c'])
        rows.append(b)
    return {'status':'REFERENCE_OPEN','startMinute':start,'boundaryMinute':bound,'rows':rows,'startTimestamp':ts,'referencePrice':price}

def window(p,length):
    if p['status']!='REFERENCE_OPEN':return {'status':p['status']},[]
    if p['startMinute']+length>p['boundaryMinute']:return {'status':'BOUNDARY_EXPIRED'},[]
    rs=[b for b in p['rows'] if b['elapsed']<=length]
    if not rs or rs[-1]['elapsed']!=length:return {'status':'UNOBSERVED'},[]
    missing=[b['elapsed'] for b in rs if b['missing']]
    if missing:return {'status':'UNKNOWN_MISSING','firstMissingMinutes':missing[0],'expectedBars':length//5,
        'observedBars':sum(not b['missing'] for b in rs)},[]
    return {'status':'COMPLETE','expectedBars':length//5,'observedBars':len(rs)},rs

def causal_prefix(rows):
    """Only completed observed bars up to this timestamp; no suffix argument."""
    assert rows and not any(b['missing'] for b in rows)
    peak=max(0.,max(b['h'] for b in rows));low=min(0.,min(b['l'] for b in rows));c=rows[-1]['c']
    streak=0;attempts=0;recovered=False;had_adverse=False
    for i,b in enumerate(rows):
        # Recovery requires a strictly later bar than the adverse LOW.
        if had_adverse and b['c']>=0:recovered=True
        if b['l']<0:had_adverse=True
        if i:
            streak=streak+1 if b['c']<rows[i-1]['c'] else 0
            attempts+=int(b['c']<0 and b['c']>rows[i-1]['c'])
    return {'timestamp':rows[-1]['end'],'elapsedMinutes':rows[-1]['elapsed'],
        'currentReturnPct':c,'runningMfePct':peak,'runningMaePct':low,
        'givebackPP':peak-c,'drawdownFromPeakPct':100*(peak-c)/(100+peak),
        'priorClosePct':rows[-2]['c'] if len(rows)>1 else None,
        'lowerCloseStreak':streak,'recoveryAttemptsBelowEntry':attempts,
        'everPositiveClose':any(b['c']>0 for b in rows),
        'positiveThenNegative':c<0 and any(b['c']>0 for b in rows[:-1]),
        'neverPositiveClose':not any(b['c']>0 for b in rows),
        'priorAdverseReclaimed':recovered,'fullUnderlyingMinutes':all(b['observedMinutes']==5 for b in rows)}

def suffix_labels(prefix,future):
    if not future:return {'status':'WINDOW_ENDED','remainingUpsidePct':None,'futureDownsidePct':None,'nextIntervalDirection':None}
    assert not any(b['missing'] for b in future)
    c=prefix['currentReturnPct'];high=max(b['h'] for b in future);low=min(b['l'] for b in future)
    nxt=future[0]['c']-c
    return {'status':'COMPLETE','remainingBars':len(future),
        'remainingUpsidePct':max(0.,100*((100+high)/(100+c)-1)),
        'remainingUpsidePP':max(0.,high-c),'futureDownsidePct':min(0.,100*((100+low)/(100+c)-1)),
        'futureDownsidePP':min(0.,low-c),'additionalPeakPP':max(0.,high-prefix['runningMfePct']),
        'nextIntervalDirection':'UP' if nxt>0 else 'DOWN' if nxt<0 else 'FLAT',
        'nextIntervalChangePP':nxt,'futureReach':{str(k):high>=k for k in LEVELS}}

def when(b):
    if b is None:return None
    return {'bar':b['slot'],'start':b['start'],'end':b['end'],
        'minutesLower':b['elapsed']-5,'minutesUpper':b['elapsed']}
def first(rows,predicate):return next((b for b in rows if predicate(b)),None)

def recovery_event(rows,depth):
    hit=first(rows,lambda b:b['l']<=-depth)
    if hit is None:return {'status':'NO_ADVERSE_TOUCH'}
    later=[b for b in rows if b['slot']>hit['slot']]
    rec=first(later,lambda b:b['c']>=0)
    before=[b for b in rows if b['slot']<hit['slot']]
    prior=before[-1]['c'] if before else 0.
    prior_rec=first(later,lambda b:b['c']>=prior)
    running=0.;new_high=None;new_high_after_reclaim=None
    for b in rows:
        if b['slot']>hit['slot'] and b['h']>running and new_high is None:new_high=b
        if rec and b['slot']>rec['slot'] and b['h']>running and new_high_after_reclaim is None:new_high_after_reclaim=b
        running=max(running,b['h'])
    post=[b for b in rows if rec and b['slot']>rec['slot']]
    until=[b for b in rows if b['slot']>=hit['slot'] and (not rec or b['slot']<=rec['slot'])]
    return {'status':'ADVERSE_OBSERVED','firstAdverse':when(hit),'entryReclaim':when(rec),
        'entryReclaimClosePct':rec['c'] if rec else None,'priorCloseReferencePct':prior,
        'priorCloseReclaim':when(prior_rec),'newRunningHighAfterAdverse':when(new_high),
        'newRunningHighAfterReclaim':when(new_high_after_reclaim),
        'depthUntilReclaimOrEndPct':min(b['l'] for b in until),
        'durationLowerMinutes':rec['elapsed']-hit['elapsed'] if rec else None,
        'durationUpperMinutes':rec['elapsed']-(hit['elapsed']-5) if rec else None,
        'noReclaimObservedWithinMinutes':rows[-1]['elapsed'] if rec is None else None,
        'postReclaimStatus':'COMPLETE' if post else 'NO_POST_RECLAIM_WINDOW' if rec else 'NO_RECLAIM',
        'postReclaimRemainingUpsidePct':max(0.,100*((100+max(b['h'] for b in post))/(100+rec['c'])-1)) if post else None,
        'winnerAfterReclaim':{str(k):any(b['h']>=k for b in post) if post else None for k in LEVELS},
        'winnerAfterAdverse':{str(k):any(b['h']>=k for b in later) if later else None for k in LEVELS},
        'sameBarWinnerOrderUnknown':{str(k):hit['h']>=k for k in LEVELS}}

def giveback_events(rows,level):
    touch=first(rows,lambda b:b['h']>=level)
    if touch is None:return {'status':'NO_LEVEL_TOUCH'}
    peak=0.;events={};types=('1pp','2pp','3pp','HALF_MFE','FULL_TO_ENTRY','NEGATIVE')
    for b in rows:
        peak=max(peak,b['h'])
        if b['slot']<touch['slot']:continue
        flags={f'{k}pp':peak-b['c']>=k for k in (1,2,3)}
        flags.update(HALF_MFE=b['c']<=peak*.5,FULL_TO_ENTRY=b['c']<=0,NEGATIVE=b['c']<0)
        for typ,flag in flags.items():
            if not flag or typ in events:continue
            later=[x for x in rows if x['slot']>b['slot']]
            rehigh=first(later,lambda x:x['h']>peak)
            neg=rows[-1]['c']<0
            outcome=('REHIGH_' if rehigh else 'NO_REHIGH_')+('NEGATIVE_ENDPOINT' if neg else 'NONNEGATIVE_ENDPOINT') if later else 'NO_POST_EVENT_WINDOW'
            events[typ]={'atClose':b['end'],'elapsedMinutes':b['elapsed'],'runningPeakPct':peak,
                'givebackPP':peak-b['c'],'closePct':b['c'],'lowerCloseStreak':causal_prefix(rows[:b['slot']])['lowerCloseStreak'],
                'recoveryAttemptsBelowEntry':causal_prefix(rows[:b['slot']])['recoveryAttemptsBelowEntry'],
                'newHighLater':when(rehigh),'outcome':outcome,
                'endpointPct':rows[-1]['c'],'postEventMaePct':min(x['l'] for x in later) if later else None}
    return {'status':'LEVEL_TOUCHED','firstLevelTouch':when(touch),'events':{k:events.get(k) for k in types}}

def panel(rows):
    hi=max(rows,key=lambda b:b['h']);lo=min(rows,key=lambda b:b['l']);mfe=max(0.,hi['h']);mae=min(0.,lo['l'])
    before=[b for b in rows if b['slot']<hi['slot']];inclusive=[b for b in rows if b['slot']<=hi['slot']]
    after=[b for b in rows if b['slot']>hi['slot']]
    running=0.;before_givebacks=[]
    for b in before:
        running=max(running,b['h']);before_givebacks.append(running-b['c'])
    touches={str(k):when(first(rows,lambda b:b['h']>=k)) for k in LEVELS}
    recovery={str(k):recovery_event(rows,k) for k in DEPTHS}
    evol={}
    for h in HORIZONS:
        prefix=[b for b in rows if b['elapsed']<=h]
        if not prefix or prefix[-1]['elapsed']!=h:evol[str(h)]={'status':'BEYOND_PANEL'};continue
        c=causal_prefix(prefix);future=[b for b in rows if b['elapsed']>h]
        evol[str(h)]={'status':'COMPLETE','causalPrefix':c,'evaluatorOnly':suffix_labels(c,future)}
    return {'status':'COMPLETE','horizonMinutes':rows[-1]['elapsed'],'bars':len(rows),
        'mfePct':mfe,'maePct':mae,'endpointPct':rows[-1]['c'],
        'timeToMfe':when(hi) if mfe>0 else None,'timeToMae':when(lo) if mae<0 else None,
        'maeStrictlyBeforeMfeBarPct':min([0.]+[b['l'] for b in before]) if mfe>0 else None,
        'maeIncludingMfeBarPct':min([0.]+[b['l'] for b in inclusive]) if mfe>0 else None,
        'peakBarLowHighOrder':'UNKNOWN_INTRABAR_ORDER',
        'givebackAtMfeBarClosePP':mfe-hi['c'] if mfe>0 else None,
        'maxRunningGivebackBeforeMfeBarPP':max(before_givebacks) if before_givebacks and mfe>0 else None,
        'worstCompletedCloseGivebackAfterMfePP':mfe-min(b['c'] for b in after) if after and mfe>0 else None,
        'endpointGivebackPP':mfe-rows[-1]['c'],'positiveThenNegative':rows[-1]['c']<0 and any(b['c']>0 for b in rows[:-1]),
        'neverPositiveClose':not any(b['c']>0 for b in rows),'firstHits':touches,
        'recovery':recovery,'giveback':{str(k):giveback_events(rows,k) for k in LEVELS},
        'evolution':evol,'fullUnderlyingMinutes':all(b['observedMinutes']==5 for b in rows),
        'sameBarPlus1Minus1':sum(b['h']>=1 and b['l']<=-1 for b in rows),
        'sameBarPlus3Minus2':sum(b['h']>=3 and b['l']<=-2 for b in rows)}

def path_metrics(ps):
    return {'n':len(ps),**{k:dist([p[k] for p in ps]) for k in ('mfePct','maePct','endpointPct','endpointGivebackPP',
        'maeStrictlyBeforeMfeBarPct','maeIncludingMfeBarPct','givebackAtMfeBarClosePP','maxRunningGivebackBeforeMfeBarPP','worstCompletedCloseGivebackAfterMfePP')},
        'timeToMfeUpperMinutes':dist([p['timeToMfe']['minutesUpper'] for p in ps if p['timeToMfe']]),
        'timeToMaeUpperMinutes':dist([p['timeToMae']['minutesUpper'] for p in ps if p['timeToMae']]),
        'positiveThenNegative':rate(sum(p['positiveThenNegative'] for p in ps),len(ps)),
        'neverPositiveClose':rate(sum(p['neverPositiveClose'] for p in ps),len(ps)),
        'recovery1Then3':rate(sum(p['recovery']['1'].get('winnerAfterReclaim',{}).get('3') is True for p in ps),len(ps)),
        'recovery2Then3':rate(sum(p['recovery']['2'].get('winnerAfterReclaim',{}).get('3') is True for p in ps),len(ps)),
        'adverse2NoReclaim':rate(sum(p['recovery']['2']['status']=='ADVERSE_OBSERVED' and p['recovery']['2']['entryReclaim'] is None for p in ps),len(ps)),
        'reach':{str(k):rate(sum(p['mfePct']>=k for p in ps),len(ps)) for k in LEVELS},
        'negative5LaterLevel':{str(k):rate(sum(p['evolution']['5']['causalPrefix']['currentReturnPct']<0
            and p['evolution']['5']['evaluatorOnly']['futureReach'][str(k)] for p in ps),
            sum(p['evolution']['5']['causalPrefix']['currentReturnPct']<0 for p in ps)) for k in (3,5)},
        'sameBarPlus1Minus1Paths':rate(sum(p['sameBarPlus1Minus1']>0 for p in ps),len(ps)),
        'sameBarPlus3Minus2Paths':rate(sum(p['sameBarPlus3Minus2']>0 for p in ps),len(ps))}

def snapshot_summary(ss,population):
    valid=[s for s in ss if s['status']=='COMPLETE'];cs=[s['causalPrefix'] for s in valid]
    fs=[s['evaluatorOnly'] for s in valid if s['evaluatorOnly']['status']=='COMPLETE']
    next_obs=[]
    for row in valid:
        lab=row['evaluatorOnly'];obs=lab.get('nextIntervalObservation')
        if obs and obs['status']=='COMPLETE':next_obs.append(obs['direction'])
        elif obs is None and lab['status']=='COMPLETE':next_obs.append(lab['nextIntervalDirection'])
    return {'coverage':rate(len(valid),population),'statuses':dict(collections.Counter(s['status'] for s in ss)),
        'prefix':{k:dist([c[k] for c in cs]) for k in ('currentReturnPct','runningMfePct','runningMaePct','givebackPP',
            'drawdownFromPeakPct','lowerCloseStreak','recoveryAttemptsBelowEntry')},
        'negativeClose':rate(sum(c['currentReturnPct']<0 for c in cs),len(cs)),
        'positiveThenNegative':rate(sum(c['positiveThenNegative'] for c in cs),len(cs)),
        'neverPositiveClose':rate(sum(c['neverPositiveClose'] for c in cs),len(cs)),
        'priorAdverseReclaimed':rate(sum(c['priorAdverseReclaimed'] for c in cs),len(cs)),
        'anyRecoveryAttempt':rate(sum(c['recoveryAttemptsBelowEntry']>0 for c in cs),len(cs)),
        'lowerCloseStreakCounts':dict(collections.Counter(str(c['lowerCloseStreak']) for c in cs)),
        'suffixCoverage':rate(len(fs),len(valid)),
        'evaluatorOnly':{k:dist([f[k] for f in fs]) for k in ('remainingUpsidePct','remainingUpsidePP','futureDownsidePct','additionalPeakPP')},
        'nextIntervalCoverage':rate(len(next_obs),len(valid)),
        'nextIntervalDirections':dict(collections.Counter(next_obs))}

def panel_summary(ps):
    out={'metrics':path_metrics(ps),'evolution':{},'winners':{},'recovery':{},'giveback':{}}
    for h in HORIZONS:out['evolution'][str(h)]=snapshot_summary([p['evolution'][str(h)] for p in ps],len(ps))
    for k in LEVELS:
        ws=[p for p in ps if p['mfePct']>=k];w={'count':rate(len(ws),len(ps)),'metrics':path_metrics(ws),
            'firstLevelHitUpperMinutes':dist([p['firstHits'][str(k)]['minutesUpper'] for p in ws]),
            'adverse':{},'negativeSnapshots':{}}
        for depth in DEPTHS:
            adverse=[p for p in ps if p['recovery'][str(depth)]['status']=='ADVERSE_OBSERVED']
            aw=[p for p in ws if p['recovery'][str(depth)]['status']=='ADVERSE_OBSERVED']
            confirmed=sum(p['recovery'][str(depth)]['winnerAfterAdverse'][str(k)] is True for p in adverse)
            same_only=sum(p['recovery'][str(depth)]['sameBarWinnerOrderUnknown'][str(k)]
                and p['recovery'][str(depth)]['winnerAfterAdverse'][str(k)] is not True for p in adverse)
            before_first=sum(p['recovery'][str(depth)]['firstAdverse']['bar']<p['firstHits'][str(k)]['bar'] for p in aw)
            w['adverse'][str(depth)]={'adverseWithinWinners':rate(len(aw),len(ws)),
                'confirmedLaterWinnerGivenAdverse':rate(confirmed,len(adverse)),
                'sameBarPossibleOnlyGivenAdverse':rate(same_only,len(adverse)),
                'adverseStrictlyBeforeFirstWinner':rate(before_first,len(ws))}
        for h in (5,10,15):
            neg=[p for p in ps if p['evolution'][str(h)]['causalPrefix']['currentReturnPct']<0]
            future=[p for p in neg if p['evolution'][str(h)]['evaluatorOnly']['futureReach'][str(k)]]
            new=[p for p in future if p['firstHits'][str(k)]['minutesUpper']>h]
            w['negativeSnapshots'][str(h)]={'negativePopulation':rate(len(neg),len(ps)),
                'laterLevelHit':rate(len(future),len(neg)),
                'notYetFirstHitWinner':rate(len(new),len(ws)),
                'remainingUpsidePct':dist([p['evolution'][str(h)]['evaluatorOnly']['remainingUpsidePct'] for p in future])}
        out['winners'][str(k)]=w
    for depth in DEPTHS:
        rs=[p['recovery'][str(depth)] for p in ps if p['recovery'][str(depth)]['status']=='ADVERSE_OBSERVED']
        recovered=[r for r in rs if r['entryReclaim'] is not None]
        post=[r for r in recovered if r['postReclaimStatus']=='COMPLETE']
        out['recovery'][str(depth)]={'adverse':rate(len(rs),len(ps)),'reclaimed':rate(len(recovered),len(rs)),
            'postReclaimObserved':rate(len(post),len(recovered)),
            'reclaimUpperMinutes':dist([r['entryReclaim']['minutesUpper'] for r in recovered]),
            'priorCloseReclaimed':rate(sum(r['priorCloseReclaim'] is not None for r in rs),len(rs)),
            'priorCloseReclaimUpperMinutes':dist([r['priorCloseReclaim']['minutesUpper'] for r in rs if r['priorCloseReclaim']]),
            'newRunningHigh':rate(sum(r['newRunningHighAfterAdverse'] is not None for r in rs),len(rs)),
            'newRunningHighUpperMinutes':dist([r['newRunningHighAfterAdverse']['minutesUpper'] for r in rs if r['newRunningHighAfterAdverse']]),
            'newRunningHighAfterReclaim':rate(sum(r['newRunningHighAfterReclaim'] is not None for r in recovered),len(recovered)),
            'newRunningHighAfterReclaimUpperMinutes':dist([r['newRunningHighAfterReclaim']['minutesUpper'] for r in recovered if r['newRunningHighAfterReclaim']]),
            **{key:dist([r[key] for r in rs]) for key in ('depthUntilReclaimOrEndPct','durationLowerMinutes','durationUpperMinutes','postReclaimRemainingUpsidePct')},
            'postReclaimWinners':{str(k):rate(sum(r['winnerAfterReclaim'][str(k)] is True for r in post),len(post)) for k in LEVELS},
            'recoveryWinner3':{'n':sum(r['winnerAfterReclaim'].get('3') is True for r in post),
                'depthPct':dist([r['depthUntilReclaimOrEndPct'] for r in post if r['winnerAfterReclaim']['3']]),
                'durationUpperMinutes':dist([r['durationUpperMinutes'] for r in post if r['winnerAfterReclaim']['3']])}}
    for k in LEVELS:
        ws=[p for p in ps if p['mfePct']>=k];g={}
        for typ in ('1pp','2pp','3pp','HALF_MFE','FULL_TO_ENTRY','NEGATIVE'):
            events=[p['giveback'][str(k)]['events'][typ] for p in ws if p['giveback'][str(k)]['events'][typ]]
            observed=[e for e in events if e['outcome']!='NO_POST_EVENT_WINDOW']
            groups={}
            for outcome in sorted({e['outcome'] for e in observed}):
                es=[e for e in observed if e['outcome']==outcome]
                groups[outcome]={'count':rate(len(es),len(observed)),**{f:dist([e[f] for e in es]) for f in
                    ('elapsedMinutes','runningPeakPct','givebackPP','closePct','lowerCloseStreak','recoveryAttemptsBelowEntry','endpointPct','postEventMaePct')}}
            g[typ]={'events':rate(len(events),len(ws)),'postEventObserved':rate(len(observed),len(events)),
                'timeMinutes':dist([e['elapsedMinutes'] for e in events]),
                'reHighLater':rate(sum(e['newHighLater'] is not None for e in observed),len(observed)),
                'outcomes':groups}
        out['giveback'][str(k)]=g
    return out

def compact_rows(rows,panel_key='own60'):
    ps=[r['panels'][panel_key] for r in rows if r['panels'][panel_key]['status']=='COMPLETE']
    return {'population':len(rows),'complete':rate(len(ps),len(rows)),'metrics':path_metrics(ps)}

def build():
    protocol=read(BASE/'protocol.json')
    for p,h in protocol['sourcePins'].items():assert sha(ROOT/p)==h,p
    original=read(PRIOR/'entry-parity/ledger.ndjson.gz');paths=read(PATHS)
    assert paths['freshAccess']==0 and paths['oosAccess']==0 and paths['providerRequests']==0
    path_map={p['selectorEventId']:p for p in paths['events']}
    ids=sorted(e['anchorId'] for e in original);assert len(ids)==len(set(ids))==2743
    assert hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest()==ANCHOR_SHA
    assert sum(e['evaluator']['primary60'] for e in original)==878
    sessions=sorted({e['sessionDate'] for e in original});assert len(sessions)==76
    counts=collections.Counter(e['symbol'] for e in original)
    top=sorted(counts,key=lambda sym:(-counts[sym],sym))[:3]
    ledger=[]
    for src in original:
        raw=path_map[src['anchorId']];ev=src['evaluator']
        for key in ('initialEvent','secondaryEvent'):
            op=src['decision'][key]
            if op is None:continue
            assert op['anchorId']==raw['selectorEventId'] and op['symbol']==raw['symbol'] and op['session']==raw['sessionDate']
            p=prepare(op,raw);own_cov,own_rows=window(p,60)
            own=panel(own_rows) if own_rows else own_cov
            common={'status':'OUTSIDE_ORIGINAL_PRIMARY_DIP328'}
            if ev['primary60'] and src['decision']['secondaryEvent'] is not None:
                length=minute(raw['decisionTimestamp'])+60-p['startMinute']
                cov,rs=window(p,length);common=panel(rs) if rs else cov
                assert common['status']=='COMPLETE'
            snaps={}
            for h in HORIZONS:
                cov,rs=window(p,h)
                if rs:
                    c=causal_prefix(rs)
                    future=[b for b in own_rows if b['elapsed']>h]
                    lab=suffix_labels(c,future) if own_rows else {'status':'UNKNOWN_OWN60_FUTURE'}
                    if h<60:
                        nc,nr=window(p,h+5)
                        if nr:
                            delta=nr[-1]['c']-c['currentReturnPct']
                            lab['nextIntervalObservation']={'status':'COMPLETE','direction':'UP' if delta>0 else 'DOWN' if delta<0 else 'FLAT','changePP':delta}
                        else:lab['nextIntervalObservation']=nc
                    else:lab['nextIntervalObservation']={'status':'WINDOW_ENDED'}
                    snaps[str(h)]={'status':'COMPLETE','causalPrefix':c,'evaluatorOnly':lab}
                else:snaps[str(h)]=cov
            tags=[]
            if key=='secondaryEvent' and ev['primary60'] and ev.get('buyImprovementPct',0)>0:
                tags.append('CHEAPER_299')
                for depth in (2,5):
                    if ev['secondaryD30']['downside']>=depth:tags.append(f'D30_DROP_{depth}')
            ledger.append({'anchorId':src['anchorId'],'symbol':src['symbol'],'sessionDate':src['sessionDate'],
                'cohort':op['eventType'],'opportunity':op,'primary60':ev['primary60'],
                'secondaryTerminal':src['decision']['secondaryState']['state'],
                'referenceStatus':p['status'],'positionStartTimestamp':p.get('startTimestamp'),
                'chronologicalBlock':1+sessions.index(src['sessionDate'])//19,
                'timeOfDay':time_of_day(p['startMinute']) if 'startMinute' in p else 'UNPRICED',
                'riskTagsEvaluatorOnly':tags,'snapshots':snaps,'panels':{'own60':own,'commonT0_60':common}})
    assert len(ledger)==3284
    summary={'status':'NEW_LONG_EXIT_PATH_STUDY_COMPLETE','startHead':protocol['startHead'],
        'anchorIdentitySHA256':ANCHOR_SHA,'opportunityRows':len(ledger),
        'dateRange':[sessions[0],sessions[-1]],'sessions':len(sessions),
        'fullAnchorSymbols':len(counts),'cohorts':{},'pairedPanels':{},'riskCohorts':{},'robustness':{},
        'safety':SAFETY,'zeroCounters':ZERO}
    for typ in TYPES:
        rows=[r for r in ledger if r['cohort']==typ];ps=[r['panels']['own60'] for r in rows if r['panels']['own60']['status']=='COMPLETE']
        summary['cohorts'][typ]={'opportunities':len(rows),
            'symbols':len({r['symbol'] for r in rows}),'sessions':len({r['sessionDate'] for r in rows}),
            'own60Symbols':len({r['symbol'] for r in rows if r['panels']['own60']['status']=='COMPLETE'}),
            'own60Sessions':len({r['sessionDate'] for r in rows if r['panels']['own60']['status']=='COMPLETE'}),
            'referenceStates':dict(collections.Counter(r['referenceStatus'] for r in rows)),
            'own60Coverage':rate(len(ps),len(rows)),
            'own60Statuses':dict(collections.Counter(r['panels']['own60']['status'] for r in rows)),
            'own60':panel_summary(ps),
            'loserGroups':{label:{'count':rate(len(group),len(ps)),'metrics':path_metrics(group),
                'evolution':{str(h):snapshot_summary([p['evolution'][str(h)] for p in group],len(group)) for h in HORIZONS}}
                for label,group in {
                    'NEGATIVE_ENDPOINT':[p for p in ps if p['endpointPct']<0],
                    'NONNEGATIVE_ENDPOINT':[p for p in ps if p['endpointPct']>=0],
                    'NEVER_POSITIVE_AND_NEGATIVE':[p for p in ps if p['endpointPct']<0 and p['neverPositiveClose']],
                    'POSITIVE_THEN_NEGATIVE':[p for p in ps if p['positiveThenNegative']]}.items()},
            'allOpportunityEvolution':{str(h):snapshot_summary([r['snapshots'][str(h)] for r in rows],len(rows)) for h in HORIZONS}}
    initial={r['anchorId']:r for r in ledger if r['cohort']==TYPES[0]}
    dips={r['anchorId']:r for r in ledger if r['cohort']==TYPES[1]}
    for panel_name,key in [('MATCHED_OWN60','own60'),('COMMON_T0_60_DIP328','commonT0_60')]:
        matched=sorted(i for i in dips if all(m[i]['panels'][key]['status']=='COMPLETE' for m in (initial,dips)))
        summary['pairedPanels'][panel_name]={'matchedAnchors':len(matched),'denominator':len(dips),
            'identitiesSHA256':hashlib.sha256(('\n'.join(matched)+'\n').encode()).hexdigest(),
            'INITIAL':panel_summary([initial[i]['panels'][key] for i in matched]),
            'DIP':panel_summary([dips[i]['panels'][key] for i in matched]),
            'DIP_minus_INITIAL':{f:dist([dips[i]['panels'][key][f]-initial[i]['panels'][key][f] for i in matched]) for f in
                ('mfePct','maePct','endpointPct','endpointGivebackPP')}}
    cheap=[r for r in dips.values() if 'CHEAPER_299' in r['riskTagsEvaluatorOnly']];assert len(cheap)==299
    for depth,n in ((2,106),(5,21)):
        hit=[r for r in cheap if f'D30_DROP_{depth}' in r['riskTagsEvaluatorOnly']]
        control=[r for r in cheap if f'D30_DROP_{depth}' not in r['riskTagsEvaluatorOnly']]
        assert len(hit)==n
        record={'cohortN':len(hit),'denominator':299,'identities':[r['anchorId'] for r in hit],
            'own60Subset':compact_rows(hit),'common55':panel_summary([r['panels']['commonT0_60'] for r in hit]),
            'controlCommon55':panel_summary([r['panels']['commonT0_60'] for r in control]),'earlyEvolution':{},'lossExpansion':{}}
        for h in (5,10,15,20):
            a=snapshot_summary([r['snapshots'][str(h)] for r in hit],len(hit))
            b=snapshot_summary([r['snapshots'][str(h)] for r in control],len(control))
            av=a['prefix']['currentReturnPct'];bv=b['prefix']['currentReturnPct']
            record['earlyEvolution'][str(h)]={'risk':a,'control':b,
                'currentReturnIQROverlap':max(0,min(av['p75'],bv['p75'])-max(av['p25'],bv['p25'])),
                'riskIQRStrictlyBelowControl':av['p75']<bv['p25']}
        for h in (10,15,20):
            rs=[r for r in hit if all(r['snapshots'][str(t)]['status']=='COMPLETE' for t in (5,h))]
            delta=[r['snapshots'][str(h)]['causalPrefix']['currentReturnPct']-r['snapshots']['5']['causalPrefix']['currentReturnPct'] for r in rs]
            record['lossExpansion'][str(h)]={'coverage':rate(len(rs),len(hit)),'closeChangeFrom5PP':dist(delta),
                'runningMaeChangeFrom5PP':dist([r['snapshots'][str(h)]['causalPrefix']['runningMaePct']-r['snapshots']['5']['causalPrefix']['runningMaePct'] for r in rs])}
        summary['riskCohorts'][str(depth)]=record
    for typ in TYPES:
        rows=[r for r in ledger if r['cohort']==typ]
        cohort_counts=collections.Counter(r['symbol'] for r in rows)
        cohort_top=sorted(cohort_counts,key=lambda sym:(-cohort_counts[sym],sym))[:3]
        summary['robustness'][typ]={
            'chronologicalBlocks':{str(b):compact_rows([r for r in rows if r['chronologicalBlock']==b]) for b in range(1,5)},
            'blockSessions':{str(b):sessions[(b-1)*19:b*19] for b in range(1,5)},
            'timeOfDay':{t:compact_rows([r for r in rows if r['timeOfDay']==t]) for t in ('09_10','10_1130','1230_14','14_END','UNPRICED')},
            'excludeTopFrequency1':compact_rows([r for r in rows if r['symbol'] not in top[:1]]),
            'excludeTopFrequency3':compact_rows([r for r in rows if r['symbol'] not in top]),
            'fullUnderlyingMinutes':compact_rows([r for r in rows if r['panels']['own60'].get('fullUnderlyingMinutes')]),
            'perSymbol':{sym:compact_rows([r for r in rows if r['symbol']==sym]) for sym in sorted({r['symbol'] for r in rows})},
            'topFrequencySymbols':[{'symbol':sym,'all2743Frequency':counts[sym]} for sym in top],
            'cohortFrequencySupplement':{
                'timing':'POST_AGGREGATE_COVERAGE_AUDIT_SUPPLEMENT_NOT_PREREGISTERED',
                'reason':'Global top3 have no DIP opportunities; add cohort-frequency-only stress without outcome-ranked exclusions.',
                'symbols':[{'symbol':sym,'cohortFrequency':cohort_counts[sym]} for sym in cohort_top],
                'excludeTop1':compact_rows([r for r in rows if r['symbol'] not in cohort_top[:1]]),
                'excludeTop3':compact_rows([r for r in rows if r['symbol'] not in cohort_top])}}
    for depth in (2,5):
        rows=[r for r in dips.values() if f'D30_DROP_{depth}' in r['riskTagsEvaluatorOnly']]
        summary['riskCohorts'][str(depth)]['robustness']={
            'byBlock':{str(b):compact_rows([r for r in rows if r['chronologicalBlock']==b],'commonT0_60') for b in range(1,5)},
            'symbols':dict(collections.Counter(r['symbol'] for r in rows)),
            'excludeTopFrequency1':compact_rows([r for r in rows if r['symbol'] not in top[:1]],'commonT0_60'),
            'excludeTopFrequency3':compact_rows([r for r in rows if r['symbol'] not in top],'commonT0_60')}
    return ledger,summary

def run(out):
    ledger,summary=build();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    write(out/'ledger.json.gz',ledger);write(out/'summary.json.gz',summary)
    inputs=dict(read(BASE/'protocol.json')['sourcePins'])
    for p in [Path(__file__),BASE/'protocol.md',BASE/'protocol.json']:inputs[str(p.relative_to(ROOT))]=sha(p)
    write(out/'manifest.json',{'schemaVersion':1,'status':summary['status'],'inputPins':inputs,
        'outputPins':{p:sha(out/p) for p in ('ledger.json.gz','summary.json.gz')},
        'anchorIdentitySHA256':ANCHOR_SHA,'safety':SAFETY,'zeroCounters':ZERO})
    print(json.dumps({'status':summary['status'],'opportunityRows':len(ledger),
        'cohorts':{k:{'opportunities':v['opportunities'],'own60':v['own60Coverage']} for k,v in summary['cohorts'].items()},
        'paired':{k:v['matchedAnchors'] for k,v in summary['pairedPanels'].items()}}))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default=str(BASE));a=p.parse_args();run(a.out)
