"""Input-only sidecar using the immutable original RC2 feature kernel.

No fit, outcome, threshold selection, order, or public row export. The original
state_task emits one final row by moving its GRID activation to the intent.
Its State/Path queue still starts at the same AM opening. Original P0 compute
is replaced worker-locally with an exact preserved 110-column snapshot; no
recomputed P0 values are consumed. The original State/profile/gaps are intact.
"""
from __future__ import annotations
import argparse
import collections
import concurrent.futures
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import numpy as np
import prebuy_projection as projection

DEFAULT_SOURCE = Path('/workspace/ark-sign-work/research/persistent-watchlist-uptrend-first-entry-20261003-v2')
DEFAULT_RC2 = Path('/workspace/scratch/ark-design-readonly/research/state9-safe-upside-hybrid-entry-20261003')
ROOT_PRIVATE = Path('/workspace/private-recovery/agent-frozen-source')
OLD_BUNDLE = ROOT_PRIVATE/'independent-bundle/legacy-extracted'
BASE_EXTRA = ('entry/p1_score','entry/p1_threshold','entry/p1_margin')
_AUTHORITY_FIELDS = ('watch_key','session','symbol','first_intent','selector_minute','selector_to_intent_active_delay')
_KERNEL = None
_ORIGINAL_ENGINE = None
_ORIGINAL_PATH = None
_ORIGINAL_COMPUTE = None


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def read(path):
    p=Path(path)
    with (gzip.open(p,'rt') if p.suffix=='.gz' else p.open()) as f:return json.load(f)


def rows(path):
    with gzip.open(path,'rt') as f:return [json.loads(line) for line in f if line.strip()]


def stable_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def initialize(source=DEFAULT_SOURCE, rc2=DEFAULT_RC2):
    global _KERNEL,_ORIGINAL_ENGINE,_ORIGINAL_PATH,_ORIGINAL_COMPUTE
    source,rc2=Path(source),Path(rc2)
    identity=read(rc2/'STATE9_FINAL_IDENTITY.json')
    for ref in identity['source_files']:
        if digest(rc2/'FROZEN_RC2_SOURCE'/ref['path'])!=ref['sha256']:
            raise ValueError('FROZEN_KERNEL_PIN_MISMATCH')
    if digest(rc2/'FROZEN_PUBLIC_INPUTS/profile.json')!=identity['profile_sha256']:
        raise ValueError('FROZEN_PROFILE_PIN_MISMATCH')
    # The reader source also has an immutable expected hash in the public freeze.
    frozen=read(source/'FEATURE_FREEZE.json')
    expected=frozen['code_hashes']['causal_features.py']
    amendment=source/'IMPLEMENTATION_FIX_RECEIPT.json'
    if amendment.exists():expected=read(amendment).get('corrected_causal_runner_sha256',expected)
    storage=source/'NPZ_STORAGE_READ_RECEIPT.json'
    if storage.exists():expected=read(storage).get('updated_code_sha256',{}).get('causal_features.py',expected)
    if digest(source/'causal_features.py')!=expected:
        raise ValueError('FROZEN_FEATURE_READER_PIN_MISMATCH')
    manifest={x['path']:x for x in read(source/'MANIFEST.json')['artifacts']}
    for name in ('common.py','price_features.py','price_primitives.py','causal_features.py'):
        if digest(source/name)!=manifest[name]['sha256']:
            raise ValueError('FROZEN_READER_DEPENDENCY_PIN_MISMATCH')
    sys.path.insert(0,str(source))
    common=importlib.import_module('common')
    common.OLD=rc2
    # Original module uses common.OLD during import; bind before importing it.
    kernel=importlib.import_module('causal_features')
    if Path(kernel.__file__).resolve()!=(source/'causal_features.py').resolve():
        raise ValueError('IMPORT_SOURCE_CONFLICT')
    _KERNEL=kernel
    _ORIGINAL_ENGINE=kernel.Engine
    _ORIGINAL_PATH=kernel.PathBuilder
    _ORIGINAL_COMPUTE=kernel.compute
    return {'kernel_source_count':len(identity['source_files']),
            'profile_sha256':identity['profile_sha256'],
            'causal_reader_sha256':digest(source/'causal_features.py'),
            'kernel_identity_sha256':digest(rc2/'STATE9_FINAL_IDENTITY.json'),
            'feature_schema_sha256':digest(rc2/'FROZEN_RC2_SOURCE/FEATURE_SCHEMA_V2.json')}


def exact_p0(runtime, names):
    values=[]
    for name in names:
        column=('entry/intent_clock' if name=='clockMinute' else
                'selector/to_intent_active_delay' if name=='activeMinutesSinceSelector' else 'p0/'+name)
        value=runtime['numeric'][column]
        if value is not None and (type(value) is bool or not isinstance(value,(int,float)) or not math.isfinite(value)):
            raise ValueError('NONFINITE_OR_INVALID_P0')
        values.append(np.nan if value is None else float(value))
    out=np.asarray(values,dtype=np.float64)
    if hashlib.sha256(out.tobytes()).hexdigest()!=runtime['p0_snapshot_hash']:
        raise ValueError('P0_SNAPSHOT_HASH_MISMATCH')
    return out


def raw_before_intent(raw, intent):
    """Do not inspect suffix OHLCV/Value, even if a suffix has an invalid shape."""
    out=[]
    for row in raw:
        start=row[0]
        if type(start) is bool or not isinstance(start,(int,float)) or not math.isfinite(start) or int(start)!=start:
            raise ValueError('RAW_START_MINUTE_REQUIRED')
        if start>=intent:continue
        out.append(row)
    return out


def one_replay(job):
    index,entry,runtime,raw,source=job
    if _KERNEL is None:initialize()
    kernel=_KERNEL
    intent=entry['first_intent'];cutoff=intent['intent_minute']
    if type(cutoff) is not int:raise ValueError('INTENT_CLOCK_REQUIRED')
    key=entry['watch_key']
    if key!=runtime['entry_id'] or key!=runtime['session']+'|'+runtime['symbol']:
        raise ValueError('ENTRY_IDENTITY_MISMATCH')
    if intent['row_id']!=runtime['p0_snapshot_row_id'] or intent['row_index']!=runtime['p0_snapshot_row_index']:
        raise ValueError('ORIGINAL_ROW_ID_INDEX_MISMATCH')
    if cutoff!=runtime['numeric']['entry/intent_clock']:
        raise ValueError('ORIGINAL_INTENT_MISMATCH')
    p0=exact_p0(runtime,kernel.P0_NAMES)
    prefix=raw_before_intent(raw['today'],cutoff)
    # previous fields are the exact saved native source subset. current_prefix
    # and other source members are not consulted by the original state_task.
    selected={k:source[k] for k in ('previous','previous_daily','previous_session')}
    if selected['previous_session'] is not None and selected['previous_session']>=entry['session']:
        raise ValueError('NONPAST_PREVIOUS_SESSION')
    selected_raw={'today':prefix,'previous':raw['previous']}
    if not prefix or prefix[-1][0]+1!=cutoff:
        raise ValueError('INTENT_HAS_NO_FINAL_CLOSED_RAW_ROW')
    # Activation affects GRID-row selection and P0 compute only. State queue,
    # normalization, history transitions and gap resets remain original.
    watch={'watch_key':key,'session':entry['session'],'selector_minute':cutoff,
           'selector_price':1.,'refresh_minutes':[]}
    trace=[]
    latest_state={}
    class LoggingEngine(_ORIGINAL_ENGINE):
        def step(self,*args,**kwargs):
            state=super().step(*args,**kwargs)
            latest_state.clear();latest_state.update(deepcopy(state))
            return state
    class LoggingPath(_ORIGINAL_PATH):
        def _push(self,state,slot):
            before=len(self.events)
            endpoint=super()._push(state,slot)
            end=slot['scheduled_t']+540
            if end>cutoff:raise ValueError('SUFFIX_STATE_STEP')
            trace.append({'bar_end_minute':end,'state':deepcopy(state),
                          'path':deepcopy(endpoint),'path_events':deepcopy(self.events[before:])})
            return endpoint
    def preserved_p0(*unused):return p0.copy()
    kernel.Engine=LoggingEngine;kernel.PathBuilder=LoggingPath;kernel.compute=preserved_p0
    try:
        _,num,cat,meta,receipt=kernel.state_task((index,watch,selected_raw,selected))
    finally:
        kernel.Engine=_ORIGINAL_ENGINE;kernel.PathBuilder=_ORIGINAL_PATH;kernel.compute=_ORIGINAL_COMPUTE
    if len(num)!=1 or len(cat)!=1 or len(meta)!=1:raise ValueError('EXPECTED_ONE_INTENT_ROW')
    if not np.array_equal(num[0,:110],p0,equal_nan=True):raise ValueError('PRESERVED_P0_CHANGED')
    numeric={('p0/'+name if i<110 else name):None if np.isnan(value) else float(value)
             for i,(name,value) in enumerate(zip(kernel.P0_NAMES+kernel.P1_NUM,num[0]))}
    numeric.update({'entry/p1_score':intent['score'],'entry/p1_threshold':intent['threshold'],
                    'entry/p1_margin':intent['score']-intent['threshold']})
    categorical=dict(zip(kernel.P1_CAT,cat[0]))
    projected=projection.project(entry,trace)
    for name,value in projected['numeric'].items():numeric['projection/'+name]=value
    for name,value in projected['categorical'].items():categorical['projection/'+name]=value
    if any(value is not None and not math.isfinite(value) for value in numeric.values()):
        raise ValueError('NONFINITE_REPLAY_OUTPUT')
    # Only compact columns with exactly the original semantics are compared.
    parity={'eligible_exact_clock':False,'numeric_checks':0,'categorical_checks':0,'mismatches':0}
    if runtime['execution_eligible'] and runtime['feature_as_of']==runtime['p0_feature_as_of'] and runtime['provenance']['max_known_minute']==cutoff:
        parity['eligible_exact_clock']=True
        current=trace[-1] if trace else None
        observed=bool(current and current['state']['current_semantics_observed'] is True
                      and current['state']['numeric_status']=='ACCEPTED'
                      and current['state']['observed_at']==current['state']['as_of']
                      and current['path']['Primary_or_null'] is not None)
        pairs={'state/observed':int(observed)}
        if observed:
            pairs.update({'state/context_direction':current['path']['context_direction'],
                          'state/local_direction':current['path']['local_direction'],
                          'state/fast_applicable':int(current['path']['fast_applicable_to_primary']),
                          'state/stop_count':(current['state'].get('stop') or {}).get('count'),
                          'path/dwell_observed_bars':current['path']['dwell_observed_bars'],
                          'path/dwell_scheduled_bars':current['path']['dwell_scheduled_bars']})
        else:pairs.update({k:None for k in ('state/context_direction','state/local_direction','state/fast_applicable','state/stop_count','path/dwell_observed_bars','path/dwell_scheduled_bars')})
        cpairs={'state/current_primary':current['path']['Primary_or_null'] if observed else '__UNKNOWN__'}
        if current:
            cpairs.update({'state/activity':current['state']['activity'], 'state/basis':current['state']['basis'],
                           'state/numeric_status':current['state']['numeric_status']})
        for name,value in pairs.items():
            parity['numeric_checks']+=1;parity['mismatches']+=value!=runtime['numeric'][name]
        for name,value in cpairs.items():
            parity['categorical_checks']+=1;parity['mismatches']+=value!=runtime['categorical'][name]
    result={'entry_id':key,'session':entry['session'],'intent_minute':cutoff,'intent_timestamp':intent['intent_timestamp'],
            'execution_eligible':runtime['execution_eligible'],'numeric':numeric,'categorical':categorical,
            'source_status':meta[0]['source_status'],'quality':projected['quality'],
            'provenance':{**projected['provenance'],'p0_snapshot_hash':runtime['p0_snapshot_hash'],
                          'original_row_id':intent['row_id'],'original_row_index':intent['row_index'],
                          'state_reader_receipt':receipt,'P0_compute':'EXACT_SNAPSHOT_STUB_ORIGINAL_P0_RECOMPUTE_UNUSED',
                          'state_grid_activation':'INTENT_ONLY_ROW_SELECTION_SAME_SCHEDULED_QUEUE',
                          'original_matrix_full_hash_parity_claimed':False},'compact_parity':parity}
    return result


def schema(kernel):
    base_num=['p0/'+name for name in kernel.P0_NAMES]+list(kernel.P1_NUM)+list(BASE_EXTRA)
    base_cat=list(kernel.P1_CAT)
    extra_num=['projection/'+name for name in projection.NUMERIC]
    extra_cat=['projection/'+name for name in projection.CATEGORICAL]
    if len(set(base_num+extra_num))!=len(base_num+extra_num):raise ValueError('DUPLICATE_FEATURE_COLUMNS')
    return {'BASE':{'numeric':base_num,'categorical':base_cat},
            'STRUCTURE':{'numeric':base_num+extra_num,'categorical':base_cat+extra_cat},
            'state_logic_changed':False,'profile_changed':False,'gap_window_changed':False,
            'teacher_fields_in_X':0,'historical_actual_arrival':'UNKNOWN',
            'availability':'INHERITED_RAW_START_PLUS_ONE_BAR_END_ASSUMPTION',
            'learned_score_lineage_audited':False,'fit_allowed':False,
            'full_original_matrix_byte_parity_claimed':False,
            'P0_snapshot_restored_columns':110,'state_history_replayed_columns':38,
            'original_categories_replayed':15}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--native-source',type=Path,required=True)
    parser.add_argument('--native-proof',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--limit',type=int,default=0)
    args=parser.parse_args()
    if not 1<=args.workers<=4:raise ValueError('WORKERS_MAX_FOUR')
    if args.output.exists():raise ValueError('OUTPUT_ALREADY_EXISTS_NO_OVERWRITE')
    proof=read(args.native_proof)
    if proof.get('status') not in ('PASS','SOURCE_SUBSET_HASH_AND_LEXICAL_PROOF_PASS','ORIGINAL_SAVED_SOURCE_HASH_VERIFIED','AUTHENTICATED_EXACT_SAVED_DEVELOPMENT_TOKENS_RESTORED_AND_ENTRY1600_SOURCE_FOUND'):
        raise ValueError('NATIVE_SOURCE_PROOF_NOT_PASS')
    expected_native=proof.get('previous_basis_subset',{}).get('sha256')
    if expected_native is None or digest(args.native_source)!=expected_native:
        raise ValueError('NATIVE_SOURCE_SUBSET_HASH_MISMATCH')
    if digest(ROOT_PRIVATE/'recovered-persistent/raw_paths_selected.json.gz')!=proof['frozen_full_RAW_source_SHA256']:
        raise ValueError('NATIVE_PROOF_RAW_BINDING_MISMATCH')
    pins=initialize()
    rp=OLD_BUNDLE/'reuse_sign/capital_rneg_defense_private/RUNTIME_FEATURES.jsonl.gz'
    ep=OLD_BUNDLE/'reuse_sign/authority_data/quality_original/inputs/FROZEN_ENTRY.jsonl.gz'
    rm={r['entry_id']:r for r in rows(rp)}
    entries=[]
    for r in rows(ep):
        if r['entry_status']=='FIRST_ENTRY':entries.append({k:r[k] for k in _AUTHORITY_FIELDS})
    if len(entries)!=1600 or len(rm)!=1600 or {e['watch_key'] for e in entries}!=set(rm):
        raise ValueError('EXACT_1600_ENTRY_SET_REQUIRED')
    entries.sort(key=lambda e:(e['session'],e['first_intent']['intent_minute'],e['watch_key']))
    raw=read(ROOT_PRIVATE/'recovered-persistent/raw_paths_selected.json.gz');native=read(args.native_source)
    if args.limit:entries=entries[:args.limit]
    jobs=[]
    for i,e in enumerate(entries):
        key=e['watch_key'];cutoff=e['first_intent']['intent_minute']
        # Suffix never crosses the process boundary. Read only its start clock
        # to exclude it, then pass current prefix and the strictly previous day.
        prefix_raw={'today':raw_before_intent(raw[key]['today'],cutoff),'previous':raw[key]['previous']}
        selected_native={k:native[key][k] for k in ('previous','previous_daily','previous_session')}
        jobs.append((i,e,rm[key],prefix_raw,selected_native))
    args.output.mkdir(parents=True)
    outputs=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers,initializer=initialize) as pool:
        for i,result in enumerate(pool.map(one_replay,jobs,chunksize=1),1):
            outputs.append(result)
            if i%50==0:print(json.dumps({'replayed_entries':i,'total_entries':len(entries),'model_fits':0}),flush=True)
    sch=schema(_KERNEL)
    sch['source_pins']=pins
    audit={'status':'INPUTS_REPLAYED_FEATURES_ONLY_NOT_FIT_ENABLED','entry_count':len(outputs),
           'eligible_entry_count':sum(r['execution_eligible'] for r in outputs),
           'source_status_counts':dict(collections.Counter(r['source_status'] for r in outputs)),
           'projection_quality_counts':dict(collections.Counter(str(r['quality']['current_observed']) for r in outputs)),
           'compact_same_intent_entries':sum(r['compact_parity']['eligible_exact_clock'] for r in outputs),
           'compact_numeric_checks':sum(r['compact_parity']['numeric_checks'] for r in outputs),
           'compact_categorical_checks':sum(r['compact_parity']['categorical_checks'] for r in outputs),
           'compact_mismatches':sum(r['compact_parity']['mismatches'] for r in outputs),
           'p0_hash_parity_entries':len(outputs),'normalization_80_120_unique_price_checks':sum(r['provenance']['state_reader_receipt'].get('normalization80_120_unique_price_checks',0) for r in outputs),
           'max_state_endpoint_after_intent':0,'labels_referenced':0,'model_fits':0,'threshold_choices':0,'capital_replays':0,
           'schema_columns':{k:{'numeric':len(v['numeric']),'categorical':len(v['categorical'])} for k,v in sch.items() if isinstance(v,dict) and 'numeric' in v},
           'actual_utc':datetime.now(timezone.utc).isoformat()}
    if audit['compact_mismatches']:audit['status']='BLOCKED_COMPACT_PARITY_MISMATCH'
    fp=args.output/'features.jsonl.gz'
    with fp.open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:
        for r in outputs:z.write((json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())
    provenance={'input_sha256':{'runtime':digest(rp),'entry':digest(ep),'raw':digest(ROOT_PRIVATE/'recovered-persistent/raw_paths_selected.json.gz'),'native':digest(args.native_source),'native_proof':digest(args.native_proof)},
                'code_sha256':digest(Path(__file__)),'features_sha256':digest(fp),'source_pins':pins,
                'model_fits':0,'teacher_fields_referenced':0,'status':audit['status']}
    for name,value in [('feature_schema.json',sch),('provenance.json',provenance),('aggregate_audit.json',audit)]:
        with (args.output/name).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)
    print(json.dumps(audit),flush=True)

if __name__=='__main__':main()
