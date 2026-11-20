"""Mechanical IO harness reuse; semantic kernel and input math byte-identical."""
from pathlib import Path
import json,hashlib,shutil,zipfile,base64,ast
R=Path(__file__).resolve().parent;V=R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1';T=R/'runner';PREFIX='research/state-r2-support-v6-20261002/'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def main():
 scope=json.loads((R/'FRESH_SCOPE_V6.json').read_text());T.mkdir(exist_ok=False)
 skip={'export_extension_v5.py','metadata_universe.py','EXTENSION_EXECUTION_FREEZE_V5.json','ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json','config.json'}
 for p in (V/'extension_runner').rglob('*'):
  if p.is_file() and p.name not in skip and '__pycache__' not in p.parts:
   q=T/p.relative_to(V/'extension_runner');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 cfg=json.loads((V/'extension_runner/config.json').read_text());cfg.update(authorized_days=scope['approved_minute_days'],blocked_days=scope['blocked_days'],maxrequests=scope['provider_request_cap'],exclusion_pairs=scope['B_exclusion_pairs'],acquisition_session_scope=scope['B_eligible_links']);save(T/'config.json',cfg);shutil.copyfile(R/'FRESH_SCOPE_V6.json',T/'FRESH_SCOPE_V6.json')
 meta=(V/'extension_runner/metadata_universe.py').read_text().replace('EXTENSION_EXECUTION_FREEZE_V5.json','ACQUISITION_EXECUTION_FREEZE_V6.json').replace("record['selected_proposal_N']==3","record['selected_proposal_N']==4").replace("record['selected_proposal_N']<3","record['selected_proposal_N']<4").replace('LESS_THAN_THREE_FACTOR_COMPATIBLE','LESS_THAN_FOUR_FACTOR_COMPATIBLE')
 (T/'metadata_universe.py').write_text(meta)
 source=(V/'extension_runner/export_extension_v5.py').read_text().replace('ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json','FRESH_SCOPE_V6.json').replace('EXTENSION_EXECUTION_FREEZE_V5.json','ACQUISITION_EXECUTION_FREEZE_V6.json')
 begin="proposals=[{**p,'retry_ordinal':i,'parent_pair_id':None,'parent_proposal_ordinal':i,'parent_status':'UNEXPOSED_DEVELOPMENT_ADDITIONAL_FIXED_METADATA','fresh_pair_eligible_before_retry':True,'fresh_eligibility_reason':'UNOPENED_DATE_AND_PAIR_BEFORE_RAW'} for i,p in enumerate(universe['proposals'],1)]"
 replacement="new=[{**p,'parent_pair_id':None,'parent_proposal_ordinal':j,'parent_status':'UNEXPOSED_DEVELOPMENT_METADATA_PAIR','fresh_pair_eligible_before_retry':True,'fresh_eligibility_reason':'NO_PRIOR_RAW_OR_LABEL_PAIR','V6_minute_retry_authorized':True,'V6_pre_skip_reason':None,'lane':'B_NEW'} for j,p in enumerate(universe['proposals'],1)]\n proposals=[{**p,'lane':'A_RETRY'} for p in scope['A_ordered136']]+new\n proposals=[{**p,'retry_ordinal':j} for j,p in enumerate(proposals,1)]"
 assert begin in source;source=source.replace(begin,replacement)
 source=source.replace("len(proposals)<=72","len(proposals)<=452").replace('FIXED_EXTENSION_ORDER','FIXED_V6_ORDER').replace('EXTENSION_SELECTED_METADATA_SCOPE_V5.json','SELECTED_METADATA_SCOPE_V6.json')
 source=source.replace("pid=f'V5E{i:03d}'","pid=f'V6N{i:03d}'")
 # Record every original selected unavailable proposal, but avoid forbidden/ineligible reopening.
 before="assert d in scope['authorized_days'] and p in scope['authorized_days'] and d not in scope['blocked_days'] and p not in scope['blocked_days'],'PROTECTED_BOUNDARY'"
 source=source.replace(before,"if pair['V6_minute_retry_authorized']:assert d in scope['authorized_days'] and p in scope['authorized_days'] and d not in scope['blocked_days'] and p not in scope['blocked_days'],'PROTECTED_BOUNDARY'")
 source=source.replace("entry.update(pair_id=pid,status=None,reason=None,replacement=0,request_attempted=False)","entry.update(pair_id=pid,lane=pair['lane'],status=None,reason=None,replacement=0,request_attempted=False)")
 source=source.replace("ledger.append(entry)\n  if provider_stopped:","ledger.append(entry)\n  if not pair['V6_minute_retry_authorized']:entry.update(status='OTHER_EXPLICIT_REASON',reason=pair['V6_pre_skip_reason']);flush();continue\n  opened_now={(z['scope']['date'],z['scope'].get('code')) for z in a.receipts if z['endpoint'].endswith('/minute') and z.get('row_N',0)>0}\n  if (d,c) in opened_now:entry.update(status='OTHER_EXPLICIT_REASON',reason='CURRENT_ALREADY_OPENED_AS_OTHER_SELECTED_DEPENDENCY_IN_V6_NO_REFILL');flush();continue\n  if provider_stopped:")
 before="# Factor eligibility was already checked before minute acquisition by unchanged metadata selector.\n   assert len(pair['factor_sources'])==2,'FACTOR_METADATA_RECEIPT_MISSING'"
 after="if pair['lane']=='A_RETRY':\n    factor=True\n    for day in [d,p]:\n     rows=fetch(day,'daily',c)\n     if not rows or any(Fraction(str(r.get('AdjFactor','0')))!=1 or r.get('ExRT') is not None for r in rows):factor=False\n    if not factor:entry.update(status='FACTOR_UNAVAILABLE',reason='FACTOR_CONTINUITY_UNAVAILABLE');flush();continue\n   else:assert len(pair['factor_sources'])==2,'FACTOR_METADATA_RECEIPT_MISSING'"
 assert before in source;source=source.replace(before,after)
 source=source.replace("status='FIXED_DEVELOPMENT_EXTENSION_COMPLETE'","status='FIXED_V6_DEVELOPMENT_PASS_COMPLETE'")
 source=source.replace("'fixed_date_N':24","'fixed_date_N':len(scope['fixed_calendar_dates'])").replace("RAW.name=='state-r2-v5-extension-raw'","RAW.name=='state-r2-v6-raw'")
 (T/'export_v6.py').write_text(source)
 core=['PATH_FROZEN.py','CAUSAL_FEATURE_BUILDER.py','input_gate.py','normalize80.py','normalize120.py','engine_stream.py','profile.json','source_snapshot.json']
 for n in core:assert sha(T/n)==sha(V/'extension_runner'/n),'FROZEN_KERNEL_COPY'
 expected={'date_links':scope['B_eligible_links'],'proposal_cap':scope['B_target_N_upper'],'scope_metadata_SHA256':sha(T/'FRESH_SCOPE_V6.json'),'remaining_kernel_step_cap':scope['frozen_slot_step_cap'],'provider_HTTP_cap':scope['provider_request_cap'],'labels_cap':0,'fit_cap':0,'bootstrap_cap':0,'code_hashes':{str(p.relative_to(T)):sha(p) for p in sorted(T.rglob('*')) if p.is_file() and (p.suffix=='.py' or p.name in ['profile.json','source_snapshot.json','config.json','FEATURE_SCHEMA_V2.json'])},'V5_semantic_kernel_change':0,'V6_scope_change_only_metadata_max_per_day':4,'same_day_other_security_exposure_explicit':True}
 save(T/'ACQUISITION_EXECUTION_FREEZE_V6.json',expected);save(R/'ACQUISITION_EXECUTION_FREEZE_V6.json',expected)
 for p in T.rglob('*.py'):ast.parse(p.read_text())
 payload=R/'ACQUISITION_PAYLOAD_V6.zip'
 with zipfile.ZipFile(payload,'x',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(T.rglob('*')):
   if p.is_file():z.write(p,str(p.relative_to(T)))
 b64=base64.b64encode(payload.read_bytes()).decode()+'\n';(R/'ACQUISITION_PAYLOAD_V6.b64').write_text(b64)
 workflow=(V/'state-r2-v5-extension-20261002.yml').read_text()
 for old,new in [('State Predictiveness V5 Disjoint Development Extension','State Predictiveness V6 Fixed Support Completion'),('state-predictiveness-v5-r2-confirmation-20261002-v1','state-predictiveness-v6-support-completion-20261002-v1'),('state-r2-v5-extension-20261002','state-r2-v6-support-20261002'),('research/state-r2-confirmation-v5-20261002/extension-payload.b64',PREFIX+'payload.b64'),('state-r2-v5-extension-code','state-r2-v6-code'),('state-r2-v5-extension-raw','state-r2-v6-raw'),('state-r2-v5-extension-evidence','state-r2-v6-evidence'),('export_extension_v5.py','export_v6.py'),('Fixed24 Development metadata-first extension; no labels','Fixed Development support completion; no labels'),('state-predictiveness-v5-extension-','state-predictiveness-v6-support-'),(sha(V/'ACQUISITION_EXTENSION_PAYLOAD_V5.zip'),sha(payload))]:workflow=workflow.replace(old,new)
 (R/'state-r2-v6-support-20261002.yml').write_text(workflow)
 print(json.dumps({'payload_bytes':payload.stat().st_size,'payload_SHA256':sha(payload),'core_change':0,'labels':0,'fits':0,'new_proposals_cap':len(scope['B_eligible_links'])*4}))
if __name__=='__main__':main()
