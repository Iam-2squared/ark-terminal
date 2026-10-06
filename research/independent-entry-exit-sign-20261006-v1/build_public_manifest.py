"""Finalize public sign artifact hashes, keeping row-level files private."""
from pathlib import Path
from sign_io import OUT, CODE, PRIVATE, read, sha, now, save, checkpoint


def main():
    late = read(OUT / "LATE_DEV_RESULTS.json")
    audit = read(OUT / "INDEPENDENT_AUDIT.json")
    ledger = read(OUT / "FIT_LEDGER.json")
    assert late["status"] == "SIGN_NOT_SEPARATED_IN_THIS_RUN"
    assert audit["status"] == "PASS" and ledger["new_fits"] == 43
    checkpoint("07_REPORT_COMPLETE", late["status"],
       ["source/teacher/input/split/family precommit", "six candidates discovery comparison",
        "one candidate GitHub lock before late check", "locked late three blocks", "group ablations",
        "independent audit PASS 1303 mismatch 0", "standalone API 1039 predictions matched",
        "measured Japanese report and three figures"],
       ["final study GitHub readback", "private archive delivery receipt"],
       "Research closed with negative sign result; preserve Rank and frozen upstream; deliver hashes and receipts")
    state = read(OUT / "CURRENT_STATE.json")
    state.update(scientific_status=late["status"], research_completed=True,
                 selected_candidate=late["candidate"], independent_audit="PASS",
                 model_reselection_after_late=0, further_experiments_authorized_in_this_cycle=False,
                 last_verified_GitHub_commit="09f99aa819cfcfc0e5e5a6101fb0d2222618db8e",
                 private_delivery_status="PENDING_ARCHIVE", scope="independent sign module only",
                 preserved_old_final_parent="07324ba54fc44a7c03ce7702c62bc7484aecf4cc")
    state["counts_this_execution"].update(calibration_fits=0, full_data_final_fits=0,
                                       new_market_features=0, Capital_connections=0, trial_conditions=48)
    save(OUT / "CURRENT_STATE.json", state)
    save(OUT / "checkpoints/07_REPORT_COMPLETE.json", state)
    paths = [p for p in OUT.rglob("*") if p.is_file() and p.name != "MANIFEST.json"]
    paths += [p for p in CODE.glob("*") if p.is_file() and p.suffix in {".py", ".md"}]
    records = [{"path": str(p.relative_to(CODE.parents[1])), "bytes": p.stat().st_size,
                "sha256": sha(p)} for p in sorted(paths)]
    save(OUT / "MANIFEST.json", {"status": "FINAL_STUDY_ARTIFACTS_READY", "exact_jst": now(),
         "scientific_status": late["status"], "files": records,
         "manifest_self_excluded": True,
         "delivery_receipt_and_later_readbacks": "append-only; actual GitHub GET verifies final mutable CURRENT_STATE separately",
         "private_first_predictions": read(OUT / "FIRST_PREDICTIONS_DESCRIPTOR.json"),
         "private_archive": "row inputs/labels/models/predictions/forensic repair originals; hash and storage ID recorded on delivery",
         "public_contains_row_level_inputs_or_models": False})
    print({"public_files_hashed": len(records), "new_fits": 0, "status": late["status"]})


if __name__ == "__main__":
    main()
