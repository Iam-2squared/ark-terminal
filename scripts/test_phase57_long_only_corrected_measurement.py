#!/usr/bin/env python3
"""Synthetic aggregate checks only; no Development input or fitting."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

PATH=Path(__file__).with_name("run_phase57_long_only_corrected_measurement.py")
SPEC=importlib.util.spec_from_file_location("corrected",PATH); MOD=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)

def row(symbol,time="09:30",score=1,valid=1,hit3=0,hit5=0):
    r={c:0.0 for c in MOD.NUMERIC}; r.update({"sessionDate":"2024-01-10","symbol":str(symbol),"decisionTimeJst":time,
      "partition":"DEVELOPMENT_A","sourceGroup":"L1","segment":"PRIME","liquidityBucket":"HIGH",
      "decisionPriceKind":"LATEST_ACCEPTED_MINUTE_CLOSE","corrected30EndpointKind":"CONTINUOUS_5M_CLOSE",
      "firstCloseHitKind2":"NONE","firstCloseHitKind3":"NONE","firstCloseHitKind5":"NONE",
      "decisionPrice":100 if valid else np.nan,"decisionPriceValid":valid,"referenceAgeMin":0 if valid else 20,
      "corrected30Evaluable":valid,"corrected30ReturnBps":100 if valid else np.nan,"mfe30Pct":3 if valid else np.nan,
      "mae30Pct":-1 if valid else np.nan,"sessionMfePct":6 if valid else np.nan,"sessionMaePct":-1 if valid else np.nan,
      "savedV1Score":score,"futureBarCount":10,"highOpportunity2":max(hit3,hit5),"highOpportunity3":max(hit3,hit5),
      "highOpportunity5":hit5,"closeOpportunity2":0,"closeOpportunity3":0,"closeOpportunity5":0,
      "auctionCloseOpportunity2":0,"auctionCloseOpportunity3":0,"auctionCloseOpportunity5":0})
    return r

class CorrectedTests(unittest.TestCase):
    def test_top5_keeps_stale_selected_without_replacement(self):
        rows=[row(i,score=100-i,valid=0 if i==0 else 1,hit3=1) for i in range(10)]
        frame=MOD.prepare(pd.DataFrame(rows)); selected=MOD.select_top5(frame)
        self.assertEqual(selected.symbol.tolist(),["0","1","2","3","4"])
        report=MOD.top5_report(frame)
        self.assertEqual(report["selectedEvents"],5); self.assertEqual(report["freshEvaluableSelected"],4)
        self.assertEqual(report["opportunities"]["highTouch"]["3"]["hitsOverAllSelectedLowerBoundPct"],80)

    def test_random_expected_is_timestamp_capacity_weighted(self):
        rows=[row(i,score=100-i,hit3=1 if i<2 else 0) for i in range(10)]
        rows += [row(i,time="10:00",score=100-i,hit3=1 if i<10 else 0) for i in range(20)]
        frame=MOD.prepare(pd.DataFrame(rows)); selected=MOD.select_top5(frame)
        metric=MOD.opportunity_metrics(frame,selected,"highOpportunity",3)
        self.assertAlmostEqual(metric["randomExpectedHits"],3.5)
        self.assertAlmostEqual(metric["actualRecallPct"],100*7/12)
        self.assertAlmostEqual(metric["recallLift"],2)

    def test_true_excursions_fail_closed(self):
        bad=row("1"); bad["mae30Pct"]=1
        with self.assertRaisesRegex(ValueError,"positive true MAE"): MOD.prepare(pd.DataFrame([bad]))
        bad=row("1"); bad["sessionMfePct"]=-1
        with self.assertRaisesRegex(ValueError,"negative MFE"): MOD.prepare(pd.DataFrame([bad]))

    def test_report_contains_no_symbols_and_no_fit(self):
        frame=MOD.prepare(pd.DataFrame([row("1",hit3=1),row("2")]))
        manifest={"contractId":MOD.CONTRACT,"model":{"name":"CORRECTED_MEASUREMENT_RIDGE_SAVED_CD"},"files":[],"sessionAudits":[],"_sha256":"x"}
        report=MOD.make_report(frame,manifest,"contract")
        import json
        encoded=json.dumps(report,allow_nan=False)
        self.assertNotIn('"symbol"',encoded); self.assertEqual(report["safety"]["fitCalls"],0)
        self.assertEqual(report["scopes"]["FULL_SAVED_DEVELOPMENT"]["ridgeTop5"]["selectedEvents"],2)

if __name__=="__main__": unittest.main()
