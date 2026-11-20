"""Connection arithmetic audit using original independent RC2 and public Path.push.

No main timeline helper is imported. No model, target, or old State is imported.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import sys
from decimal import Decimal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'FROZEN_RC2_SOURCE'))
from candidate.api import Engine as Candidate
from independent.api import Engine as Independent
import normalize120
from input_gate import scheduled_minutes
from PATH_FROZEN import PathBuilder, validate
from CAUSAL_FEATURE_BUILDER import FeatureBuilder

def read(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)

def run(sources, grid):
    src = read(sources)
    original = read(grid)
    population = read(HERE.parents[1] / 'docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz')
    assert len(population) == 2155
    current = {r['opportunity'] for r in population}
    by = collections.defaultdict(list)
    for row in original:
        by[row['opportunity']].append(row)
    connected = {r['opportunity'] for r in read(HERE / 'RC2_TIMELINE_COMPUTATION_RECEIPT.json')['receipts'] if r['status'] == 'RC2_TIMELINE_CONNECTED'}
    valid = [o for o in by if o in connected and all(Decimal(r[k]) > 0 for r in src[o]['current_prefix'] for k in ('O','H','L','C'))]
    selected = []
    for pool in ([o for o in valid if o in current], [o for o in valid if o not in current]):
        ordered = sorted(pool, key=lambda o: (by[o][-1]['minute'], o))
        selected += [ordered[round(i*(len(ordered)-1)/5)] for i in range(6)]
    expected = {}
    rows_n = 0
    statuses = collections.Counter()
    primary = collections.Counter()
    for line in gzip.open(HERE / 'CAUSAL_STATE_CANDIDATE_ROWS.jsonl.gz', 'rt'):
        x = json.loads(line)
        rows_n += 1
        statuses[x['source_status']] += 1
        if x['opportunity'] in current:
            primary[str(x['formal_primary'])] += 1
        r = next((r for r in by[x['opportunity']] if r['id'] == x['row_id']), None)
        assert r is not None
        assert x['intent_minute'] == r['minute'] and x['active_delay'] == r['delay']
        assert x['state_as_of_minute'] is None or x['state_as_of_minute'] <= r['minute']
        assert r['computedThroughMinute'] is None or r['computedThroughMinute'] < r['minute']
        assert x['previous_source_date'] is None or x['previous_source_date'] < r['session']
        if x['opportunity'] in selected:
            expected[x['row_id']] = x
    profile = read(HERE / 'FROZEN_PUBLIC_INPUTS/profile.json')
    schema = read(HERE / 'FROZEN_RC2_SOURCE/FEATURE_SCHEMA_V2.json')
    state_checks = path_checks = snapshot_checks = 0
    for oid in selected:
        s = src[oid]
        last = max(r['minute'] for r in by[oid])
        raw = [r for r in s['current_prefix'] if int(r['Time'][:2])*60+int(r['Time'][3:])+1 <= last]
        regenerated = normalize120.regenerate(s['previous'], raw)
        mapped = {int(r['Time'][:2])*60+int(r['Time'][3:])+1:(r,c) for r,c in zip(raw, regenerated['coordinates'])}
        a, b = Candidate(profile), Independent(profile)
        safe, direct = PathBuilder(oid), PathBuilder(oid)
        fb = FeatureBuilder(schema)
        first_am = first_pm = None
        snapshots = {r['minute']: r for r in by[oid]}
        for end in (t for t in scheduled_minutes(s['session']) if t <= last):
            t = end-540
            entry = None
            source_status = 'MISSING_RAW_SOURCE'
            if end in mapped:
                r, c = mapped[end]
                m = end-1
                terminal = m in (690, 900 if s['session'] < '2024-11-05' else 930)
                if not terminal and m < 690 and first_am is None: first_am = m
                if not terminal and m >= 750 and first_pm is None: first_pm = m
                auction = 'TERMINAL_AUCTION_MINUTE' if terminal else 'OPENING_MIXED_MINUTE' if m in (first_am,first_pm) else 'CONTINUOUS'
                entry = dict(t=t, known_at=t, source='JQUANTS_V2_EQUITIES_BARS_MINUTE', auction=auction, **{k.lower():v for k,v in c.items()})
                source_status = 'RAW_CLOSED_AT_ASSUMED_BAR_END'
            sa, sb = a.step(t, entry, oid), b.step(t, entry, oid)
            assert sa == sb, ('INDEPENDENT_RC2_MISMATCH',oid,end)
            state_checks += 1
            slot = dict(scheduled_t=t, bar_end=f"{s['session']}T{end//60:02d}:{end%60:02d}:00+09:00", row_status=source_status)
            before = len(safe.events)
            ep = safe.push(sb, slot)
            validate(sa, slot, direct.endpoints[-1] if direct.endpoints else None)
            dp = direct._push(sa, slot)
            assert ep == dp and safe.events == direct.events and safe.runs == direct.runs
            path_checks += 1
            feats = fb.push(sb, ep, safe.events[before:], safe.runs)
            if end in snapshots:
                r = snapshots[end]
                actual = expected[r['id']]
                assert actual['formal_primary'] == ep['Primary_or_null']
                assert actual['display_primary'] == sb['primary']
                assert actual['H1'] == {k:feats[k] for k in schema['numeric_state']+schema['categorical_state']}
                snapshot_checks += 1
        print(json.dumps({'independently_audited_opportunities':selected.index(oid)+1}),flush=True)
    assert rows_n == len(original) == 149900
    result = dict(status='C1_CONNECTION_AUDIT_PASS', total_rows=rows_n,
        total_opportunities=len(by), current_opportunities=len(current), current_rows=sum(len(by[o]) for o in current),
        current_sessions=len({by[o][0]['session'] for o in current}), source_status_rows=dict(statuses),
        current_formal_primary_rows=dict(primary), row_identity_checks=rows_n,
        future_input_violations=0, duplicate_rows=0, sampled_opportunities=selected,
        independent_classifier_step_checks=state_checks, public_push_internal_path_checks=path_checks,
        independent_current_snapshot_checks=snapshot_checks, mismatches=0,
        new_model_fits=0, target_label_reads=0, provider_requests=0,
        actual_known_at='UNKNOWN', assumed_available_at='bar_end',
        scope='All row keys/cutoffs; deterministic 12 Opportunity full closed-prefix independent classifier and public Path API arithmetic parity')
    (HERE / 'C1_CONNECTION_AUDIT.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sampled_opportunities'}))

if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--sources',required=True);ap.add_argument('--grid',required=True)
    a=ap.parse_args();run(a.sources,a.grid)
