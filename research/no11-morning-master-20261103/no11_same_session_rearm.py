#!/usr/bin/env python3
"""One-shot, manually confirmed SAME-RUN recovery of a source-only halt.

Never creates a fresh Trade run or submits/retransmits an order. Requires exact
broker/ledger agreement from one independent real RSS snapshot and a confirmed
closed owned collector. Only the approved, already-started session's source
halt may be cleared. ResumeRun is an INDEPENDENT second process after this
command finishes and releases the exclusive service lock.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys

JST = timezone(timedelta(hours=9))
SAFE_SOURCE_HALTS = frozenset({
    "NO11_BOOTSTRAP_COLLECTOR_FAILED",
    "NO11_SERVICE_CAPTURE_STOPPED_OR_STALE",
    "NO11_C50_GROWING_CHART_SHAPE",
    "NO11_C50_MARKET_READ_INVALID",
})
IGNORABLE_BUY_BLOCKERS = frozenset({"FRESH_BUYING_POWER_REQUIRED"})
MAX_REARMS = 3
SCHEMA = "ARK_NO11_SAME_RUN_SOURCE_REARM_V1"


def need(value, code):
    if not value:
        raise ValueError("NO11_REARM_" + code)


def load(path):
    p = Path(path)
    need(p.is_file() and not p.is_symlink(), "SOURCE_MISSING")
    raw = p.read_bytes()
    need(0 < len(raw) <= 25_000_000, "SOURCE_SIZE")
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def now_jst():
    return datetime.now(JST)


def rearm(*, engine_root, bootstrap_file, observation_file, launcher_store,
          run_root, manual_confirmed=False, at=None, apply=False):
    at = at or now_jst()
    day = at.date().isoformat()
    need(at.utcoffset() == timedelta(hours=9)
         and "09:00" <= at.strftime("%H:%M") < "15:20",
         "MARKET_SESSION")
    need(manual_confirmed is True, "EXPLICIT_OPERATOR_RECONNECT_CONFIRMATION")
    base = Path(engine_root).resolve()
    need(base.is_dir(), "ENGINE_ROOT")
    sys.path.insert(0, str(base / "tools"))
    try:
        bootstrap = importlib.import_module("no11_received_session_bootstrap")
        recovery = importlib.import_module("no11_received_run_recovery")
        svc = importlib.import_module("no11_received_pipeline_service")
        led = importlib.import_module("no11_broker_execution_ledger")
        funds = importlib.import_module("no11_securities_cash_only")
        controller = importlib.import_module("no11_received_session_controller")
    finally:
        sys.path.pop(0)
    # Private source and active run identity are verified against the ORIGINAL
    # controller and sealed recovery contract, not a new configuration.
    config_raw, config_bytes_sha = load(bootstrap_file)
    config = bootstrap.validate_config(config_raw, allow_explicit_live=True)
    need(config["sessionDate"] == day
         and config["orderTransmission"] is False
         and config["productionReady"] is False
         and "shadowAccountConfig" not in config, "LIVE_CONFIG_SCOPE")
    broker, broker_sha = load(config["brokerExecutionConfig"])
    need(broker.get("schemaId") == "ARK_NO11_BROKER_EXECUTION_CONFIG_V1"
         and broker.get("sessionDate") == day
         and broker.get("evidenceMode") == "BROKER_OBSERVATION"
         and broker.get("transport", {}).get("mode") == "LIVE"
         and broker.get("transport", {}).get("approvedForSession") is True
         and broker.get("transport", {}).get("operatorEnabled") is True
         and broker.get("transport", {}).get("sessionDate") == day,
         "PREVIOUS_LIVE_APPROVAL_INVALID")
    store = Path(launcher_store).resolve()
    need(store.is_dir(), "LAUNCHER_STORE_MISSING")
    marker, _ = load(store / ("TRADE-" + day + ".launch.json"))
    need(marker.get("schemaId") == "ARK_NO11_UNIFIED_START_REQUEST_V1"
         and marker.get("kind") == "TRADE"
         and marker.get("asOfDate") == day
         and marker.get("sourceSha256") == config_bytes_sha
         and marker.get("externalBrokerApprovalStillRequired") is True,
         "ORIGINAL_SAME_DAY_TRADE_RECEIPT")
    manager = recovery.RunRecovery(config)
    run = manager._run(run_root)
    root = Path(config["privateRoot"])
    need(run.parent == root and
         run.name.startswith("session-" + day + "-"), "RUN_IDENTITY")
    evidence, observation_sha = load(observation_file)
    now_string = at.isoformat(timespec="milliseconds")
    # Fully inspect the *same* broker snapshot that OneClick already captured;
    # no second request for human authentication or a new BUY intent.
    local = Path(__file__).resolve().parent
    if str(local) not in sys.path:
        sys.path.insert(0, str(local))
    from no11_manual_reconnect_review import assess
    result = {"schemaId": SCHEMA, "sessionDate": day, "applyRequested": apply,
              "tradeRelaunched": False, "orderResent": False,
              "originalReceiptsModified": False, "orderTransmission": False}
    with svc.exclusive_service(root):
        # RunRecovery.restore checks signed run input, previous snapshots and
        # *all* owned collector cleanup receipts including postmortem proof.
        manager.restore(run)
        need(controller.marked_cleanup_proven(root, run, day, manager),
             "UNRESOLVED_COLLECTOR_CLEANUP_MARKER")
        # Prevent a false clean restore after a FAILED process with a preserved
        # unsaved workbook, which would otherwise exceed RSS chart capacity.
        attempts = sorted(run.glob("attempt-*"))
        need(attempts, "COLLECTOR_ATTEMPT_MISSING")
        last = recovery.unseal(attempts[-1] / "attempt.json", recovery.ATTEMPT)
        # A source-halted collector may close with exit code 0 after
        # cooperative STOP. The original proof of its complete closure and a
        # persisted SOURCE-ONLY entry halt are decisive, not the exit code.
        # A healthy voluntary STOP with no source halt cannot be rearmed below.
        need(last.get("status") == "CLOSED" and
             type(last.get("exitCode")) is int,
             "RECOVERY_REQUIRES_CLOSED_COLLECTOR")
        db = run / "inference" / ("broker-execution-" + day + ".sqlite")
        need(db.is_file() and not db.is_symlink(), "BROKER_LEDGER_MISSING")
        # The same funds evidence is reused, not re-approved, guessed from
        # bank-inclusive RSS buying power or newly created.
        source_proof, _ = load(broker["securitiesCashEvidenceFile"])
        source_document = Path(source_proof.get("sourceDocumentPath", ""))
        need(source_document.is_file(), "FUNDS_DOCUMENT_MISSING")
        allocation = funds.verify_opening_evidence(
            source_proof, session=day, account=broker["ledger"]["account"],
            now_jst=now_string, document_bytes=source_document.read_bytes(),
            require_fresh=False,
        )
        ledger_cfg = deepcopy(broker["ledger"])
        ledger_cfg["allocatedCashJpy"] = allocation["allocatedCashJpy"]
        book = led.BrokerExecutionLedger(db, ledger_cfg)
        try:
            state = book.snapshot(now_string)
            evaluation = assess(state, evidence, day, manual_confirmed=True, now=at)
            need(evaluation.get("state") == "COLLECTOR_RESTART_REVIEW_ELIGIBLE"
                 and evaluation.get("collectorRestartCandidate") is True
                 and evaluation.get("newBuyAuthorized") is False
                 and evaluation.get("orderResendAllowed") is False,
                 "BROKER_AND_LEDGER_NOT_RECONCILED")
            # An earlier SELL fill permanently halts additional BUY, but
            # must NOT prevent resumed management of other held EXITs.
            exit_only = state.get("firstSellFillBuyHalt") is True
            need(not (book.source_checkpoint("broker.unresolved") or {}),
                 "BROKER_UNRESOLVED")
            accepted = (IGNORABLE_BUY_BLOCKERS | {"AFTER_FIRST_SELL_FILL"}
                        if exit_only else IGNORABLE_BUY_BLOCKERS)
            need(set(state.get("blockers", [])) <= accepted,
                 "LEDGER_ORDER_OR_FUNDS_BLOCKERS")
            reasons = book.source_checkpoint("controller.entryHalt")
            need(type(reasons) is list and bool(reasons) and
                 set(reasons) <= SAFE_SOURCE_HALTS, "NOT_SOURCE_ONLY_HALT")
            # A repeated outage may be recovered at most three times. Every
            # event remains in the original append-only ledger chain.
            index = next((i for i in range(1, MAX_REARMS + 1)
                          if book.source_checkpoint("controller.sameRunRearm." + str(i)) is None), None)
            need(index is not None, "MAX_REARM_ATTEMPTS_REACHED")
            original = book._read()
            halt_pin = original["sourceCheckpoints"]["controller.entryHalt"]["sha256"]
            proof = {
                "schemaId": SCHEMA, "sessionDate": day,
                "runRootSha256": led.digest(str(run)),
                "brokerConfigSha256": broker_sha,
                "originalBootstrapSha256": config_bytes_sha,
                "freshBrokerObservationSha256": observation_sha,
                "previousHaltReasons": sorted(reasons),
                "previousHaltCheckpointSha256": halt_pin,
                "collectorAttempt": len(attempts),
                "matchedOrders": evaluation["matchedOrders"],
                "matchedArkPositions": evaluation["matchedArkPositions"],
                "manualConfirmed": True, "rearmedAtJst": now_string,
                "exitOnlyContinuation": exit_only,
                "noOrderResend": True, "originalLedgerPreserved": True,
                "orderTransmission": False,
            }
            result.update(status="READ_ONLY_ELIGIBLE", matchedOrders=evaluation["matchedOrders"],
                          matchedArkPositions=evaluation["matchedArkPositions"],
                          resumeRun=str(run), previousHaltReasons=sorted(reasons),
                          exitOnlyContinuation=exit_only)
            if not apply:
                return result
            # No order transport is called here. Preserve BUY halt after an
            # earlier SELL fill and restart the original EXIT-only consumer.
            book.checkpoint_source("controller.sameRunRearm." + str(index), proof, now_string)
            if exit_only:
                need(book.source_checkpoint("controller.entryHalt") == reasons,
                     "EXIT_ONLY_HALT_CHANGED")
                result["status"] = "EXIT_ONLY_NATIVE_RESUME_READY"
                result["entryHaltPreserved"] = True
            else:
                book.checkpoint_source("controller.entryHalt", [], now_string,
                                       expected_sha256=halt_pin)
                need(book.source_checkpoint("controller.entryHalt") == [],
                     "HALT_TRANSITION_FAILED")
                result["status"] = "SOURCE_HALT_REARMED_FOR_NATIVE_RESUME"
                result["entryHaltClearedAfterReconciliation"] = True
            result["rearmIndex"] = index
            result["originalLedgerPreserved"] = True
            return result
        finally:
            book.close()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--engine", type=Path, required=True)
    p.add_argument("--bootstrap", type=Path, required=True)
    p.add_argument("--observation", type=Path, required=True)
    p.add_argument("--launcher-store", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--manual-confirmed", action="store_true")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args(argv)
    try:
        result = rearm(engine_root=a.engine, bootstrap_file=a.bootstrap,
                       observation_file=a.observation, launcher_store=a.launcher_store,
                       run_root=a.run, manual_confirmed=a.manual_confirmed, apply=a.apply)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError) as e:
        reason = str(e)
        if not re.fullmatch(r"NO11_[A-Z0-9_]+", reason):
            reason = "NO11_REARM_INPUT_OR_RUNTIME_UNVERIFIED"
        print(json.dumps({"schemaId": SCHEMA, "status": "BLOCKED",
                          "reason": reason, "tradeRelaunched": False,
                          "orderResent": False, "orderTransmission": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
