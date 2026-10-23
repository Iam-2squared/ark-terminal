#!/usr/bin/env python3
"""Restore the original corrected P1, then replay its target-free OOF decisions.

No training module is imported. Only the pinned original transform/percentile
AST nodes are evaluated; fit/run/evaluation are excluded. Private artifacts must
match the immutable public receipts before deserialization. This command has no
2026 model dispatch, broker, Excel or network path.
"""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
BASE_REL = "research/persistent-watchlist-uptrend-first-entry-20261003-v2"
CORRECTED_REL = BASE_REL + "/CORRECTED_LINEAGE_FAST_FREEZE_20261003"
HEADS = ("UPSIDE", "QUALITY", "ADVERSE")
POLICIES = ("Q70", "Q80", "Q90", "Q95")
OOF_ROWS = 223940
ATOL = 1e-12
PUBLIC_PINS = {
    BASE_REL + "/MANIFEST.json": "bdae909069de34fe01e5548836536c02c8d41c8b3f2da93f01d0547d7a056655",
    BASE_REL + "/FEATURE_FREEZE.json": "ad737e63e2a3100c4413ee30b59423f54eb197da0f9f1dcce81ffa8b71022f5e",
    BASE_REL + "/SPLIT_PRECOMMIT.json": "0f3b0958b0912bd553bfd9e08cd0b7cffa00f6b07d665cfb8bf67e4c2800922d",
    BASE_REL + "/model_oof.py": "1107373671c066d9ba825c7965e92702a4efa2b5c414616592fc8254cafa5b4d",
    CORRECTED_REL + "/P1_Q70_ENTRY_CONTRACT.json": "a60f604cdcdfe5dc9d673fd502883dc17797cceb06b1c2680b1a7e41cb07a750",
    CORRECTED_REL + "/CORRECTED_OOF_LINEAGE_RECEIPT.json": "77d62ea194f6788a6ea8b3c1645f91b129fd864859f9a9bb04332a2a15482274",
    CORRECTED_REL + "/PRIVATE_FREEZE_PACKAGE_RECEIPT.json": "5e3536be7bb6752865550535b3235cc44dc61d4d0b420493cd3c8daff1ec79de",
}


def check(ok, code):
    if not ok:
        raise ValueError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular_file(path):
    check(path.is_file() and not path.is_symlink(), "P1_FILE_MISSING_OR_SYMLINK")
    for parent in path.parents:
        check(not parent.is_symlink(), "P1_PARENT_SYMLINK_NOT_ALLOWED")


def verify_file(path, pin):
    regular_file(path)
    check(path.stat().st_size == pin["bytes"], "P1_ARTIFACT_SIZE_MISMATCH")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    check(h.hexdigest() == pin["sha256"], "P1_ARTIFACT_HASH_MISMATCH")


def verified_bytes(path, pin):
    regular_file(path)
    check(path.stat().st_size == pin["bytes"], "P1_ARTIFACT_SIZE_MISMATCH")
    data = path.read_bytes()
    check(digest(data) == pin["sha256"], "P1_ARTIFACT_HASH_MISMATCH")
    return data


def load_contracts(repo=REPO):
    public = {}
    for name, expected in PUBLIC_PINS.items():
        p = repo / name
        regular_file(p)
        # Git on Windows may checkout public text with CRLF. Private binaries
        # below are always checked without newline normalization.
        b = p.read_bytes().replace(b"\r\n", b"\n")
        check(digest(b) == expected, "P1_PUBLIC_SOURCE_PIN_MISMATCH:" + name)
        public[name] = b if name.endswith(".py") else json.loads(b)
    manifest = public[BASE_REL + "/MANIFEST.json"]
    feature = public[BASE_REL + "/FEATURE_FREEZE.json"]
    contract = public[CORRECTED_REL + "/P1_Q70_ENTRY_CONTRACT.json"]
    lineage = public[CORRECTED_REL + "/CORRECTED_OOF_LINEAGE_RECEIPT.json"]
    package = public[CORRECTED_REL + "/PRIVATE_FREEZE_PACKAGE_RECEIPT.json"]
    check(contract["family"] == "P1" and contract["Primary_Freeze_Target"] == "P1_Q70"
          and contract["decision"]["first_cross"] == "score>=threshold at earliest causal row"
          and contract["productionReady"] is False
          and lineage["status"] == "CORRECTED_OOF_COMPLETE"
          and lineage["mixed_old_bug_Q_D_predictions"] == 0
          and lineage["rows_per_family"] == OOF_ROWS, "P1_CONTRACT_MISMATCH")
    for key, width in (("P1_numeric", 148), ("P1_categorical", 15)):
        check(len(feature[key]) == width and len(set(feature[key])) == width
              and feature[key] == contract["feature_manifest"][key],
              "P1_FEATURE_ORDER_MISMATCH")
    wanted_base = ("PRIVATE_INPUTS/features_numeric.npy",
                   "PRIVATE_INPUTS/features_categories.npy",
                   "PERSISTENT_GRID.jsonl.gz", "WATCH_RECORDS.jsonl.gz")
    all_base = {a["path"]: a for a in manifest["artifacts"]}
    base_pins = {name: all_base[name] for name in wanted_base}
    wanted_corrected = ["PRIVATE_INPUTS/category_vocabulary.json",
                        "PRIVATE_INPUTS/oof_P1.npz", "FIRST_INTENTS_PRIVATE.jsonl.gz"]
    for fold in range(1, 6):
        stem = "PRIVATE_MODELS/P1_F" + str(fold)
        wanted_corrected.extend([stem + "_preprocessor.pkl", stem + "_calibration.json"])
        for head in HEADS:
            wanted_corrected.extend([stem + "_" + head + ".pkl",
                                     stem + "_" + head + "_train_prediction_reference.npy"])
    corrected_pins = {name: package["selected_private_files"][name]
                      for name in wanted_corrected}
    models = [r for r in lineage["model_lineage"] if r["family"] == "P1"]
    check(len(models) == 15 and {(r["fold"], r["head"]) for r in models}
          == {(f, h) for f in range(1, 6) for h in HEADS}, "P1_MODEL_SET_MISMATCH")
    for row in models:
        stem = "PRIVATE_MODELS/P1_F" + str(row["fold"])
        check(row["lineage"] == ("UNMODIFIED_ORIGINAL_UPSIDE_REUSE" if row["head"] == "UPSIDE"
                                  else "CORRECTED_CALENDAR_Q_D_REFIT"), "P1_OLD_MODEL_LINEAGE")
        for suffix, key in (("_preprocessor.pkl", "preprocessor_sha256"),
                            ("_" + row["head"] + ".pkl", "model_sha256"),
                            ("_" + row["head"] + "_train_prediction_reference.npy", "reference_sha256")):
            check(corrected_pins[stem + suffix]["sha256"] == row[key], "P1_MODEL_PIN_DISAGREEMENT")
    calibration = {r["fold"]: r for r in lineage["calibration"] if r["family"] == "P1"}
    split = public[BASE_REL + "/SPLIT_PRECOMMIT.json"]
    sessions = {r["id"]: set(r["test"]) for r in split["folds"]}
    check(set(calibration) == set(sessions) == set(range(1, 6)), "P1_FOLD_SET_MISMATCH")
    for fold in split["folds"]:
        check(set(fold["train"]).isdisjoint(fold["test"])
              and max(fold["train"]) < min(fold["test"]), "P1_SPLIT_NOT_TEMPORAL")
    return {"base": base_pins, "corrected": corrected_pins,
            "base_archive": package["base_package_dependency"], "corrected_archive": package,
            "feature": feature, "model_parameters": contract["model"]["parameters"],
            "calibration": calibration, "test_sessions": sessions,
            "source": public[BASE_REL + "/model_oof.py"]}


def safe_directory(path):
    check(not path.is_symlink(), "P1_OUTPUT_SYMLINK_NOT_ALLOWED")
    for parent in path.parents:
        check(not parent.is_symlink(), "P1_OUTPUT_PARENT_SYMLINK_NOT_ALLOWED")
    path.mkdir(parents=True, exist_ok=True)
    check(path.is_dir(), "P1_OUTPUT_NOT_DIRECTORY")


def materialize(source, scope, spec, private_root):
    """Read only allowlisted members; never extractall or import archive code."""
    source = Path(source).absolute()
    pins = spec[scope]
    rel = BASE_REL if scope == "base" else CORRECTED_REL
    if source.is_dir():
        candidates = (source, source / rel, source / "ark-terminal" / rel)
        root = next((p for p in candidates if (p / next(iter(pins))).is_file()), None)
        check(root is not None, "P1_EXTRACTED_ROOT_NOT_FOUND:" + scope)
        result = {name: root / name for name in pins}
        for name, path in result.items():
            verify_file(path, pins[name])
        return result
    archive = spec[scope + "_archive"]
    verify_file(source, archive)
    cache = private_root / "verified" / archive["sha256"][:16]
    safe_directory(cache)
    result = {}
    with zipfile.ZipFile(source) as z:
        members = z.namelist()
        check(len(members) == len(set(members)), "P1_DUPLICATE_ZIP_MEMBER")
        for name, pin in pins.items():
            member = "ark-terminal/" + rel + "/" + name
            if scope == "corrected":
                check(pin["archive_path"] == member, "P1_ARCHIVE_MEMBER_PIN_MISMATCH")
            info = z.getinfo(member)
            check(not info.is_dir() and info.file_size == pin["bytes"], "P1_ZIP_MEMBER_SIZE_MISMATCH")
            out = cache / name
            safe_directory(out.parent)
            if out.exists():
                verify_file(out, pin)
            else:
                fd, temporary = tempfile.mkstemp(prefix=".p1-", dir=out.parent)
                try:
                    h = hashlib.sha256()
                    size = 0
                    with os.fdopen(fd, "wb") as target, z.open(info) as src:
                        for block in iter(lambda: src.read(1024 * 1024), b""):
                            size += len(block)
                            check(size <= pin["bytes"], "P1_ZIP_MEMBER_OVERFLOW")
                            h.update(block)
                            target.write(block)
                    check(size == pin["bytes"] and h.hexdigest() == pin["sha256"],
                          "P1_ZIP_MEMBER_HASH_MISMATCH")
                    check(not out.exists() and not out.is_symlink(), "P1_CACHE_COLLISION")
                    os.replace(temporary, out)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            result[name] = out
    return result


def inference_primitives(source, np):
    """Keep the original transform and percentile math, without training code."""
    check(digest(source) == PUBLIC_PINS[BASE_REL + "/model_oof.py"], "P1_SCORER_SOURCE_CHANGED")
    parsed = ast.parse(source)
    cls = next(n for n in parsed.body if isinstance(n, ast.ClassDef) and n.name == "TrainPreprocessor")
    cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "transform"]
    pct = next(n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == "percentile")
    check(len(cls.body) == 1 and not cls.bases and not cls.decorator_list, "P1_TRANSFORM_AST_CHANGED")
    module = ast.fix_missing_locations(ast.Module(body=[cls, pct], type_ignores=[]))
    namespace = {"np": np, "__name__": "_ark_frozen_p1_inference"}
    exec(compile(module, "<pinned P1 transform and percentile only>", "exec"), namespace)
    check(not hasattr(namespace["TrainPreprocessor"], "fit"), "P1_TRAINING_CODE_PRESENT")
    return namespace["TrainPreprocessor"], namespace["percentile"]


class FrozenArtifactUnpickler(pickle.Unpickler):
    """Only for already hash-verified freeze assets, not arbitrary pickle input."""
    def __init__(self, data, preprocessor_class):
        super().__init__(io.BytesIO(data))
        self.preprocessor_class = preprocessor_class

    def find_class(self, module, name):
        if module in ("model_oof", "__main__") and name == "TrainPreprocessor":
            return self.preprocessor_class
        # sklearn 1.8.0's Cython loss records this short __module__ in the
        # original frozen pickles. Resolve only this exact observed class.
        if module == "_loss" and name == "CyHalfSquaredError":
            from sklearn._loss._loss import CyHalfSquaredError
            return CyHalfSquaredError
        if module == "builtins" and name in ("set", "frozenset", "slice", "complex"):
            return super().find_class(module, name)
        if module in ("numpy", "sklearn", "scipy") or module.startswith(("numpy.", "sklearn.", "scipy.")):
            return super().find_class(module, name)
        raise ValueError("P1_PICKLE_GLOBAL_NOT_ALLOWED:" + module + "." + name)


def load_pickle(path, pin, preprocessor_class):
    # Hash the exact byte buffer which is deserialized, before any pickle opcode.
    return FrozenArtifactUnpickler(verified_bytes(path, pin), preprocessor_class).load()


def validate_preprocessor(prep, vocab, training_rows, np):
    check(set(vars(prep)) == {"median", "known", "training_rows"}, "P1_PREPROCESSOR_STATE_CHANGED")
    check(isinstance(prep.median, np.ndarray) and prep.median.shape == (148,)
          and np.isfinite(prep.median).all() and prep.training_rows == training_rows,
          "P1_PREPROCESSOR_NUMERIC_MISMATCH")
    check(isinstance(prep.known, list) and len(prep.known) == len(vocab) == 15,
          "P1_PREPROCESSOR_CATEGORY_COUNT")
    for known, values in zip(prep.known, vocab):
        check(isinstance(values, list) and values and len(set(values)) == len(values)
              and all(type(v) is str for v in values)
              and isinstance(known, list) and known
              and all(type(k) is int and 0 <= k < len(values) for k in known)
              and known == sorted(set(known)), "P1_PREPROCESSOR_CATEGORY_MISMATCH")
    return 296 + sum(len(k) + 1 for k in prep.known)


class FrozenP1Fold:
    """Scoring of one pinned fold; no automatic fold choice for new dates."""
    def __init__(self, fold, spec, files, primitives, np):
        from sklearn.ensemble import HistGradientBoostingRegressor
        self.np = np
        self.fold = fold
        self.preprocessor_class, self.percentile = primitives
        self.calibration = spec["calibration"][fold]
        pins = spec["corrected"]
        stem = "PRIVATE_MODELS/P1_F" + str(fold)
        name = stem + "_calibration.json"
        check(json.loads(verified_bytes(files[name], pins[name])) == self.calibration,
              "P1_CALIBRATION_LINEAGE_MISMATCH")
        name = "PRIVATE_INPUTS/category_vocabulary.json"
        self.vocab = json.loads(verified_bytes(files[name], pins[name]))
        name = stem + "_preprocessor.pkl"
        self.prep = load_pickle(files[name], pins[name], self.preprocessor_class)
        check(type(self.prep) is self.preprocessor_class, "P1_PREPROCESSOR_CLASS_MISMATCH")
        width = validate_preprocessor(self.prep, self.vocab, self.calibration["training_score_N"], np)
        self.models, self.references = [], []
        for head in HEADS:
            name = stem + "_" + head + ".pkl"
            model = load_pickle(files[name], pins[name], self.preprocessor_class)
            check(type(model) is HistGradientBoostingRegressor and model.n_features_in_ == width,
                  "P1_MODEL_CLASS_OR_WIDTH_MISMATCH")
            params = model.get_params(deep=False)
            check(all(params[k] == v for k, v in spec["model_parameters"].items()), "P1_MODEL_PARAMETER_MISMATCH")
            name = stem + "_" + head + "_train_prediction_reference.npy"
            ref = np.load(files[name], allow_pickle=False, mmap_mode="r")
            check(ref.ndim == 1 and len(ref) == self.calibration["training_score_N"]
                  and np.isfinite(ref).all() and np.all(ref[:-1] <= ref[1:]),
                  "P1_REFERENCE_DISTRIBUTION_MISMATCH")
            self.models.append(model)
            self.references.append(ref)

    def score_batch(self, numeric, categorical):
        np = self.np
        check(numeric.ndim == 2 and numeric.shape[1] == 148
              and categorical.shape == (len(numeric), 15)
              and categorical.dtype.kind in "iu", "P1_FEATURE_MATRIX_SHAPE")
        for j, values in enumerate(self.vocab):
            check(np.all((categorical[:, j] >= 0) & (categorical[:, j] < len(values))),
                  "P1_CATEGORY_CODE_OUTSIDE_FROZEN_VOCAB")
        # out=None avoids the original Linux-only memmap/madvise branch.
        matrix = self.prep.transform(numeric, categorical)
        check(np.isfinite(matrix).all(), "P1_TRANSFORM_NOT_FINITE")
        pred = np.column_stack([m.predict(matrix) for m in self.models])
        check(np.isfinite(pred).all(), "P1_PREDICTION_NOT_FINITE")
        pct = np.column_stack([self.percentile(r, pred[:, h]) for h, r in enumerate(self.references)])
        scores = (pct[:, 0] + pct[:, 1] + 1 - pct[:, 2]) / 3
        return pred, pct, scores


def load_oracle(path, np, feature_rows):
    with np.load(path, allow_pickle=False) as z:
        check(set(z.files) == {"row_indices", "predictions", "percentiles", "score", "thresholds", "fold"},
              "P1_OOF_KEYS_CHANGED")
        data = {k: z[k] for k in z.files}
    for key, shape in (("row_indices", (OOF_ROWS,)), ("fold", (OOF_ROWS,)), ("score", (OOF_ROWS,)),
                       ("predictions", (OOF_ROWS, 3)), ("percentiles", (OOF_ROWS, 3)),
                       ("thresholds", (OOF_ROWS, 4))):
        check(data[key].shape == shape and np.isfinite(data[key]).all(), "P1_OOF_SHAPE_OR_FINITE")
    rows = data["row_indices"]
    check(rows.dtype.kind in "iu" and data["fold"].dtype.kind in "iu"
          and 0 <= rows[0] <= rows[-1] < feature_rows and np.all(rows[:-1] < rows[1:])
          and set(map(int, np.unique(data["fold"]))) == set(range(1, 6)), "P1_OOF_ROW_OR_FOLD_MAPPING")
    check(np.all((data["percentiles"] >= 0) & (data["percentiles"] <= 1)), "P1_OOF_PERCENTILE_RANGE")
    return data


def run_replay(spec, paths, sample_per_fold, report):
    try:
        import numpy as np
        import scipy
        import sklearn
        from threadpoolctl import threadpool_limits
    except ImportError as exc:
        raise ValueError("P1_INFERENCE_DEPENDENCIES_MISSING") from exc
    check(sklearn.__version__ == "1.8.0", "P1_REQUIRES_SCIKIT_LEARN_1_8_0")
    report["environment"] = {"python": sys.version.split()[0], "numpy": np.__version__,
                             "scipy": scipy.__version__, "scikitLearn": sklearn.__version__}
    base, corrected = paths["base"], paths["corrected"]
    x = np.load(base["PRIVATE_INPUTS/features_numeric.npy"], allow_pickle=False, mmap_mode="r")
    c = np.load(base["PRIVATE_INPUTS/features_categories.npy"], allow_pickle=False, mmap_mode="r")
    check(x.ndim == 2 and x.shape[1] == 148 and x.dtype == np.float64
          and c.shape == (len(x), 15) and c.dtype == np.int32, "P1_FROZEN_FEATURE_SHAPE")
    oracle = load_oracle(corrected["PRIVATE_INPUTS/oof_P1.npz"], np, len(x))
    primitives = inference_primitives(spec["source"], np)
    scores = np.full(OOF_ROWS, np.nan)
    report["folds"] = []
    report["originalP1ModelsExecuted"] = 0
    report["scoredRows"] = 0
    with threadpool_limits(limits=2):
        for fold in range(1, 6):
            indices = np.flatnonzero(oracle["fold"] == fold)
            expected_thresholds = np.asarray([spec["calibration"][fold]["thresholds"][p] for p in POLICIES])
            check(np.all(oracle["thresholds"][indices] == expected_thresholds), "P1_OOF_THRESHOLD_NOT_FROZEN")
            if sample_per_fold:
                indices = indices[np.unique(np.linspace(0, len(indices) - 1,
                                                       min(sample_per_fold, len(indices)), dtype=int))]
            model = FrozenP1Fold(fold, spec, corrected, primitives, np)
            errors = {"prediction": 0.0, "percentile": 0.0, "score": 0.0}
            row = {"fold": fold, "rows": 0, "q70": float(expected_thresholds[0]),
                   "maximumAbsoluteError": errors, "thresholdDecisionMismatches": 0}
            report["folds"].append(row)
            for lo in range(0, len(indices), 2048):
                js = indices[lo:lo + 2048]
                raw = oracle["row_indices"][js]
                pred, pct, result = model.score_batch(x[raw], c[raw])
                if lo == 0:
                    report["originalP1ModelsExecuted"] += 3
                scores[js] = result
                row["rows"] += len(js)
                report["scoredRows"] += len(js)
                for label, actual, expected in (("prediction", pred, oracle["predictions"][js]),
                                                ("percentile", pct, oracle["percentiles"][js]),
                                                ("score", result, oracle["score"][js])):
                    errors[label] = max(errors[label], float(np.max(np.abs(actual - expected))))
                row["thresholdDecisionMismatches"] += int(np.count_nonzero(
                    (result >= expected_thresholds[0]) != (oracle["score"][js] >= expected_thresholds[0])))
            check(max(errors.values()) <= ATOL and row["thresholdDecisionMismatches"] == 0,
                  "P1_ORIGINAL_SCORE_PARITY_FAILED")
            row["status"] = "PASS"
            print("P1_FOLD=" + str(fold) + " ROWS=" + str(row["rows"]) + " SCORE_PARITY=PASS", flush=True)
            del model
    report["scoreParityPassed"] = True
    report["fullOofReplay"] = sample_per_fold == 0
    if sample_per_fold:
        report["status"] = "ORIGINAL_CORRECTED_P1_SAMPLED_SCORE_REPLAY_PASS"
        return
    check(np.isfinite(scores).all() and report["scoredRows"] == OOF_ROWS, "P1_FULL_REPLAY_INCOMPLETE")
    from no11_frozen_p1_first_cross import replay_and_compare
    try:
        first = replay_and_compare(
            base["WATCH_RECORDS.jsonl.gz"], base["PERSISTENT_GRID.jsonl.gz"],
            corrected["FIRST_INTENTS_PRIVATE.jsonl.gz"], oracle["row_indices"], scores,
            oracle["fold"], {f: spec["calibration"][f]["thresholds"]["Q70"] for f in range(1, 6)},
            spec["test_sessions"])
    except ValueError as exc:
        # The companion raises fixed codes only, never private row values.
        raise ValueError("P1_FIRST_CROSS_" + str(exc)) from exc
    report["firstIntentParity"] = first
    check(first["parity_passed"] is True, "P1_ORIGINAL_FIRST_INTENT_PARITY_FAILED")
    report["firstIntentParityPassed"] = True
    report["status"] = "ORIGINAL_CORRECTED_P1_FULL_OOF_SCORE_AND_FIRST_INTENT_REPLAY_PASS"


def new_report(sample):
    return {"schemaId": "ARK_NO11_FROZEN_CORRECTED_P1_PRIVATE_SCORE_REPLAY_V1",
            "status": "NOT_RUN", "family": "P1", "policy": "Q70", "samplePerFold": sample,
            "originalOofRows": OOF_ROWS, "absoluteTolerance": ATOL,
            "publicSourcePins": PUBLIC_PINS, "privateArtifactsVerified": False,
            "originalP1ModelsExecuted": 0, "scoredRows": 0,
            "scoreParityPassed": False, "firstIntentParityPassed": False, "fullOofReplay": False,
            "newFits": 0, "recalibrationPerformed": False, "targetsRead": False,
            "futureEvaluationRead": False, "privateRowLevelExported": False,
            "originalFrozenFilesMutated": False,
            "modelDispatch2026": "UNDEFINED_IN_ORIGINAL_FROZEN_SPLIT",
            "native2026FeatureRowsBuilt": 0, "actualBrokerKnownAtCertified": False,
            "liveFirstEntryCertified": False, "productionReady": False, "orderTransmission": False}


def save_report(root, report):
    safe_directory(root)
    data = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    path = root / ("no11-frozen-p1-score-replay-" + digest(data)[:16] + ".json")
    if path.exists():
        check(path.read_bytes() == data and not path.is_symlink(), "P1_REPORT_COLLISION")
    else:
        with path.open("xb") as f:
            f.write(data)
    print("P1_REPLAY_STATUS=" + report["status"])
    print("REPORT_JSON=" + str(path.absolute()))
    print("ORDER_TRANSMISSION=False")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path)
    parser.add_argument("--base", type=Path)
    parser.add_argument("--corrected", type=Path)
    parser.add_argument("--sample-per-fold", type=int, default=0,
                        help="0 replays all OOF rows and first intents; positive values are sample smoke only")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    check(0 <= args.sample_per_fold <= 10000, "P1_SAMPLE_COUNT_INVALID")
    spec = load_contracts()
    if args.self_test:
        check(len(spec["base"]) == 4 and len(spec["corrected"]) == 43, "P1_ALLOWLIST_CHANGED")
        check(not any("target" in p.lower() or p.startswith("OOF_") for p in spec["corrected"]),
              "P1_TARGET_FILE_IN_ALLOWLIST")
        print("P1_PUBLIC_CONTRACT_AND_ARTIFACT_ALLOWLIST_SELFTEST=PASS")
        print("P1_PRIVATE_MODEL_EXECUTION=False")
        return 0
    check(args.private_root is not None, "P1_PRIVATE_ROOT_REQUIRED")
    report = new_report(args.sample_per_fold)
    report["requiredArchives"] = {s: {k: spec[s + "_archive"][k] for k in ("filename", "bytes", "sha256")}
                                  for s in ("base", "corrected")}
    missing = [s for s in ("base", "corrected") if getattr(args, s) is None]
    try:
        if missing:
            report["missingArtifacts"] = missing
            report["status"] = "BLOCKED_PRIVATE_ORIGINAL_ARTIFACTS_MISSING"
        else:
            paths = {}
            for scope in ("base", "corrected"):
                paths[scope] = materialize(getattr(args, scope), scope, spec, args.private_root)
            report["privateArtifactsVerified"] = True
            report["verifiedPrivateFiles"] = sum(map(len, paths.values()))
            if args.verify_only:
                print("PRECHECK=PASS")
                print("P1_VERIFIED_PRIVATE_FILES=" + str(report["verifiedPrivateFiles"]))
                return 0
            run_replay(spec, paths, args.sample_per_fold, report)
    except (ValueError, OSError, KeyError, EOFError, pickle.UnpicklingError, zipfile.BadZipFile) as exc:
        report["status"] = "BLOCKED_ORIGINAL_P1_REPLAY"
        # Do not copy private filenames, user directories or row contents into receipts.
        report["reason"] = str(exc) if isinstance(exc, ValueError) and str(exc).startswith("P1_") else type(exc).__name__
    save_report(args.private_root, report)
    return 0 if report["status"].endswith("_PASS") else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc).startswith("P1_") else type(exc).__name__
        print("P1_REPLAY_SETUP_BLOCKED=" + code, file=sys.stderr)
        print("ORDER_TRANSMISSION=False", file=sys.stderr)
        sys.exit(2)
