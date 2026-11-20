"""Explicit causal projection; labels, execution suffix and identity never enter X."""
from decimal import Decimal
import hashlib
import json

NUMERIC = [
    'entry/p1_score','entry/p1_threshold','entry/intent_clock','entry/fill_clock',
    'entry/intent_to_fill_active_delay','selector/first_clock',
    'selector/to_intent_active_delay','selector/to_entry_active_delay',
    'selector/raw_entry_vs_first_price_pct',
    'state/observed','state/context_direction','state/local_direction',
    'state/fast_applicable','state/stop_count',
    'path/dwell_observed_bars','path/dwell_scheduled_bars',
    'path/transitions_total','path/segment_breaks_total','path/observation_losses_total',
    'path/observed_prefix_rows','path/last_transition_age_minutes',
    'path/transitions_15m','path/transitions_30m','path/transitions_60m',
    'path/observed_rows_15m','path/observed_rows_30m','path/observed_rows_60m',
]
CATEGORICAL = [
    'state/current_primary','state/activity','state/basis','state/direction_basis',
    'state/fast','state/numeric_status','path/last3_connected_primary',
]
UNKNOWN='__UNKNOWN__'

def fresh(r):
    s,p=r['state'],r['path']
    return (s['current_semantics_observed'] is True and s['numeric_status']=='ACCEPTED'
            and s['observed_at']==s['as_of'] and p['Primary_or_null'] is not None)

def project(entry, trace):
    # Slice at the closed-bar availability boundary BEFORE reading nested fields.
    t=entry['fill_minute']
    prefix=[r for r in trace if r['bar_end_minute']<=t]
    if prefix:
        assert all(prefix[i]['bar_end_minute']<prefix[i+1]['bar_end_minute'] for i in range(len(prefix)-1))
    latest=prefix[-1] if prefix else None
    observed=bool(latest and fresh(latest))
    s=latest['state'] if latest else {}
    p=latest['path'] if latest else {}
    intent=entry['first_intent']
    raw=Decimal(str(entry['fill_price']))/Decimal('1.0005')
    sp=entry.get('selector_price')
    numeric={
        'entry/p1_score':intent.get('score'),'entry/p1_threshold':intent.get('threshold'),
        'entry/intent_clock':intent.get('intent_minute'),'entry/fill_clock':t,
        'entry/intent_to_fill_active_delay':entry.get('intent_to_fill_active_delay'),
        'selector/first_clock':entry.get('selector_minute'),
        'selector/to_intent_active_delay':entry.get('selector_to_intent_active_delay'),
        'selector/to_entry_active_delay':entry.get('selector_to_entry_active_delay'),
        'selector/raw_entry_vs_first_price_pct':float((raw/Decimal(str(sp))-1)*100) if sp else None,
        'state/observed':int(observed),
        'state/context_direction':p.get('context_direction') if observed else None,
        'state/local_direction':p.get('local_direction') if observed else None,
        'state/fast_applicable':int(p.get('fast_applicable_to_primary',False)) if observed else None,
        'state/stop_count':(s.get('stop') or {}).get('count') if observed else None,
        'path/dwell_observed_bars':p.get('dwell_observed_bars') if observed else None,
        'path/dwell_scheduled_bars':p.get('dwell_scheduled_bars') if observed else None,
    }
    events=[ev for r in prefix for ev in r.get('path_events',[])]
    transitions=[r['bar_end_minute'] for r in prefix for ev in r.get('path_events',[]) if ev['event_type']=='TRANSITION']
    numeric.update({
        'path/transitions_total':len(transitions),
        'path/segment_breaks_total':sum(ev['event_type']=='SEGMENT_BREAK' for ev in events),
        'path/observation_losses_total':sum(ev['event_type']=='OBSERVATION_LOST' for ev in events),
        'path/observed_prefix_rows':sum(fresh(r) for r in prefix),
        'path/last_transition_age_minutes':t-transitions[-1] if transitions else None,
    })
    for w in (15,30,60):
        numeric[f'path/transitions_{w}m']=sum(t-w<m<=t for m in transitions)
        numeric[f'path/observed_rows_{w}m']=sum(t-w<r['bar_end_minute']<=t and fresh(r) for r in prefix)
    # Last3 uses only the currently connected observation episode. A→null→B is
    # never compressed into A→B, including within the same accepted segment.
    connected=[]
    if observed:
        for r in reversed(prefix):
            if not fresh(r):break
            if connected:
                later=connected[-1]
                if (r['path']['causal_segment_id']!=later['path']['causal_segment_id']
                    or r['path']['scheduled_t']+1!=later['path']['scheduled_t']):break
            connected.append(r)
        connected.reverse()
    sequence=[]
    for r in connected:
        v=r['path']['Primary_or_null']
        if not sequence or sequence[-1]!=v:sequence.append(v)
    categorical={
        'state/current_primary':p.get('Primary_or_null') if observed else UNKNOWN,
        'state/activity':s.get('activity',UNKNOWN),
        'state/basis':s.get('basis',UNKNOWN),
        'state/direction_basis':s.get('direction_basis',UNKNOWN) if observed else UNKNOWN,
        'state/fast':str(p.get('fast')) if observed and p.get('fast') is not None else UNKNOWN,
        'state/numeric_status':s.get('numeric_status',UNKNOWN),
        'path/last3_connected_primary':'>'.join(sequence[-3:]) if sequence else UNKNOWN,
    }
    assert set(numeric)==set(NUMERIC) and list(categorical)==CATEGORICAL
    numeric={k:numeric[k] for k in NUMERIC}
    return {'numeric':numeric,'categorical':categorical,
            'provenance':{'max_known_minute':prefix[-1]['bar_end_minute'] if prefix else None,
                          'prefix_rows':len(prefix),'historical_actual_arrival':'UNKNOWN',
                          'prefix_sha256':hashlib.sha256(json.dumps(prefix,sort_keys=True,separators=(',',':')).encode()).hexdigest()}}
