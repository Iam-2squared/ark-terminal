"""Genuine original Frozen Capital V5 Python + synthetic as-of ML R0 binding.

No real account, prices, model weights, table or orders are used in CI.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_h235_asof_forward_shadow as h
import no11_h235_capital_v5_shadow as cap
import test_no11_frozen_p1_h235_asof as fixtures


class FrozenV5BindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        models = fixtures.synthetic_models(self.root, None)
        scorer = h.FrozenH235AsOf(self.root, fixtures.SESSION, manifest=models)
        row = scorer.score(fixtures.valid_input())
        self.batch = {
            "schemaId": "ARK_NO11_H235_ASOF_PRIVATE_RANK_BATCH_V1",
            "policy": scorer.policy, "results": [row],
            "capitalV5Executed": False, "brokerOrders": 0,
            "productionReady": False, "orderTransmission": False,
        }
        self.scenario = {
            "schemaId": cap.SCENARIO, "evidenceMode": "SYNTHETIC_OFFLINE_ONLY",
            "sessionDate": fixtures.SESSION,
            "decisionAtJst": fixtures.stamp(571, 12),
            "arkCapitalInputs": {"cash": 1000000, "equity": 1000000,
                                 "exposure": 0},
            "externalSymbols": [], "arkManagedSymbols": [],
            "existingBands": [],
            "afterFirstLegalSellFill": False,
            "pendingBrokerOrders": False,
            "syntheticAccountOnly": True, "productionReady": False,
            "orderTransmission": False,
        }
        self.arrival = {"8": {
            "minute_counts": {"571": [0, 0, 0]},
            "minute_bucket": {"571": "AM_SYNTHETIC"},
            "training_session_N": 10, "B_median": 1.1, "B_p75": 1.2,
        }}

    def tearDown(self):
        self.temp.cleanup()

    def test_actual_native_original_v5_allocator_is_called_only_with_synthetic_cash(self):
        req = cap.build_request(self.batch, self.scenario, self.arrival)
        self.assertEqual(req["preorderedCandidates"][0]["block"], "8")
        self.assertEqual(req["preorderedCandidates"][0]["ML"], 1.0)
        self.assertEqual(req["minute"], 571)
        outcome = cap.fund_shadow(self.batch, self.scenario, self.arrival)
        frozen = outcome["capital"]
        self.assertTrue(outcome["originalFrozenCapitalV5ExecutedOnSynthetic"])
        self.assertEqual(frozen["fundedCount"], 1)
        self.assertEqual(frozen["allocations"][0]["band"], "B")
        self.assertGreater(frozen["allocations"][0]["quantity"], 0)
        self.assertEqual(frozen["allocations"][0]["quantity"] % 100, 0)
        self.assertEqual(frozen["externalHoldingsIncludedInEquity"], False)
        self.assertIsNone(outcome["originalArrivalSha256"])
        self.assertFalse(outcome["originalArrivalSha256Verified"])
        self.assertEqual(outcome["orders"], 0)
        self.assertFalse(outcome["productionReady"])
        self.assertFalse(outcome["orderTransmission"])

    def test_original_arrival_table_file_hash_rejects_tampering(self):
        data = h.stable_bytes(self.arrival)
        path = self.root / "arrival-fixture.json"
        path.write_bytes(data)
        tables = cap.original_arrival_tables(
            path, fixture_manifest=hashlib.sha256(data).hexdigest())
        self.assertEqual(tables["8"]["training_session_N"], 10)
        path.write_bytes(data + b" ")
        with self.assertRaisesRegex(ValueError, "ORIGINAL_ARRIVAL_HASH_MISMATCH"):
            cap.original_arrival_tables(
                path, fixture_manifest=hashlib.sha256(data).hexdigest())

    def test_real_account_context_or_sell_fill_wait_cannot_be_synthetic(self):
        for key, value in [
            ("syntheticAccountOnly", False),
            ("afterFirstLegalSellFill", True),
            ("pendingBrokerOrders", True),
            ("orderTransmission", True),
        ]:
            scenario = deepcopy(self.scenario)
            scenario[key] = value
            with self.assertRaisesRegex(ValueError, "REAL_ACCOUNT_OR_ORDER_NOT_ALLOWED"):
                cap.build_request(self.batch, scenario, self.arrival)

    def test_corrupted_ml_or_rank_cannot_enter_capital(self):
        for key, value in [
            ("ML", 10.0), ("capital_score", 7), ("rank", "S"),
            ("capacity_band", "A"), ("admission", False),
        ]:
            batch = deepcopy(self.batch)
            batch["results"][0][key] = value
            with self.assertRaisesRegex(ValueError, "R0_NATIVE_ML_OR_BAND_PARITY_INVALID"):
                cap.build_request(batch, self.scenario, self.arrival)

    def test_future_fill_or_teacher_field_in_r0_is_always_rejected(self):
        for name in ("fill_price", "teacher", "future_high"):
            batch = deepcopy(self.batch)
            batch["results"][0][name] = 100000.0
            with self.assertRaisesRegex(ValueError, "R0_SOURCE_NOT_ORIGINAL_SHADOW"):
                cap.build_request(batch, self.scenario, self.arrival)

    def test_unpinned_arrival_or_wrong_minute_cannot_grant_slot(self):
        wrong = {"8": {
            "minute_counts": {}, "minute_bucket": {},
            "training_session_N": 10, "B_median": 1, "B_p75": 1,
        }}
        with self.assertRaisesRegex(ValueError, "ORIGINAL_ARRIVAL_MINUTE_UNAVAILABLE"):
            cap.build_request(self.batch, self.scenario, wrong)
        scenario = deepcopy(self.scenario)
        scenario["decisionAtJst"] = fixtures.stamp(572, 0)
        with self.assertRaisesRegex(ValueError, "R0_BATCH_NOT_SAME_OBSERVED_MINUTE"):
            cap.build_request(self.batch, scenario, self.arrival)

    def test_external_personal_stock_stays_outside_ark_buy(self):
        scenario = deepcopy(self.scenario)
        scenario["externalSymbols"] = ["7203.T"]
        with self.assertRaisesRegex(ValueError, "FROZEN_V5_REJECTED"):
            cap.fund_shadow(self.batch, scenario, self.arrival)

    def test_unsupported_date_or_new_model_policy_cannot_fund(self):
        batch = deepcopy(self.batch)
        batch["policy"]["selectedBlock"] = 1
        with self.assertRaisesRegex(ValueError, "ORIGINAL_ASOF_R0_BATCH_REQUIRED"):
            cap.build_request(batch, self.scenario, self.arrival)
        scenario = deepcopy(self.scenario)
        scenario["sessionDate"] = "2027-01-04"
        with self.assertRaisesRegex(ValueError, "SHADOW_SESSION_OUTSIDE_SCOPE"):
            cap.build_request(self.batch, scenario, self.arrival)


if __name__ == "__main__":
    unittest.main()
