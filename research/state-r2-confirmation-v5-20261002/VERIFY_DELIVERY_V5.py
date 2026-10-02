"""All required evidence, precommit and original parent bytes, no computation reruns."""
from pathlib import Path
import json,hashlib,csv,sys,zipfile
R=Path(__file__).resolve().parent
REQUIRED=['00_README.txt','V4_CONTROL_FORENSICS_REPORT.md','V4_R3_REAL_TRUE_NULL_DECOMPOSITION.csv','V4_R3_CALIBRATION_DECOMPOSITION.csv','V4_R3_FOLD_DATE_SECURITY_CONTROL.csv','V4_R3_FEATURE_TIMESTAMP_AUDIT.json','V4_CONTROL_FORENSICS_RECEIPT.json','V5_CALIBRATION_DESIGN.md','V5_CALIBRATION_RESEARCH_EXPOSED_ONLY.csv','V5_CALIBRATION_METHOD_FREEZE.json','FRESH_REACQUISITION_LEDGER_V5.csv','FRESH_DATA_SCOPE_V5.json','FRESH_DATA_MANIFEST_V5.json','PREDICTIVENESS_V5_CONTRACT.md','PREDICTIVENESS_V5_PRECOMMIT.json','FROZEN_IDENTITY_RECEIPT_V5.json','SPLIT_PLAN_V5.json','SPLIT_REALIZED_V5.json','R1_R2_FRESH_OOF_V5.csv','R1_R2_REVERSAL_METRICS_V5.csv','UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V5.csv','CALIBRATION_INNER_OOF_V5.csv','CALIBRATION_SELECTION_RECEIPT_V5.json','CALIBRATION_METRICS_V5.csv','CALIBRATION_BUCKETS_V5.csv','TRUE_NULL_R2_V5.csv','CONCENTRATION_V5.csv','BOOTSTRAP_GLOBAL_1000_RECEIPT_V5.json','INDEPENDENT_AUDIT_V5.json','BUDGET_START_V5.json','BUDGET_FINAL_V5.json','EXPOSURE_APPEND_ONLY_DELTA_V5.json','REPORT-ja.md','NEXT_STAGE_HANDOFF.md','DELIVERY_MANIFEST.json']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 missing=[n for n in REQUIRED if not (R/n).is_file()];assert not missing,missing
 pre=json.loads((R/'PREDICTIVENESS_V5_PRECOMMIT.json').read_text())
 for n,h in pre['hashes'].items():assert sha(R/n)==h,'PRECOMMIT_CHANGED:'+n
 for n,h in json.loads((R/'INHERITANCE_INPUT_VERIFICATION_V5.json').read_text())['frozen_hashes'].items():assert sha(R/'PARENT_V4'/n)==h,'PARENT_CHANGED:'+n
 final=json.loads((R/'FINAL_RECEIPT_V5.json').read_text());assert final['status']=='STATE_R2_CONFIRMATION_LIMITED_SAMPLE' and final['mismatch_N']==0 and final['direct_integrity']=='PASS' and final['R2_candidate_local_control']=='PASS' and not final['Hybrid_Entry_research_authorized']
 figures=json.loads((R/'FIGURE_MANIFEST_V5.json').read_text())['figures'];assert len(figures)==7 and all((R/'FIGURES'/n).stat().st_size>1000 for n in figures)
 report=(R/'REPORT-ja.md').read_text();assert sum(1 for line in report.splitlines() if line.startswith('| ') and line.split('|')[1].strip().isdigit())==25,'MANDATORY_ANSWERS'
 oo=list(csv.DictReader((R/'R1_R2_FRESH_OOF_V5.csv').open()));assert len(oo)==4336 and len({r['row_key'] for r in oo})==542
 canonical=list(map(json.loads,(R/'R1_R2_FRESH_OOF_V5.jsonl').open()));assert len(canonical)==len(oo)
 for x,y in zip(canonical,oo):assert all(y[k]==str(v) if not isinstance(v,list) else json.loads(y[k])==v for k,v in x.items()),'CSV_JSONL_IDENTITY'
 g=json.loads((R/'FRESH_GATE_MEASUREMENTS_V5.json').read_text());cal=g['R2_calibrated'];raw=g['R2_uncalibrated'];base=g['R1_calibrated'];imp=g['dangerous_improvement'];cs=list(csv.DictReader((R/'CONCENTRATION_V5.csv').open()))
 sample=cal['dates']>=8 and g['evaluable_folds']>=2 and cal['DOWN_REVERSAL_support']>=100 and cal['UP_CONTINUE_support']>=100
 hard=imp['improvement_pp']>0 and imp['improvement_CI_low_pp']>0
 reversal=any(cal[k]>base[k]+1e-12 for k in ['DOWN_REVERSAL_F1','UP_CONTINUE_F1','macro_F1']) and cal['DOWN_REVERSAL_Recall']>=base['DOWN_REVERSAL_Recall']-.02
 calgate=cal['date_equal_LL']<=1.05*raw['date_equal_LL']+1e-12 and cal['Brier']<=1.05*raw['Brier']+1e-12
 concentration=all(float(row['share'])<=.5+1e-12 and int(row['positive_gross_N'])>0 for row in cs if row['group']=='MAXIMUM' and row['gate_applies']=='True')
 assert [sample,hard,reversal,calgate,concentration]==[g['sample_PASS'],g['dangerous_hard_PASS'],g['major_reversal_PASS'],g['calibration_PASS'],g['concentration_PASS']],'FINAL_GATE_RECONCILIATION'
 for i in range(8):
  receipt=json.loads((R/'CHECKPOINTS'/f'C{i}_POST_GET.json').read_text())
  if i==0:
   # Initial C0 is the older minimal schema; it records actual GET SHA/tree,
   # not the later optional verified bool. Do not rewrite original receipt.
   assert receipt['post_commit_GET_HEAD']=='2afee683c889dd97418c7d9149bb21e28467aa03' and receipt['tree']=='c96d79d8451007d0f56d3d18e6aa39219c13ccf2','C0_ACTUAL_GET_IDENTITY'
  else:assert receipt['verified'],'CHECKPOINT_GET'
 exposure=json.loads((R/'EXPOSURE_APPEND_ONLY_DELTA_V5.json').read_text())
 for n in ['Holdout','Protected','Entry','EXIT','profit','Fresh_validation_reserve','OOS','Prospective','orders','broker_write','external_AI','main_merge','force_push','State9_changes','Path_changes','profile_changes','M0_changes','target_changes','family_mapping_changes']:assert exposure[n]==0,n
 files=json.loads((R/'DELIVERY_MANIFEST.json').read_text())['files'];assert all(sha(R/r['path'])==r['SHA256'] for r in files),'MANIFEST_HASH'
 result={'status':'PASS','mandatory_file_N':len(REQUIRED),'manifest_file_N':len(files),'mandatory_answer_N':25,'figures_N':len(figures),'parent_hash_PASS':True,'all_precommit_hash_PASS':True,'OOF_anchors':542,'OOF_rows':4336,'CSV_JSONL_field_identity':'PASS','final_gate_separate_reconciliation':'PASS','independent_mismatch_N':0,'C0_C7_post_GET_PASS':True,'forbidden_exposure_delta_and_semantic_changes_zero':True,'new_fit_label_bootstrap':0}
 if len(sys.argv)>1 and sys.argv[1]=='archives':
  package=json.loads((R/'DELIVERY_PACKAGE_RECEIPT_V5.json').read_text());seen=set()
  for row in package['files']:
   path=Path(row['local_path']);assert sha(path)==row['SHA256']
   with zipfile.ZipFile(path) as z:
    assert z.testzip() is None
    for r in files:
     if r['zip']==path.name:assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['SHA256'];seen.add(r['path'])
  assert seen=={r['path'] for r in files};result['ZIP_all_member_SHA_and_CRC']='PASS'
 name='ARCHIVE_VERIFICATION_RECEIPT_V5.json' if len(sys.argv)>1 and sys.argv[1]=='archives' else 'DELIVERY_VERIFICATION_V5.json'
 (R/name).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
