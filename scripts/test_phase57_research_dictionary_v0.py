import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import numpy as np
from scripts import phase57_research_dictionary_v0 as m

class Contract(unittest.TestCase):
 def row(self,t='09:00',day='2024-11-05',**kw):
  r=dict(Date=day,Time=t,Code='TEST',O=100.,H=101.,L=99.,C=100.,Vo=10.,Va=1000.);r.update(kw);return r
 def test_registry(self):
  p=m.registry();self.assertEqual(len(p['catalog']),73);self.assertEqual(len(p['composites']),6)
 def test_split(self):
  p=m.registry();groups=list(p['split'].values());self.assertEqual(sorted(sum(groups,[])),p['sessions']);self.assertEqual(len(set(sum(groups,[]))),57)
 def test_sealed(self):
  with self.assertRaises(ValueError):m.saved.authorize_date('2024-12-10')
 def test_scale_causal(self):
  hist=[{'tr':i/100} for i in range(1,11)];self.assertAlmostEqual(m.scale(hist),.055);self.assertIsNone(m.scale(hist[:4]))
 def test_scale_no_missing_fill(self):self.assertIsNone(m.scale([{'tr':None}]*10))
 def test_eligibility(self):
  rows=[self.row()];d=self.row();self.assertTrue(m.intraday_eligible(d,rows)[0]);self.assertFalse(m.intraday_eligible(dict(d,Vo=11),rows)[0]);self.assertFalse(m.intraday_eligible(dict(d,H=102),rows)[0])
 def test_invalid_prices(self):self.assertFalse(m.valid(self.row(H=1)))
 def test_actions(self):self.assertTrue(m.action(self.row(AdjFactor=.5)));self.assertFalse(m.action(self.row()))
 def test_buckets_calendar(self):
  self.assertEqual(m.bucket('2024-11-01',900),'PM2');self.assertIsNone(m.bucket('2024-11-01',930));self.assertEqual(m.bucket('2024-11-05',930),'CL');self.assertIsNone(m.bucket('2024-11-05',720))
 def test_5m_no_fill(self):
  rows=[self.row('09:0'+str(i)) for i in range(5)];self.assertEqual(len(m.bars5('2024-11-05',rows)),1);self.assertEqual(m.bars5('2024-11-05',rows[:4]),[])
 def test_vwap(self):
  rows=[self.row('09:0'+str(i),Va=1000+100*i) for i in range(5)];self.assertEqual(m.bars5('2024-11-05',rows)[0]['VWAP'],120)
 def test_duplicate_minute(self):
  with self.assertRaises(ValueError):m.bars5('2024-11-05',[self.row(),self.row()])
 def test_future_vwap_poison(self):
  rows=[self.row('09:0'+str(i)) for i in range(5)];base=m.bars5('2024-11-05',rows)
  rows.append(self.row('10:00',Va=1e10));self.assertEqual(base,m.bars5('2024-11-05',rows))
 def test_response_unknown(self):
  b=[{'t':570,'C':100},{'t':580,'C':120}];self.assertIsNone(m.response(b,0,30,lambda x:True))
 def test_response_window(self):
  b=[{'t':570+5*i,'C':100+i} for i in range(7)];self.assertEqual(m.response(b,0,30,lambda x:x['C']>=106),1.)
 def test_response_lunch(self):
  b=[{'t':680+5*i,'C':100} for i in range(7)];self.assertIsNone(m.response(b,0,30,lambda x:True))
 def test_swing_confirmation(self):
  b=[{'t':545+i*5,'C':c} for i,c in enumerate([100,101,102,101.4])];s=m.swings(b,1);self.assertEqual(s[0]['confirmedAt'],560);self.assertEqual(s[0]['extremeAt'],555);self.assertEqual(m.swings(b[:3],1),[])
 def test_swing_future_invariance(self):
  b=[{'t':545+i*5,'C':c} for i,c in enumerate([100,101,102,101.4,100,101])];self.assertEqual(m.swings(b[:4],1)[0],m.swings(b,1)[0])
 def test_swing_gap_reset(self):self.assertEqual(m.swings([{'t':545,'C':100},{'t':560,'C':120},{'t':565,'C':110}],1),[])
 def test_daily_atoms(self):
  d=self.row(O=100,H=110,L=99,C=109,Va=10000);pr=self.row();h=[dict(Va=1000,tr=.1,ret=.01,C=100,s=.1)]*10;x=m.daily_traits(d,pr,h,.05);self.assertEqual(x['large_up'],1);self.assertEqual(x['value_shock'],1)
 def test_neff(self):
  x=np.tile(np.arange(24.)[:,None],(1,3));self.assertTrue(np.all(m.neff(x)<24));self.assertTrue(np.all(m.neff(x)>0))
 def test_neff_missing(self):self.assertEqual(m.neff(np.full((20,1),np.nan))[0],0)
 def test_fdr(self):np.testing.assert_allclose(m.fdr([.01,.04,.5]),[.03,.06,.5])
 def test_bootstrap_bounds(self):
  w=m.block_weights(23,20,np.random.default_rng(1));np.testing.assert_equal(w.sum(1),23)
 def test_peer_no_b_fit(self):
  c=np.arange(120*4).reshape(120,4);a=np.arange(120.)
  _,_,b1,_,_=m.fit_peer((c,c),a,a);_,_,b2,_,_=m.fit_peer((c,c*100),a,a*100);np.testing.assert_equal(b1,b2)
 def test_rate_profile(self):
  v,raw,n,e=m.profile(np.array([[1.,0],[0,1],[1,1]]),'rate');self.assertTrue(np.isfinite(v).all());np.testing.assert_allclose(raw,[2/3,2/3])
 def test_transform(self):self.assertAlmostEqual(m.transform([.5],'share')[0],0);self.assertAlmostEqual(m.transform([0],'fisher')[0],0)
 def test_production_rejection(self):
  for x in ({},{'evidence_class':'HISTORICAL_RECONSTRUCTION'},{'evidence_class':'PIT_VERIFIED','labels':m.LABELS},{'evidence_class':'PIT_VERIFIED'}):
   with self.assertRaises(ValueError):m.production_load(x)
 def test_deterministic_gzip(self):
  with tempfile.TemporaryDirectory() as t:
   a,b=Path(t)/'a',Path(t)/'b';m.writegz(a,{'x':np.nan});m.writegz(b,{'x':np.nan});self.assertEqual(a.read_bytes(),b.read_bytes())
 def test_safety(self):self.assertTrue(all(v is False for v in m.registry()['safety'].values()))
 def test_no_fit_symbol_feature(self):self.assertEqual(m.registry()['statistics']['peer'],['logVa','logS','logPrice','observedMinuteCoverage'])
 def test_assess_all_insufficient(self):
  p=m.registry();a=np.full((57,2,73),np.nan);cov=np.ones((57,2,4));eligible=np.zeros((57,2,2),bool)
  r,prof,g=m.assess(a,cov,eligible,p,np.zeros((57,2)));self.assertEqual(len(r),73);self.assertFalse(g['complete']);self.assertEqual(g['usable'],0)
if __name__=='__main__':unittest.main()
