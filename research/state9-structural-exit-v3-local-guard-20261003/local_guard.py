"""One position-local guard. Uses only already saved State9 pivot confirmations."""
from dataclasses import dataclass, field
from fractions import Fraction
from frozen_v2_lifecycle import Lifecycle, valid, connected

DELTA = Fraction(1,2)
EXIT_C = 'LOCAL_UP_STRUCTURE_GUARD_BROKEN'

@dataclass
class LocalGuard:
    previous_trace: dict | None = None
    pivots: list = field(default_factory=list)
    level: dict | None = None
    events: list = field(default_factory=list)
    observed_pivots: list = field(default_factory=list)
    prefix_pivot_N: int = 0
    eligible_sequences: dict = field(default_factory=dict)
    higher_low_sequences: dict = field(default_factory=dict)
    candidate_bar_N: int = 0
    established_ever: bool = False
    reset_with_guard_N: int = 0

    def begin(self,row,position_decision):
        linked=connected(self.previous_trace,row)
        if not linked:
            if self.level is not None:
                self.reset_with_guard_N+=1
                if position_decision:self.events.append({'type':'LOCAL_GUARD_RESET','minute':row['bar_end_minute'],'previous_guard':self.level,'current_segment':row['path']['causal_segment_id']})
            self.level=None;self.pivots=[]
        s=row['state'];p=row['path'];t=s['as_of']
        before=self.level if self.level and self.level['effective_from']<=t and self.level['segment']==p['causal_segment_id'] and valid(row) else None
        return linked,before

    def append_current_pivot(self,row,position_decision):
        pivot=row['state']['local_pivot_confirmed']
        if valid(row) and pivot is not None:
            assert pivot['kind'] in ('L','H') and pivot['extremum_t']<=pivot['confirmed_at']<=row['state']['as_of'],'BLOCKED_V3_LOCAL_GUARD_CAUSALITY'
            duplicate=any(p==pivot for p in self.pivots)
            if not duplicate:
                assert not self.pivots or self.pivots[-1]['confirmed_at']<pivot['confirmed_at'],'BLOCKED_V3_LOCAL_GUARD_CAUSALITY'
                self.pivots=(self.pivots+[dict(pivot)])[-3:]
                if position_decision:self.observed_pivots.append({'segment':row['path']['causal_segment_id'],'pivot':dict(pivot)})
                else:self.prefix_pivot_N+=1
        self.previous_trace=row

    def update(self,row,active):
        s=row['state'];p=row['path'];t=s['as_of']
        if not active or not valid(row) or s['context']!=1 or len(self.pivots)!=3:return None
        a,h,b=self.pivots
        if [x['kind'] for x in self.pivots]!=['L','H','L'] or not all(x['confirmed_at']<t for x in self.pivots):return None
        key=(p['causal_segment_id'],a['confirmed_at'],h['confirmed_at'],b['confirmed_at'])
        self.eligible_sequences.setdefault(key,[dict(x) for x in self.pivots])
        if Fraction(b['x'])-Fraction(a['x'])<DELTA:return None
        self.higher_low_sequences.setdefault(key,[dict(x) for x in self.pivots])
        if self.level and Fraction(b['x'])<=Fraction(self.level['x']):return None
        if Fraction(s['close_u'])<Fraction(h['x'])+DELTA:return None
        self.candidate_bar_N+=1
        prior=self.level;initial=prior is None
        new={'x':b['x'],'segment':p['causal_segment_id'],'effective_from':t+1,'updated_at':t,'created_at':t if initial else prior['created_at'],'activation_minute':row['bar_end_minute'],'pivot_sequence':[dict(x) for x in self.pivots]}
        distance=Fraction(b['x'])-Fraction(s['protected_after_effective_next']) if s['protected_after_effective_next'] is not None else None
        event={'type':'LOCAL_GUARD_CREATED' if initial else 'LOCAL_GUARD_TIGHTENED','minute':row['bar_end_minute'],'scheduled_t':t,'before':prior,'after':new,'close_u':s['close_u'],'context':s['context'],'main_protected_before':s['protected_before'],'main_protected_after_effective_next':s['protected_after_effective_next'],'guard_to_main_distance_u_fraction':str(distance) if distance is not None else None,'guard_to_main_distance_u':float(distance) if distance is not None else None,'structure_pivots_exact':s['_structure_pivots'],'context_extreme_exact':s['_context_extreme']}
        self.level=new;self.established_ever=True;self.events.append(event)
        return event

@dataclass
class GuardedLifecycle:
    entry_minute: int
    deadline: int
    base: Lifecycle = field(init=False)
    guard: LocalGuard = field(default_factory=LocalGuard)

    def __post_init__(self):self.base=Lifecycle(self.entry_minute)

    def prefix(self,row):
        assert row['bar_end_minute']<self.entry_minute
        self.guard.begin(row,False);self.guard.append_current_pivot(row,False)

    def observe(self,row):
        if self.base.intent is not None:raise RuntimeError('POST_EXIT_DECISION_PROHIBITED')
        linked,before=self.guard.begin(row,True)
        suffix=[dict(x) for x in self.guard.pivots]
        self.base.observe(row)  # exact reused v2 PRE/quality/main A/B; no separate v2 Replay
        s=row['state'];p=row['path'];update=None
        active=self.base.phase=='UP_STRUCTURE_ACTIVE' and not self.base.suspended
        # The contingent closing intention is preplanned. C must precede that clock.
        if self.base.intent is None and active and linked and valid(row) and s['context']==1 and before is not None and s['protected_before'] is not None and row['bar_end_minute']<self.deadline and Fraction(before['x'])>Fraction(s['protected_before']) and Fraction(s['close_u'])<=Fraction(before['x'])-DELTA:
            self.base.intent={'reason':EXIT_C,'minute':row['bar_end_minute'],'scheduled_t':s['as_of'],'timestamp':row['slot']['bar_end'],'segment':p['causal_segment_id'],'primary':p['Primary_or_null'],'context':s['context'],'previous_context':self.base.previous['state']['context'],'protected_before':s['protected_before'],'protected_after_effective_next':s['protected_after_effective_next'],'protected_effective_from':s['protected_effective_from'],'close_u':s['close_u'],'balance':s['balance'],'dwell':p['dwell_observed_bars'],'run_id':p['run_id'],'path_sequence':list(self.base.primary_sequence),'local_guard_before':dict(before),'guard_age_since_creation_bars':s['as_of']-before['created_at'],'guard_age_since_last_update_bars':s['as_of']-before['updated_at'],'guard_to_main_distance_at_break_u':float(Fraction(before['x'])-Fraction(s['protected_before'])),'structure_pivots_exact':s['_structure_pivots'],'context_extreme_exact':s['_context_extreme'],'buffer_u':'0.5','path_event_types':[x['event_type'] for x in row['path_events']],'state_events':list(s['events'])}
            self.guard.events.append({'type':'LOCAL_GUARD_BROKEN','minute':row['bar_end_minute'],'guard_before':dict(before),'close_u':s['close_u'],'main_protected_before':s['protected_before'],'context':s['context'],'primary':p['Primary_or_null']})
        if self.base.intent is None:update=self.guard.update(row,active)
        self.guard.append_current_pivot(row,True)  # current confirmation cannot update/break this bar
        record={'minute':row['bar_end_minute'],'scheduled_t':s['as_of'],'phase':self.base.phase,'suspended':self.base.suspended,'observed':valid(row),'same_segment_observed_connection':linked,'segment':p['causal_segment_id'],'primary':p['Primary_or_null'],'context':s['context'],'protected_before':s['protected_before'],'close_u':s['close_u'],'local_pivot_confirmed_exact':s['local_pivot_confirmed'],'prior_local_pivot_suffix_exact':suffix,'local_guard_before':before,'local_guard_after_effective_next':self.guard.level,'guard_update':update,'exit_intent_reason':self.base.intent['reason'] if self.base.intent else None}
        return self.base.intent,record
