"""Synthetic Tick tests: never synthesize quote/aggressor data."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tick_feature_library import (
    TickSourceError,compute_tick_features,tick_registry,
)

JST=timezone(timedelta(hours=9))
AT=datetime(2025,5,1,9,30,tzinfo=JST)


def item(minutes_ago,price,qty,side=None):
    t=AT-timedelta(minutes=minutes_ago)
    return {"tradeAt":t.isoformat(),"availableAt":t.isoformat(),
            "price":price,"quantity":qty,"aggressorSide":side}


class TickFeatureSourceTests(unittest.TestCase):
    def test_unavailable_is_not_flat_price_or_zero(self):
        features=compute_tick_features(None,decision_at=AT.isoformat(),
            decision_price=100,complete_stream_verified=False)
        self.assertGreater(len(features),30)
        self.assertIsNone(features["tick_trade_count_5m"])
        self.assertIsNone(features["tick_aggressor_buy_ratio"])
        self.assertIsNone(features["tick_spread_proxy_bps"])

    def test_trade_activity_without_fabricated_aggressor(self):
        rows=[item(9,100,1),item(5,101,3),item(4,102,5),item(2,101,7)]
        out=compute_tick_features(rows,decision_at=AT.isoformat(),
             decision_price=102,complete_stream_verified=True)
        self.assertEqual(out["tick_trade_count_5m"],2.0)
        self.assertEqual(out["tick_volume_5m"],12)
        self.assertIsNotNone(out["tick_vwap_distance_5m_pct"])
        self.assertIsNone(out["tick_aggressor_buy_ratio"])
        self.assertIsNone(out["tick_spread_proxy_bps"])

    def test_future_tick_and_order_rejected(self):
        rows=[item(4,100,1),item(-1,100,1)]
        with self.assertRaisesRegex(TickSourceError,"FUTURE"):
            compute_tick_features(rows,decision_at=AT.isoformat(),
                                  decision_price=100,complete_stream_verified=True)
        rows=[item(1,100,1),item(4,100,1)]
        with self.assertRaisesRegex(TickSourceError,"CHRONOLOGICAL"):
            compute_tick_features(rows,decision_at=AT.isoformat(),
                                  decision_price=100,complete_stream_verified=True)

    def test_verified_aggressor_only_if_side_real(self):
        rows=[item(3,100,1,"BUY"),item(2,101,1,"BUY"),
              item(1,100,1,"SELL")]
        out=compute_tick_features(rows,decision_at=AT.isoformat(),
            decision_price=100,complete_stream_verified=True,side_semantics_verified=True)
        self.assertAlmostEqual(out["tick_aggressor_buy_ratio"],2/3)
        self.assertAlmostEqual(out["tick_aggressor_net_volume_ratio"],1/3)
        none=compute_tick_features(rows,decision_at=AT.isoformat(),
            decision_price=100,complete_stream_verified=True,side_semantics_verified=False)
        self.assertIsNone(none["tick_aggressor_buy_ratio"])


if __name__=="__main__":
    unittest.main()
