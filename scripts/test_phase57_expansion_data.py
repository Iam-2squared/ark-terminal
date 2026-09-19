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
 def test_pagination_checkpoint_and_terminal_resume(self):
  from unittest.mock import MagicMock
  day='2021-09-21'
  payloads=[{'data':[{'Date':day,'Code':'11110'}],'pagination_key':'NEXT'},{'data':[{'Date':day,'Code':'22220'}]}]
  class Response:
   def __init__(self,x):self.x=x
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self):return json.dumps(self.x).encode()
  opener=MagicMock();opener.open.side_effect=[Response(x) for x in payloads]
  with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{'JQUANTS_API_KEY':'fake-test-key'}),patch.object(d.time,'sleep'),patch.object(d.urllib.request,'build_opener',return_value=opener):
   budget={'requests':0,'limit':2};r=d.request_pages(day,'daily',tmp,budget)
   self.assertEqual(r['rows'],2);self.assertEqual(budget['requests'],2)
   self.assertIn('pagination_key=NEXT',opener.open.call_args_list[1].args[0].full_url)
   self.assertFalse((Path(tmp)/day/'daily-checkpoint.json').exists())
   r=d.request_pages(day,'daily',tmp,{'requests':0,'limit':0});self.assertTrue(r['reused'])
   pages=json.loads((Path(tmp)/day/'daily-pages.json').read_text());(Path(tmp)/day/'daily-pages.json').unlink()
   (Path(tmp)/day/'daily-checkpoint.json').write_text(json.dumps({'pages':pages,'nextCursor':None,'seen':['NEXT']}))
   d.request_pages(day,'daily',tmp,{'requests':0,'limit':0});self.assertEqual(opener.open.call_count,2)
 def test_failed_next_page_retains_first_page_checkpoint(self):
  from unittest.mock import MagicMock
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self):return b'{"data":[{"Date":"2021-09-21","Code":"11110"}],"pagination_key":"NEXT"}'
  opener=MagicMock();opener.open.side_effect=[Response(),TimeoutError('fixture')]
  with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{'JQUANTS_API_KEY':'fake-test-key'}),patch.object(d.time,'sleep'),patch.object(d.urllib.request,'build_opener',return_value=opener):
   with self.assertRaises(TimeoutError):d.request_pages('2021-09-21','daily',tmp,{'requests':0,'limit':2})
   x=json.loads((Path(tmp)/'2021-09-21/daily-checkpoint.json').read_text());self.assertEqual(len(x['pages']),1);self.assertEqual(x['nextCursor'],'NEXT')
 def test_safe_archive_path(self):
  self.assertIsNone(d.base.archive_target('raw/jquants-v2/2024-12-10/minute-pages.json',set(d.plan()['intradayDevelopment'])))
  with self.assertRaises(ValueError):d.base.archive_target('../jquants-v2/2021-09-21/daily-pages.json',{'2021-09-21'})
if __name__=='__main__':unittest.main()
