"""Read-only session identity and byte-preserving capture relay.

No models, network, Excel or orders. Use while holding the existing bootstrap
root lock. A restart reuses the SAME inference directory and original inputs;
an absent cleanup acknowledgement never grants a new collector permission.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = 'ARK_NO11_RECEIVED_RUN_CONTRACT_V1'
POINTER = 'ARK_NO11_RECEIVED_ACTIVE_RUN_V1'
ATTEMPT = 'ARK_NO11_RECEIVED_ATTEMPT_V1'
SNAPSHOT = re.compile(r'^snapshot-([a-f0-9]{64})\.json$')


def need(ok, code):
    if not ok:
        raise ValueError('NO11_RECOVERY_' + code)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def private(value, *, directory=False, exists=True):
    p = Path(value)
    need(p.is_absolute(), 'ABSOLUTE_PATH_REQUIRED')
    p = Path(os.path.abspath(p))
    need(p != ROOT and ROOT not in p.parents and not p.is_symlink()
         and not any(a.is_symlink() for a in p.parents), 'UNSAFE_PRIVATE_PATH')
    need(p.parent.is_dir(), 'PARENT_MISSING')
    if exists:
        need(p.is_dir() if directory else p.is_file(), 'PRIVATE_SOURCE_MISSING')
    return p


def read(path, limit=25_000_000):
    p = private(path)
    need(0 < p.stat().st_size <= limit, 'FILE_SIZE')
    data = p.read_bytes()
    need(0 < len(data) <= limit, 'FILE_SIZE')
    return json.loads(data.decode('utf-8-sig')), hashlib.sha256(data).hexdigest()


def workbook_pin(value):
    # Excel may save new observed rows to this file. Bind the private workbook
    # identity, not mutable workbook bytes; live PID/start time is checked by
    # the account observer for each combined snapshot.
    p = private(value)
    need(p.suffix.lower() == '.xlsx', 'ORDER_ID_WORKBOOK_TYPE')
    return {'path': str(p), 'identitySha256': hashlib.sha256(str(p).lower().encode('utf-8')).hexdigest()}


def atomic(path, obj):
    p = private(path, exists=False)
    tmp = p.with_name('.' + p.name + '.' + uuid.uuid4().hex + '.tmp')
    data = encoded(obj) + b'\n'
    try:
        with tmp.open('xb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    finally:
        if tmp.exists():
            tmp.unlink()


def sealed(body):
    return dict(body, sha256=digest(body))


def unseal(path, schema):
    obj, _ = read(path, 1_000_000)
    need(type(obj) is dict, 'SEALED_OBJECT_REQUIRED')
    body = dict(obj)
    sha = body.pop('sha256', None)
    need(sha == digest(body) and body.get('schemaId') == schema
         and body.get('productionReady') is False and body.get('orderTransmission') is False,
         'CONTRACT_CHANGED')
    return body


def instant(value, session):
    need(type(value) is str and re.fullmatch(
        r'20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?\+09:00', value), 'CLOCK_INVALID')
    dt = datetime.fromisoformat(value)
    need(dt.date().isoformat() == session and dt.utcoffset() == timedelta(hours=9), 'SESSION_CLOCK_MISMATCH')
    return dt


class RunRecovery:
    def __init__(self, config):
        self.config = json.loads(encoded(config))
        self.session = config['sessionDate']
        need(re.fullmatch(r'20\d\d-\d\d-\d\d', self.session)
             and config.get('orderTransmission') is False and config.get('productionReady') is False,
             'CONFIG_NOT_READONLY')
        self.root = private(config['privateRoot'], directory=True)
        self.daily = private(config['dailyRun'], directory=True)
        self.pointer = self.root / ('received-session-' + self.session + '.active.json')

    def _run(self, path):
        run = private(path, directory=True)
        need(run.parent == self.root and re.fullmatch(
            'session-' + re.escape(self.session) + r'-[a-f0-9]{32}', run.name), 'RUN_NOT_OWNED')
        return run

    def check_new(self):
        need(not self.pointer.exists(), 'EXISTING_SESSION_REQUIRES_RESUME')
        # Also protect prior versions which did not write an active-run pointer.
        for run in self.root.glob('session-' + self.session + '-*'):
            need(not run.is_symlink(), 'UNSAFE_PRIVATE_PATH')
            infer = run / 'inference'
            evidence = (run / 'collector-ready.json').exists() or (run / 'run-contract.json').exists()
            if infer.is_dir():
                evidence = evidence or any(infer.glob('*.sqlite')) or (infer / 'pipeline-current.json').exists()
            need(not evidence, 'UNREGISTERED_EXISTING_RUN_REQUIRES_REVIEW')

    def register(self, run_path, prepared):
        self.check_new()
        run = self._run(run_path)
        need(prepared.get('sessionDate') == self.session and prepared.get('orderTransmission') is False
             and prepared.get('productionReady') is False and set(prepared.get('files', {})) ==
             {'plan', 'mask', 'master', 'previous'}, 'PREPARED_CONTRACT_INVALID')
        _, prepared_sha = read(run / 'prepared-inputs.json', 1_000_000)
        on_disk, _ = read(run / 'prepared-inputs.json', 1_000_000)
        need(on_disk == prepared, 'PREPARED_OBJECT_CHANGED')
        files = {}
        for key, filename in prepared['files'].items():
            p = private(filename)
            need(p.parent == run, 'PREPARED_PATH_OUTSIDE_RUN')
            _, checksum = read(p)
            files[key] = {'path': str(p), 'sha256': checksum}
        extras = {}
        for key in ('shadowAccountConfig', 'brokerExecutionConfig'):
            if self.config.get(key):
                p = private(self.config[key])
                _, checksum = read(p, 100_000)
                extras[key] = {'path': str(p), 'sha256': checksum}
        body = {'schemaId': CONTRACT, 'sessionDate': self.session, 'runRoot': str(run),
                'configSha256': digest(self.config), 'preparedSha256': prepared_sha,
                'files': files, 'extras': extras, 'productionReady': False, 'orderTransmission': False}
        if self.config.get('orderIdWorkbookPath'):
            body['workbooks'] = {'orderIdWorkbookPath': workbook_pin(self.config['orderIdWorkbookPath'])}
        atomic(run / 'run-contract.json', sealed(body))
        # A crash before this pointer is written still leaves discoverable
        # evidence; check_new must not turn that orphan into a clean run.
        atomic(self.pointer, sealed({'schemaId': POINTER, 'sessionDate': self.session,
            'runRoot': str(run), 'contractSha256': digest(body),
            'productionReady': False, 'orderTransmission': False}))

    def restore(self, run_path):
        run = self._run(run_path)
        pointer = unseal(self.pointer, POINTER)
        body = unseal(run / 'run-contract.json', CONTRACT)
        need(pointer.get('runRoot') == str(run) and pointer.get('sessionDate') == self.session
             and pointer.get('contractSha256') == digest(body) and body.get('runRoot') == str(run)
             and body.get('sessionDate') == self.session and body.get('configSha256') == digest(self.config),
             'RUN_OR_CONFIG_CHANGED')
        prepared, actual = read(run / 'prepared-inputs.json', 1_000_000)
        need(actual == body['preparedSha256'], 'PREPARED_BYTES_CHANGED')
        for key, pin in body['files'].items():
            p = private(pin['path'])
            need(p.parent == run and prepared['files'].get(key) == str(p), 'PREPARED_PATH_CHANGED')
            _, checksum = read(p)
            need(checksum == pin['sha256'], 'PREPARED_INPUT_CHANGED')
        for key, pin in body['extras'].items():
            need(key in ('shadowAccountConfig', 'brokerExecutionConfig'), 'EXTRA_CONFIG_UNKNOWN')
            _, checksum = read(pin['path'], 100_000)
            need(checksum == pin['sha256'], 'BROKER_CONFIG_CHANGED'
                 if key == 'brokerExecutionConfig' else 'SHADOW_CONFIG_CHANGED')
        expected_workbooks = ({'orderIdWorkbookPath': workbook_pin(self.config['orderIdWorkbookPath'])}
                              if self.config.get('orderIdWorkbookPath') else {})
        need(body.get('workbooks', {}) == expected_workbooks, 'WORKBOOK_IDENTITY_CHANGED')
        self.history(run)  # refuses all uncertain collector-cleanup states
        return prepared

    def history(self, run_path):
        run = self._run(run_path)
        folders = []
        attempts = sorted(run.glob('attempt-*'))
        need(len(attempts) <= 16, 'ATTEMPT_LIMIT')
        for expected, path in enumerate(attempts, 1):
            need(path.name == f'attempt-{expected:04d}' and not path.is_symlink(), 'ATTEMPT_ORDER_CHANGED')
            a = unseal(path / 'attempt.json', ATTEMPT)
            need(a.get('sessionDate') == self.session and a.get('runRoot') == str(run), 'ATTEMPT_WRONG_RUN')
            if a['status'] == 'ALLOCATED':
                # No subprocess launch was ever requested in this attempt.
                continue
            need(a['status'] == 'CLOSED', 'COLLECTOR_CLEANUP_UNCONFIRMED')
            ack, checksum = read(path / 'collector-ready.json.closed.json', 100_000)
            need(checksum == a['closedSha256'] and ack.get('schemaId') == 'ARK_NO11_C50_COLLECTOR_CLOSED_V1'
                 and ack.get('processId') == a['pid'] and ack.get('temporaryWorkbookClosed') is True
                 and ack.get('orderTransmission') is False and ack.get('sessionDate') == self.session,
                 'COLLECTOR_CLEANUP_UNCONFIRMED')
            if a.get('captureFolder') is not None:
                ready, checksum = read(path / 'collector-ready.json', 100_000)
                need(checksum == a['readySha256'] and ready.get('processId') == a['pid']
                     and ready.get('captureFolder') == a['captureFolder'], 'COLLECTOR_READY_CHANGED')
                folder = private(a['captureFolder'], directory=True)
                need(folder.parent == self.daily and re.fullmatch(
                    'chart50-shadow-' + re.escape(self.session) + r'-\d{6}-' + str(a['pid']), folder.name),
                    'CAPTURE_FOLDER_NOT_OWNED')
                folders.append(folder)
        need(len(folders) == len(set(folders)), 'DUPLICATE_CAPTURE_FOLDER')
        return folders

    def begin_attempt(self, run_path):
        run = self._run(run_path)
        self.history(run)
        count = len(list(run.glob('attempt-*'))) + 1
        need(count <= 16, 'ATTEMPT_LIMIT')
        path = run / f'attempt-{count:04d}'
        path.mkdir(mode=0o700)
        atomic(path / 'attempt.json', sealed({'schemaId': ATTEMPT, 'sessionDate': self.session,
            'runRoot': str(run), 'status': 'ALLOCATED', 'pid': None, 'captureFolder': None,
            'productionReady': False, 'orderTransmission': False}))
        return Attempt(path, self.session)


class Attempt:
    def __init__(self, root, session):
        self.root = private(root, directory=True)
        self.session = session
        self.file = self.root / 'attempt.json'
        self.ready = self.root / 'collector-ready.json'
        self.stop = self.root / 'collector.stop'

    def _write(self, before, **changes):
        a = unseal(self.file, ATTEMPT)
        need(a['status'] in before, 'ATTEMPT_TRANSITION_INVALID')
        a.update(changes)
        atomic(self.file, sealed(a))

    def requesting(self):
        self._write({'ALLOCATED'}, status='SPAWN_REQUESTED')

    def started(self, pid):
        need(type(pid) is int and pid > 0, 'COLLECTOR_PID_INVALID')
        self._write({'SPAWN_REQUESTED'}, status='RUNNING', pid=pid)

    def connected(self, folder):
        data, checksum = read(self.ready, 100_000)
        a = unseal(self.file, ATTEMPT)
        need(data.get('processId') == a['pid'] and data.get('sessionDate') == self.session
             and data.get('captureFolder') == str(folder) and data.get('orderTransmission') is False,
             'READY_IDENTITY_MISMATCH')
        self._write({'RUNNING'}, status='CONNECTED', captureFolder=str(folder), readySha256=checksum)

    def close_confirmed(self, process):
        # A closed workbook alone is insufficient: the owned process must also
        # have exited, as established by wait()/poll(), not a guessed PID lookup.
        code = process.poll()
        need(type(code) is int, 'COLLECTOR_STILL_RUNNING')
        a = unseal(self.file, ATTEMPT)
        ack, checksum = read(str(self.ready) + '.closed.json', 100_000)
        need(ack.get('schemaId') == 'ARK_NO11_C50_COLLECTOR_CLOSED_V1'
             and ack.get('sessionDate') == self.session and ack.get('processId') == process.pid == a['pid']
             and ack.get('temporaryWorkbookClosed') is True and ack.get('orderTransmission') is False,
             'COLLECTOR_CLEANUP_UNCONFIRMED')
        self._write({'RUNNING', 'CONNECTED'}, status='CLOSED', exitCode=code, closedSha256=checksum)


class CaptureRelay:
    """One immutable view of original snapshots across collector restarts.

    Copies exactly verified bytes ONCE. It never edits an observation timestamp,
    interpolates downtime, changes symbols or substitutes a later price. The
    existing consumer still enforces its original freshness and missed-slot rules.
    """
    def __init__(self, view, folders, *, session, plan_sha256, selected_symbols):
        self.view = private(view, directory=True)
        self.folders = [private(p, directory=True) for p in folders]
        need(1 <= len(self.folders) <= 16 and len(self.folders) == len(set(self.folders))
             and self.view not in self.folders, 'RELAY_FOLDERS_INVALID')
        self.session, self.plan, self.symbols = session, plan_sha256, list(selected_symbols)
        self.verified = {}
        self.view_verified = {}

    def refresh(self, now):
        observed_now = instant(now, self.session)
        sources, copy_count = {}, 0
        for folder in self.folders:
            private(folder, directory=True)
            for p in folder.glob('snapshot-*'):
                m = SNAPSHOT.fullmatch(p.name)
                need(m is not None and p.is_file() and not p.is_symlink(), 'CAPTURE_NAME_INVALID')
                sources.setdefault(p.name, []).append(p)
        need(len(sources) <= 650, 'CAPTURE_LIMIT')
        views = {p.name: p for p in self.view.glob('snapshot-*')}
        need(set(views) <= set(sources), 'SOURCE_REMOVED')
        for name, originals in sources.items():
            target = self.view / name
            for p in originals:
                st = p.stat()
                need(st.st_size <= 20_000_000, 'CAPTURE_SIZE')
                fingerprint = (st.st_size, st.st_mtime_ns, st.st_ctime_ns)
                if self.verified.get(str(p)) == fingerprint and name in self.view_verified:
                    target_stat = target.stat()
                    need(not target.is_symlink() and self.view_verified[name] ==
                         (target_stat.st_size, target_stat.st_mtime_ns, target_stat.st_ctime_ns), 'VIEW_CHANGED')
                    continue
                try:
                    data = p.read_bytes()
                except PermissionError:
                    age = observed_now.timestamp() - st.st_mtime
                    need(not target.exists() and 0 <= age < 10, 'CAPTURE_UNREADABLE')
                    continue
                sha = hashlib.sha256(data).hexdigest()
                if sha != name[len('snapshot-'):-5]:
                    age = observed_now.timestamp() - st.st_mtime
                    need(not target.exists() and 0 <= age < 10, 'CAPTURE_HASH_MISMATCH')
                    continue  # incomplete new file is not published to the consumer
                payload = json.loads(data.decode('utf-8-sig'))
                need(payload.get('schemaId') == 'ARK_NO11_RSS_CHART50_1M_CAPTURE_V1'
                     and payload.get('sessionDate') == self.session and payload.get('chartPlanSha256') == self.plan
                     and payload.get('selectedSymbols') == self.symbols
                     and payload.get('source') == 'RssChart_1M_AND_RssMarket_CUMULATIVE_READONLY'
                     and payload.get('productionReady') is False and payload.get('orderTransmission') is False
                     and payload.get('shadowOnly') is True
                     and instant(payload.get('observedEndJst'), self.session) <= observed_now,
                     'CAPTURE_SCOPE_OR_CLOCK_INVALID')
                if target.exists():
                    need(not target.is_symlink() and target.read_bytes() == data, 'VIEW_CHANGED')
                else:
                    tmp = self.view / ('.relay-' + uuid.uuid4().hex)
                    try:
                        with tmp.open('xb') as f:
                            f.write(data); f.flush(); os.fsync(f.fileno())
                        # The controller holds the root/service lock; no other
                        # writer owns this view. Never replace an existing file.
                        need(not target.exists(), 'VIEW_CONCURRENT_WRITE')
                        os.rename(tmp, target)
                        copy_count += 1
                    finally:
                        if tmp.exists(): tmp.unlink()
                self.verified[str(p)] = fingerprint
                ts = target.stat()
                self.view_verified[name] = (ts.st_size, ts.st_mtime_ns, ts.st_ctime_ns)
        return {'snapshots': len(self.view_verified), 'newCopies': copy_count,
                'sourceTimesRewritten': False, 'orderTransmission': False}
