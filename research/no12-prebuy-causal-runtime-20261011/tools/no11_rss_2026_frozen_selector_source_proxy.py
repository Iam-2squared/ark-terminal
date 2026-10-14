#!/usr/bin/env python3
"""Immutable private 2026 RSS 1M -> provisional 5M Selector-source research bridge.

This is NOT the frozen Selector adapter: saved RssChart OHLCV does not certify
vendor interval semantics, first-seen timestamps, original daily/master
admission, sector/liquidity features, or State9. The only generated 5M bars
contain five distinct observed 1M labels from a continuous cash-session bin;
no partial bar, fill, interpolation or future lookup is permitted.

All processing is OFFLINE; outputs remain private. Frozen models and original
files never change. Only source-availability proxies, NEVER native scores.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

from no11_rss_batch_resume_manifest import (
    check_source, load_symbols, obj_from_bytes, require, safe_file, sha, GOOD, EMPTY
)
from no11_rss_2026_source_replay_index import (
    AUDIT_SHA256, SESSION_DAYS, EXPECTED_TOTAL, RUN_LIMITS,
    RUN_REQUESTED, RUN_END_SHA, inspected_market_minute
)

sys.dont_write_bytecode = True
REPLAY_SHA256 = "0385190d35d519ddef0bc0107dc77c149170385d34a41a21491cfbb82b83cc60"
INDEX_SHA256 = "4828a387aca426b9692fafa2322aea5384da41a1b0be69b98ace7b74fd8b86e0"
FREEZE_BLOB = "6c707566eb074ce89656be1626bd5aed63d044a8"
DECISIONS = ("09:30","10:00","10:30","11:00","11:30",
             "13:00","13:30","14:00","14:30","15:00")
REQUIRED_FEATURES = (
    "currentReturnPct","momentum30Pct","vwapDistancePct",
    "vwapSlope15Pct","logCumulativeTurnover","volumeAccelerationRatio",
    "trendEfficiency","rangeExpansionPct","timeOfDayFraction",
    "segmentStandard","segmentGrowth","liquidityLow","liquidityHigh",
    "marketBreadthPositivePct","sectorBreadthPositivePct"
)
CAN_DERIVE_RESEARCH_PROXY = (
    "currentReturnPct","momentum30Pct","vwapDistancePct",
    "vwapSlope15Pct","logCumulativeTurnover","volumeAccelerationRatio",
    "trendEfficiency","rangeExpansionPct","timeOfDayFraction",
    "marketBreadthPositivePct"
)
NEEDS_EXTERNAL_FROZEN_CONTEXT = (
    "segmentStandard","segmentGrowth","liquidityLow",
    "liquidityHigh","sectorBreadthPositivePct"
)
SCHEMA = "ARK_NO11_2026_RSS_5M_SOURCE_PROXY_NOT_FROZEN_SELECTOR_V1"
REPORT_SCHEMA = "ARK_NO11_2026_RSS_FROZEN_SELECTOR_SOURCE_GAP_AUDIT_V1"
SCOPE_CHOICES = ("priority950","all4327")
MORNING = tuple(range(540,690,5))          # 09:00..11:29 (30 complete bins)
AFTERNOON = tuple(range(750,925,5))       # 12:30..15:24 (35 complete bins)
VALID_STARTS = frozenset(MORNING+AFTERNOON)
EXPECTED_5M_PER_DAY = len(VALID_STARTS)      # 65, terminal auctions excluded
# The 4,327-symbol index holds eight sessions of first/last observed labels.
# It legitimately exceeds 5MB; retain a strict 32 MiB cap and full SHA-256 pin.
MAX_SOURCE_INDEX_BYTES = 32 * 1024 * 1024


def strict_json(path, expected_sha, size=250_000):
    content=safe_file(path,size)
    require(sha(content)==expected_sha, "NO11_SELECTOR_PROXY_INPUT_HASH_MISMATCH:"+path.name)
    return obj_from_bytes(content,path.name)


def strict_index(path, expected_sha):
    raw=safe_file(path,MAX_SOURCE_INDEX_BYTES)
    require(sha(raw)==expected_sha,"NO11_SELECTOR_PROXY_INDEX_HASH_MISMATCH")
    rows=[json.loads(ln) for ln in raw.decode("utf8").splitlines()]
    require(len(rows)==EXPECTED_TOTAL[0] and all(isinstance(x,dict) for x in rows),
            "NO11_SELECTOR_PROXY_INDEX_ROW_COUNT")
    return rows


def five_minute_bins(rows):
    """Use complete observed 5x1M *labels* within JPX regular windows.

    The end label plus one minute is an offline conservative assumption only.
    Returns closed-interval price references; NOT a vendor-certified 5M feed.
    """
    slots={}
    auction=Counter()
    for bar in rows:
        day,t,kind=inspected_market_minute(bar["label"])
        if kind=="MORNING_TERMINAL_LABEL" or kind=="AFTERNOON_TERMINAL_LABEL":
            auction[kind]+=1
            continue
        if 540<=t<690:
            start=540+5*((t-540)//5)
        elif 750<=t<925:
            start=750+5*((t-750)//5)
        else:
            auction["OUTSIDE_FULL_5M_REGULAR_GRID"]+=1
            continue
        require(start in VALID_STARTS,
                "NO11_SELECTOR_PROXY_BIN_OUTSIDE_REGULAR")
        key=(day,start)
        slots.setdefault(key,{})
        require(t not in slots[key],"NO11_SELECTOR_PROXY_DUPLICATE_1M_LABEL")
        slots[key][t]=bar
    finalized=[]
    incompletes=Counter()
    for (day,start),items in sorted(slots.items()):
        required=set(range(start,start+5))
        if set(items)!=required:
            incompletes[day]+=1
            continue
        bars=[items[t] for t in range(start,start+5)]
        open_=bars[0]["open"]
        close=bars[-1]["close"]
        high=max(x["high"] for x in bars)
        low=min(x["low"] for x in bars)
        volume=sum(x["volume"] for x in bars)
        end=start+5
        close_time=f"{day}T{end//60:02d}:{end%60:02d}:00+09:00"
        require(low<=min(open_,close)<=max(open_,close)<=high,
                "NO11_SELECTOR_PROXY_COMBINED_OHLC_INVALID")
        require(volume>=0 and float(volume).is_integer() and volume<=2**53,
                "NO11_SELECTOR_PROXY_COMBINED_VOLUME_INVALID")
        finalized.append({
            "session":day,"firstSourceLabel":bars[0]["label"],
            "lastSourceLabel":bars[-1]["label"],
            "fiveMinuteWindowStart":f"{start//60:02d}:{start%60:02d}",
            "researchAssumedNotBefore":close_time,
            "open":open_,"high":high,"low":low,"close":close,
            "volume":int(volume),"componentOneMinuteRows":5,
            "vendorFiveMinuteParityCertified":False,
            "actualVendorAvailableAtCertified":False
        })
    return finalized,incompletes,auction


def time_minutes(t):
    return int(t[:2])*60+int(t[3:])


def decision_price_availability(bins, day):
    """Latest *provisional* complete 5M bin at each frozen decision clock."""
    byday=sorted(
        [r for r in bins if r["session"]==day],
        key=lambda r:r["researchAssumedNotBefore"]
    )
    accepted={}
    for at in DECISIONS:
        minute=time_minutes(at)
        safe=[r for r in byday
              if time_minutes(r["researchAssumedNotBefore"][11:16])<=minute]
        latest=safe[-1] if safe else None
        age=(minute-time_minutes(latest["researchAssumedNotBefore"][11:16])
             if latest is not None else None)
        accepted[at]=age is not None and 0<=age<=5
    return accepted


def append_immutable(output_dir, compressed_file, digest):
    final=output_dir/f"no11-2026-5m-proxy-{digest[:16]}.jsonl.gz"
    if final.exists():
        require(final.is_file() and not final.is_symlink() and
                sha(safe_file(final, max(final.stat().st_size+1,1_000_000)))==digest,
                "NO11_SELECTOR_PROXY_EXISTING_5M_FILE_TAMPERED")
    else:
        # NTFS/POSIX create-hard-link is exclusive and never replaces a file.
        os.link(compressed_file,final)
    compressed_file.unlink()
    return final


def main(args):
    require(args.scope in SCOPE_CHOICES,
            "NO11_SELECTOR_PROXY_SCOPE_INVALID")
    src_root=args.capture_root.resolve(strict=True)
    require(src_root.is_dir() and not args.capture_root.is_symlink() and
            not src_root.is_symlink(),"NO11_SELECTOR_PROXY_CAPTURE_DIR_UNSAFE")
    require(args.out_dir.is_dir() and not args.out_dir.is_symlink(),
            "NO11_SELECTOR_PROXY_OUTPUT_DIR_UNSAFE")
    original = safe_file(args.original_symbols,250000)
    full=original.decode("utf-8-sig").splitlines()
    require(len(full)==EXPECTED_TOTAL[0] and full[20:]==load_symbols(args.original_symbols),
            "NO11_SELECTOR_PROXY_MASTER_INVALID")
    audit=strict_json(args.audit_report,AUDIT_SHA256,200000)
    replay=strict_json(args.replay_report,REPLAY_SHA256,200000)
    index=strict_index(args.source_index,INDEX_SHA256)
    require(audit.get("result")=="SOURCE_SHA256_AND_ROW_AUDIT_PASS_NOT_SUPERVISED_TRAINING" and
            audit.get("symbolsRequested")==4327 and
            audit.get("dataRows")==3705797 and
            audit.get("productionReady") is False and
            audit.get("orderTransmission") is False and
            replay.get("schemaId")=="ARK_NO11_2026_RSS_CAUSAL_SOURCE_REPLAY_INDEX_V1" and
            replay.get("sourceIndexSha256")==INDEX_SHA256 and
            replay.get("sourceAuditSha256")==AUDIT_SHA256 and
            replay.get("nativeSelectorRebuilt") is False and
            replay.get("nativeFirstEntryRebuilt") is False and
            replay.get("productionReady") is False and
            replay.get("orderTransmission") is False,
            "NO11_SELECTOR_PROXY_SOURCE_CHAIN_INVALID")
    require(all(index[i].get("symbol")==full[i] and
                index[i].get("productionReady") is False and
                index[i].get("orderTransmission") is False
                for i in range(EXPECTED_TOTAL[0])),
            "NO11_SELECTOR_PROXY_SYMBOL_INDEX_ORDER_INVALID")
    frozen_bytes=safe_file(args.frozen_selector,12_000_000)
    import subprocess
    # Preserve Git's blob identity, not arbitrary JSON rewrites.
    # Avoid network calls; Git reads the local working tree only.
    frozen_path=args.frozen_selector.resolve(strict=True)
    frozen_rel="predict/research/phase57-long-only-frozen-selector-v1.json"
    require(frozen_path.as_posix().endswith("/"+frozen_rel),
            "NO11_SELECTOR_PROXY_FROZEN_FILE_PATH_INVALID")
    frozen_repo=frozen_path.parents[2]
    frozen_sha=subprocess.run(
        ["git","-C",str(frozen_repo),"hash-object","--path="+frozen_rel,
         str(frozen_path)],
        capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    require(frozen_sha==FREEZE_BLOB,
            "NO11_SELECTOR_PROXY_FROZEN_FREEZE_BLOB_CHANGED")
    frozen=obj_from_bytes(frozen_bytes,args.frozen_selector.name)
    spec=frozen["freezePayload"]["selectorSpecification"]
    require(tuple(spec["featureUniverse"]["orderedNames"])==REQUIRED_FEATURES and
            tuple(spec["ranking"]["decisionTimesJst"])==DECISIONS and
            spec["ranking"]["topN"]==5 and
            spec["eligibility"]["maximumAgeWallClockMinutes"]==5 and
            spec["eligibility"]["forwardFillAllowed"] is False,
            "NO11_SELECTOR_PROXY_FROZEN_SELECTOR_CONTRACT_CHANGED")
    keep=PRIORITY_WATCH_COUNT if args.scope=="priority950" else EXPECTED_TOTAL[0]
    days=Counter()
    accepted=Counter()
    day_all_bins=Counter()
    day_incomplete_bins=Counter()
    auctions=Counter()
    full_days=Counter()
    available_decisions={d:{t:0 for t in DECISIONS} for d in SESSION_DAYS}
    first_watch={d:{t:0 for t in DECISIONS} for d in SESSION_DAYS}
    observed=0
    source_rows=0
    five_rows=0
    seen=0

    runs=[]
    offset=0
    for runidx,(limit,requested,expected_hash) in enumerate(zip(
            RUN_LIMITS,RUN_REQUESTED,RUN_END_SHA)):
        dirname=audit["runs"][runidx]["runDirectory"]
        require(re.fullmatch(r"rss-[0-9a-f]{32}",dirname),
                "NO11_SELECTOR_PROXY_RUN_NAME_UNSAFE")
        folder=src_root/dirname
        require(folder.is_dir() and not folder.is_symlink(),
                "NO11_SELECTOR_PROXY_RUN_DIR_UNSAFE")
        cp_path=folder/f"progress-{limit:05d}.json"
        cp=strict_json(cp_path,expected_hash,2_000_000)
        require(cp.get("completed")==limit and
                cp.get("requested")==requested and
                len(cp["files"])==limit and
                cp.get("productionReady") is False and
                cp.get("orderTransmission") is False,
                "NO11_SELECTOR_PROXY_CAPTURE_PROGRESS_INVALID")
        runs.append((folder,cp))
        offset+=limit

    run_ends=[]
    boundary=0
    for count in RUN_LIMITS:
        boundary+=count
        run_ends.append(boundary)
    require(run_ends[-1]==EXPECTED_TOTAL[0],
            "NO11_SELECTOR_PROXY_UNEXPECTED_RUN_BOUNDARIES")

    # tmp is private within user-local capture dir; never overwritten.
    tmp=args.out_dir/f".no11-5m-part-{uuid4().hex}"
    try:
        with tmp.open("xb") as fp:
            with gzip.GzipFile(fileobj=fp,mode="wb",mtime=0,filename="") as writer:
                for pos in range(keep):
                    ri=next(i for i,end in enumerate(run_ends) if pos<end)
                    local=pos-(0 if ri==0 else run_ends[ri-1])
                    folder,cp=runs[ri]
                    entry=cp["files"][local]
                    sym=full[pos]
                    filename=f"{local+1:05d}-{sym.replace('.','_')}-1M.json"
                    require(entry.get("symbol")==sym and
                            entry.get("file")==filename and
                            entry.get("sha256")==index[pos].get("sourceSha256"),
                            "NO11_SELECTOR_PROXY_SOURCE_INDEX_CHECKPOINT_DIFFER")
                    source=safe_file(folder/filename)
                    require(sha(source)==entry["sha256"],
                            "NO11_SELECTOR_PROXY_RAW_ARCHIVE_HASH_CHANGED")
                    ob=obj_from_bytes(source,filename)
                    status,count=check_source(ob,sym,local+1,"1M",filename)
                    require(status==entry["status"] and
                            count==entry["rows"] and
                            status in (GOOD,EMPTY),
                            "NO11_SELECTOR_PROXY_BAD_SOURCE")
                    seen+=1
                    if status==EMPTY:continue
                    observed+=1
                    source_rows+=count
                    bins,incompletes,specials=five_minute_bins(ob["rows"])
                    five_rows+=len(bins)
                    auctions.update(specials)
                    day_incomplete_bins.update(incompletes)
                    perday=Counter(x["session"] for x in bins)
                    for day,num in perday.items():
                        days[day]+=1
                        day_all_bins[day]+=num
                        if num==EXPECTED_5M_PER_DAY: full_days[day]+=1
                    for day in SESSION_DAYS:
                        got=decision_price_availability(bins,day)
                        for at,yes in got.items():
                            if yes:
                                available_decisions[day][at]+=1
                                if pos<PRIORITY_WATCH_COUNT:first_watch[day][at]+=1
                    for b in bins:
                        # Store only exact 5x1M provisional aggregation,
                        # not a Selector event, model score, or teacher.
                        b.update({
                            "schemaId":SCHEMA,"symbol":sym,
                            "sourceOneMinuteArchiveSha256":entry["sha256"],
                            "syntheticHistoricalAvailabilityRule":"LAST_LABEL_PLUS_1M",
                            "sourceIdentity":"MARKETSPEED_II_RSS_CHART_1M",
                            "eligibleForFrozenSelectorRuntime":False,
                            "productionReady":False,"orderTransmission":False
                        })
                        writer.write((json.dumps(b,separators=(",",":"),
                                                 sort_keys=True,allow_nan=False)+"\n").encode())
                    if seen%200==0:
                        print("NO11_SELECTOR_PROXY_PROGRESS="+str(seen)+"/"+str(keep),
                              flush=True)
        gz_digest=sha(safe_file(tmp,max(tmp.stat().st_size+1,1_000_000)))
        final=append_immutable(args.out_dir,tmp,gz_digest)
    finally:
        if tmp.exists():tmp.unlink()

    if args.scope=="all4327":
        require((seen,observed,source_rows)==
                (EXPECTED_TOTAL[0],EXPECTED_TOTAL[1],EXPECTED_TOTAL[3]),
                "NO11_SELECTOR_PROXY_INPUT_FULL_RUN_COUNTS_CHANGED")
    require(five_rows>0 and all(v<=seen for v in available_decisions[SESSION_DAYS[-1]].values()),
            "NO11_SELECTOR_PROXY_5M_RUN_INVALID")
    report={
      "schemaId":REPORT_SCHEMA,
      "status":"RESEARCH_PRICE_SOURCE_PROXY_CREATED_NOT_NATIVE_SELECTOR",
      "scope":args.scope,"symbolsInspected":seen,
      "symbolsWithSourceBars":observed,"oneMinuteSourceRows":source_rows,
      "completeProvisionalFiveMinuteRows":five_rows,
      "expectedFiveMinuteBinsPerFullObservedDay":EXPECTED_5M_PER_DAY,
      "fiveMinuteGzipSha256":gz_digest,
      "fiveMinuteGzipPrivateFilename":final.name,
      "sourceReplayReportSha256":REPLAY_SHA256,
      "sourceAuditSha256":AUDIT_SHA256,
      "sourceIndexSha256":INDEX_SHA256,
      "frozenSelectorGitBlobSha":FREEZE_BLOB,
      "frozenDecisionClocksJst":DECISIONS,
      "frozenTopN":5,
      "observedCompleteFiveMinuteRowsBySession":dict(sorted(day_all_bins.items())),
      "symbolsWithAtLeastOneCompleteFiveMinuteBarBySession":dict(sorted(days.items())),
      "symbolsWith65CompleteBarsBySession":dict(sorted(full_days.items())),
      "incompleteFiveMinuteBinsDiscardedBySession":dict(sorted(day_incomplete_bins.items())),
      "excludedSpecialOneMinuteRows":dict(sorted(auctions.items())),
      "provisionalDecisionPriceAvailableSymbolsBySession":available_decisions,
      "priority950ProvisionalDecisionPriceAvailableSymbolsBySession":first_watch,
      "frozen15FeatureNames":REQUIRED_FEATURES,
      "researchPriceDerivedFeatureFamiliesOnly":CAN_DERIVE_RESEARCH_PROXY,
      "nonPriceFrozenFeatureMetadataNotInRssCapture":NEEDS_EXTERNAL_FROZEN_CONTEXT,
      "observationEligibilityIsNotNativeSelectorEligibility":True,
      "segmentSectorClassificationCertified":False,
      "originalPriorDailyEligibilityCertified":False,
      "frozenFiveMinuteAggregationParityCertified":False,
      "historicalBarArrivalTimeCertified":False,
      "fixedClockPriceConventionCertified":False,
      "nativeSelectorRun":False,
      "nativeFirstEntryRun":False,
      "nativeState9Run":False,
      "researchH235ScoringRun":False,
      "supervisedTrainingRowsAdded2026":0,
      "frozenNo11Changed":False,
      "productionReady":False,"orderTransmission":False
    }
    report_bytes=(json.dumps(report,sort_keys=True,indent=2,
                             ensure_ascii=False,allow_nan=False)+"\n").encode()
    report_digest=sha(report_bytes)
    receipt=args.out_dir/f"no11-2026-selector-source-gap-{report_digest[:16]}.json"
    if receipt.exists():
        require(sha(safe_file(receipt,250000))==report_digest,
                "NO11_SELECTOR_PROXY_PREEXISTING_RECEIPT_TAMPERED")
    else:
        with receipt.open("xb") as f:f.write(report_bytes)
    print("NO11_SELECTOR_2026_SOURCE_BRIDGE=PROXY_ONLY_PASS")
    print("NO11_SELECTOR_PROXY_SCOPE="+args.scope)
    print("NO11_SELECTOR_PROXY_1M_ROWS="+str(source_rows))
    print("NO11_SELECTOR_PROXY_COMPLETE_5M_ROWS="+str(five_rows))
    print("NO11_SELECTOR_PROXY_GZIP="+str(final))
    print("NO11_SELECTOR_PROXY_GZIP_SHA256="+gz_digest)
    print("NO11_SELECTOR_PROXY_RECEIPT="+str(receipt))
    print("NO11_NATIVE_SELECTOR_REBUILT=False")
    print("NO11_NATIVE_FIRST_ENTRY_REBUILT=False")
    print("NO11_2026_SUPERVISED_ROWS_ADDED=0")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")


def offline_selftest():
    def bar(day,t):
        hh,mm=divmod(t,60)
        return {"label":f"{day}T{hh:02d}:{mm:02d}:00+09:00",
                "open":100.0+t-540,"high":101.0+t-540,
                "low":99.0+t-540,"close":100.5+t-540,
                "volume":10}
    day=SESSION_DAYS[-1]
    a=[bar(day,t) for t in range(540,550)]
    a.append(bar(day,690))
    bins,missing,special=five_minute_bins(a)
    assert len(bins)==2 and not missing
    assert bins[0]["researchAssumedNotBefore"]==day+"T09:05:00+09:00"
    assert bins[0]["volume"]==50
    assert special["MORNING_TERMINAL_LABEL"]==1
    assert decision_price_availability(bins,day)["09:30"] is False
    assert decision_price_availability(bins,day)["10:00"] is False
    assert decision_price_availability(bins,day)["11:30"] is False
    # A single missing 1M input must never generate a partial 5M bar.
    q=[x for x in a if x["label"]!=day+"T09:02:00+09:00"]
    bins,missing,special=five_minute_bins(q)
    assert len(bins)==1 and missing[day]==1
    # Any genuine decision 09:30 can only use 09:25-09:29 +1 minute,
    # never the 09:30 price itself.
    final,_missing,_special=five_minute_bins(
        [bar(day,t) for t in range(565,575)])
    assert decision_price_availability(final,day)["09:30"] is True
    assert decision_price_availability(final,day)["10:00"] is False
    assert len(REQUIRED_FEATURES)==15
    assert set(CAN_DERIVE_RESEARCH_PROXY+NEEDS_EXTERNAL_FROZEN_CONTEXT)==set(REQUIRED_FEATURES)
    print("NO11_SELECTOR_2026_SOURCE_BRIDGE_OFFLINE_SELFTEST=PASS")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline-self-test",action="store_true")
    p.add_argument("--original-symbols",type=Path)
    p.add_argument("--audit-report",type=Path)
    p.add_argument("--replay-report",type=Path)
    p.add_argument("--source-index",type=Path)
    p.add_argument("--capture-root",type=Path)
    p.add_argument("--out-dir",type=Path)
    p.add_argument("--frozen-selector",type=Path)
    p.add_argument("--scope",default="priority950",choices=SCOPE_CHOICES)
    a=p.parse_args()
    try:
        if a.offline_self_test:
            offline_selftest()
        else:
            require(all((a.original_symbols,a.audit_report,a.replay_report,
                         a.source_index,a.capture_root,a.out_dir,a.frozen_selector)),
                    "NO11_SELECTOR_PROXY_REQUIRED_ARGS_MISSING")
            main(a)
    except Exception as exc:
        print("NO11_SELECTOR_2026_SOURCE_BRIDGE=BLOCKED:"+str(exc),
              file=sys.stderr)
        print("NO11_PRODUCTION_READY=False",file=sys.stderr)
        print("ORDER_TRANSMISSION=False",file=sys.stderr)
        sys.exit(2)
