#!/usr/bin/env python3
"""V2: enroll the three currently open, role-checked books in one transaction.

V1 unnecessarily required the old DATA registry to match before replacing LIVE
paths. On explicit --apply, V2 discovers the actual saved books, updates both
registrations, and preserves all old sources. No workbook Save/Close, RSS
capture, Trade launch, session approval or brokerage ledger operation occurs.
Completed nightly pointers/checkpoints are never rewritten. Runtime handoff
adaptation changes only the registered OrderIds location in a new copy.
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
import no11_live_xlsb_contract as c
import no11_live_book_path_rebind as paths

JOURNAL = 'live-xlsb-open-book-enrollment-v2-transaction.json'
KIND = 'ARK_NO11_OPEN_THREE_BOOK_ENROLLMENT_V2'
HELPER = 'no11_live_book_path_rebind.py'
BRIDGE = 'launcher_automatic_bridge_v4.py'
BINDING_KEYS = {'dataWorkbookRegistration', 'dataWorkbookRegistrationSha256',
                'bridge', 'bridgeSha256', 'liveWorkbookHandoffTool',
                'liveWorkbookHandoffToolSha256'}


def need(ok, code):
    if not ok:
        raise ValueError('NO11_LIVE_XLSB_INSTALL_' + code)


def b64(raw):
    return base64.b64encode(raw).decode('ascii')


def un64(raw):
    return base64.b64decode(raw, validate=True)


def atomic_replace(path, old, new):
    need(n.safe(path).read_bytes() == old, 'CONCURRENT_LOCAL_EDIT')
    temp = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent,
                prefix='.live-book-enrollment-', delete=False) as stream:
            temp = Path(stream.name)
            stream.write(new)
            stream.flush()
            os.fsync(stream.fileno())
        need(path.read_bytes() == old, 'CONCURRENT_LOCAL_EDIT')
        os.replace(temp, path)
        temp = None
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def check_quiet():
    probe.no_workers()
    # Keep the existing no-live-worker requirement. Never terminate a process.
    code = r"""$ErrorActionPreference='Stop'
try {
 $rows=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(?:powershell|pwsh)(?:[.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11PreopenStandby[.]ps1'
 })
 if($rows.Count){exit 3};exit 0
} catch {exit 4}"""
    with tempfile.TemporaryDirectory(prefix='ark-book-process-check-') as tmp:
        script = Path(tmp) / 'check.ps1'
        script.write_text(code, encoding='utf-8')
        r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                '-ExecutionPolicy', 'Bypass', '-File', str(script)],
                capture_output=True, timeout=40, check=False)
    need(r.returncode == 0, 'LIVE_OR_ONECLICK_ACTIVE_OR_PROCESS_CHECK_FAILED')


def powershell_syntax(raw):
    with tempfile.TemporaryDirectory(prefix='ark-book-syntax-') as tmp:
        candidate = Path(tmp) / 'candidate.ps1'
        candidate.write_bytes(raw)
        script = Path(tmp) / 'parse.ps1'
        script.write_text("param([string]$Target)\n$t=$null;$e=$null\n"
            "[void][Management.Automation.Language.Parser]::ParseFile($Target,[ref]$t,[ref]$e)\n"
            "if($e.Count){exit 2}\n", encoding='utf-8')
        r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
            '-ExecutionPolicy', 'Bypass', '-File', str(script), '-Target', str(candidate)],
            capture_output=True, timeout=35, check=False)
    need(r.returncode == 0, 'POWERSHELL_PARSE')


def actual_open_books(binding, registered, allow_test=False):
    if allow_test:
        return dict(registered)
    helper = n.safe(binding['dataWorkbookResolver'])
    need(n.digest(helper.read_bytes()) == binding['dataWorkbookResolverSha256'],
         'RESOLVER_HASH')
    with tempfile.TemporaryDirectory(prefix='ark-three-open-books-') as tmp:
        output = Path(tmp) / 'new-registry.json'
        r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
            '-ExecutionPolicy', 'Bypass', '-File', str(helper),
            '-Discover', '-OutputFile', str(output)],
            capture_output=True, timeout=90, check=False)
        if r.returncode != 0 or not output.is_file():
            # Forward bounded error codes, never account cells or full paths.
            for line in (r.stdout + r.stderr).decode('utf-8', errors='replace').splitlines():
                if re.fullmatch(r'NO11_[A-Z0-9_=|]+', line):
                    print(line, flush=True)
            need(False, 'EXCEL_THREE_OR_RSS_BOOKS_NOT_OPEN')
        seen = c.checked_registration(n.read(output))
    # Registration is an explicit operation: an old path is not a prerequisite
    # for enrolling the uniquely identified current Account/Market/OrderIds.
    # Regular daily/LIVE consumers still enforce exact registered locations.
    print('NO11_LIVE_BOOK_PATH_CHECK=' +
          ('MATCHED' if paths.same_locations(seen, registered) else 'REFRESH_REQUIRED'), flush=True)
    return seen


def plan(store, binding, allow_test=False):
    need(binding.get('schemaId') == 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' and
         binding.get('orderTransmission') is False, 'BINDING_MODE')
    binding_file = n.safe(store / 'automatic-inputs.json')
    reg_path = n.safe(binding['dataWorkbookRegistration'])
    resolver = n.safe(binding['dataWorkbookResolver'])
    need(n.digest(reg_path.read_bytes()) == binding.get('dataWorkbookRegistrationSha256') and
         n.digest(resolver.read_bytes()) == binding.get('dataWorkbookResolverSha256'),
         'DATA_BOOK_REGISTRATION_PIN')
    previous = n.read(reg_path)
    registered = paths.registry_paths(previous)
    current = actual_open_books(binding, registered, allow_test)
    engine = n.safe(binding['engine'], True)
    launcher = n.safe(engine / 'windows/Start-No11UnifiedLauncher.ps1')
    operator = n.safe(engine / 'windows/Run-No11ReceivedSessionOperatorLive.ps1')
    settings = n.safe(store / 'settings.json')
    cfg = n.read(settings)
    revised = c.safe_settings_change(cfg, current)
    registry = paths.make_registration(current, previous, cfg, n.digest(reg_path.read_bytes()))
    registry_raw = n.encode(registry)
    payload = {'data-workbooks.json': registry_raw}
    bridge_source = None
    if 'bridge' in binding:
        bridge_source = n.safe(binding['bridge'])
        need(n.digest(bridge_source.read_bytes()) == binding.get('bridgeSha256'), 'BRIDGE_HASH')
        payload[BRIDGE] = paths.transform_bridge(bridge_source.read_bytes())
        payload[HELPER] = n.safe(Path(__file__).with_name(HELPER)).read_bytes()
    else:
        need(allow_test, 'BRIDGE_BINDING_MISSING')
    package_id = n.digest(n.encode({key: n.digest(value) for key, value in payload.items()}))[:24]
    package = store / ('open-three-book-enrollment-' + package_id)
    updated_binding = dict(binding,
        dataWorkbookRegistration=str(package / 'data-workbooks.json'),
        dataWorkbookRegistrationSha256=n.digest(registry_raw))
    if bridge_source is not None:
        updated_binding.update(bridge=str(package / BRIDGE),
            bridgeSha256=n.digest(payload[BRIDGE]),
            liveWorkbookHandoffTool=str(package / HELPER),
            liveWorkbookHandoffToolSha256=n.digest(payload[HELPER]))
    need(set(updated_binding) - set(binding) <= BINDING_KEYS and
         all(updated_binding.get(k) == v for k, v in binding.items() if k not in BINDING_KEYS),
         'UNRELATED_BINDING_CHANGED')
    launcher_after = c.transform_launcher(launcher.read_bytes())
    operator_after = c.transform_operator(operator.read_bytes())
    if not allow_test:
        powershell_syntax(launcher_after)
        powershell_syntax(operator_after)
    pairs = [(launcher, launcher_after), (operator, operator_after),
             (settings, n.encode(revised)), (binding_file, n.encode(updated_binding))]
    protected = [n.safe(store / 'oneclick/Start-No11OneClick.ps1'),
        n.safe(engine / 'windows/Observe-No11AccountReadOnly.ps1'), reg_path, resolver]
    if bridge_source is not None:
        protected.append(bridge_source)
    return {'schemaId': n.SCHEMA, 'kind': KIND, 'phase': 'PREPARED',
        'orderTransmission': False, 'liveOrderAuthorization': False,
        'store': str(store), 'currentBooks': current, 'package': str(package),
        'sources': [{'path': str(p), 'before': b64(p.read_bytes()), 'after': b64(after)}
                    for p, after in pairs],
        'payload': {name: {'data': b64(raw), 'sha256': n.digest(raw)}
                    for name, raw in payload.items()},
        'frozen': {str(p): n.digest(p.read_bytes()) for p in protected}}


def verify(j):
    need(j.get('schemaId') == n.SCHEMA and j.get('kind') == KIND and
         j.get('phase') in ('PREPARED', 'COMPLETE') and
         j.get('orderTransmission') is False and j.get('liveOrderAuthorization') is False,
         'JOURNAL')
    rows = j['sources']
    need(len(rows) == 4 and len({r['path'] for r in rows}) == 4, 'SOURCE_SET')
    for row in rows:
        actual = n.safe(row['path']).read_bytes()
        need(actual in (un64(row['before']), un64(row['after'])), 'EXTERNAL_CHANGE_DETECTED')
        if j['phase'] == 'COMPLETE':
            need(actual == un64(row['after']), 'COMPLETED_BINDING_CHANGED')
    for file, sha in j['frozen'].items():
        need(n.digest(n.safe(file).read_bytes()) == sha, 'FROZEN_SOURCE_CHANGED')
    for name, item in j['payload'].items():
        raw = un64(item['data'])
        need(Path(name).name == name and n.digest(raw) == item['sha256'], 'PAYLOAD_CONTRACT')
        installed = Path(j['package']) / name
        if installed.exists() or installed.is_symlink():
            need(n.safe(installed).read_bytes() == raw, 'PACKAGE_CHANGED')
        elif j['phase'] == 'COMPLETE':
            need(False, 'COMPLETED_PACKAGE_MISSING')
    before = json.loads(un64(rows[-1]['before']).decode('utf-8-sig'))
    after = json.loads(un64(rows[-1]['after']).decode('utf-8-sig'))
    need(all(after.get(k) == v for k, v in before.items() if k not in BINDING_KEYS) and
         after.get('orderTransmission') is False, 'BINDING_SCOPE_CHANGED')
    return before, after


def install(store, apply=False, allow_test=False):
    store = n.safe(store, True)
    with n.exclusive(store / 'unified-refresh-install.lock'):
        if not allow_test:
            check_quiet()
        binding = n.read(n.safe(store / 'automatic-inputs.json'))
        journal = store / JOURNAL
        if journal.exists():
            j = n.checkpoint(journal)
            verify(j)
            if j['phase'] == 'COMPLETE':
                seen = actual_open_books(binding, j['currentBooks'], allow_test)
                need(paths.same_locations(seen, j['currentBooks']), 'OPEN_BOOKS_CHANGED_SINCE_ENROLLMENT')
                return 'ALREADY_APPLIED'
            need(apply, 'INCOMPLETE_TRANSACTION_REQUIRES_APPLY')
        else:
            j = plan(store, binding, allow_test)
            if not apply:
                return 'READY'
        before, after = verify(j)
        # Check the actual books again before committing. The second check is
        # against this operation's observed books, NOT the obsolete registry.
        seen = actual_open_books(before, j['currentBooks'], allow_test)
        need(paths.same_locations(seen, j['currentBooks']), 'OPEN_BOOKS_CHANGED_DURING_INSTALL')
        if not allow_test:
            check_quiet()
        if not journal.exists():
            n.atomic(journal, j)
        package = Path(j['package'])
        package.mkdir(exist_ok=True)
        n.safe(package, True)
        for name, item in j['payload'].items():
            paths.immutable(package / name, un64(item['data']))
        verify(j)
        for row in j['sources']:
            p = Path(row['path'])
            old, new = un64(row['before']), un64(row['after'])
            if p.read_bytes() != new:
                atomic_replace(p, old, new)
        # Binding is committed last. Re-running a partially applied transaction
        # resumes known before/after bytes; never clears receipts or checkpoints.
        j['phase'] = 'COMPLETE'
        verify(j)
        n.atomic(journal, j)
        return 'PASS'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        need(os.name == 'nt', 'WINDOWS_ONLY')
        status = install(args.store, args.apply)
        print('NO11_LIVE_XLSB_PREFLIGHT_INSTALL=' + status)
        print('NO11_OPEN_BOOK_REGISTRATION_VERSION=2')
        print('NO11_DATA_AND_LIVE_BOOK_PATHS=SYNCHRONIZED')
        print('COMPLETED_DAILY_POINTERS_AND_RECEIPTS_MODIFIED=False')
        print('FROZEN_ENTRY_EXIT_MODIFIED=False')
        print('WHITE_ONECLICK_MODIFIED=False')
        print('WORKBOOKS_MODIFIED=False')
    except Exception as error:
        reason = str(error)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+', reason):
            reason = 'NO11_LIVE_XLSB_INSTALL_UNVERIFIED_SYSTEM'
        print('NO11_LIVE_XLSB_PREFLIGHT_INSTALL=BLOCKED|' + reason)
        raise SystemExit(2)
    finally:
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    main()
