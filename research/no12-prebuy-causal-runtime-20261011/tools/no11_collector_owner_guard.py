#!/usr/bin/env python3
"""Windows detached, owner-handle-bound graceful STOP for the existing C50 collector.

If the Python controller is terminated by console-window X, its finally block
is not guaranteed to run. The guard holds a SYNCHRONIZE handle to that exact
controller process (not only a recyclable PID), then requests the ORIGINAL
collector.stop protocol after the owner exits.

It NEVER kills Excel, cancels/sends orders, edits the ledger/claims, or creates
a collector .closed.json or a CLOSED attempt. A missing genuine closure stays
UNVERIFIED and still blocks recovery. Failure to attach blocks collector start.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from no11_received_run_recovery import ATTEMPT, sealed, unseal, encoded

JST = timezone(timedelta(hours=9))
ATTACHED = "ARK_NO11_COLLECTOR_OWNER_GUARD_ATTACHED_V1"
INCIDENT = "ARK_NO11_COLLECTOR_OWNER_GUARD_STOP_V1"
STOP_BYTES = b"READ_ONLY_STOP\n"
NO11_RUN = re.compile(r"session-(20\d\d-\d\d-\d\d)-[a-f0-9]{32}\Z")
NO11_ATTEMPT = re.compile(r"attempt-\d{4}\Z")
TOKEN = re.compile(r"[a-f0-9]{32}\Z")


def need(value, code):
    if not value:
        raise ValueError("NO11_OWNER_GUARD_" + code)


def owned_attempt(root, attempt, session):
    """Verify a single exact private run/attempt; no symlinks/reparse hops."""
    need(re.fullmatch(r"20\d\d-\d\d-\d\d", session) is not None, "SESSION")
    base, path = Path(root), Path(attempt)
    need(base.is_absolute() and path.is_absolute(), "ABSOLUTE_PATH")
    for obj in (base, *base.parents, path, *path.parents):
        if obj.exists() or obj.is_symlink():
            need(not obj.is_symlink() and not
                 (getattr(obj.lstat(), "st_file_attributes", 0) & 1024),
                 "REPARSE_POINT")
    need(base.is_dir() and path.is_dir(), "ROOT_OR_ATTEMPT_MISSING")
    need(path.parent.parent == base and
         NO11_RUN.fullmatch(path.parent.name) is not None and
         path.parent.name.startswith("session-" + session + "-") and
         NO11_ATTEMPT.fullmatch(path.name) is not None, "ATTEMPT_PATH_SCOPE")
    body = unseal(path / "attempt.json", ATTEMPT)
    need(body.get("sessionDate") == session and
         body.get("runRoot") == str(path.parent) and
         body.get("orderTransmission") is False and
         body.get("productionReady") is False, "ATTEMPT_CONTRACT")
    return path, body


def unique_bytes(path, raw):
    """One exclusive write; never rewrite an existing marker or receipt."""
    need(not path.exists() and not path.is_symlink(), "EXISTING_GUARD_OUTPUT")
    with path.open("xb") as fd:
        fd.write(raw)
        fd.flush()
        os.fsync(fd.fileno())


def stop_if_owner_exited(root, attempt, session, owner_pid):
    """Called ONLY when an owned, opened Windows process handle is signaled.

    This function deliberately cannot attest that the collector closed.
    It is also unit-testable without starting Excel or a broker.
    """
    path, body = owned_attempt(root, attempt, session)
    status = body.get("status")
    need(status in {"ALLOCATED", "SPAWN_REQUESTED", "RUNNING", "CONNECTED", "CLOSED"},
         "UNKNOWN_ATTEMPT_STATE")
    if status == "CLOSED":
        return "ALREADY_CLOSED_NO_ACTION"
    if status == "ALLOCATED":
        # Collector was never requested. Do not fabricate a stop or closure.
        return "ALLOCATED_NO_COLLECTOR_REQUEST"
    stop = path / "collector.stop"
    if stop.exists():
        need(stop.is_file() and not stop.is_symlink() and
             stop.read_bytes() == STOP_BYTES, "EXISTING_STOP_UNVERIFIED")
        created = False
    else:
        unique_bytes(stop, STOP_BYTES)
        created = True
    receipt = path / "owner-exit-stop-request.json"
    evidence = {
        "schemaId": INCIDENT, "sessionDate": session, "ownerProcessId": owner_pid,
        "attemptStatusAtOwnerExit": status, "stopNewlyCreated": created,
        "genuineCollectorClosedReceiptValidated": False,
        "collectorAttemptMarkedClosed": False,
        "brokerOrdersTouched": False, "excelKilled": False,
        "orderTransmission": False, "productionReady": False,
        "observedAtJst": datetime.now(JST).isoformat(timespec="milliseconds"),
    }
    # The incident is evidence of STOP request, NEVER evidence of closed workbook.
    unique_bytes(receipt, encoded(sealed(evidence)) + b"\n")
    return "OWNER_EXIT_STOP_REQUESTED_NOT_CLOSURE"


def open_exact_owner_handle(pid):
    """A real process HANDLE prevents PID-reuse false positives."""
    need(os.name == "nt" and sys.platform == "win32", "WINDOWS_ONLY")
    need(type(pid) is int and pid > 0, "OWNER_PID")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    SYNCHRONIZE = 0x00100000
    handle = kernel.OpenProcess(SYNCHRONIZE, False, pid)
    need(bool(handle), "OWNER_ATTACH_FAILED")
    return kernel, handle


def monitor(root, attempt, session, owner_pid, nonce, *, interval_ms=300):
    need(type(nonce) is str and TOKEN.fullmatch(nonce), "NONCE")
    need(100 <= interval_ms <= 2000, "INTERVAL")
    path, body = owned_attempt(root, attempt, session)
    need(body["status"] == "ALLOCATED", "ATTACH_BEFORE_COLLECTOR_SPAWN_REQUIRED")
    kernel, handle = open_exact_owner_handle(owner_pid)
    try:
        ready = {
            "schemaId": ATTACHED, "sessionDate": session,
            "ownerProcessId": owner_pid, "guardianProcessId": os.getpid(),
            "nonceSha256": hashlib.sha256(nonce.encode("ascii")).hexdigest(),
            "ownerHandleAttached": True, "brokerOrdersTouched": False,
            "orderTransmission": False, "productionReady": False,
        }
        unique_bytes(path / "owner-guard-attached.json", encoded(sealed(ready)) + b"\n")
        while True:
            status = unseal(path / "attempt.json", ATTEMPT).get("status")
            if status == "CLOSED":
                return "COLLECTOR_CLOSED_BY_ORIGINAL_CONTROLLER"
            observed = kernel.WaitForSingleObject(handle, interval_ms)
            if observed == 0x00000102:  # WAIT_TIMEOUT -- owner still alive
                continue
            need(observed == 0, "OWNER_WAIT_UNVERIFIED")  # WAIT_OBJECT_0
            return stop_if_owner_exited(root, path, session, owner_pid)
    finally:
        kernel.CloseHandle(handle)


def start_guardian(root, attempt, session, *, timeout=8.0):
    """Controller MUST obtain a sealed attached ack before spawning C50."""
    need(os.name == "nt", "WINDOWS_ONLY")
    path, body = owned_attempt(root, attempt, session)
    need(body["status"] == "ALLOCATED", "ATTACH_BEFORE_SPAWN")
    need(not (path / "owner-guard-attached.json").exists(), "ALREADY_ATTACHED")
    nonce = uuid.uuid4().hex
    cmd = [sys.executable, "-B", str(Path(__file__).resolve()), "watch",
           "--private-root", str(root), "--attempt", str(path),
           "--session", session, "--owner-pid", str(os.getpid()),
           "--nonce", nonce]
    log = path / "owner-guard-private.log"
    with log.open("xb") as stream:
        watcher = subprocess.Popen(
            cmd, cwd=str(Path(__file__).resolve().parent),
            stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
            close_fds=True, creationflags=(subprocess.DETACHED_PROCESS |
                                            subprocess.CREATE_NEW_PROCESS_GROUP))
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        attach = path / "owner-guard-attached.json"
        if attach.exists():
            report = unseal(attach, ATTACHED)
            need(report.get("sessionDate") == session and
                 report.get("ownerProcessId") == os.getpid() and
                 report.get("guardianProcessId") == watcher.pid and
                 report.get("nonceSha256") == hashlib.sha256(nonce.encode()).hexdigest()
                 and report.get("ownerHandleAttached") is True,
                 "ATTACHED_ACK_MISMATCH")
            need(watcher.poll() is None, "GUARDIAN_EXITED_EARLY")
            return watcher
        need(watcher.poll() is None, "GUARDIAN_START_FAILED")
        time.sleep(0.10)
    raise ValueError("NO11_OWNER_GUARD_HANDSHAKE_TIMEOUT")


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    subs = cli.add_subparsers(dest="command", required=True)
    watch = subs.add_parser("watch")
    watch.add_argument("--private-root", type=Path, required=True)
    watch.add_argument("--attempt", type=Path, required=True)
    watch.add_argument("--session", required=True)
    watch.add_argument("--owner-pid", type=int, required=True)
    watch.add_argument("--nonce", required=True)
    args = cli.parse_args(argv)
    if args.command == "watch":
        print(monitor(args.private_root, args.attempt, args.session,
                      args.owner_pid, args.nonce))
        print("ORDER_TRANSMISSION=False")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        code = str(exc)
        if not re.fullmatch(r"NO11_(?:OWNER_GUARD|RECOVERY)_[A-Z0-9_]+", code):
            code = "NO11_OWNER_GUARD_RUNTIME_OR_SOURCE_UNVERIFIED"
        print(code, file=sys.stderr, flush=True)
        raise SystemExit(2)
