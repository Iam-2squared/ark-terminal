#!/usr/bin/env python3
"""Restore saved MODE B objects under an OS-installed inspection registration.

This is an owner administrator's transfer/metadata tool, not a market Authority.
It cannot fit, create a source profile, install a runtime grant, or read numbers.
GitHub authentication authorizes transport only; it never authorizes research.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ark_selector_v2.contracts import FLAGS, code_hash, configuration_hash, digest, registry
from ark_selector_v2.exact_math import V2Error
from ark_selector_v2.host_channel import check_owner_file
from ark_selector_v2.source_adapter import BoundedStream

REGISTRATION = Path('/etc/ark-selector-v2/research-registration.json')


def selected_objects(scope: dict[str, Any], tree: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve logical inventory keys by immutable git blob identity, never guesses."""
    if scope.get('schema') != 'ARK_V2_MODE_B_SOURCE_SCOPE_DRAFT_V1' or scope.get('validation_final_teachers_included') is not False:
        raise V2Error('INSPECTION_SCOPE_SCHEMA')
    if tree.get('truncated') is not False:
        raise V2Error('COMPLETE_CANONICAL_SOURCE_TREE_REQUIRED')
    result = []
    for source in scope['source_objects']:
        matches = [r for r in tree['tree'] if r.get('type') == 'blob' and r['sha'] == source['original_git_blob']]
        if len(matches) != 1 or matches[0]['size'] != source['bytes']:
            raise V2Error('MISSING_OR_AMBIGUOUS_CANONICAL_SOURCE_BLOB')
        row = matches[0]
        path = PurePosixPath(row['path'])
        if path.is_absolute() or '..' in path.parts or '\\' in row['path'] or not row['path'].startswith('raw/'):
            raise V2Error('UNSAFE_CANONICAL_SOURCE_PATH')
        purposes = source['requested_dates_by_purpose']
        if not set(purposes) <= {'HISTORY', 'FIT_FEATURE', 'CAL_FEATURE', 'FIT_TEACHER', 'CAL_TEACHER'}:
            raise V2Error('EVALUATION_PURPOSE_IN_SOURCE_INSPECTION')
        result.append({**source, 'repository': 'Iam-2squared/J-quants-E', 'repository_path': row['path'],
                       'local_path': row['path'], 'inspection_dates': sorted(set(sum(purposes.values(), [])))})
    if len(result) != 24 or len({r['local_path'] for r in result}) != 24:
        raise V2Error('FIXED_24_OBJECT_SCOPE_REQUIRED')
    return result


def installed_registration() -> dict[str, Any]:
    for parent in reversed(REGISTRATION.parents):
        check_owner_file(parent, 0, directory=True)
    check_owner_file(REGISTRATION, 0)
    record = json.loads(REGISTRATION.read_text('utf-8'))
    if record.get('schema') != 'ARK_V2_OWNER_SOURCE_INSPECTION_REGISTRATION_V1':
        raise V2Error('SOURCE_INSPECTION_REGISTRATION_SCHEMA')
    if any(record.get(flag) is not False for flag in FLAGS):
        raise V2Error('SOURCE_INSPECTION_EXECUTION_FLAG')
    if record.get('test_only') is not False or record.get('numeric_parsing_allowed') is not False:
        raise V2Error('METADATA_INSPECTION_ONLY')
    if record['hashes'] != {'code': code_hash(), 'config': configuration_hash(), 'schema': digest(registry())}:
        raise V2Error('SOURCE_INSPECTION_CODE_CONFIG_SCHEMA_DRIFT')
    if record['source_scope_sha256'] != digest(record['source_objects']):
        raise V2Error('SOURCE_INSPECTION_SCOPE_DRIFT')
    if not record.get('owner_instruction_sha256') or not record.get('reuse_overlay_sha256'):
        raise V2Error('OWNER_INSTRUCTION_AND_PURPOSE_OVERLAY_REQUIRED')
    for name, pin in [('owner_instruction_file', 'owner_instruction_sha256'), ('reuse_overlay_file', 'reuse_overlay_sha256')]:
        evidence = Path(record[name])
        for parent in reversed(evidence.parents):
            check_owner_file(parent, 0, directory=True)
        check_owner_file(evidence, 0)
        data = evidence.read_bytes()
        actual = hashlib.sha256(data).hexdigest() if name == 'owner_instruction_file' else digest(json.loads(data))
        if actual != record[pin]:
            raise V2Error('OWNER_INSPECTION_EVIDENCE_PIN_MISMATCH')
    return record


def source_path(root: Path, relative: str) -> Path:
    path = root / relative
    if not root.is_absolute() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise V2Error('SOURCE_INSPECTION_SYMLINK')
    if not path.resolve().is_relative_to(root.resolve()):
        raise V2Error('SOURCE_INSPECTION_PATH_ESCAPE')
    return path


def verify_bytes(path: Path, source: dict[str, Any]) -> None:
    sha = hashlib.sha256()
    blob = hashlib.sha1(('blob ' + str(source['bytes']) + '\0').encode())
    count = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            count += len(chunk)
            if count > source['bytes']:
                raise V2Error('SAVED_SOURCE_SIZE_MISMATCH')
            sha.update(chunk)
            blob.update(chunk)
    if count != source['bytes'] or sha.hexdigest() != source['source_sha256'] or blob.hexdigest() != source['original_git_blob']:
        raise V2Error('SAVED_SOURCE_HASH_OR_BLOB_MISMATCH')


def restore_one(root: Path, source: dict[str, Any], credential: str, worker_gid: int) -> None:
    if os.getuid() != 0:
        raise V2Error('SOURCE_RESTORE_REQUIRES_OWNER_ADMINISTRATOR')
    target = source_path(root, source['local_path'])
    if target.exists():
        verify_bytes(target, source)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    for parent in [target.parent, *target.parent.parents]:
        if parent.is_relative_to(root):
            os.chown(parent, 0, worker_gid)
            os.chmod(parent, 0o750)
    url = 'https://api.github.com/repos/' + source['repository'] + '/git/blobs/' + source['original_git_blob']
    # A token is an existing transport credential, not an owner-use assertion.
    request = Request(url, headers={'Authorization': 'Bearer ' + credential,
        'Accept': 'application/vnd.github.raw+json', 'User-Agent': 'ark-v2-saved-object-restorer'})
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.restore-', delete=False) as output:
            temporary = Path(output.name)
            with urlopen(request, timeout=45) as response:
                if response.geturl().split('/')[2] != 'api.github.com':
                    raise V2Error('UNEXPECTED_SAVED_SOURCE_REDIRECT')
                count = 0
                while True:
                    chunk = response.read(min(1024 * 1024, source['bytes'] + 1 - count))
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > source['bytes']:
                        raise V2Error('SAVED_SOURCE_SIZE_MISMATCH')
                    output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        verify_bytes(temporary, source)
        os.chown(temporary, 0, worker_gid)
        os.chmod(temporary, 0o640)
        os.link(temporary, target)  # Exclusive publication; never replace originals.
    except HTTPError as exc:
        raise V2Error('AUTHENTICATED_SAVED_SOURCE_HTTP_' + str(exc.code)) from None
    except URLError:
        raise V2Error('AUTHENTICATED_SAVED_SOURCE_TRANSPORT_FAILED') from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def metadata_scan(path: Path, source: dict[str, Any], limit: int) -> dict[str, Any]:
    """Date-first metadata only; no price, label, or activity conversion."""
    verify_bytes(path, source)
    dates = set(source['inspection_dates'])
    counts = {day: 0 for day in dates}
    seen: set[tuple[str, str]] = set()
    skipped = 0
    with gzip.open(path, 'rb') as compressed:
        bounded = BoundedStream(compressed, limit)
        with io.TextIOWrapper(io.BufferedReader(bounded), encoding='utf-8-sig', newline='') as text:
            reader = csv.DictReader(text)
            header = reader.fieldnames
            if not header or len(header) != len(set(header)) or not {'Date', 'Code'} <= set(header):
                raise V2Error('SOURCE_INSPECTION_DATE_IDENTITY_HEADER')
            for row in reader:
                if None in row or any(v is None for v in row.values()):
                    raise V2Error('SOURCE_INSPECTION_MALFORMED_ROW')
                day = row['Date']
                if day not in dates:
                    skipped += 1
                    continue
                key = day, row['Code']
                if key in seen:
                    raise V2Error('SOURCE_INSPECTION_DUPLICATE_DATED_IDENTITY')
                seen.add(key)
                counts[day] += 1
                if len(seen) > 1_000_000:
                    raise V2Error('SOURCE_INSPECTION_IDENTITY_BOUND')
    return {'source_sha256': source['source_sha256'], 'header': header, 'date_record_counts': counts,
            'other_date_records_skipped_before_identity': skipped, 'numeric_records_parsed': 0,
            'source_profile_adopted': False, 'units_basis_known_at_verified': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['verify', 'restore', 'inspect-metadata'])
    parser.add_argument('--output', required=True, help='new private receipt path outside Git')
    args = parser.parse_args()
    try:
        record = installed_registration()
        output = Path(args.output).resolve()
        if output.exists() or any((parent / '.git').exists() for parent in (output.parent, *output.parents)):
            raise V2Error('NEW_PRIVATE_RECEIPT_OUTSIDE_GIT_REQUIRED')
        if not output.is_relative_to(Path(record['output_root'])):
            raise V2Error('INSPECTION_RECEIPT_OUTSIDE_OWNER_OUTPUT')
        root = Path(record['source_root'])
        credential = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        rows = []
        for source in record['source_objects']:
            target = source_path(root, source['local_path'])
            if args.operation == 'restore' and not target.exists():
                if not credential:
                    raise V2Error('AUTHENTICATED_PRIVATE_GITHUB_BINARY_TRANSPORT_NOT_CONFIGURED')
                restore_one(root, source, credential, record['worker_gid'])
            row = {'source_sha256': source['source_sha256'], 'present': target.is_file(), 'verified': False}
            if target.is_file():
                verify_bytes(target, source)
                row['verified'] = True
                if args.operation == 'inspect-metadata':
                    row['metadata'] = metadata_scan(target, source, record['inspection_max_uncompressed_bytes'])
            rows.append(row)
        receipt = {'schema': 'ARK_V2_SAVED_SOURCE_INSPECTION_RECEIPT_V1', 'operation': args.operation,
                   'registration_sha256': digest(record), 'objects': rows,
                   'objects_verified': sum(row['verified'] for row in rows),
                   'status': 'SOURCE_BYTES_VERIFIED' if all(row['verified'] for row in rows) else 'BLOCKED_SOURCE_BYTES_NOT_MOUNTED',
                   'numeric_records_parsed': 0, 'market_candidates': 0, 'market_fits': 0,
                   'market_calibrations': 0, **{flag: False for flag in FLAGS}}
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write('\n')
        print(json.dumps({key: receipt[key] for key in ['status', 'objects_verified', 'numeric_records_parsed']}))
        return 0 if receipt['objects_verified'] == 24 else 2
    except (V2Error, FileNotFoundError, FileExistsError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(exc), 'numeric_records_parsed': 0,
                          'market_fits': 0, **{flag: False for flag in FLAGS}}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
