import unittest
from phase57_cash_micro_live_gate import build_micro_live_preflight

CAND={"eligible":True,"candidateToken":"abc","cashOnly":True,"marginAllowed":False,"shortSellingAllowed":False}

def draft(**changes):
    intent={"symbol":"7203.T","direction":"LONG","side":"BUY","positionEffect":"OPEN","quantity":100}
    intent.update(changes)
    return {"function":"RssStockOrder","trigger":0,"transmitted":False,"formulaDraft":'=RssStockOrder(1,0,"7203.T",3)',"intent":intent}

class MicroLivePreflightTests(unittest.TestCase):
    def test_clean_buy_reaches_physical_unlock_boundary_only(self):
        out=build_micro_live_preflight(unlock_candidate=CAND,draft=draft())
        self.assertTrue(out["readyForPhysicalUnlock"])
        self.assertEqual(out["physicalUnlock"],"MARKETSPEED_EXCEL_ORDER_ENABLE_REQUIRED")
        self.assertFalse(out["executionAllowed"]); self.assertFalse(out["transmitted"]); self.assertFalse(out["rssCallPerformed"])
    def test_margin_function_blocked(self):
        d=draft(); d["function"]="RssMarginOpenOrder"; d["formulaDraft"]="=RssMarginOpenOrder(...)"
        out=build_micro_live_preflight(unlock_candidate=CAND,draft=d)
        self.assertIn("RSS_STOCK_ORDER_ONLY",out["blockers"]); self.assertIn("MARGIN_FUNCTION_PRESENT",out["blockers"])
    def test_short_blocked(self):
        self.assertIn("LONG_ONLY",build_micro_live_preflight(unlock_candidate=CAND,draft=draft(direction="SHORT",side="SELL"))["blockers"])
    def test_open_order_blocks_second_order(self):
        self.assertIn("ONE_ORDER_AT_A_TIME",build_micro_live_preflight(unlock_candidate=CAND,draft=draft(),open_order_count=1)["blockers"])
    def test_sell_must_be_ark_managed_and_within_quantity(self):
        d=draft(side="SELL",positionEffect="CLOSE",quantity=200)
        out=build_micro_live_preflight(unlock_candidate=CAND,draft=d,ark_managed_positions=[{"symbol":"7203.T","quantity":100}])
        self.assertIn("SELL_EXCEEDS_ARK_MANAGED_POSITION",out["blockers"])
    def test_valid_managed_sell_reaches_boundary(self):
        d=draft(side="SELL",positionEffect="CLOSE",quantity=100)
        out=build_micro_live_preflight(unlock_candidate=CAND,draft=d,ark_managed_positions=[{"symbol":"7203.T","quantity":100}])
        self.assertTrue(out["readyForPhysicalUnlock"]); self.assertFalse(out["transmitted"])
    def test_g9_candidate_required(self):
        bad={**CAND,"eligible":False,"candidateToken":None}
        self.assertIn("G9_UNLOCK_CANDIDATE_REQUIRED",build_micro_live_preflight(unlock_candidate=bad,draft=draft())["blockers"])

if __name__=="__main__": unittest.main()
