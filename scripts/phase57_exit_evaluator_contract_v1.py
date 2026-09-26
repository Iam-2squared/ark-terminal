"""R24 evaluator-only adapter and scorecard schema; never import in decisions.

This module opens only already-exposed Development evaluator records.  It does
not replay a candidate and does not calculate candidate performance.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from scripts.phase57_exit_capture_metrics_v1 import BUCKETS, OrderedGeometry, opportunity_bucket


ROOT = Path(__file__).resolve().parents[1]
OPPORTUNITIES = ROOT / "docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz"
COHORT = ROOT / "docs/evidence/phase57-entry-timing-signal-census-v1/protocol.json"
RAW_PATHS = ROOT / "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz"
SOURCE_SHA256 = "4b9afd72ccfff0b557fb4a5e067ac122ace90ae501d15a79627a89af9554a01e"
COHORT_SHA256 = "6b02b3088dd8ea7f8ce53112bc276df442bae3ce0716b8139c92733be4de2994"
RAW_PATHS_SHA256 = "37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b"
ORDERED_SCORECARD_SOURCE_SHA256 = "878aeae3f41af43fbbbde1d00d96be61a709a514ce96457a79bf89a2b0fed6b5"
HORIZON_END = 930  # inclusive knowledge cutoff; endpoint-stamped auction is known at 930
DEFINITION_ID = "CANONICAL_ORDERED_LOW_STRICTLY_LATER_HIGH_R13_SOURCE_4b9afd72_KNOWN_THROUGH_930"
EXPECTED_BUCKETS = {"<1%": 158, "1-2%": 391, "2-3%": 361,
                    "3-4%": 289, "4-5%": 188, ">=5%": 666}
EXPECTED_NOT_EVALUABLE = {
    "FULL_SESSION_OBSERVATION_INSUFFICIENT": 63,
    "NON_POSITIVE_ORDERED_RANGE": 25,
    "INSUFFICIENT_ORDERED_ROWS": 14,
}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records() -> list[dict]:
    require(sha(OPPORTUNITIES) == SOURCE_SHA256, "ORDERED_GEOMETRY_SOURCE_SHA")
    rows = json.loads(gzip.decompress(OPPORTUNITIES.read_bytes()))
    require(len(rows) == 2155 and len({r["opportunity"] for r in rows}) == 2155,
            "ORDERED_GEOMETRY_COHORT")
    return rows


def geometry(record: dict) -> tuple[OrderedGeometry | None, str | None]:
    oracle = record.get("orderedOracle", {})
    if not oracle.get("fullSessionEvaluable"):
        return None, "FULL_SESSION_OBSERVATION_INSUFFICIENT"
    if oracle.get("status") != "OBSERVED_ORDERED_ORACLE":
        return None, str(oracle.get("status") or "MISSING_ORDERED_GEOMETRY")
    low, high = oracle.get("low"), oracle.get("high")
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
               for x in (low, high)) or low <= 0 or high <= low:
        return None, "NON_POSITIVE_ORDERED_RANGE"
    low_minute, high_minute = oracle.get("lowMinute"), oracle.get("highMinute")
    if not (isinstance(low_minute, int) and isinstance(high_minute, int)
            and low_minute < high_minute):
        return None, "NON_STRICT_ORACLE_ORDER"
    expected = 100 * (high / low - 1)
    require(abs(expected - oracle["rangePct"]) < 1e-8, "RANGE_DEFINITION_MISMATCH")
    high_known_at = high_minute if high_minute == 930 else high_minute + 1
    result = OrderedGeometry(float(low), float(high), low_minute, high_minute,
                             HORIZON_END, DEFINITION_ID, "COMPLETE", high_known_at)
    result.validate()
    return result, None


def canonical_bucket_census() -> dict:
    counts = Counter()
    reasons = Counter()
    for record in records():
        value, reason = geometry(record)
        if reason:
            reasons[reason] += 1
        else:
            counts[opportunity_bucket(100 * (value.high / value.low - 1))] += 1
    require(dict(counts) == EXPECTED_BUCKETS, "CANONICAL_BUCKET_COUNT_DRIFT")
    require(dict(reasons) == EXPECTED_NOT_EVALUABLE, "CANONICAL_MISSING_COUNT_DRIFT")
    require(sum(counts.values()) + sum(reasons.values()) == 2155, "BUCKET_ACCOUNTING")
    return {
        "population": 2155,
        "evaluable": sum(counts.values()),
        "notEvaluable": sum(reasons.values()),
        "buckets": {name: counts[name] for name in BUCKETS},
        "notEvaluableReasons": dict(sorted(reasons.items())),
        "sourceSHA256": SOURCE_SHA256,
        "orderedScorecardSourceSHA256": ORDERED_SCORECARD_SOURCE_SHA256,
        "definitionId": DEFINITION_ID,
        "coverageMeaning": "LEGACY_CANONICAL_FULL_SESSION_EVALUABLE_NOT_STRICT_EVERY_1M_CERTIFICATION",
        "historicalImmediateGe5Reproduced": counts[">=5%"] == 666,
    }


def terminal_reference_census() -> dict:
    """Availability only; no policy decision or return is evaluated."""
    from scripts.phase57_exit_checkpoints_v1 import read_allowlisted_paths

    require(sha(COHORT) == COHORT_SHA256, "TERMINAL_COHORT_SHA")
    require(sha(RAW_PATHS) == RAW_PATHS_SHA256, "TERMINAL_RAW_PATH_SHA")
    allowed = set(json.loads(COHORT.read_text())["opportunityIds"])
    require(len(allowed) == 2155, "TERMINAL_COHORT_NOT_2155")
    paths = read_allowlisted_paths(RAW_PATHS, allowed)
    present = missing = single_price = 0
    for oid, path in paths.items():
        exact = [row for row in path["today"] if row[0] == 930]
        require(len(exact) <= 1, "DUPLICATE_TERMINAL_REFERENCE:" + oid)
        if not exact:
            missing += 1
            continue
        present += 1
        row = exact[0]
        require(len(row) == 7, "TERMINAL_ROW_WIDTH:" + oid)
        single_price += max(row[1:5]) == min(row[1:5])
    require((present, missing, single_price) == (2092, 63, 2092),
            "TERMINAL_REFERENCE_CENSUS_DRIFT")
    return {
        "population": 2155,
        "auctionReferencePresent": present,
        "auctionReferenceMissing": missing,
        "presentSinglePriceOHLC": single_price,
        "rawPathsSHA256": RAW_PATHS_SHA256,
        "policyPerformanceInspected": False,
    }


def scorecard_contract() -> dict:
    metrics = {
        "N": "ALL_2155_OPPORTUNITIES_ASSIGNED_BY_CANONICAL_GEOMETRY_OR_NOT_EVALUABLE",
        "evaluableN": "COMPLETE_GEOMETRY_PLUS_ENTRY_PLUS_RESOLVED_EXIT_AND_METRIC_DENOMINATOR",
        "missingN": "REQUIRED_SOURCE_OR_EXACT_EXECUTION_REFERENCE_MISSING",
        "censoredN": "HORIZON_OR_TERMINAL_UNRESOLVED_NOT_ZERO_RETURN",
        "lowToHighPct": "100*(ORDERED_HIGH-ORDERED_LOW)/ORDERED_LOW",
        "entryToSameOrderedHighPct": "R21_ENTRY_TO_SAME_ORDERED_HIGH",
        "entryToPostEntryBestHighPct": "R21_SEPARATE_POST_ENTRY_HIGH",
        "entryToExitGrossPct": "R21_REALIZED_REFERENCE_MOVE",
        "entryToExitNetPct": "GROSS_MINUS_EXPLICIT_SELL_COST_PP",
        "upmoveCapturePct": "SAME_HIGH_AND_POST_ENTRY_RATIOS_REPORTED_SEPARATELY_UNCLIPPED",
        "highToExitEvaluatorGapPp": "FUTURE_SUFFIX_MISSED_OPPORTUNITY_NEVER_OWNED_GIVEBACK",
        "ownedPeakGivebackPp": "ONLY_COMPLETE_OWNED_PATH_PEAK_KNOWN_BY_EXIT",
        "profitFactor": "SUM_POSITIVE_NET/ABS_SUM_NEGATIVE_NET_WITH_NULL_ZERO_DENOMINATOR",
        "winRate": "NET_RETURN_GT_ZERO_OVER_RESOLVED_ENTRY_EXIT",
        "averageWinLoss": "MEAN_POSITIVE_AND_MEAN_NEGATIVE_REPORTED_SEPARATELY",
        "p05P10Worst": "NET_RETURN_EMPIRICAL_QUANTILES_AND_MINIMUM",
        "holdingTime": "ACTIVE_AND_WALL_MINUTES_BOTH_MEAN_MEDIAN",
        "earlyExitOpportunityCost": "MAX(0,POST_EXIT_EVALUATOR_HIGH-EXIT)/ENTRY;_MISSED_OPPORTUNITY",
        "lateExitGiveback": "OWNED_PEAK_GIVEBACK_ONLY;_NO_AFTER_EXIT_HIGH",
    }
    return {
        "schemaVersion": "phase57-exit-full-scorecard-r24",
        "entryArms": ["IMMEDIATE", "ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF"],
        "opportunityBuckets": list(BUCKETS),
        "notEvaluableBucket": True,
        "summaryStatistics": ["N", "evaluableN", "missingN", "censoredN",
                              "mean", "median", "p05", "p10", "worst"],
        "metrics": metrics,
        "metricDenominators": "EVERY_METRIC_CARRIES_OWN_ELIGIBLE_N_NO_COMPLETE_CASE_DENOMINATOR_REUSE",
        "pairedCommonCase": {
            "identity": "SAME_OPPORTUNITY_ID_SAME_GEOMETRY_DEFINITION_AND_HORIZON",
            "eligibility": "BOTH_ARMS_HAVE_ENTRY_RESOLVED_EXIT_AND_THE_SPECIFIC_METRIC",
            "report": "PAIR_N_AND_WITHIN_PAIR_R1_MINUS_IMMEDIATE_DELTA_MEAN_MEDIAN",
            "unpairedRowsNeverCalledPaired": True,
        },
        "capabilities": {
            "WinnerContinuation": [">=5%_CAPTURE", ">=5%_EARLY_EXIT_OPPORTUNITY_COST",
                                   ">=5%_HOLDING_TIME"],
            "ProfitRetention": ["OWNED_PEAK_GIVEBACK", "POSITIVE_TRADE_RETENTION"],
            "LossContainment": ["P05", "P10", "WORST", "AVERAGE_LOSS"],
        },
        "aggregateRules": {
            "meanOfPerTradeRatios": True,
            "ratioOfAggregateMovesAlsoLabeledSeparately": True,
            "negativeAndOver100CaptureNotClipped": True,
            "winRateAloneCannotSelect": True,
        },
        "canonicalCensus": canonical_bucket_census(),
        "terminalReferenceCensus": terminal_reference_census(),
        "evaluatorOnly": True,
        "candidatePerformanceCalculated": False,
    }


if __name__ == "__main__":
    print(json.dumps(scorecard_contract(), sort_keys=True, separators=(",", ":")))
