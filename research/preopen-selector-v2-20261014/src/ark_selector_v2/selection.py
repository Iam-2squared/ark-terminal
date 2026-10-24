"""Conditional joint estimates, deterministic thresholding and sealed watchlists."""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Any
import math
import re
import numpy as np
from .calendar_phase import cutoff
from .calibration import probability_matrix
from .contracts import FLAGS, code_hash, digest, registry, forbid_outcomes, safe_flags
from .exact_math import V2Error

ITEM_FIELDS={"canonical_symbol","rss_symbol","market","rank","score","q","p3","p5",
             "g1","g2","first_reason","all_reason_codes","source_times","missing_map",
             "feature_hash",*FLAGS}
HEADER_FIELDS={"schema","candidate_id","session","cutoff_jst","generated_at","information_cutoff",
               "mode","historicalResearchOnly","intended_use","conditionalOnOutcomeKnown",
               "rankScoreIsExpectedReturn","universe_counts","selectedN","items","hashes",
               "status","reason",*FLAGS}
HASH_FIELDS={"code","config","schema","input","split","risk_model","opportunity_model","calibration","watchlist"}


def joint(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    a=probability_matrix(a,3);b=probability_matrix(b,6)
    if len(a)!=len(b):
        raise V2Error("JOINT_PROBABILITY_ROW_MISMATCH")
    q=a[:,0,None]*np.cumsum(b[:,::-1],axis=1)[:,::-1][:,1:]
    p3=a[:,1]+a[:,2];p5=a[:,2]
    tol=1e-12
    if (np.any(q<0) or np.any(q>1) or np.any(q[:,1:]-q[:,:-1]>tol)
            or np.any(q-a[:,0,None]>tol) or np.any(p5-p3>tol)
            or np.any(np.abs(a[:,0]+p3-1)>tol) or np.any(q[:,0]+p3-1>tol)):
        raise V2Error("JOINT_PROBABILITY_CONTAINMENT_FAILED")
    return q,p3,p5


def qualified(q: list[float], p3: float, p5: float) -> bool:
    if len(q)!=5 or any(not math.isfinite(x) or x<0 or x>1 for x in (*q,p3,p5)):
        raise V2Error("INVALID_SELECTION_PROBABILITY")
    if any(q[i]<q[i+1] for i in range(4)) or p5>p3 or q[0]+p3>1+1e-12:
        raise V2Error("INVALID_SELECTION_CONTAINMENT")
    # Structural probability tolerance is never used in decision comparisons.
    return q[0]>=.50 and p3<=.05 and p5<=.01


def rank_candidates(candidates: list[dict[str,Any]]) -> list[dict[str,Any]]:
    seen=set()
    good=[]
    for r in candidates:
        forbid_outcomes(r)
        code=r["canonical_symbol"]
        if code in seen or not re.fullmatch(r"[0-9A-Z]{4}",code):
            raise V2Error("DUPLICATE_OR_INVALID_CANONICAL_SYMBOL")
        seen.add(code)
        if r.get("g1")!="PASS" or r.get("g2")!="PASS":
            raise V2Error("MODEL_CANDIDATE_OUTSIDE_G2")
        if qualified(r["q"],r["p3"],r["p5"]):
            good.append({**r,"score":sum(r["q"])})
    ranked=sorted(good,key=lambda r:(-r["score"],-r["q"][4],r["canonical_symbol"]))
    return [{**r,"rank":i+1} for i,r in enumerate(ranked[:15])]


def watchlist_hash(watch: dict[str,Any]) -> str:
    value={**watch,"hashes":{k:v for k,v in watch["hashes"].items() if k!="watchlist"}}
    return digest(value)


def make_watchlist(session: date, candidates: list[dict[str,Any]], universe_counts: dict[str,int],
                   hashes: dict[str,str], *, mode: str = "SYNTHETIC",
                   empty_reason: str = "NO_PROBABILITY_QUALIFIED") -> dict[str,Any]:
    if mode!="SYNTHETIC":
        raise V2Error("MARKET_WATCHLIST_NOT_ADMITTED")
    selected=rank_candidates(candidates)
    # mode cannot be changed after publication; each candidate is synthetic-only.
    items=[]
    for r in selected:
        row={**r,**{f:False for f in FLAGS}}
        if set(row)!=ITEM_FIELDS:
            raise V2Error("WATCHLIST_ITEM_UNKNOWN_OR_MISSING_FIELD")
        items.append(row)
    actual_hashes={**hashes,"code":code_hash(),"schema":digest(registry())}
    if set(actual_hashes)!=HASH_FIELDS-{"watchlist"}:
        raise V2Error("WATCHLIST_HASH_BINDINGS_REQUIRED")
    watch: dict[str,Any]={"schema":"ARK_SELECTOR_V2_WATCHLIST_V1","candidate_id":"SYNTHETIC_V2_ENGINEERING",
           "session":session.isoformat(),"cutoff_jst":cutoff(session).isoformat(),
           "generated_at":datetime.now(timezone.utc).isoformat(),"information_cutoff":cutoff(session).isoformat(),
           "mode":mode,"historicalResearchOnly":True,"intended_use":"WATCHLIST_ONLY",
           "conditionalOnOutcomeKnown":True,"rankScoreIsExpectedReturn":False,
           "universe_counts":universe_counts,"selectedN":len(items),"items":items,
           "hashes":actual_hashes,"status":"WATCHLIST_FIXED" if items else "NO_CANDIDATE",
           "reason":None if items else empty_reason,**{f:False for f in FLAGS}}
    watch["hashes"]["watchlist"]=watchlist_hash(watch)
    validate_watchlist(watch)
    return watch


def validate_watchlist(watch: dict[str,Any]) -> None:
    if set(watch)!=HEADER_FIELDS:
        raise V2Error("WATCHLIST_UNKNOWN_OR_MISSING_FIELDS")
    forbid_outcomes(watch)
    safe_flags(watch)
    if (watch["schema"]!="ARK_SELECTOR_V2_WATCHLIST_V1" or watch["mode"] not in {"SYNTHETIC","AUTHORIZED_DEVELOPMENT"}
            or watch["historicalResearchOnly"] is not True or watch["intended_use"]!="WATCHLIST_ONLY"
            or watch["conditionalOnOutcomeKnown"] is not True or watch["rankScoreIsExpectedReturn"] is not False):
        raise V2Error("WATCHLIST_SEMANTIC_CONTRACT_MISMATCH")
    d=date.fromisoformat(watch["session"])
    if watch["cutoff_jst"]!=cutoff(d).isoformat() or watch["information_cutoff"]!=watch["cutoff_jst"]:
        raise V2Error("WATCHLIST_CUTOFF_MISMATCH")
    if datetime.fromisoformat(watch["generated_at"]).tzinfo is None:
        raise V2Error("GENERATION_TIMESTAMP_REQUIRED")
    counts=watch["universe_counts"]
    if set(counts)!={"master","price","g0","g1","g2","prob"} or any(type(v) is not int or v<0 for v in counts.values()):
        raise V2Error("INVALID_UNIVERSE_COUNTS")
    seq=[counts[k] for k in ("master","price","g0","g1","g2","prob")]
    if any(a<b for a,b in zip(seq[:-1],seq[1:])):
        raise V2Error("UNIVERSE_COUNTS_NOT_NESTED")
    n=watch["selectedN"]
    if type(n) is not int or n!=len(watch["items"]) or n>15 or n>counts["prob"]:
        raise V2Error("INVALID_SELECTED_COUNT")
    codes=[]
    for i,r in enumerate(watch["items"]):
        if set(r)!=ITEM_FIELDS:
            raise V2Error("WATCHLIST_ITEM_UNKNOWN_OR_MISSING_FIELD")
        safe_flags(r)
        if r["rank"]!=i+1 or r["score"]!=sum(r["q"]) or not qualified(r["q"],r["p3"],r["p5"]):
            raise V2Error("WATCHLIST_RANK_SCORE_OR_GATE_MISMATCH")
        if r["g1"]!="PASS" or r["g2"]!="PASS":
            raise V2Error("WATCHLIST_GATE_MISMATCH")
        if not re.fullmatch(r"[0-9A-Z]{4}",r["canonical_symbol"]) or not r["rss_symbol"]:
            raise V2Error("WATCHLIST_SYMBOL_MISMATCH")
        if not re.fullmatch(r"[0-9a-f]{64}",r["feature_hash"]):
            raise V2Error("WATCHLIST_FEATURE_HASH_MISSING")
        for name,value in r["source_times"].items():
            if name.endswith("_at"):
                stamp=datetime.fromisoformat(value)
                if stamp.tzinfo is None or (name!="captured_at" and stamp>cutoff(d)):
                    raise V2Error("WATCHLIST_SOURCE_AFTER_INFORMATION_CUTOFF")
        codes.append(r["canonical_symbol"])
    if len(set(codes))!=len(codes) or watch["items"]!=sorted(watch["items"],key=lambda r:(-r["score"],-r["q"][4],r["canonical_symbol"])):
        raise V2Error("WATCHLIST_DUPLICATE_OR_RANK_DRIFT")
    if set(watch["hashes"])!=HASH_FIELDS or any(not re.fullmatch(r"[0-9a-f]{64}",v) for v in watch["hashes"].values()):
        raise V2Error("INVALID_WATCHLIST_HASH")
    if watch["hashes"]["watchlist"]!=watchlist_hash(watch):
        raise V2Error("WATCHLIST_TAMPERED")
    if watch["hashes"]["code"]!=code_hash() or watch["hashes"]["schema"]!=digest(registry()):
        raise V2Error("WATCHLIST_CODE_OR_SCHEMA_DRIFT_NO_REFIT")
    if (n>0 and (watch["status"]!="WATCHLIST_FIXED" or watch["reason"] is not None)) or (n==0 and (watch["status"]!="NO_CANDIDATE" or watch["reason"] not in {"NO_G1_TREND","NO_G2_CAPACITY","NO_G2_DAMAGE_CLEAR","NO_PROBABILITY_QUALIFIED"})):
        raise V2Error("EMPTY_RECEIPT_IS_NOT_RUN_ERROR")
