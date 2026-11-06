"""Offline tests for the new localhost account/paper dashboard; no Excel/broker."""
from __future__ import annotations

from datetime import datetime
import http.client
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ark_shadow_ui", BASE / "ui" / "ark_shadow_ui.py")
ui = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ui
spec.loader.exec_module(ui)


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def observation(at=None):
    return {
        "schemaId": ui.ACCOUNT_SCHEMA,
        "readOnly": True,
        "orderTransmission": False,
        "status": "OBSERVED",
        "snapshot": {
            "schemaId": "ARK_ACCOUNT_READONLY_SNAPSHOT_V2",
            "captureCompletedAt": at or ui.now().isoformat(),
            "buyingPower": 123456,
            "positions": [{"symbol": "7203", "quantity": 100,
                           "marketValue": 245000, "unrealizedPnl": -5200}],
            "orders": [],
            "executions": [{"symbol": "7203", "side": "買", "quantity": 100,
                            "price": 2450, "executionDate": "2026/10/27 09:32:03"}]
        },
    }


def ledger(path, session):
    connection = sqlite3.connect(str(path))
    connection.execute("CREATE TABLE portfolio (singleton INTEGER PRIMARY KEY, body TEXT)")
    state = {"session": session, "productionReady": False,
             "orderTransmission": False, "cash": "500000",
             "clock": ui.now().isoformat(),
             "positions": {
                 "e1": {"symbol": "7203.T", "quantity": 100,
                        "mark": "2500", "markKnownAt": ui.now().isoformat()}
             },
             "orders": {
                 "o1": {"symbol": "7203.T", "side": "BUY", "quantity": 100,
                        "filled": 100, "status": "FILLED", "createdAt": ui.now().isoformat(),
                        "simulatedOnly": True, "reason": "ORIGINAL_CAPITAL_V5"}
             }}
    connection.execute("INSERT INTO portfolio VALUES (1,?)", (json.dumps(state),))
    connection.commit()
    connection.close()


class ShadowDashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.session = "2026-10-27"

    def test_account_rss_never_invents_total_equity(self):
        path = self.root / "account.json"
        save(path, observation())
        result = ui.account_view(path)
        self.assertEqual(result["status"], "OBSERVED")
        self.assertEqual(result["buyingPower"], "123456")
        self.assertEqual(result["marketValue"], "245000")
        self.assertEqual(result["unrealizedPnl"], "-5200")
        self.assertIsNone(result["totalAssets"])
        self.assertEqual(len(result["executions"]), 1)

    def test_stale_account_never_displays_stale_amounts(self):
        file = self.root / "old.json"
        save(file, observation("2026-10-26T00:00:00+09:00"))
        result = ui.account_view(file)
        self.assertEqual(result["status"], "STALE")
        self.assertIsNone(result["buyingPower"])

    def test_any_invalid_broker_safety_flag_blocks_account_display(self):
        file = self.root / "unsafe.json"
        data = observation()
        data["orderTransmission"] = True
        save(file, data)
        self.assertEqual(ui.account_view(file)["status"], "UNAVAILABLE")

    def test_secondary_original_controller_account_source(self):
        old, new = self.root / "old.json", self.root / "new.json"
        save(old, observation("2026-10-26T00:00:00+09:00"))
        save(new, observation())
        self.assertEqual(ui.select_account(old, new)["status"], "OBSERVED")

    def test_simulated_ledger_amounts_are_never_real_broker_amounts(self):
        db = self.root / "portfolio.sqlite"
        ledger(db, self.session)
        result = ui.ledger_view(db, self.session)
        self.assertEqual(result["status"], "OBSERVED_SIMULATOR_LEDGER")
        self.assertEqual(result["cash"], "500000")
        self.assertEqual(result["exposure"], "250000")
        self.assertEqual(result["equity"], "750000")
        self.assertEqual(result["fills"][0]["side"], "BUY")
        self.assertEqual(result["buyIntents"], 1)
        self.assertIsNone(ui.ledger_view(db, "2026-10-28")["cash"])

    def test_shadow_report_requires_correct_schema_date_and_original_portfolio(self):
        run = self.root / ("session-" + self.session + "-abc") / "inference"
        run.mkdir(parents=True)
        ledger(run / ("portfolio-shadow-" + self.session + ".sqlite"), self.session)
        save(run / "pipeline-latest-report.json", {
            "schemaId": ui.REPORT_SCHEMA,
            "actualCompletedAtJst": ui.now().isoformat(),
            "productionReady": False,
            "originalExitShadowConnected": True,
            "shadowPortfolio": {"schemaId":ui.PORTFOLIO_SCHEMA,"orderTransmission":False}
        })
        status = ui.shadow_view(self.root, self.session)
        self.assertEqual(status["status"], "OBSERVED")
        self.assertEqual(status["portfolio"]["equity"], "750000")
        self.assertTrue(status["pipeline"]["shadowExitConnected"])
        self.assertEqual(ui.shadow_view(self.root,"2026-10-28")["status"],"NOT_STARTED")

    def test_get_only_loopback_dashboard(self):
        status = self.root / "launcher-status.json"
        account = self.root / "account.json"
        save(status, {"schemaId":ui.LAUNCH_SCHEMA,"status":"UI_READY",
                      "steps":{"excel":"READY"},"orderTransmission":False})
        save(account, observation())
        c = type("Settings", (), {"session":self.session,"launch_status_file":status,
                                 "account_file":account,"account_secondary_file":None,
                                 "shadow_root":self.root})()
        server = ui.ThreadingHTTPServer(("127.0.0.1",0),ui.Handler)
        server.config = c
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join(timeout=1)))
        conn = http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=3)
        try:
            conn.request("GET","/api/status")
            response=conn.getresponse()
            payload=json.loads(response.read())
            self.assertEqual(response.status,200)
            self.assertFalse(payload["orderTransmission"])
            self.assertIsNone(payload["account"]["totalAssets"])
            self.assertEqual(response.getheader("Cache-Control"),"no-store, max-age=0")
            conn.request("POST","/api/status")
            self.assertEqual(conn.getresponse().status,405)
            conn.close()
            conn = http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=3)
            conn.request("GET","/api/status",headers={"Host":"evil.example.com"})
            self.assertEqual(conn.getresponse().status,403)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
