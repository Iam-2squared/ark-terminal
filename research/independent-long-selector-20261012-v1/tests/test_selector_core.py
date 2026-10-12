"""Synthetic-only tests: never load private raw data or provider credentials."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from selector_core import (
    ContractError, build_features, compare_policies, evaluate_events,
    select_top5, signed_bucket, summarize,
)

JST = timezone(timedelta(hours=9))


def timestamp(day="2026-10-09", hour=9, minute=30):
    return datetime.fromisoformat(f"{day}T00:00:00+09:00").replace(
        hour=hour, minute=minute
    )


def fake_snapshot(n=30):
    dt = timestamp()
    daily = []
    for i in range(n):
        d = dt.date() - timedelta(days=n-i)
        c = 100 + i
        daily.append({
            "session": d.isoformat(),
            "availableAt": (datetime.combine(d, datetime.min.time(), JST)
                            + timedelta(hours=17)).isoformat(),
            "open": c - 1, "high": c + 2, "low": c - 2, "close": c,
            "volume": 10000 + i,
        })
    minute = []
    for i in range(6):
        start = dt - timedelta(minutes=6-i)
        px = 101 + i
        minute.append({
            "start": start.isoformat(),
            "end": (start + timedelta(minutes=1)).isoformat(),
            "availableAt": (start + timedelta(minutes=1)).isoformat(),
            "open": px - 0.1, "high": px + 0.3,
            "low": px - 0.4, "close": px,
            "volume": 1000, "turnover": 1000 * px,
        })
    return {
        "session": "2026-10-09",
        "decisionTime": dt.isoformat(),
        "symbol": "1234", "securityId": "TEST-1234",
        "assetType": "JPX_CASH_EQUITY",
        "universeEligible": True,
        "eligibilityKnownAt": timestamp(hour=8).isoformat(),
        "corporateActionSafe": True,
        "eligibleUniverseHash": "synthetic-same-universe",
        "priceBasis": "RAW_SYNTHETIC",
        "dailyContinuityVerified": True,
        "dailyToMinutePriceParityVerified": True,
        "intradayCoverageCertified": True,
        "dailyBars": daily,
        "minuteBars": minute,
        "extraAsOf": {
            "market_breadth_pct": {
                "value": 52.0, "availableAt": timestamp(hour=9, minute=29).isoformat(),
                "pitVerified": True,
            },
        },
    }


def pick(symbol, price=100.0):
    return {
        "session": "2026-10-09",
        "decisionTime": timestamp().isoformat(),
        "symbol": symbol,
        "decisionPrice": price,
        "eligibleUniverseHash": "same-hash",
        "priceBasis": "RAW_SYNTHETIC",
        "assetType": "JPX_CASH_EQUITY",
        "score": 0.0,
    }


def future_bar(high, low, close):
    start = timestamp()
    return [{
        "kind": "CONTINUOUS_5M",
        "start": start.isoformat(),
        "end": (start + timedelta(minutes=5)).isoformat(),
        "availableAt": (start + timedelta(minutes=5)).isoformat(),
        "high": high, "low": low, "close": close,
    }]


class CausalFeaturesTests(unittest.TestCase):
    def test_five_day_sma_is_prior_closed_daily(self):
        snap = fake_snapshot()
        row = build_features(snap)
        last_five = [125, 126, 127, 128, 129]
        wanted = 100.0 * (106 / (sum(last_five) / 5) - 1.0)
        self.assertAlmostEqual(row["features"]["daily_sma5_distance_pct"], wanted)
        self.assertIsNotNone(row["features"]["daily_sma5_slope_pct"])
        self.assertEqual(row["priceAgeSeconds"], 0)
        self.assertEqual(row["features"]["market_breadth_pct"], 52.0)

    def test_reject_future_minute(self):
        snap = fake_snapshot()
        snap["minuteBars"][-1]["availableAt"] = (
            timestamp() + timedelta(seconds=10)
        ).isoformat()
        with self.assertRaisesRegex(ContractError, "MINUTE_NOT_CAUSALLY_AVAILABLE"):
            build_features(snap)

    def test_reject_current_session_daily(self):
        snap = fake_snapshot()
        snap["dailyBars"][-1]["session"] = snap["session"]
        with self.assertRaisesRegex(ContractError, "FUTURE_OR_DUPLICATE_DAILY"):
            build_features(snap)

    def test_reject_unverified_state_and_extra(self):
        snap = fake_snapshot()
        snap["state9"] = {
            "primary": "RISE", "pitVerified": False,
            "availableAt": timestamp(hour=9, minute=28).isoformat(),
        }
        with self.assertRaisesRegex(ContractError, "STATE_ASOF_UNVERIFIED"):
            build_features(snap)
        del snap["state9"]
        snap["extraAsOf"]["market_breadth_pct"]["pitVerified"] = False
        with self.assertRaisesRegex(ContractError, "EXTRA_FEATURE_ASOF_UNVERIFIED"):
            build_features(snap)

    def test_no_implicit_forward_fill_or_lookahead(self):
        snap = fake_snapshot()
        snap["minuteBars"][-1]["availableAt"] = timestamp(
            hour=9, minute=20
        ).isoformat()
        with self.assertRaises(ContractError):
            build_features(snap)
        snap = fake_snapshot()
        snap["minuteBars"] = snap["minuteBars"][:1]
        with self.assertRaisesRegex(ContractError, "STALE_PRICE"):
            build_features(snap)

    def test_source_parity_missing_keeps_daily_sma_unknown(self):
        snap = fake_snapshot()
        snap["dailyToMinutePriceParityVerified"] = False
        row = build_features(snap)
        self.assertIsNone(row["features"]["daily_sma5_distance_pct"])
        self.assertIsNone(row["features"]["opening_gap_pct"])
        self.assertIsNotNone(row["features"]["daily_sma5_slope_pct"])

    def test_future_key_forbidden_in_feature_snapshot(self):
        snap = fake_snapshot()
        snap["futureHigh"] = 200
        with self.assertRaisesRegex(ContractError, "FUTURE_INFORMATION"):
            build_features(snap)


class EvaluatorTests(unittest.TestCase):
    def test_signed_bins_do_not_clip_losses(self):
        expected = [
            (-5.8, "-6..<-5"), (-5.0, "-5..<-4"),
            (-2.0, "-2..<-1"), (-1.0, "-1..<0"),
            (-0.01, "-1..<0"), (0.0, "0..<1"),
            (0.999, "0..<1"), (1.0, "1..<2"),
            (4.999, "4..<5"), (5.0, ">=5"),
        ]
        for value, band in expected:
            with self.subTest(value=value):
                self.assertEqual(signed_bucket(value), band)
        self.assertEqual(signed_bucket(None), "UNKNOWN")

    def test_future_high_can_be_below_selection_price(self):
        row = pick("A")
        key = ("2026-10-09", timestamp().isoformat(), "A")
        result = evaluate_events([row], {key: future_bar(99, 97, 98)})[0]
        self.assertAlmostEqual(result["signedHighPct"], -1.0)
        self.assertEqual(result["bucket"], "-1..<0")
        self.assertAlmostEqual(result["maePct"], -3.0)
        self.assertEqual(summarize([result])["downsideCounts"]["3"], 1)

    def test_unevaluable_future_is_unknown_not_no_upside(self):
        result = evaluate_events([pick("A")], {})[0]
        self.assertEqual(result["bucket"], "UNKNOWN")
        self.assertIsNone(result["signedHighPct"])
        self.assertEqual(summarize([result])["unknownN"], 1)

    def test_future_bar_before_decision_rejected(self):
        row = pick("A")
        key = ("2026-10-09", timestamp().isoformat(), "A")
        bad = future_bar(110, 98, 108)
        bad[0]["start"] = (timestamp() - timedelta(minutes=5)).isoformat()
        with self.assertRaisesRegex(ContractError, "INVALID_FUTURE_BAR"):
            evaluate_events([row], {key: bad})

    def test_rank_deterministic_tie_break_and_no_outcome(self):
        rows = [pick("D"), pick("E"), pick("C"), pick("B"), pick("A"), pick("F")]
        self.assertEqual([x["symbol"] for x in select_top5(rows)],
                         ["A", "B", "C", "D", "E"])
        rows[0]["outcomeFutureHigh"] = 105
        with self.assertRaisesRegex(ContractError, "OUTCOME_IN_SCORING"):
            select_top5(rows)

    def test_fair_comparison_requires_identical_decision_universe(self):
        old = [pick(str(i)) for i in range(5)]
        new = [pick(str(i)) for i in range(1, 6)]
        outcomes = {}
        for i in range(6):
            k = ("2026-10-09", timestamp().isoformat(), str(i))
            if i != 5:
                outcomes[k] = future_bar(106, 96, 104)
            else:
                outcomes[k] = future_bar(99, 97, 98)
        report = compare_policies(old, new, outcomes)
        self.assertEqual(report["baseline"]["cumulativeHighCounts"]["5"], 5)
        self.assertEqual(report["candidate"]["cumulativeHighCounts"]["5"], 4)
        self.assertEqual(report["candidate"]["exclusiveBucketCounts"]["-1..<0"], 1)
        self.assertEqual(report["pairedDecisionN"], 1)
        for row in new:
            row["eligibleUniverseHash"] = "different"
        with self.assertRaisesRegex(ContractError, "UNPAIRED_GROUPS"):
            compare_policies(old, new, outcomes)


if __name__ == "__main__":
    unittest.main()
