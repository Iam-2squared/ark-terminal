"""Offline causal one-step Entry research. Futures enter evaluator/teacher only."""
import argparse,collections,json,math,platform
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from scripts import phase57_comprehensive_entry as v1
m=v1;c=m.c;q=m.q
ROOT=m.ROOT;BASE=ROOT/'docs/evidence/phase57-comprehensive-entry-v2'
PROTOCOL_COMMIT='5b857b6a86d20aacfff4a15732ef9e898eafdb32'
KINDS=('S1_LINEAR','S2_TREE','S3_GUARDED_LINEAR');LEVELS=(1,2,3,5);WEIGHTS={1:.25,2:.5,3:2.,5:3.}

def sources():
 p=m.read(BASE/'protocol.json')
 for f,h in p['sourcePins'].items():assert m.sha(ROOT/f)==h,f
 old,ops,paths,selectors,legacy=m.sources();assert p['split']==old['split']
 return p,ops,paths,selectors,legacy

def state(x,path,selector,legacy,t):
 """PIT projection; requires a contiguous completed prefix, not future OHLC."""
 anchor=c.minute(path['decisionTimestamp']);expected=c.grid(anchor,t)
 completed=[b for b in path['future'] if c.minute(b['end'])<=t]
 if [c.minute(b['start']) for b in completed]!=expected:return None
 return m.features(x,path,selector,legacy,t)

def open_reference(path,t):
 b=next((b for b in path['future'] if c.minute(b['start'])==t),None)
 if b is None or b.get('missing'):return None
 o=b.get('o')
 if isinstance(o,bool) or not isinstance(o,(int,float)) or not math.isfinite(o):return None
 price=path['decisionPrice']*(1+o/100)
 return price if price>0 and math.isfinite(price) else None

def evaluate(x,path,delay):
 """No EXIT calls. Pure post-decision path labels."""
 e=m.episode(x,path,delay)
 if not e:return None
 start=c.minute(x['op']['opportunityTimestamp']);bound=c.segment_end(start,path['sessionEndMinute']);bars=e['future']
 common=[b for b in bars if c.minute(b['end'])<=start+60];thirty=[b for b in bars if b['minutes']<=30]
 complete=bound is not None and start+60<=bound and len(common)==(60-delay)//5 and len(common)>0 and all(c.valid(b) for b in common)
 strict=bound is not None and e['startMinute']+30<=bound and len(thirty)==6 and all(c.valid(b) for b in thirty)
 def metrics(bs):
  return {'mfe':max(0,max(b['h'] for b in bs)),'mae':min(0,min(b['l'] for b in bs)),'return':bs[-1]['c'],'firstPositiveMinutes':next((b['minutes'] for b in bs if b['c']>0),None),'hitMinutes':{str(k):next((b['minutes'] for b in bs if b['h']>=k),None) for k in LEVELS}}
 return {'price':e['fillPriceAssumption'],'delay':delay,'commonComplete':complete,'strict30Complete':strict,'common':metrics(common) if complete else None,'strict30':metrics(thirty) if strict else None,'fastWinner':bool(complete and common[0]['h']>=1 and max(b['h'] for b in common)>=3),'fullUnderlyingMinutes':complete and all(b.get('observedMinutes')==5 for b in common)}

def utility(e):return e['common']['return']-.05+.25*e['common']['mae']
def labels(now,nxt):
 """Only a now and exactly-next purchase outcome. No max over later entries."""
 u=utility(now);miss=sum(w for k,w in WEIGHTS.items() if now['common']['mfe']>=k)
 skip=-u-miss-float(now['fastWinner'])
 wait=None;lost=None;chase=None
 if nxt is not None and nxt['commonComplete']:
  lost=sum(w for k,w in WEIGHTS.items() if now['common']['mfe']>=k and nxt['common']['mfe']<k)
  chase=float(now['fastWinner'] and nxt['price']>now['price'])
  wait=utility(nxt)-u-.05-lost-chase
 return {'buyUtility':u,'waitAdvantage':wait,'skipAdvantage':skip,'lostThresholdPenalty':lost,'fastChasePenalty':chase,'fastWinner':int(now['fastWinner'])}

def training(ops,paths,selectors,legacy):
 rows=[]
 for x in ops:
  aid=x['op']['anchorId'];path=paths[aid];cache={d:evaluate(x,path,d) for d in range(0,31,5)}
  if not cache[0] or not cache[0]['commonComplete']:continue
  group=[]
  for d in range(0,31,5):
   now=cache[d];f=state(x,path,selectors[aid],legacy.get(aid,{}),c.minute(x['op']['opportunityTimestamp'])+d)
   if not now or not now['commonComplete'] or f is None:continue
   lab=labels(now,cache.get(d+5));group.append({'id':x['id'],'session':x['session'],'source':x['op']['eventType'],'delay':d,'features':f,'labels':lab})
  waitn=sum(r['labels']['waitAdvantage'] is not None for r in group)
  for r in group:r.update(skipWeight=1/len(group),waitWeight=1/waitn if r['labels']['waitAdvantage'] is not None else 0);rows.append(r)
 return rows

class Sequential:
 def __init__(self,kind,wait,skip,guard=None):self.kind=kind;self.wait=wait;self.skip=skip;self.guard=guard
 def predict(self,f):
  wait=float(np.asarray(self.wait.predict([f])).reshape(-1)[0]);skip=float(np.asarray(self.skip.predict([f])).reshape(-1)[0]);prob=None
  if self.guard is not None:
   a=self.skip.scaler.transform(self.skip.fill(m.matrix([f],m.FEATURES)));prob=float(self.guard.predict_proba(a)[0,1])
  return wait,skip,prob
 def dump(self):
  r={'kind':self.kind,'features':m.FEATURES,'waitHead':self.wait.dump(),'skipHead':self.skip.dump(),'guard':None}
  if self.guard is not None:r['guard']={'coefficients':self.guard.coef_.tolist(),'intercept':self.guard.intercept_.tolist(),'classes':self.guard.classes_.tolist(),'threshold':.5,'scaler':'exact skipHead scaler/medians','maxIterations':2000,'iterations':self.guard.n_iter_.tolist()}
  return r

def fit_heads(rows,kind):
 heads=[]
 for label,weight in [('waitAdvantage','waitWeight'),('skipAdvantage','skipWeight')]:
  rs=[r for r in rows if r['labels'][label] is not None]
  heads.append(m.Model(kind,m.FEATURES).fit([r['features'] for r in rs],[[r['labels'][label]] for r in rs],[r[weight] for r in rs]))
 return heads

def fit_guard(rows,linear):
 fs=[r['features'] for r in rows];x=linear.skip.scaler.transform(linear.skip.fill(m.matrix(fs,m.FEATURES)));ys=[r['labels']['fastWinner'] for r in rows]
 guard=LogisticRegression(C=1,max_iter=2000,random_state=57).fit(x,ys,sample_weight=[r['skipWeight'] for r in rows]);assert max(guard.n_iter_)<2000
 return guard

def action(wait,skip,guard,can_wait):
 if guard is not None and guard>=.5:return 'BUY_NOW'
 choices=[('BUY_NOW',0.)]
 if can_wait:choices.append(('WAIT_ONE_STEP',wait))
 choices.append(('SKIP_OR_EXPIRE',skip))
 return max(choices,key=lambda z:z[1])[0]

def decide(x,path,selector,legacy,model=None,baseline=None):
 op=x['op'];start=c.minute(op['opportunityTimestamp']);bound=c.segment_end(start,path['sessionEndMinute']);log=[]
 if op['referenceStatus']!='REFERENCE_OPEN':return {'status':'EXPIRE_REFERENCE','delay':None,'transitions':log}
 for d in range(0,31,5):
  t=start+d
  if bound is None or t>=bound:return {'status':'EXPIRE_BOUNDARY','delay':None,'transitions':log}
  f=state(x,path,selector,legacy,t)
  if f is None:return {'status':'EXPIRE_MISSING_PREFIX','delay':None,'transitions':log}
  can_wait=d<30 and t+5<bound
  if baseline:
   wait=skip=guard=None;a='WAIT_ONE_STEP' if baseline=='B1_FIXED_WAIT_1' and d==0 else 'BUY_NOW'
   if a=='WAIT_ONE_STEP' and not can_wait:return {'status':'EXPIRE_BOUNDARY','delay':None,'transitions':log}
  else:
   wait,skip,guard=model.predict(f);assert math.isfinite(wait) and math.isfinite(skip);a=action(wait,skip,guard,can_wait)
  log.append({'timestamp':c.stamp(x['session'],t),'delay':d,'action':a,'waitAdvantage':wait,'skipAdvantage':skip,'fastWinnerProbability':guard,'waitAllowed':can_wait})
  if a=='BUY_NOW':
   price=open_reference(path,t)
   return {'status':'COUNTERFACTUAL_ENTER' if price is not None else 'EXPIRE_MISSING_OPEN','delay':d if price is not None else None,'transitions':log}
  if a=='SKIP_OR_EXPIRE':return {'status':'MODEL_SKIP','delay':None,'transitions':log}
 raise AssertionError('WAIT_CAP_NOT_TERMINAL')

def measure(ops,paths,selectors,legacy,model=None,baseline=None,saved=None):
 rows=[]
 for x in ops:
  aid=x['op']['anchorId'];path=paths[aid]
  d=saved[x['id']]['decision'] if saved is not None else decide(x,path,selectors[aid],legacy.get(aid,{}),model,baseline)
  b=evaluate(x,path,0);e=evaluate(x,path,d['delay']) if d['delay'] is not None else None
  if saved is not None:
   previous=saved[x['id']]['baseline']
   assert (bool(b and b['commonComplete']))==(bool(previous and previous['commonComplete']))
   if b and b['commonComplete']:assert b['common']==previous['common']
  rows.append({'id':x['id'],'session':x['session'],'symbol':x['symbol'],'source':x['op']['eventType'],'breadth':x['breadth'],'timestamp':x['op']['opportunityTimestamp'],'pathClass':m.path_class(x,path),'decision':d,'baseline':b,'entry':e,'anchorContextAvailable':aid in legacy})
 return rows

def summarize(rows):
 common=[r for r in rows if r['baseline'] and r['baseline']['commonComplete']];pairs=[r for r in common if r['entry'] and r['entry']['commonComplete']];strict=[r for r in pairs if r['baseline']['strict30Complete'] and r['entry']['strict30Complete']]
 wins={}
 for k in LEVELS:
  rs=[r for r in common if r['baseline']['common']['mfe']>=k];got=sum(r['entry'] is not None and r['entry']['commonComplete'] and r['entry']['common']['mfe']>=k for r in rs)
  wins[str(k)]={'baseline':len(rs),'entered':sum(r['entry'] is not None for r in rs),'preserved':got,'missed':len(rs)-got,'rate':got/len(rs) if rs else None}
 classes={}
 for name,rs in [('IMMEDIATE_WINNER',[r for r in common if r['pathClass']=='IMMEDIATE_WINNER']),('FAST_WINNER',[r for r in common if r['baseline']['fastWinner']]),('PULLBACK_WINNER',[r for r in common if r['pathClass'] in ('PULLBACK_THEN_WINNER','DEEP_PULLBACK_THEN_WINNER')]),('DEEP_PULLBACK_THEN_WINNER',[r for r in common if r['pathClass']=='DEEP_PULLBACK_THEN_WINNER']),('CONTINUED_FAILURE',[r for r in common if r['pathClass']=='CONTINUED_FAILURE'])]:
  pr=[r for r in rs if r['entry'] and r['entry']['commonComplete']];gp=sum(r['entry']['common']['mfe']>=3 for r in pr)
  classes[name]={'n':len(rs),'entered':len(pr),'preserved3':gp,'rate3':gp/len(rs) if rs else None,'decisions':dict(collections.Counter(r['decision']['status'] for r in rs)),'firstAction':dict(collections.Counter(r['decision']['transitions'][0]['action'] if r['decision']['transitions'] else r['decision']['status'] for r in rs)),'priceImprovement':m.dist([100*(r['baseline']['price']-r['entry']['price'])/r['baseline']['price'] for r in pr]),'baselineStrict30MAE':m.dist([r['baseline']['strict30']['mae'] for r in pr if r['baseline']['strict30Complete'] and r['entry']['strict30Complete']]),'entryStrict30MAE':m.dist([r['entry']['strict30']['mae'] for r in pr if r['baseline']['strict30Complete'] and r['entry']['strict30Complete']]),'entryMFE':m.dist([r['entry']['common']['mfe'] for r in pr]),'preservation5':{'baseline':sum(r['baseline']['common']['mfe']>=5 for r in rs),'preserved':sum(r['baseline']['common']['mfe']>=5 and r['entry']['common']['mfe']>=5 for r in pr)}}
 improvement=[100*(r['baseline']['price']-r['entry']['price'])/r['baseline']['price'] for r in pairs];delays=[r['decision']['delay'] for r in rows if r['decision']['delay'] is not None];allentered=sum(r['decision']['status']=='COUNTERFACTUAL_ENTER' for r in rows);eligible=sum(r['baseline'] is not None for r in rows)
 return {'emitted':len(rows),'referenceEvaluable':eligible,'commonComplete':len(common),'commonCoverage':len(common)/len(rows) if rows else None,'enteredAll':allentered,'enteredCommon':len(pairs),'eventualEntryRateAll':allentered/len(rows) if rows else None,'eventualEntryRateReference':allentered/eligible if eligible else None,'entryCoverage':len(pairs)/len(common) if common else None,'decisions':dict(collections.Counter(r['decision']['status'] for r in rows)),'firstActions':dict(collections.Counter(r['decision']['transitions'][0]['action'] if r['decision']['transitions'] else r['decision']['status'] for r in rows)),'waitTransitions':sum(sum(t['action'] in ('WAIT','WAIT_ONE_STEP') for t in r['decision']['transitions']) for r in rows),'delay':m.dist(delays),'delayDistribution':dict(collections.Counter('EXPIRE_OR_SKIP' if r['decision']['delay'] is None else str(r['decision']['delay']) for r in rows)),'priceImprovement':m.dist(improvement),'favorableRate':sum(v>0 for v in improvement)/len(improvement) if improvement else None,'worseRate':sum(v<0 for v in improvement)/len(improvement) if improvement else None,'preservation':wins,'classes':classes,'baselineCommonMAE':m.dist([r['baseline']['common']['mae'] for r in common]),'baselinePairedMAE':m.dist([r['baseline']['common']['mae'] for r in pairs]),'entryPairedMAE':m.dist([r['entry']['common']['mae'] for r in pairs]),'baselineStrict30MAE':m.dist([r['baseline']['strict30']['mae'] for r in strict]),'entryStrict30MAE':m.dist([r['entry']['strict30']['mae'] for r in strict]),'baselinePairedMFE':m.dist([r['baseline']['common']['mfe'] for r in pairs]),'entryPairedMFE':m.dist([r['entry']['common']['mfe'] for r in pairs]),'tails':{str(k):{'baselineAll':sum(r['baseline']['common']['mae']<=-k for r in common),'baselineEnteredPair':sum(r['baseline']['common']['mae']<=-k for r in pairs),'entryPair':sum(r['entry']['common']['mae']<=-k for r in pairs),'strict30BaselinePair':sum(r['baseline']['strict30']['mae']<=-k for r in strict),'strict30EntryPair':sum(r['entry']['strict30']['mae']<=-k for r in strict)} for k in (3,5,10)},'missingEntryOutcomes':sum(r['decision']['status']=='COUNTERFACTUAL_ENTER' and (r['entry'] is None or not r['entry']['commonComplete']) for r in rows),'pathClassCounts':dict(collections.Counter(r['pathClass'] for r in rows))}

def delta(b,a,k):return a[k]-b[k] if a[k] is not None and b[k] is not None else -math.inf

def entry_gates(s,full=True):
 b=s['baselineStrict30MAE'];a=s['entryStrict30MAE'];bm=s['baselinePairedMFE']['mean'];am=s['entryPairedMFE']['mean'];tail=s['tails']['5'];pb=s['classes']['PULLBACK_WINNER']
 g={'coverage':(s['entryCoverage'] or 0)>=.70,'price':(s['priceImprovement']['mean'] if s['priceImprovement']['mean'] is not None else -math.inf)>=.10,'strict30Median':delta(b,a,'median')>=.10,'strict30P05':delta(b,a,'p05')>=.25,'deep5':tail['baselineAll']>0 and tail['entryPair']<=.9*tail['baselineAll'],'remainingMFE':bm is not None and am is not None and am>=.9*bm}
 for k,threshold in [('1',.8),('2',.85),('3',.9),('5',.9)]:g['preserve'+k]=(s['preservation'][k]['rate'] or 0)>=threshold
 for name in ('IMMEDIATE_WINNER','FAST_WINNER'):g[name]=(s['classes'][name]['rate3'] or 0)>=.9
 if full:
  g['sample']=s['commonComplete']>=100;g['pullback']=pb['n']>=10 and (pb['rate3'] or 0)>=.85 and pb['priceImprovement']['mean'] is not None and pb['priceImprovement']['mean']>=.10 and delta(pb['baselineStrict30MAE'],pb['entryStrict30MAE'],'median')>=0
 return g

def panel(rows,top3):
 s=summarize(rows);coh={k:summarize([r for r in rows if r['source']==k]) for k in (q.INITIAL,q.DIP)};dates=sorted({r['session'] for r in rows});blocks={str(i+1):summarize([r for r in rows if r['session'] in ds]) for i,ds in enumerate(np.array_split(dates,4))};ex=summarize([r for r in rows if r['symbol'] not in top3]);g=entry_gates(s)
 g['cohorts']=all(v['commonComplete']>=30 and (v['entryCoverage'] or 0)>=.60 and all((v['preservation'][k]['rate'] or 0)>=.85 for k in ('3','5')) and delta(v['baselineStrict30MAE'],v['entryStrict30MAE'],'p05')>=-.25 for v in coh.values())
 g['chronological']=sum(v['commonComplete']>=20 and all(v['preservation'][k]['baseline']==0 or (v['preservation'][k]['rate'] or 0)>=.80 for k in ('3','5')) and v['priceImprovement']['mean'] is not None and v['priceImprovement']['mean']>=0 for v in blocks.values())>=3
 g['top3Exclusion']=all(entry_gates(ex,False).values())
 freq=collections.Counter(r['symbol'] for r in rows);sf=collections.Counter(r['session'] for r in rows)
 return {'overall':s,'cohorts':coh,'blocks':blocks,'top3Excluded':ex,'gates':g,'entryGatePass':all(g.values()),'concentration':{'top3Train':top3,'symbolHHI':sum((v/len(rows))**2 for v in freq.values()) if rows else None,'sessionHHI':sum((v/len(rows))**2 for v in sf.values()) if rows else None,'uniqueSymbols':len(freq),'top10':sorted(freq.items(),key=lambda z:(-z[1],z[0]))[:10]},'sessions':{d:summarize([r for r in rows if r['session']==d]) for d in dates},'breadth':{str(k):summarize([r for r in rows if r['breadth']==k]) for k in range(1,6)},'anchorContext':{str(k):summarize([r for r in rows if r['anchorContextAvailable']==k]) for k in (False,True)},'underlyingMinuteCoverage':{str(k):summarize([r for r in rows if r['baseline'] and r['baseline']['commonComplete'] and r['baseline']['fullUnderlyingMinutes']==k]) for k in (False,True)}}

def economic(rows,opmap,paths,top3):
 """Called only for Entry-gate survivors. Exact frozen A, no tuning."""
 runtime=c.module('v2_exact_fixed12',c.RUNTIME);ledger=[];unknown=[]
 for r in rows:
  if not r['baseline'] or not r['baseline']['commonComplete']:continue
  x=opmap[r['id']];path=paths[x['op']['anchorId']];b=m.eval_entry(x,path,0,runtime);e=m.eval_entry(x,path,r['decision']['delay'],runtime) if r['decision']['delay'] is not None else None
  if b['candidateA'] is None or (r['decision']['delay'] is not None and (e is None or e['candidateA'] is None)):
   unknown.append(r['id']);continue
  def enrich(z,delay):
   if z is None:return None
   ev=m.episode(x,path,delay);a=z['candidateA'];n=a['exitBar'];held=ev['future'][:n if a['status']=='FIXED12_FALLBACK' else n-1];execution=ev['future'][n-1]
   return {'net':a['netPct'],'reason':a['status'],'holdingMinutes':(c.minute(execution['end']) if a['status']=='FIXED12_FALLBACK' else c.minute(execution['start']))-ev['startMinute'],'MAE':min([0]+[v['l'] for v in held]+([execution['o']] if a['status']=='PROTECT_EXIT' else [])),'MFE':max([0]+[v['h'] for v in held]+([execution['o']] if a['status']=='PROTECT_EXIT' else [])),'result':a,'fixed':z['fixed']}
  ledger.append({'id':r['id'],'session':r['session'],'source':r['source'],'symbol':r['symbol'],'baseline':enrich(b,0),'entry':enrich(e,r['decision']['delay']) if e else None})
 def metrics(rs):
  base=[r['baseline']['net'] for r in rs];pol=[r['entry']['net'] if r['entry'] else 0 for r in rs];pair=[r for r in rs if r['entry']]
  return {'n':len(rs),'entered':len(pair),'baseline':m.perf(base),'policyCashIncluded':m.perf(pol),'delta':m.dist([y-x for x,y in zip(base,pol)]),'enteredBaseline':m.perf([r['baseline']['net'] for r in pair]),'enteredPolicy':m.perf([r['entry']['net'] for r in pair]),'hold':m.dist([r['entry']['holdingMinutes'] for r in pair]),'MFE':m.dist([r['entry']['MFE'] for r in pair]),'MAE':m.dist([r['entry']['MAE'] for r in pair])}
 s=metrics(ledger);coh={k:metrics([r for r in ledger if r['source']==k]) for k in (q.INITIAL,q.DIP)};dates=sorted({r['session'] for r in rows});blocks={str(i+1):metrics([r for r in ledger if r['session'] in ds]) for i,ds in enumerate(np.array_split(dates,4))};ex=metrics([r for r in ledger if r['symbol'] not in top3]);den=sum(bool(r['baseline'] and r['baseline']['commonComplete']) for r in rows)
 g={'coverage':len(ledger)>=.9*den,'mean':s['delta']['mean'] is not None and s['delta']['mean']>=.05,'PF':delta(s['baseline'],s['policyCashIncluded'],'PF')>=0,'p05':delta(s['baseline'],s['policyCashIncluded'],'p05')>=0,'cohorts':all(v['delta']['mean'] is not None and v['delta']['mean']>=0 for v in coh.values()),'blocks':sum(v['delta']['mean'] is not None and v['delta']['mean']>=0 for v in blocks.values())>=3,'top3':ex['delta']['mean'] is not None and ex['delta']['mean']>0}
 return ledger,{'overall':s,'cohorts':coh,'blocks':blocks,'top3Excluded':ex,'unknownIdentities':unknown,'gates':g,'pass':all(g.values())}

def train_monitor(rows):
 s=summarize(rows);g={k:(s['entryCoverage'] or 0)>=.5 if k=='coverage' else (s['preservation'][k]['rate'] or 0)>=.5 for k in ('coverage','3','5')}
 return {'summary':s,'gates':g,'pass':all(g.values())}

def run(outdir):
 out=Path(outdir)
 if out.exists():raise FileExistsError(out)
 p,ops,paths,selectors,legacy=sources();out.mkdir(parents=True);opmap={x['id']:x for x in ops}
 train=[x for x in ops if x['session'] in p['split']['TRAIN']];val=[x for x in ops if x['session'] in p['split']['VALIDATION']];tf=collections.Counter(x['symbol'] for x in train);top3=[k for k,v in sorted(tf.items(),key=lambda z:(-z[1],z[0]))[:3]]
 tr=training(train,paths,selectors,legacy);assert set(r['session'] for r in tr)<=set(p['split']['TRAIN']);m.write(out/'training-teacher-ledger.json.gz',tr)
 teacher={'states':len(tr),'episodes':len({r['id'] for r in tr}),'waitStates':sum(r['labels']['waitAdvantage'] is not None for r in tr),'waitLabels':m.dist([r['labels']['waitAdvantage'] for r in tr]),'skipLabels':m.dist([r['labels']['skipAdvantage'] for r in tr]),'fastWinnerLabels':dict(collections.Counter(r['labels']['fastWinner'] for r in tr)),'noFutureBestLabels':True,'waitStepMinutes':5,'TRAIN_only':True}
 results={};models={};monitor={};validation={};baselines={};selected=None;economicCalls=0
 for name in ('B0_IMMEDIATE','B1_FIXED_WAIT_1'):
  rs=measure(val,paths,selectors,legacy,baseline=name);baselines[name]=panel(rs,top3);m.write(out/(name.lower()+'.json.gz'),rs)
 for kind in ('LINEAR','TREE'):
  old=m.read(m.BASE/'measurement'/('validation-'+kind.lower()+'.json.gz'));saved={r['id']:r for r in old};assert set(saved)=={x['id'] for x in val};rs=measure(val,paths,selectors,legacy,saved=saved);baselines['B2_V1_'+kind]=panel(rs,top3)
 # Fit, monitor, and assess each precommitted architecture in fixed order.
 for name in KINDS:
  if name=='S3_GUARDED_LINEAR':
   linear=models['S1_LINEAR'];model=Sequential(name,linear.wait,linear.skip,fit_guard(tr,linear))
  else:
   heads=fit_heads(tr,'LINEAR' if name=='S1_LINEAR' else 'TREE');model=Sequential(name,*heads)
  models[name]=model;m.write(out/(name.lower()+'-model.json'),model.dump())
  trs=measure(train,paths,selectors,legacy,model);mon=train_monitor(trs);monitor[name]=mon;m.write(out/(name.lower()+'-train.json.gz'),trs)
  if not mon['pass']:
   results[name]={'status':'KILL_TRAIN_ABSTENTION_OR_WINNER_LOSS','validationOpened':False,'entry':None,'economic':None};continue
  rs=measure(val,paths,selectors,legacy,model);validation[name]=rs;v=panel(rs,top3);m.write(out/(name.lower()+'-validation.json.gz'),rs);econ=None
  if v['entryGatePass']:
   el,econ=economic(rs,opmap,paths,top3);economicCalls+=1;m.write(out/(name.lower()+'-economic.json.gz'),el)
  passed=v['entryGatePass'] and econ['pass']
  results[name]={'status':'KEEP_VALIDATION' if passed else 'KILL_ENTRY_GATE' if not v['entryGatePass'] else 'KILL_ECONOMIC_GATE','validationOpened':True,'entry':v,'economic':econ}
  if passed and selected is None:selected=name
 test=None
 if selected:
  ts=[x for x in ops if x['session'] in p['split']['DEVELOPMENT_TEST']];rs=measure(ts,paths,selectors,legacy,models[selected]);v=panel(rs,top3);m.write(out/'development-test.json.gz',rs);econ=None
  if v['entryGatePass']:
   el,econ=economic(rs,opmap,paths,top3);economicCalls+=1;m.write(out/'development-test-economic.json.gz',el)
  test={'entry':v,'economic':econ,'pass':bool(v['entryGatePass'] and econ and econ['pass'])}
 passed=bool(test and test['pass']);status='COMPREHENSIVE_LONG_ENTRY_V2_DEVELOPMENT_PASS' if passed else 'COMPREHENSIVE_LONG_ENTRY_V2_DEVELOPMENT_LIMIT_REACHED'
 allrs=[r for rs in validation.values() for r in rs]
 s={'status':status,'freeze':'DEVELOPMENT_FROZEN_NOT_FRESH_VALIDATED' if passed else 'DO_NOT_FREEZE','protocolCommit':PROTOCOL_COMMIT,'population':{'opportunities':len(ops),'sessions':76,'splitCounts':{k:sum(x['session'] in ds for x in ops) for k,ds in p['split'].items()},'sourceCounts':dict(collections.Counter(x['op']['eventType'] for x in ops))},'teacher':teacher,'trainMonitoring':monitor,'baselines':baselines,'candidates':results,'selected':selected,'developmentTest':test,'developmentTestOpened':selected is not None,'safety':p['safety'],'freshOOSOpened':False,'audit':{'featureCount':len(m.FEATURES),'candidatePolicies':3,'supervisedFits':5,'economicCohortEvaluations':economicCalls,'capitalSimulations':0,'noOracleMax':True,'noFutureFeatures':True,'sourcePinsVerified':True,'noReentryWithinEpisode':all(sum(t['action']=='BUY_NOW' for t in r['decision']['transitions'])<=1 for r in allrs),'testEvaluationCount':int(selected is not None),'runtime':{'python':platform.python_version(),'numpy':np.__version__,'sklearn':m.sklearn.__version__}}}
 m.write(out/'summary.json',s)
 if passed:m.write(out/'development-freeze.json',{'status':'DEVELOPMENT_FROZEN_NOT_FRESH_VALIDATED','candidate':selected,'modelSHA256':m.sha(out/(selected.lower()+'-model.json')),'protocolSHA256':m.sha(BASE/'protocol.json'),'sourcePins':p['sourcePins'],'safety':p['safety'],'freshOOSOpened':False})
 m.write(out/'manifest.json',{'protocolCommit':PROTOCOL_COMMIT,'protocolSHA256':m.sha(BASE/'protocol.json'),'sourcePins':p['sourcePins'],'codeSHA256':m.sha(__file__),'outputs':{f.name:m.sha(f) for f in sorted(out.iterdir())},'safety':p['safety']})
 print(json.dumps({'status':status,'selected':selected,'economicCalls':economicCalls,'testOpened':s['developmentTestOpened'],'teacher':teacher,'candidates':{k:{'status':v['status'],'trainCoverage':monitor[k]['summary']['entryCoverage'],'validation':None if v['entry'] is None else {'gates':v['entry']['gates'],'coverage':v['entry']['overall']['entryCoverage'],'preservation':v['entry']['overall']['preservation'],'price':v['entry']['overall']['priceImprovement']['mean']}} for k,v in results.items()}},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();run(a.out)
