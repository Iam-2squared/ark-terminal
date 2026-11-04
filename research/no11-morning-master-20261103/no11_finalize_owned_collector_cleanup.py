#!/usr/bin/env python3
"""Finalize EXACTLY an owned Chart50 unsaved-workbook cleanup.

The original failed collector ack/ready are immutable. The Windows helper
must have verified every original book and closed only its uniquely tokened
unsaved ARK workbook. This adds a signed postmortem proof and transitions the
attempt; no original broker ledger, old receipt or order marker is erased.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

JST = timezone(timedelta(hours=9))


def need(ok, code):
    if not ok:
        raise ValueError("NO11_POSTMORTEM_" + code)


def finalize(*, config, run_path, observation_path, engine, now=None, approved=False):
    need(approved is True, "EXPLICIT_OPERATOR_ACTION")
    now = now or datetime.now(JST)
    need(now.utcoffset() == timedelta(hours=9), "TIMEZONE")
    root = Path(config.get("privateRoot", ""))
    session = now.date().isoformat()
    need(config.get("schemaId") == "ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1" and
         config.get("sessionDate") == session and
         config.get("productionReady") is False and
         config.get("orderTransmission") is False, "CONFIG")
    module_path = Path(engine).resolve() / "tools" / "no11_received_run_recovery.py"
    need(module_path.is_file(), "RECOVERY_ENGINE_MISSING")
    spec = importlib.util.spec_from_file_location("ark_no11_recovery_same_run", module_path)
    need(spec and spec.loader, "RECOVERY_MODULE")
    r = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r)
    need(hasattr(r, "POSTMORTEM"), "POSTMORTEM_RUNTIME_NOT_INSTALLED")
    manager = r.RunRecovery(config)
    run = manager._run(run_path)
    pointer = r.unseal(manager.pointer, r.POINTER)
    need(pointer.get("runRoot") == str(run), "RUN_POINTER_MISMATCH")
    attempts = sorted(run.glob("attempt-*"))
    need(attempts and len(attempts) <= 16, "ATTEMPTS")
    attempt_dir = attempts[-1]
    a = r.unseal(attempt_dir / "attempt.json", r.ATTEMPT)
    need(a.get("status") == "CONNECTED" and
         a.get("sessionDate") == session and a.get("runRoot") == str(run) and
         type(a.get("pid")) is int and a["pid"] > 0, "FAILED_ATTEMPT_IDENTITY")
    ready, ready_sha = r.read(attempt_dir / "collector-ready.json", 100_000)
    closed, closed_sha = r.read(attempt_dir / "collector-ready.json.closed.json", 100_000)
    expected = ready.get("temporaryWorkbook", {})
    need(type(expected) is dict and
         expected.get("identitySheet") == "ARK_NO11_CUMULATIVE" and
         expected.get("identityCell") == "G1" and
         isinstance(expected.get("identityValue"), str) and
         expected["identityValue"].startswith("ARK_NO11_C50_TEMP_") and
         ready.get("sessionDate") == session and
         ready.get("processId") == a["pid"] and
         ready.get("orderTransmission") is False and
         a.get("readySha256") == ready_sha and
         closed.get("schemaId") == "ARK_NO11_C50_COLLECTOR_CLOSED_V1" and
         closed.get("sessionDate") == session and
         closed.get("processId") == a["pid"] and
         closed.get("temporaryWorkbookClosed") is False and
         closed.get("collectorFailed") is True and
         closed.get("orderTransmission") is False,
         "ORIGINAL_RECEIPTS")
    cleanup = Path(observation_path)
    need(cleanup.parent == attempt_dir and not cleanup.is_symlink(), "CLEANUP_REPORT_SCOPE")
    report, _ = r.read(cleanup, 100_000)
    need(type(report) is dict and
         report.get("schemaId") == "ARK_NO11_C50_OWNED_TEMP_CLOSURE_OBSERVED_V1" and
         report.get("sessionDate") == session and
         report.get("collectorPid") == a["pid"] and
         report.get("ownedTemporaryToken") == expected["identityValue"] and
         report.get("ownedUnsavedWorkbookClosed") is True and
         report.get("originalBooksUnchanged") is True and
         report.get("collectorProcessNotRunning") is True and
         report.get("readOnlyBrokerInspection") is True and
         report.get("orderTransmission") is False,
         "INDEPENDENT_CLOSURE_REPORT")
    observed = datetime.fromisoformat(report["verifiedAtJst"])
    need(observed.date().isoformat() == session and
         observed.utcoffset() == timedelta(hours=9) and
         0 <= (now - observed).total_seconds() <= 120,
         "CLOSURE_REPORT_NOT_FRESH")
    post = attempt_dir / "collector-postmortem-cleanup.json"
    archive = attempt_dir / "attempt.before-postmortem.json"
    need(not post.exists() and not archive.exists(), "RECOVERY_ALREADY_USED")
    # The immutable original bytes are retained before writing any new state.
    old = (attempt_dir / "attempt.json").read_bytes()
    with archive.open("xb") as f:
        f.write(old)
        f.flush()
        os.fsync(f.fileno())
    need(archive.read_bytes() == old, "BACKUP_NOT_EXACT")
    proof = {
        "schemaId": r.POSTMORTEM,
        "sessionDate": session,
        "collectorPid": a["pid"],
        "originalClosedReceiptSha256": closed_sha,
        "originalReadyReceiptSha256": ready_sha,
        "ownedTemporaryToken": expected["identityValue"],
        "ownedUnsavedWorkbookClosed": True,
        "originalBooksUnchanged": True,
        "claimedByOneClickRecovery": True,
        "operatorApproved": True,
        "closureReportSha256": hashlib.sha256(cleanup.read_bytes()).hexdigest(),
        "productionReady": False,
        "orderTransmission": False,
    }
    # Original receipt NEVER rewritten; this is a new, independently sealed
    # attestation using the same recovery schema hash.
    with post.open("xb") as f:
        f.write(r.encoded(r.sealed(proof)) + b"\n")
        f.flush()
        os.fsync(f.fileno())
    item = r.Attempt(attempt_dir, session)
    item._write({"CONNECTED"}, status="CLOSED", exitCode=2, closedSha256=closed_sha)
    need(manager.history(run) is not None, "POSTMORTEM_REPLAY_FAILED")
    return {
        "schemaId": r.POSTMORTEM,
        "status": "OWNED_C50_CLEANUP_PROVEN",
        "sessionDate": session,
        "entryHaltStillActive": True,
        "ledgerModified": False,
        "brokerOrdersModified": False,
        "historicalReceiptModified": False,
        "orderTransmission": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--bootstrap", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--engine", type=Path, required=True)
    p.add_argument("--operator-approved", action="store_true")
    args = p.parse_args(argv)
    try:
        cfg = json.loads(args.bootstrap.read_bytes().decode("utf-8-sig"))
        print(json.dumps(finalize(config=cfg, run_path=args.run, observation_path=args.report,
                                 engine=args.engine, approved=args.operator_approved),
                         ensure_ascii=False, separators=(",", ":")))
    except (OSError, ValueError, KeyError, TypeError, ImportError, json.JSONDecodeError):
        print(json.dumps({"status": "BLOCKED_UNVERIFIED_POSTMORTEM",
                          "orderTransmission": False, "ledgerModified": False}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
