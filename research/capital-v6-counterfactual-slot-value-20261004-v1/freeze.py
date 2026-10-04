"""Read-only original/remote byte and saved Control census freeze."""
from common import *
from collections import Counter
import zipfile
def main():
 checked={}; archive=WORK/'deliverables/Ark_Capital_v5_MAX3_Slot_Intelligence_20261004_PRIVATE.zip'
 with zipfile.ZipFile(archive) as z:
  for item in z.infolist():
   if item.is_dir():continue
   local=WORK/item.filename
   if local.exists():
    expected=hashlib.sha256(z.read(item)).hexdigest();assert sha(local)==expected,('V5_ARCHIVED_BYTE_MISMATCH',item.filename);checked[item.filename]=expected
 prior=json.loads((V5OUT/'SOURCE_HASHES.json').read_text())
 for name,expected in prior.items():
  local=SOURCE/name; assert sha(local)==expected,('SOURCE_HASH_MISMATCH',name);checked['source_main/'+name]=expected
 trees=json.loads((WORK/'v6_frozen_github_trees.json').read_text());remote_checks=0;line_encoding=[]
 for tag,local in [('v5_code',V5CODE),('v5_evidence',V5OUT)]:
  for item in trees[tag]['tree']:
   if item['type']!='blob':continue
   p=local/item['path'];data=p.read_bytes()
   digest=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
   if digest!=item['sha']:
    lf=data.replace(b'\r\n',b'\n');d2=hashlib.sha1(b'blob '+str(len(lf)).encode()+b'\0'+lf).hexdigest()
    assert p.suffix=='.csv' and d2==item['sha'] and 'ARTIFACT_BYTE_ENCODING_AUDIT.json' in [x['path'] for x in trees['v5_evidence']['tree']],('GITHUB_SOURCE_MISMATCH',str(p))
    line_encoding.append({'path':str(p.relative_to(ROOT)),'raw_sha256':sha(p),'github_LF_sha256':hashlib.sha256(lf).hexdigest(),'values_rows_order_identity':True})
   remote_checks+=1
 score=rows(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')
 assert len(score)==1039 and sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')=='c446633dec923e3a80a534b19325ccff49f769a2ff1d29c7af1202202de614d4'
 assert all(r['ML']==r['capital_score'] and r['admission']==(r['ML']>=1) and r['rank']==('S' if r['ML']>=2 else 'A' if r['ML']>=1.5 else 'B' if r['ML']>=1 else 'C') for r in score)
 ds=rows(V5PRIVATE/'CAPITAL_MAX3_SLOT_RESERVE_V1_DECISIONS.jsonl.gz');labels={r['entry_id']:r for r in rows(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
 control=json.loads((V5PRIVATE/'CAPITAL_MAX3_SLOT_RESERVE_V1_RESULT.json').read_text());assert control==json.loads((V5OUT/'MAIN_REPLAY_RESULT.json').read_text())
 assert control['funded_N']==150 and control['final_equity']==1477436.15
 cohorts={}
 for k,denom,fund,cap,reserve,cash in [(5,113,50,28,30,5),(10,47,26,9,10,2)]:
  ids={r['entry_id'] for r in score if r['admission'] and labels[r['entry_id']]['potential_return']>=k/100}
  cnt=Counter(d['reason'] for d in ds if d['entry_id'] in ids)
  assert len(ids)==denom and cnt=={'FUNDED':fund,'MAX_POSITION_CAP':cap,'SLOT_RESERVE_REJECT':reserve,'CASH_OR_LOT_CONSTRAINED':cash},cnt
  cohorts[f'U{k}']={'rank_pass':denom,'funded':fund,'conversion':fund/denom,'MAX3_miss':cap,'reserve_reject':reserve,'Net_Slot_Miss':cap+reserve,'cash_lot':cash}
 oracle=json.loads((V5OUT/'ORACLE_UPPER_BOUND.json').read_text());assert [oracle[k] for k in ('maximum_feasible_U5','maximum_U10_conditional_on_max_U5','maximum_Medium_conditional_on_max_U5_U10')]==[104,47,52]
 for p in [V5PRIVATE/'TRAINING_ONLY_SCORED_ARRIVALS.jsonl.gz',V5OUT/'ARRIVAL_TABLE.json',V5OUT/'ORACLE_UPPER_BOUND.json',V5PRIVATE/'ORACLE_WITNESS.jsonl.gz']:
  checked[str(p.relative_to(WORK))]=sha(p)
 save(OUT/'SOURCE_HASHES.json',checked)
 save(OUT/'V5_CONTROL_ORACLE_FREEZE.json',{'exact_jst':now(),'v5_final_head':BASIS,'archived_byte_checks':len(checked),'github_blob_checks':remote_checks,'previous_known_CSV_encoding':line_encoding,'source_mismatch':0,'model_score_rank_changes':0,'control_replay':0,'teacher_training_trajectory_replay_allowed':True,'winner_fit':0,'Control':control,'cohorts':cohorts,'oracle':oracle,'oracle_changed':0,'oracle_recovery_U5':50/104,'oracle_recovery_U10':26/47,'exposure':EXPOSURE,'safety':SAFETY})
 status('D1_V5_CONTROL_ORACLE_FREEZE','END','V5_AND_ORACLE_FROZEN',completed=['Archived source hashes and GitHub blobs verified','Saved v5 U5/U10 census independently joined','v5 Control read-only, Oracle unchanged'],not_executed=['Teacher construction','Slot fits','Main replay'],result={'checked_files':len(checked),'github_blobs':remote_checks,'U5':cohorts['U5'],'U10':cohorts['U10'],'oracle_U5':104},next_policy=['Precommit exact teacher and runtime features','Construct training-only state union and apply support gate'])
 print(json.dumps({'checked_files':len(checked),'github_blobs':remote_checks,'cohorts':cohorts}))
if __name__=='__main__':main()
