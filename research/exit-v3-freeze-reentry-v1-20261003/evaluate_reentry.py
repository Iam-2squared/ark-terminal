"""Post-seal evaluation. Original bucket and FIRST return come from saved V3."""
from work_io import *
from verify_signal_reuse import lines,write_lines
from reused_clock import active_minutes
import csv,math,statistics
from collections import Counter,defaultdict

BUCKETS=['<1%','1–<2%','2–<3%','3–<4%','4–<5%','>=5%','UNKNOWN']
REASONS=['UP_STRUCTURE_REVERSED','UP_STRUCTURE_RETIRED_BY_RANGE','LOCAL_UP_STRUCTURE_GUARD_BROKEN','SESSION_CLOSE','UNRESOLVED']
def stats(values):
    v=[x for x in values if x is not None and math.isfinite(x)]
    return {'N':len(v),'mean':statistics.fmean(v) if v else None,'median':statistics.median(v) if v else None,'sum':math.fsum(v) if v else None}
def rate(n,d):return 100*n/d if d else None
def flatten(d,prefix=''):
    out={}
    for k,v in d.items():
        if isinstance(v,dict):out.update(flatten(v,prefix+k+'_'))
        elif not isinstance(v,list):out[prefix+k]=v
    return out
def table(name,records):
    write(ROOT/(name+'.json'),records);flat=[flatten(x) for x in records];fields=list(dict.fromkeys(k for r in flat for k in r))
    with (ROOT/(name+'.csv')).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(flat)

def trade_metrics(t,base):
    filled=t['sell_status']=='FILLED';first=t['entry_type']=='FIRST'
    ret=base['realized_return_pct'] if first else 100*(t['sell_price']/t['buy_price']-1) if filled else None
    holding=base['holding_active_minutes'] if first else active_minutes(t['session'],t['buy_minute'],t['sell_minute']) if filled else None
    rawret=100*(t['sell_raw_price']/t['buy_raw_price']-1) if filled and t['buy_raw_price'] is not None and t['sell_raw_price'] is not None else None
    previous=t.get('previous_sell_minute');intent=t['buy_intent'].get('minute',t['buy_intent'].get('intent_minute'))
    return dict(t,realized_return_pct=ret,holding_active_minutes=holding,return_before_execution_adjustment_pct=rawret,execution_adjustment_drag_pp=rawret-ret if rawret is not None and ret is not None else None,previous_EXIT_to_BUY_intent_active_minutes=active_minutes(t['session'],previous,intent) if previous is not None else None,previous_EXIT_to_BUY_fill_active_minutes=active_minutes(t['session'],previous,t['buy_minute']) if previous is not None else None)

def watch_metrics(key,trades,baseline):
    known=[t['realized_return_pct'] for t in trades if t['realized_return_pct'] is not None];complete=len(known)==len(trades)
    simple=math.fsum(known) if complete else None
    compound=100*(math.prod(1+r/100 for r in known)-1) if complete else None
    first=baseline['realized_return_pct']
    return {'watch_key':key,'session':baseline['session'],'symbol':baseline['symbol'],'original_FIRST_exclusive_bucket':baseline['exclusive_bucket'],'original_FIRST_observed_Entry_to_High_pct':baseline['observed_entry_to_high_pct'],'original_remaining_source_complete':baseline['remaining_source_complete'],'total_trades_N':len(trades),'reentry_fills_N':len(trades)-1,'sell_filled_trades_N':len(known),'unresolved_trades_N':len(trades)-len(known),'all_trades_realized':complete,'FIRST_only_V3_realized_return_pct':first,'simple_cumulative_realized_return_pct':simple,'simple_reentry_incremental_return_pp':simple-first if complete and first is not None else None,'same_watch_compounded_return_pct':compound,'known_partial_sum_pct':math.fsum(known) if known else None,'FIRST_only_V3_holding_active_minutes':baseline['holding_active_minutes'],'FIRST_exit_reason':baseline['exit_reason'],'FIRST_sell_status':baseline['sell_status'],'total_holding_active_minutes':sum(t['holding_active_minutes'] for t in trades) if complete else None,'total_execution_adjustment_drag_pp':math.fsum(t['execution_adjustment_drag_pp'] for t in trades) if complete and all(t['execution_adjustment_drag_pp'] is not None for t in trades) else None}

def group(label,ww,trades):
    common=[w for w in ww if w['all_trades_realized'] and w['FIRST_only_V3_realized_return_pct'] is not None]
    a=stats(w['FIRST_only_V3_realized_return_pct'] for w in common);b=stats(w['simple_cumulative_realized_return_pct'] for w in common)
    return {'original_FIRST_Entry_to_High':label,'watch_N':len(ww),'common_completely_realized_watch_N':len(common),'unresolved_watch_N':len(ww)-len(common),'FIRST_only_all_saved_V3':stats(w['FIRST_only_V3_realized_return_pct'] for w in ww),'FIRST_only_V3_common':a,'reentry_included_simple_common':b,'delta_mean_pp':b['mean']-a['mean'] if common else None,'delta_group_median_pp':b['median']-a['median'] if common else None,'paired_incremental_return':stats(w['simple_reentry_incremental_return_pp'] for w in common),'same_watch_compounded':stats(w['same_watch_compounded_return_pct'] for w in common),'watches_with_reentry_N':sum(w['reentry_fills_N']>=1 for w in ww),'avg_total_trades_per_watch':stats(w['total_trades_N'] for w in ww),'reentry_trades_N':sum(w['reentry_fills_N'] for w in ww),'reentry_trade_return':stats(t['realized_return_pct'] for t in trades if t['entry_type']=='REENTRY'),'first_exit_reentry_rate_pct':rate(sum(w['reentry_fills_N']>=1 for w in ww),sum(w['FIRST_sell_status']=='FILLED' for w in ww)),'first_exit_filled_denominator_N':sum(w['FIRST_sell_status']=='FILLED' for w in ww),'complete_watch_additional_simple_return_sum_pp':stats(w['simple_reentry_incremental_return_pp'] for w in common)['sum'],'total_holding_active_minutes':stats(w['total_holding_active_minutes'] for w in common),'original_complete_raw_remaining_path_watch_N':sum(w['original_remaining_source_complete'] for w in ww)}

def trade_group(label,tt):
    known=[t['realized_return_pct'] for t in tt if t['realized_return_pct'] is not None]
    return {'trade_index':label,'trade_N':len(tt),'sell_filled_N':len(known),'unresolved_N':len(tt)-len(known),'realized_return_pct':stats(known),'positive_N':sum(r>0 for r in known),'nonpositive_N':sum(r<=0 for r in known),'positive_rate_pct':rate(sum(r>0 for r in known),len(known)),'holding_active_minutes':stats(t['holding_active_minutes'] for t in tt),'exit_reason_N':dict(Counter(t['exit_reason'] for t in tt)),'EXIT_to_reentry_fill_active_minutes':stats(t['previous_EXIT_to_BUY_fill_active_minutes'] for t in tt)}

def run():
    receipt=read(ROOT/'REPLAY_RECEIPT.json');assert receipt['status']=='PERSISTENT_REENTRY_V1_REPLAY_COMPLETE'
    assert sha(PRIVATE/'TRADE_LEDGER.jsonl.gz')==receipt['trade_ledger_sha256']
    saved=read(ROOT/'REENTRY_CONTRACT_FREEZE_RECEIPT.json');assert sha(P3/'ECONOMICS_ROWS.jsonl.gz')==saved['frozen_input_hashes']['V3_ECONOMICS_ROWS.jsonl.gz']
    baseline={r['watch_key']:r for r in lines(P3/'ECONOMICS_ROWS.jsonl.gz')}
    ledger=list(lines(PRIVATE/'TRADE_LEDGER.jsonl.gz'));trades=[trade_metrics(t,baseline[t['watch_key']]) for t in ledger]
    by=defaultdict(list)
    for t in trades:by[t['watch_key']].append(t)
    assert len(by)==len(baseline)==1600 and set(by)==set(baseline)
    watches=[watch_metrics(k,by[k],b) for k,b in baseline.items()]
    episodes=list(lines(PRIVATE/'FLAT_EPISODES.jsonl.gz'))
    for e in episodes:
        fill=e['previous_sell_minute'];reset=e['reset'];cross=e['fresh_cross'];buy=e['buy_fill'];day=e['session']
        e.update(EXIT_to_reset_active_minutes=active_minutes(day,fill,reset['minute']) if reset is not None else None,reset_to_cross_active_minutes=active_minutes(day,reset['minute'],cross['minute']) if cross is not None else None,EXIT_to_cross_active_minutes=active_minutes(day,fill,cross['minute']) if cross is not None else None,EXIT_to_reentry_fill_active_minutes=active_minutes(day,fill,buy['buy_minute']) if buy is not None and buy['buy_status']=='FILLED' else None)
    write_lines(PRIVATE/'TRADE_ECONOMICS_ROWS.jsonl.gz',trades);write_lines(PRIVATE/'WATCH_ECONOMICS_ROWS.jsonl.gz',watches);write_lines(PRIVATE/'FLAT_EPISODE_ECONOMICS.jsonl.gz',episodes)
    primary=[]
    for b in BUCKETS:
        ww=[w for w in watches if w['original_FIRST_exclusive_bucket']==b];keys={w['watch_key'] for w in ww};tt=[t for t in trades if t['watch_key'] in keys]
        primary.append(group(b,ww,tt))
    table('EXCLUSIVE_ORIGINAL_ENTRY_HIGH_PRIMARY',primary)
    table('WINNER_GE5_MULTI_LEG',[primary[5]])
    table('WINNER_2_TO_5_MULTI_LEG',primary[2:5])
    target=[w for w in watches if w['original_FIRST_exclusive_bucket'] in BUCKETS[2:5]];keys={w['watch_key'] for w in target}
    table('COMBINED_2_TO_5_MULTI_LEG',[group('2–<5% combined',target,[t for t in trades if t['watch_key'] in keys])])
    table('ALL_WATCH_ECONOMICS',[group('ALL_1600',watches,trades)])
    table('TRADE_INDEX',[trade_group(label,[t for t in trades if (t['trade_index']>=4 if label=='#4+' else t['trade_index']==int(label[1]))]) for label in ['#1 FIRST','#2 first REENTRY','#3 second REENTRY','#4+']])
    sessions={w['session'] for w in watches};daily=[]
    for day in sorted(sessions):
        ww=[w for w in watches if w['session']==day];daily.append({'session':day,'Frozen_FIRST_watch_N':len(ww),'reentry_fills_N':sum(w['reentry_fills_N'] for w in ww),'watches_with_reentry_N':sum(w['reentry_fills_N']>0 for w in ww)})
    table('SESSION_ACTIVITY',daily)
    activity={'saved_at_jst':now(),'watch_N':1600,'sessions_denominator':'All distinct sessions of the 1,600 Frozen FIRST ENTRY watches; zero-Reentry sessions included','session_N':len(sessions),'watches_with_0_reentry_N':sum(w['reentry_fills_N']==0 for w in watches),'watches_with_GE1_reentry_N':sum(w['reentry_fills_N']>=1 for w in watches),'watches_with_GE2_reentry_N':sum(w['reentry_fills_N']>=2 for w in watches),'watches_with_GE3_reentry_N':sum(w['reentry_fills_N']>=3 for w in watches),'total_reentry_intents_N':sum(e['fresh_cross'] is not None for e in episodes),'total_reentry_fills_N':len(trades)-1600,'reentry_trades_per_watch':stats(w['reentry_fills_N'] for w in watches),'total_trades_per_watch':stats(w['total_trades_N'] for w in watches),'total_trades_per_watch_distribution':dict(Counter(w['total_trades_N'] for w in watches)),'reentry_fills_per_session':stats(r['reentry_fills_N'] for r in daily),'sessions_with_0_reentry_N':sum(r['reentry_fills_N']==0 for r in daily),'max_reentry_count_observed':max(w['reentry_fills_N'] for w in watches),'EXIT_to_reset_active_minutes':stats(e['EXIT_to_reset_active_minutes'] for e in episodes),'reset_to_fresh_cross_active_minutes':stats(e['reset_to_cross_active_minutes'] for e in episodes),'EXIT_fill_to_next_reentry_intent_active_minutes':stats(e['EXIT_to_cross_active_minutes'] for e in episodes),'EXIT_fill_to_next_reentry_fill_active_minutes':stats(e['EXIT_to_reentry_fill_active_minutes'] for e in episodes),'safety':SAFETY}
    write(ROOT/'REENTRY_ACTIVITY.json',activity)
    prev=[]
    for r in REASONS:
        ee=[e for e in episodes if e['previous_exit_reason']==r];flat=[e for e in ee if e['previous_sell_status']=='FILLED']
        n=sum(e['buy_fill'] is not None and e['buy_fill']['buy_status']=='FILLED' for e in ee)
        prev.append({'previous_exit_reason':r,'episodes_N':len(ee),'flat_after_sell_fill_episodes_N':len(flat),'reset_observed_N':sum(e['reset'] is not None for e in ee),'fresh_cross_N':sum(e['fresh_cross'] is not None for e in ee),'reentry_filled_N':n,'reentry_rate_pct':rate(n,len(flat)),'post_SESSION_CLOSE_reentry_N':n if r=='SESSION_CLOSE' else 0})
    table('PREVIOUS_EXIT_REENTRY',prev)
    table('REENTRY_EXIT_REASON',[trade_group(r,[t for t in trades if t['entry_type']=='REENTRY' and t['exit_reason']==r]) for r in REASONS])
    re=[t for t in trades if t['entry_type']=='REENTRY'];filled=[t for t in trades if t['sell_status']=='FILLED'];allret=[t['realized_return_pct'] for t in filled]
    churn={'saved_at_jst':now(),'total_entry_trades_N':len(trades),'total_completed_round_trips_N':len(filled),'unresolved_open_trades_N':len(trades)-len(filled),'reentry_completed_round_trips_N':sum(t['sell_status']=='FILLED' for t in re),'all_trade_nonpositive_return_N':sum(r<=0 for r in allret),'reentry_trade_nonpositive_return_N':sum(t['realized_return_pct'] is not None and t['realized_return_pct']<=0 for t in re),'holding_LE_active_minutes_all':{str(k):sum(t['holding_active_minutes'] is not None and t['holding_active_minutes']<=k for t in trades) for k in [1,3,5]},'holding_LE_active_minutes_reentry':{str(k):sum(t['holding_active_minutes'] is not None and t['holding_active_minutes']<=k for t in re) for k in [1,3,5]},'EXIT_to_reentry_LE_active_minutes':{str(k):sum(t['previous_EXIT_to_BUY_fill_active_minutes']<=k for t in re) for k in [1,3,5]},'nominal_adverse_bps_per_round_trip':10,'nominal_adverse_buy_bps_sum_across_trade_legs':5*len(trades),'nominal_adverse_sell_bps_sum_across_filled_trade_legs':5*len(filled),'cost_scope':'Sums across trade legs are exposure diagnostics, not a portfolio or cash return. Exact before/after drag uses matching raw Open/closing prices; no sizing assumed.','all_trade_raw_before_adjustment_return_pct':stats(t['return_before_execution_adjustment_pct'] for t in trades),'all_trade_execution_adjusted_return_pct':stats(t['realized_return_pct'] for t in trades),'all_trade_exact_adjustment_drag_pp':stats(t['execution_adjustment_drag_pp'] for t in trades),'reentry_raw_before_adjustment_return_pct':stats(t['return_before_execution_adjustment_pct'] for t in re),'reentry_execution_adjusted_return_pct':stats(t['realized_return_pct'] for t in re),'reentry_exact_adjustment_drag_pp':stats(t['execution_adjustment_drag_pp'] for t in re),'watch_cost_drag_pp':stats(w['total_execution_adjustment_drag_pp'] for w in watches),'cooldown_or_cap_added':False,'safety':SAFETY}
    write(ROOT/'CHURN_AND_COST.json',churn)
    result={'saved_at_jst':now(),'status':'PERSISTENT_REENTRY_V1_EVALUATION_COMPLETE','watch_N':1600,'original_exclusive_denominator_sum':sum(g['watch_N'] for g in primary),'FIRST_saved_economics_reused_N':1600,'FIRST_baseline_performance_recalculation_N':0,'future_bucket_decision_reads':0,'watch_economics_sha256':sha(PRIVATE/'WATCH_ECONOMICS_ROWS.jsonl.gz'),'trade_economics_sha256':sha(PRIVATE/'TRADE_ECONOMICS_ROWS.jsonl.gz'),'null_not_zero_imputed':True,'primary':'Simple cumulative per-watch return; common completely realized watch comparison','secondary':'Theoretical compounded same-watch; not Portfolio or Capital','safety':SAFETY}
    write(ROOT/'EVALUATION_RECEIPT.json',result)
    print(json.dumps({'receipt':result,'primary':[{'bucket':g['original_FIRST_Entry_to_High'],'watch_N':g['watch_N'],'common_N':g['common_completely_realized_watch_N'],'FIRST':g['FIRST_only_V3_common'],'simple':g['reentry_included_simple_common'],'delta_mean':g['delta_mean_pp'],'delta_median':g['delta_group_median_pp']} for g in primary],'activity':activity,'churn':churn}))

if __name__=='__main__':run()
