#!/usr/bin/env python3
"""Audit by default. Install DATA resume and diagnostic transport, never Trade.

Run from a verified release checkout/package. Existing local sources must match
known contexts AND their bound hashes. Interrupted installs restore exact backed
up bytes before a new apply; unknown concurrent edits are NEVER overwritten.
The approved white UI, broker ledger and all trade/halt markers are untouched.
"""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

import no11_nightly_resume as n
import patch_no11_transport_resilience as transport

OLD_FILTER = b"if line.startswith(('AUTOMATIC_TRANSPORT_', 'ORDER_TRIGGER_', 'ORDER_SENT=')):"
NEW_FILTER = b"if line.startswith(('AUTOMATIC_TRANSPORT_', 'AUTOMATIC_TRANSPORT=BLOCKED|', 'ORDER_TRIGGER_', 'ORDER_SENT=')):"
LEGACY_NIGHTLY_BLOB = '9ca459c9f58238975fe4fe4d1e03664484458a6a'


def need(ok, reason):
    if not ok:
        raise ValueError('NO11_RESILIENCE_INSTALL_' + reason)


def replace(path, before, after):
    path = n.safe(path)
    need(path.read_bytes() == before, 'CONCURRENT_EDIT')
    candidate = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, delete=False) as out:
            candidate = Path(out.name)
            out.write(after)
            out.flush()
            os.fsync(out.fileno())
        need(path.read_bytes() == before, 'CONCURRENT_EDIT')
        os.replace(candidate, path)
        candidate = None
    finally:
        if candidate is not None:
            candidate.unlink(missing_ok=True)


def quiet():
    n.no_workers()
    # UI must not launch a competing task while binding files are exchanged.
    ps = ("$ErrorActionPreference='Stop';try{$p=@(Get-CimInstance Win32_Process -ErrorAction Stop|Where-Object{"
          "$_.ProcessId -ne $PID -and $_.Name -match '^(powershell|pwsh)([.]exe)?$' -and "
          "[string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11UnifiedLauncher[.]ps1|Start-No11PreopenStandby[.]ps1'"
          "});if($p.Count){exit 3};exit 0}catch{exit 4}")
    r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', ps],
                       capture_output=True, timeout=30, check=False)
    need(r.returncode == 0, 'CLOSE_ARK_UI_OR_PROCESS_QUERY_FAILED')


def target_paths(store, old_binding):
    b = json.loads(old_binding.decode('utf-8-sig'))
    need(b.get('schemaId') == 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' and
         b.get('orderTransmission') is False, 'ORIGINAL_BINDING_UNSAFE')
    return {'binding': n.safe(store / 'automatic-inputs.json'),
            'bridge': n.safe(b['bridge']),
            'nightly': n.safe(Path(b['engine']) / 'windows/Run-No11NightlyCycle.ps1')}


def restore_or_verify(store, journal, do_apply):
    if not journal.exists():
        return False
    j = n.checkpoint(journal)
    need(j.get('kind') == 'INSTALL_WEEK_RESILIENCE' and
         set(j.get('entries', {})) == {'binding', 'bridge', 'nightly'}, 'JOURNAL_CONTRACT')
    entries = {k: {f: base64.b64decode(v[f], validate=True) for f in ('before', 'after')}
               for k, v in j['entries'].items()}
    paths = target_paths(store, entries['binding']['before'])
    white = n.safe(store / 'oneclick/Start-No11OneClick.ps1')
    need(n.digest(white.read_bytes()) == j['whiteSha256'], 'WHITE_UI_CHANGED_DURING_INSTALL')
    # Check every path before restoring ANY path.
    for k, path in paths.items():
        need(path.read_bytes() in (entries[k]['before'], entries[k]['after']), 'INTERRUPTED_INSTALL_HAS_UNKNOWN_EDIT')
    if j['phase'] == 'COMPLETE':
        for k, path in paths.items():
            need(path.read_bytes() == entries[k]['after'], 'COMPLETED_INSTALL_CHANGED')
        b = n.read(paths['binding'])
        for field in ('transportProbe', 'nightlyResumeTool'):
            need(n.digest(n.safe(b[field]).read_bytes()) == b[field + 'Sha256'], 'INSTALLED_PACKAGE_CHANGED')
        validator = Path(b['nightlyResumeTool']).with_name('no11_selection_status.py')
        need(n.digest(n.safe(validator).read_bytes()) == b['nightlyResumeValidatorSha256'], 'INSTALLED_VALIDATOR_CHANGED')
        return True
    need(j['phase'] in ('PREPARED', 'RESTORED'), 'JOURNAL_PHASE')
    need(do_apply, 'INTERRUPTED_INSTALL_REQUIRES_EXPLICIT_APPLY')
    quiet()
    for k in ('binding', 'bridge', 'nightly'):
        current = paths[k].read_bytes()
        if current == entries[k]['after'] and current != entries[k]['before']:
            replace(paths[k], current, entries[k]['before'])
    j['phase'] = 'RESTORED'
    n.atomic(journal, j)
    return False


def plan(store, source):
    binding_file = n.safe(store / 'automatic-inputs.json')
    raw_binding = binding_file.read_bytes()
    b = n.read(binding_file)
    paths = target_paths(store, raw_binding)
    settings = n.read(n.safe(b['settings']))
    need(settings.get('sameDayApprovalRequired') is True and
         settings.get('orderTransmission') is False and
         settings.get('automaticOrderAuthorization') is False and
         settings.get('normalMaxPositions') == 3, 'SAFETY_SETTINGS')
    for name in ('bridge', 'transportProbe'):
        need(n.digest(n.safe(b[name]).read_bytes()) == b.get(name + 'Sha256'), 'BOUND_SOURCE_CHANGED')
    before = {k: path.read_bytes() for k, path in paths.items()}
    normalized = before['nightly'].decode('utf-8-sig').replace('\r\n', '\n').encode('utf-8')
    need(transport.blob(normalized) == LEGACY_NIGHTLY_BLOB, 'UNKNOWN_LOCAL_NIGHTLY_SOURCE')
    bridge = before['bridge']
    if bridge.count(OLD_FILTER) == 1 and NEW_FILTER not in bridge:
        bridge = bridge.replace(OLD_FILTER, NEW_FILTER, 1)
    else:
        need(bridge.count(NEW_FILTER) == 1 and OLD_FILTER not in bridge, 'UNKNOWN_LOCAL_BRIDGE_FILTER')
    compile(bridge.decode('utf-8-sig'), str(paths['bridge']), 'exec')
    candidate = transport.transform(n.safe(b['transportProbe']).read_bytes())
    source = n.safe(source, True)
    payload = {name: n.safe(source / name).read_bytes() for name in
               ('no11_nightly_resume.py', 'no11_selection_status.py')}
    for name, raw in payload.items():
        compile(raw.decode('utf-8-sig'), name, 'exec')
    payload['Prepare-No11AutomaticLiveTransportResilient.ps1'] = candidate
    package_id = n.digest(n.encode({k: n.digest(v) for k, v in payload.items()}))[:20]
    package = store / ('resilience-tools-' + package_id)
    new = dict(b, transportProbe=str(package / 'Prepare-No11AutomaticLiveTransportResilient.ps1'),
               transportProbeSha256=n.digest(candidate),
               nightlyResumeTool=str(package / 'no11_nightly_resume.py'),
               nightlyResumeToolSha256=n.digest(payload['no11_nightly_resume.py']),
               nightlyResumeValidatorSha256=n.digest(payload['no11_selection_status.py']),
               bridgeSha256=n.digest(bridge))
    wrapper = n.safe(source / 'Run-No11ResumableNightly.ps1').read_bytes()
    after = {'binding': n.encode(new), 'bridge': bridge, 'nightly': wrapper}
    white = n.safe(store / 'oneclick/Start-No11OneClick.ps1')
    return paths, before, after, package, payload, n.digest(white.read_bytes())


def parse_powershell(files):
    for path in files:
        # Argument passed separately; no path interpolation into a command body.
        # Use -File with a tiny parser harness, avoiding -Command argument quoting.
        with tempfile.TemporaryDirectory(prefix='ark-parse-') as tmp:
            harness = Path(tmp) / 'parse.ps1'
            harness.write_text("param([string]$Target)\n$t=$null;$e=$null;[void][Management.Automation.Language.Parser]::ParseFile($Target,[ref]$t,[ref]$e);if($e.Count){exit 2}\n", encoding='utf-8')
            r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(harness), '-Target', str(path)], capture_output=True, timeout=30, check=False)
            need(r.returncode == 0, 'POWERSHELL_PARSE_FAILED')


def install(store, source, do_apply=False):
    store = n.safe(store, True)
    journal = store / 'resilience-install-transaction.json'
    with n.exclusive(store / 'resilience-installer.lock'):
        if do_apply:
            quiet()
        if restore_or_verify(store, journal, do_apply):
            return 'ALREADY_APPLIED'
        paths, before, after, package, payload, white_sha = plan(store, source)
        if not do_apply:
            return 'READY'
        package.mkdir(exist_ok=True)
        n.safe(package, True)
        for name, raw in payload.items():
            dest = package / name
            if dest.exists() or dest.is_symlink():
                need(n.safe(dest).read_bytes() == raw, 'IMMUTABLE_PACKAGE_CONFLICT')
            else:
                candidate = None
                try:
                    with tempfile.NamedTemporaryFile('wb', dir=package, delete=False) as f:
                        candidate = Path(f.name)
                        f.write(raw); f.flush(); os.fsync(f.fileno())
                    # Publish complete bytes only. Existing destinations never overwritten.
                    os.link(candidate, dest)
                finally:
                    if candidate is not None:
                        candidate.unlink(missing_ok=True)
        parse_powershell([package / 'Prepare-No11AutomaticLiveTransportResilient.ps1',
                          n.safe(Path(source) / 'Run-No11ResumableNightly.ps1')])
        quiet()
        for k, path in paths.items():
            need(path.read_bytes() == before[k], 'CONCURRENT_EDIT')
        entries = {k: {field: base64.b64encode(raw).decode('ascii') for field, raw in
                       (('before', before[k]), ('after', after[k]))} for k in paths}
        j = {'schemaId': n.SCHEMA, 'kind': 'INSTALL_WEEK_RESILIENCE', 'phase': 'PREPARED',
             'entries': entries, 'whiteSha256': white_sha, 'orderTransmission': False}
        # Exact byte backups are durably journalled BEFORE replacing anything.
        n.atomic(journal, j)
        try:
            for k in ('nightly', 'bridge', 'binding'):
                if before[k] != after[k]:
                    replace(paths[k], before[k], after[k])
            need(n.digest(n.safe(store / 'oneclick/Start-No11OneClick.ps1').read_bytes()) == white_sha, 'WHITE_UI_CHANGED')
            for k, path in paths.items():
                need(path.read_bytes() == after[k], 'POSTINSTALL_READBACK')
            j['phase'] = 'COMPLETE'
            n.atomic(journal, j)
        except Exception:
            restore_or_verify(store, journal, True)
            raise
        return 'PASS'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store', type=Path, required=True)
    p.add_argument('--source-dir', type=Path, default=Path(__file__).parent)
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    try:
        need(os.name == 'nt', 'WINDOWS_ONLY')
        print('NO11_WEEK_RESILIENCE_INSTALL=' + install(a.store, a.source_dir, a.apply))
    except Exception as e:
        import re
        reason = str(e)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+', reason):
            reason = 'NO11_RESILIENCE_INSTALL_SOURCE_OR_RUNTIME_UNVERIFIED'
        print('NO11_WEEK_RESILIENCE_INSTALL=BLOCKED|' + reason)
        raise SystemExit(2)
    finally:
        print('WHITE_UI_CHANGED=False\nTRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')

if __name__ == '__main__':
    main()
