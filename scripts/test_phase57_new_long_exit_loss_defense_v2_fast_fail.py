import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'scripts/phase57_new_long_exit_loss_defense_v2_fast_fail.py'
s=importlib.util.spec_from_file_location('ld2',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def b(slot,c,o=None):return {'slot':slot,'o':c if o is None else o,'h':max(c,0),'l':min(c,0),'c':c,'missing':False}
class T(unittest.TestCase):
 def test_reclaim_within_two_bars_holds(self):
  r=m.sim([b(1,-.5),b(2,-.7),b(3,.1)],.1);self.assertEqual(r['status'],'HOLD_TO_HORIZON')
 def test_failed_window_and_worse_exits(self):
  r=m.sim([b(1,-.5),b(2,-.7),b(3,-.8),b(4,-.9,o=-.85)],0)
  self.assertEqual((r['status'],r['signalBar'],r['exitBar']),('EXIT_REFERENCE',3,4))
 def test_not_worse_resets_window(self):
  r=m.sim([b(1,-.5),b(2,-.4),b(3,-.3),b(4,-.2)],-.2);self.assertEqual(r['status'],'HOLD_TO_HORIZON')
 def test_build_deterministic(self):
  _,_,a=m.build();_,_,z=m.build();self.assertEqual(a,z)
if __name__=='__main__':unittest.main()
