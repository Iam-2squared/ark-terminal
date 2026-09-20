import json,os,unittest
from pathlib import Path
import numpy as np
from scripts import phase57_profile_coverage as c
class CoverageTests(unittest.TestCase):
 def setUp(self):self.p=c.read(c.BASE/'protocol.json')
 def cell(self,**kw):
  x={'eligible':True,'posterior':1.,'posterior_sd':.1,'peer_prediction':0.,'shrinkWeight':2/3,'nSessions':40,'nEff':40.,'coverage':.8,'normalizedUncertainty':.25,'driftFlag':False};x.update(kw);return x
 def test_high_exact_boundary(self):self.assertEqual(c.confidence(self.cell(),self.p),'HIGH')
 def test_unknown_drift_is_medium(self):self.assertEqual(c.confidence(self.cell(driftFlag=None),self.p),'MEDIUM')
 def test_true_drift_is_low(self):self.assertEqual(c.confidence(self.cell(driftFlag=True),self.p),'LOW')
 def test_medium_boundary(self):self.assertEqual(c.confidence(self.cell(nSessions=20,nEff=20,shrinkWeight=.5,coverage=.5,normalizedUncertainty=.5),self.p),'MEDIUM')
 def test_low_neff(self):self.assertEqual(c.confidence(self.cell(nEff=19.99),self.p),'LOW')
 def test_missing_posterior(self):self.assertEqual(c.confidence(self.cell(posterior=None),self.p),'INSUFFICIENT')
 def test_eligible_without_peer_fit(self):self.assertEqual(c.confidence(self.cell(peer_prediction=None),self.p),'INSUFFICIENT')
 def test_unknown_scale(self):self.assertEqual(c.confidence(self.cell(normalizedUncertainty=None),self.p),'LOW')
 def test_difference_not_confidence(self):
  x=self.cell(nEff=1,shrinkWeight=.05);self.assertTrue(c.differentiate(x));self.assertEqual(c.confidence(x,self.p),'LOW')
 def test_difference_boundary(self):self.assertFalse(c.differentiate(self.cell(posterior=.196)))
 def test_identity_full(self):
  X=np.random.default_rng(8).normal(size=(12,4));truth=np.array([20.,-4.,7.,.8])
  val,audit=c.solve_identity(np.column_stack([X,X@truth]).tolist());np.testing.assert_allclose(val,truth,atol=1e-9);self.assertEqual(audit['status'],'VERIFIED_FULL')
 def test_identity_partial(self):
  X=np.random.default_rng(8).normal(size=(12,4));X[:,3]=0;truth=np.array([20.,-4.,7.,.8])
  val,audit=c.solve_identity(np.column_stack([X,X@truth]).tolist());self.assertIsNone(val[3]);np.testing.assert_allclose(val[:3],truth[:3]);self.assertEqual(audit['status'],'VERIFIED_PARTIAL')
 def test_identity_poison(self):
  X=np.random.default_rng(8).normal(size=(12,4));y=X@np.arange(4);y[-1]+=1
  val,audit=c.solve_identity(np.column_stack([X,y]).tolist());self.assertEqual(val,[None]*4);self.assertEqual(audit['status'],'VALIDATION_FAILED')
 def test_identity_insufficient(self):self.assertEqual(c.solve_identity([[1,2,3,4,5]]*5)[0],[None]*4)
 def test_bin_edges(self):self.assertEqual(c.bins([0,1,2,3,5,6,10,11]),{'0':1,'1-2':2,'3-5':2,'6-10':2,'11+':1})
 def test_unknown_not_zero(self):self.assertIsNone(c.stats([None,float('nan')])['median'])
 def test_population_and_no_promotion(self):
  p=Path(os.environ['COVERAGE_OUTPUT']);rows=c.read(p/'01_trait_coverage.json');self.assertEqual(len(rows),96)
  self.assertEqual(sum(x['globalStatus']=='USABLE' and x['window']==60 for x in rows),9);self.assertEqual(sum(x['globalStatus']=='WATCH' and x['window']==60 for x in rows),23)
  for x in rows:
   self.assertEqual(sum(y['n'] for y in x['confidence'].values()),x['totalSymbols'])
   self.assertEqual(x['profileComputable']['n'],x['totalSymbols']-x['confidence']['INSUFFICIENT']['n'])
   self.assertEqual(x['highMedium']['n'],x['confidence']['HIGH']['n']+x['confidence']['MEDIUM']['n'])
   if x['globalStatus']=='WATCH':self.assertEqual(x['globalReasons'],['calibration']);self.assertFalse(x['calibrationAssessment']['correctionFitted'])
   for name in ['liquidity','price','volatility']:self.assertEqual(sum(v['totalSymbols'] for v in x['strata'][name].values()),x['totalSymbols'])
  d=c.read(p/'03_integrated_coverage.json');self.assertEqual(d['validatedHandoffSymbols'],0);self.assertNotEqual(d['endpointDates']['daily'],d['endpointDates']['intraday'])
  for window in c.WINDOWS:
   for kind in ['union','intersection']:
    for view in ['available','hm']:self.assertEqual(sum(d[str(window)][kind][view].values()),d[str(window)][kind]['symbols'])
 def test_source_and_safety(self):
  for p,h in c.read(c.BASE/'start-state.json')['files'].items():self.assertEqual(c.a.sha(c.ROOT/p),h)
  self.assertTrue(all(x is False for x in c.read(c.BASE/'start-state.json')['safety'].values()))
 def test_correction_spec_only(self):
  x=c.read(c.BASE/'correction-spec.json');self.assertEqual(x['status'],'SPECIFICATION_ONLY_NOT_IMPLEMENTED_OR_MEASURED');self.assertEqual(x['readerCandidate']['maxStalenessMinutes'],4);self.assertNotEqual(x['pullbackCandidate']['newTraitId'],x['pullbackCandidate']['oldTraitUnchanged'])
if __name__=='__main__':unittest.main()
