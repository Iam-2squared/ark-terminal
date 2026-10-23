"""Model-free economic-alpha census for the frozen Phase57 LONG Selector.

The module has two explicit stages:

* ``prepare`` selects the precommitted like-for-like arms from the already
  saved Development dataset.  It never fits a model and never filters on a
  future path.
* ``measure`` evaluates immutable projected five-minute paths.  It never sees
  the full candidate universe and cannot change membership.

DEV TEST, Fresh and OOS are not accepted by either command.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import shutil
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from scripts import run_phase57_long_only_corrected_measurement as corrected
from scripts import run_phase57_long_only_eligibility_measurement as eligibility


BASE = ROOT / "docs/evidence/phase57-selector-economic-alpha-v1"
PROTOCOL = BASE / "protocol.json"
SELECTOR_LEDGER = ROOT / "docs/evidence/phase57-selector-min-price75-v1/measurement/selector/selector-ledger.json.gz"
FROZEN_PATHS = ROOT / "docs/evidence/phase57-selector-min-price75-v1/measurement/new-paths.json.gz"
JST = dt.timezone(dt.timedelta(hours=9))
ARMS = ("FROZEN_SELECTOR", "RANDOM_TOP5", "MOMENTUM30_TOP5")
HORIZONS = (5, 10, 15, 30, 60)
DELAYS = (0, 5, 10, 15, 20, 25)
COSTS = (0.0, 0.05, 0.10, 0.20)


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()


def read(path):
    path = Path(path)
    raw = path.read_bytes()
    if path.suffix == ".gz":
        raw = gzip.decompress(raw)
    return json.loads(raw)


def write(path, value):
    path = Path(path)
    raw = encoded(value)
    if path.suffix == ".gz":
        raw = gzip.compress(raw, mtime=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_protocol():
    protocol = read(PROTOCOL)
    assert protocol["id"] == "PHASE57_FROZEN_SELECTOR_ECONOMIC_ALPHA_V1"
    assert protocol["status"] == "PRECOMMITTED_BEFORE_MEASUREMENT"
    assert protocol["scope"]["selectionRows"] == 3800
    assert protocol["scope"]["decisionTimestamps"] == 760
    assert protocol["scope"]["selectorCadenceMinutes"] == 30
    assert tuple(protocol["execution"]["entryDelayMinutes"]) == DELAYS
    assert tuple(protocol["execution"]["entryRelativeHorizonsMinutes"]) == HORIZONS
    assert protocol["cost"]["canonicalRoundTripPctPoints"] == 0.05
    assert protocol["statistics"]["bootstrapReplicates"] == 10000
    assert all(value is False for value in protocol["safety"].values())
    for key in ("developmentTestOpened", "freshOpened", "oosOpened", "selectorRetrain",
                "baselineParameterSearch", "exitTuning", "capitalTuning",
                "portfolioOptimization", "automaticPromotion", "mainMerge"):
        assert protocol["sealed"][key] is False
    for name, digest in protocol["sourcePins"].items():
        assert sha(ROOT / name) == digest, name
    return protocol


def event_id(session, time_jst, symbol):
    stamp = f"{session}T{time_jst}:00+09:00"
    return f"{session}|{stamp}|{symbol}"


def random_key(seed, session, time_jst, symbol):
    return hashlib.sha256(f"{seed}|{session}|{time_jst}|{symbol}".encode()).hexdigest(), str(symbol)


def frame_row(row, rank=None):
    session = str(row.sessionDate)
    time_jst = str(row.decisionTimeJst)
    symbol = str(row.symbol)
    result = {
        "selectorEventId": event_id(session, time_jst, symbol),
        "sessionDate": session,
        "symbol": symbol,
        "decisionTimeJst": time_jst,
        "decisionTimestamp": f"{session}T{time_jst}:00+09:00",
        "decisionPrice": float(row.decisionPrice),
        "referenceAgeMin": float(row.referenceAgeMin),
        "savedV1Score": float(row.savedV1Score),
        "momentum30Pct": float(row.momentum30Pct),
        "currentReturnPct": float(row.currentReturnPct),
    }
    if rank is not None:
        result["armRank"] = int(rank)
    return result


def prepare(dataset_dir, output):
    protocol = load_protocol()
    frame, manifest = corrected.load(Path(dataset_dir))
    eligible = eligibility.eligible_universe(frame)
    eligible = eligible[eligible.decisionPrice.gt(75)].copy()
    assert len(frame) == 2758341
    assert len(eligible) == 1736930
    assert eligible[corrected.KEYS].drop_duplicates().shape[0] == 760

    frozen = read(SELECTOR_LEDGER)["new"]
    frozen_ids = [row["selectorEventId"] for row in frozen]
    assert len(frozen_ids) == len(set(frozen_ids)) == 3800
    expected = collections.defaultdict(list)
    for row in frozen:
        expected[(row["sessionDate"], row["decisionTimeJst"])].append(row["selectorEventId"])
    for rows in expected.values():
        assert len(rows) == 5

    arms = {name: [] for name in ARMS}
    union = {}
    seed = int(protocol["baselines"]["random"]["seed"])
    for (session, time_jst), group in eligible.groupby(corrected.KEYS, sort=True):
        selector = group.sort_values(["savedV1Score", "symbol"], ascending=[False, True], kind="mergesort").head(5)
        momentum = group.sort_values(["momentum30Pct", "symbol"], ascending=[False, True], kind="mergesort").head(5)
        random_indices = sorted(
            group.index,
            key=lambda index: random_key(seed, str(session), str(time_jst), str(group.at[index, "symbol"])),
        )[:5]
        random = group.loc[random_indices]
        selected = {
            "FROZEN_SELECTOR": selector,
            "RANDOM_TOP5": random,
            "MOMENTUM30_TOP5": momentum,
        }
        got = [event_id(str(session), str(time_jst), str(symbol)) for symbol in selector.symbol]
        assert got == expected[(str(session), str(time_jst))]
        for arm, selected_frame in selected.items():
            for rank, (_, row) in enumerate(selected_frame.iterrows(), 1):
                item = frame_row(row, rank)
                arms[arm].append(item["selectorEventId"])
                previous = union.setdefault(item["selectorEventId"], item)
                assert previous["decisionPrice"] == item["decisionPrice"]

    assert all(len(rows) == len(set(rows)) == 3800 for rows in arms.values())
    assert arms["FROZEN_SELECTOR"] == frozen_ids
    frozen_map = {row["selectorEventId"]: row for row in frozen}
    for event in arms["FROZEN_SELECTOR"]:
        source = frozen_map[event]
        union[event].update({
            "selectorRank": int(source["newEligibleRank"]),
            "highOpportunity1": source["highOpportunity1"],
            "highOpportunity2": source["highOpportunity2"],
            "highOpportunity3": source["highOpportunity3"],
            "highOpportunity5": source["highOpportunity5"],
        })

    payload = {
        "schemaVersion": 1,
        "contractSHA256": sha(PROTOCOL),
        "inputManifestSHA256": manifest["_sha256"],
        "role": "PRECOMMITTED_MEMBERSHIP_ONLY_NO_FUTURE_AVAILABILITY_FILTER",
        "universe": {
            "preEligibilityRows": len(frame),
            "eligibleRows": len(eligible),
            "sessions": int(eligible.sessionDate.nunique()),
            "decisionTimestamps": int(eligible[corrected.KEYS].drop_duplicates().shape[0]),
        },
        "arms": arms,
        "new": sorted(union.values(), key=lambda row: row["selectorEventId"]),
        "fitCalls": 0,
        "providerRequests": 0,
        "developmentTestOpened": False,
        "freshOOSOpened": False,
        "safety": protocol["safety"],
    }
    write(output, payload)
    print(json.dumps({"status": "BASELINE_MEMBERSHIP_PREPARED", "union": len(union),
                      "arms": {key: len(value) for key, value in arms.items()}, "output": str(output)}))


def timestamp(value):
    value = value.replace("Z", "+00:00")
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=JST)
    return parsed.astimezone(JST)


def valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def materialize_path(path):
    bars = []
    decision_price = float(path["decisionPrice"])
    for source in path["future"]:
        bar = {
            "start": timestamp(source["start"]),
            "end": timestamp(source["end"]),
            "missing": bool(source["missing"]),
            "observedMinutes": source.get("observedMinutes"),
        }
        if not bar["missing"] and all(valid_number(source.get(key)) for key in ("o", "h", "l", "c")):
            for key in ("o", "h", "l", "c"):
                bar[key] = decision_price * (1 + float(source[key]) / 100)
            bar["valid"] = (bar["o"] > 0 and bar["h"] > 0 and bar["l"] > 0 and bar["c"] > 0
                            and bar["l"] <= min(bar["o"], bar["c"]) + 1e-7
                            and bar["h"] + 1e-7 >= max(bar["o"], bar["c"]))
        else:
            bar["valid"] = False
        bars.append(bar)
    bars.sort(key=lambda bar: bar["start"])
    assert len({bar["start"] for bar in bars}) == len(bars)
    return bars


def entry_at_or_after(bars, intended):
    candidates = [bar for bar in bars if bar["start"] >= intended]
    if not candidates:
        return {"status": "NO_REGULAR_BAR", "intended": intended.isoformat()}
    bar = candidates[0]
    if not bar["valid"]:
        return {"status": "FIRST_ELIGIBLE_BAR_MISSING", "intended": intended.isoformat(),
                "timestamp": bar["start"].isoformat()}
    return {"status": "AVAILABLE", "intended": intended.isoformat(), "timestamp": bar["start"].isoformat(),
            "actualLatencyMin": (bar["start"] - intended).total_seconds() / 60,
            "price": bar["o"], "bar": bar}


def exact_exit(bars, target):
    matches = [bar for bar in bars if bar["end"] == target]
    if not matches:
        return {"status": "NO_EXACT_COMPLETED_CLOSE", "timestamp": target.isoformat()}
    bar = matches[0]
    if not bar["valid"]:
        return {"status": "TARGET_BAR_MISSING", "timestamp": target.isoformat()}
    return {"status": "AVAILABLE", "timestamp": target.isoformat(), "price": bar["c"], "bar": bar}


def trade_return(entry, exit_row):
    if entry["status"] != "AVAILABLE" or exit_row["status"] != "AVAILABLE":
        return None
    return 100 * (exit_row["price"] / entry["price"] - 1)


def evaluate_event(path, metadata):
    bars = materialize_path(path)
    decision = timestamp(path["decisionTimestamp"])
    delays = {}
    for delay in DELAYS:
        entry = entry_at_or_after(bars, decision + dt.timedelta(minutes=delay))
        row = {
            "status": entry["status"],
            "intendedDelayMin": delay,
            "entryTimestamp": entry.get("timestamp"),
            "entryPrice": entry.get("price"),
            "actualLatencyFromIntentMin": entry.get("actualLatencyMin"),
            "actualLatencyFromDecisionMin": ((timestamp(entry["timestamp"]) - decision).total_seconds() / 60
                                             if entry.get("timestamp") else None),
            "entryRelative": {},
            "selectorTerminal": {},
        }
        for horizon in HORIZONS:
            if entry["status"] == "AVAILABLE":
                entry_time = timestamp(entry["timestamp"])
                relative_exit = exact_exit(bars, entry_time + dt.timedelta(minutes=horizon))
                relative = trade_return(entry, relative_exit)
                terminal_time = decision + dt.timedelta(minutes=horizon)
                if entry_time >= terminal_time:
                    terminal_exit = {"status": "NONPOSITIVE_HOLDING_WINDOW", "timestamp": terminal_time.isoformat()}
                    terminal = None
                else:
                    terminal_exit = exact_exit(bars, terminal_time)
                    terminal = trade_return(entry, terminal_exit)
            else:
                relative_exit = terminal_exit = {"status": "ENTRY_UNAVAILABLE"}
                relative = terminal = None
            row["entryRelative"][str(horizon)] = {
                "status": relative_exit["status"], "grossPct": relative,
                "exitTimestamp": relative_exit.get("timestamp"), "exitPrice": relative_exit.get("price")}
            row["selectorTerminal"][str(horizon)] = {
                "status": terminal_exit["status"], "grossPct": terminal,
                "exitTimestamp": terminal_exit.get("timestamp"), "exitPrice": terminal_exit.get("price")}
        delays[str(delay)] = row
    return {
        "selectorEventId": path["selectorEventId"],
        "sessionDate": path["sessionDate"],
        "symbol": path["symbol"],
        "decisionTimestamp": path["decisionTimestamp"],
        "decisionPrice": path["decisionPrice"],
        "metadata": metadata,
        "delays": delays,
    }


def quantile(values, q):
    if not values:
        return None
    return float(np.quantile(np.asarray(values, dtype=float), q))


def distribution(values, cost=0.0):
    clean = [float(value) - cost for value in values if value is not None and math.isfinite(value)]
    positives = sum(value for value in clean if value > 0)
    negatives = -sum(value for value in clean if value < 0)
    return {
        "n": len(clean),
        "mean": statistics.mean(clean) if clean else None,
        "median": statistics.median(clean) if clean else None,
        "positiveRate": sum(value > 0 for value in clean) / len(clean) if clean else None,
        "profitFactor": positives / negatives if negatives else None,
        "p05": quantile(clean, .05), "p10": quantile(clean, .10),
        "p90": quantile(clean, .90), "p95": quantile(clean, .95),
        "worst": min(clean) if clean else None, "best": max(clean) if clean else None,
        "standardDeviation": statistics.stdev(clean) if len(clean) > 1 else None,
    }


def cluster_summary(rows, cost, protocol, value_key="grossPct"):
    clean = [(row["sessionDate"], row[value_key] - cost) for row in rows
             if row.get(value_key) is not None and math.isfinite(row[value_key])]
    grouped = collections.defaultdict(list)
    for session, value in clean:
        grouped[session].append(value)
    sessions = sorted(grouped)
    sums = np.asarray([sum(grouped[s]) for s in sessions], dtype=float)
    counts = np.asarray([len(grouped[s]) for s in sessions], dtype=float)
    means = sums / counts if len(sums) else np.asarray([])
    result = distribution([value + cost for _, value in clean], cost)
    result["coverageRows"] = len(clean)
    result["sessions"] = len(sessions)
    result["sessionEqualMean"] = float(means.mean()) if len(means) else None
    if len(sessions) >= 2:
        rng = np.random.default_rng(protocol["statistics"]["bootstrapSeed"])
        reps = protocol["statistics"]["bootstrapReplicates"]
        indices = rng.integers(0, len(sessions), size=(reps, len(sessions)))
        boot = sums[indices].sum(axis=1) / counts[indices].sum(axis=1)
        result["clusterCI95"] = [float(np.quantile(boot, .025)), float(np.quantile(boot, .975))]
        z = 1.959963984540054 + .8416212335729143
        result["mde80PctPoints"] = float(z * np.std(means, ddof=1) / math.sqrt(len(means)))
        result["detectability"] = {str(effect): result["mde80PctPoints"] <= effect for effect in (.05, .10, .20)}
    else:
        result["clusterCI95"] = [None, None]
        result["mde80PctPoints"] = None
        result["detectability"] = {str(effect): False for effect in (.05, .10, .20)}
    return result


def paired_cluster(rows_a, rows_b, cost_a=0.0, cost_b=0.0, seed=20260919, reps=10000):
    def sessions(rows, cost):
        grouped = collections.defaultdict(list)
        for row in rows:
            value = row.get("grossPct")
            if value is not None and math.isfinite(value):
                grouped[row["sessionDate"]].append(value - cost)
        return grouped
    left, right = sessions(rows_a, cost_a), sessions(rows_b, cost_b)
    common = sorted(set(left) & set(right))
    delta = np.asarray([statistics.mean(left[s]) - statistics.mean(right[s]) for s in common], dtype=float)
    if not len(delta):
        return {"sessions": 0, "sessionEqualMeanDelta": None, "clusterCI95": [None, None], "mde80PctPoints": None}
    result = {"sessions": len(common), "sessionEqualMeanDelta": float(delta.mean())}
    if len(delta) > 1:
        rng = np.random.default_rng(seed)
        indices = rng.integers(0, len(delta), size=(reps, len(delta)))
        boot = delta[indices].mean(axis=1)
        result["clusterCI95"] = [float(np.quantile(boot, .025)), float(np.quantile(boot, .975))]
        result["mde80PctPoints"] = float((1.959963984540054 + .8416212335729143) * np.std(delta, ddof=1) / math.sqrt(len(delta)))
    else:
        result["clusterCI95"] = [None, None]
        result["mde80PctPoints"] = None
    return result


def result_rows(events, arm_ids, delay, horizon, mode):
    output = []
    for event_id in arm_ids:
        event = events[event_id]
        outcome = event["delays"][str(delay)][mode][str(horizon)]
        output.append({"selectorEventId": event_id, "sessionDate": event["sessionDate"],
                       "grossPct": outcome["grossPct"], "status": outcome["status"]})
    return output


def summarize_arms(events, selection, protocol):
    summary = {}
    for arm in ARMS:
        arm_summary = {"immediateEntryRelative": {}, "immediateSelectorTerminal": {}}
        for mode, key in (("entryRelative", "immediateEntryRelative"), ("selectorTerminal", "immediateSelectorTerminal")):
            for horizon in HORIZONS:
                rows = result_rows(events, selection[arm], 0, horizon, mode)
                arm_summary[key][str(horizon)] = {
                    "gross": cluster_summary(rows, 0.0, protocol),
                    "canonicalNet": cluster_summary(rows, 0.05, protocol),
                    "net10bps": cluster_summary(rows, 0.10, protocol),
                    "net20bps": cluster_summary(rows, 0.20, protocol),
                }
        summary[arm] = arm_summary
    return summary


def summarize_delay(events, ids, protocol):
    output = {"entryRelative": {}, "selectorTerminal": {}}
    for mode in output:
        for horizon in HORIZONS:
            output[mode][str(horizon)] = {}
            base = result_rows(events, ids, 0, horizon, mode)
            for delay in DELAYS:
                rows = result_rows(events, ids, delay, horizon, mode)
                output[mode][str(horizon)][str(delay)] = {
                    "canonicalNet": cluster_summary(rows, .05, protocol),
                    "deltaVsDelay0": paired_cluster(rows, base, .05, .05,
                                                    protocol["statistics"]["bootstrapSeed"],
                                                    protocol["statistics"]["bootstrapReplicates"]),
                }
    return output


def incremental(events, selection, protocol):
    output = {}
    for mode in ("entryRelative", "selectorTerminal"):
        output[mode] = {}
        for horizon in HORIZONS:
            selector = result_rows(events, selection["FROZEN_SELECTOR"], 0, horizon, mode)
            output[mode][str(horizon)] = {}
            for baseline in ("RANDOM_TOP5", "MOMENTUM30_TOP5"):
                other = result_rows(events, selection[baseline], 0, horizon, mode)
                output[mode][str(horizon)][baseline] = paired_cluster(
                    selector, other, .05, .05, protocol["statistics"]["bootstrapSeed"],
                    protocol["statistics"]["bootstrapReplicates"])
    return output


def bucket_price(price):
    if price <= 100: return "076_100"
    if price <= 200: return "101_200"
    if price <= 500: return "201_500"
    if price <= 1000: return "501_1000"
    return "1001_PLUS"


def bucket_time(time_jst):
    if time_jst <= "10:30": return "MORNING_EARLY"
    if time_jst <= "11:30": return "MORNING_LATE"
    if time_jst <= "14:00": return "AFTERNOON_EARLY"
    return "AFTERNOON_LATE"


def group_diagnostic(events, ids, field, key_fn, protocol):
    groups = collections.defaultdict(list)
    for event_id in ids:
        event = events[event_id]
        key = key_fn(event)
        outcome = event["delays"]["0"]["entryRelative"]["30"]
        groups[str(key)].append({"sessionDate": event["sessionDate"], "grossPct": outcome["grossPct"]})
    return {key: cluster_summary(rows, .05, protocol) for key, rows in sorted(groups.items())}


def diagnostics(events, selector_ids, protocol):
    symbols = collections.Counter(events[event_id]["symbol"] for event_id in selector_ids)
    total = len(selector_ids)
    prices = [float(events[event_id]["decisionPrice"]) for event_id in selector_ids]
    scores = np.asarray([events[event_id]["metadata"]["savedV1Score"] for event_id in selector_ids], dtype=float)
    boundaries = [float(value) for value in np.quantile(scores, [.2, .4, .6, .8])]
    def score_bin(event):
        return 1 + sum(event["metadata"]["savedV1Score"] > edge for edge in boundaries)
    quantization = {
        "actualDatedTickSize": None,
        "reason": "DATED_SECURITY_SPECIFIC_TICK_SCHEDULE_NOT_SAVED",
        "oneYenReturnPct": distribution([100 / price for price in prices]),
        "thresholdNominalOneYenIncrementCount": {
            str(level): distribution([math.ceil(price * level / 100) for price in prices]) for level in (1, 3, 5)
        },
        "rowsWhereOneYenAtLeastOnePct": sum(100 / price >= 1 for price in prices),
    }
    opportunity = {}
    for level in (3, 5):
        winners = []
        losing30 = 0
        for event_id in selector_ids:
            event = events[event_id]
            if event["metadata"].get(f"highOpportunity{level}") == 1:
                gross = event["delays"]["0"]["entryRelative"]["30"]["grossPct"]
                if gross is not None:
                    winners.append(gross - .05)
                    losing30 += gross - .05 <= 0
        opportunity[str(level)] = {"evaluableWinners": len(winners), "net30NonPositive": losing30,
                                   "net30NonPositiveRate": losing30 / len(winners) if winners else None,
                                   "net30": distribution([value + .05 for value in winners], .05)}
    return {
        "effectiveSample": {
            "rawRows": total,
            "sessions": len({events[event_id]["sessionDate"] for event_id in selector_ids}),
            "decisionTimestamps": len({events[event_id]["decisionTimestamp"] for event_id in selector_ids}),
            "symbols": len(symbols),
            "repeatedSymbolRows": sum(count - 1 for count in symbols.values()),
            "symbolHHI": sum((count / total) ** 2 for count in symbols.values()),
            "topSymbols": symbols.most_common(10),
        },
        "priceBand": group_diagnostic(events, selector_ids, "price", lambda e: bucket_price(float(e["decisionPrice"])), protocol),
        "timeOfDay": group_diagnostic(events, selector_ids, "time", lambda e: bucket_time(e["decisionTimestamp"][11:16]), protocol),
        "rank": group_diagnostic(events, selector_ids, "rank", lambda e: e["metadata"].get("selectorRank"), protocol),
        "scoreQuintile": {"boundaries": boundaries,
                           "results": group_diagnostic(events, selector_ids, "score", score_bin, protocol)},
        "preSelectionMomentumSign": group_diagnostic(
            events, selector_ids, "momentum",
            lambda e: "NEGATIVE" if e["metadata"]["momentum30Pct"] < 0 else "NONNEGATIVE", protocol),
        "priceQuantization": quantization,
        "mfeVsFixedReturn": opportunity,
    }


def path_range(bars, start, end):
    selected = [bar for bar in bars if bar["start"] >= start and bar["end"] <= end]
    if not selected or any(not bar["valid"] for bar in selected):
        return None
    return selected


def dip_entry(policy, bars, decision, decision_price):
    immediate = entry_at_or_after(bars, decision)
    if policy == "P0_IMMEDIATE":
        return immediate
    if policy == "P2_FIXED5":
        return entry_at_or_after(bars, decision + dt.timedelta(minutes=5))
    if policy == "P3_FIXED10":
        return entry_at_or_after(bars, decision + dt.timedelta(minutes=10))
    assert policy == "P1_DIP_FALLBACK10"
    if immediate["status"] != "AVAILABLE":
        return immediate
    first = immediate["bar"]
    if first["valid"] and first["c"] < decision_price:
        intended = first["end"]
    else:
        intended = first["end"] + dt.timedelta(minutes=5)
    return entry_at_or_after(bars, intended)


def dip_itt(paths, events, selector_ids, protocol):
    policies = ("P0_IMMEDIATE", "P1_DIP_FALLBACK10", "P2_FIXED5", "P3_FIXED10")
    rows = {policy: [] for policy in policies}
    for event_id in selector_ids:
        path = paths[event_id]
        bars = materialize_path(path)
        decision = timestamp(path["decisionTimestamp"])
        per_policy = {}
        for policy in policies:
            entry = dip_entry(policy, bars, decision, float(path["decisionPrice"]))
            item = {"sessionDate": path["sessionDate"], "selectorEventId": event_id,
                    "entryAvailable": entry["status"] == "AVAILABLE", "grossPct": None,
                    "maePct": None, "remainingMfePct": None, "entryStatus": entry["status"]}
            if entry["status"] == "AVAILABLE":
                start = timestamp(entry["timestamp"])
                exit_row = exact_exit(bars, start + dt.timedelta(minutes=30))
                item["grossPct"] = trade_return(entry, exit_row)
                window = path_range(bars, start, start + dt.timedelta(minutes=30))
                if window:
                    item["maePct"] = 100 * (min(bar["l"] for bar in window) / entry["price"] - 1)
                    item["remainingMfePct"] = 100 * (max(bar["h"] for bar in window) / entry["price"] - 1)
            per_policy[policy] = item
            rows[policy].append(item)
        baseline_mfe = per_policy["P0_IMMEDIATE"]["remainingMfePct"]
        for policy in policies:
            rows[policy][-1]["baselineMfePct"] = baseline_mfe
    result = {"populationRows": len(selector_ids), "policies": {}}
    for policy in policies:
        policy_rows = rows[policy]
        result["policies"][policy] = {
            "entryCoverage": sum(row["entryAvailable"] for row in policy_rows) / len(policy_rows),
            "entryStates": dict(collections.Counter(row["entryStatus"] for row in policy_rows)),
            "net30": cluster_summary(policy_rows, .05, protocol),
            "mae30": distribution([row["maePct"] for row in policy_rows]),
            "remainingMfe30": distribution([row["remainingMfePct"] for row in policy_rows]),
            "preservation": {
                str(level): {
                    "baseline": sum(row["baselineMfePct"] is not None and row["baselineMfePct"] >= level for row in policy_rows),
                    "preserved": sum(row["baselineMfePct"] is not None and row["baselineMfePct"] >= level
                                     and row["remainingMfePct"] is not None and row["remainingMfePct"] >= level for row in policy_rows),
                } for level in (3, 5)
            },
        }
    for comparator in ("P2_FIXED5", "P3_FIXED10", "P0_IMMEDIATE"):
        result[f"P1Minus{comparator}"] = paired_cluster(rows["P1_DIP_FALLBACK10"], rows[comparator], .05, .05,
                                                        protocol["statistics"]["bootstrapSeed"],
                                                        protocol["statistics"]["bootstrapReplicates"])
    return result


def classify(arms, delays, increments, protocol):
    primary = (10, 15, 30)
    positive = False
    negative = True
    any_positive_point = False
    for horizon in primary:
        metric = arms["FROZEN_SELECTOR"]["immediateEntryRelative"][str(horizon)]["canonicalNet"]
        random = increments["entryRelative"][str(horizon)]["RANDOM_TOP5"]
        momentum = increments["entryRelative"][str(horizon)]["MOMENTUM30_TOP5"]
        any_positive_point |= metric["mean"] is not None and metric["mean"] > 0
        positive |= (metric["mean"] is not None and metric["mean"] >= .10
                     and metric["clusterCI95"][0] is not None and metric["clusterCI95"][0] > 0
                     and metric["profitFactor"] is not None and metric["profitFactor"] > 1
                     and random["clusterCI95"][0] is not None and random["clusterCI95"][0] > 0
                     and momentum["clusterCI95"][0] is not None and momentum["clusterCI95"][0] > 0)
        negative &= metric["clusterCI95"][1] is not None and metric["clusterCI95"][1] < 0
    if positive:
        selector_verdict = "SELECTOR_ECONOMIC_ALPHA_POSITIVE"
    elif negative:
        selector_verdict = "SELECTOR_ECONOMIC_ALPHA_NEGATIVE"
    elif not any_positive_point:
        selector_verdict = "SELECTOR_ECONOMIC_ALPHA_NOT_DEMONSTRATED"
    else:
        selector_verdict = "SELECTOR_ECONOMIC_ALPHA_WEAK_OR_UNCERTAIN"

    curve = delays["selectorTerminal"]["30"]
    base_mean = curve["0"]["canonicalNet"]["mean"]
    usable = curve["0"]["canonicalNet"]["sessions"] >= 38
    mde = curve["0"]["canonicalNet"]["mde80PctPoints"]
    if not usable or mde is None or mde > .20:
        timing = "INCONCLUSIVE"
    else:
        supported = [delay for delay in DELAYS[1:]
                     if curve[str(delay)]["deltaVsDelay0"]["sessionEqualMeanDelta"] is not None
                     and curve[str(delay)]["deltaVsDelay0"]["sessionEqualMeanDelta"] >= .10
                     and curve[str(delay)]["deltaVsDelay0"]["clusterCI95"][0] is not None
                     and curve[str(delay)]["deltaVsDelay0"]["clusterCI95"][0] > 0]
        if supported:
            timing = "DELAYED_ENTRY_SUPPORTED"
        else:
            means = {delay: curve[str(delay)]["canonicalNet"]["mean"] for delay in DELAYS}
            worse = [delay for delay in DELAYS[1:]
                     if curve[str(delay)]["deltaVsDelay0"]["clusterCI95"][1] is not None
                     and curve[str(delay)]["deltaVsDelay0"]["clusterCI95"][1] < 0]
            if base_mean is not None and base_mean == max(value for value in means.values() if value is not None) and worse:
                timing = "IMMEDIATE_ENTRY_SUPPORTED"
            else:
                timing = "NO_TIMING_EDGE_DEMONSTRATED"
    return {"selectorEconomicAlpha": selector_verdict, "entryTiming": timing}


def markdown(summary):
    lines = [
        "# Phase57 Frozen Selector Economic Alpha v1", "",
        f"**Selector verdict: {summary['verdicts']['selectorEconomicAlpha']}**  ",
        f"**Entry timing verdict: {summary['verdicts']['entryTiming']}**", "",
        "Development-only, model-free diagnostic. Prices are saved five-minute reference marks, not guaranteed fills.", "",
        "## Immediate entry - entry-relative fixed horizons", "",
        "| Horizon | N | Gross mean | Canonical net mean | 95% session-cluster CI | PF | Positive |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    selector = summary["arms"]["FROZEN_SELECTOR"]["immediateEntryRelative"]
    for horizon in HORIZONS:
        gross = selector[str(horizon)]["gross"]
        net = selector[str(horizon)]["canonicalNet"]
        ci = net["clusterCI95"]
        lines.append(f"| {horizon}m | {net['n']} | {gross['mean']:.4f}% | {net['mean']:.4f}% | [{ci[0]:.4f}, {ci[1]:.4f}] | {net['profitFactor']:.4f} | {100*net['positiveRate']:.2f}% |")
    lines += ["", "## 30-minute baseline comparison", "",
              "| Arm | N | Canonical net mean | 95% CI | PF |", "|---|---:|---:|---:|---:|"]
    for arm in ARMS:
        net = summary["arms"][arm]["immediateEntryRelative"]["30"]["canonicalNet"]
        ci = net["clusterCI95"]
        lines.append(f"| {arm} | {net['n']} | {net['mean']:.4f}% | [{ci[0]:.4f}, {ci[1]:.4f}] | {net['profitFactor']:.4f} |")
    lines += ["", "## Selector-terminal 30-minute delay curve", "",
              "| Intended delay | N | Canonical net mean | 95% CI | Delta vs 0 | Delta CI |", "|---:|---:|---:|---:|---:|---:|"]
    for delay in DELAYS:
        row = summary["delays"]["selectorTerminal"]["30"][str(delay)]
        net, delta = row["canonicalNet"], row["deltaVsDelay0"]
        ci, dci = net["clusterCI95"], delta["clusterCI95"]
        lines.append(f"| {delay}m | {net['n']} | {net['mean']:.4f}% | [{ci[0]:.4f}, {ci[1]:.4f}] | {delta['sessionEqualMeanDelta']:.4f}% | [{dci[0]:.4f}, {dci[1]:.4f}] |")
    lines += ["", "## Execution limits", "",
              "- Canonical cost is the pre-existing 5bps round-trip assumption; 10bps and 20bps are fixed sensitivities.",
              "- Saved data contains no bid/ask, order book, depth or dated security-specific tick schedule.",
              "- The one-yen diagnostic is nominal price quantization, not a claim about the exchange tick or achievable spread.",
              "- DEV TEST, Fresh and OOS remain sealed. No provider request, fit, Selector/Entry/EXIT/Capital change or promotion occurred.", ""]
    return "\n".join(lines)


def measure(selection_file, path_file, output_dir):
    protocol = load_protocol()
    selection = read(selection_file)
    assert selection["contractSHA256"] == sha(PROTOCOL)
    assert selection["providerRequests"] == 0 and selection["fitCalls"] == 0
    assert selection["developmentTestOpened"] is False and selection["freshOOSOpened"] is False
    assert selection["safety"] == protocol["safety"]
    assert all(len(selection["arms"][arm]) == 3800 for arm in ARMS)
    metadata = {row["selectorEventId"]: row for row in selection["new"]}
    path_payload = read(path_file)
    paths = {row["selectorEventId"]: row for row in path_payload["events"]}
    assert set(paths) == set(metadata)
    frozen_existing = {row["selectorEventId"]: row for row in read(FROZEN_PATHS)["events"]}
    for event_id in selection["arms"]["FROZEN_SELECTOR"]:
        assert event_id in frozen_existing and encoded(paths[event_id]) == encoded(frozen_existing[event_id])
    events = {event_id: evaluate_event(paths[event_id], metadata[event_id]) for event_id in sorted(paths)}
    arms = summarize_arms(events, selection["arms"], protocol)
    delays = summarize_delay(events, selection["arms"]["FROZEN_SELECTOR"], protocol)
    increments = incremental(events, selection["arms"], protocol)
    summary = {
        "schemaVersion": 1,
        "contractSHA256": sha(PROTOCOL),
        "sourceHead": protocol["sourceHead"],
        "population": selection["universe"],
        "execution": protocol["execution"],
        "cost": protocol["cost"],
        "statistics": protocol["statistics"],
        "arms": arms,
        "incremental": increments,
        "delays": delays,
        "diagnostics": diagnostics(events, selection["arms"]["FROZEN_SELECTOR"], protocol),
        "dipITT": dip_itt(paths, events, selection["arms"]["FROZEN_SELECTOR"], protocol),
        "sealed": protocol["sealed"],
        "safety": protocol["safety"],
    }
    summary["verdicts"] = classify(arms, delays, increments, protocol)
    out = Path(output_dir)
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    shutil.copyfile(selection_file, out / "membership-ledger.json.gz")
    write(out / "event-ledger.json.gz", list(events.values()))
    write(out / "summary.json", summary)
    (out / "REPORT.md").write_text(markdown(summary))
    manifest = {
        "contractSHA256": sha(PROTOCOL),
        "selectionSHA256": sha(selection_file),
        "pathsSHA256": sha(path_file),
        "outputs": {name: sha(out / name) for name in
                    ("membership-ledger.json.gz", "event-ledger.json.gz", "summary.json", "REPORT.md")},
        "providerRequests": 0, "fitCalls": 0, "developmentTestOpened": False, "freshOOSOpened": False,
        "safety": protocol["safety"],
    }
    write(out / "manifest.json", manifest)
    print(json.dumps({"status": "ECONOMIC_ALPHA_MEASUREMENT_COMPLETE", "verdicts": summary["verdicts"],
                      "unionEvents": len(events), "output": str(out)}))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--dataset-dir", required=True)
    prepare_parser.add_argument("--output", required=True)
    measure_parser = sub.add_parser("measure")
    measure_parser.add_argument("--selection", required=True)
    measure_parser.add_argument("--paths", required=True)
    measure_parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.dataset_dir, args.output)
    else:
        measure(args.selection, args.paths, args.output_dir)


if __name__ == "__main__":
    main()
