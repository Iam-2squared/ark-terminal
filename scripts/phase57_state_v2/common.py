"""Shared exact primitives and closed semantic contract. No Future-module import."""
from __future__ import annotations
import datetime as dt
import hashlib
import importlib.util
import json
import sys
from fractions import Fraction as F
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ENGINE_SHA = 'e57d41b1a9472fb0ed254895d956623a438557f540443c0bee14a6db8f2d8d3d'
p = ROOT / 'docs/phase57-five-minute-entry-state/mechanical-v1/reference.py'
if hashlib.sha256(p.read_bytes()).hexdigest() != ENGINE_SHA:
    raise RuntimeError('FROZEN_NUMERIC_ENGINE_HASH_MISMATCH')
spec = importlib.util.spec_from_file_location('phase57_state_v2_frozen_numeric', p)
r = sys.modules.get(spec.name)
if r is None:
    r = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = r
    spec.loader.exec_module(r)
VERSION = 'state-reference-v2.0'
JST = dt.timezone(dt.timedelta(hours=9))
SAFETY = dict(r.SAFETY)
PRECEDENCE = ('OBS_CURRENT_BAR_NOT_OBSERVED','OBS_SESSION_BOUNDARY',
 'OBS_SHORT_SESSION_HISTORY','OBS_MISSING_SCHEDULED_BAR','OBS_LATEST5_INCOMPLETE',
 'SCALE_PREVIOUS_CONTEXT_UNAVAILABLE','SCALE_PRICE_BASIS_UNVERIFIED',
 'SCALE_INSUFFICIENT_BLOCKS','SCALE_ZERO','PIVOT_INSUFFICIENT_COUNT')
REASONS = frozenset(PRECEDENCE + ('OBS_NOT_OBSERVED_CAUSE_UNKNOWN',
 'PRIOR_WINDOW_NOT_COMPARABLE','ZERO_DENOMINATOR','VOLUME_UNAVAILABLE',
 'TRADING_VALUE_UNAVAILABLE','NO_TRIGGER_EVENT','PERSISTENCE_RIGHT_CENSORED',
 'PERSISTENCE_SESSION_BOUNDARY','PERSISTENCE_OBSERVATION_INSUFFICIENT',
 'LEVEL_CONTEXT_UNAVAILABLE','VWAP_PREFIX_INCOMPLETE','VWAP_ACTIVITY_UNAVAILABLE',
 'VWAP_ZERO_VOLUME','MISSING_DAILY','INVALID_DAILY','INVALID_OHLC',
 'CORPORATE_ACTION','OUTSIDE_AUTHORIZED_DEVELOPMENT','PRICE_BASIS_UNVERIFIED',
 'PREVIOUS_CONTEXT_UNAVAILABLE','SHORT_CALENDAR_HISTORY','TODAY_NOT_OBSERVED'))
STATUSES = frozenset(('DEFINED','INSUFFICIENT','NOT_EVALUATED','NOT_APPLICABLE'))
SCALE_REASON = {'PREVIOUS_CONTEXT_UNAVAILABLE':'SCALE_PREVIOUS_CONTEXT_UNAVAILABLE',
 'PRICE_BASIS_UNVERIFIED':'SCALE_PRICE_BASIS_UNVERIFIED',
 'SCALE_INSUFFICIENT':'SCALE_INSUFFICIENT_BLOCKS','SCALE_ZERO':'SCALE_ZERO'}
PHASES = ('PROGRESSION','CORRECTION','RECOVERY','BALANCE','RESTRUCTURING')
CROSS = ('CLOSE_CROSS_UP','CLOSE_CROSS_DOWN','RECLAIM_UP','RECLAIM_DOWN')

def clean(x: Any) -> Any:
    if isinstance(x, F): return {'numerator':x.numerator,'denominator':x.denominator}
    if isinstance(x, dict): return {k:clean(v) for k,v in sorted(x.items())}
    if isinstance(x, (tuple,list)): return [clean(v) for v in x]
    return x

def encoded(x: Any) -> bytes:
    return (json.dumps(clean(x), sort_keys=True, ensure_ascii=False,
                       separators=(',',':'), allow_nan=False)+'\n').encode('utf-8')

def digest(x: Any) -> str: return hashlib.sha256(encoded(x)).hexdigest()

def ordered_reasons(values):
    values=set(values)
    if not values <= REASONS: raise ValueError('UNKNOWN_REASON:'+repr(values-REASONS))
    return [s for s in PRECEDENCE if s in values] + sorted(values-set(PRECEDENCE))

def axis(status, value=None, reasons=(), **evidence):
    if status not in STATUSES: raise ValueError('ILLEGAL_STATUS')
    codes=ordered_reasons(reasons)
    if status=='DEFINED':
        if value is None or codes: raise ValueError('ILLEGAL_DEFINED_VALUE_OR_REASONS')
    elif value is not None or not codes: raise ValueError('ILLEGAL_NONDEFINED_VALUE_OR_REASONS')
    return {'status':status,'value':value,'reasonCodes':codes,
            'primaryReason':codes[0] if codes else None,'evidence':evidence}

def stamp(day, minute):
    return dt.datetime.combine(dt.date.fromisoformat(day),dt.time(),JST)+dt.timedelta(minutes=minute)

def iso(day, minute): return stamp(day,minute).isoformat()

class PITReader:
    """A per-checkpoint capability. Validate metadata before releasing any prices.

    Only admitted immutable Bar tuples reach a numeric primitive. Each primitive
    invocation registers its own reads. No delayed-known source is silently dropped.
    """
    def __init__(self, day, cutoff):
        self.cutoff=stamp(day,cutoff)
        self.maximum=None
        self.known=None
        self.reads={}
        self.historical=False

    def _check(self, event, known, primitive):
        if event > self.cutoff: raise ValueError('FUTURE_SOURCE_READ:'+primitive)
        if known is not None and known > self.cutoff: raise ValueError('KNOWN_AT_AFTER_CHECKPOINT:'+primitive)
        self.maximum=max(self.maximum,event) if self.maximum else event
        if known is not None: self.known=max(self.known,known) if self.known else known
        else: self.historical=True
        self.reads[primitive]=self.reads.get(primitive,0)+1

    def bars(self, bars, day, primitive):
        bs=tuple(bars)
        for b in bs:
            self._check(stamp(day,b.end),stamp(day,b.available_at) if b.available_at is not None else None,primitive)
        r.validate_bars(bs)
        return bs

    def daily(self, rows, today):
        out=[]
        for z in rows:
            if z['date'] >= today: raise ValueError('FUTURE_DAILY_SOURCE')
            known=z.get('knownAt')
            if known is not None:
                known=dt.datetime.fromisoformat(known)
                if known.utcoffset() is None: raise ValueError('NAIVE_KNOWN_AT')
            self._check(stamp(z['date'],1439),known,'dailyContext')
            out.append(dict(z))
        return out

    def metadata(self):
        return {'maxSourceTimestamp':self.maximum.isoformat() if self.maximum else None,
                'maxKnownAt':self.known.isoformat() if self.known else None,
                'availabilityEvidence':'HISTORICAL_CLOSED_RECONSTRUCTION' if self.historical or not self.reads else 'EXPLICIT_AVAILABLE_AT_CHECKED',
                'primitiveReadCounts':dict(sorted(self.reads.items()))}

def observation(bs, ends, t):
    w=r.window(bs,ends,t)
    found={b.end for b in bs}
    past=[e for e in ends if e<=t]
    groups=r.segments(past,time=lambda x:x)
    sg=groups[-1] if groups else []
    mapping={'CURRENT_BAR_UNAVAILABLE':'OBS_CURRENT_BAR_NOT_OBSERVED',
             'SESSION_BOUNDARY':'OBS_SESSION_BOUNDARY','SHORT_SESSION_HISTORY':'OBS_SHORT_SESSION_HISTORY',
             'MISSING_SCHEDULED_BAR':'OBS_MISSING_SCHEDULED_BAR'}
    codes=[mapping[z] for z in w['reasons']]
    if w['status']!='COMPLETE': codes.append('OBS_LATEST5_INCOMPLETE')
    any_missing=any(e not in found for e in past)
    missing_run=0
    for e in reversed(past):
        if e in found: break
        missing_run+=1
    densities={}
    shorts=[]
    for n in (5,15,30):
        stamps=sg[-n:]
        densities['density'+str(n)]=F(sum(e in found for e in stamps),len(stamps)) if stamps else None
        if len(stamps)<n:shorts.append(n)
    last=max(found) if found else None
    return {'currentBarObserved':t in found and t in past,
      'scheduled5N':len(w['expectedEnds']),'latest5ObservedK':len(w['observedEnds']),
      'latest5Complete':w['status']=='COMPLETE',**densities,
      'densityToday':F(sum(e in found for e in past),len(past)) if past else None,
      'shortHistoryWindows':shorts,
      'lastObservedAgeActiveMinutes':sum(e>last for e in past) if last is not None else None,
      'consecutiveMissingRun':missing_run,'missingFlags':ordered_reasons(codes),
      'missingCauseCodes':['OBS_NOT_OBSERVED_CAUSE_UNKNOWN'] if any_missing else [],
      'evidenceSource':'FROZEN_ADMITTED_1M_SOURCE','window':{k:v for k,v in w.items() if k!='bars'}}

def semantic_axes(mech, scale, observation_quality, tick_size=None):
    st=mech['state']; s=scale.get('scale')
    obs=observation_quality['missingFlags']
    sc=[SCALE_REASON[scale['status']]] if scale['status'] in SCALE_REASON else []
    # Structure/Phase engine prerequisites are inherited from _snapshot, NOT Direction's latest5.
    failed=obs+sc if st['identificationStatus'] in ('CURRENT_BAR_UNAVAILABLE','SCALE_UNAVAILABLE') else []
    ps=st.get('pivots',[]); active=st.get('structure')
    d=mech.get('descriptors')
    direction=axis('DEFINED',d['direction'],return5Pct=d['returnPct']) if d else axis('NOT_EVALUATED',reasons=obs)
    if active: structure=axis('DEFINED',active['kind'],pivotN=len(ps),witness=active)
    elif failed: structure=axis('NOT_EVALUATED',reasons=failed,pivotN=len(ps))
    elif len(ps)<4: structure=axis('INSUFFICIENT',reasons=['PIVOT_INSUFFICIENT_COUNT'],pivotN=len(ps))
    else: structure=axis('DEFINED','NONE',pivotN=len(ps))
    phase=axis('NOT_EVALUATED',reasons=failed) if failed else axis('DEFINED',st.get('phase',[]),leg=st.get('leg'),episode=st.get('episode'),recoveredFraction=st.get('recoveredFraction'))
    hs=[p for p in ps[-4:] if p['kind']=='HIGH'];ls=[p for p in ps[-4:] if p['kind']=='LOW']
    if failed: pivot=axis('NOT_EVALUATED',reasons=failed,pivotN=len(ps))
    elif len(ps)<4: pivot=axis('INSUFFICIENT',reasons=['PIVOT_INSUFFICIENT_COUNT'],pivotN=len(ps))
    else:
        if len(hs)!=2 or len(ls)!=2:raise ValueError('NONALTERNATING_FROZEN_PIVOTS')
        hd=hs[1]['price']-hs[0]['price'];ld=ls[1]['price']-ls[0]['price']
        def rel(d):return 'UP' if d>0 else 'DOWN' if d<0 else 'EQ'
        pivot=axis('DEFINED',{'highRelation':'H_'+rel(hd),'lowRelation':'L_'+rel(ld)},
          highDiffRaw=hd,lowDiffRaw=ld,highDiffScale=hd/s,lowDiffScale=ld/s,
          highDiffTicks=hd/tick_size if tick_size else None,lowDiffTicks=ld/tick_size if tick_size else None,
          pivotN=len(ps),pivotIds=[p['id'] for p in ps[-4:]])
    return {'direction':direction,'structure':structure,'phase':phase,'pivotSignature':pivot}

def attributes(mech, bs, ends, t, scale, obs, reader, day):
    latest=r.window(reader.bars(bs,day,'attributeLatestWindow'),ends,t)
    start=latest['expectedEnds'][0]-1 if latest['expectedEnds'] else t
    prior_bs=tuple(b for b in bs if b.end<=start)
    prior=r.window(reader.bars(prior_bs,day,'attributePriorWindow'),ends,start)
    old=mech['attributes'];out={}
    sr=[SCALE_REASON[scale['status']]] if scale['status'] in SCALE_REASON else []
    reasons=(obs['missingFlags'] if not obs['latest5Complete'] else [])+sr
    out['choppiness']=axis('NOT_EVALUATED',reasons=reasons) if reasons else axis('DEFINED','CHOPPINESS' if 'CHOPPINESS' in old['tags'] else 'NONE')
    for key,name,tag,field,missing in (('width','range','RANGE',None,None),('volume','volume','VOLUME','volume','VOLUME_UNAVAILABLE'),('value','tradingValue','TRADING_VALUE','value','TRADING_VALUE_UNAVAILABLE')):
        reasons=list(obs['missingFlags']) if not obs['latest5Complete'] else []
        comparable=prior['status']=='COMPLETE' and latest['status']=='COMPLETE' and prior['bars'][-1].end+1==latest['bars'][0].end
        if not comparable:reasons.append('PRIOR_WINDOW_NOT_COMPARABLE')
        if field and any(getattr(b,field) is None for b in latest['bars']+prior['bars']):reasons.append(missing)
        if comparable:
            denominator=r.metrics(prior['bars'])[key]
            if denominator==0:reasons.append('ZERO_DENOMINATOR')
        ratio=old.get('ratios',{}).get(key)
        if reasons:out[name]=axis('NOT_EVALUATED',reasons=reasons)
        else:
            if ratio is None:raise ValueError('UNEXPLAINED_ATTRIBUTE_NULL')
            value='EXPANSION' if tag+'_EXPANSION' in old['tags'] else 'COMPRESSION' if tag+'_COMPRESSION' in old['tags'] else 'NONE'
            out[name]=axis('DEFINED',value,ratio=ratio)
    return out

def static_and_vwap_events(bs, ends, t, scale, daily, previous_context, reader, day):
    w=r.window(reader.bars(bs,day,'eventWindow'),ends,t)
    start=w['expectedEnds'][0]-1 if w['expectedEnds'] else t
    before=tuple(b for b in bs if b.end<=start)
    levels={}
    if previous_context:
        levels.update(PREVIOUS_OBSERVED_HIGH=previous_context['observedHigh'],PREVIOUS_OBSERVED_LOW=previous_context['observedLow'])
    if 'D1Levels' in daily:levels.update({'PREVIOUS_DAILY_'+k.upper():v for k,v in daily['D1Levels'].items()})
    if before:levels.update(TODAY_PRIOR_HIGH=max(b.h for b in before),TODAY_PRIOR_LOW=min(b.l for b in before))
    if scale is not None and before and before[-1].end==start:
        baseline=r.snapshot(reader.bars(before,day,'fixedLevelBaseline'),ends,start,scale)['state']
        rg=baseline.get('localRange')
        if rg:levels.update(LOCAL_RANGE_UPPER=rg['upper'],LOCAL_RANGE_LOWER=rg['lower'])
        for kind in ('HIGH','LOW'):
            ps=[p for p in baseline.get('pivots',[]) if p['kind']==kind]
            if ps:levels['STRUCTURAL_SWING_'+kind]=ps[-1]['price']
    event_bs=reader.bars(bs,day,'fixedLevelEvents')
    fixed={name:axis('DEFINED',r.level_events(event_bs,value,name,start,start,t),level=value,levelSetAt=iso(day,start)) for name,value in sorted(levels.items())}
    for name in ('PREVIOUS_OBSERVED_HIGH','PREVIOUS_OBSERVED_LOW','PREVIOUS_DAILY_HIGH','PREVIOUS_DAILY_LOW','PREVIOUS_DAILY_CLOSE','TODAY_PRIOR_HIGH','TODAY_PRIOR_LOW','LOCAL_RANGE_UPPER','LOCAL_RANGE_LOWER','STRUCTURAL_SWING_HIGH','STRUCTURAL_SWING_LOW'):
        if name not in fixed:fixed[name]=axis('NOT_EVALUATED',reasons=['LEVEL_CONTEXT_UNAVAILABLE'])
    events=[e for z in fixed.values() if z['status']=='DEFINED' for e in z['value']]
    crosses=[e for e in events if e['kind'] in CROSS]
    persistence=[]
    for e in crosses:
        c=r.confirmation(e,reader.bars(bs,day,'eventPersistence'),ends,t)
        code={'RIGHT_CENSORED':'PERSISTENCE_RIGHT_CENSORED','SESSION_BOUNDARY':'PERSISTENCE_SESSION_BOUNDARY','OBSERVATION_INSUFFICIENT':'PERSISTENCE_OBSERVATION_INSUFFICIENT'}.get(c['status'])
        persistence.append({'event':e,'result':axis('NOT_EVALUATED',reasons=[code],witness=c) if code else axis('DEFINED',c['status'],witness=c)})
    vw=r.vwap_events(reader.bars(bs,day,'vwapEvents'),ends,start,t)
    code={'PARTIAL_OBSERVATION':'VWAP_PREFIX_INCOMPLETE','ACTIVITY_UNAVAILABLE':'VWAP_ACTIVITY_UNAVAILABLE','ZERO_VOLUME':'VWAP_ZERO_VOLUME'}.get(vw['status'])
    return {'fixedLevel':dict(sorted(fixed.items())),
            'movingVWAP':axis('NOT_EVALUATED',reasons=[code]) if code else axis('DEFINED',vw['events'],vwap=vw.get('vwap')),
            'persistence':axis('DEFINED',persistence) if crosses else axis('NOT_APPLICABLE',reasons=['NO_TRIGGER_EVENT'])}

def validate_axis(z):
    if z['status'] not in STATUSES:raise ValueError('STATUS_ENUM')
    if ordered_reasons(z['reasonCodes'])!=z['reasonCodes']:raise ValueError('REASON_ORDER')
    if z['primaryReason'] != (z['reasonCodes'][0] if z['reasonCodes'] else None):raise ValueError('PRIMARY_REASON')
    if z['status']=='DEFINED':
        if z['value'] is None or z['reasonCodes']:raise ValueError('DEFINED_SCHEMA')
    elif z['value'] is not None or not z['reasonCodes']:raise ValueError('NONDEFINED_SCHEMA')

def validate_tree(x):
    if isinstance(x,dict):
        if {'status','value','reasonCodes','primaryReason'}<=x.keys():validate_axis(x)
        for v in x.values():validate_tree(v)
    elif isinstance(x,(list,tuple)):
        for v in x:validate_tree(v)
