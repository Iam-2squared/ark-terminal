"""Separate Fraction-based source reconstruction. Never imports Primary."""
import argparse,gzip,json,hashlib,math
from pathlib import Path
from fractions import Fraction as F
from datetime import datetime,timedelta,timezone
from collections import Counter

def H(b):return hashlib.sha256(b).hexdigest()
def J(o):return json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def rows(p):return [json.loads(x) for x in gzip.decompress(p.read_bytes()).decode().splitlines()]
def clock(day,minute):return (datetime.fromisoformat(day+'T00:00:00+09:00')+timedelta(minutes=minute)).isoformat()
def textnum(q):
 # Exact terminating decimal without float conversions.
 sign='-' if q<0 else '';q=abs(q);whole,rem=divmod(q.numerator,q.denominator);s=str(whole)
 if rem:
  s+='.'
  while rem:rem*=10;n,rem=divmod(rem,q.denominator);s+=str(n)
 return sign+s
def valid(row,is_auction):
 try:
  if len(row)!=7 or not all(math.isfinite(x) for x in row):return False
  m,o,hi,lo,c,v,a=[F(str(x)) for x in row]
  if m.denominator!=1 or min(o,hi,lo,c,v,a)<=0:return False
  if lo>min(o,c) or hi<max(o,c):return False
  return not is_auction or o==hi==lo==c
 except (ValueError,TypeError,ZeroDivisionError):return False
def reconstruct(e,x,p):
 key=e['watch_key'];day=e['session'];cut=clock(day,15*60+20)
 r={'entry_id':key,'entry_timestamp':e['fill_timestamp'],'frozen_exit_status':x['sell_status'],'frozen_exit_timestamp':x['sell_timestamp'],'frozen_exit_price':x['sell_price_decimal'],'broker_commission_JPY':0,'execution_factor':'0.9995','eod_eligible':False,'eod_intent_timestamp':None,'eod_order_type':None,'eod_sor':None,'eod_execution_condition':None,'eod_remaining_quantity':None,'eod_fill_status':'NOT_APPLIED','eod_fill_source_type':None,'eod_fill_source_timestamp':None,'eod_reference_price':None,'eod_effective_price':None,'final_exit_status':None,'integrated_exit_reason':None,'integrated_exit_timestamp':None,'integrated_exit_price':None,'cash_release_timestamp':None,'cash_release_per_share':None,'historical_cash_release_authorized':False,'runtime_cash_release_certified':False,'known_at_status':'ACTUAL_ARRIVAL_UNKNOWN_REFERENCE_ONLY','assumed_available_at':None,'overnight_obligation':True,'reason':None,'regular_source_N':0,'valid_regular_source_N':0,'exact_auction_source_N':0,'valid_auction_source_N':0}
 if e['fill_minute']>=15*60+20:r.update(final_exit_status='EOD_UNEXECUTED_FAIL_CLOSED',reason='ENTRY_AT_OR_AFTER_INTENT');return r
 if x['sell_status']=='FILLED' and x['sell_timestamp']<cut:
  r.update(final_exit_status='FILLED_REFERENCE',integrated_exit_reason='FROZEN_EXIT_V3_PRIOR',integrated_exit_timestamp=x['sell_timestamp'],integrated_exit_price=x['sell_price_decimal'],cash_release_timestamp=x['sell_source_assumed_available_at'],cash_release_per_share=x['sell_price_decimal'],historical_cash_release_authorized=True,assumed_available_at=x['sell_source_assumed_available_at'],overnight_obligation=False);return r
 r.update(eod_eligible=True,eod_intent_timestamp=cut,eod_order_type='MARKET',eod_sor=True,eod_execution_condition='DAY',eod_remaining_quantity='FULL_REMAINING_SYMBOLIC')
 why=None
 if day<'2024-11-05':why='SESSION_CONTRACT_CONTRADICTION'
 elif not p.get('sourceHash'):why='LINEAGE_UNAVAILABLE'
 by={}
 for a in p['today']:
  if len(a)!=7:continue
  if 15*60+20<=a[0]<15*60+25 or a[0]==15*60+30:
   if a[0] in by and by[a[0]]!=a:why='LINEAGE_CONFLICT'
   by[a[0]]=a
 if why:r.update(eod_fill_status='EOD_UNEXECUTED_FAIL_CLOSED',final_exit_status='EOD_UNEXECUTED_FAIL_CLOSED',reason=why);return r
 regular=[by[m] for m in sorted(by) if 15*60+20<=m<15*60+25];auct=[by[15*60+30]] if 15*60+30 in by else []
 good=[a for a in regular if valid(a,False)];ga=[a for a in auct if valid(a,True)]
 r.update(regular_source_N=len(regular),valid_regular_source_N=len(good),exact_auction_source_N=len(auct),valid_auction_source_N=len(ga))
 selected=good[:1] or ga[:1]
 if not selected:
  r.update(eod_fill_status='EOD_UNEXECUTED_FAIL_CLOSED',final_exit_status='EOD_UNEXECUTED_FAIL_CLOSED',reason='INVALID_SOURCE' if by else 'UNKNOWN_NO_ADMISSIBLE_SOURCE');return r
 a=selected[0];use_auction=not good;price=F(str(a[4] if use_auction else a[1]));effective=price*F(9995,10000);t=clock(day,a[0]);known=clock(day,a[0]+1)
 r.update(eod_fill_status='FILLED_REFERENCE',eod_fill_source_type='EXACT_1530_JQUANTS_AUCTION' if use_auction else 'FIRST_POST_INTENT_REGULAR_RAW_OPEN',eod_fill_source_timestamp=t,eod_reference_price=textnum(price),eod_effective_price=textnum(effective),final_exit_status='FILLED_REFERENCE',integrated_exit_reason='EOD_1530_AUCTION' if use_auction else 'EOD_1520_POST_INTENT_TRADE',integrated_exit_timestamp=t,integrated_exit_price=textnum(effective),cash_release_timestamp=known,cash_release_per_share=textnum(effective),historical_cash_release_authorized=True,assumed_available_at=known,overnight_obligation=False)
 return r
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--primary-inputs',type=Path,required=True);ap.add_argument('--primary-rows',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();i=args.inputs
 checked=[]
 for name,mf,member in [('entry.jsonl.gz','entry_manifest.json','FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'),('raw_paths.json.gz','entry_manifest.json','SAVED_INPUTS/raw_paths_selected.json.gz'),('exit_v3.jsonl.gz','exit_manifest.json','REPLAY_ROWS.jsonl.gz')]:
  rec=json.loads((i/mf).read_text())['components'][member];b=(i/name).read_bytes();assert H(b)==rec['sha256'] and len(b)==rec['bytes'];checked.append({'role':name,'sha256':H(b),'original_manifest_match':True})
 E={r['watch_key']:r for r in rows(i/'entry.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'};X={r['watch_key']:r for r in rows(i/'exit_v3.jsonl.gz')};P=json.loads(gzip.decompress((i/'raw_paths.json.gz').read_bytes()));assert len(E)==len(X)==len(P)==1600 and set(E)==set(X)==set(P)
 result=[];buy_errors=sell_errors=cash_errors=identity_errors=0
 for k in sorted(E):
  e=E[k];x=X[k];p=P[k]
  identity_errors+=e['fill_timestamp']!=x['entry_timestamp'] or e['fill_price']!=x['entry_fill_price']
  entry_source=[a for a in p['today'] if a[0]==e['fill_minute']];assert len(entry_source)==1
  buy=F(str(entry_source[0][1]))*F(10005,10000);buy_errors+=abs(buy-F(str(e['fill_price'])))>F(1,10**8)
  if x['sell_status']=='FILLED':
   orig=[a for a in p['today'] if a[0]==x['sell_minute']];assert len(orig)==1
   raw=orig[0][1] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else orig[0][4]
   sell_errors+=F(str(raw))*F(9995,10000)!=F(x['sell_price_decimal'])
  r=reconstruct(e,x,p)
  if r['final_exit_status']=='FILLED_REFERENCE':
   q=100;starting=F(1000000);debit=q*F(str(e['fill_price']));credit=q*F(r['integrated_exit_price']);endpoint=starting-debit+credit;trade=q*(F(r['integrated_exit_price'])-F(str(e['fill_price'])));cash_errors+=endpoint-starting!=trade
   assert r['cash_release_timestamp']>r['integrated_exit_timestamp'] and r['broker_commission_JPY']==0
  result.append(r)
 args.output.mkdir(parents=True,exist_ok=True);out=args.output/'INDEPENDENT_ROWS.jsonl.gz';assert not out.exists();out.write_bytes(gzip.compress(b''.join(J(r)+b'\n' for r in result),mtime=0))
 # No Primary output accessed until independent rows have been materialized.
 primary={r['entry_id']:r for r in rows(args.primary_rows)};numeric={'frozen_exit_price','eod_reference_price','eod_effective_price','integrated_exit_price','cash_release_per_share'};mismatches=[]
 for r in result:
  for f,v in r.items():
   u=primary[r['entry_id']][f];equal=(F(v)==F(u)) if f in numeric and v is not None and u is not None else v==u
   if not equal:mismatches.append({'entry_id':r['entry_id'],'field':f})
 parent_paths=json.loads(gzip.decompress((args.primary_inputs/'raw_paths.json.gz').read_bytes()));raw_mismatch=sum(P[k]!=parent_paths[k] for k in P)
 (args.output/'MISMATCHES.json').write_text(json.dumps(mismatches,indent=2)+'\n')
 agg={'saved_at_jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'Primary_imported':False,'independent_source_route':'Original attached V2/V3 gzip components independently verified against original manifests; no Primary projection copied','arithmetic':'Fraction rational arithmetic; independent time-window and auction matching','source_hash_checks':checked,'candidate_N':len(result),'compared_fields_N':len(result[0]),'compared_values_N':len(result)*len(result[0]),'identity_mismatch_N':identity_errors+len(set(primary)^set(E)),'row_field_mismatch_N':len(mismatches),'raw_path_mismatch_N':raw_mismatch,'BUY_arithmetic_mismatch_N':buy_errors,'Frozen_SELL_arithmetic_mismatch_N':sell_errors,'closed_reference_cash_endpoint_vs_trade_PnL_mismatch_N':cash_errors,'closed_reference_checked_N':sum(r['final_exit_status']=='FILLED_REFERENCE' for r in result),'status':'PASS_IMPLEMENTATION_AGREEMENT_NOT_C2_PASS' if not(mismatches or raw_mismatch or buy_errors or sell_errors or cash_errors or identity_errors) else 'FAIL'}
 (args.output/'INDEPENDENT_AUDIT.json').write_text(json.dumps(agg,ensure_ascii=False,indent=2,sort_keys=True)+'\n');print(json.dumps({k:v for k,v in agg.items() if k not in ['source_hash_checks','independent_source_route']},ensure_ascii=False));assert agg['status'].startswith('PASS')
if __name__=='__main__':main()
