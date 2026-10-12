"""Phase57 REBOUND confirmation Entry candidate v1.

Single precommitted Development hypothesis.  For the original frozen T0 REBOUND
cohort only, suppress immediate BUY and wait for the earliest already-frozen
six-Signal trigger or a later frozen State-v3 transition to RISE/SHARP_RISE.
No classifier threshold, Signal definition, feature, model or fixed-time fallback
is added.  All evaluator-only fields open only after every intent is frozen.
"""
from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import inspect
import json
import textwrap
from pathlib import Path

from scripts import phase57_state_conditioned_signal_entry_v1 as metrics
from scripts import phase57_state_v3_9pattern_entry_v1 as v3
from scripts.phase57_drop_pull_1m_state_recheck_v1 import _position_thresholds, _capture_delta

TARGET_STATE = "REBOUND"
CONFIRM_STATES = ("RISE", "SHARP_RISE")
EXPERIMENT = "REBOUND_CONFIRM_EXISTING_EVIDENCE_V1"
POSITION_LEVELS = (0.10, 0.15, 0.25, 0.50)


def prohibited_decision_tokens(source):
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body = node.body[1:] or [ast.Pass()]
    executable = ast.unparse(tree)
    return [token for token in metrics.FORBIDDEN_DECISION_TOKENS if token in executable]


def rebound_confirm_intent(opportunity, minute_rows, state_rows, policy):
    """Causal target-only confirmation policy using existing Signals/States."""
    assert minute_rows and minute_rows[0]["delay"] == 0
    by_state_minute = {row["asOf"]: row for row in state_rows}
    initial = by_state_minute[minute_rows[0]["minute"]]
    assert initial["state"] == TARGET_STATE

    first_signal = None
    first_confirm = None
    all_signal_families = set()
    for row in minute_rows:
        firing = tuple(f for f in v3.FAMILIES if row["signals"][f]["trigger"] is True)
        all_signal_families.update(firing)
        if firing and first_signal is None:
            first_signal = (row["minute"], row["delay"], firing)
        state_row = by_state_minute.get(row["minute"])
        if (row["delay"] > 0 and state_row
                and state_row["state"] in CONFIRM_STATES and first_confirm is None):
            first_confirm = (row["minute"], row["delay"], state_row["state"])

    candidates = []
    if first_signal:
        candidates.append((first_signal[0], 0, "SIGNAL_TRIGGER"))
    if first_confirm:
        candidates.append((first_confirm[0], 1, "STATE_CONFIRM_TRIGGER"))
    if candidates:
        minute, _, reason = min(candidates)
        delay = next(row["delay"] for row in minute_rows if row["minute"] == minute)
    else:
        minute = delay = reason = None

    sources = []
    firing = ()
    state_at_intent = None
    if minute is not None:
        source_row = next(row for row in minute_rows if row["minute"] == minute)
        firing = tuple(f for f in v3.FAMILIES if source_row["signals"][f]["trigger"] is True)
        if firing:
            sources.append("SIGNAL_TRIGGER")
        state_row = by_state_minute.get(minute)
        if state_row and state_row["state"] in CONFIRM_STATES:
            sources.append("STATE_CONFIRM_TRIGGER")
            state_at_intent = state_row["state"]

    return {
        "opportunity": opportunity,
        "intentMinute": minute,
        "intentDelay": delay,
        "intentReason": reason,
        "triggerSources": sources,
        "triggerSignals": list(firing),
        "initialState": initial["state"],
        "stateAtIntent": state_at_intent,
        "firstSignalMinute": first_signal[0] if first_signal else None,
        "firstSignalDelay": first_signal[1] if first_signal else None,
        "firstStateBuyMinute": first_confirm[0] if first_confirm else None,
        "firstStateBuyDelay": first_confirm[1] if first_confirm else None,
        "firstTransitionBuyState": first_confirm[2] if first_confirm else None,
        "allWindowSignalFamilies": sorted(all_signal_families),
    }


def run(args):
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)

    base_policy = metrics.read_json(Path(args.base_policy))
    assert tuple(base_policy["buyStates"]) == v3.BUY_STATES
    assert base_policy["stateRecheckActiveMinutes"] == 5
    assert base_policy["fixedTimeFallback"] is False
    assert base_policy["providerRequestsAuthorized"] == base_policy["protectedDataOpened"] == 0
    assert all(value is False for value in base_policy["safety"].values())

    measurement = Path(args.measurement)
    minute_by_opp = collections.defaultdict(list)
    fill_grid_by_opp = collections.defaultdict(list)
    signal_checks = signal_pass = 0
    for path in sorted((measurement / "minute-census").glob("*.json.gz")):
        for row in metrics.read_json(path):
            if row["delay"] > base_policy["entryWindow"]["maximumActiveMinutes"]:
                continue
            minute_by_opp[row["opportunity"]].append(row)
            if row["comparisonEligible"]:
                fill_grid_by_opp[row["opportunity"]].append(row)
            signal_checks += 1
            through = row.get("computedThroughBarStart")
            signal_pass += through is None or through < row["minute"]
    assert len(minute_by_opp) == len(fill_grid_by_opp) == 2155
    for rows in minute_by_opp.values():
        rows.sort(key=lambda r: r["minute"])
        assert rows[0]["delay"] == 0

    state_rows = metrics.read_json(Path(args.state_checkpoints))
    state_by_opp = collections.defaultdict(list)
    state_future_violations = 0
    for row in state_rows:
        state_by_opp[row["opportunity"]].append(row)
        maximum = row.get("maxSourceBarStart")
        if maximum is not None:
            state_future_violations += int(maximum >= row["asOf"])
    for rows in state_by_opp.values():
        rows.sort(key=lambda r: r["delay"])
    assert set(state_by_opp) == set(minute_by_opp)

    target_ids = {oid for oid, rows in state_by_opp.items() if rows[0]["state"] == TARGET_STATE}
    assert len(target_ids) == 192

    intents = {}
    for oid in sorted(minute_by_opp):
        if oid in target_ids:
            intents[oid] = rebound_confirm_intent(
                oid, minute_by_opp[oid], state_by_opp[oid], base_policy
            )
        else:
            intents[oid] = v3.frozen_intent(
                oid, minute_by_opp[oid], state_by_opp[oid], base_policy
            )
    causal_intents_sha = hashlib.sha256(
        json.dumps(intents, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()

    # Evaluator-only data opens only after every causal intent is frozen.
    opportunities = metrics.read_json(measurement / "opportunity-records.json.gz")
    quote_source = metrics.read_json(Path(args.rows))
    quote_rows = {
        row["id"]: row for row in quote_source
        if row["opportunity"] in intents and row.get("eligible1")
    }
    del quote_source
    outcomes = metrics.read_json(Path(args.outcomes))
    raw_paths = metrics.read_json(Path(args.raw_paths))
    immediate = metrics.read_json(Path(args.entry_v1_measurement) / "baseline-immediate-records.json.gz")
    entry_v1 = metrics.read_json(Path(args.entry_v1_measurement) / "entry-records.json.gz")
    state_v3 = metrics.read_json(Path(args.state_v3_measurement) / "entry-records.json.gz")
    immediate_by_id = {row["opportunity"]: row for row in immediate}
    assert [row["opportunity"] for row in opportunities] == sorted(intents)

    candidate = []
    raw_trades = []
    for opportunity in opportunities:
        oid = opportunity["opportunity"]
        intent = intents[oid]
        trade = v3.simulate_fill(
            oid, opportunity["session"], fill_grid_by_opp[oid], intent, quote_rows, outcomes
        )
        trade["rangeRetention"] = v3.range_retention(opportunity, trade)
        trade["waitMaxRiseVsImmediatePct"] = v3.missed_upside(
            raw_paths[oid], immediate_by_id[oid], trade, minute_by_opp[oid][-1]["minute"]
        )
        quality = metrics.oracle_metrics(opportunity, trade)
        labels = metrics.label_metrics(trade, outcomes)
        record = v3.candidate_record(opportunity, intent, trade, quality, labels)
        record["experiment"] = EXPERIMENT
        candidate.append(record)
        raw_trades.append({**trade, **{k: intent.get(k) for k in (
            "triggerSources", "triggerSignals", "initialState", "stateAtIntent",
            "firstSignalMinute", "firstSignalDelay", "firstStateBuyMinute",
            "firstStateBuyDelay", "firstTransitionBuyState", "allWindowSignalFamilies",
        )}})

    baseline_by_id = {row["opportunity"]: row for row in state_v3}
    non_target_exact = 0
    for record in candidate:
        if record["opportunity"] not in target_ids:
            stripped = {k: value for k, value in record.items() if k != "experiment"}
            assert stripped == baseline_by_id[record["opportunity"]], record["opportunity"]
            non_target_exact += 1
    assert non_target_exact == 2155 - 192

    policies = {
        "IMMEDIATE": immediate,
        "ENTRY_V1": entry_v1,
        "STATE_V3": state_v3,
        "REBOUND_CONFIRM_V1": candidate,
    }
    summaries = {name: metrics.policy_summary(opportunities, rows) for name, rows in policies.items()}

    target_opps = [row for row in opportunities if row["opportunity"] in target_ids]
    target_policies = {
        name: [row for row in rows if row["opportunity"] in target_ids]
        for name, rows in policies.items()
    }
    target_summaries = {
        name: metrics.policy_summary(target_opps, rows)
        for name, rows in target_policies.items()
    }
    paired, paired_rows = metrics.paired_summary(
        target_policies["STATE_V3"], target_policies["REBOUND_CONFIRM_V1"],
        target_summaries["STATE_V3"], target_summaries["REBOUND_CONFIRM_V1"],
    )
    positions = {
        name: _position_thresholds(rows)
        for name, rows in target_policies.items()
    }
    # Add the newly predeclared 15% completion view without changing evaluator definitions.
    for name, rows in target_policies.items():
        values = [
            row["quality"].get("entryPosition") for row in rows
            if row.get("entryId") and row.get("quality", {}).get("entryPosition") is not None
        ]
        positions[name]["rates"]["0.15"] = {
            "count": sum(value <= 0.15 for value in values),
            "ratePct": 100 * sum(value <= 0.15 for value in values) / len(values) if values else None,
        }

    base = target_summaries["STATE_V3"]
    cand = target_summaries["REBOUND_CONFIRM_V1"]
    rate15_delta = positions["REBOUND_CONFIRM_V1"]["rates"]["0.15"]["ratePct"] - positions["STATE_V3"]["rates"]["0.15"]["ratePct"]
    rate25_delta = positions["REBOUND_CONFIRM_V1"]["rates"]["0.25"]["ratePct"] - positions["STATE_V3"]["rates"]["0.25"]["ratePct"]
    fill_delta = cand["fillRatePct"] - base["fillRatePct"]
    cap3_delta = _capture_delta(cand, base, 3)
    cap5_delta = _capture_delta(cand, base, 5)
    pos_delta = paired["entryPositionDelta"]["mean"]
    low_delta = paired["lowToEntryDistanceDeltaPct"]["mean"]

    gates = {
        "pairedEntryPositionImproves": pos_delta is not None and pos_delta < 0,
        "pairedLowToEntryImproves": low_delta is not None and low_delta < 0,
        "le15RateImproves": rate15_delta > 0,
        "le25RateImproves": rate25_delta > 0,
        "fillRateNotWorseThan2pp": fill_delta >= -2.0,
        "capture3NotWorseThan2pp": cap3_delta >= -2.0,
        "capture5NotWorseThan2pp": cap5_delta >= -2.0,
        "causality": state_future_violations == 0 and signal_pass == signal_checks,
    }

    decision_source = inspect.getsource(rebound_confirm_intent)
    prohibited = prohibited_decision_tokens(decision_source)
    causality = {
        "status": "PASS" if not prohibited and gates["causality"] else "FAIL",
        "causalIntentSHA256BeforeEvaluatorOpen": causal_intents_sha,
        "evaluatorOpenedAfterAllIntents": True,
        "stateFutureBarViolations": state_future_violations,
        "signalDecisionCount": signal_checks,
        "signalClosedBarAssertionsPassed": signal_pass,
        "decisionFunctionProhibitedTokens": prohibited,
        "oracleLowHighDecisionUse": 0,
        "mfeMaeDecisionUse": 0,
        "futureOutcomeDecisionUse": 0,
        "classifierChanged": False,
        "signalDefinitionsChanged": False,
        "fixedTimeFallbackAdded": False,
        "nonTargetRecordsExactParity": non_target_exact,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "safety": base_policy["safety"],
    }
    assert causality["status"] == "PASS", causality

    status = "PASS_PROVISIONAL_COMPONENT" if all(gates.values()) else "REJECT_NO_SECOND_REBOUND_HYPOTHESIS"
    result = {
        "artifactKind": "phase57_rebound_confirm_existing_evidence_v1_result",
        "experiment": EXPERIMENT,
        "population": 2155,
        "targetState": TARGET_STATE,
        "targetPopulation": 192,
        "confirmStates": list(CONFIRM_STATES),
        "hypothesisBudgetConsumed": 1,
        "policies": summaries,
        "targetCohort": {
            "summaries": target_summaries,
            "entryPositionThresholds": positions,
            "pairedVsStateV3": paired,
            "deltasVsStateV3": {
                "le15RatePp": rate15_delta,
                "le25RatePp": rate25_delta,
                "fillRatePp": fill_delta,
                "capture3Pp": cap3_delta,
                "capture5Pp": cap5_delta,
            },
        },
        "gateChecks": gates,
        "causalityAudit": causality,
        "status": status,
        "wholeEntryAspirationalMeanLt": 0.15,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "safety": base_policy["safety"],
    }
    metrics.write_json(output / "summary.json", result)
    metrics.write_json(output / "causality-audit.json", causality)
    metrics.write_json(output / "gate.json", {"status": status, "checks": gates})
    metrics.write_gzip_json(output / "entry-records.json.gz", candidate)
    metrics.write_gzip_json(output / "target-paired-vs-state-v3.json.gz", paired_rows)
    metrics.write_gzip_json(output / "trades.json.gz", raw_trades)
    manifest = {
        path.name: metrics.sha256(path) for path in sorted(output.iterdir())
        if path.name != "manifest.json"
    }
    metrics.write_json(output / "manifest.json", manifest)
    print(json.dumps({
        "status": status,
        "targetPopulation": 192,
        "baselineMean": positions["STATE_V3"]["mean"],
        "candidateMean": positions["REBOUND_CONFIRM_V1"]["mean"],
        "le15DeltaPp": rate15_delta,
        "le25DeltaPp": rate25_delta,
        "fillDeltaPp": fill_delta,
        "capture3DeltaPp": cap3_delta,
        "capture5DeltaPp": cap5_delta,
        "pairedEntryPositionMeanDelta": pos_delta,
        "causality": causality["status"],
    }, sort_keys=True, allow_nan=False))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement", required=True)
    parser.add_argument("--entry-v1-measurement", required=True)
    parser.add_argument("--state-v3-measurement", required=True)
    parser.add_argument("--state-checkpoints", required=True)
    parser.add_argument("--raw-paths", required=True)
    parser.add_argument("--rows", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--base-policy", required=True)
    parser.add_argument("--output", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
