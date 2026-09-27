"""R54 zero-fit A/B/C price-label geometry; futures stay evaluator/trainer only.

The old frozen R45/R52 arrays and the allowlist-first R52 raw reader are reused.
No protected partitions, provider calls, selector, Entry, or Capital mutation.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from scripts import phase57_exit_execution_contract_v1 as execution

HORIZONS = (0, 1, 5, 15, 30, 60, "EOD")
FAMILIES = ("A", "D", "HIGH", "LOW")
MIN_TRAIN_ROWS = 500
MIN_HORIZON_ROWS = 100
MIN_HORIZON_ENTRY = 10
MIN_HORIZON_SESSIONS = 3
DENIED_RUNTIME = ("futureHigh", "futureLow", "futureOPEN", "futureMFE", "futureMAE",
                  "label", "labelAvailability", "finalPnL", "capture", "oracleExit",
                  "futureMarkAvailability", "postEntryUpside", "futureEntry")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                       allow_nan=False) + "\n").encode()


def split_manifest(r52_protocol):
    out = []
    for fold in r52_protocol["folds"]:
        train = fold["train"]
        if len(train) < 8:
            raise ValueError("INSUFFICIENT_INNER_TRAIN_SESSIONS")
        fit, inner_purge, calibration = train[:-7], train[-7:-5], train[-5:]
        if not (max(fit) < min(inner_purge) <= max(inner_purge) < min(calibration)
                <= max(calibration) < min(fold["purge"]) < min(fold["score"])):
            raise ValueError("TEMPORAL_ORDER_OR_PURGE")
        out.append({"fold": fold["fold"], "fit": fit, "innerPurge": inner_purge,
                    "calibration": calibration, "outerPurge": fold["purge"],
                    "score": fold["score"]})
    return out


def planned_targets(day, now):
    """Calendar only; neither label availability nor price looks ahead at runtime."""
    starts = execution.continuous_minutes(day)
    ends = tuple(x + 1 for x in starts)
    if now not in ends or now == 925:
        return {}
    k = ends.index(now)
    out = {}
    for h in HORIZONS:
        if h == "EOD":
            target_now = 925
        else:
            if k + h >= len(ends):
                continue
            target_now = ends[k + h]
            if h != 0 and target_now == 925:
                # The EOD single-price reference is canonical, not repeated.
                continue
        out[h] = target_now
    return out


def _price(row, index):
    if not isinstance(row, (tuple, list)) or len(row) != 7:
        return None
    v = row[index]
    return float(v) if isinstance(v, (float, int)) and math.isfinite(v) and v > 0 else None


def endpoint_reference(day, target_now, path):
    if target_now == 925:
        row = path.get(930)
        if row is None:
            return None, "TERMINAL_AUCTION_MISSING", 930
        ref = execution.terminal_execution_reference([row])
        return ref["price"], ref["status"], 930
    minute = execution.next_execution_start(day, target_now)
    if minute is None:
        return None, "NO_SCHEDULED_OPEN", None
    return _price(path.get(minute), 1), ("AVAILABLE" if minute in path else
                                               "EXACT_OPEN_MISSING"), minute


def interval_extrema(day, now, target_now, path, endpoint):
    """Only complete future scheduled bars, endpoint OPEN, and EOD auction."""
    occupied = tuple(m for m in execution.continuous_minutes(day)
                     if now <= m < target_now)
    points = [endpoint]
    for minute in occupied:
        row = path.get(minute)
        if row is None:
            return None, None, "INTERIOR_BAR_MISSING"
        if not all(_price(row, i) is not None for i in (1, 2, 3, 4)):
            return None, None, "INTERIOR_BAR_INVALID"
        if not (row[2] >= max(row[1], row[4]) and row[3] <= min(row[1], row[4])):
            return None, None, "INTERIOR_BAR_OHLC_INVALID"
        points.extend((float(row[2]), float(row[3])))
    return max(points), min(points), "AVAILABLE"


def labels_for_checkpoint(day, now, raw_path, fresh):
    """Return training targets/masks; this result must never be passed to runtime."""
    path = raw_path
    price_now = _price(path.get(now - 1), 4)
    if not fresh or price_now is None:
        return {}, "NOW_PRICE_NOT_FRESH"
    targets = {}
    tmap = planned_targets(day, now)
    e0, _, _ = endpoint_reference(day, now, path)
    for h, target_now in tmap.items():
        e_h, availability, ref_minute = endpoint_reference(day, target_now, path)
        rec = {"targetNow": target_now, "referenceMinute": ref_minute,
               "A": None, "D": None, "HIGH": None, "LOW": None,
               "reasonA": availability, "reasonD": "H0_IS_EXCLUDED" if h == 0 else availability,
               "reasonC": availability}
        if e_h is not None:
            rec["A"] = 100 * (e_h / price_now - 1)
            rec["reasonA"] = "AVAILABLE"
            if h != 0:
                if e0 is None:
                    rec["reasonD"] = "EXACT_E0_OPEN_MISSING"
                else:
                    # Same-position, same-quantity sell fee applied once per hypothetical sale.
                    rec["D"] = 100 * ((e_h - e0) * (1 - .0005)) / price_now
                    rec["reasonD"] = "AVAILABLE"
                hi, lo, reason = interval_extrema(day, now, target_now, path, e_h)
                if reason == "AVAILABLE":
                    rec["HIGH"] = 100 * (hi / price_now - 1)
                    rec["LOW"] = 100 * (lo / price_now - 1)
                rec["reasonC"] = reason
        targets[h] = rec
    return targets, "AVAILABLE"


def category_schema(legacy_maps):
    """Fixed declared enum, never derive a vocabulary by scanning scored rows."""
    from scripts.phase57_exit_gen3_facts_r45 import SIGNALS, STATES
    enum = sorted(STATES) + ["UNKNOWN"]
    tri = ["FALSE", "TRUE", "UNKNOWN"]
    out = {}
    for name, observed in legacy_maps.items():
        if name in ("entryState.state", "currentState.state"):
            allowed = enum
        elif name == "entryToCurrentState":
            # The R45 encoded transition must be a finite cross-product of states.
            allowed = [json.dumps([a, b], separators=(",", ":"))
                       for a in enum for b in enum] + ["UNKNOWN"]
        elif name.startswith("signal."):
            allowed = tri
        else:
            raise ValueError("UNAPPROVED_CATEGORY:" + name)
        # Validate source representation against the *declared* universe.
        unexpected = sorted(set(observed) - set(allowed))
        if unexpected:
            raise ValueError("UNDECLARED_CATEGORY:" + name + ":" + str(unexpected[:8]))
        out[name] = {"values": allowed, "sourceCodes": observed,
                     "unknownCode": observed.get("UNKNOWN")}
    return out


def verify_feature_schema(receipt, arrays, maps):
    from scripts import phase57_exit_continuation_r52 as r52
    cats = category_schema(maps)
    numeric = list(r52.CORE_NUMERIC + r52.EXTRA_NUMERIC)
    pattern = list(receipt["patternColumns"])
    if len(pattern) != 187 or len(pattern) != len(set(pattern)):
        raise ValueError("PATTERN187_SOURCE_SCHEMA")
    if not set(numeric) <= set(receipt["numericColumns"]):
        raise ValueError("SOURCE_NUMERIC_SCHEMA")
    if not set(cats) <= set(receipt["categoricalColumns"]):
        raise ValueError("SOURCE_CATEGORICAL_SCHEMA")
    if len(arrays["numeric"]) != 656247:
        raise ValueError("FROZEN_CHECKPOINT_COUNT_CHANGED")
    # Prefix/peak/missingness remains optional NaN, never silently zero.
    return {"numeric": numeric, "categorical": cats, "pattern187": pattern,
            "deniedRuntime": list(DENIED_RUNTIME),
            "nowKnownAt": "R45 completed closed-bar end proxy <= decisionNow",
            "publicationLatencyCertified": False,
            "ablationSRemove": [x for x in numeric if x.startswith(("state", "history.5.signal", "history.5.state"))]
                + [x for x in cats if x.startswith(("entryState", "currentState", "entryToCurrentState", "signal."))],
            "ablationPRemove": pattern,
            "oneHotVocabularySource": "FIXED_R45_STATE_AND_SIGNAL_DECLARED_ENUMS"}


def readiness(source: Path, out: Path):
    """Zero-fit census: label availability only, never target performance."""
    from scripts import phase57_exit_continuation_r52 as r52
    from scripts import phase57_development_integrated_v0 as v0
    p = r52.protocol()
    receipt, arrays, identities, groups = r52.load_checkpoints(source)
    entries = r52.all_frozen_entries()
    if set(groups) != set(entries):
        raise ValueError("FROZEN_ENTRY_GROUP_MISMATCH")
    raw = r52.projected_raw(entries)
    maps = json.loads((source / "data/categorical-representation.json").read_text())["maps"]
    schema = verify_feature_schema(receipt, arrays, maps)
    folds = split_manifest(p)
    n = len(identities)
    output = {family: np.full((n, len(HORIZONS)), np.nan, np.float32)
              for family in FAMILIES}
    known_at = np.full((n, len(HORIZONS)), -1, np.int16)
    counters = collections.Counter()
    mask_counts = collections.Counter()
    missing = []
    for (arm, eid), sequence in groups.items():
        entry = entries[(arm, eid)]
        day = entry["session"]
        path = raw[entry["opportunity"]]
        for i in sequence:
            now = identities[i]["now"]
            if identities[i]["session"] != day or identities[i]["arm"] != arm:
                raise ValueError("SOURCE_ROW_JOIN")
            result, reason = labels_for_checkpoint(day, now, path, bool(arrays["fresh"][i]))
            if reason != "AVAILABLE":
                counters["NOW|" + reason] += 1
                continue
            for hi, (h, row) in enumerate((h, result[h]) for h in HORIZONS if h in result):
                j = HORIZONS.index(h)
                for family in FAMILIES:
                    if row[family] is None:
                        key = "reasonC" if family in ("HIGH", "LOW") else "reason" + family
                        counters[family + "|" + str(h) + "|" + row[key]] += 1
                        if row[key] in ("EXACT_OPEN_MISSING", "TERMINAL_AUCTION_MISSING") and day in p["sessions"]:
                            missing.append({"symbol": eid.split("|")[1], "session": day,
                                "neededTimestamp": row["referenceMinute"], "field": "exact OPEN/auction",
                                "sourceAvailability": "NOT_IN_ALLOWLISTED_ORIGINAL",
                                "knownAt": "UNKNOWN", "purpose": "TEACHER_OR_FUTURE_FILL",
                                "approvalNeeded": True})
                        continue
                    output[family][i, j] = row[family]
                    mask_counts[family + "|" + str(h) + "|" + arm] += 1
                known_at[i, j] = row["referenceMinute"] if row["referenceMinute"] is not None else -1
    # Information exposure firewall: do not summarize or print numerical targets.
    row_arm = np.asarray([x["arm"] for x in identities]);row_day=np.asarray([x["session"] for x in identities]);
    row_eid=np.asarray([x["entryId"] for x in identities]);
    support = []
    for fold in folds:
        for arm in v0.ARMS:
            for part in ("fit", "calibration", "score"):
                base = (row_arm == arm) & np.isin(row_day, fold[part])
                for family in FAMILIES:
                    mask = np.isfinite(output[family]) & base[:, None]
                    uniq = np.any(mask, axis=1)
                    summary = {"fold": fold["fold"], "arm": arm, "partition": part,
                               "family": family, "matureRows": int(mask.sum()),
                               "uniqueCheckpointRows": int(uniq.sum()),
                               "entryIds": int(len(set(row_eid[uniq]))),
                               "sessions": int(len(set(row_day[uniq]))), "horizons": {}}
                    for h in HORIZONS:
                        j=HORIZONS.index(h); q=mask[:,j]
                        summary["horizons"][str(h)]={"matureLabels": int(q.sum()),
                          "entryIds": int(len(set(row_eid[q]))),
                          "sessions": int(len(set(row_day[q])))}
                    support.append(summary)
    blocking=[]
    for x in support:
        if x["partition"] != "fit":
            continue
        if x["matureRows"] < MIN_TRAIN_ROWS:
            blocking.append("TARGET_FAMILY_SUPPORT:"+str((x["fold"],x["arm"],x["family"])))
        if x["family"]=="D":
            for h in (1,5):
                cell=x["horizons"][str(h)]
                if (cell["matureLabels"] < MIN_HORIZON_ROWS or
                    cell["entryIds"] < MIN_HORIZON_ENTRY or cell["sessions"] < MIN_HORIZON_SESSIONS):
                    blocking.append("CORE_D_SUPPORT:"+str((x["fold"],x["arm"],h)))
    size = {"baseRows": n, "numericColumns": len(schema["numeric"]),
            "patternColumns": len(schema["pattern187"]),
            "oneHotDeclaredColumns": sum(len(c["values"]) for c in schema["categorical"].values()),
            "maxHorizonReplication": len(HORIZONS), "maxEstimatorFits": 176,
            "oneHeadAtATime": True, "fullMatrixSingleAllocationProhibited": True}
    if size["oneHotDeclaredColumns"]>1000:
        blocking.append("DECLARED_ONE_HOT_MATRIX_UNSUPPORTED")
    out.mkdir(parents=True, exist_ok=False)
    (out / "source-pins.json").write_bytes(canonical({"basisProtocolSha256":sha(r52.PRECOMMIT),
         "featureSha256":r52.FEATURE_SHA,"identitySha256":r52.IDENTITY_SHA,
         "rawSha256":v0.RAW_HASH,"sourceReceiptSha256":sha(source/"data/data-receipt.json"),
         "categoricalMapSha256":sha(source/"data/categorical-representation.json")}))
    (out / "feature-schema.json").write_bytes(canonical(schema))
    (out / "fold-manifest.json").write_bytes(canonical(folds))
    (out / "train-support.json").write_bytes(canonical(support))
    unique_missing = {tuple(v.items()):v for v in missing}
    with (out / "missing-evidence-request.csv").open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=("symbol","session","neededTimestamp","field",
                    "sourceAvailability","knownAt","purpose","approvalNeeded"))
        writer.writeheader();writer.writerows(unique_missing.values())
    with (out / "training-labels.npz").open("xb") as stream:
        np.savez_compressed(stream, **output, knownAt=known_at)
    result={"schema":"phase57-r54-zero-fit-teacher-readiness-v1",
            "status":"BLOCKED_INPUT_OR_INTEGRITY" if blocking else "CONDITIONAL_MEASUREMENT",
            "blocking":blocking,"sourceRows":n,"sourceGroups":len(groups),
            "windowEntries":{a:sum(e["session"] in p["sessions"] for (arm,_),e in entries.items() if arm==a) for a in v0.ARMS},
            "maskCounts":dict(mask_counts),"unavailableReasons":dict(counters),
            "missingEvidenceRows":len(unique_missing),"resources":size,
            "teacherValuesInspected":False,"candidatePerformanceInspected":False,
            "estimatorFits":0,"policyReplays":0,"protectedOpened":0,"providerRequests":0,
            "safety":v0.SAFETY,"filesSha256":{x.name:sha(x) for x in out.iterdir()}}
    (out/"readiness.json").write_bytes(canonical(result))
    print(canonical({k:result[k] for k in ("status","blocking","sourceRows","sourceGroups",
       "windowEntries","resources","estimatorFits","policyReplays")}).decode(),flush=True)
    return result


if __name__ == "__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args();readiness(args.source,args.out)
