#!/usr/bin/env python3
"""CORRECTED-MEASUREMENT-1 aggregate evaluator. Never fits a model."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

CONTRACT = "CORRECTED-MEASUREMENT-1"
KEYS = ["sessionDate", "decisionTimeJst"]
IDENTITY = ["sessionDate", "symbol", "decisionTimeJst"]
FEATURES = [
    "currentReturnPct", "momentum30Pct", "vwapDistancePct", "vwapSlope15Pct",
    "logCumulativeTurnover", "volumeAccelerationRatio", "trendEfficiency",
    "rangeExpansionPct", "timeOfDayFraction", "segmentStandard", "segmentGrowth",
    "liquidityLow", "liquidityHigh", "marketBreadthPositivePct", "sectorBreadthPositivePct",
]
STRINGS = IDENTITY + ["partition", "sourceGroup", "segment", "liquidityBucket",
                      "decisionPriceKind", "corrected30EndpointKind",
                      "firstCloseHitKind2", "firstCloseHitKind3", "firstCloseHitKind5"]
NUMERIC = FEATURES + [
    "decisionVolatilityPct", "decisionPrice", "decisionPriceValid", "referenceAgeMin",
    "legacyReferencePrice", "legacyReferenceAgeMin", "corrected30ReturnBps",
    "corrected30EndpointMinute", "corrected30EndpointAgeMin", "corrected30Evaluable",
    "mfe30Pct", "mae30Pct", "sessionMfePct", "sessionMaePct", "futureBarCount",
    "futureAuctionCount", "legacySixObservationReturnBps", "legacySixObservationElapsedMin",
    "finalAdditionalPct", "finalPreviousReturnPct", "finalPrevious5", "savedV1Score",
] + [f"{prefix}{level}{suffix}" for prefix, suffix in [
    ("highOpportunity", ""), ("closeOpportunity", ""), ("auctionCloseOpportunity", ""),
    ("timeToHigh", "Min"), ("timeToClose", "Min")]
     for level in [2, 3, 5]]

def number(value):
    return round(float(value), 10) if value is not None and np.isfinite(value) else None

def ratio(a, b, scale=1):
    return number(scale * a / b) if b else None

def distribution(values):
    raw = np.asarray(values, dtype=float); clean = raw[np.isfinite(raw)]
    result = {"n": int(len(clean)), "missing": int(len(raw)-len(clean))}
    if not len(clean):
        return {**result, **{x: None for x in ["min","mean","p1","p5","p10","p25","p50","p75","p90","p95","p99","max"]}}
    qs = np.quantile(clean, [.01,.05,.10,.25,.50,.75,.90,.95,.99])
    return {**result, "min": number(clean.min()), "mean": number(clean.mean()),
            **{f"p{q}": number(v) for q,v in zip([1,5,10,25,50,75,90,95,99],qs)},
            "max": number(clean.max())}

def time_distribution(values):
    s = pd.Series(values, dtype=float); clean = s[np.isfinite(s)]
    return {"distributionMinutes": distribution(s), "buckets": {
        "LE15": int((clean<=15).sum()), "16_TO30": int(((clean>15)&(clean<=30)).sum()),
        "31_TO60": int(((clean>30)&(clean<=60)).sum()), "61_TO120": int(((clean>60)&(clean<=120)).sum()),
        "GT120": int((clean>120).sum())}}

def mix(frame, field):
    return {str(k): {"n": int(v), "pct": ratio(int(v),len(frame),100)}
            for k,v in frame[field].value_counts(dropna=False).items()}

def prepare(frame):
    frame=frame.copy()
    for c in STRINGS:
        if c not in frame: raise ValueError(f"missing string column {c}")
        frame[c]=frame[c].fillna("NONE").astype(str)
    for c in NUMERIC:
        if c not in frame: raise ValueError(f"missing numeric column {c}")
        frame[c]=pd.to_numeric(frame[c],errors="coerce").replace([np.inf,-np.inf],np.nan)
    if frame.duplicated(IDENTITY).any(): raise ValueError("duplicate identity")
    if not np.isfinite(frame[FEATURES+["savedV1Score"]].to_numpy(float)).all(): raise ValueError("non-finite causal score/features")
    if (frame.referenceAgeMin.dropna()<0).any(): raise ValueError("future decision reference")
    valid=frame.decisionPriceValid.eq(1)
    if (valid & (frame.referenceAgeMin.gt(5)|frame.decisionPrice.le(0)|frame.decisionPrice.isna())).any(): raise ValueError("invalid fresh price")
    if (frame.mae30Pct.dropna()>1e-10).any() or (frame.sessionMaePct.dropna()>1e-10).any(): raise ValueError("positive true MAE")
    if (frame.mfe30Pct.dropna()<-1e-10).any() or (frame.sessionMfePct.dropna()<-1e-10).any(): raise ValueError("negative MFE")
    for level in [2,3,5]:
        for prefix in ["highOpportunity","closeOpportunity","auctionCloseOpportunity"]:
            if not frame.loc[valid,f"{prefix}{level}"].isin([0,1]).all(): raise ValueError("invalid opportunity flag")
    return frame

def select_top5(frame):
    ordered=frame[KEYS+["savedV1Score","symbol"]].sort_values(
        KEYS+["savedV1Score","symbol"],ascending=[True,True,False,True],kind="mergesort")
    return frame.loc[ordered.groupby(KEYS,sort=False).head(5).index]

def evaluator_valid(frame,prefix):
    if prefix=="highOpportunity": return frame.decisionPriceValid.eq(1)&frame.futureBarCount.gt(0)
    return frame.decisionPriceValid.eq(1)&(frame.futureBarCount.add(frame.futureAuctionCount).gt(0))

def opportunity_metrics(universe,selected,prefix,level):
    valid=evaluator_valid(universe,prefix); selected_valid=selected[evaluator_valid(selected,prefix)]
    flag=f"{prefix}{level}"; opportunities=universe[valid & universe[flag].eq(1)]
    nt=universe.groupby(KEYS,sort=False).size(); kt=nt.clip(upper=5)
    ot=opportunities.groupby(KEYS,sort=False).size().reindex(nt.index,fill_value=0)
    et=universe[valid].groupby(KEYS,sort=False).size().reindex(nt.index,fill_value=0)
    expected_hits=float((ot*kt/nt).sum()); expected_eval=float((et*kt/nt).sum())
    hits=int(selected_valid[flag].eq(1).sum()); total=len(opportunities)
    prevalence=ratio(total,int(valid.sum())); precision=ratio(hits,len(selected_valid))
    return {"opportunities":total,"selectedHits":hits,"precisionAt5Pct":ratio(hits,len(selected_valid),100),
            "hitsOverAllSelectedLowerBoundPct":ratio(hits,len(selected),100),"actualRecallPct":ratio(hits,total,100),
            "randomExpectedHits":number(expected_hits),"randomExpectedRecallPct":ratio(expected_hits,total,100),
            "recallLift":ratio(hits,expected_hits),"unconditionalPrevalencePct":ratio(total,int(valid.sum()),100),
            "precisionLift":ratio(precision,prevalence),"randomExpectedPrecisionPct":ratio(expected_hits,expected_eval,100)}

def freshness(frame):
    unavailable=frame[frame.decisionPriceValid.ne(1)]
    return {"eligibleRows":len(frame),"freshPriceRows":int(frame.decisionPriceValid.eq(1).sum()),
            "unavailableRows":len(unavailable),"unavailableRatePct":ratio(len(unavailable),len(frame),100),
            "priceAgeMinutes":distribution(frame.referenceAgeMin),"unavailableByMarket":mix(unavailable,"segment"),
            "unavailableByLiquidity":mix(unavailable,"liquidityBucket"),"unavailableByDecisionTime":mix(unavailable,"decisionTimeJst")}

def corrected30(frame):
    valid=frame.corrected30Evaluable.eq(1)
    return {"evaluableRows":int(valid.sum()),"coveragePct":ratio(int(valid.sum()),len(frame),100),
            "returnBps":distribution(frame.loc[valid,"corrected30ReturnBps"]),
            "endpointAgeMinutes":distribution(frame.loc[valid,"corrected30EndpointAgeMin"]),
            "endpointKind":mix(frame[valid],"corrected30EndpointKind"),
            "mfePct":distribution(frame.loc[valid,"mfe30Pct"]),"trueMaePct":distribution(frame.loc[valid,"mae30Pct"])}

def prevalence(frame):
    valid=evaluator_valid(frame,"highOpportunity"); close_valid=evaluator_valid(frame,"closeOpportunity"); early=valid & frame.currentReturnPct.lt(3)
    output={"highEvaluableRows":int(valid.sum()),"closeEvaluableRows":int(close_valid.sum()),"earlyRows":int(early.sum()),"byThreshold":{}}
    for level in [2,3,5]:
        hits=valid & frame[f"highOpportunity{level}"].eq(1); close=close_valid & frame[f"closeOpportunity{level}"].eq(1)
        output["byThreshold"][str(level)]={"highTouchCount":int(hits.sum()),"highTouchPrevalencePct":ratio(int(hits.sum()),int(valid.sum()),100),
            "closeConfirmedCount":int(close.sum()),"closeConfirmedPrevalencePct":ratio(int(close.sum()),int(close_valid.sum()),100),
            "earlyHighTouchCount":int((hits&early).sum()),"earlyShareOfHighTouchesPct":ratio(int((hits&early).sum()),int(hits.sum()),100),
            "earlyMix":{"market":mix(frame[hits&early],"segment"),"liquidity":mix(frame[hits&early],"liquidityBucket"),"decisionTime":mix(frame[hits&early],"decisionTimeJst")}}
    return output

def alignment(frame):
    valid=frame.corrected30Evaluable.eq(1)&frame.decisionPriceValid.eq(1)
    group=frame[valid].copy(); x=group.corrected30ReturnBps
    varying=len(group)>1 and x.nunique()>1
    out={"commonRows":len(group),"corrected30VsSessionMfePearson":number(x.corr(group.sessionMfePct)) if varying else None,
         "corrected30VsSessionMfeSpearman":number(x.corr(group.sessionMfePct,method="spearman")) if varying else None,"bands":{}}
    if len(group):
        rank=x.rank(method="average",pct=True)
        bands={"TOP1":rank.gt(.99),"TOP5":rank.gt(.95),"TOP10":rank.gt(.90),"TOP20":rank.gt(.80),"MIDDLE20_80":rank.ge(.20)&rank.le(.80),"BOTTOM20":rank.lt(.20)}
        for name,mask in bands.items():
            g=group[mask]
            out["bands"][name]={"n":len(g),"mean30Bps":number(g.corrected30ReturnBps.mean()),"median30Bps":number(g.corrected30ReturnBps.median()),
                "future3Pct":ratio(int(g.highOpportunity3.eq(1).sum()),len(g),100),"future5Pct":ratio(int(g.highOpportunity5.eq(1).sum()),len(g),100),
                "sessionMfePct":number(g.sessionMfePct.mean()),"sessionMaePct":number(g.sessionMaePct.mean())}
    return out

def top5_report(universe):
    selected=select_top5(universe); fresh=selected[selected.decisionPriceValid.eq(1)]; c30=selected[selected.corrected30Evaluable.eq(1)]
    session_means=c30.groupby("sessionDate").corrected30ReturnBps.mean()
    opportunities={}
    for kind,prefix in [("highTouch","highOpportunity"),("closeConfirmed","closeOpportunity")]:
        opportunities[kind]={str(level):opportunity_metrics(universe,selected,prefix,level) for level in [2,3,5]}
    return {"model":"CORRECTED_MEASUREMENT_RIDGE_SAVED_CD","selectedEvents":len(selected),"freshEvaluableSelected":len(fresh),
            "freshCoveragePct":ratio(len(fresh),len(selected),100),"corrected30EvaluableSelected":len(c30),
            "corrected30CoveragePct":ratio(len(c30),len(selected),100),"corrected30ReturnBps":distribution(c30.corrected30ReturnBps),
            "corrected30PositiveRatePct":ratio(int(c30.corrected30ReturnBps.gt(0).sum()),len(c30),100),
            "positiveSessions":int(session_means.gt(0).sum()),"sessionsWith30m":len(session_means),
            "mfe30Pct":distribution(c30.mfe30Pct),"mae30Pct":distribution(c30.mae30Pct),
            "sessionMfePct":distribution(fresh.sessionMfePct),"sessionMaePct":distribution(fresh.sessionMaePct),
            "opportunities":opportunities,
            "timeToHigh3":time_distribution(fresh.loc[fresh.highOpportunity3.eq(1),"timeToHigh3Min"]),
            "timeToHigh5":time_distribution(fresh.loc[fresh.highOpportunity5.eq(1),"timeToHigh5Min"]),
            "timeToClose3":time_distribution(fresh.loc[fresh.closeOpportunity3.eq(1),"timeToClose3Min"]),
            "timeToClose5":time_distribution(fresh.loc[fresh.closeOpportunity5.eq(1),"timeToClose5Min"]),
            "finalPrevious5ReferencePrecisionPct":ratio(int(selected.finalPrevious5.eq(1).sum()),len(selected),100),
            "legacySixObservationDiagnostic":distribution(selected.legacySixObservationReturnBps),"noReplacementForUnavailable":True}

def scope_report(frame):
    return {"populationRows":len(frame),"sessions":int(frame.sessionDate.nunique()),"freshness":freshness(frame),
            "correctedWallClock30m":corrected30(frame),"opportunityPrevalence":prevalence(frame),
            "targetAlignment":alignment(frame),"ridgeTop5":top5_report(frame)}

def load(root):
    manifest_path=root/"dataset-manifest.json"; payload=manifest_path.read_bytes(); manifest=json.loads(payload)
    if manifest.get("contractId")!=CONTRACT or manifest.get("providerRequestsThisRun")!=0 or manifest.get("fitCalls")!=0: raise ValueError("unsafe manifest")
    if manifest.get("validationOpened") is not False or manifest.get("oosOpened") is not False: raise ValueError("sealed data invariant")
    if manifest.get("featureUniverse")!=FEATURES: raise ValueError("feature universe changed")
    frames=[]
    for item in manifest["files"]:
        path=(root/item["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or path.suffix!=".tsv": raise ValueError("unsafe dataset path")
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item["sha256"]: raise ValueError("dataset hash mismatch")
        f=pd.read_csv(path,sep="\t",dtype={c:str for c in STRINGS})
        if len(f)!=item["rows"]: raise ValueError("row count mismatch")
        frames.append(f)
    manifest["_sha256"]=hashlib.sha256(payload).hexdigest()
    return prepare(pd.concat(frames,ignore_index=True)),manifest

def make_report(frame,manifest,contract_sha=None):
    scopes={"FULL_SAVED_DEVELOPMENT":frame,"AB_OUTSIDE_CD_FIT_DIAGNOSTIC":frame[frame.sourceGroup.isin(["L1","V2"])],
            "C_IN_FIT_DIAGNOSTIC":frame[frame.sourceGroup.eq("C")],"D_IN_FIT_DIAGNOSTIC":frame[frame.sourceGroup.eq("D")]}
    result={"schemaVersion":1,"status":"CORRECTED_MEASUREMENT_COMPLETE","contract":CONTRACT,
      "contractCommit":contract_sha or manifest.get("contractCommit"),"northStar":"DECISION_PRICE_TO_SAME_SESSION_FUTURE_5M_HIGH_GE3_PRIMARY_GE5_STRETCH",
      "modelProvenance":manifest["model"],"inputManifestSha256":manifest["_sha256"],"inputFiles":manifest["files"],
      "historicalLegacyV1Reference":{"measurement":"LEGACY_SIX_OBSERVATIONS_DIAGNOSTIC_ONLY","top5MeanBps":117.21,
                                     "directlyComparableToCorrectedWallClock30m":False},
      "dataAudit":{"sessionAudits":manifest["sessionAudits"],"availableSessions":int(frame.sessionDate.nunique())},
      "safety":{"providerRequests":0,"fitCalls":0,"validationOpened":False,"oosOpened":False,"v2Retested":False,
                "newModel":False,"newFeature":False,"newTarget":False,"topNOptimized":False,"tradingEnabled":False},
      "semantics":{"decisionPrice":"latest accepted Minute close available <= t, age <=5m","primary30m":"strict wall-clock t+30 endpoint",
                   "primaryOpportunity":"future continuous 5m High touch","secondaryOpportunity":"future 5m Close or terminal auction Close",
                   "mfe":"max(0,max future high / decision price - 1)","mae":"min(0,min future low / decision price - 1)"},
      "scopes":{name:scope_report(group) for name,group in scopes.items()},
      "perSession":{str(s):scope_report(g) for s,g in frame.groupby("sessionDate",sort=True)},
      "limitations":["Saved C+D Ridge is not original C-only v1; C/D are in-fit and A/B are earlier observed Development.",
                     "High touch is an evaluator event, not executable fill evidence.","Missing saved Minute observations fail closed and may induce coverage bias."],
      "stopBoundary":"REPORT_THEN_STOP_NO_NEW_RESEARCH"}
    core=json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)
    result["reportSha256"]=hashlib.sha256(core.encode()).hexdigest()
    return result

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--dataset-dir",required=True); parser.add_argument("--output",required=True); parser.add_argument("--contract-sha")
    args=parser.parse_args(); frame,manifest=load(Path(args.dataset_dir)); report=make_report(frame,manifest,args.contract_sha)
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":report["status"],"rows":len(frame),"reportSha256":report["reportSha256"],"output":str(output)}))

if __name__=="__main__": main()
