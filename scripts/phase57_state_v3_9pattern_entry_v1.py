"""Phase57 State v3 nine-pattern recognition and Entry v1 replay.

The classifier receives only a previous-session path and a current-session
prefix whose raw bar starts are strictly earlier than ``as_of``.  Full paths,
fills, Oracle anatomy and labels stay outside the decision functions.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import inspect
import json
import math
from pathlib import Path

from scripts import phase57_state_conditioned_signal_entry_v1 as metrics


PATTERNS = (
    "RISE_STOP", "RISE", "SHARP_RISE", "PULLBACK", "RANGE",
    "REBOUND", "SHARP_DROP", "DROP", "DROP_STOP",
)
BUY_STATES = ("RISE", "SHARP_RISE", "REBOUND")
WAIT_STATES = tuple(x for x in PATTERNS if x not in BUY_STATES)
FAMILIES = metrics.FAMILIES
SAFETY_KEYS = metrics.SAFETY_KEYS
LEVELS = metrics.LEVELS
INVALID_LABEL = "INVALID_NULL"
U_FLOOR = math.log(1.001)


def sha256(path: Path) -> str:
    return metrics.sha256(path)


def read_json(path: Path):
    return metrics.read_json(path)


def write_json(path: Path, value) -> None:
    metrics.write_json(path, value)


def write_gzip_json(path: Path, value) -> None:
    metrics.write_gzip_json(path, value)


def finite_positive(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value)) and value > 0


def phase_for_bar_start(minute: int):
    if 540 <= minute < 690:
        return "AM"
    if 750 <= minute < 930:
        return "PM"
    return None


def phase_for_anchor(minute: int):
    if 540 <= minute <= 690:
        return "AM"
    if 750 <= minute <= 930:
        return "PM"
    return None


def active_ordinal(minute: int) -> int:
    """Session-active coordinate for anchors/checkpoints, lunch removed."""
    if 540 <= minute <= 690:
        return minute - 540
    if 750 <= minute <= 930:
        return 150 + minute - 750
    raise ValueError(f"OUTSIDE_ACTIVE_SESSION:{minute}")


def active_elapsed(start: int, end: int) -> int:
    return active_ordinal(end) - active_ordinal(start)


def expected_recent_starts(as_of: int, width: int = 10):
    phase = phase_for_anchor(as_of)
    if phase == "AM":
        lo = max(540, as_of - width)
        return list(range(lo, as_of))
    if phase == "PM":
        lo = max(750, as_of - width)
        return list(range(lo, as_of))
    return []


def log_return(last: float, first: float) -> float:
    return math.log(last / first)


def sign_at_unit(value: float, unit: float) -> int:
    if value >= unit:
        return 1
    if value <= -unit:
        return -1
    return 0


def previous_scale(previous):
    returns = []
    regular = [row for row in previous if phase_for_bar_start(int(row[0]))]
    for left, right in zip(regular, regular[1:]):
        lm, rm = int(left[0]), int(right[0])
        if rm == lm + 1 and phase_for_bar_start(lm) == phase_for_bar_start(rm):
            if finite_positive(left[4]) and finite_positive(right[4]):
                returns.append(abs(log_return(float(right[4]), float(left[4]))))
    if not returns:
        return U_FLOOR, 0
    return max(U_FLOOR, 0.5 * metrics.percentile(returns, .5)), len(returns)


def invalid_result(as_of, reasons, maximum_source=None):
    return {
        "state": None,
        "stateStatus": "NOT_COMPUTED",
        "dataQuality": "INVALID",
        "confidence": "NOT_ASSESSED",
        "reasonCodes": sorted(set(reasons)),
        "asOf": as_of,
        "lastPriceTime": None,
        "maxSourceBarStart": maximum_source,
        "maxSourceBarEnd": maximum_source + 1 if maximum_source is not None else None,
        "inputCutoff": as_of,
        "unit": None,
        "priorDir": None,
        "recentDir": None,
        "priorReturn": None,
        "recentReturn": None,
        "recentCoverage": None,
        "recentTransitions": 0,
        "earlierTransitions": 0,
        "contractVersion": "phase57-state-v3-price-shape-step1-v1",
    }


def classify_state_v3(day: str, as_of: int, today_prefix, previous,
                      previous_session: str | None):
    """Implement the frozen STEP 1 price-shape contract on causal inputs."""
    reasons = []
    if not phase_for_anchor(as_of):
        return invalid_result(as_of, ["ASOF_OUTSIDE_ACTIVE_SESSION"])
    if previous_session is not None and previous_session >= day:
        return invalid_result(as_of, ["PREVIOUS_SESSION_IDENTITY_INVALID"])

    today = [list(row) for row in today_prefix if phase_for_bar_start(int(row[0]))]
    prev = [list(row) for row in previous if phase_for_bar_start(int(row[0]))]
    maximum_source = max((int(row[0]) for row in today), default=None)
    if any(int(row[0]) >= as_of for row in today):
        raise ValueError("FUTURE_OR_UNCLOSED_BAR")
    for name, rows in (("TODAY", today), ("PREVIOUS", prev)):
        stamps = [int(row[0]) for row in rows]
        if stamps != sorted(stamps) or len(stamps) != len(set(stamps)):
            return invalid_result(as_of, [f"{name}_TIMESTAMP_CONFLICT"], maximum_source)
        if any(not finite_positive(row[1]) or not finite_positive(row[4]) for row in rows):
            return invalid_result(as_of, [f"{name}_PRICE_INVALID"], maximum_source)

    unit, previous_adjacent_n = previous_scale(prev)
    official_open = None
    if today and int(today[0][0]) == 540:
        official_open = float(today[0][1])
    elif today:
        reasons.append("OFFICIAL_OPEN_MISSING")

    points = []
    if official_open is not None:
        points.append((540, official_open, "OFFICIAL_OPEN"))
    points.extend((int(row[0]) + 1, float(row[4]), "CLOSED_BAR") for row in today)
    # The open and each close have distinct availability timestamps.
    if not points:
        if not prev:
            return invalid_result(as_of, ["NO_TRUSTWORTHY_POSITIVE_PRICE_ANCHOR"], maximum_source)
        # Contract: prior to the first today price, use the known prior close as
        # a one-anchor context and still return a total nine-pattern state.
        prior_only = True
        last_price_time = None
        reasons.extend(("TODAY_PRICE_UNAVAILABLE", "PRIOR_CLOSE_CONTEXT_ONLY"))
    else:
        prior_only = False
        last_price_time = points[-1][0]

    expected = expected_recent_starts(as_of)
    observed_starts = {int(row[0]) for row in today}
    recent_observed = sum(m in observed_starts for m in expected)
    recent_coverage = recent_observed / len(expected) if expected else 0.0
    stale = bool(expected) and expected[-1] not in observed_starts
    if recent_coverage < .8:
        reasons.append("RECENT_COVERAGE_LT_80PCT")
    if stale:
        reasons.append("STALE_LATEST_ANCHOR")
    if not prev:
        reasons.append("PREVIOUS_SESSION_UNAVAILABLE")
    elif previous_session is None:
        reasons.append("PREVIOUS_SESSION_IDENTITY_MISSING")
    if previous_adjacent_n == 0:
        reasons.append("PREVIOUS_ONE_MINUTE_SCALE_FALLBACK")

    quality = (
        "OK" if points and official_open is not None and prev and previous_session is not None
        and recent_coverage >= .8 and not stale else "DEGRADED"
    )

    prev_return = 0.0
    prev_duration = 1
    prev_transitions = max(0, len(prev) - 1)
    if len(prev) >= 2:
        prev_return = log_return(float(prev[-1][4]), float(prev[0][4]))
        prev_duration = max(1, active_elapsed(int(prev[0][0]) + 1, int(prev[-1][0]) + 1))

    if prior_only:
        prior_dir = sign_at_unit(prev_return, unit)
        state = "RISE" if prior_dir > 0 else "DROP" if prior_dir < 0 else "RANGE"
        confidence = "LOW"
        return {
            "state": state, "stateStatus": "CLASSIFIED", "dataQuality": quality,
            "confidence": confidence, "reasonCodes": sorted(set(reasons)), "asOf": as_of,
            "lastPriceTime": last_price_time, "maxSourceBarStart": maximum_source,
            "maxSourceBarEnd": maximum_source + 1 if maximum_source is not None else None,
            "inputCutoff": as_of, "unit": unit, "priorDir": prior_dir, "recentDir": 0,
            "priorReturn": prev_return, "recentReturn": 0.0,
            "recentCoverage": recent_coverage, "recentTransitions": 0,
            "earlierTransitions": 0, "contractVersion": "phase57-state-v3-price-shape-step1-v1",
        }

    latest_time = points[-1][0]
    latest_phase = phase_for_anchor(latest_time)
    recent_points = [
        p for p in points
        if phase_for_anchor(p[0]) == latest_phase and 0 <= active_elapsed(p[0], latest_time) <= 10
    ]
    if len(recent_points) >= 2:
        earlier_points = [p for p in points if active_ordinal(p[0]) <= active_ordinal(recent_points[0][0])]
    else:
        earlier_points = list(points)
    recent_transitions = max(0, len(recent_points) - 1)
    earlier_transitions = max(0, len(earlier_points) - 1)
    today_transitions = max(0, len(points) - 1)
    recent_return = (
        log_return(recent_points[-1][1], recent_points[0][1])
        if recent_transitions else 0.0
    )
    earlier_return = (
        log_return(earlier_points[-1][1], earlier_points[0][1])
        if earlier_transitions else 0.0
    )
    earlier_determines = earlier_transitions >= 2 and abs(earlier_return) >= unit
    if earlier_determines:
        prior_return = earlier_return
        prior_duration = max(1, active_elapsed(earlier_points[0][0], earlier_points[-1][0]))
        prior_source = "TODAY_EARLIER"
    else:
        prior_return = prev_return
        prior_duration = prev_duration
        prior_source = "PREVIOUS_SESSION_CONTEXT"
        reasons.append("PRIOR_DIRECTION_FROM_PREVIOUS_SESSION")
    prior_dir = sign_at_unit(prior_return, unit)
    recent_dir = sign_at_unit(recent_return, unit)

    if quality == "OK" and earlier_transitions >= 2 and recent_transitions >= 2:
        confidence = "HIGH"
    elif quality == "OK" or (earlier_transitions >= 1 and recent_transitions >= 1):
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    state = None
    decision_reason = None
    if recent_transitions == 0:
        state = "RISE" if prior_dir > 0 else "DROP" if prior_dir < 0 else "RANGE"
        decision_reason = "NO_RECENT_PAIR_CARRY_PRIOR_OR_RANGE"
    elif prior_dir * recent_dir == -1:
        partial = abs(recent_return) < abs(prior_return)
        if prior_dir > 0:
            state = "PULLBACK" if partial else "DROP"
        else:
            state = "REBOUND" if partial else "RISE"
        decision_reason = "OPPOSING_DIRECTION_PARTIAL" if partial else "OPPOSING_DIRECTION_FULL"
    elif recent_dir == 0:
        prices = [p[1] for p in points]
        latest = recent_points[-1][1]
        complete_recent = bool(expected) and recent_coverage == 1.0 and not stale
        enough_stop_history = recent_transitions >= 2 and (
            prior_source == "TODAY_EARLIER" or today_transitions >= 2
        )
        near_high = abs(log_return(max(prices), latest)) <= unit
        near_low = abs(log_return(latest, min(prices))) <= unit
        if prior_dir > 0 and enough_stop_history and complete_recent and near_high:
            state, decision_reason = "RISE_STOP", "OBSERVED_PLATEAU_AT_PREFIX_HIGH"
        elif prior_dir < 0 and enough_stop_history and complete_recent and near_low:
            state, decision_reason = "DROP_STOP", "OBSERVED_PLATEAU_AT_PREFIX_LOW"
        elif prior_dir and (recent_transitions < 2 or stale or recent_coverage < 1.0):
            state = "RISE" if prior_dir > 0 else "DROP"
            decision_reason = "FLAT_BUT_SPARSE_OR_STALE_CARRY_PRIOR"
            confidence = "LOW"
        else:
            state, decision_reason = "RANGE", "OBSERVED_FLAT_NOT_ELIGIBLE_STOP"
    else:
        if earlier_transitions:
            shock_prior_return = earlier_return
            shock_prior_duration = max(
                1, active_elapsed(earlier_points[0][0], earlier_points[-1][0])
            )
        else:
            shock_prior_return = prev_return
            shock_prior_duration = prev_duration
        recent_duration = max(
            1, active_elapsed(recent_points[0][0], recent_points[-1][0])
        )
        shock = (
            recent_transitions >= 3
            and abs(recent_return) >= 3 * unit
            and abs(shock_prior_return) < 2 * unit
            and abs(recent_return) / recent_duration
            >= 2 * abs(shock_prior_return) / max(1, shock_prior_duration)
            and prior_dir in (0, recent_dir)
        )
        if recent_dir > 0:
            state = "SHARP_RISE" if shock else "RISE"
        else:
            state = "SHARP_DROP" if shock else "DROP"
        decision_reason = "ELIGIBLE_SHOCK" if shock else "ORDINARY_DIRECTION"

    assert state in PATTERNS
    reasons.append(decision_reason)
    return {
        "state": state,
        "stateStatus": "CLASSIFIED",
        "dataQuality": quality,
        "confidence": confidence,
        "reasonCodes": sorted(set(reasons)),
        "asOf": as_of,
        "lastPriceTime": latest_time,
        "maxSourceBarStart": maximum_source,
        "maxSourceBarEnd": maximum_source + 1 if maximum_source is not None else None,
        "inputCutoff": as_of,
        "unit": unit,
        "priorDir": prior_dir,
        "recentDir": recent_dir,
        "priorReturn": prior_return,
        "recentReturn": recent_return,
        "recentCoverage": recent_coverage,
        "recentTransitions": recent_transitions,
        "earlierTransitions": earlier_transitions,
        "contractVersion": "phase57-state-v3-price-shape-step1-v1",
    }


def frozen_intent(opportunity, minute_rows, state_rows, policy):
    """Select first causal intent; never sees quote, fill, Oracle or outcome."""
    assert minute_rows and minute_rows[0]["delay"] == 0
    by_minute_state = {row["asOf"]: row for row in state_rows}
    initial = by_minute_state[minute_rows[0]["minute"]]
    initial_buy = initial["state"] in policy["buyStates"]
    first_signal = None
    first_state_buy = None
    all_signal_families = set()
    for row in minute_rows:
        firing = tuple(f for f in FAMILIES if row["signals"][f]["trigger"] is True)
        all_signal_families.update(firing)
        if firing and first_signal is None:
            first_signal = (row["minute"], row["delay"], firing)
        state_row = by_minute_state.get(row["minute"])
        if row["delay"] > 0 and state_row and state_row["state"] in policy["buyStates"]:
            if first_state_buy is None:
                first_state_buy = (
                    row["minute"], row["delay"], state_row["state"]
                )
    if initial_buy:
        t = minute_rows[0]["minute"]
        firing = tuple(f for f in FAMILIES if minute_rows[0]["signals"][f]["trigger"] is True)
        return {
            "opportunity": opportunity,
            "intentMinute": t,
            "intentDelay": 0,
            "intentReason": "INITIAL_STATE_BUY",
            "triggerSources": ["INITIAL_STATE_BUY"] + (["SIGNAL_TRIGGER"] if firing else []),
            "triggerSignals": list(firing),
            "initialState": initial["state"],
            "stateAtIntent": initial["state"],
            "firstSignalMinute": first_signal[0] if first_signal else None,
            "firstSignalDelay": first_signal[1] if first_signal else None,
            "firstStateBuyMinute": t,
            "firstStateBuyDelay": 0,
            "firstTransitionBuyState": None,
            "allWindowSignalFamilies": sorted(all_signal_families),
        }
    candidates = []
    if first_signal:
        candidates.append((first_signal[0], 0, "SIGNAL_TRIGGER"))
    if first_state_buy:
        candidates.append((first_state_buy[0], 1, "STATE_TRANSITION_BUY"))
    if not candidates:
        minute = delay = reason = None
    else:
        minute, _, reason = min(candidates)
        delay = next(row["delay"] for row in minute_rows if row["minute"] == minute)
    sources = []
    firing = ()
    state_at_intent = None
    if minute is not None:
        source_row = next(row for row in minute_rows if row["minute"] == minute)
        firing = tuple(f for f in FAMILIES if source_row["signals"][f]["trigger"] is True)
        if firing:
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
        "initialState": initial["state"],
        "stateAtIntent": state_at_intent,
        "firstSignalMinute": first_signal[0] if first_signal else None,
        "firstSignalDelay": first_signal[1] if first_signal else None,
        "firstStateBuyMinute": first_state_buy[0] if first_state_buy else None,
        "firstStateBuyDelay": first_state_buy[1] if first_state_buy else None,
        "firstTransitionBuyState": first_state_buy[2] if first_state_buy else None,
        "allWindowSignalFamilies": sorted(all_signal_families),
    }


def simulate_fill(oid, session, grid_rows, intent, quote_rows, outcomes):
    """Evaluator-side frozen fill proxy, called only after all intents exist."""
    attempts = []
    fill_minute = None
    price = None
    for row in grid_rows:
        minute = row["minute"]
        if intent["intentMinute"] is None or minute < intent["intentMinute"]:
            continue
        source = quote_rows.get(f"{oid}|{minute}")
        item = {"minute": minute, "intentReason": intent["intentReason"]}
        if not source or not source.get("quoteAvailable", False):
            item.update(result="UNAVAILABLE_REFERENCE", reason="STALE_OR_MISSING_REFERENCE")
        else:
            label = outcomes.get(f"{oid}|{minute}")
            value = label.get("price") if label else None
            if value is None:
                item.update(result="UNFILLED", reason="MISSING_SOURCE_UNCLASSIFIED")
            else:
                price = value
                fill_minute = minute
                item.update(result="FILLED_PROXY", price=value)
        attempts.append(item)
        if fill_minute is not None:
            break
    if fill_minute is not None:
        unfilled = None
    elif intent["intentMinute"] is None:
        unfilled = "NO_TRIGGER_WINDOW_END"
    else:
        unfilled = "RETRY_EXHAUSTED"
    delay = None
    if fill_minute is not None:
        delay = next(row["delay"] for row in grid_rows if row["minute"] == fill_minute)
    return {
        "opportunity": oid,
        "session": session,
        "entryId": f"{oid}|{fill_minute}" if fill_minute is not None else None,
        "entryMinute": fill_minute,
        "price": price,
        "delay": delay,
        "intentMinute": intent["intentMinute"],
        "intentReason": intent["intentReason"] or "NO_TRIGGER",
        "fallbackTargetDelay": None,
        "attempts": attempts,
        "buyAttemptCount": len(attempts),
        "retryCount": max(0, len(attempts) - 1),
        "unfilledReason": unfilled,
        "modelRejection": False,
    }


def range_retention(opportunity, trade):
    oracle = opportunity["orderedOracle"]
    if trade["entryId"] is None:
        return {"valuePct": None, "status": "NO_FILL"}
    if not oracle.get("fullSessionEvaluable"):
        return {"valuePct": None, "status": "FULL_SESSION_OBSERVATION_INSUFFICIENT"}
    if oracle.get("status") != "OBSERVED_ORDERED_ORACLE" or oracle.get("rangePct", 0) <= 0:
        return {"valuePct": None, "status": "INSUFFICIENT_OR_NONPOSITIVE_ORACLE"}
    if oracle["highMinute"] <= trade["entryMinute"]:
        return {"valuePct": None, "status": "ORACLE_HIGH_AT_OR_BEFORE_ENTRY"}
    status = (
        "ENTRY_BEFORE_ORACLE_LOW"
        if trade["entryMinute"] < oracle["lowMinute"] else "ENTRY_AT_OR_AFTER_ORACLE_LOW"
    )
    return {
        "valuePct": 100 * metrics.pct(oracle["high"], trade["price"]) / oracle["rangePct"],
        "status": status,
    }


def missed_upside(path, immediate, candidate, window_end):
    if not immediate.get("entryId"):
        return None
    end = candidate["entryMinute"] if candidate.get("entryId") else window_end
    if end is None:
        return None
    bars = [
        row for row in path["today"]
        if phase_for_bar_start(int(row[0]))
        and int(row[0]) >= immediate["entryMinute"] and int(row[0]) < end
    ]
    if not bars:
        return 0.0 if candidate.get("entryId") and end == immediate["entryMinute"] else None
    return max(0.0, metrics.pct(max(float(row[2]) for row in bars), immediate["price"]))


def candidate_record(opportunity, intent, trade, quality, labels):
    return {
        "opportunity": opportunity["opportunity"],
        "session": opportunity["session"],
        "symbol": opportunity["symbol"],
        "initialState": intent["initialState"],
        "sourceArm": "STATE_V3_9PATTERN",
        "policyAction": "BUY_NOW" if intent["intentReason"] == "INITIAL_STATE_BUY" else "WAIT",
        "stateAtIntent": intent["stateAtIntent"],
        "intentSignals": intent["triggerSignals"],
        "triggerSources": intent["triggerSources"],
        "intentReason": intent["intentReason"] or "NO_TRIGGER",
        "entryReason": intent["intentReason"] if trade["entryId"] else "NO_ENTRY",
        "intentMinute": trade["intentMinute"],
        "entryId": trade["entryId"],
        "entryMinute": trade["entryMinute"],
        "price": trade["price"],
        "delay": trade["delay"],
        "unfilledReason": trade["unfilledReason"],
        "fallbackTargetDelay": None,
        "waitMaxRiseVsImmediatePct": trade.get("waitMaxRiseVsImmediatePct"),
        "quality": quality,
        "labels": labels,
        "firstSignalMinute": intent["firstSignalMinute"],
        "firstSignalDelay": intent["firstSignalDelay"],
        "firstStateBuyMinute": intent["firstStateBuyMinute"],
        "firstStateBuyDelay": intent["firstStateBuyDelay"],
        "firstTransitionBuyState": intent["firstTransitionBuyState"],
        "allWindowSignalFamilies": intent["allWindowSignalFamilies"],
    }


def verify_inputs(args, policy, contract):
    assert tuple(contract["patternIds"]) == PATTERNS
    assert contract["normalization"]["recentActiveMinutes"] == 10
    assert contract["normalization"]["shockThresholdUnits"] == 3
    assert contract["invalidState"] is None
    assert policy["lockedBeforeMeasurement"] is True
    assert policy["population"] == 2155
    assert tuple(policy["buyStates"]) == BUY_STATES
    assert tuple(policy["waitStates"]) == WAIT_STATES
    assert policy["fixedTimeFallback"] is False
    assert tuple(policy["safety"].keys()) == SAFETY_KEYS
    assert all(value is False for value in policy["safety"].values())
    assert policy["providerRequestsAuthorized"] == policy["protectedDataOpened"] == 0
    pins = policy["inputPins"]
    files = {
        "step1ContractJSONSHA256": Path(args.contract),
        "step1ContractMarkdownSHA256": Path(args.contract_markdown),
        "entryTimingMeasurementManifestSHA256": Path(args.measurement) / "manifest.json",
        "entryV1MeasurementManifestSHA256": Path(args.entry_v1_measurement) / "manifest.json",
        "signalDetectorSHA256": Path(args.signal_detector),
        "opportunityRecordsSHA256": Path(args.measurement) / "opportunity-records.json.gz",
        "immediateRecordsSHA256": Path(args.entry_v1_measurement) / "baseline-immediate-records.json.gz",
        "signalOnlyRecordsSHA256": Path(args.entry_v1_measurement) / "baseline-signal-records.json.gz",
        "entryV1RecordsSHA256": Path(args.entry_v1_measurement) / "entry-records.json.gz",
        "rawPathsSHA256": Path(args.raw_paths),
        "rowsSHA256": Path(args.rows),
        "outcomesSHA256": Path(args.outcomes),
    }
    for key, path in files.items():
        assert sha256(path) == pins[key], (key, path, sha256(path), pins[key])
    existing_manifest = read_json(Path(args.measurement) / "manifest.json")
    for path in sorted((Path(args.measurement) / "minute-census").glob("*.json.gz")):
        assert sha256(path) == existing_manifest[f"minute-census/{path.name}"], path.name
    return {key: sha256(path) for key, path in files.items()}


def run(args):
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    policy = read_json(Path(args.policy))
    contract = read_json(Path(args.contract))
    input_hashes = verify_inputs(args, policy, contract)

    # Causal sources only: frozen signals and raw price paths.  Oracle and
    # outcomes are intentionally not opened until every intent is frozen.
    minute_by_opp = collections.defaultdict(list)
    fill_grid_by_opp = collections.defaultdict(list)
    checkpoint_assertions = 0
    signal_closed_bar_pass = 0
    signal_pivot_checks = 0
    signal_pivot_violations = 0
    measurement = Path(args.measurement)
    for path in sorted((measurement / "minute-census").glob("*.json.gz")):
        for row in read_json(path):
            # Decision observation includes T0 and the terminal T+30 closed
            # checkpoint.  The pre-existing fill grid excludes lunch/session
            # boundary instants; keep that separate for exact baseline fills.
            if row["delay"] > policy["entryWindow"]["maximumActiveMinutes"]:
                continue
            minute_by_opp[row["opportunity"]].append(row)
            if row["comparisonEligible"]:
                fill_grid_by_opp[row["opportunity"]].append(row)
            checkpoint_assertions += 1
            through = row.get("computedThroughBarStart")
            signal_closed_bar_pass += through is None or through < row["minute"]
            pivot = row["signals"]["HIGHER_LOW"].get("pivot")
            if pivot:
                signal_pivot_checks += 1
                signal_pivot_violations += not (
                    pivot["lowBarStart"] < pivot["confirmedAt"] <= row["minute"]
                )
    assert len(minute_by_opp) == 2155
    assert len(fill_grid_by_opp) == 2155
    for rows in minute_by_opp.values():
        rows.sort(key=lambda row: row["minute"])
        assert rows[0]["delay"] == 0
        assert all(b["delay"] > a["delay"] for a, b in zip(rows, rows[1:]))

    raw_paths = read_json(Path(args.raw_paths))
    assert set(minute_by_opp).issubset(raw_paths)
    state_records = []
    state_by_opp = {}
    intents = {}
    state_future_violations = 0
    invalid_reason_counts = collections.Counter()
    for oid in sorted(minute_by_opp):
        day = minute_by_opp[oid][0]["session"]
        path = raw_paths[oid]
        previous_session = path.get("previousSession")
        checks = []
        for row in minute_by_opp[oid]:
            if row["delay"] % policy["stateRecheckActiveMinutes"]:
                continue
            now = row["minute"]
            prefix = [bar for bar in path["today"] if int(bar[0]) < now]
            classified = classify_state_v3(
                day, now, prefix, path["previous"], previous_session
            )
            classified.update(
                opportunity=oid, session=day, delay=row["delay"],
                inputTodayPrefixRows=len(prefix),
                inputPreviousRows=len(path["previous"]),
            )
            if classified["maxSourceBarStart"] is not None:
                state_future_violations += classified["maxSourceBarStart"] >= now
            if classified["dataQuality"] == "INVALID":
                invalid_reason_counts.update(classified["reasonCodes"])
            checks.append(classified)
            state_records.append(classified)
        assert checks and checks[0]["delay"] == 0
        state_by_opp[oid] = checks
        intents[oid] = frozen_intent(oid, minute_by_opp[oid], checks, policy)
    assert len(intents) == 2155
    causal_intents_sha = hashlib.sha256(
        json.dumps(intents, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()

    # Only now open evaluator-only opportunity anatomy, fill rows and outcomes.
    opportunities = read_json(measurement / "opportunity-records.json.gz")
    opportunity_by_id = {row["opportunity"]: row for row in opportunities}
    quote_source = read_json(Path(args.rows))
    quote_rows = {
        row["id"]: row for row in quote_source
        if row["opportunity"] in intents and row.get("eligible1")
    }
    del quote_source
    outcomes = read_json(Path(args.outcomes))
    immediate = read_json(Path(args.entry_v1_measurement) / "baseline-immediate-records.json.gz")
    signal_only = read_json(Path(args.entry_v1_measurement) / "baseline-signal-records.json.gz")
    entry_v1 = read_json(Path(args.entry_v1_measurement) / "entry-records.json.gz")
    immediate_by_id = {row["opportunity"]: row for row in immediate}
    assert [row["opportunity"] for row in opportunities] == sorted(intents)
    assert all(len(rows) and rows[-1]["minute"] <= 925 for rows in minute_by_opp.values())

    candidate = []
    raw_trades = []
    for opportunity in opportunities:
        oid = opportunity["opportunity"]
        intent = intents[oid]
        trade = simulate_fill(
            oid, opportunity["session"], fill_grid_by_opp[oid], intent,
            quote_rows, outcomes,
        )
        trade["rangeRetention"] = range_retention(opportunity, trade)
        trade["waitMaxRiseVsImmediatePct"] = missed_upside(
            raw_paths[oid], immediate_by_id[oid], trade,
            minute_by_opp[oid][-1]["minute"],
        )
        quality = metrics.oracle_metrics(opportunity, trade)
        labels = metrics.label_metrics(trade, outcomes)
        candidate.append(candidate_record(opportunity, intent, trade, quality, labels))
        raw_trades.append({**trade, **{k: intent[k] for k in (
            "triggerSources", "triggerSignals", "initialState", "stateAtIntent",
            "firstSignalMinute", "firstSignalDelay", "firstStateBuyMinute",
            "firstStateBuyDelay", "firstTransitionBuyState", "allWindowSignalFamilies",
        )}})
    assert len(candidate) == 2155

    policies = {
        "A_IMMEDIATE": immediate,
        "B_SIGNAL_ONLY": signal_only,
        "C_ENTRY_V1": entry_v1,
        "D_STATE_V3": candidate,
    }
    summaries = {
        name: metrics.policy_summary(opportunities, rows)
        for name, rows in policies.items()
    }
    paired = {}
    paired_rows = {}
    for base_name in ("A_IMMEDIATE", "B_SIGNAL_ONLY", "C_ENTRY_V1"):
        result, rows = metrics.paired_summary(
            policies[base_name], candidate, summaries[base_name], summaries["D_STATE_V3"]
        )
        paired[base_name] = result
        paired_rows[base_name] = rows

    # Frozen baseline parity against the already accepted Entry-v1 summary.
    old_summary = read_json(Path(args.entry_v1_measurement) / "summary.json")
    parity = []
    for new_name, old_name in (
        ("A_IMMEDIATE", "A_IMMEDIATE"),
        ("B_SIGNAL_ONLY", "B_SIGNAL_ONLY"),
        ("C_ENTRY_V1", "C_ENTRY_V1"),
    ):
        new, old = summaries[new_name], old_summary["policies"][old_name]
        parity.extend((
            {"check": f"{new_name}/population", "pass": new["population"] == old["population"]},
            {"check": f"{new_name}/fills", "pass": new["fills"] == old["fills"]},
            {"check": f"{new_name}/delayMean", "pass": new["delay"]["mean"] == old["delay"]["mean"]},
        ))
        for level in LEVELS:
            parity.append({
                "check": f"{new_name}/capture{level}",
                "pass": math.isclose(
                    new["capture"][str(level)]["ratePct"],
                    old["capture"][str(level)]["ratePct"],
                    abs_tol=1e-12,
                ),
            })
    assert all(item["pass"] for item in parity)

    state_labels = PATTERNS + (INVALID_LABEL,)
    initial_counts = collections.Counter(
        row["state"] if row["state"] is not None else INVALID_LABEL
        for row in (state_by_opp[oid][0] for oid in sorted(state_by_opp))
    )
    t0_quality = collections.Counter(state_by_opp[oid][0]["dataQuality"] for oid in state_by_opp)
    t0_confidence = collections.Counter(state_by_opp[oid][0]["confidence"] for oid in state_by_opp)
    all_quality = collections.Counter(row["dataQuality"] for row in state_records)
    all_confidence = collections.Counter(row["confidence"] for row in state_records)
    transitions = collections.Counter()
    transitions_to_buy = collections.Counter()
    for oid, rows in state_by_opp.items():
        labels = [row["state"] if row["state"] is not None else INVALID_LABEL for row in rows]
        for left, right in zip(labels, labels[1:]):
            transitions[(left, right)] += 1
            if left != right and right in BUY_STATES:
                transitions_to_buy[(left, right)] += 1
    initial_valid = 2155 - initial_counts[INVALID_LABEL]
    state_summary = {
        "population": 2155,
        "checkpointPopulation": len(state_records),
        "t0Counts": {state: initial_counts[state] for state in state_labels},
        "t0RatesPct": {state: 100 * initial_counts[state] / 2155 for state in state_labels},
        "normalInputDenominator": initial_valid,
        "normalInputClassified": sum(initial_counts[state] for state in PATTERNS),
        "normalInputClassificationCoveragePct": (
            100 * sum(initial_counts[state] for state in PATTERNS) / initial_valid
            if initial_valid else None
        ),
        "allPopulationClassificationCoveragePct": 100 * initial_valid / 2155,
        "t0DataQuality": dict(t0_quality),
        "t0Confidence": dict(t0_confidence),
        "allCheckpointDataQuality": dict(all_quality),
        "allCheckpointConfidence": dict(all_confidence),
        "invalidReasonCounts": dict(invalid_reason_counts),
        "transitionMatrix": {
            left: {right: transitions[(left, right)] for right in state_labels}
            for left in state_labels
        },
        "changedTransitionsTop": [
            {"from": left, "to": right, "count": count}
            for (left, right), count in sorted(
                ((key, value) for key, value in transitions.items() if key[0] != key[1]),
                key=lambda item: (-item[1], item[0]),
            )[:30]
        ],
        "transitionsToBuyStates": {
            f"{left}|{right}": value
            for (left, right), value in sorted(transitions_to_buy.items())
        },
        "stateTriggerDelay": metrics.distribution(
            intent["firstStateBuyDelay"] for intent in intents.values()
            if intent["initialState"] not in BUY_STATES
        ),
    }

    final_reasons = collections.Counter(row["entryReason"] for row in candidate)
    intent_reasons = collections.Counter(
        row["intentReason"] or "NO_TRIGGER" for row in candidate
    )
    signal_families = collections.Counter()
    for row in candidate:
        if row["intentReason"] == "SIGNAL_TRIGGER":
            signal_families.update(row["intentSignals"])
    signal_leads = []
    signal_before_state = 0
    signal_without_state = 0
    state_before_signal = 0
    state_without_any_signal = 0
    for intent in intents.values():
        sd, td = intent["firstSignalDelay"], intent["firstStateBuyDelay"]
        if intent["intentReason"] == "SIGNAL_TRIGGER":
            if td is None:
                signal_without_state += 1
            elif sd is not None and sd < td:
                signal_before_state += 1
                signal_leads.append(td - sd)
        if intent["intentReason"] == "STATE_TRANSITION_BUY":
            if sd is None:
                state_without_any_signal += 1
            elif td is not None and td < sd:
                state_before_signal += 1
    trigger_summary = {
        "finalEntryReason": dict(final_reasons),
        "causalIntentReason": dict(intent_reasons),
        "initialBuyState": dict(collections.Counter(
            row["initialState"] for row in candidate
            if row["intentReason"] == "INITIAL_STATE_BUY"
        )),
        "transitionBuyDestination": dict(collections.Counter(
            row["firstTransitionBuyState"] for row in candidate
            if row["intentReason"] == "STATE_TRANSITION_BUY"
        )),
        "signalTriggerFamiliesNonExclusive": dict(signal_families),
        "signalEarlierThanStateCount": signal_before_state,
        "signalEarlierThanStateFilledCount": sum(
            row["intentReason"] == "SIGNAL_TRIGGER" and bool(row["entryId"])
            and row["firstStateBuyDelay"] is not None
            and row["firstSignalDelay"] < row["firstStateBuyDelay"]
            for row in candidate
        ),
        "signalWithoutAnyBuyStateCheckpointCount": signal_without_state,
        "signalWithoutAnyBuyStateCheckpointFilledCount": sum(
            row["intentReason"] == "SIGNAL_TRIGGER" and bool(row["entryId"])
            and row["firstStateBuyDelay"] is None for row in candidate
        ),
        "signalLeadVsLaterStateActiveMinutes": metrics.distribution(signal_leads),
        "stateEarlierThanLaterSignalCount": state_before_signal,
        "stateTransitionWithNoSignalAnywhereCount": state_without_any_signal,
        "stateTransitionWouldOtherwiseNoEntryCount": state_without_any_signal,
        "stateTransitionWithNoSignalAnywhereFilledCount": sum(
            row["intentReason"] == "STATE_TRANSITION_BUY" and bool(row["entryId"])
            and not row["allWindowSignalFamilies"] for row in candidate
        ),
        "noEntryByCausalIntent": dict(collections.Counter(
            row["intentReason"] for row in candidate if not row["entryId"]
        )),
        "noEntryByTerminalReason": dict(collections.Counter(
            row["unfilledReason"] for row in candidate if not row["entryId"]
        )),
        "sameTimestampSignalAndStateCount": sum(
            intent["intentReason"] == "SIGNAL_TRIGGER"
            and intent["firstSignalMinute"] is not None
            and intent["firstSignalMinute"] == intent["firstStateBuyMinute"]
            for intent in intents.values()
        ),
    }

    state_quality = {}
    for state in state_labels:
        ids = {
            oid for oid in sorted(intents)
            if (intents[oid]["initialState"] or INVALID_LABEL) == state
        }
        state_opps = [row for row in opportunities if row["opportunity"] in ids]
        cand = [row for row in candidate if row["opportunity"] in ids]
        base = [row for row in immediate if row["opportunity"] in ids]
        if not ids:
            state_quality[state] = {"population": 0}
            continue
        cs = metrics.policy_summary(state_opps, cand)
        bs = metrics.policy_summary(state_opps, base)
        ps, _ = metrics.paired_summary(base, cand, bs, cs)
        state_quality[state] = {"immediate": bs, "stateV3": cs, "pairedVsImmediate": ps}
    wait_ids = {
        oid for oid, intent in intents.items()
        if intent["initialState"] in WAIT_STATES or intent["initialState"] is None
    }
    buy_ids = set(intents) - wait_ids
    cohort_quality = {}
    for name, ids in (("INITIAL_BUY_STATES", buy_ids), ("INITIAL_WAIT_STATES", wait_ids)):
        opp = [row for row in opportunities if row["opportunity"] in ids]
        base = [row for row in immediate if row["opportunity"] in ids]
        cand = [row for row in candidate if row["opportunity"] in ids]
        bs, cs = metrics.policy_summary(opp, base), metrics.policy_summary(opp, cand)
        ps, _ = metrics.paired_summary(base, cand, bs, cs)
        cohort_quality[name] = {"immediate": bs, "stateV3": cs, "pairedVsImmediate": ps}

    # T0 at the 11:30 boundary is a causal intent at 690, while the frozen
    # Immediate fill harness records its first executable intent at 751.
    # Execution identity, not that bookkeeping timestamp, is the invariant.
    identity_fields = ("entryId", "entryMinute", "price", "delay", "unfilledReason")
    initial_buy_mismatches = []
    for base, cand in zip(immediate, candidate):
        if cand["initialState"] not in BUY_STATES:
            continue
        if any(base[field] != cand[field] for field in identity_fields):
            initial_buy_mismatches.append(cand["opportunity"])
    assert not initial_buy_mismatches

    classifier_source = inspect.getsource(classify_state_v3)
    decision_source = classifier_source + inspect.getsource(frozen_intent)
    prohibited_lookups = [
        token for token in (
            "orderedOracle", "selectorOutcome", "futureMFE", "futureMAE",
            "futureReturn", "outcome", "oracleLow", "oracleHigh",
            "future_resolution_v2", "pathClassEvaluatorOnly",
        ) if f'["{token}"]' in decision_source
    ]
    lookahead = {
        "status": "PASS" if (
            not prohibited_lookups
            and state_future_violations == 0
            and signal_closed_bar_pass == checkpoint_assertions
            and signal_pivot_violations == 0
        ) else "FAIL",
        "causalIntentSHA256BeforeEvaluatorOpen": causal_intents_sha,
        "evaluatorOpenedAfterAllIntents": True,
        "stateDecisionCount": len(state_records),
        "stateFutureBarViolations": state_future_violations,
        "signalDecisionCount": checkpoint_assertions,
        "signalClosedBarAssertionsPassed": signal_closed_bar_pass,
        "signalHigherLowPivotAssertions": signal_pivot_checks,
        "signalFuturePivotViolations": signal_pivot_violations,
        "decisionFunctionProhibitedLookups": prohibited_lookups,
        "oracleLowHighDecisionUse": 0,
        "mfeMaeDecisionUse": 0,
        "futureOutcomeDecisionUse": 0,
        "stateV2ReferenceDecisionUse": 0,
        "volumeDecisionUse": 0,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "safety": policy["safety"],
    }
    assert lookahead["status"] == "PASS"

    summary = {
        "artifactKind": "phase57_state_v3_9pattern_entry_v1_result",
        "version": "v1.0",
        "startHead": policy["startHead"],
        "population": 2155,
        "policyLockedBeforeMeasurement": True,
        "state": state_summary,
        "triggers": trigger_summary,
        "policies": summaries,
        "pairedStateV3Vs": paired,
        "stateQuality": state_quality,
        "cohortQuality": cohort_quality,
        "initialBuyImmediateIdentityAudit": {
            "count": len(buy_ids), "mismatchCount": 0,
            "comparedFields": list(identity_fields), "status": "PASS",
        },
        "baselineParity": {"status": "PASS", "checks": parity},
        "lookAheadAudit": lookahead,
        "inputHashes": input_hashes,
        "safety": policy["safety"],
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "studyStatus": "DEVELOPMENT_STATE_V3_ENTRY_V1_COMPLETE_NO_PROMOTION",
    }

    write_json(output / "summary.json", summary)
    write_gzip_json(output / "state-checkpoints.json.gz", state_records)
    write_gzip_json(output / "entry-records.json.gz", candidate)
    write_gzip_json(output / "trades.json.gz", raw_trades)
    for name, rows in paired_rows.items():
        slug = {
            "A_IMMEDIATE": "immediate",
            "B_SIGNAL_ONLY": "signal-only",
            "C_ENTRY_V1": "entry-v1",
        }[name]
        write_gzip_json(output / f"paired-state-v3-vs-{slug}.json.gz", rows)
    write_json(output / "state-summary.json", state_summary)
    write_json(output / "trigger-attribution.json", trigger_summary)
    write_json(output / "baseline-comparison.json", {
        "policies": summaries, "pairedStateV3Vs": paired,
        "cohortQuality": cohort_quality, "stateQuality": state_quality,
    })
    write_json(output / "causality-audit.json", lookahead)
    write_json(output / "baseline-parity.json", summary["baselineParity"])
    manifest = {
        path.name: sha256(path) for path in sorted(output.iterdir())
        if path.name != "manifest.json"
    }
    write_json(output / "manifest.json", manifest)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement", required=True)
    parser.add_argument("--entry-v1-measurement", required=True)
    parser.add_argument("--raw-paths", required=True)
    parser.add_argument("--rows", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--contract-markdown", required=True)
    parser.add_argument("--signal-detector", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({
        "status": "PASS",
        "population": result["population"],
        "t0State": result["state"]["t0Counts"],
        "fills": result["policies"]["D_STATE_V3"]["fills"],
        "causality": result["lookAheadAudit"]["status"],
        "baselineParity": result["baselineParity"]["status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
