import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'scripts/phase57_new_long_exit_candidate_c.py'
s=importlib.util.spec_from_file_location('cc',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class T(unittest.TestCase):
 def test_build_deterministic(self):
  _,a=m.build();_,z=m.build();self.assertEqual(a,z)
 def test_routes(self):
  l,s=m.build();self.assertTrue(all(x['route']=='CANDIDATE_A' for x in l if x['cohort']=='INITIAL_ENTRY_OPPORTUNITY'));self.assertTrue(all(x['route']=='TWO_STAGE_DIP' for x in l if x['cohort']=='DIP_REPRICE_OPPORTUNITY'))
if __name__=='__main__':unittest.main()
