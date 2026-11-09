#!/usr/bin/env python3
"""Only fix the DATA parser for a genuine Friday RSS recovery followed by weekday.

The old per-night parser presumed one archive stage and one chart receipt in
each log. The real 11/06->11/09 capture has two intentional stages. This parser
extracts the FINAL weekday receipt set, demands an attested recovery boundary,
and never suppresses missing 1M bars, trading evidence, or hash validation.

This file is transformation logic ONLY. It must NOT be applied to the installed
pinned module in place. Existing captured log and publishing checkpoint remain.
"""
from __future__ import annotations

import re

MARK="ARK_NO11_PROVEN_TWO_SESSION_CAPTURE_LOG_V1"

PARSE_SOURCE=r'''def parse_nightly(raw):
    # ARK_NO11_PROVEN_TWO_SESSION_CAPTURE_LOG_V1
    need(type(raw) is bytes and 0 < len(raw) < 20_000_000, "NIGHTLY_LOG_SIZE")
    lines=[l.strip() for l in decode_nightly_log(raw).splitlines() if l.strip()]
    success=[l.split("=",1)[1] for l in lines if
             l.startswith("NO11_WEEKLY_NIGHTLY_STAGE=")]
    need(len(success)==1 and success[0] in SUCCESS,"NIGHTLY_NOT_COMPLETE")
    need("ORDER_TRANSMISSION=False" in lines,"NIGHTLY_ORDER_MODE")
    result={
        "sessionDate":one(lines,"NO11_WEEKLY_NIGHTLY_NEXT_SESSION="),
        "previousSession":one(lines,"NO11_WEEKLY_NIGHTLY_ASOF="),
        "nightlyMode":success[0]
    }
    need(re.fullmatch(r"20\d\d-\d\d-\d\d",result["sessionDate"]) is not None and
         re.fullmatch(r"20\d\d-\d\d-\d\d",result["previousSession"]) is not None and
         date.fromisoformat(result["previousSession"])<date.fromisoformat(result["sessionDate"]),
         "NIGHTLY_DATES")
    def exact(prefix,start=0,end=None):
        group=lines[start:end]
        return [v[len(prefix):].strip() for v in group if v.startswith(prefix)]
    def one_at(prefix,start=0,end=None):
        found=exact(prefix,start,end)
        need(len(found)==1 and bool(found[0]),"NIGHTLY_LOG_MARKER_"+re.sub(r"[^A-Z0-9_]","_",prefix))
        return found[0]
    if result["nightlyMode"] == "FRIDAY_FULL_UNIVERSE_AND_PREVIOUS_COMPLETE":
        # Standard Friday still admits exactly one source of each type.
        result["stage"]=one_at("NO11_PREVIOUS_ARCHIVE_STAGE=")
        result["capture"]=one_at("NO11_PREVIOUS_CAPTURE_DIR=")
        result["chart"]=one_at("NO11_NIGHTLY_CHART50=")
        result["mask"]=one_at("NO11_NIGHTLY_MASK=")
        result["weekly"]=one_at("NO11_NIGHTLY_DAILY_RUN=")
        result["run"]=result["weekly"]
        need(not exact("NO11_WEEKLY_NIGHTLY_CURRENT_CHART50=") and
             not exact("NO11_WEEKLY_NIGHTLY_CURRENT_MASK=") and
             not exact("NO11_WEEKLY_NIGHTLY_REFRESH_RUN="),
             "FRIDAY_WEEKDAY_MIXED")
        return result
    need(result["nightlyMode"] in (
         "CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE",
         "YAHOO_WEEKLY_AND_RSS_429_G1_PREVIOUS_COMPLETE"),"UNKNOWN_SUCCESS_MODE")
    starts=[(i,line) for i,line in enumerate(lines) if
            line.startswith("NO11_WEEKLY_RECOVER_MISSING_FRIDAY=REAL_RSS_FULL_4328|ASOF_")]
    ends=[(i,line) for i,line in enumerate(lines) if
          line.startswith("NO11_WEEKLY_RECOVER_MISSING_FRIDAY=D100_AND_PREVIOUS_DONE|ASOF_")]
    if starts or ends:
        need(len(starts)==len(ends)==1 and starts[0][0]<ends[0][0],
             "FRIDAY_RECOVERY_BOUNDARY")
        friday=starts[0][1].split("|ASOF_",1)[1]
        need(friday==ends[0][1].split("|ASOF_",1)[1] and
             re.fullmatch(r"20\d\d-\d\d-\d\d",friday) is not None and
             date.fromisoformat(friday).weekday()==4 and
             date.fromisoformat(friday)<date.fromisoformat(result["previousSession"]) and
             1 <= (date.fromisoformat(result["previousSession"])-date.fromisoformat(friday)).days <= 6,
             "FRIDAY_RECOVERY_SOURCE_DATE")
        # One *Friday* preliminary archive, followed by one *Monday* archive.
        # Never pick last-of-many arbitrary duplicate log markers.
        start,done=starts[0][0],ends[0][0]
        need(len(exact("NO11_PREVIOUS_ARCHIVE_STAGE=",start,done))==1 and
             len(exact("NO11_PREVIOUS_CAPTURE_DIR=",start,done))==1 and
             len(exact("NO11_NIGHTLY_CHART50=",start,done))==1 and
             len(exact("NO11_NIGHTLY_MASK=",start,done))==1 and
             len(exact("NO11_NIGHTLY_DAILY_RUN=",start,done))==1 and
             len(exact("NO11_PREVIOUS_ARCHIVE_STAGE=",done+1))==1 and
             len(exact("NO11_PREVIOUS_CAPTURE_DIR=",done+1))==1 and
             not exact("NO11_NIGHTLY_CHART50=",done+1),
             "FRIDAY_RECOVERY_LOG_STRUCTURE")
        result["historicalFridayRecoveryAsOf"]=friday
        offset=done+1
    else:
        offset=0
        need(not exact("NO11_NIGHTLY_DAILY_RUN=") and
             not exact("NO11_NIGHTLY_CHART50=") and
             not exact("NO11_NIGHTLY_MASK="),
             "UNDECLARED_FRIDAY_SOURCE")
    # Pin the current weekday archive and chart, NEVER the prior-Friday ones.
    result["stage"]=one_at("NO11_PREVIOUS_ARCHIVE_STAGE=",offset)
    result["capture"]=one_at("NO11_PREVIOUS_CAPTURE_DIR=",offset)
    result["chart"]=one_at("NO11_WEEKLY_NIGHTLY_CURRENT_CHART50=",offset)
    result["mask"]=one_at("NO11_WEEKLY_NIGHTLY_CURRENT_MASK=",offset)
    result["weekly"]=one_at("NO11_WEEKLY_NIGHTLY_POOL_SOURCE=",offset)
    result["run"]=one_at("NO11_WEEKLY_NIGHTLY_REFRESH_RUN=",offset)
    return result

'''

def transform(raw):
    # Current installed base is the circuit-repaired daily_cycle.py.
    bom=raw.startswith(b"\xef\xbb\xbf")
    src=raw.decode("utf-8-sig")
    newline="\r\n" if "\r\n" in src else "\n"
    s=src.replace("\r\n","\n")
    if MARK in s:
        return raw
    a=s.find("def parse_nightly(raw):\n")
    b=s.find("def verified_sources(",a)
    if a<0 or b<0:
        raise ValueError("NO11_TWO_SESSION_PARSER_SOURCE_NOT_PINNED")
    old=s[a:b]
    if old.count("def alternatives(")!=1 or old.count("result={k:one(lines,p)")!=1 or (
         "decode_nightly_log(raw).splitlines()" not in old):
        raise ValueError("NO11_TWO_SESSION_PARSER_INSTALLED_SOURCE_CHANGED")
    output=s[:a]+PARSE_SOURCE+s[b:]
    compile(output,"no11_dual_session_parse.py","exec")
    return (b"\xef\xbb\xbf" if bom else b"")+output.replace("\n",newline).encode("utf-8")
