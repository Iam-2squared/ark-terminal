"""Phase57 DROP/PULLBACK 1m State Recheck v1.

Precommitted policy-layer experiment. The frozen State-v3 classifier and all six
existing signal definitions are unchanged. Only opportunities whose frozen T0
State-v3 classification is DROP or PULLBACK receive one-active-minute State-v3
rechecks instead of five-active-minute rechecks. T0 BUY states and every
non-target opportunity retain the exact accepted State-v3 Entry v1 policy.
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
from scripts import phase57_drop_pull_lower_wick_gate_v1 as prior

TARGET_INITIAL_STATES = ("DROP", "PULLBACK")
POSITION_LEVELS = (0.10, 0.25, 0.50)
EXPERIMENT = "DROP_PULLBACK_1M_STATE_RECHECK_V1"


def _classify_target_every_minute(oid, day, minute_rows, path):
    """Return causal State-v3 rows at every available active-minute checkpoint."""
    checks = []
    violations = 0
    previous_session = path.get("previousSession")
    for row in minute_rows:
        now = row["minute"]
        prefix = [bar for bar in path["today"] if int(bar[0]) < now]
        classified = v3.classify_state_v3(
            day, now, prefix, path["previous"], previous_session
        )
        classified.update(
            opportunity=oid,
            session=day,
            delay=row["delay"],
            inputTodayPrefixRows=len(prefix),
            inputPreviousRows=len(path["previous"]),
        )
        if classified["maxSourceBarStart"] is not None:
            violations += classified["maxSourceBarStart"] >= now
        checks.append(classified)
    assert checks and checks[0]["delay"] == 0
    return checks, violations


def _prohibited_decision_tokens(source):
    """Scan executable syntax and keys; explanatory docstrings are not inputs.

    Comments are excluded by parsing. Only actual Python docstrings are removed;
    other string constants (including payload keys), names, attributes, function
    defaults and executable expressions remain subject to the original tokens.
    This static check supplements, not replaces, runtime closed-bar assertions.
    """
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body = node.body[1:] or [ast.Pass()]
    executable_source = ast.unparse(tree)
    return [token for token in metrics.FORBIDDEN_DECISION_TOKENS
            if token in executable_source]


def _position_thresholds(records):
    values = [
        row["quality"].get("entryPosition") for row in records
        if row.get("entryId") and row.get("quality", {}).get("entryPosition") is not None
    ]
    return {
        "evaluable": len(values),
        "mean": sum(values) / len(values) if values else None,
        "median": metrics.percentile(values, .5),
        "rates": {
            str(level): {
                "count": sum(value <= level for value in values),
                "ratePct": 100 * sum(value <= level for value in values) / len(values)
                if values else None,
            }
            for level in POSITION_LEVELS
        },
    }


def _capture_delta(candidate_summary, base_summary, level):
    return (
        candidate_summary["capture"][str(level)]["ratePct"]
        - base_summary["capture"][str(level)]["ratePct"]
    )


def run(args):
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)

    policy = metrics.read_json(Path(args.policy))
    base_policy = metrics.read_json(Path(args.base_policy))
    assert policy["lockedBeforeMeasurement"] is True
    assert tuple(policy["targetInitialStates"]) == TARGET_INITIAL_STATES
    assert policy["stateRecheckActiveMinutes"] == 1
    assert policy["signalPolicy"] == "ANY_FROZEN_SIX_UNCHANGED"
    assert tuple(base_policy["buyStates"]) == v3.BUY_STATES
    assert base_policy["stateRecheckActiveMinutes"] == 5
    assert base_policy["fixedTimeFallback"] is False
    assert policy["providerRequestsAuthorized"] == policy["protectedDataOpened"] == 0
    assert all(value is False for value in policy["safety"].values())
    assert all(value is False for value in base_policy["safety"].values())

    measurement = Path(args.measurement)
    minute_by_opp = collections.defaultdict(list)
    fill_grid_by_opp = collections.defaultdict(list)
    signal_closed_bar_checks = 0
    signal_closed_bar_pass = 0
    for path in sorted((measurement / "minute-census").glob("*.json.gz")):
        for row in metrics.read_json(path):
            if row["delay"] > base_policy["entryWindow"]["maximumActiveMinutes"]:
                continue
            minute_by_opp[row["opportunity"]].append(row)
            if row["comparisonEligible"]:
                fill_grid_by_opp[row["opportunity"]].append(row)
            signal_closed_bar_checks += 1
            through = row.get("computedThroughBarStart")
            signal_closed_bar_pass += through is None or through < row["minute"]
    assert len(minute_by_opp) == 2155 == len(fill_grid_by_opp)
    for rows in minute_by_opp.values():
        rows.sort(key=lambda row: row["minute"])
        assert rows[0]["delay"] == 0

    baseline_state_rows = metrics.read_json(Path(args.state_checkpoints))
    baseline_state_by_opp = collections.defaultdict(list)
    for row in baseline_state_rows:
        baseline_state_by_opp[row["opportunity"]].append(row)
    for rows in baseline_state_by_opp.values():
        rows.sort(key=lambda row: row["delay"])
    assert set(baseline_state_by_opp) == set(minute_by_opp)

    target_ids = {
        oid for oid, rows in baseline_state_by_opp.items()
        if rows[0]["state"] in TARGET_INITIAL_STATES
    }
    assert len(target_ids) == 1757

    # Saved raw price paths are opened before intent construction only to create
    # causal prefixes. Every classifier call receives bar starts strictly < NOW.
    raw_paths = metrics.read_json(Path(args.raw_paths))
    assert set(minute_by_opp).issubset(raw_paths)

    candidate_state_by_opp = {}
    state_future_violations = 0
    target_checkpoint_count = 0
    for oid in sorted(minute_by_opp):
        if oid in target_ids:
            checks, violations = _classify_target_every_minute(
                oid,
                minute_by_opp[oid][0]["session"],
                minute_by_opp[oid],
                raw_paths[oid],
            )
            assert checks[0]["state"] == baseline_state_by_opp[oid][0]["state"], (
                "T0_STATE_CHANGED", oid
            )
            candidate_state_by_opp[oid] = checks
            target_checkpoint_count += len(checks)
            state_future_violations += violations
        else:
            candidate_state_by_opp[oid] = baseline_state_by_opp[oid]

    intents = {
        oid: v3.frozen_intent(
            oid, minute_by_opp[oid], candidate_state_by_opp[oid], base_policy
        )
        for oid in sorted(minute_by_opp)
    }
    causal_intents_sha = hashlib.sha256(
        json.dumps(intents, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()

    # Evaluator-only sources open only after all causal intents are frozen.
    opportunities = metrics.read_json(measurement / "opportunity-records.json.gz")
    quote_source = metrics.read_json(Path(args.rows))
    quote_rows = {
        row["id"]: row for row in quote_source
        if row["opportunity"] in intents and row.get("eligible1")
    }
    del quote_source
    outcomes = metrics.read_json(Path(args.outcomes))
    immediate = metrics.read_json(Path(args.entry_v1_measurement) / "baseline-immediate-records.json.gz")
    signal_only = metrics.read_json(Path(args.entry_v1_measurement) / "baseline-signal-records.json.gz")
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
            oid, opportunity["session"], fill_grid_by_opp[oid], intent,
            quote_rows, outcomes,
        )
        trade["rangeRetention"] = v3.range_retention(opportunity, trade)
        trade["waitMaxRiseVsImmediatePct"] = v3.missed_upside(
            raw_paths[oid], immediate_by_id[oid], trade,
            minute_by_opp[oid][-1]["minute"],
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

    # The intervention is target-only; audit every field in non-target records.
    baseline_by_id = {row["opportunity"]: row for row in state_v3}
    non_target_records_checked = 0
    for record in candidate:
        if record["opportunity"] not in target_ids:
            without_experiment = {k: v for k, v in record.items() if k != "experiment"}
            assert without_experiment == baseline_by_id[record["opportunity"]], (
                "NON_TARGET_RECORD_CHANGED", record["opportunity"]
            )
            non_target_records_checked += 1
    assert non_target_records_checked == 2155 - 1757

    policies = {
        "A_IMMEDIATE": immediate,
        "B_SIGNAL_ONLY": signal_only,
        "C_ENTRY_V1": entry_v1,
        "D_STATE_V3": state_v3,
        "E_DROP_PULL_1M_STATE_RECHECK_V1": candidate,
    }
    summaries = {
        name: metrics.policy_summary(opportunities, rows)
        for name, rows in policies.items()
    }
    paired = {}
    for name in ("A_IMMEDIATE", "C_ENTRY_V1", "D_STATE_V3"):
        paired[name], _ = metrics.paired_summary(
            policies[name], candidate, summaries[name], summaries["E_DROP_PULL_1M_STATE_RECHECK_V1"]
        )

    target_opps = [row for row in opportunities if row["opportunity"] in target_ids]
    target_policies = {
        name: [row for row in rows if row["opportunity"] in target_ids]
        for name, rows in policies.items()
    }
    target_summaries = {
        name: metrics.policy_summary(target_opps, rows)
        for name, rows in target_policies.items()
    }
    target_paired_vs_v3, target_pair_rows = metrics.paired_summary(
        target_policies["D_STATE_V3"],
        target_policies["E_DROP_PULL_1M_STATE_RECHECK_V1"],
        target_summaries["D_STATE_V3"],
        target_summaries["E_DROP_PULL_1M_STATE_RECHECK_V1"],
    )
    positions = {
        name: _position_thresholds(rows)
        for name, rows in target_policies.items()
        if name in ("A_IMMEDIATE", "C_ENTRY_V1", "D_STATE_V3", "E_DROP_PULL_1M_STATE_RECHECK_V1")
    }

    candidate_target = target_summaries["E_DROP_PULL_1M_STATE_RECHECK_V1"]
    base_target = target_summaries["D_STATE_V3"]
    primary_delta = (
        positions["E_DROP_PULL_1M_STATE_RECHECK_V1"]["rates"]["0.25"]["ratePct"]
        - positions["D_STATE_V3"]["rates"]["0.25"]["ratePct"]
    )
    fill_delta = candidate_target["fillRatePct"] - base_target["fillRatePct"]
    cap3_delta = _capture_delta(candidate_target, base_target, 3)
    cap5_delta = _capture_delta(candidate_target, base_target, 5)
    pos_delta = target_paired_vs_v3["entryPositionDelta"]["mean"]
    low_delta = target_paired_vs_v3["lowToEntryDistanceDeltaPct"]["mean"]

    gates = {
        "primary25RateImprovementAtLeast2pp": primary_delta >= 2.0,
        "pairedEntryPositionImproves": pos_delta is not None and pos_delta < 0,
        "pairedLowToEntryImproves": low_delta is not None and low_delta < 0,
        "fillRateNotWorseThan2pp": fill_delta >= -2.0,
        "capture3NotWorseThan2pp": cap3_delta >= -2.0,
        "capture5NotWorseThan2pp": cap5_delta >= -2.0,
        "causality": state_future_violations == 0 and signal_closed_bar_pass == signal_closed_bar_checks,
    }
    status = "PASS_CLEAR_IMPROVEMENT" if all(gates.values()) else "NO_PROMOTION"

    decision_source = inspect.getsource(_classify_target_every_minute) + inspect.getsource(v3.frozen_intent)
    prohibited = _prohibited_decision_tokens(decision_source)
    causality = {
        "status": "PASS" if not prohibited and gates["causality"] else "FAIL",
        "causalIntentSHA256BeforeEvaluatorOpen": causal_intents_sha,
        "evaluatorOpenedAfterAllIntents": True,
        "targetStateDecisionCount": target_checkpoint_count,
        "stateFutureViolations": state_future_violations,
        "signalClosedBarChecks": signal_closed_bar_checks,
        "signalClosedBarPassed": signal_closed_bar_pass,
        "decisionFunctionProhibitedTokens": prohibited,
        "staticScanMode": "AST_EXCLUDING_DOCSTRINGS_ONLY",
        "nonTargetRecordsExactParity": non_target_records_checked,
        "targetT0StatesExactParity": len(target_ids),
        "oracleLowHighDecisionUse": 0,
        "futureOutcomeDecisionUse": 0,
        "stateV3ContractChanged": False,
        "signalDefinitionChanged": False,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "safety": policy["safety"],
    }
    # Preserve the actual audit if a future run fails; never publish a silent PASS.
    metrics.write_json(output / "causality-audit.json", causality)
    assert causality["status"] == "PASS", json.dumps(causality, sort_keys=True)

    summary = {
        "artifactKind": "phase57_drop_pullback_1m_state_recheck_v1_result",
        "version": "v1.0",
        "baseHead": policy["baseHead"],
        "population": 2155,
        "targetPopulation": len(target_ids),
        "hypothesis": policy["hypothesis"],
        "precommittedSuccessGate": policy["successGate"],
        "policies": summaries,
        "pairedCandidateVs": paired,
        "targetCohort": {
            "states": list(TARGET_INITIAL_STATES),
            "summaries": target_summaries,
            "pairedVsStateV3": target_paired_vs_v3,
            "entryPositionThresholds": positions,
            "deltasVsStateV3": {
                "entryPositionLE25RatePp": primary_delta,
                "fillRatePp": fill_delta,
                "capture3Pp": cap3_delta,
                "capture5Pp": cap5_delta,
            },
        },
        "causalityAudit": causality,
        "gateChecks": gates,
        "status": status,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "safety": policy["safety"],
    }
    metrics.write_json(output / "summary.json", summary)
    metrics.write_json(output / "causality-audit.json", causality)
    metrics.write_gzip_json(output / "entry-records.json.gz", candidate)
    metrics.write_gzip_json(output / "target-paired-vs-state-v3.json.gz", target_pair_rows)
    metrics.write_gzip_json(output / "trades.json.gz", raw_trades)
    metrics.write_json(output / "gate.json", {"status": status, "checks": gates})
    manifest = {
        path.name: metrics.sha256(path) for path in sorted(output.iterdir())
        if path.name != "manifest.json"
    }
    metrics.write_json(output / "manifest.json", manifest)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement", required=True)
    parser.add_argument("--entry-v1-measurement", required=True)
    parser.add_argument("--state-v3-measurement", required=True)
    parser.add_argument("--state-checkpoints", required=True)
    parser.add_argument("--raw-paths", required=True)
    parser.add_argument("--rows", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--base-policy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run(args)
    target = result["targetCohort"]
    print(json.dumps({
        "status": result["status"],
        "population": result["population"],
        "targetPopulation": result["targetPopulation"],
        "targetLE25DeltaPp": target["deltasVsStateV3"]["entryPositionLE25RatePp"],
        "targetFillDeltaPp": target["deltasVsStateV3"]["fillRatePp"],
        "targetCapture3DeltaPp": target["deltasVsStateV3"]["capture3Pp"],
        "targetCapture5DeltaPp": target["deltasVsStateV3"]["capture5Pp"],
        "causality": result["causalityAudit"]["status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
