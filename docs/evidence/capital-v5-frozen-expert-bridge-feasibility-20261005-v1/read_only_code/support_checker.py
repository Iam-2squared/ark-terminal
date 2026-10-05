"""Pure support preflight for future separately fixed specs; never emits actions.

This Work calls it on synthetic fixtures only. No real-data condition search or routing.
"""
from adapter import support
def check(packet,snapshot,channel,required_heads=()):
 out=support(snapshot,packet,channel)
 if not out['support']:return out
 for h,wanted in required_heads:
  v=packet['heads'][h]
  if not v['available'] or v.get(wanted) is None:return {'support':False,'unknown':True,'reason':'REQUIRED_SCORE_UNKNOWN'}
  if not v[wanted]:return {'support':False,'unknown':False,'reason':'FIXED_HYPOTHETICAL_CONDITION_FALSE'}
 return {'support':True,'unknown':False,'reason':'STRUCTURAL_SUPPORT_ONLY_NOT_ECONOMIC_PROOF'}
def summarize(records):
 n=sum(r['support'] for r in records);unknown=sum(r['unknown'] for r in records)
 return {'support_N':n,'unknown_N':unknown,'status':'NO_REPLAY_REQUIRED' if n==0 and unknown==0 else 'UNMEASURABLE' if unknown else 'SUPPORT_ONLY','runtime_actions':0,'automatic_condition_relaxation':False}
