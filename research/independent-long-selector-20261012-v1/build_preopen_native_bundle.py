"""Build private preopen columnar inputs from caller-mounted immutable originals.

Does not load models or read Report labels for training. Required native market
families are preflighted together. Canary fixtures are explicitly SYNTHETIC.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import Counter
from datetime import timedelta
from pathlib import Path

from preopen_feature_store import write_feature_store
from preopen_history_features import FIN_COLUMNS, FLOW_COLUMNS, VALUATION_COLUMNS
from preopen_io import private_path, write_json, sha_file, utc_now, SAFE_FLAGS, verify_entry
from preopen_native_source import (NativeStore, parse_ohlcv, minute_row,
                                   MARKETS, validate_native_request, NULLS)
from preopen_selector import (CONTRACT, PreopenConfig, PreopenError, build_preopen_features,
                              digest, day, stamp, number)
from preopen_session_admission import exchange_sessions

REQUIRED_NATIVE_MARKET_DATASETS = {"DAILY","DATED_MASTER","MINUTE","TICK","FIN_SUMMARY",
                                  "VALUATION","EARNINGS_DATE","TOPIX","INVESTOR_TYPES"}
FIN_MAPPING = {"Sales":"fin_sales","OP":"fin_operating_profit","OdP":"fin_ordinary_profit",
               "NP":"fin_net_profit","TA":"fin_assets","Eq":"fin_equity",
               "CFO":"fin_operating_cash_flow","FSales":"fin_revenue_forecast",
               "FOdP":"fin_ordinary_profit_forecast","FDivAnn":"fin_dividend_forecast",
               "EPS":"valuation_eps","BPS":"valuation_bps","ROE":"valuation_roe"}
VALUATION_MAPPING = {"PER":"valuation_per","PBR":"valuation_pbr","MktCap":"valuation_market_cap_jpy",
                     "EPS":"valuation_eps","BPS":"valuation_bps","ROE":"valuation_roe",
                     "PSR":"valuation_psr","DY":"valuation_dividend_yield"}


def fact(store, row, field, *, scale=1):
    source = store.source(row["_sourceHash"])
    units = source.get("numericUnits",{}).get(field)
    value = row.get(field)
    contract = source.get("availabilityContract",{})
    if value in NULLS or not units or not contract.get("evidenceReference"):
        return None
    event_day = row.get(source.get("dateField","Date"))
    observed = (row["DiscDate"]+"T"+row["DiscTime"]+"+09:00" if source["dataset"] == "FIN_SUMMARY"
                else event_day+"T00:00:00+09:00")
    return {"value":number(value)*scale,"units":units,
            "sourceSha256":row["_sourceHash"],
            "publicationEvidence":contract["evidenceReference"],
            "observedAt":observed,
            "publishedAt":observed if source["dataset"] == "FIN_SUMMARY" else None,
            "effectiveSession":event_day,"capturedAt":source.get("capturedAt"),
            "historicalActualReceiveTimeVerified":False,
            "availableAt":store.available_at(row,source["dataset"])}


def known_records(store, dataset, session, code=None):
    cutoff = PreopenConfig().at(session)
    return [r for r in store.records(dataset,code=code)
            if stamp(store.available_at(r,dataset)) <= cutoff]


def optional_facts(store, session, code):
    native, external = {}, {}
    financial = known_records(store,"FIN_SUMMARY",session,code)
    if financial:
        latest = max(financial,key=lambda r:(r["DiscDate"],r["DiscTime"],r.get("DiscNo","")))
        for field in FIN_COLUMNS:
            f = fact(store,latest,field)
            if f:
                native["preopen_native_fin_"+field] = f
        for field, name in FIN_MAPPING.items():
            f = fact(store,latest,field)
            if f:
                external[name] = f
        sales = number(latest["Sales"]) if latest.get("Sales") not in NULLS else None
        if sales:
            for field, name in (("OP","fin_operating_margin"),("NP","fin_net_margin")):
                f = fact(store,latest,field)
                if f:
                    external[name] = {**f,"value":100*f["value"]/sales,"units":"PERCENT"}
        current_end = latest.get("CurPerEn","")
        if current_end:
            target_prefix = str(day(current_end).year-1)+current_end[4:]
            prior = [r for r in financial if r.get("CurPerEn") == target_prefix
                     and r.get("CurPerType") == latest.get("CurPerType")
                     and r.get("DocType") == latest.get("DocType")]
            if prior:
                earlier = max(prior,key=lambda r:(r["DiscDate"],r["DiscTime"],r.get("DiscNo","")))
                for col, name in (("Sales","fin_sales_yoy_pct"),("OP","fin_operating_profit_yoy_pct"),
                                  ("OdP","fin_ordinary_profit_yoy_pct"),("NP","fin_net_profit_yoy_pct"),
                                  ("EPS","fin_eps_growth_pct")):
                    f = fact(store,latest,col)
                    if f and earlier.get(col) not in NULLS and number(earlier[col]) != 0:
                        external[name] = {**f,"value":100*(f["value"]/number(earlier[col])-1),
                                          "units":"PERCENT"}
    valuation = known_records(store,"VALUATION",session,code)
    if valuation:
        latest = max(valuation,key=lambda r:r["Date"])
        for field in VALUATION_COLUMNS:
            f = fact(store,latest,field)
            if f:
                native["preopen_native_valuation_"+field] = f
        for field, name in VALUATION_MAPPING.items():
            f = fact(store,latest,field)
            if f:
                external[name] = f
    flows = known_records(store,"INVESTOR_TYPES",session)
    # Aggregate sections are not added to constituent sections (double counting).
    flows = [r for r in flows if r.get("Section") == store.request.get("flowSection")]
    if flows:
        latest = max(flows,key=lambda r:(r["PubDate"],r["EnDate"],r["StDate"]))
        for field in FLOW_COLUMNS:
            f = fact(store,latest,field,scale=1000)
            if f:
                native[f"preopen_native_flow_{field}_jpy"] = {**f,"units":"JPY"}
    topix = known_records(store,"TOPIX",session)
    topix.sort(key=lambda r:r["Date"])
    if topix:
        for n in (1,5,10,15,20,25,60):
            if len(topix) > n:
                f = {"value":100*(number(topix[-1]["C"])/number(topix[-n-1]["C"])-1),
                     "units":"PERCENT","sourceSha256":topix[-1]["_sourceHash"],
                     "publicationEvidence":store.source(topix[-1]["_sourceHash"])["availabilityContract"]["evidenceReference"],
                     "availableAt":store.available_at(topix[-1],"TOPIX")}
                external[f"topix_return_{n}d"] = f
        for n in (5,15,25):
            if len(topix) >= n:
                external[f"topix_sma{n}_distance"] = {
                    **external.get("topix_return_1d",{}),
                    "value":100*(number(topix[-1]["C"])/(sum(number(r["C"]) for r in topix[-n:])/n)-1),
                    "units":"PERCENT","sourceSha256":topix[-1]["_sourceHash"],
                    "publicationEvidence":store.source(topix[-1]["_sourceHash"])["availabilityContract"]["evidenceReference"],
                    "availableAt":store.available_at(topix[-1],"TOPIX")}
    earnings = known_records(store,"EARNINGS_DATE",session,code)
    if earnings:
        upcoming = [r for r in earnings if r["SchDate"] >= session]
        if upcoming:
            latest = min(upcoming,key=lambda r:r["SchDate"])
            f = {"value":(day(latest["SchDate"])-day(session)).days,"units":"CALENDAR_DAYS",
                 "sourceSha256":latest["_sourceHash"],
                 "publicationEvidence":store.source(latest["_sourceHash"])["availabilityContract"]["evidenceReference"],
                 "availableAt":store.available_at(latest,"EARNINGS_DATE")}
            external["days_until_known_earnings"] = f
            external["earnings_within_1d"] = {**f,"value":float(f["value"] <= 1),"units":"BOOLEAN"}
            external["earnings_within_5d"] = {**f,"value":float(f["value"] <= 5),"units":"BOOLEAN"}
    for name, f in list(external.items()):
        external[name] = {**f,"sourceId":f["sourceSha256"],"knownAt":f["availableAt"],
                          "observedAt":f.get("observedAt",f["availableAt"]),"pitVerified":True,
                          "liveRefreshContractVerified":False}
    return native, external


def previous_market_context(store, session, previous, masters, calendar):
    """Prior prices on the fixed as-of known peer universe; no outcome-day breadth."""
    import bisect
    ix = calendar.index(previous)
    periods = (1,5,15,25,60)
    old_maps = {n:{r["Code"]:r for r in store.records("DAILY",session=calendar[ix-n])}
                for n in periods if ix >= n}
    last = {r["Code"]:r for r in store.records("DAILY",session=previous)}
    peer = {m["Code"]:m for m in masters}
    window_dates = set(calendar[max(0,ix-60):ix+1])
    bad_dates = {}
    for date in sorted(window_dates):
        for r in store.records("DAILY",session=date):
            factor = r.get("AdjFactor")
            if (parse_ohlcv(r)["status"] != "TRADED" or factor in NULLS
                    or number(factor) != 1):
                bad_dates.setdefault(r["Code"],[]).append(date)
    returns = {n:{} for n in periods}
    for n, old in old_maps.items():
        for code in peer:
            a,b = last.get(code),old.get(code)
            if not a or not b or parse_ohlcv(a)["status"] != "TRADED" or parse_ohlcv(b)["status"] != "TRADED":
                continue
            boundary=calendar[ix-n]
            if any(boundary < d <= previous for d in bad_dates.get(code,[])):
                continue
            returns[n][code] = 100*(number(a["C"])/number(b["C"])-1)
    def ranks(values):
        ordered=sorted(values.values())
        n=len(ordered)
        return {code:100*(bisect.bisect_left(ordered,v)+bisect.bisect_right(ordered,v)-1)/2/max(1,n-1)
                for code,v in values.items()}
    rank_return = {n:ranks(values) for n,values in returns.items()}
    turnover = {c:number(last[c]["Va"]) for c in peer if c in last and last[c].get("Va") not in NULLS}
    rank_turnover=ranks(turnover)
    sector_returns={}
    for c,v in returns[1].items():
        sector_returns.setdefault(peer[c].get("S33"),{} )[c]=v
    result={}
    for code in peer:
        values={}
        for n in periods:
            if code in rank_return[n]:values[f"universe_rank_return_{n}d"]=rank_return[n][code]
        if code in rank_turnover:values["universe_rank_turnover"]=rank_turnover[code]
        market=list(returns[1].values())
        sector=list(sector_returns.get(peer[code].get("S33"),{}).values())
        for group,prefix in ((market,"market"),(sector,"sector")):
            if group:
                values[prefix+"_breadth_pct"]=100*sum(v>0 for v in group)/len(group)
                values[prefix+"_return_pct"]=sum(group)/len(group)
        if sector and market:
            values["sector_relative_strength_pct"]=sum(sector)/len(sector)-sum(market)/len(market)
        if code in last:
            source=store.source(last[code]["_sourceHash"])
            known=store.available_at(last[code],"DAILY")
            result[code]={name:{
                "value":v,"sourceId":last[code]["_sourceHash"],
                "sourceSha256":last[code]["_sourceHash"],
                "publicationEvidence":source["availabilityContract"]["evidenceReference"],
                "units":"PERCENT","knownAt":known,"observedAt":known,
                "pitVerified":True,"liveRefreshContractVerified":False}
                for name,v in values.items()}
    return result


def snapshot_rows(store, sessions, calendar, ineligible):
    previous = dict(zip(calendar[1:],calendar[:-1]))
    config = PreopenConfig()
    for session in sessions:
        if session not in previous:
            raise PreopenError("NO_ACTUAL_PREVIOUS_EXCHANGE_SESSION")
        prev = previous[session]
        masters = list(store.records("DATED_MASTER",session=session))
        if not masters:
            raise PreopenError("NO_DATED_MASTER_FOR_FIXED_SESSION")
        eligible_master = [r for r in masters if r.get("Mkt") in MARKETS
                           and r.get("ProdCat") == "011"
                           and re.fullmatch(r"[0-9A-Z]{4}0",r.get("Code",""))]
        universe_hash = digest([(r["Code"],r["Mkt"],r.get("S33"),r["ProdCat"])
                                for r in eligible_master])
        context = previous_market_context(store,session,prev,eligible_master,calendar)
        for master in eligible_master:
            code = master["Code"]
            history = list(store.records("DAILY",code=code,before=session))
            history = [r for r in history if r["Date"] in calendar]
            if not history or history[-1]["Date"] != prev:
                ineligible["MISSING_PRIOR_DAY_PRICE"] += 1
                continue
            if parse_ohlcv(history[-1])["status"] != "TRADED":
                ineligible["PRIOR_DAY_NULL_NO_PRICE"] += 1
                continue
            # Reset at gaps, Nulls and un-reconstructable split/rights boundaries.
            # No restated AdjC, no stitched mechanical 50% collapse, no fill.
            last_reset = -1
            calendar_ix = {d:i for i,d in enumerate(calendar)}
            for i, row in enumerate(history):
                if (parse_ohlcv(row)["status"] != "TRADED"
                        or (i and calendar_ix[row["Date"]] != calendar_ix[history[i-1]["Date"]]+1)):
                    last_reset = i
                factor = row.get("AdjFactor")
                if factor not in NULLS and number(factor) != 1:
                    last_reset = i-1
            history = history[last_reset+1:]
            if not history:
                ineligible["NO_CAUSAL_COMPARABLE_HISTORY"] += 1
                continue
            daily = [{**parse_ohlcv(r),"session":r["Date"],"availableAt":store.available_at(r,"DAILY")}
                     for r in history]
            if number(daily[-1]["close"]) <= config.minimum_prior_price_jpy:
                ineligible["PRIOR_PRICE_NOT_GREATER_THAN_75"] += 1
                continue
            minutes = [minute_row(r,store.available_at(r,"MINUTE"))
                       for r in store.records("MINUTE",code=code,session=prev)]
            # Features for completed prior minutes carry a historical publication
            # assumption. The close timestamp remains its real interval endpoint.
            ticks = store.prior_tick_events(prev,code,config.at(session).isoformat())
            native, external = optional_facts(store,session,code)
            external.update(context.get(code,{}))
            master_known = store.available_at(master,"DATED_MASTER")
            if stamp(master_known) > config.at(session):
                raise PreopenError("DATED_MASTER_NOT_AVAILABLE_AT_CUTOFF")
            lot = store.request.get("lotPolicyEvidence")
            if not lot:
                raise PreopenError("HISTORICAL_DOMESTIC_LOT_POLICY_EVIDENCE_REQUIRED")
            yield {"session":session,"previousSession":prev,"symbol":code,
                   "assetType":"JPX_CASH_EQUITY","master":{
                       "knownAt":master_known,"pitVerified":True,"eligible":True,
                       "segment":MARKETS[master["Mkt"]],"commonStock":True,"lotSize":100,
                       "sourceSha256":master["_sourceHash"],"lotPolicyEvidence":lot},
                   "historySessions":[r["session"] for r in daily],"dailyBars":daily,
                   "historyBasisVerifiedAsOf":True,"historyBasisKnownAt":daily[-1]["availableAt"],
                   "basisPolicy":"RAW_COMPARABLE_SUFFIX_RESET_AFTER_KNOWN_ACTION_OR_NULL_NO_ADJC",
                   "sourceManifestSha256":digest(store.request["sources"]),"universeHash":universe_hash,
                   "verifiedSourceHashes":[s["sha256"] for s in store.request["sources"]],
                   "previousMinuteBars":[b for b in minutes if b["kind"] == "CONTINUOUS_1M"],
                   "previousMinuteSessionBars":minutes,"previousMinuteCoverageVerified":True,
                   "previousTickEvents":ticks,"previousTickCoverageVerified":True,
                   "nativeFacts":native,"asofFacts":external,
                   "sampleKind":"SYNTHETIC" if store.request["mode"] == "SYNTHETIC" else "HISTORICAL",
                   "historicalAvailabilityStatus":"SCHEDULE_ASSUMED_NOT_ACTUAL_RECEIVE_OR_VERSION_RECEIPT",
                   "liveRefreshReady":False,"missingRequiredSources":(
                       ([] if minutes else ["MINUTE"]) + ([] if ticks else ["TICK"])),
                   "marketSegment":MARKETS[master["Mkt"]],"sector":master.get("S33"),
                   "sizeCategory":master.get("ScaleCat")}


def build_bundle(request, output):
    root = Path(request["privateRoot"]).resolve()
    output = private_path(output,root)
    if request.get("intendedUse") == "SOURCE_CANARY_ONLY":
        raise PreopenError("SOURCE_CANARY_CANNOT_BE_PROMOTED_TO_FULL_NATIVE_BUNDLE")
    if output.exists():
        raise PreopenError("REFUSE_OVERWRITE_NATIVE_BUNDLE")
    admission = validate_native_request(request,root)
    present = {s["dataset"] for s in request["sources"]}
    if request["mode"] == "AUTHORIZED_DEVELOPMENT" and not REQUIRED_NATIVE_MARKET_DATASETS <= present:
        raise PreopenError("KNOWN_NATIVE_SOURCE_FAMILIES_NOT_ALL_CONNECTED")
    # Preflight every mounted object together, before first numeric read.
    for s in request["sources"]:
        verify_entry(s,root)
    import gzip
    with gzip.open(verify_entry(request["calendar"],root),"rt",newline="") as stream:
        calendar = exchange_sessions(list(csv.DictReader(stream)))
    output.mkdir(parents=True,mode=0o700)
    write_json(output/"BUILD_STARTED.json",{"requestHash":digest(request),"startedAt":utc_now(),**SAFE_FLAGS})
    store = NativeStore(output/"native_shards",private_root=root,request=request)
    receipts = [store.ingest(s) for s in request["sources"]]
    inputs, excluded = {}, {}
    splits = admission["exactSplits"]
    for role in ("fit","calibration","report"):
        counts = Counter()
        features = (build_preopen_features(s) for s in snapshot_rows(store,splits[role],calendar,counts))
        inputs[role+"_snapshots"] = write_feature_store(
            features,output/role,private_root=root,input_manifest_hash=digest(request))
        excluded[role] = dict(counts)
        if role != "report":
            p = output/(role+"_labels.jsonl")
            with p.open("x",encoding="utf-8") as stream:
                for label in store.labels(splits[role]):
                    stream.write(json.dumps(label,ensure_ascii=False,allow_nan=False)+"\n")
            h, size = sha_file(p)
            inputs[role+"_labels"] = {"path":str(p),"sha256":h,"bytes":size}
    # Only a descriptor is written; actual Report price parsing occurs in the
    # runner's outcome stage. History-only reads for later Report snapshots are
    # present in the access receipts and must never be called wholly unopened.
    protected = request.get("protectedSessions",[])
    label_manifest = {"schema":"ARK_PREOPEN_NATIVE_LABEL_MANIFEST_V1",
                      "sessions":splits["report"],"protectedSessions":protected,
                      "sources":[s for s in request["sources"] if s["dataset"] == "DAILY"],
                      "sourceAdmissionHash":request["admission"]["sha256"]}
    inputs["report_labels"] = write_json(output/"REPORT_LABEL_SOURCE_DESCRIPTOR.json",label_manifest)
    inputs["report_labels"]["format"] = "ARK_PREOPEN_NATIVE_LABEL_MANIFEST_V1"
    plan = {"contract":CONTRACT,"mode":request["mode"],"splits":splits,
            "protectedSessions":request.get("protectedSessions",[]),
            "sourceManifestVerified":True,"existingSealsReconciled":True,
            "reuseBasisConfirmed":request["mode"] == "AUTHORIZED_DEVELOPMENT",
            "privateInputsOnly":True,"featureSourceCoverageVerified":True,
            "liveReadiness":"NOT_CERTIFIED",
            "sourceManifestSha256":digest(request["sources"]),
            "exposureLedgerSha256":request["admission"]["sha256"]}
    if request["mode"] == "AUTHORIZED_DEVELOPMENT":
        plan["currentReuseEvidence"] = request["currentReuseEvidence"]
        if request.get("reuseWorkId"):
            plan["reuseWorkId"] = request["reuseWorkId"]
    bundle = {"contract":CONTRACT,"privateRoot":str(root),"plan":plan,"inputs":inputs}
    write_json(output/"bundle.json",bundle)
    write_json(output/"NATIVE_ACCESS_LEDGER.json",{
        "schema":"ARK_PREOPEN_NATIVE_BUILD_ACCESS_V1","requestHash":digest(request),
        "originals":receipts,"exclusionsBeforeCurrentOutcome":excluded,
        "reportLabelEvaluationOpened":False,
        "reportEarlierSessionsMayBeReadAsCausalDMinus1History":True,**SAFE_FLAGS})
    store.close()
    return bundle


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--request",required=True)
    p.add_argument("--output",required=True)
    a = p.parse_args()
    request = json.loads(Path(a.request).read_text())
    b = build_bundle(request,Path(a.output))
    print(json.dumps({"status":"PRIVATE_NATIVE_BUNDLE_WRITTEN","mode":request["mode"],
                      "roleDays":{k:len(v) for k,v in b["plan"]["splits"].items()},
                      "marketFitN":0,"reportLabelEvaluationOpened":False},sort_keys=True))


if __name__ == "__main__":
    main()
