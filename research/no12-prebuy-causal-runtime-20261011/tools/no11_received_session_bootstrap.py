#!/usr/bin/env python3
"""Prepare existing No.1.1 inputs and supervise read-only collector and inference.

Optional shadowAccountConfig connects native V5/EXIT and simulated receipts.
Optional brokerExecutionConfig observes the broker with transmission disabled.
It never authorizes a real account, changes model weights or transmits orders.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

import no11_p1_forward_shadow as forward
import no11_rss_state9_p1_runner as received
import no11_received_pipeline_service as service

ROOT = forward.REPO
HERE = Path(__file__).resolve().parent
WINDOWS = HERE.parent / 'windows'
CONFIG = 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1'
BROKER_CONFIG = 'ARK_NO11_BROKER_EXECUTION_CONFIG_V1'
CAPTURE = 'ARK_NO11_RSS_CHART50_1M_CAPTURE_V1'
READY = 'ARK_NO11_C50_COLLECTOR_READY_V1'
CLOSED = 'ARK_NO11_C50_COLLECTOR_CLOSED_V1'
REQUIRED = {'schemaId', 'sessionDate', 'dailyRun', 'datedMaster', 'runtimeRoot',
            'privateRoot', 'productionReady', 'orderTransmission'}
OPTIONAL = {'previousContext', 'previousCaptureFiles', 'h235ModelRoot', 'pinsFile',
            'samples', 'historyBars', 'warmupSeconds', 'shadowAccountConfig',
            'brokerExecutionConfig', 'orderIdWorkbookPath'}


def need(ok, code):
    if not ok:
        raise ValueError('NO11_BOOTSTRAP_' + code)


def stamp():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='milliseconds')


def private(value, directory=False):
    need(isinstance(value, (str, Path)) and bool(str(value)), 'PRIVATE_PATH_REQUIRED')
    p = Path(value)
    need(p.is_absolute(), 'ABSOLUTE_PRIVATE_PATH_REQUIRED')
    p = p.absolute()
    need(p != ROOT and ROOT not in p.parents and not p.is_symlink()
         and not any(q.is_symlink() for q in p.parents), 'PRIVATE_PATH_UNSAFE')
    need(p.is_dir() if directory else p.is_file(), 'PRIVATE_SOURCE_MISSING')
    return p


def load_json(path, limit=25_000_000):
    p = private(path)
    need(0 < p.stat().st_size <= limit, 'PRIVATE_SOURCE_SIZE')
    data = p.read_bytes()
    return json.loads(data.decode('utf-8-sig')), hashlib.sha256(data).hexdigest()


def immutable(root, stem, value):
    root = private(root, True)
    # Preserve JS JSON.stringify member order for the original plan checksum.
    data = (json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')
    digest = hashlib.sha256(data).hexdigest()
    path = root / (stem + '-' + digest + '.json')
    need(not path.is_symlink(), 'OUTPUT_SYMLINK')
    if path.exists():
        need(path.is_file() and path.read_bytes() == data, 'OUTPUT_CONFLICT')
    else:
        with path.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    return path


def validate_readonly_broker_config(path, session):
    """Enforce the launcher's observation boundary without importing execution.

    The service validates the full ledger/order contract separately. This check
    runs both at input validation and immediately before making its arguments;
    the mandatory service flag also keeps its final config read read-only.
    """
    obj, checksum = load_json(path, 100_000)
    required = {'schemaId', 'sessionDate', 'evidenceMode', 'ledger', 'transport',
                'orderTerms', 'originalArrivalTable', 'orderTransmission'}
    need(type(obj) is dict and required <= set(obj)
         and obj.get('schemaId') == BROKER_CONFIG, 'BROKER_CONFIG_CONTRACT_INVALID')
    need(obj.get('sessionDate') == session, 'BROKER_CONFIG_SESSION_MISMATCH')
    need(obj.get('evidenceMode') == 'BROKER_OBSERVATION',
         'BROKER_CONFIG_OBSERVATION_REQUIRED')
    need(obj.get('orderTransmission') is False and type(obj.get('transport')) is dict
         and obj['transport'].get('mode') in ('DISABLED', 'OBSERVE_ONLY'),
         'BROKER_CONFIG_NOT_READONLY')
    return checksum


def validate_config(obj):
    need(type(obj) is dict and REQUIRED <= set(obj) <= REQUIRED | OPTIONAL,
         'CONFIG_FIELDS_INVALID')
    need(obj['schemaId'] == CONFIG and obj['productionReady'] is False
         and obj['orderTransmission'] is False, 'CONFIG_NOT_READONLY')
    forward.day(obj['sessionDate'])
    need(('previousContext' in obj) != ('previousCaptureFiles' in obj),
         'EXACTLY_ONE_PREVIOUS_SOURCE_REQUIRED')
    c = deepcopy(obj)
    for name, low, high, default in [('samples', 2, 390, 390),
                                   ('historyBars', 50, 150, 120),
                                   ('warmupSeconds', 5, 60, 20)]:
        value = c.get(name, default)
        need(type(value) is int and low <= value <= high, 'COLLECTOR_PARAMETER_INVALID')
        c[name] = value
    for key in ('dailyRun', 'runtimeRoot', 'privateRoot'):
        c[key] = str(private(c[key], True))
    for key in ('datedMaster', 'previousContext', 'pinsFile', 'shadowAccountConfig',
                'brokerExecutionConfig', 'orderIdWorkbookPath'):
        if key in c:
            c[key] = str(private(c[key]))
    if 'orderIdWorkbookPath' in c:
        need(Path(c['orderIdWorkbookPath']).suffix.lower() == '.xlsx', 'ORDER_ID_WORKBOOK_TYPE')
    if 'h235ModelRoot' in c:
        c['h235ModelRoot'] = str(private(c['h235ModelRoot'], True))
    need('shadowAccountConfig' not in c or 'h235ModelRoot' in c,
         'H235_REQUIRED_FOR_SHADOW_PORTFOLIO')
    need('brokerExecutionConfig' not in c or 'h235ModelRoot' in c,
         'H235_REQUIRED_FOR_BROKER_OBSERVATION')
    if 'brokerExecutionConfig' in c:
        validate_readonly_broker_config(c['brokerExecutionConfig'], c['sessionDate'])
    if 'previousCaptureFiles' in c:
        files = c['previousCaptureFiles']
        need(type(files) is list and 1 <= len(files) <= 8 and
             all(type(f) is str for f in files) and len(set(files)) == len(files),
             'PREVIOUS_CAPTURE_LIST_INVALID')
        c['previousCaptureFiles'] = [str(private(p)) for p in files]
    return c


def command_output(argv):
    result = subprocess.run(argv, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', check=False,
                            timeout=180, cwd=ROOT)
    if result.returncode:
        raise ValueError('NO11_BOOTSTRAP_SOURCE_EXPORT_OR_VALIDATION_FAILED')
    return result.stdout


def output_path(text, prefix):
    found = [line[len(prefix):] for line in text.splitlines() if line.startswith(prefix)]
    need(len(found) == 1, 'EXPORT_PATH_NOT_UNIQUE')
    return private(found[0])


def export_scope(config):
    run = config['dailyRun']
    mask_text = command_output(['node', str(HERE / 'no11_export_observed_pass_watch_mask.mjs'),
                                '--run', run])
    mask = output_path(mask_text, 'NO11_DAILY_PASS_WATCH_FILE=')
    args = ['node', str(HERE / 'no11_export_chart50_prescreen.mjs'),
            '--run', run, '--session', config['sessionDate']]
    if 'pinsFile' in config:
        args += ['--pins-file', config['pinsFile']]
    plan = output_path(command_output(args), 'NO11_CHART50_RECEIPT=')
    return plan, mask


def validate_scope(session, plan_file, mask_file, master_file, now):
    module = (HERE / 'no11_received_pipeline_tick.mjs').as_uri()
    script = ('import fs from "node:fs";import {validatePipelineInputs} from '
              + json.dumps(module) + ';const [d,p,m,a,t]=process.argv.slice(1);'
              'const read=f=>JSON.parse(fs.readFileSync(f,"utf8").replace(/^\\uFEFF/,""));'
              'const r=validatePipelineInputs({sessionDate:d,chartPlan:read(p).chartPlan,'
              'mask:read(m),master:read(a),throughJst:t});'
              'console.log(JSON.stringify({selected:r.selected}));')
    result = json.loads(command_output(['node', '--input-type=module', '-e', script,
                                       session, str(plan_file), str(mask_file),
                                       str(master_file), now]))
    selected = result.get('selected')
    need(type(selected) is list and 1 <= len(selected) <= 50 and
         len(set(selected)) == len(selected), 'SELECTED_SCOPE_INVALID')
    return selected


def prior_from_captures(files, selected, session, prior, master, prepared_at):
    forward.clock(prepared_at, session)
    by_master = {row['symbol']: row for row in master['rows']}
    rows = {code: {} for code in selected}
    conflicts, sources = set(), []
    for filename in files:
        source, sha = load_json(filename, 20_000_000)
        need(Path(filename).name == 'snapshot-' + sha + '.json', 'PREVIOUS_CAPTURE_HASH_MISMATCH')
        need(source.get('schemaId') == CAPTURE and source.get('sessionDate') == prior
             and source.get('source') == 'RssChart_1M_AND_RssMarket_CUMULATIVE_READONLY'
             and source.get('productionReady') is False and source.get('orderTransmission') is False
             and source.get('shadowOnly') is True and type(source.get('chartRows')) is list,
             'PREVIOUS_CAPTURE_CONTRACT_INVALID')
        capture_time = forward.clock(source.get('observedEndJst'), prior)
        need(capture_time < forward.clock(prepared_at, session), 'PREVIOUS_CAPTURE_FROM_FUTURE')
        sources.append(sha)
        for row in source['chartRows']:
            need(type(row) is dict and row.get('Date') == prior, 'PREVIOUS_CAPTURE_DATE_MIXED')
            code = row.get('Code')
            if code not in rows:
                continue
            m = received.minute(row.get('Time'))
            received.validate_prices(row, require_va=False)
            seen = forward.clock(row.get('knownAtJst'), prior)
            close = forward.clock(received.stamp(prior, m + 1), prior)
            need(close <= seen <= capture_time, 'PREVIOUS_BAR_NOT_CLOSED_WHEN_READ')
            value = {k: row[k] for k in ('Date', 'Code', 'Time', 'O', 'H', 'L', 'C', 'Vo')}
            old = rows[code].get(row['Time'])
            if old is not None and old != value:
                conflicts.add(code)
            rows[code][row['Time']] = value
    symbols, missing = {}, []
    for code in selected:
        metadata = by_master.get(code, {})
        source_rows = sorted(rows[code].values(), key=lambda r: r['Time'])
        if code in conflicts or not 2 <= len(source_rows) <= 400:
            missing.append(code)
            continue
        need(metadata.get('priceBasisVerified') is True
             and metadata.get('corporateActionsCleared') is True,
             'PREVIOUS_PRICE_BASIS_NOT_EVIDENCED')
        symbols[code] = {'previousSession': prior, 'priceBasis': 'COMPARABLE_RAW',
                         'corporateActionsCleared': True, 'knownAtJst': prepared_at,
                         'rows': source_rows, 'basisSource': 'EXISTING_DATED_MASTER_RECEIPT',
                         'historicalCaptureSha256': sources, 'observedPriorBars': len(source_rows),
                         'fullPreviousSessionCoverageCertified': False}
    return {'schemaId': received.PREVIOUS_SCHEMA, 'sessionDate': session,
            'previousSession': prior, 'symbols': symbols,
            'sourceCaptureSha256': sources, 'omittedSymbols': missing,
            'originalReceiveTimeIsNotRewritten': True,
            'productionReady': False, 'orderTransmission': False}


def previous_coverage(context, selected, session, prior, runtime):
    need(context.get('schemaId') == received.PREVIOUS_SCHEMA
         and context.get('sessionDate') == session and context.get('previousSession') == prior
         and context.get('orderTransmission') is False
         and isinstance(context.get('symbols'), dict), 'PREVIOUS_CONTEXT_CONTRACT')
    valid, blocked = [], {}
    for code in selected:
        try:
            received.ObservedStateStream(runtime, session, code,
                                         context['symbols'].get(code), prior)
            valid.append(code)
        except (ValueError, KeyError, TypeError, AssertionError) as exc:
            reason = str(exc)
            blocked[code] = reason if re.fullmatch(r'P1_RSS_[A-Z0-9_]+', reason) else 'PREVIOUS_SOURCE_UNUSABLE'
    return valid, blocked


def prepare(config, run_root):
    now = stamp()
    session = config['sessionDate']
    need(now[:10] == session, 'PREPARATION_REQUIRES_ACTUAL_SESSION_DATE')
    prior = received.previous_cash_session(ROOT, session)
    plan_file, mask_file = export_scope(config)
    master, master_hash = load_json(config['datedMaster'])
    selected = validate_scope(session, plan_file, mask_file, config['datedMaster'], now)
    if 'previousContext' in config:
        previous, _ = load_json(config['previousContext'], 20_000_000)
    else:
        previous = prior_from_captures(config['previousCaptureFiles'], selected,
                                       session, prior, master, stamp())
    runtime = service.features.load_feature_runtime(ROOT)
    usable, blocked = previous_coverage(previous, selected, session, prior, runtime)
    coverage = {'schemaId': 'ARK_NO11_BOOTSTRAP_SOURCE_COVERAGE_V1', 'sessionDate': session,
                'selectedCount': len(selected), 'usablePreviousContextCount': len(usable),
                'blockedPreviousSymbols': blocked, 'masterSourceSha256': master_hash,
                'productionReady': False, 'orderTransmission': False}
    immutable(run_root, 'source-coverage', coverage)
    need(bool(usable), 'NO_USABLE_PREVIOUS_CONTEXT')
    previous = deepcopy(previous)
    previous['symbols'] = {s: previous['symbols'][s] for s in usable}
    plan, _ = load_json(plan_file)
    mask, _ = load_json(mask_file)
    paths = {'plan': str(immutable(run_root, 'chart-plan', plan)),
             'mask': str(immutable(run_root, 'pass-mask', mask)),
             'master': str(immutable(run_root, 'dated-master', master)),
             'previous': str(immutable(run_root, 'previous-context', previous))}
    ready = {'schemaId': 'ARK_NO11_BOOTSTRAP_PREPARED_V1', 'sessionDate': session,
             'preparedAtJst': stamp(), 'files': paths, 'sourceCoverage': coverage,
             'modelPreflightComplete': False, 'productionReady': False, 'orderTransmission': False}
    service.atomic_private(run_root / 'prepared-inputs.json', ready)
    return ready


def service_args(config, prepared, inference_root, capture=None):
    p = prepared['files']
    args = ['--session', config['sessionDate'], '--plan', p['plan'], '--mask', p['mask'],
            '--dated-master', p['master'], '--previous-context', p['previous'],
            '--runtime-root', config['runtimeRoot'], '--private-root', str(inference_root)]
    if config.get('h235ModelRoot'):
        args += ['--h235-model-root', config['h235ModelRoot']]
    if config.get('shadowAccountConfig'):
        args += ['--shadow-account-config', config['shadowAccountConfig']]
    if config.get('brokerExecutionConfig'):
        need(bool(config.get('h235ModelRoot')), 'H235_REQUIRED_FOR_BROKER_OBSERVATION')
        validate_readonly_broker_config(config['brokerExecutionConfig'], config['sessionDate'])
        args += ['--broker-execution-config', config['brokerExecutionConfig'],
                 '--broker-execution-readonly']
    if capture is not None:
        args += ['--capture-folder', str(capture)]
    return args


def collector_command(config, prepared, ready_path, stop_path):
    args = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            str(WINDOWS / 'Probe-No11Chart50ContinuousReadOnly.ps1'),
            '-RunDir', config['dailyRun'], '-PreparedPlanFile', prepared['files']['plan'],
            '-ReadyFile', str(ready_path), '-StopFile', str(stop_path),
            '-Samples', str(config['samples']), '-HistoryBars', str(config['historyBars']),
            '-WarmupSeconds', str(config['warmupSeconds'])]
    if config.get('orderIdWorkbookPath'):
        args += ['-OrderIdWorkbookPath', config['orderIdWorkbookPath']]
    return args


def ready_capture(path, process, config, prepared):
    data, _ = load_json(path, 100_000)
    expected = Path(prepared['files']['plan'])
    need(data.get('schemaId') == READY and data.get('sessionDate') == config['sessionDate']
         and data.get('processId') == process.pid and data.get('orderTransmission') is False
         and data.get('productionReady') is False and
         data.get('planFileSha256') == hashlib.sha256(expected.read_bytes()).hexdigest()
         and Path(data.get('planFile', '')).absolute() == expected.absolute(),
         'COLLECTOR_READY_IDENTITY_MISMATCH')
    capture = private(data.get('captureFolder'), True)
    need(capture.parent == Path(config['dailyRun']).absolute()
         and re.fullmatch(r'chart50-shadow-' + re.escape(config['sessionDate'])
                          + r'-\d{6}-' + str(process.pid), capture.name),
         'COLLECTOR_CAPTURE_FOLDER_NOT_OWNED')
    return capture


def request_stop(file):
    file = Path(file)
    need(not file.is_symlink(), 'STOP_FILE_SYMLINK')
    if not file.exists():
        with file.open('xb') as handle:
            handle.write(b'READ_ONLY_STOP\n')
            handle.flush()
            os.fsync(handle.fileno())


def shutdown_collector(process, ready, stop, recovery_marker, timeout=90):
    request_stop(stop)
    try:
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        service.atomic_private(recovery_marker, {'schemaId': 'ARK_NO11_BOOTSTRAP_RECOVERY_REQUIRED_V1',
            'reason': 'COLLECTOR_STOP_TIMEOUT', 'processId': process.pid,
            'originalExcelMustNotBeKilled': True, 'productionReady': False, 'orderTransmission': False})
        raise ValueError('NO11_BOOTSTRAP_COLLECTOR_STOP_TIMEOUT_MANUAL_CLEANUP_REQUIRED') from None
    ack = Path(str(ready) + '.closed.json')
    try:
        value, _ = load_json(ack, 100_000)
        need(value.get('schemaId') == CLOSED and value.get('processId') == process.pid
             and value.get('temporaryWorkbookClosed') is True
             and value.get('orderTransmission') is False, 'COLLECTOR_CLEANUP_NOT_CONFIRMED')
    except (OSError, ValueError, KeyError, TypeError):
        service.atomic_private(recovery_marker, {'schemaId': 'ARK_NO11_BOOTSTRAP_RECOVERY_REQUIRED_V1',
            'reason': 'COLLECTOR_CLEANUP_NOT_CONFIRMED', 'processId': process.pid,
            'originalExcelMustNotBeKilled': True, 'productionReady': False, 'orderTransmission': False})
        raise ValueError('NO11_BOOTSTRAP_COLLECTOR_CLEANUP_NOT_CONFIRMED') from None
    need(code == 0, 'COLLECTOR_FAILED')


def launch(config, prepared, run_root):
    need(os.name == 'nt', 'WINDOWS_REQUIRED_FOR_EXCEL_COLLECTOR')
    now = stamp()
    need(now[:10] == config['sessionDate'] and '09:00:00' <= now[11:19] <= '15:20:00',
         'COLLECTOR_MARKET_SESSION_REQUIRED')
    inference = run_root / 'inference'
    inference.mkdir(exist_ok=True)
    args = service_args(config, prepared, inference)
    service.main(args + ['--preflight-only'])
    ready, stop = run_root / 'collector-ready.json', run_root / 'collector.stop'
    need(not ready.exists() and not stop.exists(), 'RUN_CONTROL_ALREADY_EXISTS')
    recovery = Path(config['privateRoot']) / 'bootstrap-recovery-required.json'
    process = None
    with (run_root / 'collector-private.log').open('xb') as log:
        try:
            process = subprocess.Popen(collector_command(config, prepared, ready, stop),
                                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 300
            while not ready.exists():
                need(process.poll() is None, 'COLLECTOR_EXITED_BEFORE_READY')
                need(time.monotonic() <= deadline, 'COLLECTOR_READY_TIMEOUT')
                time.sleep(.25)
            capture = ready_capture(ready, process, config, prepared)
            print('NO11_BOOTSTRAP_COLLECTOR_CONNECTED=True', flush=True)

            def stopped():
                if stop.exists():
                    raise KeyboardInterrupt
                code = process.poll()
                need(code is None or code == 0, 'COLLECTOR_FAILED')
                return code is not None

            service.main(service_args(config, prepared, inference, capture), should_stop=stopped)
        finally:
            if process is not None:
                shutdown_collector(process, ready, stop, recovery)
    print('NO11_BOOTSTRAP_STOP=COLLECTOR_AND_CONSUMER_CLOSED', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args(argv)
    run_root = None
    try:
        raw, _ = load_json(args.config, 100_000)
        config = validate_config(raw)
        root = Path(config['privateRoot'])
        need(not (root / 'bootstrap-recovery-required.json').exists(), 'PREVIOUS_CLEANUP_REQUIRES_REVIEW')
        with service.exclusive_service(root):
            run_root = root / ('session-' + config['sessionDate'] + '-' + uuid.uuid4().hex)
            run_root.mkdir(mode=0o700)
            print('NO11_BOOTSTRAP_PRIVATE_RUN=' + str(run_root), flush=True)
            prepared = prepare(config, run_root)
            if args.preflight_only:
                inference = run_root / 'inference'
                inference.mkdir()
                service.main(service_args(config, prepared, inference) + ['--preflight-only'])
                print(forward.dumps({'status': 'PREPARED_READONLY_NOT_LIVE_VERIFIED',
                    'selectedCount': prepared['sourceCoverage']['selectedCount'],
                    'usablePreviousContextCount': prepared['sourceCoverage']['usablePreviousContextCount'],
                    'collectorStarted': False, 'productionReady': False, 'orderTransmission': False}))
            else:
                launch(config, prepared, run_root)
    except BaseException as exc:
        if run_root is not None:
            message = str(exc)
            safe = message if re.fullmatch(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]+', message) else 'BOOTSTRAP_INTERRUPTED_OR_FAILED'
            service.atomic_private(run_root / 'bootstrap-failure.json', {'reason': safe,
                'productionReady': False, 'orderTransmission': False})
        raise
    print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('NO11_BOOTSTRAP_STOP=USER_INTERRUPT_READONLY')
        raise SystemExit(130)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        message = str(exc)
        print(message if re.fullmatch(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]+', message)
              else 'NO11_BOOTSTRAP_PRIVATE_SOURCE_OR_RUNTIME_FAILURE', file=sys.stderr)
        raise SystemExit(2)
