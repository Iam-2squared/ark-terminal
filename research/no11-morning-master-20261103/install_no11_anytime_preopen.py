"""After-hours, crash-resumable OneClick same-day standby migration.

Only installs a NEW read-only display module/contract, a source-verified standby
worker and a narrowly modified existing white launcher. Historical V2/overlay
journals, sidecars and all orders, ledgers, claims, Excel and broker files stay
byte-for-byte unchanged. Audit (the default) performs no writes or processes.
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
import sys

import install_no11_oneclick_display_v2 as original
import install_no11_oneclick_display_overlay_compat as overlay
import no11_anytime_preopen as widening
import no11_nightly_resume as n
import no11_oneclick_display_transform as migration

KIND = 'ARK_NO11_ANYTIME_SAME_DAY_STANDBY_INSTALL_V1'
JOURNAL = 'oneclick-anytime-standby-v1-install.json'
WORKER = 'Start-No11PreopenStandby.ps1'
LAUNCHER = 'Start-No11OneClick.ps1'
NATIVE = 'oneclick_status.py'
OLD_DISPLAY = original.DISPLAY
OLD_CONTRACT = original.CONTRACT
NEW_DISPLAY = 'no11_oneclick_display_anytime.py'
NEW_CONTRACT = 'oneclick-display-anytime.contract.json'
NEW_CONTRACT_SCHEMA = 'ARK_NO11_ONECLICK_DISPLAY_ANYTIME_INSTALL_V1'
HISTORICAL_DISPLAY_SHA256 = '47e9161e40eaa81294eaa7faa437eeb6a26753ef3c703cebaa3bd0035694dd55'
WORKER_GIT_BLOB = 'bc474fdf36c903ccb87018f2549f6a6b7ca398df'
NAMES = (NEW_DISPLAY, NEW_CONTRACT, WORKER, LAUNCHER)
BEFORE = (WORKER, LAUNCHER)
JST = timezone(timedelta(hours=9))
# The previous overlay receipt already proves the complete installed launcher.
# Never match/overwrite the local body of the original if/elseif chain:
# only splice the exact first keyword installed by that proven recipe.
OVERLAY_OLD = overlay.OLD_OVERLAY
OVERLAY_NEW = """  # ARK_NO11_ANYTIME_STANDBY_OVERLAY_COPY_V1
  if($view.phase -in @('BEFORE_OPEN','PREOPEN') -and ($preopen -or $reserved)){
       $disabledTradeOverlay.Text=if($preopen){'STANDBY READY  /  09:00'}else{[string]$view.trading}
   }
   elseif($trading -match 'ENTRY HALTED'){"""


def need(ok, code):
    if not ok:
        raise ValueError('NO11_ANYTIME_INSTALL_' + code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    raw = data.decode('utf-8-sig').replace('\r\n', '\n').encode('utf-8')
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def decode_bytes(value):
    need(type(value) is str, 'B64_TYPE')
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error):
        need(False, 'B64_INVALID')
    need(0 < len(data) < 2_000_000, 'B64_SIZE')
    return data


def checked_path(home, name, *, exists=True):
    need(name in NAMES or name in (NATIVE, OLD_DISPLAY, OLD_CONTRACT),
         'UNAPPROVED_PATH')
    path = home / name
    need(path.parent == home and not path.is_symlink(), 'UNSAFE_PATH')
    if exists:
        return n.safe(path)
    need(not path.exists() and not path.is_symlink(), 'UNRECOGNIZED_EXISTING_SIDECAR')
    return path


def original_chain(store):
    """Prove BOTH historical migration receipts from their original bytes."""
    store = n.safe(store, True)
    home, launcher, legacy, engine, external = original.context(store)
    need(launcher == checked_path(home, LAUNCHER) and
         legacy == checked_path(home, NATIVE), 'NATIVE_SOURCE_SCOPE')
    base_path = n.safe(store / original.JOURNAL)
    base = n.checkpoint(base_path)
    need(base.get('schemaId') == n.SCHEMA and base.get('kind') == original.KIND
         and base.get('phase') == 'COMPLETE' and base.get('orderTransmission') is False
         and base.get('home') == str(home) and base.get('launcher') == str(launcher),
         'BASE_RECEIPT_INVALID')
    first = decode_bytes(base.get('before'))
    second = decode_bytes(base.get('after'))
    need(migration.MARK.encode() not in first and
         migration.transform(first) == second and
         migration.transform(second) == second, 'BASE_DERIVATION_CHANGED')
    extras = base.get('sidecars')
    need(type(extras) is dict and set(extras) == {OLD_DISPLAY, OLD_CONTRACT},
         'BASE_SIDECAR_SET')
    original_display = decode_bytes(extras[OLD_DISPLAY])
    original_contract = decode_bytes(extras[OLD_CONTRACT])
    # Only the independently reviewed historic payload or this pinned release.
    published = Path(original.__file__).with_name(OLD_DISPLAY).read_bytes()
    need(sha(original_display) in {sha(published), HISTORICAL_DISPLAY_SHA256},
         'UNREVIEWED_DISPLAY_SOURCE')
    legacy_sha = sha(legacy.read_bytes())
    expected_contract = {
        'schemaId': 'ARK_NO11_ONECLICK_DISPLAY_INSTALL_V2',
        'displaySha256': sha(original_display),
        'legacyStatusSha256': legacy_sha,
        'orderTransmission': False,
        'authorizationSourceChanged': False,
    }
    need(original_contract == n.encode(expected_contract),
         'BASE_CONTRACT_TAMPERED')
    need(checked_path(home, OLD_DISPLAY).read_bytes() == original_display and
         checked_path(home, OLD_CONTRACT).read_bytes() == original_contract,
         'BASE_SIDECAR_BYTES_CHANGED')
    receipt_path = n.safe(store / overlay.JOURNAL)
    receipt = n.checkpoint(receipt_path)
    expected_launcher = overlay.change(second)
    need(receipt.get('schemaId') == n.SCHEMA and
         receipt.get('kind') == overlay.KIND and
         receipt.get('phase') == 'COMPLETE' and
         receipt.get('tradeStarted') is False and
         receipt.get('orderTransmission') is False and
         receipt.get('home') == str(home) and
         receipt.get('launcher') == str(launcher) and
         receipt.get('originalDisplayJournalSha256') == sha(base_path.read_bytes()) and
         receipt.get('originalNativeStatusSha256') == legacy_sha and
         receipt.get('originalLauncherSha256') == sha(second) and
         receipt.get('updatedLauncherSha256') == sha(expected_launcher) and
         decode_bytes(receipt.get('before')) == second and
         decode_bytes(receipt.get('after')) == expected_launcher,
         'OVERLAY_CHAIN_CHANGED')
    return {
        'home': home, 'launcher': launcher, 'legacy': legacy,
        'worker': checked_path(home, WORKER),
        'originalDisplay': original_display,
        'originalContract': original_contract,
        'oldLauncher': expected_launcher,
        'baseJournalSha256': sha(base_path.read_bytes()),
        'overlayJournalSha256': sha(receipt_path.read_bytes()),
        'nativeStatusSha256': legacy_sha,
        'settingsSha256': sha(n.safe(store / 'settings.json').read_bytes()),
        'bindingSha256': sha(n.safe(store / 'automatic-inputs.json').read_bytes()),
    }


def derive(chain, worker_before):
    need(git_blob(worker_before) == WORKER_GIT_BLOB, 'WORKER_NOT_PINNED_RELEASE')
    before_ui = chain['oldLauncher']
    newer_worker = widening.worker(worker_before)
    newer_ui = widening.ui(before_ui)
    # Old display and its own old contract remain immutable. The new module
    # carries its own explicit contract, derived from the proven old module.
    newer_display = widening.display(chain['originalDisplay'])
    source = newer_display.decode('utf-8-sig')
    need(source.count("CONTRACT = 'ARK_NO11_ONECLICK_DISPLAY_INSTALL_V2'") == 1 and
         source.count("'oneclick-display-v2.contract.json'") == 1, 'DISPLAY_CONTRACT_ANCHOR')
    source = source.replace("CONTRACT = 'ARK_NO11_ONECLICK_DISPLAY_INSTALL_V2'",
                            "CONTRACT = '" + NEW_CONTRACT_SCHEMA + "'", 1)
    source = source.replace("'oneclick-display-v2.contract.json'",
                            "'" + NEW_CONTRACT + "'", 1)
    need("CONTRACT = '" + NEW_CONTRACT_SCHEMA + "'" in source and
         "home / '" + NEW_CONTRACT + "'" in source, 'DISPLAY_CONTRACT_REWRITE')
    newer_display = (b'\xef\xbb\xbf' if newer_display.startswith(b'\xef\xbb\xbf') else b'') + source.encode('utf-8')
    ast.parse(newer_display.decode('utf-8-sig'))
    contract = n.encode({
        'schemaId': NEW_CONTRACT_SCHEMA,
        'displaySha256': sha(newer_display),
        'legacyStatusSha256': chain['nativeStatusSha256'],
        'orderTransmission': False,
        'authorizationSourceChanged': False,
    })
    old_tool = "$statusTool=Join-Path $PSScriptRoot 'no11_oneclick_display_v2.py'"
    new_tool = "$statusTool=Join-Path $PSScriptRoot '" + NEW_DISPLAY + "'"
    canonical_ui = newer_ui.decode('utf-8-sig').replace('\r\n', '\n')
    need(canonical_ui.count(old_tool) == 1 and new_tool not in canonical_ui,
         'LAUNCHER_DISPLAY_SOURCE_CHANGED')
    from no11_oneclick_display_transform import replace_regions
    newer_ui_text = replace_regions(newer_ui.decode('utf-8-sig'), [
        (old_tool, new_tool),
        (OVERLAY_OLD, OVERLAY_NEW),
    ])
    newer_ui = (b'\xef\xbb\xbf' if newer_ui.startswith(b'\xef\xbb\xbf') else b'') + newer_ui_text.encode('utf-8')
    # All original Enabled lines and actions remain identical even after V2.
    for token in (b'$trade.Enabled=', b'$nightly.Enabled=', b'$review.Enabled=',
                  b'$trade.Add_Click({', b'$nightly.Add_Click({',
                  b'$review.Add_Click({', b'$refresh.Add_Click({RefreshUi})'):
        previous = [r for r in before_ui.splitlines() if token in r]
        current = [r for r in newer_ui.splitlines() if token in r]
        need(previous and previous == current, 'TRADE_ACTION_OR_PERMISSION_CHANGED')
    need(before_ui != newer_ui, 'NO_LAUNCHER_DELTA')
    return {NEW_DISPLAY: newer_display, NEW_CONTRACT: contract,
            WORKER: newer_worker, LAUNCHER: newer_ui}


def record_from(chain, worker_before, after):
    return {
        'schemaId': n.SCHEMA, 'kind': KIND, 'phase': 'PREPARED',
        'orderTransmission': False, 'tradeStarted': False,
        'home': str(chain['home']), 'launcher': str(chain['launcher']),
        'baseJournalSha256': chain['baseJournalSha256'],
        'overlayJournalSha256': chain['overlayJournalSha256'],
        'nativeStatusSha256': chain['nativeStatusSha256'],
        'before': {
            WORKER: base64.b64encode(worker_before).decode('ascii'),
            LAUNCHER: base64.b64encode(chain['oldLauncher']).decode('ascii'),
        },
        'after': {name: base64.b64encode(after[name]).decode('ascii')
                  for name in NAMES},
        'fileSha256': {name: sha(after[name]) for name in NAMES},
        'historicalSidecarsAndJournalsPreserved': True,
        'brokerAuthorityChanged': False,
    }


def validate_plan(chain, saved):
    need(saved.get('schemaId') == n.SCHEMA and saved.get('kind') == KIND and
         saved.get('phase') in ('PREPARED', 'COMPLETE') and
         saved.get('orderTransmission') is False and
         saved.get('tradeStarted') is False and
         saved.get('historicalSidecarsAndJournalsPreserved') is True and
         saved.get('brokerAuthorityChanged') is False and
         saved.get('home') == str(chain['home']) and
         saved.get('launcher') == str(chain['launcher']) and
         saved.get('baseJournalSha256') == chain['baseJournalSha256'] and
         saved.get('overlayJournalSha256') == chain['overlayJournalSha256'] and
         saved.get('nativeStatusSha256') == chain['nativeStatusSha256'],
         'JOURNAL_IDENTITY_CHANGED')
    b = saved.get('before')
    a = saved.get('after')
    need(type(b) is dict and set(b) == set(BEFORE) and
         type(a) is dict and set(a) == set(NAMES) and
         type(saved.get('fileSha256')) is dict and
         set(saved['fileSha256']) == set(NAMES), 'JOURNAL_FILE_SET')
    original_worker = decode_bytes(b[WORKER])
    original_ui = decode_bytes(b[LAUNCHER])
    need(original_ui == chain['oldLauncher'], 'JOURNAL_BASE_LAUNCHER_CHANGED')
    expected = derive(chain, original_worker)
    for name in NAMES:
        need(decode_bytes(a[name]) == expected[name] and
             saved['fileSha256'][name] == sha(expected[name]),
             'JOURNAL_DERIVATION_CHANGED')
    return original_worker, expected


def audit(store):
    """Read-only: proves old chain, new journal and ALL installed target bytes."""
    store = n.safe(store, True)
    chain = original_chain(store)
    receipt_path = store / JOURNAL
    has_receipt = receipt_path.exists() or receipt_path.is_symlink()
    if has_receipt:
        saved = n.checkpoint(n.safe(receipt_path))
        old_worker, after = validate_plan(chain, saved)
    else:
        old_worker = chain['worker'].read_bytes()
        after = derive(chain, old_worker)
        saved = record_from(chain, old_worker, after)
    for name in NAMES:
        path = checked_path(chain['home'], name, exists=False) if name in (
            NEW_DISPLAY, NEW_CONTRACT) and not (chain['home'] / name).exists() else chain['home'] / name
        need(not path.is_symlink(), 'UNSAFE_TARGET')
        current = path.read_bytes() if path.exists() else None
        before = (old_worker if name == WORKER else
                  chain['oldLauncher'] if name == LAUNCHER else None)
        if has_receipt:
            need(current == after[name] if saved['phase'] == 'COMPLETE'
                 else current in (before, after[name]), 'INSTALLED_BYTES_MISMATCH')
        else:
            need(current == before, 'UNKNOWN_EXISTING_SOURCE_OR_SIDECAR')
    if not has_receipt:
        return 'READY_NOT_APPLIED', saved
    if saved['phase'] == 'COMPLETE':
        return 'ALREADY_APPLIED', saved
    return 'INTERRUPTED_REQUIRES_APPLY', saved


def gate_probe():
    """Reproduce the original process predicate from inside the installer.

    No changes to original.gate, order permissions, filesystem or broker data.
    Raw process command lines are never reported.
    """
    need(os.name == 'nt', 'GATE_PROBE_WINDOWS_ONLY')
    script = r"""$ErrorActionPreference='Stop'
try {
 $all=@(Get-CimInstance Win32_Process -ErrorAction Stop)
 if($all.Count -eq 0){exit 5}
 $p=@($all|Where-Object{
   $_.ProcessId -notin @($PID,OWN_PROCESS,PARENT_PROCESS) -and
   $_.Name -match '^(powershell|pwsh|python|pythonw|node)([.]exe)?$'
 })
 $bad=@($p|Where-Object{[string]::IsNullOrWhiteSpace([string]$_.CommandLine)})
 $pattern='(?i)no11_|No11|no12.*(nightly|collector)|OperatorLive[.]ps1|[\\/]controller[.]py|launcher_automatic_bridge|prestart-retry'
 $hits=@($p|Where-Object{[string]$_.CommandLine -match $pattern})
 Write-Output ('NO11_GATE_UNREADABLE='+$bad.Count)
 Write-Output ('NO11_GATE_MATCHES='+$hits.Count)
 foreach($hit in ($hits|Sort-Object ProcessId)){
   $cmd=[string]$hit.CommandLine
   $class=if($cmd -match 'no11_received_session_controller|OperatorLive|Probe-No11Chart50'){'LIVE'}
     elseif($cmd -match 'no11_nightly_resume|Run-No11NightlyCycle'){'NIGHTLY'}
     elseif($cmd -match 'Start-No11OneClick|Start-No11PreopenStandby'){'ONECLICK'}
     elseif($cmd -match 'Bootstrap-No11AnytimeStandby|install_no11_anytime_preopen'){'INSTALLER'}
     else{'OTHER'}
   Write-Output ('NO11_GATE_MATCH=PID='+$hit.ProcessId+'|PPID='+$hit.ParentProcessId+'|CLASS='+$class)
 }
 exit 0
}catch{exit 4}
""".replace('OWN_PROCESS', str(os.getpid())).replace('PARENT_PROCESS', str(os.getppid()))
    with tempfile.TemporaryDirectory(prefix='ark-gate-probe-') as tmp:
        path = Path(tmp) / 'probe.ps1'
        path.write_text(script, encoding='ascii')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                                 '-ExecutionPolicy', 'Bypass', '-File', str(path)],
                                capture_output=True, text=True, timeout=30, check=False)
    need(result.returncode == 0, 'GATE_PROBE_PROCESS_QUERY_FAILED')
    for line in result.stdout.splitlines():
        need(re.fullmatch(r'NO11_GATE_(?:UNREADABLE|MATCHES)=[0-9]{1,7}', line)
             or re.fullmatch(r'NO11_GATE_MATCH=PID=[0-9]{1,10}\|PPID=[0-9]{1,10}\|CLASS=(?:LIVE|NIGHTLY|ONECLICK|INSTALLER|OTHER)', line),
             'GATE_PROBE_INVALID_OUTPUT')
        print(line)
    print('NO11_GATE_PROBE=READ_ONLY')
    return 0


def gate():
    original.gate()
    # Original gate checks Windows, 08:00–15:40 exclusion and active ARK/OneClick
    # process command lines. A running broker/execution service must remain OFF.


def create_once(path, data):
    need(not path.exists() and not path.is_symlink(), 'SIDECAR_CONCURRENTLY_CREATED')
    with path.open('xb') as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    need(n.safe(path).read_bytes() == data, 'SIDECAR_READBACK_FAILED')


def install(store, *, apply=False):
    state, record = audit(store)
    if not apply:
        return state
    gate()
    store = n.safe(store, True)
    with n.exclusive(store / 'unified-refresh-install.lock'):
        gate()
        state, record = audit(store)
        if state == 'ALREADY_APPLIED':
            return state
        chain = original_chain(store)
        old_worker, after = validate_plan(chain, record)
        original.parse_launcher(after[LAUNCHER])
        # Prepare and seal ALL before/after bytes BEFORE modifying installed UI.
        receipt = store / JOURNAL
        if not receipt.exists():
            n.atomic(receipt, record)
        state, record = audit(store)
        need(state == 'INTERRUPTED_REQUIRES_APPLY', 'JOURNAL_PREPARE_FAILED')
        for name in (NEW_DISPLAY, NEW_CONTRACT):
            gate()
            state, record = audit(store)
            path = chain['home'] / name
            if not path.exists():
                create_once(path, after[name])
            need(n.safe(path).read_bytes() == after[name], 'NEW_SIDECAR_CHANGED')
        for name in (WORKER, LAUNCHER):
            gate()
            state, record = audit(store)
            path = chain['home'] / name
            before = old_worker if name == WORKER else chain['oldLauncher']
            if path.read_bytes() == before:
                original.replace_exact(path, before, after[name])
            need(n.safe(path).read_bytes() == after[name], 'INSTALLED_READBACK_FAILED')
        state, record = audit(store)
        need(state == 'INTERRUPTED_REQUIRES_APPLY', 'PRE_COMPLETE_CHECK_FAILED')
        finished = dict(record, phase='COMPLETE')
        n.atomic(receipt, finished)
        need(audit(store)[0] == 'ALREADY_APPLIED', 'POSTINSTALL_RECHECK_FAILED')
        return 'APPLIED_NO_TRADE'


def diagnose(store):
    """Read-only stage isolation. Never prints receipt bytes, paths or private data."""
    def probe(label, callback):
        try:
            result = callback()
        except Exception as error:
            code = str(error)
            if re.fullmatch(r'NO11_[A-Z0-9_]{1,160}', code) is None:
                code = 'NO11_ANYTIME_DIAGNOSTIC_UNVERIFIED'
            print('NO11_ANYTIME_DIAG_' + label + '=BLOCKED|' + code)
            return None
        print('NO11_ANYTIME_DIAG_' + label + '=PASS')
        return result

    store = probe('STORE', lambda: n.safe(store, True))
    if store is None:
        return 2
    original_context = probe('ORIGINAL_CONTEXT', lambda: original.context(store))
    if original_context is None:
        return 2
    home, launcher, legacy, engine, _external = original_context
    base_path = probe('V2_RECEIPT_PATH', lambda: n.safe(store / original.JOURNAL))
    if base_path is None:
        return 2
    base = probe('V2_RECEIPT_SEAL', lambda: n.checkpoint(base_path))
    if base is None:
        return 2
    first = probe('V2_BEFORE_DECODE', lambda: decode_bytes(base.get('before')))
    second = probe('V2_AFTER_DECODE', lambda: decode_bytes(base.get('after')))
    if first is None or second is None:
        return 2
    a = probe('V2_BEFORE_DERIVATION', lambda: migration.transform(first))
    b = probe('V2_AFTER_IDEMPOTENCE', lambda: migration.transform(second))
    if a is None or b is None:
        return 2
    if a != second or b != second:
        print('NO11_ANYTIME_DIAG_V2_BYTES=BLOCKED|NO11_ANYTIME_DIAGNOSTIC_DERIVATION_CHANGED')
        return 2
    print('NO11_ANYTIME_DIAG_V2_BYTES=PASS')
    chain = probe('HISTORIC_V2_OVERLAY_CHAIN', lambda: original_chain(store))
    if chain is None:
        # The stage above already isolated V2 derivation. The remaining
        # independent receipt/sidecar checks must remain fail-closed.
        return 2
    worker_raw = probe('WORKER_FILE', lambda: chain['worker'].read_bytes())
    if worker_raw is None:
        return 2
    old_worker_sha = probe('WORKER_PIN', lambda: git_blob(worker_raw))
    if old_worker_sha != WORKER_GIT_BLOB:
        print('NO11_ANYTIME_DIAG_WORKER_RELEASE=BLOCKED|NO11_ANYTIME_INSTALL_WORKER_NOT_PINNED_RELEASE')
        return 2
    print('NO11_ANYTIME_DIAG_WORKER_RELEASE=PASS')
    if probe('WORKER_TRANSFORM', lambda: widening.worker(worker_raw)) is None:
        return 2
    if probe('ONECLICK_TRANSFORM', lambda: widening.ui(chain['oldLauncher'])) is None:
        return 2
    if probe('DISPLAY_TRANSFORM', lambda: widening.display(chain['originalDisplay'])) is None:
        return 2
    if probe('SUCCESSOR_DERIVATION', lambda: derive(chain, worker_raw)) is None:
        return 2
    verified = probe('INSTALLED_STATE_AUDIT', lambda: audit(store))
    if verified is None:
        return 2
    print('NO11_ANYTIME_DIAG_RESULT=' + verified[0])
    return 0



def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store', required=True, type=Path)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--diagnose', action='store_true')
    p.add_argument('--probe-gate', action='store_true')
    args = p.parse_args(argv)
    try:
        if args.probe_gate:
            need(not args.apply and not args.diagnose, 'PROBE_CANNOT_APPLY')
            return gate_probe()
        if args.diagnose:
            need(not args.apply, 'DIAGNOSE_CANNOT_APPLY')
            return diagnose(args.store)
        print('NO11_ANYTIME_STANDBY_INSTALL=' + install(args.store, apply=args.apply))
        print('OLD_V2_AND_OVERLAY_RECEIPTS_PRESERVED=True')
        print('OLD_DISPLAY_AND_CONTRACT_BYTES_PRESERVED=True')
        print('NATIVE_TRADE_AND_BROKER_SOURCES_UNCHANGED=True')
        return 0
    except Exception as error:
        code = str(error)
        if re.fullmatch(r'NO11_[A-Z0-9_]+', code) is None:
            code = 'NO11_ANYTIME_INSTALL_UNVERIFIED_SOURCE_OR_IO'
        print('NO11_ANYTIME_STANDBY_INSTALL=BLOCKED|' + code)
        print('DO_NOT_DELETE_OR_RESET_JOURNALS_CLAIMS_LEDGER=True')
        return 2
    finally:
        print('TRADE_STARTED=False')
        print('EXCEL_TOUCHED=False')
        print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    sys.exit(main())
