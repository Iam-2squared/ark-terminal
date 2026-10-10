#!/usr/bin/env python3
"""Score Phase57 G7 independent reviewer CSVs.

This tool scores the preregistered mechanical G7 criteria only.
It does not inspect market outcomes and does not adjudicate reviewer rationales.
"""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path

ISSUE_TAGS = {
    "BOUNDARY_OR_TOLERANCE_SUSPECTED",
    "OBSERVATION_OR_PROVENANCE_PROBLEM",
    "VOCABULARY_GAP_CANDIDATE",
    "STATUS_SEMANTICS_PROBLEM",
    "INDETERMINATE",
}
SUFFICIENT = "SEMANTICS_SUFFICIENT"

def load_response(path: Path) -> dict[str, dict]:
    out = {}
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            tags = {x.strip() for x in (r.get("tags_pipe_separated") or "").split("|") if x.strip()}
            out[r["caseId"]] = {"tags": tags, "rationale": r.get("rationale", "")}
    return out

def binary_issue(tags: set[str]) -> int:
    return int(bool(tags & ISSUE_TAGS))

def kappa(a: list[int], b: list[int]):
    n=len(a)
    if not n: return None
    po=sum(x==y for x,y in zip(a,b))/n
    pa=sum(a)/n; pb=sum(b)/n
    pe=pa*pb+(1-pa)*(1-pb)
    if abs(1-pe)<1e-12: return None
    return (po-pe)/(1-pe)

def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: score_g7_reviews.py SEALED_ADMIN_KEY.json reviewerA.csv reviewerB.csv")
    key=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    A=load_response(Path(sys.argv[2])); B=load_response(Path(sys.argv[3]))
    cases=key["cases"]
    ids={x["caseId"] for x in cases}
    if set(A)!=ids or set(B)!=ids:
        raise SystemExit("RESPONSE_CASE_SET_MISMATCH")

    controls=[x for x in cases if x["kind"]=="CONTROL"]
    actual=[x for x in cases if x["kind"]=="ACTUAL"]

    def control_result(resp):
        missed=[]
        for x in controls:
            tags=resp[x["caseId"]]["tags"]
            if SUFFICIENT in tags and not (tags & ISSUE_TAGS):
                missed.append(x["caseId"])
            elif not (tags & ISSUE_TAGS):
                missed.append(x["caseId"])
        return missed

    missedA=control_result(A); missedB=control_result(B)
    a=[binary_issue(A[x["caseId"]]["tags"]) for x in actual]
    b=[binary_issue(B[x["caseId"]]["tags"]) for x in actual]
    raw=sum(x==y for x,y in zip(a,b))/len(actual)
    kap=kappa(a,b)
    gaps=sorted({
        x["caseId"] for x in actual
        if "VOCABULARY_GAP_CANDIDATE" in A[x["caseId"]]["tags"]
        or "VOCABULARY_GAP_CANDIDATE" in B[x["caseId"]]["tags"]
    })
    controls_pass=(not missedA and not missedB)
    agreement_pass=(kap is not None and kap>=0.60) or (kap is None and raw>=0.85)
    disposition=(
        "G7_MECHANICAL_PASS_PENDING_RATIONALE_ADJUDICATION"
        if controls_pass and agreement_pass and not gaps
        else "G7_FAIL_OR_ADJUDICATION_REQUIRED"
    )
    out={
        "actualN":len(actual),"controlN":len(controls),
        "reviewerAControlMisses":missedA,
        "reviewerBControlMisses":missedB,
        "rawAgreement":raw,
        "cohensKappa":kap,
        "vocabularyGapCases":gaps,
        "controlsPass":controls_pass,
        "agreementPass":agreement_pass,
        "disposition":disposition,
        "note":"Any actual future/PnL leakage finding or blocking vocabulary gap requires human adjudication and can still hard-fail G7."
    }
    print(json.dumps(out,indent=2))

if __name__=="__main__":
    main()
