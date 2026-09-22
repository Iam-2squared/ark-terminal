"""Phase57 State v2 frozen semantic adapter.

This module does not alter mechanical-v1 numeric market rules. It translates the
pinned mechanical reference into the frozen v2 status/value/reason contract and
keeps NOW and Future entry points separate.
"""
from __future__ import annotations
import hashlib, importlib.util, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"docs/phase57-five-minute-entry-state/mechanical-v1/reference.py"
sp=importlib.util.spec_from_file_location("_phase57_mechanical_v1",P)
m=importlib.util.module_from_spec(sp); sys.modules[sp.name]=m; sp.loader.exec_module(m)

VERSION="state-reference-v2.0"
H=10
STATUS={"DEFINED","INSUFFICIENT","NOT_EVALUATED","NOT_APPLICABLE"}
SAFETY={k:False for k in ("executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed",
"rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed",
"automaticPromotionAllowed","productionUpdateAllowed","transmitted")}
PRECEDENCE=("OBS_CURRENT_BAR_NOT_OBSERVED","OBS_SESSION_BOUNDARY","OBS_SHORT_SESSION_HISTORY",
"OBS_MISSING_SCHEDULED_BAR","OBS_LATEST5_INCOMPLETE","SCALE_PREVIOUS_CONTEXT_UNAVAILABLE",
"SCALE_PRICE_BASIS_UNVERIFIED","SCALE_INSUFFICIENT_BLOCKS","SCALE_ZERO",
"PIVOT_INSUFFICIENT_COUNT")

def primary(reasons):
    r=list(dict.fromkeys(reasons))
    return next((x for x in PRECEDENCE if x in r), r[0] if r else None)

def axis(status,value=None,reasons=(),**extra):
    assert status in STATUS
    rr=list(dict.fromkeys(reasons))
    if status=="DEFINED": rr=[]
    elif not rr: raise ValueError("NON_DEFINED_REQUIRES_REASON")
    z={"status":status,"value":value,"reasonCodes":rr,"primaryReason":primary(rr)}
    z.update(extra); return z

def obs_reasons(w):
    mp={"CURRENT_BAR_UNAVAILABLE":"OBS_CURRENT_BAR_NOT_OBSERVED",
        "SESSION_BOUNDARY":"OBS_SESSION_BOUNDARY","SHORT_SESSION_HISTORY":"OBS_SHORT_SESSION_HISTORY",
        "MISSING_SCHEDULED_BAR":"OBS_MISSING_SCHEDULED_BAR"}
    out=[mp[x] for x in w.get("reasons",[]) if x in mp]
    if w.get("status")!="COMPLETE": out.append("OBS_LATEST5_INCOMPLETE")
    return list(dict.fromkeys(out))

def scale_reason(s):
    return {"PREVIOUS_CONTEXT_UNAVAILABLE":"SCALE_PREVIOUS_CONTEXT_UNAVAILABLE",
      "PRICE_BASIS_UNVERIFIED":"SCALE_PRICE_BASIS_UNVERIFIED",
      "SCALE_INSUFFICIENT":"SCALE_INSUFFICIENT_BLOCKS","SCALE_ZERO":"SCALE_ZERO"}.get(s)

def _pivot_signature(ps):
    hs=[p for p in ps if p["kind"]=="HIGH"]; ls=[p for p in ps if p["kind"]=="LOW"]
    if len(hs)<2 or len(ls)<2: return None
    hd=hs[-1]["price"]-hs[-2]["price"]; ld=ls[-1]["price"]-ls[-2]["price"]
    rel=lambda d,p:"EQ" if d==0 else "UP" if d>0 else "DOWN"
    return {"highRelation":"H_"+rel(hd,"H"),"lowRelation":"L_"+rel(ld,"L"),
            "highDiffRaw":hd,"lowDiffRaw":ld}

def adapt(mech, scale):
    w=mech["observation"]; oreasons=obs_reasons(w)
    d=mech.get("descriptors")
    direction=axis("DEFINED",d["direction"],return5Pct=d["returnPct"]) if d else axis("NOT_EVALUATED",None,oreasons)
    sr=scale_reason(scale.get("status"))
    st=mech.get("state",{}); active=st.get("structure"); ps=st.get("pivots",[])
    if active:
        structure=axis("DEFINED",active["kind"],pivotN=len(ps))
    elif oreasons:
        structure=axis("NOT_EVALUATED",None,oreasons+([sr] if sr else []),pivotN=len(ps))
    elif sr:
        structure=axis("NOT_EVALUATED",None,[sr],pivotN=len(ps))
    elif len(ps)<4:
        structure=axis("INSUFFICIENT",None,["PIVOT_INSUFFICIENT_COUNT"],pivotN=len(ps))
    else:
        structure=axis("DEFINED","NONE",pivotN=len(ps))
    if oreasons or sr:
        phase=axis("NOT_EVALUATED",None,oreasons+([sr] if sr else []))
    else:
        phase=axis("DEFINED",st.get("phase",[]))
    sig=_pivot_signature(ps)
    if sig: piv=axis("DEFINED",sig)
    elif sr or oreasons: piv=axis("NOT_EVALUATED",None,oreasons+([sr] if sr else []))
    else: piv=axis("INSUFFICIENT",None,["PIVOT_INSUFFICIENT_COUNT"],pivotN=len(ps))
    return {"referenceVersion":VERSION,"checkpointAsOf":mech["asOf"],"direction":direction,
            "structure":structure,"phase":phase,"pivotSignature":piv,
            "observationQuality":{"latest5Complete":w.get("status")=="COMPLETE",
              "latest5ObservedK":len(w.get("observedEnds",[])),"scheduled5N":len(w.get("expectedEnds",[])),
              "missingFlags":oreasons,"availabilityEvidence":mech.get("availability")},
            "scale":{"scaleSpecId":"PREVIOUS_SESSION_COMPLETE_5M_TR_MEDIAN_V1",
              "scaleStatus":scale.get("status"),"scaleValue":scale.get("scale")},
            "attributes":mech.get("attributes"),"events":mech.get("levelEvents",[]),
            "safety":SAFETY.copy()}

def now_state_reference_v2(today, previous, calendar, daily, asof):
    # NOW receives only the caller's prefix; mechanical assemble hard-fails future bars.
    mech=m.assemble(today,previous,calendar,daily,asof)
    return adapt(mech,mech["contexts"]["scale"])

def future_resolution_v2(today_full, previous, calendar, daily, asof):
    # Separate evaluator path: bounded H=10 active minutes; never overwrites NOW.
    ds=list(calendar); i=ds.index(today_full.day); ep=ds[i-1] if i else None
    scale=m.scale_from_previous(previous,today_full.day,ep,today_full.security,today_full.basis) if previous else {"status":"PREVIOUS_CONTEXT_UNAVAILABLE","scale":None}
    mech=m.reference_at(today_full.bars,today_full.ends,asof,scale.get("scale"))
    out=adapt(mech,scale)
    fc=mech["futureConfirmation"]; flags=[]
    if fc["status"]=="RIGHT_CENSORED": flags.append("SESSION_CENSORED_BEFORE_H")
    if fc["status"]=="OBSERVATION_INSUFFICIENT": flags.append("OBSERVATION_CENSORED_BEFORE_H")
    out["futureResolution"]={"horizonActiveMinutes":H,"resolutionStatus":"CENSORED" if flags else "RESOLVED",
      "censorFlags":flags,"lateConfirmedPivotN":fc["lateConfirmedPivotN"],"cutoff":fc["cutoff"]}
    return out

def canonical_hash(x):
    return hashlib.sha256(m.canonical(x).encode()).hexdigest()
