"""Per-session native adapter. Teachers and forecast dependencies never share IO."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
import hashlib
import json
import numpy as np
from .authority import Authority
from .artifact_io import safe_path
from .calendar_phase import ExchangeCalendar, cutoff
from .contracts import Candle, Identity, SourceEvidence, bind_provenance, digest, forbid_outcomes, feature_names
from .exact_math import V2Error
from .gates import g0,g1,g2
from .features_daily import daily_features
from .features_context import assemble_features
from .labels import Label,label
from .model import TrainingData


@dataclass
class NativeRows:
    role: str
    sessions: list[str]
    rows: list[dict[str,Any]]
    counts: dict[str,dict[str,int]]
    layers: dict[str,list[dict[str,Any]]]

    def matrix(self) -> np.ndarray:
        return np.asarray([[np.nan if r["values"][k] is None else r["values"][k] for k in feature_names()] for r in self.rows],dtype=np.float64).reshape((-1,95))

    def training(self, teachers: dict[tuple[str,str,str],Label], test_only: bool) -> TrainingData:
        labs=[teachers[(r["session"],r["canonical_symbol"],r["market"])] for r in self.rows]
        return TrainingData(self.matrix(),np.asarray([-1 if l.r is None else l.r for l in labs],dtype=np.int64),
                            np.asarray([-1 if l.b is None else l.b for l in labs],dtype=np.int64),
                            [r["session"] for r in self.rows],[r["canonical_symbol"] for r in self.rows],
                            self.role,"ISOLATED_NATIVE_FIXTURE" if test_only else "ADMITTED_NATIVE")


class NativeReader:
    def __init__(self, authority: Authority, manifest: dict[str,Any], pre: dict[str,Any]):
        self.authority=authority;self.manifest=manifest;self.pre=pre
        self.calendar=ExchangeCalendar(tuple(date.fromisoformat(d) for d in pre["calendar_sessions"]),
                                      digest(pre["calendar_sessions"]),"SYNTHETIC" if authority.test_only else "OFFICIAL")
        self.access: list[dict[str,Any]]=[]

    def read(self, e: dict[str,Any]) -> tuple[dict[str,Any],SourceEvidence]:
        # Descriptors are already approved as one batch. Verify bytes BEFORE JSON.
        path=safe_path(self.authority.root,e["path"])
        data=path.read_bytes()
        if len(data)!=e["bytes"] or hashlib.sha256(data).hexdigest()!=e["sha256"]:
            raise V2Error("NATIVE_SOURCE_HASH_OR_SIZE_MISMATCH")
        value=json.loads(data)
        ev=dict(e["evidence"])
        for k in ("event_at","published_at","available_at","captured_at"):ev[k]=datetime.fromisoformat(ev[k])
        ev["effective_session"]=date.fromisoformat(ev["effective_session"])
        evidence=SourceEvidence(**ev)
        if evidence.source_sha256!=e["sha256"] or evidence.source_id!=e["path"] or evidence.effective_session.isoformat()!=e["session"]:
            raise V2Error("SOURCE_EVIDENCE_IDENTITY_MISMATCH")
        if evidence.known_at_evidence_kind=="SYNTHETIC" and not self.authority.test_only:
            raise V2Error("SYNTHETIC_PROVENANCE_IN_MARKET_MODE")
        self.access.append({"path":e["path"],"sha256":e["sha256"],"session":e["session"],"purpose":e["authorized_purpose"]})
        return value,evidence

    def candle_rows(self, value: dict[str,Any], session: str) -> dict[tuple[str,str],Candle]:
        if set(value)!={"schema","session","records"} or value["schema"]!="NATIVE_RAW_SESSION_V1" or value["session"]!=session:
            raise V2Error("NATIVE_DAILY_SCHEMA_OR_DATE")
        rows={}
        if len(value["records"])>self.pre["resource_limits"]["universe_rows_upper_bound"]:raise V2Error("SOURCE_UNIVERSE_EXCEEDS_PREFLIGHT_BOUND")
        for r in value["records"]:
            if set(r)!={"canonical_symbol","market","open","high","low","close","volume","turnover","basis","suffix","status","units"}:
                raise V2Error("NATIVE_RAW_FIELDS")
            key=(r["canonical_symbol"],r["market"])
            if key in rows: raise V2Error("DUPLICATE_NATIVE_IDENTITY")
            if r["units"]!=["JPY","SHARES","JPY"] or r["basis"]!="RAW" or not r["suffix"]:
                raise V2Error("NATIVE_UNITS_OR_RAW_BASIS")
            rows[key]=Candle.from_values(date.fromisoformat(session),*(r[k] for k in ("open","high","low","close","volume","turnover")),
                                        basis=r["basis"],comparable_suffix=r["suffix"],status=r["status"],units=tuple(r["units"]))
        return rows

    def forecast_plan(self, role: str) -> list[tuple[str,str,str]]:
        if role not in {"FIT","CAL","VALIDATION","FINAL"}:raise V2Error("FORECAST_ROLE")
        sessions=self.pre["split"][role]
        wanted=[]
        for d in sessions:
            idx=self.pre["calendar_sessions"].index(d)
            if idx<150:raise V2Error("NATIVE_REFERENCE_HISTORY_INSUFFICIENT")
            wanted.append(("MASTER",d,role+"_FEATURE"))
            for h in self.pre["calendar_sessions"][idx-150:idx]:wanted.append(("DAILY",h,"HISTORY"))
        return list(dict.fromkeys(wanted))

    def forecast(self, role: str) -> NativeRows:
        sessions=self.pre["split"][role]
        wanted=self.forecast_plan(role)
        entries=self.authority.preflight_entries(self.manifest,list(dict.fromkeys(wanted)),self.pre)
        by_key={(e["dataset"],e["session"]):e for e in entries}
        loaded: dict[tuple[str,str],tuple[dict[str,Any],SourceEvidence]]={}
        result=NativeRows(role,sessions,[],{}, {"master":[],"price":[],"g0":[],"g1":[],"g2":[]})
        for d in sessions:
            sd=date.fromisoformat(d)
            idx=self.pre["calendar_sessions"].index(d)
            histories=self.pre["calendar_sessions"][idx-150:idx]
            keep={("DAILY",h) for h in histories}|{("MASTER",d)}
            loaded={k:v for k,v in loaded.items() if k in keep}
            for key in sorted(keep):
                if key not in loaded:
                    v,ev=self.read(by_key[key]);forbid_outcomes(v);loaded[key]=(v,ev)
            master,master_ev=loaded[("MASTER",d)]
            master_ev.validate(cutoff(sd))
            if set(master)!={"schema","session","records"} or master["schema"]!="NATIVE_DATED_MASTER_V1" or master["session"]!=d or not master["records"]:
                raise V2Error("INPUT_BLOCKED_DATED_MASTER")
            idx=self.pre["calendar_sessions"].index(d)
            histories=self.pre["calendar_sessions"][idx-150:idx]
            daily={};evidence=[]
            for h in histories:
                v,ev=loaded[("DAILY",h)];ev.validate(cutoff(sd),basis="RAW")
                if ev.units!="JPY/SHARES/JPY":raise V2Error("SOURCE_UNIT_CONTRACT")
                daily[h]=self.candle_rows(v,h);evidence.append(ev)
            if len(master["records"])>self.pre["resource_limits"]["universe_rows_upper_bound"]:raise V2Error("MASTER_UNIVERSE_EXCEEDS_PREFLIGHT_BOUND")
            counts={k:0 for k in ("master","price","g0","g1","g2","prob")}
            seen=set()
            for m in master["records"]:
                ident=Identity(effective_session=sd,**m)
                key=(ident.canonical_symbol,ident.market)
                if key in seen:raise V2Error("DUPLICATE_DATED_MASTER_IDENTITY")
                seen.add(key)
                if not ident.eligible(sd):continue
                counts["master"]+=1
                history=[daily[h][key] for h in histories if key in daily[h]]
                diagnostic={"session":d,"canonical_symbol":key[0],"market":key[1],"reasons":[]}
                result.layers["master"].append(diagnostic)
                if not history or history[-1].session!=date.fromisoformat(histories[-1]) or history[-1].close is None or history[-1].close<=75:continue
                counts["price"]+=1;result.layers["price"].append(diagnostic)
                gate0=g0(history,ident,sd,self.calendar)
                if not gate0.passed:diagnostic["reasons"]=list(gate0.reasons);continue
                counts["g0"]+=1;result.layers["g0"].append(diagnostic)
                gate1=g1(history)
                if not gate1.passed:diagnostic["reasons"]=list(gate1.reasons);continue
                counts["g1"]+=1;result.layers["g1"].append(diagnostic)
                gate2=g2(history)
                if not gate2.passed:diagnostic["reasons"]=list(gate2.reasons);continue
                counts["g2"]+=1;result.layers["g2"].append(diagnostic)
                frame=assemble_features(daily_features(history,history[-1].session))
                # Sources already validated above. Store a content-bound dependency
                # set once; columns reference it instead of duplicating 150
                # full provenance records for every feature and every row.
                dependency_ids=[e.source_id for e in evidence]
                dep_hash=digest(dependency_ids)
                available=max(e.available_at for e in evidence).isoformat()
                frame.metadata={"source_manifest_sha256":self.authority.manifest_pin,
                                "dependency_sets":{dep_hash:dependency_ids},
                                "column_provenance":{k:{"source_set_sha256":dep_hash if v is not None else None,
                                                        "available_at":available if v is not None else None,
                                                        "missing_reason":frame.missing.get(k)} for k,v in frame.values.items()}}
                result.rows.append({"session":d,"canonical_symbol":key[0],"rss_symbol":ident.rss_symbol,"market":key[1],
                                    "values":frame.values,"missing_map":frame.missing,"provenance":frame.metadata,
                                    "feature_hash":digest(frame.values),"source_times":{"available_at":max(e.available_at for e in evidence).isoformat()}})
            result.counts[d]=counts
        return result

    def teachers(self, role: str) -> dict[tuple[str,str,str],Label]:
        wanted=[("DAILY",d,role+"_TEACHER") for d in self.pre["split"][role]]
        entries=self.authority.preflight_entries(self.manifest,wanted,self.pre)
        out={}
        for e in entries:
            v,ev=self.read(e)
            ev.validate(datetime.fromisoformat(self.pre["teacher_open_after"][role]),basis="RAW")
            for (sym,market),row in self.candle_rows(v,e["session"]).items():out[(e["session"],sym,market)]=label(row)
        return out
