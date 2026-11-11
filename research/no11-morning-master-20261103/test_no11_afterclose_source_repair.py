"""Synthetic installation roots only. Never access Excel or a broker."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import install_no11_afterclose_source_repair as repair
import test_no11_prestart_source_retry as fixtures
import test_no11_rss_opening_source_wait as waits


class AfterCloseRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = fixtures.fixture(Path(self.temp.name))
        self.store = self.f['store']
        self.entry = self.f['engine'] / repair.TARGETS['BOOTSTRAP']
        self.funding = self.f['engine'] / repair.TARGETS['FUNDING']
        white = self.store / 'oneclick/Start-No11OneClick.ps1'
        white.parent.mkdir()
        white.write_bytes(b'APPROVED_WHITE_UI_DO_NOT_REPLACE')
        # Existing local EXIT fixes are deliberately not upstream byte matches.
        (self.f['engine'] / 'tools/local_exit_fix.py').write_bytes(b'LOCAL_FIX=42\n')
        (self.f['engine'] / 'windows/Invoke-No11MsiiOrder.ps1').write_bytes(b'# EXISTING_LOCAL_SENDER_FIX\n')
        self.claim = self.store / 'PRESTART-SOURCE-RETRY-2026-11-11.claim.json'
        self.claim.write_bytes(b'EXISTING_USED_CLAIM_MUST_STAY')
        self.f['dispatch'].joinpath('preserved-evidence.json').write_bytes(b'EXISTING_EVIDENCE')
        self.journal = self.store / repair.JOURNAL

    def snapshot(self):
        return {p: p.read_bytes() for p in self.f['root'].rglob('*') if p.is_file()}

    def apply(self):
        # Only unit tests mock process/time checks; no production --test option.
        with patch.object(repair, 'gate') as gate:
            result = repair.install(self.store, apply=True)
        self.assertGreaterEqual(gate.call_count, 2)
        return result

    def test_audit_creates_nothing_and_executes_no_child(self):
        before = self.snapshot()
        with patch.object(repair.subprocess, 'run', side_effect=AssertionError('NO_CHILD')):
            self.assertEqual(repair.install(self.store), 'READY_NOT_APPLIED')
        self.assertEqual(self.snapshot(), before)

    def test_apply_changes_exactly_two_sources_preserves_existing_fixes_and_claim(self):
        before = self.snapshot()
        self.assertEqual(self.apply(), 'APPLIED_NO_TRADE')
        changed = {p for p, raw in before.items() if p.read_bytes() != raw}
        self.assertEqual(changed, {self.entry, self.funding})
        self.assertEqual(self.entry.read_bytes(), repair.weekly.transform(before[self.entry]))
        self.assertEqual(self.funding.read_bytes(), repair.funding.transform(before[self.funding]))
        self.assertEqual(self.claim.read_bytes(), before[self.claim])
        record = repair.n.checkpoint(self.journal)
        self.assertEqual(record['phase'], 'COMPLETE')
        repair.verify(self.store, record)
        after = self.snapshot()
        self.assertEqual(repair.install(self.store), 'ALREADY_APPLIED')
        self.assertEqual(self.apply(), 'ALREADY_APPLIED')
        self.assertEqual(self.snapshot(), after)

    def test_exact_weekly_fix_can_already_be_installed(self):
        self.entry.write_bytes(repair.weekly.transform(self.entry.read_bytes()))
        original = self.entry.read_bytes()
        self.assertEqual(self.apply(), 'APPLIED_NO_TRADE')
        self.assertEqual(self.entry.read_bytes(), original)

    def test_unknown_target_blocks_before_either_source_or_journal_changes(self):
        for target in (self.entry, self.funding):
            original = target.read_bytes()
            target.write_bytes(original + b'\n# unknown local edit\n')
            before = self.snapshot()
            with self.assertRaises(ValueError):
                self.apply()
            self.assertEqual(self.snapshot(), before)
            target.write_bytes(original)

    def test_bad_native_weekly_or_settings_are_refused(self):
        native = self.f['engine'] / 'tools/no11_verified_weekly_shadow_scope.mjs'
        native.write_bytes(native.read_bytes() + b'// changed\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'NATIVE_WEEKLY_CHANGED'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_unknown_patched_bootstrap_is_not_accepted_by_marker_alone(self):
        changed = repair.weekly.transform(self.entry.read_bytes()).replace(
            b'def verified_weekly_original(config):', b'def verified_weekly_original(config): # tamper')
        self.entry.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_BOOTSTRAP_SOURCE'):
            repair.install(self.store)
        self.assertFalse(self.journal.exists())

    def test_interrupt_after_first_source_resumes_only_known_journal(self):
        old_funding = self.funding.read_bytes()
        real = repair.replace_exact
        def interrupted(path, before, after):
            real(path, before, after)
            raise OSError('synthetic interruption')
        with patch.object(repair, 'replace_exact', side_effect=interrupted):
            with self.assertRaises(OSError):
                self.apply()
        self.assertEqual(self.funding.read_bytes(), old_funding)
        self.assertEqual(repair.n.checkpoint(self.journal)['phase'], 'PREPARED')
        self.assertEqual(repair.install(self.store), 'INTERRUPTED_REQUIRES_APPLY')
        self.assertEqual(self.apply(), 'APPLIED_NO_TRADE')

    def test_interruption_with_concurrent_source_change_refuses_overwrite(self):
        record = repair.make_plan(self.store)
        repair.n.atomic(self.journal, record)
        changed = self.funding.read_bytes() + b'\n# external change\n'
        self.funding.write_bytes(changed)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'CONCURRENT_TARGET_CHANGE'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_unrelated_file_added_during_install_blocks_second_write(self):
        real = repair.replace_exact
        def add_file(path, before, after):
            real(path, before, after)
            (self.f['engine'] / 'tools/surprise.py').write_bytes(b'NEW_FILE=True\n')
        original_funding = self.funding.read_bytes()
        with patch.object(repair, 'replace_exact', side_effect=add_file):
            with self.assertRaisesRegex(ValueError, 'UNRELATED_SOURCE_OR_SETTINGS_CHANGED'):
                self.apply()
        self.assertEqual(self.funding.read_bytes(), original_funding)
        self.assertEqual(repair.n.checkpoint(self.journal)['phase'], 'PREPARED')

    def test_resealed_journal_cannot_target_other_file(self):
        record = repair.make_plan(self.store)
        record['entries']['FUNDING']['path'] = str(self.claim)
        repair.n.atomic(self.journal, record)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'JOURNAL_TARGET_MISMATCH'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_resealed_journal_cannot_change_derived_bytes(self):
        import base64
        record = repair.make_plan(self.store)
        new = b'print("arbitrary replacement")\n'
        record['entries']['FUNDING']['after'] = base64.b64encode(new).decode()
        record['entries']['FUNDING']['afterSha256'] = repair.n.digest(new)
        repair.n.atomic(self.journal, record)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'JOURNAL_DERIVATION_CHANGED'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_guard_failure_creates_no_journal_or_source_change(self):
        before = self.snapshot()
        with patch.object(repair, 'gate', side_effect=ValueError('SYNTHETIC_GUARD')):
            with self.assertRaisesRegex(ValueError, 'SYNTHETIC_GUARD'):
                repair.install(self.store, apply=True)
        self.assertEqual(self.snapshot(), before)

    def test_off_hours_guard_boundaries(self):
        for hour, minute, allowed in ((7, 59, True), (8, 0, False), (12, 0, False),
                                       (15, 30, False), (15, 40, False), (15, 41, True), (20, 0, True)):
            clock = datetime(2026, 11, 11, hour, minute, tzinfo=timezone(timedelta(hours=9)))
            with self.subTest(clock=clock), patch.object(repair, 'datetime') as fake:
                fake.now.return_value = clock
                if allowed:
                    repair.no_market_window()
                else:
                    with self.assertRaisesRegex(ValueError, 'AFTER_HOURS_ONLY'):
                        repair.no_market_window()

    def test_process_probe_rejects_all_nonzero_outcomes_and_keeps_commands_private(self):
        for code in (2, 3, 4, 5):
            with self.subTest(code=code), patch.object(repair.subprocess, 'run') as run:
                run.return_value = subprocess.CompletedProcess([], code, 'PRIVATE_COMMAND', 'SECRET')
                with self.assertRaisesRegex(ValueError, 'ARK_WORKERS_UI_OR_UNREADABLE_PROCESS') as error:
                    repair.quiet()
                self.assertNotIn('PRIVATE', str(error.exception))
                self.assertNotIn('SECRET', str(error.exception))

    @unittest.skipUnless(os.name == 'nt', 'Windows PowerShell 5.1 parser')
    def test_real_windows_parser_for_process_guard(self):
        scripts = []
        def capture(args, **kwargs):
            scripts.append(Path(args[-1]).read_text(encoding='ascii'))
            return subprocess.CompletedProcess(args, 0)
        with patch.object(repair.subprocess, 'run', side_effect=capture):
            repair.quiet()
        target = Path(self.temp.name) / 'probe.ps1'
        target.write_text(scripts[0], encoding='ascii')
        harness = Path(self.temp.name) / 'parse.ps1'
        harness.write_text("param([string]$Target)\n$t=$null;$e=$null;[void][Management.Automation.Language.Parser]::ParseFile($Target,[ref]$t,[ref]$e);if(@($e).Count){exit 2};exit 0\n", encoding='ascii')
        result = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
                                 '-File',str(harness),'-Target',str(target)], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bom_and_crlf_are_preserved_for_both_sources(self):
        for path in (self.entry, self.funding):
            text = path.read_bytes().decode('utf-8-sig').replace('\r\n', '\n')
            path.write_bytes(b'\xef\xbb\xbf' + text.replace('\n', '\r\n').encode())
        self.apply()
        for path in (self.entry, self.funding):
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))
            self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))

    def test_finished_audit_allows_next_days_settings_without_writing_them(self):
        self.apply()
        data = json.loads(self.f['settings'].read_bytes())
        data['bootstrapConfigFile'] = str(self.f['private'] / 'next-day.json')
        fixtures.put(self.f['settings'], data)
        before = self.snapshot()
        self.assertEqual(repair.install(self.store), 'ALREADY_APPLIED')
        self.assertEqual(self.snapshot(), before)


class OpeningCompletionClockTests(unittest.TestCase):
    def setUp(self):
        self.helper = waits.OpeningWaitTests()
        self.helper.setUp()

    def test_first_read_cannot_run_past_budget_and_succeed(self):
        h = self.helper
        def delayed_read(path):
            h.elapsed = 1.0
            return h.envelope(), 'b' * 64
        h.reader.side_effect = delayed_read
        with self.assertRaisesRegex(ValueError, 'SOURCE_WAIT_TIMEOUT'):
            h.call()
        h.normalizer.assert_not_called()

    def test_first_normalization_cannot_run_past_budget_and_succeed(self):
        h = self.helper
        def delayed(*args):
            h.elapsed = 1.0
            return deepcopy(h.source)
        h.normalizer.side_effect = delayed
        with self.assertRaisesRegex(ValueError, 'SOURCE_WAIT_TIMEOUT'):
            h.call()

    def test_crossing_entry_cutoff_inside_normalization_is_rejected(self):
        h = self.helper
        clock = Mock(side_effect=[waits.AT, '2026-11-11T15:20:00+09:00'])
        with self.assertRaisesRegex(ValueError, 'ENTRY_WINDOW_CLOSED'):
            h.call(clock=clock)

    def test_return_clock_is_used_for_final_freshness_validation(self):
        h = self.helper
        later = (datetime.fromisoformat(waits.AT) + timedelta(seconds=0.1)).isoformat()
        result = h.call(clock=Mock(side_effect=[waits.AT, later]))
        self.assertEqual(result[3], later)


if __name__ == '__main__':
    unittest.main(verbosity=2)
