"""Read-only, source-pinned MAE attribution. No decision/model/strategy changes."""
from __future__ import annotations

import argparse
import collections
import copy
import datetime as dt
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

from scripts import phase57_new_long_entry_exit_conditional as cond
from scripts import phase57_new_long_exit_candidate_a as ca

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-strict30-mae-attribution-v1'
START_HEAD='a6824fb56e688355235af5fade91472a2eb157a0'
PROTOCOL_COMMIT='61bb2b61b7d4ed07ac2df75e9fc7e6ab56f9c533'
OLD='LEGACY_MSH_V1_ENTER'
INITIAL='INITIAL_ENTRY_OPPORTUNITY'
DIP='DIP_REPRICE_OPPORTUNITY'
BUCKETS=('(-1,0]','(-2,-1]','(-3,-2]','(-5,-3]','(-10,-5]','<=-10')
CLASSES=('RECOVERY_WINNER','RECOVERY_BUT_NO_MAJOR_WIN','CONTINUED_FAILURE','INCONCLUSIVE')
HORIZONS=('STRICT30','FIXED12_WINDOW','SESSION')
LEVELS=(1,2,3,5)
SAFETY=ca.SAFETY


def read(p):return cond.read(p)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encoded(x):return (json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
def stamp(t):return dt.datetime.fromisoformat(t.replace('Z','+00:00')).timestamp()
def dist(v):return cond.dist(v)
def rate(n,d):return cond.rate(n,d)


def perf(v):
    v=[x for x in v if x is not None];loss=-sum(x for x in v if x<0)
    return {**dist(v),'PF':sum(x for x in v if x>0)/loss if loss else None,
            'PFStatus':'DEFINED' if loss else 'NO_NEGATIVE_RETURNS',
            'win':rate(sum(x>0 for x in v),len(v))}


def bucket(mae):
    return BUCKETS[next((i for i,k in enumerate((-1,-2,-3,-5,-10)) if mae>k),5)]


def strict30(bars):
    # Uses only first six expected bars; suffix cannot change strict labels.
    if len(bars)<6:return {'status':'SESSION_END_OR_SHORT_PATH'}
    b=bars[:6]
    if any(x['minutes']!=(i+1)*5 for i,x in enumerate(b)):
        return {'status':'LUNCH_OR_SESSION_BOUNDARY'}
    if any(x.get('missing') or not cond.valid(x) for x in b):return {'status':'MISSING_BAR'}
    if any(stamp(x['end'])-stamp(x['start'])!=300 for x in b):raise AssertionError('BAR_DURATION')
    if any(stamp(b[i]['start'])!=stamp(b[i-1]['end']) for i in range(1,6)):
        return {'status':'NONCONTIGUOUS_CLOCK'}
    return {'status':'COMPLETE','bars':b}


def location(bar,reference,field):
    return {'slot':bar['slot'],'start':bar['start'],'end':bar['end'],
            'entryMinutesInterval':[bar['minutes']-5,bar['minutes']],
            'returnPct':bar[field],'price':reference*(1+bar[field]/100)}


def event_time(bar,anchor,close=False):
    duration=(stamp(anchor['end'])-stamp(anchor['start']))/60
    return {'slot':bar['slot'],'start':bar['start'],'end':bar['end'],
            'entryMinutesInterval':[bar['minutes'] if close else bar['minutes']-5,bar['minutes']],
            'delayFromAdverseIntervalMinutes':[bar['minutes']-anchor['minutes'] if close else bar['minutes']-5-anchor['minutes'],
                                               bar['minutes']-anchor['minutes']+duration]}


def after_anchor(bars,index,complete=True):
    """All returned fields are evaluator labels; no policy input or action."""
    anchor=bars[index];later=[b for b in bars[index+1:] if cond.valid(b)]
    hits={str(k):next((b for b in later if b['h']>=k),None) for k in LEVELS}
    reclaim=next((b for b in later if b['c']>=0),None)
    close_positive=next((b for b in later if b['c']>0),None)
    low=min((b['l'] for b in later),default=None)
    change=100*((1+low/100)/(1+anchor['c']/100)-1) if low is not None and anchor['c']>-100 else None
    def seen_or_false(test):return True if test else False if complete and later else None
    return {'laterBars':len(later),'completeFollowup':complete,
        'recovery':{str(k):{'observed':seen_or_false(hits[str(k)] is not None),
            'first':event_time(hits[str(k)],anchor) if hits[str(k)] else None,
            'triggerBarHighOrder':'UNKNOWN_INTRABAR_ORDER' if anchor['h']>=k else 'NO_TRIGGER_BAR_TOUCH'} for k in LEVELS},
        'laterCloseReclaim':seen_or_false(reclaim is not None),
        'reclaimTime':event_time(reclaim,anchor,True) if reclaim else None,
        'triggerBarCloseReclaimKnown':anchor['c']>=0,
        'laterPositiveClose':seen_or_false(close_positive is not None),
        'laterPositiveHigh':seen_or_false(any(b['h']>0 for b in later)),
        'additionalDropPctFromBreachClose':change,
        'additionalDropPPFromBreachClose':low-anchor['c'] if low is not None else None,
        'additionalDrop2':seen_or_false(change is not None and change<=-2),
        'additionalDrop5':seen_or_false(change is not None and change<=-5),
        'mfeAfterAnchorPct':max(0,max(b['h'] for b in later)) if later else None,
        'terminalPct':bars[-1]['c'] if complete and cond.valid(bars[-1]) else None}


def classify(bars,index,threshold,complete=True):
    if not complete:return 'INCONCLUSIVE'
    a=after_anchor(bars,index,complete)
    if a['recovery']['3']['observed'] is True:return 'RECOVERY_WINNER'
    if bars[index]['h']>=3:return 'INCONCLUSIVE'
    if a['laterCloseReclaim'] is True or a['triggerBarCloseReclaimKnown']:
        return 'RECOVERY_BUT_NO_MAJOR_WIN'
    if a['laterBars'] and a['terminalPct'] is not None and a['terminalPct']<=-threshold:
        return 'CONTINUED_FAILURE'
    return 'INCONCLUSIVE'


def exit_vs_breach(result,bars,threshold):
    hit=next((b for b in bars[:6] if b['l']<=-threshold),None)
    if hit is None:return 'NO_STRICT30_BREACH'
    if result is None:return 'UNKNOWN_EXIT'
    if result['exitBar']>hit['slot']:return 'BREACH_BEFORE_EXIT'
    if result['exitBar']<hit['slot']:return 'BREACH_AFTER_EXIT'
    if result['status']=='FIXED12_FALLBACK':return 'BREACH_BEFORE_OR_AT_CLOSE_EXIT'
    if result['grossPct']<=-threshold:return 'BREACH_AT_OR_BEFORE_EXIT_OPEN'
    # Position exits at bar OPEN above threshold; a lower LOW is necessarily later.
    return 'BREACH_AFTER_EXIT_OPEN'


def path_metrics(bars,reference):
    lo=min(range(len(bars)),key=lambda i:bars[i]['l'])
    hi=max(range(len(bars)),key=lambda i:bars[i]['h'])
    mae=min(0,bars[lo]['l']);mfe=max(0,bars[hi]['h'])
    order=('NO_POSITIVE_MFE' if mfe==0 else 'NO_ADVERSE_MAE' if mae==0 else
           'MAE_BEFORE_MFE' if lo<hi else 'MFE_BEFORE_MAE' if hi<lo else 'UNKNOWN_INTRABAR_ORDER')
    entry={'slot':0,'start':bars[0]['start'],'end':bars[0]['start'],'minutes':0,'o':0.,'h':0.,'l':0.,'c':0.,'missing':False}
    entry_location={'slot':0,'start':entry['start'],'end':entry['end'],'entryMinutesInterval':[0,0],'returnPct':0.,'price':reference}
    return {'maePct':mae,'mfePct':mfe,'maeLocation':location(bars[lo],reference,'l') if mae<0 else entry_location,
            'mfeLocation':location(bars[hi],reference,'h') if mfe>0 else entry_location,'firstMaeIndex':lo if mae<0 else None,'firstMfeIndex':hi if mfe>0 else None,
            'maeTieSlots':[b['slot'] for b in bars if b['l']==bars[lo]['l']],
            'mfeTieSlots':[b['slot'] for b in bars if b['h']==bars[hi]['h']],
            'ordering':order,'terminalPct':bars[-1]['c'],'givebackPP':mfe-bars[-1]['c'],
            'anyTimeReach':{str(k):any(b['h']>=k for b in bars) for k in LEVELS},
            'afterGlobalMae':after_anchor(bars,lo) if mae<0 else after_anchor([entry]+bars,0),
            'fullUnderlyingMinutes':all(b.get('observedMinutes')==5 for b in bars)}


def selector_link(anchor,entry_timestamp,feas,transfer):
    f,t=feas[anchor],transfer[anchor]
    assert all(f[k]==t[k] for k in ('symbol','sessionDate','ridgeScore','ridgeRank','decisionPrice'))
    assert stamp(t['selectorFeatureTimestamp'])<=stamp(t['decisionTimestamp'])
    assert stamp(t['selectorFeatureAvailableAt'])<=stamp(t['decisionTimestamp'])
    if entry_timestamp:assert stamp(t['decisionTimestamp'])<=stamp(entry_timestamp)
    return {'PIT':{k:t[k] for k in ('ridgeScore','ridgeRank','selectorFeatureTimestamp','selectorFeatureAvailableAt','decisionTimestamp')},
            'evaluatorOnly':{k:t[k] for k in ('selectorOpportunity1','selectorOpportunity2','selectorOpportunity3','selectorOpportunity5','selectorMfePct','selectorMaePct')}}


def make_row(panel,anchor,cohort,reference,timestamp,bars,fixed,ares,source_status,meta,block):
    row={'panel':panel,'anchorId':anchor,'cohort':cohort,'referencePrice':reference,'entryTimestamp':timestamp,
         'symbol':meta['symbol'],'sessionDate':meta['sessionDate'],'block':block,'sourceReferenceStatus':source_status,
         'selector':meta['selector'],'fixed':fixed if fixed.get('status')=='EXIT_REFERENCE' else None,
         'fixedStatus':fixed.get('reason',fixed['status']),'candidateA':ares,
         'candidateAScope':'FROZEN_CURRENT_POPULATION' if panel=='CURRENT' else 'DIAGNOSTIC_OLD_REFERENCE_PROJECTION',
         'strict30':{'status':source_status} if not bars else strict30(bars)}
    if row['strict30']['status']!='COMPLETE':return row
    six=row['strict30'].pop('bars');m=path_metrics(six,reference);row['strict30'].update(m)
    row['bucket']=bucket(m['maePct']);row['strict30Bars']=six
    # Mechanical audit: future suffix cannot alter strict30 metrics.
    mutated=copy.deepcopy(bars)
    for b in mutated[6:]:b.update(missing=True,h=999,c=-999,l=-999)
    assert strict30(mutated)==strict30(bars)
    fcap=fixed['exitBar'] if fixed.get('status')=='EXIT_REFERENCE' else None
    windows={'STRICT30':six,'FIXED12_WINDOW':bars[:fcap] if fcap else None,
             'SESSION':bars if bars and all(cond.valid(b) for b in bars) else None}
    row['sessionComplete']=windows['SESSION'] is not None
    row['sessionTerminalPct']=bars[-1]['c'] if row['sessionComplete'] else None
    witnessed=any(cond.valid(b) and b['minutes']>30 and b['l']<m['maePct'] for b in bars)
    row['furtherSessionWorsening']=True if witnessed else False if row['sessionComplete'] else None
    row['deep']={}
    for d in (3,5,10):
        ix=next((i for i,b in enumerate(six) if b['l']<=-d),None)
        if ix is None:continue
        x={'threshold':d,'breach':location(six[ix],reference,'l'),'horizons':{},
           'relativeToCandidateAExit':exit_vs_breach(ares,bars,d)}
        for name,bs in windows.items():
            if bs is None:
                x['horizons'][name]={'status':'UNKNOWN_INCOMPLETE_WINDOW','classification':'INCONCLUSIVE'}
            else:
                assert all(cond.valid(b) for b in bs)
                a=after_anchor(bs,ix)
                x['horizons'][name]={'status':'COMPLETE',**a,'classification':classify(bs,ix,d),
                    'mfePct':max(0,max(b['h'] for b in bs)),
                    'recoveryWinnerThenNegativeTerminal':a['recovery']['3']['observed'] is True and bs[-1]['c']<0}
        x['observedSession']={'status':'OBSERVED_EVENTS_ONLY_NOT_COMPLETE_SESSION',**after_anchor(bars,ix,complete=row['sessionComplete'])}
        row['deep'][str(d)]=x
    # Post-exit realized-path LOW uses only pre-OPEN bars plus exit OPEN.
    if ares is not None:
        n=ares['exitBar'];held=bars[:n] if ares['status']=='FIXED12_FALLBACK' else bars[:n-1]
        row['heldMaeCandidateA']=min([0,ares['grossPct']]+[b['l'] for b in held])
        assert math.isclose(ares['netPct'],ares['grossPct']-.05,abs_tol=1e-12)
    else:row['heldMaeCandidateA']=None
    return row


def build():
    pins=read(BASE/'input-pins.json')
    for p,h in pins.items():assert sha(ROOT/p)==h,('PIN_CHANGED',p)
    for p,h in cond.PINS.items():assert sha(ROOT/p)==h,p
    for p,h in cond.PARITY_PINS.items():assert sha(cond.BASE/'entry-parity'/p)==h,p
    freeze=read(ROOT/'docs/evidence/phase57-msh-entry-long-v1-upstream-freeze/manifest.json')
    for p,h in freeze['evidencePins'].items():assert sha(ROOT/p)==h,p
    assert freeze['safety']==SAFETY and all(v is False for v in SAFETY.values())
    limitation=read(ROOT/'docs/evidence/phase57-exit-loss-state-study-v1/measurement/summary.json')
    assert limitation['status']=='EXIT_ARCHITECTURE_DEVELOPMENT_LIMIT_REACHED'
    oldids=read(ROOT/freeze['historicalEnterLedger']['path'])
    assert len(oldids)==277 and sha(ROOT/freeze['historicalEnterLedger']['path'])==freeze['historicalEnterLedger']['sha256']
    oldpaths=read(ROOT/'docs/evidence/phase57-long-exit-v345-paired/paths.json.gz')['events']
    assert {r['selectorEventId'] for r in oldids}=={r['selectorEventId'] for r in oldpaths}
    oldfixed=read(ROOT/'docs/evidence/phase57-long-exit-continuation-v1/replay-ledger.json')
    source=read(ROOT/cond.PATHS);assert source['freshAccess']==source['oosAccess']==source['providerRequests']==0
    paths={r['selectorEventId']:r for r in source['events']}
    feas={r['selectorEventId']:r for r in read(ROOT/'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz')}
    transfer={r['selectorEventId']:r for r in read(ROOT/'docs/evidence/phase57-long-only-current-entry-transfer-v1-events.ndjson.gz')}
    parity=read(cond.BASE/'entry-parity/ledger.ndjson.gz');ids=sorted(r['anchorId'] for r in parity)
    assert len(ids)==len(set(ids))==2743
    assert hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest()==cond.ANCHOR_SHA
    entries=read(cond.BASE/'ledger.json.gz')
    parityops={(r['anchorId'],op['eventType']):op for r in parity for op in (r['decision']['initialEvent'],r['decision']['secondaryEvent']) if op}
    assert len(entries)==len(parityops)==3284
    amap={(r['anchorId'],r['cohort']):r for r in read(ROOT/'docs/evidence/phase57-exit-loss-state-study-v1/measurement/ledger.json.gz')}
    assert len(amap)==1469
    sessions=sorted({r['sessionDate'] for r in entries});assert len(sessions)==76
    rows=[];fullbars={};audit=collections.Counter()
    for e in sorted(entries,key=lambda r:(r['anchorId'],r['cohort'])):
        anchor=e['anchorId'];op=e['opportunity'];key=(anchor,e['cohort'])
        assert op==parityops[key]
        adapted=cond.adapt(op,paths[anchor]);bars=adapted.get('future',[])
        meta={**e,'selector':selector_link(anchor,e['positionStartTimestamp'],feas,transfer)}
        f=e['fixed'];saved=amap.get(key);ares=saved['candidateA'] if saved else None
        if saved:
            assert saved['fixed']['netPct']==f['netPct'] and saved['fixed']['exitBar']==f['exitBar']
            assert f['status']=='EXIT_REFERENCE'
            audit['savedCurrentPairedExitMatches']+=1
        else:assert f['status']!='EXIT_REFERENCE'
        r=make_row('CURRENT',anchor,e['cohort'],op.get('referencePrice'),e['positionStartTimestamp'],bars,f,ares,
                   op['referenceStatus'],meta,1+sessions.index(e['sessionDate'])//19)
        if r['strict30']['status']=='COMPLETE':
            old=e['path']['30'];assert old['status']=='COMPLETE'
            assert math.isclose(r['strict30']['maePct'],old['maePct'],abs_tol=1e-12)
            assert math.isclose(r['strict30']['mfePct'],old['mfePct'],abs_tol=1e-12)
            audit['currentSavedStrict30Matches']+=1
        else:assert e['path']['30']['status']!='COMPLETE'
        rows.append(r);fullbars[('CURRENT',anchor,e['cohort'])]=bars
    for p in sorted(oldpaths,key=lambda r:r['selectorEventId']):
        anchor=p['selectorEventId'];f=oldfixed[anchor]['FIXED12'];bars=p['future']
        a=ca.policy(bars[:f['exitBar']],f) if f['status']=='EXIT_REFERENCE' else None
        if a:audit['legacyAUnchangedPolicyProjections']+=1
        meta={**p,'selector':selector_link(anchor,p['decisionTimestamp'],feas,transfer)}
        r=make_row('LEGACY',anchor,OLD,p['decisionPrice'],p['decisionTimestamp'],bars,f,a,
                   'FROZEN_DECISION_CLOSE_REFERENCE',meta,1+sessions.index(p['sessionDate'])//19)
        assert (r['strict30']['status']=='COMPLETE')==p['horizons']['30']['available']
        if r['strict30']['status']=='COMPLETE':
            assert math.isclose(r['strict30']['maePct'],p['horizons']['30']['maePct'],abs_tol=1e-10)
            audit['legacySavedStrict30Matches']+=1
        rows.append(r);fullbars[('LEGACY',anchor,OLD)]=bars
    old=[r['strict30']['maePct'] for r in rows if r['panel']=='LEGACY' and r['strict30']['status']=='COMPLETE']
    assert len(old)==181
    for k in ('median','p05','min'):assert math.isclose(dist(old)[k],freeze['strict30mMAE'][k],abs_tol=1e-10)
    assert len({(r['panel'],r['anchorId'],r['cohort']) for r in rows})==3561
    audit['selectorPITIdentityChecks']=len(rows);audit['strict30FutureSuffixChecks']=sum(r['strict30']['status']=='COMPLETE' for r in rows)
    return rows,fullbars,dict(audit),pins,freeze


def bool_rate(values):
    known=[x for x in values if x is not None]
    return {**rate(sum(known),len(known)),'population':len(values),'unknown':len(values)-len(known)}


def event_rates(items):
    return {str(k):bool_rate([x['recovery'][str(k)]['observed'] for x in items]) for k in LEVELS}


def followup_summary(items):
    ok=[x for x in items if x.get('status','COMPLETE')=='COMPLETE']
    out={'population':len(items),'observed':len(ok),'unknown':len(items)-len(ok),
        'classes':dict(collections.Counter(x['classification'] for x in items if 'classification' in x)),
        'recovery':event_rates(ok),'laterCloseReclaim':bool_rate([x['laterCloseReclaim'] for x in ok]),
        'triggerBarCloseReclaimKnown':bool_rate([x['triggerBarCloseReclaimKnown'] for x in ok]),
        'laterPositiveClose':bool_rate([x['laterPositiveClose'] for x in ok]),
        'additionalDrop2':bool_rate([x['additionalDrop2'] for x in ok]),'additionalDrop5':bool_rate([x['additionalDrop5'] for x in ok]),
        'terminalPct':perf([x['terminalPct'] for x in ok]),'mfeAfterAnchorPct':dist([x['mfeAfterAnchorPct'] for x in ok]),
        'recoveryThenNegativeTerminal':sum(x.get('recoveryWinnerThenNegativeTerminal',False) for x in ok),
        'reclaimMinutesFromEntry':dist([x['reclaimTime']['entryMinutesInterval'][1] for x in ok if x['reclaimTime']]),
        'plus3MinutesUpperFromEntry':dist([x['recovery']['3']['first']['entryMinutesInterval'][1] for x in ok if x['recovery']['3']['first']]),
        'plus5MinutesUpperFromEntry':dist([x['recovery']['5']['first']['entryMinutesInterval'][1] for x in ok if x['recovery']['5']['first']]),
        'sameBarUnknown3':sum(x['recovery']['3']['triggerBarHighOrder']=='UNKNOWN_INTRABAR_ORDER' for x in ok),
        'sameBarUnknown5':sum(x['recovery']['5']['triggerBarHighOrder']=='UNKNOWN_INTRABAR_ORDER' for x in ok)}
    return out


def verdict(counts,n):
    if n<30 or counts.get('INCONCLUSIVE',0)>n/3:return 'INCONCLUSIVE'
    rw,cf=counts.get('RECOVERY_WINNER',0),counts.get('CONTINUED_FAILURE',0)
    if rw/n>=2/3:return 'DEEP_MAE_PRIMARILY_RECOVERY_PATH'
    if cf/n>=2/3:return 'DEEP_MAE_PRIMARILY_ENTRY_FAILURE'
    if rw>=5 and cf>=5 and rw/n>=.1 and cf/n>=.1:return 'DEEP_MAE_MIXED_RECOVERY_AND_FAILURE'
    return 'INCONCLUSIVE'


def summarize_group(rs,population):
    paired=[r for r in rs if r['fixed'] is not None and r['candidateA'] is not None]
    return {'n':len(rs),'ofStrictObserved':rate(len(rs),population['strict']),
        'ofAllOpportunities':rate(len(rs),population['all']),
        'maePct':dist([r['strict30']['maePct'] for r in rs]),'mfePct':dist([r['strict30']['mfePct'] for r in rs]),
        'strict30TerminalPct':perf([r['strict30']['terminalPct'] for r in rs]),
        'strict30GivebackPP':dist([r['strict30']['givebackPP'] for r in rs]),
        'anyTimeReach30':{str(k):rate(sum(r['strict30']['anyTimeReach'][str(k)] for r in rs),len(rs)) for k in LEVELS},
        'afterGlobal30Mae':followup_summary([r['strict30']['afterGlobalMae'] for r in rs]),
        'ordering':dict(collections.Counter(r['strict30']['ordering'] for r in rs)),
        'furtherSessionWorsening':bool_rate([r['furtherSessionWorsening'] for r in rs]),
        'sessionTerminalPct':perf([r['sessionTerminalPct'] for r in rs]),
        'pairedExitN':len(paired),'exitCensoredN':len(rs)-len(paired),
        'fixed12':perf([r['fixed']['netPct'] for r in paired]),
        'candidateA':perf([r['candidateA']['netPct'] for r in paired]),
        'selectorScore':dist([r['selector']['PIT']['ridgeScore'] for r in rs]),
        'selectorRankCounts':dict(collections.Counter(r['selector']['PIT']['ridgeRank'] for r in rs)),
        'selectorFutureOpportunityEvaluatorOnly':{str(k):dist([r['selector']['evaluatorOnly']['selectorOpportunity'+str(k)] for r in rs]) for k in LEVELS}}


def deep_summary(rs,d,population):
    rs=[r for r in rs if str(d) in r['deep']]
    out=summarize_group(rs,population);out['horizons']={}
    for h in HORIZONS:
        items=[r['deep'][str(d)]['horizons'][h] for r in rs];v=followup_summary(items)
        v['verdictAllDeepIncludingUnknown']=verdict(v['classes'],len(items))
        complete=[i for i in items if i['status']=='COMPLETE'];counts=dict(collections.Counter(i['classification'] for i in complete))
        v['verdictCompleteSubsetOnly']=verdict(counts,len(complete));v['completeClassCounts']=counts
        out['horizons'][h]=v
    out['relativeToCandidateAExit']=dict(collections.Counter(r['deep'][str(d)]['relativeToCandidateAExit'] for r in rs))
    out['observedSessionRecoveryOnly']=event_rates([r['deep'][str(d)]['observedSession'] for r in rs])
    out['symbolCounts']=dict(collections.Counter(r['symbol'] for r in rs))
    out['sessionCounts']=dict(collections.Counter(r['sessionDate'] for r in rs))
    out['classTransitions30ToFixed12']=dict(collections.Counter(r['deep'][str(d)]['horizons']['STRICT30']['classification']+' -> '+r['deep'][str(d)]['horizons']['FIXED12_WINDOW']['classification'] for r in rs))
    out['pairedExitByStrict30Class']={label:{'n':len(sub:=[r for r in rs if r['deep'][str(d)]['horizons']['STRICT30']['classification']==label]),
        'fixed12':perf([r['fixed']['netPct'] for r in sub if r['fixed']]),'candidateA':perf([r['candidateA']['netPct'] for r in sub if r['candidateA']])} for label in CLASSES}
    return out


def score_auc(rs):
    a=[r['selector']['PIT']['ridgeScore'] for r in rs if r['strict30']['maePct']<=-3]
    b=[r['selector']['PIT']['ridgeScore'] for r in rs if r['strict30']['maePct']>-3]
    return {'deepN':len(a),'nondeepN':len(b),'aucHigherScoreDeep':sum((x>y)+.5*(x==y) for x in a for y in b)/(len(a)*len(b)) if a and b else None}


def panel_summary(rows):
    rs=[r for r in rows if r['strict30']['status']=='COMPLETE'];p={'all':len(rows),'strict':len(rs)}
    out={'population':p,'coverage':dict(collections.Counter(r['strict30']['status'] for r in rows)),
         'sessions':len({r['sessionDate'] for r in rows}),'overall':summarize_group(rs,p),
         'buckets':{k:summarize_group([r for r in rs if r['bucket']==k],p) for k in BUCKETS},
         'deep':{str(d):deep_summary(rs,d,p) for d in (3,5,10)},
         'selectorRank':{str(k):summarize_group([r for r in rs if r['selector']['PIT']['ridgeRank']==k],p) for k in range(1,6)},
         'selectorScoreAUC':score_auc(rs)}
    counts=collections.Counter(r['symbol'] for r in rows);top=sorted(counts,key=lambda k:(-counts[k],k))[:3]
    groups={**{'block'+str(b):[r for r in rs if r['block']==b] for b in range(1,5)},
            'excludeFrequencyTop3':[r for r in rs if r['symbol'] not in top],
            'fullUnderlyingMinutes':[r for r in rs if r['strict30']['fullUnderlyingMinutes']]}
    out['robustness']={k:{'n':len(v),'deep3':deep_summary(v,3,{'all':len(v),'strict':len(v)}),'selectorScoreAUC':score_auc(v)} for k,v in groups.items()}
    out['excludedFrequencySymbols']=top
    return out


def build_summary(rows,fullbars,audit,pins,freeze):
    current=[r for r in rows if r['panel']=='CURRENT'];legacy=[r for r in rows if r['panel']=='LEGACY']
    panels={'CURRENT_OVERALL':panel_summary(current),'CURRENT_INITIAL':panel_summary([r for r in current if r['cohort']==INITIAL]),
            'CURRENT_DIP':panel_summary([r for r in current if r['cohort']==DIP]),'LEGACY_ENTER':panel_summary(legacy)}
    deep=panels['CURRENT_OVERALL']['deep']['3'];primary=deep['horizons']['STRICT30']['verdictAllDeepIncludingUnknown']
    fixed=deep['horizons']['FIXED12_WINDOW'];final=primary;resolution='STRICT30_PRIMARY'
    adequate=fixed['observed']>=max(30,deep['n']/2)
    if primary in ('DEEP_MAE_PRIMARILY_RECOVERY_PATH','DEEP_MAE_PRIMARILY_ENTRY_FAILURE') and adequate and fixed['verdictCompleteSubsetOnly']!=primary:
        mixed=False
        for h,denom in ((deep['horizons']['STRICT30'],deep['n']),(fixed,fixed['observed'])):
            cc=h['completeClassCounts'];rw=cc.get('RECOVERY_WINNER',0);cf=cc.get('CONTINUED_FAILURE',0)
            mixed|=rw>=5 and cf>=5 and min(rw,cf)/denom>=.1
        final='DEEP_MAE_MIXED_RECOVERY_AND_FAILURE' if mixed else 'INCONCLUSIVE';resolution='HORIZON_DISAGREEMENT'
    worst={}
    for name,rr in [('CURRENT',current),('LEGACY',legacy)]:
        observed=[r for r in rr if r['strict30']['status']=='COMPLETE'];minimum=min(r['strict30']['maePct'] for r in observed)
        worst[name]=[]
        for r in observed:
            if r['strict30']['maePct']!=minimum:continue
            b=fullbars[(name,r['anchorId'],r['cohort'])]
            prices=[{**x,**{k+'Price':r['referencePrice']*(1+x[k]/100) for k in ('o','h','l','c')}} if cond.valid(x) else x for x in b]
            matched=[{'cohort':x['cohort'],'entryTimestamp':x['entryTimestamp'],'referencePrice':x['referencePrice'],'strict30':x['strict30'],
                      'fixed':x['fixed'],'candidateA':x['candidateA']} for x in current if x['anchorId']==r['anchorId']]
            worst[name].append({'record':r,'fullSavedPath':prices,'sameAnchorCurrentReferences':matched})
    result={'schemaVersion':1,'status':'STRICT30_MAE_ATTRIBUTION_COMPLETE','sourceHead':START_HEAD,'protocolCommit':PROTOCOL_COMMIT,
        'sourceIdentity':{'selectorFreezeCommit':freeze['selectorFreezeCommit'],'selectorPayloadSHA':freeze['selectorPayloadSHA'],
            'newEntryFreezeCommit':'6fabde7dfe208e19d5611e0a290b4df6724e562e','currentAnchorSHA256':cond.ANCHOR_SHA,
            'legacyEnterSHA256':freeze['historicalEnterLedger']['sha256'],'quotedMaePopulation':'LEGACY_MSH_V1_277_ENTER_STRICT181'},
        'panels':panels,'finalAttributionVerdict':final,'verdictResolution':resolution,'strict30Verdict':primary,
        'fixed12CompleteFollowupVerdict':fixed['verdictCompleteSubsetOnly'],'fixed12FollowupCoverageAdequate':adequate,
        'worstCases':worst,'audit':audit,'sourcePins':pins,'safety':SAFETY,
        'scope':{k:0 for k in ('selectorChanges','entryChanges','exitChanges','modelFits','thresholdOptimization','providerRequests','freshAccess','oosAccess','minuteResearch','capitalTuning','portfolioTuning','mainMerge')}}
    return result


def run(out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    rows,fullbars,audit,pins,freeze=build();summary=build_summary(rows,fullbars,audit,pins,freeze)
    out.mkdir(parents=True,exist_ok=False)
    objects={'summary.json':summary,'ledger.json.gz':rows,'worst-paths.json':summary['worstCases']}
    for name,x in objects.items():
        data=encoded(x);(out/name).write_bytes(gzip.compress(data,mtime=0) if name.endswith('.gz') else data)
    manifest={'sourcePins':pins,'codePins':{'scripts/phase57_strict30_mae_attribution.py':sha(Path(__file__))},
              'outputPins':{name:sha(out/name) for name in objects},'protocolCommit':PROTOCOL_COMMIT,'safety':SAFETY}
    (out/'manifest.json').write_bytes(encoded(manifest))
    print(json.dumps({'verdict':summary['finalAttributionVerdict'],'panels':{k:{'n':v['population'],'mae':v['overall']['maePct']} for k,v in summary['panels'].items()},'audit':audit},indent=2))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);run(p.parse_args().out)
