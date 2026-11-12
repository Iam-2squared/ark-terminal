"""Synthetic installation test: real journals, no orders, Excel or LIVE process.

The prior display V2 + overlay are installed in a temporary fake store by the
published migration modules; this exercises the actual existing migration
recipes, including local white-theme customizations and retry permission lines.
"""
from __future__ import annotations

from datetime import datetime
import subprocess
import io as io_stream
from contextlib import redirect_stdout
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import install_no11_anytime_preopen as candidate
import install_no11_oneclick_display_v2 as base
import install_no11_oneclick_display_overlay_compat as overlay
import no11_nightly_resume as io
import test_no11_oneclick_display_overlay_compat as overlay_tests
import test_no11_oneclick_display_v2 as fixture

HERE = Path(__file__).resolve().parent


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.InstallTests("test_audit_is_readonly_and_does_not_run_processes")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.store = self.case.store
        self.home = self.store / "oneclick"
        self.launcher = self.case.launcher
        self.worker = self.home / candidate.WORKER
        self.launcher.write_bytes(overlay_tests.make_source())
        self.worker.write_bytes((HERE / candidate.WORKER).read_bytes())
        with patch.object(base, "gate"), patch.object(base, "parse_launcher"):
            self.assertEqual(base.install(self.store, apply=True), "APPLIED_NO_TRADE")
            self.assertEqual(overlay.install(self.store, apply=True), "APPLIED_NO_TRADE")
        self.previous = {
            self.store / base.JOURNAL: (self.store / base.JOURNAL).read_bytes(),
            self.store / overlay.JOURNAL: (self.store / overlay.JOURNAL).read_bytes(),
            self.home / base.DISPLAY: (self.home / base.DISPLAY).read_bytes(),
            self.home / base.CONTRACT: (self.home / base.CONTRACT).read_bytes(),
            self.case.legacy: self.case.legacy.read_bytes(),
            self.case.extra: self.case.extra.read_bytes(),
        }

    def run_apply(self):
        with patch.object(candidate, "gate"), patch.object(base, "parse_launcher"):
            return candidate.install(self.store, apply=True)

    def snapshots(self):
        return {p: p.read_bytes() for p in self.case.f['root'].rglob('*') if p.is_file()}

    def assert_originals(self):
        for p, raw in self.previous.items():
            self.assertEqual(p.read_bytes(), raw, str(p))

    def test_gate_probe_reproduces_strict_quiet_process_filter_without_writes(self):
        from io import StringIO
        from contextlib import redirect_stdout
        old = self.snapshots()
        native_need = candidate.need
        def allow_test_host(check, reason):
            if reason == 'GATE_PROBE_WINDOWS_ONLY':
                return None
            return native_need(check, reason)
        def fake_run(argv, **kwargs):
            self.assertIn('-File', argv)
            probe = Path(argv[-1]).read_text(encoding='ascii')
            self.assertIn("Get-CimInstance Win32_Process", probe)
            self.assertIn("No11|no12.*(nightly|collector)", probe)
            self.assertIn("ProcessId -notin @($PID,", probe)
            self.assertIn("NO11_GATE_MATCH=PID=", probe)
            self.assertNotIn('OWN_PROCESS', probe)
            self.assertNotIn('PARENT_PROCESS', probe)
            return subprocess.CompletedProcess(
                argv, 0, "NO11_GATE_ANCESTORS=4\nNO11_GATE_UNREADABLE=0\n"
                "NO11_GATE_MATCHES=1\n"
                "NO11_GATE_MATCH=PID=1357|PPID=2468|CLASS=INSTALLER|REL=ANCESTOR\n", '')
        buf = StringIO()
        with patch.object(candidate, 'need', side_effect=allow_test_host), \
             patch.object(candidate.subprocess, 'run', side_effect=fake_run), \
             redirect_stdout(buf):
            self.assertEqual(candidate.gate_probe(), 0)
        self.assertIn("NO11_GATE_MATCHES=1", buf.getvalue())
        self.assertIn("CLASS=INSTALLER|REL=ANCESTOR", buf.getvalue())
        self.assertEqual(old, self.snapshots())

    def test_probe_rejects_untrusted_raw_process_command_output(self):
        from io import StringIO
        from contextlib import redirect_stdout
        native_need = candidate.need
        def allow_test_host(check, reason):
            if reason == 'GATE_PROBE_WINDOWS_ONLY':
                return None
            return native_need(check, reason)
        bad = subprocess.CompletedProcess([], 0,
            'NO11_GATE_MATCH=PID=1|COMMANDLINE=SECRET ACCOUNT\n', '')
        with patch.object(candidate, 'need', side_effect=allow_test_host), \
             patch.object(candidate.subprocess, 'run', return_value=bad), \
             redirect_stdout(StringIO()):
            with self.assertRaisesRegex(ValueError, 'GATE_PROBE_INVALID_OUTPUT'):
                candidate.gate_probe()

    def test_audit_does_not_create_journal_or_new_sidecar_or_modify_any_source(self):
        before = self.snapshots()
        self.assertEqual(candidate.install(self.store), "READY_NOT_APPLIED")
        self.assertEqual(self.snapshots(), before)
        self.assertFalse((self.store / candidate.JOURNAL).exists())
        self.assert_originals()

    def test_install_and_rerun_are_idempotent_and_old_chain_stays_proven(self):
        before = self.snapshots()
        self.assertEqual(self.run_apply(), "APPLIED_NO_TRADE")
        self.assertEqual(candidate.install(self.store), "ALREADY_APPLIED")
        self.assertEqual(self.run_apply(), "ALREADY_APPLIED")
        self.assert_originals()
        for p in before:
            if p not in (self.launcher, self.worker):
                self.assertEqual(before[p], p.read_bytes())
        self.assertNotEqual(before[self.launcher], self.launcher.read_bytes())
        self.assertNotEqual(before[self.worker], self.worker.read_bytes())
        saved = io.checkpoint(self.store / candidate.JOURNAL)
        self.assertEqual(saved['phase'], 'COMPLETE')
        self.assertEqual(set(saved['after']), set(candidate.NAMES))
        self.assertEqual(saved['baseJournalSha256'], hashlib.sha256(
            self.previous[self.store / base.JOURNAL]).hexdigest())
        self.assertEqual(saved['overlayJournalSha256'], hashlib.sha256(
            self.previous[self.store / overlay.JOURNAL]).hexdigest())

    def test_premarket_overlay_changes_copy_not_trade_permission(self):
        state, plan = candidate.audit(self.store)
        self.assertEqual(state, "READY_NOT_APPLIED")
        chain = candidate.original_chain(self.store)
        worker, output = candidate.validate_plan(chain, plan)
        text = output[candidate.LAUNCHER].decode('utf-8-sig')
        self.assertIn("ARK_NO11_ANYTIME_STANDBY_OVERLAY_COPY_V1", text)
        self.assertIn("('BEFORE_OPEN','PREOPEN')", text)
        self.assertIn("'STANDBY READY  /  09:00'", text)
        self.assertIn("if($preopen)", text)
        for token in ("$trade.Enabled=", "$nightly.Enabled=", "$review.Enabled="):
            old = [x for x in chain['oldLauncher'].decode('utf-8-sig').splitlines()
                   if token in x]
            new = [x for x in text.splitlines() if token in x]
            self.assertEqual(old, new)

    def test_source_diagnostic_success_and_missing_v2_anchor_is_reported_readonly(self):
        before = self.snapshots()
        buf = io_stream.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(candidate.diagnose(self.store), 0)
        self.assertIn('NO11_ANYTIME_DIAG_RESULT=READY_NOT_APPLIED', buf.getvalue())
        self.assertEqual(self.snapshots(), before)
        path = self.store / base.JOURNAL
        saved = io.checkpoint(path)
        original_before = base64.b64decode(saved['before'], validate=True)
        self.assertIn(b'08:30 STANDBY READY', original_before)
        corrupted_before = original_before.replace(
            b'08:30 STANDBY READY', b'08:33 STANDBY READY', 1)
        saved['before'] = base64.b64encode(corrupted_before).decode('ascii')
        io.atomic(path, saved)
        changed = self.snapshots()
        buf = io_stream.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(candidate.diagnose(self.store), 2)
        self.assertIn('NO11_ANYTIME_DIAG_V2_BEFORE_DERIVATION=BLOCKED',
                      buf.getvalue())
        self.assertNotIn('08:33 STANDBY READY', buf.getvalue())
        self.assertEqual(self.snapshots(), changed)

    def test_overlay_splices_only_verified_first_line_not_local_body(self):
        chain = candidate.original_chain(self.store)
        old = chain['oldLauncher']
        local = old.replace(
            b"       $disabledTradeOverlay.Text='TRADING PAUSED",
            b"          $disabledTradeOverlay.Text='TRADING PAUSED", 1)
        self.assertNotEqual(old, local)
        import no11_anytime_preopen as widening
        import no11_oneclick_display_transform as migration
        prepared = widening.ui(local).decode('utf-8-sig')
        self.assertEqual(prepared.count(candidate.OVERLAY_OLD), 1)
        patched = migration.replace_regions(prepared, [
            (candidate.OVERLAY_OLD, candidate.OVERLAY_NEW)])
        self.assertIn("          $disabledTradeOverlay.Text='TRADING PAUSED", patched)
        self.assertEqual(
            migration.replace_regions(patched, [
                (candidate.OVERLAY_NEW, candidate.OVERLAY_OLD)]),
            prepared)
        self.assertEqual(
            [l for l in prepared.splitlines() if '$trade.Enabled=' in l],
            [l for l in patched.splitlines() if '$trade.Enabled=' in l])

    def test_new_read_only_display_has_bound_contract_and_old_sidecars_intact(self):
        self.run_apply()
        new = self.home / candidate.NEW_DISPLAY
        contract = self.home / candidate.NEW_CONTRACT
        item = json.loads(contract.read_text(encoding='utf-8'))
        self.assertEqual(item['schemaId'], candidate.NEW_CONTRACT_SCHEMA)
        self.assertEqual(item['displaySha256'], hashlib.sha256(new.read_bytes()).hexdigest())
        self.assertEqual(item['legacyStatusSha256'],
                         hashlib.sha256(self.case.legacy.read_bytes()).hexdigest())
        self.assertFalse(item['orderTransmission'])
        self.assertFalse(item['authorizationSourceChanged'])
        self.assertIn(candidate.NEW_DISPLAY.encode(), self.launcher.read_bytes())
        self.assertNotIn(
            b"$statusTool=Join-Path $PSScriptRoot 'no11_oneclick_display_v2.py'",
            self.launcher.read_bytes())
        # This imported module checks the new contract and native legacy status.
        import importlib.util
        spec = importlib.util.spec_from_file_location('ark_anytime_installed_test', new)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(callable(module.native_inspector()))
        self.assert_originals()

    def test_fail_closed_tampered_old_v2_or_overlay_receipt(self):
        for source in (self.store / base.JOURNAL, self.store / overlay.JOURNAL,
                       self.home / base.DISPLAY, self.home / base.CONTRACT):
            with self.subTest(source=source.name):
                original = source.read_bytes()
                source.write_bytes(original + b'# unknowable\n')
                snapshot = self.snapshots()
                with self.assertRaises(ValueError):
                    candidate.install(self.store)
                self.assertEqual(self.snapshots(), snapshot)
                source.write_bytes(original)

    def test_unknown_local_worker_and_launcher_refused(self):
        for source in (self.worker, self.launcher):
            with self.subTest(source=source.name):
                old = source.read_bytes()
                source.write_bytes(old + b'\n# unknown source change\n')
                snapshot = self.snapshots()
                with self.assertRaises(ValueError):
                    candidate.install(self.store)
                self.assertEqual(self.snapshots(), snapshot)
                source.write_bytes(old)

    def test_interruption_before_worker_commit_is_resumable_without_guessing(self):
        before = self.worker.read_bytes()
        with patch.object(candidate, "gate"), patch.object(base, "parse_launcher"), patch.object(
                base, "replace_exact", side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):
                candidate.install(self.store, apply=True)
        self.assertEqual(self.worker.read_bytes(), before)
        self.assertEqual(candidate.install(self.store), "INTERRUPTED_REQUIRES_APPLY")
        self.assertEqual(self.run_apply(), "APPLIED_NO_TRADE")
        self.assert_originals()

    def test_interruption_after_worker_commit_preserves_receipt_and_resume(self):
        real = base.replace_exact
        def interrupted(path, before, after):
            if path == self.launcher:
                raise OSError("simulated lost power before white launcher swap")
            real(path, before, after)
        with patch.object(candidate, "gate"), patch.object(base, "parse_launcher"), patch.object(
                base, "replace_exact", side_effect=interrupted):
            with self.assertRaises(OSError):
                candidate.install(self.store, apply=True)
        self.assertEqual(candidate.install(self.store), "INTERRUPTED_REQUIRES_APPLY")
        self.assertNotEqual(self.worker.read_bytes(),
                            (HERE / candidate.WORKER).read_bytes())
        self.assertEqual(self.run_apply(), "APPLIED_NO_TRADE")
        self.assert_originals()

    def test_interruption_after_launcher_swap_before_final_receipt_is_resumable(self):
        original_atomic = io.atomic
        def interrupted(path, record):
            if (Path(path).name == candidate.JOURNAL and
                    record.get("phase") == "COMPLETE"):
                raise OSError("crash after last file before commit")
            original_atomic(path, record)
        with patch.object(candidate, "gate"), patch.object(base, "parse_launcher"), patch.object(
                io, "atomic", side_effect=interrupted):
            with self.assertRaises(OSError):
                candidate.install(self.store, apply=True)
        self.assertEqual(candidate.install(self.store), "INTERRUPTED_REQUIRES_APPLY")
        self.assertEqual(self.run_apply(), "APPLIED_NO_TRADE")

    def test_wrong_new_sidecar_blocks_unknown_preexisting_source(self):
        target = self.home / candidate.NEW_DISPLAY
        target.write_bytes(b"# unknown source\n")
        before = self.snapshots()
        with self.assertRaises(ValueError):
            candidate.install(self.store)
        self.assertEqual(self.snapshots(), before)

    def test_complete_new_receipt_refuses_post_install_tampering(self):
        self.run_apply()
        for source in (self.worker, self.launcher,
                       self.home / candidate.NEW_DISPLAY,
                       self.home / candidate.NEW_CONTRACT):
            with self.subTest(source=source.name):
                raw = source.read_bytes()
                source.write_bytes(raw + b'# modified\n')
                with self.assertRaises(ValueError):
                    candidate.install(self.store)
                source.write_bytes(raw)
        self.assertEqual(candidate.install(self.store), "ALREADY_APPLIED")

    def test_old_date_scoped_claims_and_daily_data_survive(self):
        existing = self.store / "PREOPEN-2026-11-12.execution-claimed"
        existing.write_text("PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED|2026-11-12|test")
        before = existing.read_bytes()
        self.run_apply()
        self.assertEqual(existing.read_bytes(), before)
        self.assert_originals()

    @unittest.skipUnless(os.name == 'nt', 'Requires actual Windows PowerShell')
    def test_real_powershell_parser_accepts_new_white_oneclick(self):
        # Parser, not execution. Never calls form or Trade.
        state, saved = candidate.audit(self.store)
        self.assertEqual(state, "READY_NOT_APPLIED")
        chain = candidate.original_chain(self.store)
        worker, after = candidate.validate_plan(chain, saved)
        base.parse_launcher(after[candidate.LAUNCHER])
        base.parse_launcher(after[candidate.WORKER])


if __name__ == "__main__":
    unittest.main(verbosity=2)
