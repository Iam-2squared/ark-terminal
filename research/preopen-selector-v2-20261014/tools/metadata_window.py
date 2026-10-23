"""Compile a reviewable inventory proposal from calendar/receipt metadata only."""
from __future__ import annotations
import argparse
import base64
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ark_selector_v2.approval_package import cash_calendar_metadata, inventory_window, package_hash
from ark_selector_v2.artifact_io import exclusive_json
from ark_selector_v2.contracts import FLAGS
from ark_selector_v2.exact_math import V2Error


def compile_capture(capture: dict) -> dict:
    if set(capture) != {"schema", "calendar_base64", "calendar_identity", "source_receipts", "metadata_references", "protected_ranges"} or capture["schema"] != "ARK_V2_METADATA_CAPTURE_V1":
        raise V2Error("METADATA_CAPTURE_SCHEMA")
    calendar = cash_calendar_metadata(base64.b64decode(capture["calendar_base64"], validate=False), capture["calendar_identity"]["source_sha256"])
    plan = inventory_window(calendar["sessions"], capture["source_receipts"], capture["protected_ranges"])
    bindings = plan.pop("source_bindings", [])
    groups: dict[str,dict] = {}
    for binding in bindings:
        key = binding["source_id"]
        if key not in groups:
            groups[key] = {k: binding[k] for k in ("source_id", "source_sha256", "bytes", "dataset", "original_commit", "original_git_blob", "use_approved", "record_date_presence", "exposure")}
            groups[key]["role_dates_proposal"] = {}
            groups[key]["protected_dates"] = []
        groups[key]["role_dates_proposal"].setdefault(binding["role_proposal"], []).append(binding["session"])
        if binding["protected"]: groups[key]["protected_dates"].append(binding["session"])
    calendar.pop("sessions")
    result = {"schema": "ARK_V2_INVENTORY_WINDOW_METADATA_V1", "status": "INVENTORY_PROPOSAL_NOT_AUTHORIZED",
        "calendar": {**capture["calendar_identity"], **calendar}, "metadata_references": capture["metadata_references"],
        "window": plan, "source_objects": list(groups.values()), "protected_ranges": capture["protected_ranges"],
        "selection_policy": "LATEST_CONTIGUOUS_OBJECT_KEY_COVERAGE_NO_OUTCOME_SELECTION_NO_PROTECTED_GAP_SKIP_NO_OLDER_FALLBACK",
        "market_numeric_reads": 0, "market_fits": 0, "approved_market_teacher_dates": [],
        "source_entitlement": "SAVED_STORAGE_RECEIPTS_NOT_V2_PURPOSE_AUTHORIZATION",
        "unknowns": ["EXACT_RECORD_DATE_COVERAGE", "V2_RIGHTS_AND_PURPOSE_ALLOWLIST", "REPORT19_AND_OTHER_EXACT_SEALS", "CROSS_RESEARCH_DATE_EXPOSURE", "ASOF_RAW_IDENTITY_AND_SOURCE_CONTRACTS"],
        **{f: False for f in FLAGS}}
    result["package_sha256"] = package_hash(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = compile_capture(json.loads(Path(args.capture).read_text()))
    exclusive_json(Path(args.output), result)
    print(json.dumps({"status": result["window"]["status"], "source_objects": len(result["source_objects"]),
        "roles": {k: {"from": v[0], "through": v[-1], "sessions": len(v)} for k, v in result["window"]["split"].items()},
        "protected_sessions": len(result["window"]["protected_dates"]), "market_numeric_reads": 0, "market_fits": 0}))
    return 0


if __name__ == "__main__": raise SystemExit(main())
