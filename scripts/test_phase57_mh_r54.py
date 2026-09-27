"""Synthetic only: zero real labels, zero estimator fits, no policy performance."""
import math
import unittest

from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_mh_controller_r54 as c
from scripts import phase57_mh_data_r54 as d

DAY = "2025-07-22"


def f(short=-.2, long=.2, long_lower=.01):
    return {h: {"mean": v, "q10": lower, "q90": v+.5}
            for h, v, lower in ((1, short, short-.5), (5, short, short-.5),
                                 (15, long, long_lower), (30, long, long_lower),
                                 (60, long, long_lower), ("EOD", long, long_lower))}


def now_targets(now):
    return d.planned_targets(DAY, now)


class ClockAndLabels(unittest.TestCase):
    def test_h0_not_negative_teacher(self):
        self.assertEqual(d.HORIZONS, (0, 1, 5, 15, 30, 60, "EOD"))
        self.assertNotIn(0, c.SHORT)
        self.assertNotIn(0, c.LONG)

    def test_lunch_open_and_active(self):
        self.assertEqual(execution.next_execution_start(DAY, 690), 750)
        self.assertEqual(d.planned_targets(DAY, 690)[1], 751)
        self.assertEqual(c.deadline_after(DAY, 689, 2), 751)

    def test_terminal_alias_canonical(self):
        t = d.planned_targets(DAY, 924)
        self.assertEqual(t["EOD"], 925)
        self.assertNotIn(1, t)
        self.assertEqual(t[0], 924)

    def test_60_never_truncated(self):
        t = d.planned_targets(DAY, 870)
        self.assertNotIn(60, t)
        self.assertEqual(t["EOD"], 925)

    def test_exact_open_required(self):
        row = lambda minute, value: [minute, value, value, value, value, 100., 1000.]
        p={540:row(540,100), 541:row(541,101), 542:row(542,103), 930:row(930,110)}
        r, why=d.labels_for_checkpoint(DAY,541,p,True)
        self.assertEqual(why,"AVAILABLE")
        self.assertAlmostEqual(r[0]["A"],1)
        self.assertAlmostEqual(r[1]["A"],3)
        self.assertAlmostEqual(r[1]["D"],(103-101)*.9995)
        self.assertEqual(r[1]["reasonC"],"AVAILABLE")
        self.assertAlmostEqual(r[1]["HIGH"],3)
        self.assertNotIn(0,c.SHORT)

    def test_missing_e0_only_masks_d_not_a(self):
        row = lambda m,v:[m,v,v,v,v,100,100]
        p={540:row(540,100), 542:row(542,103),930:row(930,110)}
        r,_=d.labels_for_checkpoint(DAY,541,p,True)
        self.assertIsNone(r[1]["D"])
        self.assertIsNotNone(r[1]["A"])
        self.assertEqual(r[1]["reasonD"],"EXACT_E0_OPEN_MISSING")

    def test_interior_missing_makes_c_unknown_only(self):
        row = lambda m,v:[m,v,v,v,v,100,100]
        p={540:row(540,100),541:row(541,101),543:row(543,103),930:row(930,110)}
        r,_=d.labels_for_checkpoint(DAY,541,p,True)
        self.assertIsNotNone(r[2]["A"] if 2 in r else r["EOD"]["A"])
        self.assertIsNone(r["EOD"]["HIGH"])
        self.assertEqual(r["EOD"]["reasonC"],"INTERIOR_BAR_MISSING")

    def test_terminal_missing_d_not_fabricated(self):
        row=lambda m,v:[m,v,v,v,v,100,100]
        r,_=d.labels_for_checkpoint(DAY,541,{540:row(540,100),541:row(541,101)},True)
        self.assertIsNone(r["EOD"]["A"])
        self.assertIsNone(r["EOD"]["D"])
        self.assertIsNone(r["EOD"]["HIGH"])

    def test_future_high_changes_do_not_change_short_d(self):
        row=lambda m,v,hi:[m,v,hi,v,v,100,100]
        p={540:row(540,100,100),541:row(541,101,101),542:row(542,103,103),
           930:row(930,110,110)}
        a,_=d.labels_for_checkpoint(DAY,541,p,True)
        p[541]=row(541,101,180)
        b,_=d.labels_for_checkpoint(DAY,541,p,True)
        self.assertEqual(a[1]["D"],b[1]["D"])

    def test_split_purge(self):
        p={"folds":[{"fold":1,"train":[f"2025-07-{x:02d}" for x in range(1,12)],
                    "purge":["2025-07-12","2025-07-13"],"score":["2025-07-14"]}]}
        z=d.split_manifest(p)[0]
        self.assertEqual(z["fit"][-1],"2025-07-04")
        self.assertEqual(z["innerPurge"],["2025-07-05","2025-07-06"])
        self.assertEqual(z["calibration"][0],"2025-07-07")


class ControllerTest(unittest.TestCase):
    def test_no_instant_sell_from_loss_or_drop(self):
        v=c.Controller("MH_WAIT5",DAY)
        z=v.decide(541,f(short=.2),now_targets(541),fresh=True,current_return=-8)
        self.assertEqual(z["action"],"HOLD")

    def test_two_consecutive_required(self):
        v=c.Controller("MH_WAIT5",DAY)
        self.assertEqual(v.decide(541,f(long=-1),now_targets(541),fresh=True,current_return=2.8)["reason"],
                         "NEGATIVE_CONFIRMATION_WAIT")
        self.assertEqual(v.decide(542,f(long=-1),now_targets(542),fresh=True,current_return=2.7)["action"],"SELL_INTENT")

    def test_grace_is_one_shot(self):
        v=c.Controller("MH_WAIT5",DAY)
        for now in range(541,549):
            z=v.decide(now,f(),now_targets(now),fresh=True,current_return=.2)
            if z["action"]=="SELL_INTENT":
                self.assertTrue(z["state"]["grace_used"])
                self.assertLessEqual(now,z["state"]["grace_deadline"]+1)
                return
        self.fail("PERSISTENT_NEGATIVE_CAN_NOT_HOLD_FOREVER")

    def test_gap_resets_confirmation_not_grace(self):
        v=c.Controller("MH_WAIT5",DAY)
        v.decide(541,f(),now_targets(541),fresh=True,current_return=1)
        z=v.decide(542,f(),now_targets(542),fresh=True,current_return=1)
        self.assertTrue(z["state"]["grace_used"])
        z=v.decide(545,f(),now_targets(545),fresh=True,current_return=1)
        self.assertEqual(z["state"]["neg_count"],1)
        self.assertTrue(z["state"]["grace_used"])

    def test_missing_resets_not_grace_refill(self):
        v=c.Controller("MH_WAIT5",DAY)
        v.decide(541,f(),now_targets(541),fresh=True,current_return=1)
        v.decide(542,f(),now_targets(542),fresh=True,current_return=1)
        z=v.decide(543,f(),now_targets(543),fresh=False,current_return=1)
        self.assertEqual(z["reason"],"DATA_UNAVAILABLE")
        self.assertTrue(z["state"]["grace_used"])

    def test_no_missing_future_becomes_feature(self):
        v=c.Controller("MH_WAIT5",DAY)
        input_f=f()
        z=v.decide(541,input_f,now_targets(541),fresh=True,current_return=-2)
        self.assertEqual(z["reason"],"NEGATIVE_CONFIRMATION_WAIT")
        self.assertNotIn("future",repr(z).lower())

    def test_no_unsupported_long_grace(self):
        v=c.Controller("MH_WAIT5",DAY)
        z=v.decide(541,f(long=.2,long_lower=-.1),now_targets(541),fresh=True,current_return=.5)
        self.assertEqual(z["reason"],"NEGATIVE_CONFIRMATION_WAIT")
        z=v.decide(542,f(long=.2,long_lower=-.1),now_targets(542),fresh=True,current_return=.5)
        self.assertEqual(z["action"],"SELL_INTENT")

    def test_exact_unfillable_sell_does_not_free_cash(self):
        v=c.Controller("MH_WAIT5",DAY)
        v.decide(541,f(long=-1),now_targets(541),fresh=True,current_return=-.5)
        z=v.decide(542,f(long=-1),now_targets(542),fresh=True,current_return=-.5)
        self.assertTrue(z["state"]["pending_intent"])
        v.intent_result(False)
        self.assertEqual(v.state.neg_count,0)
        self.assertFalse(v.state.pending_intent)

    def test_missing_required_forecast(self):
        v=c.Controller("MH_WAIT15",DAY)
        x=f();del x[1]
        self.assertEqual(v.decide(541,x,now_targets(541),fresh=True,current_return=2)["reason"],"DATA_UNAVAILABLE")

    def test_terminal_preempts_forecast(self):
        v=c.Controller("MH_WAIT15",DAY)
        self.assertEqual(v.decide(925,{},now_targets(925),fresh=False,current_return=None)["action"],
                         "FORCE_TERMINAL")

    def test_duplicate_is_hard_error(self):
        v=c.Controller("MH_WAIT15",DAY)
        v.decide(541,f(short=1),now_targets(541),fresh=True,current_return=0)
        with self.assertRaises(ValueError):
            v.decide(541,f(short=1),now_targets(541),fresh=True,current_return=0)


if __name__ == "__main__":
    unittest.main()
