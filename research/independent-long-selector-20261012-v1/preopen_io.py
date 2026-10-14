"""Private immutable I/O. No network, credentials, orders or public artifacts."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from preopen_selector import PreopenError


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def private_path(path, root):
    root = Path(root).resolve()
    import subprocess
    for ancestor in (root, *root.parents):
        if not (ancestor / ".git").exists():
            continue
        check = subprocess.run(["git", "-C", str(ancestor), "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True)
        if check.returncode == 0 and Path(check.stdout.strip()).resolve() == ancestor:
            raise PreopenError("PRIVATE_ROOT_INSIDE_GIT_CHECKOUT")
    path = Path(path)
    path = (path if path.is_absolute() else root / path).resolve()
    if not path.is_relative_to(root):
        raise PreopenError("PATH_OUTSIDE_EXPLICIT_PRIVATE_ROOT")
    return path


def sha_file(path):
    h = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
            size += len(part)
    return h.hexdigest(), size


def verify_entry(entry, root):
    path = private_path(entry["path"], root)
    if not path.is_file():
        raise PreopenError("PRIVATE_INPUT_NOT_MOUNTED:" + path.name)
    sha, size = sha_file(path)
    if sha != entry.get("sha256") or size != entry.get("bytes"):
        raise PreopenError("PRIVATE_INPUT_HASH_OR_SIZE_MISMATCH")
    return path


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream, ensure_ascii=False, sort_keys=True,
                  allow_nan=False, indent=2)
        stream.write("\n")
    sha, size = sha_file(path)
    return {"path": str(path), "sha256": sha, "bytes": size}


def read_jsonl(entry, root):
    path = verify_entry(entry, root)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise PreopenError("NONOBJECT_INPUT_RECORD")
                yield row


def require_safe_flags(value):
    for name in ("executionAllowed", "brokerWriteAllowed",
                 "excelOrderWriteAllowed", "rssOrderFunctionAllowed",
                 "liveTradingAllowed", "paperTradingAllowed",
                 "automaticPromotionAllowed", "productionUpdateAllowed",
                 "transmitted", "productionReady", "entryAllowed"):
        if value.get(name) is not False:
            raise PreopenError("UNSAFE_OR_MISSING_FLAG:" + name)


SAFE_FLAGS = {k: False for k in (
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
    "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted",
    "productionReady", "entryAllowed")}
