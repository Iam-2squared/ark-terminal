"""Bounded offline Entry intelligence. Immutable upstream; future values are labels only."""
import argparse,collections,csv,gzip,hashlib,json,math,platform,statistics
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.tree import DecisionTreeRegressor
from sklearn.preprocessing import StandardScaler
import sklearn
from scripts import phase57_new_long_entry_exit_conditional as c
from scripts import phase57_new_long_exit_candidate_a as ca
from scripts import phase57_opportunity_quality as q
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-comprehensive-entry-v1'
SOURCE=q.SOURCE
PROTOCOL_COMMIT='862f851d1895ced65fa508292fc6f4554b50935f'
BASE_FEATURES=['selectorRank','selectorScore','isDip','candidateBreadth','anchorAge','elapsed','minutesSinceOpen','minutesUntilSegmentEnd','afternoon','anchorPrice']
PRICE=['displacement','lastBody','lastRange','closeLocation','upperWick','lowerWick','recentHighDistance','recentLowDistance','momentum3','reclaim','failedReclaim','higherHigh','higherLow','lowerHigh','lowerLow']
PATH=['rangeMean','rangeRatio','closeVolatility','acceleration','efficiency','newLowCount','lowExtension','bounce','slope','directionalPersistence','signReversals','normalizedDisplacement']
LEGACY=['directionalMomentum3Pct','directionalMomentumAccelerationPct','directionalPullback6Pct','relativeVolume5','directionalReturnFromOpenPct','directionalVwapDistancePct']
FEATURES=BASE_FEATURES+PRICE+PATH+LEGACY

def read(p):return c.read(p)
def sha(p):return c.sha(p)
def enc(x):return q.encoded(x)
def write(p,x):q.write(p,x)
def dist(v):return q.distribution(v)
def perf(v):
 d=dist(v);a=[x for x in v if x is not None];d['PF']=ca.pf(a) if a else None;return d

def sources():
 p=read(BASE/'protocol.json')
 for f,h in p['sourcePins'].items():assert sha(ROOT/f)==h,f
 frozen=read(ROOT/'predict/research/phase57-long-only-frozen-selector-min-price75-v1.json')
 for f,h in frozen['freezePayload']['filePins'].items():assert sha(ROOT/f)==h,f
 ds=read(SOURCE/'downstream/entry-decisions.json.gz')['new']
 paths={r['selectorEventId']:r for r in read(SOURCE/'new-paths.json.gz')['events']}
 selectors={r['selectorEventId']:r for r in read(SOURCE/'selector/selector-ledger.json.gz')['new']}
 legacy={r['selectorEventId']:r for r in read(ROOT/'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz')}
 ops=[]
 for d in ds:
  for k in ('initialEvent','secondaryEvent'):
   op=d['decision'][k]
   if op:ops.append({'op':op,'session':d['sessionDate'],'symbol':d['symbol'],'id':op['anchorId']+'|'+op['eventType']})
 ops.sort(key=lambda x:(x['op']['opportunityTimestamp'],x['symbol'],x['id']))
 counts=collections.Counter(x['op']['opportunityTimestamp'] for x in ops)
 for x in ops:x['breadth']=counts[x['op']['opportunityTimestamp']]
 assert len(ops)==len({x['id'] for x in ops})==3508
 return p,ops,paths,selectors,legacy

def prefix_at(path,t):
 """Only completed bars available at t. Any missing observed prefix fails closed."""
 out=[b for b in path['future'] if c.minute(b['end'])<=t]
 return out if all(c.valid(b) for b in out) else None

def features(x,path,selector,legacy,t):
 op=x['op'];start=c.minute(op['opportunityTimestamp']);anchor=c.minute(path['decisionTimestamp']);end=c.segment_end(start,path['sessionEndMinute'])
 bs=prefix_at(path,t)
 if bs is None:return None
 f=dict.fromkeys(FEATURES)
 f.update(selectorRank=selector['newEligibleRank'],selectorScore=selector['savedV1Score'],isDip=int(op['eventType']==q.DIP),candidateBreadth=x['breadth'],anchorAge=t-anchor,elapsed=t-start,minutesSinceOpen=t-540,minutesUntilSegmentEnd=(end-t if end else 0),afternoon=int(t>=750),anchorPrice=path['decisionPrice'])
 # Snapshot values retained as anchor context, never presented as a refreshed value at DIP/WAIT.
 for k in LEGACY:
  v=legacy.get('features',{}).get(k,{})
  f[k]=v.get('value') if v.get('status')=='AVAILABLE' else None
 if not bs:return f
 b=bs[-1];recent=bs[-6:];cs=[a['c'] for a in recent];ranges=[a['h']-a['l'] for a in recent];span=b['h']-b['l'];delta=[v-u for u,v in zip(cs,cs[1:])]
 f.update(displacement=b['c'],lastBody=b['c']-b['o'],lastRange=span,closeLocation=(b['c']-b['l'])/span if span else .5,upperWick=b['h']-max(b['o'],b['c']),lowerWick=min(b['o'],b['c'])-b['l'],recentHighDistance=b['c']-max(a['h'] for a in recent),recentLowDistance=b['c']-min(a['l'] for a in recent),momentum3=cs[-1]-cs[max(0,len(cs)-3)],reclaim=int(b['c']>=0),failedReclaim=int(any(a['c']>=0 for a in recent[:-1]) and b['c']<0),rangeMean=statistics.mean(ranges),rangeRatio=span/statistics.mean(ranges) if sum(ranges)>0 else 0,closeVolatility=statistics.pstdev(delta) if delta else 0,efficiency=abs(cs[-1]-cs[0])/sum(abs(z) for z in delta) if delta and any(delta) else 0,newLowCount=sum(v['l']<u['l'] for u,v in zip(recent,recent[1:])),lowExtension=recent[0]['l']-min(a['l'] for a in recent),bounce=b['c']-min(a['l'] for a in recent),slope=(cs[-1]-cs[0])/max(1,len(cs)-1),directionalPersistence=sum(z>0 for z in delta)/len(delta) if delta else .5,signReversals=sum(u*v<0 for u,v in zip(delta,delta[1:])),normalizedDisplacement=b['c']/statistics.mean(ranges) if sum(ranges)>0 else 0)
 if len(bs)>=2:
  prev=bs[-2];f.update(higherHigh=int(b['h']>prev['h']),higherLow=int(b['l']>prev['l']),lowerHigh=int(b['h']<prev['h']),lowerLow=int(b['l']<prev['l']))
 if len(delta)>=2:f['acceleration']=delta[-1]-delta[-2]
 return f

def episode(x,path,delay):
 op=x['op'];start=c.minute(op['opportunityTimestamp']);t=start+delay;bound=c.segment_end(start,path['sessionEndMinute'])
 if op['referenceStatus']!='REFERENCE_OPEN':return None
 if bound is None or t>=bound:return None
 # Scheduled OPEN price is consumed only by execution/evaluator, not feature generation.
 b=next((b for b in path['future'] if c.minute(b['start'])==t),None)
 if not c.valid(b):return None
 price=path['decisionPrice']*(1+b['o']/100)
 z={**op,'referenceTimestamp':c.stamp(x['session'],t),'referencePrice':price,'opportunityTimestamp':c.stamp(x['session'],t)}
 return c.adapt(z,path)

def eval_entry(x,path,delay,runtime):
 e=episode(x,path,delay)
 if not e:return None
 b=e['future'];start=c.minute(x['op']['opportunityTimestamp']);bound=c.segment_end(start,path['sessionEndMinute'])
 common=[r for r in b if c.minute(r['end'])<=start+60]
 complete=start+60<=bound and len(common)==(60-delay)//5 and all(c.valid(z) for z in common)
 thirty=[r for r in b if r['minutes']<=30];strict=len(thirty)==6 and e['startMinute']+30<=bound and all(c.valid(z) for z in thirty)
 f=runtime.replay(e,'FIXED12');a=ca.policy(b[:f['exitBar']],f) if f['status']=='EXIT_REFERENCE' else None
 result={'delay':delay,'price':e['fillPriceAssumption'],'commonComplete':complete,'strict30Complete':strict,'fixed':f,'candidateA':a,'common':None,'strict30':None}
 if complete:
  result['common']={'mfe':max(0,max(z['h'] for z in common)),'mae':min(0,min(z['l'] for z in common)),'return':common[-1]['c'],'firstPositiveMinutes':next((z['minutes'] for z in common if z['c']>0),None),'hitMinutes':{str(k):next((z['minutes'] for z in common if z['h']>=k),None) for k in (1,2,3,5)}}
 if strict:result['strict30']={'mfe':max(0,max(z['h'] for z in thirty)),'mae':min(0,min(z['l'] for z in thirty))}
 return result

def path_class(x,path):
 e=episode(x,path,0)
 if not e:return 'INCONCLUSIVE'
 rows=[b for b in e['future'] if b['minutes']<=60];bound=c.segment_end(e['startMinute'],e['sessionEndMinute'])
 if e['startMinute']+60>bound or len(rows)!=12 or not all(c.valid(b) for b in rows):return 'INCONCLUSIVE'
 hit=next((i for i,b in enumerate(rows) if b['h']>=3),None)
 if hit is not None:
  prior=rows[:hit];adverse=[b for b in prior if b['l']<0]
  if not adverse:
   if rows[hit]['l']<0:return 'INCONCLUSIVE'
   changes=[b['c']-a['c'] for a,b in zip(prior,prior[1:])]
   if sum(a*b<0 for a,b in zip(changes,changes[1:]))>=3:return 'CHOP_THEN_WINNER'
   return 'IMMEDIATE_WINNER'
  return 'DEEP_PULLBACK_THEN_WINNER' if min(b['l'] for b in prior)<=-3 else 'PULLBACK_THEN_WINNER'
 return 'CONTINUED_FAILURE' if rows[-1]['c']<0 and min(b['l'] for b in rows)<=-3 else 'OPPORTUNITY_EXPIRED'

def utility(e):return e['common']['return']-.05+.5*e['common']['mae']
def matrix(rows,names):return np.array([[r.get(k) if r.get(k) is not None else np.nan for k in names] for r in rows],dtype=float)
class Model:
 def __init__(self,kind,names):self.kind=kind;self.names=names
 def fit(self,fs,ys,weights):
  a=matrix(fs,self.names);self.medians=np.array([np.median(v[np.isfinite(v)]) if np.isfinite(v).any() else 0 for v in a.T]);z=self.fill(a);self.scaler=StandardScaler().fit(z);z=self.scaler.transform(z)
  self.model=Ridge(alpha=10) if self.kind=='LINEAR' else DecisionTreeRegressor(max_depth=3,min_samples_leaf=100,random_state=57)
  self.model.fit(z,np.array(ys),sample_weight=np.array(weights));return self
 def fill(self,a):return np.concatenate([np.where(np.isnan(a),self.medians,a),np.isnan(a).astype(float)],axis=1)
 def predict(self,fs):return self.model.predict(self.scaler.transform(self.fill(matrix(fs,self.names))))
 def dump(self):
  d={'kind':self.kind,'features':self.names,'medians':self.medians.tolist(),'scalerMean':self.scaler.mean_.tolist(),'scalerScale':self.scaler.scale_.tolist()}
  if self.kind=='LINEAR':d.update(coefficients=self.model.coef_.tolist(),intercept=self.model.intercept_.tolist())
  else:
   t=self.model.tree_;d['tree']={k:getattr(t,k).tolist() for k in ('children_left','children_right','feature','threshold','value','n_node_samples')}
  return d

def training(ops,paths,selectors,legacy,runtime):
 fs=[];ys=[];ws=[];ids=[];dates=[]
 for x in ops:
  path=paths[x['op']['anchorId']];evaluated={d:eval_entry(x,path,d,runtime) for d in range(0,31,5)}
  if not evaluated[0] or not evaluated[0]['commonComplete']:continue
  states=[]
  for d in range(0,31,5):
   e=evaluated[d];f=features(x,path,selectors[x['op']['anchorId']],legacy.get(x['op']['anchorId'],{}),c.minute(x['op']['opportunityTimestamp'])+d)
   if not e or not e['commonComplete'] or f is None:continue
   later=[utility(v) for k,v in evaluated.items() if k>d and v and v['commonComplete']]
   states.append((f,[utility(e),max([0]+later)]))
  for f,y in states:fs.append(f);ys.append(y);ws.append(1/len(states));ids.append(x['id']);dates.append(x['session'])
 return fs,ys,ws,ids,dates

def decide(x,path,selector,legacy,model):
 op=x['op'];start=c.minute(op['opportunityTimestamp']);bound=c.segment_end(start,path['sessionEndMinute']);log=[]
 if op['referenceStatus']!='REFERENCE_OPEN':return {'status':'EXPIRE_REFERENCE','delay':None,'transitions':[]}
 for d in range(0,31,5):
  t=start+d
  if bound is None or t>=bound:return {'status':'EXPIRE_BOUNDARY','delay':None,'transitions':log}
  f=features(x,path,selector,legacy,t)
  if f is None:return {'status':'EXPIRE_MISSING_PREFIX','delay':None,'transitions':log}
  buy,wait=map(float,model.predict([f])[0]);action='BUY_NOW' if buy>0 and buy>=wait else 'SKIP_OR_EXPIRE' if d==30 else 'WAIT'
  log.append({'timestamp':c.stamp(x['session'],t),'delay':d,'buyValue':buy,'waitValue':wait,'action':action})
  if action=='BUY_NOW':
   e=episode(x,path,d)
   return {'status':'COUNTERFACTUAL_ENTER' if e else 'EXPIRE_MISSING_OPEN','delay':d if e else None,'transitions':log}
  if action=='SKIP_OR_EXPIRE':break
 return {'status':'EXPIRE_WAIT_CAP','delay':None,'transitions':log}

def measure(ops,paths,selectors,legacy,model,runtime):
 rows=[]
 for x in ops:
  aid=x['op']['anchorId'];path=paths[aid];b=eval_entry(x,path,0,runtime);d=decide(x,path,selectors[aid],legacy.get(aid,{}),model);e=eval_entry(x,path,d['delay'],runtime) if d['delay'] is not None else None
  rows.append({'id':x['id'],'session':x['session'],'symbol':x['symbol'],'source':x['op']['eventType'],'breadth':x['breadth'],'timestamp':x['op']['opportunityTimestamp'],'pathClass':path_class(x,path),'decision':d,'baseline':b,'entry':e})
 return rows

def summary(rows):
 common=[r for r in rows if r['baseline'] and r['baseline']['commonComplete']];entered=[r for r in common if r['entry'] and r['entry']['commonComplete']];missed=[r for r in common if r['entry'] is None]
 economic=[r for r in common if r['baseline']['candidateA'] and (r['entry'] is None or r['entry']['candidateA'])];paired=[r for r in economic if r['entry']]
 base=[r['baseline']['candidateA']['netPct'] for r in economic];candidate=[r['entry']['candidateA']['netPct'] if r['entry'] else 0 for r in economic]
 improvements=[100*(r['baseline']['price']-r['entry']['price'])/r['baseline']['price'] for r in entered]
 get=lambda arm,k:[r[arm]['common'][k] for r in entered]
 preservation={}
 for k in (1,2,3,5):
  wins=[r for r in common if r['baseline']['common']['mfe']>=k]
  preservation[str(k)]={'baselineWinners':len(wins),'entered':sum(r['entry'] is not None for r in wins),'remainingWinners':sum(r['entry'] is not None and r['entry']['commonComplete'] and r['entry']['common']['mfe']>=k for r in wins),'rate':sum(r['entry'] is not None and r['entry']['commonComplete'] and r['entry']['common']['mfe']>=k for r in wins)/len(wins) if wins else None}
 tails={str(k):{'baselineAll':sum(r['baseline']['common']['mae']<=-k for r in common),'baselineEnteredPair':sum(r['baseline']['common']['mae']<=-k for r in entered),'candidate':sum(r['entry']['common']['mae']<=-k for r in entered)} for k in (3,5,10)}
 return {'opportunities':len(rows),'commonComplete':len(common),'enteredComplete':len(entered),'missedComplete':len(missed),'commonCoverage':len(common)/len(rows) if rows else 0,'entryRate':len(entered)/len(common) if common else None,'decisions':dict(collections.Counter(r['decision']['status'] for r in rows)),'waitCount':sum(sum(t['action']=='WAIT' for t in r['decision']['transitions']) for r in rows),'delay':dist([r['decision']['delay'] for r in rows]),'priceImprovement':dist(improvements),'favorablePriceRate':sum(v>0 for v in improvements)/len(improvements) if improvements else None,'baselineMAEPaired':dist(get('baseline','mae')),'entryMAEPaired':dist(get('entry','mae')),'baselineMFEPaired':dist(get('baseline','mfe')),'entryMFEPaired':dist(get('entry','mfe')),'strict30BaselinePaired':dist([r['baseline']['strict30']['mae'] for r in entered if r['baseline']['strict30Complete'] and r['entry']['strict30Complete']]),'strict30EntryPaired':dist([r['entry']['strict30']['mae'] for r in entered if r['baseline']['strict30Complete'] and r['entry']['strict30Complete']]),'preservation':preservation,'tails':tails,'economic':{'n':len(economic),'baseline':perf(base),'candidateCashIncluded':perf(candidate),'pairedDelta':dist([b-a for a,b in zip(base,candidate)]),'executedOnlyBaseline':perf([r['baseline']['candidateA']['netPct'] for r in paired]),'executedOnlyCandidate':perf([r['entry']['candidateA']['netPct'] for r in paired]),'missingCandidateEconomics':sum(r['entry'] is not None and r['entry']['candidateA'] is None for r in common)},'pathClasses':dict(collections.Counter(r['pathClass'] for r in rows)),'classDecisions':{k:dict(collections.Counter(r['decision']['status'] for r in rows if r['pathClass']==k)) for k in sorted({r['pathClass'] for r in rows})},'timeToPositive':dist([r['entry']['common']['firstPositiveMinutes'] for r in entered]),'timeToHit':{str(k):dist([r['entry']['common']['hitMinutes'][str(k)] for r in entered]) for k in (1,2,3,5)}}

def gates(s):
 def delta(a,b,k):return b.get(k)-a.get(k) if a.get(k) is not None and b.get(k) is not None else -math.inf
 e=s['economic'];p=s['priceImprovement'];b=s['baselineMAEPaired'];a=s['entryMAEPaired'];tail=s['tails']['5']
 g={'sample':s['commonComplete']>=100,'coverage':s['entryRate'] is not None and s['entryRate']>=.70,'price':p['mean'] is not None and p['mean']>=.10,'maeMedian':delta(b,a,'median')>=.10,'maeP05':delta(b,a,'p05')>=.25,'deep5':tail['baselineAll']>0 and tail['candidate']<=.9*tail['baselineAll'],'plus3':(s['preservation']['3']['rate'] or 0)>=.90,'plus5':(s['preservation']['5']['rate'] or 0)>=.90,'meanNet':(e['pairedDelta']['mean'] if e['pairedDelta']['mean'] is not None else -math.inf)>=.05,'PF':delta(e['baseline'],e['candidateCashIncluded'],'PF')>=0,'netP05':delta(e['baseline'],e['candidateCashIncluded'],'p05')>=0}
 return g

def panel(rows):
 s=summary(rows);coh={k:summary([r for r in rows if r['source']==k]) for k in (q.INITIAL,q.DIP)}
 dates=sorted({r['session'] for r in rows});chunks=[list(z) for z in np.array_split(dates,4)];blocks={str(i+1):summary([r for r in rows if r['session'] in ds]) for i,ds in enumerate(chunks)}
 freq=collections.Counter(r['symbol'] for r in rows);top3=[k for k,v in sorted(freq.items(),key=lambda z:(-z[1],z[0]))[:3]];ex=summary([r for r in rows if r['symbol'] not in top3]);g=gates(s)
 g['cohorts']=all(v['commonComplete']>=30 and all((v['preservation'][k]['rate'] or 0)>=.85 for k in ('3','5')) and v['economic']['pairedDelta']['mean'] is not None and v['economic']['pairedDelta']['mean']>=0 for v in coh.values())
 g['chronological']=sum(v['economic']['pairedDelta']['mean'] is not None and v['economic']['pairedDelta']['mean']>=0 for v in blocks.values())>=3
 g['top3Exclusion']=ex['economic']['pairedDelta']['mean'] is not None and ex['economic']['pairedDelta']['mean']>0
 return {'overall':s,'sources':coh,'blocks':blocks,'top3':top3,'top3Excluded':ex,'gates':g,'pass':all(g.values()),'concentration':{'uniqueSymbols':len(freq),'symbolHHI':sum((v/len(rows))**2 for v in freq.values()),'top10':sorted(freq.items(),key=lambda z:(-z[1],z[0]))[:10]},'breadth':{str(k):summary([r for r in rows if r['breadth']==k]) for k in range(1,6)},'time':{k:summary([r for r in rows if ('AFTERNOON' if c.minute(r['timestamp'])>=750 else 'MORNING')==k]) for k in ('MORNING','AFTERNOON')}}

def inventory(ops,paths,selectors,legacy,out):
 fs=[features(x,paths[x['op']['anchorId']],selectors[x['op']['anchorId']],legacy.get(x['op']['anchorId'],{}),c.minute(x['op']['opportunityTimestamp'])) for x in ops]
 rows=[]
 for k in FEATURES:
  n=sum(f is not None and f.get(k) is not None for f in fs);family='SELECTOR_TIME' if k in BASE_FEATURES else 'PRICE' if k in PRICE else 'PATH' if k in PATH else 'LEGACY_ANCHOR_CONTEXT'
  rows.append({'feature':k,'family':family,'status':'AVAILABLE_PIT' if k in BASE_FEATURES+LEGACY else 'DERIVABLE_PIT','source':'exact saved selector/opportunity' if k in BASE_FEATURES else 'historical matching anchor feature snapshot' if k in LEGACY else 'saved completed 5m prefix','PIT_available_at':'anchor timestamp' if k in LEGACY else 'decision timestamp; bar.end<=decision','missing_rate':1-n/len(ops),'coverage':n,'denominator':len(ops),'derivation':'see features(); immutable anchor context, not refreshed' if k in LEGACY else 'see features(); no future/open at decision input','future_leak_risk':'blocked by prefix projection; per-bar publication delay not serialized','approved_for_research':True,'notes':'coverage is opportunity-emission only; WAIT coverage separately reported; missing indicators preserve absence'})
 for k in ['volume','rollingVolume','volumeAcceleration','turnover','spread','ATR_preEntry','marketReturn','marketVolatility','marketBreadth','sectorReturn','sectorRelativeStrength','gapContext','sessionOpenPrice','orderBook','revisedMarketData']:
  rows.append({'feature':k,'family':'UNAVAILABLE_FULL_POPULATION','status':'MISSING','source':'not serialized in current new-population paths; legacy volume proxy separately available','PIT_available_at':'unverified for full 3508','missing_rate':1,'coverage':0,'denominator':len(ops),'derivation':'no new acquisition; no inferred zero','future_leak_risk':'do not substitute future or unmatched old event','approved_for_research':False,'notes':'MISSING in aligned research substrate, not claim absent everywhere in repo'})
 for k in ['futureHIGH','futureLOW','futureReturn','futureMFE','futureMAE','terminalOutcome','futureSelectorState','bestFutureEntry']:
  rows.append({'feature':k,'family':'EVALUATOR','status':'FUTURE_ONLY_FORBIDDEN','source':'saved evaluator/path','PIT_available_at':'after decision','missing_rate':None,'coverage':None,'denominator':len(ops),'derivation':'labels only','future_leak_risk':'FORBIDDEN','approved_for_research':False,'notes':'never model input'})
 with (out/'feature-inventory.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 return {'total':len(rows),'status':dict(collections.Counter(r['status'] for r in rows)),'legacyMatchedOpportunities':sum(x['op']['anchorId'] in legacy for x in ops),'inventoryCoversEmissionOnly':True}

def run(out):
 out=Path(out)
 if out.exists():raise FileExistsError(out)
 out.mkdir(parents=True);p,ops,paths,selectors,legacy=sources();inv=inventory(ops,paths,selectors,legacy,out)
 runtime=c.module('comprehensive_frozen_fixed12',c.RUNTIME)
 train=[x for x in ops if x['session'] in p['split']['TRAIN']];val=[x for x in ops if x['session'] in p['split']['VALIDATION']]
 fs,ys,ws,ids,dates=training(train,paths,selectors,legacy,runtime)
 assert not set(dates)&set(p['split']['VALIDATION']+p['split']['DEVELOPMENT_TEST'])
 # Fixed family diagnostics; all families retained regardless of result.
 ablations={};inner=set(p['split']['TRAIN'][:26]);fit=[i for i,d in enumerate(dates) if d in inner];check=[i for i,d in enumerate(dates) if d not in inner]
 for name,names in [('BASE',BASE_FEATURES),('PRICE',BASE_FEATURES+PRICE),('PATH',BASE_FEATURES+PRICE+PATH),('LEGACY',FEATURES)]:
  m=Model('LINEAR',names).fit([fs[i] for i in fit],[ys[i] for i in fit],[ws[i] for i in fit]);pred=m.predict([fs[i] for i in check]);err=pred-np.array([ys[i] for i in check]);ablations[name]={'fitStates':len(fit),'heldTrainStates':len(check),'MAE':np.mean(np.abs(err),axis=0).tolist(),'RMSE':np.sqrt(np.mean(err**2,axis=0)).tolist(),'featureCount':len(names),'parameters':int(m.model.coef_.size+m.model.intercept_.size),'notUsedForSelection':True}
 diagnostics={}
 for k in FEATURES:
  vals=[f[k] for f in fs if f[k] is not None];diagnostics[k]={'coverage':len(vals),'states':len(fs),'distribution':dist(vals),'byTrainBlock':{str(j+1):dist([f[k] for f,d in zip(fs,dates) if d in p['split']['TRAIN'][j*19:(j+1)*19]]) for j in range(2)}}
 imputed=np.array([[f[k] if f[k] is not None else 0 for k in FEATURES] for f in fs]);pairs=[]
 for i in range(len(FEATURES)):
  for j in range(i):
   if np.std(imputed[:,i])>0 and np.std(imputed[:,j])>0:
    corr=float(np.corrcoef(imputed[:,i],imputed[:,j])[0,1])
    if abs(corr)>=.9:pairs.append([FEATURES[j],FEATURES[i],corr])
 write(out/'train-diagnostics.json',{'inventory':inv,'states':len(fs),'effectiveEpisodes':len(set(ids)),'episodeWeightSum':sum(ws),'familyAblation':ablations,'features':diagnostics,'correlationMissingAsZeroDescriptiveOnly':pairs})
 # Fixed waits are diagnostics on TRAIN only, never candidate selection.
 study={};oracle=[];classes=collections.Counter()
 for d in (0,5,10,15,20,30):
  es=[]
  for x in train:
   e=eval_entry(x,paths[x['op']['anchorId']],d,runtime)
   if e and e['commonComplete']:es.append(e)
  study[str(d)]={'n':len(es),'MAE':dist([e['common']['mae'] for e in es]),'MFE':dist([e['common']['mfe'] for e in es]),'return':dist([e['common']['return'] for e in es]),'hits':{str(k):sum(e['common']['mfe']>=k for e in es) for k in (1,2,3,5)}}
 for x in train:
  path=paths[x['op']['anchorId']];classes[path_class(x,path)]+=1;b=eval_entry(x,path,0,runtime)
  if b and b['commonComplete']:
   es=[eval_entry(x,path,d,runtime) for d in range(0,31,5)];prices=[e['price'] for e in es if e and e['commonComplete']];oracle.append(100*(b['price']-min(prices))/b['price'])
 write(out/'train-location-study.json',{'fixedWaitsNotCandidates':study,'pathClasses':dict(classes),'oracleBestExecutableOpenImprovement':dist(oracle),'futureLowNeverExecution':True,'scope':'TRAIN_ONLY'})
 results={};ledgers={};models={}
 for kind in ('LINEAR','TREE'):
  m=Model(kind,FEATURES).fit(fs,ys,ws);models[kind]=m;write(out/('model-'+kind.lower()+'.json'),m.dump());rows=measure(val,paths,selectors,legacy,m,runtime);ledgers[kind]=rows;results[kind]=panel(rows)
  write(out/('validation-'+kind.lower()+'.json.gz'),rows)
 selected=next((k for k in ('LINEAR','TREE') if results[k]['pass']),None)
 test=None
 if selected:
  testops=[x for x in ops if x['session'] in p['split']['DEVELOPMENT_TEST']];rs=measure(testops,paths,selectors,legacy,models[selected],runtime);test=panel(rs);write(out/'development-test.json.gz',rs)
 verdict='COMPREHENSIVE_LONG_ENTRY_DEVELOPMENT_PASS' if test and test['pass'] else 'COMPREHENSIVE_LONG_ENTRY_DEVELOPMENT_LIMIT_REACHED'
 s={'protocolCommit':PROTOCOL_COMMIT,'inventory':inv,'population':{'sessions':76,'opportunities':3508,'splitOpportunities':{k:sum(x['session'] in ds for x in ops) for k,ds in p['split'].items()},'source':dict(collections.Counter(x['op']['eventType'] for x in ops))},'validation':results,'selected':selected,'developmentTest':test,'developmentTestOpened':selected is not None,'verdict':verdict,'freeze':'COMPREHENSIVE_LONG_ENTRY_DEVELOPMENT_FROZEN_NOT_FRESH_VALIDATED' if verdict.endswith('_PASS') else 'NO_NEW_ENTRY_FREEZE_EXISTING_OPPORTUNITY_GENERATOR_RETAINED','boundedConclusion':'Two precommitted architectures using the aligned available substrate; no claim all possible Entry intelligence is impossible.','safety':p['safety'],'freshOOSOpened':False,'audit':{'sourcePinsVerified':True,'upstreamChanges':0,'exitChanges':0,'capitalSimulation':0,'candidateFits':2,'trainDiagnosticFits':4,'featureNames':FEATURES,'runtime':{'python':platform.python_version(),'numpy':np.__version__,'sklearn':sklearn.__version__},'independentOpportunityEpisodesNotPortfolio':True,'noReentryWithinEpisode':all(sum(t['action']=='BUY_NOW' for t in r['decision']['transitions'])<=1 for rs in ledgers.values() for r in rs)}}
 write(out/'summary.json',s)
 write(out/'manifest.json',{'protocolSHA256':sha(BASE/'protocol.json'),'protocolCommit':PROTOCOL_COMMIT,'sourcePins':p['sourcePins'],'codeSHA256':sha(__file__),'outputs':{f.name:sha(f) for f in sorted(out.iterdir()) if f.is_file()},'safety':p['safety']})
 print(json.dumps({'verdict':verdict,'selected':selected,'testOpened':s['developmentTestOpened'],'validation':{k:{'gates':v['gates'],'n':v['overall']['commonComplete'],'entryRate':v['overall']['entryRate'],'netDelta':v['overall']['economic']['pairedDelta']['mean'],'preservation':v['overall']['preservation']} for k,v in results.items()}},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args();run(args.out)
