#!/usr/bin/env python3
"""Read-only, public-aggregate V1 engineering acceptance check.

NO model loading, new fit, outcomes discovery, source acquisition, or order functions.
A PASS means the already measured V1 research artifact is intact. It never
means predictive quality, fresh/OOS validity, RSS readiness, or live approval.
Keep this file below v1_acceptance/: the trained model binds all root-level *.py.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE_FLAGS = (
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
    "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted",
    "productionReady", "entryAllowed",
)
# Git blob SHAs from the fixed public artifacts; these are NOT the private model
# or original data hashes. Updating a measured result requires a new review.
PINNED_PUBLIC_BLOBS = {
    "REPORT_AGGREGATE.json": "a0e119e0449c8397fde27a43ff33f38c24b780ad",
    "MODEL_AND_INPUT_MANIFEST_PUBLIC.json": "936bbe08782d03ff603383e452bd41d7d30907ea",
    "CURRENT_STATUS.json": "639c952ce2f99848645cf1640d3fbf5bfb3efd53",
    "INDEPENDENT_RECOUNT_AUDIT.json": "8fc89cdb33da0eafd614c8756c0dbaf1b0c10f41",
    "SOURCE_COVERAGE_SUMMARY.json": "279e5d179c844dcc46e16322f4e86315c2fccb13",
    "FEATURE_SOURCE_COVERAGE_SUMMARY.csv": "5a4241b4523d205e18c3c371727593461aeb4f46",
    "OPEN_HIGH_BUCKET_COMPARISON.csv": "0492b6bf8ba163dceec64634718abd841e8fd7c5",
    "OPEN_HIGH_CUMULATIVE_COMPARISON.csv": "75285f20af542ccf20799f7f403709a093b08970",
    "MA4_EFFECTIVE_PRECOMMIT_20261013_V2.json": "5a705844973e6505a4aa91e4e13050ca2d6fcbf5",
    "EFFECTIVE_FEATURE_POLICY.json": "5618ed1ead297d19048247a816e2e161d573ac96",
    "BLOCKERS_AND_NEXT_ACTION.json": "ffa7ab1a1d04ccee1a805515a0fb569793f2ffe3",
}
MODEL_SHA = "e82279729b9ccc02fbcf7a1ffced7ade9057d8be41b058963dc4133e4ea19b48"
CODE_SHA = "3a2fb32dfad9e2ea4f9956038709f2a640a3380213f68ca7af8f1c9c621950ab"
FEATURE_SHA = "c9294e40ab8024618b0858bb4c9ccd1f388a22575765f2f761da4ac8099edc7a"
SCHEMA_SHA = "79a81013c5903913f531de6d97e402f5f19d7f13b6657e58363483128574f243"
SPLIT_SHA = "e18a181197927bed31b22fb376c42eb35fd0ed42dcabbbb88f7ffcc0b7208325"
EXACT_LEDGER_SHA = "c89f75b30d19038cdc7de8d4d785ce9ce50af1c633c0ad1c6dc55ab2e1eaf6e1"
SHIFTED_TICK_COLUMNS = (
    "preopen_previous_tick_tick_burst_relative_1m",
    "preopen_previous_tick_tick_realized_volatility_1m",
    "preopen_previous_tick_tick_realized_volatility_5m",
    "preopen_previous_tick_tick_up_tick_ratio_1m",
    "preopen_previous_tick_tick_up_tick_ratio_5m",
)


class GateError(RuntimeError):
    pass


def require(condition: bool, why: str) -> None:
    if not condition:
        raise GateError(why)


def read_json(root: Path, filename: str) -> dict:
    return json.loads((root / filename).read_text(encoding="utf-8"))


def read_csv(root: Path, filename: str) -> list[dict[str, str]]:
    with (root / filename).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def check_source_code_binding(root: Path) -> str:
    # Exactly matches source_code_hash() of the fixed computation code, without
    # importing or executing any of its model/native-source modules.
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.glob("*.py"))}
    digest = hashlib.sha256(
        json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    require(digest == CODE_SHA, "COMPUTATION_CODE_HASH_DRIFT")
    return digest


def verify(root: Path = ROOT) -> dict:
    root = Path(root)
    require(root.is_dir(), "RESEARCH_ROOT_NOT_FOUND")
    for name, expected in PINNED_PUBLIC_BLOBS.items():
        data = (root / name).read_bytes()
        require(blob_sha(data) == expected, "PUBLIC_ARTIFACT_CHANGED:" + name)

    computation = check_source_code_binding(root)
    report = read_json(root, "REPORT_AGGREGATE.json")
    manifest = read_json(root, "MODEL_AND_INPUT_MANIFEST_PUBLIC.json")
    status = read_json(root, "CURRENT_STATUS.json")
    recount = read_json(root, "INDEPENDENT_RECOUNT_AUDIT.json")
    coverage = read_json(root, "SOURCE_COVERAGE_SUMMARY.json")
    precommit = read_json(root, "MA4_EFFECTIVE_PRECOMMIT_20261013_V2.json")
    policy = read_json(root, "EFFECTIVE_FEATURE_POLICY.json")
    blockers = read_json(root, "BLOCKERS_AND_NEXT_ACTION.json")
    by_feature = {r["name"]: r for r in read_csv(root, "FEATURE_SOURCE_COVERAGE_SUMMARY.csv")}

    for name, obj in (("report", report), ("manifest", manifest), ("status", status),
                      ("recount", recount), ("coverage", coverage),
                      ("precommit", precommit), ("policy", policy), ("blockers", blockers)):
        for flag in SAFE_FLAGS:
            require(obj.get(flag) is False, name + ":UNSAFE_OR_MISSING_FLAG:" + flag)

    require(report["schema"] == "ARK_PREOPEN_FULL_BATCH_REPORT_V2", "REPORT_SCHEMA_DRIFT")
    require(report["mode"] == "AUTHORIZED_DEVELOPMENT" and report["sessions"] == 7,
            "REPORT_EXPOSURE_OR_DAYS_DRIFT")
    require(report["marketMeasurementComplete"] is True and report["legacyComparisonComplete"] is True,
            "INCOMPLETE_MEASUREMENTS")
    require(report["engineering"] == "PASS_COMPUTATION_CODE_HASH_BOUND",
            "ENGINEERING_EVIDENCE_CHANGED")
    require(report["liveReadiness"] == "NOT_CERTIFIED", "LIVE_READINESS_FALSE_PROMOTION")
    require(report["fixedBeforeReportLabelEvaluation"] is True
            and report["separateProcessTrustedReload"] is True,
            "REPORT_PREDICTION_NOT_PRECOMMITTED")
    q = report["researchQuality"]
    require(q["predictionQualityPass"] is False and q["freshOrOosCredit"] == 0
            and q["trueLossProbabilityZeroCertified"] is False,
            "RESEARCH_QUALITY_FALSE_PROMOTION")
    require(q["priorLiquidityLowSelectedN"] == 87 and q["selectedN"] == 105,
            "LIQUIDITY_DIAGNOSTIC_CHANGED")
    require(report["finalReportProbabilityDiagnostics"]["absoluteProbabilityCertified"] is False,
            "CALIBRATION_FALSE_CERTIFICATION")
    require(status["ENGINEERING_PASS"] is True and status["MARKET_MEASUREMENT_COMPLETE"] is True
            and status["LEGACY_COMPARISON_COMPLETE"] is True
            and status["RESEARCH_QUALITY"].startswith("NOT_APPROVED")
            and status["LIVE_READINESS"] == "NOT_CERTIFIED"
            and status["modelCandidatesUsed"] == 1,
            "CURRENT_STATUS_NOT_A_RESEARCH_FAILURE")
    require(not status["jobsRunning"], "RUNNING_MARKET_JOB_UNEXPECTED")
    require(blockers["newFitOrCandidateAuthorizedByThisResult"] is False
            and blockers["qualityApproval"] is False, "UNAUTHORIZED_MODEL_PROMOTION")
    require(recount["status"] == "PASS"
            and recount["originalSourceCrossMultiplicationRecount"]["status"] == "PASS"
            and recount["blindThirdPartyAudit"] is False, "RECOUNT_SCOPE_CHANGED")
    require(coverage["minuteTickDailyOHLCVolumeTurnoverMismatchN"] == 0,
            "SOURCE_DAILY_PARITY_DRIFT")
    require(coverage["registeredFeatureN"] == 554 and coverage["fitUsedFeatureN"] == 463
            and coverage["allMissingFitFeatureN"] == 90
            and coverage["constantFitFeatureN"] == 1, "FEATURE_COVERAGE_DRIFT")
    require(coverage["officialScheduleIsActualHistoricalReceiveProof"] is False,
            "HISTORICAL_RECEIVE_FALSE_CERTIFICATION")
    require(coverage["sourceCodeHash"] == computation and report["sourceCoverage"] == coverage,
            "REPORT_SOURCE_COVERAGE_DRIFT")
    require(policy["policy"]["dailyMovingAveragePeriods"] == [5, 15, 25, 75]
            and policy["policy"]["minuteMovingAveragePeriods"] == [5, 15, 30, 60]
            and policy["policy"]["coarseMovingAveragePeriods"] == [],
            "MA4_POLICY_DRIFT")
    require(precommit["watchlistCap"] == 15 and precommit["cutoffJST"] == "08:50:00"
            and precommit["candidateBudget"] == 1 and precommit["exposure"] ==
            "EXPOSED_DEVELOPMENT_NO_FRESH_CREDIT", "PRECOMMIT_OR_EXPOSURE_DRIFT")

    for key, expected in (
        ("modelSha256", MODEL_SHA), ("sourceCodeHash", CODE_SHA),
        ("featurePolicyHash", FEATURE_SHA), ("registeredSchemaHash", SCHEMA_SHA),
        ("fixedSplitHash", SPLIT_SHA), ("originalExactLedgerHash", EXACT_LEDGER_SHA),
    ):
        require(manifest[key] == expected, "PINNED_MODEL_OR_SOURCE_DRIFT:" + key)
    require(manifest["modelCandidateN"] == 1
            and manifest["baseHeadFits"] == 10 and manifest["calibrationFits"] == 10
            and manifest["reportUsedToTune"] is False and manifest["freshOosCredit"] == 0
            and manifest["rankIsExpectedReturn"] is False, "MODEL_OR_RANK_SCOPE_CHANGED")
    require(manifest["featureRows"] == coverage["featureRows"]
            and manifest["registeredFeatureN"] == coverage["registeredFeatureN"]
            and manifest["fitUsedFeatureN"] == coverage["fitUsedFeatureN"],
            "MODEL_FEATURE_ROWS_DRIFT")
    require(manifest["modelSha256"] == report["trainingSummary"]["modelFileSha256"]
            and manifest["featurePolicyHash"] == report["trainingSummary"]["featurePolicyHash"]
            and manifest["sourceCodeHash"] == report["trainingSummary"]["codeHash"]
            and manifest["watchlistHash"] == recount["watchlistHash"],
            "MODEL_REPORT_RECOUNT_LINK_DRIFT")
    require(manifest["fixedSplitHash"] == precommit["exactSplitHash"]
            and manifest["originalExactLedgerHash"] == precommit["exactLedgerSha256"]
            and manifest["registeredSchemaHash"] == precommit["featureSchemaHash"]
            and manifest["featurePolicyHash"] == precommit["featurePolicyHash"]
            and manifest["featurePolicyHash"] == policy["featurePolicyHash"],
            "PRECOMMITTED_INPUT_DRIFT")

    candidate, baseline = report["candidate"], report["previousSessionTurnoverTopK"]
    require((candidate["selectedN"], candidate["knownN"], candidate["unknownN"]) == (105, 102, 3),
            "CANDIDATE_POPULATION_DRIFT")
    require((baseline["selectedN"], baseline["knownN"], baseline["unknownN"]) == (105, 105, 0),
            "BASELINE_POPULATION_DRIFT")
    require(candidate["highHitN"]["1"] == 34 and baseline["highHitN"]["1"] == 56
            and candidate["lowHitN"]["3"] == 5 and baseline["lowHitN"]["3"] == 17,
            "QUALITY_COMPARISON_DRIFT")
    require(sum(candidate["buckets"].values()) == candidate["knownN"]
            and sum(baseline["buckets"].values()) == baseline["knownN"],
            "BUCKET_SUM_NOT_KNOWN_POPULATION")
    require(recount["originalSourceCrossMultiplicationRecount"]["methods"]["candidate"]["buckets"]
            == candidate["buckets"], "INDEPENDENT_CANDIDATE_RECOUNT_DRIFT")
    require(recount["originalSourceCrossMultiplicationRecount"]["methods"]
            ["previousSessionTurnoverTopK"]["buckets"] == baseline["buckets"],
            "INDEPENDENT_BASELINE_RECOUNT_DRIFT")
    for row in read_csv(root, "OPEN_HIGH_BUCKET_COMPARISON.csv"):
        name = row["bucket"]
        if name in candidate["buckets"]:
            require(int(row["newMA4N"]) == candidate["buckets"][name]
                    and int(row["previousTurnoverTop15N"]) == baseline["buckets"][name],
                    "CSV_BUCKET_NOT_RECONCILED:" + name)
    for row in read_csv(root, "OPEN_HIGH_CUMULATIVE_COMPARISON.csv"):
        t = row["thresholdPct"]
        require(int(row["newMA4N"]) == candidate["highHitN"][t]
                and int(row["previousTurnoverTop15N"]) == baseline["highHitN"][t],
                "CSV_CUMULATIVE_NOT_RECONCILED:" + t)

    # Flag historical feature distribution shift, but never choose new columns,
    # edit the model, or turn descriptive diagnostics into a model pass.
    drift = {}
    for name in SHIFTED_TICK_COLUMNS:
        row = by_feature[name]
        require(row["fitUsed"] == "True"
                and int(row["fitObservedN"]) > 0
                and int(row["calibrationObservedN"]) == 0
                and int(row["reportObservedN"]) == 0,
                "TICK_SUPPORT_SHIFT_EVIDENCE_CHANGED:" + name)
        drift[name] = int(row["fitObservedN"])
    require(report["privateRestoreAudit"]["trustedModelSelected105HeadRePrediction"]
            == "PASS_MAX_DELTA_0", "PRIVATE_RESTORE_EVIDENCE_CHANGED")

    return {
        "schema": "ARK_PREOPEN_SELECTOR_V1_READ_ONLY_ACCEPTANCE_V1",
        "verdict": "RESEARCH_ENGINEERING_ARTIFACT_COMPLETE",
        "quality": "NOT_APPROVED",
        "liveReadiness": "NOT_CERTIFIED",
        "newCandidateAuthorized": False,
        "trainedModelSha256": MODEL_SHA,
        "computationCodeSha256": CODE_SHA,
        "pinnedPublicArtifactN": len(PINNED_PUBLIC_BLOBS),
        "marketCandidateN": 1,
        "marketReportDays": 7,
        "marketWatchlistSymbolDays": 105,
        "up1SelectedN": candidate["highHitN"]["1"],
        "up1TurnoverBaselineN": baseline["highHitN"]["1"],
        "low3SelectedN": candidate["lowHitN"]["3"],
        "low3TurnoverBaselineN": baseline["lowHitN"]["3"],
        "lowLiquiditySelectedN": q["priorLiquidityLowSelectedN"],
        "fitUsedFeatureN": manifest["fitUsedFeatureN"],
        "tickShiftedColumns": drift,
        "freshOosCredit": 0,
        "realOrders": 0,
        "fullMarketRerunThisCheck": False,
        "thirdPartyAudit": False,
        **{flag: False for flag in SAFE_FLAGS},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        receipt = verify(args.root)
    except (GateError, KeyError, ValueError, OSError, TypeError) as exc:
        print(json.dumps({"schema": "ARK_PREOPEN_SELECTOR_V1_READ_ONLY_ACCEPTANCE_V1",
                          "verdict": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
