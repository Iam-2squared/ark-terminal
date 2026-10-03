"""Exactly 30 fixed temporal fits. Training-only preprocessing/calibration."""
import os
os.environ.setdefault('OMP_NUM_THREADS','8')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import argparse,collections,pickle,time,gc,mmap
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
import sklearn
from common import *
from price_features import P0_NAMES,P1_NUM,P1_CAT
class TrainPreprocessor:
 def fit(self,num,cat=None):
  with __import__('warnings').catch_warnings():
   __import__('warnings').simplefilter('ignore');self.median=np.nanmedian(num,axis=0)
  self.median=np.where(np.isfinite(self.median),self.median,0.);self.known=[]
  if cat is not None:
   for c in cat.T:self.known.append(sorted(set(int(x) for x in c)))
  self.training_rows=len(num);return self
 def transform(self,num,cat=None,out=None):
  d=num.shape[1];width=2*d+sum(len(k)+1 for k in self.known);arr=np.lib.format.open_memmap(out,mode='w+',dtype=np.float64,shape=(len(num),width)) if out else np.empty((len(num),width),dtype=np.float64)
  for lo in range(0,len(num),2048):
   hi=min(lo+2048,len(num));chunk=num[lo:hi];missing=~np.isfinite(chunk);arr[lo:hi,:d]=np.where(missing,self.median,chunk);arr[lo:hi,d:2*d]=missing;offset=2*d
   if cat is not None:
    for j,known in enumerate(self.known):
     # Final column is explicit unseen UNKNOWN; reserved specials unchanged.
     arr[lo:hi,offset:offset+len(known)+1]=0;idx=np.searchsorted(known,cat[lo:hi,j]);clipped=np.minimum(idx,max(len(known)-1,0));seen=(idx<len(known))&(np.asarray(known)[clipped]==cat[lo:hi,j]);idx=np.where(seen,idx,len(known));arr[np.arange(lo,hi),offset+idx]=1;offset+=len(known)+1
  if out:arr.flush();arr._mmap.madvise(mmap.MADV_DONTNEED)
  return arr
def percentile(sorted_ref,pred):return (np.searchsorted(sorted_ref,pred,'left')+np.searchsorted(sorted_ref,pred,'right'))/(2*len(sorted_ref))
def run():
 cfg=read(HERE/'MODEL_SCORE_POLICY_FREEZE.json');folds=read(HERE/'SPLIT_PRECOMMIT.json')['folds'];grid=list(lines(HERE/'PERSISTENT_GRID.jsonl.gz'));sessions=np.asarray([r['session'] for r in grid]);X=np.load(HERE/'PRIVATE_INPUTS/features_numeric.npy',mmap_mode='r');C=np.load(HERE/'PRIVATE_INPUTS/features_categories.npy',mmap_mode='r');Y=np.load(HERE/'PRIVATE_INPUTS/targets.npy',mmap_mode='r');vocab=read(HERE/'PRIVATE_INPUTS/category_vocabulary.json')
 assert len(X)==len(grid)==len(Y);primary=np.flatnonzero([r['canonical'] for r in grid]);models=HERE/'PRIVATE_MODELS';models.mkdir(exist_ok=True);fits=[];OOF={};ledger_path=HERE/'FIT_LEDGER.json';t0=time.time()
 if ledger_path.exists():
  ledger=read(ledger_path);fits=ledger['runs'];assert all(f['status']=='COMPLETED' for f in fits),'RESERVED_FIT_CANNOT_BE_RETRIED';assert len(fits)==ledger['fits_reserved']==ledger['fits_completed']
 else:write(ledger_path,{'fits_reserved':0,'fits_completed':0,'hard_cap':36,'planned':30,'runs':[]})
 matrix_dir=HERE/'PRIVATE_INPUTS/_matrix_work';matrix_dir.mkdir(exist_ok=True)
 for family in ('P0','P1'):
  family_done=[f for f in fits if f['family']==family]
  if len(family_done)==15 and (HERE/'PRIVATE_INPUTS'/f'oof_{family}.npz').exists() and all((HERE/f'OOF_{family}_{head}.jsonl.gz').exists() for head in HEADS):
   print(json.dumps({'family':family,'completed_fits_reused':15,'additional_fits':0}),flush=True);continue
  pred=np.full((len(grid),3),np.nan);pctiles=np.full_like(pred,np.nan);fold_ids=np.zeros(len(grid),int);thresholds=np.full((len(grid),4),np.nan)
  for fold in folds:
   tr=np.flatnonzero(np.isin(sessions,fold['train']));te=np.flatnonzero(np.isin(sessions,fold['test']));assert len(set(sessions[tr])&set(sessions[te]))==0 and max(sessions[tr])<min(sessions[te]);dims=len(P0_NAMES) if family=='P0' else X.shape[1]
   completed={(f['family'],f['fold'],f['head']):f for f in fits};all_done=all((family,fold['id'],head) in completed for head in HEADS);prepf=models/f'{family}_F{fold["id"]}_preprocessor.pkl'
   prep=pickle.loads(prepf.read_bytes()) if all_done else TrainPreprocessor().fit(X[tr,:dims],C[tr] if family=='P1' else None)
   if family=='P1' and not all_done:
    for j,vs in enumerate(vocab):
     for special in ('__MISSING__','__UNKNOWN_HISTORY__','__FORMAL_NULL__'):
      if special in vs:prep.known[j]=sorted(set(prep.known[j]+[vs.index(special)]))
   A=None if all_done else prep.transform(X[tr,:dims],C[tr] if family=='P1' else None,matrix_dir/'train.npy');B=prep.transform(X[te,:dims],C[te] if family=='P1' else None,matrix_dir/'test.npy');train_preds=np.load(models/f'{family}_F{fold["id"]}_train_predictions.npy') if all_done else np.empty((len(tr),3));train_pct=np.empty_like(train_preds)
   if not all_done:prepf.write_bytes(pickle.dumps(prep,protocol=5));np.save(models/f'{family}_F{fold["id"]}_train_indices.npy',tr)
   for h,head in enumerate(HEADS):
    if (family,fold['id'],head) in completed:
     entry=completed[(family,fold['id'],head)];model=pickle.loads((models/f'{family}_F{fold["id"]}_{head}.pkl').read_bytes());ref=np.load(models/f'{family}_F{fold["id"]}_{head}_train_prediction_reference.npy');vp=model.predict(B);pred[te,h]=vp;pctiles[te,h]=percentile(ref,vp);train_pct[:,h]=percentile(ref,train_preds[:,h]);print(json.dumps({'family':family,'fold':fold['id'],'head':head,'completed_fit_reused':True,'additional_fits':0}),flush=True);continue
    good=np.isfinite(Y[tr,h]);assert int(sum(good))>=40,'INSUFFICIENT_TRAIN_TARGET_SUPPORT'
    entry={'family':family,'fold':fold['id'],'head':head,'reserved_at_jst':now(),'train_rows':len(tr),'head_train_rows':int(sum(good)),'test_rows':len(te),'model_parameters':cfg['parameters'],'preprocessor_sha256':sha(prepf),'train_sessions':fold['train'],'test_sessions':fold['test'],'train_row_indices_sha256':sha(models/f'{family}_F{fold["id"]}_train_indices.npy'),'fit_ordinal':len(fits)+1,'status':'RESERVED'}
    fits.append(entry);assert len(fits)<=30<=36;write(ledger_path,{'fits_reserved':len(fits),'fits_completed':sum(f['status']=='COMPLETED' for f in fits),'hard_cap':36,'planned':30,'runs':fits})
    train_head=np.lib.format.open_memmap(matrix_dir/'head.npy',mode='w+',dtype=np.float64,shape=(int(sum(good)),A.shape[1]));selected=np.flatnonzero(good)
    for lo in range(0,len(selected),2048):train_head[lo:lo+2048]=A[selected[lo:lo+2048]]
    train_head.flush();train_head._mmap.madvise(mmap.MADV_DONTNEED);model=HistGradientBoostingRegressor(**cfg['parameters']);model.fit(train_head,Y[tr[good],h]);del train_head;gc.collect();tp=model.predict(A);vp=model.predict(B);modelp=models/f'{family}_F{fold["id"]}_{head}.pkl';modelp.write_bytes(pickle.dumps(model,protocol=5));ref=np.sort(tp);np.save(models/f'{family}_F{fold["id"]}_{head}_train_prediction_reference.npy',ref)
    pred[te,h]=vp;pctiles[te,h]=percentile(ref,vp);train_preds[:,h]=tp;train_pct[:,h]=percentile(ref,tp);entry.update(status='COMPLETED',completed_at_jst=now(),model_sha256=sha(modelp),reference_sha256=sha(models/f'{family}_F{fold["id"]}_{head}_train_prediction_reference.npy'),MAE=float(np.mean(abs(vp[np.isfinite(Y[te,h])]-Y[te[np.isfinite(Y[te,h])],h]))),Spearman=float(spearmanr(vp[np.isfinite(Y[te,h])],Y[te[np.isfinite(Y[te,h])],h]).statistic))
    write(ledger_path,{'fits_reserved':len(fits),'fits_completed':sum(f['status']=='COMPLETED' for f in fits),'hard_cap':36,'planned':30,'runs':fits});print(json.dumps({'fit_completed':len(fits),'family':family,'fold':fold['id'],'head':head,'seconds':round(time.time()-t0,1)}),flush=True)
   train_score=(train_pct[:,0]+train_pct[:,1]+1-train_pct[:,2])/3;ths=np.quantile(train_score,list(POLICIES.values()),method='linear');thresholds[te]=ths;fold_ids[te]=fold['id'];np.save(models/f'{family}_F{fold["id"]}_train_predictions.npy',train_preds);np.save(models/f'{family}_F{fold["id"]}_train_score.npy',train_score)
   write(models/f'{family}_F{fold["id"]}_calibration.json',{'family':family,'fold':fold['id'],'training_score_N':len(train_score),'thresholds':dict(zip(POLICIES,map(float,ths))),'train_score_sha256':sha(models/f'{family}_F{fold["id"]}_train_score.npy'),'quantile_method':'linear','transform':'midrank empirical training prediction distribution','absolute_probability':False})
   del A,B;gc.collect()
   for temporary in matrix_dir.glob('*.npy'):temporary.unlink()
  assert np.isfinite(pred[primary]).all() and (fold_ids[primary]>0).all()
  np.savez_compressed(HERE/'PRIVATE_INPUTS'/f'oof_{family}.npz',row_indices=primary,predictions=pred[primary],percentiles=pctiles[primary],score=(pctiles[primary,0]+pctiles[primary,1]+1-pctiles[primary,2])/3,thresholds=thresholds[primary],fold=fold_ids[primary])
  for h,head in enumerate(HEADS):
   def head_records():
    for i in primary:yield {'row_index':int(i),'row_id':grid[i]['row_id'],'watch_key':grid[i]['watch_key'],'session':grid[i]['session'],'intent_minute':grid[i]['intent_minute'],'family':family,'head':head,'fold':int(fold_ids[i]),'prediction':float(pred[i,h]),'percentile':float(pctiles[i,h]),'actual_training_target':float(Y[i,h]) if np.isfinite(Y[i,h]) else None,'target_used_by_decision':False}
   write_lines(HERE/f'OOF_{family}_{head}.jsonl.gz',head_records())
 def score_records():
  for family in ('P0','P1'):
   z=load_npz(HERE/'PRIVATE_INPUTS'/f'oof_{family}.npz')
   for j,i in enumerate(z['row_indices']):yield {'row_index':int(i),'row_id':grid[i]['row_id'],'watch_key':grid[i]['watch_key'],'session':grid[i]['session'],'intent_minute':grid[i]['intent_minute'],'family':family,'fold':int(z['fold'][j]),'U_pctile':float(z['percentiles'][j,0]),'Q_pctile':float(z['percentiles'][j,1]),'D_pctile':float(z['percentiles'][j,2]),'UPTREND_SCORE':float(z['score'][j]),'thresholds':dict(zip(POLICIES,map(float,z['thresholds'][j]))),'is_probability':False}
 write_lines(HERE/'UPTREND_SCORE_ROWS.jsonl.gz',score_records())
 write(HERE/'OOF_MODEL_RECEIPT.json',{'saved_at_jst':now(),'fits':len(fits),'hard_cap':36,'OOF_rows_per_family':len(primary),'sklearn_version':sklearn.__version__,'model_parameters':cfg['parameters'],'preprocessing_scope':'outer train feature rows only','head_training_scope':'finite targets in outer training sessions only','calibration':'all training grid in-sample predictions, no extra fits','development_evaluation':'outer test only','searches':cfg['search_counts'],'safety':SAFETY})
if __name__=='__main__':run()
