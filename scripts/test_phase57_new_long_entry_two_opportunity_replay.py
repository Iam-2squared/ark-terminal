import unittest

from scripts.phase57_new_long_entry_two_opportunity_replay import replay


class TwoOpportunityEntryReplayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger, cls.summary = replay()

    def test_anchor_identity_and_primary_population_are_preserved(self):
        s = self.summary
        self.assertEqual(s["fullAnchors"], 2743)
        self.assertEqual(s["anchorIdentitySHA256"], "985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121")
        self.assertEqual(s["primary60"], 878)
        self.assertEqual(s["primarySymbols"], 430)
        self.assertEqual(s["primarySessions"], 76)
        self.assertEqual(s["primaryFirstClosedDip"], 328)
        self.assertEqual(s["primaryNoFirstClosedDip"], 550)
        self.assertEqual(s["primarySecondaryResolved"], 328)
        self.assertEqual(s["primaryPaired"], 328)
        self.assertEqual(s["primaryStateCounts"], {
            "DIP_REPRICE_EMITTED": 328,
            "FIRST_BAR_CONTINUATION": 550,
        })

    def test_full_first_close_census_matches_saved_location_study(self):
        self.assertEqual(self.summary["fullFirstCloseCohortCounts"], {
            "FIRST_CLOSED_DIP": 580,
            "NO_FIRST_CLOSED_DIP": 1327,
            "UNKNOWN": 836,
        })
        self.assertEqual(self.summary["initialReferenceStates"], {
            "EXPIRED_BOUNDARY": 353,
            "REFERENCE_OPEN": 1907,
            "UNKNOWN_REFERENCE_OPEN": 483,
        })

    def test_dip_reprice_metrics_reproduce_location_study(self):
        p = self.summary["dipRepriceParity"]
        self.assertAlmostEqual(p["buyImprovementPct"]["mean"], 1.1184, places=4)
        self.assertAlmostEqual(p["buyImprovementPct"]["median"], 0.8002, places=4)
        self.assertAlmostEqual(p["initialD30Downside"]["mean"], 2.8980, places=4)
        self.assertAlmostEqual(p["secondaryD30Downside"]["mean"], 1.8911, places=4)
        self.assertAlmostEqual(p["initialCommon60Upside"]["mean"], 1.6876, places=4)
        self.assertAlmostEqual(p["secondaryCommon60Upside"]["mean"], 2.4291, places=4)
        self.assertEqual(p["capture3"]["denominator"], 59)
        self.assertEqual(p["capture3"]["hits"], 56)
        self.assertEqual(p["capture5"]["denominator"], 21)
        self.assertEqual(p["capture5"]["hits"], 21)

    def test_decision_payload_is_separate_from_evaluator_outcomes(self):
        for row in self.ledger:
            decision = repr(row["decision"]).lower()
            for forbidden in ("d30", "common60", "futurehigh", "futurelow", "profit", "notional", "quantity\":"):
                self.assertNotIn(forbidden, decision)
        inputs = self.summary["decisionInputs"]
        self.assertFalse(inputs["futureHighLowUsed"])
        self.assertFalse(inputs["outcomeUsed"])
        self.assertFalse(inputs["quantityOwnedByEntry"])

    def test_safety_and_scope_remain_closed(self):
        s = self.summary
        self.assertEqual(s["modelFits"], 0)
        self.assertEqual(s["modelPredictions"], 0)
        self.assertEqual(s["freshAccess"], 0)
        self.assertEqual(s["oosAccess"], 0)
        self.assertEqual(s["providerRequests"], 0)
        self.assertEqual(s["minuteResearchRuns"], 0)
        self.assertEqual(s["exitEvaluations"], 0)
        self.assertEqual(s["capitalEvaluations"], 0)
        self.assertEqual(s["portfolioEvaluations"], 0)
        self.assertFalse(s["mainMerge"])
        self.assertTrue(all(value is False for value in s["safety"].values()))


if __name__ == "__main__":
    unittest.main()
