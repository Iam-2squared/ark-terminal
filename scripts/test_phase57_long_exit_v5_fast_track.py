import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'docs/evidence/phase57-long-exit-v5-fast-track'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

class FastTrackIntegrity(unittest.TestCase):
 def test_contract_pins_and_no_promotion(self):
  c=read(B/'contract.json');s=read(B/'summary.json')
  for p,h in c['pins'].items():self.assertEqual(sha(ROOT/p),h)
  self.assertEqual(sha(B/'contract.json'),s['contractSHA'])
  self.assertEqual(c['horizonBars'],5)
  self.assertEqual(s['status'],'V5_LONG_MEASUREMENT_BLOCKED')
  self.assertFalse(s['onlineStandaloneRuntimeResolved'])
  self.assertTrue(all(x is False for x in s['safety'].values()))
  self.assertTrue(all(x==0 for x in s['counts'].values()))
  for arm in s['arms'].values():
   self.assertEqual(arm['eligibleN'],0)
   self.assertTrue(all(x is None for x in arm['metrics'].values()))
 def test_all277_identity_no_unknown_as_flat(self):
  rows=read(B/'prefix-ledger.json');old=read(ROOT/'docs/evidence/phase57-msh-entry-long-v1-upstream-freeze/historical-enter-identities.json')
  self.assertEqual(len(rows),277)
  for a,b in zip(rows,old):
   for k,v in b.items():self.assertEqual(a[k],v)
   self.assertIsNone(a['replay']['netReturnPct'])
  s=read(B/'summary.json')['rawMarketPrefixDiagnostic']
  self.assertEqual(sum(s['states'].values()),277)
  self.assertEqual(s['defensiveObserved'],s['reclaimObserved']+s['noReclaimThroughBar5Observed']+s['unknownReasons']['MISSING_PREFIX_BAR'])
 def test_saved_diagnostic_reproducible(self):
  with tempfile.TemporaryDirectory() as out:
   subprocess.run(['node','scripts/phase57_long_exit_v5_fast_track.mjs',out],cwd=ROOT,check=True,capture_output=True)
   for name in ['summary.json','prefix-ledger.json']:self.assertEqual((Path(out)/name).read_bytes(),(B/name).read_bytes())

if __name__=='__main__':unittest.main()
