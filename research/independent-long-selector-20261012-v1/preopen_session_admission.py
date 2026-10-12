"""Metadata-only reconciliation. Exposure is never a release of a separate seal."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from preopen_io import write_json, private_path, sha_file
from preopen_selector import digest, PreopenError, day

FIELDS = ("session_date", "exchange_previous_session", "original_partition",
          "current_allowed_use", "prior_outcome_exposure", "protected_by",
          "authorization_reference", "candidate_role", "history_only_permission",
          "overlap_resolution", "reason")


def exchange_sessions(calendar_rows):
    seen = set()
    out = []
    for r in calendar_rows:
        date = r["Date"]
        day(date)
        if date in seen:
            raise PreopenError("DUPLICATE_EXCHANGE_CALENDAR_DAY")
        seen.add(date)
        if str(r["HolDiv"]) not in ("0", "1", "2", "3"):
            raise PreopenError("UNKNOWN_CALENDAR_DIVISION")
        # 2 is the historical half-day cash session, 3 is derivatives-only.
        if str(r["HolDiv"]) in ("1", "2"):
            out.append(date)
    return sorted(out)


def reconcile_sessions(calendar_rows, *, budget, allocation, master_ledger,
                       dictionary_ledger, expansion, source_reference):
    sessions = exchange_sessions(calendar_rows)
    previous = dict(zip(sessions[1:], sessions[:-1]))
    explicit = set(budget["existingDevelopmentIdentity"]["trainingSessions"])
    long_rows = {x["sessionDate"]: x for x in master_ledger["sessions"]}
    dictionary = {x["sessionDate"]: x for x in dictionary_ledger["rows"]}
    partitions = {d: k for k, values in allocation["partitions"].items() for d in values}
    holdout = set(expansion["commonHoldout"])
    exclusions = expansion.get("excluded", {})
    rows = []
    for session in sessions:
        if not "2024-09-01" <= session <= "2026-10-05":
            continue
        lr, dr = long_rows.get(session, {}), dictionary.get(session, {})
        flags = lr.get("secondaryFlags", {})
        seals = []
        partition = partitions.get(session, "UNALLOCATED")
        if session in holdout:
            seals.append("STATE_DICTIONARY_COMMON_HOLDOUT")
        if partition in ("VALIDATION", "VALIDATION_REPLICATION", "PRIMARY_OOS",
                         "CONTINGENCY_OOS", "RESERVE"):
            seals.append("LONG_" + partition)
        if flags.get("sealed") or flags.get("protected") or flags.get("purged") or flags.get("excluded"):
            seals.append("GLOBAL_SECONDARY_SEAL_OR_EXCLUSION")
        if dr.get("partition") == "REPORT19" and dr.get("sealedThisTask") is True:
            seals.append("DICTIONARY_REPORT19_EXPLICIT_SEAL")
        excluded = exclusions.get(session, [])
        if any(x in excluded for x in ("sealed", "protected", "purged", "excluded")):
            seals.append("STATE_DICTIONARY_SOURCE_EXCLUSION")
        allowed = session in explicit and not seals
        reason = ("EXPLICIT_LONG_DEVELOPMENT_REUSE_ONLY_NO_FRESH_CREDIT" if allowed
                  else "EXPLICIT_SEAL_PRECEDENCE" if seals
                  else "NOT_IN_EXACT_AUTHORIZED_LONG_DEVELOPMENT_LIST")
        rows.append({
            "session_date": session,
            "exchange_previous_session": previous.get(session, ""),
            "original_partition": partition,
            "current_allowed_use": "DEVELOPMENT_RESEARCH" if allowed else "METADATA_ONLY",
            "prior_outcome_exposure": lr.get("priorOutcomeExposure", "UNKNOWN"),
            "protected_by": "|".join(seals),
            "authorization_reference": source_reference if allowed else "",
            "candidate_role": "UNASSIGNED",
            "history_only_permission": (
                "CAUSAL_HISTORY_PER_ORIGINAL_DATASET_CONTRACT;CURRENT_REUSE_BASIS_STILL_REQUIRED"
                if not flags.get("purged") else "BLOCKED_PURGED_SOURCE"),
            "overlap_resolution": "EXPOSURE_DOES_NOT_OVERRIDE_SEAL" if seals else "EXPLICIT_DEV_IDENTITY",
            "reason": reason})
    return rows


def assign_chronological_roles(rows, *, first_previous_tick_session="2024-10-01",
                               fit_days=30, calibration_days=10):
    admitted = [r for r in rows if r["current_allowed_use"] == "DEVELOPMENT_RESEARCH"
                and r["exchange_previous_session"] >= first_previous_tick_session]
    if len(admitted) <= fit_days + calibration_days:
        raise PreopenError("INSUFFICIENT_ADMITTED_SESSIONS_AFTER_SOURCE_COVERAGE")
    splits = {"fit": [], "calibration": [], "report": []}
    for i, row in enumerate(admitted):
        role = "fit" if i < fit_days else "calibration" if i < fit_days + calibration_days else "report"
        row["candidate_role"] = role
        splits[role].append(row["session_date"])
    return splits


def write_admission(rows, splits, out, source_hashes):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    with (out/"PRIVATE_SESSION_ADMISSION.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    file_hash, file_bytes = sha_file(out/"PRIVATE_SESSION_ADMISSION.csv")
    summary = {"schema": "ARK_PREOPEN_SESSION_RECONCILIATION_V1",
               "metadataOnly": True, "sourceHashes": source_hashes,
               "ledgerSha256": file_hash, "ledgerBytes": file_bytes,
               "sessionN": len(rows),
               "allowedN": sum(r["current_allowed_use"] == "DEVELOPMENT_RESEARCH" for r in rows),
               "roleN": {k: len(v) for k,v in splits.items()},
               "splitHash": digest(splits), "exactSplits": splits,
               "sealReasons": dict(Counter(r["protected_by"] for r in rows if r["protected_by"])),
               "REPORT19Released": False, "freshCredit": 0,
               "marketReuseBasisConfirmed": False, "outcomeRowsRead": 0}
    write_json(out/"SESSION_EXPOSURE_RECONCILIATION.json", summary)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--metadata-bundle", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    b = json.loads(Path(a.metadata_bundle).read_text())
    root = Path(b["privateRoot"]).resolve()
    paths = {k: private_path(v, root) for k,v in b["contracts"].items()}
    docs = {k: json.loads(v.read_text()) for k,v in paths.items()}
    import gzip
    with gzip.open(private_path(b["calendar"], root), "rt", newline="") as stream:
        calendar = list(csv.DictReader(stream))
    rows = reconcile_sessions(calendar, source_reference=b["authorizationReference"], **docs)
    splits = assign_chronological_roles(rows, **b.get("roleRule", {}))
    hashes = {k: sha_file(v)[0] for k,v in paths.items()}
    result = write_admission(rows, splits, private_path(a.output,root), hashes)
    print(json.dumps({"status":"METADATA_RECONCILED","allowedN":result["allowedN"],
                      "roleN":result["roleN"],"outcomeRowsRead":0},sort_keys=True))


if __name__ == "__main__":
    main()
