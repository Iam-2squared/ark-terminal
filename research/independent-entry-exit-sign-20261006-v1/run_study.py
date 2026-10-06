"""Finite fixed comparison. No sign grading before phase predictions are sealed."""
import sys
import pickle
import warnings
from fractions import Fraction
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits
from sign_io import *
from sign_model import estimator, fit_preprocessing, transform, TRANSFORM_VERSION
from sign_policy import select_threshold, filter_action
from sign_metrics import evaluate, bootstrap, gate

QS=["0.8","0.9","0.7"]

def support(labels):
    return len(labels)>=100 and len({r["session"] for r in labels})>=10 and sum(r["y_plus"]==1 for r in labels)>=20 and sum(r["y_plus"]==0 for r in labels)>=20

def training_payload(fit,labels,numeric,categorical,family,parameters,cutoff):
    return {"numeric":numeric,"categorical":categorical,"family":family,"parameters":parameters,
        "preprocessing":TRANSFORM_VERSION,"sample_weight":None,"class_weight":None,"fit_cutoff":cutoff,
        "rows":[{"entry_id":r["entry_id"],"numeric":[r["numeric"][k] for k in numeric],
            "categorical":[r["categorical"][k] for k in categorical],"y_plus":labels[r["entry_id"]]["y_plus"],
            "label_maturity":labels[r["entry_id"]]["label_maturity"]} for r in fit]}

def verified_precommit():
    pre=read(OUT/"MODEL_PRECOMMIT.json")
    receipt=read(OUT/"PREFIT_READBACK.json")
    assert receipt["verified"] and receipt["precommit_sha256"]==sha(OUT/"MODEL_PRECOMMIT.json")
    assert pre["versions"]["sklearn"]==sklearn.__version__
    for name,h in pre["code_hashes"].items():
        assert sha(CODE/name)==h,"CODE_CHANGED_AFTER_PREFIT_LOCK"
    for name,h in pre["input_hashes"].items():
        assert sha(PRIVATE/name)==h,"INPUT_CHANGED_AFTER_PREFIT_LOCK"
    return pre

def subset_snapshot(row,spec):
    return {**row,"numeric":{k:row["numeric"][k] for k in spec["numeric"]},
        "categorical":{k:row["categorical"][k] for k in spec["categorical"]},
        "feature_schema_hash":digest({"numeric":spec["numeric"],"categorical":spec["categorical"],"version":TRANSFORM_VERSION})}

def run_trial(candidate,spec,family,b,phase,pre,target,metadata,snapshots):
    trial=f'{phase}_{candidate}_BLOCK_{b["block"]:02d}'
    marker=PRIVATE/"claims"/(trial+"_PREDICTIONS_IMMUTABLE.json")
    assert not marker.exists(),"TRIAL_ALREADY_EXECUTED"
    bydate={p:[r for r in snapshots if metadata[r["entry_id"]]["session"] in dates] for p,dates in b["dates"].items()}
    fit_labels={}
    for r in bydate["FIT"]:
        if metadata[r["entry_id"]]["execution_eligible"]:
            label=target.get(r["entry_id"],before=b["FIT_label_before"],purpose=trial+"_FIT")
            if label["y_plus"] is not None and label["label_maturity"]<b["FIT_label_before"]:
                fit_labels[r["entry_id"]]=label
    fit=[subset_snapshot(r,spec) for r in bydate["FIT"] if r["entry_id"] in fit_labels]
    cal=[]
    for r in bydate["CAL"]:
        if metadata[r["entry_id"]]["execution_eligible"]:
            label=target.get(r["entry_id"],before=b["CAL_label_before"],purpose=trial+"_CAL")
            if label["y_plus"] is not None and label["label_maturity"]<b["CAL_label_before"]:
                cal.append((subset_snapshot(r,spec),label))
    test=[subset_snapshot(r,spec) for r in bydate["TEST"]]
    parameters=pre["all_resolved_parameters"][family]
    payload=training_payload(fit,fit_labels,spec["numeric"],spec["categorical"],family,parameters,b["FIT_label_before"])
    signature=digest(payload)
    ledger=read(OUT/"FIT_LEDGER.json")
    equivalent=next((r for r in ledger["attempts"] if r["training_signature"]==signature and r["model_available"]),None)
    started=now();model_hash=None;warning_text=[];origin="UNAVAILABLE"
    path=PRIVATE/"models"/(signature+".pkl")
    if support(list(fit_labels.values())):
        if equivalent:
            with path.open("rb") as f:artifact=pickle.load(f)
            assert sha(path)==equivalent["model_hash"]
            prep=artifact["preprocessing"];model=artifact["model"];origin="REUSED_EQUIVALENT_NEW_CYCLE_FIT"
            ledger["equivalent_fits_reused"]+=1
        else:
            pre_key=digest({"numeric":spec["numeric"],"categorical":spec["categorical"],
                "rows":[{"entry_id":r["entry_id"],"numeric":r["numeric"],"categorical":r["categorical"]} for r in fit],
                "transform_version":TRANSFORM_VERSION})
            prep_path=PRIVATE/"preprocessing"/(pre_key+".json")
            if prep_path.exists():
                prep=read(prep_path)
            else:
                prep=fit_preprocessing(fit,spec["numeric"],spec["categorical"])
                save(prep_path,prep,exclusive=True);ledger["preprocessing_fits"]+=1
            x=transform(fit,prep);y=np.array([fit_labels[r["entry_id"]]["y_plus"] for r in fit],dtype=int)
            model=estimator(family,read(OUT/"DESIGN_CONFIG.json"))
            assert model.get_params()==parameters
            save(PRIVATE/"claims"/(trial+"_FIT_STARTED.json"),{"exact_jst":started,"training_signature":signature,
                "known_N":len(fit),"family":family,"sample_weight":None,"class_weight":None,"new_fit":True},exclusive=True)
            with warnings.catch_warnings(record=True) as caught:
                with threadpool_limits(limits=2):
                    model.fit(x,y)
            warning_text=[str(w.message) for w in caught]
            assert list(model.classes_)==[0,1],"CLASS_ORDER"
            artifact={"model":model,"preprocessing":prep,"training_signature":signature,
                "fit_entry_ids":[r["entry_id"] for r in fit],"label_maturity":[fit_labels[r["entry_id"]]["label_maturity"] for r in fit],
                "fit_cutoff":b["FIT_label_before"],"fit_last_session":b["dates"]["FIT"][-1],
                "feature_schema_hash":digest({"numeric":spec["numeric"],"categorical":spec["categorical"],"version":TRANSFORM_VERSION}),
                "versions":pre["versions"],"all_parameters":parameters}
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open("xb") as f:pickle.dump(artifact,f,protocol=5)
            ledger["new_fits"]+=1;origin="NEW_FIXED_RECIPE_FIT"
            gzsave(PRIVATE/"training_payloads"/(signature+".jsonl.gz"),payload["rows"])
        model_hash=sha(path)
        with threadpool_limits(limits=2):
            fit_prob=model.predict_proba(transform(fit,prep))[:,1]
            cal_prob=model.predict_proba(transform([r for r,_ in cal],prep))[:,1] if cal else []
        cal_rows=[{"entry_id":r["entry_id"],"session":label["session"],"y_plus":label["y_plus"],"p_plus":float(p)} for (r,label),p in zip(cal,cal_prob)]
    else:
        model=None;prep=None;fit_prob=[];cal_rows=[]
    # CAL snapshots are immutable before any current TEST prediction.
    thresholds={q:select_threshold(cal_rows,q) for q in QS}
    public_thresholds={}
    for q,t in thresholds.items():
        value={**t,"candidate":candidate,"block":b["block"],"phase":phase,"model_hash":model_hash,
            "fit_cutoff":b["FIT_label_before"],"cal_cutoff":b["CAL_label_before"],
            "cal_last_session":b["dates"]["CAL"][-1],"exact_jst":now(),"post_CAL_refit":False}
        f=PRIVATE/"thresholds"/(trial+"_Q"+q+".json");save(f,value,exclusive=True)
        t["threshold_hash"]=sha(f)
        public_thresholds[q]={**value,"threshold_hash":sha(f)}
    if model is not None:
        with threadpool_limits(limits=2):
            test_prob=model.predict_proba(transform(test,prep))[:,1]
    else:
        test_prob=[None]*len(test)
    predictions=[]
    for r,p in zip(test,test_prob):
        ok=r["availability_status"]=="HISTORICAL_ASSUMED_AVAILABILITY" and r["max_source_available_at"]<=r["decision_ts"]
        score=float(p) if p is not None and ok else None
        predictions.append({"entry_id":r["entry_id"],"decision_ts":r["decision_ts"],"session":metadata[r["entry_id"]]["session"],
            "block":b["block"],"phase":phase,"candidate":candidate,"p_plus":score,
            "predicted_sign":"ABSTAIN" if score is None else "PRED_PLUS" if score>=0.5 else "PRED_MINUS",
            "filter_action":filter_action(score,thresholds["0.8"]),"actions":{q:filter_action(score,t) for q,t in thresholds.items()},
            "availability_status":r["availability_status"] if score is not None else "ABSTAIN",
            "model_hash":model_hash,"threshold_hash":thresholds["0.8"]["threshold_hash"],
            "feature_schema_hash":r["feature_schema_hash"],"max_source_available_at":r["max_source_available_at"],
            "fit_cutoff":b["FIT_label_before"],"cal_cutoff":b["CAL_label_before"],
            "exposure_status":"LATE_DEV_LOCKED_CHECK / HISTORICALLY_EXPOSED" if phase=="LATE_DEV" else "DISCOVERY / HISTORICALLY_EXPOSED"})
    ppath=PRIVATE/"predictions"/(trial+".jsonl.gz")
    gzsave(ppath,predictions)
    gzsave(PRIVATE/"cal_predictions"/(trial+".jsonl.gz"),cal_rows)
    gzsave(PRIVATE/"fit_predictions"/(trial+".jsonl.gz"),[{"entry_id":r["entry_id"],"session":fit_labels[r["entry_id"]]["session"],
        "y_plus":fit_labels[r["entry_id"]]["y_plus"],"p_plus":float(p)} for r,p in zip(fit,fit_prob)])
    save(marker,{"exact_jst":now(),"prediction_sha256":sha(ppath),
        "threshold_hashes":{q:t["threshold_hash"] for q,t in thresholds.items()},
        "model_hash":model_hash,"current_TEST_signs_decoded_before_seal":0,"immutable":True},exclusive=True)
    rec={"trial":trial,"candidate":candidate,"block":b["block"],"phase":phase,"family":family,
        "origin":origin,"training_signature":signature,"model_hash":model_hash,"model_available":model is not None,
        "numeric_N":len(spec["numeric"]),"categorical_N":len(spec["categorical"]),
        "FIT_N":len(fit),"FIT_sessions":len({fit_labels[r["entry_id"]]["session"] for r in fit}),
        "FIT_PLUS":sum(r["y_plus"]==1 for r in fit_labels.values()),"FIT_MINUS":sum(r["y_plus"]==0 for r in fit_labels.values()),
        "CAL_N":len(cal),"FIT_dates":b["dates"]["FIT"],"CAL_dates":b["dates"]["CAL"],"TEST_dates":b["dates"]["TEST"],
        "fit_cutoff":b["FIT_label_before"],"cal_cutoff":b["CAL_label_before"],
        "post_CAL_refit_N":0,"TEST_update_N":0,"sample_weight":None,"class_weight":None,
        "FIT_missing_numeric_rate":sum(v is None for r in fit for v in r["numeric"].values())/(len(fit)*len(spec["numeric"])) if fit else None,
        "CAL_missing_numeric_rate":sum(v is None for r,_ in cal for v in r["numeric"].values())/(len(cal)*len(spec["numeric"])) if cal else None,
        "TEST_missing_numeric_rate":sum(v is None for r in test for v in r["numeric"].values())/(len(test)*len(spec["numeric"])) if test else None,
        "warnings":warning_text,"started_jst":started,"completed_jst":now(),
        "prediction_sha256":sha(ppath),"thresholds":public_thresholds}
    ledger["attempts"].append(rec);save(OUT/"FIT_LEDGER.json",ledger)
    with (OUT/"TRIAL_LEDGER.jsonl").open("a") as f:f.write(canonical(rec)+"\n")
    assert ledger["new_fits"]<=48 and ledger["technical_retries"]<=2
    print(canonical({"phase":phase,"candidate":candidate,"block":b["block"],"new_fits_total":ledger["new_fits"],
        "equivalent_reuse_total":ledger["equivalent_fits_reused"],"prediction_saved_before_TEST_grading":True}),flush=True)
    return predictions

def grade_phase(phase,candidates,predictions,target,metadata):
    save(PRIVATE/"claims"/(phase+"_ALL_PREDICTIONS_SEALED.json"),{"exact_jst":now(),
        "prediction_files":{p.name:sha(p) for p in (PRIVATE/"predictions").glob(phase+"_*.jsonl.gz")},
        "current_sign_grading_started":False},exclusive=True)
    signs={p["entry_id"]:target.get(p["entry_id"],purpose=phase+"_POST_SEAL_EVALUATION") for p in predictions}
    result={}
    for candidate in candidates:
        rr=[p for p in predictions if p["candidate"]==candidate]
        blocks=[{"block":b,"binary":evaluate([p for p in rr if p["block"]==b],signs,metadata,"binary"),
            "filters":{q:evaluate([p for p in rr if p["block"]==b],signs,metadata,q=q) for q in QS}}
            for b in sorted({p["block"] for p in rr})]
        attempts=[a for a in read(OUT/"FIT_LEDGER.json")["attempts"] if a["candidate"]==candidate and a["phase"]==phase]
        primary=evaluate(rr,signs,metadata)
        mean=float(np.mean([b["filters"]["0.8"]["balanced_accuracy"] for b in blocks]))
        worst=min(b["filters"]["0.8"]["balanced_accuracy"] for b in blocks)
        active=sum(a["thresholds"]["0.8"]["status"]=="ACTIVE" for a in attempts)
        result[candidate]={"binary":evaluate(rr,signs,metadata,"binary"),"filters":{q:evaluate(rr,signs,metadata,q=q) for q in QS},
            "blocks":blocks,"mean_block_filter_BA":mean,"minimum_block_filter_BA":worst,
            "active_filter_blocks":active,"eligible_for_selection":primary["prediction_coverage"]>=0.95 and active>=3,
            "CI":bootstrap(rr,signs,metadata),
            "sessions":[{"session":s,"binary":evaluate([p for p in rr if p["session"]==s],signs,metadata,"binary"),
                "filter":evaluate([p for p in rr if p["session"]==s],signs,metadata)} for s in sorted({p["session"] for p in rr})]}
    return result,signs

def main():
    phase=sys.argv[1];assert phase in ["discovery","late","ablation"]
    pre=verified_precommit();reg=read(OUT/"FEATURE_REGISTRY.json")
    blocks=read(OUT/"SPLIT_FIT_CAL_TEST.json")["blocks"]
    snapshots=rows(PRIVATE/"SNAPSHOTS.jsonl.gz")
    metadata={r["entry_id"]:r for r in rows(PRIVATE/"METADATA.jsonl.gz")}
    target=SignIndex(PRIVATE/"SIGN_TARGETS.jsonl.gz")
    candidates=pre["candidate_ids"] if phase=="discovery" else [read(OUT/"MODEL_SELECTION_LOCK.json")["selected_candidate"]]
    if phase=="late":
        lock=read(OUT/"MODEL_SELECTION_LOCK.json");receipt=read(OUT/"MODEL_SELECTION_READBACK.json")
        assert receipt["verified"] and receipt["lock_sha256"]==sha(OUT/"MODEL_SELECTION_LOCK.json")
        assert candidates[0] is not None
    if phase=="ablation":
        selected=candidates[0];rep,family=selected.split("_");base=reg["representations"][rep]
        candidates=["DROP_G_PRICE","DROP_G_STATE","DROP_G_SCORE"]
        specs={c:{"numeric":[k for k in base["numeric"] if k not in reg["groups"][c[5:]]],
            "categorical":[] if c=="DROP_G_STATE" else base["categorical"],"enabled":True} for c in candidates}
        if rep=="RAW":
            candidates.remove("DROP_G_SCORE")
    else:
        specs={c:reg["representations"][c.split("_")[0]] for c in candidates}
    selected_blocks=[b for b in blocks if b["block"] in ([6,7,8] if phase=="late" else [1,2,3,4,5])]
    allpred=[];label_phase={"discovery":"DISCOVERY","late":"LATE_DEV","ablation":"ABLATION"}[phase]
    for b in selected_blocks:
        for candidate in candidates:
            family=family if phase=="ablation" else candidate.split("_")[1]
            allpred+=run_trial(candidate,specs[candidate],family,b,label_phase,pre,target,metadata,snapshots)
    results,signs=grade_phase(label_phase,candidates,allpred,target,metadata)
    gzsave(PRIVATE/(label_phase+"_PREDICTIONS.jsonl.gz"),allpred)
    gzsave(PRIVATE/(label_phase+"_SIGN_READ_ACCESS_LOG.jsonl.gz"),target.read_log)
    if phase=="discovery":
        qualified=[c for c,r in results.items() if r["eligible_for_selection"]]
        def selection_key(c):
            r=results[c];ba=[b["filters"]["0.8"] for b in r["blocks"]]
            exact=[(Fraction(x["TP"],x["TP"]+x["FN"])+Fraction(x["TN"],x["TN"]+x["FP"]))/2 for x in ba]
            return (sum(exact)/len(exact),min(exact),r["filters"]["0.8"]["MCC"],-r["filters"]["0.8"]["Brier"],
                int(c.startswith("RAW_")),-["L","H","E"].index(c.split("_")[1]))
        chosen=max(qualified,key=selection_key) if qualified else None
        save(OUT/"DISCOVERY_RESULTS.json",{"status":"DISCOVERY_COMPLETE","results":results,"selected_candidate":chosen,
            "late_results_read_for_selection":False,"all_prediction_claims_sealed_before_grading":True})
        save(OUT/"MODEL_SELECTION_LOCK.json",{"exact_jst":now(),"selected_candidate":chosen,
            "status":"ONE_CANDIDATE_LOCKED" if chosen else "NO_QUALIFIED_FILTER","selection_rule":read(OUT/"DESIGN_CONFIG.json")["candidate_selection"],
            "qualified_candidates":qualified,"discovery_results_sha256":sha(OUT/"DISCOVERY_RESULTS.json"),
            "family_parameters":pre["all_resolved_parameters"][chosen.split("_")[1]] if chosen else None,
            "feature_spec":specs[chosen] if chosen else None,"registry_sha256":sha(OUT/"FEATURE_REGISTRY.json"),
            "threshold_procedure_sha256":sha(CODE/"sign_policy.py"),"q_primary":0.8,
            "late_blocks":[6,7,8],"late_candidate_count":1 if chosen else 0,"gate":read(OUT/"DESIGN_CONFIG.json")["promising_gate"],
            "no_candidate_exchange_after_lock":True,"late_status":"LATE_DEV_LOCKED_CHECK / HISTORICALLY_EXPOSED"})
        checkpoint("03_DISCOVERY_LOCKED","DISCOVERY_COMPLETE_CANDIDATE_LOCK_PENDING",
            ["all fixed discovery candidates measured","selection applied without late results"],["GitHub candidate lock/readback","late 3blocks","ablation","audit/report"],
            "save and read back the single selected candidate before any late fit")
    elif phase=="late":
        c=candidates[0];m=results[c]["filters"]["0.8"];per=[b["filters"]["0.8"] for b in results[c]["blocks"]]
        status,checks=gate(m,per,results[c]["CI"])
        save(OUT/"LATE_DEV_RESULTS.json",{"status":status,"candidate":c,"result":results[c],"gate_checks":checks,
            "exposure":"LATE_DEV_LOCKED_CHECK / HISTORICALLY_EXPOSED","fresh_or_holdout":False,
            "candidate_exchanges":0,"late_candidate_N":1,"all_three_prediction_blocks_saved_before_grading":True})
        checkpoint("04_LATE_COMPLETE",status,["single locked candidate measured in all3late blocks"],
            ["discovery-only ablation","independent audit","final report"],"complete fixed information-group diagnostics without changing the chosen candidate")
    else:
        save(OUT/"ABLATION_RESULTS.json",{"status":"COMPLETE_DISCOVERY_ONLY","selected_candidate":selected,"results":results,
            "DROP_G_SCORE":"same selected RAW candidate; no refit" if rep=="RAW" else results["DROP_G_SCORE"],
            "late_reselection":False,"ablation_blocks":[1,2,3,4,5]})
    thresholds={a["trial"]:a["thresholds"] for a in read(OUT/"FIT_LEDGER.json")["attempts"]}
    save(OUT/"THRESHOLD_SNAPSHOTS.json",thresholds)
    print(canonical({"phase_complete":phase,"candidate_N":len(candidates),"new_fits":read(OUT/"FIT_LEDGER.json")["new_fits"]}))

if __name__=="__main__":
    main()
