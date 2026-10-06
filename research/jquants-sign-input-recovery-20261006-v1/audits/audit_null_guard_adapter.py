"""Finite connection check on saved Development prefixes; no stored cells/outcomes."""
import collections
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

from audit_recovered_source import HERE, SRC, ALL58_PATH, read, valid, starts, window_status

MODULE = Path("/workspace/ark-sign-work/research/sign-prebuy-quality-precision80-20261006-v2/missingness_reasons.py")


def main():
    spec = importlib.util.spec_from_file_location("null_guard", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    raw = read(SRC / "raw_paths_selected.json.gz")
    events = read(SRC / "selector_events_full144.json.gz")
    split = read(ALL58_PATH)
    all58 = set(split["all58"])
    first = {}
    for e in sorted(events, key=lambda e: (e["decisionTimestamp"], e["selectorEventId"])):
        k = e["sessionDate"] + "|" + e["symbol"]
        if k in raw:
            first.setdefault(k, e)
    # Two lexicographically fixed watches per day; only days/watches, not labels.
    keys = []
    for day in sorted(all58):
        candidates = sorted(k for k in raw if k.split("|")[0] == day)
        keys += [candidates[0]] + ([candidates[-1]] if len(candidates) > 1 else [])
    findings = collections.Counter()
    cases, checks = 0, 0
    sampled_days = set()
    features = ("w5/return", "w10/return", "w20/return", "return1", "vwapDistancePct", "activity/5/volumeRelativePreviousDay")
    for k in keys:
        day = k.split("|")[0]
        record = raw[k]
        regular = set(starts(day))
        obs = {int(x[0]) for x in record["today"] if valid(x) and int(x[0]) in regular}
        prev_reg = set(starts(record["previousSession"]))
        previous = {int(x[0]) for x in record["previous"] if valid(x) and int(x[0]) in prev_reg}
        time = first[k]["decisionTimestamp"]
        activation = int(time[11:13]) * 60 + int(time[14:16])
        decisions = sorted(m + 1 for m in obs if m + 1 >= activation)
        if not decisions:
            continue
        cuts = sorted({decisions[0], decisions[len(decisions) // 2], decisions[-1]})
        for t in cuts:
            cases += 1
            sampled_days.add(day)
            for feature in features:
                r = mod.explain_missingness(day, t, record["today"], record["previous"], feature,
                                           previous_day=record["previousSession"], observed_is_missing=None)
                assert r["stored_null_linkage"] == "STORED_CELL_NOT_CHECKED"
                assert r["evidence"]["source_basis_and_identity_verified"] is False
                if feature.startswith("w"):
                    n = int(feature.split("/")[0][1:])
                    expected = window_status(obs, t, n) != "AVAILABLE"
                elif feature == "return1":
                    expected = window_status(obs, t, 2) != "AVAILABLE"
                elif feature == "vwapDistancePct":
                    expected = sum(m < t for m in obs) / sum(m < t for m in regular) < .8
                else:
                    expected = (window_status(obs, t, 5) != "AVAILABLE"
                                or window_status(previous, t, 5) != "AVAILABLE")
                assert r["expected_null"] is expected
                findings[r["reason"]] += 1
                checks += 1
    source_hash_match = 0
    ledger = {(r["session"], r["kind"]): r["sha256"] for r in read(SRC / "source_ledger.json")}
    for k, r in raw.items():
        assert r["sourceHash"] == ledger[k.split("|")[0], "minute"]
        source_hash_match += 1
    now = datetime.datetime.now(datetime.timezone.utc)
    report = {
        "status": "SAVED_RAW_DIRECT_SCHEMA_CONNECTION_AND_FINITE_NULL_GUARD_PARITY_PASS",
        "exact_utc": now.isoformat(), "exact_jst": now.astimezone(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        "adapter_path": str(MODULE.relative_to(Path("/workspace/ark-sign-work"))),
        "adapter_sha256": hashlib.sha256(MODULE.read_bytes()).hexdigest(),
        "adapter_version": mod.VERSION,
        "schema_translation_required": False,
        "sourceHash_matches_original_session_minute_ledger_N": source_hash_match,
        "sourceHash_denominator": len(raw),
        "sample_rule": "Before any feature-cell/outcome inspection: first and last lexicographic watch per each of 58 canonical days; first/middle/last actual watch-decision endpoint; six fixed features.",
        "sampled_watches": len(keys), "sampled_dates": len(sampled_days),
        "sampled_decision_endpoints": cases, "guard_checks": checks,
        "guard_agreement_N": checks,
        "features": list(features), "reason_counts": dict(findings),
        "input_boundary": "cutoff=closed raw-start+1 endpoint; adapter examines start first and excludes H/L/C/Volume/Value at raw-start>=cutoff.",
        "inferred_arrival_timestamp": False,
        "price_volume_value_reconstructed": False,
        "actual_Entry1600_cell_linkage_checked": False,
        "frozen_original_snapshots_available": False,
        "new_feature_values_computed": False,
        "original_P0_matrix_restored": False,
        "geometry_canonical_substrate_bodies_opened": 0,
        "ZIP_member_file_types": "JSON receipt/ledger/split and gzipped JSON or JSONL. No .npy/.npz/model/frozen P1_Q70 FIRST_ENTRY records/EXIT trades/State9-Path traces in artifact.",
        "artifact_creation_dependency": "Exported before FIRST_ENTRY model training/corrected freeze; canonical/geometry/substrate file names are older reference records. Do not substitute them for corrected P1_Q70 first intents.",
        "teacher_rows_read": 0, "protected_market_bodies_opened": 0,
        "price_rows_displayed": 0, "model_fits": 0, "threshold_choices": 0, "capital_replays": 0,
        "repair_options": [
            "Recover exact frozen Entry1600 first intents and original Sign/P0 snapshots; join by session|symbol with exact clock/row identity and hash provenance.",
            "Audit source prefix versus stored numeric cell before altering any sidecar extractor; preserve original source and snapshots.",
            "If extra RAW partitions are required, verify wrapper/response/page identities and date availability. Missing scheduled observations alone do not establish acquisition failure.",
            "Use original exact source tokens or existing trace for State9/Path; rounded numeric RAW does not certify reconstruction of the frozen decimal kernel.",
        ],
        "next_action": "Restore independent Sign bundle or the exact frozen originals. This adapter audit is descriptive and does not authorize fitting or assert a feature repair effect.",
    }
    with (HERE / "NULL_GUARD_ADAPTER_AUDIT.json").open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: report[k] for k in ("status", "sampled_watches", "sampled_dates", "sampled_decision_endpoints", "guard_checks", "reason_counts", "sourceHash_matches_original_session_minute_ledger_N")}))


if __name__ == "__main__":
    main()
