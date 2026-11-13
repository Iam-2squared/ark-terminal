"""Isolated collector-owner-guardian tests; no Excel, broker or order connection."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "no12-prebuy-causal-runtime-20261011" / "tools"
sys.path.insert(0, str(TOOLS))
import no11_collector_owner_guard as guardian
import no11_received_run_recovery as recovery
import no11_owner_guard_staging as staging

DAY = "2026-11-13"


def sealed_file(path, body):
    path.write_bytes(recovery.encoded(recovery.sealed(body)) + b"\n")


class SyntheticOwnerExit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="no11-owner-guard-offline-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / ("session-" + DAY + "-" + "a" * 32)
        self.attempt = self.run / "attempt-0001"
        self.attempt.mkdir(parents=True)
        self.state("ALLOCATED")

    def state(self, state):
        sealed_file(self.attempt / "attempt.json", {
            "schemaId": recovery.ATTEMPT, "sessionDate": DAY,
            "runRoot": str(self.run), "status": state,
            "pid": None, "captureFolder": None,
            "productionReady": False, "orderTransmission": False,
        })

    def assert_no_closure_fabricated(self):
        self.assertFalse((self.attempt / "collector-ready.json.closed.json").exists())
        self.assertFalse((self.root / "bootstrap-recovery-required.json").exists())
        self.assertFalse((self.run / "inference").exists())
        self.assertFalse((self.root / ("received-session-" + DAY + ".active.json")).exists())

    def test_connected_owner_exit_requests_only_safe_stop_and_not_closed(self):
        self.state("CONNECTED")
        before = (self.attempt / "attempt.json").read_bytes()
        actual = guardian.stop_if_owner_exited(self.root, self.attempt, DAY, 1234)
        self.assertEqual(actual, "OWNER_EXIT_STOP_REQUESTED_NOT_CLOSURE")
        self.assertEqual((self.attempt / "collector.stop").read_bytes(),
                         guardian.STOP_BYTES)
        self.assertEqual((self.attempt / "attempt.json").read_bytes(), before)
        e = recovery.unseal(self.attempt / "owner-exit-stop-request.json",
                            guardian.INCIDENT)
        self.assertEqual(e["attemptStatusAtOwnerExit"], "CONNECTED")
        self.assertFalse(e["genuineCollectorClosedReceiptValidated"])
        self.assertFalse(e["collectorAttemptMarkedClosed"])
        self.assertFalse(e["excelKilled"])
        self.assertFalse(e["brokerOrdersTouched"])
        self.assertFalse(e["orderTransmission"])
        self.assert_no_closure_fabricated()

    def test_spawn_requested_before_pid_persisted_still_fails_closed(self):
        self.state("SPAWN_REQUESTED")
        actual = guardian.stop_if_owner_exited(self.root, self.attempt, DAY, 12)
        self.assertEqual(actual, "OWNER_EXIT_STOP_REQUESTED_NOT_CLOSURE")
        self.assertTrue((self.attempt / "collector.stop").exists())
        self.assert_no_closure_fabricated()

    def test_closed_attempt_never_gets_extra_stop_receipt(self):
        self.state("CLOSED")
        before = (self.attempt / "attempt.json").read_bytes()
        self.assertEqual(guardian.stop_if_owner_exited(self.root, self.attempt,
                         DAY, 1234), "ALREADY_CLOSED_NO_ACTION")
        self.assertEqual((self.attempt / "attempt.json").read_bytes(), before)
        self.assertFalse((self.attempt / "collector.stop").exists())
        self.assertFalse((self.attempt / "owner-exit-stop-request.json").exists())
        self.assert_no_closure_fabricated()

    def test_allocated_without_spawn_does_not_claim_cleanup(self):
        self.assertEqual(guardian.stop_if_owner_exited(self.root, self.attempt,
                         DAY, 1234), "ALLOCATED_NO_COLLECTOR_REQUEST")
        self.assertFalse((self.attempt / "collector.stop").exists())
        self.assertFalse((self.attempt / "owner-exit-stop-request.json").exists())
        self.assert_no_closure_fabricated()

    def test_existing_stop_does_not_rewrite_but_records_uncertainty(self):
        self.state("RUNNING")
        stop = self.attempt / "collector.stop"
        stop.write_bytes(guardian.STOP_BYTES)
        before = stop.read_bytes()
        guardian.stop_if_owner_exited(self.root, self.attempt, DAY, 4321)
        e = recovery.unseal(self.attempt / "owner-exit-stop-request.json",
                            guardian.INCIDENT)
        self.assertFalse(e["stopNewlyCreated"])
        self.assertEqual(stop.read_bytes(), before)
        self.assert_no_closure_fabricated()

    def test_unknown_stop_marker_never_overwritten(self):
        self.state("CONNECTED")
        stop = self.attempt / "collector.stop"
        stop.write_bytes(b"UNVERIFIED")
        with self.assertRaisesRegex(ValueError, "EXISTING_STOP_UNVERIFIED"):
            guardian.stop_if_owner_exited(self.root, self.attempt, DAY, 42)
        self.assertEqual(stop.read_bytes(), b"UNVERIFIED")
        self.assertFalse((self.attempt / "owner-exit-stop-request.json").exists())

    def test_replay_does_not_overwrite_original_incident(self):
        self.state("CONNECTED")
        guardian.stop_if_owner_exited(self.root, self.attempt, DAY, 111)
        receipt = (self.attempt / "owner-exit-stop-request.json")
        old = receipt.read_bytes()
        with self.assertRaisesRegex(ValueError, "EXISTING_GUARD_OUTPUT"):
            guardian.stop_if_owner_exited(self.root, self.attempt, DAY, 111)
        self.assertEqual(receipt.read_bytes(), old)

    def test_tampered_attempt_blocks_no_stop(self):
        self.state("CONNECTED")
        path = self.attempt / "attempt.json"
        path.write_bytes(path.read_bytes().replace(b"CONNECTED", b"RUNNING"))
        with self.assertRaisesRegex(ValueError, "CONTRACT_CHANGED"):
            guardian.stop_if_owner_exited(self.root, self.attempt, DAY, 111)
        self.assertFalse((self.attempt / "collector.stop").exists())

    def test_wrong_parent_or_day_blocks_no_stop(self):
        self.state("CONNECTED")
        with self.assertRaises(ValueError):
            guardian.stop_if_owner_exited(self.root, self.attempt, "2026-11-16", 111)
        with self.assertRaises(ValueError):
            guardian.stop_if_owner_exited(self.root / "wrong", self.attempt, DAY, 111)
        self.assertFalse((self.attempt / "collector.stop").exists())

    def test_no_imports_capable_of_excel_broker_or_order_dispatch(self):
        source = Path(guardian.__file__).read_text()
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported.intersection(
            {"win32com", "requests", "socket", "sqlite3"}))
        self.assertNotIn("Invoke-No11MsiiOrder", source)
        self.assertNotIn("TerminateProcess", source)
        self.assertNotIn("taskkill", source)
        self.assertNotIn("collector-ready.json.closed.json", source.split(
            "def stop_if_owner_exited")[1].split("def open_exact_owner_handle")[0])


class WiringStageTests(unittest.TestCase):
    def test_staged_wiring_changes_only_launch_same_run_and_is_reversible(self):
        root = HERE.parents[1]
        original = subprocess.check_output(
            ["git", "show", "HEAD:" + staging.CONTROLLER], cwd=root)
        modified = staging.transform(original)
        live_path = root / staging.CONTROLLER
        # Git blob uses LF; a Windows checkout may use CRLF by policy.
        self.assertEqual(live_path.read_bytes().replace(b"\r\n", b"\n"),
                         modified.replace(b"\r\n", b"\n"))  # CI stage done
        self.assertIn(b"guardian = start_guardian", modified)
        self.assertIn(b"guardian.poll() is None", modified)
        self.assertIn(b"guardian.wait(timeout=8) == 0", modified)
        self.assertNotIn(b"import win32com", modified)
        base = ast.parse(original)
        updated = ast.parse(modified)
        self.assertEqual(set(n.name for n in base.body if isinstance(n, ast.FunctionDef)),
                         set(n.name for n in updated.body if isinstance(n, ast.FunctionDef)))
        self.assertNotIn("NO11_RECEIVED_PIPELINE_ORDER", str(modified))

    def test_unknown_source_refuses_patch(self):
        original = subprocess.check_output(
            ["git", "show", "HEAD:" + staging.CONTROLLER], cwd=HERE.parents[1])
        with self.assertRaisesRegex(ValueError, "UNKNOWN_SOURCE_SPAN"):
            staging.transform(original.replace(
                b"NO11_BOOTSTRAP_STOP=COLLECTOR_AND_CONSUMER_CLOSED",
                b"UNKNOWN_WRAPPER", 1))


@unittest.skipUnless(sys.platform == "win32", "Windows process-handle test")
class WindowsKilledControllerSimulation(SyntheticOwnerExit):
    def test_actual_terminated_owner_requests_stop_and_never_marks_closed(self):
        # Synthetic owner process: a sleeping Python, NOT real Excel/controller.
        owner = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(40)"],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 creationflags=(subprocess.DETACHED_PROCESS |
                                                subprocess.CREATE_NEW_PROCESS_GROUP))
        token = "f" * 32
        monitor = None
        try:
            watch = [sys.executable, "-B", str(guardian.Path(guardian.__file__)),
                     "watch", "--private-root", str(self.root),
                     "--attempt", str(self.attempt), "--session", DAY,
                     "--owner-pid", str(owner.pid), "--nonce", token]
            monitor = subprocess.Popen(watch, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       creationflags=(subprocess.DETACHED_PROCESS |
                                                      subprocess.CREATE_NEW_PROCESS_GROUP))
            ready = self.attempt / "owner-guard-attached.json"
            deadline = time.monotonic() + 10
            while not ready.exists() and time.monotonic() < deadline:
                if monitor.poll() is not None:
                    break
                time.sleep(0.05)
            self.assertTrue(ready.exists(), monitor.communicate(timeout=2)
                            if monitor.poll() is not None else "NO_ATTACHED_ACK")
            attached = recovery.unseal(ready, guardian.ATTACHED)
            self.assertEqual(attached["ownerProcessId"], owner.pid)
            self.assertEqual(attached["guardianProcessId"], monitor.pid)
            self.assertTrue(attached["ownerHandleAttached"])
            self.state("CONNECTED")  # mock original native started and connected
            original = (self.attempt / "attempt.json").read_bytes()
            owner.kill()
            owner.wait(timeout=10)
            stdout, stderr = monitor.communicate(timeout=10)
            self.assertEqual(monitor.returncode, 0,
                             (stdout + stderr)[-3000:].decode(errors="replace"))
            self.assertEqual((self.attempt / "attempt.json").read_bytes(), original)
            self.assertEqual((self.attempt / "collector.stop").read_bytes(),
                             guardian.STOP_BYTES)
            self.assertFalse((self.attempt / "collector-ready.json.closed.json").exists())
            self.assert_no_closure_fabricated()
        finally:
            if owner.poll() is None:
                owner.kill()
                owner.wait(timeout=10)
            if monitor is not None and monitor.poll() is None:
                monitor.kill()
                monitor.wait(timeout=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
