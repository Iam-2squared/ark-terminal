"""Single-specification causal Entry/EXIT research. Never a production policy."""
from __future__ import annotations
import argparse,collections,datetime as dt,hashlib,json,math,re,shutil,statistics
from pathlib import Path
import numpy as np
import pandas as pd
from scripts import phase57_selector_low_high_anatomy as l
from scripts import phase57_new_long_exit_candidate_a as frozen_exit

a=l.a
v=l.v
ROOT=l.ROOT
BASE=ROOT/'docs/evidence/phase57-causal-entry-exit-recoverability-v1'
P=BASE/'protocol.json'
read,write,sha=l.read,l.write,l.sha
COST=.05
EF=['currentReturn','return1','return2','return3','acceleration','lowerLow','higherLow','closePosition','body','upperWick','lowerWick','recentVolatility','prefixHigh','prefixLow','drawdownFromPrefixHigh','minutesSinceSelection','selectorScore','selectorRank','selectionMinute']
XF=EF+['unrealizedReturn','mfeSoFar','maeSoFar','minutesSinceEntry']

def digest(x):return hashlib.sha256(a.old.encoded(a.clean(x))).hexdigest()

def protocol():
    p=read(P);assert sha(P)==read(BASE/'protocol-lock.json')['protocolSHA256']
    assert p['id']=='PHASE57_CAUSAL_ENTRY_EXIT_RECOVERABILITY_V1'
    assert p['features']['entry']==EF and p['features']['exit']==XF
    assert p['model']['alpha']==1 and p['calendar']['costPctPoints']==COST
    assert len(p['safety'])==9 and not any(p['safety'].values()) and not any(p['sealed'].values())
    ds=[d for split in ['FIT','QUALIFY','REPORT'] for d in p['split'][split]]
    assert len(ds)==len(set(ds))==76 and ds==sorted(ds)
    for f,h in p['sourcePins'].items():assert sha(ROOT/f)==h,f
    return p

def load_events():
    protocol();members=l.members()[a.ARMS[0]];raw={p['selectorEventId']:p for p in read(a.old.FROZEN_PATHS)['events']}
    rows=[]
    for m in members:
        p=raw[m['selectorEventId']]
        for k in ['decisionPrice','symbol','sessionDate','decisionTimestamp']:assert p[k]==m[k]
        bars=a.old.materialize_path(p)
        rawbars={a.old.timestamp(b['start']):b for b in p['future']}
        for bar in bars:
            source=rawbars[bar['start']]
            if not source['missing'] and a.old.valid_number(source.get('o')):bar['o']=p['decisionPrice']*(1+source['o']/100)
        decision=a.old.timestamp(m['decisionTimestamp']);target=decision+dt.timedelta(minutes=30)
        eligible=v.boundary(m['decisionTimestamp'],30)=='ELIGIBLE'
        mapping={b['start']:b for b in bars}
        if eligible:
            slots=[decision+dt.timedelta(minutes=5*j) for j in range(6)]
            primary=[mapping.get(t) for t in slots]
            common=all(b is not None and b['valid'] for b in primary)
        else:primary=[];common=False
        rows.append(m|{'bars':bars,'primary':primary,'decision':decision,'target':target,'eligible':eligible,'common30':common})
    assert len(rows)==3800
    return rows

def open_price(b):
    # An OPEN reference must not consult that bar's not-yet-observed H/L/C validity.
    if b is None or b.get('missing'):return None
    value=b.get('o')
    return value if a.old.valid_number(value) and value>0 else None

def state(member,prefix,at,entry=None):
    assert len(prefix)>=3
    assert all(b is not None and b['valid'] and b['end']<=at for b in prefix),'NON_PIT_PREFIX'
    assert prefix[-1]['end']==at
    assert all(x['end']==y['start'] for x,y in zip(prefix,prefix[1:])),'GAP_OR_LUNCH_IN_STATE'
    last,prev=prefix[-1],prefix[-2];price=member['decisionPrice'];close=last['c'];rng=last['h']-last['l']
    rr=[100*(b['c']/b['o']-1) for b in prefix[-3:]]
    high=max(b['h'] for b in prefix);low=min(b['l'] for b in prefix)
    decision=a.old.timestamp(member['decisionTimestamp'])
    values={'currentReturn':100*(close/price-1),'return1':rr[-1],
        'return2':100*(close/prefix[-2]['o']-1),'return3':100*(close/prefix[-3]['o']-1),
        'acceleration':rr[-1]-rr[-2],'lowerLow':float(last['l']<prev['l']),'higherLow':float(last['l']>prev['l']),
        'closePosition':(close-last['l'])/rng if rng else .5,'body':(close-last['o'])/rng if rng else 0,
        'upperWick':(last['h']-max(close,last['o']))/rng if rng else 0,'lowerWick':(min(close,last['o'])-last['l'])/rng if rng else 0,
        'recentVolatility':float(np.std(rr)),'prefixHigh':100*(high/price-1),'prefixLow':100*(low/price-1),
        'drawdownFromPrefixHigh':100*(close/high-1),'minutesSinceSelection':(at-decision).total_seconds()/60,
        'selectorScore':member['savedV1Score'],'selectorRank':member['originalRank'],'selectionMinute':decision.hour*60+decision.minute}
    if entry is not None:
        ep=entry['price'];et=a.old.timestamp(entry['timestamp']);held=[b for b in prefix if b['start']>=et]
        assert held and at>et
        values.update(unrealizedReturn=100*(close/ep-1),mfeSoFar=max(0,100*(max(b['h'] for b in held)/ep-1)),
            maeSoFar=min(0,100*(min(b['l'] for b in held)/ep-1)),minutesSinceEntry=(at-et).total_seconds()/60)
    assert all(math.isfinite(x) for x in values.values())
    return {'features':values,'availableAt':at.isoformat(),'maxInputBarEnd':prefix[-1]['end'].isoformat()}

def predict(model,s):
    assert s['maxInputBarEnd']<=s['availableAt']
    x=np.asarray([s['features'][f] for f in model['features']]);return float(model['intercept']+((x-model['mean'])/model['scale'])@model['coef'])

def fixed_entry(e,delay=0):
    if not e['eligible']:return {'status':'CALENDAR_INELIGIBLE','decision':'NO_CALENDAR_WINDOW'}
    i=delay//5;b=e['primary'][i];price=open_price(b)
    return {'status':'ENTERED' if price is not None else 'MISSING_OPEN','decision':'ENTER','index':i,'price':price,
        'timestamp':(e['decision']+dt.timedelta(minutes=delay)).isoformat(),'signalTimestamp':e['decision'].isoformat(),'delay':delay,'reason':f'FIXED_DELAY_{delay}'}

def entry_policy(e,model):
    if not e['eligible']:return {'status':'CALENDAR_INELIGIBLE','decision':'NO_CALENDAR_WINDOW','trace':[]}
    trace=[];prefix=[]
    for n in range(1,6):
        b=e['primary'][n-1]
        if b is None or not b['valid']:return {'status':'DATA_BLOCKED','decision':'UNKNOWN','reason':'MISSING_COMPLETED_PREFIX','trace':trace}
        prefix.append(b)
        if n<3:continue
        s=state(e,prefix,b['end']);score=predict(model,s)
        trace.append({'at':s['availableAt'],'score':score,'stateSHA256':digest(s)})
        if score>0:
            price=open_price(e['primary'][n])
            return {'status':'ENTERED' if price is not None else 'MISSING_OPEN','decision':'ENTER','index':n,'price':price,
                'timestamp':b['end'].isoformat(),'signalTimestamp':b['end'].isoformat(),'delay':5*n,'reason':'POSITIVE_PREDICTED_NET','trace':trace}
    return {'status':'ABSTAIN','decision':'ABSTAIN','signalTimestamp':(e['decision']+dt.timedelta(minutes=25)).isoformat(),'reason':'NO_POSITIVE_STATE_BY25','trace':trace}

def fixed_exit(e,entry):
    return {'kind':'close','index':5,'reason':'FIXED_SELECTION30'}

def exit_policy(e,entry,model):
    if entry['status']!='ENTERED':return {'kind':'none','reason':entry['status']}
    prefix=[];trace=[]
    for n in range(1,6):
        b=e['primary'][n-1]
        if b is None or not b['valid']:return {'kind':'blocked','reason':'MISSING_COMPLETED_PREFIX','trace':trace}
        prefix.append(b)
        if n<3 or n<=entry['index']:continue
        s=state(e,prefix,b['end'],entry);score=predict(model,s)
        trace.append({'at':s['availableAt'],'score':score,'stateSHA256':digest(s)})
        if score>0:return {'kind':'open','index':n,'signalTimestamp':b['end'].isoformat(),'reason':'POSITIVE_PREDICTED_EXIT_ADVANTAGE','trace':trace}
    return fixed_exit(e,entry)|{'trace':trace}

def trade(e,entry,ex,horizon=None):
    if entry['status']=='ABSTAIN':return {'status':'ABSTAIN','entered':False,'net':0.,'gross':0.,'reason':'DELIBERATE_NO_TRADE'}
    if entry['status']!='ENTERED':return {'status':entry['status'],'entered':False,'net':None,'gross':None,'reason':entry.get('reason',entry['status'])}
    price=entry['price'];start=a.old.timestamp(entry['timestamp']);allbars=e['bars']
    if horizon is not None:
        target=start+dt.timedelta(minutes=horizon)
        if v.boundary(start.isoformat(),horizon)!='ELIGIBLE':return {'status':'HORIZON_BOUNDARY','entered':True,'net':None}
        endbar=next((b for b in allbars if b['end']==target),None);exit_price=endbar['c'] if endbar and endbar['valid'] else None;kind='close';reason='FIXED_ENTRY_RELATIVE'
    else:
        kind=ex['kind'];reason=ex['reason']
        if kind not in ['open','close']:return {'status':'DATA_BLOCKED','entered':True,'net':None,'gross':None,'reason':reason}
        endbar=e['primary'][ex['index']];target=e['decision']+dt.timedelta(minutes=5*(ex['index']+(kind=='close')))
        exit_price=open_price(endbar) if kind=='open' else endbar['c'] if endbar and endbar['valid'] else None
    if exit_price is None:return {'status':'MISSING_EXIT_REFERENCE','entered':True,'net':None,'gross':None,'reason':reason}
    gross=100*(exit_price/price-1);expected=a.regular_slots(start,target);mapping={b['start']:b for b in allbars}
    complete=all(t in mapping and mapping[t]['valid'] for t in expected)
    held=[mapping[t] for t in expected] if complete else []
    mfe=max([0,gross]+[100*(b['h']/price-1) for b in held]) if complete else None
    mae=min([0,gross]+[100*(b['l']/price-1) for b in held]) if complete else None
    immediate=open_price(e['primary'][0]) if e['primary'] else None
    return {'status':'OBSERVED','entered':True,'gross':gross,'net':gross-COST,'MFE':mfe,'MAE':mae,
        'giveback':mfe-gross if mfe is not None else None,'captureRatio':(gross-COST)/mfe if mfe is not None and mfe>0 else None,
        'holdMinutes':(target-start).total_seconds()/60,'entryDelay':entry['delay'],'entryPriceImprovementPct':100*(immediate-price)/immediate if immediate else None,
        'entryTimestamp':start.isoformat(),'exitTimestamp':target.isoformat(),'exitKind':kind,'reason':reason,'pathComplete':complete,'intrabarOrder':'UNKNOWN_NOT_USED',
        'costSensitivity':{str(c):gross-c for c in [.05,.1,.2]}}

def labelled_states(events,mode,entries=None):
    rows=[];missing=collections.Counter();total=0
    for e in events:
        if not e['eligible']:missing['CALENDAR_INELIGIBLE']+=1;continue
        entry=entries[e['selectorEventId']] if mode=='exit' else None
        if mode=='exit' and entry['status']!='ENTERED':missing['NO_ROUTE_ENTRY']+=1;continue
        prefix=[]
        for n in range(1,6):
            b=e['primary'][n-1]
            if b is None or not b['valid']:missing['MISSING_PREFIX']+=1;break
            prefix.append(b)
            if n<3 or (entry is not None and n<=entry['index']):continue
            total+=1;s=state(e,prefix,b['end'],entry);op=open_price(e['primary'][n]);last=e['primary'][5]
            if op is None or last is None or not last['valid']:missing['UNKNOWN_LABEL_ENDPOINT']+=1;continue
            target=100*(last['c']/op-1)-COST if mode=='entry' else 100*(op-last['c'])/entry['price']
            rows.append({'selectorEventId':e['selectorEventId'],'sessionDate':e['sessionDate'],'symbol':e['symbol'],
                'decisionTimestamp':e['decisionTimestamp'],'stateTimestamp':s['availableAt'],'labelEnd':e['target'].isoformat(),
                'state':s,'target':target,'role':'EVALUATOR_LABEL_NEVER_POLICY_INPUT'})
    return rows,{'potentialStates':total,'identifiedStates':len(rows),'sessions':len({r['sessionDate'] for r in rows}),'missing':dict(missing)}

def fit(rows,features,allowed_days):
    assert all(r['sessionDate'] in allowed_days and r['labelEnd'][:10]==r['sessionDate'] for r in rows),'TRAIN_EVAL_ISOLATION'
    if len(rows)<200 or len({r['sessionDate'] for r in rows})<20:return None
    day_events=collections.defaultdict(set);event_states=collections.Counter(r['selectorEventId'] for r in rows)
    for r in rows:day_events[r['sessionDate']].add(r['selectorEventId'])
    w=np.asarray([1/(len(day_events)*len(day_events[r['sessionDate']])*event_states[r['selectorEventId']]) for r in rows]);assert abs(w.sum()-1)<1e-8
    x=np.asarray([[r['state']['features'][f] for f in features] for r in rows]);y=np.asarray([r['target'] for r in rows])
    mean=(x*w[:,None]).sum(axis=0);scale=np.sqrt(((x-mean)**2*w[:,None]).sum(axis=0));scale=np.where(scale<1e-12,1,scale)
    z=(x-mean)/scale;intercept=float(y@w);coef=np.linalg.solve(z.T@(w[:,None]*z)+np.eye(len(features)),z.T@(w*(y-intercept)))
    model={'features':features,'mean':mean.tolist(),'scale':scale.tolist(),'coef':coef.tolist(),'intercept':intercept,
        'alpha':1.,'fitSessions':sorted(day_events),'fitRows':len(rows),'fitInputSHA256':digest(rows),'fitCalls':1,'role':'RESEARCH_DIAGNOSTIC_NOT_PROMOTED'}
    pred=[predict(model,r['state']) for r in rows];model['scoreQuintileEdges']=np.quantile(pred,[.2,.4,.6,.8]).tolist()
    return model

def diagnostic(model,rows,availability):
    if model is None:return {'status':'INSUFFICIENT_FIT_DATA','pass':False,'availability':availability}
    scored=[r|{'prediction':predict(model,r['state'])} for r in rows];days=collections.defaultdict(list)
    for r in scored:days[r['sessionDate']].append(r)
    ic={}
    for d,rs in sorted(days.items()):
        x=pd.Series([r['prediction'] for r in rs]).rank().to_numpy();y=pd.Series([r['target'] for r in rs]).rank().to_numpy()
        if len(x)>2 and x.std()>0 and y.std()>0:ic[d]=float(np.corrcoef(x,y)[0,1])
    stat=v.cluster(ic,2);ok=len(rows)>=100 and len(ic)>=12 and stat['simultaneousCI95'][0] is not None and stat['simultaneousCI95'][0]>0
    bins={str(k):[] for k in range(1,6)}
    for r in scored:bins[str(int(np.searchsorted(model['scoreQuintileEdges'],r['prediction'],side='right'))+1)].append(r['target'])
    return {'status':'PIT_ECONOMIC_SEPARATION_SUPPORTED' if ok else 'RECOVERABILITY_NOT_DEMONSTRATED','pass':ok,'availability':availability,
        'rankIC':stat,'scoreBuckets':{k:a.dist(x) for k,x in bins.items()},'target':a.dist([r['target'] for r in rows]),
        'modelSHA256':digest(model),'stateRowsSHA256':digest(rows),'futureOutcomesNotInputs':True}

def meta(e):return {k:e[k] for k in ['selectorEventId','sessionDate','symbol','decisionTimestamp','originalRank','eligible','common30']}

def replay(events,entrymodel=None,exitmodel=None,delay=0):
    rows=[]
    for e in events:
        en=entry_policy(e,entrymodel) if entrymodel else fixed_entry(e,delay)
        ex=exit_policy(e,en,exitmodel) if exitmodel else fixed_exit(e,en)
        rows.append(meta(e)|{'entry':en,'exit':ex,'result':trade(e,en,ex)})
    return rows

def usable(rows):return [r for r in rows if r['common30'] and r['result'].get('net') is not None]

def flat(rows,onlytrades=False):
    return [{k:r[k] for k in ['selectorEventId','sessionDate','symbol','decisionTimestamp']}|r['result'] for r in usable(rows) if not onlytrades or r['result']['status']=='OBSERVED']

def clustered(rows,field='net',family=2):
    rr=[r for r in rows if r.get(field) is not None]
    return v.cluster(v.session_means(rr,field),family)

def summary(rows):
    rr=flat(rows);trades=flat(rows,True);n=len(rr)
    return {'originalOpportunities':len(rows),'calendarEligible':sum(r['eligible'] for r in rows),
        'commonObservedOpportunities':n,'enteredTrades':len(trades),'coverageOnCommonObserved':len(trades)/n if n else None,
        'enteredAllOriginal':sum(r['entry']['status']=='ENTERED' for r in rows),
        'policyStatusesAllOriginal':dict(collections.Counter(r['entry']['status'] for r in rows)),
        'sessions':len({r['sessionDate'] for r in rr}),'tradeSessions':len({r['sessionDate'] for r in trades}),
        'opportunityNet':a.dist([r['net'] for r in rr]),'tradeNet':a.dist([r['net'] for r in trades]),
        'opportunityCluster':clustered(rr),'tradeCluster':clustered(trades),
        'diagnosticCumulativeNetPctPoints':sum(r['net'] for r in rr),'notPortfolioReturn':True,
        'positiveSessions':sum(x>0 for x in v.session_means(rr,'net').values()),
        'path':{f:a.dist([r.get(f) for r in trades]) for f in ['gross','MFE','MAE','giveback','captureRatio','holdMinutes','entryDelay','entryPriceImprovementPct']},
        'exitReasons':dict(collections.Counter(r['reason'] for r in trades)),
        'costSensitivity':{str(c):a.dist([r['gross']-c for r in trades]) for c in [.05,.1,.2]},
        'scope':'COMMON_FULL0_30_OBSERVATION_CONDITIONAL; ABSTAIN_ZERO_IS_POLICY_NOT_MISSING_IMPUTATION'}

def paired(candidate,baseline):
    x={r['selectorEventId']:r for r in usable(candidate)};y={r['selectorEventId']:r for r in usable(baseline)}
    assert {r['selectorEventId'] for r in candidate}=={r['selectorEventId'] for r in baseline}
    ids=sorted(x.keys()&y.keys());left=[x[i] for i in ids];right=[y[i] for i in ids]
    delta=[{k:x[i][k] for k in ['selectorEventId','sessionDate','decisionTimestamp','symbol']}|{'net':x[i]['result']['net']-y[i]['result']['net']} for i in ids]
    return {'pairedN':len(ids),'sessions':len({r['sessionDate'] for r in left}),'identitySHA256':a.digest(ids),
        'candidate':summary(left),'baseline':summary(right),'delta':clustered(delta),'deltaDistribution':a.dist([r['net'] for r in delta]),
        'allOriginalN':len(candidate),'conditionalOnObservability':True,'unknownPricesImputed':False}

def economic_gate(comparison,kind):
    c=comparison['candidate'];b=comparison['baseline'];ci=comparison['delta']['simultaneousCI95'];coverage=c['coverageOnCommonObserved']
    checks={'sampleSessions':comparison['sessions']>=12,'samplePaired':comparison['pairedN']>=100,
        'enteredTrades':c['enteredTrades']>=50,'coverage':coverage is not None and coverage>=.10,
        'pairedEconomicDelta':ci[0] is not None and ci[0]>0,
        'p05NotWorse':c['opportunityNet'].get('p05') is not None and b['opportunityNet'].get('p05') is not None and c['opportunityNet']['p05']>=b['opportunityNet']['p05']}
    pf=c['tradeNet']['PF'];bp=b['tradeNet']['PF']
    if kind=='entry':
        ac=c['tradeCluster']['simultaneousCI95'];checks.update(absoluteNetPositive=ac[0] is not None and ac[0]>0,PF=pf is not None and pf>1)
    else:checks['PFNotWorse']=pf is not None and bp is not None and pf>=bp
    return {'pass':all(checks.values()),'checks':checks,'status':'ECONOMIC_GATE_PASS' if all(checks.values()) else 'ECONOMIC_GATE_NOT_PASSED'}

def tail(rows):
    rs=flat(rows,True)
    return {'status':'EVALUABLE' if rs else 'NOT_APPLICABLE','tail':a.tails(rs),
        'expectedShortfall5Pct':statistics.mean(sorted(r['net'] for r in rs)[:max(1,math.ceil(.05*len(rs)))]) if rs else None}

def concentration(rows):
    rr=flat(rows,True);c=collections.Counter(r['symbol'] for r in rr);n=len(rr);top=[s for s,_ in sorted(c.items(),key=lambda x:(-x[1],x[0]))[:3]]
    return {'trades':n,'uniqueSymbols':len(c),'counts':dict(c),'HHI':sum((x/n)**2 for x in c.values()) if n else None,
        'top3ByFrequency':top,'excludingTop3DescriptiveOnly':summary([r for r in rows if r['symbol'] not in top]),'policyFilterCreated':False}

def winner_capture(candidate,baseline):
    x={r['selectorEventId']:r for r in usable(candidate)};y={r['selectorEventId']:r for r in usable(baseline)};ids=sorted(x.keys()&y.keys());out={}
    for t in [3,5]:
        wins=[i for i in ids if y[i]['result'].get('MFE') is not None and y[i]['result']['MFE']>=t]
        out[str(t)]={'baselineReachedN':len(wins),'candidateOpportunityRetainedN':sum((x[i]['result'].get('MFE') or 0)>=t for i in wins),
            'candidateNet':a.dist([x[i]['result']['net'] for i in wins]),'baselineNet':a.dist([y[i]['result']['net'] for i in wins]),
            'candidateGiveback':a.dist([x[i]['result'].get('giveback') for i in wins]),'baselineGiveback':a.dist([y[i]['result'].get('giveback') for i in wins])}
    losses=[i for i in ids if y[i]['result']['net']<0]
    out['loserReduction']={'n':len(losses),'delta':a.dist([x[i]['result']['net']-y[i]['result']['net'] for i in losses])}
    return {'futureConditionedEvaluatorOnly':True,'groups':out}

def horizons(events,entrymodel=None,delay=0):
    out={}
    for h in [15,30,60,90,120]:
        rs=[];statuses=collections.Counter()
        for e in events:
            en=entry_policy(e,entrymodel) if entrymodel else fixed_entry(e,delay)
            r=trade(e,en,{},h);statuses[r['status']]+=1
            if r['status']=='OBSERVED':rs.append(meta(e)|r)
        out[str(h)]={'enteredObserved':len(rs),'statusCounts':dict(statuses),'gross':a.dist([r['gross'] for r in rs]),'net':a.dist([r['net'] for r in rs]),
            'netCluster':clustered(rs),'MFE':a.dist([r.get('MFE') for r in rs]),'MAE':a.dist([r.get('MAE') for r in rs]),
            'role':'SECONDARY_ENTRY_RELATIVE_DIFFERENT_ENDPOINTS_NOT_HORIZON_SEARCH'}
    return out

def frozen_comparison(events,entrymodel=None):
    runtime=frozen_exit.mod('recoverability_frozen_runtime',ROOT/'predict/long-only/phase57_long_exit_continuation_v1.py')
    ledger=[];statuses=collections.Counter()
    for e in events:
        en=entry_policy(e,entrymodel) if entrymodel else fixed_entry(e)
        if en['status']!='ENTERED':statuses[en['status']]+=1;continue
        start=a.old.timestamp(en['timestamp']);bs=[b for b in e['bars'] if b['start']>=start];future=[]
        for j,b in enumerate(bs,1):
            rr={'slot':j,'start':b['start'].isoformat(),'end':b['end'].isoformat(),'minutes':(b['end']-start).total_seconds()/60,'missing':not b['valid']}
            if b['valid']:
                for k in ['o','h','l','c']:rr[k]=100*(b[k]/en['price']-1)
            future.append(rr)
        adapted={'direction':'LONG','expectedBars':len(bs),'future':future};fixed=runtime.replay(adapted,'FIXED12')
        if fixed['status']!='EXIT_REFERENCE':statuses[fixed['status']]+=1;continue
        result=frozen_exit.policy(future[:fixed['exitBar']],fixed)
        ledger.append(meta(e)|{'fixedNet':fixed['netPct'],'frozenNet':result['netPct'],'delta':result['netPct']-fixed['netPct'],'reason':result['status']})
    return {'status':'EVALUATED_UNCHANGED_FROZEN_FUNCTIONS','n':len(ledger),'statuses':dict(statuses),'fixed12Net':a.dist([r['fixedNet'] for r in ledger]),
        'frozenExitNet':a.dist([r['frozenNet'] for r in ledger]),'delta':clustered([r|{'net':r['delta']} for r in ledger]),
        'ledger':ledger,'role':'SEPARATE_FIXED12_OR_CALENDAR_CAP_COMPARISON_NOT_THE_PRIMARY30_GATE','sourceFunctionChanged':False}

def four_cells(cells):
    if len(cells)!=4:return {'status':'NOT_APPLICABLE','reason':'BOTH_QUALIFICATION_CANDIDATES_REQUIRED','availableCells':list(cells)}
    maps={k:{r['selectorEventId']:r for r in usable(rs)} for k,rs in cells.items()};ids=sorted(set.intersection(*(set(m) for m in maps.values())))
    terms={'entry':{'10':1,'00':-1},'exit':{'01':1,'00':-1},'interaction':{'11':1,'10':-1,'01':-1,'00':1},'total':{'11':1,'00':-1}}
    stats={}
    for term,coefs in terms.items():
        rows=[{k:maps['00'][i][k] for k in ['selectorEventId','sessionDate','decisionTimestamp','symbol']}|{'net':sum(c*maps[cell][i]['result']['net'] for cell,c in coefs.items())} for i in ids]
        stats[term]=clustered(rows)
    return {'status':'EVALUATED_FOUR_CELLS','pairedN':len(ids),'identitySHA256':a.digest(ids),'cells':{k:summary([m[i] for i in ids]) for k,m in maps.items()},'contributions':stats,'capitalUsed':False}

def not_applicable(reason):return {'status':'NOT_APPLICABLE','reason':reason}

def run(out):
    p=protocol();out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for f in ['01_start_state.json','02_protocol_precommit.md','protocol.json','protocol-lock.json']:shutil.copy2(BASE/f,out/f)
    all_events=load_events();parts={k:[e for e in all_events if e['sessionDate'] in days] for k,days in p['split'].items()}
    assert sum(map(len,parts.values()))==3800 and all(len(events)==50*len(p['split'][k]) for k,events in parts.items())
    write(out/'03_data_feature_availability.json',{'available':p['availability']['available'],'unavailable':p['availability']['unavailable'],
        'features':p['features'],'normalizerContract':'availableAtJst=barStart+5m; saved OHLC prefix states only','sourcePathsSHA256':sha(a.old.FROZEN_PATHS),
        'rows':{k:{'all':len(rs),'calendarEligible':sum(e['eligible'] for e in rs),'commonComplete30':sum(e['common30'] for e in rs),'sessions':p['split'][k]} for k,rs in parts.items()},
        'protectedDataOpened':False,'futureAnatomyUsedAsFeatures':False,'volumeOrVWAPInvented':False})
    write(out/'05_entry_target_contract.json',p['entryTarget']|{'split':p['split'],'model':p['model']})
    write(out/'10_exit_target_contract.json',p['exitTarget']|{'split':p['split'],'model':p['model']})
    train_e,ta=labelled_states(parts['FIT'],'entry');qual_e,qa=labelled_states(parts['QUALIFY'],'entry')
    em=fit(train_e,EF,p['split']['FIT']);ed=diagnostic(em,qual_e,qa)
    qbase=replay(parts['QUALIFY']);eq=None;eqg=not_applicable('ENTRY_DIAGNOSTIC_GATE_NOT_PASSED');entry_ok=False
    if ed['pass']:
        trial=replay(parts['QUALIFY'],em);eq=paired(trial,qbase);eqg=economic_gate(eq,'entry');entry_ok=eqg['pass']
    # Exit route is decided using QUALIFY only. REPORT outcomes never rescue a failed candidate.
    route=em if entry_ok else None
    entry_by_split={k:{e['selectorEventId']:(entry_policy(e,route) if route else fixed_entry(e)) for e in parts[k]} for k in ['FIT','QUALIFY']}
    train_x,txa=labelled_states(parts['FIT'],'exit',entry_by_split['FIT']);qual_x,qxa=labelled_states(parts['QUALIFY'],'exit',entry_by_split['QUALIFY'])
    xm=fit(train_x,XF,p['split']['FIT']);xd=diagnostic(xm,qual_x,qxa)
    xq=None;xqg=not_applicable('EXIT_DIAGNOSTIC_GATE_NOT_PASSED');exit_ok=False
    if xd['pass']:
        xq=paired(replay(parts['QUALIFY'],route,xm),replay(parts['QUALIFY'],route));xqg=economic_gate(xq,'exit');exit_ok=xqg['pass']
    lock={'entryAcceptedOnQualification':entry_ok,'exitAcceptedOnQualification':exit_ok,'exitRoute':'CANDIDATE_ENTRY' if entry_ok else 'IMMEDIATE_ENTRY',
        'entryDiagnosticModel':em,'exitDiagnosticModel':xm,'entryModelSHA256':digest(em),'exitModelSHA256':digest(xm),
        'entryQualificationDiagnostic':ed,'exitQualificationDiagnostic':xd,'entryQualificationEconomicGate':eqg,'exitQualificationEconomicGate':xqg,
        'noReportOutcomesUsed':True,'candidateFreeze':False,'promotion':False}
    write(out/'qualification-lock.json',lock);lock_hash=sha(out/'qualification-lock.json')
    # The REPORT partition is evaluated only after both models, route and gates have been locked.
    report=parts['REPORT'];report_e,rea=labelled_states(report,'entry')
    re_diag=diagnostic(em,report_e,rea)
    route_entries={e['selectorEventId']:(entry_policy(e,route) if route else fixed_entry(e)) for e in report}
    report_x,rxa=labelled_states(report,'exit',route_entries);rx_diag=diagnostic(xm,report_x,rxa)
    base=replay(report);delay=replay(report,delay=5);entry_rows=replay(report,em) if entry_ok else None
    exit_rows=replay(report,route,xm) if exit_ok else None;route_base=replay(report,route)
    ep=paired(entry_rows,base) if entry_ok else not_applicable('ENTRY_QUALIFICATION_GATE_NOT_PASSED')
    xp=paired(exit_rows,route_base) if exit_ok else not_applicable('EXIT_QUALIFICATION_GATE_NOT_PASSED')
    eg=economic_gate(ep,'entry') if entry_ok else {'pass':False,'status':'NO_QUALIFIED_ENTRY_CANDIDATE'}
    xg=economic_gate(xp,'exit') if exit_ok else {'pass':False,'status':'NO_QUALIFIED_EXIT_CANDIDATE'}
    cells={'00':base}
    if entry_ok:cells['10']=entry_rows
    if exit_ok:cells['01']=replay(report,None,xm)
    if entry_ok and exit_ok:cells['11']=exit_rows
    integrated=four_cells(cells)
    sufficient=min(qa['sessions'],qxa['sessions'],rea['sessions'],rxa['sessions'])>=12 and min(qa['identifiedStates'],qxa['identifiedStates'],rea['identifiedStates'],rxa['identifiedStates'])>=100 and em is not None and xm is not None and min(len(usable(base)),len(usable(qbase)))>=100
    if eg['pass'] and xg['pass']:decision='A_KEEP_SELECTOR_DEVELOP_CAUSAL_ENTRY_EXIT'
    elif eg['pass']:decision='B_KEEP_SELECTOR_ENTRY_ONLY'
    elif xg['pass']:decision='C_KEEP_SELECTOR_EXIT_ONLY'
    elif not sufficient:decision='E_MORE_DEVELOPMENT_DATA_NEEDED'
    else:decision='F_INCONCLUSIVE'
    final={'decision':decision,'entryCandidate':entry_ok,'exitCandidate':exit_ok,'entryReportGate':eg,'exitReportGate':xg,
        'entryQualificationGate':eqg,'exitQualificationGate':xqg,'enoughStatesForDiagnostic':sufficient,
        'reason':'Only precommitted specifications tested; failure is not proof no causal policy can work. Missingness and historical Development exposure remain.',
        'fullPopulationEconomicEdge':'NOT_IDENTIFIED_WITH_MISSING_MARKS','actualExecutionProfit':'NOT_VERIFIED',
        'nextStep':'Review the failed/passing gate and PIT-observability report to decide one next Development protocol; no automatic extra search, sealed-data opening or promotion.',
        'candidateFreeze':False,'stop':True}
    write(out/'04_entry_recoverability_diagnostic.json',{'status':'ENTRY_RECOVERABILITY_SUPPORTED_ON_QUALIFY' if ed['pass'] else 'ENTRY_RECOVERABILITY_NOT_DEMONSTRATED',
        'fitAvailability':ta,'qualification':ed,'report':re_diag,'candidateNotRescuedByReport':True})
    write(out/'06_entry_candidate_spec.json',{'status':'RESEARCH_CANDIDATE_NOT_FROZEN' if entry_ok else 'NOT_APPLICABLE','reason':None if entry_ok else 'ENTRY_QUALIFICATION_GATE_NOT_PASSED',
        'diagnosticGatePassed':ed['pass'],'economicGate':eqg,'modelSHA256':digest(em) if entry_ok else None,'recipe':p['entryTarget']['candidate'],'threshold':0,'searchedVariants':1})
    write(out/'07_entry_candidate_measurement.json',{'qualificationTrial':eq or not_applicable('NO_PIT_SEPARATION_NO_POLICY_TRIAL'),
        'report':summary(entry_rows) if entry_ok else not_applicable('NO_QUALIFIED_ENTRY_CANDIDATE'),
        'baselines':{'Immediate':summary(base),'FixedDelay5':summary(delay)},
        'entryRelativeHorizons':{'Immediate':horizons(report),'FixedDelay5':horizons(report,delay=5),'Candidate':horizons(report,em) if entry_ok else not_applicable('NO_CANDIDATE')}})
    write(out/'08_entry_vs_immediate_paired.json',{'candidate':ep,'fixedDelay5':paired(delay,base),'primary':'SAME_SELECTION30_TERMINAL'})
    frozen=frozen_comparison(report,route)
    write(out/'09_exit_recoverability_diagnostic.json',{'status':'EXIT_RECOVERABILITY_SUPPORTED_ON_QUALIFY' if xd['pass'] else 'EXIT_RECOVERABILITY_NOT_DEMONSTRATED',
        'fitAvailability':txa,'qualification':xd,'report':rx_diag,'route':lock['exitRoute'],'unchangedFrozenExitComparator':frozen})
    write(out/'11_exit_candidate_spec.json',{'status':'RESEARCH_CANDIDATE_NOT_FROZEN' if exit_ok else 'NOT_APPLICABLE','reason':None if exit_ok else 'EXIT_QUALIFICATION_GATE_NOT_PASSED',
        'diagnosticGatePassed':xd['pass'],'economicGate':xqg,'modelSHA256':digest(xm) if exit_ok else None,'recipe':p['exitTarget']['candidate'],'threshold':0,'searchedVariants':1})
    write(out/'12_exit_candidate_measurement.json',{'qualificationTrial':xq or not_applicable('NO_PIT_SEPARATION_NO_POLICY_TRIAL'),
        'report':summary(exit_rows) if exit_ok else not_applicable('NO_QUALIFIED_EXIT_CANDIDATE'),'baseline':summary(route_base),
        'winnerLoser':winner_capture(exit_rows,route_base) if exit_ok else not_applicable('NO_CANDIDATE')})
    write(out/'13_exit_vs_baseline_paired.json',xp)
    write(out/'14_integrated_four_cell_comparison.json',integrated)
    qualification_trials={'Immediate':qbase,'ExitRouteBaseline':replay(parts['QUALIFY'],route)}
    if ed['pass']:qualification_trials['EntryTrial']=replay(parts['QUALIFY'],em)
    if xd['pass']:qualification_trials['ExitTrial']=replay(parts['QUALIFY'],route,xm)
    write(out/'15_path_capture_metrics.json',{'cells':{k:summary(rs)['path'] for k,rs in cells.items()},
        'qualificationTrials':{k:summary(rs)['path'] for k,rs in qualification_trials.items()},
        'qualificationExitWinnerCapture':winner_capture(qualification_trials['ExitTrial'],qualification_trials['ExitRouteBaseline']) if xd['pass'] else not_applicable('NO_EXIT_TRIAL'),
        'immediateExitWinnerCapture':winner_capture(cells['01'],cells['00']) if '01' in cells else not_applicable('NO_EXIT_CANDIDATE'),
        'candidateEntryExitWinnerCapture':winner_capture(cells['11'],cells['10']) if '11' in cells else not_applicable('NO_TWO_CANDIDATES'),'futureWinnerInformationUsedInPolicy':False})
    diagnostic_groups={'REPORT_'+k:rs for k,rs in cells.items()}|{'QUALIFY_'+k:rs for k,rs in qualification_trials.items()}
    write(out/'16_tail_risk.json',{k:tail(rs) for k,rs in diagnostic_groups.items()})
    write(out/'17_session_stability.json',{k:{'sessionNet':v.session_means(flat(rs),'net'),'counts':dict(collections.Counter(r['sessionDate'] for r in flat(rs)))} for k,rs in diagnostic_groups.items()})
    write(out/'18_symbol_concentration.json',{k:concentration(rs) for k,rs in diagnostic_groups.items()})
    write(out/'19_cluster_statistics.json',{'entry':ep,'exit':xp,'integrated':integrated,'statistics':p['statistics'],'independentRowsAssumed':False})
    write(out/'20_final_decision.json',final)
    write(out/'24_safety_data_boundary.json',{'safety':p['safety'],'sealed':p['sealed'],'newProviderRequests':0,'selectorChanged':False,'capitalChanged':False,
        'entryDiagnosticFits':int(em is not None),'exitDiagnosticFits':int(xm is not None),'refitAfterQualification':False,'candidateFreezeOrPromotion':False,
        'qualificationLockSHA256':lock_hash,'reportReadAfterLock':True,'original3800IdentitySHA256':a.digest([e['selectorEventId'] for e in all_events]),
        'splitSessionsDisjoint':True,'labelsWithinSession':all(r['labelEnd'][:10]==r['sessionDate'] for r in train_e+qual_e+report_e+train_x+qual_x+report_x),
        'intradayLabelOverlap':'Present; grouped by session, no random row split','sourcePathsSHA256':sha(a.old.FROZEN_PATHS)})
    write(out/'state-label-audit.json.gz',{'role':'EVALUATOR_ONLY_NOT_POLICY','entry':{'FIT':train_e,'QUALIFY':qual_e,'REPORT':report_e},'exit':{'FIT':train_x,'QUALIFY':qual_x,'REPORT':report_x}})
    write(out/'opportunity-ledger.json.gz',{'allOriginalIdentities':[meta(e) for e in all_events],'REPORT':cells,'fixedDelay5':delay,
        'QUALIFY':{'immediate':qbase,'entryTrial':replay(parts['QUALIFY'],em) if ed['pass'] else None,'exitTrial':replay(parts['QUALIFY'],route,xm) if xd['pass'] else None}})
    text=render(final,ed,xd,re_diag,rx_diag,eq,xq,ep,xp,integrated,summary(base),frozen)
    (out/'25_final_report.md').write_text(text)
    (out/'26_final_handoff.md').write_text('# Final handoff — STOP\n\n'+text+'\n\nProtocol precommit: `afb32cb7f17d8f9abdfe516e156ba0bf9c677ed5`. Producing HEAD / CI recorded in23_ci.json. No next research task, protected-data opening or candidate freeze/promotion was executed.\n')
    code=['scripts/phase57_causal_entry_exit.py','scripts/test_phase57_causal_entry_exit.py','.github/workflows/phase57-causal-entry-exit-recoverability-v1.yml']
    write(out/'manifest.json',{'protocolSHA256':sha(P),'code':{f:sha(ROOT/f) for f in code},'outputs':{f.name:sha(f) for f in sorted(out.iterdir())},'qualificationLockSHA256':lock_hash})
    print(json.dumps({'status':'CAUSAL_ENTRY_EXIT_RESEARCH_COMPLETE','decision':final,'entryDiagnostic':ed['status'],'exitDiagnostic':xd['status']}))

def render(final,ed,xd,er,xr,eq,xq,ep,xp,integrated,base,frozen):
    def f(x):return 'N/A' if x is None else f'{x:.4f}'
    lines=['# Frozen Selector → Causal Entry / EXIT Recoverability','',f"**Final Decision: {final['decision']}**",'',
        '既存76 Developmentのみ。FIT38 (2024-09-17〜11-12)、QUALIFY19 (11-13〜12-09)、REPORT19 (12-10〜2025-01-09)。すでに結果露出済みでSelectorの過去fitも含むため、独立した未知性能ではない。',
        'PIT入力は確定済みOHLCと固定スコア/順位。15/20/25分の状態から次OPEN参照。全日Low/High・future MFE/MAE・winnerラベルはdecisionに渡さない。出来高/RVOL/VWAPは未保存で不使用。',
        '各1仕様のridge、alpha1、予測値>0だけ。資格判定後の再fit/threshold/horizon選び直しはなし。判断後OPENとcanonical5bpsは比較用referenceで、実約定・spread/impact込み利益を保証しない。','',
        '| diagnostic | phase | states | sessions | economic target rankIC | simultaneous CI | separation gate |','|---|---|---:|---:|---:|---|---|']
    for name,q,r in [('Entry',ed,er),('EXIT',xd,xr)]:
        for phase,d in [('QUALIFY',q),('REPORT',r)]:
            ic=d.get('rankIC',{});av=d['availability'];lines.append(f"| {name} | {phase} | {av['identifiedStates']} | {av['sessions']} | {f(ic.get('sessionEqualMean'))} | {ic.get('simultaneousCI95')} | {d['pass']} |")
    lines+=['','REPORTの分離診断が良くても、QUALIFYで失敗した候補を復活させない。', '',
        f"Entry候補: {final['entryCandidate']}。EXIT候補: {final['exitCandidate']}。候補がない場合はNOT_APPLICABLE理由を保存。",'',
        '| comparison | phase | paired opportunities | sessions | candidate mean net/trade % | baseline mean net/trade % | opportunity paired delta pp | simultaneous CI |','|---|---|---:|---:|---:|---:|---:|---|']
    for name,q,r in [('Entry',eq,ep),('EXIT',xq,xp)]:
        for phase,c in [('QUALIFY',q),('REPORT',r)]:
            if not c or 'pairedN' not in c:continue
            lines.append(f"| {name} | {phase} | {c['pairedN']} | {c['sessions']} | {f(c['candidate']['tradeNet']['mean'])} | {f(c['baseline']['tradeNet']['mean'])} | {f(c['delta']['sessionEqualMean'])} | {c['delta']['simultaneousCI95']} |")
    lines+=['',f"Entry qualification gate: {json.dumps(final['entryQualificationGate'],ensure_ascii=False)}",f"EXIT qualification gate: {json.dumps(final['exitQualificationGate'],ensure_ascii=False)}",'',
        f"REPORT Immediate baseline: {base['enteredTrades']} entered / {base['commonObservedOpportunities']} common observed / {base['originalOpportunities']} original opportunities。mean net {f(base['tradeNet']['mean'])}%、median {f(base['tradeNet']['median'])}%、PF {f(base['tradeNet']['PF'])}。",'',
        'Primaryは同じselection+30終点、原IDペア、完全0〜30経路に条件付けた比較。データ欠測はnull、PIT判断による意図的ABSTAINだけopportunity return0。約定tradeと全opportunity分母を別保存。欠測による全原母集団の収益は未同定。', '',
        f"Four-cell: {integrated['status']}。"+('全セル共通IDでEntry/EXIT/interactionを14番に保存。' if integrated['status']=='EVALUATED_FOUR_CELLS' else '両候補がQUALIFY Gateを通過していないため統合候補を捏造しない。'),'',
        f"既存Frozen EXIT(+3/+1)は未変更の関数で、元のFixed12/カレンダーcapと別比較。n={frozen['n']}、Fixed12 mean {f(frozen['fixed12Net']['mean'])}% → Frozen EXIT {f(frozen['frozenExitNet']['mean'])}%。これはprimary30モデル候補の成績ではない。",'',
        '## 解釈と次工程','',
        ('利益改善はREPORTの同一ID paired差で判定。Entry・EXITの単独寄与とinteractionを区別する。' if final['entryReportGate']['pass'] or final['exitReportGate']['pass'] else '今回の固定仕様では、採用できる因果的な利益改善を確認できなかった。oracleの値幅の存在から、その底/天井をPIT識別できるとは結論しない。'),
        '失敗は「あらゆるEntry/EXITが不可能」や「Selector再設計が必ず有効」を意味しない。時系列分割でも既知Development、欠測、繰り返し銘柄、実約定可能性は未解決。CIはsession単位、5-session block感度・tail・集中度も保存。',
        final['nextStep'],'',
        '17〜19番はsession・symbol・cluster、21〜23番はtests/regression/CI。Safety9項目false、DEV TEST/Fresh/OOS sealed、新規provider0。Selector/Capital未変更、既存Frozen Entry/EXIT未変更、候補の正式freeze/promotionなし、main mergeなし。ここでSTOP。','']
    return '\n'.join(lines)

def audit(directory=None):
    p=protocol();assert len(l.members()[a.ARMS[0]])==3800
    if directory:
        d=Path(directory);m=read(d/'manifest.json');assert m['protocolSHA256']==sha(P)
        for f,h in m['outputs'].items():assert sha(d/f)==h,f
        for f,h in m['code'].items():assert sha(ROOT/f)==h,f
        lock=read(d/'qualification-lock.json');assert m['qualificationLockSHA256']==sha(d/'qualification-lock.json')
        for key in ['entryDiagnosticModel','exitDiagnosticModel']:
            model=lock[key]
            if model:assert set(model['fitSessions'])<=set(p['split']['FIT'])
        labels=read(d/'state-label-audit.json.gz')
        for side in ['entry','exit']:
            for phase,rs in labels[side].items():
                assert all(r['sessionDate'] in p['split'][phase] and r['labelEnd'][:10]==r['sessionDate'] and r['state']['maxInputBarEnd']<=r['stateTimestamp']<r['labelEnd'] for r in rs)
        ids=read(d/'opportunity-ledger.json.gz')['allOriginalIdentities'];assert len(ids)==3800 and a.digest([r['selectorEventId'] for r in ids])==a.digest(read(a.MEMBERSHIP)['arms'][a.ARMS[0]])
        if (d/'ci-manifest.json').exists():
            c=read(d/'ci-manifest.json');assert c['measurementManifestSHA256']==sha(d/'manifest.json')
            for f,h in c['outputs'].items():assert sha(d/f)==h
    print('CAUSAL_ENTRY_EXIT_AUDIT_PASS')

def finalize(directory,regression,head,run_id):
    d=Path(directory);r=Path(regression);audit(d)
    log=(r/'targeted-tests.log').read_text();m=re.search(r'Ran (\d+) tests?',log);assert m and '\nOK' in log
    report=read(r/'full/regression.json');assert report['status']=='PASS'
    write(d/'21_tests.json',{'status':'PASS','dedicatedTests':int(m[1]),'logSHA256':sha(r/'targeted-tests.log'),'deterministicFullRealRegeneration':'two CI runs identical manifests'})
    write(d/'22_regression.json',report)
    write(d/'23_ci.json',{'measurement':'SUCCESS','regression':'SUCCESS','preservation':'RUNNING_AT_CREATION_VERIFY_FINAL_LINK','producingHead':head,
        'protocolPrecommit':'afb32cb7f17d8f9abdfe516e156ba0bf9c677ed5','runId':str(run_id),'url':f'https://github.com/Iam-2squared/ark-terminal/actions/runs/{run_id}',
        'oldUnrelatedGatesNotCleared':['EXIT CC Freeze Audit','old Economic Alpha immutable-output guard']})
    write(d/'ci-manifest.json',{'measurementManifestSHA256':sha(d/'manifest.json'),'outputs':{f:sha(d/f) for f in ['21_tests.json','22_regression.json','23_ci.json']}})

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('measure');x.add_argument('--output-dir',required=True)
    x=sub.add_parser('audit');x.add_argument('--directory')
    x=sub.add_parser('finalize')
    for f in ['directory','regression','head','run-id']:x.add_argument('--'+f,required=True)
    args=p.parse_args()
    if args.command=='measure':run(args.output_dir)
    elif args.command=='audit':audit(args.directory)
    else:finalize(args.directory,args.regression,args.head,args.run_id)

if __name__=='__main__':main()
