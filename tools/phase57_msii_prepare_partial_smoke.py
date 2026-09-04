#!/usr/bin/env python3
"""Explicit smoke-only bootstrap.

Normal late starts should use phase57_msii_prepare_mid_session.py so collection begins
at the next JPX 5-minute bucket after the operator starts Lane M.
"""
import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
FALSE_SAFETY_KEYS = (
    "executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed",
    "liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed",
)
SAFETY = {
    "mode":"LANE_M_DYNAMIC_WATCHLIST_WATCH","executionAllowed":False,"brokerWriteAllowed":False,
    "excelOrderWriteAllowed":False,"excelMarketDataQueryWriteAllowed":True,"rssOrderFunctionAllowed":False,
    "liveTradingAllowed":False,"paperTradingAllowed":False,"automaticPromotionAllowed":False,
    "productionUpdateAllowed":False,"transmitted":False,
}

def expected_buckets(session_date: str):
    base=datetime.strptime(session_date,"%Y-%m-%d").replace(tzinfo=JST); out=[]
    for sh,sm,eh,em in ((9,5,11,30),(12,35,15,30)):
        at=base.replace(hour=sh,minute=sm,second=0,microsecond=0); end=base.replace(hour=eh,minute=em,second=0,microsecond=0)
        while at<=end:
            out.append(at.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")); at+=timedelta(minutes=5)
    return out

def floor_five_minutes(dt: datetime):
    dt=dt.astimezone(timezone.utc); return dt.replace(minute=dt.minute-(dt.minute%5),second=0,microsecond=0)

def read_observed_at(path: Path):
    payload=json.loads(path.read_text(encoding="utf-8")); value=payload.get("meta",{}).get("observedAt")
    if not value: raise ValueError(f"raw observedAt missing: {path}")
    parsed=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if parsed.tzinfo is None: raise ValueError(f"raw observedAt must be timezone-aware: {path}")
    return parsed

def atomic_write_json(path: Path,payload):
    path.parent.mkdir(parents=True,exist_ok=True); fd,temp_name=tempfile.mkstemp(prefix=path.name+".tmp-",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as handle:
            json.dump(payload,handle,ensure_ascii=False,indent=2); handle.write("\n")
        os.replace(temp_name,path)
    except Exception:
        try: os.unlink(temp_name)
        except FileNotFoundError: pass
        raise

def prepare_partial_smoke(raw_dir: Path,state_file: Path,session_date: str):
    for key in FALSE_SAFETY_KEYS:
        if SAFETY[key] is not False: raise RuntimeError(f"unsafe flag: {key}")
    if SAFETY["excelMarketDataQueryWriteAllowed"] is not True or SAFETY["transmitted"] is not False: raise RuntimeError("unsafe partial-smoke safety scope")
    raw_files=sorted(raw_dir.glob("*.json"))
    if not raw_files: raise ValueError(f"no raw JSON files found: {raw_dir}")
    metas=sorted((read_observed_at(path),path) for path in raw_files); first_observed,first_path=metas[0]
    first_bucket=floor_five_minutes(first_observed).isoformat(timespec="milliseconds").replace("+00:00","Z")
    schedule=expected_buckets(session_date)
    if first_bucket not in schedule: raise ValueError(f"first raw bucket is outside JPX decision schedule: {first_bucket}")
    start_index=schedule.index(first_bucket)
    if state_file.exists():
        state=json.loads(state_file.read_text(encoding="utf-8"))
        if state.get("sessionDate")!=session_date: raise ValueError("dynamic watchlist state sessionDate mismatch")
        pristine=state.get("lastObservedAt") is None and state.get("lastBucketAt") is None and int(state.get("processedBucketCount",0))==0 and not state.get("processedRaw",[])
        if not pristine: raise ValueError("refusing to bootstrap a non-pristine dynamic watchlist state")
    else:
        state={"schemaVersion":2,"sessionDate":session_date,"lastObservedAt":None,"lastBucketAt":None,"processedBucketCount":0,"priorV2Selections":[],"recentV1Selections":[],"processedRaw":[]}
    if start_index==0: raise ValueError("first raw bucket is the normal 09:05 start; partial smoke is unnecessary")
    state.update({"processedBucketCount":start_index,"sessionEligibility":"PARTIAL_SMOKE","notEligibleForProspectiveScore":True,"partialStartBucketAt":first_bucket,"partialStartObservedAt":first_observed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z"),"partialStartRaw":first_path.name,"missingOpeningBucketCount":start_index,"bootstrapReason":"MID_SESSION_START_SMOKE_ONLY","futureOutcomeUsed":False,"safety":SAFETY})
    atomic_write_json(state_file,state); return state

def main():
    parser=argparse.ArgumentParser(description="Smoke-only bootstrap from the earliest available raw bucket; use phase57_msii_prepare_mid_session.py for normal late starts.")
    parser.add_argument("--raw-dir",required=True); parser.add_argument("--state",required=True); parser.add_argument("--session-date",required=True)
    args=parser.parse_args(); state=prepare_partial_smoke(Path(args.raw_dir),Path(args.state),args.session_date)
    print(json.dumps({"status":"PHASE57_MSII_PARTIAL_SMOKE_READY","sessionDate":state["sessionDate"],"partialStartBucketAt":state["partialStartBucketAt"],"missingOpeningBucketCount":state["missingOpeningBucketCount"],"sessionEligibility":state["sessionEligibility"],"notEligibleForProspectiveScore":state["notEligibleForProspectiveScore"],"futureOutcomeUsed":state["futureOutcomeUsed"],"safety":state["safety"]},ensure_ascii=False))

if __name__=="__main__": main()
