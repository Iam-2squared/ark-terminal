import contextlib,hashlib,importlib.util,io,json,tempfile,unittest
from pathlib import Path
from scripts.phase57_long_exit_continuation_development import runtime,run

M=runtime()
def event(cs):return {'direction':'LONG','expectedBars':len(cs),'future':[{'slot':i+1,'c':c,'h':c+1,'l':c-1,'missing':False,'end':f'2024-01-01T00:{5*(i+1):02}:00Z','minutes':5*(i+1)} for i,c in enumerate(cs)]}

class RuntimeTests(unittest.TestCase):
 def test_foundation_first_bar_reclaim_and_bar5(self):
  for mode in M.MODES[1:]:
   a=M.replay(event([-1,-2,-3,-4,-5,2]),mode);self.assertEqual(a['exitBar'],5);self.assertEqual(a['reason'],'BAR5_NO_RECLAIM');self.assertAlmostEqual(a['netPct'],-5.05)
   b=M.replay(event([-1,-2,-3,-4,0,1]),mode);self.assertTrue(b['recovered']);self.assertNotEqual(b['reason'],'BAR5_NO_RECLAIM')
 def test_close_peak_uses_only_observed_closes_not_future_or_high(self):
  e=event([1,4,2,8,9]);a=M.replay(e,'BAR5_CLOSE_PEAK_HALF');self.assertEqual(a['exitBar'],3)
  e['future'][0]['h']=999;e['future'][3]['c']=-99;self.assertEqual(M.replay(e,'BAR5_CLOSE_PEAK_HALF'),a)
 def test_state_two_declines_reset_on_recovery_and_equality(self):
  a=M.replay(event([-1,0,2,1,1,0,-1,8]),'BAR5_TWO_LOWER_CLOSES');self.assertEqual(a['exitBar'],7);self.assertTrue(a['recovered'])
 def test_missing_censors_before_decision_but_not_after_exit(self):
  e=event([1,4,2,8]);e['future'][1]['missing']=True;self.assertEqual(M.replay(e,'BAR5_CLOSE_PEAK_HALF')['status'],'CENSORED')
  e=event([1,4,2,8]);e['future'][3]['missing']=True;self.assertEqual(M.replay(e,'BAR5_CLOSE_PEAK_HALF')['exitBar'],3)
 def test_fixed_inherited12_and_calendar_cap(self):
  e=event(list(range(15)));self.assertEqual(M.replay(e,'FIXED12')['exitBar'],12)
  self.assertEqual(M.replay(event([-1,-2,-3]),'BAR5_FIXED12')['reason'],'CALENDAR_SESSION_CAP')
 def test_long_only_order_and_invalid_close(self):
  with self.assertRaises(ValueError):M.new_state('FIXED12',12,'SHORT')
  e=event([1]);e['future'][0]['slot']=2
  with self.assertRaises(ValueError):M.replay(e,'FIXED12')
  e=event([1]);e['future'][0]['c']=float('nan')
  with self.assertRaises(ValueError):M.replay(e,'FIXED12')
 def test_no_future_dependence_at_any_emitted_exit(self):
  for mode in M.MODES:
   e=event([-1,0,4,2,1,0,1,4,2,1,0,1,0]);a=M.replay(e,mode)
   for b in e['future'][a['exitBar']:]:b['c']=1000;b['h']=9999;b['l']=-9999
   self.assertEqual(M.replay(e,mode),a)

class SavedEvidenceTests(unittest.TestCase):
 @unittest.skipUnless(Path('docs/evidence/phase57-long-exit-continuation-v1/measurement.json').exists(),'pre-measurement')
 def test_saved_replay_identity_and_reproducibility(self):
  base=Path('docs/evidence/phase57-long-exit-continuation-v1')
  with tempfile.TemporaryDirectory() as tmp:
   with contextlib.redirect_stdout(io.StringIO()):s=run(tmp)
   for f in ['measurement.json','replay-ledger.json']:self.assertEqual((base/f).read_bytes(),(Path(tmp)/f).read_bytes())
  self.assertEqual(s['entries'],277);self.assertFalse(s['v4Dependency']);self.assertTrue(all(v is False for v in s['safety'].values()))
 def test_final_manifest_and_all_evidence_pins(self):
  base=Path('docs/evidence/phase57-long-exit-continuation-v1');p=base/'development-final.json';f=json.loads(p.read_text())
  self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),(base/'development-final.sha256').read_text().split()[0])
  for path,sha in {**f['evidencePins'],**f['upstreamPins']}.items():self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(),sha,path)
  self.assertEqual(f['selectedMode'],'BAR5_TWO_LOWER_CLOSES');self.assertEqual(f['fixedEntryCount'],277)
  self.assertEqual(f['freshValidation'],'PENDING');self.assertFalse(f['officialPass']);self.assertFalse(f['v4Dependency'])
  self.assertEqual(len(f['safety']),9);self.assertTrue(all(v is False for v in f['safety'].values()))
 def test_final_interface_is_single_cash_long_policy(self):
  sp=importlib.util.spec_from_file_location('final_policy',Path('predict/long-only/phase57_long_exit_development_final.py'));f=importlib.util.module_from_spec(sp);sp.loader.exec_module(f)
  with self.assertRaises(ValueError):f.new_position(12,direction='SHORT')
  with self.assertRaises(ValueError):f.new_position(12,cash_equity_only=False)
  with self.assertRaises(ValueError):f.new_position(0)
  with self.assertRaises(ValueError):f.on_completed_bar(M.new_state('FIXED12',12),event([1])['future'][0])
  e=event([-1,0,3,2,1,4]);s=f.new_position(6)
  for bar in e['future']:
   out=f.on_completed_bar(s,bar)
   if out['status']!='HOLD_RESEARCH_STATE':break
  self.assertEqual(out,M.replay(e,'BAR5_TWO_LOWER_CLOSES'))

if __name__=='__main__':unittest.main()
