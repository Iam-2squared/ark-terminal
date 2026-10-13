"""Synthetic tests for broad as-of features and sparse missing behavior."""
import math
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from technical_feature_library import (
    DAILY_PERIODS, MINUTE_PERIODS, build_ohlcv_features, feature_registry,
)
from selector_core import ContractError, build_features

JST = timezone(timedelta(hours=9))


def bar(x: float):
    return {
        "open": x - .25, "high": x + 1,
        "low": x - 1, "close": x,
        "volume": 1000.0, "turnover": 1000.0*x,
    }


class AllTechnicalFamiliesTest(unittest.TestCase):
    def test_contains_every_requested_MA_and_15_25(self):
        self.assertEqual(DAILY_PERIODS, (5, 15, 25, 75))
        self.assertEqual(MINUTE_PERIODS, (5, 15, 30, 60))
        registry = feature_registry("daily_full")
        for n in DAILY_PERIODS:
            for family in ("sma_close_distance_pct", "ema_close_distance_pct",
                           "sma_slope_pct", "ema_slope_pct"):
                self.assertIn(f"daily_full_{family}_{n}", registry)
        for n in (2, 3, 7, 10, 14, 20, 26, 50, 100, 200, 250):
            for family in ("sma_close_distance_pct", "ema_close_distance_pct",
                           "sma_slope_pct", "ema_slope_pct"):
                self.assertNotIn(f"daily_full_{family}_{n}", registry)
        self.assertIn("daily_full_sma_cross_15_25_pct", registry)
        self.assertIn("daily_full_ema_cross_25_75_pct", registry)
        # 14 is used for RSI/ATR/MFI, and 20 for volume/band research,
        # but they are NOT 14- or 20-day moving-average lines.
        self.assertIn("daily_full_rsi_14", registry)
        self.assertIn("daily_full_volume_ratio_20", registry)
        self.assertNotIn("daily_full_sma_close_distance_pct_14", registry)

    def test_populated_trend_volatility_volume_oscillators(self):
        data = [bar(100 + i / 10) for i in range(300)]
        v = build_ohlcv_features(data, prefix="daily_full",
                                 reference_price=129.9)
        self.assertGreater(len(v), 150)
        for name in (
            "sma_close_distance_pct_5", "sma_close_distance_pct_15",
            "sma_close_distance_pct_25", "sma_cross_15_25_pct",
            "ema_cross_15_25_pct", "adx14", "plus_di14", "minus_di14",
            "macd_12_26_pct", "macd_signal9_pct", "rsi_14",
            "atr_pct_14", "bollinger_z_20", "cmf_20", "mfi_14",
            "volume_zscore_25", "volume_price_trend_25",
            "ichimoku_tenkan9_pct", "ichimoku_kijun26_pct",
            "ichimoku_cloud_b52_pct",
        ):
            self.assertIsNotNone(v[f"daily_full_{name}"], msg=name)
        self.assertAlmostEqual(
            v["daily_full_sma_close_distance_pct_15"],
            100*(129.9/(sum(100+i/10 for i in range(285,300))/15)-1),
        )
        self.assertTrue(all(x is None or math.isfinite(x) for x in v.values()))

    def test_short_sequence_explicit_unknown_not_fabricated_zero(self):
        v = build_ohlcv_features([bar(100)], prefix="minute_full",
                                  reference_price=100, periods=MINUTE_PERIODS)
        self.assertIsNone(v["minute_full_sma_close_distance_pct_15"])
        self.assertIsNone(v["minute_full_ema_close_distance_pct_25"])
        self.assertIsNone(v["minute_full_rsi_14"])
        self.assertIsNone(v["minute_full_adx14"])
        self.assertIsNotNone(v["minute_full_latest_clv"])

    def test_without_daily_price_parity_uses_daily_close_not_intraday_price(self):
        data = [bar(100 + i) for i in range(30)]
        v = build_ohlcv_features(data, prefix="daily_full", reference_price=None)
        result = 100*(129 / (sum(range(125, 130))/5)-1)
        self.assertAlmostEqual(v["daily_full_sma_close_distance_pct_5"], result)


if __name__ == "__main__":
    unittest.main()
