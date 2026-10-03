"""Read-only post-replay integrity audit; never used by Capital decisions."""
from __future__ import annotations
import argparse, gzip, hashlib, json
from decimal import Decimal
from pathlib import Path

from scripts.phase57_development_integrated_v0 import ARMS, CAPACITIES, PROTOCOL_V2_HASH, SAFETY


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(first, second, expected_sha):
    assert digest(first)==digest(second), "RUN_AB_BYTE_MISMATCH"
    with gzip.open(first,"rt") as stream:
        result=json.load(stream)
    assert result["schema"]=="phase57-development-integrated-v0-result-v1"
    assert result["controllingProtocolV2Sha256"]==PROTOCOL_V2_HASH
    assert result["sourceLedgerSha256"]=="770f02612cdd97ed2420f14a2fe6ab6ed1f50a96f222afa9b3c376982c8ea476"
    assert result["exitStatus"]=="BENCHMARK_NOT_FINAL_EXIT"
    assert result["developmentSubsetOnly"] is True and len(result["cohortSessions"])==34
    assert result["safety"]==SAFETY and not any(result["safety"].values())
    assert result["protectedPartitionsOpened"]==result["providerRequests"]==0
    expected={arm+"_MAX"+str(n) for arm in ARMS for n in CAPACITIES}
    assert set(result["variants"])==expected
    summary={}
    for name,container in result["variants"].items():
        ledger,card=container["ledger"],container["card"]
        assert ledger["safety"]==card["safety"]==SAFETY
        assert name==ledger["arm"]+"_MAX"+str(ledger["capacity"])
        assert card["entryArm"]==ledger["arm"] and card["capacity"]==ledger["capacity"]
        assert card["exitStatus"]=="BENCHMARK_NOT_FINAL_EXIT" and card["noFinalExitClaim"]
        funded=ledger["funded"]; closed=ledger["closed"]
        assert len(funded)==card["entries"] and len(closed)==card["exits"]
        assert len(ledger["endOpenEntryIds"])==card["censoredEndOpen"]
        assert len(funded)==len(closed)+len(ledger["endOpenEntryIds"])
        assert set(ledger["unresolvedEntryIds"])<=set(ledger["endOpenEntryIds"])
        assert all(Decimal(x["cashJpy"])>=0 and x["openCount"]<=ledger["capacity"]
                   for x in ledger["snapshots"])
        spent=sum((Decimal(x["notionalJpy"]) for x in funded.values()),Decimal(0))
        returned=sum((Decimal(x["notionalJpy"])+Decimal(x["realizedPnlJpy"])
                      for x in closed),Decimal(0))
        assert Decimal(ledger["finalCashJpy"])==Decimal(1000000)-spent+returned
        assert len(ledger["snapshots"])==card["allEvents"]
        if card["censoredEndOpen"] or ledger["snapshots"][-1]["equityJpy"] is None:
            assert card["portfolioReturnPct"] is None and card["finalEquityJpy"] is None
        else:
            assert card["portfolioReturnPct"] is not None
        if card["completeMarkedEvents"]<card["allEvents"]:
            assert card["fullPeriodMaxDrawdownPct"] is None
        assert not any(k in entry for event in ledger["events"] for entry in event["sizing"]
                       for k in ("entryToPostEntryHighPct","canonicalBucket","exitPrice","futureHigh","capture"))
        assert set(card["attributionEvaluatorOnly"])=={
            "POST_ENTRY_UPSIDE_GE5","CANONICAL_L2H_GE5"}
        assert all(not x["fedBackToCapital"] for x in card["attributionEvaluatorOnly"].values())
        assert card["attributionEvaluatorOnly"]["POST_ENTRY_UPSIDE_GE5"]["available"]==(
            222 if ledger["arm"]==ARMS[0] else 200)
        assert card["attributionEvaluatorOnly"]["CANONICAL_L2H_GE5"]["available"]==(
            387 if ledger["arm"]==ARMS[0] else 381)
        summary[name]={k:card[k] for k in ("portfolioReturnPct","finalEquityJpy","realizedPnlJpy",
                   "entries","exits","unresolved","censoredEndOpen","capacityRejects",
                   "insufficientCashRejects","pricedMinuteCoverage")}
    assert set(result["enrichment"])==set(ARMS)
    for arm in ARMS:
        enrich=result["enrichment"][arm]
        assert enrich["evaluatorOnly"] is True
        assert enrich["primarySupport"]==(222 if arm==ARMS[0] else 200)
        assert enrich["secondarySupport"]==(387 if arm==ARMS[0] else 381)
        assert set(enrich["top"])=={"1","3","5"}
    assert set(result["paired"])=={"3","4","5"}
    return {"status":"INTEGRITY_PASS_NOT_FINAL_EXIT","executionSha":expected_sha,
            "protocolSha256":PROTOCOL_V2_HASH,"resultSha256":digest(first),
            "runABByteIdentical":True,"sixVariants":summary,"safety":SAFETY}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--a",type=Path,required=True)
    p.add_argument("--b",type=Path,required=True)
    p.add_argument("--execution-sha",required=True)
    p.add_argument("--scorecard-out",type=Path)
    args=p.parse_args()
    receipt=audit(args.a,args.b,args.execution_sha)
    if args.scorecard_out is not None:
        assert not args.scorecard_out.exists(),"APPEND_ONLY_SCORECARD"
        with gzip.open(args.a,"rt") as stream:
            result=json.load(stream)
        output={"schema":"phase57-development-integrated-v0-full-scorecard-v1",
                "executionSha":args.execution_sha,"protocolSha256":PROTOCOL_V2_HASH,
                "sourceArtifactResultSha256":receipt["resultSha256"],
                "exitStatus":"BENCHMARK_NOT_FINAL_EXIT",
                "enrichment":result["enrichment"],
                "scorecards":{k:v["card"] for k,v in result["variants"].items()},
                "paired":{k:{q:z[q] for q in ("commonCandidateOpportunities",
                                       "commonFundedOpportunities")}
                          for k,z in result["paired"].items()},
                "integrity":receipt}
        raw=(json.dumps(output,sort_keys=True,separators=(",",":"),
                        ensure_ascii=False,allow_nan=False)+"\n").encode()
        with args.scorecard_out.open("wb") as handle:
            with gzip.GzipFile(filename="",fileobj=handle,mode="wb",mtime=0) as z:
                z.write(raw)
        receipt["fullScorecardSha256"]=digest(args.scorecard_out)
    print(json.dumps(receipt,sort_keys=True,allow_nan=False))


if __name__=="__main__": main()
