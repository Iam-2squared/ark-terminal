"""An owner-controlled, independently installed authority; never request trust.

The CLI has no authority by default. A deployment host may call dispatch with
an Authority built from its independently authenticated owner channel. Neither
JSON nor an environment variable nor a command-line option installs that channel.
TestAuthority is confined to a generated fixture root and exact byte hashes.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import hashlib
from .contracts import FLAGS, code_hash, configuration_hash, digest, registry, safe_flags
from .exact_math import V2Error
from .artifact_io import safe_path


def scoped_allowlists(pre: dict[str,Any],mode: str) -> dict[str,list[str]]:
    if mode=="C":return pre["allowlists"]
    history=set()
    calendar=pre["calendar_sessions"]
    for role in ("FIT","CAL"):
        for d in pre["split"][role]:
            i=calendar.index(d);history.update(calendar[max(0,i-150):i])
    return {"HISTORY":sorted(history),**{role+suffix:pre["allowlists"][role+suffix]
            for role in ("FIT","CAL") for suffix in ("_FEATURE","_TEACHER")}}


@dataclass(frozen=True)
class OwnerGrant:
    approval: dict[str, Any]
    original_text: str
    original_reference: str
    approved_at: str
    # Approval, original text and precommit pins must come from the host channel.
    approval_pin: str
    original_pin: str
    precommit_pin: str
    parent_pin: str | None


@dataclass
class Authority:
    root: Path
    output: Path
    grants: dict[str, OwnerGrant]
    manifest_pin: str
    precommit: dict[str, Any]
    artifact_pins: dict[str, dict[str, Any]] = field(default_factory=dict)
    test_only: bool = False
    fixture_pins: dict[str, tuple[str, int]] = field(default_factory=dict)

    def authorize(self, stage: str, request: dict[str, Any]) -> dict[str, Any]:
        if any((p/".git").exists() for p in (self.output.resolve(),*self.output.resolve().parents)):
            raise V2Error("PRIVATE_MODEL_OUTPUT_INSIDE_GIT_CHECKOUT")
        expected={"schema", "candidate_id", "mode", "approval", "manifest", "role"}
        if set(request)!=expected or request["schema"]!="ARK_V2_STAGE_REQUEST_V1":
            raise V2Error("STAGE_REQUEST_FIELDS")
        mode="B" if stage=="census" else "C"
        grant=self.grants.get(mode)
        if grant is None:
            raise V2Error("AWAITING_MARKET_APPROVAL:"+mode)
        approval=request["approval"]
        if approval!=grant.approval or digest(approval)!=grant.approval_pin:
            raise V2Error("UNTRUSTED_SELF_DECLARED_APPROVAL")
        safe_flags(approval)
        if (hashlib.sha256(grant.original_text.encode()).hexdigest()!=grant.original_pin
                or approval["owner_original_sha256"]!=grant.original_pin
                or approval["owner_reference"]!=grant.original_reference
                or approval["owner_approved_at"]!=grant.approved_at):
            raise V2Error("OWNER_ORIGINAL_EVIDENCE_MISMATCH")
        if not grant.original_text or not grant.original_reference:
            raise V2Error("OWNER_ORIGINAL_REQUIRED")
        from datetime import datetime
        stamp=datetime.fromisoformat(grant.approved_at)
        if stamp.tzinfo is None or stamp>datetime.now(stamp.tzinfo):
            raise V2Error("OWNER_APPROVAL_TIMESTAMP")
        if (request["mode"]!=mode or approval["mode"]!=mode
                or request["candidate_id"]!=approval["candidate_id"]
                or approval["candidate_id"]!="PREOPEN_V2_TC_C01"):
            raise V2Error("MODE_OR_CANDIDATE_MISMATCH")
        pre=self.precommit
        if digest(pre)!=grant.precommit_pin or approval["precommit_sha256"]!=grant.precommit_pin:
            raise V2Error("PRECOMMIT_PIN_MISMATCH")
        if pre["hashes"]!={"code":code_hash(),"config":configuration_hash(),"schema":digest(registry())}:
            raise V2Error("CODE_CONFIG_SCHEMA_DRIFT_NO_REFIT")
        manifest=request["manifest"]
        if (digest(manifest)!=self.manifest_pin or approval["manifest_sha256"]!=self.manifest_pin
                or pre["manifest_sha256"]!=self.manifest_pin):
            raise V2Error("NATIVE_MANIFEST_PIN_MISMATCH")
        if approval["allowlists"]!=scoped_allowlists(pre,mode) or approval["split"]!=pre["split"]:
            raise V2Error("APPROVAL_ALLOWLIST_OR_SPLIT_DRIFT")
        if approval["test_only"] is not self.test_only or pre["test_only"] is not self.test_only:
            raise V2Error("TEST_AUTHORITY_NOT_MARKET_AUTHORITY")
        wanted={"candidates":0,"fits":0,"calibrations":0} if mode=="B" else {"candidates":1,"fits":2,"calibrations":2}
        if approval["budget"]!=wanted or any(type(v) is not int for v in approval["budget"].values()):
            raise V2Error("UNAPPROVED_CANDIDATE_BUDGET")
        split=pre["split"]
        if set(split)!={"HISTORY","FIT","CAL","VALIDATION","FINAL"}:
            raise V2Error("SPLIT_ROLES")
        ordered: list[str]=sum((split[k] for k in ("HISTORY","FIT","CAL","VALIDATION","FINAL")),[])
        calendar=pre["calendar_sessions"]
        if ordered!=sorted(set(ordered)) or any(d not in calendar for d in ordered):
            raise V2Error("SPLIT_CHRONOLOGY")
        from datetime import date
        for d in calendar: date.fromisoformat(d)
        if calendar!=sorted(set(calendar)) or ordered!=calendar[calendar.index(ordered[0]):calendar.index(ordered[-1])+1]:
            raise V2Error("NONCONTIGUOUS_EXCHANGE_SPLIT")
        if not self.test_only and [len(split[k]) for k in ("HISTORY","FIT","CAL","VALIDATION","FINAL")]!=[150,120,20,20,40]:
            raise V2Error("UNAPPROVED_MARKET_SPLIT_LENGTH")
        from .calendar_phase import cutoff
        for mature,next_role in (("FIT","CAL"),("CAL","VALIDATION")):
            stamp=datetime.fromisoformat(pre["teacher_open_after"][mature])
            if stamp.tzinfo is None or stamp>=cutoff(date.fromisoformat(split[next_role][0])):
                raise V2Error("TEACHER_MATURITY_CROSSES_PARTITION_BOUNDARY")
        limits=pre["resource_limits"]
        if (set(limits)!={"universe_rows_upper_bound","ram_bytes","max_native_object_bytes"}
                or any(type(v) is not int or v<=0 for v in limits.values())):
            raise V2Error("PINNED_RESOURCE_LIMITS_REQUIRED")
        if pre["source_routes"]!={"daily":"NATIVE_RAW_SESSION_V1","master":"NATIVE_DATED_MASTER_V1","optional":"SOURCE_NOT_JOINED"}:
            raise V2Error("UNIMPLEMENTED_SOURCE_ROUTE")
        if mode=="C":
            parent=self.grants.get("B")
            if parent is None or parent.approval["split"]!=pre["split"] or parent.approval["manifest_sha256"]!=self.manifest_pin or grant.parent_pin!=parent.approval_pin or approval["parent_approval_sha256"]!=parent.approval_pin:
                raise V2Error("MODE_C_REQUIRES_INDEPENDENT_MODE_B_APPROVAL")
            if approval["census_receipt_sha256"]!=pre["census_receipt_sha256"]:
                raise V2Error("CENSUS_RECEIPT_BINDING")
        return pre|{"allowlists":scoped_allowlists(pre,mode)}

    def preflight_entries(self, manifest: dict[str, Any], wanted: list[tuple[str,str,str]], pre: dict[str,Any]) -> list[dict[str,Any]]:
        """All dates/purposes/routes checked before the first payload open."""
        fields={"path","sha256","bytes","dataset","session","purposes","protected","exposure","format","evidence","test_only","original"}
        if set(manifest)!={"schema","entries"} or manifest["schema"]!="ARK_V2_NATIVE_MANIFEST_V1":
            raise V2Error("NATIVE_MANIFEST_SCHEMA")
        entries=manifest["entries"]
        if len({e["path"] for e in entries})!=len(entries): raise V2Error("DUPLICATE_NATIVE_PATH")
        limits=pre["resource_limits"]
        if any(e["bytes"]>limits["max_native_object_bytes"] for e in entries):
            raise V2Error("NATIVE_OBJECT_MEMORY_PREFLIGHT_EXCEEDED")
        daily_sizes=sorted((e["bytes"] for e in entries if e["dataset"]=="DAILY"),reverse=True)[:150]
        upper_rows=limits["universe_rows_upper_bound"]*max(len(pre["split"]["FIT"])+len(pre["split"]["CAL"]),len(pre["split"]["FINAL"]))
        # Conservative Python native/provenance expansion + float64/copies.
        estimate=sum(daily_sizes)*15+upper_rows*(16384+95*8*8)
        if estimate>limits["ram_bytes"]:raise V2Error("NATIVE_ROUTE_RAM_PREFLIGHT_EXCEEDED")
        matched=[]
        for dataset,session,purpose in wanted:
            candidates=[e for e in entries if e["dataset"]==dataset and e["session"]==session and purpose in e["purposes"]]
            if len(candidates)!=1: raise V2Error("MISSING_OR_AMBIGUOUS_NATIVE_IDENTITY")
            e=candidates[0]
            if set(e)!=fields or e["protected"] is not False or e["test_only"] is not self.test_only:
                raise V2Error("PROTECTED_OR_TEST_NATIVE_SOURCE")
            if session not in pre["allowlists"].get(purpose,[]): raise V2Error("PURPOSE_DATE_NOT_ALLOWLISTED")
            if e["format"]!=pre["source_routes"][dataset.lower()]: raise V2Error("SOURCE_FORMAT_NOT_APPROVED")
            safe_path(self.root,e["path"])
            if self.test_only and self.fixture_pins.get(e["path"])!=(e["sha256"],e["bytes"]):
                raise V2Error("REAL_ROWS_OR_CHANGED_BYTES_IN_TEST_AUTHORITY")
            if not isinstance(e["bytes"],int) or e["bytes"]<0 or len(e["sha256"])!=64:
                raise V2Error("SOURCE_SIZE_HASH_REQUIRED")
            original=e["original"]
            if (set(original)!={"source_id","sha256","bytes","dataset","allowed_record_dates","allowed_purposes","rights_reference"}
                    or original["dataset"]!=dataset or session not in original["allowed_record_dates"]
                    or purpose not in original["allowed_purposes"] or not original["rights_reference"]
                    or len(original["sha256"])!=64 or type(original["bytes"]) is not int):
                raise V2Error("ORIGINAL_MANIFEST_RIGHTS_DATE_PURPOSE_MISMATCH")
            matched.append(e|{"authorized_purpose":purpose})
        return matched


def production_authority() -> Authority | None:
    """No owner channel is installed in this MODE A checkout.

    Host integration must supply independently authenticated OwnerGrant records
    to dispatch, including original text, complete precommit and artifact pins.
    Do not replace this with reading a user-supplied 'trusted=true' JSON file.
    """
    return None
