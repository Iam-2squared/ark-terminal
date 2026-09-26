#!/usr/bin/env python3
"""Aggregate the frozen Selector -> frozen CURRENT Entry LONG-only transfer diagnostic."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


THRESHOLDS = [1, 2, 3, 5]
STATUSES = ["PASS", "REJECT", "WAIT", "BLOCKED", "UNAVAILABLE"]
BASELINE = {1: 76.3852242744, 2: 61.2928759894, 3: 47.2559366755, 5: 24.9868073879}


def number(value):
    return round(float(value), 10) if value is not None and np.isfinite(value) else None


def ratio(numerator, denominator, scale=1):
    return number(scale * numerator / denominator) if denominator else None


def distribution(values):
    clean = pd.to_numeric(pd.Series(values), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().to_numpy(float)
    if not len(clean):
        return {"n": 0, **{name: None for name in ["mean", "min", "p25", "median", "p75", "p90", "max"]}}
    return {"n": len(clean), "mean": number(clean.mean()), "min": number(clean.min()),
            "p25": number(np.quantile(clean, .25)), "median": number(np.quantile(clean, .5)),
            "p75": number(np.quantile(clean, .75)), "p90": number(np.quantile(clean, .90)), "max": number(clean.max())}


def precision(frame, prefix, level):
    values = pd.to_numeric(frame[f"{prefix}{level}"], errors="coerce")
    valid = values.isin([0, 1])
    return {"evaluableN": int(valid.sum()), "hitN": int(values[valid].eq(1).sum()),
            "precisionPct": ratio(int(values[valid].eq(1).sum()), int(valid.sum()), 100)}


def cohort(frame):
    result = {"selectionEvents": len(frame), "uniqueSymbols": int(frame.symbol.nunique()),
              "uniqueSymbolSessions": int(frame.symbolSessionId.nunique()),
              "decisionTimestamps": int(frame[["sessionDate", "decisionTimestamp"]].drop_duplicates().shape[0]),
              "selectorTime": {}, "entryTime": {}}
    for level in THRESHOLDS:
        result["selectorTime"][str(level)] = precision(frame, "selectorOpportunity", level)
        eligible = frame[frame.entryAfterThisSelectorEvent.eq(True)]
        result["entryTime"][str(level)] = precision(eligible, "entryOpportunity", level)
    result["selectorMfePct"] = distribution(frame.selectorMfePct)
    result["selectorTrueMaePct"] = distribution(frame.selectorMaePct)
    relative = frame[frame.entryAfterThisSelectorEvent.eq(True)]
    result["entryMfePct"] = distribution(relative.entryMfePct)
    result["entryTrueMaePct"] = distribution(relative.entryMaePct)
    return result


def opportunity_precision(rows, prefix, level):
    values = []
    for row in rows:
        source = row.get(prefix) or {}
        value = source.get(f"opportunity{level}")
        if value in (0, 1):
            values.append(int(value))
    return {"evaluableN": len(values), "hitN": sum(values), "precisionPct": ratio(sum(values), len(values), 100)}


def opportunity_distribution(rows, key):
    return distribution([row.get(key) for row in rows])


def latency_report(opportunities, first_event):
    output = {}
    passed = [row for row in opportunities if row["finalStatus"] == "PASS"]
    for bucket in ["0_TO_5", "GT5_TO_10", "GT10_TO_20", "GT20_TO_30", "GT30"]:
        rows = [row for row in passed if row.get("latencyBucket") == bucket]
        status_counts = {status: 0 for status in STATUSES}
        for row in rows:
            status = first_event[row["firstSelectorEventId"]]["directStatus"]
            status_counts[status] += 1
        output[bucket] = {"N": len(rows), "initialDirectStatus": status_counts,
                          "selectorTime": {str(level): opportunity_precision(rows, "firstSelectorOutcome", level) for level in THRESHOLDS},
                          "entryTime": {str(level): opportunity_precision(rows, "entryOutcome", level) for level in THRESHOLDS},
                          "consumedReturnBps": opportunity_distribution(rows, "consumedReturnBps"),
                          "entryMfePct": distribution([(row.get("entryOutcome") or {}).get("mfePct") for row in rows]),
                          "entryTrueMaePct": distribution([(row.get("entryOutcome") or {}).get("maePct") for row in rows])}
    return output


def preservation(events):
    output = {}
    for level in THRESHOLDS:
        values = pd.to_numeric(events[f"selectorOpportunity{level}"], errors="coerce")
        hits = events[values.eq(1)]
        final_pass = int(hits.finalOpportunityStatus.eq("PASS").sum())
        direct_pass = int(hits.directStatus.eq("PASS").sum())
        output[str(level)] = {"selectorHitN": len(hits), "eventuallyPassedN": final_pass,
                              "opportunityPreservationRate": ratio(final_pass, len(hits)),
                              "opportunityPreservationPct": ratio(final_pass, len(hits), 100),
                              "directPassN": direct_pass, "directPassPreservationPct": ratio(direct_pass, len(hits), 100)}
    return output


def grouped_funnel(events, field, values):
    output = {}
    for value in values:
        group = events[events[field].eq(value)]
        output[value] = {"selectionEvents": len(group), "statuses": {status: int(group.directStatus.eq(status).sum()) for status in STATUSES}}
    return output


def verdict(events, opportunities, report, contract):
    rules = contract["verdictRule"]
    integrity = (len(events) == rules["minimumSelectorEvents"]
                 and events[["sessionDate", "decisionTimestamp"]].drop_duplicates().shape[0] == rules["minimumDecisionTimestamps"]
                 and events.sessionDate.nunique() == rules["minimumDevelopmentSessions"])
    passed = [row for row in opportunities if row["finalStatus"] == "PASS"]
    entry_coverage = ratio(sum(bool(row.get("entryOutcomeEvaluable")) for row in passed), len(passed)) if passed else None
    preservation3 = report["opportunityPreservation"]["3"]["opportunityPreservationRate"]
    preservation5 = report["opportunityPreservation"]["5"]["opportunityPreservationRate"]
    first_coverage = ratio(len(passed), len(opportunities))
    direct_pass = events[events.directStatus.eq("PASS")]
    wait_reject = events[events.directStatus.isin(["WAIT", "REJECT"])]
    pass3 = precision(direct_pass, "selectorOpportunity", 3)["precisionPct"]
    pass5 = precision(direct_pass, "selectorOpportunity", 5)["precisionPct"]
    other3 = precision(wait_reject, "selectorOpportunity", 3)["precisionPct"]
    other5 = precision(wait_reject, "selectorOpportunity", 5)["precisionPct"]
    reverse_both = all(value is not None for value in [pass3, pass5, other3, other5]) and other3-pass3 >= 5 and other5-pass5 >= 5
    filter_signals = {
        "opportunityPreservation3Below60Pct": preservation3 is not None and preservation3 < rules["filterProblemIfAny"]["opportunityPreservation3PctBelow"],
        "opportunityPreservation5Below60Pct": preservation5 is not None and preservation5 < rules["filterProblemIfAny"]["opportunityPreservation5PctBelow"],
        "symbolSessionFirstEntryCoverageBelow20Pct": first_coverage is not None and first_coverage < rules["filterProblemIfAny"]["symbolSessionFirstEntryCoverageBelow"],
        "waitOrRejectBeatsPassAtBoth3And5By5pp": reverse_both,
    }
    filter_problem = any(filter_signals.values())

    pass_latency = [row.get("latencyMinutes") for row in passed]
    median_latency = distribution(pass_latency)["median"]
    median_consumed = distribution([row.get("consumedReturnBps") for row in passed])["median"]
    def retention(level):
        source = [row for row in passed if (row.get("firstSelectorOutcome") or {}).get(f"opportunity{level}") == 1]
        remaining = sum((row.get("entryOutcome") or {}).get(f"opportunity{level}") == 1 for row in source)
        return ratio(remaining, len(source))
    retention3, retention5 = retention(3), retention(5)
    latency_signals = {
        "medianFirstPassLatencyAbove10Min": median_latency is not None and median_latency > rules["latencyProblemIfAny"]["medianFirstPassLatencyMinutesAbove"],
        "entryTimeRemaining3RetentionBelow75Pct": retention3 is not None and retention3 < rules["latencyProblemIfAny"]["entryTimeRemaining3PctRetentionBelow"],
        "entryTimeRemaining5RetentionBelow75Pct": retention5 is not None and retention5 < rules["latencyProblemIfAny"]["entryTimeRemaining5PctRetentionBelow"],
        "medianConsumedReturnAbove50Bps": median_consumed is not None and median_consumed > rules["latencyProblemIfAny"]["medianConsumedReturnBpsAbove"],
    }
    latency_problem = any(latency_signals.values())
    inconclusive_reasons = []
    if not integrity: inconclusive_reasons.append("INTEGRITY_COUNT_MISMATCH")
    scored_ticks = sum(row.get("scoredTicks", 0) for row in report["sessionAudits"])
    if scored_ticks == 0: inconclusive_reasons.append("ZERO_SCORABLE_CURRENT_ENTRY_TICKS")
    if entry_coverage is not None and entry_coverage < .90: inconclusive_reasons.append("ENTRY_OUTCOME_COVERAGE_BELOW_0_90")
    if len(passed) < rules["minimumEntryPassesForEnrichmentComparison"] and not filter_problem:
        inconclusive_reasons.append("PASS_COUNT_BELOW_MINIMUM_FOR_ENRICHMENT_AND_NO_FILTER_COVERAGE_FAILURE")
    if inconclusive_reasons:
        final = "INCONCLUSIVE"
    elif filter_problem and latency_problem:
        final = "CURRENT_ENTRY_BOTH_FILTER_AND_LATENCY_PROBLEM"
    elif filter_problem:
        final = "CURRENT_ENTRY_FILTER_PROBLEM"
    elif latency_problem:
        final = "CURRENT_ENTRY_LATENCY_PROBLEM"
    else:
        final = "CURRENT_ENTRY_WORKS"
    return {"verdict": final, "integrityCountsPass": integrity, "entryOutcomeCoverage": entry_coverage,
            "firstEntryOpportunityCoverage": first_coverage, "passedSymbolSessions": len(passed),
            "filterProblem": filter_problem, "filterSignals": filter_signals,
            "latencyProblem": latency_problem, "latencySignals": latency_signals,
            "medianFirstPassLatencyMinutes": median_latency, "medianConsumedReturnBps": median_consumed,
            "entryTimeRemainingRetention": {"3": retention3, "5": retention5},
            "directSelectorPrecisionPct": {"PASS": {"3": pass3, "5": pass5}, "WAIT_OR_REJECT": {"3": other3, "5": other5}},
            "inconclusiveReasons": inconclusive_reasons}


def markdown(report):
    v = report["finalVerdict"]
    f = report["funnel"]
    p = report["opportunityPreservation"]
    lines = ["# Phase57 LONG-only Frozen Selector v1 × CURRENT Entry transfer diagnostic", "",
             f"**Final verdict: `{v['verdict']}`**", "",
             "## Scope and integrity", "",
             "- JPX cash equity, LONG-only. SHORT scores, margin and leverage were not used.",
             "- Frozen Selector and CURRENT Entry weights/threshold/features were read only; fit calls: 0.",
             f"- Development only: {report['dataAudit']['sessions']} sessions, {report['dataAudit']['decisionTimestamps']} timestamps, {report['dataAudit']['selectionEvents']} Top5 events.",
             "- Validation/OOS remained sealed. EXIT and Capital Allocation were not used.", "",
             "## Funnel", "",
             "| Status | Events | Rate |", "|---|---:|---:|"]
    for status in STATUSES:
        row = f[status]
        lines.append(f"| {status} | {row['count']} | {row['ratePct']:.2f}% |")
    lines += ["", "CURRENT Entry has no immediate REJECT label; REJECT appears only after terminal EXPIRED state and later reselection.", "",
              "## Primary diagnostics", "", "| Metric | Value |", "|---|---:|",
              f"| First-entry symbol-session coverage | {100*v['firstEntryOpportunityCoverage']:.2f}% |",
              f"| +3 opportunity preservation | {p['3']['opportunityPreservationPct']:.2f}% |",
              f"| +5 opportunity preservation | {p['5']['opportunityPreservationPct']:.2f}% |",
              f"| Median first-pass latency | {v['medianFirstPassLatencyMinutes'] if v['medianFirstPassLatencyMinutes'] is not None else 'N/A'} min |",
              f"| Median consumed return | {v['medianConsumedReturnBps'] if v['medianConsumedReturnBps'] is not None else 'N/A'} bps |",
              f"| Entry-time +3 remaining retention | {100*v['entryTimeRemainingRetention']['3']:.2f}% |" if v['entryTimeRemainingRetention']['3'] is not None else "| Entry-time +3 remaining retention | N/A |",
              f"| Entry-time +5 remaining retention | {100*v['entryTimeRemainingRetention']['5']:.2f}% |" if v['entryTimeRemainingRetention']['5'] is not None else "| Entry-time +5 remaining retention | N/A |",
              "", "## Verdict basis", ""]
    lines.append(f"- Filter problem: `{v['filterProblem']}` — " + ", ".join(key for key, value in v["filterSignals"].items() if value))
    lines.append(f"- Latency problem: `{v['latencyProblem']}` — " + ", ".join(key for key, value in v["latencySignals"].items() if value))
    lines += ["", "This is a cross-era Development transfer diagnostic, not a Validation/OOS or causal historical performance claim. MSH_ENTRY_V1 was trained after the Selector Development dates, but its saved weights are applied without fitting and without using these Selector outcomes.", "",
              "STOP: no new LONG Entry, threshold, feature, model or WAIT redesign is created by this result.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown-output", required=True)
    parser.add_argument("--ledger-gzip-output", required=True)
    args = parser.parse_args()
    source = Path(args.input_dir)
    manifest_bytes = (source / "input-manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    contract_bytes = Path(args.contract).read_bytes()
    contract = json.loads(contract_bytes)
    events_bytes = (source / "selector-current-entry-events.ndjson").read_bytes()
    events = pd.read_json(events_bytes.decode(), lines=True)
    opportunities = json.loads((source / "first-entry-opportunities.json").read_text())
    first_event = {row.selectorEventId: row.to_dict() for _, row in events[events.isFirstSelection.eq(True)].iterrows()}
    if set(first_event) != {row["firstSelectorEventId"] for row in opportunities}:
        raise ValueError("first-entry opportunity lineage mismatch")
    if events.direction.ne("LONG").any() or events.shortScoreEvaluated.ne(False).any():
        raise ValueError("absolute LONG-only contract violation")
    funnel = {}
    for status in STATUSES:
        group = events[events.directStatus.eq(status)]
        funnel[status] = {"count": len(group), "ratePct": ratio(len(group), len(events), 100),
                          "uniqueSymbols": int(group.symbol.nunique()), "uniqueSymbolSessions": int(group.symbolSessionId.nunique()),
                          "decisionTimestamps": int(group[["sessionDate", "decisionTimestamp"]].drop_duplicates().shape[0])}
    report = {"schemaVersion": 1, "status": "CURRENT_ENTRY_TRANSFER_DIAGNOSTIC_COMPLETE_STOP",
              "contractId": contract["contractId"], "contractSha256": hashlib.sha256(contract_bytes).hexdigest(),
              "source": manifest["source"], "sessionAudits": manifest["sessionAudits"], "dataAudit": {**manifest["counts"], "directStatusTotal": sum(row["count"] for row in funnel.values()),
              "scoredEntryTicks": sum(row.get("scoredTicks", 0) for row in manifest["sessionAudits"]),
              "repeatedSelections": len(events)-events.symbolSessionId.nunique(), "eventLedgerSha256": hashlib.sha256(events_bytes).hexdigest()},
              "adapterAudit": contract["adapter"], "funnel": funnel,
              "cohorts": {status: cohort(events[events.directStatus.eq(status)]) for status in STATUSES},
              "firstEntryOpportunity": {"count": len(opportunities), "pass": sum(row["finalStatus"] == "PASS" for row in opportunities),
                "reject": sum(row["finalStatus"] == "REJECT" for row in opportunities),
                "repeatedSelectionEvents": len(events)-len(opportunities)},
              "opportunityPreservation": preservation(events),
              "selectorToEntryLatency": latency_report(opportunities, first_event),
              "opportunityConsumptionBps": distribution([row.get("consumedReturnBps") for row in opportunities if row["finalStatus"] == "PASS"]),
              "entryEnrichment": {}, "lostOpportunities": {}, "falsePass": {},
              "rank": grouped_funnel(events, "ridgeRank", [1, 2, 3, 4, 5]),
              "segment": grouped_funnel(events, "segment", ["PRIME", "STANDARD", "GROWTH"]),
              "liquidity": grouped_funnel(events, "liquidityBucket", ["LOW", "MID", "HIGH"]),
              "stateful": {}, "safety": manifest["safety"],
              "limitations": ["Cross-era Development transfer diagnostic; CURRENT Entry saved weights postdate Selector Development events.",
                "Frozen Selector selection membership is held only as active opportunity state between explicit decisions; no rank, score, Decision Price or eligibility is recomputed.",
                "CURRENT Entry has no immediate REJECT state; terminal EXPIRED opportunities are reported as REJECT.",
                "High touch is an evaluator event, not executable fill evidence.",
                "No Validation/OOS, EXIT, Capital Allocation, portfolio or order path was used."],
              "stopBoundary": contract["stopBoundary"]}
    for level in THRESHOLDS:
        pass_selector = precision(events[events.directStatus.eq("PASS")], "selectorOpportunity", level)
        pass_entry = precision(events[(events.directStatus.eq("PASS")) & events.entryAfterThisSelectorEvent.eq(True)], "entryOpportunity", level)
        report["entryEnrichment"][str(level)] = {"selectorBaselinePrecisionPct": BASELINE[level],
            "passSelectorTimePrecisionPct": pass_selector["precisionPct"],
            "passSelectorTimeDeltaPercentagePoints": number(pass_selector["precisionPct"]-BASELINE[level]) if pass_selector["precisionPct"] is not None else None,
            "passEntryTimeRemainingPrecisionPct": pass_entry["precisionPct"],
            "passEntryTimeDeltaVsSelectorBaselinePercentagePoints": number(pass_entry["precisionPct"]-BASELINE[level]) if pass_entry["precisionPct"] is not None else None}
        selector_values = pd.to_numeric(events[f"selectorOpportunity{level}"], errors="coerce")
        lost = events[selector_values.eq(1) & events.finalOpportunityStatus.eq("REJECT")]
        immediate = events[selector_values.eq(1) & events.directStatus.isin(["WAIT", "REJECT"])]
        report["lostOpportunities"][str(level)] = {"finalLostN": len(lost), "finalLostRatePct": ratio(len(lost), int(selector_values.eq(1).sum()), 100),
          "directWaitOrRejectN": len(immediate), "byDirectStatus": {status: int(immediate.directStatus.eq(status).sum()) for status in ["WAIT", "REJECT"]}}
        passed = [row for row in opportunities if row["finalStatus"] == "PASS" and row.get("entryOutcome")]
        remaining = [(row["entryOutcome"] or {}).get(f"opportunity{level}") for row in passed]
        valid = [value for value in remaining if value in (0, 1)]
        report["falsePass"][str(level)] = {"entryEvaluablePassN": len(valid), "noRemainingOpportunityN": sum(value == 0 for value in valid),
          "noRemainingOpportunityPct": ratio(sum(value == 0 for value in valid), len(valid), 100)}
    later_pass = [row for row in opportunities if row["finalStatus"] == "PASS" and first_event[row["firstSelectorEventId"]]["directStatus"] in ["WAIT", "BLOCKED"]]
    report["stateful"] = {"initialWaitOrBlockedLaterPassN": len(later_pass),
      "latencyMinutes": distribution([row.get("latencyMinutes") for row in later_pass]),
      "consumedReturnBps": distribution([row.get("consumedReturnBps") for row in later_pass]),
      "entryRemainingOpportunity": {str(level): opportunity_precision(later_pass, "entryOutcome", level) for level in THRESHOLDS}}
    report["finalVerdict"] = verdict(events, opportunities, report, contract)
    core = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["reportSha256"] = hashlib.sha256(core.encode()).hexdigest()
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    markdown_output = Path(args.markdown_output); markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown(report))
    ledger_output = Path(args.ledger_gzip_output); ledger_output.parent.mkdir(parents=True, exist_ok=True)
    with ledger_output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(events_bytes)
    print(json.dumps({"status": report["status"], "verdict": report["finalVerdict"]["verdict"],
                      "reportSha256": report["reportSha256"], "events": len(events), "opportunities": len(opportunities)}))


if __name__ == "__main__":
    main()
