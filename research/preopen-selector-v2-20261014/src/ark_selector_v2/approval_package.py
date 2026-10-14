"""Metadata-only planning: inventory candidates never become permissions."""
from __future__ import annotations
from typing import Any
from .contracts import FLAGS,digest
from .exact_math import V2Error


def propose_window(calendar: list[str], coverage: dict[str,list[str]], *, protected: set[str], candidate_range: list[str]) -> dict[str,Any]:
    if calendar!=sorted(set(calendar)) or candidate_range!=sorted(set(candidate_range)):
        raise V2Error("EXACT_CALENDAR_METADATA_REQUIRED")
    if set(coverage)!={"DAILY","MASTER"}:raise V2Error("REQUIRED_DATASET_METADATA")
    available=set(coverage["DAILY"])&set(coverage["MASTER"])
    windows=[]
    for end in range(350,len(calendar)+1):
        block=calendar[end-350:end]
        if set(block)<=available and set(block[150:])<=set(candidate_range):windows.append(block)
    if not windows:return {"status":"NO_CONTIGUOUS_INVENTORY_WINDOW","split":None,"authorized_teacher_days":0}
    # Latest inventory window selected WITHOUT outcome inspection or skipping
    # any protected day. A protected latest window remains blocked, no fallback.
    chosen=windows[-1];study=chosen[150:]
    split={"HISTORY":chosen[:150],"FIT":study[:120],"CAL":study[120:140],"VALIDATION":study[140:160],"FINAL":study[160:]}
    return {"status":"BLOCKED_PROTECTED_LATEST_INVENTORY_WINDOW" if set(chosen)&protected else "INVENTORY_PROPOSAL_NOT_AUTHORIZED",
            "split":split,"protected_dates":sorted(set(chosen)&protected),"authorized_teacher_days":0,"outcome_reads":0}


def package_hash(package: dict[str,Any]) -> str:
    return digest({k:v for k,v in package.items() if k!="package_sha256"})
