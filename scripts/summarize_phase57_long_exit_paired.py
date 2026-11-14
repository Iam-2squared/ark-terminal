"""Aggregate newly recovered fixed277 paths; never score Entry or fit EXIT."""
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

LEVELS=[1,2,3,5]
def quantile(xs,q):
    if not xs:return None
    a=sorted(xs);p=(len(a)-1)*q;i=int(p);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(p-i)
def dist(xs):
    xs=[x for x in xs if x is not None and math.isfinite(x)]
    return {'n':len(xs),'mean':sum(xs)/len(xs) if xs else None,'median':quantile(xs,.5),'p05':quantile(xs,.05),'p25':quantile(xs,.25),'p75':quantile(xs,.75),'p90':quantile(xs,.9),'min':min(xs) if xs else None,'max':max(xs) if xs else None}
def rate(n,d):return {'count':n,'denominator':d,'ratePct':100*n/d if d else None}
def timing(xs):
    xs=[x for x in xs if x is not None]
    return {'distribution':dist(xs),'exclusiveBuckets':{'<=5m':sum(x<=5 for x in xs),'5-10m':sum(5<x<=10 for x in xs),'10-15m':sum(10<x<=15 for x in xs),'15-30m':sum(15<x<=30 for x in xs),'>30m':sum(x>30 for x in xs)}}
def crossing(rows,field,bound,up):return next((i for i,b in enumerate(rows) if (b[field]>=bound if up else b[field]<=bound)),None)
def classify(e):
    p=e['horizons']['SESSION_END'];rows=e['future']
    if not p['available']:return 'G_UNKNOWN'
    up=crossing(rows,'h',1,True);down=crossing(rows,'l',-1,False)
    if up is not None and up==down:return 'G_UNKNOWN'
    early=down is not None and rows[down]['minutes']<=15
    later=early and any(b['h']>=1 for b in rows[down+1:])
    if later:return 'A_EARLY_ADVERSE_THEN_RECOVERY'
    if early and not later and p['returnPct']<=-1:return 'B_EARLY_FAILURE'
    if p['mfePct']>=1 and p['returnPct']<=0:return 'D_WINNER_THEN_GIVEBACK'
    if up is not None and rows[up]['minutes']<=30 and p['returnPct']>0:return 'C_FAST_WINNER'
    if up is not None and rows[up]['minutes']>30 and p['returnPct']>0:return 'E_SLOW_WINNER'
    return 'F_CHOP_NO_EDGE'
def horizon_summary(events,key):
    es=[e for e in events if e['horizons'][key]['available']];ps=[e['horizons'][key] for e in es]
    recovery={}
    for level in [-1,-2,-3,-5,-10]:
        cohort=[e for e in es if e['horizons'][key]['maePct']<=level];times=[];later_mfe=[];nrec=0;later_hits={str(k):0 for k in LEVELS}
        for e in cohort:
            rows=e['future'] if key=='SESSION_END' else [b for b in e['future'] if b['minutes']<=int(key)]
            ix=crossing(rows,'l',level,False);later=rows[ix+1:];rec=next((b for b in later if b['c']>=0),None)
            if rec:nrec+=1;times.append(rec['minutes']-rows[ix]['minutes'])
            if later:
                high=max(b['h'] for b in later);later_mfe.append(max(0,high))
                for k in LEVELS:later_hits[str(k)]+=int(high>=k)
        recovery[str(level)]={'adverse':rate(len(cohort),len(es)),'laterCompletedCloseReclaim':rate(nrec,len(cohort)),'recoveryClockMinutesAfterAdverse':dist(times),'laterMfePct':dist(later_mfe),'laterOpportunityCounts':later_hits,'horizonCloseReturnPct':dist([e['horizons'][key]['returnPct'] for e in cohort]),'sessionEndReturnWhenAvailable':dist([e['horizons']['SESSION_END']['returnPct'] for e in cohort if e['horizons']['SESSION_END']['available']])}
    return {'availability':rate(len(es),len(events)),'unavailableReasons':dict(collections.Counter(e['horizons'][key]['reason'] for e in events if not e['horizons'][key]['available'])),'maePct':dist([p['maePct'] for p in ps]),'mfePct':dist([p['mfePct'] for p in ps]),'returnPct':dist([p['returnPct'] for p in ps]),'mfeAtLeast':{str(k):rate(sum(p['mfePct']>=k for p in ps),len(ps)) for k in LEVELS},'ordering':dict(collections.Counter(p['ordering'] for p in ps)),'timeToMfe':timing([p['timeToMfeMinutes'] for p in ps]),'timeToMae':timing([p['timeToMaeMinutes'] for p in ps]),'sparsePathCount':sum(p['sparseMinuteBars']>0 for p in ps),'adverseRecovery':recovery}
def concentration(rows,nets):
    positive=sorted([max(0,x) for x in nets],reverse=True);absolute=sorted(map(abs,nets),reverse=True)
    shares=lambda a:{str(k):sum(a[:k])/sum(a) if sum(a)>0 else None for k in [1,3,5]}
    grouped={}
    for key in ['symbol','sessionDate']:
        g=collections.defaultdict(list)
        for e,x in zip(rows,nets):g[e[key]].append(x)
        total=sum(abs(x) for x in nets)
        grouped[key]=sorted([{'identity':k,'trades':len(v),'netSumPctPoints':sum(v),'absoluteReturnShare':sum(abs(x) for x in v)/total if total else None} for k,v in g.items()],key=lambda x:x['absoluteReturnShare'] or 0,reverse=True)
    return {'positiveProfitTop1Top3Top5':shares(positive),'absoluteReturnTop1Top3Top5':shares(absolute),'grouped':grouped}
def arm_metrics(es,key):
    ps=[e['horizons'][key] for e in es];gross=[p['returnPct'] for p in ps];net=[x-.05 for x in gross];wins=[x for x in net if x>0];loss=[x for x in net if x<0]
    eq=peak=dd=0
    for x in net:eq+=x;peak=max(peak,eq);dd=min(dd,eq-peak)
    rows=[e['future'][:12] if key=='FIXED_12' else e['future'] for e in es]
    opportunity={}
    for k in LEVELS:
        cohort=[i for i,e in enumerate(es) if e['horizons']['SESSION_END']['mfePct']>=k]
        premature=sum(crossing(es[i]['future'],'h',k,True)>=len(rows[i]) for i in cohort)
        opportunity[str(k)]={'availableWinners':len(cohort),'grossRealizedAtLeast':rate(sum(gross[i]>=k for i in cohort),len(cohort)),'netRealizedAtLeast':rate(sum(net[i]>=k for i in cohort),len(cohort)),'prematureExitBeforeLaterFirstTouch':rate(premature,len(cohort)),'winnerFinalNetPct':dist([net[i] for i in cohort])}
    recovered=[i for i,e in enumerate(es) if e['future'][0]['c']<0 and any(b['c']>=0 for b in e['future'][1:])]
    losers=[i for i,e in enumerate(es) if e['horizons']['SESSION_END']['returnPct']-.05<0]
    return {'n':len(es),'grossSumPctPoints':sum(gross),'netSumPctPoints':sum(net),'netTradePct':dist(net),'winRate':rate(len(wins),len(net)),'profitFactor':sum(wins)/abs(sum(loss)) if loss else None,'profitFactorNoLossDenominator':not bool(loss),'maxDrawdownRealizedTradeOrderProxyPctPoints':dd,'drawdownNotPortfolio':True,'lossTradePct':dist(loss),'realizedLossBuckets':{str(k):rate(sum(x<=k for x in net),len(net)) for k in [-1,-2,-3,-5,-10]},'holdingBars':dist([len(r) for r in rows]),'holdingClockMinutes':timing([r[-1]['minutes'] for r in rows]),'sessionEndExposure':rate(sum(len(r)==len(e['future']) for r,e in zip(rows,es)),len(es)),'availableMfePct':dist([e['horizons']['SESSION_END']['mfePct'] for e in es]),'preExitMaePct':dist([p['maePct'] for p in ps]),'grossAvailableMfeCapture':dist([x/e['horizons']['SESSION_END']['mfePct'] for x,e in zip(gross,es) if e['horizons']['SESSION_END']['mfePct']>0]),'netAvailableMfeCapture':dist([x/e['horizons']['SESSION_END']['mfePct'] for x,e in zip(net,es) if e['horizons']['SESSION_END']['mfePct']>0]),'captureUndefinedMfeNonpositive':sum(e['horizons']['SESSION_END']['mfePct']<=0 for e in es),'givebackFromAvailableMfePctPoints':dist([e['horizons']['SESSION_END']['mfePct']-x for x,e in zip(gross,es)]),'opportunityRealization':opportunity,'adverseHandling':{'completedCloseAdverseThenRecoveryCount':len(recovered),'recoveredWinnerPreserved':rate(sum(net[i]>0 for i in recovered),len(recovered)),'falseEarlyExitBeforeLaterCloseRecovery':sum(net[i]<0 and len(rows[i])<len(es[i]['future']) and any(b['c']>=0 for b in es[i]['future'][len(rows[i]):]) for i in recovered),'sessionEndLoserCount':len(losers),'lossReductionVsSessionEndPctPoints':dist([net[i]-(es[i]['horizons']['SESSION_END']['returnPct']-.05) for i in losers]),'loserHeldToSessionEnd':sum(len(rows[i])==len(es[i]['future']) for i in losers)},'concentration':concentration(es,net)}
def main(p,out):
    raw=gzip.open(p,'rb').read() if p.endswith('.gz') else Path(p).read_bytes();d=json.loads(raw);es=d['events']
    assert len(es)==277 and len({e['symbolSessionId'] for e in es})==277
    assert all(e['direction']=='LONG' and not e['pairedFiveArmEligible'] and e['v3'] is None and e['v4'] is None and e['v5'] is None for e in es)
    pair=sorted([e for e in es if e['horizons']['SESSION_END']['available'] and e['horizons']['FIXED_12']['available']],key=lambda e:(e['decisionTimestamp'],e['symbol'],e['selectorEventId']))
    for e in es:e['pathType']=classify(e)
    first=[e['future'][0] for e in es if e['future'] and not e['future'][0]['missing'] and e['future'][0]['minutes']==5]
    blocked={'n':0,'status':'NOT_MEASURED_CAUSAL_INPUT_BLOCKED','netSumPctPoints':None,'grossSumPctPoints':None,'profitFactor':None,'comparisonPermitted':False}
    result={'verdict':'EXIT_ARCHITECTURE_INCONCLUSIVE','measurementStatus':'PATH_DIAGNOSTIC_COMPLETE_FIVE_ARM_PAIRED_REPLAY_BLOCKED','pathArtifactUncompressedSHA':hashlib.sha256(raw).hexdigest(),'contractSHA':d['contractSHA'],'enterIdentitySHA':d['enterIdentitySHA'],'entryCount':277,'sessionCount':len(d['sources']),'exposure':'DIRECT_ENTRY_DEVELOPMENT_IN_SAMPLE','horizons':{k:horizon_summary(es,k) for k in ['5','10','15','30','SESSION_END']},'pathTypes':dict(collections.Counter(e['pathType'] for e in es)),'immediateAdverse':{'first5mCompletedCloseNegative':rate(sum(b['c']<0 for b in first),len(first)),'first5mLowBelowEntry':rate(sum(b['l']<0 for b in first),len(first))},'pairedReferenceOnly':{'n':len(pair),'excluded':277-len(pair),'identities':[e['selectorEventId'] for e in pair],'arms':{k:arm_metrics(pair,k) for k in ['FIXED_12','SESSION_END']}},'standaloneFixedAvailability':rate(sum(e['horizons']['FIXED_12']['available'] for e in es),277),'completeFiveArmPairs':0,'requestedExitArms':{k:blocked for k in ['v3','v4','v5']},'blockers':['PINNED_ANALOG_WINDOW_AFTER_ENTRY','NO_REPRODUCIBLE_CAUSAL_V3_V4_CONTINUATION','V5_BAR5_FINAL_VS_BAR6_RUNTIME_AND_TRUNCATED_TRACE_FALLBACK'],'sourceIntegrity':{'sourceSessionCount':len(d['sources']),'priorExitResultUsed':False},'counts':d['counts'],'safety':d['safety']}
    root=Path(out);root.mkdir(parents=True,exist_ok=True)
    for name,value in [('summary.json',result),('entry-path-classification.json',[{'selectorEventId':e['selectorEventId'],'pathType':e['pathType'],'pairedFiveArmEligible':False,'blockedReason':e['blockedReason']}for e in es])]:
        f=root/name
        if f.exists():raise RuntimeError('REFUSE_OVERWRITE:'+str(f))
        f.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'entries':277,'pairedReferenceOnly':len(pair),'completeFiveArmPairs':0,'verdict':result['verdict']}))
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
