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

from preopen_selector import (CONTRACT, POS_BINS, PreopenError, build_preopen_features,
    compare_preopen_watchlists, digest, evaluate_open_high, make_watchlist,
    row_key, summarize_open_high)
from preopen_model import validate_plan, train_preopen_model, save_private_model

ROLES = tuple(f"{s}_{t}" for s in ("fit","calibration","report") for t in ("snapshots","labels"))


def load_verified_input(entry: dict, private_root: Path) -> list[dict]:
    path = Path(entry["path"])
    if not path.is_absolute():
        path = private_root / path
    path = path.resolve()
    if not path.is_relative_to(private_root.resolve()):
        raise PreopenError("INPUT_OUTSIDE_EXPLICIT_PRIVATE_ROOT")
    if not path.is_file():
        raise PreopenError("PRIVATE_INPUT_NOT_MOUNTED:"+path.name)
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024*1024), b""):
            h.update(part); size += len(part)
    if h.hexdigest() != entry.get("sha256") or (entry.get("bytes") is not None and size != entry["bytes"]):
        raise PreopenError("PRIVATE_INPUT_HASH_OR_SIZE_MISMATCH")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path,"rt",encoding="utf-8") as stream:
        result=[]
        for line in stream:
            if line.strip():
                value=json.loads(line)
                if not isinstance(value,dict):
                    raise PreopenError("NONOBJECT_INPUT_RECORD")
                result.append(value)
    return result


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


def run_bundle(bundle: dict, output: Path) -> dict:
    if bundle.get("contract") != CONTRACT or set(bundle.get("inputs",{})) != set(ROLES):
        raise PreopenError("INCOMPLETE_PREOPEN_BUNDLE")
    if output.exists():
        raise PreopenError("REFUSE_OVERWRITE_RESULT")
    private_root=Path(bundle["privateRoot"]).resolve()
    loaded={role:load_verified_input(bundle["inputs"][role],private_root) for role in ROLES}
    rows={s:[build_preopen_features(r) for r in loaded[s+"_snapshots"]]
          for s in ("fit","calibration","report")}
    plan=bundle["plan"]
    validate_plan(plan,rows)
    raw={s:index_labels(loaded[s+"_labels"],set(plan["splits"][s])) for s in rows}
    fy=evaluate_population(rows["fit"],raw["fit"])
    cy=evaluate_population(rows["calibration"],raw["calibration"])
    model=train_preopen_model(rows["fit"],fy,rows["calibration"],cy,plan)
    # First Report outcome evaluation occurs after fit/calibration is complete.
    groups=defaultdict(list)
    for r in rows["report"]:groups[r["session"]].append(r)
    candidate_rows,baseline_rows,daily,watchlists=[],[],[],[]
    random_expected={k:0.0 for k in POS_BINS}
    random_unknown=0.0
    for session,rs in sorted(groups.items()):
        candidate=model.watchlist(rs)
        baseline=make_watchlist(rs,{row_key(r):r["priorTurnover"] for r in rs})
        watchlists.append(candidate)
        daily.append(compare_preopen_watchlists(baseline,candidate,raw["report"]))
        candidate_rows.extend(evaluate_open_high(candidate,raw["report"]))
        baseline_rows.extend(evaluate_open_high(baseline,raw["report"]))
        population=list(evaluate_population(rs,raw["report"]).values())
        scale=candidate["selectedN"]/len(rs)
        for lab in population:
            if lab["status"]=="KNOWN":random_expected[lab["bucket"]]+=scale
            else:random_unknown+=scale
    summary={"schema":"ARK_PREOPEN_FULL_BATCH_REPORT_V1","contract":CONTRACT,
             "bundleHash":digest(bundle),"mode":plan["mode"],
             "training":model.receipt,"sessions":len(daily),
             "candidate":summarize_open_high(candidate_rows),
             "previousSessionTurnoverTopK":summarize_open_high(baseline_rows),
             "exactSameUniverseRandom":{"expectedBucketN":random_expected,"expectedUnknownN":random_unknown},
             "pairedUncertainty":bootstrap_day_deltas(daily),
             "legacyFrozenComparison":"NOT_EXECUTED_NATIVE_INTRADAY_EVENTS_REQUIRED_LATER_INFO_NOT_FAIR_PREOPEN",
             "liveRuntimeCertified":False,"productionReady":False,
             "orders":0,"providerRequests":0,"portfolioReplays":0}
    output.mkdir(parents=True,exist_ok=False)
    save_private_model(model,output/"private_model")
    (output/"REPORT_AGGREGATE.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # These names and per-session predictions remain in PRIVATE output only.
    (output/"PRIVATE_WATCHLISTS.json").write_text(json.dumps(watchlists,ensure_ascii=False)+"\n",encoding="utf-8")
    (output/"PRIVATE_DAY_COMPARISON.json").write_text(json.dumps(daily,ensure_ascii=False)+"\n",encoding="utf-8")
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    bundle=json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    result=run_bundle(bundle,Path(args.output))
    print(json.dumps({"status":"PREOPEN_BATCH_WRITTEN_PRIVATE",
        "mode":result["mode"],"sessions":result["sessions"],
        "selectedN":result["candidate"]["selectedN"],
        "knownN":result["candidate"]["knownN"],
        "unknownN":result["candidate"]["unknownN"],
        "orders":0,"productionReady":False},sort_keys=True))


if __name__=="__main__":main()
