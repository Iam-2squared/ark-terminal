"""No11 fullwidth/ASCII market-section contract, no fitted model or RSS access.

Uses the real build_master check with a tiny synthetic, explicitly reviewed
fixture. Passing this test does NOT create or certify real review evidence.
"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import no11_prepare_received_inputs as prep

DAY = "2026-10-27"
PREVIOUS = "2026-10-26"
SYMBOL = "7203.T"
INFO = {"sessionDate": DAY, "previousSession": PREVIOUS,
        "chartPlanSha256": "a" * 64, "selectedSymbols": [SYMBOL]}


def fixtures():
    reference = {
        "schemaId": prep.REFERENCE, "sessionDate": DAY,
        "source": "RssMarket_SELECTED_REFERENCE_READONLY",
        "capturedAtJst": DAY + "T09:00:01+09:00",
        "completedAtJst": DAY + "T09:00:05+09:00",
        "chartPlanSha256": INFO["chartPlanSha256"],
        "selectedSymbols": [SYMBOL],
        "rows": [{"symbol": SYMBOL, "marketCode": "T", "marketDate": DAY,
                  "previousDate": PREVIOUS, "previousClose": 1234.5,
                  "dayBasePrice": 1234.5, "marketSection": "東証Ｐ", "lotShares": 100}],
        "readOnly": True, "productionReady": False, "orderTransmission": False
    }
    evidence = {
        "schemaId": prep.EVIDENCE, "validForSession": DAY,
        "knownAtJst": DAY + "T08:59:55+09:00",
        "reviewStatus": "EXTERNALLY_REVIEWED",
        "rows": [{"symbol": SYMBOL, "segment": "PRIME", "sector": "01",
                  "commonEquity": True, "corporateActionsCleared": True,
                  "priceBasisVerified": True, "reviewedPreviousClose": 1234.5,
                  "sourceDocumentSha256": ["b" * 64]}],
        "productionReady": False, "orderTransmission": False
    }
    return reference, evidence


def build(reference, evidence):
    return prep.build_master(INFO, reference, evidence, reference_sha="c" * 64,
                             evidence_sha="d" * 64,
                             prepared_at=DAY + "T09:01:00+09:00")


class RealInputContractWithoutModels(unittest.TestCase):
    def test_all_six_exact_section_labels_match_only_the_same_reviewed_class(self):
        for raw, segment in [("東証P", "PRIME"), ("東証Ｐ", "PRIME"),
                             ("東証S", "STANDARD"), ("東証Ｓ", "STANDARD"),
                             ("東証G", "GROWTH"), ("東証Ｇ", "GROWTH")]:
            with self.subTest(raw=raw):
                ref, review = fixtures()
                ref["rows"][0]["marketSection"] = raw
                review["rows"][0]["segment"] = segment
                raw_copy = deepcopy(ref)
                master = build(ref, review)
                self.assertEqual(master["rows"][0]["segment"], segment)
                self.assertEqual(ref, raw_copy)
                self.assertFalse(master["productionReady"])
                self.assertFalse(master["orderTransmission"])
                self.assertFalse(master["rssFieldTimestampCertified"])

    def test_raw_fullwidth_prime_must_not_match_reviewed_standard(self):
        ref, review = fixtures()
        review["rows"][0]["segment"] = "STANDARD"
        with self.assertRaisesRegex(ValueError, "RSS_IDENTITY_DATE_OR_CLASS_MISMATCH"):
            build(ref, review)

    def test_unknown_or_fuzzy_labels_are_rejected(self):
        for bad in ("東証Ｘ", "東証プライム", "東証Ｐ ", "東証p", ""):
            ref, review = fixtures()
            ref["rows"][0]["marketSection"] = bad
            with self.assertRaisesRegex(ValueError, "RSS_IDENTITY_DATE_OR_CLASS_MISMATCH"):
                build(ref, review)

    def test_no_external_review_means_no_master_even_with_exact_fullwidth_rss(self):
        for key, value in [("reviewStatus", "NOT_REVIEWED"), ("productionReady", True)]:
            ref, review = fixtures()
            review[key] = value
            with self.assertRaisesRegex(ValueError, "SECURITY_EVIDENCE_REQUIRED"):
                build(ref, review)
        ref, review = fixtures()
        review["rows"][0]["corporateActionsCleared"] = False
        with self.assertRaisesRegex(ValueError, "SECURITY_EVIDENCE_NOT_CONFIRMED"):
            build(ref, review)


if __name__ == "__main__":
    unittest.main()
