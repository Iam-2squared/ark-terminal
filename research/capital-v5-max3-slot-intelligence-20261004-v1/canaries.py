"""Pre-replay causal boundaries and frozen identity tests; no policy search."""
from common import *
from slot_policy import gate
from replay import day_replay
from arrival import build
from core_features import project
from execution import eod_source,valid_market,eod_intent,last_actual_mark
from allocation import allocation
from copy import deepcopy
from decimal import Decimal as D
def main():
 checks=[]
 def check(name,ok,detail=None):
  checks.append({'name':name,'PASS':bool(ok),'detail':detail});assert ok,name
 freeze=json.loads((OUT/'SOURCE_HASHES.json').read_text())
 check('01_H2_H3_H5_hash_identity',all(sha(SOURCE/k)==h for k,h in freeze.items() if '/models/' in k))
 score=rows(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')
 check('02_ML_rank_identity',sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')=='c446633dec923e3a80a534b19325ccff49f769a2ff1d29c7af1202202de614d4')
 check('03_new_fit0',not any('fit(' in p.read_text() for p in CODE.glob('*.py') if p.name not in ('canaries.py','preprocessing.py','core_features.py')))
 tables=json.loads((OUT/'ARRIVAL_TABLE.json').read_text());runtime=rows(SRC/'capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz')
 split=json.loads((SOURCE/'repo/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json').read_text());models={p.name:json.loads(p.read_text()) for p in (FROZEN/'models').glob('*.json')}
 check('04_training_only_arrival_tables',all(max(z['training_sessions'])<min(z['test_sessions']) and not set(z['training_sessions'])&set(z['test_sessions']) for z in tables.values()))
 altered=deepcopy(runtime)
 for r in altered:
  if r['session'] in split['blocks'][0]['test']:r['entry_minute']=919;r['numeric']={k:123456. for k in r['numeric']};r['categorical']={k:'FUTURE_MUTATED' for k in r['categorical']}
 rebuilt,_=build(altered,{'blocks':split['blocks'][:1]},models)
 check('05_test_future_arrival_mutation',json.loads(json.dumps(rebuilt['1']))==tables['1'])
 r=next(z for z in score if z['rank']=='B');t=r['entry_minute'];table=tables[str(r['block'])]
 baseline=gate(r,1,t,table);mutated=dict(r,future_U5=1,future_U10=1,future_High=999999.,future_realized=1e6)
 check('06_future_teacher_High_mutation',gate(mutated,1,t,table)==baseline)
 books={r['entry_id']:r for r in rows(SRC/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};day=min(z['session'] for z in score);candidates=[z for z in score if z['session']==day]
 prefix=600
 ordinary=day_replay(3,day,candidates,books,D(1000000),tables=tables)
 mutated_books=deepcopy(books)
 for b in mutated_books.values():
  if b['session']!=day:continue
  x=b['frozen_exit'];available=x.get('sell_source_assumed_available_at')
  if available and x['sell_status']=='FILLED':
   from datetime import datetime,timedelta
   dt=datetime.fromisoformat(available);m=dt.hour*60+dt.minute
   if prefix<m<919:x['sell_source_assumed_available_at']=(dt+timedelta(minutes=1)).isoformat()
 changed=day_replay(3,day,candidates,mutated_books,D(1000000),tables=tables)
 check('07_future_EXIT_mutation_current_decision',[d for d in ordinary[1] if d['minute']<=prefix]==[d for d in changed[1] if d['minute']<=prefix])
 records=rows(SRC/'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz');tr=rows(SRC/'work_inputs/exit_v2/FULL_TRACE/2025-05-30_17580.jsonl.gz')
 entry=next(z for z in records if z.get('session')=='2025-05-30' and z.get('symbol')=='17580' and z.get('entry_status')=='FIRST_ENTRY')
 before=project(entry,tr);suffix=deepcopy(tr)
 for z in suffix:
  if z['bar_end_minute']>entry['fill_minute']:z['state']={'FUTURE':'MUTATED'};z['path']={'FUTURE':'MUTATED'};z['path_events']=[{'FUTURE':'MUTATED'}]
 check('08_future_State_Path_suffix_mutation',project(entry,suffix)==before)
 cfg=json.loads((OUT/'POLICY_PRECOMMIT.json').read_text())
 check('09_precommit_identity',cfg['open1_B']['median_ML_and_probability_lt']==.50 and cfg['open2_B']['P_remaining_Aplus_ge1_lt']==.35 and cfg['open2_B']['expected_remaining_Aplus_lt']==.75 and cfg['open2_B']['quantile']==.75)
 check('10_B_quantiles_training_only',all(z['training_B_N']>0 and z['B_median']<=z['B_p75'] for z in tables.values()))
 check('11_remaining_statistics_training_only',all(all(0<=v[1]<=v[0]<=z['training_session_N'] and v[2]>=v[0] for v in z['minute_counts'].values()) for z in tables.values()))
 candidate_mutation=[dict(z,U5=1,U10=1,High=1e9,realized=12345) for z in candidates]
 after=day_replay(3,day,candidate_mutation,books,D(1000000),tables=tables)
 check('12_same_batch_outcomes_unused',after[1]==ordinary[1])
 check('13_no_forced_backfill',"if q<100:" in (CODE/'replay.py').read_text() and 'picked.append((r,d))' in (CODE/'replay.py').read_text())
 check('14_MAX_le3',max(x['concurrent'] for x in ordinary[3])<=3)
 check('15_100_share_lot',all(z['quantity']%100==0 for z in ordinary[1]))
 check('16_cash_nonnegative',all(D(z['cash'])>=0 for z in ordinary[3]))
 check('17_LONG_cash_only_no_leverage',not any('SHORT' in z.get('side','LONG') for z in ordinary[4]) and all(not v for v in SAFETY.values()))
 check('18_Entry_ge1520_no_funding',all(z['quantity']==0 for z in ordinary[1] if z['minute']>=920))
 altered_liq=[dict(z,liquidity={'capacity':'0','eligible':False,'reason':'MUTATED'}) for z in candidates]
 check('19_Liquidity_decision_use0',day_replay(3,day,altered_liq,books,D(1000000),tables=tables)[1]==ordinary[1])
 check('20_MTM_mark_not_fill',last_actual_mark([],570,600,'123',day)==(D(123),570))
 check('21_no_trade_no_MTM_cash_release',eod_source([],day) is None)
 check('22_valid_EXIT_EOD_only_release',not valid_market({'Vo':0,'Va':0}) and eod_intent({'quantity':100,'side':'LONG','margin':False,'intent_issued':True}) is None)
 check('23_duplicate_sell0',len({z['entry_id'] for z in ordinary[2]})==len(ordinary[2]))
 check('24_frozen_Entry_EXIT_allocation_identity',all(sha(CODE/name)==sha(SOURCE/'repo/research/capital-max3-upward-staircase-v4-20261004-v1'/name) for name in ('allocation.py','execution.py','staircase.py','core_features.py','preprocessing.py')))
 check('25_deterministic_mini_rerun_identity',day_replay(3,day,candidates,books,D(1000000),tables=tables)==ordinary)
 # Exact boundary canaries use synthetic training counts; never outcome tuning.
 test=dict(r,ML=1.25,rank='B');synthetic={'B_median':1.25,'B_p75':1.3,'training_session_N':100,'minute_counts':{},'minute_bucket':{}}
 for minute in (839,840,869,870):synthetic['minute_counts'][str(minute)]=[50,20,75,150];synthetic['minute_bucket'][str(minute)]='FIXED_BOUNDARY_CANARY'
 check('strict_p50_and_1400_boundary',not gate(test,1,839,synthetic)[0] and gate(test,1,840,synthetic)[0])
 test['ML']=1.3;synthetic['minute_counts']['869']=[35,10,74,100]
 check('strict_p35_boundary',not gate(test,2,869,synthetic)[0])
 synthetic['minute_counts']['869']=[34,10,75,100]
 check('strict_expected075_boundary',not gate(test,2,869,synthetic)[0])
 check('1430_retains_p75_boundary',gate(test,2,870,synthetic)[0] and not gate(dict(test,ML=1.299),2,870,synthetic)[0])
 save(OUT/'CAUSAL_CANARY_RESULTS.json',{'JST':now(),'checks':checks,'PASS_N':len(checks),'FAIL_N':0,'full_stream_deterministic_identity':'Pending post-primary full rerun, appended separately.','frozen_source_mutations':0})
 checkpoint('V4_CAUSAL_CANARY','PRE_REPLAY_CAUSAL_CANARIES_PASS',{'PASS':len(checks),'FAIL':0,'full_deterministic_rerun':'Pending'})
 print(json.dumps({'PASS':len(checks),'FAIL':0}))
if __name__=='__main__':main()
