from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("ark_ui2_readonly_server.py")
spec = importlib.util.spec_from_file_location("ark_ui2_readonly_server", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def model(timestamp="2026-09-16T01:00:00+00:00"):
    return {
        "schemaId": "ARK_TERMINAL_UI_READ_MODEL_V1",
        "generatedAt": timestamp,
        "readOnly": True,
        "mutationCapabilities": {key: False for key in mod.MUTATION_KEYS},
        "source": {
            "schemaValid": True,
            "freshness": {"state": "FRESH", "timestamp": timestamp, "ageSeconds": 1},
        },
        "safety": {"state": "LOCKED"},
        "system": {"health": "READ_ONLY_OK", "tradeReadiness": "LOCKED_NO_INTENT"},
        "home": {"buyingPower": 2605, "buyingPowerState": "FRESH"},
        "positions": [],
        "orders": [],
        "executions": [],
    }


class ServerModelTests(unittest.TestCase):
    def test_valid_model_requires_all_mutations_false(self):
        source = model()
        self.assertIs(mod.validate_read_model(source), source)
        source["mutationCapabilities"]["orderSubmit"] = True
        with self.assertRaisesRegex(ValueError, "MUTATION_CAPABILITY_NOT_FALSE"):
            mod.validate_read_model(source)

    def test_observed_projection_marks_old_model_stale_and_blocks(self):
        source = model("2026-09-16T01:00:00+00:00")
        projected = mod.project_observed_model(
            source,
            now_epoch=mod.parse_iso("2026-09-16T01:00:30+00:00"),
            max_model_age_seconds=15,
            refresh_state={"enabled": True, "lastError": None},
        )
        self.assertEqual(projected["source"]["freshness"]["state"], "STALE")
        self.assertEqual(projected["system"]["health"], "BLOCKED")
        self.assertEqual(projected["system"]["tradeReadiness"], "BLOCKED")
        self.assertEqual(projected["home"]["buyingPowerState"], "STALE")
        self.assertTrue(projected["localBridge"]["loopbackOnly"])
        self.assertFalse(projected["localBridge"]["mutationCapabilities"]["brokerWrite"])
        self.assertEqual(source["source"]["freshness"]["state"], "FRESH")

    def test_fresh_projection_stays_read_only(self):
        timestamp = "2026-09-16T01:00:00+00:00"
        projected = mod.project_observed_model(
            model(timestamp),
            now_epoch=mod.parse_iso("2026-09-16T01:00:05+00:00"),
            max_model_age_seconds=15,
        )
        self.assertEqual(projected["source"]["freshness"]["state"], "FRESH")
        self.assertEqual(projected["system"]["health"], "READ_ONLY_OK")
        self.assertTrue(projected["readOnly"])

    def test_loopback_server_fixture_does_not_modify_frozen_index(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            index = root / "index.html"
            overlay = root / "ark-readonly-overlay.js"
            model_path = root / "model.json"
            index.write_text('<html><body><div id="root"></div></body></html>', encoding="utf-8")
            overlay.write_text('console.log("ro")', encoding="utf-8")
            model_path.write_text(json.dumps(model()), encoding="utf-8")
            before = index.read_bytes()
            refresh = mod.RefreshState()
            server = mod.ArkUiServer(
                ("127.0.0.1", 0),
                mod.Handler,
                index_path=index,
                overlay_path=overlay,
                model_path=model_path,
                max_model_age_seconds=15,
                refresh_state=refresh,
            )
            try:
                source = index.read_text(encoding="utf-8")
                injected = source.replace("</body>", '<script src="/ark-readonly-overlay.js" defer></script></body>', 1)
                self.assertIn("/ark-readonly-overlay.js", injected)
                self.assertEqual(index.read_bytes(), before)
                self.assertEqual(server.server_address[0], "127.0.0.1")
            finally:
                server.server_close()


    def test_custom_preview_script_rejects_unapproved_path(self):
        with self.assertRaisesRegex(SystemExit, "PREVIEW_SCRIPT_NOT_APPROVED"):
            mod.main(["--no-refresh", "--preview-script", "/tmp/unapproved.ps1"])

    def test_existing_default_preview_script_path_preserved(self):
        args = mod.build_parser(MODULE_PATH.parent.parent).parse_args(["--no-refresh"])
        self.assertEqual(args.preview_script.name, "Write-No11ReadOnlyPreview.ps1")


    def test_refresh_failure_blocks_existing_fresh_model_immediately(self):
        timestamp = "2026-09-16T01:00:00+00:00"
        source = model(timestamp)
        projected = mod.project_observed_model(
            source,
            now_epoch=mod.parse_iso("2026-09-16T01:00:05+00:00"),
            max_model_age_seconds=30,
            refresh_state={"enabled": True, "lastError": "READ_ONLY_REFRESH_FAILED"},
        )
        self.assertEqual(projected["source"]["freshness"]["state"], "REFRESH_FAILED")
        self.assertEqual(projected["system"]["tradeReadiness"], "BLOCKED")
        self.assertEqual(projected["home"]["buyingPowerState"], "REFRESH_FAILED")
        self.assertEqual(source["source"]["freshness"]["state"], "FRESH")
        recovered = mod.project_observed_model(
            source, now_epoch=mod.parse_iso("2026-09-16T01:00:05+00:00"),
            max_model_age_seconds=30,
            refresh_state={"enabled": True, "lastError": None},
        )
        self.assertEqual(recovered["source"]["freshness"]["state"], "FRESH")

    def test_future_model_timestamp_does_not_look_fresh(self):
        projected = mod.project_observed_model(
            model("2026-09-16T01:01:00+00:00"),
            now_epoch=mod.parse_iso("2026-09-16T01:00:00+00:00"),
            max_model_age_seconds=30,
        )
        self.assertEqual(projected["source"]["freshness"]["state"], "INVALID")
        self.assertEqual(projected["system"]["tradeReadiness"], "BLOCKED")

    def test_refresh_failure_never_exposes_child_account_output(self):
        state = mod.RefreshState()
        loop = mod.RefreshLoop(
            state=state, preview_script=Path("fixture.ps1"),
            workbook_path=Path("private.xlsx"), model_path=Path("model.json"),
            ownership_path=None, interval_seconds=30,
        )
        loop._command = lambda: ["powershell"]
        response = SimpleNamespace(
            returncode=2, stdout="PRIVATE_BUYING_POWER=999",
            stderr="PRIVATE_SYMBOL_OR_PATH_SHOULD_NOT_LEAK",
        )
        with patch.object(mod.subprocess, "run", return_value=response):
            loop._refresh_once()
        self.assertEqual(state.snapshot()["lastError"], "READ_ONLY_REFRESH_FAILED")
        self.assertNotIn("PRIVATE_", str(state.snapshot()))


if __name__ == "__main__":
    unittest.main()
