import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'scripts/phase57_new_long_exit_candidate_a_robustness.py'
s=importlib.util.spec_from_file_location('car',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class T(unittest.TestCase):
 def test_deterministic(self):
  _,a=m.build();_,z=m.build();self.assertEqual(a,z)
if __name__=='__main__':unittest.main()
