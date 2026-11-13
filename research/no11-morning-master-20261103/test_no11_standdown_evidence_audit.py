"""Synthetic read-only stand-down evidence tests (no broker, Excel or orders)."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import no11_standdown_evidence_audit as audit

DAY = "2026-11-13"
PREV = "2026-11-12"


def save(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8")
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StandDownOffline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ark-standdown-offline-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.store = root / "store"
        self.store.mkdir()
        self.daily = root / "daily"
        self.daily.mkdir()
        self.private = root / "private"
        self.private.mkdir()
        self.boot = save(root / "bootstrap.json", {
            "schemaId": "ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1",
            "sessionDate": PREV, "privateRoot": str(self.private),
            "orderTransmission": False,
        })
        self.bridge = root / "bridge.py"
        self.bridge.write_text("# pinned original bridge; never run\n", encoding="utf-8")
        self.binding = save(self.store / "automatic-inputs.json", {
            "schemaId": "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1",
            "orderTransmission": False,
            "dailyCycleRoot": str(self.daily),
            "bridge": str(self.bridge), "bridgeSha256": digest(self.bridge),
        })
        self.settings = save(self.store / "settings.json", {
            "schemaId": "ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1",
            "normalMaxPositions": 3, "sameDayApprovalRequired": True,
            "automaticOrderAuthorization": False, "orderTransmission": False,
            "bootstrapConfigFile": str(self.boot),
        })
        self.days = self.daily / "prepared-days"
        self.days.mkdir()
        self.handoff = {
            "schemaId": "ARK_NO11_MORNING_MASTER_HANDOFF_V1",
            "sessionDate": DAY, "previousSession": PREV,
            "selectedSymbols": ["7203.T", "6758.T"],
            "orderTransmission": False, "productionReady": False,
            "reviewStatus": "NOT_REVIEWED", "datedMasterCreated": False,
        }
        raw = (json.dumps(self.handoff, sort_keys=True,
                          separators=(",", ":")) + "\n").encode()
        sha = hashlib.sha256(raw).hexdigest()
        h = self.days / ("morning-handoff-" + sha + ".json")
        h.write_bytes(raw)
        self.pointer = save(self.days / (DAY + ".json"), {
            "schemaId": "ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1",
            "sessionDate": DAY, "previousSession": PREV,
            "handoff": str(h), "handoffSha256": sha,
            "selectedSymbols": ["7203.T", "6758.T"], "selectedCount": 2,
            "orderTransmission": False, "productionReady": False,
            "humanReviewClaimed": False,
        })

    def files(self):
        return {str(p): p.read_bytes() for p in self.tmp_root.rglob("*") if p.is_file()}

    @property
    def tmp_root(self):
        return self.store.parent

    def run_audit(self):
        before = self.files()
        result = audit.inspect(self.store, day=DAY)
        self.assertEqual(self.files(), before, "AUDIT_MUST_NOT_WRITE")
        return result

    def test_verified_today_pointer_is_not_a_trade_permission(self):
        v = self.run_audit()
        self.assertEqual(v["sessionDate"], DAY)
        self.assertEqual(v["preparedData"]["state"], "VERIFIED_DATED_HANDOFF")
        self.assertEqual(v["preparedData"]["sourceSession"], PREV)
        self.assertEqual(v["preparedData"]["selectedCount"], 2)
        self.assertEqual(v["bridge"], "SOURCE_PIN_VERIFIED")
        self.assertEqual(v["legacyBootstrapDate"], PREV)
        self.assertFalse(v["legacyBootstrapDateIsToday"])
        self.assertFalse(v["canAuthorizeTrade"])
        self.assertFalse(v["brokerOrdersChecked"])
        self.assertFalse(v["brokerExecutionsChecked"])
        self.assertFalse(v["brokerPositionsChecked"])
        self.assertFalse(v["orderTransmission"])
        self.assertEqual(v["localLaunchEvidence"], "NO_LOCAL_LAUNCH_MARKERS_AT_SCANNED_ROOT")

    def test_request_claim_marker_cannot_be_ignored(self):
        names = [
            "PREOPEN-" + DAY + ".request.json",
            "PREOPEN-" + DAY + ".execution-claimed",
            "TRADE-" + DAY + ".launch.json",
        ]
        for index, name in enumerate(names):
            with self.subTest(name=name):
                path = self.store / name
                path.write_text("OPAQUE_ORIGINAL_HISTORICAL_EVIDENCE", encoding="utf-8")
                v = self.run_audit()
                self.assertEqual(v["localLaunchEvidence"], "REVIEW_OR_UNKNOWN")
                self.assertEqual(sum(x == "PRESENT_REVIEW_REQUIRED" for x in
                                     v["markers"].values()), 1)
                self.assertFalse(v["canAuthorizeTrade"])
                path.unlink()

    def test_prior_connected_collector_with_no_closure_is_not_falsely_closed(self):
        run = self.private / ("session-" + PREV + "-" + "f" * 32)
        run.mkdir()
        save(self.private / ("received-session-" + PREV + ".active.json"), {
            "sessionDate": PREV, "runRoot": str(run),
        })
        save(run / "attempt-0001" / "attempt.json", {
            "status": "CONNECTED", "sessionDate": PREV,
        })
        v = self.run_audit()
        self.assertEqual(v["previousCollector"], "UNCLOSED_ATTEMPT_CONNECTED")
        attempt = run / "attempt-0001"
        (attempt / "collector-ready.json.closed.json").write_text("not-verified")
        v = self.run_audit()
        self.assertEqual(v["previousCollector"], "CONFLICTING_ATTEMPT_AND_CLOSURE")
        self.assertFalse(v["canAuthorizeTrade"])

    def test_previous_closure_presence_is_not_certified(self):
        run = self.private / ("session-" + PREV + "-" + "f" * 32)
        run.mkdir()
        save(self.private / ("received-session-" + PREV + ".active.json"),
             {"sessionDate": PREV, "runRoot": str(run)})
        save(run / "attempt-0001" / "attempt.json", {"status": "CLOSED"})
        (run / "attempt-0001" / "collector-ready.json.closed.json").write_text("unknown")
        self.assertEqual(self.run_audit()["previousCollector"],
                         "CLOSED_RECORD_PRESENT_NOT_CERTIFIED")

    def test_invalid_handoff_hash_or_source_session_not_called_ready(self):
        old = self.pointer.read_bytes()
        body = json.loads(old)
        body["handoffSha256"] = "0" * 64
        save(self.pointer, body)
        self.assertEqual(self.run_audit()["preparedData"]["state"], "UNVERIFIED")
        self.pointer.write_bytes(old)
        body = json.loads(old)
        body["previousSession"] = "2026-11-14"
        save(self.pointer, body)
        self.assertEqual(self.run_audit()["preparedData"]["state"], "UNVERIFIED")

    def test_config_tamper_blocks_not_implicitly_trade_authorized(self):
        body = json.loads(self.settings.read_bytes())
        body["automaticOrderAuthorization"] = True
        save(self.settings, body)
        with self.assertRaisesRegex(ValueError, "LOCAL_CONFIG_UNSAFE"):
            self.run_audit()

    def test_bridge_mismatch_never_auto_executes_bridge(self):
        self.bridge.write_text("# changed\n", encoding="utf-8")
        with patch.object(subprocess, "run", side_effect=AssertionError("SUBPROCESS_IS_FORBIDDEN")):
            v = self.run_audit()
        self.assertEqual(v["bridge"], "SOURCE_PIN_MISMATCH")
        self.assertFalse(v["canAuthorizeTrade"])

    def test_portable_preflight_is_pinned_readonly_and_not_local_path_dependent(self):
        source = (Path(__file__).with_name(
            "Bootstrap-No11PortablePreflightReadOnly.ps1")).read_text(
                encoding="utf-8-sig")
        self.assertIn("Check-No11StartPrerequisitesReadOnly20261111.ps1", source)
        self.assertIn("b02804545cceb592ea613de7cd8e9b48f5bab1b1", source)
        self.assertIn("75f2c43248c4f5b168fb41c2e5f55f8fb7749886", source)
        self.assertIn("NO11_PORTABLE_PREFLIGHT_SOURCE_VERIFIED=True", source)
        self.assertIn("NO11_PORTABLE_PREFLIGHT=BLOCKED", source)
        self.assertIn("ORDER_TRANSMISSION=False", source)
        self.assertNotIn("IApproveOrdersForToday", source)
        self.assertNotIn("taskkill", source.lower())
        self.assertNotIn("Stop-Process", source)
        self.assertNotIn("Invoke-No11MsiiOrder", source)
        self.assertNotIn("--apply", source)

    def test_cli_redacts_private_paths_and_no_synthetic_shutdown(self):
        result = subprocess.run([
            sys.executable, "-B", str(Path(audit.__file__)),
            "--store", str(self.store), "--day", DAY,
        ], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(str(self.tmp_root), result.stdout)
        obj = json.loads(result.stdout)
        self.assertTrue(obj["requiresIndependentBrokerReview"])
        self.assertTrue(obj["readOnly"])
        self.assertEqual(obj["operatorNoTradeIntent"],
                         "DECLARED_IN_CHAT_NOT_LOCAL_ENFORCEMENT")
        self.assertFalse(obj["ordersCancelledByAudit"])
        self.assertFalse(obj["tradeLaunchedByAudit"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
