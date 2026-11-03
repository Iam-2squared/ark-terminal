#!/usr/bin/env python3
"""One-time offline upgrade: same broker session identity + owned C50 workbook.

Updates the already installed automatic launcher binding; patches only the
controller's environment relay and the order sink's temporary-book validator.
Original Frozen Selector, H235, Capital, EXIT, model weights, user account
settings, and RSS funding contract remain untouched. No broker order can fire
during installation. All touched files are backed up and rollback on failure.
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

BRIDGE_BLOB='453f61a9e0349851f0cf8edf0dba1f2a374a4bf5'
PROBE_BLOB='c1e2c3a165f7697691b04f477b9934c474ddb6b0'
PATCH_BLOB='23efe9652f843ed25aef3f42561baeb336ccf87f'
SCHEMA='ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'

def need(cond,code):
    if not cond:
        raise ValueError('NO11_ORDER_EXIT_WIRING_'+code)

def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def safe(path,*,folder=False):
    p=Path(path)
    need(p.is_absolute(),'ABSOLUTE_PATH')
    for item in (p,*p.parents):
        if item.exists() or item.is_symlink():
            need(not item.is_symlink() and not (getattr(item.lstat(),'st_file_attributes',0)&1024),'REPARSE_PATH')
    need(p.is_dir() if folder else p.is_file(),'PATH_MISSING')
    return p

def load(path):
    data=safe(path).read_bytes()
    need(0 < len(data) < 100000,'SOURCE_SIZE')
    return json.loads(data.decode('utf-8-sig')), data

def encode(obj):
    return (json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')

def ps_selftest(script,marker):
    cmd=['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
         '-File',str(script),'-OfflineSelfTest']
    result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=150)
    need(result.returncode==0 and marker in (result.stdout+result.stderr),'POWERSHELL_SELFTEST')

def ps_syntax(script):
    cmd="$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('"+str(script).replace("'","''")+"',[ref]$t,[ref]$e);if($e.Count){exit 2}"
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',cmd],
                          capture_output=True,text=True,timeout=60)
    need(result.returncode==0,'POWERSHELL_PARSE')

def assert_stopped():
    # The package install must not race a running user Trade/collector/transport.
    ps=r"""$p=@(Get-CimInstance Win32_Process | Where-Object {
      $_.Name -match '^(pythonw?|powershell|pwsh|node)(\.exe)?$' -and
      $_.CommandLine -match '(Start-No11UnifiedLauncher\.ps1|Run-No11ReceivedSessionOperatorLive\.ps1|no11_received_session_controller\.py|Invoke-No11MsiiOrder\.ps1)' -and
      $_.ProcessId -ne $PID
    }); if($p.Count){exit 2}"""
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],
                          capture_output=True,text=True,timeout=30)
    need(result.returncode==0,'CLOSE_RUNNING_ARK_FIRST')

def atomic(path,after,before):
    need(path.read_bytes()==before,'CONCURRENT_CHANGE')
    tmp=path.with_name(path.name+'.v3-'+uuid.uuid4().hex)
    try:
        with tmp.open('xb') as f:
            f.write(after);f.flush();os.fsync(f.fileno())
        need(path.read_bytes()==before,'CONCURRENT_CHANGE')
        os.replace(tmp,path)
    finally:
        if tmp.exists(): tmp.unlink()

def get_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def install(bridge_path,probe_path,patch_path):
    need(os.name=='nt','WINDOWS_ONLY')
    bridge=safe(bridge_path);probe=safe(probe_path);patch=safe(patch_path)
    for name,p,digest_pin in [('BRIDGE',bridge,BRIDGE_BLOB),
                              ('TRANSPORT',probe,PROBE_BLOB),
                              ('CORE_PATCH',patch,PATCH_BLOB)]:
        need(blob(p.read_bytes())==digest_pin,name+'_HASH')
    assert_stopped()
    store=safe(Path(os.environ['LOCALAPPDATA'])/'ArkTerminal/No12/unified-launcher',folder=True)
    binding_path=safe(store/'automatic-inputs.json')
    binding,binding_before=load(binding_path)
    need(type(binding) is dict and binding.get('schemaId')==SCHEMA
         and binding.get('orderTransmission') is False
         and binding.get('manualEvidenceRequired') is False
         and binding.get('manualPriceInputRequired') is False,'BINDING_CONTRACT')
    need(type(binding.get('transportProbe')) is str and
         type(binding.get('transportProbeSha256')) is str and
         type(binding.get('bridge')) is str and
         type(binding.get('bridgeSha256')) is str,'PREVIOUS_AUTO_LIVE_INSTALL_REQUIRED')
    for key in ('transportProbe','bridge','runner','automatic','handoff'):
        value=safe(binding[key])
        need(digest(value.read_bytes())==binding[key+'Sha256'],'PREVIOUS_PIN_CHANGED')
    engine=safe(binding['engine'],folder=True)
    controller=safe(engine/'tools/no11_received_session_controller.py')
    sender=safe(engine/'windows/Invoke-No11MsiiOrder.ps1')
    launcher=safe(engine/'windows/Start-No11UnifiedLauncher.ps1')
    operator=safe(engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1')
    fund=safe(engine/'windows/No11RssFundingContract.ps1')
    need('Assert-No11RssFundingContract' in operator.read_text(encoding='utf-8-sig')
         and 'AUTO_RSS_BUYING_POWER' in fund.read_text(encoding='utf-8-sig'),
         'RSS_BUYING_POWER_PATCH_MISSING')
    launcher_text=launcher.read_text(encoding='utf-8-sig')
    need(launcher_text.count('--same-day-operator-approved')==1,
         'SAME_DAY_TRADE_APPROVAL_HOOK_MISSING')

    pmod=get_module('ark_collector_transport_patch',patch)
    controller_before=controller.read_bytes()
    sender_before=sender.read_bytes()
    controller_after=pmod.transform_controller(controller_before)
    sender_after=pmod.transform_sender(sender_before)
    need(controller_after!=controller_before and sender_after!=sender_before,
         'ALREADY_INSTALLED_OR_PARTIAL')
    compile(controller_after.decode('utf-8-sig'),str(controller),'exec')
    binding_after=dict(binding)
    binding_after.update(
        bridge=str(bridge),bridgeSha256=digest(bridge.read_bytes()),
        transportProbe=str(probe),transportProbeSha256=digest(probe.read_bytes()),
        orderCollectorIdentityPolicy='PINNED_C50_READY_SHA256_AND_OBSERVER_EXCEL_SESSION',
        manualPriceInputRequired=False,manualEvidenceRequired=False,
        orderTransmission=False)
    binding_new=encode(binding_after)

    backup=store/('order-exit-wiring-'+uuid.uuid4().hex)
    backup.mkdir(mode=0o700)
    (backup/'no11_received_session_controller.py.before').write_bytes(controller_before)
    (backup/'Invoke-No11MsiiOrder.ps1.before').write_bytes(sender_before)
    (backup/'automatic-inputs.json.before').write_bytes(binding_before)
    (backup/'metadata.json').write_bytes(encode({'schemaId':'ARK_NO11_ORDER_EXIT_PATCH_BACKUP_V1',
        'controllerSha256':digest(controller_before),'senderSha256':digest(sender_before),
        'bindingSha256':digest(binding_before),'orderTransmission':False}))
    candidate=backup/'Invoke-No11MsiiOrder.test.ps1'
    candidate.write_bytes(sender_after)
    ps_syntax(candidate)
    candidate.unlink()
    ps_selftest(probe,'NO11_AUTO_TRANSPORT_OFFLINE_SELFTEST=PASS')

    paths=[(controller,controller_before,controller_after),
           (sender,sender_before,sender_after),
           (binding_path,binding_before,binding_new)]
    changed=[]
    try:
        for path,before,after in paths:
            atomic(path,after,before)
            changed.append((path,before,after))
        ps_selftest(sender,'PASS_OFFLINE_MOCK_ONLY')
        ps_selftest(launcher,'NO11_UNIFIED_OFFLINE_SELFTEST=PASS')
        ps_selftest(operator,'NO11_OPERATOR_LIVE_OFFLINE_SELFTEST=PASS')
    except BaseException:
        for path,before,after in reversed(changed):
            if path.exists() and path.read_bytes()==after:
                atomic(path,before,after)
        raise
    print('NO11_ORDER_TO_EXIT_WIRING_INSTALL=PASS')
    print('TRANSPORT_EXCEL_SESSION=ORIGINAL_READ_ONLY_OBSERVER_ID')
    print('C50_TEMPORARY_BOOK=HASH_PINNED_READY')
    print('BROKER_EXECUTION_MODE=NORMAL_MAX3_ORIGINAL')
    print('ORIGINAL_EXIT_LOGIC=UNCHANGED')
    print('RSS_BUYING_POWER_POLICY=PRESERVED')
    print('DAILY_EVIDENCE_REQUEST=False')
    print('MANUAL_PRICE_INPUT=False')
    print('ORIGINAL_LAUNCHER_EDITS=PRESERVED')
    print('LOCAL_SELFTESTS=PASS')
    print('EXCEL_TOUCHED=False')
    print('TRADE_LAUNCHED=False')
    print('ORDER_TRANSMISSION=False')
    print('BACKUP_ROOT='+str(backup))

def main():
    parser=argparse.ArgumentParser()
    for flag in ('bridge','probe','core-patch'):
        parser.add_argument('--'+flag,required=True,type=Path)
    a=parser.parse_args()
    install(a.bridge,a.probe,a.core_patch)

if __name__=='__main__':
    try:main()
    except Exception as e:
        reason=str(e)
        if not re.fullmatch(r'NO11_ORDER_EXIT_WIRING_[A-Z0-9_]+',reason):
            reason='NO11_ORDER_EXIT_WIRING_INSTALL_FAILED'
        print('NO11_ORDER_TO_EXIT_WIRING_INSTALL=BLOCKED|'+reason,file=sys.stderr)
        print('ORDER_TRANSMISSION=False',file=sys.stderr)
        raise SystemExit(2)
