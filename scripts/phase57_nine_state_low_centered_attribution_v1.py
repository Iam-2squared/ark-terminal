"""Evaluator-only Low-centered attribution for the Phase57 nine-State Entry audit.

This diagnostic computes causal State-v3 and frozen six-signal witnesses for every
available decision checkpoint before opening the already-exposed Development
Oracle anatomy. It does not change Entry decisions. Future Low/High are used only
to align the frozen causal witnesses for attribution after all witness rows are
fixed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import statistics
from pathlib import Path

from scripts import phase57_state_conditioned_signal_entry_v1 as metrics
from scripts import phase57_state_v3_9pattern_entry_v1 as v3
from scripts import phase57_nine_state_anatomy_v1 as anatomy

TARGET_STATES = ("RISE", "DROP", "PULLBACK")
OFFSETS = (-10, -5, -3, -1, 0, 1, 3, 5, 10)
AFTER_WINDOWS = (1, 3, 5, 10)


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def summarize(values):
    clean = [float(v) for v in values if finite(v)]
    return {
        "count": len(clean),
        "mean": statistics.fmean(clean) if clean else None,
        "median": statistics.median(clean) if clean else None,
        "p25": metrics.percentile(clean, .25) if clean else None,
        "p75": metrics.percentile(clean, .75) if clean else None,
    }


def causal_state_rows(day, minute_rows, path):
    out = []
    future_violations = 0
    for row in minute_rows:
        now = int(row["minute"])
        prefix = [bar for bar in path["today"] if int(bar[0]) < now]
        state = v3.classify_state_v3(
            day, now, prefix, path["previous"], path.get("previousSession")
        )
        state = {
            "minute": now,
            "delay": int(row["delay"]),
            "state": state["state"],
            "stateStatus": state["stateStatus"],
            "dataQuality": state["dataQuality"],
            "confidence": state["confidence"],
            "maxSourceBarStart": state["maxSourceBarStart"],
            "unit": state["unit"],
            "priorDir": state["priorDir"],
            "recentDir": state["recentDir"],
            "priorReturn": state["priorReturn"],
            "recentReturn": state["recentReturn"],
            "signalAny": any(
                row["signals"][family]["trigger"] is True for family in metrics.FAMILIES
            ),
            "signalFamilies": [
                family for family in metrics.FAMILIES
                if row["signals"][family]["trigger"] is True
            ],
        }
        if state["maxSourceBarStart"] is not None:
            future_violations += int(state["maxSourceBarStart"] >= now)
        out.append(state)
    return out, future_violations


def rate(count, denominator):
    return 100.0 * count / denominator if denominator else None


def nearest_exact(rows, low_minute, offset):
    matches = []
    for row in rows:
        try:
            delta = v3.active_elapsed(int(low_minute), int(row["minute"]))
        except ValueError:
            continue
        if delta == offset:
            matches.append(row)
    return min(matches, key=lambda row: int(row["minute"])) if matches else None


def first_after(rows, low_minute, predicate):
    matches = []
    for row in rows:
        try:
            delta = v3.active_elapsed(int(low_minute), int(row["minute"]))
        except ValueError:
            continue
        if delta >= 0 and predicate(row):
            matches.append((delta, int(row["minute"]), row))
    return min(matches, key=lambda item: (item[0], item[1])) if matches else None


def state_distribution(rows):
    counts = collections.Counter(row["state"] for row in rows if row)
    n = sum(counts.values())
    buy_count = sum(counts.get(state, 0) for state in v3.BUY_STATES)
    signal_count = sum(bool(row["signalAny"]) for row in rows if row)
    return {
        "n": n,
        "counts": dict(sorted(counts.items())),
        "ratesPct": {key: rate(value, n) for key, value in sorted(counts.items())},
        "buyStateCount": buy_count,
        "buyStateRatePct": rate(buy_count, n),
        "signalAnyCount": signal_count,
        "signalAnyRatePct": rate(signal_count, n),
    }


def run(args):
    measurement = Path(args.measurement)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)

    minute_by_opp = collections.defaultdict(list)
    for path in sorted((measurement / "minute-census").glob("*.json.gz")):
        for row in metrics.read_json(path):
            minute_by_opp[row["opportunity"]].append(row)
    assert len(minute_by_opp) == 2155
    for rows in minute_by_opp.values():
        rows.sort(key=lambda row: int(row["minute"]))
        assert rows and rows[0]["delay"] == 0

    baseline_state_rows = metrics.read_json(Path(args.state_checkpoints))
    baseline_state_by_opp = collections.defaultdict(list)
    for row in baseline_state_rows:
        baseline_state_by_opp[row["opportunity"]].append(row)
    for rows in baseline_state_by_opp.values():
        rows.sort(key=lambda row: int(row["delay"]))
    assert set(baseline_state_by_opp) == set(minute_by_opp)

    target_ids = {
        oid for oid, rows in baseline_state_by_opp.items()
        if rows[0]["state"] in TARGET_STATES
    }
    target_state_by_opp = {
        oid: baseline_state_by_opp[oid][0]["state"] for oid in target_ids
    }
    assert collections.Counter(target_state_by_opp.values()) == {
        "RISE": 111, "DROP": 1403, "PULLBACK": 354
    }

    raw_paths = metrics.read_json(Path(args.raw_paths))
    assert target_ids.issubset(raw_paths)
    causal_by_opp = {}
    future_violations = 0
    closed_bar_checks = 0
    closed_bar_pass = 0
    for oid in sorted(target_ids):
        rows = minute_by_opp[oid]
        states, violations = causal_state_rows(
            rows[0]["session"], rows, raw_paths[oid]
        )
        assert states[0]["state"] == target_state_by_opp[oid]
        causal_by_opp[oid] = states
        future_violations += violations
        for state in states:
            through = state["maxSourceBarStart"]
            if through is not None:
                closed_bar_checks += 1
                closed_bar_pass += int(through < state["minute"])

    causal_sha = hashlib.sha256(
        json.dumps(causal_by_opp, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    assert future_violations == 0
    assert closed_bar_pass == closed_bar_checks

    opportunities = metrics.read_json(measurement / "opportunity-records.json.gz")
    one_minute = metrics.read_json(Path(args.one_minute_records))
    opp_by = {row["opportunity"]: row for row in opportunities}
    one_by = {row["opportunity"]: row for row in one_minute}
    assert set(opp_by) == set(one_by) == set(minute_by_opp)

    states_out = {}
    for target_state in TARGET_STATES:
        ids = sorted(oid for oid in target_ids if target_state_by_opp[oid] == target_state)
        low_evaluable = []
        low_in_window = []
        entry_delta = []
        entry_before_low = 0
        entry_at_or_after_low = 0
        offset_rows = {offset: [] for offset in OFFSETS}
        first_buy_deltas = []
        first_signal_deltas = []
        first_either_deltas = []
        no_buy_after_low = 0
        no_signal_after_low = 0
        no_either_after_low = 0

        for oid in ids:
            oracle = (opp_by[oid].get("orderedOracle") or {})
            low_minute = oracle.get("lowMinute")
            if not isinstance(low_minute, int):
                continue
            low_evaluable.append(oid)
            rows = causal_by_opp[oid]
            ords = []
            try:
                low_ord = v3.active_ordinal(low_minute)
            except ValueError:
                continue
            for row in rows:
                try:
                    ords.append(v3.active_ordinal(int(row["minute"])))
                except ValueError:
                    pass
            if not ords or not (min(ords) <= low_ord <= max(ords)):
                continue
            low_in_window.append(oid)

            for offset in OFFSETS:
                item = nearest_exact(rows, low_minute, offset)
                if item is not None:
                    offset_rows[offset].append(item)

            buy = first_after(rows, low_minute, lambda row: row["state"] in v3.BUY_STATES)
            sig = first_after(rows, low_minute, lambda row: bool(row["signalAny"]))
            either = first_after(
                rows, low_minute,
                lambda row: row["state"] in v3.BUY_STATES or bool(row["signalAny"])
            )
            if buy is None:
                no_buy_after_low += 1
            else:
                first_buy_deltas.append(buy[0])
            if sig is None:
                no_signal_after_low += 1
            else:
                first_signal_deltas.append(sig[0])
            if either is None:
                no_either_after_low += 1
            else:
                first_either_deltas.append(either[0])

            entry_minute = one_by[oid].get("entryMinute")
            if isinstance(entry_minute, int):
                try:
                    delta = v3.active_elapsed(low_minute, entry_minute)
                except ValueError:
                    delta = None
                if delta is not None:
                    entry_delta.append(delta)
                    if delta < 0:
                        entry_before_low += 1
                    else:
                        entry_at_or_after_low += 1

        policy_rows = [one_by[oid] for oid in ids]
        policy_opps = [opp_by[oid] for oid in ids]
        policy_summary = metrics.policy_summary(policy_opps, policy_rows)
        position = anatomy.threshold_summary(policy_rows)

        states_out[target_state] = {
            "population": len(ids),
            "oracleLowMinuteEvaluable": len(low_evaluable),
            "oracleLowWithinDecisionWindow": len(low_in_window),
            "oracleLowWithinDecisionWindowRatePct": rate(len(low_in_window), len(ids)),
            "oneMinuteBaseline": {
                "fills": policy_summary.get("fills"),
                "fillRatePct": policy_summary.get("fillRatePct"),
                "entryPosition": position,
                "capture3": anatomy.capture_at(policy_summary, 3),
                "capture5": anatomy.capture_at(policy_summary, 5),
            },
            "entryMinuteRelativeToOracleLowActiveMinutes": {
                "summary": summarize(entry_delta),
                "beforeLowCount": entry_before_low,
                "atOrAfterLowCount": entry_at_or_after_low,
                "beforeLowRatePctAmongComparableFilled": rate(entry_before_low, len(entry_delta)),
            },
            "offsetWitness": {
                str(offset): state_distribution(offset_rows[offset]) for offset in OFFSETS
            },
            "firstCausalBuyStateAfterOracleLow": {
                "delayActiveMinutes": summarize(first_buy_deltas),
                "missing": no_buy_after_low,
                "withinPct": {
                    str(window): rate(sum(delta <= window for delta in first_buy_deltas), len(low_in_window))
                    for window in AFTER_WINDOWS
                },
            },
            "firstFrozenSignalAfterOracleLow": {
                "delayActiveMinutes": summarize(first_signal_deltas),
                "missing": no_signal_after_low,
                "withinPct": {
                    str(window): rate(sum(delta <= window for delta in first_signal_deltas), len(low_in_window))
                    for window in AFTER_WINDOWS
                },
            },
            "firstEitherAfterOracleLow": {
                "delayActiveMinutes": summarize(first_either_deltas),
                "missing": no_either_after_low,
                "withinPct": {
                    str(window): rate(sum(delta <= window for delta in first_either_deltas), len(low_in_window))
                    for window in AFTER_WINDOWS
                },
            },
        }

    all_policy_summary = metrics.policy_summary(opportunities, one_minute)
    result = {
        "artifactKind": "phase57_nine_state_low_centered_attribution_v1",
        "developmentOnly": True,
        "diagnosticOnlyNoDecisionChange": True,
        "targets": list(TARGET_STATES),
        "population": 2155,
        "causalWitnessSHA256BeforeOracleOpen": causal_sha,
        "causalWitnessBuiltBeforeOracleOpen": True,
        "stateFutureViolations": future_violations,
        "closedBarChecks": closed_bar_checks,
        "closedBarPassed": closed_bar_pass,
        "oracleLowHighDecisionUse": 0,
        "futureOutcomeDecisionUse": 0,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "oneMinuteAll": {
            "fills": all_policy_summary.get("fills"),
            "fillRatePct": all_policy_summary.get("fillRatePct"),
            "entryPosition": anatomy.threshold_summary(one_minute),
            "capture3": anatomy.capture_at(all_policy_summary, 3),
            "capture5": anatomy.capture_at(all_policy_summary, 5),
        },
        "states": states_out,
        "inputHashes": {
            "measurementManifest": metrics.sha256(measurement / "manifest.json"),
            "stateCheckpoints": metrics.sha256(Path(args.state_checkpoints)),
            "rawPaths": metrics.sha256(Path(args.raw_paths)),
            "oneMinuteRecords": metrics.sha256(Path(args.one_minute_records)),
        },
    }

    out = output / "summary.json"
    metrics.write_json(out, result)
    metrics.write_json(output / "manifest.json", {"summary.json": metrics.sha256(out)})

    print(json.dumps({
        "kind": result["artifactKind"],
        "oneMinuteAll": result["oneMinuteAll"],
        "targets": {
            state: {
                "population": block["population"],
                "lowInWindow": block["oracleLowWithinDecisionWindow"],
                "fillRatePct": block["oneMinuteBaseline"]["fillRatePct"],
                "entryPositionMean": block["oneMinuteBaseline"]["entryPosition"]["mean"],
                "entryPositionMedian": block["oneMinuteBaseline"]["entryPosition"]["median"],
                "le15PctRate": block["oneMinuteBaseline"]["entryPosition"]["thresholds"]["le15pct"]["ratePct"],
                "le25PctRate": block["oneMinuteBaseline"]["entryPosition"]["thresholds"]["le25pct"]["ratePct"],
                "entryBeforeLowRatePct": block["entryMinuteRelativeToOracleLowActiveMinutes"]["beforeLowRatePctAmongComparableFilled"],
                "firstEitherWithin1Pct": block["firstEitherAfterOracleLow"]["withinPct"]["1"],
                "firstEitherWithin3Pct": block["firstEitherAfterOracleLow"]["withinPct"]["3"],
                "firstEitherWithin5Pct": block["firstEitherAfterOracleLow"]["withinPct"]["5"],
            }
            for state, block in states_out.items()
        },
    }, sort_keys=True, allow_nan=False))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement", required=True)
    parser.add_argument("--state-checkpoints", required=True)
    parser.add_argument("--raw-paths", required=True)
    parser.add_argument("--one-minute-records", required=True)
    parser.add_argument("--output", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
