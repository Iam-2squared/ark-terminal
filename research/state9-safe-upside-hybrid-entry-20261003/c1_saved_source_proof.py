"""Restore and verify already-exposed saved sources. No provider, fit, label or State run.

Only the session/code pairs present in the frozen R1 row manifest are exported.
The encryption key is used by openssl inside Actions and never enters Python.
"""
import argparse
import collections
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

class Lex(str):
    pass

def digest(b):
    return hashlib.sha256(b).hexdigest()

def parse(b):
    return json.loads(b, parse_float=Lex, parse_int=Lex,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))

def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    b = (json.dumps(obj, sort_keys=True, separators=(',', ':')) + '\n').encode()
    p.write_bytes(gzip.compress(b, mtime=0) if p.suffix == '.gz' else b)

def minute(s):
    return int(s[:2]) * 60 + int(s[3:])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--archives', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--grid', required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = Path(args.out)
    here = Path(__file__).resolve().parent
    gridbytes = Path(args.grid).read_bytes()
    assert digest(gridbytes) == '54f7dbb8bd0c9f8974ccccb7a949c0b7ebf0bbe46581be7778f1607f9d9d8cb6'
    rows = json.loads(gridbytes)
    rawfile = root / 'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz'
    assert digest(rawfile.read_bytes()) == '37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b'
    raw = parse(gzip.decompress(rawfile.read_bytes()))
    ledgerfile = root / 'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/source-ledger.json'
    ledger = json.loads(ledgerfile.read_bytes())
    pins = {(x['session'], x['kind']): x['sha256'] for x in ledger}
    split = json.loads((root / 'docs/evidence/phase57-behavior-expansion-v1/04_session_split_manifest.json').read_bytes())
    allowed = set(split['intradayDevelopment'])
    blocked = set(split['commonHoldout']) | set(split['excluded'])
    assert not allowed & blocked
    by_opp = collections.defaultdict(list)
    for r in rows:
        by_opp[r['opportunity']].append(r)
        assert r['session'] in allowed and r['session'] not in blocked
        assert r['computedThroughMinute'] is None or r['computedThroughMinute'] < r['minute']
    wanted = collections.defaultdict(set)
    for oid, rr in by_opp.items():
        day, code = oid.split('|')
        assert day == rr[0]['session'] and oid in raw
        wanted[day].add(code)
        prev = raw[oid]['previousSession']
        if prev is not None:
            assert prev in allowed and prev < day
            wanted[prev].add(code)
    originals = {}
    receipts = []
    archives = sorted(Path(args.archives).rglob('*.tar.gz.enc'))
    assert archives, 'NO_SAVED_ARCHIVES'
    for archive in archives:
        sha_text = archive.with_name(archive.name + '.sha256').read_text().strip()
        expected = (json.loads(sha_text) if sha_text.startswith('"') else sha_text).split()[0]
        assert digest(archive.read_bytes()) == expected, 'ENCRYPTED_ARCHIVE_HASH'
        proc = subprocess.Popen(['openssl', 'enc', '-d', '-aes-256-cbc', '-pbkdf2', '-iter', '200000',
            '-pass', 'env:JQUANTS_API_KEY', '-in', str(archive)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        seen = []
        try:
            with tarfile.open(fileobj=proc.stdout, mode='r|gz') as tar:
                for member in tar:
                    if not member.isfile():
                        continue
                    parts = Path(member.name).parts
                    day = next((x for x in parts if len(x) == 10 and x[4:5] == '-' and x[7:8] == '-'), None)
                    # Metadata headers are inspected; unapproved member bodies are never read or extracted.
                    if day not in wanted or member.name.rsplit('/', 1)[-1] not in ('minute-pages.json', 'daily-pages.json'):
                        continue
                    assert day in allowed and day not in blocked, 'PROTECTED_BODY_OPEN'
                    kind = member.name.rsplit('/', 1)[-1].split('-')[0]
                    b = tar.extractfile(member).read()
                    assert digest(b) == pins[day, kind], 'ORIGINAL_PAGE_WRAPPER_SHA'
                    selected = []
                    wrapper = json.loads(b)
                    for page in wrapper:
                        response = page['responseText']
                        assert digest(response.encode()) == page['responseSha256'], 'ORIGINAL_RESPONSE_SHA'
                        for ordinal, r in enumerate(parse(response)['data']):
                            assert r['Date'] == day
                            if r['Code'] in wanted[day]:
                                selected.append({**r, '_source': {'response_SHA256': page['responseSha256'],
                                    'row_ordinal': ordinal, 'wrapper_SHA256': pins[day, kind]}})
                    key = (day, kind)
                    if key in originals:
                        assert originals[key] == selected, 'DUPLICATE_SOURCE_CONTRADICTION'
                    originals[key] = selected
                    seen.append({'date': day, 'kind': kind, 'selected_rows': len(selected), 'sha256': digest(b)})
                    del b, wrapper
            ret = proc.wait()
            assert ret == 0, 'SAVED_ARCHIVE_DECRYPT_FAILED'
        finally:
            if proc.poll() is None:
                proc.terminate()
            proc.stdout.close()
        receipts.append({'archive_SHA256': expected, 'members_opened': seen})
    missing = [dict(date=d, kind=k) for d in wanted for k in ('minute', 'daily') if (d, k) not in originals]
    assert not missing, 'SAVED_RAW_MEMBERS_NOT_AVAILABLE'
    indexed = {}
    for (day, kind), values in originals.items():
        for r in values:
            key = (day, r['Code'], r.get('Time') if kind == 'minute' else kind)
            assert key not in indexed, 'DUPLICATE_RAW_TIME'
            indexed[key] = r
    checks = 0
    selected_sources = {}
    for oid, rr in by_opp.items():
        day, code = oid.split('|')
        path = raw[oid]
        assert path['sourceHash'] == pins[day, 'minute'], 'CURRENT_SOURCE_IDENTITY'
        for field, d in [('today', day), ('previous', path['previousSession'])]:
            for bar in path[field]:
                t = int(Decimal(bar[0]))
                r = indexed[d, code, f'{t // 60:02d}:{t % 60:02d}']
                for i, key in enumerate(('O', 'H', 'L', 'C', 'Vo', 'Va'), 1):
                    assert Decimal(bar[i]) == Decimal(r[key]), 'FLOAT_COMPACT_VALUE_NOT_EXACT'
                    checks += 1
        cur = [r for r in originals[day, 'minute'] if r['Code'] == code]
        prevday = path['previousSession']
        prev = [r for r in originals[prevday, 'minute'] if r['Code'] == code] if prevday else []
        max_intent = max(x['minute'] for x in rr)
        prefix = [r for r in cur if minute(r['Time']) + 1 <= max_intent]
        selected_sources[oid] = dict(session=day, symbol=code, previous_session=prevday,
            current_prefix=prefix, previous=prev,
            current_daily=indexed.get((day, code, 'daily')),
            previous_daily=indexed.get((prevday, code, 'daily')),
            max_candidate_intent=max_intent,
            raw_received_at_history='UNKNOWN', assumed_available_at='bar_end')
    # Private source artifact only; this file must never be committed to GitHub.
    write(out / 'PRIVATE_SELECTED_SOURCE_TOKENS.json.gz', selected_sources)
    receipt = dict(status='ORIGINAL_SAVED_SOURCE_PROOF_PASS', candidate_rows=len(rows),
        opportunities=len(by_opp), sessions=len({r['session'] for r in rows}),
        exact_numeric_value_checks=checks, wrapper_sources=len(originals),
        source_dates=len(wanted), duplicate_candidate_rows=len(rows)-len({r['id'] for r in rows}),
        future_input_violations=0, protected_bodies_opened=0, provider_requests=0,
        new_model_fits=0, new_labels=0, State_runs=0, old_policy_replays=0,
        actual_known_at='UNKNOWN', bar_end_availability='RESEARCH_ASSUMPTION',
        private_source_sha256=digest((out / 'PRIVATE_SELECTED_SOURCE_TOKENS.json.gz').read_bytes()),
        private_source_bytes=(out / 'PRIVATE_SELECTED_SOURCE_TOKENS.json.gz').stat().st_size,
        encrypted_archive_receipts=receipts)
    write(out / 'ORIGINAL_SAVED_SOURCE_PROOF.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'encrypted_archive_receipts'}))

if __name__ == '__main__':
    main()
