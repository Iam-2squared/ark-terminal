import unittest
from datetime import datetime,timezone
from phase57_cash_locked_pipeline import run_locked_pipeline

NOW=datetime(2026,9,15,6,0,5,tzinfo=timezone.utc)
SAFE={"executionAllowed":False,"brokerWriteAllowed":False,"excelOrderWriteAllowed":False,"rssOrderFunctionAllowed":False,"liveTradingAllowed":False,"paperTradingAllowed":False,"automaticPromotionAllowed":False,"productionUpdateAllowed":False,"transmitted":False}
def snap(cash=1000000): return {"schemaId":"ARK_ACCOUNT_READONLY_SNAPSHOT_V2","capturedAt":"2026-09-15T15:00:00+09:00","source":"MARKETSPEED_II_RSS","mode":"READ_ONLY","positions":[{"symbol":"408A","quantity":180}],"orders":[],"executions":[],"buyingPower":cash,"safety":dict(SAFE)}
INT={"symbol":"7203.T","direction":"LONG","side":"BUY","positionEffect":"OPEN","quantity":100,"orderType":"MARKET","limitPrice":None,"timeInForce":"DAY"}
class PipelineTests(unittest.TestCase):
 def test_locked_ready(self):
  out=run_locked_pipeline(snap(),external_positions=[{"symbol":"408A","quantity":180}],intent=INT,estimated_notional=300000,now=NOW)
  self.assertEqual(out["status"],"LOCKED_READY"); self.assertFalse(out["interface"]["formulaEvaluationAllowed"]); self.assertFalse(out["interface"]["transmitted"])
 def test_insufficient_cash_blocks_g9(self):
  out=run_locked_pipeline(snap(2605),external_positions=[{"symbol":"408A","quantity":180}],intent=INT,estimated_notional=300000,now=NOW)
  self.assertEqual(out["stage"],"G9"); self.assertIn("INSUFFICIENT_CASH",out["candidate"]["blockers"])
if __name__=="__main__": unittest.main()
