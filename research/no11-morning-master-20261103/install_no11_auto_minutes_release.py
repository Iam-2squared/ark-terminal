#!/usr/bin/env python3
"""Install perpetual small-invalid-1M auto-skip; resume already complete RSS log.

One-time release install, no changes to original Excel/RSS workbooks, original
source observations, orders, frozen ENTRY/EXIT, white OneClick or live settings.

Atomic source journal + versioned package + bound SHA, then optionally reuse
the already completed Friday+Monday 2026-11-09 capture without recollecting.
Unvalidated or non-current saved logs are NEVER silently relabeled/reused.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import no11_nightly_resume as n
import no11_nightly_resume_workeraware as process_probe
import no11_auto_minute_cycle_transform as cycle_patch
import no11_auto_minute_worker_transform as worker_patch

KIND='ARK_NO11_AUTO_INVALID_MINUTE_ENTRY_EXCLUSION_RELEASE_V2'
JOURNAL='auto-minute-exclusion-release-v2-transaction.json'
MODULE='daily_cycle.py'
HELPER='no11_auto_minute_exclusion.py'
WORKER='no11_nightly_resume_workeraware.py'
VALIDATOR='no11_selection_status.py'
KEYS={'dailyCycleTool','dailyCycleToolSha256',
      'nightlyResumeTool','nightlyResumeToolSha256',
      'autoMinuteExclusionToolSha256'}
JST=timezone(timedelta(hours=9))

def need(value,reason):
    if not value:
        raise ValueError('NO11_AUTO_MINUTE_INSTALL_'+reason)

def b64(raw):
    return base64.b64encode(raw).decode('ascii')

def un64(value):
    return base64.b64decode(value,validate=True)

def read_binding(store):
    path=n.safe(store/'automatic-inputs.json')
    binding=n.read(path)
    need(binding.get('schemaId')=='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
         and binding.get('orderTransmission') is False
         and binding.get('manualEvidenceRequired') is False
         and binding.get('manualPriceInputRequired') is False,
         'DATA_BINDING_CONTRACT')
    return path,binding

def safe_output(path,raw):
    path=Path(path)
    n.safe(path.parent,True)
    need(not path.is_symlink(),'OUTPUT_REPARSE')
    if path.exists():
        need(n.safe(path).read_bytes()==raw,'VERSION_PACKAGE_CHANGED')
        return
    temp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,
                prefix='.minute-release-',delete=False) as stream:
            temp=Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp,path)
        except FileExistsError:
            need(n.safe(path).read_bytes()==raw,'CONCURRENT_PACKAGE_CHANGED')
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)

def atomic_replace(path,old,new):
    need(n.safe(path).read_bytes()==old,'CONCURRENT_BINDING_EDIT')
    temp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,
                prefix='.minute-binding-',delete=False) as stream:
            temp=Path(stream.name)
            stream.write(new)
            stream.flush()
            os.fsync(stream.fileno())
        need(path.read_bytes()==old,'CONCURRENT_BINDING_EDIT')
        os.replace(temp,path)
        temp=None
    finally:
        if temp is not None:temp.unlink(missing_ok=True)

def quiet():
    process_probe.no_workers()
    script=r"""$ErrorActionPreference='Stop'
try {
 $rows=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
 $_.ProcessId -ne $PID -and
 $_.Name -match '^(?:powershell|pwsh)(?:[.]exe)?$' -and
 [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11PreopenStandby[.]ps1'
 })
 if($rows.Count){exit 3};exit 0
} catch {exit 4}"""
    with tempfile.TemporaryDirectory(prefix='ark-minute-ui-check-') as folder:
        file=Path(folder)/'ui-process-check.ps1'
        file.write_text(script,encoding='utf-8')
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive',
                   '-ExecutionPolicy','Bypass','-File',str(file)],
                   capture_output=True,timeout=35,check=False)
    need(result.returncode!=3,'CLOSE_ONECLICK_FIRST')
    need(result.returncode==0,'UI_QUERY_FAILED')

def build(store,source):
    binding_file,binding=read_binding(store)
    settings=n.read(n.safe(store/'settings.json'))
    need(settings.get('schemaId')=='ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1'
         and settings.get('orderTransmission') is False
         and settings.get('automaticOrderAuthorization') is False
         and settings.get('sameDayApprovalRequired') is True
         and settings.get('normalMaxPositions')==3,
         'TRADING_SETTINGS_MUST_STAY_FROZEN')
    need(binding.get('dataWorkbookRegistrationSha256') and
         binding.get('dataWorkbookResolverSha256'),
         'THREE_REGISTERED_XLSB_BOOKS_REQUIRED')
    registry=n.safe(binding['dataWorkbookRegistration'])
    helperreg=n.safe(binding['dataWorkbookResolver'])
    need(n.digest(registry.read_bytes())==binding['dataWorkbookRegistrationSha256']
         and n.digest(helperreg.read_bytes())==binding['dataWorkbookResolverSha256'],
         'REGISTERED_BOOK_SOURCE_CHANGED')
    old_cycle=n.safe(binding['dailyCycleTool'])
    old_worker=n.safe(binding['nightlyResumeTool'])
    validator=n.safe(old_worker.with_name(VALIDATOR))
    need(n.digest(old_cycle.read_bytes())==binding.get('dailyCycleToolSha256') and
         n.digest(old_worker.read_bytes())==binding.get('nightlyResumeToolSha256') and
         n.digest(validator.read_bytes())==binding.get('nightlyResumeValidatorSha256'),
         'CURRENT_DATA_CODE_PIN_CHANGED')
    original_cycle=old_cycle.read_bytes()
    cycle=cycle_patch.transform(original_cycle)
    auto_helper=n.safe(source/HELPER).read_bytes()
    helper_sha=n.digest(auto_helper)
    old_worker_raw=old_worker.read_bytes()
    worker=worker_patch.transform(old_worker_raw,helper_sha)
    package_sha=n.digest(n.encode({
       MODULE:n.digest(cycle),HELPER:helper_sha,
       WORKER:n.digest(worker),VALIDATOR:n.digest(validator.read_bytes())}))
    package=store/('automatic-safe-minute-exclusion-'+package_sha[:24])
    updated=dict(binding,dailyCycleTool=str(package/MODULE),
                 dailyCycleToolSha256=n.digest(cycle),
                 nightlyResumeTool=str(package/WORKER),
                 nightlyResumeToolSha256=n.digest(worker),
                 autoMinuteExclusionToolSha256=helper_sha)
    need(all(updated.get(k)==val for k,val in binding.items()
             if k not in KEYS) and updated.get('orderTransmission') is False,
         'UNRELATED_BINDING_CHANGED')
    frozen=[
       n.safe(store/'settings.json'),
       n.safe(store/'oneclick/Start-No11OneClick.ps1'),
       n.safe(Path(binding['engine'])/'windows/Run-No11ReceivedSessionOperatorLive.ps1'),
       registry,helperreg]
    payload={MODULE:cycle,HELPER:auto_helper,WORKER:worker,
             VALIDATOR:validator.read_bytes()}
    previous_work_tag=re.findall(r"(?m)^    work = root / 'resumable-nightly' / \(asof \+ '_' \+ target \+ ('-(?:data-books-v1|auto-minutes-v1)-[a-f0-9]{16}')\)$",
                                  old_worker_raw.decode('utf-8-sig'))
    need(len(previous_work_tag)==1,'OLD_DATA_WORKER_NAMESPACE_CHANGED')
    return {'schemaId':n.SCHEMA,'kind':KIND,'phase':'PREPARED',
       'orderTransmission':False,
       'bindingFile':str(binding_file),'bindingBefore':b64(binding_file.read_bytes()),
       'bindingAfter':b64(n.encode(updated)),
       'oldCycleSha256':n.digest(original_cycle),
       'oldWorkerSha256':n.digest(old_worker_raw),
       'legacyWorkTag':previous_work_tag[0].strip("'"),
       'package':str(package),
       'payload':{k:{'data':b64(v),'sha256':n.digest(v)} for k,v in payload.items()},
       'frozenFiles':{str(p):n.digest(p.read_bytes()) for p in frozen}}

def verify(j):
    need(j.get('schemaId')==n.SCHEMA and j.get('kind')==KIND and
         j.get('phase') in ('PREPARED','COMPLETE') and
         j.get('orderTransmission') is False,'JOURNAL_SCHEMA')
    before=un64(j['bindingBefore'])
    after=un64(j['bindingAfter'])
    first=json.loads(before.decode('utf-8-sig'))
    latter=json.loads(after.decode('utf-8-sig'))
    need(all(latter.get(k)==v for k,v in first.items() if k not in KEYS)
         and first.get('orderTransmission') is False
         and latter.get('orderTransmission') is False,
         'BINDING_ESCALATION')
    need(n.safe(j['bindingFile']).read_bytes() in (before,after),
         'BINDING_MANUALLY_CHANGED')
    payload=j.get('payload',{})
    need(set(payload)=={MODULE,HELPER,WORKER,VALIDATOR},'RELEASE_FILE_SET')
    for k,row in payload.items():
        need(n.digest(un64(row['data']))==row['sha256'],
             'RELEASE_FILE_HASH_'+k.upper().split('.')[0])
    for name,sha in j['frozenFiles'].items():
        need(n.digest(n.safe(name).read_bytes())==sha,'FROZEN_UI_TRADE_OR_REGISTRY_CHANGED')
    if n.safe(j['bindingFile']).read_bytes()==before:
        need(n.digest(n.safe(first['dailyCycleTool']).read_bytes())==j['oldCycleSha256'] and
             n.digest(n.safe(first['nightlyResumeTool']).read_bytes())==j['oldWorkerSha256'],
             'OLD_INSTALLED_DATA_SOURCE_CHANGED')
    if n.safe(j['bindingFile']).read_bytes()==after or j.get('phase')=='COMPLETE':
        for name,row in payload.items():
            need(n.digest(n.safe(Path(j['package'])/name).read_bytes())==row['sha256'],
                 'INSTALLED_PACKAGE_CHANGED')
    return first,latter

def apply(j):
    first,after=verify(j)
    package=Path(j['package'])
    package.mkdir(exist_ok=True)
    n.safe(package,True)
    for name,row in j['payload'].items():
        safe_output(package/name,un64(row['data']))
    binding=Path(j['bindingFile'])
    target=un64(j['bindingAfter'])
    if binding.read_bytes()!=target:
        atomic_replace(binding,un64(j['bindingBefore']),target)
    verify(j)
    need(binding.read_bytes()==target,'BINDING_COMMIT_READBACK')
    for name,row in j['payload'].items():
        need(n.digest(n.safe(package/name).read_bytes())==row['sha256'],
             'PACKAGE_READBACK')

def locate_saved(store,j):
    # The exact old version namespace is known from its attested source.
    # Do not discover any arbitrary older dates, change the clock, or recapture.
    first,_=verify(j)
    root=n.safe(first['dailyCycleRoot'],True)
    candidates=[]
    for work in (root/'resumable-nightly').glob('*'+j['legacyWorkTag']):
        if not work.is_dir() or work.is_symlink():continue
        state_file=work/'checkpoint.json'
        if not state_file.is_file():continue
        try:
            state=n.checkpoint(state_file)
            identity=state['identity']
            asof=identity['asOfSession']
            target=identity['sessionDate']
            clock=datetime.now(JST).date().isoformat()
            if not (target>=clock and asof<target and
                    state['phase'] in ('CAPTURING','CAPTURED','PUBLISHING') and
                    identity.get('orderTransmission') is False and
                    identity.get('engine')==first['engine'] and
                    identity.get('symbolsSha256')==n.digest(
                        n.safe(n.read(store/'settings.json')['fullSymbolsFile']).read_bytes())):
                continue
            logname=state.get('captureLog') or state.get('attemptLog')
            if not (type(logname) is str and
                    re.fullmatch(r'capture-[a-f0-9]{32}\.log',logname)):
                continue
            log=n.safe(work/logname)
            candidates.append((target,work,log))
        except (ValueError,KeyError,TypeError,FileNotFoundError):
            continue
    need(len(candidates)<=1,'AMBIGUOUS_SAVED_CAPTURES')
    if not candidates:return None
    return candidates[0]

def resume(store,j):
    item=locate_saved(store,j)
    if item is None:
        print('NO11_AUTO_MINUTE_SAVED_CAPTURE=NONE_CURRENT',flush=True)
        return
    target,work,log=item
    _,after=verify(j)
    settings=n.read(store/'settings.json')
    python=n.safe(after['python'])
    worker=n.safe(after['nightlyResumeTool'])
    binding=n.safe(j['bindingFile'])
    symbols=n.safe(settings['fullSymbolsFile'])
    print('NO11_AUTO_MINUTE_SAVED_CAPTURE=VERIFIED_CURRENT_SESSION',flush=True)
    print('NO11_AUTO_MINUTE_SAVED_CAPTURE_TARGET='+target,flush=True)
    env=dict(os.environ,ARK_AUTO_MINUTE_RESUME_ONLY='1',
             PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([str(python),'-B','-X','utf8',str(worker),
                '--binding',str(binding),'--symbols',str(symbols)],
                env=env,capture_output=True,encoding='utf-8',
                errors='replace',timeout=1800,check=False)
    # Public-only status. Real saved source receipt paths remain on the PC.
    for line in (result.stdout+'\n'+result.stderr).splitlines():
        if (line.startswith('NO11_') or line.startswith('ORDER_TRANSMISSION=')
             or line.startswith('TRADE_LAUNCHED=')):
            print(line,flush=True)
    if result.returncode:
        print('NO11_AUTO_MINUTE_SAVED_STAGE=BLOCKED|VERIFIED_RECEIPT_OR_PUBLIC_SOURCE',flush=True)
        need(False,'SAVED_STAGE_FAILED')
    else:
        print('NO11_AUTO_MINUTE_SAVED_STAGE=PASS',flush=True)

def install(store,source,apply_release=False,test=False):
    store=n.safe(store,True)
    source=n.safe(source,True)
    with n.exclusive(store/'unified-refresh-install.lock'):
        journal=store/JOURNAL
        if journal.exists():
            j=n.checkpoint(journal)
            verify(j)
            if j['phase']=='COMPLETE':
                return 'ALREADY_APPLIED',j
            need(apply_release,'PREPARED_TRANSACTION_REQUIRES_APPLY')
        else:
            j=build(store,source)
            if not apply_release:
                return 'READY',j
        if not test:
            quiet()
        if not journal.exists():
            n.atomic(journal,j)
        apply(j)
        j['phase']='COMPLETE'
        n.atomic(journal,j)
        return 'PASS',j

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store',required=True,type=Path)
    p.add_argument('--source-dir',required=True,type=Path)
    p.add_argument('--apply',action='store_true')
    a=p.parse_args()
    try:
        need(os.name=='nt','WINDOWS_ONLY')
        outcome,j=install(a.store,a.source_dir,a.apply)
        print('NO11_AUTO_MINUTE_RELEASE_INSTALL='+outcome)
        print('SMALL_MISSING_1M_SYMBOLS=AUTOMATIC_EXCLUDE_UP_TO_3')
        print('WHITE_GUI_CHANGED=False')
        print('FROZEN_TRADE_AND_EXIT_CHANGED=False')
        print('ORIGINAL_RSS_RECEIPTS_CHANGED=False')
        if a.apply:
            # The newest already completed historic capture may be reused.
            # Never fall back to a new RSS capture from the install itself.
            resume(a.store,j)
    except Exception as exc:
        reason=str(exc)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+',reason):
            reason='NO11_AUTO_MINUTE_INSTALL_UNVERIFIED_RUNTIME'
        print('NO11_AUTO_MINUTE_RELEASE_INSTALL=BLOCKED|'+reason)
        raise SystemExit(2)
    finally:
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')

if __name__=='__main__':main()
