import copy,unittest
from unittest.mock import patch
import numpy as np
from scripts import phase57_behavior_full144 as f
class Full144Tests(unittest.TestCase):
 def fixture(self,day='2025-08-25',time='15:00'):
  m={'sessionDate':day,'decisionTimeJst':time,'decisionPrice':100}
  rows=[{'Date':day,'Time':f'{t//60:02d}:{t%60:02d}','Code':'11110','O':100,'H':102,'L':99,'C':101,'Vo':1,'Va':100} for t in list(range(900,925))+[930]]
  return m,rows,{'Date':day,'O':100,'H':102,'L':99,'C':101,'Vo':len(rows),'Va':100*len(rows)}
 def test_preclosing_no_synthetic_five_minutes(self):
  m,rs,d=self.fixture();x=f.labels_for_raw(m,rs,d);self.assertIsNotNone(x['mae30']);self.assertEqual(x['fullStatus'],'AVAILABLE');self.assertEqual(len(rs),26)
 def test_no_auction_no_session_endpoint(self):
  m,rs,d=self.fixture();rs.pop();d['Vo']-=1;x=f.labels_for_raw(m,rs,d);self.assertIsNone(x['returnEnd']);self.assertIsNone(x['return30'])
 def test_source_acquisition_miss_reconciliation(self):
  m,rs,d=self.fixture();rs.pop(0);x=f.labels_for_raw(m,rs,d);self.assertEqual(x['fullReason'],'SOURCE_DAILY_RECONCILIATION_FAILED')
 def test_whole_five_minute_gap_not_filled(self):
  m,rs,d=self.fixture();rs=rs[5:];d['Vo']=len(rs);x=f.labels_for_raw(m,rs,d);self.assertIsNone(x['mae30']);self.assertIsNotNone(x['maeEnd'])
 def test_endpoint_independent_denominators(self):
  m,rs,d=self.fixture();d['Vo']=999;x=f.labels_for_raw(m,rs,d);self.assertIsNotNone(x['mae30']);self.assertIsNone(x['maeEnd'])
 def test_lunch_not_wallclock_return(self):
  m,rs,d=self.fixture(time='11:30');x=f.labels_for_raw(m,rs,d);self.assertIsNone(x['mae30'])
 def test_postclose_not_measured(self):
  m,rs,d=self.fixture(time='15:30');x=f.labels_for_raw(m,rs,d);self.assertIsNone(x['mfeEnd']);self.assertIsNone(x['mae30'])
 def test_duplicate_source_rejected(self):
  m,rs,d=self.fixture()
  with self.assertRaises(AssertionError):f.labels_for_raw(m,rs+[rs[0]],d)
 def test_past_trait_not_final_backfill(self):
  meta={'sessions':['2025-08-20','2025-08-21','2025-08-22'],'codes':['11110'],'targets':{'daily':[{'id':'x','transform':'identity','tier':'daily','globalStatus':'USABLE'}]}}
  z={'daily':np.ones((3,1,1)),'cov':np.ones((3,1,4)),'eligible':np.ones((3,1,2),bool)};tr={('11110','daily','x'):{'status':'PASS','computedThrough':'2025-08-21T15:30:00+09:00','availableAt':'2025-08-21T15:31:00+09:00'}}
  def snap(data,cv,eligible,item,ix):return {'raw':[1],'post':[2],'sd':[1],'eff':[30],'n':[30],'coverage':[1]}
  with patch.object(f.s,'snapshot',side_effect=snap),patch.object(f.s,'sample',return_value='HIGH'),patch.object(f.s,'drift',return_value=[None]):
   a=f.who_day(meta,z,'2025-08-21',['11110'],tr);self.assertIsNone(a['11110'][0]['value']);self.assertEqual(a['11110'][0]['traitValue'],2)
   c=f.who_day(meta,z,'2025-08-22',['11110'],tr);self.assertEqual(c['11110'][0]['value'],2)
   z['daily'][1:]=999;self.assertEqual(a,f.who_day(meta,z,'2025-08-21',['11110'],tr))
 def test_manifest_all144_not_saved55(self):
  p=f.verify();self.assertEqual(len(p['cohortSessions']),144);self.assertEqual([len(p[k]) for k in ['fitSessions','embargoSessions','evaluationSessions']],[80,5,59])
if __name__=='__main__':unittest.main()
