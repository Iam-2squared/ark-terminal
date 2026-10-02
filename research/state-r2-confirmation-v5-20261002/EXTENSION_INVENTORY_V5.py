"""Metadata-only additional Development date inventory, never raw/outcomes."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone,timedelta
import json,hashlib
R=Path(__file__).resolve().parent;P=R/'PARENT_V4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 allocation=json.loads((R/'INVENTORY_METADATA/SESSION_ALLOCATION_METADATA_V3.json').read_text());s=json.loads((P/'DATA_SCOPE_V4.json').read_text());exp=json.loads((P/'EXPOSURE_APPEND_ONLY_DELTA.json').read_text());source=json.loads((P/'NEW_DEVELOPMENT/SOURCE_RECEIPTS.json').read_text());port=json.loads((P/'DATASET_MANIFEST_PORTABLE_V4.json').read_text());retry=json.loads((R/'FRESH_REACQUISITION_SCOPE_FREEZE_V5.json').read_text())
 partitions=allocation['partitions'];dev=set(d for k,ds in partitions.items() if k.startswith('DEVELOPMENT_') for d in ds);protected=set(d for k,ds in partitions.items() if not k.startswith('DEVELOPMENT_') for d in ds)|set(s['blocked_days']);selected=set(x['date'] for x in s['authorized_current_links']);opened=set(x['date'] for x in port['pairs'])|set(exp['V1_V2_V3_exposed_dates_retained'])|set(x['scope']['date'] for x in source if x['endpoint'].endswith('/minute') and x.get('row_N',0)>0)
 calendar=sorted(dev|set(s['authorized_Development_days']));all_candidates=sorted(dev-selected-opened-protected);eligible=[];excluded=[]
 for d in sorted(dev):
  if d in protected:excluded.append({'date':d,'reason':'PROTECTED_PARTITION'});continue
  if d in selected:excluded.append({'date':d,'reason':'ALREADY_V1_V4_FIXED_CURRENT_DATE_NO_REPLACEMENT'});continue
  if d in opened:excluded.append({'date':d,'reason':'V1_V4_OPENED_OUTCOME_OR_RAW'});continue
  idx=calendar.index(d);previous=calendar[idx-1] if idx else None
  if previous is None or previous not in dev:excluded.append({'date':d,'reason':'NO_APPROVED_DEVELOPMENT_MINUTE_PREVIOUS_DEPENDENCY'});continue
  eligible.append({'date':d,'previous':previous,'partition':next(k for k,ds in partitions.items() if d in ds),'V1_V4_labels_or_current_raw_opened':False})
 assert len(eligible)==24 and len({r['date'] for r in eligible})==24
 candidates_N=len(eligible)*3;maxendpoints=(candidates_N+sum(x['fresh_pair_eligible_before_retry'] for x in retry['proposals']))*327
 assert maxendpoints<=40000
 record={'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':'METADATA_INVENTORY_FIXED_NOT_YET_ACQUIRED','source_repo':'Iam-2squared/ark-terminal','source_HEAD':'1b0b5c3c28f8f092f16c81b07c11f818e77879ef','source_path':'predict/long-only/phase57-long-only-session-allocation-v3.json','source_SHA256':sha(R/'INVENTORY_METADATA/SESSION_ALLOCATION_METADATA_V3.json'),'source_outcomes_read':0,'eligible_date_list':[r['date'] for r in eligible],'eligible_links':eligible,'exclusion_list':excluded,'protected_exclusion_dates':sorted(protected),'selector_metadata_rule':s['metadata_selection'],'selector_code_SHA256':s['metadata_selection_source_SHA256'],'max_securities_per_day':3,'chronological_order':'ascending metadata dates; within-date exact inherited SHA256 metadata order','fixed_candidate_N_upper':candidates_N,'missing_input_day_replacement':0,'new_security_refill_after_raw':0,'raw_request_authorized_only_if_109_pass_fresh_pool_structurally_insufficient':True,'bounded_retry109_pass_count':1,'disjoint_extension_pass_count_max':1,'Actions_total_cap_unchanged':2,'provider_HTTP_total_cap_unchanged':900,'kernel_step_cap_unchanged':40000,'maximum_possible_fresh_export_steps_under_both_scopes':maxendpoints,'fresh_pair_eligibility_unit':'new exact security/session not previously returned raw/outcome; additional24 dates wholly unopened in V1–V4','no_Protected_downgrade':True}
 p=R/'ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json';assert not p.exists();p.write_text(json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({'eligible_dates':record['eligible_date_list'],'N_upper':candidates_N,'maximum_steps':maxendpoints,'Protected_exposure':0}))
if __name__=='__main__':main()
