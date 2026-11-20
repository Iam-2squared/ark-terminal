"""Phase57 one-shot confirmed-BUY persistence candidates for RISE/DROP/PULLBACK.

All candidate intents are frozen from causal closed-price prefixes and existing
frozen Signals before evaluator-only fills, Oracle anatomy or outcomes are opened.
Each target State is evaluated independently against the immutable accepted
ONE_MINUTE baseline; non-target records are copied exactly from that baseline.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import inspect
import json
import math
from pathlib import Path

from scripts import phase57_state_conditioned_signal_entry_v1 as metrics
from scripts import phase57_state_v3_9pattern_entry_v1 as v3
from scripts import phase57_drop_pull_1m_state_recheck_v1 as prior
from scripts import phase57_nine_state_anatomy_v1 as anatomy

TARGETS = ("RISE", "DROP", "PULLBACK")
EXPERIMENT = "CONFIRMED_BUY_PERSISTENCE_V1"


def causal_state_rows(day, minute_rows, path):
    rows = []
    violations = 0
    previous_session = path.get("previousSession")
    for source in minute_rows:
        now = int(source["minute"])
        prefix = [bar for bar in path["today"] if int(bar[0]) < now]
        state = v3.classify_state_v3(day, now, prefix, path["previous"], previous_session)
        state.update(
            opportunity=source["opportunity"],
            session=day,
            delay=int(source["delay"]),
            signalAny=any(
                source["signals"][family]["trigger"] is True for family in metrics.FAMILIES
            ),
            signalFamilies=[
                family for family in metrics.FAMILIES
                if source["signals"][family]["trigger"] is True
            ],
        )
        if state["maxSourceBarStart"] is not None:
            violations += int(state["maxSourceBarStart"] >= now)
        rows.append(state)
    assert rows and rows[0]["delay"] == 0
    return rows, violations


def confirmed_intent(opportunity, minute_rows, state_rows):
    """Earliest State+Signal concurrence or two consecutive BUY-state observations."""
    state_by_minute = {int(row["asOf"]): row for row in state_rows}
    assert set(int(row["minute"]) for row in minute_rows).issubset(state_by_minute)
    buy_streak = 0
    previous_minute = None
    first_signal = None
    first_state_buy = None
    all_signal_families = set()
    initial_state = state_by_minute[int(minute_rows[0]["minute"])]["state"]

    for source in minute_rows:
        minute = int(source["minute"])
        state = state_by_minute[minute]["state"]
        signals = tuple(
            family for family in metrics.FAMILIES
            if source["signals"][family]["trigger"] is True
        )
        all_signal_families.update(signals)
        if signals and first_signal is None:
            first_signal = (minute, int(source["delay"]), signals)
        if state in v3.BUY_STATES and first_state_buy is None:
            first_state_buy = (minute, int(source["delay"]), state)

        consecutive = False
        if previous_minute is not None:
            try:
                consecutive = v3.active_elapsed(previous_minute, minute) == 1
            except ValueError:
                consecutive = False
        if state in v3.BUY_STATES:
            buy_streak = buy_streak + 1 if consecutive else 1
        else:
            buy_streak = 0

        if state in v3.BUY_STATES and signals:
            reason = "CONFIRMED_SIGNAL_AND_BUY_STATE"
        elif state in v3.BUY_STATES and buy_streak >= 2:
            reason = "CONFIRMED_TWO_CONSECUTIVE_BUY_STATES"
        else:
            previous_minute = minute
            continue

        return {
            "opportunity": opportunity,
            "intentMinute": minute,
            "intentDelay": int(source["delay"]),
            "intentReason": reason,
            "triggerSources": [reason],
            "triggerSignals": list(signals),
            "initialState": initial_state,
            "stateAtIntent": state,
            "firstSignalMinute": first_signal[0] if first_signal else None,
            "firstSignalDelay": first_signal[1] if first_signal else None,
            "firstStateBuyMinute": first_state_buy[0] if first_state_buy else None,
            "firstStateBuyDelay": first_state_buy[1] if first_state_buy else None,
            "firstTransitionBuyState": first_state_buy[2] if first_state_buy else None,
            "allWindowSignalFamilies": sorted(all_signal_families),
        }

    return {
        "opportunity": opportunity,
        "intentMinute": None,
        "intentDelay": None,
        "intentReason": None,
        "triggerSources": [],
        "triggerSignals": [],
        "initialState": initial_state,
        "stateAtIntent": None,
        "firstSignalMinute": first_signal[0] if first_signal else None,
        "firstSignalDelay": first_signal[1] if first_signal else None,
        "firstStateBuyMinute": first_state_buy[0] if first_state_buy else None,
        "firstStateBuyDelay": first_state_buy[1] if first_state_buy else None,
        "firstTransitionBuyState": first_state_buy[2] if first_state_buy else None,
        "allWindowSignalFamilies": sorted(all_signal_families),
    }


def compact_policy(opportunities, rows):
    summary = metrics.policy_summary(opportunities, rows)
    return {
        "population": summary.get("population"),
        "fills": summary.get("fills"),
        "noEntry": summary.get("noEntry"),
        "fillRatePct": summary.get("fillRatePct"),
        "entryPosition": anatomy.threshold_summary(rows),
        "lowToEntryDistancePct": anatomy.stat_compact(summary.get("lowToEntryDistancePct", {})),
        "lowToEntryPrice": anatomy.stat_compact(summary.get("lowToEntryPrice", {})),
        "entryToLaterHighRemainingUpsidePct": anatomy.stat_compact(
            summary.get("entryToLaterHighRemainingUpsidePct", {})
        ),
        "capture3": anatomy.capture_at(summary, 3),
        "capture5": anatomy.capture_at(summary, 5),
        "horizon30": anatomy.horizon_compact(summary, 30),
        "horizon60": anatomy.horizon_compact(summary, 60),
        "unfilledReason": summary.get("unfilledReason", {}),
    }, summary


def compact_pair(base_rows, candidate_rows, base_summary, candidate_summary):
    paired, _ = metrics.paired_summary(base_rows, candidate_rows, base_summary, candidate_summary)
    return {
        "population": paired.get("population"),
        "pairStatus": paired.get("pairStatus", {}),
        "fillRateDeltaPp": paired.get("fillRateDeltaPp"),
        "fillDelta": paired.get("fillDelta"),
        "entryPositionDelta": anatomy.stat_compact(paired.get("entryPositionDelta", {})),
        "lowToEntryDistanceDeltaPct": anatomy.stat_compact(
            paired.get("lowToEntryDistanceDeltaPct", {})
        ),
        "priceImprovementPct": anatomy.stat_compact(paired.get("priceImprovementPct", {})),
        "delayDelta": anatomy.stat_compact(paired.get("delayDelta", {})),
        "remainingUpsideDeltaPct": anatomy.stat_compact(paired.get("remainingUpsideDeltaPct", {})),
        "MFE30DeltaPp": anatomy.stat_compact(paired.get("MFE30DeltaPp", {})),
        "MAE30DeltaPp": anatomy.stat_compact(paired.get("MAE30DeltaPp", {})),
        "MFE60DeltaPp": anatomy.stat_compact(paired.get("MFE60DeltaPp", {})),
        "MAE60DeltaPp": anatomy.stat_compact(paired.get("MAE60DeltaPp", {})),
        "captureDeltaPp": paired.get("captureDeltaPp", {}),
        "sessionEqualPriceBootstrap": paired.get("sessionEqualPriceBootstrap"),
    }


def capture_delta(candidate, baseline, level):
    return candidate["capture"][str(level)]["ratePct"] - baseline["capture"][str(level)]["ratePct"]


def suffix_invariance(day, minute_rows, path, expected_rows):
    """Mutate bars strictly after the last candidate checkpoint and prove no intent change."""
    cutoff = int(minute_rows[-1]["minute"])
    mutated = dict(path)
    mutated_today = []
    for bar in path["today"]:
        copied = list(bar)
        if int(copied[0]) >= cutoff:
            copied[1] = float(copied[1]) * 7.0
            copied[4] = float(copied[4]) * 0.2
        mutated_today.append(copied)
    mutated["today"] = mutated_today
    rerun, violations = causal_state_rows(day, minute_rows, mutated)
    key = lambda row: (
        row["asOf"], row["state"], row["maxSourceBarStart"], row["priorDir"], row["recentDir"],
        row["priorReturn"], row["recentReturn"], row["signalAny"], tuple(row["signalFamilies"]),
    )
    assert [key(row) for row in rerun] == [key(row) for row in expected_rows]
    return len(rerun), violations


def run(args):
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)

    measurement = Path(args.measurement)
    minute_by_opp = collections.defaultdict(list)
    fill_grid_by_opp = collections.defaultdict(list)
    signal_checks = signal_pass = 0
    for path in sorted((measurement / "minute-census").glob("*.json.gz")):
        for row in metrics.read_json(path):
            minute_by_opp[row["opportunity"]].append(row)
            if row["comparisonEligible"]:
                fill_grid_by_opp[row["opportunity"]].append(row)
            signal_checks += 1
            through = row.get("computedThroughBarStart")
            signal_pass += int(through is None or through < row["minute"])
    assert len(minute_by_opp) == len(fill_grid_by_opp) == 2155
    for rows in minute_by_opp.values():
        rows.sort(key=lambda row: int(row["minute"]))
        assert rows and rows[0]["delay"] == 0

    baseline = metrics.read_json(Path(args.one_minute_records))
    baseline_by = {row["opportunity"]: row for row in baseline}
    assert len(baseline_by) == 2155
    initial_state = {oid: row["initialState"] for oid, row in baseline_by.items()}
    assert collections.Counter(initial_state.values())["RISE"] == 111
    assert collections.Counter(initial_state.values())["DROP"] == 1403
    assert collections.Counter(initial_state.values())["PULLBACK"] == 354

    raw_paths = metrics.read_json(Path(args.raw_paths))
    assert set(minute_by_opp).issubset(raw_paths)

    target_union = {oid for oid, state in initial_state.items() if state in TARGETS}
    causal_by = {}
    state_future_violations = 0
    closed_checks = closed_pass = 0
    for oid in sorted(target_union):
        rows, violations = causal_state_rows(
            minute_by_opp[oid][0]["session"], minute_by_opp[oid], raw_paths[oid]
        )
        assert rows[0]["state"] == initial_state[oid]
        causal_by[oid] = rows
        state_future_violations += violations
        for row in rows:
            if row["maxSourceBarStart"] is not None:
                closed_checks += 1
                closed_pass += int(row["maxSourceBarStart"] < row["asOf"])

    intents_by_target = {}
    for target in TARGETS:
        intents_by_target[target] = {
            oid: confirmed_intent(oid, minute_by_opp[oid], causal_by[oid])
            for oid in sorted(target_union) if initial_state[oid] == target
        }

    causal_payload = {
        "states": causal_by,
        "intents": intents_by_target,
    }
    causal_sha = hashlib.sha256(
        json.dumps(causal_payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()

    suffix_checks = suffix_violations = 0
    for target in TARGETS:
        sample = sorted(intents_by_target[target])[:8]
        for oid in sample:
            n, violations = suffix_invariance(
                minute_by_opp[oid][0]["session"], minute_by_opp[oid], raw_paths[oid], causal_by[oid]
            )
            suffix_checks += n
            suffix_violations += violations
    assert state_future_violations == 0
    assert closed_checks == closed_pass
    assert signal_checks == signal_pass
    assert suffix_violations == 0

    # Evaluator sources open only after every causal candidate intent is frozen.
    opportunities = metrics.read_json(measurement / "opportunity-records.json.gz")
    opp_by = {row["opportunity"]: row for row in opportunities}
    assert set(opp_by) == set(baseline_by)
    quote_source = metrics.read_json(Path(args.rows))
    quote_rows = {
        row["id"]: row for row in quote_source
        if row["opportunity"] in baseline_by and row.get("eligible1")
    }
    del quote_source
    outcomes = metrics.read_json(Path(args.outcomes))
    immediate = metrics.read_json(Path(args.entry_v1_measurement) / "baseline-immediate-records.json.gz")
    entry_v1 = metrics.read_json(Path(args.entry_v1_measurement) / "entry-records.json.gz")
    state_v3 = metrics.read_json(Path(args.state_v3_measurement) / "entry-records.json.gz")

    output_candidates = {}
    results = {}
    for target in TARGETS:
        target_ids = set(intents_by_target[target])
        candidate = []
        for opportunity in opportunities:
            oid = opportunity["opportunity"]
            if oid not in target_ids:
                candidate.append(baseline_by[oid])
                continue
            intent = intents_by_target[target][oid]
            trade = v3.simulate_fill(
                oid, opportunity["session"], fill_grid_by_opp[oid], intent, quote_rows, outcomes
            )
            trade["rangeRetention"] = v3.range_retention(opportunity, trade)
            trade["waitMaxRiseVsImmediatePct"] = None
            quality = metrics.oracle_metrics(opportunity, trade)
            labels = metrics.label_metrics(trade, outcomes)
            record = v3.candidate_record(opportunity, intent, trade, quality, labels)
            record["experiment"] = f"{EXPERIMENT}:{target}"
            candidate.append(record)
        output_candidates[target] = candidate

        # Exact non-target parity against accepted ONE_MINUTE records.
        cand_by = {row["opportunity"]: row for row in candidate}
        parity = 0
        for oid, base in baseline_by.items():
            if oid not in target_ids:
                assert cand_by[oid] == base
                parity += 1
        assert parity == 2155 - len(target_ids)

        target_opps = [opp_by[oid] for oid in sorted(target_ids)]
        base_target = [baseline_by[oid] for oid in sorted(target_ids)]
        cand_target = [cand_by[oid] for oid in sorted(target_ids)]
        base_compact, base_summary = compact_policy(target_opps, base_target)
        cand_compact, cand_summary = compact_policy(target_opps, cand_target)
        pair = compact_pair(base_target, cand_target, base_summary, cand_summary)
        base_pos = base_compact["entryPosition"]
        cand_pos = cand_compact["entryPosition"]
        fill_delta = cand_summary["fillRatePct"] - base_summary["fillRatePct"]
        cap3_delta = capture_delta(cand_summary, base_summary, 3)
        cap5_delta = capture_delta(cand_summary, base_summary, 5)
        pos_delta = pair["entryPositionDelta"]["mean"]
        low_delta = pair["lowToEntryDistanceDeltaPct"]["mean"]
        le15_delta = (
            cand_pos["thresholds"]["le15pct"]["ratePct"]
            - base_pos["thresholds"]["le15pct"]["ratePct"]
        )
        le25_delta = (
            cand_pos["thresholds"]["le25pct"]["ratePct"]
            - base_pos["thresholds"]["le25pct"]["ratePct"]
        )
        gates = {
            "pairedEntryPositionImproves": pos_delta is not None and pos_delta < 0,
            "pairedLowToEntryImproves": low_delta is not None and low_delta < 0,
            "le15RateImproves": le15_delta > 0,
            "le25RateImproves": le25_delta > 0,
            "fillRateNotWorseThan2pp": fill_delta >= -2.0,
            "capture3NotWorseThan2pp": cap3_delta >= -2.0,
            "capture5NotWorseThan2pp": cap5_delta >= -2.0,
            "causality": True,
        }
        status = "PASS_PROVISIONAL_COMPONENT" if all(gates.values()) else "REJECT"
        whole_compact, whole_summary = compact_policy(opportunities, candidate)
        results[target] = {
            "hypothesisId": f"{target}_CONFIRMED_BUY_PERSISTENCE_V1",
            "targetPopulation": len(target_ids),
            "baseline": base_compact,
            "candidate": cand_compact,
            "pairedCandidateMinusBaseline": pair,
            "deltas": {
                "fillRatePp": fill_delta,
                "capture3Pp": cap3_delta,
                "capture5Pp": cap5_delta,
                "le15RatePp": le15_delta,
                "le25RatePp": le25_delta,
            },
            "gates": gates,
            "status": status,
            "nonTargetExactParity": parity,
            "whole2155Candidate": whole_compact,
        }

    prohibited = prior._prohibited_decision_tokens(
        inspect.getsource(causal_state_rows) + inspect.getsource(confirmed_intent)
    )
    causality = {
        "status": "PASS" if not prohibited else "FAIL",
        "causalIntentSHA256BeforeEvaluatorOpen": causal_sha,
        "evaluatorOpenedAfterAllIntents": True,
        "stateFutureViolations": state_future_violations,
        "closedBarChecks": closed_checks,
        "closedBarPassed": closed_pass,
        "signalClosedBarChecks": signal_checks,
        "signalClosedBarPassed": signal_pass,
        "futureSuffixInvarianceRowsChecked": suffix_checks,
        "futureSuffixViolations": suffix_violations,
        "decisionFunctionProhibitedTokens": prohibited,
        "oracleLowHighDecisionUse": 0,
        "futureOutcomeDecisionUse": 0,
        "stateV3ContractChanged": False,
        "signalDefinitionChanged": False,
        "providerRequests": 0,
        "protectedDataOpened": 0,
    }
    metrics.write_json(output / "causality-audit.json", causality)
    assert causality["status"] == "PASS", json.dumps(causality, sort_keys=True)

    result = {
        "artifactKind": "phase57_confirmed_buy_persistence_candidates_r1",
        "developmentOnly": True,
        "experiment": EXPERIMENT,
        "population": 2155,
        "precommittedTargets": list(TARGETS),
        "results": results,
        "causality": causality,
        "inputHashes": {
            "measurementManifest": metrics.sha256(measurement / "manifest.json"),
            "oneMinuteRecords": metrics.sha256(Path(args.one_minute_records)),
            "rawPaths": metrics.sha256(Path(args.raw_paths)),
            "rows": metrics.sha256(Path(args.rows)),
            "outcomes": metrics.sha256(Path(args.outcomes)),
        },
    }
    metrics.write_json(output / "summary.json", result)
    for target, rows in output_candidates.items():
        metrics.write_gzip_json(output / f"candidate-{target.lower()}.json.gz", rows)
    manifest = {
        path.name: metrics.sha256(path)
        for path in output.iterdir() if path.is_file()
    }
    metrics.write_json(output / "manifest.json", manifest)

    print(json.dumps({
        "kind": result["artifactKind"],
        "causality": causality,
        "targets": {
            state: {
                "status": block["status"],
                "baselineFillRatePct": block["baseline"]["fillRatePct"],
                "candidateFillRatePct": block["candidate"]["fillRatePct"],
                "baselineEntryPositionMean": block["baseline"]["entryPosition"]["mean"],
                "candidateEntryPositionMean": block["candidate"]["entryPosition"]["mean"],
                "baselineLe15Pct": block["baseline"]["entryPosition"]["thresholds"]["le15pct"]["ratePct"],
                "candidateLe15Pct": block["candidate"]["entryPosition"]["thresholds"]["le15pct"]["ratePct"],
                "baselineLe25Pct": block["baseline"]["entryPosition"]["thresholds"]["le25pct"]["ratePct"],
                "candidateLe25Pct": block["candidate"]["entryPosition"]["thresholds"]["le25pct"]["ratePct"],
                "pairedEntryPositionDelta": block["pairedCandidateMinusBaseline"]["entryPositionDelta"]["mean"],
                "pairedLowToEntryDeltaPct": block["pairedCandidateMinusBaseline"]["lowToEntryDistanceDeltaPct"]["mean"],
                "capture3DeltaPp": block["deltas"]["capture3Pp"],
                "capture5DeltaPp": block["deltas"]["capture5Pp"],
                "gates": block["gates"],
            }
            for state, block in results.items()
        },
    }, sort_keys=True, allow_nan=False))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement", required=True)
    parser.add_argument("--entry-v1-measurement", required=True)
    parser.add_argument("--state-v3-measurement", required=True)
    parser.add_argument("--one-minute-records", required=True)
    parser.add_argument("--raw-paths", required=True)
    parser.add_argument("--rows", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--output", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
