"""Second minimal semantic implementation from frozen v2 clauses 6/7.

Deliberately imports no production helper or numerical engine. Its independence
is code-path independence, not an external human/AI review. It checks the core
semantic projection; it does not independently implement every OHLC primitive.
"""
from __future__ import annotations
import json

ORDER=['OBS_CURRENT_BAR_NOT_OBSERVED','OBS_SESSION_BOUNDARY','OBS_SHORT_SESSION_HISTORY',
 'OBS_MISSING_SCHEDULED_BAR','OBS_LATEST5_INCOMPLETE','SCALE_PREVIOUS_CONTEXT_UNAVAILABLE',
 'SCALE_PRICE_BASIS_UNVERIFIED','SCALE_INSUFFICIENT_BLOCKS','SCALE_ZERO','PIVOT_INSUFFICIENT_COUNT']

def _record(status,value=None,reasons=()):
    rr=sorted(set(reasons),key=lambda x:(ORDER.index(x) if x in ORDER else len(ORDER),x))
    return {'status':status,'value':value,'reasonCodes':rr,'primaryReason':rr[0] if rr else None}

def core_from_witness(witness,scale_status):
    window=witness['observation']; state=witness['state']; d=witness.get('descriptors')
    labels={'CURRENT_BAR_UNAVAILABLE':'OBS_CURRENT_BAR_NOT_OBSERVED','SHORT_SESSION_HISTORY':'OBS_SHORT_SESSION_HISTORY','SESSION_BOUNDARY':'OBS_SESSION_BOUNDARY','MISSING_SCHEDULED_BAR':'OBS_MISSING_SCHEDULED_BAR'}
    obs=[labels[v] for v in window['reasons']]
    if window['status']!='COMPLETE':obs+=['OBS_LATEST5_INCOMPLETE']
    scale={'AVAILABLE':None,'SCALE_INSUFFICIENT':'SCALE_INSUFFICIENT_BLOCKS','SCALE_ZERO':'SCALE_ZERO','PREVIOUS_CONTEXT_UNAVAILABLE':'SCALE_PREVIOUS_CONTEXT_UNAVAILABLE','PRICE_BASIS_UNVERIFIED':'SCALE_PRICE_BASIS_UNVERIFIED'}[scale_status]
    blocked=state['identificationStatus'] in {'SCALE_UNAVAILABLE','CURRENT_BAR_UNAVAILABLE'}
    reasons=obs+([scale] if scale else [])
    result={'direction':_record('DEFINED',d['direction']) if d else _record('NOT_EVALUATED',reasons=obs)}
    n=len(state.get('pivots',[]));active=state.get('structure')
    if active:result['structure']=_record('DEFINED',active['kind'])
    elif blocked:result['structure']=_record('NOT_EVALUATED',reasons=reasons)
    elif n>=4:result['structure']=_record('DEFINED','NONE')
    else:result['structure']=_record('INSUFFICIENT',reasons=['PIVOT_INSUFFICIENT_COUNT'])
    result['phase']=_record('NOT_EVALUATED',reasons=reasons) if blocked else _record('DEFINED',state.get('phase',[]))
    if blocked:result['pivotSignature']=_record('NOT_EVALUATED',reasons=reasons)
    elif n<4:result['pivotSignature']=_record('INSUFFICIENT',reasons=['PIVOT_INSUFFICIENT_COUNT'])
    else:
        high=[x['price'] for x in state['pivots'][-4:] if x['kind']=='HIGH'];low=[x['price'] for x in state['pivots'][-4:] if x['kind']=='LOW']
        def label(a,b):return 'EQ' if a==b else 'UP' if a>b else 'DOWN'
        result['pivotSignature']=_record('DEFINED',{'highRelation':'H_'+label(high[1],high[0]),'lowRelation':'L_'+label(low[1],low[0])})
    return result

def projection(actual):
    return {k:{field:actual[k][field] for field in ('status','value','reasonCodes','primaryReason')} for k in ('direction','structure','phase','pivotSignature')}

def verify_core(actual,mechanical,scale_status):
    # Canonical comparison for the complete projection, not merely label counts.
    want=core_from_witness(mechanical,scale_status)
    got=projection(actual)
    if json.dumps(got,sort_keys=True)!=json.dumps(want,sort_keys=True):raise ValueError('INDEPENDENT_SEMANTIC_PROJECTION_MISMATCH')
    return True
