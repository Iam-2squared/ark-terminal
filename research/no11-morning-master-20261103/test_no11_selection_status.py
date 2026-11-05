"""Offline weekly/daily selection UI status tests; no Excel/broker/trade."""
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("no11_selection_status",HERE/"no11_selection_status.py")
sel=importlib.util.module_from_spec(spec)
spec.loader.exec_module(sel)
JST=timezone(timedelta(hours=9))
NOW=datetime(2026,11,5,22,12,tzinfo=JST)

def enc(obj):
    return (json.dumps(obj, ensure_ascii=False, separators=(",",":"))+"\n").encode()

def put(file,obj):
    file.parent.mkdir(exist_ok=True,parents=True)
    b=enc(obj)
    file.write_bytes(b)
    return hashlib.sha256(b).hexdigest()

class SelectionStatusTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.private=self.root/"private"
        self.private.mkdir()
        self.binding=self.root/"automatic-inputs.json"
        put(self.binding,{"schemaId":"ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1",
                          "orderTransmission":False,
                          "dailyCycleRoot":str(self.private)})

    def create_complete(self, *, weekly_asof="2026-10-26",
                        weekly_schema=sel.WEEKLY_RSS_SCHEMA,
                        target="2026-11-06",prior="2026-11-05"):
        weekly_run=self.root/"weekly-run"
        source_plan={"schemaId":weekly_schema,"asOfSession":weekly_asof,
                     "planId":"a"*64,
                     "symbols":[f"{1000+i:04d}.T" for i in range(4328)]}
        put(weekly_run/"plan.json",source_plan)
        symbols=[f"{1000+i:04d}.T" for i in range(429)]
        digest=hashlib.sha256(json.dumps(symbols,separators=(",",":")).encode()).hexdigest()
        refreshed=self.root/"refresh"
        plan={"schemaId":sel.WEEKLY_RSS_SCHEMA,
              "refreshSchemaId":sel.REFRESH_SCHEMA,
              "asOfSession":prior,"planId":"b"*64,
              "orderTransmission":False,"productionReady":False,
              "symbols":symbols,"sourceSymbolsSha256":digest,
              "weeklySource":{"asOfSession":weekly_asof,"originalPlanId":"a"*64,
                              "observedPassCount":len(symbols),
                              "observedPassSymbolsSha256":digest,
                              "originalFullUniverseCount":4328}}
        put(refreshed/"plan.json",plan)
        selected=symbols[:45]
        chart={"chartPlan":{"schemaId":sel.CHART_SCHEMA,
                            "sessionDate":target,"asOfSession":prior,
                            "selectorInputSymbols":selected,
                            "sourcePlanId":"b"*64,
                            "orderTransmission":False,"productionReady":False}}
        mask={"schemaId":sel.MASK_SCHEMA,"asOfSession":prior,
              "planId":"b"*64,"orderTransmission":False}
        stage={"schemaId":"ARK_NO11_RSS_PREVIOUS_ARCHIVE_V1",
               "selectedSymbols":selected,"orderTransmission":False}
        spec={
            "weeklySourceRun":str(weekly_run),
            "chartReceipt":str(refreshed/"no11-chart50-private.json"),
            "passMask":str(refreshed/"no11-observed-pass-watch.json"),
            "previousStage":str(self.private/"previous-stage.json")
        }
        pins={
            "chartReceipt":put(Path(spec["chartReceipt"]),chart),
            "passMask":put(Path(spec["passMask"]),mask),
            "previousStage":put(Path(spec["previousStage"]),stage),
        }
        hand={"schemaId":sel.HANDOFF_SCHEMA,"sessionDate":target,
              "previousSession":prior,"selectedSymbols":selected,
              "reviewStatus":"NOT_REVIEWED","datedMasterCreated":False,
              "productionReady":False,"orderTransmission":False,
              "sourcePins":pins,"spec":spec}
        b=enc(hand)
        digest_hand=hashlib.sha256(b).hexdigest()
        hpath=self.private/"handoffs"/("morning-handoff-"+digest_hand+".json")
        hpath.parent.mkdir(parents=True,exist_ok=True)
        hpath.write_bytes(b)
        ptr={"schemaId":sel.POINTER_SCHEMA,"sessionDate":target,
             "previousSession":prior,"selectedSymbols":selected,
             "selectedCount":len(selected),"handoff":str(hpath),
             "handoffSha256":digest_hand,"humanReviewClaimed":False,
             "manualPricesRequired":False,"manualEvidenceRequired":False,
             "productionReady":False,"orderTransmission":False}
        pointer=self.private/"prepared-days"/(target+".json")
        put(pointer,ptr)
        return {"pointer":pointer,"handoff":hpath,"weekly":weekly_run/"plan.json",
                "daily_plan":refreshed/"plan.json","chart":Path(spec["chartReceipt"])}

    def test_completed_daily_and_carried_monday_weekly(self):
        self.create_complete()
        obj=sel.inspect(self.binding,at=NOW)
        self.assertEqual(obj["daily"],{"state":"READY","target":"2026-11-06","count":45})
        self.assertEqual(obj["weekly"],{"state":"CARRIED","asOf":"2026-10-26","pool":429})
        self.assertIn("WEEKLY  CARRIED 10/26 (429)",sel.display(obj))
        self.assertIn("DAILY  READY 11/06 (45)",sel.display(obj))
        self.assertIs(obj["orderTransmission"],False)

    def test_real_last_friday_completed_weekly(self):
        self.create_complete(weekly_asof="2026-10-30")
        obj=sel.inspect(self.binding,at=NOW)
        self.assertEqual(obj["weekly"]["state"],"DONE")

    def test_provisional_yahoo_is_not_full_weekly_done(self):
        self.create_complete(weekly_asof="2026-10-30",weekly_schema=sel.WEEKLY_YAHOO_SCHEMA)
        self.assertEqual(sel.inspect(self.binding,at=NOW)["weekly"]["state"],"PROVISIONAL")

    def test_no_nightly_pointer_does_not_claim_completion(self):
        result=sel.inspect(self.binding,at=NOW)
        self.assertEqual(result["daily"]["state"],"NOT_READY")
        self.assertEqual(result["weekly"]["state"],"UNKNOWN")

    def test_failed_and_tampered_handoff_fail_closed(self):
        p=self.create_complete()
        p["handoff"].write_bytes(p["handoff"].read_bytes()+b" ")
        out=sel.inspect(self.binding,at=NOW)
        self.assertEqual(out["daily"]["state"],"INVALID")
        self.assertNotEqual(out["weekly"]["state"],"DONE")

    def test_tampered_original_chart_fails_daily(self):
        p=self.create_complete()
        p["chart"].write_bytes(p["chart"].read_bytes()+b" ")
        self.assertEqual(sel.inspect(self.binding,at=NOW)["daily"]["state"],"INVALID")

    def test_tampered_weekly_source_separate_failure(self):
        p=self.create_complete()
        x=json.loads(p["daily_plan"].read_bytes())
        x["weeklySource"]["originalPlanId"]="f"*64
        put(p["daily_plan"],x)
        out=sel.inspect(self.binding,at=NOW)
        self.assertEqual(out["daily"]["state"],"READY")
        self.assertEqual(out["weekly"]["state"],"UNVERIFIED")

    def test_morning_uses_current_day_even_with_previous(self):
        self.create_complete(target="2026-11-06",prior="2026-11-05")
        d=datetime(2026,11,6,8,35,tzinfo=JST)
        self.assertEqual(sel.inspect(self.binding,at=d)["daily"]["state"],"READY")

    def test_afterclose_requires_future_pointer_not_yesterday(self):
        self.create_complete(target="2026-11-05",prior="2026-11-04")
        self.assertEqual(sel.inspect(self.binding,at=NOW)["daily"]["state"],"NOT_READY")

    def test_never_claim_trade_authority_even_when_ready(self):
        self.create_complete()
        value=sel.inspect(self.binding,at=NOW)
        self.assertEqual(value["schemaId"],"ARK_NO11_SELECTION_DISPLAY_V1")
        self.assertTrue(value["readOnly"])
        self.assertIs(value["orderTransmission"],False)

if __name__=="__main__":
    unittest.main(verbosity=2)
