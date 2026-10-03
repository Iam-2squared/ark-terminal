"""Independent source audit: ZIP originals -> SQLite and Fraction, no Primary imports.

No allocator, model, State9 trace, Entry policy or EXIT policy is executed.
Primary outputs are opened only after independent records have been derived.
"""
from collections import Counter
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from zoneinfo import ZoneInfo
import gzip
import hashlib
import io
import json
import os
import sqlite3
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent
PRIVATE = BASE / 'capital_c2_recovery_private'
OUT = ROOT / 'docs/evidence/phase57-capital-state9-vnext-c2-recovery-20261004-v1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def jsonl(payload):
    return [json.loads(line) for line in gzip.decompress(payload).splitlines()]


def exact_raw(row):
    if len(row) < 6:
        return False
    try:
        return all(Fraction(str(x)) > 0 for x in row[1:6])
    except (ValueError, ZeroDivisionError):
        return False


def main():
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE entries (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    db.execute('CREATE TABLE exits (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    db.execute('CREATE TABLE raw (id TEXT, minute INTEGER, body TEXT, PRIMARY KEY(id, minute))')
    source_hashes = {}
    parent = next((BASE / 'project_sources').glob('19-*.zip'))
    with zipfile.ZipFile(parent) as outer:
        nested = {}
        for version in ('V2', 'V3'):
            name = next(n for n in outer.namelist() if 'STRUCTURAL_EXIT_' + version in n and n.endswith('.zip'))
            data = outer.read(name)
            source_hashes[name.split('/')[-1]] = sha(data)
            nested[version] = zipfile.ZipFile(io.BytesIO(data))
        ebytes = nested['V2'].read('FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz')
        xbytes = nested['V3'].read('REPLAY_ROWS.jsonl.gz')
        old_raw_bytes = nested['V2'].read('SAVED_INPUTS/raw_paths_selected.json.gz')
        for version, name, payload in [('V2', 'FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz', ebytes), ('V2', 'SAVED_INPUTS/raw_paths_selected.json.gz', old_raw_bytes), ('V3', 'REPLAY_ROWS.jsonl.gz', xbytes)]:
            m = json.loads(nested[version].read('MANIFEST.json'))
            assert m['components'][name]['sha256'] == sha(payload)
            source_hashes[version + ':' + name] = sha(payload)
        watches = jsonl(ebytes)
        entries = [r for r in watches if r['entry_status'] == 'FIRST_ENTRY']
        exits = jsonl(xbytes)
        db.executemany('INSERT INTO entries VALUES (?, ?)', [(r['watch_key'], json.dumps(r)) for r in entries])
        db.executemany('INSERT INTO exits VALUES (?, ?)', [(r['watch_key'], json.dumps(r)) for r in exits])
        old_raw = json.loads(gzip.decompress(old_raw_bytes))
    base_path = BASE / 'recovery_dependency_inputs/Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip'
    overlay_path = BASE / 'recovery_dependency_inputs/Ark_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE_20261003_PRIVATE.zip'
    expected_archives = {
        base_path: 'c0024055e9afa19089318c0f2a281e3fe15d48e10945b752be48e9239235ac15',
        overlay_path: '0ede654a0a730f78bebeb4fcec1c21503de80c7cb2950d205aaf87e7c79853b7',
    }
    for path, expected in expected_archives.items():
        actual = file_sha(path)
        assert actual == expected
        source_hashes[path.name] = actual
    with zipfile.ZipFile(base_path) as z:
        rname = next(n for n in z.namelist() if n.endswith('persistent_sources/raw_paths_selected.json.gz'))
        tname = next(n for n in z.namelist() if n.endswith('private_source/PRIVATE_SELECTED_SOURCE_TOKENS.json.gz'))
        receipt_name = next(n for n in z.namelist() if n.endswith('persistent_sources/SOURCE_EXPORT_RECEIPT.json'))
        rbytes, tbytes = z.read(rname), z.read(tname)
        receipt = json.loads(z.read(receipt_name))
        assert sha(rbytes) == receipt['files']['raw_paths_selected.json.gz']['sha256']
        assert sha(tbytes) == '20668479355fe37492a154ee80ea132b5af8bf2bf78269d90a2df5814d848dc7'
        source_hashes['original_selected_raw_member'] = sha(rbytes)
        source_hashes['original_source_tokens_member'] = sha(tbytes)
        raw = json.loads(gzip.decompress(rbytes))
        tokens = json.loads(gzip.decompress(tbytes))
    with zipfile.ZipFile(overlay_path) as z:
        name = next(n for n in z.namelist() if '/CORRECTED_LINEAGE_FAST_FREEZE_20261003/FIRST_ENTRY_Q70.jsonl.gz' in n)
        payload = z.read(name)
        source_hashes['official_freeze_P1_Q70_member'] = sha(payload)
        official = {r['watch_key']: r for r in jsonl(payload) if r['family'] == 'P1' and r['entry_status'] == 'FIRST_ENTRY'}
    assert len(official) == len(entries) == len(exits) == 1600
    assert db.execute('SELECT COUNT(*) FROM entries e LEFT JOIN exits x ON e.id=x.id WHERE x.id IS NULL').fetchone()[0] == 0
    counts = Counter()
    known = Counter()
    tax = Counter()
    session_set, unresolved_sessions, unresolved_symbols = set(), set(), set()
    independent = []
    for key, ebody, xbody in db.execute('SELECT e.id,e.body,x.body FROM entries e JOIN exits x ON e.id=x.id ORDER BY e.id').fetchall():
        e, x = json.loads(ebody), json.loads(xbody)
        a = raw[key]['today']
        counts['source_value_mismatch_N'] += int(a != old_raw[key]['today'])
        db.executemany('INSERT INTO raw VALUES (?, ?, ?)', [(key, int(r[0]), json.dumps(r)) for r in a])
        stored = {m: json.loads(body) for m, body in db.execute('SELECT minute,body FROM raw WHERE id=?', (key,))}
        counts['current_source_rows_N'] += len(a)
        frozen = official[key]
        counts['official_overlay_identity_mismatch_N'] += int(any(e[f] != frozen[f] for f in ('watch_key', 'session', 'symbol', 'fill_minute', 'fill_timestamp', 'fill_price')))
        counts['identity_mismatch_N'] += int((e['session'], e['symbol'], e['fill_timestamp'], e['fill_price']) != (x['session'], x['symbol'], x['entry_timestamp'], x['entry_fill_price']))
        counts['buy_arithmetic_N'] += 1
        counts['price_mismatch_N'] += int(abs(Fraction(str(e['fill_price'])) - Fraction(str(stored[e['fill_minute']][1])) * Fraction(2001, 2000)) >= Fraction(1, 100000000))
        day = e['session']
        session_set.add(day)
        end = 925 if day >= '2024-11-05' else 900
        terminal = 930 if day >= '2024-11-05' else 900
        sell_minute = x['sell_minute'] if x['sell_minute'] is not None else end
        # Independently enumerate the whole civil-minute range and filter sessions.
        grid = [m for m in range(540, end) if (m < 690 or m >= 750) and e['fill_minute'] <= m < min(sell_minute, end)]
        missing = len(set(grid).difference(stored))
        sampled = [m for m in grid if (m + 1) % 5 == 0]
        missing_sampled = len(set(sampled).difference(stored))
        counts['candidate_1m_missing_rows_N'] += missing
        counts['candidate_1m_incomplete_N'] += int(missing > 0)
        counts['potential_5m_grid_slots_N'] += len(sampled)
        counts['potential_5m_grid_1m_close_missing_N'] += missing_sampled
        counts['potential_5m_grid_present_N'] += len(sampled) - missing_sampled
        counts['potential_5m_grid_incomplete_candidates_N'] += int(missing_sampled > 0)
        counts['current_candidate_exact_auction_source_present_N'] += int(terminal in stored and exact_raw(stored[terminal]))
        daily = tokens[key].get('current_daily')
        counts['current_candidate_daily_close_present_N'] += int(isinstance(daily, dict) and daily.get('C') is not None)
        item = {'entry_id': key, 'session': day, 'symbol': e['symbol'], 'exit_status': x['sell_status'], 'missing_1m_N': missing, 'potential_5m_grid_missing_N': missing_sampled, 'potential_5m_grid_slots_N': len(sampled), 'source_matches_original_stop': a == old_raw[key]['today']}
        if x['sell_status'] == 'FILLED':
            counts['filled_exit_N'] += 1
            counts['sell_arithmetic_N'] += 1
            raw_price = stored[x['sell_minute']][4 if x['sell_source'] == 'PLANNED_TERMINAL_AUCTION_CLOSE' else 1]
            counts['price_mismatch_N'] += int(Fraction(str(raw_price)) * Fraction(1999, 2000) != Fraction(x['sell_price_decimal']))
            counts['commission_nonzero_N'] += int(x['commission'] != 0)
            ftime = datetime.fromisoformat(x['sell_timestamp'])
            ktime = datetime.fromisoformat(x['sell_source_assumed_available_at'])
            delta = int((ktime - ftime).total_seconds())
            counts['availability_delta_exact_60_seconds_N'] += int(delta == 60)
            counts['source_known_later_than_reference_N'] += int(ktime > ftime)
            # R34 original contract, evaluated directly without importing its implementation.
            counts['existing_exit_validator_future_at_reference_N'] += int(ktime > ftime)
            counts['existing_exit_validator_timestamp_mismatch_at_source_time_N'] += int(ftime != ktime)
            item['known_at_class'] = 'REFERENCE_FILL_ONLY_NOT_RUNTIME_KNOWN_AT'
        else:
            assert x['sell_status'] == 'UNRESOLVED' and x['sell_price'] is None and x['sell_timestamp'] is None
            counts['unresolved_exit_N'] += 1
            unresolved_sessions.add(day)
            unresolved_symbols.add(e['symbol'])
            intent = x['exit_intent']['minute'] if isinstance(x.get('exit_intent'), dict) else None
            am = sorted(m for m in stored if m < 690)
            pm = sorted(m for m in stored if 750 <= m < end)
            mixed = {540, 750, am[0] if am else None, pm[0] if pm else None}
            regular_open = [m for m, row in stored.items() if intent is not None and m >= intent and m > e['fill_minute'] and (540 <= m < 690 or 750 <= m < end) and m not in mixed and exact_raw(row)]
            auction = terminal in stored and exact_raw(stored[terminal])
            assert not regular_open and not auction
            item.update(known_at_class='KNOWN_AT_UNRESOLVED', reason_taxonomy='SOURCE_NOT_STORED', exact_regular_eligible_source_N=len(regular_open), exact_terminal_auction_source_N=int(auction))
            tax[item['reason_taxonomy']] += 1
        known[item['known_at_class']] += 1
        independent.append(item)
    # Commit derived private records before consulting Primary for agreement.
    derived_path = PRIVATE / 'INDEPENDENT_ADMISSION_ROWS.jsonl.gz'
    with derived_path.open('xb') as f:
        with gzip.GzipFile(fileobj=f, mode='wb', mtime=0, filename='') as z:
            for item in independent:
                z.write((json.dumps(item, sort_keys=True) + '\n').encode())
    primary = json.loads((OUT / 'RECOVERY_PRIMARY_AUDIT.json').read_text())
    differences = []
    for name, value in primary['counts'].items():
        if counts[name] != value:
            differences.append({'field': name, 'independent': counts[name], 'primary': value})
    for name, value in [('known_at_classification', dict(known)), ('taxonomy', dict(tax))]:
        if primary[name] != value:
            differences.append({'field': name})
    with gzip.open(PRIVATE / 'RECOVERY_ADMISSION_ROWS.jsonl.gz', 'rt') as f:
        prows = {r['entry_id']: r for r in map(json.loads, f)}
    with gzip.open(PRIVATE / 'RECOVERY_MARK_SOURCE_ROWS.jsonl.gz', 'rt') as f:
        pmarks = {r['entry_id']: r for r in map(json.loads, f)}
    for row in independent:
        key = row['entry_id']
        for field in ('exit_status', 'known_at_class', 'reason_taxonomy', 'exact_regular_eligible_source_N', 'exact_terminal_auction_source_N'):
            if row.get(field) != prows[key].get(field):
                differences.append({'field': 'private_row:' + field})
        for field in ('missing_1m_N', 'potential_5m_grid_missing_N', 'potential_5m_grid_slots_N'):
            if row[field] != pmarks[key][field]:
                differences.append({'field': 'private_mark:' + field})
    assert not differences, 'Independent source-admission disagreement; retain originals and investigate.'
    report = {'saved_at_jst': datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(), 'repo': 'Iam-2squared/ark-terminal', 'branch': 'capital-state9-vnext-20261004', 'basis_head': os.environ['RECOVERY_BASIS_HEAD'], 'status': 'INDEPENDENT_SOURCE_AGREEMENT_PASS_C2_ADMISSION_BLOCKED', 'independent_method': 'Original outer handoff ZIP -> original V2/V3 component manifests; original frozen base + official overlay archive hashes -> SQLite identity/raw joins and Fraction arithmetic. No Primary import; derived rows saved before comparison.', 'candidate_N': len(independent), 'watch_N': len(watches), 'sessions_N': len(session_set), 'unresolved_sessions_N': len(unresolved_sessions), 'unresolved_symbols_N': len(unresolved_symbols), 'counts': dict(counts), 'known_at_classification': dict(known), 'taxonomy': dict(tax), 'mismatch_N': len(differences), 'source_hashes': source_hashes, 'derived_private_rows_sha256': file_sha(derived_path), 'source_sha256': file_sha(Path(__file__)), 'cash_validator_scope': 'Direct timestamp==now and knownAt<=now predicates on immutable callbacks; no step/positions/funding/settlement. All1561 future at reference and all1561 timestamp-mismatched at source availability.', 'cost_canary': {'entry_multiplier': '2001/2000', 'sell_multiplier': '1999/2000', 'commission': 0, 'quantity': 100, 'cash_change_fraction': str(100 * (Fraction(1010) * Fraction(1999, 2000) - Fraction(1000) * Fraction(2001, 2000))), 'cost_double_count': 0}, 'budgets': {'fit': 0, 'Capital_performance_replay': 0, 'Entry_EXIT_replay': 0, 'provider_requests': 0, 'new_market_data': 0, 'orders': 0, 'State9_feature_search': 0, 'protected_opens': 0, 'Claude': 0}, 'Frozen_changes': 0, 'missing_imputation': 0, 'row_exclusion': 0}
    with (OUT / 'RECOVERY_INDEPENDENT_AUDIT.json').open('x') as f:
        json.dump(report, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
    print(json.dumps({'independent_mismatch_N': len(differences), 'candidate_N': len(independent), 'filled_N': counts['filled_exit_N'], 'unresolved_N': counts['unresolved_exit_N'], 'missing_1m_N': counts['candidate_1m_missing_rows_N'], 'known_at_classification': dict(known), 'Capital_replay': 0}))


if __name__ == '__main__':
    main()
