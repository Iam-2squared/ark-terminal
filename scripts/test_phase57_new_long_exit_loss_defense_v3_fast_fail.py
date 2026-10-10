import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'scripts/phase57_new_long_exit_loss_defense_v3_fast_fail.py'
s=importlib.util.spec_from_file_location('ld3',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def b(slot,c,o=None):return {'slot':slot,'o':c if o is None else o,'h':max(c,0),'l':min(c,0),'c':c,'missing':False}
class T(unittest.TestCase):
 def test_minus3_close_exits(self):
  r=m.sim([b(1,-2),b(2,-3.1),b(3,-2.8,o=-3)],0);self.assertEqual((r['status'],r['signalBar'],r['exitBar']),('EXIT_REFERENCE',2,3))
 def test_above_minus3_holds(self):
  self.assertEqual(m.sim([b(1,-2.9),b(2,-2.5)],-2.5)['status'],'HOLD_TO_HORIZON')
 def test_build_deterministic(self):
  _,_,a=m.build();_,_,z=m.build();self.assertEqual(a,z)
if __name__=='__main__':unittest.main()
