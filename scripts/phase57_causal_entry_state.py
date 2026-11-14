"""Closed-prefix state only. No future path labels or execution prices accepted."""
import math
import numpy as np
from scripts import phase57_entry_timing_signals as s

STATES = ('TREND', 'PULLBACK', 'COMPRESSION', 'CHOP', 'WEAKNESS')


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def daily_context(day, dates, records):
    assert len(dates) == len(records) == 6
    assert dates == sorted(set(dates)) and all(d < day for d in dates), 'FUTURE_DAILY'
    clean, reasons, f = [], [], {}
    for d, r in zip(dates, records):
        assert r is None or r['Date'] == d, 'DAILY_DATE'
        reason = 'MISSING_DAILY' if r is None else 'CORPORATE_ACTION' if s.legacy.v.action(r) else None
        if r is not None and not reason:
            if not all(finite(r.get(k)) and r[k] > 0 for k in ('O','H','L','C')) or not (r['L'] <= min(r['O'],r['C']) <= max(r['O'],r['C']) <= r['H']):
                reason = 'INVALID_OHLC'
        clean.append(None if reason else r)
        reasons.append(reason)
    for lag in range(1,6):
        r = clean[-lag]
        for k in ('O','H','L','C','Vo','Va'):
            f[f'D{lag}/{k}'] = r.get(k) if r and finite(r.get(k)) and r[k] >= 0 else None
        for k in ('body','upper','lower','location','range'):
            f[f'D{lag}/{k}'] = None
        if r:
            o,h,l,c = (r[k] for k in ('O','H','L','C'))
            f.update({f'D{lag}/body':100*(c-o)/o,f'D{lag}/upper':100*(h-max(o,c))/o,
                      f'D{lag}/lower':100*(min(o,c)-l)/o,f'D{lag}/location':s.ratio(c-l,h-l),f'D{lag}/range':100*(h-l)/o})
    ds = clean[-5:]
    complete = all(r is not None for r in ds)
    for n in (1,2,3,5):
        f[f'returnOC{n}'] = s.pct(clean[-1]['C'],clean[-n]['O']) if all(r is not None for r in clean[-n:]) else None
        f[f'returnCC{n}'] = s.pct(clean[-1]['C'],clean[-1-n]['C']) if all(r is not None for r in clean[-1-n:]) else None
    keys = ('HH','HL','LH','LL','upStreak','downStreak','meanRange','ATRlike','rangeRatio','volumeRatio','valueRatio','volumeChange','valueChange','position5','gapPrevious','high5','low5')
    f.update({k:None for k in keys})
    if complete:
        ref = ds[-1]['C']
        for i,r in enumerate(ds):
            for k in ('O','H','L','C'):
                f[f'trajectory{i+1}/{k}'] = s.pct(r[k],ref)
        for name,k,sign in [('HH','H',1),('HL','L',1),('LH','H',-1),('LL','L',-1)]:
            f[name] = sum(sign*(b[k]-a[k])>0 for a,b in zip(ds,ds[1:]))/4
        dif = np.diff([r['C'] for r in ds])
        for name,sign in [('upStreak',1),('downStreak',-1)]:
            count=0
            for x in dif[::-1]:
                if sign*x<=0: break
                count+=1
            f[name]=count
        rr=[100*(r['H']-r['L'])/r['O'] for r in ds]
        f['meanRange']=float(np.mean(rr)); f['rangeRatio']=s.ratio(float(np.mean(rr[-2:])),float(np.mean(rr[:3])))
        f['ATRlike']=100*float(np.mean([max(b['H']-b['L'],abs(b['H']-a['C']),abs(b['L']-a['C'])) for a,b in zip(ds,ds[1:])]))/ref
        for name,k in [('volume','Vo'),('value','Va')]:
            values=[r.get(k) for r in ds]
            if all(finite(v) and v>=0 for v in values):
                f[name+'Ratio']=s.ratio(float(np.mean(values[-2:])),float(np.mean(values[:3])))
                f[name+'Change']=s.ratio(values[-1],values[0])
        f['high5']=max(r['H'] for r in ds);f['low5']=min(r['L'] for r in ds)
        f['position5']=s.ratio(ref-f['low5'],f['high5']-f['low5'])
        f['gapPrevious']=s.pct(ds[-1]['O'],ds[-2]['C'])
    return {'complete5':complete,'status':'AVAILABLE' if complete else 'DAILY_UNAVAILABLE',
            'dates':dates,'reasons':reasons,'computedThrough':dates[-1], 'features':f}


def efficiency(w):
    den=abs(w[0,4]-w[0,1])+sum(abs(np.diff(w[:,4])))
    return float(abs(w[-1,4]-w[0,1])/den) if den else 0.


def dominant(scores):
    valid={k:v for k,v in scores.items() if v is not None}
    if not valid:return 'UNKNOWN'
    top=max(valid.values())
    if top<.5:return 'UNRESOLVED'
    names=[k for k,v in valid.items() if abs(v-top)<1e-10]
    return names[0] if len(names)==1 else 'MIXED'


def state(day,t,prefix,previous,previous_day,daily,activity):
    assert not len(prefix) or np.max(prefix[:,0]) < t, 'FUTURE_BAR'
    assert daily['computedThrough'] < day, 'FUTURE_DAILY'
    if len(previous):assert previous_day == s.legacy.f.s.calendar()[s.legacy.f.s.calendar().index(day)-1], 'PREVIOUS_DATE'
    a=s.regular(day,prefix)
    f={k:None for k in ('ret5','ret10','efficiency','HH','HL','LH','LL','reversals','RV','rangeUtilization','drawdown','peakAge','recovery','range10','rangeRatio','bodyRatio','RVratio','VWAPdistance','VWAPslope','timeAboveVWAP','volumeRatio','valueRatio','previousReturn','previousRange','previousEfficiency','dailyHighDistance','dailyLowDistance','dailyCloseDistance','fiveHighDistance','fiveLowDistance','todayGap')}
    f['previousCoverage']=len(previous)/max(1,len(s.legacy.minutes(previous_day))) if previous_day else 0.
    if len(previous):
        f['previousReturn']=s.pct(previous[-1,4],previous[0,1]);f['previousRange']=100*(max(previous[:,2])-min(previous[:,3]))/previous[0,1];f['previousEfficiency']=efficiency(previous)
    w5,w10=s.window(a,t,5),s.window(a,t,10)
    close=float(a[-1,4]) if len(a) and a[-1,0]==t-1 else None
    vw,_=s.observed_vwap(day,a,t);pv,_=s.observed_vwap(day,a,t-3)
    f['VWAPdistance']=s.pct(close,vw);f['VWAPslope']=s.pct(vw,pv)
    if w5 is not None:f['ret5']=s.pct(w5[-1,4],w5[0,1])
    if w10 is not None:
        h,l=max(w10[:,2]),min(w10[:,3]);diff=np.diff(w10[:,4]);sign=np.sign(diff);sign=sign[sign!=0]
        f.update(ret10=s.pct(close,w10[0,1]),efficiency=efficiency(w10),reversals=int(np.sum(sign[1:]!=sign[:-1])),RV=float(np.std(np.diff(np.log(w10[:,4])))*100),rangeUtilization=s.ratio(float(sum(abs(diff))),float(h-l)),drawdown=100*(h-close)/h,peakAge=int(t-1-w10[np.argmax(w10[:,2]),0]),recovery=s.ratio(close-l,h-l),range10=100*(h-l)/w10[0,1])
        for name,col,signum in [('HH',2,1),('HL',3,1),('LH',2,-1),('LL',3,-1)]:f[name]=float(np.mean(signum*np.diff(w10[:,col])>0))
        first,last=w10[:5],w10[-5:]
        f['rangeRatio']=s.ratio(float(max(last[:,2])-min(last[:,3])),float(max(first[:,2])-min(first[:,3])))
        f['bodyRatio']=s.ratio(float(np.mean(abs(last[:,4]-last[:,1]))),float(np.mean(abs(first[:,4]-first[:,1]))))
        f['RVratio']=s.ratio(float(np.std(np.diff(np.log(last[:,4])))),float(np.std(np.diff(np.log(first[:,4])))))
        for name,col in [('volume',5),('value',6)]:f[name+'Ratio']=s.ratio(float(sum(last[:,col])),float(sum(first[:,col])))
        vws=[s.observed_vwap(day,a,int(row[0])+1)[0] for row in w10]
        if all(v is not None for v in vws):f['timeAboveVWAP']=sum(row[4]>v for row,v in zip(w10,vws))/10
    df=daily['features']
    for key,ref in [('dailyHighDistance','D1/H'),('dailyLowDistance','D1/L'),('dailyCloseDistance','D1/C'),('fiveHighDistance','high5'),('fiveLowDistance','low5')]:f[key]=s.pct(close,df.get(ref))
    opening=a[a[:,0]==540]
    f['todayGap']=s.pct(opening[0,1],df.get('D1/C')) if len(opening) else None
    f.update({'ACTIVITY/'+k:v for k,v in activity.items()})
    def check(key,fn):return fn(f[key]) if f[key] is not None else None
    def both(a,b):return None if a is None or b is None else bool(a and b)
    tests={
        'TREND':[check('ret5',lambda x:x>=.1),check('efficiency',lambda x:x>=.5),check('VWAPdistance',lambda x:x>0),both(check('HH',lambda x:x>=.5),check('HL',lambda x:x>=.5))],
        'PULLBACK':[check('drawdown',lambda x:x>=.3),check('ret5',lambda x:x<0),check('peakAge',lambda x:x>=3),bool(close>previous[0,1]) if close is not None and len(previous) else None],
        'COMPRESSION':[check('rangeRatio',lambda x:x<=.65),check('bodyRatio',lambda x:x<=.8),check('volumeRatio',lambda x:x<=.8),check('valueRatio',lambda x:x<=.8)],
        'CHOP':[check('efficiency',lambda x:x<=.25),check('reversals',lambda x:x>=4),check('range10',lambda x:x>=.5),check('recovery',lambda x:.2<=x<=.8)],
        'WEAKNESS':[check('ret5',lambda x:x<=-.1),check('VWAPdistance',lambda x:x<0),check('VWAPslope',lambda x:x<0),both(check('LH',lambda x:x>=.5),check('LL',lambda x:x>=.5))]}
    scores={k:sum(v)/4 if all(x is not None for x in v) else None for k,v in tests.items()}
    integrated=dict(scores)
    if daily['complete5']:
        adds={'TREND':df['returnOC5']>0 and df['HH']>=.5 and df['HL']>=.5,
              'WEAKNESS':df['returnOC5']<0 and df['LH']>=.5 and df['LL']>=.5,
              'PULLBACK':df['returnOC5']>0 and f['ret5'] is not None and f['ret5']<0,
              'COMPRESSION':df['rangeRatio'] is not None and df['rangeRatio']<=.8,'CHOP':abs(df['returnOC5'])<1}
        for k in STATES:
            if integrated[k] is not None:integrated[k]=min(1.,integrated[k]+.1*adds[k])
    return {'minute':t,'closedThrough':t-1,'features':f,'scores':scores,'integratedScores':integrated,
            'state':dominant(integrated),'intradayState':dominant(scores),'dailyStatus':daily['status'],
            'recoveryContext':all(f[k] is not None for k in ('drawdown','ret5','recovery')) and f['drawdown']>=.3 and f['ret5']>0 and f['recovery']>=.5,
            'newClosedBarObserved':close is not None,'activity':activity}


def timing(z,signals):
    fires=lambda names:any(signals[n]['trigger'] is True for n in names)
    v=z['integratedScores']['TREND']
    early=(v is not None and v>=.75) or fires(['CONTINUATION'])
    mappings={'TREND':['CONTINUATION','BREAKOUT'],'PULLBACK':['HIGHER_LOW','LOWER_WICK','RECLAIM'],
              'COMPRESSION':['COMPRESSION_EXPANSION','BREAKOUT'],'CHOP':['HIGHER_LOW','RECLAIM']}
    label=z['state'];matched=fires(mappings.get(label,[]))
    if label=='CHOP':matched=matched and z['features']['recovery'] is not None and z['features']['recovery']<=.5
    if label=='WEAKNESS':matched=signals['HIGHER_LOW']['trigger'] is True and signals['RECLAIM']['trigger'] is True
    return {'EARLY':{'trigger':bool(early)},'APPROPRIATE':{'trigger':bool(matched)}}
