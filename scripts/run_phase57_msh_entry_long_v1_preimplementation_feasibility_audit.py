#!/usr/bin/env python3
"""NO-TRAINING semantic/data feasibility audit for Phase57 MSH-Entry LONG v1."""
import argparse
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

FEATURES = [
    "directionalReturnFromOpenPct", "directionalVwapDistancePct", "directionalMomentum3Pct",
    "directionalMomentumAccelerationPct", "directionalPullback6Pct", "relativeVolume5",
    "minutesSinceFirstSelection", "hybridReciprocalRank", "priorSelectionCount", "direction",
]
CORE = {
    "A": ["selectorScore"],
    "B": ["selectorScore", "ridgeRank"],
    "C": ["selectorScore", "directionalMomentum3Pct"],
    "D": ["selectorScore", "ridgeRank", "directionalMomentum3Pct"],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def read_ndjson(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def read_gzip_ndjson(path):
    with gzip.open(path, "rt") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def pct(n, d):
    return round(100 * n / d, 10) if d else None


def quantile(values, q):
    values = sorted(values)
    if not values:
        return None
    return values[round((len(values) - 1) * q)]


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def canonical_instant(value):
    """Normalize equivalent ISO-8601 representations before lineage comparison."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def field_audit(rows, key, validator=lambda value: finite(value)):
    values = [row.get(key) for row in rows]
    available = [value for value in values if validator(value)]
    return {
        "available": len(available), "missing": sum(value is None for value in values),
        "nonfiniteOrInvalid": len(values) - len(available) - sum(value is None for value in values),
        "availabilityPct": pct(len(available), len(values)),
        "min": min(available) if available else None, "max": max(available) if available else None,
    }


def feature_matrix(rows):
    result = {}
    for feature in FEATURES:
        statuses = Counter(row["features"][feature]["status"] for row in rows)
        result[feature] = {
            "available": statuses.get("AVAILABLE", 0),
            "availabilityPct": pct(statuses.get("AVAILABLE", 0), len(rows)),
            "statuses": dict(sorted(statuses.items())),
            "minimumHistoryAndDependency": None,
        }
    dependencies = {
        "directionalMomentum3Pct": "4 completed same-session 5m bars; latest close / close 3 completed bars earlier; lunch boundary skips scheduled recess; no prior session and no fill",
        "directionalMomentumAccelerationPct": "7 completed same-session 5m bars; Momentum3 minus Momentum6; no prior session and no fill",
        "directionalPullback6Pct": "6 completed same-session 5m bars including High; no prior session and no fill",
        "relativeVolume5": "6 completed same-session 5m bars and positive prior-five mean volume",
        "directionalReturnFromOpenPct": "exact 09:00 open plus latest completed close; session-open dependent, intervening gaps not used by the formula",
        "directionalVwapDistancePct": "complete observed session-to-date 5m grid beginning 09:00 and positive volume; session-open and grid dependent",
        "minutesSinceFirstSelection": "selector event lineage only; wall-clock elapsed time",
        "hybridReciprocalRank": "selector rank only; 1/rank",
        "priorSelectionCount": "earlier Top5 events for the same symbol-session",
        "direction": "constant LONG=1; semantically redundant in a LONG-only model",
    }
    for feature, text in dependencies.items():
        result[feature]["minimumHistoryAndDependency"] = text
    return result


def core_scoreability(rows):
    output = {}
    subsets = {"ALL": rows, "OPEN_EARLY": [row for row in rows if row["decisionTimestamp"][11:16] == "09:30"],
               "OTHER_TIMES": [row for row in rows if row["decisionTimestamp"][11:16] != "09:30"]}
    for name, features in CORE.items():
        output[name] = {"features": features}
        for subset_name, subset in subsets.items():
            count = 0
            for row in subset:
                ok = True
                for feature in features:
                    if feature == "selectorScore":
                        ok &= finite(row.get("ridgeScore"))
                    elif feature == "ridgeRank":
                        ok &= isinstance(row.get("ridgeRank"), int) and 1 <= row["ridgeRank"] <= 5
                    else:
                        ok &= row["features"][feature]["status"] == "AVAILABLE"
                count += bool(ok)
            output[name][subset_name] = {"scoreable": count, "total": len(subset), "scoreabilityPct": pct(count, len(subset))}
    return output


def grouped_label_coverage(rows):
    output = {}
    for time in sorted(set(row["decisionTimestamp"][11:16] for row in rows)):
        group = [row for row in rows if row["decisionTimestamp"][11:16] == time]
        count = sum(row["label"]["labelable"] for row in group)
        output[time] = {"events": len(group), "labelable": count, "coveragePct": pct(count, len(group)),
                        "unlabelableReasons": dict(Counter(row["label"]["reason"] for row in group if not row["label"]["labelable"]))}
    return output


def markdown(report):
    selector = report["selectorOutputAudit"]
    repetition = report["trainingRows"]["repeatedSelectionDistribution"]
    labels = report["ordinalLabelFeasibility"]
    lines = [
        "# Phase57 MSH-Entry LONG v1 Pre-Implementation Feasibility Audit", "",
        f"**Verdict: {report['feasibilityVerdict']}**", "",
        "Same already-opened 76 Development sessions only. No model was fit, no predictions or performance metrics were produced, and no threshold, class weight, L2 value, feature importance, or CV performance was searched.", "",
        "## Identity and training rows", "",
        f"- Candidate rows: {report['trainingRows']['selectionEvents']:,} Frozen Selector Top5 events",
        f"- Unique symbol-sessions: {report['trainingRows']['uniqueSymbolSessions']:,}",
        f"- Repeats per symbol-session: median {repetition['median']}, P90 {repetition['p90']}, max {repetition['max']}",
        f"- Selector score / rank / Decision Price availability: {selector['ridgeScore']['availabilityPct']:.2f}% / {selector['ridgeRank']['availabilityPct']:.2f}% / {selector['decisionPrice']['availabilityPct']:.2f}%", "",
        "## Existing feature intrinsic availability", "",
        "| Feature | All | Open Early | Dependency |", "|---|---:|---:|---|",
    ]
    for feature in FEATURES:
        all_row = report["featureAvailability"]["overall"][feature]
        open_row = report["featureAvailability"]["openEarly"][feature]
        lines.append(f"| {feature} | {all_row['availabilityPct']:.2f}% | {open_row['availabilityPct']:.2f}% | {all_row['minimumHistoryAndDependency']} |")
    lines += ["", "## Strict wall-clock 30m ordinal label", "",
              f"- Labelable: {labels['labelableEvents']:,} / {labels['selectionEvents']:,} ({labels['coveragePct']:.2f}%)",
              f"- HIGH availability: {labels['highAvailability']['available']:,}; CLOSE availability: {labels['closeAvailability']['available']:,}", "",
              "| Class | Count | Meaning |", "|---:|---:|---|",
              f"| 0 | {labels['classCounts']['0']:,} | below +1% |",
              f"| 1 | {labels['classCounts']['1']:,} | +1% to below +2% |",
              f"| 2 | {labels['classCounts']['2']:,} | +2% to below +3% |",
              f"| 3 | {labels['classCounts']['3']:,} | +3% to below +5% |",
              f"| 4 | {labels['classCounts']['4']:,} | +5% or more |", "",
              "## Core scoreability", "", "| Core | Features | All | Open Early |", "|---|---|---:|---:|"]
    for name, row in report["coreScoreability"].items():
        lines.append(f"| {name} | {', '.join(row['features'])} | {row['ALL']['scoreabilityPct']:.2f}% | {row['OPEN_EARLY']['scoreabilityPct']:.2f}% |")
    lines += ["", "## Contract recommendations", ""]
    for key, value in report["finalContractRecommendations"].items():
        lines.append(f"- **{key}:** {value}")
    lines += ["", f"STOP: {report['stopBoundary']}", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--prior-events", required=True)
    parser.add_argument("--prior-transfer-report", required=True)
    parser.add_argument("--prior-filter-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown-output", required=True)
    args = parser.parse_args()

    contract_bytes = Path(args.contract).read_bytes()
    contract = json.loads(contract_bytes)
    input_dir = Path(args.input_dir)
    rows = read_ndjson(input_dir / "entry-preimplementation-feasibility-events.ndjson")
    manifest = read_json(input_dir / "input-manifest.json")
    prior_events_bytes = gzip.decompress(Path(args.prior_events).read_bytes())
    prior_events = [json.loads(line) for line in prior_events_bytes.splitlines() if line]
    prior_by_id = {row["selectorEventId"]: row for row in prior_events}

    checks = {
        "sessions76": len({row["sessionDate"] for row in rows}) == 76,
        "decisionTimestamps760": len({(row["sessionDate"], row["decisionTimestamp"]) for row in rows}) == 760,
        "selectionEvents3800": len(rows) == 3800,
        "uniqueEventIds": len({row["selectorEventId"] for row in rows}) == len(rows),
        "priorEventIdentityMatch": set(prior_by_id) == {row["selectorEventId"] for row in rows},
        "priorTransferReportPinned": sha(Path(args.prior_transfer_report).read_bytes()) == contract["frozenInputs"]["priorTransferReportFileSha256"],
        "priorTransferLedgerGzipPinned": sha(Path(args.prior_events).read_bytes()) == contract["frozenInputs"]["priorTransferLedgerGzipSha256"],
        "priorTransferLedgerPayloadPinned": sha(prior_events_bytes) == contract["frozenInputs"]["priorTransferLedgerPayloadSha256"],
        "priorFilterAuditReportPinned": sha(Path(args.prior_filter_report).read_bytes()) == contract["frozenInputs"]["priorFilterAuditReportFileSha256"],
        "selectorFreezeUnchanged": manifest["source"]["frozenSelectorFreezeCommit"] == contract["frozenInputs"]["selectorFreezeCommit"],
        "selectorArtifactUnchanged": manifest["source"]["frozenSelectorArtifactSha256"] == contract["frozenInputs"]["selectorRidgeArtifactSha256"],
        "longOnly": all(row["direction"] == "LONG" and row["shortScoreEvaluated"] is False for row in rows),
    }
    identity_mismatch = []
    for row in rows:
        old = prior_by_id.get(row["selectorEventId"])
        timestamp_matches = old is not None and canonical_instant(old["decisionTimestamp"]) == canonical_instant(row["decisionTimestamp"])
        fields_match = old is not None and all(
            old[key] == row[key]
            for key in ["sessionDate", "symbol", "decisionPrice", "ridgeRank", "ridgeScore"]
        )
        if not timestamp_matches or not fields_match:
            identity_mismatch.append(row["selectorEventId"])
    checks["priorEventFieldsExact"] = not identity_mismatch
    failures = [key for key, value in checks.items() if not value]

    symbol_sessions = Counter(row["symbolSessionId"] for row in rows)
    repeat_values = sorted(symbol_sessions.values())
    training_rows = {
        "unit": "FROZEN_SELECTOR_TOP5_SELECTION_EVENT", "selectionEvents": len(rows),
        "uniqueSymbolSessions": len(symbol_sessions), "independentTradeInterpretationAllowed": False,
        "repeatedSelectionDistribution": {
            "median": median(repeat_values), "p90": quantile(repeat_values, .90), "max": max(repeat_values),
            "frequency": {str(key): value for key, value in sorted(Counter(repeat_values).items())},
            "repeatedSymbolSessions": sum(count > 1 for count in repeat_values),
        },
    }

    score = field_audit(rows, "ridgeScore")
    rank = field_audit(rows, "ridgeRank", lambda value: isinstance(value, int) and 1 <= value <= 5)
    price = field_audit(rows, "decisionPrice", lambda value: finite(value) and value > 0)
    age = field_audit(rows, "decisionPriceAgeMinutes", lambda value: finite(value) and 0 <= value <= 5)
    decision_groups = defaultdict(list)
    for row in rows:
        decision_groups[(row["sessionDate"], row["decisionTimestamp"])].append(row)
    duplicate_rank_groups = sum(len({row["ridgeRank"] for row in group}) != 5 for group in decision_groups.values())
    score_tie_groups = sum(len({row["ridgeScore"] for row in group}) != len(group) for group in decision_groups.values())
    selector_output = {
        "ridgeScore": {**score, "duplicateEventValuesAllowed": True, "exactTieDecisionGroups": score_tie_groups,
                       "tieBreakSemantics": "RIDGE_SCORE_DESC_THEN_SYMBOL_ASC"},
        "ridgeRank": {**rank, "duplicateRankDecisionGroups": duplicate_rank_groups,
                      "rankCounts": dict(sorted(Counter(str(row["ridgeRank"]) for row in rows).items()))},
        "decisionPrice": {**price, "freshAgeAudit": age,
                          "sourceCounts": dict(Counter(row.get("decisionPriceSource") for row in rows)),
                          "roleVerdict": "REFERENCE_ONLY",
                          "roleReason": "Required for label, opportunity and execution-reference semantics; raw nominal price has no architecture-level scale invariance that justifies a predictive feature without performance evidence."},
        "eventIdDuplicates": len(rows) - len({row["selectorEventId"] for row in rows}),
        "timestampIntegrityFailures": sum(row["decisionTimestamp"][:10] != row["sessionDate"] for row in rows),
    }

    overall_features = feature_matrix(rows)
    open_rows = [row for row in rows if row["decisionTimestamp"][11:16] == "09:30"]
    other_rows = [row for row in rows if row["decisionTimestamp"][11:16] != "09:30"]
    open_features = feature_matrix(open_rows)
    current_atomic = Counter(row.get("currentAtomicStatus") for row in rows)
    atomic_score_ready = sum(row.get("currentAtomicReason") in ["LONG_ABOVE_FROZEN_THRESHOLD", "LONG_NOT_ABOVE_FROZEN_THRESHOLD"] for row in rows)
    feature_availability = {
        "semantics": "INTRINSIC_MINIMUM_DEPENDENCY_AVAILABILITY_USING_UNCHANGED_EXISTING_FORMULAS; CURRENT_ATOMIC_GATE_REPORTED_SEPARATELY",
        "overall": overall_features, "openEarly": open_features, "otherTimes": feature_matrix(other_rows),
        "currentAtomicGate": {"statuses": dict(current_atomic), "scoreReady": atomic_score_ready,
                              "scoreReadyPct": pct(atomic_score_ready, len(rows)),
                              "note": "ALREADY_ENTERED PASS events are not counted as feature score-ready."},
    }

    labelable = [row for row in rows if row["label"]["labelable"]]
    unlabelable = [row for row in rows if not row["label"]["labelable"]]
    class_counts = Counter(str(row["label"]["ordinalClass"]) for row in labelable)
    close_class_counts = Counter(str(row["label"]["closeOrdinalClass"]) for row in labelable)
    nonzero_classes = [count for count in class_counts.values() if count]
    ordinal = {
        "selectionEvents": len(rows), "labelableEvents": len(labelable), "unlabelableEvents": len(unlabelable),
        "coveragePct": pct(len(labelable), len(rows)), "classCounts": {str(level): class_counts[str(level)] for level in range(5)},
        "classSharePct": {str(level): pct(class_counts[str(level)], len(labelable)) for level in range(5)},
        "classImbalanceMaxToMinRepresented": round(max(nonzero_classes)/min(nonzero_classes), 10) if nonzero_classes else None,
        "representedClasses": sum(class_counts[str(level)] > 0 for level in range(5)),
        "unlabelableReasons": dict(sorted(Counter(row["label"]["reason"] for row in unlabelable).items())),
        "highAvailability": {"available": sum(row["label"]["highAvailable"] for row in rows),
                             "coveragePct": pct(sum(row["label"]["highAvailable"] for row in rows), len(rows))},
        "closeAvailability": {"available": sum(row["label"]["closeAvailable"] for row in rows),
                              "coveragePct": pct(sum(row["label"]["closeAvailable"] for row in rows), len(rows)),
                              "classCounts": {str(level): close_class_counts[str(level)] for level in range(5)}},
        "highTouchGreaterThanCloseClass": sum(row["label"]["ordinalClass"] > row["label"]["closeOrdinalClass"] for row in labelable),
        "touchSemanticsAssessment": "Both are computable from the same complete historical 30m path. Future HIGH touch is suitable only as the candidate primary ordinal label; completed CLOSE must remain a separately lineage-bound supporting diagnostic, not a hybridized label in this audit.",
        "byDecisionTime": grouped_label_coverage(rows),
        "priorEndpointOnlyReference": contract["priorPublishedReference"],
    }

    cores = core_scoreability(rows)
    momentum_all = overall_features["directionalMomentum3Pct"]["availabilityPct"]
    momentum_open = open_features["directionalMomentum3Pct"]["availabilityPct"]
    selector_complete = score["available"] == len(rows) and rank["available"] == len(rows) and price["available"] == len(rows)
    all_classes = ordinal["representedClasses"] == 5
    any_core_missing = any(value["ALL"]["scoreable"] < len(rows) for key, value in cores.items() if key in ["C", "D"])
    if failures:
        verdict = "INCONCLUSIVE"
    elif not selector_complete or not all_classes or not labelable:
        verdict = "MSH_ENTRY_LONG_V1_NOT_FEASIBLE"
    elif len(labelable) < len(rows) or any_core_missing:
        verdict = "MSH_ENTRY_LONG_V1_FEASIBLE_WITH_CONTRACT_CHANGES"
    else:
        verdict = "MSH_ENTRY_LONG_V1_FEASIBLE"

    recommendations = {
        "trainingRowUnit": "One frozen Top5 selection event. Repeats remain correlated observations, never independent trades.",
        "primaryLabelSemantics": "Candidate ordinal 0..4 from maximum future continuous 5m HIGH over a complete strict +30 wall-clock-minute same-session path; unlabelable rows excluded, never class 0. Freeze only after independent review.",
        "supportingLabelDiagnostic": "Completed 5m CLOSE ordinal confirmation from the identical complete 30m path, stored separately from the primary HIGH-touch label.",
        "coreFeatures": "Mandatory v1 core: frozen Selector Ridge score and rank. Both are complete Selector outputs and require no market-bar imputation.",
        "optionalFeatures": (f"Momentum3 is intrinsically available for {momentum_all:.2f}% overall and {momentum_open:.2f}% Open Early; treat it and other bar-derived features as optional until a missing contract is frozen. "
                             "Raw Decision Price is reference-only; LONG direction is constant and should not be a model feature."),
        "missingStrategy": "Do not use raw missing=0. Keep mandatory core fully observed. If an optional feature is admitted later, use an explicit missing indicator plus training-only standardized neutral value; otherwise omit it from v1. No forward-fill or previous-session substitution.",
        "state": "Stateless ENTER or SKIP_THIS_DECISION at each frozen selection event. Re-evaluate only on a later explicit Frozen Selector reselection; do not inherit WATCH/WAIT/terminal-expiry semantics. Position/re-entry safety remains external.",
        "cvSplit": "SESSION-grouped expanding-window chronological split. All events from a JST session stay in one fold, which also keeps every symbol-session together. Fold count remains unfrozen; ordinary stratified K-fold is prohibited.",
        "developmentAllocation": "The same 76 already outcome-exposed sessions may be reused only as MSH-Entry LONG v1 Development. They cannot become Validation/OOS. Preserve all sealed Validation/OOS/EXIT/integration/allocation/portfolio data.",
    }

    report = {
        "schemaVersion": 1, "status": "MSH_ENTRY_LONG_V1_PREIMPLEMENTATION_FEASIBILITY_AUDIT_COMPLETE_STOP",
        "contractId": contract["contractId"], "contractSha256": sha(contract_bytes),
        "source": manifest["source"], "integrity": {"pass": not failures, "checks": checks, "failures": failures,
            "identityMismatchExamples": identity_mismatch[:10]},
        "methodology": {"modelFitCalls": 0, "predictionRows": 0, "thresholdSearches": 0, "cvPerformanceRuns": 0,
                        "featureImportanceRuns": 0, "newProviderRequests": 0, "validationOpened": False, "oosOpened": False,
                        "sameOpenedDevelopmentReused": True},
        "safety": contract["safety"], "trainingRows": training_rows, "selectorOutputAudit": selector_output,
        "featureAvailability": feature_availability, "ordinalLabelFeasibility": ordinal,
        "coreScoreability": cores,
        "missingSemanticsRecommendation": recommendations["missingStrategy"],
        "repeatedSelectionLeakageRisk": {
            "risk": "MATERIAL_IF_EVENT_ROWS_ARE_RANDOMLY_SPLIT",
            "reason": "Repeated events share symbol, session path, Selector context and overlapping future-label windows.",
            "recommendedGrouping": "WHOLE_JST_SESSION; SYMBOL_SESSION_CONTAINMENT_IS_THEN_AUTOMATIC",
        },
        "chronologicalSplitFeasibility": {
            "sessions": 76, "firstSession": min(row["sessionDate"] for row in rows), "lastSession": max(row["sessionDate"] for row in rows),
            "recommended": recommendations["cvSplit"],
            "fourFoldBlocked": "SEMANTICALLY_POSSIBLE_AS_4_CONTIGUOUS_19_SESSION_BLOCKS",
            "fiveFoldBlocked": "SEMANTICALLY_POSSIBLE_BUT_UNEVEN_BLOCK_SIZES",
            "stratifiedKFold": "PROHIBITED_BREAKS_TIME_AND_DEPENDENCE",
            "foldCountDecision": "NOT_FROZEN_IN_THIS_AUDIT",
        },
        "dataAllocation": {"developmentReuseAllowed": True, "reuseScope": "MSH_ENTRY_LONG_V1_DEVELOPMENT_ONLY",
                           "validationNewAccess": 0, "oosNewAccess": 0, "providerRequests": 0},
        "finalContractRecommendations": recommendations,
        "feasibilityVerdict": verdict, "stopBoundary": contract["completionBoundary"],
        "limitations": [
            "Availability and class counts are feasibility evidence, not predictive performance.",
            "Intrinsic per-feature availability preserves existing formulas but deliberately removes the legacy shared atomic gate for diagnosis only.",
            "No feature was selected by outcome and no model, coefficient, threshold, class weight, regularization value, or fold count was chosen.",
        ],
    }
    core_bytes = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    report["reportSha256"] = sha(core_bytes)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.markdown_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    Path(args.markdown_output).write_text(markdown(report))
    print(json.dumps({"status": report["status"], "verdict": verdict, "reportSha256": report["reportSha256"],
                      "events": len(rows), "labelable": len(labelable), "integrity": not failures}))


if __name__ == "__main__":
    main()
