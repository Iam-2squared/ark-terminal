from common import *
import zipfile
from collections import Counter
def main():
 z=zipfile.ZipFile(WORK/'deliverables/Ark_Capital_MAX3_Upward_Staircase_v4_20261004_PRIVATE.zip')
 checked={}
 for name in z.namelist():
  local=WORK/name
  if local.is_file():
   digest=hashlib.sha256(z.read(name)).hexdigest();assert sha(local)==digest,('FROZEN_LOCAL_PACKAGE_MISMATCH',name);checked[name]=digest
 assert sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')=='c446633dec923e3a80a534b19325ccff49f769a2ff1d29c7af1202202de614d4'
 score=rows(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz');assert len(score)==1039
 assert all(r['ML']==r['capital_score'] and r['admission']==(r['ML']>=1) and r['rank']==('S' if r['ML']>=2 else 'A' if r['ML']>=1.5 else 'B' if r['ML']>=1 else 'C') for r in score)
 tt={r['entry_id']:r for r in rows(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
 assert [sum(tt[r['entry_id']]['potential_return']>=k/100 for r in score) for k in (2,3,5,10)]==[432,297,170,67]
 result=json.loads((FROZEN/'UPWARD_STAIRCASE_V4_MAX3_RESULT.json').read_text());assert result['final_equity']==1433740.25 and result['funded_N']==172
 save(OUT/'SOURCE_HASHES.json',checked)
 x={'JST':now(),'score_sha256':sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'),'rank_counts':dict(Counter(r['rank'] for r in score)),'frozen_package_checked_files':len(checked),'models':json.loads((FROZEN/'MODEL_HASHES.json').read_text()),'new_fit':0,'v4_main_saved':{'funded_N':172,'final_equity_exact':1433740.25,'display_rounded':1433740},'no_strictly_later_actual_high_teacher_policy':'Inherited v4 fallback0, unchanged; 54 all58 rows including32 precutoff.'}
 save(OUT/'V4_IDENTITY_FREEZE.json',x);checkpoint('R1_V4_SCORE_RANK_IDENTITY_FREEZE','SCORE_RANK_SOURCE_IDENTITY_FROZEN',x)
if __name__=='__main__':main()
