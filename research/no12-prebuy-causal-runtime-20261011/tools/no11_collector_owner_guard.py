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

from no11_received_run_recovery import ATTEMPT, Attempt, read, sealed, unseal, encoded

JST = timezone(timedelta(hours=9))
ATTACHED = "ARK_NO11_COLLECTOR_OWNER_GUARD_ATTACHED_V1"
INCIDENT = "ARK_NO11_COLLECTOR_OWNER_GUARD_STOP_V1"
COLLECTOR_ATTACHED = "ARK_NO11_COLLECTOR_OWNER_GUARD_COLLECTOR_ATTACHED_V1"
NATIVE_CLOSED = "ARK_NO11_COLLECTOR_OWNER_GUARD_GENUINE_CLOSED_V1"
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


def wait_collector_attached(watcher, attempt, pid, *, timeout=8.0):
    """Controller waits for a verified C50 PROCESS HANDLE before proceeding.

    Without a durable child attachment, X may race with a recyclable PID.
    Fail closed rather than letting the broker/consumer start unprotected.
    """
    need(type(pid) is int and pid > 0, "COLLECTOR_PID_INVALID")
    path = Path(attempt)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        attach = path / "collector-guard-attached.json"
        if attach.exists():
            body = unseal(attach, COLLECTOR_ATTACHED)
            need(body.get("collectorProcessId") == pid and
                 body.get("guardianProcessId") == watcher.pid and
                 body.get("collectorHandleAttached") is True and
                 body.get("orderTransmission") is False,
                 "COLLECTOR_ATTACH_ACK_CHANGED")
            need(watcher.poll() is None, "GUARDIAN_EXITED_BEFORE_C50")
            return
        need(watcher.poll() is None, "GUARDIAN_EXITED_BEFORE_C50")
        time.sleep(0.10)
    raise ValueError("NO11_OWNER_GUARD_COLLECTOR_ATTACH_TIMEOUT")


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
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    SYNCHRONIZE = 0x00100000
    handle = kernel.OpenProcess(SYNCHRONIZE, False, pid)
    need(bool(handle), "OWNER_ATTACH_FAILED")
    return kernel, handle


def _verified_native_closure(path, session, pid, code):
    """No synthetic receipt. Check the actual native PS C50 close and exit.

    A controller killed by X cannot call Attempt.close_confirmed itself. The
    guard may call that EXACT original transition only after its previously
    attached OS handle proves the original Collector PID exited with code 0
    and the original native CLOSED receipt proves the workbook was closed.
    """
    need(type(code) is int and code == 0, "COLLECTOR_EXIT_NOT_CLEAN")
    body = unseal(path / "attempt.json", ATTEMPT)
    need(body.get("status") == "CONNECTED" and body.get("pid") == pid,
         "COLLECTOR_NOT_CONNECTED")
    original_ready, ready_hash = read(path / "collector-ready.json", 100_000)
    need(ready_hash == body.get("readySha256") and
         original_ready.get("processId") == pid and
         original_ready.get("sessionDate") == session,
         "NATIVE_READY_NOT_PINNED")
    original_close, closed_hash = read(
        path / "collector-ready.json.closed.json", 100_000)
    need(original_close.get("schemaId") == "ARK_NO11_C50_COLLECTOR_CLOSED_V1"
         and original_close.get("sessionDate") == session
         and original_close.get("processId") == pid
         and original_close.get("temporaryWorkbookClosed") is True
         and original_close.get("collectorFailed") is False
         and original_close.get("orderTransmission") is False,
         "NATIVE_CLOSE_NOT_GENUINE")
    class Exited:
        def __init__(self, original_pid, original_code):
            self.pid, self._code = original_pid, original_code

        def poll(self):
            return self._code

    Attempt(path, session).close_confirmed(Exited(pid, code))
    after = unseal(path / "attempt.json", ATTEMPT)
    need(after.get("status") == "CLOSED" and
         after.get("closedSha256") == closed_hash and
         after.get("exitCode") == code, "CLOSE_TRANSITION_NOT_PROVEN")
    unique_bytes(path / "owner-exit-genuine-close-verified.json", encoded(sealed({
        "schemaId": NATIVE_CLOSED,
        "sessionDate": session,
        "collectorProcessId": pid,
        "realNativeClosedReceiptSha256": closed_hash,
        "originalAttemptClosedUsingNativeReceipt": True,
        "nativeExitCode": code,
        "ordersCancelled": False,
        "brokerOrdersTouched": False,
        "orderTransmission": False,
        "productionReady": False,
    })) + b"\n")
    return "OWNER_EXIT_GENUINE_NATIVE_CLOSE_VERIFIED"


def monitor(root, attempt, session, owner_pid, nonce, *, interval_ms=300):
    need(type(nonce) is str and TOKEN.fullmatch(nonce), "NONCE")
    need(100 <= interval_ms <= 2000, "INTERVAL")
    path, body = owned_attempt(root, attempt, session)
    need(body["status"] == "ALLOCATED", "ATTACH_BEFORE_COLLECTOR_SPAWN_REQUIRED")
    kernel, owner_handle = open_exact_owner_handle(owner_pid)
    collector_handle = None
    collector_pid = None
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
            body = unseal(path / "attempt.json", ATTEMPT)
            status = body.get("status")
            if status == "CLOSED":
                return "COLLECTOR_CLOSED_BY_ORIGINAL_CONTROLLER"
            if status in ("RUNNING", "CONNECTED") and collector_handle is None:
                pid = body.get("pid")
                if type(pid) is int and pid > 0:
                    # Attach only while the original owner is still alive;
                    # after it exits an OS PID alone may refer to a new process.
                    if kernel.WaitForSingleObject(owner_handle, 0) == 0x00000102:
                        collector_handle = kernel.OpenProcess(
                            0x00100000 | 0x1000, False, pid)
                        need(bool(collector_handle), "COLLECTOR_HANDLE_ATTACH_FAILED")
                        collector_pid = pid
                        unique_bytes(path / "collector-guard-attached.json", encoded(sealed({
                            "schemaId": COLLECTOR_ATTACHED, "sessionDate": session,
                            "guardianProcessId": os.getpid(),
                            "collectorProcessId": pid,
                            "collectorHandleAttached": True,
                            "orderTransmission": False, "productionReady": False,
                        })) + b"\n")
            observed = kernel.WaitForSingleObject(owner_handle, interval_ms)
            if observed == 0x00000102:
                continue
            need(observed == 0, "OWNER_WAIT_UNVERIFIED")
            outcome = stop_if_owner_exited(root, path, session, owner_pid)
            if outcome != "OWNER_EXIT_STOP_REQUESTED_NOT_CLOSURE":
                return outcome
            if collector_handle is None:
                return "OWNER_EXIT_STOP_ONLY_CHILD_NOT_ATTACHED"
            # The detached C50 child processes its original STOP and closes
            # its own unsaved workbook; a timeout leaves CONNECTED, NOT CLOSED.
            native = kernel.WaitForSingleObject(collector_handle, 90_000)
            if native != 0:
                return "OWNER_EXIT_STOP_ONLY_NATIVE_CLOSE_UNVERIFIED"
            code = wintypes.DWORD()
            need(kernel.GetExitCodeProcess(collector_handle, ctypes.byref(code)),
                 "COLLECTOR_EXIT_CODE_UNVERIFIED")
            return _verified_native_closure(path, session, collector_pid, int(code.value))
    finally:
        if collector_handle is not None:
            kernel.CloseHandle(collector_handle)
        kernel.CloseHandle(owner_handle)


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
