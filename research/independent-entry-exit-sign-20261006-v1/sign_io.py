"""IO contracts for a standalone sign study; no Capital runtime dependency."""
import datetime as dt
import gzip
import hashlib
import json
import os
import re
from pathlib import Path

CODE = Path(__file__).resolve().parent
REPO = CODE.parents[1]
WORK = Path(os.environ.get("ARK_INDEPENDENT_WORKSPACE", str(REPO.parent)))
OUT = REPO / "docs/evidence/independent-entry-exit-sign-20261006-v1"
PRIVATE = WORK / "work/independent_sign_private"
OLD = WORK / "work/old_sign"
BASIS = WORK / "work/basis"
SPLIT_SOURCE = BASIS / "docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json"
SIGN_FIELDS = {"entry_id", "session", "sign_status", "y_plus", "label_maturity", "source_hash"}

def now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="microseconds")

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def rows(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]

def save(path, value, exclusive=False):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w") as f:
        f.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n")

def gzsave(path, values, exclusive=True):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb" if exclusive else "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", filename="", mtime=0) as z:
            for value in values:
                z.write((canonical(value) + "\n").encode())

def validate_sign(row):
    assert set(row) == SIGN_FIELDS, "SIGN_VIEW_NOT_ALLOWLISTED"
    direction = {"PLUS": 1, "MINUS": 0, "EXACT_ZERO": None, "UNKNOWN": None}
    assert row["sign_status"] in direction and row["y_plus"] == direction[row["sign_status"]]
    return row

class SignIndex:
    """Read identities first; decode sign payloads only for the requested stage."""
    def __init__(self, path):
        self.lines = {}; self.read_log = []
        with gzip.open(path, "rt") as f:
            for line in f:
                key = re.search(r'"entry_id"\s*:\s*"([^"]+)"', line).group(1)
                assert key not in self.lines, "DUPLICATE_TEACHER"
                self.lines[key] = line

    def get(self, entry_id, before=None, purpose="evaluation"):
        row = validate_sign(json.loads(self.lines[entry_id]))
        if before is not None:
            assert row["session"] < before, "CURRENT_OR_FUTURE_SIGN_READ"
        self.read_log.append({"entry_id": entry_id, "before": before, "purpose": purpose})
        return row

def checkpoint(name, status, completed, unexecuted, next_action):
    state = read(OUT / "CURRENT_STATE.json")
    ledger = read(OUT / "FIT_LEDGER.json") if (OUT / "FIT_LEDGER.json").exists() else {"new_fits": 0, "preprocessing_fits": 0}
    state.update(exact_jst=now(), status=status, completed=completed, unexecuted=unexecuted, next_action=next_action)
    for key in ["new_fits", "preprocessing_fits", "technical_retries", "equivalent_fits_reused"]:
        state["counts_this_execution"][key] = ledger.get(key, 0)
    save(OUT / "CURRENT_STATE.json", state)
    save(OUT / "checkpoints" / (name + ".json"), state, exclusive=True)

