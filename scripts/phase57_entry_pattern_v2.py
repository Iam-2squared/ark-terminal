"""Versioned full-chart Entry Pattern Development; no order routing."""
import argparse,collections,datetime as dt,gzip,hashlib,json,math,functools
from pathlib import Path
import numpy as np
from scripts import phase57_chart_entry as old
from scripts import phase57_entry_extended as ext
f=old.f;v=f.v;read=f.read;write=f.write;sha=f.sha;ROOT=f.ROOT;BASE=ROOT/'docs/evidence/phase57-entry-pattern-v2'

def verify():
 p=read(BASE/'protocol.json');assert sha(BASE/'protocol.json')==read(BASE/'protocol-lock.json')['sha256']
 for name,h in p['pins'].items():assert sha(ROOT/name)==h,name
 old.verify();assert p['sessions']==f.s.admission.plan()['intradayDevelopment'] and len(p['sessions'])==144
 assert all(x is False for x in p['safety'].values());return p

@functools.lru_cache(maxsize=150)
def minutes(day):return list(range(540,690))+list(range(750,900 if day<'2024-11-05' else 925))
def elapsed(day,start,t):return sum(max(0,min(t,b)-max(start,a)) for a,b in [(540,690),(750,900 if day<'2024-11-05' else 925)])
def clock(day,start,step=1):
 # Observation at t uses closed bars strictly before t; no first minute after reopen order.
 return [t for t in minutes(day) if t>=start and t not in [540,750] and elapsed(day,start,t)<=30 and elapsed(day,start,t)%step==0]
def compact(raw,day):
 assert all(x['Date']==day for x in raw)
 ts=[v.minute_time(x) for x in raw];assert len(ts)==len(set(ts)),'DUPLICATE_MINUTE'
 return np.array([[v.minute_time(x)]+[x[k] for k in ['O','H','L','C','Vo','Va']] for x in sorted(raw,key=v.minute_time) if v.valid(x)],float).reshape(-1,7)
def closed(a,t):return a[a[:,0]<t]
def pct(a,b):return 100*(a/b-1) if b and b>0 else None

def describe(a,ref,expected):
 keys=['count','coverage','return','high','low','range','volatility','body','upper','lower','volume','value','vwapDistance','closeLocation','timeHigh','timeLow','trendEfficiency']
 z={k:None for k in keys};z.update(count=len(a),coverage=min(1.,len(a)/max(expected,1)))
 if not len(a) or not ref or ref<=0:return z
 o,h,l,c=a[0,1],max(a[:,2]),min(a[:,3]),a[-1,4];vo=sum(a[:,5]);va=sum(a[:,6]);vw=va/vo if vo>0 else None
 z.update(return_=pct(c,o));z['return']=z.pop('return_')
 z.update(high=pct(h,ref),low=pct(l,ref),range=100*(h-l)/ref,body=100*(c-o)/ref,upper=100*(h-max(o,c))/ref,lower=100*(min(o,c)-l)/ref,volume=math.log1p(vo),value=math.log1p(va),vwapDistance=pct(c,vw),closeLocation=(c-l)/(h-l) if h>l else .5,timeHigh=float(a[np.argmax(a[:,2]),0]),timeLow=float(a[np.argmin(a[:,3]),0]),volatility=float(np.std(np.diff(np.log(a[:,4])))*100) if len(a)>1 else None,trendEfficiency=abs(c-o)/max(abs(a[0,4]-o)+sum(abs(np.diff(a[:,4]))),1e-9))
 return z

PROJECTION=np.random.default_rng(5709202).choice([-1.,1.],size=(391,6,24))/math.sqrt(391*6)
def projection(a,ref):
 if not len(a) or not ref:return [None]*24
 ix=(a[:,0]-540).astype(int);assert min(ix)>=0 and max(ix)<=390
 z=a[:,1:].copy();z[:,:4]=100*(z[:,:4]/ref-1);z[:,4:]=np.log1p(z[:,4:])
 return np.einsum('ij,ijk->k',z,PROJECTION[ix]).tolist()

def five_observed(a,t):
 # Actual OHLCV aggregation of available records, never an empty/artificial bar.
 bars=[]
 for lo in list(range(540,690,5))+list(range(750,925,5)):
  if lo+5>t:continue
  x=a[(a[:,0]>=lo)&(a[:,0]<lo+5)]
  if len(x):bars.append([lo+5,x[0,1],max(x[:,2]),min(x[:,3]),x[-1,4],sum(x[:,5]),sum(x[:,6]),len(x)])
 return np.array(bars,float).reshape(-1,8)

def features(day,t,start,origin,a,prev,previousDaily,recent):
 assert not len(a) or max(a[:,0])<t,'FUTURE_BAR'
 ref=a[-1,4] if len(a) else None;age=t-(a[-1,0]+(0 if a[-1,0] in [690,900,930] else 1)) if len(a) else None
 # Lunch excludes obsolete morning quotes at reopen; exact closed1m or <=5m stale contract.
 phase=540 if t<690 else 750;latestPhase=bool(len(a) and a[-1,0]>=phase)
 quote=bool(ref and latestPhase and age is not None and 0<=age<=5)
 z={'SEL/score':origin['savedV1Score'],'SEL/rank':origin['newEligibleRank'],'SEL/move':pct(ref,origin['decisionPrice']) if ref else None,'CLOCK/time':t/1440,'CLOCK/activeDelay':elapsed(day,start,t),'CLOCK/remaining':sum(m>=t for m in minutes(day)),'AVAIL/quote':int(quote),'AVAIL/age':age,'AVAIL/prevRows':len(prev),'AVAIL/todayRows':len(a)}
 for name,part,expected in [('TODAY',a,elapsed(day,540,t)),('PREV',prev,325),('PREV_AM',prev[prev[:,0]<=690],150),('PREV_PM',prev[prev[:,0]>=750],175),('PREV_LATE',prev[prev[:,0]>=870],60)]:
  rr=prev[0,1] if name.startswith('PREV') and len(prev) else ref
  z.update({name+'/'+k:val for k,val in describe(part,rr,expected).items()})
 for name,part,rr in [('SEQ_PREV',prev,prev[0,1] if len(prev) else None),('SEQ_TODAY',a,a[0,1] if len(a) else None)]:
  z.update({name+'/'+str(i):val for i,val in enumerate(projection(part,rr))})
 for w in [1,2,3,5,10,15,30,60]:
  part=a[(a[:,0]>=max(phase,t-w))&(a[:,0]<t)];z.update({f'LOCAL{w}/'+k:val for k,val in describe(part,ref,min(w,t-phase)).items()});z[f'AVAIL/fullWindow{w}']=int(t-phase>=w)
 for lag in range(15):
  r=a[a[:,0]==t-1-lag] if t-1-lag>=phase else []
  for j,k in enumerate(['O','H','L','C','Vo','Va']):z[f'SEQ_MICRO/{lag}/{k}']=(pct(r[0,j+1],ref) if j<4 else math.log1p(r[0,j+1])) if len(r) and ref else None
 z.update({'RECENT/'+k:val for k,val in recent.items()})
 if previousDaily and v.valid(previousDaily) and ref:
  for k,key in [('H','position_high'),('L','position_low'),('C','position_close')]:z['RECENT/'+key]=pct(ref,previousDaily[k])
  z['RECENT/gap']=pct(a[0,1],previousDaily['C']) if len(a) and a[0,0]==540 else None
 bars=five_observed(a,t);z['STRUCT/barCount']=len(bars);z['STRUCT/complete5Count']=sum(bars[:,7]==5)
 z['STRUCT/partial5Count']=sum(bars[:,7]<5)
 piv=[]
 for i in range(1,len(bars)-1):
  if bars[i+1,0]-bars[i-1,0]!=10:continue
  if bars[i,2]>bars[i-1,2] and bars[i,2]>bars[i+1,2]:piv.append(('H',bars[i,2],bars[i+1,0]))
  if bars[i,3]<bars[i-1,3] and bars[i,3]<bars[i+1,3]:piv.append(('L',bars[i,3],bars[i+1,0]))
 for kind in ['H','L']:
  pp=[x for x in piv if x[0]==kind];z['STRUCT/'+kind+'rising']=float(pp[-1][1]>pp[-2][1]) if len(pp)>=2 else None
 z['STRUCT/turningUp']=float(piv[-1][0]=='L') if piv else None;z['STRUCT/swingAge']=t-piv[-1][2] if piv else None
 levels={'PDH':previousDaily['H'] if v.valid(previousDaily) else None,'PDL':previousDaily['L'] if v.valid(previousDaily) else None}
 opening=a[(a[:,0]>=540)&(a[:,0]<555)];levels['ORH']=max(opening[:,2]) if t>=555 and len(opening) else None;levels['ORL']=min(opening[:,3]) if t>=555 and len(opening) else None
 for key,level in levels.items():
  z['SIGNAL/'+key+'distance']=pct(ref,level) if ref else None
  z['SIGNAL/'+key+'reclaim']=float(a[-2,4]<=level<ref) if level and len(a)>=2 else None
  z['SIGNAL/'+key+'failure']=float(a[-2,4]>=level>ref) if level and len(a)>=2 else None
 z['SIGNAL/vwapCrossUp']=None
 if len(a)>1 and sum(a[:,5])>0 and sum(a[:-1,5])>0:z['SIGNAL/vwapCrossUp']=float(a[-2,4]<=sum(a[:-1,6])/sum(a[:-1,5]) and a[-1,4]>sum(a[:,6])/sum(a[:,5]))
 for w in [1,3,5,10,15,30]:
  before=a[(a[:,0]>=max(phase,t-w))&(a[:,0]<t)];z.update({f'SIGNAL_PATH{w}/'+k:val for k,val in describe(before,ref,min(w,t-phase)).items() if k in ['return','volume','value','range','body','vwapDistance']})
 for w in [1,3,5,10]:
  cur=a[(a[:,0]>=max(phase,t-w))&(a[:,0]<t)];prior=a[(a[:,0]>=max(phase,t-2*w))&(a[:,0]<t-w)]
  for idx,name in [(5,'volume'),(6,'value')]:z[f'ACCEL{w}/'+name]=sum(cur[:,idx])/sum(prior[:,idx]) if len(cur) and len(prior) and sum(prior[:,idx])>0 else None
  hist=prev[(prev[:,0]>=max(phase,t-w))&(prev[:,0]<t)]
  for idx,name in [(5,'volume'),(6,'value')]:z[f'RVOL{w}/'+name]=sum(cur[:,idx])/sum(hist[:,idx]) if len(cur) and len(hist) and sum(hist[:,idx])>0 else None
 if len(bars)>=4:
  ranges=bars[-4:,2]-bars[-4:,3];z['STRUCT/compressionExpansion']=float(ranges[-1]/np.mean(ranges[:-1])) if np.mean(ranges[:-1])>0 else None
 else:z['STRUCT/compressionExpansion']=None
 z['STRUCT/pullbackFromHOD']=pct(ref,max(a[:,2])) if len(a) else None
 z['STRUCT/recoveryFromLOD']=pct(ref,min(a[:,3])) if len(a) else None
 return z,quote

def label(day,t,a,daily,origin):
 hit=a[a[:,0]==t];fill=hit[0,1]*1.0005 if len(hit) else None
 out={'price':fill,'fillFeasible':fill is not None,'labels':None,'improvementPct':100*(1-fill/origin) if fill else None}
 if fill is None:return out
 raw=[dict(Date=day,Time='%02d:%02d'%divmod(int(x[0]),60),**dict(zip(['O','H','L','C','Vo','Va'],x[1:]))) for x in a]
 m={'sessionDate':day,'decisionTimeJst':'%02d:%02d'%divmod(t,60),'decisionPrice':fill};legacy=f.labels_for_raw(m,raw,daily);lab={k:legacy[k] for k in ['mfeEnd','maeEnd','returnEnd','order','fullStatus','fullReason']}
 if lab['returnEnd'] is not None:lab['returnEnd']=(1+lab['returnEnd']/100)*.9995*100-100
 active=[x for x in minutes(day) if x>=t]
 for h in [30,60]:
  ms=active[:h];end=ms[-1]+1 if len(ms)==h else None
  xs=a[(a[:,0]>=t)&(a[:,0]<(end if end is not None else 1000))];reason='SESSION_BOUNDARY' if end is None else None
  if end is not None:
   chunks=[]
   for m0 in ms:
    if not chunks or len(chunks[-1])==5 or m0!=chunks[-1][-1]+1:chunks.append([])
    chunks[-1].append(m0)
   if any(not any(x in chunk for x in a[:,0]) for chunk in chunks):reason='MISSING_REQUIRED_ACTIVE_SLOT'
  obsmfe=max(0,100*(max(xs[:,2])/fill-1)) if len(xs) else None
  z={'status':'COMPLETE' if reason is None else 'CENSORED' if end is None else 'UNAVAILABLE','reason':reason,'observedMFE':obsmfe,'pathAvailable':bool(len(xs)),'MFE':None,'MAE':None,'MaxDD':None,'returnNet':None}
  if reason is None and len(xs):
   rr=[dict(zip(['O','H','L','C','Vo','Va'],x[1:])) for x in xs];dd,upper=ext.drawdown_bounds(fill,rr)
   z.update(MFE=obsmfe,MAE=min(0,100*(min(xs[:,3])/fill-1)),MaxDD=dd,MaxDDAdverseBound=upper,returnNet=100*(xs[-1,4]/fill*.9995-1))
  lab[str(h)]=z
  for name,key in [('mfe','MFE'),('mae','MAE'),('return','returnNet')]:lab[name+str(h)]=z[key]
 fut=a[a[:,0]>=t]
 for name,mask in [('timeToUpside',fut[:,2]>=fill*1.03),('timeToRecovery',fut[:,2]>=fill)]:lab[name]=elapsed(day,t,int(fut[mask][0,0])) if any(mask) else None
 if len(fut):lab['timeToHigh']=elapsed(day,t,int(fut[np.argmax(fut[:,2]),0]));lab['timeToLow']=elapsed(day,t,int(fut[np.argmin(fut[:,3]),0]))
 out['labels']=lab;return out

def substrate(cache,prior,output):
 p=verify();src=Path(prior);out=Path(output);out.mkdir(parents=True,exist_ok=False)
 for folder,man in p['priorManifests'].items():
  assert read(src/folder/'manifest.json')==man
  for name,h in man.items():assert sha(src/folder/name)==h,(folder,name)
 opps=read(src/'substrate/opportunities.json.gz');v1trades=read(src/'measurement/trades.json.gz')['E5'];v1minute={z['opportunity']:int(z['entryId'].split('|')[-1]) for z in v1trades if z['entryId']};saved=read(src/'substrate/features.json.gz');origrows={x['id']:x for x in saved};del saved
 byday=collections.defaultdict(list)
 for o in opps:byday[o['session']].append(o)
 pins={(x['session'],x['kind']):x['sha256'] for x in read(src/'substrate/input-ledger.json')};cal=f.s.calendar();prevby={};prevdaily={};history={};last=None;names=None;inventory=[];allrows=[];labels={};source=[];rootcause=collections.Counter();paths={}
 for di,day in enumerate(p['sessions']):
  previous=cal[cal.index(day)-1]
  if last!=previous:prevby={};prevdaily={};history={}
  ms=byday[day];nextcodes={o['symbol'] for o in byday[p['sessions'][di+1]]} if di+1<len(p['sessions']) else set();codes={o['symbol'] for o in ms}|nextcodes
  for kind in ['minute','daily','master']:
   f.s.admission.authorize(day,kind);path=Path(cache)/day/(kind+'-pages.json');assert sha(path)==pins[day,kind];source.append({'session':day,'kind':kind,'sha256':sha(path)})
  values,_=v.saved.pages(Path(cache)/day/'minute-pages.json');by=collections.defaultdict(list)
  for x in values:
   assert x['Date']==day
   if x['Code'] in codes:by[x['Code']].append(x)
  by={c:compact(xs,day) for c,xs in by.items()};del values
  # Today's daily used ONLY by outcome evaluator below. Features see prior session dictionary.
  daily,_=v.saved.pages(Path(cache)/day/'daily-pages.json');dc={x['Code']:x for x in daily};del daily
  xs=[];rows=[];nprev=0
  for o in ms:
   code=o['symbol'];a=by.get(code,np.empty((0,7)));pv=prevby.get(code,np.empty((0,7)));start=old.minute(o['origin']['decisionTimestamp']);grid=clock(day,start);o['v2grid']=grid;o['v2grid5']=clock(day,start,5)
   rootcause['FROZEN_ADAPTER/'+('UNAVAILABLE' if o.get('selectorFeatureReason') else 'AVAILABLE')]+=1
   nprev+=bool(len(pv));key0=o['id']+'|'+str(start);recent=f.b.recent_context(day,o['origin']['decisionPrice'],[],history.get(code,[]),cal)['features']
   paths[o['id']]={'previousSession':previous if len(pv) else None,'previous':pv.tolist(),'today':a.tolist(),'sourceHash':pins[day,'minute'],'contract':'EVALUATOR_FULL_PATH_NOT_DECISION_PAYLOAD_PREFIX_BY_INDEX_ONLY'}
   # E5 v1 rows retained only to evaluate immutable baseline under same active horizons.
   times=sorted(set(grid+([v1minute[o['id']]] if o['id'] in v1minute else [])))
   for t in times:
    prefix=closed(a,t);z,quote=features(day,t,start,o['origin'],prefix,pv,prevdaily.get(code),recent)
    if names is None:names=sorted(z)
    assert names==sorted(z);rid=o['id']+'|'+str(t)
    row={'id':rid,'opportunity':o['id'],'session':day,'symbol':code,'minute':t,'delay':elapsed(day,start,t),'eligible1':t in grid,'eligible5':t in o['v2grid5'],'quoteAvailable':quote,'previousAvailable':bool(len(pv)),'previousCoverage':'MISSING' if not len(pv) else 'FULL_SLOTS' if set(minutes(previous))<=set(pv[:,0]) else 'PARTIAL_OBSERVED','todayCoverage':'MISSING' if not len(prefix) else 'FULL_SLOTS' if {m for m in minutes(day) if m<t}<=set(prefix[:,0]) else 'PARTIAL_OBSERVED','previousThrough':previous if len(pv) else None,'todayPrefixRows':len(prefix),'computedThroughMinute':int(prefix[-1,0]) if len(prefix) else None,'featureRow':len(allrows)+len(rows)}
    assert not len(prefix) or prefix[-1,0]<t
    rows.append(row);xs.append([np.nan if z[n] is None else z[n] for n in names]);labels[rid]=label(day,t,a,dc.get(code),o['origin']['decisionPrice'])
    oldrow=origrows.get(rid)
    if oldrow:
     rootcause['NOW/'+str(oldrow['NOW'].get('reason') or oldrow['NOW']['status'])]+=1
     rootcause['RECENT/'+str(oldrow['RECENT'].get('reason') or oldrow['RECENT']['status'])]+=1
     for w in [15,30,60]:
      if oldrow['SEQ']['features'][f'w{w}_return'] is None:
       phase=540 if t<690 else 750;part=prefix[(prefix[:,0]>=max(phase,t-w))]
       reason='WARMUP_OR_LUNCH_FIXED_LAG' if t-phase<w else 'RAW_PREFIX_ABSENT' if not len(part) else 'STRICT_AGGREGATION_REJECTED_OBSERVED_PARTIAL' if len(part)<w else 'OTHER_ADAPTER_OR_CONTRACT'
       rootcause[f'w{w}/'+reason]+=1
  array=np.asarray(xs,dtype=np.float32).reshape(len(xs),len(names) if names else 0)
  # Per-day matrix avoids a giant in-memory object and Git blob limits.
  with (out/(day+'.npy.gz')).open('wb') as fh:
   with gzip.GzipFile(fileobj=fh,mode='wb',mtime=0,filename='') as gz:np.save(gz,array,allow_pickle=False)
  allrows.extend(rows);inventory.append({'session':day,'opportunities':len(ms),'patternRows':len(rows),'previousFullPathAvailable':nprev,'previousUnavailable':len(ms)-nprev,'emptyV1':sum(not o['grid'] for o in ms),'emptyV2':sum(not o['v2grid'] for o in ms),'causal':True});print(json.dumps(inventory[-1]),flush=True)
  for code,d in dc.items():history[code]=(history.get(code,[])+[{'session':day,'daily':d}])[-10:]
  prevby={c:a for c,a in by.items() if c in nextcodes};prevdaily=dc;last=day
 # No source suffix is passed to feature/model code: paths are evaluator-only reconstruction archive.
 write(out/'rows.json.gz',allrows);write(out/'outcomes.json.gz',labels);write(out/'opportunities.json.gz',opps);write(out/'names.json',names);write(out/'inventory.json',inventory);write(out/'source-ledger.json',source);write(out/'raw-paths-evaluator-only.json.gz',paths)
 write(out/'p0-audit.json',{'status':'PASS','all144':len(inventory)==144,'previousCausal':True,'todayPrefixCausal':True,'rootCauses':dict(rootcause),'clockFixed':True,'sameRetryBaseline':True,'featureNoWHO':not any('WHO' in n for n in names),'holdoutOpened':0,'safety':p['safety'],'sourceCaveat':'Observed records only; missing minute is not certified zero-trade without provider completeness metadata. Full path coverage masks remain explicit. Frozen upstream same-day metadata limitation inherited.'})
 write(out/'manifest.json',{x.name:sha(x) for x in sorted(out.iterdir())})

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('command',choices=['verify','substrate']);a.add_argument('--cache');a.add_argument('--prior');a.add_argument('--output');x=a.parse_args()
 if x.command=='verify':verify()
 else:substrate(x.cache,x.prior,x.output)
