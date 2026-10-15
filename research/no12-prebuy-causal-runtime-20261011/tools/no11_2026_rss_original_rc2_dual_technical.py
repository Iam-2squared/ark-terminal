#!/usr/bin/env python3
"""Run BOTH unchanged Frozen RC2 State9 engines on verified 2026 RSS 1M archives.

RESEARCH ONLY: real RssChart 1M data are SHA-verified, but exact vendor
decimal tokens, true known-at / first-seen times, and J-Quants parity are
UNKNOWN. A 1M label is assumed to mean bar START; knownAt=label+1m is an
offline technical hypothesis, not actual availability evidence.

No filler/interpolation, no model fitting, no live candidate, no broker/Excel,
no orders, no real-money use. Requires FULL 327-label preceding and current
cash sessions, so an absent bar is NOT silently copied or resampled.
"""
import argparse
from collections import Counter
from datetime import datetime,timedelta
from hashlib import sha1,sha256
import importlib
import json
from pathlib import Path
import re
import sys

from no11_rss_batch_resume_manifest import (
    check_source,load_symbols,obj_from_bytes,require,safe_file,sha,GOOD,EMPTY
)
from no11_rss_2026_source_replay_index import (
    AUDIT_SHA256,SESSION_DAYS,RUN_LIMITS,RUN_REQUESTED,RUN_END_SHA
)

sys.dont_write_bytecode=True

SOURCE_INDEX_SHA256="4828a387aca426b9692fafa2322aea5384da41a1b0be69b98ace7b74fd8b86e0"
FROZEN_REL="research/state9-structural-exit-v2-20261003/FROZEN_SOURCE"
CHECKED_FROZEN_BLOBS={
 "normalize80.py":"204dec355c0e905afaa6b6ce924ac14d20a98fa1",
 "normalize120.py":"63b59a121b5f9418c1b565e0b170f0517196cc40",
 "candidate/api.py":"e84ce756297c3ad03954dcdeb983c10218e283dd",
 "candidate/exact.py":"1fb33cb9236218b4f53b03e12076e8f00082b54f",
 "candidate/kernel.py":"c5f951180cb861b58d5fbca83611222f69a3fb3c",
 "independent/api.py":"f693b8eaf231d07b82e30321dbd6724acadc0261",
 "independent/exact.py":"0ad5925495306021a4af176d95eefa8c9ff56a73",
 "independent/kernel.py":"9d208d7d1089d1fe5d5eaf29cdc387e17d1db11d",
 "profile.json":"273e22bcdacef9541e4aee507939b66cc6a7d425"
}
SOURCE_TAG="RSS_CHART_VALUE2_RESEARCH_ONLY_NOT_JQUANTS_V2"
REPORT_SCHEMA="ARK_NO11_2026_RSS_NATIVE_RC2_TWO_ENGINE_TECHNICAL_REPLAY_V1"
RESEARCH_LABEL_ASSUMPTION="RSS_1M_LABEL_IS_BAR_START_AND_THEORETICAL_AVAILABLE_AT_LABEL_PLUS_ONE_MINUTE"
COMPARE=(
 "as_of","primary","basis","current_semantics_observed","observed_at",
 "context","leg_direction","activity","fast_flag",
 "fast_applicable_to_primary","numeric_status","rejection_reason",
 "direction_basis"
)
SCHEDULE=tuple(
 list(range(540,691)) + list(range(750,925)) + [930]
)
CLOCKS=tuple(
 f"{m//60:02d}:{m%60:02d}" for m in SCHEDULE
)
MAX_SYMBOLS=4327


def git_blob(data):
    clean=data.replace(b"\r\n",b"\n")
    return sha1(b"blob "+str(len(clean)).encode()+b"\0"+clean).hexdigest()


def load_frozen(frozen):
    require(frozen.is_dir() and not frozen.is_symlink(),
            "NO11_RC2_FROZEN_DIR_NOT_FOUND")
    for relative,expected in CHECKED_FROZEN_BLOBS.items():
        f=frozen/relative
        data=safe_file(f,200_000)
        require(git_blob(data)==expected,
                "NO11_RC2_FROZEN_MODULE_CHANGED:"+relative)
    sys.path.insert(0,str(frozen))
    norm80=importlib.import_module("normalize80")
    norm120=importlib.import_module("normalize120")
    candidate=importlib.import_module("candidate.api")
    independent=importlib.import_module("independent.api")
    profile=obj_from_bytes(safe_file(frozen/"profile.json",10000),"profile.json")
    return norm80,norm120,candidate.Engine,independent.Engine,profile


def session_rows(rows,day):
    found=[r for r in rows if r["label"].startswith(day+"T")]
    found.sort(key=lambda r:r["label"])
    got=tuple(r["label"][11:16] for r in found)
    # No gaps, no synthetic zero-volume rows and no forward filling.
    return found,got==CLOCKS


def previous_and_current(rows,previous,day):
    require(previous in SESSION_DAYS and day in SESSION_DAYS and
            SESSION_DAYS.index(day)==SESSION_DAYS.index(previous)+1,
            "NO11_RC2_SESSION_PAIR_NOT_ADJACENT")
    earlier,old_complete=session_rows(rows,previous)
    today,current_complete=session_rows(rows,day)
    return earlier,today,old_complete,current_complete


def _frame_bar(bar,source_sha):
    # Captured JSON floats were already rounded by Excel Value2. Do not claim
    # these string conversions reproduce the source provider's numeric tokens.
    out={
        "Date":bar["label"][:10],
        "Time":bar["label"][11:16],
        "O":str(bar["open"]),
        "H":str(bar["high"]),
        "L":str(bar["low"]),
        "C":str(bar["close"]),
        "_source":{
            "label":bar["label"],"sourceSha256":source_sha,
            "numericTokenProvenance":"EXCEL_VALUE2_JSON_FLOAT_NOT_ORIGINAL"
        }
    }
    return out


def original_rc2_replay(previous,day_rows,source_sha,modules):
    """Both ORIGINAL 80/120 normalizers and ORIGINAL RC2 engines.

    Only called on FULL 327-bar previous+current regular/auction sessions;
    actual historical receive time and live availability remain UNKNOWN.
    """
    require(len(previous)==len(CLOCKS) and len(day_rows)==len(CLOCKS),
            "NO11_RC2_FULL_SESSION_REQUIRED")
    norm80,norm120,Candidate,Independent,profile=modules
    prev=[_frame_bar(x,source_sha) for x in previous]
    current=[_frame_bar(x,source_sha) for x in day_rows]
    a=norm80.generate(prev,current)
    b=norm120.regenerate(prev,current)
    for key in ("U","P_ref","previous_return_pairs_N","previous_pair_ids",
                "previous_last_source","previous_last_source_time","coordinates"):
        require(a[key]==b[key],"NO11_RC2_NATIVE_M0_80_120_DIVERGED:"+key)
    require(a["previous_return_pairs_N"]==321 and
            len(a["coordinates"])==len(CLOCKS),
            "NO11_RC2_NATIVE_NORMALIZATION_NOT_FULL")

    candidate=Candidate(profile)
    independent=Independent(profile)
    observed=Counter()
    accepted=0
    first_observed=None
    for candle,coordinate in zip(day_rows,a["coordinates"]):
        start=datetime.fromisoformat(candle["label"])
        end=start+timedelta(minutes=1)
        t=end.hour*60+end.minute-540
        hhmm=start.strftime("%H:%M")
        bucket=(
            "TERMINAL_AUCTION_MINUTE" if hhmm in ("11:30","15:30") else
            "OPENING_MIXED_MINUTE" if hhmm in ("09:00","12:30") else
            "CONTINUOUS"
        )
        bar={k.lower():coordinate[k] for k in ("O","H","L","C")}
        bar.update({"t":t,"known_at":t,"source":SOURCE_TAG,"auction":bucket})
        # The known_at value above is theoretical bar end; it is NOT a real
        # receipt time. Reports must never call this a causal live proof.
        lhs=candidate.step(t,bar,case_id="RSS_2026_ORIGINAL_RC2_TECHNICAL")
        rhs=independent.step(t,bar,case_id="RSS_2026_ORIGINAL_RC2_TECHNICAL")
        require(all(lhs.get(k)==rhs.get(k) for k in COMPARE),
                "NO11_RC2_ORIGINAL_TWO_ENGINE_DISAGREE:"+hhmm)
        require(lhs.get("numeric_status")=="ACCEPTED" and
                lhs.get("as_of")==t,
                "NO11_RC2_ORIGINAL_TECHNICAL_ROW_REJECTED:"+hhmm)
        accepted+=1
        if lhs.get("current_semantics_observed") is True:
            require(lhs.get("basis") in
                    ("OBSERVED_FRESH","OBSERVED_NEW_SEGMENT_ONLY") and
                    lhs.get("observed_at")==t,
                    "NO11_RC2_ORIGINAL_CURRENT_STATE_NOT_OBSERVED")
            name=lhs.get("primary")
            observed[str(name)]+=1
            if first_observed is None:first_observed=hhmm
    require(accepted==len(CLOCKS),
            "NO11_RC2_ORIGINAL_TECHNICAL_COUNT_INVALID")
    return {
       "acceptedRows":accepted,
       "observedPrimaryRows":sum(observed.values()),
       "firstObservedClock":first_observed,
       "stateCounts":dict(sorted(observed.items())),
       "previousReturnPairs":a["previous_return_pairs_N"],
       "twoOriginalEnginesAgreed":True,
       "actualHistoricalKnownAtCertified":False,
       "originalVendorPriceDecimalTokensCertified":False,
       "jquantsSourceIdentityCertified":False,
       "nativeLiveState9Connected":False
    }


def source_path(root,audit,position):
    run_ends=(20,1400,4327)
    run_no=next(i for i,end in enumerate(run_ends) if position<end)
    start=0 if run_no==0 else run_ends[run_no-1]
    run=audit["runs"][run_no]
    directory=root/run["runDirectory"]
    require(directory.is_dir() and not directory.is_symlink(),
            "NO11_RC2_RUN_DIRECTORY_MISSING_OR_UNSAFE")
    local=position-start
    return directory,run_no,local


def checked_inputs(args):
    require(args.max_symbols>=1 and args.max_symbols<=MAX_SYMBOLS and
            args.previous in SESSION_DAYS and args.day in SESSION_DAYS and
            SESSION_DAYS.index(args.day)==SESSION_DAYS.index(args.previous)+1,
            "NO11_RC2_SCOPE_OR_SESSIONS_INVALID")
    root=args.capture_root.resolve(strict=True)
    require(root.is_dir() and not args.capture_root.is_symlink() and
            not root.is_symlink() and args.output_dir.is_dir() and
            not args.output_dir.is_symlink(),
            "NO11_RC2_PRIVATE_DIR_INVALID")
    original=safe_file(args.original_symbols,250000)
    full=original.decode("utf-8-sig").splitlines()
    require(len(full)==4327 and full[20:]==load_symbols(args.original_symbols),
            "NO11_RC2_MASTER_SYMBOL_LIST_CHANGED")
    audraw=safe_file(args.audit_report,200000)
    require(sha(audraw)==AUDIT_SHA256,
            "NO11_RC2_AUDIT_HASH_MISMATCH")
    audit=obj_from_bytes(audraw,args.audit_report.name)
    require(audit.get("schemaId")=="ARK_NO11_RSS_TRAINING_ALL_RUNS_SOURCE_AUDIT_V1" and
            audit.get("result")=="SOURCE_SHA256_AND_ROW_AUDIT_PASS_NOT_SUPERVISED_TRAINING" and
            audit.get("symbolsRequested")==4327 and
            audit.get("dataRows")==3705797 and
            audit.get("vendorFirstKnownAtCertified") is False and
            audit.get("nativeSelectorEntryFeatureTeacherRebuilt") is False and
            audit.get("productionReady") is False and
            audit.get("orderTransmission") is False and
            len(audit.get("runs",[]))==3,
            "NO11_RC2_SOURCE_AUDIT_CONTRACT_MISMATCH")
    indexbytes=safe_file(args.source_index,32*1024*1024)
    require(sha(indexbytes)==SOURCE_INDEX_SHA256,
            "NO11_RC2_SOURCE_INDEX_HASH_MISMATCH")
    index=[json.loads(line) for line in indexbytes.decode("utf-8").splitlines()]
    require(len(index)==4327 and
            all(index[i].get("symbol")==full[i] and
                index[i].get("productionReady") is False and
                index[i].get("orderTransmission") is False
                for i in range(4327)),
            "NO11_RC2_SOURCE_INDEX_INVALID")
    directories=[]
    for run_i,(count,requested,lastsha) in enumerate(zip(
            RUN_LIMITS,RUN_REQUESTED,RUN_END_SHA)):
        row=audit["runs"][run_i]
        require(row.get("completed")==count and
                row.get("lastProgressSha256")==lastsha and
                row.get("fullSourceSha256Verified") is True and
                row.get("fullSourceOHLCVVerified") is True,
                "NO11_RC2_AUDITED_CAPTURE_RUN_CHANGED")
        directory=root/row["runDirectory"]
        require(re.fullmatch(r"rss-[0-9a-f]{32}",directory.name) and
                directory.is_dir() and not directory.is_symlink(),
                "NO11_RC2_AUDITED_RUN_NOT_FOUND")
        progress=directory/f"progress-{count:05d}.json"
        data=safe_file(progress,2_000_000)
        require(sha(data)==lastsha,"NO11_RC2_PROGRESS_SHA_CHANGED")
        manifest=obj_from_bytes(data,progress.name)
        require(manifest.get("schemaId")==
                "ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1" and
                manifest.get("completed")==count and
                manifest.get("requested")==requested and
                len(manifest.get("files",[]))==count and
                manifest.get("productionReady") is False and
                manifest.get("orderTransmission") is False,
                "NO11_RC2_CAPTURE_MANIFEST_CHANGED")
        directories.append((directory,manifest["files"]))
    return full,index,directories


def immutable(path,data):
    require(path.parent.is_dir() and not path.parent.is_symlink(),
            "NO11_RC2_OUTPUT_ROOT_INVALID")
    if path.exists():
        require(path.is_file() and not path.is_symlink() and
                sha(safe_file(path,max(len(data)+1,200000)))==sha(data),
                "NO11_RC2_EXISTING_REPORT_CHANGED")
        return
    with path.open("xb") as f:f.write(data)


def main(args):
    full,index,runs=checked_inputs(args)
    frozen=args.repo/FROZEN_REL
    modules=load_frozen(frozen)
    observations=Counter()
    states=Counter()
    errors=Counter()
    first_observed=None
    completed=0
    run_boundary=(20,1400,4327)
    for i in range(args.max_symbols):
        run_i=next(n for n,end in enumerate(run_boundary) if i<end)
        local=i-(0 if run_i==0 else run_boundary[run_i-1])
        directory,ledger=runs[run_i]
        e=ledger[local]
        symbol=full[i]
        fname=f"{local+1:05d}-{symbol.replace('.','_')}-1M.json"
        require(e.get("symbol")==symbol and e.get("file")==fname and
                e.get("sha256")==index[i].get("sourceSha256"),
                "NO11_RC2_INDEX_CHECKPOINT_DISAGREE")
        data=safe_file(directory/fname)
        require(sha(data)==e["sha256"],"NO11_RC2_SOURCE_FILE_TAMPERED")
        src=obj_from_bytes(data,fname)
        status,number=check_source(src,symbol,local+1,"1M",fname)
        require(status==e.get("status") and
                number==e.get("rows") and status in (GOOD,EMPTY),
                "NO11_RC2_SOURCE_ARCHIVE_INVALID")
        observations["attemptedSymbols"]+=1
        if (i+1)%100==0:
            print("NO11_RC2_2026_SOURCE_CHECKED="+str(i+1)+"/"+
                  str(args.max_symbols)+"|TECHNICAL_DUAL_PASS="+
                  str(completed),flush=True)
        if status==EMPTY:
            observations["sourceUnavailable"]+=1
            continue
        old,cur,p_ok,c_ok=previous_and_current(
            src["rows"],args.previous,args.day)
        if not p_ok:
            observations["missingFullPreviousSession"]+=1
            continue
        if not c_ok:
            observations["missingFullCurrentSession"]+=1
            continue
        observations["fullPreviousAndCurrent327"]+=1
        try:
            evidence=original_rc2_replay(old,cur,e["sha256"],modules)
        except Exception as exc:
            # No row/price/private source emitted in the aggregate report.
            marker=str(exc)
            if re.fullmatch(r"NO11_RC2_[A-Z0-9_]+(?::[A-Za-z0-9_]+)?",marker):
                errors[marker]+=1
            else:
                errors["NO11_RC2_UNEXPECTED_ORIGINAL_ENGINE_FAILURE"]+=1
            continue
        completed+=1
        observations["technicalDualEnginePass"]+=1
        observations["frozenRC2TechnicalRowsAccepted"]+=evidence["acceptedRows"]
        observations["currentStateObservedRows"]+=evidence["observedPrimaryRows"]
        states.update(evidence["stateCounts"])
        if first_observed is None and evidence["firstObservedClock"] is not None:
            first_observed=evidence["firstObservedClock"]
    require(observations["attemptedSymbols"]==args.max_symbols and
            completed<=observations["fullPreviousAndCurrent327"],
            "NO11_RC2_INTERNAL_COUNTS_INCONSISTENT")
    result=("BLOCKED_FROZEN_DUAL_ENGINE_DISAGREEMENT_REVIEW" if errors
            else "RESEARCH_NATIVE_RC2_TECHNICAL_PARITY" if completed>0
            else "NO_COMPLETE_SESSION_PAIR_IN_SELECTED_SYMBOL_PREFIX")
    receipt={
      "schemaId":REPORT_SCHEMA,"status":result,
      "requestedScope":"FIRST_N_ORIGINAL_4327_CAPTURE_ORDER_ONLY",
      "symbolsInScope":args.max_symbols,
      "previousSession":args.previous,"currentSession":args.day,
      "inputSourceIndexSha256":SOURCE_INDEX_SHA256,
      "originalSourceAuditSha256":AUDIT_SHA256,
      "frozenRc2GitBlobs":CHECKED_FROZEN_BLOBS,
      "symbols":dict(sorted(observations.items())),
      "originalRc2StatesObserved":dict(sorted(states.items())),
      "technicalEngineFailures":dict(sorted(errors.items())),
      "firstTechnicalObservedPrimaryTime":first_observed,
      "originalSourceDateFormat":"RssChart_Excel_Value2_JSON_Not_JQuants",
      "asOfAssumption":RESEARCH_LABEL_ASSUMPTION,
      "bothOriginalEnginesActuallyInvoked":completed>0,
      "nativeState9From2026ArchiveTechnicalReplayPassed":completed>0 and not errors,
      "actualBrokerFirstSeenTimeCertified":False,
      "sourceBarLabelIntervalCertified":False,
      "vendorDecimalTokenCertified":False,
      "jquantsSourceIdentityCertified":False,
      "originalFrozenNativeRuntimeConnected":False,
      "originalFrozenSelectorConnected":False,
      "originalFrozenFirstEntryConnected":False,
      "originalH235R0ScoringConnected":False,
      "originalCapitalV5AndStructuralExitConnected":False,
      "modelFitPerformed":False,
      "productionReady":False,"orderTransmission":False
    }
    body=(json.dumps(receipt,sort_keys=True,indent=2,
                     ensure_ascii=False,allow_nan=False)+"\n").encode()
    hash_ = sha(body)
    out=args.output_dir/f"no11-2026-original-rc2-technical-{hash_[:16]}.json"
    immutable(out,body)
    print("NO11_RC2_2026_TECHNICAL="+
          ("PASS_RESEARCH_ONLY" if not errors and completed>0 else
           "NO_COMPLETE_PAIR_IN_FIRST_N" if not errors else "BLOCKED_TECHNICAL_MISMATCH"))
    print("NO11_RC2_FULL_PAIRS="+
          str(observations["fullPreviousAndCurrent327"]))
    print("NO11_RC2_DUAL_ENGINE_PASS_SYMBOLS="+str(completed))
    print("NO11_RC2_2026_REPORT="+str(out))
    print("NO11_RC2_BROKER_KNOWN_AT_CERTIFIED=False")
    print("NO11_RC2_NATIVE_LIVE_STATE9_CONNECTED=False")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")
    require(not errors,"NO11_RC2_ORIGINAL_DUAL_ENGINE_EXCEPTION_OR_MISMATCH")


def offline_test():
    require(len(CLOCKS)==327 and CLOCKS[0]=="09:00" and
            CLOCKS[-1]=="15:30" and
            "11:30" in CLOCKS and "12:30" in CLOCKS,
            "NO11_RC2_CASH_SESSION_SCHEDULE_INVALID")
    def bar(d,clock):
        return {
            "label":f"{d}T{clock}:00+09:00",
            "open":100,"high":101,"low":99,
            "close":100,"volume":100
        }
    p=SESSION_DAYS[-2]
    q=SESSION_DAYS[-1]
    all_rows=[bar(p,t) for t in CLOCKS]+[bar(q,t) for t in CLOCKS]
    old,new,a,b=previous_and_current(all_rows,p,q)
    require(a and b and len(old)==len(new)==327,
            "NO11_RC2_327_BAR_PAIR_REJECTED")
    gap=[x for x in all_rows if x["label"]!=f"{q}T09:30:00+09:00"]
    _,_,a,b=previous_and_current(gap,p,q)
    require(a and not b,"NO11_RC2_MISSING_BAR_NOT_REJECTED")
    frozen=Path(__file__).resolve().parents[3]/FROZEN_REL
    modules=load_frozen(frozen)
    # A reduced current prefix checks the two ORIGINAL engines without
    # falsely calling it a 327-bar source parity pass.
    prefix=[bar(q,t) for t in CLOCKS[:40]]
    p_rows=[_frame_bar(x,"f"*64) for x in old]
    c_rows=[_frame_bar(x,"f"*64) for x in prefix]
    m80,m120,Candidate,Independent,profile=modules
    lhs=m80.generate(p_rows,c_rows)
    rhs=m120.regenerate(p_rows,c_rows)
    require(lhs["coordinates"]==rhs["coordinates"] and
            lhs["previous_return_pairs_N"]==rhs["previous_return_pairs_N"]==321,
            "NO11_RC2_NORMALIZER_SMOKE_DIVERGED")
    a=Candidate(profile)
    b=Independent(profile)
    for k,(c,x) in enumerate(zip(prefix,lhs["coordinates"])):
        t=(int(c["label"][11:13])*60+int(c["label"][14:16])+1)-540
        raw={n.lower():x[n] for n in ("O","H","L","C")}
        raw.update({"t":t,"known_at":t,"source":SOURCE_TAG,
                    "auction":"OPENING_MIXED_MINUTE" if k==0 else "CONTINUOUS"})
        av=a.step(t,raw,case_id="OFFLINE_SYNTHETIC_PREFIX")
        bv=b.step(t,raw,case_id="OFFLINE_SYNTHETIC_PREFIX")
        require(av["numeric_status"]=="ACCEPTED" and
                all(av.get(key)==bv.get(key) for key in COMPARE),
                "NO11_RC2_ORIGINAL_ENGINES_PREFIX_DIVERGED")
    print("NO11_RC2_2026_SYNTHETIC_TECHNICAL_SELFTEST=PASS")
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
    p.add_argument("--output-dir",type=Path)
    p.add_argument("--previous",default="2026-10-09")
    p.add_argument("--day",default="2026-10-13")
    p.add_argument("--max-symbols",type=int,default=950)
    args=p.parse_args()
    try:
        if args.offline_self_test:
            offline_test()
        else:
            require(all((args.repo,args.capture_root,
                         args.original_symbols,args.source_index,
                         args.audit_report,args.output_dir)),
                    "NO11_RC2_REQUIRED_PRIVATE_ARGUMENT_MISSING")
            main(args)
    except Exception as e:
        print("NO11_RC2_2026_TECHNICAL=BLOCKED:"+str(e),file=sys.stderr)
        print("NO11_PRODUCTION_READY=False",file=sys.stderr)
        print("ORDER_TRANSMISSION=False",file=sys.stderr)
        sys.exit(2)
