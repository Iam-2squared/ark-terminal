#!/usr/bin/env python3
"""Fail-closed, offline scorecard for user-observed 2026 RSS price-only report.

Never equate +2/+3/+5 observed High touches with Frozen Selector's actual
entries, and never equate unobserved future bars with negative labels.
No broker, Excel, network, source capture changes or production promotion.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
SOURCE_SHA256 = "380616e9c2d05eb481b5ed160e35b92365822d770e23f9ed80d7295ac883c5e4"
SOURCE_SCHEMA = "ARK_NO11_RSS_2026_OBSERVED_PRICE_ONLY_OUTCOMES_V1"
REPORT_SCHEMA = "ARK_NO11_2026_PRICE_ONLY_80_CLOCK_SCORECARD_V1"
DAYS = ("2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06",
        "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-13")
CLOCKS = ("09:30", "10:00", "10:30", "11:00", "11:30",
          "13:00", "13:30", "14:00", "14:30", "15:00")
LEVELS = (2, 3, 5)
EXPECTED = {
    "priceAnchors": 59712, "withFutureObserved": 58652,
    "fullFutureWindow": 17251,
    "highTouch2Observed": 4801, "highTouch3Observed": 2104,
    "highTouch5Observed": 756, "lowTouch2Observed": 3623,
    "lowTouch3Observed": 1751, "lowTouch5Observed": 639,
    "highTouch2Unknown": 38979, "highTouch3Unknown": 40885,
    "highTouch5Unknown": 41888, "lowTouch2Unknown": 39607,
    "lowTouch3Unknown": 41075, "lowTouch5Unknown": 41962
}
COUNT_FIELDS = tuple(EXPECTED)


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def load_file(p):
    require(p.is_file() and not p.is_symlink() and
            0 < p.stat().st_size < 250_000, "NO11_SCORECARD_UNSAFE_INPUT")
    b = p.read_bytes()
    require(sha256(b).hexdigest() == SOURCE_SHA256,
            "NO11_SCORECARD_SOURCE_REPORT_SHA_MISMATCH")
    data = json.loads(b.decode("utf-8-sig"))
    require(isinstance(data, dict), "NO11_SCORECARD_INVALID_SOURCE_OBJECT")
    return data


def clock_counts(row):
    require(isinstance(row, dict) and set(row) == set(COUNT_FIELDS),
            "NO11_SCORECARD_COUNT_FIELDS_MISMATCH")
    require(all(type(row[k]) is int and row[k] >= 0 for k in COUNT_FIELDS),
            "NO11_SCORECARD_INVALID_COUNT")
    count = row["priceAnchors"]
    require(0 <= row["fullFutureWindow"] <= row["withFutureObserved"] <= count,
            "NO11_SCORECARD_FUTURE_COVERAGE_INCONSISTENT")
    for side in ("high", "low"):
        hits = [row[f"{side}Touch{level}Observed"] for level in LEVELS]
        unknown = [row[f"{side}Touch{level}Unknown"] for level in LEVELS]
        require(hits == sorted(hits, reverse=True) and
                unknown == sorted(unknown),
                "NO11_SCORECARD_THRESHOLD_ORDER_INCONSISTENT")
        for h, u in zip(hits, unknown):
            require(h + u <= count and u <= count - row["fullFutureWindow"],
                    "NO11_SCORECARD_UNKNOWN_OR_HIT_OVERCOUNT")
    return Counter(row)


def verify_and_sum(report, enforce_production_evidence=True):
    require(report.get("schemaId") == SOURCE_SCHEMA and
            report.get("status") == "PRICE_ONLY_OBSERVED_FUTURE_NO_FROZEN_SELECTOR" and
            report.get("decisionPriceAnchors") == EXPECTED["priceAnchors"] and
            report.get("source5mRows") == 337023 and
            report.get("source5mSha256") ==
              "63389666d55a2cb4c21d9f9ba2fb8fbae2a92cdf3044d2b949798c66997d1f74" and
            report.get("nativeSelectorExecuted") is False and
            report.get("firstEntryExecuted") is False and
            report.get("nativeState9Executed") is False and
            report.get("new2026FrozenH235TrainingRows") == 0 and
            report.get("modelFitPerformed") is False and
            report.get("productionReady") is False and
            report.get("orderTransmission") is False and
            report.get("terminalAuctionsNotIncludedInHighLow") is True and
            report.get("futureUnknownNeverConvertedToNegative") is True,
            "NO11_SCORECARD_NON_RESEARCH_OR_UNSAFE_SOURCE")
    cells = report.get("byDayDecision")
    require(isinstance(cells, dict) and set(cells) == set(DAYS) and
            all(isinstance(cells[day], dict) and
                set(cells[day]) == set(CLOCKS) for day in DAYS),
            "NO11_SCORECARD_80_SNAPSHOTS_REQUIRED")
    total = Counter()
    by_day = {}
    by_clock = {clock: Counter() for clock in CLOCKS}
    for day in DAYS:
        by_day[day] = Counter()
        for clock in CLOCKS:
            c = clock_counts(cells[day][clock])
            total.update(c)
            by_day[day].update(c)
            by_clock[clock].update(c)
    if enforce_production_evidence:
        require(dict(total) == EXPECTED,
                "NO11_SCORECARD_PHYSICAL_RECEIPT_COUNTS_CHANGED")
    def rate(n, den):
        return round(100*n/den, 4) if den else None
    levels = {}
    for side in ("high","low"):
        for level in LEVELS:
            hit=total[f"{side}Touch{level}Observed"]
            unknown=total[f"{side}Touch{level}Unknown"]
            definite_not_hit=total["priceAnchors"]-hit-unknown
            require(definite_not_hit>=0,
                    "NO11_SCORECARD_NEGATIVE_DEFINITE_NOT_HIT")
            levels[f"{side}{level}"] = {
                "observedHit":hit,
                "definiteNotHitInObservedProxy":definite_not_hit,
                "unknownWithIncompleteFuture":unknown,
                "observedHitLowerBoundPctOfAnchors":rate(hit,total["priceAnchors"]),
                "potentialHitUpperBoundPctOfAnchors":rate(hit+unknown,total["priceAnchors"]),
                "unknownPctOfAnchors":rate(unknown,total["priceAnchors"]),
                "completeCaseHitRateBiasedDoNotUse":None
            }
    summary={
        "schemaId":REPORT_SCHEMA,
        "sourceReportSha256":SOURCE_SHA256,
        "sourceWindow":{"sessions":list(DAYS),"decisionClocks":list(CLOCKS),
                        "clockSnapshots":len(DAYS)*len(CLOCKS)},
        "counts":dict(total),
        "completeFutureWindowPct":rate(total["fullFutureWindow"],
                                       total["priceAnchors"]),
        "anyFutureFiveMinuteObservedPct":rate(total["withFutureObserved"],
                                              total["priceAnchors"]),
        "thresholdBounds":levels,
        "bySession":{day:dict(by_day[day]) for day in DAYS},
        "byClock":{tm:dict(by_clock[tm]) for tm in CLOCKS},
        "interpretation":"OBSERVED_PRICE_ONLY_CENSORED_PROXY_NOT_FROZEN_STRATEGY",
        "fiveMinuteBarVendorSemanticsCertified":False,
        "originalAdjustedDailyAndMasterAdmissionAvailable":False,
        "historicalMarketFirstReceivedTimeCertified":False,
        "futureTeacherUsedInDecisionFeatures":False,
        "nativeFrozenSelectorExecuted":False,
        "nativeFirstEntryExecuted":False,
        "nativeState9Executed":False,
        "originalFrozenH235ModelResultsGenerated":False,
        "new2026SupervisedTrainingRows":0,
        "automaticModelPromotion":False,
        "productionReady":False,
        "orderTransmission":False,
    }
    return summary


def self_test():
    row = {k: 0 for k in COUNT_FIELDS}
    row.update(priceAnchors=5,withFutureObserved=4,fullFutureWindow=2,
               highTouch2Observed=2,highTouch3Observed=1,highTouch5Observed=1,
               lowTouch2Observed=1,highTouch2Unknown=2,highTouch3Unknown=3,
               highTouch5Unknown=3,lowTouch2Unknown=2,
               lowTouch3Unknown=3,lowTouch5Unknown=3)
    clock_counts(row)
    altered=dict(row)
    altered["highTouch5Observed"]=3
    try:
        clock_counts(altered)
    except RuntimeError as e:
        assert "THRESHOLD_ORDER" in str(e)
    else:
        raise AssertionError("NON_MONOTONE_HITS_ACCEPTED")
    altered=dict(row)
    altered["highTouch2Unknown"]=4
    try:
        clock_counts(altered)
    except RuntimeError:
        pass
    else:
        raise AssertionError("UNKNOWN_OVERCOUNT_ACCEPTED")
    print("NO11_2026_PRICE_ONLY_SCORECARD_OFFLINE_SELFTEST=PASS")
    print("ORDER_TRANSMISSION=False")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline-self-test",action="store_true")
    p.add_argument("--report",type=Path)
    p.add_argument("--output-dir",type=Path)
    a=p.parse_args()
    if a.offline_self_test:
        self_test()
        return
    require(a.report is not None and a.output_dir is not None and
            a.output_dir.is_dir() and not a.output_dir.is_symlink(),
            "NO11_SCORECARD_ARGUMENTS_INVALID")
    d=load_file(a.report)
    summary=verify_and_sum(d)
    raw=(json.dumps(summary,sort_keys=True,indent=2,ensure_ascii=False,
                    allow_nan=False)+"\n").encode("utf8")
    digest=sha256(raw).hexdigest()
    path=a.output_dir/("no11-2026-price-only-scorecard-"+digest[:16]+".json")
    if path.exists():
        require(path.is_file() and not path.is_symlink() and
                path.read_bytes()==raw,"NO11_SCORECARD_EXISTING_REPORT_CHANGED")
    else:
        with path.open("xb") as f:
            f.write(raw)
    print("NO11_2026_PRICE_ONLY_SCORECARD=PASS_RESEARCH_ONLY")
    print("NO11_PRICE_ONLY_ANCHORS="+str(summary["counts"]["priceAnchors"]))
    print("NO11_PRICE_ONLY_FULL_FUTURE_COUNT="+str(summary["counts"]["fullFutureWindow"]))
    print("NO11_PRICE_ONLY_REPORT="+str(path))
    print("NO11_2026_H235_NEW_TRAINING_ROWS=0")
    print("ORDER_TRANSMISSION=False")


if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print("NO11_2026_PRICE_ONLY_SCORECARD=BLOCKED:"+str(e),file=sys.stderr)
        print("NO11_PRODUCTION_READY=False",file=sys.stderr)
        print("ORDER_TRANSMISSION=False",file=sys.stderr)
        sys.exit(2)
