from pathlib import Path
from datetime import datetime, timezone, timedelta
import json, csv, hashlib, shutil, zipfile

R=Path(__file__).resolve().parent
V2=R.parent/'state_predictiveness_v2_nextstate_20261002_v1'
V1=R.parent/'state_predictiveness_20261002_v1'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
    p=R/n; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def now(): return datetime.now(timezone(timedelta(hours=9))).isoformat()

required=['00_README.txt','REPORT-ja.md','FINAL_RECEIPT.json','NEXT_STAGE_HANDOFF.md',
 'PREDICTIVENESS_V2_CONTRACT.md','PREDICTIVENESS_V2_PRECOMMIT.json','DATA_SCOPE_V2.json',
 'V1_EXPOSED_DEV.json','V2_NEW_DEV_EVAL.json','SPLIT_PLAN_V2.json','SPLIT_REALIZED_V2.json',
 'PER_STATE_PRECISION_RECALL_F1.csv','CONFUSION_MATRIX_9STATE.csv','MOTION_FAMILY_METRICS.csv',
 'TREND_CONTEXT_FAMILY_METRICS.csv','PATH_INCREMENTAL_ASSESSMENT_V2.csv','NEGATIVE_CONTROL_V2.csv',
 'SHIFT60_STRESS_V2.csv','PRICE_SECONDARY_V2.csv','INDEPENDENT_AUDIT_V2.json','BUDGET_FINAL_V2.json',
 'FIT_LEDGER_COMPLETENESS_FINDING.json','INPUT_LOCATION_INDEX_V2.csv','EXPOSURE_APPEND_ONLY_DELTA.json',
 'FROZEN_IDENTITY_RECEIPT.json','DATASET_MANIFEST.json','FEATURE_SCHEMA_V2.json',
 'GITHUB_REQUEST_USAGE_AT_DELIVERY.json','DEVELOPMENT_ACQUISITION_COMPLETENESS.csv']
files=[]
for n in required:
    p=V2/n; b=p.read_bytes()
    if n.endswith('.json'): json.loads(b)
    elif n.endswith('.csv'): list(csv.DictReader(b.decode().splitlines()))
    else: b.decode('utf-8')
    out=R/'INHERITED_V2'/n; out.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,out)
    files.append({'path':str(p),'member':'INHERITED_V2/'+n,'bytes':len(b),'SHA256':sha(p)})
assert json.loads((V2/'FINAL_RECEIPT.json').read_text())['status']=='STATE_NEXTSTATE_PREDICTIVENESS_MEASURED_NO_PROMOTABLE_STATE'
checks=[]
for c in json.loads((V1/'FROZEN_IDENTITY_RECEIPT.json').read_text())['checks'][:5]:
    p=Path(c['source_path']); h=sha(p); assert h==c['expected_SHA256'],'FROZEN_IDENTITY'
    out=R/'FROZEN_INPUTS'/p.name; out.parent.mkdir(exist_ok=True); shutil.copyfile(p,out)
    checks.append({**c,'actual_SHA256':h,'match':True,'member':str(out.relative_to(R))})
for n in ['STATE9_RC2_SEMANTIC_FREEZE_RECEIPT.json','STATE9_RC2_REPRESENTATION_SCOPE_NOTES.md',
 'STATE9_RC2_FREEZE_LIMITATIONS.md','RC1_ORIGINAL_16_FAILURES_PRESERVED.json','ORIGINAL_667_STATE_EXCLUSIONS.csv']:
    shutil.copyfile(V1/'FROZEN_INPUTS'/n,R/'FROZEN_INPUTS'/n)
z=R.parent/'State_Predictiveness_V2_NEXTSTATE_ALL_20261002.zip'
assert sha(z)=='85662d3890178e74aae36994bdcc51ff488d01f672fd27394bcf49c26b282d63'
with zipfile.ZipFile(z) as f: assert f.testzip() is None
save('V2_INHERITANCE_RECEIPT.json',{'JST':now(),'actual_latest_V2_HEAD':'57de9b1b13a9788f9d28a4d70b17fc2d0474f7e3',
 'ZIP_SHA256':sha(z),'ZIP_bytes':z.stat().st_size,'ZIP_CRC_PASS':True,'files':files,
 'V1_BLOCK_retained':True,'V2_result_not_overwritten':True,'old_RC1_FAIL_N':16,'old_workflow_incident_N':88})
save('FROZEN_IDENTITY_RECEIPT.json',{'JST':now(),'checks':checks,'State9_changes':0,'Path_changes':0,'profile_changes':0,'M0_changes':0,'status':'PASS'})
u=json.loads((V2/'NEW_DEVELOPMENT/ACQUISITION_UNIVERSE_PRECOMMIT.json').read_text())
pending=list(range(40,73)); assert len(pending)==33
old=json.loads((V2/'DATA_SCOPE_V2.json').read_text());exp=json.loads((V2/'EXPOSURE_APPEND_ONLY_DELTA.json').read_text())
exposed=sorted(set(old['V1_exposed_dates']+exp['V2_NEW_DEV_future_label_exposure_dates']))
newdates=sorted({u['proposals'][i-1]['date'] for i in pending})
save('ACQUISITION_COMPLETION_PRECOMMIT.json',{'JST':now(),'original_universe_SHA256':sha(V2/'NEW_DEVELOPMENT/ACQUISITION_UNIVERSE_PRECOMMIT.json'),
 'proposals':u['proposals'],'pending_ordinals':pending,'original_order_preserved':True,'replacement':0,
 'prior_39':'Existing exact U_UNAVAILABLE retained; no redundant refetch or changed U definition',
 'all_metadata_reused_without_reselection':True,'future_labels_generated':0})
save('DATA_SCOPE_V3.json',{'JST':now(),'parent_scope_SHA256':sha(V2/'DATA_SCOPE_V2.json'),'scope':'Exact V2 fixed 72 proposals + 25 existing original pairs; no new selection',
 'authorized_days':old['authorized_Development_days'],'blocked_days':old['blocked_days'],
 'pending_ordinals':pending,'new_evaluation_dates':newdates,'V1_V2_exposed_dates':exposed,
 'original_proposals':u['proposals'],'max_completed_pairs':93,'Holdout':0,'Protected':0,'Fresh_OOS':0,'Prospective':0,
 'provider_authority':old['provider_contract_basis'],'exclusion_identity_scope':'667 State exposure + old44, current and previous, inherited',
 'original_proposal_universe_SHA256':sha(V2/'NEW_DEVELOPMENT/ACQUISITION_UNIVERSE_PRECOMMIT.json'),'future_result_selection':0})
save('V1_V2_EXPOSED_DEV.json',{'dates':exposed,'V1':old['V1_exposed_dates'],'V2':exp['V2_NEW_DEV_future_label_exposure_dates'],
 'outside_exposure':'UNKNOWN_NONZERO_INHERITED','legacy_strategy_outcome_exposure_separate':True,'not_reset':True})
save('V3_NEW_DEV_EVAL.json',{'dates':newdates,'status':'Relative to V1/V2 future labels only; not Fresh/OOS','pending_proposals':33})
save('SPLIT_PLAN_V3.json',{'JST':now(),'fixed_three_blocks':[newdates[:4],newdates[4:8],newdates[8:]],
 'initial_train_dates_min':5,'train':'all available earlier dates; same security-session one date/fold',
 'purge':'all target/donor ends strictly earlier than test_start; each target within same session',
 'fallback':'Only if zero new acquired dates, first5 existing input dates train; remaining chronological dates split 3 balanced blocks, exposed diagnostic evaluation',
 'empty_folds_retained':True,'label_or_outcome_based_split_changes':0,'GOOD':{'folds':3,'OOF_dates':12},
 'LIMITED_BUT_EVALUABLE':{'folds':2,'OOF_dates':8},'permutation_seed':2026100302,'bootstrap_seed':2026100303})
budget=json.loads((V2/'BUDGET_FINAL_V2.json').read_text())
save('BUDGET_START_V3.json',{'JST':now(),'inherited_V2_budget_SHA256':sha(V2/'BUDGET_FINAL_V2.json'),'inherited_V2_budget':budget,'no_reset':True,
 'V3_caps':{'pending_proposals':33,'completed_pairs':93,'new_frozen_steps':18000,'provider_HTTP_requests':900,
 'isolated_Actions_runs':8,'Actions_fanout':1,'fit_operations':1200,'model_families':5,'outer_folds':3,'strengths':3,
 'tasks':4,'controls':3,'bootstrap_generated_vectors':1000,'independent_new_draws':0},
 'routine_read_depth_repair_counts':'history only; no procedural stop cap','forbidden_exposures':0})
runner=R/'runner';runner.mkdir(exist_ok=True)
for p in (V2/'runner').iterdir():
    if p.is_file() and (p.suffix=='.py' or p.name in ['profile.json','source_snapshot.json','FEATURE_SCHEMA_V2.json']):shutil.copyfile(p,runner/p.name)
shutil.copytree(V2/'runner/candidate',runner/'candidate',ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
cfg=json.loads((V2/'runner/config.json').read_text());cfg['maxrequests']=900;cfg['stage']='STATE_PREDICTIVENESS_V3_REVERSAL';cfg['newscope_sha']=sha(R/'DATA_SCOPE_V3.json');save('runner/config.json',cfg)
shutil.copyfile(R/'ACQUISITION_COMPLETION_PRECOMMIT.json',runner/'ACQUISITION_COMPLETION_PRECOMMIT.json')
save('CHECKPOINTS/C0.json',{'JST':now(),'parent_HEAD':'57de9b1b13a9788f9d28a4d70b17fc2d0474f7e3','current_HEAD':None,
 'Contract_SHA256':None,'data_scope_SHA256':sha(R/'DATA_SCOPE_V3.json'),'status':'V2_INHERITED_FROZEN_IDENTITIES_PASS',
 'next_action':'33 fixed Development acquisition + pre-label V3 Contract fixation'})
print(json.dumps({'identity':'PASS','required_files_N':len(files),'remaining':33,'new_dates':newdates,'inherited_exposed_dates_N':len(exposed)}))
