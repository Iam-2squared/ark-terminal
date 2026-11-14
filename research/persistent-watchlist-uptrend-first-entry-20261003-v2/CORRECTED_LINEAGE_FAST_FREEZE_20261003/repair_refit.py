"""Exactly twenty authorized corrected Q/D fits; no UPSIDE fit or search."""
import os
os.environ.setdefault('OMP_NUM_THREADS','8')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from repair_utils import *
import numpy as np,pickle,shutil,time,gc,mmap
from sklearn.ensemble import HistGradientBoostingRegressor
from model_oof import TrainPreprocessor,percentile

def fit_ledger(runs):
 return {'document_id':DOCUMENT_ID,'saved_at_jst':now(),'Primary_Freeze_Target':'P1_Q70','historical_completed':30,'fits_reserved':len(runs),'fits_completed':sum(r['status']=='COMPLETED' for r in runs),'incremental_hard_cap':20,'planned':20,'cumulative_completed':30+sum(r['status']=='COMPLETED' for r in runs),'UPSIDE_refits':0,'all_searches':0,'runs':runs,'safety':SAFETY}

def predict_rows(model,prep,X,C,indices,dims,family):
 out=np.empty(len(indices),np.float64)
 for lo in range(0,len(indices),2048):
  ix=indices[lo:lo+2048]
  a=prep.transform(X[ix,:dims],C[ix] if family=='P1' else None)
  out[lo:lo+len(ix)]=model.predict(a)
 return out

def run():
 frozen=read(HERE/'CORRECTED_TEACHER_FREEZE_RECEIPT.json');scope=read(HERE/'REPAIR_SCOPE_PRECOMMIT.json')
 assert frozen['U_target_eligibility_unchanged'] and scope['Primary_Freeze_Target']=='P1_Q70'
 assert scope['authorized_incremental_fits']==scope['incremental_hard_cap']==20
 ledger_path=HERE/'CORRECTED_FIT_LEDGER.json'
 if ledger_path.exists():
  prior=read(ledger_path)
  assert prior['fits_reserved']==0,'No reserved fit may be retried or repeated'
 cfg=read(BASE/'MODEL_SCORE_POLICY_FREEZE.json');folds=read(BASE/'SPLIT_PRECOMMIT.json')['folds'];ff=read(BASE/'FEATURE_FREEZE.json');oldledger=read(BASE/'FIT_LEDGER.json')
 X=np.load(BASE/'PRIVATE_INPUTS/features_numeric.npy',mmap_mode='r');C=np.load(BASE/'PRIVATE_INPUTS/features_categories.npy',mmap_mode='r');Y=np.load(BASE/'PRIVATE_INPUTS/targets.npy',mmap_mode='r')
 assert sha(BASE/'PRIVATE_INPUTS/targets.npy')==frozen['corrected_targets_sha256']
 grid=list(rows(BASE/'PERSISTENT_GRID.jsonl.gz'));sessions=np.asarray([r['session'] for r in grid]);primary=np.flatnonzero([r['canonical'] for r in grid]);assert len(X)==len(grid)==len(Y)
 models=HERE/'PRIVATE_MODELS';inputs=HERE/'PRIVATE_INPUTS';work=inputs/'_matrix_work'
 for p in [models,inputs,work]:p.mkdir(parents=True,exist_ok=True)
 runs=[];write(ledger_path,fit_ledger(runs));active=[];t0=time.time()
 for family in ['P0','P1']:
  original_oof=load_npz(BASE/'PRIVATE_INPUTS'/f'oof_{family}.npz')
  assert np.array_equal(original_oof['row_indices'],primary)
  pred=np.full((len(grid),3),np.nan);pct=np.full_like(pred,np.nan);fold_ids=np.zeros(len(grid),int);thresholds=np.full((len(grid),4),np.nan)
  pred[primary,0]=original_oof['predictions'][:,0];pct[primary,0]=original_oof['percentiles'][:,0]
  dims=len(ff['P0_numeric']) if family=='P0' else X.shape[1]
  for fold in folds:
   fid=fold['id'];tr=np.flatnonzero(np.isin(sessions,fold['train']));te=np.flatnonzero(np.isin(sessions,fold['test']))
   assert max(sessions[tr])<min(sessions[te]) and not(set(sessions[tr])&set(sessions[te]))
   assert set(te).issubset(set(primary))
   prepf=models/f'{family}_F{fid}_preprocessor.pkl';shutil.copyfile(BASE/'PRIVATE_MODELS'/prepf.name,prepf);prep=pickle.loads(prepf.read_bytes())
   assert prep.training_rows==len(tr)
   train_indices=models/f'{family}_F{fid}_train_indices.npy';shutil.copyfile(BASE/'PRIVATE_MODELS'/train_indices.name,train_indices);assert np.array_equal(np.load(train_indices),tr)
   old_u=next(r for r in oldledger['runs'] if (r['family'],r['fold'],r['head'])==(family,fid,'UPSIDE'))
   for name in [f'{family}_F{fid}_UPSIDE.pkl',f'{family}_F{fid}_UPSIDE_train_prediction_reference.npy']:shutil.copyfile(BASE/'PRIVATE_MODELS'/name,models/name)
   assert np.isfinite(Y[tr,0]).sum()==old_u['head_train_rows']
   active.append({**old_u,'lineage':'UNMODIFIED_ORIGINAL_UPSIDE_REUSE','additional_fit':False})
   old_train=np.load(BASE/'PRIVATE_MODELS'/f'{family}_F{fid}_train_predictions.npy',mmap_mode='r');train_predictions=np.empty((len(tr),3),np.float64);train_predictions[:,0]=old_train[:,0];del old_train
   train_pct=np.empty_like(train_predictions);uref=np.load(models/f'{family}_F{fid}_UPSIDE_train_prediction_reference.npy');train_pct[:,0]=percentile(uref,train_predictions[:,0])
   for h,head in [(1,'QUALITY'),(2,'ADVERSE')]:
    good=np.isfinite(Y[tr,h]);eligible=tr[good];testgood=np.isfinite(Y[te,h]);assert len(eligible)>=40
    key=[family,fid,head];assert key in scope['authorized_fit_keys'] and len(runs)<20
    targetp=models/f'{family}_F{fid}_{head}_training_target.npy';np.save(targetp,Y[eligible,h]);eligp=models/f'{family}_F{fid}_{head}_eligible_train_indices.npy';np.save(eligp,eligible);testp=models/f'{family}_F{fid}_{head}_eligible_test_indices.npy';np.save(testp,te[testgood])
    entry={'family':family,'fold':fid,'head':head,'reserved_at_jst':now(),'train_rows':len(tr),'head_train_rows':len(eligible),'test_rows':len(te),'head_test_rows':int(testgood.sum()),'model_parameters':cfg['parameters'],'preprocessor_sha256':sha(prepf),'train_sessions':fold['train'],'test_sessions':fold['test'],'train_row_indices_sha256':sha(train_indices),'eligible_train_indices_sha256':sha(eligp),'eligible_test_indices_sha256':sha(testp),'target_lineage_sha256':sha(targetp),'corrected_targets_sha256':frozen['corrected_targets_sha256'],'fit_ordinal':len(runs)+1,'cumulative_fit_ordinal':31+len(runs),'status':'RESERVED','training_preprocessor_reused_byte_identical':True}
    runs.append(entry);write(ledger_path,fit_ledger(runs))
    width=2*dims+sum(len(k)+1 for k in prep.known);train_head=np.lib.format.open_memmap(work/'head.npy',mode='w+',dtype=np.float64,shape=(len(eligible),width))
    for lo in range(0,len(eligible),2048):
     ix=eligible[lo:lo+2048];train_head[lo:lo+len(ix)]=prep.transform(X[ix,:dims],C[ix] if family=='P1' else None)
    train_head.flush();train_head._mmap.madvise(mmap.MADV_DONTNEED)
    model=HistGradientBoostingRegressor(**cfg['parameters']);model.fit(train_head,Y[eligible,h]);del train_head;gc.collect()
    modelp=models/f'{family}_F{fid}_{head}.pkl';modelp.write_bytes(pickle.dumps(model,protocol=5))
    tp=predict_rows(model,prep,X,C,tr,dims,family);vp=predict_rows(model,prep,X,C,te,dims,family);ref=np.sort(tp);refp=models/f'{family}_F{fid}_{head}_train_prediction_reference.npy';np.save(refp,ref)
    pred[te,h]=vp;pct[te,h]=percentile(ref,vp);train_predictions[:,h]=tp;train_pct[:,h]=percentile(ref,tp)
    entry.update(status='COMPLETED',completed_at_jst=now(),model_sha256=sha(modelp),reference_sha256=sha(refp),lineage='CORRECTED_CALENDAR_Q_D_REFIT',additional_fit=True)
    active.append(entry);write(ledger_path,fit_ledger(runs));print(json.dumps({'repair_fit_completed':len(runs),'incremental_hard_cap':20,'cumulative_completed':30+len(runs),'family':family,'fold':fid,'head':head,'train_eligible':len(eligible),'test_eligible':int(testgood.sum()),'elapsed_s':round(time.time()-t0,1)}),flush=True)
    del model,tp,vp,ref;gc.collect();(work/'head.npy').unlink()
   train_score=(train_pct[:,0]+train_pct[:,1]+1-train_pct[:,2])/3;ths=np.quantile(train_score,list(POLICIES.values()),method='linear');thresholds[te]=ths;fold_ids[te]=fid
   np.save(models/f'{family}_F{fid}_train_predictions.npy',train_predictions);np.save(models/f'{family}_F{fid}_train_score.npy',train_score)
   write(models/f'{family}_F{fid}_calibration.json',{'family':family,'fold':fid,'training_score_N':len(tr),'thresholds':dict(zip(POLICIES,map(float,ths))),'train_score_sha256':sha(models/f'{family}_F{fid}_train_score.npy'),'quantile_method':'linear','transform':'midrank empirical training prediction distribution','absolute_probability':False,'corrected_Q_D':True,'UPSIDE_unchanged_reuse':True})
   del prep,train_predictions,train_pct,train_score;gc.collect()
  assert np.isfinite(pred[primary]).all() and np.isfinite(pct[primary]).all() and (fold_ids[primary]>0).all()
  np.savez_compressed(inputs/f'oof_{family}.npz',row_indices=primary,predictions=pred[primary],percentiles=pct[primary],score=(pct[primary,0]+pct[primary,1]+1-pct[primary,2])/3,thresholds=thresholds[primary],fold=fold_ids[primary])
  assert np.array_equal(pred[primary,0],original_oof['predictions'][:,0]) and np.array_equal(pct[primary,0],original_oof['percentiles'][:,0])
  shutil.copyfile(BASE/f'OOF_{family}_UPSIDE.jsonl.gz',HERE/f'OOF_{family}_UPSIDE.jsonl.gz')
  for h,head in [(1,'QUALITY'),(2,'ADVERSE')]:
   def recs():
    for i in primary:
     yield {'row_index':int(i),'row_id':grid[i]['row_id'],'watch_key':grid[i]['watch_key'],'session':grid[i]['session'],'intent_minute':grid[i]['intent_minute'],'family':family,'head':head,'fold':int(fold_ids[i]),'prediction':float(pred[i,h]),'percentile':float(pct[i,h]),'actual_training_target':float(Y[i,h]) if np.isfinite(Y[i,h]) else None,'target_used_by_decision':False,'lineage':'CORRECTED_CALENDAR_Q_D_REFIT'}
   write_rows(HERE/f'OOF_{family}_{head}.jsonl.gz',recs())
  del pred,pct,original_oof;gc.collect()
 assert len(runs)==20 and all(r['status']=='COMPLETED' for r in runs) and len(active)==30
 write(HERE/'FIT_LEDGER.json',{'fits_reserved':30,'fits_completed':30,'planned':30,'hard_cap':30,'active_models_only':True,'original_UPSIDE_reuse':10,'new_corrected_Q_D':20,'cumulative_historical_ledger':50,'runs':active})
 write(HERE/'CORRECTED_REFIT_COMPLETION_RECEIPT.json',{'saved_at_jst':now(),'additional_fits':20,'corrected_Q_D_complete':20,'UPSIDE_fit_reuse':10,'UPSIDE_additional_fit':0,'cumulative_completed':50,'corrected_families':['P0','P1'],'corrected_heads':['QUALITY','ADVERSE'],'folds':[1,2,3,4,5],'OOF_rows_per_family':len(primary),'searches':0,'safety':SAFETY})

if __name__=='__main__':run()
