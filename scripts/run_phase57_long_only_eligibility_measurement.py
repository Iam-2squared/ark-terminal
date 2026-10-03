#!/usr/bin/env python3
"""ELIGIBILITY-MEASUREMENT-1 aggregate evaluator. Never fits a model."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

import run_phase57_long_only_corrected_measurement as base

CONTRACT = "ELIGIBILITY-MEASUREMENT-1"
PARENT_CONTRACT = "CORRECTED-MEASUREMENT-1"
MODEL = "ELIGIBILITY_AWARE_RIDGE_SAVED_CD"
PREVIOUS_RUN = 34985364169
PREVIOUS = {
    "selectionSemantics": "FULL_UNIVERSE_RANK_THEN_POST_RANKING_FRESHNESS_EVALUATION",
    "future3HighPrecisionPct": 53.3882441033,
    "future5HighPrecisionPct": 30.4754773493,
    "top5FreshCoveragePct": 70.5,
    "top5Corrected30CoveragePct": 50.4210526316,
    "directPerformanceComparisonIsCausalLikeForLike": False,
}


def snapshot(frame):
    return {
        "rows": len(frame),
        "market": base.mix(frame, "segment"),
        "liquidity": base.mix(frame, "liquidityBucket"),
        "currentReturnPct": base.distribution(frame.currentReturnPct),
        "decisionVolatilityPct": base.distribution(frame.decisionVolatilityPct),
    }


def eligible_universe(frame):
    valid = (
        frame.decisionPriceValid.eq(1)
        & frame.referenceAgeMin.ge(0)
        & frame.referenceAgeMin.le(5)
        & frame.decisionPrice.gt(0)
        & frame.decisionPrice.notna()
    )
    if not valid.equals(frame.decisionPriceValid.eq(1)):
        raise ValueError("prepared causal freshness flag disagrees with frozen eligibility rule")
    return frame[valid].copy()


def select_top5_after_eligibility(frame):
    eligible = eligible_universe(frame)
    return eligible, base.select_top5(eligible)


def selected_identity(frame):
    return set(map(tuple, frame[base.IDENTITY].astype(str).to_numpy()))


def evaluation_coverage(universe, selected):
    def one(frame):
        high = frame.futureBarCount.gt(0)
        close = frame.futureBarCount.add(frame.futureAuctionCount).gt(0)
        c30 = frame.corrected30Evaluable.eq(1)
        return {
            "rows": len(frame),
            "freshDecisionPriceRows": int(frame.decisionPriceValid.eq(1).sum()),
            "sessionHighEvaluableRows": int(high.sum()),
            "sessionHighCoveragePct": base.ratio(int(high.sum()), len(frame), 100),
            "sessionCloseEvaluableRows": int(close.sum()),
            "sessionCloseCoveragePct": base.ratio(int(close.sum()), len(frame), 100),
            "strict30EvaluableRows": int(c30.sum()),
            "strict30CoveragePct": base.ratio(int(c30.sum()), len(frame), 100),
            "unavailableReasons": {
                "NO_FUTURE_CONTINUOUS_5M_FOR_HIGH": int((~high).sum()),
                "NO_FUTURE_5M_OR_AUCTION_CLOSE": int((~close).sum()),
                "NO_STRICT_WALL_CLOCK_30M_ENDPOINT": int((~c30).sum()),
            },
        }
    return {"eligibleUniverse": one(universe), "selectedTop5": one(selected)}


def opportunity_set(universe, selected):
    output = {}
    for kind, prefix in [("highTouch", "highOpportunity"), ("closeConfirmed", "closeOpportunity")]:
        output[kind] = {
            str(level): base.opportunity_metrics(universe, selected, prefix, level)
            for level in [2, 3, 5]
        }
    return output


def selected_metrics(universe, selected):
    c30 = selected[selected.corrected30Evaluable.eq(1)]
    session_means = c30.groupby("sessionDate").corrected30ReturnBps.mean()
    high_valid = selected[selected.futureBarCount.gt(0)]
    close_valid = selected[selected.futureBarCount.add(selected.futureAuctionCount).gt(0)]
    return {
        "model": MODEL,
        "selectedEvents": len(selected),
        "decisionTimestamps": int(universe[base.KEYS].drop_duplicates().shape[0]),
        "selectedPerTimestamp": base.distribution(selected.groupby(base.KEYS).size()),
        "corrected30ReturnBps": base.distribution(c30.corrected30ReturnBps),
        "corrected30PositiveRatePct": base.ratio(int(c30.corrected30ReturnBps.gt(0).sum()), len(c30), 100),
        "positiveSessions": int(session_means.gt(0).sum()),
        "sessionsWith30m": len(session_means),
        "mfe30Pct": base.distribution(c30.mfe30Pct),
        "mae30Pct": base.distribution(c30.mae30Pct),
        "sessionMfePct": base.distribution(high_valid.sessionMfePct),
        "sessionMaePct": base.distribution(high_valid.sessionMaePct),
        "opportunities": opportunity_set(universe, selected),
        "timeToHigh3": base.time_distribution(high_valid.loc[high_valid.highOpportunity3.eq(1), "timeToHigh3Min"]),
        "timeToHigh5": base.time_distribution(high_valid.loc[high_valid.highOpportunity5.eq(1), "timeToHigh5Min"]),
        "timeToClose3": base.time_distribution(close_valid.loc[close_valid.closeOpportunity3.eq(1), "timeToClose3Min"]),
        "timeToClose5": base.time_distribution(close_valid.loc[close_valid.closeOpportunity5.eq(1), "timeToClose5Min"]),
        "finalPrevious5ReferencePrecisionPct": base.ratio(int(selected.finalPrevious5.eq(1).sum()), len(selected), 100),
    }


def segment_row(eligible, selected):
    high_valid = selected[selected.futureBarCount.gt(0)]
    c30 = selected[selected.corrected30Evaluable.eq(1)]
    return {
        "eligibleN": len(eligible),
        "selectedN": len(selected),
        "sessionHighEvaluableN": len(high_valid),
        "future3HighPrecisionPct": base.ratio(int(high_valid.highOpportunity3.eq(1).sum()), len(high_valid), 100),
        "future5HighPrecisionPct": base.ratio(int(high_valid.highOpportunity5.eq(1).sum()), len(high_valid), 100),
        "strict30EvaluableN": len(c30),
        "strict30MeanBps": base.number(c30.corrected30ReturnBps.mean()),
        "strict30MedianBps": base.number(c30.corrected30ReturnBps.median()),
        "strict30PositiveRatePct": base.ratio(int(c30.corrected30ReturnBps.gt(0).sum()), len(c30), 100),
        "mfe30Pct": base.number(c30.mfe30Pct.mean()),
        "trueMae30Pct": base.number(c30.mae30Pct.mean()),
        "sessionMfePct": base.number(high_valid.sessionMfePct.mean()),
        "sessionTrueMaePct": base.number(high_valid.sessionMaePct.mean()),
    }


def segment_diagnostics(eligible, selected):
    output = {}
    for field, values in [
        ("segment", ["PRIME", "STANDARD", "GROWTH"]),
        ("liquidityBucket", ["LOW", "MID", "HIGH"]),
    ]:
        output[field] = {
            value: segment_row(eligible[eligible[field].eq(value)], selected[selected[field].eq(value)])
            for value in values
        }
    return output


def scope_report(frame):
    eligible, selected = select_top5_after_eligibility(frame)
    previous_selected = base.select_top5(frame)
    overlap = len(selected_identity(selected) & selected_identity(previous_selected))
    counts = eligible.groupby(base.KEYS, sort=False).size()
    return {
        "populationRows": len(frame),
        "sessions": int(frame.sessionDate.nunique()),
        "eligibility": {
            "rule": "LATEST_CAUSALLY_AVAILABLE_PRICE_AGE_LE_5_WALL_CLOCK_MINUTES",
            "preEligibilityRows": len(frame),
            "eligibleRows": len(eligible),
            "ineligibleRows": len(frame) - len(eligible),
            "eligibleCoveragePct": base.ratio(len(eligible), len(frame), 100),
            "candidateCountPerTimestamp": base.distribution(counts),
            "pre": snapshot(frame),
            "post": snapshot(eligible),
            "selected": snapshot(selected),
        },
        "evaluationCoverage": evaluation_coverage(eligible, selected),
        "ridgeTop5": selected_metrics(eligible, selected),
        "segmentDiagnostics": segment_diagnostics(eligible, selected),
        "selectionChangeVsPostRankingFreshnessRun": {
            "previousSelectedEvents": len(previous_selected),
            "eligibilityAwareSelectedEvents": len(selected),
            "overlapEvents": overlap,
            "changedEvents": len(selected) - overlap,
            "previousRun": PREVIOUS_RUN,
            "previousMetrics": PREVIOUS,
        },
    }


def make_report(frame, manifest, contract_sha=None):
    scopes = {
        "FULL_SAVED_DEVELOPMENT": frame,
        "AB_OUTSIDE_CD_FIT_DIAGNOSTIC": frame[frame.sourceGroup.isin(["L1", "V2"])],
        "C_IN_FIT_DIAGNOSTIC": frame[frame.sourceGroup.eq("C")],
        "D_IN_FIT_DIAGNOSTIC": frame[frame.sourceGroup.eq("D")],
    }
    result = {
        "schemaVersion": 1,
        "status": "ELIGIBILITY_AWARE_MEASUREMENT_COMPLETE",
        "contract": CONTRACT,
        "contractCommit": contract_sha,
        "parentMeasurementContract": PARENT_CONTRACT,
        "northStar": "DECISION_PRICE_TO_SAME_SESSION_FUTURE_5M_HIGH_GE3_PRIMARY_GE5_STRETCH",
        "modelProvenance": {**copy.deepcopy(manifest["model"]), "name": MODEL},
        "inputManifestSha256": manifest["_sha256"],
        "inputFiles": manifest["files"],
        "dataAudit": {"sessionAudits": manifest["sessionAudits"], "availableSessions": int(frame.sessionDate.nunique())},
        "safety": {
            "providerRequests": 0,
            "fitCalls": 0,
            "validationOpened": False,
            "oosOpened": False,
            "v2Retested": False,
            "newModel": False,
            "newFeature": False,
            "newTarget": False,
            "topNOptimized": False,
            "freshnessThresholdTuned": False,
            "tradingEnabled": False,
        },
        "semantics": {
            "eligibilityOrder": "CAUSAL_FRESHNESS_THEN_RIDGE_RANK_THEN_TOP5",
            "freshness": "latest accepted market price available <= t, age <=5 wall-clock minutes",
            "primary30m": "strict wall-clock t+30 endpoint",
            "primaryOpportunity": "future continuous 5m High touch",
            "secondaryOpportunity": "future 5m Close or terminal auction Close",
            "mfe": "max(0,max future high / decision price - 1)",
            "mae": "min(0,min future low / decision price - 1)",
        },
        "scopes": {name: scope_report(group) for name, group in scopes.items()},
        "limitations": [
            "Saved C+D Ridge is not original C-only v1; C/D are in-fit and A/B are earlier observed Development.",
            "Five-minute freshness is a causal data-quality/tradability condition but materially changes market and liquidity composition.",
            "High touch is an evaluator event, not executable fill evidence.",
            "Future-path availability cannot be used as a causal ranking eligibility condition; any absence is reported after selection.",
        ],
        "stopBoundary": "REPORT_FREEZE_CANDIDATE_VERDICT_THEN_STOP",
    }
    core = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    result["reportSha256"] = hashlib.sha256(core.encode()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--contract-sha", required=True)
    args = parser.parse_args()
    frame, manifest = base.load(Path(args.dataset_dir))
    if manifest.get("contractId") != PARENT_CONTRACT:
        raise ValueError("unexpected parent measurement dataset")
    report = make_report(frame, manifest, args.contract_sha)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "rows": len(frame), "reportSha256": report["reportSha256"], "output": str(output)}))


if __name__ == "__main__":
    main()
