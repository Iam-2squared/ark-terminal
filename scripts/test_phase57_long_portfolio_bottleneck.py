import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from scripts.phase57_long_portfolio_bottleneck import OUT, read, run, digest

class BottleneckIntegrity(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=read(OUT/'diagnostic.json')
 def test_partition(self):
  c=self.d['coverage'];self.assertEqual(len({r['eventId'] for r in c['perEntry']}),277)
  self.assertEqual(sum(c['reasons'].values()),104)
  self.assertEqual(sum(r['included'] for r in c['perEntry']),173)
  self.assertEqual(c['overlappingFlags']['unresolvedLongExit'],85)
 def test_accounting(self):
  d=self.d['drawdown'];self.assertLess(d['curveReconciliationMaxErrorJpy'],1e-5)
  self.assertAlmostEqual(sum(r['totalEquityChangeJpy'] for r in d['positions']),-d['episode']['drawdownJpy'],places=5)
  a=self.d['allocation'];self.assertAlmostEqual(a['commonQuantityEffectJpy']+a['rankOnlyPnlJpy']-a['equalOnlyPnlJpy'],a['rankMinusEqualJpy'],places=5)
 def test_safety_and_pins(self):
  self.assertTrue(all(v is False for v in self.d['safety'].values()))
  self.assertEqual(len(self.d['safety']),9)
  for k in ['providerRequests','freshConsumption','oosAccess','frozenComponentChanges']:self.assertEqual(self.d[k],0)
  m=read(OUT/'manifest.json')
  for p,h in m['sha256'].items():self.assertEqual(digest(p),h,p)
 def test_reproduction_and_symbol_removal(self):
  with tempfile.TemporaryDirectory() as td:
   with contextlib.redirect_stdout(io.StringIO()):run(Path(td))
   for name in ['diagnostic.json','sensitivity-ledgers.json.gz']:self.assertEqual(digest(Path(td)/name),digest(OUT/name))
  ledger=read(OUT/'sensitivity-ledgers.json.gz')['EXCLUDE_TOP1_SYMBOL']
  self.assertTrue(all(t['symbol']!='89180' for t in ledger['closedTrades']))
  self.assertLess(ledger['totalReturnPct'],0)
if __name__=='__main__':unittest.main()
