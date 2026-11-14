"""Offline-only tests of optional, permission-gated Yahoo weekly importer."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

MODULE=Path(__file__).resolve().parents[1]/"tools"/"no11_yahoo_weekly_history.py"
SPEC=spec_from_file_location("no11_yahoo_weekly_history",MODULE)
Y=module_from_spec(SPEC)
SPEC.loader.exec_module(Y)

class YahooWeeklyHistoryTests(unittest.TestCase):
    def test_safeguards_and_raw_close_decimal(self):
        self.assertEqual(Y.decimal("1234.50"),"1234.50")
        self.assertIsNone(Y.decimal(-1))
        self.assertIsNone(Y.decimal("nan"))
        self.assertIsNone(Y.decimal("inf"))
        self.assertIsNone(Y.decimal(0))
        self.assertEqual(Y.decimal("0",allow_zero=True),"0")
    def test_exact_csv_dates_and_no_partial_today_row(self):
        a=[{"session":"2026-10-22","close":"100.2"},
           {"session":"2026-10-23","close":"100.5"},
           {"session":"2026-10-28","close":"99999"}]
        rows=Y.normalized_rows(a,"2026-10-23")
        self.assertEqual([x["session"] for x in rows],["2026-10-22","2026-10-23"])
        with self.assertRaisesRegex(ValueError,"DUPLICATE_DAILY_DATE"):
            Y.normalized_rows(a[:1]+a[:1],"2026-10-23")
        with self.assertRaisesRegex(ValueError,"ROW_DATE_INVALID"):
            Y.normalized_rows([{"session":"2026-02-30","close":"100"}],"2026-10-23")
    def test_local_sha_immutable_and_not_a_broker_signal(self):
        obs=Y.observation("7203.T","2026-10-23",
            [{"session":"2026-10-23","close":"101"}],"OBSERVED",
            "2026-10-23T19:01:00.000+09:00","2026-10-23T19:02:00.000+09:00")
        self.assertFalse(obs["autoAdjustRequested"])
        self.assertFalse(obs["splitAdjustmentCertified"])
        self.assertFalse(obs["corporateActionPriceBasisCertified"])
        self.assertFalse(obs["orderTransmission"])
        with TemporaryDirectory() as root:
            path=Y.write_immutable(Path(root),obs)
            self.assertEqual(path,Y.write_immutable(Path(root),obs))
            self.assertEqual(len(list(Path(root).glob("*.json"))),1)
    def test_express_permission_gate_precedes_market_or_network(self):
        with self.assertRaisesRegex(ValueError,"EXPRESS_YAHOO_AUTOMATED_ACCESS_PERMISSION_REQUIRED"):
            Y.main(["--original-plan","/nonexistent/plan.json",
                    "--asof","2026-10-23","--private-root","/nonexistent",
                    "--personal-research-terms-acknowledged"])
        with self.assertRaisesRegex(ValueError,"PERSONAL_RESEARCH_RIGHTS_ACKNOWLEDGEMENT_REQUIRED"):
            Y.main(["--original-plan","/nonexistent/plan.json",
                    "--asof","2026-10-23","--private-root","/nonexistent"])
if __name__=="__main__":
    unittest.main()
