"""Exact frozen RC2 on causally closed saved source tokens. No labels or model imports."""
import argparse
import collections
import concurrent.futures
from decimal import Decimal, localcontext
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'FROZEN_RC2_SOURCE'
sys.path.insert(0, str(SOURCE))
from candidate.api import Engine
import normalize80
import normalize120
from input_gate import scheduled_minutes
from PATH_FROZEN import PathBuilder, validate
from CAUSAL_FEATURE_BUILDER import FeatureBuilder

SCHEMA = json.loads((SOURCE / 'FEATURE_SCHEMA_V2.json').read_bytes())
PROFILE = json.loads((HERE / 'FROZEN_PUBLIC_INPUTS/profile.json').read_bytes())
CURRENT_FIELDS = SCHEMA['numeric_state'] + SCHEMA['categorical_state']
HISTORY_FIELDS = ('previous_distinct_formal_primary', 'previous_to_current_pair',
    'current_state_active_dwell', 'active_time_since_last_primary_change',
    'transition_count_last5active', 'transition_count_last10active',
    'transition_count_last15active', 'last3_distinct_primary_sequence')

def minute(s):
    return int(s[:2]) * 60 + int(s[3:])

def elapsed(day, start, end):
    last = 900 if day < '2024-11-05' else 925
    return sum(max(0, min(end, hi) - max(start, lo)) for lo, hi in ((540, 690), (750, last)))

def digest(b):
    return hashlib.sha256(b).hexdigest()

def coord(module, base, row):
    # Mechanical factorization of the frozen generate() expression. U/P_ref are
    # independently frozen from previous-day input; ONLY this currently closed row is read.
    with localcontext(module.context()) as ctx:
        ctx.clear_flags()
        U = Decimal(base['U'])
        pref = module.positive(base['P_ref'])
        values = {k: format(((module.positive(row[k]).ln() - pref.ln()) / U).quantize(module.Q), 'f')
            for k in ('O', 'H', 'L', 'C')}
        return values, {s.__name__: bool(v) for s, v in ctx.flags.items()}

def unavailable(oid, src, rows, reason):
    h1 = {k: None if k in SCHEMA['numeric_state'] else '__MISSING__' for k in CURRENT_FIELDS}
    h2 = {k: '__UNKNOWN_HISTORY__' if k in (HISTORY_FIELDS[0], HISTORY_FIELDS[1], HISTORY_FIELDS[-1]) else None for k in HISTORY_FIELDS}
    out = [dict(row_id=r['id'], opportunity=oid, session=r['session'], intent_minute=r['minute'],
        active_delay=r['delay'], source_status='SOURCE_UNAVAILABLE', source_reason=reason,
        formal_primary=None, display_primary=None, observed=None, H1=h1, H2=h2,
        state_as_of_minute=None, feature_max_current_bar_end=None,
        previous_source_date=src.get('previous_session')) for r in rows]
    return out, dict(opportunity=oid, status='SOURCE_UNAVAILABLE', reason=reason, kernel_steps=0,
        candidate_rows=len(rows), future_inputs=0, normalization_mismatches=0)

def task(arg):
    oid, src, rows = arg
    day = src['session']
    assert set(src) <= {'session', 'symbol', 'previous_session', 'previous',
        'previous_daily', 'current_prefix', 'max_candidate_intent'}, 'CAUSAL_SOURCE_ALLOWLIST'
    previous = src['previous']
    if not previous:
        return unavailable(oid, src, rows, 'PREVIOUS_RAW_NOT_AVAILABLE')
    pd = src.get('previous_daily') or {}
    if pd.get('AdjFactor') is None or Decimal(pd['AdjFactor']) != 1 or 'ExRT' not in pd or pd['ExRT'] is not None:
        return unavailable(oid, src, rows, 'PREVIOUS_PRICE_BASIS_NOT_CONTINUOUS')
    assert src['previous_session'] < day
    try:
        for r in previous:
            vals = [normalize80.positive(r[k]) for k in ('O', 'H', 'L', 'C')]
            if not vals[2] <= min(vals[0], vals[3]) <= max(vals[0], vals[3]) <= vals[1]:
                return unavailable(oid, src, rows, 'PREVIOUS_RAW_OHLC_INVALID')
        b80 = normalize80.generate(previous, [])
        b120 = normalize120.generate(previous, [])
    except ValueError as e:
        return unavailable(oid, src, rows, 'M0_PREVIOUS_SOURCE_' + str(e))
    assert b80['U'] == b120['U'] and b80['P_ref'] == b120['P_ref'], 'NORMALIZATION_UNSTABLE'
    current = {minute(r['Time']) + 1: r for r in src['current_prefix']}
    assert len(current) == len(src['current_prefix'])
    assert all(t <= src['max_candidate_intent'] for t in current)
    engine = Engine(PROFILE)
    path = PathBuilder(oid)
    builder = FeatureBuilder(SCHEMA)
    queue = [t for t in scheduled_minutes(day) if t <= src['max_candidate_intent']]
    cursor = 0
    latest = endpoint = None
    current_feats = None
    segment = None
    seq = []
    changes = []
    last_change = support_start = None
    first_am = first_pm = None
    kernel_steps = 0
    snapshots = []
    new_history = None
    coords_saved = []
    valid_rows = []
    parity = 0
    for r in sorted(rows, key=lambda x: x['minute']):
        now = r['minute']
        while cursor < len(queue) and queue[cursor] <= now:
            end = queue[cursor]
            cursor += 1
            t = end - 540
            original = current.get(end)
            raw = None
            row_status = 'MISSING_RAW_SOURCE'
            if original is not None:
                m = end - 1
                terminal = m in (690, 900 if day < '2024-11-05' else 930)
                if not terminal and m < 690 and first_am is None:
                    first_am = m
                if not terminal and m >= 750 and first_pm is None:
                    first_pm = m
                auction = 'TERMINAL_AUCTION_MINUTE' if terminal else 'OPENING_MIXED_MINUTE' if m in (first_am, first_pm) else 'CONTINUOUS'
                try:
                    x80, _ = coord(normalize80, b80, original)
                    x120, _ = coord(normalize120, b120, original)
                    assert x80 == x120, 'NORMALIZATION_UNSTABLE'
                    raw = dict(t=t, known_at=t, source='JQUANTS_V2_EQUITIES_BARS_MINUTE', auction=auction,
                        **{k.lower(): x80[k] for k in ('O', 'H', 'L', 'C')})
                    row_status = 'RAW_CLOSED_AT_ASSUMED_BAR_END'
                    if len(valid_rows) < 3:
                        valid_rows.append(original)
                        coords_saved.append(x80)
                        golden80 = normalize80.generate(previous, valid_rows)
                        golden120 = normalize120.generate(previous, valid_rows)
                        assert golden80['coordinates'] == coords_saved == golden120['coordinates'], 'M0_FACTORIZATION_PARITY'
                        parity += 1
                except ValueError:
                    # Invalid raw price cannot be log-normalized. The exact API
                    # rejects the deliberately invalid numeric token, forces reset,
                    # and the source deficiency remains explicit metadata.
                    raw = dict(t=t, known_at=t, source='JQUANTS_V2_EQUITIES_BARS_MINUTE', auction=auction,
                        o='INVALID_RAW_PRICE', h='INVALID_RAW_PRICE', l='INVALID_RAW_PRICE', c='INVALID_RAW_PRICE')
                    row_status = 'RAW_PRICE_NOT_NORMALIZABLE'
            assert raw is None or raw['known_at'] <= t and end <= now
            state = engine.step(t, raw, oid)
            kernel_steps += 1
            slot = dict(scheduled_t=t, bar_end=f'{day}T{end // 60:02d}:{end % 60:02d}:00+09:00', row_status=row_status)
            validate(state, slot, path.endpoints[-1] if path.endpoints else None)
            previous_event_n = len(path.events)
            # Frozen internal transition function, with frozen validation. The
            # accepted-input output is unchanged; rollback-fault claims are not made.
            endpoint = path._push(state, slot)
            events = path.events[previous_event_n:]
            all_feats = builder.push(state, endpoint, events, path.runs)
            current_feats = {k: all_feats[k] for k in CURRENT_FIELDS}
            formal = endpoint['Primary_or_null']
            if endpoint['causal_segment_id'] != segment or formal is None or any(e['event_type'] in ('SEGMENT_BREAK', 'OBSERVATION_LOST') for e in events):
                seq = []
                changes = []
                last_change = support_start = None
            segment = endpoint['causal_segment_id']
            if formal is not None:
                if support_start is None:
                    support_start = end
                if any(e['event_type'] == 'TRANSITION' for e in events):
                    changes.append(end)
                    last_change = end
                if not seq or seq[-1] != formal:
                    seq.append(formal)
                    seq = seq[-3:]
            new_history = dict(previous_distinct_formal_primary=seq[-2] if len(seq) >= 2 else '__UNKNOWN_HISTORY__',
                previous_to_current_pair='>'.join(seq[-2:]) if len(seq) >= 2 else '__UNKNOWN_HISTORY__',
                current_state_active_dwell=elapsed(day, endpoint['entered_at'] + 540, end) if formal is not None else None,
                active_time_since_last_primary_change=elapsed(day, last_change, end) if last_change is not None else None,
                last3_distinct_primary_sequence='>'.join(seq) if len(seq) >= 3 else '__UNKNOWN_HISTORY__')
            for w in (5, 10, 15):
                new_history[f'transition_count_last{w}active'] = sum(0 <= elapsed(day, x, end) < w for x in changes) if support_start is not None and elapsed(day, support_start, end) >= w else None
            latest = state
        assert latest is not None and latest['as_of'] + 540 <= now
        assert current_feats is not None and new_history is not None
        snapshots.append(dict(row_id=r['id'], opportunity=oid, session=day, intent_minute=now,
            active_delay=r['delay'], source_status='SAVED_SOURCE_CONNECTED',
            source_reason=None, formal_primary=endpoint['Primary_or_null'], display_primary=latest['primary'],
            observed=latest['current_semantics_observed'], H1=current_feats.copy(), H2=new_history.copy(),
            state_as_of_minute=latest['as_of'] + 540, feature_max_current_bar_end=latest['as_of'] + 540,
            previous_source_date=src['previous_session'], causal_segment_id=segment,
            row_source_status=endpoint['quality']['row_status']))
    return snapshots, dict(opportunity=oid, status='RC2_TIMELINE_CONNECTED', candidate_rows=len(rows),
        kernel_steps=kernel_steps, normalization_mismatches=0, future_inputs=0,
        normalization80_120_match=True, factorization_golden_checks=parity,
        U_sha256=digest(b80['U'].encode()), P_ref_token_sha256=digest(b80['P_ref'].encode()),
        previous_return_pairs=b80['previous_return_pairs_N'])

def run(sources_path, grid_path, workers):
    proof = json.loads((HERE / 'ORIGINAL_SAVED_SOURCE_PROOF.json').read_bytes())
    assert digest(Path(sources_path).read_bytes()) == proof['private_source_sha256']
    src = json.loads(gzip.decompress(Path(sources_path).read_bytes()))
    rows = json.loads(gzip.decompress(Path(grid_path).read_bytes()))
    by_opp = collections.defaultdict(list)
    for r in rows:
        by_opp[r['opportunity']].append(r)
    receipts = []
    output = HERE / 'CAUSAL_STATE_CANDIDATE_ROWS.jsonl.gz'
    count = 0
    with output.open('wb') as fb, gzip.GzipFile(fileobj=fb, mode='wb', mtime=0) as gz:
        def inputs(oid):
            s = src[oid]
            value = {k: s[k] for k in ('session', 'symbol', 'previous_session', 'previous',
                'current_prefix', 'max_candidate_intent')}
            prev = s.get('previous_daily') or {}
            value['previous_daily'] = {k: prev.get(k) for k in ('AdjFactor', 'ExRT')}
            return value
        args = ((oid, inputs(oid), rr) for oid, rr in by_opp.items())
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            for i, (records, receipt) in enumerate(pool.map(task, args, chunksize=1)):
                for r in records:
                    gz.write((json.dumps(r, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode())
                count += len(records)
                receipts.append(receipt)
                if i % 250 == 0:
                    print(json.dumps({'opportunities_completed': i + 1, 'candidate_rows': count,
                        'new_model_fits': 0, 'new_labels': 0}), flush=True)
    assert count == len(rows) == 149900
    result = dict(status='C1_TIMELINE_COMPUTATION_COMPLETE', rows=count,
        opportunities=len(receipts), kernel_steps=sum(x['kernel_steps'] for x in receipts),
        future_inputs=0, normalization_mismatches=0,
        source_unavailable=dict(collections.Counter(x.get('reason') for x in receipts if x['status'] == 'SOURCE_UNAVAILABLE')),
        factorization_golden_checks=sum(x.get('factorization_golden_checks', 0) for x in receipts),
        output_sha256=digest(output.read_bytes()), receipts=receipts,
        new_model_fits=0, new_labels=0, provider_requests=0, old_state_substitutions=0,
        State9_Profile_M0_Path_semantic_changes=0, protected_opens=0,
        actual_known_at='UNKNOWN', assumed_available_at='bar_end',
        numeric_independence='Frozen 80 and120 routes; shared Python Decimal library; finite canonical stability, not exact-log proof',
        path_runtime='Frozen validate and _push accepted-input transition; no rollback-fault certification')
    (HERE / 'RC2_TIMELINE_COMPUTATION_RECEIPT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'receipts'}))

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sources', required=True)
    ap.add_argument('--grid', required=True)
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    run(a.sources, a.grid, a.workers)
