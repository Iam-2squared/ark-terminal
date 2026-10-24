"""Runnable synthetic-only study. External datasets and model bytes are not inputs."""
from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Any
from types import SimpleNamespace
import multiprocessing as mp
import traceback
import hashlib
import sys
import platform
import importlib.metadata
import time
import numpy as np
from .artifact_io import exclusive_json,write_model,load_model,TrustedModelReceipt
from .exact_math import V2Error
from .resources import measure_stage
from .contracts import code_hash,configuration_hash,digest,registry,FLAGS,Candle
from .model import synthetic_factory,synthetic_forecast_factory,fit_synthetic_bundle,MODEL_PARAMS
from .experiment_ledger import ExperimentLedger
from .selection import joint,make_watchlist,validate_watchlist
from .evaluation import summarize,probability_diagnostics,bootstrap_days
from .labels import label


def _dispatch(queue: Any, target: Any, args: tuple) -> None:
    try:
        queue.put((True,target(*args)))
    except BaseException:
        queue.put((False,traceback.format_exc()))


def _isolated(target: Any, *args: Any) -> Any:
    context=mp.get_context("spawn")
    queue=context.Queue()
    process=context.Process(target=_dispatch,args=(queue,target,args))
    process.start()
    try:
        ok,value=queue.get(timeout=45)
        process.join(timeout=5)
        if process.is_alive() or not ok or process.exitcode!=0:
            raise V2Error("SYNTHETIC_STAGE_FAILED_NO_RETRY:"+str(value))
        return value
    finally:
        if process.is_alive():
            process.terminate();process.join(timeout=5)
        queue.close()


def _train(output: Path, binding: dict) -> TrustedModelReceipt:
    # No evaluation descriptor is received by this process.
    fit,cal,cert=synthetic_factory()
    ledger=ExperimentLedger(output.parent/(output.name+".ledger.jsonl"),mode="SYNTHETIC")
    model=fit_synthetic_bundle(fit,cal,cert,ledger,binding)
    trusted=write_model(output/"model.joblib",model,producer="THIS_PROCESS_SYNTHETIC_FACTORY")
    ledger.append("MODEL_SEALED","SYNTHETIC_V2_ENGINEERING",binding)
    exclusive_json(output/"model-contract.json",model.receipt)
    return trusted


def _forecast(output: Path, trusted: TrustedModelReceipt, binding: dict) -> dict:
    # The producer's pin comes from the independent parent, not the model path.
    ledger=ExperimentLedger(output.parent/(output.name+".ledger.jsonl"),mode="SYNTHETIC")
    model=load_model(output/"model.joblib",trusted=trusted,independently_pinned_receipts=frozenset({trusted.pinned_receipt_hash}))
    x=synthetic_forecast_factory()
    raw_a,raw_b,a,b=model.probabilities(x,origin="ARK_V2_GENERATOR_20261014_V1")
    restored=load_model(output/"model.joblib",trusted=trusted,independently_pinned_receipts=frozenset({trusted.pinned_receipt_hash}))
    restored_probs=restored.probabilities(x,origin="ARK_V2_GENERATOR_20261014_V1")
    maxdiff=max(float(np.max(np.abs(u-v))) for u,v in zip((raw_a,raw_b,a,b),restored_probs))
    if maxdiff!=0:
        from .exact_math import V2Error
        raise V2Error("RESTORE_REPREDICTION_CHANGED_NO_REFIT")
    q,p3,p5=joint(a,b)
    sessions=["2030-03-04","2030-03-05","2030-03-06"]
    keys=[];watches=[]
    calhash=digest([model.risk_temperature.beta,model.opportunity_temperature.beta])
    hashes={"config":configuration_hash(),"input":hashlib.sha256(x.tobytes()).hexdigest(),
            "split":digest(sessions),"risk_model":trusted.receipt["model_sha256"],
            "opportunity_model":trusted.receipt["model_sha256"],"calibration":calhash}
    for j,d in enumerate(sessions):
        candidates=[]
        for i in range(j*50,(j+1)*50):
            symbol=f"{i%50:04d}"
            keys.append((d,symbol,"PRIME"))
            candidates.append({"canonical_symbol":symbol,"rss_symbol":symbol+".T","market":"PRIME",
                               "q":q[i].tolist(),"p3":float(p3[i]),"p5":float(p5[i]),"g1":"PASS","g2":"PASS",
                               "first_reason":None,"all_reason_codes":[],"source_times":{"available_at":d+"T08:49:00+09:00","kind":"SYNTHETIC"},
                               "missing_map":{},"feature_hash":hashlib.sha256(x[i].tobytes()).hexdigest()})
        prob=sum(r["q"][0]>=.5 and r["p3"]<=.05 and r["p5"]<=.01 for r in candidates)
        counts={k:50 for k in ("master","price","g0","g1","g2")};counts["prob"]=prob
        w=make_watchlist(date.fromisoformat(d),candidates,counts,hashes)
        exclusive_json(output/(d+".watchlist.json"),w)
        watches.append(w)
    ledger.append("WATCHLISTS_SEALED","SYNTHETIC_V2_ENGINEERING",binding)
    return {"watches":watches,"sessions":sessions,"keys":keys,"probs":(raw_a,raw_b,a,b),
            "maxdiff":maxdiff,"betas":[model.risk_temperature.beta,model.opportunity_temperature.beta],
            "prediction_digest":hashlib.sha256(b"".join(p.tobytes() for p in (raw_a,raw_b,a,b))).hexdigest()}


def _forecast_measured(output: Path, trusted: TrustedModelReceipt, binding: dict) -> dict:
    stages: dict[str,Any]={}
    with measure_stage(stages,"restore_predict_and_watchlist"):
        result=_forecast(output,trusted,binding)
    result["resources"]=stages
    return result


def _evaluate(output: Path, result: dict, binding: dict) -> None:
    watches=result["watches"];sessions=result["sessions"];keys=result["keys"]
    raw_a,raw_b,a,b=result["probs"]
    ledger=ExperimentLedger(output.parent/(output.name+".ledger.jsonl"),mode="SYNTHETIC")
    ledger.append("LABEL_OPENED","SYNTHETIC_V2_ENGINEERING",binding)
    # The evaluation-only factory runs AFTER every forecast is sealed.
    rng=np.random.default_rng(20261016)
    labels={};risks=[];opps=[]
    for key in keys:
        up=int(rng.integers(0,8));adverse=int(rng.integers(0,7))
        if rng.random()<.01:
            row=Candle.from_values(date.fromisoformat(key[0]),None,None,None,None,status="NO_TRADE")
        else:
            row=Candle.from_values(date.fromisoformat(key[0]),100,100+up,100-adverse,100)
        lab=label(row);labels[key]=lab
        risks.append(lab.r if lab.r is not None else -1);opps.append(lab.b if lab.b is not None else -1)
    selected: list[tuple[str,str,str]]=[]
    for w in watches:
        validate_watchlist(w)
        selected.extend((w["session"],r["canonical_symbol"],r["market"]) for r in w["items"])
    evaluation=summarize(sessions,selected,labels)
    diagnostics={"raw":probability_diagnostics(raw_a,raw_b,np.asarray(risks),np.asarray(opps),[k[0] for k in keys]),
                 "calibrated":probability_diagnostics(a,b,np.asarray(risks),np.asarray(opps),[k[0] for k in keys])}
    exclusive_json(output/"evaluation.json",evaluation)
    exclusive_json(output/"probability-diagnostics.json",diagnostics)


def _evaluate_measured(output: Path, result: dict, binding: dict) -> dict:
    stages: dict[str,Any]={}
    with measure_stage(stages,"evaluation"):
        _evaluate(output,result,binding)
    return stages


def run_synthetic(output: Path) -> dict:
    started=time.monotonic()
    for parent in (output,*output.parents):
        if (parent/".git").exists():
            raise V2Error("MODEL_OUTPUT_INSIDE_GIT_CHECKOUT")
    _,_,cert=synthetic_factory()
    binding={"code":code_hash(),"schema":digest(registry()),"config":configuration_hash(),
             "input":digest([cert.fit_hash,cert.cal_hash]),"approval":"SYNTHETIC_FACTORY_ONLY"}
    ledger=ExperimentLedger(output.parent/(output.name+".ledger.jsonl"),mode="SYNTHETIC")
    ledger.reserve(output,"SYNTHETIC_V2_ENGINEERING",binding)
    trusted=_isolated(_train,output,binding)
    forecast_result=_isolated(_forecast_measured,output,trusted,binding)
    evaluation_resources=_isolated(_evaluate_measured,output,forecast_result,binding)
    watches=forecast_result["watches"];maxdiff=forecast_result["maxdiff"]
    rt,ot=forecast_result["betas"]
    model=SimpleNamespace(receipt=trusted.receipt["model_contract"],
                          risk_temperature=SimpleNamespace(beta=rt,objective_calls=trusted.receipt["model_contract"]["risk_optimizer_objective_calls"]),
                          opportunity_temperature=SimpleNamespace(beta=ot,objective_calls=trusted.receipt["model_contract"]["opportunity_optimizer_objective_calls"]))
    events=ledger.rows()
    counts={"base_fits":sum(r["event"].endswith("FIT_STARTED") for r in events),
            "calibration_optimizations":sum(r["event"].endswith("CAL_STARTED") for r in events)}
    versions={k:importlib.metadata.version(k) for k in ("numpy","scipy","scikit-learn","joblib","threadpoolctl")}
    receipt={"schema":"ARK_V2_SYNTHETIC_ENGINEERING_RECEIPT_V1","status":"SYNTHETIC_E2E_PASS",
             "python":platform.python_version(),"versions":versions,"code_hash":code_hash(),
             "schema_hash":digest(registry()),"config_hash":configuration_hash(),"synthetic_budget_used":counts,
             "market_candidates":0,"market_estimator_fits":0,"market_calibration_optimizations":0,
             "private_market_numeric_reads":0,"parameters_adopted":False,"tree_count":model.receipt["tree_count"],
             "gate_pipeline_canary":model.receipt["gate_pipeline_canary"],
             "risk_beta":model.risk_temperature.beta,"opportunity_beta":model.opportunity_temperature.beta,
             "risk_objective_calls":model.risk_temperature.objective_calls,"opportunity_objective_calls":model.opportunity_temperature.objective_calls,
             "forecast_sessions":len(watches),"restore_prediction_max_abs_diff":maxdiff,
             "watchlists_fixed_before_label_open":True,"wall_seconds":time.monotonic()-started,
             "separate_train_forecast_evaluate_processes":True,
             "prediction_digest":forecast_result["prediction_digest"],
             "resources_by_stage":{**model.receipt["resources_by_stage"],**forecast_result["resources"],**evaluation_resources},
             "ENGINEERING_PASS":True,"MARKET_MEASUREMENT_COMPLETE":False,
             "POINT_TARGETS_MET":"NOT_MEASURED_MARKET","STATISTICAL_SUPPORT_ESTABLISHED":False,
             "PREDICTIVE_QUALITY":"NOT_MEASURED","LIVE_READINESS":"NOT_CERTIFIED",**{f:False for f in FLAGS}}
    try:
        import resource
        receipt["process_peak_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except ImportError:
        receipt["process_peak_rss_kib"]=None
    exclusive_json(output/"receipt.json",receipt)
    return receipt
