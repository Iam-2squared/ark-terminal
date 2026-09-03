from __future__ import annotations

import unittest

import phase58_dynamic_slot_compat_projector as projector
import phase58_excel_dynamic_slot_capture as capture
import phase58_excel_dynamic_slot_setup as setup


class DynamicSlotTest(unittest.TestCase):
    def test_workbook_manifest_scopes_excel_writes_to_market_data_query_cells(self):
        manifest = setup.build_workbook_manifest(workbook_path="ArkLaneM.xlsx", slot_count=80, tick_rows=100)
        self.assertEqual(manifest["slotCount"], 80)
        self.assertEqual(manifest["runtimeWritableCells"], "ArkControl!B2:B81")
        self.assertTrue(manifest["symbolSwitchAtRuntime"])
        self.assertEqual(manifest["symbolSwitchScope"], "MARKET_DATA_QUERY_ONLY")
        self.assertFalse(manifest["safety"]["excelOrderWriteAllowed"])
        self.assertTrue(manifest["safety"]["excelMarketDataQueryWriteAllowed"])
        self.assertIn("RSSMARKET", manifest["allowedRssFunctions"])
        self.assertIn("RSSTICKLIST", manifest["allowedRssFunctions"])

    def test_formula_builder_uses_only_read_only_market_functions(self):
        market = setup.market_formula(2, "最良売気配値")
        ticks = setup.tick_formula(2, 100)
        self.assertIn("RssMarket", market)
        self.assertIn("RssTickList", ticks)
        setup.assert_formula_is_market_data_only(market)
        setup.assert_formula_is_market_data_only(ticks)
        with self.assertRaisesRegex(ValueError, "forbidden"):
            setup.assert_formula_is_market_data_only("=RssStockOrder(A1,B1)")

    def test_size_units_require_explicit_shares_attestation(self):
        self.assertEqual(capture.attest_size_units("SHARES", "shares"), ("SHARES", "SHARES"))
        with self.assertRaisesRegex(ValueError, "explicit"):
            capture.attest_size_units(None, "SHARES")
        with self.assertRaisesRegex(ValueError, "SHARES"):
            capture.attest_size_units("LOTS", "SHARES")
        with self.assertRaisesRegex(ValueError, "SHARES"):
            capture.attest_size_units("SHARES", "UNKNOWN")

    def test_watchlist_validator_preserves_variable_frozen_selector_cardinality(self):
        v1 = [f"{1000 + index}.T" for index in range(47)]
        v2 = v1[:28]
        payload = {
            "complete": True,
            "status": "PHASE57_MSII_DYNAMIC_WATCHLIST_READY",
            "futureOutcomeUsed": False,
            "currentV1Symbols": v1,
            "currentV2Symbols": v2,
            "pinnedSymbols": ["7203.T"],
            "assignedSymbols": [*v1, "7203.T"],
        }
        validated = capture.validate_watchlist(payload, 80)
        self.assertEqual(len(validated["currentV1Symbols"]), 47)
        self.assertEqual(len(validated["currentV2Symbols"]), 28)
        self.assertIn("7203.T", validated["assignedSymbols"])

        bad = dict(payload)
        bad["currentV2Symbols"] = [*v2, "9999.T"]
        with self.assertRaisesRegex(ValueError, "V2 must remain inside"):
            capture.validate_watchlist(bad, 80)

    def test_slot_planner_preserves_existing_desired_symbols_and_reuses_empty_slots(self):
        current = ["7203.T", "6758.T", "", "9984.T", ""]
        desired = ["7203.T", "9984.T", "8306.T"]
        planned = capture.plan_slot_assignments(current, desired, 5)
        self.assertEqual(planned[0], "7203.T")
        self.assertEqual(planned[3], "9984.T")
        self.assertIn("8306.T", planned)
        self.assertEqual({x for x in planned if x}, set(desired))

    def test_dynamic_ready_observation_projects_to_existing_lane_m_contract_with_attestation(self):
        row = {
            "schemaVersion": 2,
            "phase": "58.p32.dynamic-slot-capture",
            "recordType": "MARKET_OBSERVATION",
            "sourceMode": "MARKETSPEED_II_RSS_READ_ONLY",
            "capturedAt": "2026-09-04T00:05:01.000Z",
            "symbol": "7203.T",
            "slotId": "SLOT001",
            "assignmentGeneration": 1,
            "watchlistAsOf": "2026-09-04T00:05:00.000Z",
            "slotReady": True,
            "market": {"bestBid": 100, "bestAsk": 101, "bestBidSize": 1000, "bestAskSize": 900},
            "ticks": [],
            "sourceFunctions": ["RssMarket", "RssTickList"],
            "marketSizeUnit": "SHARES",
            "tickSizeUnit": "SHARES",
            "sizeUnitAttestation": {"explicit": True, "inferred": False, "operatorProvided": True},
            "formulaSurfaceAttestation": {"algorithm": "SHA256", "sha256": "a" * 64, "sheetNames": ["ArkControl", "ArkMarket", "ArkTicks"]},
            "methodology": {
                "dynamicSlotMode": True,
                "excelFormulaWritePerformed": False,
                "symbolSwitchWritePerformed": True,
                "symbolSwitchScope": "MARKET_DATA_QUERY_ONLY",
                "symbolSwitchCellOnly": True,
                "excelOrderWritePerformed": False,
                "pointInTimeOnly": True,
                "futureOutcomeUsed": False,
            },
            "safety": capture.SAFETY,
        }
        projected = projector.project_dynamic_slot_row(row)
        self.assertIsNotNone(projected)
        self.assertEqual(projected["schemaVersion"], 1)
        self.assertEqual(projected["phase"], "58.p31.multi-symbol-capture")
        self.assertFalse(projected["methodology"]["symbolSwitchWritePerformed"])
        self.assertTrue(projected["methodology"]["priorMarketDataQuerySwitchObserved"])
        self.assertEqual(projected["dynamicSlotProvenance"]["sourcePhase"], "58.p32.dynamic-slot-capture")
        self.assertEqual(projected["dynamicSlotProvenance"]["sourceSchemaVersion"], 2)
        self.assertTrue(projected["dynamicSlotProvenance"]["sizeUnitAttestationPreserved"])
        self.assertTrue(projected["dynamicSlotProvenance"]["formulaSurfaceAttestationPreserved"])
        self.assertEqual(projected["marketSizeUnit"], "SHARES")
        self.assertFalse(projected["safety"]["excelOrderWriteAllowed"])

    def test_schema2_projection_fails_closed_without_unit_or_formula_attestation(self):
        base = {
            "schemaVersion": 2,
            "phase": "58.p32.dynamic-slot-capture",
            "recordType": "SESSION_HEARTBEAT",
            "sourceMode": "MARKETSPEED_II_RSS_READ_ONLY",
            "marketSizeUnit": "SHARES",
            "tickSizeUnit": "SHARES",
            "methodology": {"pointInTimeOnly": True, "futureOutcomeUsed": False, "excelOrderWritePerformed": False},
            "safety": capture.SAFETY,
        }
        with self.assertRaisesRegex(ValueError, "size-unit attestation"):
            projector.project_dynamic_slot_row(base)
        with_units = dict(base)
        with_units["sizeUnitAttestation"] = {"explicit": True, "inferred": False, "operatorProvided": True}
        with self.assertRaisesRegex(ValueError, "formula-surface"):
            projector.project_dynamic_slot_row(with_units)

    def test_unsettled_slot_is_not_projected_as_market_evidence(self):
        row = {
            "schemaVersion": 1,
            "phase": "58.p32.dynamic-slot-capture",
            "recordType": "MARKET_OBSERVATION",
            "slotReady": False,
            "methodology": {"pointInTimeOnly": True, "futureOutcomeUsed": False, "excelOrderWritePerformed": False},
            "safety": capture.SAFETY,
        }
        self.assertIsNone(projector.project_dynamic_slot_row(row))

    def test_all_order_and_trading_flags_remain_false(self):
        for safety in (setup.SAFETY, capture.SAFETY):
            for key in ("executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed", "automaticPromotionAllowed", "productionUpdateAllowed"):
                self.assertFalse(safety[key])
            self.assertTrue(safety["excelMarketDataQueryWriteAllowed"])


if __name__ == "__main__":
    unittest.main()
