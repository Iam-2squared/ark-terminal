"""Artificial contracts only. No user market originals or provider credentials."""
import copy
import sys
import unittest
from datetime import date, datetime, timedelta
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preopen_selector import (CONTRACT, LABEL, JST, POS_BINS, PreopenConfig,
    PreopenError, build_preopen_features, compare_preopen_watchlists, digest,
    evaluate_open_high, make_watchlist, positive_bucket, rational, row_key,
    summarize_open_high, symbol, validate_feature_row, verify_watchlist)
from preopen_model import HEADS, validate_plan, train_preopen_model


def snapshot(code="13010", session="2025-08-01"):
    now = date.fromisoformat(session)
    ds = [(now-timedelta(days=i)).isoformat() for i in range(90,0,-1)]
    bars = []
    for i,d in enumerate(ds):
        c = 200 + i*0.25
        bars.append({"session": d, "availableAt": d+"T17:00:00+09:00",
                     "open": c-1, "high": c+2, "low": c-2, "close": c,
                     "volume": 1000+i, "turnover": (1000+i)*c})
    return {"session":session,"symbol":code,"assetType":"JPX_CASH_EQUITY",
            "sampleKind":"SYNTHETIC", "previousSession":ds[-1],
            "historySessions":ds,"dailyBars":bars,
            "master":{"knownAt": ds[-1]+"T18:00:00+09:00", "pitVerified":True,
                      "eligible":True,"segment":"PRIME","commonStock":True,"lotSize":100},
            "historyBasisVerifiedAsOf":True,"historyBasisKnownAt":ds[-1]+"T18:00:00+09:00",
            "universeHash":"synthetic-universe", "sourceManifestSha256":"synthetic-sources"}


def feature(code="13010", session="2025-08-01", x=1):
    config = PreopenConfig()
    feats = {"preopen_synthetic_signal":float(x), "preopen_missing_source":None}
    return {"schema":"ARK_PREOPEN_FEATURE_ROW_V1", "contract":CONTRACT,
            "configHash":config.sha,"session":session,"symbol":code,
            "cutoff":config.at(session).isoformat(),"assetType":"JPX_CASH_EQUITY",
            "universeHash":"synthetic-universe", "sourceManifestSha256":"synthetic-sources",
            "features":feats,"featureHash":digest(feats),"sampleKind":"SYNTHETIC"}


def label(code="13010", session="2025-08-01", o="100", h="105", l="97", c="103"):
    return {"labelId":LABEL,"session":session,"symbol":code,"market":"T",
            "priceBasis":"RAW_JPX_CASH","traded":True,"completeSession":True,
            "officialFirstTradeOpen":True,"open":o,"high":h,"low":l,"close":c}


def watch(rows):
    return make_watchlist(rows,{row_key(r):float(-i) for i,r in enumerate(rows)})


def evaluated(lab):
    w = watch([feature(lab["symbol"],lab["session"])])
    return evaluate_open_high(w,{row_key(lab):lab})[0]


class PreopenFeatureTests(unittest.TestCase):
    def test_d1_15_and_25_day_lines_use_prior_close(self):
        s = snapshot()
        r = build_preopen_features(s)
        cs = [b["close"] for b in s["dailyBars"]]
        for n in (5,15,25,75):
            wanted = 100*(cs[-1]/(sum(cs[-n:])/n)-1)
            self.assertAlmostEqual(r["features"][f"preopen_daily_sma_close_distance_pct_{n}"],wanted)
        self.assertTrue(all(k.startswith("preopen_") for k in r["features"]))
        # Breadth of unrelated indicators is important, not inflated MA count.
        self.assertGreater(r["featureCount"],300)
        self.assertLess(r["observedFeatureCount"],r["featureCount"])
        self.assertFalse(r["productionReady"])

    def test_preopen_exactly_four_ma_horizons_and_diverse_known_features(self):
        from technical_feature_library import DAILY_PERIODS
        self.assertEqual(DAILY_PERIODS, (5, 15, 25, 75))
        s = snapshot()
        # Large previous-day tape volume/value relative to earlier actual days.
        s["dailyBars"][-1]["volume"] *= 5
        s["dailyBars"][-1]["turnover"] *= 5
        prev = s["previousSession"] + "T19:00:00+09:00"
        facts = ("valuation_pbr", "fin_sales_yoy_pct", "topix_return_5d",
                 "investor_foreign_net_flow_ratio")
        s["asofFacts"] = {
            k: {"value": float(i + 1), "knownAt": prev, "observedAt": prev,
                "pitVerified": True, "sourceId": "synthetic-"+k,
                "liveRefreshContractVerified": True}
            for i,k in enumerate(facts)
        }
        f = build_preopen_features(s)["features"]
        for family in ("sma_close_distance_pct", "ema_close_distance_pct",
                       "sma_slope_pct", "ema_slope_pct"):
            times = {int(k.rsplit("_",1)[-1]) for k in f
                     if k.startswith("preopen_daily_"+family+"_")}
            self.assertEqual(times, set(DAILY_PERIODS),family)
        self.assertFalse(any(
            k.startswith(("preopen_week_sma_", "preopen_week_ema_",
                          "preopen_month_sma_", "preopen_month_ema_"))
            for k in f))
        for name in (
            "rsi_14", "atr_pct_14", "mfi_14", "cmf_20", "volume_ratio_20",
            "turnover_ratio_20", "volume_price_trend_25",
            "adx14", "macd_12_26_pct", "ichimoku_tenkan9_pct",
            "prior_day_price_impact_20d_per_100m_jpy",
        ):
            self.assertIsNotNone(f["preopen_daily_"+name],name)
        self.assertGreater(f["preopen_daily_prior_day_volume_spike_vs_20d"], 4)
        self.assertGreater(f["preopen_daily_prior_day_turnover_spike_vs_20d"], 4)
        for i,k in enumerate(facts):
            self.assertEqual(f["preopen_external_"+k],float(i+1))
        self.assertIsNone(f["preopen_external_news_sentiment"])
        self.assertNotIn("preopen_daily_sma_close_distance_pct_200",f)

    def test_unverified_fundamentals_and_volume_never_implicitly_zero(self):
        s = snapshot()
        s["asofFacts"] = {"valuation_pbr": {
            "value": 0, "knownAt":s["session"]+"T09:00:00+09:00",
            "observedAt":s["session"]+"T08:30:00+09:00",
            "pitVerified":True, "sourceId":"synthetic-pbr"}}
        out = build_preopen_features(s)
        self.assertIsNone(out["features"]["preopen_external_valuation_pbr"])
        s2 = snapshot()
        s2["dailyBars"][-1]["turnover"] = None
        # Admitted source may reject earlier than the indicator library.
        with self.assertRaises((ValueError,PreopenError)):
            build_preopen_features(s2)

    def test_current_day_bar_rejected(self):
        s = snapshot(); s["dailyBars"][-1]["session"] = s["session"]
        with self.assertRaises(PreopenError): build_preopen_features(s)

    def test_late_released_daily_rejected(self):
        s=snapshot();s["dailyBars"][-1]["availableAt"]=s["session"]+"T09:00:00+09:00"
        with self.assertRaisesRegex(PreopenError,"FUTURE_DAILY"):
            build_preopen_features(s)

    def test_no_old_five_minute_price_freshness_rule(self):
        self.assertIsInstance(build_preopen_features(snapshot())["priorClose"],float)

    def test_cutoff_not_allowed_during_market(self):
        with self.assertRaisesRegex(PreopenError,"PRECEDE_09"):
            build_preopen_features(snapshot(),PreopenConfig(cutoff="09:00:00"))

    def test_current_state_rejected(self):
        s=snapshot();s["state9"]={"primary":"RISE"}
        with self.assertRaisesRegex(PreopenError,"CURRENT_SESSION"):
            build_preopen_features(s)

    def test_dated_master_must_be_known(self):
        s=snapshot();s["master"]["knownAt"]=s["session"]+"T10:00:00+09:00"
        with self.assertRaisesRegex(PreopenError,"MASTER_ASOF"):
            build_preopen_features(s)

    def test_previous_calendar_gap_not_filled(self):
        s=snapshot();s["dailyBars"].pop(15)
        with self.assertRaisesRegex(PreopenError,"DAILY_SESSION_NO_FILL"):
            build_preopen_features(s)

    def test_future_adjustments_blocked(self):
        s=snapshot();s["historyBasisKnownAt"]=s["session"]+"T15:30:00+09:00"
        with self.assertRaisesRegex(PreopenError,"FUTURE_PRICE_ADJUSTMENT"):
            build_preopen_features(s)

    def test_cash_only_and_common_stock(self):
        s=snapshot();s["assetType"]="MARGIN"
        with self.assertRaises(PreopenError):build_preopen_features(s)
        s=snapshot();s["master"]["commonStock"]=False
        with self.assertRaises(PreopenError):build_preopen_features(s)

    def test_missing_turnover_never_zero(self):
        s=snapshot();s["dailyBars"][-1]["turnover"]=None
        with self.assertRaises(PreopenError):build_preopen_features(s)

    def test_unknown_and_late_optional_facts_remain_none(self):
        s=snapshot();s["asofFacts"]={"valuation_per":{"value":10,"knownAt":s["session"]+"T09:01:00+09:00",
             "observedAt":s["session"]+"T08:30:00+09:00","pitVerified":True,
             "sourceId":"synthetic-PER","liveRefreshContractVerified":True}}
        r=build_preopen_features(s)
        self.assertIsNone(r["features"]["preopen_external_valuation_per"])
        s["asofFacts"]["valuation_per"]["knownAt"]=s["session"]+"T08:30:00+09:00"
        r=build_preopen_features(s)
        self.assertEqual(r["features"]["preopen_external_valuation_per"],10)

    def test_current_minute_cannot_masquerade_as_prior(self):
        s=snapshot();s["previousMinuteCoverageVerified"]=True
        s["previousMinuteBars"]=[{"start":s["session"]+"T09:00:00+09:00",
            "end":s["session"]+"T09:01:00+09:00","availableAt":s["session"]+"T09:01:00+09:00"}]
        with self.assertRaises(PreopenError):build_preopen_features(s)


class OpeningHighTests(unittest.TestCase):
    def test_exact_all_integer_bucket_boundaries(self):
        for t in range(6):
            lab=label(h=str(100+t),c="100")
            r=evaluated(lab)
            self.assertEqual(r["bucket"],POS_BINS[t])
            if t: self.assertTrue(r["upHits"][str(t)])
        self.assertEqual(positive_bucket(Fraction(999999999999999,1000000000000000)),"0..<1")

    def test_decimal_ratio_no_float_boundary_drift(self):
        r=evaluated(label(o="33.3",h="33.633",l="32",c="33.3"))
        self.assertEqual(r["bucket"],"1..<2")
        self.assertEqual(r["openHighPct"],1.0)

    def test_zero_high_upside_is_not_proof_of_safety(self):
        r=evaluated(label(h="100",l="70",c="71"))
        self.assertEqual(r["openHighPct"],0)
        self.assertEqual(r["openLowPct"],-30)
        self.assertTrue(r["exactZero"])
        self.assertTrue(r["closeNegative"])

    def test_invalid_high_below_open_is_error_not_negative_bucket(self):
        with self.assertRaisesRegex(PreopenError,"INVALID_OUTCOME_OHLC"):
            evaluated(label(h="99",l="90",c="95"))

    def test_delayed_actual_open_kept(self):
        lab=label();lab["openingAt"]="2025-08-01T09:27:15+09:00"
        self.assertEqual(evaluated(lab)["openingAt"],lab["openingAt"])

    def test_no_trade_retained_unknown(self):
        lab=label();lab["traded"]=False
        r=evaluated(lab)
        self.assertEqual(r["status"],"UNKNOWN")
        self.assertEqual(summarize_open_high([r])["unknownN"],1)

    def test_missing_incomplete_open_not_replaced(self):
        w=watch([feature(),feature("13020")]);lab=label();lab["completeSession"]=False
        rs=evaluate_open_high(w,{row_key(lab):lab})
        self.assertEqual(len(rs),2)
        self.assertEqual(summarize_open_high(rs)["unknownN"],2)

    def test_adjusted_and_raw_prices_not_mixed(self):
        lab=label();lab["priceBasis"]="ADJUSTED"
        with self.assertRaisesRegex(PreopenError,"PRICE_BASIS"):
            evaluated(lab)

    def test_wrong_label_identity_rejected(self):
        w=watch([feature()])
        with self.assertRaisesRegex(PreopenError,"IDENTITY"):
            evaluate_open_high(w,{("2025-08-01","13010"):label("13020")})

    def test_future_label_change_cannot_change_watchlist(self):
        rows=[feature("13010"),feature("13020")];w=watch(rows)
        before=copy.deepcopy(w)
        evaluate_open_high(w,{("2025-08-01","13010"):label(h="110")})
        evaluate_open_high(w,{("2025-08-01","13010"):label(h="150")})
        self.assertEqual(w,before)

    def test_summary_has_all_bins_and_unknown_denominator(self):
        a=evaluated(label());b={"status":"UNKNOWN"}
        report=summarize_open_high([a,b])
        self.assertEqual(set(report["buckets"]),set(POS_BINS))
        self.assertEqual(report["highHitLowerBoundPct"]["5"],50)
        self.assertEqual(report["negativeOpenHighN"],0)
        self.assertEqual(report["negativeCountInterpretation"],"STRUCTURAL_NOT_PREDICTIVE")

    def test_invalid_finite_and_boolean_values(self):
        for value in (True,float("nan"),float("inf")):
            with self.assertRaises(PreopenError):rational(value)


class WatchlistTests(unittest.TestCase):
    def test_cap15_once_per_symbol_not_daytime_top5(self):
        rows=[feature(f"{1000+i}0",x=i) for i in range(20)]
        w=watch(rows)
        self.assertEqual(w["selectedN"],15)
        self.assertEqual(w["eligibleN"],20)
        self.assertFalse(w["entryAllowed"])
        self.assertFalse(w["executionAllowed"])
        verify_watchlist(w)

    def test_small_universe_not_padded(self):
        self.assertEqual(watch([feature()])["selectedN"],1)

    def test_duplicate_canonical_symbol_rejected(self):
        rows=[feature("1301"),feature("13010")]
        with self.assertRaisesRegex(PreopenError,"DUPLICATE"):
            make_watchlist(rows,{("2025-08-01","13010"):1})

    def test_symbol_mapping_alpha_and_bad_suffix(self):
        self.assertEqual(symbol("285A0"),"285A0")
        with self.assertRaises(PreopenError):symbol("13011")

    def test_changed_watchlist_and_features_rejected(self):
        w=watch([feature()]);w["items"][0]["rank"]=2
        with self.assertRaises(PreopenError):verify_watchlist(w)
        r=feature();r["features"]["preopen_synthetic_signal"]=2
        with self.assertRaisesRegex(PreopenError,"HASH_MISMATCH"):
            validate_feature_row(r)

    def test_fair_comparator_rejects_later_information(self):
        a=watch([feature()]);b=copy.deepcopy(a)
        b["selectionInformation"]="LEGACY_09_30_TOP5"
        b["watchlistHash"]=digest({k:v for k,v in b.items() if k!="watchlistHash"})
        with self.assertRaisesRegex(PreopenError,"LATER_INFORMATION"):
            compare_preopen_watchlists(a,b,{})

    def test_paired_same_information_and_source(self):
        a=watch([feature()]);b=watch([feature()])
        report=compare_preopen_watchlists(a,b,{("2025-08-01","13010"):label()})
        self.assertTrue(report["infoSetMatched"])
        self.assertEqual(sum(report["deltaBucketN"].values()),0)


class TrainingPlanTests(unittest.TestCase):
    def plan(self):
        return {"contract":CONTRACT,"mode":"SYNTHETIC","splits":{
            "fit":["2025-01-06"],"calibration":["2025-01-07"],"report":["2025-01-08"]}}

    def test_synthetic_cannot_bypass_real_rows(self):
        r=feature(session="2025-01-06");r["sampleKind"]="HISTORICAL"
        with self.assertRaisesRegex(PreopenError,"REAL_ROW"):
            validate_plan(self.plan(),{"fit":[r]})

    def test_no_random_row_calibration_split(self):
        p=self.plan();p["splits"]["calibration"]=["2025-01-06"]
        with self.assertRaisesRegex(PreopenError,"TIME_LEAKAGE"):
            validate_plan(p,{})

    def test_existing_seal_overrides_new_dates(self):
        p=self.plan();p["protectedSessions"]=["2025-01-07"]
        with self.assertRaisesRegex(PreopenError,"PROTECTED"):
            validate_plan(p,{})

    def test_market_needs_reconciled_sources(self):
        p=self.plan();p["mode"]="AUTHORIZED_DEVELOPMENT"
        with self.assertRaisesRegex(PreopenError,"MARKET_INPUT_GATE"):
            validate_plan(p,{})

    def test_high_negative_degenerate_head_removed(self):
        self.assertNotIn("signed_high_negative",HEADS)
        self.assertIn("close_negative",HEADS)
        self.assertEqual(len(HEADS),10)


if __name__=="__main__":
    unittest.main()
