"""Regression coverage for the observed Windows OneClick V2 overlay collision.

Uses a synthetic existing white UI plus the published selection and retry
transforms. Does not touch the user's PC or execute LIVE entry actions.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

import install_no11_oneclick_display_overlay_compat as repair
import install_no11_oneclick_display_v2 as old
import no11_oneclick_display_transform as migration
import no11_nightly_resume as journal_io
import patch_oneclick_selection_display as selection
import patch_oneclick_preorder_retry as retry
import test_no11_oneclick_display_v2 as fixtures

HERE = Path(__file__).resolve().parent
EXTRA_OVERLAY = """  if($trading -match 'ENTRY HALTED'){
       $disabledTradeOverlay.Text='TRADING PAUSED  /  RECOVERY REVIEW REQUIRED'
   }
   elseif($s.mode -ceq 'AFTER_CLOSE'){
       $disabledTradeOverlay.Text='TRADING CLOSED FOR TODAY'
   }
   elseif($s.reason -ceq 'NEW_ENTRY_WINDOW_CLOSED'){
       $disabledTradeOverlay.Text='NEW ENTRIES CLOSED'
   }
   else{
       $disabledTradeOverlay.Text='TRADING UNAVAILABLE  /  CHECK STATUS'
   }
"""
OVERLAY_CREATION = (
    "$disabledTradeOverlay=New-Object System.Windows.Forms.Label\n"
    "$form.Controls.Add($disabledTradeOverlay)\n"
)


def make_source(*, bom=False, crlf=False):
    raw = (HERE / "Start-No11OneClick.ps1").read_bytes()
    raw = raw.replace(b"FromArgb(29,32,38)", b"FromArgb(255,255,255)")
    raw = selection.patch(retry.patch_text(raw))
    old_text = raw.decode("utf-8-sig").replace("\r\n", "\n")
    assert old_text.count("function RefreshUi{") == 1
    old_text = old_text.replace("function RefreshUi{",
                                OVERLAY_CREATION + "function RefreshUi{", 1)
    anchor = "  $trade.Enabled="
    assert old_text.count(anchor) == 1
    old_text = old_text.replace(anchor, EXTRA_OVERLAY + anchor, 1)
    if crlf:
        old_text = old_text.replace("\n", "\r\n")
    return (b"\xef\xbb\xbf" if bom else b"") + old_text.encode("utf-8")


def existing_v2_install(case, raw):
    case.launcher.write_bytes(raw)
    with patch.object(old, "gate"), patch.object(old, "parse_launcher"):
        assert old.install(case.store, apply=True) == "APPLIED_NO_TRADE"
    return case.launcher.read_bytes()


class MigrationTests(unittest.TestCase):
    def test_derived_two_hunk_migration_is_reversible_and_preserves_permissions(self):
        for bom in (False, True):
            for crlf in (False, True):
                with self.subTest(bom=bom, crlf=crlf):
                    before = migration.transform(make_source(bom=bom, crlf=crlf))
                    after = repair.change(before)
                    self.assertIn(repair.MARK.encode(), after)
                    self.assertIn(b"$trading=[string]$view.trading", after)
                    self.assertIn(b"else{[string]$view.buttons.trade}", after)
                    self.assertNotIn(b"if($retryReady){'RETRY START TRADING / NORMAL MAX3'}else{'START TRADING   /   NORMAL MAX3'}", after)
                    self.assertEqual(before.count(b"$trade.Add_Click"), after.count(b"$trade.Add_Click"))
                    self.assertEqual(before.split(b"$refresh.Add_Click")[1],
                                     after.split(b"$refresh.Add_Click")[1])
                    for name in ("trade", "nightly", "review"):
                        needle = ("$" + name + ".Enabled=").encode()
                        self.assertEqual([line for line in before.splitlines() if needle in line],
                                         [line for line in after.splitlines() if needle in line])
                    self.assertEqual(after.startswith(b"\xef\xbb\xbf"), bom)
                    self.assertEqual((b"\r\n" in after), crlf)
                    with self.assertRaisesRegex(ValueError, "ALREADY_CHANGED"):
                        repair.change(after)

    def test_rejects_unknown_or_damaged_overlay_without_weakening_a_gate(self):
        before = migration.transform(make_source())
        for changed in (
            before.replace(b"if($trading -match 'ENTRY HALTED')",
                           b"if($trading -match 'UNKNOWN')"),
            before.replace(b"$disabledTradeOverlay=New-Object",
                           b"$disabledTradeOverlay=Unexpected-Object"),
            before.replace(b"$trade.Enabled=", b"$trade.Enabled=$true;"),
            before.replace(b"else{'START TRADING   /   NORMAL MAX3'}",
                           b"else{'UNKNOWN_CAPTION'}"),
            before.replace(b"$script:No11DisplayTip.SetToolTip($status,[string]$view.details)",
                           b"SetTooltip-Unknown"),
        ):
            with self.subTest(modified=changed != before):
                with self.assertRaises(ValueError):
                    repair.change(changed)


class InstalledTests(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.InstallTests("test_audit_is_readonly_and_does_not_run_processes")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.launcher = self.case.launcher
        self.before_install = make_source()
        self.v2 = existing_v2_install(self.case, self.before_install)
        self.store = self.case.store
        self.receipt = self.store / repair.JOURNAL
        self.previous_receipt = self.store / old.JOURNAL

    def apply(self):
        with patch.object(repair.previous, "gate"), patch.object(repair.previous, "parse_launcher"):
            return repair.install(self.store, apply=True)

    def test_audit_is_read_only_and_old_receipt_is_untouched(self):
        old_record = self.previous_receipt.read_bytes()
        old_launcher = self.launcher.read_bytes()
        with patch.object(repair.previous, "gate", side_effect=AssertionError("NO_PROCESS")):
            self.assertEqual(repair.install(self.store), "READY_NOT_APPLIED")
        self.assertFalse(self.receipt.exists())
        self.assertEqual(self.launcher.read_bytes(), old_launcher)
        self.assertEqual(self.previous_receipt.read_bytes(), old_record)

    def test_overlay_repair_changes_only_launcher_preserving_native_and_data(self):
        originals = {p: p.read_bytes() for p in self.case.f['root'].rglob('*') if p.is_file()}
        self.assertEqual(self.apply(), "APPLIED_NO_TRADE")
        changed = {p for p, value in originals.items() if p.read_bytes() != value}
        self.assertEqual(changed, {self.launcher})
        self.assertEqual(self.previous_receipt.read_bytes(), originals[self.previous_receipt])
        self.assertEqual(self.case.legacy.read_bytes(), originals[self.case.legacy])
        self.assertIn(b"FromArgb(255,255,255)", self.launcher.read_bytes())
        self.assertIn(b"No11WeeklyDailySelectionStatus", self.launcher.read_bytes())
        self.assertEqual(repair.audit(self.store)[0], "ALREADY_APPLIED")
        self.assertEqual(self.apply(), "ALREADY_APPLIED")
        self.assertEqual(journal_io.checkpoint(self.receipt)["phase"], "COMPLETE")

    def test_interruption_before_switch_can_recover_only_with_pinned_journal(self):
        original = self.launcher.read_bytes()
        with patch.object(repair.previous, "gate"), patch.object(
                repair.previous, "parse_launcher"), patch.object(
                repair.previous, "replace_exact", side_effect=OSError("fixture stop")):
            with self.assertRaises(OSError):
                repair.install(self.store, apply=True)
        self.assertEqual(self.launcher.read_bytes(), original)
        self.assertEqual(repair.audit(self.store)[0], "INTERRUPTED_REQUIRES_APPLY")
        self.assertEqual(self.apply(), "APPLIED_NO_TRADE")

    def test_tamper_after_complete_blocks_without_rewrite_or_reset(self):
        self.apply()
        self.launcher.write_bytes(self.launcher.read_bytes() + b"# unknown\n")
        current = self.launcher.read_bytes()
        with self.assertRaisesRegex(ValueError, "INSTALLED_LAUNCHER_CHANGED"):
            self.apply()
        self.assertEqual(self.launcher.read_bytes(), current)
        self.assertTrue(self.receipt.exists())

    def test_wrong_initial_v2_receipt_blocks_without_creating_new_journal(self):
        self.launcher.write_bytes(self.launcher.read_bytes() + b"# unknown\n")
        current = self.launcher.read_bytes()
        with self.assertRaisesRegex(ValueError, "LAUNCHER_CONCURRENT_OR_UNKNOWN"):
            self.apply()
        self.assertEqual(self.launcher.read_bytes(), current)
        self.assertFalse(self.receipt.exists())

    def test_new_day_and_unrelated_runtime_changes_do_not_require_repair_again(self):
        self.apply()
        unrelated = self.case.home / "local_helper.py"
        unrelated.write_bytes(b"LOCAL_FIX=2\n")
        self.assertEqual(repair.audit(self.store)[0], "ALREADY_APPLIED")

    def test_unknown_install_journal_bytes_are_rejected(self):
        self.apply()
        self.receipt.write_bytes(self.receipt.read_bytes().replace(
            b'"phase":"COMPLETE"', b'"phase":"CORRUPT"'))
        with self.assertRaises(ValueError):
            repair.audit(self.store)

    @unittest.skipUnless(os.name == "nt", "PowerShell 5.1 parser")
    def test_powershell_parser_accepts_both_original_and_repaired_launcher(self):
        with patch.object(repair.previous, "gate"):
            self.assertEqual(repair.install(self.store, apply=True), "APPLIED_NO_TRADE")
        old.parse_launcher(self.launcher.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
