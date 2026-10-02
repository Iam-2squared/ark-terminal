"""Outcome-free scope and exposure provenance inventory; no provider calls."""
from pathlib import Path
from collections import Counter,defaultdict
import json,csv,hashlib,zipfile
R=Path(__file__).resolve().parent;P=R/'PARENT_V4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def main():
 scope=json.loads((P/'DATA_SCOPE_V4.json').read_text());universe=json.loads((P/'NEW_DEVELOPMENT/ACQUISITION_UNIVERSE_PRECOMMIT.json').read_text());receipt=json.loads((P/'NEW_DEVELOPMENT/SOURCE_RECEIPTS.json').read_text());portable=json.loads((P/'DATASET_MANIFEST_PORTABLE_V4.json').read_text());exposure=json.loads((P/'EXPOSURE_APPEND_ONLY_DELTA.json').read_text())
 with (P/'DEVELOPMENT_COMPLETION_LEDGER_V4.csv').open() as f:allrows=list(csv.DictReader(f))
 retry=[r for r in allrows if r['security_id'] and r['status']!='ACQUIRED'];assert len(retry)==109
 fixed={str(i):p for i,p in enumerate(universe['proposals'],1)}
 links={x['date']:x['previous'] for x in scope['authorized_current_links']};requests=defaultdict(list)
 for s in receipt:
  if s['endpoint'].endswith('/minute'):requests[(s['scope']['date'],s['scope'].get('code'))].append(s)
 saved={(p['date'],p['security_id']) for p in portable['pairs']};returned_days={s['scope']['date'] for s in receipt if s['endpoint'].endswith('/minute') and s.get('row_N',0)>0}
 # A current day's raw may already have been read as another session's previous-day dependency.
 candidates=[]
 for i,r in enumerate(retry,1):
  code=r['security_id'].split('|')[-1];d=r['date'];p=links[d];source=fixed.get(r['proposal_ordinal'])
  prior=requests[(d,code)];raw_N=sum(x.get('row_N',0) for x in prior);exact_saved=(d,r['security_id']) in saved
  old=r['exposure']=='V1_V2_V3_EXPOSED_DEV'
  no_current_outcome=not exact_saved and raw_N==0 and not old
  reason='EXPOSED_CURRENT_RAW_OR_DEPENDENCY' if raw_N else 'OLD_PAIR_EXPOSURE_NOT_PROVEN_UNOPENED' if old else 'NO_CURRENT_OUTCOME_RETURNED_AND_NO_SAVED_LABEL'
  candidates.append({'retry_ordinal':i,'parent_pair_id':r['pair_id'],'parent_proposal_ordinal':r['proposal_ordinal'] or None,'date':d,'previous':p,'code':code,'security_id':r['security_id'],'session_id':'JPX:'+d,'parent_status':r['status'],'parent_reason':r['reason'],'prior_current_minute_rows_returned':raw_N,'prior_current_request_N':len(prior),'prior_saved_labels_or_features':exact_saved,'fresh_pair_eligible_before_retry':no_current_outcome,'fresh_eligibility_reason':reason,'date_has_other_V1_V4_exposure':d in set(exposure['V1_V2_V3_exposed_dates_retained'])|set(exposure['new_acquired_dates'])|returned_days,'original_selection_provenance':source if source else {'ledger_SHA256':sha(P/'DEVELOPMENT_COMPLETION_LEDGER_V4.csv'),'pair_id':r['pair_id']},'replacement':0})
 save('FRESH_REACQUISITION_SCOPE_FREEZE_V5.json',{'scope_type':'Development fixed selected unavailable109, original ledger order','before_retry_raw_or_labels':True,'bounded_passes':1,'replacement':0,'source_ledger_SHA256':sha(P/'DEVELOPMENT_COMPLETION_LEDGER_V4.csv'),'parent_universe_SHA256':sha(P/'NEW_DEVELOPMENT/ACQUISITION_UNIVERSE_PRECOMMIT.json'),'authorized_days':scope['authorized_Development_days'],'blocked_days':scope['blocked_days'],'proposals':candidates,'all_selected_N':109,'fresh_pair_eligibility_is_provenance_not_outcome':True,'eligible_dates_before_retry':sorted({r['date'] for r in candidates if r['fresh_pair_eligible_before_retry']}),'note':'Old7 conservatively ineligible absent complete prior raw provenance; all109 may be recovered for research. Successful previously returned current raw is never fresh. Same-day other-security exposure is disclosed, not hidden.'})
 fields=['retry_ordinal','parent_pair_id','date','previous','security_id','parent_status','prior_current_minute_rows_returned','prior_current_request_N','prior_saved_labels_or_features','fresh_pair_eligible_before_retry','fresh_eligibility_reason','date_has_other_V1_V4_exposure','replacement']
 with (R/'FRESH_ELIGIBILITY_PROVENANCE_V5.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in candidates)
 info={'retry_N':len(candidates),'dates':len({r['date'] for r in candidates}),'securities':len({r['security_id'] for r in candidates}),'fresh_pair_eligible_N':sum(r['fresh_pair_eligible_before_retry'] for r in candidates),'fresh_pair_eligible_dates':sorted({r['date'] for r in candidates if r['fresh_pair_eligible_before_retry']}),'already_current_raw_exposed_N':sum(r['prior_current_minute_rows_returned']>0 for r in candidates),'old_unavailable_provenance_unknown_N':sum(r['fresh_eligibility_reason']=='OLD_PAIR_EXPOSURE_NOT_PROVEN_UNOPENED' for r in candidates),'authorized_current_dates_N':len(links),'attempted_V1_V4_current_dates_N':len(set(scope['new_evaluation_dates'])|set(exposure['V1_V2_V3_exposed_dates_retained'])),'approved_extra_current_dates_not_in_V1_V4_fixed_scopes':sorted(set(links)-set(scope['new_evaluation_dates'])-set(exposure['V1_V2_V3_exposed_dates_retained'])),'research_recovery_allowed_all109':True}
 save('FRESH_INVENTORY_PROVENANCE_SUMMARY_V5.json',info);print(json.dumps(info,ensure_ascii=False))
if __name__=='__main__':main()
