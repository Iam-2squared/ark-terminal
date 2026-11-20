from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
import json,csv,hashlib,math,os,numpy as np
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now(timezone(timedelta(hours=9))).isoformat()
def save(n,x):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n');os.replace(tmp,p)
def csvout(n,rows):
 with (R/n).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['status']);w.writeheader();w.writerows(rows)
def weights(rows):
 ds=Counter(r['date'] for r in rows);ps=Counter((r['date'],r['security_id'],r['session_id']) for r in rows);per=Counter(d for d,s,z in ps)
 a=np.array([1/(len(ds)*per[r['date']]*ps[(r['date'],r['security_id'],r['session_id'])]) for r in rows]);return a/a.mean()
def ledger(family,**kw):
 p=R/'MODEL_EXECUTION_LEDGER.jsonl';previous=p.read_text().splitlines() if p.exists() else []
 n=len(previous)+1;assert n<=1200,'FIT_BUDGET_CAP'
 if previous:assert json.loads(previous[-1])['fit_N']==n-1,'LEDGER_NOT_CONTIGUOUS'
 with p.open('a') as f:
  f.write(json.dumps({'fit_N':n,'family':family,'JST':now(),'charged_before_fit':True,**kw})+'\n');f.flush();os.fsync(f.fileno())
 return n
def prob(raw):
 x=np.maximum(raw,1e-12);return x/x.sum(axis=1,keepdims=True)
def temp(p,T):
 z=np.log(p)/T;z-=z.max(axis=1,keepdims=True);e=np.exp(z);return e/e.sum(axis=1,keepdims=True)
def loss(p,Y,rows):return float(np.average(-np.log(np.maximum(p[np.arange(len(Y)),Y.argmax(axis=1)],1e-300)),weights=weights(rows)))
class Encoder:
 def __init__(self,rows,model,schema):
  suffix='path' if model=='R3' else 'anatomy' if model=='R4' else None
  self.num=schema['numeric_state']+(schema['numeric_'+suffix] if suffix else []);self.cat=schema['categorical_state']+(schema['categorical_'+suffix] if suffix else []);self.stats={};self.vocab={};w=weights(rows)
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
def build(train,Y,model,schema,alpha,tag):
 w=weights(train)
 if model in ['R0','R1']:
  charged=ledger(model,rows=len(train),**tag);prior=np.average(Y,axis=0,weights=w);lookup={}
  if model=='R1':
   for v in sorted({r['features']['formal_primary'] for r in train}):
    ids=np.array([r['features']['formal_primary']==v for r in train]);lookup[v]=((Y[ids]*w[ids,None]).sum(axis=0)+10*prior)/(w[ids].sum()+10)
  art={'prior':prior.tolist(),'lookup':{k:v.tolist() for k,v in lookup.items()},'encoder':None,'coefficients':None,'alpha':None,'charged_fit_ordinal':charged}
 else:
  enc=Encoder(train,model,schema);X=enc.transform(train);z=np.column_stack([np.ones(len(X)),X]);charged=ledger('ridge',rows=len(X),columns=X.shape[1],alpha=alpha,model=model,**tag)
  A=(z.T*w)@z/w.sum()+np.diag([0.]+[alpha]*X.shape[1]);B=(z.T*w)@Y/w.sum();c=np.linalg.solve(A,B)
  art={'prior':None,'lookup':None,'encoder':enc.data(),'coefficients':c.tolist(),'alpha':alpha,'charged_fit_ordinal':charged}
 return art
def evaluate(art,rows):
 if art['encoder'] is None:
  return prob(np.array([art['lookup'].get(r['features']['formal_primary'],art['prior']) for r in rows]))
 enc=object.__new__(Encoder);enc.num=art['encoder']['numeric'];enc.cat=art['encoder']['categorical'];enc.stats=art['encoder']['stats'];enc.vocab=art['encoder']['vocab'];X=enc.transform(rows)
 return prob(np.column_stack([np.ones(len(rows)),X])@np.array(art['coefficients']))
def fit(train,test,Y,model,schema,task,control,fold,classes):
 path=R/'FITTED'/f'{task}_{control}_{model}_F{fold}.json';tag={'task':task,'control':control,'fold':fold};last=max(r['date'] for r in train);ii=[i for i,r in enumerate(train) if r['date']<last];vi=[i for i,r in enumerate(train) if r['date']==last];grid=[];inners=[];tg=[];alpha=.1;T=1.
 if path.exists():
  art=json.loads(path.read_text());assert art['train_keys']==[r['row_key'] for r in train] and art['test_keys']==[r['row_key'] for r in test],'RESUME_DATA_CHANGED'
  return evaluate(art,test),temp(evaluate(art,test),art['temperature']),str(path.relative_to(R))
 if ii and vi:
  tr=[train[i] for i in ii];va=[train[i] for i in vi];select=[None] if model in ['R0','R1'] else [.01,.1,1.]
  for a in select:
   inner=build(tr,Y[ii],model,schema,a,{**tag,'phase':'inner'});p=evaluate(inner,va);ll=loss(p,Y[vi],va)
   grid.append({'alpha':a,'validation_loss':ll,'validation_date':last});inners.append({**inner,'train_keys':[r['row_key'] for r in tr],'validation_keys':[r['row_key'] for r in va],'validation_actual':Y[vi].argmax(axis=1).tolist(),'validation_probabilities':p.tolist()})
  pick=min(range(len(grid)),key=lambda k:(grid[k]['validation_loss'],-(grid[k]['alpha'] or 0)));alpha=grid[pick]['alpha'];p=np.array(inners[pick]['validation_probabilities'])
  for z in [.5,.75,1.,1.25,1.5,2.]:tg.append({'temperature':z,'validation_loss':loss(temp(p,z),Y[vi],va),'validation_date':last})
  T=min(tg,key=lambda x:(x['validation_loss'],abs(x['temperature']-1),-x['temperature']))['temperature']
 art=build(train,Y,model,schema,alpha,{**tag,'phase':'final'});p=evaluate(art,test);art.update(model=model,task=task,control=control,fold=fold,classes=classes,temperature=T,
  train_rows=len(train),test_rows=len(test),train_dates=sorted({r['date'] for r in train}),test_dates=sorted({r['date'] for r in test}),
  train_feature_hash=hashlib.sha256(json.dumps([[r['row_key'],r['features']] for r in train],sort_keys=True,separators=(',',':')).encode()).hexdigest(),train_target_hash=hashlib.sha256(Y.astype('<f8').tobytes()).hexdigest(),
  train_keys=[r['row_key'] for r in train],test_keys=[r['row_key'] for r in test],validation_grid=grid,temperature_grid=tg,inner_artifacts=inners,inner_unavailable=not bool(ii and vi))
 save(str(path.relative_to(R)),art);return p,temp(p,T),str(path.relative_to(R))
def main():
 for n,h in json.loads((R/'PREDICTIVENESS_V4_PRECOMMIT.json').read_text())['hashes'].items():assert sha(R/n)==h,'PRECOMMIT_CHANGED'
 assert not (R/'OOF_ALL.jsonl').exists(),'OOF_ALREADY_FIXED'
 if not (R/'MODEL_EXECUTION_LEDGER.jsonl').exists():(R/'MODEL_EXECUTION_LEDGER.jsonl').touch()
 schema=json.loads((R/'FEATURE_SCHEMA_V4.json').read_text());ts=json.loads((R/'REVERSAL_TARGET_SCHEMA.json').read_text());folds=json.loads((R/'SPLIT_REALIZED_V4.json').read_text())['folds'];manifest=json.loads((R/'DATASET_MANIFEST_V4.json').read_text());features=[];labels={}
 for p in manifest['pairs']:
  f=Path(p['feature_path']);assert sha(f)==p['feature_SHA256'];features.extend(map(json.loads,f.read_text().splitlines()));labels.update({r['row_key']:r for r in map(json.loads,(R/'LABELS'/f"{p['pair_id']}.jsonl").read_text().splitlines())})
 features.sort(key=lambda x:x['row_key']);counts=[];permap=[];oof=[];index=[]
 for task,classes in ts['classes'].items():
  for control in ['REAL','TRUE_NULL','SHIFT60']:
   key='REAL' if control=='TRUE_NULL' else control;target={r['row_key']:labels[r['row_key']][key][task] for r in features};usable=[r for r in features if target[r['row_key']]['available']]
   if control=='TRUE_NULL':
    groups=defaultdict(list)
    for r in usable:groups[(r['date'],r['security_id'],r['session_id'])].append(r)
    for group,rs in sorted(groups.items()):
     seed=int(hashlib.sha256(('2026100402|'+task+'|'+('|'.join(group))).encode()).hexdigest()[:16],16);perm=np.random.default_rng(seed).permutation(len(rs));old=[target[r['row_key']] for r in rs]
     for i,r in enumerate(rs):target[r['row_key']]=old[int(perm[i])];permap.append({'task':task,'feature_key':r['row_key'],'donor_key':rs[int(perm[i])]['row_key'],'date':r['date'],'security_id':r['security_id'],'group_N':len(rs),'singleton':len(rs)==1})
   for fold in folds:
    train=[r for r in usable if r['date'] in fold['train_dates']];test=[r for r in usable if r['date'] in fold['test_dates']];counts.append({'task':task,'control':control,'fold':fold['fold'],'train_N':len(train),'test_N':len(test),'test_date_N':len({r['date'] for r in test}),'class_support':json.dumps(dict(Counter(target[r['row_key']]['target'] for r in test)))})
    if not train or not test or not fold['initial_train_dates_sufficient']:index.append({'task':task,'control':control,'fold':fold['fold'],'status':'NO_TRAIN_OR_TEST','train_N':len(train),'test_N':len(test)});continue
    for r in train:assert target[r['row_key']]['label_end']<fold['test_start'],'PARTITION_LEAK'
    Y=np.array([[int(target[r['row_key']]['target']==c) for c in classes] for r in train],float)
    for model in ['R0','R1','R2','R3','R4']:
     p,q,fp=fit(train,test,Y,model,schema,task,control,fold['fold'],classes);index.append({'task':task,'control':control,'fold':fold['fold'],'model':model,'status':'FITTED','path':fp,'SHA256':sha(R/fp)})
     for i,r in enumerate(test):
      t=target[r['row_key']];base={'row_key':r['row_key'],'date':r['date'],'security_id':r['security_id'],'session_id':r['session_id'],'bar_end':r['bar_end'],'current_primary':r['features']['formal_primary'],'exposure':r['exposure'],'model':model,'task':task,'control':control,'fold':fold['fold'],'label_start':t.get('label_start'),'label_end':t['label_end'],'fit_path':fp,'actual':t['target']}
      for calibrated,z in [(False,p),(True,q)]:oof.append({**base,'calibrated':calibrated,'predicted':classes[int(z[i].argmax())],'probabilities':z[i].tolist()})
     print(json.dumps({'task':task,'control':control,'fold':fold['fold'],'model':model,'train':len(train),'test':len(test)}),flush=True)
 with (R/'OOF_ALL.jsonl').open('x') as f:
  for r in oof:f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
 for task in ts['classes']:
  rs=[{**{k:v for k,v in r.items() if k!='probabilities'},'probabilities':json.dumps(r['probabilities'])} for r in oof if r['task']==task]
  csvout(task+'_OOF_PREDICTIONS.csv',rs)
 csvout('PERMUTATION_MAPPING_V4.csv',permap);csvout('TARGET_CONTROL_AVAILABILITY_V4.csv',counts)
 fits=len((R/'MODEL_EXECUTION_LEDGER.jsonl').read_text().splitlines());save('FIT_INDEX_V4.json',{'fit_operations':fits,'items':index})
 save('C5_OOF_FIXATION_RECEIPT.json',{'JST':now(),'OOF_SHA256':sha(R/'OOF_ALL.jsonl'),'fit_operations':fits,'classification_records':len(oof),'post_result_changes':0})
 print(json.dumps({'fits':fits,'OOF':len(oof)}))
if __name__=='__main__':main()
