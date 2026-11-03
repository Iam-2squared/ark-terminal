"""Strictly recognize the configured order-ID book during after-close RSS collection.

No workbook is opened, closed, saved or written by these transforms; the
existing collectors still touch only their own unsaved temporary workbook.
The explicitly configured three-book layout is the ONLY extra layout accepted.
"""
from __future__ import annotations

SCRIPTS={
 'windows/Run-No11RssDailyTrendCensusReadOnly.ps1':
   "  if($excel.Workbooks.Count -ne 2){throw 'NO11_DAILY_ONLY_TWO_ORIGINAL_WORKBOOKS_REQUIRED'}",
 'windows/Run-No11WeeklyCandidateRefreshReadOnly.ps1':
   "  if($excel.Workbooks.Count -ne 2){throw 'NO11_DAILY_ONLY_TWO_ORIGINAL_WORKBOOKS_REQUIRED'}",
 'windows/Capture-No11RssTrainingBatchReadOnly.ps1':
   " if($excel.Workbooks.Count -ne 2){throw 'NO11_BATCH_ONLY_TWO_ORIGINAL_WORKBOOKS_REQUIRED'}",
}
MARKER='# ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1'
CHECK=r"""  # ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1
  # All three saved workbook identities are already known. A fourth, unsaved,
  # foreign or ambiguously named book is never admitted by this gate.
  if($excel.Workbooks.Count -notin @(2,3)){throw 'NO11_NIGHTLY_WORKBOOK_COUNT_UNEXPECTED'}
  if($excel.Workbooks.Count -eq 3){
   $nightlyConfig=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher\settings.json'
   if(-not (Test-Path -LiteralPath $nightlyConfig -PathType Leaf) -or
      (((Get-Item -LiteralPath $nightlyConfig -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)){
    throw 'NO11_NIGHTLY_CONFIGURED_ORDER_BOOK_SETTINGS_REQUIRED'
   }
   $nightlySettings=Get-Content -LiteralPath $nightlyConfig -Raw -Encoding UTF8|ConvertFrom-Json
   if($nightlySettings.schemaId -cne 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' -or
      $nightlySettings.orderTransmission -ne $false -or
      $nightlySettings.automaticOrderAuthorization -ne $false -or
      [string]::IsNullOrWhiteSpace([string]$nightlySettings.orderIdWorkbookPath) -or
      -not [IO.Path]::IsPathRooted([string]$nightlySettings.orderIdWorkbookPath)){
    throw 'NO11_NIGHTLY_ORDER_BOOK_SETTINGS_UNSAFE'
   }
   $nightlyExpected=[IO.Path]::GetFullPath([string]$nightlySettings.orderIdWorkbookPath)
   if(-not (Test-Path -LiteralPath $nightlyExpected -PathType Leaf) -or
      $nightlyExpected -ieq [IO.Path]::GetFullPath([string]$nightlySettings.accountWorkbookPath) -or
      $nightlyExpected -ieq [IO.Path]::GetFullPath([string]$nightlySettings.marketWorkbookPath)){
    throw 'NO11_NIGHTLY_ORDER_BOOK_PATH_INVALID'
   }
   $nightlyMatches=@($excel.Workbooks | Where-Object {
    [string]$_.Path -ne '' -and
    [IO.Path]::GetFullPath([string]$_.FullName).Equals($nightlyExpected,[StringComparison]::OrdinalIgnoreCase)
   })
   if($nightlyMatches.Count -ne 1 -or
      $nightlyMatches[0].Worksheets.Count -ne 1 -or
      [string]$nightlyMatches[0].Worksheets.Item(1).Name -cne 'ARK_ORDER_IDS_READONLY' -or
      [bool]$nightlyMatches[0].Date1904){
    throw 'NO11_NIGHTLY_ORDER_BOOK_IDENTITY_CHANGED'
   }
  }"""

def need(value,code):
    if not value:
        raise ValueError('NO11_NIGHTLY_BOOK_'+code)

def transform_collector(name,raw):
    need(name in SCRIPTS,'UNKNOWN_COLLECTOR')
    bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    s=raw[len(bom):].decode('utf-8')
    line='\r\n' if '\r\n' in s else '\n'
    s=s.replace('\r\n','\n')
    if MARKER in s:
        need(s.count(MARKER)==1,'ALREADY_PATCHED')
        return raw
    anchor=SCRIPTS[name].replace('\r\n','\n')
    need(s.count(anchor)==1,'SOURCE_ANCHOR_CHANGED')
    s=s.replace(anchor,CHECK,1)
    return bom+s.replace('\n',line).encode('utf-8')

def transform_launcher(raw):
    bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    s=raw[len(bom):].decode('utf-8')
    line='\r\n' if '\r\n' in s else '\n'
    s=s.replace('\r\n','\n')
    if MARKER in s:
        need(s.count(MARKER)==1,'LAUNCHER_ALREADY_PATCHED')
        return raw
    begin="   $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')"
    count="  Need ($excel.Workbooks.Count -eq $files.Count) 'EXCEL_BOOK_COUNT'"
    sheet="  if($live){\n   $ids=$excel.Workbooks.Item"
    need(s.count(begin)==1 and s.count(count)==1 and s.count(sheet)==1,
         'LAUNCHER_CHECK_EXCEL_ANCHOR')
    addition="""  # ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1
  # Only the configured third workbook may remain open after the trade session.
  if(-not $live -and $excel.Workbooks.Count -eq 3){
   $files+=@(LocalFile $cfg.orderIdWorkbookPath 'NIGHTLY_ORDER_ID_XLSX')
  }
"""
    s=s.replace(count,addition+count,1)
    s=s.replace(sheet,"  if($live -or $files.Count -eq 3){\n   $ids=$excel.Workbooks.Item",1)
    return bom+s.replace('\n',line).encode('utf-8')
