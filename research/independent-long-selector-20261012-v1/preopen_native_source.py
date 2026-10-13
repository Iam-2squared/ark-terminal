"""Offline native admission, deterministic SQLite shards and exact RAW labels.

Market use needs a separately evidenced reuse basis and reconciled admission.
This module cannot obtain data, confer rights or release a protected session.
"""
from __future__ import annotations

import csv
import gzip
import json
import re
import sqlite3
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from preopen_io import verify_entry, private_path, write_json, SAFE_FLAGS
from preopen_reuse_authorization import validate_reuse_authorization, REPOSITORIES
from preopen_selector import (CONTRACT, LABEL, PreopenError, day, stamp,
                              rational, symbol, digest, JST)

MARKETS = {"0111":"PRIME", "0112":"STANDARD", "0113":"GROWTH"}
NULLS = ("", None, "null", "Null")
DATASETS = ("DAILY", "DATED_MASTER", "MINUTE", "TICK", "FIN_SUMMARY",
            "VALUATION", "EARNINGS_DATE", "TOPIX", "INVESTOR_TYPES")


@contextmanager
def open_original_records(path, source):
    """Native gzip CSV or an intact stored v2 daily JSON page, not a rewrite.

    JSON numeric lexemes are strings until session admission. A bounded single
    original page is decoded, never a multi-year object graph. Pagination must
    be complete; the original's SHA/bytes are checked by the caller first.
    """
    required=set(source["requiredHeader"])
    fmt=source.get("sourceFormat", "NATIVE_GZIP_CSV")
    if fmt == "NATIVE_GZIP_CSV":
        with gzip.open(path,"rt",encoding="utf-8",newline="") as stream:
            reader=csv.DictReader(stream)
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise PreopenError("NATIVE_EXACT_HEADER_CONTRACT_MISMATCH:" + source["dataset"])
            yield reader,"GZIP_CRC_PASS"
    elif fmt == "JQUANTS_V2_DAILY_API_JSON":
        if source["dataset"] != "DAILY" or Path(path).stat().st_size > 32*1024**2:
            raise PreopenError("API_DAILY_FORMAT_OR_PAGE_MEMORY_BUDGET")
        with Path(path).open("rt",encoding="utf-8") as stream:
            payload=json.load(stream,parse_float=str,parse_int=str)
        if (not isinstance(payload,dict) or not isinstance(payload.get("data"),list)
                or payload.get("pagination_key") not in (None,"")):
            raise PreopenError("API_DAILY_NOT_COMPLETE_SINGLE_ORIGINAL_PAGE")
        def rows():
            for row in payload["data"]:
                if not isinstance(row,dict) or not required.issubset(row):
                    raise PreopenError("NATIVE_EXACT_HEADER_CONTRACT_MISMATCH:API_DAILY")
                yield row
        yield rows(),"JSON_SYNTAX_PASS"
    else:
        raise PreopenError("UNSUPPORTED_NATIVE_ORIGINAL_CONTAINER")


def cash_clock(session):
    day(session)
    return {"am_open":"09:00", "am_close":"11:30", "pm_open":"12:30",
            "continuous_close":"15:00" if session < "2024-11-05" else "15:25",
            "auction_close":"15:00" if session < "2024-11-05" else "15:30"}


def minute_row(row, available_at):
    session, clock = row["Date"], row["Time"]
    day(session)
    if not re.fullmatch(r"\d{2}:\d{2}", clock):
        raise PreopenError("NATIVE_MINUTE_CLOCK_SCHEMA")
    times = cash_clock(session)
    start = stamp(session + "T" + clock + ":00+09:00")
    if clock in (times["am_close"], times["auction_close"]):
        # Time denotes a one-minute bucket start even at the terminal auction.
        # Its exact first-trade time is not supplied; conservative closure +1m.
        kind, end = "TERMINAL_AUCTION_REFERENCE", start + timedelta(minutes=1)
    elif "09:00" <= clock < "11:30" or "12:30" <= clock < times["continuous_close"]:
        kind, end = "CONTINUOUS_1M", start + timedelta(minutes=1)
    else:
        raise PreopenError("NATIVE_MINUTE_OUTSIDE_DATE_SPECIFIC_CASH_SESSION")
    out = parse_ohlcv(row)
    if out["status"] != "TRADED":
        raise PreopenError("NULL_NATIVE_EXECUTION_MINUTE")
    out.update({"session":session, "symbol":row["Code"], "kind":kind,
                "start":start.isoformat(),"end":end.isoformat(),
                "availableAt":available_at})
    if stamp(available_at) < end:
        raise PreopenError("NATIVE_MINUTE_AVAILABLE_BEFORE_COMPLETE")
    return out


def parse_ohlcv(row):
    """All official Null fields => UNKNOWN; partial Null/invalid values => error."""
    source = ("O", "H", "L", "C", "Vo", "Va")
    empty = [row.get(k) in NULLS for k in source]
    if all(empty):
        return {"status":"NO_TRADE_OR_HALT_UNDISTINGUISHED"}
    if any(empty):
        raise PreopenError("PARTIAL_NULL_NATIVE_OHLCV")
    o, h, l, c, v, t = [rational(row[k]) for k in source]
    if min(o,h,l,c) <= 0 or not l <= min(o,c) <= max(o,c) <= h or min(v,t) < 0:
        raise PreopenError("INVALID_NATIVE_OHLCV")
    if row.get("AdjFactor") not in NULLS and rational(row["AdjFactor"]) <= 0:
        raise PreopenError("INVALID_NATIVE_ADJUSTMENT_FACTOR")
    return {"status":"TRADED", **{
        target:str(row[src]) for src,target in zip(source,
             ("open","high","low","close","volume","turnover"))}}


def raw_label(row, *, source_hash):
    out = parse_ohlcv(row)
    label = {"labelId":LABEL,"session":row["Date"],"symbol":symbol(row["Code"]),
             "market":"T","priceBasis":"RAW_JPX_CASH","sourceSha256":source_hash,
             "officialFirstTradeOpen":True,"completeSession":True,
             "openingAt":None,"openingTimeEvidence":"NOT_SUPPLIED_NO_ASSUMED_09_00"}
    if out["status"] != "TRADED":
        label.update({"traded":False,"open":None,"high":None,"low":None,"close":None})
    else:
        label.update({"traded":True,**{k:out[k] for k in ("open","high","low","close")}})
    return label


def validate_native_request(request, private_root):
    if request.get("contract") != CONTRACT:
        raise PreopenError("WRONG_NATIVE_BUILD_CONTRACT")
    mode = request.get("mode")
    if mode not in ("SYNTHETIC", "AUTHORIZED_DEVELOPMENT"):
        raise PreopenError("UNAUTHORIZED_NATIVE_BUILD_MODE")
    admission_path = verify_entry(request["admission"], private_root)
    admission = json.loads(admission_path.read_text())
    if digest(admission["exactSplits"]) != admission["splitHash"]:
        raise PreopenError("NATIVE_ADMISSION_SPLIT_HASH")
    if set(request.get("protectedSessions",[])) & set(
            d for dates in admission["exactSplits"].values() for d in dates):
        raise PreopenError("NATIVE_PROTECTED_SESSION_OVERLAP")
    if mode == "AUTHORIZED_DEVELOPMENT":
        evidence_path = verify_entry(request["currentReuseEvidence"], private_root)
        evidence = json.loads(evidence_path.read_text())
        validate_reuse_authorization(evidence, work_id=request.get("reuseWorkId"))
        if request.get("historicalSourceAssumptionsReviewed") is not True:
            raise PreopenError("NATIVE_AVAILABILITY_AND_REVISION_ASSUMPTIONS_UNREVIEWED")
        ledger_path = verify_entry(request["sessionLedger"],private_root)
        if request["sessionLedger"]["sha256"] != admission.get("ledgerSha256"):
            raise PreopenError("NATIVE_SESSION_LEDGER_NOT_BOUND_TO_RECONCILIATION")
        with ledger_path.open("rt",newline="") as stream:
            ledger = {r["session_date"]:r for r in csv.DictReader(stream)}
        for role, dates in admission["exactSplits"].items():
            for d in dates:
                row = ledger.get(d,{})
                if (row.get("current_allowed_use") != "DEVELOPMENT_RESEARCH"
                        or row.get("protected_by") or row.get("candidate_role") != role):
                    raise PreopenError("NATIVE_LEDGER_ROLE_OR_SEAL_MISMATCH")
    sources = request["sources"]
    if not sources or any(s.get("dataset") not in DATASETS for s in sources):
        raise PreopenError("NATIVE_DATASET_SCHEMA")
    for source in sources:
        if mode == "SYNTHETIC" and source.get("dataNature") != "ARTIFICIAL_TEST_FIXTURE":
            raise PreopenError("REAL_NATIVE_ORIGINAL_IN_SYNTHETIC_MODE")
        if (not source.get("repository") or not source.get("objectKey")
                or not source.get("sourceCommit") or not source.get("sourceContractHash")):
            raise PreopenError("NATIVE_SOURCE_IDENTITY_INCOMPLETE")
        if mode == "AUTHORIZED_DEVELOPMENT":
            if source["repository"] not in REPOSITORIES:
                raise PreopenError("NATIVE_SOURCE_REPOSITORY_OUTSIDE_AUTHORIZATION")
            receipt_path = verify_entry(source["storageReceipt"],private_root)
            receipt = json.loads(receipt_path.read_text())
            matched = [r for r in receipt["objects"] if r["object_key"] == source["objectKey"]
                       and r["repository"] == source["repository"]]
            if (len(matched) != 1 or matched[0]["sha256"] != source["sha256"]
                    or matched[0]["bytes"] != source["bytes"]
                    or matched[0].get("unmodified") is not True
                    or matched[0].get("complete") is not True):
                raise PreopenError("NATIVE_ORIGINAL_NOT_BOUND_TO_VERIFIED_STORAGE_RECEIPT")
        if source.get("priceBasis", "RAW_JPX_CASH") != "RAW_JPX_CASH":
            raise PreopenError("NATIVE_RAW_ADJUSTED_MIXTURE")
        private_path(source["path"], private_root)
    return admission


class NativeStore:
    """One full original pass; numeric admission occurs only after date filtering."""
    def __init__(self, directory, *, private_root, request):
        self.root = private_path(directory, private_root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.private_root = Path(private_root).resolve()
        self.request = request
        self.sources_by_hash = {s["sha256"]:s for s in request["sources"]}
        if len(self.sources_by_hash) != len(request["sources"]):
            raise PreopenError("DUPLICATE_NATIVE_ORIGINAL_DESCRIPTOR")
        self.admission = validate_native_request(request, private_root)
        self.connection = sqlite3.connect(self.root/"sources.sqlite")
        self.connection.execute("PRAGMA cache_size=-32768")
        self.connection.execute("PRAGMA temp_store=FILE")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS records(
            dataset TEXT,session TEXT,symbol TEXT,clock TEXT,source_hash TEXT,
            ordinal INTEGER,payload TEXT,PRIMARY KEY(dataset,source_hash,ordinal))""")
        self.connection.execute("""CREATE INDEX IF NOT EXISTS lookup
            ON records(dataset,symbol,session,clock)""")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS completed(
            source_hash TEXT PRIMARY KEY,descriptor_hash TEXT,receipt TEXT)""")
        self.connection.commit()
        self.shared_daily = None
        shared = request.get("existingDailySourceCache")
        if shared is not None:
            cache_path = verify_entry(shared, self.private_root)
            self.shared_daily = sqlite3.connect(cache_path.as_uri()+"?mode=ro",uri=True)
            if self.shared_daily.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise PreopenError("SHARED_DAILY_CACHE_INTEGRITY")
            self.shared_daily_hashes = {s["sha256"] for s in request["sources"]
                                        if s["dataset"] == "DAILY" and s.get("reuseExistingDailyCache") is True}

    def close(self):
        self.connection.close()
        if self.shared_daily is not None:
            self.shared_daily.close()

    def ingest(self, source):
        if source.get("reuseExistingDailyCache") is True:
            if self.shared_daily is None or source["sha256"] not in self.shared_daily_hashes:
                raise PreopenError("SHARED_DAILY_SOURCE_NOT_BOUND")
            done = self.shared_daily.execute("SELECT receipt FROM completed WHERE source_hash=?",
                                            (source["sha256"],)).fetchone()
            if done is None:
                raise PreopenError("SHARED_DAILY_SOURCE_NOT_COMPLETED")
            receipt = json.loads(done[0])
            if receipt.get("sourceBytes") != source["bytes"]:
                raise PreopenError("SHARED_DAILY_SOURCE_SIZE_MISMATCH")
            return {**receipt,"existingVerifiedDailyCacheReused":True,"newIngestRows":0}
        path = verify_entry(source, self.private_root)
        descriptor_hash = digest(source)
        done = self.connection.execute("SELECT descriptor_hash,receipt FROM completed WHERE source_hash=?",
                                      (source["sha256"],)).fetchone()
        if done:
            if done[0] != descriptor_hash:
                raise PreopenError("COMPLETED_NATIVE_SOURCE_DESCRIPTOR_CHANGED")
            return json.loads(done[1])
        ds = source["dataset"]
        allowed = set(source["allowedRecordDates"])
        if ds in ("DAILY","MINUTE","TICK","TOPIX"):
            # Last Report day's outcome prices are not needed by any snapshot.
            # Earlier Report prices can be D-1 history for a later snapshot and
            # that limited exposure is explicitly recorded, never called unseen.
            latest_target = max(self.admission["exactSplits"]["report"])
            allowed = {d for d in allowed if d < latest_target}
        date_field = source.get("dateField", "Date")
        required = set(source["requiredHeader"])
        counts = Counter()
        duplicate_keys = set() if ds in ("TOPIX",) else None
        with self.connection:
            with open_original_records(path,source) as (reader,container_integrity):
                for ordinal, row in enumerate(reader,2):
                    counts["lexicallyTraversedRows"] += 1
                    session = row[date_field]
                    day(session)
                    if session not in allowed:
                        counts["nonAdmittedLexicallyTraversedRows"] += 1
                        continue
                    code = row.get("Code","__MARKET__")
                    clock = row.get("Time",row.get("DiscTime",""))
                    if ds in ("DAILY","MINUTE"):
                        parse_ohlcv(row)
                        counts["numericPriceRowsParsed"] += 1
                    elif ds == "TOPIX":
                        vals = [rational(row[k]) for k in ("O","H","L","C")]
                        if min(vals) <= 0 or not vals[2] <= min(vals[0],vals[3]) <= max(vals[0],vals[3]) <= vals[1]:
                            raise PreopenError("INVALID_NATIVE_TOPIX")
                        counts["numericPriceRowsParsed"] += 1
                    elif ds == "TICK":
                        mapping = source.get("tickFieldMap")
                        if not mapping or not all(k in mapping for k in ("date","time","symbol","price","quantity")):
                            raise PreopenError("ACTUAL_TICK_HEADER_MAPPING_REQUIRED_NO_GUESS")
                        if any(name not in row for name in mapping.values()):
                            raise PreopenError("TICK_MAPPING_HEADER_MISMATCH")
                        code, clock = row[mapping["symbol"]], row[mapping["time"]]
                        if rational(row[mapping["price"]]) <= 0 or rational(row[mapping["quantity"]]) <= 0:
                            raise PreopenError("INVALID_NATIVE_TICK_PRICE_OR_QUANTITY")
                        stamp(session+"T"+clock+"+09:00")
                        counts["numericPriceRowsParsed"] += 1
                    if re.fullmatch(r"[0-9A-Z]{4}",code):
                        row["_sourceCode"] = code
                        code = symbol(code)
                        row["Code"] = code
                    if ds in ("DAILY","DATED_MASTER","MINUTE","TOPIX"):
                        existing = self.connection.execute(
                            "SELECT 1 FROM records WHERE dataset=? AND session=? AND symbol=? AND clock=? LIMIT 1",
                            (ds,session,code,clock)).fetchone()
                        if existing:
                            raise PreopenError("DUPLICATE_NATIVE_BAR_OR_MASTER_IDENTITY")
                        if ds == "DAILY" and self.shared_daily is not None:
                            shared = self.shared_daily.execute("SELECT source_hash FROM records "
                                "WHERE dataset='DAILY' AND session=? AND symbol=? LIMIT 1",(session,code)).fetchone()
                            if shared and shared[0] in self.shared_daily_hashes:
                                raise PreopenError("DUPLICATE_NATIVE_DAILY_WITH_SHARED_CACHE")
                    # Tick ordinal preserves distinct same-time/same-value prints.
                    self.connection.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?)",
                        (ds,session,code,clock,source["sha256"],ordinal,
                         json.dumps(row,sort_keys=True,ensure_ascii=False)))
                    counts["admittedRows"] += 1
                    if counts["admittedRows"] % 10000 == 0:
                        actual_bytes = (self.root/"sources.sqlite").stat().st_size
                        actual_bytes += sum(p.stat().st_size for p in self.root.glob("sources.sqlite-*"))
                        if actual_bytes > self.request.get("maxShardBytes", 8*1024**3):
                            raise PreopenError("NATIVE_PRIVATE_SHARD_DISK_BUDGET_EXCEEDED")
            receipt = {"schema":"ARK_PREOPEN_NATIVE_OBJECT_ACCESS_V1",
                       "sourceDescriptorHash":descriptor_hash,"dataset":ds,
                       "sourceSha256":source["sha256"],"sourceBytes":source["bytes"],
                       "counts":dict(counts),"allowedDatesHash":digest(sorted(allowed)),
                       "gzipCRC":"PASS" if container_integrity == "GZIP_CRC_PASS" else "NOT_APPLICABLE_JSON",
                       "originalContainerIntegrity":container_integrity,
                       "historicalReceiveTimeCertified":False,
                       "nonAdmittedRowsWereLexicallyTraversed":True,
                       "nonAdmittedNumericPricesParsed":0}
            self.connection.execute("INSERT INTO completed VALUES(?,?,?)",
                (source["sha256"],descriptor_hash,json.dumps(receipt)))
        return receipt

    def records(self, dataset, *, code=None, before=None, session=None):
        query = "SELECT payload,source_hash,ordinal FROM records WHERE dataset=?"
        args = [dataset]
        for clause, value in (("symbol=?",code),("session<?",before),("session=?",session)):
            if value is not None:
                query += " AND " + clause
                args.append(value)
        query += " ORDER BY session,symbol,clock,source_hash,ordinal"
        def admitted(cursor, shared=False):
            for payload, source_hash, ordinal in cursor:
                if shared and source_hash not in self.shared_daily_hashes:
                    continue
                row = json.loads(payload)
                if shared and row["Date"] not in self.source(source_hash)["allowedRecordDates"]:
                    continue
                yield {**row,"_sourceHash":source_hash,"_ordinal":ordinal}
        if dataset == "DAILY" and self.shared_daily is not None:
            import heapq
            yield from heapq.merge(admitted(self.connection.execute(query,args)),
                admitted(self.shared_daily.execute(query,args),True),
                key=lambda r:(r["Date"],r["Code"],r.get("Time",""),r["_sourceHash"],r["_ordinal"]))
        else:
            yield from admitted(self.connection.execute(query,args))

    def source(self, sha):
        return self.sources_by_hash[sha]

    def available_at(self, row, dataset):
        source = self.source(row["_sourceHash"])
        from preopen_source_contracts import native_available_at
        return native_available_at(row, source, calendar=self.request.get("exchangeSessions"))

    def prior_tick_events(self, previous_session, code, cutoff):
        events = []
        for row in self.records("TICK",code=code,session=previous_session):
            source = self.source(row["_sourceHash"])
            mapping = source["tickFieldMap"]
            trade_at = previous_session+"T"+row[mapping["time"]]+"+09:00"
            occurred = stamp(trade_at)
            times = cash_clock(previous_session)
            clock = occurred.strftime("%H:%M:%S")
            if not ("09:00:00" <= clock <= "11:30:00" or
                    "12:30:00" <= clock <= times["continuous_close"]+":00" or
                    clock == times["auction_close"]+":00"):
                raise PreopenError("TICK_OUTSIDE_PREVIOUS_CASH_SESSION")
            known = self.available_at(row,"TICK")
            if stamp(known) > stamp(cutoff):
                raise PreopenError("PRIOR_TICK_NOT_AVAILABLE_BY_CUTOFF")
            events.append({"tradeAt":trade_at,"availableAt":known,
                           "price":row[mapping["price"]],"quantity":row[mapping["quantity"]],
                           "sourceHash":row["_sourceHash"],"sourceOrdinal":row["_ordinal"]})
        return events

    def labels(self, sessions):
        for session in sessions:
            for row in self.records("DAILY",session=session):
                # Securities outside the ordinary stock code contract cannot
                # occur in selected keys. Do not collapse preferred suffixes.
                if re.fullmatch(r"[0-9A-Z]{4}0",row["Code"]):
                    yield raw_label(row,source_hash=row["_sourceHash"])


def read_native_report_labels(entry, private_root):
    """Called only by the outcome stage, after all watchlist hashes are fixed."""
    manifest = json.loads(verify_entry(entry,private_root).read_text())
    if manifest.get("schema") != "ARK_PREOPEN_NATIVE_LABEL_MANIFEST_V1":
        raise PreopenError("NATIVE_REPORT_LABEL_MANIFEST")
    allowed = set(manifest["sessions"])
    protected = set(manifest["protectedSessions"])
    if allowed & protected:
        raise PreopenError("NATIVE_REPORT_PROTECTED_OVERLAP")
    for source in manifest["sources"]:
        path = verify_entry(source,private_root)
        with open_original_records(path,source) as (reader,_):
            for row in reader:
                if row["Date"] in allowed and re.fullmatch(r"[0-9A-Z]{4}0",row["Code"]):
                    yield raw_label(row,source_hash=source["sha256"])
