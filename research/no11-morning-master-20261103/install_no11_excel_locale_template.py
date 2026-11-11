"""Install the locale/template compatibility fix; never run an order or Excel.

Preserve settings, data, UI, strategy, old transport source and all receipts.
Update a versioned initializer, the sender's format predicate and the packet
validator's Excel-container extension predicate in a recoverable transaction.
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
import no11_excel_locale_template as fix

JOURNAL = 'excel-locale-template-v1.transaction.json'
KIND = 'ARK_NO11_EXCEL_LOCALE_TEMPLATE_INSTALL_V1'


def need(ok, reason):
    if not ok:
        raise ValueError('NO11_LOCALE_INSTALL_' + reason)


def b64(raw):
    return base64.b64encode(raw).decode('ascii')


def raw(value):
    return base64.b64decode(value, validate=True)


def quiet():
    n.no_workers()
    # The checker is a FILE, so its own regex source cannot match itself.
    script = r'''$ErrorActionPreference='Stop'
try{
 $rows=@(Get-CimInstance Win32_Process -ErrorAction Stop|Where-Object {
  $_.ProcessId -ne $PID -and $_.Name -match '^(powershell|pwsh)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1'
 })
 if($rows.Count){exit 3};exit 0
}catch{exit 4}'''
    with tempfile.TemporaryDirectory(prefix='ark-locale-process-') as d:
        file = Path(d) / 'check.ps1'
        file.write_text(script, encoding='ascii')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
            '-ExecutionPolicy', 'Bypass', '-File', str(file)], capture_output=True,
            timeout=35, check=False)
    need(result.returncode == 0, 'CLOSE_ONECLICK_OR_PROCESS_CHECK_FAILED')


def check_syntax(*sources):
    with tempfile.TemporaryDirectory(prefix='ark-locale-syntax-') as d:
        check = Path(d) / 'parse.ps1'
        check.write_text('param([string]$File)\n$t=$null;$e=$null\n'
            '[void][Management.Automation.Language.Parser]::ParseFile($File,[ref]$t,[ref]$e)\n'
            'if($e.Count){exit 2}\n', encoding='ascii')
        for index, source in enumerate(sources):
            file = Path(d) / ('candidate-%d.ps1' % index)
            file.write_bytes(source)
            result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                '-ExecutionPolicy', 'Bypass', '-File', str(check), '-File', str(file)],
                capture_output=True, timeout=35, check=False)
            need(result.returncode == 0, 'CANDIDATE_POWERSHELL_SYNTAX')


def replace(path, before, after):
    need(n.safe(path).read_bytes() == before, 'CONCURRENT_FILE_EDIT')
    temp = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, prefix='.locale-', delete=False) as f:
            temp = Path(f.name)
            f.write(after); f.flush(); os.fsync(f.fileno())
        need(path.read_bytes() == before, 'CONCURRENT_FILE_EDIT')
        os.replace(temp, path); temp = None
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def publish(path, data):
    need(not path.is_symlink(), 'PACKAGE_REPARSE')
    if path.exists():
        need(n.safe(path).read_bytes() == data, 'PACKAGE_CHANGED')
        return
    temp = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, prefix='.locale-', delete=False) as f:
            temp = Path(f.name)
            f.write(data); f.flush(); os.fsync(f.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            need(n.safe(path).read_bytes() == data, 'PACKAGE_CONCURRENT_EDIT')
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def plan(store, test=False):
    binding_file = n.safe(store / 'automatic-inputs.json')
    binding = n.read(binding_file)
    need(binding.get('schemaId') == 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' and
         binding.get('orderTransmission') is False, 'BINDING_CONTRACT')
    settings = n.safe(store / 'settings.json')
    cfg = n.read(settings)
    need(cfg.get('schemaId') == 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' and
         cfg.get('sameDayApprovalRequired') is True and
         cfg.get('automaticOrderAuthorization') is False and
         cfg.get('orderTransmission') is False and cfg.get('normalMaxPositions') == 3,
         'SETTINGS_CONTRACT')
    old_probe = n.safe(binding['transportProbe'])
    need(n.digest(old_probe.read_bytes()) == binding['transportProbeSha256'], 'PROBE_SHA_CHANGED')
    engine = n.safe(binding['engine'], True)
    sender = n.safe(engine / 'windows/Invoke-No11MsiiOrder.ps1')
    js = n.safe(engine / 'tools/no11_msii_transport.mjs')
    probe_after = fix.transform_probe(old_probe.read_bytes())
    sender_after = fix.transform_sender(sender.read_bytes())
    js_after = fix.transform_js(js.read_bytes())
    if not test:
        check_syntax(probe_after, sender_after)
    package = store / ('excel-locale-template-' + n.digest(probe_after)[:24])
    dest = package / 'Prepare-No11AutomaticLiveTransportLocale.ps1'
    updated = dict(binding, transportProbe=str(dest), transportProbeSha256=n.digest(probe_after))
    need(set(updated) == set(binding) and all(updated[k] == v for k, v in binding.items()
         if k not in ('transportProbe', 'transportProbeSha256')), 'BINDING_SCOPE')
    frozen = [settings, old_probe,
        n.safe(store / 'oneclick/Start-No11OneClick.ps1'),
        n.safe(engine / 'windows/Run-No11ReceivedSessionOperatorLive.ps1')]
    for key in ('dataWorkbookRegistration', 'dataWorkbookResolver'):
        if key in binding:
            p = n.safe(binding[key])
            need(n.digest(p.read_bytes()) == binding[key + 'Sha256'], 'BOOK_REGISTRY_SHA')
            frozen.append(p)
    return {'schemaId': n.SCHEMA, 'kind': KIND, 'phase': 'PREPARED',
        'orderTransmission': False, 'package': str(package), 'probe': str(dest),
        'probeBytes': b64(probe_after), 'probeSha256': n.digest(probe_after),
        'sources': [{'path': str(p), 'before': b64(p.read_bytes()), 'after': b64(value)}
            for p, value in ((sender, sender_after), (js, js_after), (binding_file, n.encode(updated)))],
        'frozen': {str(p): n.digest(p.read_bytes()) for p in frozen}}


def verify(j):
    need(j.get('schemaId') == n.SCHEMA and j.get('kind') == KIND and
         j.get('phase') in ('PREPARED', 'COMPLETE') and j.get('orderTransmission') is False,
         'JOURNAL_CONTRACT')
    need(len(j['sources']) == 3 and len({r['path'] for r in j['sources']}) == 3, 'SOURCE_SET')
    for row in j['sources']:
        current = n.safe(row['path']).read_bytes()
        need(current in (raw(row['before']), raw(row['after'])), 'UNEXPECTED_LOCAL_EDIT')
        if j['phase'] == 'COMPLETE':
            need(current == raw(row['after']), 'COMPLETED_FILE_CHANGED')
    for p, sha in j['frozen'].items():
        need(n.digest(n.safe(p).read_bytes()) == sha, 'FROZEN_FILE_CHANGED')
    first = json.loads(raw(j['sources'][-1]['before']).decode('utf-8-sig'))
    last = json.loads(raw(j['sources'][-1]['after']).decode('utf-8-sig'))
    need(set(first) == set(last) and all(last[k] == v for k, v in first.items()
         if k not in ('transportProbe', 'transportProbeSha256')), 'JOURNAL_BINDING_SCOPE')
    payload = raw(j['probeBytes'])
    need(n.digest(payload) == j['probeSha256'] and fix.MARK.encode() in payload, 'PROBE_PAYLOAD')
    p = Path(j['probe'])
    if p.exists() or p.is_symlink():
        need(n.safe(p).read_bytes() == payload, 'DEPLOYED_PROBE_CHANGED')
    elif j['phase'] == 'COMPLETE':
        need(False, 'DEPLOYED_PROBE_MISSING')


def install(store, apply=False, test=False):
    store = n.safe(store, True)
    with n.exclusive(store / 'unified-refresh-install.lock'):
        journal = store / JOURNAL
        if journal.exists():
            j = n.checkpoint(journal)
            verify(j)
            if j['phase'] == 'COMPLETE':
                return 'ALREADY_APPLIED'
            need(apply, 'INTERRUPTED_INSTALL_REQUIRES_APPLY')
        else:
            j = plan(store, test)
            verify(j)
            if not apply:
                return 'READY'
        if not test:
            quiet()
        package = Path(j['package'])
        package.mkdir(exist_ok=True)
        n.safe(package, True)
        publish(Path(j['probe']), raw(j['probeBytes']))
        if not journal.exists():
            n.atomic(journal, j)
        verify(j)
        for row in j['sources']:
            p = Path(row['path'])
            if p.read_bytes() != raw(row['after']):
                replace(p, raw(row['before']), raw(row['after']))
        j['phase'] = 'COMPLETE'
        n.atomic(journal, j)
        verify(j)
        return 'PASS'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    try:
        need(os.name == 'nt', 'WINDOWS_REQUIRED')
        result = install(a.store, a.apply)
        print('NO11_EXCEL_LOCALE_TEMPLATE_INSTALL=' + result)
        print('INITIALIZER_AND_SENDER_GENERAL_POLICY=SYNCHRONIZED')
        print('TEMPLATE_INITIALIZATION=EXACT_VALUES_ONLY')
        print('UNKNOWN_CONTROL_VALUES_AUTOCLEARED=False')
        print('EXCEL_CELLS_MODIFIED=False')
        print('DATA_RECAPTURED=False')
        print('SAME_DAY_OPERATOR_APPROVAL_REQUIRED=True')
    except Exception as e:
        reason = str(e)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+', reason):
            reason = 'NO11_LOCALE_INSTALL_UNVERIFIED_IO_OR_SOURCE'
        print('NO11_EXCEL_LOCALE_TEMPLATE_INSTALL=BLOCKED|' + reason)
        raise SystemExit(2)
    finally:
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    main()
