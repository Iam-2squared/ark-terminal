"""Freeze admitted input, exact calendar split and all evaluation code before labels."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone,timedelta
import json,csv,hashlib
R=Path(__file__).resolve().parent;P=R/'PARENT_V4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 p=R/n;assert not p.exists(),'ALREADY_FIXED:'+n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def csvout(n,rs):
 columns=sorted(set().union(*(r.keys() for r in rs))) if rs else ['status']
 with (R/n).open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rs)
def main():
 assert not (R/'FRESH_LABELS').exists() and not (R/'FRESH_FITTED').exists(),'FRESH_LABEL_ALREADY_OPENED'
 current=[];all_ledger=[];input_receipts=[]
 for mode in ['RECOVERY','EXTENSION']:
  root=R/mode
  if not root.exists():continue
  receipt=json.loads((root/'RUNNER_FINAL_RECEIPT.json').read_text());assert receipt['error'] is None and receipt['labels_created']==0,'ACQUISITION_INTEGRITY'
  input_receipts.append({'mode':mode,'SHA256':sha(root/'RUNNER_FINAL_RECEIPT.json'),'receipt':receipt})
  all_ledger.extend({**r,'lane':mode} for r in json.loads((root/'FRESH_REACQUISITION_LEDGER.json').read_text()))
  for p in json.loads((root/'FRESH_DATA_MANIFEST.json').read_text())['pairs']:
   assert p['fresh_pair_eligible_before_retry'],'EXPOSED_FRESH_ADMISSION'
   q={**p,'exposure':'V5_UNEXPOSED_DEVELOPMENT_PAIR','acquisition_lane':mode}
   for field,folder,digest in [('feature_path','FEATURES','feature_SHA256'),('trace_path','STATE9_TRACES','state_trace_SHA256'),('path_endpoint_path','PATH_ENDPOINTS','path_endpoint_SHA256')]:
    file=root/folder/(p['pair_id']+'.jsonl');assert sha(file)==p[digest],'FRESH_INPUT_HASH';q[field]=str(file.relative_to(R))
   q['label_path']='FRESH_LABELS/'+p['pair_id']+'.jsonl';current.append(q)
 scopes=sorted({p['date'] for p in current})
 if (R/'EXTENSION').exists():scopes=sorted(set(scopes)|set(json.loads((R/'ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json').read_text())['eligible_date_list']))
 old=json.loads((P/'DATASET_MANIFEST_PORTABLE_V4.json').read_text())['pairs'];past=sorted({p['date'] for p in old});freshdates=sorted({p['date'] for p in current});full=sorted(set(past)|set(freshdates))
 remaining=scopes[5:];q,n=divmod(len(remaining),3);blocks=[];at=0
 for k in range(3):size=q+(k<n);blocks.append(remaining[at:at+size]);at+=size
 folds=[]
 for k,b in enumerate(blocks,1):
  tr=[d for d in full if b and d<b[0]];folds.append({'fold':k,'test_dates':b,'train_dates':tr,'test_start':b[0]+'T00:00:00+09:00' if b else None,'initial_train_dates_sufficient':len(tr)>=5,'evaluable_after_labels':None})
 manifest={'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'pairs':current,'fresh_pair_N':len(current),'fresh_date_N':len(freshdates),'fresh_security_N':len({p['security_id'] for p in current}),'endpoint_N':sum(p['scheduled_endpoints_N'] for p in current),'no_fresh_labels_yet':True,'V4_training_only_manifest':'PARENT_V4/DATASET_MANIFEST_PORTABLE_V4.json','V4_training_manifest_SHA256':sha(P/'DATASET_MANIFEST_PORTABLE_V4.json'),'scope_calendar_dates':scopes,'acquisition_receipts':input_receipts}
 save('FRESH_DATA_MANIFEST_V5.json',manifest);csvout('FRESH_REACQUISITION_LEDGER_V5.csv',all_ledger)
 scope={'JST':manifest['JST'],'unit':'preselected exact security/session pair, not reused exposed outcomes','pairs':[{'pair_id':p['pair_id'],'date':p['date'],'previous':p['previous'],'security_id':p['security_id'],'session_id':p['session_id'],'acquisition_lane':p['acquisition_lane'],'feature_SHA256':p['feature_SHA256']} for p in current],'fixed_calendar_dates':scopes,'acquired_fresh_dates':freshdates,'acquired_fresh_securities':sorted({p['security_id'] for p in current}),'old_exposed_dates_training_only':past,'fixed109_scope_SHA256':sha(R/'FRESH_REACQUISITION_SCOPE_FREEZE_V5.json'),'additional24_scope_SHA256':sha(R/'ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json'),'metadata_selected_scope_SHA256':sha(R/'EXTENSION/EXTENSION_SELECTED_METADATA_SCOPE_V5.json') if (R/'EXTENSION').exists() else None,'available_input_scope_is_fixed_before_labels':True,'new_fresh_label_N':0,'fresh_reserved_validation_used':False,'protected_requests':0,'replacement_after_results':0,'metadata_max_securities_per_extension_day':3,'ordered109_retries':1,'disjoint_extension_passes':int((R/'EXTENSION').exists()),'calendar_empty_dates_retained':True,'forbidden_exposure_delta':{'Holdout':0,'Protected':0,'Fresh_reserve':0,'OOS':0,'Prospective':0,'Entry':0,'EXIT':0,'profit':0}}
 save('FRESH_DATA_SCOPE_V5.json',scope)
 plan={'chronological':True,'warmup_dates':scopes[:5],'fixed_three_blocks':blocks,'prior_exposed_features_labels_training_only':True,'minimum_initial_train_input_dates':5,'purge':'whole-label REAL/donor label_end strictly before test_start','row_randomization':False,'post_label_refolding':False,'all_scope_calendar_dates_retained':True,'availability_fixed_before_label_generation':True};save('SPLIT_PLAN_V5.json',plan)
 save('SPLIT_REALIZED_V5.json',{'folds':folds,'mode':'V5_UNEXPOSED_DEVELOPMENT_PAIR','input_dates':full,'fresh_input_dates':freshdates,'warmup_dates':plan['warmup_dates'],'empty_test_input_dates':[d for b in blocks for d in b if d not in freshdates],'availability_refolding_after_label':False})
 parent=json.loads((P/'FROZEN_IDENTITY_RECEIPT.json').read_text());checks=[]
 for item in parent['checks']:
  checks.append({**item,'V5_actual_SHA256':sha(P/item['member'])});assert checks[-1]['V5_actual_SHA256']==item['SHA256'],'FROZEN_HASH_MISMATCH'
 assert sha(R/'TARGET_KERNEL_V3_FROZEN.py')=='bc30b2ffb2a8f2a24c5982e365c18aadbb46809a039fb422ab826b00eaf64be7','TARGET_IDENTITY'
 save('FROZEN_IDENTITY_RECEIPT_V5.json',{'status':'PASS','checks':checks,'semantic_changes':{'State9':0,'Path':0,'profile':0,'M0':0,'target':0,'family_mapping':0},'parent_status':'BLOCKED_V4_INTEGRITY','parent_head':'1b0b5c3c28f8f092f16c81b07c11f818e77879ef','V4_contract_SHA256':sha(P/'PREDICTIVENESS_V4_CONTRACT.md'),'V4_precommit_SHA256':sha(P/'PREDICTIVENESS_V4_PRECOMMIT.json'),'V4_scope_SHA256':sha(P/'DATA_SCOPE_V4.json'),'V4_OOF_SHA256':sha(P/'OOF_ALL.jsonl'),'target_source_SHA256':sha(R/'TARGET_KERNEL_V3_FROZEN.py'),'State_feature_schema_SHA256':sha(P/'FEATURE_SCHEMA_V4.json')})
 code=['MODEL_V5.py','TARGET_KERNEL_V3_FROZEN.py','FRESH_OOF_V5.py','METRICS_FRESH_V5.py','AUDIT_FRESH_V5.py','FORENSICS_V5.py','AUDIT_RESEARCH_V5.py']
 files=code+['PREDICTIVENESS_V5_CONTRACT.md','FRESH_DATA_SCOPE_V5.json','FRESH_DATA_MANIFEST_V5.json','SPLIT_PLAN_V5.json','SPLIT_REALIZED_V5.json','FROZEN_IDENTITY_RECEIPT_V5.json','BUDGET_START_V5.json','V5_CALIBRATION_DESIGN.md','V5_CALIBRATION_METHOD_FREEZE.json']
 save('PREDICTIVENESS_V5_PRECOMMIT.json',{'JST':manifest['JST'],'document':'WORK_STATE_PREDICTIVENESS_V5_R2_CONTROL_CALIBRATION_CONFIRMATION_20261002_V1','primary_candidate':'R2','baseline':'R1','R3':'diagnostic_only_zero_fresh_fits','R4':'nonpromotable_zero_fresh_fits','hashes':{n:sha(R/n) for n in files},'feature_schema_parent_SHA256':sha(P/'FEATURE_SCHEMA_V4.json'),'null_seed_prefix':2026100402,'bootstrap_seed':2026100503,'bootstrap_generated':0,'fresh_labels_seen':0,'fresh_model_fits':0,'post_result_changes_allowed':False,'calibration_method':'ROLLING_INNER_OOF_TEMPERATURE_V1','temperature_grid':[.5,.75,1,1.25,1.5,2],'alpha_grid':[.01,.1,1],'support_gate':{'OOF_dates':8,'evaluable_folds':2,'DOWN_REVERSAL':100,'UP_CONTINUE':100},'TRUE_NULL_gain_equivalence_fraction':.9,'DOWN_recall_max_decline':.02,'calibration_ratio_caps':{'date_equal_LL':1.05,'row_Brier':1.05},'concentration_max_date_security_share':.5,'finite_budget_start_SHA256':sha(R/'BUDGET_START_V5.json'),'one_shot':True})
 print(json.dumps({'fresh_pairs':len(current),'dates':len(freshdates),'securities':manifest['fresh_security_N'],'calendar_dates':len(scopes),'blocks':blocks,'new_labels':0,'precommit_SHA256':sha(R/'PREDICTIVENESS_V5_PRECOMMIT.json')}))
if __name__=='__main__':main()
