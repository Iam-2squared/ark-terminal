"""Verify exact authorized calendar repair before any new head fit."""
from repair_utils import *
import ast,numpy as np,sklearn,collections
def run():
 correction=read(BASE/'TEACHER_CALENDAR_CORRECTION_RECEIPT.json');diag=read(BASE/'CALENDAR_INTEGRITY_DIAGNOSIS.json');features=read(BASE/'FEATURE_FREEZE.json');split=read(BASE/'SPLIT_PRECOMMIT.json');cfg=read(BASE/'MODEL_SCORE_POLICY_FREEZE.json');oldledger=read(BASE/'FIT_LEDGER.json');frec=read(BASE/'FEATURE_COMPUTATION_RECEIPT.json');identity=read(REPO/'research/state9-safe-upside-hybrid-entry-20261003/STATE9_FINAL_IDENTITY.json')
 assert sha(BASE/'common.py')==correction['corrected_common_sha256']
 source=(BASE/'common.py').read_text();parsed=ast.parse(source);fn=next(n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name=='source_starts');assert ast.unparse(fn)=='def source_starts(day):\n    return sorted(regular_starts(day) + [690, close_minute(day)])'
 from common import source_starts,regular_starts,close_minute
 sessions=sorted({r['session'] for r in rows(BASE/'PERSISTENT_GRID.jsonl.gz')});calendar_checks=[]
 for day in sessions:
  old=regular_starts(day)+[690,close_minute(day)];new=source_starts(day)
  assert set(old)==set(new) and len(old)==len(new) and new==sorted(old)
  calendar_checks.append({'session':day,'scheduled_bars':len(old),'set_identical':True,'chronological_only':True})
 original=np.load(BASE/'PRIVATE_PREFIT_LINEAGE/targets.npy',mmap_mode='r');corrected=np.load(BASE/'PRIVATE_INPUTS/targets.npy',mmap_mode='r');assert original.shape==corrected.shape
 if not np.array_equal(original[:,0],corrected[:,0],equal_nan=True):
  write(HERE/'REPAIR_SCOPE_BLOCK.json',{'status':'BLOCKED_REPAIR_SCOPE_EXPANDED_BEYOND_20_FITS','reason':'UPSIDE target/eligibility changed','new_fits':0});raise SystemExit('BLOCKED_REPAIR_SCOPE_EXPANDED_BEYOND_20_FITS')
 changes={}
 for h,key in [(1,'Q'),(2,'D')]:
  oldgood=np.isfinite(original[:,h]);newgood=np.isfinite(corrected[:,h]);old_changed=int(np.count_nonzero(original[oldgood,h]!=corrected[oldgood,h]));new=int(np.count_nonzero(~oldgood & newgood));lost=int(np.count_nonzero(oldgood & ~newgood));assert old_changed==lost==0 and new==13948
  changes[key]={'old_finite_changed':old_changed,'NULL_to_known':new,'known_to_NULL':lost,'corrected_known_N':int(newgood.sum())}
 for n,k in [('features_numeric.npy','numeric_sha256'),('features_categories.npy','categorical_sha256')]:assert sha(BASE/'PRIVATE_INPUTS'/n)==frec[k]
 assert sha(BASE/'STATE_FEATURE_METADATA.jsonl.gz')==frec['state_metadata_sha256']
 assert sklearn.__version__==read(BASE/'OOF_MODEL_RECEIPT.json')['sklearn_version']
 frozen_state=features['state_identity'];assert identity==frozen_state
 old=REPO/'research/state9-safe-upside-hybrid-entry-20261003'
 for entry in identity['source_files']:assert sha(old/'FROZEN_RC2_SOURCE'/entry['path'])==entry['sha256']
 for name,k in [('RC2_CONTRACT.txt','contract_sha256'),('profile.json','profile_sha256'),('M0.md','M0_sha256'),('source_snapshot.json','source_snapshot_sha256'),('STATE_PATH_CONTRACT_V1.md','path_contract_sha256')]:assert sha(old/'FROZEN_PUBLIC_INPUTS'/name)==identity[k]
 assert not any('legacy' in f.lower() or 'state-v3' in f.lower() for f in features['P1_numeric']+features['P1_categorical'])
 assert features['P1_numeric'][:len(features['P0_numeric'])]==features['P0_numeric']
 assert oldledger['fits_completed']==oldledger['fits_reserved']==len(oldledger['runs'])==30
 sessions_by_row=np.asarray([r['session'] for r in rows(BASE/'PERSISTENT_GRID.jsonl.gz')]);reuse=[]
 lineage=read(BASE/'OOF_SCORE_LINEAGE_RECEIPT.json')
 for entry in oldledger['runs']:
  f=entry['family'];fold=entry['fold'];head=entry['head'];model=BASE/'PRIVATE_MODELS'/f'{f}_F{fold}_{head}.pkl';prep=BASE/'PRIVATE_MODELS'/f'{f}_F{fold}_preprocessor.pkl';ref=BASE/'PRIVATE_MODELS'/f'{f}_F{fold}_{head}_train_prediction_reference.npy'
  assert sha(model)==entry['model_sha256'] and sha(prep)==entry['preprocessor_sha256'] and sha(ref)==entry['reference_sha256']
  tr=np.flatnonzero(np.isin(sessions_by_row,entry['train_sessions']));assert len(tr)==entry['train_rows']
  if head=='UPSIDE':
   assert np.isfinite(corrected[tr,0]).sum()==entry['head_train_rows']
   reuse.append({'family':f,'fold':fold,'head':head,'model_sha256':sha(model),'preprocessor_sha256':sha(prep),'training_prediction_reference_sha256':sha(ref),'U_train_eligibility_unchanged':True})
 for f in ['P0','P1']:
  n=f'OOF_{f}_UPSIDE.jsonl.gz';assert sha(BASE/n)==lineage['files'][n]['sha256']
 assert len(reuse)==10 and len(diag['affected_fits'])==20
 hashes={n:sha(BASE/n) for n in ['common.py','teacher.py','first_entry.py','causal_features.py','price_features.py','price_primitives.py','CLEAN_UPTREND_TEACHER_CONTRACT.json','FEATURE_FREEZE.json','SPLIT_PRECOMMIT.json','MODEL_SCORE_POLICY_FREEZE.json','FIT_LEDGER.json','PERSISTENT_GRID.jsonl.gz','WATCH_RECORDS.jsonl.gz','WATCH_IDENTITY_CONTRACT.json','STATE_FEATURE_METADATA.jsonl.gz','STATE_TIMELINE_WATCH_RECEIPTS.jsonl.gz','TEACHER_LABELS.jsonl.gz']}
 receipt={'document_id':DOCUMENT_ID,'saved_at_jst':now(),'actual_start_head':START_HEAD,'status':'CORRECTED_TEACHER_IDENTITY_VERIFIED','Primary_Freeze_Target':'P1_Q70','fixed_before_repair_outcomes':True,'calendar_change':'source_starts chronological sort only; same scheduled bar set','calendar_sessions_checked':len(sessions),'calendar_set_checks':calendar_checks,'Q_D_scope':changes,'U_target_eligibility_unchanged':True,'teacher_definition_changes':0,'feature_changes':0,'State9_current_history_changes':0,'Legacy_State_features':0,'watch_grid_changes':0,'split_changes':0,'fill_semantics_changes':0,'frozen_hashes':hashes,'corrected_targets_sha256':sha(BASE/'PRIVATE_INPUTS/targets.npy'),'original_targets_sha256':sha(BASE/'PRIVATE_PREFIT_LINEAGE/targets.npy'),'numeric_feature_sha256':frec['numeric_sha256'],'categorical_feature_sha256':frec['categorical_sha256'],'historical_completed_fits':30,'authorized_incremental_fits':20,'incremental_hard_cap':20,'cumulative_planned_fits':50,'UPSIDE_fits_to_refit':0,'UPSIDE_reuse_lineage':reuse,'sklearn_version_unchanged':sklearn.__version__,'new_fits_so_far':0,'all_searches':0,'EXIT':0,'Reentry':0,'Capital':0,'provider':0,'safety':SAFETY}
 write(HERE/'CORRECTED_TEACHER_FREEZE_RECEIPT.json',receipt)
 write(HERE/'REPAIR_SCOPE_PRECOMMIT.json',{'document_id':DOCUMENT_ID,'saved_at_jst':now(),'actual_start_head':START_HEAD,'Primary_Freeze_Target':'P1_Q70','candidate_reselection_allowed':False,'authorized_fit_keys':[[f,i,h] for f in ['P0','P1'] for i in range(1,6) for h in ['QUALITY','ADVERSE']],'authorized_incremental_fits':20,'incremental_hard_cap':20,'model_parameters':cfg['parameters'],'UPSIDE_refits':0,'reuse_original_preprocessors':True,'score_method':cfg['score'],'percentile_method':cfg['percentile'],'thresholds':POLICIES,'quantile_method':'linear','source_calendar_set_change':0,'new_research_scope':False,'safety':SAFETY})
 print(json.dumps({'status':receipt['status'],'Q':changes['Q'],'D':changes['D'],'U_unchanged':True,'reused_UPSIDE_models':10,'features_and_State_identity_unchanged':True,'new_fits':0},ensure_ascii=False))
if __name__=='__main__':run()
