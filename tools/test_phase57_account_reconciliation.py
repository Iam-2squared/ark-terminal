import unittest
from datetime import datetime, timezone

from phase57_account_reconciliation import reconcile_account_snapshot

NOW = datetime(2026, 9, 15, 4, 0, 10, tzinfo=timezone.utc)
SAFE = {
    "executionAllowed": False,
    "brokerWriteAllowed": False,
    "excelOrderWriteAllowed": False,
    "rssOrderFunctionAllowed": False,
    "liveTradingAllowed": False,
    "paperTradingAllowed": False,
    "automaticPromotionAllowed": False,
    "productionUpdateAllowed": False,
    "transmitted": False,
}


def snapshot(positions=None, orders=None, captured="2026-09-15T13:00:00+09:00"):
    return {
        "schemaId": "ARK_ACCOUNT_READONLY_SNAPSHOT_V2",
        "capturedAt": captured,
        "source": "MARKETSPEED_II_RSS",
        "mode": "READ_ONLY",
        "positions": positions or [],
        "orders": orders or [],
        "executions": [],
        "buyingPower": 2605,
        "safety": dict(SAFE),
    }


class AccountReconciliationTests(unittest.TestCase):
    def test_exact_position_match_attests_but_never_arms(self):
        out = reconcile_account_snapshot(
            snapshot([{"symbol": "7203", "quantity": 100}]),
            [{"symbol": "7203.T", "quantity": 100}], now=NOW,
        )
        self.assertEqual(out["status"], "RECONCILIATION_PASS")
        self.assertTrue(out["reconciliationMatched"])
        self.assertFalse(out["armAllowed"])
        self.assertFalse(out["safety"]["transmitted"])

    def test_alphanumeric_jpx_code_normalizes(self):
        out = reconcile_account_snapshot(
            snapshot([{"symbol": "408A", "quantity": 180}]),
            [], external_positions=[{"symbol": "408A.T", "quantity": 180}], now=NOW,
        )
        self.assertEqual(out["status"], "RECONCILIATION_PASS")
        self.assertEqual(out["externalPositionCount"], 1)
        self.assertFalse(out["armAllowed"])

    def test_unresolved_broker_identity_blocks(self):
        out = reconcile_account_snapshot(
            snapshot([{"symbol": "", "name": "position", "quantity": 180}]), [], now=NOW,
        )
        self.assertIn("BROKER_POSITION_IDENTITY_UNRESOLVED", out["blockers"])

    def test_unknown_broker_position_blocks(self):
        out = reconcile_account_snapshot(snapshot([{"symbol": "7203", "quantity": 100}]), [], now=NOW)
        self.assertIn("UNKNOWN_BROKER_POSITION:7203.T", out["blockers"])

    def test_quantity_mismatch_blocks(self):
        out = reconcile_account_snapshot(
            snapshot([{"symbol": "7203", "quantity": 200}]),
            [{"symbol": "7203", "quantity": 100}], now=NOW,
        )
        self.assertTrue(any(x.startswith("POSITION_QUANTITY_MISMATCH:ARK:7203.T") for x in out["blockers"]))

    def test_external_quantity_mismatch_blocks(self):
        out = reconcile_account_snapshot(
            snapshot([{"symbol": "408A", "quantity": 180}]), [],
            external_positions=[{"symbol": "408A", "quantity": 100}], now=NOW,
        )
        self.assertTrue(any(x.startswith("POSITION_QUANTITY_MISMATCH:EXTERNAL:408A.T") for x in out["blockers"]))

    def test_ownership_overlap_blocks(self):
        out = reconcile_account_snapshot(
            snapshot([{"symbol": "7203", "quantity": 100}]),
            [{"symbol": "7203", "quantity": 100}],
            external_positions=[{"symbol": "7203", "quantity": 100}], now=NOW,
        )
        self.assertIn("POSITION_OWNERSHIP_OVERLAP:7203.T", out["blockers"])

    def test_partial_fill_blocks(self):
        out = reconcile_account_snapshot(
            snapshot([], [{"orderNumber": "1", "symbol": "7203", "status": "受付済", "quantity": 100, "filledQty": 50}]),
            [], now=NOW,
        )
        self.assertIn("BROKER_PARTIAL_FILL:1", out["blockers"])

    def test_stale_snapshot_blocks(self):
        out = reconcile_account_snapshot(snapshot(captured="2026-09-15T12:58:00+09:00"), [], now=NOW)
        self.assertIn("ACCOUNT_SNAPSHOT_STALE", out["blockers"])

    def test_unsafe_snapshot_blocks(self):
        value = snapshot()
        value["safety"]["brokerWriteAllowed"] = True
        out = reconcile_account_snapshot(value, [], now=NOW)
        self.assertIn("UNSAFE_ACCOUNT_SNAPSHOT:brokerWriteAllowed", out["blockers"])
        self.assertFalse(out["armAllowed"])


if __name__ == "__main__":
    unittest.main()
