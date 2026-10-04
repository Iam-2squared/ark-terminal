"""Byte-only archive handoff. Never recompute completed inputs or research outputs."""
from control import *
import zipfile


def main():
    basis = read(WORK / 'latest_basis.json')
    result = read(OUT / 'WINNER_AND_NEXT_BOTTLENECK.json')
    source = read(OUT / 'INPUT_BYTE_FREEZE.json')
    authority = read(OUT / 'AUTHORITY_FREEZE.json')
    files = {}
    data = {}
    pin_names = {'COMMON_EVAL_MASK.jsonl.gz', 'TEACHER_SUPPORT_LEDGER.jsonl.gz',
                 'TRAIN_MAPPED_SCORES.jsonl.gz', 'RANK_NATIVE_RUNTIME.jsonl.gz'}
    for row in source['files']:
        path = PRIOR / row['path']
        payload = path.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == row['sha256'] and len(payload) == row['bytes']
        name = row['path']
        if name.startswith('private/') and path.name not in pin_names:
            name = 'lineage/v7/' + name
        assert name not in data
        data[name] = payload
        files[name] = {'bytes': len(payload), 'sha256': row['sha256'],
                       'source': 'immutable v7 private delivery', 'original_path': row['path']}
    for path in sorted(PRIVATE.iterdir()):
        assert path.is_file() and path.suffix in ('.gz', '.json')
        name = 'private/' + path.name
        assert name not in data
        payload = path.read_bytes()
        data[name] = payload
        files[name] = {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
                       'source': 'completed v8R1 execution; single-execution marker or saved ledger'}
    manifest = {
        'exact_jst': now(), 'cycle': 'capital-v8r1-cash-constrained-online-max3-20261005-v1',
        'branch': BRANCH, 'basis_HEAD': basis['HEAD'], 'basis_tree': basis['tree'],
        'GitHub_reference': f"https://github.com/Iam-2squared/ark-terminal/tree/{basis['HEAD']}/" + str(OUT.relative_to(ROOT)),
        'source_byte_reuse_only': True, 'source_manifest_sha256': sha(OUT / 'INPUT_BYTE_FREEZE.json'),
        'source_v7_delivery_sha256': authority['sha256']['docs/evidence/capital-v7-rank-native-max3-20261005-v1/PRIVATE_DELIVERY_RECEIPT.json'],
        'rank_contract_sha256': authority['sha256']['docs/evidence/capital-rank-bigwinner-vnext-20261005-v1/SELECTED_RANK_CONTRACT.json'],
        'pP_stream_sha256': files['inputs/movement/MOVE_P5_SCORE_STREAM.jsonl.gz']['sha256'],
        'band_map_sha256': authority['sha256']['docs/evidence/capital-v7-rank-native-max3-20261005-v1/RANK_NATIVE_BAND_MAP.json'],
        'report_sha256': sha(OUT / 'REPORT_FINAL-ja.md'),
        'main_claim_sha256': sha(OUT / 'MAIN_REPLAY_CLAIM.json'),
        'input_authority': 'GitHub freezes; attached files must pass all saved hashes',
        'status': result['status'], 'selectedRankCandidate': 'EXISTING_MOVE_P5',
        'selectedCapitalCandidate': result['selectedCapitalCandidate'], 'diagnosticArm': result['diagnosticArm'],
        'NEXT_BOTTLENECK': result['NEXT_BOTTLENECK'], 'counts': result['counts'], 'Safety': SAFETY,
        'Exposure': 'ITERATIVE_DEVELOPMENT_EVIDENCE', 'fresh_OOS_claim': False, 'productionReady': False,
        'contains_repository_backed_code_reports': False,
        'tables_and_public_research_evidence': 'GitHub only; not duplicated in Library',
        'files': files,
    }
    payload = (json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode()
    delivery_dir = ROOT.parent / 'deliverables'
    delivery_dir.mkdir(exist_ok=True)
    delivery = delivery_dir / 'Ark_Capital_v8R1_Cash_Constrained_Online_MAX3_20261005_PRIVATE.zip'
    with zipfile.ZipFile(delivery, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr('MANIFEST.json', payload)
        for name, payload_ in data.items():
            archive.writestr(name, payload_)
    with zipfile.ZipFile(delivery) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read('MANIFEST.json')) == manifest
        for name, row in files.items():
            payload_ = archive.read(name)
            assert len(payload_) == row['bytes'] and hashlib.sha256(payload_).hexdigest() == row['sha256']
    saved = {'exact_jst': now(), 'filename': delivery.name, 'bytes': delivery.stat().st_size,
             'sha256': sha(delivery), 'manifest_sha256': hashlib.sha256(payload).hexdigest(),
             'member_N': len(files) + 1, 'readback_all_member_hashes_PASS': True,
             'contains_repository_backed_code_reports': False, 'manifest': manifest,
             'GitHub_reference': manifest['GitHub_reference']}
    save(OUT / 'PRIVATE_PACK_MANIFEST.json', saved)
    print(json.dumps({k: saved[k] for k in ['filename', 'bytes', 'sha256', 'member_N', 'readback_all_member_hashes_PASS']}))


if __name__ == '__main__':
    main()
