"""Seal corrected OOF and score lineage; uses completed fits only, fit=0."""
from repair_utils import *
import numpy as np,shutil,os

def run():
 ledger=read(HERE/'CORRECTED_FIT_LEDGER.json');assert ledger['fits_completed']==ledger['fits_reserved']==20
 active=read(HERE/'FIT_LEDGER.json');assert len(active['runs'])==30
 grid=list(rows(BASE/'PERSISTENT_GRID.jsonl.gz'));primary=np.flatnonzero([r['canonical'] for r in grid])
 files={};reuse=[]
 for f in ['P0','P1']:
  old=load_npz(BASE/'PRIVATE_INPUTS'/f'oof_{f}.npz');new=load_npz(HERE/'PRIVATE_INPUTS'/f'oof_{f}.npz')
  assert np.array_equal(new['row_indices'],old['row_indices']) and np.array_equal(new['fold'],old['fold'])
  assert np.array_equal(new['predictions'][:,0],old['predictions'][:,0]) and np.array_equal(new['percentiles'][:,0],old['percentiles'][:,0])
  assert np.isfinite(new['predictions']).all() and np.isfinite(new['percentiles']).all()
  assert np.array_equal(new['score'],(new['percentiles'][:,0]+new['percentiles'][:,1]+1-new['percentiles'][:,2])/3)
  for head in HEADS:
   name=f'OOF_{f}_{head}.jsonl.gz';n=sum(1 for _ in rows(HERE/name));assert n==len(primary)
   if head=='UPSIDE':assert sha(HERE/name)==sha(BASE/name)
   files[name]={'rows':n,'sha256':sha(HERE/name),'lineage':'UNMODIFIED_ORIGINAL_UPSIDE' if head=='UPSIDE' else 'CORRECTED_CALENDAR_Q_D_REFIT'}
  reuse.append({'family':f,'U_prediction_array_unchanged':True,'U_percentile_array_unchanged':True,'U_OOF_byte_hash_unchanged':True,'original_U_OOF_sha256':sha(BASE/f'OOF_{f}_UPSIDE.jsonl.gz')})
 def score_rows():
  for f in ['P0','P1']:
   z=load_npz(HERE/'PRIVATE_INPUTS'/f'oof_{f}.npz')
   for j,i in enumerate(z['row_indices']):
    yield {'row_index':int(i),'row_id':grid[i]['row_id'],'watch_key':grid[i]['watch_key'],'session':grid[i]['session'],'intent_minute':grid[i]['intent_minute'],'family':f,'fold':int(z['fold'][j]),'U_pctile':float(z['percentiles'][j,0]),'Q_pctile':float(z['percentiles'][j,1]),'D_pctile':float(z['percentiles'][j,2]),'UPTREND_SCORE':float(z['score'][j]),'thresholds':dict(zip(POLICIES,map(float,z['thresholds'][j]))),'is_probability':False,'Q_D_lineage':'CORRECTED_CALENDAR_Q_D_REFIT'}
 write_rows(HERE/'UPTREND_SCORE_ROWS.jsonl.gz',score_rows());files['UPTREND_SCORE_ROWS.jsonl.gz']={'rows':2*len(primary),'sha256':sha(HERE/'UPTREND_SCORE_ROWS.jsonl.gz')}
 calibration=[]
 for f in ['P0','P1']:
  for i in range(1,6):calibration.append(read(HERE/'PRIVATE_MODELS'/f'{f}_F{i}_calibration.json'))
 receipt={'document_id':DOCUMENT_ID,'saved_at_jst':now(),'status':'CORRECTED_OOF_COMPLETE','Primary_Freeze_Target':'P1_Q70','corrected_Q_D_fit_N':20,'unmodified_UPSIDE_fit_reuse_N':10,'additional_UPSIDE_fits':0,'mixed_old_bug_Q_D_predictions':0,'active_model_N':30,'cumulative_completed_fits':50,'rows_per_family':len(primary),'files':files,'UPSIDE_reuse':reuse,'model_lineage':[{'family':r['family'],'fold':r['fold'],'head':r['head'],'model_sha256':r['model_sha256'],'preprocessor_sha256':r['preprocessor_sha256'],'reference_sha256':r['reference_sha256'],'lineage':r['lineage']} for r in active['runs']],'calibration':calibration,'percentile_method':'(strictly_less + .5*equal)/N of all outer training grid predictions','score':'(U_pctile+Q_pctile+(1-D_pctile))/3','quantile_method':'np.quantile(train score,q,method=linear)','quantiles':POLICIES,'new_threshold_method':0,'threshold_optimization':0,'Entry_day_or_capacity_target':None,'source_teacher_evaluator_fields_in_decision':0,'safety':SAFETY}
 write(HERE/'CORRECTED_OOF_LINEAGE_RECEIPT.json',receipt)
 # Immutable inputs and unchanged source copies let the separate auditor use one
 # package root. No private source, feature, or old fit is overwritten.
 for name in ['PERSISTENT_GRID.jsonl.gz','WATCH_RECORDS.jsonl.gz','TEACHER_LABELS.jsonl.gz','STATE_FEATURE_METADATA.jsonl.gz','STATE_TIMELINE_WATCH_RECEIPTS.jsonl.gz','FEATURE_FREEZE.json','SPLIT_PRECOMMIT.json','MODEL_SCORE_POLICY_FREEZE.json','WATCH_IDENTITY_CONTRACT.json','SELECTOR_REPEAT_AUDIT.json','first_entry.py','model_oof.py','teacher.py','causal_features.py','common.py']:
  dest=HERE/name
  if not dest.exists():os.link(BASE/name,dest)
 for name in ['features_numeric.npy','features_categories.npy','targets.npy','category_vocabulary.json','watch_row_ranges.npy']:
  dest=HERE/'PRIVATE_INPUTS'/name
  if not dest.exists():os.link(BASE/'PRIVATE_INPUTS'/name,dest)
 print(json.dumps({'status':receipt['status'],'corrected_Q_D_fits':20,'UPSIDE_reuse':10,'OOF_rows_per_family':len(primary),'score_rows':2*len(primary),'new_fits':0}))

if __name__=='__main__':run()
