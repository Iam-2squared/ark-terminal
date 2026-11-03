#!/usr/bin/env python3
"""Upgrade the already-installed automatic Trade hook with first-session RSS broker wiring.

No Excel is touched during install. No order permission is granted. Existing
local launcher edits are preserved; only the existing automatic hook invocation
is changed to forward the already-confirmed same-day Trade approval.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, uuid
from pathlib import Path

SCHEMA='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
OLD_CALL=" & $autoPython -B -X utf8 $autoBridge run --binding $autoBinding | ForEach-Object {"
NEW_CALL=" & $autoPython -B -X utf8 $autoBridge run --binding $autoBinding --same-day-operator-approved | ForEach-Object {"
BRIDGE_BLOB='7d06ba6986dd6abb7781a215453c2ad4465bf91e'
PROBE_BLOB='41d484b11aaba684301dd940c130c15274b6256a'

def need(ok, code):
    if not ok: raise ValueError('NO11_AUTO_LIVE_INSTALL_'+code)

def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def safe(path, directory=False):
    p=Path(path)
    need(p.is_absolute(), 'ABSOLUTE_PATH')
    for q in (p,*p.parents):
        if q.exists() or q.is_symlink():
            need(not q.is_symlink() and not (getattr(q.lstat(),'st_file_attributes',0)&1024),
                 'REPARSE_PATH')
    need(p.is_dir() if directory else p.is_file(), 'PATH_MISSING')
    return p.resolve(strict=True)

def load(path):
    p=safe(path)
    raw=p.read_bytes()
    obj=json.loads(raw.decode('utf-8-sig'))
    need(type(obj) is dict,'JSON_OBJECT')
    return obj,raw

def encode(obj):
    return (json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n').encode()

def replace_atomic(path, new, expected):
    p=Path(path)
    if p.exists():
        current=p.read_bytes()
        need(current==expected,'CONCURRENT_CHANGE')
    else:
        need(expected is None,'EXPECTED_EXISTING_FILE')
    tmp=p.with_name(p.name+'.auto-live-'+uuid.uuid4().hex)
    try:
        with tmp.open('xb') as f:
            f.write(new); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if tmp.exists(): tmp.unlink()

def ps_parse(path):
    cmd=("$e=$null;$t=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
         +"'"+str(path).replace("'","''")+"',[ref]$t,[ref]$e);if($e.Count){exit 2}")
    r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',cmd],
                     capture_output=True,text=True,timeout=60)
    need(r.returncode==0,'POWERSHELL_PARSE')

def run_ps(args,label,marker):
    r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
    need(r.returncode==0 and marker in (r.stdout+r.stderr),label)

def install(bridge_file,probe_file):
    bridge=safe(bridge_file); probe=safe(probe_file)
    need(blob(bridge.read_bytes())==BRIDGE_BLOB,'BRIDGE_HASH')
    need(blob(probe.read_bytes())==PROBE_BLOB,'PROBE_HASH')
    base=Path(os.environ['LOCALAPPDATA'])/'ArkTerminal/No12'
    store=safe(base/'unified-launcher',True)
    binding_file=safe(store/'automatic-inputs.json')
    binding,before_binding=load(binding_file)
    need(binding.get('schemaId')==SCHEMA and binding.get('orderTransmission') is False,
         'BINDING_CONTRACT')
    launcher=safe(Path(binding['engine'])/'windows/Start-No11UnifiedLauncher.ps1')
    before_launcher=launcher.read_bytes()
    text=before_launcher.decode('utf-8-sig')
    need(text.count(OLD_CALL)==1 and NEW_CALL not in text,'LAUNCHER_HOOK_STATE')
    after_launcher=text.replace(OLD_CALL,NEW_CALL,1).encode('utf-8')
    candidate=store/('launcher-auto-live-candidate-'+uuid.uuid4().hex+'.ps1')
    candidate.write_bytes(after_launcher)
    ps_parse(candidate)
    candidate.unlink()

    runlive=safe(Path(binding['engine'])/'windows/Run-No11ReceivedSessionOperatorLive.ps1')
    run_text=runlive.read_text(encoding='utf-8-sig')
    contract=safe(Path(binding['engine'])/'windows/No11RssFundingContract.ps1')
    contract_text=contract.read_text(encoding='utf-8-sig')
    need('No11RssFundingContract.ps1' in run_text and
         'Assert-No11RssFundingContract' in run_text and
         'RSS_BUYING_POWER' in contract_text and
         'AUTO_RSS_BUYING_POWER' in contract_text,
         'RSS_FUNDING_PATCH_NOT_PRESENT')

    backup=store/('auto-live-upgrade-'+uuid.uuid4().hex)
    backup.mkdir()
    (backup/'Start-No11UnifiedLauncher.ps1.before').write_bytes(before_launcher)
    (backup/'automatic-inputs.json.before').write_bytes(before_binding)

    new_binding=dict(binding)
    new_binding['bridge']=str(bridge)
    new_binding['bridgeSha256']=digest(bridge.read_bytes())
    new_binding['transportProbe']=str(probe)
    new_binding['transportProbeSha256']=digest(probe.read_bytes())
    new_binding['firstBrokerWiringMode']='SAME_TRADE_APPROVAL_CURRENT_EXCEL_SESSION_ONLY'
    new_binding['manualEvidenceRequired']=False
    new_binding['manualPriceInputRequired']=False
    new_binding['orderTransmission']=False
    changed_binding=encode(new_binding)

    try:
        replace_atomic(binding_file,changed_binding,before_binding)
        replace_atomic(launcher,after_launcher,before_launcher)
        run_ps(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                '-File',str(probe),'-OfflineSelfTest'],
               'TRANSPORT_OFFLINE_SELFTEST','NO11_AUTO_TRANSPORT_OFFLINE_SELFTEST=PASS')
        run_ps(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                '-File',str(launcher),'-OfflineSelfTest'],
               'LAUNCHER_OFFLINE_SELFTEST','NO11_UNIFIED_OFFLINE_SELFTEST=PASS')
        run_ps(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                '-File',str(runlive),'-OfflineSelfTest'],
               'OPERATOR_LIVE_OFFLINE_SELFTEST','NO11_OPERATOR_LIVE_OFFLINE_SELFTEST=PASS')
    except BaseException:
        if launcher.exists() and launcher.read_bytes()==after_launcher:
            replace_atomic(launcher,before_launcher,after_launcher)
        if binding_file.exists() and binding_file.read_bytes()==changed_binding:
            replace_atomic(binding_file,before_binding,changed_binding)
        raise

    print('AUTOMATIC_FIRST_BROKER_WIRING_INSTALL=PASS')
    print('SAME_DAY_TRADE_APPROVAL_REUSED_FOR_PHYSICAL_SESSION=True')
    print('TRANSPORT_OFFLINE_SELFTEST=PASS')
    print('LAUNCHER_OFFLINE_SELFTEST=PASS')
    print('OPERATOR_LIVE_OFFLINE_SELFTEST=PASS')
    print('RSS_FUNDING_PATCH=PRESERVED')
    print('MANUAL_EVIDENCE_REQUIRED=False')
    print('MANUAL_PRICE_INPUT_REQUIRED=False')
    print('EXCEL_TOUCHED=False')
    print('TRADE_LAUNCHED=False')
    print('ORDER_TRANSMISSION=False')
    print('BACKUP_ROOT='+str(backup))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--bridge',required=True,type=Path)
    p.add_argument('--transport-probe',required=True,type=Path)
    a=p.parse_args(); install(a.bridge,a.transport_probe)

if __name__=='__main__':
    try: main()
    except Exception as e:
        msg=str(e)
        if not re.fullmatch(r'NO11_AUTO_LIVE_INSTALL_[A-Z0-9_]+',msg):
            msg='NO11_AUTO_LIVE_INSTALL_LOCAL_RUNTIME_ERROR'
        print('AUTOMATIC_FIRST_BROKER_WIRING_INSTALL=BLOCKED|'+msg,file=sys.stderr)
        print('ORDER_TRANSMISSION=False',file=sys.stderr)
        raise SystemExit(2)
