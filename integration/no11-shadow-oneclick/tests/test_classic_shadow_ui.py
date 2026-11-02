"""Original rich UI + new Shadow account-model adapter; no Excel or broker."""
from __future__ import annotations

import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ui"))
import ark_shadow_ui as original
import ark_shadow_classic as classic


def observation():
    return {
        "schemaId": original.ACCOUNT_SCHEMA,
        "readOnly": True, "orderTransmission": False,
        "status": "OBSERVED",
        "snapshot": {
            "schemaId": "ARK_ACCOUNT_READONLY_SNAPSHOT_V2",
            "captureCompletedAt": original.now().isoformat(),
            "buyingPower": 278000,
            "positions": [
                {"symbol": "7203.T", "quantity": 100,
                 "marketValue": 248000, "unrealizedPnl": 1000}],
            "orders": [],
            "executions": [
                {"symbol": "7203.T", "side": "買", "quantity": 100,
                 "price": 2480, "executionDate": original.now().isoformat()}],
        }
    }


class ClassicIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = "2026-10-27"

    def _saved(self, key, value):
        file = self.root / key
        file.write_text(json.dumps(value, ensure_ascii=False), encoding="utf8")
        return file

    def test_unchanged_original_rich_ui_loaded_and_sandboxed(self):
        source, csp = classic.classic_document()
        self.assertGreater(len(source), 100_000)
        self.assertIn(b"ark-readonly-overlay.js", source)
        self.assertIn(b"ark-shadow-classic-bridge.js", source)
        self.assertIn(b"ark-classic-preload", source)
        self.assertIn(b"</body>", source)
        self.assertIn("script-src 'self' 'sha256-", csp)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", csp)
        self.assertIn("form-action 'none'", csp)
        self.assertIn("connect-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)

    def test_real_rss_only_and_no_fabricated_total_assets(self):
        actual = original.account_view(self._saved("actual.json", observation()))
        self.assertEqual(actual["status"], "OBSERVED")
        message = {"schemaId": "ARK_SHADOW_LOCAL_DASHBOARD_V1",
                   "orderTransmission": False,
                   "account": actual,
                   "shadow": {"portfolio": {"status": "OBSERVED_SIMULATOR_LEDGER",
                                            "cash": "500000",
                                            "equity": "750000"}}}
        model = classic.account_read_model(message)
        self.assertIsNotNone(model)
        self.assertEqual(model["schemaId"], "ARK_TERMINAL_UI_READ_MODEL_V1")
        self.assertTrue(model["readOnly"])
        self.assertEqual(model["home"]["buyingPower"], 278000)
        self.assertEqual(model["positions"][0]["ownership"], "UNKNOWN")
        self.assertEqual(model["positions"][0]["marketValue"], 248000)
        self.assertEqual(model["positions"][0]["unrealizedPnl"], 1000)
        self.assertTrue(all(v is False for v in model["mutationCapabilities"].values()))
        self.assertEqual(model["system"]["tradeReadiness"], "BLOCKED")
        self.assertNotIn("equity", model["home"])
        self.assertNotIn("shadow", model)
        self.assertNotIn("totalAssets", model["home"])
        message["orderTransmission"] = True
        self.assertIsNone(classic.account_read_model(message))
        message["orderTransmission"] = False
        message["account"]["status"] = "STALE"
        self.assertIsNone(classic.account_read_model(message))

    def test_offline_local_readonly_classic_http_routes(self):
        account = self._saved("account.json", observation())
        status = self._saved("status.json", {
            "schemaId": original.LAUNCH_SCHEMA,
            "status": "UI_READY",
            "steps": {"excel": "READY", "shadow": "NOT_CONFIGURED"},
            "orderTransmission": False,
        })
        settings = type("Settings", (), {
            "session": self.session,
            "launch_status_file": status,
            "account_file": account,
            "account_secondary_file": None,
            "shadow_root": self.root,
        })()
        server = original.ThreadingHTTPServer(("127.0.0.1", 0), classic.ClassicHandler)
        server.config = settings
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join(1)))
        for endpoint in ("/", "/api/status", "/api/health",
                         "/api/classic-health", "/ark-readonly-overlay.js",
                         "/ark-shadow-classic-bridge.js", "/api/ui-read-model"):
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            try:
                conn.request("GET", endpoint)
                response = conn.getresponse()
                body = response.read()
                self.assertEqual(response.status, 200, endpoint)
                self.assertIn("no-store", response.getheader("Cache-Control"))
                self.assertEqual(response.getheader("X-Frame-Options"), "DENY")
                if endpoint == "/api/ui-read-model":
                    value = json.loads(body)
                    self.assertEqual(value["home"]["buyingPower"], 278000)
                    self.assertFalse(value["mutationCapabilities"]["orderSubmit"])
                if endpoint == "/":
                    self.assertGreater(len(body), 100_000)
                    self.assertIn(b"ark-shadow-classic-bridge.js", body)
                    self.assertIn("script-src 'self' 'sha256-", response.getheader("Content-Security-Policy"))
            finally:
                conn.close()
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        try:
            conn.request("POST", "/api/status")
            self.assertEqual(conn.getresponse().status, 405)
        finally:
            conn.close()
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        try:
            conn.request("GET", "/api/status", headers={"Host": "untrusted.example"})
            self.assertEqual(conn.getresponse().status, 403)
        finally:
            conn.close()

    def test_missing_account_is_503_and_not_fake_zero_positions(self):
        invalid = self._saved("invalid.json", {"fake": True})
        status = self._saved("status.json", {
            "schemaId": original.LAUNCH_SCHEMA, "orderTransmission": False})
        settings = type("Settings", (), {
            "session": self.session, "launch_status_file": status,
            "account_file": invalid, "account_secondary_file": None,
            "shadow_root": self.root,
        })()
        server = original.ThreadingHTTPServer(("127.0.0.1", 0), classic.ClassicHandler)
        server.config = settings
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join(1)))
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        try:
            conn.request("GET", "/api/ui-read-model")
            result = conn.getresponse()
            self.assertEqual(result.status, 503)
            body = json.loads(result.read())
            self.assertEqual(body["code"], "CURRENT_RSS_ACCOUNT_MODEL_NOT_OBSERVED")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
