"""Emit public code and explicitly allowed aggregate receipts only."""
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parent;PREFIX='research/state-r2-confirmation-v5-20261002/'
ALLOWED={'00_README.txt','INHERITANCE_INPUT_VERIFICATION_V5.json','WORK_LANES_V5.json','BUDGET_START_V5.json','BUDGET_FINAL_V5.json','V4_CONTROL_FORENSICS_REPORT.md','V4_CONTROL_FORENSICS_RECEIPT.json','V4_R3_FEATURE_TIMESTAMP_AUDIT.json','V5_CALIBRATION_DESIGN.md','V5_CALIBRATION_METHOD_FREEZE.json','FRESH_DATA_SCOPE_V5.json','PREDICTIVENESS_V5_CONTRACT.md','PREDICTIVENESS_V5_PRECOMMIT.json','FROZEN_IDENTITY_RECEIPT_V5.json','REPORT-ja.md','NEXT_STAGE_HANDOFF.md','FINAL_RECEIPT_V5.json','INDEPENDENT_AUDIT_V5.json','FRESH_RECOVERY_SUMMARY_V5.json','ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json','EXTENSION_ACTIVATION_RECEIPT_V5.json'}
ALLOWED.update({'FRESH_OOF_FIXATION_RECEIPT_V5.json','FRESH_GATE_MEASUREMENTS_V5.json','R1_R2_REVERSAL_METRICS_V5.csv','UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V5.csv','CALIBRATION_METRICS_V5.csv','CALIBRATION_BUCKETS_V5.csv','TRUE_NULL_R2_V5.csv','CONCENTRATION_V5.csv','V5_CALIBRATION_RESEARCH_EXPOSED_ONLY.csv','BOOTSTRAP_GLOBAL_1000_RECEIPT_V5.json','SOURCE_CODE_LOCATION_INDEX_V5.json','DELIVERY_MANIFEST.json','GITHUB_REQUEST_USAGE_V5.json'})
if __name__=='__main__':
 files=[p for p in R.iterdir() if p.is_file() and (p.suffix=='.py' or p.name in ALLOWED)]
 files+=sorted((R/'CHECKPOINTS').glob('C*.json'))
 elements=[{'path':PREFIX+str(p.relative_to(R)),'type':'blob','mode':'100644','content':p.read_text()} for p in sorted(files)]
 if len(sys.argv)==3:elements=elements[int(sys.argv[1])::int(sys.argv[2])]
 print(json.dumps({'tree_elements':elements},ensure_ascii=False))
