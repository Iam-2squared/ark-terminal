"""Reviewed repairs to installed DATA->handoff->Trade-preparation connections.

No signal, ranking, capital, quantity, entry or exit rule is changed.
Transform the already-bound local sources and retain unrelated local edits.
No collector replacement, real Excel calls or order submission by this module.
"""
from __future__ import annotations
import ast

MARK='ARK_NO11_CIRCUIT_AUDIT_V1'


def need(ok,reason):
    if not ok:raise ValueError('NO11_CIRCUIT_REPAIR_'+reason)


def once(s,old,new):
    need(s.count(old)==1,'REVIEWED_SOURCE_CONTEXT_CHANGED')
    return s.replace(old,new,1)


def function_span(text,name):
    tree=ast.parse(text)
    matches=[x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name==name]
    need(len(matches)==1,'FUNCTION_NOT_UNIQUE_'+name.upper())
    node=matches[0]
    first=min([node.lineno]+[d.lineno for d in node.decorator_list])
    lines=text.splitlines(keepends=True)
    return sum(map(len,lines[:first-1])),sum(map(len,lines[:node.end_lineno]))


LOCK='''@contextmanager
def lock(path):
    # ARK_NO11_CIRCUIT_AUDIT_V1: OS-owned exclusion, not filename existence.
    # A crash releases the lock; never unlink a shared lock file (ABA race).
    path = Path(path)
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
        except OSError:
            raise ValueError('NO11_AUTOSTART_PREPARATION_ALREADY_RUNNING') from None
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
'''

DECODE_LOG='''def decode_nightly_log(raw):
    # ARK_NO11_CIRCUIT_AUDIT_V1: no silent U+FFFD replacement in paths.
    if raw.startswith((b'\\xff\\xfe', b'\\xfe\\xff')):
        return raw.decode('utf-16')
    for encoding in ('utf-8-sig', 'cp932'):
        try:
            text = raw.decode(encoding)
            need('\\x00' not in text, 'NIGHTLY_LOG_ENCODING')
            return text
        except UnicodeDecodeError:
            continue
    need(False, 'NIGHTLY_LOG_ENCODING')


'''

ATOMIC_POINTER='''    else:
        # ARK_NO11_CIRCUIT_AUDIT_V1: publish complete bytes, never overwrite.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('wb', dir=directory,
                    prefix='.handoff-pending-', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, dest)
            except FileExistsError:
                need(dest.read_bytes() == raw, 'DAY_ALREADY_PINNED_TO_DIFFERENT_SOURCE')
            if os.name != 'nt':
                descriptor = os.open(directory, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return dest'''

RUN_LOGGED='''def run_logged(argv, log, timeout=28800):
    # ARK_NO11_CIRCUIT_AUDIT_V1: actual child path, PID, progress and exit code.
    log = Path(log)
    print('NO11_NIGHTLY_RESUME_CHILD_LOG=' + str(log), flush=True)
    with log.open('xb', buffering=0) as out:
        child = subprocess.Popen(argv, stdout=out, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, close_fds=True)
        print('NO11_NIGHTLY_RESUME_CHILD_PID=' + str(child.pid), flush=True)
        started = time.monotonic()
        last = 0
        pos = 0
        pending = b''

        def relay():
            nonlocal pos, pending
            with log.open('rb') as src:
                src.seek(pos)
                block = src.read(262144)
            pos += len(block)
            pieces = (pending + block).split(b'\\n')
            pending = pieces.pop()
            for line in pieces:
                if line.startswith((b'NO11_', b'ORDER_TRANSMISSION=', b'TRADE_LAUNCHED=')):
                    try:
                        text = line.rstrip(b'\\r').decode('utf-8-sig')
                    except UnicodeDecodeError:
                        try:
                            text = line.rstrip(b'\\r').decode('cp932')
                        except UnicodeDecodeError:
                            continue
                    print(text, flush=True)
            return bool(block)

        while child.poll() is None:
            if time.monotonic() - started > timeout:
                child.terminate()
                print('NO11_NIGHTLY_RESUME_CHILD_TIMEOUT=True', flush=True)
                need(False, 'DATA_CHILD_TIMEOUT_CHECK_DESCENDANTS')
            elapsed = int(time.monotonic() - started)
            if elapsed >= last + 15:
                last = elapsed
                relay()
                print('NO11_NIGHTLY_RESUME_HEARTBEAT=' + str(elapsed)
                      + '|LOG_BYTES=' + str(log.stat().st_size), flush=True)
            time.sleep(0.2)
        os.fsync(out.fileno())
        while relay():
            pass
        print('NO11_NIGHTLY_RESUME_CHILD_EXIT=' + str(child.returncode), flush=True)
        need(child.returncode == 0, 'NATIVE_STAGE_FAILED_SEE_PERSISTED_LOG')
'''

VISIBLE_MAIN='''@contextmanager
def visible_update_output(binding_file):
    # Existing OPEN LOGS opens this directory. Keep the original deep logs too.
    # This changes observability, not data source, retry or trading decisions.
    folder = safe(binding_file).parent / 'oneclick-logs'
    folder.mkdir(exist_ok=True)
    safe(folder, True)
    path = folder / ('DataUpdate-' + datetime.now(JST).strftime('%Y-%m-%d-%H%M%S')
                     + '-' + uuid.uuid4().hex + '.log')
    previous = sys.stdout
    with path.open('x', encoding='utf-8', buffering=1) as output:
        class Tee:
            def write(self, text):
                output.write(text)
                try:
                    return previous.write(text)
                except (OSError, ValueError):
                    return len(text)
            def flush(self):
                output.flush()
                try:
                    previous.flush()
                except (OSError, ValueError):
                    pass
        sys.stdout = Tee()
        try:
            print('NO11_UPDATE_VISIBLE_LOG=' + str(path), flush=True)
            yield path
        finally:
            sys.stdout = previous
            output.flush()
            os.fsync(output.fileno())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binding', required=True, type=Path)
    p.add_argument('--symbols', required=True, type=Path)
    p.add_argument('--weekend-friday', action='store_true')
    a = p.parse_args()
    with visible_update_output(a.binding):
        try:
            native(a.binding, a.symbols, a.weekend_friday)
        except Exception as exc:
            reason = str(exc)
            if not re.fullmatch(r'NO11_[A-Z0-9_]+', reason):
                reason = 'NO11_NIGHTLY_RESUME_UNVERIFIED_SOURCE_OR_RUNTIME'
            print('NO11_NIGHTLY_RESUME=BLOCKED|' + reason, flush=True)
            print('SAVED_RECEIPTS_PRESERVED=True\\nTRADE_LAUNCHED=False\\nORDER_TRANSMISSION=False', flush=True)
            raise SystemExit(2)
'''


def transform_bridge(text):
    text=once(text,"        original_chart, original_sha = load(old['precomputedChartReceipt'])",
                   "        original_chart, original_raw = load(old['precomputedChartReceipt'])\n        original_sha = digest(original_raw)")
    a,b=function_span(text,'lock')
    need("path.open('xb')" in text[a:b] and 'path.unlink()' in text[a:b],'ORIGINAL_LOCK_CHANGED')
    text=text[:a]+LOCK+text[b:]
    text=once(text,"        if merged is None:\n            result, broker_path = make_initial_broker(",
        "        if merged is None:\n            candidate_root = safe(prepared['privateRoot'], True)\n            need(not (candidate_root / ('received-session-' + today + '.active.json')).exists(),\n                 'ACTIVE_SESSION_NO_REBIND')\n            result, broker_path = make_initial_broker(")
    return text


def transform_cycle(text):
    text=once(text,'from datetime import date','from datetime import date, datetime, timedelta, timezone')
    text=once(text,'import uuid\n','import uuid\nimport tempfile\n')
    text=once(text,'def parse_nightly(raw):',DECODE_LOG+'def parse_nightly(raw):')
    text=once(text,'raw.decode("utf-8-sig",errors="replace").splitlines()','decode_nightly_log(raw).splitlines()')
    text=once(text,'    else:\n        with dest.open("xb") as f:\n            f.write(raw); f.flush();os.fsync(f.fileno())\n    return dest',ATOMIC_POINTER)
    text=once(text,'    today=date.today()','    today=datetime.now(timezone(timedelta(hours=9))).date()')
    return text


def transform_worker(text):
    need('ARK_NO11_NIGHTLY_RESUME_WORKER_PROBE_V2' in text,'WORKER_PROBE_V2_REQUIRED')
    a,b=function_span(text,'run_logged')
    need('subprocess.Popen(argv' in text[a:b] and 'NATIVE_STAGE_FAILED_SEE_PERSISTED_LOG' in text[a:b],'ORIGINAL_LOG_RUNNER_CHANGED')
    text=text[:a]+RUN_LOGGED+text[b:]
    a,b=function_span(text,'main')
    need('native(a.binding, a.symbols, a.weekend_friday)' in text[a:b],'ORIGINAL_MAIN_CHANGED')
    return text[:a]+VISIBLE_MAIN+text[b:]


def transform(kind,raw):
    bom=raw.startswith(b'\xef\xbb\xbf');text=raw.decode('utf-8-sig')
    newline='\r\n' if '\r\n' in text else '\n'
    text=text.replace('\r\n','\n');need('\r' not in text,'SOURCE_LINE_ENDING')
    if MARK in text:
        compile(text,'<already-fixed-'+kind+'>','exec');return raw
    fn={'bridge':transform_bridge,'cycle':transform_cycle,'worker':transform_worker}.get(kind)
    need(fn is not None,'UNKNOWN_COMPONENT')
    updated=fn(text);compile(updated,'<circuit-fixed-'+kind+'>','exec')
    return (b'\xef\xbb\xbf' if bom else b'')+updated.replace('\n',newline).encode('utf-8')
