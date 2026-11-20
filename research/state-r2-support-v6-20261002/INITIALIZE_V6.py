"""Read-only parent verification; outcome-free scope provenance. No fits/acquisition."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
import json,hashlib,zipfile,csv
R=Path(__file__).resolve().parent;V=R.parent/'state_predictiveness_v5_r2_confirmation_20261002_v1';P=V/'PARENT_V4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
 p=R/n;assert not p.exists(),'IMMUTABLE_EXISTING:'+n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def main():
 jst=datetime.now(timezone(timedelta(hours=9))).isoformat();remote=json.loads((R/'INITIAL_REPO_GET_V6.json').read_text());final=json.loads((V/'FINAL_RECEIPT_V5.json').read_text());delivery=json.loads((V/'GITHUB_DELIVERY_FINAL_SNAPSHOT_V5.json').read_text());manifest=json.loads((V/'DELIVERY_MANIFEST.json').read_text());checks=[]
 publication_differences=[]
 for name,text in remote['exact_files'].items():
  original=(V/name).read_bytes();published=(V/name).read_text().encode()
  assert text.encode()==published,'PARENT_REMOTE_CONTENT_MISMATCH:'+name
  if original!=published:publication_differences.append({'path':name,'archive_bytes':len(original),'archive_SHA256':sha(V/name),'public_bytes':len(published),'public_SHA256':hashlib.sha256(published).hexdigest(),'conversion':'V5 PUBLISH_TREE_V5.py p.read_text() universal-newline CRLF to LF; archive remains authoritative','numeric_or_row_changes':0})
 for n,h in json.loads((V/'PREDICTIVENESS_V5_PRECOMMIT.json').read_text())['hashes'].items():assert sha(V/n)==h,'V5_PRECOMMIT_HASH_MISMATCH:'+n
 assert remote['branch']['commit']['sha']==delivery['verified_delivery_snapshot_HEAD'],'PARENT_HEAD_MISMATCH'
 assert final['status']=='STATE_R2_CONFIRMATION_LIMITED_SAMPLE' and final['independent_audit']=='PASS' and final['mismatch_N']==0 and final['R2_candidate_local_control']=='PASS','PARENT_RESULT_MISMATCH'
 for e in remote['directory']:
  p=V/e['name']
  if p.is_file() and e['name']!='SOURCE_CODE_LOCATION_INDEX_V5.json':
   published=p.read_text().encode();assert hashlib.sha1(b'blob '+str(len(published)).encode()+b'\0'+published).hexdigest()==e['sha'],'PARENT_GIT_BLOB_MISMATCH:'+e['name']
 archives=[];members={}
 for p in sorted((R.parent/'delivery_v5').glob('Ark_Terminal_V5_Part*.zip')):
  with zipfile.ZipFile(p) as z:
   assert z.testzip() is None,'PARENT_ZIP_CRC'
   for n in z.namelist():
    if n.endswith('/'):continue
    h=hashlib.sha256(z.read(n)).hexdigest()
    if n in members:assert members[n]==h,'PARENT_PART_MEMBER_MISMATCH'
    members[n]=h
  archives.append({'path':str(p.relative_to(R.parent)),'bytes':p.stat().st_size,'SHA256':sha(p)})
 assert len(archives)==3,'V5_COMPLETE_ARCHIVES_MISSING'
 for e in manifest['files']:
  n=e['path'];assert n in members and members[n]==e['SHA256'],'PARENT_COMPLETE_MANIFEST_MISMATCH:'+n
 rows=[json.loads(line) for line in (V/'R1_R2_FRESH_OOF_V5.jsonl').open()];real=[r for r in rows if r['control']=='REAL' and r['model']=='R2' and r['calibrated']];down=[r for r in real if r['actual']=='DOWN_REVERSAL'];up=[r for r in real if r['actual']=='UP_CONTINUE'];assert len(down)==75 and len(up)==354 and len(real)==542,'PARENT_SUPPORT_MISMATCH'
 for logical,n,key in [('contract','PREDICTIVENESS_V5_CONTRACT.md','contract_SHA256'),('precommit','PREDICTIVENESS_V5_PRECOMMIT.json','precommit_SHA256'),('scope','FRESH_DATA_SCOPE_V5.json','scope_SHA256'),('OOF','R1_R2_FRESH_OOF_V5.jsonl','OOF_SHA256')]:
  h=sha(V/n);assert h==final[key],'PARENT_FROZEN_HASH_MISMATCH';checks.append({'identity':logical,'path':n,'SHA256':h})
 audit=json.loads((V/'INDEPENDENT_AUDIT_V5.json').read_text());budget=json.loads((V/'BUDGET_FINAL_V5.json').read_text());exposure=json.loads((V/'EXPOSURE_APPEND_ONLY_DELTA_V5.json').read_text());null=list(csv.DictReader((V/'TRUE_NULL_R2_V5.csv').open()))
 counts={}
 for model in ['R1','R2']:
  rr=[r for r in rows if r['control']=='REAL' and r['model']==model and r['calibrated']];pred=Counter(r['predicted'] for r in rr);num=sum(r['actual']=='DOWN_REVERSAL' and r['predicted']=='UP_CONTINUE' for r in rr);den=pred['UP_CONTINUE'];counts[model]={'N':len(rr),'predicted':dict(pred),'dangerous_numerator':num,'dangerous_denominator':den,'dangerous_rate':num/den}
 receipt={'JST':jst,'status':'PASS','V5_status_unchanged':final['status'],'V5_branch':remote['branch']['name'],'V5_final_experimental_HEAD':delivery['experimental_C7_snapshot_HEAD'],'V5_final_delivery_HEAD':remote['branch']['commit']['sha'],'actual_repo_GET':True,'hash_checks':checks,'complete_archive_checks':archives,'manifest_entries_verified':len(manifest['files']),'exact_evaluable_dates':sorted({r['date'] for r in real}),'exact_evaluable_folds':sorted({r['fold'] for r in real}),'R1_R2_prediction_counts':counts,'DOWN_support':75,'DOWN_support_by_date':dict(Counter(r['date'] for r in down)),'DOWN_support_by_fold':dict(Counter(r['fold'] for r in down)),'DOWN_support_by_security':dict(Counter(r['security_id'] for r in down)),'UP_support':354,'TRUE_NULL_receipt':null,'independent_receipt_SHA256':sha(V/'INDEPENDENT_AUDIT_V5.json'),'independent_status':audit['status'],'independent_mismatch_N':audit['mismatch_N'],'calibration_failure':'date-equal LL +7.573886% and row Brier +7.745282%, both exceed precommitted 5%; method remains frozen','exposure_receipt_SHA256':sha(V/'EXPOSURE_APPEND_ONLY_DELTA_V5.json'),'exposure_ledger':exposure,'budget_final_SHA256':sha(V/'BUDGET_FINAL_V5.json'),'past_known_bootstrap':budget['cumulative_known_bootstrap_vectors'],'past_known_provider_HTTP':budget['cumulative_known_provider_HTTP'],'past_known_kernel_steps':budget['cumulative_known_frozen_steps'],'parent_writes':0,'past_history_retained':True}
 receipt['public_CSV_newline_conversion_separately_verified']=publication_differences;receipt['V5_publication_source_SHA256']=sha(V/'PUBLISH_TREE_V5.py');receipt['frozen_original_hash_mismatch_N']=0
 receipt['source_index_snapshot_distinction']={'archive_index_SHA256':sha(V/'SOURCE_CODE_LOCATION_INDEX_V5.json'),'repo_published_index_SHA256':sha(R/'V5_REPO_SOURCE_INDEX_GET.json'),'reason':'delivery index pins final delivery HEAD after the public snapshot; both retained, no model/precommit/result change'}
 save('V5_INHERITANCE_RECEIPT_V6.json',receipt)
 allocation=json.loads(remote['allocation_text']);assert not allocation['outcomesInspected'] and not allocation['futureLabelsGenerated'];assert (V/'INVENTORY_METADATA/SESSION_ALLOCATION_METADATA_V3.json').read_bytes()==remote['allocation_text'].encode(),'ALLOCATION_METADATA_MISMATCH'
 dev={d for k,ds in allocation['partitions'].items() if k.startswith('DEVELOPMENT_') for d in ds};blocked={d for k,ds in allocation['partitions'].items() if not k.startswith('DEVELOPMENT_') for d in ds};scope=json.loads((P/'DATA_SCOPE_V4.json').read_text());blocked|=set(scope['blocked_days']);links={r['date']:r['previous'] for r in scope['authorized_current_links']};links.update({r['date']:r['previous'] for r in json.loads((V/'ADDITIONAL_DEVELOPMENT_INVENTORY_FREEZE_V5.json').read_text())['eligible_links']});eligible=[{'date':d,'previous':links[d]} for d in sorted(dev) if d in links and links[d] in dev and d not in blocked and links[d] not in blocked];excluded=[{'date':d,'reason':'NO_APPROVED_EXPLICIT_PREVIOUS_DEVELOPMENT_DEPENDENCY'} for d in sorted(dev) if d not in {r['date'] for r in eligible}]
 returned=set();all_proposed=set();sources=[]
 for root in [P/'NEW_DEVELOPMENT',V/'RECOVERY',V/'EXTENSION']:
  fn=root/'SOURCE_RECEIPTS.json'
  for s in json.loads(fn.read_text()):
   if s['endpoint'].endswith('/minute') and s.get('row_N',0)>0:returned.add((s['scope']['date'],s['scope'].get('code')))
  sources.append({'path':str(fn.relative_to(V)),'SHA256':sha(fn)})
 for p in json.loads((P/'DATASET_MANIFEST_PORTABLE_V4.json').read_text())['pairs']+json.loads((V/'FRESH_DATA_MANIFEST_V5.json').read_text())['pairs']:returned.add((p['date'],p['security_id'].split('|')[-1]))
 original=json.loads((V/'FRESH_REACQUISITION_SCOPE_FREEZE_V5.json').read_text())['proposals'];ext=json.loads((V/'EXTENSION/EXTENSION_SELECTED_METADATA_SCOPE_V5.json').read_text())['proposals'];prior={('RECOVERY',r['retry_ordinal']):r for r in original};prior.update({('EXTENSION',r['retry_ordinal']):r for r in ext});retry=[]
 for lane in ['RECOVERY','EXTENSION']:
  for row in json.loads((V/lane/'FRESH_REACQUISITION_LEDGER.json').read_text()):
   pair=prior[(lane,row['retry_ordinal'])];all_proposed.add((pair['date'],pair['code']))
   if row['status']=='ACQUIRED':continue
   fresh=(pair['date'],pair['code']) not in returned and pair.get('fresh_pair_eligible_before_retry',False);reason='NO_V1_V5_RETURNED_CURRENT_RAW_OR_LABEL' if fresh else 'PRIOR_RAW_LABEL_OR_UNPROVEN_OLD_EXPOSURE'
   retry.append({**pair,'retry_ordinal':len(retry)+1,'parent_lane':lane,'parent_V5_status':row['status'],'parent_V5_reason':row['reason'],'fresh_pair_eligible_before_retry':fresh,'fresh_eligibility_reason':reason,'parent_proposal_ordinal':pair.get('parent_proposal_ordinal'), 'replacement':0})
 assert len(retry)==136,'FIXED_UNAVAILABLE_INVENTORY_MISMATCH'
 save('INVENTORY_PROVENANCE_V6.json',{'JST':jst,'source_repo_HEAD':remote['branch']['commit']['sha'],'partition_source_path':'predict/long-only/phase57-long-only-session-allocation-v3.json','partition_source_SHA256':hashlib.sha256(remote['allocation_text'].encode()).hexdigest(),'outcomes_read_from_inventory':0,'eligible_links':eligible,'eligible_dates':[r['date'] for r in eligible],'date_exclusions':excluded,'blocked_days':sorted(blocked),'historical_current_or_dependency_raw_exclusion_pairs':[{'date':d,'code':c} for d,c in sorted(returned)],'previously_selected_pairs_no_replacement':[{'date':d,'code':c} for d,c in sorted(all_proposed)],'source_receipts':sources,'original_ordered_unavailable136':retry,'original136_fresh_eligible_N':sum(r['fresh_pair_eligible_before_retry'] for r in retry),'B_outcome_unit':'exact security/session, dates may have other-security prior exposure; never claim wholly unseen dates','same_date_reused_security_rule':'exclude current AND previous minute-returned pair for B selection','prior_labels_unknown_conservatively_excluded':True})
 print(json.dumps({'inheritance':'PASS','V5_head':receipt['V5_final_delivery_HEAD'],'V5_hashes':checks,'V5_DOWN':75,'V5_UP':354,'metadata_B_eligible_dates':len(eligible),'A_unavailable136':len(retry),'A_fresh_eligible':sum(r['fresh_pair_eligible_before_retry'] for r in retry),'minute_exclusion_pairs':len(returned),'new_labels':0,'new_fits':0}))
if __name__=='__main__':main()
