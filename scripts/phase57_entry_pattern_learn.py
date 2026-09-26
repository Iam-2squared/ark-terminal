"""Bounded Entry-quality / continuation research. Frozen split and candidate set."""
import argparse,collections,gzip,json,math,time
from pathlib import Path
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from scripts import phase57_entry_pattern_v2 as e
read,write,sha=e.read,e.write,e.sha
WEIGHTS=np.array([1.,.15,.3,.2])

def quality(lab,delay,upside=.15):
 if not lab or any(lab['30'].get(k) is None for k in ['returnNet','MFE','MAE','MaxDD']):return None
 z=lab['30'];return z['returnNet']+upside*min(z['MFE'],10)+.3*z['MAE']+.2*z['MaxDD']-.002*delay

def make_targets(rows,labs):
 n=len(rows);Y=np.full((n,5),np.nan);by=collections.defaultdict(list)
 for i,r in enumerate(rows):
  by[r['opportunity']].append(i);l=labs[r['id']]['labels']
  if l and l['30']['status']=='COMPLETE':Y[i,:4]=[l['30']['returnNet'],min(l['30']['MFE'],10),l['30']['MAE'],l['30']['MaxDD']]
 for ix in by.values():
  for ii,i in enumerate(ix):
   future=[j for j in ix[ii+1:] if rows[j]['eligible1'] and rows[j]['quoteAvailable'] and labs[rows[j]['id']]['price'] is not None]
   # Continuation is an explicit optimistic realized-best label, never an executable oracle.
   # Unknown feasible future rewards censor the continuation target, not zero-impute them.
   if any(not np.all(np.isfinite(Y[j,:4])) for j in future):continue
   Y[i,4]=max([0.]+[float(Y[j,:4]@WEIGHTS-.002*rows[j]['delay']) for j in future])
 return Y

def fit_predict(X,Y,fitmask,cols,family):
 # Fit statistics only from fit55 days, no selection/evaluation labels.
 A=X[:,cols].astype(float);F=A[fitmask];med=[]
 for j in range(A.shape[1]):
  v=F[:,j];v=v[np.isfinite(v)];med.append(float(np.median(v)) if len(v) else 0.)
 med=np.array(med);missing=~np.isfinite(A);A=np.where(missing,med,A);A=np.c_[A,missing.astype(float)]
 mean=A[fitmask].mean(0);sd=A[fitmask].std(0);sd[sd<1e-8]=1;A=(A-mean)/sd
 pred=np.empty((len(X),5));models=[]
 for k in range(5):
  ix=fitmask&np.isfinite(Y[:,k]);assert ix.sum()>=100,'INSUFFICIENT_FIT_TARGET'
  a=A[ix];y=Y[ix,k]
  if family=='RIDGE':
   center=a.mean(0);yc=y.mean();ac=a-center;coef=np.linalg.solve(ac.T@ac+10*np.eye(a.shape[1]),ac.T@(y-yc));pred[:,k]=(A-center)@coef+yc
   models.append({'target':k,'n':int(ix.sum()),'coef':coef.tolist(),'center':center.tolist(),'intercept':float(yc)})
  else:
   m=HistGradientBoostingRegressor(max_iter=60,max_leaf_nodes=7,min_samples_leaf=100,l2_regularization=10,learning_rate=.05,early_stopping=False,random_state=5709202).fit(a,y);pred[:,k]=m.predict(A)
   nodes=[[{name:(int(z[name]) if np.issubdtype(z.dtype[name],np.integer) else float(z[name])) for name in z.dtype.names} for z in tree[0].nodes] for tree in m._predictors]
   models.append({'target':k,'n':int(ix.sum()),'baseline':m._baseline_prediction.tolist(),'nodes':nodes})
 return pred,{'family':family,'columns':cols,'medians':med.tolist(),'mean':mean.tolist(),'std':sd.tolist(),'heads':models}

def predict_saved(X,model):
 A=X[:,model['columns']].astype(float);missing=~np.isfinite(A);A=np.where(missing,np.array(model['medians']),A);A=np.c_[A,missing.astype(float)];A=(A-np.array(model['mean']))/np.array(model['std']);pred=np.empty((len(A),5))
 for h in model['heads']:
  k=h['target']
  if model['family']=='RIDGE':pred[:,k]=(A-np.array(h['center']))@np.array(h['coef'])+h['intercept']
  else:
   ys=[]
   for x in A:
    val=h['baseline'][0][0]
    for tree in h['nodes']:
     i=0
     while not tree[i]['is_leaf']:
      n=tree[i];i=n['left'] if x[n['feature_idx']]<=n['num_threshold'] else n['right']
     val+=tree[i]['value']
    ys.append(val)
   pred[:,k]=ys
 return pred

def replay(opps,rows,labs,pred,mode,step=1,wait=0):
 by=collections.defaultdict(list)
 for i,r in enumerate(rows):by[r['opportunity']].append((i,r))
 ans=[]
 for o in opps:
  logs=[];chosen=None
  for i,r in by[o['id']]:
   if not r['eligible1'] or (step==5 and not r['eligible5']):continue
   if not r['quoteAvailable']:logs.append({'minute':r['minute'],'state':'STALE_OR_MISSING_REFERENCE'});continue
   q=float(pred[i,:4]@WEIGHTS-.002*r['delay']) if pred is not None else None
   continuation=max(0.,float(pred[i,4])) if pred is not None else None
   buy=r['delay']>=wait if mode=='BASE' else q>=0 and (mode=='QUALITY' or q>=continuation)
   if not buy:logs.append({'minute':r['minute'],'state':'MODEL_WAIT' if pred is not None else 'FIXED_WAIT'});continue
   if labs[r['id']]['price'] is None:logs.append({'minute':r['minute'],'state':'BUY_ATTEMPT_UNFILLED','reason':'NO_SOURCE_TRADE'});continue
   chosen=r;logs.append({'minute':r['minute'],'state':'BUY','qualityPrediction':q,'continuationPrediction':continuation});break
  reason=None if chosen else 'SESSION_BOUNDARY' if not o['v2grid'] or (o['v2grid'] and e.elapsed(o['session'],e.old.minute(o['origin']['decisionTimestamp']),o['v2grid'][-1])<30) else 'MONITOR_BUDGET'
  if not chosen:logs.append({'state':'EXPIRED','reason':reason})
  ans.append({'opportunity':o['id'],'symbol':o['symbol'],'session':o['session'],'entryId':chosen['id'] if chosen else None,'delay':chosen['delay'] if chosen else None,'attempts':logs,'expireReason':reason})
 return ans

def metrics(opps,trades,labs):
 # All opportunities remain in fixed-population capture and throughput denominators.
 ent=[t for t in trades if t['entryId']];caps=e.ext.capture(opps,trades,labs);result={'opportunities':len(opps),'BUY':len(ent),'enterPerSession':len(ent)/max(1,len({o['session'] for o in opps})),'capture':caps,'noEntry':len(opps)-len(ent),'delay':e.ext.distribution(t['delay'] for t in ent),'entryPriceImprovement':e.ext.distribution(labs[t['entryId']]['improvementPct'] for t in ent),'reasons':dict(collections.Counter(a['state'] for t in trades for a in t['attempts'])),'decisionEvaluations':sum(a['state']!='EXPIRED' for t in trades for a in t['attempts'])}
 for h in ['30','60']:
  ls=[labs[t['entryId']]['labels'][h] for t in ent];result[h]={'hit':e.ext.hit_rates(ls),'coverage':dict(collections.Counter(z['status'] for z in ls))}
  for k in ['MFE','MAE','MaxDD','returnNet']:result[h][k]=e.ext.distribution(z[k] for z in ls)
 for k in ['mfeEnd','maeEnd','returnEnd','timeToHigh','timeToLow','timeToRecovery','timeToUpside']:result[k]=e.ext.distribution(labs[t['entryId']]['labels'].get(k) for t in ent)
 for level in [3,5]:
  winners={o['id'] for o in opps if o['selectorOutcome']['mfeEnd'] is not None and o['selectorOutcome']['mfeEnd']>=level and o['selectorOutcome']['order']=='LOW_THEN_HIGH'}
  hit=sum(t['opportunity'] in winners and labs[t['entryId']]['labels']['mfeEnd'] is not None and labs[t['entryId']]['labels']['mfeEnd']>=level for t in ent)
  result['capture'][str(level)]['lowThenHigh']={'denominator':len(winners),'captured':hit,'pct':100*hit/len(winners) if winners else None}
 us=[quality(labs[t['entryId']]['labels'],t['delay']) for t in ent];result['populationQuality']=sum(x for x in us if x is not None)/max(1,len(opps));result['qualityUnknown']=sum(x is None for x in us)
 result['badBuy']={'negativeReturn30':sum(labs[t['entryId']]['labels']['return30'] is not None and labs[t['entryId']]['labels']['return30']<0 for t in ent),'mae30BelowMinus2':sum(labs[t['entryId']]['labels']['mae30'] is not None and labs[t['entryId']]['labels']['mae30']<=-2 for t in ent)}
 return result

def measure(substrate,prior,output):
 p=e.verify();src=Path(substrate);out=Path(output);out.mkdir(parents=True,exist_ok=False)
 for name,h in read(src/'manifest.json').items():assert sha(src/name)==h
 assert read(src/'p0-audit.json')['status']=='PASS'
 rows=read(src/'rows.json.gz');labs=read(src/'outcomes.json.gz');opps=read(src/'opportunities.json.gz');names=read(src/'names.json')
 arrays=[]
 for day in p['sessions']:
  with gzip.open(src/(day+'.npy.gz'),'rb') as fh:a=np.load(fh,allow_pickle=False)
  if a.shape[1]:arrays.append(a)
 X=np.vstack(arrays);assert len(X)==len(rows);Y=make_targets(rows,labs)
 fit=np.array([r['session'] in p['fit'] and r['eligible1'] and r['quoteAvailable'] and labs[r['id']]['price'] is not None for r in rows]);selection=[o for o in opps if o['session'] in p['selection']];ev=[o for o in opps if o['session'] in p['evaluation']]
 # Explicit model plan before evaluation. No dictionary or pattern-memory lookup in primary.
 cols=list(range(len(names)));preds={};models={}
 plan=[('RIDGE_FULL','RIDGE',cols),('TREE_FULL','TREE',cols),('RIDGE_NO_SEQUENCE','RIDGE',[i for i,n in enumerate(names) if not n.startswith('SEQ_')]),('RIDGE_NO_PREVIOUS','RIDGE',[i for i,n in enumerate(names) if not n.startswith(('PREV','SEQ_PREV','RVOL'))]),('RIDGE_NO_RECENT','RIDGE',[i for i,n in enumerate(names) if not n.startswith('RECENT/')])]
 for key,family,cc in plan:
  pred,model=fit_predict(X,Y,fit,cc,family);np.testing.assert_allclose(predict_saved(X[:10],model),pred[:10],rtol=1e-10,atol=1e-10);preds[key]=pred;models[key]=model;print(json.dumps({'fit':key,'fitRows':int(fit.sum()),'features':len(cc)}),flush=True)
 choices={};sel={}
 for family in ['RIDGE_FULL','TREE_FULL']:
  for mode in ['QUALITY','STOP']:
   key=family+'_'+mode;ts=replay(selection,rows,labs,preds[family],mode);sel[key]=metrics(selection,ts,labs)
 def score(key):
  z=sel[key];b=replay(selection,rows,labs,None,'BASE');base=metrics(selection,b,labs)
  qualified=all(z['capture'][str(t)]['rate'] is not None and z['capture'][str(t)]['rate']>=90 for t in [3,5]) and z['BUY']>=.9*base['BUY']
  return (qualified,z['populationQuality']-.5*sum((z['capture'][str(t)]['missed']/max(z['capture'][str(t)]['selectorWinnerDenominator'],1)) for t in [3,5]),key.startswith('RIDGE'),key.endswith('STOP'))
 chosen=max(sel,key=score);write(out/'selection-lock.json',{'selected':chosen,'selection':sel,'fit':p['fit'],'selectionDates':p['selection'],'evaluationUnused':True,'qualificationPassed':score(chosen)[0]})
 result={};alltrades={}
 for step in [1,5]:
  for wait in [0,5,10,15,30]:
   key=f'B0_RETRY_{step}m' if wait==0 else f'B1_WAIT{wait}_{step}m';alltrades[key]=replay(ev,rows,labs,None,'BASE',step,wait)
  for family in ['RIDGE_FULL','TREE_FULL']:
   for mode in ['QUALITY','STOP']:alltrades[family+'_'+mode+f'_{step}m']=replay(ev,rows,labs,preds[family],mode,step)
 for family in ['RIDGE_NO_SEQUENCE','RIDGE_NO_PREVIOUS','RIDGE_NO_RECENT']:alltrades[family+'_STOP_1m']=replay(ev,rows,labs,preds[family],'STOP')
 oldtr=read(Path(prior)/'measurement/trades.json.gz')['E5'];alltrades['B2_E5_V1_PRESERVED']=[{**t,'attempts':[{'state':a.get('action',a.get('reason')),'v1Reason':a.get('reason'),'minute':a.get('minute')} for a in t['attempts']]} for t in oldtr]
 # No change to v1 timestamps, fill prices or full-session capture; active horizon is a new diagnostic only.
 oldlabs=read(Path(prior)/'substrate/outcomes.json.gz')
 for t in oldtr:
  if t['entryId']:
   assert e.ext.same(labs[t['entryId']]['price'],oldlabs[t['entryId']]['price'])
   assert e.ext.same(labs[t['entryId']]['labels']['mfeEnd'],oldlabs[t['entryId']]['labels']['mfeEnd'])
 for key,ts in alltrades.items():result[key]=metrics(ev,ts,labs)
 oldmetrics=read(Path(prior)/'measurement/metrics.json')['E5']
 for t in ['1','2','3','5']:assert e.ext.same(result['B2_E5_V1_PRESERVED']['capture'][t]['rate'],oldmetrics['capture'][t]['pct'])
 chosenKey=chosen+'_1m';base=result['B0_RETRY_1m'];z=result[chosenKey]
 gate={'status':'ENTRY_V2_DEVELOPMENT_COMPARISON_COMPLETE_NOT_PROMOTED','selected':chosenKey,'opportunityPreservation90':all((z['capture'][str(t)]['rate'] or 0)>=90 for t in [3,5]),'throughput90OfRetry':z['BUY']>=.9*base['BUY'],'noAutomaticPromotion':True,'holdoutOpened':0,'safety':p['safety'],'continuationCaveat':'Supervised expectation of realized-best future utility is an optimistic continuation proxy, not a solved Bellman policy or executable oracle.'}
 gate['performanceJudgment']='ENTRY_DEVELOPMENT_INCONCLUSIVE' if not gate['opportunityPreservation90'] or not gate['throughput90OfRetry'] else 'REQUIRES_PAIRED_FIXED_POPULATION_STABILITY_REVIEW_NO_AUTOMATIC_SUCCESS'
 sessions=[]
 for day in p['evaluation']:
  oo=[o for o in ev if o['session']==day]
  if not oo:continue
  for key in ['B0_RETRY_1m','B0_RETRY_5m','B2_E5_V1_PRESERVED',chosenKey]:sessions.append({'session':day,'arm':key,**metrics(oo,[t for t in alltrades[key] if t['session']==day],labs)})
 # Good/bad anatomy, fixed criteria, never model selection inputs.
 anatomy={split:{'sampleRows':sum(r['session'] in ds for r in rows),'complete30':sum(r['session'] in ds and np.isfinite(Y[i,0]) for i,r in enumerate(rows)),'good':sum(r['session'] in ds and np.all(np.isfinite(Y[i,:4])) and Y[i,0]>0 and Y[i,1]>=2 and Y[i,2]>-1 for i,r in enumerate(rows)),'bad':sum(r['session'] in ds and np.isfinite(Y[i,0]) and (Y[i,0]<0 or Y[i,2]<=-2) for i,r in enumerate(rows))} for split,ds in [('fit',p['fit']),('selection',p['selection']),('evaluation',p['evaluation'])]}
 sensitivity={str(w):e.ext.distribution(quality(labs[t['entryId']]['labels'],t['delay'],w) for t in alltrades[chosenKey] if t['entryId']) for w in [0,.15,.3]}
 attribution={key:sorted([{'feature':names[c],'absoluteBuyUtilityWeight':float(sum(abs(np.array(model['heads'][k]['coef'])[j]*WEIGHTS[k]) for k in range(4)))} for j,c in enumerate(model['columns'])],key=lambda x:-x['absoluteBuyUtilityWeight'])[:30] for key,model in models.items() if model['family']=='RIDGE'}
 for name,data in [('metrics.json',result),('trades.json.gz',alltrades),('models.json.gz',models),('decisions.json',gate),('session-metrics.json',sessions),('anatomy.json',anatomy),('weight-sensitivity.json',sensitivity),('attribution.json',attribution)]:write(out/name,data)
 # Scores and targets stored evaluator-only, with stable numeric array bytes.
 for name,a in [('predictions',np.stack(list(preds.values()))),('targets',Y)]:
  with (out/(name+'.npy.gz')).open('wb') as fh:
   with gzip.GzipFile(fileobj=fh,mode='wb',mtime=0,filename='') as gz:np.save(gz,a,allow_pickle=False)
 write(out/'prediction-order.json',list(preds));write(out/'manifest.json',{x.name:sha(x) for x in sorted(out.iterdir())})

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--substrate',required=True);a.add_argument('--prior',required=True);a.add_argument('--output',required=True);x=a.parse_args();measure(x.substrate,x.prior,x.output)
