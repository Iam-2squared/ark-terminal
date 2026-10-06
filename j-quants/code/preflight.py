"""Metadata-only prerequisite checks. This program never requests market data.

The live downloader is deliberately not enabled by a successful preflight.
Entitlement, owner-only durable storage, a cross-Work rate binding and pinned
readers must all be established in the actual acquisition environment first.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import tempfile

JST = timezone(timedelta(hours=9))


def aware_time(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return result if result.tzinfo is not None else None


def license_reasons(record, now, operation="acquire"):
    if operation not in ("acquire", "read"):
        raise ValueError("unknown license operation")
    if now.tzinfo is None:
        raise ValueError("an aware execution clock is required")
    reasons = []
    if record.get("active_now") is not True:
        reasons.append("LIVE_ENTITLEMENT_NOT_VERIFIED")
    evidence = record.get("evidence", [])
    if not any(item.get("kind") in ("LIVE_ACCOUNT", "LIVE_PROVIDER_PERMISSION")
               and aware_time(item.get("observed_at")) is not None
               and aware_time(item.get("observed_at")) <= now
               for item in evidence if isinstance(item, dict)):
        reasons.append("LIVE_ENTITLEMENT_EVIDENCE_MISSING")
    field = "acquisition_allowed_until" if operation == "acquire" else "use_allowed_until"
    end = aware_time(record.get(field))
    if end is None:
        reasons.append("CONFIRMED_LICENSE_DEADLINE_MISSING")
    elif now >= end:
        reasons.append("LICENSE_ENDED_USE_STOPPED")
    if record.get("retention_requires_active_license") is not True:
        reasons.append("RETENTION_CONTRACT_UNBOUND")
    old_end = aware_time(record.get("previous_confirmed_until"))
    if old_end and end and end > old_end:
        renewal = record.get("renewal_evidence", {})
        if not (record.get("renewal_confirmed") is True
                and renewal.get("kind") == "LIVE_ACCOUNT"
                and aware_time(renewal.get("observed_at")) is not None
                and aware_time(renewal.get("observed_at")) <= now):
            reasons.append("UNSUPPORTED_LICENSE_EXTENSION")
    return sorted(set(reasons))


def storage_reasons(binding):
    required = ("owner_controlled", "owner_only_access_verified", "durability_verified", "deletion_supported")
    reasons = []
    if any(binding.get(key) is not True for key in required):
        reasons.append("BLOCKED_DURABLE_DESTINATION")
    raw_root = binding.get("private_cache_root")
    if not isinstance(raw_root, str) or not raw_root:
        return sorted(set(reasons + ["PRIVATE_CACHE_ROOT_UNBOUND"]))
    root = Path(raw_root)
    if not root.is_absolute():
        return sorted(set(reasons + ["ABSOLUTE_STORAGE_PATH_REQUIRED"]))
    try:
        resolved = root.resolve(strict=True)
        if not resolved.is_dir():
            reasons.append("STORAGE_DIRECTORY_MISSING")
        if any(resolved.is_relative_to(Path(prefix)) for prefix in
               ("/tmp", "/var/tmp", "/workspace/scratch", "/home/runner/work")):
            reasons.append("EPHEMERAL_STORAGE_NOT_DURABLE")
        stat = resolved.stat()
        if stat.st_mode & 0o077 or stat.st_uid != os.geteuid():
            reasons.append("OWNER_ONLY_FILESYSTEM_ACCESS_NOT_VERIFIED")
        marker = json.loads((resolved / ".ark-cache-binding.json").read_text())
        if not binding.get("binding_id") or marker.get("binding_id") != binding.get("binding_id"):
            reasons.append("STORAGE_BINDING_MARKER_MISMATCH")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        reasons.append("STORAGE_BINDING_NOT_ACCESSIBLE")
    return sorted(set(reasons))


def rate_reasons(contract):
    rate = contract.get("shared_rate_limit", {})
    if (rate.get("bound") is not True or rate.get("all_account_consumers_included") is not True
            or rate.get("cross_process_verified") is not True
            or rate.get("aggregate_rpm") != 54
            or rate.get("domain_mapping") != "CONSERVATIVE_SINGLE_ACCOUNT_DOMAIN"):
        return ["SHARED_ACCOUNT_LIMITER_UNBOUND"]
    if not rate.get("binding_evidence"):
        return ["SHARED_ACCOUNT_LIMITER_EVIDENCE_MISSING"]
    return []


def snapshot_reasons(contract):
    snapshot = contract.get("main_snapshot", {})
    reasons = []
    if not snapshot.get("basis_head") or snapshot.get("reader_allowlist_verified") is not True:
        reasons.append("MAIN_SNAPSHOT_READER_BINDING_UNVERIFIED")
    if snapshot.get("automatic_adoption") is not False or contract.get("cancel_in_progress") is not False:
        reasons.append("MAIN_ISOLATION_CONTRACT_UNBOUND")
    return reasons


def inspect_inputs(entitlement, storage, contract, key_present, now):
    records = entitlement.get("datasets", [])
    license_errors = {row["dataset"]: license_reasons(row, now) for row in records}
    reasons = sorted(set(reason for errors in license_errors.values() for reason in errors))
    if not records:
        reasons.append("DATASET_ENTITLEMENT_REGISTRY_UNBOUND")
    if not key_present:
        reasons.append("AUTHENTICATED_API_KEY_UNAVAILABLE_IN_THIS_PROCESS")
    reasons.extend(storage_reasons(storage))
    reasons.extend(rate_reasons(contract))
    reasons.extend(snapshot_reasons(contract))
    reasons = sorted(set(reasons))
    return {
        "schema": "ARK_JQUANTS_CACHE_PREFLIGHT_V1",
        "exact_utc": now.astimezone(timezone.utc).isoformat(),
        "exact_jst": now.astimezone(JST).isoformat(),
        "pid": os.getpid(),
        "job_id": os.environ.get("GITHUB_RUN_ID"),
        "status": "CACHE_BLOCKED_AUTH_OR_STORAGE" if reasons else "PREFLIGHT_READY_ACQUISITION_NOT_STARTED",
        "credential_present": bool(key_present),
        "credential_value_emitted": False,
        "dataset_count": len(records),
        "license_reasons_by_dataset": license_errors,
        "blockers": reasons,
        "provider_requests": 0,
        "signed_urls_issued": 0,
        "new_raw_objects": 0,
        "raw_bytes_transferred": 0,
        "model_fits": 0,
        "capital_replays": 0,
        "main_jobs_cancelled": 0,
        "acquisition_implementation": "NOT_ENABLED_BY_THIS_METADATA_ONLY_PROGRAM",
    }


def atomic_report(path, report):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        name = handle.name
    os.replace(name, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    entitlement = json.loads((args.evidence / "ENTITLEMENT_AND_RETENTION.json").read_text())
    storage = json.loads((args.evidence / "STORAGE_BINDING.json").read_text())
    contract = json.loads((args.evidence / "PARALLEL_WORK_CONTRACT.json").read_text())
    report = inspect_inputs(entitlement, storage, contract, bool(os.environ.get("JQUANTS_API_KEY")),
                            datetime.now(timezone.utc))
    atomic_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("## J-Quants RAW cache preflight\n\n```json\n")
            handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n```\n")


if __name__ == "__main__":
    main()
