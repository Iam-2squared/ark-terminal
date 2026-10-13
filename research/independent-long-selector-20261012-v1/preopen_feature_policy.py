"""Outcome-independent MA4 policy, exact schemas and derived-cache bindings."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

VERSION = "ARK_MA4_DIVERSE_FIXED_PARAMETERS_20261013_V2"
DAILY_MA = (5, 15, 25, 75)
MINUTE_MA = (5, 15, 30, 60)

# Each indicator has a reasoned horizon, not indicator x period x timeframe.
DAILY_INDICATORS = {
    "return_pct": (1, 5, 15, 25, 60),
    "high_break_pct": (20, 60), "low_buffer_pct": (20, 60),
    "range_position": (20,), "volume_ratio": (5, 20),
    "turnover_ratio": (5, 20), "volume_zscore": (25,),
    "turnover_zscore": (25,), "realized_vol_pct": (20, 60),
    "downside_vol_pct": (20, 60), "efficiency": (20,),
    "max_drawdown_pct": (20, 60), "atr_pct": (14,), "rsi": (14,),
    "bollinger_z": (20,), "bollinger_width_pct": (20,),
    "donchian_high_gap_pct": (20,), "donchian_low_gap_pct": (20,),
    "stochastic_k": (14,), "cci": (20,), "cmf": (20,), "mfi": (14,),
    "obv_delta": (25,), "volume_price_trend": (25,),
    "up_close_ratio": (20,), "up_candle_ratio": (20,),
    "close_location_avg": (20,), "range_avg_pct": (20,),
}
MINUTE_INDICATORS = {
    "return_pct": (3, 5, 10, 15, 30, 60),
    "high_break_pct": (15, 60), "low_buffer_pct": (15, 60),
    "range_position": (30,), "volume_ratio": (15, 60),
    "turnover_ratio": (15, 60), "volume_zscore": (30,),
    "turnover_zscore": (30,), "realized_vol_pct": (15, 60),
    "downside_vol_pct": (15, 60), "efficiency": (15, 60),
    "max_drawdown_pct": (60,), "atr_pct": (14,), "rsi": (14,),
    "bollinger_z": (20,), "bollinger_width_pct": (20,),
    "donchian_high_gap_pct": (30,), "donchian_low_gap_pct": (30,),
    "stochastic_k": (14,), "cci": (20,), "cmf": (20,), "mfi": (14,),
    "obv_delta": (30,), "volume_price_trend": (30,),
    "up_close_ratio": (30,), "up_candle_ratio": (30,),
    "close_location_avg": (30,), "range_avg_pct": (30,),
}
COARSE_INDICATORS = {
    "return_pct": (2, 3, 6, 12), "volume_ratio": (3,),
    "turnover_ratio": (3,), "realized_vol_pct": (6, 12),
    "downside_vol_pct": (6, 12), "efficiency": (6,),
    "max_drawdown_pct": (12,), "up_candle_ratio": (3,),
    "close_location_avg": (3,), "range_avg_pct": (3,),
}
LATEST_NAMES = ("latest_body_pct", "latest_upper_wick_pct", "latest_lower_wick_pct",
                "latest_clv", "latest_gap_pct", "latest_volume", "latest_turnover",
                "total_volume", "total_turnover")
OSCILLATOR_NAMES = ("macd_12_26_pct", "macd_signal9_pct", "macd_hist9_pct",
                    "adx14", "plus_di14", "minus_di14", "ichimoku_tenkan9_pct",
                    "ichimoku_kijun26_pct", "ichimoku_cloud_a_pct",
                    "ichimoku_cloud_b52_pct", "ichimoku_tenkan_vs_kijun_pct")
POLICY = {
    "version": VERSION, "dailyMovingAveragePeriods": DAILY_MA,
    "minuteMovingAveragePeriods": MINUTE_MA, "coarseMovingAveragePeriods": (),
    "indicatorParameters": {"daily": DAILY_INDICATORS, "minute": MINUTE_INDICATORS,
                            "week": COARSE_INDICATORS, "month": COARSE_INDICATORS},
    "recursiveSeed": "SMA_FIRST_N_IN_ACTUAL_COMPARABLE_SUFFIX",
    "recursiveAdditionalWarmupBars": 0,
    "recursiveWarmupCaveat": "ALL_AVAILABLE_SUFFIX_AFTER_SEED; NO_STATIONARITY_CERTIFICATION",
    "bollinger": "20_POPULATION_STD; Z_SCORE; WIDTH_4_STD_OVER_MEAN_PERCENT",
    "surpriseBaseline": "MEDIAN_20_PRIOR_SESSIONS_EXCLUDING_EVALUATED_D_MINUS_1",
    "relativeVolumeBaseline": "MEAN_N_INCLUDING_D_MINUS_1",
    "removedDeterministicAlias": "WILLIAMS_R_EQUALS_STOCHASTIC_K_MINUS_100",
    "nativeDirectAliasPolicy": "ONE_CANONICAL_EXTERNAL_VALUE_FOR_10_FINANCIAL_AND_6_VALUATION_DIRECT_ALIASES",
    "financialVsValuationBasis": "PRESERVE_NATIVE_FIN_EPS_BPS_ROE; NEVER_ALIAS_PERIOD_FINANCIAL_VALUES_TO_DAILY_VALUATION",
    "coarseSemantics": "REGIME_WINDOWS_ONLY_NO_MACD_WILDER_ICHIMOKU_OR_MA_GRID",
    "changedBeforeMarketFits": True, "marketResultsConsulted": False,
}


def policy_hash():
    return hashlib.sha256(json.dumps(POLICY, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_code_hash():
    root = Path(__file__).resolve().parent
    # Includes serializer/source/model/report code. Documentation-only commits
    # preserve the binding; changing computation invalidates derived caches.
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.glob("*.py"))}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def technical_contracts(prefix, periods):
    """Per-column dependency metadata; minimum seed is not stable warmup proof."""
    from technical_feature_library import feature_registry
    parameters = indicator_parameters(prefix)
    specs = {}
    extra_bar = {"return_pct", "rsi", "atr_pct", "mfi", "obv_delta",
                 "volume_price_trend", "efficiency", "realized_vol_pct",
                 "downside_vol_pct", "donchian_high_gap_pct", "donchian_low_gap_pct"}
    units = {"range_position": "RATIO", "volume_ratio": "RATIO",
             "turnover_ratio": "RATIO", "volume_zscore": "ZSCORE",
             "turnover_zscore": "ZSCORE", "bollinger_z": "ZSCORE",
             "cmf": "RATIO", "efficiency": "RATIO", "obv_delta": "RATIO",
             "volume_price_trend": "RATIO", "up_close_ratio": "RATIO",
             "up_candle_ratio": "RATIO", "close_location_avg": "RATIO",
             "rsi": "INDEX_0_100", "mfi": "INDEX_0_100",
             "stochastic_k": "INDEX_0_100", "cci": "INDEX"}
    for indicator, horizons in parameters.items():
        for n in horizons:
            name = f"{prefix}_{indicator}_{n}"
            fields = (["volume", "close"] if indicator in ("obv_delta", "volume_price_trend")
                      else ["volume"] if indicator.startswith("volume_")
                      else ["turnover"] if indicator.startswith("turnover_")
                      else ["high", "low", "close", "volume"] if indicator in ("mfi", "cmf")
                      else ["open", "high", "low", "close"])
            specs[name] = {"indicator": indicator, "parameters": {"period": n},
                           "units": units.get(indicator, "PERCENT"),
                           "minimumBars": n + int(indicator in extra_bar),
                           "requiredFields": fields, "timeScale": scope(prefix),
                           "recursiveSeed": ("WILDER_SMA_FIRST_N_DIFFERENCES" if indicator in
                                             ("rsi", "atr_pct") else None)}
    minimum = {"latest_gap_pct": 2, "macd_12_26_pct": 26,
               "macd_signal9_pct": 34, "macd_hist9_pct": 34,
               "adx14": 29, "plus_di14": 29, "minus_di14": 29,
               "ichimoku_tenkan9_pct": 9, "ichimoku_kijun26_pct": 26,
               "ichimoku_cloud_a_pct": 26, "ichimoku_cloud_b52_pct": 52,
               "ichimoku_tenkan_vs_kijun_pct": 26,
               "prior_day_volume_spike_vs_20d": 21,
               "prior_day_turnover_spike_vs_20d": 21,
               "prior_day_price_impact_20d_per_100m_jpy": 21}
    for name in feature_registry(prefix, periods):
        if name in specs:
            continue
        suffix = name[len(prefix)+1:]
        count = minimum.get(suffix, 1)
        if suffix.startswith(("sma_", "ema_")):
            if "_cross_" in suffix:
                count = max(int(suffix.split("_")[-3]), int(suffix.split("_")[-2]))
            else:
                count = int(suffix.rsplit("_", 1)[-1]) + int("slope" in suffix)
        fields = ["volume"] if "volume" in suffix else ["turnover"] if "turnover" in suffix else ["open", "high", "low", "close"]
        if "price_impact" in suffix:
            fields = ["close", "turnover"]
        specs[name] = {"indicator": suffix, "units": "SHARES" if suffix in
                       ("latest_volume", "total_volume") else "JPY" if suffix in
                       ("latest_turnover", "total_turnover") else "PERCENT_PER_100M_JPY" if
                       "price_impact" in suffix else "RATIO" if suffix == "latest_clv" else "PERCENT",
                       "minimumBars": count, "requiredFields": fields, "timeScale": scope(prefix),
                       "recursiveSeed": POLICY["recursiveSeed"] if suffix.startswith("ema_") or
                       suffix.startswith(("macd_", "adx", "plus_di", "minus_di")) else None,
                       "windowMeaning": "ALL_COMPARABLE_SUFFIX" if suffix.startswith("total_") else
                       "FIXED_WINDOW_OR_RECURSIVE_SUFFIX"}
    return specs


def technical_missing_reasons(features, bars, *, prefix, periods):
    specs = technical_contracts(prefix, periods)
    reasons = {}
    for name, spec in specs.items():
        if features[name] is not None:
            continue
        if not bars:
            reason = "SOURCE_NOT_JOINED"
        elif len(bars) < spec["minimumBars"]:
            reason = "INSUFFICIENT_LOOKBACK"
        elif any(b.get(field) is None for b in bars for field in spec["requiredFields"]):
            reason = "NOT_AVAILABLE_IN_SOURCE"
        else:
            reason = "UNDEFINED_ZERO_DENOMINATOR"
        reasons[name] = reason
    return reasons


def scope(prefix):
    if "minute" in prefix:
        return "minute"
    if "week" in prefix:
        return "week"
    if "month" in prefix:
        return "month"
    return "daily"


def indicator_parameters(prefix):
    return POLICY["indicatorParameters"][scope(prefix)]


@lru_cache(maxsize=1)
def preopen_schema():
    from technical_feature_library import feature_registry
    from selector_core import EXTRA_FEATURES
    from preopen_history_features import native_feature_names
    from preopen_selector import STATE_NAMES
    names = set(feature_registry("preopen_daily", DAILY_MA))
    names.update(feature_registry("preopen_previous_minute", MINUTE_MA))
    for interval in ("week", "month"):
        names.update(feature_registry("preopen_" + interval, ()))
    names.update("preopen_external_"+name for name in EXTRA_FEATURES)
    names.update("preopen_previous_state_"+name for name in STATE_NAMES)
    names.update(native_feature_names())
    return tuple(sorted(names))


def cache_binding(*, code_hash, input_hash, calendar_hash, basis_hash, schema_hash):
    values = {"codeHash": code_hash, "inputHash": input_hash,
              "calendarHash": calendar_hash, "basisHash": basis_hash,
              "featureSchemaHash": schema_hash, "featurePolicyHash": policy_hash()}
    if any(not isinstance(x, str) or len(x) != 64 or any(c not in "0123456789abcdef" for c in x)
           for x in values.values()):
        raise ValueError("CACHE_BINDING_REQUIRES_VERIFIED_SHA256_VALUES")
    values["cacheKey"] = hashlib.sha256(json.dumps(values, sort_keys=True,
                                                  separators=(",", ":")).encode()).hexdigest()
    return values
