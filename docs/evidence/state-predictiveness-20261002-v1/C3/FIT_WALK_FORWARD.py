"""Finite precommitted weighted linear baselines; no engine or provider imports."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,datetime,hashlib,json,math
import numpy as np
from scipy.stats import spearmanr
R=Path(__file__).resolve().parent
FITS=0
def fit_ledger(kind,**fields):
 with (R/'MODEL_EXECUTION_LEDGER.jsonl').open('a') as f:f.write(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':kind,**fields},sort_keys=True)+'\n')
def save(n,x):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def csvout(name,rows):
 p=R/name;p.parent.mkdir(parents=True,exist_ok=True)
 if not rows:return
 keys=list(dict.fromkeys(k for row in rows for k in row))
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def encode_prob(a):
 x=np.maximum(np.asarray(a,dtype=float),1e-12);return x/x.sum(axis=1,keepdims=True)
def weights(rows):
 dates=Counter(r['date'] for r in rows);pairs=Counter((r['date'],r['security_id'],r['session_id']) for r in rows)
 perdate=Counter(d for d,s,x in pairs)
 a=np.array([1/(len(dates)*perdate[r['date']]*pairs[(r['date'],r['security_id'],r['session_id'])]) for r in rows]);return a/a.mean()
class Encoder:
 def __init__(self,rows,model,schema):
  self.num=schema['numeric_state']+(schema['numeric_path'] if model=='B3' else [])
  self.cat=schema['categorical_state']+(schema['categorical_path'] if model=='B3' else [])
  w=weights(rows);self.stats={};self.voc={};self.names=[]
  for name in self.num:
   vals=np.array([np.nan if r['features'][name] is None else r['features'][name] for r in rows],dtype=float);ok=np.isfinite(vals)
   mean=float(np.sum(vals[ok]*w[ok])/w[ok].sum()) if ok.any() else 0.0
   var=float(np.sum((vals[ok]-mean)**2*w[ok])/w[ok].sum()) if ok.any() else 0.0
   scale=math.sqrt(var) if var>0 else 1.0;self.stats[name]=[mean,scale];self.names.extend([name,name+'__missing'])
  for name in self.cat:
   self.voc[name]=sorted({r['features'][name] for r in rows});self.names.extend(name+'='+s for s in self.voc[name])
 def transform(self,rows):
  columns=[]
  for name in self.num:
   mean,scale=self.stats[name];a=np.array([np.nan if r['features'][name] is None else r['features'][name] for r in rows],dtype=float);miss=~np.isfinite(a)
   columns.extend([np.where(miss,0,(a-mean)/scale),miss.astype(float)])
  for name in self.cat:
   for value in self.voc[name]:columns.append(np.array([r['features'][name]==value for r in rows],dtype=float))
  return np.column_stack(columns) if columns else np.empty((len(rows),0))
 def data(self):return dict(numeric=self.num,categorical=self.cat,stats=self.stats,vocab=self.voc,columns=self.names)
def ridge(X,Y,w,alpha):
 global FITS;FITS+=1
 fit_ledger('FIT_RIDGE_STARTED',new_fit_count=FITS,rows=len(X),columns=X.shape[1],outputs=Y.shape[1],alpha=alpha)
 z=np.column_stack([np.ones(len(X)),X]);sw=w.sum();A=(z.T*w)@z/sw;A+=np.diag([0.0]+[alpha]*(z.shape[1]-1));B=(z.T*w)@Y/sw
 return np.linalg.solve(A,B)
def ridge_predict(X,coef):return np.column_stack([np.ones(len(X)),X])@coef
def baseline(rows,Y,model):
 global FITS;FITS+=1
 fit_ledger('FIT_BASELINE_STARTED',new_fit_count=FITS,rows=len(rows),outputs=Y.shape[1],family=model)
 w=weights(rows);mean=np.sum(Y*w[:,None],axis=0)/w.sum();lookup={}
 if model=='B1':
  cats=sorted({r['features']['formal_primary'] for r in rows})
  for c in cats:
   ids=np.array([r['features']['formal_primary']==c for r in rows]);mass=w[ids].sum();lookup[c]=((np.sum(Y[ids]*w[ids,None],axis=0)+10*mean)/(mass+10)).tolist()
 return {'mean':mean.tolist(),'lookup':lookup,'alpha':10 if model=='B1' else None}
def baseline_predict(rows,fit):return np.array([fit['lookup'].get(r['features']['formal_primary'],fit['mean']) for r in rows])
def blocks(dates):
 assert len(dates)>=6,'INSUFFICIENT_DATES_FOR_FIXED_FOLDS'
 remaining=dates[3:];q,r=divmod(len(remaining),3);out=[];cursor=0
 for k in range(3):
  n=q+(k<r);test=remaining[cursor:cursor+n];cursor+=n
  out.append({'fold':k+1,'test_dates':test,'train_dates':[d for d in dates if d<test[0]],'inner_validation_date':None if not test else [d for d in dates if d<test[0]][-1]})
 return out
def weighted_loss(rows,y,p):
 if not rows:return math.inf
 w=weights(rows);return float(np.sum(w*(y-p)**2)/w.sum())
def fit_one(train,test,Y,model,fold,schema,task_key,secondary=False):
 path=R/'FITTED'/f"{task_key}_{model}_F{fold['fold']}.json"
 hashes={'train_feature_SHA256':hashlib.sha256(json.dumps([[r['row_key'],r['features']] for r in train],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'test_feature_SHA256':hashlib.sha256(json.dumps([[r['row_key'],r['features']] for r in test],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'train_target_matrix_SHA256':hashlib.sha256(Y.astype('<f8').tobytes()).hexdigest(),'model_plan_SHA256':digest(R/'MODEL_PLAN.json')}
 if path.exists():
  fit=json.loads(path.read_text());assert all(fit[k]==v for k,v in hashes.items()),'RETAINED_FIT_INPUT_IDENTITY_CHANGED'
  if model in ['B0','B1']:prediction=baseline_predict(test,fit)
  else:
   e=fit['encoder'];enc=Encoder.__new__(Encoder);enc.num=e['numeric'];enc.cat=e['categorical'];enc.stats=e['stats'];enc.voc=e['vocab'];enc.names=e['columns'];prediction=ridge_predict(enc.transform(test),np.array(fit['coefficients']))
  fit_ledger('EXISTING_FIT_REPLAY_NO_REFIT',path=str(path.relative_to(R)),SHA256=digest(path))
  return prediction,str(path.relative_to(R))
 if model in ['B0','B1']:
  f=baseline(train,Y,model);pred=baseline_predict(test,f);fit={'family':model,**f,'columns':[]}
 else:
  last=max(r['date'] for r in train);inner=[i for i,r in enumerate(train) if r['date']<last];val=[i for i,r in enumerate(train) if r['date']==last]
  grid=[];alpha=0.1
  if not secondary:
   assert inner and val,'INNER_PAST_SPLIT_UNAVAILABLE'
   tr=[train[i] for i in inner];va=[train[i] for i in val];enc=Encoder(tr,model,schema);X=enc.transform(tr);VX=enc.transform(va)
   for a in [0.01,0.1,1.0]:
    c=ridge(X,Y[inner],weights(tr),a);prediction=ridge_predict(VX,c)[:,0];loss=weighted_loss(va,Y[val,0],prediction);grid.append({'alpha':a,'continuous_validation_MSE':loss})
   alpha=min(grid,key=lambda x:(x['continuous_validation_MSE'],-x['alpha']))['alpha']
  enc=Encoder(train,model,schema);coef=ridge(enc.transform(train),Y,weights(train),alpha);pred=ridge_predict(enc.transform(test),coef)
  fit={'family':model,'alpha':alpha,'validation_grid':grid,'encoder':enc.data(),'coefficients':coef.tolist()}
 fit.update(fold=fold['fold'],train_dates=fold['train_dates'],test_dates=fold['test_dates'],train_key_SHA256=hashlib.sha256('\n'.join(r['row_key'] for r in train).encode()).hexdigest(),train_row_N=len(train),test_row_N=len(test),task=task_key)
 fit.update(hashes);save(str(path.relative_to(R)),fit)
 return pred,str(path.relative_to(R))
def metric(rows):
 y=np.array([r['y'] for r in rows]);p=np.array([r['prediction'] for r in rows]);q=np.array([[r['p_negative'],r['p_zero'],r['p_positive']] for r in rows]);classes=np.array([r['direction']+1 for r in rows]);pred=q.argmax(axis=1)
 per=defaultdict(list)
 for i,r in enumerate(rows):per[r['date']].append(i)
 date_mse=[float(np.mean((y[ids]-p[ids])**2)) for ids in per.values()];date_mae=[float(np.mean(abs(y[ids]-p[ids]))) for ids in per.values()]
 ic=None if len(set(y))<2 or len(set(p))<2 else float(spearmanr(y,p).statistic)
 if ic is not None and not math.isfinite(ic):ic=None
 return {'row_N':len(rows),'date_N':len(per),'security_N':len({r['security_id'] for r in rows}),'security_session_N':len({(r['security_id'],r['session_id']) for r in rows}),'run_N':len({r['run_id'] for r in rows if r['run_id']}),'MAE':float(np.mean(abs(y-p))),'MSE':float(np.mean((y-p)**2)),'date_equal_MAE':float(np.mean(date_mae)),'date_equal_MSE':float(np.mean(date_mse)),'Spearman_IC':ic,'accuracy':float(np.mean(pred==classes)),'balanced_accuracy':float(np.mean([np.mean(pred[classes==c]==c) for c in sorted(set(classes))])),'regression_sign_accuracy':float(np.mean(np.sign(p)==(classes-1))),'Brier':float(np.mean(np.sum((q-np.eye(3)[classes])**2,axis=1))),'log_loss':float(np.mean(-np.log(q[np.arange(len(rows)),classes])))}
def main():
 manifest=json.loads((R/'RECEIVED_DEVELOPMENT/DATASET_MANIFEST.json').read_text());schema=json.loads((R/'FEATURE_SCHEMA.json').read_text());labels={};features=[]
 for p in manifest['pairs']:
  pid=p['pair_id'];f=R/'RECEIVED_DEVELOPMENT/FEATURES'/f'{pid}.jsonl';assert digest(f)==p['feature_SHA256']
  features.extend(json.loads(l) for l in f.read_text().splitlines())
  for l in (R/'LABELS'/f'{pid}.jsonl').read_text().splitlines():
   row=json.loads(l);assert row['row_key'] not in labels;labels[row['row_key']]=row
 features.sort(key=lambda r:r['row_key']);assert len(labels)==len(features)
 dates=sorted({p['date'] for p in manifest['pairs']});folds=blocks(dates);save('SPLIT_REALIZED.json',{'dates':dates,'folds':folds,'same_security_session_test_fold':True,'random_row_split':False,'purged_train_rows':0,'embargo_minutes':30,'max_primary_horizon':30,'label_overlap_outside_session_allowed':False})
 all_predictions=[];fitindex=[];controlmap=[];availability=[]
 permutation_rng=np.random.default_rng(2026100202)
 for control in ['REAL','PERMUTATION','SHIFT60']:
  for h in [5,15,30]:
   usable=[];target_by_key={}
   for row in features:
    label=labels[row['row_key']][('shift60' if control=='SHIFT60' else 'real')][str(h)]
    if label['available']:usable.append(row);target_by_key[row['row_key']]=label
   if control=='PERMUTATION':
    # Complete regression+direction+provenance tuple is permuted, never sign alone.
    rng=permutation_rng
    for date in dates:
     subset=[r for r in usable if r['date']==date];order=rng.permutation(len(subset));old=[target_by_key[r['row_key']] for r in subset]
     for i,r in enumerate(subset):target_by_key[r['row_key']]=old[order[i]];controlmap.append({'horizon':h,'feature_key':r['row_key'],'label_donor_future_key':old[order[i]]['future_key'],'date':date,'permutation_index':int(order[i])})
   availability.append({'control':control,'horizon':h,'available_all_dates_N':len(usable),'available_date_N':len({r['date'] for r in usable})})
   for fold in folds:
    train=[r for r in usable if r['date'] in fold['train_dates']];test=[r for r in usable if r['date'] in fold['test_dates']]
    if not train or not test:
     fitindex.append({'control':control,'horizon':h,'fold':fold['fold'],'status':'UNAVAILABLE_TRAIN_OR_TEST','train_N':len(train),'test_N':len(test)});continue
    if not any(r['date']<max(x['date'] for x in train) for r in train):
     fitindex.append({'control':control,'horizon':h,'fold':fold['fold'],'status':'UNAVAILABLE_INNER_PAST_DATES','train_N':len(train),'test_N':len(test)});continue
    first_test=min(fold['test_dates'])+'T00:00:00+09:00'
    for r in train:
     target=target_by_key[r['row_key']];assert target['label_end']<first_test,'TRAIN_TEST_LABEL_OVERLAP'
    Y=np.array([[float(target_by_key[r['row_key']]['y_token'])]+[int(target_by_key[r['row_key']]['direction']==c) for c in [-1,0,1]] for r in train])
    for model in ['B0','B1','B2','B3']:
     key=f'{control}_H{h}';prediction,fitpath=fit_one(train,test,Y,model,fold,schema,key)
     q=encode_prob(prediction[:,1:]);fitindex.append({'control':control,'horizon':h,'fold':fold['fold'],'model':model,'fit_path':fitpath,'fit_SHA256':digest(R/fitpath),'train_N':len(train),'test_N':len(test),'status':'FITTED'})
     for i,row in enumerate(test):
      target=target_by_key[row['row_key']]
      all_predictions.append({'control':control,'horizon':h,'fold':fold['fold'],'model':model,'row_key':row['row_key'],'security_id':row['security_id'],'session_id':row['session_id'],'date':row['date'],'bar_end':row['bar_end'],'run_id':row['run_id'],'formal_primary':row['features']['formal_primary'],'y':float(target['y_token']),'y_token':target['y_token'],'direction':target['direction'],'prediction':float(prediction[i,0]),'p_negative':float(q[i,0]),'p_zero':float(q[i,1]),'p_positive':float(q[i,2]),'label_end':target['label_end'],'fit_path':fitpath})
 csvout('PERMUTATION_MAPPING.csv',controlmap);csvout('TARGET_CONTROL_AVAILABILITY.csv',availability)
 for control in ['REAL','PERMUTATION','SHIFT60']:
  for h in [5,15,30]:csvout(f'OOF/{control}_H{h}.csv',[r for r in all_predictions if r['control']==control and r['horizon']==h])
 save('FIT_INDEX.json',{'fit_operations':FITS,'items':fitindex,'definition_changes':0,'families_added_after_results':0})
 groups=defaultdict(list);foldgroups=defaultdict(list)
 for row in all_predictions:groups[(row['control'],row['horizon'],row['model'])].append(row);foldgroups[(row['control'],row['horizon'],row['model'],row['fold'])].append(row)
 aggregates=[{'control':c,'horizon':h,'model':m,**metric(rows)} for (c,h,m),rows in sorted(groups.items())]
 byfold=[{'control':c,'horizon':h,'model':m,'fold':f,**metric(rows)} for (c,h,m,f),rows in sorted(foldgroups.items())]
 for values in [aggregates,byfold]:
  for row in values:
   base=next(x for x in values if x['control']==row['control'] and x['horizon']==row['horizon'] and x['model']=='B0' and x.get('fold')==row.get('fold'))
   row['R2_vs_saved_B0']=None if base['MSE']==0 else 1-row['MSE']/base['MSE'];row['date_equal_R2_vs_B0']=None if base['date_equal_MSE']==0 else 1-row['date_equal_MSE']/base['date_equal_MSE']
 csvout('METRICS_AGGREGATE.csv',aggregates);csvout('METRICS_BY_FOLD.csv',byfold)
 rng=np.random.default_rng(2026100201);draws={};increments=[];date_errors=[]
 comparisons=[('B1','B0'),('B2','B1'),('B3','B2'),('B2','B0'),('B3','B0'),('B3','B1')]
 for h in [5,15,30]:
  base=groups.get(('REAL',h,'B0'),[]);ds=sorted({r['date'] for r in base})
  if not ds:continue
  draw=rng.integers(0,len(ds),size=(1000,len(ds)));draws[str(h)]={'dates':ds,'draws':draw.tolist()}
  vals={}
  for model in ['B0','B1','B2','B3']:
   rr=groups[('REAL',h,model)];a=[]
   for d in ds:
    subset=[r for r in rr if r['date']==d];v=float(np.mean([(r['y']-r['prediction'])**2 for r in subset]));a.append(v);date_errors.append({'horizon':h,'model':model,'date':d,'MSE':v,'N':len(subset)})
   vals[model]=np.array(a)
  for m,b in comparisons:
   bv=vals[b];mv=vals[m];ratio=None if bv.mean()==0 else float(1-mv.mean()/bv.mean());den=bv[draw].mean(axis=1);num=(bv[draw]-mv[draw]).mean(axis=1);ok=den!=0;rep=num[ok]/den[ok]
   lo,hi=(None,None) if not len(rep) else [float(x) for x in np.quantile(rep,[1/240,239/240])]
   positive=sum(next((x['date_equal_MSE'] for x in byfold if x['control']=='REAL' and x['horizon']==h and x['model']==m and x['fold']==f),math.inf)<next((x['date_equal_MSE'] for x in byfold if x['control']=='REAL' and x['horizon']==h and x['model']==b and x['fold']==f),-math.inf) for f in [1,2,3])
   increments.append({'horizon':h,'candidate':m,'comparator':b,'date_equal_MSE_reduction':float(bv.mean()-mv.mean()),'relative_reduction':ratio,'CI_low':lo,'CI_high':hi,'interval_level':1-1/120,'date_cluster_N':len(ds),'bootstrap_replicates':len(rep),'positive_folds':positive})
 save('BOOTSTRAP_DATE_DRAWS.json',{'seed':2026100201,'replicates':1000,'unit':'session date','by_horizon':draws});csvout('DATE_CLUSTER_ERRORS.csv',date_errors);csvout('INCREMENTAL_VALUE.csv',increments)
 negative=[]
 realmaps={(h,m):{r['row_key']:r for r in rows} for (c,h,m),rows in groups.items() if c=='REAL'}
 for control in ['PERMUTATION','SHIFT60']:
  for h in [5,15,30]:
   for m in ['B1','B2','B3']:
    rr=groups.get((control,h,m),[]);bb=groups.get((control,h,'B0'),[])
    if not rr or not bb:negative.append({'control':control,'horizon':h,'model':m,'status':'UNAVAILABLE'});continue
    keys={r['row_key'] for r in rr};matched_m=[v for k,v in realmaps.get((h,m),{}).items() if k in keys];matched_b=[v for k,v in realmaps.get((h,'B0'),{}).items() if k in keys]
    cm,cb=metric(rr),metric(bb);rm,rb=metric(matched_m),metric(matched_b)
    nc=None if cb['date_equal_MSE']==0 else 1-cm['date_equal_MSE']/cb['date_equal_MSE'];effect=None if rb['date_equal_MSE']==0 else 1-rm['date_equal_MSE']/rb['date_equal_MSE']
    comparable=effect is not None and effect>0 and nc is not None and nc>0 and nc>=0.9*effect
    negative.append({'control':control,'horizon':h,'model':m,'status':'COMPARABLE_GOOD_BLOCK' if comparable else 'CONTROL_NOT_COMPARABLY_GOOD','control_rows_N':len(rr),'matched_real_rows_N':len(matched_m),'control_date_N':cm['date_N'],'real_matched_relative_improvement':effect,'control_relative_improvement':nc,'same_row_key_set':keys=={r['row_key'] for r in matched_m},'comparably_good':comparable})
 csvout('NEGATIVE_CONTROL_RESULTS.csv',negative)
 buckets=[];calibration=[]
 for (control,h,m),rr in groups.items():
  if control!='REAL':continue
  ordered=sorted(rr,key=lambda r:(r['prediction'],r['row_key']))
  for k in range(5):
   subset=ordered[(k*len(ordered))//5:((k+1)*len(ordered))//5]
   if subset:buckets.append({'horizon':h,'model':m,'bucket':k+1,'N':len(subset),'predicted_mean':float(np.mean([r['prediction'] for r in subset])),'realized_mean':float(np.mean([r['y'] for r in subset])),'realized_median':float(np.median([r['y'] for r in subset])),'date_N':len({r['date'] for r in subset}),'security_session_N':len({(r['security_id'],r['session_id']) for r in subset})})
  cells=defaultdict(list)
  for r in rr:
   q=[r['p_negative'],r['p_zero'],r['p_positive']];conf=max(q);pred=q.index(conf)-1;cells[min(9,int(conf*10))].append((conf,int(pred==r['direction'])))
  for k,cell in sorted(cells.items()):calibration.append({'horizon':h,'model':m,'confidence_bin':k,'N':len(cell),'mean_confidence':float(np.mean([x[0] for x in cell])),'observed_accuracy':float(np.mean([x[1] for x in cell]))})
 csvout('PREDICTION_BUCKETS.csv',buckets);csvout('DIRECTION_CALIBRATION.csv',calibration)
 # Fixed secondary classification, no metric-driven hyperparameter choice.
 secondary=[];secmetrics=[];states=['RISE','SHARP_RISE','RISE_STOP','PULLBACK','RANGE','REBOUND','DROP','SHARP_DROP','DROP_STOP']
 for task,classes in [('NEXT_PRIMARY',states),('TRANSITION_WITHIN30',[0,1])]:
  usable=[];truth={}
  for row in features:
   s=labels[row['row_key']]['structural'];ok=s['next_primary_available'] if task=='NEXT_PRIMARY' else s['transition_window_available']
   if ok:usable.append(row);truth[row['row_key']]=s['next_primary'] if task=='NEXT_PRIMARY' else s['transition_within30']
  for fold in folds:
   tr=[r for r in usable if r['date'] in fold['train_dates']];te=[r for r in usable if r['date'] in fold['test_dates']]
   if not tr or not te:continue
   Y=np.array([[int(truth[r['row_key']]==c) for c in classes] for r in tr],dtype=float)
   for m in ['B0','B1','B2','B3']:
    prediction,fitpath=fit_one(tr,te,Y,m,fold,schema,task,secondary=True);q=encode_prob(prediction)
    for i,row in enumerate(te):secondary.append({'task':task,'fold':fold['fold'],'model':m,'row_key':row['row_key'],'date':row['date'],'security_id':row['security_id'],'session_id':row['session_id'],'truth':truth[row['row_key']],'prediction':classes[int(q[i].argmax())],'probabilities_json':json.dumps(q[i].tolist(),separators=(',',':')),'classes_json':json.dumps(classes,separators=(',',':')),'fit_path':fitpath})
 for task,classes in [('NEXT_PRIMARY',states),('TRANSITION_WITHIN30',[0,1])]:
  for m in ['B0','B1','B2','B3']:
   rr=[r for r in secondary if r['task']==task and r['model']==m]
   if not rr:continue
   truth=np.array([classes.index(r['truth']) for r in rr]);q=np.array([json.loads(r['probabilities_json']) for r in rr]);pred=q.argmax(axis=1)
   secmetrics.append({'task':task,'model':m,'row_N':len(rr),'date_N':len({r['date'] for r in rr}),'accuracy':float(np.mean(pred==truth)),'balanced_accuracy':float(np.mean([np.mean(pred[truth==c]==c) for c in sorted(set(truth))])),'Brier':float(np.mean(np.sum((q-np.eye(len(classes))[truth])**2,axis=1))),'log_loss':float(np.mean(-np.log(q[np.arange(len(rr)),truth]))),'interpretation':'SECONDARY_ONLY_NOT_PRIMARY_GATE'})
 csvout('SECONDARY_OOF.csv',secondary);csvout('SECONDARY_METRICS.csv',secmetrics)
 # Contribution and leave-one-cluster analysis on the registered date-equal effect.
 concentration=[]
 for h in [5,15,30]:
  for m in ['B2','B3']:
   for b in ['B0','B1','B2']:
    if m==b:continue
    mm=realmaps.get((h,m),{});bb=realmaps.get((h,b),{});keys=sorted(set(mm)&set(bb))
    if not keys:continue
    dateN=Counter(mm[k]['date'] for k in keys);delta={k:((bb[k]['y']-bb[k]['prediction'])**2-(mm[k]['y']-mm[k]['prediction'])**2)/dateN[mm[k]['date']] for k in keys}
    for unit in ['date','security_id','security_session']:
     contributions=defaultdict(float)
     for k in keys:
      group=mm[k]['date'] if unit=='date' else mm[k]['security_id'] if unit=='security_id' else mm[k]['security_id']+'|'+mm[k]['session_id'];contributions[group]+=delta[k]
     positives={}
     for k in keys:
      group=mm[k]['date'] if unit=='date' else mm[k]['security_id'] if unit=='security_id' else mm[k]['security_id']+'|'+mm[k]['session_id'];positives[group]=positives.get(group,0)+max(0,delta[k])
     gross=sum(positives.values());total=sum(delta.values());leave=[]
     for group in contributions:
      keep=[k for k in keys if (mm[k]['date'] if unit=='date' else mm[k]['security_id'] if unit=='security_id' else mm[k]['security_id']+'|'+mm[k]['session_id'])!=group]
      if keep:
       a=metric([mm[k] for k in keep])['date_equal_MSE'];c=metric([bb[k] for k in keep])['date_equal_MSE'];leave.append(c-a)
     concentration.append({'horizon':h,'candidate':m,'comparator':b,'cluster_unit':unit,'cluster_N':len(contributions),'maximum_gross_positive_share':None if gross==0 else max(positives.values())/gross,'minimum_leave_one_MSE_improvement':min(leave) if leave else None,'net_date_weighted_improvement':total/len(dateN),'contributions_json':json.dumps(contributions,sort_keys=True,separators=(',',':'))})
 csvout('CONCENTRATION_LEAVE_ONE.csv',concentration)
 save('C3_OOF_FIXATION_RECEIPT.json',{'created_at_jst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'status':'OOF_RESULTS_FIXED_PENDING_INDEPENDENT_AUDIT','OOF_records_N':len(all_predictions),'secondary_OOF_records_N':len(secondary),'fit_operations':FITS,'primary_model_family_N':4,'ridge_strength_N':3,'kernel_runs':0,'provider_requests':0,'post_result_changes':0,'files':[{'path':str(p.relative_to(R)),'SHA256':digest(p),'bytes':p.stat().st_size} for p in sorted((R/'OOF').glob('*.csv'))]+[{'path':n,'SHA256':digest(R/n)} for n in ['METRICS_AGGREGATE.csv','METRICS_BY_FOLD.csv','INCREMENTAL_VALUE.csv','NEGATIVE_CONTROL_RESULTS.csv','BOOTSTRAP_DATE_DRAWS.json']]})
 print(json.dumps({'OOF_records_N':len(all_predictions),'fit_operations':FITS,'primary_results_saved':len(aggregates),'secondary_OOF_N':len(secondary),'definition_changes':0}))
if __name__=='__main__':main()
