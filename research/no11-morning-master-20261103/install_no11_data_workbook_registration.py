#!/usr/bin/env python3
"""Register the three saved, open DATA workbooks without renaming or saving them.

Read-only Excel discovery uses the user's existing EXCEL7 process, not a new
Excel instance. All data collectors share a hash-pinned role/path registry.
Live settings, historical handoffs, trading approval, UI and order ledgers are
NOT rebound. Original files and failed attempts remain byte-for-byte saved.
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
import no11_nightly_resume_workeraware as probe
import nightly_workbook_compat as legacy

MARK='ARK_NO11_REGISTERED_DATA_WORKBOOKS_V1'
KIND='ARK_NO11_DATA_BOOK_REGISTRATION_INSTALL_V1'
JOURNAL='data-workbook-registration-v1-transaction.json'
HELPER='No11DataWorkbookRegistry.ps1'
REGISTRY='data-workbooks.json'
WORKER='no11_nightly_resume_workeraware.py'
VALIDATOR='no11_selection_status.py'
ROLES={'Account':'ARK_ACCOUNT_READONLY','Market':'ARK_MARKET_READONLY','OrderIds':'ARK_ORDER_IDS_READONLY'}
STEMS=('Run-No11RssDailyTrendCensusReadOnly','Run-No11WeeklyCandidateRefreshReadOnly','Capture-No11RssTrainingBatchReadOnly')
STARTUP=r'''  # ARK_NO11_REGISTERED_DATA_WORKBOOKS_V1
  # Exact registered paths, not .xlsx filenames; no workbook changes.
  $dataBindingFile=Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\unified-launcher\automatic-inputs.json'
  $dataBinding=Get-Content -LiteralPath $dataBindingFile -Raw -Encoding UTF8|ConvertFrom-Json
  if($dataBinding.schemaId -cne 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' -or $dataBinding.orderTransmission -ne $false){throw 'NO11_DATA_BOOK_BINDING_INVALID'}
  $dataHelper=[string]$dataBinding.dataWorkbookResolver
  if(-not [IO.Path]::IsPathRooted($dataHelper) -or -not (Test-Path -LiteralPath $dataHelper -PathType Leaf)){throw 'NO11_DATA_BOOK_RESOLVER_MISSING'}
  if((Get-FileHash -LiteralPath $dataHelper -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$dataBinding.dataWorkbookResolverSha256){throw 'NO11_DATA_BOOK_RESOLVER_HASH'}
  . $dataHelper
  $nightlyDataBooks=Get-No11RegisteredDataBooks $excel
  $script:No11DataOriginalBookCount=$nightlyDataBooks.OriginalCount
  Write-Host 'NO11_DATA_WORKBOOK_REGISTRY=EXACT_THREE_PATHS_AND_SHEETS_MATCHED'
'''


def need(ok,why):
    if not ok:raise ValueError('NO11_DATA_BOOK_INSTALL_'+why)


def b64(raw):return base64.b64encode(raw).decode('ascii')
def un64(raw):return base64.b64decode(raw,validate=True)


def transform_collector(raw):
    bom=raw.startswith(b'\xef\xbb\xbf');source=raw.decode('utf-8-sig')
    newline='\r\n' if '\r\n' in source else '\n'
    text=source.replace('\r\n','\n')
    need('\r' not in text,'UNRECOGNIZED_EOL')
    if MARK in text:return raw
    need(text.count(legacy.CHECK)==1,'THREE_BOOK_BLOCK_NOT_RECOGNIZED')
    anchor="$account=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx');$market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')"
    need(text.count(anchor)==1,'ACCOUNT_MARKET_LOOKUP_NOT_RECOGNIZED')
    loop='foreach($wb in @($account,$market))'
    need(text.count(loop)==1,'CAPACITY_SCAN_NOT_RECOGNIZED')
    text=text.replace(legacy.CHECK,STARTUP.rstrip(),1)
    text=text.replace(anchor,'$account=$nightlyDataBooks.Account;$market=$nightlyDataBooks.Market',1)
    # Count formulas in ALL three originals, not just two. Maximum configured
    # batch stays 47 minus occupied chart slots; no unnecessary 5-call ramp.
    text=text.replace(loop,'foreach($wb in $nightlyDataBooks.Originals)',1)
    if 'function Close-ExcelTemporaryWorkbook' in text:
        a='if($count -eq 2){return}';b="if($count -ne 3){throw 'NO11_DAILY_EXCEL_CLOSE_OUTCOME_AMBIGUOUS'}"
        need(text.count(a)==1 and text.count(b)==1,'TEMP_CLOSE_BASELINE_NOT_RECOGNIZED')
        text=text.replace(a,'if($count -eq $script:No11DataOriginalBookCount){return}',1)
        text=text.replace(b,"if($count -ne ($script:No11DataOriginalBookCount+1)){throw 'NO11_DAILY_EXCEL_CLOSE_OUTCOME_AMBIGUOUS'}",1)
    need('47' in text and 'ORDER_TRANSMISSION=False' in text,'MAXIMUM_OR_DATA_MODE_MISSING')
    return (b'\xef\xbb\xbf' if bom else b'')+text.replace('\n',newline).encode('utf-8')


def transform_worker(raw,registration_hash):
    source=raw.decode('utf-8-sig');text=source.replace('\r\n','\n')
    needle="'-real-friday-v1-pathfix-v2'"
    need(text.count(needle)==1 and 'ARK_NO11_CIRCUIT_AUDIT_V1' in text and 'DataUpdate-' in text,'WORKER_VERSION_NOT_RECOGNIZED')
    text=text.replace(needle,"'-data-books-v1-"+registration_hash[:16]+"'",1)
    compile(text,WORKER,'exec')
    return (b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.replace('\n','\r\n' if '\r\n' in source else '\n').encode('utf-8')


def validate_registration(record):
    need(type(record) is dict and record.get('schemaId')=='ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1'
         and record.get('orderTransmission') is False,'REGISTRY_CONTRACT')
    books=record.get('books');need(type(books) is list and len(books)==3,'THREE_BOOKS_REQUIRED')
    seen=set();paths=set()
    for row in books:
        role=row.get('role');need(role in ROLES and role not in seen,'BOOK_ROLE_NOT_UNIQUE')
        need(row.get('sheet')==ROLES[role] and row.get('date1904') is False,'SHEET_OR_DATE_MODE')
        path=n.safe(row['path']);need(path.name==row.get('name') and path.suffix.lower() in ('.xlsx','.xlsb','.xlsm'),'BOOK_FILE_FORMAT')
        key=str(path).casefold();need(key not in paths,'BOOK_PATH_NOT_UNIQUE')
        seen.add(role);paths.add(key)
    return record


def discover(helper):
    with tempfile.TemporaryDirectory(prefix='ark-data-books-readonly-') as directory:
        output=Path(directory)/'observed-books.json'
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
           '-File',str(helper),'-Discover','-OutputFile',str(output)],capture_output=True,text=True,
           encoding='utf-8',errors='replace',timeout=45)
        need(result.returncode==0 and output.is_file(),'READ_ONLY_EXCEL_DISCOVERY_FAILED')
        record=validate_registration(n.read(output))
        for row in record['books']:print('NO11_DATA_BOOK_DISCOVERED='+row['role']+'|'+row['name'],flush=True)
        return record


def quiet():
    probe.no_workers()
    code=r"""$ErrorActionPreference='Stop';try{
 $rows=@(Get-CimInstance Win32_Process -ErrorAction Stop|Where-Object{
 $_.ProcessId -ne $PID -and $_.Name -match '^(powershell|pwsh)([.]exe)?$' -and
 [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11PreopenStandby[.]ps1'
 });if($rows.Count){exit 3};exit 0}catch{exit 4}"""
    with tempfile.TemporaryDirectory(prefix='ark-data-books-ui-') as d:
        path=Path(d)/'probe.ps1';path.write_text(code,encoding='utf-8')
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(path)],capture_output=True,timeout=35)
    need(result.returncode!=3,'CLOSE_ONECLICK_FIRST')
    need(result.returncode==0,'PROCESS_QUERY_FAILED')


def immutable(path,raw):
    n.safe(path.parent,True)
    if path.exists() or path.is_symlink():need(n.safe(path).read_bytes()==raw,'PACKAGE_CONFLICT');return
    tmp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,delete=False) as out:
            tmp=Path(out.name);out.write(raw);out.flush();os.fsync(out.fileno())
        try:os.link(tmp,path)
        except FileExistsError:need(n.safe(path).read_bytes()==raw,'PACKAGE_RACE')
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)


def replace(path,before,after):
    need(n.safe(path).read_bytes()==before,'CONCURRENT_LOCAL_EDIT')
    tmp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,delete=False) as out:
            tmp=Path(out.name);out.write(after);out.flush();os.fsync(out.fileno())
        need(path.read_bytes()==before,'CONCURRENT_LOCAL_EDIT');os.replace(tmp,path);tmp=None
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)


def parse_candidates(rows):
    with tempfile.TemporaryDirectory(prefix='ark-data-books-parse-') as directory:
        folder=Path(directory);paths=[]
        for index,raw in enumerate(rows):
            p=folder/(str(index)+'.ps1');p.write_bytes(raw);paths.append(p)
        harness=folder/'parse-all.ps1'
        harness.write_text("param([string]$Folder)\n$ErrorActionPreference='Stop'\nforeach($p in @(Get-ChildItem -LiteralPath $Folder -Filter '*.ps1')){$t=$null;$e=$null;[void][Management.Automation.Language.Parser]::ParseFile($p.FullName,[ref]$t,[ref]$e);if($e.Count){exit 2}}\n",encoding='utf-8')
        r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(harness),'-Folder',str(folder)],capture_output=True,timeout=40)
        need(r.returncode==0,'POWERSHELL_CANDIDATE_SYNTAX')


def targets(engine):
    windows=n.safe(engine/'windows',True)
    names={stem+'.ps1' for stem in STEMS}
    # Preserve deployed Clean references: update the ACTUAL referenced file too.
    for name in ('Prepare-No11NextSessionNightlyReadOnly.ps1','Prepare-No11WeeklyAfterCloseReadOnly.ps1','Prepare-No11PreviousArchiveReadOnly.ps1'):
        src=n.safe(windows/name).read_text(encoding='utf-8-sig')
        for literal in re.findall(r"['\"]([^'\"\r\n]+\.ps1)['\"]",src):
            if any(literal.startswith(stem) for stem in STEMS):
                need(Path(literal).name==literal and '/' not in literal and '\\' not in literal,'COLLECTOR_REFERENCE_PATH')
                names.add(literal)
    return [n.safe(windows/name) for name in sorted(names)]


def plan(store,source,record):
    registration=validate_registration(record);registry_raw=n.encode(registration)
    binding_file=n.safe(store/'automatic-inputs.json');before=binding_file.read_bytes();binding=n.read(binding_file)
    need(binding.get('schemaId')=='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' and binding.get('orderTransmission') is False,'BINDING_MODE')
    engine=n.safe(binding['engine'],True);worker=n.safe(binding['nightlyResumeTool'])
    need(n.digest(worker.read_bytes())==binding['nightlyResumeToolSha256'],'WORKER_HASH')
    validator=n.safe(worker.with_name(VALIDATOR));need(n.digest(validator.read_bytes())==binding['nightlyResumeValidatorSha256'],'VALIDATOR_HASH')
    helper=n.safe(source/HELPER).read_bytes();new_worker=transform_worker(worker.read_bytes(),n.digest(registry_raw))
    payload={HELPER:helper,REGISTRY:registry_raw,WORKER:new_worker,VALIDATOR:validator.read_bytes()}
    package_hash=n.digest(n.encode({k:n.digest(v) for k,v in payload.items()}))
    package=store/('registered-data-books-'+package_hash[:20])
    updated=dict(binding,nightlyResumeTool=str(package/WORKER),nightlyResumeToolSha256=n.digest(new_worker),
        dataWorkbookRegistration=str(package/REGISTRY),dataWorkbookRegistrationSha256=n.digest(registry_raw),
        dataWorkbookResolver=str(package/HELPER),dataWorkbookResolverSha256=n.digest(helper))
    entries=[]
    for path in targets(engine):
        raw=path.read_bytes();candidate=transform_collector(raw)
        need(raw!=candidate,'ALREADY_PATCHED_WITHOUT_JOURNAL')
        entries.append({'path':str(path),'before':b64(raw),'after':b64(candidate),'beforeSha256':n.digest(raw),'afterSha256':n.digest(candidate)})
    settings=n.safe(store/'settings.json');cfg=n.read(settings)
    need(cfg.get('orderTransmission') is False and cfg.get('automaticOrderAuthorization') is False,'SETTINGS_MODE')
    unchanged=[settings,n.safe(store/'oneclick/Start-No11OneClick.ps1'),n.safe(engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1')]
    return {'schemaId':n.SCHEMA,'kind':KIND,'phase':'PREPARED','orderTransmission':False,
        'binding':str(binding_file),'bindingBefore':b64(before),'bindingAfter':b64(n.encode(updated)),
        'entries':entries,'package':str(package),
        'payload':{name:{'bytes':b64(raw),'sha256':n.digest(raw)} for name,raw in payload.items()},
        'unchanged':{str(p):n.digest(p.read_bytes()) for p in unchanged}}


def verify(j):
    need(j.get('kind')==KIND and j.get('phase') in ('PREPARED','COMPLETE') and j.get('orderTransmission') is False,'JOURNAL_CONTRACT')
    before=un64(j['bindingBefore']);after=un64(j['bindingAfter'])
    allowed={'nightlyResumeTool','nightlyResumeToolSha256','dataWorkbookRegistration','dataWorkbookRegistrationSha256','dataWorkbookResolver','dataWorkbookResolverSha256'}
    old=json.loads(before);new=json.loads(after)
    need(all(new.get(k)==v for k,v in old.items() if k not in allowed) and new.get('orderTransmission') is False,'UNRELATED_BINDING_CHANGE')
    need(n.safe(j['binding']).read_bytes() in (before,after),'BINDING_EDIT')
    for row in j['entries']:
        a=un64(row['before']);b=un64(row['after'])
        need(n.digest(a)==row['beforeSha256'] and n.digest(b)==row['afterSha256'],'ENTRY_HASH')
        need(n.safe(row['path']).read_bytes() in (a,b),'EXTERNAL_COLLECTOR_EDIT')
    for path,sha in j['unchanged'].items():need(n.digest(n.safe(path).read_bytes())==sha,'LIVE_SETTINGS_OR_UI_CHANGED')
    for row in j['payload'].values():need(n.digest(un64(row['bytes']))==row['sha256'],'PACKAGE_HASH')


def install(store,source,do_apply=False,test_record=None):
    store=n.safe(store,True);source=n.safe(source,True);journal=store/JOURNAL
    with n.exclusive(store/'unified-refresh-install.lock'):
        if journal.exists():
            j=n.checkpoint(journal);verify(j)
            if j['phase']=='COMPLETE':
                need(n.safe(j['binding']).read_bytes()==un64(j['bindingAfter']),'COMPLETED_BINDING_CHANGED')
                for row in j['entries']:need(n.safe(row['path']).read_bytes()==un64(row['after']),'COMPLETED_COLLECTOR_CHANGED')
                for name,row in j['payload'].items():need(n.digest(n.safe(Path(j['package'])/name).read_bytes())==row['sha256'],'COMPLETED_PACKAGE_CHANGED')
                return 'ALREADY_APPLIED'
            need(do_apply,'INTERRUPTED_INSTALL_REQUIRES_APPLY')
        else:
            if test_record is None:quiet()
            record=test_record if test_record is not None else discover(n.safe(source/HELPER))
            j=plan(store,source,record)
            if not do_apply:return 'READY'
        if test_record is None:
            quiet()
            parse_candidates([un64(row['after']) for row in j['entries']]+[un64(j['payload'][HELPER]['bytes'])])
            # Check the same open books once more before committing code.
            observed=discover(n.safe(source/HELPER))
            expected=json.loads(un64(j['payload'][REGISTRY]['bytes']))
            normalize=lambda r: sorted(r['books'],key=lambda b:b['role'])
            need(normalize(observed)==normalize(expected),'OPEN_BOOKS_CHANGED_DURING_INSTALL')
        verify(j)
        if not journal.exists():n.atomic(journal,j)
        package=Path(j['package']);package.mkdir(exist_ok=True);n.safe(package,True)
        for name,row in j['payload'].items():immutable(package/name,un64(row['bytes']))
        for row in j['entries']:
            path=Path(row['path']);candidate=un64(row['after'])
            if path.read_bytes()!=candidate:replace(path,un64(row['before']),candidate)
            print('NO11_DATA_COLLECTOR_REGISTRATION='+path.name+'|PASS',flush=True)
        binding=Path(j['binding']);after=un64(j['bindingAfter'])
        if binding.read_bytes()!=after:replace(binding,un64(j['bindingBefore']),after)
        verify(j);j['phase']='COMPLETE';n.atomic(journal,j)
        return 'PASS'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store',required=True,type=Path);p.add_argument('--source-dir',required=True,type=Path);p.add_argument('--apply',action='store_true')
    a=p.parse_args()
    try:
        need(os.name=='nt','WINDOWS_ONLY')
        print('NO11_DATA_BOOK_REGISTRATION_INSTALL='+install(a.store,a.source_dir,a.apply))
        print('EXCEL_WORKBOOKS_MODIFIED=False\nLIVE_WORKBOOK_SETTINGS_CHANGED=False\nWEEKLY_DAILY_MAX47_PRESERVED=True\nWHITE_GUI_CHANGED=False')
    except Exception as e:
        reason=str(e)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+',reason):reason='NO11_DATA_BOOK_INSTALL_LOCAL_RUNTIME'
        print('NO11_DATA_BOOK_REGISTRATION_INSTALL=BLOCKED|'+reason)
        raise SystemExit(2)
    finally:print('TRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')

if __name__=='__main__':main()
