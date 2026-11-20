"""Expanded Development remeasurement; fixed v0 traits/Gates, explicit new split."""
import argparse,collections,copy,gzip,hashlib,json,math,time
from pathlib import Path
import numpy as np
from scripts import phase57_research_dictionary_v0 as v
from scripts import phase57_expansion_data as admission
from scripts.phase57_expansion_assess import assess
B=admission.B

def collect(cache,lane,p):
 allowed=p['dailyDevelopment'] if lane=='daily' else p['intradayDevelopment'];allowed=set(allowed)
 calendar=sorted(r['Date'] for r in v.saved.read(B/'probe-v2/calendar.json')['data'] if r['HolDiv']=='1')
 grid=[d for d in calendar if min(allowed)<=d<=max(allowed)];universe={};pins={};codes=set()
 for day in sorted(allowed):
  folder=Path(cache)/day;master,info=v.saved.pages(folder/'master-pages.json')
  assert all(r['Date']==day for r in master)
  universe[day]={r['Code'] for r in master if str(r.get('Mkt')) in {'0111','0112','0113'} and str(r.get('ProdCat'))=='011'}
  codes.update(universe[day]);pins[day]={'master':info}
 codes=sorted(codes);index={c:i for i,c in enumerate(codes)};catalog=v.registry()['catalog'];mi={x['id']:i for i,x in enumerate(catalog)}
 data=np.full((len(grid),len(codes),len(catalog)),np.nan);cov=np.full((len(grid),len(codes),4),np.nan);eligible=np.zeros((len(grid),len(codes),2),bool);returns=np.full((len(grid),len(codes)),np.nan)
 histories={c:[] for c in codes};records=[]
 for di,day in enumerate(grid):
  if day not in allowed:
   histories={c:[] for c in codes};records.append({'session':day,'status':'EXCLUDED_NO_PAYLOAD_READ'});continue
  admission.authorize(day,'daily',p);folder=Path(cache)/day;daily,diinfo=v.saved.pages(folder/'daily-pages.json');pins[day]['daily']=diinfo
  assert all(r['Date']==day for r in daily);assert len({r['Code'] for r in daily})==len(daily)
  dc={r['Code']:r for r in daily};by=collections.defaultdict(list);minute_rows=0
  if lane=='intraday':
   admission.authorize(day,'minute',p);minutes,minfo=v.saved.pages(folder/'minute-pages.json');pins[day]['minute']=minfo;minute_rows=len(minutes)
   assert all(r['Date']==day for r in minutes)
   for r in minutes:
    if r['Code'] in universe[day]:by[r['Code']].append(r)
   del minutes
  rec=collections.Counter(universe=len(universe[day]),rawDailyRows=len(daily),rawMinuteRows=minute_rows)
  for code in codes:
   j=index[code];hist=histories[code];d=dc.get(code) if code in universe[day] else None;prev=hist[-1].get('daily') if hist else None;s=v.scale(hist)
   entry={'daily':d,'tr':None,'Va':d['Va'] if v.valid(d) else None,'C':d['C'] if v.valid(d) else None,'s':s,'ret':None}
   safe=v.valid(d) and v.valid(prev) and not v.action(d) and not v.action(prev)
   if safe:
    entry['tr']=max(d['H']-d['L'],abs(d['H']-prev['C']),abs(d['L']-prev['C']))/prev['C'];entry['ret']=d['C']/prev['C']-1;returns[di,j]=entry['ret']
   rows=sorted(by[code],key=v.minute_time) if lane=='intraday' else []
   assert len({v.minute_time(x) for x in rows})==len(rows),'DUPLICATE_MINUTE'
   ok,info=v.intraday_eligible(d,rows) if lane=='intraday' else (False,{})
   rec['vol_recon_ok']+=bool(info.get('vol_recon_ok'));rec['extrema_match']+=bool(info.get('extrema_match'));rec['reconstruction_eligible']+=ok
   if safe and s and len(hist)>=5:
    eligible[di,j,0]=True;rec['dailyEligible']+=1;traits=v.daily_traits(d,prev,hist,s)
    regular=sum(v.saved.phase(day,v.minute_time(x))=='REGULAR' for x in rows);expected=300 if day<'2024-11-05' else 325
    coverage=regular/expected if lane=='intraday' else sum(v.valid(x.get('daily')) for x in hist[-10:])/len(hist[-10:])
    cov[di,j]=[math.log(max(d['Va'],1)),math.log(s),math.log(d['C']),coverage]
    if ok:
     eligible[di,j,1]=True;rec['intradayEligible']+=1;it,ev,extra=v.intraday_traits(day,d,prev,rows,s,hist);traits.update(it);entry.update(extra)
    for name,value in traits.items():
     if name in mi and v.num(value):data[di,j,mi[name]]=value
   hist.append(entry);histories[code]=hist[-10:]
  records.append({'session':day,'status':'ADMITTED',**dict(rec)})
  print(json.dumps({'lane':lane,'session':day,'dailyEligible':rec['dailyEligible'],'intradayEligible':rec['intradayEligible']}),flush=True)
 q=copy.deepcopy(v.registry());q['sessions']=grid;q['split']=p['dailySplit' if lane=='daily' else 'intradaySplit']
 return data,cov,eligible,returns,codes,q,{'sessions':records,'inputHashes':pins,'unknownMissing':'UNKNOWN','noZeroFill':True}

def drift_summary(z,window):
 n=len(z);recent=z[max(0,n-window):];prior=z[max(0,n-2*window):max(0,n-window)]
 a=v.mean(recent);na=np.isfinite(recent).sum(0)
 if len(prior):
  b=v.mean(prior);nb=np.isfinite(prior).sum(0);va=v.mean((recent-a)**2);vb=v.mean((prior-b)**2)
  se=np.sqrt(va/np.maximum(na,1)+vb/np.maximum(nb,1));score=np.divide(a-b,se,out=np.full_like(a,np.nan),where=(se>0)&(na>=20)&(nb>=20))
 else:score=np.full_like(a,np.nan)
 ew={}
 for half in [20,60,250]:
  weights=np.exp2(-np.arange(n-1,-1,-1)/half)[:,None];valid=np.isfinite(z);den=(weights*valid).sum(0)
  ew[str(half)]=np.divide((weights*np.nan_to_num(z)).sum(0),den,out=np.full(z.shape[1],np.nan),where=(den>0)&(valid.sum(0)>=20)).tolist()
 return {'nonOverlapZ':score.tolist(),'driftFlag':[bool(abs(x)>3) if np.isfinite(x) else None for x in score],'ewHalfLife':ew,'use':'confidence only; no P&L signal','structuralEventEvidence':'corporate action rows excluded by unchanged v0 rule; identity-event feed unavailable'}

def window_profiles(data,cov,eligible,p,codes,results):
 output=[];status={x['id']:x for x in results}
 for window in [20,60,250]:
  ix=np.arange(max(0,len(data)-window),len(data));cv=v.mean(cov[ix]);through=p['sessions'][-1]
  for k,item in enumerate(p['catalog']):
   z=v.transform(data[ix,:,k],item['transform']);val,raw,n,eff=v.profile(z,item['transform']);tier=0 if item['tier']=='daily' else 1
   minimum=8 if item['id'] in v.CONDITIONAL else 20
   mask=(eligible[ix,:,tier].sum(0)>=20)&(n>=minimum)&np.isfinite(val)&np.all(np.isfinite(cv),axis=1)
   record={'trait':item['id'],'window':window,'windowStart':p['sessions'][ix[0]],'computed_through':through,'firstUseRule':'strictly later session only','definition_hash':v.saved.digest(item),'evidence_class':'HISTORICAL_RECONSTRUCTION','transform':item['transform'],'raw':v.mean(data[ix,:,k]).tolist(),'transformed':val.tolist(),'n_sessions':n.tolist(),'nEff':eff.tolist(),'episodes':n.tolist() if item['id'] in v.CONDITIONAL else None,'coverage':(eligible[ix,:,tier].sum(0)/len(ix)).tolist(),'reliability':status[item['id']],'status':['ELIGIBLE' if m else 'INSUFFICIENT' for m in mask],'insufficientShrinkWeight':0}
   if mask.sum()>=100:
    x,_,beta,mu,sd=v.fit_peer((cv[mask],cv[mask]),val[mask],val[mask]);peer=x@beta;res=val[mask]-peer;weight=eff[mask]/(eff[mask]+20);post=peer+weight*res
    psd=np.sqrt(np.maximum(v.mean((z-v.mean(z)[None,:])**2)[mask],0)/(eff[mask]+20))
    if item['transform']=='rate':
     prob=1/(1+np.exp(-np.clip(peer,-30,30)));alpha=eff[mask]*raw[mask]+20*prob;beta_r=eff[mask]*(1-raw[mask])+20*(1-prob);pp=alpha/(alpha+beta_r);post=np.log(np.clip(pp,1e-9,1-1e-9)/(1-np.clip(pp,1e-9,1-1e-9)));psd=np.sqrt(alpha*beta_r/((alpha+beta_r)**2*(alpha+beta_r+1)))/np.maximum(pp*(1-pp),1e-12)
    record.update(indices=np.flatnonzero(mask).tolist(),peer_relative=res.tolist(),peer_prediction=peer.tolist(),posterior=post.tolist(),shrink_w=weight.tolist(),posterior_sd=psd.tolist(),CI=np.column_stack([post-1.96*psd,post+1.96*psd]).tolist(),confidence='shrink_w + posterior_sd + coverage; no combined invented score',priorTrainWindowEnd=through)
   record.update(stability='See fixed A-to-B reliability; window estimates alone do not prove persistence',drift=drift_summary(v.transform(data[:,:,k],item['transform']),window))
   output.append(record)
 return {'codeJoinKeys':codes,'symbolIdAsPredictor':False,'labels':v.LABELS,'profiles':output}

def measure(cache,output):
 out=Path(output);out.mkdir(parents=True,exist_ok=False);p=admission.plan();start=time.time();lane_results={}
 for lane in ['daily','intraday']:
  data,cov,eligible,returns,codes,q,coverage=collect(cache,lane,p)
  results,profiles,gate=assess(data,cov,eligible,q,returns)
  old={r['id']:r['status'] for r in v.saved.read(v.BASE/'measurement/24_trait_gate.json')}
  v.write(out,lane+'-coverage.json',coverage);v.write(out,lane+'-reliability.json',results);v.write(out,lane+'-gate.json',gate)
  v.writegz(out/(lane+'-profiles.json.gz'),{'labels':v.LABELS,'codeJoinKeys':codes,'split':q['split'],'profiles':profiles})
  v.writegz(out/(lane+'-windows.json.gz'),window_profiles(data,cov,eligible,q,codes,results))
  v.write(out,lane+'-transition.json',[{'id':r['id'],'previous':old[r['id']],'expanded':r['status'],'reasons':r['reasons']} for r in results])
  lane_results[lane]={'gate':gate,'counts':dict(collections.Counter(r['status'] for r in results)),'usable':[r['id'] for r in results if r['status']=='USABLE']}
  del data,cov,eligible,returns,profiles
 complete=lane_results['intraday']['gate']['complete']
 v.write(out,'summary.json',{'lanes':lane_results,'labels':v.LABELS,'complete':complete,'entryExitDevelopmentAllowed':complete,'entryExitStatus':'ELIGIBLE_FOR_SEPARATE_DEVELOPMENT_PRECOMMIT' if complete else 'NOT_STARTED_DICTIONARY_GATE_FAILED','commonHoldoutPayloadsRead':0,'existingSealedPayloadsRead':0,'rawPersisted':'PRECONDITION_SUCCESSFUL_ACQUISITION_ARTIFACTS','registryHash':p['registrySha256'],'splitHash':v.saved.sha(B/'04_session_split_manifest.json')})
 v.write(out,'manifest.json',{x.name:v.saved.sha(x) for x in sorted(out.iterdir()) if x.is_file()})
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--cache',required=True);a.add_argument('--output',required=True);x=a.parse_args();measure(x.cache,x.output)
