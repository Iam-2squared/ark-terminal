#!/usr/bin/env python3
"""Offline, immutable recovery of exactly unprocessed RSS symbols.

Only reads original symbols and a prior capture directory; verifies the last
20-symbol checkpoint and every SHA256. Reuses any *fully validated contiguous*
partial-wave source files. Creates a new private resume input and receipt.
No Excel, broker, network, training, model promotion, or orders.
"""
import argparse
from collections import Counter
import hashlib
import json
import re
import sys
from pathlib import Path
from uuid import uuid4

sys.dont_write_bytecode = True

MASTER_SHA256 = "22d31026c76dd1a555a2deed2d2b5743004687a239dcc8856b5abeae47782056"
SYMBOL_RE = re.compile(r"[0-9A-Z]{4}\.T\Z")
DATA_RE = re.compile(r"(\d{5})-([0-9A-Z]{4})_T-(1M|5M)\.json\Z")
PROGRESS_RE = re.compile(r"progress-(\d{5})\.json\Z")
GOOD = "OBSERVED_ARCHIVE_NOT_TRAINING_CERTIFIED"
EMPTY = "SOURCE_UNAVAILABLE"
REJECTED = "ROW_AUDIT_FAILED"
EXPECTED_CAPTURE = 4307
FIRST_SKIP = 20
MAX_BYTES = 3_000_000


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def safe_file(p, upper=MAX_BYTES):
    require(p.is_file() and not p.is_symlink(), "NO11_RESUME_FILE_MISSING_OR_SYMLINK:" + p.name)
    n = p.stat().st_size
    require(0 < n <= upper, "NO11_RESUME_FILE_SIZE_INVALID:" + p.name)
    return p.read_bytes()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def obj_from_bytes(b, where):
    try:
        v = json.loads(b.decode("utf-8-sig"), parse_constant=lambda x: require(False, "NONFINITE:" + x))
    except (UnicodeError, ValueError) as e:
        raise RuntimeError("NO11_RESUME_INVALID_JSON:" + where) from e
    require(isinstance(v, dict), "NO11_RESUME_NOT_OBJECT:" + where)
    return v


def check_false(v, keys, name):
    for k in keys:
        require(v.get(k) is False, "NO11_RESUME_UNSAFE_FLAG:" + name + ":" + k)


def check_source(v, symbol, index, period, file_name):
    require(v.get("schemaId") == "ARK_NO11_RSS_TRAINING_SYMBOL_ARCHIVE_V1", "NO11_RESUME_SOURCE_SCHEMA:" + file_name)
    require(v.get("symbol") == symbol and v.get("period") == period and
            v.get("sourceFunction") == "RssChart" and
            v.get("evidenceMode") == "OBSERVED_READ_ONLY" and
            v.get("requestedBars") == 3000, "NO11_RESUME_SOURCE_IDENTITY:" + file_name)
    status = v.get("status")
    require(status in (GOOD, EMPTY, REJECTED), "NO11_RESUME_SOURCE_UNKNOWN_STATUS:" + file_name)
    check_false(v, ("privateAccountDataIncluded", "vendorLabelCertified",
                    "actualHistoricalKnownAtCertified", "vendorDecimalTokenCertified",
                    "nativeSelectorProduced", "modelTrainingReady",
                    "productionReady", "orderTransmission"), file_name)
    rows = v.get("rows")
    require(isinstance(rows, list) and
            type(v.get("validRows")) is int and len(rows) == v["validRows"] and
            type(v.get("numericRows")) is int and v["numericRows"] >= v["validRows"] and
            type(v.get("invalidRows")) is int and v["invalidRows"] >= 0 and
            type(v.get("duplicateRows")) is int and v["duplicateRows"] >= 0,
            "NO11_RESUME_SOURCE_COUNTS:" + file_name)
    require((status == GOOD and len(rows) > 0 and
             v["numericRows"] == len(rows) and v["invalidRows"] == 0 and v["duplicateRows"] == 0) or
            (status == EMPTY and len(rows) == 0 and v["numericRows"] == 0 and
             v["invalidRows"] == 0 and v["duplicateRows"] == 0) or
            (status == REJECTED and v["numericRows"] > 0 and
             (v["invalidRows"] > 0 or v["duplicateRows"] > 0)),
            "NO11_RESUME_SOURCE_STATUS:" + file_name)
    # Check row values rather than trusting file names alone. No missing bars are invented.
    labels = set()
    for bar in rows:
        require(isinstance(bar, dict), "NO11_RESUME_ROW_OBJECT:" + file_name)
        label = bar.get("label")
        require(isinstance(label, str) and
                re.fullmatch(r"20\d\d-\d\d-\d\dT\d\d:\d\d:00\+09:00", label) and
                label not in labels, "NO11_RESUME_ROW_TIME:" + file_name)
        labels.add(label)
        vals = [bar.get(key) for key in ("open", "high", "low", "close", "volume")]
        require(all(type(v) in (int, float) for v in vals), "NO11_RESUME_ROW_TYPE:" + file_name)
        from math import isfinite
        o, h, l, c, qty = vals
        require(all(isfinite(v) for v in vals) and
                o > 0 and c > 0 and l > 0 and
                l <= min(o,c) <= h and h >= max(o,c) and
                qty >= 0 and int(qty) == qty,
                "NO11_RESUME_ROW_OHLCV:" + file_name)
    return status, len(rows)


def load_symbols(master):
    b = safe_file(master, 250_000)
    require(sha(b) == MASTER_SHA256, "NO11_RESUME_ORIGINAL_LIST_SHA256_MISMATCH")
    ss = b.decode("utf-8-sig").splitlines()
    require(len(ss) == EXPECTED_CAPTURE + FIRST_SKIP, "NO11_RESUME_MASTER_COUNT")
    require(all(SYMBOL_RE.fullmatch(s) for s in ss) and len(set(ss)) == len(ss),
            "NO11_RESUME_MASTER_SYMBOLS")
    return ss[FIRST_SKIP:]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-symbols", type=Path, required=True)
    p.add_argument("--prior-run", type=Path, required=True)
    p.add_argument("--expected-completed", type=int, default=0)
    p.add_argument("--audit-only", action="store_true")
    args = p.parse_args()

    run = args.prior_run.resolve(strict=True)
    require(run.is_dir() and not args.prior_run.is_symlink() and
            re.fullmatch(r"rss-[0-9a-f]{32}", run.name),
            "NO11_RESUME_PRIOR_RUN_ID_INVALID")
    parent = run.parent
    require(parent.is_dir() and not parent.is_symlink(), "NO11_RESUME_PRIVATE_PARENT_UNSAFE")
    symbols = load_symbols(args.original_symbols)

    manifests = {}
    for f in run.iterdir():
        if f.name.startswith("progress-") and f.name.endswith(".json"):
            match = PROGRESS_RE.fullmatch(f.name)
            require(match is not None, "NO11_RESUME_INVALID_CHECKPOINT_NAME")
            manifests[int(match.group(1))] = f
    require(bool(manifests), "NO11_RESUME_NO_SAVED_CHECKPOINTS")
    last = max(manifests)
    require(last % 20 == 0 and last <= len(symbols) and
            len(manifests) == last // 20 and
            set(manifests) == set(range(20, last + 1, 20)),
            "NO11_RESUME_CHECKPOINT_SEQUENCE_BROKEN")
    if args.expected_completed:
        require(last == args.expected_completed, "NO11_RESUME_COMPLETED_COUNT_CHANGED")
    checkpoint_bytes = safe_file(manifests[last], 1_500_000)
    receipt = obj_from_bytes(checkpoint_bytes, manifests[last].name)
    entries = receipt.get("files")
    require(receipt.get("schemaId") == "ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1" and
            type(receipt.get("completed")) is int and receipt["completed"] == last and
            receipt.get("requested") == EXPECTED_CAPTURE and
            isinstance(entries, list) and len(entries) == last,
            "NO11_RESUME_CHECKPOINT_INVALID")
    check_false(receipt, ("productionReady", "orderTransmission"), "checkpoint")

    stored_names = set()
    counts = Counter()
    for i, e in enumerate(entries):
        symbol = symbols[i]
        file_name = f"{i+1:05d}-{symbol.replace('.', '_')}-1M.json"
        require(isinstance(e, dict) and e.get("symbol") == symbol and
                e.get("file") == file_name and
                re.fullmatch(r"[0-9a-f]{64}", e.get("sha256", "")) and
                type(e.get("rows")) is int and e["rows"] >= 0,
                "NO11_RESUME_CHECKPOINT_ENTRY:" + str(i+1))
        data_bytes = safe_file(run/file_name)
        require(sha(data_bytes) == e["sha256"], "NO11_RESUME_DATA_SHA256:" + file_name)
        v = obj_from_bytes(data_bytes, file_name)
        status, n = check_source(v, symbol, i+1, "1M", file_name)
        require(status == e["status"] and n == e["rows"], "NO11_RESUME_ENTRY_DATA_DISAGREES:" + file_name)
        stored_names.add(file_name)
        counts["rows"] += n if status == GOOD else 0
        counts["observed" if status == GOOD else "unavailable"] += 1
        if status == REJECTED:
            counts["quarantined"] += 1

    require(counts["rows"] == receipt.get("rows") and
            counts["observed"] == receipt.get("observedSymbols") and
            counts["unavailable"] == receipt.get("unavailableSymbols") and
            counts["observed"] + counts["unavailable"] == last,
            "NO11_RESUME_CHECKPOINT_SUMS")
    # Detect source files written within the interrupted 20-symbol wave, after
    # the last complete checkpoint. Reuse only a contiguous, fully-audited prefix.
    extras = []
    for f in run.iterdir():
        m = DATA_RE.fullmatch(f.name)
        if m and f.name not in stored_names:
            extras.append((int(m.group(1)), f))
        elif re.fullmatch(r"\d{5}-.*\.json", f.name) and not m:
            raise RuntimeError("NO11_RESUME_UNEXPECTED_SOURCE_FILE:" + f.name)
    extras.sort(key=lambda pair: pair[0])
    require(len(extras) <= 20 and
            [idx for idx, _ in extras] == list(range(last+1, last+len(extras)+1)),
            "NO11_RESUME_PARTIAL_WAVE_NONCONTIGUOUS")
    partial_manifest = []
    for pos, f in extras:
        require(pos <= len(symbols), "NO11_RESUME_PARTIAL_OVERFLOW")
        symbol = symbols[pos-1]
        expected_name = f"{pos:05d}-{symbol.replace('.', '_')}-1M.json"
        require(f.name == expected_name, "NO11_RESUME_PARTIAL_SYMBOL_MISMATCH:" + f.name)
        b = safe_file(f)
        v = obj_from_bytes(b, f.name)
        status, rows = check_source(v, symbol, pos, "1M", f.name)
        partial_manifest.append({"index":pos, "file":f.name, "sha256":sha(b),
                                 "symbol":symbol,"status":status,"rows":rows})
        counts["rows"] += rows if status == GOOD else 0
        counts["observed" if status == GOOD else "unavailable"] += 1
        if status == REJECTED:
            counts["quarantined"] += 1

    completed = last + len(extras)
    remaining = symbols[completed:]
    print(f"NO11_RESUME_VERIFIED_COMPLETE_CHECKPOINT={last}/{len(symbols)}")
    print(f"NO11_RESUME_VERIFIED_PARTIAL_FILES={len(extras)}")
    print(f"NO11_RESUME_ACCEPTED_SYMBOLS={completed}")
    print(f"NO11_RESUME_ACCEPTED_ROWS={counts['rows']}")
    print(f"NO11_RESUME_QUARANTINED_SOURCES={counts['quarantined']}")
    print(f"NO11_RESUME_REMAINING_SYMBOLS={len(remaining)}")
    print("NO11_RESUME_ORIGINAL_DATA_UNCHANGED=True")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")
    if args.audit_only or not remaining:
        return

    output = parent / f"resume-after-{completed:05d}-{uuid4().hex}.txt"
    body = ("\n".join(remaining) + "\n").encode("utf-8")
    with output.open("xb") as w:
        w.write(body)
    manifest = {
      "schemaId":"ARK_NO11_RSS_CAPTURE_IMMUTABLE_RESUME_V1",
      "originalSymbolsSha256":MASTER_SHA256,
      "sourceRun":run.name,
      "checkpointFile":manifests[last].name,
      "checkpointSha256":sha(checkpoint_bytes),
      "completedCheckpoint":last,
      "auditedPartialFiles":partial_manifest,
      "totalPreviouslyCompleted":completed,
      "remainingSymbols":len(remaining),
      "resumeSymbolsFile":output.name,
      "resumeSymbolsSha256":sha(body),
      "result":"SOURCE_CAPTURE_READY_NOT_MODEL_TRAINING",
      "brokerAccess":False,
      "productionReady":False,
      "orderTransmission":False
    }
    with output.with_suffix(".receipt.json").open("x", encoding="utf-8") as w:
        json.dump(manifest,w,sort_keys=True,ensure_ascii=False)
        w.write("\n")
    print("NO11_RESUME_LIST="+str(output))
    print("NO11_RESUME_LIST_SHA256="+sha(body))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("NO11_RSS_RESUME=BLOCKED:"+str(exc), file=sys.stderr)
        print("NO11_PRODUCTION_READY=False",file=sys.stderr)
        print("ORDER_TRANSMISSION=False",file=sys.stderr)
        sys.exit(2)
