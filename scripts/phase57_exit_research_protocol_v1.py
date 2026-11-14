"""R25 finite NEW EXIT Development protocol preregistration.

This file enumerates the entire allowed search before any candidate fit or
performance inspection.  It contains no estimator import and performs no fit.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "docs/evidence/phase57-entry-timing-signal-census-v1/protocol.json"
COHORT_SHA256 = "6b02b3088dd8ea7f8ce53112bc276df442bae3ce0716b8139c92733be4de2994"
ENTRY_FREEZE = "4878a1cc53430e816261dea0fb16aeb53b3c238d"
ARMS = ("IMMEDIATE", "ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF")


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def development_sessions() -> list[str]:
    require(hashlib.sha256(COHORT.read_bytes()).hexdigest() == COHORT_SHA256,
            "COHORT_PROTOCOL_SHA")
    protocol = json.loads(COHORT.read_text())
    ids = protocol["opportunityIds"]
    require(len(ids) == len(set(ids)) == 2155, "COHORT_NOT_2155")
    sessions = sorted({oid.split("|", 1)[0] for oid in ids})
    require(len(sessions) == 58 and sessions[0] == "2025-05-30" and sessions[-1] == "2025-08-25",
            "DEVELOPMENT_SESSION_DRIFT")
    return sessions


def folds() -> list[dict]:
    sessions = development_sessions()
    specifications = ((22, 8), (30, 8), (38, 8), (46, 10))
    output = []
    scored = []
    for index, (train_count, score_count) in enumerate(specifications, 1):
        train = sessions[:train_count]
        purge = sessions[train_count:train_count + 2]
        score = sessions[train_count + 2:train_count + 2 + score_count]
        require(len(purge) == 2 and len(score) == score_count, "FOLD_LENGTH")
        require(set(train).isdisjoint(purge + score) and set(purge).isdisjoint(score),
                "FOLD_OVERLAP")
        output.append({"fold": index, "train": train, "purge": purge, "score": score})
        scored.extend(score)
    require(len(scored) == len(set(scored)) == 34 and scored == sessions[24:],
            "OOF_SCORE_COVERAGE")
    return output


def candidate_grid() -> list[dict]:
    configs = []
    for feature_set, alpha, threshold, persistence in itertools.product(
            ("CORE", "CORE_PLUS_CURATED_PATTERN"), (1.0, 10.0), (0.0, 0.10), (1, 2)):
        configs.append({
            "family": "RIDGE_THREE_INDEPENDENT_HORIZON_HEADS",
            "featureSet": feature_set,
            "alpha": alpha,
            "exitThresholdPp": threshold,
            "persistenceFreshCheckpoints": persistence,
        })
    for leaves, threshold, persistence in itertools.product((7, 15), (0.0, 0.10), (1, 2)):
        configs.append({
            "family": "HIST_GRADIENT_BOOSTING_THREE_HEADS",
            "featureSet": "CORE_PLUS_CURATED_PATTERN",
            "maxLeafNodes": leaves,
            "learningRate": 0.05,
            "maxIter": 100,
            "minSamplesLeaf": 50,
            "l2Regularization": 1.0,
            "randomSeed": 5757,
            "exitThresholdPp": threshold,
            "persistenceFreshCheckpoints": persistence,
        })
    require(len(configs) == 24 and len({json.dumps(x, sort_keys=True) for x in configs}) == 24,
            "CANDIDATE_GRID_NOT_24")
    for index, config in enumerate(configs, 1):
        config["candidateId"] = f"NEW_EXIT_PRECOMMITTED_{index:02d}"
    return configs


def contract() -> dict:
    fold_rows = folds()
    candidates = candidate_grid()
    return {
        "schemaVersion": "phase57-new-exit-finite-research-protocol-r25",
        "entryFreeze": ENTRY_FREEZE,
        "entryArms": list(ARMS),
        "objective": "MAXIMIZE_CAUSAL_ENTRY_TO_EXIT_VALUE_WITH_WINNER_CONTINUATION_PROFIT_RETENTION_AND_LOSS_CONTAINMENT_SEPARATE",
        "decisionMeaning": "IS_SELECTOR_PLUS_ENTRY_UPSIDE_THESIS_STILL_ALIVE_AT_NOW",
        "labels": {
            "type": "TRAINING_ONLY_FUTURE_INCREMENTAL_HOLD_VALUE_PERCENTAGE_POINTS",
            "exitNowReference": "EXACT_NEXT_SCHEDULED_CONTINUOUS_OPEN_AFTER_DECISION_NOW",
            "hold5": "EXACT_OPEN_AFTER_FIVE_ADDITIONAL_ACTIVE_1M_BARS_VS_EXIT_NOW_REFERENCE",
            "hold15": "EXACT_OPEN_AFTER_FIFTEEN_ADDITIONAL_ACTIVE_1M_BARS_VS_EXIT_NOW_REFERENCE",
            "holdTerminal": "EXACT_15:30_ENDPOINT_STAMPED_AUCTION_VS_EXIT_NOW_REFERENCE",
            "formula": "100*(FUTURE_SELL_REFERENCE/EXIT_NOW_SELL_REFERENCE-1)",
            "cost": "SAME_SELL_COST_CANCELS_IN_INCREMENTAL_LABEL;_SCORECARD_APPLIES_EXPLICIT_COST",
            "missing": "TARGET_NULL_AND_CENSORED_NEVER_ZERO_NEVER_FORWARD_SEARCHED",
            "auxiliaryAuditOnly": ["futureUpside", "futureAdverseMove"],
            "neverDecisionFeatures": True,
        },
        "featureSets": {
            "CORE": "R20_STATE_V3_SIX_SIGNALS_ENTRY_TO_NOW_HISTORY_QUALITY_AND_MISSINGNESS",
            "CORE_PLUS_CURATED_PATTERN": "CORE_PLUS_EXACT_187_R23_COLUMNS",
            "blocked": ["R23_30_PRIOR_DAILY_COLUMNS", "ALL_FUTURE_GEOMETRY",
                        "DICTIONARY_OUTCOMES", "OLD_EXIT_OUTPUTS"],
            "all476AtOnce": False,
        },
        "split": {
            "kind": "FOUR_EXPANDING_WALK_FORWARD_SESSION_GROUPED",
            "folds": fold_rows,
            "purgeSessionsBetweenTrainAndScore": 2,
            "randomRowSplit": False,
            "grouping": "WHOLE_SESSION_OPPORTUNITY_ENTRY_ARM_SEQUENCE",
            "scoreSessions": 34,
            "developmentSessions": 58,
            "sameHyperparametersRequiredAcrossArms": True,
            "separateModelFitPerArmAndFold": True,
        },
        "preprocessing": {
            "fitOnTrainingSessionsOnly": True,
            "categorical": "EXPLICIT_UNKNOWN_LEVEL_NOT_FALSE",
            "numeric": "TRAIN_MEDIAN_PLUS_MISSING_INDICATOR",
            "scaling": "TRAIN_ONLY_STANDARDIZATION_FOR_RIDGE;_NONE_FOR_HGB",
            "weights": "EQUAL_SESSION_THEN_EQUAL_OPPORTUNITY_THEN_SEQUENCE_WEIGHT_SUMS_TO_ONE",
            "targetMissingness": "EACH_HEAD_FITS_ONLY_ROWS_WITH_ITS_TARGET;_NO_LABEL_IMPUTATION;_COUNTS_REPORTED",
            "noOutcomeCompleteCaseSelection": True,
        },
        "decisionMapping": {
            "thesisAliveScorePp": "MAX(PREDICTED_HOLD5,HOLD15,HOLD_TERMINAL)",
            "exitCondition": "SCORE_LE_EXIT_THRESHOLD_FOR_PRECOMMITTED_CONSECUTIVE_FRESH_CHECKPOINTS",
            "missingPredictionOrCurrentObservation": "HOLD_NO_ACTION_NOT_SELL_NOT_IMPUTED",
            "execution": "R24_EXACT_NEXT_SCHEDULED_OPEN_OR_NO_FILL_AND_REEVALUATE",
            "terminal": "R24_FORCED_AUCTION_OR_UNRESOLVED",
            "conceptualStateNamesAreNotPolicyClasses": True,
        },
        "models": {
            "grid": candidates,
            "candidateConfigurations": len(candidates),
            "ridgeConfigurations": sum(c["family"].startswith("RIDGE_THREE") for c in candidates),
            "hgbConfigurations": sum(c["family"].startswith("HIST_GRADIENT") for c in candidates),
            "diagnosticNonSelectableReferences": ["HOLD_TO_TERMINAL", "EXIT_FIRST_AVAILABLE_REFERENCE"],
            "retiredExitReferences": [],
        },
        "selection": {
            "scope": "ALL_24_COMPLETE_BEFORE_ANY_WINNER_DECLARATION",
            "hardCoverage": "RESOLVED_EXIT_AT_LEAST_95_PERCENT_OF_FILLED_ENTRIES_IN_EACH_ARM;_ALL_MISSING_CENSORED_REPORTED",
            "referenceComparisonDenominator": "CANDIDATE_VS_NEUTRAL_REFERENCE_IS_PAIRED_ON_SAME_OPPORTUNITY_IDS_AND_SPECIFIC_METRIC",
            "winnerContinuationGate": {
                "aggregateBothArms": ">=5%_MEDIAN_POST_ENTRY_CAPTURE_NOT_MORE_THAN_10PP_BELOW_HOLD_TO_TERMINAL",
                "earlyExit": ">=5%_MEDIAN_EARLY_EXIT_COST_NOT_MORE_THAN_0.25PP_ABOVE_HOLD_TO_TERMINAL",
                "foldRobustness": "AT_LEAST_3_OF_4_FOLDS_PER_ARM_MEET_NONINFERIORITY",
            },
            "profitRetentionGate": {
                "aggregateBothArms": "MEDIAN_CERTIFIED_OWNED_PEAK_GIVEBACK_NOT_MORE_THAN_0.10PP_ABOVE_HOLD_TO_TERMINAL",
                "improvement": "AT_LEAST_2_OF_4_FOLDS_PER_ARM_IMPROVE_GIVEBACK_BY_AT_LEAST_0.10PP",
            },
            "lossContainmentGate": {
                "aggregateBothArms": "P05_NET_AT_LEAST_0.25PP_ABOVE_HOLD_TO_TERMINAL_AND_WORST_NOT_MORE_THAN_0.25PP_WORSE",
                "foldRobustness": "AT_LEAST_3_OF_4_FOLDS_PER_ARM_P10_NOT_WORSE_THAN_HOLD_TO_TERMINAL",
            },
            "netCostGate": "PF_GE_1.00_AT_0.10PP_SELL_COST_AND_PF_GE_0.95_AT_0.20PP_IN_BOTH_ARMS",
            "concentrationGate": {
                "largestTradeSharePositivePnlMax": 0.25,
                "topFiveTradeSharePositivePnlMax": 0.50,
                "largestSessionSharePositivePnlMax": 0.35,
                "nonPositiveAggregatePositivePnl": "FAIL_UNDEFINED_SHARE",
            },
            "reproducibilityGate": "RUN_A_AND_B_BYTE_IDENTICAL_INPUTS_DECISIONS_SCORECARD_AND_RANKING",
            "rankingAfterGates": "MINIMIZE_WORST_OF_THREE_CAPABILITY_RANKS_THEN_SUM_OF_RANKS",
            "tiePolicy": "EXACT_TIE_MEANS_NO_SELECTION_NOT_MANUAL_CHOICE",
            "winRateAloneCanSelect": False,
        },
        "searchBudget": {
            "maximumCandidateConfigurations": 24,
            "maximumFeatureSets": 2,
            "maximumModelFamilies": 2,
            "folds": 4,
            "entryArms": 2,
            "adaptiveFeatureThresholdModelAddition": False,
            "stoppingRule": "AFTER_24_CONFIGS_SELECT_ONE_ONLY_IF_ALL_GATES_PASS_ELSE_NO_SELECTION_STOP",
            "noPassAction": "NO_SELECTION_STOP_AND_NEW_PRECOMMIT_REQUIRED_BEFORE_ANY_FURTHER_SEARCH",
        },
        "dataBoundary": {
            "cohort": "2155_OUTCOME_EXPOSED_DEVELOPMENT",
            "newProtectedPartitionsOpened": 0,
            "providerRequests": 0,
            "freshOosClaims": False,
        },
        "status": {
            "modelFits": 0,
            "candidatePerformanceInspected": False,
            "candidateWinnerSelected": False,
            "exitFrozen": False,
        },
    }


if __name__ == "__main__":
    print(json.dumps(contract(), sort_keys=True, separators=(",", ":")))
