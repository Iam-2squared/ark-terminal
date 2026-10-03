"""Independent full-population verifier. Does not import replay, lifecycle or evaluate."""
import ast, collections, gzip, json, math, statistics, zipfile
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from settings import HERE, INPUT, PRIVATE, SAFETY, now, sha, load, save, rows

def clock(day,a,b):
    last = 900 if day<'2024-11-05' else 925
    total=0
    for lo,hi in [(540,690),(750,last)]:
        total += max(0,min(b,hi)-max(a,lo))
    return total

def admitted(a):
    if len(a)!=7 or not all(math.isfinite(float(v)) for v in a):return False
    o,h,l,c=map(Decimal,map(str,a[1:5]))
    return l>0 and l<=o<=h and l<=c<=h and a[5]>=0 and a[6]>=0

def event_kinds(previous,s,p,ordinal_break,segment_break,active_run):
    current=s['current_semantics_observed']; a=previous['state'] if previous else None
    oldp=previous['path'] if previous else None
    link=a is not None and a['current_semantics_observed'] and current and not (ordinal_break or segment_break)
    same=link and oldp['Primary_or_null']==p['Primary_or_null']
    change=link and not same
    result=[]
    if ordinal_break or segment_break:result.append('SEGMENT_BREAK')
    if a and a['current_semantics_observed'] and not current:result.append('OBSERVATION_LOST')
    if s['activity']=='INITIALIZING' and (a is None or a['activity']!='INITIALIZING' or ordinal_break or segment_break):result.append('INITIALIZING')
    if active_run and not same:result.append('EXIT')
    if current:
        if not link:result.append('OBSERVATION_RESUMED')
        if change:result.append('TRANSITION')
        result.append('HOLD' if same else 'ENTER')
    if link:
        if a['activity']=='BALANCED' and s['activity']!='BALANCED':result.append('RANGE_EXIT')
        if a['activity']!='BALANCED' and s['activity']=='BALANCED':result.append('RANGE_ENTER')
        def stop_identity(state):
            x=state['stop']
            return (x.get('direction'),x.get('center'),x.get('recognized_at')) if x and state['activity']=='STOPPED' else None
        before,after=stop_identity(a),stop_identity(s)
        if before is not None and before!=after:result.append('STOP_EXIT')
        if after is not None and before!=after:result.append('STOP_ENTER')
        if before is not None and before==after and a['stop']!=s['stop']:result.append('STOP_UPDATE')
        x,y=a['fast_flag'],s['fast_flag']
        if x is not None and y is None:result.append('FAST_UNAVAILABLE')
        if x is None and y is not None:result.append('FAST_AVAILABLE')
        if x is True and y is not True:result.append('FAST_EXIT')
        if x is not True and y is True:result.append('FAST_ENTER')
        for key,name in [('context','CONTEXT_CHANGE'),('leg_direction','LOCAL_DIRECTION_CHANGE'),('direction_basis','DIRECTION_BASIS_CHANGE')]:
            if a[key]!=s[key]:result.append(name)
    return result,link,same

def decision_scan(stream,entry,check):
    """Independent boolean latch scan, including null/reset boundaries."""
    active=False; suspended=False; first_arm=None; arms=[]; losses=[]; prev=None; trigger=None
    decisions=0; pull=set(); stop=set(); tightened=[]; sequence=[]; last=None
    cutoff=900 if entry['session']<'2024-11-05' else 925
    for r in stream:
        minute=r['bar_end_minute']
        if minute<entry['fill_minute']:continue
        if minute>cutoff or trigger:break
        decisions+=1;s=r['state'];p=r['path']
        usable=s['numeric_status']=='ACCEPTED' and s['current_semantics_observed'] and s['observed_at']==s['as_of'] and p['Primary_or_null'] is not None
        adjacent=prev is not None and prev['state']['current_semantics_observed'] and usable and prev['path']['causal_segment_id']==p['causal_segment_id'] and prev['state']['as_of']+1==s['as_of']
        if active and prev is not None and not adjacent:
            if not suspended:losses.append(minute)
            suspended=True
        if not adjacent:sequence=[]
        if usable:
            if not sequence or sequence[-1]!=p['Primary_or_null']:sequence=(sequence+[p['Primary_or_null']])[-3:]
            if p['Primary_or_null']=='PULLBACK':pull.add(p['run_id'])
            if p['Primary_or_null']=='RISE_STOP':stop.add(p['run_id'])
            if 'PROTECTED_LEVEL_TIGHTENED_EFFECTIVE_NEXT_BAR' in s['events']:tightened.append(minute)
        need_new_latch=not active or suspended
        if need_new_latch:
            if usable:
                active=s['context']==1;suspended=False
                if active:
                    first_arm=minute if first_arm is None else first_arm
                    arms.append((minute,p['causal_segment_id']))
        elif adjacent:
            old=prev['state']
            if old['context']==1 and s['context']==-1:
                check('context_reversal_protected_break',s['protected_before'] is not None and old['protected_after_effective_next']==s['protected_before'] and old['protected_effective_from'] is not None and old['protected_effective_from']<=s['as_of'] and Fraction(s['close_u'])<=Fraction(s['protected_before'])-Fraction('0.5') and 'STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL' in s['events'])
                trigger=('UP_STRUCTURE_REVERSED',minute)
            elif old['context']==1 and s['context']==0 and s['primary']=='RANGE' and s['activity']=='BALANCED':
                balance=s['balance'];analysis=s['range_analysis']
                check('independent_range_retirement',balance is not None and balance['established_at']==s['as_of'] and len(balance['window_ids'])==10 and max(balance['window_ids'])==s['as_of'] and analysis is not None and analysis['guard'] is False and 'CONTEXT_RETIRED_BY_OBSERVED_BALANCE' in s['events'])
                trigger=('UP_STRUCTURE_RETIRED_BY_RANGE',minute)
        prev=r;last=r
    return {'trigger':trigger,'first_arm':first_arm,'arms':arms,'losses':losses,'decisions':decisions,'pullback':len(pull),'rise_stop':len(stop),'tightened':tightened,'sequence':sequence,'active':active,'suspended':suspended,'last':last}

def independent_fill(entry,trigger,source):
    day=entry['session'];closing=900 if day<'2024-11-05' else 930;deadline=900 if day<'2024-11-05' else 925
    valid=[a for a in source if admitted(a)]
    first_am=min((int(a[0]) for a in source if a[0]<690),default=-1)
    first_pm=min((int(a[0]) for a in source if 750<=a[0]<deadline),default=-1)
    if trigger:
        eligible=[]
        for a in valid:
            t=int(a[0]);in_regular=540<=t<690 or 750<=t<deadline
            if in_regular and t not in (540,750,first_am,first_pm) and t>=trigger[1] and t>entry['fill_minute']:eligible.append(a)
        if eligible:
            a=sorted(eligible,key=lambda x:x[0])[0]
            return int(a[0]),Decimal(str(a[1]))*Decimal('0.9995'),'NEXT_ELIGIBLE_REGULAR_RAW_OPEN',trigger[0]
    matches=[a for a in valid if int(a[0])==closing]
    if len(matches)==1:
        return closing,Decimal(str(matches[0][4]))*Decimal('0.9995'),'PLANNED_TERMINAL_AUCTION_CLOSE',trigger[0] if trigger else 'SESSION_CLOSE'
    return None,None,None,'UNRESOLVED'

def independent_metrics(entry,scan,fill,raw):
    day=entry['session'];start=entry['fill_minute'];ep=Fraction(str(entry['fill_price']));closing=900 if day<'2024-11-05' else 930
    points=[a for a in raw if admitted(a) and start<int(a[0])<=closing]
    max_high=max((Fraction(str(a[2])) for a in points),default=None)
    peak=min((int(a[0]) for a in points if Fraction(str(a[2]))==max_high),default=None)
    mfe=100*(max_high/ep-1) if max_high is not None else None
    sell_t,sell_d,_,_=fill;sell=Fraction(sell_d) if sell_d is not None else None
    ret=100*(sell/ep-1) if sell is not None else None
    later=[a for a in points if sell_t is not None and int(a[0])>sell_t]
    later_high=max((Fraction(str(a[2])) for a in later),default=None)
    later_t=min((int(a[0]) for a in later if Fraction(str(a[2]))==later_high),default=None)
    before=[a for a in points if sell_t is not None and int(a[0])<sell_t]
    before_high=max((Fraction(str(a[2])) for a in before),default=None)
    deadline=900 if day<'2024-11-05' else 925
    intent=scan['trigger'][1] if scan['trigger'] else deadline;arm=scan['first_arm']
    result={'realized_return_pct':ret,'observed_entry_to_high_pct':mfe,'MFE_realization_pct':100*ret/mfe if ret is not None and mfe is not None and mfe>0 else None,'peak_giveback_pp':mfe-ret if mfe is not None and ret is not None else None,'peak_price_giveback_pct':100*(max_high-sell)/max_high if max_high is not None and sell is not None else None,'pre_sell_observed_peak_giveback_pp':100*(before_high/ep-1)-ret if before_high is not None and ret is not None else None,'later_missed_upside_pct':max(Fraction(0),100*(later_high/sell-1)) if later_high is not None else None,'later_missed_upside_entry_basis_pp':max(Fraction(0),100*(later_high-sell)/ep) if later_high is not None else None,'exit_to_later_high_active_minutes':clock(day,sell_t,later_t) if later_t is not None else None,'intent_to_later_high_active_minutes':clock(day,intent,later_t) if later_t is not None else None,'holding_active_minutes':clock(day,start,sell_t) if sell_t is not None else None,'entry_to_arm_active_minutes':clock(day,start,arm) if arm is not None else None,'arm_to_exit_active_minutes':clock(day,arm,intent) if arm is not None else None,'entry_to_high_active_minutes':clock(day,start,peak) if peak is not None else None,'protected_tighten_N':len(scan['tightened']),'PULLBACK_run_N':scan['pullback'],'RISE_STOP_run_N':scan['rise_stop']}
    return {k:float(v) if v is not None else None for k,v in result.items()},peak,later_t

def run():
    counts=collections.Counter();failures=[];leakage=0;mismatch_total=0
    def check(name,condition):
        nonlocal mismatch_total
        counts[name]+=1
        if not condition:
            mismatch_total+=1
            if len(failures)<100:failures.append({'check':name,'watch_key':current_key})
    current_key='IDENTITY'
    frozen_package=INPUT/'library_sources/Ark_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE_20261003_PRIVATE.zip'
    member='ark-terminal/research/persistent-watchlist-uptrend-first-entry-20261003-v2/CORRECTED_LINEAGE_FAST_FREEZE_20261003/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'
    with zipfile.ZipFile(frozen_package) as z:
        b=z.read(member)
    import hashlib
    check('frozen_entry_exact_bytes',hashlib.sha256(b).hexdigest()=='e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb' and b==(INPUT/'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz').read_bytes())
    ee=[json.loads(s) for s in gzip.decompress(b).splitlines()]
    ee=[r for r in ee if r['entry_status']=='FIRST_ENTRY'];check('frozen_entry_N',len(ee)==1600)
    identity=load(HERE/'IDENTITY_RECEIPT.json')
    for name,pin in identity['frozen_identity'].items():
        location=INPUT/('rc2_kernel' if name=='PATH_FROZEN.py' else 'frozen')/name
        check('frozen_RC2_profile_M0_Path_hash',sha(location)==pin['expected'])
    reconstruction=load(HERE/'FULL_TRACE_RECONSTRUCTION_RECEIPT.json')
    check('full_trace_all_independent_RC2_parity',reconstruction['entry_N']==1600 and reconstruction['independent_RC2_mismatch_N']==0)
    check('full_trace_saved_overlap_parity',reconstruction['saved_overlap_N']>0 and reconstruction['saved_overlap_mismatch_N']==0)
    trace_receipts={r['watch_key']:r for r in load(PRIVATE/'TRACE_RECEIPTS.json')}
    source=load(INPUT/'base/raw_paths_selected.json.gz')
    replay={r['watch_key']:r for r in rows(PRIVATE/'REPLAY_ROWS.jsonl.gz')}
    economics={r['watch_key']:r for r in rows(PRIVATE/'ECONOMICS_ROWS.jsonl.gz')}
    check('all_1600_identity_set',set(replay)==set(economics)==set(r['watch_key'] for r in ee)==set(trace_receipts))
    independently_computed=[]
    for i,entry in enumerate(ee,1):
        current_key=entry['watch_key'];r=replay[current_key];e=economics[current_key]
        trace_file=PRIVATE/'FULL_TRACE'/(current_key.replace('|','_')+'.jsonl.gz')
        check('trace_hash',sha(trace_file)==trace_receipts[current_key]['trace_sha256'])
        stream=list(rows(trace_file));day=entry['session'];last=900 if day<'2024-11-05' else 925
        expected_minutes=list(range(541,691))+[691]+list(range(751,last+1))+[901 if last==900 else 931]
        check('full_dated_slot_coverage',[x['bar_end_minute'] for x in stream]==expected_minutes)
        prev=None;accepted=None;pending=set();segment=0;run_count=0;run_active=False;dwell=0;entered=None
        for row in stream:
            s=row['state'];p=row['path'];t=s['as_of'];meta=s['bar_metadata'] or {}
            if s['numeric_status']=='ACCEPTED':
                reset=bool(pending) or (accepted is not None and (accepted['t']+1!=t or accepted['source']!=meta['source'] or accepted['auction']!=meta['auction'])) or 'SEGMENT_RESET_NO_GAP_RETURN' in s['events']
                if accepted is None:segment=1
                elif reset:segment+=1
                accepted=meta;pending.clear()
            else:pending.add(s['numeric_status'])
            expected_segment=f'{current_key}:S{segment:04d}'
            check('independent_Path_segment',p['causal_segment_id']==expected_segment)
            expected_primary=s['primary'] if s['current_semantics_observed'] else None
            check('observed_null_distinction',p['Primary_or_null']==expected_primary and (not s['current_semantics_observed'] or (s['numeric_status']=='ACCEPTED' and s['activity']!='INITIALIZING' and s['observed_at']==t)))
            check('Path_copied_directions',p['context_direction']==s['context'] and p['local_direction']==s['leg_direction'])
            ordinal=prev is not None and prev['state']['as_of']+1!=t
            broken=prev is not None and prev['path']['causal_segment_id']!=expected_segment and not prev['path']['causal_segment_id'].endswith(':S0000')
            expected,link,same=event_kinds(prev,s,p,ordinal,broken,run_active)
            check('independent_Path_event_order',[x['event_type'] for x in row['path_events']]==expected)
            check('no_gap_reset_synthetic_transition',not (ordinal or broken or not link) or 'TRANSITION' not in expected)
            if s['current_semantics_observed']:
                if not same:run_count+=1;entered=t;dwell=1
                else:dwell+=1
                run_active=True
                check('independent_Path_run_dwell',p['run_id']==f'{current_key}:R{run_count:05d}' and p['entered_at']==entered and p['dwell_observed_bars']==dwell and p['dwell_scheduled_bars']==t-entered+1)
            else:
                run_active=False;check('null_has_no_run',p['run_id'] is None and p['dwell_observed_bars'] is None)
            safe=s['as_of']==row['bar_end_minute']-540 and row['slot']['scheduled_t']==t
            token=row['input']
            if token is not None:safe=safe and token['t']==t and token['known_at']<=t
            safe=safe and (s['observed_at'] is None or s['observed_at']<=t)
            for obj in [s.get('range_analysis'),s.get('fast_analysis'),s.get('balance')]:
                if obj:
                    for field in ['window_ids','old_window_ids']:
                        safe=safe and all(x<=t for x in obj.get(field,[]))
            for pv in s.get('_structure_pivots') or []:
                safe=safe and pv['t']<=t and pv['confirmed_at']<=t
            if not safe:leakage+=1
            check('causal_cutoff_all_trace_slots',safe)
            prev=row
        check('M0_previous_only',trace_receipts[current_key]['source_reason'] is not None or trace_receipts[current_key]['previous_session']<day)
        scan=decision_scan(stream,entry,check)
        check('Entry_fill_unchanged',r['entry_minute']==entry['fill_minute'] and r['entry_fill_price']==entry['fill_price'] and r['entry_timestamp']==entry['fill_timestamp'])
        actual_trigger=(r['exit_intent']['reason'],r['exit_intent']['minute']) if r['exit_intent'] else None
        check('first_valid_structural_EXIT',scan['trigger']==actual_trigger)
        check('UP_arm_timestamp',scan['first_arm']==r['first_arm_minute'] and [(x['minute'],x['segment']) for x in r['arm_events']]==scan['arms'])
        check('continuity_suspension',[x['minute'] for x in r['observations_suspended']]==scan['losses'])
        check('lifecycle_run_and_protection_counts',scan['pullback']==r['PULLBACK_run_N'] and scan['rise_stop']==r['RISE_STOP_run_N'] and scan['tightened']==[x['minute'] for x in r['protected_tighten_events']] and scan['sequence']==r['exit_last3_distinct_primary'])
        check('post_exit_decision_zero',r['post_exit_decision_N']==0 and scan['decisions']==r['decision_N'])
        if r['exit_intent']:
            check('PULLBACK_alone_SELL_zero',not (r['exit_intent']['primary']=='PULLBACK' and r['exit_intent']['context']==1))
            check('RISE_STOP_alone_SELL_zero',not (r['exit_intent']['primary']=='RISE_STOP' and r['exit_intent']['context']==1))
            check('tighten_alone_SELL_zero','PROTECTED_LEVEL_TIGHTENED_EFFECTIVE_NEXT_BAR' not in r['exit_intent']['state_events'])
        fill=independent_fill(entry,scan['trigger'],source[current_key]['today'])
        check('next_open_5bps_or_exact_session_close',fill[0]==r['sell_minute'] and fill[2]==r['sell_source'] and fill[3]==r['exit_reason'] and ((fill[1] is None and r['sell_price_decimal'] is None) or (fill[1] is not None and fill[1]==Decimal(r['sell_price_decimal']) and math.isclose(float(fill[1]),r['sell_price'],abs_tol=1e-11,rel_tol=0))))
        mm,peak,later=independent_metrics(entry,scan,fill,source[current_key]['today'])
        for name,v in mm.items():
            check('independent_economics_'+name,(v is None and e[name] is None) or (v is not None and e[name] is not None and math.isclose(v,e[name],abs_tol=1e-10,rel_tol=1e-12)))
        check('strictly_later_high_timestamp',peak==e['final_observed_high_minute'] and later==e['later_observed_high_minute'])
        check('EXIT_before_final_high',e['exit_before_final_observed_high']==(fill[0]<peak if fill[0] is not None and peak is not None else None))
        independently_computed.append({**r,**mm,'remaining_source_complete':entry['remaining_source_complete'],'exit_before_final_observed_high':e['exit_before_final_observed_high']})
        if i%400==0:print(json.dumps({'audit_entries':i,'failure_examples_N':len(failures),'future_leakage_N':leakage}),flush=True)
    current_key='TABLES'
    def subset(group,name):
        if name=='ALL_ENTRY_ECONOMICS':return independently_computed
        if name in ('WINNER_CUMULATIVE','WINNER_GE3_DETAILED','WINNER_GE5_DETAILED'):
            k=float(group[2:-1]);return [r for r in independently_computed if r['observed_entry_to_high_pct'] is not None and r['observed_entry_to_high_pct']>=k]
        if name=='WINNER_EXCLUSIVE':
            if group=='UNKNOWN_HIGH':return [r for r in independently_computed if r['observed_entry_to_high_pct'] is None]
            limits={'<1%':(-math.inf,1),'1–<2%':(1,2),'2–<3%':(2,3),'3–<4%':(3,4),'4–<5%':(4,5),'>=5%':(5,math.inf)}
            lo,hi=limits[group];return [r for r in independently_computed if r['observed_entry_to_high_pct'] is not None and lo<=r['observed_entry_to_high_pct']<hi]
        if name=='ARMED_VS_NEVER_ARMED':return [r for r in independently_computed if r['armed_ever']==(group=='armed')]
        if name=='EXIT_REASON_DECOMPOSITION':return [r for r in independently_computed if r['exit_reason']==group]
        raise ValueError(name)
    for name in ['ALL_ENTRY_ECONOMICS','WINNER_CUMULATIVE','WINNER_EXCLUSIVE','WINNER_GE3_DETAILED','WINNER_GE5_DETAILED','ARMED_VS_NEVER_ARMED','EXIT_REASON_DECOMPOSITION','ENTRY_PRIMARY_CONTEXT']:
        for g in load(HERE/(name+'.json')):
            selected=[r for r in independently_computed if r['entry_snapshot']['primary']==g['entry_primary'] and r['entry_snapshot']['context']==g['entry_context']] if name=='ENTRY_PRIMARY_CONTEXT' else subset(g['group'],name)
            check('winner_and_group_denominators',g['denominator_N']==len(selected) and g['sell_filled_N']==sum(r['sell_status']=='FILLED' for r in selected) and g['unresolved_N']==sum(r['sell_status']=='UNRESOLVED' for r in selected))
            for metric,st in g['metrics'].items():
                values=[r[metric] for r in selected if r[metric] is not None]
                check('group_metric_denominators',st['N']==len(values))
                for field,value in [('mean',statistics.fmean(values) if values else None),('median',statistics.median(values) if values else None)]:
                    check('group_metric_'+field,(value is None and st[field] is None) or (value is not None and st[field] is not None and math.isclose(value,st[field],abs_tol=1e-10,rel_tol=1e-12)))
    for name in ['lifecycle.py','replay.py','evaluate.py','reconstruct_trace.py','independent_audit.py','settings.py']:
        tree=ast.parse((HERE/name).read_text())
        check('no_model_fit_or_provider_call',not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr in ('fit','predict','predict_proba','request','urlopen') for x in ast.walk(tree)))
    decision_imports=[x.module for x in ast.walk(ast.parse((HERE/'lifecycle.py').read_text())) if isinstance(x,ast.ImportFrom)]
    check('decision_has_no_future_evaluator_import',decision_imports==['dataclasses'])
    for key,value in identity['budget'].items():check('zero_budget_boundaries',value==1 if key=='new_EXIT_policies' else value==0)
    check('safety_all_false',all(v is False for v in SAFETY.values()))
    result={'saved_at_jst':now(),'status':'BLOCKED_STATE9_STRUCTURAL_EXIT_CAUSAL_LEAKAGE' if leakage else 'BLOCKED_STATE9_STRUCTURAL_EXIT_AUDIT_MISMATCH' if mismatch_total else 'INDEPENDENT_AUDIT_PASS','Entry_N':len(ee),'check_N':sum(counts.values()),'check_counts':dict(counts),'mismatch_N':mismatch_total,'mismatch_examples':failures,'future_causal_leakage_N':leakage,'audit_fit':0,'independent_policy_imports_from_primary':0,'full_RC2_independent_kernel_slots_N':reconstruction['trace_slots_N'],'saved_overlap_N':reconstruction['saved_overlap_N'],'PULLBACK_alone_SELL_N':0 if not mismatch_total else None,'RISE_STOP_alone_SELL_N':0 if not mismatch_total else None,'protected_tighten_alone_SELL_N':0 if not mismatch_total else None,'old_EXIT_access_replay_comparison':0,'Hard1_fixed_stop_trailing':0,'Reentry_Capital':0,'shared_dependencies':['immutable saved raw/source','frozen RC2 response and profile schema','Python runtime, Decimal/Fraction libraries','settings I/O paths/hash helpers; decision, calendar and economics are independently implemented'],'historical_known_at':'UNKNOWN; leakage gate checks stated causal bar_end assumption','safety':SAFETY}
    save(HERE/'INDEPENDENT_AUDIT.json',result);print(json.dumps(result,ensure_ascii=False))
    if failures or leakage:raise SystemExit(2)

if __name__=='__main__':run()
