"""Offline test of the actual-reference review queue. No Excel, no models, no orders."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

TARGET = Path(__file__).resolve().parents[1] / "tools" / "no11_review_queue_from_actual_rss.py"
SPEC = importlib.util.spec_from_file_location("no11_actual_reference_queue", TARGET)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

DAY = "2026-10-27"
PRIOR = "2026-10-26"
CODES = ["7203.T", "6758.T"]
PLAN_SHA = "a" * 64
MASK_PLAN = "b" * 64


def sources():
    plan = {
        "schemaId": "ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1",
        "productionReady": False,
        "orderTransmission": False,
        "chartPlan": {
            "schemaId": "ARK_NO11_G1_PASS_CHART50_SHADOW_CAPACITY_V1",
            "sessionDate": DAY,
            "asOfSession": PRIOR,
            "sourcePlanId": MASK_PLAN,
            "planSha256": PLAN_SHA,
            "selectorInputSymbols": CODES,
            "productionReady": False,
            "orderTransmission": False,
        },
    }
    mask = {
        "schemaId": "ARK_NO11_DAILY_OBSERVED_PASS_ONLY_SHADOW_V1",
        "asOfSession": PRIOR,
        "planId": MASK_PLAN,
        "observedPassSymbols": CODES,
        "observedPassCount": 2,
        "shadowOnly": True,
        "strictNoUnknownFallback": True,
        "productionReady": False,
        "orderTransmission": False,
    }
    reference = {
        "schemaId": "ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1",
        "source": "RssMarket_SELECTED_REFERENCE_READONLY",
        "sessionDate": DAY,
        "capturedAtJst": DAY + "T10:21:01.000+09:00",
        "completedAtJst": DAY + "T10:21:02.000+09:00",
        "chartPlanSha256": PLAN_SHA,
        "selectedSymbols": CODES,
        "rows": [
            {"symbol": c, "marketCode": "T", "marketDate": DAY,
             "previousDate": PRIOR, "previousClose": 100.0,
             "dayBasePrice": 100.0, "marketSection": "東証P",
             "lotShares": 100, "exRightsDateRaw": "",
             "exDividendDateRaw": "", "interimExDividendDateRaw": ""}
            for c in CODES
        ],
        "corporateActionReviewPerformed": False,
        "readOnly": True,
        "productionReady": False,
        "orderTransmission": False,
    }
    return plan, mask, reference


class ReviewQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.plan, self.mask, self.reference = sources()
        self.raw = (json.dumps(self.reference, ensure_ascii=False,
                               separators=(",", ":")) + "\n").encode()
        self.ref = self.folder / ("session-reference-" +
                                  hashlib.sha256(self.raw).hexdigest() + ".json")
        self.ref.write_bytes(self.raw)

    def build(self):
        return MODULE.build_queue(self.reference, self.raw, self.ref,
                                  self.plan, self.mask)

    def test_real_reference_fields_never_certify_third_party_review(self):
        record = self.build()
        self.assertEqual(record["selectedCount"], 2)
        self.assertEqual(record["rssReferenceFieldsPresent"], 2)
        self.assertEqual(record["independentlyClearedCount"], 0)
        self.assertFalse(record["corporateActionReviewPerformed"])
        self.assertFalse(record["datedMasterCreated"])
        self.assertFalse(record["fullIntegratedShadowAuthorized"])
        self.assertFalse(record["orderTransmission"])
        self.assertEqual(record["status"],
                         "REQUIRES_INDEPENDENT_EXTERNAL_DOCUMENT_REVIEW")
        for row in record["rows"]:
            self.assertEqual(row["reviewStatus"], "NOT_REVIEWED")
            self.assertIsNone(row["corporateActionsCleared"])
            self.assertIsNone(row["priceBasisVerified"])
            self.assertIsNone(row["commonEquity"])
            self.assertIsNone(row["reviewedPreviousClose"])
            self.assertEqual(row["sourceDocumentSha256"], [])
            self.assertFalse(row["approvedForDatedMaster"])
        filename = MODULE.immutable(self.folder, record)
        self.assertEqual(filename, MODULE.immutable(self.folder, record))
        self.assertEqual(
            hashlib.sha256(filename.read_bytes()).hexdigest(),
            filename.stem.split("-")[-1],
        )

    def test_fullwidth_market_labels_are_present_not_independently_reviewed(self):
        for market, valid in [('東証Ｐ', True), ('東証Ｓ', True), ('東証Ｇ', True),
                              ('東証Ｘ', False), ('東証プライム', False)]:
            self.reference['rows'][0]['marketSection'] = market
            self.raw = (json.dumps(self.reference, ensure_ascii=False,
                                   separators=(",", ":")) + "\n").encode()
            self.ref = self.folder / ("session-reference-" +
                                      hashlib.sha256(self.raw).hexdigest() + ".json")
            result = self.build()
            self.assertEqual(result['rssReferenceFieldsPresent'], 2 if valid else 1)
            self.assertEqual(result['rows'][0]['actualRssObservation']['marketSection'], market)
            self.assertEqual(result['independentlyClearedCount'], 0)
            self.assertFalse(result['datedMasterCreated'])
            self.assertFalse(result['fullIntegratedShadowAuthorized'])
            self.assertFalse(result['orderTransmission'])

    def test_missing_vendor_price_never_becomes_zero_or_verified(self):
        self.reference["rows"][0]["previousClose"] = None
        self.raw = json.dumps(self.reference).encode()
        self.ref = self.folder / ("session-reference-" +
                                  hashlib.sha256(self.raw).hexdigest() + ".json")
        result = self.build()
        self.assertEqual(result["rssReferenceFieldsMissing"], 1)
        self.assertFalse(result["sourcePriceBasisCertified"])

    def test_changed_reference_content_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "IMMUTABLE_REFERENCE_SHA256_MISMATCH"):
            MODULE.build_queue(self.reference, self.raw + b"x", self.ref,
                               self.plan, self.mask)

    def test_reviewed_flag_fails_closed(self):
        self.reference["corporateActionReviewPerformed"] = True
        with self.assertRaisesRegex(ValueError, "REFERENCE_SCOPE_MODE_OR_DATE_INVALID"):
            self.build()

    def test_wrong_session_or_plan_identity_fails_closed(self):
        self.plan["chartPlan"]["sessionDate"] = PRIOR
        with self.assertRaisesRegex(ValueError, "PRIVATE_CHART_PLAN_REQUIRED"):
            self.build()
        self.plan, self.mask, self.reference = sources()
        self.mask["planId"] = "z" * 64
        with self.assertRaisesRegex(ValueError, "G1_DAY_OR_MEMBERSHIP_INVALID"):
            self.build()

    def test_unknown_symbol_not_accepted(self):
        self.reference["rows"][1]["symbol"] = "9999.T"
        with self.assertRaisesRegex(ValueError, "REFERENCE_ROW_MEMBERSHIP_OR_ORDER_INVALID"):
            self.build()


if __name__ == "__main__":
    unittest.main()
