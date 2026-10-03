"""Finite 13-head multi-horizon Development forecast; no runtime future values.

The one-head-at-a-time runner consumes the committed protocol and zero-fit
source receipts before any estimator call. Fits are counted before each call;
errors leave a manifest. This module never authorizes an order.
"""
from __future__ import annotations

import argparse
import collections
import gc
import hashlib
import json
import os
import platform
from pathlib import Path

import numpy as np

from scripts import phase57_mh_data_r54 as data

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/phase57-exit-mh-r54"
PROTOCOL = EVIDENCE / "CYCLE2_PRECOMMIT.json"
PROTOCOL_SHA = EVIDENCE / "CYCLE2_PRECOMMIT.sha256"
HEADS = {"A": (("mean", None), ("q10", .1), ("q50", .5), ("q90", .9)),
         "D": (("mean", None), ("q10", .1), ("q90", .9)),
         "HIGH": (("q10", .1), ("q50", .5), ("q90", .9)),
         "LOW": (("q10", .1), ("q50", .5), ("q90", .9))}
MODEL = dict(learning_rate=.05, max_iter=150, max_leaf_nodes=15,
             min_samples_leaf=100, l2_regularization=1., max_bins=63,
             early_stopping=False, random_state=52)
FIT_CAP = 176


def verify_protocol(summary, labels_path, source):
    from scripts import phase57_exit_continuation_r52 as r52
    from scripts import phase57_development_integrated_v0 as v0
    raw = PROTOCOL.read_bytes()
    p = json.loads(raw)
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA.read_text().strip():
        raise ValueError("FROZEN_PROTOCOL_HASH")
    if (p["cycleId"] != "CYCLE2_CORRECTED_D_TEACHER"
        or p["readiness"]["runId"] != 36361518409
        or p["inputHashes"]["labels"] !=
           "a017a10b5b0b6dc0a023ba070a60b0e991d3d98d62a800d36fe743b85c2c759b"
        or p["inputHashes"]["readinessJson"] != data.sha(summary["summaryPath"] / "readiness.json")
        or summary["filesSha256"]["training-labels.npz"] != p["inputHashes"]["labels"]):
        raise ValueError("CORRECTED_CYCLE_IDENTITY")
    if (p["status"] != "FROZEN_BEFORE_NEW_FORECAST_PERFORMANCE"
        or p["fixed"]["selector"] != "FROZEN"
        or p["model"]["hyperparameters"] != MODEL
        or p["budget"]["maxRealEstimatorFits"] != FIT_CAP
        or p["safety"] != v0.SAFETY or any(v0.SAFETY.values())):
        raise ValueError("FROZEN_PROTOCOL_IDENTITY")
    if summary["status"] != "CONDITIONAL_MEASUREMENT" or summary["blocking"]:
        raise ValueError("SOURCE_READINESS_NOT_PASS")
    if p["inputHashes"]["labels"] != data.sha(labels_path):
        raise ValueError("TEACHER_LABEL_HASH_DRIFT")
    for file, digest in p["inputHashes"]["summaryFiles"].items():
        if data.sha(summary["summaryPath"] / file) != digest:
            raise ValueError("READINESS_FILE_CHANGED:"+file)
    if data.sha(EVIDENCE/"FEATURE_SCHEMA_LOCKED.json") != p["inputHashes"]["lockedFeatureSchema"]:
        raise ValueError("FROZEN_FEATURE_AUDIT_CHANGED")
    schema = json.loads((EVIDENCE / "FEATURE_SCHEMA_LOCKED.json").read_text())
    if p["inputHashes"]["consumedFeatureLayouts"] != {
        variant: hashlib.sha256(data.canonical(feature_layout(schema, variant))).hexdigest()
        for variant in ("FULL", "S", "P")
    }:
        raise ValueError("CONSUMED_FEATURE_LAYOUT_CHANGED")
    if p["fixed"]["r52ProtocolSha256"] != data.sha(r52.PRECOMMIT):
        raise ValueError("OLD_FOLD_SOURCE_CHANGED")
    r52.protocol()
    receipt, arrays, ids, groups = r52.load_checkpoints(source)
    if p["fixed"]["r45FeatureSha256"] != data.sha(source / "data/decision-features.npz"):
        raise ValueError("FEATURE_SOURCE_CHANGED")
    return p, receipt, arrays, ids, groups


def feature_layout(schema, variant):
    if variant not in ("FULL", "S", "P"):
        raise ValueError("UNKNOWN_ABLATION")
    banned = set(schema["ablationSRemove"] if variant == "S" else
                 schema["ablationPRemove"] if variant == "P" else ())
    columns = [n for n in schema["numeric"] if n not in banned]
    if variant != "P":
        columns.extend(n for n in schema["pattern187"] if n not in banned)
    for name, info in schema["categorical"].items():
        if name not in banned:
            columns.extend(name + "=" + value for value in info["values"])
    return columns + ["HORIZON/activeDelay", "HORIZON/eodFlag"]


def feature_columns(receipt, schema, arrays, idx, horizons, variant):
    """One-hot only the frozen declared enum. No score-era vocab learning."""
    from scripts import phase57_exit_continuation_r52 as r52
    if variant not in ("FULL", "S", "P"):
        raise ValueError("UNKNOWN_ABLATION")
    banned = set(schema["ablationSRemove"] if variant == "S" else
                 schema["ablationPRemove"] if variant == "P" else ())
    num_names = [n for n in schema["numeric"] if n not in banned]
    num_cols = [receipt["numericColumns"].index(n) for n in num_names]
    blocks = [np.asarray(arrays["numeric"][np.ix_(idx, num_cols)], np.float32)]
    if variant != "P":
        pat_cols = [j for j, n in enumerate(schema["pattern187"]) if n not in banned]
        if pat_cols:
            blocks.append(np.asarray(arrays["pattern"][np.ix_(idx, pat_cols)],np.float32))
    for name, info in schema["categorical"].items():
        if name in banned:
            continue
        raw = arrays["categorical"][idx, receipt["categoricalColumns"].index(name)]
        source_code = info["sourceCodes"]
        # If a frozen R45 source code is unknown to declared vocabulary, encode UNKNOWN.
        valid = np.asarray(list(source_code.values()), np.int16)
        raw = np.where(np.isin(raw, valid), raw, source_code.get("UNKNOWN", -1))
        block = np.empty((len(idx), len(info["values"])), dtype=np.float32)
        for j, word in enumerate(info["values"]):
            code = source_code.get(word)
            block[:,j] = 0 if code is None else raw == code
        blocks.append(block)
    active = np.asarray([data.scheduled_delay(ids_day, int(now), int(t))
         if t is not None else 0 for ids_day, now, t in horizons], dtype=np.float32)
    eod = np.asarray([h[2] == 925 for h in horizons], dtype=np.float32)
    # Actual active delay is the only ordinal horizon distance, EOD has an explicit flag.
    blocks.append(np.column_stack((active, eod)).astype(np.float32))
    x = np.concatenate(blocks,axis=1)
    del blocks
    if (len(x) != len(idx) or x.shape[1] != len(feature_layout(schema, variant))
        or not np.all(np.isfinite(x[:,-2:]))):
        raise ValueError("FEATURE_HORIZON_GEOMETRY")
    return x


def design(rows, horizon_indices, ids, arrays, receipt, schema, variant):
    from scripts import phase57_exit_continuation_r52 as r52
    clock = [(ids[i]["session"],ids[i]["now"],data.planned_targets(ids[i]["session"],ids[i]["now"]).get(data.HORIZONS[j]))
             for i,j in zip(rows,horizon_indices)]
    if any(t is None for _,_,t in clock):
        raise ValueError("UNSUPPORTED_CALENDAR_TARGET")
    return feature_columns(receipt,schema,arrays,rows,clock,variant)


def eligible_horizons(support, fold, arm, family):
    match=[x for x in support if x["fold"]==fold and x["arm"]==arm
           and x["family"]==family and x["partition"]=="fit"]
    if len(match)!=1 or match[0]["matureRows"] < data.MIN_TRAIN_ROWS:
        raise ValueError("FAMILY_TRAIN_SUPPORT")
    return [h for h in data.HORIZONS if family!="D" or h!=0
            if (lambda z:z["matureLabels"]>=data.MIN_HORIZON_ROWS and
                     z["entryIds"]>=data.MIN_HORIZON_ENTRY and
                     z["sessions"]>=data.MIN_HORIZON_SESSIONS)(match[0]["horizons"][str(h)])]


def training_rows(labels, family, days, ids, allowed):
    dates=np.asarray([v["session"] for v in ids]);group=np.isin(dates, days)
    by_h=[(np.flatnonzero(group & np.isfinite(labels[family][:, data.HORIZONS.index(h)])),h)
          for h in allowed]
    rows=np.concatenate([r for r,h in by_h]);hs=np.concatenate([np.full(len(r), data.HORIZONS.index(h),np.int8)
                                                 for r,h in by_h])
    if len(rows)<data.MIN_TRAIN_ROWS:
        raise ValueError("TRAIN_ROWS_UNDER_FAMILY_FLOOR")
    return rows,hs


def prediction_rows(days, ids, allowed):
    dayset=set(days);col=[];hs=[]
    for i,r in enumerate(ids):
        if r["session"] not in dayset or r["now"]==925:continue
        plan=data.planned_targets(r["session"],r["now"])
        for h in allowed:
            if h in plan:
                col.append(i);hs.append(data.HORIZONS.index(h))
    return np.asarray(col,np.int32),np.asarray(hs,np.int8)


def entry_weights(rows, ids):
    # For each family, each Entry carries the same total weight across its
    # checkpoints and unique valid horizons. Missing labels remain missing.
    per=collections.Counter(ids[i]["entryId"] for i in rows)
    w=np.asarray([1/per[ids[i]["entryId"]] for i in rows],np.float64)
    return w * (len(w)/w.sum())


def new_model(head, quantile):
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(loss="squared_error" if head=="mean" else "quantile",
             **({} if quantile is None else {"quantile":quantile}), **MODEL)


def main(source, summary_path, labels_path, out):
    from scripts import phase57_exit_continuation_r52 as r52
    from scripts import phase57_development_integrated_v0 as v0
    import joblib
    summary=json.loads((summary_path/"readiness.json").read_text());summary["summaryPath"]=summary_path
    p,receipt,arrays,ids,groups=verify_protocol(summary,labels_path,source)
    if out.exists():raise ValueError("APPEND_ONLY_RESULT")
    out.mkdir(parents=True)
    manifests=[]; manifest_path=out/"fit-manifest.json"
    def manifest():
        manifest_path.write_bytes(data.canonical({"fits":manifests,"consumedCalls":len(manifests),
             "protocolSha256":data.sha(PROTOCOL),"safety":v0.SAFETY}))
    manifest()
    schema=json.loads((EVIDENCE/"FEATURE_SCHEMA_LOCKED.json").read_text())
    original=json.loads((summary_path/"feature-schema.json").read_text())
    # The only zero-fit correction to the first source census is the exact
    # predeclared S-ablation removal list; it changes no target or main input.
    if {k:v for k,v in schema.items() if k!="ablationSRemove"} != \
       {k:v for k,v in original.items() if k!="ablationSRemove"}:
        raise ValueError("FEATURE_SCHEMA_OUTSIDE_S_ABLATION_CHANGE")
    folds=json.loads((summary_path/"fold-manifest.json").read_text())
    support=json.loads((summary_path/"train-support.json").read_text())
    with np.load(labels_path,allow_pickle=False) as z: labels={k:z[k] for k in data.FAMILIES}
    for family in data.FAMILIES:
        if labels[family].shape != (len(ids),len(data.HORIZONS)):
            raise ValueError("TEACHER_ROW_IDENTITY")
    outputs={k:np.full((len(ids),len(data.HORIZONS)),np.nan,np.float32)
             for k in [f"{variant}__{fam}__{head}" for variant in ("FULL","S","P")
                       for fam in data.FAMILIES if variant=="FULL" or fam=="D"
                       for head,_ in HEADS[fam]]}
    calibration={k:np.full((len(ids),len(data.HORIZONS)),np.nan,np.float32)
                 for k in outputs if k.startswith("FULL__")}
    model_dir=out/"models";model_dir.mkdir()
    for fold in folds:
        for arm in v0.ARMS:
            for variant in ("FULL","S","P"):
                for family in (data.FAMILIES if variant=="FULL" else ("D",)):
                    eligible=eligible_horizons(support,fold["fold"],arm,family)
                    if family=="D" and not set((1,5)) <= set(eligible):
                        raise ValueError("PRECOMMITTED_D1_D5_SUPPORT")
                    arm_rows=np.asarray([v["arm"]==arm for v in ids],bool)
                    tr, th=training_rows(labels,family,fold["fit"],ids,eligible)
                    take=arm_rows[tr];tr,th=tr[take],th[take]
                    te,eh=prediction_rows(fold["score"],ids,eligible)
                    take=arm_rows[te];te,eh=te[take],eh[take]
                    ca,ch=prediction_rows(fold["calibration"],ids,eligible)
                    take=arm_rows[ca];ca,ch=ca[take],ch[take]
                    if not len(tr) or not len(te):raise ValueError("TRAIN_OR_SCORE_EMPTY")
                    X=design(tr,th,ids,arrays,receipt,schema,variant)
                    weights=entry_weights(tr,ids)
                    y=labels[family][tr,th]
                    if not np.all(np.isfinite(y)):raise ValueError("NONFINITE_TEACHER")
                    for head,q in HEADS[family]:
                        key=f"{variant}__{family}__{head}"
                        if len(manifests)>=FIT_CAP:raise ValueError("FIT_BUDGET_EXCEEDED")
                        model=new_model(head,q)
                        rec={"ordinal":len(manifests)+1,"status":"CALL_STARTED","fold":fold["fold"],
                             "arm":arm,"variant":variant,"family":family,"head":head,
                             "fitRows":len(tr),"scoreRows":len(te),"featureWidth":X.shape[1],
                             "fitMaxSession":max(fold["fit"]),"scoreMinSession":min(fold["score"])}
                        manifests.append(rec);manifest()
                        model.fit(X,y,sample_weight=weights)
                        filename=f"F{fold['fold']}__{'IM' if arm==v0.IM else 'R1'}__{key}.joblib"
                        joblib.dump(model,model_dir/filename,compress=3)
                        rec.update(status="FIT_COMPLETE",modelFile=filename,
                                   modelSha256=data.sha(model_dir/filename))
                        # Evaluate only from saved model; no teacher mask joins to runtime.
                        for left in range(0,len(te),20000):
                            ix=te[left:left+20000];hi=eh[left:left+20000]
                            Z=design(ix,hi,ids,arrays,receipt,schema,variant)
                            vals=model.predict(Z).astype(np.float32)
                            if not np.all(np.isfinite(vals)) or np.isfinite(outputs[key][ix,hi]).any():
                                raise ValueError("OOF_FINITE_UNIQUE")
                            outputs[key][ix,hi]=vals
                        if variant=="FULL":
                            for left in range(0,len(ca),20000):
                                ix=ca[left:left+20000];hi=ch[left:left+20000]
                                Z=design(ix,hi,ids,arrays,receipt,schema,variant)
                                vals=model.predict(Z).astype(np.float32)
                                if not np.all(np.isfinite(vals)) or np.isfinite(calibration[key][ix,hi]).any():
                                    raise ValueError("CALIBRATION_FINITE_UNIQUE")
                                calibration[key][ix,hi]=vals
                        rec["scoreCompleted"]=True;manifest()
                        print(data.canonical({"phase":"FIT_COMPLETE","ordinal":len(manifests),
                          "candidatePerformanceViewed":False}).decode(),flush=True)
                    del X,y,tr,th,te,eh,ca,ch,weights
                    gc.collect()
    if len(manifests)!=152 or sum(x["status"]!="FIT_COMPLETE" for x in manifests):
        raise ValueError("MAIN_AND_ABLATION_FIT_COUNT")
    # Required independent 24 D-head refits use exactly the original train rows.
    # Their prediction equality, not merely a serialized model SHA, is audited.
    refit_deltas=[]
    refit_outputs={"REFIT__D__"+head:np.full((len(ids),len(data.HORIZONS)),np.nan,np.float32)
                   for head,_ in HEADS["D"]}
    for fold in folds:
        for arm in v0.ARMS:
            eligible=eligible_horizons(support,fold["fold"],arm,"D")
            tr,th=training_rows(labels,"D",fold["fit"],ids,eligible)
            trmask=np.asarray([ids[i]["arm"]==arm for i in tr]);tr,th=tr[trmask],th[trmask]
            te,eh=prediction_rows(fold["score"],ids,eligible)
            temask=np.asarray([ids[i]["arm"]==arm for i in te]);te,eh=te[temask],eh[temask]
            X=design(tr,th,ids,arrays,receipt,schema,"FULL")
            y=labels["D"][tr,th];weights=entry_weights(tr,ids)
            for head,q in HEADS["D"]:
                if len(manifests)>=FIT_CAP:raise ValueError("REFIT_BUDGET_EXCEEDED")
                m=new_model(head,q)
                rec={"ordinal":len(manifests)+1,"status":"CALL_STARTED","family":"D",
                     "variant":"INDEPENDENT_REFIT","arm":arm,"fold":fold["fold"],"head":head}
                manifests.append(rec);manifest()
                m.fit(X,y,sample_weight=weights)
                reference=outputs[f"FULL__D__{head}"]
                deltas=[]
                for left in range(0,len(te),20000):
                    ix=te[left:left+20000];hi=eh[left:left+20000]
                    Z=design(ix,hi,ids,arrays,receipt,schema,"FULL")
                    z=m.predict(Z).astype(np.float32)
                    deltas.append(float(np.max(np.abs(z-reference[ix,hi]))))
                    refit_outputs["REFIT__D__"+head][ix,hi]=z
                rec.update(status="FIT_COMPLETE",maxPredictionDelta=max(deltas,default=0.))
                refit_deltas.append(rec["maxPredictionDelta"]);manifest()
                print(data.canonical({"phase":"REFIT_COMPLETE","ordinal":len(manifests),
                     "candidatePerformanceViewed":False}).decode(),flush=True)
            del X,y,tr,th,te,eh,weights
            gc.collect()
    if len(manifests)!=FIT_CAP:raise ValueError("FIT_COUNT_176")
    coverage={}
    for variant in ("FULL","S","P"):
        for family in (data.FAMILIES if variant=="FULL" else ("D",)):
            expected=np.zeros((len(ids),len(data.HORIZONS)),bool)
            for fold in folds:
                for arm in v0.ARMS:
                    eligible=eligible_horizons(support,fold["fold"],arm,family)
                    ix,hi=prediction_rows(fold["score"],ids,eligible)
                    mask=np.asarray([ids[i]["arm"]==arm for i in ix]);ix,hi=ix[mask],hi[mask]
                    if np.any(expected[ix,hi]):raise ValueError("DUPLICATE_OOF_FOLD_MEMBERSHIP")
                    expected[ix,hi]=True
            for head,_ in HEADS[family]:
                key=f"{variant}__{family}__{head}"
                actual=np.isfinite(outputs[key])
                if not np.array_equal(expected,actual):
                    raise ValueError("OOF_MISSING_OR_UNEXPECTED_ROW:"+key)
                coverage[key]=int(actual.sum())
    for head,_ in HEADS["D"]:
        if not np.array_equal(np.isfinite(refit_outputs["REFIT__D__"+head]),
                              np.isfinite(outputs["FULL__D__"+head])):
            raise ValueError("REFIT_OOF_COVERAGE_DRIFT")
    with (out/"oof-forecasts.npz").open("xb") as stream:np.savez_compressed(stream,**outputs)
    with (out/"calibration-forecasts.npz").open("xb") as stream:np.savez_compressed(stream,**calibration)
    with (out/"oof-refit-d.npz").open("xb") as stream:np.savez_compressed(stream,**refit_outputs)
    (out/"oof-audit.json").write_bytes(data.canonical({"schema":"phase57-r54-oof-audit-v1",
       "sourceIdentitySha256":r52.IDENTITY_SHA,"expectedFits":FIT_CAP,"actualFits":len(manifests),
       "modelsSha256":{x["modelFile"]:x["modelSha256"] for x in manifests if "modelFile" in x},
       "independentDRefitMaxPredictionDelta":max(refit_deltas,default=None),
       "predictionsSha256":data.sha(out/"oof-forecasts.npz"),
       "coverageByOutput":coverage,
       "calibrationPredictionsSha256":data.sha(out/"calibration-forecasts.npz"),
       "independentPredictionsSha256":data.sha(out/"oof-refit-d.npz"),
       "outputRowN":len(ids),"performanceReadBeforeAudit":False,
       "safety":v0.SAFETY}))
    print(data.canonical({"phase":"OOF_SAVED","fits":len(manifests),
        "predictionSha256":data.sha(out/"oof-forecasts.npz"),
        "candidatePerformanceViewed":False}).decode(),flush=True)


if __name__ == "__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--summary",type=Path,required=True)
    ap.add_argument("--labels",type=Path,required=True);ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args();main(args.source,args.summary,args.labels,args.out)
