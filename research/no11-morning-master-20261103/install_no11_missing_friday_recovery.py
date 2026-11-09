#!/usr/bin/env python3
"""Atomic, checkpointed installation of missing-Friday *real RSS* data recovery.

Never calls Excel, changes order permissions, launches a collection, touches
model/ENTRY/EXIT, drops receipts or bypasses weekly-staleness checks.
Stage new files and immutable backup before one-by-one engine update, commit
the worker binding LAST, and resume any partial local installation safely.
"""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import no11_nightly_resume as n
import no11_nightly_resume_workeraware as live_probe
import no11_missing_friday_recovery_transform as patch

KIND='ARK_NO11_MISSING_FRIDAY_REAL_RSS_RECOVERY_RELEASE_V1'
JOURNAL='missing-friday-real-rss-transaction.json'
ENGINE={
 'dailyTool':'tools/no11_rss_daily_trend_census.mjs',
 'dailyCollector':'windows/Run-No11RssDailyTrendCensusReadOnly.ps1',
 'next':'windows/Prepare-No11NextSessionNightlyReadOnly.ps1',
 'weekly':'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1'}
WORKER='no11_nightly_resume_workeraware.py'
VALIDATOR='no11_selection_status.py'
WORKEE='nightlyResumeTool'


def need(ok,code):
    if not ok:
        raise ValueError('NO11_REAL_FRIDAY_INSTALL_'+code)


def b64(raw):
    return base64.b64encode(raw).decode('ascii')


def un64(s):
    return base64.b64decode(s,validate=True)


def harmless_signature(before,after):
    need(before!=after,'NO_CHANGES')
    need(after.get('orderTransmission') is False,'ORDER_TRANSMISSION')
    for key,val in before.items():
        if key not in ('nightlyResumeTool','nightlyResumeToolSha256'):
            need(val==after.get(key),'UNRELATED_BINDING_EDIT')


def plan(store):
    binding_file=n.safe(store/'automatic-inputs.json')
    before=binding_file.read_bytes()
    binding=n.read(binding_file)
    need(binding.get('schemaId')=='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
         and binding.get('orderTransmission') is False
         and binding.get('manualEvidenceRequired') is False
         and binding.get('manualPriceInputRequired') is False,
         'BINDING_CONTRACT')
    settings=n.read(n.safe(store/'settings.json'))
    need(settings.get('schemaId')=='ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1'
         and settings.get('orderTransmission') is False
         and settings.get('sameDayApprovalRequired') is True
         and settings.get('normalMaxPositions')==3
         and settings.get('automaticOrderAuthorization') is False,
         'TRADING_SETTINGS_CHANGED')
    gui=n.safe(store/'oneclick/Start-No11OneClick.ps1')
    ui_hash=n.digest(gui.read_bytes())
    engine=n.safe(binding['engine'],True)
    trade=n.safe(engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1')
    trade_hash=n.digest(trade.read_bytes())
    old_worker=n.safe(binding[WORKEE])
    need(n.digest(old_worker.read_bytes())==binding.get(WORKEE+'Sha256'),
         'BOUND_WORKER_MISMATCH')
    validator=n.safe(old_worker.with_name(VALIDATOR))
    need(n.digest(validator.read_bytes())==binding.get('nightlyResumeValidatorSha256'),
         'VALIDATOR_CHANGED')
    updates={}
    for kind,relative in ENGINE.items():
        p=n.safe(engine/relative)
        raw=p.read_bytes()
        result=patch.transform(kind,raw)
        need(raw!=result,'FILE_ALREADY_PATCHED_NO_JOURNAL')
        updates[kind]={'path':str(p),'before':b64(raw),
                       'after':b64(result),
                       'beforeSha256':n.digest(raw),
                       'afterSha256':n.digest(result)}
    worker_source=old_worker.read_bytes()
    new_worker=patch.transform('worker',worker_source)
    package=store/('real-friday-worker-'+n.digest(new_worker)[:20])
    updated=dict(binding,nightlyResumeTool=str(package/WORKER),
                 nightlyResumeToolSha256=n.digest(new_worker))
    harmless_signature(binding,updated)
    after=n.encode(updated)
    return {'schemaId':n.SCHEMA,'kind':KIND,'phase':'PREPARED','orderTransmission':False,
            'store':str(store),'bindingFile':str(binding_file),
            'bindingBefore':b64(before),'bindingAfter':b64(after),
            'bindingBeforeSha256':n.digest(before),'bindingAfterSha256':n.digest(after),
            'worker':str(package/WORKER),'workerRaw':b64(new_worker),
            'workerSha256':n.digest(new_worker),
            'validator':str(package/VALIDATOR),'validatorRaw':b64(validator.read_bytes()),
            'validatorSha256':n.digest(validator.read_bytes()),
            'approvedGuiSha256':ui_hash,'gui':str(gui),
            'tradeScriptSha256':trade_hash,'tradeScript':str(trade),
            'engineUpdates':updates}


def materialize_immutable(path,raw):
    path=Path(path)
    n.safe(path.parent,True)
    if path.exists() or path.is_symlink():
        need(n.safe(path).read_bytes()==raw,'PACKAGE_CONFLICT')
        return
    temp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,
                prefix='.friday-source-',delete=False) as stream:
            temp=Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp,path)
        except FileExistsError:
            need(n.safe(path).read_bytes()==raw,'PACKAGE_RACE')
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def atomic_replace(path,raw,new):
    p=n.safe(path)
    need(p.read_bytes()==raw,'CONCURRENT_SOURCE_EDIT')
    temp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=p.parent,
                prefix='.friday-upgrade-',delete=False) as stream:
            temp=Path(stream.name)
            stream.write(new)
            stream.flush()
            os.fsync(stream.fileno())
        need(p.read_bytes()==raw,'CONCURRENT_SOURCE_EDIT')
        os.replace(temp,p)
        temp=None
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def quiet():
    live_probe.no_workers()
    script=r"""$ErrorActionPreference='Stop'
try{
 $ps=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object{
 $_.ProcessId -ne $PID -and
 $_.Name -match '^(?:powershell|pwsh)(?:[.]exe)?$' -and
 [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11PreopenStandby[.]ps1'
 })
 if($ps.Count){exit 3};exit 0
}catch{exit 4}"""
    with tempfile.TemporaryDirectory(prefix='ark-friday-ui-query-') as t:
        file=Path(t)/'readonly-cim.ps1'
        file.write_text(script,encoding='utf-8')
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive',
                '-ExecutionPolicy','Bypass','-File',str(file)],
                capture_output=True,timeout=35,check=False)
    need(r.returncode!=3,'CLOSE_ONECLICK_FIRST')
    need(r.returncode==0,'UI_PROCESS_QUERY_FAILED')


def checked(j):
    need(j.get('kind')==KIND and j.get('orderTransmission') is False
         and j.get('phase') in ('PREPARED','COMPLETE'),'JOURNAL_CONTRACT')
    before=un64(j['bindingBefore'])
    after=un64(j['bindingAfter'])
    need(n.digest(before)==j['bindingBeforeSha256']
         and n.digest(after)==j['bindingAfterSha256'],
         'BINDING_JOURNAL_CHECKSUM')
    b1=json.loads(before.decode('utf-8-sig'))
    b2=json.loads(after.decode('utf-8-sig'))
    harmless_signature(b1,b2)
    for kind,entry in j['engineUpdates'].items():
        need(kind in ENGINE,'JOURNAL_ENGINE_KEY')
        pre=un64(entry['before'])
        post=un64(entry['after'])
        need(n.digest(pre)==entry['beforeSha256'] and
             n.digest(post)==entry['afterSha256'] and
             patch.MARK.encode() in post,
             'ENGINE_JOURNAL_CHECKSUM')
        real=n.safe(entry['path']).read_bytes()
        need(real in (pre,post),'LOCAL_ENGINE_EDIT')
    need(n.digest(un64(j['workerRaw']))==j['workerSha256']
         and n.digest(un64(j['validatorRaw']))==j['validatorSha256'],
         'PACKAGE_JOURNAL_CHECKSUM')
    need(n.digest(n.safe(j['gui']).read_bytes())==j['approvedGuiSha256']
         and n.digest(n.safe(j['tradeScript']).read_bytes())==j['tradeScriptSha256'],
         'GUI_OR_TRADE_CHANGED')
    bind=n.safe(j['bindingFile']).read_bytes()
    need(bind in (before,after),'LOCAL_BINDING_EDIT')
    return before,after


def apply_stage(j):
    before,after=checked(j)
    package=Path(j['worker']).parent
    package.mkdir(exist_ok=True)
    n.safe(package,True)
    materialize_immutable(j['worker'],un64(j['workerRaw']))
    materialize_immutable(j['validator'],un64(j['validatorRaw']))
    for kind in ENGINE:
        entry=j['engineUpdates'][kind]
        path=Path(entry['path'])
        old=un64(entry['before'])
        new=un64(entry['after'])
        if path.read_bytes()==new:
            continue
        atomic_replace(path,old,new)
        print('NO11_REAL_FRIDAY_ENGINE_PATCH='+kind.upper()+'|PASS',flush=True)
    bind=Path(j['bindingFile'])
    if bind.read_bytes()!=after:
        atomic_replace(bind,before,after)
    checked(j)
    need(bind.read_bytes()==after
         and n.digest(n.safe(j['worker']).read_bytes())==j['workerSha256']
         and n.digest(n.safe(j['validator']).read_bytes())==j['validatorSha256'],
         'POSTCOMMIT_VERIFICATION')


def install(store,apply=False,test=False):
    store=n.safe(store,True)
    journal=store/JOURNAL
    with n.exclusive(store/'unified-refresh-install.lock'):
        if journal.exists():
            j=n.checkpoint(journal)
            before,after=checked(j)
            if j['phase']=='COMPLETE':
                need(n.safe(j['bindingFile']).read_bytes()==after,
                     'COMPLETED_BINDING_CHANGED')
                return 'ALREADY_APPLIED'
            need(apply,'INCOMPLETE_INSTALL_REQUIRES_APPLY')
        else:
            j=plan(store)
            if not apply:
                print('NO11_REAL_FRIDAY_RECOVERY_PREFLIGHT=PASS',flush=True)
                return 'READY'
        if not test:
            quiet()
        if not journal.exists():
            n.atomic(journal,j)
        apply_stage(j)
        j['phase']='COMPLETE'
        n.atomic(journal,j)
        return 'PASS'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store',type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    a=p.parse_args()
    try:
        need(os.name=='nt','WINDOWS_ONLY')
        print('NO11_REAL_FRIDAY_INSTALL='+install(a.store,a.apply))
        print('FRIDAY_FULL_MARKET=REAL_RSS_ONLY')
        print('FRIDAY_SOURCE_CLOCK=ACTUAL_JST_OBSERVATION')
        print('WEEKDAY_MAX47_PRESERVED=True')
        print('WHITE_GUI_CHANGED=False')
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')
    except Exception as exc:
        value=str(exc)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+',value):
            value='NO11_REAL_FRIDAY_INSTALL_SOURCE_OR_RUNTIME'
        print('NO11_REAL_FRIDAY_INSTALL=BLOCKED|'+value)
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')
        raise SystemExit(2)


if __name__=='__main__':main()
