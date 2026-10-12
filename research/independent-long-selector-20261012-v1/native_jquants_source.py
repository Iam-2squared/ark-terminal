"""Streaming source adapter for SHA-verified J-Quants private GitHub originals.

ONLY processes caller-mounted files; no remote fetch, API calls, GitHub pushes,
broker functions, raw rewriting or latent portfolio actions.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

JST = timezone(timedelta(hours=9))
NATIVE_MINUTE_HEADER = ("Date", "Time", "Code", "O", "H", "L", "C", "Vo", "Va")
MINUTE_SOURCE_ATTESTATION = "HISTORICAL_INTERVAL_CLOSE_ASSUMED_NOT_VENDOR_RECEIVE_TIME"
GITHUB_ORIGINAL_SHA_STATUS = "REQUIRED_EXACT_MATCH"
ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_HM = re.compile(r"^\d{2}:\d{2}$")


class SourceError(ValueError):
    pass


def verify_native_original(path: str | Path, expected_sha256: str,
                           expected_bytes: int | None = None) -> dict:
    """No partial/raw-name-only acceptance; exact original byte digest required."""
    f = Path(path)
    if not f.is_file():
        raise SourceError("MISSING_GITHUB_ORIGINAL")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise SourceError("EXPECTED_SHA256_REQUIRED")
    h = hashlib.sha256()
    n = 0
    with f.open("rb") as stream:
        while part := stream.read(1024 * 1024):
            h.update(part)
            n += len(part)
    if h.hexdigest() != expected_sha256 or (
        expected_bytes is not None and n != expected_bytes
    ):
        raise SourceError("GITHUB_NATIVE_SOURCE_HASH_OR_SIZE_MISMATCH")
    return {"verified": True, "bytes": n, "sha256": h.hexdigest(),
            "filename": f.name}


def manifest_paths(allocation_json: str | Path, raw_root: str | Path
                   ) -> list[dict]:
    """No guessing from file names; native allocation contains exact object keys."""
    obj = json.loads(Path(allocation_json).read_text(encoding="utf-8"))
    entries = obj.get("objects")
    if not isinstance(entries, list):
        raise SourceError("INVALID_ALLOCATION")
    root = Path(raw_root).resolve()
    result = []
    for item in entries:
        name = item["object_key"]
        if not isinstance(name, str) or not name.endswith(".csv.gz"):
            raise SourceError("INVALID_NATIVE_KEY")
        resolved = (root / name).resolve()
        if not resolved.is_relative_to(root):
            raise SourceError("SOURCE_PATH_TRAVERSAL")
        result.append({"dataset": item["dataset"], "objectKey": name,
                       "rawPath": str(resolved), "expectedBytes": item["bytes"]})
    return result


def _native_price(value: str, name: str) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError) as exc:
        raise SourceError(f"INVALID_{name}_PRICE") from exc
    if not (0 < f < float("inf")):
        raise SourceError(f"INVALID_{name}_PRICE")
    return f


def _nonnegative(value: str, name: str) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError) as exc:
        raise SourceError(f"INVALID_{name}_AMOUNT") from exc
    if not (0 <= f < float("inf")):
        raise SourceError(f"INVALID_{name}_AMOUNT")
    return f


def iter_native_minute(path: str | Path, *,
                       start_session: str | None = None,
                       end_session: str | None = None
                       ) -> Iterator[dict]:
    """Read one original monthly or live object; preserve sparse native rows.

    File is expected Date→Code→Time sorted; output remains one row per original
    bar. Price is RAW unadjusted. No price/volume fill or interpolation.
    Provider-receive time is unknown for historical copies.

    15:30 exchange-auction rows are separately tagged and NEVER counted
    as continuous one-minute bars. Any alternative provider semantics must
    have its own independently audited source-contract version.
    """
    previous_order: tuple[str, str, str] | None = None
    with gzip.open(path, "rt", newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not set(NATIVE_MINUTE_HEADER).issubset(reader.fieldnames):
            raise SourceError("NATIVE_MINUTE_SCHEMA_MISMATCH")
        for n, row in enumerate(reader, 2):
            day, clock, code = row["Date"], row["Time"], row["Code"]
            if not ISO_DAY.fullmatch(day) or not TIME_HM.fullmatch(clock):
                raise SourceError(f"BAD_MINUTE_TIMESTAMP_ROW:{n}")
            if not code or not isinstance(code, str):
                raise SourceError("EMPTY_SECURITY_CODE")
            order = day, code, clock
            if previous_order is not None and order <= previous_order:
                raise SourceError("DUPLICATED_OR_UNSORTED_NATIVE_ROW")
            previous_order = order
            if start_session and day < start_session:
                continue
            if end_session and day > end_session:
                break
            dt = datetime.fromisoformat(f"{day}T{clock}:00+09:00")
            is_auction = clock == "15:30"
            if clock < "09:00" or clock > "15:30":
                raise SourceError("OUTSIDE_RECOGNIZED_JPX_SESSION")
            o, h, l, c = [_native_price(row[col], col) for col in ("O","H","L","C")]
            if not l <= min(o,c) <= max(o,c) <= h:
                raise SourceError("NATIVE_MINUTE_OHLC_INCONSISTENT")
            volume, turnover = _nonnegative(row["Vo"],"Vo"), _nonnegative(row["Va"],"Va")
            if is_auction:
                observed = dt
                kind = "TERMINAL_AUCTION_REFERENCE"
            else:
                observed = dt + timedelta(minutes=1)
                kind = "CONTINUOUS_1M"
            yield {
                "session": day, "symbol": code, "kind": kind,
                "start": dt.isoformat(), "end": observed.isoformat(),
                "availableAt": observed.isoformat(),
                "availabilityBasis": MINUTE_SOURCE_ATTESTATION,
                "open": o,"high": h,"low": l,"close": c,
                "volume": volume,"turnover": turnover,
                "rawPriceBasis": "UNADJUSTED_RAW",
            }


def collect_one_day_for_schema_diagnostics(path: str | Path,
                                           date: str) -> dict:
    """Counts only, doesn't inspect future labels or emit symbol rows."""
    n = 0
    times = set()
    symbols = set()
    bars0930 = 0
    bars1500 = 0
    auction_n = 0
    for row in iter_native_minute(path, start_session=date,end_session=date):
        n += 1
        symbols.add(row["symbol"])
        clock = row["start"][11:16]
        times.add(clock)
        bars0930 += clock == "09:30"
        bars1500 += clock == "15:00"
        auction_n += row["kind"] == "TERMINAL_AUCTION_REFERENCE"
    return {
        "date": date, "rows": n,"symbols":len(symbols),
        "observedTimeCount":len(times),
        "minTime":min(times) if times else None,
        "maxTime":max(times) if times else None,
        "rows0930":bars0930,"rows1500":bars1500,
        "terminalAuctionRows":auction_n,
        "historicalReceiveTimeCertified":False,
        "futureOutcomesOpened":False,
    }
