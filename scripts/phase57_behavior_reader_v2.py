"""Causal shared research Behavior Reader. No Entry/EXIT or execution decisions."""
import datetime as dt
import hashlib
import json
import math
import statistics
from scripts import phase57_research_dictionary_v0 as v

VERSION = 'CAUSAL_BEHAVIOR_READER_V2'
PULLBACK_ID = 'long_pullback_depth_contiguous_v1'

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def timestamp(value):
    x = dt.datetime.fromisoformat(value)
    if x.tzinfo is None:
        raise ValueError('TIMEZONE_REQUIRED')
    return x

def history_adapter(history, day):
    out = []
    for row in history:
        r = dict(row)
        session = r.get('session', (r.get('daily') or {}).get('Date'))
        if not isinstance(session, str):
            raise ValueError('HISTORY_SESSION_REQUIRED')
        dt.date.fromisoformat(session)
        if session >= day or out and session <= out[-1]['session']:
            raise ValueError('HISTORY_DATE_ORDER_OR_FUTURE')
        if r.get('daily') and r['daily']['Date'] != session:
            raise ValueError('HISTORY_DATE_MISMATCH')
        if 'barValue' in r and 'barValues' in r:
            raise ValueError('AMBIGUOUS_HISTORY_SCHEMA')
        values = r.pop('barValue', r.get('barValues', {}))
        canonical = {}
        for k, value in values.items():
            if str(int(k)) != str(k) or int(k) in canonical or not v.num(value) or value < 0:
                raise ValueError('INVALID_HISTORY_BAR_VALUE')
            canonical[int(k)] = value
        r.update(session=session, barValues=canonical)
        if 'barVolumes' in r:
            if any(not v.num(x) or x<0 for x in r['barVolumes'].values()):
                raise ValueError('INVALID_HISTORY_BAR_VOLUME')
            r['barVolumes']={int(k):x for k,x in r['barVolumes'].items()}
        out.append(r)
    return out

def segments(bars):
    groups = []
    for b in bars:
        if not groups or b['t'] - groups[-1][-1]['t'] != 5 or not v.same_phase(b['t'], groups[-1][-1]['t']):
            groups.append([])
        groups[-1].append(b)
    return groups

def pullback_events(bars, unit):
    events = []
    for segment, group in enumerate(segments(bars)):
        sw = v.swings(group, unit)
        for up, down in zip(sw, sw[1:]):
            if up['direction'] == 1 and down['direction'] == -1 and up['amplitude'] > 0:
                events.append({'trait_id': PULLBACK_ID, 'segment': segment,
                               'value': down['amplitude'] / up['amplitude'],
                               'peakAt': up['extremeAt'], 'troughAt': down['extremeAt'],
                               'availableAt': down['confirmedAt'], 'confirmedLag': down['lag'],
                               'scaleUnit': unit, 'impulseAmplitude': up['amplitude'],
                               'correctionAmplitude': down['amplitude']})
    return events

def validate_snapshot(snapshot, decision_time):
    t = timestamp(decision_time)
    at = timestamp(snapshot['asOf'])
    if not at < t or not snapshot.get('researchOnly'):
        raise ValueError('SNAPSHOT_ASOF_OR_NAMESPACE')
    for row in snapshot['traits']:
        if timestamp(row['computedThrough']) != at:
            raise ValueError('MIXED_ASOF')
        for key in ['peerArtifactThrough', 'normalizationThrough', 'referenceScaleThrough']:
            if timestamp(row[key]) != at:
                raise ValueError('MIXED_ARTIFACT_ASOF')
        if row['symbol'] != snapshot['symbol'] or not row.get('definitionHash'):
            raise ValueError('IDENTITY_OR_DEFINITION')
    return True

def dispatch(snapshot, decision_time):
    validate_snapshot(snapshot, decision_time)
    return [r for r in snapshot['traits']
            if r['globalStatus'] == 'USABLE' and r['sampleConfidence'] in ['HIGH', 'MEDIUM']
            and r['temporalReliability']['status'] == 'PASS' and r['drift'] is not True
            and r['identityStatus'] == 'DATED_MASTER_CODE_RESEARCH_ONLY']

def context(day, asof, minute_rows, previous, history, calendar, personality=None):
    out = {'schema': VERSION, 'session': day, 'asOfMinute': asof,
           'status': 'UNAVAILABLE', 'missingReason': None, 'features': {},
           'featureMissing': {}, 'events': [], 'researchOnly': True,
           'evidenceClass': 'HISTORICAL_RECONSTRUCTION_NOT_PIT', 'productionAllowed': False}
    def unavailable(reason):
        out['missingReason'] = reason
        return out
    close = 900 if day < '2024-11-05' else 925
    if not isinstance(asof, int) or not (545 <= asof <= 690 or 755 <= asof <= close):
        return unavailable('OUTSIDE_CONTINUOUS_PHASE')
    expected = asof // 5 * 5
    hist = history_adapter(history, day)
    if calendar != sorted(set(calendar)) or day not in calendar:
        return unavailable('INVALID_CALENDAR')
    di = calendar.index(day)
    if di == 0 or not v.valid(previous) or previous.get('Date') != calendar[di-1]:
        return unavailable('EXACT_PREVIOUS_EXCHANGE_SESSION_REQUIRED')
    if v.action(previous):
        return unavailable('PREVIOUS_CORPORATE_ACTION')
    if not hist or hist[-1]['session'] != calendar[di-1]:
        return unavailable('HISTORY_NOT_CURRENT')
    if any(r.get('daily') and v.action(r['daily']) for r in hist[-10:]):
        return unavailable('HISTORY_CORPORATE_ACTION')
    s = v.scale(hist)
    if not s:
        return unavailable('PRIOR_SCALE_UNAVAILABLE')
    times = []
    for row in minute_rows:
        if row.get('Date') != day or not v.valid(row):
            raise ValueError('INVALID_BAR_DATE_OR_OHLC')
        t = v.minute_time(row)
        parts=str(row['Time']).split(':')
        if len(parts) not in [2,3] or len(parts)==3 and parts[2]!='00':
            raise ValueError('MINUTE_TIMESTAMP_PRECISION')
        if t >= asof:
            raise ValueError('FUTURE_OR_UNCLOSED_MINUTE')
        if not (540 <= t < 690 or 750 <= t < close):
            raise ValueError('BAR_OUTSIDE_CONTINUOUS_PHASE')
        if times and t <= times[-1]:
            raise ValueError('DUPLICATE_OR_UNSORTED_BAR')
        times.append(t)
    if len({r.get('Code') for r in minute_rows}) > 1:
        raise ValueError('MIXED_SECURITY')
    if minute_rows and previous.get('Code') != minute_rows[0].get('Code'):
        raise ValueError('PREVIOUS_SECURITY_MISMATCH')
    bars = v.bars5(day, minute_rows)
    if not bars or bars[-1]['t'] != expected:
        return unavailable('MISSING_CURRENT_BAR')
    if not 0 <= asof - bars[-1]['t'] <= 4:
        return unavailable('STALE_BAR')
    if personality is not None:
        now = day + 'T%02d:%02d:00+09:00' % divmod(asof, 60)
        validate_snapshot(personality, now)
        if timestamp(personality['asOf']).date().isoformat() != calendar[di-1]:
            return unavailable('STALE_DICTIONARY_SESSION')
        if minute_rows and personality['symbol'] != minute_rows[0].get('Code'):
            raise ValueError('DICTIONARY_SECURITY_MISMATCH')
        out['personality'] = dispatch(personality, now)
    unit = previous['C'] * s
    last = bars[-1]
    c = last['C']
    f = out['features']
    f.update(body_s=(c-last['O'])/unit,
             upper_wick_s=(last['H']-max(c,last['O']))/unit,
             lower_wick_s=(min(c,last['O'])-last['L'])/unit,
             range_s=(last['H']-last['L'])/unit,
             pdh=previous['H'], pdl=previous['L'],
             close_pdh_s=(c-previous['H'])/unit, close_pdl_s=(c-previous['L'])/unit)
    # VWAP is session cumulative, never a partial-data approximation called full VWAP.
    required = list(range(540, min(expected,690)))
    if expected > 750:
        required += list(range(750, expected))
    complete_prefix = set(required).issubset(times)
    f['cumulative_vwap'] = last['VWAP'] if complete_prefix else None
    f['close_vwap_s'] = (c-last['VWAP'])/unit if complete_prefix and last['VWAP'] else None
    if f['close_vwap_s'] is None:
        out['featureMissing']['cumulative_vwap'] = 'MISSING_PREFIX_OR_ZERO_VOLUME'
    group = segments(bars)[-1]
    recent = group[-6:]
    prior_ranges = [b['H']-b['L'] for b in recent[:-1]]
    ratio = (last['H']-last['L'])/statistics.mean(prior_ranges) if len(prior_ranges)>=2 and statistics.mean(prior_ranges)>0 else None
    f.update(compression_ratio=ratio, expansion_ratio=ratio)
    if ratio is None:
        out['featureMissing']['compression_ratio'] = 'INSUFFICIENT_CONTIGUOUS_BARS'
    out['confirmedSwings'] = v.swings(group, unit)
    out['pullbacks'] = pullback_events(group, unit)
    f['pullback_depth_vnext'] = out['pullbacks'][-1]['value'] if out['pullbacks'] else None
    if not out['pullbacks']:
        out['featureMissing']['pullback_depth_vnext'] = 'NO_CONFIRMED_UP_DOWN_PAIR'
    orb = [b for b in bars if 545 <= b['t'] <= 570]
    levels = {'PDH': previous['H'], 'PDL': previous['L']}
    if [b['t'] for b in orb] == list(range(545,571,5)):
        levels.update(ORH=max(b['H'] for b in orb), ORL=min(b['L'] for b in orb))
    else:
        out['featureMissing']['opening_range'] = 'NOT_COMPLETE_OR_MISSING'
    f['opening_range_high'] = levels.get('ORH')
    f['opening_range_low'] = levels.get('ORL')
    for name, level in levels.items():
        eligible = [b for b in group if not name.startswith('OR') or b['t'] >= 570]
        for sign, label in [(1,'BREAKOUT'),(-1,'BREAKDOWN')]:
            # Transition, not simply already being on one side of a level.
            for left, right in zip(eligible, eligible[1:]):
                if sign*(left['C']-level) <= .25*unit < sign*(right['C']-level):
                    out['events'].append({'type': name+'_'+label, 'availableAt': right['t']})
                    back = next((b for b in eligible if right['t'] < b['t'] <= right['t']+30 and sign*(b['C']-level) < -.25*unit),None)
                    if back:
                        out['events'].append({'type': name+('_FAILURE' if sign==1 else '_RECLAIM'), 'availableAt':back['t']})
    if complete_prefix:
        for a,b in zip(group,group[1:]):
            if a['VWAP'] and b['VWAP']:
                for sign,name in [(1,'VWAP_RECLAIM'),(-1,'VWAP_LOSS')]:
                    if sign*(a['C']-a['VWAP']) < -.25*unit and sign*(b['C']-b['VWAP']) > .25*unit:
                        out['events'].append({'type':name,'availableAt':b['t']})
    prior_values = [r['barValues'].get(last['t']) for r in hist[-10:]]
    prior_values = [x for x in prior_values if v.num(x) and x>0]
    f['rvol_trading_value'] = last['Va']/statistics.median(prior_values) if len(prior_values)>=5 else None
    f['trading_value_shock'] = f['rvol_trading_value']>=2 if f['rvol_trading_value'] is not None else None
    if f['rvol_trading_value'] is None:
        out['featureMissing']['rvol_trading_value'] = 'INSUFFICIENT_SAME_TIME_HISTORY'
    volume_values=[r.get('barVolumes',{}).get(last['t']) for r in hist[-10:]]
    volume_values=[x for x in volume_values if v.num(x) and x>0]
    f['rvol_volume']=last['Vo']/statistics.median(volume_values) if len(volume_values)>=5 else None
    if f['rvol_volume'] is None:
        out['featureMissing']['rvol_volume']='INSUFFICIENT_SAME_TIME_HISTORY'
    out.update(status='RESEARCH_CONTEXT_AVAILABLE', missingReason=None,
               lastCompletedBar=last['t'], scaleS=s, expectedEnd=expected,
               stalenessMinutes=asof-last['t'], units={'*_s':'priorClose * prior S','prices':'JPY','RVOL':'ratio'})
    return out
