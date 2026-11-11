#!/usr/bin/env python3
"""One-file DATA calendar-path hotfix with a fresh immutable worker namespace.

The most recent Friday recovery code wrote a Python triple-quoted PowerShell
string with tools\no11_..., silently interpreting backslash+n as a newline.
The parent weekly mode used a raw string and worked; the child did not.
Fix only that broken string and move the worker's DATA checkpoint namespace,
leaving the old failed checkpoint and all receipts intact. No trading,
Excel, RSS, selector, or workbook actions in this installer.
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
import no11_nightly_resume_workeraware as runtime

MARK='ARK_NO11_REAL_FRIDAY_CALENDAR_PATHFIX_V2'
KIND='ARK_NO11_FRIDAY_CHILD_CALENDAR_PATHFIX_V2'
JOURNAL='friday-child-calendar-pathfix-v2-journal.json'
BROKEN="$calendarTool=Join-Path $base 'tools\no11_rss_daily_trend_census.mjs'"
CORRECT="$calendarTool=Join-Path $base 'tools\\no11_rss_daily_trend_census.mjs'"
OLD_NAMESPACE="'-real-friday-v1'"
NEW_NAMESPACE="'-real-friday-v1-pathfix-v2'"


def need(value,reason):
    if not value:
        raise ValueError('NO11_FRIDAY_CHILD_PATHFIX_'+reason)


def b64(data):
    return base64.b64encode(data).decode('ascii')


def un64(data):
    return base64.b64decode(data,validate=True)


def patch_next(raw):
    bom=raw.startswith(b'\xef\xbb\xbf')
    src=raw.decode('utf-8-sig')
    crlf='\r\n' in src
    text=src.replace('\r\n','\n')
    need('\r' not in text,'SOURCE_LINE_ENDINGS')
    need(text.count("ARK_NO11_MISSING_PREVIOUS_FRIDAY_REAL_RSS_RECOVERY_V1") == 1
         and 'ARK_NO11_LATEST_COMPLETED_SESSION_DATA_V1' in text
         and 'ARK_NO11_NEXT_SESSION_MAX47_V1' in text
         and text.count(BROKEN)==1 and CORRECT not in text,
         'EXACT_CHILD_PATH_BUG_NOT_PRESENT')
    # Preserve every other character, including the approved 47 chart cap.
    amended=text.replace(BROKEN,CORRECT,1)
    need(amended.count(CORRECT)==1 and BROKEN not in amended,
         'PATHFIX_NOT_ISOLATED')
    candidate=(b'\xef\xbb\xbf' if bom else b'')+(
        amended.replace('\n','\r\n' if crlf else '\n').encode('utf-8'))
    need(n.digest(raw)!=n.digest(candidate),'NO_CHANGE')
    return candidate


def patch_worker(raw):
    text=raw.decode('utf-8-sig')
    normalized=text.replace('\r\n','\n')
    anchor=("    work = root / 'resumable-nightly' / "
            "(asof + '_' + target + "+OLD_NAMESPACE+")")
    replacement=("    # ARK_NO11_REAL_FRIDAY_CALENDAR_PATHFIX_V2: retain old failed\n"
                 "    # work journal and partial receipts, never erase/mutate them.\n"
                 "    work = root / 'resumable-nightly' / "
                 "(asof + '_' + target + "+NEW_NAMESPACE+")")
    need(normalized.count(anchor)==1 and MARK not in normalized
         and 'ARK_NO11_CIRCUIT_AUDIT_V1' in normalized
         and 'ARK_NO11_NIGHTLY_RESUME_WORKER_PROBE_V2' in normalized
         and 'ARK_NO11_MISSING_PREVIOUS_FRIDAY_REAL_RSS_RECOVERY_V1' in normalized,
         'BOUND_WORKER_SOURCE_NOT_EXPECTED')
    changed=normalized.replace(anchor,replacement,1)
    compile(changed,'read-only-friday-worker.py','exec')
    return (b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+(
       changed.replace('\n','\r\n' if '\r\n' in text else '\n').encode('utf-8'))


def immutable(p,raw):
    p=Path(p)
    n.safe(p.parent,True)
    if p.exists() or p.is_symlink():
        need(n.safe(p).read_bytes()==raw,'IMMUTABLE_PACKAGE_CHANGED')
        return
    tmp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=p.parent,
                 prefix='.friday-pathfix-',delete=False) as f:
            tmp=Path(f.name);f.write(raw);f.flush();os.fsync(f.fileno())
        try:
            os.link(tmp,p)
        except FileExistsError:
            need(n.safe(p).read_bytes()==raw,'PACKAGE_RACE')
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)


def switch(p,before,after):
    p=n.safe(p)
    need(p.read_bytes()==before,'SOURCE_EDIT_WHILE_APPLYING')
    tmp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=p.parent,
                 prefix='.friday-pathfix-',delete=False) as f:
            tmp=Path(f.name);f.write(after);f.flush();os.fsync(f.fileno())
        need(p.read_bytes()==before,'SOURCE_EDIT_WHILE_APPLYING')
        os.replace(tmp,p)
        tmp=None
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)


def close_check():
    # Block ANY old real data/Trade/Chart worker, never stop it. Actual current
    # Python probe ancestry may include the installer shell, excluded by V2.
    runtime.no_workers()
    script=r"""$ErrorActionPreference='Stop'
try {
 $rows=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
 $_.ProcessId -ne $PID -and
 $_.Name -match '^(?:powershell|pwsh)(?:[.]exe)?$' -and
 [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11PreopenStandby[.]ps1'
 })
 if($rows.Count){exit 3};exit 0
} catch {exit 4}"""
    with tempfile.TemporaryDirectory(prefix='ark-friday-path-cim-') as t:
        ps=Path(t)/'safe-ps-cim.ps1'
        ps.write_text(script,encoding='utf-8')
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive',
             '-ExecutionPolicy','Bypass','-File',str(ps)],
             capture_output=True,timeout=35,check=False)
    need(r.returncode!=3,'CLOSE_ONECLICK_FIRST')
    need(r.returncode==0,'CIM_QUERY_FAILED')


def preflight(store):
    bfile=n.safe(store/'automatic-inputs.json')
    b=n.read(bfile)
    need(b.get('schemaId')=='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
         and b.get('orderTransmission') is False
         and b.get('manualPriceInputRequired') is False
         and b.get('manualEvidenceRequired') is False,
         'BINDING_CONTRACT')
    settings=n.read(n.safe(store/'settings.json'))
    need(settings.get('schemaId')=='ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1'
         and settings.get('normalMaxPositions')==3
         and settings.get('sameDayApprovalRequired') is True
         and settings.get('automaticOrderAuthorization') is False
         and settings.get('orderTransmission') is False,
         'ORDER_APPROVAL_SETTINGS')
    engine=n.safe(b['engine'],True)
    nextfile=n.safe(engine/'windows/Prepare-No11NextSessionNightlyReadOnly.ps1')
    raw=nextfile.read_bytes()
    amended=patch_next(raw)
    worker=n.safe(b['nightlyResumeTool'])
    old_worker=worker.read_bytes()
    # The previous successfully installed recovery has a sha-attested journal
    # of every locally modified engine file. Reject any intervening edits.
    prior_file=n.safe(store/'missing-friday-real-rss-transaction.json')
    prior=n.checkpoint(prior_file)
    need(prior.get('kind')=='ARK_NO11_MISSING_FRIDAY_REAL_RSS_RECOVERY_RELEASE_V1'
         and prior.get('phase')=='COMPLETE' and
         prior.get('orderTransmission') is False,
         'PRIOR_RELEASE_NOT_ATTESTED')
    expected={'dailyTool':'tools/no11_rss_daily_trend_census.mjs',
              'dailyCollector':'windows/Run-No11RssDailyTrendCensusReadOnly.ps1',
              'next':'windows/Prepare-No11NextSessionNightlyReadOnly.ps1',
              'weekly':'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1'}
    for key,rel in expected.items():
        source=n.safe(engine/rel)
        row=prior.get('engineUpdates',{}).get(key,{})
        need(row.get('path')==str(source)
             and row.get('afterSha256')==n.digest(source.read_bytes()),
             'ENGINE_CHANGED_SINCE_SIGNED_FRIDAY_INSTALL')
    need(prior.get('workerSha256')==n.digest(old_worker),
         'WORKER_CHANGED_SINCE_SIGNED_FRIDAY_INSTALL')
    need(n.digest(old_worker)==b.get('nightlyResumeToolSha256'),
         'BOUND_WORKER_DIGEST')
    validator=n.safe(worker.with_name('no11_selection_status.py'))
    need(n.digest(validator.read_bytes())==b.get('nightlyResumeValidatorSha256'),
         'BOUND_VALIDATOR_DIGEST')
    newer=patch_worker(old_worker)
    package=store/('friday-calendar-pathfix-v2-'+n.digest(newer)[:20])
    target=package/'no11_nightly_resume_workeraware.py'
    validator_target=package/'no11_selection_status.py'
    after=dict(b,nightlyResumeTool=str(target),
               nightlyResumeToolSha256=n.digest(newer))
    need(all(after.get(k)==v for k,v in b.items()
             if k not in ('nightlyResumeTool','nightlyResumeToolSha256')),
         'UNRELATED_BINDING_EDIT')
    binding_before=bfile.read_bytes()
    binding_after=n.encode(after)
    ui=n.safe(store/'oneclick/Start-No11OneClick.ps1')
    trade=n.safe(engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1')
    return {
      'schemaId':n.SCHEMA,'kind':KIND,'phase':'PREPARED',
      'orderTransmission':False,
      'bindingFile':str(bfile),'bindingBefore':b64(binding_before),
      'bindingAfter':b64(binding_after),
      'bindingBeforeSha256':n.digest(binding_before),
      'bindingAfterSha256':n.digest(binding_after),
      'nextFile':str(nextfile),'nextBefore':b64(raw),
      'nextAfter':b64(amended),
      'nextBeforeSha256':n.digest(raw),
      'nextAfterSha256':n.digest(amended),
      'workerNewFile':str(target),'workerNewBytes':b64(newer),
      'workerNewSha256':n.digest(newer),
      'validatorFile':str(validator_target),
      'validatorBytes':b64(validator.read_bytes()),
      'validatorSha256':n.digest(validator.read_bytes()),
      'uiFile':str(ui),'uiSha256':n.digest(ui.read_bytes()),
      'tradeFile':str(trade),'tradeSha256':n.digest(trade.read_bytes())
    }


def verify(j):
    need(j.get('kind')==KIND and j.get('orderTransmission') is False and
         j.get('phase') in ('PREPARED','COMPLETE'),
         'JOURNAL_CONTRACT')
    for stem in ('binding','next'):
        first=un64(j[stem+'Before'])
        latter=un64(j[stem+'After'])
        need(n.digest(first)==j[stem+'BeforeSha256'] and
             n.digest(latter)==j[stem+'AfterSha256'],
             'JOURNAL_DIGEST_'+stem.upper())
        disk=n.safe(j[stem+'File']).read_bytes()
        need(disk in (first,latter),'EXTERNAL_LOCAL_EDIT_'+stem.upper())
    need(n.digest(un64(j['workerNewBytes']))==j['workerNewSha256']
         and n.digest(un64(j['validatorBytes']))==j['validatorSha256'],
         'NEW_PACKAGE_JOURNAL_HASH')
    need(n.digest(n.safe(j['uiFile']).read_bytes())==j['uiSha256'] and
         n.digest(n.safe(j['tradeFile']).read_bytes())==j['tradeSha256'],
         'WHITE_GUI_OR_TRADE_CHANGED')
    prior=json.loads(un64(j['bindingBefore']).decode('utf-8-sig'))
    latter=json.loads(un64(j['bindingAfter']).decode('utf-8-sig'))
    need(all(latter.get(k)==v for k,v in prior.items()
             if k not in ('nightlyResumeTool','nightlyResumeToolSha256'))
         and latter.get('orderTransmission') is False,
         'SCOPE_ESCALATION')
    return prior,latter


def apply(j):
    verify(j)
    pkg=Path(j['workerNewFile']).parent
    pkg.mkdir(exist_ok=True)
    n.safe(pkg,True)
    immutable(j['workerNewFile'],un64(j['workerNewBytes']))
    immutable(j['validatorFile'],un64(j['validatorBytes']))
    nfile=Path(j['nextFile'])
    bfile=Path(j['bindingFile'])
    if nfile.read_bytes()!=un64(j['nextAfter']):
        switch(nfile,un64(j['nextBefore']),un64(j['nextAfter']))
        print('NO11_FRIDAY_CHILD_CALENDAR_PATH=FIXED_ONE_LINE',flush=True)
    if bfile.read_bytes()!=un64(j['bindingAfter']):
        switch(bfile,un64(j['bindingBefore']),un64(j['bindingAfter']))
        print('NO11_FRIDAY_WORKER_CHECKPOINT_NAMESPACE=V2_PRESERVED_OLD',flush=True)
    verify(j)
    need(n.safe(j['workerNewFile']).read_bytes()==un64(j['workerNewBytes'])
         and n.safe(j['validatorFile']).read_bytes()==un64(j['validatorBytes'])
         and nfile.read_bytes()==un64(j['nextAfter'])
         and bfile.read_bytes()==un64(j['bindingAfter']),
         'COMMIT_READBACK')


def install(store,do_apply=False,test=False):
    store=n.safe(store,True)
    with n.exclusive(store/'unified-refresh-install.lock'):
        path=store/JOURNAL
        if path.exists():
            j=n.checkpoint(path)
            verify(j)
            if j['phase']=='COMPLETE':
                need(n.safe(j['bindingFile']).read_bytes()==un64(j['bindingAfter'])
                     and n.safe(j['nextFile']).read_bytes()==un64(j['nextAfter']),
                     'COMPLETE_FILES_CHANGED')
                return 'ALREADY_APPLIED'
            need(do_apply,'PREPARED_JOURNAL_REQUIRES_APPLY')
        else:
            j=preflight(store)
            if not do_apply:
                print('NO11_FRIDAY_CHILD_PATHFIX_PREFLIGHT=READY',flush=True)
                return 'READY'
        if not test:
            close_check()
        if not path.exists():n.atomic(path,j)
        apply(j)
        j['phase']='COMPLETE'
        n.atomic(path,j)
        return 'PASS'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store',required=True,type=Path)
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    try:
        need(os.name=='nt','WINDOWS_ONLY')
        result=install(args.store,args.apply)
        print('NO11_FRIDAY_CHILD_PATHFIX_INSTALL='+result)
        print('OLD_CAPTURES_AND_CHECKPOINTS_PRESERVED=True')
        print('WEEKLY_DAILY_MAX47_UNCHANGED=True')
        print('WHITE_GUI_CHANGED=False')
        print('FROZEN_TRADE_AND_EXIT_CHANGED=False')
    except Exception as exc:
        reason=str(exc)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+',reason):
            reason='NO11_FRIDAY_CHILD_PATHFIX_UNKNOWN_RUNTIME'
        print('NO11_FRIDAY_CHILD_PATHFIX_INSTALL=BLOCKED|'+reason)
        raise SystemExit(2)
    finally:
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')

if __name__=='__main__':main()
