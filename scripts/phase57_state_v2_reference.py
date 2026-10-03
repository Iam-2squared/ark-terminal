"""Compatibility NOW entry point. Future lives only in phase57_state_v2.future.

The first 2026-09-22 adapter is preserved in the bootstrap artifact; it was not
accepted. This wrapper does not import or expose the Future evaluator.
"""
from phase57_state_v2.common import r as m, SAFETY, digest as canonical_hash, F
from phase57_state_v2.now import now_state_reference_v2 as _now


def make_context(today,previous,calendar,daily):
    ds=list(calendar);i=ds.index(today.day);prevday=ds[i-1] if i else None
    scale=m.scale_from_previous(previous,today.day,prevday,today.security,today.basis) if previous is not None else {'status':'PREVIOUS_CONTEXT_UNAVAILABLE','scale':None,'blockN':0}
    bs=previous.bars if previous else ()
    return {'previous':bs,'previousDay':prevday,'previousBasis':previous.basis if previous else None,
      'previousContext':{'observedHigh':max(b.h for b in bs),'observedLow':min(b.l for b in bs)} if bs else None,
      'scale':scale,'dailyRows':list(daily),'dailyReasons':{},'sourceHashes':{'todayMinute':None,'previousMinute':None,'dailyProjection':None},
      'quality':['CALLER_SUPPLIED_CONTEXT_NOT_HISTORICAL_ACCEPTANCE'],'calendar':ds,'basis':today.basis,
      'sourceVintageId':'CALLER_SUPPLIED_UNVERIFIED','previousCoverage':F(len(bs),len(previous.ends)) if previous and previous.ends else F(0)}

def now_state_reference_v2(today,previous,calendar,daily,asof):
    return _now(prefix=today.bars,ends=today.ends,asof=asof,
        identity={'opportunityId':today.day+'|'+today.security,'sessionDate':today.day,'securityId':today.security,'selectorAt':None,'elapsedActiveMinutesFromSelector':None},
        context=make_context(today,previous,calendar,daily))

def primary(reasons):
    from phase57_state_v2.common import ordered_reasons
    codes=ordered_reasons(reasons)
    return codes[0] if codes else None
