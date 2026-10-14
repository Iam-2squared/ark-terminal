"""Admitted native census/fit/calibration/forecast/evaluation/restore stages.

No fixed synthetic matrix is accepted here. All features derive from admitted
RAW session objects. Authority precedes IO; a host retains artifact trust pins
independently of on-disk receipts. START events consume budgets even on failure.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date,datetime,timezone
from pathlib import Path
from typing import Any
import hashlib
import io
import json
import os
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits
from .authority import Authority
from .artifact_io import exclusive_bytes,exclusive_json,safe_path
from .contracts import FLAGS,code_hash,configuration_hash,digest,registry
from .exact_math import V2Error
from .native import NativeReader,NativeRows
from .model import MODEL_PARAMS,TrainingData,partition,teacher_support,oracle_supply
from .weights import used_columns,check_cal_support
from .calibration import Temperature,fit_temperature,temperature,probability_matrix
from .selection import joint,qualified,rank_candidates,watchlist_hash,validate_watchlist
from .calendar_phase import cutoff
from .evaluation import summarize,capture,exclusion_audit,bootstrap_days,probability_diagnostics
from .resources import memory_preflight

STAGES={"census","train","calibrate","predict","evaluate","restore-verify"}


class Store:
    """Pins live in the trusted host, never obtained by trusting a receipt file."""
    def __init__(self,authority: Authority):self.authority=authority

    def put(self,name: str,value: Any, *, model: bool=False) -> dict[str,Any]:
        if model:
            import joblib
            buffer=io.BytesIO();joblib.dump(value,buffer,compress=3);data=buffer.getvalue()
        else:data=(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n").encode()
        pin={"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),"self_produced":True,
             "code":code_hash(),"model":model,"test_only":self.authority.test_only}
        path=safe_path(self.authority.output,name)
        exclusive_bytes(path,data)
        # The host must persist this pin via its independent channel before a
        # later process is allowed to read. The disk sidecar cannot grant trust.
        exclusive_json(path.with_suffix(path.suffix+".receipt.json"),pin)
        self.authority.artifact_pins[name]=pin
        return pin

    def get(self,name: str, *, model: bool=False) -> Any:
        pin=self.authority.artifact_pins.get(name)
        if pin is None or pin.get("self_produced") is not True or pin["model"] is not model or pin["test_only"] is not self.authority.test_only:
            raise V2Error("INDEPENDENT_ARTIFACT_PRODUCER_PIN_REQUIRED_BEFORE_OPEN")
        if pin["code"]!=code_hash():raise V2Error("ARTIFACT_CODE_DRIFT_NO_REFIT")
        path=safe_path(self.authority.output,name)
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=pin["sha256"] or len(data)!=pin["bytes"]:
            raise V2Error("ARTIFACT_HASH_SIZE_DRIFT_NO_REFIT")
        if model:
            import joblib
            result=joblib.load(io.BytesIO(data))
            if not isinstance(result,NativeBundle):raise V2Error("ADMITTED_MODEL_SCHEMA")
            result.validate(self.authority)
            return result
        return json.loads(data)

    def event(self,name: str,pre: dict[str,Any]) -> None:
        # Exclusive publication + independent pins preserve failed STARTs.
        self.put("events/"+name+".json",{"event":name,"precommit":digest(pre),"candidate_id":"PREOPEN_V2_TC_C01",
                                            "at":datetime.now(timezone.utc).isoformat(),"test_only":self.authority.test_only})


@dataclass
class NativeBundle:
    risk: Any
    opportunity: Any
    risk_columns: tuple[int,...]
    opportunity_columns: tuple[int,...]
    receipt: dict[str,Any]
    risk_temperature: Temperature | None=None
    opportunity_temperature: Temperature | None=None

    def validate(self,authority: Authority) -> None:
        if self.receipt["hashes"]!={"code":code_hash(),"config":configuration_hash(),"schema":digest(registry())}:
            raise V2Error("MODEL_CODE_CONFIG_SCHEMA_DRIFT_NO_REFIT")
        if (self.receipt["test_only"] is not authority.test_only or self.receipt["manifest_sha256"]!=authority.manifest_pin
                or self.receipt["precommit_sha256"]!=authority.grants["C"].precommit_pin):
            raise V2Error("MODEL_AUTHORITY_OR_NATIVE_MANIFEST_MISMATCH")
        if not np.array_equal(self.risk.classes_,np.arange(3)) or not np.array_equal(self.opportunity.classes_,np.arange(6)):
            raise V2Error("MODEL_CLASS_ORDER_MISMATCH")

    def probabilities(self,x: np.ndarray,authority: Authority, *, calibrated: bool=True) -> tuple[np.ndarray,np.ndarray]:
        self.validate(authority)
        if x.dtype!=np.float64 or x.ndim!=2 or x.shape[1]!=95 or np.isinf(x).any():raise V2Error("NATIVE_PREDICTION_MATRIX")
        if len(x)==0:return np.empty((0,3)),np.empty((0,6))
        with threadpool_limits(limits=1):
            a=probability_matrix(self.risk.predict_proba(x[:,self.risk_columns]),3)
            b=probability_matrix(self.opportunity.predict_proba(x[:,self.opportunity_columns]),6)
        if calibrated:
            if self.risk_temperature is None or self.opportunity_temperature is None:raise V2Error("MODEL_NOT_CALIBRATED")
            a=temperature(a,self.risk_temperature.beta);b=temperature(b,self.opportunity_temperature.beta)
        return a,b


def support(reader: NativeReader) -> tuple[dict[str,NativeRows],dict[str,TrainingData],dict[str,Any]]:
    # Validate FIT/CAL inputs and teachers as a complete descriptor batch,
    # before opening even a history object. VAL/FINAL teachers are excluded.
    wanted=[]
    for role in ("FIT","CAL"):
        wanted.extend(reader.forecast_plan(role))
        wanted.extend(("DAILY",d,role+"_TEACHER") for d in reader.pre["split"][role])
    reader.authority.preflight_entries(reader.manifest,list(dict.fromkeys(wanted)),reader.pre)
    rows={};data={};stats={}
    for role in ("FIT","CAL"):
        rows[role]=reader.forecast(role)
        teachers=reader.teachers(role)
        data[role]=rows[role].training(teachers,reader.authority.test_only)
        stats[role]=teacher_support(data[role],synthetic=reader.authority.test_only)
        stats[role]["gate_counts"]=rows[role].counts
        stats[role]["observation_counts"]={name:int(sum(r["values"][name] is not None for r in rows[role].rows)) for name in rows[role].rows[0]["values"]}
        if role=="FIT":
            counts={d:(sum(bool((teachers[(r["session"],r["canonical_symbol"],r["market"])].clean_winner or (False,)*5)[2]) for r in rows[role].rows if r["session"]==d),
                       sum(bool((teachers[(r["session"],r["canonical_symbol"],r["market"])].clean_winner or (False,)*5)[4]) for r in rows[role].rows if r["session"]==d)) for d in rows[role].sessions}
            stats["oracle_upper"]=oracle_supply(rows[role].sessions,counts)
    known,r0,_,_=partition(data["FIT"]);cknown,cr0,_,_=partition(data["CAL"])
    rc,_=used_columns(data["FIT"].x[known]);oc,_=used_columns(data["FIT"].x[r0])
    check_cal_support(data["CAL"].x[cknown],rc);check_cal_support(data["CAL"].x[cr0],oc)
    stats["memory_preflight"]=memory_preflight(len(data["FIT"].x),len(data["CAL"].x))
    stats["used_columns"]={"risk":list(rc),"opportunity":list(oc)}
    return rows,data,stats


def stage_gate(stage: str,role: str,authority: Authority,pre: dict[str,Any],store: Store) -> None:
    if stage in {"census","train","calibrate"} and role!="FIT_CAL":raise V2Error("LEARNER_DESCRIPTOR_ROLE_LEAK_BEFORE_OPEN")
    if stage in {"predict","evaluate","restore-verify"} and role not in {"VALIDATION","FINAL"}:raise V2Error("EVALUATION_DESCRIPTOR_ROLE")
    if stage!="census":
        census=store.get("census.json")
        if census["status"]!="CENSUS_COMPLETE" or digest(census)!=pre["census_receipt_sha256"] or census["manifest"]!=authority.manifest_pin or census["hashes"]!=pre["hashes"]:
            raise V2Error("MODE_C_CENSUS_NOT_PASSED_OR_HASH_DRIFT")
    if stage in {"predict","evaluate","restore-verify"} and role=="FINAL":
        validation=store.get("evaluation-VALIDATION.json")
        if validation["status"]!="VALIDATION_TARGETS_MET":raise V2Error("FINAL_REMAINS_SEALED_VALIDATION_FAILED")
    if stage in {"evaluate","restore-verify"}:
        sealed=store.get("watchlists-"+role+".json")
        if sealed["sessions"]!=pre["split"][role] or len(sealed["watchlists"])!=len(sealed["sessions"]):
            raise V2Error("ALL_WATCHLISTS_MUST_BE_FIXED_BEFORE_LABEL_OPEN")
        for w in sealed["watchlists"]:validate_watchlist(w)


def dispatch(stage: str, request: dict[str,Any], *, authority: Authority | None) -> dict[str,Any]:
    if authority is None:raise V2Error("AWAITING_MARKET_APPROVAL:OWNER_CHANNEL_NOT_INSTALLED")
    if stage not in STAGES:raise V2Error("UNKNOWN_STAGE")
    pre=authority.authorize(stage,request)
    store=Store(authority);role=request["role"]
    stage_gate(stage,role,authority,pre,store)
    # The run root is tied to the trusted host, not selected by request flags.
    authority.output.mkdir(parents=True,exist_ok=True)
    lock=authority.output/"stage.lock"
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise V2Error("EXCLUSIVE_STAGE_LOCK_NO_RETRY") from None
    try:
        store.event("START-"+stage+"-"+role,pre)
        reader=NativeReader(authority,request["manifest"],pre)
        if stage=="census":
            _,_,stats=support(reader)
            result={"status":"CENSUS_COMPLETE","manifest":authority.manifest_pin,"hashes":pre["hashes"],
                    "stats":stats,"test_only":authority.test_only,"market_fits":0,"access":reader.access}
            store.put("census.json",result)
        elif stage=="train":
            # Recheck support/native hashes before reservation or estimator.fit.
            _,data,stats=support(reader)
            if stats!=store.get("census.json")["stats"]:raise V2Error("CENSUS_REPLAY_DRIFT")
            store.event("CANDIDATE_RESERVED",pre)
            fit=data["FIT"];known,r0,wf,c=partition(fit)
            rc=tuple(stats["used_columns"]["risk"]);oc=tuple(stats["used_columns"]["opportunity"])
            risk=HistGradientBoostingClassifier(**MODEL_PARAMS);opp=HistGradientBoostingClassifier(**MODEL_PARAMS)
            with threadpool_limits(limits=1):
                store.event("RISK_FIT_STARTED",pre);risk.fit(fit.x[known][:,rc],fit.risk[known],sample_weight=wf[known]);store.event("RISK_FIT_FINISHED",pre)
                store.event("OPPORTUNITY_FIT_STARTED",pre);opp.fit(fit.x[r0][:,oc],fit.opportunity[r0],sample_weight=wf[r0]);store.event("OPPORTUNITY_FIT_FINISHED",pre)
            bundle=NativeBundle(risk,opp,rc,oc,{"hashes":pre["hashes"],"manifest_sha256":authority.manifest_pin,"test_only":authority.test_only,
                                             "precommit_sha256":authority.grants["C"].precommit_pin,"fit_fingerprint":fit.fingerprint(),"weight_scale":c,"base_fit_calls":2})
            bundle.validate(authority);store.put("base-model.joblib",bundle,model=True)
            result={"status":"BASE_MODELS_FIXED","fits":2,"calibrations":0,"test_only":authority.test_only}
        elif stage=="calibrate":
            model=store.get("base-model.joblib",model=True)
            cal_rows=reader.forecast("CAL");cal=cal_rows.training(reader.teachers("CAL"),authority.test_only)
            teacher_support(cal,synthetic=authority.test_only)
            known,r0,wc,c=partition(cal)
            check_cal_support(cal.x[known],model.risk_columns);check_cal_support(cal.x[r0],model.opportunity_columns)
            a,b=model.probabilities(cal.x,authority,calibrated=False)
            store.event("RISK_CAL_STARTED",pre);model.risk_temperature=fit_temperature(a[known],cal.risk[known],wc[known]);store.event("RISK_CAL_FINISHED",pre)
            store.event("OPPORTUNITY_CAL_STARTED",pre);model.opportunity_temperature=fit_temperature(b[r0],cal.opportunity[r0],wc[r0]);store.event("OPPORTUNITY_CAL_FINISHED",pre)
            model.receipt.update({"cal_fingerprint":cal.fingerprint(),"cal_weight_scale":c,"calibration_optimizations":2,
                                  "tree_count":sum(len(g) for g in model.risk._predictors)+sum(len(g) for g in model.opportunity._predictors)})
            store.put("fixed-model.joblib",model,model=True);store.event("MODEL_SEALED",pre)
            result={"status":"MODEL_FIXED","fits":2,"calibrations":2,"test_only":authority.test_only}
        elif stage=="predict":
            model=store.get("fixed-model.joblib",model=True)
            rows=reader.forecast(role);a,b=model.probabilities(rows.matrix(),authority)
            raw_a,raw_b=model.probabilities(rows.matrix(),authority,calibrated=False)
            q,p3,p5=joint(a,b);watches=[]
            for d in rows.sessions:
                candidates=[]
                for i,r in enumerate(rows.rows):
                    if r["session"]!=d:continue
                    candidates.append({k:r[k] for k in ("canonical_symbol","rss_symbol","market","source_times","missing_map","feature_hash")}|{
                        "q":q[i].tolist(),"p3":float(p3[i]),"p5":float(p5[i]),"g1":"PASS","g2":"PASS","first_reason":None,"all_reason_codes":[]})
                counts=rows.counts[d];counts["prob"]=sum(qualified(r["q"],r["p3"],r["p5"]) for r in candidates)
                selected=rank_candidates(candidates)
                hashes={"code":code_hash(),"config":configuration_hash(),"schema":digest(registry()),"input":authority.manifest_pin,
                        "split":digest(pre["split"]),"risk_model":authority.artifact_pins["fixed-model.joblib"]["sha256"],
                        "opportunity_model":authority.artifact_pins["fixed-model.joblib"]["sha256"],"calibration":digest([vars(model.risk_temperature),vars(model.opportunity_temperature)])}
                w: dict[str,Any]={"schema":"ARK_SELECTOR_V2_WATCHLIST_V1","candidate_id":"PREOPEN_V2_TC_C01","session":d,"cutoff_jst":cutoff(date.fromisoformat(d)).isoformat(),
                   "generated_at":datetime.now(timezone.utc).isoformat(),"information_cutoff":cutoff(date.fromisoformat(d)).isoformat(),
                   "mode":"SYNTHETIC" if authority.test_only else "AUTHORIZED_DEVELOPMENT","historicalResearchOnly":True,"intended_use":"WATCHLIST_ONLY",
                   "conditionalOnOutcomeKnown":True,"rankScoreIsExpectedReturn":False,"universe_counts":counts,"selectedN":len(selected),
                   "items":[r|{f:False for f in FLAGS} for r in selected],"hashes":hashes,"status":"WATCHLIST_FIXED" if selected else "NO_CANDIDATE",
                   "reason":None if selected else ("NO_G1_TREND" if not counts["g1"] else "NO_G2_DAMAGE_CLEAR" if not counts["g2"] else "NO_PROBABILITY_QUALIFIED"),**{f:False for f in FLAGS}}
                w["hashes"]["watchlist"]=watchlist_hash(w);validate_watchlist(w);watches.append(w)
            store.put("forecast-"+role+".json",{"rows":rows.rows,"layers":rows.layers,"counts":rows.counts,"role":role,"sessions":rows.sessions,"a":a.tolist(),"b":b.tolist(),"raw_a":raw_a.tolist(),"raw_b":raw_b.tolist()})
            sealed={"sessions":rows.sessions,"watchlists":watches,"model_sha256":authority.artifact_pins["fixed-model.joblib"]["sha256"]}
            store.put("watchlists-"+role+".json",sealed);store.event("WATCHLISTS_SEALED-"+role,pre)
            result={"status":role+"_WATCHLISTS_FIXED","sessions":len(watches),"selectedN":sum(w["selectedN"] for w in watches),"test_only":authority.test_only}
        elif stage=="evaluate":
            sealed=store.get("watchlists-"+role+".json");forecast=store.get("forecast-"+role+".json")
            if sealed["model_sha256"]!=authority.artifact_pins["fixed-model.joblib"]["sha256"]:raise V2Error("WATCHLIST_MODEL_DRIFT")
            # The whole teacher descriptor set must be approved before OPEN event.
            authority.preflight_entries(request["manifest"],[("DAILY",d,role+"_TEACHER") for d in pre["split"][role]],pre)
            store.event("LABEL_OPENED-"+role,pre);teachers=reader.teachers(role)
            selected_keys=[(w["session"],r["canonical_symbol"],r["market"]) for w in sealed["watchlists"] for r in w["items"]]
            report=summarize(pre["split"][role],selected_keys,teachers)
            layers={k:{(r["session"],r["canonical_symbol"],r["market"]) for r in v} for k,v in forecast["layers"].items()}
            layers["selected"]=set(selected_keys);report["capture"]=capture(layers,teachers)
            excluded={(r["session"],r["canonical_symbol"],r["market"]):tuple(r["reasons"]) for r in forecast["layers"]["master"] if r["reasons"]}
            report["exclusions"]=exclusion_audit(excluded,teachers)
            diag_rows=forecast["rows"]
            labs=[teachers[(r["session"],r["canonical_symbol"],r["market"])] for r in diag_rows]
            yy=np.asarray([-1 if l.r is None else l.r for l in labs],dtype=np.int64)
            bb=np.asarray([-1 if l.b is None else l.b for l in labs],dtype=np.int64)
            ss=[r["session"] for r in diag_rows]
            report["probability_diagnostics"]={}
            if len(yy):
                from .weights import common_weights
                weights,_=common_weights(ss,(yy>=0).tolist())
                selected_mask=np.asarray([(r["session"],r["canonical_symbol"],r["market"]) in layers["selected"] for r in diag_rows])
                for kind,ak,bk in (("raw","raw_a","raw_b"),("calibrated","a","b")):
                    aa=np.asarray(forecast[ak]);ob=np.asarray(forecast[bk])
                    report["probability_diagnostics"][kind]={"g2_day_uniform":probability_diagnostics(aa,ob,yy,bb,ss,weights),
                          "g2_unweighted":probability_diagnostics(aa,ob,yy,bb,ss),
                          "selected_unweighted":probability_diagnostics(aa[selected_mask],ob[selected_mask],yy[selected_mask],bb[selected_mask],[s for s,m in zip(ss,selected_mask) if m]) if selected_mask.any() else {"status":"NOT_MEASURED"}}
            boot=[]
            for d in pre["split"][role]:
                ds=[teachers[k] for k in selected_keys if k[0]==d]
                boot.append({"selectedN":len(ds),"unknownN":sum(l.status!="KNOWN" for l in ds),
                             "raw1N":sum(bool(l.raw_winner and l.raw_winner[0]) for l in ds),
                             "clean3N":sum(bool(l.clean_winner and l.clean_winner[2]) for l in ds),
                             "clean5N":sum(bool(l.clean_winner and l.clean_winner[4]) for l in ds),
                             "loser3N":sum(bool(l.raw_loser and l.raw_loser[2]) for l in ds),
                             "loser5N":sum(bool(l.raw_loser and l.raw_loser[3]) for l in ds)})
            report["uncertainty"]=bootstrap_days(boot,consecutive_window_verified=True)
            result={"status":("VALIDATION_TARGETS_MET" if report["POINT_TARGETS_MET"] else "FAIL") if role=="VALIDATION" else "RESEARCH_MEASURED",
                    "report":report,"test_only":authority.test_only,"model_sha256":sealed["model_sha256"]}
            store.put("evaluation-"+role+".json",result)
        else:
            # Restore from self-produced artifact only; never fit to repair load.
            model=store.get("fixed-model.joblib",model=True);forecast=store.get("forecast-"+role+".json")
            rows=forecast["rows"]
            from .contracts import feature_names
            x=np.asarray([[np.nan if r["values"][k] is None else r["values"][k] for k in feature_names()] for r in rows],dtype=np.float64).reshape((-1,95))
            a,b=model.probabilities(x,authority)
            delta=max(float(np.max(np.abs(a-np.asarray(forecast["a"])))) if len(a) else 0.,float(np.max(np.abs(b-np.asarray(forecast["b"])))) if len(b) else 0.)
            if delta!=0:raise V2Error("RESTORE_PREDICTION_DRIFT_NO_REFIT")
            result={"status":"RESTORE_VERIFIED","prediction_max_abs_difference":delta,"fits":0,"test_only":authority.test_only}
            store.put("restore-"+role+".json",result)
        store.put("access-"+stage+"-"+role+".json",reader.access)
        store.event("FINISH-"+stage+"-"+role,pre)
        return result
    except Exception as error:
        # Preserve start/budget evidence, never auto retry or silently report zero.
        if "START-"+stage+"-"+role+".json" in {Path(k).name for k in authority.artifact_pins}:
            try:store.put("failure-"+stage+"-"+role+".json",{"reason":str(error),"retry_allowed":False})
            except FileExistsError:pass
        raise
    finally:
        os.close(fd);lock.unlink()
