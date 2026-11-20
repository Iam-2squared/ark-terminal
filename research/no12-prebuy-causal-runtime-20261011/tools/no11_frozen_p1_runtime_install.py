#!/usr/bin/env python3
"""Verify/install original P1 assets and run a target-free 160-row runtime smoke.

This sampled runtime check does not repeat the prior full OOF/first-intent
replay, choose a 2026 fold, fit models, recalibrate, or connect to a broker.
The private bundle contains no Python code. Verify-only needs the stdlib only.
"""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import pickle
import platform
import stat
import sys
import tempfile
import zipfile

import no11_frozen_p1_score_replay as core


sys.dont_write_bytecode = True
PACKAGE_PATH = Path(__file__).resolve().parents[1] / "NO11_FROZEN_P1_INFERENCE_PACKAGE_20261023.json"
PACKAGE_SHA256 = "8b83704224c496b6dd5f86306e25d1c92a80994e4dac682c67007413576de834"
FULL_REPLAY_SHA256 = "9faa6cb373fab70f3d05705184168f0d3a3fd94326b971b95dc00427f4d422e9"
SAMPLE_ROWS = 160
ROWS_PER_FOLD = 32
INPUT_MEMBER = "SMOKE_INPUTS.npz"
EXPECTED_MEMBER = "SMOKE_EXPECTED.npz"
check = core.check


def inference_names(spec):
    names = set(spec["corrected"]) - {
        "PRIVATE_INPUTS/oof_P1.npz", "FIRST_INTENTS_PRIVATE.jsonl.gz"}
    expected = {"PRIVATE_INPUTS/category_vocabulary.json"}
    for fold in range(1, 6):
        stem = "PRIVATE_MODELS/P1_F" + str(fold)
        expected.update((stem + "_preprocessor.pkl", stem + "_calibration.json"))
        for head in core.HEADS:
            expected.update((stem + "_" + head + ".pkl",
                             stem + "_" + head + "_train_prediction_reference.npy"))
    check(names == expected and len(names) == 41, "P1_RUNTIME_ORIGINAL_SET_INCOMPLETE")
    return names


def validate_package(package, spec):
    names = inference_names(spec)
    members = package["members"]
    expected = {"ORIGINAL_P1/" + name for name in names} | {INPUT_MEMBER, EXPECTED_MEMBER}
    check(set(members) == expected and package["memberCount"] == 43
          and package["originalInferenceFileCount"] == 41
          and package["originalModelCount"] == 15, "P1_RUNTIME_MEMBER_SET_INCOMPLETE")
    for name in names:
        pin = members["ORIGINAL_P1/" + name]
        original = spec["corrected"][name]
        check(all(pin[key] == original[key] for key in ("bytes", "sha256")),
              "P1_RUNTIME_ORIGINAL_ASSET_PIN_CHANGED")
    for scope in ("base", "corrected"):
        check(all(package["originalArchives"][scope][key] == spec[scope + "_archive"][key]
                  for key in ("filename", "bytes", "sha256")), "P1_RUNTIME_ARCHIVE_LINEAGE_CHANGED")
    smoke = package["runtimeSmoke"]
    check(package["schemaId"] == "ARK_NO11_FROZEN_P1_INFERENCE_PACKAGE_V1"
          and package["fullReplayEvidence"]["sha256"] == FULL_REPLAY_SHA256
          and package["fullOofReplay"] is False
          and smoke["scope"] == "SAMPLED_PC_RUNTIME_ONLY"
          and smoke["fullOofReplay"] is False and smoke["firstIntentReplay"] is False
          and smoke["rows"] == SAMPLE_ROWS and smoke["rowsPerFold"] == ROWS_PER_FOLD
          and smoke["folds"] == [1, 2, 3, 4, 5]
          and smoke["headOrder"] == list(core.HEADS)
          and smoke["thresholdOrder"] == list(core.POLICIES)
          and smoke["absoluteTolerance"] == core.ATOL
          and package["requiredScikitLearn"] == "1.8.0"
          and package["modelDispatch2026"] == "UNDEFINED_IN_ORIGINAL_FROZEN_SPLIT"
          and package["newFits"] == 0 and package["recalibrationPerformed"] is False
          and package["targetsRead"] is False and package["futureEvaluationRead"] is False
          and package["productionReady"] is False and package["orderTransmission"] is False,
          "P1_RUNTIME_PACKAGE_SCOPE_CHANGED")


def load_package(spec, path=PACKAGE_PATH):
    core.regular_file(path)
    # Public Git text may be checked out as CRLF on the Windows target.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    check(core.digest(data) == PACKAGE_SHA256, "P1_RUNTIME_PUBLIC_PACKAGE_PIN_MISMATCH")
    package = json.loads(data)
    validate_package(package, spec)
    return package


def _check_member(archive, info, pin):
    check(not info.is_dir() and not (info.flag_bits & 1)
          and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
          and info.file_size == pin["bytes"], "P1_RUNTIME_ZIP_MEMBER_METADATA_INVALID")
    digest = hashlib.sha256()
    size = 0
    with archive.open(info) as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            size += len(block)
            check(size <= pin["bytes"], "P1_RUNTIME_ZIP_MEMBER_OVERFLOW")
            digest.update(block)
    check(size == pin["bytes"] and digest.hexdigest() == pin["sha256"],
          "P1_RUNTIME_ZIP_MEMBER_HASH_MISMATCH")


def materialize_bundle(bundle, package, spec, private_root):
    """Check the whole bundle and every member before creating the cache."""
    validate_package(package, spec)
    bundle = Path(bundle).absolute()
    core.verify_file(bundle, package["bundle"])
    pins = package["members"]
    cache = Path(private_root).absolute() / "verified" / package["bundle"]["sha256"][:16]
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        check(len(names) == len(set(names)) and set(names) == set(pins),
              "P1_RUNTIME_ZIP_MEMBERS_MISMATCH")
        # No arbitrary paths are accepted: names equal the fixed original
        # relative-path set plus the two literal NPZ names above.
        for name in sorted(pins):
            _check_member(archive, archive.getinfo(name), pins[name])
        core.safe_directory(cache)
        result = {}
        for name in sorted(pins):
            pin = pins[name]
            output = cache / name
            core.safe_directory(output.parent)
            if output.exists() or output.is_symlink():
                core.verify_file(output, pin)
            else:
                fd, temporary = tempfile.mkstemp(prefix=".p1-runtime-", dir=output.parent)
                try:
                    digest = hashlib.sha256()
                    size = 0
                    with os.fdopen(fd, "wb") as target, archive.open(name) as source:
                        for block in iter(lambda: source.read(1024 * 1024), b""):
                            size += len(block)
                            check(size <= pin["bytes"], "P1_RUNTIME_ZIP_MEMBER_OVERFLOW")
                            digest.update(block)
                            target.write(block)
                    check(size == pin["bytes"] and digest.hexdigest() == pin["sha256"],
                          "P1_RUNTIME_ZIP_MEMBER_HASH_MISMATCH")
                    check(not output.exists() and not output.is_symlink(), "P1_RUNTIME_CACHE_COLLISION")
                    os.replace(temporary, output)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            result[name] = output
    return result


def _load_npz(path, pin, expected_keys, np):
    # Load the very same verified buffer, with object/pickle arrays disabled.
    data = core.verified_bytes(path, pin)
    with np.load(io.BytesIO(data), allow_pickle=False) as archive:
        check(set(archive.files) == set(expected_keys), "P1_RUNTIME_SMOKE_KEYS_CHANGED")
        return {key: archive[key] for key in expected_keys}


def run_runtime_smoke(spec, package, files, report):
    try:
        import numpy as np
        import scipy
        import sklearn
        from threadpoolctl import threadpool_limits
    except ImportError as exc:
        raise ValueError("P1_INFERENCE_DEPENDENCIES_MISSING") from exc
    check(sklearn.__version__ == "1.8.0", "P1_REQUIRES_SCIKIT_LEARN_1_8_0")
    report["environment"] = {"python": sys.version.split()[0], "numpy": np.__version__,
                             "scipy": scipy.__version__, "scikitLearn": sklearn.__version__,
                             "operatingSystem": platform.system(), "machine": platform.machine()}
    report["windowsRuntimeObserved"] = sys.platform == "win32"
    pins = package["members"]
    inputs = _load_npz(files[INPUT_MEMBER], pins[INPUT_MEMBER],
                       ("numeric", "categories", "fold", "row_indices", "oof_positions"), np)
    x, categories, folds = inputs["numeric"], inputs["categories"], inputs["fold"]
    # Missing numeric values are an original P1 input representation, handled
    # by the frozen median/missing-indicator transform; do not reject NaNs.
    check(x.shape == (SAMPLE_ROWS, 148) and x.dtype == np.float64
          and categories.shape == (SAMPLE_ROWS, 15) and categories.dtype == np.int32
          and folds.shape == (SAMPLE_ROWS,) and folds.dtype.kind in "iu"
          and set(map(int, np.unique(folds))) == set(range(1, 6)), "P1_RUNTIME_INPUT_SHAPE")
    for name in ("row_indices", "oof_positions"):
        values = inputs[name]
        check(values.shape == (SAMPLE_ROWS,) and values.dtype.kind in "iu"
              and np.all(values >= 0) and len(np.unique(values)) == SAMPLE_ROWS,
              "P1_RUNTIME_INPUT_ROW_MAPPING")
    check(np.all(inputs["oof_positions"] < core.OOF_ROWS), "P1_RUNTIME_INPUT_ROW_MAPPING")
    corrected = {name: files["ORIGINAL_P1/" + name] for name in inference_names(spec)}
    primitives = core.inference_primitives(spec["source"], np)
    predictions = np.empty((SAMPLE_ROWS, 3), dtype=np.float64)
    percentiles = np.empty_like(predictions)
    scores = np.empty(SAMPLE_ROWS, dtype=np.float64)
    thresholds = np.empty((SAMPLE_ROWS, 4), dtype=np.float64)
    report["folds"] = []
    with threadpool_limits(limits=2):
        for fold in range(1, 6):
            indices = np.flatnonzero(folds == fold)
            check(len(indices) == ROWS_PER_FOLD, "P1_RUNTIME_FOLD_SAMPLE_COUNT")
            for name in ("row_indices", "oof_positions"):
                values = inputs[name][indices]
                check(np.all(values[:-1] < values[1:]), "P1_RUNTIME_INPUT_ROW_MAPPING")
            model = core.FrozenP1Fold(fold, spec, corrected, primitives, np)
            pred, pct, score = model.score_batch(x[indices], categories[indices])
            predictions[indices], percentiles[indices], scores[indices] = pred, pct, score
            thresholds[indices] = [spec["calibration"][fold]["thresholds"][p] for p in core.POLICIES]
            report["originalP1ModelsExecuted"] += 3
            report["scoredRows"] += len(indices)
            report["folds"].append({"fold": fold, "rows": len(indices)})
            del model

    # The separate expected NPZ is opened only after all model predictions.
    expected = _load_npz(files[EXPECTED_MEMBER], pins[EXPECTED_MEMBER],
                         ("predictions", "percentiles", "score", "thresholds"), np)
    report["expectedOracleReadAfterPrediction"] = True
    for name, shape in (("predictions", (SAMPLE_ROWS, 3)), ("percentiles", (SAMPLE_ROWS, 3)),
                        ("score", (SAMPLE_ROWS,)), ("thresholds", (SAMPLE_ROWS, 4))):
        value = expected[name]
        check(value.shape == shape and value.dtype == np.float64 and np.isfinite(value).all(),
              "P1_RUNTIME_ORACLE_SHAPE_OR_FINITE")
    check(np.all((expected["percentiles"] >= 0) & (expected["percentiles"] <= 1))
          and np.all((expected["score"] >= 0) & (expected["score"] <= 1)),
          "P1_RUNTIME_ORACLE_RANGE")
    check(np.array_equal(thresholds, expected["thresholds"]), "P1_RUNTIME_THRESHOLDS_NOT_FROZEN")
    for row in report["folds"]:
        indices = np.flatnonzero(folds == row["fold"])
        errors = {}
        for label, actual, oracle_key in (("prediction", predictions, "predictions"),
                                          ("percentile", percentiles, "percentiles"),
                                          ("score", scores, "score"),
                                          ("threshold", thresholds, "thresholds")):
            errors[label] = float(np.max(np.abs(actual[indices] - expected[oracle_key][indices])))
        actual_decisions = scores[indices, None] >= thresholds[indices]
        expected_decisions = expected["score"][indices, None] >= expected["thresholds"][indices]
        mismatches = int(np.count_nonzero(actual_decisions != expected_decisions))
        row.update(maximumAbsoluteError=errors, thresholdDecisionMismatches=mismatches,
                   q70DecisionMismatches=int(np.count_nonzero(actual_decisions[:, 0] != expected_decisions[:, 0])))
        check(max(errors.values()) <= core.ATOL and mismatches == 0, "P1_RUNTIME_SCORE_PARITY_FAILED")
        row["status"] = "PASS"
        print("P1_RUNTIME_FOLD=" + str(row["fold"]) + " ROWS=" + str(row["rows"]) + " SCORE_PARITY=PASS", flush=True)
    check(report["scoredRows"] == SAMPLE_ROWS and report["originalP1ModelsExecuted"] == 15,
          "P1_RUNTIME_SMOKE_INCOMPLETE")
    report["scoreParityPassed"] = True
    report["status"] = "ORIGINAL_CORRECTED_P1_PC_RUNTIME_SAMPLED_SCORE_PARITY_PASS"


def new_runtime_report():
    report = core.new_report(ROWS_PER_FOLD)
    report.update(schemaId="ARK_NO11_FROZEN_P1_PORTABLE_RUNTIME_SMOKE_V1",
                  runtimeScope="SAMPLED_PC_RUNTIME_ONLY", sampledRuntimeOnly=True,
                  runtimePackageReceiptSha256=PACKAGE_SHA256,
                  priorFullReplayEvidenceSha256=FULL_REPLAY_SHA256,
                  verifiedPrivateFiles=0, originalInferenceAssetCount=41,
                  expectedOracleReadAfterPrediction=False, windowsRuntimeObserved=False)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    report = new_runtime_report()
    try:
        spec = core.load_contracts()
        package = load_package(spec)
        report["portableBundle"] = package["bundle"]
        if args.bundle is None:
            report["status"] = "BLOCKED_PRIVATE_P1_INFERENCE_BUNDLE_MISSING"
            report["reason"] = "P1_RUNTIME_BUNDLE_REQUIRED"
        else:
            files = materialize_bundle(args.bundle, package, spec, args.private_root)
            report["privateArtifactsVerified"] = True
            report["verifiedPrivateFiles"] = len(files)
            if args.verify_only:
                print("PRECHECK=PASS")
                print("P1_PORTABLE_VERIFIED_FILES=" + str(len(files)))
                print("P1_PRIVATE_MODEL_EXECUTION=False")
                print("ORDER_TRANSMISSION=False")
                return 0
            run_runtime_smoke(spec, package, files, report)
    except (ValueError, OSError, KeyError, EOFError, ImportError, AttributeError,
            TypeError, RuntimeError, pickle.UnpicklingError, zipfile.BadZipFile) as exc:
        report["status"] = "BLOCKED_ORIGINAL_P1_RUNTIME_SMOKE"
        report["reason"] = str(exc) if isinstance(exc, ValueError) and str(exc).startswith("P1_") else type(exc).__name__
    core.save_report(args.private_root, report)
    return 0 if report["status"].endswith("_PASS") else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc).startswith("P1_") else type(exc).__name__
        print("P1_RUNTIME_SETUP_BLOCKED=" + code, file=sys.stderr)
        print("ORDER_TRANSMISSION=False", file=sys.stderr)
        sys.exit(2)
