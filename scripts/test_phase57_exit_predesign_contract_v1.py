from __future__ import annotations

import ast
import unittest
from pathlib import Path

from scripts import phase57_exit_evaluator_contract_v1 as evaluator
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_exit_feature_contract_v1 as feature
from scripts import phase57_exit_research_protocol_v1 as research


class FeatureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = feature.contract()
        cls.rows = cls.contract["patternRegistry"]["rows"]

    def test_registry_is_exact_476(self):
        self.assertEqual(len(self.rows), 476)
        self.assertEqual(len({r["feature"] for r in self.rows}), 476)

    def test_pattern_column_classification_is_exhaustive(self):
        self.assertEqual(self.contract["patternRegistry"]["statusCounts"],
                         {"BLOCKED": 30, "MODEL_ADMITTED": 446})
        self.assertTrue(all(r["status"] in {"MODEL_ADMITTED", "BLOCKED", "EVALUATOR_ONLY"}
                            for r in self.rows))

    def test_prior_daily_columns_are_the_only_blocked_pattern_columns(self):
        blocked = {r["feature"] for r in self.rows if r["status"] == "BLOCKED"}
        self.assertEqual(sum(x.startswith("RECENT/") for x in blocked), 24)
        self.assertEqual(sum(x.startswith(("SIGNAL/PDH", "SIGNAL/PDL")) for x in blocked), 6)

    def test_finite_pattern_subset_is_187_not_all_476(self):
        self.assertEqual(sum(r["selectedInFiniteSearch"] for r in self.rows), 187)
        self.assertTrue(all(r["status"] == "MODEL_ADMITTED"
                            for r in self.rows if r["selectedInFiniteSearch"]))

    def test_selector_join_is_exact_2155_and_sanitized(self):
        audit = self.contract["selectorContext"]
        self.assertEqual((audit["cohort"], audit["missing"], audit["outcomeFieldsProjected"]),
                         (2155, 0, 0))

    def test_state_has_all_nine_and_drop_is_not_exit(self):
        state = self.contract["stateV3"]
        self.assertEqual(len(state["states"]), 9)
        self.assertIn("DROP_OR_NEGATIVE_RETURN_ALONE_MUST_NOT_FORCE_EXIT", state["rule"])

    def test_signals_remain_six_and_unknown_not_false(self):
        signals = self.contract["timingSignals"]
        self.assertEqual(len(signals["families"]), 6)
        self.assertIn("UNKNOWN_NOT_FALSE", signals["status"])

    def test_pattern_now_recomputes_and_removes_blocked(self):
        def bar(m, price):
            return [m, price, price + .4, price - .4, price + .1, 1000 + m, 100000 + m]
        previous = [bar(m, 99 + (m - 540) * .01) for m in range(540, 551)]
        today = [bar(m, 100 + (m - 540) * .02) for m in range(540, 551)]
        result = feature.pattern_now(
            day="2025-06-02", now=551, selector_minute=545,
            selector_origin={"decisionPrice": 100., "savedV1Score": 12., "newEligibleRank": 3},
            today_prefix=today, previous_prefix=previous)
        self.assertEqual(len(result["admitted"]), 446)
        self.assertEqual(len(result["curated"]), 187)
        self.assertEqual(len(result["blocked"]), 30)
        self.assertTrue(all(value is None for value in result["blocked"].values()))

    def test_pattern_now_rejects_future_bar(self):
        row = [551, 100., 101., 99., 100., 1., 100.]
        with self.assertRaisesRegex(ValueError, "PATTERN_TODAY_NOT_CLOSED_AT_NOW"):
            feature.pattern_now(
                day="2025-06-02", now=551, selector_minute=545,
                selector_origin={"decisionPrice": 100., "savedV1Score": 12., "newEligibleRank": 3},
                today_prefix=[row], previous_prefix=[])


class ExecutionContractTests(unittest.TestCase):
    def test_decision_grid_includes_lunch_and_terminal_prepoint(self):
        grid = execution.decision_endpoints("2025-06-02", 600)
        self.assertIn(690, grid)
        self.assertIn(925, grid)
        self.assertNotIn(750, grid)  # 12:30 bar has not completed at 12:30.
        self.assertIn(751, grid)

    def test_lunch_decision_executes_at_1230_open(self):
        self.assertEqual(execution.next_execution_start("2025-06-02", 690), 750)

    def test_regular_decision_executes_at_same_minute_open(self):
        self.assertEqual(execution.next_execution_start("2025-06-02", 601), 601)

    def test_last_decision_has_no_continuous_reference(self):
        self.assertIsNone(execution.next_execution_start("2025-06-02", 925))

    def test_missing_reference_does_not_use_stale_or_queue(self):
        result = execution.ordinary_execution_reference(
            "2025-06-02", 601, [[600, 10, 10, 10, 10, 1, 10]])
        self.assertEqual(result["status"], "MISSING_EXECUTION_REFERENCE")
        self.assertIsNone(result["price"])
        self.assertFalse(result["queuedIntent"])

    def test_exact_reference_resolves(self):
        result = execution.ordinary_execution_reference(
            "2025-06-02", 601, [[601, 10, 11, 9, 10, 1, 10]])
        self.assertEqual(result["price"], 10.)

    def test_terminal_is_exact_single_price_auction(self):
        resolved = execution.terminal_execution_reference([[930, 10, 10, 10, 10, 1, 10]])
        self.assertEqual(resolved["status"], "RESOLVED_TERMINAL_AUCTION")
        self.assertFalse(resolved["censored"])
        missing = execution.terminal_execution_reference([])
        self.assertTrue(missing["censored"])

    def test_terminal_does_not_accept_range_bar(self):
        with self.assertRaisesRegex(ValueError, "AUCTION_NOT_SINGLE_PRICE"):
            execution.terminal_execution_reference([[930, 10, 11, 9, 10, 1, 10]])

    def test_active_time_excludes_lunch(self):
        self.assertEqual(execution.active_minutes("2025-06-02", 689, 751), 2)

    def test_cost_and_safety_are_explicit(self):
        contract = execution.contract()
        self.assertEqual(contract["priceAndCost"]["primarySellCostPp"], .05)
        self.assertTrue(all(value is False for value in contract["safety"].values()))
        self.assertFalse(contract["session"]["overnightAllowed"])


class EvaluatorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = evaluator.canonical_bucket_census()
        cls.scorecard = evaluator.scorecard_contract()

    def test_canonical_geometry_reproduces_all_six_buckets(self):
        self.assertEqual(self.census["buckets"], evaluator.EXPECTED_BUCKETS)
        self.assertEqual(self.census["buckets"][">=5%"], 666)

    def test_bucket_and_missing_accounting(self):
        self.assertEqual(self.census["evaluable"], 2053)
        self.assertEqual(self.census["notEvaluable"], 102)
        self.assertEqual(sum(self.census["buckets"].values()) + self.census["notEvaluable"], 2155)

    def test_not_evaluable_reasons_remain_explicit(self):
        self.assertEqual(self.census["notEvaluableReasons"],
                         dict(sorted(evaluator.EXPECTED_NOT_EVALUABLE.items())))

    def test_terminal_reference_census_is_not_silently_complete(self):
        terminal = self.scorecard["terminalReferenceCensus"]
        self.assertEqual((terminal["auctionReferencePresent"],
                          terminal["auctionReferenceMissing"]), (2092, 63))
        self.assertEqual(terminal["presentSinglePriceOHLC"], 2092)
        self.assertFalse(terminal["policyPerformanceInspected"])

    def test_geometry_is_strictly_ordered_and_has_fixed_horizon(self):
        row = next(r for r in evaluator.records() if r["orderedOracle"].get("rangePct", 0) > 0
                   and r["orderedOracle"].get("fullSessionEvaluable"))
        geometry, reason = evaluator.geometry(row)
        self.assertIsNone(reason)
        self.assertLess(geometry.low_bar_start, geometry.high_bar_start)
        self.assertEqual(geometry.horizon_end, 930)

    def test_endpoint_auction_geometry_uses_same_timestamp_known_at(self):
        row = next(r for r in evaluator.records()
                   if r["orderedOracle"].get("fullSessionEvaluable")
                   and r["orderedOracle"].get("highMinute") == 930
                   and r["orderedOracle"].get("rangePct", 0) > 0)
        geometry, reason = evaluator.geometry(row)
        self.assertIsNone(reason)
        self.assertEqual(geometry.high_bar_start, 930)
        self.assertEqual(geometry.high_available_at(), 930)

    def test_scorecard_has_requested_arms_and_metrics(self):
        self.assertEqual(self.scorecard["entryArms"],
                         ["IMMEDIATE", "ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF"])
        for metric in ("profitFactor", "winRate", "p05P10Worst", "holdingTime",
                       "earlyExitOpportunityCost", "lateExitGiveback"):
            self.assertIn(metric, self.scorecard["metrics"])

    def test_future_high_is_not_owned_giveback(self):
        metrics = self.scorecard["metrics"]
        self.assertIn("NEVER_OWNED_GIVEBACK", metrics["highToExitEvaluatorGapPp"])
        self.assertIn("OWNED_PEAK", metrics["lateExitGiveback"])

    def test_paired_view_requires_same_metric_denominator(self):
        paired = self.scorecard["pairedCommonCase"]
        self.assertIn("SPECIFIC_METRIC", paired["eligibility"])
        self.assertTrue(paired["unpairedRowsNeverCalledPaired"])


class FiniteProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = research.contract()

    def test_four_folds_and_34_unique_oof_sessions(self):
        folds = self.contract["split"]["folds"]
        scored = [day for fold in folds for day in fold["score"]]
        self.assertEqual(len(folds), 4)
        self.assertEqual(len(scored), len(set(scored)))
        self.assertEqual(len(scored), 34)

    def test_two_session_purge_every_fold(self):
        self.assertTrue(all(len(fold["purge"]) == 2 for fold in self.contract["split"]["folds"]))

    def test_candidate_grid_is_finite_24(self):
        models = self.contract["models"]
        self.assertEqual(models["candidateConfigurations"], 24)
        self.assertEqual((models["ridgeConfigurations"], models["hgbConfigurations"]), (16, 8))

    def test_no_retired_exit_reference(self):
        self.assertEqual(self.contract["models"]["retiredExitReferences"], [])

    def test_no_adaptive_search_and_no_pass_stops(self):
        budget = self.contract["searchBudget"]
        self.assertFalse(budget["adaptiveFeatureThresholdModelAddition"])
        self.assertIn("NO_SELECTION_STOP", budget["stoppingRule"])

    def test_all_three_capabilities_gate_selection(self):
        selection = self.contract["selection"]
        for name in ("winnerContinuationGate", "profitRetentionGate", "lossContainmentGate"):
            self.assertIn(name, selection)
        self.assertFalse(selection["winRateAloneCanSelect"])

    def test_candidate_work_has_not_started(self):
        status = self.contract["status"]
        self.assertEqual(status["modelFits"], 0)
        self.assertFalse(status["candidatePerformanceInspected"])
        self.assertFalse(status["candidateWinnerSelected"])

    def test_evaluator_kernel_is_not_imported_by_decision_modules(self):
        for module in (feature, execution):
            tree = ast.parse(Path(module.__file__).read_text())
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any("exit_capture_metrics" in name or "exit_evaluator" in name
                                 for name in imports), module.__name__)


if __name__ == "__main__":
    unittest.main()
