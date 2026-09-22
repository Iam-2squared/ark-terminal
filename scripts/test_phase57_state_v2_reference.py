import importlib.util, pathlib, unittest
P=pathlib.Path(__file__).with_name("phase57_state_v2_reference.py")
s=importlib.util.spec_from_file_location("v2",P); v=importlib.util.module_from_spec(s); s.loader.exec_module(v)
m=v.m
class T(unittest.TestCase):
 def bars(self,n=20):
  return tuple(m.Bar(541+i,100+i,101+i,99+i,100+i,10,1000) for i in range(n))
 def sess(self,n=20):
  es=tuple(range(541,571)); return m.Session("2026-01-06","X","RAW",es,self.bars(n))
 def prev(self):
  es=tuple(range(541,571)); bs=tuple(m.Bar(t,100,102,99,101,10,1000) for t in es)
  return m.Session("2026-01-05","X","RAW",es,bs)
 def test_safety9(self): self.assertEqual(9,len(v.SAFETY)); self.assertFalse(any(v.SAFETY.values()))
 def test_direction_does_not_require_scale(self):
  today=self.sess(5); z=v.now_state_reference_v2(today,None,["2026-01-05","2026-01-06"],[],545)
  self.assertEqual("DEFINED",z["direction"]["status"]); self.assertEqual("UP",z["direction"]["value"])
  self.assertEqual("NOT_EVALUATED",z["structure"]["status"])
 def test_future_source_rejected_by_now(self):
  with self.assertRaises(ValueError):
   v.now_state_reference_v2(self.sess(6),self.prev(),["2026-01-05","2026-01-06"],[],545)
 def test_primary_reason(self):
  self.assertEqual("OBS_CURRENT_BAR_NOT_OBSERVED",v.primary(["SCALE_ZERO","OBS_CURRENT_BAR_NOT_OBSERVED"]))
 def test_future_is_separate_and_h10(self):
  z=v.future_resolution_v2(self.sess(20),self.prev(),["2026-01-05","2026-01-06"],[],545)
  self.assertEqual(10,z["futureResolution"]["horizonActiveMinutes"])
 def test_canonical_hash_deterministic(self):
  x={"b":2,"a":1}; self.assertEqual(v.canonical_hash(x),v.canonical_hash({"a":1,"b":2}))
if __name__=="__main__": unittest.main()
