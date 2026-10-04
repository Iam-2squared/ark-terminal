"""One precommitted downstream reference adapter; no allocator, EXIT runner or provider."""
import argparse, gzip, hashlib, json, math
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

DEADLINE=929
JST=timezone(timedelta(hours=9))
def hash_bytes(b):return hashlib.sha256(b).hexdigest()
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def read_gz(p):
 with gzip.open(p,'rt') as f:return json.load(f)
def read_rows(p):
 with gzip.open(p,'rt') as f:return [json.loads(x) for x in f if x.strip()]
def write_rows(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('wb') as raw:
  with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:
   for r in rows:f.write(canonical(r)+b'\n')
def stamp(day,minute):return day+'T%02d:%02d:00+09:00'%divmod(minute,60)
def open_only(rows,minute):
 """Completed High/Low/Close/volume/value never validate an Open at the deadline."""
 matches=[r for r in rows if int(r[0])==minute]
 if len(matches)!=1:return None
 try:value=Decimal(str(matches[0][1]))
 except Exception:return None
 return value if value.is_finite() and value>0 else None
def regular_at(day,minute):
 end=900 if day<'2024-11-05' else 925
 return 540<=minute<690 or 750<=minute<end
def adapter(entry,exitrow,path):
 """Only frozen fill reference fields and exact Open are inspected. No outcome input."""
 day=entry['session']; fill=entry['fill_minute']; rows=path['today']
 if fill>=DEADLINE:raise ValueError('ENTRY_DEADLINE_CONTRACT_CONTRADICTION')
 status=exitrow['sell_status']; sell_min=exitrow['sell_minute']
 if status=='FILLED' and sell_min==DEADLINE:raise ValueError('CONTRACT_BOUNDARY_UNRESOLVED')
 prior=status=='FILLED' and sell_min is not None and sell_min<DEADLINE
 if status=='FILLED':
  assert exitrow['sell_timestamp']==stamp(day,sell_min)
 open_price=open_only(rows,DEADLINE)
 raw_n=sum(int(r[0])==DEADLINE for r in rows)
 active=regular_at(day,DEADLINE)
 eod_needed=not prior
 eod_fill=eod_needed and active and open_price is not None
 if not active:reason='SESSION_NOT_ACTIVE'
 elif raw_n!=1 or open_price is None:reason='SOURCE_MISSING'
 else:reason=None
 # An exact historical reference Open never certifies a live fill/cash receipt.
 known='REFERENCE_FILL_ONLY_NOT_RUNTIME_KNOWN_AT' if prior else ('REFERENCE_OPEN_ONLY_ACTUAL_ARRIVAL_UNKNOWN' if eod_fill else 'NO_ADMISSIBLE_EXECUTION_SOURCE')
 final_price=exitrow['sell_price_decimal'] if prior else (str(open_price*Decimal('0.9995')) if eod_fill else None)
 final_time=exitrow['sell_timestamp'] if prior else (stamp(day,DEADLINE) if eod_fill else None)
 source_key=exitrow['sell_source'] if prior else ('EOD_1529_EXACT_REGULAR_OPEN' if eod_fill else None)
 row={'entry_id':entry['watch_key'],'session':day,'symbol':entry['symbol'],'entry_timestamp':entry['fill_timestamp'],'entry_effective_price':entry['fill_price'],'frozen_exit_v3_status':status,'frozen_exit_v3_timestamp':exitrow['sell_timestamp'],'frozen_exit_v3_price':exitrow['sell_price_decimal'],'frozen_exit_v3_source':exitrow['sell_source'],'frozen_exit_v3_assumed_available_at':exitrow['sell_source_assumed_available_at'],'frozen_exit_v3_original_row_sha256':hash_bytes(canonical(exitrow)), 'prior_frozen_exit_before_1529':prior,'eod_overlay_applied':eod_needed,'eod_decision_timestamp':stamp(day,DEADLINE) if eod_needed else None,'eod_source_timestamp':stamp(day,DEADLINE) if raw_n==1 else None,'eod_source_price':str(open_price) if open_price is not None else None,'eod_raw_source_rows_N':raw_n,'eod_raw_Open_present_valid':open_price is not None,'deadline_regular_execution_active':active,'eod_admissible_source':active and open_price is not None,'eod_fill':eod_fill,'eod_unfillable_reason':reason if eod_needed and not eod_fill else None,'eod_effective_sell_price':str(open_price*Decimal('0.9995')) if eod_fill else None,'final_integrated_exit_status':'FROZEN_PRIOR_FILLED_REFERENCE' if prior else ('EOD_FILLED_REFERENCE' if eod_fill else 'UNRESOLVED_FAIL_CLOSED'),'final_integrated_exit_reason':exitrow['exit_reason'] if prior else ('EOD_FORCE_EXIT_1529' if eod_fill else 'UNRESOLVED_FAIL_CLOSED'),'final_integrated_exit_timestamp':final_time,'final_integrated_exit_price':final_price,'final_integrated_exit_source':source_key,'cash_release_reference_timestamp':final_time,'cash_release_timestamp':None,'cash_release_authorized':False,'known_at_status':known,'source_lineage':{'policy_id':'EOD_FORCE_EXIT_1529_V1','raw_frozen_sourceHash':path['sourceHash'],'source_role':'raw unadjusted1m Open; regular execution required','actual_arrival':'UNKNOWN','frozen_assumed_availability_unchanged':True},'position_quantity':None,'quantity_status':'NO_ALLOCATOR_NO_FUNDED_POSITION','same_day_reference_closed':prior or eod_fill,'fail_closed_obligation_retained':not(prior or eod_fill),'candidate_excluded':False}
 return row
def run(args):
 inp=Path(args.inputs); pub=Path(args.public); private=Path(args.private);pub.mkdir(parents=True,exist_ok=True);private.mkdir(parents=True,exist_ok=True)
 policy_path=pub/'EOD_1529_PRECOMMIT.json'
 assert policy_path.exists(),'precommit required'
 policy=json.loads(policy_path.read_text());assert policy['policy_id']=='EOD_FORCE_EXIT_1529_V1'
 assert policy['deadline_minute']==DEADLINE
 assert hash_bytes((pub/'EOD_1529_SOURCE_CONTRACT.json').read_bytes())==policy['source_contract_sha256']
 assert hash_bytes((pub/'EOD_1529_ACCOUNTING_CONTRACT.json').read_bytes())==policy['accounting_contract_sha256']
 assert policy['new_1529_price_coverage_PnL_seen_before_precommit'] is False
 entries=[r for r in read_rows(inp/'entry.jsonl.gz') if r['entry_status']=='FIRST_ENTRY']
 exits=read_rows(inp/'exit_v3.jsonl.gz'); paths=read_gz(inp/'raw_paths.json.gz');tokens=read_gz(inp/'source_tokens.json.gz')
 E={x['watch_key']:x for x in entries};X={x['watch_key']:x for x in exits}
 assert len(E)==len(entries)==len(X)==len(exits)==len(paths)==1600
 assert set(E)==set(X)==set(paths)==set(tokens)
 original={n:hash_bytes((inp/n).read_bytes()) for n in ('entry.jsonl.gz','exit_v3.jsonl.gz','raw_paths.json.gz','source_tokens.json.gz')}
 rows=[]; buy_mismatch=sell_mismatch=cash_mismatch=0; prior_known_delta=Counter();token929=0
 for key in sorted(E):
  e=E[key];x=X[key];p=paths[key]
  assert x['entry_timestamp']==e['fill_timestamp'] and x['entry_fill_price']==e['fill_price']
  a=open_only(p['today'],e['fill_minute']);assert a is not None
  buy_mismatch += not math.isclose(float(a*Decimal('1.0005')),e['fill_price'],rel_tol=1e-12,abs_tol=1e-8)
  assert x['commission']==0 and x['sell_adjustment_bps']==5
  if x['sell_status']=='FILLED':
   rr=[r for r in p['today'] if int(r[0])==x['sell_minute']];assert len(rr)==1
   raw_price=Decimal(str(rr[0][1] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else rr[0][4]))
   sell_mismatch += raw_price*Decimal('0.9995') != Decimal(x['sell_price_decimal'])
   qty=Decimal(100);buy=qty*Decimal(str(e['fill_price']));sell=qty*Decimal(x['sell_price_decimal'])
   endpoint=Decimal(1000000)-buy+sell;trade=qty*(Decimal(x['sell_price_decimal'])-Decimal(str(e['fill_price'])))
   cash_mismatch += endpoint-Decimal(1000000)!=trade
  row=adapter(e,x,p)
  if row['prior_frozen_exit_before_1529']:
   delta=(datetime.fromisoformat(x['sell_source_assumed_available_at'])-datetime.fromisoformat(x['sell_timestamp'])).total_seconds();prior_known_delta[str(int(delta))]+=1
  token929 += any(t['Time']=='15:29' for t in tokens[key]['current_prefix'])
  rows.append(row)
 assert original=={n:hash_bytes((inp/n).read_bytes()) for n in original}
 assert buy_mismatch==sell_mismatch==cash_mismatch==0
 write_rows(private/'EOD_OVERLAY_ROWS.jsonl.gz',rows)
 old39=[r for r in rows if r['frozen_exit_v3_status']=='UNRESOLVED'];assert len(old39)==39
 write_rows(private/'OLD39_EOD_OVERLAY_ROWS.jsonl.gz',old39)
 sessions=sorted({r['session'] for r in rows});session_rows=[]
 for i,day in enumerate(sessions,1):
  group=[r for r in rows if r['session']==day]
  session_rows.append({'session_ordinal':i,'candidate_N':len(group),'prior_frozen_exit_N':sum(r['prior_frozen_exit_before_1529'] for r in group),'EOD_needed_N':sum(r['eod_overlay_applied'] for r in group),'EOD_valid_fill_N':sum(r['eod_fill'] for r in group),'EOD_unfillable_N':sum(r['eod_overlay_applied'] and not r['eod_fill'] for r in group),'old39_unresolved_N':sum(r['frozen_exit_v3_status']=='UNRESOLVED' for r in group),'raw1529_presence_N':sum(r['eod_raw_source_rows_N']>0 for r in group)})
 def n(field):return sum(bool(r[field]) for r in rows)
 coverage={'saved_at_jst':datetime.now(JST).isoformat(),'policy_id':policy['policy_id'],'contract_sha256':hash_bytes(policy_path.read_bytes()),'precommit_result_HEAD':args.basis,'population':'Frozen candidate-level Development; not funded positions','candidate_N':len(rows),'sessions_N':len(sessions),'distinct_symbols_N':len({r['symbol'] for r in rows}),'dataset_period':{'first':sessions[0],'last':sessions[-1]},'prior_frozen_exit_before1529_N':n('prior_frozen_exit_before_1529'),'EOD_needed_N':n('eod_overlay_applied'),'EOD_valid_fill_N':n('eod_fill'),'EOD_unfillable_N':sum(r['eod_overlay_applied'] and not r['eod_fill'] for r in rows),'raw1529_presence_N':sum(r['eod_raw_source_rows_N']>0 for r in rows),'raw1529_Open_valid_N':n('eod_raw_Open_present_valid'),'raw1529_missing_N':sum(r['eod_raw_source_rows_N']==0 for r in rows),'raw1529_duplicate_N':sum(r['eod_raw_source_rows_N']>1 for r in rows),'admissible1529_source_N':n('eod_admissible_source'),'original_source_token_current_prefix_1529_presence_N':token929,'deadline_regular_execution_active_N':n('deadline_regular_execution_active'),'EOD_unfillable_reason_counts':dict(Counter(r['eod_unfillable_reason'] for r in rows if r['eod_overlay_applied'] and not r['eod_fill'])),'old39':{'N':len(old39),'new_overlay_same_day_closed_N':sum(r['eod_fill'] for r in old39),'unchanged_Frozen_unresolved_N':39,'EOD_unfillable_reasons':dict(Counter(r['eod_unfillable_reason'] for r in old39)),'affected_sessions_N':len({r['session'] for r in old39}),'affected_symbols_N':len({r['symbol'] for r in old39})},'same_day_reference_closed_N':n('same_day_reference_closed'),'retained_fail_closed_candidate_obligation_N':n('fail_closed_obligation_retained'),'actual_overnight_funded_positions_N':None,'actual_overnight_funded_positions_reason':'Allocator not run. Candidate-level unresolved obligations must not be called real funded overnight positions.','known_at_classification':dict(Counter(r['known_at_status'] for r in rows)),'runtime_cash_release_authorized_N':n('cash_release_authorized'),'prior_reference_assumed_availability_delta_seconds':dict(prior_known_delta),'missing_price_imputation_N':0,'future_price_input_N':0,'candidate_exclusion_N':0,'Frozen_changes_N':0,'input_component_sha256':original,'source_market_boundary':'TSE continuous trading ends15:25;15:29 pre-closing has no executions. No auction substitution or time shift.','source_retrieval':'Existing Private parent only. New market data/provider requests0.','performance_metrics':'NOT_EXECUTED_C2_NOT_PASS'}
 (pub/'EOD_1529_SOURCE_COVERAGE.json').write_text(json.dumps(coverage,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 (pub/'SESSION_COVERAGE_AGGREGATE.json').write_text(json.dumps(session_rows,sort_keys=True,indent=2)+'\n')
 accounting={'saved_at_jst':datetime.now(JST).isoformat(),'BUY_arithmetic_N':1600,'BUY_arithmetic_mismatch_N':buy_mismatch,'Frozen_SELL_arithmetic_N':1561,'Frozen_SELL_arithmetic_mismatch_N':sell_mismatch,'isolated_100share_cash_endpoint_vs_trade_PnL_N':1561,'isolated_accounting_mismatch_N':cash_mismatch,'isolated_checks_are_Portfolio_replay':False,'EOD_fill_N':n('eod_fill'),'EOD_cash_release_N':0,'cash_double_release_N':0,'cost_double_count_N':0,'commission':0,'Frozen_entry_cost_included_once':True,'Frozen_sell_cost_included_once':True,'extra_fee_N':0,'reference_vs_runtime_cash':'Preserved Frozen reference timestamps are not authorized cash-known events; source assumption+1m unchanged; actual arrival UNKNOWN.','runtime_funded_ledger_verified':False,'current_MTM_binding':'Parent C2 remains unresolved; no new cadence, last-price, cross-session mark or partial comparison adopted.'}
 (pub/'ACCOUNTING_KNOWN_AT_AUDIT.json').write_text(json.dumps(accounting,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'candidate_N':coverage['candidate_N'],'prior_exit_N':coverage['prior_frozen_exit_before1529_N'],'EOD_needed_N':coverage['EOD_needed_N'],'EOD_valid_fill_N':coverage['EOD_valid_fill_N'],'EOD_unfillable_N':coverage['EOD_unfillable_N'],'raw1529_presence_N':coverage['raw1529_presence_N'],'admissible1529_source_N':coverage['admissible1529_source_N'],'reasons':coverage['EOD_unfillable_reason_counts'],'old39':coverage['old39'],'arithmetic_mismatch_N':buy_mismatch+sell_mismatch+cash_mismatch},ensure_ascii=False))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--inputs',required=True);parser.add_argument('--public',required=True);parser.add_argument('--private',required=True);parser.add_argument('--basis',required=True);run(parser.parse_args())
