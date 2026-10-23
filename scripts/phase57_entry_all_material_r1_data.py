"""R1 reproducible prefit reconstruction. Existing Development only, no model fit.

A local path suffix is used solely to form strictly closed prefixes. Current
signals, original State-v3 and ONE_MINUTE intents must exactly match references.
"""
from __future__ import annotations
import argparse, collections, concurrent.futures, functools, gzip, hashlib, json, math, os
from pathlib import Path
import numpy as np
from scripts import phase57_entry_timing_signals as signals
from scripts import phase57_state_v3_9pattern_entry_v1 as state

ROOT=Path(__file__).resolve().parents[1]
SUB=ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate'
TIMING=ROOT/'docs/evidence/phase57-entry-timing-signal-census-v1/measurement'
OUT=ROOT/'artifacts/all-material-r1'
REFERENCE=ROOT/'artifacts/reference'
STATES=state.PATTERNS
WINDOWS=(3,5,10)

def read(p):
    with (gzip.open if str(p).endswith('.gz') else open)(p,'rt',encoding='utf8') as f:return json.load(f)
def write(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    b=(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
    p.write_bytes(gzip.compress(b,mtime=0) if str(p).endswith('.gz') else b)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def object_hash(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def safe_opp(o):
    return {'id':o['id'],'session':o['session'],'symbol':o['symbol'],
            'origin':{k:o['origin'][k] for k in ('decisionTimestamp','decisionPrice')}}
def overlay_names():
    names=['STATE/current/'+s for s in STATES]+['STATE/previous/'+s for s in STATES]
    names+=['STATE/valid','STATE/priorAvailable','STATE/staleness','STATE/dwell','STATE/leftCensored']
    for w in WINDOWS:names += [f'STATE/transitions{w}',f'STATE/churn{w}',f'STATE/historyCoverage{w}']
    for f in signals.FAMILIES:
        names += [f'SIX/{f}/known',f'SIX/{f}/trigger',f'SIX/{f}/sinceLastTrue']
        for w in WINDOWS:names += [f'SIX/{f}/count{w}',f'SIX/{f}/knownFraction{w}']
    names+=['CONTEXT/activeMinute','CONTEXT/pm','CONTEXT/lunchBoundary','CONTEXT/logClosedPrice']
    assert len(names)==90
    return names

def overlay(now,obs,checks,prefix):
    """All inputs end at NOW; unknown signal != false; no suffix accepted."""
    assert not len(prefix) or max(prefix[:,0])<now
    assert all(r['minute']<=now for r in obs)
    assert all(r['asOf']<=now for r in checks)
    nan=float('nan'); latest=checks[-1] if checks else None
    prev=checks[-2] if len(checks)>1 else None
    def onehot(r):return [float(r['state']==s) for s in STATES] if r and r['state'] in STATES else [nan]*len(STATES)
    vals=onehot(latest)+onehot(prev)
    age=state.active_ordinal(now)
    valid=bool(latest and latest['state'] in STATES and latest['dataQuality']!='INVALID')
    changes=[r for a,r in zip(checks,checks[1:]) if a['state']!=r['state']]
    start=(changes[-1] if changes else checks[0])['asOf'] if checks else None
    vals += [float(valid),float(prev is not None),state.active_elapsed(latest['asOf'],now) if latest else nan,
             state.active_elapsed(start,now) if start is not None else nan,float(not changes) if checks else nan]
    for w in WINDOWS:
        coverage=min(1.,state.active_elapsed(checks[0]['asOf'],now)/w) if checks else 0.
        n=sum(0<=age-state.active_ordinal(c['asOf'])<w for c in changes)
        vals += [float(n) if coverage==1 else nan,n/w if coverage==1 else nan,coverage]
    by_delay={state.active_ordinal(r['minute']):r for r in obs}
    current=by_delay.get(age)
    for f in signals.FAMILIES:
        trigger=current['signals'][f]['trigger'] if current else None
        last=next((r['minute'] for r in reversed(obs) if r['signals'][f]['trigger'] is True),None)
        vals += [float(trigger is not None),float(trigger) if trigger is not None else nan,
                 state.active_elapsed(last,now) if last is not None else nan]
        for w in WINDOWS:
            tri=[by_delay[d]['signals'][f]['trigger'] if d in by_delay else None for d in range(age-w+1,age+1)]
            known=sum(t is not None for t in tri)
            vals += [float(sum(t is True for t in tri)) if known==w else nan,known/w]
    vals += [float(age),float(now>=750),float(now in (690,750,751)),math.log(float(prefix[-1,4])) if len(prefix) else nan]
    assert len(vals)==90
    return vals

def generate_day(task):
    day,opps,raws,day_rows=task
    with gzip.open(SUB/f'{day}.npy.gz','rb') as f:base=np.load(f,allow_pickle=False)
    assert base.shape==(len(day_rows),476)
    eligible=[(i,r) for i,r in enumerate(day_rows) if r['eligible1'] and 0<=r['delay']<=30]
    by_opp=collections.defaultdict(list)
    for i,r in eligible:by_opp[r['opportunity']].append((i,r))
    current_file=TIMING/'minute-census'/f'{day}.json.gz'
    current=read(current_file) if current_file.exists() else []
    expected_sig={(r['opportunity'],r['minute']):r for r in current if r['delay']<=30}
    expected_state_file=REFERENCE/'state-checkpoints.json.gz'
    expected_states=[r for r in read(expected_state_file) if r['session']==day] if expected_sig else []
    expected_st={(r['opportunity'],r['asOf']):r for r in expected_states}
    policy=read(ROOT/'docs/evidence/phase57-state-v3-9pattern-entry-v1/POLICY_LOCK.json')
    rows_out=[]; x_out=[]; source_out={}; sig_eq=st_eq=0
    for o in sorted(opps,key=lambda x:x['id']):
        oid=o['id'];path=raws[oid]
        a=np.asarray(path['today'],float).reshape(-1,7)
        previous=np.asarray(path['previous'],float).reshape(-1,7)
        start=signals.legacy.old.minute(o['origin']['decisionTimestamp'])
        grid=set(signals.comparison_grid(day,start))
        obs=[];original=[];minute_states=[]
        ts=[t for t in signals.census_grid(day,start) if signals.legacy.elapsed(day,start,t)<=30]
        assert ts and signals.legacy.elapsed(day,start,ts[0])==0
        for t in ts:
            prefix=signals.legacy.closed(a,t)
            z=signals.detect(day,t,o['origin']['decisionPrice'],prefix,previous,path['previousSession'])
            z.update(opportunity=oid,session=day,delay=signals.legacy.elapsed(day,start,t),comparisonEligible=t in grid)
            if expected_sig:
                assert z==expected_sig[(oid,t)],('SIGNAL_PARITY',oid,t)
                sig_eq+=1
            obs.append(z)
            c=state.classify_state_v3(day,t,prefix.tolist(),path['previous'],path['previousSession'])
            c.update(opportunity=oid,session=day,delay=z['delay'],inputTodayPrefixRows=len(prefix),inputPreviousRows=len(previous))
            minute_states.append(c)
            if z['delay']%5==0:
                original.append(c)
                if expected_st:
                    assert c==expected_st[(oid,t)],('STATE_PARITY',oid,t)
                    st_eq+=1
        target=original[0]['state'] in ('DROP','PULLBACK')
        intent=state.frozen_intent(oid,obs,minute_states if target else original,policy)
        slim_obs=[{'opportunity':oid,'session':day,'minute':r['minute'],'delay':r['delay'],
                   'comparisonEligible':r['comparisonEligible'],'computedThroughBarStart':r['computedThroughBarStart'],
                   'signals':{f:{'trigger':r['signals'][f]['trigger']} for f in signals.FAMILIES}} for r in obs]
        source_out[oid]={'opportunity':o,'originalState':original,'observations':slim_obs,'oneMinuteIntent':intent}
        for i,r in by_opp.get(oid,[]):
            now=r['minute']; assert r.get('computedThroughMinute') is None or r['computedThroughMinute']<now
            prefix=signals.legacy.closed(a,now)
            ov=overlay(now,[z for z in obs if z['minute']<=now],[z for z in original if z['asOf']<=now],prefix)
            rows_out.append({k:r[k] for k in ('id','opportunity','session','minute','delay','quoteAvailable','computedThroughMinute')})
            x_out.append(np.r_[base[i],ov])
    x=np.asarray(x_out,dtype=np.float64).reshape(-1,566)
    dest=OUT/'prefit/days';dest.mkdir(parents=True,exist_ok=True)
    np.save(dest/(day+'.npy'),x,allow_pickle=False)
    write(dest/(day+'.rows.json'),rows_out)
    write(dest/(day+'.sources.json.gz'),source_out)
    return {'session':day,'rows':len(rows_out),'opportunities':len(opps),'signalParityRows':sig_eq,'stateParityRows':st_eq}

def make_splits(ops,current_days,prior_days):
    counts=collections.Counter(o['session'] for o in ops)
    chunks=[list(a) for a in np.array_split(current_days,5)];folds=[]
    for k,test in enumerate(chunks):
        seen=prior_days+[s for s in current_days if s<test[0]]
        purge='2025-05-29' if k==0 else seen[-1]
        train=seen if k==0 else seen[:-1]
        width=len(train)//5
        inn=[]
        for j in range(3):
            pos=len(train)-(3-j)*width
            itr=train[:pos-1];val=train[pos:pos+width];gap=train[pos-1]
            assert itr and val and max(itr)<gap<min(val)
            inn.append({'id':j+1,'train':itr,'purge':gap,'validation':val})
        folds.append({'id':k+1,'train':train,'purge':purge,'test':test,'inner':inn,
                      'testN':sum(counts[s] for s in test)})
    assert [f['testN'] for f in folds]==[442,446,445,412,410]
    return folds

def prepare(workers=2):
    OUT.mkdir(parents=True,exist_ok=True)
    for n,h in read(SUB/'manifest.json').items():assert digest(SUB/n)==h,n
    p=read(ROOT/'docs/evidence/phase57-entry-pattern-v2/protocol.json')
    allowed=set(p['fit']+p['selection']+p['evaluation'])
    # Future outcomes present in the source object are not copied into decision payloads.
    all_ops=read(SUB/'opportunities.json.gz')
    ops=[safe_opp(o) for o in all_ops if o['session'] in allowed];del all_ops
    assert len(ops)==5021
    raw=read(SUB/'raw-paths-evaluator-only.json.gz')
    day_op=collections.defaultdict(list);day_raw=collections.defaultdict(dict);day_rows=collections.defaultdict(list)
    for o in ops:day_op[o['session']].append(o);day_raw[o['session']][o['id']]=raw[o['id']]
    del raw
    for r in read(SUB/'rows.json.gz'):
        if r['session'] in allowed:day_rows[r['session']].append(r)
    names=read(SUB/'names.json')+overlay_names();write(OUT/'prefit/feature-names.json',names)
    tasks=[(d,day_op[d],day_raw[d],day_rows[d]) for d in sorted(day_op)]
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
        for ans in ex.map(generate_day,tasks,chunksize=1):
            results.append(ans);print(json.dumps(ans),flush=True)
    assert sum(x['rows'] for x in results)==149900
    assert sum(x['signalParityRows'] for x in results)==65910
    assert sum(x['stateParityRows'] for x in results)==14906
    current=sorted(set(p['evaluation'])&set(day_op));prior=p['fit']+p['selection']
    folds=make_splits(ops,current,prior);write(OUT/'prefit/folds.json',folds)
    sources={};rr=[];size=sum(r['rows'] for r in results)
    matrix=np.lib.format.open_memmap(OUT/'prefit/features.npy',mode='w+',dtype=np.float64,shape=(size,566))
    offset=0
    for item in results:
        d=item['session'];sub=OUT/'prefit/days'
        x=np.load(sub/(d+'.npy'));matrix[offset:offset+len(x)]=x;offset+=len(x)
        rr.extend(read(sub/(d+'.rows.json')));sources.update(read(sub/(d+'.sources.json.gz')))
    matrix.flush();del matrix
    write(OUT/'prefit/rows.json',rr);write(OUT/'prefit/sources.json.gz',sources)
    intents={o:s['oneMinuteIntent'] for o,s in sorted(sources.items()) if s['opportunity']['session'] in current}
    assert object_hash(intents)=='8e9f1bfaf10884dc140d0cf6243cab7149b64490baa9124b33a64a433e238878','INTENT_PARITY'
    have={r['opportunity'] for r in rr};curids={o['id'] for o in ops if o['session'] in current}
    assert len(curids)==2155 and curids<=have
    for f in folds:
        for days in [f['test']]+[i['validation'] for i in f['inner']]:
            assert all(o['id'] in have for o in ops if o['session'] in days)
    write(OUT/'prefit/summary.json',{'population':2155,'rows':len(rr),'columns':len(names),
        'priorRaw':2866,'priorNoRows':sum(o['id'] not in have for o in ops),
        'signalParityRows':65910,'stateParityRows':14906,'intentSHA256':object_hash(intents),
        'modelFits':0,'newTrainingLabelsBuilt':0,'protectedOpens':0,'providerRequests':0,'safety':dict.fromkeys(state.SAFETY_KEYS,False)})
    write(OUT/'prefit/manifest.json',{n:digest(OUT/'prefit'/n) for n in ('features.npy','feature-names.json','rows.json','sources.json.gz','folds.json','summary.json')})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=2)
    prepare(ap.parse_args().workers)
