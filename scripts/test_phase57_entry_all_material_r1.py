import unittest,math,numpy as np
from scripts import phase57_entry_all_material_r1_train as m
from scripts import phase57_entry_all_material_r1_data as d
class R1Tests(unittest.TestCase):
    def test_first_threshold(self):
        rr=[{'minute':600+i,'delay':i} for i in range(7)]
        self.assertEqual(m.scoring_intent(rr,[.1,.2,.6,.8,.9,.9,.9],5,.5),(602,'MODEL_THRESHOLD',.6))
    def test_exact_forced_horizon(self):
        rr=[{'minute':600+i,'delay':i} for i in range(6)]
        self.assertEqual(m.scoring_intent(rr,[.1]*6,5,.5),(605,'FORCED_HORIZON',.1))
    def test_no_synthetic_horizon(self):
        self.assertEqual(m.scoring_intent([{'minute':600,'delay':0}],[.1],5,.5),(None,'HORIZON_UNREACHABLE',None))
    def test_missing_t0_lunch(self):
        rr=[{'minute':750+i,'delay':i} for i in range(1,6)]
        self.assertEqual(m.scoring_intent(rr,[.7]*5,5,.5)[0],751)
    def test_future_scoring_suffix(self):
        rr=[{'minute':600+i,'delay':i} for i in range(6)];p=[.1]*6
        a=m.scoring_intent(rr,p,5,.5)
        self.assertEqual(a,m.scoring_intent(rr+[{'minute':610,'delay':10}],p+[1.],5,.5))
    def test_nonfinite_prediction_rejected(self):
        with self.assertRaises(AssertionError):m.scoring_intent([{'minute':600,'delay':0}],[float('nan')],5,.5)
    def test_preprocessing_train_only(self):
        x=np.array([[1.,np.nan],[3.,np.nan]])
        p=m.fit_preprocessor(x);before={k:v.copy() if hasattr(v,'copy') else v for k,v in p.items()}
        z=m.transform(np.array([[1e12,50.]]),p)
        for k in ('median','mean','scale'):np.testing.assert_array_equal(p[k],before[k])
        np.testing.assert_array_equal(p['median'],[2.,0.]);self.assertTrue(np.isfinite(z).all())
    def test_missing_indicator(self):
        x=np.array([[1.,np.nan],[3.,5.]])
        z=m.transform(x,m.fit_preprocessor(x));np.testing.assert_array_equal(z[:,2:],[[0,1],[0,0]])
    def test_feature_count(self):self.assertEqual(len(d.overlay_names()),90)
    def test_unknown_signal_not_false(self):
        obs={'minute':600,'signals':{f:{'trigger':None} for f in d.signals.FAMILIES}}
        x=d.overlay(600,[obs],[],np.array([[599,1,1,1,1,1,1.]]))
        names=d.overlay_names();self.assertTrue(math.isnan(x[names.index('SIX/BREAKOUT/trigger')]))
        self.assertEqual(x[names.index('SIX/BREAKOUT/known')],0.)
    def test_feature_future_bar_rejected(self):
        with self.assertRaises(AssertionError):d.overlay(600,[],[],np.array([[600,1,1,1,1,1,1.]]))
    def test_finite_config_space(self):self.assertEqual(len(set(m.CONFIGS)),36)
if __name__=='__main__':unittest.main()
