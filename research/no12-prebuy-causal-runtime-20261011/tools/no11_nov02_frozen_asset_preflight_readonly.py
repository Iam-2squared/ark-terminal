#!/usr/bin/env python3
"""No11 2026-11-02 real local frozen-asset load BEFORE RSS/cash review.

Original P1-F5 and original 24 H235 saved model members plus original Capital
and Structural EXIT source identity are validated using the existing pinned
No11 implementation. No model scoring, fitting, Excel/COM, bank, accounts,
broker transport, order permissions, or synthetic trading. Status/proof is
saved only outside the repository and never claims LIVE readiness.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys
import tempfile

SESSION = "2026-11-02"
SCHEMA = "ARK_NO11_NOV02_FROZEN_ASSETS_READONLY_PREFLIGHT_V1"
STOP_DIRS = frozenset((
    "daily-trend-capture", "weekly-pool-refresh", "previous-source",
    "unified-launcher", "external-security-review", "equity-type-backfill",
    "nov02-24-prelive", "securities-cash-evidence",
))
H235_MEMBER = Path("inputs/frozen_models/H2_BLOCK_01.json")
MODEL_FILES = tuple(
    Path("inputs/frozen_models") / f"H{head}_BLOCK_{block:02d}.json"
    for head in (2, 3, 5) for block in range(1, 9)
)


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError("NO11_NOV02_ASSETS_" + code)


def private(p: Path, *, directory: bool = True) -> Path:
    need(p.is_absolute(), "ABSOLUTE_PATH_REQUIRED")
    q = p.resolve(strict=True)
    need(q.is_dir() if directory else q.is_file(), "PATH_TYPE")
    need(not p.is_symlink() and not any(x.is_symlink() for x in p.parents),
         "SYMLINK_FORBIDDEN")
    return q


def look_for_h235(root: Path, limit: int = 25000) -> list[Path]:
    """Bounded private-local discovery; no raw model or position data is read."""
    root = private(root)
    found: list[Path] = []
    visited = 0
    for current, subdirs, _ in os.walk(root, topdown=True, followlinks=False):
        visited += 1
        need(visited <= limit, "H235_DISCOVERY_BOUNDED_LIMIT")
        base = Path(current)
        subdirs[:] = sorted(
            name for name in subdirs
            if name not in STOP_DIRS
            and not (base / name).is_symlink()
            and len((base / name).relative_to(root).parts) <= 7
        )
        if (base / H235_MEMBER).is_file():
            found.append(base)
        if len(found) > 3:
            raise ValueError("NO11_NOV02_ASSETS_H235_MULTIPLE_CANDIDATES")
    return found


def immutable(root: Path, value: dict) -> Path:
    data = (json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    dest = root / f"frozen-assets-{sha}.json"
    need(not dest.is_symlink(), "REPORT_OUTPUT_SYMLINK")
    if dest.exists():
        need(dest.read_bytes() == data, "REPORT_CONFLICT")
    else:
        with dest.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    return dest


def execute(*, engine: Path, no12: Path, p1_root: Path,
            h235_root: Path | None = None, output: Path) -> tuple[dict, Path]:
    engine = private(engine)
    no12 = private(no12)
    output = private(output)
    need(output == no12 or no12 in output.parents, "OUTPUT_NOT_IN_PRIVATE_ROOT")
    need(engine != no12 and engine not in no12.parents and no12 not in engine.parents,
         "ENGINE_AND_PRIVATE_ROOT_OVERLAP")
    need((engine / "tools/no11_p1_forward_shadow.py").is_file()
         and (engine / "tools/no11_h235_asof_forward_shadow.py").is_file(),
         "EXISTING_FROZEN_CODE_REQUIRED")
    need(sys.version_info[:2] == (3, 12), "PYTHON312_REQUIRED")
    pinned = {"numpy": "2.3.5", "scipy": "1.17.0", "scikit-learn": "1.8.0"}
    for package, required in pinned.items():
        need(importlib.metadata.version(package) == required,
             "PINNED_DEPENDENCY_" + package.upper().replace("-", "_"))

    tools_dir = str(engine / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    from no11_p1_forward_shadow import FrozenP1Scorer
    from no11_h235_asof_forward_shadow import FrozenH235AsOf
    from no11_broker_decision_bridge import original_functions, original_execution
    from no11_original_exit_shadow import load_original_exit

    # Real model loading verifies all original private model and public source
    # hashes; a preflight PASS does not imply economic model/live parity.
    p1_root = private(p1_root)
    scorer = FrozenP1Scorer(p1_root, engine.parents[2], SESSION)
    need(scorer.model_kind == "ORIGINAL_CORRECTED_P1_F5"
         and scorer.policy["selectedFold"] == 5,
         "P1_F5_CONTRACT_CHANGED")
    print("NO11_NOV02_FROZEN_P1=F5_Q70_ACTUAL_HASH_VERIFIED")
    print("NO11_NOV02_FROZEN_P1_PREDICTIONS=NOT_EXECUTED")

    candidates = [private(h235_root)] if h235_root is not None else look_for_h235(no12)
    print("NO11_NOV02_H235_MODEL_ROOT_CANDIDATES=" + str(len(candidates)))
    need(len(candidates) == 1, "H235_ROOT_NOT_UNIQUE_OR_NOT_FOUND")
    model_root = candidates[0]
    need(all((model_root / name).is_file() for name in MODEL_FILES),
         "H235_24_FILES_NOT_PRESENT")
    h235 = FrozenH235AsOf(model_root, SESSION)
    need(h235.original_model_count == 24, "H235_MODEL_COUNT")
    print("NO11_NOV02_H235=24_OF_24_ORIGINAL_MODELS_HASH_VERIFIED")

    original_functions()
    original_execution()
    print("NO11_NOV02_CAPITAL=ORIGINAL_NATIVE_SOURCE_HASH_VERIFIED")
    load_original_exit()
    print("NO11_NOV02_EXIT=ORIGINAL_STRUCTURAL_SOURCE_HASH_VERIFIED")
    report = {
        "schemaId": SCHEMA, "sessionDate": SESSION,
        "checkedAtJst": datetime.now(timezone(timedelta(hours=9))).isoformat(
            timespec="milliseconds"),
        "engine": str(engine),
        "p1Root": str(p1_root),
        "h235ModelRoot": str(model_root),
        "p1F5Loaded": True, "h235OriginalModelCount": 24,
        "capitalNativeSourceLoaded": True, "structuralExitSourceLoaded": True,
        "originalModelWeightsModified": False,
        "modelScoringExecuted": False, "modelFittingExecuted": False,
        "liveBrokerTested": False, "currentSessionDatedMasterVerified": False,
        "securitiesCashEvidenceVerified": False, "productionReady": False,
        "orderTransmission": False,
    }
    file = immutable(output, report)
    return report, file


def selftest() -> None:
    need(len(MODEL_FILES) == 24 and len(set(MODEL_FILES)) == 24
         and H235_MEMBER in MODEL_FILES, "MODEL_MEMBER_SET")
    with tempfile.TemporaryDirectory(prefix="ark-model-preflight-selftest-") as d:
        root = Path(d)
        (root / "model/inputs/frozen_models").mkdir(parents=True)
        (root / H235_MEMBER).parent.mkdir(parents=True, exist_ok=True)
        (root / "model" / H235_MEMBER).write_text("{}", encoding="utf-8")
        (root / "previous-source/inputs/frozen_models").mkdir(parents=True)
        (root / "previous-source" / H235_MEMBER).write_text("{}", encoding="utf-8")
        found = look_for_h235(root)
        need(found == [(root / "model").resolve()], "H235_BOUNDED_LOCAL_DISCOVERY")
    print("NO11_NOV02_FROZEN_ASSETS_OFFLINE_SELFTEST=PASS_NO_EXCEL_NO_BROKER")
    print("ORDER_TRANSMISSION=False")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-selftest", action="store_true")
    parser.add_argument("--engine", type=Path)
    parser.add_argument("--private-root", type=Path)
    parser.add_argument("--p1-root", type=Path)
    parser.add_argument("--h235-root", type=Path)
    parser.add_argument("--output", type=Path)
    a = parser.parse_args(argv)
    if a.offline_selftest:
        selftest()
        return
    need(all(x is not None for x in (a.engine, a.private_root, a.p1_root, a.output)),
         "REQUIRED_ARGUMENT_MISSING")
    _, file = execute(engine=a.engine, no12=a.private_root, p1_root=a.p1_root,
                      h235_root=a.h235_root, output=a.output)
    print("NO11_NOV02_FROZEN_ASSETS_PROOF=" + str(file))
    print("NO11_NOV02_FROZEN_ASSETS_STATUS=ORIGINAL_MODELS_LOADED_NOT_LIVE_READY")
    print("ORDER_TRANSMISSION=False")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, ImportError, KeyError,
            TypeError) as exc:
        code = str(exc)
        if not re.fullmatch(r"NO11_NOV02_ASSETS_[A-Z0-9_]+", code):
            code = "NO11_NOV02_ASSETS_PINNED_MODEL_OR_DEPENDENCY_FAILURE"
        print("NO11_NOV02_FROZEN_ASSETS=BLOCKED|" + code, file=sys.stderr)
        print("ORDER_TRANSMISSION=False")
        raise SystemExit(2)
