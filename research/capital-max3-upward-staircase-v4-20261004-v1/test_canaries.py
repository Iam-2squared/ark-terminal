"""Future-blind canaries. Zero extra fits; no second Development replay."""
from common import *
from copy import deepcopy
from collections import defaultdict
from decimal import Decimal as D
import math,inspect
import numpy as np
from preprocessing import predict_saved
from staircase import materialize,pava,candidate_order
from core_features import NUMERIC,CATEGORICAL,project
from train_h2 import teacher_index
from replay import day_replay
from execution import eod_source
def main():
 result=[]
 def check(name,ok,detail=None):result.append({'name':name,'status':'PASS' if bool(ok) else 'FAIL','details':detail})
 runtime=rows(SRC/'capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz');stream=rows(PRIVATE/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz');days=sorted({r['session'] for r in runtime});book=source_books();index=teacher_index(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')
 ok=True
 for block,start in enumerate(range(20,58,5),1):
  model=json.loads((PRIVATE/'models'/f'H2_BLOCK_{block:02d}.json').read_text());train=[r for r in runtime if r['session'] in days[:start] and r['entry_minute']<920];ids=[r['entry_id'] for r in train]
  poison={k:v if k in ids else '{"future_teacher_payload":"POISON"}' for k,v in index.items()}
  labels={k:int(json.loads(poison[k])['potential_return']>=.02) for k in ids}
  finger=hashlib.sha256(json.dumps([{'entry_id':r['entry_id'],'numeric':r['numeric'],'categorical':r['categorical'],'label':labels[r['entry_id']]} for r in train],sort_keys=True,separators=(',',':')).encode()).hexdigest()
  ok=ok and finger==model['training_input_hash']
 check('01_future_High_H2_fit_input_and_prediction_invariant',ok,'All non-training teacher payloads poisoned; identical saved fit fingerprints; no refit.')
 r=stream[0];models=[json.loads((PRIVATE/'models'/f'{h}_BLOCK_{r["block"]:02d}.json').read_text()) for h in ('H2','H3','H5')];baseline=[predict_saved([r],m) for m in models]
 def predict_same(x):return all(np.array_equal(a,predict_saved([x],m)) for a,m in zip(baseline,models))
 for name,field in [('02_future_High_H3_H5_reuse_invariant','future_High'),('03_future_EXIT_all_heads_invariant','future_EXIT'),('04_future_State_all_heads_invariant','future_State_suffix'),('05_future_Path_all_heads_invariant','future_Path_suffix'),('06_future_liquidity_all_heads_invariant','liquidity')]:
  x=deepcopy(r);x[field]={'future':'POISON','value':10**30};check(name,predict_same(x))
 reused=json.loads((PRIVATE/'REUSED_MODEL_HASHES.json').read_text())
 check('07_H5_hash_exact_identity',all(sha(PRIVATE/'models'/k)==v for k,v in reused.items() if k.startswith('H5')) and sha(SRC/'capital_v2_private/CORE_P5_SCORE_STREAM.jsonl.gz')=='a34f2c4a090a589d4e80858b65f01f3dc95a7849a57aece7e815213d20429731')
 check('08_H3_hash_exact_identity',all(sha(PRIVATE/'models'/k)==v for k,v in reused.items() if k.startswith('H3')))
 check('09_CORE_feature_manifest_exact_identity',sha(OUT/'CORE_FEATURE_MANIFEST.json')=='3aa3abd322e239d27776dfde896d93e38c4e84602ddbf0f9d6a6451865ba55f2' and all(m['preprocessing']['numeric_fields']==NUMERIC and m['preprocessing']['categorical_fields']==CATEGORICAL for m in models))
 baseline_score=materialize(r)
 for name,fields in [('10_HF1_HL0_field_change_decision_invariant',('HF1','HL0','p_floor1','p_loss0','LF1','LSAFE')),('11_Movement_field_change_decision_invariant',tuple('movement/M'+str(k) for k in range(1,17)))]:
  x=deepcopy(r)
  for field in fields:x[field]={'poison':10**30};x['numeric'][field]=10**30
  check(name,materialize(x)==baseline_score and predict_same(x))
 x=deepcopy(r);x['liquidity']={'eligible':False,'capacity':'0','reason':'LIQUIDITY_UNKNOWN'}
 check('12_Liquidity_status_admission_invariant',materialize(x)==baseline_score)
 admitted=next(v for v in stream if v['admission'] and v['entry_minute']<920 and D(v['raw_reference'])*100<D(250000));b=book[admitted['entry_id']]
 def initialbuy(candidate,market):
  o=day_replay(3,candidate['session'],[candidate],{candidate['entry_id']:market},1000000);return o[1][0]['quantity'],o[1][0]['reason'],o[1][0].get('debit')
 base_buy=initialbuy(admitted,b);x=deepcopy(admitted);x['liquidity']={'eligible':False,'capacity':'0','reason':'EXTREME_ILLIQUIDITY_REJECT'}
 check('13_Liquidity_status_quantity_invariant',base_buy==initialbuy(x,b))
 x=deepcopy(r);x['future_outcome']={'High':10**30,'EXIT':-10**30};check('14_PAVA_outcome_blind',materialize(x)==baseline_score and 'outcome' not in inspect.signature(pava).parameters)
 check('15_PAVA_monotonic',all(v['m2']>=v['m3']>=v['m5'] for v in stream))
 check('16_ML_deterministic',all(materialize(v)==materialize(deepcopy(v)) and materialize(v)['ML']==v['ML'] for v in stream))
 fail=deepcopy(admitted);fail.update(p2=1e-8,p3=1e-8,p5=1e-8);fail.update(materialize(fail));check('17_ML_below1_funded0',fail['rank']=='C' and initialbuy(fail,b)[0]==0)
 synthetic=day_replay(3,admitted['session'],[admitted],{admitted['entry_id']:b},1000000)
 check('18_no_forced_backfill',len(synthetic[1])==1 and max(v['concurrent'] for v in synthetic[3])<=1)
 ds=rows(PRIVATE/f'{PROFILE}_DECISIONS.jsonl.gz');ts=rows(PRIVATE/f'{PROFILE}_TRADES.jsonl.gz');cs=rows(PRIVATE/f'{PROFILE}_CURVE.jsonl.gz');it=rows(PRIVATE/f'{PROFILE}_INTENTS.jsonl.gz');pr=json.loads((PRIVATE/f'{PROFILE}_RESULT.json').read_text())
 check('19_max_concurrent3',max(f['concurrent'] for f in cs)<=3)
 check('20_100_share_lot',all(d['quantity']%100==0 for d in ds))
 check('21_cash_nonnegative',all(D(f['cash'])>=0 for f in cs))
 check('22_LONG_only',all(i['side']=='SELL' for i in it) and all(t['quantity']>0 for t in ts))
 check('23_short_margin_leverage0',all(v is False for v in SAFETY.values()))
 check('24_Entry_ge1520_funded0',all(d['quantity']==0 for d in ds if d['minute']>=920))
 empty=deepcopy(b);empty['market']=[];empty['frozen_exit']={'sell_status':'UNEXECUTED'};no=day_replay(3,admitted['session'],[admitted],{admitted['entry_id']:empty},1000000)
 check('25_MTM_mark_is_not_fill',not no[2] and no[0]['ending_cash'] is None and eod_source([],admitted['session']) is None)
 check('26_no_trade_MTM_cash_release0',not no[2] and len({f['cash'] for f in no[3] if f['minute']>=admitted['entry_minute']})==1)
 buy=defaultdict(D);sell=defaultdict(D)
 for d in ds:
  if d['reason']=='FUNDED':buy[d['session'],d['minute']]+=D(d['debit'])
 for t in ts:sell[t['session'],t['release_minute']]+=D(t['credit'])
 starts={d['session']:D(d['starting_cash']) for d in pr['daily_series']};past={};ledger=True
 for f in cs:
  before=past.get(f['session'],starts[f['session']]);ledger=ledger and D(f['cash'])==before-buy[f['session'],f['minute']]+sell[f['session'],f['minute']];past[f['session']]=D(f['cash'])
 check('27_cash_release_valid_EXIT_EOD_only',ledger and all(t['lineage'] and t['exit_kind'] in ('FROZEN_EXIT_V3','EOD_REGULAR','EOD_EXACT_1530_AUCTION') for t in ts))
 check('28_duplicate_sell0',len(ts)==len({t['entry_id'] for t in ts}))
 sources=json.loads((OUT/'SOURCE_HASHES.json').read_text());check('29_Frozen_Entry_EXIT_changes0',all(sha(SRC/k)==v for k,v in sources.items()))
 check('30_deterministic_rerun_identity',synthetic==day_replay(3,admitted['session'],[admitted],{admitted['entry_id']:b},1000000) and all(np.array_equal(predict_saved([r],m),predict_saved([deepcopy(r)],m)) for m in models),'Repeat synthetic event ledger and score materialization; full primary Development rerun0. Independent full ledger identity checked separately.')
 # Actual State/Path suffix mutation at the Frozen Entry cut.
 entries=rows(SRC/'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz');e=entries[0];trace=rows(SRC/'work_inputs/exit_v2/FULL_TRACE/2025-05-30_17580.jsonl.gz');pre=project(e,trace)
 for part in ('state','path'):
  x=deepcopy(trace)
  for z in x:
   if z['bar_end_minute']>e['fill_minute']:z[part]={'future':'POISON'};z['path_events']=[{'future':'POISON'}]
  check('actual_future_'+part+'_suffix_feature_invariant',pre==project(e,x))
 check('water_fill_initially_funded_only',all(d['first_pass_quantity']>=100 or d['water_fill_lots']==0 for d in ds if 'first_pass_quantity' in d))
 check('funded_ML_ge1_and_no_C',all(d['ML']>=1 and d['rank']!='C' for d in ds if d['reason']=='FUNDED'))
 check('H2_exact8_H3_H5_fit0',len(list((PRIVATE/'models').glob('H2_BLOCK_*.json')))==8 and len(list((PRIVATE/'models').glob('*.json')))==24)
 check('independent_PAVA_implementations_no_primary_import',not any(line.startswith(('from common','from staircase','from replay','from allocation','from preprocessing')) for line in (CODE/'independent_audit.py').read_text().splitlines()))
 failed=sum(r['status']=='FAIL' for r in result);save(OUT/'CANARY_RESULTS.json',{'JST':now(),'status':'PASS' if failed==0 else 'FAIL','canary_N':len(result),'failed_N':failed,'results':result,'extra_fits':0,'extra_full_primary_replays':0,'synthetic_canary_events_only':True,'Safety':SAFETY})
 print(json.dumps({'canary_N':len(result),'failed_N':failed}),flush=True);assert failed==0,'CANARY_FAIL'
if __name__=='__main__':main()
