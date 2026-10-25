#!/usr/bin/env python3
"""Local received RSS -> existing Selector/P1/H235 -> optional execution adapters.

The normal bootstrap is read-only. An explicitly configured broker adapter is
kept separate from the synthetic portfolio; shared entry/source failures halt
both entry paths while preserving held-position EXIT and its EOD clock.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time

import no11_p1_forward_shadow as forward
import no11_frozen_p1_feature_runtime as features
import no11_rss_state9_p1_runner as received
import no11_h235_asof_forward_shadow as h235_module

ROOT = forward.REPO
TICK = Path(__file__).with_name('no11_received_pipeline_tick.mjs')
JST = timezone(timedelta(hours=9))
PROCESS_ERRORS = (OSError, ValueError, KeyError, TypeError, RuntimeError,
                  sqlite3.Error, subprocess.SubprocessError)


def now_jst():
    return datetime.now(JST).isoformat(timespec='milliseconds')


def need(value, code):
    if not value:
        raise ValueError('NO11_SERVICE_' + code)


def private_path(value, directory=False):
    p = Path(value).absolute()
    need(p != ROOT and ROOT not in p.parents and not p.is_symlink()
         and not any(a.is_symlink() for a in p.parents), 'PRIVATE_PATH_UNSAFE')
    need(p.is_dir() if directory else p.is_file(), 'PRIVATE_PATH_MISSING')
    return p


def atomic_private(path, value):
    path = Path(path).absolute()
    private_path(path.parent, True)
    need(not path.is_symlink(), 'OUTPUT_SYMLINK')
    data = (forward.dumps(value) + '\n').encode('utf-8')
    temp = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    need(not temp.exists() and not temp.is_symlink(), 'TEMP_OUTPUT_EXISTS')
    try:
        with temp.open('xb') as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return hashlib.sha256(data).hexdigest()


@contextmanager
def exclusive_service(root):
    file = Path(root) / 'received-pipeline.lock'
    need(not file.is_symlink(), 'LOCK_SYMLINK')
    handle = file.open('a+b')
    try:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError('NO11_SERVICE_ALREADY_RUNNING') from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


class ProcessingTimedP1(forward.ForwardP1Session):
    """Preserve first-receipt time; separately record actual feature processing."""
    def __init__(self, database, scorer, clock=now_jst):
        try:
            super().__init__(database, scorer)
            self.processing_clock = clock
            self.db.execute('''CREATE TABLE IF NOT EXISTS received_processing
              (watch_key TEXT NOT NULL, bar_end TEXT NOT NULL, source_hash TEXT NOT NULL,
               evaluated_at TEXT NOT NULL, status TEXT NOT NULL,
               PRIMARY KEY(watch_key,bar_end))''')
            self.db.commit()
        except BaseException:
            # A constructor that opened SQLite owns its cleanup even before
            # main() has received an instance to close.
            if getattr(self, 'db', None) is not None:
                self.db.close()
            raise

    def evaluate(self, source_event):
        need(isinstance(source_event, dict), 'FEATURE_OBJECT_REQUIRED')
        event = deepcopy(source_event)
        key, end = event['watchKey'], event['barEndJst']
        source_hash = forward.digest(event)
        now = self.processing_clock()
        process = forward.clock(now, self.session)
        bar = forward.clock(end, self.session)
        need(forward.clock(event['evaluatedAtJst'], self.session) <= process,
             'FEATURE_RECEIPT_FROM_FUTURE')
        old = self.db.execute('SELECT * FROM received_processing WHERE watch_key=? AND bar_end=?',
                              (key, end)).fetchone()
        if old:
            need(old['source_hash'] == source_hash, 'REPLAY_SOURCE_CHANGED')
            evaluation = old['evaluated_at']
            status = old['status']
        else:
            evaluation, status = now, 'PENDING'
        completed = self.db.execute('SELECT result_json FROM evaluations WHERE watch_key=? AND bar_end=?',
                                    (key, end)).fetchone()
        if status == 'STALE' or completed is None and (process - bar).total_seconds() > 90:
            with self.db:
                self.db.execute('INSERT INTO received_processing VALUES (?,?,?,?,?) '
                                'ON CONFLICT(watch_key,bar_end) DO UPDATE SET status=excluded.status',
                                (key, end, source_hash, evaluation, 'STALE'))
            return {'status': 'STALE_NOT_RETROACTIVELY_SCORED', 'idempotentReplay': old is not None,
                    'barEndJst': end, 'evaluatedAtJst': evaluation, 'shadowOnly': True,
                    'productionReady': False, 'orderTransmission': False,
                    'orderAuthorized': False}
        if old is None:
            with self.db:
                self.db.execute('INSERT INTO received_processing VALUES (?,?,?,?,?)',
                                (key, end, source_hash, evaluation, 'PENDING'))
        event['evaluatedAtJst'] = evaluation
        event['featureKnownAtJst'] = evaluation
        result = super().evaluate(event)
        with self.db:
            self.db.execute('UPDATE received_processing SET status=? WHERE watch_key=? AND bar_end=?',
                            ('DONE', key, end))
        return result


def source_signature(folder):
    files = sorted(Path(folder).glob('snapshot-*.json'))
    need(len(files) <= 650, 'CAPTURE_FILE_LIMIT')
    values = []
    for p in files:
        need(not p.is_symlink() and re.fullmatch(r'snapshot-[a-f0-9]{64}\.json', p.name),
             'CAPTURE_FILENAME_INVALID')
        s = p.stat()
        values.append((p.name, s.st_size, s.st_mtime_ns))
    return values


def load_checkpoint(root):
    pointer = Path(root) / 'pipeline-current.json'
    if not pointer.exists():
        return None
    obj, _ = received.read_json(private_path(pointer), 100_000)
    need(obj.get('schemaId') == 'ARK_NO11_PIPELINE_POINTER_V1' and
         obj.get('orderTransmission') is False, 'CHECKPOINT_POINTER_INVALID')
    path = private_path(obj.get('privateTick'))
    need(path.parent == Path(root).absolute(), 'CHECKPOINT_PATH_OUTSIDE_PRIVATE_ROOT')
    data = path.read_bytes()
    need(hashlib.sha256(data).hexdigest() == obj.get('sha256'), 'CHECKPOINT_BYTES_CHANGED')
    return str(path)


def run_tick(request, root):
    file = Path(root) / 'pipeline-request.json'
    atomic_private(file, request)
    result = subprocess.run(['node', str(TICK), '--request', str(file)],
                            capture_output=True, text=True, timeout=90, check=False)
    if result.returncode != 0:
        message = result.stderr.strip()
        if message == 'NO11_PIPELINE_CAPTURE_WRITE_IN_PROGRESS':
            return None
        raise ValueError(message if re.fullmatch(r'NO11_[A-Z0-9_]+', message)
                         else 'NO11_SERVICE_NODE_TICK_FAILED')
    reply = json.loads(result.stdout)
    path = private_path(reply.get('privateTick'))
    need(path.parent == Path(root).absolute(), 'TICK_OUTPUT_OUTSIDE_PRIVATE_ROOT')
    payload, digest = received.read_json(path, 35_000_000)
    need(payload.get('summary', {}).get('orderTransmission') is False and
         payload.get('state', {}).get('orderTransmission') is False,
         'TICK_OUTPUT_UNSAFE')
    atomic_private(Path(root) / 'pipeline-current.json', {
        'schemaId': 'ARK_NO11_PIPELINE_POINTER_V1', 'privateTick': str(path),
        'sha256': digest, 'orderTransmission': False})
    return payload, str(path)


def broker_report_flags(actual, *, configured=False, mode='DISABLED'):
    """Describe observed account input and configured transport independently.

    A current broker-shaped snapshot is not certification of a physical
    connection, a transmitted order, an acknowledgement or a fill.
    """
    actual = actual or {}
    return {'brokerExecutionConfigured': configured,
            'brokerTransportMode': actual.get('mode', mode),
            'realAccountConnected': (actual.get('evidenceMode') == 'BROKER_OBSERVATION'
                                     and actual.get('sourceCurrent') is True),
            'exitConnected': configured,
            'brokerConnectionPhysicallyVerified': actual.get('brokerConnectionPhysicallyVerified') is True,
            'orderTransmission': actual.get('orderTransmission') is True}


def main(argv=None, *, should_stop=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--capture-folder', type=Path)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--mask', required=True, type=Path)
    parser.add_argument('--dated-master', required=True, type=Path)
    parser.add_argument('--previous-context', required=True, type=Path)
    parser.add_argument('--runtime-root', required=True, type=Path)
    parser.add_argument('--h235-model-root', type=Path)
    parser.add_argument('--shadow-account-config', type=Path)
    parser.add_argument('--broker-execution-config', type=Path)
    parser.add_argument('--broker-execution-readonly', action='store_true')
    parser.add_argument('--private-root', required=True, type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--poll-seconds', type=float, default=2)
    args = parser.parse_args(argv)
    need(should_stop is None or callable(should_stop), 'SUPERVISOR_CALLBACK_INVALID')
    need(1 <= args.poll_seconds <= 30, 'POLL_INTERVAL_INVALID')
    root = private_path(args.private_root, True)
    for p in (args.plan, args.mask, args.dated_master, args.previous_context):
        private_path(p)
    prior = received.previous_cash_session(ROOT, args.session)
    previous, previous_hash = received.read_json(args.previous_context, 20_000_000)
    need(previous.get('schemaId') == received.PREVIOUS_SCHEMA and
         previous.get('sessionDate') == args.session and
         previous.get('previousSession') == prior and previous.get('orderTransmission') is False,
         'PREVIOUS_CONTEXT_REQUIRED')
    runtime = features.load_feature_runtime(ROOT)
    scorer = forward.FrozenP1Scorer(args.runtime_root, ROOT, args.session)
    h235 = h235_module.FrozenH235AsOf(args.h235_model_root, args.session) if args.h235_model_root else None
    execution_settings = None
    broker_settings = None
    if args.shadow_account_config is not None:
        need(h235 is not None, 'H235_REQUIRED_FOR_SHADOW_PORTFOLIO')
        import no11_received_failure_isolation as execution_module
        execution_settings = execution_module.settings(private_path(args.shadow_account_config), args.session)
    if args.broker_execution_config is not None:
        need(h235 is not None, 'H235_REQUIRED_FOR_BROKER_EXECUTION')
        import no11_broker_execution_service as broker_module
        broker_settings = broker_module.settings(private_path(args.broker_execution_config), args.session,
            read_only=args.broker_execution_readonly)
        # Enforce the bootstrap promise here as well as inside settings(). A
        # future adapter must not silently ignore the read-only launch flag.
        need(not args.broker_execution_readonly or
             broker_settings[0]['transport']['mode'] in ('DISABLED', 'OBSERVE_ONLY'),
             'READONLY_BROKER_TRANSPORT_REQUIRED')
    if args.preflight_only:
        print(forward.dumps({'status': 'ASSETS_LOADED_READONLY_NOT_LIVE_VERIFIED',
            'p1Fold': 5, 'h235ModelsVerified': 24 if h235 else 0,
            'shadowPortfolioConfigured': execution_settings is not None,
            'brokerExecutionConfigured': broker_settings is not None,
            'brokerTransportMode': broker_settings[0]['transport']['mode'] if broker_settings else 'DISABLED',
            'productionReady': False, 'orderTransmission': False}))
        return
    need(args.capture_folder is not None, 'CAPTURE_FOLDER_REQUIRED')
    folder = private_path(args.capture_folder, True)
    with exclusive_service(root):
        checkpoint = load_checkpoint(root)
        engine = ProcessingTimedP1(root / ('p1-shadow-' + args.session + '.sqlite'), scorer)
        execution = None
        broker = None
        signature = None
        verify_history = True
        started = time.monotonic()
        last_summary = None
        final_actual = None
        try:
            if execution_settings is not None:
                execution = execution_module.ExecutionShadow(root, *execution_settings, runtime, previous, prior)
            if broker_settings is not None:
                broker = broker_module.BrokerExecution(root, *broker_settings, runtime, previous, prior)

            def failure_reason(error):
                return (execution_module.reason_code(error) if execution is not None
                        else broker_module.safe_reason(error))

            def halt_entry_paths(reason):
                failures = []
                for controller in (execution, broker):
                    if controller is not None:
                        try:
                            controller.halt_entry(reason, now_jst())
                        except PROCESS_ERRORS as error:
                            failures.append(error)
                if failures:
                    # Try both durable halts before propagating a ledger fault;
                    # never represent an unavailable ledger as healthy.
                    raise failures[0]

            def held_reports(feed=None, *, clock_only=False):
                nonlocal final_actual
                reports, failures = [None, None], []
                for index, controller in enumerate((execution, broker)):
                    if controller is None:
                        continue
                    try:
                        if clock_only:
                            reports[index] = controller.heartbeat(now_jst())
                        else:
                            try:
                                reports[index] = controller.exit_only(feed, now_jst())
                            except PROCESS_ERRORS as error:
                                if isinstance(error, sqlite3.Error):
                                    failures.append(error)
                                try:
                                    halt_entry_paths(failure_reason(error))
                                except PROCESS_ERRORS as halt_error:
                                    failures.append(halt_error)
                                reports[index] = controller.heartbeat(now_jst())
                        filename = 'portfolio-latest-report.json' if index == 0 else 'broker-execution-latest-report.json'
                        atomic_private(root / filename, reports[index])
                        if index == 1:
                            final_actual = reports[index]
                    except PROCESS_ERRORS as error:
                        failures.append(error)
                if failures:
                    # The other independent held-position clock was attempted
                    # even when one report/ledger failed. Entry stays halted.
                    halt_entry_paths(failure_reason(failures[0]))
                    raise failures[0]
                return reports

            def halted_summary(reason):
                return {'schemaId': 'ARK_NO11_ENTRY_PIPELINE_HALTED_V1', 'status': 'ENTRY_PIPELINE_HALTED',
                        'failureCode': reason, 'p1Session': engine.summary(), 'h235OriginalModelExecutions': 0,
                        'productionReady': False, 'orderTransmission': False}

            def source_blocked(error):
                if execution is None and broker is None:
                    raise error
                reason = failure_reason(error)
                halt_entry_paths(reason)
                paper, actual = held_reports(clock_only=True)
                atomic_private(root / 'pipeline-source-failure.json', {
                    'schemaId': 'ARK_NO11_SOURCE_HALTED_EXIT_CLOCK_ONLY_V1', 'reason': reason,
                    'actualObservedAtJst': now_jst(), 'entryPipelineHalted': True,
                    'structuralExitSourceAvailable': False, 'shadowPortfolio': paper,
                    'brokerExecution': actual, 'productionReady': False,
                    **broker_report_flags(actual, configured=broker is not None)})
                return paper

            while True:
                try:
                    stop_after_tick = bool(should_stop()) if should_stop is not None else False
                except PROCESS_ERRORS as error:
                    # A failed read-only source relay must not bypass the
                    # portfolio halt or silently disable its EOD clock.
                    source_blocked(error)
                    stop_after_tick = False
                current = now_jst()
                need(current[:10] == args.session, 'NOT_SELECTED_SESSION_TODAY')
                held_reports(clock_only=True)
                if current[11:16] >= '15:26':
                    print('NO11_SERVICE_STOP=SESSION_END_READONLY')
                    break
                try:
                    new_signature = source_signature(folder)
                except (OSError, ValueError, TypeError) as error:
                    source_blocked(error)
                    if args.once or stop_after_tick: break
                    time.sleep(args.poll_seconds)
                    continue
                if len(new_signature) < 2:
                    if time.monotonic() - started > 300:
                        source_blocked(ValueError('NO11_SERVICE_CAPTURE_START_TIMEOUT'))
                    if args.once or stop_after_tick:
                        print('NO11_SERVICE_WAIT=NEEDS_TWO_COMPLETE_SNAPSHOTS')
                        break
                    time.sleep(args.poll_seconds)
                    continue
                if new_signature != signature:
                    request = {'schemaId': 'ARK_NO11_RECEIVED_PIPELINE_REQUEST_V1',
                        'sessionDate': args.session, 'captureFolder': str(folder),
                        'plan': str(args.plan.absolute()), 'mask': str(args.mask.absolute()),
                        'master': str(args.dated_master.absolute()), 'checkpoint': checkpoint,
                        'verifyHistory': verify_history, 'privateRoot': str(root),
                        'productionReady': False, 'orderTransmission': False}
                    try:
                        tick = run_tick(request, root)
                    except PROCESS_ERRORS as error:
                        source_blocked(error)
                        signature = new_signature  # retry only when new source bytes arrive
                        if args.once or stop_after_tick: break
                        time.sleep(args.poll_seconds)
                        continue
                    if tick is None:
                        if stop_after_tick:
                            source_blocked(ValueError('NO11_SERVICE_COLLECTOR_ENDED_WITH_PARTIAL_CAPTURE'))
                            break
                        time.sleep(args.poll_seconds)
                        continue
                    payload, checkpoint = tick

                    def infer():
                        return received.consume_received_feed(runtime, engine, payload['feed'],
                            payload['selectorEnvelopes'], previous, previous_session=prior,
                            through=now_jst(), h235=h235, h235_store=root)
                    summary, paper, actual = None, None, None
                    try:
                        if execution is None:
                            summary = (halted_summary('NO11_ENTRY_PIPELINE_ALREADY_HALTED')
                                       if broker is not None and broker.entry_halted else infer())
                        else:
                            summary, paper = execution_module.guarded_inference(execution, payload['feed'], infer,
                                clock=now_jst, p1_summary=engine.summary)
                        if summary.get('status') == 'ENTRY_PIPELINE_HALTED':
                            halt_entry_paths(summary.get('failureCode', 'NO11_ENTRY_PIPELINE_FAILURE'))
                        if broker is not None:
                            actual = (broker.exit_only(payload['feed'], now_jst()) if broker.entry_halted
                                      else broker.advance(payload['feed'], summary, now_jst()))
                    except PROCESS_ERRORS as error:
                        if execution is None and broker is None:
                            raise
                        reason = failure_reason(error)
                        halt_entry_paths(reason)
                        paper, actual = held_reports(payload['feed'])
                        summary = halted_summary(reason)
                    final_actual = actual
                    last_summary = payload['summary']
                    report = {'schemaId': 'ARK_NO11_CONTINUOUS_RECEIVED_SHADOW_V1',
                        'actualCompletedAtJst': now_jst(), 'source': last_summary,
                        'inference': summary, 'previousContextSha256': previous_hash,
                        'shadowPortfolio': paper, 'collectorLaunchedByThisProcess': False,
                        'brokerExecution': actual,
                        'originalExitShadowConnected': execution is not None,
                        'productionReady': False,
                        **broker_report_flags(actual, configured=broker is not None)}
                    atomic_private(root / 'pipeline-latest-report.json', report)
                    if paper is not None:
                        atomic_private(root / 'portfolio-latest-report.json', paper)
                    if actual is not None:
                        atomic_private(root / 'broker-execution-latest-report.json', actual)
                    degraded = (summary.get('status') == 'ENTRY_PIPELINE_HALTED'
                                or paper is not None and paper.get('entryPipelineHalted') is True
                                or actual is not None and actual.get('entryPipelineHalted') is True)
                    print(forward.dumps({'status': 'DEGRADED_EXIT_ONLY' if degraded else 'RECEIVED_PIPELINE_TICK_COMPLETE',
                        'snapshots': last_summary['snapshots'], 'minuteRows': last_summary['minuteRows'],
                        'selectorRuns': last_summary['executedSlots'], 'missedSlots': last_summary['missedSlots'],
                        'p1Candidates': summary['p1Session']['firstEntryCandidates'],
                        'h235Executions': summary.get('h235OriginalModelExecutions', 0),
                        'shadowPositions': paper['positionCount'] if paper else 0,
                        'shadowBuyIntents': paper['buyIntentCount'] if paper else 0,
                        'shadowSellIntents': paper['sellIntentCount'] if paper else 0,
                        'brokerPositions': actual['positionCount'] if actual else 0,
                        'productionReady': False, 'orderTransmission': actual['orderTransmission'] if actual else False}), flush=True)
                    signature, verify_history = new_signature, False
                if args.once or stop_after_tick:
                    break
                if last_summary and last_summary.get('lastSourceAtJst'):
                    age = (forward.clock(now_jst(), args.session) -
                           forward.clock(last_summary['lastSourceAtJst'], args.session)).total_seconds()
                    if age > 120:
                        source_blocked(ValueError('NO11_SERVICE_CAPTURE_STOPPED_OR_STALE'))
                time.sleep(args.poll_seconds)
        finally:
            try:
                if execution is not None:
                    try:
                        atomic_private(root / 'portfolio-latest-report.json', execution.summary())
                    finally:
                        execution.close()
            finally:
                try:
                    if broker is not None:
                        try:
                            atomic_private(root / 'broker-execution-latest-report.json', broker.summary())
                        finally:
                            broker.close()
                finally:
                    engine.close()
    print('ORDER_TRANSMISSION=' + str(broker_report_flags(final_actual)['orderTransmission']))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('NO11_SERVICE_STOP=USER_INTERRUPT_READONLY')
        raise SystemExit(130)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, sqlite3.Error,
            subprocess.SubprocessError) as exc:
        message = str(exc)
        print(message if re.fullmatch(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]+', message)
              else 'NO11_SERVICE_PRIVATE_INPUT_OR_RUNTIME_FAILURE', file=sys.stderr)
        raise SystemExit(2)
