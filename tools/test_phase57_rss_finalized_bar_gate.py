import unittest
from datetime import datetime

from phase57_rss_finalization import BarState, FinalizationError
from phase57_rss_finalized_bar_gate import FinalizedBarShadowGate


def bar(t, close=100, volume=1000):
    return BarState("2026-09-15", t, 100, 101, 99, close, volume)


class FinalizedBarShadowGateTests(unittest.TestCase):
    def test_forming_latest_bar_is_never_released(self):
        gate = FinalizedBarShadowGate()
        out = gate.observe([bar("11:05")], datetime.fromisoformat("2026-09-15T11:10:00"))
        self.assertEqual(out["released"], [])

    def test_observed_next_bar_releases_previous_once(self):
        gate = FinalizedBarShadowGate()
        first = gate.observe(
            [bar("11:05"), bar("11:10")],
            datetime.fromisoformat("2026-09-15T11:10:02.708"),
        )
        self.assertEqual(len(first["released"]), 1)
        self.assertEqual(first["released"][0]["bar"]["time"], "11:05")
        self.assertEqual(first["released"][0]["finalizedByNextBar"], "11:10")
        self.assertFalse(first["released"][0]["safety"]["transmitted"])
        again = gate.observe(
            [bar("11:05"), bar("11:10")],
            datetime.fromisoformat("2026-09-15T11:10:20"),
        )
        self.assertEqual(again["released"], [])

    def test_finalized_revision_fails_closed(self):
        gate = FinalizedBarShadowGate()
        gate.observe([bar("11:05"), bar("11:10")], datetime.fromisoformat("2026-09-15T11:10:02.708"))
        with self.assertRaisesRegex(FinalizationError, "FINALIZED_BAR_REVISED"):
            gate.observe([bar("11:05", close=101), bar("11:10")], datetime.fromisoformat("2026-09-15T11:10:30"))

    def test_non_five_minute_successor_fails_closed(self):
        gate = FinalizedBarShadowGate()
        with self.assertRaisesRegex(FinalizationError, "NON_5M_NEXT_BAR"):
            gate.observe([bar("11:05"), bar("11:15")], datetime.fromisoformat("2026-09-15T11:15:42.709"))

    def test_all_safety_writes_remain_false(self):
        gate = FinalizedBarShadowGate()
        out = gate.observe([bar("11:10"), bar("11:15")], datetime.fromisoformat("2026-09-15T11:15:42.709"))
        safety = out["released"][0]["safety"]
        for key in (
            "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
            "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
            "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted",
        ):
            self.assertIs(safety[key], False)


if __name__ == "__main__":
    unittest.main()
