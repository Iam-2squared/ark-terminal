"""Checkpoint metadata and bounded public tree emitter; no private raw or fits."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,sys
R=Path(__file__).resolve().parent;PREFIX='research/state-r2-support-v6-20261002/'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def main():
 mode=sys.argv[1]
 if mode=='checkpoint':
  name,head,status,action=sys.argv[2:6];p=R/'CHECKPOINTS'/f'{name}.json';p.parent.mkdir(exist_ok=True)
  if p.exists():
   old=json.loads(p.read_text());assert old['current_HEAD_before_commit']==head and old['status']==status and not (R/'CHECKPOINTS'/f'{name}_POST_GET.json').exists(),'CHECKPOINT_IMMUTABLE';print(json.dumps(old));return
  inherit=json.loads((R/'V5_INHERITANCE_RECEIPT_V6.json').read_text());obj={'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'checkpoint':name,'parent_HEAD':inherit['V5_final_delivery_HEAD'],'current_HEAD_before_commit':head,'V5_hashes':{r['identity']:r['SHA256'] for r in inherit['hash_checks']},'V6_contract_SHA256':sha(R/'PREDICTIVENESS_V6_CONTRACT.md'),'V6_precommit_SHA256':sha(R/'PREDICTIVENESS_V6_PRECOMMIT.json'),'scope_SHA256':sha(R/'FRESH_SCOPE_V6.json'),'status':status,'next_action':action};p.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n');print(json.dumps(obj));return
 allowed={'V5_INHERITANCE_RECEIPT_V6.json','FRESH_SCOPE_V6.json','FRESH_SCOPE_PRECOMMIT_V6.json','INVENTORY_PROVENANCE_V6.json','BUDGET_START_V6.json','BUDGET_START_V5.json','PREDICTIVENESS_V6_CONTRACT.md','PREDICTIVENESS_V6_PRECOMMIT.json','EVALUATION_CODE_FREEZE_V6.json','FROZEN_IDENTITY_RECEIPT_V6.json','SPLIT_PLAN_V6.json','SPLIT_REALIZED_V6.json','ACQUISITION_EXECUTION_FREEZE_V6.json','REPORT-ja.md','NEXT_STAGE_HANDOFF.md','HYBRID_ENTRY_INTELLIGENCE_HANDOFF.md','00_README.txt','FINAL_RECEIPT_V6.json','INDEPENDENT_AUDIT_V6.json','INDEPENDENT_CORE_AUDIT_V6.json','CALIBRATION_STATUS_V6.json','V6_GATE_MEASUREMENTS.json','BOOTSTRAP_GLOBAL_1000_RECEIPT_V6.json','BUDGET_FINAL_V6.json','EXPOSURE_APPEND_ONLY_DELTA_V6.json','DELIVERY_VERIFICATION_V6.json','SOURCE_CODE_LOCATION_INDEX_V6.json','FRESH_INPUT_FIXATION_RECEIPT_V6.json','FRESH_OOF_FIXATION_RECEIPT_V6.json','R1_R2_HARD_METRICS_V6.csv','UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V6.csv','V5_V6_POOLED_METRICS.csv','V6_ONLY_METRICS.csv','TRUE_NULL_R2_V6.csv','STABILITY_AND_CONCENTRATION_V6.csv','CALIBRATION_METRICS_V6.csv','CALIBRATION_BUCKETS_V6.csv'}
 files=sorted(p for p in R.iterdir() if p.is_file() and (p.suffix=='.py' or p.name in allowed));files+=sorted((R/'CHECKPOINTS').glob('*.json'));elements=[{'path':PREFIX+str(p.relative_to(R)),'type':'blob','mode':'100644','content':p.read_bytes().decode('utf-8')} for p in files]
 data=json.dumps({'tree_elements':elements},ensure_ascii=False)
 if mode=='tree_length':print(len(data));return
 if mode=='tree_chunk':
  start=int(sys.argv[2])*12000;sys.stdout.write(data[start:start+12000]);return
 print(data)
if __name__=='__main__':main()
