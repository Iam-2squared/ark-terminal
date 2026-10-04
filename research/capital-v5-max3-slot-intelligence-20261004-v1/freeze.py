from common import *
import zipfile
from collections import Counter
def main():
 z=zipfile.ZipFile(WORK/'source_v4/deliverables/Ark_Capital_MAX3_Upward_Staircase_v4_20261004_PRIVATE.zip')
 checked={}
 for item in z.infolist():
  if item.is_dir():continue
  local=SOURCE/item.filename
  digest=hashlib.sha256(z.read(item)).hexdigest()
  assert sha(local)==digest,('SOURCE_CHANGED',item.filename)
  checked[item.filename]=digest
 save(OUT/'SOURCE_HASHES.json',checked)
 score=rows(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')
 assert len(score)==1039 and sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')=='c446633dec923e3a80a534b19325ccff49f769a2ff1d29c7af1202202de614d4'
 assert all(r['ML']==r['capital_score'] and r['rank']==('S' if r['ML']>=2 else 'A' if r['ML']>=1.5 else 'B' if r['ML']>=1 else 'C') and r['admission']==(r['ML']>=1) for r in score)
 teachers={r['entry_id']:r for r in rows(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
 ds=rows(FROZEN/'UPWARD_STAIRCASE_V4_MAX3_DECISIONS.jsonl.gz')
 control=json.loads((FROZEN/'UPWARD_STAIRCASE_V4_MAX3_RESULT.json').read_text())
 assert control['final_equity']==1433740.25 and control['funded_N']==172
 assert all(r['session'] in json.loads((SOURCE/'repo/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json').read_text())['all58'] for r in score)
 summary={}
 for k,denom,funded,miss,cash,below in [(5,113,42,66,5,57),(10,47,23,21,3,20)]:
  cohort={r['entry_id'] for r in score if teachers[r['entry_id']]['potential_return']>=k/100}
  counts=dict(Counter(d['reason'] for d in ds if d['entry_id'] in cohort))
  assert counts=={'FUNDED':funded,'MAX_POSITION_CAP':miss,'CASH_OR_LOT_CONSTRAINED':cash,'UPWARD_BELOW_BASELINE':below},counts
  assert sum(r['admission'] and r['entry_id'] in cohort for r in score)==denom
  summary[f'U{k}']={'denominator':denom,'funded':funded,'conversion':funded/denom,'MAX3_miss':miss,'reserve_rejected':0,'Net_Slot_Miss':miss,'cash_lot_miss':cash,'below_baseline':below}
 x={'JST':now(),'source_files_checked':len(checked),'control':control,'primary_denominators':summary,'model_hashes':json.loads((FROZEN/'MODEL_HASHES.json').read_text()),'score_sha256':sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'),'rank_counts':dict(Counter(r['rank'] for r in score)),'control_replay':0,'new_fit':0,'frozen_Entry_HEAD':'4a2d6f35946b16820a13449a9288a6685a5c283c','frozen_EXIT_HEAD':'c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad','EXIT_receipt':'1ecbcc43f75279fa302f19fd896add2aac15b537','v4_main_HEAD':'dd35da3fc19770823b3844e2e2798e6c1e9a91d3'}
 save(OUT/'V4_CONTROL_FREEZE.json',x)
 checkpoint('V1_V4_MODEL_RANK_CONTROL_FREEZE','FROZEN',{'files':len(checked),'U5':summary['U5'],'U10':summary['U10'],'control_final':control['final_equity']})
 print(json.dumps({'source_files':len(checked),'U5':summary['U5'],'U10':summary['U10']}))
if __name__=='__main__':main()
