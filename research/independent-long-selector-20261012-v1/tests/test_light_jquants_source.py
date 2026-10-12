"""Synthetic-only tests for J-Quants E as-of financial data and native Daily."""
import csv
import gzip
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from light_jquants_source import (
    LightSourceError, exact_asof_numeric_fields, iter_unadjusted_daily_native,
)
from selector_model import authorized_development_split
from selector_core import ContractError


class LightAsOfTests(unittest.TestCase):
    def test_original_daily_ignores_adj_columns_and_prevents_same_session(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"daily.csv.gz"
            with gzip.open(path,"wt",encoding="utf-8",newline="") as f:
                w=csv.writer(f)
                w.writerow(("Date","Code","O","H","L","C","Vo","Va","AdjC"))
                w.writerow(("2025-05-01","13010","100","102","99","101","1000","101000","500"))
            rows=list(iter_unadjusted_daily_native(path))
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]["close"],101)
            self.assertEqual(rows[0]["availableAt"],"2025-05-02T00:00:00+09:00")
            self.assertTrue(rows[0]["futureAdjustedFieldsIgnored"])
            self.assertFalse(rows[0]["historicalActualReceiveTimeVerified"])

    def test_financials_cannot_enter_before_actual_publication(self):
        row={"PublishedEPS":"123.45"}
        fmap={"valuation_eps":"PublishedEPS"}
        prov={"pitPublicationVerified":True,"dataset":"VALUATION",
              "sourceObjectKey":"synthetic-only"}
        early,missing=exact_asof_numeric_fields(
            row,fieldmap=fmap,publication_at="2025-05-01T15:20:00+09:00",
            decision_at="2025-05-01T14:00:00+09:00",provenance=prov)
        self.assertEqual(early,{})
        self.assertEqual(missing["valuation_eps"],"NOT_YET_PUBLIC_AT_DECISION")
        late,missing=exact_asof_numeric_fields(
            row,fieldmap=fmap,publication_at="2025-05-01T15:20:00+09:00",
            decision_at="2025-05-02T09:30:00+09:00",provenance=prov)
        self.assertEqual(late["valuation_eps"]["value"],123.45)
        self.assertTrue(late["valuation_eps"]["pitVerified"])

    def test_unknown_provenance_stays_unknown(self):
        extras,missing=exact_asof_numeric_fields(
            {"Amount":"999"},fieldmap={"fin_sales":"Amount"},
            publication_at="2025-05-01T01:00:00+09:00",
            decision_at="2025-05-02T09:30:00+09:00",
            provenance={"pitPublicationVerified":False})
        self.assertEqual(extras,{})
        self.assertEqual(missing["fin_sales"],"UNKNOWN_PUBLICATION_TIME")

    def test_protected_holdout_rejected_by_fixed_split(self):
        dates=[]
        import datetime
        start=datetime.date(2024,10,1)
        for n in range(365):
            d=start+datetime.timedelta(days=n)
            dates.append({"session":d.isoformat()})
        groups=authorized_development_split(dates)
        self.assertGreater(len(groups["fit"]),10)
        self.assertGreater(len(groups["select"]),10)
        self.assertGreater(len(groups["report"]),10)
        dates.append({"session":"2025-10-01"})
        with self.assertRaisesRegex(ContractError,"SEALED_HOLDOUT"):
            authorized_development_split(dates)


if __name__=="__main__":
    unittest.main()
