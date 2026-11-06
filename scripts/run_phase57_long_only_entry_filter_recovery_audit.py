#!/usr/bin/env python3
"""Descriptive CURRENT Entry filter-recovery audit on already-opened Development only."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd


LEVELS = [1, 2, 3, 5]
STATUSES = ["PASS", "WAIT", "REJECT", "BLOCKED", "UNAVAILABLE"]
FEATURES = [
    "directionalReturnFromOpenPct", "directionalVwapDistancePct", "directionalMomentum3Pct",
    "directionalMomentumAccelerationPct", "directionalPullback6Pct", "relativeVolume5",
    "minutesSinceFirstSelection", "hybridReciprocalRank", "priorSelectionCount", "direction",
]


def finite(value):
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def number(value):
    return round(float(value), 10) if finite(value) else None


def ratio(numerator, denominator, scale=1):
    return number(scale * numerator / denominator) if denominator else None


def distribution(values):
    clean = pd.to_numeric(pd.Series(list(values), dtype="object"), errors="coerce").replace(
        [np.inf, -np.inf], np.nan).dropna().to_numpy(float)
    if not len(clean):
        return {"n": 0, **{key: None for key in ["mean", "min", "p25", "median", "p75", "p90", "max"]}}
    return {"n": int(len(clean)), "mean": number(clean.mean()), "min": number(clean.min()),
            "p25": number(np.quantile(clean, .25)), "median": number(np.quantile(clean, .5)),
            "p75": number(np.quantile(clean, .75)), "p90": number(np.quantile(clean, .90)),
            "max": number(clean.max())}


def opportunity_metrics(frame):
    result = {"selectionEvents": int(len(frame)), "uniqueSymbols": int(frame.symbol.nunique()) if len(frame) else 0,
              "uniqueSymbolSessions": int(frame.symbolSessionId.nunique()) if len(frame) else 0,
              "sessions": int(frame.sessionDate.nunique()) if len(frame) else 0, "opportunity": {}}
    for level in LEVELS:
        values = pd.to_numeric(frame[f"selectorOpportunity{level}"], errors="coerce")
        valid = values.isin([0, 1])
        hits = int(values[valid].eq(1).sum())
        result["opportunity"][str(level)] = {"evaluableN": int(valid.sum()), "hitN": hits,
                                               "precisionPct": ratio(hits, int(valid.sum()), 100)}
    result["selectorMfePct"] = distribution(frame.selectorMfePct)
    result["selectorTrueMaePct"] = distribution(frame.selectorMaePct)
    return result


def canonical_class(reason, contract):
    return contract["canonicalBlockedReasonClasses"].get(str(reason), "OTHER" if reason else "UNKNOWN")


def time_band(time_value, contract):
    for band, times in contract["timeOfDayBandsJst"].items():
        if time_value in times:
            return band
    return "UNKNOWN"


def grouped_status_and_opportunity(events, field, values):
    output = {}
    for value in values:
        group = events[events[field].eq(value)]
        output[str(value)] = {
            "selectionEvents": int(len(group)),
            "statuses": {status: {"count": int(group.directStatus.eq(status).sum()),
                                   "ratePct": ratio(int(group.directStatus.eq(status).sum()), len(group), 100)}
                         for status in STATUSES},
            "byStatusOpportunity": {status: opportunity_metrics(group[group.directStatus.eq(status)])
                                    for status in STATUSES if group.directStatus.eq(status).any()},
        }
    return output


def feature_summary(rows, key):
    values = [(row.get(key) or {}) for row in rows]
    return {feature: distribution(value.get(feature) for value in values) for feature in FEATURES}


def contribution_comparison(pass_ticks, nonpass_ticks):
    output = {}
    for feature in FEATURES:
        pass_values = [(row.get("features") or {}).get(feature) for row in pass_ticks]
        nonpass_values = [(row.get("features") or {}).get(feature) for row in nonpass_ticks]
        pass_contrib = [(row.get("contributions") or {}).get(feature) for row in pass_ticks]
        nonpass_contrib = [(row.get("contributions") or {}).get(feature) for row in nonpass_ticks]
        pass_dist, nonpass_dist = distribution(pass_values), distribution(nonpass_values)
        pass_c, nonpass_c = distribution(pass_contrib), distribution(nonpass_contrib)
        output[feature] = {
            "firstPassValue": pass_dist,
            "neverPassLastScoreReadyValue": nonpass_dist,
            "medianValueDifference": number(pass_dist["median"]-nonpass_dist["median"])
            if pass_dist["median"] is not None and nonpass_dist["median"] is not None else None,
            "firstPassLogitContribution": pass_c,
            "neverPassLastScoreReadyLogitContribution": nonpass_c,
            "meanContributionDifference": number(pass_c["mean"]-nonpass_c["mean"])
            if pass_c["mean"] is not None and nonpass_c["mean"] is not None else None,
        }
    return output


def latest_score_ready_ticks(ticks, symbol_sessions):
    candidates = [row for row in ticks if row["symbolSessionId"] in symbol_sessions and finite(row.get("probability"))]
    latest = {}
    for row in sorted(candidates, key=lambda value: (value["symbolSessionId"], value["evaluationTimestamp"])):
        latest[row["symbolSessionId"]] = row
    return list(latest.values())


def first_pass_ticks(ticks):
    output = {}
    for row in sorted(ticks, key=lambda value: (value["symbolSessionId"], value["evaluationTimestamp"])):
        if row["status"] == "PASS" and row["symbolSessionId"] not in output:
            output[row["symbolSessionId"]] = row
    return list(output.values())


def score_snapshot(rows):
    return {
        "probability": distribution(row.get("probability") for row in rows),
        "thresholdDistance": distribution(row.get("thresholdDistance") for row in rows),
        "logit": distribution(row.get("logit") for row in rows),
        "features": feature_summary(rows, "features"),
        "contributions": feature_summary(rows, "contributions"),
    }


def markdown(report):
    verdict = report["architectureMismatchVerdict"]
    lines = [
        "# Phase57 LONG-only CURRENT Entry Filter Recovery Audit",
        "",
        f"**Verdict: {verdict['verdict']}**",
        "",
        "This is a descriptive pre-development audit on the same already-opened 76 Development sessions. "
        "No Selector or CURRENT Entry decision, model, feature, coefficient, threshold, state rule, Validation/OOS, "
        "EXIT, allocation, or order path was changed.",
        "",
        "## Funnel",
        "",
        "| Status | Count | Rate |",
        "|---|---:|---:|",
    ]
    for status, row in report["funnel"].items():
        lines.append(f"| {status} | {row['count']:,} | {row['ratePct']:.2f}% |")
    lines += ["", "## BLOCKED root causes", "",
              "| Canonical reason | Count | All events | +1 | +2 | +3 | +5 | MFE mean | true MAE mean |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in report["blockedRootCauseAttribution"]:
        quality = row["quality"]
        lines.append(
            f"| {row['reason']} | {row['count']:,} | {row['rateOfAllEventsPct']:.2f}% | "
            f"{quality['opportunity']['1']['precisionPct']:.2f}% | {quality['opportunity']['2']['precisionPct']:.2f}% | "
            f"{quality['opportunity']['3']['precisionPct']:.2f}% | {quality['opportunity']['5']['precisionPct']:.2f}% | "
            f"{quality['selectorMfePct']['mean']:.3f}% | {quality['selectorTrueMaePct']['mean']:.3f}% |")
    lines += ["", "## Lost opportunity attribution", "",
              "| Source | +1 | +2 | +3 | +5 |",
              "|---|---:|---:|---:|---:|"]
    sources = sorted({key for level in LEVELS for key in report["lostOpportunityAttribution"][str(level)]["eventBasedBySource"]})
    for source in sources:
        lines.append("| " + source + " | " + " | ".join(
            f"{report['lostOpportunityAttribution'][str(level)]['eventBasedBySource'].get(source, 0):,}"
            for level in LEVELS) + " |")
    lines += ["", "## Opportunity throughput", "",
              "| Measure | Total | Per session mean | Per session median |",
              "|---|---:|---:|---:|"]
    for key, row in report["throughput"]["measures"].items():
        lines.append(f"| {key} | {row['total']:,} | {row['perSession']['mean']:.3f} | {row['perSession']['median']:.3f} |")
    lines += ["", "## Mismatch components", ""]
    for key, value in verdict["components"].items():
        lines.append(f"- {key}: `{value['triggered']}` — {value['evidence']}")
    lines += ["", "## MSH-Entry LONG v1 design requirements (requirements only)", ""]
    for section, values in report["designRequirements"].items():
        lines.append(f"### {section}")
        lines.append("")
        lines.extend(f"- {value}" for value in values)
        lines.append("")
    lines += ["STOP: no MSH-Entry LONG v1 architecture, target, feature, model, coefficient, threshold, or WAIT rule was created.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--prior-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown-output", required=True)
    args = parser.parse_args()

    source = Path(args.input_dir)
    contract_bytes = Path(args.contract).read_bytes()
    contract = json.loads(contract_bytes)
    prior_report_bytes = Path(args.prior_report).read_bytes()
    prior_report = json.loads(prior_report_bytes)
    manifest = json.loads((source / "input-manifest.json").read_text())
    event_bytes = (source / "selector-current-entry-events.ndjson").read_bytes()
    tick_bytes = (source / "entry-evaluation-ticks.ndjson").read_bytes()
    events = pd.read_json(StringIO(event_bytes.decode()), lines=True, convert_dates=False)
    ticks = [json.loads(line) for line in tick_bytes.decode().splitlines() if line]
    opportunities = json.loads((source / "first-entry-opportunities.json").read_text())
    opportunity_by_symbol_session = {row["symbolSessionId"]: row for row in opportunities}

    frozen = contract["frozenInputs"]
    integrity_failures = []
    checks = {
        "sessions76": bool(events.sessionDate.nunique() == 76),
        "decisionTimestamps760": bool(events[["sessionDate", "decisionTimestamp"]].drop_duplicates().shape[0] == 760),
        "selectionEvents3800": bool(len(events) == 3800),
        "firstEntryCandidates2743": bool(len(opportunities) == 2743),
        "longOnlyEvents": bool(events.direction.eq("LONG").all() and events.shortScoreEvaluated.eq(False).all()),
        "longOnlyTicks": bool(all(row["direction"] == "LONG" and row["shortScoreEvaluated"] is False for row in ticks)),
        "scoredTicksPresent": bool(sum(finite(row.get("probability")) for row in ticks) > 0),
        "priorTransferReportPinned": bool(hashlib.sha256(prior_report_bytes).hexdigest() == frozen["priorTransferReportFileSha256"]),
        "priorTransferLedgerPayloadPinned": bool(hashlib.sha256(event_bytes).hexdigest() == frozen["priorTransferLedgerPayloadSha256"]),
        "priorTransferContractPinned": bool(prior_report["contractSha256"] == frozen["priorTransferContractSha256"]),
        "selectorFreezeUnchanged": bool(manifest["source"]["frozenSelectorFreezeCommit"] == frozen["selectorFreezeCommit"]),
        "selectorArtifactUnchanged": bool(manifest["source"]["frozenSelectorArtifactSha256"] == frozen["selectorRidgeArtifactSha256"]),
        "currentEntryModelUnchanged": bool(manifest["source"]["currentEntryModelSha256"] == frozen["currentEntryModelSha256"]),
        "currentEntryFeatureContractUnchanged": bool(manifest["source"]["currentEntryFeatureContractSha256"] == frozen["currentEntryFeatureContractSha256"]),
        "currentEntryFeatureImplementationUnchanged": bool(manifest["source"]["currentEntryFeatureImplementationSha256"] == frozen["currentEntryFeatureImplementationSha256"]),
    }
    integrity_failures.extend(key for key, value in checks.items() if not value)

    events["timeBand"] = events.decisionTimeJst.map(lambda value: time_band(value, contract))
    funnel = {}
    for status in STATUSES:
        group = events[events.directStatus.eq(status)]
        funnel[status] = {"count": int(len(group)), "ratePct": ratio(len(group), len(events), 100),
                          "uniqueSymbols": int(group.symbol.nunique()), "uniqueSymbolSessions": int(group.symbolSessionId.nunique()),
                          "sessions": int(group.sessionDate.nunique())}

    pass_events = events[events.directStatus.eq("PASS")]
    pass_quality = opportunity_metrics(pass_events)
    blocked = events[events.directStatus.eq("BLOCKED")].copy()
    blocked["reasonClass"] = blocked.directReason.map(lambda value: canonical_class(value, contract))
    blocked_rows = []
    for reason, group in blocked.groupby("directReason", sort=False):
        quality = opportunity_metrics(group)
        blocked_rows.append({
            "reason": str(reason), "reasonClass": canonical_class(reason, contract), "count": int(len(group)),
            "rateOfAllEventsPct": ratio(len(group), len(events), 100),
            "rateOfBlockedPct": ratio(len(group), len(blocked), 100),
            "uniqueSymbols": int(group.symbol.nunique()), "uniqueSymbolSessions": int(group.symbolSessionId.nunique()),
            "sessions": int(group.sessionDate.nunique()),
            "timeOfDay": {str(key): int(value) for key, value in group.decisionTimeJst.value_counts().sort_index().items()},
            "timeBands": {str(key): int(value) for key, value in group.timeBand.value_counts().sort_index().items()},
            "quality": quality,
            "vsPassPrecisionDeltaPercentagePoints": {
                str(level): number(quality["opportunity"][str(level)]["precisionPct"]-pass_quality["opportunity"][str(level)]["precisionPct"])
                for level in LEVELS},
            "opportunityCountDespiteBlock": {str(level): quality["opportunity"][str(level)]["hitN"] for level in LEVELS},
        })
    blocked_rows.sort(key=lambda row: (-row["count"], row["reason"]))

    lost = {}
    first_events = events[events.isFirstSelection.eq(True)].copy()
    for level in LEVELS:
        event_hits = events[pd.to_numeric(events[f"selectorOpportunity{level}"], errors="coerce").eq(1)]
        event_lost = event_hits[event_hits.finalOpportunityStatus.ne("PASS")].copy()
        event_lost["source"] = event_lost.apply(
            lambda row: f"BLOCKED:{row.directReason}" if row.directStatus == "BLOCKED"
            else f"{row.directStatus}:{row.directReason}", axis=1)
        first_hits = first_events[pd.to_numeric(first_events[f"selectorOpportunity{level}"], errors="coerce").eq(1)]
        first_lost = first_hits[first_hits.finalOpportunityStatus.ne("PASS")].copy()
        first_lost["source"] = first_lost.apply(
            lambda row: f"BLOCKED:{row.directReason}" if row.directStatus == "BLOCKED"
            else f"{row.directStatus}:{row.directReason}", axis=1)
        lost[str(level)] = {
            "eventSelectorHitN": int(len(event_hits)), "eventLostN": int(len(event_lost)),
            "eventLostRatePct": ratio(len(event_lost), len(event_hits), 100),
            "eventBasedBySource": {str(key): int(value) for key, value in event_lost.source.value_counts().items()},
            "firstEntrySelectorHitN": int(len(first_hits)), "firstEntryLostN": int(len(first_lost)),
            "firstEntryLostRatePct": ratio(len(first_lost), len(first_hits), 100),
            "firstEntryUniqueBySource": {str(key): int(value) for key, value in first_lost.source.value_counts().items()},
        }

    ticks_by_symbol = defaultdict(list)
    for row in ticks:
        ticks_by_symbol[row["symbolSessionId"]].append(row)
    for rows in ticks_by_symbol.values():
        rows.sort(key=lambda value: value["evaluationTimestamp"])

    wait_events = events[events.directStatus.eq("WAIT")].copy()
    wait_primary = []
    wait_flags = Counter()
    for index, row in wait_events.iterrows():
        future_ticks = [tick for tick in ticks_by_symbol[row.symbolSessionId]
                        if tick["evaluationTimestamp"] >= row.decisionTimestamp]
        later_pass = bool(row.entryAfterThisSelectorEvent)
        later_block = any(tick["status"] == "BLOCKED" for tick in future_ticks)
        opportunity = opportunity_by_symbol_session[row.symbolSessionId]
        terminal = opportunity.get("expiredReason")
        if later_pass:
            primary = "WAIT_TO_LATER_PASS"
        elif later_block:
            primary = "WAIT_TO_BLOCKED_NEVER_PASS"
        elif terminal == "SESSION_CLOSE":
            primary = "WAIT_TO_SESSION_END"
        else:
            primary = "WAIT_TO_REJECT"
        wait_primary.append((index, primary))
        wait_flags["WAIT_TO_LATER_PASS"] += int(later_pass)
        wait_flags["WAIT_TO_NEVER_PASS"] += int(not later_pass)
        wait_flags["WAIT_TO_BLOCKED"] += int(later_block)
        wait_flags["WAIT_TO_REJECT"] += int(not later_pass and terminal == "NOT_SELECTED_ON_NEXT_COMPLETE_FROZEN_SELECTOR_DECISION")
        wait_flags["WAIT_TO_SESSION_END"] += int(not later_pass and terminal == "SESSION_CLOSE")
    wait_events["transition"] = pd.Series(dict(wait_primary))
    wait_transition = {
        "selectionEvents": int(len(wait_events)),
        "nonExclusiveTransitionCounts": dict(wait_flags),
        "primaryMutuallyExclusive": {
            name: {"count": int(len(group)), "ratePct": ratio(len(group), len(wait_events), 100),
                   "quality": opportunity_metrics(group),
                   "score": {"probability": distribution(group.longProbability),
                             "thresholdDistance": distribution(pd.to_numeric(group.longProbability, errors="coerce")-.6)}}
            for name, group in wait_events.groupby("transition")
        },
    }

    reject_events = events[events.directStatus.eq("REJECT")]
    reject_sessions = set(reject_events.symbolSessionId)
    reject_prior_ticks = latest_score_ready_ticks(ticks, reject_sessions)
    reject_attribution = {
        "quality": opportunity_metrics(reject_events),
        "reasons": {str(key): int(value) for key, value in reject_events.directReason.value_counts().items()},
        "stateSemantics": "REJECT_IS_TERMINAL_EXPIRED_RESELECTION_NOT_AN_IMMEDIATE_MODEL_REJECT",
        "lastPriorScoreReadyTickCoverage": ratio(len(reject_prior_ticks), len(reject_sessions)),
        "lastPriorScoreReady": score_snapshot(reject_prior_ticks),
    }

    passed_ticks = first_pass_ticks(ticks)
    never_pass_sessions = {row["symbolSessionId"] for row in opportunities if row["finalStatus"] != "PASS"}
    never_pass_last_ticks = latest_score_ready_ticks(ticks, never_pass_sessions)
    feature_comparison = contribution_comparison(passed_ticks, never_pass_last_ticks)
    pass_enrichment = {
        "priorMeasuredEnrichment": prior_report["entryEnrichment"],
        "firstPassTicks": len(passed_ticks),
        "neverPassLastScoreReadyTicks": len(never_pass_last_ticks),
        "scoreComparison": {
            "firstPass": score_snapshot(passed_ticks),
            "neverPassLastScoreReady": score_snapshot(never_pass_last_ticks),
        },
        "featureAndFrozenContributionComparison": feature_comparison,
        "interpretationBoundary": "DESCRIPTIVE_EXISTING_FEATURE_ATTRIBUTION_NOT_FEATURE_SELECTION_OR_CAUSAL_IMPORTANCE",
    }

    attempted_event = events[events.directStatus.isin(["WAIT", "BLOCKED"]) |
                             ((events.directStatus == "PASS") & (events.directReason == "LONG_ABOVE_FROZEN_THRESHOLD"))]
    ready_event = attempted_event[attempted_event.directStatus.isin(["WAIT", "PASS"])]
    scored_ticks = [row for row in ticks if finite(row.get("probability"))]
    blocked_ticks = [row for row in ticks if row["status"] in ["BLOCKED", "UNAVAILABLE"]]
    tick_reasons = Counter(row["reason"] for row in blocked_ticks)
    feature_availability = {
        "atomicContractSemantics": "ALL_TEN_FEATURES_SHARE_ONE_FAIL_CLOSED_ROW_AVAILABILITY_GATE",
        "selectionEventAttemptedN": int(len(attempted_event)), "selectionEventReadyN": int(len(ready_event)),
        "selectionEventAvailabilityRatePct": ratio(len(ready_event), len(attempted_event), 100),
        "selectionEventMissingRatePct": ratio(len(attempted_event)-len(ready_event), len(attempted_event), 100),
        "tickAttemptedN": len(ticks), "tickScoreReadyN": len(scored_ticks),
        "tickAvailabilityRatePct": ratio(len(scored_ticks), len(ticks), 100),
        "tickMissingRatePct": ratio(len(ticks)-len(scored_ticks), len(ticks), 100),
        "tickBlockedReasons": dict(tick_reasons),
        "perFeature": {feature: {"availabilityRatePct": ratio(len(scored_ticks), len(ticks), 100),
                                 "missingRatePct": ratio(len(ticks)-len(scored_ticks), len(ticks), 100),
                                 "blockedContribution": "SHARED_CANONICAL_PREFIX_GATE"}
                       for feature in FEATURES},
        "timeOfDay": grouped_status_and_opportunity(events, "timeBand", list(contract["timeOfDayBandsJst"])),
        "segment": grouped_status_and_opportunity(events, "segment", ["PRIME", "STANDARD", "GROWTH"]),
        "liquidity": grouped_status_and_opportunity(events, "liquidityBucket", ["LOW", "MID", "HIGH"]),
    }

    descriptive = {
        "timeOfDay": feature_availability["timeOfDay"],
        "segment": feature_availability["segment"],
        "liquidity": feature_availability["liquidity"],
        "rank": grouped_status_and_opportunity(events, "ridgeRank", [1, 2, 3, 4, 5]),
    }

    per_session = {}
    for session, group in first_events.groupby("sessionDate"):
        row = {"firstEntryCandidates": int(len(group)), "pass": int(group.finalOpportunityStatus.eq("PASS").sum())}
        for level in LEVELS:
            row[f"preserved{level}"] = int((group.finalOpportunityStatus.eq("PASS") &
                                             pd.to_numeric(group[f"selectorOpportunity{level}"], errors="coerce").eq(1)).sum())
        per_session[str(session)] = row
    throughput_measures = {}
    for key in ["firstEntryCandidates", "pass", "preserved1", "preserved2", "preserved3", "preserved5"]:
        values = [row[key] for row in per_session.values()]
        throughput_measures[key] = {"total": int(sum(values)), "perSession": distribution(values)}
    throughput = {"sessions": 76, "measures": throughput_measures, "perSession": per_session}

    selector_quality = opportunity_metrics(events)
    first_pass_events = first_events[first_events.finalOpportunityStatus.eq("PASS")]
    frontier = {
        "selectorOnly": {
            "selectionEvents": int(len(events)), "eventsPerSession": ratio(len(events), 76),
            "opportunityPreservationPct": {str(level): 100.0 for level in LEVELS},
            "precisionPct": {str(level): selector_quality["opportunity"][str(level)]["precisionPct"] for level in LEVELS},
        },
        "currentDirectPass": {
            "selectionEvents": int(len(pass_events)), "eventsPerSession": ratio(len(pass_events), 76),
            "opportunityPreservationPct": {str(level): prior_report["opportunityPreservation"][str(level)]["directPassPreservationPct"] for level in LEVELS},
            "precisionPct": {str(level): pass_quality["opportunity"][str(level)]["precisionPct"] for level in LEVELS},
        },
        "currentFirstEntryFinalPass": {
            "symbolSessions": int(len(first_pass_events)), "symbolSessionsPerSession": ratio(len(first_pass_events), 76),
            "coveragePct": ratio(len(first_pass_events), len(first_events), 100),
            "precisionPct": {str(level): opportunity_metrics(first_pass_events)["opportunity"][str(level)]["precisionPct"] for level in LEVELS},
        },
        "noIntermediatePointFitted": True,
    }

    recoverable = {}
    for level in LEVELS:
        event_hits = events[(events.finalOpportunityStatus.ne("PASS")) &
                            pd.to_numeric(events[f"selectorOpportunity{level}"], errors="coerce").eq(1)]
        first_hits = first_events[(first_events.finalOpportunityStatus.ne("PASS")) &
                                  pd.to_numeric(first_events[f"selectorOpportunity{level}"], errors="coerce").eq(1)]
        recoverable[str(level)] = {
            "selectionEventUpperBoundN": int(len(event_hits)),
            "uniqueFirstEntryCandidateUpperBoundN": int(len(first_hits)),
            "byDirectStatusSelectionEvents": {str(key): int(value) for key, value in event_hits.directStatus.value_counts().items()},
            "notAchievablePerformance": True,
        }

    baseline3 = selector_quality["opportunity"]["3"]["precisionPct"] / 100
    blocked3 = opportunity_metrics(blocked)["opportunity"]["3"]["precisionPct"] / 100
    reject3 = opportunity_metrics(reject_events)["opportunity"]["3"]["precisionPct"] / 100
    wait_lost3 = int(((events.directStatus == "WAIT") & events.finalOpportunityStatus.ne("PASS") &
                      pd.to_numeric(events.selectorOpportunity3, errors="coerce").eq(1)).sum())
    all3 = int(pd.to_numeric(events.selectorOpportunity3, errors="coerce").eq(1).sum())
    rules = contract["architectureMismatchVerdictRule"]
    first_coverage = len(first_pass_events)/len(first_events)
    model_trigger = (first_coverage < rules["MODEL_FILTER_TOO_STRICT"]["firstEntryPassCoverageBelow"] and
                     wait_lost3/all3 >= rules["MODEL_FILTER_TOO_STRICT"]["waitLost3ShareOfAllSelector3HitsAtLeast"])
    feature_trigger = (len(blocked)/len(events) >= rules["FEATURE_AVAILABILITY_TOO_STRICT"]["blockedSelectionEventRateAtLeast"] and
                       blocked3 >= baseline3*rules["FEATURE_AVAILABILITY_TOO_STRICT"]["blocked3PrecisionAtLeastFractionOfSelectorBaseline"])
    state_trigger = (len(reject_events)/len(events) >= rules["STATE_FILTER_TOO_STRICT"]["rejectSelectionEventRateAtLeast"] and
                     reject3 >= baseline3*rules["STATE_FILTER_TOO_STRICT"]["reject3PrecisionAtLeastFractionOfSelectorBaseline"])
    components = {
        "MODEL_FILTER_TOO_STRICT": {"triggered": bool(model_trigger),
            "evidence": f"first-entry coverage={100*first_coverage:.2f}%; WAIT-lost +3 share={100*wait_lost3/all3:.2f}%"},
        "FEATURE_AVAILABILITY_TOO_STRICT": {"triggered": bool(feature_trigger),
            "evidence": f"BLOCKED rate={100*len(blocked)/len(events):.2f}%; BLOCKED +3 precision={100*blocked3:.2f}%"},
        "STATE_FILTER_TOO_STRICT": {"triggered": bool(state_trigger),
            "evidence": f"REJECT rate={100*len(reject_events)/len(events):.2f}%; REJECT +3 precision={100*reject3:.2f}%"},
    }
    triggered = [key for key, value in components.items() if value["triggered"]]
    if integrity_failures:
        verdict = "E.INCONCLUSIVE"
    elif len(triggered) >= 2:
        verdict = "D.MULTIPLE"
    elif len(triggered) == 1:
        verdict = {"MODEL_FILTER_TOO_STRICT": "A.MODEL_FILTER_TOO_STRICT",
                   "FEATURE_AVAILABILITY_TOO_STRICT": "B.FEATURE_AVAILABILITY_TOO_STRICT",
                   "STATE_FILTER_TOO_STRICT": "C.STATE_FILTER_TOO_STRICT"}[triggered[0]]
    else:
        verdict = "E.INCONCLUSIVE"

    design_requirements = {
        "MUST_PRESERVE": [
            "LONG-only JPX cash-equity direction with SHORT, margin and leverage absent.",
            "Frozen Selector Decision Price semantics, PIT feature availability and no future bars.",
            "Fast decisions: the existing Entry median first-PASS latency is 0 minutes and must not regress.",
            "The observed enrichment signal across +1/+2/+3/+5, not +5 alone.",
            "State safety, single entry per symbol-session, cost awareness and all execution locks.",
        ],
        "MUST_IMPROVE": [
            "First-entry coverage above the current 3.50% while measuring precision, preservation and throughput together.",
            "Evidence-backed tolerance for missing session-open or non-consecutive 5m history; do not assume Selector freshness implies Entry feature availability.",
            "Opportunity preservation at +1, +2, +3 and +5, with +3 primary but not exclusive.",
            "Low- and mid-liquidity feature availability without segment or liquidity-specific thresholds.",
            "Explicit accounting for WAIT-to-expiry and terminal state loss.",
        ],
        "MUST_NOT": [
            "Optimize only +5 precision or call the descriptive recoverable pool achievable performance.",
            "Reuse SHORT scores, targets, coefficients or fallback behavior.",
            "Require unavailable history without demonstrated value, impute missing bars, or use future information.",
            "Tune thresholds, select features, redesign WAIT, or fit architecture from this audit.",
            "Open Validation/OOS or change Selector, EXIT, Capital Allocation, portfolio or order paths.",
        ],
    }

    report = {
        "schemaVersion": 1, "status": "CURRENT_ENTRY_FILTER_RECOVERY_AUDIT_COMPLETE_STOP",
        "contractId": contract["contractId"], "contractSha256": hashlib.sha256(contract_bytes).hexdigest(),
        "source": manifest["source"], "priorEvidence": {
            "transferReportFileSha256": hashlib.sha256(prior_report_bytes).hexdigest(),
            "transferEventLedgerPayloadSha256": hashlib.sha256(event_bytes).hexdigest(),
            "sameOpenedDevelopmentReused": True, "newProviderRequests": 0, "validationOpened": False, "oosOpened": False,
        },
        "integrity": {"pass": not integrity_failures, "checks": checks, "failures": integrity_failures,
                      "selectionEvents": len(events), "entryEvaluationTicks": len(ticks),
                      "scoredEntryTicks": len(scored_ticks), "firstEntryCandidates": len(opportunities)},
        "safety": contract["safety"], "funnel": funnel, "passReferenceQuality": pass_quality,
        "blockedRootCauseAttribution": blocked_rows, "lostOpportunityAttribution": lost,
        "waitTransitionAttribution": wait_transition, "rejectAttribution": reject_attribution,
        "passEnrichmentAttribution": pass_enrichment, "featureAvailabilityAudit": feature_availability,
        "descriptiveDiagnosis": descriptive, "throughput": throughput,
        "precisionPreservationFrontier": frontier, "recoverableOpportunityPool": recoverable,
        "architectureMismatchVerdict": {"verdict": verdict, "components": components,
                                         "integrityFailures": integrity_failures},
        "designRequirements": design_requirements,
        "targetPhilosophyCandidatesForIndependentReview": {
            "decision": "NOT_SELECTED_IN_THIS_AUDIT",
            "binary": "Future +X positive; simple but risks one-threshold tunnel vision.",
            "ordinal": "+1/+2/+3/+5 opportunity levels; preserves magnitude ordering but needs censoring semantics.",
            "continuous": "Remaining upside, expected return or MFE-related value; richer but calibration-sensitive.",
            "multiObjective": "Preservation x Quality x Throughput; closest to the observed failure but requires an explicit utility contract.",
        },
        "limitations": [
            "Same cross-era Development transfer limitation as the prior diagnostic.",
            "Opportunity pools are descriptive upper bounds and may overlap across thresholds and repeated selections.",
            "Existing-feature contribution comparisons describe the frozen linear logit, not causal feature value.",
            "No requirement-removal simulation, threshold counterfactual or replacement Entry was run.",
        ],
        "stopBoundary": contract["completionBoundary"],
    }
    core = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    report["reportSha256"] = hashlib.sha256(core).hexdigest()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.markdown_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)+"\n")
    Path(args.markdown_output).write_text(markdown(report))
    print(json.dumps({"status": report["status"], "verdict": verdict, "reportSha256": report["reportSha256"],
                      "events": len(events), "ticks": len(ticks), "scoredTicks": len(scored_ticks)}))


if __name__ == "__main__":
    main()
