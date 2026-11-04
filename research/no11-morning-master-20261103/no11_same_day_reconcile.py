#!/usr/bin/env python3
"""Audit-only by default; explicitly reconcile one closed failed Chart50 attempt.

No orders, cancels, Excel operations or automatic launch. An --apply needs
fresh independent read-only broker evidence and operator confirmation.
Never delete/reinitialize any LIVE ledger, source, or start marker.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1] / "no12-prebuy-causal-runtime-20261011"
sys.path.insert(0, str(ROOT / "tools"))
import no11_received_session_bootstrap as bootstrap
import no11_received_run_recovery as recovery
import no11_broker_execution_ledger as ledger

JST = timezone(timedelta(hours=9))
ALLOWED = {"NO11_BOOTSTRAP_COLLECTOR_FAILED", "NO11_SERVICE_CAPTURE_STOPPED_OR_STALE"}

def need(value, reason):
    if not value:
        raise RuntimeError("NO11_SAMEDAY_RECOVERY_" + reason)

def jst_now():
    return datetime.now(JST)

def load(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), "FILE_NOT_FOUND")
    data = path.read_bytes()
    need(0 < len(data) <= 25_000_000, "FILE_SIZE")
    return json.loads(data.decode("utf-8-sig")), hashlib.sha256(data).hexdigest()

def do_reconcile(args):
    need(args.session == jst_now().date().isoformat(), "NOT_TODAY")
    need(jst_now().strftime("%H:%M") < "15:20", "ENTRY_CUTOFF")
    config_raw, _ = load(args.bootstrap)
    config = bootstrap.validate_config(config_raw, allow_explicit_live=True)
    need(config["sessionDate"] == args.session, "CONFIG_DATE")
    need(config.get("shadowAccountConfig") is None, "SHADOW_PORTFOLIO_NEEDS_SEPARATE_REVIEW")
    root = Path(config["privateRoot"])
    run = recovery.RunRecovery(config)
    pointer = recovery.unseal(run.pointer, recovery.POINTER)
    run_root = Path(pointer["runRoot"])
    need(run_root.is_dir() and run_root.parent == root, "RUN_IDENTITY")
    contract = recovery.unseal(run_root / "run-contract.json", recovery.CONTRACT)
    need(contract["runRoot"] == str(run_root)
         and pointer["contractSha256"] == recovery.digest(contract)
         and contract["configSha256"] == recovery.digest(config), "RUN_CONTRACT")
    attempts = sorted(run_root.glob("attempt-*"))
    need(len(attempts) == 1, "MULTIPLE_ATTEMPTS_REVIEW")
    attempt_root = attempts[0]
    attempt = recovery.unseal(attempt_root / "attempt.json", recovery.ATTEMPT)
    need(attempt.get("status") in ("CONNECTED", "CLOSED"), "ATTEMPT_STATE")
    need(attempt["sessionDate"] == args.session and attempt["runRoot"] == str(run_root), "ATTEMPT_IDENTITY")
    ready, ready_sha = recovery.read(attempt_root / "collector-ready.json", 100_000)
    closed, closed_sha = recovery.read(attempt_root / "collector-ready.json.closed.json", 100_000)
    need(attempt["readySha256"] == ready_sha and ready["processId"] == attempt["pid"]
         and ready["sessionDate"] == args.session and ready.get("captureFolder") == attempt.get("captureFolder"),
         "READY_PIN")
    need(closed.get("schemaId") == "ARK_NO11_C50_COLLECTOR_CLOSED_V1"
         and closed.get("processId") == attempt["pid"] and closed.get("sessionDate") == args.session
         and closed.get("temporaryWorkbookClosed") is True
         and closed.get("collectorFailed") is True
         and closed.get("orderTransmission") is False, "CLOSED_RECEIPT")
    if attempt["status"] == "CLOSED":
        need(attempt["closedSha256"] == closed_sha and attempt.get("exitCode") == 2, "CLOSED_ATTEMPT_CHANGED")
    need(not (root / "bootstrap-recovery-required.json").exists(), "EXPLICIT_RECOVERY_MARKER")
    # The old trade marker is part of the preserved one-launch history.
    marker = Path(args.launcher_store) / ("TRADE-" + args.session + ".launch.json")
    mark, _ = load(marker)
    need(mark.get("kind") == "TRADE" and mark.get("asOfDate") == args.session,
         "TRADE_MARKER_MISSING")
    need(mark.get("sourceSha256") == hashlib.sha256(Path(args.bootstrap).read_bytes()).hexdigest(),
         "BOOTSTRAP_CHANGED")
    bro, bro_sha = load(config["brokerExecutionConfig"])
    need(bro.get("sessionDate") == args.session
         and bro.get("fundingPolicy") == "RSS_BUYING_POWER"
         and bro.get("ledger", {}).get("allocatedCashJpy") == "AUTO_RSS_BUYING_POWER"
         and bro.get("transport", {}).get("mode") == "LIVE"
         and bro.get("transport", {}).get("approvedForSession") is True, "BROKER_CONFIG")
    funds, _ = load(run_root / "inference" / ("rss-opening-funding-" + args.session + ".json"))
    checksum = funds.get("receiptSha256")
    body = dict(funds);body.pop("receiptSha256", None)
    need(checksum == ledger.digest(body) and funds.get("configSha256") == ledger.digest(bro)
         and funds.get("sessionDate") == args.session, "OPENING_FUNDS_RECEIPT")
    ledger_config = deepcopy(bro["ledger"])
    ledger_config["allocatedCashJpy"] = funds["allocatedCashJpy"]
    ledger_config["externalSymbols"] = funds["externalSymbols"]
    database = run_root / "inference" / ("broker-execution-" + args.session + ".sqlite")
    need(database.is_file(), "LEDGER_MISSING")
    # The read-only observation is collected independently from the stopped LIVE process.
    fresh, obs_sha = load(args.observation)
    external = fresh.get("brokerObservation", {})
    need(fresh.get("status") == "OBSERVED" and fresh.get("readOnly") is True
         and fresh.get("orderTransmission") is False and external.get("status") == "OBSERVED"
         and external.get("completeTables") is True
         and external.get("sameSnapshotVerified") is True
         and external.get("rowsTruncated") is False, "BROKER_NOT_OBSERVED")
    for field in ("idRows", "orders", "executions"):
        need(external.get(field) == [] and fresh.get("snapshot", {}).get(
            "orders" if field == "orders" else "executions" if field == "executions" else "orders") == [],
            "BROKER_HAS_" + field.upper())
    obs_time = datetime.fromisoformat(external["captureCompletedAt"])
    need(obs_time.utcoffset() == timedelta(hours=9)
         and 0 <= (jst_now()-obs_time).total_seconds() <= 60, "BROKER_OBSERVATION_STALE")
    with bootstrap.service.exclusive_service(root):
        book = ledger.BrokerExecutionLedger(database, ledger_config)
        try:
            state = book.snapshot(jst_now().isoformat(timespec="milliseconds"))
            need(not state["orders"] and not state["positions"] and not state["commands"]
                 and not state.get("dispatchStarted") and not state.get("firstSellFillBuyHalt"),
                 "PRIOR_ORDER_OR_POSITION")
            need(not (book.source_checkpoint("broker.unresolved") or {}),
                 "UNRESOLVED_BROKER")
            reasons = book.source_checkpoint("controller.entryHalt") or []
            need(type(reasons) is list and set(reasons) == ALLOWED, "HALT_REASON_NOT_RECOVERABLE")
            need(set(state.get("blockers", [])) <= {"FRESH_BUYING_POWER_REQUIRED"},
                 "OTHER_LEDGER_BLOCKERS")
            print("RECOVERY_REVIEW=ELIGIBLE_CLOSED_FAILED_COLLECTOR")
            print("LEDGER_ORDERS=0")
            print("LEDGER_COMMANDS=0")
            print("LEDGER_POSITIONS=0")
            print("FRESH_BROKER_ORDERS=0")
            print("OLD_HALT_REASONS=" + ",".join(reasons))
            if not args.apply:
                print("FILES_MODIFIED=False")
                print("ORDER_TRANSMISSION=False")
                return
            need(args.i_approve_today, "EXPLICIT_APPROVAL_REQUIRED")
            need(jst_now().strftime("%H:%M") < "15:20", "ENTRY_CUTOFF")
            if attempt["status"] == "CONNECTED":
                # Archived signed attempt before audited state transition.
                archive = attempt_root / "attempt.pre-reconciliation.json"
                need(not archive.exists(), "BACKUP_ALREADY_EXISTS")
                archive.write_bytes((attempt_root / "attempt.json").read_bytes())
                assert hash(archive.read_bytes()) == hash((attempt_root / "attempt.json").read_bytes())
                item = recovery.Attempt(attempt_root, args.session)
                item._write({"CONNECTED"}, status="CLOSED", exitCode=2, closedSha256=closed_sha)
            restored = run.restore(run_root)
            need(restored["sessionDate"] == args.session, "RESTORE_REJECTED")
            at = jst_now().isoformat(timespec="milliseconds")
            # Ledger events remain in the append-only chain. Never erase the failed event.
            proof = {"schemaId": "ARK_NO11_SAMEDAY_RECOVERY_AUDIT_V1",
                     "sessionDate": args.session, "oldHaltReasons": sorted(reasons),
                     "closedReceiptSha256": closed_sha, "freshBrokerObservationSha256": obs_sha,
                     "brokerConfigSha256": bro_sha, "runRootSha256": ledger.digest(str(run_root)),
                     "operatorApproved": True, "recoveredAtJst": at}
            need(book.source_checkpoint("controller.samedayRecovery") is None,
                 "RECOVERY_ALREADY_USED")
            book.checkpoint_source("controller.samedayRecovery", proof, at)
            saved = book._read()["sourceCheckpoints"]["controller.entryHalt"]
            book.checkpoint_source("controller.entryHalt", [], at, expected_sha256=saved["sha256"])
            need(book.source_checkpoint("controller.entryHalt") == [], "RECOVERY_NOT_APPLIED")
            print("SAME_DAY_RUN_RECONCILED=PASS")
            print("ENTRY_HALT_AUDIT_PRESERVED=True")
            print("LIVE_LEDGER_PRESERVED=True")
            print("ORDER_SENT_BY_RECOVERY=False")
            print("RUN_PATH=" + str(run_root))
        finally:
            book.close()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--session", required=True)
    p.add_argument("--bootstrap", required=True, type=Path)
    p.add_argument("--observation", required=True, type=Path)
    p.add_argument("--launcher-store", required=True, type=Path)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--i-approve-today", action="store_true")
    try:
        do_reconcile(p.parse_args())
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as e:
        text = str(e)
        code = text if text.startswith("NO11_SAMEDAY_RECOVERY_") else "NO11_SAMEDAY_RECOVERY_REVIEW_FAILED"
        print(code, file=sys.stderr)
        raise SystemExit(2)
