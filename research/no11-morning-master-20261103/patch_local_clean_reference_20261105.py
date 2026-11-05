#!/usr/bin/env python3
"""One-time local-only compatibility patch for actual Nov 5 ARK clean RSS collector.

Requires the EXACT user-observed git blob b06fbb4194d468313ad450033cb6a7717ea1f5fd
after newline normalization. No fallback to unknown source. Preserves the
existing No11CleanCompatibility dot-source, configured broker workbook and
the two Clean data-conversion calls, unchanged byte-for-byte in the source.
Only repairs the EXCEL7 attachment block and adds read-only stage diagnostics.
Outputs a separate candidate; never changes input, Excel, broker or orders.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import re
import sys

ORIGINAL = "b06fbb4194d468313ad450033cb6a7717ea1f5fd"
BEGIN = " # Bind the single visible original Excel window."
END = " $excel=$windowObject.Application"
KNOWN_CLEAN = (
    ". (Join-Path $PSScriptRoot 'No11CleanCompatibility.ps1')",
    "# ARK_NO11_REFERENCE_OPTIONAL_CONFIGURED_BROKER_V1",
    "Read-No11CleanReferenceRows $sheet $symbols.Count",
    "ConvertTo-No11CleanJson $obj",
    "CONFIGURED_BROKER_BOOK_IDENTITY",
)
EXCEL_REPLACEMENT = """ # ARK_NO11_LOCAL_CLEAN_REFERENCE_EXCEL_ROT_PID_FIX_20261105
 # Read-only reference and original workbook identity must remain inside one
 # already-running physical Excel process. Never spawn another Excel.
 $script:referenceStage='EXCEL_PROCESS_CHECK'
 $processes=@(Get-Process EXCEL -ErrorAction SilentlyContinue)
 Need ($processes.Count -eq 1) 'EXCEL_PROCESS_NOT_UNIQUE'
 $visible=@($processes|Where-Object{$_.MainWindowHandle -ne [IntPtr]::Zero})
 Need ($visible.Count -eq 1 -and $visible[0].MainWindowTitle -like 'Ark_No11_*') 'EXCEL_WINDOW_IDENTITY'
 Write-Host 'NO11_REFERENCE_STAGE=EXCEL_WINDOW_OK'
 $script:referenceStage='EXCEL_ROT_ATTACH'
 $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
 Need ($null -ne $excel) 'EXCEL_ROT_UNAVAILABLE'
 if(-not ('No11VerifiedExcelPid' -as [type])){
  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class No11VerifiedExcelPid {
 [DllImport("user32.dll")]
 public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint processId);
}
'@ -ErrorAction Stop
 }
 [uint32]$attachedProcessId=0
 $hwnd=[IntPtr]([long]$excel.Hwnd)
 [void][No11VerifiedExcelPid]::GetWindowThreadProcessId($hwnd,[ref]$attachedProcessId)
 Need ($attachedProcessId -eq [uint32]$processes[0].Id) 'EXCEL_ROT_PID_MISMATCH'
 Write-Host 'NO11_REFERENCE_STAGE=EXCEL_ROT_PID_OK'
 $script:referenceStage='EXCEL_CONFIGURED_BROKER_BOOK_CHECK'
 # ARK_NO11_LOCAL_CLEAN_REFERENCE_EXCEL_ROT_PID_FIX_END"""

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def patch(raw: bytes) -> bytes:
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    endline = "\r\n" if text.count("\r\n") > 4 else "\n"
    normalized = text.replace("\r\n", "\n")
    if "\r" in normalized:
        raise ValueError("NO11_CLEAN_PATCH_INVALID_LINE_ENDING")
    if git_blob((b"\xef\xbb\xbf" if bom else b"") + normalized.encode("utf-8")) != ORIGINAL:
        raise ValueError("NO11_CLEAN_PATCH_UNRECOGNIZED_LOCAL_SOURCE")
    for token in KNOWN_CLEAN:
        if normalized.count(token) != 1:
            raise ValueError("NO11_CLEAN_PATCH_CLEAN_COMPATIBILITY_NOT_UNIQUE")
    if normalized.count(BEGIN) != 1 or normalized.count(END) != 1:
        raise ValueError("NO11_CLEAN_PATCH_EXCEL_ATTACH_ANCHOR")
    start = normalized.index(BEGIN)
    finish = normalized.index(END, start) + len(END)
    before = normalized[start:finish]
    if "AccessibleObjectFromWindow" not in before or "EXCEL7_NOT_UNIQUE" not in before:
        raise ValueError("NO11_CLEAN_PATCH_EXPECTED_OLD_EXCEL7_MISSING")
    updated = normalized[:start] + EXCEL_REPLACEMENT + normalized[finish:]
    diagnostics = (
        ("$excel=$null;$book=$null;$sheet=$null;$failed=$false",
         "$excel=$null;$book=$null;$sheet=$null;$failed=$false;$script:referenceStage='SOURCE_VALIDATION'"),
        (" Write-Host 'NO11_REFERENCE_STAGE=ORIGINAL_WORKBOOK_FORMULA_SCAN_START'",
         " $script:referenceStage='FORMULA_SCAN'\n Write-Host 'NO11_REFERENCE_STAGE=ORIGINAL_WORKBOOK_FORMULA_SCAN_START'"),
        (" Write-Host 'NO11_REFERENCE_STAGE=CREATE_UNSAVED_TEMP_WORKBOOK'",
         " $script:referenceStage='TEMP_REFERENCE_BOOK'\n Write-Host 'NO11_REFERENCE_STAGE=CREATE_UNSAVED_TEMP_WORKBOOK'"),
        (" $start=Stamp;$values=Read-No11CleanReferenceRows $sheet $symbols.Count;$end=Stamp",
         " $script:referenceStage='CLEAN_READ_REFERENCE_ROWS'\n $start=Stamp;$values=Read-No11CleanReferenceRows $sheet $symbols.Count;$end=Stamp"),
        (" $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-No11CleanJson $obj)+[char]10)",
         " $script:referenceStage='CLEAN_SERIALIZE_RECEIPT'\n $bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-No11CleanJson $obj)+[char]10)"),
        ("  Write-Host ('NO11_SESSION_REFERENCE=BLOCKED|'+$msg)",
         "  Write-Host ('NO11_REFERENCE_DIAGNOSTIC_STAGE='+$script:referenceStage)\n"
         "  Write-Host ('NO11_SESSION_REFERENCE=BLOCKED|'+$msg)"),
    )
    for old, new in diagnostics:
        if updated.count(old) != 1:
            raise ValueError("NO11_CLEAN_PATCH_DIAGNOSTIC_ANCHOR")
        updated = updated.replace(old, new)
    # Proof: invert all changes and verify EVERY other source character
    # is identical, including two Clean data functions and broker allowlist.
    inverted = updated
    for old, new in reversed(diagnostics):
        if inverted.count(new) != 1:
            raise ValueError("NO11_CLEAN_PATCH_ROUNDTRIP_DIAG")
        inverted = inverted.replace(new, old)
    if inverted.count(EXCEL_REPLACEMENT) != 1:
        raise ValueError("NO11_CLEAN_PATCH_ROUNDTRIP_EXCEL")
    inverted = inverted.replace(EXCEL_REPLACEMENT, before)
    if inverted != normalized:
        raise ValueError("NO11_CLEAN_PATCH_OTHER_CODE_CHANGED")
    if updated.count("No11CleanCompatibility.ps1") != 1 or (
        updated.count("CONFIGURED_BROKER_BOOK_IDENTITY") != 1
    ):
        raise ValueError("NO11_CLEAN_PATCH_SAFETY_GATES_CHANGED")
    result = updated.replace("\n", endline) if endline == "\r\n" else updated
    return (b"\xef\xbb\xbf" if bom else b"") + result.encode("utf-8")

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--original", required=True, type=Path)
    p.add_argument("--candidate", required=True, type=Path)
    a = p.parse_args(argv)
    if a.candidate.exists():
        raise ValueError("NO11_CLEAN_PATCH_OUTPUT_EXISTS")
    original = a.original.read_bytes()
    rewritten = patch(original)
    a.candidate.write_bytes(rewritten)
    print("NO11_CLEAN_REFERENCE_PATCH=CREATED_ONLY")
    print("ORIGINAL_GIT_BLOB=" + ORIGINAL)
    print("PATCHED_GIT_BLOB=" + git_blob(rewritten))
    print("CLEAN_COMPATIBILITY_PRESERVED=True")
    print("CONFIGURED_BROKER_VALIDATION_PRESERVED=True")
    print("ORDER_TRANSMISSION=False")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, UnicodeError) as e:
        value = str(e)
        if not re.fullmatch(r"NO11_CLEAN_PATCH_[A-Z0-9_]+", value):
            value = "NO11_CLEAN_PATCH_UNKNOWN_SOURCE_OR_RUNTIME"
        print("NO11_CLEAN_REFERENCE_PATCH=BLOCKED|" + value, file=sys.stderr)
        sys.exit(2)
