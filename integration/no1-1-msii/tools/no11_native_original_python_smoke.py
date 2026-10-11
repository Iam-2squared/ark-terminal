#!/usr/bin/env python3
"""Original-byte-pinned frozen H2/H3/H5 math, isolated SYNTHETIC smoke only.

Never constructs trading intents, downloads data, authorizes Excel order functions,
claims native live feature certification, or writes to a broker/account.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
CODE = Path(__file__).resolve().parents[1] / "frozen-native-code"
SOURCE_PINS = {
    "core_features.py": "685a7774ed96556b810aa23957d12fda8f9654ba",
    "preprocessing.py": "29119e9d9e5ca880159289728c9391e17f8427ca",
    "staircase.py": "6863b2dded50e4d0caa4e2d470619017fcf0b759",
}
LINEAGE = ROOT / "research" / "capital-v5-sharp-drop-exit-reset20-20261007" / "FROZEN_NATIVE_INPUT_LINEAGE.json"
MANIFEST_BLOB = "1cf7c59b55890ba51b570a28210fbec715d27f5e"


def original_blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def pinned_text_bytes(filename, sha):
    raw = filename.read_bytes().replace(b"\r\n", b"\n")
    if original_blob_sha(raw) != sha:
        raise ValueError("ORIGINAL_NATIVE_CODE_OR_MANIFEST_PIN_MISMATCH")
    return raw


def original_dependencies():
    for name, sha in SOURCE_PINS.items():
        pinned_text_bytes(CODE / name, sha)
    # Import directly the byte-pinned original source, never a rewritten port.
    sys.path.insert(0, str(CODE))
    try:
        from preprocessing import predict_saved
        from staircase import materialize
    finally:
        sys.path.pop(0)
    return predict_saved, materialize


def synthetic_smoke():
    predict_saved, materialize = original_dependencies()
    artifact = {
        "preprocessing": {
            "numeric_fields": ["test_numeric"],
            "categorical_fields": ["test_category"],
            "numeric_mean": [0.0, 0.0],
            "numeric_scale": [1.0, 1.0],
            "categorical_train_vocab": {"test_category": ["__UNKNOWN__"]},
        },
        "coef": [0.0, 0.0, 0.0], "intercept": 0.0,
    }
    feature = {"numeric": {"test_numeric": None}, "categorical": {"test_category": "__UNKNOWN__"}}
    v = float(predict_saved([feature], artifact)[0])
    if v != .5:
        raise AssertionError("ORIGINAL_NATIVE_SYNTHETIC_LOGISTIC_MISMATCH")
    rank = materialize({"p2": v, "p3": v, "p5": v, "base2": .6, "base3": .5, "base5": .4})
    if rank["m2"] != .5 or rank["m3"] != .5 or rank["m5"] != .5 or rank["rank"] != "B":
        raise AssertionError("ORIGINAL_NATIVE_SYNTHETIC_PAVA_MISMATCH")
    return 1


def original_private_model_smoke(private_root):
    predict_saved, materialize = original_dependencies()
    source = json.loads(pinned_text_bytes(LINEAGE, MANIFEST_BLOB).decode("utf-8"))
    if source["status"] != "EXACT_MEMBER_HASH_PASS" or source["original_model_member_N"] != 24:
        raise ValueError("ORIGINAL_NATIVE_MODEL_MANIFEST_INVALID")
    names = sorted(x["local_member"] for x in source["models"])
    expected = sorted(
        "inputs/frozen_models/H{}_BLOCK_{:02d}.json".format(h, block)
        for h in (2, 3, 5) for block in range(1, 9)
    )
    if names != expected:
        raise ValueError("ORIGINAL_NATIVE_MODEL_SET_INVALID")
    pool = {}
    for row in source["models"]:
        filename = private_root / row["local_member"]
        expected_path = filename.resolve(strict=True)
        if not str(expected_path).startswith(str(private_root.resolve(strict=True)) + os.sep):
            raise ValueError("ORIGINAL_NATIVE_MODEL_PATH_ESCAPE")
        raw = filename.read_bytes()
        if (
            len(raw) != row["bytes"]
            or hashlib.sha256(raw).hexdigest() != row["sha256"]
            or original_blob_sha(raw) != row["git_blob"]
        ):
            raise ValueError("ORIGINAL_NATIVE_MODEL_HASH_MISMATCH")
        artifact = json.loads(raw)
        family, _, block_ext = filename.stem.partition("_BLOCK_")
        block = int(block_ext)
        if family not in ("H2", "H3", "H5") or block not in range(1, 9):
            raise ValueError("ORIGINAL_NATIVE_MODEL_IDENTITY_INVALID")
        prep = artifact["preprocessing"]
        case = {
            "numeric": {name: None for name in prep["numeric_fields"]},
            "categorical": {name: "__UNKNOWN__" for name in prep["categorical_fields"]},
        }
        p = float(predict_saved([case], artifact)[0])
        if not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("ORIGINAL_NATIVE_PREDICTION_NONFINITE")
        pool[(family, block)] = (p, float(artifact["base_rate"]))
    for block in range(1, 9):
        data = {}
        for h in (2, 3, 5):
            score, base = pool[("H" + str(h), block)]
            data["p" + str(h)] = score
            data["base" + str(h)] = base
        result = materialize(data)
        if not (
            0 <= result["m5"] <= result["m3"] <= result["m2"] <= 1
            and math.isfinite(result["ML"])
        ):
            raise ValueError("ORIGINAL_NATIVE_PAVA_INVARIANT_FAILED")
    return 24, 8


def run():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--offline-self-test", action="store_true")
    group.add_argument("--private-model-smoke", action="store_true")
    parser.add_argument("--model-root", type=Path, default=None)
    args = parser.parse_args()
    if args.offline_self_test:
        synthetic_smoke()
        print("NO11_FROZEN_NATIVE_ORIGINAL_PYTHON_SYNTHETIC_PASS=True")
    else:
        appdata = os.environ.get("LOCALAPPDATA")
        folder = args.model_root or (
            Path(appdata) / "ArkTerminal" / "No11" / "private-native-models"
            if appdata else None
        )
        if folder is None or not folder.is_absolute():
            raise ValueError("ORIGINAL_NATIVE_PRIVATE_MODEL_ROOT_REQUIRED")
        count, blocks = original_private_model_smoke(folder)
        print("NO11_FROZEN_NATIVE_ORIGINAL_MODELS_SCORING_SMOKE={}/{}".format(count, 24))
        print("NO11_FROZEN_NATIVE_PAVA_BLOCKS={}/{}".format(blocks, 8))
        print("NO11_NATIVE_FEATURES_CERTIFIED=False")
    print("NO11_NATIVE_LIVE_DECISION_EMITTED=False")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")


if __name__ == "__main__":
    try:
        run()
    except Exception:
        # No private coefficient, symbol, private folder, source feature or model data in logs.
        print("NO11_FROZEN_NATIVE_ORIGINAL_SMOKE=BLOCKED")
        print("NO11_NATIVE_LIVE_DECISION_EMITTED=False")
        print("NO11_PRODUCTION_READY=False")
        print("ORDER_TRANSMISSION=False")
        raise SystemExit(2)
