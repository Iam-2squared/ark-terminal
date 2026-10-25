"""Phase57 Entry UNKNOWN causal-coverage diagnostic.

Diagnostic only. This program does not create or modify an Entry policy. Causal
state trajectories are computed first from the frozen minute census. Evaluator-
only paired metrics are opened only after the fixed initial-UNKNOWN cohort and
all causal trajectories have been constructed.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path

from scripts.phase57_state_conditioned_signal_entry_v1 import (
    STATES,
    distribution,
    estimate_state,
    read_json,
    sha256,
    write_gzip_json,
    write_json,
)

OFFSETS = (1, 2, 3, 5, 10)
PAIR_METRICS = (
    "priceImprovementPct",
    "delayDelta",
    "lowToEntryDistanceDeltaPct",
    "remainingUpsideDeltaPct",
    "entryPositionDelta",
    "rangeRetentionDeltaPp",
    "MFE30DeltaPp",
    "MAE30DeltaPp",
    "MFE60DeltaPp",
    "MAE60DeltaPp",
)
EXPECTED_POPULATION = 2155
EXPECTED_INITIAL_UNKNOWN = 1144


def phase_start(minute: int) -> int:
    """Match the frozen signal detector half-session boundary semantics."""
    return 540 if minute <= 690 else 750


def phase_age_bucket(minute: int) -> str:
    age = minute - phase_start(minute)
    if age <= 5:
        return "PHASE_AGE_0_5"
    if age <= 10:
        return "PHASE_AGE_6_10"
    if age <= 30:
        return "PHASE_AGE_11_30"
    if age <= 60:
        return "PHASE_AGE_31_60"
    return "PHASE_AGE_61_PLUS"


def unknown_reason(row: dict) -> str:
    """Classify why the frozen 5-minute-return estimator is UNKNOWN.

    The estimator requires six contiguous closed one-minute bars to form the
    5-minute close-to-close return. No outcome, oracle, reference State-v2, or
    future field is inspected here.
    """
    value = row["context"]["returnPct"]["5"]
    if value is not None:
        raise ValueError("ROW_NOT_UNKNOWN")
    minute = int(row["minute"])
    if minute - 6 < phase_start(minute):
        return "INSUFFICIENT_PHASE_HISTORY_FOR_RETURN5"
    if row.get("newClosedBarObserved") is not True:
        return "NO_NEW_CLOSED_BAR_AT_ASOF"
    return "STRICT_CONTIGUOUS_WINDOW_UNAVAILABLE"


def exact_offset_row(rows_by_delay: dict[int, dict], delay: int):
    return rows_by_delay.get(delay)


def causal_trajectory(rows: list[dict]) -> dict:
    by_delay = {int(row["delay"]): row for row in rows}
    if 0 not in by_delay:
        raise ValueError("MISSING_DECISION_ROW")
    initial = estimate_state(by_delay[0])
    if initial != "UNKNOWN":
        raise ValueError("NOT_INITIAL_UNKNOWN")

    exact = {}
    first_defined_delay = None
    first_defined_state = None
    for delay in sorted(by_delay):
        state = estimate_state(by_delay[delay])
        if delay > 0 and first_defined_delay is None and state != "UNKNOWN":
            first_defined_delay = delay
            first_defined_state = state
    for offset in OFFSETS:
        row = exact_offset_row(by_delay, offset)
        exact[str(offset)] = {
            "checkpointPresent": row is not None,
            "state": estimate_state(row) if row is not None else "NO_CHECKPOINT",
        }

    compact = ["UNKNOWN"]
    previous = "UNKNOWN"
    for delay in sorted(d for d in by_delay if d > 0 and d <= max(OFFSETS)):
        state = estimate_state(by_delay[delay])
        if state != previous:
            compact.append(state)
            previous = state
    return {
        "firstDefinedDelay": first_defined_delay,
        "firstDefinedState": first_defined_state,
        "exactOffsets": exact,
        "transitionSignatureThroughT10": ">".join(compact),
    }


def mean_or_none(values):
    xs = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return sum(xs) / len(xs) if xs else None


def load_gzip_json(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def verify_source_hashes(signal_measurement: Path, entry_measurement: Path,
                         entry_manifest_path: Path) -> dict:
    signal_manifest = read_json(signal_measurement / "manifest.json")
    for path in sorted((signal_measurement / "minute-census").glob("*.json.gz")):
        key = f"minute-census/{path.name}"
        if key not in signal_manifest or sha256(path) != signal_manifest[key]:
            raise AssertionError(("MINUTE_CENSUS_HASH", key))

    entry_manifest = read_json(entry_manifest_path)
    expected = entry_manifest["files"]
    for name in (
        "baseline-immediate-records.json.gz",
        "entry-records.json.gz",
        "paired-entry-v1-vs-immediate.json.gz",
        "state-diagnostics.json",
        "lookahead-audit.json",
    ):
        rel = f"docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/{name}"
        if rel not in expected or sha256(entry_measurement / name) != expected[rel]:
            raise AssertionError(("ENTRY_V1_HASH", name))
    if not entry_manifest.get("safety9AllFalse"):
        raise AssertionError("SAFETY_NOT_FROZEN_FALSE")
    if entry_manifest.get("providerRequests") != 0 or entry_manifest.get("protectedDataOpened") != 0:
        raise AssertionError("PROTECTED_INPUT_VIOLATION")
    return {
        "signalMeasurementManifestSHA256": sha256(signal_measurement / "manifest.json"),
        "entryV1ManifestSHA256": sha256(entry_manifest_path),
        "sourceIntegrity": "PASS",
    }


def run(args):
    signal_measurement = Path(args.signal_measurement)
    entry_measurement = Path(args.entry_v1_measurement)
    entry_manifest_path = Path(args.entry_v1_manifest)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)

    source_audit = verify_source_hashes(signal_measurement, entry_measurement, entry_manifest_path)

    rows_by_opportunity = collections.defaultdict(list)
    decision_rows = {}
    checkpoint_count = 0
    closed_bar_violations = 0
    for path in sorted((signal_measurement / "minute-census").glob("*.json.gz")):
        for row in read_json(path):
            checkpoint_count += 1
            through = row.get("computedThroughBarStart")
            if through is not None and through >= row["minute"]:
                closed_bar_violations += 1
            oid = row["opportunity"]
            rows_by_opportunity[oid].append(row)
            if int(row["delay"]) == 0:
                if oid in decision_rows:
                    raise AssertionError(("DUPLICATE_DECISION", oid))
                decision_rows[oid] = row

    if len(decision_rows) != EXPECTED_POPULATION:
        raise AssertionError(("POPULATION", len(decision_rows)))
    if closed_bar_violations:
        raise AssertionError(("CLOSED_BAR_VIOLATIONS", closed_bar_violations))

    unknown_ids = sorted(
        oid for oid, row in decision_rows.items() if estimate_state(row) == "UNKNOWN"
    )
    if len(unknown_ids) != EXPECTED_INITIAL_UNKNOWN:
        raise AssertionError(("INITIAL_UNKNOWN", len(unknown_ids)))

    reasons = collections.Counter()
    selection_minute = collections.Counter()
    phase_age = collections.Counter()
    data_availability = collections.Counter()
    exact_state_counts = {str(offset): collections.Counter() for offset in OFFSETS}
    defined_by = {str(offset): 0 for offset in OFFSETS}
    first_defined_delay_counts = collections.Counter()
    first_defined_state_counts = collections.Counter()
    transition_signatures = collections.Counter()
    details = []

    for oid in unknown_ids:
        decision = decision_rows[oid]
        reason = unknown_reason(decision)
        trajectory = causal_trajectory(rows_by_opportunity[oid])
        reasons[reason] += 1
        minute = int(decision["minute"])
        selection_minute[str(minute)] += 1
        phase_age[phase_age_bucket(minute)] += 1
        data_availability["newClosedBarObserved_true" if decision.get("newClosedBarObserved") is True
                          else "newClosedBarObserved_false"] += 1
        data_availability["previousDayAvailable_true" if decision["context"].get("previousDayAvailable")
                          else "previousDayAvailable_false"] += 1
        for horizon in ("1", "3", "5", "10"):
            data_availability[f"return{horizon}_defined" if decision["context"]["returnPct"].get(horizon) is not None
                              else f"return{horizon}_missing"] += 1

        first = trajectory["firstDefinedDelay"]
        if first is None:
            first_defined_delay_counts["NOT_DEFINED_BY_LAST_CHECKPOINT"] += 1
        else:
            first_defined_delay_counts[str(first)] += 1
            first_defined_state_counts[trajectory["firstDefinedState"]] += 1
        for offset in OFFSETS:
            item = trajectory["exactOffsets"][str(offset)]
            exact_state_counts[str(offset)][item["state"]] += 1
            if first is not None and first <= offset:
                defined_by[str(offset)] += 1
        transition_signatures[trajectory["transitionSignatureThroughT10"]] += 1
        details.append({
            "opportunity": oid,
            "selectionMinute": minute,
            "phaseAgeBucket": phase_age_bucket(minute),
            "unknownReason": reason,
            **trajectory,
        })

    causal_summary = {
        "initialUnknown": len(unknown_ids),
        "initialUnknownRatePct": 100 * len(unknown_ids) / EXPECTED_POPULATION,
        "reasonCounts": dict(sorted(reasons.items())),
        "selectionMinuteCounts": dict(sorted(selection_minute.items(), key=lambda item: int(item[0]))),
        "phaseAgeCounts": dict(phase_age),
        "dataAvailabilityCounts": dict(data_availability),
        "exactOffsetStateCounts": {
            offset: {state: exact_state_counts[offset].get(state, 0)
                     for state in STATES + ("NO_CHECKPOINT",)}
            for offset in map(str, OFFSETS)
        },
        "definedByOffset": {
            str(offset): {
                "count": defined_by[str(offset)],
                "ratePct": 100 * defined_by[str(offset)] / len(unknown_ids),
            }
            for offset in OFFSETS
        },
        "firstDefinedDelayCounts": dict(sorted(first_defined_delay_counts.items())),
        "firstDefinedStateCounts": {state: first_defined_state_counts.get(state, 0) for state in STATES},
        "transitionSignaturesThroughT10": dict(
            transition_signatures.most_common()
        ),
    }

    # Evaluator-only section. Cohort membership and all causal trajectories are
    # already fixed above; these fields can describe the consequence of WAIT
    # but cannot create, tune, or select a policy.
    entry_records = load_gzip_json(entry_measurement / "entry-records.json.gz")
    immediate_records = load_gzip_json(entry_measurement / "baseline-immediate-records.json.gz")
    paired = load_gzip_json(entry_measurement / "paired-entry-v1-vs-immediate.json.gz")
    unknown_set = set(unknown_ids)
    candidate = {row["opportunity"]: row for row in entry_records if row["opportunity"] in unknown_set}
    immediate = {row["opportunity"]: row for row in immediate_records if row["opportunity"] in unknown_set}
    pair_rows = [row for row in paired if row["opportunity"] in unknown_set]
    if not (len(candidate) == len(immediate) == len(pair_rows) == EXPECTED_INITIAL_UNKNOWN):
        raise AssertionError(("PAIRED_COHORT_SIZE", len(candidate), len(immediate), len(pair_rows)))

    intent_reasons = collections.Counter(candidate[oid]["intentReason"] or "NO_INTENT" for oid in unknown_ids)
    immediate_fills = sum(immediate[oid]["entryId"] is not None for oid in unknown_ids)
    wait_fills = sum(candidate[oid]["entryId"] is not None for oid in unknown_ids)
    pair_status = collections.Counter(row["status"] for row in pair_rows)
    evaluator_summary = {
        "evaluatorOnly": True,
        "cohortFixedBeforeEvaluatorOpen": True,
        "population": len(pair_rows),
        "intentReasonCounts": dict(intent_reasons),
        "immediateFills": immediate_fills,
        "waitFills": wait_fills,
        "immediateFillRatePct": 100 * immediate_fills / len(pair_rows),
        "waitFillRatePct": 100 * wait_fills / len(pair_rows),
        "fillRateDeltaPp": 100 * (wait_fills - immediate_fills) / len(pair_rows),
        "pairStatus": dict(pair_status),
        "pairedMetrics": {
            metric: distribution(row.get(metric) for row in pair_rows)
            for metric in PAIR_METRICS
        },
    }

    summary = {
        "artifactKind": "phase57_entry_unknown_coverage_diagnostic_v1",
        "version": "v1.0",
        "diagnosticOnly": True,
        "policyCreated": False,
        "policyChanged": False,
        "thresholdSearch": False,
        "entryV2Started": False,
        "exitStarted": False,
        "capitalStarted": False,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "population": EXPECTED_POPULATION,
        "checkpointCount": checkpoint_count,
        "sourceAudit": source_audit,
        "causal": causal_summary,
        "evaluatorPairedAnatomy": evaluator_summary,
        "safety": {
            "executionAllowed": False,
            "brokerWriteAllowed": False,
            "excelOrderWriteAllowed": False,
            "rssOrderFunctionAllowed": False,
            "liveTradingAllowed": False,
            "paperTradingAllowed": False,
            "automaticPromotionAllowed": False,
            "productionUpdateAllowed": False,
            "transmitted": False,
        },
        "status": "DIAGNOSTIC_COMPLETE_STOP_NO_POLICY_DECISION",
    }
    write_json(output / "summary.json", summary)
    write_gzip_json(output / "unknown-trajectories.json.gz", details)
    manifest = {
        "summary.json": sha256(output / "summary.json"),
        "unknown-trajectories.json.gz": sha256(output / "unknown-trajectories.json.gz"),
    }
    write_json(output / "manifest.json", manifest)
    print("UNKNOWN_DIAGNOSTIC_SUMMARY_BEGIN")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    print("UNKNOWN_DIAGNOSTIC_SUMMARY_END")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--signal-measurement", required=True)
    parser.add_argument("--entry-v1-measurement", required=True)
    parser.add_argument("--entry-v1-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
