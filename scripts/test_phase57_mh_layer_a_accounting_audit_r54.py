"""The frozen R34 sell cost uses Entry cost in the paired comparison."""
from decimal import Decimal
import unittest

from scripts.phase57_mh_layer_a_accounting_audit_r54 import corrected_pair


class AccountingIdentity(unittest.TestCase):
    def test_winning_exit_uses_same_entry_fee_basis(self):
        funded = {"entryId": "e", "quantity": 100, "notionalJpy": "10000"}
        old = {"entryId": "e", "quantity": 100,
               "candidatePnlJpy": "994.50000", "controlPnlJpy": "200"}
        corrected, delta = corrected_pair(old, funded, 110)
        self.assertEqual(Decimal(corrected["candidatePnlJpy"]), Decimal("995"))
        self.assertEqual(Decimal(corrected["sameQuantityPnlDeltaJpy"]), Decimal("795"))
        self.assertEqual(delta, Decimal("0.5"))

    def test_missing_exit_stays_unknown(self):
        funded = {"entryId": "e", "quantity": 100, "notionalJpy": "10000"}
        old = {"entryId": "e", "quantity": 100,
               "candidatePnlJpy": None, "controlPnlJpy": "200"}
        corrected, delta = corrected_pair(old, funded, None)
        self.assertIsNone(corrected["candidatePnlJpy"])
        self.assertEqual(delta, Decimal(0))


if __name__ == "__main__":
    unittest.main()
