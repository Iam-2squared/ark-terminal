"""Offline contract tests. No private P1/H235 weights are in GitHub CI."""
import ast
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "tools/no11_parallel_original_inference_smoke.py"
SPEC = importlib.util.spec_from_file_location("no11_parallel_original_inference_smoke", SCRIPT)
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class SyntheticOriginalInferenceContract(unittest.TestCase):
    def test_parser_and_fixture(self):
        ast.parse(SCRIPT.read_text(encoding="utf-8"))
        row = PROBE.synthetic_h235_input("2026-10-27")
        self.assertEqual(row["stateTrace"][0]["bar_end_minute"], 569)
        self.assertEqual(row["stateTrace"][-1]["bar_end_minute"], 571)
        self.assertEqual(row["selectorFirstAtJst"], "2026-10-27T09:30:00+09:00")
        self.assertEqual(row["decisionAtJst"], "2026-10-27T09:31:12+09:00")
        self.assertFalse(row["orderTransmission"])
        self.assertFalse(row["productionReady"])
        with self.assertRaisesRegex(ValueError, "SYNTHETIC_SYMBOL_INVALID"):
            PROBE.synthetic_h235_input("2026-10-27", 'bad";evil')

    def test_true_model_result_must_include_verified_head_count_and_order_guards(self):
        result = {
            "schemaId": "ARK_NO11_H235_RECEIVED_ASOF_R0_V1",
            "sessionDate": "2026-10-27",
            "selectedBlock": 8,
            "originalFrozenModelFilesVerified": 24,
            "originalModelsExecuted": 3,
            "newFits": 0,
            "sourceKind": "RSS_CUMULATIVE_PROXY",
            "shadowOnly": True,
            "productionReady": False,
            "orderTransmission": False,
            "orderAuthorized": False,
            "capitalExecutionAuthorized": False,
            "changedFeatureSemantics": True,
            "modelInputOriginalHistoricalParity": False,
            "ML": 1.25,
            "rank": "B",
        }
        PROBE.validate_h235_output(result, "2026-10-27")
        for field, value in (
            ("originalFrozenModelFilesVerified", 23),
            ("originalModelsExecuted", 2),
            ("newFits", 1),
            ("orderTransmission", True),
            ("capitalExecutionAuthorized", True),
            ("sourceKind", "BROKER_FILL"),
        ):
            with self.subTest(field=field):
                altered = dict(result, **{field: value})
                with self.assertRaisesRegex(ValueError, "H235_INFERENCE_OUTPUT_INVALID"):
                    PROBE.validate_h235_output(altered, "2026-10-27")

    def test_true_p1_output_cannot_be_fabricated(self):
        a = {
            "score": 0.6,
            "headPredictions": [0.0, 1.0, 2.0],
            "headPercentiles": [0.2, 0.6, 0.4],
            "unseenCategoryCounts": [0] * 15,
        }
        PROBE.validate_p1_output(a)
        for field, wrong in (
            ("score", float("nan")),
            ("score", 1.1),
            ("headPredictions", [0.0]),
            ("headPercentiles", [0.5, -0.1, 0.5]),
            ("unseenCategoryCounts", [0] * 14),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "P1_INFERENCE_OUTPUT_INVALID"):
                    PROBE.validate_p1_output(dict(a, **{field: wrong}))

    def test_no_model_fit_excel_broker_private_scores_or_order_functions(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for phrase in ("FrozenP1Scorer", "FrozenH235AsOf",
                       "p1.score(numeric, categories)", "h235.score(fake)",
                       "NO11_FROZEN_REAL_INFERENCE_TEST_INPUT=SYNTHETIC_ONLY",
                       "NO11_FROZEN_REAL_INFERENCE_REAL_RSS_SELECTOR=False",
                       "NO11_FROZEN_REAL_INFERENCE_PAPER_TRADES=False"):
            self.assertIn(phrase, source)
        for forbidden in ("Excel.Application", "GetActiveObject", "win32com",
                          "RssStockOrder(", "RssCancelOrder(", "RssMarginOpenOrder(",
                          "fit_transform(", ".fit(", "requests.get(", "requests.post(",
                          "urllib.request", "smtplib", "brokerExecutionConfig"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
