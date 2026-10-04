"""Future intent isolation and no fabricated releases; no Capital performance."""
import argparse,copy,gzip,hashlib,json
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone,timedelta
import audit_eod1520_primary as primary

def H(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--rows',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 files=['entry.jsonl.gz','exit_v3.jsonl.gz','raw_paths.json.gz','source_tokens.json.gz'];before={x:H((a.inputs/x).read_bytes()) for x in files}
 E={r['watch_key']:r for r in [json.loads(s) for s in gzip.decompress((a.inputs/'entry.jsonl.gz').read_bytes()).decode().splitlines()] if r['entry_status']=='FIRST_ENTRY'}
 X={r['watch_key']:r for r in [json.loads(s) for s in gzip.decompress((a.inputs/'exit_v3.jsonl.gz').read_bytes()).decode().splitlines()]};P=json.loads(gzip.decompress((a.inputs/'raw_paths.json.gz').read_bytes()));R={r['entry_id']:r for r in [json.loads(s) for s in gzip.decompress(a.rows.read_bytes()).decode().splitlines()]}
 counts=Counter();fail=[]
 def check(name,condition):
  counts[name]+=1
  if not condition:fail.append(name)
 for k in sorted(E):
  e,x,path=E[k],X[k],P[k];r=R[k];it=primary.intent(e,x)
  ef=copy.deepcopy(e)
  for f in ['remaining_upside_pct','session_end_mfe_pct','session_end_mae_pct','observed_terminal_return_pct','first_upside','peak_minute']:ef[f]='POISON_FUTURE_OUTCOME'
  check('future_entry_outcomes_do_not_change_intent',primary.intent(ef,x)==it)
  # A later EXIT result cannot become a pre-intent fact.
  xf=copy.deepcopy(x)
  if x.get('sell_timestamp') is None or x['sell_timestamp']>=primary.iso(e['session'],920):
   xf.update(sell_status='FILLED',sell_timestamp=primary.iso(e['session'],930),sell_minute=930,sell_price_decimal='999999999')
   check('future_EXIT_outcome_do_not_change_intent',primary.intent(e,xf)==it)
  changed={'contract':path['contract'],'sourceHash':path['sourceHash'],'today':[],'previous':[['POISON_NEXT_DAY']],'previousSession':'POISON'}
  for raw in path['today']:
   nr=list(raw)
   if nr[0]>=920:
    nr[1:5]=[v*2 for v in nr[1:5]];nr[6]*=2
   changed['today'].append(nr)
  rr=primary.adapt(e,x,changed)
  check('post_intent_prices_do_not_change_intent',rr['eod_intent']==r['eod_intent'])
  nextday=copy.deepcopy(path);nextday['nextDay']=[[540,999,999,999,999,999,999]];nextday['previous']=[['POISON_NOT_USED']]
  check('nextday_prices_do_not_change_today_adapter',primary.adapt(e,x,nextday)==r)
  check('commission_zero',r['broker_commission_JPY']==0)
  check('at_most_one_final_cash_release',bool(r['cash_release_timestamp'])==r['historical_cash_release_authorized'])
  if not it['committed']:
   check('already_closed_or_late_not_EOD_filled',r['eod_fill_status']=='NOT_APPLIED')
  else:
   check('idempotent_intent_guard',not primary.intent(e,x,already_committed=True)['committed'])
   check('zero_remaining_quantity_guard',not primary.intent(e,x,remaining_quantity=0)['committed'])
   missing=copy.deepcopy(path);missing['today']=[z for z in path['today'] if z[0]<920]
   mr=primary.adapt(e,x,missing)
   check('missing_execution_no_fabricated_fill_or_cash',mr['eod_fill_status']=='EOD_UNEXECUTED_FAIL_CLOSED' and mr['cash_release_timestamp'] is None and mr['cash_release_per_share'] is None)
   if r['eod_fill_status']=='FILLED_REFERENCE':
    check('cash_after_reference_source_completion',r['cash_release_timestamp']>r['integrated_exit_timestamp'])
    if r['eod_fill_source_type']=='FIRST_POST_INTENT_REGULAR_RAW_OPEN':
     # Remove/poison later minutes, exact auction and following-day prices;
     # the selected first trade remains unchanged.
     cutoff=r['source_lineage']['source_minute'];tail=copy.deepcopy(path);tail['today']=[z for z in path['today'] if z[0]<=cutoff]
     check('later_trade_suffix_does_not_change_first_fill',primary.adapt(e,x,tail)['eod_effective_price']==r['eod_effective_price'])
 check('identities_unique',len(R)==len(E)==1600)
 check('Frozen_sources_immutable',before=={x:H((a.inputs/x).read_bytes()) for x in files})
 result={'saved_at_jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':'PASS' if not fail else 'FAIL','canary_checks_N':sum(counts.values()),'mismatch_N':len(fail),'tests':dict(counts),'immutable_source_hashes':before,'policy_deadline_sweep':0,'provider_requests':0,'runtime_or_performance_certification':False,'execution_prices_are_outcomes':'Post-intent prices can change fill results but never order intent; no claim of price-invariance to changing actual first trade.'}
 assert not a.output.exists();a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n');print(json.dumps({'status':result['status'],'checks':result['canary_checks_N'],'mismatch':len(fail)},ensure_ascii=False));assert not fail,fail
if __name__=='__main__':main()
