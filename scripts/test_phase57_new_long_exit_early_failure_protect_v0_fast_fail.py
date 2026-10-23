import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'scripts/phase57_new_long_exit_early_failure_protect_v0_fast_fail.py'
s=importlib.util.spec_from_file_location('efp',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def b(slot,o,h,l,c):return {'slot':slot,'o':o,'h':h,'l':l,'c':c,'missing':False}
class T(unittest.TestCase):
 def test_arm_plus1_then_close_entry_exits(self):
  f={'exitBar':4,'grossPct':2,'netPct':1.95};r=m.policy([b(1,0,1.2,-.2,.8),b(2,.8,1,-.1,0),b(3,-.1,.2,-.3,.1)],f);self.assertEqual((r['status'],r['exitBar']),('EARLY_FAILURE_EXIT',3))
 def test_no_arm_no_exit(self):
  f={'exitBar':2,'grossPct':-.2,'netPct':-.25};r=m.policy([b(1,0,.9,-1,-.5),b(2,-.5,.5,-1,-.2)],f);self.assertEqual(r['status'],'FIXED12_FALLBACK')
 def test_build_deterministic(self):
  _,a=m.build();_,z=m.build();self.assertEqual(a,z);self.assertTrue(all(v is False for v in a['safety'].values()))
if __name__=='__main__':unittest.main()
