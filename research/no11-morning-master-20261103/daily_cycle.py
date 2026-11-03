#!/usr/bin/env python3
"""No11 weekly/nightly -> next-session immutable handoff, with no daily user inputs.

The original after-close RSS pipelines produce daily/weekly G1, Chart50 and
previous RssChart archives. This module verifies their *actual* outputs, uses
the already pinned public-source preparer and source eligibility selector, and
publishes a date-scoped handoff for the existing Trade button. It never changes
Frozen strategy, invents data, launches Trade, or authorizes a broker order.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import uuid

SCHEMA = "ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1"
SYMBOL = re.compile(r"^[0-9A-Z]{4}\.T$")
SHA = re.compile(r"^[a-f0-9]{64}$")
SUCCESS = {
    "CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE",
    "YAHOO_WEEKLY_AND_RSS_429_G1_PREVIOUS_COMPLETE",
    "FRIDAY_FULL_UNIVERSE_AND_PREVIOUS_COMPLETE",
}
MARKERS = {
    "sessionDate": "NO11_WEEKLY_NIGHTLY_NEXT_SESSION=",
    "previousSession": "NO11_WEEKLY_NIGHTLY_ASOF=",
    "stage": "NO11_PREVIOUS_ARCHIVE_STAGE=",
    "capture": "NO11_PREVIOUS_CAPTURE_DIR=",
}

def need(ok, code):
    if not ok:
        raise ValueError("NO11_DAILY_CYCLE_" + code)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def safe(p, directory=False):
    p = Path(p)
    need(p.is_absolute(), "ABSOLUTE_PATH")
    for v in (p, *p.parents):
        if v.exists() or v.is_symlink():
            need(not v.is_symlink() and not (getattr(v.lstat(),"st_file_attributes",0)&1024),
                 "REPARSE_PATH")
    need(p.is_dir() if directory else p.is_file(), "SOURCE_MISSING")
    return p.resolve(strict=True)

def decode(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 25000000, "JSON_LENGTH")
    def pairs(items):
        out = {}
        for k,v in items:
            need(k not in out, "DUPLICATE_JSON_KEY")
            out[k] = v
        return out
    obj = json.loads(raw.decode("utf-8-sig"),object_pairs_hook=pairs,
                     parse_constant=lambda _: need(False,"NONFINITE_JSON"))
    need(type(obj) is dict, "JSON_OBJECT_REQUIRED")
    return obj

def read(path):
    raw=safe(path).read_bytes()
    return decode(raw),raw

def encode(obj):
    return (json.dumps(obj,ensure_ascii=False,allow_nan=False,
                       separators=(",",":"))+"\n").encode("utf-8")

def native_module(name, path):
    spec=importlib.util.spec_from_file_location(name, safe(path))
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def one(lines,prefix):
    v=[line[len(prefix):] for line in lines if line.startswith(prefix)]
    need(len(v)==1 and bool(v[0].strip()),"NIGHTLY_LOG_MARKER_"+re.sub(r"[^A-Z0-9_]","_",prefix))
    return v[0].strip()

def parse_nightly(raw):
    need(type(raw) is bytes and 0 < len(raw) < 20_000_000,"NIGHTLY_LOG_SIZE")
    lines=[l.strip() for l in raw.decode("utf-8-sig",errors="replace").splitlines() if l.strip()]
    success=[l for l in lines if l.startswith("NO11_WEEKLY_NIGHTLY_STAGE=")]
    need(len(success)>=1 and
         success[-1].split("=",1)[1] in SUCCESS, "NIGHTLY_NOT_COMPLETE")
    need("ORDER_TRANSMISSION=False" in lines, "NIGHTLY_ORDER_MODE")
    result={k:one(lines,p) for k,p in MARKERS.items()}
    def alternatives(prefixes):
        values=[]
        for p in prefixes:
            values += [line[len(p):] for line in lines if line.startswith(p)]
        need(len(values)==1 and bool(values[0]),"NIGHTLY_FILE_PATH_AMBIGUOUS")
        return values[0]
    result["chart"]=alternatives(("NO11_WEEKLY_NIGHTLY_CURRENT_CHART50=",
                                   "NO11_NIGHTLY_CHART50="))
    result["mask"]=alternatives(("NO11_WEEKLY_NIGHTLY_CURRENT_MASK=",
                                  "NO11_NIGHTLY_MASK="))
    result["weekly"]=alternatives(("NO11_WEEKLY_NIGHTLY_POOL_SOURCE=",
                                    "NO11_NIGHTLY_DAILY_RUN="))
    result["run"]=alternatives(("NO11_WEEKLY_NIGHTLY_REFRESH_RUN=",
                                 "NO11_NIGHTLY_DAILY_RUN="))
    need(re.fullmatch(r"20\d\d-\d\d-\d\d",result["sessionDate"]) is not None and
         re.fullmatch(r"20\d\d-\d\d-\d\d",result["previousSession"]) is not None and
         date.fromisoformat(result["previousSession"])<date.fromisoformat(result["sessionDate"]),
         "NIGHTLY_DATES")
    result["nightlyMode"]=success[-1].split("=",1)[1]
    return result

def verified_sources(m, record, seed):
    spec=seed["spec"]
    for key in ("engineRoot","runtimeRoot","h235ModelRoot","settingsFile"):
        m.safe(spec[key],directory=key in ("engineRoot","runtimeRoot","h235ModelRoot"))
    paths={key:safe(record[key],directory=key in ("weekly","run","capture"))
           for key in ("chart","mask","stage","capture","weekly","run")}
    need(paths["chart"].parent==paths["mask"].parent==paths["run"],
         "CHART_MASK_REFRESH_RUN_MISMATCH")
    chart,cb=m.read(paths["chart"])
    mask,mb=m.read(paths["mask"])
    stage,sb=m.read(paths["stage"])
    m.verify_receipt(paths["chart"],cb,"no11-chart50-private",16)
    m.verify_receipt(paths["mask"],mb,"no11-observed-pass-watch",16)
    m.verify_receipt(paths["stage"],sb,"previous-archive-stage",64)
    prepared=dict(seed["spec"],sessionDate=record["sessionDate"],
                  chartReceipt=str(paths["chart"]),passMask=str(paths["mask"]),
                  previousStage=str(paths["stage"]),previousCaptureDir=str(paths["capture"]),
                  weeklySourceRun=str(paths["weekly"]))
    selected,prior=m.validate_scope(prepared,chart,mask,stage)
    need(prior==record["previousSession"] and selected==stage["selectedSymbols"],
         "NIGHTLY_SOURCE_SCOPE")
    need(m.native_scope(prepared["engineRoot"],paths["chart"],paths["mask"])==selected,
         "NIGHTLY_NATIVE_SCOPE")
    need(set(selected)==set(stage.get("symbols",{})) and
         not stage.get("omittedSymbols"),
         "PREVIOUS_MINUTES_INCOMPLETE")
    root,progress,checkpoint_sha=previous_checkpoint(paths["capture"])
    need(checkpoint_sha==stage.get("progressSha256") and
         progress.get("completed")==len(selected)==progress.get("requested"),
         "PREVIOUS_ARCHIVE_CHECKPOINT_INCOMPLETE")
    return prepared,selected,cb,mb,sb

def previous_checkpoint(folder):
    files=list(folder.glob("progress-*.json"))
    need(bool(files) and len(files)<=250 and
         all(re.fullmatch(r"progress-\d{5}\.json",p.name) for p in files),
         "PREVIOUS_PROGRESS_FILE_SET")
    last=max(files,key=lambda p:int(p.stem.split("-")[1]))
    obj,raw=read(last)
    need(obj.get("schemaId")=="ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1" and
         obj.get("productionReady") is False and
         obj.get("orderTransmission") is False, "PREVIOUS_PROGRESS_SCHEMA")
    return folder,obj,digest(raw)

def check_seed(seed):
    need(seed.get("schemaId")=="ARK_NO11_MORNING_MASTER_HANDOFF_V1" and
         seed.get("productionReady") is False and
         seed.get("orderTransmission") is False and
         type(seed.get("spec")) is dict,"SEED_HANDOFF")

def publish(root,record,hand,stage_sha,log_sha):
    root=safe(root,True)
    directory=root/"prepared-days"
    directory.mkdir(exist_ok=True)
    directory=safe(directory,True)
    handoff, hb=read(hand)
    need(handoff.get("schemaId")=="ARK_NO11_MORNING_MASTER_HANDOFF_V1" and
         handoff.get("sessionDate")==record["sessionDate"] and
         handoff.get("previousSession")==record["previousSession"] and
         handoff.get("productionReady") is False and
         handoff.get("orderTransmission") is False and
         handoff.get("reviewStatus")=="NOT_REVIEWED","HANDOFF_SCOPE")
    symbols=handoff.get("selectedSymbols")
    need(type(symbols) is list and len(symbols)>0 and len(symbols)<=47 and
         len(set(symbols))==len(symbols) and
         all(type(x) is str and SYMBOL.fullmatch(x) for x in symbols),
         "HANDOFF_SYMBOLS")
    need(Path(hand).name=="morning-handoff-"+digest(hb)+".json",
         "HANDOFF_SOURCE_HASH")
    pointer={"schemaId":SCHEMA,"sessionDate":record["sessionDate"],
             "previousSession":record["previousSession"],
             "handoff":str(safe(hand)),"handoffSha256":digest(hb),
             "selectedSymbols":symbols,"selectedCount":len(symbols),
             "originalPreviousStageSha256":stage_sha,
             "nightlyLogSha256":log_sha,
             "nightlyMode":record["nightlyMode"],
             "humanReviewClaimed":False,
             "manualPricesRequired":False,
             "manualEvidenceRequired":False,
             "productionReady":False,"orderTransmission":False}
    dest=directory/(record["sessionDate"]+".json")
    raw=encode(pointer)
    if dest.exists():
        need(dest.read_bytes()==raw,"DAY_ALREADY_PINNED_TO_DIFFERENT_SOURCE")
    else:
        with dest.open("xb") as f:
            f.write(raw); f.flush();os.fsync(f.fileno())
    return dest

def stage(binding_file,nightly_file):
    binding, _=read(binding_file)
    need(binding.get("schemaId")=="ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1" and
         binding.get("orderTransmission") is False and
         binding.get("manualEvidenceRequired") is False and
         binding.get("manualPriceInputRequired") is False,"LAUNCHER_BINDING")
    need(type(binding.get("dailyCycleRoot")) is str,"DAY_ROOT_NOT_INSTALLED")
    for name,pin in (("runner","runnerSha256"),("scopeTool","scopeToolSha256"),
                     ("dailyCycleTool","dailyCycleToolSha256"),("handoff","handoffSha256")):
        need(type(binding.get(name)) is str and
             type(binding.get(pin)) is str and SHA.fullmatch(binding[pin]) and
             digest(safe(binding[name]).read_bytes())==binding[pin],
             "BOUND_"+name.upper()+"_CHANGED")
    root=safe(binding["dailyCycleRoot"],True)
    hand_seed, raw=read(binding["handoff"])
    check_seed(hand_seed)
    nightly_raw=safe(nightly_file).read_bytes()
    record=parse_nightly(nightly_raw)
    need(record["sessionDate"]!=hand_seed["sessionDate"],
         "SEED_SESSION_MUST_NOT_BE_RELABELED")
    today=date.today()
    need(date.fromisoformat(record["sessionDate"])>=today or
         (record["sessionDate"]==(date.fromisoformat(record["previousSession"])).isoformat()),
         "TARGET_SESSION_PASSED")
    m=native_module("ark_pinned_morning",binding["runner"])
    prepared,selected,cb,mb,sb=verified_sources(m,record,hand_seed)
    sources=root/record["sessionDate"]/"master-materials"
    sources.mkdir(parents=True,exist_ok=True)
    sources=safe(sources,True)
    prepared["outputRoot"]=str(sources)
    spec_file=m.immutable(sources,"nightly-spec",prepared)
    parent=m.prepare(spec_file)
    # The saved official source originals are rechecked before entry exclusion.
    scope=native_module("ark_pinned_entry_scope",binding["scopeTool"])
    narrowed=scope.scope(m,parent)
    ptr=publish(root,record,narrowed,digest(sb),digest(nightly_raw))
    print("NO11_DAILY_CYCLE_SESSION="+record["sessionDate"])
    print("NO11_DAILY_CYCLE_ASOF="+record["previousSession"])
    print("NO11_DAILY_CYCLE_CHART_BUDGET="+str(len(selected)))
    print("NO11_DAILY_CYCLE_ELIGIBLE_ENTRIES="+str(len(read(narrowed)[0]["selectedSymbols"])))
    print("NO11_DAILY_CYCLE_HANDOFF="+str(narrowed))
    print("NO11_DAILY_CYCLE_POINTER="+str(ptr))
    print("NO11_DAILY_CYCLE_STATUS=NEXT_SESSION_HANDOFF_READY")
    print("MANUAL_EVIDENCE_REQUIRED=False")
    print("MANUAL_PRICE_INPUT_REQUIRED=False")
    print("TRADE_LAUNCHED=False")
    print("ORDER_TRANSMISSION=False")

def main(argv=None):
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    s=sub.add_parser("stage")
    s.add_argument("--binding",type=Path,required=True)
    s.add_argument("--nightly-log",type=Path,required=True)
    a=p.parse_args(argv)
    if a.command=="stage":stage(a.binding,a.nightly_log)

if __name__=="__main__":
    try:main()
    except Exception as exc:
        reason=str(exc)
        if not re.fullmatch(r"NO11_DAILY_CYCLE_[A-Z0-9_]+",reason):
            reason="NO11_DAILY_CYCLE_UNVERIFIED_NIGHTLY_OR_LOCAL_RUNTIME"
        print("NO11_DAILY_CYCLE=BLOCKED|"+reason,file=sys.stderr)
        print("TRADE_LAUNCHED=False\nORDER_TRANSMISSION=False",file=sys.stderr)
        raise SystemExit(2)
