#!/usr/bin/env python3
"""Fix native DATA-only duplicate workbook-path gate, not broker/trading checks.

The original RSS collectors already verify workbook identities (2 or the
configured 3-book layout), sheet identities, and Excel/RSS state. The native
OneClick Weekly gate additionally demands EXACT account/market path spelling,
and 2026-11-09 twice failed there before a collector was ever started.

This change delegates Weekly's redundant check to the existing collector.
It does not modify CheckExcel(), RunTrade(), StartChild(), trading approval,
the approved WHITE OneClick GUI, or any collector, order, EXIT, or receipt.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

MARKER = 'ARK_NO11_WEEKLY_BOOK_GATE_DELEGATED_TO_RSS_COLLECTOR_V1'
NEEDLE = ' CheckExcel $cfg $false'
NEW = """ # ARK_NO11_WEEKLY_BOOK_GATE_DELEGATED_TO_RSS_COLLECTOR_V1
 # For DATA-ONLY Weekly, do not recheck settings-vs-Excel FullName spelling.
 # The RSS D100/1M collectors independently check exact workbook names,
 # the configured third saved book, RSS state, and the Excel COM instance.
 Write-Host 'NO11_UNIFIED_WEEKLY_WORKBOOK_CHECK=DELEGATED_TO_RSS_COLLECTOR'"""


def require(ok, code):
    if not ok:
        raise ValueError('NO11_WEEKLY_BOOK_FIX_' + code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def no_links(path, is_file=True):
    p = Path(path)
    require(p.is_absolute(), 'PATH_NOT_ABSOLUTE')
    for q in (p, *p.parents):
        if q.exists() or q.is_symlink():
            st = q.lstat()
            require(not q.is_symlink() and not (getattr(st,'st_file_attributes',0)&1024), 'REPARSE_PATH')
    require(p.is_file() if is_file else p.is_dir(), 'PATH_MISSING')
    return p


def read_json(path):
    def unique(pairs):
        d = {}
        for k, v in pairs:
            require(k not in d, 'DUPLICATE_JSON_KEY')
            d[k] = v
        return d
    data = no_links(path).read_bytes()
    require(0 < len(data) <= 2_000_000, 'JSON_SIZE')
    obj = json.loads(data.decode('utf-8-sig'), object_pairs_hook=unique)
    require(isinstance(obj,dict), 'JSON_CONTRACT')
    return obj


def transform(raw):
    bom = raw.startswith(b'\xef\xbb\xbf')
    src = raw.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in src else '\n'
    text = src.replace('\r\n','\n')
    require('\r' not in text, 'LINE_ENDING_UNRECOGNIZED')
    # Idempotence: don't try to reinsert the guard after it was removed.
    if MARKER in text:
        require(text.count(MARKER) == 1
                and text.count('NO11_UNIFIED_WEEKLY_WORKBOOK_CHECK=DELEGATED_TO_RSS_COLLECTOR') == 1,
                'ALREADY_PATCHED_INVALID')
        return raw
    begin, end = text.find('function RunWeekly($cfg){'), text.find('function StopRunningEngine(')
    require(begin >= 0 and end > begin, 'NATIVE_FUNCTIONS_CHANGED')
    before, weekly, after = text[:begin], text[begin:end], text[end:]
    require(weekly.count(NEEDLE) == 1
            and 'ARK_NO11_LATEST_COMPLETED_SESSION_DATA_V1' in weekly
            and "StartChild 'WEEKLY' $weekly" in weekly
            and 'NO11_UNIFIED_DATA_ASOF=' in weekly
            and 'NO11_UNIFIED_DATA_TARGET=' in weekly,
            'NATIVE_WEEKLY_CONTEXT_CHANGED')
    require('function CheckExcel($cfg,[bool]$live)' in before
            and 'CheckExcel $cfg $true' in before
            and "StartChild 'TRADE'" in before,
            'TRADE_GATE_MISSING')
    # Exact single-statement replacement; everything outside Weekly is unchanged.
    fixed = weekly.replace(NEEDLE, NEW, 1)
    result = before + fixed + after
    return (b'\xef\xbb\xbf' if bom else b'') + result.replace('\n', newline).encode('utf-8')


def preflight(store):
    store = no_links(store, False)
    b = read_json(store/'automatic-inputs.json')
    s = read_json(store/'settings.json')
    require(b.get('schemaId') == 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
            and b.get('orderTransmission') is False
            and s.get('schemaId') == 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1'
            and s.get('normalMaxPositions') == 3
            and s.get('sameDayApprovalRequired') is True
            and s.get('orderTransmission') is False,
            'INSTALLED_BINDING_OR_SETTINGS')
    native = no_links(Path(b['engine'])/'windows/Start-No11UnifiedLauncher.ps1')
    gui = no_links(store/'oneclick/Start-No11OneClick.ps1')
    collectors = (
        'Run-No11RssDailyTrendCensusReadOnly.ps1',
        'Run-No11WeeklyCandidateRefreshReadOnly.ps1',
        'Capture-No11RssTrainingBatchReadOnly.ps1',
    )
    # The downstream collector must already support the user's real 3 books.
    # This is a source preflight, NEVER a new trading/selector gate.
    for name in collectors:
        source = no_links(Path(b['engine'])/'windows'/name).read_bytes()
        require(b'ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1' in source,
                'COLLECTOR_THREE_BOOK_NOT_INSTALLED_' + name.split('.')[0].upper())
    return native, gui


def atomic_replace(path, before, after):
    require(path.read_bytes() == before, 'LOCAL_EDIT_BEFORE_REPLACE')
    candidate = None
    try:
        with tempfile.NamedTemporaryFile('wb',prefix='.ark-weekly-book-',dir=path.parent,delete=False) as fp:
            candidate = Path(fp.name)
            fp.write(after)
            fp.flush()
            os.fsync(fp.fileno())
        require(path.read_bytes() == before, 'LOCAL_EDIT_BEFORE_COMMIT')
        os.replace(candidate,path)
        candidate = None
    finally:
        if candidate is not None:
            candidate.unlink(missing_ok=True)


def publish_backup(store, before):
    backups=store/'weekly-workbook-gate-backups'
    if not backups.exists():
        backups.mkdir(mode=0o700)
    no_links(backups,False)
    dest=backups/(sha(before)+'.ps1')
    if dest.exists():
        require(no_links(dest).read_bytes()==before,'ORIGINAL_BACKUP_CHANGED')
    else:
        try:
            with dest.open('xb') as f:
                f.write(before)
                f.flush()
                os.fsync(f.fileno())
        except FileExistsError:
            require(no_links(dest).read_bytes()==before,'ORIGINAL_BACKUP_RACED')
    return dest


def parse_powershell(candidate):
    with tempfile.TemporaryDirectory(prefix='ark-ps-parse-') as d:
        harness=Path(d)/'parse.ps1'
        harness.write_text(
            "param([string]$Target)\n$t=$null;$e=$null;"
            "[void][Management.Automation.Language.Parser]::ParseFile($Target,[ref]$t,[ref]$e);"
            "if($e.Count){foreach($x in $e){Write-Host ('PARSE:'+ $x.Extent.StartLineNumber+':'+$x.Message)};exit 2}\n",
            encoding='utf-8'
        )
        target=Path(d)/'candidate.ps1'
        target.write_bytes(candidate)
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                          '-File',str(harness),'-Target',str(target)],capture_output=True,
                         text=True,encoding='utf-8',errors='replace',timeout=35,check=False)
        require(r.returncode==0,'POWERSHELL_CANDIDATE_PARSE_FAILED')


def install(store, apply=False, synthetic=False):
    store=no_links(store,False)
    native,gui=preflight(store)
    raw=native.read_bytes()
    ui_hash=sha(gui.read_bytes())
    fixed=transform(raw)
    if raw==fixed:
        print('NO11_WEEKLY_BOOK_GATE=ALREADY_APPLIED',flush=True)
        return 'ALREADY_APPLIED'
    print('NO11_WEEKLY_BOOK_GATE=READY',flush=True)
    print('NO11_NATIVE_ORIGINAL_SHA256='+sha(raw),flush=True)
    print('NO11_NATIVE_NEW_SHA256='+sha(fixed),flush=True)
    if not apply:
        return 'READY'
    if not synthetic:
        parse_powershell(fixed)
    backup=publish_backup(store,raw)
    require(native.read_bytes()==raw and sha(gui.read_bytes())==ui_hash,
            'PRECOMMIT_LOCAL_CHANGE')
    atomic_replace(native,raw,fixed)
    require(native.read_bytes()==fixed and sha(gui.read_bytes())==ui_hash
            and backup.read_bytes()==raw,'POSTINSTALL_READBACK')
    return 'PASS'


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--store',required=True,type=Path)
    a.add_argument('--apply',action='store_true')
    args=a.parse_args()
    try:
        require(os.name=='nt','WINDOWS_ONLY')
        result=install(args.store,args.apply)
        print('NO11_WEEKLY_WORKBOOK_GATE_INSTALL='+result)
        print('TRADE_WORKBOOK_CHECK_CHANGED=False')
        print('RSS_COLLECTOR_VALIDATION_PRESERVED=True')
        print('WHITE_GUI_CHANGED=False')
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')
    except Exception as e:
        v=str(e)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+',v):
            v='NO11_WEEKLY_BOOK_FIX_LOCAL_SOURCE_OR_RUNTIME'
        print('NO11_WEEKLY_WORKBOOK_GATE_INSTALL=BLOCKED|'+v)
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')
        raise SystemExit(2)


if __name__=='__main__':
    main()
