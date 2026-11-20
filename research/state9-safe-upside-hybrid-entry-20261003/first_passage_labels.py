"""New fill-anchored evaluator labels from frozen saved paths; no decision inputs.

This module never imports a State classifier, a model, or an old policy runner.
Unknown coverage and unknown intrabar order are retained.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np

UP = (1, 2, 3, 4, 5)
DOWN = (.5, 1, 2)
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SUB = REPO / 'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate'

def read(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def key(u, d):
    return f'+{u}/-{d:g}'

def active(day, start, end):
    last = 900 if day < '2024-11-05' else 925
    return sum(max(0, min(end, hi) - max(start, lo)) for lo, hi in ((540, 690), (750, last)))

def slots(day, start):
    last = 900 if day < '2024-11-05' else 925
    terminal = 900 if day < '2024-11-05' else 930
    return [x for x in list(range(540, 690)) + [690] + list(range(750, last)) + [terminal] if x >= start]

def before_bounds(a, touch, p0, upside):
    if touch is None:
        return dict(exact_pct=None, optimistic_pct=None, adverse_pct=None, status='NOT_APPLICABLE')
    b = a[touch]
    if upside:
        prior = min(0., float(np.min(a[:touch, 3]) / p0 - 1) * 100) if touch else 0.
        known = min(prior, 100 * (b[1] / p0 - 1), 0.)
        adverse = min(known, 100 * (b[3] / p0 - 1))
    else:
        prior = max(0., float(np.max(a[:touch, 2]) / p0 - 1) * 100) if touch else 0.
        known = max(prior, 100 * (b[1] / p0 - 1), 0.)
        adverse = max(known, 100 * (b[2] / p0 - 1))
    equal = abs(known - adverse) <= 1e-12
    return dict(exact_pct=known if equal else None, optimistic_pct=known,
        adverse_pct=adverse, status='EXACT' if equal else 'INTRABAR_BOUNDED')

def evaluate(day, fill_minute, p0, path, full_status):
    a = np.asarray(path['today'], dtype=np.float64).reshape(-1, 7)
    a = a[a[:, 0] >= fill_minute]
    expected = slots(day, fill_minute)
    seen = set(a[:, 0].astype(int))
    first_missing = next((t for t in expected if t not in seen), None)
    up_touch = {u: next(iter(np.flatnonzero(a[:, 2] >= p0 * (1 + u / 100))), None) for u in UP}
    down_touch = {d: next(iter(np.flatnonzero(a[:, 3] <= p0 * (1 - d / 100))), None) for d in DOWN}
    grid = {}
    for u in UP:
        for d in DOWN:
            ui, di = up_touch[u], down_touch[d]
            first = min((int(i) for i in (ui, di) if i is not None), default=None)
            gap_before = first_missing is not None and (first is None or first_missing < int(a[first, 0]))
            reason = None
            if not len(a):
                status, reason = 'DATA_UNAVAILABLE', 'NO_POST_FILL_ROWS'
            elif gap_before:
                status, reason = 'DATA_UNAVAILABLE', 'UNCLASSIFIED_MISSING_SOURCE_BEFORE_FIRST_TOUCH'
            elif first is None:
                status = 'NEITHER' if full_status == 'AVAILABLE' else 'DATA_UNAVAILABLE'
                reason = None if status == 'NEITHER' else 'CANONICAL_SESSION_END_NOT_EVALUABLE'
            else:
                o, h, l = map(float, a[first, 1:4])
                high, low = p0 * (1 + u / 100), p0 * (1 - d / 100)
                if o >= high:
                    status = 'UP_FIRST'
                elif o <= low:
                    status = 'DOWN_FIRST'
                elif h >= high and l <= low:
                    status, reason = 'ORDER_UNKNOWN', 'BOTH_BARRIERS_SAME_BAR_OPEN_INSIDE'
                elif h >= high:
                    status = 'UP_FIRST'
                elif l <= low:
                    status = 'DOWN_FIRST'
                else:
                    raise AssertionError('FIRST_TOUCH_ARITHMETIC_CONTRADICTION')
            times = {}
            for name, i in [('up', ui), ('down', di)]:
                observable = i is not None and (first_missing is None or first_missing > a[int(i), 0])
                t = int(a[int(i), 0]) if observable else None
                times[f'time_to_{name}_active'] = active(day, fill_minute, t) if t is not None else None
                times[f'first_{name}_bar_start'] = t
                times[f'first_{name}_bar_end'] = t + 1 if t is not None else None
            mae = before_bounds(a, int(ui) if ui is not None else None, p0, True) if status == 'UP_FIRST' else before_bounds(a, None, p0, True)
            mfe = before_bounds(a, int(di) if di is not None else None, p0, False) if status == 'DOWN_FIRST' else before_bounds(a, None, p0, False)
            # If the barrier is already reached at open, intrabar extrema happen after first passage.
            if status == 'UP_FIRST' and a[int(ui), 1] >= p0 * (1 + u / 100):
                mae.update(exact_pct=mae['optimistic_pct'], adverse_pct=mae['optimistic_pct'], status='EXACT_OPEN_TOUCH')
            if status == 'DOWN_FIRST' and a[int(di), 1] <= p0 * (1 - d / 100):
                mfe.update(exact_pct=mfe['optimistic_pct'], adverse_pct=mfe['optimistic_pct'], status='EXACT_OPEN_TOUCH')
            grid[key(u, d)] = dict(status=status, censor_reason=reason,
                first_touch_bar_start=int(a[first, 0]) if first is not None and not gap_before else None,
                same_bar_ambiguity=status == 'ORDER_UNKNOWN', **times,
                MAE_before_up=mae, MFE_before_down=mfe)
    later = a[a[:, 0] > fill_minute]
    later_high = None if full_status != 'AVAILABLE' or not len(later) else 100 * (float(np.max(later[:, 2])) / p0 - 1)
    return dict(grid=grid, strictly_later_high_pct=later_high,
        source_coverage=dict(expected_rows=len(expected), observed_rows=len(seen & set(expected)),
            first_missing_minute=first_missing, missing_is_not_no_trade=True),
        remaining_active_minutes=active(day, fill_minute, 1000))

def run(r1_archive):
    assert read(HERE / 'STATE9_ENTRY_TIMELINE_RECEIPT.json')['gate'] == 'PASS', 'C1_GATE_REQUIRED'
    assert read(HERE / 'FIRST_PASSAGE_CONTRACT.json')['status'] == 'FROZEN', 'C2_FREEZE_REQUIRED'
    with zipfile.ZipFile(r1_archive) as z:
        rb = z.read('all-material-r1/prefit/rows.json')
        assert hashlib.sha256(rb).hexdigest() == '54f7dbb8bd0c9f8974ccccb7a949c0b7ebf0bbe46581be7778f1607f9d9d8cb6'
        rows = json.loads(rb)
    raw = read(SUB / 'raw-paths-evaluator-only.json.gz')
    outcomes = read(SUB / 'outcomes.json.gz')
    assert sha(SUB / 'raw-paths-evaluator-only.json.gz') == '37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b'
    by_opp = collections.defaultdict(list)
    for r in rows:
        by_opp[r['opportunity']].append(r)
    counts = collections.Counter()
    unique_fill_count = 0
    labels_path = HERE / 'FIRST_PASSAGE_LABELS.jsonl.gz'
    with labels_path.open('wb') as fb, gzip.GzipFile(fileobj=fb, mode='wb', mtime=0) as gz:
        for oi, (oid, rr) in enumerate(by_opp.items()):
            rr.sort(key=lambda r: r['minute'])
            fills = {}
            next_fill = None
            for r in reversed(rr):
                saved = outcomes.get(r['id']) or {}
                if r['quoteAvailable'] and saved.get('price') is not None:
                    next_fill = (r, saved)
                fills[r['minute']] = next_fill
            cache = {}
            for r in rr:
                fill = fills[r['minute']]
                if fill is None:
                    item = dict(row_id=r['id'], opportunity=oid, session=r['session'],
                        intent_minute=r['minute'], active_delay=r['delay'], fill_id=None,
                        fill_minute=None, fill_price=None, primary_status='DATA_UNAVAILABLE',
                        censor_reason='NO_CANONICAL_FILL_WITHIN_SAVED_WINDOW',
                        grid={key(u, d): {'status': 'DATA_UNAVAILABLE', 'censor_reason': 'NO_CANONICAL_FILL'} for u in UP for d in DOWN})
                else:
                    fr, saved = fill
                    if fr['id'] not in cache:
                        p0 = saved['price']
                        a = np.asarray(raw[oid]['today'], dtype=np.float64).reshape(-1, 7)
                        hit = a[a[:, 0] == fr['minute']]
                        assert len(hit) == 1 and abs(float(hit[0, 1]) * 1.0005 - p0) <= max(1e-10, abs(p0) * 1e-12)
                        lab = saved.get('labels') or {}
                        cache[fr['id']] = dict(fill_id=fr['id'], fill_minute=fr['minute'], fill_price=p0,
                            saved_session_end_MFE=lab.get('mfeEnd'), saved_session_end_MAE=lab.get('maeEnd'),
                            saved_full_status=lab.get('fullStatus'), saved_30=lab.get('30'), saved_60=lab.get('60'),
                            **evaluate(r['session'], fr['minute'], p0, raw[oid], lab.get('fullStatus')))
                        unique_fill_count += 1
                    item = dict(row_id=r['id'], opportunity=oid, session=r['session'],
                        intent_minute=r['minute'], active_delay=r['delay'], **cache[fr['id']])
                    item['primary_status'] = item['grid']['+2/-1']['status']
                counts[item['primary_status']] += 1
                gz.write((json.dumps(item, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode())
            if oi % 500 == 0:
                print(json.dumps({'processed_opportunities': oi + 1, 'new_label_passes': 1}), flush=True)
    receipt = dict(status='LABEL_PASS_COMPLETE', rows=len(rows), opportunities=len(by_opp),
        unique_fill_labels=unique_fill_count, primary_counts=dict(counts), secondary_pairs=15,
        label_passes=1, source_raw_sha256=sha(SUB / 'raw-paths-evaluator-only.json.gz'),
        source_saved_outcomes_sha256=sha(SUB / 'outcomes.json.gz'), labels_sha256=sha(labels_path),
        evaluator_only=True, future_decision_use=False, old_entry_regenerated=0,
        provider_requests=0, new_model_fits=0, policy_replays=0)
    (HERE / 'LABEL_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--r1-archive', required=True)
    run(ap.parse_args().r1_archive)
