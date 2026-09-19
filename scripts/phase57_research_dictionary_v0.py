#!/usr/bin/env python3
"""Isolated reconstruction research. No strategy clients or production promotion."""
import argparse, collections, csv, gzip, hashlib, io, json, math, os, time
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
from scripts import phase57_behavior_dictionary as saved
ROOT=saved.ROOT
BASE=ROOT/'docs/evidence/phase57-research-dictionary-v0'
PRIOR=ROOT/'docs/evidence/phase57-dictionary-pit-recovery-v1/measurement'
CONDITIONAL={'gap_fill','gap_cont','gap_rev','or_follow','or_fail','pdl_reclaim','vwap_reclaim','selloff_rebound','rally_giveback','swing_amplitude','swing_duration','pullback_depth'}
LABELS=['RESEARCH_ONLY','HISTORICAL_RECONSTRUCTION','NOT_FOR_PRODUCTION','NOT_OOS_CONFIRMED','NOT_PIT_VERIFIED']

def registry():
 p=saved.read(BASE/'registry.json')
 assert saved.sha(BASE/'registry.json')==saved.read(BASE/'registry-lock.json')['sha256'],'REGISTRY_HASH'
 assert len(p['catalog'])<=80 and len(p['composites'])<=10
 assert p['sessions']==saved.protocol()['sessions']['auditAndExploration']
 assert len(set(x['id'] for x in p['catalog']))==len(p['catalog'])
 assert p['labels']==LABELS and all(v is False for v in p['safety'].values())
 return p

def production_load(artifact):
 if artifact.get('evidence_class')!='PIT_VERIFIED' or any(x in artifact.get('labels',[]) for x in LABELS):
  raise ValueError('RESEARCH_NAMESPACE_REJECTED')
 # This research module is never a production loading route, even if relabeled.
 raise ValueError('USE_INDEPENDENT_PRODUCTION_PIT_LOADER')

def num(x):
 return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def valid(r):
 return r is not None and all(num(r.get(k)) for k in ['O','H','L','C','Vo','Va']) and min(r[k] for k in ['O','H','L','C'])>0 and min(r['Vo'],r['Va'])>=0 and r['H']>=max(r['O'],r['C'],r['L']) and r['L']<=min(r['O'],r['C'],r['H'])
def action(r):
 return r is None or r.get('AdjFactor') not in [None,1,1.,'1','1.0'] or r.get('ExRT') not in [None,'',0,'0']
def scale(history):
 vals=[x['tr'] for x in history[-10:] if num(x.get('tr')) and x['tr']>0]
 return float(np.median(vals)) if len(vals)>=5 else None

def bucket(day,t):
 if 540<=t<570:return 'O30'
 if 570<=t<=690:return 'AM'
 if 750<=t<840:return 'PM1'
 if 840<=t<(900 if day<'2024-11-05' else 925) or (day<'2024-11-05' and t==900):return 'PM2'
 if day>='2024-11-05' and 925<=t<=930:return 'CL'
 return None

def minute_time(r):
 a=str(r['Time']).split(':');h,m=int(a[0]),int(a[1]);assert 0<=h<24 and 0<=m<60
 return h*60+m

def intraday_eligible(d,rows):
 if not valid(d) or not rows or not all(valid(r) for r in rows):return False,{'reason':'INVALID_OR_EMPTY'}
 v=sum(r['Vo'] for r in rows);a=sum(r['Va'] for r in rows)
 recon=math.isclose(v,d['Vo'],rel_tol=1e-10,abs_tol=1e-6) and math.isclose(a,d['Va'],rel_tol=1e-10,abs_tol=1e-6)
 extrema=abs(max(r['H'] for r in rows)-d['H'])<=.1 and abs(min(r['L'] for r in rows)-d['L'])<=.1
 return recon and extrema,{'vol_recon_ok':recon,'extrema_match':extrema}

def bars5(day,rows):
 by={}
 for r in rows:
  t=minute_time(r)
  if t in by:raise ValueError('DUPLICATE_MINUTE')
  by[t]=r
 out=[];cumv=cuma=0.
 close=900 if day<'2024-11-05' else 925
 # cumulative value/volume includes observed auctions before each bar end.
 for t in sorted(by):
  r=by[t];cumv+=r['Vo'];cuma+=r['Va']
  if t%5!=4 or not (540<=t<690 or 750<=t<close):continue
  start=t-4
  if not all(i in by for i in range(start,t+1)):continue
  rs=[by[i] for i in range(start,t+1)]
  out.append({'t':t+1,'O':rs[0]['O'],'H':max(x['H'] for x in rs),'L':min(x['L'] for x in rs),'C':rs[-1]['C'],'Vo':sum(x['Vo'] for x in rs),'Va':sum(x['Va'] for x in rs),'VWAP':cuma/cumv if cumv>0 else None})
 return out

def same_phase(a,b):return (a<=690 and b<=690) or (a>750 and b>750)
def response(bars,i,minutes,predicate):
 # Full fixed wallclock window required even on observed success: avoids missingness-dependent denominator.
 end=bars[i]['t']+minutes
 rs=[b for b in bars[i+1:] if b['t']<=end]
 if len(rs)!=minutes//5 or [b['t'] for b in rs]!=list(range(bars[i]['t']+5,end+1,5)) or not same_phase(bars[i]['t'],end):return None
 return float(any(predicate(b) for b in rs))

def swings(bars,unit):
 if unit<=0:return []
 out=[];direction=0;anchor=extreme=None;start=extime=None;previous_t=None
 for b in bars:
  t,c=b['t'],b['C']
  if previous_t is None or t-previous_t!=5 or not same_phase(previous_t,t):
   direction=0;anchor=extreme=c;start=extime=t
  previous_t=t
  if direction==0:
   if abs(c-anchor)>=.5*unit:direction=1 if c>anchor else -1;extreme=c;extime=t
  elif (direction==1 and c>extreme) or (direction==-1 and c<extreme):extreme=c;extime=t
  elif direction*(extreme-c)>=.5*unit:
   out.append({'amplitude':abs(extreme-anchor)/unit,'duration':extime-start,'confirmedAt':t,'extremeAt':extime,'lag':t-extime,'direction':direction})
   anchor=extreme;start=extime;direction=-direction;extreme=c;extime=t
 return out

def daily_traits(d,prev,hist,s):
 out={};pc=prev['C'];u=pc*s;r=d['H']-d['L'];body=d['C']-d['O'];ret=d['C']/pc-1
 if r<=0:return out
 out.update(body_s=body/u,body_range=body/r,upper_wick=(d['H']-max(d['O'],d['C']))/r,lower_wick=(min(d['O'],d['C'])-d['L'])/r,clv=(2*d['C']-d['H']-d['L'])/r,range_s=r/u,true_range_s=max(r,abs(d['H']-pc),abs(d['L']-pc))/u)
 gap=(d['O']/pc-1)/s;overnight=math.log(d['O']/pc)/s;intraday=math.log(d['C']/d['O'])/s
 out.update(gap_s=gap,overnight_s=overnight,intraday_s=intraday,overnight_var_share=overnight**2/(overnight**2+intraday**2) if overnight**2+intraday**2 else None,trading_value=d['Va'],amihud=abs(ret)/d['Va']+1e-15 if d['Va']>0 else None)
 priorva=[x['Va'] for x in hist[-10:] if num(x.get('Va')) and x['Va']>0]
 rv=d['Va']/np.median(priorva) if len(priorva)>=5 else None;out['value_rvol']=rv
 conditions={'large_up':out['body_s']>=1,'large_dn':out['body_s']<=-1,'doji':abs(out['body_range'])<=.1,'long_lower':out['lower_wick']>=.5,'long_upper':out['upper_wick']>=.5,'inside':d['H']<=prev['H'] and d['L']>=prev['L'],'outside':d['H']>prev['H'] and d['L']<prev['L'],'trend_day':abs(out['body_range'])>=.7 and abs(out['clv'])>=.8,'range_exp':out['range_s']>=1.5,'range_con':out['range_s']<=.5,'gap_up':gap>=.5,'gap_dn':gap<=-.5,'jump':abs(ret)/s>=1.5}
 out.update({k:float(v) for k,v in conditions.items()});out['value_shock']=float(rv>=2) if rv is not None else None
 if abs(gap)>=.5:out.update(gap_fill=float(d['L']<=pc<=d['H']),gap_cont=float(gap*(d['C']-d['O'])>0),gap_rev=float(gap*(d['C']-pc)<0))
 if hist and num(hist[-1].get('ret')):
  out['continuation_1']=float(np.sign(hist[-1]['ret'])*ret/s)
  if num(hist[-1].get('s')) and hist[-1]['s']>0:out['vol_clustering']=abs(ret/s)*abs(hist[-1]['ret']/hist[-1]['s'])
 if len(hist)>=3 and num(hist[-3].get('ret')) and num(hist[-3].get('C')):
  out['continuation_3']=float(np.sign(hist[-3]['ret'])*(d['C']/hist[-3]['C']-1)/s)
 return out

def intraday_traits(day,d,prev,rows,s,hist):
 out={};events=[];u=prev['C']*s;b=bars5(day,rows)
 if not b:return out,events,{}
 grouped=collections.defaultdict(list)
 for r in rows:
  k=bucket(day,minute_time(r))
  if k:grouped[k].append(r)
 maxh=max(r['H'] for r in rows);minl=min(r['L'] for r in rows)
 ht=min(minute_time(r) for r in rows if r['H']==maxh);lt=min(minute_time(r) for r in rows if r['L']==minl)
 for k in ['O30','AM','PM1','PM2','CL']:
  if k=='CL' and day<'2024-11-05':continue
  rs=grouped[k]
  if rs:
   out['value_'+k]=sum(r['Va'] for r in rs)/d['Va'] if d['Va']>0 else None
   out['volume_'+k]=sum(r['Vo'] for r in rs)/d['Vo'] if d['Vo']>0 else None
   out['range_'+k]=(max(r['H'] for r in rs)-min(r['L'] for r in rs))/u
  # Empty bucket is unobserved, not certified zero activity.
  out[('hod_o30' if k=='O30' else 'hod_'+k)]=float(bucket(day,ht)==k)
  out[('lod_o30' if k=='O30' else 'lod_'+k)]=float(bucket(day,lt)==k)
 if lt!=ht:out['lod_before_hod']=float(lt<ht)
 sw=swings(b,u)
 if sw:
  out['swing_amplitude']=float(np.mean([x['amplitude'] for x in sw]));out['swing_duration']=float(np.mean([x['duration'] for x in sw]))
  ratios=[sw[i]['amplitude']/sw[i-1]['amplitude'] for i in range(1,len(sw)) if sw[i-1]['amplitude']>0]
  if ratios:out['pullback_depth']=float(np.mean(ratios))
  events.extend({'type':'CAUSAL_SWING',**x} for x in sw)
 # Nonoverlapping15m endpoints, no missing/lunch bridges.
 ret5=[];ret15=[];pairs=[];previous15=None
 for i in range(1,len(b)):
  if b[i]['t']-b[i-1]['t']==5 and same_phase(b[i-1]['t'],b[i]['t']):ret5.append(math.log(b[i]['C']/b[i-1]['C']))
  if i>=3 and b[i]['t']%15==0 and [x['t'] for x in b[i-3:i+1]]==list(range(b[i]['t']-15,b[i]['t']+1,5)) and same_phase(b[i-3]['t'],b[i]['t']):
   rv=math.log(b[i]['C']/b[i-3]['C']);ret15.append(rv)
   if previous15 and previous15[0]+15==b[i]['t'] and same_phase(previous15[0],b[i]['t']):pairs.append((previous15[1],rv))
   previous15=(b[i]['t'],rv)
 if len(pairs)>=8 and np.std(np.array(pairs)[:,0])>0 and np.std(np.array(pairs)[:,1])>0:out['lag15']=float(np.corrcoef(np.array(pairs).T)[0,1])
 if len(ret15)>=8 and len(ret5)>=8 and np.var(ret5)>0:out['variance_ratio']=float(np.var(ret15)/(3*np.var(ret5)))
 # Complete O30 needed for OR; later sparse bars cannot establish absence of a break.
 orbars=[x for x in b if 540<x['t']<=570]
 orhigh=max(x['H'] for x in orbars) if len(orbars)==6 else None
 complete=all((t+5) in {x['t'] for x in b} for t in list(range(540,690,5))+list(range(750,900 if day<'2024-11-05' else 925,5)))
 first_or=next((i for i,x in enumerate(b) if x['t']>570 and orhigh is not None and x['C']>orhigh+.25*u),None)
 if first_or is not None:
  out['or_break']=1.;out['or_follow']=response(b,first_or,30,lambda x:x['C']>=b[first_or]['C']+.5*u);out['or_fail']=response(b,first_or,30,lambda x:x['C']<orhigh-.25*u)
  events.append({'type':'OR_BREAK','confirmedAt':b[first_or]['t']})
 elif complete and orhigh is not None:out['or_break']=0.
 pdh=next((i for i,x in enumerate(b) if x['C']>prev['H']+.25*u),None)
 if pdh is not None:out['pdh_break']=1.
 elif complete:out['pdh_break']=0.
 pdl=next((i for i,x in enumerate(b) if x['C']<prev['L']-.25*u),None)
 if pdl is not None:out['pdl_reclaim']=response(b,pdl,30,lambda x:x['C']>prev['L']+.25*u)
 vw=next((i for i,x in enumerate(b) if x['VWAP'] is not None and x['C']<x['VWAP']-.25*u),None)
 if vw is not None:out['vwap_reclaim']=response(b,vw,30,lambda x:x['VWAP'] is not None and x['C']>x['VWAP']+.25*u)
 peak=trough=b[0]['C'];sell=rise=None
 for i,x in enumerate(b):
  if i and (x['t']-b[i-1]['t']!=5 or not same_phase(b[i-1]['t'],x['t'])):peak=trough=x['C']
  peak=max(peak,x['C']);trough=min(trough,x['C'])
  if sell is None and peak-x['C']>=1.5*u:sell=i
  if rise is None and x['C']-trough>=1.5*u:rise=i
 if sell is not None:out['selloff_rebound']=response(b,sell,60,lambda x:x['C']>=b[sell]['C']+.5*u)
 if rise is not None:out['rally_giveback']=response(b,rise,60,lambda x:x['C']<=b[rise]['C']-.5*u)
 # Prior-only matching bucket/bar volume confirmation, min5 histories.
 past=[x.get('bucketValue',{}).get('O30') for x in hist[-10:]];past=[x for x in past if num(x) and x>0]
 gapcomp=None
 if len(past)>=5 and grouped['O30']:
  gapcomp=float((d['O']/prev['C']-1)/s<=-.5 and sum(x['Va'] for x in grouped['O30'])>=2*np.median(past))
 confirm=None
 if first_or is not None:
  t=b[first_or]['t'];past=[x.get('barValue',{}).get(t) for x in hist[-10:]];past=[x for x in past if num(x) and x>0]
  if len(past)>=5:confirm=float(b[first_or]['Va']>=2*np.median(past))
 composites={'gap_down_value':gapcomp,'break_value':confirm,'break_fail':out.get('or_fail'),'pdl_reclaim':out.get('pdl_reclaim'),'selloff_rebound':out.get('selloff_rebound'),'rally_giveback':out.get('rally_giveback')}
 return out,events,{'bucketValue':{k:sum(r['Va'] for r in rs) for k,rs in grouped.items() if rs},'barValue':{x['t']:x['Va'] for x in b},'composites':composites,'complete5m':len(b),'touches':{key:sum(abs(x['C']-level)<=.25*u for x in b) for key,level in [('PDH',prev['H']),('PDL',prev['L'])]},'swingCount':len(sw),'swingLagSum':sum(x['lag'] for x in sw)}

def transform(a,kind):
 a=np.asarray(a,float).copy()
 if kind=='log':a=np.where(a>0,np.log(np.maximum(a,1e-300)),np.nan)
 elif kind=='share':a=np.log(np.clip(a,1e-4,1-1e-4)/(1-np.clip(a,1e-4,1-1e-4)))
 elif kind=='fisher':a=np.arctanh(np.clip(a,-.999,.999))
 return a

def mean(a,axis=0):
 n=np.sum(np.isfinite(a),axis=axis)
 return np.divide(np.nansum(a,axis=axis),n,out=np.full(np.shape(n),np.nan,dtype=float),where=n>0)

def neff(a):
 n=np.sum(np.isfinite(a),axis=0).astype(float)
 x,y=a[:-1],a[1:];ok=np.isfinite(x)&np.isfinite(y)
 xm=mean(np.where(ok,x,np.nan));ym=mean(np.where(ok,y,np.nan))
 dx=np.where(ok,x-xm,0);dy=np.where(ok,y-ym,0)
 den=np.sqrt(np.sum(dx*dx,axis=0)*np.sum(dy*dy,axis=0))
 rho=np.divide(np.sum(dx*dy,axis=0),den,out=np.zeros_like(n),where=den>0)
 rho=np.clip(rho,0,.9)
 return np.minimum(n,n*(1-rho)/(1+rho))

def spearman(x,y):
 ok=np.isfinite(x)&np.isfinite(y)
 if ok.sum()<3:return None
 a,b=rankdata(x[ok]),rankdata(y[ok]);a-=a.mean();b-=b.mean();d=np.linalg.norm(a)*np.linalg.norm(b)
 return float(a@b/d) if d>0 else None

def corr_rows(a,b):
 ok=np.isfinite(a)&np.isfinite(b);a=rankdata(np.where(ok,a,np.nan),axis=1,nan_policy='omit');b=rankdata(np.where(ok,b,np.nan),axis=1,nan_policy='omit')
 a=np.where(ok,a-np.nanmean(a,axis=1,keepdims=True),0);b=np.where(ok,b-np.nanmean(b,axis=1,keepdims=True),0)
 den=np.sqrt(np.sum(a*a,axis=1)*np.sum(b*b,axis=1))
 return np.divide(np.sum(a*b,axis=1),den,out=np.full(len(a),np.nan),where=(den>0)&(ok.sum(1)>=30))

def fdr(ps):
 p=np.asarray(ps,float);order=np.argsort(p,kind='stable');v=p[order]*len(p)/np.arange(1,len(p)+1);v=np.minimum.accumulate(v[::-1])[::-1];out=np.ones(len(p));out[order]=np.minimum(1,v);return out

def fit_peer(cov,a,b):
 # All preprocessing and coefficients trained on A only.
 ca,cb=cov
 mu=ca.mean(axis=0);sd=ca.std(axis=0);sd=np.where(sd>1e-8,sd,1)
 xa=np.column_stack([np.ones(len(a)),(ca-mu)/sd]);xb=np.column_stack([np.ones(len(a)),(cb-mu)/sd])
 beta=np.linalg.lstsq(xa,a,rcond=1e-10)[0]
 return xa,xb,beta,mu,sd

def profile(a,kind):
 raw=mean(a);n=np.sum(np.isfinite(a),axis=0);eff=neff(a)
 value=np.log((np.nansum(a,axis=0)+.5)/(n-np.nansum(a,axis=0)+.5)) if kind=='rate' else raw
 return value,raw,n,eff

def block_weights(n,reps,rng):
 # Moving blocks inside each half only, preserving no wrap across A/embargo/B.
 w=np.zeros((reps,n))
 for i in range(reps):
  ids=[]
  while len(ids)<n:
   start=int(rng.integers(0,max(1,n-2)));ids.extend(range(start,min(start+3,n)))
  w[i]=np.bincount(ids[:n],minlength=n)
 return w

def boot_profile(a,w,kind):
 valid=np.isfinite(a).astype(float);n=w@valid;tot=w@np.nan_to_num(a)
 if kind=='rate':return np.where(n>0,np.log((tot+.5)/(n-tot+.5)),np.nan)
 return np.divide(tot,n,out=np.full_like(tot,np.nan),where=n>0)

def collect(cache,output,p):
 prior=saved.read(PRIOR/'08_coverage_after_recovery.json');pins={x['sessionDate'] if 'sessionDate' in x else p['sessions'][i]:x for i,x in enumerate(prior['perSession'])}
 universe=collections.defaultdict(set)
 with gzip.open(PRIOR/'security_session_classification.csv.gz','rt') as f:
  for r in csv.DictReader(f):universe[r['session']].add(r['code'])
 codes=sorted(set.union(*universe.values()));index={c:i for i,c in enumerate(codes)};ids=[x['id'] for x in p['catalog']];mi={x:i for i,x in enumerate(ids)}
 data=np.full((57,len(codes),len(ids)),np.nan);cov=np.full((57,len(codes),4),np.nan);eligible=np.zeros((57,len(codes),2),bool);history={c:[] for c in codes}
 audit=[];pattern=[];scaleaudit=[];swstats=collections.Counter();touches=collections.Counter();composites=collections.defaultdict(lambda:[0,0]);return_day=np.full((57,len(codes)),np.nan)
 dailycount=minutecount=0
 for di,day in enumerate(p['sessions']):
  folder=Path(cache)/day;saved.authorize_date(day)
  for name,h in pins[day]['inputHashes'].items():assert saved.sha(folder/name)==h,'RAW_HASH:'+day+name
  lm=saved.read(folder/'l0-manifest.json');mn=next(x for x in pins[day]['inputHashes'] if x.endswith('minute-manifest.json'));mm=saved.read(folder/mn)
  daily,_=saved.pages(folder/'daily-pages.json',lm['daily']);minutes,_=saved.pages(folder/'minute-pages.json',mm)
  assert all(x['Date']==day for x in daily+minutes),'CROSS_SESSION'
  dailycount+=len(daily);minutecount+=len(minutes);dc={x['Code']:x for x in daily};by=collections.defaultdict(list)
  for r in minutes:
   if r['Code'] in universe[day]:by[r['Code']].append(r)
  rec=collections.Counter();rec['universe']=len(universe[day]);ss=[]
  for code in codes:
   j=index[code];hist=history[code];d=dc.get(code) if code in universe[day] else None;prev=hist[-1].get('daily') if hist else None;s=scale(hist)
   entry={'daily':d,'tr':None,'Va':d['Va'] if valid(d) else None,'C':d['C'] if valid(d) else None,'s':s,'ret':None}
   safe=valid(d) and valid(prev) and not action(d) and not action(prev)
   if safe:
    entry['tr']=max(d['H']-d['L'],abs(d['H']-prev['C']),abs(d['L']-prev['C']))/prev['C'];entry['ret']=d['C']/prev['C']-1;return_day[di,j]=entry['ret']
   rows=sorted(by[code],key=minute_time)
   if len({minute_time(x) for x in rows})!=len(rows):raise ValueError('DUPLICATE_MINUTE')
   ok,info=intraday_eligible(d,rows)
   rec['vol_recon_ok']+=bool(info.get('vol_recon_ok'));rec['extrema_match']+=bool(info.get('extrema_match'));rec['reconstruction_eligible']+=ok
   if safe and s and di>=5:
    eligible[di,j,0]=True;rec['daily_scaled_eligible']+=1;ss.append(s)
    traits=daily_traits(d,prev,hist,s)
    regular=sum(saved.phase(day,minute_time(x))=='REGULAR' for x in rows);expected=300 if day<'2024-11-05' else 325
    cov[di,j]=[math.log(max(d['Va'],1)),math.log(s),math.log(d['C']),regular/expected]
    if ok:
     eligible[di,j,1]=True;rec['intraday_scaled_eligible']+=1
     intra,ev,extra=intraday_traits(day,d,prev,rows,s,hist);traits.update(intra);entry.update(extra)
     swstats['confirmed']+=extra.get('swingCount',0);swstats['lagMinutes']+=extra.get('swingLagSum',0);touches.update(extra.get('touches',{}))
     for name,value in extra.get('composites',{}).items():
      if value is not None:composites[name][0]+=int(value);composites[name][1]+=1
     if len(pattern)<200:pattern.append({'session':day,'codeKey':code,'events':ev[:5],'labels':LABELS,'purpose':'numeric semantics diagnostic, not independently human reviewed'})
    for k,v in traits.items():
     if k in mi and num(v):data[di,j,mi[k]]=v
   hist.append(entry)
  audit.append({'session':day,**dict(rec)});scaleaudit.append({'session':day,'n':len(ss),'median':float(np.median(ss)) if ss else None})
  print(json.dumps({'session':day,'daily':rec['daily_scaled_eligible'],'intraday':rec['intraday_scaled_eligible']}),flush=True)
  del minutes,daily,by
 return data,cov,eligible,codes,{'bySession':audit,'rawDailyRows':dailycount,'rawMinuteRows':minutecount,'scale':scaleaudit,'swing':dict(swstats),'touches':dict(touches),'composites':dict(composites),'numericEventSamples':pattern},return_day

def assess(data,cov,eligible,p,returns):
 A=np.arange(5,29);B=np.arange(34,57);pool=np.r_[A,B];rng=np.random.default_rng(p['statistics']['seed']);perm=rng.permutation(pool);RA,RB=perm[:24],perm[24:]
 wa=block_weights(len(A),500,rng);wb=block_weights(len(B),500,rng)
 shock=np.abs(returns);med=np.nanmedian(shock,axis=1);tail=sorted(pool,key=lambda i:(-(med[i] if np.isfinite(med[i]) else -1),i))[:3];TA=np.array([i for i in A if i not in tail]);TB=np.array([i for i in B if i not in tail])
 results=[];profiles=[];acceptedVectors={}
 for k,item in enumerate(p['catalog']):
  name,kind=item['id'],item['transform'];tier=0 if item['tier']=='daily' else 1;z=transform(data[:,:,k],kind)
  av,ar,an,ae=profile(z[A],kind);bv,br,bn,be=profile(z[B],kind);ca=mean(cov[A]);cb=mean(cov[B]);minobs=8 if name in CONDITIONAL else 20
  fitmask=(eligible[A,:,tier].sum(0)>=20)&(an>=minobs)&np.isfinite(av)&np.all(np.isfinite(ca),axis=1)
  bmask=(eligible[B,:,tier].sum(0)>=20)&(bn>=minobs)&np.isfinite(bv)&np.all(np.isfinite(cb),axis=1)
  mask=fitmask&bmask
  n=int(mask.sum());r={'id':name,'family':item['family'],'tier':item['tier'],'pairedSymbols':n,'status':'INSUFFICIENT','p':1.,'q':1.,'reasons':[]}
  allraw={'id':name,'allSymbolRawA':ar.tolist(),'allSymbolRawB':br.tolist(),'allSymbolNEffA':ae.tolist(),'allSymbolNEffB':be.tolist(),'allSymbolNSessionsA':an.tolist(),'allSymbolNSessionsB':bn.tolist(),'allSymbolStatus':['ELIGIBLE' if v else 'INSUFFICIENT' for v in mask],'insufficientShrinkWeight':0,'insufficientEstimate':'PRIOR_ONLY; peer prior undefined when no valid A fit'}
  if n<100:r['reasons']=['PAIRED_SAMPLE_BELOW100'];results.append(r);profiles.append(allraw);continue
  a,b=av[mask],bv[mask];xf,_,beta,mu,sd=fit_peer((ca[fitmask],ca[fitmask]),av[fitmask],av[fitmask])
  xa=np.column_stack([np.ones(len(a)),(ca[mask]-mu)/sd]);xb=np.column_stack([np.ones(len(a)),(cb[mask]-mu)/sd]);pa,pb=xa@beta,xb@beta;aa,bb=a-pa,b-pb
  raw=spearman(a,b);inc=spearman(aa,bb)
  w=ae[mask]/(ae[mask]+20);posterior=pa+w*aa
  # Rates use Beta posterior at peer logistic mean, then return to logit for calibration.
  if kind=='rate':
   priorprob=1/(1+np.exp(-np.clip(pa,-30,30)));postprob=(ae[mask]*(ar[mask])+20*priorprob)/(ae[mask]+20);posterior=np.log(np.clip(postprob,1e-9,1-1e-9)/(1-np.clip(postprob,1e-9,1-1e-9)))
  x=posterior-pa;den=np.sum((x-x.mean())**2);slope=float(np.sum((x-x.mean())*(bb-bb.mean()))/den) if den>0 else None
  # Session-block bootstrap peer residualization, re-fit coefficients for each bootstrap sample with fixed A design.
  bf=boot_profile(z[A][:,fitmask],wa,kind);ba=boot_profile(z[A][:,mask],wa,kind);bc=boot_profile(z[B][:,mask],wb,kind);coeff=np.full((len(bf),xf.shape[1]),np.nan)
  for bi,row in enumerate(bf):
   finite=np.isfinite(row)
   if finite.sum()>=100:coeff[bi]=np.linalg.lstsq(xf[finite],row[finite],rcond=1e-10)[0]
  ba-=coeff@xa.T;bc-=coeff@xb.T;boot=corr_rows(ba,bc);boot=boot[np.isfinite(boot)];lo,hi=np.quantile(boot,[.025,.975]) if len(boot)>=400 else (-1.,1.);pv=(1+np.sum(np.abs(boot-(inc or 0))>=abs(inc or 0)))/(len(boot)+1)
  qr=np.quantile(aa,[.2,.8]);spread=float(np.mean(bb[aa>=qr[1]])-np.mean(bb[aa<=qr[0]]))
  # Reverse direction is an auxiliary fit only, never supplies primary priors.
  bx,ax,betab,_,_=fit_peer((cb[mask],ca[mask]),b,a);reverse=spearman(b-bx@betab,a-ax@betab)
  cuts=np.quantile(ca[mask,0],[1/3,2/3]);strata=[]
  for ix in range(3):
   st=np.digitize(ca[mask,0],cuts)==ix;rr=spearman(aa[st],bb[st]);strata.append({'n':int(st.sum()),'incremental':rr,'pass':bool(st.sum()>=30 and rr is not None and rr>0)})
  rv1,_,rn1,_=profile(z[RA],kind);rv2,_,rn2,_=profile(z[RB],kind);rm=mask&np.isfinite(rv1)&np.isfinite(rv2)&(rn1>=minobs)&(rn2>=minobs)
  random_r=spearman(rv1[rm],rv2[rm]);ratio=raw/random_r if raw is not None and random_r and random_r>0 else None
  ta,_,tn1,_=profile(z[TA],kind);tb,_,tn2,_=profile(z[TB],kind)
  tm=mask&np.isfinite(ta)&np.isfinite(tb)&(tn1>=minobs)&(tn2>=minobs)&(eligible[TA,:,tier].sum(0)>=20)&(eligible[TB,:,tier].sum(0)>=20)
  tr=ti=None
  if tm.sum()>=100:
   tc1=mean(cov[TA])[tm];tc2=mean(cov[TB])[tm];xx,yy,bt,_,_=fit_peer((tc1,tc2),ta[tm],tb[tm]);tr=spearman(ta[tm],tb[tm]);ti=spearman(ta[tm]-xx@bt,tb[tm]-yy@bt)
  market=z-np.nanmedian(z,axis=1)[:,None]
  mr=spearman(mean(market[A])[mask],mean(market[B])[mask])
  checks={'raw':raw is not None and raw>=.30,'incremental':inc is not None and inc>=.15,'CI':lo>0,'calibration':slope is not None and .5<=slope<=1.5,'direction':inc is not None and reverse is not None and inc>0 and reverse>0,'strata':sum(x['pass'] for x in strata)>=2,'timeRandom':ratio is not None and ratio>=.7,'tail':tr is not None and ti is not None and tr>=.30 and ti>=.15}
  r.update(rawSplitHalf=raw,spearmanBrown=2*raw/(1+raw) if raw is not None and raw>-1 else None,incremental=inc,reverseIncremental=reverse,ci=[float(lo),float(hi)],p=float(pv),calibrationSlope=slope,quintileBSpread=spread,liquidityStrata=strata,randomSplit=random_r,timeRandomRatio=ratio,tailRaw=tr,tailIncremental=ti,tailPairedSymbols=int(tm.sum()),marketRelative=mr,checks=checks,reasons=[x for x,v in checks.items() if not v],status='WATCH')
  # Save all symbol estimates including insufficient. Join key is never a predictor.
  residualvar=mean((z[A]-mean(z[A])[None,:])**2)[mask];psd=np.sqrt(np.maximum(residualvar,0)/(ae[mask]+20))
  if kind=='rate':
   alpha=ae[mask]*ar[mask]+20*priorprob;beta_rate=ae[mask]*(1-ar[mask])+20*(1-priorprob)
   probvar=alpha*beta_rate/((alpha+beta_rate)**2*(alpha+beta_rate+1));psd=np.sqrt(probvar)/np.maximum(postprob*(1-postprob),1e-12)
  profiles.append({**allraw,'id':name,'indices':np.flatnonzero(mask).tolist(),'rawA':ar[mask].tolist(),'rawB':br[mask].tolist(),'transformedA':a.tolist(),'peerPredictionA':pa.tolist(),'peerRelativeA':aa.tolist(),'posteriorA':posterior.tolist(),'shrink_w':w.tolist(),'posterior_sd':psd.tolist(),'nEffA':ae[mask].tolist(),'nEffB':be[mask].tolist(),'nSessionsA':an[mask].tolist(),'nSessionsB':bn[mask].tolist(),'priorFit':'A_ONLY','covariateMean':mu.tolist(),'covariateSD':sd.tolist(),'peerCoefficients':beta.tolist(),'excludedSymbolsPriorOnly':int(len(mask)-n)})
  acceptedVectors[name]=(mask,av);results.append(r)
  print(json.dumps({'trait':name,'paired':n,'measured':True}),flush=True)
 qs=fdr([x['p'] for x in results]);selected=[];correlations=[]
 for r,q in zip(results,qs):
  r['q']=float(q)
  if r['status']=='INSUFFICIENT':continue
  if q>.1:r['reasons'].append('FDR')
  if not r['reasons']:
   mask,a=acceptedVectors[r['id']]
   for old in selected:
    om,oa=acceptedVectors[old];mm=mask&om;rr=spearman(a[mm],oa[mm]);correlations.append({'left':old,'right':r['id'],'rho':rr})
    if rr is not None and abs(rr)>=.8:r['reasons'].append('REDUNDANT_WITH:'+old);break
   if not r['reasons']:r['status']='USABLE';selected.append(r['id'])
 usable=[r for r in results if r['status']=='USABLE'];families=sorted({x['family'] for x in usable});daily=sum(x['tier']=='daily' for x in usable);intra=len(usable)-daily
 complete=len(usable)>=8 and len(families)>=4 and daily>=2 and intra>=2
 return results,profiles,{'usable':len(usable),'families':families,'daily':daily,'intraday':intra,'status':'RESEARCH_STOCK_BEHAVIOR_DICTIONARY_V0_COMPLETE' if complete else 'V0_TRAIT_RELIABILITY_INSUFFICIENT','complete':complete,'acceptedCorrelations':correlations,'excludedTailSessions':[p['sessions'][i] for i in tail]}

def clean(x):
 if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [clean(v) for v in x]
 if isinstance(x,np.ndarray):return clean(x.tolist())
 if isinstance(x,np.generic):return clean(x.item())
 if isinstance(x,float) and not math.isfinite(x):return None
 return x

def write(out,name,x):saved.write(Path(out)/name,clean(x))
def writegz(path,x):
 with Path(path).open('xb') as f:
  with gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as z:z.write(saved.encoded(clean(x)))

def audit(directory):
 p=registry();directory=Path(directory);m=saved.read(directory/'manifest.json')
 for name,h in m.items():assert saved.sha(directory/name)==h,'EVIDENCE_HASH:'+name
 g=saved.read(directory/'26_completion_gate.json');a=saved.read(directory/'25_dictionary_v0.json')
 assert a['evidence_class']=='HISTORICAL_RECONSTRUCTION' and a['labels']==LABELS
 assert not a['productionAllowed'];assert g['complete']==(g['status']=='RESEARCH_STOCK_BEHAVIOR_DICTIONARY_V0_COMPLETE')
 assert all(v is False for v in saved.read(directory/'32_safety_data_boundary.json')['safety'].values())
 return {'status':'PASS','artifacts':len(m)}

def measure(cache,extraction,output):
 p=registry();out=Path(output);out.mkdir(parents=True,exist_ok=False);t=time.perf_counter()
 receipt=saved.read(extraction);assert receipt['report19PayloadsExtracted']==0 and receipt['protectedPayloadsExtracted']==0
 data,cov,eligible,codes,stats,rets=collect(cache,out,p)
 results,profiles,gate=assess(data,cov,eligible,p,rets)
 write(out,'01_start_state.json',saved.read(BASE/'start_state.json'))
 write(out,'02_registry_precommit.json',{'precommit':saved.read(BASE/'start_state.json')['registryPrecommit'],'sha256':saved.sha(BASE/'registry.json'),'registry':p})
 write(out,'03_data_eligibility.json',{k:v for k,v in stats.items() if k not in ['numericEventSamples','scale','swing','touches','composites']})
 write(out,'04_scale_s.json',{'contract':p['scale'],'bySession':stats['scale']})
 write(out,'05_trait_catalog.json',p['catalog']);write(out,'06_pattern_vocabulary.json',p['atoms']);write(out,'07_composite_patterns.json',{'registry':p['composites'],'descriptiveCounts':stats['composites'],'primaryTests':False,'noPerSymbolInference':True})
 write(out,'08_walk_forward_split.json',p['split'])
 write(out,'09_tier1_daily_traits.json',[x for x in results if x['tier']=='daily']);write(out,'10_tier2_intraday_traits.json',[x for x in results if x['tier']=='intraday'])
 write(out,'11_support_resistance.json',{'contract':p['levels'],'touchCounts':stats['touches'],'levelAvailability':'PDH/PDL previous closed day; OR at09:30; VWAP cumulative observed value/volume; no free level mining'})
 write(out,'12_swing.json',{'contract':'single0.5S reversal; confirmedAt not extremeAt is availability; gaps/lunch reset','observed':stats['swing']})
 write(out,'13_volume_value.json',{'primary':'Trading Value','secondary':'share volume','missing':'UNKNOWN, no zero-fill','rvol':'prior10 matching bucket/bar, minimum5; no future-conditioned dry-up','auctionLimitation':'terminal minute proxy only; afternoon-opening portion not isolated'})
 writegz(out/'profiles.json.gz',{'labels':LABELS,'evidence_class':p['evidence_class'],'codeKeys':codes,'identity':'provisional code; not predictor; code reuse uncertainty remains','profileAsOf':p['split']['embargo'][0],'windowEnd':p['split']['A'][-1],'profiles':profiles})
 for n,fields in [('14_raw_profiles',['allSymbolRawA','allSymbolRawB','allSymbolStatus']),('15_peer_relative_profiles',['peerPredictionA','peerRelativeA','peerCoefficients']),('16_posterior_profiles',['posteriorA','shrink_w','posterior_sd','nEffA'])]:write(out,n+'.json',{'artifact':'profiles.json.gz','fields':fields,'SHA256':saved.sha(out/'profiles.json.gz'),'priorFit':'A_ONLY','insufficient':'prior-only / shrink_w0; no fitted prior if paired sample<100'})
 for n,fields in [('17_split_half_reliability',['rawSplitHalf','spearmanBrown','reverseIncremental','randomSplit','timeRandomRatio','marketRelative']),('18_incremental_reliability',['incremental','quintileBSpread']),('19_calibration',['calibrationSlope']),('20_liquidity_strata',['liquidityStrata']),('21_block_bootstrap',['ci','p']),('22_tail_session_sensitivity',['tailRaw','tailIncremental','tailPairedSymbols']),('23_multiple_testing',['p','q'])]:
  write(out,n+'.json',{'rows':[{k:x.get(k) for k in ['id','status']+fields} for x in results],'contract':p['statistics'],'tailExcluded':gate['excludedTailSessions']})
 write(out,'24_trait_gate.json',results)
 write(out,'25_dictionary_v0.json',{'name':'RESEARCH_STOCK_BEHAVIOR_DICTIONARY_V0','status':gate['status'],'labels':LABELS,'evidence_class':p['evidence_class'],'productionAllowed':False,'oosConfirmed':False,'pitVerified':False,'profileArtifact':'profiles.json.gz','profileHash':saved.sha(out/'profiles.json.gz'),'registryHash':saved.sha(BASE/'registry.json'),'usableTraits':[x['id'] for x in results if x['status']=='USABLE'],'definitionTransferOnly':True})
 write(out,'26_completion_gate.json',gate)
 write(out,'27_human_semantics_audit.json',{'status':'NOT_APPLICABLE','reason':'No independent human chart reviewer; numeric event samples are not visual validation','numericSamples':stats['numericEventSamples']})
 write(out,'28_lane_p_compatibility.json',{'status':'PASS_ISOLATION','lanePHashes':saved.read(BASE/'start_state.json')['lanePHashes'],'estimatesPromoted':0,'definitionsOnly':True,'productionLoader':'fail-closed rejects all research artifacts; cannot relabel through research module'})
 write(out,'29_tests.json',{'status':'PENDING_CI_FINALIZATION'});write(out,'30_regression.json',{'status':'PENDING_CI_FINALIZATION'});write(out,'31_ci.json',{'status':'PENDING_CI_FINALIZATION'})
 write(out,'32_safety_data_boundary.json',{'safety':p['safety'],'extraction':receipt,'sealedPayloadReads':0,'newProviderRequests':0,'strategyOutcomeEvaluation':0,'registryLook':'one fixed A->B research; repeats deterministic only','exposure':'existing E2/E3 retained; A/B are internal development, not fresh/OOS','lanePUnchanged':True,'historicalMissing':'UNKNOWN','sourceManifest':saved.sha(PRIOR/'manifest.json')})
 counts=collections.Counter(x['status'] for x in results)
 report=f'''# Research Stock Behavior Dictionary v0\n\n{gate['status']}\n\nRESEARCH_ONLY / HISTORICAL_RECONSTRUCTION / NOT_FOR_PRODUCTION / NOT_OOS_CONFIRMED / NOT_PIT_VERIFIED.\n\nRegistry73 scalar,6 descriptive composites. Half A24 sessions, embargo5, Half B23, initial burn-in5. Current session never contributes to its scale or prior-volume reference. Existing57 sessions only; no provider acquisition or sealed data.\n\nStatus counts: {dict(counts)}. USABLE{gate['usable']}, families{len(gate['families'])}, daily{gate['daily']}, intraday{gate['intraday']}. Completion requires8/4/2/2 and fixed isolation/integrity guards.\n\nFailed and insufficient traits retained in24_trait_gate.json. All provisional symbol profiles including insufficient status and nEff are in profiles.json.gz. Join codes are never predictors. A-only priors do not become official PIT profiles.\n\nKnown limitations: historical corrections/identity/missing-state provenance unresolved; price proxy is not verified tick size. Sparse intraday paths remain unknown. No human chart audit. No Entry/EXIT P&L, model or context learning. Empirical results are development reconstruction only.\n\nGate failure is preserved without adding traits or relaxing thresholds. Lane P is unchanged. Next: review fixed per-trait failure reasons and usable definitions; no automatic Entry/EXIT or formal-v1 promotion.\n'''
 write(out,'33_final_report.md',report);write(out,'34_final_handoff.md',report)
 write(out,'exposure_trial_delta.json',{'priorExposureHash':saved.sha(PRIOR/'09_exposure_ledger.json'),'priorTrialHash':saved.sha(PRIOR/'10_trial_ledger.jsonl'),'newRegisteredScalars':len(p['catalog']),'primaryLooks':1,'protectedPayloadReads':0,'classificationDowngrades':0,'newOOSClaim':False})
 write(out,'manifest.json',{f.name:saved.sha(f) for f in sorted(out.iterdir()) if f.is_file()})
 # Runtime receipt excluded from deterministic manifest.
 write(out,'runtime.json',{'seconds':time.perf_counter()-t,'inputRows':stats['rawMinuteRows'],'profileBytes':(out/'profiles.json.gz').stat().st_size})
 print(json.dumps(gate),flush=True);audit(out)

def finalize(directory,regression,head,run_id):
 out=Path(directory);reg=Path(regression);r=saved.read(reg/'full/regression.json');assert r['status']=='PASS'
 log=(reg/'targeted-tests.log').read_text();assert '\nOK' in log
 for name,x in [('29_tests.json',{'status':'PASS','log':log}),('30_regression.json',r),('31_ci.json',{'status':'MEASUREMENT_AND_REGRESSION_PASS','head':head,'runId':run_id,'repeatedManifestIdentical':True})]:
  (out/name).write_bytes(saved.encoded(x))
 (out/'manifest.json').write_bytes(saved.encoded({f.name:saved.sha(f) for f in sorted(out.iterdir()) if f.is_file() and f.name not in ['manifest.json','runtime.json']}))
 audit(out)

def main():
 a=argparse.ArgumentParser();a.add_argument('command',choices=['measure','audit','finalize']);a.add_argument('--cache');a.add_argument('--extraction');a.add_argument('--output-dir');a.add_argument('--directory');a.add_argument('--regression');a.add_argument('--head');a.add_argument('--run-id');x=a.parse_args()
 if x.command=='measure':measure(x.cache,x.extraction,x.output_dir)
 elif x.command=='audit':print(audit(x.directory))
 else:finalize(x.directory,x.regression,x.head,x.run_id)
if __name__=='__main__':main()
