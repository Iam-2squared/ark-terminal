"""Exclusive, claim+actual-GET guarded independent D/DR reconstruction runner."""

from pathlib import Path
from datetime import datetime, timedelta, timezone
import argparse
import gzip
import hashlib
import json
import os
import uuid

from independent_engine import run_profile
from independent_pre_main import load_intelligence


ROOT = Path('/workspace/scratch/f3d0aa747c89')
STRATEGY_PARENT = '710656491be06235901b45c50a8b5cbd714ba4eb'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    with gzip.open(path, 'rt') as reader:
        return [json.loads(line) for line in reader]


def exclusive_bytes(path, payload):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp.' + uuid.uuid4().hex)
    with temp.open('xb') as writer:
        writer.write(payload)
        writer.flush()
        os.fsync(writer.fileno())
    assert temp.read_bytes() == payload
    os.link(temp, path)  # Atomic exclusive publication; an existing path fails.
    temp.unlink()
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def save(path, data):
    payload = (json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    assert json.loads(payload) == data
    exclusive_bytes(path, payload)


def gzsave(path, data):
    raw = ''.join(json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n'
                  for row in data).encode()
    compressed = gzip.compress(raw, mtime=0)
    assert gzip.decompress(compressed) == raw
    decoded = [json.loads(line) for line in gzip.decompress(compressed).splitlines()]
    assert len(decoded) == len(data) and decoded == data
    exclusive_bytes(path, compressed)
    assert gzip.decompress(Path(path).read_bytes()) == raw
    return {'record_N': len(data), 'raw_sha256': hashlib.sha256(raw).hexdigest(),
            'compressed_sha256': hashlib.sha256(compressed).hexdigest(), 'compression_mtime': 0}


def now():
    return datetime.now(timezone(timedelta(hours=9))).isoformat()


def verify_map(files):
    assert isinstance(files, dict) and files
    for path, digest in files.items():
        location = Path(path)
        if not location.is_absolute():
            location = ROOT / location
        assert sha(location) == digest, ('PRECLAIM_FILE_HASH_CHANGED', path)


def run(arm, claim_path, receipt_path, output):
    assert arm in ('D', 'DR')
    claim, receipt = read(claim_path), read(receipt_path)
    assert claim['phase'] == 'R9_INDEPENDENT_RECONSTRUCTION'
    assert claim['strategy_parent'] == STRATEGY_PARENT
    assert claim['counts'][f'independent_{arm}_reconstruction_max'] == 1
    assert receipt['status'] == 'PASS' and receipt['verified'] is True
    assert receipt['claim_sha256'] == sha(claim_path)
    assert receipt.get('commit') and receipt.get('tree')
    files = claim['independent_input_files']
    own_current = str(ROOT / 'r1_work/independent/FOUR_HEAD_CURRENT.jsonl.gz')
    own_reference = str(ROOT / 'r1_work/independent/FOUR_HEAD_REFERENCES.json')
    assert own_current in files and own_reference in files
    verify_map(files)
    verify_map(claim['code_files'])
    must_be_frozen = ('independent_harness.py', 'independent_engine.py', 'independent_pre_main.py')
    assert all(any(Path(path).name == name for path in claim['code_files']) for name in must_be_frozen)
    output = Path(output).resolve()
    if 'output_dirs' in claim:
        assert output == Path(claim['output_dirs'][arm]).resolve()
    assert not (output / 'STARTED.json').exists() and not (output / 'COMPLETE.json').exists()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / 'r1_work/inputs/RUNTIME_INPUT_MANIFEST.json'
    assert str(manifest_path) in files
    manifest = read(manifest_path)
    for value in manifest['inputs'].values():
        if 'sha256' in value:
            assert sha(value['path']) == value['sha256']
        elif 'code_files' in value:
            for name, digest in value['code_files'].items():
                assert sha(Path(value['path']) / name) == digest
    save(output / 'STARTED.json', {
        'JST': now(), 'arm': arm, 'run_id': claim.get('run_id'), 'strategy_parent': STRATEGY_PARENT,
        'claim_sha256': sha(claim_path), 'actual_GET_receipt_sha256': sha(receipt_path),
        'actual_GET_HEAD': receipt['commit'], 'independent_reconstruction_invocation': 1,
        'rerun_permitted': False, 'new_fit': 0, 'primary_implementation_import_N': 0,
        'protected100_decision_inputs': False, 'teacher_decision_inputs': False,
    })
    inputs = manifest['inputs']
    native = rows(inputs['native_stream']['path'])
    books = {row['entry_id']: row for row in rows(inputs['market_execution_books']['path'])}
    tables = read(inputs['V5_arrival_tables']['path'])
    intelligence = load_intelligence()
    reconstructed = run_profile(arm, native, books, tables, intelligence)
    artifacts = {name: gzsave(output / (name.upper() + '.jsonl.gz'), values)
                 for name, values in reconstructed.items()}
    result = {'arm': arm, 'status': 'RECONSTRUCTION_COMPLETE', 'new_fit': 0,
              'primary_implementation_import_N': 0, 'independent_reconstruction_invocation': 1,
              'artifact_counts': {name: len(value) for name, value in reconstructed.items()},
              'economic_or_quality_evaluation_executed_here': False,
              'unresolved_day_N': sum(d['status'] != 'COMPLETE' for d in reconstructed['daily'])}
    save(output / 'RESULT.json', result)
    save(output / 'COMPLETE.json', {'JST': now(), 'arm': arm, 'claim_sha256': sha(claim_path),
         'STARTED_sha256': sha(output / 'STARTED.json'), 'RESULT_sha256': sha(output / 'RESULT.json'),
         'artifacts': artifacts, 'rerun_permitted': False})
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('arm')
    parser.add_argument('--claim', required=True)
    parser.add_argument('--actual-get', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.arm, args.claim, args.actual_get, args.output)
