#!/usr/bin/env python3
"""Stage 3: original Frozen RC2 sparse-bar missingness research, OFFLINE ONLY.

This is not a new/changed State9 engine. On verified 2026 MarketSpeed II
RssChart 1M archives, use exact original normalize80/120 and candidate/
independent engine code, feed NO_ADMISSIBLE_CLOSED_BAR as raw=None at each
missing current 1M scheduled tick, and compare both original outputs.

Historical bar label+one minute is ONLY a research hypothetical availability,
not the observed broker receivedAt. The source is Excel Value2 JSON, NOT
original J-Quants decimal lexemes; original frozen source identity and real
native readiness remain unproven. Never issue a Selector candidate or order.
"""
import argparse
from collections import Counter
from datetime import datetime,timedelta
import json
from pathlib import Path
import re
import sys

from no11_rss_batch_resume_manifest import (
    check_source,load_symbols,obj_from_bytes,require,safe_file,sha,GOOD,EMPTY
)
import no11_2026_rss_original_rc2_dual_technical as parent

sys.dont_write_bytecode=True
REPORT_SCHEMA="ARK_NO11_2026_RSS_ORIGINAL_RC2_SPARSE_MISSING_REPLAY_V1"
BASELINE_REPORT_SHA="2e79d4f530ed492bf8c82a1df63b641ba1b3ab5c6ab4608c6a9b9c3adefbd5bc"
EARLIER_DAY="2026-10-09"
TODAY="2026-10-13"
CHECKED_SYMBOLS=950
# Explicit research-quality floors. Not frozen signal thresholds or a native
# source availability contract. Lower-coverage names are counted as blocked.
MIN_PREVIOUS_CONSECUTIVE_PAIRS=30
MIN_CURRENT_OBSERVED_BARS=15
ANCHOR_CLOCKS=("09:00","12:30","15:30")
SOURCE_TAG=parent.SOURCE_TAG
COMPARE=parent.COMPARE
SCHEDULE=parent.SCHEDULE
CLOCKS=parent.CLOCKS


def previous_continuous_source_pairs(previous):
    """Count only adjacent CONTINUOUS original 1M labels for M0 U.

    Opening/auction samples NEVER count; this is source availability only.
    """
    mins=[int(r["label"][11:13])*60+int(r["label"][14:16])
          for r in previous]
    return sum(1 for a,b in zip(mins,mins[1:])
               if b==a+1 and
               ((541<=a<b<690) or (751<=a<b<925)))


def precondition(previous,current):
    """Keep previous reference non-fabricated and normalize only real pairs."""
    if not previous:return "PREVIOUS_SESSION_ABSENT"
    clockset={r["label"][11:16] for r in previous}
    if not set(ANCHOR_CLOCKS).issubset(clockset):
        return "PREVIOUS_OPENINGS_OR_1530_CLOSE_MISSING"
    am=[r for r in previous if r["label"][11:16]<"11:30"]
    pm=[r for r in previous if "12:30"<=r["label"][11:16]<"15:25"]
    # Do not grant native parity if the previous reference or opening grid
    # is absent. The original normalizer itself decides U from exact pairs.
    if not am or not pm:return "PREVIOUS_CONTINUOUS_SEGMENT_MISSING"
    if previous_continuous_source_pairs(previous)<MIN_PREVIOUS_CONSECUTIVE_PAIRS:
        return "PREVIOUS_CONSECUTIVE_PAIRS_BELOW_30"
    if len(current)<MIN_CURRENT_OBSERVED_BARS:
        return "CURRENT_TOO_FEW_OBSERVED_1M"
    return None


def technical_sparse_replay(previous,current,source_sha,modules):
    """Invoke both ORIGINAL normalizers and engines; missing ticks use None.

    Return aggregate counts only, never a trade, account value, market price,
    per-symbol candidate score, future High or label.
    """
    reason=precondition(previous,current)
    require(reason is None,"NO11_RC2_SPARSE_PRECONDITION:"+str(reason))
    m80,m120,Candidate,Independent,profile=modules
    earlier=[parent._frame_bar(r,source_sha) for r in previous]
    present=[parent._frame_bar(r,source_sha) for r in current]
    a=m80.generate(earlier,present)
    b=m120.regenerate(earlier,present)
    for key in ("U","P_ref","previous_return_pairs_N","previous_pair_ids",
                "previous_last_source","previous_last_source_time","coordinates"):
        require(a[key]==b[key],"NO11_RC2_SPARSE_M0_80_120_MISMATCH:"+key)
    pairs=a["previous_return_pairs_N"]
    require(type(pairs) is int and pairs>=MIN_PREVIOUS_CONSECUTIVE_PAIRS,
            "NO11_RC2_SPARSE_PREVIOUS_PAIRS_TOO_FEW")
    require(len(a["coordinates"])==len(present),
            "NO11_RC2_SPARSE_M0_COORDINATE_COUNT_INVALID")
    price_map={}
    for candle,coordinate in zip(current,a["coordinates"]):
        time=candle["label"][11:16]
        require(time in CLOCKS and time not in price_map,
                "NO11_RC2_SPARSE_SOURCE_CLOCK_INVALID")
        price_map[time]=coordinate

    one=Candidate(profile)
    two=Independent(profile)
    observed=Counter()
    counts=Counter()
    first=None
    for minute in SCHEDULE:
        clock=f"{minute//60:02d}:{minute%60:02d}"
        t=minute+1-540
        coord=price_map.get(clock)
        if coord is None:
            raw=None  # original gate's explicit missingness contract
            counts["nativeMissingTickCalls"]+=1
        else:
            bucket=("TERMINAL_AUCTION_MINUTE" if minute in (690,930)
                    else "OPENING_MIXED_MINUTE" if minute in (540,750)
                    else "CONTINUOUS")
            raw={k.lower():coord[k] for k in ("O","H","L","C")}
            raw.update({"t":t,"known_at":t,"source":SOURCE_TAG,
                        "auction":bucket})
            counts["observedOneMinuteInputs"]+=1
        left=one.step(t,raw,case_id="2026_SPARSE_ORIGINAL_RC2")
        right=two.step(t,raw,case_id="2026_SPARSE_ORIGINAL_RC2")
        require(all(left.get(field)==right.get(field) for field in COMPARE),
                "NO11_RC2_SPARSE_TWO_ENGINE_DISAGREEMENT:"+clock)
        counts["dualEngineMatchedClockCalls"]+=1
        if raw is None:
            require(left["numeric_status"]=="NOT_AVAILABLE" and
                    left["current_semantics_observed"] is False,
                    "NO11_RC2_SPARSE_GAP_FABRICATED_OBSERVATION")
        else:
            require(left["numeric_status"]=="ACCEPTED" and left["as_of"]==t,
                    "NO11_RC2_SPARSE_PRESENT_BAR_REJECTED")
            counts["nativeAcceptedOneMinuteInputs"]+=1
            if left["current_semantics_observed"] is True:
                require(left["observed_at"]==t and
                        left["basis"] in (
                            "OBSERVED_FRESH","OBSERVED_NEW_SEGMENT_ONLY"),
                        "NO11_RC2_SPARSE_OBSERVED_SEMANTICS_INVALID")
                counts["nativeObservedPrimaryTicks"]+=1
                observed[str(left["primary"])]+=1
                if first is None:first=clock
    require(counts["dualEngineMatchedClockCalls"]==len(SCHEDULE) and
            counts["nativeMissingTickCalls"]+
            counts["nativeAcceptedOneMinuteInputs"]==len(SCHEDULE),
            "NO11_RC2_SPARSE_GRID_ACCOUNTING_INVALID")
    full=(len(previous)==len(CLOCKS) and len(current)==len(CLOCKS))
    if full:
        # Full-grid results MUST match the earlier 327-bar native replay.
        old=parent.original_rc2_replay(previous,current,source_sha,modules)
        require(old["acceptedRows"]==counts["nativeAcceptedOneMinuteInputs"] and
                old["observedPrimaryRows"]==counts["nativeObservedPrimaryTicks"] and
                old["stateCounts"]==dict(sorted(observed.items())),
                "NO11_RC2_SPARSE_FULL_PAIR_REPLAY_PARITY_INVALID")
    return {
      "precedingOriginalM0Pairs":pairs,
      "input1mRows":len(current),
      "scheduled1mCalls":counts["dualEngineMatchedClockCalls"],
      "missingOneMinuteCalls":counts["nativeMissingTickCalls"],
      "actualBarNativeAccepts":counts["nativeAcceptedOneMinuteInputs"],
      "currentObservedStateTicks":counts["nativeObservedPrimaryTicks"],
      "stateCounts":dict(sorted(observed.items())),
      "firstTechnicalObservedStateClock":first,
      "originalFullPairParityAlsoRechecked":full,
      "trueBrokerFirstSeenCertified":False,
      "vendorOriginalNumericLexemesCertified":False,
      "nativeLiveState9Connected":False
    }


def inspect_complete_capture(args):
    require(args.max_symbols==CHECKED_SYMBOLS and
            args.max_replayed>=1 and args.max_replayed<=200 and
            args.previous==EARLIER_DAY and args.day==TODAY,
            "NO11_RC2_SPARSE_SCOPE_OR_REPLAY_LIMIT_CHANGED")
    # No future labels, no symbol sorting by observed State/outcome, no source
    # request. Reuse Stage2's pinned 4,327 source+SHA checkpoint verification.
    full,index,runs=parent.checked_inputs(args)
    baseline=safe_file(args.baseline_report,200000)
    require(sha(baseline)==BASELINE_REPORT_SHA,
            "NO11_RC2_SPARSE_950_BASELINE_SHA_MISMATCH")
    report=obj_from_bytes(baseline,args.baseline_report.name)
    require(report.get("schemaId")==
            "ARK_NO11_2026_RSS_NATIVE_RC2_TWO_ENGINE_TECHNICAL_REPLAY_V1" and
            report.get("status")=="RESEARCH_NATIVE_RC2_TECHNICAL_PARITY" and
            report.get("symbolsInScope")==CHECKED_SYMBOLS and
            report.get("previousSession")==EARLIER_DAY and
            report.get("currentSession")==TODAY and
            report.get("symbols",{}).get("technicalDualEnginePass")==4 and
            report.get("symbols",{}).get("fullPreviousAndCurrent327")==4 and
            report.get("actualBrokerFirstSeenTimeCertified") is False and
            report.get("productionReady") is False and
            report.get("orderTransmission") is False,
            "NO11_RC2_SPARSE_BASELINE_CONTRACT_INVALID")
    return full,index,runs


def main(args):
    full,index,runs=inspect_complete_capture(args)
    modules=parent.load_frozen(args.repo/parent.FROZEN_REL)
    seen=Counter()
    reasons=Counter()
    outcomes=Counter()
    states=Counter()
    groups=Counter()
    errors=Counter()
    first=None
    cap=args.max_replayed
    cumulativePairs=0
    run_ends=(20,1400,4327)
    for pos in range(args.max_symbols):
        run_i=next(i for i,end in enumerate(run_ends) if pos<end)
        local=pos-(0 if run_i==0 else run_ends[run_i-1])
        directory,entries=runs[run_i]
        row=entries[local]
        symbol=full[pos]
        fname=f"{local+1:05d}-{symbol.replace('.','_')}-1M.json"
        require(row.get("symbol")==symbol and
                row.get("file")==fname and
                row.get("sha256")==index[pos].get("sourceSha256"),
                "NO11_RC2_SPARSE_SOURCE_CHECKPOINT_DIVERGED")
        data=safe_file(directory/fname)
        require(sha(data)==row["sha256"],
                "NO11_RC2_SPARSE_ARCHIVE_SHA_CHANGED")
        source=obj_from_bytes(data,fname)
        status,n=check_source(source,symbol,local+1,"1M",fname)
        require(status==row["status"] and n==row["rows"] and
                status in (GOOD,EMPTY),
                "NO11_RC2_SPARSE_ARCHIVE_CONTRACT_INVALID")
        seen["sourceInspected"]+=1
        if status==EMPTY:
            reasons["UNAVAILABLE_ARCHIVE"]+=1
            continue
        previous,pcomplete=parent.session_rows(source["rows"],args.previous)
        current,ccomplete=parent.session_rows(source["rows"],args.day)
        # Require all labels on the exact 327 tick grid; source extra times
        # and invalid chronology must never be silently projected away.
        require(all(r["label"][11:16] in CLOCKS for r in previous+current),
                "NO11_RC2_SPARSE_OUTSIDE_SCHEDULE")
        if pcomplete and ccomplete:
            seen["fullyObservedSessionPairs"]+=1
        reason=precondition(previous,current)
        if reason:
            reasons[reason]+=1
            continue
        seen["meetsSourceAnchorAndCurrentFloor"]+=1
        if seen["replayedPairs"]>=cap:
            reasons["REPLAY_CAP_REACHED_NOT_SELECTED_FIRST_ELIGIBLE"]+=1
            continue
        # Before calling engines, original normalization may have too few
        # consecutive positive prior candles for stable quantitative state.
        try:
            evidence=technical_sparse_replay(previous,current,row["sha256"],modules)
        except (ValueError,RuntimeError,ArithmeticError,AssertionError,KeyError) as exc:
            msg=str(exc)
            if "PREVIOUS_PAIRS_TOO_FEW" in msg:
                reasons["PREVIOUS_CONSECUTIVE_PAIRS_BELOW_30"]+=1
            else:
                safe=(msg if re.fullmatch(
                   r"NO11_RC2_[A-Z0-9_]+(?::[A-Za-z0-9_]+)?",msg)
                   else "NO11_RC2_SPARSE_ORIGINAL_ENGINE_EXCEPTION")
                errors[safe]+=1
            continue
        seen["replayedPairs"]+=1
        if evidence["originalFullPairParityAlsoRechecked"]:
            seen["completePairCrosscheckPass"]+=1
        outcomes["nativeMissingTickCalls"]+=evidence["missingOneMinuteCalls"]
        outcomes["nativeAcceptedTicks"]+=evidence["actualBarNativeAccepts"]
        outcomes["nativeObservedStateTicks"]+=evidence["currentObservedStateTicks"]
        outcomes["totalOriginalDualEngineTickAgreements"]+=evidence["scheduled1mCalls"]
        cumulativePairs+=evidence["precedingOriginalM0Pairs"]
        groups["originalPreviousPairFloor30"]+=1
        states.update(evidence["stateCounts"])
        if first is None:first=evidence["firstTechnicalObservedStateClock"]
        if seen["replayedPairs"]%10==0:
            print("NO11_RC2_SPARSE_ENGINE_PROGRESS="+
                  str(seen["replayedPairs"])+"/"+str(cap),flush=True)
        if (pos+1)%100==0:
            print("NO11_RC2_SPARSE_SOURCE_PROGRESS="+
                  str(pos+1)+"/"+str(args.max_symbols),flush=True)
    require(seen["sourceInspected"]==CHECKED_SYMBOLS and
            seen["replayedPairs"]<=cap and
            outcomes["nativeMissingTickCalls"]+
            outcomes["nativeAcceptedTicks"]==
            outcomes["totalOriginalDualEngineTickAgreements"] and
            outcomes["totalOriginalDualEngineTickAgreements"]==
            seen["replayedPairs"]*len(SCHEDULE),
            "NO11_RC2_SPARSE_ACCOUNTING_INVALID")
    classification=("TECHNICAL_SPARSE_DUAL_ENGINE_DISAGREEMENT_BLOCKED"
                    if errors else
                    "TECHNICAL_SPARSE_DUAL_ENGINE_PASS_RESEARCH_ONLY"
                    if seen["replayedPairs"]>0 else
                    "NO_ELIGIBLE_SPARSE_PAIRS_UNDER_SOURCE_FLOORS")
    report={
      "schemaId":REPORT_SCHEMA,"status":classification,
      "previous":"2026-10-09","current":"2026-10-13",
      "inspectedOriginalFirstSymbols":CHECKED_SYMBOLS,
      "actualReplayedOriginalFirstEligibleCount":seen["replayedPairs"],
      "maxNativeRc2TechnicalReplays":cap,
      "sourceCoverageCounters":dict(sorted(seen.items())),
      "sourceExclusions":dict(sorted(reasons.items())),
      "researchTechnicalTickCounts":dict(sorted(outcomes.items())),
      "observedOriginalPrimaryStates":dict(sorted(states.items())),
      "technicalErrorCounts":dict(sorted(errors.items())),
      "firstObservedTechnicalClock":first,
      "cumulativePreviousM0ReturnPairs":cumulativePairs,
      "previousSessionAnchorClocksRequired":ANCHOR_CLOCKS,
      "previousM0ContiguousPairsMinimumResearchOnly":MIN_PREVIOUS_CONSECUTIVE_PAIRS,
      "currentObservedOneMinuteMinimumResearchOnly":MIN_CURRENT_OBSERVED_BARS,
      "baseline950ReportSha256":BASELINE_REPORT_SHA,
      "inputSourceIndexSha256":parent.SOURCE_INDEX_SHA256,
      "originalSourceAuditSha256":parent.AUDIT_SHA256,
      "frozenRC2GitBlobPins":parent.CHECKED_FROZEN_BLOBS,
      "missingTickSemantics":"ORIGINAL_RC2_STEP_NONE_NOT_FORWARD_FILL",
      "barTimeSemantics":"RSS_1M_START_LABEL_ASSUMED_NOT_VENDOR_CERTIFIED",
      "brokerKnownAtIsInferredNotObserved":True,
      "originalNativeRC2BothEnginesInvoked":seen["replayedPairs"]>0,
      "fullPairReproductionExtraPassCount":seen["completePairCrosscheckPass"],
      "stateLabelsEligibleForLiveSelectorOrEntry":False,
      "h235R0OnReal2026Candidate":False,
      "frozenCapitalExitLiveConnected":False,
      "futureObservedOutcomeUsedInModelInputs":False,
      "trainingPerformed":False,
      "originalFrozenFilesMutated":False,
      "productionReady":False,"orderTransmission":False
    }
    body=(json.dumps(report,sort_keys=True,indent=2,
                     ensure_ascii=False,allow_nan=False)+"\n").encode()
    digest=sha(body)
    path=args.output_dir/("no11-2026-rc2-sparse-research-"+digest[:16]+".json")
    parent.immutable(path,body)
    print("NO11_RC2_SPARSE_2026="+(
        "PASS_RESEARCH_ONLY" if seen["replayedPairs"]>0 and not errors else
        "BLOCKED" if errors else "NO_ELIGIBLE_INPUT"))
    print("NO11_RC2_SPARSE_OBSERVED_SYMBOLS="+str(seen["replayedPairs"]))
    print("NO11_RC2_SPARSE_ORIGINAL_DUAL_ENGINE_CLOCKS="+str(
        outcomes["totalOriginalDualEngineTickAgreements"]))
    print("NO11_RC2_SPARSE_REPORT="+str(path))
    print("NO11_RC2_ACTUAL_KNOWN_AT_CERTIFIED=False")
    print("NO11_NATIVE_SELECTOR_FIRST_ENTRY_CONNECTED=False")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")
    require(not errors,"NO11_RC2_SPARSE_FROZEN_ENGINE_SEMANTIC_MISMATCH")


def selftest():
    day=parent.SESSION_DAYS[-1]
    prev=parent.SESSION_DAYS[-2]
    def bar(d,m):
        price=100+((m-540)//20)
        return {"label":f"{d}T{m//60:02d}:{m%60:02d}:00+09:00",
                "open":price,"high":price+1,"low":price-1,
                "close":price,"volume":100}
    previous=[bar(prev,m) for m in SCHEDULE]
    current=[bar(day,m) for m in SCHEDULE]
    assert precondition(previous,current) is None
    assert precondition(previous[:-1],current)=="PREVIOUS_OPENINGS_OR_1530_CLOSE_MISSING"
    assert precondition(previous,current[:10])=="CURRENT_TOO_FEW_OBSERVED_1M"
    frozen=Path(__file__).resolve().parents[3]/parent.FROZEN_REL
    modules=parent.load_frozen(frozen)
    full=technical_sparse_replay(previous,current,"c"*64,modules)
    assert full["originalFullPairParityAlsoRechecked"] is True
    assert full["precedingOriginalM0Pairs"]==321
    assert full["scheduled1mCalls"]==327
    assert full["missingOneMinuteCalls"]==0
    sparse=[r for r in current if r["label"][11:16]
            not in ("09:31","10:45","12:45","14:11","15:30")]
    selected=technical_sparse_replay(previous,sparse,"c"*64,modules)
    assert selected["originalFullPairParityAlsoRechecked"] is False
    assert selected["missingOneMinuteCalls"]==5
    assert selected["actualBarNativeAccepts"]==322
    assert selected["scheduled1mCalls"]==327
    assert selected["currentObservedStateTicks"]<=322
    assert selected["trueBrokerFirstSeenCertified"] is False
    print("NO11_RC2_SPARSE_2026_OFFLINE_SELFTEST=PASS")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline-self-test",action="store_true")
    p.add_argument("--repo",type=Path)
    p.add_argument("--capture-root",type=Path)
    p.add_argument("--original-symbols",type=Path)
    p.add_argument("--source-index",type=Path)
    p.add_argument("--audit-report",type=Path)
    p.add_argument("--baseline-report",type=Path)
    p.add_argument("--output-dir",type=Path)
    p.add_argument("--previous",default=EARLIER_DAY)
    p.add_argument("--day",default=TODAY)
    p.add_argument("--max-symbols",type=int,default=CHECKED_SYMBOLS)
    p.add_argument("--max-replayed",type=int,default=40)
    a=p.parse_args()
    try:
        if a.offline_self_test:
            selftest()
        else:
            require(all((a.repo,a.capture_root,a.original_symbols,
                         a.source_index,a.audit_report,a.baseline_report,
                         a.output_dir)),
                    "NO11_RC2_SPARSE_REQUIRED_LOCAL_ARGUMENTS_MISSING")
            main(a)
    except Exception as e:
        msg=str(e)
        if not re.fullmatch(r"NO11_RC2_[A-Z0-9_]+(?::[A-Za-z0-9_]+)?",msg):
            msg="NO11_RC2_SPARSE_UNEXPECTED_INPUT_OR_RUNTIME"
        print("NO11_RC2_SPARSE_2026=BLOCKED:"+msg,file=sys.stderr)
        print("NO11_PRODUCTION_READY=False",file=sys.stderr)
        print("ORDER_TRANSMISSION=False",file=sys.stderr)
        sys.exit(2)
