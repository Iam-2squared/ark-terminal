"""24 unique fixed temporal fits;3 arms reuse the same MOVE_P artifacts."""
import json,warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from checkpoint import OUT,PRIVATE,save,sha
from io_data import rows,gzwrite
from allocation import band
from core_features import NUMERIC as AUDITED_CORE_NUMERIC,CATEGORICAL as AUDITED_CATEGORICAL

UNKNOWN='__UNKNOWN__'
MANIFEST=json.loads((OUT/'FEATURE_MANIFEST.json').read_text())
assert set(MANIFEST['core_numeric'])==set(AUDITED_CORE_NUMERIC)
assert set(MANIFEST['categorical'])==set(AUDITED_CATEGORICAL)
CORE_NUMERIC=AUDITED_CORE_NUMERIC
CATEGORICAL=AUDITED_CATEGORICAL
MOVE_NUMERIC=CORE_NUMERIC+['movement/M'+str(i) for i in range(1,17)]+['movement/I'+str(i) for i in range(1,4)]
CONFIG=dict(penalty='l2',C=1.0,solver='lbfgs',max_iter=2000,class_weight=None,random_state=57)

def transform(train,test,numeric_fields):
 def numeric(rr):
  a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in numeric_fields] for r in rr])
  assert not np.isinf(a).any()
  return np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)])
 a=numeric(train);z=numeric(test);mu=a.mean(axis=0);scale=a.std(axis=0);scale[scale==0]=1
 vocab={k:sorted({r['categorical'][k] or UNKNOWN for r in train}|{UNKNOWN}) for k in CATEGORICAL}
 def cat(rr):
  col=[]
  for k in CATEGORICAL:
   vv=[r['categorical'][k] if r['categorical'][k] in vocab[k] else UNKNOWN for r in rr]
   col.extend([[float(v==c) for v in vv] for c in vocab[k]])
  return np.array(col).T
 return np.column_stack([(a-mu)/scale,cat(train)]),np.column_stack([(z-mu)/scale,cat(test)]),{
  'numeric_fields':numeric_fields,'categorical_fields':CATEGORICAL,'numeric_mean':mu.tolist(),
  'numeric_scale':scale.tolist(),'categorical_train_vocab':vocab,'constant_missing':0,
  'missing_indicators':True,'training_only':True}

def predict_saved(rr,artifact):
 prep=artifact['preprocessing'];nn=prep['numeric_fields'];cc=prep['categorical_fields']
 a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in nn] for r in rr])
 a=np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)])
 a=(a-np.array(prep['numeric_mean']))/np.array(prep['numeric_scale']);col=[]
 for k in cc:
  voc=prep['categorical_train_vocab'][k];vv=[r['categorical'][k] if r['categorical'][k] in voc else UNKNOWN for r in rr]
  col.extend([[float(v==c) for v in vv] for c in voc])
 x=np.column_stack([a,np.array(col).T]);logits=x@np.array(artifact['coef'])+artifact['intercept']
 return np.exp(-np.logaddexp(0,-logits))

def main():
 assert (OUT/'MODEL_PRECOMMIT.json').exists() and (OUT/'MOVEMENT_ANATOMY.json').exists()
 runtime=rows(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz');teachers={r['entry_id']:r for r in rows(PRIVATE/'TEACHERS_EVALUATION.jsonl.gz')}
 days=sorted({r['session'] for r in runtime});assert len(days)==58
 scored={arm:[] for arm in ('CORE_P5','MOVE_P5','MOVE_DUAL')};ledger=[];hashes={}
 for block,start in enumerate(range(20,58,5),1):
  past=set(days[:start]);future=set(days[start:start+5]);test=[r for r in runtime if r['session'] in future]
  fits={}
  for name,fields,label in (('CORE_P',CORE_NUMERIC,'label_bigwinner5'),('MOVE_P',MOVE_NUMERIC,'label_bigwinner5'),('MOVE_R',MOVE_NUMERIC,'label_realized_positive')):
   train=[r for r in runtime if r['session'] in past and r['entry_minute']<920 and teachers[r['entry_id']][label] is not None]
   assert max(r['session'] for r in train)<min(future)
   y=np.array([teachers[r['entry_id']][label] for r in train],dtype=int);assert set(y)=={0,1}
   a,z,prep=transform(train,test,fields);clf=LogisticRegression(**CONFIG)
   with warnings.catch_warnings(record=True) as ws:
    warnings.simplefilter('always');clf.fit(a,y)
   assert not any(issubclass(w.category,ConvergenceWarning) for w in ws),'FIXED_LOGISTIC_CONVERGENCE_FAIL'
   prob=clf.predict_proba(z)[:,1];base=float(y.mean())
   artifact={'head':name,'block':block,'train_session_N':start,'train_through':days[start-1],'test_dates':days[start:start+5],
    'train_N':len(train),'train_positive_N':int(y.sum()),'train_entry_ids':[r['entry_id'] for r in train],
    'base_rate':base,'parameters':CONFIG,'preprocessing':prep,'coef':clf.coef_[0].tolist(),
    'intercept':float(clf.intercept_[0]),'iterations':int(clf.n_iter_[0])}
   assert np.max(np.abs(predict_saved(test,artifact)-prob))<1e-12
   fname=f'{name}_BLOCK_{block:02d}.json';save(PRIVATE/'models'/fname,artifact);hashes[fname]=sha(PRIVATE/'models'/fname)
   fits[name]=(prob,base,hashes[fname])
   ledger.append({k:artifact[k] for k in ('head','block','train_session_N','train_through','test_dates','train_N','train_positive_N','base_rate','iterations')})
  for i,r in enumerate(test):
   for arm,phead in (('CORE_P5','CORE_P'),('MOVE_P5','MOVE_P'),('MOVE_DUAL','MOVE_P')):
    p,base,hh=fits[phead];pP=float(p[i]);lp=pP/base
    if arm=='MOVE_DUAL':
     rp,rb,rh=fits['MOVE_R'];pR=float(rp[i]);lr=pR/rb;score=float(np.sqrt(lp*lr))
    else:pR=rb=lr=rh=None;score=lp
    scored[arm].append({**r,'arm':arm,'block':block,'pP':pP,'baseP':base,'liftP':lp,
     'pR':pR,'baseR':rb,'liftR':lr,'capital_score':score,'capacity_band':band(score),
     'P_model_sha256':hh,'R_model_sha256':rh,'funding_threshold':1.0})
 assert len(hashes)==24
 for arm,stream in scored.items():gzwrite(PRIVATE/(arm+'_SCORE_STREAM.jsonl.gz'),stream)
 save(PRIVATE/'MODEL_HASHES.json',hashes)
 # Same audited core fields + unchanged teacher yield the original fitted P probabilities.
 old={r['entry_id']:r for r in rows(PRIVATE.parent/'bigwinner_private/ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz')}
 delta=max(abs(r['pP']-old[r['entry_id']]['p_bigwinner5']) for r in scored['CORE_P5'])
 assert delta<1e-10,'AUDITED_CORE_LOGISTIC_REPRODUCTION_MISMATCH'
 save(OUT/'ROLLING_ORIGIN_HEAD_FITS.json',{'status':'FIXED_HEAD_FITS_COMPLETE','fits':24,'blocks':8,'fit_ledger':ledger,
  'model_hashes':hashes,'CORE_v1_probability_max_abs_difference':delta,'Movement_manifest_unchanged':True,
  'within_block_refits':0,'profile_refits':0,'model_count_per_definition':1,'hyperparameter_sweep':0,
  'feature_search':0,'threshold_sweep':0,'teacher_labels_runtime_visible':False,'productionReady':False})
 save(OUT/'FIXED_ARMS_SCORE_STREAMS.json',{'arms':{arm:{'N':len(stream),'score_stream_sha256':sha(PRIVATE/(arm+'_SCORE_STREAM.jsonl.gz')),
  'score_ge1_N':sum(r['capital_score']>=1 for r in stream),'capacity_bands':{str(b) if b is not None else 'BELOW_THRESHOLD':sum(r['capacity_band']==b for r in stream) for b in ('HIGH','MID','BASE',None)}} for arm,stream in scored.items()},
  'OOF_sessions':38,'warmup_sessions':20,'MOVE_P_shared_by_B_C':True,'fits_added_at_score_materialization':0,'productionReady':False})
 print(json.dumps({'fits':24,'blocks':8,'arms':3,'OOF_candidate_N':len(scored['CORE_P5']),'CORE_v1_p_difference':delta}))

if __name__=='__main__':main()
