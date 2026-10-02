"""Explicit public allowlist; never upload row-level prices, features or OOF."""
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parent;dest='research/state-confirmation-v4-20261002/'
stage=sys.argv[1];part=int(sys.argv[2]) if len(sys.argv)>2 else 0
original_stage=stage
if stage in ['C3','C4','C5','C6']:stage='evaluation'
names={'precommit':['INITIALIZE_V4.py','PREDICTIVENESS_V4_CONTRACT.md','PREDICTIVENESS_V4_PRECOMMIT.json','DATA_SCOPE_V4.json','SPLIT_PLAN_V4.json','BUDGET_START_V4.json','FROZEN_IDENTITY_RECEIPT.json','INHERITANCE_V4.json','CHECKPOINTS/C0.json','CHECKPOINTS/C2.json','DELIVERY_PREFERENCE.json'], 'acquisition':['PREPARE_RUNNER_V4.py','PUBLIC_TREE_V4.py','WORKFLOW_PREFLIGHT_V4.json','runner/export_expansion_v4.py','runner/metadata_universe.py'], 'evaluation':['PUBLIC_TREE_V4.py','BUILD_V4.py','FIT_V4.py','METRICS_V4.py','ASSESS_V4.py','INDEPENDENT_AUDIT_V4.py','AUDIT_SUPPLEMENT_V4.py','RENDER_V4.py','ADAPT_INHERITED_V4.py','CHECKPOINT_V4.py','EXECUTION_PREFLIGHT_V4.py','EXECUTION_PREFLIGHT_V4.json','INHERITED_TARGET_ANATOMY_V3.py','CHECKPOINTS/C0.json','CHECKPOINTS/C2.json','CHECKPOINTS/C0_INITIAL_FIXATION.json','CHECKPOINTS/C2_INITIAL_FIXATION.json']}[stage]
if stage=='evaluation':names+=['AUDIT_TRACE_PREFIX_V4.py','FINALIZE_V4.py','PACK_DELIVERY_V4.py','VALIDATE_CHARTS_V4.py','RECONCILE_PROVIDER_V4.py','IMPORT_ARTIFACT_V4.py','ROUTINE_REPAIR_RECEIPT.json']
if original_stage=='C3':names+=['CHECKPOINTS/C1.json','CHECKPOINTS/C3.json','C3_DATASET_FIXATION_RECEIPT.json','SPLIT_REALIZED_V4.json','DEVELOPMENT_COMPLETION_SUMMARY_V4.json','DEVELOPMENT_COMPLETION_LEDGER_V4.csv','UNAVAILABLE_INPUTS_V4.csv','ACQUISITION_IMPORT_RECEIPT_V4.json','RUNNER_ACCOUNTING_V4.json']
if original_stage=='C4':names+=['CHECKPOINTS/C4.json','C4_LABEL_FIXATION_RECEIPT.json','C5_OOF_FIXATION_RECEIPT.json','BOOTSTRAP_GLOBAL_1000_RECEIPT.json','CURRENT_POSITION_V4.json']
if original_stage=='C5':names+=['CHECKPOINTS/C5.json','INDEPENDENT_AUDIT_V4.json','GATE_ASSESSMENT_V4.json','PROMOTION_GATE_V4.csv','MAJOR_METRIC_GAIN_GATE_V4.csv','REVERSAL_METRICS_V4.csv','REVERSAL_METRICS_BY_FOLD_V4.csv','NEGATIVE_CONTROL_V4.csv','SHIFT60_STRESS_V4.csv','PATH_ANATOMY_SUPPORT_SUMMARY_V4.csv','CURRENT_POSITION_V4.json']
if original_stage=='C6':names+=['CHECKPOINTS/C6.json','00_README.txt','REPORT-ja.md','NEXT_STAGE_HANDOFF.md','FINAL_RECEIPT.json','BUDGET_FINAL_V4.json','EXPOSURE_APPEND_ONLY_DELTA.json','GITHUB_REQUEST_USAGE_AT_DELIVERY.json','CHART_MANIFEST.json','CHART_VALIDATION_V4.json','V3_V4_DANGEROUS_COMPARISON.csv','STATE_SUPPORT_V2_V3_V4.csv','NINE_STATE_ACCURACY_V2_V3_V4.csv','CURRENT_POSITION_V4.json']
elements=[{'path':dest+n,'mode':'100644','type':'blob','content':(R/n).read_text()} for n in names]
if stage=='acquisition':
 elements +=[{'path':dest+'payload.b64','mode':'100644','type':'blob','content':(R/'ACQUISITION_PAYLOAD_V4.b64').read_text()},{'path':'.github/workflows/state-confirmation-v4-20261002.yml','mode':'100644','type':'blob','content':(R/'state-confirmation-v4-20261002.yml').read_text()}]
s=json.dumps(elements,ensure_ascii=False)
if part<0:print(json.dumps({'chars':len(s),'parts':(len(s)+23999)//24000}));sys.exit()
print(json.dumps(s[part*24000:(part+1)*24000],ensure_ascii=False))
