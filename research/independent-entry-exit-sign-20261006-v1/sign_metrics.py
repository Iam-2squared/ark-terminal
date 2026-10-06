"""Sign-only evaluation; every confusion cell is one Entry, equally weighted."""
import math
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, log_loss

def ratio(a, b):
    return a / b if b else None

def cells_metrics(tp, fn, fp, tn):
    keep = ratio(tp, tp+fn); remove = ratio(tn, tn+fp)
    denom = (tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)
    return {"TP":tp,"FN":fn,"FP":fp,"TN":tn,
        "plus_retention":keep,"minus_removal":remove,
        "pass_PLUS_rate":ratio(tp,tp+fp),"pass_MINUS_rate":ratio(fp,tp+fp),
        "PLUS_precision":ratio(tp,tp+fp),"PLUS_recall":keep,
        "MINUS_precision":ratio(tn,tn+fn),"MINUS_recall":remove,
        "balanced_accuracy":(keep+remove)/2 if keep is not None and remove is not None else None,
        "accuracy":ratio(tp+tn,tp+fn+fp+tn),
        "MCC":(tp*tn-fp*fn)/math.sqrt(denom) if denom else 0.0,
        "before_MINUS_rate":ratio(tn+fp,tp+fn+fp+tn),
        "pass_N":tp+fp,"reject_N":tn+fn,"known_scored_N":tp+fn+fp+tn}

def evaluate(predictions, signs, metadata, mode="filter", q="0.8"):
    eligible=[p for p in predictions if metadata[p["entry_id"]]["execution_eligible"]]
    known=[p for p in eligible if signs[p["entry_id"]]["y_plus"] is not None]
    valid=[p for p in known if p["p_plus"] is not None]
    scored=valid if mode=="binary" else known
    cells={"TP":0,"FN":0,"FP":0,"TN":0}
    for p in scored:
        y=signs[p["entry_id"]]["y_plus"]
        positive=(p["p_plus"]>=0.5) if mode=="binary" else (p["actions"][q]=="PASS_CANDIDATE")
        cells["TP" if y==1 and positive else "FN" if y==1 else "FP" if positive else "TN"]+=1
    out=cells_metrics(**{k.lower():v for k,v in cells.items()})
    out.update(all_Entry_N=len(predictions),execution_eligible_N=len(eligible),known_N=len(known),
        exact_zero_N=sum(signs[p["entry_id"]]["sign_status"]=="EXACT_ZERO" for p in eligible),
        unknown_N=sum(signs[p["entry_id"]]["sign_status"]=="UNKNOWN" for p in eligible),
        all_exact_zero_N=sum(signs[p["entry_id"]]["sign_status"]=="EXACT_ZERO" for p in predictions),
        all_unknown_N=sum(signs[p["entry_id"]]["sign_status"]=="UNKNOWN" for p in predictions),
        predictable_N=sum(p["p_plus"] is not None for p in eligible),
        ABSTAIN_N=sum(p["p_plus"] is None for p in eligible),
        prediction_coverage=ratio(sum(p["p_plus"] is not None for p in eligible),len(eligible)),
        known_prediction_coverage=ratio(len(valid),len(known)),sessions=len({p["session"] for p in eligible}),
        mode=mode,q=float(q) if mode=="filter" else None,
        raw_ABSTAIN_not_correct=True,filter_ABSTAIN_passed=(mode=="filter"))
    if valid:
        y=np.array([signs[p["entry_id"]]["y_plus"] for p in valid])
        score=np.array([p["p_plus"] for p in valid],dtype=float)
        both=len(set(y.tolist()))==2
        out.update(AUROC=float(roc_auc_score(y,score)) if both else None,
            PLUS_AP=float(average_precision_score(y,score)) if sum(y)==len(y) or sum(y)>0 else None,
            MINUS_AP=float(average_precision_score(1-y,1-score)) if sum(y)<len(y) else None,
            Brier=float(np.mean((score-y)**2)),log_loss=float(log_loss(y,score,labels=[0,1])))
    else:
        out.update(AUROC=None,PLUS_AP=None,MINUS_AP=None,Brier=None,log_loss=None)
    return out

def bootstrap(predictions, signs, metadata, repeats=2000, seed=20261006):
    dates=sorted({p["session"] for p in predictions})
    counts=[]
    for date in dates:
        m=evaluate([p for p in predictions if p["session"]==date],signs,metadata)
        counts.append([m[k] for k in ["TP","FN","FP","TN"]])
    a=np.array(counts,dtype=int)
    generator=np.random.default_rng(seed)
    values={k:[] for k in ["balanced_accuracy","plus_retention","minus_removal","pass_MINUS_rate"]}
    for _ in range(repeats):
        indices=generator.integers(0,len(dates),len(dates))
        tp,fn,fp,tn=map(int,a[indices].sum(axis=0))
        if not tp+fn or not tn+fp:
            continue
        m=cells_metrics(tp,fn,fp,tn)
        for k in values:
            if m[k] is not None:
                values[k].append(m[k])
    result={k:{"valid_N":len(v),"NA_N":repeats-len(v),"status":"PASS" if len(v)>=0.95*repeats else "CI_INSUFFICIENT",
        "lower":float(np.percentile(v,2.5)) if len(v)>=0.95*repeats else None,
        "upper":float(np.percentile(v,97.5)) if len(v)>=0.95*repeats else None} for k,v in values.items()}
    return {"unit":"session","sessions":dates,"repeats":repeats,"seed":seed,"metrics":result,"new_fits":0,
        "limitations":"historically exposed Development; does not correct model selection, repeated exposure, or all temporal dependence"}

def gate(metrics, blocks, ci):
    if metrics["balanced_accuracy"] is None:
        return "SIGN_SIGNAL_LIMITED",{"scoring_support":False}
    if metrics["balanced_accuracy"]<=0.5 or metrics["MCC"]<=0:
        return "SIGN_NOT_SEPARATED_IN_THIS_RUN",{"BA_above_half":metrics["balanced_accuracy"]>0.5,"MCC_positive":metrics["MCC"]>0}
    checks={"plus_retention_ge80":metrics["plus_retention"]>=0.8,"minus_removal_ge40":metrics["minus_removal"]>=0.4,
        "BA_ge60":metrics["balanced_accuracy"]>=0.6,"MCC_positive":metrics["MCC"]>0,
        "coverage_ge95":metrics["prediction_coverage"]>=0.95,
        "blocks_BA_above_half_ge2":sum(b["balanced_accuracy"] is not None and b["balanced_accuracy"]>0.5 for b in blocks)>=2,
        "known_ge100":metrics["known_N"]>=100,"each_class_ge30":metrics["TP"]+metrics["FN"]>=30 and metrics["TN"]+metrics["FP"]>=30,
        "sessions_ge10":metrics["sessions"]>=10,
        "bootstrap_BA_lower_above_half":ci["metrics"]["balanced_accuracy"]["lower"] is not None and ci["metrics"]["balanced_accuracy"]["lower"]>0.5}
    return ("SIGN_LOCKED_DEV_PROMISING_UNCONFIRMED" if all(checks.values()) else "SIGN_SIGNAL_LIMITED"),checks

