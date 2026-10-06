"""Post-lock sign-only baselines and learning/subset summaries, with zero fits."""
import copy
from sign_io import *
from sign_policy import select_threshold, filter_action
from sign_metrics import evaluate

def aggregate(rr,signs,metadata):
    return {"binary":evaluate(rr,signs,metadata,"binary"),"filter":evaluate(rr,signs,metadata)}

def main():
    assert (OUT/"LATE_DEV_RESULTS.json").exists() and (OUT/"ABLATION_RESULTS.json").exists()
    selected=read(OUT/"MODEL_SELECTION_LOCK.json")["selected_candidate"]
    signs={r["entry_id"]:r for r in rows(PRIVATE/"SIGN_TARGETS.jsonl.gz")}
    metadata={r["entry_id"]:r for r in rows(PRIVATE/"METADATA.jsonl.gz")}
    mainpred=[r for phase in ["DISCOVERY","LATE_DEV"] for r in rows(PRIVATE/(phase+"_PREDICTIONS.jsonl.gz")) if r["candidate"]==selected]
    ledger=read(OUT/"FIT_LEDGER.json")["attempts"]
    block_records={r["block"]:r for r in ledger if r["candidate"]==selected and r["phase"]!="ABLATION"}
    baselines={x:[] for x in ["B0","ALL_PLUS","ALL_MINUS","FIT_MAJORITY"]}
    learning=[];baseline_policies={}
    for b,rec in sorted(block_records.items()):
        tr=rows(PRIVATE/"training_payloads"/(rec["training_signature"]+".jsonl.gz"))
        prior=sum(r["y_plus"] for r in tr)/len(tr)
        cal=rows(PRIVATE/"cal_predictions"/(rec["trial"]+".jsonl.gz"))
        policies={q:select_threshold([{**r,"p_plus":prior} for r in cal],q) for q in ["0.8","0.9","0.7"]}
        baseline_policies[str(b)]=policies
        for p in [p for p in mainpred if p["block"]==b]:
            for name,score in [("B0",prior),("ALL_PLUS",1.0),("ALL_MINUS",0.0),("FIT_MAJORITY",float(prior>=0.5))]:
                baselines[name].append({**p,"candidate":name,"p_plus":score,
                    "predicted_sign":"PRED_PLUS" if score>=0.5 else "PRED_MINUS",
                    "actions":{q:filter_action(score,policies[q]) for q in policies},
                    "filter_action":filter_action(score,policies["0.8"])})
        for partition,directory in [("FIT","fit_predictions"),("CAL","cal_predictions")]:
            raw=rows(PRIVATE/directory/(rec["trial"]+".jsonl.gz"))
            preds=[{**p,"actions":{q:filter_action(p["p_plus"],rec["thresholds"][q]) for q in ["0.8","0.9","0.7"]}} for p in raw]
            learning.append({"block":b,"partition":partition,"N":len(preds),**aggregate(preds,signs,metadata)})
        preds=[p for p in mainpred if p["block"]==b]
        learning.append({"block":b,"partition":"TEST","N":len(preds),**aggregate(preds,signs,metadata),
            "missing_rates":{part:rec[part+"_missing_numeric_rate"] for part in ["FIT","CAL","TEST"]}})
    reference=rows(OLD/"capital_sign_only_private/REFERENCE_OOF.jsonl.gz")
    current_byid={p["entry_id"]:p for p in mainpred}
    old_pred={name:[] for name in ["HL0","OLD_D1","OLD_D2"]}
    for p in reference:
        if p["recipe"] in old_pred:
            old_pred[p["recipe"]].append({**current_byid[p["entry_id"]],"candidate":p["recipe"],
                "p_plus":1-p["score_neg"] if p["model_prediction_valid"] else None})
    old_stage_pred=rows(OLD/"capital_sign_only_private/INITIAL_OOF_PREDICTIONS.jsonl.gz")
    old_actions=rows(OLD/"capital_sign_only_private/SIGN_FILTER_ACTIONS.jsonl.gz")
    action_map={p["entry_id"]:p for p in old_actions if p["recipe"]=="SF_D_UNION" and p["alpha"]=="0.10"}
    stage=[]
    for p in old_stage_pred:
        if p["recipe"]=="SF_D_UNION":
            a=action_map[p["entry_id"]]
            assert a["action"] in {"PASS","PASS_UNASSESSED_OFF","PASS_UNASSESSED_INELIGIBLE","REJECT"}
            action="PASS_CANDIDATE" if a["action"].startswith("PASS") else "REJECT_CANDIDATE"
            stage.append({**current_byid[p["entry_id"]],"candidate":"OLD_STAGE1_UNION_PRIMARY",
                "p_plus":1-p["score_neg"] if p["model_prediction_valid"] else None,
                "actions":{"0.8":action},"filter_action":action})
    intervals={"DISCOVERY":[1,2,3,4,5],"LATE_DEV_LOCKED_CHECK":[6,7,8],"SELECTED_OOF_ALL":[1,2,3,4,5,6,7,8]}
    result={}
    for interval,bs in intervals.items():
        result[interval]={"baselines":{name:aggregate([p for p in pred if p["block"] in bs],signs,metadata)
            for name,pred in baselines.items()},
            "legacy_probability_references":{name:{"binary":evaluate([p for p in pred if p["block"] in bs],signs,metadata,"binary")}
                for name,pred in old_pred.items()},
            "old_stage1":aggregate([p for p in stage if p["block"] in bs],signs,metadata)}
    assert result["SELECTED_OOF_ALL"]["old_stage1"]["filter"]["TP"]==447
    assert result["SELECTED_OOF_ALL"]["old_stage1"]["filter"]["TN"]==26
    save(OUT/"BASELINE_AND_LEGACY_COMPARISON.json",{"status":"COMPLETE_ZERO_FITS","results":result,
        "B0_policies":baseline_policies,"B0_training":"same matured eligible FIT prefix; CAL/TEST excluded",
        "legacy_limitation":"saved HL0/D1/D2 and old stage1 include CAL dates in training and different representations/policies; not identical training-condition comparisons",
        "fixed_binary_ALL_PLUS_MINUS_MAJORITY_filter":"only B0 receives meaningful CAL procedure; fixed binary rows are reference labels"})
    gzsave(PRIVATE/"BASELINE_PREDICTIONS.jsonl.gz",[p for rr in baselines.values() for p in rr])
    gzsave(PRIVATE/"LEGACY_REFERENCE_PREDICTIONS.jsonl.gz",[p for rr in old_pred.values() for p in rr]+stage)
    save(OUT/"LEARNING_DIAGNOSTICS.json",{"status":"COMPLETE_ZERO_FITS","rows":learning,"selected_candidate":selected})
    membership={r["entry_id"]:r for r in rows(OLD/"capital_sign_only_private/AUXILIARY_MEMBERSHIP.jsonl.gz")}
    auxiliary={}
    for interval,bs in intervals.items():
        auxiliary[interval]={name:aggregate([p for p in mainpred if p["block"] in bs and membership[p["entry_id"]][key]],signs,metadata)
            for name,key in [("RANK_PASS","rank_pass"),("OLD_V5_PURCHASED","old_V5_purchased")]}
    save(OUT/"AUXILIARY_SUBSETS.json",{"status":"POST_LOCK_DIAGNOSTIC_ONLY","results":auxiliary,
        "used_for_selection_or_gate":False,"second_layer_learning_or_Capital_connection":0})
    gzsave(PRIVATE/"FIRST_PREDICTIONS.jsonl.gz",rows(PRIVATE/"DISCOVERY_PREDICTIONS.jsonl.gz")+rows(PRIVATE/"LATE_DEV_PREDICTIONS.jsonl.gz"))
    print(canonical({"baseline_model_fits":0,"reference_refits":0,"learning_rows":len(learning),"legacy_primary_counts_match":True}))

if __name__=="__main__":
    main()
