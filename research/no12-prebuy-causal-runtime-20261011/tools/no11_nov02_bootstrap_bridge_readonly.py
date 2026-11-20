#!/usr/bin/env python3
"""Connect the already VERIFIED Nov2 24-stock source + original Frozen assets.

PREPARE: create a source-only *non-executable* bridge to existing 24-stock
Chart50, prior context source, H235 and P1 files. No RSS, Excel, account I/O.
FINALIZE: only on actual Nov2 with an independently reviewed original dated
master, master-bound genuine previous context, and independently prepared
session-approved broker config. Validate all contracts and write bootstrap
JSON with orderTransmission=false; NEVER approve trading, alter launcher
settings, submit orders or turn live transport on. Fail closed on gaps.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

SESSION = "2026-11-02"
PRIOR = "2026-10-30"
SOURCE_SCHEMA = "ARK_NO11_NOV02_24_BOOTSTRAP_SOURCE_BRIDGE_V1"
EXPECTED = frozenset((
    "3753.T", "4478.T", "2002.T", "8163.T", "5273.T", "2810.T",
    "1914.T", "7678.T", "9245.T", "2705.T", "9900.T", "7581.T",
    "4733.T", "8070.T", "2004.T", "4502.T", "4565.T", "4544.T",
    "7083.T", "6532.T", "7821.T", "219A.T", "8923.T", "3023.T",
))
NEVER_ADMIT = frozenset(("1690.T", "2014.T", "2038.T", "4347.T", "5029.T", "2612.T"))
SHA = re.compile(r"^[a-f0-9]{64}$")


def need(ok, reason):
    if not ok:
        raise ValueError("NO11_NOV02_BOOTSTRAP_" + reason)


def safe_path(value, *, folder=False):
    need(isinstance(value, (str, Path)) and bool(str(value)), "PATH_REQUIRED")
    p = Path(value)
    need(p.is_absolute(), "ABSOLUTE_PATH_REQUIRED")
    need(not p.is_symlink() and not any(q.is_symlink() for q in p.parents),
         "SYMLINK_SOURCE_BLOCKED")
    need(p.is_dir() if folder else p.is_file(), "SOURCE_TYPE_OR_MISSING")
    need(folder or 0 < p.stat().st_size <= 15_000_000, "SOURCE_SIZE")
    return p.resolve(strict=True)


def load(path, prefix=None):
    p = safe_path(path)
    raw = p.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if prefix is not None:
        need(re.fullmatch(re.escape(prefix) + r"-([a-f0-9]{64})\.json",
                          p.name) is not None, "RECEIPT_NAME")
        need(p.name == prefix + "-" + sha + ".json", "RECEIPT_SHA_MISMATCH")
    try:
        obj = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        raise ValueError("NO11_NOV02_BOOTSTRAP_JSON_INVALID") from None
    need(isinstance(obj, dict), "JSON_OBJECT")
    return obj, sha


def store(folder, prefix, obj):
    root = safe_path(folder, folder=True)
    raw = (json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False) + "\n").encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    target = root / (prefix + "-" + sha + ".json")
    need(not target.is_symlink(), "OUTPUT_SYMLINK")
    if target.exists():
        need(target.is_file() and target.read_bytes() == raw, "OUTPUT_IMMUTABILITY")
    else:
        with target.open("xb") as f:
            f.write(raw)
            f.flush()
    return target


def jst_now():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="milliseconds")


def validate_sources(handoff_path, proof_path, engine_path, private_root):
    repo_engine = safe_path(engine_path, folder=True)
    private = safe_path(private_root, folder=True)
    need(repo_engine != private and repo_engine not in private.parents and
         private not in repo_engine.parents, "PUBLIC_PRIVATE_PATH_OVERLAP")
    handoff, handoff_sha = load(handoff_path, "morning-handoff")
    proof, proof_sha = load(proof_path, "frozen-assets")
    need(handoff.get("schemaId") == "ARK_NO11_NOV02_SOURCE_ONLY_HANDOFF_V1"
         and handoff.get("sessionDate") == SESSION
         and handoff.get("previousSession") == PRIOR
         and handoff.get("orderTransmission") is False
         and handoff.get("productionReady") is False
         and handoff.get("tradingAuthorized") is False
         and handoff.get("capturedMinuteArchiveCount") == 24,
         "HANDOFF_NOT_SOURCE_ONLY")
    need(proof.get("schemaId") == "ARK_NO11_NOV02_FROZEN_ASSETS_READONLY_PREFLIGHT_V1"
         and proof.get("sessionDate") == SESSION
         and proof.get("p1F5Loaded") is True
         and proof.get("h235OriginalModelCount") == 24
         and proof.get("capitalNativeSourceLoaded") is True
         and proof.get("structuralExitSourceLoaded") is True
         and proof.get("modelScoringExecuted") is False
         and proof.get("modelFittingExecuted") is False
         and proof.get("orderTransmission") is False
         and proof.get("productionReady") is False
         and proof.get("liveBrokerTested") is False,
         "FROZEN_MODEL_PROOF_INCOMPLETE")
    need(Path(proof.get("engine", "")).resolve() == repo_engine,
         "FROZEN_MODEL_ENGINE_IDENTITY")
    selected = handoff.get("selectedSymbols")
    need(type(selected) is list and len(selected) == 24 and
         len(set(selected)) == 24 and set(selected) == EXPECTED and
         not (set(selected) & NEVER_ADMIT), "NARROW_24_SCOPE_CHANGED")
    chart, chart_sha = load(handoff["chartPlanReceipt"])
    mask, _ = load(handoff["passMask"])
    need(chart.get("schemaId") == "ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1"
         and chart.get("chartPlan", {}).get("planSha256") == handoff.get("chartPlanSha256")
         and chart["chartPlan"].get("sessionDate") == SESSION
         and chart["chartPlan"].get("selectorInputSymbols") == selected
         and chart.get("orderTransmission") is False
         and mask.get("orderTransmission") is False
         and mask.get("asOfSession") == PRIOR,
         "CHART_AND_MASK_CHANGED")
    stage, stage_sha = load(handoff["previousArchiveStage"], "previous-archive-stage")
    need(stage.get("schemaId") == "ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1"
         and stage.get("sessionDate") == SESSION
         and stage.get("previousSession") == PRIOR
         and stage.get("selectedSymbols") == selected
         and stage.get("chartPlanSha256") == chart["chartPlan"]["planSha256"]
         and isinstance(stage.get("symbols"), dict)
         and set(stage["symbols"]) == set(selected)
         and stage.get("omittedSymbols") == {}
         and stage.get("orderTransmission") is False,
         "24_PREVIOUS_SOURCE_CHANGED")
    p1 = safe_path(proof["p1Root"], folder=True)
    h235 = safe_path(proof["h235ModelRoot"], folder=True)
    order_ids = safe_path(handoff["orderIdWorkbookPath"])
    need(order_ids.suffix.lower() == ".xlsx", "ORDER_ID_WORKBOOK_CHANGED")
    for name in ("tools/no11_received_session_bootstrap.py",
                 "tools/no11_received_session_controller.py",
                 "tools/no11_broker_execution_service.py",
                 "windows/Run-No11ReceivedSessionOperatorLive.ps1"):
        need((repo_engine / name).is_file(), "ORIGINAL_ENGINE_MISSING")
    daily = safe_path(handoff["dailyRun"], folder=True)
    weekly = safe_path(handoff["weeklySourceRun"], folder=True)
    need(Path(handoff["chartPlanReceipt"]).parent == daily and
         Path(handoff["passMask"]).parent == daily and weekly != daily,
         "WEEKLY_SOURCE_LINEAGE_CHANGED")
    report = {
        "schemaId": SOURCE_SCHEMA,
        "sessionDate": SESSION, "previousSession": PRIOR,
        "sourceMode": "VERIFIED_STATIC_INPUTS_ONLY_NO_DATED_MASTER",
        "handoffFile": str(safe_path(handoff_path)),
        "handoffSha256": handoff_sha,
        "frozenProofFile": str(safe_path(proof_path)),
        "frozenProofSha256": proof_sha,
        "sourceChartReceiptSha256": chart_sha,
        "previousArchiveStageSha256": stage_sha,
        "selectedCount": 24,
        "selectedSymbols": selected,
        "knownBootstrapFields": {
            "schemaId": "ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1",
            "sessionDate": SESSION,
            "dailyRun": str(daily),
            "runtimeRoot": str(p1),
            "h235ModelRoot": str(h235),
            "orderIdWorkbookPath": str(order_ids),
            "precomputedChartReceipt": str(safe_path(handoff["chartPlanReceipt"])),
            "precomputedG1Mask": str(safe_path(handoff["passMask"])),
            "weeklySourceRun": str(weekly),
            "productionReady": False,
            "orderTransmission": False,
        },
        "missingActualDay": [
            "INDEPENDENT_24_SYMBOL_SECURITY_AND_CORPORATE_ACTION_REVIEW",
            "CURRENT_DAY_RSS_REFERENCE_AND_PREVIOUS_CLOSE_PRICE_BASIS",
            "DATED_MASTER_CREATED_FROM_GENUINE_EXTERNAL_EVIDENCE",
            "REVIEWED_MASTER_BOUND_24_SYMBOL_PREVIOUS_CONTEXT",
            "BROKER_SESSION_CONFIG_FROM_REAL_EXCEL_SESSION",
            "SECURITIES_ACCOUNT_CASH_PROOF_AFTER_REAL_FUNDING",
            "ACTUAL_REFRESHED_BROKER_BUYING_POWER_EVIDENCE",
            "INTEGRATED_FROZEN_LIVE_PREFLIGHT",
            "EXPLICIT_HUMAN_APPROVAL_OF_REAL_CASH_ORDERS",
        ],
        "executableBootstrapCreated": False,
        "tradePermissionChanged": False,
        "productionReady": False,
        "orderTransmission": False,
    }
    return report


def finalize(source_bridge, master_file, previous_file, broker_file,
             engine, private_root, output):
    # Explicitly refuse to build a final config before the real session day.
    now = jst_now()
    need(now[:10] == SESSION, "ACTUAL_SESSION_DATE_REQUIRED")
    bridge, _ = load(source_bridge, "bootstrap-source-only")
    need(bridge.get("schemaId") == SOURCE_SCHEMA and
         bridge.get("sourceMode") == "VERIFIED_STATIC_INPUTS_ONLY_NO_DATED_MASTER" and
         bridge.get("selectedCount") == 24 and
         bridge.get("executableBootstrapCreated") is False and
         bridge.get("tradePermissionChanged") is False and
         bridge.get("orderTransmission") is False,
         "STATIC_SOURCE_BRIDGE_INVALID")
    original = validate_sources(
        bridge["handoffFile"], bridge["frozenProofFile"], engine, private_root)
    need(original["handoffSha256"] == bridge["handoffSha256"] and
         original["frozenProofSha256"] == bridge["frozenProofSha256"] and
         original["knownBootstrapFields"] == bridge["knownBootstrapFields"],
         "BRIDGE_OR_VERIFIED_MODEL_CHANGED")
    master, master_sha = load(master_file)
    previous, _ = load(previous_file)
    broker, _ = load(broker_file)
    need(master.get("schemaId") == "ARK_NO11_DATED_MASTER_RECEIPT_V1"
         and master.get("sessionDate") == SESSION and
         master.get("corporateActionReviewSource") ==
           "EXISTING_EXTERNAL_REVIEW_NOT_INFERRED_BY_ADAPTER"
         and type(master.get("securityEvidenceSha256")) is str
         and SHA.fullmatch(master["securityEvidenceSha256"]) is not None
         and type(master.get("referenceSourceSha256")) is str
         and SHA.fullmatch(master["referenceSourceSha256"]) is not None
         and master.get("orderTransmission") is False and
         master.get("productionReady") is False,
         "INDEPENDENT_MASTER_PROVENANCE_REQUIRED")
    rows = master.get("rows")
    need(type(rows) is list and len(rows) >= 24 and
         len({r.get("symbol") for r in rows if type(r) is dict}) == len(rows) and
         EXPECTED <= {r.get("symbol") for r in rows if type(r) is dict},
         "MASTER_MISSING_24_REVIEWED_SYMBOLS")
    need(previous.get("schemaId") == "ARK_NO11_RSS_P1_PREVIOUS_CONTEXT_V1"
         and previous.get("sessionDate") == SESSION and
         previous.get("previousSession") == PRIOR and
         previous.get("masterSha256") == master_sha
         and type(previous.get("symbols")) is dict and
         EXPECTED <= set(previous["symbols"])
         and previous.get("productionReady") is False and
         previous.get("orderTransmission") is False,
         "PREVIOUS_CONTEXT_NOT_BOUND_TO_REAL_MASTER")
    need(broker.get("schemaId") == "ARK_NO11_BROKER_EXECUTION_CONFIG_V1"
         and broker.get("sessionDate") == SESSION
         and broker.get("evidenceMode") == "BROKER_OBSERVATION"
         and broker.get("orderTransmission") is True
         and broker.get("transport", {}).get("mode") == "LIVE"
         and broker.get("transport", {}).get("approvedForSession") is True
         and broker.get("ledger", {}).get("maxSymbols") == 3
         and broker.get("ledger", {}).get("lotSize") == 100
         and broker.get("ledger", {}).get("allocatedCashJpy") ==
            "AUTO_SECURITIES_ACCOUNT_CASH_ONLY"
         and type(broker.get("securitiesCashEvidenceFile")) is str
         and safe_path(broker["securitiesCashEvidenceFile"]).is_file(),
         "Genuine_BROKER_CONFIG_AND_SECURITIES_CASH_REQUIRED".upper())
    repo_engine = safe_path(engine, folder=True)
    private_root = safe_path(private_root, folder=True)
    output = safe_path(output, folder=True)
    # A template is not a trade permit. Runtime still requires fresh RSS,
    # valid live transport details, same-day explicit approval, ledger/EXIT.
    session_runtime = private_root / "nov02-24-received-session"
    need(not session_runtime.is_symlink(), "SESSION_DIRECTORY_SYMLINK")
    session_runtime.mkdir(mode=0o700, exist_ok=True)
    fields = dict(original["knownBootstrapFields"])
    fields.update({
        "privateRoot": str(session_runtime),
        "datedMaster": str(safe_path(master_file)),
        "previousContext": str(safe_path(previous_file)),
        "brokerExecutionConfig": str(safe_path(broker_file)),
        "samples": 390,
        "historyBars": 120,
        "warmupSeconds": 20,
    })
    sys.path.insert(0, str(repo_engine / "tools"))
    import no11_received_session_bootstrap as bootstrap
    import no11_broker_execution_service as broker_service
    # Genuine private source, original code/Capital and all broker terms
    # are validated. No method here sends an order or opens Excel.
    bootstrap.validate_config(fields, allow_explicit_live=True)
    broker_service.settings(safe_path(broker_file), SESSION)
    selected = bootstrap.validate_scope(
        SESSION,
        Path(fields["precomputedChartReceipt"]),
        Path(fields["precomputedG1Mask"]),
        Path(fields["datedMaster"]), now)
    need(set(selected) == EXPECTED and len(selected) == 24,
         "ACTUAL_MASTER_SCOPE_NOT_24")
    return store(output, "bootstrap-validated-not-live", fields)


def selftest():
    need(len(EXPECTED) == 24 and not (EXPECTED & NEVER_ADMIT)
         and SHA.fullmatch("a" * 64) is not None,
         "STATIC_NARROW_24")
    need("datedMaster" not in SOURCE_SCHEMA and
         "PREPARE" in __doc__ and "FINALIZE" in __doc__,
         "SOURCE_ONLY_CONTRACT")
    print("NO11_NOV02_BOOTSTRAP_BRIDGE_OFFLINE_SELFTEST=PASS_NO_EXCEL_NO_ORDERS")
    print("ORDER_TRANSMISSION=False")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline-selftest", action="store_true")
    p.add_argument("--handoff", type=Path)
    p.add_argument("--proof", type=Path)
    p.add_argument("--engine", type=Path)
    p.add_argument("--private-root", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--finalize", action="store_true")
    p.add_argument("--bridge", type=Path)
    p.add_argument("--dated-master", type=Path)
    p.add_argument("--previous-context", type=Path)
    p.add_argument("--broker-config", type=Path)
    a = p.parse_args(argv)
    if a.offline_selftest:
        selftest()
        return
    need(a.engine is not None and a.private_root is not None and
         a.output is not None, "COMMON_PARAMETERS_REQUIRED")
    if not a.finalize:
        need(a.handoff is not None and a.proof is not None
             and a.bridge is None and a.dated_master is None and
             a.previous_context is None and a.broker_config is None,
             "PREPARE_ARGUMENTS_INVALID")
        result = validate_sources(a.handoff, a.proof, a.engine, a.private_root)
        file = store(a.output, "bootstrap-source-only", result)
        print("NO11_NOV02_BOOTSTRAP_STATIC_24=VERIFIED")
        print("NO11_NOV02_BOOTSTRAP_P1_ROOT=" + result["knownBootstrapFields"]["runtimeRoot"])
        print("NO11_NOV02_BOOTSTRAP_H235_ROOT=" + result["knownBootstrapFields"]["h235ModelRoot"])
        print("NO11_NOV02_BOOTSTRAP_BRIDGE=" + str(file))
        print("NO11_NOV02_BOOTSTRAP_LIVE_CONFIG=NOT_CREATED")
    else:
        need(all(x is not None for x in (
            a.bridge, a.dated_master, a.previous_context, a.broker_config)),
            "FINALIZE_REQUIRES_REAL_EVIDENCE")
        path = finalize(a.bridge, a.dated_master, a.previous_context,
                        a.broker_config, a.engine, a.private_root, a.output)
        print("NO11_NOV02_BOOTSTRAP_CONFIG=" + str(path))
        print("NO11_NOV02_BOOTSTRAP_EXTERNAL_LIVE_GATES=STILL_REQUIRED")
    print("ORDER_TRANSMISSION=False")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError,
            RuntimeError, ImportError) as e:
        reason = str(e)
        if not re.fullmatch(r"NO11_NOV02_BOOTSTRAP_[A-Z0-9_]+", reason):
            reason = "NO11_NOV02_BOOTSTRAP_PRIVATE_SOURCE_OR_VERIFICATION_FAILED"
        print("NO11_NOV02_BOOTSTRAP_BRIDGE=BLOCKED|" + reason, file=sys.stderr)
        print("ORDER_TRANSMISSION=False")
        raise SystemExit(2)
