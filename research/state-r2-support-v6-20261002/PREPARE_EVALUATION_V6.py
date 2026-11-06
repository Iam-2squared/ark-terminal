"""IO-only reuse of frozen V5 candidate and independent coefficient checker."""
from pathlib import Path
import json,hashlib,ast
R=Path(__file__).resolve().parent;V=R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1'
def main():
 source=(V/'FRESH_OOF_V5.py').read_text().replace('PREDICTIVENESS_V5_PRECOMMIT.json','PREDICTIVENESS_V6_PRECOMMIT.json').replace('V5_PRECOMMIT_BREACH','V6_PRECOMMIT_BREACH').replace('FRESH_DATA_MANIFEST_V5.json','FRESH_DATA_MANIFEST_V6.json').replace('R1_R2_FRESH_OOF_V5','R1_R2_OOF_V6').replace('LABEL_FIXATION_RECEIPT_V5','LABEL_FIXATION_RECEIPT_V6').replace('V5_UNEXPOSED_DEVELOPMENT_PAIR','V6_UNEXPOSED_DEVELOPMENT_PAIR').replace('PERMUTATION_MAPPING_V5','PERMUTATION_MAPPING_V6').replace('SPLIT_REALIZED_V5','SPLIT_REALIZED_V6').replace('CALIBRATION_INNER_OOF_V5','CALIBRATION_INNER_OOF_V6').replace('CALIBRATION_SELECTION_RECEIPT_V5','CALIBRATION_SELECTION_RECEIPT_V6').replace('FRESH_OOF_FIXATION_RECEIPT_V5','FRESH_OOF_FIXATION_RECEIPT_V6').replace("CHECKPOINTS/C4_POST_GET.json","CHECKPOINTS/C3_POST_GET.json")
 before=" # Old exposed labels are reused only for chronological training.\n for p in old['pairs']:"
 after=" # Immutable V4 and V5 exposed outcomes are chronological training-only.\n old={**old,'pairs':old['pairs']+[{**p,'_V5':True} for p in json.loads((R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1/FRESH_DATA_MANIFEST_V5.json').read_text())['pairs']]}\n for p in old['pairs']:"
 assert before in source;source=source.replace(before,after)
 source=source.replace("lab={r['row_key']:r['REAL']['CONTEXT_REVERSAL'] for r in map(json.loads,(P/p['label_path']).open())}","root=(R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1') if p.get('_V5') else P\n  lab={r['row_key']:r['REAL']['CONTEXT_REVERSAL'] for r in map(json.loads,(root/p['label_path']).open())}")
 source=source.replace("(P/p['feature_path']).open()","(root/p['feature_path']).open()")
 source=source.replace("return pre\ndef main():","for n,h in json.loads((R/'EVALUATION_CODE_FREEZE_V6.json').read_text())['hashes'].items():assert m.sha(R/n)==h,'V6_EVALUATION_CODE_BREACH:'+n\n return pre\ndef main():")
 (R/'FRESH_OOF_V6.py').write_text(source)
 # Core independent audit ends before slow metric replay; V6 metric checker is separate.
 audit=(V/'AUDIT_FRESH_V5.py').read_text();audit=audit[:audit.index(" bootstrap=read('BOOTSTRAP_GLOBAL_DATE_DRAWS_V5.json')")]
 for old,new in [('PREDICTIVENESS_V5_PRECOMMIT','PREDICTIVENESS_V6_PRECOMMIT'),('FRESH_DATA_SCOPE_V5','FRESH_SCOPE_V6'),('FRESH_DATA_MANIFEST_V5','FRESH_DATA_MANIFEST_V6'),('SPLIT_REALIZED_V5','SPLIT_REALIZED_V6'),('PERMUTATION_MAPPING_V5','PERMUTATION_MAPPING_V6'),('R1_R2_FRESH_OOF_V5','R1_R2_OOF_V6')]:audit=audit.replace(old,new)
 before=" for n,h in read('INHERITANCE_INPUT_VERIFICATION_V5.json')['frozen_hashes'].items():a.check(a.sha(P/n)==h,'original_V4_hash_unchanged',n)"
 after=" for n,h in read('EVALUATION_CODE_FREEZE_V6.json')['hashes'].items():a.check(a.sha(R/n)==h,'evaluation_code_hash',n)\n V=R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1'\n for e in read('V5_INHERITANCE_RECEIPT_V6.json')['hash_checks']:a.check(a.sha(V/e['path'])==e['SHA256'],'original_V5_hash_unchanged',e['path'])"
 assert before in audit;audit=audit.replace(before,after)
 before=" for p in json.loads((P/'DATASET_MANIFEST_PORTABLE_V4.json').read_text())['pairs']:\n  ls={l['row_key']:l['REAL']['CONTEXT_REVERSAL'] for l in map(json.loads,(P/p['label_path']).open())}"
 after=" oldpairs=json.loads((P/'DATASET_MANIFEST_PORTABLE_V4.json').read_text())['pairs']+[{**p,'_V5':True} for p in json.loads((V/'FRESH_DATA_MANIFEST_V5.json').read_text())['pairs']]\n for p in oldpairs:\n  root=V if p.get('_V5') else P\n  ls={l['row_key']:l['REAL']['CONTEXT_REVERSAL'] for l in map(json.loads,(root/p['label_path']).open())}"
 assert before in audit;audit=audit.replace(before,after).replace("(P/p['feature_path']).open()","(root/p['feature_path']).open()")
 audit+=''' ledger=list(map(json.loads,(R/'MODEL_EXECUTION_LEDGER_V5.jsonl').open()));caps=read('BUDGET_START_V6.json')['finite_caps'];a.check(sorted(charged)==list(range(1,len(charged)+1)) and len(charged)==len(ledger) and all(l['charged_before_fit'] and l['lane']=='fresh' for l in ledger),'append_before_fit_full_accounting');a.check(len(ledger)<=caps['total_fits'] and len(ledger)<=caps['fresh_fits'],'finite_model_budget')
 runner=read('ACQUISITION/RUNNER_FINAL_RECEIPT.json');a.check(runner['protected_requests']==runner['labels_created']==runner['model_fits']==runner['bootstrap_draws']==runner['secret_values_exported']==0,'provider_boundary_and_no_labels');a.check(runner['actual_provider_HTTP']<=caps['new_provider_HTTP'] and runner['new_steps']<=caps['frozen_current_slot_steps'],'finite_provider_kernel_budget')
 receipt={'status':'PASS' if not a.ERRORS else 'FAIL','mismatch_N':len(a.ERRORS),'errors':a.ERRORS[:100],'assertion_counts':dict(a.CHECKS),'new_fits':0,'new_bootstrap_draws':0,'candidate_helper_imports':0,'new_labels_or_outcomes':0,'fresh_available_anchor_N':len(fresh),'fresh_model_fit_N':len(charged),'provider_HTTP':runner['actual_provider_HTTP'],'kernel_steps':runner['new_steps'],'direct_future_leakage_found':False if not a.ERRORS else None,'V5_result_changes':0,'independent_logic':'V5 independent target/prefix/encoder/coefficient/inner/selection/OOF logic with V6 IO-only adaptation; no candidate imports, solve0'}
 (R/'INDEPENDENT_CORE_AUDIT_V6.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['errors','assertion_counts']}))
 if a.ERRORS:raise RuntimeError('UNRECONCILED_CORE_MISMATCH')
if __name__=='__main__':main()
'''
 (R/'AUDIT_CORE_V6.py').write_text(audit)
 for n in ['FRESH_OOF_V6.py','AUDIT_CORE_V6.py']:ast.parse((R/n).read_text())
 print(json.dumps({'V5_hard_model_source_changes':0,'target_source_changes':0,'candidate_wrapper_IO_only':True,'independent_source_no_candidate_imports':True,'fits':0,'labels':0}))
if __name__=='__main__':main()
