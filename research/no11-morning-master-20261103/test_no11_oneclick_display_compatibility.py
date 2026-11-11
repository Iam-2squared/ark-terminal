"""Provenance and compatibility regressions; synthetic roots only, no LIVE I/O."""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import no11_update_path as weekend
import install_no11_completed_session_update as completed
import no11_oneclick_display_v2 as display
import no11_oneclick_display_transform as migration
import install_no11_oneclick_display_v2 as installer
import patch_oneclick_selection_display as selection
import test_no11_oneclick_display_v2 as original_tests

HERE = Path(__file__).resolve().parent
OBSERVED_STATUS = '89034581d9ee797ba76151d62668184942bbad3f'


def derived_sources():
    base = (HERE / 'oneclick_status.py').read_bytes()
    saturday = weekend.transform('status', base)
    latest = completed.transform('status', base)
    both = completed.transform('status', saturday)
    return {'ORIGINAL': base, 'WEEKEND_DATA': saturday,
            'COMPLETED_SESSION_DATA': latest, 'WEEKEND_AND_COMPLETED_SESSION_DATA': both}


class ProvenanceTests(unittest.TestCase):
    def test_published_derivation_reproduces_reported_installed_status(self):
        sources = derived_sources()
        for label, raw in sources.items():
            print('STATUS_DERIVATION|' + label + '=' + installer.blob(raw), flush=True)
        self.assertEqual(installer.blob(sources['ORIGINAL']), installer.LEGACY_BLOB)
        self.assertEqual(installer.blob(sources['WEEKEND_AND_COMPLETED_SESSION_DATA']), OBSERVED_STATUS)

    def test_official_patches_change_only_inspect_not_underlying_evidence_rules(self):
        def functions(raw):
            tree = ast.parse(raw.decode('utf-8-sig'))
            return {node.name: ast.dump(node) for node in tree.body if isinstance(node, ast.FunctionDef)}
        base = functions(derived_sources()['ORIGINAL'])
        for label, raw in derived_sources().items():
            with self.subTest(family=label):
                actual = functions(raw)
                self.assertEqual(set(actual), set(base))
                for name in set(base) - {'inspect'}:
                    self.assertEqual(actual[name], base[name], name)

    def test_classifier_accepts_only_exact_published_families_in_windows_encodings(self):
        for family, raw in derived_sources().items():
            canonical = raw.decode('utf-8-sig').replace('\r\n', '\n')
            for bom, newline in ((b'', '\n'), (b'', '\r\n'), (b'\xef\xbb\xbf', '\r\n')):
                with self.subTest(family=family, newline=newline, bom=bool(bom)):
                    candidate = bom + canonical.replace('\n', newline).encode('utf-8')
                    self.assertEqual(display.native_source_family(candidate), family)
            for changed in (canonical + '# unreviewed\n', canonical.replace('canRequestTrade=True', 'canRequestTrade=False')):
                with self.assertRaises(ValueError):
                    display.native_source_family(changed.encode())

    def test_weekend_copy_is_not_market_open_when_native_data_updates_are_enabled(self):
        original = {'mode': 'WEEKEND_FRIDAY_DATA', 'reason': 'PREVIOUS_FRIDAY_RSS_REFRESH_AVAILABLE',
                    'canRequestTrade': False, 'canRunNightly': True}
        for day in ('2026-11-14', '2026-11-15'):
            for hour in ('08:45:00', '09:01:00', '12:00:00', '20:00:00'):
                state = deepcopy(original)
                out = display.present(state, datetime.fromisoformat(day + 'T' + hour + '+09:00'),
                    {'state': 'NONE'}, {'state': 'NO_RECORD'}, {'state': 'NOT_READY'}, 'APPLIED')
                self.assertEqual(out['phase'], 'NO_SESSION')
                self.assertEqual(state, original)
                self.assertNotIn('RESERVED 09:00', out['text'])


class NativeFamilyInstallationTests(unittest.TestCase):
    def test_preserves_each_native_variant_and_exact_permissions_across_date_windows(self):
        for family, source in derived_sources().items():
            helper = original_tests.InstallTests('test_audit_is_readonly_and_does_not_run_processes')
            helper.setUp()
            try:
                helper.legacy.write_bytes(source)
                # Exercise the real selection-header migration, not a comment-only stand-in.
                helper.launcher.write_bytes(selection.patch(helper.launcher.read_bytes()))
                before = helper.snapshot()
                self.assertEqual(helper.apply(), 'APPLIED_NO_TRADE')
                self.assertEqual(helper.legacy.read_bytes(), source)
                self.assertEqual({p for p, raw in before.items() if p.read_bytes() != raw}, {helper.launcher})
                self.assertEqual(helper.apply(), 'ALREADY_APPLIED')
                installed = display.module(helper.home / installer.DISPLAY, 'family_display_installed')
                native = display.module(helper.legacy, 'family_native_installed')
                # DATA installation is available; this exercises the exact branches
                # the historical patches changed without running any data collector.
                binding = installer.n.read(helper.f['binding'])
                data_tool = helper.f['root'] / 'synthetic-data-tool.ps1'
                data_tool.write_text('# never executed', encoding='ascii')
                binding.update(dailyCycleTool=str(data_tool), dailyCycleRoot=str(helper.f['root']))
                original_tests.put(helper.f['binding'], binding)
                for day in ('2026-11-11', '2026-11-12', '2026-11-14', '2026-11-15'):
                    for hour in ('07:00:00', '08:30:00', '09:00:00', '09:02:00', '15:20:00', '18:00:00', '23:59:59'):
                        with self.subTest(family=family, day=day, hour=hour):
                            at = original_tests.now(hour, day)
                            expected = native.inspect(helper.f['settings'], helper.f['binding'], at=at)
                            actual = installed.inspect(helper.f['settings'], helper.f['binding'], at=at)
                            view = actual.pop('presentation')
                            self.assertEqual(actual, expected)
                            if at.weekday() >= 5:
                                self.assertEqual(view['phase'], 'NO_SESSION')
                installed.native_inspector()
                helper.legacy.write_bytes(source + b'# unauthorized replacement\n')
                with self.assertRaisesRegex(ValueError, 'DISPLAY_DEPENDENCY_CHANGED'):
                    installed.native_inspector()
            finally:
                helper.doCleanups()


if __name__ == '__main__':
    unittest.main(verbosity=2)
