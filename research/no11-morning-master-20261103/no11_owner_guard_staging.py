#!/usr/bin/env python3
"""Derive exact controller-only owner-guard wiring in an isolated Git checkout.

No LIVE PC installer. The frozen controller stays unchanged on the branch;
offline Windows/Linux CI executes this reversible derivation and tests it.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path

CONTROLLER = ("research/no12-prebuy-causal-runtime-20261011/tools/"
              "no11_received_session_controller.py")

EDITS = (
    (
        "from no11_received_run_recovery import RunRecovery, CaptureRelay, read, need, atomic, unseal, ATTEMPT, POSTMORTEM\n",
        "from no11_received_run_recovery import RunRecovery, CaptureRelay, read, need, atomic, unseal, ATTEMPT, POSTMORTEM\n"
        "from no11_collector_owner_guard import start_guardian\n"
    ),
    (
        "            process = popen(argv, cwd=bootstrap.ROOT, stdout=log, stderr=subprocess.STDOUT)",
        "            # ARK_NO11_COLLECTOR_CONSOLE_ISOLATION_V1: C50 must survive console X\n"
        "            # long enough to observe the original STOP and close its OWN workbook.\n"
        "            process = popen(argv, cwd=bootstrap.ROOT, stdout=log, stderr=subprocess.STDOUT,\n"
        "                            stdin=subprocess.DEVNULL, close_fds=True,\n"
        "                            creationflags=(subprocess.DETACHED_PROCESS |\n"
        "                                           subprocess.CREATE_NEW_PROCESS_GROUP))"
    ),
    (
        "    process = None\n    with (attempt.root / 'collector-private.log').open('xb') as log:",
        "    process = None\n"
        "    # ARK_NO11_OWNER_PROCESS_GUARD_V1. Attach to the exact controller OS\n"
        "    # handle BEFORE requesting or spawning the Collector; failure blocks.\n"
        "    guardian = start_guardian(config['privateRoot'], attempt.root, config['sessionDate'])\n"
        "    with (attempt.root / 'collector-private.log').open('xb') as log:"
    ),
    (
        "            def stopped():\n                if attempt.stop.exists():",
        "            def stopped():\n"
        "                bootstrap.need(guardian.poll() is None, 'OWNER_GUARD_LOST')\n"
        "                if attempt.stop.exists():"
    ),
    (
        "    print('NO11_BOOTSTRAP_STOP=COLLECTOR_AND_CONSUMER_CLOSED', flush=True)",
        "    # Only an actually CLOSED, sealed native attempt lets the guard exit.\n"
        "    bootstrap.need(guardian.wait(timeout=8) == 0, 'OWNER_GUARD_NOT_CLOSED')\n"
        "    print('NO11_BOOTSTRAP_STOP=COLLECTOR_AND_CONSUMER_CLOSED', flush=True)"
    ),
)


def replace_once(src, old, new):
    if src.count(old) != 1:
        raise ValueError("NO11_OWNER_STAGING_UNKNOWN_SOURCE_SPAN")
    return src.replace(old, new, 1)


def transform(raw):
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    source = raw.decode('utf-8-sig')
    # Windows checkout may materialize CRLF. Match reviewed LF spans, then
    # restore EXACT original newline policy; never silently normalize source.
    crlf = '\r\n' in source
    normalized = source.replace('\r\n', '\n')
    if '\r' in normalized:
        raise ValueError("NO11_OWNER_STAGING_UNKNOWN_LINE_ENDINGS")
    updated = normalized
    for old, new in EDITS:
        updated = replace_once(updated, old, new)
    inverted = updated
    for old, new in reversed(EDITS):
        inverted = replace_once(inverted, new, old)
    if inverted != normalized:
        raise ValueError("NO11_OWNER_STAGING_NONREVERSIBLE")
    ast.parse(updated)
    old_ast = ast.parse(normalized)
    new_ast = ast.parse(updated)
    def methods(tree):
        return {node.name: ast.dump(node) for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    preserved, changed = methods(old_ast), methods(new_ast)
    if preserved.keys() != changed.keys() or any(
        preserved[k] != changed[k] for k in preserved if k != 'launch_same_run'
    ):
        raise ValueError("NO11_OWNER_STAGING_ORIGINAL_CONTROLLER_SCOPE_CHANGED")
    return bom + (updated.replace('\n', '\r\n') if crlf else updated).encode('utf-8')


def stage(root):
    root = Path(root).resolve()
    if not (root / '.git').exists():
        raise ValueError("NO11_OWNER_STAGING_GIT_CHECKOUT_REQUIRED")
    target = root / CONTROLLER
    original = target.read_bytes()
    modified = transform(original)
    if modified == original:
        raise ValueError("NO11_OWNER_STAGING_DERIVATION_EMPTY")
    target.write_bytes(modified)
    print("STAGED_CONTROLLER_SHA256=" + hashlib.sha256(modified).hexdigest())
    print("NATIVE_ORDER_OR_EXIT_PATH_CHANGED=False")
    print("HISTORICAL_COLLECTOR_RECEIPT_CHANGED=False")
    print("NO11_OWNER_GUARD_PC_INSTALLED=False")


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument('--staging-checkout', type=Path, required=True)
    args = cli.parse_args()
    stage(args.staging_checkout)
