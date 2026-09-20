"""Precommitted chart-aware BUY/WAIT Development. No order routing or EXIT development."""
import argparse,collections,datetime as dt,hashlib,json,math,subprocess
from pathlib import Path
import numpy as np
from scripts import phase57_behavior_full144 as f
b=f.b;v=f.v;r=f.r;s=f.s
ROOT=f.ROOT;BASE=ROOT/'docs/evidence/phase57-chart-entry-v1'
read=f.read;write=f.write;sha=f.sha;digest=f.digest
ARMS={'E0':[],'E1':['RECENT'],'E2':['NOW'],'E3':['SEQ'],'E4':['WHO'],'E5':['RECENT','NOW','SEQ'],'E6':['WHO','RECENT','NOW','SEQ'],'E7':['WHO','RECENT','NOW','SEQ','ANALOG']}
CHANNELS=['O','H','L','C','range','body','upper','lower','volume','value','vwap','rvol','swing']

def verify():
 p=read(BASE/'protocol.json');assert sha(BASE/'protocol.json')==read(BASE/'protocol-lock.json')['sha256']
 for file,h in p['pins'].items():assert sha(ROOT/file)==h,file
 assert p['sessions']==s.admission.plan()['intradayDevelopment'] and len(p['sessions'])==144
 assert p['fit']+p['embargo1']+p['selection']+p['embargo2']+p['evaluation']==p['sessions']
 assert all(x is False for x in p['safety'].values());return p

def stamp(day,t):return day+'T%02d:%02d:00+09:00'%divmod(t,60)
def minute(st):return int(st[11:13])*60+int(st[14:16])
def clock(day,start):
 close=900 if day<'2024-11-05' else 925
 return [t for t in range(start,min(start+30,close-5)+1,5) if 545<=t<690 or 755<=t<close]

def causal_prefix(day,t,raw):
 close=900 if day<'2024-11-05' else 925
 return [x for x in raw if v.minute_time(x)<t and (540<=v.minute_time(x)<690 or 750<=v.minute_time(x)<close)]

def sequence(day,t,prefix,history,ref,origin):
 # Fixed wall-clock lags; lunch and missing slots remain null, never compressed or filled.
 assert all(x['Date']==day and v.minute_time(x)<t for x in prefix)
 valid=all(v.valid(x) for x in prefix);bars=v.bars5(day,prefix) if valid else []
 bm={x['t']:x for x in bars};out={};raw=[]
 for lag in range(12):
  at=t-lag*5;bar=bm.get(at);same=(at<=690 and t<=690) or (at>750 and t>750)
  if not same:bar=None
  vals={c:None for c in CHANNELS}
  if bar and ref and ref>0:
   raw.append(bar);o,h,l,c=bar['O'],bar['H'],bar['L'],bar['C'];den=ref
   vals.update({k:100*(bar[k]/den-1) for k in ['O','H','L','C']})
   vals.update(range=100*(h-l)/den,body=100*(c-o)/den,upper=100*(h-max(o,c))/den,lower=100*(min(o,c)-l)/den,volume=math.log1p(bar['Vo']),value=math.log1p(bar['Va']),swing=float(np.sign(c-o)))
   expected=list(range(540,min(at,690)))+(list(range(750,at)) if at>750 else [])
   times={v.minute_time(x) for x in prefix if v.minute_time(x)<at}
   if set(expected)<=times and bar['VWAP']:vals['vwap']=100*(c/bar['VWAP']-1)
   hv=[x.get('barVolumes',{}).get(at) for x in history[-10:]];hv=[x for x in hv if x and x>0]
   vals['rvol']=bar['Vo']/float(np.median(hv)) if len(hv)>=5 else None
  if bar:
   scale=v.scale(history);prev=history[-1].get('daily') if history else None
   sw=v.swings([z for z in bars if z['t']<=at],prev['C']*scale) if v.valid(prev) and scale else []
   vals['swing']=sw[-1]['direction'] if sw else None
  for k,val in vals.items():out[f'lag{lag:02d}_{k}']=val
 for window in [15,30,60]:
  bs=[bm.get(t-j*5) for j in range(window//5)]
  if t<=690:phase=t-window>=540
  else:phase=t-window>=750
  good=phase and all(bs)
  out[f'w{window}_return']=100*(bs[0]['C']/bs[-1]['O']-1) if good else None
  out[f'w{window}_range']=100*(max(x['H'] for x in bs)/min(x['L'] for x in bs)-1) if good else None
  out[f'w{window}_efficiency']=abs(bs[0]['C']-bs[-1]['O'])/max(sum(abs(x['C']-x['O']) for x in bs),1e-9) if good else None
 path=[x for x in prefix if v.valid(x) and v.minute_time(x)>=origin['minute']]
 out['since_selection_low']=100*(min(x['L'] for x in path)/origin['price']-1) if path else None
 out['since_selection_high']=100*(max(x['H'] for x in path)/origin['price']-1) if path else None
 return {'features':out,'rawClosed5m':sorted(raw,key=lambda x:x['t']),'status':'AVAILABLE' if bm.get(t) and valid else 'UNAVAILABLE'}

def structure(now,prefix):
 out={k:None for k in ['HH','HL','LH','LL','turning_up','turning_down','one_min_body','one_min_range','one_min_close']}
 reader=now['reader'];sw=reader.get('confirmedSwings',[])
 for sign,names in [(1,('HH','LH')),(-1,('HL','LL'))]:
  a=[x for x in sw if x['direction']==sign]
  if len(a)>=2:
   bars={x['t']:x for x in v.bars5(prefix[0]['Date'],prefix)} if prefix and all(v.valid(x) for x in prefix) else {}
   aa=bars.get(a[-1]['extremeAt']);bb=bars.get(a[-2]['extremeAt'])
   if aa and bb:out[names[0]]=float(aa['C']>bb['C']);out[names[1]]=float(aa['C']<bb['C'])
 if len(sw)>=2:out.update(turning_up=float(sw[-1]['direction']==1),turning_down=float(sw[-1]['direction']==-1))
 if prefix and v.valid(prefix[-1]) and v.minute_time(prefix[-1])+1==reader.get('asOfMinute'):
  x=prefix[-1];out.update(one_min_body=100*(x['C']/x['O']-1),one_min_range=100*(x['H']/x['L']-1),one_min_close=x['C'])
 return out

def outcome(day,t,raw,daily,origin):
 fill=next((x for x in raw if v.minute_time(x)==t and v.valid(x)),None)
 if not fill:return {'fillStatus':'UNAVAILABLE_NO_TRADE_AT_ORDER_MINUTE','price':None,'labels':None}
 price=fill['O']*1.0005
 m={'sessionDate':day,'decisionTimeJst':'%02d:%02d'%divmod(t,60),'decisionPrice':price}
 lab=f.labels_for_raw(m,raw,daily)
 for h in ['30','60','End']:
  if lab['return'+h] is not None:lab['return'+h]=(1+lab['return'+h]/100)*.9995*100-100
 future=[x for x in raw if v.valid(x) and v.minute_time(x)>=t]
 if lab['mfeEnd'] is not None:
  low=min(x['L'] for x in future);high=max(x['H'] for x in future)
  lab['timeToLow']=next(v.minute_time(x)-t for x in future if x['L']==low);lab['timeToHigh']=next(v.minute_time(x)-t for x in future if x['H']==high)
  lab['timeToRecovery']=next((v.minute_time(x)-t for x in future if x['H']>=price),None)
  lab['timeToUpside1']=next((v.minute_time(x)-t for x in future if x['H']>=price*1.01),None)
 return {'fillStatus':'OBSERVED_NEXT_MINUTE_OPEN_PLUS_5BPS','price':price,'improvementPct':100*(1-price/origin),'labels':lab}

def history_row(day,code,d,raw,hist):
 prev=hist[-1]['daily'] if hist else None
 row={'session':day,'daily':d,'tr':None,'Va':d.get('Va') if v.valid(d) else None,'C':d['C'] if v.valid(d) else None,'s':v.scale(hist),'ret':None}
 if v.valid(d) and v.valid(prev) and not v.action(d) and not v.action(prev):row.update(tr=max(d['H']-d['L'],abs(d['H']-prev['C']),abs(d['L']-prev['C']))/prev['C'],ret=d['C']/prev['C']-1)
 bars=v.bars5(day,raw) if all(v.valid(x) for x in raw) else [];row['barValues']={x['t']:x['Va'] for x in bars};row['barVolumes']={x['t']:x['Vo'] for x in bars};return row

def substrate(cache,prior,output):
 p=verify();out=Path(output);out.mkdir(parents=True,exist_ok=False);prior=Path(prior)
 assert read(prior/'manifest.json')==p['priorManifest']
 for name,h in read(prior/'manifest.json').items():assert sha(prior/name)==h
 old=read(prior/'features.json.gz');assert len(old)==7100
 pins={(x['session'],x['kind']):x['sha256'] for x in read(prior/'input-ledger.json')}
 byday=collections.defaultdict(list)
 for x in old:byday[x['member']['sessionDate']].append(x)
 codes={x['member']['symbol'] for x in old};history={};cal=s.calendar();last=None;allrows=[];opps=[];labels={};inventory=[];lineage=[];currentlogs=[]
 for day in p['sessions']:
  prev=cal[cal.index(day)-1]
  if last!=prev:history={}
  def pages(kind):
   s.admission.authorize(day,kind);file=Path(cache)/day/(kind+'-pages.json');assert sha(file)==pins[day,kind]
   data,_=v.saved.pages(file);assert all(x['Date']==day for x in data);lineage.append({'session':day,'kind':kind,'sha256':sha(file)});return data
  by=collections.defaultdict(list)
  for x in pages('minute'):
   if x['Code'] in codes:by[x['Code']].append(x)
  for code in by:by[code].sort(key=v.minute_time)
  members=sorted(byday[day],key=lambda x:x['member']['selectorEventId']);ms=[x['member'] for x in members]
  adapter={'projected':{},'missing':{},'currentOpportunities':[],'currentTicks':[]}
  if ms:
   tmp=out/'adapter-input.json';dest=out/'adapter-output.json';write(tmp,ms)
   subprocess.run(['node','--max-old-space-size=4096','scripts/phase57_chart_entry_adapter.mjs',str(cache),day,prev if prev in p['sessions'] else 'UNAVAILABLE',str(tmp),str(dest)],check=True)
   adapter=read(dest);tmp.unlink();dest.unlink()
  current={x['stateSymbol']:x for x in adapter['currentOpportunities']};currentlogs.extend(adapter['currentTicks'])
  first={}
  for row in members:first.setdefault(row['member']['symbol'],row)
  today=[];opday=[]
  for code,orig in sorted(first.items()):
   m=orig['member'];start=minute(m['decisionTimestamp']);oid=day+'|'+code;hist=history.get(code,[]);previous=hist[-1]['daily'] if hist else None
   who=orig['WHO'];assert all(r.timestamp(c['computedThrough'])<r.timestamp(m['decisionTimestamp']) for c in who)
   source=adapter['projected'].get(m['selectorEventId']);cf=current[code];ct=None
   if cf['firstPassTimestamp']:ct=minute((r.timestamp(cf['firstPassTimestamp']).astimezone(dt.timezone(dt.timedelta(hours=9)))).isoformat())
   opportunity={'id':oid,'session':day,'symbol':code,'origin':m,'WHO':who,'selectorFeatures':source,'selectorFeatureReason':adapter['missing'].get(m['selectorEventId']),'current':cf,'currentMinute':ct,'stateContract':'FIRST_SYMBOL_SESSION_NO_REENTRY_KEEP_WATCHING_AFTER_DESELECTION','grid':clock(day,start)}
   opps.append(opportunity);opday.append(opportunity)
   # CURRENT may pass later than the NEW bounded wait grid; build same-price evaluator row for it.
   times=sorted(set(clock(day,start)+([ct] if ct is not None else [])))
   for t in times:
    prefix=causal_prefix(day,t,by[code]);refs=[x for x in prefix if v.valid(x)]
    ref=refs[-1]['C'] if refs and 0<=t-(v.minute_time(refs[-1])+1)<=5 else None
    recent=b.recent_context(day,ref or m['decisionPrice'],prefix,hist,cal);now=b.now_context(day,t,prefix,previous,hist,cal)
    if ref is None:
     for k in ['position_high','position_low','position_close']:recent['features'][k]=None
    seq=sequence(day,t,prefix,hist,ref,{'minute':start,'price':m['decisionPrice']});now['features'].update(structure(now,prefix))
    assert recent['computedThrough'] is None or r.timestamp(recent['computedThrough'])<r.timestamp(stamp(day,t))
    info={'score':m['savedV1Score'],'rank':m['newEligibleRank'],'referencePrice':ref,'originalPrice':m['decisionPrice'],'elapsed':t-start,'remaining':(900 if day<'2024-11-05' else 930)-t,'moveSinceSelection':100*(ref/m['decisionPrice']-1) if ref else None,'timeFraction':(t-540)/390}
    if source:info.update({'frozen_'+k:val for k,val in source['features'].items()})
    row={'id':oid+'|'+str(t),'opportunity':oid,'session':day,'symbol':code,'minute':t,'decisionTime':stamp(day,t),'newEligibleTick':t in opportunity['grid'],'quoteAvailable':ref is not None,'SELECTOR':info,'WHO':who,'RECENT':recent,'NOW':now,'SEQ':seq}
    today.append(row)
  # Source daily data is evaluator-only at this point, then history for subsequent days.
  dc={x['Code']:x for x in pages('daily')};master=pages('master');uni={x['Code'] for x in master if str(x.get('Mkt')) in ['0111','0112','0113'] and str(x.get('ProdCat'))=='011'}
  for row in today:labels[row['id']]=outcome(day,row['minute'],by[row['symbol']],dc.get(row['symbol']),row['SELECTOR']['originalPrice'])
  for o in opday:
   raw=by[o['symbol']];lab=f.labels_for_raw(o['origin'],raw,dc.get(o['symbol']));o['selectorOutcome']=lab
   future=[x for x in raw if v.valid(x) and v.minute_time(x)>=minute(o['origin']['decisionTimestamp'])]
   if lab['mfeEnd'] is not None and future:
    lo=min(x['L'] for x in future);hi=max(x['H'] for x in future);st=minute(o['origin']['decisionTimestamp'])
    o['anatomy']={'timeToLow':next(v.minute_time(x)-st for x in future if x['L']==lo),'timeToHigh':next(v.minute_time(x)-st for x in future if x['H']==hi),'oracleLowPriceImprovementPct':100*(1-lo/o['origin']['decisionPrice']),'oracleOnly':True}
  for code in codes:
   hist=history.get(code,[]);history[code]=(hist+[history_row(day,code,dc.get(code) if code in uni else None,by[code],hist)])[-10:]
  allrows.extend(today);last=day
  inv={'session':day,'inputAudited':True,'selectorCandidates':len(ms),'opportunities':len(opday),'decisionRows':len(today),'reason':None if ms else 'EXACT_PREVIOUS_SESSION_OUTSIDE_AUTHORIZED_CACHE','WHOavailable':sum(any(c['availability']=='AVAILABLE' for c in x['WHO']) for x in today),'RECENTavailable':sum(x['RECENT']['status']=='AVAILABLE' for x in today),'NOWavailable':sum(x['NOW']['status']=='RESEARCH_CONTEXT_AVAILABLE' for x in today),'SEQavailable':sum(x['SEQ']['status']=='AVAILABLE' for x in today)}
  inventory.append(inv);print(json.dumps(inv),flush=True)
 # Store features and labels separately; no oracle or realized fill in the feature projection.
 write(out/'features.json.gz',allrows);write(out/'outcomes.json.gz',labels);write(out/'opportunities.json.gz',opps);write(out/'current-ticks.json.gz',currentlogs);write(out/'inventory.json',inventory);write(out/'input-ledger.json',lineage)
 write(out/'audit.json',{'all144':len(inventory)==144,'candidateIdentityHash':digest([x['member'] for x in old]),'candidateCount':len(old),'WHOpriorOnly':True,'RECENTpreviousDay':True,'NOWclosedBars':True,'sequenceFixedLagsNoFill':True,'newAcquisition':0,'commonHoldoutOpened':0,'sealedOpened':0,'safety':b.SAFETY,'upstreamLimitation':'Inherited Frozen admission uses same-date Daily metadata. Not independently prospective PIT or OOS.'})
 write(out/'manifest.json',{x.name:sha(x) for x in sorted(out.iterdir())})

def vector(row,families):
 out={'SELECTOR/'+k:val for k,val in row['SELECTOR'].items()}
 out.update(b.feature_vector(row,[x for x in families if x in ['WHO','RECENT','NOW']]))
 if 'NOW' in families:out.update({'NOW/'+k:val for k,val in row['NOW']['features'].items()})
 if 'SEQ' in families:out.update({'SEQ/'+k:val for k,val in row['SEQ']['features'].items()})
 if 'ANALOG' in families:out.update({'ANALOG/'+k:val for k,val in row['ANALOG'].items() if k not in ['neighbors','maxRealizedThrough']})
 return out

def utility(lab,delay):
 if not lab or any(lab.get(k) is None for k in ['return30','mae30','mfeEnd','maeEnd']):return None
 return lab['return30']+.2*min(lab['mfeEnd'],10)+.3*lab['mae30']+.1*lab['maeEnd']-.002*delay

def target_rows(rows,labels,opps):
 target={};by={o['id']:o for o in opps};mapping={x['id']:x for x in rows}
 for x in rows:
  if not x['newEligibleTick']:continue
  nxt=x['minute']+5;k=x['opportunity']+'|'+str(nxt)
  if k not in mapping or not mapping[k]['newEligibleTick']:continue
  u=utility(labels[x['id']]['labels'],x['SELECTOR']['elapsed']);w=utility(labels[k]['labels'],mapping[k]['SELECTOR']['elapsed'])
  if u is not None and w is not None:target[x['id']]=u-w
 return target

def analog_signature(x):
 q=x['SEQ']['features'];n=x['NOW']['features'];recent=x['RECENT']['features']
 values=[q.get('w15_return'),q.get('w30_return'),q.get('w60_return'),q.get('w30_range'),q.get('lag00_vwap'),q.get('lag00_rvol'),recent.get('trend5'),n.get('swing_direction')]
 values=[None if y is None else float(np.clip(y,-20,20))/5 for y in values]
 values += [x['SELECTOR']['timeFraction'],sum(c['availability']=='AVAILABLE' for c in x['WHO'])/9]
 return np.array([0 if z is None else z for z in values]+[float(z is None) for z in values])

def add_analog(rows,labels,opps):
 # One initial case per opportunity, prior session only: each label is fully realized before query.
 by=collections.defaultdict(list)
 for x in rows:by[x['session']].append(x)
 origins={o['id']:minute(o['origin']['decisionTimestamp']) for o in opps};pool=[];audit=[]
 for day,group in sorted(by.items()):
  pool=pool[-10000:];pm=np.array([a['signature'] for a in pool])
  maxthrough=max((a['realizedThrough'] for a in pool),default=None)
  for x in group:
   a={'count':0,'distanceMean':None,'returnMean':None,'returnMedian':None,'maeMean':None,'mfeMean':None,'recoveryProbability':None,'timeToRecovery':None,'timeToUpside':None,'uncertainty':None,'maxRealizedThrough':maxthrough,'neighbors':[]}
   if pool:
    assert maxthrough<x['decisionTime']
    dist=np.sqrt(np.mean((pm-analog_signature(x))**2,axis=1));ix=np.argsort(dist,kind='stable')[:20];near=[pool[i] for i in ix];ls=[z['label'] for z in near]
    if len(ls)>=5:
     a.update(count=len(ls),distanceMean=float(np.mean(dist[ix])),returnMean=float(np.mean([z['return30'] for z in ls])),returnMedian=float(np.median([z['return30'] for z in ls])),maeMean=float(np.mean([z['mae30'] for z in ls])),mfeMean=float(np.mean([z['mfeEnd'] for z in ls])),recoveryProbability=float(np.mean([z.get('timeToRecovery') is not None for z in ls])),uncertainty=float(np.std([z['return30'] for z in ls])/math.sqrt(len(ls))),neighbors=[z['id'] for z in near])
     for dst,src in [('timeToRecovery','timeToRecovery'),('timeToUpside','timeToUpside1')]:
      vs=[z[src] for z in ls if z.get(src) is not None];a[dst]=float(np.median(vs)) if vs else None
   x['ANALOG']=a
  # Add only after all queries of the session, never own/same-session future case.
  for x in group:
   if x['minute']!=origins[x['opportunity']]:continue
   lab=labels[x['id']]['labels']
   if utility(lab,0) is not None:pool.append({'id':x['id'],'signature':analog_signature(x),'label':lab,'realizedThrough':stamp(day,931 if day>='2024-11-05' else 901)})
  audit.append({'session':day,'queries':len(group),'covered':sum(x['ANALOG']['count']>=5 for x in group),'poolAfterSession':len(pool),'maxRealizedThroughUsed':maxthrough})
 return audit

def fit_model(train,query,y,family):
 from sklearn.ensemble import HistGradientBoostingRegressor
 names=sorted(set().union(*(x.keys() for x in train)))
 def array(xs):return np.array([[z.get(k) if z.get(k) is not None else np.nan for k in names] for z in xs],float)
 a=array(train);q=array(query);med=np.array([np.median(a[np.isfinite(a[:,i]),i]) if np.isfinite(a[:,i]).any() else 0 for i in range(len(names))]);missing=~np.isfinite(a);qm=~np.isfinite(q)
 a=np.where(missing,med,a);q=np.where(qm,med,q);mu=a.mean(0);sd=a.std(0);sd[sd<1e-8]=1
 a=np.column_stack([(a-mu)/sd,missing]);q=np.column_stack([(q-mu)/sd,qm]);model={'family':family,'names':names,'median':med.tolist(),'mean':mu.tolist(),'scale':sd.tolist(),'n':len(train),'allMissing':[names[i] for i in range(len(names)) if missing[:,i].all()]}
 if family=='RIDGE':
  ym=float(np.mean(y));center=a.mean(0);a-=center;q-=center;weights=np.linalg.solve(a.T@a+10*np.eye(a.shape[1]),a.T@(np.array(y)-ym));pred=q@weights+ym
  model.update(weights=weights.tolist(),intercept=ym,designCenter=center.tolist());importance=sorted(zip(names+['MISSING/'+n for n in names],abs(weights).tolist()),key=lambda z:(-z[1],z[0]))
 else:
  fit=HistGradientBoostingRegressor(max_iter=80,max_leaf_nodes=7,min_samples_leaf=50,l2_regularization=10,learning_rate=.05,early_stopping=False,random_state=570920).fit(a,y)
  pred=fit.predict(q)
  # Deterministic training loss sensitivity by family, not used for feature/model selection.
  base=float(np.mean((fit.predict(a)-y)**2));importance=[]
  for prefix in ['SELECTOR','RECENT','NOW','SEQ','WHO','ANALOG']:
   ii=[i for i,n in enumerate(names) if n.startswith(prefix+'/')];test=a.copy();test[:,ii]=test[::-1,ii];importance.append((prefix,float(np.mean((fit.predict(test)-y)**2)-base)))
  model['treeStateHash']=digest([{'nodes':tree.nodes.tolist()} for stage in fit._predictors for tree in stage])
 model['importance']=importance[:30];return pred,model

def policy(opps,rows,labels,scores,mode):
 mapping={x['id']:x for x in rows};result=[]
 for o in opps:
  start=minute(o['origin']['decisionTimestamp']);chosen=None;attempts=[];reason='EXPIRED_NO_CAUSAL_FILL'
  if mode=='CURRENT':times=[o['currentMinute']] if o['currentMinute'] is not None else []
  elif mode.startswith('WAIT_'):times=[start+int(mode.split('_')[1])] if start+int(mode.split('_')[1]) in o['grid'] else []
  elif mode=='IMMEDIATE':times=[start] if start in o['grid'] else []
  else:times=o['grid']
  for t in times:
   key=o['id']+'|'+str(t);x=mapping.get(key)
   if not x:continue
   buy=mode in ['CURRENT','IMMEDIATE'] or mode.startswith('WAIT_') or t==o['grid'][-1] or scores.get(key,0)>=0
   if not x['quoteAvailable']:attempts.append({'minute':t,'action':'WAIT','reason':'STALE_OR_MISSING_REFERENCE'});continue
   if not buy:attempts.append({'minute':t,'action':'WAIT','reason':'LEARNED_NEXT_STEP_ADVANTAGE'});continue
   if labels[key]['price'] is None:attempts.append({'minute':t,'action':'WAIT','reason':'BUY_ORDER_UNFILLED_NO_SOURCE_TRADE'});continue
   chosen=key;reason='BUY';attempts.append({'minute':t,'action':'BUY','reason':'CURRENT_FROZEN' if mode=='CURRENT' else 'DEADLINE' if mode not in ['IMMEDIATE'] and not mode.startswith('WAIT_') and t==o['grid'][-1] else mode});break
  result.append({'opportunity':o['id'],'session':o['session'],'symbol':o['symbol'],'entryId':chosen,'status':reason,'delay':mapping[chosen]['minute']-start if chosen else None,'attempts':attempts})
 return result

def stats(xs):return b.dist(xs)
def metrics(opps,trades,labels):
 by={o['id']:o for o in opps};entered=[x for x in trades if x['entryId']];n=len(opps);sessions=len({o['session'] for o in opps})
 out={'opportunities':n,'enterCount':len(entered),'enterPerSession':len(entered)/sessions if sessions else None,'noEntryPct':100*(1-len(entered)/n) if n else None,'waitMinutes':stats(x['delay'] for x in entered),'entryImprovement':stats(labels[x['entryId']]['improvementPct'] for x in entered),'capture':{}}
 for key in ['mae30','mae60','maeEnd','mfeEnd','return30','returnEnd']:
  out[key]=stats((labels[x['entryId']]['labels'] or {}).get(key) for x in entered)
 for t in [1,2,3,5]:
  winners={o['id'] for o in opps if o['selectorOutcome']['mfeEnd'] is not None and o['selectorOutcome']['mfeEnd']>=t};hit=[];missing=[]
  for tr in trades:
   if tr['opportunity'] not in winners:continue
   lab=labels[tr['entryId']]['labels'] if tr['entryId'] else None
   if tr['entryId'] and (not lab or lab['mfeEnd'] is None):missing.append(tr['opportunity'])
   if lab and lab['mfeEnd'] is not None and lab['mfeEnd']>=t:hit.append(tr['opportunity'])
  out['capture'][str(t)]={'baselineWinners':len(winners),'captured':len(hit),'unknownEntered':len(missing),'pct':100*len(hit)/len(winners) if winners else None,'missedOrUnknownPct':100*(1-len(hit)/len(winners)) if winners else None}
  if t in [3,5]:
   lw={o['id'] for o in opps if o['id'] in winners and o['selectorOutcome']['order']=='LOW_THEN_HIGH'};out['capture'][str(t)]['lowThenHighPct']=100*len(lw&set(hit))/len(lw) if lw else None
 vals=[labels[x['entryId']]['labels']['mae30'] for x in entered if labels[x['entryId']]['labels'] and labels[x['entryId']]['labels']['mae30'] is not None]
 out['downsideRates']={str(t):100*float(np.mean(np.array(vals)<=-t)) if vals else None for t in [1,2,3]}
 returns=[labels[x['entryId']]['labels']['return30'] for x in entered if labels[x['entryId']]['labels'] and labels[x['entryId']]['labels']['return30'] is not None];out['positive30Pct']=100*float(np.mean(np.array(returns)>0)) if returns else None
 us=[utility(labels[x['entryId']]['labels'],x['delay']) for x in entered];out['utility']=stats(us)
 # Fixed population denominator; absent entry/unknown utility gets zero, and +3/+5 missed winners penalized.
 out['populationObjective']=sum(z for z in us if z is not None)/max(1,n)-sum(.5*(out['capture'][str(t)]['baselineWinners']-out['capture'][str(t)]['captured'])/max(1,n) for t in [3,5])
 out['symbolConcentration']=collections.Counter(x['symbol'] for x in entered).most_common(10)
 return out

def paired(opps,a,c,labels):
 aa={x['opportunity']:x for x in a};cc={x['opportunity']:x for x in c};daily=collections.defaultdict(list);detail=[]
 for o in opps:
  x=aa[o['id']];z=cc[o['id']]
  if not x['entryId'] or not z['entryId']:continue
  la=labels[x['entryId']]['labels'];lc=labels[z['entryId']]['labels']
  if not la or not lc or la['mae30'] is None or lc['mae30'] is None:continue
  d=la['mae30']-lc['mae30'];daily[o['session']].append(d);detail.append({'opportunity':o['id'],'maeImprovementPp':d,'priceImprovementPp':labels[x['entryId']]['improvementPct']-labels[z['entryId']]['improvementPct']})
 xs=np.array([np.mean(x) for _,x in sorted(daily.items())]);rng=np.random.default_rng(570920);boot=[]
 if len(xs):
  for _ in range(1000):
   starts=rng.integers(0,len(xs),size=math.ceil(len(xs)/5));ix=[(s+j)%len(xs) for s in starts for j in range(5)][:len(xs)];boot.append(float(np.mean(xs[ix])))
 return {'pairedN':len(detail),'sessions':len(xs),'meanSessionMAEImprovementPp':float(np.mean(xs)) if len(xs) else None,'block5CI95':np.quantile(boot,[.025,.975]).tolist() if boot else None,'positiveSessionsPct':100*float(np.mean(xs>0)) if len(xs) else None,'pairedPriceImprovementMeanPp':float(np.mean([x['priceImprovementPp'] for x in detail])) if detail else None,'selectionBiasWarning':'Paired entrants only; read with fixed-population capture, throughput and missing-outcome counts. Descriptive reused Development.'}

def measure(substrate_dir,output):
 p=verify();src=Path(substrate_dir);out=Path(output);out.mkdir(parents=True,exist_ok=False)
 for name,h in read(src/'manifest.json').items():assert sha(src/name)==h
 rows=read(src/'features.json.gz');labels=read(src/'outcomes.json.gz');opps=read(src/'opportunities.json.gz');targets=target_rows(rows,labels,opps)
 pre_anatomy={}
 for split,dates in [('fit',p['fit']),('selection',p['selection']),('evaluation',p['evaluation'])]:
  os=[o for o in opps if o['session'] in dates];pre_anatomy[split]={'order':dict(collections.Counter(o['selectorOutcome']['order'] for o in os)),'oracleOnly':True,'fixedWait':{mode:metrics(os,policy(os,rows,labels,{},mode),labels) for mode in ['IMMEDIATE','WAIT_5','WAIT_10','WAIT_15','WAIT_30']}}
 write(out/'pretraining-anatomy.json',pre_anatomy)
 analog=add_analog(rows,labels,opps);train=[x for x in rows if x['session'] in p['fit'] and x['id'] in targets];assert len(train)>=100
 query=[x for x in rows if x['session'] in p['selection']+p['evaluation']];selection=[o for o in opps if o['session'] in p['selection']];ev=[o for o in opps if o['session'] in p['evaluation']]
 models={};scores={};selectionMetrics={};chosen={};alltrades={};result={};effects={}
 for arm,families in ARMS.items():
  tr=[vector(x,families) for x in train];qr=[vector(x,families) for x in query]
  for family in ['RIDGE','TREE']:
   key=arm+'_'+family;pred,model=fit_model(tr,qr,[targets[x['id']] for x in train],family);models[key]=model;scores[key]={x['id']:float(y) for x,y in zip(query,pred)}
   trades=policy(selection,query,labels,scores[key],key);selectionMetrics[key]=metrics(selection,trades,labels)
  def choice(family):
   x=selectionMetrics[arm+'_'+family];good=all((x['capture'][str(t)]['pct'] or 0)>=90 for t in [3,5]) and (100-(x['noEntryPct'] or 0))>=90
   return (good,x['populationObjective'],family=='RIDGE')
  chosen[arm]=arm+'_'+max(['RIDGE','TREE'],key=choice)
  print(json.dumps({'trainedArm':arm,'trainN':len(train),'selectionChosen':chosen[arm]}),flush=True)
 # Persist family choices before any evaluation summary is computed; no refit or evaluation winner selection.
 write(out/'selection-lock.json',{'chosen':chosen,'selectionMetrics':selectionMetrics,'fitThrough':p['fit'][-1],'selectionThrough':p['selection'][-1],'evaluationNotUsedForSelection':True})
 for mode in ['IMMEDIATE','CURRENT','WAIT_5','WAIT_10','WAIT_15','WAIT_30']+list(ARMS):
  trades=policy(ev,query,labels,scores.get(chosen.get(mode,''),{}),mode);alltrades[mode]=trades;result[mode]=metrics(ev,trades,labels)
 for arm in ARMS:
  effects[arm]={'vsImmediate':paired(ev,alltrades[arm],alltrades['IMMEDIATE'],labels),'vsCurrent':paired(ev,alltrades[arm],alltrades['CURRENT'],labels)}
 for a,c in [('E1','E0'),('E2','E0'),('E3','E0'),('E4','E0'),('E5','E2'),('E6','E5'),('E7','E6')]:effects[a]['vs'+c]=paired(ev,alltrades[a],alltrades[c],labels)
 decisions={}
 for arm in ARMS:
  met=result[arm];effect=effects[arm]['vsImmediate'];ci=effect['block5CI95'];cap=all((met['capture'][str(t)]['pct'] or 0)>=90 for t in [3,5]);through=met['enterCount']>=.9*result['IMMEDIATE']['enterCount']
  good=cap and through and ci and ci[0]>0 and (effect['meanSessionMAEImprovementPp'] or 0)>=.1 and (effect['pairedPriceImprovementMeanPp'] or 0)>0
  decisions[arm]={'status':'NEW_ENTRY_REDUCES_DOWNSIDE_WITH_ACCEPTABLE_OPPORTUNITY_PRESERVATION' if good else 'NO_MEANINGFUL_ENTRY_IMPROVEMENT','preservationPass':cap,'throughputPass':through,'timingValuePass':bool(good),'automaticPromotionAllowed':False}
 missed={}
 for arm,ts in alltrades.items():
  om={o['id']:o for o in ev};counts=collections.Counter()
  for tr in ts:
   o=om[tr['opportunity']]
   for t in [3,5]:
    if o['selectorOutcome']['mfeEnd'] is None or o['selectorOutcome']['mfeEnd']<t:continue
    lab=labels[tr['entryId']]['labels'] if tr['entryId'] else None
    reason='NO_ENTRY' if not tr['entryId'] else 'OUTCOME_UNAVAILABLE' if not lab or lab['mfeEnd'] is None else 'CAPTURED' if lab['mfeEnd']>=t else 'UPSIDE_LOST_BEFORE_OR_BY_ENTRY_PRICE'
    counts[str(t)+'/'+o['selectorOutcome']['order']+'/'+reason]+=1
  missed[arm]=dict(counts)
 write(out/'missed-winners.json',missed)
 decisions['WHO']={'status':'DICTIONARY_ENTRY_VALUE_INCONCLUSIVE','reason':'No formally usable trait values in causal cohort. State information is separate.'}
 session=[]
 for day in p['evaluation']:
  os=[o for o in ev if o['session']==day]
  for arm,trades in alltrades.items():session.append({'session':day,'arm':arm,**metrics(os,[t for t in trades if t['session']==day],labels)})
 anatomy={}
 for split,dates in [('fit',p['fit']),('selection',p['selection']),('evaluation',p['evaluation'])]:
  os=[o for o in opps if o['session'] in dates];anatomy[split]={'opportunities':len(os),'order':dict(collections.Counter(o['selectorOutcome']['order'] for o in os)),'selectionToLow':stats(o['selectorOutcome']['maeEnd'] for o in os),'selectionToHigh':stats(o['selectorOutcome']['mfeEnd'] for o in os),'timeToLow':stats(o.get('anatomy',{}).get('timeToLow') for o in os),'timeToHigh':stats(o.get('anatomy',{}).get('timeToHigh') for o in os),'oracleLowPriceImprovement':stats(o.get('anatomy',{}).get('oracleLowPriceImprovementPct') for o in os),'oracleNotTradable':True}
 # Deterministic examples: highest hash in success/failure class; no handpicked flattering chart.
 examples=[]
 for name,want in [('success',True),('failure',False)]:
  ts=[x for x in alltrades['E7'] if x['entryId'] and ((labels[x['entryId']]['improvementPct']>0)==want)]
  for tr in sorted(ts,key=lambda x:hashlib.sha256(x['opportunity'].encode()).hexdigest())[:2]:
   trace=[x for x in query if x['opportunity']==tr['opportunity'] and x['newEligibleTick']];examples.append({'category':name,'trade':tr,'decisionFrames':[{'time':x['decisionTime'],'rawClosed5m':x['SEQ']['rawClosed5m']} for x in trace],'outcomeSeparate':labels[tr['entryId']]})
 coverage={'evalRows':len([x for x in query if x['session'] in p['evaluation']]),'WHOusableRows':sum(any(c['availability']=='AVAILABLE' for c in x['WHO']) for x in query if x['session'] in p['evaluation']),'WHOstates':dict(collections.Counter(c['sampleConfidence']+'/'+c['temporalReliability'] for x in query if x['session'] in p['evaluation'] for c in x['WHO'])),'analog':analog}
 for name,data in [('metrics.json',result),('decisions.json',decisions),('effects.json',effects),('anatomy.json',anatomy),('session-metrics.json',session),('models.json',models),('coverage.json',coverage),('examples.json',examples),('trades.json.gz',alltrades),('analog-ledger.json.gz',[{'id':x['id'],**x['ANALOG']} for x in rows]),('score-ledger.json.gz',scores),('training-targets.json.gz',targets)]:write(out/name,data)
 write(out/'audit.json',{'fitRows':len(train),'selectionOpportunities':len(selection),'evaluationOpportunities':len(ev),'fitSessions':p['fit'],'selectionSessions':p['selection'],'evaluationSessions':p['evaluation'],'analogFullyRealizedPriorSessionOnly':True,'targetNotFeature':True,'precommittedModelFamilies':True,'all144Input':True,'commonHoldoutOpened':0,'sealedOpened':0,'safety':b.SAFETY,'independentOOS':False})
 write(out/'manifest.json',{x.name:sha(x) for x in sorted(out.iterdir())})

def main():
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['verify','substrate','measure']);parser.add_argument('--cache');parser.add_argument('--prior');parser.add_argument('--substrate');parser.add_argument('--output');a=parser.parse_args()
 if a.command=='verify':print(json.dumps({'verified':verify()['id']}))
 elif a.command=='substrate':substrate(a.cache,a.prior,a.output)
 else:measure(a.substrate,a.output)
if __name__=='__main__':main()
