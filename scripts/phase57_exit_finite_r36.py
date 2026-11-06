"""One-shot finite R25 NEW EXIT fit, causal replay and selection.

This is the first performance-bearing NEW EXIT runner.  Its implementation is
frozen by R36 before the workflow is allowed to execute.  It consumes the
immutable R35 CORE cache and repository-pinned Development evaluator sources.
It fits exactly the six R33 prediction specifications (three heads, two Entry
arms, four folds = 144 fits), then reuses those predictions for all 24 policies.

The module has no provider or protected-partition interface and no trading or
promotion path.  Run A/B below means two independent causal replay/score passes
over one shared, immutable set of fitted OOF predictions; models are not fitted
twice merely to vary policy thresholds or prove score serialization.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import gzip
import hashlib
import io
import json
import math
import multiprocessing
import os
import pickle
import shutil
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from scripts import phase57_exit_checkpoints_v1 as r20
from scripts import phase57_exit_evaluator_contract_v1 as evaluator_contract
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_exit_feature_contract_v1 as feature_contract
from scripts import phase57_exit_fit_contract_r33 as r33
from scripts import phase57_exit_research_protocol_v1 as r25
from scripts.phase57_chart_entry import minute as chart_minute
from scripts.phase57_exit_capture_metrics_v1 import (
    BUCKETS, OrderedGeometry, PostEntryHigh, evaluate_capture, opportunity_bucket,
)
from scripts.phase57_exit_core_runtime_r35 import exit_intent
from scripts.phase57_exit_hold_targets_r35 import hold_targets


ROOT = Path(__file__).resolve().parents[1]
RAW_PATHS = ROOT / "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz"
PATTERN_OPPORTUNITIES = ROOT / "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/opportunities.json.gz"
OPPORTUNITY_RECORDS = ROOT / "docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz"
R35_ARTIFACT_SHA256 = "a12852e36f270e247a9a0bb7f0f7f618da934297c05f7c687fccb7ceade40434"
R35_PROJECTION_SHA256 = ""  # checked against A/B manifests, never guessed here
RAW_PATHS_SHA256 = "37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b"
PATTERN_OPPORTUNITIES_SHA256 = "1138960e489c3403e49f502a7ff7ab1fa1e9ef205910d2d018f2bb938df813ea"
OPPORTUNITY_RECORDS_SHA256 = "4b9afd72ccfff0b557fb4a5e067ac122ace90ae501d15a79627a89af9554a01e"
ARMS = r33.ARMS
HEADS = ("HOLD5", "HOLD15", "HOLD_TERMINAL")
COSTS = (0.05, 0.10, 0.20)
SAFETY = {k: False for k in (
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
    "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted",
)}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def sha(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def read_json(path: Path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def write_json(path: Path, value) -> None:
    require(not path.exists(), "APPEND_ONLY_OUTPUT_EXISTS:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def write_jsonl_gz(path: Path, rows) -> None:
    require(not path.exists(), "APPEND_ONLY_OUTPUT_EXISTS:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as bf, gzip.GzipFile(fileobj=bf, mode="wb", filename="", mtime=0) as gz:
        for row in rows:
            gz.write(canonical(row))


def finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def numeric(value):
    return float(value) if finite(value) else np.nan


def percentile(values, q):
    values = np.asarray([x for x in values if finite(x)], dtype=np.float64)
    return None if not len(values) else float(np.percentile(values, q, method="linear"))


def summary(values) -> dict:
    a = np.asarray([x for x in values if finite(x)], dtype=np.float64)
    if not len(a):
        return {"n": 0, "mean": None, "median": None, "p05": None,
                "p10": None, "worst": None}
    return {"n": int(len(a)), "mean": float(np.mean(a)), "median": float(np.median(a)),
            "p05": float(np.percentile(a, 5, method="linear")),
            "p10": float(np.percentile(a, 10, method="linear")), "worst": float(np.min(a))}


def profit_stats(values) -> dict:
    a = np.asarray([x for x in values if finite(x)], dtype=np.float64)
    pos, neg = a[a > 0], a[a < 0]
    return {
        "n": int(len(a)),
        "profitFactor": None if not len(neg) or -float(neg.sum()) == 0 else float(pos.sum() / -neg.sum()),
        "winRate": None if not len(a) else float(np.mean(a > 0)),
        "averageWin": None if not len(pos) else float(np.mean(pos)),
        "averageLoss": None if not len(neg) else float(np.mean(neg)),
        **summary(a),
    }


def _oid(entry_id: str) -> str:
    parts = entry_id.split("|")
    require(len(parts) == 3, "ENTRY_ID_FORMAT")
    return "|".join(parts[:2])


@dataclass
class Data:
    session_names: list[str]
    categorical_names: list[str]
    numeric_names: list[str]
    pattern_names: list[str]
    sessions: np.ndarray
    arms: np.ndarray
    entries: np.ndarray
    now: np.ndarray
    fresh: np.ndarray
    categorical: np.ndarray
    numeric: np.ndarray
    pattern: np.ndarray
    targets: np.ndarray
    entry_ids: list[str]
    entry_rows: dict[str, dict]
    raw: dict
    opportunity_records: dict


_AUX_RAW = None
_AUX_ORIGINS = None
_AUX_PATTERN_NAMES = None


def _aux_init(raw, origins, pattern_names):
    global _AUX_RAW, _AUX_ORIGINS, _AUX_PATTERN_NAMES
    _AUX_RAW, _AUX_ORIGINS, _AUX_PATTERN_NAMES = raw, origins, pattern_names


def _session_aux(task):
    """Compute each Opportunity/NOW Pattern vector and future label once."""
    session, keys = task
    patterns = np.full((len(keys), len(_AUX_PATTERN_NAMES)), np.nan, dtype=np.float32)
    targets = np.full((len(keys), 3), np.nan, dtype=np.float32)
    schedules = execution.continuous_minutes(session)
    for i, (oid, now) in enumerate(keys):
        path = _AUX_RAW[oid]
        origin = _AUX_ORIGINS[oid]
        previous = (r20.closed_prefix(path["previousSession"], 1440, path["previous"])
                    if path["previousSession"] else ())
        today = r20.closed_prefix(session, now, path["today"])
        result = feature_contract.pattern_now(
            day=session, now=now, selector_minute=chart_minute(origin["decisionTimestamp"]),
            selector_origin=origin, today_prefix=today, previous_prefix=previous,
        )["curated"]
        require(list(result) == _AUX_PATTERN_NAMES, "PATTERN_COLUMN_ORDER_DRIFT")
        patterns[i] = [numeric(result[n]) for n in _AUX_PATTERN_NAMES]
        target = hold_targets(now, schedules, path["today"])["targetsPp"]
        targets[i] = [numeric(target[h]) for h in HEADS]
        if i and i % 2000 == 0:
            print(canonical({"auxSession": session, "done": i, "total": len(keys)}).decode().strip(), flush=True)
    return session, keys, patterns, targets


def _verify_r35(core_root: Path) -> tuple[dict, dict]:
    a = read_json(core_root / "core-a/manifest.json")
    b = read_json(core_root / "core-b/manifest.json")
    require(a["projectionSha256"] == b["projectionSha256"], "R35_PROJECTION_AB")
    require(a["outputHashes"] == b["outputHashes"], "R35_OUTPUT_HASHES_AB")
    require(a["checkpointCounts"] == {"IMMEDIATE": 345893,
            "ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF": 310354}, "R35_COUNTS")
    require(a["modelFits"] == a["candidateReplays"] == a["performanceInspections"] == 0,
            "R35_NOT_PREP_ONLY")
    require(a["providerRequests"] == a["protectedPartitionsOpened"] == 0, "R35_BOUNDARY")
    require(all(v is False for v in a["safety"].values()), "R35_SAFETY")
    return a, b


def build_data(core_root: Path, cache: Path, workers: int) -> Data:
    """Build an in-memory design substrate; no estimator or score is touched."""
    manifest_a, _ = _verify_r35(core_root)
    for path, expected in ((RAW_PATHS, RAW_PATHS_SHA256),
                           (PATTERN_OPPORTUNITIES, PATTERN_OPPORTUNITIES_SHA256),
                           (OPPORTUNITY_RECORDS, OPPORTUNITY_RECORDS_SHA256)):
        require(sha(path) == expected, "SOURCE_HASH:" + path.name)
    columns = read_json(core_root / "core-a/columns.json")
    require(columns["labelsIncluded"] is False and columns["preprocessingFitted"] is False,
            "R35_CACHE_BOUNDARY")
    pattern_names = sorted(r["feature"] for r in feature_contract.pattern_rows()
                           if r["selectedInFiniteSearch"])
    require(len(pattern_names) == 187, "PATTERN_NOT_187")
    cohort = set(r25.development_sessions())
    envelopes = read_json(core_root / "core-a/entry-envelopes.json.gz")
    entry_rows = {}
    for arm in ARMS:
        for source in envelopes[arm]:
            if source["entryId"] is None:
                continue
            row = dict(source); row["entryArm"] = arm
            entry_rows[f"{arm}::{row['entryId']}"] = row
    require(len(entry_rows) == 1963 + 1885, "ENTRY_ID_COHORT")
    allowed_oids = {row["opportunity"] for arm in ARMS for row in envelopes[arm]}
    require(len(allowed_oids) == 2155, "OPPORTUNITY_COHORT")

    raw_all = read_json(RAW_PATHS)
    raw = {k: raw_all[k] for k in sorted(allowed_oids)}
    del raw_all
    opp_all = read_json(PATTERN_OPPORTUNITIES)
    origins = {r["id"]: r["origin"] for r in opp_all if r["id"] in allowed_oids}
    del opp_all
    require(set(raw) == set(origins) == allowed_oids, "RAW_ORIGIN_JOIN")
    records = {r["opportunity"]: r for r in read_json(OPPORTUNITY_RECORDS)}
    require(set(records) == allowed_oids, "OPPORTUNITY_RECORD_JOIN")

    cache.mkdir(parents=True, exist_ok=False)
    # Union keys are taken from both arms. The observed R1 subset relation is
    # asserted rather than assumed and Pattern/labels are computed once per key.
    tasks = []
    total_rows = 0
    for session in r25.development_sessions():
        keys, immediate, r1keys = set(), set(), set()
        core_path = core_root / "core-a/checkpoints" / f"{session}.jsonl.gz"
        with gzip.open(core_path, "rt", encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                arm, eid, now = row["identity"]
                key = (_oid(eid), int(now)); keys.add(key)
                (immediate if arm == "IMMEDIATE" else r1keys).add(key)
                total_rows += 1
        require(r1keys <= immediate, "R1_PATTERN_KEY_NOT_IN_IMMEDIATE:" + session)
        tasks.append((session, sorted(keys)))
    require(total_rows == 656247, "R35_TOTAL_ROWS")
    require(sum(len(k) for _, k in tasks) == 345893, "UNIQUE_PATTERN_KEY_COUNT")

    aux_by_session = {}
    if workers == 1:
        _aux_init(raw, origins, pattern_names)
        results = map(_session_aux, tasks)
        for item in results:
            aux_by_session[item[0]] = item[1:]
    else:
        context = multiprocessing.get_context("fork")
        with concurrent.futures.ProcessPoolExecutor(
                max_workers=workers, mp_context=context,
                initializer=_aux_init, initargs=(raw, origins, pattern_names)) as pool:
            for item in pool.map(_session_aux, tasks, chunksize=1):
                aux_by_session[item[0]] = item[1:]

    session_names = r25.development_sessions()
    session_code = {s: i for i, s in enumerate(session_names)}
    entry_ids = sorted(entry_rows)
    entry_code = {e: i for i, e in enumerate(entry_ids)}
    category_maps = [dict() for _ in columns["categorical"]]
    # Stable representation codes do not fit categories; OneHotEncoder still
    # learns the actually present levels from each head's train rows only.
    for session in session_names:
        p = core_root / "core-a/checkpoints" / f"{session}.jsonl.gz"
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            for line in fh:
                vals = json.loads(line)["categorical"]
                for j, value in enumerate(vals):
                    category_maps[j].setdefault(value, None)
    category_maps = [{v: i for i, v in enumerate(sorted(m))} for m in category_maps]

    n = total_rows
    sessions = np.empty(n, dtype=np.int16); arms = np.empty(n, dtype=np.int8)
    entries = np.empty(n, dtype=np.int32); now_values = np.empty(n, dtype=np.int16)
    fresh = np.empty(n, dtype=np.bool_)
    cats = np.empty((n, len(columns["categorical"])), dtype=np.int16)
    nums = np.empty((n, len(columns["numeric"])), dtype=np.float32)
    patterns = np.empty((n, len(pattern_names)), dtype=np.float32)
    targets = np.empty((n, 3), dtype=np.float32)
    cursor = 0
    for session in session_names:
        keys, pmat, tmat = aux_by_session[session]
        aux_index = {key: i for i, key in enumerate(keys)}
        path = core_root / "core-a/checkpoints" / f"{session}.jsonl.gz"
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh]
        rows.sort(key=lambda r: (0 if r["identity"][0] == ARMS[0] else 1,
                                 r["identity"][1], r["identity"][2]))
        for row in rows:
            arm, eid, now = row["identity"]
            sessions[cursor] = session_code[session]
            arms[cursor] = 0 if arm == ARMS[0] else 1
            entries[cursor] = entry_code[f"{arm}::{eid}"]
            now_values[cursor] = now; fresh[cursor] = row["fresh"]
            cats[cursor] = [category_maps[j][v] for j, v in enumerate(row["categorical"])]
            nums[cursor] = [numeric(v) for v in row["numeric"]]
            k = aux_index[(_oid(eid), int(now))]
            patterns[cursor] = pmat[k]; targets[cursor] = tmat[k]
            cursor += 1
    require(cursor == n, "ASSEMBLY_COUNT")

    # R31 post-Entry High anatomy is reproduced before any estimator fit.
    anatomy = reproduce_r31_anatomy(entry_rows, raw, records)
    write_json(cache / "data-receipt.json", {
        "schema": "phase57-r36-fit-data-receipt-v1", "rows": n,
        "rowsByArm": {ARMS[i]: int(np.sum(arms == i)) for i in range(2)},
        "uniquePatternKeys": sum(len(x) for _, x in tasks),
        "patternColumns": len(pattern_names), "targetColumns": list(HEADS),
        "r35ProjectionSha256": manifest_a["projectionSha256"],
        "sourceHashes": {str(p.relative_to(ROOT)): sha(p) for p in
                         (RAW_PATHS, PATTERN_OPPORTUNITIES, OPPORTUNITY_RECORDS)},
        "r31Anatomy": anatomy, "modelFits": 0, "candidateReplays": 0,
        "providerRequests": 0, "protectedPartitionsOpened": 0, "safety": SAFETY,
    })
    return Data(session_names, columns["categorical"], columns["numeric"], pattern_names,
                sessions, arms, entries, now_values, fresh, cats, nums, patterns,
                targets, entry_ids, entry_rows, raw, records)


def _post_entry_high(entry: dict, rows) -> PostEntryHigh | None:
    candidates = [r for r in rows if len(r) == 7 and int(r[0]) == r[0]
                  and r[0] > entry["entryMinute"] and finite(r[2])]
    if not candidates:
        return None
    high = max(float(r[2]) for r in candidates)
    # Earliest identical best High is deterministic; R21 does not impose a tie rule.
    row = next(r for r in candidates if float(r[2]) == high)
    known = int(row[0]) if int(row[0]) == 930 else int(row[0]) + 1
    return PostEntryHigh(high, int(row[0]), 930,
                         "POST_ENTRY_BEST_HIGH_R31_RAW_PATH_37853e73", "COMPLETE", known)


def _ordered_geometry(record: dict) -> OrderedGeometry | None:
    value, _ = evaluator_contract.geometry(record)
    return value


def reproduce_r31_anatomy(entry_rows: dict, raw: dict, records: dict) -> dict:
    expected = {
        ARMS[0]: (1963, 3.2759536262693145, 1.853834987268277),
        ARMS[1]: (1885, 3.08034166631174, 1.6673793687348892),
    }
    out = {}
    for arm in ARMS:
        values = []
        selected = [e for e in entry_rows.values() if e["entryArm"] == arm]
        for entry in selected:
            high = _post_entry_high(entry, raw[entry["opportunity"]]["today"])
            require(high is not None, "POST_ENTRY_HIGH_MISSING")
            values.append(100 * (high.high / entry["price"] - 1))
        n, mean, median = expected[arm]
        require(len(values) == n, "R31_POST_HIGH_N")
        require(abs(float(np.mean(values)) - mean) < 1e-12, "R31_POST_HIGH_MEAN")
        require(abs(float(np.median(values)) - median) < 1e-12, "R31_POST_HIGH_MEDIAN")
        out[arm] = {"n": n, "mean": mean, "median": median}
    return out


def prediction_specs() -> list[dict]:
    return r33.prediction_specs()


def spec_id(spec: dict) -> str:
    family = "RIDGE" if spec["family"].startswith("RIDGE") else "HGB"
    param = f"A{spec['alpha']:g}" if family == "RIDGE" else f"L{spec['maxLeafNodes']}"
    return f"{family}_{'CORE' if spec['featureSet']=='CORE' else 'PATTERN'}_{param}"


def candidate_spec(candidate: dict) -> str:
    lookup = {json.dumps({k: v for k, v in s.items()}, sort_keys=True): spec_id(s)
              for s in prediction_specs()}
    keep = {k: candidate[k] for k in candidate if k in (
        "family", "featureSet", "alpha", "maxLeafNodes", "learningRate",
        "maxIter", "minSamplesLeaf", "l2Regularization", "randomSeed")}
    return lookup[json.dumps(keep, sort_keys=True)]


def weights_for(data: Data, indices: np.ndarray) -> np.ndarray:
    rows_per_entry = np.bincount(data.entries[indices], minlength=len(data.entry_ids))
    unique_entries = np.flatnonzero(rows_per_entry)
    entry_session = np.full(len(data.entry_ids), -1, dtype=np.int16)
    entry_session[data.entries[indices]] = data.sessions[indices]
    opps_per_session = np.bincount(entry_session[unique_entries], minlength=len(data.session_names))
    w = 1.0 / (opps_per_session[data.sessions[indices]] * rows_per_entry[data.entries[indices]])
    w /= np.mean(w)
    require(np.all(np.isfinite(w)) and np.all(w > 0), "INVALID_WEIGHTS")
    return w.astype(np.float64)


def _matrix(data: Data, indices: np.ndarray, include_pattern: bool) -> np.ndarray:
    numeric_matrix = data.numeric[indices]
    return (np.concatenate((numeric_matrix, data.pattern[indices]), axis=1)
            if include_pattern else numeric_matrix)


def _fit_preprocess(data: Data, train: np.ndarray, score: np.ndarray,
                    include_pattern: bool, dense: bool, ridge: bool):
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=not dense,
                            dtype=np.float32)
    cat_train = encoder.fit_transform(data.categorical[train])
    cat_score = encoder.transform(data.categorical[score])
    imputer = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
    num_train = imputer.fit_transform(_matrix(data, train, include_pattern)).astype(np.float32)
    num_score = imputer.transform(_matrix(data, score, include_pattern)).astype(np.float32)
    if dense:
        x_train = np.concatenate((np.asarray(cat_train, dtype=np.float32), num_train), axis=1)
        x_score = np.concatenate((np.asarray(cat_score, dtype=np.float32), num_score), axis=1)
        scaler = None
    else:
        x_train = sparse.hstack((cat_train, sparse.csr_matrix(num_train)), format="csr", dtype=np.float32)
        x_score = sparse.hstack((cat_score, sparse.csr_matrix(num_score)), format="csr", dtype=np.float32)
        scaler = StandardScaler(with_mean=False)
        x_train = scaler.fit_transform(x_train)
        x_score = scaler.transform(x_score)
    return x_train, x_score, encoder, imputer, scaler


def fit_predictions(data: Data, out: Path) -> tuple[dict[str, np.ndarray], dict]:
    specs = prediction_specs()
    predictions = {spec_id(s): np.full((len(data.sessions), 3), np.nan, dtype=np.float32)
                   for s in specs}
    model_dir = out / "models"; model_dir.mkdir(parents=True, exist_ok=False)
    model_rows = []; model_fits = 0
    folds = r25.folds()
    session_code = {s: i for i, s in enumerate(data.session_names)}
    for fold in folds:
        train_sessions = np.asarray([session_code[s] for s in fold["train"]])
        score_sessions = np.asarray([session_code[s] for s in fold["score"]])
        for arm_code, arm in enumerate(ARMS):
            base_train = np.flatnonzero((data.arms == arm_code) & np.isin(data.sessions, train_sessions))
            score = np.flatnonzero((data.arms == arm_code) & np.isin(data.sessions, score_sessions))
            require(len(base_train) and len(score), "EMPTY_FOLD_ARM")
            for head in range(3):
                train = base_train[np.isfinite(data.targets[base_train, head])]
                require(len(train), "EMPTY_TARGET_TRAIN")
                weights = weights_for(data, train)
                y = data.targets[train, head].astype(np.float64)
                transforms = {}
                for feature_set, dense, ridge_flag in (
                        ("CORE", False, True),
                        ("CORE_PLUS_CURATED_PATTERN", False, True),
                        ("CORE_PLUS_CURATED_PATTERN", True, False)):
                    transforms[(feature_set, dense)] = _fit_preprocess(
                        data, train, score, feature_set != "CORE", dense, ridge_flag)
                for spec in specs:
                    sid = spec_id(spec); is_ridge = spec["family"].startswith("RIDGE")
                    dense = not is_ridge
                    x_train, x_score, encoder, imputer, scaler = transforms[(spec["featureSet"], dense)]
                    if is_ridge:
                        model = Ridge(alpha=spec["alpha"], solver="lsqr", tol=1e-6,
                                      max_iter=2000, fit_intercept=True)
                    else:
                        model = HistGradientBoostingRegressor(
                            max_leaf_nodes=spec["maxLeafNodes"],
                            learning_rate=spec["learningRate"], max_iter=spec["maxIter"],
                            min_samples_leaf=spec["minSamplesLeaf"],
                            l2_regularization=spec["l2Regularization"],
                            random_state=spec["randomSeed"], early_stopping=False,
                        )
                    model.fit(x_train, y, sample_weight=weights)
                    predicted = model.predict(x_score)
                    require(np.all(np.isfinite(predicted)), "NONFINITE_PREDICTION")
                    predictions[sid][score, head] = predicted.astype(np.float32)
                    bundle = {"spec": spec, "fold": fold["fold"], "arm": arm,
                              "head": HEADS[head], "encoder": encoder,
                              "imputer": imputer, "scaler": scaler, "model": model}
                    name = f"{sid}__F{fold['fold']}__{arm}__{HEADS[head]}.joblib"
                    path = model_dir / name
                    joblib.dump(bundle, path, compress=3)
                    model_rows.append({"file": name, "sha256": sha(path),
                                       "trainRows": int(len(train)), "scoreRows": int(len(score)),
                                       "featureColumnsAfterTransform": int(x_train.shape[1])})
                    model_fits += 1
                    print(canonical({"fit": model_fits, "spec": sid, "fold": fold["fold"],
                                     "arm": arm, "head": HEADS[head]}).decode().strip(), flush=True)
    require(model_fits == 144, "MODEL_FIT_COUNT_NOT_144")
    score_codes = {session_code[s] for f in folds for s in f["score"]}
    scored = np.isin(data.sessions, list(score_codes))
    for sid, values in predictions.items():
        require(np.all(np.isfinite(values[scored])), "MISSING_OOF_PREDICTION:" + sid)
        require(np.all(np.isnan(values[~scored])), "PREDICTION_OUTSIDE_OOF:" + sid)
    pred_path = out / "oof-predictions.npz"
    np.savez_compressed(pred_path, **predictions)
    receipt = {"schema": "phase57-r36-finite-fit-receipt-v1", "modelFits": model_fits,
               "predictionSpecs": len(specs), "heads": 3, "arms": 2, "folds": 4,
               "models": model_rows, "predictionSha256": sha(pred_path),
               "providerRequests": 0, "protectedPartitionsOpened": 0, "safety": SAFETY}
    write_json(out / "fit-receipt.json", receipt)
    return predictions, receipt


def _position(data: Data, index: int) -> dict:
    return {name.removeprefix("position."): data.numeric[index, j]
            for j, name in enumerate(data.numeric_names) if name.startswith("position.")}


def replay_candidate(data: Data, predicted: np.ndarray, candidate: dict) -> list[dict]:
    score_sessions = {s for f in r25.folds() for s in f["score"]}
    score_codes = {data.session_names.index(s) for s in score_sessions if s in data.session_names}
    indices = np.flatnonzero(np.isin(data.sessions, list(score_codes)))
    groups = collections.defaultdict(list)
    for idx in indices:
        groups[int(data.entries[idx])].append(int(idx))
    rows = []
    for entry_code in sorted(groups):
        sequence = sorted(groups[entry_code], key=lambda i: int(data.now[i]))
        entry_key = data.entry_ids[entry_code]; entry = data.entry_rows[entry_key]
        eid = entry["entryId"]
        path = data.raw[entry["opportunity"]]["today"]
        count = 0; chosen = None; trigger = None; missing_refs = 0
        for idx in sequence:
            result = exit_intent(predicted[idx].tolist(), bool(data.fresh[idx]), count,
                                 candidate["exitThresholdPp"],
                                 candidate["persistenceFreshCheckpoints"])
            count = result["consecutive"]
            if result["action"] != "EXIT_INTENT":
                continue
            ref = execution.ordinary_execution_reference(entry["session"], int(data.now[idx]), path)
            if ref["status"] == "RESOLVED_NEXT_SCHEDULED_OPEN":
                chosen = (float(ref["price"]), int(ref["referenceStart"]), "MODEL_EXIT")
                trigger = idx; break
            missing_refs += 1
        if chosen is None:
            terminal = execution.terminal_execution_reference(path)
            if terminal["status"] == "RESOLVED_TERMINAL_AUCTION":
                chosen = (float(terminal["price"]), 930, "FORCED_TERMINAL")
                trigger = sequence[-1]
        exit_price = chosen[0] if chosen else None
        exit_minute = chosen[1] if chosen else None
        pos = _position(data, trigger if trigger is not None else sequence[-1])
        geometry = _ordered_geometry(data.opportunity_records[entry["opportunity"]])
        post_high = _post_entry_high(entry, path)
        owned_peak = numeric(pos.get("observedRunningHigh"))
        owned_time = numeric(pos.get("peakConfirmedAt"))
        if exit_price is None or not finite(owned_peak) or not finite(owned_time):
            owned_peak = owned_time = None
        metrics = evaluate_capture(
            entry_price=float(entry["price"]), entry_minute=int(entry["entryMinute"]),
            exit_price=exit_price, exit_minute=exit_minute, cost_pp=0.05,
            geometry=geometry, post_entry_high=post_high,
            owned_peak=owned_peak, owned_peak_confirmed_at=(int(owned_time) if owned_time is not None else None),
            owned_path_complete=bool(pos.get("fullOwnedPrefix") == 1),
        )
        later_highs = [] if exit_minute is None else [float(r[2]) for r in path
            if len(r) == 7 and finite(r[2]) and
            ((int(r[0]) if int(r[0]) == 930 else int(r[0]) + 1) > exit_minute)]
        early = (None if exit_minute is None else
                 100 * max(0.0, (max(later_highs, default=exit_price) - exit_price) / entry["price"]))
        net = {f"{cost:.2f}": (None if exit_price is None else
               100 * (exit_price / entry["price"] - 1) - cost) for cost in COSTS}
        rows.append({
            "candidateId": candidate["candidateId"], "entryArm": ARMS[int(data.arms[sequence[0]])],
            "fold": next(f["fold"] for f in r25.folds() if entry["session"] in f["score"]),
            "session": entry["session"], "opportunity": entry["opportunity"],
            "entryId": eid, "entryMinute": entry["entryMinute"], "entryPrice": entry["price"],
            "exitStatus": "RESOLVED" if chosen else "UNRESOLVED_TERMINAL_EXIT",
            "exitKind": chosen[2] if chosen else None, "exitMinute": exit_minute,
            "exitPrice": exit_price, "missingOrdinaryReferences": missing_refs,
            "activeMinutesHeld": None if exit_minute is None else execution.active_minutes(
                entry["session"], entry["entryMinute"], exit_minute),
            "wallMinutesHeld": None if exit_minute is None else exit_minute - entry["entryMinute"],
            "earlyExitOpportunityCostPp": early, "netReturnPctBySellCost": net,
            "metrics": metrics,
        })
    return rows


def neutral_terminal(data: Data) -> list[dict]:
    dummy = np.full((len(data.sessions), 3), 1e9, dtype=np.float32)
    c = {"candidateId": "HOLD_TO_TERMINAL", "exitThresholdPp": 0.0,
         "persistenceFreshCheckpoints": 1}
    return replay_candidate(data, dummy, c)


METRICS = {
    "lowToHighPct": lambda r: r["metrics"]["opportunityRangePct"],
    "entryToSameOrderedHighPct": lambda r: r["metrics"]["entryToSameOrderedHighPct"],
    "entryToPostEntryBestHighPct": lambda r: r["metrics"]["entryToPostEntryHighPct"],
    "entryToExitGrossPct": lambda r: r["metrics"]["entryToExitGrossPct"],
    "entryToExitNetPct": lambda r: r["netReturnPctBySellCost"]["0.05"],
    "wholeOpportunityCapturePct": lambda r: r["metrics"]["wholeOpportunityCapturePct"],
    "sameHighUpsideCapturePct": lambda r: r["metrics"]["sameHighUpsideCapturePct"],
    "postEntryUpsideCapturePct": lambda r: r["metrics"]["postEntryUpsideCapturePct"],
    "sameHighEvaluatorGapPp": lambda r: r["metrics"]["sameHighEvaluatorGapPp"],
    "postEntryHighEvaluatorGapPp": lambda r: r["metrics"]["postEntryHighEvaluatorGapPp"],
    "ownedPeakGivebackPp": lambda r: r["metrics"]["ownedPeakGivebackPp"],
    "activeMinutesHeld": lambda r: r["activeMinutesHeld"],
    "wallMinutesHeld": lambda r: r["wallMinutesHeld"],
    "earlyExitOpportunityCostPp": lambda r: r["earlyExitOpportunityCostPp"],
    "lateExitGivebackPp": lambda r: r["metrics"]["ownedPeakGivebackPp"],
}


def _bucket(row):
    return row["metrics"]["bucket"] if row["metrics"]["bucket"] in BUCKETS else "NOT_EVALUABLE"


def group_score(rows: list[dict]) -> dict:
    resolved = [r for r in rows if r["exitStatus"] == "RESOLVED"]
    metrics = {name: summary(fn(r) for r in rows) for name, fn in METRICS.items()}
    nets = [r["netReturnPctBySellCost"]["0.05"] for r in rows]
    return {
        "N": len(rows), "resolvedN": len(resolved), "missingN": sum(
            r["missingOrdinaryReferences"] > 0 for r in rows),
        "censoredN": len(rows) - len(resolved), "metrics": metrics,
        "returnRisk": profit_stats(nets),
        "costStress": {f"{c:.2f}": profit_stats(
            r["netReturnPctBySellCost"][f"{c:.2f}"] for r in rows) for c in COSTS},
    }


def _score_population(data: Data) -> dict:
    score_sessions = {s for f in r25.folds() for s in f["score"]}
    result = collections.Counter()
    for oid, record in data.opportunity_records.items():
        if record["session"] not in score_sessions:
            continue
        geometry = _ordered_geometry(record)
        bucket = (opportunity_bucket(100 * (geometry.high / geometry.low - 1))
                  if geometry is not None else "NOT_EVALUABLE")
        result[bucket] += 1
    require(sum(result.values()) > 0, "EMPTY_SCORE_POPULATION")
    return {b: result[b] for b in (*BUCKETS, "NOT_EVALUABLE")}


def full_scorecard(rows: list[dict], data: Data) -> dict:
    out = {"overall": {}, "byFold": {}, "byBucket": {}}
    population = _score_population(data)
    for arm in ARMS:
        arm_rows = [r for r in rows if r["entryArm"] == arm]
        out["overall"][arm] = group_score(arm_rows)
        out["overall"][arm].update(populationN=sum(population.values()),
                                    filledN=len(arm_rows),
                                    noEntryN=sum(population.values()) - len(arm_rows))
        out["byFold"][arm] = {str(f): group_score([r for r in arm_rows if r["fold"] == f])
                              for f in range(1, 5)}
        out["byBucket"][arm] = {}
        for b in (*BUCKETS, "NOT_EVALUABLE"):
            card = group_score([r for r in arm_rows if _bucket(r) == b])
            card.update(populationN=population[b], filledN=card["N"],
                        noEntryN=population[b] - card["N"])
            out["byBucket"][arm][b] = card
    out["paired"] = paired_scorecard(rows)
    return out


def paired_scorecard(rows: list[dict]) -> dict:
    by_arm = {arm: {r["opportunity"]: r for r in rows if r["entryArm"] == arm} for arm in ARMS}
    out = {}
    for bucket in (*BUCKETS, "NOT_EVALUABLE", "ALL"):
        out[bucket] = {}
        common = sorted(set(by_arm[ARMS[0]]) & set(by_arm[ARMS[1]]))
        if bucket != "ALL":
            common = [oid for oid in common if _bucket(by_arm[ARMS[0]][oid]) == bucket]
        for name, fn in METRICS.items():
            deltas = []
            for oid in common:
                a, b = fn(by_arm[ARMS[0]][oid]), fn(by_arm[ARMS[1]][oid])
                if finite(a) and finite(b): deltas.append(b - a)
            out[bucket][name] = summary(deltas)
    return out


def _paired(candidate, neutral, arm, selector=lambda r: True):
    c = {r["opportunity"]: r for r in candidate if r["entryArm"] == arm and selector(r)}
    n = {r["opportunity"]: r for r in neutral if r["entryArm"] == arm and selector(r)}
    return [(c[k], n[k]) for k in sorted(set(c) & set(n))]


def _median_pair(pairs, fn):
    vals = [(fn(a), fn(b)) for a, b in pairs]
    vals = [(a, b) for a, b in vals if finite(a) and finite(b)]
    return (None, None, 0) if not vals else (
        float(np.median([a for a, _ in vals])), float(np.median([b for _, b in vals])), len(vals))


def _quant_pair(pairs, fn, q):
    vals = [(fn(a), fn(b)) for a, b in pairs]
    vals = [(a, b) for a, b in vals if finite(a) and finite(b)]
    return (None, None, 0) if not vals else (percentile([a for a, _ in vals], q),
        percentile([b for _, b in vals], q), len(vals))


def concentration(rows, arm) -> dict:
    positive = [(r, r["netReturnPctBySellCost"]["0.05"]) for r in rows
                if r["entryArm"] == arm and finite(r["netReturnPctBySellCost"]["0.05"])
                and r["netReturnPctBySellCost"]["0.05"] > 0]
    total = sum(v for _, v in positive)
    if total <= 0:
        return {"defined": False, "largestTradeShare": None, "topFiveTradeShare": None,
                "largestSessionShare": None, "pass": False}
    vals = sorted((v for _, v in positive), reverse=True)
    sessions = collections.Counter()
    for r, v in positive: sessions[r["session"]] += v
    result = {"defined": True, "largestTradeShare": vals[0] / total,
              "topFiveTradeShare": sum(vals[:5]) / total,
              "largestSessionShare": max(sessions.values()) / total}
    result["pass"] = (result["largestTradeShare"] <= .25 and
                      result["topFiveTradeShare"] <= .50 and
                      result["largestSessionShare"] <= .35)
    return result


def gate_candidate(rows, neutral, candidate) -> dict:
    detail = {"arms": {}}; capability = {"winner": [], "retention": [], "loss": []}
    passed = True
    bucket_gate = read_json(ROOT / "docs/evidence/phase57-comprehensive-exit-v1/NEW_EXIT_BUCKET_COMPLETION_GATE_R31.json")["bucketCompletionExpectations"]
    for arm in ARMS:
        arm_rows = [r for r in rows if r["entryArm"] == arm]
        resolved = [r for r in arm_rows if r["exitStatus"] == "RESOLVED"]
        coverage = len(resolved) / len(arm_rows) if arm_rows else 0
        primary = summary(r["netReturnPctBySellCost"]["0.05"] for r in arm_rows)
        cost10 = profit_stats(r["netReturnPctBySellCost"]["0.10"] for r in arm_rows)
        cost20 = profit_stats(r["netReturnPctBySellCost"]["0.20"] for r in arm_rows)
        conc = concentration(rows, arm)
        bucket_results = {}
        for bucket, rule in bucket_gate.items():
            br = [r for r in arm_rows if _bucket(r) == bucket]
            net = summary(r["netReturnPctBySellCost"]["0.05"] for r in br)
            cap = summary(r["metrics"]["postEntryUpsideCapturePct"] for r in br)
            ok = (net["mean"] is not None and net["mean"] >= rule["meanNetFloorPct"] and
                  net["median"] is not None and net["median"] >= rule["medianNetFloorPct"] and
                  (rule["medianCaptureFloorPct"] is None or
                   (cap["median"] is not None and cap["median"] >= rule["medianCaptureFloorPct"])))
            bucket_results[bucket] = {"pass": ok, "net": net, "capture": cap, "rule": rule}

        ge5 = lambda r: _bucket(r) == ">=5%"
        pairs = _paired(rows, neutral, arm, ge5)
        ccap, ncap, capn = _median_pair(pairs, lambda r: r["metrics"]["postEntryUpsideCapturePct"])
        cearly, nearly, earlyn = _median_pair(pairs, lambda r: r["earlyExitOpportunityCostPp"])
        winner_agg = (capn > 0 and earlyn > 0 and ccap >= ncap - 10 and cearly <= nearly + .25)
        winner_folds = 0
        for fold in range(1, 5):
            fp = [(a, b) for a, b in pairs if a["fold"] == fold]
            fc, fn, nn = _median_pair(fp, lambda r: r["metrics"]["postEntryUpsideCapturePct"])
            fe, fne, en = _median_pair(fp, lambda r: r["earlyExitOpportunityCostPp"])
            winner_folds += bool(nn and en and fc >= fn - 10 and fe <= fne + .25)
        winner_ok = winner_agg and winner_folds >= 3
        winner_margin = min((ccap - ncap + 10) if capn else -1e99,
                            (nearly + .25 - cearly) if earlyn else -1e99,
                            float(winner_folds - 3))

        pairs_all = _paired(rows, neutral, arm)
        cg, ng, gn = _median_pair(pairs_all, lambda r: r["metrics"]["ownedPeakGivebackPp"])
        improve_folds = 0
        for fold in range(1, 5):
            fg = [(a, b) for a, b in pairs_all if a["fold"] == fold]
            ca, ne, nn = _median_pair(fg, lambda r: r["metrics"]["ownedPeakGivebackPp"])
            improve_folds += bool(nn and ne - ca >= .10)
        retention_ok = gn > 0 and cg <= ng + .10 and improve_folds >= 2
        retention_margin = min((ng + .10 - cg) if gn else -1e99,
                               float(improve_folds - 2))

        cp05, np05, p05n = _quant_pair(pairs_all, lambda r: r["netReturnPctBySellCost"]["0.05"], 5)
        cworst, nworst, worstn = _quant_pair(pairs_all, lambda r: r["netReturnPctBySellCost"]["0.05"], 0)
        robust_folds = 0
        for fold in range(1, 5):
            fl = [(a, b) for a, b in pairs_all if a["fold"] == fold]
            ca, ne, nn = _quant_pair(fl, lambda r: r["netReturnPctBySellCost"]["0.05"], 10)
            robust_folds += bool(nn and ca >= ne)
        loss_ok = (p05n and worstn and cp05 >= np05 + .25 and cworst >= nworst - .25
                   and robust_folds >= 3)
        loss_margin = min((cp05 - np05 - .25) if p05n else -1e99,
                          (cworst - nworst + .25) if worstn else -1e99,
                          float(robust_folds - 3))

        arm_pass = (coverage >= .95 and primary["mean"] is not None and primary["mean"] >= 2.0
                    and all(x["pass"] for x in bucket_results.values())
                    and winner_ok and retention_ok and loss_ok and
                    cost10["profitFactor"] is not None and cost10["profitFactor"] >= 1.0 and
                    cost20["profitFactor"] is not None and cost20["profitFactor"] >= .95 and conc["pass"])
        detail["arms"][arm] = {"pass": arm_pass, "coverage": coverage,
            "primaryMeanNetGate": primary, "bucketGates": bucket_results,
            "winner": {"pass": winner_ok, "candidateCaptureMedian": ccap,
                       "neutralCaptureMedian": ncap, "candidateEarlyCostMedian": cearly,
                       "neutralEarlyCostMedian": nearly, "foldsPassing": winner_folds,
                       "margin": winner_margin},
            "retention": {"pass": retention_ok, "candidateGivebackMedian": cg,
                          "neutralGivebackMedian": ng, "foldsImproved": improve_folds,
                          "margin": retention_margin},
            "loss": {"pass": loss_ok, "candidateP05": cp05, "neutralP05": np05,
                     "candidateWorst": cworst, "neutralWorst": nworst,
                     "foldsP10Noninferior": robust_folds, "margin": loss_margin},
            "cost10": cost10, "cost20": cost20, "concentration": conc}
        passed &= bool(arm_pass)
        capability["winner"].append(winner_margin)
        capability["retention"].append(retention_margin)
        capability["loss"].append(loss_margin)
    detail["pass"] = passed
    detail["capabilityMargins"] = {k: min(v) for k, v in capability.items()}
    return detail


def rank_selection(gates: list[dict]) -> dict:
    passing = [g for g in gates if g["gate"]["pass"]]
    if not passing:
        return {"outcome": "NO_SELECTION_STOP", "selectedCandidateId": None,
                "reason": "NO_CANDIDATE_PASSED_ALL_PRECOMMITTED_R25_R31_GATES"}
    metrics = ("winner", "retention", "loss")
    ranks = {g["candidateId"]: {} for g in passing}
    for metric in metrics:
        ordered = sorted({g["gate"]["capabilityMargins"][metric] for g in passing}, reverse=True)
        for g in passing:
            ranks[g["candidateId"]][metric] = ordered.index(g["gate"]["capabilityMargins"][metric]) + 1
    scored = []
    for g in passing:
        rr = list(ranks[g["candidateId"]].values())
        scored.append((max(rr), sum(rr), tuple(g["gate"]["capabilityMargins"][m] for m in metrics), g))
    scored.sort(key=lambda x: (x[0], x[1], tuple(-v for v in x[2])))
    best = scored[0]
    ties = [x for x in scored if x[:3] == best[:3]]
    if len(ties) != 1:
        return {"outcome": "NO_SELECTION_STOP", "selectedCandidateId": None,
                "reason": "EXACT_SUBSTANTIVE_CAPABILITY_TIE", "tied": [x[3]["candidateId"] for x in ties]}
    return {"outcome": "SELECT", "selectedCandidateId": best[3]["candidateId"],
            "capabilityRanks": ranks[best[3]["candidateId"]],
            "capabilityMargins": best[3]["gate"]["capabilityMargins"]}


def replay_and_score(data: Data, predictions: dict, out: Path) -> dict:
    neutral = neutral_terminal(data)
    write_jsonl_gz(out / "neutral-hold-terminal.jsonl.gz", neutral)
    gates = []; manifest = {}
    for candidate in r25.candidate_grid():
        sid = candidate_spec(candidate)
        rows = replay_candidate(data, predictions[sid], candidate)
        ledger_path = out / "ledgers" / f"{candidate['candidateId']}.jsonl.gz"
        write_jsonl_gz(ledger_path, rows)
        card = full_scorecard(rows, data)
        card_path = out / "scorecards" / f"{candidate['candidateId']}.json"
        write_json(card_path, card)
        gate = gate_candidate(rows, neutral, candidate)
        gates.append({"candidateId": candidate["candidateId"], "predictionSpec": sid,
                      "configuration": candidate, "gate": gate})
        manifest[candidate["candidateId"]] = {"ledgerSha256": sha(ledger_path),
                                             "scorecardSha256": sha(card_path)}
    selection = rank_selection(gates)
    result = {"schema": "phase57-r36-finite-selection-v1", "selection": selection,
              "candidates": gates, "artifactHashes": manifest,
              "candidateConfigurations": 24, "modelFits": 144,
              "providerRequests": 0, "protectedPartitionsOpened": 0,
              "developmentOutcomeExposed": True, "freshOosClaim": False, "safety": SAFETY}
    write_json(out / "selection.json", result)
    return result


def tree_hashes(root: Path) -> dict:
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def run(args) -> dict:
    require(not args.out.exists(), "APPEND_ONLY_OUTPUT_EXISTS")
    args.out.mkdir(parents=True)
    data = build_data(args.core_root, args.out / "data", args.workers)
    predictions, fit_receipt = fit_predictions(data, args.out)
    run_a = args.out / "run-a"; run_b = args.out / "run-b"
    run_a.mkdir(); run_b.mkdir()
    result_a = replay_and_score(data, predictions, run_a)
    result_b = replay_and_score(data, predictions, run_b)
    hashes_a, hashes_b = tree_hashes(run_a), tree_hashes(run_b)
    require(hashes_a == hashes_b, "RUN_AB_NOT_BYTE_IDENTICAL")
    require(result_a == result_b, "RUN_AB_RESULT_DRIFT")
    final = {"schema": "phase57-r36-one-shot-finite-run-receipt-v1",
             "status": result_a["selection"]["outcome"],
             "selection": result_a["selection"], "modelFits": fit_receipt["modelFits"],
             "candidatePoliciesReplayed": 24, "runABByteIdentical": True,
             "runAHashes": hashes_a, "predictionSha256": fit_receipt["predictionSha256"],
             "sourceSha256": sha(Path(__file__)), "providerRequests": 0,
             "protectedPartitionsOpened": 0, "safety": SAFETY}
    write_json(args.out / "receipt.json", final)
    return final


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-root", type=Path, required=True,
                        help="Extracted R35 artifact root containing core-a/core-b")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    require(1 <= args.workers <= 4, "WORKERS_OUT_OF_FROZEN_RANGE")
    print(canonical(run(args)).decode(), end="")


if __name__ == "__main__":
    main()
