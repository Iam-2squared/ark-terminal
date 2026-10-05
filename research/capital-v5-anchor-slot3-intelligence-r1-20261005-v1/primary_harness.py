"""Durable single-run harness. A claim and its actual GET receipt are mandatory."""
from datetime import datetime
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from primary_adapter import run_profile, FrozenNative
from primary_policy import ranks_from_record

STRATEGY_PARENT = '710656491be06235901b45c50a8b5cbd714ba4eb'
CODE_FILES = ('primary_policy.py', 'primary_adapter.py', 'primary_harness.py')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode()

def now():
    return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()

def read_rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]

def atomic_bytes(path, payload):
    path = Path(path)
    if path.exists():
        raise FileExistsError('IMMUTABLE_OUTPUT_EXISTS:' + str(path))
    temporary = path.with_name(path.name + '.partial')
    with temporary.open('xb') as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)

def run_claimed(claim_path, actual_get_receipt_path):
    claim_path, receipt_path = Path(claim_path).resolve(), Path(actual_get_receipt_path).resolve()
    claim = json.loads(claim_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    claim_hash = sha(claim_path)
    if claim['schema'] != 'R1_PRIMARY_EXECUTION_CLAIM_V1' or claim['arm'] not in ('OFF', 'D', 'DR'):
        raise ValueError('UNAUTHORIZED_CLAIM_SCHEMA_OR_ARM')
    if claim['scope'] != 'FULL38_CONTIGUOUS_CHAIN' or claim['strategy_parent'] != STRATEGY_PARENT:
        raise ValueError('CLAIM_SCOPE_OR_STRATEGY_PARENT_MISMATCH')
    if (receipt.get('verified') is not True or receipt.get('claim_sha256') != claim_hash
            or len(receipt.get('commit', '')) != 40 or len(receipt.get('tree', '')) != 40):
        raise ValueError('ACTUAL_GET_RECEIPT_REQUIRED')
    for filename in CODE_FILES:
        if sha(Path(__file__).with_name(filename)) != claim['code_files'][filename]:
            raise ValueError('CLAIM_CODE_HASH_MISMATCH:' + filename)
    input_manifest_path = Path(claim['input_manifest']['path']).resolve()
    if sha(input_manifest_path) != claim['input_manifest']['sha256']:
        raise ValueError('CLAIM_INPUT_MANIFEST_HASH_MISMATCH')
    manifest = json.loads(input_manifest_path.read_text())
    if manifest['strategy_parent'] != STRATEGY_PARENT:
        raise ValueError('INPUT_STRATEGY_PARENT_MISMATCH')
    inputs = manifest['inputs']
    # Source coverage diagnostics and teacher/evaluation memberships are excluded.
    keys = ('native_stream', 'market_execution_books', 'V5_arrival_tables',
            'current_four_head_intelligence', 'ordered_training_references',
            'score_reference_certification')
    for key in keys:
        if sha(inputs[key]['path']) != inputs[key]['sha256']:
            raise ValueError('CLAIM_INPUT_HASH_MISMATCH:' + key)
    certification = json.loads(Path(inputs['score_reference_certification']['path']).read_text())
    if (certification.get('status') != 'PASS' or certification.get('current_missing_N') != 0
            or certification.get('current_nonfinite_N') != 0
            or certification.get('current_four_head_available_N') != manifest['native_current_N']):
        raise ValueError('OFFICIAL_SCORE_REFERENCE_CERTIFICATION_BLOCKED')
    native = FrozenNative(inputs['V5_native_code_directory']['path'])
    for name, record in native.audit.items():
        if record['sha256'] != inputs['V5_native_code_directory']['code_files'][name + '.py']:
            raise ValueError('CLAIM_NATIVE_CODE_HASH_MISMATCH:' + name)
    output_dir = Path(claim['output_directory']).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    started = {'schema': 'R1_PRIMARY_RUN_STARTED_V1', 'run_id': claim['run_id'],
               'arm': claim['arm'], 'JST': now(), 'claim_sha256': claim_hash,
               'actual_GET_commit': receipt['commit'], 'actual_GET_tree': receipt['tree'],
               'replay_budget_consumed': 1, 'blind_rerun_permitted': False}
    atomic_bytes(output_dir / 'STARTED.json', canonical(started))
    # Failures after STARTED consume the claim; caller investigates the receipt.
    stream = read_rows(inputs['native_stream']['path'])
    books = {row['entry_id']: row for row in read_rows(inputs['market_execution_books']['path'])}
    tables = json.loads(Path(inputs['V5_arrival_tables']['path']).read_text())
    intelligence = None
    if claim['arm'] != 'OFF':
        intelligence = {row['entry_id']: row for row in read_rows(inputs['current_four_head_intelligence']['path'])}
        if len(intelligence) != len(stream) or any(row['entry_id'] not in intelligence for row in stream):
            raise ValueError('OFFICIAL_CURRENT_INTELLIGENCE_COVERAGE_BLOCKED')
        if any(not all(rank.available for rank in ranks_from_record(intelligence[row['entry_id']]))
               for row in stream):
            raise ValueError('OFFICIAL_CURRENT_INTELLIGENCE_UNAVAILABLE')
    if len({row['session'] for row in stream}) != 38:
        raise ValueError('FROZEN_38_SESSION_IDENTITY_REQUIRED')
    output = run_profile(claim['arm'], stream, books, tables, intelligence, native=native)
    # Frozen V5 main appended these authority metadata fields after run_profile.
    output['result'].update(score_stream_sha256=inputs['native_stream']['sha256'],
                            avg_funded_per_session=output['result']['funded_N'] / 38)
    artifacts = {}
    for key in ('daily', 'decisions', 'trades', 'curves', 'intents', 'token_events', 'native_proposals'):
        raw = b''.join(canonical(row) for row in output[key])
        # Verify the complete uncompressed ledger before publication.
        parsed = [json.loads(line) for line in raw.splitlines()]
        if len(parsed) != len(output[key]):
            raise ValueError('LEDGER_ROW_COUNT_MISMATCH:' + key)
        packed = gzip.compress(raw, mtime=0)
        if gzip.decompress(packed) != raw:
            raise ValueError('GZIP_ROUNDTRIP_MISMATCH')
        path = output_dir / (key.upper() + '.jsonl.gz')
        atomic_bytes(path, packed)
        artifacts[key] = {'path': str(path), 'rows': len(output[key]),
                          'raw_sha256': hashlib.sha256(raw).hexdigest(),
                          'compressed_sha256': hashlib.sha256(packed).hexdigest()}
    result_path = output_dir / 'RESULT.json'
    atomic_bytes(result_path, canonical(output['result']))
    artifacts['result'] = {'path': str(result_path), 'sha256': sha(result_path)}
    audit_path = output_dir / 'NATIVE_MODULE_AUDIT.json'
    atomic_bytes(audit_path, canonical(output['native_module_audit']))
    artifacts['native_module_audit'] = {'path': str(audit_path), 'sha256': sha(audit_path)}
    completed = {'schema': 'R1_PRIMARY_RUN_COMPLETE_V1', 'run_id': claim['run_id'], 'arm': claim['arm'],
                 'JST': now(), 'claim_sha256': claim_hash, 'actual_GET_commit': receipt['commit'],
                 'actual_GET_tree': receipt['tree'], 'replay_count': 1,
                 'status': ('COMPLETE' if len(output['daily']) == 38
                            and all(day['status'] == 'COMPLETE' for day in output['daily'])
                            else 'EXECUTION_INCOMPLETE_FAIL_CLOSED'),
                 'completed_sessions': len(output['daily']), 'artifacts': artifacts,
                 'code_files': claim['code_files'], 'input_manifest_sha256': claim['input_manifest']['sha256'],
                 'rerun_permitted': False, 'new_fits': 0, 'orders': 0,
                 'main_merge': 0, 'force_push': 0, 'candidate_policy_retuned': False}
    atomic_bytes(output_dir / 'COMPLETE.json', canonical(completed))
    return completed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--claim', required=True)
    parser.add_argument('--actual-get-receipt', required=True)
    args = parser.parse_args()
    result = run_claimed(args.claim, args.actual_get_receipt)
    print(json.dumps({key: result[key] for key in ('run_id', 'arm', 'status', 'completed_sessions', 'replay_count')}))

if __name__ == '__main__':
    main()
