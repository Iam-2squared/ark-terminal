"""Independent post-run artifact boundary, with no estimator fit or policy replay.

All metadata, data lineage and ledger semantics must pass before the frozen R41
scorer may read returns for performance aggregation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from scripts.phase57_exit_gen2_runtime_r41 import load_protocol, PROTOCOL_SHA256
from scripts.phase57_exit_gen2_preflight_r41 import source_manifest, assert_safety

ROOT = Path(__file__).resolve().parents[1]
EXECUTION_SHA = 'c031976a319130b6be379586147fff53cee6f741'
RUN_ID = 36233758837
ARTIFACT_ID = 10904078164
ARCHIVE_SHA256 = 'dbbc9e79292c8701d962a09f9ddf50d817241273fc50a5652d6b28d5580dffcd'
CI_SHA = '0d20b9aee00ff0b667f698e4c93d5f92ee057f38'
CI_RUN_ID = 36233629987


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n')


def model_inventory(gen2_root, protocol, fitted):
    specs = {s['specId'] for s in protocol['predictionSpecs']}
    expected = {(spec, fold['fold'], arm, head)
                for spec in specs for fold in protocol['split']['folds']
                for arm in protocol['entryArms'] for head in ('CONTINUATION', 'FAILURE')}
    models = fitted['models']
    actual = [(r['spec'], r['fold'], r['arm'], r['head']) for r in models]
    require(len(expected) == len(actual) == 64 and set(actual) == expected,
            'MODEL_IDENTITY_GRID')
    require([r['ordinal'] for r in models] == list(range(1, 65)), 'MODEL_ORDINALS')
    expected_files = set()
    for row in models:
        name = f"{row['spec']}__F{row['fold']}__{row['arm']}__{row['head']}.joblib"
        require(row['file'] == name, 'MODEL_FILENAME_IDENTITY')
        require(sha(gen2_root / 'models' / name) == row['sha256'], 'MODEL_BUNDLE_HASH')
        require(row['trainRows'] > 0 and row['scoreRows'] > 0 and row['featureColumns'] > 0,
                'MODEL_ROW_COUNTS')
        expected_files.add(name)
    require({p.name for p in (gen2_root / 'models').iterdir()} == expected_files,
            'MODEL_FILE_ALLOWLIST')
    journal = [json.loads(line) for line in (gen2_root / 'fit-progress.jsonl').read_text().splitlines()]
    require(len(journal) == 128, 'FIT_JOURNAL_COUNT')
    for i, row in enumerate(models):
        attempt, complete = journal[2 * i:2 * i + 2]
        require(attempt['status'] == 'FIT_ATTEMPT_STARTED'
                and complete['status'] == 'FIT_AND_BUNDLE_COMPLETED', 'FIT_JOURNAL_ORDER')
        for key in ('ordinal', 'spec', 'fold', 'arm', 'head'):
            require(attempt[key] == complete[key] == row[key], 'FIT_JOURNAL_IDENTITY')
        require(complete['sha256'] == row['sha256'], 'FIT_JOURNAL_HASH')
    return {'modelFiles': 64, 'attempts': 64, 'completed': 64,
            'uniqueSpecFoldArmHeadGrid': True, 'allBundleHashesVerified': True}


def audit_metadata(artifact_zip, artifact_root, protocol):
    require(sha(artifact_zip) == ARCHIVE_SHA256, 'ARCHIVE_DIGEST')
    gen2 = artifact_root / 'gen2'
    with zipfile.ZipFile(artifact_zip) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'DUPLICATE_ARCHIVE_MEMBERS')
        for name in names:
            require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'ARCHIVE_PATH')
            require(hashlib.sha256(archive.read(name)).hexdigest() == sha(artifact_root / name),
                    'EXTRACTED_ARCHIVE_BYTES:' + name)
    actual = {p.relative_to(artifact_root).as_posix() for p in artifact_root.rglob('*') if p.is_file()}
    require(actual == set(names), 'ARCHIVE_FILE_ALLOWLIST')
    require(not any('scorecard' in n or 'selection' in n or 'partial-failure' in n for n in names),
            'UNEXPECTED_PERFORMANCE_OR_FAILURE_ARTIFACT')
    receipt, fitted, replay, prepare = [read(gen2 / name) for name in
        ('receipt.json', 'fit-receipt.json', 'replay-receipt.json', 'prepare-receipt.json')]
    require(receipt['status'] == 'AWAITING_POST_RUN_AUDIT', 'PENDING_AUDIT_STATUS')
    require(receipt['executionHead'] == prepare['executionHead'] == EXECUTION_SHA, 'EXECUTION_SHA')
    sources = source_manifest(ROOT)
    require(receipt['sourceSha256'] == prepare['sourceSha256'] == sources, 'EXACT_EXECUTION_SOURCE')
    for name, expected in protocol['baselineSourceHashes'].items():
        require(sha(ROOT / name) == expected, 'FROZEN_BASELINE:' + name)
    for path in (ROOT / 'docs/evidence/phase57-comprehensive-exit-v1/GEN2_PRECOMMIT_R41.json',
                 gen2 / 'protocol.json', artifact_root / 'gen2-contract/protocol.json'):
        require(sha(path) == PROTOCOL_SHA256, 'PROTOCOL_BYTES')
    require(receipt['protocolSha256'] == prepare['protocolSha256'] == PROTOCOL_SHA256, 'PROTOCOL_RECEIPT')
    expected_versions = protocol['dependencies']
    for record in (receipt, prepare, read(gen2 / 'execution-identity.json')):
        for name, expected in expected_versions.items():
            actual = record['dependencies'][name]
            require(actual.startswith(expected + '.') if name == 'python' else actual == expected,
                    'FROZEN_DEPENDENCY:' + name)
    require(receipt['modelFits'] == fitted['modelFits'] == 64, 'FIT_COUNT')
    require(fitted['heads'] == ['CONTINUATION', 'FAILURE'] and fitted['predictionSpecs'] == 4,
            'PREDICTION_SPEC_HEADS')
    require(fitted['calibratedProbabilities'] is False, 'UNSUPPORTED_CALIBRATION_CLAIM')
    for record in (receipt, replay):
        require(record['candidatePoliciesReplayed'] == 16 and record['policyReplayPasses'] == 32
                and record['neutralDiagnosticReplayPasses'] == 2, 'REPLAY_COUNTS')
        require(record['runABByteIdentical'] is True and record['predictionRefits'] == 0,
                'REPLAY_REPRODUCIBILITY')
        require(record['selection'] is None and record['scorecardsProduced'] == 0,
                'PERFORMANCE_ALREADY_PRODUCED')
    for record in (receipt, fitted, prepare, read(gen2 / 'data/data-receipt.json')):
        assert_safety(record['safety'])
        require(record['providerRequests'] == record['protectedPartitionsOpened'] == 0, 'EXPOSURE')
    require(all(value is False for value in receipt['claims'].values()), 'CLAIM_BOUNDARY')
    for name, expected in prepare['preparedDataHashes'].items():
        require(sha(gen2 / name) == expected, 'PREPARED_DATA_HASH:' + name)
    require(sha(gen2 / 'oof-predictions.npz') == fitted['predictionSha256']
            == receipt['predictionSha256'], 'OOF_HASH')
    ci = read(artifact_root / 'gen2-contract/receipt.json')
    require(ci['executionHead'] == CI_SHA and int(ci['runId']) == CI_RUN_ID,
            'PREREQUISITE_CI_IDENTITY')
    require(ci['sourceSha256'] == sources and ci['protocolSha256'] == PROTOCOL_SHA256,
            'CI_EXACT_SOURCE_PROTOCOL')
    require(ci['modelFitsPerformed'] == ci['candidateReplaysPerformed'] == 0
            and ci['candidatePerformanceInspected'] is False, 'CI_PERFORMANCE_BOUNDARY')
    for suffix in ('initial', 'before-fit'):
        pre = read(artifact_root / f'gen2-logs/launch-verification-{suffix}.json')
        require(pre['status'] == 'GEN2_LAUNCH_VERIFIED_FIT_NOT_STARTED'
                and pre['executionHead'] == EXECUTION_SHA and int(pre['runId']) == RUN_ID
                and pre['requiredContractRunId'] == CI_RUN_ID, 'LAUNCH_PREFLIGHT_IDENTITY')
        require(pre['protocolSha256'] == PROTOCOL_SHA256 and pre['sourceSha256'] == sources,
                'LAUNCH_SOURCE_IDENTITY')
        require(pre['sourceTreeUnchangedSinceRequiredCI'] is True
                and pre['duplicateGenerationRunCount'] == pre['legacyR36ActiveRunCount'] == 0,
                'ONE_SHOT_LINEAGE')
    inventory = model_inventory(gen2, protocol, fitted)
    return {'status': 'PASS', 'archiveSha256': ARCHIVE_SHA256, 'artifactFileCount': len(names),
            'sourceFilesVerified': len(sources), 'modelInventory': inventory,
            'artifactFileHashes': {n: sha(artifact_root / n) for n in sorted(names)},
            'sourceSha256': sources, 'dependencies': receipt['dependencies']}


def audit_artifact(artifact_zip, artifact_root, core_root):
    protocol = load_protocol()
    metadata = audit_metadata(artifact_zip, artifact_root, protocol)
    from scripts.phase57_exit_gen2_data_audit_r43 import audit_data
    from scripts.phase57_exit_gen2_ledger_audit_r43 import audit_ledgers
    data = audit_data(artifact_root / 'gen2', core_root, protocol)
    ledgers = audit_ledgers(artifact_root / 'gen2', core_root, protocol)
    return assemble_audit(metadata, data, ledgers, protocol)


def assemble_audit(metadata, data, ledgers, protocol):
    """Assemble freshly verified independent stages without repeating their work."""
    require(metadata['status'] == 'PASS' and metadata['archiveSha256'] == ARCHIVE_SHA256,
            'ARCHIVE_METADATA_PASS_REQUIRED')
    require(data['status'] == ledgers['status'] == 'PASS', 'INDEPENDENT_SUBAUDIT_REQUIRED')
    require(data['executionHead'] == EXECUTION_SHA and data['protocolSha256'] == PROTOCOL_SHA256,
            'DATA_SUBAUDIT_IDENTITY')
    require(data['predictionSha256'] == metadata['artifactFileHashes']['gen2/oof-predictions.npz'],
            'DATA_SUBAUDIT_PREDICTION_HASH')
    require(len(ledgers['inputLedgerHashes']) == 34, 'LEDGER_SUBAUDIT_FILE_COUNT')
    for name, digest in ledgers['inputLedgerHashes'].items():
        require(metadata['artifactFileHashes'].get('gen2/' + name) == digest,
                'LEDGER_SUBAUDIT_INPUT_IDENTITY:' + name)
    return {'schemaVersion': 'phase57-gen2-independent-artifact-audit-r43-v1',
            'status': 'GEN2_ARTIFACT_AUDIT_PASS', 'executionHead': EXECUTION_SHA,
            'runId': RUN_ID, 'artifactId': ARTIFACT_ID, 'archiveSha256': ARCHIVE_SHA256,
            'protocolSha256': PROTOCOL_SHA256, 'metadataAudit': metadata,
            'dataAudit': data, 'ledgerAudit': ledgers,
            'inputLedgerHashes': ledgers['inputLedgerHashes'],
            'modelFitsPerformed': 0, 'policyReplaysPerformed': 0,
            'performanceAggregatedDuringAudit': False,
            'providerRequests': 0, 'protectedPartitionsOpened': 0, 'safety': protocol['safety']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact-zip', type=Path, required=True)
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--core-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), 'APPEND_ONLY_AUDIT_OUTPUT')
    result = audit_artifact(args.artifact_zip, args.artifact_root, args.core_root)
    write_new(args.out, result)
    print(json.dumps({k: result[k] for k in ('status', 'runId', 'artifactId', 'protocolSha256')}, sort_keys=True))


if __name__ == '__main__':
    main()
