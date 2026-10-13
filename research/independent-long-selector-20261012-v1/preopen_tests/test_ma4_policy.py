"""MA4 policy and stale-cache rejection tests; no market source or fit."""
import copy
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preopen_feature_policy import (policy_hash, preopen_schema, cache_binding,
                                   technical_contracts, source_code_hash)
from technical_feature_library import feature_registry, build_ohlcv_features
from preopen_selector import build_preopen_features, validate_feature_row, digest, PreopenError
from preopen_feature_store import write_feature_store, FeatureStore
from run_preopen_selector import load_feature_input
from test_preopen import snapshot, feature
from build_preopen_native_bundle import current_earnings_versions, ordinary_stock_master
from preopen_native_source import parse_ohlcv


class Ma4FixedParameterTests(unittest.TestCase):
    def test_indicator_periods_are_fixed_individually(self):
        names = feature_registry("preopen_daily")
        self.assertEqual([k for k in names if k.startswith("preopen_daily_rsi_")],
                         ["preopen_daily_rsi_14"])
        self.assertEqual([k for k in names if k.startswith("preopen_daily_atr_pct_")],
                         ["preopen_daily_atr_pct_14"])
        self.assertEqual([k for k in names if k.startswith("preopen_daily_bollinger_z_")],
                         ["preopen_daily_bollinger_z_20"])
        self.assertFalse(any("williams_r" in k for k in names))
        self.assertIn("preopen_daily_stochastic_k_14", names)

    def test_extra_daily_ma_and_coarse_grid_refused(self):
        for prefix, periods in (("preopen_daily", (5,15,25,75,200)),
                                ("preopen_week", (5,15,25,75)),
                                ("preopen_month", (5,15,25,75))):
            with self.assertRaisesRegex(ValueError,"UNAPPROVED"):
                feature_registry(prefix, periods)
        with self.assertRaisesRegex(ValueError,"GRID"):
            feature_registry("preopen_daily", signal_periods=(3,5,14,20))
        for interval in ("week", "month"):
            names = feature_registry("preopen_"+interval, ())
            self.assertFalse(any(word in k for k in names for word in ("sma_", "ema_", "rsi_", "macd", "adx", "ichimoku")))
            self.assertIn(f"preopen_{interval}_return_pct_12", names)

    def test_full_builder_matches_schema_and_propagates_missing_reasons(self):
        s = snapshot(); s["dailyBars"] = s["dailyBars"][-30:]
        s["historySessions"] = [x["session"] for x in s["dailyBars"]]
        r = build_preopen_features(s)
        self.assertEqual(tuple(sorted(r["features"])), preopen_schema())
        self.assertEqual(r["featurePolicyHash"], policy_hash())
        self.assertEqual(r["missingReasons"]["preopen_daily_sma_slope_pct_75"], "INSUFFICIENT_LOOKBACK")
        self.assertEqual(r["missingReasons"]["preopen_daily_macd_signal9_pct"], "INSUFFICIENT_LOOKBACK")

    def test_market_row_cannot_supply_external_or_serialized_200_day_line(self):
        for key in ("preopen_daily_sma_close_distance_pct_200", "preopen_external_topix_sma200_distance"):
            r = build_preopen_features(snapshot()); r["sampleKind"] = "HISTORICAL"
            r["features"][key] = 1; r["featureHash"] = digest(r["features"])
            with self.assertRaisesRegex(PreopenError,"UNAPPROVED"):
                validate_feature_row(r)

    def test_75_day_slope_needs_76_closes_independent_expected_formula(self):
        s = snapshot(); bars = s["dailyBars"][-75:]
        f = build_ohlcv_features(bars, prefix="preopen_daily", reference_price=None)
        self.assertIsNotNone(f["preopen_daily_sma_close_distance_pct_75"])
        self.assertIsNone(f["preopen_daily_sma_slope_pct_75"])
        bars = s["dailyBars"][-76:]
        f = build_ohlcv_features(bars, prefix="preopen_daily", reference_price=None)
        closes = [b["close"] for b in bars]
        self.assertAlmostEqual(f["preopen_daily_sma_slope_pct_75"],
            100*(sum(closes[1:])/sum(closes[:-1])-1))
        self.assertEqual(technical_contracts("preopen_daily",(5,15,25,75))["preopen_daily_sma_slope_pct_75"]["minimumBars"],76)

    def test_bollinger_population_definition_matches_independent_arithmetic(self):
        bars = snapshot()["dailyBars"][-20:]
        closes = [b["close"] for b in bars]
        avg = sum(closes)/20
        sd = math.sqrt(sum((x-avg)**2 for x in closes)/20)
        f = build_ohlcv_features(bars, prefix="preopen_daily", reference_price=None)
        self.assertAlmostEqual(f["preopen_daily_bollinger_z_20"],(closes[-1]-avg)/sd)
        self.assertAlmostEqual(f["preopen_daily_bollinger_width_pct_20"],400*sd/avg)

    def test_prior_spike_excludes_evaluated_day_and_uses_median(self):
        bars = snapshot()["dailyBars"][-21:]
        for b in bars[:-1]: b["volume"] = 100; b["turnover"] = 10000
        bars[-2]["volume"] = 10000; bars[-2]["turnover"] = 1000000
        bars[-1]["volume"] = 500; bars[-1]["turnover"] = 50000
        f = build_ohlcv_features(bars, prefix="preopen_daily", reference_price=None)
        self.assertEqual(f["preopen_daily_prior_day_volume_spike_vs_20d"],5)
        self.assertEqual(f["preopen_daily_prior_day_turnover_spike_vs_20d"],5)
        self.assertAlmostEqual(f["preopen_daily_volume_ratio_20"],500/((18*100+10000+500)/20))


class CacheBindingTests(unittest.TestCase):
    def test_code_policy_input_calendar_basis_and_schema_each_change_cache_key(self):
        args = dict(code_hash="1"*64, input_hash="2"*64, calendar_hash="3"*64,
                    basis_hash="4"*64, schema_hash="5"*64)
        original = cache_binding(**args)
        for k in args:
            self.assertNotEqual(original["cacheKey"], cache_binding(**{**args,k:"6"*64})["cacheKey"])
        with self.assertRaises(ValueError):cache_binding(**{**args,"calendar_hash":"unverified"})

    def test_old_columnar_cache_is_refused_before_reading_rows(self):
        with self.assertRaisesRegex(PreopenError,"STALE"):
            load_feature_input({"format":"ARK_PREOPEN_COLUMNAR_FEATURES_V1"},Path("/not-mounted"))

    def test_tampered_policy_or_calendar_binding_is_rejected(self):
        for field in ("featurePolicyHash", "calendarHash", "codeHash"):
            with tempfile.TemporaryDirectory() as t:
                root = Path(t); row = build_preopen_features(snapshot())
                entry = write_feature_store([row],root/"features",private_root=root,
                    input_manifest_hash="1"*64,cache_context={"calendarHash":"2"*64,"basisHash":"3"*64})
                path = Path(entry["path"]); obj = json.loads(path.read_text())
                obj["cacheBinding"][field] = "0"*64; path.write_text(json.dumps(obj))
                with self.assertRaises(PreopenError):FeatureStore(path,private_root=root)


class NativePitAuditTests(unittest.TestCase):
    def test_direct_financial_and_valuation_aliases_keep_one_canonical_output(self):
        names = preopen_schema()
        self.assertIn("preopen_external_fin_sales", names)
        self.assertNotIn("preopen_native_fin_Sales", names)
        self.assertIn("preopen_external_valuation_pbr", names)
        self.assertNotIn("preopen_native_valuation_PBR", names)
        self.assertIn("preopen_native_fin_CFI", names)
        self.assertIn("preopen_native_valuation_FwdEPS", names)
        for field in ("EPS", "BPS", "ROE"):
            self.assertIn("preopen_native_fin_"+field, names)
        self.assertIn("preopen_external_valuation_eps", names)
        from build_preopen_native_bundle import FIN_MAPPING
        self.assertNotIn("valuation_eps", FIN_MAPPING.values())

    def test_schedule_revision_and_tbd_do_not_reuse_earlier_date(self):
        first = {"Code":"10000","FQName":"2Q","FYE":"0930",
                 "PubDate":"2024-10-01","SchDate":"2024-11-01"}
        changed = {**first,"PubDate":"2024-10-10","FYE":"1231","SchDate":"2024-11-15"}
        self.assertEqual(current_earnings_versions([first, changed]),[changed])
        tbd = {**changed,"PubDate":"2024-10-20","SchDate":""}
        self.assertEqual(current_earnings_versions([changed, first, tbd]),[tbd])
        with self.assertRaisesRegex(PreopenError,"AMBIGUOUS"):
            current_earnings_versions([changed,{**changed,"SchDate":"2024-11-16"}])

    def test_prodcat_011_and_suffix_zero_do_not_certify_common_stock(self):
        class Store:
            request = {"mode":"AUTHORIZED_DEVELOPMENT"}
        row = {"Code":"10000","Mkt":"0111","ProdCat":"011"}
        with self.assertRaisesRegex(PreopenError,"CLASSIFICATION_NOT_VERIFIED"):
            ordinary_stock_master(Store(),"2024-10-02",[row])
        Store.request = {"mode":"SYNTHETIC"}
        self.assertEqual(ordinary_stock_master(Store(),"2024-10-02",[row]),[])
        self.assertEqual(ordinary_stock_master(Store(),"2024-10-02",[{**row,"CommonStock":"1"}]),
                         [{**row,"CommonStock":"1"}])

    def test_invalid_adjustment_factor_never_becomes_history_reset(self):
        row = {"O":100,"H":101,"L":99,"C":100,"Vo":100,"Va":10000}
        for factor in (0,-1,"NaN","Infinity",True):
            with self.subTest(factor=factor),self.assertRaises(PreopenError):
                parse_ohlcv({**row,"AdjFactor":factor})


if __name__ == "__main__":unittest.main()
