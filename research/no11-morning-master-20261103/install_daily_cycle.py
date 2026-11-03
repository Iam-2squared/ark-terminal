#!/usr/bin/env python3
"""One-time transactional installation of nightly/weekly No11 Launcher rollover.

Preserve the patched Trade path, account settings and executable strategy.
Patch only the existing launcher Weekly command's target. The existing Trade
hook reads a pin-checked V4 bridge that activates the exact same-day handoff.
No RSS request, Excel attachment, market order or approval during installation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

PINS={
    'daily_cycle.py':'0720dc62ce9625c8e19b43d17c500c6b2c1e4f04',
    'scope_morning_master.py':'7006f673850401d0f3a076f2bf01ba1b25040c48',
    'launcher_automatic_bridge_v4.py':'224766266bfe953bc6dfa1abda28230fae6ff69f',
    'Run-No11NightlyCycle.ps1':'9ca459c9f58238975fe4fe4d1e03664484458a6a',
    'nightly_workbook_compat.py':'d1355306a10f86d055966e9f16e1ef8996959e70',
}
OLD = "$weekly=Join-Path $PSScriptRoot 'Prepare-No11WeeklyAfterCloseReadOnly.ps1'"
NEW = "$weekly=Join-Path $PSScriptRoot 'Run-No11NightlyCycle.ps1'"
SCHEMA='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'

def need(value,code):
    if not value:
        raise ValueError('NO11_DAILY_CYCLE_INSTALL_'+code)

def blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def safe(path,folder=False):
    p=Path(path)
    need(p.is_absolute(),'ABSOLUTE_PATH')
    for a in (p,*p.parents):
        if a.exists() or a.is_symlink():
            need(not a.is_symlink() and not (getattr(a.lstat(),'st_file_attributes',0)&1024),
                 'REPARSE_PATH')
    need(p.is_dir() if folder else p.is_file(),'SOURCE_MISSING')
    return p.resolve(strict=True)

def encode(obj):
    return (json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')

def load(path):
    raw=safe(path).read_bytes()
    need(0<len(raw)<150000,'JSON_LENGTH')
    obj=json.loads(raw.decode('utf-8-sig'))
    need(type(obj) is dict,'JSON_OBJECT')
    return obj,raw

def pin_sources(folder):
    result={}
    for name,pin in PINS.items():
        p=safe(folder/name)
        need(blob(p.read_bytes())==pin,'SOURCE_BLOB_'+name.replace('.','_').upper())
        result[name]=p
    return result

def patch_weekly_launcher(raw):
    bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text=raw[len(bom):].decode('utf-8')
    need(text.count('function RunTrade(')==1 and
         text.count('function RunWeekly(')==1 and
         '--same-day-operator-approved' in text and
         'No11RssFundingContract.ps1' in text,
         'EXISTING_TRADE_OR_RSS_PATCH_MISSING')
    if text.count(NEW)==1 and OLD not in text:
        return raw
    need(text.count(OLD)==1 and NEW not in text,
         'WEEKLY_ANCHOR_CHANGED')
    return bom+text.replace(OLD,NEW,1).encode('utf-8')

def stopped():
    ps=r"""$p=@(Get-CimInstance Win32_Process | Where-Object {
      $_.Name -match '^(pythonw?|powershell|pwsh|node)(\.exe)?$' -and
      $_.CommandLine -match '(Start-No11UnifiedLauncher\.ps1|Run-No11ReceivedSessionOperatorLive\.ps1|no11_received_session_controller\.py)' -and
      $_.ProcessId -ne $PID
    });if($p.Count){exit 2}"""
    r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],
                     capture_output=True,text=True,timeout=45)
    need(r.returncode==0,'CLOSE_ARK_BEFORE_INSTALL')

def atomic(path,raw,expected):
    p=Path(path)
    if p.exists():need(p.read_bytes()==expected,'CONCURRENT_MODIFICATION')
    else:need(expected is None,'FILE_DISAPPEARED')
    tmp=p.with_name(p.name+'.daily-'+uuid.uuid4().hex)
    try:
        with tmp.open('xb') as f:
            f.write(raw); f.flush();os.fsync(f.fileno())
        if expected is None:
            need(not p.exists(),'CONCURRENT_CREATION')
            os.rename(tmp,p)
        else:
            need(p.read_bytes()==expected,'CONCURRENT_MODIFICATION')
            os.replace(tmp,p)
    finally:
        if tmp.exists():tmp.unlink()

def ps_selftest(p,marker):
    r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy',
                      'Bypass','-File',str(p),'-OfflineSelfTest'],
                     capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
    need(r.returncode==0 and marker in (r.stdout+r.stderr),'POWERSHELL_SELFTEST')

def check_syntax(p):
    ps="$t=$null;$e=$null;[void][Management.Automation.Language.Parser]::ParseFile('"+str(p).replace("'","''")+"',[ref]$t,[ref]$e);if($e.Count){exit 2}"
    r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],
                     capture_output=True,text=True,timeout=50)
    need(r.returncode==0,'POWERSHELL_SYNTAX')

def install(folder):
    need(os.name=='nt','WINDOWS_ONLY')
    stopped()
    sources=pin_sources(folder)
    store=safe(Path(os.environ['LOCALAPPDATA'])/'ArkTerminal/No12/unified-launcher',True)
    binding_file=safe(store/'automatic-inputs.json')
    binding,before_binding=load(binding_file)
    need(binding.get('schemaId')==SCHEMA
         and binding.get('orderTransmission') is False
         and binding.get('manualEvidenceRequired') is False
         and binding.get('manualPriceInputRequired') is False,
         'INSTALLED_AUTOMATIC_TRADE_BINDING_REQUIRED')
    need('transportProbe' in binding and 'orderCollectorIdentityPolicy' in binding,
         'ORDER_EXIT_V3_MUST_BE_INSTALLED')
    for k in ('bridge','runner','automatic','handoff','transportProbe'):
        need(digest(safe(binding[k]).read_bytes())==binding[k+'Sha256'],
             'EXISTING_BOUND_'+k.upper()+'_CHANGED')
    engine=safe(binding['engine'],True)
    old_weekly=safe(engine/'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1')
    for p in (engine/'tools/no11_received_session_controller.py',
              engine/'windows/Invoke-No11MsiiOrder.ps1'):
        need(p.is_file(),'FROZEN_LIVE_RUNTIME_MISSING')
    need('# ARK_NO11_PINNED_COLLECTOR_READY_TO_ORDER_DISPATCH_V1' in
         (engine/'tools/no11_received_session_controller.py').read_text(encoding='utf-8-sig'),
         'ORDER_COLLECTOR_WIRING_MISSING')
    launcher=safe(engine/'windows/Start-No11UnifiedLauncher.ps1')
    before_launcher=launcher.read_bytes()
    compat_file=sources['nightly_workbook_compat.py']
    compat_spec=importlib.util.spec_from_file_location('ark_nightly_excel_compat',compat_file)
    compat=importlib.util.module_from_spec(compat_spec)
    compat_spec.loader.exec_module(compat)
    new_launcher=compat.transform_launcher(patch_weekly_launcher(before_launcher))
    # Accept only the already-configured order-ID workbook on the nightly path.
    # The separate LIVE order sender remains byte-for-byte unchanged.
    collector_changes={}
    for relative in compat.SCRIPTS:
        path=safe(engine/relative)
        before=path.read_bytes()
        after=compat.transform_collector(relative,before)
        need(before!=after,'NIGHTLY_COLLECTOR_ALREADY_PATCHED')
        collector_changes[path]=(before,after)
    root=store/'daily-cycle'
    root.mkdir(exist_ok=True)
    root=safe(root,True)
    package=store/'daily-cycle-tools-v1'
    package.mkdir(exist_ok=True)
    package=safe(package,True)
    files={
        package/'daily_cycle.py': sources['daily_cycle.py'].read_bytes(),
        package/'scope_morning_master.py': sources['scope_morning_master.py'].read_bytes(),
        package/'launcher_automatic_bridge_v4.py':sources['launcher_automatic_bridge_v4.py'].read_bytes(),
        package/'nightly_workbook_compat.py':sources['nightly_workbook_compat.py'].read_bytes(),
        engine/'windows/Run-No11NightlyCycle.ps1':sources['Run-No11NightlyCycle.ps1'].read_bytes(),
    }
    for path,raw in files.items():
        if path.exists():
            need(path.read_bytes()==raw,'UNKNOWN_PREEXISTING_TOOL_'+path.name.replace('.','_').upper())
    new_binding=dict(binding,
        bridge=str(package/'launcher_automatic_bridge_v4.py'),
        bridgeSha256=digest(files[package/'launcher_automatic_bridge_v4.py']),
        scopeTool=str(package/'scope_morning_master.py'),
        scopeToolSha256=digest(files[package/'scope_morning_master.py']),
        dailyCycleTool=str(package/'daily_cycle.py'),
        dailyCycleToolSha256=digest(files[package/'daily_cycle.py']),
        dailyCycleRoot=str(root),
        dateRolloverMode='ORIGINAL_RSS_NIGHTLY_IMMUTABLE_NEXT_SESSION_ONLY',
        manualEvidenceRequired=False,manualPriceInputRequired=False,orderTransmission=False)
    after_binding=encode(new_binding)
    backup=store/('daily-cycle-install-'+uuid.uuid4().hex)
    backup.mkdir(mode=0o700)
    (backup/'launcher.before.ps1').write_bytes(before_launcher)
    (backup/'automatic-inputs.before.json').write_bytes(before_binding)
    import py_compile
    for key in ('daily_cycle.py','launcher_automatic_bridge_v4.py','scope_morning_master.py','nightly_workbook_compat.py'):
        py_compile.compile(str(sources[key]),doraise=True,
                           cfile=str(backup/(key+'.pyc')))
    candidate=backup/'nightly.candidate.ps1'
    candidate.write_bytes(files[engine/'windows/Run-No11NightlyCycle.ps1'])
    check_syntax(candidate)
    candidate.unlink()
    for p,(original,patched) in collector_changes.items():
        (backup/(p.name+'.before')).write_bytes(original)
        candidate=backup/(p.name+'.candidate.ps1')
        candidate.write_bytes(patched)
        check_syntax(candidate)
        candidate.unlink()
    candidate=backup/'launcher.candidate.ps1'
    candidate.write_bytes(new_launcher)
    check_syntax(candidate)
    candidate.unlink()
    modified=[]
    try:
        for path,raw in files.items():
            if not path.exists():
                atomic(path,raw,None)
                modified.append((path,None,raw))
        for p,(before,after) in collector_changes.items():
            atomic(p,after,before)
            modified.append((p,before,after))
        if new_launcher!=before_launcher:
            atomic(launcher,new_launcher,before_launcher)
            modified.append((launcher,before_launcher,new_launcher))
        if after_binding!=before_binding:
            atomic(binding_file,after_binding,before_binding)
            modified.append((binding_file,before_binding,after_binding))
        ps_selftest(engine/'windows/Run-No11NightlyCycle.ps1',
                    'NO11_NIGHTLY_CYCLE_OFFLINE_SELFTEST=PASS')
        for name,marker in (
            ('Run-No11RssDailyTrendCensusReadOnly.ps1','NO11_DAILY_OFFLINE_SELFTEST=PASS'),
            ('Run-No11WeeklyCandidateRefreshReadOnly.ps1','NO11_DAILY_OFFLINE_SELFTEST=PASS'),
            ('Capture-No11RssTrainingBatchReadOnly.ps1','NO11_BATCH_OFFLINE_SELFTEST=PASS')
        ):
            ps_selftest(engine/'windows'/name,marker)
        ps_selftest(launcher,'NO11_UNIFIED_OFFLINE_SELFTEST=PASS')
        need(safe(old_weekly).read_bytes()!=b'','WEEKLY_SOURCE_CHANGED')
    except BaseException:
        for p,before,after in reversed(modified):
            if p.is_file() and p.read_bytes()==after:
                if before is None:p.unlink()
                else:atomic(p,before,after)
        raise
    print('NO11_DAILY_WEEKLY_LAUNCHER_INSTALL=PASS')
    print('WEEKLY_BUTTON=ORIGINAL_RSS_THEN_NEXT_DAY_HANDOFF')
    print('TRADE_BUTTON=CURRENT_SESSION_IMMUTABLE_HANDOFF')
    print('ORIGINAL_STRATEGY_FILES_MODIFIED=False')
    print('NIGHTLY_CONFIGURED_THIRD_ORDER_BOOK=SUPPORTED_WITHOUT_TOUCHING_IT')
    print('ORIGINAL_LIVE_ORDER_EXIT_PATCH=PRESERVED')
    print('MANUAL_EVIDENCE_REQUIRED=False')
    print('MANUAL_PRICE_INPUT_REQUIRED=False')
    print('LAUNCHER_OFFLINE_SELFTEST=PASS')
    print('NIGHTLY_OFFLINE_SELFTEST=PASS')
    print('EXCEL_TOUCHED=False')
    print('TRADE_LAUNCHED=False')
    print('ORDER_TRANSMISSION=False')
    print('BACKUP_ROOT='+str(backup))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source-dir',required=True,type=Path)
    a=p.parse_args()
    install(a.source_dir)

if __name__=="__main__":
    try:main()
    except Exception as e:
        code=str(e)
        if not re.fullmatch(r'NO11_DAILY_CYCLE_INSTALL_[A-Z0-9_]+',code):
            code='NO11_DAILY_CYCLE_INSTALL_UNVERIFIED_LOCAL_CHANGE'
        print('NO11_DAILY_WEEKLY_LAUNCHER_INSTALL=BLOCKED|'+code,file=sys.stderr)
        print('ORDER_TRANSMISSION=False',file=sys.stderr)
        raise SystemExit(2)
