import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'scripts/phase57_new_long_exit_loss_defense_v1_fast_fail.py'
s=importlib.util.spec_from_file_location('v1',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def b(slot,o,h,l,c):return {'slot':slot,'o':o,'h':h,'l':l,'c':c,'missing':False}
class T(unittest.TestCase):
 def test_lower_close_without_range_break_holds(self):
  r=m.sim([b(1,0,.2,-.6,-.2),b(2,-.2,.1,-.5,-.3),b(3,-.3,0,-.4,-.2)],-.2)
  self.assertEqual(r['status'],'HOLD_TO_HORIZON')
 def test_close_below_prior_low_exits_next_open(self):
  r=m.sim([b(1,0,.1,-.5,-.2),b(2,-.2,0,-.8,-.6),b(3,-.7,-.4,-.9,-.5)],0)
  self.assertEqual((r['status'],r['signalBar'],r['exitBar']),('EXIT_REFERENCE',2,3))
  self.assertAlmostEqual(r['grossPct'],-.7)
 def test_reclaim_resets(self):
  r=m.sim([b(1,0,.1,-.5,-.2),b(2,-.2,.2,-.3,.1),b(3,.1,.2,-.1,.05)],.05)
  self.assertEqual(r['status'],'HOLD_TO_HORIZON')
 def test_full_build_deterministic(self):
  _,_,a=m.build();_,_,z=m.build();self.assertEqual(a,z)
  self.assertIn(a['status'],('NEW_LONG_EXIT_LOSS_DEFENSE_V1_FAST_FAIL_PASS','NEW_LONG_EXIT_LOSS_DEFENSE_V1_FAST_FAIL_KILL'))
  self.assertTrue(all(v is False for v in a['safety'].values()))
if __name__=='__main__':unittest.main()
