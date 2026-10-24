"""Metadata-only planning: inventory candidates never become permissions."""
from __future__ import annotations
from typing import Any
from .contracts import FLAGS,digest
from .exact_math import V2Error


def cash_calendar_metadata(compressed: bytes, expected_sha256: str) -> dict[str,Any]:
    """Only Date/HolDiv metadata; no market-price dataset is accepted here."""
    import csv
    import gzip
    import hashlib
    import io
    from datetime import date,timedelta
    if hashlib.sha256(compressed).hexdigest()!=expected_sha256:
        raise V2Error("CALENDAR_METADATA_HASH_MISMATCH")
    decoded=gzip.decompress(compressed)
    reader=csv.DictReader(io.StringIO(decoded.decode("utf-8-sig")))
    if reader.fieldnames!=["Date","HolDiv"]:raise V2Error("CALENDAR_METADATA_ONLY_SCHEMA")
    dates=[];sessions=[];previous=None
    for row in reader:
        if set(row)!={"Date","HolDiv"} or row["HolDiv"] not in {"0","1","2","3"}:
            raise V2Error("CALENDAR_HOLDIV_METADATA")
        current=date.fromisoformat(row["Date"])
        if current.isoformat()!=row["Date"] or (previous is not None and current!=previous+timedelta(days=1)):
            raise V2Error("CALENDAR_DATE_GAP_OR_DUPLICATE")
        previous=current;dates.append(row["Date"])
        # 3 is OSE holiday trading, not a TSE cash-equity session.
        if row["HolDiv"] in {"1","2"}:sessions.append(row["Date"])
    if not dates:raise V2Error("EMPTY_CALENDAR_METADATA")
    return {"sessions":sessions,"from":dates[0],"through":dates[-1],"calendar_days":len(dates),
            "compressed_sha256":expected_sha256,"decoded_sha256":hashlib.sha256(decoded).hexdigest(),
            "cash_session_holiday_divisions":["1","2"],"excluded_holiday_divisions":["0","3"]}


def inventory_window(calendar: list[str], sources: list[dict[str,Any]],
                     protected_ranges: list[dict[str,str]]) -> dict[str,Any]:
    """Latest object-key coverage proposal. Record coverage/rights stay unknown."""
    coverage: dict[str,list[str]]={"DAILY":[],"MASTER":[]}
    matches: dict[tuple[str,str],list[dict[str,Any]]]={}
    for source in sources:
        dataset="MASTER" if source["dataset"]=="DATED_MASTER" else source["dataset"]
        if dataset not in coverage or source.get("period") is None:continue
        period=source["period"]
        for day in calendar:
            if period["from"]<=day<=period["to"]:
                coverage[dataset].append(day);matches.setdefault((dataset,day),[]).append(source)
    protected={d for d in calendar if any(r["from"]<=d<=r["through"] for r in protected_ranges)}
    plan=propose_window(calendar,{k:sorted(set(v)) for k,v in coverage.items()},
                        protected=protected,candidate_range=calendar)
    plan["record_date_coverage_verified"]=False
    plan["coverage_basis"]="SOURCE_OBJECT_KEY_PERIOD_METADATA_NOT_MARKET_RECORD_CENSUS"
    if plan["split"] is None:return plan
    split=plan["split"]
    bindings=[]
    for role,days in split.items():
        for day in days:
            # Full reference master identities are required for RAW symbol rules.
            for dataset in ("DAILY","MASTER"):
                candidates=matches[(dataset,day)]
                if len(candidates)!=1:raise V2Error("AMBIGUOUS_SOURCE_OBJECT_PERIOD_METADATA")
                source=candidates[0]
                bindings.append({"session":day,"role_proposal":role,"dataset":dataset,
                    "source_id":source["repository"]+"/"+source["object_key"],"source_sha256":source["sha256"],
                    "bytes":source["bytes"],"original_commit":source["destination_commit"],
                    "original_git_blob":source["destination_git_blob"],"record_date_presence":"NOT_NUMERICALLY_INSPECTED",
                    "use_approved":False,"protected":day in protected,
                    "exposure":"CROSS_RESEARCH_DATE_LINEAGE_NOT_RECONCILED"})
    plan["source_bindings"]=bindings
    plan["authorized_teacher_dates"]=[]
    plan["authorized_history_dates"]=[]
    return plan


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
