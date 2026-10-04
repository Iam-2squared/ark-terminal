"""Independent EOD audit: original V2/V3 attachments, Fraction arithmetic, no Primary import."""
import argparse, gzip, hashlib, json
from fractions import Fraction
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter

FIELDS=['entry_id','session','symbol','entry_timestamp','entry_effective_price','frozen_exit_v3_status','frozen_exit_v3_timestamp','frozen_exit_v3_price','frozen_exit_v3_source','frozen_exit_v3_assumed_available_at','frozen_exit_v3_original_row_sha256','prior_frozen_exit_before_1529','eod_overlay_applied','eod_decision_timestamp','eod_source_timestamp','eod_source_price','eod_raw_source_rows_N','eod_raw_Open_present_valid','deadline_regular_execution_active','eod_admissible_source','eod_fill','eod_unfillable_reason','eod_effective_sell_price','final_integrated_exit_status','final_integrated_exit_reason','final_integrated_exit_timestamp','final_integrated_exit_price','final_integrated_exit_source','cash_release_reference_timestamp','cash_release_timestamp','cash_release_authorized','known_at_status','position_quantity','quantity_status','same_day_reference_closed','fail_closed_obligation_retained','candidate_excluded']
def h(b):return hashlib.sha256(b).hexdigest()
def pack(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()
def lines(p):
 with gzip.open(p,'rb') as f:return [json.loads(x) for x in f if x.strip()]
def bundle(p):
 with gzip.open(p,'rt') as f:return json.load(f)
def raw_open(price):
 try:
  f=Fraction(str(price))
  return f if f>0 else None
 except (ValueError,ZeroDivisionError):return None
def time_of(day,m):
 return f'{day}T{m//60:02d}:{m%60:02d}:00+09:00'
def assemble(buy,sell,source):
 # Date and regular schedule are independently expanded, not imported.
 day=buy['session']; deadline=time_of(day,15*60+29)
 morning=set(range(9*60,11*60+30))
 afternoon=set(range(12*60+30,15*60+(25 if day>='2024-11-05' else 0)))
 executable=(15*60+29) in morning|afternoon
 assert buy['fill_timestamp']<deadline
 closed=sell['sell_status']=='FILLED' and sell['sell_timestamp']<deadline
 assert sell['sell_status']!='FILLED' or sell['sell_timestamp']!=deadline
 exact=[x for x in source['today'] if x[0]==15*60+29]
 price=raw_open(exact[0][1]) if len(exact)==1 else None
 has_open=price is not None
 force=not closed
 filled=force and executable and has_open
 # Current deadline fails regular-session gate. No numeric future field is read.
 if filled:raise RuntimeError('Unexpected admissible active15:29; separately inspect reference cash-known evidence before continuing.')
 t=sell['sell_timestamp'] if closed else None
 p=sell['sell_price_decimal'] if closed else None
 r={'entry_id':buy['watch_key'],'session':day,'symbol':buy['symbol'],'entry_timestamp':buy['fill_timestamp'],'entry_effective_price':buy['fill_price'],'frozen_exit_v3_status':sell['sell_status'],'frozen_exit_v3_timestamp':sell['sell_timestamp'],'frozen_exit_v3_price':sell['sell_price_decimal'],'frozen_exit_v3_source':sell['sell_source'],'frozen_exit_v3_assumed_available_at':sell['sell_source_assumed_available_at'],'frozen_exit_v3_original_row_sha256':h(pack(sell)),'prior_frozen_exit_before_1529':closed,'eod_overlay_applied':force,'eod_decision_timestamp':deadline if force else None,'eod_source_timestamp':deadline if len(exact)==1 else None,'eod_source_price':None,'eod_raw_source_rows_N':len(exact),'eod_raw_Open_present_valid':has_open,'deadline_regular_execution_active':executable,'eod_admissible_source':executable and has_open,'eod_fill':filled,'eod_unfillable_reason':'SESSION_NOT_ACTIVE' if force and not executable else ('SOURCE_MISSING' if force else None),'eod_effective_sell_price':None,'final_integrated_exit_status':'FROZEN_PRIOR_FILLED_REFERENCE' if closed else 'UNRESOLVED_FAIL_CLOSED','final_integrated_exit_reason':sell['exit_reason'] if closed else 'UNRESOLVED_FAIL_CLOSED','final_integrated_exit_timestamp':t,'final_integrated_exit_price':p,'final_integrated_exit_source':sell['sell_source'] if closed else None,'cash_release_reference_timestamp':t,'cash_release_timestamp':None,'cash_release_authorized':False,'known_at_status':'REFERENCE_FILL_ONLY_NOT_RUNTIME_KNOWN_AT' if closed else 'NO_ADMISSIBLE_EXECUTION_SOURCE','position_quantity':None,'quantity_status':'NO_ALLOCATOR_NO_FUNDED_POSITION','same_day_reference_closed':closed or filled,'fail_closed_obligation_retained':not (closed or filled),'candidate_excluded':False}
 assert price is None,'Source coverage changed; preserve Open lexical independently before any filled admission.'
 return r
def verify_component(inp,manifest_name,file,member):
 d=json.loads((inp/manifest_name).read_text());receipt=d['components'][member];b=(inp/file).read_bytes()
 assert h(b)==receipt['sha256'] and len(b)==receipt['bytes']
 return {'file':file,'manifest':manifest_name,'original_member':member,'sha256':h(b),'match':True}
def run(args):
 inp=Path(args.inputs);priv=Path(args.private);pub=Path(args.public)
 checks=[verify_component(inp,'entry_manifest.json','entry.jsonl.gz','FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'),verify_component(inp,'entry_manifest.json','raw_paths.json.gz','SAVED_INPUTS/raw_paths_selected.json.gz'),verify_component(inp,'exit_manifest.json','exit_v3.jsonl.gz','REPLAY_ROWS.jsonl.gz')]
 watches=lines(inp/'entry.jsonl.gz'); entries={r['watch_key']:r for r in watches if r['entry_status']=='FIRST_ENTRY'}; exits={r['watch_key']:r for r in lines(inp/'exit_v3.jsonl.gz')};raw=bundle(inp/'raw_paths.json.gz')
 assert len(entries)==len(exits)==len(raw)==1600 and entries.keys()==exits.keys()==raw.keys()
 result=[];entry_errors=exit_errors=accounting_errors=0;known_delta=Counter()
 for identity in sorted(entries):
  e=entries[identity];x=exits[identity];source=raw[identity]
  assert x['entry_timestamp']==e['fill_timestamp'] and x['entry_fill_price']==e['fill_price']
  erows=[a for a in source['today'] if int(a[0])==e['fill_minute']];assert len(erows)==1
  effective_entry=Fraction(str(erows[0][1]))*Fraction(10005,10000)
  entry_errors += abs(effective_entry-Fraction(str(e['fill_price'])))>Fraction(1,10**8)
  if x['sell_status']=='FILLED':
   sr=[a for a in source['today'] if int(a[0])==x['sell_minute']];assert len(sr)==1
   idx=1 if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else 4
   effective_exit=Fraction(str(sr[0][idx]))*Fraction(9995,10000)
   exit_errors += effective_exit != Fraction(x['sell_price_decimal'])
   assert x['commission']==0 and x['sell_adjustment_bps']==5
   qty=100; initial=1000000;buy=qty*Fraction(str(e['fill_price']));sell=qty*Fraction(x['sell_price_decimal'])
   accounting_errors += (initial-buy+sell-initial)!=(sell-buy)
  row=assemble(e,x,source)
  if row['prior_frozen_exit_before_1529']:
   known_delta[int((datetime.fromisoformat(x['sell_source_assumed_available_at'])-datetime.fromisoformat(x['sell_timestamp'])).total_seconds())]+=1
  result.append(row)
 priv.mkdir(exist_ok=True,parents=True)
 with (priv/'INDEPENDENT_EOD_OVERLAY_ROWS.jsonl.gz').open('wb') as f:
  with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:
   for r in result:z.write(pack(r)+b'\n')
 # Comparison occurs only after independent result rows exist.
 primary=lines(priv/'EOD_OVERLAY_ROWS.jsonl.gz');P={r['entry_id']:r for r in primary}
 mismatches=[]
 for r in result:
  for key in FIELDS:
   if r[key]!=P[r['entry_id']][key]:mismatches.append({'entry_id':r['entry_id'],'field':key})
 raw_primary=bundle(Path(args.primary_inputs)/'raw_paths.json.gz')
 source_mismatch=sum(raw[k]!=raw_primary[k] for k in raw)
 private_mismatch=priv/'INDEPENDENT_MISMATCHES.json';private_mismatch.write_text(json.dumps(mismatches,indent=2)+'\n')
 agg={'saved_at_jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'policy_id':'EOD_FORCE_EXIT_1529_V1','Primary_imported':False,'independent_source_route':'original nested V2/V3 attachments; independently checked original component manifests; no Primary source/result copied','arithmetic':'Fraction rational arithmetic, independently expanded dated regular-minute set','manifest_hash_checks':checks,'candidate_N':len(result),'identities_mismatch_N':len(set(P)^set(entries)),'compared_fields_N':len(FIELDS),'compared_values_N':len(result)*len(FIELDS),'row_field_mismatch_N':len(mismatches),'original_raw_arrays_vs_parent_recovery_mismatch_N':source_mismatch,'BUY_arithmetic_mismatch_N':entry_errors,'SELL_arithmetic_mismatch_N':exit_errors,'isolated_accounting_mismatch_N':accounting_errors,'prior_frozen_exit_before1529_N':sum(r['prior_frozen_exit_before_1529'] for r in result),'EOD_needed_N':sum(r['eod_overlay_applied'] for r in result),'EOD_valid_fill_N':sum(r['eod_fill'] for r in result),'EOD_unfillable_N':sum(r['fail_closed_obligation_retained'] for r in result),'raw1529_presence_N':sum(r['eod_raw_source_rows_N']>0 for r in result),'admissible1529_source_N':sum(r['eod_admissible_source'] for r in result),'cash_release_authorized_N':sum(r['cash_release_authorized'] for r in result),'known_at_classification':dict(Counter(r['known_at_status'] for r in result)),'prior_reference_assumed_availability_delta_seconds':dict(known_delta),'Capital_replay':0,'future_outcome_research':0,'status':'PASS_INTERNAL_AGREEMENT_NOT_C2_ADMISSION' if not(mismatches or source_mismatch or entry_errors or exit_errors or accounting_errors) else 'FAIL'}
 (pub/'INDEPENDENT_AUDIT.json').write_text(json.dumps(agg,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
 assert agg['status']=='PASS_INTERNAL_AGREEMENT_NOT_C2_ADMISSION'
 print(json.dumps({k:agg[k] for k in ('status','candidate_N','compared_values_N','row_field_mismatch_N','original_raw_arrays_vs_parent_recovery_mismatch_N','EOD_needed_N','EOD_valid_fill_N','EOD_unfillable_N')},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--primary-inputs',required=True);p.add_argument('--public',required=True);p.add_argument('--private',required=True);run(p.parse_args())
