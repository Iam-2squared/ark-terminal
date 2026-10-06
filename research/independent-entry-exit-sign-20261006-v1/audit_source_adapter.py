"""Quarantined binding/audit adapter. This alone may read original outcomes."""
from collections import Counter
from fractions import Fraction
import numpy as np
from sign_io import *

def sign_row(source, original_source_hash):
    status = "UNKNOWN"; y = None
    if source["known"] and source["buy_debit"] is not None and source["sell_credit"] is not None:
        debit = Fraction(str(source["buy_debit"])); credit = Fraction(str(source["sell_credit"]))
        assert debit > 0
        status = "PLUS" if credit > debit else "MINUS" if credit < debit else "EXACT_ZERO"
        y = {"PLUS": 1, "MINUS": 0, "EXACT_ZERO": None}[status]
    return validate_sign({"entry_id": source["entry_id"], "session": source["session"], "sign_status": status,
                          "y_plus": y, "label_maturity": source["label_maturity"], "source_hash": original_source_hash})

def main():
    # Registry and legal score representation are already frozen before this
    # adapter accesses sign outcomes. Only allowlisted views leave the adapter.
    assert (OUT / "FEATURE_REGISTRY.json").exists() and (OUT / "SCORE_LINEAGE_AUDIT.json").exists()
    raw_path = OLD / "reuse_sign/capital_rneg_defense_private/RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz"
    runtime_path = OLD / "reuse_sign/capital_rneg_defense_private/RUNTIME_FEATURES.jsonl.gz"
    assert sha(raw_path) == "fe8053da6798adcf01b5f4c09236304f607113c541acfee35a8f4ea74c9b9293"
    assert sha(runtime_path) == "2ac6acd608385eedf61e5ad912b6ec5a4be5750622167c1f619b30dda323628d"
    raw = rows(raw_path); runtime = rows(runtime_path)
    inherited = {r["entry_id"]: r for r in rows(OLD / "capital_sign_only_private/SIGN_LABEL_VIEW.jsonl.gz")}
    targets = [sign_row(r, inherited[r["entry_id"]]["source_hash"]) for r in raw]
    assert len(targets) == len(runtime) == len({r["entry_id"] for r in targets}) == 1600
    assert {r["entry_id"] for r in targets} == {r["entry_id"] for r in runtime}
    assert all(t["y_plus"] == 1 - s["y_neg"] for t, s in zip(targets, raw) if t["y_plus"] is not None)
    differences = 0
    invariance = 0
    for source, target in zip(raw, targets):
        old = inherited[source["entry_id"]]
        assert target["source_hash"] == digest(source) == old["source_hash"]
        assert target["label_maturity"] == old["label_maturity"]
        expected = {"POSITIVE": "PLUS", "NEGATIVE": "MINUS", "EXACT_ZERO": "EXACT_ZERO", "UNKNOWN": "UNKNOWN"}[old["sign_status"]]
        differences += int(target["sign_status"] != expected)
        # Replace result magnitude by two deliberately different values without
        # changing sign. Frozen provenance remains an input, not a learned value.
        if target["y_plus"] is not None:
            debit = Fraction(str(source["buy_debit"]))
            for factor in [Fraction(1, 10000), Fraction(30, 100)]:
                altered = dict(source)
                altered["sell_credit"] = str(float(debit * (1 + factor if target["y_plus"] == 1 else 1 - factor)))
                altered["r_original"] = "FORBIDDEN_TEST_POISON"
                assert sign_row(altered, target["source_hash"]) == target
                invariance += 1
    assert differences == 0
    gzsave(PRIVATE / "SIGN_TARGETS.jsonl.gz", targets)
    metadata = [{"entry_id": r["entry_id"], "session": r["session"], "execution_eligible": r["execution_eligible"],
                 "first_intent_row_id": r["p0_snapshot_row_id"], "first_intent_row_index": r["p0_snapshot_row_index"]}
                for r in runtime]
    gzsave(PRIVATE / "METADATA.jsonl.gz", metadata)
    split = read(SPLIT_SOURCE); rm = {r["entry_id"]: r for r in runtime}
    groups = {"ALL58": targets, "WARMUP20": [r for r in targets if r["session"] in split["warmup20"]],
              "OOF38_ALL": [r for r in targets if r["session"] in split["OOF38"]],
              "OOF38_ELIGIBLE": [r for r in targets if r["session"] in split["OOF38"] and rm[r["entry_id"]]["execution_eligible"]]}
    counts = {k: {"N": len(v), "sessions": len({r["session"] for r in v}), **dict(Counter(r["sign_status"] for r in v))} for k, v in groups.items()}
    assert counts["OOF38_ALL"]["PLUS"] == 462 and counts["OOF38_ALL"]["MINUS"] == 554 and counts["OOF38_ALL"]["UNKNOWN"] == 23
    assert counts["ALL58"]["PLUS"] + counts["ALL58"]["MINUS"] == 1560
    save(OUT / "SIGN_TARGET_CONTRACT.json", {
        "status": "PASS", "allowed_fields": sorted(SIGN_FIELDS), "target": "PLUS=1 MINUS=0; exact zero/unknown=null",
        "comparison": "exact Fraction(sell_credit) vs Fraction(buy_debit), no epsilon, no return computation",
        "costs": "original BUY1.0005 SELL0.9995, no repeated fee application",
        "source_target_sha256": sha(raw_path), "view_sha256": sha(PRIVATE / "SIGN_TARGETS.jsonl.gz"),
        "source_hash": "frozen original row provenance; never part of mathematical training/threshold/selection/gate payload",
        "source_sign_difference_N": differences, "magnitude_invariance_adapter_cases": invariance,
        "sample_weight": None, "class_weight": None, "new_R_materializations": 0})
    save(OUT / "SIGN_LABEL_COUNTS.json", counts)
    save(OUT / "SIGN_DATASET_MANIFEST.json", {"status": "PASS", "counts": counts,
        "identity_uniqueness_N": 1600, "metadata_separate_from_X": True, "runtime_unknown_rows_retained": True,
        "files": {p.name: sha(p) for p in PRIVATE.glob("*.jsonl.gz")}, "new_market_features": 0})
    print(canonical({"adapter": "PASS", "known": 1560, "OOF_PLUS": 462, "OOF_MINUS": 554, "magnitude_cases": invariance}))

if __name__ == "__main__":
    main()

