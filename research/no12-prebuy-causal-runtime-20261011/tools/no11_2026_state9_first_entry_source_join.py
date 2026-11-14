#!/usr/bin/env python3
"""Frozen State9 RC2 x RSS price: 2026 as-of First Entry SOURCE GAP bridge.

NO native Selector, First Entry P1 fit/score/threshold, H2/H3/H5 R0,
Capital/EXIT, broker, order, Excel, provider request or live knownAt.

Join only historical source observations at ten precommitted clocks on 2026-10-13.
State9 inputs are the TWO ORIGINAL RC2 engines' agreed tick outputs from
prior privately SHA-audited MarketSpeed II RssChart JSON 1M. They assume
1M label is start and theoretical end=label+1minute. The private price
archive is derived 5x1M research bars, NOT a certified provider 5M series.
Nothing here asserts receipt-time point-in-time certifiability.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime,timedelta
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys

sys.dont_write_bytecode=True

SCHEMA="ARK_NO11_2026_RSS_STATE9_TO_FIRST_ENTRY_SOURCE_GAP_V1"
JOINED_SCHEMA="ARK_NO11_2026_RSS_STATE9_PRICE_ASOF_RESEARCH_JOIN_V1"
STATE_SCHEMA="ARK_NO11_2026_RSS_RC2_TECHNICAL_ASOF_STATE_V1"
PRICE_SCHEMA="ARK_NO11_2026_PRICE_ONLY_ASOF_RESEARCH_V1"
RECEIPT_SCHEMA="ARK_NO11_2026_RSS_ORIGINAL_RC2_SPARSE_MISSING_REPLAY_V1"
PRICE_RECEIPT_SCHEMA="ARK_NO11_RSS_2026_OBSERVED_PRICE_ONLY_OUTCOMES_V1"
DAY="2026-10-13"
CLOCKS=("09:30","10:00","10:30","11:00","11:30",
        "13:00","13:30","14:00","14:30","15:00")
SESSION_TICKS=tuple(list(range(540,691))+list(range(750,925))+[930])
STATE_ROWS=244*327
PRICE_ROWS=59712
TODAY_PRICE_ROWS=7539
MASTER_SHA256="22d31026c76dd1a555a2deed2d2b5743004687a239dcc8856b5abeae47782056"
STATE_RECEIPT_BASENAME="no11-2026-rc2-sparse-research-7e563a16a33064a3.json"
STATE_RECEIPT_SHA_PREFIX="7e563a16a33064a3"
PRICE_RECEIPT_BASENAME="no11-2026-price-only-observability-380616e9c2d05eb4.json"
PRICE_RECEIPT_SHA256="380616e9c2d05eb481b5ed160e35b92365822d770e23f9ed80d7295ac883c5e4"
STAGE3_STATE_GZIP="no11-2026-state9-asof-research-10e44a4bb66bef29.jsonl.gz"
STAGE3_STATE_GZIP_SHA="10e44a4bb66bef293637651dd19daefc711a460037e0ec05b994eae1a7be5723"
PRICE_ASOF_GZIP="no11-2026-observed-asof-72422775d56f4502.jsonl.gz"
PRICE_ASOF_GZIP_SHA="72422775d56f450230a8c7c91d6e8ed62fac8e0d66b9aef57c6f16e696d5c851"
SOURCE_INDEX_SHA="4828a387aca426b9692fafa2322aea5384da41a1b0be69b98ace7b74fd8b86e0"
AUDIT_SHA="04294e96395361e6f7030b68bd008135cbe296c588858d0e01e8023fe800f0a7"
H235_2025_TRAINING="PROVISIONALLY_COMPLETE_UNCHANGED"
STATE_SOURCE="RSS_CHART_VALUE2_RESEARCH_ONLY_NOT_JQUANTS_V2"
ALLOWED_PRIMARY=frozenset(("RISE","RISE_STOP","SHARP_RISE","PULLBACK",
      "RANGE","REBOUND","SHARP_DROP","DROP","DROP_STOP"))
EXCLUDED_PRIMARY=frozenset(("PULLBACK","SHARP_DROP"))
STATE_FIELDS=frozenset((
 "schemaId","scheduledClock","researchAssumedBarEnd","sourceLabel",
 "originalNumericStatus","state9CurrentObserved","formalPrimary",
 "basis","directionBasis","activity","originalSource","missingSourceBar",
 "actualBrokerKnownAtCertified","firstEntryP1NativeFeatureRowCertified",
 "eligibleForNativeSelectorOrFirstEntry","futureOutcomeIncluded",
 "productionReady","orderTransmission","symbol","session",
 "sourceArchiveSha256"))
PRICE_FIELDS=frozenset((
 "schemaId","researchId","symbol","session","decisionClockJst",
 "observedReferencePrice","sourceBarWindow","researchAssumedSourceClosedAt",
 "observedPriceAgeMin","frozenSelectorScoreAvailable","modelReady",
 "productionReady","orderTransmission"))


def ensure(ok,why):
    if not ok:raise RuntimeError(why)


def digest(b):
    return hashlib.sha256(b).hexdigest()


def safe_bytes(file,max_size):
    ensure(file.is_file() and not file.is_symlink() and
           0<file.stat().st_size<=max_size,"NO11_STAGE4_FILE_UNSAFE:"+file.name)
    return file.read_bytes()


def checked_json(file,hash_expected,prefix=False):
    b=safe_bytes(file,250_000)
    h=digest(b)
    ensure(h.startswith(hash_expected) if prefix else h==hash_expected,
           "NO11_STAGE4_REPORT_SHA_MISMATCH:"+file.name)
    try:obj=json.loads(b.decode("utf-8-sig"))
    except (UnicodeError,ValueError) as e:
        raise RuntimeError("NO11_STAGE4_INVALID_JSON:"+file.name) from e
    ensure(type(obj) is dict,"NO11_STAGE4_REPORT_NOT_OBJECT")
    return obj,h


def verify_master(master):
    source=safe_bytes(master,250_000)
    ensure(digest(source)==MASTER_SHA256,
           "NO11_STAGE4_ORIGINAL_SYMBOL_MASTER_SHA")
    symbols=source.decode("utf-8-sig").splitlines()
    ensure(len(symbols)==4327 and len(set(symbols))==4327 and
           all(re.fullmatch(r"[0-9A-Z]{4}\.T",sym) for sym in symbols),
           "NO11_STAGE4_ORIGINAL_SYMBOL_MASTER_CHANGED")
    return {sym:i for i,sym in enumerate(symbols)}


def clock_number(stamp):
    ensure(type(stamp) is str and re.fullmatch(r"\d{2}:\d{2}",stamp),
           "NO11_STAGE4_BAD_CLOCK")
    n=int(stamp[:2])*60+int(stamp[3:])
    ensure(0<=n<=24*60 and n%60<60,"NO11_STAGE4_BAD_CLOCK_NUMBER")
    return n


def verified_2026_receipts(state,price):
    ensure(state.get("schemaId")==RECEIPT_SCHEMA and
           state.get("status")=="TECHNICAL_SPARSE_DUAL_ENGINE_PASS_RESEARCH_ONLY" and
           state.get("sourceCoverageCounters",{}).get("sourceInspected")==950 and
           state["sourceCoverageCounters"].get("replayedPairs")==244 and
           state["sourceCoverageCounters"].get("meetsSourceAnchorAndCurrentFloor")==244 and
           state.get("fullEligibleSetTechnicalReplayed") is True and
           state.get("eligibleNotReplayed")==0 and
           state.get("privateState9AsOfEventRows")==STATE_ROWS and
           state.get("privateState9AsOfGzipFilename")==STAGE3_STATE_GZIP and
           state.get("privateState9AsOfGzipSha256")==STAGE3_STATE_GZIP_SHA and
           state.get("inputSourceIndexSha256")==SOURCE_INDEX_SHA and
           state.get("originalSourceAuditSha256")==AUDIT_SHA and
           state.get("technicalErrorCounts")=={} and
           state.get("actualReplayedOriginalFirstEligibleCount")==244 and
           state.get("barTimeSemantics")=="RSS_1M_START_LABEL_ASSUMED_NOT_VENDOR_CERTIFIED" and
           state.get("brokerKnownAtIsInferredNotObserved") is True and
           state.get("trainingPerformed") is False and
           state.get("stateLabelsEligibleForLiveSelectorOrEntry") is False and
           state.get("originalFrozenFilesMutated") is False and
           state.get("productionReady") is False and
           state.get("orderTransmission") is False and
           state.get("researchTechnicalTickCounts",{}).get(
               "totalOriginalDualEngineTickAgreements")==STATE_ROWS and
           state["researchTechnicalTickCounts"].get("nativeAcceptedTicks")==46571 and
           state["researchTechnicalTickCounts"].get("nativeMissingTickCalls")==33217 and
           state["researchTechnicalTickCounts"].get("nativeObservedStateTicks")==25330,
           "NO11_STAGE4_STATE9_RECEIPT_CONTRACT_MISMATCH")
    ensure(price.get("schemaId")==PRICE_RECEIPT_SCHEMA and
           price.get("status")=="PRICE_ONLY_OBSERVED_FUTURE_NO_FROZEN_SELECTOR" and
           price.get("decisionPriceAnchors")==PRICE_ROWS and
           price.get("source5mRows")==337023 and
           price.get("asofOnlyPrivateFilename")==PRICE_ASOF_GZIP and
           price.get("asofOnlySha256")==PRICE_ASOF_GZIP_SHA and
           price.get("nativeSelectorExecuted") is False and
           price.get("firstEntryExecuted") is False and
           price.get("nativeState9Executed") is False and
           price.get("new2026FrozenH235TrainingRows")==0 and
           price.get("futureUnknownNeverConvertedToNegative") is True and
           price.get("productionReady") is False and
           price.get("orderTransmission") is False,
           "NO11_STAGE4_PRICE_RECEIPT_CONTRACT_MISMATCH")


def parse_research_stamp(value,label):
    ensure(type(value) is str and re.fullmatch(
        r"2026-10-13T\d\d:\d\d:00\+09:00",value),label)
    try:time=datetime.fromisoformat(value)
    except ValueError as e:raise RuntimeError(label) from e
    ensure(time.strftime("%Y-%m-%d")==DAY,label)
    return time


def validate_state(row):
    ensure(type(row) is dict and set(row)==STATE_FIELDS and
           row["schemaId"]==STATE_SCHEMA and row["session"]==DAY and
           re.fullmatch(r"[0-9A-Z]{4}\.T",row["symbol"]) and
           re.fullmatch(r"[a-f0-9]{64}",row["sourceArchiveSha256"]) and
           row["actualBrokerKnownAtCertified"] is False and
           row["firstEntryP1NativeFeatureRowCertified"] is False and
           row["eligibleForNativeSelectorOrFirstEntry"] is False and
           row["futureOutcomeIncluded"] is False and
           row["productionReady"] is False and
           row["orderTransmission"] is False and
           row["scheduledClock"] in (
               f"{t//60:02d}:{t%60:02d}" for t in SESSION_TICKS),
           "NO11_STAGE4_STATE_ROW_SCHEMA_OR_FLAGS_INVALID")
    n=clock_number(row["scheduledClock"])
    if row["missingSourceBar"]:
        ensure(row["sourceLabel"] is None and
               row["researchAssumedBarEnd"] is None and
               row["originalSource"] is None and
               row["originalNumericStatus"]=="NOT_AVAILABLE" and
               row["state9CurrentObserved"] is False and
               row["formalPrimary"] is None and
               row["basis"] is None and
               row["directionBasis"] is None and
               row["activity"] is None,
               "NO11_STAGE4_MISSING_BAR_IS_FABRICATED")
    else:
        expected=DAY+"T"+row["scheduledClock"]+":00+09:00"
        ensure(row["sourceLabel"]==expected and
               row["originalSource"]==STATE_SOURCE and
               row["originalNumericStatus"]=="ACCEPTED",
               "NO11_STAGE4_STATE_SOURCE_OR_CLOCK_MISMATCH")
        dt=parse_research_stamp(expected,
                                "NO11_STAGE4_STATE_LABEL_INVALID")
        end=(dt+timedelta(minutes=1)).isoformat(timespec="seconds")
        ensure(row["researchAssumedBarEnd"]==end,
               "NO11_STAGE4_STATE_KNOWN_AT_ASSUMPTION_MISMATCH")
        observed=row["state9CurrentObserved"]
        ensure(type(observed) is bool,
               "NO11_STAGE4_STATE_OBSERVED_FLAG_INVALID")
        if observed:
            ensure(row["formalPrimary"] in ALLOWED_PRIMARY and
                   row["basis"] in (
                       "OBSERVED_FRESH","OBSERVED_NEW_SEGMENT_ONLY"),
                   "NO11_STAGE4_ORIGINAL_STATE_NOT_VALIDLY_OBSERVED")
        else:
            ensure(row["formalPrimary"] is None and row["basis"] is None,
                   "NO11_STAGE4_UNOBSERVED_STATE_MUST_NOT_COUNT")
    return n


def validate_price(row):
    ensure(type(row) is dict and set(row)==PRICE_FIELDS and
           row["schemaId"]==PRICE_SCHEMA and
           re.fullmatch(r"2026-10-(?:01|02|05|06|07|08|09|13)",
                        row.get("session","")) and
           re.fullmatch(r"[0-9A-Z]{4}\.T",row["symbol"]) and
           row["decisionClockJst"] in CLOCKS and
           row["researchId"]=="|".join([
               row["session"],row["decisionClockJst"],row["symbol"]]) and
           type(row["observedReferencePrice"]) in (int,float) and
           math.isfinite(row["observedReferencePrice"]) and
           row["observedReferencePrice"]>0 and
           row["frozenSelectorScoreAvailable"] is False and
           row["modelReady"] is False and
           row["productionReady"] is False and
           row["orderTransmission"] is False,
           "NO11_STAGE4_PRICE_ROW_SCHEMA_OR_SAFETY_INVALID")
    age=row["observedPriceAgeMin"]
    ensure(type(age) is int and 0<=age<=5,
           "NO11_STAGE4_PRICE_AGE_INVALID")
    minute=clock_number(row["sourceBarWindow"])
    ensure(minute in tuple(range(540,690,5))+tuple(range(750,925,5)),
           "NO11_STAGE4_PRICE_SOURCE_5M_OUTSIDE_REGULAR")
    closed=minute+5
    prefix=row["session"]+"T"
    time=f"{closed//60:02d}:{closed%60:02d}:00+09:00"
    ensure(row["researchAssumedSourceClosedAt"]==prefix+time and
           clock_number(row["decisionClockJst"])-closed==age,
           "NO11_STAGE4_PRICE_CLOSED_AFTER_DECISION")
    return (row["session"],row["symbol"],row["decisionClockJst"])


def stream_gzip(root,name,expected_sha,max_compressed=80_000_000):
    file=root/name
    ensure(file.parent==root and file.name==name and
           not file.is_symlink() and file.is_file() and
           0<file.stat().st_size<max_compressed,
           "NO11_STAGE4_PRIVATE_GZIP_MISSING_OR_UNSAFE")
    sha=hashlib.sha256()
    with file.open("rb") as inp:
        for block in iter(lambda:inp.read(1_048_576),b""):
            sha.update(block)
    ensure(sha.hexdigest()==expected_sha,
           "NO11_STAGE4_PRIVATE_GZIP_SHA_MISMATCH:"+name)
    with gzip.open(file,"rt",encoding="utf8") as source:
        for line in source:
            ensure(0<len(line)<10000,
                   "NO11_STAGE4_GZIP_LINE_TOO_LARGE")
            try:row=json.loads(line)
            except ValueError as e:
                raise RuntimeError("NO11_STAGE4_GZIP_INVALID_JSON") from e
            yield row


def inspect_asof_rows(rows,master,expected_symbols=244,
                      expected_rows=STATE_ROWS,expected_accepted=46571,
                      expected_missing=33217,expected_observed=25330):
    """Consume stream, enforce original capture order and all 327 ticks/stock."""
    lookup={};counts=Counter()
    group_symbol=None;group_sha=None;group_pos=-1;tick_index=0
    last_index=-1;symbols=[]
    clocks_by_prior_tick={
        clock_number(clock)-1:clock for clock in CLOCKS
    }
    for row in rows:
        minute=validate_state(row)
        symbol=row["symbol"];index=master.get(symbol)
        ensure(index is not None and index<950,
               "NO11_STAGE4_STATE_SYMBOL_OUTSIDE_FIRST950")
        if symbol!=group_symbol:
            if group_symbol is not None:
                ensure(tick_index==327,
                       "NO11_STAGE4_SPARSE_STATE_GROUP_SHORT")
            ensure(index>last_index and symbol not in lookup,
                   "NO11_STAGE4_STATE_SYMBOL_ORIGINAL_ORDER_BROKEN")
            last_index=index
            group_symbol=symbol
            group_sha=row["sourceArchiveSha256"]
            group_pos=index
            tick_index=0
            lookup[symbol]={}
            symbols.append(symbol)
        else:
            ensure(row["sourceArchiveSha256"]==group_sha,
                   "NO11_STAGE4_STATE_SOURCE_HASH_CHANGED_IN_GROUP")
        ensure(tick_index<len(SESSION_TICKS) and
               minute==SESSION_TICKS[tick_index],
               "NO11_STAGE4_STATE_CLOCK_NOT_EXACT_327_GRID")
        tick_index+=1
        counts["stateRows"]+=1
        if row["missingSourceBar"]:
            counts["missingTicks"]+=1
        else:
            counts["acceptedTicks"]+=1
        if row["state9CurrentObserved"]:
            counts["observedStateTicks"]+=1
        clock=clocks_by_prior_tick.get(minute)
        if clock is not None:
            lookup[symbol][clock]={
                "stateSourceAvailable":not row["missingSourceBar"],
                "state9CurrentObserved":row["state9CurrentObserved"],
                "formalPrimary":row["formalPrimary"],
                "researchAssumedBarClosedAt":row["researchAssumedBarEnd"],
                "stateSourceSha256":group_sha
            }
    ensure(group_symbol is not None and tick_index==327,
           "NO11_STAGE4_STATE_FINAL_GROUP_INCOMPLETE")
    ensure(len(lookup)==expected_symbols and
           len(symbols)==expected_symbols and
           counts["stateRows"]==expected_rows and
           counts["acceptedTicks"]==expected_accepted and
           counts["missingTicks"]==expected_missing and
           counts["observedStateTicks"]==expected_observed and
           all(len(lookup[s])==len(CLOCKS) for s in symbols),
           "NO11_STAGE4_STATE_COUNT_OR_CLOCK_CONTRACT_DRIFT")
    return lookup,symbols,counts


def inspect_price_rows(rows,selected,expected_total=PRICE_ROWS,
                       expected_today=TODAY_PRICE_ROWS):
    today={};counts=Counter()
    for row in rows:
        key=validate_price(row)
        counts["priceRows"]+=1
        if key[0]==DAY:
            counts["todayRows"]+=1
            if key[1] in selected:
                join=(key[1],key[2])
                ensure(join not in today,
                       "NO11_STAGE4_DUPLICATE_PRICE_AT_CLOCK")
                today[join]=row
    ensure(counts["priceRows"]==expected_total and
           counts["todayRows"]==expected_today,
           "NO11_STAGE4_2026_PRICE_ANCHOR_COUNT_MISMATCH")
    return today,counts


def join_day_sources(state_lookup,symbols,prices):
    per_clock={clock:Counter() for clock in CLOCKS}
    join=[];totals=Counter()
    for symbol in symbols:
        for clock in CLOCKS:
            state=state_lookup[symbol][clock]
            price=prices.get((symbol,clock))
            c=per_clock[clock]
            totals["checkedSymbolClocks"]+=1;c["checkedSymbolClocks"]+=1
            if state["stateSourceAvailable"]:
                totals["stateSourcePresent"]+=1;c["stateSourcePresent"]+=1
            if state["state9CurrentObserved"]:
                totals["state9CurrentObserved"]+=1;c["state9CurrentObserved"]+=1
            if price is not None:
                totals["researchPriceAvailable"]+=1;c["researchPriceAvailable"]+=1
            excluded=state["formalPrimary"] in EXCLUDED_PRIMARY
            if excluded:
                totals["originalEntryStateExcluded"]+=1
                c["originalEntryStateExcluded"]+=1
            joined=bool(price is not None and state["state9CurrentObserved"])
            allowed=bool(joined and not excluded)
            if joined:totals["stateAndPriceResearchOverlap"]+=1;c["stateAndPriceResearchOverlap"]+=1
            if allowed:
                totals["overlapWithoutFrozenExcludedStates"]+=1
                c["overlapWithoutFrozenExcludedStates"]+=1
            if price is None: reason="SOURCE_PRICE_UNAVAILABLE"
            elif not state["state9CurrentObserved"]: reason="STATE9_CURRENT_NOT_OBSERVED"
            elif excluded:reason="FROZEN_STATE9_ENTRY_EXCLUDED"
            else:reason="RESEARCH_STATE_PRICE_SOURCE_OVERLAP_NOT_NATIVE_FIRST_ENTRY"
            totals["reason:"+reason]+=1
            join.append({
                "schemaId":JOINED_SCHEMA,"session":DAY,
                "symbol":symbol,"decisionClockJst":clock,
                "state9SourceAvailable":state["stateSourceAvailable"],
                "state9CurrentObserved":state["state9CurrentObserved"],
                "formalPrimary":state["formalPrimary"],
                "state9ResearchAssumedClosedAt":state["researchAssumedBarClosedAt"],
                "state9SourceArchiveSha256":state["stateSourceSha256"],
                "researchPriceAvailable":price is not None,
                "referencePriceResearchOnly":(
                    price["observedReferencePrice"] if price is not None else None),
                "researchPriceAssumedClosedAt":(
                    price["researchAssumedSourceClosedAt"] if price is not None else None),
                "originalSelectorWatchObserved":False,
                "originalFirstEntryP1ScoreObserved":False,
                "originalFirstEntryQ70ThresholdObserved":False,
                "nativeState9KnownAtCertified":False,
                "researchStateAndPriceOverlap":joined,
                "researchNonExcludedOverlap":allowed,
                "nativeFirstEntryCandidateEmitted":False,
                "blockedReason":reason,
                "futurePriceOrTeacherIncluded":False,
                "productionReady":False,"orderTransmission":False
            })
    ensure(totals["checkedSymbolClocks"]==len(symbols)*len(CLOCKS),
           "NO11_STAGE4_JOIN_COUNT_MISMATCH")
    return join,totals,per_clock


def immutable(root,name,data):
    file=root/name
    ensure(file.parent==root,"NO11_STAGE4_OUTPUT_DIRECTORY_MISMATCH")
    if file.exists():
        ensure(file.is_file() and not file.is_symlink() and
               file.read_bytes()==data,
               "NO11_STAGE4_EXISTING_OUTPUT_NOT_IDENTICAL")
    else:
        with file.open("xb") as stream:
            stream.write(data)
    return file


def main(args):
    root=args.private_root.resolve(strict=True)
    ensure(root.is_dir() and not args.private_root.is_symlink() and
           not root.is_symlink(),
           "NO11_STAGE4_PRIVATE_ROOT_INVALID")
    master=verify_master(args.original_symbols)
    state,state_sha=checked_json(root/STATE_RECEIPT_BASENAME,
                                  STATE_RECEIPT_SHA_PREFIX,prefix=True)
    price,price_sha=checked_json(root/PRICE_RECEIPT_BASENAME,
                                PRICE_RECEIPT_SHA256)
    verified_2026_receipts(state,price)
    st,syms,counts=inspect_asof_rows(
        stream_gzip(root,state["privateState9AsOfGzipFilename"],
                    state["privateState9AsOfGzipSha256"]),master)
    px,price_counts=inspect_price_rows(
        stream_gzip(root,price["asofOnlyPrivateFilename"],
                    price["asofOnlySha256"]),set(syms))
    joined,totals,per_clock=join_day_sources(st,syms,px)
    ensure(len(joined)==2440 and
           totals["checkedSymbolClocks"]==2440,
           "NO11_STAGE4_JOIN_EXPECTED_2440_MISMATCH")
    # Private per-symbol records never go to public GitHub or the receipt.
    memory=io.BytesIO()
    with gzip.GzipFile(fileobj=memory,filename="",mode="wb",mtime=0,
                       compresslevel=6) as writer:
        for row in joined:
            writer.write((json.dumps(row,sort_keys=True,separators=(",",":"),
                                     ensure_ascii=False,allow_nan=False)+"\n").encode())
    raw=memory.getvalue()
    raw_sha=digest(raw)
    name="no11-2026-first-entry-source-join-"+raw_sha[:16]+".jsonl.gz"
    out=immutable(root,name,raw)
    summary={
       "schemaId":SCHEMA,
       "status":"PRICE_AND_FROZEN_RC2_STATE9_SOURCE_CLOCK_JOIN_RESEARCH_ONLY",
       "session":DAY,
       "sourceState9SparseReportSha256":state_sha,
       "sourceState9AsOfGzipSha256":state["privateState9AsOfGzipSha256"],
       "sourcePriceOnlyReportSha256":price_sha,
       "sourcePriceAsOfGzipSha256":price["asofOnlySha256"],
       "sourceSymbolsOriginalMasterSha256":MASTER_SHA256,
       "symbolsOriginalFirst950Inspected":950,
       "symbolsOriginalRc2DualAgreed":244,
       "stateAsOfRowsVerified":counts["stateRows"],
       "stateAcceptedOneMinuteTicksVerified":counts["acceptedTicks"],
       "stateNativeMissingTickCallsVerified":counts["missingTicks"],
       "statePrimaryObservedTicksVerified":counts["observedStateTicks"],
       "priceOnlyArchiveDecisionAnchorsVerified":price_counts["priceRows"],
       "priceOnlyArchiveCurrentSessionAnchorsVerified":price_counts["todayRows"],
       "sourceClocksCompared":totals["checkedSymbolClocks"],
       "aggregateCoverage":dict(sorted(totals.items())),
       "byFrozenSelectorDecisionClock":{
          clock:dict(sorted(per_clock[clock].items())) for clock in CLOCKS},
       "privatePriceStateJoinedFilename":name,
       "privatePriceStateJoinedSha256":raw_sha,
       "privatePriceStateJoinedRows":len(joined),
       "firstEntryOriginalP1Q70FeatureInputsAvailable":False,
       "frozenSelectorWatchEventsAvailable":False,
       "originalH235R0ExecutedOn2026":False,
       "new2026SupervisedModelTrainingRows":0,
       "historicalBrokerReceivedAtCertified":False,
       "state9SourceVendorIdentityCertified":False,
       "fiveMinutePriceVendorParityCertified":False,
       "overlapCanProduceRealOrders":False,
       "originalFrozenModelFilesChanged":False,
       "nativeSelectorExecuted":False,
       "nativeFirstEntryExecuted":False,
       "nativeCapitalExitExecuted":False,
       "productionReady":False,"orderTransmission":False
    }
    body=(json.dumps(summary,sort_keys=True,indent=2,
                     ensure_ascii=False,allow_nan=False)+"\n").encode("utf8")
    hs=digest(body)
    reportfile=immutable(root,"no11-2026-first-entry-source-join-gap-"+
                         hs[:16]+".json",body)
    print("NO11_2026_FIRST_ENTRY_SOURCE_JOIN=PASS_RESEARCH_ONLY")
    print("NO11_STATE9_SOURCE_SYMBOLS=244")
    print("NO11_FIXED_CLOCKS_ASOF_EXAMINED="+str(totals["checkedSymbolClocks"]))
    print("NO11_PRICE_STATE_OVERLAP="+str(totals["stateAndPriceResearchOverlap"]))
    print("NO11_NOT_EXCLUDED_STATE_PRICE_OVERLAP="+str(
        totals["overlapWithoutFrozenExcludedStates"]))
    print("NO11_PRIVATE_FIRST_ENTRY_SOURCE_ROWS="+str(len(joined)))
    print("NO11_FIRST_ENTRY_SOURCE_JOIN_REPORT="+str(reportfile))
    print("NO11_FROZEN_SELECTOR_FIRST_ENTRY_EXECUTED=False")
    print("NO11_2026_NEW_SUPERVISED_MODEL_ROWS=0")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")


def offline_self_test():
    def clock(n):return f"{n//60:02d}:{n%60:02d}"
    def state(s,n,observed=False,primary=None):
        t=clock(n);label=f"{DAY}T{t}:00+09:00"
        return {
          "schemaId":STATE_SCHEMA,"scheduledClock":t,"sourceLabel":label,
          "researchAssumedBarEnd":(
             datetime.fromisoformat(label)+timedelta(minutes=1)).isoformat(),
          "originalNumericStatus":"ACCEPTED",
          "state9CurrentObserved":observed,
          "formalPrimary":primary if observed else None,
          "basis":"OBSERVED_FRESH" if observed else None,
          "directionBasis":None,"activity":None,
          "originalSource":STATE_SOURCE,"missingSourceBar":False,
          "actualBrokerKnownAtCertified":False,
          "firstEntryP1NativeFeatureRowCertified":False,
          "eligibleForNativeSelectorOrFirstEntry":False,
          "futureOutcomeIncluded":False,"productionReady":False,
          "orderTransmission":False,"symbol":s,"session":DAY,
          "sourceArchiveSha256":"a"*64
        }
    def price(sym,tm):
        at=clock_number(tm)
        minute=at-5
        return {
          "schemaId":PRICE_SCHEMA,"symbol":sym,"session":DAY,
          "decisionClockJst":tm,"researchId":f"{DAY}|{tm}|{sym}",
          "observedReferencePrice":1000.0,
          "sourceBarWindow":clock(minute),
          "researchAssumedSourceClosedAt":f"{DAY}T{tm}:00+09:00",
          "observedPriceAgeMin":0,"frozenSelectorScoreAvailable":False,
          "modelReady":False,"productionReady":False,
          "orderTransmission":False
        }
    first="1001.T";second="1002.T"
    state_rows=[]
    for symbol in (first,second):
        for n in SESSION_TICKS:
            observed=n in (569,599,659,779)
            primary=("PULLBACK" if symbol==first and n==599 else "RISE")
            state_rows.append(state(symbol,n,observed,primary))
    master={first:0,second:1}
    lookup,symbols,counts=inspect_asof_rows(
        state_rows,master,expected_symbols=2,expected_rows=654,
        expected_accepted=654,expected_missing=0,expected_observed=8)
    prices=[
        price(first,"09:30"),price(first,"10:00"),
        price(second,"09:30"),price(second,"10:00")
    ]
    price_index,c=inspect_price_rows(
        prices,set(symbols),expected_total=4,expected_today=4)
    joined,totals,byclock=join_day_sources(lookup,symbols,price_index)
    assert len(joined)==20 and totals["checkedSymbolClocks"]==20
    assert totals["stateAndPriceResearchOverlap"]==4
    assert totals["overlapWithoutFrozenExcludedStates"]==3
    assert all(x["nativeFirstEntryCandidateEmitted"] is False for x in joined)
    future=price(first,"09:30")
    future["researchAssumedSourceClosedAt"]=f"{DAY}T09:35:00+09:00"
    try:validate_price(future)
    except RuntimeError as e:
        assert "PRICE_CLOSED_AFTER_DECISION" in str(e)
    else:raise AssertionError("FUTURE_PRICE_ACCEPTED")
    fake=state(first,569,True,"RISE")
    fake["eligibleForNativeSelectorOrFirstEntry"]=True
    try:validate_state(fake)
    except RuntimeError:pass
    else:raise AssertionError("UNPROVEN_NATIVE_READY_ACCEPTED")
    corrupted=state(first,569)
    corrupted["futureHigh"]=5000
    try:validate_state(corrupted)
    except RuntimeError:pass
    else:raise AssertionError("FUTURE_FEATURE_FIELD_ACCEPTED")
    missing=state(first,569)
    missing.update(missingSourceBar=True,sourceLabel=None,
                   researchAssumedBarEnd=None,originalSource=None,
                   originalNumericStatus="NOT_AVAILABLE",
                   state9CurrentObserved=False,formalPrimary=None,basis=None)
    validate_state(missing)
    print("NO11_STAGE4_FIRST_ENTRY_RSS_STATE9_ASOF_JOIN_SYNTHETIC=PASS")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline-self-test",action="store_true")
    p.add_argument("--private-root",type=Path)
    p.add_argument("--original-symbols",type=Path)
    a=p.parse_args()
    try:
        if a.offline_self_test:offline_self_test()
        else:
            ensure(a.private_root is not None and
                   a.original_symbols is not None,
                   "NO11_STAGE4_REQUIRED_ARGUMENTS_MISSING")
            main(a)
    except Exception as exc:
        msg=str(exc)
        if not re.fullmatch(r"NO11_STAGE4_[A-Z0-9_]+(?::[A-Za-z0-9._-]+)?",msg):
            msg="NO11_STAGE4_UNEXPECTED_DATA_OR_RUNTIME_ERROR"
        print("NO11_2026_FIRST_ENTRY_SOURCE_JOIN=BLOCKED:"+msg,file=sys.stderr)
        print("NO11_PRODUCTION_READY=False",file=sys.stderr)
        print("ORDER_TRANSMISSION=False",file=sys.stderr)
        sys.exit(2)
