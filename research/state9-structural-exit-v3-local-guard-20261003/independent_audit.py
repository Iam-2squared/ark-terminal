"""Separate latch/pivot-ledger/fill/economics audit. No primary decision imports."""
import ast,collections,gzip,hashlib,json,math,statistics
from fractions import Fraction
from pathlib import Path
from settings import HERE,INPUT,V2,PUBLIC_V2,PRIVATE,SAFETY,BUDGET,now,sha,load,rows,save

HALF=Fraction(1,2)
C_REASON='LOCAL_UP_STRUCTURE_GUARD_BROKEN'

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

def reference_scan(stream,entry,actual_meta,check):
    """Boolean phase latch; full segment ledger, independently formed next-bar guard."""
    active=False;lost=False;first_arm=None;arms=[];losses=[];old_position=None;old_input=None
    ledger=[];guard=None;sequence=[];trigger=None;decisions=0;prefix_pivots=0;position_pivots=[]
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
        current_pivot=s['local_pivot_confirmed']
        if usable and current_pivot is not None:
            check('source_local_pivot_causality',current_pivot['extremum_t']<=current_pivot['confirmed_at']<=t,causal=True)
        if minute<entry['fill_minute']:
            if usable and current_pivot is not None and current_pivot not in ledger:
                check('prefix_pivot_confirmed_order',not ledger or ledger[-1]['confirmed_at']<current_pivot['confirmed_at'],causal=True)
                ledger.append(dict(current_pivot));prefix_pivots+=1
            old_input=r;continue
        before=guard if guard is not None and guard['effective_from']<=t and guard['segment']==p['causal_segment_id'] and usable else None
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
        expected={'minute':minute,'scheduled_t':t,'phase':'UP_STRUCTURE_ACTIVE' if active else 'PRE_UP_STRUCTURE','suspended':lost,'observed':usable,'same_segment_observed_connection':input_link,'segment':p['causal_segment_id'],'primary':p['Primary_or_null'],'context':s['context'],'protected_before':s['protected_before'],'close_u':s['close_u'],'local_pivot_confirmed_exact':current_pivot,'prior_local_pivot_suffix_exact':prior_suffix,'local_guard_before':before,'local_guard_after_effective_next':guard,'guard_update':update,'exit_intent_reason':trigger[0] if trigger else None}
        check('decision_metadata_exact',decisions<len(actual_meta) and expected==actual_meta[decisions])
        check('local_pivot_exact_original_field',decisions<len(actual_meta) and actual_meta[decisions]['local_pivot_confirmed_exact']==current_pivot)
        if not input_link:check('no_cross_segment_carry',before is None and prior_suffix==[])
        if usable and current_pivot is not None and current_pivot not in ledger:
            check('position_pivot_confirmed_order',not ledger or ledger[-1]['confirmed_at']<current_pivot['confirmed_at'],causal=True)
            ledger.append(dict(current_pivot));position_pivots.append({'segment':p['causal_segment_id'],'pivot':dict(current_pivot)})
        old_position=r;old_input=r;decisions+=1
        if trigger is not None:break
    return {'trigger':trigger,'first_arm':first_arm,'arms':arms,'losses':losses,'decisions':decisions,'active':active,'lost':lost,'suffix_sequence':sequence,'guard':guard,'updates':updates,'creation_N':creations,'tighten_N':tightens,'reset_N':resets,'eligible_N':len(eligible),'higher_N':len(higher),'observed_pivots':position_pivots,'prefix_pivot_N':prefix_pivots,'pullback_N':len(pull),'rise_stop_N':len(stop),'main_tighten_N':main_tightens,'last':old_position,'guard_before_final':before}

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
        'intent_advance_vs_v2_active_minutes':audit_clock(day,fm,old_intent)-audit_clock(day,fm,intent),
        'sell_advance_vs_v2_active_minutes':baseline['holding_active_minutes']-audit_clock(day,fm,sm) if filled and baseline['sell_status']=='FILLED' else None,
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

def run():
    counts=collections.Counter();fails=[];mismatch=leak=lineage=trace_missing=0;current=None
    def check(name,condition,causal=False,lineage_check=False,trace_check=False):
        nonlocal mismatch,leak,lineage,trace_missing
        counts[name]+=1
        if not condition:
            mismatch+=1;leak+=causal;lineage+=lineage_check;trace_missing+=trace_check
            if len(fails)<30:fails.append({'watch_key':current,'check':name})
    manifest=load(V2/'MANIFEST.json')['components'];public_manifest=load(PUBLIC_V2/'FINAL_PROVENANCE_MANIFEST.json')['files']
    entry_file=V2/'FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'
    check('Frozen_Entry_exact_bytes',sha(entry_file)==manifest['FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz']['sha256']=='e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb',lineage_check=True)
    original_entry=list(rows(entry_file));ee=[r for r in original_entry if r['entry_status']=='FIRST_ENTRY']
    check('Frozen_Entry_N',len(ee)==1600 and len(original_entry)==2155,lineage_check=True)
    for name in ['REPLAY_ROWS.jsonl.gz','ECONOMICS_ROWS.jsonl.gz','TRACE_RECEIPTS.json','SAVED_INPUTS/raw_paths_selected.json.gz']:
        check('v2_saved_component_hash',sha(V2/name)==manifest[name]['sha256'],lineage_check=True)
    identity=load(PUBLIC_V2/'IDENTITY_RECEIPT.json')
    for name,pin in identity['frozen_identity'].items():
        check('six_Frozen_semantic_hashes',sha(PUBLIC_V2/'FROZEN_SOURCE'/name)==pin['expected']==pin['actual'],lineage_check=True)
    for name in ['lifecycle.py','replay.py','settings.py','INDEPENDENT_AUDIT.json','WINNER_EXCLUSIVE.json','ALL_ENTRY_ECONOMICS.json']:
        check('v2_audited_public_hash',sha(PUBLIC_V2/name)==public_manifest[name]['sha256'],lineage_check=True)
    freeze=load(HERE/'CONTRACT_FREEZE_RECEIPT.json');check('S0_contract_unchanged',sha(HERE/'CONTRACT.md')==freeze['contract_sha256'],lineage_check=True)
    for name,d in freeze['decision_code_hashes'].items():check('S0_decision_code_unchanged',sha(HERE/name)==d,lineage_check=True)
    check('exact_v2_base_code_reuse',sha(HERE/'frozen_v2_lifecycle.py')==sha(PUBLIC_V2/'lifecycle.py'),lineage_check=True)
    code_receipt=load(HERE/'V2_CODE_REUSE_RECEIPT.json')
    for source_name,func_names,target in [('settings.py',list(code_receipt['clock_function_slice_sha256']),'reused_clock.py'),('replay.py',['fill_from_source'],'reused_fill.py')]:
        source=(PUBLIC_V2/source_name).read_text();target_text=(HERE/target).read_text()
        source_functions={n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
        target_functions={n.name:ast.get_source_segment(target_text,n) for n in ast.parse(target_text).body if isinstance(n,ast.FunctionDef)}
        for n in func_names:check('exact_execution_clock_function_slice',source_functions[n]==target_functions[n],lineage_check=True)
    raw=load(V2/'SAVED_INPUTS/raw_paths_selected.json.gz')
    baseline={r['watch_key']:r for r in rows(V2/'ECONOMICS_ROWS.jsonl.gz')};old_replay={r['watch_key']:r for r in rows(V2/'REPLAY_ROWS.jsonl.gz')}
    new={r['watch_key']:r for r in rows(PRIVATE/'ECONOMICS_ROWS.jsonl.gz')};replay={r['watch_key']:r for r in rows(PRIVATE/'REPLAY_ROWS.jsonl.gz')};paired={r['watch_key']:r for r in rows(PRIVATE/'PAIRED_ROWS.jsonl.gz')}
    decision_receipts={r['watch_key']:r for r in load(PRIVATE/'DECISION_TRACE_RECEIPTS.json')}
    check('all1600_identity_sets',set(baseline)==set(old_replay)==set(new)==set(replay)==set(paired)==set(decision_receipts)=={r['watch_key'] for r in ee},lineage_check=True)
    independent_pairs=[];refs=[]
    for entry in ee:
        current=entry['watch_key'];a=baseline[current];r=replay[current];n=new[current]
        check('Entry_immutable_fill',r['entry_minute']==entry['fill_minute'] and r['entry_timestamp']==entry['fill_timestamp'] and r['entry_fill_price']==entry['fill_price'],lineage_check=True)
        path=V2/'FULL_TRACE'/(current.replace('|','_')+'.jsonl.gz');check('full_trace_exact_reuse',sha(path)==manifest['FULL_TRACE/'+path.name]['sha256'],trace_check=True)
        mp=PRIVATE/'DECISION_TRACE'/path.name;check('v3_metadata_hash',sha(mp)==decision_receipts[current]['sha256'])
        meta=list(rows(mp));ref=reference_scan(rows(path),entry,meta,check);refs.append(ref)
        actual_trigger=(r['exit_intent']['reason'],r['exit_intent']['minute']) if r['exit_intent'] else None
        check('first_valid_A_B_C_precedence',actual_trigger==ref['trigger'])
        check('UP_arm_and_PRE_unchanged',ref['first_arm']==r['first_arm_minute']==a['first_arm_minute'])
        check('observation_suspension_unchanged',[x['minute'] for x in r['observations_suspended']]==ref['losses'])
        check('arm_events',[(x['minute'],x['segment']) for x in r['arm_events']]==ref['arms'])
        check('post_exit_decision_zero',r['post_exit_decision_N']==0 and ref['decisions']==r['decision_N']==len(meta))
        check('phase_and_quality',r['phase_at_last_decision']==('UP_STRUCTURE_ACTIVE' if ref['active'] else 'PRE_UP_STRUCTURE') and r['suspended_at_last_decision']==ref['lost'])
        check('pivot_exact_bytes_reused',r['local_pivot_observed_exact']==ref['observed_pivots'])
        check('all_guard_mechanics',r['local_guard_creation_N']==ref['creation_N'] and r['local_guard_tighten_N']==ref['tighten_N'] and r['local_guard_reset_with_level_N']==ref['reset_N'] and r['LHL_eligible_sequence_N']==ref['eligible_N'] and r['LHL_higher_low_sequence_N']==ref['higher_N'] and r['local_pivot_observed_N']==len(ref['observed_pivots']) and r['prefix_local_pivot_N']==ref['prefix_pivot_N'])
        check('guard_update_events_exact',[e for e in r['local_guard_events'] if e['type'] in ['LOCAL_GUARD_CREATED','LOCAL_GUARD_TIGHTENED']]==ref['updates'])
        check('guard_position_coverage',r['local_guard_established_ever']==bool(ref['creation_N']))
        check('distinct_Primary_runs',r['exit_last3_distinct_primary']==ref['suffix_sequence'] and r['PULLBACK_run_N']==ref['pullback_N'] and r['RISE_STOP_run_N']==ref['rise_stop_N'] and r['protected_tighten_N']==ref['main_tighten_N'])
        if ref['trigger'] and ref['trigger'][0]==C_REASON:
            ci=r['exit_intent'];before=ref['guard_before_final'];last=ref['last']['state']
            check('C_guard_exact',ci['local_guard_before']==before and ci['buffer_u']=='0.5' and ci['context']==1)
            check('C_age_and_main_metadata',ci['guard_age_since_creation_bars']==last['as_of']-before['created_at'] and ci['guard_age_since_last_update_bars']==last['as_of']-before['updated_at'] and ci['structure_pivots_exact']==last['_structure_pivots'] and ci['context_extreme_exact']==last['_context_extreme'])
            old_intent=a['exit_intent']['minute'] if a['exit_intent'] else a['planned_close_intent_minute']
            check('C_genuinely_before_saved_v2_intent',ref['trigger'][1]<old_intent and audit_clock(entry['session'],ref['trigger'][1],old_intent)>0)
        else:
            check('non_C_base_reason_and_fill_identical',r['exit_intent']==old_replay[current]['exit_intent'] and r['sell_status']==old_replay[current]['sell_status'] and r['sell_price']==old_replay[current]['sell_price'] and r['sell_minute']==old_replay[current]['sell_minute'])
        fill=independent_fill(entry,ref['trigger'],raw[current]['today'])
        check('canonical_next_open_5bps_session_close',r['sell_status']==fill[0] and r['sell_minute']==fill[1] and equivalent(r['sell_price'],float(fill[2]) if fill[2] is not None else None) and r['sell_source']==fill[3] and r['exit_reason']==fill[4] and r['sell_adjustment_bps']==5 and r['commission']==0)
        metric=independent_metrics(entry,ref,fill,a,raw[current]['today'])
        for k,v in metric.items():check('independent_'+k,equivalent(n[k],v))
        opportunity=['observed_entry_to_high_pct','observed_high','final_observed_high_minute','latest_tied_observed_high_minute','remaining_source_complete','entry_to_high_active_minutes','observed_High_unknown']
        check('Frozen_opportunity_no_recalculation_or_change',all(n[k]==a[k] for k in opportunity))
        check('saved_v2_join_exact_identity',paired[current]['v2']==a and paired[current]['v3']==n and paired[current]['exclusive_bucket']==label_of(a['observed_entry_to_high_pct']),lineage_check=True)
        expected=dict(n);expected.update(metric);independent_pairs.append({'watch_key':current,'exclusive_bucket':label_of(a['observed_entry_to_high_pct']),'v2':a,'v3':expected})
    current=None
    def subset(name,label):
        if name=='ALL_ENTRY_ECONOMICS':return independent_pairs
        if name=='EXCLUSIVE_ENTRY_HIGH_PRIMARY':return [p for p in independent_pairs if p['exclusive_bucket']==label]
        if name=='WINNER_GE5_PROTECTION':return [p for p in independent_pairs if p['exclusive_bucket']=='>=5%']
        c=[p for p in independent_pairs if p['v3']['exit_intent'] is not None and p['v3']['exit_intent']['reason']==C_REASON]
        if name=='EXIT_C_PAIRED_DIAGNOSIS':return c
        if name=='EXIT_C_EXCLUSIVE':return [p for p in c if p['exclusive_bucket']==label]
        if name=='WINNER_GE5_EXIT_C':return [p for p in c if p['exclusive_bucket']=='>=5%']
        if name=='EXIT_C_V2_REASON':return [p for p in c if p['v2']['exit_intent'] is not None and p['v2']['exit_intent']['reason']==label] if label!='SESSION_CLOSE' else [p for p in c if p['v2']['exit_intent'] is None]
        if name=='V3_EXIT_REASON':return [p for p in independent_pairs if p['v3']['exit_reason']==label]
        raise ValueError(name)
    for name in ['EXCLUSIVE_ENTRY_HIGH_PRIMARY','WINNER_GE5_PROTECTION','ALL_ENTRY_ECONOMICS','EXIT_C_PAIRED_DIAGNOSIS','EXIT_C_EXCLUSIVE','WINNER_GE5_EXIT_C','EXIT_C_V2_REASON','V3_EXIT_REASON']:
        for g in load(HERE/(name+'.json')):
            ps=subset(name,g['group']);check('exclusive_and_subgroup_denominators',len(ps)==g['denominator_N'])
            check('group_EXIT_C_N',g['EXIT_C_N']==sum(p['v3']['exit_intent'] is not None and p['v3']['exit_intent']['reason']==C_REASON for p in ps))
            for version in ['v2','v3']:
                items=[p[version] for p in ps];filled=[r['realized_return_pct'] for r in items if r['sell_status']=='FILLED'];negative=[v for v in filled if v<0];before=[r['exit_before_final_observed_high'] for r in items if r['exit_before_final_observed_high'] is not None]
                expectations={'sell_filled_N':len(filled),'unresolved_N':len(items)-len(filled),'positive_N':sum(v>0 for v in filled),'negative_N':len(negative),'positive_rate_pct':100*sum(v>0 for v in filled)/len(filled) if filled else None,'worst_return_pct':min(filled) if filled else None,'below_minus1_N':sum(v<-1 for v in filled),'below_minus2_N':sum(v<-2 for v in filled),'EXIT_before_final_High_N':sum(before),'EXIT_before_final_High_denominator_N':len(before),'EXIT_before_final_High_rate_pct':100*sum(before)/len(before) if before else None}
                for k,v in expectations.items():check('group_'+k,equivalent(g[version][k],v))
                check('negative_return_N',g[version]['negative_return']['N']==len(negative))
                check('negative_return_mean',equivalent(g[version]['negative_return']['mean'],sum(negative)/len(negative) if negative else None))
                check('negative_return_median',equivalent(g[version]['negative_return']['median'],statistics.median(negative) if negative else None))
                for metric,st in g[version]['metrics'].items():
                    vv=[r[metric] for r in items if r[metric] is not None]
                    check('group_metric_N',st['N']==len(vv))
                    check('group_metric_mean',equivalent(st['mean'],statistics.fmean(vv) if vv else None))
                    check('group_metric_median',equivalent(st['median'],statistics.median(vv) if vv else None))
            for metric,st in g['paired_delta'].items():
                dd=[p['v3'][metric]-p['v2'][metric] for p in ps if p['v3'][metric] is not None and p['v2'][metric] is not None]
                check('paired_delta_N',st['N']==len(dd));check('paired_delta_mean',equivalent(st['mean'],statistics.fmean(dd) if dd else None));check('paired_delta_median',equivalent(st['median'],statistics.median(dd) if dd else None))
                for k in ['mean','median']:
                    aa=g['v2']['metrics'][metric][k];bb=g['v3']['metrics'][metric][k]
                    check('group_difference_'+k,equivalent(g['group_difference'][metric][k],bb-aa if aa is not None and bb is not None else None))
            for timing in ['intent_advance_vs_v2_active_minutes','sell_advance_vs_v2_active_minutes']:
                values=[p['v3'][timing] for p in ps if p['v3'][timing] is not None]
                check('timing_N',g[timing]['N']==len(values));check('timing_mean',equivalent(g[timing]['mean'],statistics.fmean(values) if values else None));check('timing_median',equivalent(g[timing]['median'],statistics.median(values) if values else None))
    mechanics=load(HERE/'LOCAL_GUARD_MECHANICS.json')
    mech={'local_pivot_observed_after_Entry_N':sum(len(r['observed_pivots']) for r in refs),'prefix_local_pivot_observed_N':sum(r['prefix_pivot_N'] for r in refs),'LHL_eligible_unique_sequence_N':sum(r['eligible_N'] for r in refs),'LHL_higher_low_unique_sequence_N':sum(r['higher_N'] for r in refs),'local_guard_creation_N':sum(r['creation_N'] for r in refs),'local_guard_tighten_N':sum(r['tighten_N'] for r in refs),'guard_candidate_bar_N':sum(len(r['updates']) for r in refs),'unique_positions_with_guard_N':sum(bool(r['creation_N']) for r in refs),'guard_never_established_N':sum(not r['creation_N'] for r in refs),'guard_reset_with_level_N':sum(r['reset_N'] for r in refs),'guard_break_N':sum(r['trigger'] is not None and r['trigger'][0]==C_REASON for r in refs)}
    for k,v in mech.items():check('mechanics_aggregate_'+k,mechanics[k]==v)
    all_updates=[u for r in refs for u in r['updates']]
    c_refs=[r for r in refs if r['trigger'] is not None and r['trigger'][0]==C_REASON]
    mechanics_stats={
        'guard_to_main_distance_u_at_activation':[u['guard_to_main_distance_u'] for u in all_updates if u['guard_to_main_distance_u'] is not None],
        'guard_age_since_creation_bars_at_break':[r['last']['state']['as_of']-r['guard_before_final']['created_at'] for r in c_refs],
        'guard_age_since_last_update_bars_at_break':[r['last']['state']['as_of']-r['guard_before_final']['updated_at'] for r in c_refs],
    }
    for name,values in mechanics_stats.items():
        check('mechanics_stats_N',mechanics[name]['N']==len(values))
        check('mechanics_stats_mean',equivalent(mechanics[name]['mean'],sum(values)/len(values) if values else None))
        check('mechanics_stats_median',equivalent(mechanics[name]['median'],statistics.median(values) if values else None))
    check('mechanics_break_Primary_context',mechanics['break_Primary_context_N']==dict(collections.Counter(str(r['last']['path']['Primary_or_null'])+'/'+str(r['last']['state']['context']) for r in c_refs)))
    check('mechanics_break_distinct_Primary',mechanics['break_preceding3_distinct_Primary_N']==dict(collections.Counter('>'.join(r['suffix_sequence']) for r in c_refs)))
    for name in ['local_guard.py','frozen_v2_lifecycle.py','replay_v3.py','reused_fill.py','reused_clock.py','settings.py','evaluate_v3.py']:
        tree=ast.parse((HERE/name).read_text());imports=[x.module for x in ast.walk(tree) if isinstance(x,ast.ImportFrom)]
        check('no_engine_model_provider_import',not any(x and any(forbidden in x for forbidden in ['candidate','independent.api','normalize','PATH_FROZEN','sklearn','torch','requests']) for x in imports))
        check('no_model_fit_predict_call',not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr in ['fit','predict','predict_proba','step','request','urlopen'] for x in ast.walk(tree)))
    ownimports=[x.module for x in ast.walk(ast.parse(Path(__file__).read_text())) if isinstance(x,ast.ImportFrom)]
    check('independent_audit_no_primary_logic_import',not set(ownimports)&{'local_guard','frozen_v2_lifecycle','reused_fill','reused_clock','evaluate_v3','replay_v3'})
    for key,v in BUDGET.items():check('budget_exact',v==1 if key in ['new_EXIT_policies','local_guard_variants'] else v==0)
    check('all_safety_false',all(v is False for v in SAFETY.values()))
    status='BLOCKED_V3_FROZEN_TRACE_NOT_AVAILABLE' if trace_missing else 'BLOCKED_V3_LOCAL_GUARD_CAUSALITY' if leak else 'BLOCKED_V3_LINEAGE_MISMATCH' if lineage else 'BLOCKED_V3_AUDIT_MISMATCH' if mismatch else 'INDEPENDENT_V3_AUDIT_PASS'
    report={'saved_at_jst':now(),'status':status,'Entry_N':1600,'mismatch_N':mismatch,'future_causal_leakage_N':leak,'lineage_mismatch_N':lineage,'check_N':sum(counts.values()),'check_counts':dict(counts),'mismatch_examples':fails,'independent_primary_logic_import_N':0,'State9_Path_reconstruction':0,'v2_replay':0,'model_teacher_search':0,'audit_fit':0,'PULLBACK_alone_SELL_N':0 if not mismatch else None,'RISE_STOP_alone_SELL_N':0 if not mismatch else None,'STOP_count_dwell_alone_SELL_N':0 if not mismatch else None,'fixed_loss_profit_stop_trailing_SELL_N':0 if not mismatch else None,'main_A_B_PRE_quality_code_byte_unchanged':True,'Reentry_Capital':0,'availability_assumption':'historical actual_known_at UNKNOWN; inherited bar_end availability assumption only','shared_dependencies':['immutable v2 saved trace/raw/opportunity/outcomes','Python Fraction/standard runtime','settings I/O/hash only; independent phase/pivots/fill/calendar/economics'],'budget':BUDGET,'safety':SAFETY}
    save(HERE/'INDEPENDENT_AUDIT.json',report);print(json.dumps(report))
    if mismatch:raise SystemExit(2)

if __name__=='__main__':run()
