#!/usr/bin/env python3
"""Make three original XLSB workbook paths consistent for LIVE preflight.

NOT an order authorization, not a dated signed-source refresh, not a BUY or EXIT
change. Preserves old settings and launcher bytes in a crash-safe journal.
Never writes any Excel workbook, brokerage ledger or trading configuration.
"""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import no11_nightly_resume as n
import no11_live_xlsb_contract as c

JOURNAL="live-xlsb-exact-three-preflight-v1-transaction.json"
KIND="ARK_NO11_LIVE_THREE_BOOK_PREFLIGHT_REBIND_V1"

def need(ok,code):
    if not ok:raise ValueError('NO11_LIVE_XLSB_INSTALL_'+code)

def b64(x):return base64.b64encode(x).decode('ascii')
def un64(x):return base64.b64decode(x,validate=True)

def atomic_replace(path,old,new):
    need(path.read_bytes()==old,'CONCURRENT_LOCAL_EDIT')
    tmp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,
                prefix='.live-three-preflight-',delete=False) as stream:
            tmp=Path(stream.name);stream.write(new)
            stream.flush();os.fsync(stream.fileno())
        need(path.read_bytes()==old,'CONCURRENT_LOCAL_EDIT')
        os.replace(tmp,path);tmp=None
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)

def check_quiet():
    # Any active LIVE process disallows rebinding. Never kill workers.
    n.no_workers()
    code=r"""$ErrorActionPreference='Stop'
try {
  $rows=@(Get-CimInstance Win32_Process -ErrorAction Stop|Where-Object {
    $_.ProcessId -ne $PID -and
    $_.Name -match '^(?:powershell|pwsh|python|pythonw)(?:[.]exe)?$' -and
    [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11UnifiedLauncher[.]ps1|Run-No11ReceivedSessionOperatorLive[.]ps1|no11_received_session_controller[.]py'
  })
  if($rows.Count){exit 3}
  exit 0
} catch {exit 4}"""
    with tempfile.TemporaryDirectory(prefix="ark-live-book-process-check-") as tmp:
        script=Path(tmp)/'check.ps1';script.write_text(code,encoding='utf-8')
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive',
                          '-ExecutionPolicy','Bypass','-File',str(script)],
                         capture_output=True,timeout=40,check=False)
    need(r.returncode==0,'LIVE_OR_ONECLICK_ACTIVE_OR_PROCESS_CHECK_FAILED')

def powershell_syntax(raw):
    with tempfile.TemporaryDirectory(prefix='ark-three-book-syntax-') as tmp:
        p=Path(tmp)/'candidate.ps1';p.write_bytes(raw)
        probe=Path(tmp)/'parse.ps1'
        probe.write_text(
          "param([string]$Target)\n"
          "$ErrorActionPreference='Stop'\n"
          "$t=$null;$e=$null\n"
          "[void][Management.Automation.Language.Parser]::ParseFile($Target,[ref]$t,[ref]$e)\n"
          "if($e.Count){exit 2}\n",encoding='utf-8')
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive',
              '-ExecutionPolicy','Bypass','-File',str(probe),'-Target',str(p)],
              capture_output=True,timeout=35,check=False)
    need(r.returncode==0,'POWERSHELL_PARSE')

def actual_open_books(binding,registered,allow_test=False):
    if allow_test:return
    helper=n.safe(binding['dataWorkbookResolver'])
    # A fresh, independent read-only Excel COM capture. No cached guesses.
    with tempfile.TemporaryDirectory(prefix='ark-three-open-books-') as tmp:
        output=Path(tmp)/'new-registry.json'
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive',
                  '-ExecutionPolicy','Bypass','-File',str(helper),
                  '-Discover','-OutputFile',str(output)],
                  capture_output=True,timeout=90,check=False)
        need(r.returncode==0 and output.is_file(),
             'EXCEL_THREE_OR_RSS_BOOKS_NOT_OPEN')
        seen=c.checked_registration(n.read(output))
    need({x:str(Path(y).resolve()).casefold() for x,y in seen.items()}==
         {x:str(Path(y).resolve()).casefold() for x,y in registered.items()},
         'EXCEL_OPEN_BOOKS_DIFFER_FROM_REGISTERED')

def plan(store,binding,allow_test=False):
    need(binding.get('schemaId')=='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' and
         binding.get('orderTransmission') is False,'BINDING_MODE')
    reg_path=n.safe(binding['dataWorkbookRegistration'])
    resolver=n.safe(binding['dataWorkbookResolver'])
    need(n.digest(reg_path.read_bytes())==binding.get('dataWorkbookRegistrationSha256')
         and n.digest(resolver.read_bytes())==binding.get('dataWorkbookResolverSha256'),
         'DATA_BOOK_REGISTRATION_PIN')
    registered=c.checked_registration(n.read(reg_path))
    actual_open_books(binding,registered,allow_test)
    engine=n.safe(binding['engine'],True)
    launcher=n.safe(engine/'windows/Start-No11UnifiedLauncher.ps1')
    operator=n.safe(engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1')
    settings=n.safe(store/'settings.json')
    original_settings=settings.read_bytes()
    cfg=n.read(settings)
    revised=c.safe_settings_change(cfg,registered)
    need(revised.get('bootstrapConfigFile')==cfg.get('bootstrapConfigFile') and
         revised.get('fullSymbolsFile')==cfg.get('fullSymbolsFile') and
         revised.get('normalMaxPositions')==3 and
         revised.get('sameDayApprovalRequired') is True and
         revised.get('orderTransmission') is False and
         revised.get('automaticOrderAuthorization') is False,
         'UNCHANGED_TRADE_POLICY')
    new_settings=n.encode(revised)
    original_launcher=launcher.read_bytes()
    transformed=c.transform_launcher(original_launcher)
    original_operator=operator.read_bytes()
    transformed_operator=c.transform_operator(original_operator)
    need(original_launcher!=transformed or c.MARK in
         original_launcher.decode('utf-8-sig'),'LAUNCHER_EDIT_NOT_NEEDED')
    if not allow_test:
        powershell_syntax(transformed)
        powershell_syntax(transformed_operator)
    protected=[store/'oneclick/Start-No11OneClick.ps1',
               engine/'windows/Observe-No11AccountReadOnly.ps1']
    for file in protected:n.safe(file)
    return {
       'schemaId':n.SCHEMA,'kind':KIND,'phase':'PREPARED',
       'orderTransmission':False,'liveOrderAuthorization':False,
       'sources':[
           {'path':str(launcher),'before':b64(original_launcher),
            'after':b64(transformed)},
           {'path':str(operator),'before':b64(original_operator),
            'after':b64(transformed_operator)},
           {'path':str(settings),'before':b64(original_settings),
            'after':b64(new_settings)}],
       'frozen':{str(p):n.digest(p.read_bytes()) for p in protected},
       'registryHash':n.digest(reg_path.read_bytes()),
       'resolverHash':n.digest(resolver.read_bytes()),
       'registration':str(reg_path),'resolver':str(resolver)}

def verify(j):
    need(j.get('schemaId')==n.SCHEMA and j.get('kind')==KIND and
         j.get('phase') in ('PREPARED','COMPLETE') and
         j.get('orderTransmission') is False and
         j.get('liveOrderAuthorization') is False,'JOURNAL')
    rows=j.get('sources')
    need(type(rows) is list and len(rows)==3 and
         len({r['path'] for r in rows})==3,'SOURCE_SET')
    for row in rows:
        p=n.safe(row['path'])
        need(p.read_bytes() in (un64(row['before']),un64(row['after'])),
             'EXTERNAL_CHANGE_DETECTED')
    for file,sha in j['frozen'].items():
        need(n.digest(n.safe(file).read_bytes())==sha,
             'FROZEN_WHITE_UI_OR_ACCOUNT_OBSERVER_CHANGED')
    need(n.digest(n.safe(j['registration']).read_bytes())==j['registryHash']
         and n.digest(n.safe(j['resolver']).read_bytes())==j['resolverHash'],
         'REGISTRATION_EDITED')
    if j['phase']=='COMPLETE':
        need(all(n.safe(row['path']).read_bytes()==un64(row['after'])
                 for row in rows),'COMPLETED_BINDING_CHANGED')

def install(store,apply=False,allow_test=False):
    store=n.safe(store,True)
    with n.exclusive(store/'unified-refresh-install.lock'):
        binding=n.read(n.safe(store/'automatic-inputs.json'))
        journal=store/JOURNAL
        if journal.exists():
            j=n.checkpoint(journal)
            verify(j)
            if j['phase']=='COMPLETE':
                return 'ALREADY_APPLIED'
            need(apply,'INCOMPLETE_TRANSACTION_REQUIRES_APPLY')
        else:
            j=plan(store,binding,allow_test)
            if not apply:return 'READY'
        if not allow_test:check_quiet()
        if not journal.exists():n.atomic(journal,j)
        for row in j['sources']:
            p=Path(row['path'])
            before=un64(row['before']);after=un64(row['after'])
            if p.read_bytes()!=after:
                atomic_replace(p,before,after)
        j['phase']='COMPLETE'
        n.atomic(journal,j);verify(j)
        return 'PASS'

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--store',required=True,type=Path)
    a.add_argument('--apply',action='store_true')
    args=a.parse_args()
    try:
        need(os.name=='nt','WINDOWS_ONLY')
        print('NO11_LIVE_XLSB_PREFLIGHT_INSTALL='+install(args.store,args.apply))
        print('NO11_LIVE_XLSB_THREE_ORIGINAL_BOOKS=REGISTERED')
        print('NO11_LIVE_XLSB_DATED_SOURCE_AND_BROKER_REVIEW_STILL_REQUIRED=True')
        print('FROZEN_ENTRY_EXIT_MODIFIED=False')
        print('WHITE_ONECLICK_MODIFIED=False')
        print('WORKBOOKS_MODIFIED=False')
    except Exception as e:
        reason=str(e)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+',reason):
            reason='NO11_LIVE_XLSB_INSTALL_UNVERIFIED_SYSTEM'
        print('NO11_LIVE_XLSB_PREFLIGHT_INSTALL=BLOCKED|'+reason)
        raise SystemExit(2)
    finally:
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')
if __name__=='__main__':main()
