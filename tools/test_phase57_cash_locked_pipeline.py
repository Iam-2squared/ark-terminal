import unittest
from datetime import datetime,timezone
from phase57_cash_locked_pipeline import run_locked_pipeline

NOW=datetime(2026,9,15,6,0,5,tzinfo=timezone.utc)
SAFE={"executionAllowed":False,"brokerWriteAllowed":False,"excelOrderWriteAllowed":False,"rssOrderFunctionAllowed":False,"liveTradingAllowed":False,"paperTradingAllowed":False,"automaticPromotionAllowed":False,"productionUpdateAllowed":False,"transmitted":False}
def snap(cash=1000000,positions=None): return {"schemaId":"ARK_ACCOUNT_READONLY_SNAPSHOT_V2","capturedAt":"2026-09-15T15:00:00+09:00","source":"MARKETSPEED_II_RSS","mode":"READ_ONLY","positions":positions if positions is not None else [{"symbol":"408A","quantity":180}],"orders":[],"executions":[],"buyingPower":cash,"safety":dict(SAFE)}
ENTRY={"symbol":"7203.T","direction":"LONG","side":"BUY","positionEffect":"OPEN","quantity":100,"orderType":"MARKET","limitPrice":None,"timeInForce":"DAY"}
EXIT={"symbol":"7203.T","direction":"LONG","side":"SELL","positionEffect":"CLOSE","quantity":100,"orderType":"MARKET","limitPrice":None,"timeInForce":"DAY"}
class PipelineTests(unittest.TestCase):
 def test_locked_ready(self):
  out=run_locked_pipeline(snap(),external_positions=[{"symbol":"408A","quantity":180}],intent=ENTRY,estimated_notional=300000,now=NOW)
  self.assertEqual(out["status"],"LOCKED_READY"); self.assertFalse(out["interface"]["formulaEvaluationAllowed"]); self.assertFalse(out["interface"]["transmitted"])
 def test_insufficient_cash_blocks_g9(self):
  out=run_locked_pipeline(snap(2605),external_positions=[{"symbol":"408A","quantity":180}],intent=ENTRY,estimated_notional=300000,now=NOW)
  self.assertEqual(out["stage"],"G9"); self.assertIn("INSUFFICIENT_CASH",out["candidate"]["blockers"])
 def test_managed_cash_exit_reconciles_and_reaches_locked_ready(self):
  broker=[{"symbol":"408A","quantity":180},{"symbol":"7203","quantity":100}]
  out=run_locked_pipeline(snap(2605,broker),external_positions=[{"symbol":"408A","quantity":180}],ark_managed_positions=[{"symbol":"7203.T","quantity":100}],intent=EXIT,estimated_notional=300000,now=NOW)
  self.assertEqual(out["status"],"LOCKED_READY")
  self.assertEqual(out["draft"]["intent"]["side"],"SELL")
  self.assertFalse(out["interface"]["formulaEvaluationAllowed"])
 def test_unowned_cash_exit_blocks_at_g6(self):
  broker=[{"symbol":"408A","quantity":180},{"symbol":"7203","quantity":100}]
  out=run_locked_pipeline(snap(2605,broker),external_positions=[{"symbol":"408A","quantity":180}],intent=EXIT,estimated_notional=300000,now=NOW)
  self.assertEqual(out["stage"],"G6")
  self.assertIn("UNKNOWN_BROKER_POSITION:7203.T",out["reconciliation"]["blockers"])
if __name__=="__main__": unittest.main()
