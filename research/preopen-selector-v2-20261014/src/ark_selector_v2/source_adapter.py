"""Approved CSV.gz slices. Inspect record dates before parsing any numbers.

Column names, units, dated identities and RAW comparable suffixes are explicit
owner-pinned source contracts. There are no guessed J-Quants field aliases,
code-suffix classifications, adjusted-price fallbacks or provider requests.
"""
from __future__ import annotations
import csv
import gzip
import io
import re
from decimal import Decimal, localcontext
from datetime import date
from pathlib import Path
from typing import Any
from .artifact_io import sha_file
from .contracts import Candle, Identity, digest
from .exact_math import V2Error, rational

CSV_ROUTES = {"DAILY": "JQUANTS_CSV_GZIP_RAW_V1", "MASTER": "JQUANTS_CSV_GZIP_MASTER_V1"}


def validate_profile(entry: dict[str, Any], pre: dict[str, Any]) -> dict[str, Any]:
    profile = pre.get("source_contracts", {}).get(entry["format"])
    fields = {"schema", "dataset", "header", "date_column", "symbol_column", "fields",
              "units", "factors", "missing_tokens", "identities", "raw_suffixes",
              "all_null_status", "max_uncompressed_bytes"}
    if not isinstance(profile, dict) or set(profile) != fields or profile["schema"] != "ARK_V2_TABULAR_SOURCE_PROFILE_V1":
        raise V2Error("APPROVED_TABULAR_SOURCE_CONTRACT_REQUIRED")
    dataset = entry["dataset"]
    if profile["dataset"] != dataset or entry["format"] != CSV_ROUTES.get(dataset):
        raise V2Error("TABULAR_SOURCE_DATASET_OR_ROUTE")
    if entry["evidence"]["source_contract_hash"] != digest(profile):
        raise V2Error("TABULAR_SOURCE_CONTRACT_HASH")
    header = profile["header"]
    if (not isinstance(header, list) or len(header) != len(set(header)) or
            not all(isinstance(k, str) and k for k in header) or
            profile["date_column"] not in header or profile["symbol_column"] not in header):
        raise V2Error("TABULAR_EXACT_HEADER_REQUIRED")
    if type(profile["max_uncompressed_bytes"]) is not int or profile["max_uncompressed_bytes"] <= 0:
        raise V2Error("TABULAR_DECOMPRESSION_LIMIT_REQUIRED")
    session = entry["session"]
    identities = profile["identities"].get(session)
    if not isinstance(identities, dict) or not identities:
        raise V2Error("DATED_IDENTITY_RULES_REQUIRED_BEFORE_OPEN")
    for source_symbol, row in identities.items():
        if not isinstance(source_symbol, str) or not source_symbol:
            raise V2Error("EXPLICIT_SOURCE_SYMBOL_MAPPING_REQUIRED")
        Identity(effective_session=date.fromisoformat(session), **row).eligible(date.fromisoformat(session))
    numeric = {"open", "high", "low", "close", "volume", "turnover"}
    if dataset == "DAILY":
        if set(profile["fields"]) != numeric or not set(profile["fields"].values()) <= set(header):
            raise V2Error("EXPLICIT_RAW_COLUMNS_REQUIRED")
        columns = list(profile["fields"].values())
        if (len(set(columns)) != 6 or set(columns) & {profile["date_column"], profile["symbol_column"]} or
                any(re.search(r"adj|adjust|future|outcome|label", column, re.I) for column in columns)):
            raise V2Error("ADJUSTED_OR_OUTCOME_OR_DUPLICATE_RAW_COLUMN")
        if profile["units"] != ["JPY", "SHARES", "JPY"] or set(profile["factors"]) != numeric:
            raise V2Error("EXPLICIT_RAW_UNIT_FACTORS_REQUIRED")
        for factor in profile["factors"].values():
            if rational(factor) <= 0:
                raise V2Error("NONPOSITIVE_UNIT_FACTOR")
        suffixes = profile["raw_suffixes"].get(session, {})
        if set(suffixes) != set(identities) or not all(isinstance(s, str) and s for s in suffixes.values()):
            raise V2Error("ASOF_COMPARABLE_RAW_SUFFIX_REQUIRED")
        if profile["all_null_status"] not in {"NO_TRADE", "INCOMPLETE_SOURCE", "NO_VERIFIED_OPEN"}:
            raise V2Error("NULL_OHLC_SOURCE_CONTRACT_REQUIRED")
    elif profile["fields"] or profile["factors"] or profile["units"] != ["IDENTITY"]:
        raise V2Error("MASTER_SOURCE_CONTRACT_FIELDS")
    return profile


class BoundedStream(io.RawIOBase):
    def __init__(self, source: Any, limit: int):
        self.source = source
        self.limit = limit
        self.count = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: Any) -> int:
        data = self.source.read(len(buffer))
        self.count += len(data)
        if self.count > self.limit:
            raise V2Error("TABULAR_UNCOMPRESSED_SIZE_LIMIT")
        buffer[:len(data)] = data
        return len(data)


def parse_record(row: dict[str, str], profile: dict[str, Any], session: str) -> dict[str, Any]:
    """Called only after the record's exact date and purpose have been admitted."""
    source_symbol = row[profile["symbol_column"]]
    identities = profile["identities"][session]
    if source_symbol not in identities:
        raise V2Error("UNMAPPED_DATED_SOURCE_IDENTITY")
    ident = identities[source_symbol]
    if profile["dataset"] == "MASTER":
        return dict(ident)
    values: dict[str, str | None] = {}
    for key, column in profile["fields"].items():
        text = row[column]
        if text in profile["missing_tokens"]:
            values[key] = None
        else:
            try:
                number = rational(text) * rational(profile["factors"][key])
            except (ValueError, TypeError, ZeroDivisionError) as exc:
                raise V2Error("TABULAR_NONFINITE_OR_INVALID_RAW_NUMBER") from exc
            if key in {"volume", "turnover"} and number < 0:
                raise V2Error("DATA_INTEGRITY_ERROR_ACTIVITY")
            with localcontext() as context:
                context.prec = max(28, len(str(abs(number.numerator))) + len(str(number.denominator)) + 10)
                values[key] = format(Decimal(number.numerator) / Decimal(number.denominator), "f")
    status = profile["all_null_status"] if all(values[k] is None for k in ("open", "high", "low", "close")) else "TRADED"
    Candle.from_values(date.fromisoformat(session), *(values[k] for k in ("open", "high", "low", "close", "volume", "turnover")), status=status)
    return {"canonical_symbol": ident["canonical_symbol"], "market": ident["market"], **values,
            "basis": "RAW", "suffix": profile["raw_suffixes"][session][source_symbol],
            "status": status, "units": ["JPY", "SHARES", "JPY"]}


def read_csv_session(path: Path, entry: dict[str, Any], pre: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    profile = validate_profile(entry, pre)
    session = entry["session"]
    purpose = entry.get("authorized_purpose")
    if (not purpose or session not in pre["allowlists"].get(purpose, []) or
            entry["protected"] is not False or purpose not in entry["original"]["allowed_purposes"] or
            session not in entry["original"]["allowed_record_dates"]):
        raise V2Error("TABULAR_SLICE_NOT_AUTHORIZED_BEFORE_OPEN")
    if sha_file(path) != (entry["sha256"], entry["bytes"]):
        raise V2Error("NATIVE_SOURCE_HASH_OR_SIZE_MISMATCH")
    records = []
    ordinals = []
    seen = set()
    skipped = 0
    with gzip.open(path, "rb") as zipped:
        stream = BoundedStream(zipped, profile["max_uncompressed_bytes"])
        with io.TextIOWrapper(io.BufferedReader(stream), encoding="utf-8-sig", newline="") as text:
            reader = csv.DictReader(text)
            if reader.fieldnames != profile["header"]:
                raise V2Error("TABULAR_HEADER_DRIFT_NO_FALLBACK")
            for ordinal, row in enumerate(reader):
                if None in row or any(v is None for v in row.values()):
                    raise V2Error("TABULAR_MALFORMED_RECORD")
                record_date = row[profile["date_column"]]
                try:
                    if date.fromisoformat(record_date).isoformat() != record_date:
                        raise ValueError(record_date)
                except ValueError as exc:
                    raise V2Error("TABULAR_INVALID_RECORD_DATE") from exc
                # Other dates are compared as metadata strings only. Their price,
                # outcome, classification and symbol fields are never converted.
                if record_date != session:
                    skipped += 1
                    continue
                record = parse_record(row, profile, session)
                key = (record["canonical_symbol"], record["market"])
                if key in seen:
                    raise V2Error("DUPLICATE_NATIVE_IDENTITY")
                seen.add(key)
                records.append(record)
                ordinals.append(ordinal)
                if len(records) > pre["resource_limits"]["universe_rows_upper_bound"]:
                    raise V2Error("SOURCE_UNIVERSE_EXCEEDS_PREFLIGHT_BOUND")
    if not records:
        raise V2Error("REQUIRED_SESSION_ABSENT_FROM_MONTHLY_SOURCE")
    schema = "NATIVE_RAW_SESSION_V1" if entry["dataset"] == "DAILY" else "NATIVE_DATED_MASTER_V1"
    return {"schema": schema, "session": session, "records": records}, {
        "source_id": entry["original"]["source_id"], "source_sha256": entry["sha256"],
        "session": session, "purpose": purpose, "source_contract_sha256": digest(profile),
        "original_ordinals": ordinals, "selected_records": len(records),
        "other_date_records_numeric_parsed": 0, "other_date_records_skipped": skipped}
