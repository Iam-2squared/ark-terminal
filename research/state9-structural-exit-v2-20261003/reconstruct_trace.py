"""Exact Frozen RC2/Path reconstruction and saved-overlap parity; no EXIT code."""
import argparse, collections, concurrent.futures, gzip, json, math, sys, time
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
import numpy as np
from settings import *

KERNEL = INPUT / 'rc2_kernel'
AUDIT_KERNEL = INPUT / 'rc2_audit_source/reference/source/rc2'
sys.path[:0] = [str(KERNEL), str(AUDIT_KERNEL)]
from candidate.api import Engine
from independent.api import Engine as IndependentEngine
from PATH_FROZEN import PathBuilder, validate
import normalize80, normalize120
from input_gate import scheduled_minutes

RAW = SOURCE = OVERLAP = PROFILE = None

def reason_and_bases(src):
    pd = src.get('previous_daily') or {}
    if not src['previous']:
        return 'PREVIOUS_RAW_NOT_AVAILABLE', None, None
    if pd.get('AdjFactor') is None or Decimal(pd['AdjFactor']) != 1 or 'ExRT' not in pd or pd['ExRT'] is not None:
        return 'PREVIOUS_PRICE_BASIS_NOT_CONTINUOUS', None, None
    try:
        a = normalize80.generate(src['previous'], [])
        b = normalize120.regenerate(src['previous'], [])
        if a['U'] != b['U'] or a['P_ref'] != b['P_ref']:
            raise AssertionError('NORMALIZATION_UNSTABLE')
        return None, a, b
    except ValueError as e:
        return 'M0_PREVIOUS_SOURCE_' + str(e), None, None

def task(entry):
    key = entry['watch_key']; day = entry['session']
    raw = RAW[key]['today']; src = SOURCE[key]
    reason, b80, b120 = reason_and_bases(src)
    assert reason or src['previous_session'] < day
    assert len(raw) == len({int(x[0]) for x in raw})
    assert all(raw[i][0] < raw[i+1][0] for i in range(len(raw)-1))
    current = {int(x[0])+1: x for x in raw}
    first_am = min((int(x[0]) for x in raw if x[0] < 690), default=None)
    first_pm = min((int(x[0]) for x in raw if 750 <= x[0] < regular_end(day)), default=None)
    engine = Engine(PROFILE); oracle = IndependentEngine(PROFILE); path = PathBuilder(key)
    cache = {}; overlap = OVERLAP.get(key, {})
    independent_mismatch = saved_mismatch = compared = coordinates = 0
    null_source_rows = 0; errors = []; canonical = []
    output = PRIVATE / 'FULL_TRACE' / (key.replace('|', '_') + '.jsonl.gz')
    output.parent.mkdir(parents=True, exist_ok=True)

    def coord(value):
        nonlocal coordinates
        lex = json.dumps(value, allow_nan=False)
        if lex not in cache:
            values = []
            for prec, base in ((80, b80), (120, b120)):
                ctx = normalize80.context() if prec == 80 else Context(prec=120, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
                with localcontext(ctx):
                    values.append(format(((Decimal(lex).ln()-Decimal(base['P_ref']).ln()) / Decimal(base['U'])).quantize(Decimal('1e-24')), 'f'))
            if values[0] != values[1]:
                raise AssertionError('NORMALIZATION_UNSTABLE')
            cache[lex] = values[0]; coordinates += 1
        return cache[lex]

    with output.open('wb') as f, gzip.GzipFile(fileobj=f, mode='wb', mtime=0) as gz:
        for end in scheduled_minutes(day):
            t = end - 540; a = current.get(end); token = None
            status = 'SOURCE_UNAVAILABLE' if reason else 'MISSING_RAW_SOURCE'
            if a is not None and reason is None:
                auction = 'TERMINAL_AUCTION_MINUTE' if int(a[0]) in (690, session_close(day)) else 'OPENING_MIXED_MINUTE' if int(a[0]) in (first_am, first_pm) else 'CONTINUOUS'
                token = {'t': t, 'known_at': t, 'source': 'JQUANTS_V2_EQUITIES_BARS_MINUTE', 'auction': auction}
                if valid_raw(a):
                    token.update({k: coord(a[c]) for k,c in (('o',1),('h',2),('l',3),('c',4))})
                    status = 'RAW_CLOSED_AT_ASSUMED_BAR_END'
                else:
                    token.update({k: 'INVALID_RAW_PRICE' for k in 'ohlc'})
                    status = 'RAW_PRICE_NOT_NORMALIZABLE'
            state = engine.step(t, token, key)
            reference = oracle.step(t, token, key)
            if state != reference:
                independent_mismatch += 1
                if len(errors) < 8:
                    errors.append({'bar_end_minute':end, 'kind':'INDEPENDENT_RC2', 'fields':[k for k in state if state[k] != reference.get(k)]})
            slot = {'scheduled_t': t, 'bar_end': stamp(day,end), 'row_status': status}
            validate(state, slot, path.endpoints[-1] if path.endpoints else None)
            offset = len(path.events); endpoint = path._push(state, slot); events = path.events[offset:]
            if end in overlap:
                old = overlap[end]; compared += 1
                observed = bool(old.get('observed', False))
                expected_context = old['context']; expected_direction = old['local_direction']
                equal = old['formal_primary'] == endpoint['Primary_or_null'] and expected_context == state['context'] and expected_direction == state['leg_direction'] and observed == state['current_semantics_observed']
                if old['source_status'] == 'SOURCE_UNAVAILABLE':
                    null_source_rows += 1
                    equal = equal and reason is not None and state['numeric_status'] == 'NOT_AVAILABLE' and old['observed_numeric'] is None
                else:
                    equal = equal and old['observed_numeric'] == int(state['current_semantics_observed']) and old.get('causal_segment_id') == endpoint['causal_segment_id'] and old['display_primary'] == state['primary']
                if not equal:
                    saved_mismatch += 1
                    if len(errors) < 8:
                        errors.append({'bar_end_minute':end, 'kind':'SAVED_OVERLAP', 'saved':old, 'reconstructed':{'formal_primary':endpoint['Primary_or_null'],'context':state['context'],'local_direction':state['leg_direction'],'observed':state['current_semantics_observed'],'segment':endpoint['causal_segment_id'],'display':state['primary']}})
            record = {'watch_key':key, 'bar_end_minute':end, 'slot':slot, 'state':state, 'path':endpoint, 'path_events':events, 'input':token, 'source_status':status, 'source_unavailable_reason':reason, 'historical_actual_known_at':'UNKNOWN', 'assumed_available_at':stamp(day,end)}
            gz.write(jsonline(record))
            canonical.append({'bar_end_minute':end,'t':t,'raw':token})
    assert compared == len(overlap)
    return {'watch_key':key,'entry_minute':entry['fill_minute'],'source_reason':reason,'slots_N':len(path.endpoints),'saved_overlap_N':compared,'saved_unavailable_overlap_N':null_source_rows,'saved_overlap_mismatch_N':saved_mismatch,'independent_RC2_mismatch_N':independent_mismatch,'normalization80_120_price_checks':coordinates,'trace_sha256':sha(output),'trace_bytes':output.stat().st_size,'input_causal_leakage_N':0,'previous_session':src.get('previous_session'),'M0_U':b80['U'] if b80 else None,'M0_P_ref':b80['P_ref'] if b80 else None,'previous_return_pairs_N':b80['previous_return_pairs_N'] if b80 else None,'errors':errors}

def prepare(selected):
    global RAW, SOURCE, OVERLAP, PROFILE
    wanted = {r['watch_key'] for r in selected}
    RAW = {k:v for k,v in load(INPUT/'base/raw_paths_selected.json.gz').items() if k in wanted}
    SOURCE = {k:v for k,v in load(INPUT/'base/PRIVATE_SELECTED_SOURCE_TOKENS.json.gz').items() if k in wanted}
    assert wanted == set(RAW) == set(SOURCE), 'MISSING_REQUIRED_SAVED_SOURCE'
    matrix = np.load(INPUT/'base/features_numeric.npy', mmap_mode='r')
    names = load(INPUT/'P1_Q70_ENTRY_CONTRACT.json')['feature_manifest']['P1_numeric']
    ix = [names.index(k) for k in ['state/context_direction','state/local_direction','state/observed']]
    OVERLAP = collections.defaultdict(dict)
    for m in rows(INPUT/'base/STATE_FEATURE_METADATA.jsonl.gz'):
        if m['watch_key'] not in wanted:
            continue
        x = matrix[m['row_index'],ix]
        d = {**m, **{k:None if np.isnan(v) else int(v) for k,v in zip(['context','local_direction','observed_numeric'],x)}}
        assert m['intent_minute'] not in OVERLAP[m['watch_key']]
        OVERLAP[m['watch_key']][m['intent_minute']] = d
    PROFILE = load(KERNEL/'profile.json')
    pins = load(INPUT/'frozen/source_snapshot.json')
    for prefix in ['candidate','independent']:
        root = KERNEL if prefix == 'candidate' else AUDIT_KERNEL
        for name in ['api.py','exact.py','kernel.py']:
            p = prefix+'/'+name
            assert sha(root/p) == pins[p], p
    assert sha(KERNEL/'PATH_FROZEN.py') == 'ad59222fcc0f9dfed4698efb49a87d66ea4e01b90562cdcaa8b9bc028ffffbf8'

def run(workers, limit):
    selected = entries()[:limit] if limit else entries()
    prepare(selected); start = time.time(); receipts = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for i,r in enumerate(pool.map(task, selected, chunksize=1),1):
            receipts.append(r)
            if i % 50 == 0 or i == len(selected):
                print(json.dumps({'trace_watches':i,'total':len(selected),'seconds':round(time.time()-start,1),'saved_mismatch':sum(x['saved_overlap_mismatch_N'] for x in receipts),'independent_mismatch':sum(x['independent_RC2_mismatch_N'] for x in receipts)}), flush=True)
    save(PRIVATE/('TRACE_RECEIPTS_SAMPLE.json' if limit else 'TRACE_RECEIPTS.json'),receipts)
    summary = {'saved_at_jst':now(),'entry_N':len(selected),'trace_slots_N':sum(r['slots_N'] for r in receipts),'saved_overlap_N':sum(r['saved_overlap_N'] for r in receipts),'saved_unavailable_overlap_N':sum(r['saved_unavailable_overlap_N'] for r in receipts),'saved_overlap_mismatch_N':sum(r['saved_overlap_mismatch_N'] for r in receipts),'independent_RC2_mismatch_N':sum(r['independent_RC2_mismatch_N'] for r in receipts),'normalization80_120_price_checks':sum(r['normalization80_120_price_checks'] for r in receipts),'full_trace_bytes':sum(r['trace_bytes'] for r in receipts),'source_unavailable_watch_N':sum(r['source_reason'] is not None for r in receipts),'future_causal_leakage_N':0,'provider_requests':0,'new_market_data':0,'semantic_changes':0,'formal_unavailable_observed_false_provenance':'saved SOURCE_UNAVAILABLE feature rows have missing numeric observation; require formal null, null context/direction and no observed State; no false market transition','safety':SAFETY}
    total = summary['saved_overlap_mismatch_N'] + summary['independent_RC2_mismatch_N']
    summary['status'] = 'BLOCKED_STATE9_TRACE_RECONSTRUCTION_MISMATCH' if total else 'FULL_STATE9_PATH_TRACE_PARITY_PASS'
    save(HERE/('TRACE_SAMPLE_RECEIPT.json' if limit else 'FULL_TRACE_RECONSTRUCTION_RECEIPT.json'),summary)
    if total:
        print(json.dumps([r for r in receipts if r['errors']][:3],ensure_ascii=False)); raise SystemExit(2)

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8);p.add_argument('--limit',type=int,default=0);a=p.parse_args();run(a.workers,a.limit)
