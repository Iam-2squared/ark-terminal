#!/usr/bin/env python3
"""Install/run automatic inputs from the EXISTING Trade button.

The installer never contacts Excel, changes funding, or grants an order.
Runtime builds automatic inputs. Under the same explicit Trade approval it may
pin the current physical Excel session and create the first same-day RSS broker
config; it never auto-approves independently, silently re-dates a config,
sends an order itself, or overwrites a running session's inputs.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

SCHEMA = 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
RUNNER_BLOB = '4887918a01751f5107b6d6f56c4d838d75107ed2'
AUTOMATIC_BLOB = '2ee5fd79ba8f06372585d2fdb2ea84df29b2f0a4'
ARRIVAL_SHA256 = '69f8edafb4708e9a7b61b4f85eb92f353049cf21324e1647602e9973f195f999'
ARRIVAL_BYTES = 158661
MARKER = '# ARK_NO11_AUTOMATIC_INPUT_HOOK_V1'
START = ' $file=LocalFile $cfg.bootstrapConfigFile \'LIVE_BOOTSTRAP_CONFIG\''
END = '# ARK_NO11_AUTOMATIC_INPUT_HOOK_END'
HOOK = r''' # ARK_NO11_AUTOMATIC_INPUT_HOOK_V1
 $autoBinding=Join-Path $store 'automatic-inputs.json'
 Need (Test-Path -LiteralPath $autoBinding -PathType Leaf) 'AUTOMATIC_INPUT_BINDING_MISSING'
 Need (-not (Test-Path -LiteralPath (Join-Path $store ('TRADE-'+$day+'.launch.json')))) 'TRADE_ALREADY_STARTED_NO_DUPLICATE'
 $auto=Get-Content -LiteralPath $autoBinding -Raw -Encoding UTF8|ConvertFrom-Json
 Need ($auto.schemaId -ceq 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1') 'AUTOMATIC_INPUT_BINDING_INVALID'
 $autoPython=LocalFile ([string]$auto.python) 'AUTOMATIC_PYTHON'
 $autoBridge=LocalFile ([string]$auto.bridge) 'AUTOMATIC_BRIDGE'
 Need ((Get-FileHash -LiteralPath $autoBridge -Algorithm SHA256).Hash.ToLowerInvariant() -ceq [string]$auto.bridgeSha256) 'AUTOMATIC_BRIDGE_HASH'
 $autoPrepared=''
 & $autoPython -B -X utf8 $autoBridge run --binding $autoBinding | ForEach-Object {
  $line=[string]$_
  if($line.StartsWith('AUTOSTART_LIVE_BOOTSTRAP=')){$autoPrepared=$line.Substring('AUTOSTART_LIVE_BOOTSTRAP='.Length)}
  Write-Host $line
 }
 Need ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($autoPrepared)) 'AUTOMATIC_INPUTS_OR_INITIAL_BROKER_CONNECTION_INCOMPLETE'
 $cfg.bootstrapConfigFile=LocalFile $autoPrepared 'AUTOMATIC_LIVE_BOOTSTRAP'
 # ARK_NO11_AUTOMATIC_INPUT_HOOK_END
'''


def need(ok, code):
    if not ok:
        raise ValueError('NO11_AUTOSTART_' + code)


def now():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='milliseconds')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def safe(value, directory=False):
    p = Path(value)
    need(p.is_absolute(), 'ABSOLUTE_PATH_REQUIRED')
    for q in (p, *p.parents):
        if q.exists() or q.is_symlink():
            need(not q.is_symlink() and not (getattr(q.lstat(), 'st_file_attributes', 0) & 1024), 'REPARSE_PATH')
    need(p.is_dir() if directory else p.is_file(), 'PATH_MISSING')
    return p


def load(path):
    raw = safe(path).read_bytes()
    need(0 < len(raw) < 20_000_000, 'SOURCE_SIZE')
    def pairs(values):
        d = {}
        for k, v in values:
            need(k not in d, 'DUPLICATE_JSON_KEY')
            d[k] = v
        return d
    obj = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs)
    need(type(obj) is dict, 'JSON_OBJECT_REQUIRED')
    return obj, raw


def encode(obj):
    return (json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def replace_bytes(path, raw, expected):
    current = path.read_bytes() if path.exists() else None
    need(current == expected, 'CONCURRENT_EDIT')
    temp = path.with_name(path.name + '.auto-' + uuid.uuid4().hex)
    try:
        with temp.open('xb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        # Recheck after flushing, before replacement. Install additionally blocks
        # an active launcher/controller, and runtime serializes on a local lock.
        need((path.read_bytes() if path.exists() else None) == expected, 'CONCURRENT_EDIT')
        if expected is None:
            # Avoid overwriting a file created concurrently on Windows.
            if os.name == 'nt':
                os.rename(temp, path)
            else:
                os.link(temp, path)
                temp.unlink()
        else:
            os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def patch_launcher(raw):
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text = raw[len(bom):].decode('utf-8')
    newline = '\r\n' if '\r\n' in text else '\n'
    text = text.replace('\r\n', '\n')
    need('\r' not in text, 'LAUNCHER_LINE_ENDINGS')
    need(text.count('function RunTrade(') == 1 and text.count('function RunWeekly(') == 1,
         'LAUNCHER_FUNCTIONS_CHANGED')
    start, end = text.index('function RunTrade('), text.index('function RunWeekly(')
    need(start < end, 'LAUNCHER_FUNCTION_ORDER')
    body = text[start:end]
    need(body.count(START) == 1 and "Need $approved 'TODAYS_EXPLICIT_OPERATOR_APPROVAL_REQUIRED'" in body,
         'TRADE_APPROVAL_OR_CONFIG_ANCHOR_CHANGED')
    need(body.index('Need $approved') < body.index(START), 'APPROVAL_ORDER')
    if MARKER in text:
        need(text.count(MARKER) == 1 and text.count(END) == 1 and HOOK in body,
             'PARTIAL_OR_DIFFERENT_HOOK')
        return raw
    need(END not in text and '$autoBinding=' not in text, 'PARTIAL_HOOK')
    body = body.replace(START, HOOK + START, 1)
    new = text[:start] + body + text[end:]
    return bom + new.replace('\n', newline).encode('utf-8')


def invoke(args, code):
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    if r.returncode:
        for line in (r.stdout + '\n' + r.stderr).splitlines():
            if line.startswith('NO11_'):
                print(line, flush=True)
        raise ValueError('NO11_AUTOSTART_' + code)
    return r.stdout


def assert_stopped():
    command = r"$ErrorActionPreference='Stop';$p=@(Get-CimInstance Win32_Process|Where-Object {$_.Name -match '^(pythonw?|powershell|pwsh|node)(\.exe)?$' -and $_.CommandLine -match '(Start-No11UnifiedLauncher\.ps1|Run-No11ReceivedSessionOperatorLive\.ps1|no11_received_session_controller\.py)' -and $_.ProcessId -ne $PID});if($p.Count){exit 2}"
    invoke(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command], 'CLOSE_ARK_LAUNCHER_BEFORE_INSTALL')


def parse_ps(path):
    command = "$a=$null;$b=$null;[void][Management.Automation.Language.Parser]::ParseFile('" + str(path).replace("'", "''") + "',[ref]$a,[ref]$b);if($b.Count){exit 2}"
    invoke(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command], 'POWERSHELL_SYNTAX')


def settings_contract(settings):
    need(settings.get('schemaId') == 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1'
         and settings.get('normalMaxPositions') == 3
         and settings.get('sameDayApprovalRequired') is True
         and settings.get('automaticOrderAuthorization') is False
         and settings.get('orderTransmission') is False, 'LAUNCHER_SETTINGS_CONTRACT')


def install(runner, handoff_file):
    need(os.name == 'nt', 'WINDOWS_INSTALL_ONLY')
    assert_stopped()
    runner, handoff_file = safe(runner), safe(handoff_file)
    need(blob(runner.read_bytes()) == RUNNER_BLOB, 'RUNNER_HASH')
    automatic = safe(Path(__file__).with_name('automatic_morning.py'))
    need(blob(automatic.read_bytes()) == AUTOMATIC_BLOB, 'AUTOMATIC_HASH')
    handoff, hb = load(handoff_file)
    need(handoff_file.name == 'morning-handoff-' + digest(hb) + '.json'
         and handoff.get('schemaId') == 'ARK_NO11_MORNING_MASTER_HANDOFF_V1'
         and handoff.get('orderTransmission') is False and handoff.get('productionReady') is False,
         'HANDOFF_CONTRACT')
    spec = handoff['spec']
    need(len(handoff.get('selectedSymbols', [])) >= 1, 'EMPTY_SELECTION')
    engine = safe(spec['engineRoot'], True)
    settings_file = safe(spec['settingsFile'])
    settings, settings_before = load(settings_file)
    settings_contract(settings)
    for key, sha in handoff['sourcePins'].items():
        need(digest(safe(spec[key]).read_bytes()) == sha, 'HANDOFF_SOURCE_CHANGED')
    safe(runner.parent / 'xls-reader', True)
    launcher = safe(engine / 'windows/Start-No11UnifiedLauncher.ps1')
    before = launcher.read_bytes()
    after = patch_launcher(before)
    store = safe(settings_file.parent, True)
    binding_file = store / 'automatic-inputs.json'
    if binding_file.exists():
        previous, _ = load(binding_file)
        need(previous.get('handoff') == str(handoff_file) and previous.get('runner') == str(runner),
             'EXISTING_DIFFERENT_BINDING')
        need(MARKER.encode() in before, 'BINDING_WITHOUT_HOOK')
        print('AUTOMATIC_LAUNCHER_INSTALL=ALREADY_PRESENT')
        return
    need(MARKER.encode() not in before, 'HOOK_WITHOUT_BINDING')
    work = store / ('automatic-install-' + uuid.uuid4().hex)
    work.mkdir()
    backup = work / 'Start-No11UnifiedLauncher.ps1.before'
    backup.write_bytes(before)
    need(backup.read_bytes() == before, 'BACKUP_FAILED')
    # Parse in a private candidate; self-test the real location only after apply.
    candidate = work / 'candidate.ps1'
    candidate.write_bytes(after)
    parse_ps(candidate)
    bridge = safe(Path(__file__).resolve())
    binding = {'schemaId': SCHEMA, 'sessionDate': handoff['sessionDate'],
               'handoff': str(handoff_file), 'handoffSha256': digest(hb),
               'runner': str(runner), 'runnerSha256': digest(runner.read_bytes()),
               'automatic': str(automatic), 'automaticSha256': digest(automatic.read_bytes()),
               'bridge': str(bridge), 'bridgeSha256': digest(bridge.read_bytes()),
               'python': str(Path(sys.executable).resolve()), 'engine': str(engine),
               'settings': str(settings_file), 'selectedCount': len(handoff['selectedSymbols']),
               'manualEvidenceRequired': False, 'manualPriceInputRequired': False,
               'orderTransmission': False, 'backup': str(backup)}
    bound = encode(binding)
    changed = False
    try:
        replace_bytes(binding_file, bound, None)
        replace_bytes(launcher, after, before)
        changed = True
        result = invoke(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                         'Bypass', '-File', str(launcher), '-OfflineSelfTest'], 'LAUNCHER_SELFTEST')
        need('NO11_UNIFIED_OFFLINE_SELFTEST=PASS' in result, 'LAUNCHER_SELFTEST_MARKER')
        need(settings_file.read_bytes() == settings_before, 'SETTINGS_UNEXPECTEDLY_CHANGED')
    except BaseException:
        if changed and launcher.read_bytes() == after:
            replace_bytes(launcher, before, after)
        if binding_file.exists() and binding_file.read_bytes() == bound:
            binding_file.unlink()
        raise
    print('AUTOMATIC_LAUNCHER_INSTALL=PASS')
    print('LOCAL_LAUNCHER_EDITS=PRESERVED')
    print('LAUNCHER_OFFLINE_SELFTEST=PASS')
    print('AUTOMATIC_INPUT_BINDING=' + str(binding_file))
    print('LAUNCHER_BACKUP=' + str(backup))
    print('SELECTED_SYMBOLS=' + str(binding['selectedCount']))
    print('BROKER_BOOTSTRAP_CONFIGURED=' + str(bool(settings.get('bootstrapConfigFile'))))
    print('MANUAL_EVIDENCE_REQUIRED=False\nMANUAL_PRICE_INPUT_REQUIRED=False')
    print('ACCOUNT_SETTINGS_CHANGED=False\nTRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')


@contextmanager
def lock(path):
    stream = None
    try:
        try:
            stream = path.open('xb')
        except FileExistsError:
            raise ValueError('NO11_AUTOSTART_PREPARATION_ALREADY_RUNNING_OR_INTERRUPTED') from None
        stream.write(encode({'pid': os.getpid(), 'createdAtJst': now()}))
        stream.flush()
        os.fsync(stream.fileno())
        yield
    finally:
        if stream is not None:
            stream.close()
            path.unlink()


def merge_current_broker(prepared, old, broker, day):
    need(prepared.get('sessionDate') == day and old.get('sessionDate') == day,
         'BROKER_MUST_BE_CURRENT_SESSION')
    need(prepared.get('schemaId') == 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1'
         and prepared.get('productionReady') is False and prepared.get('orderTransmission') is False
         and 'brokerExecutionConfig' not in prepared and 'shadowAccountConfig' not in prepared,
         'AUTOMATIC_BOOTSTRAP_CONTRACT')
    need(old.get('orderTransmission') is False and old.get('productionReady') is False,
         'EXISTING_BOOTSTRAP_MODE')
    need(broker.get('schemaId') == 'ARK_NO11_BROKER_EXECUTION_CONFIG_V1'
         and broker.get('sessionDate') == day and broker.get('fundingPolicy') == 'RSS_BUYING_POWER'
         and broker.get('feeCourse') == 'ZERO' and broker.get('orderTransmission') is True
         and broker.get('productionReady') is False, 'EXISTING_RSS_BROKER_REQUIRED')
    transport, ledger, terms = broker.get('transport', {}), broker.get('ledger', {}), broker.get('orderTerms', {})
    need(transport.get('sessionDate') == day and transport.get('mode') == 'LIVE'
         and transport.get('operatorEnabled') is True and transport.get('approvedForSession') is True
         and transport.get('orderTransmission') is True, 'EXISTING_SESSION_TRANSPORT_REQUIRED')
    need(ledger.get('maxSymbols') == 3 and ledger.get('lotSize') == 100
         and ledger.get('account') == '一般' and ledger.get('allocatedCashJpy') == 'AUTO_RSS_BUYING_POWER'
         and terms.get('sor') is True and terms.get('accountType') == 1
         and terms.get('accountTypeVerified') is True and terms.get('orderType') == 'MARKET'
         and terms.get('timeInForce') == 'DAY', 'ORIGINAL_ACCOUNT_CAPITAL_TERMS')
    for key in ('orderIdWorkbookPath', 'runtimeRoot', 'h235ModelRoot', 'precomputedChartReceipt',
                'precomputedG1Mask', 'weeklySourceRun'):
        need(prepared.get(key) == old.get(key), 'OLD_AND_PREPARED_INPUT_SCOPE_DIFFERS')
    need(transport.get('workbookPath') == prepared.get('orderIdWorkbookPath'), 'PHYSICAL_BOOK_DIFFERS')
    merged = dict(prepared)
    # Preserve session/ledger location and collector parameters, not just broker settings.
    merged['privateRoot'] = old['privateRoot']
    merged['brokerExecutionConfig'] = old['brokerExecutionConfig']
    for key in ('samples', 'historyBars', 'warmupSeconds'):
        if key in old:
            merged[key] = old[key]
    return merged



def discover_original_arrival(root):
    root = safe(root, True)
    matches, visited = [], 0
    for parent, dirs, files in os.walk(root):
        base = Path(parent)
        dirs[:] = [d for d in dirs if not (base / d).is_symlink()]
        for name in files:
            visited += 1
            need(visited <= 100000, 'ORIGINAL_ARRIVAL_SEARCH_LIMIT')
            candidate = base / name
            try:
                if candidate.is_symlink() or candidate.stat().st_size != ARRIVAL_BYTES:
                    continue
                if digest(candidate.read_bytes()) == ARRIVAL_SHA256:
                    matches.append(candidate.resolve(strict=True))
            except OSError:
                continue
    need(bool(matches), 'ORIGINAL_ARRIVAL_NOT_FOUND')
    # Duplicate byte-identical private copies are equivalent; select deterministically.
    return sorted(set(matches), key=lambda p: (len(str(p)), str(p).lower()))[0]


def capture_transport(binding, settings, prepared, day):
    probe = safe(binding.get('transportProbe'))
    need(digest(probe.read_bytes()) == binding.get('transportProbeSha256'),
         'TRANSPORT_PROBE_CHANGED')
    root = safe(prepared['privateRoot'], True) / 'physical-session'
    root.mkdir(exist_ok=True)
    root = safe(root, True)
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
         '-File', str(probe), '-SettingsFile', str(binding['settings']),
         '-OutputRoot', str(root), '-SessionDate', day, '-SameDayOperatorApproved'],
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    for line in (result.stdout + '\n' + result.stderr).splitlines():
        if line.startswith(('AUTOMATIC_TRANSPORT_', 'ORDER_TRIGGER_', 'ORDER_SENT=')):
            print(line, flush=True)
    need(result.returncode == 0, 'PHYSICAL_TRANSPORT_SETUP_FAILED')
    paths = [line.split('=', 1)[1] for line in result.stdout.splitlines()
             if line.startswith('AUTOMATIC_TRANSPORT=') and not line.startswith('AUTOMATIC_TRANSPORT=BLOCKED|')]
    need(len(paths) == 1, 'PHYSICAL_TRANSPORT_RECEIPT_MISSING')
    transport, _ = load(paths[0])
    return Path(paths[0]), transport


def make_initial_broker(binding, settings, prepared_file, prepared, day):
    transport_file, transport = capture_transport(binding, settings, prepared, day)
    private_base = Path(binding['settings']).resolve().parents[1]
    arrival = discover_original_arrival(private_base)
    engine = safe(binding['engine'], True)
    output = safe(prepared['privateRoot'], True) / 'rss-live'
    output.mkdir(exist_ok=True)
    output = safe(output, True)
    old_sys = list(sys.path)
    try:
        sys.path.insert(0, str(engine / 'tools'))
        import no11_make_rss_live_config as maker
        boot, broker = maker.build({
            'bootstrapInputs': prepared,
            'transport': transport,
            'originalArrivalTable': str(arrival),
        }, output, now())
    finally:
        sys.path[:] = old_sys
    print('AUTOSTART_INITIAL_PHYSICAL_TRANSPORT=' + str(transport_file), flush=True)
    print('AUTOSTART_ORIGINAL_ARRIVAL=PINNED_SHA256_' + ARRIVAL_SHA256, flush=True)
    print('AUTOSTART_INITIAL_BROKER_CONNECTION=CREATED_FROM_EXPLICIT_TRADE_APPROVAL', flush=True)
    return Path(boot), Path(broker)


def run(binding_file, same_day_operator_approved=False):
    binding_file = safe(binding_file)
    binding, _ = load(binding_file)
    need(binding.get('schemaId') == SCHEMA and binding.get('orderTransmission') is False, 'BINDING_CONTRACT')
    need(same_day_operator_approved is True, 'SAME_DAY_OPERATOR_APPROVAL_REQUIRED')
    need(type(binding.get('transportProbe')) is str and
         type(binding.get('transportProbeSha256')) is str, 'TRANSPORT_PROBE_BINDING')
    today = now()[:10]
    need(binding.get('sessionDate') == today, 'CURRENT_SESSION_HANDOFF_REQUIRED')
    store = binding_file.parent
    need(not (store / ('TRADE-' + today + '.launch.json')).exists(), 'TRADE_ALREADY_STARTED')
    for key in ('bridge', 'automatic', 'runner', 'handoff'):
        need(digest(safe(binding[key]).read_bytes()) == binding[key + 'Sha256'], 'BOUND_SOURCE_CHANGED')
    settings, settings_before = load(binding['settings'])
    settings_contract(settings)
    with lock(store / 'automatic-inputs.lock'):
        module_spec = importlib.util.spec_from_file_location('ark_automatic_entry', binding['automatic'])
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        m = module.load_runner(binding['runner'])
        prepared_file = module.execute(m, Path(binding['handoff']))
        need(prepared_file is not None, 'AUTOMATIC_INPUTS_UNAVAILABLE')
        prepared, _ = load(prepared_file)
        pointer = store / ('prepared-inputs-' + today + '.json')
        previous = pointer.read_bytes() if pointer.exists() else None
        replace_bytes(pointer, encode({'schemaId': 'ARK_NO11_AUTOMATIC_READY_INPUT_POINTER_V1',
                                     'sessionDate': today, 'bootstrap': str(prepared_file),
                                     'orderTransmission': False}), previous)
        old_path = settings.get('bootstrapConfigFile')
        merged = None
        result = None
        if type(old_path) is str and old_path:
            try:
                old, _ = load(old_path)
                if (old.get('sessionDate') == today and
                        type(old.get('brokerExecutionConfig')) is str):
                    broker, _ = load(old['brokerExecutionConfig'])
                    merged = merge_current_broker(prepared, old, broker, today)
            except (OSError, ValueError, KeyError, TypeError):
                merged = None
        if merged is None:
            result, broker_path = make_initial_broker(
                binding, settings, prepared_file, prepared, today)
            merged, _ = load(result)
        runtime = safe(merged['privateRoot'], True)
        need(not (runtime / ('received-session-' + today + '.active.json')).exists(),
             'ACTIVE_SESSION_NO_REBIND')
        engine = safe(binding['engine'], True)
        if result is None:
            old_sys = list(sys.path)
            try:
                sys.path.insert(0, str(engine / 'tools'))
                import no11_received_session_bootstrap as bootstrap
                bootstrap.validate_config(merged, allow_explicit_live=True)
                result = bootstrap.immutable(runtime, 'automatic-rss-live-bootstrap', merged)
            finally:
                sys.path[:] = old_sys
        backup = store / ('settings-before-automatic-' + uuid.uuid4().hex + '.json')
        backup.write_bytes(settings_before)
        need(backup.read_bytes() == settings_before, 'SETTINGS_BACKUP_FAILED')
        settings['bootstrapConfigFile'] = str(result)
        replace_bytes(Path(binding['settings']), encode(settings), settings_before)
        print('AUTOSTART_LIVE_BOOTSTRAP=' + str(result))
        print('AUTOSTART_INPUT_CHAIN=CONNECTED_TO_EXISTING_TRADE')
        print('MANUAL_EVIDENCE_REQUIRED=False\nMANUAL_PRICE_INPUT_REQUIRED=False')
        print('ORDER_PERMISSION_CHANGED=False\nORDER_SENT_BY_BRIDGE=False')
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    i = sub.add_parser('install')
    i.add_argument('--runner', required=True, type=Path)
    i.add_argument('--handoff', required=True, type=Path)
    r = sub.add_parser('run')
    r.add_argument('--binding', required=True, type=Path)
    r.add_argument('--same-day-operator-approved', action='store_true')
    a = p.parse_args()
    if a.command == 'install':
        install(a.runner, a.handoff)
    else:
        run(a.binding, a.same_day_operator_approved)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        reason = str(error)
        if not re.fullmatch(r'(?:NO11|P1_RSS)_[A-Z0-9_]+', reason):
            reason = 'NO11_AUTOSTART_LOCAL_RUNTIME_ERROR'
        print('AUTOMATIC_LAUNCHER=BLOCKED|' + reason, flush=True)
        print('MANUAL_EVIDENCE_REQUIRED=False\nMANUAL_PRICE_INPUT_REQUIRED=False')
        print('ORDER_SENT_BY_BRIDGE=False')
        raise SystemExit(2)
