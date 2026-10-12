"""Offline batch runner for admitted preopen snapshots and separate raw labels.

python run_preopen_selector.py --bundle /private/bundle.json --output /private/new-run
No credentials, network downloads, broker writes or public raw upload are used.
The bundle is an admission product, not a substitute for the missing original
Daily/master/finance/Tick joins or the existing sealed-session audit.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from fractions import Fraction

from preopen_selector import (CONTRACT, POS_BINS, PreopenError, build_preopen_features,
    compare_preopen_watchlists, digest, evaluate_open_high, make_watchlist,
    row_key, summarize_open_high)
from preopen_model import validate_plan, train_preopen_model, save_private_model
from preopen_model import load_private_model
from preopen_io import private_path, verify_entry, read_jsonl, write_json, utc_now, SAFE_FLAGS

ROLES = tuple(f"{s}_{t}" for s in ("fit","calibration","report") for t in ("snapshots","labels"))


def load_verified_input(entry: dict, private_root: Path) -> list[dict]:
    return list(read_jsonl(entry, private_root))


def load_feature_input(entry, root):
    if entry.get("format") == "ARK_PREOPEN_COLUMNAR_FEATURES_V1":
        from preopen_feature_store import FeatureStore
        return FeatureStore(verify_entry(entry, root), private_root=root)
    snapshots = load_verified_input(entry, root)
    if entry.get("format") == "ARK_PREOPEN_FEATURE_ROWS_V1":
        return snapshots
    return [build_preopen_features(r) for r in snapshots]


def load_outcome_input(entry, root):
    if entry.get("format") == "ARK_PREOPEN_NATIVE_LABEL_MANIFEST_V1":
        from preopen_native_source import read_native_report_labels
        return list(read_native_report_labels(entry, root))
    return load_verified_input(entry, root)


def index_labels(labels: list[dict], allowed: set) -> dict:
    out = {}
    for lab in labels:
        key = row_key(lab)
        if key[0] not in allowed or key in out:
            raise PreopenError("OUTSIDE_PARTITION_OR_DUPLICATE_LABEL")
        out[key] = lab
    return out


def evaluate_population(rows: list[dict], labels: dict) -> dict:
    """Teacher evaluation is independent of model ranking and future eligibility."""
    result = {}
    for r in rows:
        w = make_watchlist([r],{row_key(r):0.0})
        result[row_key(r)] = evaluate_open_high(w,labels)[0]
    return result


def bootstrap_day_deltas(daily: list[dict], draws=2000, seed=20261012) -> dict:
    if len(daily)<2:
        return {"status":"INSUFFICIENT_DISTINCT_SESSIONS","sessionN":len(daily)}
    rng=random.Random(seed)
    values={str(t):[] for t in (1,2,3,4,5)}
    for _ in range(draws):
        batch=rng.choices(daily,k=len(daily))
        an=sum(d["baseline"]["selectedN"] for d in batch)
        bn=sum(d["candidate"]["selectedN"] for d in batch)
        for t in values:
            a=sum(d["baseline"]["highHitN"][t] for d in batch)
            b=sum(d["candidate"]["highHitN"][t] for d in batch)
            values[t].append(100*(b/bn-a/an))
    result={}
    for t,v in values.items():
        v.sort()
        result[t]=[v[int(.025*(draws-1))],v[int(.975*(draws-1))]]
    return {"status":"DESCRIPTIVE_PAIRED_DAY_BOOTSTRAP_NOT_GENERALIZATION_CERTIFICATE",
            "sessionN":len(daily),"draws":draws,"seed":seed,
            "allSelectedHitRateDelta95PctPoints":result}


def preflight_bundle(bundle: dict, output: Path) -> Path:
    if bundle.get("contract") != CONTRACT or set(bundle.get("inputs",{})) != set(ROLES):
        raise PreopenError("INCOMPLETE_PREOPEN_BUNDLE")
    root = Path(bundle["privateRoot"]).resolve()
    private_path(output, root)
    validate_plan(bundle["plan"], {})
    if bundle["plan"]["mode"] == "AUTHORIZED_DEVELOPMENT":
        evidence_path=verify_entry(bundle["plan"]["currentReuseEvidence"],root)
        evidence=json.loads(evidence_path.read_text())
        from preopen_reuse_authorization import validate_reuse_authorization
        validate_reuse_authorization(evidence, work_id=bundle["plan"].get("reuseWorkId"))
    for role, entry in bundle["inputs"].items():
        private_path(entry["path"], root)
        if not isinstance(entry.get("bytes"), int) or entry["bytes"] < 0:
            raise PreopenError("INPUT_SIZE_REQUIRED")
        if not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64:
            raise PreopenError("INPUT_HASH_REQUIRED")
    # No Report label stat/open/hash/parse occurs here. The reference is only
    # a descriptor until all watchlists are immutably persisted.
    return root


def train_bundle(bundle: dict, output: Path) -> dict:
    private_root = preflight_bundle(bundle, output)
    output = private_path(output, private_root)
    if output.exists():
        raise PreopenError("REFUSE_OVERWRITE_RESULT")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    write_json(output/"FIT_ATTEMPT.json", {
        "schema": "ARK_PREOPEN_FINITE_FIT_ATTEMPT_V1", "bundleHash": digest(bundle),
        "startedAt": utc_now(), "candidateBudget": 1, "headFitsMax": 10,
        "calibrationFitsMax": 10, "automaticRetry": False, **SAFE_FLAGS})
    plan=bundle["plan"]
    rows={s:load_feature_input(bundle["inputs"][s+"_snapshots"], private_root)
          for s in ("fit","calibration")}
    validate_plan(plan,rows)
    raw={s:index_labels(load_outcome_input(bundle["inputs"][s+"_labels"],private_root),
                        set(plan["splits"][s])) for s in rows}
    fy=evaluate_population(rows["fit"],raw["fit"])
    cy=evaluate_population(rows["calibration"],raw["calibration"])
    def execution_event(event, head):
        with (output/"FIT_EXECUTION_LEDGER.jsonl").open("a",encoding="utf-8") as stream:
            stream.write(json.dumps({"event":event,"head":head,"mode":plan["mode"],
                                    "at":utc_now(),"bundleHash":digest(bundle)})+"\n")
    model=train_preopen_model(rows["fit"],fy,rows["calibration"],cy,plan,
                             execution_event=execution_event)
    receipt=save_private_model(model,output/"private_model")
    stage={"schema":"ARK_PREOPEN_TRAINING_STAGE_V1","bundleHash":digest(bundle),
           "model":receipt,"completedAt":utc_now(),"reportLabelsOpened":False,
           "reportFeatureInputOpened":False, **SAFE_FLAGS}
    write_json(output/"TRAINING_STAGE.json",stage)
    return stage


def predict_bundle(bundle: dict, output: Path) -> dict:
    private_root = preflight_bundle(bundle, output)
    output = private_path(output, private_root)
    stage=json.loads((output/"TRAINING_STAGE.json").read_text())
    if stage["bundleHash"] != digest(bundle):
        raise PreopenError("TRAINING_BUNDLE_CHANGED")
    receipt=stage["model"]
    model=load_private_model(output/"private_model",private_root=private_root,
        expected_model_sha256=receipt["modelFileSha256"],
        expected_schema_sha256=receipt["featureSchemaHash"])
    rows=load_feature_input(bundle["inputs"]["report_snapshots"],private_root)
    validate_plan(bundle["plan"], {"report":rows})
    groups=defaultdict(list)
    for r in rows:groups[r["session"]].append(r)
    watchlists, baselines, universe_keys = [], [], []
    for session, rs in sorted(groups.items()):
        watchlists.append(model.watchlist(rs))
        baselines.append(make_watchlist(rs,{row_key(r):r["priorTurnover"] for r in rs}))
        universe_keys.append({"session":session,"items":[
            {"key":row_key(r),"featureHash":r["featureHash"]} for r in rs]})
    c=write_json(output/"PRIVATE_WATCHLISTS.json",watchlists)
    b=write_json(output/"PRIVATE_BASELINE_WATCHLISTS.json",baselines)
    u=write_json(output/"PRIVATE_UNIVERSE_KEYS.json",universe_keys)
    prediction={"schema":"ARK_PREOPEN_PREDICTION_STAGE_V1","bundleHash":digest(bundle),
                "completedAt":utc_now(),"watchlists":c,"baselineWatchlists":b,
                "eligibleKeys":u,"reportLabelsOpened":False, **SAFE_FLAGS}
    write_json(output/"PREDICTION_STAGE.json",prediction)
    return prediction


def evaluate_bundle(bundle: dict, output: Path) -> dict:
    private_root = preflight_bundle(bundle, output)
    output = private_path(output, private_root)
    stage=json.loads((output/"TRAINING_STAGE.json").read_text())
    prediction=json.loads((output/"PREDICTION_STAGE.json").read_text())
    if stage["bundleHash"] != digest(bundle) or prediction["bundleHash"] != digest(bundle):
        raise PreopenError("FIXED_BUNDLE_CHANGED")
    fixed={}
    for role in ("watchlists","baselineWatchlists","eligibleKeys"):
        p=verify_entry(prediction[role],private_root)
        fixed[role]=json.loads(p.read_text())
    # This is the FIRST Report label read, after model and ALL watchlists fixed.
    write_json(output/"REPORT_LABEL_OPEN_ATTEMPT.json",{
        "openedAt":utc_now(),"predictionStageHash":digest(prediction),
        "modelFileSha256":stage["model"]["modelFileSha256"], **SAFE_FLAGS})
    labels=index_labels(load_outcome_input(bundle["inputs"]["report_labels"],private_root),
                        set(bundle["plan"]["splits"]["report"]))
    rows=load_feature_input(bundle["inputs"]["report_snapshots"],private_root)
    validate_plan(bundle["plan"], {"report": rows})
    groups=defaultdict(list)
    for r in rows:groups[r["session"]].append(r)
    expected_keys={x["session"]:x["items"] for x in fixed["eligibleKeys"]}
    for session, rs in groups.items():
        actual=[{"key":list(row_key(r)),"featureHash":r["featureHash"]} for r in rs]
        if actual != expected_keys[session]:
            raise PreopenError("FIXED_ELIGIBLE_UNIVERSE_CHANGED")
    watchlists=fixed["watchlists"]
    baselines={w["session"]:w for w in fixed["baselineWatchlists"]}
    candidate_rows,baseline_rows,daily,watchlists=[],[],[],[]
    random_expected={k:Fraction(0) for k in POS_BINS}
    random_unknown=Fraction(0)
    random_low, random_close = defaultdict(Fraction), defaultdict(Fraction)
    random_up_hits={str(k):Fraction(0) for k in (1,2,3,4,5)}
    random_low_hits={str(k):Fraction(0) for k in (1,2,3,5)}
    random_close_negative=Fraction(0)
    for candidate in fixed["watchlists"]:
        session=candidate["session"]
        rs=groups[session]
        baseline=baselines[session]
        daily.append(compare_preopen_watchlists(baseline,candidate,labels))
        candidate_rows.extend(evaluate_open_high(candidate,labels))
        baseline_rows.extend(evaluate_open_high(baseline,labels))
        population=list(evaluate_population(rs,labels).values())
        scale=Fraction(candidate["selectedN"],len(rs))
        for lab in population:
            if lab["status"]=="KNOWN":
                random_expected[lab["bucket"]]+=scale
                random_low[lab["lowBucket"]]+=scale
                random_close[lab["closeBucket"]]+=scale
                for k in random_up_hits:random_up_hits[k]+=scale*lab["upHits"][k]
                for k in random_low_hits:random_low_hits[k]+=scale*lab["lowHits"][k]
                random_close_negative+=scale*lab["closeNegative"]
            else:random_unknown+=scale
    if sum(random_expected.values())+random_unknown != sum(w["selectedN"] for w in fixed["watchlists"]):
        raise PreopenError("EXACT_RANDOM_EXPECTATION_CARDINALITY_MISMATCH")
    from preopen_report import extended_diagnostics, independent_recount, paired_day_uncertainty
    recount=independent_recount(fixed["watchlists"],labels,candidate_rows)
    summary={"schema":"ARK_PREOPEN_FULL_BATCH_REPORT_V2","contract":CONTRACT,
             "bundleHash":digest(bundle),"mode":bundle["plan"]["mode"],
             "training":stage["model"],"sessions":len(daily),
             "candidate":summarize_open_high(candidate_rows),
             "previousSessionTurnoverTopK":summarize_open_high(baseline_rows),
             "exactSameUniverseRandom":{
                 "expectedBucketN":{k:float(v) for k,v in random_expected.items()},
                 "expectedUnknownN":float(random_unknown),
                 "expectedLowBucketN":{k:float(v) for k,v in random_low.items()},
                 "expectedCloseBucketN":{k:float(v) for k,v in random_close.items()},
                 "expectedUpHitN":{k:float(v) for k,v in random_up_hits.items()},
                 "expectedLowHitN":{k:float(v) for k,v in random_low_hits.items()},
                 "expectedCloseNegativeN":float(random_close_negative),
                 "exactBucketRationals":{k:{"numerator":v.numerator,"denominator":v.denominator}
                                         for k,v in random_expected.items()},
                 "exactUnknownRational":{"numerator":random_unknown.numerator,
                                         "denominator":random_unknown.denominator},
                 "expectationsAreNotIntegerRealizedSelections":True},
             "pairedUncertainty":paired_day_uncertainty(daily),
             "diagnostics":extended_diagnostics(candidate_rows),
             "independentRecount":recount,
             "legacyFrozenComparison":"NOT_EXECUTED_NATIVE_INTRADAY_EVENTS_REQUIRED_LATER_INFO_NOT_FAIR_PREOPEN",
             "liveRuntimeCertified":False,"productionReady":False,
             "orders":0,"providerRequests":0,"portfolioReplays":0}
    write_json(output/"REPORT_AGGREGATE.json",summary)
    write_json(output/"PRIVATE_DAY_COMPARISON.json",daily)
    write_json(output/"PRIVATE_EVALUATED_ROWS.json",candidate_rows)
    write_json(output/"INDEPENDENT_RECOUNT_AUDIT.json",recount)
    return summary


def run_bundle(bundle: dict, output: Path) -> dict:
    train_bundle(bundle, output)
    predict_bundle(bundle, output)
    return evaluate_bundle(bundle, output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--stage", choices=("all","train","predict","evaluate"), default="all")
    args=parser.parse_args()
    bundle=json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    result={"all":run_bundle,"train":train_bundle,"predict":predict_bundle,
            "evaluate":evaluate_bundle}[args.stage](bundle,Path(args.output))
    print(json.dumps({"status":"PREOPEN_PRIVATE_STAGE_COMPLETE","stage":args.stage,
        "mode":bundle["plan"]["mode"],"orders":0,"productionReady":False},sort_keys=True))


if __name__=="__main__":main()
