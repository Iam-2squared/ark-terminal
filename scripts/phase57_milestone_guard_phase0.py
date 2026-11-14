"""Precommitted, zero-fit milestone and guard feasibility census.

This module only consumes pinned Development artifacts. It never calls a
provider, evaluates a trading candidate or loads a protected partition.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import statistics
import zipfile
from pathlib import Path

import numpy as np
from scipy.special import ndtri
from scipy.stats import rankdata

from scripts import phase57_wpsd_phase0 as old
from scripts import phase57_exit_continuation_r52 as r52
from scripts import phase57_exit_execution_contract_v1 as clock


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/phase57-milestone-guard-exit"
PRE_SHA = "1b7bc9d41333958e3bb1cc5845d044427f107ebf6824f6a8975ab37eaa58293d"
STEPS = ((1, 2, 0), (2, 3, 1), (3, 5, 2), (5, 10, 3))
FLOORS = {1: 0, 2: 1, 3: 2, 5: 3, 10: 5}
MILESTONES = (1, 2, 3, 5, 10)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, sort_keys=True, ensure_ascii=False,
                                 separators=(",", ":"), allow_nan=False) + "\n").encode())


def number(value):
    return value if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value > 0 else None


def observation(row):
    if not isinstance(row, list) or len(row) != 7:
        return None
    values = [number(row[i]) for i in (1, 2, 3, 4)]
    if any(x is None for x in values):
        return None
    op, hi, lo, cl = values
    if not hi >= max(op, cl) >= lo or lo > min(op, cl):
        return None
    return (op, hi, lo, cl)


def load(r45, replay, audit):
    raw = (EVIDENCE / "CYCLE_PRECOMMIT.json").read_bytes()
    require(sha(raw) == PRE_SHA and
            (EVIDENCE / "CYCLE_PRECOMMIT.sha256").read_text().strip() == PRE_SHA,
            "CYCLE_PRECOMMIT_PIN")
    pre = json.loads(raw)
    require(pre["milestones"]["ladderPct"] == [0, 1, 2, 3, 5, 10] and
            pre["milestones"]["confirmation"] == 2 and
            not any(pre["safety"].values()), "PRECOMMIT_RULE_OR_SAFETY_DRIFT")
    frozen, receipt, ledgers, paired = old.load_fixed(r45, replay, audit)
    require(pre["sourcePins"] == frozen["sourcePins"], "SOURCE_PIN_DRIFT")
    entries, control, funded, context, paths, sessions = old.control_universe(frozen, ledgers)
    with zipfile.ZipFile(replay) as z:
        standalone = json.loads(gzip.decompress(z.read(
            "r54-result/standalone-all-entries.json.gz")))
    upside = {}
    for arm, name in old.ARMS.items():
        rows = standalone[name + "_R50_A_CONTROL"]
        for item in rows:
            key = (arm, item["entryId"])
            require(key in entries and key not in upside and
                    item["session"] == entries[key]["session"], "UPSIDE_ID_DRIFT")
            value = item["evaluatorOnlyPostEntryUpsidePct"]
            require(value is None or isinstance(value, (int, float)) and math.isfinite(value),
                    "UPSIDE_INVALID")
            upside[key] = value
    require(set(upside) == set(entries), "UPSIDE_CENSUS_DRIFT")
    return pre, entries, control, funded, paths, sessions, upside


def available_rows(entry, cutoff, path):
    """Use only bars owned through Control decision; missing stays missing."""
    starts = [m for m in clock.continuous_minutes(entry["session"])
              if entry["entryMinute"] <= m and m + 1 <= cutoff]
    return [(m + 1, observation(path.get(m))) for m in starts]


def reached_at(rows, entry_price, milestone):
    prior_missing = False
    for i, (_, bar) in enumerate(rows):
        if bar is None:
            prior_missing = True
        elif bar[1] >= entry_price * (1 + milestone / 100):
            return ("MISSING_PRIOR" if prior_missing else "REACHED", i)
    return ("MISSING" if prior_missing else "CONTROL_TERMINAL_FIRST", None)


def passage(rows, entry_price, reached, prior, nxt, floor):
    status, origin = reached[prior]
    if status != "REACHED":
        return {"status": status, "at": None, "twoCheckpointUnrecovered": None,
                "recoveredAfterBreach": None, "nextReachedAfterBreach": None,
                "oneCheckpointNoise": None}
    for i in range(origin, len(rows)):
        _, bar = rows[i]
        if bar is None:
            return {"status": "MISSING", "at": i, "twoCheckpointUnrecovered": None,
                    "recoveredAfterBreach": None, "nextReachedAfterBreach": None,
                    "oneCheckpointNoise": None}
        lower = bar[2] < entry_price * (1 + floor / 100)
        upper = nxt is not None and bar[1] >= entry_price * (1 + nxt / 100)
        if lower and (upper or i == origin):
            state = "AMBIGUOUS_SAME_BAR"
        elif upper:
            state = "UPPER_FIRST"
        elif lower:
            state = "FLOOR_FIRST"
        else:
            continue
        first = {"status": state, "at": i, "twoCheckpointUnrecovered": None,
                 "recoveredAfterBreach": None, "nextReachedAfterBreach": None,
                 "oneCheckpointNoise": i - origin <= 1 if state == "FLOOR_FIRST" else None}
        if state == "FLOOR_FIRST":
            closes = [rows[k][1][3] if rows[k][1] is not None else None
                      for k in (i, i + 1) if k < len(rows)]
            first["twoCheckpointUnrecovered"] = (len(closes) == 2 and all(
                x is not None and x < entry_price * (1 + floor / 100) for x in closes))
            following = [bar for _, bar in rows[i + 1:]]
            first["recoveredAfterBreach"] = any(
                b is not None and b[3] >= entry_price * (1 + floor / 100)
                for b in following)
            first["nextReachedAfterBreach"] = (None if nxt is None else any(
                b is not None and b[1] >= entry_price * (1 + nxt / 100)
                for b in following))
        return first
    return {"status": "CONTROL_TERMINAL_FIRST", "at": None,
            "twoCheckpointUnrecovered": None, "recoveredAfterBreach": None,
            "nextReachedAfterBreach": None, "oneCheckpointNoise": None}


def alerts(rows, day, entry_price, path):
    """Guard state without policy replay: find first breach anchors and 30m teacher."""
    highest, consecutive, stopped = 0, 0, False
    out = []
    minutes = clock.continuous_minutes(day)
    index = {m: j for j, m in enumerate(minutes)}
    for now, bar in rows:
        if stopped:
            break
        if bar is None:
            consecutive = 0  # gap cannot confirm a consecutive closed checkpoint
            continue
        gross_high = 100 * (bar[1] / entry_price - 1)
        for milestone in MILESTONES:
            if gross_high >= milestone:
                highest = max(highest, milestone)
        if highest == 0:
            continue
        floor = FLOORS[highest]
        close_ret = 100 * (bar[3] / entry_price - 1)
        if close_ret >= floor:
            consecutive = 0
            continue
        consecutive += 1
        if consecutive >= 2:
            stopped = True
            continue
        j = index[now - 1]
        target = j + 30
        endpoint = (None if target >= len(minutes) else
                    observation(path.get(minutes[target])) )
        y = None if endpoint is None else int(endpoint[3] >= entry_price * (1 + floor / 100))
        fraction = j / max(1, len(minutes) - 1)
        timing = "EARLY" if fraction < 1/3 else "MID" if fraction < 2/3 else "LATE"
        out.append({"now": now, "highest": highest, "floor": floor, "label": y,
                    "timing": timing, "reason": ("EXACT_ENDPOINT_MISSING_OR_SESSION_END"
                    if y is None else None)})
    return out


def roc(y, score):
    y, score = np.asarray(y, dtype=np.int8), np.asarray(score)
    n = int(y.sum()); m = len(y) - n
    if n == 0 or m == 0:
        return None
    return float((rankdata(score, method="average")[y == 1].sum() - n * (n + 1) / 2) / (n * m))


def estimate_power(labels, seed, repetitions, bootstraps):
    """The predeclared geometry-only AUC=.60 session simulation."""
    labels = sorted(labels)
    y = np.array([z[1] for z in labels], dtype=np.int8)
    ses = [z[0] for z in labels]
    unique = sorted(set(ses))
    groups = [np.array([i for i, s in enumerate(ses) if s == day], dtype=np.int32)
              for day in unique]
    if not (y.any() and (1-y).any()):
        return {"power": None, "reason": "SINGLE_CLASS"}
    rng = np.random.default_rng(seed)
    delta = float(np.sqrt(2) * ndtri(0.6))
    group_id = np.empty(len(y), dtype=np.int32)
    for j, ids in enumerate(groups):
        group_id[ids] = j
    positive = np.flatnonzero(y == 1)
    negative = np.flatnonzero(y == 0)
    pair_group = (group_id[positive, None] * len(groups)
                  + group_id[None, negative]).ravel()
    positive_by_group = np.bincount(group_id[positive], minlength=len(groups))
    negative_by_group = np.bincount(group_id[negative], minlength=len(groups))
    detected = valid = 0
    for _ in range(repetitions):
        effect = rng.normal(size=len(groups)) * .25
        score = delta*y + rng.normal(size=len(y))
        for j, ids in enumerate(groups):
            score[ids] += effect[j]
        # A session resample repeats whole session blocks. The weighted
        # Mann-Whitney numerator can therefore be computed from fixed
        # pairwise wins, without sorting all repeated Entry rows 199 times.
        a = score[positive, None]
        b = score[None, negative]
        win = (a > b).astype(np.float64) + .5 * (a == b)
        pair_wins = np.bincount(pair_group, weights=win.ravel(),
                                 minlength=len(groups)**2).reshape(len(groups), len(groups))
        draws = []
        for _ in range(bootstraps):
            sample = rng.integers(0, len(groups), len(groups))
            weights = np.bincount(sample, minlength=len(groups))
            npos = weights @ positive_by_group
            nneg = weights @ negative_by_group
            if npos and nneg:
                draws.append(float(weights @ pair_wins @ weights / (npos*nneg)))
        if len(draws) >= math.ceil(.95 * bootstraps):
            valid += 1
            detected += bool(np.quantile(draws, .025) > .5)
    return {"power": float(detected/repetitions), "detected": int(detected),
            "validSimulations": valid, "repetitions": repetitions,
            "bootstrapPerRep": bootstraps, "delta": delta}


def count_power(rows, requirement, settings, seed):
    known = [r for r in rows if r["label"] is not None]
    pos = [r for r in known if r["label"] == 1]
    neg = [r for r in known if r["label"] == 0]
    counts = {"positiveN": len(pos), "negativeN": len(neg),
              "positiveSessions": len({r["session"] for r in pos}),
              "negativeSessions": len({r["session"] for r in neg}),
              "knownN": len(known), "unknownN": len(rows)-len(known)}
    prelim = (counts["positiveN"] >= requirement["minPositiveN"] and
              counts["negativeN"] >= requirement["minNegativeN"] and
              counts["positiveSessions"] >= requirement["minPositiveSessions"] and
              counts["negativeSessions"] >= requirement["minNegativeSessions"])
    if not prelim:
        return {**counts, "power": None, "status": "COUNT_SESSION_NO_GO"}
    sim = estimate_power([(r["session"], r["label"]) for r in known], seed,
                         settings["repetitions"], settings["bootstrapPerRep"])
    return {**counts, **sim, "status": ("PASS" if sim["power"] is not None and
            sim["power"] >= settings["minPower"] else "POWER_NO_GO")}


def evaluate(args):
    pre, entries, control, funded, paths, sessions, upside = load(
        args.r45, args.replay, args.audit)
    phase_a = {"schema": "phase57-mg-phase0a-v1", "precommitSha256": PRE_SHA,
               "sourcePins": pre["sourcePins"], "counts": {}, "milestones": {},
               "transitions": {}, "survival": {}, "potentialPower": {},
               "exposure": pre["exposure"], "safety": pre["safety"]}
    phase_b = {"schema": "phase57-mg-phase0b-v1", "precommitSha256": PRE_SHA,
               "buckets": {}, "trajectory": {}, "postBreach": {},
               "winnerFeasibility": {}, "winnerFeasibilityByArm": {},
               "exposure": pre["exposure"], "safety": pre["safety"]}
    records, survival = [], []
    for key, entry in sorted(entries.items()):
        arm = old.ARMS[key[0]]
        day = entry["session"]
        rows = available_rows(entry, control[key], paths[entry["opportunity"]])
        price = entry["effectiveEntryPrice"]
        reached = {k: reached_at(rows, price, k) for k in MILESTONES}
        transitions = {f"{m}->{n}": passage(rows, price, reached, m, n, floor)
                       for m, n, floor in STEPS}
        transitions["10->floor5"] = passage(rows, price, reached, 10, None, 5)
        reach_pct = upside[key]
        bucket = ("UNKNOWN" if reach_pct is None else "<1" if reach_pct < 1 else
                  "1-2" if reach_pct < 2 else "2-3" if reach_pct < 3 else
                  "3-5" if reach_pct < 5 else "5-10" if reach_pct < 10 else ">=10")
        alerts_here = alerts(rows, day, price, paths[entry["opportunity"]])
        for x in alerts_here:
            survival.append({"arm": arm, "entryId": key[1], "session": day, **x})
        highs = [100*(bar[1]/price-1) for _,bar in rows if bar is not None]
        closes = [100*(bar[3]/price-1) for _,bar in rows if bar is not None]
        # This is a descriptive observed Control prefix, never an imputed exit.
        giveback = max(highs)-closes[-1] if highs and closes and all(
            bar is not None for _,bar in rows) else None
        records.append({"arm": arm, "entryId": key[1], "session": day,
                        "funded": key in funded, "upsidePct": reach_pct,
                        "bucket": bucket, "reach": reached,
                        "transitions": transitions,
                        "alertsN": len(alerts_here), "controlPrefixGivebackPp": giveback,
                        "observedBars": len(rows),
                        "missingBars": sum(bar is None for _,bar in rows)})
    require(len(records) == 1614 and sum(x["funded"] for x in records) == 111,
            "FROZEN_ENTRY_AND_FUNDED_CENSUS")
    phase_a["bySession"] = {}
    for day in sessions:
        phase_a["bySession"][day] = {}
        for arm in ("IM", "R1"):
            subset = [r for r in records if r["session"] == day and r["arm"] == arm]
            phase_a["bySession"][day][arm] = {
                "entries": len(subset),
                **{f"upsideGe{k}": sum(r["upsidePct"] is not None and
                      r["upsidePct"] >= k for r in subset) for k in MILESTONES},
                **{f"observedReach{k}": sum(r["reach"][k][0] == "REACHED"
                      for r in subset) for k in MILESTONES},
                "missingUpside": sum(r["upsidePct"] is None for r in subset)}
    for arm in ("IM", "R1", "combined"):
        subset = [r for r in records if arm == "combined" or r["arm"] == arm]
        phase_a["counts"][arm] = {"entries": len(subset), "sessions": len({r["session"] for r in subset}),
              "unknownUpside": sum(r["upsidePct"] is None for r in subset),
              **{f"ge{k}": sum(r["upsidePct"] is not None and r["upsidePct"] >= k
                              for r in subset) for k in MILESTONES}}
        phase_a["milestones"][arm] = {str(k): collections.Counter(
            r["reach"][k][0] for r in subset) for k in MILESTONES}
        phase_a["transitions"][arm] = {str(step): dict(collections.Counter(
            r["transitions"][step]["status"] for r in subset)) for step in
            ("1->2", "2->3", "3->5", "5->10", "10->floor5")}
        applicable = [x for x in survival if arm == "combined" or x["arm"] == arm]
        phase_a["survival"][arm] = {"alerts": len(applicable),
             "known": sum(x["label"] is not None for x in applicable),
             "positive": sum(x["label"] == 1 for x in applicable),
             "negative": sum(x["label"] == 0 for x in applicable),
             "unknown": sum(x["label"] is None for x in applicable),
             "byTiming": {t:dict(collections.Counter(
                 "UNKNOWN" if x["label"] is None else "POS" if x["label"] else "NEG"
                 for x in applicable if x["timing"] == t)) for t in ("EARLY","MID","LATE")},
             "byMilestone": {str(m):dict(collections.Counter(
                 "UNKNOWN" if x["label"] is None else "POS" if x["label"] else "NEG"
                 for x in applicable if x["highest"] == m)) for m in MILESTONES}}
    phase_a["survival"]["bySession"] = {s: dict(collections.Counter(
        "UNKNOWN" if x["label"] is None else "POS" if x["label"] else "NEG"
        for x in survival if x["session"] == s)) for s in sessions}
    pp = pre["power"]
    for k in (5, 10):
        power_rows = [{"session":r["session"],"label":None if r["upsidePct"] is None
                       else int(r["upsidePct"] >= k)} for r in records]
        phase_a["potentialPower"][str(k)] = count_power(power_rows, pp, pp, pp["seed"]+k)
    surv_power = count_power(survival, pp, pp, pp["seed"]+30)
    coverage = ((surv_power["knownN"] / len(survival)) if survival else 0)
    surv_power["exactCoverage"] = coverage
    if coverage < pp["survivalExactEndpointCoverageMin"]:
        surv_power["status"] = "SURVIVAL_POWER_NO_GO_COVERAGE"
    phase_a["survivalPower"] = surv_power
    for bucket in ("<1", "1-2", "2-3", "3-5", "5-10", ">=10", "UNKNOWN"):
        group = [r for r in records if r["bucket"] == bucket]
        values = [r["controlPrefixGivebackPp"] for r in group
                  if r["controlPrefixGivebackPp"] is not None]
        phase_b["buckets"][bucket] = {"entries":len(group),
             "IM":sum(r["arm"]=="IM" for r in group),
             "R1":sum(r["arm"]=="R1" for r in group),
             "milestoneReachedWithinControl": {str(m):sum(r["reach"][m][0]=="REACHED"
                                                  for r in group) for m in MILESTONES},
             "knownControlPrefixGivebackN":len(values),
             "medianControlPrefixGivebackPp": statistics.median(values) if values else None,
             "maxControlPrefixGivebackPp": max(values) if values else None}
    for arm in ("IM", "R1", "combined"):
        phase_b["trajectory"][arm] = {}
        phase_b["postBreach"][arm] = {}
        for bucket in ("<1", "1-2", "2-3", "3-5", "5-10", ">=10", "UNKNOWN"):
            subset = [r for r in records if r["bucket"] == bucket and
                      (arm == "combined" or r["arm"] == arm)]
            givebacks = [r["controlPrefixGivebackPp"] for r in subset
                         if r["controlPrefixGivebackPp"] is not None]
            phase_b["trajectory"][arm][bucket] = {
                "entries": len(subset),
                "milestones": {str(k): {"reached": sum(r["reach"][k][0] == "REACHED"
                                for r in subset),
                    "medianActiveMinutesToReach": statistics.median(
                        r["reach"][k][1]+1 for r in subset
                        if r["reach"][k][0] == "REACHED")
                    if any(r["reach"][k][0] == "REACHED" for r in subset) else None}
                    for k in MILESTONES},
                "transitions": {name:dict(collections.Counter(
                    r["transitions"][name]["status"] for r in subset))
                    for name in ("1->2","2->3","3->5","5->10","10->floor5")},
                "givebackKnownN":len(givebacks),
                "givebackMeanPp":statistics.mean(givebacks) if givebacks else None,
                "givebackMedianPp":statistics.median(givebacks) if givebacks else None,
                "givebackQ75Pp":float(np.quantile(givebacks,.75)) if givebacks else None}
        for name in ("1->2","2->3","3->5","5->10","10->floor5"):
            group = [r["transitions"][name] for r in records
                     if arm == "combined" or r["arm"] == arm]
            breached = [x for x in group if x["status"] == "FLOOR_FIRST"]
            phase_b["postBreach"][arm][name] = {
                "floorFirstN":len(breached),
                "recoveredN":sum(x["recoveredAfterBreach"] is True for x in breached),
                "nextMilestoneAfterBreachN":sum(x["nextReachedAfterBreach"] is True for x in breached),
                "twoCheckpointUnrecoveredN":sum(x["twoCheckpointUnrecovered"] is True for x in breached),
                "oneCheckpointNoiseN":sum(x["oneCheckpointNoise"] is True for x in breached)}
    for threshold in (5, 10):
        eligible = [r for r in records if r["upsidePct"] is not None and r["upsidePct"] >= threshold]
        names = [f"{m}->{n}" for m,n,_ in STEPS if n <= threshold]
        classified = []
        for r in eligible:
            states = [r["transitions"][name]["status"] for name in names]
            if "FLOOR_FIRST" in states:
                classification = "FLOOR_FIRST"
            elif all(s == "UPPER_FIRST" for s in states):
                classification = "UPPER_FIRST_ALL"
            else:
                classification = "UNKNOWN_OR_CONTROL_TERMINAL"
            classified.append((r, classification))
        known = [(r,s) for r,s in classified if s != "UNKNOWN_OR_CONTROL_TERMINAL"]
        breach = sum(s == "FLOOR_FIRST" for _,s in known)
        sessions_known = sorted({r["session"] for r,_ in known})
        session_rates = [sum(s == "FLOOR_FIRST" for r,s in known if r["session"]==day) /
                         sum(r["session"]==day for r,_ in known) for day in sessions_known]
        exact = len(known)/len(eligible) if eligible else 0
        stats = {"totalWinnerEntries":len(eligible), "exactKnownEntries":len(known),
                 "exactKnownCoverage":exact,"knownSessions":len(sessions_known),
                 "floorFirstEntries":breach,"entryWeightedFloorFirstRate":breach/len(known) if known else None,
                 "sessionWeightedFloorFirstRate":statistics.mean(session_rates) if session_rates else None,
                 "unknownOrControlTerminal":len(eligible)-len(known),
                 "relevantTransitions":names,
                 "twoCheckpointUnrecoveredN":sum(any(r["transitions"][name]["twoCheckpointUnrecovered"]
                    is True for name in names) for r,s in known if s == "FLOOR_FIRST")}
        measurable = exact >= .80 and len(known) >= 20 and len(sessions_known) >= 8
        stats["status"] = ("GUARD_FEASIBILITY_UNMEASURABLE" if not measurable else
             "GUARD_FEASIBILITY_NO_GO" if stats["entryWeightedFloorFirstRate"] > .5 or
             stats["sessionWeightedFloorFirstRate"] > .5 else "PASS")
        phase_b["winnerFeasibility"][str(threshold)] = stats
        by_arm = {}
        for arm in ("IM", "R1"):
            cohort = [(r,s) for r,s in classified if r["arm"] == arm]
            known_arm = [(r,s) for r,s in cohort if s != "UNKNOWN_OR_CONTROL_TERMINAL"]
            breach_arm = sum(s == "FLOOR_FIRST" for _,s in known_arm)
            day_rates = [sum(s == "FLOOR_FIRST" for r,s in known_arm if r["session"] == day) /
                         sum(r["session"] == day for r,_ in known_arm)
                         for day in sorted({r["session"] for r,_ in known_arm})]
            by_arm[arm] = {"total":len(cohort),"known":len(known_arm),
                           "floorFirst":breach_arm,
                           "entryWeighted":breach_arm/len(known_arm) if known_arm else None,
                           "sessionWeighted":statistics.mean(day_rates) if day_rates else None}
        phase_b["winnerFeasibilityByArm"][str(threshold)] = by_arm
    phase_b["guardGate"] = ("PASS" if all(x["status"]=="PASS" for x in
          phase_b["winnerFeasibility"].values()) else
          "GUARD_FEASIBILITY_UNMEASURABLE" if any(x["status"]=="GUARD_FEASIBILITY_UNMEASURABLE"
          for x in phase_b["winnerFeasibility"].values()) else "GUARD_FEASIBILITY_NO_GO")
    # A compact per-Entry trace is retained locally for independent checking.
    # GitHub receives the aggregate and its hash; regeneration is deterministic.
    rows_bytes = gzip.compress(("".join(json.dumps(r, sort_keys=True,
        separators=(",", ":"), allow_nan=False)+"\n" for r in records)).encode(), mtime=0)
    (EVIDENCE/"PHASE0_B_ENTRY_ROWS.jsonl.gz").write_bytes(rows_bytes)
    phase_b["entryRowsSha256"] = sha(rows_bytes)
    phase_b["entryRowsN"] = len(records)
    dump(EVIDENCE/"PHASE0_A.json", phase_a)
    dump(EVIDENCE/"PHASE0_B.json", phase_b)
    print(json.dumps({"precommitSha256":PRE_SHA,"phaseA":sha((EVIDENCE/"PHASE0_A.json").read_bytes()),
          "phaseB":sha((EVIDENCE/"PHASE0_B.json").read_bytes()),
          "counts":phase_a["counts"],"potentialPower":phase_a["potentialPower"],
          "survivalPower":phase_a["survivalPower"],"guardGate":phase_b["guardGate"],
          "winnerFeasibility":phase_b["winnerFeasibility"]}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--r45", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    evaluate(parser.parse_args())
