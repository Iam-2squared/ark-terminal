"""Scoped after-hours source-guard installer, NEVER a Trade retry or order action.

Only the installed bootstrap weekly source selection is updated. Frozen
strategy, sender, MSII validator, original weekly validator, white OneClick UI,
three workbooks, settings, binding, receipts and same-day trading markers stay.
Default is read-only audit; apply is explicit, journaled and off-market only.
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
import no11_weekly_filtered_lineage as patch

JOURNAL = 'weekly-filtered-lineage-v1-install.json'
KIND = 'ARK_NO11_WEEKLY_FILTERED_LINEAGE_INSTALL_V1'
KNOWN_ORIGINAL_BLOB = '19f006b08f6687db0bfea67b9bd7519d77957ce4'
# Exact original plus the already-installed RSS funding transform from
# no11-rss-funding-live-20261103/patches.py:change_bootstrap. Never remove that
# funding contract while repairing the independent weekly-source boundary.
KNOWN_RSS_FUNDING_BLOB = '011171c82c960e3b2a8f520439e3e609b2578607'
KNOWN_BOOTSTRAP_BLOBS = frozenset((KNOWN_ORIGINAL_BLOB, KNOWN_RSS_FUNDING_BLOB))
KNOWN_NATIVE_BLOB = 'b777b944379c7c6dda15eac10ddda5959ab181c8'


def need(ok, why):
    if not ok:
        raise ValueError('NO11_WEEKLY_FILTER_INSTALL_' + why)


def b64(raw):
    return base64.b64encode(raw).decode('ascii')


def raw(s):
    return base64.b64decode(s, validate=True)


def git_blob(source):
    _, text, _ = patch.norm(source)
    data = text.encode('utf-8')
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def safe_source(store):
    binding_path = n.safe(store / 'automatic-inputs.json')
    settings_path = n.safe(store / 'settings.json')
    binding = n.read(binding_path)
    settings = n.read(settings_path)
    need(binding.get('schemaId') == 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' and
         binding.get('orderTransmission') is False, 'BINDING_CONTRACT')
    need(settings.get('schemaId') == 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' and
         settings.get('orderTransmission') is False and
         settings.get('automaticOrderAuthorization') is False and
         settings.get('sameDayApprovalRequired') is True and
         settings.get('normalMaxPositions') == 3, 'SETTINGS_SAFETY')
    engine = n.safe(binding['engine'], True)
    entry = n.safe(engine / 'tools/no11_received_session_bootstrap.py')
    native = n.safe(engine / 'tools/no11_verified_weekly_shadow_scope.mjs')
    need(git_blob(native.read_bytes()) == KNOWN_NATIVE_BLOB, 'NATIVE_WEEKLY_SOURCE_CHANGED')
    white = n.safe(store / 'oneclick/Start-No11OneClick.ps1')
    sender = n.safe(engine / 'windows/Invoke-No11MsiiOrder.ps1')
    js = n.safe(engine / 'tools/no11_msii_transport.mjs')
    return entry, {str(p): n.digest(p.read_bytes())
                   for p in (binding_path, settings_path, native, white, sender, js)}


def plan(store):
    entry, frozen = safe_source(store)
    current = entry.read_bytes()
    need(git_blob(current) in KNOWN_BOOTSTRAP_BLOBS, 'UNKNOWN_INSTALLED_BOOTSTRAP')
    target = patch.transform(current)
    need(target != current and patch.MARK.encode() in target, 'PATCH_SOURCE_SCOPE')
    ast.parse(target.decode('utf-8-sig'))
    return {'schemaId': n.SCHEMA, 'kind': KIND,
            'phase': 'PREPARED', 'orderTransmission': False,
            'sourcePath': str(entry), 'before': b64(current),
            'after': b64(target), 'beforeSha256': n.digest(current),
            'afterSha256': n.digest(target), 'frozen': frozen}


def verify(j):
    need(j.get('schemaId') == n.SCHEMA and j.get('kind') == KIND and
         j.get('orderTransmission') is False and
         j.get('phase') in ('PREPARED', 'COMPLETE'), 'JOURNAL_CONTRACT')
    before, after = raw(j['before']), raw(j['after'])
    need(n.digest(before) == j['beforeSha256'] and
         n.digest(after) == j['afterSha256'] and
         git_blob(before) in KNOWN_BOOTSTRAP_BLOBS and
         patch.transform(before) == after and
         patch.transform(after) == after, 'JOURNAL_SOURCE_NOT_PINNED')
    source = n.safe(j['sourcePath'])
    current = source.read_bytes()
    need(current in (before, after), 'INSTALLED_SOURCE_CHANGED')
    if j['phase'] == 'COMPLETE':
        need(current == after, 'COMPLETED_SOURCE_CHANGED')
    for path, sha in j['frozen'].items():
        need(n.digest(n.safe(path).read_bytes()) == sha, 'FROZEN_FILE_CHANGED')
    return before, after


def _quiet_oneclick():
    # Distinct from n.no_workers(): OneClick's desktop UI process remains open
    # even while idle. It must be closed before changing code it might read.
    script = r"""$ErrorActionPreference='Stop'
try{
 $x=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
  $_.Name -match '^(powershell|pwsh)([.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1'
 })
 if($x.Count){exit 2}
 exit 0
}catch{exit 3}
"""
    with tempfile.TemporaryDirectory(prefix='ark-weekly-lineage-quiet-') as tmp:
        f = Path(tmp) / 'quiet.ps1'
        f.write_text(script, encoding='ascii')
        cp = subprocess.run(
            ['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy',
             'Bypass','-File',str(f)], capture_output=True, timeout=40, check=False)
    need(cp.returncode == 0, 'CLOSE_ONECLICK_OR_PROCESS_CHECK_FAILED')


def _no_market_window():
    jst = datetime.now(timezone(timedelta(hours=9))).time()
    need(not (time(8, 0) <= jst <= time(15, 30)), 'OFF_MARKET_INSTALL_ONLY')


def _replace_exact(entry, before, after):
    need(entry.read_bytes() == before, 'CONCURRENT_LOCAL_SOURCE_CHANGE')
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=entry.parent,
                                         prefix='.week-filtered-', delete=False) as f:
            tmp = Path(f.name)
            f.write(after)
            f.flush()
            os.fsync(f.fileno())
        need(entry.read_bytes() == before, 'CONCURRENT_LOCAL_SOURCE_CHANGE')
        os.replace(tmp, entry)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def install(store, apply=False, test=False):
    store = n.safe(store, True)
    journal = store / JOURNAL
    if not apply:
        if journal.exists():
            j = n.checkpoint(journal)
            verify(j)
            return 'ALREADY_APPLIED' if j['phase'] == 'COMPLETE' else 'INTERRUPTED_REQUIRES_APPLY'
        plan(store)  # audit only: no changes or private artifact creation
        return 'READY'
    with n.exclusive(store / 'unified-refresh-install.lock'):
        if not test:
            _no_market_window()
            n.no_workers()
            _quiet_oneclick()
        if journal.exists():
            j = n.checkpoint(journal)
        else:
            j = plan(store)
            n.atomic(journal, j)  # durable journal BEFORE any source change
        before, after = verify(j)
        if j['phase'] == 'COMPLETE':
            return 'ALREADY_APPLIED'
        entry = n.safe(j['sourcePath'])
        if entry.read_bytes() == before:
            _replace_exact(entry, before, after)
        need(entry.read_bytes() == after, 'INSTALL_READBACK_UNVERIFIED')
        j['phase'] = 'COMPLETE'
        n.atomic(journal, j)
        verify(j)
        return 'PASS'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        need(os.name == 'nt', 'WINDOWS_REQUIRED')
        status = install(args.store, args.apply)
        print('NO11_WEEKLY_FILTERED_LINEAGE_INSTALL=' + status)
        print('ORIGINAL_16_HEX_SOURCE_VALIDATOR=UNCHANGED')
        print('FILTERED_64_HEX_LINEAGE=EXACT_REPORT_AND_MASTER_PROOF')
        print('FROZEN_NATIVE_PLAN_VALIDATION=RETAINED')
        print('SAME_DAY_TRADE_RESTARTED=False')
        print('ORIGINAL_WORKBOOKS_OR_SETTINGS_CHANGED=False')
    except Exception as exc:
        reason = str(exc)
        if re.fullmatch(r'NO11_[A-Z0-9_]+', reason) is None:
            reason = 'NO11_WEEKLY_FILTER_INSTALL_UNKNOWN_SOURCE_OR_IO'
        print('NO11_WEEKLY_FILTERED_LINEAGE_INSTALL=BLOCKED|' + reason)
        raise SystemExit(2)
    finally:
        print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    main()
