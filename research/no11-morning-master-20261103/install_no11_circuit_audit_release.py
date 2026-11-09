#!/usr/bin/env python3
"""Install the integrated circuit repair in ONE versioned package.

No Excel calls, data collection, order sending, trading approval or UI layout
changes. All old bound files remain available. The four new package files are
published before the sole binding pointer is atomically switched. Re-running
a completed or interrupted installation is supported without marker deletion.
"""
from __future__ import annotations
import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import no11_nightly_resume as n
import no11_nightly_resume_workeraware as worker
import no11_circuit_repair as repair

KIND='ARK_NO11_INTEGRATED_CIRCUIT_RELEASE_V1'
JOURNAL='integrated-circuit-release-transaction.json'
FIELDS={'bridge':'launcher_automatic_bridge_v4.py',
        'dailyCycleTool':'daily_cycle.py',
        'nightlyResumeTool':'no11_nightly_resume_workeraware.py'}


def need(ok,code):
    if not ok:raise ValueError('NO11_CIRCUIT_INSTALL_'+code)


def normalized(raw):
    return raw.decode('utf-8-sig').replace('\r\n','\n')


def immutable(path,raw):
    n.safe(path.parent,True)
    if path.exists() or path.is_symlink():
        need(n.safe(path).read_bytes()==raw,'PACKAGE_CONFLICT');return
    tmp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,delete=False) as out:
            tmp=Path(out.name);out.write(raw);out.flush();os.fsync(out.fileno())
        try:os.link(tmp,path)
        except FileExistsError:need(n.safe(path).read_bytes()==raw,'PACKAGE_RACE')
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)


def replace(path,before,after):
    need(n.safe(path).read_bytes()==before,'CONCURRENT_EDIT')
    tmp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,delete=False) as out:
            tmp=Path(out.name);out.write(after);out.flush();os.fsync(out.fileno())
        need(path.read_bytes()==before,'CONCURRENT_EDIT')
        os.replace(tmp,path);tmp=None
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)


def quiet():
    worker.no_workers()
    # This file is used only for installation; no permanent run-time gate added.
    cmd="""$ErrorActionPreference='Stop';try{
 $rows=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object{
 $_.ProcessId -ne $PID -and $_.Name -match '^(?:powershell|pwsh)(?:[.]exe)?$' -and
 [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11PreopenStandby[.]ps1'
 });if($rows.Count){exit 3};exit 0}catch{exit 4}
"""
    with tempfile.TemporaryDirectory(prefix='no11-install-state-') as tmp:
        path=Path(tmp)/'probe.ps1';path.write_text(cmd,encoding='utf-8')
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(path)],capture_output=True,timeout=35,check=False)
    need(r.returncode!=3,'CLOSE_ONECLICK_BEFORE_INSTALL')
    need(r.returncode==0,'PROCESS_QUERY_FAILED')


def plan(store,source):
    binding=n.safe(store/'automatic-inputs.json');raw=binding.read_bytes();b=n.read(binding)
    need(b.get('schemaId')=='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' and b.get('orderTransmission') is False,'BINDING_CONTRACT')
    settings=n.read(n.safe(store/'settings.json'))
    need(settings.get('normalMaxPositions')==3 and settings.get('sameDayApprovalRequired') is True
         and settings.get('automaticOrderAuthorization') is False and settings.get('orderTransmission') is False,'SETTINGS_CONTRACT')
    ui=n.safe(store/'oneclick/Start-No11OneClick.ps1')
    installed={}
    for field in FIELDS:
        path=n.safe(b[field]);content=path.read_bytes()
        need(n.digest(content)==b.get(field+'Sha256'),'BOUND_'+field.upper()+'_CHANGED')
        installed[field]=content
    validator=n.safe(Path(b['nightlyResumeTool']).with_name('no11_selection_status.py'))
    need(n.digest(validator.read_bytes())==b.get('nightlyResumeValidatorSha256'),'VALIDATOR_CHANGED')
    original=n.safe(source/'no11_nightly_resume.py').read_bytes()
    workeraware=n.safe(source/'no11_nightly_resume_workeraware.py').read_bytes()
    current=installed['nightlyResumeTool']
    need(normalized(current) in (normalized(original),normalized(workeraware)), 'UNKNOWN_BOUND_WORKER_VERSION')
    payload={FIELDS['bridge']:repair.transform('bridge',installed['bridge']),
             FIELDS['dailyCycleTool']:repair.transform('cycle',installed['dailyCycleTool']),
             FIELDS['nightlyResumeTool']:repair.transform('worker',workeraware),
             'no11_selection_status.py':validator.read_bytes()}
    for name,content in payload.items():compile(content.decode('utf-8-sig'),name,'exec')
    package_hash=n.digest(n.encode({name:n.digest(data) for name,data in payload.items()}))
    package=store/('circuit-release-'+package_hash[:20])
    updated=dict(b)
    for field,name in FIELDS.items():
        updated[field]=str(package/name)
        updated[field+'Sha256']=n.digest(payload[name])
    after=n.encode(updated)
    permitted=set(FIELDS)|{k+'Sha256' for k in FIELDS}
    need(all(updated.get(k)==v for k,v in b.items() if k not in permitted),'UNRELATED_BINDING_CHANGED')
    return binding,raw,after,ui,package,payload


def resume(store,journal,apply,test):
    j=n.checkpoint(journal)
    need(j.get('kind')==KIND and j.get('phase') in ('PREPARED','COMPLETE'),'JOURNAL_CONTRACT')
    binding=n.safe(store/'automatic-inputs.json');ui=n.safe(store/'oneclick/Start-No11OneClick.ps1')
    before=base64.b64decode(j['before'],validate=True);after=base64.b64decode(j['after'],validate=True)
    need(n.digest(before)==j['beforeSha256'] and n.digest(after)==j['afterSha256'],'JOURNAL_HASH')
    need(binding.read_bytes() in (before,after) and n.digest(ui.read_bytes())==j['uiSha256'],'UNEXPECTED_LOCAL_EDIT')
    updated=json.loads(after.decode('utf-8-sig'))
    for field in FIELDS:
        need(n.digest(n.safe(updated[field]).read_bytes())==updated[field+'Sha256'],'PACKAGE_CHANGED')
    validator=n.safe(Path(updated['nightlyResumeTool']).with_name('no11_selection_status.py'))
    need(n.digest(validator.read_bytes())==updated['nightlyResumeValidatorSha256'],'VALIDATOR_CHANGED')
    if j['phase']=='COMPLETE':
        need(binding.read_bytes()==after,'COMPLETED_BINDING_REVERTED');return 'ALREADY_APPLIED'
    need(apply,'INTERRUPTED_APPLY_REQUIRED')
    if not test:quiet()
    if binding.read_bytes()==before:replace(binding,before,after)
    j['phase']='COMPLETE';n.atomic(journal,j)
    return 'PASS'


def install(store,source,apply=False,test=False):
    store=n.safe(store,True);source=n.safe(source,True)
    with n.exclusive(store/'unified-refresh-install.lock'):
        journal=store/JOURNAL
        if journal.exists():return resume(store,journal,apply,test)
        binding,before,after,ui,package,payload=plan(store,source)
        print('NO11_CIRCUIT_SOURCE_AUDIT=READY',flush=True)
        if not apply:return 'READY'
        if not test:quiet()
        ui_sha=n.digest(ui.read_bytes())
        package.mkdir(exist_ok=True);n.safe(package,True)
        for name,raw in payload.items():immutable(package/name,raw)
        need(binding.read_bytes()==before and n.digest(ui.read_bytes())==ui_sha,'PRECOMMIT_CHANGED')
        j={'schemaId':n.SCHEMA,'kind':KIND,'phase':'PREPARED','orderTransmission':False,
           'before':base64.b64encode(before).decode('ascii'),'after':base64.b64encode(after).decode('ascii'),
           'beforeSha256':n.digest(before),'afterSha256':n.digest(after),'uiSha256':ui_sha}
        n.atomic(journal,j)
        replace(binding,before,after)
        need(binding.read_bytes()==after and n.digest(ui.read_bytes())==ui_sha,'POSTCOMMIT_CHANGED')
        j['phase']='COMPLETE';n.atomic(journal,j)
        return 'PASS'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store',type=Path,required=True);p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--apply',action='store_true');a=p.parse_args()
    try:
        need(os.name=='nt','WINDOWS_REQUIRED')
        print('NO11_INTEGRATED_CIRCUIT_INSTALL='+install(a.store,a.source_dir,a.apply))
        print('WEEKLY_DAILY_MAX47_UNCHANGED=True\nWHITE_GUI_CHANGED=False\nFROZEN_TRADING_RULES_CHANGED=False')
    except Exception as e:
        reason=str(e)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+',reason):reason='NO11_CIRCUIT_INSTALL_LOCAL_RUNTIME'
        print('NO11_INTEGRATED_CIRCUIT_INSTALL=BLOCKED|'+reason)
        raise SystemExit(2)
    finally:print('TRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')

if __name__=='__main__':main()
