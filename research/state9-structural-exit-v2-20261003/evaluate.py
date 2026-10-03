"""Post-replay economics only. Future High never enters decision modules."""
import collections, csv, gzip, json, math, statistics
from settings import *

METRICS = ['realized_return_pct','observed_entry_to_high_pct','MFE_realization_pct','peak_giveback_pp','peak_price_giveback_pct','pre_sell_observed_peak_giveback_pp','later_missed_upside_pct','later_missed_upside_entry_basis_pp','exit_to_later_high_active_minutes','intent_to_later_high_active_minutes','holding_active_minutes','entry_to_arm_active_minutes','arm_to_exit_active_minutes','entry_to_high_active_minutes','protected_tighten_N','PULLBACK_run_N','RISE_STOP_run_N']

def statistics_of(values):
    a = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    return {'N':len(a),'mean':statistics.fmean(a) if a else None,'median':statistics.median(a) if a else None}

def group_summary(label,rr):
    stats = {k:statistics_of(r.get(k) for r in rr) for k in METRICS}
    r = [x['realized_return_pct'] for x in rr if x['realized_return_pct'] is not None]
    negative = [x for x in r if x<0]
    before = [x['exit_before_final_observed_high'] for x in rr if x['exit_before_final_observed_high'] is not None]
    return {'group':label,'denominator_N':len(rr),'sell_filled_N':sum(x['sell_status']=='FILLED' for x in rr),'unresolved_N':sum(x['sell_status']=='UNRESOLVED' for x in rr),'High_known_N':sum(x['observed_entry_to_high_pct'] is not None for x in rr),'full_remaining_source_complete_N':sum(x['remaining_source_complete'] for x in rr),'positive_N':sum(x>0 for x in r),'positive_rate_pct':100*sum(x>0 for x in r)/len(r) if r else None,'negative_N':len(negative),'negative_return':statistics_of(negative),'worst_return_pct':min(r) if r else None,'below_minus1_N':sum(x < -1 for x in r),'below_minus2_N':sum(x < -2 for x in r),'winner_ge3_N':sum(x['observed_entry_to_high_pct'] is not None and x['observed_entry_to_high_pct']>=3 for x in rr),'winner_ge5_N':sum(x['observed_entry_to_high_pct'] is not None and x['observed_entry_to_high_pct']>=5 for x in rr),'session_close_reason_N':sum(x['exit_reason']=='SESSION_CLOSE' for x in rr),'session_close_fill_source_N':sum(x['sell_source']=='PLANNED_TERMINAL_AUCTION_CLOSE' for x in rr),'structural_intent_N':sum(x['exit_intent'] is not None for x in rr),'exit_before_final_high_denominator_N':len(before),'exit_before_final_high_N':sum(before),'exit_before_final_high_rate_pct':100*sum(before)/len(before) if before else None,'metrics':stats}

def flat(summary):
    d={k:v for k,v in summary.items() if not isinstance(v,dict)}
    d.update({f'negative_return_{a}':v for a,v in summary['negative_return'].items()})
    for k,st in summary['metrics'].items():
        d.update({k+'_'+a:v for a,v in st.items()})
    return d

def table(name,groups):
    save(HERE/(name+'.json'),groups)
    rr=[flat(g) for g in groups]
    with (HERE/(name+'.csv')).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)

def enrich(r,entry,source):
    day=r['session']; fp=r['entry_fill_price']; fm=r['entry_minute']
    good=[x for x in source if valid_raw(x) and fm < int(x[0]) <= session_close(day)]
    high=max((x[2] for x in good),default=None)
    peak=min((int(x[0]) for x in good if x[2]==high),default=None)
    last_tie=max((int(x[0]) for x in good if x[2]==high),default=None)
    mfe=100*(high/fp-1) if high is not None else None
    assert (mfe is None and entry['remaining_upside_pct'] is None) or (mfe is not None and abs(mfe-entry['remaining_upside_pct']) < 1e-10), 'FROZEN_ENTRY_HIGH_PARITY'
    filled=r['sell_status']=='FILLED'; sell=r['sell_price']; sm=r['sell_minute']
    ret=100*(sell/fp-1) if filled else None
    later=[x for x in good if filled and int(x[0])>sm]
    lh=max((x[2] for x in later),default=None)
    lm=min((int(x[0]) for x in later if x[2]==lh),default=None)
    held=[x for x in good if filled and int(x[0])<sm]
    ph=max((x[2] for x in held),default=None)
    arm=r['first_arm_minute']; intent=r['exit_intent']['minute'] if r['exit_intent'] else regular_end(day)
    d=dict(r)
    d.update(observed_entry_to_high_pct=mfe,observed_high=high,final_observed_high_minute=peak,latest_tied_observed_high_minute=last_tie,remaining_source_complete=entry['remaining_source_complete'],realized_return_pct=ret,MFE_realization_pct=100*ret/mfe if filled and mfe is not None and mfe>0 else None,peak_giveback_pp=mfe-ret if filled and mfe is not None else None,peak_price_giveback_pct=100*(high-sell)/high if filled and high is not None else None,pre_sell_observed_peak_giveback_pp=100*(ph/fp-1)-ret if filled and ph is not None else None,later_observed_high=lh,later_observed_high_minute=lm,later_missed_upside_pct=max(0,100*(lh/sell-1)) if lh is not None else None,later_missed_upside_entry_basis_pp=max(0,100*(lh-sell)/fp) if lh is not None else None,exit_before_final_observed_high=sm<peak if filled and peak is not None else None,intent_before_final_observed_high=intent<peak if peak is not None else None,exit_to_later_high_active_minutes=active_minutes(day,sm,lm) if lm is not None else None,intent_to_later_high_active_minutes=active_minutes(day,intent,lm) if lm is not None else None,holding_active_minutes=active_minutes(day,fm,sm) if filled else None,entry_to_arm_active_minutes=active_minutes(day,fm,arm) if arm is not None else None,arm_to_exit_active_minutes=active_minutes(day,arm,intent) if arm is not None else None,arm_to_fill_active_minutes=active_minutes(day,arm,sm) if arm is not None and filled else None,entry_to_high_active_minutes=active_minutes(day,fm,peak) if peak is not None else None,observed_High_unknown=mfe is None)
    return d

def run():
    ee={r['watch_key']:r for r in entries()}; raw=load(INPUT/'base/raw_paths_selected.json.gz')
    rr=[enrich(r,ee[r['watch_key']],raw[r['watch_key']]['today']) for r in rows(PRIVATE/'REPLAY_ROWS.jsonl.gz')]
    assert len(rr)==1600
    target=PRIVATE/'ECONOMICS_ROWS.jsonl.gz'
    with target.open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as gz:
        for r in rr:gz.write(jsonline(r))
    table('ALL_ENTRY_ECONOMICS',[group_summary('ALL_1600_FROZEN_ENTRY',rr)])
    cum=[group_summary('>='+str(k)+'%', [r for r in rr if r['observed_entry_to_high_pct'] is not None and r['observed_entry_to_high_pct']>=k]) for k in range(1,6)]
    table('WINNER_CUMULATIVE',cum)
    exclusive=[]
    for label,lower,upper in [('<1%',-math.inf,1),('1–<2%',1,2),('2–<3%',2,3),('3–<4%',3,4),('4–<5%',4,5),('>=5%',5,math.inf)]:
        exclusive.append(group_summary(label,[r for r in rr if r['observed_entry_to_high_pct'] is not None and lower<=r['observed_entry_to_high_pct']<upper]))
    exclusive.append(group_summary('UNKNOWN_HIGH',[r for r in rr if r['observed_entry_to_high_pct'] is None]))
    table('WINNER_EXCLUSIVE',exclusive)
    table('WINNER_GE3_DETAILED',[cum[2]])
    table('WINNER_GE5_DETAILED',[cum[4]])
    armed=[group_summary(label,[r for r in rr if r['armed_ever']==flag]) for label,flag in [('armed',True),('never_armed',False)]]
    table('ARMED_VS_NEVER_ARMED',armed)
    reasons=[group_summary(reason,[r for r in rr if r['exit_reason']==reason]) for reason in ['UP_STRUCTURE_REVERSED','UP_STRUCTURE_RETIRED_BY_RANGE','SESSION_CLOSE','UNRESOLVED']]
    for g in reasons:
        subset=[r for r in rr if r['exit_reason']==g['group']]
        g['exit_path_sequence_N']=dict(collections.Counter('>'.join(r['exit_last3_distinct_primary']) or 'NO_OBSERVED_SEQUENCE' for r in subset))
    table('EXIT_REASON_DECOMPOSITION',reasons)
    facets=[]
    keys=sorted({(r['entry_snapshot']['primary'],r['entry_snapshot']['context']) for r in rr},key=str)
    for primary,context in keys:
        subset=[r for r in rr if (r['entry_snapshot']['primary'],r['entry_snapshot']['context'])==(primary,context)]
        g=group_summary(f'primary={primary};context={context}',subset)
        g.update(entry_primary=primary,entry_context=context,armed_N=sum(r['armed_ever'] for r in subset),arm_rate_pct=100*sum(r['armed_ever'] for r in subset)/len(subset))
        facets.append(g)
    table('ENTRY_PRIMARY_CONTEXT',facets)
    coverage={'Entry_N':1600,'entry_UP_context_N':sum(r['arm_at_entry'] for r in rr),'first_UP_context_after_entry_N':sum(r['armed_ever'] and not r['arm_at_entry'] for r in rr),'armed_total_N':sum(r['armed_ever'] for r in rr),'never_armed_N':sum(not r['armed_ever'] for r in rr),'EXIT_A_reversal_intent_N':sum(r['exit_intent'] is not None and r['exit_intent']['reason']=='UP_STRUCTURE_REVERSED' for r in rr),'EXIT_B_range_retirement_intent_N':sum(r['exit_intent'] is not None and r['exit_intent']['reason']=='UP_STRUCTURE_RETIRED_BY_RANGE' for r in rr),'observation_suspended_position_N':sum(r['observation_suspended_ever'] for r in rr),'observation_suspension_events_N':sum(len(r['observations_suspended']) for r in rr),'rearm_events_N':sum(max(0,len(r['arm_events'])-1) for r in rr),'session_close_reason_N':sum(r['exit_reason']=='SESSION_CLOSE' for r in rr),'session_close_fill_source_N':sum(r['sell_source']=='PLANNED_TERMINAL_AUCTION_CLOSE' for r in rr),'closing_fallback_locked_structural_intent_N':sum(r['closing_fallback_for_locked_intent'] for r in rr),'unresolved_N':sum(r['sell_status']=='UNRESOLVED' for r in rr),'protected_tighten_events_N':sum(r['protected_tighten_N'] for r in rr),'PULLBACK_runs_N':sum(r['PULLBACK_run_N'] for r in rr),'RISE_STOP_runs_N':sum(r['RISE_STOP_run_N'] for r in rr),'entry_to_arm_active_minutes':statistics_of(r['entry_to_arm_active_minutes'] for r in rr),'arm_to_exit_active_minutes':statistics_of(r['arm_to_exit_active_minutes'] for r in rr),'table_counts_are_not_all_disjoint':'entry_UP + first_UP = armed; armed + never =1600; suspensions overlap armed; intent counts differ from fill-source counts'}
    save(HERE/'LIFECYCLE_COVERAGE.json',coverage)
    save(HERE/'EVALUATION_RECEIPT.json',{'saved_at_jst':now(),'Entry_N':1600,'High_known_N':sum(r['observed_entry_to_high_pct'] is not None for r in rr),'High_unknown_N':sum(r['observed_entry_to_high_pct'] is None for r in rr),'observed_High_parity_with_Frozen_entry_mismatch_N':0,'future_evaluator_values_used_by_decision_N':0,'economics_rows_sha256':sha(target),'winner_exclusive_denominator_sum':sum(g['denominator_N'] for g in exclusive),'safety':SAFETY})
    print(json.dumps({'Entry_N':1600,'lifecycle':coverage,'all_entry':flat(group_summary('all',rr))},ensure_ascii=False))

if __name__=='__main__':run()
