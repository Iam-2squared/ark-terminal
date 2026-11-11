"""Install reusable OneClick display V2, not a Trade or recovery command.

Default is audit. Explicit after-hours apply preserves local white layout and
all action handlers; installs verified read-only sidecars before the atomic
launcher switch. A durable journal preserves exact originals and permits only
verified interrupted-install continuation. Dates and accounts are never edited.
"""
from __future__ import annotations

import argparse
import ast
import base64
from datetime import datetime, time, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import no11_nightly_resume as n
import no11_oneclick_display_transform as migration
from no11_oneclick_display_v2 import native_source_family

JOURNAL = 'oneclick-display-v2-install.json'
KIND = 'ARK_NO11_ONECLICK_DISPLAY_MIGRATION_V2'
LEGACY_BLOB = '1f5611336abc8d68731a44243fa67a6c6a4ebf9f'
DISPLAY = 'no11_oneclick_display_v2.py'
CONTRACT = 'oneclick-display-v2.contract.json'


def need(ok, reason):
    if not ok:
        raise ValueError('NO11_DISPLAY_INSTALL_' + reason)


def blob(raw):
    data = raw.decode('utf-8-sig').replace('\r\n', '\n').encode('utf-8')
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def context(store):
    store = n.safe(store, True)
    binding_path, settings_path = store / 'automatic-inputs.json', store / 'settings.json'
    binding, settings = n.read(binding_path), n.read(settings_path)
    need(binding.get('schemaId') == 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
         and binding.get('orderTransmission') is False, 'BINDING_UNSAFE')
    need(settings.get('schemaId') == 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1'
         and settings.get('sameDayApprovalRequired') is True
         and settings.get('automaticOrderAuthorization') is False
         and settings.get('orderTransmission') is False
         and type(settings.get('normalMaxPositions')) is int
         and settings['normalMaxPositions'] == 3, 'SETTINGS_UNSAFE')
    home = n.safe(store / 'oneclick', True)
    launcher = n.safe(home / 'Start-No11OneClick.ps1')
    legacy = n.safe(home / 'oneclick_status.py')
    try:
        native_source_family(legacy.read_bytes())
    except (ValueError, UnicodeError):
        need(False, 'UNKNOWN_NATIVE_STATUS_SOURCE')
    engine = n.safe(binding['engine'], True)
    return home, launcher, legacy, engine, (binding_path, settings_path)


def payload(legacy):
    display = Path(__file__).with_name(DISPLAY).read_bytes()
    ast.parse(display.decode('utf-8-sig'))
    contract = {'schemaId': 'ARK_NO11_ONECLICK_DISPLAY_INSTALL_V2',
                'displaySha256': n.digest(display),
                'legacyStatusSha256': n.digest(legacy.read_bytes()),
                'orderTransmission': False, 'authorizationSourceChanged': False}
    return {DISPLAY: display, CONTRACT: n.encode(contract)}


def inventory(home, launcher, engine, external):
    items = set(external)
    for folder in (home, engine / 'tools', engine / 'windows', engine / 'runtime', engine / 'ui'):
        if not folder.exists():
            continue
        n.safe(folder, True)
        for item in folder.rglob('*'):
            if item.suffix.lower() in {'.py', '.ps1', '.mjs', '.js', '.css', '.html'}:
                if item != launcher and item != home / DISPLAY:
                    items.add(n.safe(item))
    return {str(p): n.digest(p.read_bytes()) for p in sorted(items)}


def plan(store):
    home, launcher, legacy, engine, external = context(store)
    before = launcher.read_bytes()
    need(migration.MARK not in before.decode('utf-8-sig'), 'EXISTING_MIGRATION_REQUIRES_JOURNAL')
    after = migration.transform(before)
    need(before != after, 'NO_SOURCE_CHANGE')
    extras = payload(legacy)
    for name in extras:
        need(not (home / name).exists() and not (home / name).is_symlink(), 'SIDECAR_ALREADY_EXISTS')
    return {'schemaId': n.SCHEMA, 'kind': KIND, 'phase': 'PREPARED',
            'orderTransmission': False, 'home': str(home), 'launcher': str(launcher),
            'before': base64.b64encode(before).decode('ascii'),
            'after': base64.b64encode(after).decode('ascii'),
            'sidecars': {name: base64.b64encode(data).decode('ascii') for name, data in extras.items()},
            'frozen': inventory(home, launcher, engine, external)}


def verify(store, record, *, frozen=True):
    home, launcher, legacy, engine, external = context(store)
    need(record.get('schemaId') == n.SCHEMA and record.get('kind') == KIND
         and record.get('phase') in ('PREPARED', 'COMPLETE')
         and record.get('orderTransmission') is False
         and record.get('home') == str(home) and record.get('launcher') == str(launcher), 'JOURNAL_CONTRACT')
    before, after = (base64.b64decode(record[k], validate=True) for k in ('before', 'after'))
    need(migration.MARK not in before.decode('utf-8-sig')
         and migration.transform(before) == after
         and migration.transform(after) == after, 'JOURNAL_DERIVATION_CHANGED')
    extras = payload(legacy)
    need(type(record.get('sidecars')) is dict and set(record['sidecars']) == set(extras), 'JOURNAL_SIDECARS')
    for name, data in extras.items():
        need(base64.b64decode(record['sidecars'][name], validate=True) == data, 'JOURNAL_PAYLOAD_CHANGED')
        path = home / name
        if path.exists() or path.is_symlink():
            need(n.safe(path).read_bytes() == data, 'SIDECAR_CHANGED')
        else:
            need(record['phase'] != 'COMPLETE', 'SIDECAR_MISSING')
    current = launcher.read_bytes()
    need(current in (before, after), 'CONCURRENT_LAUNCHER_CHANGE')
    if record['phase'] == 'COMPLETE':
        need(current == after, 'INSTALLED_LAUNCHER_CHANGED')
    if frozen:
        need(inventory(home, launcher, engine, external) == record['frozen'], 'UNRELATED_FILE_CHANGED')
    return launcher, before, after, extras


def off_hours():
    now = datetime.now(timezone(timedelta(hours=9))).time()
    need(not time(8, 0) <= now <= time(15, 40), 'AFTER_HOURS_ONLY')


def quiet():
    # Invoke directly from an interactive PowerShell. Never waive unknown
    # ancestors or kill arbitrary Python/UI/Excel processes to pass this gate.
    script = r"""$ErrorActionPreference='Stop'
try{
 $p=@();$bad=@()
 for($i=0;$i -lt 4;$i++){
  $all=@(Get-CimInstance Win32_Process -ErrorAction Stop)
  if($all.Count -eq 0){exit 5}
  $p=@($all|Where-Object{
   $_.ProcessId -notin @($PID,OWN_PROCESS,PARENT_PROCESS) -and
   $_.Name -match '^(powershell|pwsh|python|pythonw|node)([.]exe)?$'
  })
  $bad=@($p|Where-Object{[string]::IsNullOrWhiteSpace([string]$_.CommandLine)})
  if($bad.Count -eq 0){break}
  if($i -lt 3){Start-Sleep -Milliseconds 180}
 }
 if($bad.Count){exit 3}
 $pattern='(?i)no11_|No11|no12.*(nightly|collector)|OperatorLive[.]ps1|[\\/]controller[.]py|launcher_automatic_bridge|prestart-retry'
 if(@($p|Where-Object{[string]$_.CommandLine -match $pattern}).Count){exit 2}
 exit 0
}catch{exit 4}
""".replace('OWN_PROCESS', str(os.getpid())).replace('PARENT_PROCESS', str(os.getppid()))
    with tempfile.TemporaryDirectory(prefix='ark-display-quiet-') as tmp:
        path = Path(tmp) / 'quiet.ps1'
        path.write_text(script, encoding='ascii')
        proc = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
            '-ExecutionPolicy', 'Bypass', '-File', str(path)], capture_output=True, timeout=30, check=False)
    code = {2: 'ARK_WORKER_OR_UI_RUNNING', 3: 'PROCESS_COMMAND_UNREADABLE',
            4: 'PROCESS_QUERY_FAILED', 5: 'PROCESS_QUERY_EMPTY'}.get(proc.returncode, 'PROCESS_CHECK_FAILED')
    need(proc.returncode == 0, code)


def gate():
    need(os.name == 'nt', 'WINDOWS_REQUIRED')
    off_hours()
    quiet()


def parse_launcher(raw):
    with tempfile.TemporaryDirectory(prefix='ark-display-parse-') as tmp:
        target = Path(tmp) / 'launcher.ps1'
        target.write_bytes(raw)
        harness = Path(tmp) / 'parse.ps1'
        harness.write_text("param([string]$Target)\n$t=$null;$e=$null;[void][Management.Automation.Language.Parser]::ParseFile($Target,[ref]$t,[ref]$e);if(@($e).Count){exit 2};exit 0\n", encoding='ascii')
        proc = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
            'Bypass', '-File', str(harness), '-Target', str(target)], capture_output=True, timeout=30, check=False)
        need(proc.returncode == 0, 'POWERSHELL_PARSE_FAILED')


def replace_exact(path, before, after):
    need(n.safe(path).read_bytes() == before, 'CONCURRENT_LAUNCHER_CHANGE')
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, prefix='.ark-display-', delete=False) as out:
            tmp = Path(out.name)
            out.write(after)
            out.flush()
            os.fsync(out.fileno())
        need(path.read_bytes() == before, 'CONCURRENT_LAUNCHER_CHANGE')
        os.replace(tmp, path)
        tmp = None
        need(path.read_bytes() == after, 'LAUNCHER_READBACK_FAILED')
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def install(store, *, apply=False):
    store = n.safe(store, True)
    journal = store / JOURNAL
    record = n.checkpoint(journal) if journal.exists() else plan(store)
    decoded = verify(store, record, frozen=record['phase'] != 'COMPLETE')
    if not apply:
        return ('ALREADY_APPLIED' if record['phase'] == 'COMPLETE' else
                'INTERRUPTED_REQUIRES_APPLY' if journal.exists() else 'READY_NOT_APPLIED')
    gate()
    if record['phase'] == 'COMPLETE':
        return 'ALREADY_APPLIED'
    parse_launcher(decoded[2])
    with n.exclusive(store / 'unified-refresh-install.lock'):
        gate()
        record = n.checkpoint(journal) if journal.exists() else plan(store)
        launcher, before, after, extras = verify(store, record, frozen=record['phase'] != 'COMPLETE')
        if record['phase'] == 'COMPLETE':
            return 'ALREADY_APPLIED'
        if not journal.exists():
            n.atomic(journal, record)
        # UI remains original until BOTH read-only dependencies exist intact.
        for name, raw in extras.items():
            gate()
            verify(store, record)
            path = launcher.parent / name
            if not path.exists():
                with path.open('xb') as out:
                    out.write(raw)
                    out.flush()
                    os.fsync(out.fileno())
            need(path.read_bytes() == raw, 'SIDECAR_READBACK_FAILED')
        gate()
        verify(store, record)
        if launcher.read_bytes() == before:
            replace_exact(launcher, before, after)
        verify(store, record)
        record['phase'] = 'COMPLETE'
        n.atomic(journal, record)
        verify(store, record)
        return 'APPLIED_NO_TRADE'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    args = p.parse_args(argv)
    try:
        status = install(args.store, apply=args.apply)
        print('NO11_ONECLICK_DISPLAY_V2=' + status)
        print('WHITE_LAYOUT_AND_ACTION_HANDLERS=PRESERVED')
        print('NATIVE_AUTHORIZATION_AND_SCHEDULES=UNCHANGED')
        print('PAST_RESERVATIONS_LEDGER_AND_DATA=PRESERVED')
        return 0
    except Exception as exc:
        code = str(exc)
        if re.fullmatch(r'NO11_[A-Z0-9_]+', code) is None:
            code = 'NO11_DISPLAY_INSTALL_LOCAL_SOURCE_OR_IO_UNVERIFIED'
        print('NO11_ONECLICK_DISPLAY_V2=BLOCKED|' + code)
        print('PRESERVE_INSTALL_JOURNAL=True')
        return 2
    finally:
        print('TRADE_STARTED=False')
        print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    raise SystemExit(main())
