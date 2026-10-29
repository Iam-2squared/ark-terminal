#!/usr/bin/env python3
"""Existing No.1.1 bootstrap with explicit same-run recovery, orders OFF.

Models, Selector, State9, Capital and EXIT remain in their existing modules.
This coordinator owns only collector lifetime, capture relay and run identity.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from no11_received_run_recovery import RunRecovery, CaptureRelay, read, need, atomic


def launch_same_run(config, prepared, run_root, recovery, bootstrap, *,
                    allow_explicit_live=False,
                    popen=subprocess.Popen, monotonic=time.monotonic, sleep=time.sleep):
    """Use the original collector/consumer and the SAME inference database path."""
    bootstrap.need(bootstrap.os.name == 'nt', 'WINDOWS_REQUIRED_FOR_EXCEL_COLLECTOR')
    now = bootstrap.stamp()
    bootstrap.need(now[:10] == config['sessionDate'] and '09:00:00' <= now[11:19] <= '15:20:00',
                   'COLLECTOR_MARKET_SESSION_REQUIRED')
    infer = run_root / 'inference'
    infer.mkdir(exist_ok=True)
    history = recovery.history(run_root)
    attempt = recovery.begin_attempt(run_root)
    view = run_root / 'capture-view'
    view.mkdir(exist_ok=True)
    marker = Path(config['privateRoot']) / 'bootstrap-recovery-required.json'
    process = None
    with (attempt.root / 'collector-private.log').open('xb') as log:
        try:
            # Record ambiguity BEFORE the external process start. A crash in
            # this interval cannot be reinterpreted as "nothing was running".
            attempt.requesting()
            argv = bootstrap.collector_command(config, prepared, attempt.ready, attempt.stop)
            process = popen(argv, cwd=bootstrap.ROOT, stdout=log, stderr=subprocess.STDOUT)
            attempt.started(process.pid)
            deadline = monotonic() + 300
            while not attempt.ready.exists():
                bootstrap.need(process.poll() is None, 'COLLECTOR_EXITED_BEFORE_READY')
                bootstrap.need(monotonic() <= deadline, 'COLLECTOR_READY_TIMEOUT')
                sleep(.25)
            capture = bootstrap.ready_capture(attempt.ready, process, config, prepared)
            attempt.connected(capture)
            chart, _ = read(prepared['files']['plan'])
            plan = chart['chartPlan']
            relay = CaptureRelay(view, history + [capture], session=config['sessionDate'],
                                 plan_sha256=plan['planSha256'], selected_symbols=plan['selectorInputSymbols'])
            print('NO11_BOOTSTRAP_COLLECTOR_CONNECTED=True', flush=True)
            print('NO11_BOOTSTRAP_RESUME_HISTORY_FOLDERS=' + str(len(history)), flush=True)

            def stopped():
                if attempt.stop.exists():
                    raise KeyboardInterrupt
                code = process.poll()
                bootstrap.need(code is None or code == 0, 'COLLECTOR_FAILED')
                relay.refresh(bootstrap.stamp())
                return code is not None

            # Immutable originals from all attempts are combined by verified
            # bytes. The consumer sees its original checkpoint and clocks.
            bootstrap.service.main(bootstrap.service_args(
                config, prepared, infer, view, allow_explicit_live=allow_explicit_live),
                should_stop=stopped)
        finally:
            if process is not None:
                try:
                    bootstrap.shutdown_collector(process, attempt.ready, attempt.stop, marker)
                finally:
                    # Never clear the existing recovery marker. Failure to
                    # establish closed process+workbook leaves RUNNING/CONNECTED.
                    if process.poll() is not None:
                        attempt.close_confirmed(process)
    print('NO11_BOOTSTRAP_STOP=COLLECTOR_AND_CONSUMER_CLOSED', flush=True)


def execute(config, bootstrap, *, resume_run=None, preflight_only=False,
            allow_explicit_live=False, popen=subprocess.Popen, sleep=time.sleep):
    """Caller supplies validated config and the unchanged bootstrap functions."""
    root = Path(config['privateRoot'])
    if allow_explicit_live:
        now = bootstrap.stamp()
        bootstrap.need(now[:10] == config['sessionDate'],
                       'LIVE_REQUIRES_ACTUAL_SESSION_DAY')
        bootstrap.need(config.get('brokerExecutionConfig') is not None and
                       bool(config.get('h235ModelRoot')),
                       'LIVE_REQUIRES_BROKER_AND_H235')
        bootstrap.validate_readonly_broker_config(
            config['brokerExecutionConfig'], config['sessionDate'],
            allow_explicit_live=True)
    bootstrap.need(not (root / 'bootstrap-recovery-required.json').exists(),
                   'PREVIOUS_CLEANUP_REQUIRES_REVIEW')
    recovery = RunRecovery(config)
    run_root = None
    with bootstrap.service.exclusive_service(root):
        try:
            if resume_run is not None:
                run_root = Path(resume_run).absolute()
                prepared = recovery.restore(run_root)
            else:
                if not preflight_only:
                    recovery.check_new()
                run_root = root / ('session-' + config['sessionDate'] + '-' + uuid.uuid4().hex)
                run_root.mkdir(mode=0o700)
                prepared = bootstrap.prepare(config, run_root)
            print('NO11_BOOTSTRAP_PRIVATE_RUN=' + str(run_root), flush=True)
            infer = run_root / 'inference'
            infer.mkdir(exist_ok=True)
            # Genuine model and source preflight happens before ANY collector.
            # It does not initialize/reset portfolio or P1 databases.
            bootstrap.service.main(bootstrap.service_args(
                config, prepared, infer, allow_explicit_live=allow_explicit_live) +
                ['--preflight-only'])
            if preflight_only:
                print('NO11_BOOTSTRAP_PREFLIGHT=EXISTING_ASSETS_LOADED_NOT_LIVE_VERIFIED')
                return run_root
            if resume_run is None:
                recovery.register(run_root, prepared)
            launch_same_run(config, prepared, run_root, recovery, bootstrap,
                            allow_explicit_live=allow_explicit_live,
                            popen=popen, sleep=sleep)
            return run_root
        except BaseException as exc:
            if run_root is not None and run_root.is_dir() and run_root.parent == root:
                message = str(exc)
                safe = message if re.fullmatch(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]+', message) else 'SESSION_CONTROLLER_INTERRUPTED_OR_FAILED'
                atomic(run_root / 'controller-failure.json', {'reason': safe,
                    'productionReady': False, 'orderTransmission': False})
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--resume-run', type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--operator-approved-broker-live', action='store_true')
    args = parser.parse_args(argv)
    # Lazy import keeps model-free relay/recovery tests independent of NumPy.
    import no11_received_session_bootstrap as bootstrap
    raw, _ = bootstrap.load_json(args.config, 100_000)
    config = bootstrap.validate_config(
        raw, allow_explicit_live=args.operator_approved_broker_live)
    execute(config, bootstrap, resume_run=args.resume_run,
            preflight_only=args.preflight_only,
            allow_explicit_live=args.operator_approved_broker_live)
    print('NO11_LIVE_OPERATOR_MODE=' +
          ('EXPLICIT_SESSION_ONLY' if args.operator_approved_broker_live else 'DISABLED'))
    if not args.operator_approved_broker_live:
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
