"""Exactly one prescribed Slot fit per block; no Winner fit or sweeps."""
from common import *
from features import NUMERIC,CATEGORICAL
from slot_model import vector,probability
from sklearn.linear_model import LogisticRegression
import sklearn,numpy as np,warnings
from sklearn.exceptions import ConvergenceWarning
def main():
 block=int(sys.argv[1]);assert block in range(1,9)
 for b in range(1,9):assert json.loads((OUT/f'TEACHER_SUPPORT_BLOCK_{b:02d}.json').read_text())['support_pass']
 assert not (PRIVATE/f'SLOT_MODEL_BLOCK_{block:02d}.json').exists(),'WITHIN_BLOCK_REFIT_FORBIDDEN'
 rows_=rows(PRIVATE/f'TRAINING_TEACHERS_BLOCK_{block:02d}.jsonl.gz');split=json.loads((SOURCE/'repo/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json').read_text())['blocks'][block-1]
 assert all(r['session'] in split['train'] for r in rows_) and not set(split['train'])&set(split['test']) and max(split['train'])<min(split['test'])
 raw=np.array([[float(r['features']['numeric'][k]) if r['features']['numeric'][k] is not None else 0. for k in NUMERIC] for r in rows_]);means=raw.mean(axis=0);std=raw.std(axis=0);std[std==0]=1
 prep={'numeric_fields':NUMERIC,'numeric_mean':means.tolist(),'numeric_std':std.tolist(),'missing_indicators':NUMERIC,'missing_raw_fill':0,'indicator_scaling':'unscaled','categorical_fields':CATEGORICAL,'vocabulary':{k:sorted({r['features']['categorical'][k] for r in rows_}) for k in CATEGORICAL},'unknown_handling':'allzero','training_only':True}
 X=np.array([vector(r['features'],prep) for r in rows_]);y=np.array([int(r['teacher']=='ACCEPT') for r in rows_]);assert np.isfinite(X).all()
 save(PRIVATE/f'SLOT_FIT_STARTED_BLOCK_{block:02d}.json',{'exact_jst':now(),'block':block,'fit_count_for_block':1,'teacher_sha256':sha(PRIVATE/f'TRAINING_TEACHERS_BLOCK_{block:02d}.jsonl.gz'),'no_refit':True})
 with warnings.catch_warnings(record=True) as ws:
  warnings.simplefilter('always');model=LogisticRegression(penalty='l2',C=1.,solver='lbfgs',max_iter=2000,class_weight=None,random_state=57).fit(X,y)
  convergence=[str(w.message) for w in ws if issubclass(w.category,ConvergenceWarning)]
 assert not convergence,('SLOT_FIT_CONVERGENCE_BLOCKED',block,convergence)
 obj={'exact_jst':now(),'block':block,'family':'LogisticRegression','parameters':{'penalty':'l2','C':1.,'solver':'lbfgs','max_iter':2000,'class_weight':None,'random_state':57},'sklearn_version':sklearn.__version__,'classes':model.classes_.tolist(),'coef':model.coef_[0].tolist(),'intercept':float(model.intercept_[0]),'n_iter':model.n_iter_.tolist(),'preprocessing':prep,'train_N':len(y),'ACCEPT_N':int(y.sum()),'RESERVE_N':int(len(y)-y.sum()),'train_sessions':split['train'],'test_sessions':split['test'],'training_state_keys':[r['state_key'] for r in rows_],'teacher_sha256':sha(PRIVATE/f'TRAINING_TEACHERS_BLOCK_{block:02d}.jsonl.gz'),'effective_teacher_precommit_sha256':sha(OUT/'TEACHER_PRECOMMIT_U5_PRIORITY_AMENDMENT.json'),'model_precommit_sha256':sha(OUT/'SLOT_MODEL_PRECOMMIT.json'),'winner_fit':0,'within_block_refit':0,'threshold':.5}
 save(PRIVATE/f'SLOT_MODEL_BLOCK_{block:02d}.json',obj);save(OUT/'models'/f'SLOT_MODEL_BLOCK_{block:02d}.json',obj)
 fitted=model.predict_proba(X)[:,1];manual=np.array([probability(r['features'],obj) for r in rows_]);assert np.max(np.abs(fitted-manual))<1e-12
 save(OUT/f'SLOT_FIT_RECEIPT_BLOCK_{block:02d}.json',{'exact_jst':now(),'block':block,'model_sha256':sha(PRIVATE/f'SLOT_MODEL_BLOCK_{block:02d}.json'),'train_N':len(y),'iterations':obj['n_iter'],'accept_rate':float(y.mean()),'probability_manual_max_abs_diff':float(np.max(np.abs(fitted-manual))),'winner_fit':0,'slot_fit_this_block':1,'within_block_refit':0,'threshold_sweep':0})
 print(json.dumps({'block':block,'train_N':len(y),'accept_rate':float(y.mean()),'iterations':obj['n_iter'],'model_sha256':sha(PRIVATE/f'SLOT_MODEL_BLOCK_{block:02d}.json')}))
if __name__=='__main__':main()
