"""Inspect target-only market rows in inherited previous-session source links.

No new data; old frozen source tokens and original raw-path member only.
Source rows in another watch are not automatically current Frozen EXIT receipts.
"""
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from zoneinfo import ZoneInfo
import gzip
import hashlib
import json
import os
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent
OUT = ROOT / 'docs/evidence/phase57-capital-state9-vnext-c2-recovery-20261004-v1'
PRIVATE = BASE / 'capital_c2_recovery_private'


def main():
    with gzip.open(BASE / 'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz', 'rt') as f:
        entries = {r['watch_key']: r for r in map(json.loads, f) if r['entry_status'] == 'FIRST_ENTRY'}
    with gzip.open(BASE / 'work_inputs/exit_v3/REPLAY_ROWS.jsonl.gz', 'rt') as f:
        exits = {r['watch_key']: r for r in map(json.loads, f)}
    with zipfile.ZipFile(BASE / 'recovery_dependency_inputs/Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip') as z:
        n = next(n for n in z.namelist() if n.endswith('private_source/PRIVATE_SELECTED_SOURCE_TOKENS.json.gz'))
        source_bytes = z.read(n)
        tokens = json.loads(gzip.decompress(source_bytes))
        n = next(n for n in z.namelist() if n.endswith('persistent_sources/raw_paths_selected.json.gz'))
        raw_bytes = z.read(n)
        paths = json.loads(gzip.decompress(raw_bytes))
    target = {(e['session'], e['symbol']): key for key, e in entries.items()}
    found = defaultdict(dict)
    counts = Counter()
    for origin_key, token in tokens.items():
        for role in ('current_prefix', 'previous'):
            for row in token[role]:
                pair = (row.get('Date'), str(row.get('Code')))
                if pair not in target:
                    continue
                key = target[pair]
                minute = int(row['Time'].split(':')[0]) * 60 + int(row['Time'].split(':')[1])
                counts['target_token_row_occurrences_N'] += 1
                # Frozen source tokens preserve JSON number lexemes as strings.
                signature = tuple(str(Fraction(str(row.get(f)))) for f in ('O', 'H', 'L', 'C', 'Vo', 'Va'))
                identity = (minute, signature)
                found[key].setdefault(identity, []).append({'origin_watch': origin_key, 'source_role': role, 'source_receipt': row.get('_source'), 'raw_received_at_history': token.get('raw_received_at_history')})
    # A distinct, original array route checks inherited previous-session duplicates.
    alternate = defaultdict(set)
    for origin_key, source in paths.items():
        pair = (source.get('previousSession'), origin_key.split('|')[-1])
        if pair in target:
            for row in source['previous']:
                alternate[target[pair]].add((int(row[0]), tuple(str(Fraction(str(v))) for v in row[1:7])))
    differences = []
    full_details = []
    for key, e in entries.items():
        frozen = {int(r[0]): tuple(str(Fraction(str(v))) for v in r[1:7]) for r in paths[key]['today']}
        extra = [(minute, signature, origins) for (minute, signature), origins in found[key].items() if minute not in frozen]
        conflicts = [(minute, signature) for minute, signature in found[key] if minute in frozen and signature != frozen[minute]]
        counts['target_unique_token_rows_N'] += len(found[key])
        counts['additional_target_minutes_N'] += len({x[0] for x in extra})
        counts['candidate_with_additional_minutes_N'] += int(bool(extra))
        counts['source_value_conflict_N'] += len(conflicts)
        array_extra = {minute for minute, _ in alternate[key] if minute not in frozen}
        token_previous_extra = {minute for (minute, _), origins in found[key].items() if minute not in frozen and any(o['source_role'] == 'previous' for o in origins)}
        counts['independent_previous_link_extra_minutes_N'] += len(array_extra)
        counts['previous_link_extra_minutes_mismatch_N'] += int(array_extra != token_previous_extra)
        x = exits[key]
        if x['sell_status'] == 'UNRESOLVED':
            terminal = 930 if e['session'] >= '2024-11-05' else 900
            counts['unresolved_with_additional_minutes_N'] += int(bool(extra))
            counts['unresolved_with_additional_terminal_minute_N'] += int(any(v[0] == terminal for v in extra))
            full_details.append({'entry_id': key, 'additional_source_rows': [{'minute': minute, 'OHLC_volume_value': signature, 'origins': origins} for minute, signature, origins in extra], 'conflicts': conflicts, 'current_exit_status_changed': False, 'known_at_generated': False})
    assert not counts['source_value_conflict_N'], 'Original source values conflict; retain originals and investigate.'
    assert not counts['previous_link_extra_minutes_mismatch_N'], 'Source-route mismatch; investigate before admitting.'
    with (PRIVATE / 'PREVIOUS_SOURCE_LINK_ROWS.jsonl.gz').open('xb') as file:
        with gzip.GzipFile(fileobj=file, mode='wb', mtime=0, filename='') as z:
            for item in full_details:
                z.write((json.dumps(item, sort_keys=True) + '\n').encode())
    report = {'saved_at_jst': datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(), 'repo': 'Iam-2squared/ark-terminal', 'branch': 'capital-state9-vnext-20261004', 'basis_head': os.environ['RECOVERY_BASIS_HEAD'], 'status': 'PREVIOUS_SOURCE_LINK_SEARCH_COMPLETE', 'source_hashes': {'original_source_token_member': hashlib.sha256(source_bytes).hexdigest(), 'original_raw_path_member': hashlib.sha256(raw_bytes).hexdigest()}, 'scope': 'Only current1600 symbol/session pairs examined. Original selected4931 Development source context already frozen; unrelated market/teacher rows not analyzed.', 'counts': dict(counts), 'direct_admission_or_Frozen_correction': False, 'Capital_replay': 0, 'Entry_EXIT_replay': 0, 'provider_requests': 0, 'new_market_data': 0, 'known_at_generated': 0}
    with (OUT / 'PREVIOUS_SOURCE_LINK_DISCOVERY.json').open('x') as f:
        json.dump(report, f, sort_keys=True, indent=2)
        f.write('\n')
    print(json.dumps({'status': report['status'], 'counts': dict(counts), 'Capital_replay': 0}))


if __name__ == '__main__':
    main()
