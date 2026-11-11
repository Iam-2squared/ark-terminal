"""After-hours TWO-FILE source repair. No Excel, orders, rearm or Trade entry.

Audit is the default. Apply requires Windows, a quiet runtime, an off-market
clock and the existing installer lock. Unknown local sources are never replaced.
A durable journal saves exact original bytes before either atomic replacement.
Interrupted partial installation can only continue from its verified journal.
Existing strategy, observer, transport, UI, settings and session evidence stay.
"""
from __future__ import annotations

import argparse
import ast
import base64
from datetime import datetime, time, timedelta, timezone
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile

import no11_nightly_resume as n
import no11_weekly_filtered_lineage as weekly
import no11_rss_opening_source_wait as funding

KIND = 'ARK_NO11_AFTERCLOSE_SOURCE_REPAIR_V1'
JOURNAL = 'afterclose-source-repair-v1-install.json'
RSS_BOOTSTRAP_BLOB = '011171c82c960e3b2a8f520439e3e609b2578607'
NATIVE_WEEKLY_BLOB = 'b777b944379c7c6dda15eac10ddda5959ab181c8'
TARGETS = {
    'BOOTSTRAP': 'tools/no11_received_session_bootstrap.py',
    'FUNDING': 'tools/no11_rss_buying_power.py',
}


def need(ok, reason):
    if not ok:
        raise ValueError('NO11_AFTERCLOSE_REPAIR_' + reason)


def blob(raw):
    data = weekly.norm(raw)[1].encode('utf-8')
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def bootstrap_target(raw):
    """Accept the exact installed RSS source or its exact weekly derivation."""
    if blob(raw) == RSS_BOOTSTRAP_BLOB:
        return weekly.transform(raw)
    bom, text, newline = weekly.norm(raw)
    anchor = weekly.HELPER + 'def export_scope(config):\n'
    need(text.count(anchor) == 1 and text.count(weekly.NEW) == 1,
         'UNKNOWN_BOOTSTRAP_SOURCE')
    original = text.replace(anchor, 'def export_scope(config):\n', 1)
    original = original.replace(weekly.NEW, weekly.OLD, 1)
    before = bom + original.replace('\n', newline).encode('utf-8')
    need(blob(before) == RSS_BOOTSTRAP_BLOB and weekly.transform(before) == raw,
         'UNKNOWN_BOOTSTRAP_SOURCE')
    return raw


def paths(store):
    store = n.safe(store, True)
    bfile = n.safe(store / 'automatic-inputs.json')
    sfile = n.safe(store / 'settings.json')
    binding, settings = n.read(bfile), n.read(sfile)
    need(binding.get('schemaId') == 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
         and binding.get('orderTransmission') is False, 'BINDING_CONTRACT')
    need(settings.get('schemaId') == 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1'
         and settings.get('sameDayApprovalRequired') is True
         and settings.get('automaticOrderAuthorization') is False
         and settings.get('orderTransmission') is False
         and type(settings.get('normalMaxPositions')) is int
         and settings['normalMaxPositions'] == 3, 'SETTINGS_CONTRACT')
    engine = n.safe(binding['engine'], True)
    targets = {key: n.safe(engine / name) for key, name in TARGETS.items()}
    need(len(set(targets.values())) == 2, 'TARGET_COLLISION')
    native = n.safe(engine / 'tools/no11_verified_weekly_shadow_scope.mjs')
    need(blob(native.read_bytes()) == NATIVE_WEEKLY_BLOB, 'NATIVE_WEEKLY_CHANGED')
    white = n.safe(store / 'oneclick/Start-No11OneClick.ps1')
    return engine, targets, (bfile, sfile, white)


def frozen_inventory(engine, targets, external):
    files = set(external)
    for folder in ('tools', 'windows', 'runtime', 'ui'):
        root = engine / folder
        if not root.exists():
            continue
        n.safe(root, True)
        for path in root.rglob('*'):
            if path.suffix.lower() in {'.py', '.mjs', '.js', '.ps1', '.html', '.css'}:
                files.add(n.safe(path))
    files.difference_update(targets.values())
    return {str(p): n.digest(p.read_bytes()) for p in sorted(files)}


def make_plan(store):
    engine, targets, external = paths(store)
    entries = {}
    for key, path in targets.items():
        before = path.read_bytes()
        after = bootstrap_target(before) if key == 'BOOTSTRAP' else funding.transform(before)
        ast.parse(after.decode('utf-8-sig'))
        entries[key] = {
            'path': str(path),
            'before': base64.b64encode(before).decode('ascii'),
            'after': base64.b64encode(after).decode('ascii'),
            'beforeSha256': n.digest(before), 'afterSha256': n.digest(after),
        }
    return {'schemaId': n.SCHEMA, 'kind': KIND, 'phase': 'PREPARED',
            'engine': str(engine), 'entries': entries,
            'frozen': frozen_inventory(engine, targets, external),
            'orderTransmission': False}


def verify(store, record, *, frozen=True):
    engine, targets, external = paths(store)
    need(record.get('schemaId') == n.SCHEMA and record.get('kind') == KIND
         and record.get('phase') in ('PREPARED', 'COMPLETE')
         and record.get('orderTransmission') is False
         and record.get('engine') == str(engine)
         and type(record.get('entries')) is dict
         and set(record['entries']) == set(TARGETS), 'JOURNAL_CONTRACT')
    decoded = {}
    for key, path in targets.items():
        entry = record['entries'][key]
        need(entry['path'] == str(path), 'JOURNAL_TARGET_MISMATCH')
        before, after = (base64.b64decode(entry[name], validate=True)
                         for name in ('before', 'after'))
        expected = bootstrap_target(before) if key == 'BOOTSTRAP' else funding.transform(before)
        need(n.digest(before) == entry['beforeSha256']
             and n.digest(after) == entry['afterSha256']
             and expected == after, 'JOURNAL_DERIVATION_CHANGED')
        current = path.read_bytes()
        need(current in (before, after), 'CONCURRENT_TARGET_CHANGE')
        if record['phase'] == 'COMPLETE':
            need(current == after, 'INSTALLED_TARGET_CHANGED')
        decoded[key] = (path, before, after)
    if frozen:
        need(frozen_inventory(engine, targets, external) == record['frozen'],
             'UNRELATED_SOURCE_OR_SETTINGS_CHANGED')
    return decoded


def no_market_window():
    current = datetime.now(timezone(timedelta(hours=9))).time()
    need(not time(8, 0) <= current <= time(15, 40), 'AFTER_HOURS_ONLY')


def quiet():
    """Complete CIM snapshots; neither kill workers nor exempt unknown ones."""
    script = r"""$ErrorActionPreference='Stop'
try {
 $bad=@();$p=@()
 for($attempt=0;$attempt -lt 4;$attempt++){
  $all=@(Get-CimInstance Win32_Process -ErrorAction Stop)
  if($all.Count -eq 0){exit 5}
  $p=@($all|Where-Object{
   $_.ProcessId -notin @($PID,OWN_PROCESS,PARENT_PROCESS) -and
   $_.Name -match '^(powershell|pwsh|python|pythonw|node)([.]exe)?$'
  })
  $bad=@($p|Where-Object{[string]::IsNullOrWhiteSpace([string]$_.CommandLine)})
  if($bad.Count -eq 0){break}
  Start-Sleep -Milliseconds 180
 }
 if($bad.Count){exit 3}
 $pattern='(?i)no11_|No11|no12.*(nightly|collector)|OperatorLive[.]ps1|[\\/]controller[.]py|launcher_automatic_bridge|prestart-retry'
 $workers=@($p|Where-Object{[string]$_.CommandLine -match $pattern})
 if($workers.Count){exit 2}
 exit 0
}catch{exit 4}
""".replace('OWN_PROCESS', str(os.getpid())).replace('PARENT_PROCESS', str(os.getppid()))
    with tempfile.TemporaryDirectory(prefix='ark-source-repair-quiet-') as temporary:
        harness = Path(temporary) / 'quiet.ps1'
        harness.write_text(script, encoding='ascii')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
            '-ExecutionPolicy', 'Bypass', '-File', str(harness)],
            capture_output=True, timeout=30, check=False)
    need(result.returncode == 0, 'ARK_WORKERS_UI_OR_UNREADABLE_PROCESS')


def gate():
    need(os.name == 'nt', 'WINDOWS_REQUIRED')
    no_market_window()
    quiet()


def replace_exact(path, before, after):
    need(n.safe(path).read_bytes() == before, 'CONCURRENT_TARGET_CHANGE')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent,
                                         prefix='.ark-source-repair-', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(after)
            handle.flush()
            os.fsync(handle.fileno())
        need(n.safe(path).read_bytes() == before, 'CONCURRENT_TARGET_CHANGE')
        os.replace(temporary, path)
        temporary = None
        need(path.read_bytes() == after, 'SOURCE_READBACK_FAILED')
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def install(store, *, apply=False):
    store = n.safe(store, True)
    journal = store / JOURNAL
    if not apply:
        if journal.exists():
            record = n.checkpoint(journal)
            verify(store, record, frozen=record['phase'] != 'COMPLETE')
            return 'ALREADY_APPLIED' if record['phase'] == 'COMPLETE' else 'INTERRUPTED_REQUIRES_APPLY'
        make_plan(store)
        return 'READY_NOT_APPLIED'
    gate()
    with n.exclusive(store / 'unified-refresh-install.lock'):
        gate()
        if journal.exists():
            record = n.checkpoint(journal)
            verify(store, record, frozen=record['phase'] != 'COMPLETE')
            if record['phase'] == 'COMPLETE':
                return 'ALREADY_APPLIED'
        else:
            record = make_plan(store)
            verify(store, record)
            n.atomic(journal, record)
        for key in TARGETS:
            gate()
            decoded = verify(store, record)
            path, before, after = decoded[key]
            if path.read_bytes() == before and before != after:
                replace_exact(path, before, after)
        verify(store, record)
        for path, before, after in verify(store, record).values():
            need(path.read_bytes() == after, 'SOURCE_READBACK_FAILED')
        record['phase'] = 'COMPLETE'
        n.atomic(journal, record)
        verify(store, record)
        return 'APPLIED_NO_TRADE'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    try:
        status = install(args.store, apply=args.apply)
        print('NO11_AFTERCLOSE_SOURCE_REPAIR=' + status)
        print('WHITE_ONECLICK_AND_OTHER_RUNTIME=UNCHANGED')
        print('SETTINGS_BINDING_AND_SESSION_RECORDS=UNCHANGED')
        print('FUNDING_POLICY_AND_EXTERNAL_HOLDING_EXCLUSIONS=RETAINED')
        print('TWO_TARGET_SOURCES=BOOTSTRAP_WEEKLY_LINEAGE_AND_RSS_OPENING_READ')
        return 0
    except Exception as exc:
        reason = str(exc)
        if re.fullmatch(r'NO11_[A-Z0-9_]+', reason) is None:
            reason = 'NO11_AFTERCLOSE_REPAIR_LOCAL_OR_IO_UNVERIFIED'
        print('NO11_AFTERCLOSE_SOURCE_REPAIR=BLOCKED|' + reason)
        print('PRESERVE_INSTALL_JOURNAL_AND_DO_NOT_START_TRADE=True')
        return 2
    finally:
        print('TRADE_STARTED=False')
        print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    raise SystemExit(main())
