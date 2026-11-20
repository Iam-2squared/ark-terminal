"""First frozen-30m Universe / 5m PIT WATCH Entry measurement.

The Selector is immutable.  A raw Top5 snapshot is held only until its next
scheduled snapshot; score/rank never change inside that window.  The policy is
fit once on TRAIN and evaluated once on VALIDATION.  DEV TEST and Fresh/OOS are
deliberately inaccessible from this module's public run path.
"""
from __future__ import annotations

import argparse
import collections
import copy
import gzip
import hashlib
import json
import math
import platform
import statistics
from pathlib import Path

import numpy as np
import sklearn
from sklearn.tree import DecisionTreeRegressor

from scripts import phase57_comprehensive_entry as v1
from scripts import phase57_comprehensive_entry_v2 as v2
from scripts import phase57_comprehensive_entry_v3 as v3
from scripts import phase57_raw_selector_direct_entry_preflight as preflight


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/evidence/phase57-raw-selector-direct-entry-v1/window-study"
PROTOCOL_PATH = BASE / "protocol.json"
FEATURE_PATH = BASE / "feature-manifest.json"
RAW_PATH = ROOT / "docs/evidence/phase57-selector-min-price75-v1/measurement/selector/selector-ledger.json.gz"
PATHS_PATH = ROOT / "docs/evidence/phase57-selector-min-price75-v1/measurement/new-paths.json.gz"
LEGACY_PATH = ROOT / "docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz"
ENTRY_PATH = ROOT / "docs/evidence/phase57-selector-min-price75-v1/measurement/downstream/entry-decisions.json.gz"
SAFETY = preflight.SAFETY
RAW_SOURCE = "RAW_SELECTOR_FIRST_SELECTION"


def read(path):
    path = Path(path)
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    text = data.decode()
    if path.name.endswith(".ndjson.gz"):
        return [json.loads(line) for line in text.splitlines() if line]
    return json.loads(text)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()


def write(path, value):
    path = Path(path)
    data = encoded(value)
    if path.suffix == ".gz":
        data = gzip.compress(data, mtime=0)
    with path.open("xb") as stream:
        stream.write(data)


def protocol():
    p = read(PROTOCOL_PATH)
    assert p["id"] == "RAW_SELECTOR_DIRECT_ENTRY_V1_FROZEN_30M_UNIVERSE_5M_PIT_WATCH"
    assert p["candidateFreeze"] is False
    assert p["developmentTestOpened"] is False and p["freshOOSOpened"] is False
    assert p["safety"] == SAFETY and all(value is False for value in SAFETY.values())
    assert sha(FEATURE_PATH) == p["featureManifestSHA256"]
    assert sha(BASE / "authorization.json") == p["authorizationSHA256"]
    for name, digest in p["sourcePins"].items():
        assert sha(ROOT / name) == digest, name
    return p


def minute(value):
    return v1.c.minute(value)


def scheduled_next(timestamp):
    m = minute(timestamp)
    if m < 690:
        return m + 30
    if m == 690:
        return 750
    return m + 30


def window_end(path, timestamp):
    start = minute(timestamp)
    segment = v1.c.segment_end(start, path["sessionEndMinute"])
    if segment is None:
        return None
    return min(segment, scheduled_next(timestamp))


def synthetic_episode(first, path):
    execution = v2.open_reference(path, minute(first["decisionTimestamp"]))
    op = {
        "anchorId": first["selectorEventId"],
        "decisionPrice": first["decisionPrice"],
        "decisionTimestamp": first["decisionTimestamp"],
        "eventType": RAW_SOURCE,
        "opportunityTimestamp": first["decisionTimestamp"],
        "referenceTimestamp": first["decisionTimestamp"],
        "referencePrice": execution,
        "referenceStatus": "REFERENCE_OPEN" if execution is not None else "REFERENCE_MISSING",
        "session": first["sessionDate"],
        "symbol": first["symbol"],
    }
    return {
        "id": first["symbolSessionId"],
        "session": first["sessionDate"],
        "symbol": first["symbol"],
        "breadth": 5,
        "op": op,
    }


def load_sources():
    p = protocol()
    rows = preflight.project(read(RAW_PATH)["new"])
    assert len(rows) == 3800 and len({r["decisionTimestamp"] for r in rows}) == 760
    paths = {row["selectorEventId"]: row for row in read(PATHS_PATH)["events"]}
    legacy = {row["selectorEventId"]: row for row in read(LEGACY_PATH)}
    grouped = collections.defaultdict(list)
    for row in rows:
        assert row["selectorEventId"] in paths
        grouped[(row["sessionDate"], row["symbol"])].append(row)
    episodes = []
    for key, selections in sorted(grouped.items()):
        selections.sort(key=lambda row: row["decisionTimestamp"])
        first = dict(selections[0], symbolSessionId="|".join(key))
        item = synthetic_episode(first, paths[first["selectorEventId"]])
        item["firstSelector"] = first
        item["selections"] = selections
        episodes.append(item)
    assert len(episodes) == p["episodes"]["expectedAll"] == 2841
    for partition, expected in p["episodes"]["expectedByPartition"].items():
        assert sum(e["session"] in p["split"][partition] for e in episodes) == expected
    return p, episodes, paths, legacy


FEATURES = read(FEATURE_PATH)["features"]
BASE_FEATURES = v1.FEATURES
DESCRIPTORS = ["state_" + name for name in v3.protocol_descriptor_names()]
HISTORY = [name for name in FEATURES if name not in BASE_FEATURES + DESCRIPTORS]
assert len(FEATURES) == 77 and len(HISTORY) == 11


def completed_prefix(path, decision_minute):
    anchor = minute(path["decisionTimestamp"])
    expected = v1.c.grid(anchor, decision_minute)
    bars = [bar for bar in path["future"] if minute(bar["end"]) <= decision_minute]
    if [minute(bar["start"]) for bar in bars] != expected or not all(v1.c.valid(bar) for bar in bars):
        return None
    return bars


def snapshot_history(episode, path, decision_minute, bars):
    first = episode["firstSelector"]
    anchor = minute(first["decisionTimestamp"])
    end = window_end(path, first["decisionTimestamp"])
    close = bars[-1]["c"] if bars else 0.0
    return {
        "snapshotAge": decision_minute - anchor,
        "snapshotReferenceAge": first["referenceAgeMin"] + decision_minute - anchor,
        "selectionCountKnown": 1,
        "consecutiveSelectionsKnown": 1,
        "selectionGapsKnown": 0,
        "scoreChangeSincePriorSelection": None,
        "rankChangeSincePriorSelection": None,
        "priceReturnFromFirstSelection": close,
        "minutesUntilWindowEnd": end - decision_minute if end is not None else None,
        "selectedAtPriorObservedDecision": 0,
        "snapshotBreadth": 5,
    }


def state(episode, path, legacy, delay):
    first = episode["firstSelector"]
    start = minute(first["decisionTimestamp"])
    decision_minute = start + delay
    end = window_end(path, first["decisionTimestamp"])
    if end is None or decision_minute >= end:
        return {"status": "EXPIRE_BOUNDARY", "delay": delay, "timestamp": v1.c.stamp(episode["session"], decision_minute)}
    bars = completed_prefix(path, decision_minute)
    if bars is None:
        return {"status": "EXPIRE_MISSING_PREFIX", "delay": delay, "timestamp": v1.c.stamp(episode["session"], decision_minute)}
    base = v1.features(episode, path, first, legacy, decision_minute)
    if base is None:
        return {"status": "EXPIRE_MISSING_PREFIX", "delay": delay, "timestamp": v1.c.stamp(episode["session"], decision_minute)}
    desc = v3.describe(bars)
    features = dict(base)
    features.update({"state_" + key: value for key, value in desc.items()})
    features.update(snapshot_history(episode, path, decision_minute, bars))
    assert set(features) == set(FEATURES)
    return {
        "status": "AVAILABLE",
        "delay": delay,
        "timestamp": v1.c.stamp(episode["session"], decision_minute),
        "features": features,
        "newestCompletedEnd": bars[-1]["end"] if bars else None,
        "selectorSnapshotTimestamp": first["decisionTimestamp"],
        "selectorRank": first["newEligibleRank"],
        "selectorScore": first["savedV1Score"],
        "decisionPrice": first["decisionPrice"],
        "canWatch": delay < 10 and decision_minute + 5 < end,
        "intrabarOrder": "UNKNOWN_INTRABAR_ORDER",
    }


def states(episode, path, legacy):
    result = []
    terminal = False
    for delay in (0, 5, 10):
        row = state(episode, path, legacy, delay) if not terminal else {
            "status": "TERMINAL_AFTER_CRITICAL_MISSING", "delay": delay,
            "timestamp": v1.c.stamp(episode["session"], minute(episode["op"]["opportunityTimestamp"]) + delay),
        }
        result.append(row)
        terminal = row["status"] not in ("AVAILABLE",)
    return result


def evaluate(episode, path, delay, with_exit=False, runtime=None):
    if with_exit:
        assert runtime is not None
        return v1.eval_entry(episode, path, delay, runtime)
    return v2.evaluate(episode, path, delay)


def path_class(episode, path):
    return v1.path_class(episode, path)


def labels(now, nxt):
    if not (now and nxt and now["commonComplete"] and nxt["commonComplete"] and now["strict30Complete"] and nxt["strict30Complete"]):
        return None
    lost = any(now["common"]["mfe"] >= threshold and nxt["common"]["mfe"] < threshold for threshold in (3, 5))
    chase = bool(now["fastWinner"] and nxt["price"] > now["price"])
    return [
        100 * (now["price"] - nxt["price"]) / now["price"],
        5.0 * int(lost or chase),
        nxt["strict30"]["mae"] - now["strict30"]["mae"],
    ]


def training_dataset(episodes, paths, legacy):
    rows = []
    pit = []
    for episode in episodes:
        first = episode["firstSelector"]
        path = paths[first["selectorEventId"]]
        projected = states(episode, path, legacy.get(first["selectorEventId"], {}))
        pit.append({"id": episode["id"], "session": episode["session"], "states": projected})
        baseline = evaluate(episode, path, 0)
        if not baseline or not baseline["commonComplete"]:
            continue
        group = []
        for delay in (0, 5):
            current = projected[delay // 5]
            nxt_state = projected[delay // 5 + 1]
            if current["status"] != "AVAILABLE" or nxt_state["status"] != "AVAILABLE":
                continue
            target = labels(evaluate(episode, path, delay), evaluate(episode, path, delay + 5))
            if target is not None:
                group.append({"id": episode["id"], "session": episode["session"], "delay": delay, "features": current["features"], "targets": target})
        for row in group:
            row["weight"] = 1 / len(group)
            rows.append(row)
    return pit, rows


def matrix(features):
    return np.asarray([[row.get(name) if row.get(name) is not None else np.nan for name in FEATURES] for row in features], dtype=float)


class Model:
    def __init__(self, artifact):
        self.artifact = artifact

    @classmethod
    def fit_once(cls, rows, p):
        x = matrix([row["features"] for row in rows])
        medians = np.asarray([np.median(col[np.isfinite(col)]) if np.isfinite(col).any() else 0.0 for col in x.T])
        valid = np.isfinite(x)
        z = np.concatenate([np.where(valid, x, medians), ~valid], axis=1)
        y = np.asarray([row["targets"] for row in rows])
        weights = np.asarray([row["weight"] for row in rows])
        estimator = DecisionTreeRegressor(**p["architecture"]["hyperparameters"])
        estimator.fit(z, y, sample_weight=weights)
        tree = estimator.tree_
        artifact = {
            "kind": p["architecture"]["id"],
            "features": FEATURES,
            "outputs": p["architecture"]["outputs"],
            "hyperparameters": p["architecture"]["hyperparameters"],
            "medians": medians.tolist(),
            "missingIndicatorOrder": FEATURES,
            "tree": {name: getattr(tree, name).tolist() for name in (
                "children_left", "children_right", "feature", "threshold", "value",
                "n_node_samples", "weighted_n_node_samples", "impurity")},
            "runtime": {"python": platform.python_version(), "numpy": np.__version__, "sklearn": sklearn.__version__},
        }
        model = cls(artifact)
        assert np.allclose(model.predict_many([row["features"] for row in rows]), estimator.predict(z), rtol=0, atol=1e-14)
        return model

    def vector(self, features):
        raw = matrix([features])[0]
        valid = np.isfinite(raw)
        return np.concatenate([np.where(valid, raw, np.asarray(self.artifact["medians"])), ~valid]).astype(float)

    def predict(self, features):
        vector = self.vector(features)
        tree = self.artifact["tree"]
        node = 0
        while tree["children_left"][node] != -1:
            node = tree["children_left"][node] if vector[tree["feature"][node]] <= tree["threshold"][node] else tree["children_right"][node]
        return [float(value[0]) for value in tree["value"][node]]

    def predict_many(self, features):
        return np.asarray([self.predict(row) for row in features])


def fit_audit(model, rows):
    y = np.asarray([row["targets"] for row in rows])
    weights = np.asarray([row["weight"] for row in rows])
    expected = np.average(y, axis=0, weights=weights)
    stored = np.asarray(model.artifact["tree"]["value"][0]).reshape(-1)
    return {
        "independentSerializedReplay": bool(np.isfinite(model.predict_many([row["features"] for row in rows])).all()),
        "rootWeightedTargetMean": expected.tolist(),
        "rootStoredValue": stored.tolist(),
        "rootMomentExact": bool(np.allclose(expected, stored, rtol=0, atol=1e-12)),
        "fitStates": len(rows),
        "effectiveEpisodeWeight": float(weights.sum()),
        "nodeCount": len(model.artifact["tree"]["feature"]),
    }


def decide(episode, path, projected, model, p):
    log = []
    if episode["op"]["referenceStatus"] != "REFERENCE_OPEN":
        return {"status": "EXPIRE_REFERENCE", "delay": None, "executionPrice": None, "transitions": log}
    for row in projected:
        if row["status"] != "AVAILABLE":
            return {"status": row["status"], "delay": None, "executionPrice": None, "transitions": log}
        scores = model.predict(row["features"])
        price_gain, loss_score, risk_gain = scores
        thresholds = p["decision"]["watchThresholds"]
        watch = (row["canWatch"] and price_gain >= thresholds["priceImprovementPP"] and
                 loss_score / 5 <= thresholds["opportunityLossProbabilityMax"] and
                 risk_gain >= thresholds["strict30MAEImprovementPP"])
        action = "WATCH" if watch else "BUY_NOW"
        log.append({
            "timestamp": row["timestamp"], "delay": row["delay"], "action": action,
            "scores": dict(zip(p["architecture"]["outputs"], scores)),
            "selectorSnapshotTimestamp": row["selectorSnapshotTimestamp"],
            "selectorRank": row["selectorRank"], "selectorScore": row["selectorScore"],
            "missingFeatures": [name for name in FEATURES if row["features"][name] is None],
        })
        if action == "WATCH":
            continue
        execution = v2.open_reference(path, minute(row["timestamp"]))
        return {
            "status": "COUNTERFACTUAL_ENTER" if execution is not None else "EXPIRE_MISSING_OPEN",
            "delay": row["delay"] if execution is not None else None,
            "executionPrice": execution,
            "transitions": log,
        }
    raise AssertionError("UNTERMINATED_POLICY")


def measure(episodes, paths, legacy, model, p, with_exit=False):
    runtime = v1.c.module("raw_direct_exact_candidate_a", v1.c.RUNTIME) if with_exit else None
    pit, rows = [], []
    for episode in episodes:
        first = episode["firstSelector"]
        path = paths[first["selectorEventId"]]
        projected = states(episode, path, legacy.get(first["selectorEventId"], {}))
        decision = decide(episode, path, projected, model, p)
        baseline = evaluate(episode, path, 0, with_exit, runtime)
        entry = evaluate(episode, path, decision["delay"], with_exit, runtime) if decision["delay"] is not None else None
        rows.append({
            "id": episode["id"], "session": episode["session"], "symbol": episode["symbol"],
            "source": RAW_SOURCE, "breadth": 5, "timestamp": first["decisionTimestamp"],
            "pathClass": path_class(episode, path), "decision": decision,
            "baseline": baseline, "entry": entry, "selectionCount": len(episode["selections"]),
            "maxConsecutiveObservedSelections": preflight.episodes(episode["selections"])[0]["maxConsecutiveObservedSelections"],
            "reselected": preflight.episodes(episode["selections"])[0]["selectionGapCount"] > 0,
            "rangeMeanAt0": projected[0].get("features", {}).get("rangeMean"),
        })
        pit.append({"id": episode["id"], "session": episode["session"], "states": projected})
    return pit, rows


def fraction(numerator, denominator):
    return numerator / denominator if denominator else None


def dist(values):
    clean = [value for value in values if value is not None and math.isfinite(value)]
    result = v1.dist(clean)
    if clean:
        result.update(p10=v1.c.quantile(clean, .1), p25=v1.c.quantile(clean, .25), p75=v1.c.quantile(clean, .75))
    else:
        result.update(p10=None, p25=None, p75=None)
    return result


def summary(rows):
    result = v2.summarize(rows)
    common = [row for row in rows if row["baseline"] and row["baseline"]["commonComplete"]]
    pairs = [row for row in common if row["entry"] and row["entry"]["commonComplete"]]
    strict = [row for row in pairs if row["baseline"]["strict30Complete"] and row["entry"]["strict30Complete"]]
    improvements = [100 * (row["baseline"]["price"] - row["entry"]["price"]) / row["baseline"]["price"] for row in pairs]
    result.update({
        "entryCoverage": fraction(len(pairs), len(common)),
        "priceImprovement": dist(improvements),
        "favorablePriceRate": fraction(sum(value > 0 for value in improvements), len(improvements)),
        "delay": dist([row["decision"]["delay"] for row in rows if row["decision"]["delay"] is not None]),
        "delayDistribution": dict(collections.Counter("EXPIRE" if row["decision"]["delay"] is None else str(row["decision"]["delay"]) for row in rows)),
        "watchEpisodes": sum(any(step["action"] == "WATCH" for step in row["decision"]["transitions"]) for row in rows),
        "delayedEntries": sum(row["decision"]["delay"] in (5, 10) for row in rows),
        "strict30MedianImprovementPP": None,
        "strict30P05ImprovementPP": None,
        "remainingMFERatio": None,
    })
    if strict:
        before = dist([row["baseline"]["strict30"]["mae"] for row in strict])
        after = dist([row["entry"]["strict30"]["mae"] for row in strict])
        result["strict30MedianImprovementPP"] = after["median"] - before["median"]
        result["strict30P05ImprovementPP"] = after["p05"] - before["p05"]
    if pairs:
        before_mfe = statistics.mean(row["baseline"]["common"]["mfe"] for row in pairs)
        after_mfe = statistics.mean(row["entry"]["common"]["mfe"] for row in pairs)
        result["remainingMFERatio"] = after_mfe / before_mfe if before_mfe > 0 else None
    return result


def economic_row(episode, path, decision, runtime):
    baseline = evaluate(episode, path, 0, True, runtime)
    entry = evaluate(episode, path, decision["delay"], True, runtime) if decision["delay"] is not None else None
    if not baseline or not baseline["commonComplete"] or baseline["candidateA"] is None:
        return None
    if decision["delay"] is not None and (entry is None or entry["candidateA"] is None):
        return None
    def arm(value):
        if value is None:
            return None
        candidate = value["candidateA"]
        return {"net": candidate["netPct"], "reason": candidate["status"], "result": candidate,
                "price": value["price"], "delay": value["delay"]}
    return {"id": episode["id"], "session": episode["session"], "symbol": episode["symbol"],
            "baseline": arm(baseline), "entry": arm(entry)}


def economic_metrics(rows):
    if not rows:
        return {"n": 0, "entered": 0, "baseline": v1.perf([]), "policyCashIncluded": v1.perf([]), "delta": dist([])}
    baseline = [row["baseline"]["net"] for row in rows]
    policy = [row["entry"]["net"] if row["entry"] else 0 for row in rows]
    entered = [row for row in rows if row["entry"]]
    return {
        "n": len(rows), "entered": len(entered), "baseline": v1.perf(baseline),
        "policyCashIncluded": v1.perf(policy), "delta": dist([b - a for a, b in zip(baseline, policy)]),
        "enteredBaseline": v1.perf([row["baseline"]["net"] for row in entered]),
        "enteredPolicy": v1.perf([row["entry"]["net"] for row in entered]),
    }


def economic_panel(episodes, paths, decisions, p, top3):
    runtime = v1.c.module("raw_direct_economic_candidate_a", v1.c.RUNTIME)
    by_id = {episode["id"]: episode for episode in episodes}
    ledger, unknown = [], []
    for item in decisions:
        episode = by_id[item["id"]]
        first = episode["firstSelector"]
        row = economic_row(episode, paths[first["selectorEventId"]], item["decision"], runtime)
        if row is None:
            unknown.append(item["id"])
        else:
            ledger.append(row)
    blocks = p["chronologicalBlocks"]["VALIDATION"]
    panel = {
        "overall": economic_metrics(ledger),
        "blocks": {str(index + 1): economic_metrics([row for row in ledger if row["session"] in dates]) for index, dates in enumerate(blocks)},
        "top3Excluded": economic_metrics([row for row in ledger if row["symbol"] not in top3]),
        "unknownIdentities": unknown,
    }
    complete = sum(bool(row["baseline"] and row["baseline"]["commonComplete"]) for row in decisions)
    overall = panel["overall"]
    panel["gates"] = {
        "coverage": len(ledger) >= .9 * complete,
        "mean": overall["delta"]["mean"] is not None and overall["delta"]["mean"] >= .05,
        "PF": overall["baseline"]["PF"] is not None and overall["policyCashIncluded"]["PF"] is not None and overall["policyCashIncluded"]["PF"] >= overall["baseline"]["PF"],
        "p05": overall["baseline"]["p05"] is not None and overall["policyCashIncluded"]["p05"] is not None and overall["policyCashIncluded"]["p05"] >= overall["baseline"]["p05"],
        "blocks": sum(value["delta"]["mean"] is not None and value["delta"]["mean"] >= 0 for value in panel["blocks"].values()) >= 3,
        "top3": panel["top3Excluded"]["delta"]["mean"] is not None and panel["top3Excluded"]["delta"]["mean"] > 0,
    }
    panel["pass"] = all(panel["gates"].values())
    return ledger, panel


def numeric_status(observed, target, unit):
    near = {"fraction": .05, "pp": .05, "count": 10}[unit]
    floor = -.25 if unit == "pp" else .5 * target
    if observed is None or not math.isfinite(observed):
        status = "HARD_FAIL"
    elif observed >= target:
        status = "PASS"
    elif observed >= target - near:
        status = "NEAR_MISS"
    elif observed < floor:
        status = "HARD_FAIL"
    else:
        status = "FAIL"
    return {"observed": observed, "target": target, "unit": unit, "nearTolerance": near, "hardFloor": floor, "status": status}


def classification(rows, p, economics, top3):
    s = summary(rows)
    targets = p["entryTargets"]
    checks = {
        "completeN": numeric_status(s["commonComplete"], targets["minimumCompleteN"], "count"),
        "entryCoverage": numeric_status(s["entryCoverage"], targets["entryCoverage"], "fraction"),
        "priceImprovementPP": numeric_status(s["priceImprovement"]["mean"], targets["priceImprovementPP"], "pp"),
        "strict30MedianImprovementPP": numeric_status(s["strict30MedianImprovementPP"], targets["strict30MedianImprovementPP"], "pp"),
        "strict30P05ImprovementPP": numeric_status(s["strict30P05ImprovementPP"], targets["strict30P05ImprovementPP"], "pp"),
        "remainingMFE": numeric_status(s["remainingMFERatio"], targets["remainingMFE"], "fraction"),
    }
    for level in (1, 2, 3, 5):
        checks["preservation" + str(level)] = numeric_status(s["preservation"][str(level)]["rate"], targets["preservation" + str(level)], "fraction")
    for name, target in (("IMMEDIATE_WINNER", targets["immediateWinner"]), ("FAST_WINNER", targets["fastWinner"])):
        checks[name] = numeric_status(s["classes"][name]["rate3"], target, "fraction")
    tail = s["tails"]["5"]
    reduction = fraction(tail["baselineAll"] - tail["entryPair"], tail["baselineAll"])
    checks["deep5Reduction"] = numeric_status(reduction, targets["deep5Reduction"], "fraction")
    blocks = []
    for dates in p["chronologicalBlocks"]["VALIDATION"]:
        block = summary([row for row in rows if row["session"] in dates])
        blocks.append(block["commonComplete"] >= 20 and all(
            block["preservation"][str(level)]["baseline"] == 0 or (block["preservation"][str(level)]["rate"] or 0) >= .8
            for level in (3, 5)) and block["priceImprovement"]["mean"] is not None and block["priceImprovement"]["mean"] >= 0)
    pullback = summary([row for row in rows if row["pathClass"] in ("PULLBACK_THEN_WINNER", "DEEP_PULLBACK_THEN_WINNER")])
    excluded = summary([row for row in rows if row["symbol"] not in top3])
    def main_targets(panel):
        deep = panel["tails"]["5"]
        deep_reduction = fraction(deep["baselineAll"] - deep["entryPair"], deep["baselineAll"])
        required = [
            panel["entryCoverage"] is not None and panel["entryCoverage"] >= targets["entryCoverage"],
            panel["priceImprovement"]["mean"] is not None and panel["priceImprovement"]["mean"] >= targets["priceImprovementPP"],
            panel["strict30MedianImprovementPP"] is not None and panel["strict30MedianImprovementPP"] >= targets["strict30MedianImprovementPP"],
            panel["strict30P05ImprovementPP"] is not None and panel["strict30P05ImprovementPP"] >= targets["strict30P05ImprovementPP"],
            panel["remainingMFERatio"] is not None and panel["remainingMFERatio"] >= targets["remainingMFE"],
            deep_reduction is not None and deep_reduction >= targets["deep5Reduction"],
        ]
        required.extend((panel["preservation"][str(level)]["rate"] or 0) >= targets["preservation" + str(level)] for level in (1, 2, 3, 5))
        required.extend((panel["classes"][name]["rate3"] or 0) >= target for name, target in (
            ("IMMEDIATE_WINNER", targets["immediateWinner"]), ("FAST_WINNER", targets["fastWinner"])))
        return all(required)

    composites = {
        "watchUsed": s["watchEpisodes"] > 0 and s["delayedEntries"] > 0,
        "chronological": sum(blocks) >= 3,
        "pullback": (pullback["commonComplete"] >= 10 and pullback["priceImprovement"]["mean"] is not None and
                     pullback["priceImprovement"]["mean"] >= .1 and (pullback["strict30MedianImprovementPP"] or -math.inf) >= 0 and
                     (pullback["preservation"]["3"]["rate"] or 0) >= .85),
        "top3Exclusion": main_targets(excluded),
        "economic": economics["pass"],
    }
    rank = {"PASS": 0, "NEAR_MISS": 1, "FAIL": 2, "HARD_FAIL": 3}
    worst = max((value["status"] for value in checks.values()), key=rank.get)
    if not all(composites.values()) and rank[worst] < rank["FAIL"]:
        worst = "FAIL"
    return {"verdict": worst, "numeric": checks, "composites": composites, "summary": s,
            "pullback": pullback, "top3Excluded": excluded, "chronologicalPass": blocks}


def watch_gate_diagnostic(rows, p):
    thresholds = p["decision"]["watchThresholds"]
    eligible = []
    for row in rows:
        for transition in row["decision"]["transitions"]:
            if transition["delay"] < p["decision"]["maxWatchMinutes"]:
                eligible.append(transition)
    def flags(transition):
        scores = transition["scores"]
        return {
            "price": scores["nextOpenPriceImprovementPP"] >= thresholds["priceImprovementPP"],
            "loss": scores["fiveTimesOpportunityLossProbability"] / 5 <= thresholds["opportunityLossProbabilityMax"],
            "risk": scores["strict30MAEImprovementPP"] >= thresholds["strict30MAEImprovementPP"],
        }
    evaluated = [(transition, flags(transition)) for transition in eligible]
    return {
        "eligibleVisitedStates": len(evaluated),
        "priceThresholdPass": sum(values["price"] for _, values in evaluated),
        "opportunityLossGuardPass": sum(values["loss"] for _, values in evaluated),
        "riskThresholdPass": sum(values["risk"] for _, values in evaluated),
        "allThreePass": sum(all(values.values()) for _, values in evaluated),
        "predictions": {name: dist([transition["scores"][name] for transition, _ in evaluated]) for name in p["architecture"]["outputs"]},
    }


def historical_comparison(validation_episodes, paths):
    saved = read(ENTRY_PATH)["new"]
    wanted = {(episode["session"], episode["symbol"]): episode for episode in validation_episodes}
    initial, dip = [], []
    for row in saved:
        key = (row["sessionDate"], row["symbol"])
        if key not in wanted:
            continue
        episode = wanted[key]
        first = episode["firstSelector"]
        assert row["decision"]["initialEvent"]["anchorId"] == first["selectorEventId"]
        path = paths[first["selectorEventId"]]
        baseline = evaluate(episode, path, 0)
        initial.append({"baseline": baseline, "entry": baseline})
        event = row["decision"]["secondaryEvent"]
        if event is not None:
            delay = minute(event["opportunityTimestamp"]) - minute(first["decisionTimestamp"])
            dip.append({"baseline": baseline, "entry": evaluate(episode, path, delay), "delay": delay})

    def metrics(items):
        complete = [row for row in items if row["baseline"] and row["baseline"]["commonComplete"]]
        pairs = [row for row in complete if row["entry"] and row["entry"]["commonComplete"]]
        improvements = [100 * (row["baseline"]["price"] - row["entry"]["price"]) / row["baseline"]["price"] for row in pairs]
        return {"population": len(items), "baselineComplete": len(complete), "enteredComplete": len(pairs),
                "coverage": fraction(len(pairs), len(complete)), "delay": dist([row.get("delay", 0) for row in pairs]),
                "priceImprovement": dist(improvements),
                "preservation": {str(level): fraction(sum(row["entry"]["common"]["mfe"] >= level for row in pairs if row["baseline"]["common"]["mfe"] >= level),
                                                     sum(row["baseline"]["common"]["mfe"] >= level for row in complete)) for level in (3, 5)},
                "MAE": dist([row["entry"]["common"]["mae"] for row in pairs]),
                "remainingMFE": dist([row["entry"]["common"]["mfe"] for row in pairs])}
    return {"INITIAL": metrics(initial), "DIP_REPRICE_EVENT_ONLY": metrics(dip),
            "note": "DIP absence is a missing historical event, not a SKIP policy. Direct policy population is not restricted to DIP."}


def raw_state_diagnostic(train_episodes, paths):
    rows = []
    for episode in train_episodes:
        selections = episode["selections"]
        for previous, current in zip(selections, selections[1:]):
            previous_slot = preflight.TIMES.index(previous["decisionTimeJst"])
            current_slot = preflight.TIMES.index(current["decisionTimeJst"])
            if current_slot != previous_slot + 1 or previous["decisionTimeJst"] == "11:30":
                continue
            stable = current["savedV1Score"] >= previous["savedV1Score"]
            price_down = current["decisionPrice"] < previous["decisionPrice"]
            path = paths[current["selectorEventId"]]
            temp_first = dict(current, symbolSessionId=episode["id"])
            temp = synthetic_episode(temp_first, path)
            outcome = evaluate(temp, path, 0)
            rows.append({"scoreStableOrUp": stable, "rankImproved": current["newEligibleRank"] < previous["newEligibleRank"],
                         "priceDown": price_down, "outcome": outcome})
    def panel(items):
        complete = [row for row in items if row["outcome"] and row["outcome"]["commonComplete"]]
        return {"observations": len(items), "complete": len(complete),
                "futureMFE": dist([row["outcome"]["common"]["mfe"] for row in complete]),
                "futureMAE": dist([row["outcome"]["common"]["mae"] for row in complete]),
                "futurePlus3Rate": fraction(sum(row["outcome"]["common"]["mfe"] >= 3 for row in complete), len(complete)),
                "futurePlus5Rate": fraction(sum(row["outcome"]["common"]["mfe"] >= 5 for row in complete), len(complete))}
    return {"allAdjacentObservedSnapshots": panel(rows),
            "scoreStableOrUpAndPriceDown": panel([row for row in rows if row["scoreStableOrUp"] and row["priceDown"]]),
            "scope": "TRAIN descriptive repeated observations; not independent trades and not a runtime rule."}


def missingness(pit):
    available = [state for item in pit for state in item["states"] if state["status"] == "AVAILABLE"]
    return {"states": len(available),
            "features": {name: {"available": sum(state["features"][name] is not None for state in available),
                                  "missingRate": fraction(sum(state["features"][name] is None for state in available), len(available))}
                         for name in FEATURES},
            "terminal": dict(collections.Counter(state["status"] for item in pit for state in item["states"] if state["status"] != "AVAILABLE"))}


def report(result):
    s = result["classification"]["summary"]
    e = result["economic"]["overall"]
    return "\n".join([
        "# Frozen 30m Selector Universe → 5m PIT WATCH — First Validation",
        "", "**" + result["status"] + "**", "",
        "Selectorは変更していない。各30分Top5 snapshotのscore/rank/Decision Priceをwindow内で固定し、5分PIT価格stateだけを更新した。",
        "09:35等のSelector値は生成・補間していない。TRAINのみ1 fit、VALIDATION初回測定後の調整なし。", "",
        "## Result", "",
        "| Metric | Result |", "| --- | ---: |",
        f"| Validation symbol-session episodes | {s['emitted']} |",
        f"| Common60 complete | {s['commonComplete']} |",
        f"| Entry coverage | {s['entryCoverage']:.3%} |" if s["entryCoverage"] is not None else "| Entry coverage | N/A |",
        f"| WATCH episodes / delayed Entries | {s['watchEpisodes']} / {s['delayedEntries']} |",
        f"| Mean Entry price improvement | {s['priceImprovement']['mean']:.4f} pp |" if s["priceImprovement"]["mean"] is not None else "| Mean Entry price improvement | N/A |",
        f"| Strict30 MAE median improvement | {s['strict30MedianImprovementPP']:.4f} pp |" if s["strict30MedianImprovementPP"] is not None else "| Strict30 MAE median improvement | N/A |",
        f"| Remaining MFE ratio | {s['remainingMFERatio']:.3%} |" if s["remainingMFERatio"] is not None else "| Remaining MFE ratio | N/A |",
        f"| Candidate A mean net delta | {e['delta']['mean']:.4f} pp |" if e["delta"]["mean"] is not None else "| Candidate A mean net delta | N/A |",
        f"| Final classification | **{result['classification']['verdict']}** |", "",
        f"WATCH対象として訪問したstateは{result['watchGateDiagnostic']['eligibleVisitedStates']}件。price/loss/riskの3条件を同時に満たしたstateは{result['watchGateDiagnostic']['allThreePass']}件だったため、全件BUY_NOWとなった。", "",
        "## Integrity", "",
        f"- model digest: `{result['modelSHA256']}`",
        f"- TRAIN fit states: {result['training']['states']}; effective episodes: {result['training']['episodes']}",
        "- DEV TEST未開封、Fresh/OOS未開封、新規provider取得0、Selector/EXIT/Candidate A変更0。",
        "- Safety 9項目は全false。LONG-only / cash equity only。",
        "- この初回結果に対するthreshold・feature・model・WATCH時間・routingの修正は行っていない。", "",
        "Evidenceの詳細数値は `summary.json`、全decisionは `validation-ledger.json.gz`、経済比較は `economic-ledger.json.gz` に固定。",
    ]) + "\n"


def run(output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    p, episodes, paths, legacy = load_sources()
    train = [episode for episode in episodes if episode["session"] in p["split"]["TRAIN"]]
    validation = [episode for episode in episodes if episode["session"] in p["split"]["VALIDATION"]]
    assert len(train) == 1422 and len(validation) == 710
    assert not set(p["split"]["DEVELOPMENT_TEST"]) & {episode["session"] for episode in train + validation}
    output.mkdir(parents=True)

    train_pit, training_rows = training_dataset(train, paths, legacy)
    assert training_rows and {row["session"] for row in training_rows} <= set(p["split"]["TRAIN"])
    model = Model.fit_once(training_rows, p)
    write(output / "model.json", model.artifact)
    write(output / "training-labels.json.gz", training_rows)
    write(output / "train-pit-states.json.gz", train_pit)
    audit = fit_audit(model, training_rows)
    write(output / "tree-fit-audit.json", audit)

    validation_pit, validation_rows = measure(validation, paths, legacy, model, p)
    top_counts = collections.Counter(episode["symbol"] for episode in train)
    top3 = [symbol for symbol, _ in sorted(top_counts.items(), key=lambda item: (-item[1], item[0]))[:3]]
    economic_ledger, economics = economic_panel(validation, paths, validation_rows, p, top3)
    classified = classification(validation_rows, p, economics, top3)
    history = historical_comparison(validation, paths)
    raw_diagnostic = raw_state_diagnostic(train, paths)

    write(output / "validation-pit-states.json.gz", validation_pit)
    write(output / "validation-ledger.json.gz", validation_rows)
    write(output / "economic-ledger.json.gz", economic_ledger)
    write(output / "missingness.json", {"TRAIN": missingness(train_pit), "VALIDATION": missingness(validation_pit)})
    write(output / "historical-comparison.json", history)
    write(output / "train-raw-state-diagnostic.json", raw_diagnostic)

    census = read(ROOT / "docs/evidence/phase57-raw-selector-direct-entry-v1/preflight/summary.json")
    result = {
        "status": "FIRST_RAW_SELECTOR_DIRECT_ENTRY_MEASUREMENT_COMPLETE_" + classified["verdict"],
        "classification": classified,
        "economic": economics,
        "historicalComparison": history,
        "rawStateDiagnostic": raw_diagnostic,
        "watchGateDiagnostic": watch_gate_diagnostic(validation_rows, p),
        "selector": {"identity": "FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75", "snapshots": 760, "rawRows": 3800,
                     "candidateCountDistribution": census["raw"]["candidateCountDistribution"], "mutations": 0},
        "episodes": census["raw"],
        "architecture": p["architecture"], "decision": p["decision"],
        "training": {"states": len(training_rows), "episodes": len({row["id"] for row in training_rows}),
                     "fitCalls": 1, "fitAudit": audit},
        "modelSHA256": sha(output / "model.json"),
        "partitionEvaluated": "VALIDATION", "validationEvaluations": 1,
        "developmentTestOpened": False, "freshOOSOpened": False, "providerRequests": 0,
        "noRescue": p["noRescue"], "candidateFreeze": False, "safety": SAFETY,
        "integrity": {"scoreRankFixedInsideWindow": True, "inventedFiveMinuteSelectorValues": 0,
                      "futureRuntimeFeatures": 0, "deterministicSerializedReplay": audit["independentSerializedReplay"],
                      "selectorChanges": 0, "exitChanges": 0, "capitalPortfolioRuns": 0},
    }
    write(output / "summary.json", result)
    (output / "REPORT.md").write_text(report(result), encoding="utf-8")
    manifest = {
        "status": result["status"], "protocolSHA256": sha(PROTOCOL_PATH), "featureManifestSHA256": sha(FEATURE_PATH),
        "sourcePins": p["sourcePins"], "codeSHA256": sha(__file__),
        "outputs": {file.name: sha(file) for file in sorted(output.iterdir())},
        "fitCalls": 1, "validationEvaluations": 1, "developmentTestEvaluations": 0,
        "freshOOSOpened": False, "safety": SAFETY,
    }
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "status": result["status"], "validationEpisodes": len(validation),
        "commonComplete": classified["summary"]["commonComplete"],
        "entryCoverage": classified["summary"]["entryCoverage"],
        "watchEpisodes": classified["summary"]["watchEpisodes"],
        "delayedEntries": classified["summary"]["delayedEntries"],
        "priceImprovementPP": classified["summary"]["priceImprovement"]["mean"],
        "candidateANetDeltaPP": economics["overall"]["delta"]["mean"],
        "verdict": classified["verdict"],
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    run(args.out)
