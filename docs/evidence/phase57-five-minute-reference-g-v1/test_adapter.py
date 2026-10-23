"""Synthetic input-adapter tests; no market files are read here."""
import ast
import importlib.util
import json
from pathlib import Path
import unittest
from fractions import Fraction as F
import generate_reference as g
ROOT=Path(__file__).parent
DEFINITION=ROOT/'definition' if (ROOT/'definition').exists() else ROOT.parents[1]/'phase57-five-minute-entry-state/mechanical-v1'
r=g.load_ref(DEFINITION)

def raw(ts,prices=None):
 return [[t,p,p,p,p,1,p] for t,p in zip(ts,prices or [100]*len(ts))]

class AdapterTests(unittest.TestCase):
 def test_start_to_end(self):
  b,a,o=g.convert_rows(raw([540,541,542,543,544]),'2025-06-02');self.assertEqual([x.end for x in b],[541,542,543,544,545]);self.assertFalse(a or o)
 def test_no_received_at_invented(self):
  b,_,_=g.convert_rows(raw([540]),'2025-06-02');self.assertIsNone(b[0].available_at)
 def test_current_future_bar_not_in_prefix(self):
  b,_,_=g.convert_rows(raw([543,544,545]),'2025-06-02');self.assertEqual([x.end for x in b if x.end<=545],[544,545])
 def test_lunch_auction_not_shifted(self):
  b,a,_=g.convert_rows(raw([689,690,750]),'2025-06-02');self.assertEqual([x.end for x in b],[690,751]);self.assertEqual(a[0][0],690)
 def test_close_auction_separate(self):
  b,a,_=g.convert_rows(raw([924,930]),'2025-06-02');self.assertEqual([x.end for x in b],[925]);self.assertEqual(a[0][0],930)
 def test_old_close(self):
  b,a,_=g.convert_rows(raw([899,900]),'2024-10-01');self.assertEqual([x.end for x in b],[900]);self.assertEqual(a[0][0],900)
 def test_no_after_1525_regular(self):
  b,_,o=g.convert_rows(raw([925]),'2025-06-02');self.assertFalse(b);self.assertEqual(len(o),1)
 def test_duplicate_rejected(self):
  with self.assertRaisesRegex(ValueError,'DUPLICATE'):g.convert_rows(raw([540,540]),'2025-06-02')
 def test_unsorted_rejected(self):
  with self.assertRaisesRegex(ValueError,'UNSORTED'):g.convert_rows(raw([542,541]),'2025-06-02')
 def test_noninteger_minute_rejected(self):
  with self.assertRaisesRegex(ValueError,'TIME'):g.convert_rows(raw([540.5]),'2025-06-02')
 def test_columns_rejected(self):
  with self.assertRaisesRegex(ValueError,'COLUMNS'):g.convert_rows([[540,100]],'2025-06-02')
 def test_ohlc_rejected(self):
  with self.assertRaisesRegex(ValueError,'INVALID_OHLC'):g.convert_rows([[540,100,99,98,100,1,100]],'2025-06-02')
 def test_nan_rejected(self):
  with self.assertRaisesRegex(ValueError,'NONFINITE'):g.convert_rows(raw([540],[float('nan')]),'2025-06-02')
 def test_negative_volume_rejected(self):
  with self.assertRaisesRegex(ValueError,'NEGATIVE'):g.convert_rows([[540,100,100,100,100,-1,100]],'2025-06-02')
 def test_grid_never_retimed(self):
  es=g.ends_for('2025-06-02');a=r.grid(570,es);b=r.grid(570,es);self.assertEqual(a,b);self.assertEqual(a['checkpoints'][0:3],[570,575,580])
 def test_late_selection_grid(self):self.assertEqual(r.grid(900,g.ends_for('2025-06-02'))['checkpoints'],[900,905,910,915,920,925])
 def test_lunch_grid(self):self.assertEqual(r.grid(688,g.ends_for('2025-06-02'))['checkpoints'][1],753)
 def test_end_tail(self):self.assertEqual(r.grid(923,g.ends_for('2025-06-02'))['tailEnds'],[924,925])
 def test_exact_fraction_retained(self):self.assertEqual(g.clean(F(1,3)),{'numerator':1,'denominator':3})
 def test_canonical_replay(self):self.assertEqual(g.encoded({'b':F(2,3),'a':1}),g.encoded({'a':1,'b':F(2,3)}))
 def test_no_models_or_legacy_import(self):
  tree=ast.parse((ROOT/'generate_reference.py').read_text());names=[]
  for n in ast.walk(tree):
   if isinstance(n,ast.Import):names += [x.name for x in n.names]
   if isinstance(n,ast.ImportFrom):names.append(n.module or '')
  self.assertFalse(any(any(k in x for k in ('sklearn','scripts.phase57','requests','httpx')) for x in names))
 def test_hashes_fixed(self):
  self.assertEqual(g.sha(DEFINITION/'reference.py'),g.DEF_PINS['reference.py']);self.assertEqual(r.ORACLE_HORIZON,10)

if __name__=='__main__':unittest.main(verbosity=2)
