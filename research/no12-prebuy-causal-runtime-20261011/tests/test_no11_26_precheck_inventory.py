import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import no11_26_precheck_inventory as mod

class Inventory(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.root=Path(self.tmp.name)
  self.cfg={"schemaId":mod.SCHEMA,"sessionDate":mod.DATE,
    "productionReady":False,"orderTransmission":False,
    "dailyRun":str(self.root),"runtimeRoot":str(self.root),
    "privateRoot":str(self.root),
    "datedMaster":str(self.root/"master.json"),
    "previousContext":str(self.root/"previous.json")}
  (self.root/"master.json").write_text(json.dumps({
    "schemaId":"ARK_NO11_DATED_MASTER_RECEIPT_V1",
    "sessionDate":mod.DATE,"rows":[{"symbol":"7203.T"}]}))
  (self.root/"previous.json").write_text(json.dumps({
    "schemaId":"ARK_NO11_RSS_P1_PREVIOUS_CONTEXT_V1",
    "sessionDate":mod.DATE,"previousSession":"2026-10-23"}))
 def tearDown(self):self.tmp.cleanup()
 def test_all_files_exist_does_not_claim_live_ready(self):
  r=mod.audit(self.cfg)
  self.assertEqual(r["blockers"],[])
  self.assertFalse(r["shadowReady"])
  self.assertFalse(r["productionReady"])
  self.assertFalse(r["orderTransmission"])
 def test_missing_previous_is_a_blocker(self):
  (self.root/"previous.json").unlink()
  self.assertIn("previousContext",mod.audit(self.cfg)["blockers"])
 def test_old_master_date_is_blocked(self):
  (self.root/"master.json").write_text(json.dumps({
    "schemaId":"ARK_NO11_DATED_MASTER_RECEIPT_V1",
    "sessionDate":"2026-10-23","rows":[{}]}))
  self.assertIn("datedMaster",mod.audit(self.cfg)["blockers"])
 def test_orders_cannot_be_enabled(self):
  self.cfg["orderTransmission"]=True
  with self.assertRaisesRegex(ValueError,"ORDER_MUST_BE_OFF"):
   mod.audit(self.cfg)
 def test_wrong_previous_day_is_blocked(self):
  (self.root/"previous.json").write_text(json.dumps({
    "schemaId":"ARK_NO11_RSS_P1_PREVIOUS_CONTEXT_V1",
    "sessionDate":mod.DATE,"previousSession":"2026-10-22"}))
  self.assertIn("previousContext",mod.audit(self.cfg)["blockers"])
if __name__=="__main__":unittest.main()
