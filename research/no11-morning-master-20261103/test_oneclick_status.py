"""Offline tests: no Excel, RSS, brokerage or trading process required."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

import oneclick_status as status

JST = timezone(timedelta(hours=9))
NOW = datetime(2026, 11, 5, 9, 30, tzinfo=JST)
DAY = NOW.date().isoformat()


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


class OneClickOffline(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / "unified-launcher"
        self.store.mkdir()
        self.private = self.root / "private"
        self.private.mkdir()
        self.settings = self.store / "settings.json"
        self.binding = self.store / "automatic-inputs.json"
        self.bootstrap = self.private / "bootstrap.json"
        self.handoff = self.private / "handoff.json"
        write(self.bootstrap, {"sessionDate": DAY, "privateRoot": str(self.private),
                               "orderTransmission": False})
        write(self.handoff, {"sessionDate": DAY,
                             "selectedSymbols": ["1111.T", "2222.T"],
                             "orderTransmission": False, "productionReady": False})
        write(self.settings, {"normalMaxPositions": 3, "sameDayApprovalRequired": True,
                              "automaticOrderAuthorization": False,
                              "orderTransmission": False,
                              "bootstrapConfigFile": str(self.bootstrap)})
        self.bind = {"schemaId": "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1",
                     "orderTransmission": False, "handoff": str(self.handoff)}
        write(self.binding, self.bind)

    def state(self, at=NOW):
        return status.inspect(self.settings, self.binding, at=at)

    def test_legacy_same_day_requires_approval(self):
        s = self.state()
        self.assertEqual(s["mode"], "OPERATOR_CHECK")
        self.assertTrue(s["canRequestTrade"])
        self.assertTrue(s["requiresSameDayApproval"])
        self.assertFalse(s["brokerOrderTransmission"])

    def test_duplicate_trade_blocked(self):
        write(self.store / ("TRADE-" + DAY + ".launch.json"),
              {"kind": "TRADE", "asOfDate": DAY})
        self.assertFalse(self.state()["canRequestTrade"])
        self.assertEqual(self.state()["reason"], "ALREADY_STARTED_TODAY")

    def test_existing_run_blocked_even_without_trade_marker(self):
        write(self.private / ("received-session-" + DAY + ".active.json"), {"x": 1})
        self.assertEqual(self.state()["reason"], "EXISTING_RUN_REQUIRES_REVIEW")

    def test_unsafe_config_never_enables_trade(self):
        write(self.settings, {"normalMaxPositions": 3, "sameDayApprovalRequired": False,
                              "automaticOrderAuthorization": True,
                              "orderTransmission": False,
                              "bootstrapConfigFile": str(self.bootstrap)})
        self.assertEqual(self.state()["reason"], "CONFIG_UNSAFE")

    def test_legacy_handoff_date_never_relabelled(self):
        write(self.handoff, {"sessionDate": "2026-11-04",
                             "selectedSymbols": ["1111.T"], "orderTransmission": False})
        self.assertFalse(self.state()["canRequestTrade"])

    def test_nightly_ready_only_after_close_and_installed(self):
        s = self.state(datetime(2026, 11, 5, 18, 5, tzinfo=JST))
        self.assertFalse(s["canRunNightly"])
        tool = self.private / "daily_cycle.py"
        tool.write_text("pass")
        self.bind.update(dailyCycleTool=str(tool), dailyCycleRoot=str(self.private))
        write(self.binding, self.bind)
        s = self.state(datetime(2026, 11, 5, 18, 5, tzinfo=JST))
        self.assertEqual(s["mode"], "AFTER_CLOSE")
        self.assertTrue(s["canRunNightly"])
        self.assertFalse(s["canRequestTrade"])

    def test_pinned_next_day_handoff(self):
        self.bind.update(dailyCycleRoot=str(self.private))
        write(self.binding, self.bind)
        self.assertEqual(self.state()["reason"], "TODAY_HANDOFF_MISSING")
        p = self.private / "prepared-days" / (DAY + ".json")
        sha = hashlib.sha256(self.handoff.read_bytes()).hexdigest()
        write(p, {"schemaId": "ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1",
                  "sessionDate": DAY, "handoff": str(self.handoff),
                  "handoffSha256": sha, "selectedSymbols": ["1111.T", "2222.T"],
                  "selectedCount": 2, "productionReady": False,
                  "orderTransmission": False})
        self.assertEqual(self.state()["mode"], "OPERATOR_CHECK")
        self.handoff.write_bytes(self.handoff.read_bytes() + b" ")
        self.assertFalse(self.state()["canRequestTrade"])
        self.assertEqual(self.state()["reason"], "HANDOFF_HASH_CHANGED")

    def test_entry_window_closes_at_1520(self):
        s = self.state(datetime(2026, 11, 5, 15, 20, tzinfo=JST))
        self.assertEqual(s["reason"], "NEW_ENTRY_WINDOW_CLOSED")
        self.assertFalse(s["canRequestTrade"])

    def test_non_trading_day(self):
        s = self.state(datetime(2026, 11, 7, 10, tzinfo=JST))
        self.assertEqual(s["reason"], "NON_TRADING_DAY")


if __name__ == "__main__":
    unittest.main()
