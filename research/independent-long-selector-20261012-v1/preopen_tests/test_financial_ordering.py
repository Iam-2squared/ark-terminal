import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_preopen_native_bundle import latest_financial_record

class FinancialOrdering(unittest.TestCase):
    def test_identifier_cannot_order_simultaneous_distinct_disclosures(self):
        a={'DiscDate':'2024-10-01','DiscTime':'15:00:00','DiscNo':'999','EPS':'100'}
        b={**a,'DiscNo':'001','EPS':'150'}
        self.assertIsNone(latest_financial_record([a,b]))
        self.assertIsNone(latest_financial_record([b,a]))

    def test_chronology_and_exact_payload_duplicates(self):
        a={'DiscDate':'2024-10-01','DiscTime':'15:00:00','DiscNo':'999','EPS':'100'}
        b={**a,'DiscDate':'2024-10-02','DiscNo':'001','EPS':'150'}
        self.assertEqual(latest_financial_record([a,b]),b)
        self.assertEqual(latest_financial_record([b,{**b,'DiscNo':'002','_ordinal':10}]),b)
        self.assertIsNone(latest_financial_record([]))
