"""Permanent, journaled OneClick V2 local-overlay compatibility migration.

Applies only to a COMPLETE, byte-for-byte verified Display V2 installation
whose legacy white launcher still refers to the old $trading variable inside
an additional disabled-trading overlay. Does not import broker modules, launch
a trading engine, reset a claim, touch Excel, or alter an action callback.
Default operation is read-only audit.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
from pathlib import Path
import re
import sys

import install_no11_oneclick_display_v2 as previous
import no11_nightly_resume as journal_io
import no11_oneclick_display_transform as display_migration

JOURNAL = "oneclick-display-v2-overlay-compat-install.json"
KIND = "ARK_NO11_DISPLAY_V2_OVERLAY_COMPAT_V1"
MARK = "# ARK_NO11_DISPLAY_V2_OVERLAY_COMPAT_V1"
OLD_OVERLAY = "  if($trading -match 'ENTRY HALTED'){"
NEW_OVERLAY = (
    "  " + MARK + "\n"
    "  $trading=[string]$view.trading\n"
    "  Need (-not [string]::IsNullOrWhiteSpace($trading)) 'DISPLAY_V2_TRADING_MISSING'\n"
    + OLD_OVERLAY
)
OLD_CAPTION = (
    "  $trade.Text=if($retryReady){'RETRY START TRADING / NORMAL MAX3'}"
    "else{'START TRADING   /   NORMAL MAX3'}"
)
NEW_CAPTION = (
    "   $trade.Text=if($retryReady){'RETRY START TRADING / NORMAL MAX3'}"
    "else{[string]$view.buttons.trade}"
)


def need(ok, code):
    if not ok:
        raise ValueError("NO11_OVERLAY_COMPAT_" + code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def change(before):
    """Only two exact display-only substitutions, preserving all other bytes."""
    body = before.decode("utf-8-sig")
    canonical = body.replace("\r\n", "\n")
    need("\r" not in canonical, "UNSUPPORTED_LINE_ENDING")
    need(body.count(display_migration.MARK) == 1, "DISPLAY_V2_NOT_INSTALLED")
    need(body.count(display_migration.NEW_TOOL) == 1, "V2_ENTRY_MISSING")
    need(canonical.count(MARK) == 0, "ALREADY_CHANGED")
    need(canonical.count(OLD_OVERLAY) == 1 and canonical.count(OLD_CAPTION) == 1,
         "UNRECOGNIZED_OVERLAY")
    # Require the exact existing published pre-order-retry Enabled gate. This
    # compatibility update never accepts a newly weakened authorization line.
    approved_trade_gate = ("  $trade.Enabled=(($s.canRequestTrade -eq $true) -or "
                           "$preopen) -and (-not $reserved) -or $retryReady")
    need(canonical.count(approved_trade_gate) == 1, "UNKNOWN_TRADE_AUTHORIZATION")
    need(canonical.count("$script:No11DisplayTip.SetToolTip($status,[string]$view.details)") == 1,
         "V2_DISPLAY_REGION_CHANGED")
    # A real existing overlay is mandatory: never fabricate one for another UI.
    prefix = canonical.split("function RefreshUi{", 1)
    need(len(prefix) == 2 and re.search(
        r"(?m)^[ \t]*\$disabledTradeOverlay[ \t]*=[ \t]*New-Object\b", prefix[0])
        and "$disabledTradeOverlay.Text=" in prefix[1], "OVERLAY_OBJECT_UNVERIFIED")
    need(canonical.index(OLD_OVERLAY) > canonical.index("function RefreshUi{")
         and canonical.index(OLD_OVERLAY) < canonical.index("  $trade.Enabled=")
         and canonical.index(OLD_CAPTION) < canonical.index("  $nightly.Enabled="),
         "OVERLAY_PLACEMENT_UNVERIFIED")
    normalized_new = canonical.replace(OLD_OVERLAY, NEW_OVERLAY, 1).replace(
        OLD_CAPTION, NEW_CAPTION, 1)
    # Unmodified body is guaranteed, including unrelated white-theme patches,
    # selection header, preserved retry gates and all button callbacks.
    normalized_back = normalized_new.replace(NEW_OVERLAY, OLD_OVERLAY, 1).replace(
        NEW_CAPTION, OLD_CAPTION, 1)
    need(normalized_back == canonical, "TRANSFORM_NOT_REVERSIBLE")
    newline = "\r\n" if "\r\n" in body else "\n"
    need(not ("\r\n" in body and "\n" in body.replace("\r\n", "")),
         "MIXED_LINE_ENDINGS_UNVERIFIED")
    new_body = normalized_new.replace("\n", newline)
    result = (b"\xef\xbb\xbf" if before.startswith(b"\xef\xbb\xbf") else b"") + new_body.encode("utf-8")
    need(result != before, "NO_CHANGE")
    # Compare the actual enabled assignments/callback source, not merely
    # output labels. None may be moved, enabled, or changed.
    for token in ("$trade.Enabled=", "$nightly.Enabled=", "$review.Enabled=",
                  "$trade.Add_Click({", "$nightly.Add_Click({", "$review.Add_Click({",
                  "$refresh.Add_Click({RefreshUi})", "$timer.Add_Tick({RefreshUi})"):
        old_rows = [row for row in canonical.splitlines() if token in row]
        new_rows = [row for row in normalized_new.splitlines() if token in row]
        need(old_rows and old_rows == new_rows, "ACTION_OR_AUTHORIZATION_CHANGED")
    return result


def context(store):
    store = journal_io.safe(store, True)
    home, launcher, legacy, engine, external = previous.context(store)
    original_journal = journal_io.safe(store / previous.JOURNAL)
    original_record = journal_io.checkpoint(original_journal)
    need(original_record.get("kind") == previous.KIND
         and original_record.get("phase") == "COMPLETE"
         and original_record.get("launcher") == str(launcher)
         and original_record.get("home") == str(home), "ORIGINAL_INSTALL_UNVERIFIED")
    try:
        original_after = base64.b64decode(original_record["after"], validate=True)
    except (KeyError, ValueError) as exc:
        raise ValueError("NO11_OVERLAY_COMPAT_ORIGINAL_RECEIPT_INVALID") from exc
    need(display_migration.MARK.encode("ascii") in original_after,
         "ORIGINAL_DISPLAY_NOT_INSTALLED")
    return store, home, launcher, legacy, engine, external, original_journal, original_after


def expected(store):
    (store, home, launcher, legacy, engine, external,
     original_journal, original_after) = context(store)
    new = change(original_after)
    return {
        "schemaId": journal_io.SCHEMA, "kind": KIND, "phase": "PREPARED",
        "orderTransmission": False, "tradeStarted": False,
        "launcher": str(launcher), "home": str(home),
        "originalDisplayJournalSha256": digest(original_journal.read_bytes()),
        "originalNativeStatusSha256": digest(legacy.read_bytes()),
        "originalLauncherSha256": digest(original_after),
        "updatedLauncherSha256": digest(new),
        "before": base64.b64encode(original_after).decode("ascii"),
        "after": base64.b64encode(new).decode("ascii"),
        "frozen": previous.inventory(home, launcher, engine, external),
    }


def audit(store):
    store = journal_io.safe(store, True)
    base = expected(store)
    (store, home, launcher, legacy, engine, external,
     original_journal, original_after) = context(store)
    receipt = store / JOURNAL
    current = launcher.read_bytes()
    after = base64.b64decode(base["after"], validate=True)
    if not receipt.exists():
        need(current == original_after, "LAUNCHER_CONCURRENT_OR_UNKNOWN")
        return "READY_NOT_APPLIED", base, None
    saved = journal_io.checkpoint(receipt)
    need(saved.get("schemaId") == journal_io.SCHEMA
         and saved.get("kind") == KIND
         and saved.get("phase") in ("PREPARED", "COMPLETE")
         and saved.get("orderTransmission") is False
         and saved.get("tradeStarted") is False, "PATCH_JOURNAL_UNVERIFIED")
    for key in base:
        if key != "phase" and not (key == "frozen" and saved["phase"] == "COMPLETE"):
            need(saved.get(key) == base[key], "PATCH_JOURNAL_CHANGED_" + key.upper())
    if saved["phase"] == "COMPLETE":
        need(current == after, "INSTALLED_LAUNCHER_CHANGED")
        return "ALREADY_APPLIED", base, saved
    need(current in (original_after, after), "INTERRUPTED_LAUNCHER_CHANGED")
    need(previous.inventory(home, launcher, engine, external) == base["frozen"],
         "SOURCE_CHANGED_DURING_INTERRUPTION")
    return "INTERRUPTED_REQUIRES_APPLY", base, saved


def install(store, *, apply=False):
    state, base, saved = audit(store)
    if not apply:
        return state
    previous.gate()  # After-hours, no ARK/OneClick workers or unreadable processes.
    store = journal_io.safe(store, True)
    with journal_io.exclusive(store / "unified-refresh-install.lock"):
        previous.gate()
        state, base, saved = audit(store)
        if state == "ALREADY_APPLIED":
            return state
        launcher = journal_io.safe(base["launcher"])
        before = base64.b64decode(base["before"], validate=True)
        after = base64.b64decode(base["after"], validate=True)
        previous.parse_launcher(after)  # Real Windows PowerShell 5.1 syntax.
        receipt = store / JOURNAL
        if not receipt.exists():
            journal_io.atomic(receipt, base)
        state, base, saved = audit(store)
        if launcher.read_bytes() == before:
            previous.replace_exact(launcher, before, after)
        need(launcher.read_bytes() == after, "LAUNCHER_READBACK_FAILED")
        state, base, saved = audit(store)
        need(state == "INTERRUPTED_REQUIRES_APPLY", "INSTALL_SEQUENCE_INVALID")
        finished = dict(saved)
        finished["phase"] = "COMPLETE"
        journal_io.atomic(receipt, finished)
        state, _, _ = audit(store)
        need(state == "ALREADY_APPLIED", "FINAL_RECHECK_FAILED")
        return "APPLIED_NO_TRADE"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        status = install(args.store, apply=args.apply)
        print("NO11_ONECLICK_DISPLAY_V2_OVERLAY=" + status)
        print("ONECLICK_WHITE_THEME_AND_ACTIONS=PRESERVED")
        print("NATIVE_STATUS_AND_BROKER_SOURCES=UNCHANGED")
        print("EXISTING_DISPLAY_V2_RECEIPT=PRESERVED")
        return 0
    except Exception as exc:
        code = str(exc)
        if re.fullmatch(r"NO11_[A-Z0-9_]+", code) is None:
            code = "NO11_OVERLAY_COMPAT_UNVERIFIED_SOURCE_OR_IO"
        print("NO11_ONECLICK_DISPLAY_V2_OVERLAY=BLOCKED|" + code)
        print("DO_NOT_RESET_EXISTING_INSTALL_JOURNAL=True")
        return 2
    finally:
        print("TRADE_STARTED=False")
        print("ORDER_TRANSMISSION=False")


if __name__ == "__main__":
    sys.exit(main())
