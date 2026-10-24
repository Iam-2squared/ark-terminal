"""Permissions precede numeric parsing. No self-authored approval creates rights."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable
from .contracts import DESIGN_ID, FLAGS, digest, safe_flags
from .exact_math import V2Error


class Mode(str, Enum):
    ENGINEERING="DESIGN_AND_ENGINEERING"
    CENSUS="AUTHORIZED_DEVELOPMENT_CENSUS"
    MARKET="ONE_CANDIDATE_MARKET_STUDY"


TRANSITIONS={
    "DESIGN_PROPOSAL":{"ENGINEERING_READY"},
    "ENGINEERING_READY":{"DATA_CENSUS_AUTHORIZED"},
    "DATA_CENSUS_AUTHORIZED":{"CENSUS_COMPLETE","BLOCKED_DATA_CENSUS"},
    "CENSUS_COMPLETE":{"MARKET_PRECOMMIT_APPROVED"},
    "MARKET_PRECOMMIT_APPROVED":{"FIT_ATTEMPT_STARTED"},
    "FIT_ATTEMPT_STARTED":{"MODEL_FIXED","BLOCKED_FIT"},
    "MODEL_FIXED":{"VALIDATION_WATCHLISTS_FIXED"},
    "VALIDATION_WATCHLISTS_FIXED":{"VALIDATION_OPENED"},
    "VALIDATION_OPENED":{"VALIDATION_TARGETS_MET","FAIL","NOT_ESTABLISHED"},
    "VALIDATION_TARGETS_MET":{"FINAL_WATCHLISTS_FIXED"},
    "FINAL_WATCHLISTS_FIXED":{"FINAL_OPENED"},
    "FINAL_OPENED":{"RESEARCH_MEASURED"},
}


def transition(state: str, target: str) -> str:
    if target not in TRANSITIONS.get(state,set()):
        raise V2Error("ILLEGAL_RESEARCH_STATE_TRANSITION")
    return target


@dataclass(frozen=True)
class ApprovalPins:
    # Pins are supplied by the owner through a trusted control plane, never by
    # the same request/file being checked. Mode A deliberately has no pins.
    owner_evidence_hashes: frozenset[str] = frozenset()
    precommit_hashes: frozenset[str] = frozenset()
    parent_approval_hashes: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Admission:
    mode: Mode
    approval_hash: str
    purpose: str
    allowed_sessions: frozenset[str]
    manifest_hash: str
    candidate_id: str


def validate_approval(request: dict[str,Any], pins: ApprovalPins,
                      *, purpose: str, mode: Mode, manifest_hash: str) -> Admission:
    if mode==Mode.ENGINEERING:
        raise V2Error("AWAITING_MARKET_APPROVAL")
    required={"schema","design_id","candidate_id","mode","owner_evidence_reference",
              "owner_evidence_sha256","owner_approved_at","parent_approval_sha256","purpose",
              "manifest_sha256","precommit_sha256","exact_session_allowlists","budget",*FLAGS}
    if set(request)!=required:
        raise V2Error("APPROVAL_UNKNOWN_OR_MISSING_FIELDS")
    safe_flags(request)
    if (request["schema"]!="ARK_SELECTOR_V2_OWNER_APPROVAL_V1" or request["design_id"]!=DESIGN_ID
            or request["candidate_id"]!="PREOPEN_V2_TC_C01" or request["mode"]!=mode.value):
        raise V2Error("APPROVAL_IDENTITY_OR_MODE_MISMATCH")
    if (request["owner_evidence_sha256"] not in pins.owner_evidence_hashes
            or request["precommit_sha256"] not in pins.precommit_hashes
            or request["parent_approval_sha256"] not in pins.parent_approval_hashes):
        raise V2Error("UNTRUSTED_SELF_DECLARED_APPROVAL")
    if not isinstance(request["owner_evidence_reference"],str) or not request["owner_evidence_reference"]:
        raise V2Error("OWNER_ORIGINAL_APPROVAL_REFERENCE_REQUIRED")
    try:
        stamp=datetime.fromisoformat(request["owner_approved_at"])
    except (ValueError,TypeError):
        raise V2Error("OWNER_APPROVAL_TIMESTAMP_REQUIRED") from None
    if stamp.tzinfo is None or stamp>datetime.now(stamp.tzinfo):
        raise V2Error("INVALID_OWNER_APPROVAL_TIMESTAMP")
    if request["purpose"]!=purpose or request["manifest_sha256"]!=manifest_hash:
        raise V2Error("APPROVAL_PURPOSE_OR_MANIFEST_MISMATCH")
    roles=request["exact_session_allowlists"]
    if not isinstance(roles,dict) or purpose not in roles or not isinstance(roles[purpose],list):
        raise V2Error("EXACT_PURPOSE_ALLOWLIST_REQUIRED")
    days=roles[purpose]
    if days!=sorted(set(days)) or not days:
        raise V2Error("INVALID_APPROVED_SESSION_LIST")
    for d in days:
        date.fromisoformat(d)
    wanted={"candidates":1,"base_fits":2,"calibration_optimizations":2} if mode==Mode.MARKET else {"candidates":0,"base_fits":0,"calibration_optimizations":0}
    if request["budget"]!=wanted:
        raise V2Error("MARKET_BUDGET_NOT_APPROVED")
    if mode==Mode.CENSUS and purpose not in {"HISTORY","FIT_TEACHER","CAL_TEACHER"}:
        raise V2Error("PROTECTED_EVALUATION_ROLE_IN_CENSUS")
    return Admission(mode,digest(request),purpose,frozenset(days),manifest_hash,request["candidate_id"])


def descriptor_gate(descriptors: list[dict[str,Any]], *, permitted_roles: set[str],
                    admission: Admission | None) -> None:
    for d in descriptors:
        if set(d)!={"role","purpose","session","source_sha256","bytes","protected","path"}:
            raise V2Error("DESCRIPTOR_UNKNOWN_OR_MISSING_FIELDS")
        if d["role"] not in permitted_roles:
            raise V2Error("FORBIDDEN_DESCRIPTOR_BEFORE_OPEN")
        if admission is None:
            raise V2Error("AWAITING_MARKET_APPROVAL")
        if d["protected"] is not False or d["session"] not in admission.allowed_sessions or d["purpose"]!=admission.purpose:
            raise V2Error("UNAPPROVED_DATE_PURPOSE_OR_PROTECTED_SOURCE")


def admitted_open(descriptors: list[dict[str,Any]], *, permitted_roles: set[str],
                  admission: Admission | None, opener: Callable[[dict[str,Any]],Any]) -> list[Any]:
    # Validate the entire batch BEFORE opening even the first raw object.
    descriptor_gate(descriptors,permitted_roles=permitted_roles,admission=admission)
    return [opener(d) for d in descriptors]


def metadata_audit(request: dict[str,Any]) -> dict[str,Any]:
    allowed={"schema","calendar_sessions","allowed_v2_sessions","sources","protected_sessions","exposed_sessions"}
    if set(request)!=allowed or request["schema"]!="ARK_V2_METADATA_REQUEST_V1":
        raise V2Error("METADATA_ONLY_SCHEMA_REQUIRED")
    sessions=request["calendar_sessions"]
    authorized=request["allowed_v2_sessions"]
    if sessions!=sorted(set(sessions)) or authorized!=sorted(set(authorized)):
        raise V2Error("INVALID_METADATA_SESSION_LIST")
    for d in sessions:
        date.fromisoformat(d)
    for s in request["sources"]:
        if set(s)!={"source_id","sha256","bytes","dataset","allowed_record_dates","allowed_purposes","protected_reason","latest_available_at","rights_reference"}:
            raise V2Error("NUMERIC_CONTENT_IN_METADATA_REQUEST")
        if not isinstance(s["bytes"],int) or s["bytes"]<0 or len(s["sha256"])!=64:
            raise V2Error("INVALID_SOURCE_METADATA")
    protected=set(request["protected_sessions"])
    by_dataset={k:set().union(*(set(s["allowed_record_dates"]) for s in request["sources"] if s["dataset"]==k)) for k in ("DAILY","DATED_MASTER","CALENDAR")}
    coverage=set.intersection(*by_dataset.values())
    usable=set(authorized)&coverage-protected
    windows=[]
    for end in range(350,len(sessions)+1):
        block=sessions[end-350:end]
        # 150 preceding reference sessions plus a continuous 200-day plan.
        if set(block)<=usable:
            windows.append(block)
    last=windows[-1] if windows else None
    split=None
    if last:
        teachers=last[150:]
        split={"history":last[:150],"fit":teachers[:120],"calibration":teachers[120:140],"validation":teachers[140:160],"final_report":teachers[160:]}
    return {"metadataOnly":True,"raw_numeric_reads":0,"market_fits":0,
            "eligible_windows":len(windows),"latest_window_proposal":split,
            "approved_v2_teacher_days":0,"metadata_eligible_requested_days":len(usable),
            "authorization_shortfall":200,"v2_authorization_verified":False,
            "blocking_protected_sessions":len(protected),"status":"WINDOW_PROPOSED_NOT_AUTHORIZED" if last else "BLOCKED_EXACT_V2_ALLOWLIST_OR_COVERAGE"}
