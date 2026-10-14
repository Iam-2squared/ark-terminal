import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate_preopen_state import normalized_coordinates,terminal_segment,state_bar
from preopen_selector import PreopenError

class CausalNormalization(unittest.TestCase):
    def test_frozen_bar_receives_interval_tag_and_valid_closed_time(self):
        from dataclasses import dataclass
        from decimal import Decimal
        @dataclass
        class StrictBar:
            t:int;o:Decimal;h:Decimal;l:Decimal;c:Decimal;known_at:int;source:str;auction:str
            def valid(self):
                return (type(self.t) is int and self.known_at==self.t
                        and self.l<=min(self.o,self.c)<=max(self.o,self.c)<=self.h
                        and isinstance(self.auction,str) and bool(self.auction))
        t,bar=state_bar({'Time':'15:24'}, {'O':'-1','H':'2','L':'-2','C':'1'},StrictBar,Decimal)
        self.assertEqual(t,925)
        self.assertEqual(bar.auction,'CONTINUOUS_PM')
        self.assertTrue(bar.valid())
        with self.assertRaisesRegex(PreopenError,'STATE_NORMALIZED_BAR_SCHEMA_REJECTED'):
            state_bar({'Time':'15:24'}, {'O':'-1','H':'0','L':'-2','C':'1'},StrictBar,Decimal)

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
