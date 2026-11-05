#!/usr/bin/env python3
"""Offline source-exact recreation of the user's Nov 5 local Clean collector.

Test the NORMALIZED exact b06f Git identity from the user's 58-line diff,
then the deterministic, reversible PID-safe patch; no Excel or orders.
"""
import importlib.util
import sys
import hashlib
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures/nov05_reference_original.ps1.txt"
PATCHER = HERE / "patch_local_clean_reference_20261105.py"
spec = importlib.util.spec_from_file_location("clean_fix", PATCHER)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def recreate_clean() -> bytes:
    raw = FIXTURE.read_bytes()
    before = raw.decode("utf-8-sig").replace("\r\n", "\n")
    assert raw.startswith(b"\xef\xbb\xbf")

    def change(old: str, new: str):
        nonlocal before
        assert before.count(old) == 1, old
        before = before.replace(old, new, 1)

    change("$ErrorActionPreference='Stop';Set-StrictMode -Version Latest",
           "$ErrorActionPreference='Stop';Set-StrictMode -Version Latest\n"
           ". (Join-Path $PSScriptRoot 'No11CleanCompatibility.ps1')")
    original = " Need ($excel.Workbooks.Count -eq 2) 'TWO_ORIGINAL_BOOKS_REQUIRED'"
    new = """ # ARK_NO11_REFERENCE_OPTIONAL_CONFIGURED_BROKER_V1
 Need ($excel.Workbooks.Count -in @(2,3)) 'TWO_ORIGINAL_BOOKS_OR_CONFIGURED_BROKER_REQUIRED'
 if($excel.Workbooks.Count -eq 3){
  $configuredFile=Join-Path $env:LOCALAPPDATA 'ArkTerminal\\No12\\unified-launcher\\settings.json'
  $configured=Get-Content -LiteralPath $configuredFile -Raw -Encoding UTF8|ConvertFrom-Json
  Need ($configured.schemaId -ceq 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -and
        $configured.automaticOrderAuthorization -eq $false -and
        $configured.orderTransmission -eq $false) 'CONFIGURED_BROKER_SETTINGS'
  $orderPath=[IO.Path]::GetFullPath([string]$configured.orderIdWorkbookPath)
  $optionalBook=$null
  try{
   $optionalBook=$excel.Workbooks.Item([IO.Path]::GetFileName($orderPath))
   Need ([IO.Path]::GetFullPath([string]$optionalBook.FullName).Equals($orderPath,[StringComparison]::OrdinalIgnoreCase) -and
         $optionalBook.Worksheets.Count -eq 1 -and
         $optionalBook.Worksheets.Item(1).Name -ceq 'ARK_ORDER_IDS_READONLY') 'CONFIGURED_BROKER_BOOK_IDENTITY'
  }finally{
   if($null -ne $optionalBook -and [Runtime.InteropServices.Marshal]::IsComObject($optionalBook)){
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($optionalBook)
   }
  }
 }
 # ARK_NO11_REFERENCE_OPTIONAL_CONFIGURED_BROKER_END"""
    change(original, new)
    change("$start=Stamp;$values=$sheet.Range($range).Value2;$end=Stamp",
           "$start=Stamp;$values=Read-No11CleanReferenceRows $sheet $symbols.Count;$end=Stamp")
    change("$bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-Json -InputObject $obj -Depth 10 -Compress)+[char]10)",
           "$bytes=[Text.UTF8Encoding]::new($false).GetBytes((ConvertTo-No11CleanJson $obj)+[char]10)")
    return b"\xef\xbb\xbf" + before.encode("utf-8")

class CleanReference(unittest.TestCase):
    def test_exact_user_source_and_preservation(self):
        old = recreate_clean()
        canonical = b"\xef\xbb\xbf" + old.decode("utf-8-sig").replace("\r\n","\n").encode()
        self.assertEqual(mod.git_blob(canonical), mod.ORIGINAL)
        patched = mod.patch(old)
        self.assertNotEqual(patched, old)
        out = patched.decode("utf-8-sig")
        for item in mod.KNOWN_CLEAN:
            self.assertEqual(out.count(item), 1, item)
        self.assertIn("GetWindowThreadProcessId", out)
        self.assertIn("EXCEL_ROT_PID_MISMATCH", out)
        self.assertIn("NO11_REFERENCE_DIAGNOSTIC_STAGE=", out)
        self.assertIn("CLEAN_READ_REFERENCE_ROWS", out)
        self.assertIn("CONFIGURED_BROKER_BOOK_IDENTITY", out)
        self.assertNotIn("EXCEL7_NOT_UNIQUE", out)
        self.assertEqual(out.count("RssStockOrder"), 0)
        self.assertEqual(out.count("RssCancelOrder"), 0)

    def test_line_ending_normalization_but_no_other_source_changes(self):
        old = recreate_clean()
        modified = old.replace(b"\n",b"\r\n")
        patched = mod.patch(modified)
        self.assertIn(b"\r\n",patched)
        self.assertNotIn(b"\r\r\n",patched)
        with self.assertRaisesRegex(ValueError,"UNRECOGNIZED_LOCAL_SOURCE"):
            mod.patch(old.replace(b"Read-No11CleanReferenceRows",b"Read-No11CleanReferenceRowsTampered"))
        with self.assertRaisesRegex(ValueError,"UNRECOGNIZED_LOCAL_SOURCE"):
            mod.patch(old.replace(b"CONFIGURED_BROKER_BOOK_IDENTITY",b"CONFIGURED_BROKER_BOOK_INVALID"))
        with self.assertRaisesRegex(ValueError,"UNRECOGNIZED_LOCAL_SOURCE"):
            mod.patch(old.replace(b"No11CleanCompatibility.ps1",b"Unknown.ps1"))

    def test_cli_candidate_only_never_overwrites_original(self):
        import subprocess
        old = recreate_clean()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            src, dest = p/"original.ps1", p/"candidate.ps1"
            src.write_bytes(old)
            result = subprocess.run(
                ["python", "-B", str(PATCHER), "--original", str(src),
                 "--candidate", str(dest)], capture_output=True, text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(src.read_bytes(),old)
            self.assertEqual(dest.read_bytes(),mod.patch(old))
            self.assertIn("CLEAN_COMPATIBILITY_PRESERVED=True",result.stdout)
            self.assertIn("ORDER_TRANSMISSION=False",result.stdout)
            again = subprocess.run(["python","-B",str(PATCHER),"--original",str(src),
                                     "--candidate",str(dest)],capture_output=True,text=True)
            self.assertEqual(again.returncode,2)

if __name__=="__main__":
    if len(sys.argv)==3 and sys.argv[1]=="--emit-fixture":
        Path(sys.argv[2]).write_bytes(recreate_clean())
        print("NO11_CLEAN_FIXTURE=CREATED_ONLY")
    else:
        unittest.main()
