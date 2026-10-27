#!/usr/bin/env python3
"""Verify the ACTUAL original P1 F5, H235 x24, Capital V5 and EXIT assets
while a separate RSS/Excel Chart50 collector is running.

Read-only asset loading; this file does not import the bootstrap collector,
Excel, brokerage APIs, read account values, decide BUY/SELL, or write reports.
Never substitute TEST-ONLY account state for an authenticated account.
Never infer EXTERNALLY_REVIEWED, dated master or production clearance.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import sys


class ProbeError(ValueError):
    pass


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ProbeError("NO11_PARALLEL_ASSETS_" + code)


def path_directory(value: str | Path) -> Path:
    p = Path(value)
    need(p.is_absolute() and p.is_dir() and not p.is_symlink()
         and all(not ancestor.is_symlink() for ancestor in p.parents),
         "DIRECTORY_REQUIRED")
    return p.resolve(strict=True)


def path_file(value: str | Path) -> Path:
    p = Path(value)
    need(p.is_absolute() and p.is_file() and not p.is_symlink()
         and all(not ancestor.is_symlink() for ancestor in p.parents),
         "FILE_REQUIRED")
    return p.resolve(strict=True)


def original_p1_root(local: Path) -> Path:
    verified = path_directory(local / "frozen-p1-replay" / "verified")
    roots = [root for root in verified.iterdir()
             if root.is_dir() and not root.is_symlink()
             and (root / "ORIGINAL_P1" / "PRIVATE_INPUTS" / "category_vocabulary.json").is_file()]
    need(len(roots) == 1, "P1_VERIFIED_ORIGINAL_DIRECTORY_NOT_UNIQUE")
    original = path_directory(roots[0] / "ORIGINAL_P1")
    for name in ("PRIVATE_INPUTS", "PRIVATE_MODELS"):
        path_directory(original / name)
    return path_directory(roots[0])


def validate_session(value: str) -> str:
    need(re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", value) is not None,
         "SESSION_DATE_INVALID")
    need(datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") == value,
         "SESSION_DATE_INVALID")
    return value


def probe(*, engine_root: Path, private_local_root: Path, session: str) -> dict:
    engine = path_directory(engine_root)
    local = path_directory(private_local_root)
    validate_session(session)
    need(engine != local and engine not in local.parents
         and local not in engine.parents, "PRIVATE_AND_ENGINE_OVERLAP")
    tools = path_directory(engine / "tools")
    # The checked-in modules discover their own pinned public contract paths
    # from their __file__, NOT from this executable's download location.
    for name in ("no11_p1_forward_shadow.py",
                 "no11_h235_asof_forward_shadow.py",
                 "no11_h235_capital_v5_shadow.py",
                 "no11_original_exit_shadow.py"):
        path_file(tools / name)
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))

    p1_root = original_p1_root(local)
    print("NO11_PARALLEL_ASSETS_P1=LOADING_ORIGINAL_F5", flush=True)
    from no11_p1_forward_shadow import FrozenP1Scorer
    p1 = FrozenP1Scorer(p1_root, engine.parents[2], session)
    need(p1.model_kind == "ORIGINAL_CORRECTED_P1_F5"
         and p1.policy["newFits"] == 0
         and p1.policy["orderTransmission"] is False, "P1_POLICY_CHANGED")
    print("NO11_PARALLEL_ASSETS_P1=ORIGINAL_F5_HASH_AND_MODEL_LOAD_PASS", flush=True)

    h235_root = path_directory(local / "h235-verified-original")
    print("NO11_PARALLEL_ASSETS_H235=LOADING_24_ORIGINALS", flush=True)
    from no11_h235_asof_forward_shadow import FrozenH235AsOf
    h235 = FrozenH235AsOf(h235_root, session)
    need(h235.original_model_count == 24
         and h235.policy["newFits"] == 0
         and h235.policy["orderTransmission"] is False, "H235_ORIGINAL_POLICY_CHANGED")
    print("NO11_PARALLEL_ASSETS_H235=24_OF_24_HASH_AND_MODEL_LOAD_PASS", flush=True)

    arrival = path_file(local / "capital-verified-original" / "ARRIVAL_TABLE.json")
    from no11_h235_capital_v5_shadow import original_arrival_tables
    original_arrival_tables(arrival)
    print("NO11_PARALLEL_ASSETS_CAPITAL_V5=ARRIVAL_SHA256_AND_LAYOUT_PASS", flush=True)

    from no11_original_exit_shadow import load_original_exit
    exit_class, valid = load_original_exit()
    need(callable(exit_class) and callable(valid), "ORIGINAL_EXIT_NOT_LOADED")
    print("NO11_PARALLEL_ASSETS_EXIT=PINNED_ORIGINAL_CODE_LOAD_PASS", flush=True)

    # Keep the valid component checks distinct from integrated preflight.
    result = {
        "p1OriginalVerified": True,
        "h235OriginalVerified": 24,
        "capitalArrivalVerified": True,
        "originalExitVerified": True,
        "modelInferenceExecuted": False,
        "selectorExecuted": False,
        "integratedShadowPreflightPassed": False,
        "datedMasterVerified": False,
        "externalCorporateActionReviewVerified": False,
        "realAccountReconciled": False,
        "brokerTouched": False,
        "excelTouched": False,
        "shadowTradesExecuted": False,
        "orderTransmission": False,
    }
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-root", required=False, type=Path)
    parser.add_argument("--local-root", required=False, type=Path)
    parser.add_argument("--session", default="2026-10-27")
    parser.add_argument("--offline-self-test", action="store_true")
    a = parser.parse_args(argv)
    try:
        if a.offline_self_test:
            validate_session("2026-10-27")
            try:
                validate_session("2026-10-32")
            except ValueError:
                pass
            else:
                need(False, "DATE_SELF_TEST_FAILED")
            print("NO11_PARALLEL_ASSETS_OFFLINE_SELFTEST=PASS")
            print("ORDER_TRANSMISSION=False")
            return 0
        need(a.engine_root is not None and a.local_root is not None,
             "PATH_ARGUMENTS_REQUIRED")
        result = probe(engine_root=a.engine_root,
                       private_local_root=a.local_root, session=a.session)
        need(result["orderTransmission"] is False
             and result["integratedShadowPreflightPassed"] is False,
             "READONLY_CONTRACT_CHANGED")
        print("NO11_PARALLEL_ASSETS_ORIGINALS=ALL_HASH_VERIFIED_LOADED")
        print("NO11_PARALLEL_ASSETS_MODEL_INFERENCE=False")
        print("NO11_PARALLEL_ASSETS_SHADOW=NOT_LAUNCHED")
        print("NO11_PARALLEL_ASSETS_EXCEL_TOUCHED=False")
        print("NO11_PARALLEL_ASSETS_INTEGRATED_PREFLIGHT=NOT_PASSED")
        print("ORDER_TRANSMISSION=False")
        return 0
    except (ProbeError, ValueError, TypeError, KeyError, ImportError,
            RuntimeError, OSError, AssertionError) as exc:
        reason = str(exc)
        if not re.fullmatch(r"[A-Z][A-Z0-9_:]+", reason):
            reason = "NO11_PARALLEL_ASSETS_ORIGINAL_LOAD_OR_PRIVATE_INPUT_FAILED"
        print("NO11_PARALLEL_ASSETS=BLOCKED|" + reason)
        print("ORDER_TRANSMISSION=False")
        return 2


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
