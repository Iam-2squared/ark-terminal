"""Fail-closed provenance and one-shot authorization. No estimator imports."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote
from scripts import phase57_exit_gen3_runtime_r45 as runtime
from scripts.phase57_exit_gen2_preflight_r41 import github_get

ROOT = runtime.ROOT
REPO = 'Iam-2squared/ark-terminal'
BRANCH = 'research/phase57-long-only-cash-equity'
EVIDENCE = 'docs/evidence/phase57-comprehensive-exit-v1'
MARKER = EVIDENCE + '/GEN3_LAUNCH_R45.json'
CI_PATH = '.github/workflows/phase57-exit-gen3-contract-r45.yml'
FINITE_PATH = '.github/workflows/phase57-exit-gen3-r45.yml'
R35_RUN = 36220335998
R35_ARTIFACT = 10899151845
R35_DIGEST = 'a12852e36f270e247a9a0bb7f0f7f618da934297c05f7c687fccb7ceade40434'
require = runtime.require


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, sort_keys=True, ensure_ascii=False, allow_nan=False); f.write('\n')


def source_manifest(root):
    p = runtime.load_protocol()
    pins = {**p['reusedGen2SourceHashes'], **p['baselineSourceHashes']}
    pins[EVIDENCE + '/GEN3_PRECOMMIT_R45.json'] = runtime.PROTOCOL_SHA256
    pins['docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/names.json'] = 'efcbcaf4c4024679dc5f6e7881dcccc7c0186361b6bd469b7d3a5e6a5421e8eb'
    for name, digest in pins.items():
        require((root / name).is_file() and sha(root / name) == digest, 'R45_INHERITED_SOURCE_HASH:' + name)
    new = list((root / 'scripts').glob('phase57_exit_gen3*_r45.py'))
    new += list((root / 'scripts').glob('test_phase57_exit_gen3*_r45.py'))
    require(any(f.name.startswith('test_') for f in new), 'R45_NO_TEST_SOURCE')
    for name in ('runtime', 'facts', 'labels', 'data', 'runner', 'preflight'):
        require((root / 'scripts' / ('phase57_exit_gen3_' + name + '_r45.py')).is_file(), 'R45_MISSING_MODULE:' + name)
    new += [root / CI_PATH, root / FINITE_PATH]
    for f in new:
        require(f.is_file(), 'R45_MISSING_WORKFLOW:' + str(f))
        pins[str(f.relative_to(root))] = sha(f)
    return dict(sorted(pins.items()))


def contract_receipt(root, support_dir, logs):
    p = runtime.load_protocol(); sources = source_manifest(root)
    support = json.loads((support_dir / 'support-gate.json').read_text())
    require(support['status'] == 'ALL_24_PASS_BEFORE_FIT' and len(support['slices']) == 24,
            'R45_SUPPORT_NOT_PASSED')
    require(support['modelFits'] == support['policyReplays'] == 0 and support['performanceInspected'] is False,
            'R45_PREFIT_EXPOSURE')
    data = json.loads((support_dir / 'data/data-receipt.json').read_text())
    require(data['rows'] == 656247 and data['supportOnly'] is True, 'R45_SUPPORT_DATA_SCOPE')
    execution = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    require(execution == os.environ['GITHUB_SHA'] and os.environ['GITHUB_REF'].startswith('refs/heads/research/phase57-gen3-r45-ci-'),
            'R45_CI_BRANCH_IDENTITY')
    require(all(v is False for v in p['safety'].values()) and len(p['safety']) == 9, 'R45_SAFETY9')
    log = logs.read_text()
    require(re.search(r'Ran \d+ tests', log) and re.search(r'^OK$', log, re.M), 'R45_TEST_LOG_NOT_SUCCESS')
    return {'schema': 'phase57-gen3-contract-r45-v1', 'status': 'GEN3_PREFLIGHT_PASS_NOT_PERFORMANCE_PASS',
            'executionSha': execution, 'runId': int(os.environ['GITHUB_RUN_ID']),
            'protocolSha256': runtime.PROTOCOL_SHA256, 'sourceHashes': sources,
            'supportGateSha256': sha(support_dir / 'support-gate.json'), 'supportSlices': 24,
            'testsLogSha256': sha(logs), 'candidateCount': 4, 'expectedModelFitCount': 24,
            'modelFits': 0, 'policyReplays': 0, 'gen3PerformanceInspected': False,
            'providerRequests': 0, 'protectedPartitionsOpened': 0, 'safety': p['safety']}


def validate_launch(marker, ci, sources, execution, environment, get):
    require(marker.get('schema') == 'phase57-gen3-launch-r45-v1' and marker.get('authorizedByUser') is True,
            'R45_EXPLICIT_USER_AUTHORIZATION')
    require(re.fullmatch('[0-9a-f]{40}', marker.get('executionSha', '')) is not None, 'R45_EXECUTION_SHA_FORMAT')
    require(marker['protocolSha256'] == ci['protocolSha256'] == runtime.PROTOCOL_SHA256, 'R45_LAUNCH_PROTOCOL')
    require(marker['executionSha'] == ci['executionSha'] == execution, 'R45_TESTED_EXECUTION_SHA')
    require(ci['status'] == 'GEN3_PREFLIGHT_PASS_NOT_PERFORMANCE_PASS' and ci['sourceHashes'] == sources,
            'R45_CI_SOURCE_IDENTITY')
    require(ci['candidateCount'] == 4 and ci['expectedModelFitCount'] == 24 and ci['supportSlices'] == 24,
            'R45_CI_BUDGET_SUPPORT')
    require(ci['modelFits'] == ci['policyReplays'] == 0 and ci['gen3PerformanceInspected'] is False, 'R45_CI_EXPOSURE')
    require(ci['safety'] == runtime.load_protocol()['safety'], 'R45_CI_SAFETY')
    require(environment['GITHUB_REPOSITORY'] == REPO and environment['GITHUB_REF'] == 'refs/heads/' + BRANCH,
            'R45_LAUNCH_BRANCH')
    require(environment['GITHUB_RUN_ATTEMPT'] == '1', 'R45_NO_RERUN')
    trigger = environment['GITHUB_SHA']; rid = int(environment['GITHUB_RUN_ID'])
    require(get('/git/ref/heads/' + BRANCH)['object']['sha'] == trigger, 'R45_BRANCH_HEAD_MOVED')
    prior = get('/actions/runs/' + str(marker['contractRunId']))
    require(prior['id'] == ci['runId'] == marker['contractRunId'] and prior['head_sha'] == execution and
            prior['path'] == CI_PATH and prior['status'] == 'completed' and prior['conclusion'] == 'success',
            'R45_REQUIRED_CI_RUN')
    this = get('/actions/runs/' + str(rid))
    require(this['head_sha'] == trigger and this['path'] == FINITE_PATH and this['run_attempt'] == 1,
            'R45_FINITE_RUN_IDENTITY')
    runs = []
    for page in range(1, 101):
        batch = get(f"/actions/workflows/{this['workflow_id']}/runs?per_page=100&page={page}")['workflow_runs']
        runs.extend(batch)
        if len(batch) < 100: break
    else: raise ValueError('R45_DUPLICATE_PAGINATION_UNRESOLVED')
    require(len(runs) == 1 and runs[0]['id'] == rid, 'R45_DUPLICATE_FINITE_RUN')
    comparison = get('/compare/' + execution + '...' + trigger)
    require(comparison['status'] == 'ahead' and comparison['base_commit']['sha'] == execution,
            'R45_LAUNCH_NOT_DESCENDANT')
    files = comparison.get('files', [])
    allowed = {MARKER, EVIDENCE + '/GEN3_IMPLEMENTATION_HANDOFF_R45.md'}
    require(files and len(files) < 300 and any(f['filename'] == MARKER and f['status'] == 'added' for f in files),
            'R45_LAUNCH_MARKER_NOT_NEW')
    require(all(f['filename'] in allowed and f['status'] in ('added', 'modified') for f in files),
            'R45_SOURCE_CHANGED_AFTER_CI')
    a = get('/actions/artifacts/' + str(R35_ARTIFACT))
    require(a['id'] == R35_ARTIFACT and a['workflow_run']['id'] == R35_RUN and not a['expired'] and
            a['digest'] == 'sha256:' + R35_DIGEST, 'R45_R35_ARTIFACT_IDENTITY')
    return {'status': 'R45_LAUNCH_AUTHORIZED', 'executionSha': execution, 'triggerSha': trigger,
            'runId': rid, 'contractRunId': marker['contractRunId'], 'protocolSha256': runtime.PROTOCOL_SHA256,
            'sourceHashes': sources, 'candidateCount': 4, 'expectedModelFitCount': 24,
            'safety': runtime.load_protocol()['safety'], 'providerRequests': 0, 'protectedPartitionsOpened': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=('contract', 'launch'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--support-dir', type=Path)
    parser.add_argument('--tests-log', type=Path)
    parser.add_argument('--marker', type=Path)
    parser.add_argument('--ci-receipt', type=Path)
    args = parser.parse_args()
    if args.phase == 'contract':
        receipt = contract_receipt(ROOT, args.support_dir, args.tests_log)
        write(args.out, receipt)
        # Explicit source allowlist only; no credentials/configuration are exported.
        for name in receipt['sourceHashes']:
            dst = args.out.parent / 'source' / name; dst.parent.mkdir(parents=True, exist_ok=True)
            with dst.open('xb') as f: f.write((ROOT / name).read_bytes())
    else:
        marker = json.loads(args.marker.read_text()); ci = json.loads(args.ci_receipt.read_text())
        execution = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True, cwd=ROOT).strip()
        write(args.out, validate_launch(marker, ci, source_manifest(ROOT), execution, os.environ, github_get))


if __name__ == '__main__':
    main()
