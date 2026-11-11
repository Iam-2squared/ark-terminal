"""Offline fixtures only: no Excel, broker, live entry or user-data access."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import no11_oneclick_display_v2 as display
import no11_oneclick_display_transform as migration
import install_no11_oneclick_display_v2 as installer
import test_no11_prestart_source_retry as fixtures

HERE = Path(__file__).resolve().parent
DAY = '2026-11-11'


def now(clock='20:21:00', day=DAY):
    return datetime.fromisoformat(day + 'T' + clock + '+09:00')


def put(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
    return path


def presentation(clock='20:21:00', **changes):
    params = dict(state={'mode': 'AFTER_CLOSE', 'reason': 'NIGHTLY_OPERATOR_BUTTON_AVAILABLE',
                         'canRequestTrade': False, 'canRunNightly': True},
                  now=now(clock), reserved={'state': 'RESERVED_RECORD', 'tradeRequested': False},
                  run={'state': 'NO_RECORD'}, data={'state': 'READY', 'target': '2026-11-12',
                  'count': 41, 'weekly': 'DONE'}, repair='APPLIED')
    params.update(changes)
    return display.present(**params)


class DisplayStateTests(unittest.TestCase):
    def test_closed_window_cannot_be_overwritten_by_old_reservation(self):
        out = presentation()
        self.assertEqual(out['phase'], 'AFTER_CLOSE')
        self.assertIn('CLOSED / 本日終了', out['text'])
        self.assertNotIn('RESERVED 09:00', out['text'])
        self.assertIn('予約履歴', out['text'])

    def test_preopen_reservation_is_explicitly_unverified_activity(self):
        out = presentation('08:59:59')
        self.assertIn('RESERVED 09:00 / 当日・稼働未確認', out['text'])
        self.assertFalse(out['liveVerified'])

    def test_expiration_boundary_has_no_permanent_reserved_state(self):
        self.assertIn('RESERVED 09:00', presentation('09:01:59')['text'])
        self.assertNotIn('RESERVED 09:00', presentation('09:02:00')['text'])

    def test_entry_close_does_not_claim_held_position_management_is_finished(self):
        out = presentation('15:20:00', run={'state': 'REGISTERED', 'collector': 'CONNECTED'})
        self.assertEqual(out['phase'], 'ENTRY_CLOSED')
        self.assertIn('新規受付終了', out['text'])
        self.assertIn('稼働未確認', out['text'])
        self.assertNotIn('本日終了', out['text'])

    def test_failure_record_takes_priority_over_launch_marker(self):
        out = presentation(reserved={'state': 'ATTEMPT_RECORDED', 'tradeRequested': True},
                           run={'state': 'FAILURE_RECORDED', 'collector': 'CLOSED',
                                'reason': 'NO11_BROKER_SOURCE_UNAVAILABLE'})
        self.assertIn('STOPPED', out['text'])
        self.assertIn('NO11_BROKER_SOURCE_UNAVAILABLE', out['details'])
        self.assertNotIn('START REQUESTED', out['text'])

    def test_unverified_records_are_not_called_running(self):
        out = presentation(run={'state': 'UNVERIFIED'})
        self.assertIn('UNVERIFIED', out['trading'])
        self.assertFalse(out['liveVerified'])
        self.assertFalse(out['orderTransmission'])

    def test_request_and_registered_run_never_claim_live_success(self):
        cases = ({'state': 'REGISTERED'}, {'state': 'COLLECTOR_CLOSED_RECORD'})
        for run in cases:
            with self.subTest(run=run):
                out = presentation(run=run)
                self.assertNotIn('LIVE RUNNING', out['text'])
                self.assertFalse(out['liveVerified'])

    def test_next_data_is_separate_from_today_and_preserves_count(self):
        out = presentation()
        self.assertIn('TODAY 2026-11-11', out['text'])
        self.assertIn('NEXT 11/12 READY 41銘柄', out['text'])
        self.assertEqual(len(out['text'].splitlines()), 4)

    def test_today_data_is_not_mislabeled_next(self):
        out = presentation('08:45:00', data={'state': 'READY', 'target': DAY, 'count': 42, 'weekly': 'DONE'})
        self.assertIn('TODAY 11/11 READY 42銘柄', out['text'])

    def test_invalid_missing_and_weekly_unverified_data_have_distinct_display(self):
        self.assertIn('NOT READY', presentation(data={'state': 'NOT_READY'})['text'])
        self.assertIn('データ要確認', presentation(data={'state': 'INVALID'})['text'])
        out = presentation(data={'state': 'READY', 'target': '2026-11-12', 'count': 41, 'weekly': 'UNVERIFIED'})
        self.assertIn('WEEKLY要確認', out['text'])

    def test_repair_installed_does_not_imply_live_verified(self):
        out = presentation()
        self.assertIn('適用済み', out['text'])
        self.assertFalse(out['liveVerified'])
        self.assertIn('INSTALL INCOMPLETE', presentation(repair='INCOMPLETE')['text'])

    def test_weekend_is_not_displayed_as_pending_market_start(self):
        out = presentation(state={'reason': 'NON_TRADING_DAY'}, now=now('08:40:00', '2026-11-14'))
        self.assertEqual(out['phase'], 'NO_SESSION')
        self.assertNotIn('RESERVED 09:00', out['text'])

    def test_copy_is_bilingual_but_no_ansi_script_literal_is_required(self):
        out = presentation()
        encoded = json.dumps(out, ensure_ascii=True)
        encoded.encode('ascii')
        self.assertIn('状態更新', json.loads(encoded)['buttons']['refresh'])
        self.assertTrue(all(len(line) <= 90 for line in out['text'].splitlines()))

    def test_reducer_does_not_mutate_permission_fields(self):
        state = {'canRequestTrade': False, 'canRunNightly': True, 'requiresSameDayApproval': True}
        old = deepcopy(state)
        presentation(state=state)
        self.assertEqual(state, old)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.queue = self.root / ('PREOPEN-' + DAY + '.request.json')
        self.claim = self.root / ('PREOPEN-' + DAY + '.execution-claimed')
        self.request = {'schemaId': 'ARK_NO11_PREOPEN_STANDBY_REQUEST_V1', 'sessionDate': DAY,
                        'sameDayExplicitOrderApproval': True, 'nonce': 'f' * 32,
                        'requestedAtJst': DAY + 'T08:35:00+09:00',
                        'earliestTradeStartJst': DAY + 'T09:00:00+09:00',
                        'expiresAtJst': DAY + 'T09:02:00+09:00',
                        'tradeLaunchedAtArm': False, 'orderTransmissionAtArm': False}

    def test_today_queue_becomes_expired_without_deleting_evidence(self):
        put(self.queue, self.request)
        before = self.queue.read_bytes()
        self.assertEqual(display.reservation(self.root, DAY, now('08:45:00'))['state'], 'RESERVED_RECORD')
        self.assertEqual(display.reservation(self.root, DAY, now())['state'], 'EXPIRED')
        self.assertEqual(self.queue.read_bytes(), before)

    def test_used_attempt_cannot_be_displayed_as_waiting(self):
        put(self.queue, self.request)
        self.claim.write_text('PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED|' + DAY + '|' + 'f' * 32)
        self.assertEqual(display.reservation(self.root, DAY, now('09:01:00'))['state'], 'ATTEMPT_RECORDED')

    def test_next_day_does_not_reuse_yesterdays_queue_or_claim(self):
        put(self.queue, self.request)
        self.claim.write_text('PRESERVED_OLD_CLAIM')
        result = display.reservation(self.root, '2026-11-12', now('08:45:00', '2026-11-12'))
        self.assertEqual(result['state'], 'NONE')
        self.assertTrue(self.queue.exists())
        self.assertTrue(self.claim.exists())

    def test_corrupt_claim_or_expiry_is_not_certified(self):
        put(self.queue, self.request)
        self.claim.write_text('MISMATCH')
        self.assertEqual(display.reservation(self.root, DAY, now())['state'], 'UNVERIFIED')
        self.claim.unlink()
        self.request['expiresAtJst'] = '2026-11-12T09:02:00+09:00'
        put(self.queue, self.request)
        self.assertEqual(display.reservation(self.root, DAY, now())['state'], 'UNVERIFIED')

    def test_duplicate_json_keys_fail_closed(self):
        self.queue.write_text('{"status":1,"status":2}')
        self.assertEqual(display.reservation(self.root, DAY, now())['state'], 'UNVERIFIED')

    def test_active_pointer_is_date_scoped_and_errors_are_redacted(self):
        private = self.root / 'private'
        private.mkdir()
        boot = put(self.root / 'bootstrap.json', {'privateRoot': str(private)})
        settings = {'bootstrapConfigFile': str(boot)}
        run = private / ('session-' + DAY + '-' + 'a' * 32)
        run.mkdir()
        put(private / ('received-session-' + DAY + '.active.json'),
            {'schemaId': 'ARK_NO11_RECEIVED_ACTIVE_RUN_V1', 'sessionDate': DAY, 'runRoot': str(run)})
        put(run / 'attempt-0001/attempt.json', {'status': 'CLOSED'})
        put(run / 'controller-failure.json', {'reason': 'secret account 123'})
        result = display.run_evidence(settings, DAY)
        self.assertEqual(result['state'], 'FAILURE_RECORDED')
        self.assertEqual(result['reason'], 'UNCLASSIFIED')
        self.assertEqual(display.run_evidence(settings, '2026-11-12')['state'], 'NO_RECORD')

    def test_old_failure_does_not_prove_new_attempt_failed(self):
        private = self.root / 'private'
        private.mkdir()
        boot = put(self.root / 'bootstrap.json', {'privateRoot': str(private)})
        run = private / ('session-' + DAY + '-' + 'a' * 32)
        run.mkdir()
        put(private / ('received-session-' + DAY + '.active.json'),
            {'schemaId': 'ARK_NO11_RECEIVED_ACTIVE_RUN_V1', 'sessionDate': DAY, 'runRoot': str(run)})
        failure = put(run / 'controller-failure.json', {'reason': 'NO11_BROKER_SOURCE_UNAVAILABLE'})
        os.utime(failure, ns=(1_000_000_000, 1_000_000_000))
        put(run / 'attempt-0002/attempt.json', {'status': 'CONNECTED'})
        result = display.run_evidence({'bootstrapConfigFile': str(boot)}, DAY)
        self.assertEqual(result['state'], 'REGISTERED')
        self.assertTrue(result['previousFailure'])

    def test_registered_data_validator_hash_is_checked_before_import(self):
        tool = self.root / 'no11_selection_status.py'
        tool.write_text('raise AssertionError("must not execute")')
        resume = self.root / 'resume.py'
        resume.write_text('# fixture')
        binding = {'nightlyResumeTool': str(resume), 'nightlyResumeValidatorSha256': '0' * 64}
        self.assertEqual(display.prepared_data(self.root / 'binding.json', binding, now())['state'], 'UNVERIFIED')


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.f = fixtures.fixture(Path(self.tmp.name))
        self.store = self.f['store']
        self.home = self.store / 'oneclick'
        self.home.mkdir()
        self.launcher = self.home / 'Start-No11OneClick.ps1'
        raw = (HERE / 'Start-No11OneClick.ps1').read_bytes()
        # A local white-theme addition plus unrelated customization must survive.
        raw = raw.replace(b'FromArgb(29,32,38)', b'FromArgb(255,255,255)')
        raw += b'\n# LOCAL_WHITE_AND_SELECTION_CUSTOMIZATION_MUST_STAY\n'
        self.launcher.write_bytes(raw)
        self.legacy = self.home / 'oneclick_status.py'
        self.legacy.write_bytes((HERE / 'oneclick_status.py').read_bytes())
        self.extra = self.home / 'local_helper.py'
        self.extra.write_bytes(b'LOCAL_FIX=1\n')
        self.journal = self.store / installer.JOURNAL

    def apply(self):
        with patch.object(installer, 'gate'), patch.object(installer, 'parse_launcher'):
            return installer.install(self.store, apply=True)

    def snapshot(self):
        return {p: p.read_bytes() for p in self.f['root'].rglob('*') if p.is_file()}

    def test_audit_is_readonly_and_does_not_run_processes(self):
        before = self.snapshot()
        with patch.object(installer.subprocess, 'run', side_effect=AssertionError('NO_PROCESS')):
            self.assertEqual(installer.install(self.store), 'READY_NOT_APPLIED')
        self.assertEqual(self.snapshot(), before)

    def test_install_changes_only_launcher_and_adds_pinned_sidecars(self):
        before = self.snapshot()
        self.assertEqual(self.apply(), 'APPLIED_NO_TRADE')
        changed = {p for p, raw in before.items() if p.read_bytes() != raw}
        self.assertEqual(changed, {self.launcher})
        self.assertIn(b'LOCAL_WHITE_AND_SELECTION_CUSTOMIZATION_MUST_STAY', self.launcher.read_bytes())
        self.assertIn(b'FromArgb(255,255,255)', self.launcher.read_bytes())
        self.assertEqual(installer.n.checkpoint(self.journal)['phase'], 'COMPLETE')
        self.assertEqual(installer.install(self.store), 'ALREADY_APPLIED')
        self.assertEqual(self.apply(), 'ALREADY_APPLIED')

    def test_action_callbacks_and_enabled_guards_are_byte_identical(self):
        before = self.launcher.read_bytes()
        after = migration.transform(before)
        self.assertEqual(before.split(b'$refresh.Add_Click')[1], after.split(b'$refresh.Add_Click')[1])
        for name in ('trade', 'nightly', 'review'):
            token = ('$' + name + '.Enabled=').encode()
            self.assertEqual([l for l in before.splitlines() if token in l],
                             [l for l in after.splitlines() if token in l])

    def test_bom_crlf_and_transform_idempotence(self):
        raw = self.launcher.read_bytes().decode('utf-8-sig').replace('\r\n', '\n')
        for prefix, newline in ((b'', '\n'), (b'', '\r\n'), (b'\xef\xbb\xbf', '\r\n')):
            before = prefix + raw.replace('\n', newline).encode()
            after = migration.transform(before)
            self.assertEqual(migration.transform(after), after)
            if prefix:
                self.assertTrue(after.startswith(prefix))
            if newline == '\r\n':
                self.assertNotIn(b'\n', after.replace(b'\r\n', b''))

    def test_unknown_display_region_is_not_overwritten(self):
        self.launcher.write_bytes(self.launcher.read_bytes().replace(b'09:00 START RESERVED - check logs', b'UNREVIEWED_DISPLAY'))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_DISPLAY_SOURCE'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_unknown_native_authority_is_not_imported_or_replaced(self):
        self.legacy.write_bytes(self.legacy.read_bytes() + b'# unknown\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_NATIVE_STATUS_SOURCE'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_interruption_before_launcher_switch_preserves_original_and_can_continue(self):
        before = self.launcher.read_bytes()
        with patch.object(installer, 'replace_exact', side_effect=OSError('fixture interruption')):
            with self.assertRaises(OSError):
                self.apply()
        self.assertEqual(self.launcher.read_bytes(), before)
        self.assertEqual(installer.install(self.store), 'INTERRUPTED_REQUIRES_APPLY')
        self.assertEqual(self.apply(), 'APPLIED_NO_TRADE')

    def test_unknown_partial_sidecar_is_never_overwritten(self):
        with patch.object(installer, 'replace_exact', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                self.apply()
        sidecar = self.home / installer.DISPLAY
        sidecar.write_bytes(b'# unknown edit\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'SIDECAR_CHANGED'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_no_journal_reset_when_local_launcher_changes(self):
        self.apply()
        self.launcher.write_bytes(self.launcher.read_bytes() + b'# concurrent\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'CONCURRENT_LAUNCHER_CHANGE'):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_day_rollover_does_not_require_reinstallation(self):
        self.apply()
        settings = json.loads(self.f['settings'].read_bytes())
        settings['bootstrapConfigFile'] = str(self.f['private'] / 'tomorrow.json')
        put(self.f['settings'], settings)
        self.assertEqual(installer.install(self.store), 'ALREADY_APPLIED')

    def test_installed_wrapper_returns_exact_native_permissions_at_all_windows(self):
        self.apply()
        installed = display.module(self.home / installer.DISPLAY, 'installed_display_test')
        native = display.module(self.legacy, 'legacy_display_test')
        for day in (DAY, '2026-11-12', '2026-11-14'):
            for clock in ('07:00:00', '08:30:00', '09:00:00', '09:02:00', '15:20:00', '18:00:00', '23:59:59'):
                with self.subTest(day=day, clock=clock):
                    at = now(clock, day)
                    old = native.inspect(self.f['settings'], self.f['binding'], at=at)
                    new = installed.inspect(self.f['settings'], self.f['binding'], at=at)
                    new.pop('presentation')
                    self.assertEqual(old, new)

    def test_changed_native_dependency_blocks_wrapper(self):
        self.apply()
        installed = display.module(self.home / installer.DISPLAY, 'installed_display_tamper')
        self.legacy.write_bytes(self.legacy.read_bytes() + b'# changed\n')
        with self.assertRaisesRegex(ValueError, 'DISPLAY_DEPENDENCY_CHANGED'):
            installed.native_inspector()

    def test_process_gate_keeps_distinct_redacted_failures(self):
        for code, expected in ((2, 'ARK_WORKER_OR_UI_RUNNING'), (3, 'PROCESS_COMMAND_UNREADABLE'),
                               (4, 'PROCESS_QUERY_FAILED'), (5, 'PROCESS_QUERY_EMPTY')):
            with self.subTest(code=code), patch.object(installer.subprocess, 'run') as run:
                run.return_value = subprocess.CompletedProcess([], code, 'PRIVATE', 'SECRET')
                with self.assertRaisesRegex(ValueError, expected) as exc:
                    installer.quiet()
                self.assertNotIn('PRIVATE', str(exc.exception))

    def test_time_guard_is_not_date_specific(self):
        for year in (2026, 2027, 2030):
            for hour, minute, allowed in ((7, 59, True), (8, 0, False), (15, 40, False), (15, 41, True), (20, 0, True)):
                at = datetime(year, 1, 4, hour, minute, tzinfo=display.JST)
                with self.subTest(at=at), patch.object(installer, 'datetime') as clock:
                    clock.now.return_value = at
                    if allowed:
                        installer.off_hours()
                    else:
                        with self.assertRaisesRegex(ValueError, 'AFTER_HOURS_ONLY'):
                            installer.off_hours()

    @unittest.skipUnless(os.name == 'nt', 'Windows PowerShell parser')
    def test_real_powershell_parser_accepts_migrated_white_launcher(self):
        installer.parse_launcher(migration.transform(self.launcher.read_bytes()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
