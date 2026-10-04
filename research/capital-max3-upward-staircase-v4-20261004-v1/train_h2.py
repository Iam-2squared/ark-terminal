"""Exactly eight new H2 expanding-origin fits; future teacher payload unread."""
import re,json,warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from common import *
from core_features import NUMERIC
from preprocessing import transform,predict_saved
def teacher_index(path):
 index={}
 for line in gzip.open(path,'rt'):
  identity=re.search(r'"entry_id"\s*:\s*"([^"]+)"',line).group(1)
  assert identity not in index;index[identity]=line
 return index
def main():
 assert (OUT/'MODEL_PRECOMMIT_CODE_PIN.json').exists()
 save(PRIVATE/'H2_FITS_STARTED.json',{'JST':now(),'planned_fits':8,'refit_permitted':False})
 runtime=rows(SRC/'capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz');days=sorted({r['session'] for r in runtime})
 index=teacher_index(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz');cfg=json.loads((OUT/'DESIGN_PRECOMMIT.json').read_text())['logistic']
 hashes=json.loads((PRIVATE/'REUSED_MODEL_HASHES.json').read_text());ledger=[];predictions=[]
 for block,start in enumerate(range(20,58,5),1):
  past=set(days[:start]);future=set(days[start:start+5]);test=[r for r in runtime if r['session'] in future]
  train=[r for r in runtime if r['session'] in past and r['entry_minute']<920];ids=[r['entry_id'] for r in train]
  labels={key:int(json.loads(index[key])['potential_return']>=.02) for key in ids}
  y=np.array([labels[key] for key in ids],dtype=int);assert set(y)=={0,1},'H2_MISSING_TRAINING_CLASS'
  h3=json.loads((PRIVATE/'models'/f'H3_BLOCK_{block:02d}.json').read_text());h5=json.loads((PRIVATE/'models'/f'H5_BLOCK_{block:02d}.json').read_text())
  assert ids==h3['train_entry_ids']==h5['train_entry_ids'];assert h3['test_dates']==days[start:start+5]==h5['test_dates']
  x,z,prep=transform(train,test,NUMERIC);assert prep==h3['preprocessing']==h5['preprocessing']
  clf=LogisticRegression(**cfg)
  with warnings.catch_warnings(record=True) as warning_list:
   warnings.simplefilter('always');clf.fit(x,y)
  assert not any(issubclass(w.category,ConvergenceWarning) for w in warning_list),'FIXED_LOGISTIC_CONVERGENCE_FAIL'
  fingerprint=hashlib.sha256(json.dumps([{'entry_id':r['entry_id'],'numeric':r['numeric'],'categorical':r['categorical'],'label':labels[r['entry_id']]} for r in train],sort_keys=True,separators=(',',':')).encode()).hexdigest()
  artifact={'head':'H2','block':block,'train_session_N':start,'train_through':days[start-1],'test_dates':days[start:start+5],'train_N':len(train),'train_positive_N':int(y.sum()),'train_entry_ids':ids,'base_rate':float(y.mean()),'parameters':cfg,'preprocessing':prep,'coef':clf.coef_[0].tolist(),'intercept':float(clf.intercept_[0]),'iterations':int(clf.n_iter_[0]),'training_input_hash':fingerprint,'heldout_teacher_payload_reads_before_fit':0}
  assert artifact['base_rate']>=h3['base_rate']>=h5['base_rate'] and artifact['base_rate']+h3['base_rate']+h5['base_rate']>0,'CONTRACT_FAIL_BASE_ORDER'
  fn=f'H2_BLOCK_{block:02d}.json';save(PRIVATE/'models'/fn,artifact);hashes[fn]=sha(PRIVATE/'models'/fn)
  probs=predict_saved(test,artifact);assert np.max(np.abs(probs-clf.predict_proba(z)[:,1]))<1e-12
  for r,p in zip(test,probs):predictions.append({'entry_id':r['entry_id'],'block':block,'p2':float(p),'base2':artifact['base_rate'],'model_hash':hashes[fn]})
  ledger.append({k:artifact[k] for k in ('head','block','train_session_N','train_through','test_dates','train_N','train_positive_N','base_rate','iterations','training_input_hash','heldout_teacher_payload_reads_before_fit')})
 assert len(predictions)==1039 and len(list((PRIVATE/'models').glob('H2_BLOCK_*.json')))==8
 gzwrite(PRIVATE/'H2_OOF_PREDICTIONS.jsonl.gz',predictions);save(PRIVATE/'MODEL_HASHES.json',hashes)
 save(OUT/'H2_FITS.json',{'JST':now(),'fit_count':8,'fit_ledger':ledger,'H3_new_fit':0,'H5_new_fit':0,'HF1_HL0_H10_Movement_fit':0,'within_block_refit':0,'profile_refit':0,'hyperparameter_sweep':0,'predictions_hash':sha(PRIVATE/'H2_OOF_PREDICTIONS.jsonl.gz'),'model_hashes':hashes,'sklearn_version':__import__('sklearn').__version__,'heldout_teacher_payload_reads_before_fit':0,'Safety':SAFETY})
 checkpoint('U4_H2_ROLLING_ORIGIN_FITS','H2_FIXED8_FITS_COMPLETE',{'H2_fits':8,'OOF_N':1039,'H3_H5_fit':0})
 print(json.dumps({'H2_fits':8,'OOF_N':1039}),flush=True)
if __name__=='__main__':main()
