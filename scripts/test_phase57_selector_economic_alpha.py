import copy
import unittest

from scripts import phase57_selector_economic_alpha as m


def bar(start, o, h, l, c, missing=False):
    hour, minute = map(int, start.split(":"))
    total = hour * 60 + minute + 5
    end = f"{total // 60:02}:{total % 60:02}"
    return {
        "start": f"2024-09-17T{start}:00+09:00",
        "end": f"2024-09-17T{end}:00+09:00",
        "missing": missing,
        "o": o, "h": h, "l": l, "c": c,
        "observedMinutes": 5,
    }


def path(decision="09:30", future=None):
    return {
        "selectorEventId": f"2024-09-17|2024-09-17T{decision}:00+09:00|10000",
        "sessionDate": "2024-09-17", "symbol": "10000",
        "decisionTimestamp": f"2024-09-17T{decision}:00+09:00",
        "decisionPrice": 100.0, "direction": "LONG", "sessionEndMinute": 900,
        "entryMinute": 570, "expectedBars": len(future or []), "future": future or [],
    }


class EconomicAlphaTest(unittest.TestCase):
    def test_protocol_is_pinned_and_safe(self):
        protocol = m.load_protocol()
        self.assertEqual(protocol["scope"]["selectionRows"], 3800)
        self.assertTrue(all(value is False for value in protocol["safety"].values()))

    def test_entry_open_and_exact_completed_close(self):
        source = path(future=[
            bar("09:30", 0, 1, 0, 1),
            bar("09:35", 1, 2, 1, 2),
            bar("09:40", 2, 3, 2, 3),
        ])
        result = m.evaluate_event(source, {"savedV1Score": 1, "momentum30Pct": 0})
        self.assertAlmostEqual(result["delays"]["0"]["entryRelative"]["5"]["grossPct"], 1.0)
        self.assertAlmostEqual(result["delays"]["5"]["entryRelative"]["5"]["grossPct"], 100 * (102 / 101 - 1))
        self.assertEqual(result["delays"]["0"]["entryRelative"]["30"]["status"], "NO_EXACT_COMPLETED_CLOSE")

    def test_missing_first_eligible_bar_fails_closed(self):
        missing = bar("09:30", 0, 0, 0, 0, True)
        source = path(future=[missing, bar("09:35", 0, 1, 0, 1)])
        result = m.evaluate_event(source, {"savedV1Score": 1, "momentum30Pct": 0})
        self.assertEqual(result["delays"]["0"]["status"], "FIRST_ELIGIBLE_BAR_MISSING")
        self.assertIsNone(result["delays"]["0"]["entryRelative"]["5"]["grossPct"])

    def test_lunch_uses_first_regular_open_and_reports_latency(self):
        source = path("11:30", [bar("12:30", 0, 1, 0, 1), bar("12:35", 1, 2, 1, 2)])
        result = m.evaluate_event(source, {"savedV1Score": 1, "momentum30Pct": 0})
        self.assertEqual(result["delays"]["0"]["actualLatencyFromDecisionMin"], 60)
        self.assertEqual(result["delays"]["25"]["actualLatencyFromIntentMin"], 35)
        self.assertEqual(result["delays"]["0"]["selectorTerminal"]["30"]["status"], "NONPOSITIVE_HOLDING_WINDOW")

    def test_random_order_is_deterministic(self):
        first = m.random_key(20260919, "2024-09-17", "09:30", "72030")
        second = m.random_key(20260919, "2024-09-17", "09:30", "72030")
        changed = m.random_key(20260920, "2024-09-17", "09:30", "72030")
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)

    def test_cost_and_profit_factor(self):
        result = m.distribution([1.0, -0.5], .05)
        self.assertAlmostEqual(result["mean"], .2)
        self.assertAlmostEqual(result["profitFactor"], .95 / .55)

    def test_cluster_bootstrap_is_deterministic(self):
        protocol = m.load_protocol()
        rows = [
            {"sessionDate": "2024-09-17", "grossPct": 1.0},
            {"sessionDate": "2024-09-17", "grossPct": 0.0},
            {"sessionDate": "2024-09-18", "grossPct": -1.0},
            {"sessionDate": "2024-09-18", "grossPct": 0.0},
        ]
        first = m.cluster_summary(rows, .05, protocol)
        second = m.cluster_summary(copy.deepcopy(rows), .05, protocol)
        self.assertEqual(first, second)
        self.assertEqual(first["sessions"], 2)

    def test_dip_policy_has_mandatory_fallback(self):
        down = path(future=[bar("09:30", 0, 0, -1, -1), bar("09:35", -1, 0, -1, 0)])
        bars = m.materialize_path(down)
        decision = m.timestamp(down["decisionTimestamp"])
        entry = m.dip_entry("P1_DIP_FALLBACK10", bars, decision, 100)
        self.assertEqual(entry["timestamp"][11:16], "09:35")
        up = path(future=[bar("09:30", 0, 1, 0, 1), bar("09:35", 1, 2, 1, 2), bar("09:40", 2, 3, 2, 3)])
        bars = m.materialize_path(up)
        entry = m.dip_entry("P1_DIP_FALLBACK10", bars, decision, 100)
        self.assertEqual(entry["timestamp"][11:16], "09:40")


if __name__ == "__main__":
    unittest.main()
