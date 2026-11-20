import copy,csv,datetime as dt,gzip,hashlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import phase57_dictionary_pit_recovery as m
from scripts import phase57_behavior_dictionary as old
DAY='2024-09-17';CUT='2024-09-18T09:00:00+09:00';END=DAY+'T15:00:00+09:00'
class PITRecovery(unittest.TestCase):
 def test_precommit_pins_and_thresholds(self):m.protocol()
 def test_receipt_bound_not_backdated(self):
  r=m.bound(END,'2026-09-15T01:00:00Z',CUT,'sha');self.assertFalse(r['historicalAvailable']);self.assertEqual(r['upper'],'2026-09-15T01:00:00Z');self.assertIsNone(r['exactKnownAt'])
 def test_historical_receipt_upper_can_qualify(self):self.assertTrue(m.bound(END,DAY+'T17:00:00+09:00',CUT,'sha')['historicalAvailable'])
 def test_knownat_bound_without_hash_rejected(self):self.assertFalse(m.bound(END,DAY+'T17:00:00+09:00',CUT,None)['historicalAvailable'])
 def test_missing_receipt_not_schedule(self):self.assertEqual(m.bound(END,None,CUT,'sha')['status'],'UNUSABLE')
 def test_receipt_before_event_rejected(self):
  with self.assertRaises(ValueError):m.bound(END,DAY+'T09:00:00+09:00',CUT,'sha')
 def test_master_effective_is_not_publication_lower(self):self.assertIsNone(m.bound(None,'2026-09-15T01:00:00Z',CUT,'sha')['lower'])
 def test_timezone_not_optional(self):
  with self.assertRaises(ValueError):m.bound(END,'2024-09-17T18:00:00',CUT,'sha')
 def test_partial_cannot_be_profile(self):
  r=m.family_eligibility(True,True,True,110,False,False);self.assertTrue(r['retrospectiveInputEligible']['T1_LOG_RANGE']);self.assertFalse(any(r['historicalProfileEligible'].values()))
 def test_identity_still_required(self):self.assertFalse(any(m.family_eligibility(True,True,True,110,True,False)['historicalProfileEligible'].values()))
 def test_actions_not_needed_for_within_session_range(self):self.assertTrue(m.family_eligibility(True,True,True,110,True,True)['historicalProfileEligible']['T1_LOG_RANGE'])
 def test_exrt_does_not_admit_gap(self):self.assertFalse(m.family_eligibility(True,True,True,110,True,True)['historicalProfileEligible']['T4_GAP_UP_RATE'])
 def test_mixed_auction_not_continuous_volume(self):self.assertFalse(m.family_eligibility(True,True,True,110,True,True)['historicalProfileEligible']['T3_AM_VOLUME_SHARE'])
 def test_absent_minute_not_no_trade(self):self.assertEqual(m.missing_reason({'absent':True,'providerOmitsNoTrade':True,'dailyReconciled':True}),'UNKNOWN')
 def test_explicit_missing_classes(self):
  for k,v in [('outsideSession','OUTSIDE_SESSION'),('notListedVerified','NOT_LISTED'),('haltVerified','HALT'),('specialQuoteVerified','SPECIAL_QUOTE'),('feedOutageVerified','DATA_MISSING')]:self.assertEqual(m.missing_reason({k:True}),v)
 def test_no_trade_requires_both_proofs(self):
  self.assertEqual(m.missing_reason({'noTradeVerified':True}),'UNKNOWN');self.assertEqual(m.missing_reason({'noTradeVerified':True,'completeFeedVerified':True}),'NO_TRADE')
 def test_classes_require_real_contract(self):
  self.assertEqual(m.classify(False,True,True,True),'PIT_UNUSABLE');self.assertEqual(m.classify(True,False,True,True),'PIT_PARTIAL');self.assertEqual(m.classify(True,True,False,True),'PIT_PARTIAL');self.assertEqual(m.classify(True,True,True,True),'PIT_VERIFIED')
 def test_observed_coverage_does_not_pass_gate(self):
  g=m.coverage_gate(100,0,0,0,m.protocol());self.assertEqual(g['status'],'BLOCKED_INPUT_COVERAGE')
 def test_g2_boundaries_unchanged(self):
  self.assertTrue(m.coverage_gate(100,95,.99,300,m.protocol())['pass'])
  for args in [(100,94,.99,300),(100,95,.989,300),(100,95,.99,299)]:self.assertFalse(m.coverage_gate(*args,m.protocol())['pass'])
 def test_empty_coverage_no_pass(self):self.assertFalse(m.coverage_gate(0,0,1,300,m.protocol())['pass'])
 def test_three_complete_bars_make_one_return_pair(self):self.assertEqual(m.lag_pairs(set(range(540,555)),DAY),(3,1))
 def test_incomplete_bar_breaks_pairs(self):self.assertEqual(m.lag_pairs(set(range(540,555))-{547},DAY),(2,0))
 def test_lunch_cannot_make_lag_pair(self):self.assertEqual(m.lag_pairs(set(range(685,690))|set(range(750,760)),DAY),(3,0))
 def test_preclose_and_terminal_excluded(self):self.assertEqual(m.lag_pairs(set(range(925,931)),'2024-11-05'),(0,0))
 def test_20241105_session_extension(self):
  self.assertEqual(m.lag_pairs(set(range(900,915)),'2024-11-01'),(0,0));self.assertEqual(m.lag_pairs(set(range(900,915)),'2024-11-05'),(3,1))
 def test_reconciliation_not_tolerant_of_missing_trade(self):self.assertTrue(m.reconciles(100,100));self.assertFalse(m.reconciles(99,100));self.assertFalse(m.reconciles(0,None))
 def test_nonfinite_prices_rejected(self):
  for r in [{'O':1,'H':2,'L':.5,'C':float('nan')},{'O':1,'H':.9,'L':.5,'C':1}]:self.assertFalse(m.valid_ohlc(r))
 def test_name_change_and_code_gap_not_identity_recovery(self):
  h={'ABCD0':[{'day':'2024-09-17','nameHash':'a'},{'day':'2024-09-19','nameHash':'b'}]};r=m.identity_summary(h,['2024-09-17','2024-09-18','2024-09-19'])[0]
  self.assertEqual(r['unobservedBetween'],1);self.assertEqual(r['nameHashChanges'],1);self.assertIsNone(r['securityId']);self.assertIsNone(r['codeReuse'])
 def test_code_reuse_requires_explicit_effective_intervals(self):
  maps=[{'code':'X','securityId':'A','effectiveFrom':'2024-01-01','effectiveTo':'2024-09-01','knownAt':'2024-01-01T00:00:00Z'},{'code':'X','securityId':'B','effectiveFrom':'2024-09-01','effectiveTo':'2025-01-01','knownAt':'2024-09-01T00:00:00Z'}]
  self.assertEqual(old.resolve_security('X',DAY,CUT,maps),'B')
 def test_sealed_date_rejected_before_any_read(self):
  p=m.protocol()
  with patch.object(m,'sha',side_effect=AssertionError('READ')):
   with self.assertRaises(ValueError):m.session_audit('/does-not-exist','2025-01-10',p,{},None,{})
 def test_trial_prefix_exposure_preservation(self):
  prior=old.read(m.PRIOR/'measurement/02_exposure_ledger.json');self.assertEqual(prior['classificationCounts'],{'E2':38,'E3':38,'UNKNOWN_EXPOSURE':437})
 def test_t6_window_counts_no_lunch_pairs_or_stable_id(self):
  dates=[(dt.date(2024,1,1)+dt.timedelta(days=i)).isoformat() for i in range(19)]
  h={'X':[{'day':d,'lagPairs':10,'completeRegular':True} for d in dates]}
  r=m.window_availability(h,dates)[0];self.assertEqual(r['provisionalCodesT6Pairs100NEff12'],1);self.assertEqual(r['stableIdentityAdmittedSymbols'],0)
 def test_real_session_audit_fixture_full_and_missing(self):
  def page(rows):
   text=json.dumps({'data':rows});h=hashlib.sha256(text.encode()).hexdigest();return [{'page':1,'responseText':text,'responseSha256':h}],{'pageCount':1,'aggregateSha256':hashlib.sha256(json.dumps([h],separators=(',',':')).encode()).hexdigest()}
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);master=[{'Date':DAY,'Code':'X','Mkt':'0111','ProdCat':'011','CoName':'X'}]
   minute=[{'Date':DAY,'Code':'X','Time':f'{t//60:02}:{t%60:02}','O':1,'H':1,'L':1,'C':1,'Vo':1,'Va':1} for t in list(range(540,690))+list(range(750,900))]
   daily=[{'Date':DAY,'Code':'X','O':1,'H':1,'L':1,'C':1,'Vo':300,'Va':300,'ExRT':None,'AdjFactor':1}]
   metas={}
   for kind,rows in [('master',master),('daily',daily),('minute',minute)]:
    ps,meta=page(rows);(d/(kind+'-pages.json')).write_text(json.dumps(ps));metas[kind]=meta
   base={'sessionDate':DAY,'partition':'DEVELOPMENT_C','fetchedAt':'2026-09-15T01:00:00Z'}
   (d/'l0-manifest.json').write_text(json.dumps({**base,'master':metas['master'],'daily':metas['daily']}));(d/'l1-minute-manifest.json').write_text(json.dumps({**base,**metas['minute']}))
   prior={'files':{f.name:{'sha256':m.sha(f)} for f in d.iterdir()},'coverage':{'observedRegularMinuteSlots':300,'completeFiveMinuteBuckets':60}}
   target=io.StringIO();history={}
   r=m.session_audit(d,DAY,m.protocol(),prior,csv.writer(target),history)
   self.assertEqual(r['classification']['PIT_PARTIAL'],1);self.assertEqual(r['reconciliation']['bothReconciledDays'],1);self.assertFalse(any(r['historicalProfileEligibleByMetric'].values()));self.assertEqual(r['coverage']['full5mLagPairsWithinSession'],56)
 def test_safety_and_no_strategy_import(self):
  self.assertTrue(all(x is False for x in m.protocol()['safety'].values()));source=Path(m.__file__).read_text();self.assertNotIn('import requests',source);self.assertNotIn('import urllib',source);self.assertNotIn('phase57_causal_entry_exit',source)
 def test_precommit_definition_hash_unchanged(self):self.assertEqual(len(m.METRICS),8);self.assertEqual(m.protocol()['traitFamilies'],6)
 def test_no_eb_or_drift_measurement_before_input(self):self.assertIn('G1/G2',m.NA_REASON)
if __name__=='__main__':unittest.main()
