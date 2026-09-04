#!/usr/bin/env python3
import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
FALSE_KEYS = (
    "executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed",
    "liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed",
)
WATCHLIST_SAFETY = {
    "mode":"LANE_M_DYNAMIC_WATCHLIST_WATCH","executionAllowed":False,"brokerWriteAllowed":False,
    "excelOrderWriteAllowed":False,"excelMarketDataQueryWriteAllowed":True,"rssOrderFunctionAllowed":False,
    "liveTradingAllowed":False,"paperTradingAllowed":False,"automaticPromotionAllowed":False,
    "productionUpdateAllowed":False,"transmitted":False,
}
SESSION_SAFETY = {
    "mode":"LANE_M_FULL_SESSION_WATCHER_READ_ONLY","executionAllowed":False,"brokerWriteAllowed":False,
    "excelOrderWriteAllowed":False,"rssOrderFunctionAllowed":False,"liveTradingAllowed":False,
    "paperTradingAllowed":False,"automaticPromotionAllowed":False,"productionUpdateAllowed":False,
    "transmitted":False,
}

def schedule(session_date):
    base=datetime.strptime(session_date,"%Y-%m-%d").replace(tzinfo=JST)
    out=[]
    for sh,sm,eh,em in ((9,5,11,30),(12,35,15,30)):
        at=base.replace(hour=sh,minute=sm,second=0,microsecond=0); end=base.replace(hour=eh,minute=em,second=0,microsecond=0)
        while at<=end:
            out.append(at.astimezone(timezone.utc)); at+=timedelta(minutes=5)
    return out

def parse_iso(value):
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None: raise ValueError("start-at must be timezone-aware")
    return dt.astimezone(timezone.utc)

def atomic_json(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+".tmp-",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as h:
            json.dump(payload,h,ensure_ascii=False,indent=2); h.write("\n")
        os.replace(tmp,path)
    except Exception:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
        raise

def raw_bucket(path):
    p=json.loads(path.read_text(encoding="utf-8")); v=p.get("meta",{}).get("observedAt")
    if not v: raise ValueError(f"raw observedAt missing: {path}")
    dt=parse_iso(v); minute=dt.minute-(dt.minute%5)
    return dt.replace(minute=minute,second=0,microsecond=0)

def pristine(path, session_date):
    if not path.exists(): return True
    s=json.loads(path.read_text(encoding="utf-8"))
    return s.get("sessionDate")==session_date and s.get("lastObservedAt") is None and s.get("lastBucketAt") is None and int(s.get("processedBucketCount",0))==0 and not s.get("processedRaw",[])

def prepare(raw_dir,state_file,lane_m_state_file,session_date,start_at):
    for safety in (WATCHLIST_SAFETY,SESSION_SAFETY):
        for key in FALSE_KEYS:
            if safety[key] is not False: raise RuntimeError(f"unsafe flag {key}")
        if safety.get("transmitted") is not False: raise RuntimeError("transmitted must remain false")
    if not pristine(state_file,session_date):
        raise ValueError("refusing to mid-session bootstrap a non-pristine watchlist state")
    points=schedule(session_date); requested=parse_iso(start_at)
    candidates=[(i,p) for i,p in enumerate(points) if p>=requested]
    if not candidates: raise ValueError("no remaining JPX decision bucket for this session")
    start_index,start_bucket=candidates[0]
    start_iso=start_bucket.isoformat(timespec="milliseconds").replace("+00:00","Z")
    older=[]
    for path in sorted(raw_dir.glob("*.json")):
        if raw_bucket(path)<start_bucket: older.append(path.name)
    watch={
        "schemaVersion":2,"sessionDate":session_date,"lastObservedAt":None,"lastBucketAt":None,
        "processedBucketCount":start_index,"priorV2Selections":[],"recentV1Selections":[],"processedRaw":older,
        "sessionEligibility":"MID_SESSION_CAUSAL","notEligibleForFullFreshScore":True,
        "eligibleForMidSessionScore":True,"stateInitialization":"COLD_START",
        "collectionRequestedAt":requested.isoformat(timespec="milliseconds").replace("+00:00","Z"),
        "collectionStartBucketAt":start_iso,"skippedOpeningBucketCount":start_index,
        "futureOutcomeUsed":False,"safety":WATCHLIST_SAFETY,
    }
    # Seed Lane M so envelopes before collection start are ignored rather than converted into missing-evidence blocks.
    before=start_bucket-timedelta(milliseconds=1)
    lane={
        "schemaVersion":2,"version":"phase57-msii-full-session-r3-coverage","sessionDate":session_date,
        "lastDecisionAt":before.isoformat(timespec="milliseconds").replace("+00:00","Z"),
        "ledger":[],"processedEvidenceHashes":[],"blockedPoints":[],"committedPoints":[],
        "predeclaredStartAt":start_iso,"actualStartAt":start_iso,"missingCaptureCount":0,
        "sessionQuality":"MID_SESSION_CAUSAL_COLD_START","collectionMode":"MID_SESSION_CAUSAL",
        "notEligibleForFullFreshScore":True,"eligibleForMidSessionScore":True,
        "stateInitialization":"COLD_START","futureOutcomeUsed":False,"safety":SESSION_SAFETY,
    }
    atomic_json(state_file,watch); atomic_json(lane_m_state_file,lane)
    return watch

def main():
    ap=argparse.ArgumentParser(description="Prepare a standard causal Lane M mid-session start at the next JPX 5-minute decision bucket.")
    ap.add_argument("--raw-dir",required=True); ap.add_argument("--state",required=True)
    ap.add_argument("--lane-m-state",required=True); ap.add_argument("--session-date",required=True); ap.add_argument("--start-at",required=True)
    a=ap.parse_args(); s=prepare(Path(a.raw_dir),Path(a.state),Path(a.lane_m_state),a.session_date,a.start_at)
    print(json.dumps({"status":"PHASE57_MSII_MID_SESSION_READY","sessionDate":s["sessionDate"],"collectionStartBucketAt":s["collectionStartBucketAt"],"skippedOpeningBucketCount":s["skippedOpeningBucketCount"],"sessionEligibility":s["sessionEligibility"],"eligibleForMidSessionScore":s["eligibleForMidSessionScore"],"notEligibleForFullFreshScore":s["notEligibleForFullFreshScore"],"stateInitialization":s["stateInitialization"],"futureOutcomeUsed":False,"safety":s["safety"]},ensure_ascii=False))

if __name__=="__main__": main()
