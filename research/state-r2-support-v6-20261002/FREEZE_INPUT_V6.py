"""Freeze acquired inputs and evaluation source before any V6 target label."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,csv,shutil
R=Path(__file__).resolve().parent;V=R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1';P=R/'PARENT_V4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 p=R/n;assert not p.exists(),'ALREADY_FIXED:'+n;p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def output(n,rows):
 cols=sorted(set().union(*(r.keys() for r in rows))) if rows else ['status']
 with (R/n).open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def main():
 assert not (R/'FRESH_LABELS').exists(),'LABEL_BEFORE_INPUT_FREEZE';pre=json.loads((R/'PREDICTIVENESS_V6_PRECOMMIT.json').read_text())
 for n,h in pre['hashes'].items():assert sha(R/n)==h,'PRECOMMIT_CHANGED:'+n
 for n,h in json.loads((R/'METHOD_SOURCE_PRELABEL_FREEZE_V6.json').read_text())['hashes'].items():assert sha(R/n)==h,'PRELABEL_METHOD_SOURCE_CHANGED:'+n
 scope=json.loads((R/'FRESH_SCOPE_V6.json').read_text());root=R/'ACQUISITION';receipt=json.loads((root/'RUNNER_FINAL_RECEIPT.json').read_text());assert receipt['error'] is None and receipt['labels_created']==receipt['model_fits']==receipt['bootstrap_draws']==0,'ACQUISITION_INTEGRITY';old=json.loads((P/'DATASET_MANIFEST_PORTABLE_V4.json').read_text())['pairs'];v5=json.loads((V/'FRESH_DATA_MANIFEST_V5.json').read_text())['pairs'];pairs=[]
 for p in json.loads((root/'FRESH_DATA_MANIFEST.json').read_text())['pairs']:
  q={**p,'exposure':'V6_UNEXPOSED_DEVELOPMENT_PAIR'}
  for field,folder,digest in [('feature_path','FEATURES','feature_SHA256'),('trace_path','STATE9_TRACES','state_trace_SHA256'),('path_endpoint_path','PATH_ENDPOINTS','path_endpoint_SHA256')]:
   file=root/folder/(p['pair_id']+'.jsonl');assert sha(file)==p[digest],'INPUT_HASH';q[field]=str(file.relative_to(R))
  q['label_path']='FRESH_LABELS/'+p['pair_id']+'.jsonl';pairs.append(q)
 full=sorted({p['date'] for p in old+v5+pairs});folds=[]
 for k,b in enumerate(scope['outer_test_blocks'],1):
  tr=[d for d in full if b and d<b[0]];folds.append({'fold':k,'test_dates':b,'train_dates':tr,'test_start':b[0]+'T00:00:00+09:00' if b else None,'initial_train_dates_sufficient':len(tr)>=5,'evaluable_after_labels':None})
 manifest={'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'pairs':pairs,'fresh_pair_N':len(pairs),'fresh_date_N':len({p['date'] for p in pairs}),'fresh_security_N':len({p['security_id'] for p in pairs}),'endpoint_N':sum(p['scheduled_endpoints_N'] for p in pairs),'no_fresh_labels_yet':True,'parent_training_manifest_SHA256':sha(P/'DATASET_MANIFEST_PORTABLE_V4.json'),'V5_training_manifest_SHA256':sha(V/'FRESH_DATA_MANIFEST_V5.json'),'scope_calendar_dates':scope['fixed_calendar_dates']}
 save('FRESH_DATA_MANIFEST_V6.json',manifest);save('SPLIT_REALIZED_V6.json',{'folds':folds,'mode':'V6_UNEXPOSED_DEVELOPMENT_PAIR','input_dates':full,'fresh_input_dates':sorted({p['date'] for p in pairs}),'warmup_dates':scope['outer_warmup_dates'],'availability_refolding_after_label':False})
 ledger=json.loads((root/'FRESH_REACQUISITION_LEDGER.json').read_text())
 for row in json.loads((root/'METADATA_UNAVAILABLE.json').read_text()):ledger.append({**row,'lane':'B_METADATA','pair_id':None,'retry_ordinal':None,'request_attempted':True,'fresh_trace_export':False,'metadata_candidate_not_selected_for_minute':True})
 for row in json.loads((root/'METADATA_DATE_LEDGER.json').read_text()):
  if row['status']!='METADATA_SELECTION_COMPLETE':ledger.append({**row,'lane':'B_DATE_METADATA','pair_id':None,'security_id':None,'retry_ordinal':None,'fresh_trace_export':False,'metadata_candidate_not_selected_for_minute':True})
 output('DEVELOPMENT_COMPLETION_LEDGER_V6.csv',ledger);output('UNAVAILABLE_INPUTS_V6.csv',[r for r in ledger if r['status']!='ACQUIRED'])
 files=['MODEL_V5.py','TARGET_KERNEL_V3_FROZEN.py','FRESH_OOF_V6.py','AUDIT_CORE_V6.py','FORENSICS_V5.py','AUDIT_RESEARCH_V5.py','METRICS_V6.py','AUDIT_METRICS_V6.py','METHOD_SOURCE_PRELABEL_FREEZE_V6.json','FRESH_DATA_MANIFEST_V6.json','SPLIT_REALIZED_V6.json']
 save('EVALUATION_CODE_FREEZE_V6.json',{'JST':manifest['JST'],'hashes':{n:sha(R/n) for n in files},'original_precommit_SHA256':sha(R/'PREDICTIVENESS_V6_PRECOMMIT.json'),'fresh_labels':0,'fits':0,'new_draws':0,'scope_or_method_or_gate_changes':0,'all_successful_inputs_fixed_before_labels':True})
 save('FRESH_INPUT_FIXATION_RECEIPT_V6.json',{'status':'PASS','input_manifest_SHA256':sha(R/'FRESH_DATA_MANIFEST_V6.json'),'evaluation_code_freeze_SHA256':sha(R/'EVALUATION_CODE_FREEZE_V6.json'),'precommit_SHA256':sha(R/'PREDICTIVENESS_V6_PRECOMMIT.json'),'pairs':len(pairs),'dates':manifest['fresh_date_N'],'securities':manifest['fresh_security_N'],'labels_generated':0,'raw_page_reopen_to_select_support':0})
 print(json.dumps({'pairs':len(pairs),'dates':manifest['fresh_date_N'],'securities':manifest['fresh_security_N'],'endpoints':manifest['endpoint_N'],'labels':0,'evaluation_source_frozen':True}))
if __name__=='__main__':main()
