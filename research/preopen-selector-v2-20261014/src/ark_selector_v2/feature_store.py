"""Streaming SQLite feature cache bound to complete policy and provenance."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable
import json
import sqlite3
from .contracts import digest, forbid_outcomes, validate_features
from .exact_math import V2Error

CACHE_KEYS={"input","code","policy","basis","calendar","phase","schema"}


def cache_identity(binding: dict[str,str]) -> str:
    if set(binding)!=CACHE_KEYS or binding["basis"]!="RAW":
        raise V2Error("INCOMPLETE_CACHE_BINDING")
    return digest(binding)


def write_features(path: Path, rows: Iterable[dict[str,Any]], binding: dict[str,str]) -> str:
    bound=cache_identity(binding)
    if path.exists() or path.is_symlink():
        raise V2Error("FEATURE_STORE_ALREADY_EXISTS")
    with path.open("xb"):
        pass
    try:
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE binding(hash TEXT PRIMARY KEY, json TEXT NOT NULL)")
            db.execute("INSERT INTO binding VALUES (?,?)",(bound,json.dumps(binding,sort_keys=True)))
            db.execute("CREATE TABLE features(session TEXT,symbol TEXT,market TEXT,payload TEXT,hash TEXT,PRIMARY KEY(session,symbol,market))")
            for row in rows:
                forbid_outcomes(row)
                if set(row)!={"session","canonical_symbol","market","features","provenance"}:
                    raise V2Error("UNKNOWN_FEATURE_ROW_FIELD")
                validate_features(row["features"])
                payload=json.dumps(row,allow_nan=False,separators=(",",":"))
                db.execute("INSERT INTO features VALUES (?,?,?,?,?)",(row["session"],row["canonical_symbol"],row["market"],payload,digest(row)))
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise V2Error("FEATURE_STORE_INTEGRITY_ERROR")
    except Exception:
        # Failed artifacts remain available for audit; never retry/overwrite.
        raise
    return bound


def read_features(path: Path, binding: dict[str,str]):
    bound=cache_identity(binding)
    with sqlite3.connect(path.as_uri()+"?mode=ro",uri=True) as db:
        if db.execute("SELECT hash FROM binding").fetchone()[0]!=bound:
            raise V2Error("CACHE_HASH_DRIFT")
        for payload,h in db.execute("SELECT payload,hash FROM features ORDER BY session,symbol,market"):
            row=json.loads(payload)
            if digest(row)!=h:
                raise V2Error("FEATURE_ROW_HASH_MISMATCH")
            yield row
