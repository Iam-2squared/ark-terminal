"""R54 fixed-Capital, full-event A/B/S/P EXIT research and certified reporting.

Forecast arrays must pass OOF and source-identity audit before this script is
invoked. Runtime calendars consume only forecasts and frozen NOW facts; future
prices are read solely *after* a SELL_INTENT by the frozen execution adapter.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import gzip
import json
import math
import statistics
from decimal import Decimal
from pathlib import Path
from unittest import mock

import numpy as np

from scripts import phase57_mh_data_r54 as data
from scripts import phase57_mh_controller_r54 as ctl

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/phase57-exit-mh-r54"
STRESS = (Decimal("0.10"),Decimal("0.20"))


def forecast(npz, index, variant, targets):
    """Use train-supported and calendar-supported predictions, never labels."""
    x = {}
    for h in targets:
        j=data.HORIZONS.index(h)
        family="REFIT" if variant=="REFIT" else variant
        names=[family+"__D__"+head for head in ("mean","q10","q90")]
        v=[float(npz[k][index,j]) for k in names]
        if all(math.isfinite(z) for z in v):
            x[h]={"mean":v[0],"q10":min(v[1],v[2]),"q90":max(v[1],v[2]),
                  "rawQ10":v[1],"rawQ90":v[2],"quantilesCrossed":v[1]>v[2]}
    return x


def calendars(receipt, arrays, identities, groups, entries, raw, npz, variant, policy, days):
    from scripts import phase57_exit_continuation_r52 as r52
    from scripts import phase57_development_integrated_v0 as v0
    cols=receipt["numericColumns"]
    ret=cols.index("facts.currentReturnPct")
    result={arm:{} for arm in v0.ARMS};traces=[]
    for (arm,eid),seq in sorted(groups.items()):
        entry=entries[arm,eid];day=entry["session"]
        if day not in days:continue
        path=raw[entry["opportunity"]]
        observed=[path[t] for t in sorted(path)]
        controller=ctl.Controller(policy,day)
        selected=None;reasons=collections.Counter();issues=[]
        for i in seq:
            now=identities[i]["now"]
            plan=data.planned_targets(day,now)
            preds=forecast(npz,i,variant,plan)
            r=float(arrays["numeric"][i,ret]);ret_value=r if math.isfinite(r) else None
            act=controller.decide(now,preds,plan,fresh=bool(arrays["fresh"][i]),
                                  current_return=ret_value)
            reasons[act["reason"]]+=1
            if act["action"]=="HOLD":continue
            if act["action"]=="FORCE_TERMINAL":
                ref=data.execution.terminal_execution_reference(observed)
                selected={"session":day,"entryId":eid,"decisionNow":now,
                    "exitMinute":930 if ref["price"] is not None else None,
                    "exitPrice":ref["price"],"exitKind":"FORCED_TERMINAL",
                    "reason":act["reason"],"sourceStatus":ref["status"]}
                break
            # This exact OPEN lookup only occurs after NOW-generated SELL_INTENT.
            ref=data.execution.ordinary_execution_reference(day,now,observed)
            if ref["status"]!="RESOLVED_NEXT_SCHEDULED_OPEN":
                issues.append({"now":now,"reason":ref["status"]})
                controller.intent_result(False)
                continue
            selected={"session":day,"entryId":eid,"decisionNow":now,
                "exitMinute":ref["referenceStart"],"exitPrice":ref["price"],
                "exitKind":"MODEL_EXIT","reason":act["reason"],"sourceStatus":ref["status"]}
            controller.intent_result(True)
            break
        if selected is None:raise ValueError("MISSING_FROZEN_TERMINAL_CHECKPOINT:"+eid)
        result[arm][eid]=selected
        traces.append({"variant":variant,"policy":policy,"arm":arm,**selected,
           "reasons":dict(reasons),"graceUsed":controller.state.grace_used,
           "graceOrigin":controller.state.grace_origin,
           "graceDeadline":controller.state.grace_deadline,
           "missingOrdinaryReferences":issues})
    return result,traces


def write_csv(path,rows,cols):
    with path.open("w",newline="") as fd:
        writer=csv.DictWriter(fd,fieldnames=cols,extrasaction="ignore")
        writer.writeheader();writer.writerows(rows)


def detailed_buckets(ledger,evaluation,contexts):
    """Post-replay attribution only; never returned to funding or EXIT."""
    from scripts import phase57_capital_exit_integrated as integrated
    closed={x["entryId"]:x for x in ledger["closed"]}
    output={}
    for context in ("Initial","Replacement","Combined"):
        rows=[]
        for item in integrated.distribution({"funded":{eid:r for eid,r in ledger["funded"].items()
                    if context=="Combined" or contexts[eid]==context},
                    "closed":[x for x in ledger["closed"] if context=="Combined" or
                                      contexts[x["entryId"]]==context]},evaluation):
            name=item["bucket"]
            ids=[eid for eid in ledger["funded"] if
                 (context=="Combined" or contexts[eid]==context) and
                 integrated.upside_bucket(evaluation[eid]["postUpsidePct"])==name]
            pnl=[Decimal(closed[eid]["realizedPnlJpy"]) for eid in ids if eid in closed]
            gains=sum((x for x in pnl if x>0),Decimal(0));loss=-sum((x for x in pnl if x<0),Decimal(0))
            rows.append({**item,"confirmedPnlJpy":str(sum(pnl,Decimal(0))),
                "grossProfitsJpy":str(gains),"grossLossesJpy":str(loss),
                "profitFactor":float(gains/loss) if loss else None,
                "winRate":sum(x>0 for x in pnl)/len(pnl) if pnl else None,
                "netEvaluableCount":len(pnl)})
        output[context]=rows
    return output


def standalone_all_entries(calendars_all,control,entries,evaluation,days):
    """All frozen Entry IDs, one 100-share diagnostic unit, not funded PnL."""
    from scripts import phase57_development_integrated_v0 as v0
    rows={}
    for arm in v0.ARMS:
        name="IM" if arm==v0.IM else "R1"
        for variant,calendar in [("R50_A_CONTROL",control[arm])]+[
            (key,val[arm]) for key,val in calendars_all.items()]:
            sub=[]
            for (a,eid),entry in sorted(entries.items()):
                if a!=arm or entry["session"] not in days:continue
                pos=calendar.get(eid)
                if pos is None:raise ValueError("ALL_ENTRY_EXIT_CALENDAR_INCOMPLETE")
                fill=pos["exitPrice"]
                effective=Decimal(str(entry["effectiveEntryPrice"]))
                profit=(None if fill is None else
                       str((Decimal(str(fill))-effective*Decimal("1.0005"))*100))
                sub.append({"entryId":eid,"session":entry["session"],
                    "diagnosticShareQuantity":100,"entryEffectivePrice":str(effective),
                    "exitPrice":fill,"exitMinute":pos["exitMinute"],
                    "closedDiagnosticPnlJpy":profit,
                    "evaluatorOnlyPostEntryUpsidePct":evaluation[arm][eid]["postUpsidePct"]})
            rows[name+"_"+variant]=sub
    return rows


def forecast_metrics(predictions,labels,ids,folds,arm,variant="FULL",partition="score",now_prices=None):
    """Scored OOF only. Checkpoint error is grouped Entry then session."""
    rows=[]
    for fold in folds:
        scored=set(fold[partition])
        for h in data.HORIZONS:
            j=data.HORIZONS.index(h)
            for family in (data.FAMILIES if variant=="FULL" else ("D",)):
                head="mean" if family in ("A","D") else "q50"
                key=f"{variant}__{family}__{head}"
                pred=predictions[key][:,j]
                target=labels[family][:,j]
                sel=np.asarray([x["arm"]==arm and x["session"] in scored for x in ids])
                sel &= np.isfinite(pred) & np.isfinite(target)
                ii=np.flatnonzero(sel)
                if len(ii)==0:
                    rows.append({"fold":fold["fold"],"arm":arm,"variant":variant,
                                 "partition":partition,"family":family,
                                 "horizon":str(h),"n":0,"mae":None,"rmse":None,"bias":None})
                    continue
                diff=pred[ii]-target[ii]
                record={"fold":fold["fold"],"arm":arm,"family":family,"horizon":str(h),
                        "variant":variant,"partition":partition,
                        "n":len(ii),"entryIds":len({ids[i]["entryId"] for i in ii}),
                        "mae":float(np.abs(diff).mean()),"rmse":float(np.sqrt(np.square(diff).mean())),
                        "bias":float(diff.mean()),"zeroMse":float(np.square(target[ii]).mean())}
                if family in ("A","D"):
                    q10=predictions[f"{variant}__{family}__q10"][ii,j]
                    q90=predictions[f"{variant}__{family}__q90"][ii,j]
                else:
                    q10=predictions[f"{variant}__{family}__q10"][ii,j]
                    q90=predictions[f"{variant}__{family}__q90"][ii,j]
                lo=np.minimum(q10,q90);hi=np.maximum(q10,q90)
                record.update(intervalCoverage=float(np.mean((target[ii]>=lo)&(target[ii]<=hi))),
                              nominalIntervalCoverage=.8,intervalWidthPp=float((hi-lo).mean()),
                              quantileCrossingRate=float(np.mean(q10>q90)),
                              zeroComparatorMse=float(np.square(target[ii]).mean()),
                              q10Pinball=float(np.mean(np.maximum(.1*(target[ii]-q10),-.9*(target[ii]-q10)))),
                              q90Pinball=float(np.mean(np.maximum(.9*(target[ii]-q90),-.1*(target[ii]-q90)))))
                if now_prices is not None and family=="A":
                    prices=now_prices[ii];valid=np.isfinite(prices)
                    record["yenMeanAbsoluteError"]=(float(np.mean(np.abs(diff[valid])*prices[valid]/100))
                                                   if np.any(valid) else None)
                if family=="D":
                    # Each session receives equal weight, then each Entry.
                    bysession=collections.defaultdict(lambda:collections.defaultdict(list))
                    for ix,delta,truth in zip(ii,diff,target[ii]):
                        bysession[ids[ix]["session"]][ids[ix]["entryId"]].append((float(delta**2),float(truth**2)))
                    pairs=[(statistics.fmean([statistics.fmean(t[0] for t in vals)
                               for vals in entries.values()]),
                            statistics.fmean([statistics.fmean(t[1] for t in vals)
                               for vals in entries.values()])) for entries in bysession.values()]
                    record["entrySessionWeightedMse"]=statistics.fmean(p[0] for p in pairs)
                    record["entrySessionWeightedZeroMse"]=statistics.fmean(p[1] for p in pairs)
                rows.append(record)
    return rows


def frozen_gate(protocol, reports, paired, metrics, arm_im, control, stress,
                byte_ok, refit_ok):
    g=protocol["gate"];out={}
    b=reports["IM"]["R50_A_CONTROL"]
    for policy in ctl.POLICIES:
        name="FULL_"+policy
        x=reports["IM"][name];q=x["quality"];co=q["Combined"];rep=q["Replacement"]
        score=x["portfolio"];old=b["portfolio"]
        # Layer A fixed baseline ids and quantities; unsupported fills remain null.
        rows=paired["IM"][name]
        groups={"ge5":[r for r in rows if r["evaluatorOnlyUpsidePct"] is not None and r["evaluatorOnlyUpsidePct"]>=5],
                "ge10":[r for r in rows if r["evaluatorOnlyUpsidePct"] is not None and r["evaluatorOnlyUpsidePct"]>=10],
                "3to5":[r for r in rows if r["evaluatorOnlyUpsidePct"] is not None and 3<=r["evaluatorOnlyUpsidePct"]<5],
                "below1":[r for r in rows if r["evaluatorOnlyUpsidePct"] is not None and r["evaluatorOnlyUpsidePct"]<1]}
        def pnls(k):
            z=[r for r in groups[k] if r["candidatePnlJpy"] is not None]
            return [Decimal(r["candidatePnlJpy"]) for r in z],len(z)==len(groups[k])
        def mean_net(k):
            z,complete=pnls(k)
            return None if not z or not complete else statistics.fmean(
               float(Decimal(r["candidatePnlJpy"])/Decimal(control["funded"][r["entryId"]]["notionalJpy"])*100)
               for r in groups[k])
        ge5,complete5=pnls("ge5");w5=mean_net("ge5");w10=mean_net("ge10")
        w35=mean_net("3to5");low=mean_net("below1")
        final=score["finalEquityJpy"]
        rules={"integrity":byte_ok and refit_ok,
             "IM24certifiedEod":x["dailySummary"]["validSessions"]==24,
             "positiveAndAboveControl":final is not None and
                  Decimal(final)>Decimal("1000000") and
                  old["finalEquityJpy"] is not None and Decimal(final)>Decimal(old["finalEquityJpy"]),
             "pairedWinnerGe5MeanNet":w5 is not None and w5>=g["pairedGe5MeanNetPctMin"],
             "pairedWinnerGe5Currency":complete5 and len(ge5)==27 and sum(ge5)>=Decimal(g["pairedGe5PnlJpyMin"]),
             "pairedWinnerGe10MeanNet":w10 is not None and w10>=g["pairedGe10MeanNetPctMin"],
             "pairedThreeToFiveMeanNet":w35 is not None and w35>=0,
             "pairedBelowOneMeanNet":low is not None and low>=g["pairedBelow1MeanNetPctMin"],
             "combinedGe5":co["ge5"]>=27,"combinedGe10":co["ge10"]>=15,
             "ge5Reach":x["upside"]["reach"]>=g["ge5ReachMin"],
             "replacementSupportAndGe5":rep["n"]>=5 and rep["ge5"]>=1,
             "replacementUpsideMedian":rep["medianUpsidePct"] is not None and
                rep["medianUpsidePct"]>=g["replacementMedianUpsidePctMin"],
             "EodMaxDD":x["eodMaxDrawdownPct"] is not None and
                 b["eodMaxDrawdownPct"] is not None and
                 x["eodMaxDrawdownPct"]>=b["eodMaxDrawdownPct"],
             "topSessionConcentration":x["supplemental"]["topSessionNotionalShare"] is not None
                        and x["supplemental"]["topSessionNotionalShare"]<=.2}
        stress_new=stress[f"0.20|IM|{name}"]
        stress_old=stress["0.20|IM|R50_A_CONTROL"]
        rules["costStress20bp"]=(stress_new["certifiedDays"]==24 and
            stress_old["finalEquityJpy"] is not None and
            stress_new["finalEquityJpy"] is not None and
            Decimal(stress_new["finalEquityJpy"])>Decimal("1000000") and
            Decimal(stress_new["finalEquityJpy"])>Decimal(stress_old["finalEquityJpy"]))
        skill=[r for r in metrics if r["arm"]==arm_im and r["variant"]=="FULL" and r["family"]=="D" and
               r["horizon"] in ("1","5","15") and r["n"]>0]
        per=collections.defaultdict(list)
        for row in skill:per[row["fold"]].append(row)
        passed=sum(statistics.fmean(r["entrySessionWeightedMse"] for r in x)<
                   statistics.fmean(r["entrySessionWeightedZeroMse"] for r in x)
                   for x in per.values())
        rules["DforecastSkill"]=(len(per)==4 and passed>=3 and
             statistics.fmean(r["entrySessionWeightedMse"] for r in skill)<
             statistics.fmean(r["entrySessionWeightedZeroMse"] for r in skill))
        out[name]={"rules":rules,"allPass":all(rules.values()),
                   "winnerGe5MeanNetPct":w5,"winnerGe10MeanNetPct":w10,
                   "paired3to5MeanNetPct":w35,"pairedBelow1MeanNetPct":low,
                   "pairedGe5PnlJpy":None if not complete5 else str(sum(ge5))}
    winners=[name for name,x in out.items() if x["allPass"]]
    selection=None
    if winners:
        rank=lambda name:(Decimal(reports["IM"][name]["portfolio"]["finalEquityJpy"]),
            Decimal(out[name]["pairedGe5PnlJpy"]),reports["IM"][name]["quality"]["Combined"]["ge5"])
        top=max(map(rank,winners));chosen=[name for name in winners if rank(name)==top]
        if len(chosen)==1:selection=chosen[0]
    return {"integrity":"PASS" if byte_ok else "INTEGRITY_ABORT",
            "measurement":"CERTIFIED" if all(reports["IM"][n]["dailySummary"]["validSessions"]==24
                                            for n in out) else "MEASUREMENT_BLOCKED",
            "selection":"SELECT_DEVELOPMENT_ONLY" if selection else "NO_SELECTION_STOP",
            "selected":selection,"votes":out,"productionReady":False}


def finite(source, summary, label_path, forecast_path, refit_path, out):
    from scripts import phase57_exit_continuation_r52 as r52
    from scripts import phase57_exit_continuation_r52_independent_audit as audit52
    from scripts import phase57_capital_exit_integrated as integrated
    from scripts import phase57_capital_v3 as v3
    from scripts import phase57_development_integrated_v0 as v0
    from scripts import phase57_development_integrated_v1 as v1
    from scripts import phase57_cash_capital_r34 as cash
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    protocol=json.loads((EVIDENCE/"PRECOMMIT.json").read_text())
    if data.sha(EVIDENCE/"PRECOMMIT.json")!=(EVIDENCE/"PRECOMMIT.sha256").read_text().strip():
        raise ValueError("R54_PROTOCOL_CHANGED")
    oof_audit=json.loads((forecast_path.parent/"oof-audit.json").read_text())
    if (data.sha(forecast_path)!=oof_audit["predictionsSha256"]
        or data.sha(refit_path)!=oof_audit["independentPredictionsSha256"]
        or oof_audit["expectedFits"]!=protocol["budget"]["maxRealEstimatorFits"]
        or data.sha(label_path)!=protocol["inputHashes"]["labels"]):
        raise ValueError("UNAUDITED_OOF_FORECAST")
    receipt,arrays,ids,groups=r52.load_checkpoints(source)
    entries=r52.all_frozen_entries();raw=r52.projected_raw(entries)
    _,original,score,control_exit=integrated.load_inputs()
    _,_,cohort,intents,evaluation,_,joined_raw,_,_,labels=original
    days=protocol["sessions"]
    if out.exists():raise ValueError("APPEND_ONLY_REPLAY")
    out.mkdir(parents=True)
    with np.load(forecast_path,allow_pickle=False) as z:
        preds={k:z[k] for k in z.files}
    with np.load(refit_path,allow_pickle=False) as z:
        refit={k:z[k] for k in z.files}
    with np.load(label_path,allow_pickle=False) as z:
        truth={k:z[k] for k in data.FAMILIES}
    folds=json.loads((summary/"fold-manifest.json").read_text())
    now_prices=np.full(len(ids),np.nan,np.float32)
    for (arm,eid),seq in groups.items():
        path=raw[entries[arm,eid]["opportunity"]]
        for i in seq:
            now_prices[i]=data._price(path.get(ids[i]["now"]-1),4) or np.nan
    metrics={short:(forecast_metrics(preds,truth,ids,folds,arm,now_prices=now_prices)
                   +forecast_metrics(preds,truth,ids,folds,arm,"S",now_prices=now_prices)
                   +forecast_metrics(preds,truth,ids,folds,arm,"P",now_prices=now_prices))
             for short,arm in (("IM",v0.IM),("R1",v0.R1))}
    if data.sha(forecast_path.parent/"calibration-forecasts.npz")!=oof_audit["calibrationPredictionsSha256"]:
        raise ValueError("UNAUDITED_CALIBRATION")
    with np.load(forecast_path.parent/"calibration-forecasts.npz",allow_pickle=False) as z:
        calib={k:z[k] for k in z.files}
    calibration_metrics={short:forecast_metrics(calib,truth,ids,folds,arm,
                               partition="calibration",now_prices=now_prices)
                         for short,arm in (("IM",v0.IM),("R1",v0.R1))}
    names=[("FULL",k) for k in ctl.POLICIES]+[(ab,k) for ab in ("S","P") for k in ctl.POLICIES]
    calendars_all={};traces=[]
    for variant,policy in names:
        name=variant+"_"+policy
        calendars_all[name],trace=calendars(receipt,arrays,ids,groups,entries,raw,
                                             preds,variant,policy,set(days))
        traces.extend(trace)
    control={arm:r52.archive_control(arm) for arm in v0.ARMS}
    standalone=standalone_all_entries(calendars_all,control_exit,entries,evaluation,set(days))
    replays={};reports={"IM":{},"R1":{}};paired={"IM":{},"R1":{}}
    repeat_checks={}
    for arm in v0.ARMS:
        short="IM" if arm==v0.IM else "R1"
        subset={**cohort,"sessions":days}
        intent=v3.ranked_intents([x for x in intents[arm] if x["timestamp"][:10] in days],score[arm])
        slots=[("R50_A_CONTROL",control_exit[arm])]+[(name,cals[arm]) for name,cals in calendars_all.items()]
        for name,exit_calendar in slots:
            first=integrated.replay(arm,3,subset,intent,joined_raw,exit_calendar)
            second=integrated.replay(arm,3,subset,intent,joined_raw,exit_calendar)
            same=v0.canonical(first)==v0.canonical(second)
            if not same:raise ValueError("SAVED_FORECAST_REPLAY_NONDETERMINISTIC:"+name)
            if name=="R50_A_CONTROL" and v0.canonical(first)!=v0.canonical(control[arm]):
                raise ValueError("R50_ARCHIVED_CONTROL_BYTE_DRIFT")
            replays[short,name]=first;repeat_checks[short+"_"+name]=same
            report=r52.score(first,intent,evaluation[arm],labels[arm],original[0]["split"]["folds"],days)
            report["supplemental"]=audit52.supplemental(first,evaluation[arm],days)
            report["bucketsDetailed"]=detailed_buckets(first,evaluation[arm],r52.classify(first))
            reports[short][name]=report
            if name!="R50_A_CONTROL":
                paired[short][name]=r52.layer_a(control[arm],exit_calendar,evaluation[arm])
                report["currencyAttributionVsControl"]=r52.pnl_delta(control[arm],first)
            with (out/(short+"_"+name+"_ledger.json.gz")).open("xb") as fd:
                fd.write(gzip.compress(v0.canonical(first),mtime=0))
            curve=v1.curve(first)
            (out/(short+"_"+name+"_equity.json")).write_bytes(v0.canonical(curve))
            write_csv(out/(short+"_"+name+"_equity.csv"),curve,
                ("timestamp","equityJpy","cashJpy","grossExposureJpy","utilization","drawdownPct","equityValid"))
            write_csv(out/(short+"_"+name+"_daily.csv"),report["daily"],
                ("session","cashJpy","equityJpy","certified","dailyReturn"))
            (out/(short+"_"+name+"_buckets.json")).write_bytes(v0.canonical(report["bucketsDetailed"]))
    # The 0.10/0.20 pp fees are separate counterfactual controls, never edits
    # to the saved 0.05pp core ledger or prediction source.
    stress_results={}
    for fee in STRESS:
        for arm in v0.ARMS:
            short="IM" if arm==v0.IM else "R1"
            subset={**cohort,"sessions":days}
            intent=v3.ranked_intents([x for x in intents[arm] if x["timestamp"][:10] in days],score[arm])
            for name in ("R50_A_CONTROL","FULL_MH_WAIT15","FULL_MH_WAIT5"):
                cal=control_exit[arm] if name=="R50_A_CONTROL" else calendars_all[name][arm]
                with mock.patch.object(cash,"SELL_COST_PP",fee):
                    z=integrated.replay(arm,3,subset,intent,joined_raw,cal)
                dd,summ=integrated.daily(z,days)
                stress_results[f"{fee}|{short}|{name}"]={"finalEquityJpy":z["snapshots"][-1]["equityJpy"],
                    "certifiedDays":summ["validSessions"],"closedPnlJpy":str(sum(
                        (Decimal(r["realizedPnlJpy"]) for r in z["closed"]),Decimal(0)))}
    # Independently refitted D forecasts are actually passed through both
    # Controllers and the full event engine (four configurations).
    refit_identical={}
    for policy in ctl.POLICIES:
        cal,_=calendars(receipt,arrays,ids,groups,entries,raw,refit,"REFIT",policy,set(days))
        for arm in v0.ARMS:
            short="IM" if arm==v0.IM else "R1";name="FULL_"+policy
            intent=v3.ranked_intents([x for x in intents[arm] if x["timestamp"][:10] in days],score[arm])
            replay=integrated.replay(arm,3,{**cohort,"sessions":days},intent,joined_raw,cal[arm])
            refit_identical[short+"_"+policy]=v0.canonical(replay)==v0.canonical(replays[short,name])
    for arm in v0.ARMS:
        short="IM" if arm==v0.IM else "R1"
        fig,ax=plt.subplots(figsize=(11,4))
        for name in ("R50_A_CONTROL","FULL_MH_WAIT15","FULL_MH_WAIT5"):
            curve=v1.curve(replays[short,name])
            ax.plot([dt.datetime.fromisoformat(p["timestamp"]) for p in curve],
                [float(p["equityJpy"]) if p["equityJpy"] is not None else math.nan for p in curve],
                label=short+" "+name,linewidth=1)
        ax.set_title("Outcome-exposed Development: certified equity only")
        ax.set_ylabel("JPY; null gaps not connected")
        ax.grid(alpha=.3);ax.legend(fontsize=7);fig.autofmt_xdate();fig.tight_layout()
        fig.savefig(out/(short+"_asset_curve.png"),dpi=120);plt.close(fig)
    choice=frozen_gate(protocol,reports,paired,metrics["IM"],v0.IM,control[v0.IM],stress_results,
                       all(repeat_checks.values()),all(refit_identical.values()))
    (out/"scorecard.json").write_bytes(v0.canonical(reports))
    (out/"paired-layer-a.json").write_bytes(v0.canonical(paired))
    (out/"standalone-all-entries.json.gz").write_bytes(gzip.compress(v0.canonical(standalone),mtime=0))
    (out/"forecast-metrics.json").write_bytes(v0.canonical(metrics))
    (out/"calibration-diagnostics.json").write_bytes(v0.canonical(calibration_metrics))
    (out/"cost-stress.json").write_bytes(v0.canonical(stress_results))
    (out/"controller-trace.json.gz").write_bytes(gzip.compress(v0.canonical(traces),mtime=0))
    (out/"reproducibility.json").write_bytes(v0.canonical({"sameSavedForecast":repeat_checks,
                                                          "independentDRefits":refit_identical}))
    (out/"selection.json").write_bytes(v0.canonical(choice))
    (out/"manifest.json").write_bytes(v0.canonical({"filesSha256":{x.name:data.sha(x)
           for x in sorted(out.iterdir()) if x.is_file()},"integratedInvocations":44,
           "newModelFits":176,"protectedOpened":0,"providerRequests":0,"safety":v0.SAFETY}))
    print(v0.canonical({"phase":"FULL_FINITE_COMPLETE","selection":choice["selection"],
             "measurement":choice["measurement"],"IM_finalEquityJpy":
             {k:v["portfolio"]["finalEquityJpy"] for k,v in reports["IM"].items()}}).decode(),flush=True)


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--summary",type=Path,required=True)
    ap.add_argument("--labels",type=Path,required=True)
    ap.add_argument("--forecasts",type=Path,required=True)
    ap.add_argument("--refits",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    q=ap.parse_args();finite(q.source,q.summary,q.labels,q.forecasts,q.refits,q.out)
