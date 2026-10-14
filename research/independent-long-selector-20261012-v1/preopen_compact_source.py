"""Bounded native intraday admission; originals are never rewritten.

Minutes are losslessly compressed per security/day. Tick rows are validated
throughout the day, while only the last 120 minutes needed by the fixed Tick
formulas are retained transiently. Saved output is a derived feature aggregate,
not a substitute original or a historical delivery/version certificate.
"""
from __future__ import annotations

import json
import re
import zlib
from collections import Counter
from datetime import timedelta
from decimal import Decimal

from preopen_io import verify_entry
from preopen_native_source import NativeStore, open_original_records, cash_clock, parse_ohlcv
from preopen_selector import PreopenError, digest, stamp, symbol
from preopen_history_features import prior_tick_features
from preopen_feature_policy import policy_hash, preopen_schema
from pathlib import Path
import hashlib

COMPACT_VERSION = "ARK_PREOPEN_INTRADAY_COMPACT_V1"


def compact_binding(source,request):
    files=("preopen_compact_source.py","preopen_native_source.py","preopen_history_features.py",
           "tick_feature_library.py","preopen_source_contracts.py","preopen_selector.py")
    root=Path(__file__).resolve().parent
    return {"version":COMPACT_VERSION,"codeHash":digest({n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in files}),
            "featurePolicyHash":policy_hash(),"schemaHash":digest(preopen_schema()),
            "sourceDescriptorHash":digest(source),"admissionHash":request["admission"]["sha256"],
            "calendarHash":request.get("calendar",{}).get("sha256",digest(request.get("exchangeSessions",[]))),
            "dailyReferenceInputHash":digest([(s["sha256"],s["allowedRecordDates"],s["sourceContractHash"])
                                              for s in request["sources"] if s["dataset"]=="DAILY"])}


def tick_units(name):
    if "trade_count" in name:
        return "AGGREGATED_PRICE_TIME_RECORDS_NOT_INDIVIDUAL_EXECUTIONS"
    if "volume" in name and "ratio" not in name or "trade_size" in name:
        return "SHARES"
    if "value" in name and "ratio" not in name:
        return "JPY"
    if name.endswith("seconds"):
        return "SECONDS"
    if "pct" in name or "volatility" in name:
        return "PERCENT"
    if "zscore" in name:
        return "ZSCORE"
    return "RATIO"


def tick_features_for_group(rows, *, previous_session, cutoff, reference_price):
    closing = stamp(previous_session+"T"+cash_clock(previous_session)["auction_close"]+":00+09:00")
    horizon = closing+timedelta(microseconds=1)-timedelta(minutes=120)
    events, last, previous_time, previous_id = [], None, None, None
    volume, value, high, low, opening, close = Decimal(0), Decimal(0), None, None, None, None
    n = 0
    for r in rows:
        clock = r["Time"]
        occurred = stamp(previous_session+"T"+clock+"+09:00")
        tm = occurred.strftime("%H:%M:%S")
        hours = cash_clock(previous_session)
        valid = ("09:00:00" <= tm <= "11:30:00" or
                 "12:30:00" <= tm <= hours["continuous_close"]+":00" or
                 occurred == closing)
        if not valid or r["Date"] != previous_session:
            raise PreopenError("COMPACT_TICK_OUTSIDE_DATED_SESSION")
        if previous_time is not None and occurred < previous_time:
            raise PreopenError("COMPACT_TICK_NOT_CHRONOLOGICAL")
        transaction = r.get("TransactionId")
        if not transaction or not re.fullmatch(r"[0-9]+", transaction):
            raise PreopenError("COMPACT_TICK_TRANSACTION_ID_UNVERIFIED")
        tid = int(transaction)
        if previous_id is not None and tid <= previous_id:
            raise PreopenError("COMPACT_DUPLICATE_OR_REORDERED_TICK_TRANSACTION")
        p, q = Decimal(r["Price"]), Decimal(r["TradingVolume"])
        if not p.is_finite() or not q.is_finite() or min(p,q) <= 0:
            raise PreopenError("INVALID_COMPACT_TICK_PRICE_OR_QUANTITY")
        if q != q.to_integral_value():
            raise PreopenError("COMPACT_TICK_NONINTEGRAL_SHARES")
        if n == 0:
            opening = p
        high, low = (p if high is None else max(high,p)), (p if low is None else min(low,p))
        close, volume, value = p, volume+q, value+p*q
        event = {"tradeAt":occurred.isoformat(),"availableAt":cutoff,
                 "price":r["Price"],"quantity":r["TradingVolume"]}
        if occurred > horizon:
            events.append(event)
        last, previous_time, previous_id = event, occurred, tid
        n += 1
    if last is not None and not events:
        events = [last]  # preserve age/no-recent-trade semantics, not zero fill
    features = prior_tick_features(events, previous_session=previous_session, cutoff=cutoff,
        reference_price=reference_price, complete_source_verified=True)
    totals = {"rows":n,"volume":str(volume),"turnover":str(value),
              **{k:None if v is None else str(v) for k,v in
                 (("open",opening),("high",high),("low",low),("close",close))}}
    return features, totals, len(events)


def reconciled_totals(totals, daily):
    parsed = parse_ohlcv(daily)
    if parsed["status"] != "TRADED":
        return totals["rows"] == 0
    return all(Decimal(totals[k]) == Decimal(parsed[k])
               for k in ("open","high","low","close","volume","turnover"))


class CompactNativeStore(NativeStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection.execute("""CREATE TABLE IF NOT EXISTS compact_intraday(
            dataset TEXT,session TEXT,symbol TEXT,source_hash TEXT,payload BLOB,
            PRIMARY KEY(dataset,session,symbol))""")
        self.connection.commit()

    def _group_body(self, ds, rows, source, session, code):
        # Bulk files need not order simultaneous records by TransactionId.
        # Canonicalize the derived group, retain every distinct source ordinal.
        # Transaction identity conflicts still fail; equal time/value is not dedup.
        rows = sorted(rows,key=(lambda r:(r["Time"],int(r["TransactionId"])))
                      if ds == "TICK" else (lambda r:r["Time"]))
        ids = [r["TransactionId"] for r in rows] if ds == "TICK" else [r["Time"] for r in rows]
        if len(ids) != len(set(ids)):
            raise PreopenError("COMPACT_DUPLICATE_INTRADAY_IDENTITY")
        daily = list(self.records("DAILY",code=code,session=session))
        if len(daily) != 1:
            raise PreopenError("COMPACT_REQUIRES_ONE_ADMITTED_RAW_DAILY_REFERENCE")
        known = self.available_at({**rows[0],"_sourceHash":source["sha256"]}, ds)
        if ds == "TICK":
            f, totals, retained = tick_features_for_group(rows, previous_session=session,
                cutoff=known, reference_price=daily[0]["C"])
            return {"features":f,"totals":totals,"retainedCalculationRows":retained,
                    "completeAgainstSavedDaily":reconciled_totals(totals,daily[0]),
                    "actualHistoricalReceiveVerified":False,"availableAt":known}
        # Original minute strings/ordinals are retained without float conversion.
        total_volume = sum((Decimal(r["Vo"]) for r in rows),Decimal(0))
        total_value = sum((Decimal(r["Va"]) for r in rows),Decimal(0))
        for r in rows:
            parse_ohlcv(r)
        totals = {"rows":len(rows),"volume":str(total_volume),"turnover":str(total_value),
                  "open":rows[0]["O"],"close":rows[-1]["C"],
                  "high":str(max(Decimal(r["H"]) for r in rows)),
                  "low":str(min(Decimal(r["L"]) for r in rows))}
        return {"rows":rows,"totals":totals,
                "completeAgainstSavedDaily":reconciled_totals(totals,daily[0]),
                "actualHistoricalReceiveVerified":False,"availableAt":known}

    def ingest(self, source):
        ds = source["dataset"]
        if ds not in ("MINUTE","TICK"):
            return super().ingest(source)
        path = verify_entry(source,self.private_root)
        binding = compact_binding(source,self.request)
        descriptor_hash = digest(binding)
        done = self.connection.execute("SELECT descriptor_hash,receipt FROM completed WHERE source_hash=?",
                                      (source["sha256"],)).fetchone()
        if done:
            if done[0] != descriptor_hash:
                raise PreopenError("COMPLETED_COMPACT_SOURCE_DESCRIPTOR_CHANGED")
            return json.loads(done[1])
        allowed = set(source["allowedRecordDates"])
        latest = max(self.admission["exactSplits"]["report"])
        allowed = {d for d in allowed if d < latest}
        if allowed & set(self.request.get("protectedSessions", [])):
            raise PreopenError("COMPACT_PROTECTED_SOURCE_DATE")
        counts, key, group, last_order = Counter(), None, [], None
        def flush():
            if not group:
                return
            body = self._group_body(ds, group, source, key[0], key[1])
            counts["derivedSecurityDays"] += 1
            counts["completeAgainstSavedDailySecurityDays"] += int(body["completeAgainstSavedDaily"])
            counts["inconsistentAgainstSavedDailySecurityDays"] += int(not body["completeAgainstSavedDaily"])
            packed = zlib.compress(json.dumps(body,sort_keys=True,separators=(",",":")).encode(),3)
            self.connection.execute("INSERT INTO compact_intraday VALUES(?,?,?,?,?)",
                (ds,key[0],key[1],source["sha256"],packed))
            counts["compressedDerivedBytes"] += len(packed)
            if counts["derivedSecurityDays"] % 5000 == 0:
                print(json.dumps({"dataset":ds,"completedSecurityDays":counts["derivedSecurityDays"],
                                  "admittedRecords":counts["admittedRows"]}),flush=True)
        with self.connection:
            with open_original_records(path,source) as (reader, integrity):
                for ordinal, row in enumerate(reader,2):
                    counts["lexicallyTraversedRows"] += 1
                    if row["Date"] not in allowed:
                        counts["nonAdmittedLexicallyTraversedRows"] += 1
                        continue
                    raw_code = row["Code"]
                    if re.fullmatch(r"[0-9A-Z]{4}",raw_code):
                        code = raw_code+"0"
                    elif re.fullmatch(r"[0-9A-Z]{5}",raw_code):
                        code = raw_code
                    else:
                        raise PreopenError("COMPACT_NATIVE_SECURITY_CODE_SCHEMA")
                    current = (row["Date"],code)
                    if current != key:
                        flush()
                        key, group, last_order = current, [], None
                    clock = row["Time"]
                    row["Code"], row["_ordinal"] = current[1], ordinal
                    group.append(row)
                    counts["admittedRows"] += 1
                    # Bound the biggest single security/day; never sample winners.
                    if len(group) > self.request.get("maxIntradayGroupRows",1000000):
                        raise PreopenError("COMPACT_SECURITY_DAY_MEMORY_BUDGET")
                flush()
            receipt = {"schema":COMPACT_VERSION,"dataset":ds,"sourceSha256":source["sha256"],
                       "sourceBytes":source["bytes"],"sourceDescriptorHash":descriptor_hash,
                       "counts":dict(counts),"allowedDatesHash":digest(sorted(allowed)),
                       "originalContainerIntegrity":integrity,"nonAdmittedNumericPricesParsed":0,
                       "historicalReceiveTimeCertified":False,"immutableOriginalModified":False,
                       "cacheBinding":binding}
            self.connection.execute("INSERT INTO completed VALUES(?,?,?)",
                (source["sha256"],descriptor_hash,json.dumps(receipt)))
        return receipt

    def _compact(self,dataset,session,code):
        row = self.connection.execute("SELECT payload,source_hash FROM compact_intraday "
            "WHERE dataset=? AND session=? AND symbol=?",(dataset,session,code)).fetchone()
        if row is None:
            return None, None
        return json.loads(zlib.decompress(row[0])), row[1]

    def records(self,dataset,*,code=None,before=None,session=None):
        if dataset != "MINUTE":
            yield from super().records(dataset,code=code,before=before,session=session)
            return
        if code is None or session is None or before is not None:
            raise PreopenError("COMPACT_MINUTE_REQUIRES_EXACT_SECURITY_DAY")
        body, sha = self._compact(dataset,session,code)
        if body:
            for row in body["rows"]:
                yield {**row,"_sourceHash":sha}

    def prior_tick_events(self,previous_session,code,cutoff):
        return None  # aggregate facts below use the identical fixed formulas

    def prior_tick_feature_facts(self,previous_session,code,cutoff):
        body, sha = self._compact("TICK",previous_session,code)
        if body is None or not body["completeAgainstSavedDaily"]:
            return {},False
        if stamp(body["availableAt"]) > stamp(cutoff):
            raise PreopenError("COMPACT_TICK_NOT_AVAILABLE_AT_CUTOFF")
        evidence = self.source(sha)["availabilityContract"]["evidenceReference"]
        return {k:{"value":v,"units":tick_units(k),
                    "sourceSha256":sha,"publicationEvidence":evidence,
                    "availableAt":body["availableAt"]}
                for k,v in body["features"].items() if v is not None},True

    def minute_complete(self,previous_session,code):
        body,_ = self._compact("MINUTE",previous_session,code)
        return bool(body and body["completeAgainstSavedDaily"])
