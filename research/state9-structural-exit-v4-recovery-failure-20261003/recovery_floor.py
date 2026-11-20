"""One new recovery floor, composed over byte-exact V3 A/B/C lifecycle."""
from dataclasses import dataclass,field
from fractions import Fraction
from local_guard import GuardedLifecycle
from frozen_v2_lifecycle import valid,connected

DELTA=Fraction(1,2)
EXIT_D='LOCAL_RECOVERY_FAILED'

@dataclass
class RecoveryFloor:
    previous_trace:dict|None=None
    level:dict|None=None
    events:list=field(default_factory=list)
    observed_L:list=field(default_factory=list)
    established_ever:bool=False
    reset_with_level_N:int=0

    def begin(self,row):
        linked=connected(self.previous_trace,row)
        if not linked:
            if self.level is not None:
                self.reset_with_level_N+=1
                self.events.append({'type':'RECOVERY_FLOOR_RESET','minute':row['bar_end_minute'],'before':self.level,'current_segment':row['path']['causal_segment_id']})
            self.level=None
        s=row['state'];p=row['path']
        before=self.level if self.level is not None and valid(row) and self.level['segment']==p['causal_segment_id'] and self.level['effective_from']<=s['as_of'] else None
        return linked,before

    def update(self,row,active):
        s=row['state'];p=row['path'];t=s['as_of'];pivot=s['local_pivot_confirmed']
        if valid(row) and pivot is not None and pivot['kind']=='L':
            self.observed_L.append({'segment':p['causal_segment_id'],'pivot':dict(pivot)})
        if not active or not valid(row) or s['context']!=1 or pivot is None or pivot['kind']!='L' or pivot['generation_reason']!='DC_CONFIRMED':return None
        assert pivot['extremum_t']<=pivot['confirmed_at']<=t,'BLOCKED_V4_RECOVERY_FLOOR_CAUSALITY'
        if s['protected_before'] is None or Fraction(pivot['x'])<=Fraction(s['protected_before']):return None
        if self.level is not None and Fraction(pivot['x'])<=Fraction(self.level['x']):return None
        prior=self.level;initial=prior is None
        after={'x':pivot['x'],'segment':p['causal_segment_id'],'effective_from':t+1,'updated_at':t,'created_at':t if initial else prior['created_at'],'activation_minute':row['bar_end_minute'],'local_L_exact':dict(pivot)}
        update={'type':'RECOVERY_FLOOR_CREATED' if initial else 'RECOVERY_FLOOR_TIGHTENED','minute':row['bar_end_minute'],'scheduled_t':t,'before':prior,'after':after,'context':s['context'],'close_u':s['close_u'],'main_protected_before':s['protected_before'],'main_protected_after_effective_next':s['protected_after_effective_next'],'local_L_exact':dict(pivot),'floor_to_main_distance_before_u':float(Fraction(pivot['x'])-Fraction(s['protected_before']))}
        self.level=after;self.established_ever=True;self.events.append(update)
        return update

@dataclass
class RecoveryLifecycle:
    entry_minute:int
    deadline:int
    fallback:GuardedLifecycle=field(init=False)
    floor:RecoveryFloor=field(default_factory=RecoveryFloor)

    def __post_init__(self):self.fallback=GuardedLifecycle(self.entry_minute,self.deadline)

    @property
    def base(self):return self.fallback.base

    @property
    def guard(self):return self.fallback.guard

    def prefix(self,row):
        self.fallback.prefix(row)
        self.floor.previous_trace=row  # continuity only; never establish a pre-Entry floor

    def observe(self,row):
        if self.base.intent is not None:raise RuntimeError('POST_EXIT_DECISION_PROHIBITED')
        linked,before=self.floor.begin(row)
        intent,metadata=self.fallback.observe(row)  # only this V4 stream; no V3 Replay runner
        fallback_reason=intent['reason'] if intent is not None else None
        s=row['state'];p=row['path'];t=s['as_of'];update=None
        active=self.base.phase=='UP_STRUCTURE_ACTIVE' and not self.base.suspended
        # Preserve the same preplanned closing-intent clock as V3.
        if intent is None and active and linked and valid(row) and s['context']==1 and before is not None and s['protected_before'] is not None and row['bar_end_minute']<self.deadline and Fraction(before['x'])>Fraction(s['protected_before']) and Fraction(s['close_u'])<=Fraction(before['x'])-DELTA:
            intent={'reason':EXIT_D,'minute':row['bar_end_minute'],'scheduled_t':t,'timestamp':row['slot']['bar_end'],'segment':p['causal_segment_id'],'primary':p['Primary_or_null'],'context':s['context'],'protected_before':s['protected_before'],'protected_after_effective_next':s['protected_after_effective_next'],'protected_effective_from':s['protected_effective_from'],'close_u':s['close_u'],'balance':s['balance'],'dwell':p['dwell_observed_bars'],'run_id':p['run_id'],'path_sequence':list(self.base.primary_sequence),'recovery_floor_before':dict(before),'floor_age_since_creation_bars':t-before['created_at'],'floor_age_since_update_bars':t-before['updated_at'],'floor_to_main_distance_at_break_u':float(Fraction(before['x'])-Fraction(s['protected_before'])),'buffer_u':'0.5','path_event_types':[e['event_type'] for e in row['path_events']],'state_events':list(s['events'])}
            self.base.intent=intent
            self.floor.events.append({'type':'RECOVERY_FLOOR_BROKEN','minute':row['bar_end_minute'],'floor_before':dict(before),'context':s['context'],'primary':p['Primary_or_null'],'close_u':s['close_u'],'main_protected_before':s['protected_before']})
        if intent is None:update=self.floor.update(row,active)
        self.floor.previous_trace=row
        metadata.update(recovery_floor_before=before,recovery_floor_after_effective_next=self.floor.level,recovery_floor_update=update,V3_fallback_intent_reason_on_bar=fallback_reason,exit_intent_reason=intent['reason'] if intent else None)
        return intent,metadata
