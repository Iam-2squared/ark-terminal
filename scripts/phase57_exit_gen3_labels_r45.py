"""Training-only R45 sampled executable utility targets. Never a runtime input."""
from bisect import bisect_left
import math
from scripts.phase57_exit_execution_contract_v1 import continuous_minutes
from scripts.phase57_exit_gen3_runtime_r45 import HEADS, EPOCH, finite, require, load_protocol

_P=load_protocol()
REASONS=('AVAILABLE','STALE_NOW','NO_CONTINUOUS_ANCHOR','INSUFFICIENT_REMAINING_BARS',
         'MISSING_OR_INVALID_EXACT_REFERENCE','INVALID_AUCTION','PROTECTION_NOT_ELIGIBLE')


def reference_minutes(day, now):
    require(type(now) is int and now in EPOCH,'R45_LABEL_NOW')
    starts=continuous_minutes(day); index=bisect_left(starts,now); remaining=len(starts)-index
    h=min(15,remaining)
    if remaining==0:
        return None,[],h,'NO_CONTINUOUS_ANCHOR'
    if h<3:
        return starts[index],[],h,'INSUFFICIENT_REMAINING_BARS'
    offsets=[(h+2)//3,(2*h+2)//3,h]
    samples=[starts[index+d] if index+d<len(starts) else 930 for d in offsets]
    require(len(set(samples))==3 and min(samples)>now,'R45_LABEL_REFERENCE_ORDER')
    return starts[index],samples,h,None


def utility_labels(day,now,entry_price,fresh,certified_mfe,indexed_rows):
    require(finite(entry_price) and entry_price>0,'R45_LABEL_ENTRY_PRICE')
    require(type(fresh) is bool,'R45_LABEL_FRESH')
    anchor,samples,h,reason=reference_minutes(day,now)
    if not fresh:reason='STALE_NOW'
    out={'targets':dict.fromkeys(HEADS),'available':dict.fromkeys(HEADS,False),
         'knownAt':dict.fromkeys(HEADS),'horizonBars':h,'sampleReferenceMinutes':samples,
         'anchorMinute':anchor,'reasonCode':dict.fromkeys(HEADS,reason)}
    if reason:return out
    prices=[]
    for t in [anchor]+samples:
        row=indexed_rows.get(t)
        if row is None or len(row)!=7 or not finite(row[1]) or row[1]<=0:
            reason='MISSING_OR_INVALID_EXACT_REFERENCE';break
        if t==930 and not all(finite(v) and v==row[1] for v in row[1:5]):
            reason='INVALID_AUCTION';break
        prices.append(float(row[1]))
    if reason:
        out['reasonCode']=dict.fromkeys(HEADS,reason);return out
    utilities=[100*(v-prices[0])/entry_price for v in prices[1:]]
    p=_P; label=p['labels']
    c=int(utilities[-1]>=label['continuationMarginPp'] and sum(x>0 for x in utilities)>=label['positiveOrNegativeSampleMinimum'])
    d=int(utilities[-1]<=-label['deteriorationMarginPp'] and sum(x<0 for x in utilities)>=label['positiveOrNegativeSampleMinimum'])
    protection=int(utilities[-1]<=-label['protectionMarginPp']) if finite(certified_mfe) and certified_mfe>=p['policy']['profitArmMfePp'] else None
    vals=(c,protection,d)
    out.update(targets=dict(zip(HEADS,vals)),available={k:v is not None for k,v in zip(HEADS,vals)},
               knownAt={k:samples[-1] if v is not None else None for k,v in zip(HEADS,vals)},
               reasonCode={k:'AVAILABLE' if v is not None else 'PROTECTION_NOT_ELIGIBLE' for k,v in zip(HEADS,vals)},
               anchorPrice=prices[0],futureExecutablePrices=prices[1:],futureUtility=utilities)
    return out
