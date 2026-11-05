#!/usr/bin/env python3
"""Strict, source-pinned update of the user's installed Clean reference collector.

Never loosen a PID identity check. Require two matching native Win32 PID
observations (same thread) plus a second single-process check. Retry probes
three times, bounded ~400 ms. Emit PIDs so future failures are diagnosable.
Do not open Excel or transmit any orders. Writes candidate ONLY.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import re
import sys

PIN = "d52794cc647c8552a9953dc0c3352e08076cf716"
OLD = """ [uint32]$attachedProcessId=0
 $hwnd=[IntPtr]([long]$excel.Hwnd)
 [void][No11VerifiedExcelPid]::GetWindowThreadProcessId($hwnd,[ref]$attachedProcessId)
 Need ($attachedProcessId -eq [uint32]$processes[0].Id) 'EXCEL_ROT_PID_MISMATCH'
 Write-Host 'NO11_REFERENCE_STAGE=EXCEL_ROT_PID_OK'"""
NEW = """ # NO11_STRICT_ROT_PID_DOUBLE_SAMPLE_20261105
 # No PIN bypass: two consecutive Win32 readings must match the original
 # single Excel process and its COM Hwnd, with stable thread identity.
 $expectedExcelProcessId=[uint32]$processes[0].Id
 $excelWindowHandle=[IntPtr]([long]$excel.Hwnd)
 Need ($excelWindowHandle -ne [IntPtr]::Zero) 'EXCEL_ROT_HWND_INVALID'
 $pidMatchStable=$false
 for($identityAttempt=1;$identityAttempt -le 3;$identityAttempt++){
  [uint32]$firstObservedPid=0
  $threadId=[No11VerifiedExcelPid]::GetWindowThreadProcessId(
   $excelWindowHandle,[ref]$firstObservedPid)
  [uint32]$secondObservedPid=0
  $threadIdAgain=[No11VerifiedExcelPid]::GetWindowThreadProcessId(
   $excelWindowHandle,[ref]$secondObservedPid)
  $after=@(Get-Process EXCEL -ErrorAction SilentlyContinue)
  Write-Host ('NO11_REFERENCE_ROT_PID_PROBE='+
   'EXPECTED='+$expectedExcelProcessId+
   '|COM1='+$firstObservedPid+'|COM2='+$secondObservedPid+
   '|THREAD1='+$threadId+'|THREAD2='+$threadIdAgain+
   '|EXCEL_COUNT='+$after.Count+'|TRY='+$identityAttempt)
  if($threadId -gt 0 -and $threadId -eq $threadIdAgain -and
     $firstObservedPid -eq $expectedExcelProcessId -and
     $secondObservedPid -eq $expectedExcelProcessId -and
     $after.Count -eq 1 -and
     [uint32]$after[0].Id -eq $expectedExcelProcessId){
   $pidMatchStable=$true
   break
  }
  if($identityAttempt -lt 3){Start-Sleep -Milliseconds 200}
 }
 Need $pidMatchStable 'EXCEL_ROT_PID_MISMATCH'
 Write-Host 'NO11_REFERENCE_STAGE=EXCEL_ROT_PID_OK'"""

def digest(raw: bytes):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def patch(raw: bytes) -> bytes:
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    crlf = text.count("\r\n") > 4
    clean = text.replace("\r\n", "\n")
    if "\r" in clean or digest((b"\xef\xbb\xbf" if bom else b"") + clean.encode("utf-8")) != PIN:
        raise ValueError("NO11_PID_PATCH_INSTALLED_CLEAN_COLLECTOR_CHANGED")
    for token in (
        "No11CleanCompatibility.ps1",
        "Read-No11CleanReferenceRows $sheet $symbols.Count",
        "ConvertTo-No11CleanJson $obj",
        "CONFIGURED_BROKER_BOOK_IDENTITY",
        "NO11_REFERENCE_DIAGNOSTIC_STAGE=",
        "NO11_REFERENCE_STAGE=EXCEL_WINDOW_OK"
    ):
        if clean.count(token) != 1:
            raise ValueError("NO11_PID_PATCH_CLEAN_OR_BROKER_GATES_MISSING")
    if clean.count(OLD) != 1:
        raise ValueError("NO11_PID_PATCH_OLD_PID_BLOCK_NOT_FOUND")
    changed = clean.replace(OLD, NEW)
    if changed.replace(NEW, OLD) != clean:
        raise ValueError("NO11_PID_PATCH_OUTSIDE_PID_BLOCK_MODIFIED")
    out = changed.replace("\n", "\r\n") if crlf else changed
    return (b"\xef\xbb\xbf" if bom else b"") + out.encode("utf-8")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--original", required=True, type=Path)
    p.add_argument("--candidate", required=True, type=Path)
    args = p.parse_args()
    if args.candidate.exists():
        raise ValueError("NO11_PID_PATCH_CANDIDATE_ALREADY_EXISTS")
    original = args.original.read_bytes()
    candidate = patch(original)
    args.candidate.write_bytes(candidate)
    print("NO11_PID_DIAGNOSTIC_CANDIDATE=CREATED_ONLY")
    print("ORIGINAL_CAPTURE_SOURCE_CHANGED=False")
    print("PID_MATCH_BYPASSED=False")
    print("DOUBLE_PID_SAMPLE_REQUIRED=True")
    print("EXCEL_TOUCHED=False")
    print("ORDER_TRANSMISSION=False")
    print("PATCHED_GIT_BLOB=" + digest(candidate))

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, UnicodeError) as e:
        reason=str(e)
        if not re.fullmatch(r"NO11_PID_PATCH_[A-Z0-9_]+",reason):
            reason="NO11_PID_PATCH_UNVERIFIED_SOURCE"
        print("NO11_PID_DIAGNOSTIC=BLOCKED|"+reason,file=sys.stderr)
        sys.exit(2)
