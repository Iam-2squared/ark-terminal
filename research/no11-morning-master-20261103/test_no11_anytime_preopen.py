"""Offline regression for flexible same-day standby.

Never invokes an actual worker, creates a broker order, touches Excel, or
modifies the installed OneClick. Tests exact transforms in memory.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest

import no11_anytime_preopen as a

HERE = Path(__file__).resolve().parent
DAY = "2026-11-13"


def raw(name):
    return (HERE / name).read_bytes()


class SourceMigration(unittest.TestCase):
    def test_worker_early_start_is_same_day_and_does_not_widen_native_trade(self):
        before = raw("Start-No11PreopenStandby.ps1")
        after = a.worker(before)
        self.assertNotEqual(before, after)
        txt = after.decode("utf-8-sig")
        self.assertIn("IsArmWindow", txt)
        self.assertIn("$t.ToString('HH:mm:ss') -ge '00:00:00'", txt)
        self.assertIn("$t.ToString('HH:mm:ss') -lt '09:00:00'", txt)
        self.assertIn("'SELFTEST_MIDNIGHT'", txt)
        self.assertIn("'SELFTEST_EARLY'", txt)
        self.assertIn("IsLaunchWindow $launchClock", txt)
        self.assertIn("$t.ToString('HH:mm:ss') -ge '09:00:00'", txt)
        self.assertIn("$t.ToString('HH:mm:ss') -lt '09:02:00'", txt)
        self.assertIn("$req.sessionDate -ceq $day", txt)
        self.assertIn("$req.sameDayExplicitOrderApproval -eq $true", txt)
        self.assertIn("'PREOPEN-'+$day+'.execution-claimed'", txt)
        self.assertIn("'-Mode','Trade','-IApproveOrdersForToday'", txt)
        self.assertIn("PREOPEN_NEVER_RETRIES_TRADE=True", txt)
        with self.assertRaises(ValueError):
            a.worker(after)

    def test_ui_only_widens_same_day_queue_and_preserves_enabled_actions(self):
        before = raw("Start-No11OneClick.ps1")
        after = a.ui(before)
        old, new = (x.decode("utf-8-sig") for x in (before, after))
        self.assertIn("    $now.ToString('HH:mm:ss') -lt '00:00:00' -or", new)
        self.assertIn("    $now.ToString('HH:mm:ss') -ge '09:00:00'", new)
        self.assertIn("$s.sessionDate -cne $now.ToString('yyyy-MM-dd')", new)
        self.assertIn("$s.mode -cne 'OUTSIDE_ENTRY_WINDOW'", new)
        self.assertIn("$s.reason -cne 'NEW_ENTRY_WINDOW_CLOSED'", new)
        for token in ("$trade.Enabled=", "$nightly.Enabled=", "$review.Enabled="):
            self.assertEqual([line for line in old.splitlines() if token in line],
                             [line for line in new.splitlines() if token in line])
        for token in ("$trade.Add_Click({", "$nightly.Add_Click({",
                      "$refresh.Add_Click({RefreshUi})", "$review.Add_Click({"):
            self.assertEqual(old.count(token), new.count(token))
        self.assertEqual(old.count("StartOriginal 'Trade'"), new.count("StartOriginal 'Trade'"))
        with self.assertRaises(ValueError):
            a.ui(after)

    def test_display_same_day_early_reservation_and_no_backward_acceptance(self):
        before = raw("no11_oneclick_display_v2.py")
        after = a.display(before)
        self.assertNotEqual(before, after)
        mod = types.ModuleType("ark_no11_anytime_display_test")
        mod.__file__ = str(HERE / "no11_oneclick_display_v2.py")
        exec(compile(after.decode("utf-8-sig"), mod.__file__, "exec"), mod.__dict__)
        with tempfile.TemporaryDirectory() as d:
            store = Path(d)
            name = "PREOPEN-" + DAY + ".request.json"
            def receipt(issued):
                return {
                    "schemaId": "ARK_NO11_PREOPEN_STANDBY_REQUEST_V1",
                    "sessionDate": DAY,
                    "requestedAtJst": issued,
                    "earliestTradeStartJst": DAY + "T09:00:00+09:00",
                    "expiresAtJst": DAY + "T09:02:00+09:00",
                    "nonce": "a" * 32, "sameDayExplicitOrderApproval": True,
                    "tradeLaunchedAtArm": False, "orderTransmissionAtArm": False,
                }
            for time in ("00:00:00", "05:20:00", "08:29:59", "08:59:59"):
                with self.subTest(time=time):
                    (store / name).write_text(
                        json.dumps(receipt(DAY + "T" + time + "+09:00")),
                        encoding="utf-8")
                    now = datetime.fromisoformat(DAY + "T08:59:59+09:00")
                    r = mod.reservation(store, DAY, now)
                    self.assertEqual(r["state"], "RESERVED_RECORD")
            # Unlike the old status UI, a valid early reservation is displayed.
            now = datetime.fromisoformat(DAY + "T07:00:00+09:00")
            (store / name).write_text(json.dumps(receipt(DAY + "T06:00:00+09:00")))
            r = mod.reservation(store, DAY, now)
            state = {"mode": "OUTSIDE_ENTRY_WINDOW", "reason": "NEW_ENTRY_WINDOW_CLOSED",
                     "canRequestTrade": False}
            shown = mod.present(state, now, r, {"state": "NO_RECORD"},
                                {"state": "NOT_READY"}, "NOT_VERIFIED")
            self.assertEqual(shown["phase"], "BEFORE_OPEN")
            self.assertIn("RESERVED 09:00", shown["trading"])
            self.assertFalse(shown["liveVerified"])
            self.assertFalse(shown["orderTransmission"])
            # Previous-night approval cannot secretly carry into the next day.
            (store / name).write_text(
                json.dumps(receipt("2026-11-12T21:00:00+09:00")),
                encoding="utf-8")
            self.assertEqual(mod.reservation(store, DAY, now)["state"], "UNVERIFIED")
            (store / name).write_text(
                json.dumps(receipt(DAY + "T09:00:00+09:00")),
                encoding="utf-8")
            self.assertEqual(mod.reservation(store, DAY, now)["state"], "UNVERIFIED")
            (store / name).write_text(
                json.dumps(receipt(DAY + "T06:00:00+09:00")),
                encoding="utf-8")
            later = datetime.fromisoformat(DAY + "T09:02:00+09:00")
            self.assertEqual(mod.reservation(store, DAY, later)["state"], "EXPIRED")
        with self.assertRaises(ValueError):
            a.display(after)

    def test_all_changes_are_limited_to_three_reviewed_sources(self):
        self.assertEqual(set(a.TARGETS), {
            a.MORNING + "Start-No11PreopenStandby.ps1",
            a.MORNING + "Start-No11OneClick.ps1",
            a.MORNING + "no11_oneclick_display_v2.py",
        })
        # Native broker transport, buy/exit policy, one-shot receipt and
        # session config are NOT in this source migration.
        self.assertTrue(all("broker" not in f and "transport" not in f
                            and "service" not in f for f in a.TARGETS))
        for filename, fn in (("Start-No11PreopenStandby.ps1", a.worker),
                             ("Start-No11OneClick.ps1", a.ui),
                             ("no11_oneclick_display_v2.py", a.display)):
            self.assertEqual(fn(raw(filename)), fn(raw(filename)))
        self.assertTrue(a.MARK.endswith("_V1"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
