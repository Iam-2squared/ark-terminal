import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import phase57_expansion_data as d
class ExpansionBoundaryTests(unittest.TestCase):
 def test_all_partitions_disjoint_from_seals(self):
  p=d.plan();self.assertFalse((set(p['dailyDevelopment'])|set(p['intradayDevelopment'])) & (set(p['commonHoldout'])|set(p['excluded'])))
 def test_holdout_requests_rejected_before_network(self):
  for day in d.plan()['commonHoldout']:
   for kind in ['daily','master','minute']:
    with self.assertRaisesRegex(ValueError,'ACQUISITION_BOUNDARY'):d.authorize(day,kind)
 def test_report19_rejected(self):
  with self.assertRaises(ValueError):d.authorize('2024-12-10','minute')
 def test_no_minute_for_daily_development(self):
  with self.assertRaises(ValueError):d.authorize('2021-09-21','minute')
 def test_matrix_complete_unique_bounded(self):
  p=d.plan();m=d.matrix();daily=[v for j in m if j['kind']=='daily' for v in j['dates']];minute=[v for j in m if j['kind']=='minute' for v in j['dates']]
  self.assertEqual(daily,p['dailyDevelopment']);self.assertEqual(minute,[x for x in p['intradayDevelopment'] if x not in p['reuseMinuteDates']]);self.assertEqual(len(minute),len(set(minute)));self.assertLessEqual(len(daily)*2+len(minute)*32,6000)
 def test_hash_tamper_rejected(self):
  original=d.base.sha
  with patch.object(d.base,'sha',side_effect=lambda p:'bad' if str(p).endswith('04_session_split_manifest.json') else original(p)):
   with self.assertRaisesRegex(AssertionError,'SPLIT_HASH'):d.plan()
 def test_raw_hash_reuse_mismatch_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp)/'2021-09-21';folder.mkdir();(folder/'daily-pages.json').write_text(json.dumps([{'responseText':'{"data":[]}','responseSha256':'bad'}]))
   with self.assertRaisesRegex(AssertionError,'PAGE_HASH_MISMATCH'):d.request_pages('2021-09-21','daily',tmp,{'requests':0,'limit':1})
 def test_safe_archive_path(self):
  self.assertIsNone(d.base.archive_target('raw/jquants-v2/2024-12-10/minute-pages.json',set(d.plan()['intradayDevelopment'])))
  with self.assertRaises(ValueError):d.base.archive_target('../jquants-v2/2021-09-21/daily-pages.json',{'2021-09-21'})
if __name__=='__main__':unittest.main()
