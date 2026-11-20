"""Post-R50 evaluator-only anatomy; never imported by decision modules."""
from __future__ import annotations
import argparse, collections, gzip, hashlib, json, statistics
from pathlib import Path
import numpy as np

ARMS=("IMMEDIATE","ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF")
SIGNALS=("CONTINUATION","BREAKOUT","COMPRESSION_EXPANSION","HIGHER_LOW","LOWER_WICK","RECLAIM")
NUMERIC=("facts.currentReturnPct","facts.certifiedMfePct","facts.certifiedGivebackPp","facts.timeSincePeak","facts.barsHeld",
         "facts.newPeak","position.fullOwnedPrefix","position.observedRunningHigh","position.observedPeakGivebackPp",
         "stateDwellObservedActiveMinutes","history.3.stateChanges","history.5.stateChanges","history.10.stateChanges",
         "facts.stateRecovery","facts.failedRecovery","facts.weakRun","facts.momentum5Pct","facts.range5Pct","facts.signalTrueN",
         "facts.signalFalseN","facts.signalUnknownN","facts.signalLossN","facts.signalRecoveryN",
         "history.3.stateKnown","history.5.stateKnown","history.10.stateKnown",
         "history.3.signal.CONTINUATION.true","history.3.signal.CONTINUATION.false",
         "history.5.signal.CONTINUATION.true","history.5.signal.CONTINUATION.false",
         "history.10.signal.CONTINUATION.true","history.10.signal.CONTINUATION.false",
         "history.3.signal.RECLAIM.true","history.3.signal.RECLAIM.false",
         "history.5.signal.RECLAIM.true","history.5.signal.RECLAIM.false",
         "history.10.signal.RECLAIM.true","history.10.signal.RECLAIM.false",
         "position.missingOwnedBars","position.observedOwnedBars")
PATTERN=("STRUCT/Lrising","STRUCT/Hrising","STRUCT/turningUp","STRUCT/recoveryFromLOD",
         "STRUCT/pullbackFromHOD","STRUCT/compressionExpansion","LOCAL5/trendEfficiency",
         "LOCAL5/volatility","LOCAL5/return","LOCAL10/return")

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def rows(p):
    with gzip.open(p,"rt") as f:
        for line in f: yield json.loads(line)

def median(a):
    return None if not a else statistics.median(a)

def summarize(group,fields):
    out={}
    for field in fields:
        a=[x["now"][field] for x in group if x["now"][field] is not None]
        out[field]={"n":len(a),"median":median(a),"missing":len(group)-len(a)}
        if field.startswith("currentState.") or field.startswith("signal.") or field.startswith("entryToCurrentState"):
            out[field]["counts"]=dict(collections.Counter(a))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--r50",type=Path,required=True)
    ap.add_argument("--r45",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    assert not args.out.exists()
    results=json.loads((args.r50/"result.json").read_text())
    assert results["status"]=="NO_SELECTION_STOP" and results["runABIdentical"] and results["candidateCount"]==2
    assert results["protocolSha256"]=="011b4959bf7cd343694f44e2986d13d87c07b6fa238dc326f5273e86885afe18"
    for c in ("R50_A_LIFECYCLE","R50_B_FAILED_RECOVERY"):
        assert sha(args.r50/f"{c}-run-a.jsonl.gz")==sha(args.r50/f"{c}-run-b.jsonl.gz")==results["ledgerHashes"][c]
    a={(x["entryArm"],x["entryId"]):x for x in rows(args.r50/"R50_A_LIFECYCLE-run-a.jsonl.gz")}
    b={(x["entryArm"],x["entryId"]):x for x in rows(args.r50/"R50_B_FAILED_RECOVERY-run-a.jsonl.gz")}
    assert len(a)==len(b)==2257 and set(a)==set(b)
    changes={}
    for k,x in a.items():
        baseline=b[k]
        if x["metrics"]["entryToPostEntryHighPct"]<5 or x["exitMinute"]==baseline["exitMinute"]: continue
        assert x["authority"]=="WINNER_HARVEST" and x["exitKind"]=="MODEL_EXIT"
        d=x["metrics"]["entryToExitNetPct"]-baseline["metrics"]["entryToExitNetPct"]
        if d==0: continue  # A different clock time at the same executable price is not a changed economic exit.
        changes[k]={"arm":k[0],"entryId":k[1],"opportunity":x["opportunity"],"session":x["session"],
                    "nowMinute":x["decisionNow"],"exitMinute":x["exitMinute"],
                    "deltaNetPp":d,"deltaCapturePct":x["metrics"]["postEntryUpsideCapturePct"]-baseline["metrics"]["postEntryUpsideCapturePct"],
                    "improve":d>0,"aPremature":x["metrics"]["premature"],
                    "evaluatorPostExitHighKnownAt":x["metrics"]["postEntryHighKnownAt"]}
    assert len([x for x in changes.values() if x["arm"]==ARMS[0]])==32
    assert len([x for x in changes.values() if x["arm"]==ARMS[1]])==32
    manifest=json.loads((args.r45/"gen3/data/data-receipt.json").read_text())
    numeric_names=manifest["numericColumns"]; categorical_names=manifest["categoricalColumns"]; pattern_names=manifest["patternColumns"]
    catmap=json.loads((args.r45/"gen3/data/categorical-representation.json").read_text())["maps"]
    cats=("entryState.state","currentState.state","entryToCurrentState") + tuple(
        f"signal.{sig}.{suffix}" for sig in SIGNALS for suffix in ("currentTriState","observedTrueToFalseTriState"))
    assert set(NUMERIC)<=set(numeric_names) and set(PATTERN)<=set(pattern_names) and set(cats)<=set(categorical_names)
    with np.load(args.r45/"gen3/data/decision-features.npz",allow_pickle=False) as z:
        numeric=z["numeric"]; categorical=z["categorical"]; pattern=z["pattern"]; fresh=z["fresh"]
    with np.load(args.r45/"gen3/oof-predictions.npz",allow_pickle=False) as z:
        scores=z["HGB_GEN3_UTILITY_PATTERN187"]
    matching={}; prior={}
    for idx,x in enumerate(rows(args.r45/"gen3/data/row-identities.jsonl.gz")):
        k=(x["arm"],x["entryId"])
        if k in changes and changes[k]["nowMinute"]==x["now"]:
            assert k not in matching
            matching[k]=idx
        if k in changes and x["now"]<changes[k]["nowMinute"]:
            prior[k]=idx
    assert len(matching)==64
    for k,i in matching.items():
        now={}
        for f in NUMERIC:
            v=float(numeric[i,numeric_names.index(f)]); now[f]=v if np.isfinite(v) else None
        for f in PATTERN:
            v=float(pattern[i,pattern_names.index(f)]); now[f]=v if np.isfinite(v) else None
        for f in cats:
            v=int(categorical[i,categorical_names.index(f)])
            inv={v:k for k,v in catmap[f].items()}
            now[f]=inv.get(v)
        if k in prior:
            f="currentState.state"; v=int(categorical[prior[k],categorical_names.index(f)])
            now["previousState.state"]={v:k for k,v in catmap[f].items()}.get(v)
        else: now["previousState.state"]=None
        now["previousToCurrentState"]=(None if now["previousState.state"] is None or now["currentState.state"] is None else
            now["previousState.state"]+"->"+now["currentState.state"])
        for name,v in zip(("C","P","D"),scores[i]):
            now["score."+name]=float(v) if np.isfinite(v) else None
        now["fresh"]=bool(fresh[i])
        assert now["fresh"] and now["position.fullOwnedPrefix"]==1
        assert now["facts.certifiedGivebackPp"] is not None and now["facts.certifiedMfePct"] is not None
        changes[k]["now"]=now
    case=list(changes.values())
    fields=list(NUMERIC)+list(PATTERN)+list(cats)+["previousState.state","previousToCurrentState","score.C","score.P","score.D","fresh"]
    byarm={}
    for arm in ARMS:
        group=[x for x in case if x["arm"]==arm]
        byarm[arm]={"n":len(group),"improve":sum(x["improve"] for x in group),
            "worsen":sum(not x["improve"] for x in group),
            "medianDeltaNetPp":median([x["deltaNetPp"] for x in group]),
            "improveNow":summarize([x for x in group if x["improve"]],fields),
            "worsenNow":summarize([x for x in group if not x["improve"]],fields),
            "premature":{v:sum(x["aPremature"]==v for x in group) for v in (False,True)}}
        byarm[arm]["structHrising"]={
            str(label): {str(status):sum((x["improve"]==label and x["now"]["STRUCT/Hrising"]==status) for x in group)
                    for status in (0.0,1.0,None)} for label in (True,False)}
        byarm[arm]["stateTransition"]={
            str(label):dict(collections.Counter(x["now"]["previousState.state"]+"->"+x["now"]["currentState.state"]
                for x in group if x["improve"]==label)) for label in (True,False)}
        primary=[k for k,x in a.items() if k[0]==arm and x["metrics"]["entryToPostEntryHighPct"]>=5]
        cap_a=[a[k]["metrics"]["postEntryUpsideCapturePct"] for k in primary]
        cap_b=[b[k]["metrics"]["postEntryUpsideCapturePct"] for k in primary]
        # Evaluator-only bound, not an executable policy or an admitted decision input.
        byarm[arm]["aOrBUpperBoundDiagnostic"]={
            "AAbove50":sum(v>=50 for v in cap_a),"BAbove50":sum(v>=50 for v in cap_b),
            "eitherAbove50":sum(max(v,w)>=50 for v,w in zip(cap_a,cap_b)),
            "medianOfPerCaseBetterFrozenAorB":median([max(v,w) for v,w in zip(cap_a,cap_b)])}
    im={x["opportunity"]:x for x in case if x["arm"]==ARMS[0]}
    r1={x["opportunity"]:x for x in case if x["arm"]==ARMS[1]}
    common=sorted(set(im)&set(r1))
    paired={"bothChangedOpportunities":len(common),"improveBoth":sum(im[k]["improve"] and r1[k]["improve"] for k in common),
      "worsenBoth":sum(not im[k]["improve"] and not r1[k]["improve"] for k in common),
      "discordant":sum(im[k]["improve"]!=r1[k]["improve"] for k in common),
      "nowSameMinute":sum(im[k]["nowMinute"]==r1[k]["nowMinute"] for k in common)}
    paired["uniqueChangedOpportunities"]=len(set(im)|set(r1))
    paired["commonHrisingByOutcome"]={
        str(label):{str(status):sum(im[k]["improve"]==label and im[k]["now"]["STRUCT/Hrising"]==status for k in common)
          for status in (0.0,1.0,None)} for label in (True,False)}
    split=json.loads((args.r45/"r45-tested-ci/source/docs/evidence/phase57-comprehensive-exit-v1/GEN3_PRECOMMIT_R45.json").read_text())
    fold={s:f["fold"] for f in split["split"]["folds"] for s in f["score"]}
    byfold={arm:{str(f):{"n":sum(z["arm"]==arm and fold[z["session"]]==f for z in case),
                  "improve":sum(z["arm"]==arm and fold[z["session"]]==f and z["improve"] for z in case),
                  "hrising1Improve":sum(z["arm"]==arm and fold[z["session"]]==f and z["improve"] and z["now"]["STRUCT/Hrising"]==1 for z in case),
                  "hrising1Worsen":sum(z["arm"]==arm and fold[z["session"]]==f and not z["improve"] and z["now"]["STRUCT/Hrising"]==1 for z in case)}
                 for f in range(1,5)} for arm in ARMS}
    # Leakage fence: the feature projection is never passed into a decision or replay.
    evidence={"schema":"phase57-r50-changed-exit-anatomy-v1","source":{"r50ResultSha256":sha(args.r50/"result.json"),
      "r45DecisionFeaturesSha256":sha(args.r45/"gen3/data/decision-features.npz"),
      "r45PredictionsSha256":sha(args.r45/"gen3/oof-predictions.npz")},
      "caseSelection":"Evaluator-only post-entry-upside>=5 and A exit differs B; no decision branch or training strata",
      "byArm":byarm,"byFold":byfold,"commonPaired":paired,"caseRows":case,
      "outcomeFieldsEvaluatorOnly":["deltaNetPp","deltaCapturePct","improve","aPremature","evaluatorPostExitHighKnownAt"],
      "decisionProhibited":True}
    args.out.write_text(json.dumps(evidence,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n")
    print(json.dumps({"byArm":{k:{a:b for a,b in v.items() if a not in ("improveNow","worsenNow")} for k,v in byarm.items()},
      "commonPaired":paired,"outputSha256":sha(args.out)},sort_keys=True))
if __name__=="__main__": main()
