#!/usr/bin/env python3
"""No.1.1 26 Oct PRE-DAY local input inventory. Never starts Excel or broker.

Unlike day-of bootstrap, this runs on the prior calendar day. It does not
generate a dated master, set evidence flags, or certify any 26 Oct data.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys

SCHEMA="ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1"
DATE="2026-10-26"
PREFIX="NO11_26_PRECHECK_"
REQUIRED=("dailyRun","datedMaster","runtimeRoot","privateRoot")
CHOICE=("previousContext","previousCaptureFiles")
OPTIONAL=("h235ModelRoot","pinsFile")
def fail(code):
    raise ValueError(PREFIX+code)
def check_path(value,kind):
    if not isinstance(value,str) or not value:
        return {"status":"MISSING_PATH","kind":kind}
    p=Path(value)
    if not p.is_absolute() or p.is_symlink():
        return {"status":"INVALID_PATH","kind":kind}
    if not p.exists():
        return {"status":"ABSENT","kind":kind}
    if kind=="directory" and not p.is_dir():
        return {"status":"WRONG_TYPE","kind":kind}
    if kind=="file" and not p.is_file():
        return {"status":"WRONG_TYPE","kind":kind}
    if kind=="file":
        if p.stat().st_size==0 or p.stat().st_size>25000000:
            return {"status":"INVALID_SIZE","kind":kind}
        return {"status":"PRESENT","kind":kind,
                "sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
    return {"status":"PRESENT","kind":kind}
def audit(cfg):
    if type(cfg)!=dict or cfg.get("schemaId")!=SCHEMA:
        fail("CONFIG_SCHEMA")
    if cfg.get("sessionDate")!=DATE:
        fail("SESSION_MUST_BE_2026_10_26")
    if cfg.get("productionReady") is not False or cfg.get("orderTransmission") is not False:
        fail("ORDER_MUST_BE_OFF")
    if ("previousContext" in cfg)==("previousCaptureFiles" in cfg):
        fail("PREVIOUS_SOURCE_CHOICE")
    results={}
    for key in REQUIRED:
        results[key]=check_path(cfg.get(key),"file" if key=="datedMaster" else "directory")
    for key in OPTIONAL:
        if key in cfg:
            results[key]=check_path(cfg[key],"file" if key=="pinsFile" else "directory")
    if "previousContext" in cfg:
        results["previousContext"]=check_path(cfg["previousContext"],"file")
    else:
        values=cfg["previousCaptureFiles"]
        if type(values)!=list or not 1<=len(values)<=8:
            fail("PREVIOUS_CAPTURE_LIST")
        for i,v in enumerate(values):
            results[f"previousCaptureFiles[{i}]"]=check_path(v,"file")
    if results["datedMaster"]["status"]=="PRESENT":
        try:
            m=json.loads(Path(cfg["datedMaster"]).read_text(encoding="utf-8-sig"))
            if m.get("schemaId")!="ARK_NO11_DATED_MASTER_RECEIPT_V1" or m.get("sessionDate")!=DATE:
                results["datedMaster"]["status"]="WRONG_MASTER_DATE_OR_SCHEMA"
            elif not isinstance(m.get("rows"),list) or not m["rows"]:
                results["datedMaster"]["status"]="NO_MASTER_ROWS"
        except (ValueError,UnicodeError,OSError):
            results["datedMaster"]["status"]="INVALID_JSON"
    if "previousContext" in cfg and results["previousContext"]["status"]=="PRESENT":
        try:
            m=json.loads(Path(cfg["previousContext"]).read_text(encoding="utf-8-sig"))
            if m.get("schemaId")!="ARK_NO11_RSS_P1_PREVIOUS_CONTEXT_V1" or m.get("sessionDate")!=DATE or m.get("previousSession")!="2026-10-23":
                results["previousContext"]["status"]="WRONG_PREVIOUS_SESSION_OR_SCHEMA"
        except (ValueError,UnicodeError,OSError):
            results["previousContext"]["status"]="INVALID_JSON"
    missing=[key for key,val in results.items() if val["status"]!="PRESENT"]
    return {"schemaId":"ARK_NO11_26_PRECHECK_RESULT_V1",
            "targetSession":DATE,"files":results,"blockers":missing,
            "filePresenceOnly":True,"jpxMarketHoursTested":False,
            "frozenModelsExecuted":False,"excelStarted":False,
            "shadowReady":False,"productionReady":False,
            "orderTransmission":False}
def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--config",type=Path,required=True)
    a=p.parse_args(argv)
    if not a.config.is_file() or a.config.stat().st_size>100000:
        fail("CONFIG_NOT_FOUND_OR_TOO_LARGE")
    cfg=json.loads(a.config.read_text(encoding="utf-8-sig"))
    report=audit(cfg)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    print(PREFIX+("FILES_PRESENT_NOT_VALIDATED" if not report["blockers"] else "BLOCKED_INPUTS"))
    print("ORDER_TRANSMISSION=False")
    return 0 if not report["blockers"] else 2
if __name__=="__main__":
    try:sys.exit(main())
    except (ValueError,OSError,UnicodeError) as exc:
        msg=str(exc)
        print(msg if re.fullmatch(r"NO11_26_PRECHECK_[A-Z0-9_]+",msg)
              else PREFIX+"INVALID_PRIVATE_INPUT",file=sys.stderr)
        sys.exit(2)
