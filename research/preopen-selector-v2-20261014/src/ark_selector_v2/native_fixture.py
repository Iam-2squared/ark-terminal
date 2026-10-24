"""Test-only native objects and independent simulated owner channel.

No input path, real row or arbitrary matrix is accepted by the fixture factory.
Generated objects are private temporary outputs, not checked into the repository.
"""
from __future__ import annotations
from datetime import date,datetime,timedelta,timezone
from fractions import Fraction as F
from decimal import Decimal
from pathlib import Path
import contextlib
import importlib.util
import io
from typing import Any
import hashlib
import json
import numpy as np
from .artifact_io import exclusive_json,sha_file
from .authority import Authority,OwnerGrant,scoped_allowlists
from .contracts import ROOT,FLAGS,code_hash,configuration_hash,digest,registry
from .orchestration import dispatch,Store


def fixture_authority(root: Path) -> tuple[Authority,dict[str,Any]]:
    from .exact_math import V2Error
    if any((p/".git").exists() for p in (root.resolve(),*root.resolve().parents)):
        raise V2Error("PRIVATE_FIXTURE_OUTPUT_INSIDE_GIT_CHECKOUT")
    root.mkdir(parents=True,exist_ok=False)
    source=root/"generated-native";source.mkdir()
    days=[(date(2030,1,1)+timedelta(days=i)).isoformat() for i in range(175)]
    split={"HISTORY":days[:150],"FIT":days[150:162],"CAL":days[162:168],"VALIDATION":days[168:171],"FINAL":days[171:]}
    allow={"HISTORY":days[:-1]}
    for role in ("FIT","CAL","VALIDATION","FINAL"):
        allow[role+"_FEATURE"]=split[role];allow[role+"_TEACHER"]=split[role]
    entries=[];pins={}
    rng=np.random.default_rng(20261014)
    for idx,d in enumerate(days):
        records=[]
        for s in range(60):
            c=F(200+s*12)+F(idx,5)
            # All history has a comparable rising RAW close and enough capacity.
            # Labels are actual open/high/low of each session, not model arrays.
            r=0 if s<44 else 1 if s<52 else 2
            b=s%6
            if idx>=150:
                noise=.12 if idx<162 else .24
                if rng.random()<noise:r=int(rng.choice(3,p=[.8,.12,.08]))
                if rng.random()<noise:b=int(rng.integers(6))
            u=F(b)+F(1,5);a=F(1) if r==0 else F(4) if r==1 else F(6)
            h=c*(1+u/100);l=c*(1-a/100)
            # Reference turnover has independent synthetic variation, no labels.
            va=F(200000000+s*1000000+idx*10000)
            records.append({"canonical_symbol":f"{s+1:04d}","market":"PRIME","open":str(Decimal(c.numerator)/Decimal(c.denominator)),"high":str(Decimal(h.numerator)/Decimal(h.denominator)),"low":str(Decimal(l.numerator)/Decimal(l.denominator)),"close":str(Decimal(c.numerator)/Decimal(c.denominator)),
                            "volume":"1000000","turnover":str(Decimal(va.numerator)/Decimal(va.denominator)),"basis":"RAW","suffix":"GENERATED_RAW_V1","status":"TRADED","units":["JPY","SHARES","JPY"]})
        daily={"schema":"NATIVE_RAW_SESSION_V1","session":d,"records":records}
        master={"schema":"NATIVE_DATED_MASTER_V1","session":d,"records":[{"canonical_symbol":f"{s+1:04d}","rss_symbol":f"{s+1:04d}.T","market":"PRIME",
                   "security_kind":"COMMON_STOCK","lot":100,"rule_version":"ISOLATED_TEST_RULE_V1","domestic":True,"cash":True} for s in range(60)]}
        for dataset,value,fmt,stamp in (("DAILY",daily,"NATIVE_RAW_SESSION_V1",d+"T16:30:00+09:00"),("MASTER",master,"NATIVE_DATED_MASTER_V1",d+"T08:00:00+09:00")):
            purposes=[p for p,ds in allow.items() if d in ds and ((dataset=="MASTER" and p.endswith("FEATURE")) or (dataset=="DAILY" and (p=="HISTORY" or p.endswith("TEACHER"))))]
            if not purposes:continue
            path=dataset.lower()+"/"+d+".json";exclusive_json(source/path,value);sha,size=sha_file(source/path);pins[path]=(sha,size)
            ev={"source_id":path,"source_sha256":sha,"source_version":"GENERATED_NATIVE_V1","source_record_id":d,"event_at":stamp,"published_at":stamp,
                "available_at":stamp,"captured_at":stamp,"effective_session":d,"units":"JPY/SHARES/JPY" if dataset=="DAILY" else "IDENTITY",
                "raw_or_adjusted":"RAW","transformation_version":"NONE","original_ordinal":0,"lookback_sessions":0,"source_contract_hash":digest(fmt),
                "known_at_evidence_kind":"SYNTHETIC","missing_reason":None,"historical_live_parity_status":"ISOLATED_TEST_ONLY"}
            entries.append({"path":path,"sha256":sha,"bytes":size,"dataset":dataset,"session":d,"purposes":purposes,"protected":False,"exposure":"GENERATED_SYNTHETIC",
                            "format":fmt,"evidence":ev,"test_only":True,
                            "original":{"source_id":path,"sha256":sha,"bytes":size,"dataset":dataset,"allowed_record_dates":[d],
                                        "allowed_purposes":purposes,"rights_reference":"test://generated-original-no-market-rights"}})
    manifest={"schema":"ARK_V2_NATIVE_MANIFEST_V1","entries":entries}
    pre={"schema":"ARK_V2_NATIVE_PRECOMMIT_V1","hashes":{"code":code_hash(),"config":configuration_hash(),"schema":digest(registry())},"manifest_sha256":digest(manifest),
         "split":split,"calendar_sessions":days,"allowlists":allow,"source_routes":{"daily":"NATIVE_RAW_SESSION_V1","master":"NATIVE_DATED_MASTER_V1","optional":"SOURCE_NOT_JOINED"},
         "resource_limits":{"universe_rows_upper_bound":60,"ram_bytes":1073741824,"max_native_object_bytes":10485760},"test_only":True,"census_receipt_sha256":None,"teacher_open_after":{role:split[role][-1]+"T17:00:00+09:00" for role in ("FIT","CAL","VALIDATION","FINAL")}}
    authority=Authority(source,root/"stage-output",{},digest(manifest),pre,test_only=True,fixture_pins=pins)
    install_test_grant(authority,"B")
    return authority,manifest


def install_test_grant(authority: Authority,mode: str) -> None:
    if not authority.test_only:raise ValueError("Test grant cannot authorize market authority")
    text="ISOLATED ENGINEERING TEST OWNER SIMULATION: "+mode+"; not market approval"
    sha=hashlib.sha256(text.encode()).hexdigest();stamp=datetime.now(timezone.utc).isoformat();ref="test://generated-owner/"+mode
    parent=authority.grants["B"].approval_pin if mode=="C" else None
    approval={"schema":"ARK_V2_NATIVE_OWNER_GRANT_V1","candidate_id":"PREOPEN_V2_TC_C01","mode":mode,"owner_original_sha256":sha,
              "owner_reference":ref,"owner_approved_at":stamp,"precommit_sha256":digest(authority.precommit),"manifest_sha256":authority.manifest_pin,
              "allowlists":scoped_allowlists(authority.precommit,mode),"split":authority.precommit["split"],"parent_approval_sha256":parent,
              "census_receipt_sha256":authority.precommit["census_receipt_sha256"],"test_only":True,
              "budget":{"candidates":0,"fits":0,"calibrations":0} if mode=="B" else {"candidates":1,"fits":2,"calibrations":2},**{f:False for f in FLAGS}}
    authority.grants[mode]=OwnerGrant(approval,text,ref,stamp,digest(approval),sha,digest(authority.precommit),parent)


def request_for(authority: Authority,manifest: dict[str,Any],mode: str,role: str="FIT_CAL") -> dict[str,Any]:
    # Copy request JSON so tests cannot mutate the trusted channel by aliasing.
    return json.loads(json.dumps({"schema":"ARK_V2_STAGE_REQUEST_V1","candidate_id":"PREOPEN_V2_TC_C01","mode":mode,
                                 "approval":authority.grants[mode].approval,"manifest":manifest,"role":role}))


def run_native_fixture(output: Path) -> dict[str,Any]:
    # Exercise ordinary census/train/calibrate/predict/evaluate/restore CLI
    # branches with an isolated host-supplied authority; no authority-file flag.
    spec=importlib.util.spec_from_file_location("ark_v2_isolated_host_cli",ROOT/"tools/v2_cli.py")
    assert spec is not None and spec.loader is not None
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    def invoke(stage: str,mode: str,role: str="FIT_CAL") -> dict[str,Any]:
        request_path=output/("request-"+stage+"-"+role+".json")
        exclusive_json(request_path,request_for(authority,manifest,mode,role))
        capture=io.StringIO()
        with contextlib.redirect_stdout(capture):
            result_code=cli.main([stage,"--request",str(request_path)],authority=authority)
        result=json.loads(capture.getvalue())
        if result_code!=0:raise RuntimeError("ISOLATED_STAGE_CLI_BLOCKED: "+str(result))
        return result
    authority,manifest=fixture_authority(output)
    results={"census":invoke("census","B")}
    authority.precommit["census_receipt_sha256"]=digest(results["census"])
    install_test_grant(authority,"C")
    for stage in ("train","calibrate"):
        results[stage]=invoke(stage,"C")
    for stage in ("predict","evaluate","restore-verify"):
        results[stage]=invoke(stage,"C","VALIDATION")
    model=Store(authority).get("fixed-model.joblib",model=True)
    # FINAL is conditional on the SAME unmodified point targets. A failed
    # synthetic validation is retained and tests the sealed FINAL boundary.
    final="UNOPENED_VALIDATION_FAILED"
    if results["evaluate"]["status"]=="VALIDATION_TARGETS_MET":
        for stage in ("predict","evaluate","restore-verify"):
            results["final-"+stage]=invoke(stage,"C","FINAL")
        final="ISOLATED_SYNTHETIC_EVALUATED"
    events=[p for p in authority.artifact_pins if p.startswith("events/")]
    receipt={"schema":"ARK_V2_NATIVE_ROUTE_TEST_RECEIPT_V1","test_only":True,"market_approval_established":False,
             "code_hash":code_hash(),"config_hash":configuration_hash(),"schema_hash":digest(registry()),
             "entrypoint":"SIX_NORMAL_STAGE_CLI_SUBCOMMANDS_WITH_ISOLATED_HOST_AUTHORITY","input_path":"GENERATED_NATIVE_RAW_TO_G0_G1_G2_CORE95_TEACHERS_HGB_ARTIFACT_FORECAST_EVALUATION",
             "FIT_rows":results["census"]["stats"]["FIT"]["known"],"CAL_rows":results["census"]["stats"]["CAL"]["known"],
             "isolated_candidate_reservations":sum("CANDIDATE_RESERVED" in p for p in events),
             "isolated_fit_starts":sum("FIT_STARTED" in p for p in events),"isolated_calibration_starts":sum("CAL_STARTED" in p for p in events),
             "tree_count":model.receipt["tree_count"],"restore_prediction_difference":results["restore-verify"]["prediction_max_abs_difference"],
             "validation_status":results["evaluate"]["status"],"final_status":final,
             "market_candidates":0,"market_fits":0,"market_calibrations":0,**{f:False for f in FLAGS}}
    exclusive_json(output/"native-route-receipt.json",receipt)
    return receipt
