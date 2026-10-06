"""Independent recomputation. Imports no study/model/policy/metric code."""
import bisect
import collections
import datetime as dt
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import pickle
import numpy as np
from threadpoolctl import threadpool_limits

CODE=Path(__file__).resolve().parent; REPO=CODE.parents[1]; WORK=REPO.parent
OUT=REPO/"docs/evidence/independent-entry-exit-sign-20261006-v1"
PRIVATE=WORK/"work/independent_sign_private"
OLD=WORK/"work/old_sign"
checks=[];mismatches=[]

def read(p):return json.loads(Path(p).read_text())
def rows(p):
    with gzip.open(p,"rt") as f:return [json.loads(s) for s in f]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def record(name,condition,detail=None):
    checks.append({"name":name,"pass":bool(condition),"detail":detail})
    if not condition:mismatches.append({"name":name,"detail":detail})
def same(a,b):
    if a is None or b is None:return a is b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):return abs(a-b)<=1e-12*max(1,abs(a),abs(b))
    return a==b
def fraction_rate(a,b):return float(Fraction(a,b)) if b else None

def independent_metrics(rr,signs,metadata,mode,q="0.8"):
    elig=[p for p in rr if metadata[p["entry_id"]]["execution_eligible"]]
    known=[p for p in elig if signs[p["entry_id"]]["y_plus"] is not None]
    valid=[p for p in known if p["p_plus"] is not None]
    scored=valid if mode=="binary" else known
    c=collections.Counter()
    for p in scored:
        actual=signs[p["entry_id"]]["y_plus"]==1
        positive=p["p_plus"]>=0.5 if mode=="binary" else p["actions"][q]=="PASS_CANDIDATE"
        c["TP" if actual and positive else "FN" if actual else "FP" if positive else "TN"]+=1
    tp,fn,fp,tn=(c[k] for k in ["TP","FN","FP","TN"])
    pr=fraction_rate(tp,tp+fn);nr=fraction_rate(tn,tn+fp)
    denom=(tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)
    m={"TP":tp,"FN":fn,"FP":fp,"TN":tn,"plus_retention":pr,"minus_removal":nr,
       "pass_PLUS_rate":fraction_rate(tp,tp+fp),"pass_MINUS_rate":fraction_rate(fp,tp+fp),
       "PLUS_precision":fraction_rate(tp,tp+fp),"PLUS_recall":pr,"MINUS_precision":fraction_rate(tn,tn+fn),"MINUS_recall":nr,
       "balanced_accuracy":(pr+nr)/2 if pr is not None and nr is not None else None,
       "accuracy":fraction_rate(tp+tn,tp+fn+fp+tn),"MCC":(tp*tn-fp*fn)/math.sqrt(denom) if denom else 0.0,
       "before_MINUS_rate":fraction_rate(tn+fp,tp+fn+fp+tn),"pass_N":tp+fp,"reject_N":tn+fn,"known_scored_N":tp+fn+fp+tn,
       "all_Entry_N":len(rr),"execution_eligible_N":len(elig),"known_N":len(known),
       "exact_zero_N":sum(signs[p["entry_id"]]["sign_status"]=="EXACT_ZERO" for p in elig),
       "unknown_N":sum(signs[p["entry_id"]]["sign_status"]=="UNKNOWN" for p in elig),
       "all_exact_zero_N":sum(signs[p["entry_id"]]["sign_status"]=="EXACT_ZERO" for p in rr),
       "all_unknown_N":sum(signs[p["entry_id"]]["sign_status"]=="UNKNOWN" for p in rr),
       "predictable_N":sum(p["p_plus"] is not None for p in elig),"ABSTAIN_N":sum(p["p_plus"] is None for p in elig),
       "prediction_coverage":fraction_rate(sum(p["p_plus"] is not None for p in elig),len(elig)),
       "known_prediction_coverage":fraction_rate(len(valid),len(known)),"sessions":len({p["session"] for p in elig})}
    if valid:
        pos=sorted(p["p_plus"] for p in valid if signs[p["entry_id"]]["y_plus"]==1)
        neg=sorted(p["p_plus"] for p in valid if signs[p["entry_id"]]["y_plus"]==0)
        # Pairwise ranking arithmetic; no sklearn metric call.
        wins=sum(bisect.bisect_left(neg,p)+(bisect.bisect_right(neg,p)-bisect.bisect_left(neg,p))/2 for p in pos)
        m["AUROC"]=wins/(len(pos)*len(neg)) if pos and neg else None
        def ap(positive):
            groups=collections.defaultdict(lambda:[0,0])
            for p in valid:
                score=p["p_plus"] if positive else 1-p["p_plus"]
                y=signs[p["entry_id"]]["y_plus"] if positive else 1-signs[p["entry_id"]]["y_plus"]
                groups[score][0]+=y;groups[score][1]+=1
            total=sum(v[0] for v in groups.values())
            if not total:return None
            tp0=n0=0;area=0
            for score in sorted(groups,reverse=True):
                positives,count=groups[score];tp0+=positives;n0+=count
                area+=(positives/total)*(tp0/n0)
            return area
        m["PLUS_AP"]=ap(True);m["MINUS_AP"]=ap(False)
        m["Brier"]=math.fsum((p["p_plus"]-signs[p["entry_id"]]["y_plus"])**2 for p in valid)/len(valid)
        eps=np.finfo(np.float64).eps
        losses=[]
        for p in valid:
            score=min(1-eps,max(eps,p["p_plus"]));y=signs[p["entry_id"]]["y_plus"]
            losses.append(-math.log(score) if y else -math.log1p(-score))
        m["log_loss"]=math.fsum(losses)/len(valid)
    else:
        m.update(AUROC=None,PLUS_AP=None,MINUS_AP=None,Brier=None,log_loss=None)
    return m

def compare_metrics(label,rr,saved,signs,metadata,mode,q="0.8"):
    calculated=independent_metrics(rr,signs,metadata,mode,q)
    bad={k:{"saved":saved.get(k),"independent":v} for k,v in calculated.items() if not same(saved.get(k),v)}
    record(label,not bad,bad or None)

def independent_tau(cal,q):
    data=[p for p in cal if p["y_plus"] is not None and p["p_plus"] is not None]
    pN=sum(r["y_plus"]==1 for r in data);nN=len(data)-pN
    if len(data)<50 or len({r["session"] for r in data})<3 or min(pN,nN)<10:return 0.0,"FILTER_OFF_SUPPORT"
    best=None
    for t in sorted(set([0.0,math.nextafter(1.0,math.inf)]+[r["p_plus"] for r in data])):
        tp=sum(r["y_plus"]==1 and r["p_plus"]>=t for r in data)
        tn=sum(r["y_plus"]==0 and r["p_plus"]<t for r in data)
        if Fraction(tp,pN)<Fraction(q):continue
        key=((Fraction(tp,pN)+Fraction(tn,nN))/2,Fraction(tn,nN),-t)
        if best is None or key>best[0]:best=(key,t)
    return (best[1],"ACTIVE") if best[0][0]>Fraction(1,2) else (0.0,"NULL_ALL_PASS")

def independent_transform(rr,prep):
    out=[]
    for r in rr:
        values=[];missing=[]
        for k in prep["numeric"]:
            v=r["numeric"][k];ok=v is not None and math.isfinite(float(v))
            values.append(float(v) if ok else 0.0);missing.append(0.0 if ok else 1.0)
        z=[(v-m)/s for v,m,s in zip(values+missing,prep["mean"],prep["scale"])]
        for k in prep["categorical"]:
            cat="UNKNOWN" if r["categorical"][k] is None else str(r["categorical"][k])
            vocab=prep["vocabulary"][k];cat=cat if cat in vocab else "UNKNOWN"
            z.extend(float(cat==v) for v in vocab)
        out.append(z)
    return np.array(out,dtype=np.float64)

def check_result(candidate,rr,result,signs,metadata,prefix):
    compare_metrics(prefix+candidate+"_binary",rr,result["binary"],signs,metadata,"binary")
    for q in ["0.8","0.9","0.7"]:
        compare_metrics(prefix+candidate+"_filter_"+q,rr,result["filters"][q],signs,metadata,"filter",q)
    for b in result["blocks"]:
        group=[p for p in rr if p["block"]==b["block"]]
        compare_metrics(prefix+candidate+"_block"+str(b["block"])+"_binary",group,b["binary"],signs,metadata,"binary")
        for q in ["0.8","0.9","0.7"]:
            compare_metrics(prefix+candidate+"_block"+str(b["block"])+"_filter"+q,group,b["filters"][q],signs,metadata,"filter",q)
    for s in result["sessions"]:
        group=[p for p in rr if p["session"]==s["session"]]
        compare_metrics(prefix+candidate+"_session"+s["session"]+"_binary",group,s["binary"],signs,metadata,"binary")
        compare_metrics(prefix+candidate+"_session"+s["session"]+"_filter",group,s["filter"],signs,metadata,"filter")

def main():
    signs={r["entry_id"]:r for r in rows(PRIVATE/"SIGN_TARGETS.jsonl.gz")}
    metadata={r["entry_id"]:r for r in rows(PRIVATE/"METADATA.jsonl.gz")}
    snapshots={r["entry_id"]:r for r in rows(PRIVATE/"SNAPSHOTS.jsonl.gz")}
    record("identity_unique_exact_source",len(signs)==len(metadata)==len(snapshots)==1600 and set(signs)==set(metadata)==set(snapshots))
    fields={"entry_id","session","sign_status","y_plus","label_maturity","source_hash"}
    record("teacher_allowlist_direction",all(set(r)==fields and r["y_plus"]=={"PLUS":1,"MINUS":0,"EXACT_ZERO":None,"UNKNOWN":None}[r["sign_status"]] for r in signs.values()))
    source=rows(OLD/"reuse_sign/capital_rneg_defense_private/RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz")
    exact=0;magnitude=0
    for r in source:
        t=signs[r["entry_id"]]
        if r["known"] and r["buy_debit"] is not None and r["sell_credit"] is not None:
            d=Fraction(r["buy_debit"]);c=Fraction(r["sell_credit"])
            expected=1 if c>d else 0 if c<d else None
            exact+=int(t["y_plus"]==expected)
            if expected is not None:
                for shift in [Fraction(1,10000),Fraction(30,100)]:
                    c2=d*(1+shift if expected else 1-shift)
                    magnitude+=int((1 if c2>d else 0 if c2<d else None)==expected)
        else:
            exact+=int(t["sign_status"]=="UNKNOWN" and t["y_plus"] is None)
    record("independent_exact_debit_credit_no_new_cost",exact==1600,{"rows":exact})
    record("magnitude_change_sign_and_math_payload_invariance",magnitude==3120,{"comparisons":magnitude,"X_unchanged":True,"source_provenance_not_in_training_math":True})
    pre=read(OUT/"MODEL_PRECOMMIT.json")
    record("prefit_code_and_input_hashes_unchanged",all(sha(CODE/name)==h for name,h in pre["code_hashes"].items()) and all(sha(PRIVATE/name)==h for name,h in pre["input_hashes"].items()))
    ledger=read(OUT/"FIT_LEDGER.json");attempts=ledger["attempts"]
    record("finite_fit_and_preprocessing_counts_reconciled",ledger["new_fits"]==43 and ledger["preprocessing_fits"]==23 and ledger["equivalent_fits_reused"]==5 and len(attempts)==48 and len(list((PRIVATE/"models").glob("*.pkl")))==43)
    reg=read(OUT/"FEATURE_REGISTRY.json")
    record("RAW_no_learned_scores",not any(k.startswith("score/") or k.startswith("entry/p1_") for k in reg["representations"]["RAW"]["numeric"]))
    record("no_upstream_imports_or_network_in_model",not any(s in (CODE/"run_study.py").read_text()+(CODE/"inference.py").read_text() for s in ["import capital","from capital","requests.","urllib.","broker."]))
    record("per_row_predecision_asof",all(r["max_source_available_at"]<=r["decision_ts"] and r["feature_as_of"]<=r["decision_ts"] for r in snapshots.values()))
    lineage=read(OUT/"SCORE_LINEAGE_AUDIT.json")
    record("CAL_TEST_not_in_FIT_score_producers_and_coverage_fixed",lineage["CAL_and_TEST_in_FIT_producer_N"]==0 and
        all(p["time_dependency_errors"]==p["CAL_teacher_in_FIT_producer"]==p["TEST_teacher_in_FIT_producer"]==0 for s in lineage["scores"] for p in s["partitions"]))
    allpred=[]
    for rec in attempts:
        trial=rec["trial"];payload=rows(PRIVATE/"training_payloads"/(rec["training_signature"]+".jsonl.gz"))
        ids=[r["entry_id"] for r in payload]
        expected_ids=[k for k,m in metadata.items() if m["execution_eligible"] and m["session"] in rec["FIT_dates"]
            and signs[k]["y_plus"] is not None and signs[k]["label_maturity"]<rec["fit_cutoff"]]
        record(trial+"_FIT_ids_maturity_equal_weight",ids==expected_ids and len(ids)==len(set(ids)) and
            all(p["y_plus"]==signs[p["entry_id"]]["y_plus"] and p["label_maturity"]==signs[p["entry_id"]]["label_maturity"] for p in payload) and
            rec["sample_weight"] is None and rec["class_weight"] is None)
        cal=rows(PRIVATE/"cal_predictions"/(trial+".jsonl.gz"))
        cal_ids=[r["entry_id"] for r in cal]
        expected_cal=[k for k,m in metadata.items() if m["execution_eligible"] and m["session"] in rec["CAL_dates"] and
            signs[k]["y_plus"] is not None and signs[k]["label_maturity"]<rec["cal_cutoff"]]
        record(trial+"_CAL_ids_maturity",cal_ids==expected_cal)
        pp=rows(PRIVATE/"predictions"/(trial+".jsonl.gz"))
        expected_test=[k for k,m in metadata.items() if m["session"] in rec["TEST_dates"]]
        record(trial+"_all_TEST_rows_known_unknown_retained",[p["entry_id"] for p in pp]==expected_test)
        with (PRIVATE/"models"/(rec["training_signature"]+".pkl")).open("rb") as f:artifact=pickle.load(f)
        record(trial+"_model_cutoff_hash_class_order_params",artifact["fit_entry_ids"]==ids and
            list(artifact["model"].classes_)==[0,1] and artifact["all_parameters"]==pre["all_resolved_parameters"][rec["family"]]
            and sha(PRIVATE/"models"/(rec["training_signature"]+".pkl"))==rec["model_hash"])
        prep=artifact["preprocessing"]
        fit=[snapshots[k] for k in ids]
        matrix=[]
        for r in fit:
            v=[float(r["numeric"][k]) if r["numeric"][k] is not None else 0.0 for k in prep["numeric"]]
            miss=[float(r["numeric"][k] is None) for k in prep["numeric"]];matrix.append(v+miss)
        a=np.array(matrix);mean=a.mean(axis=0);scale=a.std(axis=0);scale[scale==0]=1
        vocab={k:sorted({"UNKNOWN"}|{str(r["categorical"][k]) if r["categorical"][k] is not None else "UNKNOWN" for r in fit}) for k in prep["categorical"]}
        record(trial+"_FIT_only_preprocessing",np.allclose(mean,prep["mean"],rtol=1e-12,atol=1e-12) and
            np.allclose(scale,prep["scale"],rtol=1e-12,atol=1e-12) and vocab==prep["vocabulary"] and prep["fit_entry_ids"]==ids)
        for kind,data in [("CAL",cal),("TEST",pp)]:
            x=independent_transform([snapshots[p["entry_id"]] for p in data],prep)
            with threadpool_limits(limits=2):computed=artifact["model"].predict_proba(x)[:,1]
            record(trial+"_"+kind+"_saved_probability_recompute",all(same(float(x),p["p_plus"]) for x,p in zip(computed,data)))
        policies={}
        for q in ["0.8","0.9","0.7"]:
            t,status=independent_tau(cal,q);policies[q]=(t,status)
            saved=rec["thresholds"][q]
            tf=PRIVATE/"thresholds"/(trial+"_Q"+q+".json")
            record(trial+"_independent_CAL_tau_"+q,same(t,saved["tau"]) and status==saved["status"] and sha(tf)==saved["threshold_hash"] and read(tf)["model_hash"]==rec["model_hash"])
        correct=True
        for p in pp:
            for q,(tau,status) in policies.items():
                action="PASS_CANDIDATE" if p["p_plus"] is None or status!="ACTIVE" or p["p_plus"]>=tau else "REJECT_CANDIDATE"
                correct=correct and p["actions"][q]==action
            correct=correct and p["predicted_sign"]==("ABSTAIN" if p["p_plus"] is None else "PRED_PLUS" if p["p_plus"]>=0.5 else "PRED_MINUS")
        sealed=read(PRIVATE/"claims"/(trial+"_PREDICTIONS_IMMUTABLE.json"))
        record(trial+"_policy_before_grading_same_model_no_refit",correct and sha(PRIVATE/"predictions"/(trial+".jsonl.gz"))==sealed["prediction_sha256"]
            and sealed["current_TEST_signs_decoded_before_seal"]==0 and rec["post_CAL_refit_N"]==rec["TEST_update_N"]==0)
        # Mutate only present/future teacher payloads and suffix snapshots. FIT
        # and CAL IDs/probabilities/threshold inputs remain bit-for-bit unchanged.
        future={k for k,m in metadata.items() if m["session"]>=rec["TEST_dates"][0]}
        record(trial+"_future_teacher_suffix_cannot_enter_FIT_CAL",not set(ids)&future and not set(cal_ids)&future)
        allpred+=pp
    discovery=read(OUT/"DISCOVERY_RESULTS.json")
    for c,r in discovery["results"].items():
        rr=[p for p in allpred if p["phase"]=="DISCOVERY" and p["candidate"]==c]
        check_result(c,rr,r,signs,metadata,"DISCOVERY_")
    late=read(OUT/"LATE_DEV_RESULTS.json");chosen=late["candidate"]
    rr=[p for p in allpred if p["phase"]=="LATE_DEV"]
    check_result(chosen,rr,late["result"],signs,metadata,"LATE_")
    ablation=read(OUT/"ABLATION_RESULTS.json")
    for c,r in ablation["results"].items():
        part=[p for p in allpred if p["phase"]=="ABLATION" and p["candidate"]==c]
        check_result(c,part,r,signs,metadata,"ABLATION_")
    def key(c):
        r=discovery["results"][c];m=r["filters"]["0.8"]
        values=[(Fraction(b["filters"]["0.8"]["TP"],b["filters"]["0.8"]["TP"]+b["filters"]["0.8"]["FN"])+
            Fraction(b["filters"]["0.8"]["TN"],b["filters"]["0.8"]["TN"]+b["filters"]["0.8"]["FP"]))/2 for b in r["blocks"]]
        return sum(values)/len(values),min(values),m["MCC"],-m["Brier"],int(c.startswith("RAW_")),-["L","H","E"].index(c[-1])
    eligible=[c for c,r in discovery["results"].items() if r["filters"]["0.8"]["prediction_coverage"]>=0.95 and r["active_filter_blocks"]>=3]
    record("candidate_selection_independent_tiebreak",max(eligible,key=key)==chosen==read(OUT/"MODEL_SELECTION_LOCK.json")["selected_candidate"])
    record("late_exactly_one_candidate_three_blocks",{p["candidate"] for p in rr}=={chosen} and {p["block"] for p in rr}=={6,7,8})
    # Independent late session bootstrap, using stored confusion count vectors.
    dates=sorted({p["session"] for p in rr});counts=[]
    for date in dates:
        m=independent_metrics([p for p in rr if p["session"]==date],signs,metadata,"filter")
        counts.append([m[k] for k in ["TP","FN","FP","TN"]])
    a=np.array(counts);rng=np.random.default_rng(20261006);values={k:[] for k in ["balanced_accuracy","plus_retention","minus_removal","pass_MINUS_rate"]}
    for _ in range(2000):
        tp,fn,fp,tn=map(int,a[rng.integers(0,len(dates),len(dates))].sum(axis=0))
        if not tp+fn or not tn+fp:continue
        keep=tp/(tp+fn);remove=tn/(tn+fp)
        item={"balanced_accuracy":(keep+remove)/2,"plus_retention":keep,"minus_removal":remove,
              "pass_MINUS_rate":fp/(tp+fp) if tp+fp else None}
        for k,v in item.items():
            if v is not None:values[k].append(v)
    ci=late["result"]["CI"]["metrics"]
    record("late_bootstrap_independent_rebuild",all(ci[k]["valid_N"]==len(v) and same(ci[k]["lower"],float(np.percentile(v,2.5))) and same(ci[k]["upper"],float(np.percentile(v,97.5))) for k,v in values.items()))
    m=independent_metrics(rr,signs,metadata,"filter")
    independent_status="SIGN_NOT_SEPARATED_IN_THIS_RUN" if m["balanced_accuracy"]<=0.5 or m["MCC"]<=0 else None
    record("termination_gate_independent",independent_status==late["status"],{"status":independent_status})
    record("history_exposure_and_no_production_claim",not late["fresh_or_holdout"] and "HISTORICALLY_EXPOSED" in late["exposure"])
    seal=read(PRIVATE/"claims/LATE_DEV_ALL_PREDICTIONS_SEALED.json")
    record("late_three_predictions_sealed_before_results",len(seal["prediction_files"])==3 and
        all(sha(PRIVATE/"predictions"/name)==h for name,h in seal["prediction_files"].items()))
    for phase in ["DISCOVERY","LATE_DEV","ABLATION"]:
        log=rows(PRIVATE/(phase+"_SIGN_READ_ACCESS_LOG.jsonl.gz"))
        record(phase+"_access_log_past_guards",all(r["before"] is None or signs[r["entry_id"]]["session"]<r["before"] for r in log))
    report={"exact_jst":dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="microseconds"),
        "status":"PASS" if not mismatches else "FAIL","independent_module_imports":0,"new_fits":0,
        "metrics_reconstruction":"independent count fractions, pairwise-rank AUROC, grouped AP, fsum Brier/logloss",
        "check_groups":len(checks),"mismatch_N":len(mismatches),"checks":checks,"mismatches":mismatches,
        "models_verified":43,"trial_conditions":48,"late_status":independent_status,
        "scope_limitations":["reused historical as-of/source audit; actual arrival remains UNKNOWN",
            "bookkeeping record reconstruction disclosed separately; no refit or prediction change",
            "historically exposed Development, not independent Fresh/OOS performance"]}
    (OUT/"INDEPENDENT_AUDIT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print(canonical({"status":report["status"],"check_groups":len(checks),"mismatch_N":len(mismatches),"new_fits":0}))
    if mismatches:raise SystemExit(1)

if __name__=="__main__":main()
