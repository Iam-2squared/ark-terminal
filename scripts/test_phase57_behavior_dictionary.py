import copy,hashlib,io,json,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import phase57_behavior_dictionary as m
DAY='2024-09-17';CUT=DAY+'T15:01:00+09:00'
def observation():return {'eventTime':DAY+'T14:55:00+09:00','knownAt':DAY+'T15:00:00+09:00','availableAt':DAY+'T15:00:00+09:00','value':1}
def archive(items):
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz') as t:
  for name,data in items:
   i=tarfile.TarInfo(name);i.size=len(data);t.addfile(i,io.BytesIO(data))
 b.seek(0);return b
class DictionaryContracts(unittest.TestCase):
 def test_protocol_source_pins(self):m.protocol()
 def test_sealed_and_report_rejected_before_read(self):
  for d in ['2024-12-10','2025-01-10','2026-09-19']:
   with patch.object(m,'read',side_effect=AssertionError('READ_OCCURRED')):
    with self.assertRaises(ValueError):m.authorize_date(d,{'sessions':{'auditAndExploration':[DAY]}})
 def test_future_poison(self):
  r=observation();poison={**r,'knownAt':'2026-09-19T00:00:00+09:00','value':9999}
  self.assertEqual(m.available([r],CUT),m.available([r,poison],CUT))
 def test_negative_control_canary(self):
  r=observation();r['eventTime']='2025-01-01T00:00:00+09:00';self.assertEqual(m.available([r],CUT),[])
 def test_truncation_invariance(self):
  r=observation();later={**r,'eventTime':DAY+'T15:02:00+09:00','knownAt':DAY+'T15:03:00+09:00'}
  self.assertEqual(m.available([r,later],CUT),m.available([r],CUT))
 def test_unknown_knownat_not_backdated(self):
  r=observation();del r['knownAt'];r['fetchedAt']='2026-09-19T00:00:00+09:00';self.assertEqual(m.available([r],CUT),[])
 def test_bar_end_availability(self):
  r=observation();self.assertEqual(m.available([r],DAY+'T14:59:59+09:00'),[])
 def test_label_maturity(self):
  r=observation();r['maturityAt']=DAY+'T15:30:00+09:00';self.assertEqual(m.available([r],CUT),[])
 def test_timezone_required(self):
  with self.assertRaises(ValueError):m.instant('2024-09-17T15:00:00')
 def test_fitted_artifact_cutoff(self):
  a={'trainWindowEnd':DAY,'knownAt':DAY+'T16:00:00+09:00'}
  self.assertFalse(m.fitted_allowed(a,DAY+'T17:00:00+09:00'));self.assertTrue(m.fitted_allowed(a,'2024-09-18T09:00:00+09:00'))
 def test_future_fitted_knownat(self):self.assertFalse(m.fitted_allowed({'trainWindowEnd':'2024-09-16','knownAt':'2026-01-01T00:00:00+09:00'},CUT))
 def test_security_mapping_requires_effective_window(self):
  row={'code':'ABC','securityId':'stable','effectiveFrom':'2024-01-01','effectiveTo':'2025-01-01','knownAt':'2024-01-01T00:00:00+09:00'}
  self.assertEqual(m.resolve_security('ABC',DAY,CUT,[row]),'stable')
  with self.assertRaises(ValueError):m.resolve_security('ABC','2025-01-01','2025-01-01T09:00:00+09:00',[row])
 def test_current_master_not_retroactive(self):
  row={'code':'ABC','securityId':'stable','effectiveFrom':'2024-01-01','effectiveTo':'2025-01-01','knownAt':'2026-01-01T00:00:00+09:00'}
  with self.assertRaises(ValueError):m.resolve_security('ABC',DAY,CUT,[row])
 def test_ambiguous_mapping_rejected(self):
  row={'code':'ABC','securityId':'stable','effectiveFrom':'2024-01-01','effectiveTo':'2025-01-01','knownAt':'2024-01-01T00:00:00+09:00'}
  with self.assertRaises(ValueError):m.resolve_security('ABC',DAY,CUT,[row,row])
 def test_corporate_action_pit(self):
  a={'effectiveDate':DAY,'knownAt':'2024-09-16T00:00:00+09:00','versionHash':'hash'}
  self.assertTrue(m.corporate_action_allowed(a,CUT));a['knownAt']='2026-09-19T00:00:00+09:00';self.assertFalse(m.corporate_action_allowed(a,CUT))
 def test_adjustment_factor_not_sufficient(self):self.assertFalse(m.corporate_action_allowed({'AdjFactor':.5},CUT))
 def test_missing_no_fill(self):self.assertEqual(m.classify_missing({'volume':0,'rowAbsent':True}),'UNKNOWN')
 def test_missing_reason_evidence(self):
  for evidence,want in [({'completeFeedVerified':True,'noTradeVerified':True},'NO_TRADE'),({'feedOutageVerified':True},'DATA_MISSING'),({'haltOrSpecialQuoteVerified':True},'HALT_SPECIAL_QUOTE'),({'notListedVerified':True},'NOT_LISTED')]:self.assertEqual(m.classify_missing(evidence),want)
 def test_lunch_session_calendar(self):
  self.assertEqual(m.phase(DAY,690),'TERMINAL_AUCTION');self.assertEqual(m.phase(DAY,720),'OUTSIDE_REGULAR');self.assertEqual(m.phase(DAY,750),'REGULAR')
 def test_1500_1530_regime(self):
  self.assertEqual(m.phase('2024-11-01',900),'TERMINAL_AUCTION');self.assertEqual(m.phase('2024-11-05',900),'REGULAR');self.assertEqual(m.phase('2024-11-05',925),'PRECLOSE_NO_EXECUTION');self.assertEqual(m.phase('2024-11-05',930),'TERMINAL_AUCTION')
 def test_rolling_excludes_current_preserves_dates(self):self.assertEqual(m.rolling_sessions(['2024-09-13',DAY,'2024-09-18','2024-09-19'],'2024-09-19',2),[DAY,'2024-09-18'])
 def test_no_raw_symbol_no_selector_outcome(self):
  p={'symbol':'ABC','securityId':'S1','code':'ABC','selectorScore':4,'winner':True,'entryPnl':5,'value':.3}
  self.assertEqual(m.projected_profile(p),{'value':.3})
 def test_selector_agnostic_projection(self):
  p={'value':.3,'selectorRank':1};q={**p,'selectorRank':5,'selectorScore':999};self.assertEqual(m.projected_profile(p),m.projected_profile(q))
 def test_trial_append_only_chain(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'ledger.jsonl';a=m.append_trial(p,{'trialId':'A'});b=p.read_bytes();z=m.append_trial(p,{'trialId':'B'});self.assertTrue(p.read_bytes().startswith(b));self.assertEqual(z['previousHash'],m.digest(a))
   with self.assertRaises(ValueError):m.append_trial(p,{'trialId':'A'})
 def test_archive_selected_payload_only(self):
  items=[('phase57-l0-cache/phase57-long-only/raw/jquants-v2/'+DAY+'/daily-pages.json',b'[]'),('phase57-l0-cache/phase57-long-only/raw/jquants-v2/2024-12-10/daily-pages.json',b'REPORT_POISON'),('phase57-l0-cache/phase57-long-only/raw/jquants-v2/2025-01-10/daily-pages.json',b'SEALED_POISON')]
  with tempfile.TemporaryDirectory() as d:
   r=m.extract_stream(archive(items),d,{DAY});self.assertEqual(r['selectedFiles'],1);self.assertEqual(r['skippedFiles'],2);self.assertEqual([p.parent.name for p in Path(d).rglob('*.json')],[DAY])
 def test_archive_traversal_rejected(self):
  with self.assertRaises(ValueError):m.archive_target('../jquants-v2/'+DAY+'/daily-pages.json',{DAY})
 def test_archive_conflict_rejected(self):
  prefix='phase57-long-only/raw/jquants-v2/'+DAY+'/daily-pages.json'
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(AssertionError):m.extract_stream(archive([(prefix,b'[]'),(prefix,b'[1]')]),d,{DAY})
 def test_page_hash_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'pages.json';p.write_text(json.dumps([{'responseText':'{}','responseSha256':'bad'}]))
   with self.assertRaises(AssertionError):m.pages(p)
 def test_empty_admission_fails_closed(self):
  r=m.admission([]);self.assertFalse(r['pass']);self.assertEqual(r['traitsStatisticallyTested'],0)
 def test_exposure_never_resets_report_to_unseen(self):
  p=m.protocol();rs=m.exposure(p);r=[r for r in rs if r['sessionDate']=='2024-12-10'][0];self.assertEqual(r['exposure'],'E3');self.assertTrue(r['sealedThisTask']);self.assertFalse(r['dictionaryRawAuditAllowed'])
 def test_no_provider_or_strategy_import(self):
  source=Path(m.__file__).read_text();self.assertNotIn('import requests',source);self.assertNotIn('import urllib',source);self.assertNotIn('import phase57_causal_entry_exit',source)
 def test_deterministic_contract_serialization(self):self.assertEqual(m.digest({'a':1,'b':2}),m.digest({'b':2,'a':1}))
 def test_shrinkage_drift_blocked_not_fabricated(self):
  x=m.notapp('EARLY_KILL');self.assertIsNone(x['measuredValue']);self.assertEqual(x['status'],'NOT_APPLICABLE')
 def test_safety_all_false(self):self.assertTrue(all(x is False for x in m.protocol()['safety'].values()))
if __name__=='__main__':unittest.main()
