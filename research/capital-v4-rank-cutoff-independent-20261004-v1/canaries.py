from common import *
from replay import run_profile,day_replay,candidate_order
from allocation import CAP,BASE
from execution import valid_market
from decimal import Decimal as D
import copy
def main():
 stream=rows(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz');books=source_books();tests=[]
 def test(name,ok,detail=None):tests.append({'name':name,'PASS':bool(ok),'detail':detail})
 test('v4_score_stream_hash_exact',sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')=='c446633dec923e3a80a534b19325ccff49f769a2ff1d29c7af1202202de614d4')
 test('ML_exact_identity',all(r['ML']==r['capital_score'] for r in stream));test('rank_exact_identity',all(r['rank']==('S' if r['ML']>=2 else 'A' if r['ML']>=1.5 else 'B' if r['ML']>=1 else 'C') for r in stream))
 test('new_fit0',not list(PRIVATE.glob('*MODEL*')) and not list(PRIVATE.glob('*BLOCK*')))
 test('rank_cap_unchanged',CAP=={'S':D('.45'),'A':D('.35'),'B':D('.25')});test('base_utilization_unchanged',BASE=={'S':D('.68'),'A':D('.56'),'B':D('.44')})
 for arm in PROFILES:
  result=json.loads((PRIVATE/f'{arm}_RESULT.json').read_text());ds=rows(PRIVATE/f'{arm}_DECISIONS.jsonl.gz');ts=rows(PRIVATE/f'{arm}_TRADES.jsonl.gz');cs=rows(PRIVATE/f'{arm}_CURVE.jsonl.gz');sm={r['entry_id']:r for r in stream};funded=[d for d in ds if d['reason']=='FUNDED']
  test(arm+'/excluded_rank_funding0',all(sm[d['entry_id']]['rank'] in ALLOWED[arm] for d in funded));test(arm+'/no_backfill',all(d['quantity']==0 for d in ds if d['reason'].startswith('RANK_CUTOFF_')))
  test(arm+'/score_order_unchanged',all([d['entry_id'] for d in ds if d['session']==day and d['minute']==minute]==[r['entry_id'] for r in sorted([r for r in stream if r['session']==day and r['entry_minute']==minute],key=candidate_order)] for day,minute in {(d['session'],d['minute']) for d in ds}))
  test(arm+'/MAX3',max(c['concurrent'] for c in cs)<=3);test(arm+'/100_share_lot',all(d['quantity']%100==0 for d in ds));test(arm+'/cash_nonnegative',all(D(c['cash'])>=0 for c in cs));test(arm+'/LONG_cash_only',all(d['quantity']>=0 for d in ds) and all(t['quantity']>0 and D(t['debit'])>0 and D(t['credit'])>0 for t in ts))
  test(arm+'/entry_cutoff',all(d['minute']<920 for d in funded));test(arm+'/duplicate_sell0',len(ts)==len({t['entry_id'] for t in ts}));test(arm+'/valid_exit_only_release',all(t['exit_kind'] in ('FROZEN_EXIT_V3','EOD_REGULAR','EOD_EXACT_1530_AUCTION') and t['release_minute']>t['source_minute'] for t in ts))
  trades_by_time={}
  for t in ts:trades_by_time.setdefault((t['session'],t['release_minute']),D(0));trades_by_time[t['session'],t['release_minute']]+=D(t['credit'])
  buys_by_time={}
  for d in funded:buys_by_time.setdefault((d['session'],d['minute']),D(0));buys_by_time[d['session'],d['minute']]+=D(d['debit'])
  changes=[]
  for a,b in zip(cs,cs[1:]):
   if a['session']==b['session']:changes.append(D(b['cash'])-D(a['cash'])==trades_by_time.get((b['session'],b['minute']),D(0))-buys_by_time.get((b['session'],b['minute']),D(0)))
  test(arm+'/MTM_no_trade_cash_release0',all(changes),'Every cash change must equal actual BUY/SELL, never MTM.')
  mutated=copy.deepcopy(stream)
  for r in mutated:r['liquidity']={'reason':'MUTATED_EXTREME'};r['HF1']=999;r['HL0']=-999;r['Movement']='MUTATED'
  rerun,rds,rts,rcs,rit=run_profile(arm,3,mutated,books)
  test(arm+'/liquidity_fields_admission_quantity_invariant',rds==ds and rts==ts and rcs==cs)
  test(arm+'/deterministic_replay_identity',rerun['daily_series']==result['daily_series'] and rds==ds and rts==ts and rcs==cs and rit==rows(PRIVATE/f'{arm}_INTENTS.jsonl.gz'))
 # Future EXIT changes legitimately affect later available cash/slots. Test the
 # causal contract on the same isolated Entry decision, not all later sessions.
 r=next(x for x in stream if x['rank']=='S' and x['entry_minute']<920);key=r['entry_id'];book=copy.deepcopy(books[key])
 base=day_replay(3,r['session'],[r],{key:book},D(1000000),True,'S_ONLY_MAX3')[1][0]
 for row in book['market']:
  if row['minute']>r['entry_minute']:row['H']=str(D(row['H'])*10)
 book['frozen_exit']['sell_status']='UNFILLED'
 changed=day_replay(3,r['session'],[r],{key:book},D(1000000),True,'S_ONLY_MAX3')[1][0]
 test('future_High_EXIT_same_entry_decision_invariant',base==changed,'Execution can change subsequent cash/slots; current funding decision is outcome blind.')
 identity=json.loads((OUT/'B_PLUS_IDENTITY.json').read_text());test('B_PLUS_funded_ID_quantity_daily_all_metrics_exact',not identity['mismatch']);test('B_PLUS_final_equity_exact',identity['final_equity_exact']==1433740.25)
 hashes=json.loads((OUT/'SOURCE_HASHES.json').read_text());test('Frozen_Entry_EXIT_source_changes0',all(sha(WORK/k)==v for k,v in hashes.items()))
 pin=json.loads((OUT/'CODE_PRECOMMIT.json').read_text());test('precommitted_code_unchanged',all(sha(CODE/k)==v for k,v in pin.items()));test('short_margin_leverage_orders_promotion0',all(v is False for v in SAFETY.values()))
 result={'tests':tests,'pass_N':sum(t['PASS'] for t in tests),'failed_N':sum(not t['PASS'] for t in tests),'deterministic_canary_replays':3,'main_diagnostic_replays':3,'isolated_mutation_replays':2,'new_fit':0,'independent_mismatch_N':json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text())['mismatch_N']}
 save(OUT/'CANARY_RESULTS.json',result);assert not result['failed_N'];checkpoint('R8_INDEPENDENT_AUDIT','INDEPENDENT_AUDIT_CANARIES_PASS',{'independent_mismatch_N':result['independent_mismatch_N'],'canary_pass_N':result['pass_N'],'new_fit':0});print(json.dumps({k:v for k,v in result.items() if k!='tests'}))
if __name__=='__main__':main()
