import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'scripts/phase57_new_long_exit_profit_protection_v2_fast_fail.py'
s=importlib.util.spec_from_file_location('pp2',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def b(slot,o,h,l,c):return {'slot':slot,'o':o,'h':h,'l':l,'c':c,'missing':False}
class T(unittest.TestCase):
 def test_break_activation_close_exits(self):
  r=m.sim([b(1,0,3.2,0,2.5),b(2,2.5,3.1,2,2.4),b(3,2.3,2.8,2,2.6)],2.6)
  self.assertEqual((r['status'],r['signalBar'],r['exitBar']),('EXIT_REFERENCE',2,3))
 def test_above_activation_holds(self):
  r=m.sim([b(1,0,3.2,0,2.5),b(2,2.5,3.1,2,2.6)],2.6);self.assertEqual(r['status'],'HOLD_TO_HORIZON')
 def test_build_deterministic(self):
  _,a=m.build();_,z=m.build();self.assertEqual(a,z)
if __name__=='__main__':unittest.main()
