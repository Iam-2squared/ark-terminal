#!/usr/bin/env python3
"""Hash-only guard: never imports model/training/evaluation or generates predictions."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/phase57-msh-entry-long-v1-first-development'
PINNED = {
    'predict/research/phase57-msh-entry-long-v1-fit-contract-v1.json': '64c20d785be5f23b0a9103f419726b191a12a58fd5d3a7ad5185c69f9644a938',
    'predict/research/phase57_msh_entry_long_v1_proportional_odds.py': '9e5910c476c6957aab65cc24490ffb2759084e5e49b36db42fe284674979ae74',
    'predict/research/phase57-msh-entry-v1-model.json': 'f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a',
    'predict/research/phase57-minimal-stateful-entry-contract.json': 'cc70b1eb07c0719f72c4a8caa0f165a2812aec4af0b2fdeae42ef3ff400c4115',
    'scripts/lib/phase57-minimal-stateful-entry.mjs': '7cd4ab03f4de8e0b845fc5f7fb2893d9585feee0989b0f6b085a18a28be73ba0',
    'scripts/run_phase57_msh_entry_long_v1_development.py': 'cfd287dc32399b34b0fdb2175a8d7079d72a561a9459dd861137969cb343ced8',
    'scripts/audit_phase57_msh_entry_long_v1_development.py': '0876a7a7a819fd140902c08a08304b5c1019e6e81e2d214a91159680cf0c0e5d',
    'scripts/report_phase57_msh_entry_long_v1_development.mjs': '3133131ad5cb57eb4b4d474b69f03209e6b86c7319e460fd801d962c15aceff1',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    manifest_path = EVIDENCE / 'manifest.json'
    assert sha(manifest_path) == '0d63a4b5461db863e731e1d19c29b7fc07417e71f2743d334f20c812862d48f1', 'ORIGINAL_MANIFEST_CHANGED'
    before = json.loads(manifest_path.read_text())['files']
    result = {}
    for name, expected in before.items():
        actual = sha(EVIDENCE / name)
        assert actual == expected, 'ARTIFACT_HASH_CHANGED:' + name
        result[name] = {'before': expected, 'after': actual, 'unchanged': True}
    for name, expected in PINNED.items():
        assert sha(ROOT / name) == expected, 'PROTECTED_SOURCE_CHANGED:' + name
    selector = json.loads((ROOT / 'predict/research/phase57-long-only-frozen-selector-v1.json').read_text())
    payload = json.dumps(selector['freezePayload'],sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    selector_sha = hashlib.sha256(payload).hexdigest()
    assert selector_sha == '3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59'
    assert selector['hashes']['savedModelArtifactSha256'] == '994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb'
    report = json.loads((EVIDENCE / 'development-report.json').read_text())
    verdict = json.loads((EVIDENCE / 'development-verdict.json').read_text())
    assert verdict['verdict'] == 'MSH_ENTRY_LONG_V1_DEVELOPMENT_BORDERLINE'
    assert verdict['selectedThreshold'] is None
    assert set(report['thresholds']) == {'1.0','2.0','3.0'}
    assert all(value is False for value in report['safety'].values())
    return {'status':'PASS','originalDevelopmentCommit':'772c4ed40a43590c6198f6f34ab18b5e9226df18',
            'selectorPayloadSha256':selector_sha,'ridgeArtifactReferenceSha256':selector['hashes']['savedModelArtifactSha256'],
            'ridgeRawArtifactReacquired':False,'artifacts':result,'protectedSourceHashes':PINNED,
            'newProjectFits':0,'newProjectPredictions':0,'newOofGeneration':0,'thresholdSelection':None}


if __name__=='__main__':
    print(json.dumps(verify(),indent=2,sort_keys=True))
