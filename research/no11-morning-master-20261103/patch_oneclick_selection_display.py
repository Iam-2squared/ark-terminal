#!/usr/bin/env python3
"""Add one display-only selection-status line to the EXISTING WHITE OneClick.

Never replace the user's colors, fonts, buttons, trade click handlers, etc.
The original UI must round-trip byte-for-byte by reversing exactly two
inserts. Refuse to patch unexpected or already-patched UI. Candidate only.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys

MARKER="# ARK_NO11_ONECLICK_WEEKLY_DAILY_SELECTION_READONLY_V1"
SCRIPT=r"""
# ARK_NO11_ONECLICK_WEEKLY_DAILY_SELECTION_READONLY_V1
# Read-only extra label in the existing unused title/status gap.
# Original status text, control geometry, colors, click actions unchanged.
$selectionStatus=New-Object System.Windows.Forms.Label
$selectionStatus.Name='No11WeeklyDailySelectionStatus'
$selectionStatus.AutoSize=$false
$selectionStatus.Size=New-Object System.Drawing.Size(708,21)
$selectionStatus.Location=New-Object System.Drawing.Point(26,57)
$selectionStatus.Font=$notice.Font
$selectionStatus.ForeColor=$status.ForeColor
$selectionStatus.BackColor=$form.BackColor
$selectionStatus.Text='WEEKLY  VERIFYING   |   DAILY  VERIFYING'
$form.Controls.Add($selectionStatus)
function ReadNo11SelectionDisplay {
 $tool=Join-Path $PSScriptRoot 'no11_selection_status.py'
 if(-not (Test-Path -LiteralPath $tool -PathType Leaf)){
  return 'WEEKLY  NOT INSTALLED   |   DAILY  NOT INSTALLED'
 }
 try{
  $lines=@(& $python -B -X utf8 $tool --binding $bindingFile --line)
  if($LASTEXITCODE -ne 0 -or $lines.Count -ne 1){
   return 'WEEKLY  CHECK FAILED   |   DAILY  CHECK FAILED'
  }
  $value=[string]$lines[0]
  if($value.Length -gt 150 -or
     $value -cnotmatch '^NO11_SELECTION_UI=[A-Z0-9 /().|:-]+$'){
   return 'WEEKLY  UNVERIFIED   |   DAILY  UNVERIFIED'
  }
  return $value.Substring('NO11_SELECTION_UI='.Length)
 }catch{
  return 'WEEKLY  UNVERIFIED   |   DAILY  UNVERIFIED'
 }
}
"""


def patch(raw: bytes) -> bytes:
    bom=raw.startswith(b"\xef\xbb\xbf")
    text=raw.decode("utf-8-sig")
    newline="\r\n" if text.count("\r\n")>4 else "\n"
    source=text.replace("\r\n","\n")
    if "\r" in source:
        raise ValueError("NO11_SELECTION_UI_INVALID_LINE_ENDING")
    if MARKER in source:
        raise ValueError("NO11_SELECTION_UI_ALREADY_APPLIED")
    required=(
        "function UiReason([string]$raw){",
        "function RefreshUi{",
        "$form.Controls.Add($status)",
        "$form.Controls.Add($title)",
        "$status.Text=(",
        "$nightly.Add_Click({",
        "$trade.Add_Click({",
        "$refresh.Add_Click({RefreshUi})",
        "$timer.Add_Tick({RefreshUi})",
    )
    for token in required:
        if source.count(token)!=1:
            raise ValueError("NO11_SELECTION_UI_UNEXPECTED_WHITE_LAYOUT")
    replacements=[]
    def once(old,new):
        nonlocal source
        if source.count(old)!=1:
            raise ValueError("NO11_SELECTION_UI_NONUNIQUE_ANCHOR")
        source=source.replace(old,new,1)
        replacements.append((old,new))

    once("function UiReason([string]$raw){",
         SCRIPT.strip("\n")+"\nfunction UiReason([string]$raw){")
    once("function RefreshUi{\n try{",
         "function RefreshUi{\n"
         " $selectionStatus.Text=ReadNo11SelectionDisplay\n"
         " try{")
    # All existing GUI style tokens/control sizes/button locations/handlers
    # are provably retained; only a new, non-overlapping label is added.
    back=source
    for a,b in reversed(replacements):
        if back.count(b)!=1:
            raise ValueError("NO11_SELECTION_UI_ROUNDTRIP_ANCHOR")
        back=back.replace(b,a,1)
    if back!=text.replace("\r\n","\n"):
        raise ValueError("NO11_SELECTION_UI_ORIGINAL_CHANGED")
    encoded=(source.replace("\n",newline) if newline=="\r\n" else source).encode()
    return (b"\xef\xbb\xbf" if bom else b"")+encoded


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    a=p.parse_args()
    if a.candidate.exists():
        raise ValueError("NO11_SELECTION_UI_CANDIDATE_EXISTS")
    old=a.original.read_bytes()
    new=patch(old)
    a.candidate.write_bytes(new)
    print("NO11_SELECTION_WHITE_UI_CANDIDATE=CREATED_ONLY")
    print("EXISTING_WHITE_THEME_CHANGED=False")
    print("EXISTING_BUTTONS_OR_LAYOUT_CHANGED=False")
    print("ORIGINAL_CLICK_HANDLERS_CHANGED=False")
    print("TRADING_APPROVAL_CHANGED=False")
    print("ORDER_TRANSMISSION=False")


if __name__=="__main__":
    try:main()
    except (ValueError, UnicodeError, OSError) as e:
        code=str(e)
        if not re.fullmatch(r"NO11_SELECTION_UI_[A-Z0-9_]+",code):
            code="NO11_SELECTION_UI_UNKNOWN_WHITE_SOURCE"
        print("NO11_SELECTION_UI=BLOCKED|"+code,file=sys.stderr)
        sys.exit(2)
