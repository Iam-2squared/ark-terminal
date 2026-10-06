"""Verify the standalone interface against already sealed selected OOF outputs."""
import copy
from inference import load_artifacts, predict_sign
from sign_io import OUT, PRIVATE, read, rows, save, now


def main():
    selected = read(OUT / "MODEL_SELECTION_LOCK.json")["selected_candidate"]
    snapshots = {r["entry_id"]: r for r in rows(PRIVATE / "SNAPSHOTS.jsonl.gz")}
    predictions = [p for phase in ["DISCOVERY", "LATE_DEV"]
                   for p in rows(PRIVATE / (phase + "_PREDICTIONS.jsonl.gz")) if p["candidate"] == selected]
    ledger = read(OUT / "FIT_LEDGER.json")["attempts"]
    artifacts = {}
    checked = 0
    keys = ["entry_id", "decision_ts", "predicted_sign", "filter_action", "availability_status",
            "model_hash", "threshold_hash", "feature_schema_hash", "max_source_available_at",
            "fit_cutoff", "cal_cutoff"]
    for p in predictions:
        b = p["block"]
        if b not in artifacts:
            rec = next(r for r in ledger if r["block"] == b and r["candidate"] == selected and r["phase"] != "ABLATION")
            artifacts[b] = load_artifacts(PRIVATE / "models" / (rec["training_signature"] + ".pkl"),
                                         PRIVATE / "thresholds" / (rec["trial"] + "_Q0.8.json"))
        model, threshold = artifacts[b]
        s = copy.deepcopy(snapshots[p["entry_id"]])
        s["numeric"] = {k: s["numeric"][k] for k in model["preprocessing"]["numeric"]}
        s["categorical"] = {k: s["categorical"][k] for k in model["preprocessing"]["categorical"]}
        s["feature_schema_hash"] = model["feature_schema_hash"]
        result = predict_sign(s, model, threshold)
        assert all(result[k] == p[k] for k in keys)
        assert (result["p_plus"] is None) == (p["p_plus"] is None)
        if p["p_plus"] is not None:
            assert abs(result["p_plus"] - p["p_plus"]) <= 1e-12
        assert result["exposure_status"] == "HISTORICALLY_EXPOSED_DEVELOPMENT"
        checked += 1
    forbidden = ["y_plus", "true_R", "future_EXIT", "buy_debit", "capital", "quantity"]
    for key in forbidden:
        injected = {**s, key: 1}
        try:
            predict_sign(injected, model, threshold)
        except AssertionError:
            pass
        else:
            raise AssertionError("forbidden teacher/outcome/account field accepted: " + key)
    future = {**s, "max_source_available_at": "2099-01-01T00:00:00+09:00"}
    unavailable = predict_sign(future, model, threshold)
    assert unavailable["predicted_sign"] == "ABSTAIN" and unavailable["p_plus"] is None
    assert unavailable["filter_action"] == "PASS_CANDIDATE"
    save(OUT / "STANDALONE_INFERENCE_CHECK.json", {
        "status": "PASS", "completed_jst": now(), "selected_candidate": selected,
        "sealed_predictions_matched_N": checked, "block_artifacts_verified_N": len(artifacts),
        "forbidden_fields_rejected": forbidden, "future_source_ABSTAIN_operational_PASS": True,
        "new_fits": 0, "model_or_threshold_changes": 0, "Capital_connection": 0,
        "note": "Predict interface preserves generic historical exposure; archived outputs also retain phase-specific exposure."
    })
    print({"status": "PASS", "sealed_predictions_matched_N": checked, "new_fits": 0})


if __name__ == "__main__":
    main()
