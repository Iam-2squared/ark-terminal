"""STEP 1 static contract checks only; deliberately no State v3 classifier."""
import hashlib
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/phase57-state-v3-9pattern"


class ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((EVIDENCE / "CONTRACT.json").read_text(encoding="utf-8"))
        cls.prose = (EVIDENCE / "CONTRACT.md").read_text(encoding="utf-8")

    def test_nine_stable_unique_patterns(self):
        c = self.contract
        self.assertEqual(len(c["patternIds"]), len(set(c["patternIds"])))
        self.assertEqual(len(c["patternIds"]), len(c["japaneseNames"]))
        self.assertEqual(len(c["patternIds"]), 9)
        self.assertNotIn("UNKNOWN", c["patternIds"])
        self.assertNotIn("INVALID", c["patternIds"])
        for identifier, name in zip(c["patternIds"], c["japaneseNames"]):
            self.assertIn(identifier, self.prose)
            self.assertIn(name, self.prose)

    def test_all_prior_recent_direction_cells_and_resolutions(self):
        c = self.contract
        self.assertEqual(c["directions"], [-1, 0, 1])
        matrix = c["baseDecisionMatrix"]
        self.assertEqual(set(matrix), {"priorMinus", "priorZero", "priorPlus"})
        for row in matrix.values():
            self.assertEqual(set(row), {"recentMinus", "recentZero", "recentPlus"})
            for resolution in row.values():
                self.assertTrue(set(resolution.split("_OR_")).issubset(c["patternIds"]))
        self.assertEqual(len(c["decisionOrder"]), 5)
        self.assertEqual(c["oppositionEquality"], "fullReversalNotPartial")
        self.assertEqual(c["thresholdEquality"], "directionShockAndStopInclusive")

    def test_causal_bar_and_forbidden_inputs(self):
        c = self.contract["input"]
        self.assertTrue(c["closedBarEndLteAsOf"] and c["publicationTimeLteAsOf"])
        for key in ("overnightGapExcludedFromDirection", "lunchRecessExcludedFromActiveMinutes", "missingBarIsNotNoTrade", "pivotAvailabilityNeverBackdated"):
            self.assertTrue(c[key])
        self.assertIn("future_resolution_v2", c["forbidden"])
        self.assertIn("oracleLow", c["forbidden"])
        self.assertIn("outcome", c["forbidden"])
        self.assertIn("volume", c["forbidden"])
        self.assertTrue(set(c["allowed"]).isdisjoint(c["forbidden"]))

    def test_missing_is_separate_from_state(self):
        c = self.contract
        self.assertIsNone(c["invalidState"])
        self.assertEqual(c["invalidStateStatus"], "NOT_COMPUTED")
        self.assertEqual(c["dataQuality"], ["OK", "DEGRADED", "INVALID"])
        self.assertEqual(c["confidence"], ["HIGH", "MEDIUM", "LOW", "NOT_ASSESSED"])
        self.assertIn("one-anchor", self.prose)
        self.assertIn("stale", self.prose)

    def test_separation_and_normalization_fixed(self):
        c = self.contract
        self.assertEqual(c["normalization"]["recentActiveMinutes"], 10)
        self.assertEqual(c["normalization"]["shockThresholdUnits"], 3)
        self.assertEqual(c["normalization"]["unitFallback"], "log(1.001)")
        self.assertFalse(c["volumeLayer"]["implemented"])
        self.assertFalse(c["volumeLayer"]["mayModifyPriceState"])
        for pair in ("RISE_STOP", "PULLBACK", "DROP_STOP", "REBOUND", "SHARP_RISE", "SHARP_DROP"):
            self.assertIn(pair, self.prose)

    def test_scope_and_safety(self):
        c = self.contract
        self.assertEqual(len(c["safety"]), 9)
        self.assertTrue(all(value is False for value in c["safety"].values()))
        self.assertFalse(c["step1"]["classifierImplemented"])
        self.assertFalse(c["step1"]["populationApplied"])
        self.assertFalse(c["step1"]["entryEvaluated"])
        self.assertEqual(c["step1"]["providerRequests"], 0)
        self.assertFalse(c["step1"]["protectedHoldoutOpened"])

    def test_manifest_content_hashes(self):
        manifest_path = EVIDENCE / "MANIFEST.json"
        if not manifest_path.exists():
            self.skipTest("manifest created at freeze commit preparation")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for path, expected in manifest["sha256"].items():
            item = ROOT / path
            self.assertEqual(hashlib.sha256(item.read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
