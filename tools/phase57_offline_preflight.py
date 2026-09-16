"""Offline package verification. No downloads, COM, credentials or RSS calls."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
from phase57_offline_excel_reader import ROOT, inspect_fixture, require


def preflight():
    require(sys.version_info >= (3, 12), 'PYTHON_3_12_REQUIRED')
    node = subprocess.run(['node', '--version'], capture_output=True, text=True, check=True).stdout.strip()
    require(int(node.lstrip('v').split('.')[0]) >= 22, 'NODE_22_REQUIRED')
    contract = json.loads((ROOT/'predict/research/phase57-offline-parity/contract.json').read_text(encoding='utf-8'))
    require(all(v is False for v in contract['safety'].values()), 'SAFETY_NOT_FALSE')
    require(contract['boundaries']['realCaptureEnabled'] is False, 'REAL_CAPTURE_LOCKED')
    manifest = json.loads((ROOT/'predict/research/phase57-offline-parity/source-integrity.json').read_text(encoding='utf-8'))
    for relative, expected in manifest['fileSha256'].items():
        candidate = (ROOT/relative).resolve()
        require(candidate.is_relative_to(ROOT.resolve()), 'INVALID_SOURCE_PATH')
        require(hashlib.sha256(candidate.read_bytes()).hexdigest() == expected, 'SOURCE_HASH_MISMATCH:'+relative)
    packet = inspect_fixture(ROOT/'tools/templates/ArkParityOffline.xlsx')
    return {'status':'OFFLINE_PREFLIGHT_PASS', 'platform':platform.system(), 'python':platform.python_version(), 'node':node,
            'workbookSha256':packet['workbookSha256'], 'verifiedFiles':len(manifest['fileSha256']),
            'excelConnectionTested':False, 'msiiConnectionTested':False, 'reservedOpened':False,
            'safety':contract['safety']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = preflight()
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(result['status'])
