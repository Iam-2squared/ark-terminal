import unittest
from fractions import Fraction as F
from r_labels import classify
from io_utils import *

class LabelTests(unittest.TestCase):
    def test_exact_boundaries(self):
        for threshold in [5,10]:
            for delta,expected in [(-F(1,10**20),False),(F(0),True),(F(1,10**20),True)]:
                credit=F(100+threshold)+delta
                r=classify('100',credit);self.assertEqual(r['R'+str(threshold)],expected)
    def test_zero_and_unknown(self):
        self.assertTrue(classify('100','100')['Loser']);self.assertIsNone(classify(None,None)['Loser']);self.assertIsNone(classify(None,None)['R5'])
    def test_r10_subset(self):
        for n in [-100,-1,0,1,5,9,10,50]:
            r=classify('100',str(100+n));self.assertFalse(r['R10'] and not r['R5'])

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LabelTests))
    save(OUT/'R_LABEL_BOUNDARY_TESTS.json',{'exact_jst':now(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'pass':result.wasSuccessful()})
    raise SystemExit(0 if result.wasSuccessful() else 1)
