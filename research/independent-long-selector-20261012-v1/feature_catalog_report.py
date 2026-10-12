"""Frozen-source-aware feature registry census: safe to print in public CI."""
from __future__ import annotations
import json
from selector_core import EXTRA_FEATURES
from technical_feature_library import DAILY_PERIODS, MINUTE_PERIODS, feature_registry
from tick_feature_library import tick_registry

def feature_catalog():
    d=feature_registry("daily_full",DAILY_PERIODS)
    m=feature_registry("minute_full",MINUTE_PERIODS)
    t=tick_registry()
    x=EXTRA_FEATURES
    categories={
        "daily_OHLCV":d,
        "minute_OHLCV":m,
        "tick_A_B":t,
        "asof_E_fundamentals_and_cross_section_and_state_external":x,
    }
    all_names=[s for values in categories.values() for s in values]
    if len(set(all_names))!=len(all_names):
        raise RuntimeError("DUPLICATE_FEATURE_NAME_AMONG_FAMILIES")
    return {
        "status":"FEATURE_REGISTRY_ONLY_NO_MARKET_PERFORMANCE",
        "N_catalog_not_unique_predictive_information":len(all_names),
        "familyN":{k:len(v) for k,v in categories.items()},
        "registered_daily_sma_periods":list(DAILY_PERIODS),
        "registered_minute_sma_periods":list(MINUTE_PERIODS),
        "presence_of_15_and_25_day_MA":{
            "sma15":("daily_full_sma_close_distance_pct_15" in d),
            "sma25":("daily_full_sma_close_distance_pct_25" in d),
            "ema15":("daily_full_ema_close_distance_pct_15" in d),
            "ema25":("daily_full_ema_close_distance_pct_25" in d)
        },
        "all_sources_required_before_effectiveness_claim":True,
        "missing_or_noncausal_fields_must_not_be_imputed":True,
    }
if __name__=="__main__":
    print(json.dumps(feature_catalog(),ensure_ascii=False,sort_keys=True))
