"""Frozen Development-only path diagnostic; no policy fitting or optimization."""
from __future__ import annotations
import argparse, collections, datetime as dt, gzip, hashlib, json, math, statistics
from pathlib import Path
import numpy as np
import pandas as pd
from scripts import phase57_selector_economic_alpha as old

ROOT=old.ROOT
BASE=ROOT/'docs/evidence/phase57-selector-full-day-path-anatomy-v1'
PROTOCOL=BASE/'protocol.json'
MEMBERSHIP=old.BASE/'measurement/membership-ledger.json.gz'
H=(5,10,15,30,60,90,120)
ARMS=old.ARMS
COST=.05
read,write,sha=old.read,old.write,old.sha

def protocol():
    p=read(PROTOCOL)
    assert p['id']=='PHASE57_FROZEN_SELECTOR_FULL_DAY_PATH_ANATOMY_V1'
    assert p['horizonsMinutes']==[0,*H] and p['commonCohortsMinutes']==[60,90,120]
    assert p['cost']['canonicalRoundTripPctPoints']==COST
    assert p['statistics']['bootstrapReplicates']==10000
    assert all(v is False for v in p['safety'].values())
    assert p['sealed']['newProviderRequests']==0
    assert all(v is False for k,v in p['sealed'].items() if k!='newProviderRequests')
    for f,h in p['sourcePins'].items(): assert sha(ROOT/f)==h,f
    return p

def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [clean(v) for v in x]
    if isinstance(x,np.generic): x=x.item()
    if isinstance(x,float) and not math.isfinite(x): return None
    return x

def digest(ids): return hashlib.sha256(old.encoded(sorted(ids))).hexdigest()

def band(price):
    for ceiling,label in [(100,'(75,100]'),(200,'(100,200]'),(500,'(200,500]'),(1000,'(500,1000]')]:
        if price<=ceiling:return label
    return '(1000,infinity)'

def pit_ranks(frame):
    frame=frame.copy()
    frame['scoreDecile']=np.ceil(10*frame.savedV1Score.rank(method='average',pct=True)).astype(int)
    rank=frame.decisionVolatilityPct.rank(method='average',pct=True)
    frame['volatilityStratum']=np.select([rank.le(1/3),rank.le(2/3),rank.notna()],['LOW','MID','HIGH'],default='UNKNOWN')
    return frame

def dist(values):
    a=np.asarray([v for v in values if v is not None and math.isfinite(v)],float)
    if not len(a):return {'n':0,'mean':None,'median':None,'positiveRate':None,'PF':None}
    loss=-a[a<0].sum();sd=a.std();z=(a-a.mean())/sd if sd else np.zeros(len(a))
    return clean({'n':len(a),'mean':a.mean(),'median':np.median(a),'positiveRate':(a>0).mean(),
        'PF':a[a>0].sum()/loss if loss else None, **{f'p{q:02}':np.quantile(a,q/100) for q in [1,5,10,25,75,90,95,99]},
        'skewness':np.mean(z**3) if sd else None,'excessKurtosis':np.mean(z**4)-3 if sd else None})

BOOT={}
def cluster(values, family=1):
    # Input is one equal-weight estimate per session, never raw overlapping rows.
    a=np.asarray(list(values.values()),float);n=len(a)
    result={'clusters':n,'sessionEqualMean':float(a.mean()) if n else None,'clusterCI95':[None,None],
            'simultaneousCI95':[None,None],'ciWidth':None,'MDE80':None,'sessionValues':values}
    if n<2:return result
    if n not in BOOT: BOOT[n]=np.random.default_rng(20260919).integers(0,n,size=(10000,n))
    boot=a[BOOT[n]].mean(axis=1)
    ci=np.quantile(boot,[.025,.975]);sim=np.quantile(boot,[.025/family,1-.025/family])
    result.update(clusterCI95=ci.tolist(),simultaneousCI95=sim.tolist(),ciWidth=float(ci[1]-ci[0]),
        MDE80=float((1.959963984540054+.8416212335729143)*a.std(ddof=1)/math.sqrt(n)))
    return result

def by_session(rows,field):
    d=collections.defaultdict(list)
    for r in rows:d[r['sessionDate']].append(r[field])
    return {k:statistics.mean(v) for k,v in sorted(d.items())}

def regular_slots(decision,end):
    t=decision;out=[]
    while t<end:
        m=t.hour*60+t.minute
        if 540<=m<690 or 750<=m<(900 if str(t.date())<'2024-11-05' else 930):out.append(t)
        t+=dt.timedelta(minutes=5)
    return out

def summarize_window(bars,decision,entry,end):
    if entry['status']!='AVAILABLE':return {'status':entry['status']}
    if old.timestamp(entry['timestamp'])>=end:return {'status':'NONPOSITIVE_HOLDING_WINDOW'}
    expected=regular_slots(decision,end)
    if not expected:return {'status':'NO_REGULAR_BAR'}
    mapping={b['start']:b for b in bars}
    if any(t not in mapping or not mapping[t]['valid'] for t in expected):return {'status':'INCOMPLETE_PATH'}
    selected=[mapping[t] for t in expected]
    if selected[-1]['end']!=end:return {'status':'NO_EXACT_COMPLETED_CLOSE'}
    price=entry['price'];hi=[100*(b['h']/price-1) for b in selected];lo=[100*(b['l']/price-1) for b in selected]
    mfe=max(0,max(hi));mae=min(0,min(lo));gross=100*(selected[-1]['c']/price-1)
    def timing(i):
        b=selected[i];return [(b[k]-decision).total_seconds()/60 for k in ['start','end']]
    ih=hi.index(max(hi));il=lo.index(min(lo))
    first={str(t):next((timing(i) for i,v in enumerate(hi) if v>=t-1e-10),None) for t in [1,2,3,5]}
    return {'status':'AVAILABLE','gross':gross,'net':gross-COST,'MFE':mfe,'MAE':mae,'absMAE':-mae,
        'balance':mfe+mae,'giveback':mfe-gross,'peakInterval':timing(ih) if mfe>0 else None,
        'troughInterval':timing(il) if mae<0 else None,'firstHitIntervals':first,
        'ordering':'NO_TWO_SIDED_EXCURSION' if mfe<=0 or mae>=0 else 'UNKNOWN_INTRABAR_ORDER' if ih==il else 'MFE_FIRST' if ih<il else 'MAE_FIRST',
        'sparseBars':sum((b.get('observedMinutes') or 0)<5 for b in selected),'barCount':len(selected),
        'elapsedMinutes':(end-decision).total_seconds()/60}

def evaluate(path):
    bars=old.materialize_path(path);decision=old.timestamp(path['decisionTimestamp'])
    entry=old.entry_at_or_after(bars,decision)
    end=decision.replace(hour=15,minute=0 if path['sessionDate']<'2024-11-05' else 30)
    outcomes={'0':{'status':'REFERENCE_ONLY','gross':0}}
    m=decision.hour*60+decision.minute;close=end.hour*60+end.minute
    for h in H:
        if m+h>close:result={'status':'SESSION_END'}
        elif 690<=m<750 or m<690<m+h:result={'status':'LUNCH_BREAK'}
        else:result=summarize_window(bars,decision,entry,decision+dt.timedelta(minutes=h))
        outcomes[str(h)]=result
    outcomes['SESSION_END']=summarize_window(bars,decision,entry,end)
    return {'selectorEventId':path['selectorEventId'],'sessionDate':path['sessionDate'],'symbol':path['symbol'],
        'decisionTimestamp':path['decisionTimestamp'],'decisionPrice':path['decisionPrice'],'outcomes':outcomes}

def prepare(dataset,out):
    protocol();out=Path(out);out.mkdir(parents=True,exist_ok=False)
    frame,manifest=old.corrected.load(Path(dataset));eligible=old.eligibility.eligible_universe(frame)
    eligible=eligible[eligible.decisionPrice.gt(75)].copy();del frame
    assert len(eligible)==1736930 and eligible.sessionDate.nunique()==76
    membership=read(MEMBERSHIP);ids=set(x['selectorEventId'] for x in membership['new'])
    assert all(len(v)==3800 for v in membership['arms'].values())
    expected={arm:collections.defaultdict(list) for arm in ARMS}
    lookup={r['selectorEventId']:r for r in membership['new']}
    for arm,events in membership['arms'].items():
        for eid in events:
            r=lookup[eid];expected[arm][(r['sessionDate'],r['decisionTimeJst'])].append(eid)
    context={};universe_context=[];files=[]
    fields=['decisionPrice','savedV1Score','momentum30Pct','currentReturnPct','decisionVolatilityPct','logCumulativeTurnover','volumeAccelerationRatio','liquidityBucket','segment','scoreDecile','volatilityStratum']
    for date,day in eligible.groupby('sessionDate',sort=True):
        parts=[]
        for (session,time),g in day.groupby(old.corrected.KEYS,sort=True):
            g=pit_ranks(g);g['selectorEventId']=[old.event_id(session,time,str(s)) for s in g.symbol]
            orders=[g.sort_values(['savedV1Score','symbol'],ascending=[False,True]).head(5),
                g.loc[sorted(g.index,key=lambda i:old.random_key(20260919,session,time,g.at[i,'symbol']))[:5]],
                g.sort_values(['momentum30Pct','symbol'],ascending=[False,True]).head(5)]
            for arm,ordered in zip(ARMS,orders):assert ordered.selectorEventId.tolist()==expected[arm][(session,time)],(arm,session,time)
            for r in g[g.selectorEventId.isin(ids)].to_dict('records'):
                context[r['selectorEventId']]=clean({k:r[k] for k in fields})
            universe_context.append({'sessionDate':session,'decisionTimeJst':time,'n':len(g),
                'numeric':{k:dist(g[k].tolist()) for k in fields[:7]},
                'categorical':{k:{str(a):int(b) for a,b in g[k].value_counts().items()} for k in fields[7:]}})
            parts.append(g[['sessionDate','symbol','decisionTimeJst','decisionPrice','savedV1Score','scoreDecile']])
        target=out/f'{date}.tsv';pd.concat(parts).to_csv(target,sep='\t',index=False)
        files.append({'sessionDate':date,'path':target.name,'sha256':sha(target)})
    assert set(context)==ids
    write(out/'context.json',{'context':context,'universe':universe_context,'inputManifestSHA256':manifest['_sha256'],'files':files})
    print(json.dumps({'status':'PIT_CONTEXT_AND_MEMBERSHIP_PARITY_PASS','universeRows':len(eligible),'sessions':76,'unionRows':len(ids)}))

def flatten(events,ids,h):
    return [{**events[i]['outcomes'][str(h)],'selectorEventId':i,'sessionDate':events[i]['sessionDate'],
        'symbol':events[i]['symbol'],'decisionTimestamp':events[i]['decisionTimestamp']} for i in ids if events[i]['outcomes'][str(h)]['status']=='AVAILABLE']

def common_ids(events,ids,max_h):
    return [i for i in ids if all(events[i]['outcomes'][str(h)]['status']=='AVAILABLE' for h in H if h<=max_h)]

def matched_ids(events,left,right):
    def group(ids):
        d=collections.defaultdict(list)
        for i in ids:d[events[i]['decisionTimestamp']].append(i)
        return d
    a,b=group(left),group(right);ts=sorted(t for t in a.keys()&b.keys() if len(a[t])==len(b[t])==5)
    return [i for t in ts for i in a[t]],[i for t in ts for i in b[t]],ts

def summary(rows):
    return {'rawN':len(rows),'gross':dist([r['gross'] for r in rows]),'net':dist([r['net'] for r in rows]),
        'absoluteNetCI':cluster(by_session(rows,'net')),
        'costSensitivity':{str(c):dist([r['gross']-c for r in rows]) for c in [0,.05,.1,.2]},
        **{k:dist([r[k] for r in rows]) for k in ['MFE','MAE','balance','giveback']},
        'reach':{str(t):statistics.mean([r['MFE']>=t-1e-10 for r in rows]) if rows else None for t in [1,2,3,5]}}

def pair(events,left,right,h,family=1):
    a,b=flatten(events,left,h),flatten(events,right,h)
    assert len(a)==len(b)
    result={'timestamps':len(a)//5,'rawNPerArm':len(a),'selector':summary(a),'baseline':summary(b),'differences':{}}
    for field in ['gross','net','MFE','absMAE','balance','giveback']:
        sa,sb=by_session(a,field),by_session(b,field);assert sa.keys()==sb.keys()
        result['differences'][field]=cluster({k:sa[k]-sb[k] for k in sa},family if field in ['net','gross'] else 1)
    for t in [1,2,3,5]:
        ra=[{**r,'hit':float(r['MFE']>=t-1e-10)} for r in a];rb=[{**r,'hit':float(r['MFE']>=t-1e-10)} for r in b]
        sa,sb=by_session(ra,'hit'),by_session(rb,'hit')
        result['differences'][f'reach{t}']=cluster({k:sa[k]-sb[k] for k in sa})
    return result

def tails(rows):
    ordered=sorted(rows,key=lambda r:(r['net'],r['selectorEventId']));n=len(rows);vals=[r['net'] for r in rows]
    result={'full':dist(vals)}
    for side in ['top','worst']:
        candidates=[r for r in ordered if r['net']>0] if side=='top' else [r for r in ordered if r['net']<0]
        if side=='top':candidates=list(reversed(candidates))
        for f in [.01,.05]:
            removed=candidates[:math.ceil(f*n)];ids={r['selectorEventId'] for r in removed};remain=[r for r in rows if r['selectorEventId'] not in ids]
            result[f'{side}{int(100*f)}Excluded']={'removedN':len(removed),'removedSum':sum(r['net'] for r in removed),
                'removedMeanContribution':sum(r['net'] for r in removed)/n if n else None,
                'remaining':dist([r['net'] for r in remain]),'sessionCI':cluster(by_session(remain,'net'))}
    result['winsorizedMean']=float(np.clip(vals,*np.quantile(vals,[.01,.99])).mean()) if vals else None
    return result

def timing(rows):
    result={}
    for field in ['peakInterval','troughInterval']+[str(t) for t in [1,2,3,5]]:
        intervals=[r.get(field) if field.endswith('Interval') else r['firstHitIntervals'][field] for r in rows]
        vals=[x[1] for x in intervals if x is not None]
        result[field]={'eligibleN':len(rows),'reachedN':len(vals),'upperBoundMinutes':dist(vals),
            'cumulativeConditional':{str(t):sum(v<=t for v in vals)/len(vals) if vals else None for t in H},
            'cumulativeAllRows':{str(t):sum(v<=t for v in vals)/len(rows) if rows else None for t in H}}
    result['ordering']=dict(collections.Counter(r['ordering'] for r in rows))
    return result

def translation(events,ids):
    out={}
    full=[i for i in ids if events[i]['outcomes']['SESSION_END']['status']=='AVAILABLE']
    for kind,thresholds in [('winner',[1,2,3,5]),('deepLoser',[-3,-5,-10])]:
        for t in thresholds:
            selected=[i for i in full if (events[i]['outcomes']['SESSION_END']['MFE']>=t-1e-10 if kind=='winner' else events[i]['outcomes']['SESSION_END']['MAE']<=t+1e-10)]
            item={'fullDayConditionN':len(selected),'futureConditionedDescriptionOnly':True,
                'fullDayTiming':timing(flatten(events,selected,'SESSION_END')),'horizons':{}}
            for h in [30,60,90,120,'SESSION_END']:
                rows=flatten(events,selected,h);gross=[r['gross'] for r in rows];post=[]
                for r in rows:
                    day=events[r['selectorEventId']]['outcomes']['SESSION_END'];peak=day['peakInterval']
                    if peak and peak[1]<=r['elapsedMinutes']:post.append(day['MFE']-r['gross'])
                item['horizons'][str(h)]={'n':len(rows),'terminalGross':dist(gross),'terminalNet':dist([r['net'] for r in rows]),
                    'grossNegativeRate':sum(x<0 for x in gross)/len(gross) if gross else None,
                    'nearZeroRate':sum(abs(x)<=.05 for x in gross)/len(gross) if gross else None,
                    'nearZeroExclusive':{'positiveAbove005':sum(x>.05 for x in gross),'withinPlusMinus005':sum(abs(x)<=.05 for x in gross),'negativeBelowMinus005':sum(x<-.05 for x in gross)},
                    'terminalAtLeast':{str(k):sum(x>=k for x in gross)/len(gross) if gross else None for k in [1,2,3]},
                    'givebackToHorizonMFE':dist([r['giveback'] for r in rows]),'postFullDayPeakGiveback':dist(post),
                    'fullDayTroughBeforeEndpointN':sum(events[r['selectorEventId']]['outcomes']['SESSION_END']['troughInterval'] is not None and events[r['selectorEventId']]['outcomes']['SESSION_END']['troughInterval'][1]<=r['elapsedMinutes'] for r in rows)}
            out[f'{kind}{t}']=item
    return out

def strata(events,arms,context,field):
    out={}
    for h in [30,120,'SESSION_END']:
        out[str(h)]={}
        keys=sorted(set(str(context[i][field]) for ids in arms.values() for i in ids))
        for key in keys:
            cohorts={arm:[i for i in ids if str(context[i][field])==key and events[i]['outcomes'][str(h)]['status']=='AVAILABLE'] for arm,ids in arms.items()}
            item={arm:summary(flatten(events,ids,h)) for arm,ids in cohorts.items()}
            # Within a stratum, retain timestamps represented by both arms; no replacement/rerank.
            a=flatten(events,cohorts[ARMS[0]],h);b=flatten(events,cohorts[ARMS[1]],h)
            common={r['decisionTimestamp'] for r in a}&{r['decisionTimestamp'] for r in b}
            paired={}
            for metric in ['net','MFE','absMAE','giveback']:
                def tsmeans(rows):
                    d=collections.defaultdict(list)
                    for r in rows:
                        if r['decisionTimestamp'] in common:d[r['decisionTimestamp']].append(r[metric])
                    return {k:statistics.mean(v) for k,v in d.items()}
                sa,sb=tsmeans(a),tsmeans(b);d=collections.defaultdict(list)
                for stamp in sorted(common):d[stamp[:10]].append(sa[stamp]-sb[stamp])
                paired[metric]=cluster({k:statistics.mean(v) for k,v in sorted(d.items())})
            item['withinStratumPairedTimestamp']={'timestamps':len(common),'partialTop5Descriptive':True,'differences':paired}
            out[str(h)][key]=item
    return out

def score_analysis(directory):
    out={}
    for h in [15,30,60,90,120]:
        frame=pd.read_csv(Path(directory)/f'score-{h}.tsv',sep='\t',dtype={'sessionDate':str,'decisionTimeJst':str})
        item={'n':len(frame),'deciles':{},'rankIC':{},'futureAvailabilityUsedForRanks':False}
        for d,g in frame.groupby('scoreDecile',sort=True):
            item['deciles'][str(d)]={'n':len(g),'gross':dist(g.gross),'net':dist(g.gross-COST),'MFE':dist(g.MFE),'MAE':dist(g.MAE)}
        for outcome in ['gross','MFE','absMAE']:
            if outcome=='absMAE':frame[outcome]=-frame.MAE
            ics=[]
            for (session,time),g in frame.groupby(['sessionDate','decisionTimeJst'],sort=True):
                a=g.savedV1Score.rank(method='average').to_numpy();b=g[outcome].rank(method='average').to_numpy()
                if len(a)>1 and a.std()>0 and b.std()>0:ics.append({'sessionDate':session,'value':float(np.corrcoef(a,b)[0,1])})
            item['rankIC'][outcome]={'evaluableTimestamps':len(ics),'cluster':cluster(by_session(ics,'value'))}
        means=[item['deciles'][str(d)]['net']['mean'] for d in range(1,11) if str(d) in item['deciles']]
        item['nondecreasingNetDecileMeans']=len(means)==10 and all(b>=a for a,b in zip(means,means[1:]))
        out[str(h)]=item
    return out

def decide(paired,tails_out):
    p=paired['COMMON120']['RANDOM_TOP5'];n=p['120']['differences']['net']['clusters']
    pos=[h for h in H if (p[str(h)]['differences']['net']['simultaneousCI95'][0] or -math.inf)>0]
    early=p['30']['differences']['net']['sessionValues'];late=p['120']['differences']['net']['sessionValues']
    assert early.keys()==late.keys()
    change=cluster({k:late[k]-early[k] for k in early})
    tags=[]
    if len(pos)>=2 and n>=38 and p['120']['differences']['balance']['sessionEqualMean'] is not None and p['120']['differences']['balance']['sessionEqualMean']>0:
        tags.append('RELATIVE_DIRECTIONAL_EVIDENCE_REQUIRES_TAIL_AND_PRICE_REVIEW')
    if n>=38 and (change['clusterCI95'][0] or -math.inf)>0 and 120 in pos:tags.append('DELAYED_ALPHA')
    else:tags.append('DELAYED_ALPHA_INCONCLUSIVE')
    if any(h<=30 for h in pos) and (change['clusterCI95'][1] or math.inf)<0 and p['120']['differences']['giveback']['sessionEqualMean']>p['30']['differences']['giveback']['sessionEqualMean']:tags.append('SHORT_LIVED_ALPHA_WITH_GIVEBACK')
    q=p['30']['differences']
    if (q['MFE']['clusterCI95'][0] or -math.inf)>0 and (q['absMAE']['clusterCI95'][0] or -math.inf)>0 and len(pos)<2:tags.append('VOLATILITY_RANGE_SIGNAL')
    t=tails_out['COMMON120'][ARMS[0]]['30']
    if t['full']['mean'] is not None and t['full']['mean']>0 and all(t[k]['remaining']['mean'] is not None and t[k]['remaining']['mean']<=0 for k in ['top1Excluded','top5Excluded']):tags.append('TAIL_DRIVEN_OPPORTUNITY')
    return {'id':'PHASE57_FROZEN_SELECTOR_FULL_DAY_PATH_ANATOMY_V1','pathVerdict':'MIXED' if n>=38 else 'INCONCLUSIVE',
        'diagnosticTags':tags,'positiveSimultaneousCommon120Horizons':pos,'lateMinus30PairedAdvantage':change,
        'nextStep':'REVIEW_DIAGNOSTIC_BEFORE_ANY_SELECTOR_UNFREEZE','automaticAction':False,'stop':True}

def measure(paths,context_dir,score_dir,output):
    p=protocol();output=Path(output);output.mkdir(parents=True,exist_ok=False)
    membership=read(MEMBERSHIP);arms=membership['arms'];projection=read(paths)
    assert sha(paths)==read(old.BASE/'measurement/manifest.json')['pathsSHA256'],'BASELINE_PATH_PARITY'
    events={x['selectorEventId']:evaluate(x) for x in projection['events']}
    assert set(events)=={x['selectorEventId'] for x in membership['new']}
    meta=read(Path(context_dir)/'context.json');context=meta['context'];assert set(context)==set(events)
    for eid,c in context.items():
        c['priceBand']=band(c['decisionPrice']);c['sessionHalf']='AM' if old.timestamp(events[eid]['decisionTimestamp']).hour<12 else 'PM'
    cohorts={'AVAILABLE':{arm:ids for arm,ids in arms.items()},'SESSION_END':{arm:[i for i in ids if events[i]['outcomes']['SESSION_END']['status']=='AVAILABLE'] for arm,ids in arms.items()}}
    for h in [60,90,120]:cohorts[f'COMMON{h}']={arm:common_ids(events,ids,h) for arm,ids in arms.items()}
    manifest={};terminal={};paired={};tail={};timings={}
    for name,members in cohorts.items():
        horizons=['SESSION_END'] if name=='SESSION_END' else [h for h in H if name=='AVAILABLE' or h<=int(name[6:])]
        manifest[name]={arm:{'n':len(ids),'identitySHA256':digest(ids),'ids':ids} for arm,ids in members.items()}
        terminal[name]={arm:{str(h):summary(flatten(events,ids,h)) for h in horizons} for arm,ids in members.items()}
        tail[name]={arm:{str(h):tails(flatten(events,ids,h)) for h in horizons} for arm,ids in members.items()}
        timings[name]={arm:{str(h):timing(flatten(events,ids,h)) for h in horizons} for arm,ids in members.items()}
        paired[name]={};manifest[name]['pairs']={}
        for baseline in ARMS[1:]:
            paired[name][baseline]={};manifest[name]['pairs'][baseline]={}
            for h in horizons:
                a=[i for i in members[ARMS[0]] if events[i]['outcomes'][str(h)]['status']=='AVAILABLE']
                b=[i for i in members[baseline] if events[i]['outcomes'][str(h)]['status']=='AVAILABLE']
                a,b,ts=matched_ids(events,a,b)
                manifest[name]['pairs'][baseline][str(h)]={'timestamps':ts,'selectorIds':a,'baselineIds':b,'selectorSHA256':digest(a),'baselineSHA256':digest(b)}
                paired[name][baseline][str(h)]=pair(events,a,b,h,7 if name=='COMMON120' and baseline==ARMS[1] else 1)
    coverage={arm:{str(h):dict(collections.Counter(events[i]['outcomes'][str(h)]['status'] for i in ids)) for h in [*H,'SESSION_END']} for arm,ids in arms.items()}
    score=score_analysis(score_dir)
    price=strata(events,arms,context,'priceBand');vol=strata(events,arms,context,'volatilityStratum')
    price['actualExchangeTick']={'status':'NOT_EVALUABLE','reason':'Dated security-specific tick schedule absent; nominal 1JPY is not exchange tick.'}
    price['nominalOneYenOnly']={arm:{'oneYenPct':dist([100/context[i]['decisionPrice'] for i in ids]),
        'oneYenAtLeast1PctRate':sum(100/context[i]['decisionPrice']>=1 for i in ids)/len(ids),
        'twoYenAtLeast3PctRate':sum(200/context[i]['decisionPrice']>=3 for i in ids)/len(ids),
        'nominalIncrements':{str(t):dist([math.ceil(context[i]['decisionPrice']*t/100) for i in ids]) for t in [1,3,5]}} for arm,ids in arms.items()}
    symbols={};sessions={}
    for arm,ids in arms.items():
        freq=collections.Counter(events[i]['symbol'] for i in ids);top=sorted(freq,key=lambda k:(-freq[k],k))[:3]
        symbols[arm]={'uniqueSymbols':len(freq),'frequencyHHI':sum((n/len(ids))**2 for n in freq.values()),'topFrequency':sorted(freq.items(),key=lambda x:(-x[1],x[0]))[:20],
            'excludedTop3':top,'descriptiveExclusion':{str(h):summary(flatten(events,[i for i in ids if events[i]['symbol'] not in top],h)) for h in [30,120,'SESSION_END']}}
    for name,baselines in paired.items():
        sessions[name]={}
        for baseline,hs in baselines.items():
            sessions[name][baseline]={}
            for h,result in hs.items():
                vals=result['differences']['net']['sessionValues'];ordered=sorted(vals.items(),key=lambda x:(x[1],x[0]));n=len(vals)
                sessions[name][baseline][h]={'positiveSessions':sum(v>0 for v in vals.values()),'negativeSessions':sum(v<0 for v in vals.values()),'median':dist(list(vals.values()))['median'],
                    'top5':ordered[-5:],'worst5':ordered[:5],'top5MeanContribution':sum(v for _,v in ordered[-5:])/n if n else None,'worst5MeanContribution':sum(v for _,v in ordered[:5])/n if n else None}
    pre={'eligibleUniverseByTimestamp':meta['universe'],'arms':{arm:{'numeric':{k:dist([context[i][k] for i in ids]) for k in ['decisionPrice','momentum30Pct','currentReturnPct','decisionVolatilityPct','logCumulativeTurnover','volumeAccelerationRatio','savedV1Score']},
        'categorical':{k:dict(collections.Counter(context[i][k] for i in ids)) for k in ['volatilityStratum','priceBand','segment','liquidityBucket']}} for arm,ids in arms.items()}}
    decision=decide(paired,tail)
    summary_all={'id':p['id'],'scope':p['scope'],'coverage':coverage,'cohortCounts':{k:{a:len(ids) for a,ids in v.items()} for k,v in cohorts.items()},'paired':paired,'decision':decision,
        'safety':p['safety'],'sealed':p['sealed'],'fitCalls':0,'providerRequests':0,'historicalDevelopmentInSample':True,'uncertainty':'Session cluster controls within-session dependence only; temporal independence not guaranteed. Multiple descriptive subgroup CIs are not confirmatory.'}
    outputs={'common-cohort-manifest.json':manifest,'terminal-return-summary.json':terminal,'mfe-mae-summary.json':{k:{a:{h:{x:r[x] for x in ['MFE','MAE','balance','reach']} for h,r in hs.items()} for a,hs in v.items()} for k,v in terminal.items()},
        'peak-trough-timing.json':timings,'giveback-summary.json':{k:{a:{h:r['giveback'] for h,r in hs.items()} for a,hs in v.items()} for k,v in terminal.items()},
        'threshold-translation.json':{a:translation(events,ids) for a,ids in arms.items()},'tail-contribution.json':tail,'price-tick-diagnostic.json':price,'ex-ante-volatility-diagnostic.json':vol,
        'pre-selection-path-diagnostic.json':pre,'score-economic-monotonicity.json':score,'session-concentration.json':sessions,'symbol-concentration.json':symbols,
        'cluster-bootstrap.json':paired,'MDE-report.json':{k:{a:{h:{x:r['differences']['net'][x] for x in ['clusters','ciWidth','MDE80']} for h,r in hs.items()} for a,hs in v.items()} for k,v in paired.items()},
        'measurement-summary.json':summary_all,'decision.json':decision,'am-pm-diagnostic.json':strata(events,arms,context,'sessionHalf')}
    for arm,label in zip(ARMS,['selector','random','momentum']):outputs[f'{label}-path-ledger.json.gz']={'events':[{**events[i],'context':context[i]} for i in arms[arm]]}
    for f,value in outputs.items():write(output/f,clean(value))
    report=render(summary_all,terminal,price,score,outputs['threshold-translation.json'],tail)
    (output/'REPORT.md').write_text(report)
    source={'protocolSHA256':sha(PROTOCOL),'sourcePins':p['sourcePins'],'membershipSHA256':sha(MEMBERSHIP),'projectedPathsSHA256':sha(paths),'inputManifestSHA256':meta['inputManifestSHA256'],
        'implementation':{f:sha(ROOT/f) for f in ['scripts/phase57_selector_path_anatomy.py','scripts/phase57_selector_path_scores.mjs']},
        'outputs':{f.name:sha(f) for f in sorted(output.iterdir())},'safety':p['safety'],'sealed':p['sealed'],'fitCalls':0,'providerRequests':0}
    write(output/'source-manifest.json',source)
    print(json.dumps({'status':'FULL_DAY_PATH_ANATOMY_MEASURED','cohorts':summary_all['cohortCounts'],'decision':decision['pathVerdict']}))

def fmt(v):return 'NA' if v is None else f'{v:+.4f}'
def render(s,terminal,price,score,translation,tail):
    p=s['paired']['COMMON120']['RANDOM_TOP5'];d=s['decision'];q=p['30']['differences'];late=d['lateMinus30PairedAdvantage']
    lines=['# Frozen Selector Full-Day Path Anatomy / Null-Control Diagnostic','',
        'Development-only descriptive evidence. Fixed frozen Selector, 30-minute cadence, Top5, 76 sessions / 760 timestamps / 3,800 selections per arm. Reference OPEN/CLOSE returns; no guaranteed fills or strategy P&L. All percentage values are percentage points; canonical round-trip cost 0.05pp.','',
        '## Primary answers (Q1–Q10)','',
        f"1. Directionality: COMMON120 multiple-comparison-adjusted positive Selector–Random horizons: {d['positiveSimultaneousCommon120Horizons']}. Relative information and absolute net performance are separate; this is in-sample Development, not validation.",
        f"2. Range selection: at COMMON120 / 30m, paired MFE uplift {fmt(q['MFE']['sessionEqualMean'])}pp, absolute MAE uplift {fmt(q['absMAE']['sessionEqualMean'])}pp, balance uplift {fmt(q['balance']['sessionEqualMean'])}pp. Compare the CIs in cluster-bootstrap.json before assigning directionality.",
        '3. +3/+5 economic translation: future-conditioned full-day winner outcomes appear below; they cannot define a trading policy.',
        f"4. Giveback: COMMON120 / 30m Selector–Random giveback {fmt(q['giveback']['sessionEqualMean'])}pp; 120m {fmt(p['120']['differences']['giveback']['sessionEqualMean'])}pp.",
        f"5. Delayed edge: 120m minus 30m paired advantage {fmt(late['sessionEqualMean'])}pp, CI {late['clusterCI95']}. Tags: {', '.join(d['diagnosticTags'])}.",
        '6. Fat-tail dependence: full, top1% and top5% excluded net returns are tabulated below. Exclusions are outcome-conditioned diagnostics, not deployable filters.',
        '7. Price/tick: fixed price-band results are in price-tick-diagnostic.json. Actual dated exchange tick sizes are NOT_EVALUABLE; nominal 1JPY quantities cannot establish tick causality.',
        '8. Score ranking: exact frozen scores reconstructed from the existing PIT contract; deciles are set before future availability. Rank IC against terminal/MFE/absolute MAE appears below.',
        '9. Redesign rationale: range-only association, weak absolute net and tail dependence would support considering an economic-target redesign; a strong common-cohort terminal signal would support retaining the Selector. This report supplies diagnostic evidence only, not unfreeze approval.',
        '10. Recommended next step: review the diagnostic and its power/coverage before an explicit user decision on Selector redesign or additional Development evidence. Do not begin Entry, EXIT, Capital or new acquisition automatically.','',
        f"Final Path Verdict: **{d['pathVerdict']}**. Tags: {', '.join(d['diagnosticTags'])}.",
        'Final Selector Interpretation: The frozen ranking must be described by its matched terminal advantage together with its upside and downside excursions. Development results alone do not establish deployable absolute LONG alpha.','',
        '## Primary common-cohort evidence','',
        '| Cohort | Selector rows | Random rows | Momentum rows | Matched Selector–Random timestamps |',
        '|---|---:|---:|---:|---:|']
    for name in ['COMMON60','COMMON90','COMMON120','SESSION_END']:
        counts=s['cohortCounts'][name];h='SESSION_END' if name=='SESSION_END' else '30'
        lines.append(f"| {name} | {counts[ARMS[0]]} | {counts[ARMS[1]]} | {counts[ARMS[2]]} | {s['paired'][name][ARMS[1]][h]['timestamps']} |")
    lines+=['','COMMON120 below uses identical event IDs at every horizon and full original Top5 in each arm at matched timestamps. Independent pair cohorts may differ between Random and Momentum. Session-equal means are primary; row distribution medians/PF are descriptive.','',
        '| min | Selector net | Random net | delta | simultaneous 95% CI | MFE delta | absMAE delta | giveback delta | clusters | MDE |','|---|---:|---:|---:|---|---:|---:|---:|---:|---:|']
    for h,r in p.items():
        v=r['differences'];n=v['net'];lines.append(f"| {h} | {fmt(r['selector']['absoluteNetCI']['sessionEqualMean'])} | {fmt(r['baseline']['absoluteNetCI']['sessionEqualMean'])} | {fmt(n['sessionEqualMean'])} | {n['simultaneousCI95']} | {fmt(v['MFE']['sessionEqualMean'])} | {fmt(v['absMAE']['sessionEqualMean'])} | {fmt(v['giveback']['sessionEqualMean'])} | {n['clusters']} | {fmt(n['MDE80'])} |")
    lines+=['','## Available cohorts and session end (descriptive)','', '| horizon | arm | n | net mean | median | PF | positive rate | session-equal mean | cluster CI |','|---|---|---:|---:|---:|---:|---:|---:|---|']
    for cohort in ['AVAILABLE','SESSION_END']:
        for arm,hs in terminal[cohort].items():
            for h,r in hs.items():
                n=r['net'];ci=r['absoluteNetCI'];lines.append(f"| {h} | {arm} | {n['n']} | {fmt(n['mean'])} | {fmt(n['median'])} | {fmt(n['PF'])} | {fmt(n['positiveRate'])} | {fmt(ci['sessionEqualMean'])} | {ci['clusterCI95']} |")
    lines+=['','Do not read this changing-N table as a longitudinal path. Session end crosses lunch using actual regular bars; fixed horizons never cross lunch.','',
        '## Winner translation and tails','', '| arm | full-day reach | complete winners | end net mean | end gross positive rate | end gross negative rate | end giveback mean |','|---|---|---:|---:|---:|---:|---:|']
    for a in ARMS:
        for t in [3,5]:
            x=translation[a][f'winner{t}'];e=x['horizons']['SESSION_END'];lines.append(f"| {a} | +{t}% | {x['fullDayConditionN']} | {fmt(e['terminalNet']['mean'])} | {fmt(e['terminalGross']['positiveRate'])} | {fmt(e['grossNegativeRate'])} | {fmt(e['givebackToHorizonMFE']['mean'])} |")
    lines+=['','| COMMON120 arm / 30m | full net | top1 excluded | top5 excluded | worst1 excluded | worst5 excluded | winsorized |','|---|---:|---:|---:|---:|---:|---:|']
    for a in ARMS:
        t=tail['COMMON120'][a]['30'];lines.append('| '+a+' | '+' | '.join(fmt(x) for x in [t['full']['mean'],*[t[k]['remaining']['mean'] for k in ['top1Excluded','top5Excluded','worst1Excluded','worst5Excluded']],t['winsorizedMean']])+' |')
    lines+=['','## Score economic monotonicity','', '| horizon | n | terminal rank IC | MFE rank IC | absolute MAE rank IC | monotone net deciles |','|---|---:|---:|---:|---:|---|']
    for h,x in score.items():lines.append(f"| {h} | {x['n']} | {fmt(x['rankIC']['gross']['cluster']['sessionEqualMean'])} | {fmt(x['rankIC']['MFE']['cluster']['sessionEqualMean'])} | {fmt(x['rankIC']['absMAE']['cluster']['sessionEqualMean'])} | {x['nondecreasingNetDecileMeans']} |")
    lines+=['','## Integrity and limits','',
        'Primary: common-cohort terminal, Random null, excursion balance, giveback, tails, fixed price/volatility strata, score analysis. Descriptive supporting work: timing buckets, AM/PM, concentration, conditional winners/deep losers. No additional path archetypes or optimized filters.',
        'Common cohort manifests include full event IDs and hashes. Selection membership and projected paths must exactly match the prior Economic Census. Missing bars fail closed without interpolation or zero imputation. Sparse observed-minute 5m bars are counted. Time-to-hit/peak/trough are 5m intervals, not precise event times; same-bar ordering is unknown.',
        'Session bootstrap: deterministic seed 20260919, 10,000 replicates. Seven COMMON120 Random contrasts use simultaneous Bonferroni intervals; all other CIs are pointwise descriptive. 0m is a zero gross reference only; no net/PF at zero duration. PF is return-sum ratio, not a capital-weighted portfolio statistic.',
        'Selector / Entry / EXIT / Capital unchanged. DEV TEST / Fresh / OOS sealed. New provider requests 0; fit calls 0. All nine safety flags false. No merge, promotion, paper or live execution. STOP after diagnostic.','']
    return '\n'.join(lines)

def audit(directory=None):
    protocol()
    if directory:
        d=Path(directory);m=read(d/'source-manifest.json')
        assert m['protocolSHA256']==sha(PROTOCOL)
        for f,h in m['outputs'].items():assert sha(d/f)==h,f
        for f,h in m['implementation'].items():assert sha(ROOT/f)==h,f
        assert all(v is False for v in m['safety'].values()) and m['providerRequests']==m['fitCalls']==0
        c=read(d/'common-cohort-manifest.json')
        for name in ['COMMON60','COMMON90','COMMON120']:
            for a in ARMS:
                assert c[name][a]['identitySHA256']==digest(c[name][a]['ids'])
            for baseline,hs in c[name]['pairs'].items():
                assert len({r['selectorSHA256'] for r in hs.values()})==1
                assert len({r['baselineSHA256'] for r in hs.values()})==1
                for r in hs.values():assert len(r['selectorIds'])==len(r['baselineIds'])==5*len(r['timestamps'])
        s=read(d/'measurement-summary.json');assert s['scope']['selectionRows']==3800
        for a,hs in s['coverage'].items():
            for h,counts in hs.items():assert sum(counts.values())==3800
    print('PATH_ANATOMY_AUDIT_PASS')

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--dataset-dir',required=True);a.add_argument('--output-dir',required=True)
    a=sub.add_parser('measure');a.add_argument('--paths',required=True);a.add_argument('--context-dir',required=True);a.add_argument('--score-dir',required=True);a.add_argument('--output-dir',required=True)
    a=sub.add_parser('audit');a.add_argument('--measurement')
    x=p.parse_args()
    if x.command=='prepare':prepare(x.dataset_dir,x.output_dir)
    elif x.command=='measure':measure(x.paths,x.context_dir,x.score_dir,x.output_dir)
    else:audit(x.measurement)
if __name__=='__main__':main()
