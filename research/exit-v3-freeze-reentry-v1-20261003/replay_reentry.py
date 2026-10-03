"""One all-watch Re-entry replay. FIRST EXIT comes only from frozen saved rows."""
from collections import defaultdict,Counter
from work_io import *
from verify_signal_reuse import lines,write_lines
from fresh_cross import FreshCross
from reentry_fill import buy_fill
from local_guard import GuardedLifecycle
from reused_fill import fill_from_source
from reused_clock import regular_end,session_close,stamp,valid_raw
import gzip

SELL_KEYS=['sell_status','sell_minute','sell_timestamp','sell_price','sell_price_decimal','sell_raw_price','sell_source','sell_source_start','sell_source_assumed_available_at','sell_adjustment_bps','commission','exit_reason','closing_fallback_for_locked_intent','unresolved_reason','unfilled_intent_reason']

def trace_path(key):return TRACE/'FULL_TRACE'/(key.replace('|','_')+'.jsonl.gz')

def first_trade(e,b,raw,baseline_sha):
    m=e['fill_minute'];prices=[r[1] for r in raw if int(r[0])==m and valid_raw(r)]
    return {'watch_key':e['watch_key'],'session':e['session'],'symbol':e['symbol'],'trade_index':1,'entry_type':'FIRST','buy_intent':dict(e['first_intent']),'buy_status':'FILLED','buy_minute':m,'buy_timestamp':e['fill_timestamp'],'buy_price':e['fill_price'],'buy_raw_price':prices[0] if len(prices)==1 else None,'buy_adjustment_bps':5,'buy_source':'EXACT_FROZEN_FIRST_ENTRY_FILL','FIRST_saved_outcome_reused':True,'FIRST_saved_outcome_sha256':baseline_sha,'exit_intent':b['exit_intent'],'planned_close_intent_minute':b['planned_close_intent_minute'],'decision_N':0,'FIRST_saved_decision_N':b['decision_N'],'EXIT_baseline_decision_replay_N':0,'post_exit_decision_N':0,**{k:b[k] for k in SELL_KEYS if k in b}}

def reentry_trade(key,day,symbol,index,intent,fill,rows,raw,previous,receipt):
    life=GuardedLifecycle(fill['buy_minute'],regular_end(day))
    target=PRIVATE/'EXIT_DECISION_TRACE'/f'{key.replace("|","_")}_{index}.jsonl.gz'
    target.parent.mkdir(parents=True,exist_ok=True)
    entry_snapshot=None;metadata=[]
    for row in rows:
        m=row['bar_end_minute']
        if m<fill['buy_minute']:life.prefix(row);continue
        if m>regular_end(day):break
        if entry_snapshot is None:
            if m!=fill['buy_minute']:raise RuntimeError('BLOCKED_REENTRY_LINEAGE_MISMATCH: absent entry snapshot')
            entry_snapshot={'minute':m,'primary':row['path']['Primary_or_null'],'context':row['state']['context'],'observed':row['state']['current_semantics_observed'],'segment':row['path']['causal_segment_id']}
        out,record=life.observe(row);metadata.append(record)
        if out is not None:break
    if entry_snapshot is None:raise RuntimeError('BLOCKED_REENTRY_LINEAGE_MISMATCH: no position trace')
    write_lines(target,metadata)
    base=life.base;guard=life.guard
    sell=fill_from_source({'session':day,'fill_minute':fill['buy_minute']},base.intent,raw)
    t={'watch_key':key,'session':day,'symbol':symbol,'trade_index':index,'entry_type':'REENTRY','buy_intent':dict(intent),**fill,'FIRST_saved_outcome_reused':False,'entry_snapshot':entry_snapshot,'exit_intent':base.intent,'planned_close_intent_minute':regular_end(day) if base.intent is None else None,'first_arm_minute':base.first_arm_minute,'arm_at_entry':base.arm_at_entry,'arm_events':base.arm_events,'observations_suspended':base.suspensions,'phase_at_last_decision':base.phase,'suspended_at_last_decision':base.suspended,'decision_N':base.decisions,'post_exit_decision_N':0,'exit_last3_distinct_primary':list(base.primary_sequence),'last_decision_snapshot':base.last_snapshot,'local_guard_established_ever':guard.established_ever,'local_guard_creation_N':sum(e['type']=='LOCAL_GUARD_CREATED' for e in guard.events),'local_guard_tighten_N':sum(e['type']=='LOCAL_GUARD_TIGHTENED' for e in guard.events),'local_guard_events':guard.events,'previous_exit_reason':previous['exit_reason'],'previous_sell_minute':previous['sell_minute'],'previous_sell_intent_minute':previous['exit_intent']['minute'] if previous['exit_intent'] else previous['planned_close_intent_minute'],**sell}
    receipt.append({'watch_key':key,'trade_index':index,'file':str(target.relative_to(PRIVATE)),'sha256':sha(target),'bytes':target.stat().st_size,'decision_N':base.decisions,'source_trace_sha256':sha(trace_path(key))})
    return t

def simulate_watch(e,baseline,signals,raw,rows,baseline_sha,exit_receipts):
    day=e['session'];key=e['watch_key'];trades=[first_trade(e,baseline,raw,baseline_sha)]
    episodes=[];flat_trace=[]
    while True:
        previous=trades[-1]
        episode={'watch_key':key,'session':day,'after_trade_index':previous['trade_index'],'previous_exit_reason':previous['exit_reason'],'previous_sell_status':previous['sell_status'],'previous_sell_minute':previous['sell_minute'],'reset':None,'fresh_cross':None,'buy_fill':None,'entry_decision_N':0}
        if previous['sell_status']!='FILLED':episode['terminal_status']='UNRESOLVED_POSITION';episodes.append(episode);break
        if previous['exit_reason']=='SESSION_CLOSE' or previous['sell_minute']>=regular_end(day):
            episode['terminal_status']='SESSION_CLOSE_TERMINAL';episodes.append(episode);break
        machine=FreshCross(previous['sell_minute'])
        for signal in signals:
            # No score is read during a position, pending sell, same sell raw minute,
            # or the earlier flat episodes. The saved grid itself persists to close.
            if signal['minute']<=previous['sell_minute'] or signal['minute']>regular_end(day):continue
            intent,metadata=machine.observe(signal)
            flat_trace.append({'watch_key':key,'after_trade_index':previous['trade_index'],'sell_fill_minute':previous['sell_minute'],**metadata})
            if intent is not None:break
        episode.update(reset=machine.reset,fresh_cross=machine.intent,entry_decision_N=machine.decision_N)
        if machine.intent is None:
            episode['terminal_status']='NO_FRESH_CROSS_BEFORE_SESSION_CLOSE';episodes.append(episode);break
        fill=buy_fill(day,machine.intent,raw);episode['buy_fill']=fill;episode['terminal_status']=fill['buy_status'];episodes.append(episode)
        if fill['buy_status']!='FILLED':break
        if fill['buy_minute']<=previous['sell_minute']:raise RuntimeError('BLOCKED_REENTRY_POSITION_OVERLAP: same-bar or earlier buy')
        if fill['buy_minute']<machine.intent['minute']:raise RuntimeError('BLOCKED_REENTRY_CAUSALITY: buy before intent')
        # Fresh EXIT v3 position metadata only; saved market prefix is causal input.
        t=reentry_trade(key,day,e['symbol'],len(trades)+1,machine.intent,fill,rows,raw,previous,exit_receipts)
        trades.append(t)
    return trades,episodes,flat_trace

def run():
    lock=PRIVATE/'RUN_ONCE.json'
    if lock.exists():raise RuntimeError('REENTRY_REPLAY_ALREADY_STARTED: one primary replay only')
    freeze=read(ROOT/'EXIT_V3_OFFICIAL_FREEZE_RECEIPT.json');contract=read(ROOT/'REENTRY_CONTRACT_FREEZE_RECEIPT.json')
    assert freeze['ExitFrozen'] and contract['primary_replay_started'] is False
    assert sha(ROOT/'CONTRACT.md')==contract['contract_sha256']
    for f,pin in contract['decision_code_hashes'].items():assert sha(ROOT/f)==pin,f
    assert read(ROOT/'R0_ACTUAL_RESULT_GET.json')['actual_GET']['commit']['sha']==read(ROOT/'R0_ACTUAL_RESULT_GET.json')['saved_result_head']
    sig=read(ROOT/'FROZEN_SIGNAL_REUSE_RECEIPT.json');assert sha(PRIVATE/'FROZEN_P1_Q70_SIGNAL_ROWS.jsonl.gz')==sig['signal_projection_sha256']
    tm=read(TRACE/'MANIFEST.json')['components'];rawpath=TRACE/'SAVED_INPUTS/raw_paths_selected.json.gz'
    assert sha(rawpath)==tm['SAVED_INPUTS/raw_paths_selected.json.gz']['sha256']
    with gzip.open(rawpath,'rt') as f:raw=json.load(f)
    baseline={r['watch_key']:r for r in lines(P3/'REPLAY_ROWS.jsonl.gz')};baseline_sha=sha(P3/'REPLAY_ROWS.jsonl.gz')
    assert baseline_sha==contract['frozen_input_hashes']['V3_REPLAY_ROWS.jsonl.gz']
    entries=[r for r in lines(TRACE/'FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if r['entry_status']=='FIRST_ENTRY']
    # Use a minimal identity view; original future evaluator fields do not enter decisions.
    headers=[{k:r[k] for k in ['watch_key','session','symbol','first_intent','fill_minute','fill_price','fill_timestamp']} for r in entries]
    signals=defaultdict(list)
    for s in lines(PRIVATE/'FROZEN_P1_Q70_SIGNAL_ROWS.jsonl.gz'):signals[s['watch_key']].append(s)
    assert len(headers)==1600 and {x['watch_key'] for x in headers}==set(baseline)==set(signals)
    write(lock,{'saved_at_jst':now(),'status':'STARTED','primary_reentry_replay_invocation_N':1,'contract_sha256':contract['contract_sha256'],'decision_code_hashes':contract['decision_code_hashes']})
    ledger=[];episodes=[];flat_trace=[];exit_receipts=[];watch_receipts=[]
    for e in headers:
        key=e['watch_key'];path=trace_path(key)
        assert sha(path)==tm['FULL_TRACE/'+path.name]['sha256'],'BLOCKED_REENTRY_LINEAGE_MISMATCH'
        trace=list(lines(path))
        ts,eps,ds=simulate_watch(e,baseline[key],signals[key],raw[key]['today'],trace,baseline_sha,exit_receipts)
        ledger.extend(ts);episodes.extend(eps);flat_trace.extend(ds)
        watch_receipts.append({'watch_key':key,'total_trades_N':len(ts),'reentry_fills_N':len(ts)-1,'reentry_intents_N':sum(p['fresh_cross'] is not None for p in eps),'flat_entry_decision_N':len(ds),'source_trace_sha256':sha(path)})
    for name,values in [('TRADE_LEDGER.jsonl.gz',ledger),('FLAT_EPISODES.jsonl.gz',episodes),('FLAT_DECISION_TRACE.jsonl.gz',flat_trace),('WATCH_REPLAY_RECEIPTS.jsonl.gz',watch_receipts)]:write_lines(PRIVATE/name,values)
    write(PRIVATE/'EXIT_DECISION_TRACE_RECEIPTS.json',exit_receipts)
    result={'saved_at_jst':now(),'status':'PERSISTENT_REENTRY_V1_REPLAY_COMPLETE','watch_N':1600,'FIRST_saved_outcomes_reused_N':1600,'FIRST_EXIT_decision_replay_N':0,'new_reentry_intents_N':sum(e['fresh_cross'] is not None for e in episodes),'new_reentry_fills_N':len(ledger)-1600,'total_trades_N':len(ledger),'reentry_sell_filled_N':sum(t['sell_status']=='FILLED' for t in ledger if t['entry_type']=='REENTRY'),'reentry_unresolved_N':sum(t['sell_status']=='UNRESOLVED' for t in ledger if t['entry_type']=='REENTRY'),'flat_entry_decision_N':len(flat_trace),'Entry_decisions_while_position_open_N':0,'Entry_decisions_same_sell_raw_minute_N':0,'post_exit_decision_N':0,'session_close_post_reentry_N':0,'future_bucket_decision_reads':0,'primary_reentry_replay_invocation_N':1,'Frozen_V3_reentry_position_lifecycle_evaluations_N':len(ledger)-1600,'State9_Path_reconstruction_N':0,'trade_ledger_sha256':sha(PRIVATE/'TRADE_LEDGER.jsonl.gz'),'flat_episode_sha256':sha(PRIVATE/'FLAT_EPISODES.jsonl.gz'),'flat_decision_trace_sha256':sha(PRIVATE/'FLAT_DECISION_TRACE.jsonl.gz'),'baseline_reuse_sha256':baseline_sha,'safety':SAFETY}
    write(ROOT/'REPLAY_RECEIPT.json',result)
    lockdata=read(lock);lockdata.update(status='COMPLETED',completed_at_jst=now(),ledger_sha256=result['trade_ledger_sha256']);write(lock,lockdata)
    print(json.dumps(result))

if __name__=='__main__':run()
