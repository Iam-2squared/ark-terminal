"""Independent V4 latch/ledger audit. No primary decision/evaluator imports."""
import ast,collections,gzip,hashlib,json,math,statistics
from fractions import Fraction
from pathlib import Path
from settings import HERE,V2,PUBLIC_V2,PRIVATE,V3_PRIVATE,V3_PUBLIC,SAFETY,BUDGET,now,sha,load,rows,save
HALF=Fraction(1,2)
C_REASON='LOCAL_UP_STRUCTURE_GUARD_BROKEN'
D_REASON='LOCAL_RECOVERY_FAILED'

def is_observed(r):
    state=r['state'];path=r['path']
    return state['numeric_status']=='ACCEPTED' and state['current_semantics_observed'] is True and state['observed_at']==state['as_of'] and path['Primary_or_null'] is not None

def joined(a,b):
    return a is not None and is_observed(a) and is_observed(b) and a['state']['as_of']+1==b['state']['as_of'] and a['path']['causal_segment_id']==b['path']['causal_segment_id']

def audit_clock(day,a,b):
    end=900 if day<'2024-11-05' else 925
    return sum(max(0,min(b,hi)-max(a,lo)) for lo,hi in [(540,690),(750,end)])

def raw_ok(a):
    if len(a)!=7 or not all(math.isfinite(float(v)) for v in a):return False
    o,h,l,c=(Fraction(str(v)) for v in a[1:5])
    return l>0 and l<=o<=h and l<=c<=h and a[5]>=0 and a[6]>=0

def independent_fill(entry,intent,raw):
    day=entry['session'];end=900 if day<'2024-11-05' else 925;close=900 if day<'2024-11-05' else 930
    firstam=min((int(a[0]) for a in raw if a[0]<690),default=-1)
    firstpm=min((int(a[0]) for a in raw if 750<=a[0]<end),default=-1)
    excluded={540,750,firstam,firstpm}
    selected=None
    if intent is not None:
        for a in raw:
            m=int(a[0])
            if raw_ok(a) and (540<=m<690 or 750<=m<end) and m not in excluded and m>=intent[1] and m>entry['fill_minute']:
                selected=a;break
    if selected is not None:return ('FILLED',int(selected[0]),Fraction(str(selected[1]))*Fraction(9995,10000),'NEXT_ELIGIBLE_REGULAR_RAW_OPEN',intent[0])
    terminal=[a for a in raw if int(a[0])==close and raw_ok(a)]
    if len(terminal)==1:return ('FILLED',close,Fraction(str(terminal[0][4]))*Fraction(9995,10000),'PLANNED_TERMINAL_AUCTION_CLOSE',intent[0] if intent else 'SESSION_CLOSE')
    return ('UNRESOLVED',None,None,None,'UNRESOLVED')

def independent_metrics(entry,ref,fill,baseline,raw):
    day=entry['session'];fp=Fraction(str(entry['fill_price']));fm=entry['fill_minute'];status,sm,sell,source,reason=fill
    filled=status=='FILLED';end=900 if day<'2024-11-05' else 925;close=900 if day<'2024-11-05' else 930
    good=[a for a in raw if raw_ok(a) and fm<int(a[0])<=close]
    held=[Fraction(str(a[2])) for a in good if filled and int(a[0])<sm]
    later=[a for a in good if filled and int(a[0])>sm]
    high=max((Fraction(str(a[2])) for a in later),default=None)
    hm=min((int(a[0]) for a in later if Fraction(str(a[2]))==high),default=None)
    ret=100*(sell/fp-1) if filled else None
    mfe=baseline['observed_entry_to_high_pct'];peak=baseline['final_observed_high_minute']
    old_intent=baseline['exit_intent']['minute'] if baseline['exit_intent'] else baseline['planned_close_intent_minute']
    intent=ref['trigger'][1] if ref['trigger'] else end
    fraction_mfe=Fraction(str(mfe)) if mfe is not None else None
    result={
        'realized_return_pct':float(ret) if ret is not None else None,
        'MFE_realization_pct':float(100*ret/fraction_mfe) if filled and fraction_mfe is not None and fraction_mfe>0 else None,
        'peak_giveback_pp':float(fraction_mfe-ret) if filled and fraction_mfe is not None else None,
        'pre_sell_observed_peak_giveback_pp':float(100*(max(held)/fp-1)-ret) if held else None,
        'later_missed_upside_pct':float(max(0,100*(high/sell-1))) if high is not None else None,
        'later_missed_upside_entry_basis_pp':float(max(0,100*(high-sell)/fp)) if high is not None else None,
        'peak_price_giveback_pct':float(100*(Fraction(str(baseline['observed_high']))-sell)/Fraction(str(baseline['observed_high']))) if filled and baseline['observed_high'] is not None else None,
        'holding_active_minutes':audit_clock(day,fm,sm) if filled else None,
        'exit_to_later_high_active_minutes':audit_clock(day,sm,hm) if hm is not None else None,
        'entry_to_arm_active_minutes':audit_clock(day,fm,ref['first_arm']) if ref['first_arm'] is not None else None,
        'arm_to_exit_active_minutes':audit_clock(day,ref['first_arm'],intent) if ref['first_arm'] is not None else None,
        'observed_entry_to_high_pct':mfe,'entry_to_high_active_minutes':baseline['entry_to_high_active_minutes'],
        'exit_before_final_observed_high':sm<peak if filled and peak is not None else None,
        'intent_advance_vs_V3_active_minutes':audit_clock(day,fm,old_intent)-audit_clock(day,fm,intent),
        'sell_advance_vs_V3_active_minutes':baseline['holding_active_minutes']-audit_clock(day,fm,sm) if filled and baseline['sell_status']=='FILLED' else None,
        'later_observed_high':float(high) if high is not None else None,'later_observed_high_minute':hm,
    }
    return result

def equivalent(a,b):
    if a is None or b is None:return a is None and b is None
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-10)
    return a==b

def label_of(value):
    if value is None:return 'UNKNOWN'
    if value<1:return '<1%'
    if value<2:return '1–<2%'
    if value<3:return '2–<3%'
    if value<4:return '3–<4%'
    if value<5:return '4–<5%'
    return '>=5%'

def reference_scan(stream,entry,actual_meta,check):
    """Boolean phase latch; full segment ledger, independently formed next-bar guard."""
    active=False;lost=False;first_arm=None;arms=[];losses=[];old_position=None;old_input=None
    ledger=[];guard=None;floor=None;floor_updates=[];floor_L=[];floor_resets=0;floor_creations=0;floor_tightens=0;floor_events=[];sequence=[];trigger=None;decisions=0;prefix_pivots=0;position_pivots=[]
    eligible=set();higher=set();creations=0;tightens=0;resets=0;updates=[];pull=set();stop=set();main_tightens=0
    end=900 if entry['session']<'2024-11-05' else 925
    for r in stream:
        minute=r['bar_end_minute'];s=r['state'];p=r['path'];t=s['as_of']
        if minute>end:break
        check('trace_bar_end_and_input_cutoff',minute==t+540 and (r['input'] is None or r['input']['known_at']<=t),causal=True)
        usable=is_observed(r);input_link=joined(old_input,r)
        if not input_link:
            if guard is not None:resets+=1
            guard=None;ledger=[]
        if not input_link:
            if floor is not None:
                floor_resets+=1;floor_events.append({'type':'RECOVERY_FLOOR_RESET','minute':minute,'before':floor,'current_segment':p['causal_segment_id']})
            floor=None
        current_pivot=s['local_pivot_confirmed']
        if usable and current_pivot is not None:
            check('source_local_pivot_causality',current_pivot['extremum_t']<=current_pivot['confirmed_at']<=t,causal=True)
        if minute<entry['fill_minute']:
            if usable and current_pivot is not None and current_pivot not in ledger:
                check('prefix_pivot_confirmed_order',not ledger or ledger[-1]['confirmed_at']<current_pivot['confirmed_at'],causal=True)
                ledger.append(dict(current_pivot));prefix_pivots+=1
            old_input=r;continue
        before=guard if guard is not None and guard['effective_from']<=t and guard['segment']==p['causal_segment_id'] and usable else None
        floor_before=floor if floor is not None and floor['effective_from']<=t and floor['segment']==p['causal_segment_id'] and usable else None
        prior_suffix=[dict(x) for x in ledger[-3:]]
        link=joined(old_position,r);event_names={e['event_type'] for e in r['path_events']}
        if active and old_position is not None and not link:
            if not lost:losses.append(minute)
            lost=True
        if not link:sequence=[]
        if usable:
            if not sequence or sequence[-1]!=p['Primary_or_null']:sequence=(sequence+[p['Primary_or_null']])[-3:]
            if p['Primary_or_null']=='PULLBACK':pull.add(p['run_id'])
            if p['Primary_or_null']=='RISE_STOP':stop.add(p['run_id'])
            if 'PROTECTED_LEVEL_TIGHTENED_EFFECTIVE_NEXT_BAR' in s['events']:main_tightens+=1
        if lost:
            if usable:
                active=s['context']==1;lost=False
                if active:
                    first_arm=minute if first_arm is None else first_arm;arms.append((minute,p['causal_segment_id']))
        elif not active:
            if usable and s['context']==1:
                active=True;first_arm=minute if first_arm is None else first_arm;arms.append((minute,p['causal_segment_id']))
        elif link:
            prior=old_position['state']
            if prior['context']==1 and s['context']==-1:
                check('main_A_unchanged',s['protected_before'] is not None and prior['protected_after_effective_next']==s['protected_before'] and prior['protected_effective_from'] is not None and prior['protected_effective_from']<=t and Fraction(s['close_u'])<=Fraction(s['protected_before'])-HALF and 'STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL' in s['events'] and 'CONTEXT_CHANGE' in event_names)
                trigger=('UP_STRUCTURE_REVERSED',minute)
            elif prior['context']==1 and s['context']==0 and s['primary']=='RANGE' and s['activity']=='BALANCED':
                check('main_B_unchanged',s['balance'] is not None and s['balance']['established_at']==t and len(s['balance']['window_ids'])==10 and max(s['balance']['window_ids'])==t and s['range_analysis']['guard'] is False and 'CONTEXT_RETIRED_BY_OBSERVED_BALANCE' in s['events'] and {'RANGE_ENTER','CONTEXT_CHANGE'}<=event_names)
                trigger=('UP_STRUCTURE_RETIRED_BY_RANGE',minute)
        if trigger is None and active and not lost and usable and input_link and before is not None and s['context']==1 and s['protected_before'] is not None and minute<end:
            if Fraction(before['x'])>Fraction(s['protected_before']) and Fraction(s['close_u'])<=Fraction(before['x'])-HALF:
                trigger=(C_REASON,minute)
                check('C_requires_UP_and_exact_break',s['context']==1 and Fraction(before['x'])>Fraction(s['protected_before']) and Fraction(s['close_u'])<=Fraction(before['x'])-HALF)
                check('C_effective_next_bar',before['effective_from']==before['updated_at']+1 and before['effective_from']<=t and before['updated_at']<t,causal=True)
                check('C_same_segment',before['segment']==p['causal_segment_id'] and input_link)
        update=None
        if trigger is None and active and not lost and usable and s['context']==1 and len(prior_suffix)==3 and [x['kind'] for x in prior_suffix]==['L','H','L']:
            a,h,b=prior_suffix;key=(p['causal_segment_id'],a['confirmed_at'],h['confirmed_at'],b['confirmed_at'])
            check('LHL_confirmed_before_t',all(x['confirmed_at']<t for x in prior_suffix),causal=True)
            check('LHL_confirmation_order',a['confirmed_at']<h['confirmed_at']<b['confirmed_at'],causal=True)
            if all(x['confirmed_at']<t for x in prior_suffix):
                eligible.add(key)
                higher_low=Fraction(b['x'])-Fraction(a['x'])>=HALF
                if higher_low:higher.add(key)
                if higher_low and (guard is None or Fraction(b['x'])>Fraction(guard['x'])) and Fraction(s['close_u'])>=Fraction(h['x'])+HALF:
                    was=guard;initial=was is None
                    guard={'x':b['x'],'segment':p['causal_segment_id'],'effective_from':t+1,'updated_at':t,'created_at':t if initial else was['created_at'],'activation_minute':minute,'pivot_sequence':prior_suffix}
                    distance=Fraction(b['x'])-Fraction(s['protected_after_effective_next']) if s['protected_after_effective_next'] is not None else None
                    update={'type':'LOCAL_GUARD_CREATED' if initial else 'LOCAL_GUARD_TIGHTENED','minute':minute,'scheduled_t':t,'before':was,'after':guard,'close_u':s['close_u'],'context':s['context'],'main_protected_before':s['protected_before'],'main_protected_after_effective_next':s['protected_after_effective_next'],'guard_to_main_distance_u_fraction':str(distance) if distance is not None else None,'guard_to_main_distance_u':float(distance) if distance is not None else None,'structure_pivots_exact':s['_structure_pivots'],'context_extreme_exact':s['_context_extreme']}
                    check('guard_higher_low_and_progress',higher_low and Fraction(s['close_u'])>=Fraction(h['x'])+HALF)
                    check('guard_monotonicity',initial or Fraction(guard['x'])>Fraction(was['x']))
                    check('guard_next_bar_not_current',guard['effective_from']==t+1 and before==was,causal=True)
                    creations+=initial;tightens+=not initial;updates.append(update)
        fallback_reason=trigger[0] if trigger else None
        if trigger is None and active and not lost and usable and input_link and s['context']==1 and floor_before is not None and s['protected_before'] is not None and minute<end:
            broken=Fraction(s['close_u'])+HALF<=Fraction(floor_before['x'])
            if Fraction(floor_before['x'])>Fraction(s['protected_before']) and broken:
                trigger=(D_REASON,minute)
                check('D_UP_exact_break',s['context']==1 and Fraction(floor_before['x'])>Fraction(s['protected_before']) and broken)
                check('D_next_bar_causality',floor_before['effective_from']==floor_before['updated_at']+1 and floor_before['updated_at']<t and floor_before['effective_from']<=t,causal=True)
                check('D_same_segment',input_link and floor_before['segment']==p['causal_segment_id'])
                floor_events.append({'type':'RECOVERY_FLOOR_BROKEN','minute':minute,'floor_before':dict(floor_before),'context':s['context'],'primary':p['Primary_or_null'],'close_u':s['close_u'],'main_protected_before':s['protected_before']})
        floor_update=None
        if trigger is None:
            if usable and current_pivot is not None and current_pivot['kind']=='L':floor_L.append({'segment':p['causal_segment_id'],'pivot':dict(current_pivot)})
            qualifies=active and not lost and usable and s['context']==1 and current_pivot is not None and current_pivot['kind']=='L' and current_pivot['generation_reason']=='DC_CONFIRMED'
            if qualifies:
                check('floor_L_DC_confirmed_causal',current_pivot['extremum_t']<=current_pivot['confirmed_at']<=t,causal=True)
                if s['protected_before'] is not None and Fraction(current_pivot['x'])>Fraction(s['protected_before']) and (floor is None or Fraction(current_pivot['x'])>Fraction(floor['x'])):
                    previous_floor=floor;initial=floor is None
                    floor={'x':current_pivot['x'],'segment':p['causal_segment_id'],'effective_from':t+1,'updated_at':t,'created_at':t if initial else previous_floor['created_at'],'activation_minute':minute,'local_L_exact':dict(current_pivot)}
                    floor_update={'type':'RECOVERY_FLOOR_CREATED' if initial else 'RECOVERY_FLOOR_TIGHTENED','minute':minute,'scheduled_t':t,'before':previous_floor,'after':floor,'context':s['context'],'close_u':s['close_u'],'main_protected_before':s['protected_before'],'main_protected_after_effective_next':s['protected_after_effective_next'],'local_L_exact':dict(current_pivot),'floor_to_main_distance_before_u':float(Fraction(current_pivot['x'])-Fraction(s['protected_before']))}
                    check('floor_kind_DC_context_above_main',current_pivot['kind']=='L' and current_pivot['generation_reason']=='DC_CONFIRMED' and s['context']==1 and Fraction(floor['x'])>Fraction(s['protected_before']))
                    check('floor_monotonic',initial or Fraction(floor['x'])>Fraction(previous_floor['x']))
                    check('floor_effective_next_not_same_bar',floor['effective_from']==t+1 and floor_before==previous_floor,causal=True)
                    floor_creations+=initial;floor_tightens+=not initial;floor_updates.append(floor_update);floor_events.append(floor_update)
        expected={'minute':minute,'scheduled_t':t,'phase':'UP_STRUCTURE_ACTIVE' if active else 'PRE_UP_STRUCTURE','suspended':lost,'observed':usable,'same_segment_observed_connection':input_link,'segment':p['causal_segment_id'],'primary':p['Primary_or_null'],'context':s['context'],'protected_before':s['protected_before'],'close_u':s['close_u'],'local_pivot_confirmed_exact':current_pivot,'prior_local_pivot_suffix_exact':prior_suffix,'local_guard_before':before,'local_guard_after_effective_next':guard,'guard_update':update,'exit_intent_reason':trigger[0] if trigger else None}
        expected.update(recovery_floor_before=floor_before,recovery_floor_after_effective_next=floor,recovery_floor_update=floor_update,V3_fallback_intent_reason_on_bar=fallback_reason)
        check('decision_metadata_exact',decisions<len(actual_meta) and expected==actual_meta[decisions])
        check('local_pivot_exact_original_field',decisions<len(actual_meta) and actual_meta[decisions]['local_pivot_confirmed_exact']==current_pivot)
        if not input_link:check('no_cross_segment_carry',before is None and prior_suffix==[] and floor_before is None)
        if usable and current_pivot is not None and current_pivot not in ledger:
            check('position_pivot_confirmed_order',not ledger or ledger[-1]['confirmed_at']<current_pivot['confirmed_at'],causal=True)
            ledger.append(dict(current_pivot));position_pivots.append({'segment':p['causal_segment_id'],'pivot':dict(current_pivot)})
        old_position=r;old_input=r;decisions+=1
        if trigger is not None:break
    return {'trigger':trigger,'first_arm':first_arm,'arms':arms,'losses':losses,'decisions':decisions,'active':active,'lost':lost,'suffix_sequence':sequence,'guard':guard,'updates':updates,'creation_N':creations,'tighten_N':tightens,'reset_N':resets,'eligible_N':len(eligible),'higher_N':len(higher),'observed_pivots':position_pivots,'prefix_pivot_N':prefix_pivots,'pullback_N':len(pull),'rise_stop_N':len(stop),'main_tighten_N':main_tightens,'last':old_position,'guard_before_final':before,'floor_before_final':floor_before,'floor':floor,'floor_updates':floor_updates,'floor_L':floor_L,'floor_reset_N':floor_resets,'floor_creation_N':floor_creations,'floor_tighten_N':floor_tightens,'floor_events':floor_events}

def run():
    counts=collections.Counter();fails=[];mismatch=leak=lineage=trace_missing=0;current=None
    def check(name,condition,causal=False,lineage_check=False,trace_check=False):
        nonlocal mismatch,leak,lineage,trace_missing
        counts[name]+=1
        if not condition:
            mismatch+=1;leak+=causal;lineage+=lineage_check;trace_missing+=trace_check
            if len(fails)<40:fails.append({'watch_key':current,'check':name})
    def statcheck(name,published,values):
        values=[v for v in values if v is not None]
        check(name+'_N',published['N']==len(values))
        check(name+'_mean',equivalent(published['mean'],statistics.fmean(values) if values else None))
        check(name+'_median',equivalent(published['median'],statistics.median(values) if values else None))
    source=load(V2/'MANIFEST.json')['components']
    entry_file=V2/'FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'
    check('Frozen_Entry_exact_bytes',sha(entry_file)==source['FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz']['sha256']=='e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb',lineage_check=True)
    all_entry=list(rows(entry_file));ee=[e for e in all_entry if e['entry_status']=='FIRST_ENTRY']
    check('Frozen_Entry_N',len(all_entry)==2155 and len(ee)==1600,lineage_check=True)
    identity=load(PUBLIC_V2/'IDENTITY_RECEIPT.json')
    for n,pin in identity['frozen_identity'].items():check('six_Frozen_semantic_hashes',sha(PUBLIC_V2/'FROZEN_SOURCE'/n)==pin['expected']==pin['actual'],lineage_check=True)
    original=load(V3_PUBLIC/'FINAL_PROVENANCE_MANIFEST.json')
    for n,item in original['files'].items():check('V3_public_component_hash',sha(V3_PUBLIC/n)==item['sha256'],lineage_check=True)
    check('V3_audited_READY',original['status']=='STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_EVIDENCE_READY' and load(V3_PUBLIC/'INDEPENDENT_AUDIT.json')['mismatch_N']==0 and load(V3_PUBLIC/'INDEPENDENT_AUDIT.json')['future_causal_leakage_N']==0,lineage_check=True)
    reused=load(HERE/'V3_TRACE_REUSE_RECEIPT.json')
    for n,pin in [('ECONOMICS_ROWS.jsonl.gz','V3_economics_sha256'),('REPLAY_ROWS.jsonl.gz','V3_replay_rows_sha256'),('PAIRED_ROWS.jsonl.gz','V3_paired_rows_sha256')]:check('V3_saved_results_exact_bytes',sha(V3_PRIVATE/n)==reused[pin],lineage_check=True)
    check('raw_source_exact_bytes',sha(V2/'SAVED_INPUTS/raw_paths_selected.json.gz')==source['SAVED_INPUTS/raw_paths_selected.json.gz']['sha256'],lineage_check=True)
    freeze=load(HERE/'CONTRACT_FREEZE_RECEIPT.json')
    check('S0_contract_unchanged',sha(HERE/'CONTRACT.md')==freeze['contract_sha256'],lineage_check=True)
    for n,d in {**freeze['decision_code_hashes'],**freeze['evaluation_and_selection_code_hashes']}.items():check('S0_decision_evaluation_gate_unchanged',sha(HERE/n)==d,lineage_check=True)
    for n in ['frozen_v2_lifecycle.py','local_guard.py','reused_clock.py','reused_fill.py']:check('V3_A_B_C_PRE_quality_fill_clock_exact_bytes',sha(HERE/n)==sha(V3_PUBLIC/n),lineage_check=True)
    actual_get=load(HERE/'GITHUB_CONTRACT_GET_RECEIPT.json')
    check('contract_actual_GET_before_replay',actual_get['actual_GET_verified'] and actual_get['contract_saved_before_primary_V4_replay'] and actual_get['S0_actual_HEAD']!='c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad')
    once=load(PRIVATE/'RUN_ONCE.json');check('one_primary_V4_replay',once['primary_replay_invocation_N']==1 and once['status']=='COMPLETE' and once['started_at_jst']>freeze['saved_at_jst'])
    raw=load(V2/'SAVED_INPUTS/raw_paths_selected.json.gz')
    old={r['watch_key']:r for r in rows(V3_PRIVATE/'ECONOMICS_ROWS.jsonl.gz')}
    old_replay={r['watch_key']:r for r in rows(V3_PRIVATE/'REPLAY_ROWS.jsonl.gz')}
    old_pairs={r['watch_key']:r for r in rows(V3_PRIVATE/'PAIRED_ROWS.jsonl.gz')}
    new={r['watch_key']:r for r in rows(PRIVATE/'ECONOMICS_ROWS.jsonl.gz')}
    replay={r['watch_key']:r for r in rows(PRIVATE/'REPLAY_ROWS.jsonl.gz')}
    paired={r['watch_key']:r for r in rows(PRIVATE/'PAIRED_ROWS.jsonl.gz')}
    dr={r['watch_key']:r for r in load(PRIVATE/'DECISION_TRACE_RECEIPTS.json')}
    check('all1600_identity_sets',set(old)==set(old_replay)==set(old_pairs)==set(new)==set(replay)==set(paired)==set(dr)=={e['watch_key'] for e in ee},lineage_check=True)
    independent_pairs=[];refs=[];non_d_unchanged=0;d_valid=0
    for entry in ee:
        current=entry['watch_key'];a=old[current];r=replay[current];n=new[current]
        check('Frozen_Entry_identity_and_fill',r['entry_minute']==entry['fill_minute'] and r['entry_timestamp']==entry['fill_timestamp'] and r['entry_fill_price']==entry['fill_price'] and r['symbol']==entry['symbol'] and r['session']==entry['session'],lineage_check=True)
        check('V3_existing_pair_join_identity',old_pairs[current]['v3']==a and all(a[k]==old_replay[current][k] for k in old_replay[current]),lineage_check=True)
        path=V2/'FULL_TRACE'/(current.replace('|','_')+'.jsonl.gz')
        check('Full_State9_Path_trace_exact_reuse',sha(path)==source['FULL_TRACE/'+path.name]['sha256']==dr[current]['source_trace_sha256'],trace_check=True)
        mp=PRIVATE/'DECISION_TRACE'/path.name
        check('V4_metadata_hash',sha(mp)==dr[current]['sha256'])
        meta=list(rows(mp));ref=reference_scan(rows(path),entry,meta,check);refs.append(ref)
        actual=(r['exit_intent']['reason'],r['exit_intent']['minute']) if r['exit_intent'] else None
        check('first_valid_A_B_C_D_precedence',actual==ref['trigger'])
        check('UP_arm_PRE_unchanged',ref['first_arm']==r['first_arm_minute']==a['first_arm_minute'])
        check('arm_events',[(x['minute'],x['segment']) for x in r['arm_events']]==ref['arms'])
        check('observation_suspensions',[x['minute'] for x in r['observations_suspended']]==ref['losses'])
        check('phase_quality',r['phase_at_last_decision']==('UP_STRUCTURE_ACTIVE' if ref['active'] else 'PRE_UP_STRUCTURE') and r['suspended_at_last_decision']==ref['lost'])
        check('post_exit_decision_zero',r['post_exit_decision_N']==0 and ref['decisions']==r['decision_N']==len(meta))
        check('local_pivot_exact_original_fields',r['local_pivot_observed_exact']==ref['observed_pivots'])
        check('floor_current_L_exact_fields',r['recovery_local_L_evaluated_exact']==ref['floor_L'])
        check('floor_all_events_exact',r['recovery_floor_events']==ref['floor_events'])
        check('floor_counts',r['recovery_floor_creation_N']==ref['floor_creation_N'] and r['recovery_floor_tighten_N']==ref['floor_tighten_N'] and r['recovery_floor_reset_with_level_N']==ref['floor_reset_N'] and r['recovery_floor_established_ever']==bool(ref['floor_creation_N']))
        check('guard_mechanics_unchanged',r['local_guard_creation_N']==ref['creation_N'] and r['local_guard_tighten_N']==ref['tighten_N'] and r['local_guard_reset_with_level_N']==ref['reset_N'] and r['LHL_eligible_sequence_N']==ref['eligible_N'] and r['LHL_higher_low_sequence_N']==ref['higher_N'] and r['prefix_local_pivot_N']==ref['prefix_pivot_N'])
        check('local_primary_runs_and_main_tightens',r['PULLBACK_run_N']==ref['pullback_N'] and r['RISE_STOP_run_N']==ref['rise_stop_N'] and r['protected_tighten_N']==ref['main_tighten_N'])
        check('last3_Primary',r['exit_last3_distinct_primary']==ref['suffix_sequence'])
        if ref['trigger'] is not None and ref['trigger'][0]==D_REASON:
            d_valid+=1;intent=r['exit_intent'];before=ref['floor_before_final'];last=ref['last']
            check('D_intent_exact_floor_causality',intent['recovery_floor_before']==before and before['local_L_exact']['kind']=='L' and before['local_L_exact']['generation_reason']=='DC_CONFIRMED' and before['local_L_exact']['confirmed_at']<=before['updated_at']<last['state']['as_of'],causal=True)
            check('D_intent_exact_market_fields',intent['context']==last['state']['context']==1 and intent['primary']==last['path']['Primary_or_null'] and intent['protected_before']==last['state']['protected_before'] and intent['close_u']==last['state']['close_u'])
            prior_intent=a['exit_intent']['minute'] if a['exit_intent'] else a['planned_close_intent_minute']
            check('D_genuinely_before_V3_intent',intent['minute']<prior_intent)
            check('D_age_and_segment',intent['floor_age_since_creation_bars']==last['state']['as_of']-before['created_at'] and intent['floor_age_since_update_bars']==last['state']['as_of']-before['updated_at'] and intent['segment']==before['segment'])
        else:
            unchanged=r['exit_intent']==a['exit_intent'] and all(r[k]==a[k] for k in ['sell_status','sell_minute','sell_timestamp','sell_price','sell_price_decimal','sell_raw_price','sell_source','exit_reason','planned_close_intent_minute'])
            non_d_unchanged+=unchanged;check('non_D_V3_outcome_exact_unchanged',unchanged)
        fill=independent_fill(entry,ref['trigger'],raw[current]['today']);status,sm,sell,origin,reason=fill
        check('canonical_fill_status_time_price_source',status==r['sell_status'] and sm==r['sell_minute'] and equivalent(float(sell) if sell is not None else None,r['sell_price']) and origin==r['sell_source'] and reason==r['exit_reason'])
        check('sell_exact_decimal_5bps_no_double_Entry_cost',r['sell_adjustment_bps']==5 and r['commission']==0 and (sell is None and r['sell_price_decimal'] is None or sell is not None and Fraction(r['sell_price_decimal'])==sell))
        computed=independent_metrics(entry,ref,fill,a,raw[current]['today'])
        for k,value in computed.items():check('independent_economics_'+k,equivalent(n[k],value))
        opportunity=['observed_entry_to_high_pct','observed_high','final_observed_high_minute','latest_tied_observed_high_minute','remaining_source_complete','entry_to_high_active_minutes','observed_High_unknown','exclusive_bucket']
        check('Frozen_opportunity_bucket_exact_reuse',all(n[k]==a[k] for k in opportunity) and a['exclusive_bucket']==label_of(a['observed_entry_to_high_pct']))
        check('V3_V4_saved_pair_exact_join',paired[current]['v3']==a and paired[current]['v4']==n and paired[current]['exclusive_bucket']==a['exclusive_bucket'],lineage_check=True)
        expected=dict(n);expected.update(computed);independent_pairs.append({'watch_key':current,'exclusive_bucket':a['exclusive_bucket'],'v3':a,'v4':expected})
    current=None
    targets={'2–<3%','3–<4%','4–<5%'}
    def is_d(p):return p['v4']['exit_intent'] is not None and p['v4']['exit_intent']['reason']==D_REASON
    def old_reason(p):return p['v3']['exit_intent']['reason'] if p['v3']['exit_intent'] else 'SESSION_CLOSE'
    def subset(name,label):
        allp=independent_pairs;d=[p for p in allp if is_d(p)]
        if name=='ALL_ENTRY_ECONOMICS':return allp
        if name=='PRIMARY_2_TO_5':return [p for p in allp if p['exclusive_bucket'] in targets] if label=='2–<5%_COMBINED' else [p for p in allp if p['exclusive_bucket']==('>=5%' if label=='>=5%_PROTECTION' else label)]
        if name=='EXCLUSIVE_ENTRY_HIGH_ALL':return [p for p in allp if p['exclusive_bucket']==label]
        if name=='WINNER_GE5_PROTECTION':return [p for p in allp if p['exclusive_bucket']=='>=5%']
        if name=='EXIT_D_PAIRED_DIAGNOSIS':return d
        if name=='EXIT_D_EXCLUSIVE':return [p for p in d if p['exclusive_bucket']==label]
        if name=='WINNER_GE5_EXIT_D':return [p for p in d if p['exclusive_bucket']=='>=5%']
        if name=='EXIT_D_V3_REASON':return [p for p in d if old_reason(p)==label]
        if name=='V4_EXIT_REASON':return [p for p in allp if p['v4']['exit_reason']==label]
        if name=='V4_EXIT_REASON_EXCLUSIVE':
            reason,b=label.split('/',1);return [p for p in allp if p['v4']['exit_reason']==reason and p['exclusive_bucket']==b]
        if name=='TARGET_V3_EXIT_A':return [p for p in allp if p['exclusive_bucket'] in targets and old_reason(p)=='UP_STRUCTURE_REVERSED']
        raise ValueError(name)
    table_names=['PRIMARY_2_TO_5','EXCLUSIVE_ENTRY_HIGH_ALL','WINNER_GE5_PROTECTION','ALL_ENTRY_ECONOMICS','EXIT_D_PAIRED_DIAGNOSIS','EXIT_D_EXCLUSIVE','WINNER_GE5_EXIT_D','EXIT_D_V3_REASON','V4_EXIT_REASON','V4_EXIT_REASON_EXCLUSIVE','TARGET_V3_EXIT_A']
    for name in table_names:
        for g in load(HERE/(name+'.json')):
            ps=subset(name,g['group']);check('all_subgroup_denominators',len(ps)==g['denominator_N'])
            check('exclusive_bucket_decomposition',g['exclusive_bucket_N']==dict(collections.Counter(p['exclusive_bucket'] for p in ps)))
            check('group_EXIT_D_N',g['EXIT_D_N']==sum(is_d(p) for p in ps))
            common=[p for p in ps if p['v3']['sell_status']=='FILLED' and p['v4']['sell_status']=='FILLED']
            check('common_filled_denominator',g['return_common_filled_N']==len(common))
            check('negative_positive_changes',g['negative_to_positive_N']==sum(p['v3']['realized_return_pct']<0<p['v4']['realized_return_pct'] for p in common) and g['positive_to_negative_N']==sum(p['v4']['realized_return_pct']<0<p['v3']['realized_return_pct'] for p in common))
            for version in ['v3','v4']:
                items=[p[version] for p in ps];filled=[r['realized_return_pct'] for r in items if r['sell_status']=='FILLED'];neg=[v for v in filled if v<0];before=[r['exit_before_final_observed_high'] for r in items if r['exit_before_final_observed_high'] is not None]
                values={'sell_filled_N':len(filled),'unresolved_N':len(items)-len(filled),'positive_N':sum(v>0 for v in filled),'negative_N':len(neg),'positive_rate_pct':100*sum(v>0 for v in filled)/len(filled) if filled else None,'worst_return_pct':min(filled) if filled else None,'below_minus1_N':sum(v<-1 for v in filled),'below_minus2_N':sum(v<-2 for v in filled),'EXIT_before_final_High_N':sum(before),'EXIT_before_final_High_denominator_N':len(before),'EXIT_before_final_High_rate_pct':100*sum(before)/len(before) if before else None}
                for k,v in values.items():check('summary_'+k,equivalent(g[version][k],v))
                statcheck('negative_return',g[version]['negative_return'],neg)
                statcheck('common_return',g['return_common_filled'][version],[p[version]['realized_return_pct'] for p in common])
                for k,pub in g[version]['metrics'].items():statcheck('group_metric',pub,[r[k] for r in items])
            for k,pub in g['paired_delta'].items():
                deltas=[p['v4'][k]-p['v3'][k] for p in ps if p['v4'][k] is not None and p['v3'][k] is not None]
                statcheck('paired_delta',pub,deltas)
                for which in ['mean','median']:
                    a=g['v3']['metrics'][k][which];b=g['v4']['metrics'][k][which]
                    check('group_difference',equivalent(g['group_difference'][k][which],b-a if a is not None and b is not None else None))
            for which in ['mean','median']:
                a=g['return_common_filled']['v3'][which];b=g['return_common_filled']['v4'][which]
                check('common_group_difference',equivalent(g['return_common_group_difference'][which],b-a if a is not None and b is not None else None))
            for k in ['intent_advance_vs_V3_active_minutes','sell_advance_vs_V3_active_minutes']:statcheck('timing',g[k],[p['v4'][k] for p in ps])
    mech=load(HERE/'RECOVERY_FLOOR_MECHANICS.json');dref=[r for r in refs if r['trigger'] is not None and r['trigger'][0]==D_REASON]
    d=[p for p in independent_pairs if is_d(p)];updates=[u for r in refs for u in r['floor_updates']]
    aggregate={'Recovery_Floor_established_position_N':sum(bool(r['floor_creation_N']) for r in refs),'floor_never_established_N':sum(not r['floor_creation_N'] for r in refs),'floor_creation_N':sum(r['floor_creation_N'] for r in refs),'floor_tighten_N':sum(r['floor_tighten_N'] for r in refs),'floor_reset_with_level_N':sum(r['floor_reset_N'] for r in refs),'local_L_evaluated_before_first_intent_N':sum(len(r['floor_L']) for r in refs),'EXIT_D_N':len(d),'V3_EXIT_A_preempted_N':sum(old_reason(p)=='UP_STRUCTURE_REVERSED' for p in d),'target_V3_EXIT_A_preempted_N':sum(old_reason(p)=='UP_STRUCTURE_REVERSED' and p['exclusive_bucket'] in targets for p in d),'GE5_EXIT_D_N':sum(p['exclusive_bucket']=='>=5%' for p in d)}
    for k,v in aggregate.items():check('mechanics_'+k,mech[k]==v)
    statcheck('mechanics_distance',mech['distance_to_main_u_at_activation'],[u['floor_to_main_distance_before_u'] for u in updates])
    statcheck('mechanics_creation_age',mech['floor_age_since_creation_bars_at_break'],[r['last']['state']['as_of']-r['floor_before_final']['created_at'] for r in dref])
    statcheck('mechanics_update_age',mech['floor_age_since_update_bars_at_break'],[r['last']['state']['as_of']-r['floor_before_final']['updated_at'] for r in dref])
    check('mechanics_break_Primary',mech['break_Primary_context_N']==dict(collections.Counter(str(r['last']['path']['Primary_or_null'])+'/'+str(r['last']['state']['context']) for r in dref)))
    check('mechanics_break_sequence',mech['break_preceding3_distinct_Primary_N']==dict(collections.Counter('>'.join(r['suffix_sequence']) for r in dref)))
    check('mechanics_V3_reason_N',mech['EXIT_D_v3_intent_reason_N']==dict(collections.Counter(old_reason(p) for p in d)))
    primary=load(HERE/'PRIMARY_2_TO_5.json');provisional=load(HERE/'SELECTION_PREAUDIT.json');by={g['group']:g for g in primary}
    dc=by['2–<5%_COMBINED']['return_common_group_difference'];dg=by['>=5%_PROTECTION']['return_common_group_difference'];ex={b:by[b]['return_common_group_difference']['mean'] for b in targets}
    expected_conditions={'combined_mean_strictly_greater':dc['mean']>0,'combined_median_strictly_greater':dc['median']>0,'three_exclusive_means_nonworse':all(v>=0 for v in ex.values()),'at_least_two_exclusive_means_strictly_greater':sum(v>0 for v in ex.values())>=2,'GE5_mean_nonworse':dg['mean']>=0,'GE5_median_nonworse':dg['median']>=0,'audit_zero':False}
    check('fixed_gate_each_numerical_condition',provisional['fixed_conditions']==expected_conditions)
    expected_status='V4_NOT_BETTER_KEEP_V3' if dc['mean']<=0 or dc['median']<=0 else 'V4_MIXED_KEEP_HUMAN_JUDGMENT' if any(v<0 for v in ex.values()) or dg['mean']<0 or dg['median']<0 else 'V4_NOT_BETTER_KEEP_V3' if sum(v>0 for v in ex.values())<2 else 'AUDIT_PENDING_STRICT_NUMERICAL_CONDITIONS_MET'
    check('fixed_gate_status_no_post_result_changes',provisional['status']==expected_status)
    target=subset('PRIMARY_2_TO_5','2–<5%_COMBINED');target_common=[p for p in target if p['v3']['sell_status']=='FILLED' and p['v4']['sell_status']=='FILLED']
    check('exclusive_2_to_5_426_417',len(target)==426 and len(target_common)==417 and by['2–<5%_COMBINED']['return_common_filled_N']==417)
    check('GE5_253_denominator',by['>=5%_PROTECTION']['denominator_N']==253)
    con=load(HERE/'TARGET_CONCENTRATION_DIAGNOSTIC.json');deltas=[paired[p['watch_key']]['v4']['realized_return_pct']-paired[p['watch_key']]['v3']['realized_return_pct'] for p in target_common];net=sum(deltas);largest=max(0,max(deltas))
    for k,v in {'target_common_filled_N':417,'target_D_N':sum(is_d(p) for p in target_common),'positive_delta_N':sum(x>0 for x in deltas),'negative_delta_N':sum(x<0 for x in deltas),'zero_delta_N':sum(x==0 for x in deltas),'net_delta_sum_pp':net,'largest_positive_delta_pp':largest,'mean_delta_pp':net/417,'mean_delta_without_largest_positive_case_pp':(net-largest)/416}.items():check('concentration_'+k,equivalent(con[k],v))
    for name in list(freeze['decision_code_hashes'])+list(freeze['evaluation_and_selection_code_hashes']):
        tree=ast.parse((HERE/name).read_text());imports=[x.module for x in ast.walk(tree) if isinstance(x,ast.ImportFrom)]
        check('no_engine_model_provider_import',not any(x and any(bad in x for bad in ['candidate','independent.api','normalize','PATH_FROZEN','sklearn','torch','requests']) for x in imports))
        check('no_model_fit_predict_provider_calls',not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr in ['fit','predict','predict_proba','step','request','urlopen'] for x in ast.walk(tree)))
    decision_text='\n'.join((HERE/n).read_text() for n in ['frozen_v2_lifecycle.py','local_guard.py','recovery_floor.py'])
    check('future_bucket_return_gain_dwell_not_decision_inputs',not any(k in decision_text for k in ['exclusive_bucket','observed_entry_to_high','realized_return_pct','probability','raw_score','rank','profit_threshold']))
    imports=[x.module for x in ast.walk(ast.parse(Path(__file__).read_text())) if isinstance(x,ast.ImportFrom)]
    check('audit_no_primary_logic_import',not set(imports)&{'local_guard','recovery_floor','frozen_v2_lifecycle','reused_clock','reused_fill','replay_v4','evaluate_v4','selection_gate'})
    for k,v in BUDGET.items():check('budget_exact',v==1 if k in ['new_EXIT_policies','recovery_floor_variants'] else v==0)
    check('all_safety_false',all(v is False for v in SAFETY.values()))
    status='BLOCKED_V4_FROZEN_TRACE_NOT_AVAILABLE' if trace_missing else 'BLOCKED_V4_RECOVERY_FLOOR_CAUSALITY' if leak else 'BLOCKED_V4_LINEAGE_MISMATCH' if lineage else 'BLOCKED_V4_AUDIT_MISMATCH' if mismatch else 'INDEPENDENT_V4_AUDIT_PASS'
    report={'saved_at_jst':now(),'status':status,'Entry_N':1600,'mismatch_N':mismatch,'future_causal_leakage_N':leak,'lineage_mismatch_N':lineage,'trace_mismatch_N':trace_missing,'check_N':sum(counts.values()),'check_counts':dict(counts),'mismatch_examples':fails,'EXIT_D_exact_conditions_verified_N':d_valid,'non_D_exact_saved_V3_outcomes_unchanged_N':non_d_unchanged,'independent_primary_logic_import_N':0,'one_primary_V4_replay':1,'V3_replay':0,'State9_Path_reconstruction':0,'model_teacher_search':0,'audit_fit':0,'PULLBACK_alone_SELL_N':0 if not mismatch else None,'local_DOWN_alone_SELL_N':0 if not mismatch else None,'RISE_STOP_alone_SELL_N':0 if not mismatch else None,'dwell_time_stop_count_alone_SELL_N':0 if not mismatch else None,'fixed_loss_profit_stop_trailing_SELL_N':0 if not mismatch else None,'V3_A_B_C_PRE_quality_fill_calendar_whole_bytes_unchanged':True,'Reentry_Capital':0,'availability_assumption':'historical actual_known_at UNKNOWN; inherited assumed bar_end availability only','metric_float_verification_tolerance':'1e-10 absolute /1e-12 relative for economics representation only; all decision arithmetic exact Fraction without tolerance','shared_dependencies':['immutable V3 outcomes and original State9/Path/raw trace','Python Fraction/standard runtime','settings I/O/hash only; independent phase/floor/pivot/fill/calendar/economics'],'budget':BUDGET,'safety':SAFETY}
    save(HERE/'INDEPENDENT_AUDIT.json',report);print(json.dumps(report))
    if mismatch:raise SystemExit(2)

if __name__=='__main__':run()
