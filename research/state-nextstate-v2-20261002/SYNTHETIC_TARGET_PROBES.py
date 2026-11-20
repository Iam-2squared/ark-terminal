import json
from pathlib import Path
from BUILD_TARGETS_V2 import state_target
from INDEPENDENT_AUDIT_V2 import target_ref
R=Path(__file__).resolve().parent
def stream(states,segments=None):
 rows=[]
 for i,p in enumerate(states):
  seg=segments[i] if segments else 'S1';changed=i>0 and p is not None and states[i-1] is not None and p!=states[i-1] and seg==(segments[i-1] if segments else 'S1')
  rows.append({'row_key':str(i),'bar_end':f'T{i:03d}','tradable_index':i,'causal_segment_id':seg,'audit_source':{'observed':p is not None,'formal_primary':p,'numeric_status':'ACCEPTED' if p else 'NOT_AVAILABLE','auction':'CONTINUOUS','events':[{'event_type':'TRANSITION','from_primary_or_null':states[i-1],'to_primary_or_null':p}] if changed else []}})
 return rows
cases=[('HOLD',['RISE']*31,None,'NEXT_DISTINCT_PRIMARY',(False,None,None,'NO_TRANSITION_WITHIN30')),('HOLD_BINARY',['RISE']*31,None,'TRANSITION_WITHIN30',(True,'NO_TRANSITION','T030',None)),('HOLD_NEXT',['RISE']*31,None,'NEXT_OBSERVED_PRIMARY',(True,'RISE','T001',None)),('EARLY_TRANSITION_LATER_NULL',['RISE']*3+['RISE_STOP']*7+[None]+['RISE']*20,None,'NEXT_DISTINCT_PRIMARY',(True,'RISE_STOP','T003',None)),('BINARY_REQUIRES_FULL_OBSERVED',['RISE']*3+['RISE_STOP']*7+[None]+['RISE']*20,None,'TRANSITION_WITHIN30',(False,None,None,'NULL_GAP_OR_AUCTION')),('NO_NULL_SKIP',['RISE',None,'DROP'],None,'NEXT_OBSERVED_PRIMARY',(False,None,None,'NULL_GAP_OR_AUCTION')),('NO_RESET_CROSS',['RISE','DROP'],['S1','S2'],'NEXT_DISTINCT_PRIMARY',(False,None,None,'SEGMENT_BREAK')),('FIRST_EVENT',['RISE','SHARP_RISE','RISE_STOP']+['RISE_STOP']*28,None,'NEXT_DISTINCT_PRIMARY',(True,'SHARP_RISE','T001',None)),('EXACT30',['RISE']*30+['PULLBACK'],None,'NEXT_DISTINCT_PRIMARY',(True,'PULLBACK','T030',None)),('AFTER30_NOT_ELIGIBLE',['RISE']*31+['PULLBACK'],None,'NEXT_DISTINCT_PRIMARY',(False,None,None,'NO_TRANSITION_WITHIN30'))]
results=[]
for name,states,segments,task,expected in cases:
 s=stream(states,segments);a=state_target(s,0,task);c=(a['available'],a['target'],a['label_end'],a['reason']);b=target_ref(s,0,task);assert c==b==expected,(name,c,b,expected);results.append({'id':name,'task':task,'PASS':True,'expected':expected})
(R/'SYNTHETIC_TARGET_PROBES.json').write_text(json.dumps({'probes':results,'assertions':len(results)*2,'mismatches':0,'market_lookahead':0,'kernel_reruns':0},indent=2)+'\n')
print(json.dumps({'probes':len(results),'assertions':len(results)*2,'mismatches':0}))
