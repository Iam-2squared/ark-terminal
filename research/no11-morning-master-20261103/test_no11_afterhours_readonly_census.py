"""Synthetic no-trade diagnostics only. Never connect to Excel or a broker."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "no11_afterhours_readonly_census", BASE / "no11_afterhours_readonly_census.py"
)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AfterHoursNoTrade(unittest.TestCase):
    DATE = "2026-11-13"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "unified"
        self.root.mkdir()
        self.source = Path(self.tmp.name) / "cycles"
        (self.source / "prepared-days").mkdir(parents=True)
        self.private = Path(self.tmp.name) / "private"
        self.private.mkdir()
        self.boot = Path(self.tmp.name) / "bootstrap.json"
        self.hand = Path(self.tmp.name) / "morning-handoff.json"

    @staticmethod
    def write(path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    def fixture(self, *, date="2026-11-13", hand_date="2026-11-13") -> None:
        settings = {
            "schemaId": "ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1",
            "bootstrapConfigFile": str(self.boot),
            "automaticOrderAuthorization": False,
            "orderTransmission": False,
            "productionReady": False,
        }
        binding = {
            "schemaId": "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1",
            "dailyCycleRoot": str(self.source),
            "orderTransmission": False,
        }
        self.write(self.root / "settings.json", settings)
        self.write(self.root / "automatic-inputs.json", binding)
        self.write(self.boot, {"sessionDate": date, "privateRoot": str(self.private)})
        self.write(self.hand, {
            "schemaId": "ARK_NO11_MORNING_MASTER_HANDOFF_V1",
            "sessionDate": hand_date,
            "orderTransmission": False,
            "productionReady": False,
            "reviewStatus": "NOT_REVIEWED",
            "datedMasterCreated": False,
            "secretsNotForOutput": "SENSITIVE_CONTENT_NEVER_PRINT",
        })
        self.write(self.source / "prepared-days" / (self.DATE + ".json"), {
            "schemaId": "ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1",
            "sessionDate": self.DATE,
            "orderTransmission": False,
            "productionReady": False,
            "humanReviewClaimed": False,
            "handoff": str(self.hand),
            "handoffSha256": hashlib.sha256(self.hand.read_bytes()).hexdigest(),
        })

    def check(self):
        return audit.readonly_audit(self.root, self.DATE, preflight=BASE / "Check-No11StartPrerequisitesReadOnly20261111.ps1")

    def test_01_missing_config_is_fail_closed(self):
        x = self.check()
        self.assertEqual(x["checks"]["SETTINGS_AND_BINDING"], "BLOCKED_SOURCE_MISSING")
        self.assertFalse(x["trade_authorized"])
        self.assertFalse(x["order_transmission"])

    def test_02_stale_bootstrap_does_not_relabel_day(self):
        self.fixture(date="2026-11-12")
        x = self.check()
        self.assertEqual(x["checks"]["BOOTSTRAP_SESSION"], "WRONG_SESSION_DATE")
        self.assertEqual(x["checks"]["PREPARED_DAY"], "DATE_AND_HASH_MATCH_READONLY")
        self.assertEqual(json.loads(self.boot.read_text())["sessionDate"], "2026-11-12")
        self.assertFalse(x["trade_authorized"])

    def test_03_handoff_checks_do_not_grant_live(self):
        self.fixture()
        x = self.check()
        self.assertEqual(x["checks"]["PREPARED_DAY"], "DATE_AND_HASH_MATCH_READONLY")
        self.assertEqual(x["checks"]["LOCAL_RUN_EVIDENCE"], "NO_LOCAL_MARKER_FOUND_NOT_BROKER_CLEARANCE")
        self.assertFalse(x["broker_orders_fills_positions_verified"])
        self.assertFalse(x["live_start_verified"])
        self.assertEqual(x["checks"]["CHART50_ATTEMPT_CLOSURE"], "RECONCILIATION_REQUIRED")

    def test_04_handoff_tampering_does_not_erase_original(self):
        self.fixture()
        self.hand.write_bytes(self.hand.read_bytes() + b"tamper")
        x = self.check()
        self.assertEqual(x["checks"]["PREPARED_DAY"], "BLOCKED_HANDOFF_SHA256")
        self.assertIn(b"tamper", self.hand.read_bytes())

    def test_05_local_marker_cannot_be_ignored(self):
        self.fixture()
        (self.private / "bootstrap-recovery-required.json").write_text("{}")
        x = self.check()
        self.assertEqual(x["checks"]["LOCAL_RUN_EVIDENCE"], "EXISTING_CLAIM_REQUIRES_MANUAL_REVIEW")
        self.assertTrue((self.private / "bootstrap-recovery-required.json").exists())

    def test_06_wrong_handoff_date_blocks(self):
        self.fixture(hand_date="2026-11-12")
        x = self.check()
        self.assertEqual(x["checks"]["PREPARED_DAY"], "BLOCKED_HANDOFF_SCOPE")

    def test_07_unapproved_order_flags_are_not_green(self):
        self.fixture()
        settings = json.loads((self.root / "settings.json").read_text())
        settings["automaticOrderAuthorization"] = True
        self.write(self.root / "settings.json", settings)
        x = self.check()
        self.assertEqual(x["checks"]["SETTINGS_AND_BINDING"], "BLOCKED_CONFIG_CONTRACT")

    def test_08_no_private_values_or_paths_in_result(self):
        self.fixture()
        x = self.check()
        output = json.dumps(x)
        self.assertNotIn("SENSITIVE_CONTENT_NEVER_PRINT", output)
        self.assertNotIn(str(self.private), output)
        self.assertNotIn(str(self.hand), output)
        self.assertNotIn("python.exe", output)

    def test_09_invalid_day_fails_even_for_readonly(self):
        self.fixture()
        x = audit.readonly_audit(self.root, "2026-11-99")
        self.assertEqual(x["checks"]["DATE_FORMAT"], "BLOCKED_NONCANONICAL_DATE")
        self.assertFalse(x["trade_authorized"])

    def test_10_future_session_not_automatically_authorized(self):
        self.fixture()
        x = audit.readonly_audit(self.root, "2026-11-16")
        self.assertFalse(x["trade_authorized"])
        self.assertEqual(x["checks"]["DATE_SCOPE"], "OTHER_SESSION_READONLY_NO_DATE_REWRITE")

    def test_11_broken_json_is_classified_not_dumped(self):
        (self.root / "settings.json").write_text("{ account_token", encoding="utf-8")
        x = self.check()
        self.assertEqual(x["checks"]["SETTINGS_AND_BINDING"], "BLOCKED_INVALID_JSON")
        self.assertNotIn("account_token", json.dumps(x))

    def test_12_trade_launch_marker_forces_manual_review(self):
        self.fixture()
        (self.root / "TRADE-2026-11-13.launch.json").write_text('{"count":0}')
        x = self.check()
        self.assertEqual(x["checks"]["LOCAL_RUN_EVIDENCE"], "EXISTING_CLAIM_REQUIRES_MANUAL_REVIEW")

    def test_13_offline_script_source_is_present(self):
        self.fixture()
        x = self.check()
        self.assertEqual(x["checks"]["PREFLIGHT_IN_GIT_CHECKOUT"], "PRESENT")


if __name__ == "__main__":
    unittest.main()
