#!/usr/bin/env python3
"""Scoped versioned install for the safe BD4 Excel 1004 format-first fix.

Never touches Excel/RSS/Market Speed II, original Trading strategy, LIVE order
authorization, any broker ledger, old transport source, daily pointer, data
receipt or white OneClick. Never launches Trade or replays a sent order.

Detects an actual Sha-pinned resilient V3 probe; writes a distinct versioned
transport source, safely journals the two-key binding switch, validates source
PowerShell syntax on Windows, and guarantees rollback/retry on interrupted
installation without ever rewriting unknown local changes.
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
import no11_transport_format_guard as guard

JOURNAL='excel-bd4-format-first-v1-transaction.json'
KIND='ARK_NO11_EXCEL_BD4_FORMAT_BEFORE_SESSION_RELEASE_V1'
SCRIPT='Prepare-No11AutomaticLiveTransportFormatFirst.ps1'
ONLY_CHANGED={'transportProbe','transportProbeSha256'}

def need(ok,reason):
    if not ok:raise ValueError('NO11_BD4_RELEASE_'+reason)

def b64(raw):
    return base64.b64encode(raw).decode('ascii')
def un64(txt):
    return base64.b64decode(txt,validate=True)

def immutable(path,raw):
    path=Path(path)
    need(not path.is_symlink(),'REPARSE_OUTPUT')
    if path.exists():
        need(n.safe(path).read_bytes()==raw,'IMMUTABLE_OUTPUT_CHANGED')
        return
    tmp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,
             prefix='.bd4-format-',delete=False) as stream:
            tmp=Path(stream.name);stream.write(raw)
            stream.flush();os.fsync(stream.fileno())
        try:os.link(tmp,path)
        except FileExistsError:need(n.safe(path).read_bytes()==raw,'RACING_OUTPUT_CHANGED')
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)

def exchange(path,old,new):
    need(n.safe(path).read_bytes()==old,'LOCAL_BINDING_CHANGED')
    tmp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,
             prefix='.bd4-binding-',delete=False) as stream:
            tmp=Path(stream.name);stream.write(new)
            stream.flush();os.fsync(stream.fileno())
        need(path.read_bytes()==old,'LOCAL_BINDING_CHANGED')
        os.replace(tmp,path);tmp=None
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)

def syntax(source):
    with tempfile.TemporaryDirectory(prefix='ark-bd4-safe-parse-') as folder:
        src=Path(folder)/'candidate.ps1'
        src.write_bytes(source)
        harness=Path(folder)/'parse.ps1'
        harness.write_text(
          'param([string]$Candidate)\n'
          '$ErrorActionPreference="Stop"\n'
          '$a=$null;$b=$null\n'
          '[void][Management.Automation.Language.Parser]::ParseFile($Candidate,[ref]$a,[ref]$b)\n'
          'if($b.Count -gt 0){exit 2}\n',encoding='utf-8')
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive',
            '-ExecutionPolicy','Bypass','-File',str(harness),
            '-Candidate',str(src)],capture_output=True,timeout=40,check=False)
        need(r.returncode==0,'SOURCE_POWERSHELL_PARSE_FAILED')

def quiet():
    n.no_workers()
    script=r"""$ErrorActionPreference='Stop'
try{
 $rows=@(Get-CimInstance Win32_Process -ErrorAction Stop|Where-Object {
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(powershell|pwsh|python|pythonw|node)([.]exe)?$' -and
  [string]$_.CommandLine -match '(?:Start-No11OneClick[.]ps1|Start-No11UnifiedLauncher[.]ps1|Run-No11ReceivedSessionOperatorLive[.]ps1|no11_received_session_controller[.]py|Invoke-No11MsiiOrder[.]ps1)'
 })
 if($rows.Count){exit 3}
 exit 0
}catch{exit 4}"""
    with tempfile.TemporaryDirectory(prefix='ark-bd4-worker-check-') as folder:
        checker=Path(folder)/'process-check.ps1'
        checker.write_text(script,encoding='utf-8')
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive',
            '-ExecutionPolicy','Bypass','-File',str(checker)],
            capture_output=True,timeout=40,check=False)
        need(r.returncode==0,'CLOSE_ONECLICK_OR_ACTIVE_LIVE_WORKER')

def plan(store,allow_test=False):
    binding_file=n.safe(store/'automatic-inputs.json')
    original=binding_file.read_bytes()
    binding=n.read(binding_file)
    need(binding.get('schemaId')=='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
         and binding.get('orderTransmission') is False
         and binding.get('manualPriceInputRequired') is False,
         'BINDING_MODE')
    settings=n.safe(store/'settings.json')
    cfg=n.read(settings)
    need(cfg.get('schemaId')=='ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1'
         and cfg.get('orderTransmission') is False
         and cfg.get('automaticOrderAuthorization') is False
         and cfg.get('sameDayApprovalRequired') is True
         and cfg.get('normalMaxPositions')==3,'ORIGINAL_TRADE_POLICY')
    original_source=n.safe(binding['transportProbe'])
    raw=original_source.read_bytes()
    need(n.digest(raw)==binding['transportProbeSha256'],
         'ORIGINAL_TRANSPORT_SOURCE_SHA_MISMATCH')
    changed=guard.transform(raw)
    need(changed!=raw and guard.MARK.encode() in changed,
         'FORMAT_FIX_NOT_NEW')
    if not allow_test:syntax(changed)
    package=store/('transport-format-first-'+n.digest(changed)[:24])
    destination=package/SCRIPT
    new_binding=dict(binding,
       transportProbe=str(destination),
       transportProbeSha256=n.digest(changed))
    need(all(new_binding.get(k)==v for k,v in binding.items()
             if k not in ONLY_CHANGED)
         and set(new_binding)==set(binding),
         'UNRELATED_BINDING_EDIT')
    engine=n.safe(binding['engine'],True)
    frozen=[settings,
            n.safe(store/'oneclick/Start-No11OneClick.ps1'),
            n.safe(engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1'),
            n.safe(engine/'windows/Invoke-No11MsiiOrder.ps1')]
    for field in ('dataWorkbookRegistration','dataWorkbookResolver'):
        if field in binding:
            file=n.safe(binding[field])
            need(n.digest(file.read_bytes())==binding[field+'Sha256'],
                 'THREE_BOOK_REGISTRATION_CHANGED')
            frozen.append(file)
    return {
        'schemaId':n.SCHEMA,'kind':KIND,'phase':'PREPARED',
        'orderTransmission':False,'liveOrderAuthorization':False,
        'binding':str(binding_file),'bindingBefore':b64(original),
        'bindingAfter':b64(n.encode(new_binding)),
        'originalProbe':str(original_source),
        'originalProbeSha256':n.digest(raw),
        'package':str(package),'candidate':str(destination),
        'candidateSha256':n.digest(changed),'candidateBytes':b64(changed),
        'frozen':{str(p):n.digest(p.read_bytes()) for p in frozen}
    }

def verify(j):
    need(j.get('schemaId')==n.SCHEMA and j.get('kind')==KIND and
         j.get('phase') in ('PREPARED','COMPLETE') and
         j.get('orderTransmission') is False and
         j.get('liveOrderAuthorization') is False,'JOURNAL_SCHEMA')
    before=un64(j['bindingBefore'])
    after=un64(j['bindingAfter'])
    a=json.loads(before.decode('utf-8-sig'))
    b=json.loads(after.decode('utf-8-sig'))
    need(set(a)==set(b) and
         all(b.get(k)==v for k,v in a.items() if k not in ONLY_CHANGED)
         and a.get('orderTransmission') is False
         and b.get('orderTransmission') is False,
         'JOURNAL_BINDING_SCOPE')
    need(n.safe(j['binding']).read_bytes() in (before,after),
         'JOURNAL_BINDING_UNKNOWN_EDIT')
    candidate=un64(j['candidateBytes'])
    need(n.digest(candidate)==j['candidateSha256'] and
         guard.MARK.encode() in candidate and
         n.digest(n.safe(j['originalProbe']).read_bytes())==j['originalProbeSha256'],
         'JOURNAL_PROBE_SOURCE_CHANGED')
    for path,digest in j['frozen'].items():
        need(n.digest(n.safe(path).read_bytes())==digest,
             'FROZEN_ORIGINAL_EDIT')
    path=Path(j['candidate'])
    if path.exists() or path.is_symlink():
        need(n.safe(path).read_bytes()==candidate,'INSTALLED_TRANSPORT_EDIT')
    elif j['phase']=='COMPLETE':
        need(False,'INSTALLED_TRANSPORT_MISSING')
    if j['phase']=='COMPLETE':
        need(n.safe(j['binding']).read_bytes()==after,
             'FINISHED_BINDING_CHANGED')
    return before,after,candidate

def install(store,apply=False,allow_test=False):
    store=n.safe(store,True)
    with n.exclusive(store/'unified-refresh-install.lock'):
        journal=store/JOURNAL
        if journal.exists():
            j=n.checkpoint(journal)
            before,after,candidate=verify(j)
            if j['phase']=='COMPLETE':return 'ALREADY_APPLIED'
            need(apply,'PREPARED_REQUIRES_APPLY')
        else:
            j=plan(store,allow_test)
            if not apply:return 'READY'
            before,after,candidate=verify_before_new(j)
        if not allow_test:quiet()
        package=Path(j['package'])
        package.mkdir(exist_ok=True)
        n.safe(package,True)
        immutable(Path(j['candidate']),candidate)
        if not journal.exists():n.atomic(journal,j)
        # Full frozen-file and prior probe verification just before the swap.
        verify(j)
        current=n.safe(j['binding']).read_bytes()
        if current!=after:exchange(Path(j['binding']),before,after)
        j['phase']='COMPLETE'
        n.atomic(journal,j)
        verify(j)
        return 'PASS'

def verify_before_new(j):
    # Prior to writing a journal, candidate does not yet exist.
    need(j.get('phase')=='PREPARED','NEW_PHASE')
    candidate=un64(j['candidateBytes'])
    need(n.digest(candidate)==j['candidateSha256'],'NEW_CANDIDATE_SHA')
    need(n.safe(j['binding']).read_bytes()==un64(j['bindingBefore']),
         'NEW_SOURCE_CHANGED')
    return un64(j['bindingBefore']),un64(j['bindingAfter']),candidate

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store',required=True,type=Path)
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    try:
        need(os.name=='nt','WINDOWS_ONLY')
        state=install(args.store,args.apply)
        print('NO11_BD4_FORMAT_FIRST_INSTALL='+state)
        print('FORMULA_GENERAL_VALIDATED_BEFORE_SESSION=True')
        print('PARTIAL_SESSION_KEY_GUARD=True')
        print('TRANSPORT_WRITE_RETRY=False')
        print('WHITE_UI_ORIGINAL_CHANGED=False')
        print('EXCEL_WORKBOOKS_CHANGED=False')
        print('DATA_RECAPTURED=False')
    except Exception as exc:
        reason=str(exc)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+',reason):
            reason='NO11_BD4_RELEASE_UNVERIFIED_INSTALLED_SOURCE'
        print('NO11_BD4_FORMAT_FIRST_INSTALL=BLOCKED|'+reason)
        raise SystemExit(2)
    finally:
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')
if __name__=='__main__':
    main()
