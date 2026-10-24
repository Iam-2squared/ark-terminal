#!/usr/bin/env python3
"""Local read-only service: incremental RSS capture -> Selector -> P1 -> H235.

Runs only when explicitly launched on the PC. No broker or account writes.
The native P1/H235 models are loaded once. Each new capture replays the saved
received prefix for State9, while SQLite makes already evaluated bars idempotent.
New stale bars after downtime never generate retroactive Entry candidates.
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
    """Keep source receipts intact; record actual feature evaluation time separately."""
    def __init__(self, database, scorer, clock=now_jst):
        super().__init__(database, scorer)
        self.processing_clock = clock
        self.db.execute('''CREATE TABLE IF NOT EXISTS received_processing
          (watch_key TEXT NOT NULL, bar_end TEXT NOT NULL, source_hash TEXT NOT NULL,
           evaluated_at TEXT NOT NULL, status TEXT NOT NULL,
           PRIMARY KEY(watch_key,bar_end))''')
        self.db.commit()

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
        # Completed results retain their original processing instant on replay.
        # A pre-inference crash cannot revive an unscored stale bar later.
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
    # Commit source observations and selector envelopes BEFORE P1; a crash after
    # this point reuses precisely the same received prefix, never reselects.
    atomic_private(Path(root) / 'pipeline-current.json', {
        'schemaId': 'ARK_NO11_PIPELINE_POINTER_V1', 'privateTick': str(path),
        'sha256': digest, 'orderTransmission': False})
    return payload, str(path)


def main(argv=None, *, should_stop=None):
    """Optional supervisor callback: True drains once; exceptions stop immediately.

    Standalone CLI behavior is unchanged. The bootstrap owns the collector and
    uses this hook rather than killing Excel or weakening the data-time gates.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--capture-folder', type=Path)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--mask', required=True, type=Path)
    parser.add_argument('--dated-master', required=True, type=Path)
    parser.add_argument('--previous-context', required=True, type=Path)
    parser.add_argument('--runtime-root', required=True, type=Path)
    parser.add_argument('--h235-model-root', type=Path)
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
    if args.preflight_only:
        print(forward.dumps({'status': 'ASSETS_LOADED_READONLY_NOT_LIVE_VERIFIED',
            'p1Fold': 5, 'h235ModelsVerified': 24 if h235 else 0,
            'productionReady': False, 'orderTransmission': False}))
        return
    need(args.capture_folder is not None, 'CAPTURE_FOLDER_REQUIRED')
    folder = private_path(args.capture_folder, True)
    with exclusive_service(root):
        checkpoint = load_checkpoint(root)
        engine = ProcessingTimedP1(root / ('p1-shadow-' + args.session + '.sqlite'), scorer)
        signature = None
        verify_history = True
        started = time.monotonic()
        last_summary = None
        try:
            while True:
                stop_after_tick = bool(should_stop()) if should_stop is not None else False
                current = now_jst()
                need(current[:10] == args.session, 'NOT_SELECTED_SESSION_TODAY')
                if current[11:16] >= '15:26':
                    print('NO11_SERVICE_STOP=SESSION_END_READONLY')
                    break
                new_signature = source_signature(folder)
                if len(new_signature) < 2:
                    need(time.monotonic() - started <= 300, 'CAPTURE_START_TIMEOUT')
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
                    tick = run_tick(request, root)
                    if tick is None:
                        need(not stop_after_tick, 'COLLECTOR_ENDED_WITH_PARTIAL_CAPTURE')
                        time.sleep(args.poll_seconds)
                        continue
                    payload, checkpoint = tick
                    summary = received.consume_received_feed(runtime, engine, payload['feed'],
                        payload['selectorEnvelopes'], previous, previous_session=prior,
                        through=now_jst(), h235=h235, h235_store=root)
                    last_summary = payload['summary']
                    report = {'schemaId': 'ARK_NO11_CONTINUOUS_RECEIVED_SHADOW_V1',
                        'actualCompletedAtJst': now_jst(), 'source': last_summary,
                        'inference': summary, 'previousContextSha256': previous_hash,
                        'collectorLaunchedByThisProcess': False,
                        'realAccountConnected': False, 'exitConnected': False,
                        'productionReady': False, 'orderTransmission': False}
                    atomic_private(root / 'pipeline-latest-report.json', report)
                    print(forward.dumps({'status': 'RECEIVED_PIPELINE_TICK_COMPLETE',
                        'snapshots': last_summary['snapshots'], 'minuteRows': last_summary['minuteRows'],
                        'selectorRuns': last_summary['executedSlots'], 'missedSlots': last_summary['missedSlots'],
                        'p1Candidates': summary['p1Session']['firstEntryCandidates'],
                        'h235Executions': summary.get('h235OriginalModelExecutions', 0),
                        'productionReady': False, 'orderTransmission': False}), flush=True)
                    signature, verify_history = new_signature, False
                if args.once or stop_after_tick:
                    break
                if last_summary and last_summary.get('lastSourceAtJst'):
                    age = (forward.clock(now_jst(), args.session) -
                           forward.clock(last_summary['lastSourceAtJst'], args.session)).total_seconds()
                    need(age <= 120, 'CAPTURE_STOPPED_OR_STALE')
                time.sleep(args.poll_seconds)
        finally:
            engine.close()
    print('ORDER_TRANSMISSION=False')


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
