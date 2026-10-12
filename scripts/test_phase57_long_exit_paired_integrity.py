"""Verify saved diagnostic evidence without provider access or research replay."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-long-exit-v345-paired'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

class Integrity(unittest.TestCase):
    def test_pins_and_identity(self):
        c=read(BASE/'contract.json')
        for p,h in c['sourcePins'].items():self.assertEqual(sha(ROOT/p),h,p)
        raw=gzip.decompress((BASE/'paths.json.gz').read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(),(BASE/'paths.json.sha256').read_text().strip())
        d=json.loads(raw)
        self.assertEqual(d['contractSHA'],sha(BASE/'contract.json'))
        ledger=read(ROOT/'docs/evidence/phase57-msh-entry-long-v1-upstream-freeze/historical-enter-identities.json')
        self.assertEqual(len(d['events']),277)
        self.assertEqual({e['selectorEventId'] for e in ledger},{e['selectorEventId'] for e in d['events']})
        indexed={e['selectorEventId']:e for e in d['events']}
        for e in ledger:
            for k,v in e.items():self.assertEqual(indexed[e['selectorEventId']][k],v)
        self.assertEqual(len(d['sources']),76)
        self.assertEqual(sorted(s['sessionDate'] for s in d['sources']),sorted(c['sessionList']))
        self.assertTrue(all(s['partition'].startswith('DEVELOPMENT_') for s in d['sources']))
        self.assertTrue(all(v is False for v in d['safety'].values()))
        self.assertTrue(all(v==0 for v in d['counts'].values()))

    def test_saved_path_summary_reproducible_and_not_five_arm_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable,str(ROOT/'scripts/summarize_phase57_long_exit_paired.py'),str(BASE/'paths.json.gz'),tmp],check=True,capture_output=True)
            for p in ['summary.json','entry-path-classification.json']:
                self.assertEqual((Path(tmp)/p).read_bytes(),(BASE/p).read_bytes())
        s=read(BASE/'summary.json')
        self.assertEqual(s['verdict'],'EXIT_ARCHITECTURE_INCONCLUSIVE')
        self.assertEqual(s['completeFiveArmPairs'],0)
        self.assertEqual(s['pairedReferenceOnly']['n'],41)
        self.assertEqual(sum(s['pathTypes'].values()),277)
        for arm in s['requestedExitArms'].values():
            self.assertIsNone(arm['netSumPctPoints'])
            self.assertFalse(arm['comparisonPermitted'])

    def test_new_path_matches_published_entry_risk_reference(self):
        s=read(BASE/'summary.json')['horizons']['30']
        self.assertEqual(s['availability']['count'],181)
        self.assertAlmostEqual(s['maePct']['median'],-1.5337423312883458)
        self.assertAlmostEqual(s['maePct']['p05'],-10.256410256410254)
        self.assertAlmostEqual(s['maePct']['min'],-35.29411764705882)
        self.assertEqual([s['mfeAtLeast'][str(k)]['count'] for k in [1,2,3,5]],[156,132,95,56])

if __name__=='__main__':unittest.main()
