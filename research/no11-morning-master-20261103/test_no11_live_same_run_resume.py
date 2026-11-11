"""Offline recovery contracts. Never invoke Excel, RSS, brokers or Trade."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import sys

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "no12-prebuy-causal-runtime-20261011"
RECOVERY_FILE = ENGINE / "tools" / "no11_received_run_recovery.py"
spec = importlib.util.spec_from_file_location("ark_test_no11_recovery", RECOVERY_FILE)
assert spec and spec.loader
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PostmortemOriginalReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "private"
        self.daily = Path(self.tmp.name) / "daily"
        self.daily.mkdir()
        self.root.mkdir()
        self.day = "2026-11-05"
        self.run = self.root / ("session-" + self.day + "-" + "a" * 32)
        self.run.mkdir()
        self.attempt = self.run / "attempt-0001"
        self.attempt.mkdir()
        self.token = "ARK_NO11_C50_TEMP_" + "b" * 32
        ready = {
            "schemaId": "ARK_NO11_C50_COLLECTOR_READY_V1",
            "sessionDate": self.day, "processId": 991,
            "temporaryWorkbook": {
                "identityValue": self.token,
                "identitySheet": "ARK_NO11_CUMULATIVE",
                "identityCell": "G1",
                "worksheetNames": ["ARK_NO11_CUMULATIVE", "Q01"],
                "name": "Book1",
            }, "orderTransmission": False,
        }
        closed = {
            "schemaId": "ARK_NO11_C50_COLLECTOR_CLOSED_V1",
            "sessionDate": self.day, "processId": 991,
            "temporaryWorkbookClosed": False,
            "collectorFailed": True, "orderTransmission": False,
        }
        self.ready_sha = write(self.attempt / "collector-ready.json", ready)
        self.closed_sha = write(self.attempt / "collector-ready.json.closed.json", closed)
        attempt = {
            "schemaId": recovery.ATTEMPT, "sessionDate": self.day,
            "runRoot": str(self.run), "status": "CLOSED",
            "pid": 991, "captureFolder": None, "readySha256": self.ready_sha,
            "closedSha256": self.closed_sha, "exitCode": 2,
            "productionReady": False, "orderTransmission": False,
        }
        write(self.attempt / "attempt.json", recovery.sealed(attempt))
        self.manager = recovery.RunRecovery({
            "sessionDate": self.day, "privateRoot": str(self.root),
            "dailyRun": str(self.daily), "productionReady": False,
            "orderTransmission": False,
        })

    def cleanup_proof(self, **overrides):
        report_sha = write(self.attempt / "owned-temp-closure-observed.json", {
            "schemaId": "ARK_NO11_C50_OWNED_TEMP_CLOSURE_OBSERVED_V1",
            "sessionDate": self.day, "collectorPid": 991,
            "ownedTemporaryToken": self.token,
            "ownedUnsavedWorkbookClosed": True,
            "originalBooksUnchanged": True,
            "noBrokerOrdersTouched": True,
            "orderTransmission": False,
        })
        p = {
            "schemaId": recovery.POSTMORTEM,
            "closureReportSha256": report_sha,
            "sessionDate": self.day, "collectorPid": 991,
            "originalClosedReceiptSha256": self.closed_sha,
            "originalReadyReceiptSha256": self.ready_sha,
            "ownedTemporaryToken": self.token,
            "ownedUnsavedWorkbookClosed": True,
            "originalBooksUnchanged": True,
            "claimedByOneClickRecovery": True,
            "operatorApproved": True,
            "productionReady": False, "orderTransmission": False,
        }
        p.update(overrides)
        write(self.attempt / "collector-postmortem-cleanup.json",
              recovery.sealed(p))

    def test_unclosed_fail_does_not_restart(self):
        with self.assertRaisesRegex(ValueError, "PRIVATE_SOURCE_MISSING"):
            self.manager.history(self.run)

    def test_separate_cleanup_proof_allows_verified_history(self):
        self.cleanup_proof()
        self.assertEqual(self.manager.history(self.run), [])
        old = json.loads((self.attempt / "collector-ready.json.closed.json").read_text())
        self.assertIs(old["temporaryWorkbookClosed"], False)

    def test_existing_recovery_marker_accepted_only_by_matching_proof(self):
        self.cleanup_proof()
        tools = str(ENGINE / "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
        import no11_received_session_controller as controller
        marker = self.root / "bootstrap-recovery-required.json"
        marker.write_text(json.dumps({
            "schemaId": "ARK_NO11_BOOTSTRAP_RECOVERY_REQUIRED_V1",
            "reason": "COLLECTOR_CLEANUP_NOT_CONFIRMED",
            "processId": 991,
            "originalExcelMustNotBeKilled": True,
            "orderTransmission": False,
        }), encoding="utf-8")
        self.assertTrue(controller.marked_cleanup_proven(
            self.root, self.run, self.day, self.manager))
        self.assertTrue(marker.exists())  # Failure marker is never deleted.
        record = json.loads(marker.read_text())
        record["processId"] = 992
        marker.write_text(json.dumps(record), encoding="utf-8")
        self.assertFalse(controller.marked_cleanup_proven(
            self.root, self.run, self.day, self.manager))
        record["processId"] = 991
        record["reason"] = "COLLECTOR_STOP_TIMEOUT"
        marker.write_text(json.dumps(record), encoding="utf-8")
        self.assertFalse(controller.marked_cleanup_proven(
            self.root, self.run, self.day, self.manager))

    def test_wrong_token_blocks(self):
        self.cleanup_proof(ownedTemporaryToken="ARK_NO11_C50_TEMP_" + "f" * 32)
        with self.assertRaisesRegex(ValueError, "POSTMORTEM_CLEANUP_NOT_VERIFIED"):
            self.manager.history(self.run)

    def test_altered_cleanup_report_stays_blocked(self):
        self.cleanup_proof()
        report = self.attempt / "owned-temp-closure-observed.json"
        report.write_bytes(report.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "POSTMORTEM_CLOSURE_REPORT_CHANGED"):
            self.manager.history(self.run)

    def test_wrong_source_hash_blocks(self):
        self.cleanup_proof(originalClosedReceiptSha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "POSTMORTEM_CLEANUP_NOT_VERIFIED"):
            self.manager.history(self.run)

    def test_no_original_books_proof_blocks(self):
        self.cleanup_proof(originalBooksUnchanged=False)
        with self.assertRaisesRegex(ValueError, "POSTMORTEM_CLEANUP_NOT_VERIFIED"):
            self.manager.history(self.run)

    def test_cleanup_receipt_not_rewritten_or_implicitly_trusted(self):
        self.cleanup_proof(orderTransmission=True)
        with self.assertRaisesRegex(ValueError, "CONTRACT_CHANGED"):
            self.manager.history(self.run)

    def test_fake_boolean_is_rejected_by_sealed_integrity(self):
        self.cleanup_proof(ownedUnsavedWorkbookClosed=False)
        with self.assertRaisesRegex(ValueError, "POSTMORTEM_CLEANUP_NOT_VERIFIED"):
            self.manager.history(self.run)


class ClosedCollectorResumptionTests(unittest.TestCase):
    def test_clean_exit_can_be_source_halted_and_closed(self):
        import sys
        local = str(HERE)
        if local not in sys.path:
            sys.path.insert(0, local)
        import no11_same_session_rearm as rearm
        self.assertTrue(rearm.closed_collector_proven(
            {"status": "CLOSED", "exitCode": 0}))
        self.assertTrue(rearm.closed_collector_proven(
            {"status": "CLOSED", "exitCode": 2}))
        self.assertFalse(rearm.closed_collector_proven(
            {"status": "CONNECTED", "exitCode": 2}))
        self.assertFalse(rearm.closed_collector_proven(
            {"status": "CLOSED", "exitCode": None}))
        # The actual rearm still checks broker orders, source-only halt
        # reasons, original Trade marker and every collector closure receipt.
        self.assertIn("NOT_SOURCE_ONLY_HALT",
                      (HERE / "no11_same_session_rearm.py").read_text())


class LiveResumeSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = (HERE / "no11_same_session_rearm.py").read_text(encoding="utf-8")
        cls.ps = (HERE / "Resume-No11SameSession.ps1").read_text(encoding="utf-8-sig")
        cls.cleanup = (HERE / "Close-No11OwnedC50Temporary.ps1").read_text(encoding="utf-8-sig")
        cls.ui = (HERE / "Start-No11OneClick.ps1").read_text(encoding="utf-8-sig")
        cls.orig = (ENGINE / "windows" / "Run-No11ReceivedSessionOperatorLive.ps1").read_text(encoding="utf-8-sig")
        cls.controller = (ENGINE / "tools" / "no11_received_session_controller.py").read_text(encoding="utf-8-sig")

    def test_original_live_resume_preserved(self):
        self.assertIn("[string]$ResumeRun=''", self.orig)
        self.assertIn("'--resume-run'", self.orig)
        self.assertIn("--resume-run", self.controller)
        self.assertIn("recovery.restore(run_root)", self.controller)
        self.assertIn("self.history(run)", (RECOVERY_FILE).read_text())

    def test_rearm_only_source_halt_and_never_order_resend(self):
        h = self.helper
        self.assertIn("SAFE_SOURCE_HALTS", h)
        self.assertIn("MAX_REARMS = 3", h)
        self.assertIn("manager.restore(run)", h)
        self.assertIn("COLLECTOR_RESTART_REVIEW_ELIGIBLE", h)
        self.assertIn("BROKER_UNRESOLVED", h)
        self.assertIn("firstSellFillBuyHalt", h)
        self.assertIn("controller.sameRunRearm.", h)
        self.assertIn("EXIT_ONLY_NATIVE_RESUME_READY", h)
        self.assertIn("exitOnlyContinuation", h)
        self.assertIn("entryHaltPreserved", h)
        self.assertIn("expected_sha256=halt_pin", h)
        self.assertIn("book.checkpoint_source(\"controller.entryHalt\", []", h)
        self.assertNotIn("book.prepare_order(", h)
        self.assertNotIn("record_transport_result(", h)
        self.assertNotIn("RssStockOrder", h)
        self.assertNotIn("RssCancelOrder", h)
        self.assertNotIn("Stop-Process", h)

    def test_owned_temporary_only_and_originals_protected(self):
        x = self.cleanup
        self.assertIn("Workbooks.Count -eq 4", x)
        self.assertIn("identityValue", x)
        self.assertIn("ARK_NO11_C50_TEMP_", x)
        self.assertIn("$owned.Close($false)", x)
        self.assertIn("ORIGINAL_BOOK_INVENTORY_CHANGED", x)
        self.assertIn("collector-ready.json.closed.json", x)
        self.assertNotIn("Workbooks.Close(", x)
        self.assertNotIn("Workbooks.Open(", x)
        self.assertNotIn("Stop-Process", x)

    def test_single_review_then_same_run_launcher_no_duplicate_trade(self):
        p = self.ps
        self.assertIn("ONECLICK_RESUME", p)
        self.assertIn("-IConfirmSameDayBrokerOrdersAndPositions", self.ui)
        self.assertIn("Resume-No11SameSession.ps1", self.ui)
        self.assertIn("Review-No11RecoveryReadOnly.ps1", self.ui)
        self.assertIn("-ResumeRun", p)
        self.assertIn("-IApproveFullArkLiveOrdersForThisSession", p)
        self.assertIn("NO11_ONECLICK_SAME_RUN_RESUME=REQUESTED", p)
        self.assertIn("NO11_ONECLICK_RESUME_ALREADY_IN_PROGRESS", p)
        self.assertIn("RESUME_ALREADY_REQUESTED_FOR_ATTEMPT", p)
        self.assertIn("RESUME-'+$day+'-'+$attempts[-1].Name+", p)
        self.assertIn("$applyResult=@(& $python -B -X utf8 $rearmTool @arguments --apply)", p)
        self.assertNotIn("$preflight=@(& $python", p)
        self.assertNotIn("'-Mode','Trade'", p)
        self.assertNotIn("TRADE-\"+$day+", p)
        self.assertNotIn("RssStockOrder", p)


if __name__ == "__main__":
    unittest.main()
