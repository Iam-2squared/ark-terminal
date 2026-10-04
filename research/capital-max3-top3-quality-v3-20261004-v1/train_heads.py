"""Exactly24 temporal Head fits; held-out teacher payloads not parsed before fit."""
import gzip,re,json,hashlib,warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from checkpoint import *
from io_data import rows,gzwrite
from preprocessing import transform,predict_saved
from core_features import NUMERIC,CATEGORICAL
CONFIG=dict(penalty='l2',C=1.,solver='lbfgs',max_iter=2000,class_weight=None,random_state=57)
HEADS=('H3','HF1','HL0')
def teacher_index(path):
 # Read IO bytes and identity metadata only. No future teacher payload is decoded.
 index={}
 for line in gzip.open(path,'rt'):
  identity=re.search(r'"entry_id"\s*:\s*"([^"]+)"',line).group(1)
  index[identity]=line
 return index

def past_labels(index,train_ids,head):
 result={}
 for key in train_ids:
  t=json.loads(index[key])
  if head=='H3':value=t['label_bigwinner3']
  else:
   ret=t['realized_net_return']
   value=None if ret is None else int(ret>=.01) if head=='HF1' else int(ret<=0)
  if value is not None:result[key]=int(value)
 return result

def fingerprint(train,labels):
 data=[{'entry_id':r['entry_id'],'numeric':r['numeric'],'categorical':r['categorical'],'label':labels[r['entry_id']]} for r in train if r['entry_id'] in labels]
 return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
 assert (OUT/'MODEL_PRECOMMIT_CODE_PIN.json').exists()
 runtime=rows(PRIVATE/'CORE_RUNTIME_CAUSAL.jsonl.gz');days=sorted({r['session'] for r in runtime});assert len(days)==58
 index=teacher_index(V2/'TEACHERS_EVALUATION.jsonl.gz');ledger=[];hashes={};predictions=[]
 for block,start in enumerate(range(20,58,5),1):
  past=set(days[:start]);future=set(days[start:start+5]);test=[r for r in runtime if r['session'] in future]
  prefix=[r for r in runtime if r['session'] in past and r['entry_minute']<920]
  ids=[r['entry_id'] for r in prefix];results={}
  for head in HEADS:
   labels=past_labels(index,ids,head);train=[r for r in prefix if r['entry_id'] in labels]
   assert set(ids).isdisjoint(r['entry_id'] for r in test)
   y=np.array([labels[r['entry_id']] for r in train],dtype=int);assert set(y)=={0,1}
   x,z,prep=transform(train,test,NUMERIC);clf=LogisticRegression(**CONFIG)
   with warnings.catch_warnings(record=True) as warning_list:
    warnings.simplefilter('always');clf.fit(x,y)
   assert not any(issubclass(w.category,ConvergenceWarning) for w in warning_list),'FIXED_LOGISTIC_CONVERGENCE_FAIL'
   # Evaluation teacher payloads remain unread. Saved coefficient inference materializes probabilities.
   artifact={'head':head,'block':block,'train_session_N':start,'train_through':days[start-1],'test_dates':days[start:start+5],'train_N':len(train),'train_positive_N':int(y.sum()),'train_missing_label_excluded_N':len(prefix)-len(train),'train_entry_ids':[r['entry_id'] for r in train],'base_rate':float(y.mean()),'parameters':CONFIG,'preprocessing':prep,'coef':clf.coef_[0].tolist(),'intercept':float(clf.intercept_[0]),'iterations':int(clf.n_iter_[0]),'training_input_hash':fingerprint(train,labels),'heldout_teacher_payload_reads_before_fit':0}
   prob=predict_saved(test,artifact);assert np.max(np.abs(prob-clf.predict_proba(z)[:,1]))<1e-12
   fn=f'{head}_BLOCK_{block:02d}.json';save(PRIVATE/'models'/fn,artifact);hashes[fn]=sha(PRIVATE/'models'/fn)
   results[head]=(prob,artifact['base_rate'],hashes[fn])
   ledger.append({k:artifact[k] for k in ('head','block','train_session_N','train_through','test_dates','train_N','train_positive_N','train_missing_label_excluded_N','base_rate','iterations','training_input_hash','heldout_teacher_payload_reads_before_fit')})
  for i,r in enumerate(test):
   predictions.append({**r,'block':block,**{h:{'p':float(results[h][0][i]),'base_rate':results[h][1],'model_hash':results[h][2]} for h in HEADS}})
 assert len(hashes)==24 and len(predictions)==1039
 gzwrite(PRIVATE/'NEW_HEAD_OOF_PREDICTIONS.jsonl.gz',predictions);save(PRIVATE/'MODEL_HASHES.json',hashes)
 save(OUT/'NEW_HEAD_FITS.json',{'jst':now(),'status':'FIXED24_HEAD_FITS_COMPLETE','fits':24,'H5_new_fits':0,'fit_ledger':ledger,'model_hashes':hashes,'predictions_hash':sha(PRIVATE/'NEW_HEAD_OOF_PREDICTIONS.jsonl.gz'),'sklearn_version':__import__('sklearn').__version__,'within_block_refits':0,'profile_refits':0,'sweeps':0,'safety':SAFETY})
 print(json.dumps({'fits':24,'OOF_N':1039,'heldout_teacher_payload_reads_before_fit':0}),flush=True)
if __name__=='__main__':main()
