"""Frozen V3 independent latch/pivot reference; no primary logic imports."""
import math
from fractions import Fraction
HALF=Fraction(1,2)
C_REASON="LOCAL_UP_STRUCTURE_GUARD_BROKEN"

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

