"""Independent R41 training/OOF provenance audit, before candidate performance.

No trainer, policy replayer or evaluator is imported. This audit reconstructs
row order, event labels, eligibility and weighting from the immutable sources.
Saved model objects are inspected only as metadata: no fit, predict or transform
method is invoked. Candidate ledgers and returns are never opened.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import warnings

import joblib
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_SHA256 = "5fdc059936ba31466a7dace520f218353c634e6c8444d20d5ab21069c745deb4"
ARMS = ("IMMEDIATE", "ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF")
HEADS = ("CONTINUATION", "FAILURE")
STARTS = np.array([*range(540, 690), *range(750, 925)], dtype=np.int16)
ENDPOINTS = frozenset((STARTS + 1).tolist())
REASONS = ("AVAILABLE", "NO_CONTINUOUS_REFERENCE", "EXACT_ANCHOR_MISSING",
           "EXACT_ANCHOR_INVALID_OPEN", "TARGET_WINDOW_MISSING_BAR", "TARGET_WINDOW_INVALID_OHLC")
SAFETY = dict.fromkeys(("executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
    "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted"), False)
RAW_REL = "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz"
SOURCE_PINS = {
    RAW_REL: "37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b",
    "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/opportunities.json.gz":
        "1138960e489c3403e49f502a7ff7ab1fa1e9ef205910d2d018f2bb938df813ea",
    "docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz":
        "4b9afd72ccfff0b557fb4a5e067ac122ace90ae501d15a79627a89af9554a01e",
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(path):
    with Path(path).open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def read_json(path):
    path = Path(path)
    with (gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz"
          else path.open(encoding="utf-8")) as fh:
        return json.load(fh)


def _price(value):
    return type(value) in (float, int) and np.isfinite(value) and value > 0


def independent_labels(raw_rows, now_values):
    """Direct fixed-calendar window audit, independent of the R41 label module."""
    present = np.zeros(len(STARTS), dtype=bool)
    valid = np.zeros(len(STARTS), dtype=bool)
    prices = np.full((len(STARTS), 4), np.nan, dtype=np.float64)
    lookup = {int(start): index for index, start in enumerate(STARTS)}
    seen = set()
    for row in raw_rows:
        require(len(row) == 7 and type(row[0]) in (int, float)
                and np.isfinite(row[0]) and int(row[0]) == row[0], "RAW_ROW_SCHEMA")
        minute = int(row[0])
        require(minute not in seen, "DUPLICATE_RAW_MINUTE")
        seen.add(minute)
        if minute not in lookup:
            continue  # Auction cannot enter either label window.
        index = lookup[minute]
        present[index] = True
        for column, value in enumerate(row[1:5]):
            if _price(value):
                prices[index, column] = value
        opening, high, low, close = prices[index]
        valid[index] = (np.isfinite(prices[index]).all()
                        and low <= min(opening, close) <= max(opening, close) <= high)
    n = len(now_values)
    targets = np.full((n, 2), np.nan, dtype=np.float32)
    known = np.full((n, 2), -1, dtype=np.int16)
    ends = np.full((n, 2), -1, dtype=np.int16)
    horizons = np.zeros((n, 2), dtype=np.int16)
    reasons = np.zeros((n, 2), dtype=np.uint8)
    for row_index, now in enumerate(now_values):
        require(int(now) in ENDPOINTS, "NON_ENDPOINT_ROW")
        first = int(np.searchsorted(STARTS, now))
        for head, maximum in enumerate((60, 15)):
            last = min(len(STARTS), first + maximum)
            horizons[row_index, head] = last - first
            if first == len(STARTS):
                reasons[row_index, head] = 1
                continue
            ends[row_index, head] = STARTS[last - 1] + 1
            anchor = prices[first, 0]
            reason = 2 if not present[first] else 3 if not np.isfinite(anchor) else 0
            if not reason:
                bad = np.flatnonzero(~valid[first:last])
                if len(bad):
                    reason = 4 if not present[first + int(bad[0])] else 5
            reasons[row_index, head] = reason
            if reason:
                continue
            targets[row_index, head] = (np.max(prices[first:last, 1]) >= anchor * 1.01
                                       if head == 0 else np.min(prices[first:last, 2]) <= anchor * 0.9925)
            known[row_index, head] = ends[row_index, head]
    return {"targets": targets, "available": np.isfinite(targets), "knownAt": known,
            "windowEnd": ends, "horizonBars": horizons, "reasonCode": reasons}


def check_label_arrays(saved, expected, now):
    require(set(saved) == set(expected), "LABEL_NPZ_KEYS")
    for name, values in expected.items():
        require(saved[name].shape == values.shape, "LABEL_SHAPE:" + name)
        require(np.array_equal(saved[name], values, equal_nan=True), "LABEL_CONTENT:" + name)
    available = saved["available"]
    require(available.dtype == np.bool_, "LABEL_MASK_NOT_BOOLEAN")
    require(np.all(np.isnan(saved["targets"][~available])), "MISSING_LABEL_NOT_NAN")
    require(np.all(np.isin(saved["targets"][available], [0, 1])), "LABEL_NOT_BINARY")
    require(np.all(saved["knownAt"][available] > np.broadcast_to(now[:, None], available.shape)[available]),
            "LABEL_NOT_AFTER_NOW")
    require(np.all(saved["knownAt"][available] <= 925), "LABEL_MATURES_AFTER_SESSION")
    require(np.all(np.isnan(saved["targets"][now == 925])), "TERMINAL_LABEL_PRESENT")


def check_oof(predictions, expected_specs, scored, n):
    require(set(predictions) == set(expected_specs), "OOF_SPEC_KEYS")
    for name, values in predictions.items():
        require(values.shape == (n, 2), "OOF_SHAPE:" + name)
        require(values.dtype == np.float32, "OOF_DTYPE:" + name)
        require(np.all(np.isfinite(values[scored])), "OOF_MISSING_SCORE:" + name)
        require(np.all((values[scored] >= 0) & (values[scored] <= 1)), "OOF_OUT_OF_RANGE:" + name)
        require(np.all(np.isnan(values[~scored])), "OOF_OUTSIDE_SCORE_FOLD_OR_TERMINAL:" + name)


def expected_weights(session, entry):
    """Equal eligible sessions, then entries, then checkpoint rows; mean one."""
    entries, first, inverse, counts = np.unique(entry, return_index=True, return_inverse=True, return_counts=True)
    entry_sessions = session[first]
    session_ids, n_opps = np.unique(entry_sessions, return_counts=True)
    opps = dict(zip(session_ids.tolist(), n_opps.tolist()))
    weight = np.array([1.0 / opps[int(s)] for s in session]) / counts[inverse]
    weight /= weight.mean()
    require(np.all(np.isfinite(weight)) and np.all(weight > 0), "WEIGHT_INVALID")
    session_totals = np.array([weight[session == s].sum() for s in session_ids])
    require(np.allclose(session_totals, len(weight) / len(session_ids), rtol=1e-12, atol=1e-9),
            "SESSION_WEIGHT_IMBALANCE")
    for s in session_ids:
        totals = np.bincount(inverse, weights=weight)[entry_sessions == s]
        require(np.allclose(totals, totals[0], rtol=1e-12, atol=1e-9), "ENTRY_WEIGHT_IMBALANCE")
    return {"rows": len(weight), "sessions": len(session_ids), "opportunities": len(entries),
            "mean": float(weight.mean()), "sum": float(weight.sum()),
            "weightSha256": hashlib.sha256(weight.astype("<f8").tobytes()).hexdigest()}


def _r35(core_root, protocol):
    a, b = (read_json(core_root / variant / "manifest.json") for variant in ("core-a", "core-b"))
    require(a["outputHashes"] == b["outputHashes"], "R35_AB_HASH_MANIFEST")
    for variant, manifest in (("core-a", a), ("core-b", b)):
        require(manifest["projectionSha256"] == protocol["features"]["r35ProjectionSha256"], "R35_PROJECTION")
        require(manifest["fitContractSha256"] == protocol["features"]["coreFitContractSha256"], "R35_FIT_CONTRACT")
        require(manifest["safety"] == SAFETY, "R35_SAFETY")
        for relative, expected in manifest["outputHashes"].items():
            require(not Path(relative).is_absolute() and ".." not in Path(relative).parts, "R35_UNSAFE_PATH")
            require(sha(core_root / variant / relative) == expected, "R35_FILE_HASH:" + relative)
    sessions = sorted(Path(relative).name.removesuffix(".jsonl.gz") for relative in a["outputHashes"]
                      if relative.startswith("checkpoints/"))
    require(len(sessions) == 58 and len(a["outputHashes"]) == 60, "R35_FILE_POPULATION")
    return a, sessions, read_json(core_root / "core-a/columns.json")


def _load_source_rows(gen2_root, core_root, protocol, names, columns):
    envelopes = read_json(core_root / "core-a/entry-envelopes.json.gz")
    require(set(envelopes) == set(ARMS), "ENVELOPE_ARMS")
    cohorts = [{r["opportunity"] for r in envelopes[a]} for a in ARMS]
    require(cohorts[0] == cohorts[1] and len(cohorts[0]) == 2155, "DEVELOPMENT_COHORT")
    entry_rows = {f"{arm}::{r['entryId']}": r for arm in ARMS for r in envelopes[arm] if r["entryId"] is not None}
    require(len(entry_rows) == 3848, "ENTRY_ENVELOPE_FILLS")
    entry_names = sorted(entry_rows)
    entry_code = {s: i for i, s in enumerate(entry_names)}
    representation = read_json(gen2_root / "data/categorical-representation.json")
    require(representation["ordinalFeature"] is False and representation["preprocessingFitted"] is False,
            "CATEGORY_REPRESENTATION_BOUNDARY")
    maps = representation["maps"]
    require(set(maps) == set(columns["categorical"]), "CATEGORY_REPRESENTATION_COLUMNS")
    sessions = np.empty(656247, dtype=np.int16); arms = np.empty(656247, dtype=np.int8)
    entries = np.empty(656247, dtype=np.int32); now = np.empty(656247, dtype=np.int16)
    cats = np.empty((656247, 21), dtype=np.int16); nums = np.empty((656247, 86), dtype=np.float32)
    observed_levels = [set() for _ in range(21)]
    by_opportunity = collections.defaultdict(list)
    cursor = 0
    with gzip.open(gen2_root / "data/source-row-identity.jsonl.gz", "rt", encoding="utf-8") as identity:
        for session_code, session in enumerate(names):
            with gzip.open(core_root / "core-a/checkpoints" / f"{session}.jsonl.gz", "rt", encoding="utf-8") as fh:
                rows = [json.loads(line) for line in fh]
            rows.sort(key=lambda r: (ARMS.index(r["identity"][0]), r["identity"][1], r["identity"][2]))
            previous = None
            for row in rows:
                arm, eid, minute = row["identity"]
                key = (arm, eid, minute)
                require(key != previous and row["session"] == session, "R35_DUPLICATE_OR_SESSION")
                previous = key
                record = {"index": cursor, "session": session, "arm": arm, "entryId": eid, "now": minute}
                require(json.loads(next(identity)) == record, "ROW_IDENTITY_ORDER_OR_VALUE")
                require(cursor < 656247, "EXTRA_CORE_ROW")
                entry_key = f"{arm}::{eid}"
                entry = entry_rows[entry_key]
                require(entry["session"] == session and minute > entry["entryMinute"]
                        and minute in ENDPOINTS, "ENTRY_CHECKPOINT_GEOMETRY")
                sessions[cursor] = session_code; arms[cursor] = ARMS.index(arm)
                entries[cursor] = entry_code[entry_key]; now[cursor] = minute
                require(len(row["categorical"]) == 21 and len(row["numeric"]) == 83, "SOURCE_FEATURE_DIMENSIONS")
                for j, value in enumerate(row["categorical"]):
                    cats[cursor, j] = maps[columns["categorical"][j]][value]
                    observed_levels[j].add(value)
                nums[cursor, :83] = [np.nan if value is None else value for value in row["numeric"]]
                remaining = len(STARTS) - int(np.searchsorted(STARTS, minute))
                nums[cursor, 83:] = [remaining, min(60, remaining), min(15, remaining)]
                oid = "|".join(eid.split("|")[:2])
                require(oid == entry["opportunity"], "ENTRY_OPPORTUNITY_ID")
                by_opportunity[oid].append(cursor)
                cursor += 1
        require(next(identity, None) is None, "EXTRA_IDENTITY_ROW")
    require(cursor == 656247, "MISSING_CORE_ROWS")
    for j, name in enumerate(columns["categorical"]):
        require(maps[name] == {v: i for i, v in enumerate(sorted(observed_levels[j]))}, "CATEGORY_CODE_MAP:" + name)
    require(np.bincount(arms).tolist() == [345893, 310354], "ARM_ROW_COUNTS")
    return sessions, arms, entries, now, cats, nums, by_opportunity, cohorts[0]


def audit_data(gen2_root: Path, core_root: Path, protocol: dict) -> dict:
    gen2_root, core_root = Path(gen2_root), Path(core_root)
    require(sha(gen2_root / "protocol.json") == PROTOCOL_SHA256
            and read_json(gen2_root / "protocol.json") == protocol, "IMMUTABLE_PROTOCOL")
    require(protocol["entryArms"] == list(ARMS), "FROZEN_ARMS")
    prepared = read_json(gen2_root / "prepare-receipt.json")
    execution = read_json(gen2_root / "execution-identity.json")
    require(prepared["sourceSha256"] == execution["sourceSha256"], "SOURCE_MANIFEST_IDENTITY")
    for relative, expected in prepared["sourceSha256"].items():
        require(not Path(relative).is_absolute() and ".." not in Path(relative).parts, "SOURCE_UNSAFE_PATH")
        require(sha(ROOT / relative) == expected, "EXECUTION_SOURCE_HASH:" + relative)
    for relative, expected in prepared["preparedDataHashes"].items():
        require(sha(gen2_root / relative) == expected, "PREPARED_DATA_HASH:" + relative)
    data_receipt = read_json(gen2_root / "data/data-receipt.json")
    require(data_receipt["sourceHashes"] == SOURCE_PINS, "DATA_SOURCE_PINS")
    for relative, expected in SOURCE_PINS.items():
        require(sha(ROOT / relative) == expected, "RAW_SOURCE_HASH:" + relative)
    for relative, expected in data_receipt["outputHashes"].items():
        require(sha(gen2_root / "data" / relative) == expected, "DATA_OUTPUT_HASH:" + relative)
    for receipt in (prepared, data_receipt):
        require(receipt["safety"] == SAFETY and receipt["providerRequests"] == 0
                and receipt["protectedPartitionsOpened"] == 0 and receipt["modelFits"] == 0,
                "PREPARATION_BOUNDARY")
    r35, session_names, columns = _r35(core_root, protocol)
    require(data_receipt["categoricalColumns"] == columns["categorical"] and len(columns["categorical"]) == 21,
            "CATEGORICAL21")
    require(data_receipt["numericColumns"] == columns["numeric"] + protocol["features"]["calendarFields"]
            and len(data_receipt["numericColumns"]) == 86, "NUMERIC86")
    require(data_receipt["patternColumns"] == protocol["features"]["patternNames"]
            and len(data_receipt["patternColumns"]) == 187, "PATTERN187")
    require(data_receipt["targetColumns"] == list(HEADS) and data_receipt["labelAvailabilityUsedAsFeature"] is False
            and data_receipt["independentHeadMasks"] is True, "TARGET_BOUNDARY")
    sessions, arms, entries, now, cats, nums, groups, cohort = _load_source_rows(
        gen2_root, core_root, protocol, session_names, columns)
    n = len(now)
    with np.load(gen2_root / "data/training-labels.npz", allow_pickle=False) as saved:
        labels = {k: saved[k] for k in saved.files}
    expected = {name: np.empty_like(value) for name, value in labels.items()}
    require(set(expected) == {"targets", "available", "knownAt", "windowEnd", "horizonBars", "reasonCode"},
            "LABEL_NPZ_KEYS")
    raw_all = read_json(ROOT / RAW_REL)
    require(cohort <= set(raw_all), "RAW_COHORT_MISSING")
    unique_keys = 0
    for oid, index in groups.items():
        index = np.asarray(index)
        unique_now, inverse = np.unique(now[index], return_inverse=True)
        result = independent_labels(raw_all[oid]["today"], unique_now)
        for name in expected:
            expected[name][index] = result[name][inverse]
        unique_keys += len(unique_now)
    del raw_all
    require(unique_keys == 345893, "UNIQUE_OPPORTUNITY_NOW_KEYS")
    check_label_arrays(labels, expected, now)
    reason_receipt = read_json(gen2_root / "data/training-label-reasons.json")
    require(reason_receipt["reasonCodes"] == {str(i): r for i, r in enumerate(REASONS)}, "REASON_CODE_MAPPING")
    require(reason_receipt["labelsSha256"] == sha(gen2_root / "data/training-labels.npz")
            and reason_receipt["sourceRowIdentitySha256"] == sha(gen2_root / "data/source-row-identity.jsonl.gz"),
            "LABEL_REASON_HASH_RECEIPT")
    for a, arm in enumerate(ARMS):
        mask = arms == a
        for h, head in enumerate(HEADS):
            counts = {"total": int(mask.sum()), "available": int(labels["available"][mask, h].sum()),
                "zero": int(np.sum(labels["targets"][mask, h] == 0)),
                "one": int(np.sum(labels["targets"][mask, h] == 1)),
                "reasonCounts": {r: int(np.sum(labels["reasonCode"][mask, h] == i)) for i, r in enumerate(REASONS)}}
            require(reason_receipt["countsByArmHead"][arm][head] == counts, "LABEL_REASON_COUNTS")

    session_code = {s: i for i, s in enumerate(session_names)}
    support = read_json(gen2_root / "support-gate.json")
    require(support["status"] == "PASS_BEFORE_ANY_FIT" and support["modelFits"] == 0
            and support["fallback"] is False, "SUPPORT_GATE_STATUS")
    support_rows, slices, weight_rows = [], {}, []
    score_seen = set()
    for fold in protocol["split"]["folds"]:
        train_days, purge_days, score_days = map(set, (fold["train"], fold["purge"], fold["score"]))
        require(not (train_days & purge_days or train_days & score_days or purge_days & score_days), "FOLD_OVERLAP")
        require(not score_seen & score_days, "DUPLICATE_SCORE_FOLD")
        require(len(purge_days) == 2 and max(train_days) < min(purge_days) < min(score_days), "CAUSAL_FOLD_ORDER")
        require(max(session_code[s] for s in train_days) + 3 == min(session_code[s] for s in score_days),
                "TWO_SESSION_PURGE")
        score_seen |= score_days
        for a, arm in enumerate(ARMS):
            score_mask = (arms == a) & np.isin(sessions, [session_code[s] for s in score_days]) & (now != 925)
            base = (arms == a) & np.isin(sessions, [session_code[s] for s in train_days])
            for h, head in enumerate(HEADS):
                train = np.flatnonzero(base & labels["available"][:, h])
                values = labels["targets"][train, h]
                row = {"fold": fold["fold"], "arm": arm, "head": head, "trainRows": len(train),
                    "scoreRows": int(score_mask.sum()), "classRows": {"0": int(np.sum(values == 0)), "1": int(np.sum(values == 1))},
                    "opportunities": len(np.unique(entries[train])), "sessions": len(np.unique(sessions[train]))}
                gate = protocol["supportGate"]
                require(row["trainRows"] >= gate["minimumRowsPerFoldArmHead"]
                        and min(row["classRows"].values()) >= gate["minimumClassRows"]
                        and row["opportunities"] >= gate["minimumOpportunities"]
                        and row["sessions"] >= gate["minimumSessions"], "SUPPORT_GATE_FAILED")
                support_rows.append(row)
                slices[(fold["fold"], arm, head)] = (row, train)
                weight_rows.append({"fold": fold["fold"], "arm": arm, "head": head,
                                    **expected_weights(sessions[train], entries[train])})
    require(len(score_seen) == 34 and len(support_rows) == 16, "FOLD_OR_SLICE_COUNT")
    require(support["slices"] == support_rows, "SUPPORT_SLICE_RECONSTRUCTION")
    fit = read_json(gen2_root / "fit-receipt.json")
    require(fit["modelFits"] == 64 and fit["heads"] == list(HEADS) and fit["predictionSpecs"] == 4, "FIT_BUDGET")
    require(fit["safety"] == SAFETY and fit["providerRequests"] == fit["protectedPartitionsOpened"] == 0, "FIT_BOUNDARY")
    require(sha(gen2_root / "oof-predictions.npz") == fit["predictionSha256"], "PREDICTION_HASH")
    specs = {s["specId"]: s for s in protocol["predictionSpecs"]}
    scored = np.isin(sessions, [session_code[s] for s in score_seen]) & (now != 925)
    with np.load(gen2_root / "oof-predictions.npz", allow_pickle=False) as predictions:
        check_oof(predictions, specs, scored, n)

    model_rows = fit["models"]
    expected_identities = {(sid, f["fold"], arm, head) for sid in specs
                           for f in protocol["split"]["folds"] for arm in ARMS for head in HEADS}
    require(len(model_rows) == 64 and {(m["spec"], m["fold"], m["arm"], m["head"]) for m in model_rows}
            == expected_identities, "MODEL_IDENTITIES")
    require({p.name for p in (gen2_root / "models").iterdir()} == {m["file"] for m in model_rows}, "MODEL_FILE_SET")
    warning_messages = set()
    preprocess_expected = {}
    for ordinal, model_row in enumerate(model_rows, 1):
        require(model_row["ordinal"] == ordinal, "MODEL_ORDINAL")
        path = gen2_root / "models" / model_row["file"]
        require(sha(path) == model_row["sha256"], "MODEL_FILE_HASH")
        slice_key = (model_row["fold"], model_row["arm"], model_row["head"])
        row, train = slices[slice_key]
        require(model_row["trainRows"] == row["trainRows"] and model_row["scoreRows"] == row["scoreRows"], "MODEL_SUPPORT_COUNTS")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            bundle = joblib.load(path)
        warning_messages.update(type(w.message).__name__ for w in caught)
        spec = specs[model_row["spec"]]
        require(bundle["spec"] == spec and bundle["fold"] == model_row["fold"]
                and bundle["arm"] == model_row["arm"] and bundle["head"] == model_row["head"], "MODEL_BUNDLE_IDENTITY")
        require(bundle["categoricalNames"] == data_receipt["categoricalColumns"]
                and bundle["numericNames"] == data_receipt["numericColumns"], "MODEL_FEATURE_NAMES")
        include_pattern = spec["featureSet"] == "CORE_CALENDAR_PATTERN187"
        require(bundle["patternNames"] == (data_receipt["patternColumns"] if include_pattern else []), "MODEL_PATTERN_NAMES")
        require(bundle["categoricalRepresentation"] == "data/categorical-representation.json", "MODEL_CATEGORY_MAP")
        model, encoder, imputer, scaler = (bundle[k] for k in ("model", "encoder", "imputer", "scaler"))
        require(model.classes_.tolist() == [0, 1] and model.n_features_in_ == model_row["featureColumns"], "MODEL_CLASSES_OR_DIMENSION")
        parameters = model.get_params(deep=False)
        require(all(parameters[k] == v for k, v in spec["parameters"].items()), "MODEL_PARAMETER_DRIFT")
        require(encoder.n_features_in_ == 21 and encoder.handle_unknown == "ignore", "ENCODER_PARAMETERS")
        if slice_key not in preprocess_expected:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                medians = np.nanmedian(nums[train], axis=0)
            medians[np.isnan(medians)] = 0
            preprocess_expected[slice_key] = (
                [np.unique(cats[train, j]) for j in range(21)], medians,
                np.flatnonzero(np.isnan(nums[train]).any(axis=0)))
        expected_categories, medians, expected_missing = preprocess_expected[slice_key]
        for j, observed in enumerate(encoder.categories_):
            require(np.array_equal(observed, expected_categories[j]), "ENCODER_TRAIN_ONLY_CATEGORIES")
        require(imputer.n_features_in_ == (273 if include_pattern else 86) and imputer.strategy == "median"
                and imputer.add_indicator is True and imputer.keep_empty_features is True, "IMPUTER_PARAMETERS")
        # Only CORE+calendar statistics are reconstructed; Pattern187 values are
        # intentionally not regenerated in this post-run audit.
        require(np.array_equal(imputer.statistics_[:86], medians), "IMPUTER_CORE_TRAIN_ONLY_MEDIANS")
        require(np.array_equal(imputer.indicator_.features_[imputer.indicator_.features_ < 86], expected_missing),
                "IMPUTER_CORE_TRAIN_ONLY_MISSING_INDICATORS")
        if spec["family"] == "LOGISTIC":
            require(scaler is not None and scaler.with_mean is False
                    and int(scaler.n_samples_seen_) == row["trainRows"], "SCALER_TRAIN_ONLY_COUNT")
        else:
            require(scaler is None, "HGB_UNEXPECTED_SCALER")
    journal = [json.loads(line) for line in (gen2_root / "fit-progress.jsonl").read_text().splitlines()]
    require(len(journal) == 128, "FIT_JOURNAL_COUNT")
    for i, model in enumerate(model_rows):
        for offset, status in ((0, "FIT_ATTEMPT_STARTED"), (1, "FIT_AND_BUNDLE_COMPLETED")):
            saved = journal[2 * i + offset]
            require(saved["status"] == status and all(saved[k] == model[k] for k in ("ordinal", "spec", "fold", "arm", "head")),
                    "FIT_JOURNAL_IDENTITY")
            if offset:
                require(saved["sha256"] == model["sha256"], "FIT_JOURNAL_MODEL_HASH")
    return {"schemaVersion": "phase57-exit-gen2-data-audit-r43-v1", "status": "PASS",
        "protocolSha256": PROTOCOL_SHA256, "executionHead": prepared["executionHead"],
        "rows": n, "rowsByArm": dict(zip(ARMS, map(int, np.bincount(arms)))),
        "sessions": len(session_names), "scoreSessions": len(score_seen), "supportSlices": len(support_rows),
        "uniqueOpportunityNowKeys": unique_keys, "labelsIndependentlyReconstructedAllRows": True,
        "independentHeadMasks": True, "terminalLabelsNull": True, "featureDimensions": [21, 86, 187],
        "oofSpecs": len(specs), "oofScoredRows": int(scored.sum()), "oofNaNRows": int((~scored).sum()),
        "predictionSha256": fit["predictionSha256"], "modelBundlesVerified": 64,
        "fitJournalVerifiedRows": len(journal), "weights": weight_rows,
        "modelMetadataOnly": True, "modelPredictionCalls": 0, "modelFitCalls": 0,
        "candidatePerformanceInspected": False, "candidateLedgersOpened": 0,
        "localSklearnVersion": importlib.metadata.version("scikit-learn"),
        "artifactSklearnVersion": prepared["dependencies"]["scikit-learn"],
        "metadataDeserializationWarningClasses": sorted(warning_messages),
        "limits": ["Pattern187 full feature matrix was not regenerated; source identity and saved model feature names verified",
                   "Actual sample-weight arrays were not persisted; eligible masks/weights independently reconstructed and frozen source verified",
                   "Model bundles inspected as attributes only in local runtime; no estimator computation performed"],
        "providerRequests": 0, "protectedPartitionsOpened": 0, "safety": SAFETY}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gen2-root", type=Path, required=True)
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "APPEND_ONLY_OUTPUT_EXISTS")
    result = audit_data(args.gen2_root, args.core_root, read_json(args.gen2_root / "protocol.json"))
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "receipt.json").write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "rows", "supportSlices", "modelBundlesVerified", "candidatePerformanceInspected")}, sort_keys=True))


if __name__ == "__main__":
    main()
