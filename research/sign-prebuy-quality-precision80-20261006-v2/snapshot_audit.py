"""Read-only aggregate audit of preserved Sign inputs; never reads outcomes.

This audits the OLD views. It does not certify them for the new BUY_INTENT
boundary, repair snapshots, choose a threshold, or train a model.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path

JST = timezone(timedelta(hours=9))
REQUIRED = ("SNAPSHOTS.jsonl.gz", "METADATA.jsonl.gz", "INPUT_PROVENANCE.jsonl.gz")
INTENT_UNAVAILABLE = frozenset({
    "entry/fill_clock", "entry/intent_to_fill_active_delay",
    "selector/to_entry_active_delay", "selector/raw_entry_vs_first_price_pct",
})


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_rows(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def index(rows):
    out = {r["entry_id"]: r for r in rows}
    if len(out) != len(rows):
        raise ValueError("DUPLICATE_ENTRY_ID")
    return out


def timestamp(value):
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("NAIVE_TIMESTAMP_IS_NOT_AVAILABILITY_PROOF")
    return d


def number_missing(value):
    return value is None or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)


def audit_snapshot_views(snapshots, metadata, provenance, registry):
    sm, mm, pm = index(snapshots), index(metadata), index(provenance)
    if set(sm) != set(mm) or set(sm) != set(pm):
        raise ValueError("ENTRY_IDENTITY_SET_MISMATCH")
    if any(type(r.get("execution_eligible")) is not bool for r in metadata):
        raise ValueError("EXECUTION_ELIGIBILITY_UNKNOWN_NOT_FALSE")
    eligible = [k for k in sm if mm[k]["execution_eligible"] is True]
    groups = {}
    for group, columns in registry["groups"].items():
        cols = list(columns)
        missing_cells = sum(number_missing(sm[k]["numeric"].get(c)) for k in eligible for c in cols)
        absent_cells = sum(c not in sm[k]["numeric"] for k in eligible for c in cols)
        null_cells = sum(c in sm[k]["numeric"] and sm[k]["numeric"][c] is None for k in eligible for c in cols)
        missing_entries = sum(any(number_missing(sm[k]["numeric"].get(c)) for c in cols) for k in eligible) if cols else 0
        present_entries = [k for k in eligible if any(not number_missing(sm[k]["numeric"].get(c)) for c in cols)]
        denom = len(eligible) * len(cols)
        temporal = Counter()
        for k in eligible:
            clock = sm[k]["numeric"].get("entry/intent_clock")
            if isinstance(clock, bool) or not isinstance(clock, (int, float)) or not math.isfinite(clock) or clock != int(clock) or not 0 <= clock < 1440:
                temporal["intent_clock_unavailable"] += 1
                continue
            intent = datetime.fromisoformat(mm[k]["session"]).replace(tzinfo=JST) + timedelta(minutes=clock)
            receipt = pm[k].get(group, {})
            for field in ("source_available_at", "feature_as_of", "valid_from"):
                if receipt.get(field) is None:
                    temporal[field + "_unproven"] += 1
                else:
                    try:
                        temporal[field + "_after_intent"] += timestamp(receipt[field]) > intent
                    except (ValueError, TypeError, AttributeError):
                        temporal[field + "_invalid"] += 1
        groups[group] = {
            "numeric_columns": len(cols), "entry_denominator": len(eligible),
            "cell_denominator": denom, "missing_cells": missing_cells,
            "absent_numeric_key_cells": absent_cells, "explicit_null_cells": null_cells,
            "invalid_numeric_cells": missing_cells - absent_cells - null_cells,
            "missing_cell_rate": missing_cells / denom if denom else None,
            "entries_with_any_missing": missing_entries,
            "entry_any_missing_rate": missing_entries / len(eligible) if eligible and cols else None,
            "entries_with_any_observed_numeric": len(present_entries),
            "dates_with_any_observed_numeric": len({mm[k]["session"] for k in present_entries}),
            "symbols_with_any_observed_numeric": len({k.split("|")[1] for k in present_entries}),
            "intent_boundary_receipt_counts": dict(temporal),
            "structural_intent_unavailable_columns": sorted(INTENT_UNAVAILABLE.intersection(cols)),
            "cause": "UNATTRIBUTED_REQUIRES_ORIGINAL_PREFIX_AND_ACQUISITION_MANIFEST",
        }
    return {
        "status": "DESCRIPTIVE_INPUT_AUDIT_NOT_MODEL_READY",
        "all_entry_count": len(sm), "eligible_entry_count": len(eligible),
        "eligible_date_count": len({mm[k]["session"] for k in eligible}),
        "eligible_symbol_count": len({k.split("|")[1] for k in eligible}),
        "groups": groups, "labels_read": 0, "model_fits": 0,
        "threshold_choices": 0, "capital_replays": 0,
        "actual_arrival_verified": False, "quality_subset_adopted": False,
        "note": "Old fill-boundary views require intent re-extraction. Receipt comparisons are historical as-of diagnostics, not proof of actual arrival or RAW acquisition failures.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root", type=Path, required=True)
    p.add_argument("--expected-manifest", type=Path, required=True)
    p.add_argument("--registry", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    missing = [name for name in REQUIRED if not (args.private_root / name).is_file()]
    if missing:
        result = {"status": "BLOCKED_PRIVATE_INPUT_NOT_MOUNTED", "missing": missing,
                  "labels_read": 0, "model_fits": 0, "threshold_choices": 0,
                  "capital_replays": 0, "market_performance_measured": False}
        code = 2
    else:
        expected = json.loads(args.expected_manifest.read_text())["files"]
        hashes = {name: digest(args.private_root / name) for name in REQUIRED}
        if any(hashes[name] != expected[name] for name in REQUIRED):
            raise ValueError("PRIVATE_SOURCE_HASH_MISMATCH_NO_REBIND")
        result = audit_snapshot_views(*(read_rows(args.private_root / name) for name in REQUIRED),
                                      json.loads(args.registry.read_text()))
        result["input_sha256"] = hashes
        code = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Do not overwrite evidence on a repeated invocation.
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({"status": result["status"], "model_fits": 0}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
