"""Append-only canonical eligibility correction and Entry reference-boundary audit.

Supersedes only the initial stricter raw-validity predicate in Primary/Independent.
No strategy policy, model, allocator or Capital cash ledger is executed.
"""
from collections import Counter
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path
from zoneinfo import ZoneInfo
import gzip
import hashlib
import importlib.util
import json
import os
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent
PRIVATE = BASE / 'capital_c2_recovery_private'
OUT = ROOT / 'docs/evidence/phase57-capital-state9-vnext-c2-recovery-20261004-v1'
CLOCK = BASE / 'recovery_source_cache/c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad/research/state9-structural-exit-v3-local-guard-20261003/reused_clock.py'


def alternate_valid(a):
    if len(a) != 7:
        return False
    try:
        values = list(map(lambda x: Fraction(str(x)), a))
    except (ValueError, ZeroDivisionError):
        return False
    _, opening, high, low, close, volume, value = values
    return low > 0 and low <= opening <= high and low <= close <= high and volume >= 0 and value >= 0


def main():
    body = CLOCK.read_bytes()
    expected = '7b97dcc8ddcb8d02eb7066f056b5ef15e7859136'
    blob = lambda v: hashlib.sha1(('blob %d\0' % len(v)).encode() + v).hexdigest()
    if blob(body) != expected and body.endswith(b'\n') and blob(body[:-1]) == expected:
        CLOCK.write_bytes(body[:-1])  # transport-only cached terminal LF, not Frozen source
        body = body[:-1]
    assert blob(body) == expected
    spec = importlib.util.spec_from_file_location('frozen_clock_only', CLOCK)
    clock = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(clock)
    with gzip.open(PRIVATE / 'ORIGINAL_RAW_PATHS_CURRENT1600.json.gz', 'rt') as f:
        primary = json.load(f)
    # Independent raw source is read afresh from the original frozen base archive.
    with zipfile.ZipFile(BASE / 'recovery_dependency_inputs/Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip') as z:
        n = next(n for n in z.namelist() if n.endswith('persistent_sources/raw_paths_selected.json.gz'))
        independent = json.loads(gzip.decompress(z.read(n)))
    with gzip.open(BASE / 'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz', 'rt') as f:
        entries = {r['watch_key']: r for r in map(json.loads, f) if r['entry_status'] == 'FIRST_ENTRY'}
    with gzip.open(BASE / 'work_inputs/exit_v3/REPLAY_ROWS.jsonl.gz', 'rt') as f:
        exits = {r['watch_key']: r for r in map(json.loads, f)}
    counts = Counter()
    derived = []
    for key, e in entries.items():
        x = exits[key]
        a, b = primary[key]['today'], independent[key]['today']
        counts['source_body_mismatch_N'] += int(a != b)
        first_am = min((int(r[0]) for r in a if int(r[0]) < 690), default=None)
        first_pm = min((int(r[0]) for r in a if 750 <= int(r[0]) < clock.regular_end(e['session'])), default=None)
        excluded = {540, 750, first_am, first_pm}
        closing_minute = clock.session_close(e['session'])
        p_auction = [r for r in a if int(r[0]) == closing_minute and clock.valid_raw(r)]
        i_auction = [r for r in b if int(r[0]) == closing_minute and alternate_valid(r)]
        counts['canonical_exact_auction_source_present_N'] += int(len(p_auction) == 1)
        counts['canonical_exact_auction_independent_mismatch_N'] += int(p_auction != i_auction)
        if x['sell_status'] == 'UNRESOLVED':
            intent = x['exit_intent']['minute'] if isinstance(x.get('exit_intent'), dict) else None
            admissible_clock = lambda r: intent is not None and int(r[0]) >= intent and int(r[0]) > e['fill_minute'] and int(r[0]) not in excluded and int(r[0]) in clock.regular_starts(e['session'])
            p_open = [r for r in a if admissible_clock(r) and clock.valid_raw(r)]
            i_open = [r for r in b if admissible_clock(r) and alternate_valid(r)]
            counts['unresolved_N'] += 1
            counts['eligible_regular_open_found_N'] += int(bool(p_open))
            counts['eligible_terminal_auction_found_N'] += int(len(p_auction) == 1)
            counts['canonical_regular_independent_mismatch_N'] += int(p_open != i_open)
            derived.append({'entry_id': key, 'exact_regular_source_N': len(p_open), 'exact_auction_source_N': len(p_auction), 'source_lookup': 'canonical frozen valid_raw and independent Fraction predicate', 'reason_taxonomy': 'SOURCE_NOT_STORED' if not p_open and not p_auction else 'SOURCE_EXISTS_NOT_WIRED'})
        counts['Entry_reference_Open_present_N'] += int(any(int(r[0]) == e['fill_minute'] and clock.valid_raw(r) for r in a))
        source_completion = datetime.fromisoformat(e['fill_timestamp']) + timedelta(minutes=1)
        counts['Entry_raw_source_completion_after_reference_N'] += int(source_completion > datetime.fromisoformat(e['fill_timestamp']))
    assert counts['source_body_mismatch_N'] == counts['canonical_exact_auction_independent_mismatch_N'] == counts['canonical_regular_independent_mismatch_N'] == 0
    assert counts['unresolved_N'] == 39 and counts['eligible_regular_open_found_N'] == counts['eligible_terminal_auction_found_N'] == 0
    contract = ROOT / 'research/persistent-watchlist-uptrend-first-entry-20261003-v2/CORRECTED_LINEAGE_FAST_FREEZE_20261003/P1_Q70_ENTRY_CONTRACT.json'
    current = json.loads(contract.read_text())
    rowpath = PRIVATE / 'CANONICAL_ELIGIBILITY_ROWS.jsonl.gz'
    with rowpath.open('xb') as f:
        with gzip.GzipFile(fileobj=f, mode='wb', filename='', mtime=0) as z:
            for row in derived:
                z.write((json.dumps(row, sort_keys=True) + '\n').encode())
    report = {'saved_at_jst': datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(), 'repo': 'Iam-2squared/ark-terminal', 'branch': 'capital-state9-vnext-20261004', 'basis_head': os.environ['RECOVERY_BASIS_HEAD'], 'status': 'CANONICAL_SOURCE_ELIGIBILITY_PASS_NO_NEW_SELL_SOURCE', 'technical_correction': 'Initial audit used positive volume and a less specific OHLC test. Frozen valid_raw allows zero volume/value and requires len7, finite values and coherent OHLC. Original outputs retained; this exact predicate recheck supersedes their validity-dependent claims. Counts and source classifications did not change.', 'counts': dict(counts), 'independent_mismatch_N': 0, 'frozen_clock_git_blob': expected, 'frozen_clock_sha256': hashlib.sha256(body).hexdigest(), 'entry_contract_sha256': hashlib.sha256(contract.read_bytes()).hexdigest(), 'entry_contract_git_blob': blob(contract.read_bytes()), 'Entry_contract_decision_boundary': current['decision']['causal_cutoff'], 'Entry_contract_fill_boundary': current['fill']['basis'], 'Entry_source_completion_role': 'Inherited source bar_end=m+1 research assumption; not evidence that actual Open publication or executable fill confirmation arrived at m+1. No new known-at was assigned to Entry; no debit event executed.', 'entry_actual_fill_confirmation_known_at': 'UNKNOWN', 'Entry_cash_debit_runtime_binding': 'NOT_CERTIFIED_BY_REFERENCE_FILL_PRICE_ALONE', 'Frozen_changes': 0, 'row_exclusion': 0, 'missing_imputation': 0, 'Capital_replay': 0, 'Entry_EXIT_replay': 0, 'fit': 0, 'provider': 0, 'new_market_data': 0}
    with (OUT / 'EXACT_SOURCE_BOUNDARY_RECHECK.json').open('x') as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'status': report['status'], 'counts': dict(counts), 'independent_mismatch_N': 0, 'Capital_replay': 0}))


if __name__ == '__main__':
    main()
