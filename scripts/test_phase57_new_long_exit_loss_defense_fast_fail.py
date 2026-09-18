import importlib.util, pathlib, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/'scripts/phase57_new_long_exit_loss_defense_fast_fail.py'
spec=importlib.util.spec_from_file_location('ld',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def b(slot,c,o=None,h=None,l=None):
    o=c if o is None else o;h=max(o,c) if h is None else h;l=min(o,c) if l is None else l
    return {'slot':slot,'o':o,'h':h,'l':l,'c':c,'missing':False}

class LossDefenseFastFailTests(unittest.TestCase):
    def test_negative_then_lower_signals_next_open(self):
        r=m.sim([b(1,-.2),b(2,-.4),b(3,.1,o=-.35)],0)
        self.assertEqual(r['status'],'EXIT_REFERENCE');self.assertEqual(r['signalBar'],2)
        self.assertEqual(r['exitBar'],3);self.assertAlmostEqual(r['grossPct'],-.35)
    def test_reclaim_returns_to_hold(self):
        r=m.sim([b(1,-.4),b(2,.1),b(3,.2)],.2)
        self.assertEqual(r['status'],'HOLD_TO_HORIZON')
        self.assertIn([2,'RECLAIM',.1],r['transitions'])
    def test_stabilization_does_not_exit(self):
        r=m.sim([b(1,-.5),b(2,-.3),b(3,-.3),b(4,-.2)],-.2)
        self.assertEqual(r['status'],'HOLD_TO_HORIZON')
    def test_later_re_deterioration_exits(self):
        r=m.sim([b(1,-.5),b(2,-.3),b(3,-.4),b(4,-.2,o=-.45)],0)
        self.assertEqual((r['signalBar'],r['exitBar']),(3,4))
    def test_high_low_do_not_change_decision(self):
        a=[b(1,-.2,h=20,l=-20),b(2,-.4,h=50,l=-50),b(3,0,o=-.3,h=99,l=-99)]
        z=[b(1,-.2,h=.1,l=-.3),b(2,-.4,h=.1,l=-.5),b(3,0,o=-.3,h=.1,l=-.4)]
        ra=m.sim(a,0);rz=m.sim(z,0)
        self.assertEqual((ra['signalBar'],ra['exitBar'],ra['grossPct']),(rz['signalBar'],rz['exitBar'],rz['grossPct']))
    def test_missing_exit_reference_is_unknown(self):
        rows=[b(1,-.2),b(2,-.4),{'slot':3,'missing':True}]
        r=m.sim(rows,0);self.assertEqual(r['status'],'UNKNOWN_EXIT_REFERENCE')
    def test_cost_applied_only_to_reference_return(self):
        r=m.sim([b(1,-.2),b(2,-.4),b(3,0,o=-.3)],0,cost=.05)
        self.assertAlmostEqual(r['policyReturnPct'],-.35)
    def test_contract_exists(self):
        self.assertTrue(m.CONTRACT.exists())
    def test_full_build_and_gates_are_deterministic(self):
        _,_,a=m.build();_,_,z=m.build()
        self.assertEqual(a,z)
        self.assertEqual(a['anchorIdentitySHA256'],'985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121')
        self.assertIn(a['status'],('NEW_LONG_EXIT_LOSS_DEFENSE_FAST_FAIL_PASS','NEW_LONG_EXIT_LOSS_DEFENSE_FAST_FAIL_KILL'))
        self.assertTrue(all(v is False for v in a['safety'].values()))
        self.assertTrue(all(v==0 for v in a['zeroCounters'].values()))

if __name__=='__main__':unittest.main()
