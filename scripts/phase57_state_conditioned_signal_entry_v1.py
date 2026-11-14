"""Phase57 State-Conditioned Signal Entry v1.

The decision half of this program accepts only the saved causal minute-census
row plus the precommitted policy.  State-v2 NOW reference and every future /
oracle field are opened only by the diagnostic and evaluator halves after the
Entry arm has been selected.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import hashlib
import inspect
import json
import math
import random
from pathlib import Path


FAMILIES = (
    "CONTINUATION",
    "BREAKOUT",
    "COMPRESSION_EXPANSION",
    "HIGHER_LOW",
    "LOWER_WICK",
    "RECLAIM",
)
STATES = ("UP", "DOWN", "NEUTRAL", "UNKNOWN")
LEVELS = (1, 2, 3, 5)
SAFETY_KEYS = (
    "executionAllowed",
    "brokerWriteAllowed",
    "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed",
    "liveTradingAllowed",
    "paperTradingAllowed",
    "automaticPromotionAllowed",
    "productionUpdateAllowed",
    "transmitted",
)
FORBIDDEN_DECISION_TOKENS = (
    "future_resolution_v2",
    "orderedOracle",
    "pathClassEvaluatorOnly",
    "inheritedPathOrderEvaluatorOnly",
    "selectorOutcome",
    "futureMFE",
    "futureMAE",
    "futureReturn",
    "outcome",
    "oracleLow",
    "oracleHigh",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, value) -> None:
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_gzip_json(path: Path, value) -> None:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as fh:
            fh.write(data)


def percentile(values, p):
    xs = sorted(values)
    if not xs:
        return None
    position = (len(xs) - 1) * p
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return float(xs[lo])
    weight = position - lo
    return float(xs[lo] * (1 - weight) + xs[hi] * weight)


def distribution(values):
    xs = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not xs:
        return {"count": 0, "mean": None, "median": None, "p5": None,
                "p25": None, "p75": None, "p90": None, "p95": None,
                "positiveRate": None, "minimum": None, "maximum": None}
    return {
        "count": len(xs),
        "mean": sum(xs) / len(xs),
        "median": percentile(xs, .5),
        "p5": percentile(xs, .05),
        "p25": percentile(xs, .25),
        "p75": percentile(xs, .75),
        "p90": percentile(xs, .90),
        "p95": percentile(xs, .95),
        "positiveRate": 100 * sum(x > 0 for x in xs) / len(xs),
        "minimum": min(xs),
        "maximum": max(xs),
    }


def pct(new, old):
    if new is None or old is None or old <= 0:
        return None
    return 100 * (new / old - 1)


def estimate_state(causal_row):
    """Decision function: one causal row in, one coarse state out.

    Deliberately no Opportunity outcome, oracle, State-v2 reference, model, or
    learned threshold enters this capability.
    """
    if set(causal_row) & set(FORBIDDEN_DECISION_TOKENS):
        raise ValueError("FORBIDDEN_DECISION_PAYLOAD")
    minute = causal_row["minute"]
    through = causal_row.get("computedThroughBarStart")
    if through is not None and through >= minute:
        raise ValueError("FUTURE_OR_UNCLOSED_BAR")
    value = causal_row["context"]["returnPct"]["5"]
    if value is None:
        return "UNKNOWN"
    if value > 0:
        return "UP"
    if value < 0:
        return "DOWN"
    return "NEUTRAL"


def select_policy_arm(causal_row, policy):
    """Select a frozen causal arm; evaluators are intentionally absent."""
    state = estimate_state(causal_row)
    rule = policy["entryPolicy"][state]
    return {
        "state": state,
        "sourceArm": rule["sourceArm"],
        "action": rule["action"],
        "signalFamilies": list(rule["signalFamilies"]),
        "fallbackActiveMinutes": rule["fallbackActiveMinutes"],
    }


def reference_coarse(record):
    axis = record["direction"]
    if axis["status"] != "DEFINED":
        return "UNKNOWN"
    return {"UP": "UP", "DOWN": "DOWN", "UNCHANGED": "NEUTRAL"}[axis["value"]]


def jst_minute(iso_value):
    value = dt.datetime.fromisoformat(iso_value)
    return value.hour * 60 + value.minute


def intent_signals(trade):
    for attempt in trade["attempts"]:
        if attempt["state"] == "BUY_ATTEMPT":
            return list(attempt.get("firing", [])) if trade["intentReason"] == "SIGNAL" else []
    return []


def oracle_metrics(opportunity, trade):
    oracle = opportunity["orderedOracle"]
    filled = trade["entryId"] is not None
    result = {
        "selectorPrice": opportunity["selectorPrice"],
        "entryPrice": trade["price"],
        "selectorToEntryPrice": None,
        "selectorToEntryPct": None,
        "priceImprovementVsSelectorPct": None,
        "oracleLowPrice": None,
        "oracleHighPrice": None,
        "lowToEntryPrice": None,
        "entryToLaterHighPrice": None,
        "lowToEntryDistancePct": None,
        "entryToLaterHighRemainingUpsidePct": None,
        "entryPosition": None,
        "rangeRetentionPct": trade["rangeRetention"].get("valuePct"),
        "rangeRetentionStatus": trade["rangeRetention"].get("status"),
        "entryAfterOracleLow": None,
        "oracleEvaluable": False,
        "laterHighEvaluable": False,
    }
    if not filled:
        return result
    selector = opportunity["selectorPrice"]
    entry = trade["price"]
    result["selectorToEntryPrice"] = entry - selector
    result["selectorToEntryPct"] = pct(entry, selector)
    result["priceImprovementVsSelectorPct"] = 100 * (1 - entry / selector) if selector else None
    if not oracle.get("fullSessionEvaluable") or oracle.get("status") != "OBSERVED_ORDERED_ORACLE":
        return result
    low, high = oracle.get("low"), oracle.get("high")
    if low is None or high is None or high <= low:
        return result
    result["oracleEvaluable"] = True
    result["oracleLowPrice"] = low
    result["oracleHighPrice"] = high
    result["lowToEntryPrice"] = entry - low
    result["lowToEntryDistancePct"] = pct(entry, low)
    result["entryPosition"] = (entry - low) / (high - low)
    result["entryAfterOracleLow"] = trade["entryMinute"] >= oracle["lowMinute"]
    if trade["entryMinute"] < oracle["highMinute"]:
        result["laterHighEvaluable"] = True
        result["entryToLaterHighPrice"] = high - entry
        result["entryToLaterHighRemainingUpsidePct"] = pct(high, entry)
    return result


def label_metrics(trade, outcomes):
    empty = {"30": None, "60": None, "mfeEnd": None, "maeEnd": None,
             "returnEnd": None, "status": "NO_ENTRY"}
    if not trade["entryId"]:
        return empty
    saved = outcomes.get(trade["entryId"])
    if not saved or not saved.get("labels"):
        return {**empty, "status": "OUTCOME_UNAVAILABLE"}
    labels = saved["labels"]
    return {
        "30": labels["30"],
        "60": labels["60"],
        "mfeEnd": labels.get("mfeEnd"),
        "maeEnd": labels.get("maeEnd"),
        "returnEnd": labels.get("returnEnd"),
        "status": "AVAILABLE",
    }


def capture(opportunities, records):
    out = {}
    for level in LEVELS:
        winners = {
            row["opportunity"] for row in opportunities
            if row["selectorOutcome"]["mfeEnd"] is not None
            and row["selectorOutcome"]["mfeEnd"] >= level
        }
        counts = collections.Counter()
        for row in records:
            if row["opportunity"] not in winners:
                continue
            if not row["entryId"]:
                counts["noEntry"] += 1
            elif row["labels"]["mfeEnd"] is None:
                counts["unknownEntered"] += 1
            elif row["labels"]["mfeEnd"] >= level:
                counts["captured"] += 1
            else:
                counts["belowThreshold"] += 1
        denominator = len(winners)
        assert sum(counts.values()) == denominator
        out[str(level)] = {
            "selectorWinnerDenominator": denominator,
            "captured": counts["captured"],
            "missed": denominator - counts["captured"],
            "ratePct": 100 * counts["captured"] / denominator if denominator else None,
            "noEntry": counts["noEntry"],
            "unknownEntered": counts["unknownEntered"],
            "belowThreshold": counts["belowThreshold"],
        }
    return out


def policy_summary(opportunities, records):
    fills = [row for row in records if row["entryId"]]
    result = {
        "population": len(records),
        "fills": len(fills),
        "noEntry": len(records) - len(fills),
        "fillRatePct": 100 * len(fills) / len(records) if records else None,
        "intentReason": dict(collections.Counter(row["intentReason"] for row in records)),
        "unfilledReason": dict(collections.Counter(row["unfilledReason"] for row in records if not row["entryId"])),
        "delay": distribution(row["delay"] for row in fills),
        "selectorToEntryPrice": distribution(row["quality"]["selectorToEntryPrice"] for row in fills),
        "selectorToEntryPct": distribution(row["quality"]["selectorToEntryPct"] for row in fills),
        "priceImprovementVsSelectorPct": distribution(row["quality"]["priceImprovementVsSelectorPct"] for row in fills),
        "lowToEntryPrice": distribution(row["quality"]["lowToEntryPrice"] for row in fills),
        "lowToEntryDistancePct": distribution(row["quality"]["lowToEntryDistancePct"] for row in fills),
        "entryToLaterHighPrice": distribution(row["quality"]["entryToLaterHighPrice"] for row in fills),
        "entryToLaterHighRemainingUpsidePct": distribution(row["quality"]["entryToLaterHighRemainingUpsidePct"] for row in fills),
        "entryPosition": distribution(row["quality"]["entryPosition"] for row in fills),
        "rangeRetentionPct": distribution(row["quality"]["rangeRetentionPct"] for row in fills),
        "waitMaxRiseVsImmediatePct": distribution(row["waitMaxRiseVsImmediatePct"] for row in records),
        "oracleEvaluable": sum(row["quality"]["oracleEvaluable"] for row in fills),
        "laterHighEvaluable": sum(row["quality"]["laterHighEvaluable"] for row in fills),
        "capture": capture(opportunities, records),
        "horizons": {},
    }
    for horizon in ("30", "60"):
        panels = [row["labels"][horizon] for row in fills if row["labels"][horizon] is not None]
        result["horizons"][horizon] = {
            "coverage": dict(collections.Counter(panel["status"] for panel in panels)),
            "MFE": distribution(panel.get("MFE") for panel in panels),
            "MAE": distribution(panel.get("MAE") for panel in panels),
            "returnNet": distribution(panel.get("returnNet") for panel in panels),
        }
    return result


def paired_summary(immediate, candidate, immediate_summary, candidate_summary):
    pairs = []
    session_prices = collections.defaultdict(list)
    statuses = collections.Counter()
    for base, cand in zip(immediate, candidate):
        assert base["opportunity"] == cand["opportunity"]
        if base["entryId"] and cand["entryId"]:
            status = "BOTH_FILLED"
        elif base["entryId"]:
            status = "BASE_ONLY"
        elif cand["entryId"]:
            status = "CANDIDATE_ONLY"
        else:
            status = "NEITHER_FILLED"
        statuses[status] += 1
        row = {"opportunity": base["opportunity"], "session": base["session"], "status": status}
        metrics = {
            "priceImprovementPct": None,
            "delayDelta": None,
            "lowToEntryDistanceDeltaPct": None,
            "remainingUpsideDeltaPct": None,
            "entryPositionDelta": None,
            "rangeRetentionDeltaPp": None,
            "MFE30DeltaPp": None,
            "MAE30DeltaPp": None,
            "MFE60DeltaPp": None,
            "MAE60DeltaPp": None,
        }
        if status == "BOTH_FILLED":
            metrics["priceImprovementPct"] = 100 * (1 - cand["price"] / base["price"])
            metrics["delayDelta"] = cand["delay"] - base["delay"]
            for key, output in (
                ("lowToEntryDistancePct", "lowToEntryDistanceDeltaPct"),
                ("entryToLaterHighRemainingUpsidePct", "remainingUpsideDeltaPct"),
                ("entryPosition", "entryPositionDelta"),
                ("rangeRetentionPct", "rangeRetentionDeltaPp"),
            ):
                a, b = base["quality"].get(key), cand["quality"].get(key)
                metrics[output] = b - a if a is not None and b is not None else None
            for horizon in ("30", "60"):
                for metric in ("MFE", "MAE"):
                    a = base["labels"][horizon]
                    b = cand["labels"][horizon]
                    a = a.get(metric) if a else None
                    b = b.get(metric) if b else None
                    metrics[f"{metric}{horizon}DeltaPp"] = b - a if a is not None and b is not None else None
            session_prices[row["session"]].append(metrics["priceImprovementPct"])
        row.update(metrics)
        pairs.append(row)
    per_session = [sum(values) / len(values) for values in session_prices.values() if values]
    bootstrap = None
    if per_session:
        rng = random.Random(570922)
        means = []
        for _ in range(2000):
            draw = [per_session[rng.randrange(len(per_session))] for _ in per_session]
            means.append(sum(draw) / len(draw))
        bootstrap = {
            "sessionCount": len(per_session),
            "mean": sum(per_session) / len(per_session),
            "percentile95": [percentile(means, .025), percentile(means, .975)],
            "descriptiveNotConfirmatory": True,
        }
    out = {
        "population": len(pairs),
        "pairStatus": dict(statuses),
        "fillDelta": candidate_summary["fills"] - immediate_summary["fills"],
        "fillRateDeltaPp": candidate_summary["fillRatePct"] - immediate_summary["fillRatePct"],
        "sessionEqualPriceBootstrap": bootstrap,
    }
    for key in (
        "priceImprovementPct", "delayDelta", "lowToEntryDistanceDeltaPct",
        "remainingUpsideDeltaPct", "entryPositionDelta", "rangeRetentionDeltaPp",
        "MFE30DeltaPp", "MAE30DeltaPp", "MFE60DeltaPp", "MAE60DeltaPp",
    ):
        out[key] = distribution(row[key] for row in pairs)
    out["captureDeltaPp"] = {
        str(level): candidate_summary["capture"][str(level)]["ratePct"]
        - immediate_summary["capture"][str(level)]["ratePct"]
        for level in LEVELS
    }
    return out, pairs


def build_record(opportunity, trade, state, arm, action, state_at_intent, signals, outcomes):
    quality = oracle_metrics(opportunity, trade)
    labels = label_metrics(trade, outcomes)
    return {
        "opportunity": opportunity["opportunity"],
        "session": opportunity["session"],
        "symbol": opportunity["symbol"],
        "initialState": state,
        "sourceArm": arm,
        "policyAction": action,
        "stateAtIntent": state_at_intent,
        "intentSignals": signals,
        "intentReason": trade["intentReason"],
        "intentMinute": trade["intentMinute"],
        "entryId": trade["entryId"],
        "entryMinute": trade["entryMinute"],
        "price": trade["price"],
        "delay": trade["delay"],
        "unfilledReason": trade["unfilledReason"],
        "fallbackTargetDelay": trade["fallbackTargetDelay"],
        "waitMaxRiseVsImmediatePct": trade.get("waitMaxRiseVsImmediatePct"),
        "quality": quality,
        "labels": labels,
    }


def source_static_audit(policy, detector_path, measurement, state_manifest):
    decision_source = inspect.getsource(estimate_state) + inspect.getsource(select_policy_arm)
    forbidden_hits = [token for token in FORBIDDEN_DECISION_TOKENS if token in decision_source]
    # Tokens exist only in the explicit rejecting guard; verify no evaluator key lookup appears.
    forbidden_lookups = [token for token in FORBIDDEN_DECISION_TOKENS if f'["{token}"]' in decision_source]
    pins = policy["inputPins"]
    return {
        "decisionFunctionForbiddenLookups": forbidden_lookups,
        "decisionFunctionRejectGuardTokens": forbidden_hits,
        "signalDetectorSHA256": sha256(detector_path),
        "signalDetectorPinMatch": sha256(detector_path) == pins["entryTimingSignalDetectorSHA256"],
        "measurementManifestSHA256": sha256(measurement / "manifest.json"),
        "measurementManifestPinMatch": sha256(measurement / "manifest.json") == pins["entryTimingMeasurementManifestSHA256"],
        "stateV2GenerationManifestSHA256": sha256(state_manifest),
        "stateV2GenerationManifestPinMatch": sha256(state_manifest) == pins["stateV2GenerationManifestSHA256"],
    }


def run(args):
    measurement = Path(args.measurement)
    state_root = Path(args.state_reference)
    outcomes_path = Path(args.outcomes)
    policy_path = Path(args.policy)
    detector_path = Path(args.signal_detector)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)

    policy = read_json(policy_path)
    assert policy["population"] == 2155
    assert policy["policyLockedBeforeV1OutcomeEvaluation"] is True
    assert tuple(policy["safety"].keys()) == SAFETY_KEYS
    assert all(value is False for value in policy["safety"].values())
    assert policy["providerRequestsAuthorized"] == policy["protectedDataOpened"] == 0

    existing_manifest = read_json(measurement / "manifest.json")
    for name in ("opportunity-records.json.gz", "trades.json.gz", "paired.json.gz",
                 "metrics.json", "oracle-anatomy.json"):
        assert sha256(measurement / name) == existing_manifest[name], ("INPUT_HASH", name)
    for path in sorted((measurement / "minute-census").glob("*.json.gz")):
        assert sha256(path) == existing_manifest[f"minute-census/{path.name}"], path.name

    state_by_key = {}
    decision_row = {}
    current_state_counts = collections.Counter()
    signal_checkpoint = collections.Counter()
    signal_opportunities = collections.defaultdict(set)
    state_opportunities = collections.defaultdict(set)
    cooccurrence = collections.Counter()
    checkpoint_count = 0
    closed_bar_pass = 0
    higher_low_pivot_checks = 0
    higher_low_pivot_violations = 0
    missing_signal_values = 0
    for path in sorted((measurement / "minute-census").glob("*.json.gz")):
        for row in read_json(path):
            checkpoint_count += 1
            state = estimate_state(row)
            key = (row["opportunity"], row["minute"])
            assert key not in state_by_key
            state_by_key[key] = state
            current_state_counts[state] += 1
            state_opportunities[state].add(row["opportunity"])
            through = row.get("computedThroughBarStart")
            closed_bar_pass += through is None or through < row["minute"]
            if row["delay"] == 0:
                assert row["opportunity"] not in decision_row
                decision_row[row["opportunity"]] = row
            firing = [family for family in FAMILIES if row["signals"][family]["trigger"] is True]
            missing_signal_values += sum(
                row["signals"][family]["trigger"] is None for family in FAMILIES
            )
            pivot = row["signals"]["HIGHER_LOW"].get("pivot")
            if pivot is not None:
                higher_low_pivot_checks += 1
                if not (pivot["lowBarStart"] < pivot["confirmedAt"] <= row["minute"]):
                    higher_low_pivot_violations += 1
            for family in firing:
                signal_checkpoint[(state, family)] += 1
                signal_opportunities[(state, family)].add(row["opportunity"])
            for left in firing:
                for right in firing:
                    cooccurrence[(left, right)] += 1
    # The signal census is a one-minute grid (377,450 rows).  State-v2's
    # accepted reference is the sparser, frozen 77,214-checkpoint grid; the
    # overlap is asserted separately below instead of conflating the two.
    assert checkpoint_count == 377450
    assert closed_bar_pass == checkpoint_count
    assert len(decision_row) == 2155

    decision_ids = sorted(decision_row)
    decisions = {oid: select_policy_arm(decision_row[oid], policy) for oid in decision_ids}
    decision_state_counts = collections.Counter(value["state"] for value in decisions.values())

    confusion = collections.Counter()
    reference_counts = collections.Counter()
    joined = 0
    future_source_violations = 0
    reference_safety_violations = 0
    decision_reference = {}
    for path in sorted(state_root.glob("*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                key = (row["opportunityId"], jst_minute(row["checkpointAsOf"]))
                if key not in state_by_key:
                    continue
                joined += 1
                estimated = state_by_key[key]
                reference = reference_coarse(row)
                confusion[(reference, estimated)] += 1
                reference_counts[reference] += 1
                maximum = row["causalMetadata"].get("maxSourceTimestamp")
                if maximum and dt.datetime.fromisoformat(maximum) > dt.datetime.fromisoformat(row["checkpointAsOf"]):
                    future_source_violations += 1
                if set(row["safety"]) != set(SAFETY_KEYS) or any(row["safety"].values()):
                    reference_safety_violations += 1
                if row["elapsedActiveMinutesFromSelector"] == 0:
                    decision_reference[row["opportunityId"]] = reference
    assert joined == 77214
    assert len(decision_reference) == 2155

    # Evaluator-only files carry Oracle/Outcome information.  They are parsed
    # only after every causal state and policy arm is immutable above.
    opportunities = read_json(measurement / "opportunity-records.json.gz")
    trades = read_json(measurement / "trades.json.gz")
    outcomes = read_json(outcomes_path)
    old_metrics = read_json(measurement / "metrics.json")
    assert len(opportunities) == 2155
    ids = [row["opportunity"] for row in opportunities]
    assert len(set(ids)) == 2155
    assert set(ids) == set(decision_ids)
    trade_by_arm = {arm: {row["opportunity"]: row for row in rows} for arm, rows in trades.items()}
    assert all(set(index) == set(ids) for index in trade_by_arm.values())

    signal_matrix = {
        state: {
            family: {
                "checkpointTriggerCount": signal_checkpoint[(state, family)],
                "checkpointDenominator": current_state_counts[state],
                "checkpointTriggerRatePct": (
                    100 * signal_checkpoint[(state, family)] / current_state_counts[state]
                    if current_state_counts[state] else None
                ),
                "opportunityCount": len(signal_opportunities[(state, family)]),
                "statePresentOpportunityDenominator": len(state_opportunities[state]),
                "opportunityRatePct": (
                    100 * len(signal_opportunities[(state, family)]) / len(state_opportunities[state])
                    if state_opportunities[state] else None
                ),
            }
            for family in FAMILIES
        }
        for state in STATES
    }

    policy_rows = {"A_IMMEDIATE": [], "B_SIGNAL_ONLY": [], "C_ENTRY_V1": []}
    selected_arm_counts = collections.Counter()
    transition_at_intent = collections.Counter()
    for opportunity in opportunities:
        oid = opportunity["opportunity"]
        decision = decisions[oid]
        initial = decision["state"]
        selected_arm = decision["sourceArm"]
        selected_arm_counts[selected_arm] += 1
        variants = {
            "A_IMMEDIATE": ("A", "BUY_NOW", trade_by_arm["A"][oid]),
            "B_SIGNAL_ONLY": ("E", "WAIT_ANY_EXISTING_SIGNAL", trade_by_arm["E"][oid]),
            "C_ENTRY_V1": (selected_arm, decision["action"], trade_by_arm[selected_arm][oid]),
        }
        for name, (arm, action, trade) in variants.items():
            signals = intent_signals(trade)
            at_intent = state_by_key.get((oid, trade["intentMinute"])) if trade["intentMinute"] is not None else None
            if name == "C_ENTRY_V1":
                transition_at_intent[(initial, at_intent or "NO_INTENT", trade["intentReason"] or "NO_INTENT")] += 1
            policy_rows[name].append(build_record(opportunity, trade, initial, arm, action,
                                                  at_intent, signals, outcomes))

    identity_fields = (
        "entryId", "entryMinute", "price", "delay", "intentMinute",
        "intentReason", "unfilledReason",
    )
    up_identity_mismatches = []
    for immediate, candidate in zip(policy_rows["A_IMMEDIATE"], policy_rows["C_ENTRY_V1"]):
        if candidate["initialState"] != "UP":
            continue
        if any(immediate[field] != candidate[field] for field in identity_fields):
            up_identity_mismatches.append(candidate["opportunity"])
    up_identity_audit = {
        "upDecisionCount": decision_state_counts["UP"],
        "comparedFields": list(identity_fields),
        "mismatchCount": len(up_identity_mismatches),
        "status": "PASS" if not up_identity_mismatches else "FAIL",
    }
    assert up_identity_audit["status"] == "PASS"

    summaries = {name: policy_summary(opportunities, rows) for name, rows in policy_rows.items()}
    paired_b, pairs_b = paired_summary(policy_rows["A_IMMEDIATE"], policy_rows["B_SIGNAL_ONLY"],
                                       summaries["A_IMMEDIATE"], summaries["B_SIGNAL_ONLY"])
    paired_c, pairs_c = paired_summary(policy_rows["A_IMMEDIATE"], policy_rows["C_ENTRY_V1"],
                                       summaries["A_IMMEDIATE"], summaries["C_ENTRY_V1"])
    paired_c_vs_b, pairs_c_vs_b = paired_summary(
        policy_rows["B_SIGNAL_ONLY"], policy_rows["C_ENTRY_V1"],
        summaries["B_SIGNAL_ONLY"], summaries["C_ENTRY_V1"],
    )

    state_quality = {}
    state_comparisons = {}
    for state in STATES:
        subset = [row for row in policy_rows["C_ENTRY_V1"] if row["initialState"] == state]
        immediate_subset = [row for row in policy_rows["A_IMMEDIATE"] if row["initialState"] == state]
        signal_subset = [row for row in policy_rows["B_SIGNAL_ONLY"] if row["initialState"] == state]
        state_opps = [row for row in opportunities if decisions[row["opportunity"]]["state"] == state]
        state_quality[state] = policy_summary(state_opps, subset)
        immediate_state_summary = policy_summary(state_opps, immediate_subset)
        signal_state_summary = policy_summary(state_opps, signal_subset)
        paired_state, _ = paired_summary(immediate_subset, subset,
                                         immediate_state_summary, state_quality[state])
        paired_signal_state, _ = paired_summary(
            immediate_subset, signal_subset,
            immediate_state_summary, signal_state_summary,
        )
        state_comparisons[state] = {
            "immediate": immediate_state_summary,
            "signalOnly": signal_state_summary,
            "entryV1": state_quality[state],
            "pairedVsImmediate": paired_state,
            "signalOnlyPairedVsImmediate": paired_signal_state,
        }

    signal_quality = {}
    for label in ("IMMEDIATE", "FALLBACK", "NO_ENTRY") + FAMILIES:
        if label == "IMMEDIATE":
            subset = [row for row in policy_rows["C_ENTRY_V1"] if row["intentReason"] == "IMMEDIATE"]
        elif label == "FALLBACK":
            subset = [row for row in policy_rows["C_ENTRY_V1"] if row["intentReason"] == "FALLBACK"]
        elif label == "NO_ENTRY":
            subset = [row for row in policy_rows["C_ENTRY_V1"] if not row["entryId"]]
        else:
            subset = [row for row in policy_rows["C_ENTRY_V1"] if label in row["intentSignals"]]
        subset_ids = {row["opportunity"] for row in subset}
        subset_opps = [row for row in opportunities if row["opportunity"] in subset_ids]
        signal_quality[label] = policy_summary(subset_opps, subset) if subset else {"population": 0}

    state_signal_quality = {}
    for state in STATES:
        state_signal_quality[state] = {}
        for family in FAMILIES:
            subset = [row for row in policy_rows["C_ENTRY_V1"]
                      if row["initialState"] == state and family in row["intentSignals"]]
            subset_ids = {row["opportunity"] for row in subset}
            subset_opps = [row for row in opportunities if row["opportunity"] in subset_ids]
            state_signal_quality[state][family] = (
                policy_summary(subset_opps, subset) if subset else {"population": 0}
            )

    def close(a, b, tol=1e-10):
        return a == b if a is None or b is None else math.isclose(a, b, rel_tol=1e-12, abs_tol=tol)

    parity_checks = []
    for name, arm in (("A_IMMEDIATE", "A"), ("B_SIGNAL_ONLY", "E")):
        new = summaries[name]
        old = old_metrics[arm]
        parity_checks.extend([
            {"check": f"{name}/population", "pass": new["population"] == old["opportunities"]},
            {"check": f"{name}/fills", "pass": new["fills"] == old["fills"]},
            {"check": f"{name}/delayMean", "pass": close(new["delay"]["mean"], old["delay"]["mean"])},
            {"check": f"{name}/rangeRetentionMean", "pass": close(new["rangeRetentionPct"]["mean"], old["rangeRetention"]["mean"])},
        ])
        for level in LEVELS:
            parity_checks.append({
                "check": f"{name}/capture{level}",
                "pass": close(new["capture"][str(level)]["ratePct"], old["capture"][str(level)]["rate"]),
            })
        for horizon in ("30", "60"):
            for metric in ("MFE", "MAE"):
                parity_checks.append({
                    "check": f"{name}/{horizon}/{metric}/mean",
                    "pass": close(new["horizons"][horizon][metric]["mean"], old["30" if horizon == "30" else "60"][metric]["mean"]),
                })

    reference_defined_pairs = sum(value for (ref, est), value in confusion.items()
                                  if ref != "UNKNOWN" and est != "UNKNOWN")
    reference_defined_agree = sum(confusion[(state, state)] for state in ("UP", "DOWN", "NEUTRAL"))
    all_agree = sum(confusion[(state, state)] for state in STATES)
    decision_confusion = collections.Counter(
        (decision_reference[oid], decisions[oid]["state"]) for oid in ids
    )
    decision_defined_n = sum(value for (ref, est), value in decision_confusion.items()
                             if ref != "UNKNOWN" and est != "UNKNOWN")
    decision_defined_agree = sum(decision_confusion[(state, state)]
                                 for state in ("UP", "DOWN", "NEUTRAL"))
    decision_all_agree = sum(decision_confusion[(state, state)] for state in STATES)
    diagnostics = {
        "signalCensusCheckpointPopulation": checkpoint_count,
        "stateV2ReferenceJoinedCheckpoints": joined,
        "decisionPopulation": len(decisions),
        "estimatorCheckpointCounts": dict(current_state_counts),
        "estimatorDecisionCounts": dict(decision_state_counts),
        "referenceCheckpointCounts": dict(reference_counts),
        "referenceDecisionCounts": dict(collections.Counter(decision_reference.values())),
        "confusion": {
            ref: {est: confusion[(ref, est)] for est in STATES}
            for ref in STATES
        },
        "decisionConfusion": {
            ref: {est: decision_confusion[(ref, est)] for est in STATES}
            for ref in STATES
        },
        "overallAgreementPct": 100 * all_agree / joined,
        "bothDefinedAgreementPct": 100 * reference_defined_agree / reference_defined_pairs,
        "bothDefinedN": reference_defined_pairs,
        "decisionOverallAgreementPct": 100 * decision_all_agree / 2155,
        "decisionBothDefinedAgreementPct": (
            100 * decision_defined_agree / decision_defined_n if decision_defined_n else None
        ),
        "decisionBothDefinedN": decision_defined_n,
        "decisionDelayActiveMinutes": {"count": 2155, "minimum": 0, "maximum": 0},
        "referenceUse": "DIAGNOSTIC_ONLY_NOT_DECISION_INPUT",
    }

    static_audit = source_static_audit(policy, detector_path, measurement,
                                       Path(args.state_manifest))
    lookahead = {
        "status": "PASS" if (
            not static_audit["decisionFunctionForbiddenLookups"]
            and static_audit["signalDetectorPinMatch"]
            and static_audit["measurementManifestPinMatch"]
            and static_audit["stateV2GenerationManifestPinMatch"]
            and closed_bar_pass == checkpoint_count
            and higher_low_pivot_violations == 0
            and future_source_violations == 0
            and reference_safety_violations == 0
        ) else "FAIL",
        "checkpointAssertions": checkpoint_count,
        "closedBarAssertionsPassed": closed_bar_pass,
        "higherLowPivotTimestampAssertions": higher_low_pivot_checks,
        "higherLowPivotBackdatingViolations": higher_low_pivot_violations,
        "missingSignalValuesPreserved": missing_signal_values,
        "evaluatorInputsParsedAfterAllDecisions": True,
        "futureSourceViolations": future_source_violations,
        "referenceSafetyViolations": reference_safety_violations,
        "oracleUsedByDecision": False,
        "futureOutcomeUsedByDecision": False,
        "stateV2ReferenceUsedByDecision": False,
        "pivotBackdating": False,
        "outcomeFiltering": False,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "staticAudit": static_audit,
        "safety": policy["safety"],
    }
    assert lookahead["status"] == "PASS"
    assert all(item["pass"] for item in parity_checks)

    summary = {
        "artifactKind": "phase57_state_conditioned_signal_entry_v1_result",
        "version": "v1.0",
        "startHead": policy["startHead"],
        "population": 2155,
        "checkpoints": checkpoint_count,
        "selectedArmCounts": dict(selected_arm_counts),
        "policies": summaries,
        "pairedVsImmediate": {"B_SIGNAL_ONLY": paired_b, "C_ENTRY_V1": paired_c},
        "pairedEntryV1VsSignalOnly": paired_c_vs_b,
        "stateQuality": state_quality,
        "stateComparisonsVsImmediate": state_comparisons,
        "upBuyNowIdentityAudit": up_identity_audit,
        "signalQuality": signal_quality,
        "stateSignalQuality": state_signal_quality,
        "transitionAtIntent": {
            "|".join(key): value for key, value in sorted(transition_at_intent.items())
        },
        "stateDiagnostics": diagnostics,
        "signalMatrix": signal_matrix,
        "cooccurrenceCheckpointCounts": {
            f"{left}|{right}": cooccurrence[(left, right)]
            for left in FAMILIES for right in FAMILIES
        },
        "lookAheadAudit": lookahead,
        "baselineParity": {"status": "PASS", "checks": parity_checks},
        "safety": policy["safety"],
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "studyStatus": "DEVELOPMENT_ENTRY_V1_COMPLETE_NO_PROMOTION",
    }

    write_json(output / "summary.json", summary)
    write_gzip_json(output / "entry-records.json.gz", policy_rows["C_ENTRY_V1"])
    write_gzip_json(output / "baseline-immediate-records.json.gz", policy_rows["A_IMMEDIATE"])
    write_gzip_json(output / "baseline-signal-records.json.gz", policy_rows["B_SIGNAL_ONLY"])
    write_gzip_json(output / "paired-entry-v1-vs-immediate.json.gz", pairs_c)
    write_gzip_json(output / "paired-signal-vs-immediate.json.gz", pairs_b)
    write_gzip_json(output / "paired-entry-v1-vs-signal.json.gz", pairs_c_vs_b)
    write_json(output / "state-diagnostics.json", diagnostics)
    write_json(output / "state-signal.json", {
        "signalMatrix": signal_matrix,
        "cooccurrenceCheckpointCounts": summary["cooccurrenceCheckpointCounts"],
        "transitionAtIntent": summary["transitionAtIntent"],
    })
    write_json(output / "lookahead-audit.json", lookahead)
    write_json(output / "baseline-parity.json", summary["baselineParity"])
    evaluator_inputs = {
        "entryPatternArtifactId": 10605887642,
        "entryPatternArtifactSHA256": "749caf82bbd9d39969f5712ef5a6f2705ac973a2f74483f03307c671586ae05a",
        "outcomesSHA256": sha256(outcomes_path),
        "stateV2ArtifactId": policy["inputPins"]["stateV2A12ArtifactId"],
        "stateV2ArtifactSHA256": policy["inputPins"]["stateV2A12ArtifactSHA256"],
        "stateV2GenerationManifestSHA256": sha256(Path(args.state_manifest)),
        "decisionUse": False,
        "evaluatorOnly": True,
    }
    write_json(output / "evaluator-inputs.json", evaluator_inputs)
    manifest = {path.name: sha256(path) for path in sorted(output.iterdir())
                if path.name != "manifest.json"}
    write_json(output / "manifest.json", manifest)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement", required=True)
    parser.add_argument("--state-reference", required=True)
    parser.add_argument("--state-manifest", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--signal-detector", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    summary = run(args)
    print(json.dumps({
        "status": "PASS",
        "population": summary["population"],
        "checkpoints": summary["checkpoints"],
        "entryV1Fills": summary["policies"]["C_ENTRY_V1"]["fills"],
        "lookAhead": summary["lookAheadAudit"]["status"],
        "baselineParity": summary["baselineParity"]["status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
