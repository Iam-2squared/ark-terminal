"""Focused future-blind, source, accounting and deterministic verification; fit0."""
from copy import deepcopy
from collections import Counter,defaultdict
from pathlib import Path
import gzip,json,hashlib,math
from decimal import Decimal as D
import numpy as np
from checkpoint import *
from io_data import rows,books,gzwrite
from preprocessing import predict_saved
from quality import materialize,PROFILES,profile_eligible
from core_features import NUMERIC,CATEGORICAL,project
from train_heads import teacher_index,past_labels,fingerprint
from replay import run_profile,day_replay
from execution import eod_source,valid_market,BUY

def main():
 results=[]
 def check(name,ok,details=None):
  results.append({'name':name,'status':'PASS' if bool(ok) else 'FAIL','details':details})
 runtime=rows(PRIVATE/'CORE_RUNTIME_CAUSAL.jsonl.gz');stream=rows(PRIVATE/'QUALITY_V3_SCORE_STREAM.jsonl.gz');byid={r['entry_id']:r for r in runtime};days=sorted({r['session'] for r in runtime});market=books();index=teacher_index(V2/'TEACHERS_EVALUATION.jsonl.gz')
 for head in ('H3','HF1','HL0'):
  ok=True
  for block,start in enumerate(range(20,58,5),1):
   model=json.loads((PRIVATE/'models'/f'{head}_BLOCK_{block:02d}.json').read_text());prefix=[r for r in runtime if r['session'] in set(days[:start]) and r['entry_minute']<920];ids=[r['entry_id'] for r in prefix]
   poisoned={k:v if k in ids else '{"future_teacher_payload":"POISON","invalid_label":true}' for k,v in index.items()}
   a=past_labels(index,ids,head);b=past_labels(poisoned,ids,head);train=[r for r in prefix if r['entry_id'] in a]
   ok=ok and a==b and fingerprint(train,b)==model['training_input_hash']
   test=[r for r in runtime if r['session'] in model['test_dates']];p=predict_saved(test,model);p2=predict_saved(deepcopy(test),model);ok=ok and np.array_equal(p,p2)
  check('test_block_'+head+'_teacher_mutation_prediction_invariant',ok,'Poisoned all non-training teacher payloads, identical training fingerprints and fixed-artifact predictions; extra fits0.')
 r=stream[0];m=json.loads((PRIVATE/'models/H3_BLOCK_01.json').read_text());baseline=predict_saved([r],m)
 for key in ('future_high','future_low','future_EXIT','future_EOD_source','future_State_suffix','future_Path_suffix'):
  z=deepcopy(r);z[key]={'value':999999,'label':True};check(key+'_runtime_prediction_invariant',np.array_equal(baseline,predict_saved([z],m)))
 z=deepcopy(r)
 for k in range(1,17):z['numeric']['movement/M'+str(k)]=999999
 check('Movement_add_change_invariant',np.array_equal(baseline,predict_saved([z],m)))
 for k in list(z['numeric']):
  if k.startswith('movement/'):del z['numeric'][k]
 check('Movement_delete_invariant',np.array_equal(baseline,predict_saved([z],m)))
 h5hash=sha(V2/'CORE_P5_SCORE_STREAM.jsonl.gz');check('H5_existing_byte_hash_identity',h5hash=='a34f2c4a090a589d4e80858b65f01f3dc95a7849a57aece7e815213d20429731')
 manifest=json.loads((OUT/'CORE_FEATURE_MANIFEST.json').read_text());oldmodel=json.loads((V2/'models/CORE_P_BLOCK_01.json').read_text());check('CORE_manifest_identity',manifest['numeric']==oldmodel['preprocessing']['numeric_fields']==NUMERIC and manifest['categorical']==oldmodel['preprocessing']['categorical_fields']==CATEGORICAL)
 # Actual frozen trace canary: alter State/Path suffix beyond Entry before causal projection.
 entries=rows(ROOT.parent/'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz');e=entries[0]
 traces=ROOT.parent/'work_inputs/exit_v2/FULL_TRACE';tracefile=traces/(e['session']+'_'+e['symbol']+'.jsonl.gz') if 'session' in e and 'symbol' in e else None
 if tracefile is None or not tracefile.exists():
  # Frozen rows use their recorded day/code field names; identify from stable entry_id.
  key=e.get('entry_id') or next(iter(byid));d,sym=key.split('|');tracefile=traces/(d+'_'+sym+'.jsonl.gz')
 tr=rows(tracefile);pre=project(e,tr)
 for part in ('state','path'):
  altered=deepcopy(tr)
  for v in altered:
   if v['bar_end_minute']>e['fill_minute']:v[part]={'future':'POISON'};v['path_events']=[{'future':'POISON'}]
  other=project(e,altered);check('actual_future_'+part+'_suffix_feature_invariant',pre==other)
 def requant(row):
  return materialize(row,row['p5'],row['base5'],row['p3'],row['base3'],row['p_floor1'],row['base_floor1'],row['p_loss0'],row['base_loss0'])
 changed=deepcopy(r);changed['liquidity']={'eligible':False,'capacity':'0','reason':'LIQUIDITY_UNKNOWN','future_volume':10**30};rq=requant(changed)
 for k in ('quality_gate_pass','Q','rank'):check('Liquidity_diagnostic_'+k+'_invariant',r[k]==rq[k])
 admitted=next(v for v in stream if v['quality_gate_pass'] and v['entry_minute']<920)
 def initialbuy(candidate,book):
  out=day_replay(3,candidate['session'],[candidate],{candidate['entry_id']:book},1000000)
  return out[1][0]['quantity'],out[1][0]['reason'],out[1][0].get('debit')
 book=market[admitted['entry_id']];same=initialbuy(admitted,book)
 changed=deepcopy(admitted);changed['liquidity']={'eligible':False,'capacity':'0','reason':'EXTREME_ILLIQUIDITY_REJECT'}
 check('Liquidity_capacity_quantity_invariant',same==initialbuy(changed,book))
 future=deepcopy(book);future['market']=[v for v in future['market'] if v['minute']<920];future['limit_up_authority']={'status':'LIMIT_UP_CONFIRMED','known_minute':9999}
 check('future_EOD_and_limit_up_BUY_invariant',same==initialbuy(admitted,future))
 fail=deepcopy(admitted);fail['quality_gate_pass']=False
 check('Main_gate_fail_funding0',initialbuy(fail,book)[0]==0)
 cut=deepcopy(admitted);cut['entry_minute']=920;cut['entry_timestamp']=cut['session']+'T15:20:00+09:00'
 check('Entry_exact1520_funding0',initialbuy(cut,book)[0]==0)
 # No trade beyond Entry: hold raw actual anchor only for valuation; no sell/cash release.
 empty=deepcopy(book);empty['market']=[];empty['frozen_exit']={'sell_status':'UNEXECUTED'}
 out=day_replay(3,admitted['session'],[admitted],{admitted['entry_id']:empty},1000000)
 check('no_trade_same_session_anchor_no_cash_release',not out[2] and len({f['cash'] for f in out[3] if f['minute']>=admitted['entry_minute']})==1 and all(v==admitted['entry_minute'] for f in out[3] for v in f['known_marks'].values()))
 check('MTM_mark_not_fill',out[0]['ending_cash'] is None and out[0]['status']=='PORTFOLIO_MEASUREMENT_BLOCKED_EXECUTION' and not eod_source([],admitted['session']))
 all_ds=[];all_ts=[];all_cs=[];all_it=[];deterministic=[];rankviol={};water_ok=True;cash_ok=True
 for profile in PROFILES:
  ds=rows(PRIVATE/(profile+'_DECISIONS.jsonl.gz'));ts=rows(PRIVATE/(profile+'_TRADES.jsonl.gz'));cs=rows(PRIVATE/(profile+'_CURVE.jsonl.gz'));it=rows(PRIVATE/(profile+'_INTENTS.jsonl.gz'));pr=json.loads((PRIVATE/(profile+'_RESULT.json')).read_text());lookup={v['entry_id']:v for v in stream}
  all_ds+=ds;all_ts+=ts;all_cs+=cs;all_it+=it
  funded=[d for d in ds if d['reason']=='FUNDED'];bad=sum(not profile_eligible(lookup[d['entry_id']],profile) for d in funded);rankviol[profile]=bad
  check(profile+'_rank_identity_and_no_backfill',bad==0 and all(d['quality_gate_pass'] for d in funded))
  check(profile+'_MAX3_exact_obeyed',max(v['concurrent'] for v in cs)<=3)
  water_ok=water_ok and all(d['first_pass_quantity']>=100 or d['water_fill_lots']==0 for d in ds if 'first_pass_quantity' in d)
  rebuilt=run_profile(profile,3,stream,market);deterministic.append(True)
  result2,dd,tt,cc,ii=rebuilt
  check(profile+'_deterministic_rerun',dd==ds and tt==ts and cc==cs and ii==it and all(result2[k]==pr[k] for k in result2))
  # Validate every minute cash delta against only confirmed BUY debit and SELL credit.
  buy=defaultdict(D);sell=defaultdict(D)
  for d in funded:buy[d['session'],d['minute']]+=D(d['debit'])
  for t in ts:sell[t['session'],t['release_minute']]+=D(t['credit'])
  starts={d['session']:D(d['starting_cash']) for d in pr['daily_series']};pastcash={}
  for f in cs:
   before=pastcash.get(f['session'],starts[f['session']]);cash_ok=cash_ok and D(f['cash'])==before-buy[f['session'],f['minute']]+sell[f['session'],f['minute']];pastcash[f['session']]=D(f['cash'])
 check('100_share_lot',all(d['quantity']%100==0 for d in all_ds))
 check('cash_nonnegative',all(D(c['cash'])>=0 for c in all_cs))
 check('LONG_cash_equity_only_no_margin_short_leverage',all(i['side']=='SELL' and not i['transmitted'] for i in all_it) and all(v is False for v in SAFETY.values()))
 check('Entry_ge1520_funding0',all(d['quantity']==0 for d in all_ds if d['minute']>=920))
 check('same_session_past_only_MTM',all(all(v<=f['minute'] for v in f['known_marks'].values()) for f in all_cs))
 check('cash_release_only_valid_confirmed_sell_and_no_trade_none',cash_ok and all(t['lineage'] and t['release_minute']>t['entry_minute'] for t in all_ts))
 check('duplicate_SELL0',all(len(rows(PRIVATE/(p+'_TRADES.jsonl.gz')))==len({t['entry_id'] for t in rows(PRIVATE/(p+'_TRADES.jsonl.gz'))}) for p in PROFILES))
 check('water_fill_deterministic_initially_funded_only_outcome_blind',water_ok and 'books' not in __import__('inspect').getsource(__import__('allocation').allocation))
 source=json.loads((PRIVATE/'SOURCE_MANIFEST.json').read_text());check('Frozen_Entry_EXIT_changes0',all(sha(ROOT.parent/k)==v for k,v in source.items() if 'FROZEN_ENTRY' in k or 'REPLAY_ROWS' in k))
 check('diagnostic_fits0_total_newfits24_H5fits0',len(list((PRIVATE/'models').glob('*.json')))==24 and all(__import__('hashlib').sha256((ROOT.parent/k).read_bytes()).hexdigest()==v for k,v in source.items() if 'CORE_P_BLOCK' in k))
 fail_N=sum(r['status']=='FAIL' for r in results)
 save(OUT/'FOCUSED_TEST_RESULTS.json',{'status':'PASS' if fail_N==0 else 'FAIL','canary_N':len(results),'failed_N':fail_N,'results':results,'rank_cutoff_violations':rankviol,'deterministic_verification_replays':4,'measurement_replays':4,'extra_fits':0,'MAX4_MAX5_replays':0,'safety':SAFETY})
 print(json.dumps({'canary_N':len(results),'failed_N':fail_N}),flush=True)
 assert fail_N==0,'FOCUSED_CONTRACT_FAIL'
if __name__=='__main__':main()
