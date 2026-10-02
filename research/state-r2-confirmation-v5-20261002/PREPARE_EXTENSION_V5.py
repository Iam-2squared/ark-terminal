"""Prepare disjoint, pre-listed Development acquisition only after fixed109 ends.

This never repeats the fixed109 pass. It uses its remaining overall HTTP/step
budget and the second (last) Actions slot. Metadata selector maths are V4 exact.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,zipfile,base64,ast,sys
R=Path(__file__).resolve().parent;T=R/'extension_runner';OLD=R.parent/'state_predictiveness_v4_confirmation_20261002_v1'
PREFIX='research/state-r2-confirmation-v5-20261002/'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def main():
 receipt=json.loads((R/'RECOVERY/RUNNER_FINAL_RECEIPT.json').read_text());ledger=json.loads((R/'RECOVERY/FRESH_REACQUISITION_LEDGER.json').read_text())
 assert receipt['status']=='BOUNDED109_RECOVERY_COMPLETE' and receipt['classified_N']==109 and receipt['labels_created']==0,'RECOVERY_NOT_FIXED'
 fresh=[r for r in ledger if r['status']=='ACQUIRED' and r.get('fresh_trace_export')]
 assert len({r['date'] for r in fresh})<8,'STRUCTURAL_EXTENSION_TRIGGER_NOT_MET'
 assert not any(r.get('reason') in ['PROVIDER_HTTP_401','PROVIDER_HTTP_403','PROVIDER_HTTP_429'] for r in ledger),'PERMISSION_OR_RATE_STOP'
 scope=json.loads((R/'ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json').read_text());caps=json.loads((R/'BUDGET_START_V5.json').read_text())['finite_caps']
 http=caps['new_provider_HTTP']-receipt['actual_provider_HTTP'];steps=caps['frozen_current_slot_steps']-receipt['new_steps'];assert http>0 and steps>0,'NO_REMAINING_BUDGET'
 trigger={'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'trigger':'RECOVERED_FRESH_DATES_LT8_BEFORE_LABELS','recovery_receipt_SHA256':sha(R/'RECOVERY/RUNNER_FINAL_RECEIPT.json'),'scope_metadata_SHA256':sha(R/'ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json'),'fixed109_single_pass_completed':True,'recovered_fresh_pairs':len(fresh),'recovered_fresh_dates':len({r['date'] for r in fresh}),'fresh_labels_created':0,'remaining_HTTP_cap':http,'remaining_kernel_step_cap':steps,'Actions_slot':2,'Actions_total_cap':2,'bounded_acquisition_passes_budget_unit':'one bounded original109 reacquisition; conditional disjoint Development extension is separately authorized by user7.1, not an additional109 retry','old_caps_unchanged':True}
 assert not (R/'EXTENSION_ACTIVATION_RECEIPT_V5.json').exists();save(R/'EXTENSION_ACTIVATION_RECEIPT_V5.json',trigger)
 T.mkdir(exist_ok=False)
 skip={'export_recovery_v5.py','FRESH_REACQUISITION_SCOPE_FREEZE_V5.json','RETRY_EXECUTION_FREEZE_V5.json','config.json'}
 for p in sorted((R/'runner').rglob('*')):
  if p.is_file() and '__pycache__' not in str(p) and p.name not in skip:
   q=T/p.relative_to(R/'runner');q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
 cfg=json.loads((R/'runner/config.json').read_text());cfg.update(authorized_days=sorted({r[k] for r in scope['eligible_links'] for k in ['date','previous']}),blocked_days=scope['protected_exclusion_dates'],maxrequests=http,acquisition_session_scope=[{'date':r['date'],'previous':r['previous']} for r in scope['eligible_links']]);save(T/'config.json',cfg)
 selected_source=(OLD/'runner/metadata_universe.py').read_text()
 start="cfg=a.CFG;pre=json.loads((H/'ACQUISITION_EXPANSION_PRECOMMIT.json').read_text())"
 selected_source=selected_source.replace(start,"cfg=a.CFG;pre=json.loads((H/'EXTENSION_EXECUTION_FREEZE_V5.json').read_text())")
 old="v4=json.loads((H/'PREDICTIVENESS_V4_PRECOMMIT.json').read_text())\n for n,h in v4['hashes'].items():\n  assert hashlib.sha256((H/n).read_bytes()).hexdigest()==h,'PRECOMMIT_CHANGED'"
 assert old in selected_source
 selected_source=selected_source.replace(old,"for n,h in pre['code_hashes'].items():\n  assert hashlib.sha256((H/n).read_bytes()).hexdigest()==h,'PRECOMMIT_CHANGED'")
 selected_source=selected_source.replace("'V4_precommit_SHA256':pre['V4_precommit_SHA256']","'scope_metadata_SHA256':pre['scope_metadata_SHA256']")
 (T/'metadata_universe.py').write_text(selected_source)
 wrapper=(R/'runner/export_recovery_v5.py').read_text()
 wrapper=wrapper.replace('One bounded109 recovery pass.','One disjoint pre-listed24 Development extension pass.')
 wrapper=wrapper.replace("scope=json.loads((H/'FRESH_REACQUISITION_SCOPE_FREEZE_V5.json').read_text())","scope=json.loads((H/'ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json').read_text())")
 wrapper=wrapper.replace("expected=json.loads((H/'RETRY_EXECUTION_FREEZE_V5.json').read_text())","expected=json.loads((H/'EXTENSION_EXECUTION_FREEZE_V5.json').read_text())")
 wrapper=wrapper.replace("sha(H/'FRESH_REACQUISITION_SCOPE_FREEZE_V5.json')==expected['scope_SHA256']","sha(H/'ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json')==expected['scope_metadata_SHA256']")
 before="proposals=scope['proposals'];assert len(proposals)==109 and [p['retry_ordinal'] for p in proposals]==list(range(1,110)),'FIXED109_ORDER'\n save('FRESH_REACQUISITION_SCOPE_FREEZE_V5.json',scope);save('RETRY_EXECUTION_FREEZE_V5.json',expected)"
 after="import metadata_universe\n universe=metadata_universe.build(H,save)\n proposals=[{**p,'retry_ordinal':i,'parent_pair_id':None,'parent_proposal_ordinal':i,'parent_status':'UNEXPOSED_DEVELOPMENT_ADDITIONAL_FIXED_METADATA','fresh_pair_eligible_before_retry':True,'fresh_eligibility_reason':'UNOPENED_DATE_AND_PAIR_BEFORE_RAW'} for i,p in enumerate(universe['proposals'],1)]\n assert len(proposals)<=72,'FIXED_EXTENSION_ORDER'\n scope={**scope,'authorized_days':cfg['authorized_days'],'blocked_days':cfg['blocked_days']}\n save('EXTENSION_SELECTED_METADATA_SCOPE_V5.json',{'proposals':proposals,'minute_requests_before_selection':0,'labels_before_selection':0,'scope_metadata_SHA256':expected['scope_metadata_SHA256']});save('EXTENSION_EXECUTION_FREEZE_V5.json',expected)"
 assert before in wrapper;wrapper=wrapper.replace(before,after)
 before="factor=True\n   for day in [d,p]:\n    rows=fetch(day,'daily',c)\n    if not rows or any(Fraction(str(r.get('AdjFactor','0')))!=1 or r.get('ExRT') is not None for r in rows):factor=False\n   if not factor:entry.update(status='FACTOR_UNAVAILABLE',reason='FACTOR_CONTINUITY_UNAVAILABLE');flush();continue"
 assert before in wrapper;wrapper=wrapper.replace(before,"# Factor eligibility was already checked before minute acquisition by unchanged metadata selector.\n   assert len(pair['factor_sources'])==2,'FACTOR_METADATA_RECEIPT_MISSING'")
 wrapper=wrapper.replace("pid=f'V5N{i:03d}'","pid=f'V5E{i:03d}'").replace("steps<=40000","steps<=expected['remaining_kernel_step_cap']").replace("status='BOUNDED109_RECOVERY_COMPLETE'","status='FIXED_DEVELOPMENT_EXTENSION_COMPLETE'").replace("'original_fixed_N':109","'original_fixed_N':len(proposals),'fixed_date_N':24,'metadata_HTTP':universe['provider_requests_before_minute']").replace("RAW.name=='state-r2-v5-raw'","RAW.name=='state-r2-v5-extension-raw'")
 (T/'export_extension_v5.py').write_text(wrapper);(T/'ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json').write_bytes((R/'ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json').read_bytes())
 frozen={**trigger,'date_links':cfg['acquisition_session_scope'],'proposal_cap':72,'scope_metadata_SHA256':sha(T/'ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json'),'code_hashes':{str(p.relative_to(T)):sha(p) for p in sorted(T.rglob('*')) if p.is_file() and (p.suffix=='.py' or p.name in ['profile.json','source_snapshot.json','config.json','FEATURE_SCHEMA_V2.json'])},'labels_cap':0,'fit_cap':0,'bootstrap_cap':0,'selector_original_V4_SHA256':sha(OLD/'runner/metadata_universe.py'),'selector_semantic_change':0}
 save(T/'EXTENSION_EXECUTION_FREEZE_V5.json',frozen);save(R/'EXTENSION_EXECUTION_FREEZE_V5.json',frozen)
 for p in T.rglob('*.py'):ast.parse(p.read_text())
 payload=R/'ACQUISITION_EXTENSION_PAYLOAD_V5.zip'
 with zipfile.ZipFile(payload,'x',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(T.rglob('*')):
   if p.is_file():z.write(p,str(p.relative_to(T)))
 b64=base64.b64encode(payload.read_bytes()).decode()+'\n';(R/'ACQUISITION_EXTENSION_PAYLOAD_V5.b64').write_text(b64)
 workflow=(R/'state-r2-confirmation-v5-20261002.yml').read_text()
 before_hash=sha(R/'ACQUISITION_PAYLOAD_V5.zip')
 for a,b in [('State Predictiveness V5 Fixed109 Recovery','State Predictiveness V5 Disjoint Development Extension'),('state-r2-confirmation-v5-20261002.yml','state-r2-v5-extension-20261002.yml'),('state-r2-confirmation-v5-20261002\n','state-r2-v5-extension-20261002\n'),('/payload.b64','/extension-payload.b64'),('state-r2-v5-code','state-r2-v5-extension-code'),('state-r2-v5-raw','state-r2-v5-extension-raw'),('state-r2-v5-evidence','state-r2-v5-extension-evidence'),('export_recovery_v5.py','export_extension_v5.py'),('Fixed109 approved Development recovery; no labels','Fixed24 Development metadata-first extension; no labels'),('state-predictiveness-v5-recovery-','state-predictiveness-v5-extension-'),(before_hash,sha(payload))]:workflow=workflow.replace(a,b)
 (R/'state-r2-v5-extension-20261002.yml').write_text(workflow)
 print(json.dumps({'tree_elements':[{'path':'.github/workflows/state-r2-v5-extension-20261002.yml','type':'blob','mode':'100644','content':workflow},{'path':PREFIX+'extension-payload.b64','type':'blob','mode':'100644','content':b64}]}))
if __name__=='__main__':main()
