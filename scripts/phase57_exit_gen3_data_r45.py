"""R45 immutable R35 + NOW-only decision facts and sampled-utility labels.

The output preserves R36's complete row population and ordering. Availability
of future labels is saved exclusively in the training-only artifact and never
enters a feature. No estimator, policy replay, scorecard or selection is run.
"""
from __future__ import annotations

import collections
import concurrent.futures
import gzip
import json
import multiprocessing
from pathlib import Path

import numpy as np

from scripts import phase57_exit_finite_r36 as r36
from scripts import phase57_exit_checkpoints_v1 as r20
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_exit_feature_contract_v1 as feature_contract
from scripts import phase57_exit_research_protocol_v1 as r25
from scripts.phase57_chart_entry import minute as chart_minute
from scripts.phase57_exit_gen3_labels_r45 import HEADS, REASONS, utility_labels
from scripts.phase57_exit_gen2_labels_r41 import index_raw_rows
from scripts.phase57_exit_gen3_facts_r45 import FactMemo, past_five, calendar
from scripts.phase57_exit_gen3_runtime_r45 import PROTOCOL_PATH, PROTOCOL_SHA256, PRECOMMIT_SHA, load_protocol


PRECOMMIT_HEAD = PRECOMMIT_SHA
CALENDAR_NAMES = ['calendar.remainingContinuousBars', 'calendar.utilityHorizonBars']
FACT_NAMES = load_protocol()['features']['decisionFactFields']
_AUX_RAW = _AUX_ORIGINS = _AUX_NAMES = None


def verify_r35(core_root: Path, protocol: dict) -> dict:
    """Verify actual A/B file bytes as well as their pinned manifest claims."""
    a, b = r36._verify_r35(core_root)
    expected_paths = {f"checkpoints/{s}.jsonl.gz" for s in r25.development_sessions()}
    expected_paths.update(("columns.json", "entry-envelopes.json.gz"))
    for variant, manifest in (("core-a", a), ("core-b", b)):
        r36.require(manifest["projectionSha256"] == protocol["features"]["r35ProjectionSha256"],
                    "PINNED_R35_PROJECTION")
        r36.require(manifest["fitContractSha256"] == protocol["features"]["coreFitContractSha256"],
                    "PINNED_R35_FIT_CONTRACT")
        r36.require(manifest["sessions"] == 58 and manifest["populationPerArm"] == 2155,
                    "R35_SESSION_OR_POPULATION_COUNT")
        r36.require(manifest["categoricalFields"] == 21 and manifest["numericFields"] == 83,
                    "R35_FEATURE_COUNTS")
        r36.require(manifest["safety"] == r36.SAFETY, "R35_EXACT_SAFETY9")
        r36.require(set(manifest["outputHashes"]) == expected_paths, "R35_FILE_ALLOWLIST")
        for relative, expected in manifest["outputHashes"].items():
            r36.require(r36.sha(core_root / variant / relative) == expected,
                        f"R35_ACTUAL_FILE_HASH:{variant}/{relative}")
    return a


def pattern_vector(session, now, path, origin, pattern_names):
    """Build Pattern187 solely from canonical known closed prefixes."""
    previous = (r20.closed_prefix(path["previousSession"], 1440, path["previous"])
                if path["previousSession"] else ())
    today = r20.closed_prefix(session, now, path["today"])
    result = feature_contract.pattern_now(
        day=session, now=now, selector_minute=chart_minute(origin["decisionTimestamp"]),
        selector_origin=origin, today_prefix=today, previous_prefix=previous,
    )["curated"]
    r36.require(list(result) == pattern_names, "PATTERN_COLUMN_ORDER_DRIFT")
    return [r36.numeric(result[name]) for name in pattern_names]


def _aux_init(raw, origins, names):
    global _AUX_RAW, _AUX_ORIGINS, _AUX_NAMES
    _AUX_RAW, _AUX_ORIGINS, _AUX_NAMES = raw, origins, names


def _session_aux(task):
    # Pattern is shared only by identical (Opportunity,NOW); labels depend on Entry.
    session, keys = task
    patterns = np.full((len(keys),len(_AUX_NAMES)),np.nan,dtype=np.float32)
    for i,(oid,now) in enumerate(keys):
        patterns[i]=pattern_vector(session,now,_AUX_RAW[oid],_AUX_ORIGINS[oid],_AUX_NAMES)
        if i and i%2000==0:
            print(r36.canonical({'patternSession':session,'done':i,'total':len(keys)}).decode().strip(),flush=True)
    return session, keys, patterns


def _core_rows(core_root, session):
    with gzip.open(core_root / "core-a/checkpoints" / f"{session}.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            r36.require(set(row) == {"session", "identity", "fresh", "categorical", "numeric"},
                        "R35_ROW_FIELDS")
            r36.require(row["session"] == session, "R35_ROW_SESSION")
            r36.require(len(row["categorical"]) == 21 and len(row["numeric"]) == 83,
                        "R35_ROW_FEATURE_COUNT")
            r36.require(type(row["fresh"]) is bool, "R35_FRESH_TYPE")
            yield row


def build_data(core_root: Path, out: Path, workers: int, protocol: dict, *, include_pattern: bool = True) -> r36.Data:
    """Create all 656,247 rows, labels and audit receipts without fitting."""
    r36.require(workers in (1, 2), "GEN3_DATA_WORKERS_OUTSIDE_PROTOCOL")
    r36.require(r36.sha(PROTOCOL_PATH) == PROTOCOL_SHA256
                and r36.read_json(PROTOCOL_PATH) == protocol, "IMMUTABLE_PROTOCOL_IDENTITY")
    r36.require(protocol["features"]["calendarFields"] == CALENDAR_NAMES, "CALENDAR_COLUMN_ORDER")
    manifest = verify_r35(core_root, protocol)
    for path, expected in ((r36.RAW_PATHS, r36.RAW_PATHS_SHA256),
                           (r36.PATTERN_OPPORTUNITIES, r36.PATTERN_OPPORTUNITIES_SHA256),
                           (r36.OPPORTUNITY_RECORDS, r36.OPPORTUNITY_RECORDS_SHA256)):
        r36.require(r36.sha(path) == expected, "SOURCE_HASH:" + path.name)
    columns = r36.read_json(core_root / "core-a/columns.json")
    r36.require(columns["labelsIncluded"] is False and columns["preprocessingFitted"] is False
                and columns["identityIsNotAFeature"] is True, "R35_CACHE_BOUNDARY")
    r36.require(len(columns["numeric"]) == 83 and len(columns["categorical"]) == 21,
                "R35_COLUMN_COUNTS")
    pattern_names = sorted(row["feature"] for row in feature_contract.pattern_rows()
                           if row["selectedInFiniteSearch"])
    r36.require(len(pattern_names) == 187 and pattern_names == protocol["features"]["patternNames"],
                "EXACT_FROZEN_PATTERN187")
    session_names = r25.development_sessions()
    envelopes = r36.read_json(core_root / "core-a/entry-envelopes.json.gz")
    r36.require(set(envelopes) == set(r36.ARMS), "ENTRY_ARMS")
    allowed_oids, entry_rows = set(), {}
    for arm in r36.ARMS:
        population = envelopes[arm]
        ids = {row["opportunity"] for row in population}
        r36.require(len(population) == len(ids) == 2155, "ENTRY_POPULATION")
        if allowed_oids:
            r36.require(allowed_oids == ids, "ENTRY_ARM_OPPORTUNITY_COHORT")
        allowed_oids = ids
        for source in population:
            r36.require(source["session"] in session_names, "NON_DEVELOPMENT_SESSION")
            if source["entryId"] is None:
                continue
            r36.require(r36._oid(source["entryId"]) == source["opportunity"], "ENTRY_OPPORTUNITY_JOIN")
            key = f"{arm}::{source['entryId']}"
            r36.require(key not in entry_rows, "DUPLICATE_ENTRY_ID")
            entry_rows[key] = {**source, "entryArm": arm}
    r36.require(collections.Counter(row["entryArm"] for row in entry_rows.values())
                == {r36.ARMS[0]: 1963, r36.ARMS[1]: 1885}, "ENTRY_FILLED_COUNTS")

    raw_all = r36.read_json(r36.RAW_PATHS)
    raw = {key: raw_all[key] for key in sorted(allowed_oids)}
    del raw_all
    origin_rows = r36.read_json(r36.PATTERN_OPPORTUNITIES)
    origins = {row["id"]: row["origin"] for row in origin_rows if row["id"] in allowed_oids}
    del origin_rows
    records = {row["opportunity"]: row for row in r36.read_json(r36.OPPORTUNITY_RECORDS)}
    r36.require(set(raw) == set(origins) == set(records) == allowed_oids, "PINNED_SOURCE_COHORT_JOIN")
    out.mkdir(parents=True, exist_ok=False)
    tasks, total_rows = [], 0
    category_maps = [dict() for _ in columns["categorical"]]
    for session in session_names:
        by_arm = [set(), set()]
        seen = set()
        for row in _core_rows(core_root, session):
            arm, eid, now = row["identity"]
            r36.require(arm in r36.ARMS and type(now) is int, "R35_IDENTITY_TYPE")
            identity = (arm, eid, now)
            r36.require(identity not in seen, "DUPLICATE_CORE_ROW_IDENTITY")
            seen.add(identity)
            entry = entry_rows.get(f"{arm}::{eid}")
            r36.require(entry is not None and entry["session"] == session
                        and now in execution.decision_endpoints(session, entry["entryMinute"]),
                        "R35_ENTRY_OR_NOW_JOIN")
            by_arm[r36.ARMS.index(arm)].add((r36._oid(eid), now))
            total_rows += 1
            for j, value in enumerate(row["categorical"]):
                r36.require(isinstance(value, str), "R35_CATEGORY_TYPE")
                category_maps[j].setdefault(value, None)
        r36.require(by_arm[1] <= by_arm[0], "R1_PATTERN_KEY_NOT_IN_IMMEDIATE:" + session)
        tasks.append((session, sorted(by_arm[0] | by_arm[1])))
    r36.require(total_rows == 656247 and sum(len(keys) for _, keys in tasks) == 345893,
                "COMPLETE_R35_ROW_POPULATION")
    category_maps = [{value: i for i, value in enumerate(sorted(mapping))} for mapping in category_maps]

    auxiliaries = {}
    if not include_pattern:
        auxiliaries = {session:(keys,None) for session,keys in tasks}
    elif workers == 1:
        _aux_init(raw, origins, pattern_names)
        for item in map(_session_aux, tasks):
            auxiliaries[item[0]] = item[1:]
    else:
        with concurrent.futures.ProcessPoolExecutor(
                max_workers=workers, mp_context=multiprocessing.get_context("fork"),
                initializer=_aux_init, initargs=(raw, origins, pattern_names)) as pool:
            for item in pool.map(_session_aux, tasks, chunksize=1):
                auxiliaries[item[0]] = item[1:]

    n = total_rows
    session_code = {s: i for i, s in enumerate(session_names)}
    entry_ids = sorted(entry_rows)
    entry_code = {e: i for i, e in enumerate(entry_ids)}
    numeric_names = columns["numeric"] + CALENDAR_NAMES + ["facts."+k for k in FACT_NAMES]
    r36.require(columns["numeric"]==protocol["features"]["baseNumeric"] and columns["categorical"]==protocol["features"]["categorical"], "R45_EXACT_BASE_COLUMNS")
    r36.require(len(numeric_names)==protocol["features"]["numericCount"]==106, "R45_NUMERIC_COLUMNS")
    sessions = np.empty(n, dtype=np.int16); arms = np.empty(n, dtype=np.int8)
    entries = np.empty(n, dtype=np.int32); now_values = np.empty(n, dtype=np.int16)
    fresh = np.empty(n, dtype=np.bool_)
    cats = np.empty((n, 21), dtype=np.int16); nums = np.empty((n, 106), dtype=np.float32)
    patterns = np.full((n, 187), np.nan, dtype=np.float32); targets = np.empty((n, 3), dtype=np.float32)
    known = np.empty((n, 3), dtype=np.int16); ends = np.empty((n, 3), dtype=np.int16)
    horizons = np.empty((n, 3), dtype=np.int16); reasons = np.empty((n, 3), dtype=np.uint8)
    fact_values=np.full((n,21),np.nan,dtype=np.float64)
    sample_refs=np.full((n,3),-1,dtype=np.int16)
    utilities=np.full((n,3),np.nan,dtype=np.float64)
    anchor_prices=np.full(n,np.nan,dtype=np.float64)
    future_prices=np.full((n,3),np.nan,dtype=np.float64)
    cursor = 0
    for session in session_names:
        keys, pmat = auxiliaries.pop(session)
        memo=None; previous_key=None; indexed=None; prices_cache={}
        starts=execution.continuous_minutes(session)
        aux_index = {key: i for i, key in enumerate(keys)}
        rows = sorted(_core_rows(core_root, session), key=lambda row: (
            r36.ARMS.index(row["identity"][0]), row["identity"][1], row["identity"][2]))
        for row in rows:
            arm, eid, now = row["identity"]
            sessions[cursor] = session_code[session]; arms[cursor] = r36.ARMS.index(arm)
            entries[cursor] = entry_code[f"{arm}::{eid}"]
            now_values[cursor] = now; fresh[cursor] = row["fresh"]
            cats[cursor] = [category_maps[j][value] for j, value in enumerate(row["categorical"])]
            nums[cursor, :83] = [r36.numeric(value) for value in row["numeric"]]
            # Causal facts receive only exact last5 completed bars, never suffix.
            key=f"{arm}::{eid}"
            if key!=previous_key:
                memo=FactMemo(); previous_key=key
                indexed=index_raw_rows(raw[r36._oid(eid)]['today'])
            pair=(r36._oid(eid),now)
            if pair not in prices_cache:
                past_starts=[s for s in starts if s+1<=now][-5:]
                closed=[indexed[s] for s in past_starts if s in indexed]
                prices_cache[pair]=past_five(session,now,closed)
            envelope=memo.update(session,row,prices_cache[pair])
            fv=envelope['values']
            fact_values[cursor]=[r36.numeric(fv[name]) for name in FACT_NAMES]
            nums[cursor,83:85]=calendar(session,now)
            nums[cursor,85:]=fact_values[cursor]
            if include_pattern:
                patterns[cursor]=pmat[aux_index[pair]]
            # Training-only target module: its outputs never enter feature arrays.
            target=utility_labels(session,now,float(entry_rows[key]['price']),row['fresh'],fv['certifiedMfePct'],indexed)
            for j,head in enumerate(HEADS):
                targets[cursor,j]=r36.numeric(target['targets'][head])
                known[cursor,j]=target['knownAt'][head] or -1
                ends[cursor,j]=target['sampleReferenceMinutes'][-1] if target['sampleReferenceMinutes'] else -1
                horizons[cursor,j]=target['horizonBars']
                reasons[cursor,j]=REASONS.index(target['reasonCode'][head])
            if target['sampleReferenceMinutes']: sample_refs[cursor]=target['sampleReferenceMinutes']
            if 'futureUtility' in target:
                utilities[cursor]=target['futureUtility'];anchor_prices[cursor]=target['anchorPrice'];future_prices[cursor]=target['futureExecutablePrices']
            cursor += 1
    r36.require(cursor == n, "ASSEMBLY_COUNT")
    available = np.isfinite(targets)
    r36.require(np.array_equal(available, reasons == 0), "LABEL_REASON_MASK_MISMATCH")
    r36.require(np.all(known[available] > np.broadcast_to(now_values[:, None], known.shape)[available])
                and np.all(known[available] <= 930), "LABEL_MATURITY_OUTSIDE_SESSION")
    identity_path = out / "source-row-identity.jsonl.gz"
    r36.write_jsonl_gz(identity_path, ({
        "index": i, "session": session_names[int(sessions[i])], "arm": r36.ARMS[int(arms[i])],
        "entryId": entry_ids[int(entries[i])].split("::", 1)[1], "now": int(now_values[i]),
    } for i in range(n)))
    label_path = out / "training-labels.npz"
    with label_path.open("xb") as fh:
        np.savez_compressed(fh, targets=targets, available=available, knownAt=known,
                            windowEnd=ends, horizonBars=horizons, reasonCode=reasons,
                            sampleReferenceMinutes=sample_refs, anchorPrice=anchor_prices,
                            futureExecutablePrices=future_prices, futureUtility=utilities)
    fact_path=out / "decision-facts.npz"
    with fact_path.open("xb") as fh:
        np.savez_compressed(fh, values=fact_values, now=now_values, fresh=fresh)
    representation_path = out / "categorical-representation.json"
    r36.write_json(representation_path, {
        "schema": "phase57-gen3-stable-categorical-representation-r45-v1",
        "ordinalFeature": False, "preprocessingFitted": False,
        "maps": dict(zip(columns["categorical"], category_maps)),
    })
    counts = {}
    for a, arm in enumerate(r36.ARMS):
        mask = arms == a
        counts[arm] = {}
        for h, head in enumerate(HEADS):
            counts[arm][head] = {
                "total": int(np.sum(mask)), "available": int(np.sum(available[mask, h])),
                "zero": int(np.sum(targets[mask, h] == 0)), "one": int(np.sum(targets[mask, h] == 1)),
                "reasonCounts": {reason: int(np.sum(reasons[mask, h] == i)) for i, reason in enumerate(REASONS)},
            }
    reasons_path = out / "training-label-reasons.json"
    r36.write_json(reasons_path, {
        "schema": "phase57-gen3-training-label-reasons-r45-v1", "trainingOnly": True,
        "heads": list(HEADS), "reasonCodes": dict(enumerate(REASONS)), "nullMinuteSentinel": -1,
        "independentHeadMasks": True, "labelImputation": False,
        "countsByArmHead": counts, "labelsSha256": r36.sha(label_path),
        "sourceRowIdentitySha256": r36.sha(identity_path),
    })
    r36.write_json(out / "data-receipt.json", {
        "schema": "phase57-gen3-data-receipt-r45-v1", "rows": n,
        "rowsByArm": {r36.ARMS[i]: int(np.sum(arms == i)) for i in range(2)},
        "numericColumns": numeric_names, "categoricalColumns": columns["categorical"],
        "patternColumns": pattern_names, "targetColumns": list(HEADS),
        "uniquePatternKeys": sum(len(keys) for _, keys in tasks),
        "protocolSha256": PROTOCOL_SHA256, "precommitHead": PRECOMMIT_HEAD,
        "r35ProjectionSha256": manifest["projectionSha256"], "r35ActualFileHashesVerified": True,
        "sourceHashes": {str(path.relative_to(r36.ROOT)): r36.sha(path) for path in
                         (r36.RAW_PATHS, r36.PATTERN_OPPORTUNITIES, r36.OPPORTUNITY_RECORDS)},
        "outputHashes": {path.name: r36.sha(path) for path in
                         (identity_path, label_path, fact_path, representation_path, reasons_path)},
        "patternComputed": include_pattern, "decisionFactNames": FACT_NAMES,
        "labelAvailabilityUsedAsFeature": False, "independentHeadMasks": True,
        "modelFits": 0, "candidateReplays": 0, "performanceInspections": 0,
        "providerRequests": 0, "protectedPartitionsOpened": 0, "safety": r36.SAFETY,
    })
    data = r36.Data(session_names, columns["categorical"], numeric_names, pattern_names,
                    sessions, arms, entries, now_values, fresh, cats, nums, patterns,
                    targets, entry_ids, entry_rows, raw, records)

    data.fact_values=fact_values
    data.pattern_computed=include_pattern
    return data
