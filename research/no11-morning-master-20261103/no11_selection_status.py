#!/usr/bin/env python3
"""Read-only weekly-source and next-session selection status for WHITE OneClick.

Only immutable date-scoped private evidence is inspected. A launch receipt,
UI status, after-close attempt, or unverified JSON never counts as completion.
The weekly label distinguishes actual Friday full-RSS sweep vs legacy Monday
seed / unverified provisional source. This does not authorize any orders.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

JST = timezone(timedelta(hours=9))
SYMBOL = re.compile(r"^[0-9A-Z]{4}\.T$")
DAY = re.compile(r"^20\d\d-\d\d-\d\d$")
SHA = re.compile(r"^[0-9a-f]{64}$")
POINTER_SCHEMA = "ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1"
HANDOFF_SCHEMA = "ARK_NO11_MORNING_MASTER_HANDOFF_V1"
WEEKLY_RSS_SCHEMA = "ARK_NO11_RSS_DAILY_CENSUS_PLAN_V1"
WEEKLY_YAHOO_SCHEMA = "ARK_NO11_YAHOO_WEEKLY_SOURCE_PLAN_V1"
REFRESH_SCHEMA = "ARK_NO11_WEEKLY_G1_DAILY_REFRESH_PLAN_V1"
MASK_SCHEMA = "ARK_NO11_DAILY_OBSERVED_PASS_ONLY_SHADOW_V1"
CHART_SCHEMA = "ARK_NO11_G1_PASS_CHART50_SHADOW_CAPACITY_V1"


def require(test: bool, reason: str) -> None:
    if not test:
        raise ValueError(reason)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def symbols(values, lower=1, upper=500):
    return (type(values) is list and lower <= len(values) <= upper
            and len(set(values)) == len(values)
            and all(type(v) is str and SYMBOL.fullmatch(v) for v in values))


def stored(path: Path, *, root: Path | None = None, max_size=16_000_000):
    require(path.is_absolute() and path.is_file() and not path.is_symlink(),
            "MISSING_OR_LINKED_SOURCE")
    if root is not None:
        require(path.resolve().is_relative_to(root.resolve()), "SOURCE_OUTSIDE_ROOT")
    require(0 < path.stat().st_size <= max_size, "SOURCE_SIZE")
    data = path.read_bytes()
    require(len(data) <= max_size, "SOURCE_SIZE")
    return data


def data(path: Path, *, root: Path | None = None, max_size=16_000_000):
    raw = stored(path, root=root, max_size=max_size)
    try:
        obj = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, ValueError) as e:
        raise ValueError("INVALID_JSON") from e
    require(type(obj) is dict, "JSON_OBJECT")
    return obj, raw


def evidence(path: Path, digest: str, *, root: Path | None = None, size=64_000_000):
    require(type(digest) is str and SHA.fullmatch(digest), "SOURCE_HASH_FORMAT")
    require(path.is_absolute() and path.is_file() and not path.is_symlink(),
            "PINNED_SOURCE_MISSING")
    if root is not None:
        require(path.resolve().is_relative_to(root.resolve()), "PINNED_SOURCE_OUTSIDE_ROOT")
    require(0 < path.stat().st_size <= size, "PINNED_SOURCE_SIZE")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(262144), b""):
            h.update(block)
    require(h.hexdigest() == digest, "PINNED_SOURCE_CHANGED")


def valid_day(s):
    require(type(s) is str and DAY.fullmatch(s), "DAY_FORMAT")
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise ValueError("DAY_INVALID") from e


def blank():
    return {
        "schemaId": "ARK_NO11_SELECTION_DISPLAY_V1",
        "weekly": {"state": "UNKNOWN", "asOf": None, "pool": None},
        "daily": {"state": "NOT_READY", "target": None, "count": None},
        "orderTransmission": False,
        "readOnly": True,
    }


def choose_target(root: Path, now: datetime):
    folder = root / "prepared-days"
    if not folder.is_dir() or folder.is_symlink():
        return None, None
    today = now.date()
    evening = now.hour >= 18
    candidates = []
    for p in folder.iterdir():
        if not p.is_file() or p.is_symlink() or not re.fullmatch(r"20\d{2}-\d{2}-\d{2}\.json",p.name):
            continue
        try:
            day = valid_day(p.stem)
        except ValueError:
            continue
        if 0 <= (day - today).days <= 8 and (not evening or day > today):
            candidates.append((day, p))
    if candidates:
        selected = sorted(candidates)[0]
        return selected[1], selected[0]
    return None, None


def validate_pointer(path: Path, root: Path):
    pointer, _ = data(path, root=root, max_size=500_000)
    target = valid_day(path.stem)
    require(pointer.get("schemaId") == POINTER_SCHEMA and
            pointer.get("sessionDate") == path.stem and
            pointer.get("orderTransmission") is False and
            pointer.get("productionReady") is False and
            pointer.get("humanReviewClaimed") is False and
            pointer.get("manualPricesRequired") is False and
            pointer.get("manualEvidenceRequired") is False,
            "POINTER_SCHEMA")
    previous = valid_day(pointer.get("previousSession"))
    require(previous < target, "POINTER_DATES")
    selected = pointer.get("selectedSymbols")
    require(symbols(selected, upper=47) and
            pointer.get("selectedCount") == len(selected),
            "POINTER_SELECTED")
    hand_path = Path(pointer.get("handoff", ""))
    hand, hb = data(hand_path, root=root, max_size=4_000_000)
    require(hand_path.name == "morning-handoff-" + sha(hb) + ".json"
            and sha(hb) == pointer.get("handoffSha256")
            and hand.get("schemaId") == HANDOFF_SCHEMA
            and hand.get("sessionDate") == path.stem
            and hand.get("previousSession") == pointer["previousSession"]
            and hand.get("selectedSymbols") == selected
            and hand.get("reviewStatus") == "NOT_REVIEWED"
            and hand.get("productionReady") is False
            and hand.get("orderTransmission") is False
            and hand.get("datedMasterCreated") is False,
            "HANDOFF_INVALID")
    spec, pins = hand.get("spec"), hand.get("sourcePins")
    require(type(spec) is dict and type(pins) is dict and
            set(pins) == {"chartReceipt", "passMask", "previousStage"},
            "HANDOFF_PINS")
    # Never make the UI claim that 45/45 archives are ready when pin sources
    # were overwritten or the daily scope is mismatched.
    for key in ("chartReceipt","passMask","previousStage"):
        evidence(Path(spec[key]), pins[key])
    chart,_ = data(Path(spec["chartReceipt"]), max_size=4_000_000)
    mask,_ = data(Path(spec["passMask"]), max_size=4_000_000)
    ch = chart.get("chartPlan")
    require(type(ch) is dict and ch.get("schemaId") == CHART_SCHEMA and
            ch.get("sessionDate") == path.stem and
            ch.get("asOfSession") == pointer["previousSession"] and
            ch.get("selectorInputSymbols") == selected and
            ch.get("orderTransmission") is False and
            ch.get("productionReady") is False and
            mask.get("schemaId") == MASK_SCHEMA and
            mask.get("asOfSession") == pointer["previousSession"] and
            mask.get("orderTransmission") is False,
            "DAILY_PLAN_SCOPE")
    return pointer, hand, ch, mask


def weekly_info(hand, chart, mask, previous):
    spec=hand["spec"]
    weekly_path=Path(spec.get("weeklySourceRun", "")) / "plan.json"
    refresh_path=Path(spec["chartReceipt"]).parent / "plan.json"
    weekly,_=data(weekly_path, max_size=4_000_000)
    refresh,_=data(refresh_path, max_size=4_000_000)
    source = refresh.get("weeklySource")
    # These immutable JSON plans are authored by JavaScript via
    # SHA256(JSON.stringify(body)) and a planId field. Recheck the actual
    # digest, not merely the recorded cross-link between two mutable files.
    for plan in (weekly, refresh):
        planid=plan.get("planId")
        require(type(planid) is str and SHA.fullmatch(planid), "PLAN_ID_FORMAT")
        body={k:v for k,v in plan.items() if k!="planId"}
        require(sha(json.dumps(body,separators=(",",":"),ensure_ascii=False).encode())==planid,
                "PLAN_HASH_MISMATCH")
    # Friday's genuine 4,328-symbol RSS sweep is also the daily G1 source.
    # Unlike Mon-Thu, it intentionally has NO separate weekly-refresh plan.
    # Do not mislabel a complete Friday-to-Monday handoff UNVERIFIED.
    if weekly_path == refresh_path:
        asof = valid_day(weekly.get("asOfSession"))
        pass_symbols = mask.get("observedPassSymbols")
        require(weekly.get("schemaId") == WEEKLY_RSS_SCHEMA
                and asof == valid_day(previous) and asof.weekday() == 4
                and weekly.get("productionReady") is False
                and weekly.get("orderTransmission") is False
                and type(weekly.get("symbols")) is list
                and len(weekly["symbols"]) == 4328
                and chart.get("sourcePlanId") == weekly["planId"]
                and mask.get("planId") == weekly["planId"]
                and symbols(pass_symbols)
                and mask.get("observedPassCount") == len(pass_symbols),
                "FRIDAY_FULL_WEEKLY_SOURCE_NOT_LINKED")
        return {"state": "DONE", "asOf": str(asof), "pool": len(pass_symbols)}
    require(type(source) is dict and
            weekly.get("schemaId") in (WEEKLY_RSS_SCHEMA, WEEKLY_YAHOO_SCHEMA)
            and type(weekly.get("planId")) is str and SHA.fullmatch(weekly["planId"])
            and type(weekly.get("symbols")) is list and len(weekly["symbols"]) == 4328
            and valid_day(weekly.get("asOfSession")) <= valid_day(previous)
            and refresh.get("schemaId") == WEEKLY_RSS_SCHEMA
            and refresh.get("refreshSchemaId") == REFRESH_SCHEMA
            and refresh.get("asOfSession") == previous
            and refresh.get("orderTransmission") is False
            and refresh.get("productionReady") is False
            and refresh.get("planId") == chart.get("sourcePlanId")
            and source.get("originalPlanId") == weekly["planId"]
            and source.get("asOfSession") == weekly["asOfSession"]
            and source.get("originalFullUniverseCount") == len(weekly["symbols"])
            and source.get("observedPassCount") == len(refresh.get("symbols", []))
            and 0 < source["observedPassCount"] <= 500
            and source.get("observedPassSymbolsSha256") ==
                sha(json.dumps(refresh["symbols"],separators=(",",":"),ensure_ascii=False).encode())
            and refresh.get("sourceSymbolsSha256") == source["observedPassSymbolsSha256"]
            and mask.get("planId") == refresh.get("planId"),
            "WEEKLY_SOURCE_NOT_LINKED")
    asof = valid_day(weekly["asOfSession"])
    # A Monday warm-start and a provisional Yahoo weekly source are not a
    # confirmed full Friday RSS scan. Make the distinction visible.
    if weekly["schemaId"] == WEEKLY_YAHOO_SCHEMA:
        state = "PROVISIONAL"
    elif asof.weekday() != 4:
        state = "CARRIED"
    elif (valid_day(previous) - asof).days > 8:
        state = "CARRIED"
    else:
        state = "DONE"
    return {"state":state,"asOf":str(asof),
            "pool":source["observedPassCount"]}


def inspect(binding_file: Path, *, at: datetime | None = None):
    result=blank()
    try:
        now = at or datetime.now(JST)
        require(now.utcoffset() == timedelta(hours=9), "JST_REQUIRED")
        binding,_=data(binding_file, max_size=1_000_000)
        require(binding.get("schemaId") == "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1" and
                binding.get("orderTransmission") is False,
                "BINDING_UNSAFE")
        root=Path(binding.get("dailyCycleRoot",""))
        require(root.is_absolute() and root.is_dir() and not root.is_symlink(),
                "DAILY_ROOT_MISSING")
        target_file,target=choose_target(root, now)
        if target_file is None:
            return result
        result["daily"]["target"] = str(target)
        try:
            ptr, hand, chart, mask=validate_pointer(target_file,root)
        except (OSError, ValueError, TypeError, KeyError):
            result["daily"]["state"] = "INVALID"
            return result
        result["daily"].update(state="READY",count=ptr["selectedCount"])
        try:
            result["weekly"]=weekly_info(hand,chart,mask,ptr["previousSession"])
        except (OSError, ValueError, TypeError, KeyError):
            result["weekly"]["state"]="UNVERIFIED"
        return result
    except (OSError, ValueError, TypeError, KeyError):
        result["weekly"]["state"]="UNVERIFIED"
        result["daily"]["state"]="UNVERIFIED"
        return result


def display(summary):
    w,d=summary["weekly"],summary["daily"]
    wdate=w.get("asOf")
    ddate=d.get("target")
    wk=("WEEKLY  "+w["state"]+
        (" "+wdate[5:].replace("-","/") if wdate else "")+
        (" ("+str(w["pool"])+")" if w.get("pool") is not None else ""))
    dy=("DAILY  "+d["state"]+
        (" "+ddate[5:].replace("-","/") if ddate else "")+
        (" ("+str(d["count"])+")" if d.get("count") is not None else ""))
    return wk+"   |   "+dy


def main(argv=None):
    a=argparse.ArgumentParser()
    a.add_argument("--binding",type=Path,required=True)
    a.add_argument("--line",action="store_true")
    args=a.parse_args(argv)
    result=inspect(args.binding)
    if args.line:
        print("NO11_SELECTION_UI="+display(result))
    else:
        print(json.dumps(result,separators=(",",":"),sort_keys=True))
    return 0


if __name__=="__main__":
    sys.exit(main())
