"""Allowlisted causal snapshot extraction; no label inputs or future run records."""
from fractions import Fraction
from collections import deque

def number(v):
 if v is None:return None
 if isinstance(v,bool):return int(v)
 if isinstance(v,dict):
  assert set(v)=={'num','den'},'FROZEN_RATIO_SCHEMA'
  return float(Fraction(v['num'])/Fraction(v['den']))
 return float(Fraction(str(v)))
def category(v):return '__MISSING__' if v is None else str(v)
def diff(a,b):return None if a is None or b is None else float(Fraction(str(a))-Fraction(str(b)))

class FeatureBuilder:
 def __init__(self,schema):
  self.schema=schema;self.segment=None;self.segment_start=None;self.history=[]
  self.window=deque(maxlen=15);self.reset_at=None;self.previous_primary=None;self.previous_dwell=None
  self.last_endpoint=None
 def push(self,state,endpoint,new_events,current_runs):
  t=endpoint['scheduled_t'];seg=endpoint['causal_segment_id'];event_types=[x['event_type'] for x in new_events]
  if seg!=self.segment:
   self.segment=seg;self.segment_start=t;self.history=[];self.window.clear();self.previous_primary=None;self.previous_dwell=None;self.reset_at=t
  if any(x in event_types for x in ('SEGMENT_BREAK','OBSERVATION_LOST')):self.reset_at=t
  transitions=[x for x in new_events if x['event_type']=='TRANSITION']
  if transitions:
   assert len(transitions)==1
   self.history.append(transitions[0]);self.previous_primary=transitions[0]['from_primary_or_null']
   closed=[r for r in current_runs if r.get('closed_at')==t and r.get('closed_reason')=='PRIMARY_CHANGE']
   assert len(closed)==1
   self.previous_dwell=closed[0]['dwell_observed_bars']
  self.window.append((int('HOLD' in event_types),int(bool(transitions))))
  st=state.get('stop') or {};bal=state.get('balance') or {};ra=state.get('range_analysis') or {};fa=state.get('fast_analysis') or {}
  for analysis in [ra,fa]:
   for k in ['window_ids','old_window_ids']:
    assert all(x<=t for x in analysis.get(k,[])),'FUTURE_ANALYSIS_WINDOW'
  for o,k in [(st,'start'),(st,'recognized_at'),(st,'progress_at'),(bal,'established_at')]:
   assert o.get(k) is None or o[k]<=t,'FUTURE_RECOGNITION_METADATA'
  assert state.get('observed_at') is None or state['observed_at']<=t
  vals={
   'observed':int(state['current_semantics_observed']),
   'observed_age':None if state['observed_at'] is None else t-state['observed_at'],
   'local_direction':number(state['leg_direction']),'context_direction':number(state['context']),
   'fast':number(state['fast_flag']),'fast_applicable':number(state['fast_applicable_to_primary']),
   'close_u':number(state['close_u']),
   'stop_direction':number(st.get('direction')),'stop_width':diff(st.get('high'),st.get('low')),
   'stop_center_distance':diff(state['close_u'],st.get('center')),
   'stop_age':None if not st else t-st['start'],
   'stop_recognized_age':None if not st else t-st['recognized_at'],
   'stop_count':number(st.get('count')),'stop_progress_age':None if not st else t-st['progress_at'],
   'range_width':diff(bal.get('high'),bal.get('low')),
   'range_established_age':None if not bal else t-bal['established_at'],
   'range_exit_low_distance':diff(state['close_u'],bal.get('exit_low')),
   'range_exit_high_distance':diff(bal.get('exit_high'),state['close_u']),
   'formal_primary':'__FORMAL_NULL__' if endpoint['Primary_or_null'] is None else endpoint['Primary_or_null'],
   'display_primary':category(state['primary']),
   'activity':category(state['activity']),'basis':category(state['basis']),
   'direction_basis':category(state['direction_basis']),'numeric_status':category(state['numeric_status']),
   'rejection_reason':category(state['rejection_reason']),
   'auction':category((state['bar_metadata'] or {}).get('auction')),
   'source':category((state['bar_metadata'] or {}).get('source')),
   'source_events':'|'.join(sorted(state['events'])),'range_reason':category(bal.get('reason')),
   'dwell_scheduled_bars':endpoint['dwell_scheduled_bars'],'dwell_observed_bars':endpoint['dwell_observed_bars'],
   'entered_age':None if endpoint['entered_at'] is None else t-endpoint['entered_at'],
   'previous_run_dwell':self.previous_dwell,
   'bars_since_transition':None if not self.history else t-self.history[-1]['scheduled_t'],
   'segment_age':t-self.segment_start,'segment_transition_count':len(self.history),
   'recent_hold_count_15':sum(x[0] for x in self.window),
   'recent_transition_count_15':sum(x[1] for x in self.window),
   'recent_transition_density_15':sum(x[1] for x in self.window)/len(self.window),
   'reset_recency':None if self.reset_at is None else t-self.reset_at,
   'current_run_primary':category(endpoint['Primary_or_null']),
   'previous_primary':category(self.previous_primary),
   'last_transition_from':category(self.history[-1]['from_primary_or_null']) if self.history else '__MISSING__',
   'last_transition_to':category(self.history[-1]['to_primary_or_null']) if self.history else '__MISSING__'
  }
  for k in ['net','tv','span','width','eta','turns','guard']:vals['range_analysis_'+k]=number(ra.get(k))
  for k in ['A','B','C','D']:vals['range_'+k]=number((ra.get('conditions') or {}).get(k))
  for k in ['net','tv','eta','directional_net']:vals['fast_analysis_'+k]=number(fa.get(k))
  for i in range(4):
   tr=self.history[-1-i] if len(self.history)>i else None
   vals['transition_seq_'+str(i)]='__MISSING__' if tr is None else tr['from_primary_or_null']+'>'+tr['to_primary_or_null']
  expected=sum([self.schema[k] for k in ['numeric_state','categorical_state','numeric_path','categorical_path']],[])
  assert set(vals)==set(expected),'FEATURE_ALLOWLIST'
  self.last_endpoint=endpoint
  return vals
