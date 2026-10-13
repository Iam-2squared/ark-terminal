#!/usr/bin/env python3
"""Offline verification of No.1.1's three immutable RSS training-source runs.

Full SHA256 verification of every captured symbol plus per-row OHLCV and date
coverage. Aggregate ONLY. No Excel, RSS, order, network, model training,
replacement of Frozen strategy, or provenance promotion.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

from no11_rss_batch_resume_manifest import (
    MASTER_SHA256, check_source, obj_from_bytes, safe_file, sha, load_symbols,
    require, GOOD, EMPTY, REJECTED,
)

sys.dont_write_bytecode = True
EXPECTED_FULL = 4327
EXPECTED_RUNS = (20, 1380, 2927)
EXPECTED_OBSERVED = (19, 1312, 2740)
EXPECTED_UNAVAILABLE = (1, 68, 187)
EXPECTED_ROWS = (12683, 928225, 2764889)
SYMBOL_COLUMNS = ("open", "high", "low", "close", "volume")


def path_guard(path):
    require(path.is_dir() and not path.is_symlink()
            and re.fullmatch(r"rss-[0-9a-f]{32}", path.name),
            "NO11_ALL_RSS_RUN_FOLDER_INVALID:" + path.name)
    require(not path.parent.is_symlink(), "NO11_ALL_RSS_RUN_PARENT_SYMLINK")
    return path


def audit_run(root, run_symbols, *, name="batch", exact=True):
    """Verify every checkpoint and source file; return only aggregates.

    run_symbols can be short synthetic lists in offline tests.
    """
    root = path_guard(root)
    n = len(run_symbols)
    require(n > 0 and n <= 5000, "NO11_ALL_RSS_RUN_COUNT_INVALID")
    expected_checkpoints = [min(i+20,n) for i in range(0,n,20)]
    actual_checkpoints = sorted(
        int(m.group(1)) for f in root.iterdir()
        if (m := re.fullmatch(r"progress-(\d{5})\.json", f.name))
    )
    require(actual_checkpoints == expected_checkpoints,
            "NO11_ALL_RSS_PROGRESS_SEQUENCE_MISSING:" + name)
    checkpoints = {}
    for cutoff in actual_checkpoints:
        b = safe_file(root / f"progress-{cutoff:05d}.json", 2_000_000)
        cp = obj_from_bytes(b, f"progress-{cutoff:05d}.json")
        require(cp.get("schemaId") == "ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1"
                and type(cp.get("completed")) is int and cp["completed"] == cutoff
                and type(cp.get("requested")) is int and cp["requested"] == n
                and isinstance(cp.get("files"), list)
                and len(cp["files"]) == cutoff
                and cp.get("productionReady") is False
                and cp.get("orderTransmission") is False,
                "NO11_ALL_RSS_PROGRESS_SCHEMA_INVALID:" + str(cutoff))
        checkpoints[cutoff] = (b, cp)

    last = checkpoints[n][1]
    names = set()
    counts = Counter()
    dates = Counter()
    days_per_symbol = Counter()
    rows_per_symbol = Counter()
    earliest = None
    latest = None
    nonempty_symbols = 0
    seen_source_names = set()
    for idx, e in enumerate(last["files"], start=1):
        symbol = run_symbols[idx-1]
        fname = f"{idx:05d}-{symbol.replace('.', '_')}-1M.json"
        require(isinstance(e, dict) and e.get("symbol") == symbol and
                e.get("file") == fname and
                type(e.get("rows")) is int and e["rows"] >= 0 and
                re.fullmatch(r"[0-9a-f]{64}", e.get("sha256","")),
                "NO11_ALL_RSS_PROGRESS_ENTRY_MISMATCH:" + str(idx))
        b = safe_file(root / fname)
        require(sha(b) == e["sha256"], "NO11_ALL_RSS_SHA256_FAIL:" + fname)
        data = obj_from_bytes(b, fname)
        status, row_count = check_source(data, symbol, idx, "1M", fname)
        require(status == e.get("status") and e["rows"] == row_count,
                "NO11_ALL_RSS_FILE_DISAGREES_WITH_PROGRESS:" + fname)
        require(data.get("sourceFunction") == "RssChart" and
                data.get("period") == "1M", "NO11_ALL_RSS_SOURCE_CHANGED")
        require(isinstance(data.get("observedAt"), str) and
                datetime.fromisoformat(data["observedAt"]).utcoffset() is not None,
                "NO11_ALL_RSS_LOCAL_OBSERVATION_TIME_INVALID:" + fname)
        names.add(fname)
        counts["seen"] += 1
        if status == GOOD:
            counts["observed"] += 1
            counts["rows"] += row_count
        elif status == EMPTY:
            counts["unavailable"] += 1
        else:
            counts["quarantined"] += 1
        seen_dates = set()
        for bar in data["rows"] if status == GOOD else ():
            label = bar["label"]
            day = label[:10]
            seen_dates.add(day)
            dates[day] += 1
            earliest = label if earliest is None or label < earliest else earliest
            latest = label if latest is None or label > latest else latest
        if status == GOOD:
            nonempty_symbols += 1
            days_per_symbol[len(seen_dates)] += 1
            rows_per_symbol[row_count] += 1
        del b, data
        if idx in checkpoints:
            cp = checkpoints[idx][1]
            require(cp["files"] == last["files"][:idx] and
                    cp.get("rows") == counts["rows"] and
                    cp.get("observedSymbols") == counts["observed"] and
                    cp.get("unavailableSymbols") ==
                      counts["unavailable"] + counts["quarantined"],
                    "NO11_ALL_RSS_INTERMEDIATE_PROGRESS_DISAGREEMENT:" + str(idx))

    actual_names = set()
    for f in root.iterdir():
        if re.fullmatch(r"\d{5}-.*\.json", f.name):
            actual_names.add(f.name)
        elif f.name.endswith(".json") and not re.fullmatch(r"progress-\d{5}\.json", f.name):
            raise RuntimeError("NO11_ALL_RSS_UNKNOWN_JSON_FILE:" + f.name)
    require(names == actual_names and len(names) == n,
            "NO11_ALL_RSS_CAPTURE_FILE_COVERAGE_MISMATCH")
    require(counts["seen"] == n and
            last["observedSymbols"] == counts["observed"] and
            last["unavailableSymbols"] ==
              counts["unavailable"] + counts["quarantined"] and
            last["rows"] == counts["rows"],
            "NO11_ALL_RSS_FINAL_SUMMARY_NOT_REPRODUCED")
    return {
        "runName": name, "runDirectory": root.name,
        "completed": counts["seen"], "observed": counts["observed"],
        "unavailable": counts["unavailable"],
        "quarantined": counts["quarantined"], "rows": counts["rows"],
        "firstLabel": earliest, "lastLabel": latest,
        "rowsByDay": dict(sorted(dates.items())),
        "symbolsByAvailableDays": {str(k):v for k,v in sorted(days_per_symbol.items())},
        "symbolRowRange": [
            min(rows_per_symbol) if rows_per_symbol else None,
            max(rows_per_symbol) if rows_per_symbol else None,
        ],
        "lastProgressSha256": sha(checkpoints[n][0]),
        "fullSourceSha256Verified": True,
        "fullSourceOHLCVVerified": True,
        "sourceIsFullyCausalOrMarketCertified": False,
        "productionReady": False,
        "orderTransmission": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-symbols", type=Path, required=True)
    p.add_argument("--first-run", type=Path, required=True)
    p.add_argument("--second-run", type=Path, required=True)
    p.add_argument("--third-run", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    symbols = load_symbols(args.original_symbols)
    require(len(symbols) == EXPECTED_FULL-20, "NO11_ALL_RSS_MASTER_SYMBOL_COUNT")
    full_bytes = safe_file(args.original_symbols, 250_000)
    full = full_bytes.decode("utf-8-sig").splitlines()
    require(len(full) == EXPECTED_FULL, "NO11_ALL_RSS_ORIGINAL_LIST_COUNT")
    runs = [path_guard(pth.resolve(strict=True)) for pth in
            (args.first_run, args.second_run, args.third_run)]
    require(len(set(runs)) == 3, "NO11_ALL_RSS_RUNS_NOT_DISTINCT")
    segments = [full[:20], full[20:1400], full[1400:]]
    require([len(s) for s in segments] == list(EXPECTED_RUNS),
            "NO11_ALL_RSS_SEGMENT_BOUNDARIES_INVALID")
    results = []
    for i,(root, ss) in enumerate(zip(runs, segments)):
        result = audit_run(root, ss, name=("FIRST20","NEXT1380","LAST2927")[i])
        require((result["completed"], result["observed"],
                 result["unavailable"], result["quarantined"], result["rows"]) ==
                (EXPECTED_RUNS[i], EXPECTED_OBSERVED[i],
                 EXPECTED_UNAVAILABLE[i], 0, EXPECTED_ROWS[i]),
                "NO11_ALL_RSS_AGGREGATE_CHANGED:" + result["runName"])
        results.append(result)
        print(f"NO11_ALL_RSS_RUN_{i+1}_VERIFIED={result['completed']}|"
              f"OBSERVED={result['observed']}|"
              f"UNAVAILABLE={result['unavailable']}|ROWS={result['rows']}", flush=True)

    counts = Counter()
    by_day = Counter()
    for r in results:
        for k in ("completed","observed","unavailable","quarantined","rows"):
            counts[k] += r[k]
        by_day.update(r["rowsByDay"])
    require((counts["completed"],counts["observed"],counts["unavailable"],
             counts["quarantined"],counts["rows"]) == (4327,4071,256,0,3705797),
            "NO11_ALL_RSS_TOTAL_DISAGREEMENT")
    require(all(d <= "2026-10-13" for d in by_day),
            "NO11_ALL_RSS_FUTURE_DATE_OBSERVED")
    require(args.out_dir.is_dir() and not args.out_dir.is_symlink(),
            "NO11_ALL_RSS_REPORT_DIR_INVALID")
    report={
      "schemaId": "ARK_NO11_RSS_TRAINING_ALL_RUNS_SOURCE_AUDIT_V1",
      "originalSymbolsSha256": MASTER_SHA256,
      "source": "RssChart value2 1M read-only",
      "result": "SOURCE_SHA256_AND_ROW_AUDIT_PASS_NOT_SUPERVISED_TRAINING",
      "dataRows": counts["rows"],
      "symbolsRequested": counts["completed"],
      "symbolsObserved": counts["observed"],
      "symbolsUnavailable": counts["unavailable"],
      "symbolsQuarantined": counts["quarantined"],
      "aggregateRowsByDate": dict(sorted(by_day.items())),
      "runs": results,
      "marketCoverageCertified": False,
      "vendorFirstKnownAtCertified": False,
      "nativeSelectorEntryFeatureTeacherRebuilt": False,
      "supervised2026TrainingRowsCertified": 0,
      "modelFitPerformed": False,
      "productionReady": False,
      "orderTransmission": False
    }
    b=(json.dumps(report,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
    digest=sha(b)
    report_path=args.out_dir / f"rss-all-source-audit-{digest[:16]}.json"
    with report_path.open("xb") as dst:
        dst.write(b)
    print("NO11_ALL_RSS_AUDIT=SOURCE_PASS_NOT_MODEL_TRAINING")
    print("NO11_ALL_RSS_SYMBOLS_VERIFIED=4327")
    print("NO11_ALL_RSS_VALID_SYMBOLS=4071")
    print("NO11_ALL_RSS_UNAVAILABLE_SYMBOLS=256")
    print("NO11_ALL_RSS_VALID_ROWS=3705797")
    print("NO11_ALL_RSS_DAYS="+",".join(sorted(by_day)))
    print("NO11_ALL_RSS_AUDIT_FILE="+str(report_path))
    print("NO11_ALL_RSS_AUDIT_SHA256="+digest)
    print("NO11_MODEL_TRAINING_READY=False")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("NO11_ALL_RSS_SOURCE_AUDIT=BLOCKED:"+str(e), file=sys.stderr)
        print("NO11_PRODUCTION_READY=False",file=sys.stderr)
        print("ORDER_TRANSMISSION=False",file=sys.stderr)
        sys.exit(2)
