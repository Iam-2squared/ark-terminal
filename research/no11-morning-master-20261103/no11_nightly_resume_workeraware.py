#!/usr/bin/env python3
"""Restartable No11 DATA-ONLY nightly pipeline. Never launches Trade or orders.

Native collectors retain their original per-symbol receipt checks. This wrapper
adds a process-lifetime lock, durable stage journal and publication recovery.
An interrupted capture is retried only by a NEW explicit invocation, after all
old workers are gone. Completed capture is reused, never silently re-dated.
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
import tempfile
import time
import uuid

JST = timezone(timedelta(hours=9))
SCHEMA = 'ARK_NO11_NIGHTLY_RESUME_V1'
SHA = re.compile(r'^[a-f0-9]{64}$')


def need(ok, code):
    if not ok:
        raise ValueError('NO11_NIGHTLY_RESUME_' + code)


def safe(path, directory=False):
    p = Path(path)
    need(p.is_absolute(), 'ABSOLUTE_PATH')
    for v in (p, *p.parents):
        if v.exists() or v.is_symlink():
            need(not v.is_symlink() and not (getattr(v.lstat(), 'st_file_attributes', 0) & 1024), 'REPARSE_PATH')
    need(p.is_dir() if directory else p.is_file(), 'PATH_MISSING')
    return p


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(obj):
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8')


def read(path):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            need(k not in result, 'DUPLICATE_KEY')
            result[k] = v
        return result
    raw = safe(path).read_bytes()
    need(0 < len(raw) <= 32_000_000, 'FILE_SIZE')
    obj = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique)
    need(type(obj) is dict, 'JSON_OBJECT')
    return obj


def atomic(path, obj):
    """Previous checkpoint survives failed writes; incomplete temp is not read."""
    path = Path(path)
    safe(path.parent, True)
    if path.exists() or path.is_symlink():
        safe(path)
    payload = dict(obj)
    payload['checkpointSha256'] = digest(encode(obj))
    temp = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, prefix='.checkpoint-', delete=False) as stream:
            temp = Path(stream.name)
            stream.write(encode(payload))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        temp = None
        if os.name != 'nt':
            fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def checkpoint(path):
    obj = read(path)
    checksum = obj.pop('checkpointSha256', None)
    need(checksum == digest(encode(obj)), 'CHECKPOINT_CORRUPTED')
    need(obj.get('schemaId') == SCHEMA and obj.get('orderTransmission') is False, 'CHECKPOINT_CONTRACT')
    return obj


@contextmanager
def exclusive(path):
    """OS releases this lock on process crash; its file is NEVER deleted."""
    path = Path(path)
    safe(path.parent, True)
    if path.exists() or path.is_symlink():
        safe(path)
    stream = path.open('a+b')
    locked = False
    try:
        if path.stat().st_size == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError as exc:
            raise ValueError('NO11_NIGHTLY_RESUME_ALREADY_RUNNING') from exc
        yield
    finally:
        if locked:
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def checked_log(work, name, expected):
    need(type(name) is str and re.fullmatch(r'capture-[a-f0-9]{32}\.log', name), 'CAPTURE_LOG_NAME')
    p = safe(Path(work) / name)
    need(type(expected) is str and SHA.fullmatch(expected) and digest(p.read_bytes()) == expected, 'CAPTURE_LOG_CHANGED')
    return p


class Pipeline:
    """Callbacks are deliberately DATA-only; no retry of a live order is possible."""
    def __init__(self, work, identity, pointer, capture, publish, validate, quiet):
        self.work = Path(work)
        self.identity = identity
        self.pointer = Path(pointer)
        self.capture = capture
        self.publish = publish
        self.validate = validate
        self.quiet = quiet
        self.work.mkdir(parents=True, exist_ok=True)
        safe(self.work, True)
        self.state_file = self.work / 'checkpoint.json'

    def save(self, state, **changes):
        result = dict(state, **changes)
        result['updatedAtJst'] = datetime.now(JST).isoformat(timespec='seconds')
        atomic(self.state_file, result)
        return result

    def run(self):
        with exclusive(self.work.parent / 'nightly.lock'):
            self.quiet()
            identity_sha = digest(encode(self.identity))
            if self.state_file.exists():
                state = checkpoint(self.state_file)
                need(state.get('identitySha256') == identity_sha, 'INPUT_OR_CODE_CHANGED')
            else:
                state = self.save({'schemaId': SCHEMA, 'identitySha256': identity_sha,
                                   'identity': self.identity, 'orderTransmission': False}, phase='NEW')
            need(state.get('phase') in ('NEW', 'CAPTURING', 'CAPTURED', 'PUBLISHING', 'COMPLETE'), 'PHASE_INVALID')
            if state['phase'] == 'COMPLETE':
                need(self.pointer.exists(), 'COMPLETED_POINTER_MISSING')
                self.validate(self.pointer, state.get('captureSha256'))
                need(digest(self.pointer.read_bytes()) == state.get('pointerSha256'), 'COMPLETED_POINTER_CHANGED')
                print('NO11_NIGHTLY_RESUME=ALREADY_COMPLETE')
                return
            # Publication may have finished immediately before a power loss.
            if self.pointer.exists():
                self.validate(self.pointer, state.get('captureSha256'))
                self.save(state, phase='COMPLETE', pointerSha256=digest(self.pointer.read_bytes()))
                print('NO11_NIGHTLY_RESUME=EXISTING_HANDOFF_VERIFIED')
                return
            if state['phase'] in ('NEW', 'CAPTURING'):
                log = self.work / ('capture-' + uuid.uuid4().hex + '.log')
                state = self.save(state, phase='CAPTURING', attemptLog=log.name)
                self.quiet()
                self.capture(log)
                safe(log)
                state = self.save(state, phase='CAPTURED', captureLog=log.name,
                                  captureSha256=digest(log.read_bytes()))
            log = checked_log(self.work, state['captureLog'], state['captureSha256'])
            self.quiet()
            state = self.save(state, phase='PUBLISHING')
            print('NO11_NIGHTLY_RESUME=REUSING_VERIFIED_CAPTURE_LOG')
            self.publish(log)
            self.validate(self.pointer, state['captureSha256'])
            self.save(state, phase='COMPLETE', pointerSha256=digest(self.pointer.read_bytes()))
            print('NO11_NIGHTLY_RESUME=COMPLETE')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, safe(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def no_workers():
    """ARK_NO11_NIGHTLY_RESUME_WORKER_PROBE_V2.

    Avoid falsely classifying OUR OWN launcher ancestry as a concurrent worker.
    Block every active unrelated ARK workflow; ambiguous CIM output still blocks.
    Distinguish *active old worker* from a failed process query for diagnostics.
    Never terminate, reset, rearm, or resend any worker or order.
    """
    need(os.name == 'nt', 'WINDOWS_ONLY')
    own = os.getpid()
    # Execute from a temporary .ps1 rather than using -Command, so the
    # query subprocess does not match its own commandline's regex literals.
    probe = r'''param([int]$OwnPid)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
try {
  $rows=@(Get-CimInstance Win32_Process -ErrorAction Stop)
  if($rows.Count -lt 1){throw 'EMPTY_CIM_SNAPSHOT'}
  $byId=@{}
  foreach($r in $rows){$byId[[int]$r.ProcessId]=$r}
  if(-not $byId.ContainsKey($OwnPid)){throw 'PYTHON_PID_NOT_IN_CIM_SNAPSHOT'}
  # This python's own parent, grandparent and other in-process launch
  # ancestors are trusted for *this DATA request only*. Other ARK jobs
  # are not exempt. Stop on cycles / unexpected process hierarchy.
  $ancestors=@{}
  $p=$OwnPid
  for($i=0;$i -lt 32;$i++){
    if($ancestors.ContainsKey($p)){break}
    $ancestors[$p]=$true
    if(-not $byId.ContainsKey($p)){break}
    $next=[int]$byId[$p].ParentProcessId
    if($next -le 0 -or $next -eq $p){break}
    if(-not $byId.ContainsKey($next)){break}
    # No PID reuse can be accepted as lineage when the purported
    # parent's creation time is later than this child.
    $parentTime=$byId[$next].CreationDate
    $childTime=$byId[$p].CreationDate
    if($null -eq $parentTime -or $null -eq $childTime){throw 'ANCESTOR_CREATION_TIME_MISSING'}
    if($parentTime -gt $childTime){throw 'ANCESTOR_PID_REUSED'}
    $p=$next
  }
  # The PowerShell CIM probe is a descendant of this python; exclude it
  # directly by $PID (it is not part of Python's ancestor chain).
  $pattern='(?:no11_nightly_resume[.]py|no11_nightly_resume_workeraware[.]py|Run-No11NightlyCycle|Prepare-No11WeeklyAfterCloseReadOnly|Prepare-No11NextSessionNightlyReadOnly|Run-No11RssDailyTrendCensusReadOnly|Run-No11WeeklyCandidateRefreshReadOnly|Capture-No11RssTrainingBatchReadOnly|Prepare-No11PreviousArchiveReadOnly|Start-No11UnifiedLauncher|Start-No11PreopenStandby|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller|Probe-No11Chart50ContinuousReadOnly|Invoke-No11MsiiOrder)'
  $busyWorkers=@()
  foreach($r in $rows){
    $id=[int]$r.ProcessId
    if($id -eq $PID -or $ancestors.ContainsKey($id)){continue}
    if([string]$r.Name -notmatch '^(?:powershell|pwsh|python|pythonw|node)(?:[.]exe)?$'){continue}
    $cmd=[string]$r.CommandLine
    if($cmd -match $pattern){
      # Only the role and IDs are logged. No command line, account,
      # workbook path, symbol, position, or order detail is disclosed.
      $role=if($cmd -match '(?i)Invoke-No11MsiiOrder|Run-No11ReceivedSessionOperatorLive|no11_received_session_controller'){'LIVE'}
      elseif($cmd -match '(?i)Probe-No11Chart50ContinuousReadOnly'){'CHART'}
      else{'DATA'}
      $busyWorkers+=@([pscustomobject]@{pid=$id;parentPid=[int]$r.ParentProcessId;role=$role})
    }
  }
  if($busyWorkers.Count -gt 0){
    [pscustomobject]@{schemaId='ARK_NO11_WORKER_PROBE_V2';workers=$busyWorkers} | ConvertTo-Json -Depth 5 -Compress
    exit 3
  }
  [pscustomobject]@{schemaId='ARK_NO11_WORKER_PROBE_V2';workers=@()} | ConvertTo-Json -Depth 5 -Compress
  exit 0
} catch {
  # Never treat a failed CIM check as proof that the machine is quiet.
  Write-Output 'NO11_WORKER_CIM_QUERY_OR_ANCESTRY_FAILED'
  exit 4
}
'''
    with tempfile.TemporaryDirectory(prefix='ark-no11-worker-scan-') as tmp:
        script = Path(tmp) / 'read-only-process-scan.ps1'
        script.write_text(probe, encoding='utf-8')
        try:
            result = subprocess.run(
                ['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive',
                 '-ExecutionPolicy', 'Bypass', '-File', str(script), '-OwnPid', str(own)],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=35, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            print('NO11_NIGHTLY_RESUME_WORKER_PROBE=QUERY_UNAVAILABLE', flush=True)
            need(False, 'WORKER_QUERY_FAILED')
    if result.returncode not in (0, 3) or not result.stdout.strip():
        print('NO11_NIGHTLY_RESUME_WORKER_PROBE=QUERY_UNAVAILABLE', flush=True)
        need(False, 'WORKER_QUERY_FAILED')
    try:
        data = json.loads(result.stdout.strip())
        valid = (type(data) is dict and data.get('schemaId') == 'ARK_NO11_WORKER_PROBE_V2'
                 and type(data.get('workers')) is list
                 and len(data['workers']) <= 512
                 and all(type(x) is dict and
                         type(x.get('pid')) is int and x['pid'] > 0 and
                         type(x.get('parentPid')) is int and
                         x.get('role') in ('LIVE', 'CHART', 'DATA')
                         for x in data['workers']))
    except (ValueError, TypeError):
        valid = False
        data = {}
    if not valid or bool(data['workers']) != (result.returncode == 3):
        print('NO11_NIGHTLY_RESUME_WORKER_PROBE=MALFORMED_RESPONSE', flush=True)
        need(False, 'WORKER_QUERY_FAILED')
    if data['workers']:
        print('NO11_NIGHTLY_RESUME_WORKER_PROBE=OTHER_ARK_WORKERS_RUNNING', flush=True)
        for item in data['workers'][:12]:
            print('NO11_NIGHTLY_RESUME_ACTIVE_WORKER=PID_{}|ROLE_{}'.format(
                item['pid'], item['role']), flush=True)
        need(False, 'OLD_WORKER_STILL_RUNNING')
    print('NO11_NIGHTLY_RESUME_WORKER_PROBE=NO_UNRELATED_ARK_WORKERS', flush=True)


def run_logged(argv, log, timeout=28800):
    """Persist output while running, including stderr; preserve failed attempts."""
    with Path(log).open('xb', buffering=0) as out:
        p = subprocess.Popen(argv, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             close_fds=True)
        started = time.monotonic()
        try:
            last = 0
            while p.poll() is None:
                if time.monotonic() - started > timeout:
                    # This is only our DATA child; no broker process is invoked.
                    p.terminate()
                    need(False, 'DATA_CHILD_TIMEOUT_CHECK_DESCENDANTS')
                elapsed = int(time.monotonic() - started)
                if elapsed >= last + 15:
                    last = elapsed
                    print('NO11_NIGHTLY_RESUME_HEARTBEAT=' + str(elapsed) + '|LOG_BYTES=' + str(Path(log).stat().st_size), flush=True)
                time.sleep(0.2)
            os.fsync(out.fileno())
            need(p.returncode == 0, 'NATIVE_STAGE_FAILED_SEE_PERSISTED_LOG')
        except BaseException:
            # Never repeat a child implicitly; a new invocation checks all workers.
            raise


def native(binding_file, symbols_file, weekend=False):
    binding_file = safe(binding_file)
    binding = read(binding_file)
    need(binding.get('schemaId') == 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1' and
         binding.get('orderTransmission') is False and binding.get('manualPriceInputRequired') is False and
         binding.get('manualEvidenceRequired') is False, 'BINDING_CONTRACT')
    engine = safe(binding['engine'], True)
    root = safe(binding['dailyCycleRoot'], True)
    symbols_file = safe(symbols_file)
    paths = {'original': safe(engine / 'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1'),
             'schedule': safe(engine / 'tools/no11_weekly_g1_refresh.mjs'),
             'validator': safe(Path(__file__).with_name('no11_selection_status.py'))}
    for key in ('runner', 'scopeTool', 'dailyCycleTool', 'handoff'):
        paths[key] = safe(binding[key])
        need(digest(paths[key].read_bytes()) == binding[key + 'Sha256'], 'BOUND_SOURCE_CHANGED')
    need(digest(paths['validator'].read_bytes()) == binding.get('nightlyResumeValidatorSha256'), 'VALIDATOR_SOURCE_CHANGED')
    python = safe(binding['python'])
    args = ['node', str(paths['schedule']), 'schedule'] + (['--weekend-friday'] if weekend else [])
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
    need(r.returncode == 0, 'SCHEDULE_UNAVAILABLE')
    schedule = json.loads(r.stdout)
    asof, target = schedule.get('asOfSession'), schedule.get('sessionDate')
    need(schedule.get('schemaId') == 'ARK_NO11_WEEKLY_REFRESH_SCHEDULE_V1' and
         schedule.get('orderTransmission') is False and all(type(v) is str and
         re.fullmatch(r'20[0-9]{2}-[0-9]{2}-[0-9]{2}', v) for v in (asof, target)), 'SCHEDULE_CONTRACT')
    need(asof < target and target >= datetime.now(JST).date().isoformat(), 'TARGET_PASSED')
    if weekend:
        need(schedule.get('weekendMaintenance') is True and schedule.get('mode') == 'FULL_MARKET_FRIDAY', 'WEEKEND_CONTRACT')
    # Pin the actual installed collector/parser bytes, including local Clean fixes.
    pins = {key: digest(p.read_bytes()) for key, p in paths.items()}
    for folder in ('tools', 'windows'):
        for p in sorted((engine / folder).iterdir()):
            if p.is_file() and p.suffix in ('.py', '.ps1', '.mjs', '.js'):
                safe(p)
                pins[folder + '/' + p.name] = digest(p.read_bytes())
    identity = {'asOfSession': asof, 'sessionDate': target, 'engine': str(engine),
                'mode': schedule['mode'], 'symbolsSha256': digest(symbols_file.read_bytes()),
                'pins': pins, 'orderTransmission': False}
    work = root / 'resumable-nightly' / (asof + '_' + target)
    pointer = root / 'prepared-days' / (target + '.json')
    daily = module('no11_bound_daily_for_resume', paths['dailyCycleTool'])
    validator = module('no11_pointer_validator_for_resume', paths['validator'])

    def validate(ptr, log_sha):
        data, hand, chart, mask = validator.validate_pointer(ptr, root)
        need(data['sessionDate'] == target and data['previousSession'] == asof, 'HANDOFF_DATE')
        if log_sha is not None:
            need(data.get('nightlyLogSha256') == log_sha, 'HANDOFF_CAPTURE_LINEAGE')

    def capture(log):
        no_workers()
        argv = ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                '-File', str(paths['original']), '-FullSymbolsFile', str(symbols_file),
                '-PythonExecutable', str(python)]
        if weekend:
            argv.append('-WeekendFriday')
        run_logged(argv, log)
        result = daily.parse_nightly(log.read_bytes())
        need(result['sessionDate'] == target and result['previousSession'] == asof, 'CAPTURE_DATE')

    def publish(log):
        result = daily.parse_nightly(log.read_bytes())
        need(result['sessionDate'] == target and result['previousSession'] == asof, 'CAPTURE_DATE')
        run_logged([str(python), '-B', '-X', 'utf8', str(paths['dailyCycleTool']), 'stage',
                    '--binding', str(binding_file), '--nightly-log', str(log)],
                   work / ('publish-' + uuid.uuid4().hex + '.log'), timeout=1800)

    Pipeline(work, identity, pointer, capture, publish, validate, no_workers).run()
    print('NO11_DAILY_CYCLE_SESSION=' + target)
    print('NO11_DAILY_CYCLE_ASOF=' + asof)
    print('NO11_DAILY_CYCLE_STATUS=NEXT_SESSION_HANDOFF_READY')
    print('NO11_NIGHTLY_CYCLE=NEXT_SESSION_READY_FOR_TRADE_BUTTON')
    print('TRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binding', required=True, type=Path)
    p.add_argument('--symbols', required=True, type=Path)
    p.add_argument('--weekend-friday', action='store_true')
    a = p.parse_args()
    try:
        native(a.binding, a.symbols, a.weekend_friday)
    except Exception as exc:
        reason = str(exc)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+', reason):
            reason = 'NO11_NIGHTLY_RESUME_UNVERIFIED_SOURCE_OR_RUNTIME'
        print('NO11_NIGHTLY_RESUME=BLOCKED|' + reason)
        print('SAVED_RECEIPTS_PRESERVED=True\nTRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')
        raise SystemExit(2)

if __name__ == '__main__':
    main()
