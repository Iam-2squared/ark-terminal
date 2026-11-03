#!/usr/bin/env python3
"""Transactional local installation of the automatic Trade input hook.

Allow only the existing explicitly configured broker workbook as a third book
in the read-only reference collector. Do not open/close/save any workbook.
"""
import argparse
from pathlib import Path
import re
import sys
import uuid

import launcher_automatic_bridge as bridge

MARKER = '# ARK_NO11_REFERENCE_OPTIONAL_CONFIGURED_BROKER_V1'
ANCHOR = " Need ($excel.Workbooks.Count -eq 2) 'TWO_ORIGINAL_BOOKS_REQUIRED'"
REPLACEMENT = r''' # ARK_NO11_REFERENCE_OPTIONAL_CONFIGURED_BROKER_V1
 Need ($excel.Workbooks.Count -in @(2,3)) 'TWO_ORIGINAL_BOOKS_OR_CONFIGURED_BROKER_REQUIRED'
 if($excel.Workbooks.Count -eq 3){
  $configuredFile=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher\settings.json'
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
 # ARK_NO11_REFERENCE_OPTIONAL_CONFIGURED_BROKER_END'''


def patch_reference(raw):
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text = raw[len(bom):].decode('utf-8')
    newline = '\r\n' if '\r\n' in text else '\n'
    text = text.replace('\r\n', '\n')
    bridge.need('\r' not in text, 'REFERENCE_LINE_ENDINGS')
    if MARKER in text:
        bridge.need(text.count(MARKER) == 1 and REPLACEMENT in text,
                    'REFERENCE_PARTIAL_PATCH')
        return raw
    bridge.need(text.count(ANCHOR) == 1, 'REFERENCE_BOOK_CHECK_CHANGED')
    return bom + text.replace(ANCHOR, REPLACEMENT, 1).replace('\n', newline).encode('utf-8')


def install(runner, handoff_file):
    bridge.need(sys.platform == 'win32', 'WINDOWS_INSTALL_ONLY')
    bridge.assert_stopped()
    h, _ = bridge.load(handoff_file)
    engine = bridge.safe(h['spec']['engineRoot'], True)
    reference = bridge.safe(engine / 'windows/Capture-No11SessionReferenceReadOnly.ps1')
    before = reference.read_bytes()
    after = patch_reference(before)
    store = bridge.safe(Path(h['spec']['settingsFile']).parent, True)
    work = store / ('reference-auto-install-' + uuid.uuid4().hex)
    work.mkdir()
    candidate = work / 'candidate.ps1'
    candidate.write_bytes(after)
    bridge.parse_ps(candidate)
    backup = work / 'Capture-No11SessionReferenceReadOnly.ps1.before'
    backup.write_bytes(before)
    bridge.need(backup.read_bytes() == before, 'REFERENCE_BACKUP_FAILED')
    changed = False
    try:
        if after != before:
            bridge.replace_bytes(reference, after, before)
            changed = True
        result = bridge.invoke(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                                'Bypass', '-File', str(reference), '-OfflineSelfTest'], 'REFERENCE_SELFTEST')
        bridge.need('NO11_REFERENCE_OFFLINE_SELFTEST=PASS' in result, 'REFERENCE_SELFTEST_MARKER')
        bridge.install(runner, handoff_file)
    except BaseException:
        if changed and reference.read_bytes() == after:
            bridge.replace_bytes(reference, before, after)
            print('REFERENCE_INSTALL_ROLLBACK=PASS')
        elif changed:
            print('REFERENCE_INSTALL_ROLLBACK=CONCURRENT_EDIT_NOT_OVERWRITTEN')
        raise
    print('CONFIGURED_BROKER_THIRD_BOOK=SUPPORTED_WITHOUT_OPEN_CLOSE_SAVE')
    print('REFERENCE_BACKUP=' + str(backup))
    print('REFERENCE_OFFLINE_SELFTEST=PASS')
    print('ORDER_SENT_BY_INSTALLER=False')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runner', required=True, type=Path)
    p.add_argument('--handoff', required=True, type=Path)
    a = p.parse_args()
    try:
        install(a.runner, a.handoff)
    except Exception as error:
        msg = str(error)
        if not re.fullmatch(r'NO11_AUTOSTART_[A-Z0-9_]+', msg):
            msg = 'NO11_AUTOSTART_INSTALL_LOCAL_RUNTIME_ERROR'
        print('AUTOMATIC_LAUNCHER_INSTALL=BLOCKED|' + msg)
        print('ORDER_SENT_BY_INSTALLER=False')
        raise SystemExit(2)
