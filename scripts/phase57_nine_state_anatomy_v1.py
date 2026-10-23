"""Evaluator-only anatomy census for the frozen Phase57 nine-State Entry study.

This diagnostic does not make decisions and does not alter the frozen classifier,
Signals or Entry policies.  It groups the already exposed Development population
by the original State-v3 T0 label, then compares existing immutable policies with
existing evaluator-only Oracle/label fields.  Future Low/High, Capture and MFE/MAE
remain evaluation outputs only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

from scripts import phase57_state_conditioned_signal_entry_v1 as metrics

PATTERNS = (
    "REBOUND", "RISE", "SHARP_RISE", "DROP", "PULLBACK",
    "RANGE", "SHARP_DROP", "DROP_STOP", "RISE_STOP",
)
THRESHOLDS = (0.10, 0.15, 0.25, 0.50)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path: Path):
    return metrics.read_json(path)


def finite(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def manifest_assert(root: Path, name: str) -> str:
    manifest = read(root / "manifest.json")
    path = root / name
    expected = manifest[name]
    actual = sha256(path)
    assert actual == expected, (root, name, actual, expected)
    return actual


def stat_compact(value):
    if not isinstance(value, dict):
        return None
    return {
        key: value.get(key)
        for key in ("count", "mean", "median", "p25", "p5", "p75", "p90", "p95")
        if key in value
    }


def threshold_summary(rows):
    values = []
    for row in rows:
        quality = row.get("quality") or {}
        value = quality.get("entryPosition")
        if finite(value):
            values.append(float(value))
    result = {
        "validN": len(values),
        "mean": statistics.fmean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "thresholds": {},
    }
    for threshold in THRESHOLDS:
        count = sum(value <= threshold for value in values)
        result["thresholds"][f"le{int(threshold * 100):02d}pct"] = {
            "count": count,
            "denominator": len(values),
            "ratePct": (100.0 * count / len(values)) if values else None,
        }
    return result


def capture_at(summary, level):
    capture = summary.get("capture", {})
    item = capture.get(level, capture.get(str(level), {}))
    return {
        key: item.get(key)
        for key in (
            "captured", "missed", "noEntry", "belowThreshold",
            "selectorWinnerDenominator", "ratePct",
        )
        if key in item
    }


def horizon_compact(summary, horizon):
    block = summary.get("horizons", {}).get(str(horizon), summary.get("horizons", {}).get(horizon, {}))
    return {
        "MFE": stat_compact(block.get("MFE", {})),
        "MAE": stat_compact(block.get("MAE", {})),
        "returnNet": stat_compact(block.get("returnNet", {})),
        "coverage": block.get("coverage", {}),
    }


def policy_compact(opportunities, rows):
    summary = metrics.policy_summary(opportunities, rows)
    return {
        "population": summary.get("population"),
        "fills": summary.get("fills"),
        "noEntry": summary.get("noEntry"),
        "fillRatePct": summary.get("fillRatePct"),
        "oracleEvaluable": summary.get("oracleEvaluable"),
        "laterHighEvaluable": summary.get("laterHighEvaluable"),
        "delay": stat_compact(summary.get("delay", {})),
        "entryPosition": stat_compact(summary.get("entryPosition", {})),
        "entryPositionGoal": threshold_summary(rows),
        "lowToEntryDistancePct": stat_compact(summary.get("lowToEntryDistancePct", {})),
        "lowToEntryPrice": stat_compact(summary.get("lowToEntryPrice", {})),
        "entryToLaterHighRemainingUpsidePct": stat_compact(
            summary.get("entryToLaterHighRemainingUpsidePct", {})
        ),
        "capture3": capture_at(summary, 3),
        "capture5": capture_at(summary, 5),
        "horizon30": horizon_compact(summary, 30),
        "horizon60": horizon_compact(summary, 60),
        "unfilledReason": summary.get("unfilledReason", {}),
    }, summary


def paired_compact(base_rows, candidate_rows, base_summary, candidate_summary):
    paired, _ = metrics.paired_summary(base_rows, candidate_rows, base_summary, candidate_summary)
    return {
        "population": paired.get("population"),
        "pairStatus": paired.get("pairStatus", {}),
        "fillRateDeltaPp": paired.get("fillRateDeltaPp"),
        "fillDelta": paired.get("fillDelta"),
        "entryPositionDelta": stat_compact(paired.get("entryPositionDelta", {})),
        "lowToEntryDistanceDeltaPct": stat_compact(paired.get("lowToEntryDistanceDeltaPct", {})),
        "priceImprovementPct": stat_compact(paired.get("priceImprovementPct", {})),
        "delayDelta": stat_compact(paired.get("delayDelta", {})),
        "remainingUpsideDeltaPct": stat_compact(paired.get("remainingUpsideDeltaPct", {})),
        "MFE30DeltaPp": stat_compact(paired.get("MFE30DeltaPp", {})),
        "MAE30DeltaPp": stat_compact(paired.get("MAE30DeltaPp", {})),
        "MFE60DeltaPp": stat_compact(paired.get("MFE60DeltaPp", {})),
        "MAE60DeltaPp": stat_compact(paired.get("MAE60DeltaPp", {})),
        "captureDeltaPp": paired.get("captureDeltaPp", {}),
        "sessionEqualPriceBootstrap": paired.get("sessionEqualPriceBootstrap"),
    }


def indexed(rows):
    out = {row["opportunity"]: row for row in rows}
    assert len(out) == len(rows)
    return out


def run(args):
    state_root = Path(args.state_v3_measurement)
    entry_root = Path(args.entry_v1_measurement)
    timing_root = Path(args.entry_timing_measurement)
    one_min_root = Path(args.one_minute_root)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)

    hashes = {
        "stateV3EntryRecords": manifest_assert(state_root, "entry-records.json.gz"),
        "immediateRecords": manifest_assert(entry_root, "baseline-immediate-records.json.gz"),
        "entryV1Records": manifest_assert(entry_root, "entry-records.json.gz"),
        "opportunityRecords": manifest_assert(timing_root, "opportunity-records.json.gz"),
        "oneMinuteEntryRecords": manifest_assert(one_min_root, "entry-records.json.gz"),
    }

    opportunities = read(timing_root / "opportunity-records.json.gz")
    state_v3 = read(state_root / "entry-records.json.gz")
    immediate = read(entry_root / "baseline-immediate-records.json.gz")
    entry_v1 = read(entry_root / "entry-records.json.gz")
    one_minute = read(one_min_root / "entry-records.json.gz")

    assert len(opportunities) == len(state_v3) == len(immediate) == len(entry_v1) == len(one_minute) == 2155
    opp_ids = [row["opportunity"] for row in opportunities]
    assert len(set(opp_ids)) == 2155
    state_by = indexed(state_v3)
    policies_by = {
        "IMMEDIATE": indexed(immediate),
        "ENTRY_V1": indexed(entry_v1),
        "STATE_V3": state_by,
        "ONE_MINUTE": indexed(one_minute),
    }
    for mapping in policies_by.values():
        assert set(mapping) == set(opp_ids)

    t0_counts = {state: sum(state_by[oid].get("initialState") == state for oid in opp_ids) for state in PATTERNS}
    assert sum(t0_counts.values()) == 2155

    cohorts = list(PATTERNS) + ["ALL"]
    result = {
        "artifactKind": "phase57_nine_state_evaluator_anatomy_v1",
        "developmentOnly": True,
        "population": 2155,
        "t0StateCounts": t0_counts,
        "entryPositionCompletionTarget": {
            "aspirationalMeanLt": 0.15,
            "requiredReportedThresholds": [0.10, 0.15, 0.25, 0.50],
            "futureOracleDecisionUse": 0,
            "note": "Evaluator-only completion evidence; not a decision threshold or tuning loop.",
        },
        "inputHashes": hashes,
        "states": {},
        "providerRequests": 0,
        "protectedDataOpened": 0,
    }

    for state in cohorts:
        ids = opp_ids if state == "ALL" else [oid for oid in opp_ids if state_by[oid].get("initialState") == state]
        opp = [row for row in opportunities if row["opportunity"] in set(ids)]
        policy_rows = {
            name: [mapping[oid] for oid in ids]
            for name, mapping in policies_by.items()
        }
        summaries = {}
        compact = {}
        for name, rows in policy_rows.items():
            compact[name], summaries[name] = policy_compact(opp, rows)
        pairs = {
            "STATE_V3_MINUS_IMMEDIATE": paired_compact(
                policy_rows["IMMEDIATE"], policy_rows["STATE_V3"],
                summaries["IMMEDIATE"], summaries["STATE_V3"],
            ),
            "STATE_V3_MINUS_ENTRY_V1": paired_compact(
                policy_rows["ENTRY_V1"], policy_rows["STATE_V3"],
                summaries["ENTRY_V1"], summaries["STATE_V3"],
            ),
            "ONE_MINUTE_MINUS_STATE_V3": paired_compact(
                policy_rows["STATE_V3"], policy_rows["ONE_MINUTE"],
                summaries["STATE_V3"], summaries["ONE_MINUTE"],
            ),
        }
        result["states"][state] = {
            "population": len(ids),
            "policies": compact,
            "paired": pairs,
        }

    (output / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    manifest = {"summary.json": sha256(output / "summary.json")}
    (output / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    for state in cohorts:
        block = result["states"][state]
        sv3 = block["policies"]["STATE_V3"]
        one = block["policies"]["ONE_MINUTE"]
        goal = sv3["entryPositionGoal"]
        print(json.dumps({
            "state": state,
            "N": block["population"],
            "stateV3FillRatePct": sv3["fillRatePct"],
            "stateV3EntryPositionMean": goal["mean"],
            "stateV3EntryPositionMedian": goal["median"],
            "stateV3Le15PctRate": goal["thresholds"]["le15pct"]["ratePct"],
            "stateV3Le25PctRate": goal["thresholds"]["le25pct"]["ratePct"],
            "stateV3Capture3Pct": sv3["capture3"].get("ratePct"),
            "stateV3Capture5Pct": sv3["capture5"].get("ratePct"),
            "oneMinuteEntryPositionMean": one["entryPositionGoal"]["mean"],
            "oneMinuteFillRatePct": one["fillRatePct"],
        }, sort_keys=True, allow_nan=False))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-v3-measurement", required=True)
    parser.add_argument("--entry-v1-measurement", required=True)
    parser.add_argument("--entry-timing-measurement", required=True)
    parser.add_argument("--one-minute-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
