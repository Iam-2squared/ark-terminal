"""Known and worst-case rates, all-session supply, capture and uncertainty."""
from __future__ import annotations
from collections import Counter
from fractions import Fraction as F
from typing import Any
import math
import numpy as np
from .labels import Label
from .exact_math import V2Error
from .selection import joint
from .calibration import probability_matrix

Key=tuple[str,str,str]


def rate(n: int | float,d: int | float) -> float | None:
    return n/d if d else None


def summarize(sessions: list[str], selected: list[Key], labels: dict[Key,Label]) -> dict[str,Any]:
    if not sessions or sessions!=sorted(set(sessions)) or len(set(selected))!=len(selected) or any(k[0] not in sessions for k in selected):
        raise V2Error("EVALUATION_SESSION_OR_SELECTION_IDENTITY_MISMATCH")
    known=[]
    unknown=[]
    for k in selected:
        lab=labels.get(k)
        if lab is not None and lab.status=="KNOWN":
            known.append((k,lab))
        else:
            unknown.append(k)
    buckets=[0]*6
    raw=[0]*5;clean=[0]*5;losers=[0]*4
    close_buckets: Counter[str]=Counter()
    exact0=0
    for _,lab in known:
        assert lab.b is not None and lab.raw_winner is not None and lab.clean_winner is not None and lab.raw_loser is not None and lab.close_pct is not None
        buckets[lab.b]+=1
        exact0+=int(lab.exact_zero is True)
        for i in range(5):raw[i]+=int(lab.raw_winner[i]);clean[i]+=int(lab.clean_winner[i])
        for i in range(4):losers[i]+=int(lab.raw_loser[i])
        close_buckets[str(math.floor(lab.close_pct))]+=1
    n=len(selected);kn=len(known);un=len(unknown);days=len(sessions)
    day_table: list[dict[str,Any]]=[]
    for d in sessions:
        dk=[lab for k,lab in known if k[0]==d]
        dn=sum(k[0]==d for k in selected)
        cl3=sum(bool(l.clean_winner and l.clean_winner[2]) for l in dk)
        cl5=sum(bool(l.clean_winner and l.clean_winner[4]) for l in dk)
        day_table.append({"session":d,"selectedN":dn,"knownN":len(dk),"unknownN":dn-len(dk),
                          "clean3":cl3,"clean5":cl5,
                          "worst_low_pct":-float(max(l.adverse_pct for l in dk if l.adverse_pct is not None)) if dk else None,
                          "worst_close_pct":float(min(l.close_pct for l in dk if l.close_pct is not None)) if dk else None})
    no_candidates=sum(d["selectedN"]==0 for d in day_table)
    result: dict[str,Any]={"label_id":"JPX_RAW_OPEN_FULL_SESSION_UP_RISK_JOINT_V2","selectedN":n,"knownN":kn,"unknownN":un,
            "all_calendar_sessions":days,"up_buckets":buckets,"exact0_inside_B0":exact0,
            "signed_close_1pct_buckets":dict(close_buckets),"raw_winnerN":raw,"clean_winnerN":clean,"loserN_1_2_3_5":losers,
            "raw_winner_known_rates":[rate(v,kn) for v in raw],"raw_winner_all_selected_lower_rates":[rate(v,n) for v in raw],
            "clean_winner_known_rates":[rate(v,kn) for v in clean],"clean_winner_all_selected_lower_rates":[rate(v,n) for v in clean],
            "loser_known_rates":[rate(v,kn) for v in losers],"loser_observed_lower_rates":[rate(v,n) for v in losers],
            "loser_unknown_worst_upper_rates":[rate(v+un,n) for v in losers],
            "selected_unknown_rate":rate(un,n),"raw_winner_per_all_session":[v/days for v in raw],
            "clean_winner_per_all_session":[v/days for v in clean],"zero_candidate_days":no_candidates,
            "candidate_day_rate":(days-no_candidates)/days,"clean3_day_rate":sum(d["clean3"]>0 for d in day_table)/days,
            "clean5_day_rate":sum(d["clean5"]>0 for d in day_table)/days,"days":day_table,
            "symbol_concentration":dict(Counter(k[1] for k in selected)),
            "STATISTICAL_SUPPORT_ESTABLISHED":False,"LIVE_READINESS":"NOT_CERTIFIED"}
    result["POINT_TARGETS_MET"]=point_targets(result)
    return result


def point_targets(report: dict[str,Any]) -> bool:
    vals=(report["raw_winner_all_selected_lower_rates"][0],report["loser_unknown_worst_upper_rates"][2],
          report["loser_unknown_worst_upper_rates"][3],report["selected_unknown_rate"])
    if any(v is None for v in vals):
        return False
    return (vals[0]>=.5 and report["clean_winner_per_all_session"][2]>=1
            and report["clean_winner_per_all_session"][4]>=.5 and vals[1]<=.05
            and vals[2]<=.01 and vals[3]<=.01)


def capture(layers: dict[str,set[Key]], labels: dict[Key,Label]) -> dict[str,Any]:
    for a,b in (("g0","g2"),("g2","selected")):
        if not layers[b]<=layers[a]:
            raise V2Error("CAPTURE_LAYERS_NOT_NESTED")
    out={}
    for k in (1,3,5):
        def hit(key: Key) -> bool:
            lab=labels.get(key)
            return lab is not None and lab.clean_winner is not None and lab.clean_winner[k-1]
        counts={name:sum(hit(key) for key in keys) for name,keys in layers.items()}
        out[str(k)]={"GateRetention":rate(counts["g2"],counts["g0"]),"ModelCapture":rate(counts["selected"],counts["g2"]),"EndToEndCapture":rate(counts["selected"],counts["g0"]),"known_hit_counts":counts}
    return out


def exclusion_audit(excluded: dict[Key,tuple[str,...]], labels: dict[Key,Label]) -> dict[str,Any]:
    first: dict[str,dict[str,int]]={};all_reasons: dict[str,dict[str,int]]={}
    for key,reasons in excluded.items():
        lab=labels.get(key)
        for table,rs in ((first,reasons[:1]),(all_reasons,reasons)):
            for reason in rs:
                row=table.setdefault(reason,{"N":0,"unknownN":0,"raw5":0,"clean5":0,"loser5":0})
                row["N"]+=1
                if lab is None or lab.status!="KNOWN":row["unknownN"]+=1
                else:
                    row["raw5"]+=int(bool(lab.raw_winner and lab.raw_winner[4]))
                    row["clean5"]+=int(bool(lab.clean_winner and lab.clean_winner[4]))
                    row["loser5"]+=int(bool(lab.raw_loser and lab.raw_loser[3]))
    return {"exclusive_first_reason":first,"overlapping_all_reasons":all_reasons}


def bootstrap_days(day_rows: list[dict[str,int]], *, consecutive_window_verified: bool,
                   draws: int = 5000) -> dict[str,Any]:
    if not consecutive_window_verified or not day_rows or draws!=5000:
        raise V2Error("BOOTSTRAP_REQUIRES_FIXED_CONTINUOUS_EXCHANGE_WINDOW")
    for row in day_rows:
        if any(type(v) is not int or v<0 for v in row.values()) or "selectedN" not in row:
            raise V2Error("INVALID_BOOTSTRAP_DAY_COUNTS")
    definitions: dict[str,tuple[tuple[str,...],str]]={"observed_loser_rate":(("loserN",),"selectedN")}
    if all(set(("raw1N","clean3N","clean5N","loser3N","loser5N","unknownN"))<=set(row) for row in day_rows):
        definitions.update({"raw_winner1_lower_rate":(("raw1N",),"selectedN"),
            "clean3_per_all_session":(("clean3N",),"ALL_DAYS"),
            "clean5_per_all_session":(("clean5N",),"ALL_DAYS"),
            "loser3_unknown_worst_rate":(("loser3N","unknownN"),"selectedN"),
            "loser5_unknown_worst_rate":(("loser5N","unknownN"),"selectedN"),
            "selected_unknown_rate":(("unknownN",),"selectedN")})
    if not all("loserN" in row for row in day_rows):
        definitions.pop("observed_loser_rate")
    if not definitions:raise V2Error("BOOTSTRAP_METRIC_COUNTS_REQUIRED")
    rng=np.random.default_rng(20261014)
    n=len(day_rows)
    samples: dict[str,list[float]]={name:[] for name in definitions}
    undefined={name:0 for name in definitions}
    for _ in range(draws):
        indices: list[int]=[]
        while len(indices)<n:
            start=int(rng.integers(n))
            indices.extend((start+j)%n for j in range(5))
        rows=[day_rows[i] for i in indices[:n]]
        for name,(numerators,denominator_name) in definitions.items():
            denominator=n if denominator_name=="ALL_DAYS" else sum(r[denominator_name] for r in rows)
            if denominator==0:
                undefined[name]+=1
                continue
            numerator=sum(sum(r[k] for k in numerators) for r in rows)
            samples[name].append(numerator/denominator)
    intervals={name:{"descriptive_interval":np.quantile(values,[.025,.975]).tolist() if values else None,
                     "undefined_draws":undefined[name],"undefined_fraction":undefined[name]/draws}
               for name,values in samples.items()}
    primary=intervals.get("observed_loser_rate",next(iter(intervals.values())))
    return {"draws":draws,"block_sessions":5,"seed":20261014,**primary,"metrics":intervals,
            "zero_observed_tail_is_zero_true_risk":False,"STATISTICAL_SUPPORT_ESTABLISHED":False}


def binary_diagnostics(p: np.ndarray, y: np.ndarray, sessions: list[str], bins: list[float],
                       weights: np.ndarray | None = None) -> dict[str,Any]:
    if len(p)!=len(y) or len(p)!=len(sessions) or len(p)==0 or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise V2Error("INVALID_PROBABILITY_DIAGNOSTIC_INPUT")
    w=np.ones(len(p),dtype=np.float64) if weights is None else weights
    if not np.isfinite(w).all() or np.any(w<=0):
        raise V2Error("INVALID_DIAGNOSTIC_WEIGHT")
    bounded=np.maximum(np.minimum(p,1-1e-15),1e-15)  # NLL only; never selection.
    table=[]
    for i,(left,right) in enumerate(zip(bins[:-1],bins[1:])):
        mask=(p>=left)&((p<=right) if i==len(bins)-2 else (p<right))
        count=int(mask.sum())
        table.append({"left":left,"right":right,"right_inclusive":i==len(bins)-2,"N":count,
                      "days":len({sessions[j] for j in np.flatnonzero(mask)}),
                      "mean_p":float(np.average(p[mask],weights=w[mask])) if count else None,
                      "observed_rate":float(np.average(y[mask],weights=w[mask])) if count else None,
                      "support":"INSUFFICIENT_SUPPORT" if count<10 else "DESCRIPTIVE_ONLY"})
    return {"brier":float(np.average((p-y)**2,weights=w)),
            "log_loss":float(np.average(-y*np.log(bounded)-(1-y)*np.log1p(-bounded),weights=w)),
            "estimand":"DAY_UNIFORM_WEIGHTED" if weights is not None else "UNWEIGHTED_REAL_SELECTION",
            "bins":table,"probability_tail_certified":False}


def probability_diagnostics(a: np.ndarray,b: np.ndarray,risk: np.ndarray,opportunity: np.ndarray,
                            sessions: list[str],weights: np.ndarray | None = None) -> dict[str,Any]:
    a=probability_matrix(a,3);b=probability_matrix(b,6)
    if len(a)!=len(risk) or len(b)!=len(opportunity) or len(a)!=len(sessions):
        raise V2Error("PROBABILITY_DIAGNOSTIC_TEACHER_MISMATCH")
    known=risk>=0;r0=risk==0
    if not known.any():return {"status":"NOT_MEASURED"}
    w=np.ones(len(a)) if weights is None else weights
    q,p3,p5=joint(a[known],b[known])
    ss=[sessions[j] for j in np.flatnonzero(known)]
    ws=w[known] if weights is not None else None
    out: dict[str,Any]={"risk_nll":float(np.average(-np.log(np.maximum(a[known][np.arange(known.sum()),risk[known]],1e-15)),weights=w[known])),
         "opportunity_R0_nll":float(np.average(-np.log(np.maximum(b[r0][np.arange(r0.sum()),opportunity[r0]],1e-15)),weights=w[r0])) if r0.any() else None,
         "binary":{},"conditionalOnOutcomeKnown":True}
    for k in range(1,6):
        y=((risk[known]==0)&(opportunity[known]>=k)).astype(float)
        out["binary"][f"q{k}"]=binary_diagnostics(q[:,k-1],y,ss,[j/10 for j in range(11)],ws)
    for name,p,limit in (("p3",p3,1),("p5",p5,2)):
        out["binary"][name]=binary_diagnostics(p,(risk[known]>=limit).astype(float),ss,[0,.01,.025,.05,.10,.20,.50,1],ws)
    return out


def public_suppression(partition: dict[str,int]) -> dict[str,Any]:
    # Suppress the complete partition (including its total) when ANY small
    # cell could be reconstructed by subtraction. Public market row release
    # remains separately prohibited.
    if any(0<n<10 for n in partition.values()):
        return {"suppressed":True,"reason":"SMALL_CELL_COMPLEMENTARY_SUPPRESSION"}
    return {"suppressed":False,"partition":partition}
