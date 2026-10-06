"""Restore a lost bookkeeping record from immutable model/prediction artifacts."""
import pickle
from sign_io import *

def main():
    ledger=read(OUT/"FIT_LEDGER.json")
    model_files=list((PRIVATE/"models").glob("*.pkl"))
    missing=[p for p in (PRIVATE/"claims").glob("*_FIT_STARTED.json")
             if read(p)["training_signature"] not in {r["training_signature"] for r in ledger["attempts"]}]
    assert len(missing)==1 and missing[0].name=="LATE_DEV_AUG_L_BLOCK_08_FIT_STARTED.json"
    claim=read(missing[0]);signature=claim["training_signature"]
    model_path=PRIVATE/"models"/(signature+".pkl")
    with model_path.open("rb") as f:artifact=pickle.load(f)
    assert artifact["training_signature"]==signature
    trial="LATE_DEV_AUG_L_BLOCK_08"
    sealed=read(PRIVATE/"claims"/(trial+"_PREDICTIONS_IMMUTABLE.json"))
    predictions=PRIVATE/"predictions"/(trial+".jsonl.gz")
    assert sha(predictions)==sealed["prediction_sha256"] and sha(model_path)==sealed["model_hash"]
    b=next(r for r in read(OUT/"SPLIT_FIT_CAL_TEST.json")["blocks"] if r["block"]==8)
    schema=read(OUT/"MODEL_SELECTION_LOCK.json")["feature_spec"]
    snaps={r["entry_id"]:r for r in rows(PRIVATE/"SNAPSHOTS.jsonl.gz")}
    targets={r["entry_id"]:r for r in rows(PRIVATE/"SIGN_TARGETS.jsonl.gz")}
    metadata={r["entry_id"]:r for r in rows(PRIVATE/"METADATA.jsonl.gz")}
    fit=[snaps[k] for k in artifact["fit_entry_ids"]]
    cal=rows(PRIVATE/"cal_predictions"/(trial+".jsonl.gz"))
    test=[snaps[r["entry_id"]] for r in rows(predictions)]
    assert all(targets[r["entry_id"]]["label_maturity"]<b["FIT_label_before"] for r in fit)
    assert all(metadata[r["entry_id"]]["session"] in b["dates"]["FIT"] for r in fit)
    thresholds={}
    for q in ["0.8","0.9","0.7"]:
        path=PRIVATE/"thresholds"/(trial+"_Q"+q+".json")
        assert sha(path)==sealed["threshold_hashes"][q]
        thresholds[q]={**read(path),"threshold_hash":sha(path)}
    missing_rate=lambda rr:sum(r["numeric"][k] is None for r in rr for k in schema["numeric"])/(len(rr)*len(schema["numeric"]))
    rec={"trial":trial,"candidate":"AUG_L","block":8,"phase":"LATE_DEV","family":"L",
        "origin":"NEW_FIXED_RECIPE_FIT","training_signature":signature,"model_hash":sha(model_path),"model_available":True,
        "numeric_N":len(schema["numeric"]),"categorical_N":len(schema["categorical"]),"FIT_N":len(fit),
        "FIT_sessions":len({metadata[r["entry_id"]]["session"] for r in fit}),
        "FIT_PLUS":sum(targets[r["entry_id"]]["y_plus"]==1 for r in fit),
        "FIT_MINUS":sum(targets[r["entry_id"]]["y_plus"]==0 for r in fit),
        "CAL_N":len(cal),"FIT_dates":b["dates"]["FIT"],"CAL_dates":b["dates"]["CAL"],"TEST_dates":b["dates"]["TEST"],
        "fit_cutoff":b["FIT_label_before"],"cal_cutoff":b["CAL_label_before"],
        "post_CAL_refit_N":0,"TEST_update_N":0,"sample_weight":None,"class_weight":None,
        "FIT_missing_numeric_rate":missing_rate(fit),"CAL_missing_numeric_rate":missing_rate([snaps[r["entry_id"]] for r in cal]),
        "TEST_missing_numeric_rate":missing_rate(test),
        "warnings":None,"started_jst":claim["exact_jst"],"completed_jst":sealed["exact_jst"],
        "prediction_sha256":sha(predictions),"thresholds":thresholds,
        "record_reconstructed":True,"completed_jst_semantics":"immutable prediction seal timestamp; original ledger-write timestamp unavailable"}
    before={"new_fits":ledger["new_fits"],"preprocessing_fits":ledger["preprocessing_fits"],"attempt_N":len(ledger["attempts"])}
    # Preserve both observed ledgers. No fitted/predicted/target/selection
    # artifact is changed by this repair, and no training is invoked.
    save(PRIVATE/"repair/OBSERVED_FIT_LEDGER.json",ledger,exclusive=True)
    (PRIVATE/"repair").mkdir(exist_ok=True)
    (PRIVATE/"repair/OBSERVED_TRIAL_LEDGER.jsonl").write_bytes((OUT/"TRIAL_LEDGER.jsonl").read_bytes())
    ledger["attempts"].append(rec)
    ledger["new_fits"]=len(model_files)
    ledger["preprocessing_fits"]=len(list((PRIVATE/"preprocessing").glob("*.json")))
    assert sum(r["origin"]=="NEW_FIXED_RECIPE_FIT" for r in ledger["attempts"])==ledger["new_fits"]==43
    assert len(ledger["attempts"])==48 and len({r["training_signature"] for r in ledger["attempts"]})==43
    save(OUT/"FIT_LEDGER.json",ledger)
    with (OUT/"TRIAL_LEDGER.jsonl").open("a") as f:f.write(canonical(rec)+"\n")
    save(OUT/"THRESHOLD_SNAPSHOTS.json",{r["trial"]:r["thresholds"] for r in ledger["attempts"]})
    save(OUT/"TECHNICAL_BOOKKEEPING_REPAIR.json",{"exact_jst":now(),"status":"RECONCILED_FROM_IMMUTABLE_ARTIFACTS",
        "observed":before,"reconciled":{"new_fits":43,"preprocessing_fits":23,"attempt_N":48},
        "missing_trial":trial,"diagnosis":"block8 record absent from both mutable ledgers after stage updates; exact overwrite mechanism not established",
        "immutable_evidence":{"fit_claim_sha256":sha(missing[0]),"model_sha256":sha(model_path),
            "prediction_sha256":sha(predictions),"seal_sha256":sha(PRIVATE/"claims"/(trial+"_PREDICTIONS_IMMUTABLE.json"))},
        "already_seen_results":["discovery and locked late aggregate results"],
        "recovery_fit_N":0,"model_or_prediction_rewrites":0,"teacher_or_policy_changes":0,
        "selection_lock_unchanged_sha256":sha(OUT/"MODEL_SELECTION_LOCK.json"),
        "late_result_unchanged_sha256":sha(OUT/"LATE_DEV_RESULTS.json"),
        "unrecoverable_bookkeeping_fields":["original warnings","original ledger-write timestamp"],
        "original_observed_ledgers_preserved_private":True})
    checkpoint("05_GROUPS_COMPLETE","ABLATION_COMPLETE_AUDIT_PENDING",["30discovery fits","3locked late fits","10new group-ablation fits","5equivalent RAW_L fits reused","bookkeeping reconciled from immutable artifacts"],
        ["independent audit","report","final GitHub readback"],"verify every saved prediction/threshold and rebuild all sign metrics independently")
    print(canonical({"new_fits":43,"equivalent_reuse":5,"preprocessing_fits":23,"recovery_fits":0}))

if __name__=="__main__":
    main()
