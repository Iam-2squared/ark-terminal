"""v3 input-only: frozen-normalization 32-slot paths and known-selector peers.

No outcomes, models, threshold selection, or State semantic changes. Missing
scheduled rows remain missing. All current market suffixes are clock-filtered
before market values are inspected or sent to worker processes.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import concurrent.futures
from datetime import datetime,timedelta,timezone
from decimal import Decimal,Context,localcontext,ROUND_HALF_EVEN
import gzip,hashlib,json,math
from pathlib import Path
import sys
import numpy as np
sys.dont_write_bytecode=True
V2=Path(__file__).resolve().parent.parent/'sign-prebuy-quality-precision80-20261006-v2'
sys.path.insert(0,str(V2))
import intent_feature_replay as replay
from study_input_adapter import check_global_receipt

SLOTS=32
TRAJECTORY_FIELDS=tuple(f'trajectory/lag{lag:02d}/{field}' for lag in range(32,0,-1)
                       for field in ('open_u','high_u','low_u','close_u','log_volume','log_value','bar_present','half_slot_eligible'))
CONTEXT_FIELDS=('peer/known_count','peer/fresh_count','peer/fresh_fraction','peer/fresh_age_median',
    *(f'peer/return{n}/{field}' for n in (5,10) for field in ('valid_count','valid_fraction','positive_fraction','median','q25','q75')))
JST=timezone(timedelta(hours=9))
_KERNEL=None


def initialize():
    global _KERNEL
    replay.initialize();_KERNEL=replay._KERNEL


def phase_bounds(day,intent):
    return (540,690) if intent<=690 else (750,900 if day<'2024-11-05' else 925)


def accepted_prefix(rows,day,intent):
    prefix=replay.raw_before_intent(rows,intent)
    out=[];previous_start=None
    regular=set(range(540,690))|set(range(750,900 if day<'2024-11-05' else 925))
    for row in prefix:
        start=int(row[0])
        if previous_start is not None and start<=previous_start:raise ValueError('RAW_CLOCK_ORDER')
        previous_start=start
        if start not in regular:continue
        if not _KERNEL.valid_bar(row):raise ValueError('INVALID_PREFIX_OHLCV_VALUE')
        out.append(row)
    return out


def trajectory(rows,day,intent,previous,source_connected):
    if _KERNEL is None:initialize()
    prefix=accepted_prefix(rows,day,intent);lo,hi=phase_bounds(day,intent)
    if not prefix or prefix[-1][0]+1!=intent:raise ValueError('FINAL_CLOSED_INTENT_BAR_MISSING')
    bytime={int(row[0]):row for row in prefix};out={};cache={};checks=0
    if source_connected:
        b80=_KERNEL.normalize80.generate(previous,[]);b120=_KERNEL.normalize120.regenerate(previous,[])
        if b80['U']!=b120['U'] or b80['P_ref']!=b120['P_ref']:raise ValueError('NORMALIZATION_BASE_PARITY')
        def coordinate(value):
            nonlocal checks
            lex=json.dumps(value,allow_nan=False)
            if lex not in cache:
                coords=[]
                for precision,base in ((80,b80),(120,b120)):
                    ctx=_KERNEL.normalize80.context() if precision==80 else Context(prec=120,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999)
                    with localcontext(ctx):coords.append(((Decimal(lex).ln()-Decimal(base['P_ref']).ln())/Decimal(base['U'])).quantize(Decimal('1e-24')))
                if coords[0]!=coords[1]:raise ValueError('NORMALIZATION_COORDINATE_PARITY')
                cache[lex]=coords[0];checks+=1
            return cache[lex]
        center=coordinate(prefix[-1][4])
    else:center=None
    present=0;eligible_count=0
    first_am=min((int(row[0]) for row in prefix if row[0]<690),default=None)
    first_pm=min((int(row[0]) for row in prefix if row[0]>=750),default=None)
    mixed_in_window=0
    for lag in range(SLOTS,0,-1):
        start=intent-lag;eligible=lo<=start<hi;row=bytime.get(start) if eligible else None
        token=f'trajectory/lag{lag:02d}/';eligible_count+=eligible;present+=row is not None
        if row is not None and start in (first_am,first_pm):mixed_in_window+=1
        for field,index in (('open_u',1),('high_u',2),('low_u',3),('close_u',4)):
            if row is not None and center is not None:
                with localcontext(_KERNEL.normalize80.context()):value=float(coordinate(row[index])-center)
            else:value=None
            out[token+field]=value
        for field,index in (('log_volume',5),('log_value',6)):
            out[token+field]=math.log1p(row[index]) if row is not None else None
        out[token+'bar_present']=int(row is not None);out[token+'half_slot_eligible']=int(eligible)
    assert tuple(out)==TRAJECTORY_FIELDS
    return out,{'normalization_price_checks':checks,'slot_denominator':SLOTS,'same_half_eligible_slots':eligible_count,
                'observed_slots':present,'opening_mixed_slots_included':mixed_in_window,'source_connected':source_connected}


def known_peers(events,day,intent,target_symbol):
    decision=datetime.fromisoformat(day).replace(tzinfo=JST)+timedelta(minutes=intent)
    peers=set()
    for event in events:
        if event['sessionDate']!=day:continue
        ts=datetime.fromisoformat(event['decisionTimestamp']);available=datetime.fromisoformat(event['decisionPriceAvailableAtJst'])
        if ts.utcoffset() is None or available.utcoffset() is None:raise ValueError('SELECTOR_NAIVE_TIMESTAMP')
        # Exclude before consulting symbol or any Selector price/score fields.
        if ts>decision or available>decision:continue
        symbol=event['symbol']
        if symbol!=target_symbol:peers.add(symbol)
    return sorted(peers)


def peer_values(rows,day,intent):
    if _KERNEL is None:initialize()
    prefix=accepted_prefix(rows,day,intent);lo,hi=phase_bounds(day,intent)
    same=[r for r in prefix if lo<=r[0]<hi]
    if not same:return {'fresh':False,'age':None,'returns':{5:None,10:None}}
    latest=same[-1];age=intent-int(latest[0])-1
    first_am=min((int(row[0]) for row in prefix if row[0]<690),default=None)
    first_pm=min((int(row[0]) for row in prefix if row[0]>=750),default=None)
    fresh=0<=age<=5 and int(latest[0]) not in (first_am,first_pm)
    returns={5:None,10:None}
    if fresh:
        a=np.asarray(prefix,np.float64).reshape(-1,7)
        for n in (5,10):
            # Same frozen P0 close-lag definition; do not fill a missing minute.
            window=_KERNEL.window(a,intent,n+1)
            if window is not None:returns[n]=float(_KERNEL.pct(a[-1,4],window[0,4]))
    return {'fresh':fresh,'age':age if fresh else None,'returns':returns}


def context(peers_raw,day,intent):
    values=[peer_values(rows,day,intent) for rows in peers_raw]
    n=len(values);fresh=[v for v in values if v['fresh']]
    out={'peer/known_count':n,'peer/fresh_count':len(fresh),'peer/fresh_fraction':len(fresh)/n if n else 0.,
         'peer/fresh_age_median':float(np.median([v['age'] for v in fresh])) if fresh else None}
    valid_counts={}
    for horizon in (5,10):
        ret=[v['returns'][horizon] for v in values if v['returns'][horizon] is not None];k=len(ret);valid_counts[str(horizon)]=k
        out.update({f'peer/return{horizon}/valid_count':k,f'peer/return{horizon}/valid_fraction':k/n if n else 0.,
                    f'peer/return{horizon}/positive_fraction':sum(r>0 for r in ret)/k if k else None,
                    f'peer/return{horizon}/median':float(np.median(ret)) if k else None,
                    f'peer/return{horizon}/q25':float(np.quantile(ret,.25,method='linear')) if k else None,
                    f'peer/return{horizon}/q75':float(np.quantile(ret,.75,method='linear')) if k else None})
    assert tuple(out)==CONTEXT_FIELDS
    return out,{'known_peer_count':n,'fresh_peer_count':len(fresh),'valid_peer_counts':valid_counts}


def build_one(job):
    index,base,base_schema,target_raw,previous,source_connected,peers_raw=job
    if _KERNEL is None:initialize()
    day=base['session'];intent=base['intent_minute']
    target,ta=trajectory(target_raw,day,intent,previous,source_connected)
    peer,pa=context(peers_raw,day,intent)
    numeric={k:base['numeric'][k] for k in base_schema['numeric']};numeric.update(target);numeric.update(peer)
    categorical={k:base['categorical'][k] for k in base_schema['categorical']}
    out={k:base[k] for k in ('entry_id','session','intent_minute','supported','input_asof')}
    out.update(numeric=numeric,categorical=categorical)
    if any(v is not None and (type(v) not in (int,float) or not math.isfinite(v)) for v in numeric.values()):raise ValueError('INVALID_OUTPUT_NUMBER')
    return out,{'trajectory':ta,'context':pa}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--global-receipt',type=Path,required=True)
    parser.add_argument('--global-receipt-sha256',required=True)
    parser.add_argument('--limit',type=int,default=0)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('OUTPUT_EXISTS_NO_OVERWRITE')
    if not 1<=args.workers<=4:raise ValueError('WORKERS_LIMIT_FOUR')
    gate=check_global_receipt(args.global_receipt,args.global_receipt_sha256);initialize()
    root=Path('/workspace/private-recovery');raw_root=replay.ROOT_PRIVATE/'recovered-persistent'
    fp=root/'sign-v2-inputs/study_features.jsonl.gz';sp=root/'sign-v2-inputs/feature_schema.json'
    with gzip.open(fp,'rt') as f:base=[json.loads(line) for line in f]
    full_path=root/'sign-v2-inputs/features.jsonl.gz'
    schema0=replay.read(sp)['BASE']
    raw_path=raw_root/'raw_paths_selected.json.gz';event_path=raw_root/'selector_events_full144.json.gz'
    native_path=replay.ROOT_PRIVATE/'recovered-state9/ENTRY1600_PREVIOUS_BASIS.json.gz'
    expected={raw_path:'28a7d3faadda1e677a45cf6c7290bb99e4986c3e026da6746a9f3c04883a9c86',
              event_path:'1c8fabdd930ee21d55c064d779721f6854e0bb2db9abc5d94c3d991950bb82cb',
              native_path:'7403265d12af5758bce3075a2c8f4ac3dfdb42aa858caeb2b84e4eee01f8a0e4',
              fp:'bf3b77b48c18d218ae9c3d77f5f7c11991359ce6a332de000c950df2c496d52e',
              full_path:'f56672a67031d2560d1bfbc6b81827e8ff973bfbc67d22192db2300ec4ec663b',
              sp:'a5a3c1f492e617b8f73cf43abd94489bc952557ee497ddc35e238b66f1b05838'}
    for path,digest in expected.items():
        if replay.digest(path)!=digest:raise ValueError('SOURCE_HASH_BINDING')
    full=replay.rows(full_path);full_map={r['entry_id']:r for r in full}
    assert len(base)==1600 and len(full_map)==1600
    raw=replay.read(raw_path);events=replay.read(event_path);native=replay.read(native_path)
    byday=defaultdict(list)
    for event in events:byday[event['sessionDate']].append(event)
    if args.limit:base=base[:args.limit]
    jobs=[];member_counts=[]
    for i,row in enumerate(base):
        day=row['session'];intent=row['intent_minute'];key=row['entry_id'];symbol=key.split('|',1)[1]
        members=known_peers(byday[day],day,intent,symbol);member_counts.append(len(members))
        # Every process gets only selected known identities and past bar values.
        peers=[replay.raw_before_intent(raw[day+'|'+peer]['today'],intent) for peer in members]
        target=replay.raw_before_intent(raw[key]['today'],intent)
        source_connected=full_map[key]['source_status']=='SAVED_SOURCE_CONNECTED'
        jobs.append((i,row,schema0,target,native[key]['previous'],source_connected,peers))
    args.output.mkdir(parents=True)
    output=[];quality=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers,initializer=initialize) as pool:
        for i,(row,audit) in enumerate(pool.map(build_one,jobs,chunksize=1),1):
            output.append(row);quality.append(audit)
            if i%100==0:print(json.dumps({'built_entry_count':i,'total':len(jobs),'model_fits':0}),flush=True)
    base_num=list(schema0['numeric']);cats=list(schema0['categorical']);tcols=list(TRAJECTORY_FIELDS);pcols=list(CONTEXT_FIELDS)
    schema={'TRAJECTORY':{'numeric':base_num+tcols,'categorical':cats},'TRAJECTORY_CONTEXT':{'numeric':base_num+tcols+pcols,'categorical':cats},
            'fit_allowed':False,'slots':32,'state_semantics_changed':False,'profile_changed':False,
            'price_basis':'Original frozen U coordinates centered on last closed C, 80/120 equality required',
            'missing_scheduled_rows_imputed':False,'historical_actual_received_at':'UNKNOWN','global_metadata_gate':gate}
    audit={'status':'V3_INPUTS_BUILT_FEATURES_ONLY_NOT_FIT_ALLOWED','entry_count':len(output),
           'supported_entry_count':sum(r['supported'] for r in output),'source_connected_entries':sum(q['trajectory']['source_connected'] for q in quality),
           'source_unavailable_price_null_entries':sum(not q['trajectory']['source_connected'] for q in quality),
           'trajectory_slot_denominator':len(output)*32,'same_half_eligible_slots':sum(q['trajectory']['same_half_eligible_slots'] for q in quality),
           'trajectory_observed_slots':sum(q['trajectory']['observed_slots'] for q in quality),
           'trajectory_opening_mixed_slots_included':sum(q['trajectory']['opening_mixed_slots_included'] for q in quality),
           'normalization80_120_unique_price_checks':sum(q['trajectory']['normalization_price_checks'] for q in quality),
           'known_peer_count_min':min(member_counts),'known_peer_count_max':max(member_counts),'Entry_peer_links':sum(member_counts),
           'fresh_Entry_peer_links':sum(q['context']['fresh_peer_count'] for q in quality),
           'valid_Entry_peer_links':{str(n):sum(q['context']['valid_peer_counts'][str(n)] for q in quality) for n in (5,10)},
           'parent_process_future_suffix_market_values_read':0,'worker_future_suffix_rows_received':0,'future_selector_membership_used':0,
           'output_columns':{'TRAJECTORY':{'numeric':407,'categorical':15},'TRAJECTORY_CONTEXT':{'numeric':423,'categorical':15}},
           'model_fits':0,'teacher_sign_reads':0,'Late_performance_reads':0,'threshold_choices':0,
           'created_utc':datetime.now(timezone.utc).isoformat()}
    feature=args.output/'features.jsonl.gz'
    with feature.open('xb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as gz:
        for row in output:gz.write((json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())
    provenance={'status':audit['status'],'source_sha256':{str(p):h for p,h in expected.items()},'v2_feature_schema_sha256':replay.digest(sp),
                'code_sha256':replay.digest(Path(__file__)),'features_sha256':replay.digest(feature),'original_base_columns_reused':151,
                'frozen_normalizer_source_pins':replay.initialize(),'all_actual_input_asof_at_intent':True,'fit_allowed':False}
    for name,value in (('feature_schema.json',schema),('aggregate_audit.json',audit),('provenance.json',provenance)):
        with (args.output/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    print(json.dumps(audit),flush=True)

if __name__=='__main__':main()
