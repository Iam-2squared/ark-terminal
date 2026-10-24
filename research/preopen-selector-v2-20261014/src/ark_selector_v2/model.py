"""Two fixed multiclass estimators. The runnable route accepts factory data only."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import time
from typing import Any, Callable
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits
from .contracts import ROOT, code_hash, configuration_hash, digest, feature_names, registry
from .exact_math import V2Error
from .weights import common_weights, used_columns, check_cal_support
from .calibration import Temperature, fit_temperature, temperature, probability_matrix
from .experiment_ledger import ExperimentLedger
from .resources import measure_stage,memory_preflight

MODEL_PARAMS={"loss":"log_loss","learning_rate":0.05,"max_leaf_nodes":15,"max_depth":None,
              "max_iter":120,"min_samples_leaf":40,"l2_regularization":10.0,"max_bins":255,
              "max_features":1.0,"categorical_features":None,"class_weight":None,
              "early_stopping":False,"warm_start":False,"random_state":20261014}


@dataclass
class TrainingData:
    x: np.ndarray
    risk: np.ndarray  # -1 is genuine UNKNOWN, never R0.
    opportunity: np.ndarray
    sessions: list[str]
    symbols: list[str]
    role: str
    origin: str

    def fingerprint(self) -> str:
        h=hashlib.sha256()
        for a in (self.x,self.risk,self.opportunity):
            h.update(str(a.shape).encode()+str(a.dtype).encode()+a.tobytes())
        h.update(digest([self.sessions,self.symbols,self.role,self.origin]).encode())
        return h.hexdigest()

    def validate(self) -> None:
        n=len(self.x)
        if (self.x.ndim!=2 or self.x.shape[1]!=95 or self.x.dtype!=np.float64
                or np.isinf(self.x).any() or len(self.risk)!=n or len(self.opportunity)!=n
                or len(self.sessions)!=n or len(self.symbols)!=n
                or self.role not in {"FIT","CAL"}):
            raise V2Error("INVALID_TRAINING_DATA_CONTRACT")
        if self.risk.dtype.kind not in "iu" or self.opportunity.dtype.kind not in "iu":
            raise V2Error("NONINTEGER_TEACHER_CLASS")
        if np.any((self.risk < -1)|(self.risk>2)) or np.any((self.opportunity < -1)|(self.opportunity>5)):
            raise V2Error("TEACHER_CLASS_OUTSIDE_CONTRACT")
        if np.any((self.risk==-1)!=(self.opportunity==-1)):
            raise V2Error("UNKNOWN_TEACHER_MASK_MISMATCH")
        if n!=len(set(zip(self.sessions,self.symbols))):
            raise V2Error("DUPLICATE_TRAINING_IDENTITY")


@dataclass(frozen=True)
class SyntheticCertificate:
    fit_hash: str
    cal_hash: str
    factory_id: str


def synthetic_factory() -> tuple[TrainingData,TrainingData,SyntheticCertificate]:
    """All values generated here; no caller-supplied row/seed/file is accepted."""
    rng=np.random.default_rng(20261014)
    def make(n: int, role: str, offset: int, strength: float) -> TrainingData:
        x=rng.normal(size=(n,95)).astype(np.float64)
        x[:,93]=np.nan
        x[:,94]=1
        latent=np.column_stack((1.5*x[:,0],-.7*x[:,0]+.3*x[:,1],-1.0*x[:,0]))*strength
        rp=np.exp(latent-latent.max(axis=1,keepdims=True));rp/=rp.sum(axis=1,keepdims=True)
        risk=np.asarray([rng.choice(3,p=p) for p in rp],dtype=np.int64)
        latent2=np.column_stack([(k-2.5)*.4*x[:,2] for k in range(6)])*strength
        bp=np.exp(latent2-latent2.max(axis=1,keepdims=True));bp/=bp.sum(axis=1,keepdims=True)
        opportunity=np.asarray([rng.choice(6,p=p) for p in bp],dtype=np.int64)
        risk[::101]=-1;opportunity[::101]=-1
        # Synthetic identifiers and sessions are explicitly fictitious.
        from datetime import date,timedelta
        days=[(date(2030,1,1)+timedelta(days=offset+i//100)).isoformat() for i in range(n)]
        symbols=[f"{i%100:04d}" for i in range(n)]
        return TrainingData(x,risk,opportunity,days,symbols,role,"ARK_V2_GENERATOR_20261014_V1")
    fit=make(1800,"FIT",0,1.0)
    cal=make(600,"CAL",25,.4)
    return fit,cal,SyntheticCertificate(fit.fingerprint(),cal.fingerprint(),"ARK_V2_GENERATOR_20261014_V1")


def confirm_synthetic(fit: TrainingData, cal: TrainingData, cert: SyntheticCertificate) -> None:
    if not isinstance(cert,SyntheticCertificate):
        raise V2Error("SYNTHETIC_FACTORY_CERTIFICATE_REQUIRED")
    # Reconstruct independently from the fixed code factory, preventing real
    # rows relabelled SYNTHETIC or a self-supplied fingerprint from bypassing.
    _,_,expected=synthetic_factory()
    if (cert!=expected or fit.fingerprint()!=expected.fit_hash or cal.fingerprint()!=expected.cal_hash
            or fit.origin!=expected.factory_id or cal.origin!=expected.factory_id):
        raise V2Error("REAL_OR_MODIFIED_ROWS_IN_SYNTHETIC_MODE")


def synthetic_forecast_factory() -> np.ndarray:
    rng=np.random.default_rng(20261015)
    x=rng.normal(size=(150,95)).astype(np.float64)
    x[:,93]=np.nan;x[:,94]=1
    row,_=synthetic_gate_canary()
    x[0]=row
    return x


def synthetic_gate_canary() -> tuple[np.ndarray,dict[str,Any]]:
    """Actual RAW candles -> G0/G1/G2 -> 95-column builder, no labels."""
    from datetime import date,timedelta
    from fractions import Fraction as F
    from .calendar_phase import ExchangeCalendar
    from .contracts import Candle,Identity
    from .gates import g0,g1,g2
    from .features_daily import daily_features
    from .features_context import assemble_features
    days=tuple(date(2029,9,1)+timedelta(days=i) for i in range(151))
    rows=[]
    for i,d in enumerate(days[:-1]):
        c=F(100)+F(i,10)
        rows.append(Candle(d,c,c+1,c-1,c,F(1000000),F(200000000)))
    calendar=ExchangeCalendar(days,digest([d.isoformat() for d in days]),"SYNTHETIC")
    identity=Identity("0001","0001.T","PRIME",days[-1],"COMMON_STOCK",100,"SYNTHETIC_RULE")
    gates=(g0(rows,identity,days[-1],calendar),g1(rows),g2(rows))
    if not all(g.passed for g in gates):
        raise V2Error("SYNTHETIC_GATE_CANARY_FAILED")
    frame=assemble_features(daily_features(rows,rows[-1].session))
    vector=np.asarray([np.nan if v is None else v for v in frame.values.values()],dtype=np.float64)
    return vector,{"g0":gates[0].state,"g1":gates[1].state,"g2":gates[2].state,
                   "registered_columns":len(vector),"feature_hash":digest(frame.values),
                   "optional_unjoined_columns":int(np.isnan(vector[51:]).sum()),
                   "calendar_evidence":"SYNTHETIC"}


def partition(fit: TrainingData) -> tuple[np.ndarray,np.ndarray,np.ndarray,float]:
    fit.validate()
    known=fit.risk>=0
    r0=fit.risk==0
    weights,c=common_weights(fit.sessions,known.tolist())
    return known,r0,weights,c


def teacher_support(data: TrainingData, *, synthetic: bool = False) -> dict[str,Any]:
    data.validate()
    known,r0,_,_=partition(data)
    stats: dict[str,Any]={"known":int(known.sum()),"r0":int(r0.sum()),"unknown":int((~known).sum()),"classes":{}}
    proposal=json.loads((ROOT/"V2_PARAM_PROPOSAL.json").read_text())["support_proposal"]
    is_fit=data.role=="FIT"
    for head,mask,y,classes in (("risk",known,data.risk,3),("opportunity",r0,data.opportunity,6)):
        for cls in range(classes):
            indices=np.flatnonzero(mask&(y==cls))
            s={"N":len(indices),"days":len({data.sessions[i] for i in indices}),"symbols":len({data.symbols[i] for i in indices})}
            stats["classes"][f"{head}_{cls}"]=s
            minimums=(1,1,1) if synthetic else ((100,10,20) if is_fit else (20,5,10))
            if any(s[k]<minimum for k,minimum in zip(("N","days","symbols"),minimums)):
                raise V2Error("BLOCKED_INSUFFICIENT_TEACHER_SUPPORT")
    if not synthetic:
        if is_fit and (stats["known"]<proposal["risk_fit_known_min"] or stats["r0"]<proposal["opportunity_fit_r0_min"]):
            raise V2Error("BLOCKED_INSUFFICIENT_TEACHER_SUPPORT")
        if stats["unknown"]/len(data.x)>proposal["g2_unknown_teacher_rate_max"]:
            raise V2Error("BLOCKED_OUTCOME_COVERAGE")
    return stats


def oracle_supply(sessions: list[str], clean_counts: dict[str,tuple[int,int]]) -> dict[str,float]:
    if not sessions or sessions!=sorted(set(sessions)) or set(clean_counts)-set(sessions):
        raise V2Error("ORACLE_ALL_CALENDAR_SESSIONS_REQUIRED")
    upper={"clean3":sum(min(15,clean_counts.get(d,(0,0))[0]) for d in sessions)/len(sessions),
           "clean5":sum(min(15,clean_counts.get(d,(0,0))[1]) for d in sessions)/len(sessions)}
    if upper["clean3"]<1 or upper["clean5"]<.5:
        raise V2Error("BLOCKED_GATE_ORACLE_SUPPLY_FIT0")
    return upper


@dataclass
class ModelBundle:
    risk_model: Any
    opportunity_model: Any
    risk_columns: tuple[int,...]
    opportunity_columns: tuple[int,...]
    risk_temperature: Temperature
    opportunity_temperature: Temperature
    receipt: dict[str,Any]

    def validate_identity(self) -> None:
        if (self.receipt["code_hash"]!=code_hash() or self.receipt["schema_hash"]!=digest(registry())
                or self.receipt["config_hash"]!=configuration_hash()):
            raise V2Error("MODEL_CODE_CONFIG_SCHEMA_DRIFT_NO_REFIT")
        if not np.array_equal(self.risk_model.classes_,np.arange(3)) or not np.array_equal(self.opportunity_model.classes_,np.arange(6)):
            raise V2Error("MODEL_CLASS_ORDER_MISMATCH")

    def probabilities(self, x: np.ndarray, *, origin: str) -> tuple[np.ndarray,np.ndarray,np.ndarray,np.ndarray]:
        self.validate_identity()
        if origin!=self.receipt["origin"]:
            raise V2Error("SYNTHETIC_MODEL_WITH_MARKET_INPUT")
        if x.dtype!=np.float64 or x.ndim!=2 or x.shape[1]!=95 or np.isinf(x).any():
            raise V2Error("INVALID_PREDICTION_MATRIX")
        if hashlib.sha256(x.tobytes()).hexdigest()!=self.receipt["synthetic_forecast_hash"]:
            raise V2Error("REAL_OR_MODIFIED_FORECAST_IN_SYNTHETIC_MODE")
        with threadpool_limits(limits=1):
            a=probability_matrix(self.risk_model.predict_proba(x[:,self.risk_columns]),3)
            b=probability_matrix(self.opportunity_model.predict_proba(x[:,self.opportunity_columns]),6)
        return a,b,temperature(a,self.risk_temperature.beta),temperature(b,self.opportunity_temperature.beta)


def fit_synthetic_bundle(fit: TrainingData, cal: TrainingData, cert: SyntheticCertificate,
                         ledger: ExperimentLedger, binding: dict[str,Any],
                         *, estimator_factory: Callable[...,Any] = HistGradientBoostingClassifier) -> ModelBundle:
    confirm_synthetic(fit,cal,cert)
    fit.validate();cal.validate()
    if fit.role!="FIT" or cal.role!="CAL" or max(fit.sessions)>=min(cal.sessions):
        raise V2Error("FIT_CAL_PARTITION_OR_CHRONOLOGY_ERROR")
    teacher_support(fit,synthetic=True);teacher_support(cal,synthetic=True)
    known,r0,wf,cf=partition(fit)
    cknown,cr0,wc,cc=partition(cal)
    risk_cols,risk_removed=used_columns(fit.x[known])
    opp_cols,opp_removed=used_columns(fit.x[r0])
    check_cal_support(cal.x[cknown],risk_cols)
    check_cal_support(cal.x[cr0],opp_cols)
    memory_plan=memory_preflight(len(fit.x),len(cal.x))
    candidate="SYNTHETIC_V2_ENGINEERING"
    risk=estimator_factory(**MODEL_PARAMS)
    opp=estimator_factory(**MODEL_PARAMS)
    start=time.monotonic()
    stages: dict[str,Any]={}
    with threadpool_limits(limits=1):
        ledger.append("RISK_FIT_STARTED",candidate,binding)
        with measure_stage(stages,"risk_fit"):
            risk.fit(fit.x[known][:,risk_cols],fit.risk[known],sample_weight=wf[known])
        ledger.append("RISK_FIT_FINISHED",candidate,binding)
        ledger.append("OPPORTUNITY_FIT_STARTED",candidate,binding)
        with measure_stage(stages,"opportunity_fit"):
            opp.fit(fit.x[r0][:,opp_cols],fit.opportunity[r0],sample_weight=wf[r0])
        ledger.append("OPPORTUNITY_FIT_FINISHED",candidate,binding)
        if not np.array_equal(risk.classes_,np.arange(3)) or not np.array_equal(opp.classes_,np.arange(6)):
            raise V2Error("MODEL_CLASS_ORDER_MISMATCH")
        ledger.append("RISK_CAL_STARTED",candidate,binding)
        with measure_stage(stages,"risk_calibration"):
            rt=fit_temperature(risk.predict_proba(cal.x[cknown][:,risk_cols]),cal.risk[cknown],wc[cknown])
        ledger.append("RISK_CAL_FINISHED",candidate,binding)
        ledger.append("OPPORTUNITY_CAL_STARTED",candidate,binding)
        with measure_stage(stages,"opportunity_calibration"):
            ot=fit_temperature(opp.predict_proba(cal.x[cr0][:,opp_cols]),cal.opportunity[cr0],wc[cr0])
        ledger.append("OPPORTUNITY_CAL_FINISHED",candidate,binding)
    receipt={"schema":"ARK_V2_MODEL_BUNDLE_V1","mode":"SYNTHETIC","origin":cert.factory_id,
             "code_hash":code_hash(),"schema_hash":digest(registry()),"config_hash":configuration_hash(),
             "risk_classes":[0,1,2],"opportunity_classes":list(range(6)),
             "used_columns_risk":[feature_names()[j] for j in risk_cols],
             "used_columns_opportunity":[feature_names()[j] for j in opp_cols],
             "used_columns_risk_hash":digest(risk_cols),"used_columns_opportunity_hash":digest(opp_cols),
             "removed_risk":risk_removed,"removed_opportunity":opp_removed,
             "fit_weight_common_scale":cf,"cal_weight_common_scale":cc,
             "fit_data_hash":fit.fingerprint(),"cal_data_hash":cal.fingerprint(),
             "synthetic_forecast_hash":hashlib.sha256(synthetic_forecast_factory().tobytes()).hexdigest(),
             "base_fit_calls":2,"calibration_optimizations":2,
             "risk_optimizer_objective_calls":rt.objective_calls,"opportunity_optimizer_objective_calls":ot.objective_calls,
             "tree_count":sum(len(group) for group in risk._predictors)+sum(len(group) for group in opp._predictors),
             "wall_seconds":time.monotonic()-start,"fixed_at":datetime.now(timezone.utc).isoformat(),
             "conditionalOnOutcomeKnown":True,"productionReady":False}
    receipt["resources_by_stage"]=stages
    receipt["memory_preflight"]=memory_plan
    receipt["gate_pipeline_canary"]=synthetic_gate_canary()[1]
    return ModelBundle(risk,opp,risk_cols,opp_cols,rt,ot,receipt)
