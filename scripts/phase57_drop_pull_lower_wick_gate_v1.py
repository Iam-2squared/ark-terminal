"""Phase57 DROP/PULLBACK Lower-Wick Gate v1.

Precommitted policy-layer experiment.  State-v3 classifier and the six existing
signal definitions are immutable.  For opportunities whose T0 State-v3 state is
DROP or PULLBACK, SIGNAL_TRIGGER is eligible only when the already-frozen
LOWER_WICK family is true.  The existing five-active-minute State-v3 BUY-state
recheck remains unchanged.  Every causal intent is frozen and hashed before any
Oracle/outcome/raw-path evaluator source is opened.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import inspect
import json
from pathlib import Path

from scripts import phase57_state_conditioned_signal_entry_v1 as metrics
from scripts import phase57_state_v3_9pattern_entry_v1 as v3

TARGET_INITIAL_STATES = ("DROP", "PULLBACK")
PRIMARY_SIGNAL = "LOWER_WICK"
POSITION_LEVELS = (0.10, 0.25, 0.50)


def _intent_with_lower_wick_gate(opportunity, minute_rows, state_rows, policy):
    """Causal intent selector; no evaluator fields are accepted or inspected."""
    assert minute_rows and minute_rows[0]["delay"] == 0
    by_minute_state = {row["asOf"]: row for row in state_rows}
    initial = by_minute_state[minute_rows[0]["minute"]]
    initial_state = initial["state"]
    if initial_state not in TARGET_INITIAL_STATES:
        return v3.frozen_intent(opportunity, minute_rows, state_rows, policy)

    first_signal = None
    first_state_buy = None
    all_signal_families = set()
    for row in minute_rows:
        firing_all = tuple(
            family for family in v3.FAMILIES
            if row["signals"][family]["trigger"] is True
        )
        all_signal_families.update(firing_all)
        if row["signals"][PRIMARY_SIGNAL]["trigger"] is True and first_signal is None:
            first_signal = (row["minute"], row["delay"], (PRIMARY_SIGNAL,))
        state_row = by_minute_state.get(row["minute"])
        if (
            row["delay"] > 0 and state_row
            and state_row["state"] in policy["buyStates"]
            and first_state_buy is None
        ):
            first_state_buy = (row["minute"], row["delay"], state_row["state"])

    candidates = []
    if first_signal:
        candidates.append((first_signal[0], 0, "SIGNAL_TRIGGER"))
    if first_state_buy:
        candidates.append((first_state_buy[0], 1, "STATE_TRANSITION_BUY"))
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
        if source_row["signals"][PRIMARY_SIGNAL]["trigger"] is True:
            firing = (PRIMARY_SIGNAL,)
            sources.append("SIGNAL_TRIGGER")
        state_row = by_minute_state.get(minute)
        if state_row and state_row["state"] in policy["buyStates"]:
            sources.append("STATE_TRANSITION_BUY")
            state_at_intent = state_row["state"]

    return {
        "opportunity": opportunity,
        "intentMinute": minute,
        "intentDelay": delay,
        "intentReason": reason,
        "triggerSources": sources,
        "triggerSignals": list(firing),
        "initialState": initial_state,
        "stateAtIntent": state_at_intent,
        "firstSignalMinute": first_signal[0] if first_signal else None,
        "firstSignalDelay": first_signal[1] if first_signal else None,
        "firstStateBuyMinute": first_state_buy[0] if first_state_buy else None,
        "firstStateBuyDelay": first_state_buy[1] if first_state_buy else None,
        "firstTransitionBuyState": first_state_buy[2] if first_state_buy else None,
        "allWindowSignalFamilies": sorted(all_signal_families),
        "signalGate": "LOWER_WICK_ONLY_FOR_DROP_PULLBACK",
    }


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


def _active_add(anchor, delta):
    try:
        ordinal = v3.active_ordinal(anchor) + delta
    except ValueError:
        return None
    if ordinal < 0 or ordinal > 330:
        return None
    if ordinal <= 150:
        return 540 + ordinal
    return 750 + ordinal - 150


def _low_known_minute(oracle):
    minute = oracle.get("lowMinute")
    if minute is None:
        return None
    minute = int(minute)
    if 540 <= minute < 690 or 750 <= minute < 930:
        return minute + 1
    return None


def _low_anatomy(target_ids, opportunities, raw_paths, minute_by_opp):
    offsets = (-10, -5, -3, -1, 0, 1, 3, 5, 10)
    state_counts = {str(offset): collections.Counter() for offset in offsets}
    signal_counts = {str(offset): collections.Counter() for offset in offsets}
    denominators = collections.Counter()
    price_from_low = {str(offset): [] for offset in offsets}
    for opportunity in opportunities:
        oid = opportunity["opportunity"]
        if oid not in target_ids:
            continue
        oracle = opportunity["orderedOracle"]
        if not oracle.get("fullSessionEvaluable") or oracle.get("status") != "OBSERVED_ORDERED_ORACLE":
            continue
        low_known = _low_known_minute(oracle)
        if low_known is None:
            continue
        path = raw_paths[oid]
        day = opportunity["session"]
        previous_session = path.get("previousSession")
        minute_rows = {row["minute"]: row for row in minute_by_opp[oid]}
        for offset in offsets:
            now = _active_add(low_known, offset)
            if now is None or v3.phase_for_anchor(now) is None:
                continue
            prefix = [bar for bar in path["today"] if int(bar[0]) < now]
            classified = v3.classify_state_v3(day, now, prefix, path["previous"], previous_session)
            state_counts[str(offset)][classified["state"] or v3.INVALID_LABEL] += 1
            denominators[str(offset)] += 1
            if prefix and oracle.get("low"):
                latest = float(prefix[-1][4])
                price_from_low[str(offset)].append(metrics.pct(latest, oracle["low"]))
            row = minute_rows.get(now)
            if row:
                firing = [f for f in v3.FAMILIES if row["signals"][f]["trigger"] is True]
                if not firing:
                    signal_counts[str(offset)]["NONE"] += 1
                else:
                    signal_counts[str(offset)].update(firing)
    return {
        "offsetSemantics": "active minutes relative to the first as-of when the oracle-low regular bar has closed; evaluator-only",
        "offsets": {
            str(offset): {
                "denominator": denominators[str(offset)],
                "stateCounts": dict(state_counts[str(offset)]),
                "signalCountsNonExclusive": dict(signal_counts[str(offset)]),
                "priceVsOracleLowPct": metrics.distribution(price_from_low[str(offset)]),
            }
            for offset in offsets
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
    assert policy["baseHead"] == "281f215fa3d86c9ef2dffebce8fd211425b6817c"
    assert tuple(policy["targetInitialStates"]) == TARGET_INITIAL_STATES
    assert policy["signalGate"] == PRIMARY_SIGNAL
    assert tuple(base_policy["buyStates"]) == v3.BUY_STATES
    assert base_policy["fixedTimeFallback"] is False
    assert base_policy["stateRecheckActiveMinutes"] == 5
    assert tuple(base_policy["safety"].keys()) == v3.SAFETY_KEYS
    assert all(value is False for value in base_policy["safety"].values())
    assert policy["providerRequestsAuthorized"] == policy["protectedDataOpened"] == 0
    assert all(value is False for value in policy["safety"].values())

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

    state_rows = metrics.read_json(Path(args.state_checkpoints))
    state_by_opp = collections.defaultdict(list)
    for row in state_rows:
        state_by_opp[row["opportunity"]].append(row)
    for rows in state_by_opp.values():
        rows.sort(key=lambda row: row["delay"])
    assert set(state_by_opp) == set(minute_by_opp)

    intents = {}
    target_ids = set()
    for oid in sorted(minute_by_opp):
        initial = state_by_opp[oid][0]["state"]
        if initial in TARGET_INITIAL_STATES:
            target_ids.add(oid)
        intents[oid] = _intent_with_lower_wick_gate(
            oid, minute_by_opp[oid], state_by_opp[oid], base_policy
        )
    causal_intents_sha = hashlib.sha256(
        json.dumps(intents, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()

    opportunities = metrics.read_json(measurement / "opportunity-records.json.gz")
    raw_paths = metrics.read_json(Path(args.raw_paths))
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
        record["experiment"] = "DROP_PULLBACK_LOWER_WICK_GATE_V1"
        candidate.append(record)
        raw_trades.append({**trade, **{k: intent.get(k) for k in (
            "triggerSources", "triggerSignals", "initialState", "stateAtIntent",
            "firstSignalMinute", "firstSignalDelay", "firstStateBuyMinute",
            "firstStateBuyDelay", "firstTransitionBuyState", "allWindowSignalFamilies",
        )}})

    policies = {
        "A_IMMEDIATE": immediate,
        "B_SIGNAL_ONLY": signal_only,
        "C_ENTRY_V1": entry_v1,
        "D_STATE_V3": state_v3,
        "E_DROP_PULL_LOWER_WICK_GATE_V1": candidate,
    }
    summaries = {name: metrics.policy_summary(opportunities, rows) for name, rows in policies.items()}
    paired = {}
    for name in ("A_IMMEDIATE", "C_ENTRY_V1", "D_STATE_V3"):
        paired[name], _ = metrics.paired_summary(
            policies[name], candidate, summaries[name], summaries["E_DROP_PULL_LOWER_WICK_GATE_V1"]
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
        target_policies["E_DROP_PULL_LOWER_WICK_GATE_V1"],
        target_summaries["D_STATE_V3"],
        target_summaries["E_DROP_PULL_LOWER_WICK_GATE_V1"],
    )
    positions = {
        name: _position_thresholds(rows)
        for name, rows in target_policies.items()
        if name in ("A_IMMEDIATE", "C_ENTRY_V1", "D_STATE_V3", "E_DROP_PULL_LOWER_WICK_GATE_V1")
    }

    candidate_target = target_summaries["E_DROP_PULL_LOWER_WICK_GATE_V1"]
    base_target = target_summaries["D_STATE_V3"]
    primary_delta = (
        positions["E_DROP_PULL_LOWER_WICK_GATE_V1"]["rates"]["0.25"]["ratePct"]
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
        "causality": signal_closed_bar_pass == signal_closed_bar_checks,
    }
    status = "PASS_CLEAR_IMPROVEMENT" if all(gates.values()) else "NO_PROMOTION"

    decision_source = inspect.getsource(_intent_with_lower_wick_gate)
    prohibited = [
        token for token in metrics.FORBIDDEN_DECISION_TOKENS
        if token in decision_source
    ]
    causality = {
        "status": "PASS" if not prohibited and gates["causality"] else "FAIL",
        "causalIntentSHA256BeforeEvaluatorOpen": causal_intents_sha,
        "evaluatorOpenedAfterAllIntents": True,
        "signalClosedBarChecks": signal_closed_bar_checks,
        "signalClosedBarPassed": signal_closed_bar_pass,
        "decisionFunctionProhibitedTokens": prohibited,
        "oracleLowHighDecisionUse": 0,
        "futureOutcomeDecisionUse": 0,
        "stateV3ContractChanged": False,
        "signalDefinitionChanged": False,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "safety": policy["safety"],
    }
    assert causality["status"] == "PASS"

    summary = {
        "artifactKind": "phase57_drop_pullback_lower_wick_gate_v1_result",
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
        "lowCenteredAnatomy": _low_anatomy(target_ids, opportunities, raw_paths, minute_by_opp),
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
    metrics.write_json(output / "low-centered-anatomy.json", summary["lowCenteredAnatomy"])
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
