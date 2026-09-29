"""Descriptive analysis of two already saved EXIT outcomes, after A0 freeze."""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
import math
import statistics

from scripts import phase57_post_prr_phase_a as a


def percentile_rank(values):
    order=sorted(range(len(values)), key=lambda i:values[i])
    ranks=[0.0]*len(values)
    i=0
    while i<len(order):
        j=i+1
        while j<len(order) and values[order[j]]==values[order[i]]:
            j+=1
        for k in order[i:j]:ranks[k]=(i+j+1)/2
        i=j
    return ranks


def corr(x,y):
    if len(x)<3:return None
    xm,ym=statistics.mean(x),statistics.mean(y)
    den=math.sqrt(sum((v-xm)**2 for v in x)*sum((v-ym)**2 for v in y))
    return None if den==0 else sum((v-xm)*(w-ym) for v,w in zip(x,y))/den


def record(row, mask):
    if not mask["paired_outcome_known"]:return None
    cost=a.D(row["entryCostJpy"])
    c,m=a.D(row["normalizedControlPnlJpy"]),a.D(row["normalizedCcmgPnlJpy"])
    delta=m-c
    routed=m if row["routeDecision"]=="DEFENSIVE_ELIGIBLE" else c
    label=a.D(row["futureUpsidePctEvaluatorOnly"])
    band="<5" if label<5 else "5-10" if label<10 else ">=10"
    return {"world":row["world"],"arm":row["arm"],"entryId":row["entryId"],
      "session":row["session"],"symbol":row["symbol"],"opportunityId":row["opportunityId"],
      "primary":row["primary"],"quantity":row["quantity"],"entryMinute":row["entryMinute"],
      "entryCostJpy":str(cost),"routeDecision":row["routeDecision"],
      "futureUpsidePctEvaluatorOnly":row["futureUpsidePctEvaluatorOnly"],"band":band,
      "controlPnlJpy":str(c),"ccmgPnlJpy":str(m),"routedPnlJpy":str(routed),
      "deltaPnlJpy":str(delta),"routedDeltaPnlJpy":str(routed-c),
      "controlNetPct":str(c/cost*100),"ccmgNetPct":str(m/cost*100),
      "deltaNetPp":str(delta/cost*100),"routedDeltaNetPp":str((routed-c)/cost*100),
      "score5":row["score5"],"score10":row["score10"],
      "rank5Decile":row["rank5Decile"],"rank10Decile":row["rank10Decile"],
      "ccmgFirstIntentMinute":row["ccmgFirstIntentMinute"],
      "controlModelIntentMinute":mask["controlIntentMinute"],
      "controlTerminalDecisionMinute":row["controlDecisionMinute"],
      "controlExitKind":row["controlExitKind"],
      "controlFillMinute":row["controlExitMinute"],"ccmgFillMinute":row["ccmgExitMinute"],
      "controlExitPrice":row["controlExitPrice"],"ccmgExitPrice":row["ccmgExitPrice"],
      "intentOrder":mask["intentOrder"],
      "causalGuardTraceAtIntent":mask["causalGuardTraceAtIntent"],
      "runtimeFeatureAsOfValid":mask["runtime_feature_asof_valid"],
      "fullStage2RuntimeFeatureSnapshot":False}


def summary(rows, delta_key="deltaPnlJpy"):
    n=len(rows)
    if not n:return {"pairedN":0,"status":"INCONCLUSIVE_NO_PAIRED_ROWS"}
    sums={name:sum((a.D(r[name]) for r in rows),a.ZERO) for name in
          ("controlPnlJpy","ccmgPnlJpy","routedPnlJpy","deltaPnlJpy",
           "routedDeltaPnlJpy","controlNetPct","ccmgNetPct","deltaNetPp","routedDeltaNetPp",
           "entryCostJpy")}
    diffs=[a.D(r[delta_key]) for r in rows]
    return {"pairedN":n,"distinctSessionN":len({r["session"] for r in rows}),
       "distinctOpportunityN":len({r["opportunityId"] for r in rows}),
       "improveN":sum(x>0 for x in diffs),"equalN":sum(x==0 for x in diffs),
       "worseN":sum(x<0 for x in diffs),
       "controlPnlJpy":str(sums["controlPnlJpy"]),
       "ccmgPnlJpy":str(sums["ccmgPnlJpy"]),
       "routedPnlJpy":str(sums["routedPnlJpy"]),
       "deltaPnlJpy":str(sums["deltaPnlJpy"]),
       "routedDeltaPnlJpy":str(sums["routedDeltaPnlJpy"]),
       "meanControlPnlJpy":str(sums["controlPnlJpy"]/n),
       "meanCcmgPnlJpy":str(sums["ccmgPnlJpy"]/n),
       "meanDeltaPnlJpy":str(sums["deltaPnlJpy"]/n),
       "meanControlNetPct":str(sums["controlNetPct"]/n),
       "meanCcmgNetPct":str(sums["ccmgNetPct"]/n),
       "meanDeltaNetPp":str(sums["deltaNetPp"]/n),
       "meanRoutedDeltaNetPp":str(sums["routedDeltaNetPp"]/n),
       "capitalWeightedControlReturnPct":str(100*sums["controlPnlJpy"]/sums["entryCostJpy"]),
       "capitalWeightedCcmgReturnPct":str(100*sums["ccmgPnlJpy"]/sums["entryCostJpy"]),
       "costSumJpy":str(sums["entryCostJpy"])}


def concentration(rows):
    positives=sorted((r for r in rows if a.D(r["deltaPnlJpy"])>0),
                     key=lambda r:a.D(r["deltaPnlJpy"]),reverse=True)
    negatives=sorted((r for r in rows if a.D(r["deltaPnlJpy"])<0),
                     key=lambda r:a.D(r["deltaPnlJpy"]))
    pos=sum((a.D(r["deltaPnlJpy"]) for r in positives),a.ZERO)
    loss=-sum((a.D(r["deltaPnlJpy"]) for r in negatives),a.ZERO)
    by_session=defaultdict(lambda:a.ZERO)
    for r in rows:by_session[r["session"]]+=a.D(r["deltaPnlJpy"])
    return {"pairedN":len(rows),"positiveN":len(positives),"negativeN":len(negatives),
      "zeroN":len(rows)-len(positives)-len(negatives),
      "grossGainJpy":str(pos),"grossLossAbsoluteJpy":str(loss),
      "netDeltaJpy":str(pos-loss),
      "lossTopN":{str(n):{"absoluteJpy":str(-sum((a.D(r["deltaPnlJpy"]) for r in negatives[:n]),a.ZERO)),
                           "shareOfGrossLossPct":None if loss==0 else str(-100*sum((a.D(r["deltaPnlJpy"]) for r in negatives[:n]),a.ZERO)/loss)}
                  for n in (1,3,5,10)},
      "topLossRows":[{"entryId":r["entryId"],"session":r["session"],
                      "deltaPnlJpy":r["deltaPnlJpy"],"band":r["band"],
                      "routeDecision":r["routeDecision"]} for r in negatives[:10]],
      "topGainRows":[{"entryId":r["entryId"],"session":r["session"],
                      "deltaPnlJpy":r["deltaPnlJpy"],"band":r["band"],
                      "routeDecision":r["routeDecision"]} for r in positives[:10]],
      "sessionDeltaJpy":{k:str(v) for k,v in sorted(by_session.items())},
      "negativeSessionN":sum(v<0 for v in by_session.values()),
      "positiveSessionN":sum(v>0 for v in by_session.values())}


def rank_relation(rows):
    out={}
    for head in (5,10):
        field=f"rank{head}Decile"
        out[f"head{head}"]={"deciles":{str(i):summary([r for r in rows if r[field]==i])
                                             for i in range(10)},
          "scoreDeltaPearson":corr([float(r[f"score{head}"]) for r in rows],
                                    [float(r["deltaPnlJpy"]) for r in rows]),
          "scoreDeltaSpearmanDescriptive":corr(
              percentile_rank([float(r[f"score{head}"]) for r in rows]),
              percentile_rank([float(r["deltaPnlJpy"]) for r in rows])),
          "allPairedN":len(rows),"nonzeroDiagnosticN":sum(a.D(r["deltaPnlJpy"])!=0 for r in rows)}
    return out


def cross_arm(rows):
    by=defaultdict(lambda:defaultdict(list))
    for r in rows:
        if r["world"]=="ALL_100":by[r["opportunityId"]][r["arm"]].append(r)
    paired=[];multi=[]
    for oid, arms in sorted(by.items()):
        if not all(k in arms for k in ("IM","R1")):continue
        if len(arms["IM"])!=1 or len(arms["R1"])!=1:
            multi.append({"opportunityId":oid,"IM":len(arms["IM"]),"R1":len(arms["R1"])})
            continue
        im,r1=arms["IM"][0],arms["R1"][0]
        paired.append({"opportunityId":oid,"imEntryId":im["entryId"],
            "r1EntryId":r1["entryId"],"entryMinuteDifferenceR1MinusIM":r1["entryMinute"]-im["entryMinute"],
            "imPrimary":im["primary"],"r1Primary":r1["primary"],
            "imDeltaJpy":im["deltaPnlJpy"],"r1DeltaJpy":r1["deltaPnlJpy"],
            "deltaDifferenceR1MinusIMJpy":str(a.D(r1["deltaPnlJpy"])-a.D(im["deltaPnlJpy"]))})
    a.write_rows("CROSS_ARM_OPPORTUNITY_ROWS.jsonl.gz",paired)
    return {"sameOpportunityKnownPairedN":len(paired),"ambiguousMultiEntryOpportunityN":len(multi),
       "ambiguousExamples":multi[:10],"bothPrimaryN":sum(x["imPrimary"] and x["r1Primary"] for x in paired),
       "sameEntryMinuteN":sum(x["entryMinuteDifferenceR1MinusIM"]==0 for x in paired),
       "sameDeltaSignN":sum((a.D(x["imDeltaJpy"])>0)-(a.D(x["imDeltaJpy"])<0)==
                            (a.D(x["r1DeltaJpy"])>0)-(a.D(x["r1DeltaJpy"])<0) for x in paired),
       "interpretation":"Corresponding opportunities, not independent extra observations or same-Entry policy effects."}


def intent(rows):
    with_c=[r for r in rows if r["ccmgFirstIntentMinute"] is not None]
    both=[r for r in with_c if r["controlModelIntentMinute"] is not None]
    early=[r for r in with_c if r["ccmgFirstIntentMinute"]<r["controlFillMinute"]]
    after=[r for r in with_c if r["ccmgFillMinute"]>r["controlFillMinute"]]
    return {"pairedN":len(rows),"ccmgFirstIntentN":len(with_c),
      "r50ModelIntentN":sum(r["controlModelIntentMinute"] is not None for r in rows),
      "r50ForcedTerminalN":sum(r["controlExitKind"]=="FORCED_TERMINAL" for r in rows),
      "bothModelIntentKnownN":len(both),
      "intentOrderN":dict(Counter(r["intentOrder"] for r in both)),
      "ccmgIntentBeforeR50FillN":len(early),
      "ccmgFillAfterR50FillN":len(after),
      "sameFillMinuteN":sum(r["ccmgFillMinute"]==r["controlFillMinute"] for r in rows),
      "sameFillPriceN":sum(a.D(r["ccmgExitPrice"])==a.D(r["controlExitPrice"]) for r in rows),
      "intentToFillMinuteN":dict(Counter(str(r["ccmgFillMinute"]-r["ccmgFirstIntentMinute"])
                                     for r in with_c)),
      "guardTraceAsOfN":sum(r["runtimeFeatureAsOfValid"] for r in with_c),
      "fullStage2FeatureSnapshotN":0,
      "ccmgIntentBeforeR50FillDeltaJpy":str(sum((a.D(r["deltaPnlJpy"]) for r in early),a.ZERO)),
      "ccmgFillAfterR50FillDeltaJpy":str(sum((a.D(r["deltaPnlJpy"]) for r in after),a.ZERO)),
      "meaning":"R50 MODEL_EXIT controlNow is intent; 925 forced terminal is not an early model intent. ExitMinute is execution reference, never intent."}


def run():
    spec=a.read("A1_ANALYSIS_SPEC.json")
    if a.sha(a.OUT / "A1_ANALYSIS_SPEC.json")!=(a.OUT / "A1_ANALYSIS_SPEC.sha256").read_text().split()[0] or \
       a.sha(a.OUT / "A0_CENSUS.json")!=spec["a0Sha256"] or \
       a.sha(a.OUT / "A0_FREEZE.json")!=spec["a0FreezeSha256"]:
        raise AssertionError("A0_OR_A1_SPEC_DRIFT")
    source=a.rows(a.OUT / "ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz")
    masks=a.rows(a.OUT / "COMPARISON_MASK_ROWS.jsonl.gz")
    mask={(x["world"],x["arm"],x["entryId"]):x for x in masks}
    if len(mask)!=len(source):raise AssertionError("MASK_POPULATION")
    paired=[record(x,mask[(x["world"],x["arm"],x["entryId"])]) for x in source]
    paired=[x for x in paired if x is not None]
    a.write_rows("A1_PAIRED_ROWS.jsonl.gz",paired)
    populations={"ALL_100":lambda x:x["world"]=="ALL_100",
                 "PRIMARY_FUNDED":lambda x:x["world"]=="PRIMARY_FUNDED",
                 "PRIMARY_OUTSIDE_100":lambda x:x["world"]=="ALL_100" and not x["primary"]}
    values={};bands={};concentrations={};rank={};intents={};gates={}
    # Old receipts are only read for their status, not used as monetary inputs.
    import json
    oldp=json.loads((a.PRR/"LAYER_A_RESULT.json").read_text())
    olda=json.loads((a.PRR/"ALL_ENTRY_RESULT.json").read_text())
    for world,filter_world in populations.items():
        for arm in ("IM","R1"):
            xs=[r for r in paired if r["arm"]==arm and filter_world(r)]
            for route in ("ALL_ROUTES","DEFENSIVE_ELIGIBLE","CONTROL_DEFAULT"):
                sub=[r for r in xs if route=="ALL_ROUTES" or r["routeDecision"]==route]
                values[f"{world}:{arm}:{route}"]=summary(sub)
            for band in ("<5","5-10",">=10",">=5"):
                sub=[r for r in xs if (r["band"]==band if band!=">=5" else r["band"]!="<5")]
                bands[f"{world}:{arm}:{band}"]=summary(sub)
            concentrations[f"{world}:{arm}"]=concentration(xs)
            intents[f"{world}:{arm}"]=intent(xs)
            if world=="ALL_100":rank[arm]=rank_relation(xs)
            for threshold in (5,10):
                sub=[r for r in xs if a.D(r["futureUpsidePctEvaluatorOnly"])>=threshold]
                m=summary(sub)
                if m["pairedN"]:
                    cc=a.D(m["deltaPnlJpy"]); pct=a.D(m["meanDeltaNetPp"])
                    rd=a.D(m["routedDeltaPnlJpy"]);rpct=a.D(m["meanRoutedDeltaNetPp"])
                    gates[f"{world}:{arm}:>={threshold}"]={"pairedN":m["pairedN"],
                       "ccmgAggregateDeltaJpy":str(cc),"ccmgMeanDeltaNetPp":str(pct),
                       "ccmgBothGate":"PASS" if cc>=0 and pct>=0 else "FAIL",
                       "routedAggregateDeltaJpy":str(rd),"routedMeanDeltaNetPp":str(rpct),
                       "routedBothGate":"PASS" if rd>=0 and rpct>=0 else "FAIL",
                       "oldRoutedReceiptGate":(oldp["winner"][f"{arm}>={threshold}"]["gate"]
                          if world=="PRIMARY_FUNDED" else olda["winnerGate"] if world=="ALL_100" else None)}
    cross=cross_arm(paired)
    out={"schema":"phase57-post-prr-a1-results-v1","specSha256":a.sha(a.OUT/"A1_ANALYSIS_SPEC.json"),
         "pairedRowsSha256":a.sha(a.OUT/"A1_PAIRED_ROWS.jsonl.gz"),
         "crossArmRowsSha256":a.sha(a.OUT/"CROSS_ARM_OPPORTUNITY_ROWS.jsonl.gz"),
         "values":values,"bands":bands,"concentration":concentrations,
         "rank":rank,"crossArmOpportunity":cross,"intentAndFill":intents,
         "winnerGateAudit":gates,"inference":"Repeated Development exposure, no new external validation; descriptive saved-outcome comparison only.",
         "fits":0,"policyReplays":0}
    a.write("A1_RESULTS.json",out)
    print(json.dumps({"paired":{k:v["pairedN"] for k,v in values.items() if k.endswith("ALL_ROUTES")},
                      "a1Sha256":a.sha(a.OUT/"A1_RESULTS.json")}))


if __name__=="__main__":
    run()
