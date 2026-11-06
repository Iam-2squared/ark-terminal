from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,csv,sys
R=Path(__file__).resolve().parent;P=R/'PARENT_V4'
def now():return datetime.now(timezone(timedelta(hours=9))).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError('ALREADY_FIXED:'+n)
 p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def main():
 v=json.loads((R/'INHERITANCE_INPUT_VERIFICATION_V5.json').read_text());assert v['manifest_full_verification']=='PASS'
 b=json.loads((P/'BUDGET_FINAL_V4.json').read_text())
 save('BUDGET_START_V5.json',{'JST':now(),'finite_caps':{'research_fits':80,'fresh_fits':160,'total_fits':240,'new_provider_HTTP':900,'frozen_current_slot_steps':40000,'fixed_retry_proposals':109,'bounded_acquisition_passes':1,'Actions_runs':2,'fanout':1,'global_fresh_bootstrap_vectors':1000,'bootstrap_generations':1,'GitHub_GET':140,'GitHub_writes':50},'consumption_before_budget_fixation':{'new_fit':0,'new_provider_HTTP':0,'new_label':0,'new_bootstrap':0,'GitHub_GET':10,'GitHub_writes':1},'Lane_A':{'new_fits':0,'new_labels':0,'new_bootstrap':0,'state_kernel_reruns':0},'inherited_V4_budget':b,'no_reset':True,'old16FAIL':16,'old88workflow_incident':88,'historical_outside_exposure_unknown_nonzero_retained':True,'cap_expansion_after_results':False})
 save('WORK_LANES_V5.json',{'JST':now(),'document':'WORK_STATE_PREDICTIVENESS_V5_R2_CONTROL_CALIBRATION_CONFIRMATION_20261002_V1','parent_status':'BLOCKED_V4_INTEGRITY','primary_candidate':'R2','baseline':'R1','R3':'diagnostic-only','R4':'descriptive challenger, no fresh fits','Lane_A':'saved V4 only; no fits/labels/draws/kernel','Lane_B':'V4 exposed-only method sanity, no promotion','Lane_C':'single fixed109 retry; only approved unexposed Development extension','Lane_D':'one-shot only after final contract/scope hashes','Lane_E':'separate logic, saved artifacts only','semantic_changes':{'State9':0,'Path':0,'target':0,'family':0,'profile':0,'M0':0},'forbidden_exposure_delta':{'Holdout':0,'Protected':0,'Fresh_reserve':0,'OOS':0,'Prospective':0,'Entry':0,'EXIT':0,'profit':0,'Capital':0,'Portfolio':0,'orders':0,'external_AI':0},'delivery':'2–3 normal ZIPs for large complete delivery'})
 checkpoint('C0','V4_INHERITANCE_VERIFIED_FORENSIC_STARTED','Read-only V4 forensic; inventory and calibration specification preparation',sys.argv[1] if len(sys.argv)>1 else v['parent_head'])
def checkpoint(c,status,next_action,head):
 v=json.loads((R/'INHERITANCE_INPUT_VERIFICATION_V5.json').read_text())
 hashes={n:sha(R/n) if (R/n).exists() else None for n in ['PREDICTIVENESS_V5_CONTRACT.md','PREDICTIVENESS_V5_PRECOMMIT.json','FRESH_DATA_SCOPE_V5.json']}
 save('CHECKPOINTS/'+c+'.json',{'checkpoint':c,'JST':now(),'parent_HEAD':v['parent_head'],'current_HEAD_before_checkpoint_commit':head,'V4_hashes':v['frozen_hashes'],'V5_hashes':hashes,'current_status':status,'next_action':next_action,'post_commit_GET_required':True})
if __name__=='__main__':
 if len(sys.argv)>2:checkpoint(*sys.argv[1:5])
 else:main()
