import unittest

from phase57_execution_dryrun_gate import build_locked_cash_order_draft

RECON = {
    "status": "RECONCILIATION_PASS",
    "reconciliationMatched": True,
    "blockers": [],
}


def intent(**changes):
    value = {
        "symbol": "7203.T",
        "direction": "LONG",
        "side": "BUY",
        "positionEffect": "OPEN",
        "quantity": 100,
        "orderType": "MARKET",
        "limitPrice": None,
        "timeInForce": "DAY",
    }
    value.update(changes)
    return value


class ExecutionDryRunGateTests(unittest.TestCase):
    def test_passed_reconciliation_builds_locked_cash_draft(self):
        out = build_locked_cash_order_draft(RECON, intent(), order_id=1)
        self.assertEqual(out["function"], "RssStockOrder")
        self.assertEqual(out["trigger"], 0)
        self.assertFalse(out["transmitted"])
        self.assertFalse(out["executable"])
        self.assertFalse(out["excelWritePerformed"])
        self.assertFalse(out["rssCallPerformed"])
        self.assertIn('RssStockOrder(1,0,"7203.T",3', out["formulaDraft"])

    def test_alphanumeric_jpx_symbol_is_accepted(self):
        out = build_locked_cash_order_draft(RECON, intent(symbol="408A.T"), order_id=2)
        self.assertIn('"408A.T"', out["formulaDraft"])

    def test_blocked_reconciliation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "RECONCILIATION_PASS_REQUIRED"):
            build_locked_cash_order_draft({"status": "RECONCILIATION_BLOCKED"}, intent(), order_id=1)

    def test_cash_short_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "CASH_SHORT_UNSUPPORTED"):
            build_locked_cash_order_draft(RECON, intent(direction="SHORT", side="SELL"), order_id=1)

    def test_wrong_cash_side_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "CASH_LONG_SIDE_MISMATCH"):
            build_locked_cash_order_draft(RECON, intent(side="SELL"), order_id=1)

    def test_non_lot_quantity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "MSII_LOT_QUANTITY_REQUIRED"):
            build_locked_cash_order_draft(RECON, intent(quantity=180), order_id=1)

    def test_market_with_limit_price_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "MARKET_LIMIT_PRICE_MUST_BE_NULL"):
            build_locked_cash_order_draft(RECON, intent(limitPrice=3000), order_id=1)

    def test_limit_draft(self):
        out = build_locked_cash_order_draft(
            RECON, intent(orderType="LIMIT", limitPrice=3000), order_id=3,
        )
        self.assertIn(',1,3000,', out["formulaDraft"])
        self.assertEqual(out["trigger"], 0)
        self.assertFalse(out["transmitted"])


if __name__ == "__main__":
    unittest.main()
