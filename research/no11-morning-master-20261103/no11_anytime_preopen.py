"""Offline, source-pinned widening of same-day standby to 00:00–08:59 JST.

DO NOT directly edit installed OneClick/Display sidecars: the existing V2,
overlay, and preopen receipts pin those files. This creates a candidate-only
delta for a separately journaled after-close release. It changes neither
native Trade approval nor any 09:00–09:02 launch constraint.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from no11_oneclick_display_transform import replace_regions

MORNING = "research/no11-morning-master-20261103/"
MARK = "ARK_NO11_ANYTIME_SAME_DAY_STANDBY_V1"

WORKER_EDITS = (
    ("# ARK No.1.1 — operator-approved 08:30-08:59 JST standby.",
     "# ARK No.1.1 — operator-approved same-day 00:00-08:59 JST standby."),
    ("         $t.ToString('HH:mm:ss') -ge '08:30:00' -and",
     "         $t.ToString('HH:mm:ss') -ge '00:00:00' -and"),
    (" Need (-not (IsArmWindow ([DateTimeOffset]::Parse('2026-11-05T08:29:59+09:00')))) 'SELFTEST_BEFORE_0830'",
     " Need (IsArmWindow ([DateTimeOffset]::Parse('2026-11-05T00:00:00+09:00'))) 'SELFTEST_MIDNIGHT'"),
    (" Need (IsArmWindow ([DateTimeOffset]::Parse('2026-11-05T08:30:00+09:00'))) 'SELFTEST_0830'",
     " Need (IsArmWindow ([DateTimeOffset]::Parse('2026-11-05T08:29:59+09:00'))) 'SELFTEST_EARLY'\n Need (IsArmWindow ([DateTimeOffset]::Parse('2026-11-05T08:30:00+09:00'))) 'SELFTEST_0830'"),
    ("'ARM_WINDOW_0830_TO_0900_ONLY'", "'ARM_WINDOW_SAME_DAY_BEFORE_0900_ONLY'"),
)
UI_EDITS = (
    ("# Status is read-only: only same-day, source-verified 08:30-08:59 can queue.",
     "# Status is read-only: same-day, source-verified 00:00-08:59 can queue."),
    ("    $now.ToString('HH:mm:ss') -lt '08:30:00' -or",
     "    $now.ToString('HH:mm:ss') -lt '00:00:00' -or"),
    ("'08:30 STANDBY READY - 09:00 AUTO START'",
     "'STANDBY READY - 09:00 AUTO START'"),
    ("'ARK - 08:30 STANDBY FOR 09:00'",
     "'ARK - SAME-DAY STANDBY FOR 09:00'"),
)
DISPLAY_EDITS = (
    ("not '08:30:00' <= issued.strftime('%H:%M:%S') < '09:00:00'",
     "not '00:00:00' <= issued.strftime('%H:%M:%S') < '09:00:00'"),
    ("reserved.get('state') == 'RESERVED_RECORD' and phase in ('PREOPEN', 'SESSION')",
     "reserved.get('state') == 'RESERVED_RECORD' and phase in ('BEFORE_OPEN', 'PREOPEN', 'SESSION')"),
)

# Invariants are checked on SOURCE, not by trusting a new, manually written
# approval marker. The status/presentation text cannot grant broker permission.
WORKER_GUARDS = (
    "Need $IApproveOrdersForToday 'SAME_DAY_EXPLICIT_APPROVAL_REQUIRED'",
    "$req.sameDayExplicitOrderApproval -eq $true",
    "$req.sessionDate -ceq $day",
    "IsLaunchWindow $launchClock",
    "09:02:00",
    "PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED",
    "[IO.FileMode]::CreateNew",
    "HANDOFF_CHANGED_SINCE_APPROVAL",
    "NATIVE_CODE_CHANGED_SINCE_APPROVAL",
    "STANDBY_CODE_CHANGED",
    "'-Mode','Trade','-IApproveOrdersForToday'",
    "PREOPEN_NEVER_RETRIES_TRADE=True",
)
UI_GUARDS = (
    "if(CanQueuePreopen $s){",
    "if($approval -ne [System.Windows.Forms.DialogResult]::Yes){return}",
    "-Mode Arm -IApproveOrdersForToday",
    "$trade.Enabled=(($s.canRequestTrade -eq $true) -or $preopen) -and (-not $reserved)",
    "# ARK_NO11_ONECLICK_PREOPEN_STANDBY_0830_V1",
)
DISPLAY_GUARDS = (
    "r.get('sameDayExplicitOrderApproval') is not True",
    "issued.date().isoformat() != day",
    "r.get('expiresAtJst') != day + 'T09:02:00+09:00'",
    "'orderTransmission': False",
)


def need(ok, reason):
    if not ok:
        raise ValueError("NO11_ANYTIME_STANDBY_" + reason)


def patch(raw: bytes, edits, guards):
    need(isinstance(raw, bytes) and len(raw) < 3_000_000, "INPUT_SIZE")
    bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
    source = raw.decode("utf-8-sig")
    canonical = source.replace("\r\n", "\n")
    need("\r" not in canonical and all(canonical.count(g) >= 1 for g in guards),
         "SOURCE_GUARD_CHANGED")
    for before, after in edits:
        need(canonical.count(before) == 1 and canonical.count(after) == 0,
             "SOURCE_NOT_EXACT_RELEASE")
    after = replace_regions(source, edits)
    reversed_edits = tuple((new, old) for old, new in edits)
    need(replace_regions(after, reversed_edits) == source, "NONREVERSIBLE")
    canonical_after = after.replace("\r\n", "\n")
    need(all(canonical_after.count(g) >= 1 for g in guards), "GUARD_MODIFIED")
    return bom + after.encode("utf-8")


def worker(raw):
    return patch(raw, WORKER_EDITS, WORKER_GUARDS)


def ui(raw):
    """This patch must run before Display V2 derivation or on a verified V2 UI.

    The optional old text label is absent from V2-derived launcher variants;
    the control-flow guard is mandatory in both forms.
    """
    s = raw.decode("utf-8-sig").replace("\r\n", "\n")
    edits = [UI_EDITS[0], UI_EDITS[1]]
    # The V2 installation replaces the original status text, but leaves the
    # approval message and queue guard unchanged.
    if UI_EDITS[2][0] in s:
        edits.append(UI_EDITS[2])
    edits.append(UI_EDITS[3])
    before_permissions = [line for line in s.splitlines() if
                          "$trade.Enabled=" in line or "$nightly.Enabled=" in line
                          or "$review.Enabled=" in line]
    result = patch(raw, tuple(edits), UI_GUARDS)
    new = result.decode("utf-8-sig").replace("\r\n", "\n")
    need(before_permissions == [line for line in new.splitlines() if
         "$trade.Enabled=" in line or "$nightly.Enabled=" in line
         or "$review.Enabled=" in line], "PERMISSION_LINE_CHANGED")
    for callback in ("$trade.Add_Click({", "$nightly.Add_Click({",
                     "$review.Add_Click({", "$refresh.Add_Click({RefreshUi})"):
        need(s.count(callback) == new.count(callback) == 1, "CALLBACK_CHANGED")
    return result


def display(raw):
    return patch(raw, DISPLAY_EDITS, DISPLAY_GUARDS)


TARGETS = {
    MORNING + "Start-No11PreopenStandby.ps1": worker,
    MORNING + "Start-No11OneClick.ps1": ui,
    MORNING + "no11_oneclick_display_v2.py": display,
}


def stage(root):
    root = Path(root).resolve()
    need((root / ".git").exists(), "STAGING_CHECKOUT_REQUIRED")
    # Validate ALL targets prior to writing ANY source in ephemeral CI.
    changes = [(root / name, change((root / name).read_bytes()))
               for name, change in TARGETS.items()]
    for path, data in changes:
        path.write_bytes(data)
        print("STAGED_ANYTIME_STANDBY|" + str(path.relative_to(root)) +
              "=" + hashlib.sha256(data).hexdigest())
    print("BROKER_AND_NATIVE_TRADE_SOURCE_CHANGED=False")
    print("INSTALLED_PC_CHANGED=False")
    print("TRADE_STARTED=False")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging-checkout", required=True, type=Path)
    args = parser.parse_args()
    stage(args.staging_checkout)
