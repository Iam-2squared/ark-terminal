"""Training-only frozen-model inference and exact-current-minute arrivals.

Fixed half-hour buckets are display summaries. Runtime uses the remaining curve
at its actual minute (inclusive of that minute, exclusive of15:20), calculated
only from the current block's training sessions. Empty days count as zero.
"""
from common import *
from preprocessing import predict_saved
from staircase import materialize
import numpy as np
from collections import Counter
BUCKETS=[(540,570),(570,600),(600,630),(630,660),(660,690),(750,780),(780,810),(810,840),(840,870),(870,900),(900,920)]
def build(runtime,split,models):
 tables={};pred=[]
 for b in split['blocks']:
  block=b['block'];training=[r for r in runtime if r['session'] in b['train'] and r['entry_minute']<920]
  heads=[models[f'H{k}_BLOCK_{block:02d}.json'] for k in (2,3,5)]
  assert all([r['entry_id'] for r in training]==h['train_entry_ids'] for h in heads)
  assert max(b['train'])<min(b['test']) and not set(b['train'])&set(b['test'])
  probabilities=[predict_saved(training,h) for h in heads];scored=[]
  for i,r in enumerate(training):
   pp={f'p{k}':float(probabilities[j][i]) for j,k in enumerate((2,3,5))}|{f'base{k}':heads[j]['base_rate'] for j,k in enumerate((2,3,5))}
   sc={'block':block,**{k:r[k] for k in ('entry_id','session','entry_minute','symbol')},**pp,**materialize(pp)}
   scored.append(sc);pred.append(sc)
  B=sorted(r['ML'] for r in scored if r['rank']=='B');assert B
  table={'block':block,'training_sessions':b['train'],'training_session_N':len(b['train']),'test_sessions':b['test'],'training_candidate_N':len(scored),'training_B_N':len(B),'B_median':float(np.quantile(B,.5,method='linear')),'B_p75':float(np.quantile(B,.75,method='linear')),'quantile_convention':'linear type7','model_hashes':{f'H{k}':sha(FROZEN/'models'/f'H{k}_BLOCK_{block:02d}.json') for k in (2,3,5)},'buckets':[],'minute_counts':{},'minute_bucket':{},'training_scored_sha256':hashlib.sha256(json.dumps(scored,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
  for lower,upper in BUCKETS:
   label=f'{lower//60:02d}:{lower%60:02d}-{upper//60:02d}:{upper%60:02d}'
   for minute in range(lower,upper):
    by_day=[(sum(r['session']==day and r['entry_minute']>=minute and r['admission'] for r in scored),sum(r['session']==day and r['entry_minute']>=minute and r['rank'] in ('S','A') for r in scored)) for day in b['train']]
    admission=[z[0] for z in by_day];a=[z[1] for z in by_day];n=len(a)
    table['minute_counts'][str(minute)]=[sum(z>=1 for z in a),sum(z>=2 for z in a),sum(a),sum(admission)]
    table['minute_bucket'][str(minute)]=label
    if minute==lower:
     table['buckets'].append({'bucket':label,'anchor_minute':lower,'remaining_Admission_pass_distribution':dict(Counter(admission)),'remaining_A_or_better_distribution':dict(Counter(a)),'P_remaining_Aplus_ge1':sum(z>=1 for z in a)/n,'P_remaining_Aplus_ge2':sum(z>=2 for z in a)/n,'expected_remaining_Aplus':sum(a)/n,'per_training_session_counts':by_day})
  tables[str(block)]=table
 return tables,pred

def main():
 runtime=rows(SRC/'capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz')
 split=json.loads((SOURCE/'repo/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json').read_text())
 models={p.name:json.loads(p.read_text()) for p in (FROZEN/'models').glob('*.json')}
 tables,pred=build(runtime,split,models)
 gzwrite(PRIVATE/'TRAINING_ONLY_SCORED_ARRIVALS.jsonl.gz',pred)
 with (OUT/'ARRIVAL_TABLE.json').open('x') as f:json.dump(tables,f,sort_keys=True,separators=(',',':'),allow_nan=False);f.write('\n')
 config={'JST':now(),'name':PROFILE,'policy_count':1,'new_fit':0,'rank_changes':0,'Control_replay':0,'open0':'ML>=1 no reserve','open1_SA':'admit','open1_B':{'median_ML_and_probability_lt':.50,'OR_time_ge':'14:00'},'open2_SA':'admit','open2_B':{'quantile':.75,'P_remaining_Aplus_ge1_lt':.35,'expected_remaining_Aplus_lt':.75,'time_ge_1430_quality_only':True},'open3':'reject; no forced exit or replacement','Aplus_definition':'S or A, ML>=1.5','B_quantiles':'training candidates with1<=ML<1.5, before15:20; numpy linear type7','arrival_method':'Apply each block frozen H2/H3/H5/preprocessing/PAVA to its training rows only; counts include zeros for all training sessions. Resubstitution training estimates, not OOF-quality estimates. No fit.','arrival_time':'At exact current minute t<=entry_minute<920; fixed30-minute buckets summarize at their lower anchor. Runtime does not use test-session arrivals.','same_batch_contract':'v4 ordering; sequential slot admission occupancy=open positions + prior same-batch slot admissions. All admitted candidates use unchanged simultaneous v4 proportional allocation/water-fill. A cash/lot failure does not trigger backfill. Pending admissions vanish at batch end. Funded slot labels count actual successful positions.','allocation':'v4 byte-identical allocation.py and execution.py; caps45/35/25%, utilization68/56/44%, breadth5.5pp, max92%, ML proportional,100-share, no later topup','oracle_isolated':True,'threshold_changes_after_results':0,'grid_search':0,'training_only':True,'fixed_score_sha256':sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'),'arrival_table_sha256':sha(OUT/'ARRIVAL_TABLE.json'),'training_predictions_sha256':sha(PRIVATE/'TRAINING_ONLY_SCORED_ARRIVALS.jsonl.gz'),'runtime_code_hashes':{p.name:sha(p) for p in CODE.glob('*.py')},'Safety':SAFETY}
 save(OUT/'POLICY_PRECOMMIT.json',config)
 checkpoint('V3_ARRIVAL_TABLE_AND_SLOT_POLICY_PRECOMMIT','ONE_SHOT_POLICY_AND_TRAINING_TABLE_FROZEN',{'block_N':len(tables),'training_scored_row_N':len(pred),'tables_hash':config['arrival_table_sha256'],'precommit_hash':sha(OUT/'POLICY_PRECOMMIT.json')})
 print(json.dumps({'blocks':len(tables),'training_scored_rows':len(pred),'table_bytes':(OUT/'ARRIVAL_TABLE.json').stat().st_size}))
if __name__=='__main__':main()
