#!/usr/bin/env python3
"""Offline 2026 RSS source-to-replay index, NOT native Selector/First Entry.

Reads the user's three immutable RssChart 1M runs, validates each saved source
against its capture checkpoint and the already-passed aggregate audit, and
derives only chronological source coverage and a noncertified closed-bar
prefix rule.  No labels, model inference, live use, broker access, orders, or
retroactive observed/known-at claims. Outputs only PRIVATE local files.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
import re
import sys
from pathlib import Path

from no11_rss_batch_resume_manifest import (
    check_source, load_symbols, obj_from_bytes, require, safe_file, sha, GOOD, EMPTY
)

sys.dont_write_bytecode = True
SESSION_DAYS = (
    "2026-10-01","2026-10-02","2026-10-05","2026-10-06",
    "2026-10-07","2026-10-08","2026-10-09","2026-10-13"
)
AUDIT_SHA256 = "04294e96395361e6f7030b68bd008135cbe296c588858d0e01e8023fe800f0a7"
EXPECTED_TOTAL = (4327, 4071, 256, 3705797)
RUN_LIMITS = (20, 1380, 2927)
RUN_REQUESTED = (20, 4307, 2927)
RUN_END_SHA = (
    "1b682e8cb13c5b2700952fa648f626f3c9dea2f13cb2148ab127aa6660e3eea6",
    "4a438ea31c9cd17c80ffc38a481245b77468c072286fccb03685248b72c4b2f3",
    "9c1e76ef5bea5ae60bb015c91bfbeac4b6ea60af81b1d3599385a0782fbc2ce7"
)
PRIORITY_WATCH_COUNT = 950


def inspected_market_minute(label):
    """Validate historic RssChart clock as an observed label, not known-at."""
    require(type(label) is str and
            re.fullmatch(r"20\d\d-\d\d-\d\dT\d\d:\d\d:00\+09:00", label),
            "NO11_REPLAY_BAR_LABEL_INVALID")
    day = label[:10]
    require(day in SESSION_DAYS, "NO11_REPLAY_UNEXPECTED_SOURCE_SESSION")
    hh, mm = int(label[11:13]), int(label[14:16])
    minute = hh * 60 + mm
    require((540 <= minute <= 690) or (750 <= minute <= 930),
            "NO11_REPLAY_OUTSIDE_RSS_CASH_GRID")
    special = ("MORNING_TERMINAL_LABEL" if minute == 690 else
               "AFTERNOON_TERMINAL_LABEL" if minute == 930 else
               "OPENING_OR_MIXED_LABEL" if minute in (540,750) else
               "REGULAR_UNVERIFIED_LABEL")
    return day, minute, special


def assumed_closed_before_decision(label, decision_at):
    """Conservative +1 minute, for offline exploratory replay ONLY.

    A label might be interval-start or interval-end. The broker's actual
    publication time is unknown, so this rule never confers live usability.
    """
    inspected_market_minute(label)
    require(type(decision_at) is str and
            re.fullmatch(r"20\d\d-\d\d-\d\dT\d\d:\d\d:00\+09:00", decision_at),
            "NO11_REPLAY_DECISION_TIME_INVALID")
    when = datetime.fromisoformat(decision_at)
    require(when.tzinfo is not None and decision_at[:10] in SESSION_DAYS,
            "NO11_REPLAY_DECISION_DATE_INVALID")
    src = datetime.fromisoformat(label)
    return src.date() == when.date() and src + timedelta(minutes=1) <= when


def preceding_observed_day_pairs(dates):
    seen = set(dates)
    return sum(SESSION_DAYS[i-1] in seen and SESSION_DAYS[i] in seen
               for i in range(1,len(SESSION_DAYS)))


def immutable_write(path, payload):
    require(path.parent.is_dir() and not path.parent.is_symlink(),
            "NO11_REPLAY_OUTPUT_PARENT_INVALID")
    if path.exists():
        require(path.is_file() and not path.is_symlink() and
                sha(safe_file(path, max(1_000_000, len(payload)+100))) == sha(payload),
                "NO11_REPLAY_EXISTING_FILE_CHANGED")
        return
    with path.open("xb") as f:
        f.write(payload)


def run(args):
    master = args.original_symbols
    b = safe_file(master,250000)
    symbols = b.decode("utf-8-sig").splitlines()
    # load_symbols independently checks the original SHA, symbol syntax and 4327 count.
    require(symbols[20:] == load_symbols(master),
            "NO11_REPLAY_ORIGINAL_SYMBOLS_DIVERGED")
    audit_data = safe_file(args.audit_report,200000)
    require(sha(audit_data) == AUDIT_SHA256, "NO11_REPLAY_AUDIT_SHA_MISMATCH")
    original_audit = obj_from_bytes(audit_data,args.audit_report.name)
    require(original_audit.get("schemaId") ==
            "ARK_NO11_RSS_TRAINING_ALL_RUNS_SOURCE_AUDIT_V1" and
            original_audit.get("result") ==
            "SOURCE_SHA256_AND_ROW_AUDIT_PASS_NOT_SUPERVISED_TRAINING" and
            original_audit.get("symbolsRequested") == EXPECTED_TOTAL[0] and
            original_audit.get("symbolsObserved") == EXPECTED_TOTAL[1] and
            original_audit.get("symbolsUnavailable") == EXPECTED_TOTAL[2] and
            original_audit.get("dataRows") == EXPECTED_TOTAL[3] and
            original_audit.get("modelFitPerformed") is False and
            original_audit.get("productionReady") is False and
            original_audit.get("orderTransmission") is False,
            "NO11_REPLAY_SOURCE_AUDIT_NOT_APPROVED")

    capture_root = args.capture_root.resolve(strict=True)
    require(capture_root.is_dir() and not args.capture_root.is_symlink() and
            not capture_root.is_symlink(),
            "NO11_REPLAY_CAPTURE_ROOT_INVALID")
    audit_runs=original_audit.get("runs")
    require(isinstance(audit_runs,list) and len(audit_runs)==3,
            "NO11_REPLAY_MISSING_AUDIT_RUNS")

    offset=0
    seen_observed=0
    seen_unavailable=0
    all_rows=0
    full_eight=0
    watch_observed=0
    watch_full_eight=0
    symbol_day_pairs=0
    observed_day_symbol_counts=Counter()
    all_day_rows=Counter()
    specials=Counter()
    private_lines=[]
    for ri,(limit,requested) in enumerate(zip(RUN_LIMITS,RUN_REQUESTED)):
        aud=audit_runs[ri]
        require(aud.get("completed")==limit and
                aud.get("lastProgressSha256")==RUN_END_SHA[ri] and
                aud.get("fullSourceSha256Verified") is True and
                aud.get("fullSourceOHLCVVerified") is True and
                aud.get("productionReady") is False and
                aud.get("orderTransmission") is False and
                re.fullmatch(r"rss-[0-9a-f]{32}",aud.get("runDirectory","")),
                "NO11_REPLAY_RUN_AUDIT_MISMATCH")
        folder=capture_root / aud["runDirectory"]
        require(folder.is_dir() and not folder.is_symlink(),
                "NO11_REPLAY_SAVED_RUN_MISSING")
        cp_path=folder/f"progress-{limit:05d}.json"
        cp_bytes=safe_file(cp_path, 2_000_000)
        require(sha(cp_bytes)==RUN_END_SHA[ri],
                "NO11_REPLAY_CHECKPOINT_TAMPERED")
        cp=obj_from_bytes(cp_bytes,cp_path.name)
        files=cp.get("files")
        require(cp.get("schemaId")=="ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1" and
                cp.get("completed")==limit and
                cp.get("requested")==requested and
                isinstance(files,list) and len(files)==limit and
                cp.get("productionReady") is False and
                cp.get("orderTransmission") is False,
                "NO11_REPLAY_CHECKPOINT_SEMANTICS_CHANGED")
        run_rows=0
        run_ok=0
        run_empty=0
        for local_i, e in enumerate(files):
            position=offset+local_i
            symbol=symbols[position]
            filename=f"{local_i+1:05d}-{symbol.replace('.','_')}-1M.json"
            require(e.get("file")==filename and e.get("symbol")==symbol and
                    re.fullmatch(r"[a-f0-9]{64}",e.get("sha256","")),
                    "NO11_REPLAY_SYMBOL_LEDGER_MISMATCH")
            raw=safe_file(folder/filename)
            require(sha(raw)==e["sha256"],
                    "NO11_REPLAY_SYMBOL_HASH_MISMATCH:"+filename)
            obj=obj_from_bytes(raw,filename)
            status, count=check_source(obj,symbol,local_i+1,"1M",filename)
            require(status==e.get("status") and count==e.get("rows") and
                    status in (GOOD,EMPTY),
                    "NO11_REPLAY_SYMBOL_SOURCE_INVALID")
            byday=Counter()
            clocks=Counter()
            first={}
            last={}
            prev=None
            for bar in obj["rows"] if status==GOOD else ():
                label=bar["label"]
                day,_,kind=inspected_market_minute(label)
                # A provider archive can arrive with rows out of order. Sort
                # is allowed downstream; keep disorder observable in ledger.
                if prev is not None and label<=prev:
                    clocks["NON_MONOTONE_LABEL_ORDER"]+=1
                prev=label
                byday[day]+=1
                clocks[kind]+=1
                first[day]=min(first.get(day,label),label)
                last[day]=max(last.get(day,label),label)
            n_days=len(byday)
            if status==GOOD:
                run_ok+=1
                seen_observed+=1
                if position<PRIORITY_WATCH_COUNT: watch_observed+=1
                if n_days==8:
                    full_eight+=1
                    if position<PRIORITY_WATCH_COUNT:watch_full_eight+=1
                for day, num in byday.items():
                    observed_day_symbol_counts[day]+=1
                    all_day_rows[day]+=num
                symbol_day_pairs+=preceding_observed_day_pairs(byday)
                specials.update(clocks)
            else:
                run_empty+=1
                seen_unavailable+=1
            run_rows+=count if status==GOOD else 0
            all_rows+=count if status==GOOD else 0
            private_lines.append(json.dumps({
                "symbol":symbol,"captureRun":ri+1,"sourceSha256":e["sha256"],
                "status":status,"historicalMinuteRows":count if status==GOOD else 0,
                "sessions":dict(sorted(byday.items())),
                "firstSeenBarLabels":dict(sorted(first.items())),
                "lastSeenBarLabels":dict(sorted(last.items())),
                "observedAdjacentSessionPairs":preceding_observed_day_pairs(byday),
                "historicalActualKnownAt":"UNKNOWN",
                "eligibleAsNativeSelectorInput":False,
                "eligibleAs2026SupervisedTrainingRow":False,
                "productionReady":False,"orderTransmission":False
            },separators=(",",":"),ensure_ascii=False))
        require(run_rows==aud.get("rows") and run_ok==aud.get("observed") and
                run_empty==aud.get("unavailable"),
                "NO11_REPLAY_RUN_AGGREGATE_CHANGED")
        offset+=limit
        print("NO11_REPLAY_RUN_VERIFIED="+str(ri+1)+"|SYMBOLS="+str(limit)+
              "|ROWS="+str(run_rows),flush=True)
    require(offset==EXPECTED_TOTAL[0] and
            (seen_observed,seen_unavailable,all_rows)==EXPECTED_TOTAL[1:] and
            full_eight==3864 and
            dict(sorted(all_day_rows.items()))==
                original_audit.get("aggregateRowsByDate"),
            "NO11_REPLAY_AGGREGATE_VS_AUDIT_DISAGREES")
    payload=("\n".join(private_lines)+"\n").encode("utf-8")
    digest=sha(payload)
    receipt={
      "schemaId":"ARK_NO11_2026_RSS_CAUSAL_SOURCE_REPLAY_INDEX_V1",
      "result":"POSTHOC_PRICE_INDEX_PASS_SELECTOR_ENTRY_NOT_REBUILT",
      "sourceAuditSha256":AUDIT_SHA256,
      "sourceIndexSha256":digest,
      "sourceIndexFile":"no11-2026-source-index-"+digest[:16]+".jsonl",
      "sourceRows":all_rows,
      "sourceSymbols":offset,
      "observedSymbols":seen_observed,
      "unavailableSymbols":seen_unavailable,
      "eightSessionObservedSymbols":full_eight,
      "first950HistoricalWatchSymbolsObserved":watch_observed,
      "first950HistoricalWatchSymbolsAllEightDays":watch_full_eight,
      "adjacentObservedSymbolSessionPairs":symbol_day_pairs,
      "sessions":SESSION_DAYS,
      "rowsBySession":dict(sorted(all_day_rows.items())),
      "observedSymbolCountBySession":dict(sorted(observed_day_symbol_counts.items())),
      "barClockCategories":dict(sorted(specials.items())),
      "offlineConservativePrefixRule":"Assume bar un-usable until label+1m; NEVER vendor known-at certification",
      "nativeSelectorRebuilt":False,
      "nativeFirstEntryRebuilt":False,
      "nativeState9FromRssCertified":False,
      "historicalVendorBarIntervalCertified":False,
      "historicalActualKnownAtCertified":False,
      "historicalTeacherRebuilt":False,
      "2026SupervisedTrainingExamples":0,
      "researchOnly":True,
      "productionReady":False,
      "orderTransmission":False
    }
    out=capture_root/receipt["sourceIndexFile"]
    immutable_write(out,payload)
    report_bytes=(json.dumps(receipt,sort_keys=True,indent=2,
                             ensure_ascii=False)+"\n").encode("utf-8")
    report_hash=sha(report_bytes)
    report_file=capture_root/("no11-2026-replay-readiness-"+report_hash[:16]+".json")
    immutable_write(report_file,report_bytes)
    print("NO11_RSS_2026_REPLAY_INDEX=PASS_SOURCE_ONLY")
    print("NO11_REPLAY_SYMBOLS_WITH_ALL_EIGHT_SESSIONS="+str(full_eight))
    print("NO11_REPLAY_FIRST950_OBSERVED="+str(watch_observed))
    print("NO11_REPLAY_FIRST950_ALL_EIGHT_SESSIONS="+str(watch_full_eight))
    print("NO11_REPLAY_INDEX_PRIVATE_FILE="+str(out))
    print("NO11_REPLAY_INDEX_SHA256="+digest)
    print("NO11_REPLAY_REPORT_FILE="+str(report_file))
    print("NO11_REPLAY_REPORT_SHA256="+report_hash)
    print("NO11_NATIVE_SELECTOR_FIRST_ENTRY_REBUILT=False")
    print("NO11_MODEL_2026_SUPERVISED_ROWS=0")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")


def self_test():
    assert inspected_market_minute("2026-10-13T15:30:00+09:00")[2]=="AFTERNOON_TERMINAL_LABEL"
    assert inspected_market_minute("2026-10-13T11:30:00+09:00")[2]=="MORNING_TERMINAL_LABEL"
    assert inspected_market_minute("2026-10-13T12:30:00+09:00")[2]=="OPENING_OR_MIXED_LABEL"
    assert not assumed_closed_before_decision(
        "2026-10-13T09:30:00+09:00","2026-10-13T09:30:00+09:00")
    assert assumed_closed_before_decision(
        "2026-10-13T09:30:00+09:00","2026-10-13T09:31:00+09:00")
    assert not assumed_closed_before_decision(
        "2026-10-09T15:30:00+09:00","2026-10-13T09:30:00+09:00")
    assert preceding_observed_day_pairs(("2026-10-01","2026-10-05","2026-10-06"))==1
    assert preceding_observed_day_pairs(SESSION_DAYS)==7
    for bad in ("2026-10-14T09:01:00+09:00",
                "2026-10-13T12:01:00+09:00",
                "2026-10-13T15:31:00+09:00"):
        try:
            inspected_market_minute(bad)
        except RuntimeError:
            continue
        raise AssertionError("INVALID_BAR_TIME_ACCEPTED")
    print("NO11_RSS_2026_REPLAY_INDEX_OFFLINE_SELFTEST=PASS")
    print("ORDER_TRANSMISSION=False")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline-self-test",action="store_true")
    p.add_argument("--original-symbols",type=Path)
    p.add_argument("--audit-report",type=Path)
    p.add_argument("--capture-root",type=Path)
    args=p.parse_args()
    if args.offline_self_test:
        self_test()
        return
    require(all((args.original_symbols,args.audit_report,args.capture_root)),
            "NO11_REPLAY_REQUIRED_LOCAL_ARGS_MISSING")
    run(args)


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print("NO11_RSS_2026_REPLAY_INDEX=BLOCKED:"+str(exc),file=sys.stderr)
        print("NO11_PRODUCTION_READY=False",file=sys.stderr)
        print("ORDER_TRANSMISSION=False",file=sys.stderr)
        sys.exit(2)
