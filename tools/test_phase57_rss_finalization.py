import unittest
from datetime import datetime

from phase57_rss_finalization import BarState, FinalizationError, NextBarFinalizationObserver


def bar(t, close=100, volume=1000):
    return BarState("2026-09-15", t, 100, 101, 99, close, volume)


class FinalizationObserverTests(unittest.TestCase):
    def test_clock_boundary_alone_does_not_finalize(self):
        obs = NextBarFinalizationObserver()
        out = obs.observe([bar("11:05")], datetime.fromisoformat("2026-09-15T11:10:00"))
        self.assertEqual(out["finalized"], [])

    def test_next_bar_observation_finalizes_previous(self):
        obs = NextBarFinalizationObserver()
        out = obs.observe(
            [bar("11:05"), bar("11:10")],
            datetime.fromisoformat("2026-09-15T11:10:02.708"),
        )
        self.assertEqual(len(out["finalized"]), 1)
        self.assertEqual(out["finalized"][0]["time"], "11:05")
        self.assertEqual(out["finalized"][0]["finalizedByNextBar"], "11:10")

    def test_late_next_bar_still_finalizes_previous(self):
        obs = NextBarFinalizationObserver()
        out = obs.observe(
            [bar("11:10"), bar("11:15")],
            datetime.fromisoformat("2026-09-15T11:15:42.709"),
        )
        self.assertEqual(out["finalized"][0]["time"], "11:10")

    def test_finalized_bar_revision_fails_closed(self):
        obs = NextBarFinalizationObserver()
        obs.observe(
            [bar("11:05"), bar("11:10")],
            datetime.fromisoformat("2026-09-15T11:10:02.708"),
        )
        with self.assertRaisesRegex(FinalizationError, "FINALIZED_BAR_REVISED"):
            obs.observe(
                [bar("11:05", close=101), bar("11:10")],
                datetime.fromisoformat("2026-09-15T11:10:30"),
            )

    def test_nonmonotonic_next_bar_fails_closed(self):
        obs = NextBarFinalizationObserver()
        with self.assertRaisesRegex(FinalizationError, "NONMONOTONIC_NEXT_BAR"):
            obs.observe(
                [bar("11:10"), bar("11:05")],
                datetime.fromisoformat("2026-09-15T11:10:03"),
            )


if __name__ == "__main__":
    unittest.main()
