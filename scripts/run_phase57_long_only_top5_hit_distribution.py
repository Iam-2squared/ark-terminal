#!/usr/bin/env python3
"""Aggregate Top5 hit-distribution diagnostic. Never fits or changes a selector."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

import run_phase57_long_only_corrected_measurement as base
import run_phase57_long_only_eligibility_measurement as eligibility

CONTRACT = "ELIGIBILITY-TOP5-HIT-DISTRIBUTION-1"
PARENT_CONTRACT = "ELIGIBILITY-MEASUREMENT-1"
MODEL = "ELIGIBILITY_AWARE_RIDGE_SAVED_CD"
THRESHOLDS = [1, 2, 3, 5]
TIME_GROUPS = {
    "MORNING": ["09:30", "10:00"],
    "LATE_MORNING": ["10:30", "11:00", "11:30"],
    "AFTERNOON": ["13:00", "13:30", "14:00", "14:30", "15:00"],
}


def prepare_evaluator_additions(frame):
    frame = frame.copy()
    columns = [f"{prefix}{level}{suffix}" for prefix, suffix in [
        ("highOpportunity", ""), ("closeOpportunity", ""), ("auctionCloseOpportunity", ""),
        ("timeToHigh", "Min"), ("timeToClose", "Min")]
        for level in THRESHOLDS]
    for column in columns:
        if column not in frame:
            raise ValueError(f"missing evaluator column {column}")
        frame[column] = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    valid = frame.decisionPriceValid.eq(1)
    for level in THRESHOLDS:
        for prefix in ["highOpportunity", "closeOpportunity", "auctionCloseOpportunity"]:
            if not frame.loc[valid, f"{prefix}{level}"].isin([0, 1]).all():
                raise ValueError(f"invalid evaluator flag {prefix}{level}")
    for prefix in ["highOpportunity", "closeOpportunity"]:
        hit_counts = [int(frame.loc[base.evaluator_valid(frame, prefix), f"{prefix}{level}"].eq(1).sum()) for level in THRESHOLDS]
        if hit_counts != sorted(hit_counts, reverse=True):
            raise ValueError(f"non-monotone opportunity thresholds for {prefix}")
    return frame


def hit_distribution(selected, prefix, level):
    flag = f"{prefix}{level}"
    valid = base.evaluator_valid(selected, prefix)
    work = selected[base.KEYS].copy()
    work["hit"] = (valid & selected[flag].eq(1)).astype(int)
    work["valid"] = valid.astype(int)
    grouped = work.groupby(base.KEYS, sort=True).agg(hits=("hit", "sum"), valid=("valid", "sum"))
    if grouped.empty:
        raise ValueError("no decision timestamps")
    if grouped.shape[0] != selected[base.KEYS].drop_duplicates().shape[0]:
        raise ValueError("decision timestamp loss")
    counts = grouped.hits.value_counts().reindex(range(6), fill_value=0).sort_index()
    decisions = len(grouped)
    return {
        "decisions": decisions,
        "distribution": {
            str(hit): {"decisionCount": int(counts.loc[hit]), "pct": base.ratio(int(counts.loc[hit]), decisions, 100)}
            for hit in range(6)
        },
        "meanHitsPerTop5": base.number(grouped.hits.mean()),
        "medianHitsPerTop5": base.number(grouped.hits.median()),
        "probabilityPct": {
            "GE1": base.ratio(int(grouped.hits.ge(1).sum()), decisions, 100),
            "GE2": base.ratio(int(grouped.hits.ge(2).sum()), decisions, 100),
            "GE3": base.ratio(int(grouped.hits.ge(3).sum()), decisions, 100),
            "GE4": base.ratio(int(grouped.hits.ge(4).sum()), decisions, 100),
            "EQ5": base.ratio(int(grouped.hits.eq(5).sum()), decisions, 100),
        },
        "evaluatorCoverage": {
            "selectedEvents": len(selected),
            "evaluableEvents": int(valid.sum()),
            "coveragePct": base.ratio(int(valid.sum()), len(selected), 100),
            "decisionsWithAnyUnavailable": int(grouped.valid.lt(5).sum()),
        },
    }


def curve(universe, selected, prefix):
    return {
        str(level): {
            "metrics": base.opportunity_metrics(universe, selected, prefix, level),
            "perDecisionTop5": hit_distribution(selected, prefix, level),
        }
        for level in THRESHOLDS
    }


def time_to_hit(selected, prefix, level):
    valid = base.evaluator_valid(selected, prefix)
    hits = valid & selected[f"{prefix}{level}"].eq(1)
    time_prefix = "timeToHigh" if prefix == "highOpportunity" else "timeToClose"
    return base.time_distribution(selected.loc[hits, f"{time_prefix}{level}Min"])


def time_group_diagnostics(universe, selected):
    output = {}
    for name, decision_times in TIME_GROUPS.items():
        u = universe[universe.decisionTimeJst.isin(decision_times)]
        s = selected[selected.decisionTimeJst.isin(decision_times)]
        observed = sorted(u.decisionTimeJst.unique().tolist())
        if observed != decision_times:
            raise ValueError(f"unexpected decision-time coverage for {name}: {observed}")
        output[name] = {
            "decisionTimes": decision_times,
            "decisionCount": int(u[base.KEYS].drop_duplicates().shape[0]),
            "selectedEvents": len(s),
            "highTouch": {},
            "closeConfirmed": {},
        }
        for kind, prefix in [("highTouch", "highOpportunity"), ("closeConfirmed", "closeOpportunity")]:
            for level in THRESHOLDS:
                metric = base.opportunity_metrics(u, s, prefix, level)
                distribution = hit_distribution(s, prefix, level)
                output[name][kind][str(level)] = {
                    "precisionAt5Pct": metric["precisionAt5Pct"],
                    "meanHitsPerTop5": distribution["meanHitsPerTop5"],
                    "probabilityAtLeastOnePct": distribution["probabilityPct"]["GE1"],
                }
    return output


def segment_diagnostics(selected):
    output = {}
    for field, values in [
        ("market", ["PRIME", "STANDARD", "GROWTH"]),
        ("liquidity", ["LOW", "MID", "HIGH"]),
    ]:
        column = "segment" if field == "market" else "liquidityBucket"
        output[field] = {}
        for value in values:
            group = selected[selected[column].eq(value)]
            valid = base.evaluator_valid(group, "highOpportunity")
            output[field][value] = {
                "selectedN": len(group),
                "highEvaluableN": int(valid.sum()),
                "highCoveragePct": base.ratio(int(valid.sum()), len(group), 100),
                "highPrecisionPct": {
                    str(level): base.ratio(int((valid & group[f"highOpportunity{level}"].eq(1)).sum()), int(valid.sum()), 100)
                    for level in THRESHOLDS
                },
            }
    return output


def make_report(frame, manifest, contract_sha):
    frame = prepare_evaluator_additions(frame)
    universe, selected = eligibility.select_top5_after_eligibility(frame)
    decision_count = int(universe[base.KEYS].drop_duplicates().shape[0])
    selected_per_decision = selected.groupby(base.KEYS, sort=True).size()
    if not selected_per_decision.eq(5).all():
        raise ValueError("fixed Top5 capacity was not preserved")
    if decision_count != len(selected_per_decision):
        raise ValueError("eligible decision timestamps missing selections")
    report = {
        "schemaVersion": 1,
        "status": "TOP5_HIT_DISTRIBUTION_COMPLETE",
        "contract": CONTRACT,
        "contractCommit": contract_sha,
        "parentContract": PARENT_CONTRACT,
        "model": {**manifest["model"], "name": MODEL},
        "inputManifestSha256": manifest["_sha256"],
        "dataAudit": {
            "availableSessions": int(frame.sessionDate.nunique()),
            "populationRows": len(frame),
            "eligibleRows": len(universe),
            "decisionCount": decision_count,
            "top5SelectionEvents": len(selected),
            "selectedPerDecision": base.distribution(selected_per_decision),
            "repeatSymbolsAcrossDecisionsAllowed": True,
        },
        "semantics": {
            "eligibility": "LATEST_CAUSALLY_AVAILABLE_PRICE_AGE_LE_5_WALL_CLOCK_MINUTES",
            "selection": "ELIGIBILITY_THEN_SAVED_RIDGE_SCORE_DESC_SYMBOL_ASC_TOP5",
            "primary": "DECISION_PRICE_TO_SAME_SESSION_FUTURE_CONTINUOUS_5M_HIGH",
            "secondary": "DECISION_PRICE_TO_FUTURE_5M_OR_TERMINAL_AUCTION_CLOSE",
            "thresholdPct": THRESHOLDS,
            "timeGroups": TIME_GROUPS,
        },
        "highTouch": curve(universe, selected, "highOpportunity"),
        "closeConfirmed": curve(universe, selected, "closeOpportunity"),
        "timeToHit": {
            "highTouch": {str(level): time_to_hit(selected, "highOpportunity", level) for level in THRESHOLDS},
            "closeConfirmed": {str(level): time_to_hit(selected, "closeOpportunity", level) for level in THRESHOLDS},
        },
        "timeOfDay": time_group_diagnostics(universe, selected),
        "segments": segment_diagnostics(selected),
        "safety": {
            "providerRequests": 0,
            "fitCalls": 0,
            "validationOpened": False,
            "oosOpened": False,
            "modelChanged": False,
            "featureChanged": False,
            "targetChanged": False,
            "topNChanged": False,
            "eligibilityChanged": False,
            "thresholdOptimized": False,
            "tradingEnabled": False,
        },
        "limitations": [
            "Saved C+D Ridge is not the unavailable original C-only v1 model.",
            "High touch is evaluator evidence, not executable fill evidence.",
            "Ten selected events lack a continuous future 5m High path and remain selected as non-hits in per-decision lower-bound distributions.",
            "Development evidence cannot establish sealed Validation/OOS performance.",
        ],
        "stopBoundary": "REPORT_FREEZE_READINESS_THEN_STOP_NO_FORMAL_FREEZE",
    }
    core = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["reportSha256"] = hashlib.sha256(core.encode()).hexdigest()
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--contract-sha", required=True)
    args = parser.parse_args()
    frame, manifest = base.load(Path(args.dataset_dir))
    report = make_report(frame, manifest, args.contract_sha)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "status": report["status"],
        "decisions": report["dataAudit"]["decisionCount"],
        "selected": report["dataAudit"]["top5SelectionEvents"],
        "reportSha256": report["reportSha256"],
        "output": str(output),
    }))


if __name__ == "__main__":
    main()
