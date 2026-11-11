"""Offline regression tests: no RSS, Excel, broker, trade or user account files."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import tempfile
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import no11_return_after_skip as ret
import no11_manual_reconnect_review as recovery

SESSION = "2026-11-05"
NOW = datetime(2026, 11, 5, 10, 0, 30, tzinfo=timezone(timedelta(hours=9)))


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


class SkippedDayReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "private"
        self.root.mkdir()
        self.binding = self.root / "automatic-inputs.json"
        self.binding.write_bytes(encoded({
            "schemaId": "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1",
            "dailyCycleRoot": str(self.root), "orderTransmission": False,
        }))
        (self.root / "prepared-days").mkdir()

    def create(self, day: str, asof: str, *, tamper=False):
        source = self.root / day / "master-materials"
        source.mkdir(parents=True)
        hand = {
            "schemaId": "ARK_NO11_MORNING_MASTER_HANDOFF_V1",
            "sessionDate": day, "previousSession": asof,
            "selectedSymbols": ["7203.T"], "reviewStatus": "NOT_REVIEWED",
            "datedMasterCreated": False,
            "productionReady": False, "orderTransmission": False,
        }
        hb = encoded(hand)
        sha = hashlib.sha256(hb).hexdigest()
        filename = source / ("morning-handoff-" + sha + ".json")
        filename.write_bytes(hb + (b" " if tamper else b""))
        pointer = {
            "schemaId": "ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1",
            "sessionDate": day, "previousSession": asof, "handoff": str(filename),
            "handoffSha256": sha, "selectedSymbols": ["7203.T"],
            "selectedCount": 1, "productionReady": False,
            "orderTransmission": False, "humanReviewClaimed": False,
        }
        (self.root / "prepared-days" / (day + ".json")).write_bytes(encoded(pointer))

    def test_current_day_uses_actual_exact_date(self):
        self.create(SESSION, "2026-11-04")
        r = ret.inspect(self.binding, SESSION)
        self.assertEqual(r["state"], "CURRENT_DAY_HANDOFF_VERIFIED")
        self.assertFalse(r["canTrade"])
        self.assertFalse(r["freshActualRssRequired"])

    def test_skipped_day_reuses_history_without_backdating(self):
        self.create(SESSION, "2026-11-04")
        r = ret.inspect(self.binding, "2026-11-09")
        self.assertEqual(r["state"], "CATCHUP_REQUIRED")
        self.assertEqual(r["sessionDate"], "2026-11-05")
        self.assertEqual(r["daysSinceLastHandoff"], 4)
        self.assertFalse(r["canTrade"])
        self.assertFalse(r["staleHandoffMayBeTraded"])
        self.assertTrue(r["requiresNewDailyD100"])
        self.assertTrue(r["requiresRecentPrevious1M"])
        self.assertTrue(r["requiresNewChart50AndG1"])
        self.assertFalse(r["sourceDatesRelabeled"])

    def test_invalid_latest_cannot_fall_back_to_old_valid(self):
        self.create(SESSION, "2026-11-04")
        self.create("2026-11-06", SESSION, tamper=True)
        r = ret.inspect(self.binding, "2026-11-09")
        self.assertEqual(r["state"], "BLOCKED_SOURCE_INTEGRITY")
        self.assertEqual(r["latestPointerDate"], "2026-11-06")
        self.assertNotIn("sessionDate", r)

    def test_no_prepared_day_not_faked(self):
        r = ret.inspect(self.binding, SESSION)
        self.assertEqual(r["state"], "NO_PREPARED_DAY")
        self.assertFalse(r["canTrade"])

    def test_future_pointer_does_not_authorize_today(self):
        self.create("2026-11-09", "2026-11-06")
        r = ret.inspect(self.binding, SESSION)
        self.assertEqual(r["state"], "NO_PREPARED_DAY")

    def test_pointer_integrity_enforced(self):
        self.create(SESSION, "2026-11-04", tamper=True)
        r = ret.inspect(self.binding, SESSION)
        self.assertEqual(r["state"], "BLOCKED_SOURCE_INTEGRITY")


def snapshot(*, positions=None, orders=None, executions=None, ids=None):
    positions = positions if positions is not None else [
        {"symbol": "7203", "account": "一般", "quantity": 100}]
    orders = orders if orders is not None else [{
        "orderNumber": "123", "symbol": "7203", "account": "一般",
        "side": "買付", "trade": "現物", "quantity": 100,
        "filledQty": 100, "status": "約定",
    }]
    executions = executions if executions is not None else [{
        "symbol": "7203", "account": "一般", "side": "買付", "quantity": 100
    }]
    ids = ids if ids is not None else [{
        "rssOrderId": 77, "orderNumber": "123",
        "functionName": "RssStockOrder", "orderDate": SESSION,
        "orderTime": "09:10:00",
    }]
    ext = {
        "schemaId": "ARK_NO11_BROKER_OBSERVATION_V1",
        "status": "OBSERVED", "completeTables": True, "sameSnapshotVerified": True,
        "rowsTruncated": False, "readOnly": True, "orderTransmission": False,
        "captureCompletedAt": "2026-11-05T10:00:00+09:00",
        "orders": orders, "executions": executions, "positions": positions,
        "idRows": ids,
    }
    return {"schemaId": "ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1",
            "status": "OBSERVED", "readOnly": True, "orderTransmission": False,
            "brokerObservation": ext,
            "snapshot": {"orders": deepcopy(orders),
                         "executions": deepcopy(executions),
                         "positions": deepcopy(positions)}}


def ledger():
    return {
        "sessionDate": SESSION,
        "orders": {"entry-order": {
            "symbol": "7203.T", "account": "一般", "side": "BUY",
            "phase": "FILLED", "brokerOrderNumber": "123", "rssOrderId": 77,
            "quantity": 100, "cumulativeQuantity": 100,
        }},
        "positions": {"entry": {
            "symbol": "7203.T", "account": "一般", "quantity": 100,
        }},
        "commands": {"command": {
            "state": "RECEIVED", "brokerObserved": True,
            "command": {"kind": "ORDER", "rssOrderId": 77}
        }}
    }


class ManualReconnectionTests(unittest.TestCase):
    def review(self, l=None, s=None, approved=False):
        return recovery.assess(l if l is not None else ledger(),
                               s if s is not None else snapshot(), SESSION,
                               manual_confirmed=approved, now=NOW)

    def test_real_fill_and_nonzero_position_can_be_compared_once(self):
        a = self.review()
        self.assertEqual(a["state"], "MANUAL_CONFIRMATION_REQUIRED")
        b = self.review(approved=True)
        self.assertEqual(b["state"], "COLLECTOR_RESTART_REVIEW_ELIGIBLE")
        self.assertTrue(b["collectorRestartCandidate"])
        self.assertTrue(b["exitManagementMustRemainAvailable"])
        self.assertEqual(b["matchedOrders"], 1)
        self.assertEqual(b["matchedArkPositions"], 1)
        self.assertFalse(b["newBuyAuthorized"])
        self.assertFalse(b["orderResendAllowed"])
        self.assertFalse(b["haltMarkerCleared"])

    def test_original_vendor_status_semantics_and_partial_fill(self):
        from pathlib import Path
        import sys
        engine = str(HERE.parent / "no12-prebuy-causal-runtime-20261011" / "tools")
        if engine not in sys.path:
            sys.path.insert(0, engine)
        from no11_broker_fill_attribution import order_phase as original
        samples = [
            ("約定", 100, "FILLED"),
            ("出来有", 20, "PARTIAL"),
            ("執行待ち", 0, "ACKNOWLEDGED"),
            ("執行待ち", 20, "PARTIAL"),
            ("執行中", 20, "PARTIAL"),
            ("訂正済", 20, "PARTIAL"),
            ("取消済（出来有）", 20, "CANCELLED"),
            ("取消済(出来無)", 0, "CANCELLED"),
            ("出来ず（出来無）", 0, "EXPIRED"),
            ("取消中（出来無）", 0, "CANCEL_PENDING"),
        ]
        for raw, filled, wanted in samples:
            row = {"status": raw, "quantity": 100.0,
                   "filledQty": float(filled)}
            self.assertEqual(recovery.broker_order_phase(row), wanted)
            normalized = dict(row, quantity=100, filledQty=filled)
            self.assertEqual(recovery.broker_order_phase(row),
                             original(normalized))

    def test_partial_fill_uses_order_phase_not_raw_word(self):
        x = ledger()
        x["orders"]["entry-order"]["phase"] = "PARTIAL"
        x["orders"]["entry-order"]["cumulativeQuantity"] = 20
        x["positions"]["entry"]["quantity"] = 20
        r = snapshot()
        r["brokerObservation"]["orders"][0].update(status="執行中", filledQty=20)
        r["snapshot"]["orders"][0].update(status="執行中", filledQty=20)
        r["brokerObservation"]["executions"][0]["quantity"] = 20
        r["snapshot"]["executions"][0]["quantity"] = 20
        r["brokerObservation"]["positions"][0]["quantity"] = 20
        r["snapshot"]["positions"][0]["quantity"] = 20
        self.assertEqual(self.review(l=x,s=r,approved=True)["state"],
                         "COLLECTOR_RESTART_REVIEW_ELIGIBLE")

    def test_supported_vendor_side_aliases_are_reconciled(self):
        x = snapshot()
        x["brokerObservation"]["orders"][0]["side"] = "買"
        x["snapshot"]["orders"][0]["side"] = "買"
        x["brokerObservation"]["executions"][0]["side"] = "買"
        x["snapshot"]["executions"][0]["side"] = "買"
        self.assertEqual(self.review(s=x, approved=True)["state"],
                         "COLLECTOR_RESTART_REVIEW_ELIGIBLE")

    def test_reverse_broker_side_never_matches_ark_buy(self):
        x = snapshot()
        x["brokerObservation"]["orders"][0]["side"] = "売付"
        x["snapshot"]["orders"][0]["side"] = "売付"
        self.assertEqual(self.review(s=x, approved=True)["state"], "BLOCKED")

    def test_unverified_rss_order_function_or_date_blocks(self):
        for name, value in (("functionName", "RssCancelOrder"),
                            ("orderDate", "2026-11-04"),
                            ("orderTime", "INVALID")):
            x = snapshot()
            x["brokerObservation"]["idRows"][0][name] = value
            self.assertEqual(self.review(s=x, approved=True)["state"], "BLOCKED")

    def test_invalid_five_digit_symbol_never_truncated(self):
        x = snapshot()
        x["brokerObservation"]["orders"][0]["symbol"] = "72030"
        x["snapshot"]["orders"][0]["symbol"] = "72030"
        self.assertEqual(self.review(s=x, approved=True)["state"], "BLOCKED")

    def test_broker_position_quantity_mismatch(self):
        x = snapshot(positions=[{"symbol": "7203", "account": "一般",
                                 "quantity": 200}])
        self.assertEqual(self.review(s=x, approved=True)["state"], "BLOCKED")

    def test_unconfirmed_broker_command_stays_blocked(self):
        x = ledger()
        x["commands"]["command"]["brokerObserved"] = False
        x["commands"]["command"]["state"] = "IN_FLIGHT"
        self.assertEqual(self.review(l=x, approved=True)["state"], "BLOCKED")

    def test_unattributed_active_manual_order_requires_review(self):
        x = snapshot()
        row = {"orderNumber": "456", "symbol": "4755",
               "account": "一般", "side": "買付", "trade": "現物",
               "quantity": 100, "filledQty": 0, "status": "執行待ち"}
        x["brokerObservation"]["orders"].append(row)
        x["snapshot"]["orders"].append(deepcopy(row))
        self.assertEqual(self.review(s=x, approved=True)["state"], "BLOCKED")

    def test_missing_order_id_blocks(self):
        x = snapshot(ids=[])
        self.assertEqual(self.review(s=x, approved=True)["state"], "BLOCKED")

    def test_unknown_order_blocks(self):
        x = ledger()
        x["orders"]["entry-order"]["phase"] = "UNKNOWN"
        self.assertEqual(self.review(l=x, approved=True)["state"], "BLOCKED")

    def test_stale_broker_snapshot_blocks(self):
        x = snapshot()
        x["brokerObservation"]["captureCompletedAt"] = "2026-11-05T09:57:00+09:00"
        self.assertEqual(self.review(s=x, approved=True)["state"], "BLOCKED")

    def test_unrelated_external_position_not_adopted(self):
        x = snapshot()
        p = {"symbol": "4755", "account": "一般", "quantity": 100}
        x["brokerObservation"]["positions"].append(p)
        x["snapshot"]["positions"].append(deepcopy(p))
        a = self.review(s=x, approved=True)
        self.assertEqual(a["state"], "COLLECTOR_RESTART_REVIEW_ELIGIBLE")
        self.assertEqual(a["matchedArkPositions"], 1)
        self.assertFalse(a["newBuyAuthorized"])

    def test_no_trades_no_positions_is_not_required(self):
        x = {"sessionDate": SESSION, "orders": {}, "commands": {}, "positions": {}}
        s = snapshot(positions=[], orders=[], executions=[], ids=[])
        self.assertEqual(self.review(l=x, s=s, approved=True)["state"],
                         "COLLECTOR_RESTART_REVIEW_ELIGIBLE")

    def test_incomplete_or_mismatched_tables_block(self):
        s = snapshot()
        s["brokerObservation"]["sameSnapshotVerified"] = False
        self.assertEqual(self.review(s=s, approved=True)["state"], "BLOCKED")
        s = snapshot()
        s["snapshot"]["orders"][0]["quantity"] = 999
        self.assertEqual(self.review(s=s, approved=True)["state"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
