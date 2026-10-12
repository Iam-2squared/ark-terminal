"""Teacher-reference module. It never imports NOW and never modifies its artifact."""
from __future__ import annotations
from .common import r, VERSION, SAFETY, PITReader, iso, observation, semantic_axes, validate_tree
H = 10
RESOLUTION_STATUSES=frozenset(('RESOLVED_WITHIN_H','NOT_RESOLVED_WITHIN_H','CENSORED'))

def future_resolution_v2(*, bounded_bars, ends, asof, identity, context):
    """Bounded evidence-only adjudication: effectiveAt<=t, confirmedAt<=t+H.

    Resolution status concerns an active StructureAtT, not PnL or a forecast of t+H.
    The frozen engine's witness confirmedAt sets the earliest confirmation delay;
    a censored H retains partial witness without calling the full window complete.
    """
    day=identity['sessionDate']
    future=[e for e in ends if e>asof][:H]
    cutoff=future[-1] if future else asof
    reader=PITReader(day,cutoff)
    bs=reader.bars(bounded_bars,day,'futureBoundedPrefix')
    if any(b.end not in ends for b in bs):raise ValueError('BAR_OUTSIDE_INJECTED_CALENDAR')
    # reference_at is the unmodified, source-pinned evaluator.
    mech=r.reference_at(bs,ends,asof,context['scale'].get('scale'))
    prefix=tuple(b for b in bs if b.end<=asof and (b.available_at is None or b.available_at<=asof))
    oq=observation(prefix,ends,asof)
    axes=semantic_axes(mech,context['scale'],oq)
    ps=mech['state'].get('pivots',[])
    if any(p['effectiveAt']>asof or p['confirmedAt']>cutoff for p in ps):raise ValueError('FUTURE_TARGET_BOUNDARY')
    found={b.end for b in bs}
    flags=[]
    if any(e not in found for e in future):flags.append('OBSERVATION_CENSORED_BEFORE_H')
    if len(future)<H:flags.append('SESSION_CENSORED_BEFORE_H')
    active=mech['state'].get('structure')
    typ=active['kind'] if active else None
    status='CENSORED' if flags else 'RESOLVED_WITHIN_H' if active else 'NOT_RESOLVED_WITHIN_H'
    confirmed=active.get('confirmedAt') if active else None
    minutes=sum(asof<e<=confirmed for e in ends) if confirmed is not None else None
    if minutes is not None and not 0<=minutes<=H:raise ValueError('RESOLUTION_DELAY')
    z={**identity,'checkpointAsOf':iso(day,asof),'definitionVersion':VERSION,'artifactKind':'future_resolution_v2','horizonActiveMinutes':H,'adjudicatedStructureAtT':axes['structure'],'adjudicatedPhaseAtT':axes['phase'],'adjudicatedPivotSignatureAtT':axes['pivotSignature'],'lateConfirmedPivotN':sum(p['confirmedAt']>asof for p in ps),'resolutionStatus':status,'resolutionType':typ,'resolutionActiveMinutes':minutes,'censorFlags':flags,'futureCutoff':iso(day,cutoff),'futureScheduledEnds':future,'futureMissingEnds':[e for e in future if e not in found],'futureMaxSourceTimestamp':reader.metadata()['maxSourceTimestamp'],'futureMaxKnownAt':reader.metadata()['maxKnownAt'],'futureSourceHashes':context['sourceHashes'],'sourceVintageId':context['sourceVintageId'],'stateAtTWitness':{'pivots':ps,'activeStructure':active},'dataQualification':context['quality'],'safety':SAFETY}
    validate_tree(z)
    validate_future(z)
    return z

def validate_future(z):
    if z['horizonActiveMinutes']!=H or z['resolutionStatus'] not in RESOLUTION_STATUSES:raise ValueError('FUTURE_SCHEMA')
    if z['resolutionType'] not in (None,'UP_STRUCTURE','DOWN_STRUCTURE','RANGE_STRUCTURE'):raise ValueError('RESOLUTION_TYPE')
    allowed={'OBSERVATION_CENSORED_BEFORE_H','SESSION_CENSORED_BEFORE_H'}
    if not set(z['censorFlags'])<=allowed or bool(z['censorFlags'])!=(z['resolutionStatus']=='CENSORED'):raise ValueError('CENSOR_SCHEMA')
    if z['futureMaxSourceTimestamp'] and z['futureMaxSourceTimestamp']>z['futureCutoff']:raise ValueError('FUTURE_MAX_TIMESTAMP')
