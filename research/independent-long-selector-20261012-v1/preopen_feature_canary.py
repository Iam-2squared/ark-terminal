"""Read-only, label-free source-feature resource canary; never a candidate fit.

All source symbols for the admitted D-1 are traversed. A dated eligible master
is deliberately not invented. Outputs cannot enter the full native/model CLI.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import resource
import sqlite3
import time
from collections import Counter
from pathlib import Path

import numpy as np

from preopen_io import private_path, verify_entry, write_json, sha_file, SAFE_FLAGS
from preopen_selector import CONTRACT, PreopenError, digest, day, _bar, _resample_complete_history
from preopen_native_source import parse_ohlcv, NULLS
from preopen_reuse_authorization import validate_reuse_authorization
from preopen_session_admission import exchange_sessions
from preopen_feature_policy import (DAILY_MA, policy_hash, source_code_hash,
    cache_binding, technical_contracts, technical_missing_reasons)
from technical_feature_library import build_ohlcv_features, feature_registry


def run_canary(request, output):
    if (request.get("contract") != CONTRACT or request.get("intendedUse") != "SOURCE_FEATURE_CANARY_ONLY"
            or any(k in request for k in ("labels", "outcomes", "report_labels"))):
        raise PreopenError("INVALID_SOURCE_FEATURE_CANARY_SCOPE")
    root = Path(request["privateRoot"]).resolve()
    output = private_path(output, root)
    if output.exists():
        raise PreopenError("REFUSE_OVERWRITE_FEATURE_CANARY")
    evidence = json.loads(verify_entry(request["currentReuseEvidence"], root).read_text())
    authority = validate_reuse_authorization(evidence, work_id=request["reuseWorkId"])
    admission = json.loads(verify_entry(request["admission"], root).read_text())
    if digest(admission["exactSplits"]) != admission["splitHash"]:
        raise PreopenError("CANARY_ADMISSION_SPLIT_HASH_MISMATCH")
    session = request["session"]
    if session not in admission["exactSplits"]["fit"]:
        raise PreopenError("FEATURE_CANARY_MUST_USE_ADMITTED_FIT_DAY")
    ledger_path = verify_entry(request["sessionLedger"], root)
    if request["sessionLedger"]["sha256"] != admission["ledgerSha256"]:
        raise PreopenError("CANARY_LEDGER_HASH_MISMATCH")
    with ledger_path.open(newline="") as stream:
        ledger = {r["session_date"]:r for r in csv.DictReader(stream)}
    if ledger[session]["protected_by"] or ledger[session]["candidate_role"] != "fit":
        raise PreopenError("CANARY_ROLE_OR_SEAL_MISMATCH")
    with gzip.open(verify_entry(request["calendar"], root), "rt", newline="") as stream:
        calendar = exchange_sessions(list(csv.DictReader(stream)))
    ix = calendar.index(session)
    previous = calendar[ix-1]
    history_dates = request["historyDates"]
    if (not history_dates or history_dates != sorted(set(history_dates))
            or history_dates[-1] != previous):
        raise PreopenError("CANARY_HISTORY_NOT_CAUSAL_D_MINUS_1")
    for d in history_dates:
        row = ledger.get(d, {})
        if (d >= session or d not in calendar or row.get("protected_by")
                or row.get("current_allowed_use") != "DEVELOPMENT_RESEARCH"):
            raise PreopenError("CANARY_HISTORY_OUTSIDE_ADMITTED_DEVELOPMENT")
    db = verify_entry(request["sourceShard"], root)
    columns = tuple(sorted(name for scope in ("daily", "week", "month")
                           for name in feature_registry("preopen_"+scope, DAILY_MA if scope == "daily" else ())))
    binding = cache_binding(code_hash=source_code_hash(), input_hash=digest(request),
        calendar_hash=request["calendar"]["sha256"],
        basis_hash=digest({"rule":"RAW_CONTIGUOUS_SUFFIX_RESET_ON_NULL_GAP_OR_KNOWN_ACTION"}),
        schema_hash=digest(columns))
    output.mkdir(parents=True, mode=0o700)
    start = time.perf_counter()
    excluded, reasons, observed, source_hashes = Counter(), Counter(), Counter(), set()
    count = 0
    c = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
    c.execute("PRAGMA query_only=ON")
    allowed = set(history_dates)
    calendar_ix = {d:i for i,d in enumerate(calendar)}
    source_n = c.execute("SELECT count(DISTINCT symbol) FROM records WHERE dataset='DAILY' AND session=?",
                         (previous,)).fetchone()[0]
    seen = c.execute("SELECT DISTINCT symbol FROM records WHERE dataset='DAILY' AND session=? ORDER BY symbol",
                     (previous,))
    with (output/"features.f64").open("xb") as binary, (output/"rows.jsonl").open("x") as rows:
        for (symbol,) in seen:
            records = c.execute("SELECT session,source_hash,payload FROM records WHERE dataset='DAILY'"
                                " AND symbol=? AND session<=? ORDER BY session", (symbol, previous))
            bars = []
            hashes = set()
            last = None
            for date, sha, payload in records:
                # No unadmitted numeric interpretation, even if an older shard
                # contains additional records. This is not an outcome reader.
                if date not in allowed:
                    continue
                raw = json.loads(payload)
                if raw["Date"] != date or raw["Code"] != symbol:
                    raise PreopenError("CANARY_SOURCE_IDENTITY_MISMATCH")
                parsed = parse_ohlcv(raw)
                if parsed["status"] != "TRADED":
                    bars = []; last = date
                    continue
                if last and calendar_ix[date] != calendar_ix[last]+1:
                    bars = []
                if raw.get("AdjFactor") not in NULLS and float(raw["AdjFactor"]) != 1:
                    bars = []
                bars.append(_bar({**parsed, "session":date}))
                hashes.add(sha); last = date
            if not bars or bars[-1]["session"] != previous:
                excluded["PRIOR_NO_TRADE_OR_NO_COMPARABLE_SUFFIX"] += 1
                continue
            values, missing = {}, {}
            for scope in ("daily", "week", "month"):
                prefix = "preopen_"+scope
                series = bars if scope == "daily" else _resample_complete_history(bars, scope)
                periods = DAILY_MA if scope == "daily" else ()
                f = build_ohlcv_features(series, prefix=prefix,
                    reference_price=bars[-1]["close"], periods=periods)
                values.update(f)
                missing.update(technical_missing_reasons(f, series, prefix=prefix, periods=periods))
            vector = np.asarray([np.nan if values[k] is None else values[k] for k in columns], dtype="<f8")
            binary.write(vector.tobytes())
            observed.update(k for k in columns if values[k] is not None)
            reasons.update(missing.values()); source_hashes.update(hashes)
            rows.write(json.dumps({"symbol":symbol, "session":session, "previousSession":previous,
                "historyN":len(bars), "sourceHashes":sorted(hashes), "featureHash":digest(values),
                "missingReasons":missing, "ordinaryStockEligibilityVerified":False,
                **SAFE_FLAGS}, sort_keys=True)+"\n")
            count += 1
    c.close()
    matrix_hash, matrix_bytes = sha_file(output/"features.f64")
    row_hash, row_bytes = sha_file(output/"rows.jsonl")
    receipt = {"schema":"ARK_PREOPEN_SOURCE_FEATURE_CANARY_V1", "intendedUse":"SOURCE_FEATURE_CANARY_ONLY",
        "candidateFeatureRowN":0, "sourceFeatureRowN":count, "sourceSymbolN":source_n,
        "computedSchemaColumns":len(columns), "observedColumnN":sum(observed[k] > 0 for k in columns),
        "columns":columns, "observedCounts":{k:observed[k] for k in columns},
        "missingReasonCounts":dict(reasons), "preOutcomeExclusions":dict(excluded),
        "matrix":{"path":str(output/"features.f64"),"sha256":matrix_hash,"bytes":matrix_bytes},
        "rows":{"path":str(output/"rows.jsonl"),"sha256":row_hash,"bytes":row_bytes},
        "cacheBinding":binding, "sourceOriginalN":len(source_hashes),
        "wallSeconds":time.perf_counter()-start, "peakRssKiB":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "diskOutputBytes":matrix_bytes+row_bytes, "schemaPolicyHash":policy_hash(),
        "authority":authority, "ordinaryStockEligibilityVerified":False,
        "fullCandidateFamilyConnection":False, "fullNativeScaleCertified":False,
        "fitLabelsRead":False, "reportLabelsRead":False, "marketFits":0, "calibrationFits":0,
        "marketWatchlists":0, "allDMinus1SourceSymbolsVisited":count+sum(excluded.values()) == source_n,
        **SAFE_FLAGS}
    if not receipt["allDMinus1SourceSymbolsVisited"]:
        raise PreopenError("CANARY_SOURCE_UNIVERSE_CARDINALITY_MISMATCH")
    write_json(output/"FEATURE_CANARY_RECEIPT_PRIVATE.json", receipt)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--request", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = run_canary(json.loads(Path(a.request).read_text()), a.output)
    print(json.dumps({k:result[k] for k in ("sourceFeatureRowN", "sourceSymbolN", "computedSchemaColumns",
        "observedColumnN", "wallSeconds", "peakRssKiB", "fullCandidateFamilyConnection", "marketFits")}))


if __name__ == "__main__":
    main()
