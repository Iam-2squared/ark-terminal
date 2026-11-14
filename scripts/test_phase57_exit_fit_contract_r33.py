import unittest
from scripts import phase57_exit_fit_contract_r33 as r

class T(unittest.TestCase):
 def test_r33(self):
  c=r.contract()
  self.assertEqual(c["scope"]["scoreSessionCount"],34)
  self.assertEqual(c["fitReuse"]["predictionSpecCount"],6)
  self.assertEqual(c["fitReuse"]["policyConfigurations"],24)
  self.assertEqual(c["fitReuse"]["modelFitsTotal"],144)
  self.assertEqual(c["patternEncoding"]["columns"],187)
  self.assertEqual(c["exposureAtFreeze"]["modelFits"],0)
  self.assertFalse(c["exposureAtFreeze"]["candidatePerformanceInspected"])
  self.assertTrue(all(v is False for v in c["safety"].values()))

if __name__=="__main__":
 unittest.main()
