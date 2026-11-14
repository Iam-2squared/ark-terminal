import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'scripts/phase57_new_long_exit_profit_protection_v0_fast_fail.py'
s=importlib.util.spec_from_file_location('pp',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def b(slot,o,h,l,c):return {'slot':slot,'o':o,'h':h,'l':l,'c':c,'missing':False}
class T(unittest.TestCase):
 def test_no_protect_before_three(self):
  r=m.sim([b(1,0,2,-1,1),b(2,1,2.5,0,1.5)],1.5);self.assertEqual(r['status'],'HOLD_TO_HORIZON')
 def test_two_lower_without_new_high_exits(self):
  rows=[b(1,0,3.2,0,3),b(2,3,3.1,2,2.5),b(3,2.5,3.0,1.5,2),b(4,1.9,2.2,1,1.5)]
  r=m.sim(rows,1.5);self.assertEqual((r['status'],r['signalBar'],r['exitBar']),('EXIT_REFERENCE',3,4))
 def test_new_high_resets_persistence(self):
  rows=[b(1,0,3.2,0,3),b(2,3,3.1,2,2.5),b(3,2.5,3.5,2,3.1),b(4,3,3.4,2.5,2.9)]
  r=m.sim(rows,2.9);self.assertEqual(r['status'],'HOLD_TO_HORIZON')
 def test_build_deterministic(self):
  _,a=m.build();_,z=m.build();self.assertEqual(a,z);self.assertTrue(all(v is False for v in a['safety'].values()))
if __name__=='__main__':unittest.main()
