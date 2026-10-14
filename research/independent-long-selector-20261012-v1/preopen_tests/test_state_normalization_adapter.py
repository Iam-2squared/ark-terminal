import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate_preopen_state import normalized_coordinates,terminal_segment
from preopen_selector import PreopenError

class CausalNormalization(unittest.TestCase):
    def test_constant_series_has_fixed_positive_scale_and_exact_origin(self):
        previous=[{'Date':'2024-11-13','Time':t,'O':'100','H':'100','L':'100','C':'100'} for t in ('12:30','12:31','12:32','12:33','15:30')]
        current=[{'O':'100','H':'101','L':'99','C':'100'}]
        a=normalized_coordinates(previous,current,80);b=normalized_coordinates(previous,current,120)
        self.assertEqual(a['coordinates'],b['coordinates'])
        self.assertEqual(a['U'],b['U'])
        self.assertEqual(a['coordinates'][0]['C'],'0.000000000000000000000000')
        self.assertGreater(float(a['U']),0)
        self.assertEqual(a['previous_return_pairs_N'],2)

    def test_gap_and_nonpositive_scale_input_are_not_filled(self):
        previous=[{'Date':'2024-11-13','Time':t,'C':'100'} for t in ('12:30','12:33')]
        with self.assertRaisesRegex(PreopenError,'INSUFFICIENT_LOOKBACK'):
            normalized_coordinates(previous,[],80)
        with self.assertRaisesRegex(PreopenError,'NONPOSITIVE'):
            normalized_coordinates([{'Date':'2024-11-13','Time':t,'C':'0'} for t in ('12:30','12:31','12:32')],[],80)

    def test_missing_actual_continuous_close_is_not_carried(self):
        rows=[{'Time':t} for t in ('12:30','12:31','15:22','15:23','15:24','15:30')]
        self.assertEqual([r['Time'] for r in terminal_segment(rows,'2024-11-13')],['15:22','15:23','15:24'])
        self.assertEqual(terminal_segment(rows[:-2],'2024-11-13'),[])
