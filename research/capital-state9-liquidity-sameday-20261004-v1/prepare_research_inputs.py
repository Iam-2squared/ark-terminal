"""Recover exact saved causal inputs; outcomes are isolated evaluation columns."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
from capital_contract import candidate_runtime, liquidity_capacity

HERE=Path(__file__).resolve().parent
def digest(b):return hashlib.sha256(b).hexdigest()
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def valid(row):
    s,p=row['state'],row['path']
    return (s['current_semantics_observed'] is True and s['numeric_status']=='ACCEPTED'
            and s['observed_at']==s['as_of'] and p['Primary_or_null'] is not None)
def prefix_features(rows,entry):
    # A row's end is the closed-source known-at assumption, not its raw Open time.
    rows=[r for r in rows if r['bar_end_minute']<=entry['fill_minute']]
    latest=rows[-1] if rows else None
    observed=valid(latest) if latest else False
    primary=latest['path']['Primary_or_null'] if observed else None
    segment=latest['path']['causal_segment_id'] if latest else None
    good=[r for r in rows if valid(r)]
    current=[r for r in good if r['path']['causal_segment_id']==segment]
    seq=[];changes=[];last=None
    for r in current:
        label=r['path']['Primary_or_null']
        if label!=last:
            seq.append(label);changes.append(r['bar_end_minute']);last=label
    age=entry['fill_minute']-changes[-1] if changes else None
    transitions=[sum(t>entry['fill_minute']-w for t in changes[1:]) for w in [5,10,20]]
    gaps=sum(not valid(r) for r in rows)
    resets=sum(rows[i]['path']['causal_segment_id']!=rows[i-1]['path']['causal_segment_id'] for i in range(1,len(rows)))
    return {'primary':primary,'observed':observed,'known_at_minute':latest['bar_end_minute'] if latest else None,
            'observed_at':latest['state']['observed_at'] if latest else None,
            'state_as_of':latest['state']['as_of'] if latest else None,
            'state_age':age if observed else None,'path_last3':'>'.join(seq[-3:]) if seq else '__UNKNOWN_PATH__',
            'dwell':latest['path'].get('dwell_observed_bars') if observed else None,
            'change_age':age,'transition5':transitions[0],'transition10':transitions[1],'transition20':transitions[2],
            'path_length':len(good),'path_duration':good[-1]['bar_end_minute']-good[0]['bar_end_minute'] if good else 0,
            'gap_count':gaps,'reset_count':resets,'carry_only':bool(latest and not observed and latest['state'].get('primary')),
            'source_status':'OBSERVED_CURRENT' if observed else 'DISPLAY_OR_STALE_ONLY' if latest and latest['state'].get('primary') else 'UNAVAILABLE',
            'prefix_hash':digest(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()),'prefix_rows':len(rows)}

def main():
    root=Path(sys.argv[1]);out=root/'svnext_private';out.mkdir(exist_ok=True)
    entries=[e for e in map(json.loads,gzip.open(root/'eod_private/primary/entry.jsonl.gz','rt')) if e['entry_status']=='FIRST_ENTRY']
    exits={r['watch_key']:r for r in map(json.loads,gzip.open(root/'eod_private/primary/exit_v3.jsonl.gz','rt'))}
    with zipfile.ZipFile(out/'daily/private.zip') as dz:
        member=next(n for n in dz.namelist() if n.endswith('.gz'))
        dailybytes=dz.read(member);daily=json.loads(gzip.decompress(dailybytes))
    with zipfile.ZipFile(out/'daily/receipt.zip') as dz:
        rr=json.loads(dz.read(next(n for n in dz.namelist() if n.endswith('.json'))))
    assert digest(dailybytes)==rr['private_sha256']
    base=zipfile.ZipFile(root/'svnext_source/Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip')
    scope=json.loads((HERE/'DAILY_RECOVERY_SCOPE.json').read_text())
    # Required dates include the intentionally un-opened protected/purged date.
    calendar=scope['required_prior_dates']+scope['entry_cohort_dates']
    calendar=sorted(set(calendar));wanted={e['symbol'] for e in entries}
    daily=[d for d in daily if d['Code'] in wanted]
    bysymbol={code:[] for code in wanted}
    for r in daily:bysymbol[r['Code']].append(r)
    capacities={};liquidity_counts=Counter();liquidity_private=[]
    for e in entries:
        prior=[d for d in calendar if d<e['session']][-20:]
        cap=liquidity_capacity(e['session'],prior,bysymbol[e['symbol']])
        capacities[e['watch_key']]=str(cap) if cap is not None else None
        status='KNOWN' if cap is not None else 'INPUT_UNKNOWN'
        liquidity_counts[status]+=1
        liquidity_private.append({'entry_id':e['watch_key'],'prior20_dates':prior,'capacity_jpy':capacities[e['watch_key']],
                                  'source_rows':[r for r in bysymbol[e['symbol']] if r['Date'] in prior],'status':status})
    save(out/'LIQUIDITY_SOURCE_PRIVATE.json',liquidity_private)
    save(out/'CAPACITIES_PRIVATE.json',capacities)
    report={'jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'policy_id':'CAPITAL_SIMPLE_LIQUIDITY_CAP_V1',
            'candidate_N':1600,'coverage':dict(liquidity_counts),'exact_current_symbol_N':len(wanted),
            'exact_filtered_daily_source_rows':len(daily),'recovered_source_dates':rr['source_dates_recovered'],
            'required_source_dates':rr['prior_dates_required'],'unopened_protected_or_purged_dates_N':1,
            'capacity_formula':'1% x median(exact prior20 trading-session Va)','source_sha256':rr['private_sha256'],
            'provider_requests':0,'new_data_acquisition':False,'source_completion_rule':'No missing-day substitute; missing history capacity UNKNOWN.'}
    save(out/'LIQUIDITY_AUDIT.json',report)
    # Recover the immutable State/Path trace pack from the local attachment, not a new State run.
    attachment=root/'project_sources/19-Ark_Terminal_NEW_CHAT_HANDOFF_After_EXITV3_REENTRY_CapitalNext_20261003-5-.zip'
    with zipfile.ZipFile(attachment) as outer:
        path=next(n for n in outer.namelist() if n.endswith('Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip'))
        package=outer.read(path)
    assert digest(package)=='31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89'
    tracezip=zipfile.ZipFile(io.BytesIO(package));manifest=json.loads(tracezip.read('MANIFEST.json'))
    components=manifest['components'];states=[];mismatches=0;canaries=0;asofbad=0
    for e in entries:
        name='FULL_TRACE/'+e['session']+'_'+e['symbol']+'.jsonl.gz';b=tracezip.read(name)
        item=components[name] if isinstance(components,dict) else next(x for x in components if x['path']==name)
        assert digest(b)==item['sha256'],'FROZEN_TRACE_HASH'
        prefix=[]
        with gzip.GzipFile(fileobj=io.BytesIO(b)) as stream:
            for line in stream:
                r=json.loads(line)
                if r['bar_end_minute']>e['fill_minute']:break
                prefix.append(r)
        s=prefix_features(prefix,e)
        # Independent originally saved entry snapshot, never copied to the primary computation.
        original=exits[e['watch_key']]['entry_snapshot']
        mismatches+=s['primary']!=original['primary']
        asofbad+=s['known_at_minute'] is not None and s['known_at_minute']>e['fill_minute']
        future={'bar_end_minute':e['fill_minute']+1,'profit':1e99,'state':{'primary':'FORBIDDEN_FUTURE'},'path':{}}
        assert prefix_features(prefix+[future],e)==s;canaries+=1
        s.update(entry_id=e['watch_key'],session=e['session'],symbol=e['symbol'],entry_timestamp=e['fill_timestamp'])
        states.append(s)
    state_counts=Counter(s['source_status'] for s in states)
    joined={s['entry_id']:s for s in states}
    packed=gzip.compress(('\n'.join(json.dumps(s,sort_keys=True) for s in states)+'\n').encode(),mtime=0)
    (out/'STATE9_ENTRY_ROWS.jsonl.gz').write_bytes(packed)
    state_report={'jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':'PASS' if not (mismatches or asofbad) else 'BLOCKED',
                  'candidates':len(states),'source_status_counts':dict(state_counts),'causal_observed_sessions':len({s['session'] for s in states if s['observed']}),
                  'observed_current_primary_N':sum(s['observed'] for s in states),'independent_snapshot_mismatches':mismatches,
                  'asof_violations':asofbad,'future_suffix_canaries':canaries,'future_suffix_mismatches':0,
                  'trace_package_sha256':digest(package),'join_rows_sha256':digest(packed),
                  'freshness_rule':'current_semantics_observed && ACCEPTED && observed_at==as_of && Primary_or_null!=null',
                  'P1_metadata_raw_primary_is_not_fresh_current_certificate':'98 stale/non-current raw labels are not substituted for fresh currentState; use original EXIT lineage FULL_TRACE valid guard.',
                  'actual_arrival':'UNKNOWN; same closed-bar historical research assumption, not live certification'}
    save(out/'STATE9_JOIN_AUDIT.json',state_report)
    assert mismatches==0 and asofbad==0,'C4_ASOF_JOIN_BLOCKED'
    # Frozen P0 numeric context comes from the original saved feature rows, not a new model or feature computation.
    prefix='ark-terminal/research/persistent-watchlist-uptrend-first-entry-20261003-v2/'
    contract=json.load(open(root/'eod_cache/frozen/research/persistent-watchlist-uptrend-first-entry-20261003-v2/CORRECTED_LINEAGE_FAST_FREEZE_20261003/P1_Q70_ENTRY_CONTRACT.json'))
    p0_names=contract['feature_manifest']['P0_numeric']
    with base.open(prefix+'PRIVATE_INPUTS/features_numeric.npy') as f:matrix=np.load(f)
    indices=np.array([e['first_intent']['row_index'] for e in entries],dtype=int)
    A=matrix[indices,:len(p0_names)].copy();del matrix
    A=np.column_stack([A,np.array([e['first_intent']['score'] for e in entries])])
    B=np.column_stack([A,[[float(joined[e['watch_key']]['observed']),joined[e['watch_key']]['state_age'] if joined[e['watch_key']]['state_age'] is not None else np.nan] for e in entries]])
    path_keys=['dwell','change_age','transition5','transition10','transition20','path_length','path_duration','gap_count','reset_count']
    C=np.column_stack([B,[[joined[e['watch_key']][k] if joined[e['watch_key']][k] is not None else np.nan for k in path_keys] for e in entries]])
    catsB=np.array([[joined[e['watch_key']]['primary'] or '__UNKNOWN_CURRENT__'] for e in entries],dtype=str)
    catsC=np.column_stack([catsB,np.array([joined[e['watch_key']]['path_last3'] for e in entries],dtype=str)])
    targets=[]
    for e in entries:
        v=exits[e['watch_key']];hit=e['first_upside']['5']
        win=1 if hit['minute'] is not None else 0 if e['remaining_source_complete'] else np.nan
        mae=e['pre_peak_mae_abs_pct'];mae=np.nan if mae is None else mae
        ret=100*(float(v['sell_price_decimal'])/e['fill_price']-1) if v['sell_status']=='FILLED' else np.nan
        hold=max(0,min(v['sell_minute'],925)-max(e['fill_minute'],750))+max(0,min(v['sell_minute'],690)-max(e['fill_minute'],540)) if v['sell_status']=='FILLED' else np.nan
        targets.append([win,mae,ret,hold])
    np.savez_compressed(out/'CAUSAL_DIAGNOSTIC_PRIVATE.npz',A=A,B=B,C=C,catsB=catsB,catsC=catsC,Y=np.array(targets,dtype=float),
                        sessions=np.array([e['session'] for e in entries]),eligible=np.array([e['fill_minute']<920 for e in entries]))
    save(out/'FEATURE_SOURCE_AUDIT.json',{'causal_P0_fields':len(p0_names),'entry_score_not_probability':True,'frozen_numeric_source_sha256':digest(base.read(prefix+'PRIVATE_INPUTS/features_numeric.npy')),
                                       'source_row_identity':'Frozen first_intent row_id/index unchanged,1600 prior matched','outcomes_are_separate_Y':True,'State_current_join_source':'Frozen v2/v3 FULL_TRACE prefix, fresh guard; NOT P1 raw formal labels',
                                       'teacher_complete_N':np.isfinite(np.array(targets,dtype=float)).sum(axis=0).tolist()})
    print(json.dumps({'liquidity':report,'state9':state_report,'teacher_N':np.isfinite(np.array(targets,dtype=float)).sum(axis=0).tolist()}))

if __name__=='__main__':main()
