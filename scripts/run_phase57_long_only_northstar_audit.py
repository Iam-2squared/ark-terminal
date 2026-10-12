#!/usr/bin/env python3
"""NS-MEASUREMENT-1: deterministic saved-data aggregation, never model fitting.

Input rows and scores are produced by the independently audited Node preparer.
No provider client, model class, training method, or outcome-driven search exists
in this script. Output contains aggregates only, not individual security records.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


CONTRACT = "NS-MEASUREMENT-1"
KEYS = ["sessionDate", "decisionTimeJst"]
IDENTITY = ["sessionDate", "symbol", "decisionTimeJst"]
FEATURES = [
    "currentReturnPct", "momentum30Pct", "vwapDistancePct", "vwapSlope15Pct",
    "logCumulativeTurnover", "volumeAccelerationRatio", "trendEfficiency",
    "rangeExpansionPct", "timeOfDayFraction", "segmentStandard", "segmentGrowth",
    "liquidityLow", "liquidityHigh", "marketBreadthPositivePct",
    "sectorBreadthPositivePct",
]
STRINGS = IDENTITY + ["partition", "sourceGroup", "segment", "liquidityBucket"]
NUMERIC = list(dict.fromkeys(FEATURES + [
    "decisionVolatilityPct", "legacyEligible", "legacyReferencePrice",
    "legacyBucketAgeMin", "legacySourceAgeMin", "referenceAgeMin",
    "referenceValid", "referencePrice", "referenceChanged", "horizonMinutes",
    "y30Bps", "strict30Bps", "strict30FreshBps", "rawMae30Pct", "trueMae30Pct",
    "legacySessionMfePct", "legacySessionMaePct", "legacyTrueSessionMaePct",
    "futureMfePct", "trueMaePct", "futureMinuteCount", "timeTo1Min", "timeTo2Min",
    "timeTo3Min", "timeTo5Min", "finalAdditionalPct", "finalPreviousReturnPct",
    "winner", "savedV1Score", "futureOpportunity1", "futureOpportunity2",
    "futureOpportunity3", "futureOpportunity5",
]))
QUANTILES = [.01, .05, .10, .25, .50, .75, .90, .95, .99]


def number(value):
    return round(float(value), 10) if value is not None and np.isfinite(value) else None


def ratio(numerator, denominator, scale=1):
    return number(scale * numerator / denominator) if denominator else None


def finite(values):
    values = np.asarray(values, dtype=float)
    return values[np.isfinite(values)]


def distribution(values):
    raw = np.asarray(values, dtype=float)
    clean = finite(raw)
    result = {"n": int(len(clean)), "missing": int(len(raw) - len(clean))}
    names = ["min", "mean", "max"] + [f"p{int(q * 100)}" for q in QUANTILES]
    if not len(clean):
        return {**result, **{name: None for name in names}}
    return {
        **result, "min": number(clean.min()), "mean": number(clean.mean()),
        "max": number(clean.max()),
        **{f"p{int(q * 100)}": number(v) for q, v in zip(QUANTILES, np.quantile(clean, QUANTILES))},
    }


def outcome_valid(df):
    return ((df.referenceValid == 1) & np.isfinite(df.futureMfePct)
            & (df.futureMinuteCount > 0))


def outcome_hit(df, threshold):
    # Preparer compares prices directly, avoiding 4.999999999999% rounding.
    return df[f"futureOpportunity{threshold}"].eq(1)


def current_return_bucket(series):
    labels = ["LT0", "0_TO_LT1", "1_TO_LT2", "2_TO_LT3", "3_TO_LT5", "GE5"]
    return pd.cut(series, [-np.inf, 0, 1, 2, 3, 5, np.inf],
                  labels=labels, right=False).astype("object").fillna("MISSING")


def prepare_rows(df, copy=True):
    if copy:
        df = df.copy()
    for column in STRINGS:
        if column not in df:
            raise ValueError(f"Missing identity/context column: {column}")
        df[column] = df[column].fillna("UNKNOWN").astype(str)
    for column in NUMERIC:
        if column not in df:
            raise ValueError(f"Missing declared column: {column}")
        df[column] = pd.to_numeric(df[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    if df.duplicated(IDENTITY).any():
        raise ValueError("Duplicate session/symbol/decision identities")
    if not np.isfinite(df[FEATURES].to_numpy(float)).all():
        raise ValueError("Preparer emitted non-finite causal model features")
    if not (df.legacyEligible.eq(1) == df.y30Bps.notna()).all():
        raise ValueError("Legacy eligibility must equal genuinely finite y30; null is not zero")
    for age in ["legacyBucketAgeMin", "legacySourceAgeMin", "referenceAgeMin"]:
        if (df[age] < 0).any():
            raise ValueError(f"Negative price age: {age}")
    declared_valid = df.referenceValid.eq(1)
    if (declared_valid & ((df.referenceAgeMin > 5) | (df.referencePrice <= 0)
                          | df.referenceAgeMin.isna() | df.referencePrice.isna())).any():
        raise ValueError("Invalid fresh reference marked valid")
    if (df.trueMaePct.dropna() > 1e-10).any():
        raise ValueError("True adverse excursion cannot be positive")
    scorable = outcome_valid(df)
    for threshold in [1, 2, 3, 5]:
        flags = df[f"futureOpportunity{threshold}"]
        if not flags.loc[scorable].isin([0, 1]).all():
            raise ValueError("Scorable future path lacks direct-price opportunity membership")
    for raw, clipped in [("rawMae30Pct", "trueMae30Pct"),
                         ("legacySessionMaePct", "legacyTrueSessionMaePct")]:
        m = df[raw].notna() & df[clipped].notna()
        if not np.allclose(np.minimum(0, df.loc[m, raw]), df.loc[m, clipped], rtol=0, atol=1e-8):
            raise ValueError(f"Clipped MAE differs from min(0, {raw})")
    df["currentReturnBucket"] = current_return_bucket(df.currentReturnPct)
    vrank = df.groupby(KEYS, sort=False).decisionVolatilityPct.rank(method="average", pct=True)
    df["volatilityBucket"] = np.ceil(vrank * 5).clip(1, 5).astype("Int64").astype(str)
    df.loc[vrank.isna(), "volatilityBucket"] = "MISSING"
    time = df.decisionTimeJst.str.extract(r"(\d{2}):(\d{2})(?::\d{2})?")[0]
    df["timeOfDay"] = np.where(pd.to_numeric(time, errors="coerce") < 12, "MORNING", "AFTERNOON")
    df.reset_index(drop=True, inplace=True)
    return df


def bucket_summary(series, boundaries, labels):
    b = pd.cut(series, boundaries, labels=labels, include_lowest=True, right=True)
    n = int(series.notna().sum())
    counts = b.value_counts(sort=False)
    return {str(label): {"n": int(counts.get(label, 0)),
                         "pctOfFinite": ratio(int(counts.get(label, 0)), n, 100)} for label in labels}


def horizon_summary(df):
    x = df.horizonMinutes
    return {
        "distributionMinutes": distribution(x),
        "buckets": {
            "LT30": int((x < 30).sum()), "EXACT30": int((x == 30).sum()),
            "GT30_TO35": int(((x > 30) & (x <= 35)).sum()),
            "GT35_TO45": int(((x > 35) & (x <= 45)).sum()),
            "GT45_TO60": int(((x > 45) & (x <= 60)).sum()),
            "GT60_TO90": int(((x > 60) & (x <= 90)).sum()), "GT90": int((x > 90).sum()),
        },
        "non30PctOfFinite": ratio(int((x.notna() & x.ne(30)).sum()), int(x.notna().sum()), 100),
    }


def label_comparison(df, left="y30Bps", right="strict30Bps"):
    m = df[left].notna() & df[right].notna()
    a, b = df.loc[m, left], df.loc[m, right]
    n = len(a)
    varying = n > 1 and a.nunique() > 1 and b.nunique() > 1
    return {
        "left": left, "right": right, "populationRows": len(df), "commonFiniteRows": n,
        "leftFiniteRows": int(df[left].notna().sum()), "rightFiniteRows": int(df[right].notna().sum()),
        "pearson": number(a.corr(b)) if varying else None,
        "spearman": number(a.corr(b, method="spearman")) if varying else None,
        "leftMeanBps": number(a.mean()), "rightMeanBps": number(b.mean()),
        "meanAbsoluteDifferenceBps": number((a - b).abs().mean()),
        "medianAbsoluteDifferenceBps": number((a - b).abs().median()),
        "signDisagreementPct": ratio(int((np.sign(a) != np.sign(b)).sum()), n, 100),
        "opportunityDisagreement": {
            str(t): {"n": int(((a >= t) != (b >= t)).sum()),
                     "pct": ratio(int(((a >= t) != (b >= t)).sum()), n, 100)} for t in [50, 100, 200]
        },
    }


def mae_summary(df, raw, clipped):
    m = df[raw].notna() & df[clipped].notna()
    a, b = df.loc[m, raw], df.loc[m, clipped]
    return {
        "commonFiniteRows": len(a), "rawMeanPct": number(a.mean()), "trueMeanPct": number(b.mean()),
        "positiveRawMaeRows": int((a > 0).sum()),
        "positiveRawMaeRatePct": ratio(int((a > 0).sum()), len(a), 100),
        "rawMinusTrueMeanPercentagePoints": number((a - b).mean()),
        "rawDistribution": distribution(a), "trueDistribution": distribution(b),
    }


def count_mix(df, fields=("segment", "liquidityBucket", "timeOfDay")):
    return {field: {str(k): {"n": int(v), "pct": ratio(int(v), len(df), 100)}
                    for k, v in df[field].value_counts(dropna=False).items()} for field in fields}


def freshness_summary(df):
    ages = {}
    for name in ["legacyBucketAgeMin", "legacySourceAgeMin", "referenceAgeMin"]:
        ages[name] = {
            "distributionMinutes": distribution(df[name]),
            "buckets": bucket_summary(df[name], [0, 5, 10, 20, np.inf],
                                      ["0_TO5", "GT5_TO10", "GT10_TO20", "GT20"]),
        }
    return {
        "rows": len(df), "ages": ages, "freshReferenceRows": int(df.referenceValid.eq(1).sum()),
        "futureEvaluableRows": int(outcome_valid(df).sum()),
        "referenceChangedRows": int(df.referenceChanged.eq(1).sum()),
        "legacySourceStaleGT5": {"n": int(df.legacySourceAgeMin.gt(5).sum()),
                                  "mix": count_mix(df[df.legacySourceAgeMin.gt(5)])},
        "legacySourceStaleGT20": {"n": int(df.legacySourceAgeMin.gt(20).sum()),
                                   "mix": count_mix(df[df.legacySourceAgeMin.gt(20)])},
        "newReferenceStaleGT5": {"n": int(df.referenceAgeMin.gt(5).sum()),
                                 "mix": count_mix(df[df.referenceAgeMin.gt(5)])},
        "observedFutureMinuteCount": distribution(df.futureMinuteCount),
    }


def measurement_audit(df):
    return {
        "horizon": horizon_summary(df),
        "horizonByDecisionTime": {str(k): horizon_summary(g) for k, g in df.groupby("decisionTimeJst", sort=True)},
        "horizonByTimeOfDay": {str(k): horizon_summary(g) for k, g in df.groupby("timeOfDay", sort=True)},
        "legacyVsStrictSameDenominator": label_comparison(df),
        "legacyVsStrictFreshDenominator": label_comparison(df, right="strict30FreshBps"),
        "strictDenominatorSensitivity": label_comparison(df, "strict30Bps", "strict30FreshBps"),
        "decisionPriceFreshness": freshness_summary(df),
        "mae30": mae_summary(df, "rawMae30Pct", "trueMae30Pct"),
        "legacySameSessionMae": mae_summary(df, "legacySessionMaePct", "legacyTrueSessionMaePct"),
    }


def outcome_summary(df, base_prevalence=None):
    valid = df.loc[outcome_valid(df)]
    n = len(valid)
    hits5 = int(outcome_hit(valid, 5).sum())
    prevalence = hits5 / n if n else None
    return {
        "rows": len(df), "scorableRows": n, "scorableCoveragePct": ratio(n, len(df), 100),
        "futureOpportunity": {str(t): {"count": int(outcome_hit(valid, t).sum()),
                                         "prevalencePct": ratio(int(outcome_hit(valid, t).sum()), n, 100)}
                              for t in [1, 2, 3, 5]},
        "future5LiftVsSameAnalyzablePopulation": ratio(prevalence, base_prevalence) if prevalence is not None else None,
        "futureMfeMeanPct": number(valid.futureMfePct.mean()),
        "futureMfeMedianPct": number(valid.futureMfePct.median()),
        "trueMaeMeanPct": number(valid.trueMaePct.mean()),
        "finalAdditionalMeanPct": number(valid.finalAdditionalPct.mean()),
        "finalPreviousClose5RatePct": number(100 * valid.winner.mean()),
        "timeTo5Minutes": distribution(valid.loc[outcome_hit(valid, 5), "timeTo5Min"]),
    }


def alignment_for(df, column):
    values = df[column]
    ranks = df.groupby(KEYS, sort=False)[column].rank(method="average", pct=True)
    analyzable = values.notna() & outcome_valid(df)
    base = df.loc[analyzable]
    prevalence = float(outcome_hit(base, 5).mean()) if len(base) else None
    bands = {
        "TOP1": ranks.gt(.99), "TOP5": ranks.gt(.95), "TOP10": ranks.gt(.90),
        "TOP20": ranks.gt(.80), "MIDDLE20_TO80": ranks.gt(.20) & ranks.le(.80),
        "BOTTOM20": ranks.le(.20),
    }
    return {
        "variable": column,
        "interpretation": ("DESCRIPTIVE_OUTCOME_TO_OUTCOME_NOT_PREDICTIVE_SKILL"
                           if column != "savedV1Score" else "V1_SAVED_CD_REFIT_NOT_HISTORICAL_C_ONLY"),
        "finiteVariableRows": int(values.notna().sum()), "commonEvaluableRows": len(base),
        "unconditionalFuture5PrevalencePct": number(100 * prevalence) if prevalence is not None else None,
        "bands": {name: outcome_summary(df.loc[analyzable & mask], prevalence) for name, mask in bands.items()},
    }


def target_alignment(df):
    valid = outcome_valid(df)
    common = df.loc[valid & df.y30Bps.notna() & df.strict30Bps.notna()]
    common_fresh = common.loc[common.strict30FreshBps.notna()]
    total_hits = int((valid & outcome_hit(df, 5)).sum())
    buckets = {}
    for name, group in df.groupby("currentReturnBucket", sort=True, observed=True):
        summary = outcome_summary(group)
        hits = summary["futureOpportunity"]["5"]["count"]
        buckets[str(name)] = {**summary, "shareOfAllFuture5OpportunitiesPct": ratio(hits, total_hits, 100)}
    early = df[df.currentReturnPct < 3]
    return {
        "fullCrossSection": outcome_summary(df),
        "alignments": {name: alignment_for(df, name)
                       for name in ["y30Bps", "strict30Bps", "strict30FreshBps", "savedV1Score"]},
        "commonLegacyStrictAlignment": {
            "commonEvaluableRows": len(common),
            "populationRule": "FINITE_LEGACY_AND_STRICT_AND_VALID_FUTURE_PATH_SAME_ROWS_RECOMPUTED_PERCENTILES",
            "alignments": {name: alignment_for(common, name) for name in ["y30Bps", "strict30Bps"]},
        },
        "commonLegacyStrictFreshAlignment": {
            "commonEvaluableRows": len(common_fresh),
            "populationRule": "FINITE_LEGACY_STRICT_STRICTFRESH_AND_VALID_FUTURE_PATH_SAME_ROWS_RECOMPUTED_PERCENTILES",
            "alignments": {name: alignment_for(common_fresh, name)
                           for name in ["y30Bps", "strict30Bps", "strict30FreshBps"]},
        },
        "currentReturnBuckets": buckets,
        "earlyCurrentReturnLT3": {
            **outcome_summary(early),
            "shareOfAllFuture5OpportunitiesPct": ratio(int((outcome_valid(early) & outcome_hit(early, 5)).sum()), total_hits, 100),
        },
    }


def effect_and_overlap(a, b):
    a, b = finite(a), finite(b)
    def stats(x):
        return {"n": len(x), "mean": number(x.mean()) if len(x) else None,
                "median": number(np.median(x)) if len(x) else None,
                "p25": number(np.quantile(x, .25)) if len(x) else None,
                "p75": number(np.quantile(x, .75)) if len(x) else None}
    result = {"opportunity": stats(a), "control": stats(b), "standardizedMeanDifference": None,
              "distributionOverlap": None, "histogramBins": 0}
    if not len(a) or not len(b):
        return result
    pooled = np.concatenate([a, b])
    unique = np.unique(pooled)
    if len(unique) == 1:
        return {**result, "standardizedMeanDifference": 0.0, "distributionOverlap": 1.0, "histogramBins": 1}
    denom = len(a) + len(b) - 2
    var = (((a - a.mean()) ** 2).sum() + ((b - b.mean()) ** 2).sum()) / denom if denom > 0 else np.nan
    if var > 0:
        result["standardizedMeanDifference"] = number((a.mean() - b.mean()) / np.sqrt(var))
    else:
        result["zeroWithinGroupVarianceDifferentMeans"] = True
    edges = np.array([-np.inf, (unique[0] + unique[1]) / 2, np.inf]) if len(unique) == 2 else np.unique(np.quantile(pooled, np.linspace(0, 1, 21)))
    edges[0], edges[-1] = -np.inf, np.inf
    pa = np.histogram(a, edges)[0] / len(a)
    pb = np.histogram(b, edges)[0] / len(b)
    result["distributionOverlap"] = number(np.minimum(pa, pb).sum())
    result["histogramBins"] = len(edges) - 1
    return result


def matched_indices(df, early=False):
    eligible = outcome_valid(df)
    if early:
        eligible &= df.currentReturnPct.lt(3)
    fields = KEYS + ["segment", "currentReturnBucket", "liquidityBucket", "volatilityBucket"]
    candidates = df.loc[eligible, fields + ["symbol", "futureOpportunity5"]].copy()
    candidates["_index"] = candidates.index
    # Row identity is used only to select deterministically, never emitted.
    identity = (CONTRACT + "|" + candidates.sessionDate + "|" + candidates.symbol + "|" + candidates.decisionTimeJst)
    candidates["_hash"] = identity.map(lambda value: hashlib.sha256(value.encode()).hexdigest())
    candidates = candidates.sort_values(fields + ["_hash", "symbol"], kind="mergesort")
    opportunity = candidates[candidates.futureOpportunity5.eq(1)].copy()
    control = candidates[candidates.futureOpportunity5.eq(0)].copy()
    opportunity["_pair"] = opportunity.groupby(fields, sort=False, dropna=False).cumcount()
    control["_pair"] = control.groupby(fields, sort=False, dropna=False).cumcount()
    pairs = opportunity[fields + ["_pair", "_index"]].merge(
        control[fields + ["_pair", "_index"]], on=fields + ["_pair"], suffixes=("_opp", "_ctrl"), validate="one_to_one")
    return pairs._index_opp.to_numpy(), pairs._index_ctrl.to_numpy(), opportunity._index.to_numpy(), control._index.to_numpy()


def feature_sufficiency(df, early=False):
    opp, ctrl, all_opp, all_ctrl = matched_indices(df, early)
    unmatched = df.loc[np.setdiff1d(all_opp, opp)]
    return {
        "comparison": "EARLY_CURRENT_RETURN_LT3" if early else "ALL_FUTURE5",
        "matching": "EXACT_SESSION_TIME_MARKET_RETURNBIN_LIQUIDITY_VOLQUINTILE_1TO1_SHA256_WITHOUT_REPLACEMENT",
        "opportunityAvailable": len(all_opp), "controlAvailable": len(all_ctrl), "matchedPairs": len(opp),
        "opportunityMatchRatePct": ratio(len(opp), len(all_opp), 100),
        "unmatchedOpportunities": len(all_opp) - len(opp), "unmatchedOpportunityMix": count_mix(unmatched),
        "unusedControls": len(all_ctrl) - len(ctrl),
        "features": {name: effect_and_overlap(df.loc[opp, name], df.loc[ctrl, name]) for name in FEATURES},
        "limitation": "Unmatched observations excluded without relaxing strata; marginal overlap cannot exclude multivariate interactions.",
    }


def select_top5(df):
    policy = df.loc[df.legacyEligible.eq(1)]
    # A missing score may not silently shrink the ranking population.
    if policy.savedV1Score.isna().any():
        raise ValueError("Saved score missing in original eligible universe; Top5 cannot be reconstructed")
    # Sort narrow keys, not the several-million-row feature/outcome frame.
    ordered = policy[KEYS + ["savedV1Score", "symbol"]].sort_values(
        KEYS + ["savedV1Score", "symbol"], ascending=[True, True, False, True], kind="mergesort")
    indices = ordered.groupby(KEYS, sort=False).head(5).index
    selected = policy.loc[indices]
    return policy, selected


def capacity_metrics(policy, selected):
    good = outcome_valid(policy)
    selected_good = selected.loc[outcome_valid(selected)]
    nt = policy.groupby(KEYS, sort=False).size()
    kt = nt.clip(upper=5)
    et = policy.loc[good].groupby(KEYS, sort=False).size().reindex(nt.index, fill_value=0)
    expected_evaluable = float((et * kt / nt).sum())
    total_evaluable = int(good.sum())
    result = {}
    for threshold in [1, 2, 3, 5]:
        opportunities = policy.loc[good & outcome_hit(policy, threshold)]
        ot = opportunities.groupby(KEYS, sort=False).size().reindex(nt.index, fill_value=0)
        opportunity_n = len(opportunities)
        hits = int(outcome_hit(selected_good, threshold).sum())
        expected_hits = float((ot * kt / nt).sum())
        prevalence = opportunity_n / total_evaluable if total_evaluable else None
        precision = hits / len(selected_good) if len(selected_good) else None
        result[str(threshold)] = {
            "opportunityEvents": opportunity_n, "selectedHits": hits,
            "actualRecallPct": ratio(hits, opportunity_n, 100),
            "randomExpectedHits": number(expected_hits),
            "randomExpectedRecallPct": ratio(expected_hits, opportunity_n, 100),
            "recallLift": ratio(hits, expected_hits),
            "precisionAt5Pct": ratio(hits, len(selected_good), 100),
            "hitsOverAllSelectedLowerBoundPct": ratio(hits, len(selected), 100),
            "unconditionalScorablePrevalencePct": ratio(opportunity_n, total_evaluable, 100),
            "precisionLift": ratio(precision, prevalence) if precision is not None else None,
            "capacityMatchedRandomExpectedScorablePrecisionPct": ratio(expected_hits, expected_evaluable, 100),
            "randomExpectedEvaluableSelections": number(expected_evaluable),
        }
    return {
        "policyEligibleRows": len(policy), "scorableUniverseRows": total_evaluable,
        "decisionTimestamps": len(nt), "selectedEvents": len(selected), "scorableSelectedEvents": len(selected_good),
        "missingSelectedEvents": len(selected) - len(selected_good),
        "selectedEvaluableCoveragePct": ratio(len(selected_good), len(selected), 100),
        "noReplacementForUnscorableSelections": True, "opportunities": result,
        "futureMfePct": distribution(selected_good.futureMfePct),
        "trueMaePct": distribution(selected_good.trueMaePct),
        "medianTimeTo5Minutes": number(selected_good.loc[outcome_hit(selected_good, 5), "timeTo5Min"].median()),
        "previousCloseFinal5Secondary": {
            "precisionPct": number(100 * selected.winner.mean()),
            "recallPct": ratio(float(selected.winner.sum()), float(policy.winner.sum()), 100),
            "selectedHits": int(selected.winner.sum()), "totalEvents": int(policy.winner.sum()),
        },
    }


def time_minutes_after_open(values):
    parts = values.str.extract(r"(\d{2}):(\d{2})(?::\d{2})?")
    return pd.to_numeric(parts[0], errors="coerce") * 60 + pd.to_numeric(parts[1], errors="coerce") - 540


def daily_diagnostic(policy, selected):
    ordered = selected.sort_values(IDENTITY, kind="mergesort")
    first = ordered.drop_duplicates(["sessionDate", "symbol"], keep="first")
    good = first.loc[outcome_valid(first)]
    hits = good.loc[outcome_hit(good, 5)]
    repeats = selected.groupby(["sessionDate", "symbol"], sort=False).size()
    sessions = sorted(policy.sessionDate.unique().tolist())
    rows = []
    for session in sessions:
        pop = policy[policy.sessionDate.eq(session)]
        events = selected[selected.sessionDate.eq(session)]
        f = first[first.sessionDate.eq(session)]
        g = good[good.sessionDate.eq(session)]
        h = hits[hits.sessionDate.eq(session)]
        rows.append({
            "sessionDate": session, "decisionTimestamps": int(pop.decisionTimeJst.nunique()),
            "selectionEvents": len(events), "distinctSelectedSymbols": len(f),
            "repeatSelectionEvents": len(events) - len(f), "scorableDistinctSymbols": len(g),
            "future5DistinctHits": len(h), "future5DistinctPrecisionPct": ratio(len(h), len(g), 100),
            "future5HitsOverAllDistinctLowerBoundPct": ratio(len(h), len(f), 100),
            "medianFirstDetectionMinutesAfter0900": number(time_minutes_after_open(f.decisionTimeJst).median()),
            "medianHitFirstDetectionMinutesAfter0900": number(time_minutes_after_open(h.decisionTimeJst).median()),
            "hitAdditionalUpsideMeanPct": number(h.futureMfePct.mean()),
            "hitAdditionalUpsideMedianPct": number(h.futureMfePct.median()),
        })
    return {
        "identityRule": "FIRST_SELECTED_EVENT_PER_SESSION_SYMBOL_NO_BEST_OF_DAY",
        "sessions": len(sessions), "distinctSymbolDays": len(first), "scorableDistinctSymbolDays": len(good),
        "future5DistinctHits": len(hits), "future5DistinctPrecisionPct": ratio(len(hits), len(good), 100),
        "future5DistinctHitsPerDay": ratio(len(hits), len(sessions)),
        "medianFirstDetectionMinutesAfter0900": number(time_minutes_after_open(first.decisionTimeJst).median()),
        "medianHitFirstDetectionMinutesAfter0900": number(time_minutes_after_open(hits.decisionTimeJst).median()),
        "repeatSelectionsPerSymbolDay": distribution(repeats - 1),
        "hitAdditionalUpsidePct": distribution(hits.futureMfePct), "perSession": rows,
    }


def selection_audit(df):
    try:
        policy, selected = select_top5(df)
    except ValueError as error:
        return {"status": "UNAVAILABLE", "reason": str(error)}
    return {
        "status": "SAVED_CD_REFIT_DIAGNOSTIC_ONLY", "model": "V1_SAVED_CD_REFIT",
        "notHistoricalCOnlyV1Benchmark": True, "top5": capacity_metrics(policy, selected),
        "top5Legacy30m": {"meanBps": number(selected.y30Bps.mean()), "medianBps": number(selected.y30Bps.median()),
                          "rawMaePct": number(selected.rawMae30Pct.mean()), "trueMaePct": number(selected.trueMae30Pct.mean())},
        "dailyDistinct": daily_diagnostic(policy, selected),
        "perSession": {str(s): capacity_metrics(g, selected[selected.sessionDate.eq(s)])
                       for s, g in policy.groupby("sessionDate", sort=True)},
    }


def make_report(df, manifest, contract_sha=None):
    # Scopes and analyses are predeclared; no empirical threshold choices.
    # Store masks, not simultaneous full-width scope copies.
    scopes = {
        "FULL_SAVED_DEVELOPMENT": None,
        "AB_OUTSIDE_CD_FIT_DIAGNOSTIC": df.sourceGroup.isin(["L1", "V2"]),
        "C_IN_FIT_DIAGNOSTIC": df.sourceGroup.eq("C"),
        "D_IN_FIT_DIAGNOSTIC": df.sourceGroup.eq("D"),
    }
    result = {
        "schemaVersion": 1, "status": "NORTHSTAR_MEASUREMENT_AUDIT_COMPLETE_EVALUATOR_ONLY",
        "contractVersion": CONTRACT, "contractCommit": contract_sha or manifest.get("contractCommit"),
        "northStar": "ADDITIONAL_SAME_SESSION_FUTURE_HIGH_TOUCH_FROM_FRESH_DECISION_REFERENCE_GE5PCT",
        "modelProvenance": manifest.get("model", {}),
        "historicalModelNorthStarMetrics": {
            "C_ONLY_V1_BENCHMARK": {"status": "UNAVAILABLE", "reason": "No verified saved original C-only weights/scores; no refit authorized."},
            "V2_HIST_GRADIENT_BOOSTING": {"status": "UNAVAILABLE", "reason": "No verified saved fitted weights/scores; no refit authorized."},
        },
        "population": {"causalRows": len(df), "legacyEligibleRows": int(df.legacyEligible.eq(1).sum()),
                       "sessions": int(df.sessionDate.nunique()), "sessionDates": sorted(df.sessionDate.unique().tolist()),
                       "bySourceGroup": {str(k): {"rows": len(g), "sessions": int(g.sessionDate.nunique()),
                                                 "legacyEligibleRows": int(g.legacyEligible.eq(1).sum())}
                                         for k, g in df.groupby("sourceGroup", sort=True)}},
        "inputManifestSha256": manifest.get("_inputSha256"),
        "dataAudit": {"sessionAudits": manifest.get("sessionAudits", []),
                      "scope": "ALLOWLISTED_SAVED_DEVELOPMENT_ONLY_MISSING_SESSIONS_NOT_FETCHED_OR_REPLACED"},
        "inputFiles": [{k: f[k] for k in ["path", "sourceGroup", "partition", "rows", "sha256"] if k in f}
                       for f in manifest.get("files", [])],
        "safety": {"providerRequestsThisRun": 0, "validationOpened": False, "oosOpened": False,
                   "fitOrRefitPerformed": False, "modelWeightsChanged": False, "targetChanged": False,
                   "featureUniverseChanged": False, "topNChanged": False, "thresholdOptimization": False,
                   "entryExitAllocationChanged": False, "oldSelectorsCompared": False},
        "scopes": {},
    }
    for name, mask in scopes.items():
        group = df if mask is None else df.loc[mask]
        print(json.dumps({"stage": "aggregateScope", "scope": name, "rows": len(group)}), flush=True)
        result["scopes"][name] = {
            "measurement": measurement_audit(group), "targetAlignment": target_alignment(group),
            "legacyEligibleTargetAlignment": target_alignment(group[group.legacyEligible.eq(1)]),
            "selection": selection_audit(group),
        }
    print(json.dumps({"stage": "matchedFeatureSufficiency", "rows": len(df)}), flush=True)
    result["featureSufficiency"] = {
        "allFuture5": feature_sufficiency(df), "earlyFuture5": feature_sufficiency(df, early=True),
    }
    result["timeOfDayAlignment"] = {str(k): target_alignment(g) for k, g in df.groupby("timeOfDay", sort=True)}
    result["perSessionMeasurement"] = {
        str(s): {"sourceGroup": str(g.sourceGroup.iloc[0]), "rows": len(g),
                 "horizon": horizon_summary(g), "futureNorthStar": outcome_summary(g),
                 "freshReferencePct": ratio(int(g.referenceValid.eq(1).sum()), len(g), 100),
                 "legacySourceAgeGT5Pct": ratio(int(g.legacySourceAgeMin.gt(5).sum()), len(g), 100)}
        for s, g in df.groupby("sessionDate", sort=True)
    }
    result["limitations"] = [
        "Saved C+D refit is not the historical C-only v1 baseline and C/D are in-fit; A/B are already-observed Development, not unbiased validation.",
        "Future high touches do not imply executable fills, tradable profit, or complete missing-minute coverage.",
        "Observed-return alignment is descriptive and cannot establish prediction skill.",
        "Exact matching may discard opportunities; marginal feature overlap does not exclude interactions.",
        "Timestamp Top5 remains unchanged; daily distinct statistics do not define or optimize daily Top5.",
    ]
    core = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    result["reportSha256"] = hashlib.sha256(core.encode()).hexdigest()
    return result


def load_dataset(root):
    manifest_path = root / "dataset-manifest.json"
    payload = manifest_path.read_bytes()
    manifest = json.loads(payload)
    manifest["_inputSha256"] = hashlib.sha256(payload).hexdigest()
    if manifest.get("providerRequestsThisRun") != 0 or manifest.get("validationOpened") is not False or manifest.get("oosOpened") is not False:
        raise ValueError("Dataset provenance lacks explicit zero-request/sealed safety evidence")
    if manifest.get("featureUniverse") != FEATURES:
        raise ValueError("Feature universe/order differs from fixed saved v1 contract")
    frames = []
    for item in manifest.get("files", []):
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or path.suffix != ".tsv":
            raise ValueError("Dataset path escapes allowlisted directory or is not TSV")
        expected = item.get("sha256")
        if expected:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest() != expected:
                raise ValueError("Prepared dataset checksum mismatch")
        frame = pd.read_csv(path, sep="\t", dtype={**{k: str for k in STRINGS},
                                                  **{k: float for k in NUMERIC}})
        if "rows" in item and len(frame) != item["rows"]:
            raise ValueError("Prepared dataset row count mismatch")
        if not frame.empty and not frame.sourceGroup.eq(item["sourceGroup"]).all():
            raise ValueError("Dataset sourceGroup mismatch")
        frames.append(frame)
    if not frames:
        raise ValueError("No allowlisted datasets")
    combined = pd.concat(frames, ignore_index=True)
    frames.clear()
    del frame
    return prepare_rows(combined, copy=False), manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--contract-sha")
    args = parser.parse_args()
    frame, manifest = load_dataset(Path(args.dataset_dir))
    report = make_report(frame, manifest, args.contract_sha)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "rows": len(frame),
                      "reportSha256": report["reportSha256"], "output": str(destination)}))


if __name__ == "__main__":
    main()
