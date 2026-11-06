from pathlib import Path
from collections import Counter,defaultdict
import json,csv,hashlib,math,numpy as np,datetime
R=Path(__file__).resolve().parent;FITS=0
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def csvout(n,rows,columns=None):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=columns or list(rows[0]) if rows else columns or ['status']);w.writeheader();w.writerows(rows)
def weights(rows):
 ds=Counter(r['date'] for r in rows);ps=Counter((r['date'],r['security_id'],r['session_id']) for r in rows);per=Counter(d for d,s,z in ps)
 a=np.array([1/(len(ds)*per[r['date']]*ps[(r['date'],r['security_id'],r['session_id'])]) for r in rows]);return a/a.mean()
class Encoder:
 def __init__(self,rows,model,schema):
  self.num=schema['numeric_state']+(schema['numeric_path'] if model=='B3' else []);self.cat=schema['categorical_state']+(schema['categorical_path'] if model=='B3' else []);self.stats={};self.vocab={};w=weights(rows)
  for n in self.num:
   a=np.array([np.nan if r['features'][n] is None else r['features'][n] for r in rows]);ok=np.isfinite(a);mean=float(np.average(a[ok],weights=w[ok])) if ok.any() else 0.;var=float(np.average((a[ok]-mean)**2,weights=w[ok])) if ok.any() else 0.;self.stats[n]=[mean,math.sqrt(var) if var>0 else 1.]
  for n in self.cat:self.vocab[n]=sorted({r['features'][n] for r in rows})
 def transform(self,rows):
  cols=[]
  for n in self.num:
   mean,sd=self.stats[n];a=np.array([np.nan if r['features'][n] is None else r['features'][n] for r in rows]);miss=~np.isfinite(a);cols.extend([np.where(miss,0,(a-mean)/sd),miss.astype(float)])
  for n in self.cat:
   for v in self.vocab[n]:cols.append(np.array([r['features'][n]==v for r in rows],float))
  return np.column_stack(cols)
 def data(self):return {'numeric':self.num,'categorical':self.cat,'stats':self.stats,'vocab':self.vocab}
def ledger(family,**kw):
 global FITS;FITS+=1;assert FITS<=648,'FIT_BUDGET_CAP'
 with (R/'MODEL_EXECUTION_LEDGER.jsonl').open('a') as f:f.write(json.dumps({'fit_N':FITS,'family':family,'JST':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),**kw})+'\n')
def prob(x):
 x=np.maximum(x,1e-12);return x/x.sum(axis=1,keepdims=True)
def ridge(X,Y,w,alpha):
 ledger('ridge',rows=len(X),columns=X.shape[1],alpha=alpha);z=np.column_stack([np.ones(len(X)),X]);A=(z.T*w)@z/w.sum()+np.diag([0.]+[alpha]*X.shape[1]);B=(z.T*w)@Y/w.sum();return np.linalg.solve(A,B)
def applycoef(X,c):return np.column_stack([np.ones(len(X)),X])@c
def fit(train,test,Y,model,schema,task,control,fold):
 path=R/'FITTED'/f'{task}_{control}_{model}_F{fold}.json';assert not path.exists(),'NO_DUPLICATE_FIT'
 w=weights(train);grid=[]
 if model in ['B0','B1']:
  ledger(model,rows=len(train),task=task,control=control,fold=fold);prior=np.average(Y,axis=0,weights=w);lookup={}
  if model=='B1':
   for v in sorted({r['features']['formal_primary'] for r in train}):
    ids=np.array([r['features']['formal_primary']==v for r in train]);lookup[v]=((Y[ids]*w[ids,None]).sum(axis=0)+10*prior)/(w[ids].sum()+10)
  prediction=np.array([lookup.get(r['features']['formal_primary'],prior) for r in test]);art={'prior':prior.tolist(),'lookup':{k:v.tolist() for k,v in lookup.items()},'encoder':None,'coefficients':None,'alpha':None}
 else:
  last=max(r['date'] for r in train);inner=[i for i,r in enumerate(train) if r['date']<last];val=[i for i,r in enumerate(train) if r['date']==last];alpha=.1
  if inner and val:
   tr=[train[i] for i in inner];va=[train[i] for i in val];enc=Encoder(tr,model,schema);X=enc.transform(tr);VX=enc.transform(va)
   for a in [.01,.1,1.]:
    c=ridge(X,Y[inner],weights(tr),a);p=applycoef(VX,c)
    loss=float(np.average((Y[val,0]-p[:,0])**2,weights=weights(va))) if task.startswith('PRICE') else float(np.average(-np.log(prob(p)[np.arange(len(val)),Y[val].argmax(axis=1)]),weights=weights(va)))
    grid.append({'alpha':a,'validation_loss':loss,'validation_date':last})
   alpha=min(grid,key=lambda v:(v['validation_loss'],-v['alpha']))['alpha']
  enc=Encoder(train,model,schema);c=ridge(enc.transform(train),Y,w,alpha);prediction=applycoef(enc.transform(test),c);art={'encoder':enc.data(),'coefficients':c.tolist(),'alpha':alpha,'inner_unavailable':not bool(inner and val)}
 art.update(model=model,task=task,control=control,fold=fold,train_rows=len(train),test_rows=len(test),train_dates=sorted({r['date'] for r in train}),test_dates=sorted({r['date'] for r in test}),train_feature_hash=hashlib.sha256(json.dumps([[r['row_key'],r['features']] for r in train],sort_keys=True,separators=(',',':')).encode()).hexdigest(),train_target_hash=hashlib.sha256(Y.astype('<f8').tobytes()).hexdigest(),train_keys=[r['row_key'] for r in train],test_keys=[r['row_key'] for r in test],validation_grid=grid)
 save(str(path.relative_to(R)),art);return prediction,str(path.relative_to(R))
def main():
 pre=json.loads((R/'PREDICTIVENESS_V2_PRECOMMIT.json').read_text())
 for n,v in pre['hashes'].items():assert sha(R/n)==v,'PRECOMMIT_CHANGED'
 assert not (R/'OOF_ALL.jsonl').exists(),'OOF_ALREADY_FIXED'
 schema=json.loads((R/'FEATURE_SCHEMA_V2.json').read_text());ts=json.loads((R/'TARGET_SCHEMA_V2.json').read_text());folds=json.loads((R/'SPLIT_REALIZED_V2.json').read_text())['folds'];manifest=json.loads((R/'DATASET_MANIFEST.json').read_text());features=[];labels={}
 for p in manifest['pairs']:
  f=Path(p['feature_path']);assert sha(f)==p['feature_SHA256'];rs=list(map(json.loads,f.read_text().splitlines()))
  for r in rs:r['exposure']=p['exposure']
  features.extend(rs);labels.update({r['row_key']:r for r in map(json.loads,(R/'LABELS'/f"{p['pair_id']}.jsonl").read_text().splitlines())})
 features.sort(key=lambda x:x['row_key']);counts=[];permap=[];oof=[];prices=[];index=[]
 for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY','TRANSITION_WITHIN30','PRICE_H5','PRICE_H15','PRICE_H30']:
  classes=['NO_TRANSITION','TRANSITION'] if task=='TRANSITION_WITHIN30' else ts['class_order'];isprice=task.startswith('PRICE');h=int(task[7:]) if isprice else None
  for control in ['REAL'] if isprice else ['REAL','TRUE_NULL','SHIFT60']:
   key='REAL' if control=='TRUE_NULL' else control;target={r['row_key']:labels[r['row_key']]['PRICE'][str(h)] if isprice else labels[r['row_key']][key][task] for r in features};usable=[r for r in features if target[r['row_key']]['available']]
   if control=='TRUE_NULL':
    groups=defaultdict(list)
    for r in usable:groups[(r['date'],r['security_id'],r['session_id'])].append(r)
    for group,rs in sorted(groups.items()):
     seed=int(hashlib.sha256(('2026100202|'+task+'|'+('|'.join(group))).encode()).hexdigest()[:16],16);perm=np.random.default_rng(seed).permutation(len(rs));old=[target[r['row_key']] for r in rs]
     for i,r in enumerate(rs):target[r['row_key']]=old[int(perm[i])];permap.append({'task':task,'feature_key':r['row_key'],'donor_key':rs[int(perm[i])]['row_key'],'date':r['date'],'security_id':r['security_id'],'group_N':len(rs),'singleton':len(rs)==1})
   for fold in folds:
    train=[r for r in usable if r['date'] in fold['train_dates']];test=[r for r in usable if r['date'] in fold['test_dates']];counts.append({'task':task,'control':control,'fold':fold['fold'],'train_N':len(train),'test_N':len(test),'test_date_N':len({r['date'] for r in test})})
    if not train or not test:index.append({'task':task,'control':control,'fold':fold['fold'],'status':'NO_TRAIN_OR_TEST','train_N':len(train),'test_N':len(test)});continue
    for r in train:assert target[r['row_key']]['label_end']<fold['test_start'],'PARTITION_LEAK'
    if isprice:Y=np.array([[float(target[r['row_key']]['y_token'])]+[int(target[r['row_key']]['direction']==c) for c in [-1,0,1]] for r in train])
    else:Y=np.array([[int(target[r['row_key']]['target']==c) for c in classes] for r in train],float)
    for model in ['B0','B1','B2','B3']:
     p,fp=fit(train,test,Y,model,schema,task,control,fold['fold']);q=prob(p[:,1:] if isprice else p);index.append({'task':task,'control':control,'fold':fold['fold'],'model':model,'status':'FITTED','path':fp,'SHA256':sha(R/fp)})
     for i,r in enumerate(test):
      t=target[r['row_key']];base={'row_key':r['row_key'],'date':r['date'],'security_id':r['security_id'],'session_id':r['session_id'],'bar_end':r['bar_end'],'current_primary':r['features']['formal_primary'],'exposure':r['exposure'],'model':model,'task':task,'control':control,'fold':fold['fold'],'label_start':t.get('label_start'),'label_end':t['label_end'],'fit_path':fp}
      if isprice:prices.append({**base,'horizon':h,'y':float(t['y_token']),'y_token':t['y_token'],'direction':t['direction'],'prediction':float(p[i,0]),'p_negative':float(q[i,0]),'p_zero':float(q[i,1]),'p_positive':float(q[i,2])})
      else:oof.append({**base,'actual':t['target'],'predicted':classes[int(q[i].argmax())],'probabilities':q[i].tolist()})
 with (R/'OOF_ALL.jsonl').open('x') as f:
  for r in oof:f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
 for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY','TRANSITION_WITHIN30']:
  rs=[{**{k:v for k,v in r.items() if k!='probabilities'},'probabilities':json.dumps(r['probabilities'])} for r in oof if r['task']==task];csvout(task+'_OOF.csv',rs)
 csvout('PRICE_SECONDARY_OOF.csv',prices);csvout('PERMUTATION_MAPPING_V2.csv',permap);csvout('TARGET_CONTROL_AVAILABILITY_V2.csv',counts);save('FIT_INDEX_V2.json',{'fit_operations':FITS,'items':index})
 save('C4_OOF_FIXATION_RECEIPT.json',{'JST':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'OOF_SHA256':sha(R/'OOF_ALL.jsonl'),'price_SHA256':sha(R/'PRICE_SECONDARY_OOF.csv'),'fit_operations':FITS,'classification_records':len(oof),'price_records':len(prices),'post_result_changes':0})
 print(json.dumps({'fits':FITS,'OOF':len(oof),'price':len(prices)}))
if __name__=='__main__':main()
