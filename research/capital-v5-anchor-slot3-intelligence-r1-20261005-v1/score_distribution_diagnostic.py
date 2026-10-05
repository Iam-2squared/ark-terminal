"""Descriptive post-precommit native-slot score/rank diagnostic. No tuning or PnL input."""
from fractions import Fraction
from pathlib import Path
import csv,gzip,hashlib,json,statistics
ROOT=Path('/workspace/scratch/f3d0aa747c89');OUT=ROOT/'r1_work/metrics/supplement';OUT.mkdir(exist_ok=True)
def rows(p):return [json.loads(s) for s in gzip.decompress(Path(p).read_bytes()).splitlines() if s.strip()]
dp=ROOT/'r1_work/runs/D_PRIMARY/DECISIONS.jsonl.gz'
sp=ROOT/'r1_work/score_certification/CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz'
d=rows(dp); scores={r['entry_id']:r for r in rows(sp)};funded=[r for r in d if r.get('quantity',0)>0]
assert len(funded)==len({r['entry_id'] for r in funded})==150
heads=dict(zip(('pP','MOVE_U2','MOVE_U3','MRET'),('rP','r2','r3','rM')))
raw=[];summaries=[]
def frac(v):return {'numerator':v.numerator,'denominator':v.denominator}
for slot in (1,2,3):
 cohort=[r for r in funded if r['funded_slot']==slot]
 for head,rank_name in heads.items():
  values=[];ranks=[];low=0
  for r in cohort:
   sc=scores[r['entry_id']][head];rk=r['intelligence'][rank_name]
   assert rk['numerator']==sc['rank_numerator'] and rk['denominator']==sc['rank_denominator']
   rank=Fraction(rk['numerator'],rk['denominator']);ranks.append(rank);values.append(sc['score']);low+=rk['LOW']
   raw.append({'entry_id':r['entry_id'],'native_funded_slot':slot,'head':head,'score':sc['score'],'rank_numerator':rank.numerator,'rank_denominator':rank.denominator,'LOW':rk['LOW'],'HIGH':rk['HIGH'],'model_sha256':sc['model_sha256']})
  summaries.append({'native_funded_slot':slot,'head':head,'N':len(cohort),'LOW_N':low,'HIGH_N':len(cohort)-low,
     'rank_min':frac(min(ranks)),'rank_mean':frac(sum(ranks,Fraction())/len(ranks)),'rank_median':frac(statistics.median(ranks)),'rank_max':frac(max(ranks)),
     'raw_score_min':min(values),'raw_score_mean_display_only':statistics.mean(values),'raw_score_median':statistics.median(values),'raw_score_max':max(values)})
raw_bytes=b''.join((json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode() for r in raw)
(OUT/'V5_FUNDED150_FOUR_SCORE_NATIVE_SLOT.jsonl.gz').write_bytes(gzip.compress(raw_bytes,mtime=0))
a={'schema':'R1_FIXED_NATIVE_SLOT_FOUR_SCORE_DIAGNOSTIC_V1','status':'DESCRIPTIVE_ONLY','funded_N':150,'score_rank_record_N':600,'complete_all_heads':True,'source_decisions_sha256':hashlib.sha256(dp.read_bytes()).hexdigest(),'source_scores_sha256':hashlib.sha256(sp.read_bytes()).hexdigest(),'membership':'V5 funded identities proven equal to D/DR; grouped by original native funded slot','summaries':summaries,'current_policy_retuned':False,'new_fits':0,'market_replays':0,'PnL_join':0,'raw_score_summary_display_only':True,'rank_statistics':'EXACT_FRACTION; threshold unchanged'}
(OUT/'V5_FUNDED150_FOUR_SCORE_NATIVE_SLOT_SUMMARY.json').write_text(json.dumps(a,indent=2)+'\n')
with (OUT/'V5_FUNDED150_FOUR_SCORE_NATIVE_SLOT.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(raw[0]));w.writeheader();w.writerows(raw)
print(json.dumps({'funded_N':150,'records':len(raw),'slots':{s:sum(r['funded_slot']==s for r in funded) for s in (1,2,3)},'PnL_join':0}))
