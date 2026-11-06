import unittest
from scripts.summarize_phase57_long_exit_paired import dist,rate,classify,arm_metrics

class SummaryTests(unittest.TestCase):
    def test_missing_is_not_zero(self):
        self.assertIsNone(dist([])['mean']);self.assertIsNone(rate(0,0)['ratePct'])
    def test_same_bar_unknown_and_incomplete(self):
        self.assertEqual(classify({'horizons':{'SESSION_END':{'available':False}},'future':[]}), 'G_UNKNOWN')
        e={'horizons':{'SESSION_END':{'available':True,'mfePct':2,'returnPct':1}},'future':[{'h':2,'l':-2,'c':1,'minutes':5}]}
        self.assertEqual(classify(e),'G_UNKNOWN')
    def test_reference_cost_capture_and_no_portfolio_claim(self):
        e={'symbol':'SYNTHETIC','sessionDate':'2000-01-01','future':[{'h':2,'l':-1,'c':1,'minutes':5}], 'horizons':{'SESSION_END':{'mfePct':2,'maePct':-1,'returnPct':1}}}
        m=arm_metrics([e],'SESSION_END')
        self.assertEqual(m['n'],1);self.assertAlmostEqual(m['netSumPctPoints'],.95);self.assertEqual(m['grossAvailableMfeCapture']['mean'],.5);self.assertTrue(m['drawdownNotPortfolio']);self.assertEqual(m['sessionEndExposure']['count'],1)
    def test_percentile_matches_linear_saved_convention(self):
        d=dist([-10,-2,0,4]);self.assertEqual(d['median'],-1);self.assertAlmostEqual(d['p05'],-8.8)
if __name__=='__main__':unittest.main(verbosity=2)
