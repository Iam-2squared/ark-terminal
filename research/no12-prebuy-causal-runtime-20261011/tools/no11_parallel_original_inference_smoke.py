#!/usr/bin/env python3
"""Prove actual original Frozen P1 F5 and original H235 BLOCK08 INFERENCE.

All feature values are EXPLICITLY SYNTHETIC and must not be represented as
observed 2026 stock signals, simulated orders, profitable trades or valid
account funding. This script uses NO saved RSS, account, Excel, broker APIs,
model fitting, model modification or order functions. It does not publish
individual model scores or any personal/account data.

Runs on the user's PINNED Python 3.12/scikit-learn 1.8.0 runtime and private
hash-verified original model directories, never fetching private models.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import math
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError("NO11_FROZEN_REAL_INFERENCE_" + code)


def safe_directory(path: Path) -> Path:
    need(path.is_absolute() and path.is_dir() and not path.is_symlink()
         and all(not p.is_symlink() for p in path.parents), "DIRECTORY_INVALID")
    return path.resolve(strict=True)


def synthetic_h235_input(session: str, symbol: str = "7203.T") -> dict:
    """Fixed synthetic RC2/Path shape from original H235 contract tests."""
    need(isinstance(session, str) and re.fullmatch(r"20\d\d-\d\d-\d\d", session)
         and datetime.strptime(session, "%Y-%m-%d").strftime("%Y-%m-%d") == session,
         "SESSION_DATE_INVALID")
    need(re.fullmatch(r"[0-9A-Z]{4}\.T", symbol) is not None,
         "SYNTHETIC_SYMBOL_INVALID")

    def stamp(minute: int, second: int = 0) -> str:
        return f"{session}T{minute // 60:02d}:{minute % 60:02d}:{second:02d}+09:00"

    trace = []
    for minute in (569, 570, 571):
        tick = minute - 540
        state = {
            "as_of": tick,
            "numeric_status": "ACCEPTED",
            "current_semantics_observed": True,
            "observed_at": tick,
            "activity": "LIVE",
            "basis": "OBSERVED_FRESH",
            "direction_basis": "PRICE",
            "stop": {"count": 2},
        }
        path = {
            "bar_end": stamp(minute),
            "scheduled_t": tick,
            "Primary_or_null": "RISE",
            "context_direction": 1,
            "local_direction": 1,
            "fast_applicable_to_primary": True,
            "fast": False,
            "dwell_observed_bars": minute - 568,
            "dwell_scheduled_bars": minute - 568,
            "causal_segment_id": "S1",
        }
        trace.append({
            "bar_end_minute": minute,
            "knownAtJst": stamp(minute, 8),
            "state": state,
            "path": path,
            "path_events": [],
        })
    return {
        "schemaId": "ARK_NO11_H235_RECEIVED_ASOF_CANDIDATE_V1",
        "sessionDate": session,
        "symbol": symbol,
        "candidateId": "a" * 64,
        "selectorFirstAtJst": stamp(570),
        "firstIntentAtJst": stamp(571),
        "decisionAtJst": stamp(571, 12),
        "p1Score": 0.75,
        "p1Threshold": 0.583,
        "selectorFirstPrice": 99.0,
        "referencePrice": 101.25,
        "referenceBarEndJst": stamp(571),
        "referenceKnownAtJst": stamp(571, 8),
        "stateTrace": trace,
        "sourceKind": "RSS_CUMULATIVE_PROXY",
        "shadowOnly": True,
        "productionReady": False,
        "orderTransmission": False,
    }


def prepare_private(private_root: Path) -> tuple[Path, Path]:
    local = safe_directory(private_root)
    verified = safe_directory(local / "frozen-p1-replay" / "verified")
    roots = [r for r in verified.iterdir()
             if r.is_dir() and not r.is_symlink()
             and (r / "ORIGINAL_P1" / "PRIVATE_INPUTS" / "category_vocabulary.json").is_file()
             and (r / "ORIGINAL_P1" / "PRIVATE_MODELS").is_dir()]
    need(len(roots) == 1, "P1_ORIGINAL_NOT_UNIQUE")
    safe_directory(roots[0] / "ORIGINAL_P1")
    h235 = safe_directory(local / "h235-verified-original")
    return safe_directory(roots[0]), h235


def validate_p1_output(value: dict) -> None:
    need(type(value) is dict and
         type(value.get("score")) is float and
         0 <= value["score"] <= 1 and math.isfinite(value["score"]) and
         type(value.get("headPredictions")) is list and
         len(value["headPredictions"]) == 3 and
         all(type(v) is float and math.isfinite(v) for v in value["headPredictions"]) and
         type(value.get("headPercentiles")) is list and
         len(value["headPercentiles"]) == 3 and
         all(type(v) is float and 0 <= v <= 1 and math.isfinite(v)
             for v in value["headPercentiles"]) and
         type(value.get("unseenCategoryCounts")) is list and
         len(value["unseenCategoryCounts"]) == 15,
         "P1_INFERENCE_OUTPUT_INVALID")


def validate_h235_output(value: dict, session: str) -> None:
    need(type(value) is dict and
         value.get("schemaId") == "ARK_NO11_H235_RECEIVED_ASOF_R0_V1" and
         value.get("sessionDate") == session and
         value.get("selectedBlock") == 8 and
         value.get("originalFrozenModelFilesVerified") == 24 and
         value.get("originalModelsExecuted") == 3 and
         value.get("newFits") == 0 and
         value.get("sourceKind") == "RSS_CUMULATIVE_PROXY" and
         value.get("shadowOnly") is True and
         value.get("productionReady") is False and
         value.get("orderTransmission") is False and
         value.get("orderAuthorized") is False and
         value.get("capitalExecutionAuthorized") is False and
         value.get("changedFeatureSemantics") is True and
         value.get("modelInputOriginalHistoricalParity") is False and
         type(value.get("ML")) in (int, float) and
         math.isfinite(value["ML"]) and
         type(value.get("rank")) is str,
         "H235_INFERENCE_OUTPUT_INVALID")


def run(*, engine_root: Path, private_root: Path, session: str) -> None:
    engine = safe_directory(engine_root)
    local = safe_directory(private_root)
    repo = safe_directory(engine.parents[1])
    need(engine.name == "no12-prebuy-causal-runtime-20261011" and
         engine.parent.name == "research" and
         repo != local and repo not in local.parents and
         local not in repo.parents,
         "ENGINE_ROOT_OR_PRIVATE_OVERLAP")
    tools = safe_directory(engine / "tools")
    p1_root, h235_root = prepare_private(local)
    sys.path.insert(0, str(tools))

    from no11_p1_forward_shadow import FrozenP1Scorer
    from no11_h235_asof_forward_shadow import FrozenH235AsOf

    # These model constructors verify the shipped original pin and every file.
    print("NO11_FROZEN_REAL_INFERENCE_P1=LOADING_PINNED_ORIGINAL_F5", flush=True)
    p1 = FrozenP1Scorer(p1_root, repo, session)
    need(p1.model_kind == "ORIGINAL_CORRECTED_P1_F5" and
         p1.policy.get("newFits") == 0 and
         p1.policy.get("orderTransmission") is False,
         "ORIGINAL_P1_NOT_VERIFIED")
    # 148 artificial numeric values, 15 vocabulary-valid synthetic categories.
    # Not a live market feature, and not fed into the H235 synthetic example.
    vocab = p1.model.vocab
    need(type(vocab) is list and len(vocab) == 15 and
         all(type(values) is list and values and
             all(type(name) is str for name in values)
             for values in vocab), "P1_VOCAB_SHAPE")
    categories = ["__MISSING__" if "__MISSING__" in values else values[0]
                  for values in vocab]
    numeric = [0.0] * 148
    x1 = p1.score(numeric, categories)
    x2 = p1.score(numeric, categories)
    validate_p1_output(x1)
    need(x1 == x2, "P1_NOT_DETERMINISTIC")
    print("NO11_FROZEN_REAL_INFERENCE_P1=THREE_ORIGINAL_HEADS_EXECUTED_SYNTHETIC", flush=True)

    print("NO11_FROZEN_REAL_INFERENCE_H235=LOADING_PINNED_24_ORIGINALS", flush=True)
    h235 = FrozenH235AsOf(h235_root, session)
    need(h235.original_model_count == 24 and
         h235.policy.get("newFits") == 0 and
         h235.policy.get("orderTransmission") is False, "ORIGINAL_H235_NOT_VERIFIED")
    fake = synthetic_h235_input(session)
    y1 = h235.score(fake)
    y2 = h235.score(fake)
    validate_h235_output(y1, session)
    need(y1 == y2, "H235_NOT_DETERMINISTIC")
    print("NO11_FROZEN_REAL_INFERENCE_H235=THREE_ORIGINAL_BLOCK08_HEADS_EXECUTED_SYNTHETIC", flush=True)

    print("NO11_FROZEN_REAL_INFERENCE_TEST_INPUT=SYNTHETIC_ONLY", flush=True)
    print("NO11_FROZEN_REAL_INFERENCE_ORIGINAL_WEIGHTS_CHANGED=False", flush=True)
    print("NO11_FROZEN_REAL_INFERENCE_FIT_COUNT=0", flush=True)
    print("NO11_FROZEN_REAL_INFERENCE_REAL_RSS_SELECTOR=False", flush=True)
    print("NO11_FROZEN_REAL_INFERENCE_PAPER_TRADES=False", flush=True)
    print("NO11_FROZEN_REAL_INFERENCE_ACCOUNT_OR_BROKER_TOUCHED=False", flush=True)
    print("NO11_FROZEN_REAL_INFERENCE_REAL_2026_PERFORMANCE_VERIFIED=False", flush=True)
    print("NO11_FROZEN_REAL_INFERENCE_INTEGRATED_PREFLIGHT=NOT_PASSED", flush=True)
    print("ORDER_TRANSMISSION=False", flush=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-root", type=Path)
    parser.add_argument("--local-root", type=Path)
    parser.add_argument("--session", default="2026-10-27")
    parser.add_argument("--offline-self-test", action="store_true")
    a = parser.parse_args(argv)
    try:
        if a.offline_self_test:
            x = synthetic_h235_input("2026-10-27")
            need(len(x["stateTrace"]) == 3 and
                 x["sourceKind"] == "RSS_CUMULATIVE_PROXY" and
                 x["orderTransmission"] is False,
                 "SYNTHETIC_FIXTURE_CONTRACT")
            try:
                validate_h235_output({"orderAuthorized": True}, "2026-10-27")
            except ValueError:
                pass
            else:
                need(False, "FAIL_CLOSED_TEST_FAILED")
            print("NO11_FROZEN_REAL_INFERENCE_OFFLINE_SELFTEST=PASS")
            print("ORDER_TRANSMISSION=False")
            return 0
        need(a.engine_root is not None and a.local_root is not None,
             "ENGINE_AND_LOCAL_ROOT_REQUIRED")
        run(engine_root=a.engine_root, private_root=a.local_root, session=a.session)
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError,
            ImportError, AssertionError) as exc:
        value = str(exc)
        code = (value if re.fullmatch(r"(?:NO11|P1)_[A-Z0-9_]+", value)
                else "NO11_FROZEN_REAL_INFERENCE_ORIGINAL_MODEL_OR_RUNTIME_UNAVAILABLE")
        print("NO11_FROZEN_REAL_INFERENCE=BLOCKED|" + code, flush=True)
        print("ORDER_TRANSMISSION=False", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
