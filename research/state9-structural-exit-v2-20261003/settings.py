"""Research I/O and dated clock only. No policy, network or model code."""
from pathlib import Path
import datetime, gzip, hashlib, json, math
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
INPUT = WORKSPACE / 'inputs'
PRIVATE = WORKSPACE / 'private_structural_v2'
ENTRY_FILE = INPUT / 'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'
SAFETY = {k: False for k in ('executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed', 'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted', 'productionReady')}

def now():
    return datetime.datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def load(p):
    p = Path(p)
    with (gzip.open(p, 'rt') if p.suffix == '.gz' else p.open()) as f:
        return json.load(f)

def rows(p):
    with gzip.open(p, 'rt') as f:
        for s in f:
            yield json.loads(s)

def save(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n')

def jsonline(x):
    return (json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()

def stamp(day, minute):
    return day + 'T%02d:%02d:00+09:00' % divmod(minute, 60)

def regular_end(day):
    return 900 if day < '2024-11-05' else 925

def session_close(day):
    return 900 if day < '2024-11-05' else 930

def regular_starts(day):
    return list(range(540, 690)) + list(range(750, regular_end(day)))

def active_minutes(day, start, end):
    return sum(max(0, min(end, b) - max(start, a)) for a, b in ((540, 690), (750, regular_end(day))))

def valid_raw(a):
    return len(a) == 7 and all(math.isfinite(float(x)) for x in a) and a[3] > 0 and a[3] <= min(a[1], a[4]) <= max(a[1], a[4]) <= a[2] and a[5] >= 0 and a[6] >= 0

def entries():
    assert sha(ENTRY_FILE) == 'e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb'
    all_rows = list(rows(ENTRY_FILE))
    result = [r for r in all_rows if r['entry_status'] == 'FIRST_ENTRY']
    assert len(all_rows) == 2155 and len(result) == 1600 and len({r['watch_key'] for r in result}) == 1600
    return result
