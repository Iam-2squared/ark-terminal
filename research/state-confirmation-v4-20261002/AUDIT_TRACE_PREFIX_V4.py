"""Local source/timestamp/tuple audit; not a State9 or Path kernel re-audit."""
from fractions import Fraction
def exact(v):
 if v is None:return None
 if isinstance(v,bool):return int(v)
 if isinstance(v,dict):return float(Fraction(v['num'],v['den']))
 return float(Fraction(str(v)))
def run(a,stream,traces):
 for r,s in zip(stream,traces):
  t=r['scheduled_t'];f=r['features'];src=r['audit_source']
  a.check(s['as_of']==t and (s['observed_at'] is None or s['observed_at']<=t),'independent_trace_asof')
  a.check(bool(f['observed'])==bool(s['current_semantics_observed'])==bool(src['observed']),'independent_observed_tuple')
  for k,sk in [('local_direction','leg_direction'),('context_direction','context'),('fast','fast_flag'),('fast_applicable','fast_applicable_to_primary'),('close_u','close_u')]:a.check(a.near(f[k],exact(s[sk])),'independent_current_tuple_'+k)
  a.check(f['formal_primary']==(src['formal_primary'] if src['formal_primary'] is not None else '__FORMAL_NULL__'),'independent_formal_null_not_carried')
  for name in ['range_analysis','fast_analysis']:
   for field in ['window_ids','old_window_ids']:a.check(all(x<=t for x in (s.get(name) or {}).get(field,[])),'independent_analysis_source_window')
  for name,fields in [('stop',['start','recognized_at','progress_at']),('balance',['established_at'])]:
   for field in fields:
    v=(s.get(name) or {}).get(field);a.check(v is None or v<=t,'independent_recognition_not_future')
  for event in src['events']:a.check(event['scheduled_t']==t and event['bar_end']==r['bar_end'],'independent_event_destination_timestamp')
  if src['observed']:a.check(src['raw_present'] and r['source_pointer'] is not None,'independent_current_source_pointer')
