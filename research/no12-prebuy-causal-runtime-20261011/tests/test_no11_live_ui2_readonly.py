"""Regression: UI2 live-only never displays Shadow/synthetic or stale broker data."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "tools" / "no11_live_ui2_readonly.py"
spec = importlib.util.spec_from_file_location("no11_live_ui2_readonly", SOURCE)
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)
DAY = "2026-11-02"
NOW = datetime(2026, 11, 2, 10, 0, 8, tzinfo=timezone(timedelta(hours=9)))


def ledger():
    return dict(schemaId=ui.LEDGER, sessionDate=DAY,
                evidenceMode="BROKER_OBSERVATION",
                orderTransmission=False, productionReady=False,
                positionCount=1,
                positions={"entry": {"symbol": "7203.T", "quantity": 100,
                                     "knownCostJpy": "102000", "costComplete": True,
                                     "fillTimeVerified": True}},
                orders={"intent": {"symbol": "7203.T", "side": "BUY", "quantity": 100,
                                   "cumulativeQuantity": 100, "phase": "FILLED",
                                   "brokerOrderNumber": "123456"}},
                commands={}, newBuysAllowed=False, cashJpy="650000",
                availableCashJpy="650000", reservedCashJpy="0",
                unresolvedCommands=[])


def actual():
    return dict(schemaId=ui.BROKER, sessionDate=DAY,
                evaluatedAtJst="2026-11-02T10:00:06+09:00",
                mode="LIVE", evidenceMode="BROKER_OBSERVATION",
                orderTransmission=True, realFillsAppliedToShadow=False,
                sourceCurrent=True, buyingPowerRefreshVerified=True,
                securitiesOnlyOpeningCashReviewed=True,
                entryPipelineHalted=False, entryHaltReasons=[],
                ledger=ledger(),
                capital={"intents": []}, positionCount=1)


def sealed(body):
    return dict(body, sha256=ui.checksum(body))


class LiveUIReadOnly(unittest.TestCase):
    def test_real_ledger_positions_and_orders_only(self):
        model = ui.project(actual(), DAY, NOW)
        self.assertTrue(model["realBrokerReportObserved"])
        self.assertEqual(model["positionCount"], 1)
        self.assertEqual(model["positions"][0]["symbol"], "7203.T")
        self.assertEqual(model["orders"][0]["brokerOrderNumber"], "123456")
        self.assertEqual(model["cashJpy"], "650000")
        self.assertIsNone(model["realOrderAccepted"])
        self.assertIsNone(model["realOrderFilled"])
        self.assertFalse(model["simulatedDataIncluded"])
        self.assertFalse(model["uiCanPlaceOrders"])
        self.assertFalse(model["uiCanStopEngine"])
        self.assertFalse(model["performanceVerified"])

    def test_shadow_and_offline_sources_fail_closed(self):
        for key, value in (("mode", "OBSERVE_ONLY"), ("evidenceMode", "OFFLINE_REPLAY"),
                           ("orderTransmission", False), ("realFillsAppliedToShadow", True),
                           ("sessionDate", "2026-10-30")):
            fake = actual()
            fake[key] = value
            model = ui.project(fake, DAY, NOW)
            self.assertFalse(model["realBrokerReportObserved"], key)
            self.assertEqual(model["orders"], [], key)
            self.assertEqual(model["positions"], [], key)

    def test_stale_or_future_report_is_not_a_live_balance(self):
        for now in (NOW + timedelta(seconds=100),
                    NOW - timedelta(seconds=30)):
            model = ui.project(actual(), DAY, now)
            self.assertFalse(model["realBrokerReportObserved"])
            self.assertIsNone(model["cashJpy"])
            self.assertFalse(model["newBuysAllowed"])

    def test_no_cash_display_without_securities_only_review(self):
        report = actual()
        report["securitiesOnlyOpeningCashReviewed"] = False
        model = ui.project(report, DAY, NOW)
        self.assertTrue(model["realBrokerReportObserved"])
        self.assertIsNone(model["cashJpy"])
        self.assertIsNone(model["reservedCashJpy"])

    def test_external_position_is_not_included(self):
        report = actual()
        report["ledger"]["positions"] = {}
        report["ledger"]["positionCount"] = 0
        model = ui.project(report, DAY, NOW)
        self.assertEqual(model["positionCount"], 0)
        self.assertEqual(model["positions"], [])
        self.assertNotIn("externalPositions", model)

    def test_identity_checked_pointer_run_and_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(ui.read_model(root, DAY, NOW)["status"],
                             "WAITING_FOR_ACTIVE_REAL_RUN")
            run = root / ("session-" + DAY + "-" + "a" * 32)
            (run / "inference").mkdir(parents=True)
            contract = dict(schemaId=ui.CONTRACT, sessionDate=DAY,
                            runRoot=str(run),
                            extras={"brokerExecutionConfig": {"path": "/private/broker.json",
                                                             "sha256": "a" * 64}},
                            productionReady=False, orderTransmission=False)
            pointer = dict(schemaId=ui.POINTER, sessionDate=DAY,
                           runRoot=str(run), contractSha256=ui.checksum(contract),
                           productionReady=False, orderTransmission=False)
            p = root / ("received-session-" + DAY + ".active.json")
            p.write_text(json.dumps(sealed(pointer)), encoding="utf-8")
            (run / "run-contract.json").write_text(json.dumps(sealed(contract)), encoding="utf-8")
            (run / "inference" / "broker-execution-latest-report.json").write_text(
                json.dumps(actual()), encoding="utf-8")
            model = ui.read_model(root, DAY, NOW)
            self.assertTrue(model["realBrokerReportObserved"])
            changed = dict(sealed(pointer), runRoot=str(root / "elsewhere"))
            p.write_text(json.dumps(changed), encoding="utf-8")
            self.assertFalse(ui.read_model(root, DAY, NOW)["realBrokerReportObserved"])

    def test_ui_pages_are_six_live_readonly_sections(self):
        doc = (HERE.parent / "ui" / "no11_live_operations.html").read_text(encoding="utf-8")
        self.assertEqual(doc.count("data-view="), 6)
        self.assertIn("ARK TERMINAL 2.0", doc)
        self.assertIn("/api/live", doc)
        self.assertNotIn("SHADOW PORTFOLIO", doc)
        self.assertNotIn("Ark Terminal Shadow READ ONLY", doc)
        self.assertNotIn("const mock", doc)
        self.assertNotIn("7203.T", doc)
        self.assertIn("実口座", doc)
        self.assertIn("READ ONLY", doc)


if __name__ == "__main__":
    unittest.main()
