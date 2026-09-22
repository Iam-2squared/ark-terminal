"""NOW reference from a caller-supplied prefix. No Future module or target input."""
from __future__ import annotations
from .common import (r, F, VERSION, SAFETY, PITReader, axis, iso, observation,
 semantic_axes, attributes, static_and_vwap_events, validate_tree, digest)


def now_state_reference_v2(*, prefix, ends, asof, identity, context):
    """Evaluate one checkpoint independently; neither suffix nor prior NOW output is accepted.

    context is fixed source material for the actual prior session / exact daily lags.
    Historical qualification is retained; it is NOT independent as-of verification.
    """
    day=identity['sessionDate']; reader=PITReader(day,asof)
    bs=reader.bars(prefix,day,'todayPrefixAdmission')
    if any(b.end not in ends for b in bs):raise ValueError('BAR_OUTSIDE_INJECTED_CALENDAR')
    rows=reader.daily(context['dailyRows'],day)
    prev=context['previous']
    if prev:
        reader.bars(prev,context['previousDay'],'previousSessionScaleAndContext')
    # This material was built from verified immutable historical source. Never infer clean PIT.
    scale=context['scale']
    mech=r.snapshot(reader.bars(bs,day,'snapshot'),ends,asof,scale.get('scale'))
    oq=observation(reader.bars(bs,day,'observation'),ends,asof)
    axes=semantic_axes(mech,scale,oq)
    attrs=attributes(mech,bs,ends,asof,scale,oq,reader,day)
    dc=r.daily_context(day,context['calendar'],rows,identity['securityId'],context['basis'])
    dc['reasons'].update(context.get('dailyReasons',{}))
    pc=context.get('previousContext')
    if scale['status']=='PRICE_BASIS_UNVERIFIED':pc=None
    events=static_and_vwap_events(bs,ends,asof,scale.get('scale'),dc,pc,reader,day)
    daily={}
    dates=context['calendar']; idx=dates.index(day)
    raw={z['date']:z for z in rows}
    for lag in range(1,6):
        d=dates[idx-lag] if idx>=lag else None
        reason='SHORT_CALENDAR_HISTORY' if d is None else dc['reasons'].get(d)
        if d is not None and d not in dc['rawDaily']: reason=reason or 'MISSING_DAILY'
        daily['D'+str(lag)]=axis('NOT_EVALUATED',reasons=[reason],sourceDate=d) if reason else axis('DEFINED',dc['rawDaily'][d],sourceDate=d,sourceHash=context['sourceHashes']['dailyProjection'],sourceKnownAt=raw[d].get('knownAt'))
    if prev and context['previousBasis']==context['basis'] and context['basis']:
        previous=axis('DEFINED',{'observedHigh':max(b.h for b in prev),'observedLow':min(b.l for b in prev),'observedRegularClose':prev[-1].c,'observed1mN':len(prev)},sourceDate=context['previousDay'],coverage=context['previousCoverage'],sourceHash=context['sourceHashes'].get('previousMinute'))
    else:
        previous=axis('NOT_EVALUATED',reasons=['PRICE_BASIS_UNVERIFIED' if prev else 'PREVIOUS_CONTEXT_UNAVAILABLE'],sourceDate=context['previousDay'])
    live=reader.bars(bs,day,'todayContext')
    if live:
        vol=sum(b.volume for b in live) if all(b.volume is not None for b in live) else None
        val=sum(b.value for b in live) if all(b.value is not None for b in live) else None
        today=axis('DEFINED',{'observedHigh':max(b.h for b in live),'observedLow':min(b.l for b in live),'observedClose':live[-1].c,'observedN':len(live),'scheduledN':sum(e<=asof for e in ends),'observedVWAP':val/vol if vol and val is not None else None},prefixComplete=len(live)==sum(e<=asof for e in ends),lastObservedAt=iso(day,live[-1].end))
    else:today=axis('NOT_EVALUATED',reasons=['TODAY_NOT_OBSERVED'])
    metadata=reader.metadata()
    oq.update(metadata,sourceVintageId=context['sourceVintageId'],sourceHashes=context['sourceHashes'])
    current_schedule=[e for e in ends if e<=asof]
    seg='AM' if asof<=690 else 'PM'
    out={**identity,'checkpointAsOf':iso(day,asof),'activeMinutesSinceOpen':len(current_schedule),'sessionSegment':seg,'definitionVersion':VERSION,'inheritedRuleVersion':r.VERSION,'artifactKind':'now_state_reference_v2',**axes,'observationQuality':oq,'attributes':attrs,'events':events,'context':{'recentDaily':daily,'previousObservedSession':previous,'todayOpenToNow':today},'scale':{'scaleSpecId':'PREVIOUS_SESSION_COMPLETE_5M_TR_MEDIAN_V1','scaleStatus':scale['status'],'scaleValue':scale.get('scale'),'scaleSourceDay':context['previousDay'],'previousComplete5mBlockN':scale.get('blockN',0),'scaleSource':context['sourceHashes'].get('previousMinute'),'scaleProvenance':context['quality']},'causalMetadata':{**metadata,'sourceVintageId':context['sourceVintageId'],'tickSize':None,'tickSizeStatus':'UNAVAILABLE_NOT_INFERRED','tickSizeSource':None,'atDailyLimit':None,'dailyLimitStatus':'UNAVAILABLE_NOT_INFERRED','dailyLimitSource':None,'timestampConvention':'REGULAR_MINUTE_START_NORMALIZED_ONCE_TO_END_PLUS_ONE','dailySourceTimePrecision':'DATE_ONLY_END_OF_DAY_BOUND_NOT_RECEIVED_AT'},'dataQualification':context['quality'],'safety':SAFETY}
    validate_tree(out)
    validate_now(out)
    return out


def validate_now(z):
    for name,allowed in [('direction',{'UP','DOWN','UNCHANGED'}),('structure',{'UP_STRUCTURE','DOWN_STRUCTURE','RANGE_STRUCTURE','NONE'})]:
        if z[name]['status']=='DEFINED' and z[name]['value'] not in allowed:raise ValueError('AXIS_VALUE_ENUM:'+name)
    phase=z['phase']
    if phase['status']=='DEFINED':
        if not isinstance(phase['value'],list) or len(set(phase['value']))!=len(phase['value']) or not set(phase['value'])<={'PROGRESSION','CORRECTION','RECOVERY','BALANCE','RESTRUCTURING'}:raise ValueError('PHASE_ENUM')
    if any(x is not False for x in z['safety'].values()) or len(z['safety'])!=9:raise ValueError('SAFETY9')
    if z['causalMetadata']['maxSourceTimestamp'] and z['causalMetadata']['maxSourceTimestamp']>z['checkpointAsOf']:raise ValueError('MAX_SOURCE_FUTURE')
    if z['causalMetadata']['maxKnownAt'] and z['causalMetadata']['maxKnownAt']>z['checkpointAsOf']:raise ValueError('MAX_KNOWN_FUTURE')
    for name,zaxis in z['attributes'].items():
        allowed={'CHOPPINESS','NONE'} if name=='choppiness' else {'EXPANSION','COMPRESSION','NONE'}
        if zaxis['status']=='DEFINED' and zaxis['value'] not in allowed:raise ValueError('ATTRIBUTE_ENUM')
