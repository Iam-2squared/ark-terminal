"""A local-only bootstrap must retain unrelated modifications and old raw bytes."""
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import sys
import unittest

TOOL = Path(__file__).resolve().parents[1] / 'tools' / 'no11_patch_weekly_bootstrap_local.py'
SPEC = importlib.util.spec_from_file_location('no11_bootstrap_local_patch_test', TOOL)
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)


def old_fixture():
    return """from copy import deepcopy
from pathlib import Path
REQUIRED = {}
OPTIONAL = {'prior',
""" + PATCH.BEFORE[0] + """
def need(value, name):
    if not value:
        raise ValueError(name)
def validate_readonly_broker_config(*args):
    pass
def validate_config(obj):
    need(obj['orderTransmission'] is False, 'CONFIG_NOT_READONLY')
    need(True, 'EXACTLY_ONE_PREVIOUS_SOURCE_REQUIRED')
""" + PATCH.BEFORE[1] + """ [('samples', 1, 2, 3)]:
        pass
""" + PATCH.BEFORE[2] + """
        if key in c:
            pass
""" + PATCH.BEFORE[3] + """
    validate_readonly_broker_config('dummy')
    return c
""" + PATCH.BEFORE[4] + """
    return run
LOCAL_UNRELATED_CHANGE = 'never rewrite me'
"""


class LocalOnlyBootstrapPatchTests(unittest.TestCase):
    def test_only_five_exact_anchors_change(self):
        src = old_fixture()
        repaired, changed = PATCH.patch_bytes(src.encode('utf-8'))
        self.assertTrue(changed)
        result = repaired.decode()
        self.assertIn("LOCAL_UNRELATED_CHANGE = 'never rewrite me'", result)
        for new in PATCH.AFTER:
            self.assertIn(new, result)
        self.assertIn("NO11_WEEKLY_SHADOW_SCOPE=PASS_OBSERVED_NOT_EXTERNALLY_REVIEWED", result)
        self.assertIn("weekly_supplied = weekly_keys & set(obj)", result)
        self.assertIn("NO11_WEEKLY_SHADOW_SCOPE=PASS_OBSERVED_NOT_EXTERNALLY_REVIEWED", result)
        self.assertIn("obj['orderTransmission'] is False", result)
        self.assertEqual(PATCH.patch_bytes(repaired), (repaired, False))

    def test_crlf_and_bom_are_preserved(self):
        b = b'\xef\xbb\xbf' + old_fixture().replace('\n', '\r\n').encode()
        updated, changed = PATCH.patch_bytes(b)
        self.assertTrue(changed)
        self.assertTrue(updated.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n', updated.replace(b'\r\n', b''))
        self.assertIn(b'LOCAL_UNRELATED_CHANGE', updated)

    def test_unknown_partial_and_duplicate_anchors_fail_without_approved_output(self):
        src = old_fixture()
        with self.assertRaisesRegex(ValueError, 'ANCHOR_MISMATCH'):
            PATCH.patch_text(src.replace(PATCH.BEFORE[0], 'LOCAL_CHANGED_DICT'))
        with self.assertRaisesRegex(ValueError, 'PARTIAL_WEEKLY_WIRING'):
            PATCH.patch_text(src + "\nprecomputedChartReceipt = True\n")
        with self.assertRaisesRegex(ValueError, 'ANCHOR_MISMATCH'):
            PATCH.patch_text(src + "\n" + PATCH.BEFORE[0] + "\n")

    def test_staged_cli_keeps_original_source_bytes(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / 'no11_received_session_bootstrap.py'
            dest = Path(tmp) / 'staged.py'
            raw = old_fixture().encode()
            source.write_bytes(raw)
            self.assertEqual(PATCH.run(['--input', str(source), '--staged-output', str(dest)]), 0)
            self.assertEqual(source.read_bytes(), raw)
            self.assertNotEqual(dest.read_bytes(), raw)
            self.assertEqual(PATCH.run(['--input', str(source), '--staged-output', str(dest)]), 2)


if __name__ == '__main__':
    unittest.main()
