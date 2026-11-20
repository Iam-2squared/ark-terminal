"""Adapt one AST-extraction test to the new pure serializer dependency.

The existing regression extracts only Publish, deliberately avoiding top-level
Excel observation. Publish now calls a pure helper, so that helper must be
loaded explicitly too. No assertion, fixture, skip or expectation is changed.
This touches only the disposable CI baseline test, never production payload.
"""
from pathlib import Path
import hashlib
import json
import os

ORIGINAL = 'a61b1dcbd4aa3bd10c9dd2fb2ed6bcc215f2f8fc'
ANCHOR = '$source=$functions[0].Extent.Text\n'
ADDITION = "# New pure dependency only; do not execute observer top-level Excel code.\n. (Join-Path (Split-Path -Parent $env:NO11_TEST_OBSERVER) 'No11CleanCompatibility.ps1')\n"


def prepare():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('NO11_CLEAN_TEST_HARNESS_CI_ONLY')
    engine = Path(os.environ['NO11_CLEAN_ENGINE'])
    file = engine / 'tests/no11_windows_native_io_regression.test.mjs'
    original = file.read_text(encoding='utf-8').replace('\r\n', '\n')
    raw = original.encode('utf-8')
    actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if actual != ORIGINAL or original.count(ANCHOR) != 1:
        raise SystemExit('NO11_CLEAN_TEST_HARNESS_PIN_MISMATCH')
    modified = original.replace(ANCHOR, ANCHOR + ADDITION)
    if modified.replace(ANCHOR + ADDITION, ANCHOR) != original:
        raise SystemExit('NO11_CLEAN_TEST_HARNESS_SCOPE_MISMATCH')
    file.write_text(modified, encoding='utf-8', newline='\n')
    note = {'scope': 'CI_TEST_DEPENDENCY_ONLY', 'sourceGitBlob': ORIGINAL,
            'test': file.name, 'added': ADDITION, 'assertionsChanged': False,
            'skipsAdded': False, 'productionPayloadChanged': False}
    Path(os.environ['NO11_CLEAN_PACKAGE'], 'node-harness-adjustment.json').write_text(
        json.dumps(note, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    print('NO11_CLEAN_NATIVE_IO_TEST_HELPER=LOADED_WITHOUT_WEAKENING_ASSERTIONS')


if __name__ == '__main__':
    prepare()
