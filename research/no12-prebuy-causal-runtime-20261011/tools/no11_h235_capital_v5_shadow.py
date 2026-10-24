#!/usr/bin/env python3
"""As-of R0 -> ORIGINAL Capital V5 synthetic funding, with pinned Arrival Table.

No fake original receipt, no hypothetical future fill, broker, Excel or live
money. Only synthetic cash scenario and the original byte-pinned V5 allocator.
The last received closing price is an EXPLICIT shadow funding reference,
not a fill guarantee. Original 2025 Frozen rankings / historical equity are
not claimed reproduced.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import no11_h235_asof_forward_shadow as h235
import no11_capital_v5_crlf_safe_synthetic as native_v5

sys.dont_write_bytecode = True
SOURCE_BINDING = h235.ROOT / "research/capital-v5-sharp-drop-exit-reset20-20261007/SOURCE_BINDING.json"
ARRIVAL_SHA256 = "69f8edafb4708e9a7b61b4f85eb92f353049cf21324e1647602e9973f195f999"
FROZEN = "10c94c92c4bd2a59a22744667fd0210252602df4"
AUTHORITY = "710656491be06235901b45c50a8b5cbd714ba4eb"
SCENARIO = "ARK_NO11_H235_R0_CAPITAL_V5_SYNTHETIC_SCENARIO_V1"
OUTPUT = "ARK_NO11_H235_ASOF_TO_ORIGINAL_CAPITAL_V5_SYNTHETIC_RESULT_V1"
R0_ROW_FIELDS = frozenset((
    "schemaId", "sessionDate", "candidateId", "symbol",
    "entry_timestamp", "decisionAtJst", "asofReferenceBarEndJst",
    "referenceKnownAtJst", "raw_reference", "selectedBlock", "policySha256",
    "sourceKind", "sourceInputSha256", "changedFeatureSemantics",
    "modelInputOriginalHistoricalParity", "originalFrozenModelFilesVerified",
    "originalModelsExecuted", "newFits", "m2", "m3", "m5", "M", "B", "ML",
    "capital_score", "admission", "rank", "capacity_band",
    "shadowOnly", "productionReady", "orderTransmission",
    "orderAuthorized", "capitalExecutionAuthorized",
))


def require(ok, code):
    if not ok:
        raise ValueError("NO11_H235_CAPITAL_" + code)


def read_private(path, limit=25_000_000):
    path = Path(path).absolute()
    require(path.is_file() and not path.is_symlink() and
            all(not p.is_symlink() for p in path.parents) and
            0 < path.stat().st_size <= limit, "PRIVATE_INPUT_FILE_INVALID")
    data = path.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def original_arrival_tables(path, *, fixture_manifest=None):
    # A test can explicitly pass a local synthetic hash, NEVER through CLI.
    pin = ARRIVAL_SHA256 if fixture_manifest is None else fixture_manifest
    if fixture_manifest is None:
        binding = json.loads(SOURCE_BINDING.read_bytes())
        require(binding["V5_resolved_members"]["arrival"]["sha256"] == ARRIVAL_SHA256,
                "FROZEN_ORIGINAL_ARRIVAL_AUTHORITY_CHANGED")
    path = Path(path).absolute()
    require(path.is_file() and not path.is_symlink(), "ORIGINAL_ARRIVAL_ABSENT")
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == pin, "ORIGINAL_ARRIVAL_HASH_MISMATCH")
    tables = json.loads(data)
    require(type(tables) is dict and "8" in tables and isinstance(tables["8"], dict),
            "ORIGINAL_ARRIVAL_LAYOUT_UNRECOGNIZED")
    for key in ("minute_counts", "minute_bucket", "training_session_N", "B_median", "B_p75"):
        require(key in tables["8"], "ORIGINAL_ARRIVAL_TABLE_FIELDS_MISSING")
    return tables


def require_scenario(scenario):
    require(type(scenario) is dict and set(scenario) == {
        "schemaId", "evidenceMode", "sessionDate", "decisionAtJst",
        "arkCapitalInputs", "externalSymbols", "arkManagedSymbols",
        "existingBands", "afterFirstLegalSellFill", "pendingBrokerOrders",
        "syntheticAccountOnly", "productionReady", "orderTransmission",
    }, "SYNTHETIC_SCENARIO_FIELDS_INVALID")
    require(scenario["schemaId"] == SCENARIO and
            scenario["evidenceMode"] == "SYNTHETIC_OFFLINE_ONLY" and
            scenario["syntheticAccountOnly"] is True and
            scenario["afterFirstLegalSellFill"] is False and
            scenario["pendingBrokerOrders"] is False and
            scenario["productionReady"] is False and
            scenario["orderTransmission"] is False, "REAL_ACCOUNT_OR_ORDER_NOT_ALLOWED")
    h235.policy(scenario["sessionDate"])
    decision = h235.timestamp(scenario["decisionAtJst"], scenario["sessionDate"])
    require(decision.second >= 0 and 540 <= h235.minute(decision) < 920,
            "CAPITAL_DECISION_OUTSIDE_ORIGINAL_CUTOFF")
    return decision


def build_request(r0_batch, scenario, arrival):
    decision = require_scenario(scenario)
    require(type(r0_batch) is dict and
            r0_batch.get("schemaId") == "ARK_NO11_H235_ASOF_PRIVATE_RANK_BATCH_V1" and
            r0_batch.get("productionReady") is False and
            r0_batch.get("orderTransmission") is False and
            r0_batch.get("capitalV5Executed") is False and
            r0_batch.get("policy") == h235.policy(scenario["sessionDate"]),
            "ORIGINAL_ASOF_R0_BATCH_REQUIRED")
    rows = r0_batch.get("results")
    require(type(rows) is list and len(rows) <= 20, "RANK_BATCH_INVALID")
    _, _, stair, _ = h235.original_dependencies()
    require(rows == sorted(rows, key=stair.candidate_order),
            "R0_NOT_FROZEN_NATIVE_PRIORITY_ORDER")
    used = set()
    candidates = []
    for row in rows:
        require(type(row) is dict and set(row) == R0_ROW_FIELDS and
                row.get("schemaId") == h235.OUTPUT_SCHEMA and
                row.get("sessionDate") == scenario["sessionDate"] and
                row.get("selectedBlock") == 8 and
                row.get("policySha256") == r0_batch["policy"]["policySha256"] and
                row.get("changedFeatureSemantics") is True and
                row.get("modelInputOriginalHistoricalParity") is False and
                row.get("sourceKind") == "RSS_CUMULATIVE_PROXY" and
                type(row.get("sourceInputSha256")) is str and
                re.fullmatch(r"[a-f0-9]{64}", row["sourceInputSha256"]) and
                row.get("originalFrozenModelFilesVerified") == 24 and
                row.get("originalModelsExecuted") == 3 and
                row.get("newFits") == 0 and
                row.get("productionReady") is False and
                row.get("orderTransmission") is False and
                row.get("shadowOnly") is True and
                row.get("orderAuthorized") is False and
                row.get("capitalExecutionAuthorized") is False,
                "R0_SOURCE_NOT_ORIGINAL_SHADOW")
        identity, symbol = row.get("candidateId"), row.get("symbol")
        require(type(identity) is str and re.fullmatch(r"[a-f0-9]{64}", identity) and
                type(symbol) is str and h235.SYMBOL.fullmatch(symbol) and
                identity not in used, "R0_CANDIDATE_IDENTITY_DUPLICATE_OR_INVALID")
        used.add(identity)
        h235.timestamp(row["decisionAtJst"], scenario["sessionDate"])
        require(row["decisionAtJst"] <= scenario["decisionAtJst"] and
                h235.minute(h235.timestamp(row["decisionAtJst"], scenario["sessionDate"]))
                  == h235.minute(decision) and
                row["entry_timestamp"] <= row["decisionAtJst"],
                "R0_BATCH_NOT_SAME_OBSERVED_MINUTE")
        p = row.get("raw_reference")
        ml = row.get("ML")
        require(type(ml) in (int, float) and math.isfinite(ml) and
                type(p) in (int, float) and math.isfinite(p) and p > 0,
                "R0_FROZEN_SCORE_OR_REFERENCE_INVALID")
        comps = [row.get("m2"), row.get("m3"), row.get("m5")]
        total, baseline = row.get("M"), row.get("B")
        require(all(type(x) in (int, float) and math.isfinite(x) for x in
                    comps + [total, baseline]) and
                1 >= comps[0] >= comps[1] >= comps[2] >= 0 and
                baseline > 0 and
                abs(sum(comps) - total) < 1e-10 and
                abs(total / baseline - ml) < 1e-10 and
                row.get("admission") is (ml >= 1) and
                row.get("rank") == stair.band(ml) and
                row.get("capacity_band") == row.get("rank") and
                row.get("capital_score") == ml,
                "R0_NATIVE_ML_OR_BAND_PARITY_INVALID")
        if row["admission"] is False:
            continue
        require(ml >= 1 and row["rank"] in ("S", "A", "B"),
                "R0_CAPITAL_BAND_MISMATCH")
        candidates.append({
            "entry_id": identity, "brokerSymbol": symbol, "ML": ml,
            "capital_score": ml, "rank": row["rank"], "block": "8",
            "raw_reference": p,
        })
    # Preserve native frozen R0 multi-key ordering, not P1 score order.
    candidates.sort(key=lambda v: next(i for i, r in enumerate(rows)
                                       if r["candidateId"] == v["entry_id"]))
    if candidates:
        require("8" in arrival and type(arrival["8"]) is dict,
                "ORIGINAL_ARRIVAL_TABLE_REQUIRED")
        active = str(h235.minute(decision))
        require(active in arrival["8"].get("minute_counts", {}) and
                active in arrival["8"].get("minute_bucket", {}),
                "ORIGINAL_ARRIVAL_MINUTE_UNAVAILABLE")
    request = {
        "schemaId": "ARK_NO11_FROZEN_V5_SYNTHETIC_BRIDGE_V1",
        "evidenceMode": "SYNTHETIC_OFFLINE_ONLY",
        "strategyFreezeCommit": FROZEN,
        "capitalAuthorityCommit": AUTHORITY,
        "researchInputProvenance": "EXPLICIT_2026_RECEIVED_ASOF_R0_NOT_ORIGINAL_FILL",
        "afterFirstLegalSellFill": False,
        "pendingBrokerOrders": False, "sessionVerified": False,
        "productionReady": False, "orderTransmission": False,
        "minute": h235.minute(decision),
        "arkCapitalInputs": scenario["arkCapitalInputs"],
        "externalSymbols": scenario["externalSymbols"],
        "arkManagedSymbols": scenario["arkManagedSymbols"],
        "existingBands": scenario["existingBands"],
        "preorderedCandidates": candidates,
        "syntheticTrainingTables": arrival,
    }
    return request


def fund_shadow(r0_batch, scenario, arrival, *, original_arrival_verified=False):
    request = build_request(r0_batch, scenario, arrival)
    try:
        funded = native_v5.run_request(request)
    except Exception:
        # Original bridge errors are deliberately redacted; never echo holdings.
        raise ValueError("NO11_H235_CAPITAL_FROZEN_V5_REJECTED") from None
    require(funded.get("status") == "SYNTHETIC_SHADOW_ONLY" and
            funded.get("productionReady") is False and
            funded.get("transmitted") is False and
            funded.get("orderAllowed") is False, "FROZEN_CAPITAL_V5_NOT_SHADOW")
    return {
        "schemaId": OUTPUT,
        "sourceR0Sha256": h235.digest(r0_batch),
        "originalArrivalSha256": ARRIVAL_SHA256 if original_arrival_verified else None,
        "originalArrivalSha256Verified": bool(original_arrival_verified),
        "originalFrozenCapitalV5ExecutedOnSynthetic": True,
        "originalFrozenH235R0ScoredBeforeCapital": True,
        "preBuyOriginalHistoricalParityCertified": False,
        "shadowReferenceIsActualFill": False,
        "riskFreeExecutionGuaranteed": False,
        "modelDispatchIsNewShadowPolicy": True,
        "capital": funded,
        "productionReady": False,
        "orderTransmission": False,
        "orders": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h235-batch", required=True, type=Path)
    parser.add_argument("--original-arrival-table", required=True, type=Path)
    parser.add_argument("--synthetic-account-scenario", required=True, type=Path)
    parser.add_argument("--private-output", required=True, type=Path)
    args = parser.parse_args(argv)
    r0, _ = read_private(args.h235_batch)
    arrival = original_arrival_tables(args.original_arrival_table)
    scenario, _ = read_private(args.synthetic_account_scenario, 100_000)
    result = fund_shadow(r0, scenario, arrival, original_arrival_verified=True)
    out = args.private_output.absolute()
    require(out.parent.is_dir() and out != h235.ROOT and h235.ROOT not in out.parents
            and not out.is_symlink(), "OUTPUT_MUST_BE_PRIVATE")
    data = h235.stable_bytes(result) + b"\n"
    if out.exists():
        require(out.is_file() and out.read_bytes() == data, "OUTPUT_CONFLICT")
    else:
        with out.open("xb") as handle:
            handle.write(data)
    summary = {
        "status": "ASOF_R0_TO_FROZEN_V5_SYNTHETIC_ONLY",
        "fundedCount": result["capital"]["fundedCount"],
        "allocatedDebitJpy": result["capital"]["allocatedDebitJpy"],
        "outputSha256": hashlib.sha256(data).hexdigest(),
        "orders": 0, "productionReady": False, "orderTransmission": False,
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, AssertionError, TypeError,
            ImportError, RuntimeError) as exc:
        message = str(exc)
        print(message if re.fullmatch(r"NO11_H235_CAPITAL_[A-Z0-9_]+", message)
              else "NO11_H235_CAPITAL_UNVERIFIED_SOURCE_BLOCKED", file=sys.stderr)
        raise SystemExit(2)
