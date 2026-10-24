#!/usr/bin/env python3
"""Replay selected complete original watches from raw bars through P1/Q70.

Selection uses WATCH_RECORDS order and the original outer-test sessions only.
Saved feature matrices, OOF scores and first intents are comparison artifacts,
never feature or decision inputs. This is a historical sample with complete
watch coverage, not a full raw-feature replay or a model dispatch for 2026.
"""
import argparse
from collections import Counter
from datetime import datetime
import gzip
import json
import math
from pathlib import Path
import sys

import no11_frozen_p1_feature_runtime as features
import no11_frozen_p1_score_replay as core


def check(ok, code):
    core.check(ok, "P1_RAW_" + code)


def json_lines(path):
    with gzip.open(path, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            check(isinstance(row, dict), "JSONL_OBJECT_REQUIRED")
            yield row


def select_watches(watches, ranges, test_sessions, per_fold=1):
    """Predeclare whole watches without reading scores, labels or intents."""
    check(type(per_fold) is int and 1 <= per_fold <= 20, "SAMPLE_COUNT_INVALID")
    check(getattr(ranges, "shape", None) == (len(watches), 2)
          and ranges.dtype.kind in "iu", "WATCH_RANGES_INVALID")
    sessions = {}
    for fold, days in test_sessions.items():
        for day in days:
            check(day not in sessions, "SAVED_TEST_SESSIONS_OVERLAP")
            sessions[day] = fold
    selected = []
    counts = Counter()
    previous_hi = 0
    seen = set()
    for wi, watch in enumerate(watches):
        lo, hi = map(int, ranges[wi])
        check(lo == previous_hi and hi >= lo, "WATCH_RANGES_NOT_CONTIGUOUS")
        previous_hi = hi
        key = watch.get("watch_key")
        check(isinstance(key, str) and key not in seen
              and key == watch.get("session", "") + "|" + watch.get("symbol", ""),
              "WATCH_IDENTITY_INVALID")
        seen.add(key)
        check(type(watch.get("canonical")) is bool, "WATCH_CANONICAL_INVALID")
        if not watch["canonical"]:
            continue
        check(watch["session"] in sessions, "CANONICAL_SESSION_OUTSIDE_FROZEN_SPLIT")
        fold = sessions[watch["session"]]
        if hi > lo and counts[fold] < per_fold:
            selected.append({"watch_index": wi, "watch": watch, "lo": lo, "hi": hi, "fold": fold})
            counts[fold] += 1
    check(set(counts) == set(test_sessions)
          and all(n == per_fold for n in counts.values()), "WHOLE_WATCH_SAMPLE_INCOMPLETE")
    return selected


def selected_grid(path, selected):
    wanted = {}
    output = {}
    for item in selected:
        wi = item["watch_index"]
        output[wi] = []
        for index in range(item["lo"], item["hi"]):
            check(index not in wanted, "SELECTED_RANGES_OVERLAP")
            wanted[index] = item
    for index, row in enumerate(json_lines(path)):
        item = wanted.get(index)
        if item is None:
            continue
        watch = item["watch"]
        check(row.get("canonical") is True and row.get("watch_index") == item["watch_index"]
              and all(row.get(k) == watch[k] for k in ("watch_key", "session", "symbol")),
              "SELECTED_GRID_WATCH_MISMATCH")
        output[item["watch_index"]].append(row)
    check(all(len(output[x["watch_index"]]) == x["hi"] - x["lo"] for x in selected),
          "WHOLE_WATCH_GRID_COVERAGE_INCOMPLETE")
    return output


def derive_first_intent(item, grid, scores, threshold, test_sessions):
    """Complete-watch first crossing; expected-intent files are not arguments."""
    watch, fold = item["watch"], item["fold"]
    check(fold in test_sessions and watch["session"] in test_sessions[fold],
          "SESSION_OUTSIDE_FROZEN_SPLIT")
    check(len(grid) == len(scores) == item["hi"] - item["lo"] > 0,
          "WHOLE_WATCH_DECISION_COVERAGE_INCOMPLETE")
    check(math.isfinite(threshold) and 0 <= threshold <= 1, "THRESHOLD_INVALID")
    result = {"session": watch["session"], "symbol": watch["symbol"],
              "scoring_decisions": 0, "first_intent": None, "rows_after_lock": 0}
    last_time = None
    for offset, (row, value) in enumerate(zip(grid, scores)):
        check(row.get("canonical") is True
              and all(row.get(k) == watch[k] for k in ("watch_key", "session", "symbol")),
              "DECISION_WATCH_MISMATCH")
        timestamp = row.get("intent_timestamp")
        try:
            instant = datetime.fromisoformat(timestamp)
            maximum = datetime.fromisoformat(row["feature_max_timestamp"])
        except (TypeError, ValueError, KeyError):
            raise ValueError("P1_RAW_GRID_CLOCK_INVALID") from None
        check(instant.utcoffset() is not None and maximum.utcoffset() is not None,
              "GRID_CLOCK_WITHOUT_TIMEZONE")
        check(maximum <= instant and instant.date().isoformat() == watch["session"]
              and (last_time is None or last_time < instant), "GRID_NOT_CAUSAL_OR_CHRONOLOGICAL")
        minute = instant.hour * 60 + instant.minute
        check(row.get("intent_minute") == minute and row.get("closed_raw_start") == minute - 1,
              "GRID_BAR_END_MISMATCH")
        last_time = instant
        score = float(value)
        check(math.isfinite(score) and 0 <= score <= 1, "SCORE_INVALID")
        if result["first_intent"] is not None:
            result["rows_after_lock"] += 1
            continue
        result["scoring_decisions"] += 1
        # No tolerance is applied to the actual decision.
        if score >= threshold:
            result["first_intent"] = {
                "row_index": item["lo"] + offset, "fold": fold,
                "intent_timestamp": timestamp, "score": score, "threshold": float(threshold),
            }
    return result


def compare_first_intents(path, actual):
    """Read expected intents only after every actual decision has completed."""
    mismatch = Counter({k: 0 for k in (
        "missingExpectedWatch", "duplicateExpectedWatch", "watchIdentity", "scoringDecisions",
        "firstIntentPresence", "row_index", "fold", "intent_timestamp", "score", "threshold")})
    seen = set()
    for row in json_lines(path):
        if row.get("family") != "P1" or row.get("policy") != "Q70" or row.get("watch_key") not in actual:
            continue
        key = row["watch_key"]
        if key in seen:
            mismatch["duplicateExpectedWatch"] += 1
            continue
        seen.add(key)
        observed = actual[key]
        mismatch["watchIdentity"] += int(any(row.get(k) != observed[k] for k in ("session", "symbol")))
        mismatch["scoringDecisions"] += int(row.get("scoring_decisions") != observed["scoring_decisions"])
        check("first_intent" in row, "EXPECTED_FIRST_INTENT_MISSING")
        expected, first = row["first_intent"], observed["first_intent"]
        check(expected is None or isinstance(expected, dict), "EXPECTED_FIRST_INTENT_INVALID")
        if (expected is None) != (first is None):
            mismatch["firstIntentPresence"] += 1
        elif first is not None:
            for field in ("row_index", "fold", "intent_timestamp"):
                mismatch[field] += int(expected.get(field) != first[field])
            for field in ("score", "threshold"):
                value = expected.get(field)
                check(type(value) in (int, float) and math.isfinite(value), "EXPECTED_SCORE_INVALID")
                mismatch[field] += int(abs(value - first[field]) > core.ATOL)
    mismatch["missingExpectedWatch"] = len(set(actual) - seen)
    return {"scope": "SELECTED_COMPLETE_WATCHES_ONLY", "comparedWatches": len(seen),
            "firstIntents": sum(x["first_intent"] is not None for x in actual.values()),
            "noIntents": sum(x["first_intent"] is None for x in actual.values()),
            "scoringDecisions": sum(x["scoring_decisions"] for x in actual.values()),
            "rowsAfterFirstIntentLock": sum(x["rows_after_lock"] for x in actual.values()),
            "mismatches": dict(mismatch), "parityPassed": not any(mismatch.values())}


def run_replay(spec, paths, raw_paths, per_fold, report):
    import numpy as np
    import scipy
    import sklearn
    from threadpoolctl import threadpool_limits
    check(sklearn.__version__ == "1.8.0", "REQUIRES_SCIKIT_LEARN_1_8_0")
    report["environment"] = {"python": sys.version.split()[0], "numpy": np.__version__,
                             "scipy": scipy.__version__, "scikitLearn": sklearn.__version__}
    base, corrected = paths["base"], paths["corrected"]
    watches = list(json_lines(base["WATCH_RECORDS.jsonl.gz"]))
    ranges = np.load(raw_paths["watch_ranges"], allow_pickle=False)
    selected = select_watches(watches, ranges, spec["test_sessions"], per_fold)
    grids = selected_grid(base["PERSISTENT_GRID.jsonl.gz"], selected)
    with gzip.open(raw_paths["raw_paths"], "rt", encoding="utf-8") as source:
        raw = json.load(source)
    with gzip.open(raw_paths["source_tokens"], "rt", encoding="utf-8") as source:
        tokens = json.load(source)
    runtime = features.load_feature_runtime(np=np)
    primitives = core.inference_primitives(spec["source"], np)
    actual_intents, predictions = {}, []
    feature_error = 0.0
    numeric_mismatches = missing_mismatches = category_mismatches = 0
    # Matrices are opened as comparison references, never passed to a scorer.
    x = np.load(base["PRIVATE_INPUTS/features_numeric.npy"], allow_pickle=False, mmap_mode="r")
    c = np.load(base["PRIVATE_INPUTS/features_categories.npy"], allow_pickle=False, mmap_mode="r")
    check(x.shape == (int(ranges[-1, 1]), 148) and x.dtype == np.float64
          and c.shape == (len(x), 15) and c.dtype == np.int32, "REFERENCE_FEATURE_SHAPE")
    report["folds"] = []
    overlap = Counter()
    source_counts = Counter()
    unknown_counts = [0] * 15
    kernel_steps = 0
    with threadpool_limits(limits=2):
        for fold in sorted(spec["test_sessions"]):
            model = core.FrozenP1Fold(fold, spec, corrected, primitives, np)
            executed = False
            fold_report = {"fold": fold, "watches": 0, "rows": 0}
            report["folds"].append(fold_report)
            for item in (s for s in selected if s["fold"] == fold):
                wi, watch, lo, hi = item["watch_index"], item["watch"], item["lo"], item["hi"]
                key = watch["watch_key"]
                overlap.update(features.verify_saved_compact_overlap(raw[key], tokens[key]))
                actual_wi, numeric, named, meta, receipt = features.compute_watch_features(
                    runtime, watch, raw[key], tokens[key], watch_index=wi)
                grid = grids[wi]
                check(actual_wi == wi and len(numeric) == len(named) == len(meta) == len(grid) == hi - lo,
                      "REBUILT_WATCH_RANGE_MISMATCH")
                check(all(m["intent_minute"] == r["intent_minute"] for m, r in zip(meta, grid)),
                      "REBUILT_GRID_CLOCK_MISMATCH")
                # Predictions consume the newly computed raw-derived values.
                encoded, unseen = model.encode_named_categories(named)
                pred, pct, score = model.score_named_batch(numeric, named)
                if not executed:
                    report["originalP1ModelsExecuted"] += 3
                    executed = True
                unknown_counts = [a + b for a, b in zip(unknown_counts, unseen)]
                actual_intents[key] = derive_first_intent(
                    item, grid, score, model.calibration["thresholds"]["Q70"], spec["test_sessions"])
                predictions.append({"item": item, "pred": pred, "pct": pct, "score": score})
                # Saved features are read only after actual inference/decisions.
                expected_x = x[lo:hi]
                missing_mismatches += int(np.count_nonzero(np.isnan(numeric) != np.isnan(expected_x)))
                same = (numeric == expected_x) | (np.isnan(numeric) & np.isnan(expected_x))
                numeric_mismatches += int(np.count_nonzero(~same))
                finite = np.isfinite(numeric) & np.isfinite(expected_x)
                if finite.any():
                    feature_error = max(feature_error, float(np.max(np.abs(numeric[finite] - expected_x[finite]))))
                category_mismatches += int(np.count_nonzero(encoded != c[lo:hi]))
                source_counts[receipt["source_status"]] += 1
                kernel_steps += receipt["kernel_steps"]
                fold_report["watches"] += 1
                fold_report["rows"] += len(numeric)
                report["scoredRows"] += len(numeric)
            print("P1_RAW_FOLD=" + str(fold) + " REBUILT_ROWS=" + str(fold_report["rows"]), flush=True)
            del model
    report["rawFeatureParity"] = {
        "numericFields": 148, "categoricalFields": 15, "maximumAbsoluteNumericError": feature_error,
        "numericValueMismatches": numeric_mismatches, "missingMaskMismatches": missing_mismatches,
        "categoricalMismatches": category_mismatches, "globalUnknownCellsByColumn": unknown_counts,
        "stateKernelSteps": kernel_steps, "sourceStatusWatchCounts": dict(source_counts),
        "originalDecimalLexemeOverlap": dict(overlap),
    }
    check(not any((numeric_mismatches, missing_mismatches, category_mismatches, sum(unknown_counts))),
          "ORIGINAL_FEATURE_PARITY_FAILED")
    report["rawFeatureParityPassed"] = True
    # All actual scores/first crosses now exist. Open expected OOF only here.
    oracle = core.load_oracle(corrected["PRIVATE_INPUTS/oof_P1.npz"], np, len(x))
    errors = {"prediction": 0.0, "percentile": 0.0, "score": 0.0, "threshold": 0.0}
    decisions = 0
    for result in predictions:
        item, fold = result["item"], result["item"]["fold"]
        rows = np.arange(item["lo"], item["hi"])
        positions = np.searchsorted(oracle["row_indices"], rows)
        check(np.all(positions < len(oracle["row_indices"])), "OOF_ROW_COVERAGE_MISMATCH")
        check(np.array_equal(oracle["row_indices"][positions], rows)
              and np.all(oracle["fold"][positions] == fold), "OOF_ROW_FOLD_MISMATCH")
        thresholds = np.asarray([spec["calibration"][fold]["thresholds"][p] for p in core.POLICIES])
        for name, actual, expected in (
            ("prediction", result["pred"], oracle["predictions"][positions]),
            ("percentile", result["pct"], oracle["percentiles"][positions]),
            ("score", result["score"], oracle["score"][positions]),
            ("threshold", thresholds, oracle["thresholds"][positions]),
        ):
            errors[name] = max(errors[name], float(np.max(np.abs(actual - expected))))
        decisions += int(np.count_nonzero((result["score"][:, None] >= thresholds)
                                          != (oracle["score"][positions, None] >= oracle["thresholds"][positions])))
    report["scoreParity"] = {"maximumAbsoluteError": errors, "fourPolicyDecisionMismatches": decisions}
    check(max(errors.values()) <= core.ATOL and decisions == 0, "ORIGINAL_SCORE_PARITY_FAILED")
    report["scoreParityPassed"] = True
    first = compare_first_intents(corrected["FIRST_INTENTS_PRIVATE.jsonl.gz"], actual_intents)
    report["firstIntentParity"] = first
    check(first["parityPassed"], "ORIGINAL_SELECTED_FIRST_INTENT_PARITY_FAILED")
    report["selectedWholeWatchFirstIntentParityPassed"] = True
    report["selectedWatches"] = len(selected)
    report["status"] = "ORIGINAL_RAW_TO_FROZEN_P1_SELECTED_WHOLE_WATCH_REPLAY_PASS"


def new_report(per_fold):
    return {
        "schemaId": "ARK_NO11_FROZEN_P1_RAW_FEATURE_WHOLE_WATCH_REPLAY_V1", "status": "NOT_RUN",
        "family": "P1", "policy": "Q70", "watchesPerFold": per_fold,
        "selection": "FIRST_NONEMPTY_CANONICAL_WATCHES_IN_ORIGINAL_WATCH_RECORD_ORDER_PER_SAVED_TEST_FOLD",
        "rawSourceKind": features.SOURCE_KIND, "rawInputPins": features.RAW_PINS,
        "publicSourcePins": core.PUBLIC_PINS, "privateArtifactsVerified": False,
        "originalP1ModelsExecuted": 0, "scoredRows": 0, "selectedWatches": 0,
        "rawFeatureParityPassed": False, "scoreParityPassed": False,
        "selectedWholeWatchFirstIntentParityPassed": False,
        "fullRawFeatureReplay": False, "fullOofReplay": False,
        "referenceArtifactsUsedOnlyForComparison": True, "expectedIntentsOpenedAfterAllDecisions": True,
        "actualKnownAt": "UNKNOWN", "assumedAvailableAt": "bar_end",
        "modelDispatch2026": "UNDEFINED_IN_ORIGINAL_FROZEN_SPLIT", "native2026FeatureRowsBuilt": 0,
        "newFits": 0, "recalibrationPerformed": False, "targetsRead": False,
        "futureEvaluationRead": False, "privateRowLevelExported": False,
        "originalFrozenFilesMutated": False, "actualBrokerKnownAtCertified": False,
        "liveFirstEntryCertified": False, "productionReady": False, "orderTransmission": False,
    }


def save_report(root, report):
    core.safe_directory(root)
    data = (json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()
    path = root / ("no11-frozen-p1-raw-feature-replay-" + core.digest(data)[:16] + ".json")
    if path.exists():
        check(not path.is_symlink() and path.read_bytes() == data, "REPORT_COLLISION")
    else:
        with path.open("xb") as target:
            target.write(data)
    print("P1_RAW_REPLAY_STATUS=" + report["status"])
    print("REPORT_JSON=" + str(path.absolute()))
    print("ORDER_TRANSMISSION=False")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path)
    parser.add_argument("--corrected", type=Path)
    parser.add_argument("--private-root", type=Path)
    parser.add_argument("--watches-per-fold", type=int, default=1)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    check(1 <= args.watches_per_fold <= 20, "SAMPLE_COUNT_INVALID")
    spec = core.load_contracts()
    if args.self_test:
        runtime = features.load_feature_runtime()
        check(len(runtime.numeric_names) == 148 and len(runtime.categorical_names) == 15,
              "FEATURE_ORDER_INVALID")
        print("P1_ORIGINAL_RAW_FEATURE_PUBLIC_SOURCE_SELFTEST=PASS")
        print("P1_PRIVATE_MODEL_EXECUTION=False")
        return 0
    check(args.private_root is not None, "PRIVATE_ROOT_REQUIRED")
    report = new_report(args.watches_per_fold)
    try:
        if args.base is None or args.corrected is None:
            report["status"] = "BLOCKED_PRIVATE_ORIGINAL_RAW_ARTIFACTS_MISSING"
        else:
            paths = {scope: core.materialize(getattr(args, scope), scope, spec, args.private_root)
                     for scope in ("base", "corrected")}
            raw_paths = features.materialize_saved_feature_inputs(args.base, args.private_root)
            report["privateArtifactsVerified"] = True
            report["verifiedPrivateFiles"] = sum(map(len, paths.values())) + len(raw_paths)
            report["verifiedArchives"] = {
                scope: {key: spec[scope + "_archive"][key] for key in ("bytes", "sha256")}
                for scope in ("base", "corrected")}
            run_replay(spec, paths, raw_paths, args.watches_per_fold, report)
    except Exception as exc:
        report["status"] = "BLOCKED_ORIGINAL_RAW_TO_P1_REPLAY"
        report["reason"] = str(exc) if isinstance(exc, ValueError) and str(exc).startswith("P1_") else type(exc).__name__
    save_report(args.private_root, report)
    return 0 if report["status"].endswith("_PASS") else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        reason = str(exc) if isinstance(exc, ValueError) and str(exc).startswith("P1_") else type(exc).__name__
        print("P1_RAW_REPLAY_SETUP_BLOCKED=" + reason, file=sys.stderr)
        print("ORDER_TRANSMISSION=False", file=sys.stderr)
        sys.exit(2)
