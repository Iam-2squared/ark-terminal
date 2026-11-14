"""Evaluator-only Future Path, fixed-population diagnostics and research replay."""
import argparse
import collections
import json
from pathlib import Path
import numpy as np
from scripts import phase57_entry_timing_census as c
from scripts import phase57_causal_entry_state as st

s,e=c.s,c.e
BASE=e.ROOT/'docs/evidence/phase57-causal-entry-state-v1'
SRC=c.SOURCE/'substrate'
CENSUS=s.BASE/'measurement'
PATHS=('DIRECT_CONTINUATION','PULLBACK_RECOVERY','CONSOLIDATION_BREAKOUT','MULTI_SWING_CHOP','PERSISTENT_WEAKNESS','AMBIGUOUS_INSUFFICIENT')
ARMS={'A':['IMMEDIATE'],'B':['EARLY'],'C':['APPROPRIATE'],'F':[]}
CHECKPOINTS=(0,5,10,15,30)


def verify():
    assert c.sha(BASE/'PROTOCOL.md')==c.read(BASE/'protocol-lock.json')['sha256']
    p=s.verify()
    for name,h in c.read(CENSUS/'manifest.json').items():assert c.sha(CENSUS/name)==h,name
    return p


def opportunities():
    ids=set(s.verify()['opportunityIds'])
    # Project identity only; never copy Dictionary, rank or score into State.
    return sorted([{'id':o['id'],'session':o['session'],'symbol':o['symbol'],
                    'origin':{'decisionTimestamp':o['origin']['decisionTimestamp'],'decisionPrice':o['origin']['decisionPrice']},
                    'selectorOutcome':o['selectorOutcome']} for o in c.read(SRC/'opportunities.json.gz') if o['id'] in ids],key=lambda o:o['id'])


def restore(archives,cache,output):
    import subprocess
    p=verify();allowed=set(p['developmentSessions']);receipts=[]
    for f in sorted(Path(archives).rglob('*.tar.gz.enc')):
        expected=f.with_name(f.name+'.sha256').read_text().split()[0]
        assert c.sha(f)==expected,'ARCHIVE_HASH'
        proc=subprocess.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','200000','-pass','env:JQUANTS_API_KEY','-in',str(f)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:r=e.f.s.admission.base.extract_stream(proc.stdout,cache,allowed)
        finally:proc.stdout.close();proc.stderr.read();code=proc.wait()
        assert code==0,'DECRYPT_FAILED'
        assert set(r['selectedDates'])<=allowed
        receipts.append({'archiveSha256':expected,**r})
    assert receipts,'NO_ARCHIVES'
    c.write(output,{'receipts':receipts,'providerRequests':0,'holdoutOpened':0,'safety':p['safety']})


def daily(cache,output):
    p=verify();opps=opportunities();calendar=e.f.s.calendar();needed=collections.defaultdict(set)
    for o in opps:
        ix=calendar.index(o['session'])
        for day in calendar[ix-6:ix]:
            if day in p['developmentSessions']:needed[day].add(o['symbol'])
    pins={(x['session'],x['kind']):x['sha256'] for x in c.read(SRC/'source-ledger.json')}
    data={};ledger=[]
    for day,codes in sorted(needed.items()):
        f=Path(cache)/day/'daily-pages.json'
        if not f.exists():
            ledger.append({'day':day,'status':'MISSING_CACHE'});continue
        assert c.sha(f)==pins[day,'daily'],'DAILY_SOURCE_CHANGED'
        rows,receipt=e.v.saved.pages(f)
        assert all(r['Date']==day for r in rows)
        data[day]={r['Code']:r for r in rows if r['Code'] in codes}
        ledger.append({'day':day,'status':'AVAILABLE','sha256':c.sha(f),'symbols':len(data[day])})
    contexts={}
    for o in opps:
        day=o['session'];ix=calendar.index(day);dates=calendar[ix-6:ix]
        contexts[o['id']]=st.daily_context(day,dates,[data.get(d,{}).get(o['symbol']) for d in dates])
        for i,d in enumerate(dates):
            if d not in p['developmentSessions']:contexts[o['id']]['reasons'][i]='OUTSIDE_AUTHORIZED_DEVELOPMENT'
    c.write(output,{'contexts':contexts,'sourceLedger':ledger,'providerRequests':0,'holdoutOpened':0,'safety':p['safety']})


def reversal_count(a):
    total=0;direction=0;extreme=None;prev=None
    for row in a:
        t,price=int(row[0]),row[4]
        if prev is None or t-prev!=1:
            direction=0;extreme=price
        elif direction==0:
            if abs(s.pct(price,extreme))>=.5:direction=1 if price>extreme else -1;extreme=price
        elif direction==1:
            if price<=extreme*.995:total+=1;direction=-1;extreme=price
            else:extreme=max(extreme,price)
        else:
            if price>=extreme*1.005:total+=1;direction=1;extreme=price
            else:extreme=min(extreme,price)
        prev=t
    return total


def classify(day,start,price,a,full):
    a=c.future_rows(day,a,start)
    out={'path':PATHS[-1],'reason':None,'predicate':{k:False for k in PATHS[:-1]},'rows':len(a),'sameBarOrderUnknown':False}
    if not len(a):out['reason']='MISSING_PATH_DATA';return out
    if not full or len(a)<20 or sum(m>=start for m in e.minutes(day))<30:
        out['reason']='INSUFFICIENT_OBSERVATION';return out
    hit=a[a[:,2]>=price*1.01];dip=a[a[:,3]<=price*.995]
    same=bool(len(hit) and len(dip) and hit[0,0]==dip[0,0])
    eff=st.efficiency(a);rev=reversal_count(a);terminal=s.pct(a[-1,4],price)
    oracle=c.ordered_oracle(a,start)
    out.update(sameBarOrderUnknown=same,efficiency=eff,reversals=rev,terminalReturn=terminal,orderedRange=oracle.get('rangePct'))
    pred=out['predicate']
    pred[PATHS[0]]=bool(len(hit) and (not len(dip) or hit[0,0]<dip[0,0]) and terminal>=0 and eff>=.2)
    running_low=None
    for row in a:
        if running_low is not None and running_low<=price*.995 and row[2]>=running_low*1.02 and a[-1,4]>=running_low*1.01:
            pred[PATHS[1]]=True
        running_low=min(running_low,row[3]) if running_low is not None else row[3]
    regular=s.regular(day,a)
    for i in range(10,len(regular)):
        w=regular[i-10:i]
        if np.any(np.diff(w[:,0])!=1):continue
        h,l=max(w[:,2]),min(w[:,3]);mean=float(np.mean(w[:,2]-w[:,3]))
        if 100*(h-l)/w[0,1]>.6:continue
        for j in range(i,min(i+10,len(regular))):
            z=regular[j]
            if z[0]-w[-1,0]!=j-i+1:break
            if z[4]>=h*1.003 and z[2]-z[3]>=1.5*mean and a[-1,4]>=z[4]:pred[PATHS[2]]=True
    pred[PATHS[3]]=bool(rev>=4 and eff<=.3)
    pred[PATHS[4]]=bool(terminal<=-1 and np.mean(a[:,4]<price)>=.6 and oracle.get('rangePct',100)<2)
    yes=[k for k,v in pred.items() if v]
    if len(yes)==1:out['path']=yes[0]
    elif len(yes)>1 and pred[PATHS[3]] and rev>=6 and eff<=.15:out['path']=PATHS[3]
    else:out['reason']='TRUE_MIXED_PATH' if yes else 'NO_DOMINANT_PATH'
    return out


def low_distance(day,path,oracle,t,price,full):
    reason=None
    if t is None:reason='NO_FILL'
    elif not full:reason='INSUFFICIENT_OBSERVATION'
    elif path==PATHS[0]:reason='DIRECT_NOT_APPLICABLE'
    elif 'lowMinute' not in oracle:reason='MISSING_ORACLE'
    elif t<oracle['lowMinute']:reason='ENTRY_BEFORE_LOW'
    elif t==oracle['lowMinute']:reason='SAME_BAR_ORDER_UNKNOWN'
    return {'status':reason or 'AFTER_LOW','distancePct':s.pct(price,oracle['low']) if not reason else None,
            'delayActive':e.elapsed(day,oracle['lowMinute'],t) if not reason else None,
            'oracleLow':oracle.get('low'),'entryPrice':price}


def timebucket(t):return 'AM_EARLY' if t<600 else 'AM_LATE' if t<690 else 'PM_EARLY' if t<840 else 'PM_LATE'


def diagnostic(rows):
    result=[];predictions=[];effects=[]
    sessions=sorted({r['session'] for r in rows});split=len(sessions)//2;fitdays=set(sessions[:split])
    for checkpoint in CHECKPOINTS:
        rr=[r for r in rows if r['checkpoint']==checkpoint]
        for variant in ('INTRADAY','PLUS_DAILY'):
            selected=[r for r in rr if r['features'] is not None]
            keys=sorted({k for r in selected for k in r['features'] if variant=='PLUS_DAILY' or not k.startswith('DAILY/')})
            train=[r for r in selected if r['session'] in fitdays];test=[r for r in selected if r['session'] not in fitdays]
            if not train or not test:continue
            x=np.array([[r['features'].get(k) if r['features'].get(k) is not None else np.nan for k in keys] for r in train],float)
            y=np.array([[r['features'].get(k) if r['features'].get(k) is not None else np.nan for k in keys] for r in test],float)
            keep=np.any(np.isfinite(x),axis=0);x=x[:,keep];y=y[:,keep];kk=[k for k,q in zip(keys,keep) if q]
            med=np.nanmedian(x,axis=0);missx=~np.isfinite(x);missy=~np.isfinite(y)
            x=np.where(missx,med,x);y=np.where(missy,med,y);mu=x.mean(0);sd=x.std(0);sd[sd==0]=1
            x=np.column_stack([(x-mu)/sd,missx]);y=np.column_stack([(y-mu)/sd,missy])
            classes=sorted({r['path'] for r in train});centers=np.array([x[[r['path']==cl for r in train]].mean(0) for cl in classes])
            guesses=np.argmin(((y[:,None,:]-centers[None,:,:])**2).sum(2),axis=1)
            conf=collections.Counter();bymonth=collections.defaultdict(list);bysession=collections.defaultdict(list);bytime=collections.defaultdict(list)
            for r,g in zip(test,guesses):
                pred=classes[g];conf[r['path']+'|'+pred]+=1;ok=pred==r['path']
                bymonth[r['session'][:7]].append(ok);bysession[r['session']].append(ok);bytime[r['timeBucket']].append(ok)
                predictions.append({'opportunity':r['opportunity'],'checkpoint':checkpoint,'variant':variant,'actualEvaluatorOnly':r['path'],'prediction':pred})
            rec=[conf[cl+'|'+cl]/sum(r['path']==cl for r in test) for cl in PATHS if any(r['path']==cl for r in test)]
            result.append({'checkpoint':checkpoint,'variant':variant,'fitN':len(train),'testN':len(test),'missingCheckpointN':len(rr)-len(selected),
                           'accuracy':sum(conf[cl+'|'+cl] for cl in PATHS)/len(test),'balancedAccuracy':float(np.mean(rec)),
                           'confusion':dict(conf),'classesInFit':classes,'features':kk,'fitMedian':med.tolist(),'fitMean':mu.tolist(),'fitSD':sd.tolist(),'centroids':centers.tolist(),
                           'monthAccuracy':{k:float(np.mean(v)) for k,v in bymonth.items()},'sessionAccuracy':{k:float(np.mean(v)) for k,v in bysession.items()},'timeAccuracy':{k:float(np.mean(v)) for k,v in bytime.items()}})
        selected=[r for r in rr if r['features'] is not None]
        keys=sorted({k for r in selected for k in r['features']})
        for key in keys:
            for cl in PATHS:
                inside=[r['features'][key] for r in selected if r['path']==cl and r['features'].get(key) is not None]
                outside=[r['features'][key] for r in selected if r['path']!=cl and r['features'].get(key) is not None]
                pooled=np.sqrt((np.var(inside,ddof=1)+np.var(outside,ddof=1))/2) if len(inside)>1 and len(outside)>1 else 0
                effects.append({'checkpoint':checkpoint,'path':cl,'feature':key,'inside':c.dist(inside),'outside':c.dist(outside),
                                'standardizedMeanDifference':float((np.mean(inside)-np.mean(outside))/pooled) if pooled>0 else None})
    return {'fits':result,'fitSessions':sessions[:split],'testSessions':sessions[split:],'scope':'REUSED_DEVELOPMENT_DIAGNOSTIC_NOT_ENTRY_TRAINING'},predictions,effects


def run(dailyfile,output):
    p=verify();out=Path(output);out.mkdir(parents=True,exist_ok=False)
    dd=c.read(dailyfile);opps=opportunities();ids={o['id'] for o in opps}
    assert set(dd['contexts'])==ids
    rawpaths=c.read(SRC/'raw-paths-evaluator-only.json.gz');labs=c.read(SRC/'outcomes.json.gz')
    quotes={r['id']:r['quoteAvailable'] for r in c.read(SRC/'rows.json.gz') if r['opportunity'] in ids and r['eligible1']}
    baseline={t['opportunity']:t for t in c.read(CENSUS/'trades.json.gz')['A']}
    records=[];trades={k:[] for k in ARMS};paired={k:[] for k in ARMS};checks=[]
    transitions=collections.Counter();signals=collections.defaultdict(lambda:collections.Counter());statepath=collections.Counter()
    dayrows=[];lastday=None;signalrows={};firstsignals=[]
    for no,o in enumerate(opps):
        oid,day=o['id'],o['session'];start=e.old.minute(o['origin']['decisionTimestamp']);dailyctx=dd['contexts'][oid]
        if day!=lastday:
            if lastday:c.write(out/'states'/(lastday+'.json.gz'),dayrows)
            dayrows=[];signalrows=collections.defaultdict(list)
            for z in c.read(CENSUS/'minute-census'/(day+'.json.gz')):signalrows[z['opportunity']].append(z)
            lastday=day
        path=rawpaths.pop(oid);a=np.asarray(path['today'],float).reshape(-1,7);prev=np.asarray(path['previous'],float).reshape(-1,7)
        grid=s.comparison_grid(day,start);states={};obs={};previousstate=None;duration=0;sigfirst={}
        for z in signalrows.pop(oid):
            t=z['minute'];now=st.state(day,t,e.closed(a,t),prev,path['previousSession'],dailyctx,z['activity'])
            consecutive=previousstate is not None and t==previousstate['minute']+1 and now['newClosedBarObserved'] and previousstate['newClosedBarObserved']
            if consecutive:transitions[previousstate['state']+'|'+now['state']]+=1
            duration=duration+1 if consecutive and now['scores']['COMPRESSION'] is not None and now['scores']['COMPRESSION']>=.5 else int(now['scores']['COMPRESSION'] is not None and now['scores']['COMPRESSION']>=.5)
            now.update(compressionDuration=duration,opportunity=oid,session=day,delay=e.elapsed(day,start,t))
            states[t]=now;obs[t]={'signals':st.timing(now,z['signals'])};previousstate=now
            for f in s.FAMILIES:
                val=z['signals'][f]['trigger']
                signals[now['state']+'|'+f]['true' if val is True else 'false' if val is False else 'unknown']+=1
                if val is True and f not in sigfirst:sigfirst[f]={'minute':t,'delay':now['delay'],'state':now['state'],'timestamp':day+'T'+z['barClosedAtJst']+':00+09:00'}
            fired=[f for f in s.FAMILIES if z['signals'][f]['trigger'] is True]
            for f in fired:
                for g in fired:signals[now['state']+'|CO|'+f+'|'+g]['true']+=1
            # Activity is immutable in pinned original census, avoid duplicating large payload.
            now.pop('activity');dayrows.append(now)
        future=c.future_rows(day,a,start);full=o['selectorOutcome']['mfeEnd'] is not None
        anatomy=classify(day,start,o['origin']['decisionPrice'],a,full);oracle=c.ordered_oracle(future,start)
        state0=states.get(start,{}).get('state','UNKNOWN');statepath[state0+'|'+anatomy['path']]+=1
        firstsignals.append({'opportunity':oid,'signals':sigfirst})
        tt=s.replay(oid,day,start,obs,{t:quotes[oid+'|'+str(t)] for t in grid},{t:labs[oid+'|'+str(t)]['price'] for t in grid},ARMS)
        assert tt['A']['entryId']==baseline[oid]['entryId'],'BASELINE_CHANGED'
        for arm,tr in tt.items():
            t,price=tr['entryMinute'],tr['price'];tr['state0']=state0;tr['fillState']=states[t]['state'] if t is not None else None
            tr['strictCoverage']={str(h):c.strict_coverage(day,t,a,h) for h in (30,60)}
            tr['rangeRetention']=c.retention(oracle,t,price,full,a)
            tr['lowProximity']=low_distance(day,anatomy['path'],oracle,t,price,full)
            waiting=a[(a[:,0]>=tt['A']['entryMinute'])&(a[:,0]<t)] if t is not None and tt['A']['entryMinute'] is not None else []
            tr['waitMaxRiseVsImmediatePct']=max(0.,s.pct(max(waiting[:,2]),tt['A']['price'])) if len(waiting) else 0. if t is not None and t==tt['A']['entryMinute'] else None
            tr['waitCoverage']={'observed':len(waiting),'expected':e.elapsed(day,tt['A']['entryMinute'],t) if t is not None and tt['A']['entryMinute'] is not None else None}
            later=a[a[:,0]>t] if t is not None else []
            tr['strictLaterHighPct']=s.pct(max(later[:,2]),price) if len(later) and full else None
            tr['endMaxDD']=None;tr['endMaxDDAdverseBound']=None
            if t is not None and full:
                rr=[dict(zip(['O','H','L','C','Vo','Va'],x[1:])) for x in a[a[:,0]>=t]]
                if rr:tr['endMaxDD'],tr['endMaxDDAdverseBound']=e.ext.drawdown_bounds(price,rr)
            trades[arm].append(tr)
        for arm in ARMS:
            q=c.paired_record(tt['A'],tt[arm],labs,o['selectorOutcome'])
            q['state0']=state0;q['lowDistanceDelta']=None
            x,y=tt['A']['lowProximity']['distancePct'],tt[arm]['lowProximity']['distancePct']
            if x is not None and y is not None:q['lowDistanceDelta']=y-x
            v=q['priceImprovementPct'];flags=[]
            if v is None:flags.append('UNPAIRED')
            else:flags.append('CHEAPER' if v>1e-10 else 'DEARER' if v< -1e-10 else 'UNCHANGED')
            lost=q['captureDelta']['3']==-1
            if v is not None and v>1e-10 and lost:flags.append('CHEAPER_BUT_UPSIDE_LOST')
            if q['30']['MAE'] is not None and q['30']['MAE']>0 and lost:flags.append('MAE_IMPROVED_UPSIDE_LOST')
            if q['lowDistanceDelta'] is not None and q['lowDistanceDelta']<0 and q['rangeRetentionDeltaPp'] is not None and q['rangeRetentionDeltaPp']>=0:flags.append('LOW_CLOSER_RANGE_RETAINED')
            if tt[arm]['intentReason']=='FALLBACK':flags.append('NO_SIGNAL_FALLBACK')
            q['failureSuccessFlags']=flags;paired[arm].append(q)
        for delay in CHECKPOINTS:
            ts=[t for t,z in states.items() if z['delay']==delay];t=min(ts) if ts else None
            z=states.get(t);features=None
            if z:
                features={**z['features'],**{'SCORE/'+k:v for k,v in z['scores'].items()},**{'DAILY/'+k:v for k,v in dailyctx['features'].items()}}
                # Raw levels introduce security-price scale, normalize daily OHLC and extrema.
                ref=dailyctx['features'].get('D1/C')
                for k,v in list(features.items()):
                    if k.startswith('DAILY/') and (k.rsplit('/',1)[-1] in ('O','H','L','C','high5','low5')):features[k]=s.pct(v,ref)
                    if k.startswith('DAILY/') and k.rsplit('/',1)[-1] in ('Vo','Va'):features[k]=float(np.log1p(v)) if v is not None else None
            checks.append({'opportunity':oid,'session':day,'checkpoint':delay,'minute':t,'path':anatomy['path'],'state':z['state'] if z else None,'features':features,'timeBucket':timebucket(start)})
        records.append({'opportunity':oid,'session':day,'symbol':o['symbol'],'start':start,'state0':state0,'pathEvaluatorOnly':anatomy,'oracleEvaluatorOnly':oracle,'dailyComplete':dailyctx['complete5'],'fullSessionEvaluable':full})
        if no%100==0:print(json.dumps({'processed':no,'day':day}),flush=True)
    c.write(out/'states'/(lastday+'.json.gz'),dayrows)
    metrics={k:c.arm_summary(opps,trades[k],labs) for k in ARMS}
    assert metrics['A']['fills']==1963
    for lv in range(1,6):assert e.ext.same(metrics['A']['capture'][str(lv)]['rate'],c.read(CENSUS/'metrics.json')['A']['capture'][str(lv)]['rate'])
    summary={k:c.paired_summary(v) for k,v in paired.items()}
    for k in ARMS:
        metrics[k]['lowDistance']=c.dist(t['lowProximity']['distancePct'] for t in trades[k]);metrics[k]['lowDelay']=c.dist(t['lowProximity']['delayActive'] for t in trades[k])
        metrics[k]['lowReasons']=dict(collections.Counter(t['lowProximity']['status'] for t in trades[k]))
        metrics[k]['endMaxDD']=c.dist(t['endMaxDD'] for t in trades[k]);metrics[k]['endMaxDDAdverseBound']=c.dist(t['endMaxDDAdverseBound'] for t in trades[k])
        summary[k]['failureSuccessFlags']=dict(collections.Counter(f for r in paired[k] for f in r['failureSuccessFlags']))
    strata=[]
    for kind,fn in [('state',lambda r:r['state0']),('path',lambda r:r['pathEvaluatorOnly']['path']),('session',lambda r:r['session']),('month',lambda r:r['session'][:7]),('time',lambda r:timebucket(r['start']))]:
        for group in sorted({fn(r) for r in records}):
            ix=[i for i,r in enumerate(records) if fn(r)==group];oo=[opps[i] for i in ix]
            for arm in ARMS:
                ts=[trades[arm][i] for i in ix];ps=[paired[arm][i] for i in ix]
                strata.append({'kind':kind,'group':group,'arm':arm,'metrics':c.arm_summary(oo,ts,labs),'paired':c.paired_summary(ps),
                               'lowDistance':c.dist(t['lowProximity']['distancePct'] for t in ts),'lowReasons':dict(collections.Counter(t['lowProximity']['status'] for t in ts))})
    diag,pred,effects=diagnostic(checks)
    audit={'population':2155,'protocolSHA256':c.sha(BASE/'PROTOCOL.md'),'dailySHA256':c.sha(dailyfile),
           'pathCounts':dict(collections.Counter(r['pathEvaluatorOnly']['path'] for r in records)),
           'path6Reasons':dict(collections.Counter(r['pathEvaluatorOnly']['reason'] for r in records if r['pathEvaluatorOnly']['path']==PATHS[-1])),
           'dailyComplete':sum(r['dailyComplete'] for r in records),'dailyReasons':dict(collections.Counter(reason for d in dd['contexts'].values() for reason in d['reasons'] if reason)),
           'state0Counts':dict(collections.Counter(r['state0'] for r in records)),'statePathConfusion':dict(statepath),'stateTransitions':dict(transitions),
           'signalsByState':dict(signals),'baselineParity':True,'holdoutOpened':0,'providerRequests':0,'trainingEntry':False,'dictionaryUsed':False,'safety':p['safety']}
    for name,value in [('audit.json',audit),('records.json.gz',records),('trades.json.gz',trades),('paired.json.gz',paired),('metrics.json',metrics),('paired-summary.json',summary),('strata.json',strata),('checkpoints.json.gz',checks),('diagnostic.json',diag),('predictions.json.gz',pred),('feature-separation.json.gz',effects),('first-signals.json.gz',firstsignals)]:c.write(out/name,value)
    c.write(out/'manifest.json',{str(f.relative_to(out)):c.sha(f) for f in sorted(out.rglob('*')) if f.is_file()})


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['verify','restore','daily','run']);ap.add_argument('--archives');ap.add_argument('--cache');ap.add_argument('--daily');ap.add_argument('--output');a=ap.parse_args()
    if a.command=='verify':verify()
    elif a.command=='restore':restore(a.archives,a.cache,a.output)
    elif a.command=='daily':daily(a.cache,a.output)
    else:run(a.daily,a.output)
