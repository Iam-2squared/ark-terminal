import unittest
from phase57_locked_excel_adapter import build_locked_excel_interface

PREF={"readyForPhysicalUnlock":True,"cashOnly":True,"marginAllowed":False,"shortSellingAllowed":False,"transmitted":False,"rssCallPerformed":False}
DRAFT={"function":"RssStockOrder","trigger":0,"transmitted":False,"formulaDraft":'=RssStockOrder(1,0,"7203.T",3)',"intent":{"symbol":"7203.T","side":"BUY","quantity":100}}

class LockedExcelAdapterTests(unittest.TestCase):
    def test_maps_locked_interface(self):
        out=build_locked_excel_interface(preflight=PREF,draft=DRAFT,buying_power=1000000)
        self.assertEqual(out["sheet"],"ARK_CASH_ORDER_LOCKED")
        self.assertEqual(out["cells"]["B11"],0)
        self.assertEqual(out["cellTypes"]["B13"],"TEXT")
        self.assertFalse(out["formulaEvaluationAllowed"])
        self.assertFalse(out["excelOrderWriteAllowed"])
        self.assertFalse(out["rssCallAllowed"])
        self.assertFalse(out["transmitted"])
    def test_margin_formula_rejected(self):
        d={**DRAFT,"formulaDraft":"=RssMarginOpenOrder(...)"}
        with self.assertRaisesRegex(ValueError,"CASH_RSS_STOCK_ORDER_REQUIRED"):
            build_locked_excel_interface(preflight=PREF,draft=d,buying_power=1)
    def test_unready_g10_rejected(self):
        p={**PREF,"readyForPhysicalUnlock":False}
        with self.assertRaisesRegex(ValueError,"G10_READY_REQUIRED"):
            build_locked_excel_interface(preflight=p,draft=DRAFT,buying_power=1)
    def test_trigger_one_rejected(self):
        d={**DRAFT,"trigger":1}
        with self.assertRaisesRegex(ValueError,"DRAFT_NOT_LOCKED"):
            build_locked_excel_interface(preflight=PREF,draft=d,buying_power=1)

if __name__=="__main__": unittest.main()
