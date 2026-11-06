"""Post-R54 descriptive anatomy only: no fit, replay, policy, or provider call.

Run after the append-only ANATOMY_PRECOMMIT. Future prices are confined to
evaluator-only outputs and never joined into the as-of feature dictionary.
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import hashlib
import io
import json
import math
import statistics
import zipfile
from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import fisher_exact, mannwhitneyu

from scripts import phase57_exit_continuation_r52 as r52
from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_exit_execution_contract_v1 as clock
from scripts import phase57_mh_data_r54 as mh

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "docs/evidence/phase57-post-r54-winner-anatomy/ANATOMY_PRECOMMIT.json"
PROTOCOL = ROOT / "docs/evidence/phase57-exit-mh-r54/CYCLE2_PRECOMMIT.json"
SCHEMA = ROOT / "docs/evidence/phase57-exit-mh-r54/FEATURE_SCHEMA_LOCKED.json"
HORIZONS = (1, 5, 15, 30, 60, "EOD")
SIGNALS = ("CONTINUATION", "BREAKOUT", "COMPRESSION_EXPANSION",
           "HIGHER_LOW", "LOWER_WICK", "RECLAIM")
COHORTS = ("winnerGe5", "defensive")
SHORT = {v0.IM: "IM", v0.R1: "R1"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def number(value):
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def stats(values):
    x = np.asarray([v for v in values if v is not None and math.isfinite(float(v))],
                   dtype=np.float64)
    if not len(x):
        return {"knownN": 0, "median": None, "q25": None, "q75": None,
                "mean": None}
    return {"knownN": len(x), "median": float(np.median(x)),
            "q25": float(np.quantile(x, .25)), "q75": float(np.quantile(x, .75)),
            "mean": float(np.mean(x))}


def fmt_time(minute):
    return None if minute is None else f"{minute//60:02}:{minute%60:02}"


def active_distance(day, start, finish):
    schedule = clock.continuous_minutes(day)
    return sum(start <= minute < finish for minute in schedule)


def path_at_decision(day, entry_minute, now, path, entry_price):
    """Only complete observed entry-to-NOW OHLC may certify extrema."""
    minutes = [m for m in clock.continuous_minutes(day) if entry_minute <= m < now]
    last_close = mh._price(path.get(now - 1), 4)
    out = {"freshNowPriceJpy": last_close, "completePrefix": False,
           "mfeSoFarPct": None, "maeSoFarPct": None,
           "preSellHighJpy": None, "preSellLowJpy": None,
           "drawdownFromHighPct": None, "recoveryFromLowPct": None,
           "minutesSinceHigh": None, "minutesSinceLow": None,
           "slope5Pct": None, "slope15Pct": None, "vol15Pct": None,
           "upRun": None, "downRun": None}
    if last_close is not None and entry_price > 0:
        out["grossReturnPct"] = 100 * (last_close / entry_price - 1)
        out["r34NetAtNowPct"] = 100 * (last_close / entry_price - 1.0005)
    else:
        out["grossReturnPct"] = out["r34NetAtNowPct"] = None
    rows = [path.get(m) for m in minutes]
    valid = [row is not None and all(mh._price(row, j) is not None
                                   for j in (1, 2, 3, 4)) for row in rows]
    if minutes and all(valid) and last_close is not None:
        highs = [float(row[2]) for row in rows]
        lows = [float(row[3]) for row in rows]
        high, low = max(highs), min(lows)
        out.update(completePrefix=True, preSellHighJpy=high, preSellLowJpy=low,
                   mfeSoFarPct=100 * (high / entry_price - 1),
                   maeSoFarPct=100 * (low / entry_price - 1),
                   drawdownFromHighPct=100 * (high-last_close) / high,
                   recoveryFromLowPct=100 * (last_close/low-1),
                   minutesSinceHigh=active_distance(day, minutes[len(highs)-1-highs[::-1].index(high)], now),
                   minutesSinceLow=active_distance(day, minutes[len(lows)-1-lows[::-1].index(low)], now))
    schedule = clock.continuous_minutes(day)
    if now-1 in schedule:
        k = schedule.index(now-1)
        for window in (5, 15):
            selected = schedule[max(0, k-window+1):k+1]
            closes = [mh._price(path.get(m), 4) for m in selected]
            if len(closes) == window and all(v is not None for v in closes):
                out[f"slope{window}Pct"] = 100 * (closes[-1]/closes[0]-1)
                if window == 15:
                    returns = [100 * (b/a-1) for a,b in zip(closes,closes[1:])]
                    out["vol15Pct"] = statistics.pstdev(returns)
        # Runs end at NOW, and stop at the first missing earlier close.
        closes = [mh._price(path.get(schedule[j]), 4) for j in range(max(0,k-60),k+1)]
        if closes and closes[-1] is not None:
            up=down=0
            for a,b in zip(closes[-2::-1],closes[:0:-1]):
                if a is None or b is None:
                    break
                if b>a and down==0:up+=1
                elif b<a and up==0:down+=1
                else:break
            out["upRun"],out["downRun"]=up,down
    return out


def future_after_sell(day, sell_minute, sell_price, now_price, pre_high, path):
    """Evaluator-only exact OPENs and complete future high; no approximation."""
    schedule = clock.continuous_minutes(day)
    output={}
    if sell_minute not in schedule or sell_price is None:
        return {str(h): {"priceJpy": None, "deltaJpy": None, "deltaPct": None,
                         "recoveredNow": None, "newHigh": None,
                         "intervalComplete": False} for h in HORIZONS}, None
    k=schedule.index(sell_minute)
    for h in HORIZONS:
        target=930 if h=="EOD" else (schedule[k+h] if k+h<len(schedule) else None)
        endpoint=(None if target is None else
                  mh.endpoint_reference(day,925,path)[0] if target==930 else
                  mh._price(path.get(target),1))
        inner=[] if target is None else [m for m in schedule if sell_minute <= m < (925 if target==930 else target)]
        complete=target is not None and endpoint is not None and all(
            m in path and all(mh._price(path[m],j) is not None for j in (1,2,3,4))
            for m in inner)
        # Endpoint only is sufficient for exact price change; high needs every bar.
        high=(max([endpoint]+[float(path[m][2]) for m in inner]) if complete else None)
        output[str(h)]={"priceJpy": endpoint,
            "deltaJpy": None if endpoint is None else endpoint-sell_price,
            "deltaPct": None if endpoint is None else 100*(endpoint/sell_price-1),
            "recoveredNow": None if endpoint is None or now_price is None else endpoint>=now_price,
            "newHigh": None if high is None or pre_high is None else high>pre_high,
            "intervalComplete": bool(complete)}
    remaining=list(schedule[k:])
    auction=mh.endpoint_reference(day,925,path)[0]
    all_complete=auction is not None and all(m in path and all(
        mh._price(path[m],j) is not None for j in (1,2,3,4)) for m in remaining)
    whole=None
    if all_complete:
        high=max([auction]+[float(path[m][2]) for m in remaining])
        first=next((m for m in remaining if float(path[m][2])==high),930)
        whole={"additionalUpsidePct":100*(high/sell_price-1),
               "remainingHighJpy":high,
               "timeToRemainingHighActiveMinutes":active_distance(day,sell_minute,first),
               "reachedNewHigh":None if pre_high is None else high>pre_high}
    return output,whole


def load_inputs(folder, r45_zip, forecast_zip, replay_zip, audit_zip):
    p=json.loads(PRE.read_text());pins=p["sourcePins"]
    assert p["status"]=="FROZEN_BEFORE_POST_R54_DETAILED_PERFORMANCE_ANATOMY"
    assert not any(p["safety"].values()) and p["budget"]["newEstimatorFitsAllowed"]==0
    assert sha(PROTOCOL)==pins["r54ProtocolSha256"]
    assert sha(SCHEMA)==pins["lockedFeatureSchemaSha256"]
    assert sha(r52.RAW)==pins["rawPathSha256"]
    for name,path in (("forecastArtifactZipDigest",forecast_zip),
                      ("replayArtifactZipDigest",replay_zip),
                      ("r34AuditZipDigest",audit_zip)):
        if sha(path)!=pins[name]: raise ValueError("ARTIFACT_ZIP_DIGEST:"+name)
    with zipfile.ZipFile(r45_zip) as z:
        member=z.read("gen3/data/decision-features.npz")
    if hashlib.sha256(member).hexdigest()!=pins["r45FeatureSha256"]:
        raise ValueError("R45_FEATURE_MEMBER_DIGEST")
    ids_path=folder/"gen3/data/row-identities.jsonl.gz"
    if sha(ids_path)!=pins["r45RowIdentitySha256"]:
        raise ValueError("R45_ROW_IDENTITY")
    result=folder/"r54-result"
    if sha(result/"manifest.json")!=pins["resultManifestSha256"]:
        raise ValueError("RESULT_MANIFEST")
    manifest=json.loads((result/"manifest.json").read_text())
    if manifest["newModelFits"]!=176 or manifest["integratedInvocations"]!=44:
        raise ValueError("R54_BUDGET_DRIFT")
    for name,digest in manifest["filesSha256"].items():
        if sha(result/name)!=digest:raise ValueError("RESULT_FILE:"+name)
    training=folder/"r54-train"
    audit=json.loads((training/"oof-audit.json").read_text())
    if sha(training/"oof-forecasts.npz")!=pins["oofForecastSha256"] or \
       audit["predictionsSha256"]!=pins["oofForecastSha256"] or \
       audit["outputRowN"]!=656247:
        raise ValueError("OOF_DIGEST_OR_ROW_ID")
    for name,key in (("paired-layer-a-r34.json","r34CorrectedPairedSha256"),
                     ("selection-r34.json","r34CorrectedSelectionSha256")):
        if sha(folder/name)!=pins[key]:raise ValueError("R34_AUDIT_DIGEST:"+name)
    receipt=json.loads((folder/"gen3/data/data-receipt.json").read_text())
    with np.load(io.BytesIO(member),allow_pickle=False) as z:
        arrays={key:z[key] for key in ("numeric","categorical","pattern","fresh")}
    with np.load(training/"oof-forecasts.npz",allow_pickle=False) as z:
        forecasts={key:z[key] for key in z.files if key.startswith("FULL__")}
    with gzip.open(result/"controller-trace.json.gz","rt") as f: traces=json.load(f)
    with gzip.open(result/"standalone-all-entries.json.gz","rt") as f: standalone=json.load(f)
    paired=json.loads((folder/"paired-layer-a-r34.json").read_text())
    ledgers={}
    for arm in ("IM","R1"):
        ledgers[arm]={}
        for variant in ("R50_A_CONTROL","FULL_MH_WAIT15"):
            with gzip.open(result/f"{arm}_{variant}_ledger.json.gz","rt") as f:
                ledgers[arm][variant]=json.load(f)
    return p,receipt,arrays,forecasts,traces,standalone,paired,ledgers,ids_path


def write_csv(path,rows):
    if not rows:raise ValueError("EMPTY_TABLE:"+path.name)
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for row in rows:
            w.writerow({k:(json.dumps(v,ensure_ascii=False,sort_keys=True)
                             if isinstance(v,(list,dict)) else v) for k,v in row.items()})


def cohort_flags(trace, upside, candidate, baseline):
    model=(trace["exitKind"]=="MODEL_EXIT" and trace["exitPrice"] is not None)
    paired=(candidate is not None and baseline is not None)
    delta=None if not paired else float(Decimal(str(candidate))-Decimal(str(baseline)))
    winner=model and upside is not None and upside>=5
    defensive=model and upside is not None and upside<5 and delta is not None and delta>0
    retained=(trace["exitKind"]=="FORCED_TERMINAL" and trace["exitPrice"] is not None
              and upside is not None and upside>=5)
    return {"winnerGe5":winner,"winnerGe10":winner and upside>=10,
            "defensive":defensive,
            "defensiveBucket":None if not defensive else
                "below1" if upside<1 else "1to3" if upside<3 else "3to5",
            "retainedWinner":retained,
            "falseProtection":winner and delta is not None and delta<0,
            "missedDefense":upside is not None and upside<5 and delta is not None and delta<=0,
            "pairedDeltaJpy":delta,
            "unknownReason":("UPSIDE_UNKNOWN" if upside is None else
                "R54_FILL_UNKNOWN" if trace["exitPrice"] is None else
                "PAIRED_PNL_UNKNOWN" if not paired else None)}


def path_series(day, now, sell_minute, now_price, sell_price, path):
    schedule=clock.continuous_minutes(day)
    before={}; around={}
    if now-1 in schedule and now_price is not None:
        k=schedule.index(now-1)
        for t in range(-60,1):
            m=k+t
            if m<0:continue
            value=mh._price(path.get(schedule[m]),4)
            if value is not None:before[str(t)]=100*(value/now_price-1)
    if sell_minute in schedule and sell_price is not None:
        k=schedule.index(sell_minute)
        for t in range(-60,61):
            m=k+t
            if not 0<=m<len(schedule):continue
            value=(sell_price if t==0 else
                   mh._price(path.get(schedule[m]),4 if t<0 else 1))
            if value is not None:around[str(t)]=100*(value/sell_price-1)
    return before,around


def build_records(folder, receipt, arrays, forecasts, traces, standalone, paired,
                  ledgers, ids_path):
    schema=json.loads(SCHEMA.read_text())
    numeric_cols={name:i for i,name in enumerate(receipt["numericColumns"])}
    cat_cols={name:i for i,name in enumerate(receipt["categoricalColumns"])}
    decode={name:{int(code):word for word,code in info["sourceCodes"].items()}
            for name,info in schema["categorical"].items()}
    pattern_names=receipt["patternColumns"]
    if len(pattern_names)!=187 or arrays["pattern"].shape!=(656247,187):
        raise ValueError("PATTERN187_SOURCE")
    trace_map={(x["arm"],x["entryId"]):x for x in traces
               if x["variant"]=="FULL" and x["policy"]=="MH_WAIT15"}
    if len(trace_map)!=1614:
        raise ValueError("FULL_TRACE_ENTRY_CENSUS")
    needed={(a,e,t["decisionNow"]) for (a,e),t in trace_map.items()}
    index={}
    with gzip.open(ids_path,"rt") as f:
        for expected,line in enumerate(f):
            x=json.loads(line)
            if x["index"]!=expected:raise ValueError("ROW_ORDER")
            key=(x["arm"],x["entryId"],x["now"])
            if key in needed:
                if key in index:raise ValueError("DUPLICATE_ANCHOR")
                index[key]=expected
    if len(index)!=len(needed):
        raise ValueError("MISSING_ANCHOR_ROW")
    entries=r52.all_frozen_entries()
    raw=r52.projected_raw(entries)
    baseline={a:{x["entryId"]:x for x in standalone[a+"_R50_A_CONTROL"]}
              for a in ("IM","R1")}
    candidate={a:{x["entryId"]:x for x in standalone[a+"_FULL_MH_WAIT15"]}
               for a in ("IM","R1")}
    pairrows={a:{x["entryId"]:x for x in paired[a]["FULL_MH_WAIT15"]}
              for a in ("IM","R1")}
    class_control={a:r52.classify(ledgers[a]["R50_A_CONTROL"])
                   for a in ("IM","R1")}
    class_full={a:r52.classify(ledgers[a]["FULL_MH_WAIT15"])
                for a in ("IM","R1")}
    secondary=[];primary=[]
    for arm in (v0.IM,v0.R1):
        short=SHORT[arm]
        funded=ledgers[short]["R50_A_CONTROL"]["funded"]
        for eid in sorted(e for a,e in trace_map if a==arm):
            t=trace_map[arm,eid];br=baseline[short][eid];cr=candidate[short][eid]
            y=br["evaluatorOnlyPostEntryUpsidePct"]
            b=br["closedDiagnosticPnlJpy"];c=cr["closedDiagnosticPnlJpy"]
            flags=cohort_flags(t,y,c,b)
            secondary.append({"arm":short,"entryId":eid,"upsidePct":y,
                              "exitKind":t["exitKind"],**flags})
            if eid not in funded:continue
            pair=pairrows[short][eid]
            if y!=pair["evaluatorOnlyUpsidePct"]:
                raise ValueError("EVALUATOR_UPSIDE_DRIFT")
            flags=cohort_flags(t,y,pair["candidatePnlJpy"],pair["controlPnlJpy"])
            ix=index[arm,eid,t["decisionNow"]]
            e=entries[arm,eid]
            path=raw[e["opportunity"]]
            entry_price=float(e["effectiveEntryPrice"])
            pos=path_at_decision(e["session"],e["entryMinute"],t["decisionNow"],
                                 path,entry_price)
            features={name:number(arrays["numeric"][ix,numeric_cols[name]])
                      for name in schema["numeric"]}
            categoricals={name:decode[name].get(int(arrays["categorical"][ix,cat_cols[name]]),
                                                "UNKNOWN_SOURCE_CODE")
                          for name in schema["categorical"]}
            patterns={name:number(arrays["pattern"][ix,j])
                      for j,name in enumerate(pattern_names)}
            forecast={}
            for h in HORIZONS:
                j=mh.HORIZONS.index(h)
                forecast[str(h)]={}
                for family,heads in (("A",("mean","q10","q50","q90")),
                                     ("D",("mean","q10","q90")),
                                     ("HIGH",("q10","q50","q90")),
                                     ("LOW",("q10","q50","q90"))):
                    forecast[str(h)][family]={head:number(forecasts[f"FULL__{family}__{head}"][ix,j])
                                               for head in heads}
            short_h=[forecast[str(h)]["D"]["mean"] for h in (1,5)
                     if forecast[str(h)]["D"]["mean"] is not None]
            long_h=[forecast[str(h)]["D"] for h in (15,30,60,"EOD")]
            short_negative=bool(short_h) and all(x<0 for x in short_h)
            long_support=any(x["mean"] is not None and x["q10"] is not None
                             and x["mean"]>0 and x["q10"]>=0 for x in long_h)
            if t["exitKind"]=="MODEL_EXIT" and not short_negative:
                raise ValueError("SELL_FORECAST_CONTROLLER_DRIFT:"+eid)
            future,whole=future_after_sell(e["session"],t["exitMinute"],
                                            t["exitPrice"],pos["freshNowPriceJpy"],
                                            pos["preSellHighJpy"],path)
            before,around=path_series(e["session"],t["decisionNow"],t["exitMinute"],
                                      pos["freshNowPriceJpy"],t["exitPrice"],path)
            # Rank is taken from frozen checkpoint rows, not the selected SELL point.
            primary.append({"arm":short,"entryId":eid,"session":e["session"],
                "symbol":e["symbol"],"entryMinute":e["entryMinute"],
                "effectiveEntryPriceJpy":entry_price,
                "decisionNow":t["decisionNow"],"sellMinute":t["exitMinute"],
                "sellPriceJpy":t["exitPrice"],"exitKind":t["exitKind"],
                "sourceStatus":t["sourceStatus"],"reason":t["reason"],
                "reasonCounts":t["reasons"],"graceUsed":t["graceUsed"],
                "upsidePct":y,"controlQuantity":pair["quantity"],
                "candidatePnlJpy":pair["candidatePnlJpy"],
                "controlPnlJpy":pair["controlPnlJpy"],
                "controlContext":class_control[short][eid],
                "r54Context":class_full[short].get(eid),
                "fundedByR54":eid in class_full[short],
                "entryToSellActiveMinutes":active_distance(e["session"],e["entryMinute"],t["decisionNow"]),
                "decisionFresh":bool(arrays["fresh"][ix]),
                "state":categoricals["currentState.state"],
                "signalCurrent":{name:categoricals[f"signal.{name}.currentTriState"]
                                  for name in SIGNALS},
                "numeric":features,"categorical":categoricals,"patterns":patterns,
                "forecast":forecast,"shortNegative":short_negative,"longSupport":long_support,
                "path":pos,"future":future,"wholeFuture":whole,
                "preSellPath":before,"sellEventPath":around,**flags})
    if len(primary)!=111 or len(secondary)!=1614:
        raise ValueError("PRIMARY_OR_SECONDARY_CENSUS")
    # checkpoint rank: scan row identity, counting within Entry only; no future labels.
    wants={(v0.IM if row["arm"]=="IM" else v0.R1,row["entryId"],row["decisionNow"]):row
           for row in primary}
    ranks=collections.Counter()
    with gzip.open(ids_path,"rt") as f:
        for line in f:
            x=json.loads(line);key=(x["arm"],x["entryId"])
            ranks[key]+=1
            row=wants.get((key[0],key[1],x["now"]))
            if row is not None:
                row["checkpointRank"]=ranks[key]
                row["prefixBin"]="FIRST5" if ranks[key]<=5 else "NEXT10" if ranks[key]<=15 else "LATER"
                row["timeBin"]="EARLY" if x["now"]<630 else "MID" if x["now"]<810 else "LATE"
                row["entryTimeBin"]=("EARLY" if row["entryMinute"]<630 else
                                     "MID" if row["entryMinute"]<810 else "LATE")
    if any("checkpointRank" not in x for x in primary):
        raise ValueError("MISSING_CHECKPOINT_RANK")
    return primary,secondary,pattern_names


def compare_feature(rows, accessor, *, family, name):
    w=[r for r in rows if r["winnerGe5"]]
    d=[r for r in rows if r["defensive"]]
    x=[number(accessor(r)) for r in w]
    y=[number(accessor(r)) for r in d]
    x=[v for v in x if v is not None];y=[v for v in y if v is not None]
    sx,sy=stats(x),stats(y)
    kind="binary" if x and y and set(x+y)<={0.,1.} else "continuous"
    pooled=stats(x+y)
    iqr=(pooled["q75"]-pooled["q25"]) if pooled["knownN"] else None
    diff=None if not x or not y else sx["median"]-sy["median"]
    rate_diff=None if not x or not y else 100*(sum(v>0 for v in x)/len(x)-sum(v>0 for v in y)/len(y))
    effect=(None if diff is None or iqr is None or iqr==0 else abs(diff)/iqr)
    coverage=min(len(x)/len(w),len(y)/len(d)) if w and d else 0
    arm_signs=[]
    for arm in ("IM","R1"):
        xa=[number(accessor(r)) for r in w if r["arm"]==arm]
        ya=[number(accessor(r)) for r in d if r["arm"]==arm]
        xa=[v for v in xa if v is not None];ya=[v for v in ya if v is not None]
        if len(xa)>=5 and len(ya)>=5:
            arm_signs.append(np.sign(
                (sum(v>0 for v in xa)/len(xa)-sum(v>0 for v in ya)/len(ya)) if kind=="binary"
                else (float(np.median(xa))-float(np.median(ya)))))
    observed=np.sign(rate_diff if kind=="binary" and rate_diff is not None else diff or 0)
    agree=bool(arm_signs) and all(z==observed for z in arm_signs)
    no_opposite=all(z==observed or z==0 for z in arm_signs)
    magnitude=abs(rate_diff) if kind=="binary" and rate_diff is not None else effect
    grade="UNMEASURABLE"
    if min(len(x),len(y))>=5 and coverage>=.5:
        grade="NO EVIDENCE"
        if magnitude is not None:
            if magnitude >= (5 if kind=="binary" else .2):grade="WEAK"
            if min(len(x),len(y))>=10 and coverage>=.7 and no_opposite and \
               magnitude >= (15 if kind=="binary" else .5):grade="MODERATE"
            if min(len(x),len(y))>=20 and coverage>=.8 and agree and \
               magnitude >= (25 if kind=="binary" else 1):grade="STRONG"
    pvalue=None
    if len(x)>=2 and len(y)>=2:
        if kind=="binary":
            pvalue=float(fisher_exact([[sum(v>0 for v in x),sum(v<=0 for v in x)],
                                      [sum(v>0 for v in y),sum(v<=0 for v in y)]])[1])
        else:
            pvalue=float(mannwhitneyu(x,y,alternative="two-sided").pvalue)
    return {"family":family,"feature":name,"type":kind,
            "winnerN":len(w),"defensiveN":len(d),
            "winnerKnownN":len(x),"defensiveKnownN":len(y),
            "winnerMedian":sx["median"],"winnerQ25":sx["q25"],"winnerQ75":sx["q75"],
            "defensiveMedian":sy["median"],"defensiveQ25":sy["q25"],"defensiveQ75":sy["q75"],
            "winnerPositivePct":None if not x else 100*sum(v>0 for v in x)/len(x),
            "defensivePositivePct":None if not y else 100*sum(v>0 for v in y)/len(y),
            "medianDifference":diff,"positiveRateDifferencePp":rate_diff,
            "pooledIqr":iqr,"standardizedMedianDifference":effect,
            "knownCoverageMin":coverage,"supportedArmSigns":len(arm_signs),
            "armDirectionConsistent":agree,"grade":grade,"rawP":pvalue}


def bh_qvalues(rows):
    indexed=sorted(((x["rawP"],i) for i,x in enumerate(rows) if x["rawP"] is not None))
    m=len(indexed);q=1.
    for reverse_index in range(m-1,-1,-1):
        p,i=indexed[reverse_index]
        q=min(q,p*m/(reverse_index+1))
        rows[i]["bhQWithin187"]=min(1.,q)
    for row in rows:
        row.setdefault("bhQWithin187",None)


def count_table(rows,universe):
    out=[]
    for arm in ("IM","R1","COMBINED"):
        z=[x for x in rows if arm=="COMBINED" or x["arm"]==arm]
        out.append({"universe":universe,"arm":arm,"entries":len(z),
            "confirmedModelSell":sum(x["exitKind"]=="MODEL_EXIT" for x in z),
            "winnerGe10Subset":sum(x["winnerGe10"] for x in z),
            "winnerGe5Inclusive":sum(x["winnerGe5"] for x in z),
            "defensive3to5":sum(x["defensiveBucket"]=="3to5" for x in z),
            "defensive1to3":sum(x["defensiveBucket"]=="1to3" for x in z),
            "defensiveBelow1":sum(x["defensiveBucket"]=="below1" for x in z),
            "retainedWinner":sum(x["retainedWinner"] for x in z),
            "falseProtectionCrossFlag":sum(x["falseProtection"] for x in z),
            "missedDefenseCrossFlag":sum(x["missedDefense"] for x in z),
            "unknownUpside":sum(x["unknownReason"]=="UPSIDE_UNKNOWN" for x in z),
            "unknownFill":sum(x["unknownReason"]=="R54_FILL_UNKNOWN" for x in z),
            "unknownPaired":sum(x["unknownReason"]=="PAIRED_PNL_UNKNOWN" for x in z)})
    return out


def group_rows(primary,arm,cohort):
    return [x for x in primary if (arm=="COMBINED" or x["arm"]==arm) and x[cohort]]


def metric_row(group, name, getter):
    s=stats(getter(x) for x in group)
    return {"metric":name,"knownN":s["knownN"],"median":s["median"],
            "q25":s["q25"],"q75":s["q75"]}


def build_tables(primary,secondary,pattern_names,schema):
    tables={}
    tables["A_cohorts.csv"]=count_table(primary,"PRIMARY_ARCHIVED_R50_FUNDED")+count_table(
        secondary,"SECONDARY_ALL_ENTRIES_100_SHARE_DIAGNOSTIC")
    buckets=[]
    for arm in ("IM","R1","COMBINED"):
        z=[x for x in primary if arm=="COMBINED" or x["arm"]==arm]
        for bucket,include in (
                ("ge10",lambda x:x["upsidePct"] is not None and x["upsidePct"]>=10),
                ("ge5_inclusive",lambda x:x["upsidePct"] is not None and x["upsidePct"]>=5),
                ("5to10",lambda x:x["upsidePct"] is not None and 5<=x["upsidePct"]<10),
                ("3to5",lambda x:x["upsidePct"] is not None and 3<=x["upsidePct"]<5),
                ("1to3",lambda x:x["upsidePct"] is not None and 1<=x["upsidePct"]<3),
                ("below1",lambda x:x["upsidePct"] is not None and x["upsidePct"]<1)):
            items=[x for x in z if include(x)]
            paired=[x for x in items if x["pairedDeltaJpy"] is not None]
            cost=lambda x:x["effectiveEntryPriceJpy"]*x["controlQuantity"]
            model=[x for x in items if x["exitKind"]=="MODEL_EXIT"]
            gap=stats(x["upsidePct"]-100*(x["sellPriceJpy"]/
                      x["effectiveEntryPriceJpy"]-1) for x in model)
            buckets.append({"arm":arm,"upsideBucket":bucket,"N":len(items),
                "pairedKnownN":len(paired),"confirmedModelSellN":len(model),
                "pairedImprovedN":sum(x["pairedDeltaJpy"]>0 for x in paired),
                "pairedUnchangedN":sum(x["pairedDeltaJpy"]==0 for x in paired),
                "pairedWorsenedN":sum(x["pairedDeltaJpy"]<0 for x in paired),
                "controlMeanNetPct":None if not paired else sum(
                    100*float(x["controlPnlJpy"])/cost(x) for x in paired)/len(paired),
                "r54MeanNetPct":None if not paired else sum(
                    100*float(x["candidatePnlJpy"])/cost(x) for x in paired)/len(paired),
                "controlPnlJpy":sum(Decimal(str(x["controlPnlJpy"])) for x in paired),
                "r54PnlJpy":sum(Decimal(str(x["candidatePnlJpy"])) for x in paired),
                "deltaPnlJpy":sum(Decimal(str(x["pairedDeltaJpy"])) for x in paired),
                "fullPathPeakMinusSellPctMedian":gap["median"],
                "peakGapKnownN":gap["knownN"],
                "peakGapMeaning":"EVALUATOR_ONLY_FULL_POST_ENTRY_HIGH_NOT_CONFIRMED_POST_SELL_RESIDUAL"})
    tables["A_upside_buckets.csv"]=buckets
    timing=[];recovery=[];forecast=[];whole=[]
    mechanism=[]
    getters={
        "entryToSellActiveMinutes":lambda x:x["entryToSellActiveMinutes"],
        "r34NetAtNowPct":lambda x:x["path"]["r34NetAtNowPct"],
        "completeMfeSoFarPct":lambda x:x["path"]["mfeSoFarPct"],
        "completeMaeSoFarPct":lambda x:x["path"]["maeSoFarPct"],
        "drawdownFromHighPct":lambda x:x["path"]["drawdownFromHighPct"],
        "recoveryFromLowPct":lambda x:x["path"]["recoveryFromLowPct"],
        "minutesSinceHigh":lambda x:x["path"]["minutesSinceHigh"],
        "slope5Pct":lambda x:x["path"]["slope5Pct"],
        "slope15Pct":lambda x:x["path"]["slope15Pct"],
        "vol15Pct":lambda x:x["path"]["vol15Pct"],
        "controlPairedPnlJpy":lambda x:number(x["controlPnlJpy"]),
        "r54PairedPnlJpy":lambda x:number(x["candidatePnlJpy"]),
        "pairedPnlDeltaJpy":lambda x:x["pairedDeltaJpy"],
    }
    for arm in ("IM","R1","COMBINED"):
        for cohort in COHORTS:
            z=group_rows(primary,arm,cohort)
            mechanism.append({"arm":arm,"cohort":cohort,"N":len(z),
                "shortNegativeN":sum(x["shortNegative"] for x in z),
                "longSupportAtSellN":sum(x["longSupport"] for x in z),
                "graceUsedN":sum(x["graceUsed"] for x in z),
                "confirmedPersistentShortSellN":sum(
                    x["reason"]=="PERSISTENT_SHORT_DISADVANTAGE" for x in z),
                "priorNegativeConfirmationWaitN":sum(
                    x["reasonCounts"].get("NEGATIVE_CONFIRMATION_WAIT",0)>0 for x in z),
                "priorDataUnavailableN":sum(
                    x["reasonCounts"].get("DATA_UNAVAILABLE",0)>0 for x in z),
                "priorShortNotNegativeN":sum(
                    x["reasonCounts"].get("SHORT_NOT_NEGATIVE",0)>0 for x in z)})
            for name,getter in getters.items():
                timing.append({"arm":arm,"cohort":cohort,"cohortN":len(z),
                               **metric_row(z,name,getter)})
            comp=[x for x in z if x["wholeFuture"] is not None]
            whole.append({"arm":arm,"cohort":cohort,"cohortN":len(z),
                "completeRemainingN":len(comp),
                "additionalUpsidePctMedian":stats(x["wholeFuture"]["additionalUpsidePct"]
                                                    for x in comp)["median"],
                "timeToRemainingHighActiveMinutesMedian":stats(
                    x["wholeFuture"]["timeToRemainingHighActiveMinutes"] for x in comp)["median"],
                "additionalUpsideGe5KnownN":len(comp),
                "additionalUpsideGe5N":sum(x["wholeFuture"]["additionalUpsidePct"]>=5 for x in comp)})
            for h in HORIZONS:
                key=str(h);valid=[x for x in z if x["future"][key]["deltaPct"] is not None]
                rec=[x for x in z if x["future"][key]["recoveredNow"] is not None]
                new=[x for x in z if x["future"][key]["newHigh"] is not None]
                delta=stats(x["future"][key]["deltaPct"] for x in z)
                jpy=stats(x["future"][key]["deltaJpy"] for x in z)
                recovery.append({"arm":arm,"cohort":cohort,"horizon":key,"cohortN":len(z),
                    "exactPriceKnownN":len(valid),"deltaPctMedian":delta["median"],
                    "deltaPctQ25":delta["q25"],"deltaPctQ75":delta["q75"],
                    "deltaJpyMedian":jpy["median"],
                    "recoveredToPreSellNowKnownN":len(rec),
                    "recoveredToPreSellNowN":sum(x["future"][key]["recoveredNow"] for x in rec),
                    "newHighCompleteIntervalKnownN":len(new),
                    "newHighCompleteIntervalN":sum(x["future"][key]["newHigh"] for x in new)})
                for family,heads in (("A",("mean","q10","q50","q90")),
                                     ("D",("mean","q10","q90")),
                                     ("HIGH",("q10","q50","q90")),
                                     ("LOW",("q10","q50","q90"))):
                    for head in heads:
                        forecast.append({"arm":arm,"cohort":cohort,"horizon":key,
                            "family":family,"head":head,"cohortN":len(z),
                            **{k:v for k,v in stats(x["forecast"][key][family][head]
                                         for x in z).items()}})
    tables["B_sell_timing.csv"]=timing
    tables["B_sell_mechanism.csv"]=mechanism
    tables["E_forecast_at_sell.csv"]=forecast
    tables["F_recovery.csv"]=recovery
    tables["F_whole_remaining_path.csv"]=whole
    compare=[x for x in primary if x["winnerGe5"] or x["defensive"]]
    path_fields=("r34NetAtNowPct","mfeSoFarPct","maeSoFarPct",
                 "drawdownFromHighPct","recoveryFromLowPct","minutesSinceHigh",
                 "minutesSinceLow","slope5Pct","slope15Pct","vol15Pct","upRun","downRun")
    feature_rows=[compare_feature(compare,lambda r,k=k:r["path"].get(k),family="PATH",name=k)
                  for k in path_fields]
    feature_rows += [compare_feature(compare,lambda r,k=k:r["numeric"].get(k),
                     family="R54_NUMERIC",name=k) for k in schema["numeric"]]
    state_signal=[]
    state_codes=schema["categorical"]["currentState.state"]["sourceCodes"]
    for state in state_codes:
        r=compare_feature(compare,lambda x,s=state:float(x["state"]==s),
                          family="STATE",name=state)
        state_signal.append(r);feature_rows.append(r)
    for signal in SIGNALS:
        for category in ("TRUE","FALSE","UNKNOWN"):
            r=compare_feature(compare,lambda x,n=signal,c=category:
                              float(x["signalCurrent"][n]==c),
                              family="SIGNAL",name=signal+"/"+category)
            state_signal.append(r);feature_rows.append(r)
    tables["C_state_signals.csv"]=state_signal
    transition=[]
    for family,column in (("ENTRY_STATE","entryState.state"),
                          ("ENTRY_TO_CURRENT","entryToCurrentState")):
        for value in schema["categorical"][column]["sourceCodes"]:
            transition.append(compare_feature(compare,
                lambda x,k=column,v=value:float(x["categorical"][k]==v),
                family=family,name=value))
    tables["C_state_transition.csv"]=transition
    patterns=[]
    for name in pattern_names:
        r=compare_feature(compare,lambda x,n=name:x["patterns"][n],
                          family="PATTERN187",name=name)
        patterns.append(r)
    bh_qvalues(patterns)
    tables["D_pattern187.csv"]=patterns
    tables["C_all_asof_features.csv"]=feature_rows
    fcompare=[]
    for family,heads in (("D",("mean","q10","q90")),
                         ("A",("mean","q10","q90")),
                         ("HIGH",("q10","q50","q90")),
                         ("LOW",("q10","q50","q90"))):
        for h in HORIZONS:
            for head in heads:
                fcompare.append(compare_feature(compare,
                    lambda x,f=family,j=str(h),p=head:x["forecast"][j][f][p],
                    family=family,name=f"h{h}/{head}"))
    for family,head,near,far in (("D","mean",1,15),("D","mean",5,60),
                                 ("D","mean",1,"EOD"),("A","mean",1,"EOD"),
                                 ("HIGH","q50",1,"EOD"),("LOW","q50",1,"EOD")):
        fcompare.append(compare_feature(compare,
            lambda x,f=family,p=head,a=str(near),b=str(far):
                None if x["forecast"][b][f][p] is None or
                        x["forecast"][a][f][p] is None else
                x["forecast"][b][f][p]-x["forecast"][a][f][p],
            family="HORIZON_SHAPE",name=f"{family}/{head}/h{far}-h{near}"))
    for h in HORIZONS:
        fcompare.append(compare_feature(compare,
            lambda x,j=str(h):None if x["forecast"][j]["A"]["mean"] is None
                    or x["forecast"][j]["D"]["mean"] is None else
                x["forecast"][j]["A"]["mean"]-x["forecast"][j]["D"]["mean"],
            family="FORECAST_DISAGREEMENT",name=f"h{h}/Amean-Dmean"))
    tables["E_forecast_contrasts.csv"]=fcompare
    strata=[]
    for attr in ("arm","session","state","timeBin","entryTimeBin",
                 "prefixBin","controlContext","r54Context"):
        values=sorted({str(x.get(attr)) for x in primary})
        for value in values:
            z=[x for x in primary if str(x.get(attr))==value]
            strata.append({"stratum":attr,"value":value,"N":len(z),
                           "winnerGe5":sum(x["winnerGe5"] for x in z),
                           "defensive":sum(x["defensive"] for x in z),
                           "winnerGe10Subset":sum(x["winnerGe10"] for x in z)})
    tables["A_entry_context_strata.csv"]=strata
    path_rows=[]
    for arm in ("IM","R1","COMBINED"):
        for cohort in COHORTS:
            z=group_rows(primary,arm,cohort)
            for kind,lo,hi in (("preSell",-60,0),("sellEvent",-60,60)):
                field="preSellPath" if kind=="preSell" else "sellEventPath"
                for t in range(lo,hi+1):
                    s=stats(x[field].get(str(t)) for x in z)
                    path_rows.append({"arm":arm,"cohort":cohort,"path":kind,
                        "activeMinuteFromAnchor":t,"cohortN":len(z),**s})
    tables["B_event_paths.csv"]=path_rows
    return tables


def charts(primary,tables,out):
    out.mkdir(parents=True)
    plt.rcParams.update({"font.size":9,"svg.fonttype":"none","axes.grid":True,
                         "grid.alpha":.2,"figure.facecolor":"white"})
    colors={"winnerGe5":"#b84a62","defensive":"#247a76"}
    labels={"winnerGe5":"Winner ≥5%","defensive":"Useful defense <5%"}
    saved=[]
    def save(fig,name):
        fig.tight_layout()
        fig.savefig(out/name,format="svg",bbox_inches="tight")
        plt.close(fig);saved.append(name)

    path=tables["B_event_paths.csv"]
    for kind,name,title in (("preSell","01_pre_sell_normalized.svg",
                             "Pre-SELL observed close / decision NOW close"),
                            ("sellEvent","02_sell_zero_event_time.svg",
                             "SELL fill=0: observed close before, exact OPEN after")):
        fig,ax=plt.subplots(figsize=(9,4.2))
        for c in COHORTS:
            z=[r for r in path if r["arm"]=="COMBINED" and r["cohort"]==c
               and r["path"]==kind]
            xs=[r["activeMinuteFromAnchor"] for r in z]
            y=[r["median"] if r["median"] is not None else np.nan for r in z]
            lo=[r["q25"] if r["q25"] is not None else np.nan for r in z]
            hi=[r["q75"] if r["q75"] is not None else np.nan for r in z]
            ax.plot(xs,y,color=colors[c],label=labels[c]+f" (N={z[0]['cohortN']})")
            ax.fill_between(xs,lo,hi,color=colors[c],alpha=.12)
        ax.axvline(0,color="black",alpha=.4,linestyle="--")
        ax.axhline(0,color="black",alpha=.4,linewidth=.7)
        ax.set(title=title,xlabel="Scheduled active minutes from anchor",
               ylabel="Price change (%)")
        ax.legend(loc="best",fontsize=8)
        ax.text(.01,-.25,"Pointwise observed N varies; missing bars are never filled. Post-SELL is evaluator-only.",
                transform=ax.transAxes,fontsize=8)
        save(fig,name)

    fields=[("mfeSoFarPct","Complete prefix MFE (%)"),
            ("drawdownFromHighPct","Drawdown from pre-SELL high (%)")]
    fig,axes=plt.subplots(1,2,figsize=(9.5,4))
    for ax,(field,title) in zip(axes,fields):
        groups=[[x["path"][field] for x in group_rows(primary,"COMBINED",c)
                 if x["path"][field] is not None] for c in COHORTS]
        ax.boxplot(groups,tick_labels=[f"Winner\nN={len(groups[0])}",
                                        f"Defense\nN={len(groups[1])}"],
                   showfliers=True)
        ax.set_title(title)
    save(fig,"03_mfe_drawdown_distribution.svg")

    f=tables["E_forecast_at_sell.csv"]
    fig,ax=plt.subplots(figsize=(9,4.2))
    for c in COHORTS:
        for head,style in (("mean","-"),("q10","--"),("q90",":")):
            rows=[x for h in HORIZONS for x in f if x["arm"]=="COMBINED"
                  and x["cohort"]==c and x["horizon"]==str(h)
                  and x["family"]=="D" and x["head"]==head]
            ax.plot(range(len(HORIZONS)),[r["median"] for r in rows],style,
                    color=colors[c],label=labels[c]+" / "+head)
    ax.set_xticks(range(len(HORIZONS)),[str(h) for h in HORIZONS])
    ax.axhline(0,color="black",alpha=.5,linewidth=.7)
    ax.set(xlabel="Horizon (active minutes / EOD)",ylabel="D forecast (pct of fresh NOW)",
           title="D horizon profile at saved SELL decision")
    ax.legend(fontsize=7,ncol=2)
    save(fig,"04_d_horizon_profile.svg")

    fig,axes=plt.subplots(1,3,figsize=(12,3.6))
    for ax,family,head in zip(axes,("A","HIGH","LOW"),("mean","q50","q50")):
        for c in COHORTS:
            rows=[x for h in HORIZONS for x in f if x["arm"]=="COMBINED"
                  and x["cohort"]==c and x["horizon"]==str(h)
                  and x["family"]==family and x["head"]==head]
            ax.plot(range(len(HORIZONS)),[r["median"] for r in rows],marker="o",
                    color=colors[c],label=labels[c])
        ax.set_xticks(range(len(HORIZONS)),[str(h) for h in HORIZONS])
        ax.axhline(0,color="black",alpha=.4,linewidth=.7)
        ax.set_title(f"{family} / {head}")
        ax.set_xlabel("Active min / EOD")
        ax.set_ylabel("Forecast vs NOW (%)")
    axes[0].legend(fontsize=7)
    fig.suptitle("A / HIGH / LOW diagnostic-only horizon profiles; not R54 trade inputs")
    save(fig,"05_a_high_low_profile.svg")

    cs=tables["C_state_signals.csv"]
    fig,ax=plt.subplots(figsize=(9,8))
    ys=np.arange(len(cs))
    vals=[x["positiveRateDifferencePp"] or 0 for x in cs]
    ax.barh(ys,vals,color=["#456c97" if x["family"]=="STATE" else "#7a8a5c" for x in cs])
    ax.set_yticks(ys,[x["feature"] for x in cs],fontsize=7)
    ax.axvline(0,color="black",linewidth=.7)
    ax.set(xlabel="Winner minus defense prevalence (percentage points)",
           title="State and six signals at the frozen SELL anchor (known N in table C)")
    ax.invert_yaxis()
    save(fig,"06_state_signal_differences.svg")

    patrows=tables["D_pattern187.csv"]
    binary=sorted([x for x in patrows if x["type"]=="binary" and
                   x["winnerKnownN"]>=5 and x["defensiveKnownN"]>=5],
                  key=lambda x:(-abs(x["positiveRateDifferencePp"]),x["feature"]))[:8]
    continuous=sorted([x for x in patrows if x["type"]=="continuous" and
                       x["winnerKnownN"]>=5 and x["defensiveKnownN"]>=5 and
                       x["standardizedMedianDifference"] is not None],
                      key=lambda x:(-x["standardizedMedianDifference"],x["feature"]))[:10]
    fig,axes=plt.subplots(1,2,figsize=(13,5.8))
    for ax,selection,field,title in (
            (axes[0],binary,"positiveRateDifferencePp","Observed 0/1: positive-rate difference (pp)"),
            (axes[1],continuous,"medianDifference","Continuous: median difference / pooled IQR")):
        values=[(x[field] / x["pooledIqr"] if field=="medianDifference" else x[field])
                for x in selection]
        ax.barh(range(len(selection)),values,color="#5d7493")
        ax.set_yticks(range(len(selection)),
                      [f"{x['feature']} ({x['winnerKnownN']}/{x['defensiveKnownN']})"
                       for x in selection],fontsize=7)
        ax.axvline(0,color="black",linewidth=.7)
        ax.set_title(title,fontsize=9)
        ax.invert_yaxis()
    fig.suptitle("Pattern187 exploratory differences; N winner/defense, all 187 and BH-q in table D")
    save(fig,"07_pattern187_support_difference.svg")

    rec=tables["F_recovery.csv"]
    fig,ax=plt.subplots(figsize=(9,4.3))
    for c in COHORTS:
        rows=[x for h in HORIZONS for x in rec if x["arm"]=="COMBINED"
              and x["cohort"]==c and x["horizon"]==str(h)]
        ax.plot(range(len(HORIZONS)),[r["deltaPctMedian"] for r in rows],
                marker="o",color=colors[c],label=labels[c])
        for j,r in enumerate(rows):
            if r["deltaPctMedian"] is not None:
                ax.annotate("n="+str(r["exactPriceKnownN"]),(j,r["deltaPctMedian"]),
                            xytext=(0,7 if c=="winnerGe5" else -14),
                            textcoords="offset points",ha="center",fontsize=7)
    ax.set_xticks(range(len(HORIZONS)),[str(h) for h in HORIZONS])
    ax.axhline(0,color="black",alpha=.5,linewidth=.7)
    ax.set(xlabel="Scheduled active minutes / EOD from confirmed SELL fill",
           ylabel="Exact reference minus SELL price (%)",
           title="Post-SELL recovery (evaluator-only; exact price N annotated)")
    ax.legend(fontsize=8)
    save(fig,"08_post_sell_recovery.svg")
    return saved


def run(folder,r45_zip,forecast_zip,replay_zip,audit_zip,out):
    if out.exists():raise ValueError("APPEND_ONLY_ANATOMY_OUTPUT")
    p,receipt,arrays,forecasts,traces,standalone,paired,ledgers,ids_path=load_inputs(
        folder,r45_zip,forecast_zip,replay_zip,audit_zip)
    primary,secondary,pattern_names=build_records(
        folder,receipt,arrays,forecasts,traces,standalone,paired,ledgers,ids_path)
    schema=json.loads(SCHEMA.read_text())
    tables=build_tables(primary,secondary,pattern_names,schema)
    out.mkdir(parents=True)
    for name,rows in tables.items():write_csv(out/name,rows)
    figures=charts(primary,tables,out/"figures")
    result={"schema":"phase57-post-r54-winner-anatomy-result-v1",
        "precommitSha256":sha(PRE),"sourceArtifactIds":p["sourcePins"],
        "r45ArtifactZipSha256":sha(r45_zip),
        "primaryN":len(primary),"secondaryN":len(secondary),
        "primaryCounts":tables["A_cohorts.csv"][:3],
        "secondaryCounts":tables["A_cohorts.csv"][3:],
        "primaryCompletePrefixN":sum(x["path"]["completePrefix"] for x in primary),
        "primaryCompleteRemainingPathN":sum(x["wholeFuture"] is not None for x in primary),
        "fullTraceN":len([x for x in traces if x["variant"]=="FULL" and x["policy"]=="MH_WAIT15"]),
        "fullGraceUsedN":sum(x["graceUsed"] for x in traces
                             if x["variant"]=="FULL" and x["policy"]=="MH_WAIT15"),
        "primaryLongSupportAtModelSellN":sum(x["longSupport"] for x in primary
                                               if x["exitKind"]=="MODEL_EXIT"),
        "gradeCriteria":p["evidenceGrades"],
        "interpretation":"DESCRIPTIVE_ONLY_NO_PREDICTIVE_OR_EXIT_SELECTION_AUTHORITY",
        "newEstimatorFits":0,"newIntegratedReplays":0,"providerRequests":0,
        "protectedOpened":0,"safety":p["safety"]}
    (out/"RESULT.json").write_bytes(canonical(result))
    (out/"PRIMARY_ENTRY_EVALUATOR_ONLY.json").write_bytes(canonical(primary))
    files={str(x.relative_to(out)):sha(x) for x in sorted(out.rglob("*")) if x.is_file()}
    (out/"MANIFEST.json").write_bytes(canonical({"schema":"phase57-post-r54-anatomy-files-v1",
        "filesSha256":files,"precommitSha256":sha(PRE),"newEstimatorFits":0,
        "newIntegratedReplays":0,"providerRequests":0,"protectedOpened":0}))
    return result,tables,figures


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    for key in ("folder","r45-zip","forecast-zip","replay-zip","audit-zip","out"):
        ap.add_argument("--"+key,type=Path,required=True)
    a=ap.parse_args()
    result,tables,figures=run(a.folder,a.r45_zip,a.forecast_zip,
                              a.replay_zip,a.audit_zip,a.out)
    print(canonical({"status":"DESCRIPTIVE_COMPLETE", "primaryN":result["primaryN"],
                     "counts":result["primaryCounts"],"tables":list(tables),
                     "figures":figures,"newEstimatorFits":0,
                     "newIntegratedReplays":0}).decode(),flush=True)
