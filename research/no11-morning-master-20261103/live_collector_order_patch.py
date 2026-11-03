#!/usr/bin/env python3
"""Pin the collector's owned temporary workbook into live order dispatch.

The controller starts the unchanged collector. Once its READY file is validated,
it passes a *hashed, immutable* READY file to the order transport subprocess.
The transport still requires exact identities of all saved workbooks and the
dedicated order controls. This patch never weakens a broker permit or creates
order approval. Installation is offline and preserves locally patched files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

CONTROLLER = 'tools/no11_received_session_controller.py'
SENDER = 'windows/Invoke-No11MsiiOrder.ps1'
CONTROLLER_MARKER = '# ARK_NO11_PINNED_COLLECTOR_READY_TO_ORDER_DISPATCH_V1'
SENDER_MARKER = '# ARK_NO11_ORDER_EXPECT_COLLECTOR_TEMPORARY_V1'
CONTROLLER_BEFORE = """            bootstrap.service.main(consumer_args(
                bootstrap, config, prepared, infer, view, live=allow_explicit_live),
                should_stop=stopped)"""
CONTROLLER_AFTER = """            # ARK_NO11_PINNED_COLLECTOR_READY_TO_ORDER_DISPATCH_V1
            # The collector already authenticated the READY receipt in ready_capture.
            # Its unsaved workbook was created AFTER the initial Excel session pin.
            # Pass exact READY bytes to live transport so it cannot be misclassified.
            key_path = 'ARK_NO11_PINNED_C50_READY_FILE'
            key_hash = 'ARK_NO11_PINNED_C50_READY_SHA256'
            old_path, old_hash = os.environ.get(key_path), os.environ.get(key_hash)
            try:
                if allow_explicit_live:
                    os.environ[key_path] = str(attempt.ready)
                    os.environ[key_hash] = hashlib.sha256(attempt.ready.read_bytes()).hexdigest()
                bootstrap.service.main(consumer_args(
                    bootstrap, config, prepared, infer, view, live=allow_explicit_live),
                    should_stop=stopped)
            finally:
                if old_path is None:
                    os.environ.pop(key_path, None)
                else:
                    os.environ[key_path] = old_path
                if old_hash is None:
                    os.environ.pop(key_hash, None)
                else:
                    os.environ[key_hash] = old_hash"""

SENDER_BEFORE = """ $descriptors=@($Config.expectedTemporaryWorkbooks)
 Need-No11Transport ($temporary.Count -eq $descriptors.Count) 'TEMPORARY_WORKBOOKS_CHANGED'"""

SENDER_AFTER = r""" $descriptors=@($Config.expectedTemporaryWorkbooks)
 # ARK_NO11_ORDER_EXPECT_COLLECTOR_TEMPORARY_V1
 # The original C50 collector starts AFTER the physical transport session pin.
 # Only the owned, READY-pinned temporary workbook can be joined; NEVER allow
 # an arbitrary unsaved book or loosen the saved workbook/broker destination.
 if($Config.mode -ceq 'LIVE' -and $descriptors.Count -eq 0 -and $temporary.Count -eq 1){
  $readyPath=[Environment]::GetEnvironmentVariable('ARK_NO11_PINNED_C50_READY_FILE','Process')
  $readySha=[Environment]::GetEnvironmentVariable('ARK_NO11_PINNED_C50_READY_SHA256','Process')
  Need-No11Transport (-not [string]::IsNullOrWhiteSpace($readyPath) -and
      [IO.Path]::IsPathRooted($readyPath) -and $readySha -cmatch '^[a-f0-9]{64}$') 'C50_READY_PIN_MISSING'
  $readyPath=[IO.Path]::GetFullPath($readyPath)
  Need-No11Transport ((Test-Path -LiteralPath $readyPath -PathType Leaf) -and
     (Get-Item -LiteralPath $readyPath).Length -gt 100 -and
     (Get-Item -LiteralPath $readyPath).Length -le 100000) 'C50_READY_FILE_INVALID'
  $cursor=$readyPath
  while(-not [string]::IsNullOrWhiteSpace($cursor)){
   Need-No11Transport (((Get-Item -LiteralPath $cursor -Force).Attributes -band
       [IO.FileAttributes]::ReparsePoint) -eq 0) 'C50_READY_REPARSE'
   $next=Split-Path -Parent $cursor
   if($next -ceq $cursor){break}
   $cursor=$next
  }
  $actualSha=(Get-FileHash -LiteralPath $readyPath -Algorithm SHA256).Hash.ToLowerInvariant()
  Need-No11Transport ($actualSha -ceq $readySha) 'C50_READY_BYTES_CHANGED'
  $ready=Get-Content -LiteralPath $readyPath -Raw -Encoding UTF8|ConvertFrom-Json
  Need-No11Transport ($ready.schemaId -ceq 'ARK_NO11_C50_COLLECTOR_READY_V1' -and
    $ready.sessionDate -ceq $Config.sessionDate -and
    $ready.orderTransmission -eq $false -and $ready.productionReady -eq $false -and
    $ready.processId -is [ValueType] -and [int]$ready.processId -gt 0 -and
    $ready.planFileSha256 -cmatch '^[a-f0-9]{64}$' -and
    $ready.temporaryWorkbook.identitySheet -ceq 'ARK_NO11_CUMULATIVE' -and
    $ready.temporaryWorkbook.identityCell -ceq 'G1' -and
    $ready.temporaryWorkbook.identityValue -cmatch '^ARK_NO11_C50_TEMP_[a-f0-9]{32}$' -and
    [string]::IsNullOrWhiteSpace([string]$ready.temporaryWorkbook.bookPath)) 'C50_READY_CONTRACT'
  $started=[datetimeoffset]::MinValue
  Need-No11Transport ([datetimeoffset]::TryParse([string]$ready.readyAtJst,
     [Globalization.CultureInfo]::InvariantCulture,
     [Globalization.DateTimeStyles]::None,[ref]$started) -and
     $started.ToOffset([TimeSpan]::FromHours(9)).ToString('yyyy-MM-dd') -ceq $Config.sessionDate -and
     $started -le [datetimeoffset]::UtcNow) 'C50_READY_CLOCK'
  $collector=Get-Process -Id ([int]$ready.processId) -ErrorAction SilentlyContinue
  Need-No11Transport ($null -ne $collector -and
     $collector.ProcessName -in @('powershell','pwsh')) 'C50_COLLECTOR_NOT_RUNNING'
  $descriptors=@($ready.temporaryWorkbook)
 }
 Need-No11Transport ($temporary.Count -eq $descriptors.Count) 'TEMPORARY_WORKBOOKS_CHANGED'"""

def need(cond, code):
    if not cond:
        raise ValueError('NO11_COLLECTOR_TRANSPORT_' + code)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def norm(b):
    raw=b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b''
    text=b[len(raw):].decode('utf-8')
    line='\r\n' if '\r\n' in text else '\n'
    text=text.replace('\r\n','\n')
    need('\r' not in text,'LINE_ENDINGS')
    return raw,text,line

def pack(bom,text,line):
    return bom+text.replace('\n',line).encode('utf-8')

def transform_controller(raw):
    bom,s,line=norm(raw)
    if CONTROLLER_MARKER in s:
        need(s.count(CONTROLLER_MARKER)==1,'CONTROLLER_PARTIAL_PATCH')
        return raw
    need(s.count(CONTROLLER_BEFORE)==1,'CONTROLLER_ANCHOR')
    need(s.count('import argparse\n')==1 and 'import hashlib\n' not in s and 'import os\n' not in s,
         'CONTROLLER_IMPORTS')
    s=s.replace('import argparse\n','import argparse\nimport hashlib\nimport os\n',1)
    s=s.replace(CONTROLLER_BEFORE,CONTROLLER_AFTER,1)
    return pack(bom,s,line)

def transform_sender(raw):
    bom,s,line=norm(raw)
    if SENDER_MARKER in s:
        need(s.count(SENDER_MARKER)==1,'SENDER_PARTIAL_PATCH')
        return raw
    need(s.count(SENDER_BEFORE)==1,'SENDER_ANCHOR')
    s=s.replace(SENDER_BEFORE,SENDER_AFTER,1)
    return pack(bom,s,line)

def safe(p,dir=False):
    p=Path(p)
    need(p.is_absolute(),'ABSOLUTE_PATH')
    for cur in (p,*p.parents):
        if cur.exists() or cur.is_symlink():
            need(not cur.is_symlink() and
                 not (getattr(cur.lstat(),'st_file_attributes',0)&1024),'REPARSE_PATH')
    need(p.is_dir() if dir else p.is_file(),'PATH_MISSING')
    return p

def atomic(path,new,expected):
    need(path.read_bytes()==expected,'FILE_CONCURRENTLY_CHANGED')
    temp=path.with_name(path.name+'.collector-'+uuid.uuid4().hex)
    try:
        with temp.open('xb') as f:
            f.write(new); f.flush(); os.fsync(f.fileno())
        need(path.read_bytes()==expected,'FILE_CONCURRENTLY_CHANGED')
        os.replace(temp,path)
    finally:
        if temp.exists(): temp.unlink()

def powershell_syntax(path):
    cmd="$e=$null;$t=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('"+str(path).replace("'","''")+"',[ref]$t,[ref]$e);if($e.Count){exit 2}"
    r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',cmd],
                     capture_output=True,text=True,timeout=60)
    need(r.returncode==0,'POWERSHELL_PARSE')

def install(engine,backups):
    engine=safe(engine,True)
    backups=safe(backups,True)
    files={CONTROLLER:transform_controller,SENDER:transform_sender}
    originals={}
    changes={}
    for name,patch in files.items():
        path=safe(engine/name)
        before=path.read_bytes()
        after=patch(before)
        need(after!=before,'ALREADY_INSTALLED')
        originals[name]=before
        changes[name]=after
    folder=backups/('collector-transport-'+uuid.uuid4().hex)
    folder.mkdir(mode=0o700)
    for name,raw in originals.items():
        (folder/Path(name).name).write_bytes(raw)
    candidate=folder/'Invoke-No11MsiiOrder.candidate.ps1'
    candidate.write_bytes(changes[SENDER])
    powershell_syntax(candidate)
    candidate.unlink()
    updated=[]
    try:
        for name in files:
            path=engine/name
            atomic(path,changes[name],originals[name])
            updated.append(name)
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive',
                '-ExecutionPolicy','Bypass','-File',str(engine/SENDER),'-OfflineSelfTest'],
            capture_output=True,text=True,timeout=90)
        need(result.returncode==0 and 'PASS_OFFLINE_MOCK_ONLY' in result.stdout,
             'TRANSPORT_OFFLINE_SELFTEST')
        import py_compile
        py_compile.compile(str(engine/CONTROLLER),doraise=True,
             cfile=str(folder/'controller-compile.pyc'))
    except BaseException:
        for name in reversed(updated):
            path=engine/name
            if path.read_bytes()==changes[name]:
                atomic(path,originals[name],changes[name])
        raise
    print('NO11_COLLECTOR_TRANSPORT_INSTALL=PASS')
    print('CONTINUOUS_C50_TEMPORARY_WORKBOOK=PINNED_TO_COLLECTOR_READY')
    print('SAVED_BOOK_DESTINATION=UNCHANGED')
    print('BRIDGE_ORDER_SESSION_WIRING=UNCHANGED')
    print('ORIGINAL_EXIT_PATH=UNCHANGED')
    print('TRANSPORT_OFFLINE_SELFTEST=PASS')
    print('EXCEL_TOUCHED=False')
    print('ORDER_TRANSMISSION=False')
    print('BACKUP_ROOT='+str(folder))

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--engine',type=Path,required=True)
    p.add_argument('--backups',type=Path,required=True)
    args=p.parse_args(argv)
    install(args.engine,args.backups)

if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as e:
        code=str(e)
        if not re.fullmatch(r'NO11_COLLECTOR_TRANSPORT_[A-Z0-9_]+',code):
            code='NO11_COLLECTOR_TRANSPORT_INSTALL_FAILED'
        print('NO11_COLLECTOR_TRANSPORT_INSTALL=BLOCKED|'+code,file=sys.stderr)
        print('ORDER_TRANSMISSION=False',file=sys.stderr)
        raise SystemExit(2)
