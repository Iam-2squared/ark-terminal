"""The single State9-native decision policy. Inputs are current/past State9 only."""
from dataclasses import dataclass, field

POLICY = 'STATE9_STRUCTURAL_EXIT_V2'

def valid(row):
    s = row['state']; p = row['path']
    return s['current_semantics_observed'] is True and s['numeric_status'] == 'ACCEPTED' and s['observed_at'] == s['as_of'] and p['Primary_or_null'] is not None

def connected(a,b):
    return a is not None and valid(a) and valid(b) and a['path']['causal_segment_id'] == b['path']['causal_segment_id'] and b['state']['as_of'] == a['state']['as_of'] + 1

@dataclass
class Lifecycle:
    entry_minute: int
    phase: str = 'PRE_UP_STRUCTURE'
    suspended: bool = False
    first_arm_minute: int | None = None
    arm_at_entry: bool = False
    arm_events: list = field(default_factory=list)
    suspensions: list = field(default_factory=list)
    previous: dict | None = None
    intent: dict | None = None
    decisions: int = 0
    pullback_runs: set = field(default_factory=set)
    rise_stop_runs: set = field(default_factory=set)
    tighten_events: list = field(default_factory=list)
    primary_sequence: list = field(default_factory=list)
    last_snapshot: dict | None = None

    def _arm(self,row):
        minute = row['bar_end_minute']
        if self.first_arm_minute is None:
            self.first_arm_minute = minute
            self.arm_at_entry = minute == self.entry_minute
        self.phase = 'UP_STRUCTURE_ACTIVE'; self.suspended = False
        self.arm_events.append({'minute':minute,'segment':row['path']['causal_segment_id'],'context_established_at':row['state']['context_established_at'],'first_arm':len(self.arm_events)==0})

    def observe(self,row):
        if self.intent is not None:
            raise RuntimeError('POST_EXIT_DECISION_PROHIBITED')
        assert row['bar_end_minute'] >= self.entry_minute
        s = row['state']; p = row['path']; self.decisions += 1
        event_names = {e['event_type'] for e in row['path_events']}
        is_valid = valid(row); link = connected(self.previous,row)
        if self.phase == 'UP_STRUCTURE_ACTIVE' and not link and self.previous is not None:
            if not self.suspended:
                self.suspensions.append({'minute':row['bar_end_minute'],'old_segment':self.previous['path']['causal_segment_id'],'new_segment':p['causal_segment_id'],'quality_events':sorted(event_names.intersection({'SEGMENT_BREAK','OBSERVATION_LOST','OBSERVATION_RESUMED'})),'observed':is_valid})
            self.suspended = True
        if not link:
            self.primary_sequence = []
        if is_valid:
            primary = p['Primary_or_null']
            if not self.primary_sequence or self.primary_sequence[-1] != primary:
                self.primary_sequence.append(primary); self.primary_sequence = self.primary_sequence[-3:]
            if primary == 'PULLBACK':
                self.pullback_runs.add(p['run_id'])
            if primary == 'RISE_STOP':
                self.rise_stop_runs.add(p['run_id'])
            if 'PROTECTED_LEVEL_TIGHTENED_EFFECTIVE_NEXT_BAR' in s['events']:
                self.tighten_events.append({'minute':row['bar_end_minute'],'before':s['protected_before'],'after':s['protected_after_effective_next'],'effective_from':s['protected_effective_from']})
        if self.suspended:
            if is_valid:
                if s['context'] == 1:
                    self._arm(row)
                else:
                    self.phase = 'PRE_UP_STRUCTURE'; self.suspended = False
        elif self.phase == 'PRE_UP_STRUCTURE':
            if is_valid and s['context'] == 1:
                self._arm(row)
        elif is_valid and link:
            old = self.previous['state']; trigger = None
            if old['context'] == 1 and s['context'] == -1:
                assert 'STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL' in s['events']
                assert 'CONTEXT_CHANGE' in event_names
                trigger = 'UP_STRUCTURE_REVERSED'
            elif old['context'] == 1 and s['context'] == 0 and s['primary'] == 'RANGE' and s['activity'] == 'BALANCED':
                assert 'CONTEXT_RETIRED_BY_OBSERVED_BALANCE' in s['events']
                assert {'RANGE_ENTER','CONTEXT_CHANGE'} <= event_names
                trigger = 'UP_STRUCTURE_RETIRED_BY_RANGE'
            if trigger:
                self.intent = {'reason':trigger,'minute':row['bar_end_minute'],'scheduled_t':s['as_of'],'timestamp':row['slot']['bar_end'],'segment':p['causal_segment_id'],'primary':p['Primary_or_null'],'context':s['context'],'previous_context':old['context'],'previous_primary':self.previous['path']['Primary_or_null'],'previous_protected_after':old['protected_after_effective_next'],'previous_protected_effective_from':old['protected_effective_from'],'protected_before':s['protected_before'],'protected_after_effective_next':s['protected_after_effective_next'],'protected_effective_from':s['protected_effective_from'],'close_u':s['close_u'],'balance':s['balance'],'dwell':p['dwell_observed_bars'],'run_id':p['run_id'],'path_sequence':list(self.primary_sequence),'path_event_types':[e['event_type'] for e in row['path_events']],'state_events':list(s['events'])}
        self.previous = row
        self.last_snapshot = {'minute':row['bar_end_minute'],'primary':p['Primary_or_null'],'context':s['context'],'protected_before':s['protected_before'],'protected_after_effective_next':s['protected_after_effective_next'],'balance':s['balance'],'dwell':p['dwell_observed_bars'],'segment':p['causal_segment_id'],'observed':is_valid,'path_sequence':list(self.primary_sequence)}
        return self.intent
