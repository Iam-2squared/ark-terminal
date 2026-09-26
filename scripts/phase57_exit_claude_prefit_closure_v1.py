"""R30 machine-readable closure of Claude R28 pre-fit findings.

This module performs no estimator fit and never inspects NEW EXIT candidate
performance. It binds the already-frozen R20/R23/R24/R25 contracts to executable
checks before any Development fit is allowed.
"""
from __future__ import annotations

import json

from scripts import phase57_exit_checkpoints_v1 as checkpoints
from scripts import phase57_exit_evaluator_contract_v1 as evaluator
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_exit_feature_contract_v1 as feature
from scripts import phase57_exit_research_protocol_v1 as research


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def _bar(start: int, o: float, h: float, l: float, c: float, known_at: int | None = None):
    return checkpoints.KnownBar(start, o, h, l, c, 1000.0, 100000.0,
                                start + 1 if known_at is None else known_at)


def synthetic_checks() -> dict:
    day = "2025-06-02"

    # F001: State at NOW is the direct canonical observation carried at NOW.
    entry = {
        "opportunity": day + "|TEST",
        "session": day,
        "symbol": "TEST",
        "entryId": day + "|TEST|540",
        "entryMinute": 540,
        "price": 100.0,
    }
    observer = checkpoints.PositionObserver(
        entry,
        entry_state={"state": "RISE", "dataQuality": "OK"},
    )
    prefix = (_bar(540, 100, 101, 99, 100.5),)
    recognition = {
        "state": {
            "state": "DROP",
            "dataQuality": "OK",
            "reason": "SYNTHETIC_DIRECT_NOW",
            "confidence": 1.0,
        },
        "signals": {
            family: {"state": None, "event": None, "trigger": None}
            for family in checkpoints.FAMILIES
        },
        "signalContext": {},
        "activity": {},
    }
    observed = observer.step(541, prefix, recognition)
    require(observed["recognition"]["state"]["state"] == "DROP", "STATE_NOT_DIRECT_NOW")
    require(observed["entryToCurrentState"] == ["RISE", "DROP"], "STATE_TRANSITION_NOT_DIRECT")
    require("action" not in observed and "exit" not in observed, "OBSERVER_CONTAINS_STATE_ACTION")

    # F002: UNKNOWN remains a third state and TRUE->UNKNOWN is not disappearance.
    rows = []
    for now, value in ((601, True), (602, None)):
        signals = {family: None for family in checkpoints.FAMILIES}
        signals["CONTINUATION"] = value
        rows.append({"now": now, "state": "RISE", "signals": signals})
    history = checkpoints.summarize_history(rows, 602)
    cont = history["3"]["signals"]["CONTINUATION"]
    require(cont == {"true": 1, "false": 0, "unknown": 1}, "TRISTATE_COUNT_COLLAPSE")
    require(history["bullishStateDisappeared"]["CONTINUATION"] is None,
            "TRUE_TO_UNKNOWN_MISCLASSIFIED_AS_FAILURE")

    # F003/F007/F009: observed extrema are causal history, while certified
    # complete-prefix metrics are unavailable if an expected owned bar is missing.
    incomplete = (
        _bar(540, 100, 101, 99, 100.5),
        _bar(542, 100.5, 103, 100, 101.0),
    )
    pos = checkpoints.position_features(checkpoints.entry_envelope(entry), 543, incomplete)
    require(pos["observedRunningHigh"] == 103, "OBSERVED_HIGH_NOT_PRESERVED")
    require(pos["fullOwnedPrefix"] is False and pos["missingOwnedBars"] == 1,
            "INCOMPLETE_PREFIX_NOT_FLAGGED")
    require(pos["completePrefixMfePct"] is None and pos["completePrefixMaePct"] is None,
            "INCOMPLETE_PREFIX_CERTIFIED_EXTREMA")
    stale = (_bar(540, 100, 101, 99, 100.5),)
    stale_pos = checkpoints.position_features(checkpoints.entry_envelope(entry), 543, stale)
    require(stale_pos["freshClosedPrice"] is False and stale_pos["currentReturnPct"] is None,
            "MISSING_FRESH_CLOSE_FORWARD_FILLED")
    require(stale_pos["lastObservedClose"] == 100.5, "LAST_OBSERVED_NOT_SEPARATE")

    # F005/F008: decisions are exact integer endpoints and lunch/terminal are fixed.
    endpoints = execution.decision_endpoints(day, 540)
    require(all(type(x) is int for x in endpoints), "NON_INTEGER_DECISION_EPOCH")
    require(690 in endpoints and execution.next_execution_start(day, 690) == 750,
            "LUNCH_EXECUTION_CONTRACT")
    require(execution.next_execution_start(day, 925) is None, "TERMINAL_PREPOINT_HAS_ORDINARY_FILL")
    terminal_missing = execution.terminal_execution_reference([])
    require(terminal_missing["censored"] is True and terminal_missing["price"] is None,
            "TERMINAL_MISSING_NOT_CENSORED")

    rc = research.contract()
    fc = feature.contract()
    ec = evaluator.scorecard_contract()

    # F004/F006/F010/F011/F012: training/search stays finite and bucket-free.
    training_surface = {
        "featureSets": rc["featureSets"],
        "split": rc["split"],
        "preprocessing": rc["preprocessing"],
        "models": rc["models"],
        "decisionMapping": rc["decisionMapping"],
    }
    training_text = json.dumps(training_surface, sort_keys=True)
    require("orderedLow" not in training_text and "opportunityBuckets" not in training_text,
            "EVALUATOR_BUCKET_LEAKED_TO_TRAINING_SURFACE")
    require(rc["models"]["candidateConfigurations"] == 24, "CANDIDATE_COUNT_CHANGED")
    thresholds = sorted({x["exitThresholdPp"] for x in rc["models"]["grid"]})
    persistence = sorted({x["persistenceFreshCheckpoints"] for x in rc["models"]["grid"]})
    require(thresholds == [0.0, 0.10] and persistence == [1, 2],
            "REGISTERED_DECISION_THRESHOLDS_CHANGED")
    require("probab" not in json.dumps(rc["decisionMapping"], sort_keys=True).lower(),
            "UNREGISTERED_PROBABILITY_THRESHOLD")
    require(len(rc["split"]["folds"]) == 4 and rc["split"]["developmentSessions"] == 58,
            "SESSION_SPLIT_DRIFT")
    require(len(research.development_sessions()) == 58, "CALENDAR_SESSION_COUNT_DRIFT")
    require(ec["terminalReferenceCensus"]["auctionReferenceMissing"] == 63,
            "TERMINAL_MISSING_CENSUS_DRIFT")
    require(ec["evaluatorOnly"] is True, "EVALUATOR_NOT_ISOLATED")
    require(fc["timingSignals"]["status"] == "MODEL_ADMITTED_TRI_STATE_UNKNOWN_NOT_FALSE",
            "SIGNAL_ENCODING_DRIFT")

    return {
        "schemaVersion": "phase57-exit-claude-prefit-closure-r30",
        "basis": {
            "r28Disposition": "CLAUDE_INDEPENDENT_REVIEW_DISPOSITION_R28",
            "r23FeatureContract": fc["schemaVersion"],
            "r24EvaluatorContract": ec["schemaVersion"],
            "r25ResearchProtocol": rc["schemaVersion"],
        },
        "findings": {
            "F001": {
                "disposition": "PARTIAL",
                "closed": True,
                "rule": "CURRENT_STATE_IS_DIRECT_STRICT_NOW_CANONICAL_EVIDENCE_NO_STATE_ONLY_ACTION",
            },
            "F002": {
                "disposition": "ACCEPT",
                "closed": True,
                "encoding": ["TRUE", "FALSE", "UNKNOWN"],
                "trueToUnknownIsFailure": False,
                "completeSignalFilteringAllowed": False,
            },
            "F003": {
                "disposition": "PARTIAL",
                "closed": True,
                "observedExtrema": "COMPLETED_OWNED_BARS_KNOWN_BY_NOW",
                "incompleteCertifiedExtrema": None,
            },
            "F004": {
                "disposition": "PARTIAL",
                "closed": True,
                "blockedPatternColumns": fc["patternRegistry"]["statusCounts"]["BLOCKED"],
                "finitePatternColumns": fc["patternRegistry"]["finiteSearchCuratedColumns"],
            },
            "F005": {
                "disposition": "ACCEPT",
                "closed": True,
                "decisionEpoch": "EXACT_COMPLETED_1M_ENDPOINT_ONLY_NO_INTRABAR_DECISION",
            },
            "F006": {
                "disposition": "ACCEPT",
                "closed": True,
                "bucketUse": "EVALUATOR_ONLY_NOT_MODEL_INPUT_PREPROCESSING_FIT_STRATUM_OR_CONFIG",
                "precommittedWinnerGateException": "R25_POST_REPLAY_EVALUATOR_GATE_ONLY",
            },
            "F007": {
                "disposition": "ACCEPT",
                "closed": True,
                "certifiedOwnedGivebackRequiresCompletePrefix": True,
            },
            "F008": {
                "disposition": "ACCEPT",
                "closed": True,
                "lunch": "11:30_DECISION_TO_12:30_OPEN",
                "overnight": False,
                "terminalMissingCensored": 63,
            },
            "F009": {
                "disposition": "ACCEPT",
                "closed": True,
                "freshMissingForwardFill": False,
            },
            "F010": {
                "disposition": "ACCEPT",
                "closed": True,
                "candidateConfigurations": 24,
                "adaptiveExpansion": False,
            },
            "F011": {
                "disposition": "REJECT",
                "closed": True,
                "reason": "NUMERIC_HOLD_VALUE_REGRESSION_NOT_EXIT_PROBABILITY_CLASSIFIER",
                "registeredThresholdPp": thresholds,
                "registeredPersistence": persistence,
            },
            "F012": {
                "disposition": "ACCEPT",
                "closed": True,
                "sessions": 58,
                "sessionMeaning": "OPPORTUNITY_BEARING_TRADING_CALENDAR_SESSIONS",
                "runABMeaning": "DETERMINISTIC_REGENERATION_MUST_BE_BYTE_IDENTICAL",
            },
        },
        "syntheticChecks": {
            "stateDirectNow": True,
            "signalTriState": True,
            "trueToUnknownNotFailure": True,
            "incompletePrefixCertifiedMetricsNull": True,
            "missingFreshCloseNotForwardFilled": True,
            "exactMinuteDecisionEpochs": True,
            "terminalMissingCensored": True,
            "trainingSurfaceBucketFree": True,
            "finite24Unchanged": True,
            "probabilityThresholdAbsent": True,
            "calendarSessions58": True,
        },
        "candidatePerformanceInspected": False,
        "modelFits": 0,
        "providerRequests": 0,
        "protectedPartitionsOpened": 0,
        "safety": execution.SAFETY,
        "status": "R28_REQUIRED_PREFIT_CORRECTIONS_MACHINE_CLOSED",
    }


if __name__ == "__main__":
    print(json.dumps(synthetic_checks(), sort_keys=True, separators=(",", ":")))
