"""Admit already-produced prior State rows with explicit frozen upstream lineage.

Does not modify State9, select a different classifier, fit an upstream model,
or turn a displayed carried label into an observed formal State.
"""
from __future__ import annotations

import json
from functools import lru_cache

from preopen_io import verify_entry
from preopen_selector import PreopenError, PreopenConfig, stamp, digest


@lru_cache(maxsize=4)
def _ledger(path, sha256, size, private_root):
    verified=verify_entry({"path":path,"sha256":sha256,"bytes":size},private_root)
    with verified.open(encoding="utf-8") as stream:
        data=json.load(stream)
    if data.get("schema") != "ARK_PREOPEN_PRIOR_STATE_LEDGER_V1":
        raise PreopenError("WRONG_PRIOR_STATE_LEDGER_SCHEMA")
    rows=data["rows"]
    keys=[(r["session"],r["symbol"]) for r in rows]
    if len(keys)!=len(set(keys)):
        raise PreopenError("DUPLICATE_PRIOR_STATE_IDENTITY")
    return dict(zip(keys,rows))


def admitted_previous_state(store, previous_session, code, target_session):
    contract=store.request.get("previousStateContract")
    if contract is None:
        return None,"PIT_OR_BASIS_UNVERIFIED"
    if (contract.get("reviewed") is not True or not contract.get("evidenceReference")
            or contract.get("cutoffPolicy") != "D_MINUS_1_CONTINUOUS_CLOSE_FORMAL_OBSERVED"):
        raise PreopenError("PRIOR_STATE_INPUT_CONTRACT_UNVERIFIED")
    entry=contract["ledger"]
    rows=_ledger(entry["path"],entry["sha256"],entry["bytes"],str(store.private_root))
    row=rows.get((previous_session,code))
    if row is None:
        return None,"NOT_AVAILABLE_IN_SOURCE"
    if row.get("formalObserved") is not True or row.get("primary") is None:
        return None,row.get("missingReason","FORMAL_STATE_NOT_OBSERVED")
    cutoff=PreopenConfig().at(target_session)
    if (row["session"]!=previous_session or previous_session>=target_session
            or stamp(row["knownAt"])>cutoff or stamp(row["observedAt"])>cutoff):
        raise PreopenError("PRIOR_STATE_SESSION_OR_AVAILABILITY")
    lineage=row.get("upstreamLineage",{})
    if lineage.get("contractSha256")!=contract.get("contractSha256"):
        raise PreopenError("PRIOR_STATE_CONTRACT_NOT_BOUND")
    if lineage.get("artifactSha256")!=contract.get("artifactSha256"):
        raise PreopenError("PRIOR_STATE_ARTIFACT_NOT_BOUND")
    if lineage.get("requiresFit") is False:
        if (lineage.get("kind")!="DETERMINISTIC_FROZEN_RULES"
                or lineage.get("profileSha256")!=contract.get("profileSha256")
                or not contract.get("profileSha256")):
            raise PreopenError("PRIOR_STATE_NONFITTED_RULE_LINEAGE_REQUIRED")
    elif lineage.get("requiresFit") is True:
        if not lineage.get("lastFitSession") or lineage["lastFitSession"]>=previous_session:
            raise PreopenError("PRIOR_STATE_FUTURE_UPSTREAM_FIT")
    else:
        raise PreopenError("PRIOR_STATE_FIT_NATURE_UNKNOWN")
    if not row.get("sourceHashes") or set(row["sourceHashes"])-set(store.sources_by_hash):
        raise PreopenError("PRIOR_STATE_SOURCE_NOT_IN_ADMITTED_MANIFEST")
    return {**row,"pitVerified":True,"verificationBasis":"REVIEWED_CAUSAL_INPUT_NOT_ACTUAL_RECEIVE"},None
