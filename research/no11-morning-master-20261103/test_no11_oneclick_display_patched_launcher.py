"""Published launcher transforms only; never execute a launcher or retry route."""
from pathlib import Path
import os
import re
import unittest

import no11_oneclick_display_transform as migration
import install_no11_oneclick_display_v2 as installer
import patch_oneclick_selection_display as selection
import patch_oneclick_preorder_retry as historical
import test_no11_oneclick_display_v2 as originals

HERE = Path(__file__).resolve().parent


def variants():
    raw = (HERE / 'Start-No11OneClick.ps1').read_bytes()
    raw = raw.replace(b'FromArgb(29,32,38)', b'FromArgb(255,255,255)')
    retry = historical.patch_text(raw)
    return {'white': raw, 'white_selection': selection.patch(raw),
            'white_retry': retry, 'white_retry_selection': selection.patch(retry)}


class PatchedLauncherTests(unittest.TestCase):
    def test_preserves_entire_action_suffix_and_all_existing_enabled_expressions(self):
        for label, raw in variants().items():
            with self.subTest(variant=label):
                changed = migration.transform(raw)
                self.assertEqual(changed.split(b'$refresh.Add_Click')[1], raw.split(b'$refresh.Add_Click')[1])
                for name in ('trade', 'nightly', 'review'):
                    token = ('$' + name + '.Enabled=').encode()
                    self.assertEqual([l for l in raw.splitlines() if token in l],
                                     [l for l in changed.splitlines() if token in l])
                self.assertEqual(migration.transform(changed), changed)
                self.assertIn(b'FromArgb(255,255,255)', changed)
                self.assertEqual(raw.count(b'$retryReady=CanRetryPreorder $s'),
                                 changed.count(b'$retryReady=CanRetryPreorder $s'))
                for old, new in migration.DISPLAY_PAIRS:
                    text = changed.decode('utf-8-sig')
                    if new in text.replace('\r\n', '\n'):
                        restored = migration.replace_regions(text, ((new, old),
                            (migration.NEW_TOOL, migration.OLD_TOOL), (migration.TOOLTIP, '')))
                        self.assertEqual(restored, raw.decode('utf-8-sig'))

    def test_mixed_eol_customization_outside_region_remains_byte_exact(self):
        for label, raw in variants().items():
            canonical = raw.decode('utf-8-sig').replace('\r\n', '\n')
            for bom, newline in ((b'', '\n'), (b'', '\r\n'), (b'\xef\xbb\xbf', '\r\n')):
                with self.subTest(variant=label, newline=newline, bom=bool(bom)):
                    before = bom + canonical.replace('\n', newline).encode() + b'\n# PRESERVE_LOCAL_SUFFIX\n'
                    after = migration.transform(before)
                    self.assertEqual(before.split(b'$refresh.Add_Click')[1], after.split(b'$refresh.Add_Click')[1])
                    self.assertEqual(migration.transform(after), after)

    def test_unknown_or_incomplete_historical_region_is_not_guessed(self):
        raw = variants()['white_retry_selection']
        for altered in (
                raw.replace(b'function CanRetryPreorder($s){', b'function ChangedRetry($s){'),
                raw.replace(b'$retryReady=CanRetryPreorder $s', b'$retryReady=$true'),
                raw.replace(b'PRE-ORDER REFERENCE FAILED - VERIFIED RETRY AVAILABLE', b'UNREVIEWED_STATUS')):
            with self.assertRaises(ValueError):
                migration.transform(altered)

    def test_installer_preserves_published_local_launcher_variants(self):
        for label, raw in variants().items():
            helper = originals.InstallTests('test_audit_is_readonly_and_does_not_run_processes')
            helper.setUp()
            try:
                helper.launcher.write_bytes(raw)
                before = helper.snapshot()
                self.assertEqual(helper.apply(), 'APPLIED_NO_TRADE')
                self.assertEqual({p for p, data in before.items() if p.read_bytes() != data}, {helper.launcher})
                self.assertEqual(helper.apply(), 'ALREADY_APPLIED')
            finally:
                helper.doCleanups()

    @unittest.skipUnless(os.name == 'nt', 'Windows PowerShell 5.1 parser')
    def test_actual_parser_accepts_all_published_launcher_variants(self):
        for label, raw in variants().items():
            with self.subTest(variant=label):
                installer.parse_launcher(migration.transform(raw))


if __name__ == '__main__':
    unittest.main(verbosity=2)
