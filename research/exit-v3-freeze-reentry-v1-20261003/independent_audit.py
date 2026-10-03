"""Independent array-selection/Fraction audit. No primary engine/evaluator imports."""
from work_io import ROOT,WORK,V3,V4,TRACE,P3,PRIVATE,INPUT,ENTRY_HEAD,V3_HEAD,V4_HEAD,PINS,BUDGET,SAFETY,read,write,sha,now
from audit_v3_reference import reference_scan,independent_fill,audit_clock,raw_ok
from fractions import Fraction
from collections import Counter,defaultdict
import ast,gzip,hashlib,json,math

SELL=['sell_status','sell_minute','sell_timestamp','sell_price','sell_price_decimal','sell_raw_price','sell_source','sell_source_start','sell_source_assumed_available_at','sell_adjustment_bps','commission','exit_reason','closing_fallback_for_locked_intent','unresolved_reason','unfilled_intent_reason']
BUCKETS=['<1%','1–<2%','2–<3%','3–<4%','4–<5%','>=5%','UNKNOWN']
REASONS=['UP_STRUCTURE_REVERSED','UP_STRUCTURE_RETIRED_BY_RANGE','LOCAL_UP_STRUCTURE_GUARD_BROKEN','SESSION_CLOSE','UNRESOLVED']
def stream(p):
    with gzip.open(p,'rt') as f:
        for x in f:yield json.loads(x)
def F(x):return Fraction(str(x))
def close(a,b):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-10)
    if isinstance(a,dict) and isinstance(b,dict):return set(a)==set(b) and all(close(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    return a==b
def summary(values):
    a=sorted(v for v in values if v is not None and math.isfinite(v));n=len(a)
    return {'N':n,'mean':float(sum(F(v) for v in a)/n) if n else None,'median':float((F(a[(n-1)//2])+F(a[n//2]))/2) if n else None,'sum':float(sum(F(v) for v in a)) if n else None}
def pct(n,d):return 100*n/d if d else None

def new_buy(day,intent,raw):
    end=900 if day<'2024-11-05' else 925
    choices=sorted((r for r in raw if raw_ok(r) and (540<=int(r[0])<690 or 750<=int(r[0])<end) and int(r[0]) not in [540,750] and int(r[0])>=intent['minute']),key=lambda a:a[0])
    if not choices:return None
    r=choices[0];return int(r[0]),r[1],float(r[1]*1.0005)

def flat_expected(t,signals):
    end=900 if t['session']<'2024-11-05' else 925
    if t['sell_status']!='FILLED':return [],None,None,None,'UNRESOLVED_POSITION'
    if t['exit_reason']=='SESSION_CLOSE' or t['sell_minute']>=end:return [],None,None,None,'SESSION_CLOSE_TERMINAL'
    rows=[s for s in signals if t['sell_minute']<s['minute']<=end]
    reset_i=next((i for i,s in enumerate(rows) if F(s['score'])<F(s['threshold'])),None)
    cross_i=next((i for i in range((reset_i+1) if reset_i is not None else len(rows),len(rows)) if F(rows[i-1]['score'])<F(rows[i-1]['threshold']) and F(rows[i]['score'])>=F(rows[i]['threshold'])),None)
    decisions=rows[:cross_i+1] if cross_i is not None else rows
    return decisions,rows[reset_i] if reset_i is not None else None,rows[cross_i] if cross_i is not None else None,(reset_i,cross_i),'NO_FRESH_CROSS_BEFORE_SESSION_CLOSE' if cross_i is None else None

def decision_overlaps_position(minute,after_trade_index,trades):
    # At timestamp t, previous raw bar closes, decision is sealed, then next raw
    # Open t may fill the newly intended buy. Only that next trade can start at t
    # after the decision. Existing positions remain inclusive through sell t.
    return any((x['buy_minute']<minute or (x['buy_minute']==minute and x['trade_index']<=after_trade_index)) and minute<=(x['sell_minute'] if x['sell_minute'] is not None else 10000) for x in trades)

def trade_economics(t,base):
    first=t['entry_type']=='FIRST';filled=t['sell_status']=='FILLED'
    ret=base['realized_return_pct'] if first else float(100*(F(t['sell_price'])/F(t['buy_price'])-1)) if filled else None
    h=base['holding_active_minutes'] if first else audit_clock(t['session'],t['buy_minute'],t['sell_minute']) if filled else None
    rawret=float(100*(F(t['sell_raw_price'])/F(t['buy_raw_price'])-1)) if filled and t['buy_raw_price'] is not None and t['sell_raw_price'] is not None else None
    prior=t.get('previous_sell_minute');intent=t['buy_intent'].get('minute',t['buy_intent'].get('intent_minute'))
    return dict(t,realized_return_pct=ret,holding_active_minutes=h,return_before_execution_adjustment_pct=rawret,execution_adjustment_drag_pp=float(F(rawret)-F(ret)) if rawret is not None and ret is not None else None,previous_EXIT_to_BUY_intent_active_minutes=audit_clock(t['session'],prior,intent) if prior is not None else None,previous_EXIT_to_BUY_fill_active_minutes=audit_clock(t['session'],prior,t['buy_minute']) if prior is not None else None)

def watch_economics(key,tt,b):
    rr=[t['realized_return_pct'] for t in tt if t['realized_return_pct'] is not None];allknown=len(rr)==len(tt)
    total=float(sum(F(r) for r in rr)) if allknown else None
    compound=Fraction(1)
    for r in rr:compound*=1+F(r)/100
    return {'watch_key':key,'session':b['session'],'symbol':b['symbol'],'original_FIRST_exclusive_bucket':b['exclusive_bucket'],'original_FIRST_observed_Entry_to_High_pct':b['observed_entry_to_high_pct'],'original_remaining_source_complete':b['remaining_source_complete'],'total_trades_N':len(tt),'reentry_fills_N':len(tt)-1,'sell_filled_trades_N':len(rr),'unresolved_trades_N':len(tt)-len(rr),'all_trades_realized':allknown,'FIRST_only_V3_realized_return_pct':b['realized_return_pct'],'simple_cumulative_realized_return_pct':total,'simple_reentry_incremental_return_pp':float(F(total)-F(b['realized_return_pct'])) if allknown else None,'same_watch_compounded_return_pct':float(100*(compound-1)) if allknown else None,'known_partial_sum_pct':float(sum(F(r) for r in rr)) if rr else None,'FIRST_only_V3_holding_active_minutes':b['holding_active_minutes'],'FIRST_exit_reason':b['exit_reason'],'FIRST_sell_status':b['sell_status'],'total_holding_active_minutes':sum(t['holding_active_minutes'] for t in tt) if allknown else None,'total_execution_adjustment_drag_pp':float(sum(F(t['execution_adjustment_drag_pp']) for t in tt)) if allknown and all(t['execution_adjustment_drag_pp'] is not None for t in tt) else None}

def group(label,ww,tt):
    pp=[w for w in ww if w['all_trades_realized'] and w['FIRST_only_V3_realized_return_pct'] is not None]
    a=summary(w['FIRST_only_V3_realized_return_pct'] for w in pp);b=summary(w['simple_cumulative_realized_return_pct'] for w in pp)
    n=sum(w['reentry_fills_N']>0 for w in ww);d=sum(w['FIRST_sell_status']=='FILLED' for w in ww)
    return {'original_FIRST_Entry_to_High':label,'watch_N':len(ww),'common_completely_realized_watch_N':len(pp),'unresolved_watch_N':len(ww)-len(pp),'FIRST_only_all_saved_V3':summary(w['FIRST_only_V3_realized_return_pct'] for w in ww),'FIRST_only_V3_common':a,'reentry_included_simple_common':b,'delta_mean_pp':b['mean']-a['mean'] if pp else None,'delta_group_median_pp':b['median']-a['median'] if pp else None,'paired_incremental_return':summary(w['simple_reentry_incremental_return_pp'] for w in pp),'same_watch_compounded':summary(w['same_watch_compounded_return_pct'] for w in pp),'watches_with_reentry_N':n,'avg_total_trades_per_watch':summary(w['total_trades_N'] for w in ww),'reentry_trades_N':sum(w['reentry_fills_N'] for w in ww),'reentry_trade_return':summary(t['realized_return_pct'] for t in tt if t['entry_type']=='REENTRY'),'first_exit_reentry_rate_pct':pct(n,d),'first_exit_filled_denominator_N':d,'complete_watch_additional_simple_return_sum_pp':summary(w['simple_reentry_incremental_return_pp'] for w in pp)['sum'],'total_holding_active_minutes':summary(w['total_holding_active_minutes'] for w in pp),'original_complete_raw_remaining_path_watch_N':sum(w['original_remaining_source_complete'] for w in ww)}

def trade_group(label,tt):
    rr=[t['realized_return_pct'] for t in tt if t['realized_return_pct'] is not None]
    return {'trade_index':label,'trade_N':len(tt),'sell_filled_N':len(rr),'unresolved_N':len(tt)-len(rr),'realized_return_pct':summary(rr),'positive_N':sum(r>0 for r in rr),'nonpositive_N':sum(r<=0 for r in rr),'positive_rate_pct':pct(sum(r>0 for r in rr),len(rr)),'holding_active_minutes':summary(t['holding_active_minutes'] for t in tt),'exit_reason_N':dict(Counter(t['exit_reason'] for t in tt)),'EXIT_to_reentry_fill_active_minutes':summary(t['previous_EXIT_to_BUY_fill_active_minutes'] for t in tt)}

def run():
    counts=Counter();fails=[];current=None;leak=overlap=futurebucket=failed_checks=0
    def check(name,ok,causal=False,overlap_check=False,**kwargs):
        nonlocal leak,overlap,failed_checks
        counts[name]+=1
        if not ok:
            failed_checks+=1
            leak+=int(causal);overlap+=int(overlap_check)
            if len(fails)<100:fails.append({'watch_key':current,'check':name})
    official=read(ROOT/'EXIT_V3_OFFICIAL_FREEZE_RECEIPT.json');contract=read(ROOT/'REENTRY_CONTRACT_FREEZE_RECEIPT.json');sigreceipt=read(ROOT/'FROZEN_SIGNAL_REUSE_RECEIPT.json')
    check('FIRST_EXIT_OFFICIAL_FREEZE_identities',official['ExitFrozen'] and official['EntryFrozen'] and official['FIRST_ENTRY_HEAD']==ENTRY_HEAD and official['V3_FINAL_HEAD']==V3_HEAD and official['V4_FINAL_HEAD']==V4_HEAD and official['V4_status']=='V4_NOT_BETTER_KEEP_V3')
    check('Frozen_official_receipt_byte_identity',sha(ROOT/'EXIT_V3_OFFICIAL_FREEZE_RECEIPT.json')==contract['Frozen_EXIT_v3_official_receipt_sha256'])
    check('contract_immutable_pre_replay',sha(ROOT/'CONTRACT.md')==contract['contract_sha256'] and read(PRIVATE/'RUN_ONCE.json')['contract_sha256']==contract['contract_sha256'])
    for f,pin in contract['decision_code_hashes'].items():check('precommitted_decision_code_unchanged',sha(ROOT/f)==pin)
    for f,pin in contract['Frozen_EXIT_v3_whole_code_hashes'].items():check('Frozen_V3_A_B_C_PRE_quality_fill_calendar_unchanged',sha(ROOT/f)==sha(V3/f)==pin)
    for f,pin in PINS.items():check('Frozen_RC2_Path_pin',sha(WORK/'inputs_v3/v2_public/FROZEN_SOURCE'/f)==pin)
    check('Frozen_Entry_exact_bytes',sha(TRACE/'FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz')==contract['frozen_input_hashes']['Frozen_FIRST_ENTRY.jsonl.gz']=='e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb')
    check('V3_saved_first_outcomes_unchanged',sha(P3/'REPLAY_ROWS.jsonl.gz')==contract['frozen_input_hashes']['V3_REPLAY_ROWS.jsonl.gz'] and sha(P3/'ECONOMICS_ROWS.jsonl.gz')==contract['frozen_input_hashes']['V3_ECONOMICS_ROWS.jsonl.gz'])
    entry={e['watch_key']:e for e in stream(TRACE/'FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if e['entry_status']=='FIRST_ENTRY'}
    baseline={e['watch_key']:e for e in stream(P3/'REPLAY_ROWS.jsonl.gz')};baseeco={e['watch_key']:e for e in stream(P3/'ECONOMICS_ROWS.jsonl.gz')}
    check('all_1600_Frozen_watch_identities',len(entry)==len(baseline)==len(baseeco)==1600 and set(entry)==set(baseline)==set(baseeco))
    signals=defaultdict(list);projection=list(stream(PRIVATE/'FROZEN_P1_Q70_SIGNAL_ROWS.jsonl.gz'))
    check('signal_projection_hash',sha(PRIVATE/'FROZEN_P1_Q70_SIGNAL_ROWS.jsonl.gz')==sigreceipt['signal_projection_sha256'])
    source=INPUT/'frozen_signal';pkg=read(INPUT/'first_entry_public/PRIVATE_FREEZE_PACKAGE_RECEIPT.json')
    for f in ['UPTREND_SCORE_ROWS.jsonl.gz','WATCH_RECORDS.jsonl.gz']:
        check('Frozen_score_watch_exact_source_hash',sha(source/f)==pkg['selected_private_files'][f]['sha256'])
    grid=list(stream(source/'PERSISTENT_GRID.jsonl.gz'));check('Frozen_grid_exact_hash',sha(source/'PERSISTENT_GRID.jsonl.gz')==read(INPUT/'first_entry_public/PERSISTENT_GRID_RECEIPT.json')['grid_sha256'])
    calibration={i:read(source/f'P1_F{i}_calibration.json') for i in range(1,6)}
    for i,c in calibration.items():check('Frozen_fold_threshold_exact_hash',sha(source/f'P1_F{i}_calibration.json')==pkg['selected_private_files'][f'PRIVATE_MODELS/P1_F{i}_calibration.json']['sha256'] and c['corrected_Q_D'] and c['UPSIDE_unchanged_reuse'])
    projected={s['row_id']:s for s in projection};matched=set();p1=0
    for original in stream(source/'UPTREND_SCORE_ROWS.jsonl.gz'):
        if original['family']!='P1':continue
        p1+=1
        if original['watch_key'] not in entry:continue
        g=grid[original['row_index']];s=projected[original['row_id']];matched.add(s['row_id'])
        expected={'watch_key':original['watch_key'],'session':original['session'],'minute':original['intent_minute'],'timestamp':g['intent_timestamp'],'closed_raw_start':g['closed_raw_start'],'feature_max_timestamp':g['feature_max_timestamp'],'actual_known_at':'UNKNOWN','availability_assumption':'bar_end','row_id':original['row_id'],'row_index':original['row_index'],'fold':original['fold'],'score':original['UPTREND_SCORE'],'threshold':original['thresholds']['Q70'],'Q_D_lineage':original['Q_D_lineage']}
        check('every_saved_P1_score_threshold_grid_exact_projection',s==expected)
        check('P1_Q70_corrected_fold_lineage',original['Q_D_lineage']=='CORRECTED_CALENDAR_Q_D_REFIT' and s['threshold']==calibration[s['fold']]['thresholds']['Q70'])
        check('P1_feature_cutoff_and_closed_bar_availability',g['canonical'] and g['row_id']==s['row_id'] and g['feature_max_timestamp']<=g['intent_timestamp'] and g['closed_raw_start']+1==s['minute'],causal=True)
        check('bucket_absent_from_decision_input',not any(k in s for k in ['exclusive_bucket','observed_high','realized_return_pct','original_FIRST_exclusive_bucket']))
        signals[s['watch_key']].append(s)
    check('complete_post_exit_signal_coverage_identity',p1==223940 and len(matched)==len(projection)==157133 and len(signals)==1600)
    ledger=list(stream(PRIVATE/'TRADE_LEDGER.jsonl.gz'));actualeco={(t['watch_key'],t['trade_index']):t for t in stream(PRIVATE/'TRADE_ECONOMICS_ROWS.jsonl.gz')}
    actualwatch={w['watch_key']:w for w in stream(PRIVATE/'WATCH_ECONOMICS_ROWS.jsonl.gz')}
    episodes={(e['watch_key'],e['after_trade_index']):e for e in stream(PRIVATE/'FLAT_EPISODES.jsonl.gz')}
    flattrace=defaultdict(list)
    for d in stream(PRIVATE/'FLAT_DECISION_TRACE.jsonl.gz'):flattrace[(d['watch_key'],d['after_trade_index'])].append(d)
    by=defaultdict(list)
    for t in ledger:by[t['watch_key']].append(t)
    with gzip.open(TRACE/'SAVED_INPUTS/raw_paths_selected.json.gz','rt') as f:raw=json.load(f)
    trace_manifest=read(TRACE/'MANIFEST.json')['components'];actualee={(e['watch_key'],e['after_trade_index']):e for e in stream(PRIVATE/'FLAT_EPISODE_ECONOMICS.jsonl.gz')}
    expected_trade=[];expected_watch=[];expected_episode=[];newlife=0;samebar=0
    check('ledger_episodes_all_watches',len(by)==len(actualwatch)==1600 and set(by)==set(entry) and len(episodes)==len(ledger))
    for key,ee in entry.items():
        current=key;tt=by[key];good=raw[key]['today'];expected_tt=[]
        path=TRACE/'FULL_TRACE'/(key.replace('|','_')+'.jsonl.gz')
        check('exact_frozen_full_State9_Path_trace_no_reconstruction',sha(path)==trace_manifest['FULL_TRACE/'+path.name]['sha256'])
        rows=list(stream(path))
        check('raw_source_chronology',len({r[0] for r in good})==len(good) and all(a[0]<b[0] for a,b in zip(good,good[1:])))
        check('consecutive_trade_indices',list(t['trade_index'] for t in tt)==list(range(1,len(tt)+1)))
        previous=None
        for t in tt:
            idx=t['trade_index'];pair=(key,idx);episode=episodes[pair]
            if idx==1:
                check('Frozen_FIRST_entry_identity',t['entry_type']=='FIRST' and t['buy_price']==ee['fill_price'] and t['buy_minute']==ee['fill_minute'] and t['buy_intent']==ee['first_intent'] and t['buy_timestamp']==ee['fill_timestamp'])
                check('Frozen_FIRST_V3_outcome_identity_no_replay',all(t.get(k)==baseline[key].get(k) for k in SELL) and t['exit_intent']==baseline[key]['exit_intent'] and t['planned_close_intent_minute']==baseline[key]['planned_close_intent_minute'] and t['decision_N']==0 and t['EXIT_baseline_decision_replay_N']==0 and t['FIRST_saved_outcome_reused'])
            else:
                prev_episode=episodes[(key,idx-1)];expected_buy=new_buy(t['session'],prev_episode['fresh_cross'],good)
                check('reentry_BUY_exact_next_regular_Open_plus5bps',expected_buy is not None and (t['buy_minute'],t['buy_raw_price'],t['buy_price'])==expected_buy)
                check('reentry_buy_intent_exact_fresh_cross',t['buy_intent']==prev_episode['fresh_cross'])
                check('no_same_bar_sell_buy',t['buy_minute']>previous['sell_minute'],overlap_check=True,causal=True)
                samebar+=int(t['buy_minute']==previous['sell_minute'])
                check('no_position_overlap',previous['sell_status']=='FILLED' and t['buy_minute']>previous['sell_minute'],overlap_check=True)
                check('SELL_fill_then_flat_not_intent',t['previous_sell_minute']==previous['sell_minute'] and t['previous_exit_reason']==previous['exit_reason'])
                metadata=list(stream(PRIVATE/'EXIT_DECISION_TRACE'/f'{key.replace("|","_")}_{idx}.jsonl.gz'))
                ref=reference_scan(rows,{'session':t['session'],'fill_minute':t['buy_minute']},metadata,check);newlife+=1
                actual=(t['exit_intent']['reason'],t['exit_intent']['minute']) if t['exit_intent'] else None
                check('new_position_V3_A_B_C_first_valid_precedence',actual==ref['trigger'])
                check('new_V3_phase_no_prior_position_carry',t['first_arm_minute']==ref['first_arm'] and t['arm_at_entry']==(ref['first_arm']==t['buy_minute']) and [(e['minute'],e['segment']) for e in t['arm_events']]==ref['arms'])
                check('new_position_quality_suspension_exact',[(e['minute']) for e in t['observations_suspended']]==ref['losses'] and t['suspended_at_last_decision']==ref['lost'])
                check('new_position_guard_causality_and_mechanics',t['local_guard_creation_N']==ref['creation_N'] and t['local_guard_tighten_N']==ref['tighten_N'])
                check('post_exit_decision_zero',len(metadata)==t['decision_N']==ref['decisions'] and t['post_exit_decision_N']==0)
                check('planned_close_exact_clock',t['planned_close_intent_minute']==((900 if t['session']<'2024-11-05' else 925) if actual is None else None))
                result=independent_fill({'session':t['session'],'fill_minute':t['buy_minute']},ref['trigger'],good)
                check('sell_next_open_or_exact_close_minus5bps',result[0]==t['sell_status'] and result[1]==t['sell_minute'] and result[3]==t['sell_source'] and result[4]==t['exit_reason'] and (F(t['sell_price_decimal'])==result[2] if result[2] is not None else t['sell_price'] is None))
                check('V4_D_never_adopted',t['exit_reason'] in REASONS and (t['exit_intent'] is None or t['exit_intent']['reason'] in REASONS[:3]))
            if t['sell_status']=='FILLED':check('sell_after_entry_no_overlap',t['sell_minute']>t['buy_minute'],overlap_check=True)
            calc=trade_economics(t,baseeco[key]);expected_tt.append(calc);expected_trade.append(calc)
            for f in ['realized_return_pct','holding_active_minutes','return_before_execution_adjustment_pct','execution_adjustment_drag_pp','previous_EXIT_to_BUY_intent_active_minutes','previous_EXIT_to_BUY_fill_active_minutes']:
                check('trade_economics_'+f,close(actualeco[pair][f],calc[f]))
            selected,reset,cross,indices,status=flat_expected(t,signals[key]);decs=flattrace[pair]
            check('post_exit_flat_episode_identity',episode['previous_sell_status']==t['sell_status'] and episode['previous_sell_minute']==t['sell_minute'] and episode['previous_exit_reason']==t['exit_reason'])
            check('reset_strictly_below_threshold',episode['reset']==reset)
            check('fresh_cross_previous_below_current_GE',episode['fresh_cross']==cross)
            check('post_exit_scoring_only_expected_prefix',len(decs)==episode['entry_decision_N']==len(selected))
            for i,s in enumerate(selected):
                reset_i,cross_i=indices
                before='WAIT_FOR_RESET' if reset_i is None or i<=reset_i else 'ARMED_FOR_FRESH_CROSS'
                after='REENTRY_BUY_INTENT' if cross_i==i else 'ARMED_FOR_FRESH_CROSS' if reset_i is not None and i>=reset_i else 'WAIT_FOR_RESET'
                d={'watch_key':key,'after_trade_index':idx,'sell_fill_minute':t['sell_minute'],'minute':s['minute'],'row_id':s['row_id'],'score':s['score'],'threshold':s['threshold'],'state_before':before,'state_after':after,'reset_observed':reset_i==i,'fresh_cross':cross_i==i}
                check('flat_decision_each_row_exact',i<len(decs) and decs[i]==d)
                check('score_only_strictly_after_sell_fill',s['minute']>t['sell_minute'],causal=True)
                check('no_Entry_decision_in_any_open_position',not decision_overlaps_position(s['minute'],idx,tt),causal=True)
            fill=new_buy(t['session'],cross,good) if cross is not None else None
            if cross is not None:
                status='FILLED' if fill is not None else 'NO_REENTRY_NO_NEXT_REGULAR_OPEN'
                actualfill=episode['buy_fill']
                check('canonical_fresh_cross_fill',actualfill['buy_status']==status and ((actualfill['buy_minute'],actualfill['buy_raw_price'],actualfill['buy_price'])==fill if fill is not None else actualfill['buy_price'] is None))
            else:check('no_fake_buy_fill',episode['buy_fill'] is None)
            check('flat_episode_terminal_status',episode['terminal_status']==status)
            check('all_chronological_cycles_without_arbitrary_cap',(idx<len(tt))==(cross is not None and fill is not None))
            if t['exit_reason']=='SESSION_CLOSE':check('session_close_terminal_reentry_zero',cross is None and idx==len(tt))
            ev=dict(episode,EXIT_to_reset_active_minutes=audit_clock(t['session'],t['sell_minute'],reset['minute']) if reset is not None else None,reset_to_cross_active_minutes=audit_clock(t['session'],reset['minute'],cross['minute']) if cross is not None else None,EXIT_to_cross_active_minutes=audit_clock(t['session'],t['sell_minute'],cross['minute']) if cross is not None else None,EXIT_to_reentry_fill_active_minutes=audit_clock(t['session'],t['sell_minute'],fill[0]) if fill is not None else None)
            check('flat_episode_all_timing_economics',close(actualee[pair],ev));expected_episode.append(ev)
            previous=t
        w=watch_economics(key,expected_tt,baseeco[key]);expected_watch.append(w)
        for f,v in w.items():check('watch_economics_'+f,close(actualwatch[key][f],v))
        check('original_first_bucket_fixed',all(actualwatch[key]['original_FIRST_exclusive_bucket']==baseeco[key]['exclusive_bucket'] for _ in tt))
        check('unresolved_not_zero_imputed',w['all_trades_realized'] or (w['simple_cumulative_realized_return_pct'] is None and w['same_watch_compounded_return_pct'] is None))
    audit_tables(expected_watch,expected_trade,expected_episode,check)
    for name in ['fresh_cross.py','reentry_fill.py','replay_reentry.py','frozen_v2_lifecycle.py','local_guard.py']:
        s=(ROOT/name).read_text();tree=ast.parse(s)
        imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]+[a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
        check('no_model_State9_reconstruction_provider_V4_import',not any(any(w in name for w in ['model','teacher','State9','recovery_floor','replay_v4','evaluate']) for name in imports))
        calls=[n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        check('fit_predict_search_provider_orders_zero',not any(n in calls for n in ['fit','predict','predict_proba','get_quotes','place_order','send_order']))
        constants=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
        illegal={'exclusive_bucket','observed_high','original_FIRST_exclusive_bucket','remaining_upside_pct'}&set(constants)
        futurebucket+=len(illegal);check('future_bucket_engine_reads_zero',not illegal)
    check('one_primary_Reentry_replay',read(PRIVATE/'RUN_ONCE.json')['primary_reentry_replay_invocation_N']==1 and read(PRIVATE/'RUN_ONCE.json')['status']=='COMPLETED')
    check('new_V3_lifecycles_all_additional_fills',newlife==len(ledger)-1600==588)
    check('10_safety_flags_false',len(SAFETY)==10 and not any(SAFETY.values()))
    mismatch=failed_checks
    result={'saved_at_jst':now(),'status':'INDEPENDENT_REENTRY_V1_AUDIT_PASS' if mismatch==leak==overlap==futurebucket==0 else 'BLOCKED_REENTRY_AUDIT_MISMATCH','watch_N':1600,'trade_N':len(ledger),'reentry_position_lifecycle_checks_N':newlife,'independent_check_N':sum(counts.values()),'checks_by_name':dict(counts),'mismatch_N':mismatch,'future_causal_leakage_N':leak,'position_overlap_N':overlap,'same_bar_sell_buy_N':samebar,'future_bucket_decision_reads':futurebucket,'mismatch_examples':fails,'independent_primary_engine_import_N':0,'Frozen_FIRST_V3_decision_replay_N':0,'State9_Path_reconstruction_N':0,'V4_D_used_N':0,'new_model_teacher_threshold_search_N':0,'Capital_Portfolio_N':0,'historical_actual_known_at':'UNKNOWN','availability_assumption':'bar_end only; not verified actual historical arrival','economics_numeric_tolerance':'absolute1e-10/relative1e-12; all structure/score comparisons exact, no decision tolerance','safety':SAFETY}
    write(ROOT/'INDEPENDENT_AUDIT.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='checks_by_name'}))
    if result['status']!='INDEPENDENT_REENTRY_V1_AUDIT_PASS':raise RuntimeError(result['status'])

def audit_tables(watches,trades,episodes,check):
    primary=[]
    for b in BUCKETS:
        ww=[w for w in watches if w['original_FIRST_exclusive_bucket']==b];kk={w['watch_key'] for w in ww}
        primary.append(group(b,ww,[t for t in trades if t['watch_key'] in kk]))
    check('primary_exclusive_full_table_exact',close(read(ROOT/'EXCLUSIVE_ORIGINAL_ENTRY_HIGH_PRIMARY.json'),primary))
    check('exclusive_original_denominators',sum(p['watch_N'] for p in primary)==1600 and [p['watch_N'] for p in primary]==[619,297,213,130,83,253,5])
    check('Winner_GE5_multi_leg',close(read(ROOT/'WINNER_GE5_MULTI_LEG.json'),[primary[5]]))
    check('Winner_2_to_5_exclusive_multi_leg',close(read(ROOT/'WINNER_2_TO_5_MULTI_LEG.json'),primary[2:5]))
    ww=[w for w in watches if w['original_FIRST_exclusive_bucket'] in BUCKETS[2:5]];keys={w['watch_key'] for w in ww}
    check('combined_2_to_5_excludes_GE5',close(read(ROOT/'COMBINED_2_TO_5_MULTI_LEG.json'),[group('2–<5% combined',ww,[t for t in trades if t['watch_key'] in keys])]))
    check('all_watch_economics',close(read(ROOT/'ALL_WATCH_ECONOMICS.json'),[group('ALL_1600',watches,trades)]))
    indexes=[]
    for n,label in [(1,'#1 FIRST'),(2,'#2 first REENTRY'),(3,'#3 second REENTRY'),(4,'#4+')]:indexes.append(trade_group(label,[t for t in trades if t['trade_index']==n or n==4 and t['trade_index']>4]))
    check('trade_index_quality_tables',close(read(ROOT/'TRADE_INDEX.json'),indexes))
    check('reentry_exit_reason_tables',close(read(ROOT/'REENTRY_EXIT_REASON.json'),[trade_group(r,[t for t in trades if t['entry_type']=='REENTRY' and t['exit_reason']==r]) for r in REASONS]))
    prev=[]
    for r in REASONS:
        ee=[e for e in episodes if e['previous_exit_reason']==r];d=sum(e['previous_sell_status']=='FILLED' for e in ee);n=sum(e['buy_fill'] is not None and e['buy_fill']['buy_status']=='FILLED' for e in ee)
        prev.append({'previous_exit_reason':r,'episodes_N':len(ee),'flat_after_sell_fill_episodes_N':d,'reset_observed_N':sum(e['reset'] is not None for e in ee),'fresh_cross_N':sum(e['fresh_cross'] is not None for e in ee),'reentry_filled_N':n,'reentry_rate_pct':pct(n,d),'post_SESSION_CLOSE_reentry_N':n if r=='SESSION_CLOSE' else 0})
    check('previous_exit_reset_cross_fill_rates',close(read(ROOT/'PREVIOUS_EXIT_REENTRY.json'),prev))
    daily=[]
    for day in sorted({w['session'] for w in watches}):
        ww=[w for w in watches if w['session']==day];daily.append({'session':day,'Frozen_FIRST_watch_N':len(ww),'reentry_fills_N':sum(w['reentry_fills_N'] for w in ww),'watches_with_reentry_N':sum(w['reentry_fills_N']>0 for w in ww)})
    check('session_activity_includes_zero',read(ROOT/'SESSION_ACTIVITY.json')==daily)
    a=read(ROOT/'REENTRY_ACTIVITY.json')
    expected={'watch_N':1600,'session_N':len(daily),'watches_with_0_reentry_N':sum(w['reentry_fills_N']==0 for w in watches),'watches_with_GE1_reentry_N':sum(w['reentry_fills_N']>=1 for w in watches),'watches_with_GE2_reentry_N':sum(w['reentry_fills_N']>=2 for w in watches),'watches_with_GE3_reentry_N':sum(w['reentry_fills_N']>=3 for w in watches),'total_reentry_intents_N':sum(e['fresh_cross'] is not None for e in episodes),'total_reentry_fills_N':len(trades)-1600,'reentry_trades_per_watch':summary(w['reentry_fills_N'] for w in watches),'total_trades_per_watch':summary(w['total_trades_N'] for w in watches),'total_trades_per_watch_distribution':{str(k):v for k,v in Counter(w['total_trades_N'] for w in watches).items()},'reentry_fills_per_session':summary(d['reentry_fills_N'] for d in daily),'sessions_with_0_reentry_N':sum(d['reentry_fills_N']==0 for d in daily),'max_reentry_count_observed':max(w['reentry_fills_N'] for w in watches),'EXIT_to_reset_active_minutes':summary(e['EXIT_to_reset_active_minutes'] for e in episodes),'reset_to_fresh_cross_active_minutes':summary(e['reset_to_cross_active_minutes'] for e in episodes),'EXIT_fill_to_next_reentry_intent_active_minutes':summary(e['EXIT_to_cross_active_minutes'] for e in episodes),'EXIT_fill_to_next_reentry_fill_active_minutes':summary(e['EXIT_to_reentry_fill_active_minutes'] for e in episodes)}
    for k,v in expected.items():check('activity_'+k,close(a[k],v))
    c=read(ROOT/'CHURN_AND_COST.json');re=[t for t in trades if t['entry_type']=='REENTRY'];filled=[t for t in trades if t['sell_status']=='FILLED']
    for k,v in {'total_entry_trades_N':len(trades),'total_completed_round_trips_N':len(filled),'unresolved_open_trades_N':len(trades)-len(filled),'reentry_completed_round_trips_N':sum(t['sell_status']=='FILLED' for t in re),'all_trade_nonpositive_return_N':sum(t['realized_return_pct']<=0 for t in filled),'reentry_trade_nonpositive_return_N':sum(t['realized_return_pct'] is not None and t['realized_return_pct']<=0 for t in re),'nominal_adverse_buy_bps_sum_across_trade_legs':5*len(trades),'nominal_adverse_sell_bps_sum_across_filled_trade_legs':5*len(filled)}.items():check('churn_'+k,c[k]==v)
    for k in [1,3,5]:
        check('short_holding_diagnostics_all',c['holding_LE_active_minutes_all'][str(k)]==sum(t['holding_active_minutes'] is not None and t['holding_active_minutes']<=k for t in trades))
        check('short_holding_diagnostics_reentry',c['holding_LE_active_minutes_reentry'][str(k)]==sum(t['holding_active_minutes'] is not None and t['holding_active_minutes']<=k for t in re))
        check('short_EXIT_reentry_diagnostics',c['EXIT_to_reentry_LE_active_minutes'][str(k)]==sum(t['previous_EXIT_to_BUY_fill_active_minutes']<=k for t in re))
    for k,field,tt in [('all_trade_raw_before_adjustment_return_pct','return_before_execution_adjustment_pct',trades),('all_trade_execution_adjusted_return_pct','realized_return_pct',trades),('all_trade_exact_adjustment_drag_pp','execution_adjustment_drag_pp',trades),('reentry_raw_before_adjustment_return_pct','return_before_execution_adjustment_pct',re),('reentry_execution_adjusted_return_pct','realized_return_pct',re),('reentry_exact_adjustment_drag_pp','execution_adjustment_drag_pp',re),('watch_cost_drag_pp','total_execution_adjustment_drag_pp',watches)]:check('exact_execution_cost_'+k,close(c[k],summary(t[field] for t in tt)))

if __name__=='__main__':run()
