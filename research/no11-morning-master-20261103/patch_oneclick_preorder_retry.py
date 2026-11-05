#!/usr/bin/env python3
"""Surgically add a VERIFIED pre-order-only retry to the existing OneClick START.

No colors/layout/buttons/styles moved, no original action removed, no trade,
no Excel, no workbook access. Refuses unknown UI. Output candidate only.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

MARKER = "# ARK_NO11_ONECLICK_VERIFIED_PREORDER_RETRY_20261105"

FUNCTION = """
# ARK_NO11_ONECLICK_VERIFIED_PREORDER_RETRY_20261105
# PURE status: no order permission until user clicks existing START button.
function CanRetryPreorder($s){
 $now=[DateTimeOffset]::UtcNow.ToOffset([timespan]::FromHours(9))
 if($now.ToString('yyyy-MM-dd') -cne '2026-11-05' -or
    $now.ToString('HH:mm:ss') -lt '12:35:00' -or
    $now.ToString('HH:mm:ss') -ge '15:20:00' -or
    $s.sessionDate -cne '2026-11-05' -or
    $s.mode -cne 'OPERATOR_CHECK' -or
    $s.reason -cne 'PRELIMINARY_INPUTS_READY' -or
    $s.canRequestTrade -ne $true){return $false}
 $tool=Join-Path $PSScriptRoot 'Retry-No11OneClickPreorder.ps1'
 if(-not (Test-Path -LiteralPath $tool -PathType Leaf)){return $false}
 $result=@(& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $tool -Mode Status)
 return ($LASTEXITCODE -eq 0 -and
         $result -contains 'NO11_ONECLICK_RETRY_STATUS=READY')
}
"""
CLICK = """ if(CanRetryPreorder $s){
  $approved=[System.Windows.Forms.MessageBox]::Show(
   'Retry REAL broker cash LONG orders for TODAY only? The 09:00 and 12:30 native requests must both be proven to have FAILED BEFORE orders. Only the 39 source-verified symbols may be considered. All original broker, RSS, MAX3 and one-shot checks remain mandatory. This retry can be requested ONCE and may be blocked.',
   'ARK - VERIFIED PRE-ORDER RETRY TODAY',
   [System.Windows.Forms.MessageBoxButtons]::YesNo,
   [System.Windows.Forms.MessageBoxIcon]::Warning)
  if($approved -ne [System.Windows.Forms.DialogResult]::Yes){return}
  try{
   $tool=Join-Path $PSScriptRoot 'Retry-No11OneClickPreorder.ps1'
   $trade.Enabled=$false
   $results=@(& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $tool -Mode Trade -IApproveOrdersForToday)
   if($LASTEXITCODE -ne 0 -or $results -notcontains 'NO11_ONECLICK_RETRY=REQUESTED_ONCE'){
    $failure=@($results|Where-Object{$_ -like 'NO11_ONECLICK_RETRY=BLOCKED|*'})
    $status.Text=if($failure.Count){$failure[-1]}else{'PRE-ORDER RETRY BLOCKED - inspect logs'}
   }else{
    $status.Text='VERIFIED PRE-ORDER RETRY REQUESTED ONCE. Original native LIVE gates still pending; check OneClickRetry logs.'
   }
  }catch{
   $status.Text='PRE-ORDER RETRY FAILED before native launch; inspect preserved logs'
  }
  RefreshUi
  return
 }
"""


def patch_text(raw: bytes) -> bytes:
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    nl = "\r\n" if text.count("\r\n") > 4 else "\n"
    # Normalize internally so a CRLF source never becomes CRCRLF.
    text = text.replace("\r\n", "\n")
    if MARKER in text:
        raise ValueError("NO11_RETRY_UI_ALREADY_PATCHED")
    for token in ("# ARK_NO11_ONECLICK_PREOPEN_STANDBY_0830_V1",
                  "function PreopenReserved($s){",
                  "function CanQueuePreopen($s){",
                  "function RefreshUi{",
                  "$trade.Add_Click({",
                  "if(CanQueuePreopen $s){"):
        if text.count(token) != 1:
            raise ValueError("NO11_RETRY_UI_REQUIRED_ANCHOR_MISSING_" + str(len(token)))
    # Ensure styles and button geometry are never edited: four insertions and
    # one original Enabled expression change only. Reconstruct original below.
    replacements: list[tuple[str, str]] = []

    def once(a: str, b: str):
        nonlocal text
        if text.count(a) != 1:
            raise ValueError("NO11_RETRY_UI_ANCHOR_NOT_UNIQUE")
        text = text.replace(a, b, 1)
        replacements.append((a, b))

    once("function RefreshUi{", FUNCTION.strip("\n") + "\nfunction RefreshUi{")
    once("  $reserved=PreopenReserved $s",
         "  $reserved=PreopenReserved $s\n  $retryReady=CanRetryPreorder $s")
    original_line = ("  if($reserved){$trading=if($s.reason -ceq 'ALREADY_STARTED_TODAY')"
                     "{'TRADE REQUESTED - check logs'}else{'09:00 START RESERVED - check logs'}}")
    once(original_line, original_line +
         "\n  if($retryReady){$trading='PRE-ORDER REFERENCE FAILED - VERIFIED RETRY AVAILABLE'}")
    old_enabled = ("  $trade.Enabled=(($s.canRequestTrade -eq $true) -or $preopen)"
                   " -and (-not $reserved)")
    once(old_enabled,
         old_enabled.replace(" -and (-not $reserved)",
                             " -and (-not $reserved) -or $retryReady") +
         "\n  $trade.Text=if($retryReady){'RETRY START TRADING / NORMAL MAX3'}"
         "else{'START TRADING   /   NORMAL MAX3'}")
    once("$trade.Add_Click({\n $s=GetStatus",
         "$trade.Add_Click({\n $s=GetStatus\n" + CLICK.rstrip("\n"))
    # Exact round-trip demonstrates no other token, including white theme,
    # font, button positions, existing click branches, or layout was touched.
    back = text
    for a, b in reversed(replacements):
        if back.count(b) != 1:
            raise ValueError("NO11_RETRY_UI_ROUNDTRIP_ANCHOR_CHANGED")
        back = back.replace(b, a)
    original = raw.decode("utf-8-sig").replace("\r\n", "\n")
    if back != original:
        raise ValueError("NO11_RETRY_UI_LAYOUT_OR_CODE_CHANGED")
    text = text.replace("\n", nl) if nl == "\r\n" else text
    result = text.encode("utf-8")
    return (b"\xef\xbb\xbf" + result) if bom else result


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    args = p.parse_args(argv)
    before = args.original.read_bytes()
    after = patch_text(before)
    if before == after or args.candidate.exists():
        raise ValueError("NO11_RETRY_UI_CANDIDATE_CONFLICT")
    args.candidate.write_bytes(after)
    print("NO11_ONECLICK_RETRY_CANDIDATE=CREATED_ONLY")
    print("UI_STYLING_CHANGED=False")
    print("UI_BUTTON_LAYOUT_CHANGED=False")
    print("PREVIOUS_UI_ACTIONS_REMOVED=False")
    print("ORDER_TRANSMISSION=False")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, UnicodeError) as e:
        code = str(e)
        if not re.fullmatch(r"NO11_RETRY_UI_[A-Z0-9_]+", code):
            code = "NO11_RETRY_UI_SOURCE_OR_INPUT_UNVERIFIED"
        print("NO11_RETRY_UI=BLOCKED|" + code, file=sys.stderr)
        sys.exit(2)
