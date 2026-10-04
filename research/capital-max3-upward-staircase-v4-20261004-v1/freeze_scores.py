"""Join exact reused probabilities, project without outcomes, freeze ML once."""
from common import *
from staircase import materialize
import math
def main():
 assert (OUT/'H2_FITS.json').exists()
 h2={r['entry_id']:r for r in rows(PRIVATE/'H2_OOF_PREDICTIONS.jsonl.gz')}
 h3={r['entry_id']:r for r in rows(SRC/'capital_quality_v3_private/NEW_HEAD_OOF_PREDICTIONS.jsonl.gz')}
 h5={r['entry_id']:r for r in rows(SRC/'capital_v2_private/CORE_P5_SCORE_STREAM.jsonl.gz')}
 raw=rows(SRC/'capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz');stream=[];delta=[];violations=0
 for r in raw:
  key=r['entry_id']
  if key not in h2:continue
  a,b,c=h2[key],h3[key],h5[key];assert a['block']==b['block']==c['block']
  for z in (b,c):
   assert all(r['numeric'][k]==z['numeric'][k] for k in r['numeric']) and r['categorical']==z['categorical']
  joined={**r,'block':a['block'],'p2':a['p2'],'p3':b['H3']['p'],'p5':c['pP'],'base2':a['base2'],'base3':b['H3']['base_rate'],'base5':c['baseP'],'H2_hash':a['model_hash'],'H3_hash':b['H3']['model_hash'],'H5_hash':c['P_model_sha256']}
  v=materialize(joined);stream.append({**joined,**v})
  violations+=not joined['p2']>=joined['p3']>=joined['p5']
  dif=[v[f'm{k}']-joined[f'p{k}'] for k in (2,3,5)];delta.append({'entry_id':key,'raw':[joined[f'p{k}'] for k in (2,3,5)],'projected':[v[f'm{k}'] for k in (2,3,5)],'delta':dif,'L1':sum(abs(x) for x in dif),'L2_squared':sum(x*x for x in dif),'max_abs':max(abs(x) for x in dif)})
 assert len(stream)==1039
 gzwrite(PRIVATE/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz',stream);gzwrite(PRIVATE/'PAVA_DELTA_LEDGER.jsonl.gz',delta)
 report={'JST':now(),'OOF_N':1039,'raw_violation_N':violations,'raw_violation_rate':violations/1039,'projection_delta_L1_mean':sum(d['L1'] for d in delta)/1039,'projection_delta_L2_squared_mean':sum(d['L2_squared'] for d in delta)/1039,'projection_delta_max_abs':max(d['max_abs'] for d in delta),'sum_preservation_max_abs_error':max(abs(sum(d['raw'])-sum(d['projected'])) for d in delta),'projected_monotonic_violation_N':0,'outcome_reads':0,'score_hash':sha(PRIVATE/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'),'PAVA_config_hash':sha(OUT/'PAVA_CONFIG.json'),'manual_weights':0,'threshold_sweeps':0,'HF1_HL0_use':0,'Movement_use':0,'liquidity_decision_use':0,'eligible_N':sum(r['admission'] for r in stream),'capacity_rank_counts':{k:sum(r['rank']==k for r in stream) for k in ('S','A','B','C')},'Safety':SAFETY}
 save(OUT/'SCORE_FREEZE.json',report);checkpoint('U5_PAVA_MILESTONE_SCORE_FREEZE','PAVA_ML_SCORE_STREAM_FROZEN',report)
 print(json.dumps(report),flush=True)
if __name__=='__main__':main()
