"""Separate evaluation census. No model, ranking or allocation uses this module."""
from checkpoint import *
from io_data import rows,gzwrite
from core_features import NUMERIC,CATEGORICAL
rr=rows(V2/'RUNTIME_CAUSAL.jsonl.gz');days=sorted({r['session'] for r in rr});assert len(days)==58
core=[]
for r in rr:
 core.append({**{k:r[k] for k in ('entry_id','session','symbol','entry_minute','entry_timestamp','raw_reference','liquidity','provenance')},'numeric':{k:r['numeric'][k] for k in NUMERIC},'categorical':{k:r['categorical'][k] for k in CATEGORICAL}})
gzwrite(PRIVATE/'CORE_RUNTIME_CAUSAL.jsonl.gz',core)
tt={r['entry_id']:r for r in rows(V2/'TEACHERS_EVALUATION.jsonl.gz')}
oof=[r for r in rr if r['session'] in days[20:]];t=[tt[r['entry_id']] for r in oof];resolved=[r for r in t if r['realized_net_return'] is not None]
counts={'candidate_N':len(oof),'U3_N':sum(r['label_bigwinner3']==1 for r in t),'U5_N':sum(r['label_bigwinner5']==1 for r in t),'U10_N':sum(r['label_bigwinner10']==1 for r in t),'Medium_N':sum(r['label_bigwinner3']==1 and r['label_bigwinner5']==0 for r in t),'realized_resolved_N':len(resolved),'realized_missing_N':len(t)-len(resolved),'PF1_N':sum(r['realized_net_return']>=.01 for r in resolved),'loss0_N':sum(r['realized_net_return']<=0 for r in resolved),'tail1_N':sum(r['realized_net_return']<=-.01 for r in resolved),'tail3_N':sum(r['realized_net_return']<=-.03 for r in resolved)}
assert {k:counts[k] for k in ('candidate_N','U3_N','U5_N','U10_N','Medium_N','realized_resolved_N','realized_missing_N','PF1_N','loss0_N','tail1_N')}==dict(candidate_N=1039,U3_N=297,U5_N=170,U10_N=67,Medium_N=127,realized_resolved_N=1016,realized_missing_N=23,PF1_N=271,loss0_N=554,tail1_N=294)
control=rows(ROOT.parent/'capital_liquidity_off_private/LIQUIDITY_OFF_MAX3_TRADES.jsonl.gz');assert len(control)==167
cs={'funded_N':len(control),'PF1_N':sum(r['net_return']>=.01 for r in control),'loss0_N':sum(r['net_return']<=0 for r in control),'tail1_N':sum(r['net_return']<=-.01 for r in control)}
assert cs==dict(funded_N=167,PF1_N=54,loss0_N=89,tail1_N=58)
save(OUT/'TEACHER_CENSUS_AND_CONTRACT.json',{'jst':now(),'OOF_counts':counts,'control_selection_counts':cs,'training_prefilter':'same CORE pre15:20 only, labels known in completed past sessions only','runtime_future_outcome_visible':False,'HF1_HL0_missing_zero_imputation':0,'runtime_missing_outcome_filter':0,'numeric_N':len(NUMERIC),'categorical_N':len(CATEGORICAL),'CORE_runtime_sha256':sha(PRIVATE/'CORE_RUNTIME_CAUSAL.jsonl.gz'),'H5_byte_hash':sha(V2/'CORE_P5_SCORE_STREAM.jsonl.gz'),'Movement_retained_in_CORE':False,'source_expansion':0,'exposure':EXPOSURE,'safety':SAFETY})
save(OUT/'EXPOSURE_LEDGER.json',{'jst':now(),'allowed':EXPOSURE,'artifacts_read':json.loads((PRIVATE/'SOURCE_MANIFEST.json').read_text()),'provider_requests':0,'Protected_Holdout_Fresh_Validation_OOS_Prospective_opened':0,'control_replays':0,'result_based_retune':0,'future_teacher_scope':'training completed sessions / evaluation only; never runtime features','safety':SAFETY})
checkpoint('Q2_TEACHER_CENSUS_AND_CONTRACT','TEACHER_CENSUS_VERIFIED_NO_IMPUTATION',counts,next_direction='Pin new Head trainer, score arithmetic and all four replay/audit code before fits.')
