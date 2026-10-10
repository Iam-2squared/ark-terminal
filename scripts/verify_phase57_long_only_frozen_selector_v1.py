#!/usr/bin/env python3
"""Fail-closed integrity verification for Phase57 LONG-only Frozen Selector v1."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "predict/research/phase57-long-only-frozen-selector-v1.json"
EVIDENCE = ROOT / "docs/evidence/phase57-long-only-frozen-selector-v1-development-evidence.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise SystemExit(f"FROZEN SELECTOR INTEGRITY FAILURE: {message}")


def main():
    spec = json.loads(SPEC.read_text())
    evidence = json.loads(EVIDENCE.read_text())
    payload = spec["freezePayload"]
    hashes = spec["hashes"]
    selector = payload["selectorSpecification"]
    model = selector["model"]["configuration"]
    head = model["heads"][0]
    development = payload["development"]

    require(spec["status"] == "PHASE57_LONG_ONLY_FROZEN_SELECTOR_V1", "status")
    require(payload["identity"]["formalName"] == "Phase57 LONG-only Frozen Selector v1", "formal name")
    require(canonical_sha(payload) == hashes["freezePayloadSha256"], "freeze payload SHA")
    require(canonical_sha(development["sessions"]) == hashes["developmentSessionListSha256"], "session list SHA")
    require(canonical_sha(development["sessionIdentities"]) == hashes["developmentSessionIdentitySha256"], "session identity SHA")
    require(canonical_sha(selector["featureUniverse"]["orderedNames"]) == hashes["featureListSha256"], "feature list/order SHA")
    require(canonical_sha(model) == hashes["modelConfigurationSha256"], "model configuration SHA")

    head_core = {key: value for key, value in head.items() if key != "artifactSha256"}
    model_core = {key: value for key, value in model.items() if key != "artifactSha256"}
    node_head_sha = hashlib.sha256(json.dumps(head_core, separators=(",", ":")).encode()).hexdigest()
    node_model_sha = hashlib.sha256(json.dumps(model_core, separators=(",", ":")).encode()).hexdigest()
    require(node_head_sha == head["artifactSha256"] == hashes["savedModelHeadArtifactSha256"], "saved Ridge head identity")
    require(node_model_sha == model["artifactSha256"] == hashes["savedModelArtifactSha256"], "saved Ridge model identity")

    require(development["sessionCount"] == 76 == len(development["sessions"]), "Development session count")
    require(len(set(development["sessions"])) == 76, "Development sessions unique")
    require(development["sessions"] == sorted(development["sessions"]), "Development session ordering")
    require([row["sessionDate"] for row in development["sessionIdentities"]] == development["sessions"], "session identity coverage")
    require(development["decisionTimestampCount"] == 760, "decision timestamp count")
    require(development["top5SelectionEvents"] == 3800, "Top5 selection event count")

    require(selector["eligibility"]["maximumAgeWallClockMinutes"] == 5, "freshness threshold")
    require(selector["eligibility"]["order"] == "ELIGIBILITY_BEFORE_RANKING", "eligibility order")
    require(selector["ranking"]["topN"] == 5, "Top5 policy")
    require(selector["ranking"]["decisionTimesJst"] == ["09:30", "10:00", "10:30", "11:00", "11:30", "13:00", "13:30", "14:00", "14:30", "15:00"], "decision schedule")
    require(head["lambda"] == 0.1 and model["candidateId"] == "RIDGE_Y30", "Ridge configuration")
    require(head["featureNames"] == selector["featureUniverse"]["orderedNames"], "model feature order")
    require(selector["trainingTarget"]["observationsForward"] == 6, "target observation horizon")

    require(file_sha(EVIDENCE) == hashes["evidenceFileSha256"], "evidence file SHA")
    evidence_core = {key: value for key, value in evidence.items() if key != "reportSha256"}
    require(canonical_sha(evidence_core) == evidence["reportSha256"] == hashes["evidenceReportSha256"], "evidence report self-SHA")
    require(evidence["dataAudit"]["availableSessions"] == 76, "evidence sessions")
    require(evidence["dataAudit"]["decisionCount"] == 760, "evidence decisions")
    require(evidence["dataAudit"]["top5SelectionEvents"] == 3800, "evidence selections")

    for threshold in ("1", "2", "3", "5"):
        frozen = payload["frozenEvidence"]["highTouch"][threshold]
        observed = evidence["highTouch"][threshold]
        comparisons = {
            "precisionAt5Pct": observed["metrics"]["precisionAt5Pct"],
            "meanHitsPerTop5": observed["perDecisionTop5"]["meanHitsPerTop5"],
            "medianHitsPerTop5": observed["perDecisionTop5"]["medianHitsPerTop5"],
            "probabilityAtLeastOnePct": observed["perDecisionTop5"]["probabilityPct"]["GE1"],
            "actualRecallPct": observed["metrics"]["actualRecallPct"],
            "randomExpectedRecallPct": observed["metrics"]["randomExpectedRecallPct"],
            "recallLift": observed["metrics"]["recallLift"],
            "precisionLift": observed["metrics"]["precisionLift"],
            "medianTimeToHitMinutes": evidence["timeToHit"]["highTouch"][threshold]["distributionMinutes"]["p50"],
        }
        require(frozen == comparisons, f"frozen High evidence +{threshold}%")
        close = payload["frozenEvidence"]["closeConfirmation"][threshold]
        close_observed = evidence["closeConfirmed"][threshold]
        require(close == {
            "precisionAt5Pct": close_observed["metrics"]["precisionAt5Pct"],
            "probabilityAtLeastOnePct": close_observed["perDecisionTop5"]["probabilityPct"]["GE1"],
        }, f"frozen Close evidence +{threshold}%")

    for relative, expected in hashes["implementationFilesSha256"].items():
        require(file_sha(ROOT / relative) == expected, f"implementation SHA {relative}")

    for flag in ("executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed", "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed"):
        require(payload["safety"][flag] is False, f"safety flag {flag}")
    require(payload["safety"]["providerRequests"] == 0, "provider requests")
    require(payload["safety"]["fitCalls"] == 0, "fit calls")
    require(payload["sealedBoundaries"] == {"validation": "SEALED", "oos": "SEALED", "entryExitAllocation": "NOT_STARTED", "automaticNextStepAllowed": False}, "sealed boundaries")

    print(json.dumps({
        "status": "PHASE57_LONG_ONLY_FROZEN_SELECTOR_V1_REPRODUCIBILITY_PASS",
        "formalName": payload["identity"]["formalName"],
        "freezePayloadSha256": hashes["freezePayloadSha256"],
        "developmentSessionListSha256": hashes["developmentSessionListSha256"],
        "featureListSha256": hashes["featureListSha256"],
        "modelConfigurationSha256": hashes["modelConfigurationSha256"],
        "evidenceFileSha256": hashes["evidenceFileSha256"],
        "validation": "SEALED",
        "oos": "SEALED",
        "fitCalls": 0,
        "providerRequests": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
