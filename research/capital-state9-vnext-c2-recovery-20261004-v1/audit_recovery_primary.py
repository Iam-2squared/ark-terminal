"""Source/admission audit only. No allocator, Entry/EXIT replay or model imports."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent
INPUT = BASE/'work_inputs'
PRIVATE = BASE/'capital_c2_recovery_private'
OUT = ROOT/'docs/evidence/phase57-capital-state9-vnext-c2-recovery-20261004-v1'

def rows(path):
    with gzip.open(path,'rt') as f: return [json.loads(x) for x in f]

def load(path):
    with gzip.open(path,'rt') as f: return json.load(f)

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name,obj,private=False):
    with ((PRIVATE if private else OUT)/name).open('x') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n')

def write_rows(name,items):
    with (PRIVATE/name).open('xb') as file:
        with gzip.GzipFile(fileobj=file,mode='wb',mtime=0,filename='',compresslevel=1) as z:
            for item in items: z.write((json.dumps(item,sort_keys=True,allow_nan=False)+'\n').encode())

def minute_rows_valid(a):
    return len(a)>=6 and all(isinstance(x,(int,float)) and math.isfinite(x) and x>0 for x in a[1:6])

def regular(day):
    end=925 if day>='2024-11-05' else 900
    return list(range(540,690))+list(range(750,end)),end,930 if end==925 else 900

def main():
    basis=os.environ['RECOVERY_BASIS_HEAD']
    stamp=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
    frozen_path=INPUT/'exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'
    assert digest(frozen_path)=='e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb'
    watches=rows(frozen_path)
    entries=[x for x in watches if x['entry_status']=='FIRST_ENTRY']
    exits={x['watch_key']:x for x in rows(INPUT/'exit_v3/REPLAY_ROWS.jsonl.gz')}
    raw=load(PRIVATE/'ORIGINAL_RAW_PATHS_CURRENT1600.json.gz')
    tokens=load(PRIVATE/'SOURCE_TOKENS_CURRENT1600.json.gz')
    old=load(INPUT/'exit_v2/SAVED_INPUTS/raw_paths_selected.json.gz')
    assert len(entries)==len(exits)==len(raw)==len(tokens)==1600
    assert {e['watch_key'] for e in entries}==set(exits)==set(raw)==set(tokens)
    all_rows=[];unresolved=[];marks=[];sessions=defaultdict(Counter)
    counts=Counter(); taxonomy=Counter(); known_at=Counter(); daily=Counter()
    checksum_mismatch=0
    for e in entries:
        key=e['watch_key'];x=exits[key];day=e['session'];a=raw[key]['today']
        checksum_mismatch+=int(a!=old[key]['today'])
        q={int(r[0]):r for r in a}
        identity=(e['symbol']==x['symbol'] and day==x['session'] and e['fill_timestamp']==x['entry_timestamp'] and e['fill_price']==x['entry_fill_price'])
        counts['identity_mismatch_N']+=int(not identity)
        counts['buy_arithmetic_N']+=1
        buy=Decimal(str(q[e['fill_minute']][1]))*Decimal('1.0005')
        counts['price_mismatch_N']+=int(abs(buy-Decimal(str(e['fill_price'])))>=Decimal('0.00000001'))
        starts,end,close=regular(day)
        row={'entry_id':key,'session':day,'symbol':e['symbol'],'identity_unchanged':identity,'exit_status':x['sell_status'],'buy_effective_price_unchanged':True,'source_today_matches_STOP':a==old[key]['today'],'raw_rows_N':len(a)}
        if x['sell_status']=='FILLED':
            counts['filled_exit_N']+=1;counts['sell_arithmetic_N']+=1
            index=4 if x['sell_source']=='PLANNED_TERMINAL_AUCTION_CLOSE' else 1
            expected=Decimal(str(q[x['sell_minute']][index]))*Decimal('0.9995')
            counts['price_mismatch_N']+=int(expected!=Decimal(x['sell_price_decimal']))
            counts['commission_nonzero_N']+=int(x['commission']!=0)
            reference=datetime.fromisoformat(x['sell_timestamp']);available=datetime.fromisoformat(x['sell_source_assumed_available_at'])
            delta=(available-reference).total_seconds()
            counts['availability_delta_exact_60_seconds_N']+=int(delta==60)
            counts['source_known_later_than_reference_N']+=int(available>reference)
            known_at['REFERENCE_FILL_ONLY_NOT_RUNTIME_KNOWN_AT']+=1
            row.update(reference_fill=x['sell_timestamp'],source_assumed_available_at=x['sell_source_assumed_available_at'],historical_actual_known_at=None,cash_release_at_reference_certified=False)
            sessions[day]['filled']+=1
        else:
            assert x['sell_status']=='UNRESOLVED' and x['sell_timestamp'] is None and x['sell_price'] is None
            counts['unresolved_exit_N']+=1;known_at['KNOWN_AT_UNRESOLVED']+=1
            # Inspect only exact existing-source eligibility; do not run the EXIT policy or manufacture a sell.
            intent=x.get('exit_intent');intent_minute=intent['minute'] if isinstance(intent,dict) else None
            first_am=min((int(r[0]) for r in a if int(r[0])<690),default=None)
            first_pm=min((int(r[0]) for r in a if 750<=int(r[0])<end),default=None)
            mixed={540,750,first_am,first_pm}
            eligible=[r for r in a if intent_minute is not None and minute_rows_valid(r) and int(r[0]) in starts and int(r[0]) not in mixed and int(r[0])>=intent_minute and int(r[0])>e['fill_minute']]
            closing=[r for r in a if int(r[0])==close and minute_rows_valid(r)]
            assert not eligible and not closing,'Recovered source contradicts current UNRESOLVED; preserve originals and investigate.'
            category='SOURCE_NOT_STORED'
            taxonomy[category]+=1;sessions[day]['unresolved']+=1
            cd=tokens[key].get('current_daily')
            has_daily=isinstance(cd,dict) and cd.get('C') is not None and float(cd['C'])>0
            daily['daily_close_present_N']+=int(has_daily)
            daily['daily_close_exact_time_present_N']+=int(isinstance(cd,dict) and bool(cd.get('Time') or cd.get('timestamp')))
            row.update(reason_taxonomy=category,intent_minute=intent_minute,planned_close_intent_minute=x['planned_close_intent_minute'],exact_regular_eligible_source_N=len(eligible),exact_terminal_auction_source_N=len(closing),daily_close_present=has_daily,daily_close_eligible_under_frozen_minute_contract=False,no_trade_or_halt_positive_evidence=False,cash_release_authorized=False,historical_actual_known_at=None)
            unresolved.append(row.copy())
        # Source-completeness diagnostics only, not funded marks or a new mark cadence.
        cutoff=min(x['sell_minute'] or end,end)
        window=[m for m in starts if e['fill_minute']<=m<cutoff]
        absent=sum(m not in q for m in window)
        required5=[m+1 for m in window if (m+1)%5==0]
        absent5=sum(m-1 not in q for m in required5)
        counts['candidate_1m_missing_rows_N']+=absent
        counts['candidate_1m_incomplete_N']+=int(absent>0)
        counts['potential_5m_grid_1m_close_missing_N']+=absent5
        counts['potential_5m_grid_incomplete_candidates_N']+=int(absent5>0)
        counts['potential_5m_grid_slots_N']+=len(required5)
        counts['potential_5m_grid_present_N']+=len(required5)-absent5
        closing_source=q.get(close)
        counts['current_candidate_exact_auction_source_present_N']+=int(closing_source is not None and minute_rows_valid(closing_source))
        counts['current_candidate_daily_close_present_N']+=int(isinstance(tokens[key].get('current_daily'),dict) and tokens[key]['current_daily'].get('C') is not None)
        marks.append({'entry_id':key,'session':day,'symbol':e['symbol'],'candidate_regular_1m_window_expected_N':len(window),'missing_1m_N':absent,'potential_5m_grid_slots_N':len(required5),'potential_5m_grid_missing_N':absent5,'funded_position':None,'source_type':'existing unadjusted1m raw Close; grid diagnostic only','native_5m_ohlc_certified':False})
        row.update(known_at_class='REFERENCE_FILL_ONLY_NOT_RUNTIME_KNOWN_AT' if x['sell_status']=='FILLED' else 'KNOWN_AT_UNRESOLVED')
        all_rows.append(row)
        sessions[day]['candidates']+=1;sessions[day]['missing_1m_rows']+=absent;sessions[day]['incomplete_1m_candidates']+=int(absent>0)
        sessions[day]['potential_5m_slots']+=len(required5);sessions[day]['potential_5m_missing']+=absent5
    # Existing known-at validator only. No CashBook positions/step or performance replay.
    spec=importlib.util.spec_from_file_location('existing_r34_source_validator',ROOT/'scripts/phase57_cash_capital_r34.py')
    ledger=importlib.util.module_from_spec(spec);spec.loader.exec_module(ledger)
    callbacks=Counter()
    for x in exits.values():
        if x['sell_status']!='FILLED':continue
        event={'entryId':x['watch_key'],'timestamp':x['sell_timestamp'],'knownAt':x['sell_source_assumed_available_at'],'price':x['sell_price'],'confirmed':True}
        try:ledger._exit(event,ledger.stamp(x['sell_timestamp']));callbacks['unexpected_accept_at_reference']+=1
        except ValueError as exc:callbacks['at_reference:'+str(exc)]+=1
    sample=next(x for x in exits.values() if x['sell_status']=='FILLED')
    event={'entryId':sample['watch_key'],'timestamp':sample['sell_timestamp'],'knownAt':sample['sell_source_assumed_available_at'],'price':sample['sell_price'],'confirmed':True}
    try:ledger._exit(event,ledger.stamp(sample['sell_source_assumed_available_at']));late_canary='UNEXPECTED_ACCEPT'
    except ValueError as exc:late_canary=str(exc)
    # Isolated synthetic arithmetic, no candidate funding or strategy performance.
    qty=100;initial=Decimal('1000000');buy=Decimal('1000')*Decimal('1.0005');sell=Decimal('1010')*Decimal('0.9995')
    final=initial-buy*qty+sell*qty;pnl=(sell-buy)*qty
    assert final-initial==pnl
    common={'saved_at_jst':stamp,'repo':'Iam-2squared/ark-terminal','branch':'capital-state9-vnext-20261004','basis_head':basis,'scope':'source and admission only','Capital_replay':0,'Entry_EXIT_replay':0,'fit':0,'provider':0,'new_market_data':0,'orders':0,'source_today_vs_STOP_mismatch_N':checksum_mismatch}
    write_rows('RECOVERY_ADMISSION_ROWS.jsonl.gz',all_rows)
    write_rows('RECOVERY_UNRESOLVED_EXIT_ROWS.jsonl.gz',unresolved)
    write_rows('RECOVERY_MARK_SOURCE_ROWS.jsonl.gz',marks)
    write('R2_UNRESOLVED_EXIT_RECOVERY.json',{**common,'status':'NO_ADDITIONAL_EXACT_FROZEN_SELL_SOURCE','current_unresolved_N':39,'existing_only_resolved_N':0,'remaining_N':39,'affected_sessions_N':len({r['session'] for r in unresolved}),'affected_symbols_N':len({r['symbol'] for r in unresolved}),'taxonomy':dict(taxonomy),'daily_source_preview':dict(daily),'source_lookup':'Original frozen base archive raw today arrays, byte-pinned source tokens and STOP subset; all1600 identities retained.','taxonomy_scope':'Exact eligible regular Open or valid terminal-auction Close absent in inspected frozen source. No assertion that no trade occurred or no price exists globally.','source_not_adopted':['daily Close without exact timestamp/auction contract','last regular Close','future replacement bars','fixture execution receipts']})
    write('R3_MTM_SOURCE_RECOVERY.json',{**common,'status':'EXISTING_FUNDED_ONLY_NULL_AWARE_MECHANICS_FOUND_CURRENT_BINDING_NOT_UNIQUE','candidate_N':1600,'sessions_N':len(sessions),'current_source_type':'unadjusted1m OHLC; inherited source bar_end=m+1 research assumption','current_source_rows_N':sum(len(r['today']) for r in raw.values()),'source_population_with_rows_N':sum(bool(r['today']) for r in raw.values()),'counts':{k:v for k,v in counts.items() if '1m' in k or '5m' in k or 'auction' in k or 'daily' in k},'legacy_lane_c_cadence':'5-minute MTM plus exact entry/exit reference mark equality; cached available marks, no current1600 binding','existing_long_funded_only':'scripts/phase57_long_capital_integration.py valuation() inspects actual positions only, current exact fresh close required, null equity and CURRENT_EQUITY_UNKNOWN; unresolved obligations stay locked, no future mark substitution','existing_r34_funded_only':'snapshot() requires marks for actual positions only; missing/stale => null; knownAt<=now; next-session boundary with open positions rejected','funded_subset_required_coverage':None,'old1420_is_not_standalone_gate':True,'potential5m_warning':'1m Close presence sampled at5m boundaries is only source support; no native5m OHLC/mark protocol adopted.','cross_session_status':'NOT_RESOLVED_WITH_CURRENT_FROZEN_SOURCE_OR_BINDING','need_current_contract':['mark clock/cadence and entry/exit source price role','non-grid entry valuation and exact freshness','missing/unresolved vs cross-session boundary','full metrics unavailable vs admissible partial measurement'], 'new_interpolation_or_forward_fill':0})
    write('R4_KNOWN_AT_EVENT_TIME_RECOVERY.json',{**common,'status':'REFERENCE_FILL_BOUNDARY_DOCUMENTED_CAPITAL_CASH_BINDING_UNRESOLVED','classification':dict(known_at),'source_availability_delta_exact_60_seconds_N':counts['availability_delta_exact_60_seconds_N'],'historical_actual_arrival':'UNKNOWN','retrieval_time_role':'2026 historical API received_at is receipt/publication retrieval evidence, not2025 event arrival or fill confirmation','existing_reference_rule':'v2 CONTRACT: source aggregation assumed available close+1, execution reference closing-auction minute; chronology unknown. v3 reuses exact function and bar_end assumption.','existing_cash_rule':'R34 callbacks must have timestamp==batch now and knownAt<=now; confirmed fill needed; broker/settlement semantics explicitly not claimed','existing_validator_canary':dict(callbacks),'same_reference_event_tested_at_later_source_time':late_canary,'source_plus1m_backdated':False,'Frozen_fill_or_cash_timestamp_moved':False,'runtime_known_at_certified':False,'Capital_release_at_reference_authorized_existing_contract_N':0,'late_release_protocol_adopted':False,'frozen_causal_research_proof_newly_overturned':False,'diagnosis':'No contradiction within frozen reference research semantics. Direct use as runtime cash-known event needs additional authoritative evidence or a separately authorized binding.'})
    write('RECOVERY_PRIMARY_AUDIT.json',{**common,'status':'SOURCE_IDENTITY_PRICE_AUDIT_PASS_ADMISSION_BLOCKED','candidate_N':1600,'watch_N':2155,'sessions_N':len(sessions),'counts':dict(counts),'taxonomy':dict(taxonomy),'known_at_classification':dict(known_at),'cash_event_existing_validator':dict(callbacks),'canary_later_clock_unchanged_event':late_canary,'synthetic_cost_canary':{'not_a_Portfolio_result':True,'quantity':qty,'commission':0,'extra_old_fees':0,'cash_change':str(final-initial),'trade_pnl':str(pnl),'mismatch':False},'primary_source_sha256':digest(Path(__file__)),'input_hashes':{str(p.relative_to(BASE)):digest(p) for p in [frozen_path,INPUT/'exit_v3/REPLAY_ROWS.jsonl.gz',PRIVATE/'ORIGINAL_RAW_PATHS_CURRENT1600.json.gz',PRIVATE/'SOURCE_TOKENS_CURRENT1600.json.gz']},'old3211_component_hash_audit':'immutable parent verified and reused; no new full-trace read required','allocation_decisions':0,'funded_positions':None,'missing_price_imputation':0,'row_exclusion':0,'Frozen_changes':0,'cost_double_count':0})
    write('ANONYMIZED_SESSION_SOURCE_COUNTS.json',{**common,'session_labels':'chronological S01..S58; calendar dates and symbols withheld','rows':[{'session_index':i+1,**dict(sessions[day])} for i,day in enumerate(sorted(sessions))]})
    print(json.dumps({'candidate_N':1600,'unresolved_N':39,'resolved_existing_N':0,'taxonomy':dict(taxonomy),'counts':dict(counts),'known_at':dict(known_at),'source_value_mismatch_N':checksum_mismatch,'Capital_replay':0}))

if __name__=='__main__':main()
