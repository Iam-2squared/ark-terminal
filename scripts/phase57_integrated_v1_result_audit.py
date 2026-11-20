"""Post-replay artifact integrity, causal ledger audit and lossless curve export."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from decimal import Decimal
from pathlib import Path

from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_development_integrated_v1 as v1

FIELDS = ("timestamp", "equityJpy", "cashJpy", "grossExposureJpy",
          "utilization", "drawdownPct", "equityValid")


def audit(result):
    v0.require(result["schema"] == "phase57-development-integrated-v1-result-v1" and
               result["protocolSha256"] == v1.PROTOCOL_SHA256 and
               result["exitStatus"] == "BENCHMARK_NOT_FINAL_EXIT",
               "RESULT_PROTOCOL_OR_BENCHMARK_DRIFT")
    v0.require(result["safety"] == v1.SAFETY and not any(result["safety"].values())
               and result["providerRequests"] == 0 and
               result["protectedPartitionsOpened"] == 0 and
               result["modelFits"] == 0, "RESULT_SAFETY_OR_EXPOSURE")
    expected = {arm+"_MAX"+str(capacity) for arm in v0.ARMS
                for capacity in v0.CAPACITIES}
    v0.require(set(result["variants"]) == expected, "EXACT_SIX_VARIANTS")
    cards, missing = {}, []
    for name, variant in result["variants"].items():
        ledger, curve, card = variant["ledger"], variant["curve"], variant["card"]
        snaps = ledger["snapshots"]
        v0.require(len(snaps) == len(curve) and len(snaps) > 0 and
                   card["exitStatus"] == "BENCHMARK_NOT_FINAL_EXIT" and
                   ledger["safety"] == v1.SAFETY, "VARIANT_SCHEMA")
        capacity = ledger["capacity"]
        v0.require(name == ledger["arm"]+"_MAX"+str(capacity), "VARIANT_NAME")
        seen_missing = []
        for row, curve_row in zip(snaps,curve):
            v0.require(row["timestamp"] == curve_row["timestamp"] and
                       row["equityJpy"] == curve_row["equityJpy"] and
                       row["cashJpy"] == curve_row["cashJpy"] and
                       row["openCount"] == len(row["positions"]) <= capacity and
                       Decimal(row["cashJpy"]) >= 0, "CURVE_ACCOUNTING_IDENTITY")
            exposure = Decimal(0)
            unrealized = Decimal(0)
            invalid = False
            for pos in row["positions"]:
                v0.require(pos["quantity"] > 0 and pos["quantity"] % 100 == 0,
                           "LOT_INVARIANT")
                if pos["markPrice"] is None:
                    invalid = True
                    v0.require(pos["unrealizedPnlJpy"] is None and
                               pos["missingReason"] is not None, "MISSING_MARK_MUST_BE_NULL")
                    seen_missing.append((name,row["timestamp"],pos["entryId"]))
                    continue
                known = v0.cash.stamp(pos["markKnownAt"])
                now = v0.cash.stamp(row["timestamp"])
                entered = v0.cash.stamp(pos["entryTimestamp"])
                v0.require(entered <= known <= now and known.date() == now.date() and
                           v1.segment(known.hour*60+known.minute) ==
                           v1.segment(now.hour*60+now.minute) is not None and
                           pos["staleMinutes"] == int((now-known).total_seconds()/60),
                           "FUTURE_CROSS_SESSION_OR_HIDDEN_STALE_MARK")
                v0.require(entered.date() == now.date(), "UNCERTIFIED_CORPORATE_ACTION_MARK")
                notional = Decimal(str(pos["markPrice"])) * pos["quantity"]
                exposure += notional
                unrealized += notional-Decimal(pos["costBasisJpy"])
                v0.require(Decimal(pos["markedNotionalJpy"]) == notional and
                           Decimal(pos["unrealizedPnlJpy"]) ==
                           notional-Decimal(pos["costBasisJpy"]), "POSITION_MTM_DRIFT")
            if invalid:
                v0.require(row["equityJpy"] is None and
                           row["grossExposureJpy"] is None and
                           row["unrealizedPnlJpy"] is None and
                           curve_row["drawdownPct"] is None, "INVALID_EQUITY_NOT_NULL")
            else:
                v0.require(Decimal(row["equityJpy"]) ==
                           Decimal(row["cashJpy"])+exposure and
                           Decimal(row["grossExposureJpy"]) == exposure and
                           Decimal(row["unrealizedPnlJpy"]) == unrealized,
                           "EQUITY_RECONCILIATION")
        actual = [(x["variant"],x["timestamp"],x["entryId"])
                  for x in ledger["missingReferences"]]
        v0.require(actual == seen_missing and len(actual) ==
                   card["missingReferenceCount"], "MISSING_REFERENCE_ENUMERATION")
        v0.require(card["validEventCount"] == sum(x["equityValid"] for x in snaps)
                   and card["valuationEventCoverage"] ==
                   card["validEventCount"]/len(snaps), "COVERAGE_DRIFT")
        if actual or ledger["endOpenEntryIds"]:
            v0.require(card["portfolioReturnPct"] is None and
                       card["finalEquityJpy"] is None, "CENSORED_RETURN_MUST_BE_NULL")
        if actual:
            v0.require(card["fullPeriodMaxDrawdownPct"] is None, "CENSORED_DRAWDOWN")
        cards[name] = card
        missing.extend(ledger["missingReferences"])
    return cards, missing


def write_outputs(result_path, out_dir, run_b=None):
    if run_b is not None:
        v0.require(v0.digest(result_path) == v0.digest(run_b),
                   "RUN_AB_NOT_BYTE_IDENTICAL")
    with gzip.open(result_path, "rt") as stream:
        result = json.load(stream)
    cards, missing = audit(result)
    out_dir = Path(out_dir)
    v0.require(not out_dir.exists(), "APPEND_ONLY_OUTPUT_DIR")
    out_dir.mkdir(parents=True)
    old = v0.EVIDENCE / "DEVELOPMENT_INTEGRATED_V0_FULL_SCORECARD.json.gz"
    v0.require(v0.digest(old) == v1.V0_SCORECARD_SHA256, "PRIOR_ENRICHMENT_IDENTITY")
    with gzip.open(old, "rt") as stream:
        old_card = json.load(stream)
    summary = {
        "schema":"phase57-development-integrated-v1-audited-scorecard",
        "protocolSha256":v1.PROTOCOL_SHA256,
        "resultSha256":v0.digest(result_path),
        "runABByteIdentical":run_b is not None,
        "exitStatus":"BENCHMARK_NOT_FINAL_EXIT",
        "scope":"Development outcome-exposed R50 34-session score window; not Fresh/OOS/live",
        "enrichmentUnchangedFromPinnedV0":old_card["enrichment"],
        "enrichmentSourceSha256":v1.V0_SCORECARD_SHA256,
        "cards":cards,"paired":result["paired"],
        "missingReferenceRows":len(missing),
        "completeFullPeriodAssetCurves":sum(not any(x["equityJpy"] is None
                                 for x in result["variants"][name]["curve"])
                                 for name in sorted(result["variants"])),
        "safety":v1.SAFETY,"providerRequests":0,"protectedPartitionsOpened":0}
    (out_dir/"scorecard.json").write_bytes(v0.canonical(summary))
    with (out_dir/"missing-references.json.gz").open("wb") as raw:
        with gzip.GzipFile(filename="",fileobj=raw,mode="wb",mtime=0) as stream:
            stream.write(v0.canonical(missing))
    for name,variant in sorted(result["variants"].items()):
        with (out_dir/(name+".csv")).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            for item in variant["curve"]:
                writer.writerow({key:item[key] for key in FIELDS})
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-a",type=Path,required=True)
    parser.add_argument("--result-b",type=Path)
    parser.add_argument("--out-dir",type=Path,required=True)
    args = parser.parse_args()
    summary = write_outputs(args.result_a,args.out_dir,args.result_b)
    print(json.dumps({"status":"AUDITED","resultSha256":summary["resultSha256"],
                      "missingReferenceRows":summary["missingReferenceRows"],
                      "completeFullPeriodAssetCurves":summary["completeFullPeriodAssetCurves"],
                      "coverage":{name:card["valuationEventCoverage"]
                                  for name,card in summary["cards"].items()}},
                     sort_keys=True))


if __name__ == "__main__":
    main()
