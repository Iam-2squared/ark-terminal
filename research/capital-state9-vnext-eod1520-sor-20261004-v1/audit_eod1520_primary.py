"""Research-only downstream adapter. Never writes Frozen inputs or sends orders."""
import argparse, gzip, hashlib, json, math
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
from collections import Counter, defaultdict

POLICY='EOD_LIQUIDATION_1520_SOR_MARKET_V1'
ENTRY_FIELDS=('watch_key','session','symbol','entry_status','fill_minute','fill_timestamp','fill_price')
EXIT_FIELDS=('watch_key','sell_status','sell_minute','sell_timestamp','sell_price_decimal','sell_raw_price','sell_source','sell_source_assumed_available_at')
def digest(b):return hashlib.sha256(b).hexdigest()
def canonical(o):return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def iso(session,m):return (datetime.fromisoformat(session+'T00:00:00+09:00')+timedelta(minutes=m)).isoformat()
def number(x):return Decimal(str(x))
def raw_valid(a,auction=False):
 if len(a)!=7 or not all(isinstance(v,(float,int)) and math.isfinite(v) for v in a):return False
 m,o,h,l,c,v,z=a
 if m!=int(m) or min(o,h,l,c)<=0 or v<=0 or z<=0:return False
 if not l<=min(o,c)<=max(o,c)<=h:return False
 return (o==h==l==c) if auction else True
def intent(entry,prior,already_committed=False,remaining_quantity=None):
 """Accepts causal position/prior-fill facts only, never the future path."""
 if already_committed:return {'committed':False,'reason':'EOD_ALREADY_COMMITTED'}
 if remaining_quantity is not None and remaining_quantity<=0:return {'committed':False,'reason':'POSITION_NOT_OPEN'}
 if entry['fill_minute']>=920:return {'committed':False,'reason':'ENTRY_AT_OR_AFTER_INTENT'}
 before=(prior.get('sell_status')=='FILLED' and prior.get('sell_timestamp') is not None and datetime.fromisoformat(prior['sell_timestamp'])<datetime.fromisoformat(iso(entry['session'],920)))
 if before:return {'committed':False,'reason':'PRIOR_FROZEN_EXIT'}
 return {'committed':True,'reason':'OPEN_AT_1520','policy':POLICY,'timestamp':iso(entry['session'],920),'side':'SELL','order_type':'MARKET','SOR':True,'execution_condition':'DAY','quantity':'FULL_REMAINING_SYMBOLIC','trigger':0,'transmitted':False}
def adapt(entry,prior,path):
 ee={k:entry[k] for k in ENTRY_FIELDS};xx={k:prior.get(k) for k in EXIT_FIELDS}
 it=intent(ee,xx)
 row={'entry_id':ee['watch_key'],'session':ee['session'],'symbol':ee['symbol'],'entry_timestamp':ee['fill_timestamp'],'entry_effective_price':str(number(ee['fill_price'])),'entry_fields_sha256':digest(canonical(ee)),'frozen_exit_fields_sha256':digest(canonical(xx)),'frozen_exit_status':xx['sell_status'],'frozen_exit_timestamp':xx['sell_timestamp'],'frozen_exit_price':xx['sell_price_decimal'],'frozen_exit_source':xx['sell_source'],'frozen_exit_assumed_available_at':xx['sell_source_assumed_available_at'],'eod_policy_id':POLICY,'eod_eligible':it['committed'],'eod_intent':it,'eod_intent_timestamp':it.get('timestamp'),'eod_order_type':'MARKET' if it['committed'] else None,'eod_sor':True if it['committed'] else None,'eod_execution_condition':'DAY' if it['committed'] else None,'eod_remaining_quantity':'FULL_REMAINING_SYMBOLIC' if it['committed'] else None,'eod_fill_status':'NOT_APPLIED','eod_fill_source_type':None,'eod_fill_source_timestamp':None,'eod_reference_price':None,'eod_effective_price':None,'final_exit_status':None,'integrated_exit_reason':None,'integrated_exit_timestamp':None,'integrated_exit_price':None,'cash_release_timestamp':None,'cash_release_per_share':None,'historical_cash_release_authorized':False,'runtime_cash_release_certified':False,'known_at_status':'ACTUAL_ARRIVAL_UNKNOWN_REFERENCE_ONLY','assumed_available_at':None,'overnight_obligation':True,'broker_commission_JPY':0,'execution_factor':'0.9995','source_lineage':{'frozen_path_sourceHash':path.get('sourceHash'),'original_saved_raw_path':True},'reason':None,'regular_source_N':0,'valid_regular_source_N':0,'exact_auction_source_N':0,'valid_auction_source_N':0}
 if it['reason']=='PRIOR_FROZEN_EXIT':
  row.update(final_exit_status='FILLED_REFERENCE',integrated_exit_reason='FROZEN_EXIT_V3_PRIOR',integrated_exit_timestamp=xx['sell_timestamp'],integrated_exit_price=xx['sell_price_decimal'],cash_release_timestamp=xx['sell_source_assumed_available_at'],cash_release_per_share=xx['sell_price_decimal'],historical_cash_release_authorized=True,assumed_available_at=xx['sell_source_assumed_available_at'],overnight_obligation=False)
  return row
 if not it['committed']:
  row.update(final_exit_status='EOD_UNEXECUTED_FAIL_CLOSED',reason=it['reason']);return row
 if ee['session']<'2024-11-05':
  row.update(eod_fill_status='EOD_UNEXECUTED_FAIL_CLOSED',final_exit_status='EOD_UNEXECUTED_FAIL_CLOSED',reason='SESSION_CONTRACT_CONTRADICTION');return row
 if not path.get('sourceHash'):
  row.update(eod_fill_status='EOD_UNEXECUTED_FAIL_CLOSED',final_exit_status='EOD_UNEXECUTED_FAIL_CLOSED',reason='LINEAGE_UNAVAILABLE');return row
 raw=[a for a in path['today'] if len(a)==7 and (920<=a[0]<925 or a[0]==930)]
 by=defaultdict(list)
 for a in raw:by[a[0]].append(a)
 if any(len({canonical(a) for a in aa})>1 for aa in by.values()):
  row.update(eod_fill_status='EOD_UNEXECUTED_FAIL_CLOSED',final_exit_status='EOD_UNEXECUTED_FAIL_CLOSED',reason='LINEAGE_CONFLICT');return row
 regular=[aa[0] for m,aa in sorted(by.items()) if 920<=m<925]
 auction=by.get(930,[])
 vr=[a for a in regular if raw_valid(a)]
 va=[a for a in auction if raw_valid(a,True)]
 row.update(regular_source_N=len(regular),valid_regular_source_N=len(vr),exact_auction_source_N=len(auction),valid_auction_source_N=len(va))
 chosen=vr[0] if vr else va[0] if va else None
 if chosen is None:
  row.update(eod_fill_status='EOD_UNEXECUTED_FAIL_CLOSED',final_exit_status='EOD_UNEXECUTED_FAIL_CLOSED',reason='INVALID_SOURCE' if raw else 'UNKNOWN_NO_ADMISSIBLE_SOURCE');return row
 auction_used=not bool(vr)
 ref=number(chosen[4] if auction_used else chosen[1]);effective=ref*Decimal('0.9995')
 m=chosen[0];t=iso(ee['session'],m);known=iso(ee['session'],m+1)
 source='EXACT_1530_JQUANTS_AUCTION' if auction_used else 'FIRST_POST_INTENT_REGULAR_RAW_OPEN'
 row['source_lineage'].update(exact_row_sha256=digest(canonical(chosen)),source_minute=m)
 row.update(eod_fill_status='FILLED_REFERENCE',eod_fill_source_type=source,eod_fill_source_timestamp=t,eod_reference_price=str(ref),eod_effective_price=str(effective),final_exit_status='FILLED_REFERENCE',integrated_exit_reason='EOD_1530_AUCTION' if auction_used else 'EOD_1520_POST_INTENT_TRADE',integrated_exit_timestamp=t,integrated_exit_price=str(effective),cash_release_timestamp=known,cash_release_per_share=str(effective),historical_cash_release_authorized=True,assumed_available_at=known,overnight_obligation=False)
 return row
def main():
 a=argparse.ArgumentParser();a.add_argument('--inputs',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--precommit',type=Path,required=True);a.add_argument('--basis-head',required=True);args=a.parse_args()
 assert args.precommit.exists(); policy=json.loads(args.precommit.read_text());assert policy['policy_id']==POLICY and not policy['new_1520_source_coverage_or_outcomes_seen']
 args.output.mkdir(parents=True,exist_ok=True)
 for p in ['EOD1520_ADAPTER_ROWS.jsonl.gz','SOURCE_COVERAGE.json']:assert not (args.output/p).exists(),p
 entries=[r for r in (json.loads(s) for s in gzip.decompress((args.inputs/'entry.jsonl.gz').read_bytes()).decode().splitlines()) if r['entry_status']=='FIRST_ENTRY']
 exits={r['watch_key']:r for r in (json.loads(s) for s in gzip.decompress((args.inputs/'exit_v3.jsonl.gz').read_bytes()).decode().splitlines())}
 paths=json.loads(gzip.decompress((args.inputs/'raw_paths.json.gz').read_bytes()))
 assert len(entries)==len(exits)==len(paths)==1600 and len({r['watch_key'] for r in entries})==1600 and set(exits)==set(paths)=={r['watch_key'] for r in entries}
 rows=[adapt(r,exits[r['watch_key']],paths[r['watch_key']]) for r in sorted(entries,key=lambda r:r['watch_key'])]
 gz=gzip.compress(b''.join(canonical(r)+b'\n' for r in rows),mtime=0);(args.output/'EOD1520_ADAPTER_ROWS.jsonl.gz').write_bytes(gz)
 needed=[r for r in rows if r['eod_eligible']];old39=[r for r in rows if r['frozen_exit_status']=='UNRESOLVED'];nf=[r for r in rows if r['final_exit_status']!='FILLED_REFERENCE']
 sessions=sorted({r['session'] for r in rows})
 late=[r for r in rows if r['reason']=='ENTRY_AT_OR_AFTER_INTENT'];missing=[r for r in nf if r['eod_eligible']]
 counts={'candidate_N':len(rows),'sessions_N':len(sessions),'distinct_symbols_N':len({r['symbol'] for r in rows}),'prior_EXIT_before1520_N':sum(r['integrated_exit_reason']=='FROZEN_EXIT_V3_PRIOR' for r in rows),'open_at1520_N':len(needed),'regular_post_intent_fill_N':sum(r['integrated_exit_reason']=='EOD_1520_POST_INTENT_TRADE' for r in rows),'auction_fallback_fill_N':sum(r['integrated_exit_reason']=='EOD_1530_AUCTION' for r in rows),'EOD_fill_N':sum(r['eod_fill_status']=='FILLED_REFERENCE' for r in rows),'no_fill_exception_N':len(missing),'final_admission_unresolved_N':len(nf),'old39_N':len(old39),'old39_same_day_closed_N':sum(r['eod_fill_status']=='FILLED_REFERENCE' for r in old39),'old39_unresolved_N':sum(r['final_exit_status']!='FILLED_REFERENCE' for r in old39),'same_day_reference_closed_N':sum(r['final_exit_status']=='FILLED_REFERENCE' for r in rows),'unresolved_candidate_obligation_N':sum(r['overnight_obligation'] for r in rows),'actual_funded_overnight_positions_N':None,'entry_after_or_at_intent_N':len(late),'late_entry_original_FILLED_N':sum(r['frozen_exit_status']=='FILLED' for r in late),'late_entry_original_UNRESOLVED_N':sum(r['frozen_exit_status']=='UNRESOLVED' for r in late),'source_missing_symbols_N':len({r['symbol'] for r in missing}),'source_missing_sessions_N':len({r['session'] for r in missing}),'late_entry_sessions_N':len({r['session'] for r in late})}
 agg={'counts':counts,'missing_reason_taxonomy':dict(Counter(r['reason'] for r in nf)),'old39_reason_taxonomy':dict(Counter(r['reason'] or r['integrated_exit_reason'] for r in old39)),'known_at':dict(Counter(r['known_at_status'] for r in rows)),'historical_reference_cash_authorized_N':sum(r['historical_cash_release_authorized'] for r in rows),'runtime_cash_release_certified_N':0,'execution_factor':'0.9995','broker_commission_JPY':0,'source_type':'Frozen unadjusted J-Quants1m full saved path; selected records only used as outcome after intent','session_start':sessions[0],'session_end':sessions[-1],'precommit_sha256':digest(args.precommit.read_bytes()),'basis_head':args.basis_head,'adapter_rows_sha256':digest(gz),'no_price_imputation':True,'identities_excluded':0,'Frozen_writes':0,'performance_replay_executed':False,'new_market_data_requests':0,'allocation_executed':False,'session_aggregate':[{'session_index':i+1,'candidate_N':sum(r['session']==s for r in rows),'prior_N':sum(r['session']==s and r['integrated_exit_reason']=='FROZEN_EXIT_V3_PRIOR' for r in rows),'eod_needed_N':sum(r['session']==s and r['eod_eligible'] for r in rows),'regular_N':sum(r['session']==s and r['integrated_exit_reason']=='EOD_1520_POST_INTENT_TRADE' for r in rows),'auction_N':sum(r['session']==s and r['integrated_exit_reason']=='EOD_1530_AUCTION' for r in rows),'no_fill_N':sum(r['session']==s and r['final_exit_status']!='FILLED_REFERENCE' for r in rows)} for i,s in enumerate(sessions)]}
 (args.output/'SOURCE_COVERAGE.json').write_text(json.dumps(agg,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
 (args.output/'UNEXECUTED_ROWS.jsonl.gz').write_bytes(gzip.compress(b''.join(canonical(r)+b'\n' for r in nf),mtime=0))
 print(json.dumps({'counts':counts,'missing_reasons':agg['missing_reason_taxonomy'],'old39':agg['old39_reason_taxonomy'],'rows_sha256':digest(gz)},ensure_ascii=False))
if __name__=='__main__':main()
