"""R33 implementation freeze for the finite R25 NEW EXIT run.

This module is contract-only. It performs zero estimator fits and reads no
candidate performance.  It closes implementation details that R25 intentionally
left as plumbing choices so the finite run cannot drift after results appear.
"""
from __future__ import annotations

import json
from scripts import phase57_exit_research_protocol_v1 as r25

R20 = {
    "workflowRun": 36128852207,
    "artifactId": 10862675162,
    "artifactDigest": "sha256:6019809ca4ac9793c5a34ec1c894580c52ffea5074b6ee0ee8e593d10ef12b40",
    "member": "run-a",
    "runABRequiredByteIdentical": True,
}
PATTERN = {
    "workflowRun": 35510863265,
    "artifactId": 10605887642,
    "artifactDigest": "sha256:749caf82bbd9d39969f5712ef5a6f2705ac973a2f74483f03307c671586ae05a",
    "rawPathsSHA256": "37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b",
}
ARMS = ("IMMEDIATE", "ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF")
SIGNALS = ("CONTINUATION", "BREAKOUT", "COMPRESSION_EXPANSION",
           "HIGHER_LOW", "LOWER_WICK", "RECLAIM")


def prediction_specs():
    """Six fitted prediction surfaces shared by the 24 policy mappings."""
    grid = r25.candidate_grid()
    unique = {}
    for row in grid:
        if row["family"].startswith("RIDGE"):
            key = (row["family"], row["featureSet"], row["alpha"])
        else:
            key = (row["family"], row["featureSet"], row["maxLeafNodes"])
        unique.setdefault(key, {
            "family": row["family"],
            "featureSet": row["featureSet"],
            **({"alpha": row["alpha"]} if "alpha" in row else {
                "maxLeafNodes": row["maxLeafNodes"],
                "learningRate": row["learningRate"],
                "maxIter": row["maxIter"],
                "minSamplesLeaf": row["minSamplesLeaf"],
                "l2Regularization": row["l2Regularization"],
                "randomSeed": row["randomSeed"],
            }),
        })
    rows = list(unique.values())
    assert len(rows) == 6
    return rows


def contract():
    base = r25.contract()
    score_sessions = [d for fold in base["split"]["folds"] for d in fold["score"]]
    return {
        "schemaVersion": "phase57-new-exit-fit-implementation-freeze-r33",
        "status": "PRECOMMITTED_BEFORE_FIRST_R25_ESTIMATOR_FIT",
        "entryDualFreeze": base["entryFreeze"],
        "sources": {"r20": R20, "pattern": PATTERN},
        "scope": {
            "fit": "ONLY_EACH_FOLD_TRAIN_SESSIONS",
            "purge": "NEVER_FIT_NEVER_SCORE",
            "selectionPerformance": "OOF_SCORE_SESSIONS_ONLY",
            "scoreSessions": score_sessions,
            "scoreSessionCount": len(score_sessions),
            "all24RequiredBeforeWinnerDeclaration": True,
            "trainingOrScoringOnProtectedPartitions": False,
        },
        "rowIdentity": "ENTRY_ARM|OPPORTUNITY|NOW;_WHOLE_SESSION_OPPORTUNITY_ARM_SEQUENCE_GROUPED",
        "coreEncoding": {
            "categorical": [
                "entryState.state", "entryState.dataQuality", "entryState.confidence",
                "currentState.state", "currentState.dataQuality", "currentState.confidence",
                "entryToCurrentState", "entryState.reasonCodesSorted",
                "currentState.reasonCodesSorted",
                *[f"signal.{s}.currentTriState" for s in SIGNALS],
                *[f"signal.{s}.observedTrueToFalseTriState" for s in SIGNALS],
            ],
            "numeric": [
                "stateDwellObservedActiveMinutes",
                *[f"history.{w}.stateChanges" for w in (3,5,10)],
                *[f"history.{w}.stateKnown" for w in (3,5,10)],
                *[f"history.{w}.stateKnownAdjacentPairs" for w in (3,5,10)],
                *[f"history.{w}.signal.{s}.{k}" for w in (3,5,10)
                  for s in SIGNALS for k in ("true","false","unknown")],
                "history.stateRunObservedSamplesCapped10",
                "position.clockMinutesHeld", "position.activeMinutesHeld",
                "position.observedOwnedBars", "position.missingOwnedBars",
                "position.fullOwnedPrefix", "position.freshClosedPrice",
                "position.lastObservedClose", "position.lastObservedClosedAt",
                "position.currentReturnPct", "position.observedRunningHigh",
                "position.observedRunningLow", "position.observedMfePct",
                "position.observedMaePct", "position.completePrefixMfePct",
                "position.completePrefixMaePct", "position.observedPeakGivebackPp",
                "position.peakConfirmedAt", "position.activeMinutesSincePeakConfirmation",
            ],
            "unknownSignalEncoding": "TRUE_FALSE_UNKNOWN;_TRUE_TO_UNKNOWN_IS_NOT_FAILURE",
            "reasonCodes": "SORTED_JOINED_CATEGORICAL;_NO_REASON_IS_EXPLICIT_UNKNOWN",
            "booleanNumericEncoding": "FALSE_0_TRUE_1_MISSING_NULL",
            "blocked": "ANY_FUTURE_GEOMETRY_OUTCOME_OR_EVALUATOR_FIELD",
        },
        "patternEncoding": {
            "onlyFor": "CORE_PLUS_CURATED_PATTERN",
            "columns": 187,
            "producer": "scripts.phase57_exit_feature_contract_v1.pattern_now",
            "cacheKey": "OPPORTUNITY|NOW",
            "todayInput": "RAW_PATH_ROWS_WITH_BAR_START_PLUS_1_LE_NOW_ONLY",
            "previousInput": "PINNED_PREVIOUS_SESSION_OBSERVED_PATH",
            "priorDaily": "NONE_BLOCKED_30_REMAIN_NULL",
            "selectorOrigin": "PINNED_DECISION_PRICE_SAVED_V1_SCORE_NEW_ELIGIBLE_RANK",
            "futureSuffixMutationMayNotAlterEarlierFeature": True,
        },
        "labels": {
            "exitNow": "EXACT_NEXT_SCHEDULED_CONTINUOUS_OPEN_AFTER_NOW",
            "hold5": "OPEN_AFTER_5_ADDITIONAL_SCHEDULED_CONTINUOUS_1M_BARS_FROM_EXIT_NOW",
            "hold15": "OPEN_AFTER_15_ADDITIONAL_SCHEDULED_CONTINUOUS_1M_BARS_FROM_EXIT_NOW",
            "holdTerminal": "EXACT_MINUTE_930_ENDPOINT_AUCTION",
            "exactMissing": "NULL_CENSORED_NO_FORWARD_SEARCH_NO_ZERO",
            "terminalMissing": "NULL_CENSORED",
            "labelSideOnly": True,
        },
        "preprocessing": {
            "categorical": "EXPLICIT_UNKNOWN_THEN_TRAIN_FOLD_ONE_HOT_HANDLE_UNKNOWN_IGNORE",
            "numeric": "TRAIN_FOLD_MEDIAN_IMPUTATION_PLUS_MISSING_INDICATOR",
            "ridgeScaling": "STANDARD_SCALER_FIT_ON_TRAIN_FOLD_AFTER_IMPUTATION",
            "hgbScaling": "NONE",
            "targetSpecificFitRows": True,
            "labelImputation": False,
        },
        "weights": {
            "formulaBeforeRescale": "1/(TRAIN_SESSION_COUNT * TARGET_ELIGIBLE_OPPORTUNITIES_IN_SESSION * TARGET_ELIGIBLE_ROWS_IN_OPPORTUNITY_ARM_SEQUENCE)",
            "estimatorRescale": "MULTIPLY_ALL_TARGET_HEAD_WEIGHTS_SO_MEAN_WEIGHT_EQUALS_1",
            "reason": "PRESERVE_R25_HIERARCHICAL_EQUALIZATION_WITH_CONVENTIONAL_ALPHA_SCALE",
        },
        "fitReuse": {
            "predictionSpecs": prediction_specs(),
            "predictionSpecCount": 6,
            "headsPerSpecPerArmFold": 3,
            "modelFitsTotal": 6*3*len(ARMS)*4,
            "policyConfigurations": 24,
            "rule": "THRESHOLD_AND_PERSISTENCE_SHARE_THE_IDENTICAL_FITTED_PREDICTIONS;_ALL_24_POLICIES_STILL_REPLAY_AND_SCORE_SEPARATELY",
        },
        "decisionFreshness": {
            "freshCurrentObservation": "R20_POSITION_FRESH_CLOSED_PRICE_IS_TRUE",
            "missingOrStale": "HOLD_NO_ACTION_AND_DO_NOT_ADVANCE_PERSISTENCE",
            "freshConditionFalse": "RESET_CONSECUTIVE_EXIT_CONDITION_TO_ZERO",
            "freshConditionTrue": "INCREMENT_CONSECUTIVE_EXIT_CONDITION",
            "failedExecutionReference": "NO_QUEUED_INTENT;_REEVALUATE_NEXT_FRESH_CHECKPOINT",
        },
        "selection": base["selection"],
        "searchBudget": base["searchBudget"],
        "exposureAtFreeze": {
            "modelFits": 0,
            "candidatePerformanceInspected": False,
            "candidateWinnerSelected": False,
            "providerRequests": 0,
            "protectedPartitionsOpened": 0,
        },
        "safety": {k: False for k in (
            "executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed",
            "rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed",
            "automaticPromotionAllowed","productionUpdateAllowed","transmitted")},
    }


if __name__ == "__main__":
    print(json.dumps(contract(), sort_keys=True, separators=(",", ":")))
