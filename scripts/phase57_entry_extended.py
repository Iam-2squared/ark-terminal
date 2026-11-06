"""Evaluation only. Reads frozen trades; never invokes a policy, inference or fit."""
import argparse, collections, csv, json, math
from pathlib import Path
import numpy as np
from scripts import phase57_behavior_full144 as f
read,write,sha=f.read,f.write,f.sha
ROOT=f.ROOT
BASE=ROOT/'docs/evidence/phase57-entry-extended-v1'
ARMS=['IMMEDIATE','CURRENT']+[f'E{i}' for i in range(8)]
LEVELS=list(range(1,6))

def verify():
 p=read(BASE/'protocol.json')
 assert sha(BASE/'protocol.json')==read(BASE/'protocol-lock.json')['sha256']
 for name,h in p['pins'].items():assert sha(ROOT/name)==h,name
 old=read(ROOT/'docs/evidence/phase57-chart-entry-v1/protocol.json')
 for name,h in old['pins'].items():assert sha(ROOT/name)==h,name
 assert p['sessions']==f.s.admission.plan()['intradayDevelopment'] and len(p['sessions'])==144
 assert all(x is False for x in p['safety'].values())
 return p

def distribution(vals):
 xs=np.array([x for x in vals if x is not None],float)
 out={'count':len(xs),'mean':None,'median':None,'worstObserved':None,'positiveRate':None}
 for q in [5,25,75,90,95]:out['p'+str(q)]=None
 if len(xs):
  out.update(mean=float(xs.mean()),median=float(np.median(xs)),worstObserved=float(xs.min()),positiveRate=float(100*np.mean(xs>0)))
  for q in [5,25,75,90,95]:out['p'+str(q)]=float(np.percentile(xs,q))
 return out

def drawdown_bounds(price,rows):
 """Confirmed chronological drawdown and adverse OHLC-order bound, both <=0.
 Prior peak -> current low, open -> low and high -> close have known ordering.
 Current high -> current low ordering is unknown; only adverse bound includes it.
 """
 peak=price;confirmed=adverse=0.
 for x in rows:
  confirmed=min(confirmed,100*(x['L']/max(peak,x['O'])-1),100*(x['C']/x['H']-1))
  peak=max(peak,x['H']);adverse=min(adverse,100*(x['L']/peak-1))
 return confirmed,adverse

def horizon(day,start,price,raw,h,legacy):
 assert h in [30,60] and price>0
 assert all(x['Date']==day for x in raw),'CROSS_SESSION_SOURCE'
 close=900 if day<'2024-11-05' else 930;continuous=900 if close==900 else 925
 end=start+h;boundary=690 if start<690 else close;stop=min(end,boundary)
 # Identical strict horizon source selection to frozen labels; truncate censored paths at first session boundary.
 valid=sorted([x for x in raw if f.v.valid(x)],key=f.v.minute_time)
 assert len({f.v.minute_time(x) for x in valid})==len(valid),'DUPLICATE_SOURCE'
 rows=[x for x in valid if (f.v.minute_time(x)>start if f.v.minute_time(x) in [690,close] else f.v.minute_time(x)>=start) and (f.v.minute_time(x)<=stop if f.v.minute_time(x) in [690,close] else f.v.minute_time(x)<stop) and (540<=f.v.minute_time(x)<690 or 750<=f.v.minute_time(x)<continuous or f.v.minute_time(x) in [690,close])]
 reason=legacy['reason'+str(h)]
 status='COMPLETE' if reason is None else 'CENSORED' if reason=='LUNCH_OR_SESSION_BOUNDARY' else 'UNAVAILABLE'
 observedMFE=max(0,max((100*(x['H']/price-1) for x in rows),default=0)) if rows else None
 result={'horizon':h,'status':status,'reason':reason,'pathAvailable':bool(rows),'observedRows':len(rows),'observedThroughMinute':f.v.minute_time(rows[-1]) if rows else None,'observedMFE':observedMFE,'MFE':None,'MAE':None,'MaxDD':None,'MaxDDAdverseBound':None,'returnNet':None,'returnGross':None,'givebackNetPp':None}
 if status=='COMPLETE':
  assert rows
  mfe=observedMFE;mae=min(0,min(100*(x['L']/price-1) for x in rows));ret=100*(rows[-1]['C']/price-1)
  assert math.isclose(mae,legacy['mae'+str(h)],abs_tol=1e-10)
  assert math.isclose(mfe,legacy['mfe'+str(h)],abs_tol=1e-10)
  dd,adverse=drawdown_bounds(price,rows)
  net=(1+ret/100)*.9995*100-100
  result.update(MFE=mfe,MAE=mae,MaxDD=dd,MaxDDAdverseBound=adverse,returnGross=ret,returnNet=net,givebackNetPp=mfe-net)
 return result

def hit_rates(rows):
 out={};den=len(rows)
 for t in LEVELS:
  hit=sum(x['observedMFE'] is not None and x['observedMFE']>=t for x in rows)
  unknown=sum(x['status']!='COMPLETE' and (x['observedMFE'] is None or x['observedMFE']<t) for x in rows)
  complete=[x for x in rows if x['status']=='COMPLETE'];ch=sum(x['MFE']>=t for x in complete)
  out[str(t)]={'buyDenominator':den,'observedHits':hit,'confirmedMisses':den-hit-unknown,'unknown':unknown,'rate':100*hit/den if den else None,'upperBoundRate':100*(hit+unknown)/den if den else None,'completeDenominator':len(complete),'completeHits':ch,'completeOnlyRate':100*ch/len(complete) if complete else None}
 return out

def capture(opps,trades,labels):
 out={}
 for t in LEVELS:
  winners={o['id'] for o in opps if o['selectorOutcome']['mfeEnd'] is not None and o['selectorOutcome']['mfeEnd']>=t}
  counts=collections.Counter()
  for tr in trades:
   if tr['opportunity'] not in winners:continue
   if not tr['entryId']:counts['noEntry']+=1;continue
   lab=labels[tr['entryId']]['labels']
   if not lab or lab['mfeEnd'] is None:counts['unknownEntered']+=1
   elif lab['mfeEnd']>=t:counts['captured']+=1
   else:counts['belowThreshold']+=1
  n=len(winners);hit=counts['captured']
  assert sum(counts.values())==n
  out[str(t)]={'selectorWinnerDenominator':n,'captured':hit,'missed':n-hit,'rate':100*hit/n if n else None,**{k:counts[k] for k in ['noEntry','unknownEntered','belowThreshold']}}
 return out

def same(a,b):return a is b if a is None or b is None else math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-10)

def measure(cache,prior,output):
 p=verify();src=Path(prior);out=Path(output);out.mkdir(parents=True,exist_ok=False)
 for folder,pins in p['priorManifests'].items():
  assert read(src/folder/'manifest.json')==pins
  for name,h in pins.items():assert sha(src/folder/name)==h,(folder,name)
 trades=read(src/'measurement/trades.json.gz');labels=read(src/'substrate/outcomes.json.gz');opps=read(src/'substrate/opportunities.json.gz');old=read(src/'measurement/metrics.json')
 ev=[o for o in opps if o['session'] in p['evaluation']];ids={o['id'] for o in ev};assert len(ids)==2155
 entries={t['entryId']:t for a in ARMS for t in trades[a] if t['entryId']}
 assert all({t['opportunity'] for t in trades[a]}==ids and len(trades[a])==len(ids) for a in ARMS)
 pins={(x['session'],x['kind']):x['sha256'] for x in read(src/'substrate/input-ledger.json')};ledger=[];records={};checks=[]
 for day in p['sessions']:
  for kind in ['minute','daily','master']:
   f.s.admission.authorize(day,kind);path=Path(cache)/day/(kind+'-pages.json');h=sha(path);assert h==pins[day,kind]
   ledger.append({'session':day,'kind':kind,'sha256':h})
  today=[(key,t) for key,t in entries.items() if t['session']==day]
  if not today:continue
  codes={t['symbol'] for _,t in today};by=collections.defaultdict(list)
  raw,_=f.v.saved.pages(Path(cache)/day/'minute-pages.json')
  for x in raw:
   assert x['Date']==day
   if x['Code'] in codes:by[x['Code']].append(x)
  daily,_=f.v.saved.pages(Path(cache)/day/'daily-pages.json');dc={x['Code']:x for x in daily};assert all(x['Date']==day for x in daily)
  for key,tr in sorted(today):
   start=int(key.split('|')[-1]);saved=labels[key];price=saved['price'];raw=by[tr['symbol']]
   fill=next((x for x in raw if f.v.minute_time(x)==start and f.v.valid(x)),None)
   checks.append({'entryId':key,'check':'savedFill','pass':bool(fill and same(fill['O']*1.0005,price))})
   m={'sessionDate':day,'decisionTimeJst':'%02d:%02d'%divmod(start,60),'decisionPrice':price};legacy=f.labels_for_raw(m,raw,dc.get(tr['symbol']))
   for h in [30,60]:
    for metric in ['mae','mfe','return']:
     k=metric+str(h);val=legacy[k]
     if metric=='return' and val is not None:val=(1+val/100)*.9995*100-100
     checks.append({'entryId':key,'check':k,'pass':same(val,saved['labels'][k]),'new':val,'saved':saved['labels'][k]})
   for k in ['mfeEnd','maeEnd']:checks.append({'entryId':key,'check':k,'pass':same(legacy[k],saved['labels'][k])})
   records[key]={'entryId':key,'opportunity':tr['opportunity'],'session':day,'symbol':tr['symbol'],'price':price,'30':horizon(day,start,price,raw,30,legacy),'60':horizon(day,start,price,raw,60,legacy)}
  print(json.dumps({'session':day,'fixedEntriesEvaluated':len(today)}),flush=True)
 result={}
 for arm in ARMS:
  entered=[t for t in trades[arm] if t['entryId']];caps=capture(ev,trades[arm],labels);result[arm]={'buyTotal':len(entered),'opportunities':len(ev),'capture':caps}
  for h in ['30','60']:
   rs=[records[t['entryId']][h] for t in entered];counts=collections.Counter(x['status'] for x in rs)
   panel={'coverage':{'buyTotal':len(rs),'pathAvailable':sum(x['pathAvailable'] for x in rs),'complete':counts['COMPLETE'],'censored':counts['CENSORED'],'unavailable':counts['UNAVAILABLE'],'reasons':dict(collections.Counter(x['reason'] for x in rs if x['reason']))},'hit':hit_rates(rs)}
   for k in ['MFE','MAE','MaxDD','MaxDDAdverseBound','returnNet','returnGross','givebackNetPp']:panel[k]=distribution(x[k] for x in rs)
   result[arm][h]=panel
  both=[records[t['entryId']] for t in entered if records[t['entryId']]['30']['status']=='COMPLETE' and records[t['entryId']]['60']['status']=='COMPLETE']
  result[arm]['pairedCompleteReturn']={h:distribution(x[h]['returnNet'] for x in both) for h in ['30','60']}
  checks.append({'arm':arm,'check':'BUY','pass':len(entered)==old[arm]['enterCount']})
  for metric,newkey in [('n','count'),('median','median'),('mean','mean'),('p05','p5')]:checks.append({'arm':arm,'check':'MAE30/'+metric,'pass':same(result[arm]['30']['MAE'][newkey],old[arm]['mae30'][metric])})
  for t in ['1','2','3','5']:
   for nk,ok in [('selectorWinnerDenominator','baselineWinners'),('captured','captured'),('rate','pct')]:checks.append({'arm':arm,'check':'capture/'+t+'/'+nk,'pass':same(caps[t][nk],old[arm]['capture'][t][ok])})
 # Additional human-reported rounded baseline cross-check, never overwrite a mismatch.
 for arm,n,med,c3,c5 in [('IMMEDIATE',1392,-1.240,66.0,68.4),('CURRENT',60,-1.626,3.7,5.1),('E5',1645,-1.161,71.7,74.5)]:
  z=result[arm];checks.append({'arm':arm,'check':'userReference','pass':z['buyTotal']==n and round(z['30']['MAE']['median'],3)==med and round(z['capture']['3']['rate'],1)==c3 and round(z['capture']['5']['rate'],1)==c5})
 failures=[x for x in checks if not x['pass']]
 audit={'status':'STOP_DEFINITION_COHORT_OR_SOURCE_MISMATCH' if failures else 'PASS','checks':len(checks),'failures':failures,'decisionLedgerSHA256':sha(src/'measurement/trades.json.gz'),'modelSHA256':sha(src/'measurement/models.json'),'fitCalls':0,'policyCalls':0,'inferenceCalls':0,'all144InputHashesAudited':True,'commonHoldoutOpened':0,'sealedOpened':0,'safety':p['safety']}
 write(out/'reproduction-audit.json',audit);write(out/'reproduction-checks.json.gz',checks)
 assert not failures,'STOP: existing values differ; see reproduction-audit.json'
 write(out/'summary.json',result);write(out/'outcome-ledger.json.gz',records);write(out/'input-ledger.json',ledger)
 write(out/'denominators.json',{a:{'capture':result[a]['capture'],**{h:{'coverage':result[a][h]['coverage'],'hit':result[a][h]['hit']} for h in ['30','60']}} for a in ARMS})
 write(out/'distributions.json.gz',{a:{h:{k:[records[t['entryId']][h][k] for t in trades[a] if t['entryId'] and records[t['entryId']][h][k] is not None] for k in ['MFE','MAE','MaxDD','MaxDDAdverseBound','returnNet','givebackNetPp']} for h in ['30','60']} for a in ARMS})
 from scripts.phase57_entry_extended_report import report
 report(out)
 write(out/'manifest.json',{x.name:sha(x) for x in sorted(out.iterdir())})

def main():
 a=argparse.ArgumentParser();a.add_argument('command',choices=['verify','measure']);a.add_argument('--cache');a.add_argument('--prior');a.add_argument('--output');x=a.parse_args()
 if x.command=='verify':verify()
 else:measure(x.cache,x.prior,x.output)
if __name__=='__main__':main()
