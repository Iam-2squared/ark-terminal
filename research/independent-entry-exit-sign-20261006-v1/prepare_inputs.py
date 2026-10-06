"""One mechanical view batch; semantics and lineage fixed before sign comparison."""
import subprocess
import sys
import platform
import numpy as np
import sklearn
import scipy
from sign_io import *
from sign_model import estimator, TRANSFORM_VERSION

def main():
    assert not (PRIVATE / "SNAPSHOTS.jsonl.gz").exists(), "VIEW_ALREADY_BOUND"
    PRIVATE.mkdir(parents=True, exist_ok=True)
    cfg_path = BASIS / "docs/evidence/capital-rneg-defense-reuse-20261006-v1/PREPARED_INPUT_CONFIG.json"
    cfg = read(cfg_path)
    runtime_path = OLD / "reuse_sign/capital_rneg_defense_private/RUNTIME_FEATURES.jsonl.gz"
    joined_path = OLD / "capital_sign_only_private/INPUT_ROWS.jsonl.gz"
    runtime = rows(runtime_path); joined = rows(joined_path)
    rm = {r["entry_id"]: r for r in runtime}; jm = {r["entry_id"]: r for r in joined}
    assert len(rm) == len(jm) == 1600 and set(rm) == set(jm)
    assert sha(runtime_path) == cfg["input_hashes"][runtime_path.name]
    binding = read(BASIS / "docs/evidence/capital-sign-only-filter-stage1-20261006-v1/SOURCE_BINDING.json")
    assert sha(joined_path) == binding["new_view_input_hashes"][joined_path.name]
    split = read(SPLIT_SOURCE)
    assert sha(SPLIT_SOURCE) == "e83291b8706c48a4e496739219f1a645246b73be28f2195bebfaeb6614a12274"
    assert len(split["all58"]) == 58 and len(split["OOF38"]) == 38 and len(split["warmup20"]) == 20
    assert {r["session"] for r in runtime} == set(split["all58"])
    # All allocation/Rank/outcome/identity fields are excluded from actual X.
    score_requested = ["entry/p1_score", "entry/p1_threshold", "score/pP", "score/MOVE_U2", "score/MOVE_U3"]
    p1 = {r["entry_id"]: r for r in rows(OLD / "capital_sign_only_private/P1_LINEAGE_ROWS.jsonl.gz")}
    score_rows = rows(OLD / "capital_sign_only_private/SCORE_LINEAGE_ROWS.jsonl.gz")
    score_map = {(r["score"], r["entry_id"]): r for r in score_rows}
    lineage = read(BASIS / "docs/evidence/capital-sign-only-filter-stage1-20261006-v1/ASOF_AND_SCORE_LINEAGE.json")
    deps = {r["entry_model_fold"]: r for r in lineage["P1_dependencies"]}
    score_audit = []
    legal = []
    for column in score_requested:
        receipts = []
        lineage_ok = True
        for b in split["blocks"]:
            parts = {"FIT": b["train"][:-5], "CAL": b["train"][-5:], "TEST": b["test"]}
            cal_ids = {r["entry_id"] for r in runtime if r["session"] in parts["CAL"]}
            test_ids = {r["entry_id"] for r in runtime if r["session"] in parts["TEST"]}
            cal_indices = {r["p0_snapshot_row_index"] for r in runtime if r["session"] in parts["CAL"]}
            test_indices = {r["p0_snapshot_row_index"] for r in runtime if r["session"] in parts["TEST"]}
            for part, dates in parts.items():
                part_rows = [r for r in joined if r["session"] in dates and r["execution_eligible"]]
                connected = [r for r in part_rows if r["numeric"].get(column) is not None]
                bad = 0; cal_in_fit = 0; test_in_fit = 0
                if column.startswith("entry/p1_"):
                    for r in connected:
                        dep = p1[r["entry_id"]]; d = deps[dep["producer_fold"]]
                        bad += int(dep["producer_cutoff"] != d["train_cutoff"] or dep["producer_cutoff"] >= r["session"])
                    if part == "FIT":
                        for fold in sorted({p1[r["entry_id"]]["producer_fold"] for r in connected}):
                            f = OLD / "reuse_sign/authority_data/frozen/ark-terminal/research/persistent-watchlist-uptrend-first-entry-20261003-v2/CORRECTED_LINEAGE_FAST_FREEZE_20261003/PRIVATE_MODELS" / f"P1_F{fold}_train_indices.npy"
                            a = np.load(f, allow_pickle=False)
                            expected = deps[fold]["train_indices_hash"]
                            assert sha(f) == expected, "P1_TRAIN_INDEX_HASH"
                            assert len(a) == deps[fold]["train_row_N"] and len(set(a.tolist())) == len(a)
                            cal_in_fit += len(set(a.tolist()) & cal_indices)
                            test_in_fit += len(set(a.tolist()) & test_indices)
                            assert int(a.max()) < min(cal_indices), "P1_FIT_DEPENDENCY_AFTER_CAL_START"
                else:
                    name = column.split("/", 1)[1]
                    for r in connected:
                        dep = score_map[(name, r["entry_id"])]
                        bad += int(dep["producer_cutoff"] >= r["session"])
                    if part == "FIT":
                        name = column.split("/", 1)[1]
                        directory, prefix = {"pP": ("capital_v2_private", "CORE_P"),
                            "MOVE_U2": ("quality_original/private", "MOVE_U2"),
                            "MOVE_U3": ("quality_original/private", "MOVE_U3")}[name]
                        for block_id in sorted({score_map[(name, r["entry_id"])]["producer_block"] for r in connected}):
                            f = OLD / "reuse_sign/score_authority" / directory / "models" / f"{prefix}_BLOCK_{block_id:02d}.json"
                            producer = read(f)
                            ids = set(producer["train_entry_ids"])
                            cal_in_fit += len(ids & cal_ids); test_in_fit += len(ids & test_ids)
                            assert all(rm[k]["session"] < parts["CAL"][0] for k in ids)
                lineage_ok = lineage_ok and bad == cal_in_fit == test_in_fit == 0
                receipts.append({"block": b["block"], "partition": part, "eligible_N": len(part_rows),
                    "connected_N": len(connected), "coverage": len(connected)/len(part_rows),
                    "time_dependency_errors": bad, "CAL_teacher_in_FIT_producer": cal_in_fit,
                    "TEST_teacher_in_FIT_producer": test_in_fit})
        meets = lineage_ok and min(x["coverage"] for x in receipts) >= 0.95
        if meets:
            legal.append(column)
        score_audit.append({"column": column, "enabled": meets, "lineage_ok": lineage_ok,
            "reason": "LEGAL_ALL_PARTITIONS_GE95" if meets else "COVERAGE_BELOW95_WITH_NO_WARMUP_SUBSTITUTION",
            "partitions": receipts})
    context = {"entry/intent_clock", "entry/fill_clock", "entry/intent_to_fill_active_delay",
        "selector/first_clock", "selector/to_intent_active_delay", "selector/to_entry_active_delay",
        "p0/knownRefreshCount", "p0/activeMinutesSinceLatestSelector", "p0/isPM"}
    raw = [k for k in cfg["D2_numeric"] if k not in {"entry/p1_score", "entry/p1_threshold"}]
    raw_cat = cfg["categorical"]
    groups = {"G_PRICE": [], "G_STATE": [], "G_CONTEXT": [], "G_SCORE": legal}
    for k in raw:
        groups["G_CONTEXT" if k in context else "G_STATE" if k.startswith(("state/", "path/")) else "G_PRICE"].append(k)
    specs = {"RAW": {"numeric": raw, "categorical": raw_cat, "enabled": True},
             "AUG": {"numeric": raw + legal, "categorical": raw_cat, "enabled": bool(legal)}}
    features = []
    for group, cols in groups.items():
        for k in cols:
            features.append({"column": k, "group": group, "kind": "numeric", "definition": "stored " + k,
                "producer": "Frozen P1" if group == "G_SCORE" else "Frozen P0 first-intent" if k.startswith("p0/") else "CORE closed State/Path" if group == "G_STATE" else "CORE Entry/Selector",
                "learned": group == "G_SCORE", "source_available_at": "row source group receipt",
                "feature_as_of": "row original event/p0 intent", "valid_from": "same original availability event",
                "transform_version": TRANSFORM_VERSION, "source_hash": "row original snapshot/prefix or inherited P1 indices hash",
                "same_time_order": "inherited closed prefix -> first-intent admission -> before quantity",
                "selection_basis": "producer semantics only; signs/correlations not inspected"})
    for k in raw_cat:
        features.append({"column": k, "group": "G_STATE", "kind": "categorical", "definition": "stored "+k,
            "learned": False, "source_available_at": "CORE closed-prefix event", "feature_as_of": "row feature_as_of",
            "valid_from": "closed prefix before quantity", "transform_version": TRANSFORM_VERSION, "source_hash": "row closed-prefix hash"})
    registry = {"fixed_before_sign_comparison": True, "representations": specs, "groups": groups, "features": features,
        "RAW_score_columns_N": 0, "G_SCORE_legal": legal, "excluded_scores": [x for x in score_requested if x not in legal],
        "MRET": "not in requested recovery set; excluded", "G_STATE_categorical": raw_cat,
        "metadata_not_X": ["entry_id", "session", "symbol", "row_index", "execution_eligible", "Rank/funding membership"],
        "new_features": 0, "one_mechanical_view_batch": True}
    save(OUT / "FEATURE_REGISTRY.json", registry, exclusive=True)
    save(OUT / "SCORE_LINEAGE_AUDIT.json", {"status": "PASS", "X_AUG_enabled": bool(legal),
        "scores": score_audit, "producer_refits": 0, "warmup_backscore": 0, "actual_arrival": "UNKNOWN",
        "P1_grid_date_and_maturity_proof": "reuse frozen producer audit; exact saved train-index hashes rechecked, max FIT producer grid index before first CAL index",
        "CAL_and_TEST_in_FIT_producer_N": 0, "historical_exposure_not_removed": True})
    snapshots = []; provenance = []
    all_num = specs["AUG"]["numeric"] if legal else raw
    for r in runtime:
        j = jm[r["entry_id"]]
        assert j["numeric"] == {**r["numeric"], **{k:v for k,v in j["numeric"].items() if k.startswith("score/")}}
        assert r["p0_snapshot_row_id"].split("|")[0] == r["session"]
        assert r["p0_snapshot_row_id"] == r["entry_id"] + "|" + str(int(r["numeric"]["entry/intent_clock"]))
        assert r["D1_asof_ok"] and r["D2_asof_ok"]
        assert r["feature_as_of"] <= r["entry_timestamp"] and r["p0_feature_as_of"] <= r["entry_timestamp"]
        assert r["max_source_available_at"] <= r["entry_timestamp"]
        snapshots.append({"entry_id": r["entry_id"], "decision_ts": r["entry_timestamp"],
            "numeric": {k: j["numeric"][k] for k in all_num}, "categorical": {k:r["categorical"][k] for k in raw_cat},
            "availability_status": "HISTORICAL_ASSUMED_AVAILABILITY", "feature_as_of": r["feature_as_of"],
            "source_available_at": r["max_source_available_at"], "valid_from": r["feature_as_of"],
            "transform_version": TRANSFORM_VERSION, "source_hash": digest({"prefix":r["provenance"]["prefix_sha256"],"snapshot":r["p0_snapshot_hash"]}),
            "max_source_available_at": r["max_source_available_at"], "feature_schema_hash": digest(registry)})
        provenance.append({"entry_id":r["entry_id"],"first_intent_row_id":r["p0_snapshot_row_id"],"first_intent_row_index":r["p0_snapshot_row_index"],
            "G_PRICE":{"source_available_at":r["max_source_available_at"],"feature_as_of":r["p0_feature_as_of"],"valid_from":r["p0_feature_as_of"],"source_hash":r["p0_snapshot_hash"]},
            "G_STATE":{"source_available_at":r["max_source_available_at"],"feature_as_of":r["feature_as_of"],"valid_from":r["feature_as_of"],"source_hash":r["provenance"]["prefix_sha256"]},
            "G_CONTEXT":{"source_available_at":r["max_source_available_at"],"feature_as_of":r["feature_as_of"],"valid_from":r["feature_as_of"],"source_hash":digest(r["provenance"])},
            "G_SCORE":{"source_available_at":r["p0_feature_as_of"],"feature_as_of":r["p0_feature_as_of"],"valid_from":r["p0_feature_as_of"],"source_hash":p1[r["entry_id"]]["producer_train_indices_hash"]},
            "transform_version":TRANSFORM_VERSION,"historical_actual_arrival":"UNKNOWN"})
    gzsave(PRIVATE / "SNAPSHOTS.jsonl.gz", snapshots)
    gzsave(PRIVATE / "INPUT_PROVENANCE.jsonl.gz", provenance)
    subprocess.run([sys.executable, str(CODE / "audit_source_adapter.py")], check=True)
    metadata = rows(PRIVATE / "METADATA.jsonl.gz"); targets = SignIndex(PRIVATE / "SIGN_TARGETS.jsonl.gz")
    splits = []
    for b in split["blocks"]:
        parts = {"FIT": b["train"][:-5], "CAL": b["train"][-5:], "TEST": b["test"]}
        ids = {}
        support = {}
        for part, dates in parts.items():
            ids[part] = [r["entry_id"] for r in metadata if r["session"] in dates and r["execution_eligible"]]
            if part in ["FIT", "CAL"]:
                before = parts["CAL"][0] if part == "FIT" else parts["TEST"][0]
                label = [targets.get(k,before=before,purpose="binding_"+part) for k in ids[part]]
                matured = [r for r in label if r["y_plus"] is not None and r["label_maturity"] < before]
                support[part] = {"eligible_N":len(label), "matured_known_N":len(matured),
                    "sessions":len({r["session"] for r in matured}),"PLUS":sum(r["y_plus"]==1 for r in matured),
                    "MINUS":sum(r["y_plus"]==0 for r in matured),"purged_or_unknown":len(label)-len(matured)}
            else:
                support[part] = {"eligible_N":len(ids[part]),"signs_not_read_for_this_binding":True}
        gzsave(PRIVATE/"split_ids"/f'BLOCK_{b["block"]:02d}.jsonl.gz',[{"partition":p,"entry_id":k} for p,ks in ids.items() for k in ks])
        splits.append({"block":b["block"],"dates":parts,"FIT_label_before":parts["CAL"][0],
            "CAL_label_before":parts["TEST"][0],"support":support,"entry_ID_hashes":{p:digest(ks) for p,ks in ids.items()}})
    save(OUT / "SPLIT_FIT_CAL_TEST.json", {"source_sha256":sha(SPLIT_SOURCE),"sessions":58,"warmup":20,"OOF":38,
        "cal_sessions":5,"discovery":[1,2,3,4,5],"late":[6,7,8],"blocks":splits,
        "FIT_then_CAL_same_model":True,"post_CAL_refits":0,"TEST_updates":0})
    design = read(OUT / "DESIGN_CONFIG.json")
    versions={"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__,"sklearn":sklearn.__version__}
    resolved={family:estimator(family,design).get_params() for family in ["L","H","E"]}
    # Old stage1 used all PAST including the five new CAL sessions and different
    # score representations. Every old signature is therefore non-equivalent.
    old_fits=read(BASIS/"docs/evidence/capital-sign-only-filter-stage1-20261006-v1/FIT_LEDGER.json")
    save(OUT/"REUSE_MATRIX.json",{"old_stage1_fits_preserved":32,"new_equivalent_reuse":0,
        "reason":"new FIT excludes last5 PAST CAL dates; old fits include them, with different feature order/teacher direction",
        "old_attempt_signatures":[{"recipe":r["recipe"],"block":r["block"],"hash":r["training_payload_hash"],"train_N":r["train_N"]} for r in old_fits["attempts"]],
        "old_reference_models_retained":24,"reference_refits":0})
    save(OUT/"SOURCE_BINDING.json",{"status":"PASS","basis_head":read(OUT/"CURRENT_STATE.json")["execution_basis_head"],
        "old_archive_sha256":sha(WORK/"work/recovered/Ark_Capital_Sign_Only_Filter_Stage1_20261006_PRIVATE.zip"),
        "inherited_frozen_code_hashes":binding["frozen_code_hashes"],
        "original_inputs":{str(p.relative_to(WORK)):sha(p) for p in [runtime_path,joined_path,SPLIT_SOURCE,OLD/"capital_sign_only_private/SIGN_LABEL_VIEW.jsonl.gz"]},
        "derived_private_files":{str(p.relative_to(PRIVATE)):sha(p) for p in PRIVATE.rglob("*") if p.is_file()},
        "old_market_calculations_reused":True,"new_feature_definitions":0,"new_R_materializations":0,
        "availability":"HISTORICAL_ASSUMED_AVAILABILITY","same_time_proof":"inherited original stage ordering plus exact first-intent identity; actual arrival unverified"})
    save(OUT/"MODEL_PRECOMMIT.json",{"exact_jst":now(),"versions":versions,"all_resolved_parameters":resolved,
        "candidate_ids":[p+"_"+f for p,s in specs.items() if s["enabled"] for f in ["L","H","E"]],
        "registry_sha256":sha(OUT/"FEATURE_REGISTRY.json"),"split_sha256":sha(OUT/"SPLIT_FIT_CAL_TEST.json"),
        "input_hashes":{p.name:sha(p) for p in PRIVATE.glob("*.jsonl.gz")},
        "code_hashes":{p.name:sha(p) for p in CODE.glob("*.py")},
        "weights":{"sample_weight":None,"class_weight":None},
        "preprocessing":TRANSFORM_VERSION,"post_CAL_refits":0,"budget_max":48,"technical_retries_max":2})
    save(OUT/"FIT_LEDGER.json",{"new_fits":0,"preprocessing_fits":0,"equivalent_fits_reused":0,"technical_retries":0,"attempts":[]})
    checkpoint("02_INPUTS_FIXED","INPUTS_AND_SPLIT_FIXED",["old source reused","sign-only teacher/raw views built once","all score lineage and partition coverage fixed","family/default parameters and time splits fixed"],
        ["GitHub prefit readback","DISCOVERY 30fits maximum","one candidate lock","late 3fits","ablation","independent audit"],
        "read back input/model/code freeze before any fitting")
    print(canonical({"RAW_numeric":len(raw),"RAW_categorical":len(raw_cat),"AUG_added":legal,"group_N":{k:len(v) for k,v in groups.items()},"new_fits":0}))

if __name__ == "__main__":
    main()
