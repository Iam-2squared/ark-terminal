"""Synthetic R20 substrate tests. Canonical producer tests are mandatory in CI."""
import gzip
import json
import os
import tempfile
import unittest
from pathlib import Path
from scripts import phase57_exit_checkpoints_v1 as s

DAY = '2025-06-02'


def entry(minute=570, price=100.05):
    return {'opportunity': DAY+'|TEST', 'session': DAY, 'symbol': 'TEST',
            'entryId': DAY+'|TEST|'+str(minute), 'entryMinute': minute, 'price': price}


def bars(start=540, end=620):
    return [[m, 100., 101., 99., 100., 10., 1000.] for m in range(start, end)]


def fake(day, now, prefix, previous_day, previous):
    return {'state': {'state': 'RISE', 'dataQuality': 'OK'},
            'signals': {f: dict(state=True, event=False, trigger=True) for f in s.FAMILIES},
            'signalContext': {}, 'activity': {}}


class Core(unittest.TestCase):
    def test_effective_entry_is_not_reslipped(self):
        e = entry(); self.assertEqual(s.entry_envelope(e), e)

    def test_future_label_keys_never_accessed(self):
        class OnlyEntry(dict):
            def __getitem__(self, key):
                if key not in s.ENTRY_KEYS: raise AssertionError('OUTCOME_READ')
                return super().__getitem__(key)
        self.assertEqual(s.entry_envelope(OnlyEntry(entry())), entry())

    def test_no_entry_has_no_checkpoints(self):
        e=entry();e.update(entryId=None,entryMinute=None,price=None)
        self.assertEqual(s.PositionObserver(e).grid, ())

    def test_invalid_no_entry_and_bad_identity(self):
        for patch in ({'entryId':None}, {'symbol':'OTHER'}, {'price':float('nan')}, {'entryMinute':True}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                s.entry_envelope({**entry(),**patch})

    def test_first_owned_bar_is_entry_minute_not_next5m(self):
        e=entry(571);p=s.closed_prefix(DAY,572,bars())
        f=s.position_features(e,572,p)
        self.assertEqual(f['observedOwnedBars'],1)
        self.assertEqual(f['activeMinutesHeld'],1)

    def test_no_entry_30minute_deadline_or_12bar_cap(self):
        self.assertEqual(s.checkpoint_grid(DAY,570)[-1],925)
        self.assertIn(850,s.checkpoint_grid(DAY,570))

    def test_lunch_grid_and_active_clock_are_distinct(self):
        grid=s.checkpoint_grid(DAY,689)
        self.assertEqual(grid[:2],(690,751))
        self.assertEqual(s.active_elapsed(DAY,689,751),2)
        self.assertEqual(s.active_elapsed(DAY,690,750),0)

    def test_terminal_observation_not_auction_fill(self):
        self.assertEqual(s.checkpoint_grid(DAY,924),(925,))
        with self.assertRaises(ValueError):s.checkpoint_grid(DAY,925)
        self.assertEqual(s.closed_prefix(DAY,931,bars(925,931)),())

    def test_old_calendar(self):
        self.assertEqual(s.checkpoint_grid('2024-11-01',899),(900,))

    def test_future_suffix_does_not_change_position(self):
        a=bars(540,580);b=bars(540,600)
        for r in b:
            if r[0]>=580:r[1:5]=[10000.,20000.,0.01,5000.]
        self.assertEqual(s.position_features(entry(),580,s.closed_prefix(DAY,580,a)),
                         s.position_features(entry(),580,s.closed_prefix(DAY,580,b)))

    def test_invalid_future_values_do_not_poison_past(self):
        a=bars(540,580)+[[590,-1,-1,-1,-1,-1,-1]]
        self.assertEqual(len(s.closed_prefix(DAY,580,a)),40)
        with self.assertRaises(ValueError):s.closed_prefix(DAY,591,a)

    def test_future_bars_rejected_by_decision_boundary(self):
        p=s.closed_prefix(DAY,581,bars())
        with self.assertRaises(ValueError):s.market_snapshot(DAY,580,p,None,(),fake)

    def test_late_publication_is_not_backdated(self):
        b=s.KnownBar(570,100,101,99,100,10,1000,575)
        self.assertEqual(s.closed_prefix(DAY,571,[b]),())
        self.assertEqual(s.closed_prefix(DAY,575,[b]),(b,))
        self.assertFalse(s.position_features(entry(),575,(b,))['freshClosedPrice'])

    def test_early_known_at_cannot_open_unclosed_bar(self):
        b=s.KnownBar(580,100,101,99,100,10,1000,579)
        self.assertEqual(s.closed_prefix(DAY,580,[b]),())
        with self.assertRaises(ValueError):s.closed_prefix(DAY,581,[b])

    def test_duplicate_and_bad_ohlc_fail_closed(self):
        for xs in (bars(570,571)*2, [[570,100,99,101,100,10,1000]]):
            with self.subTest(xs=xs),self.assertRaises(ValueError):s.closed_prefix(DAY,571,xs)

    def test_missing_is_not_zero_or_certified_full_mfe(self):
        p=s.closed_prefix(DAY,573,bars(570,571))
        f=s.position_features(entry(),573,p)
        self.assertEqual(f['missingOwnedBars'],2)
        self.assertIsNone(f['currentReturnPct'])
        self.assertIsNone(f['completePrefixMfePct'])
        self.assertIsNotNone(f['observedMfePct'])

    def test_preentry_high_is_not_owned(self):
        a=bars(569,572);a[0][2]=1000
        f=s.position_features(entry(),572,s.closed_prefix(DAY,572,a))
        self.assertEqual(f['observedRunningHigh'],101.)

    def test_peak_tie_uses_latest_confirmation(self):
        f=s.position_features(entry(),573,s.closed_prefix(DAY,573,bars(570,573)))
        self.assertEqual(f['peakConfirmedAt'],573)
        self.assertEqual(f['activeMinutesSincePeakConfirmation'],0)

    def test_current_return_not_realized_net(self):
        f=s.position_features(entry(),571,s.closed_prefix(DAY,571,bars()))
        self.assertAlmostEqual(f['currentReturnPct'],100*(100/100.05-1))
        self.assertNotIn('netReturn',f)

    def test_previous_day_must_be_past(self):
        with self.assertRaises(ValueError):s.market_snapshot(DAY,571,(),DAY,(),fake)

    def test_tri_state_not_coerced(self):
        def bad(*args):
            r=fake(*args);r['signals']['RECLAIM']['state']=0;return r
        with self.assertRaises(ValueError):s.market_snapshot(DAY,571,(),None,(),bad)

    def test_missing_signal_does_not_become_disappearance(self):
        rows=[{'now':571,'state':'RISE','signals':dict.fromkeys(s.FAMILIES,True)},
              {'now':572,'state':None,'signals':dict.fromkeys(s.FAMILIES,None)}]
        h=s.summarize_history(rows,572)
        self.assertIsNone(h['bullishStateDisappeared']['CONTINUATION'])
        self.assertEqual(h['3']['signals']['CONTINUATION']['unknown'],1)

    def test_observed_true_to_false_is_disappearance(self):
        rows=[{'now':571,'state':'RISE','signals':dict.fromkeys(s.FAMILIES,True)},
              {'now':572,'state':'DROP','signals':dict.fromkeys(s.FAMILIES,False)}]
        self.assertTrue(s.summarize_history(rows,572)['bullishStateDisappeared']['CONTINUATION'])

    def test_history_resets_at_lunch(self):
        rows=[{'now':690,'state':'RISE','signals':dict.fromkeys(s.FAMILIES,True)},
              {'now':751,'state':'DROP','signals':dict.fromkeys(s.FAMILIES,False)}]
        h=s.summarize_history(rows,751)
        self.assertEqual(h['10']['samples'],1)
        self.assertIsNone(h['bullishStateDisappeared']['BREAKOUT'])

    def test_sequential_order_required(self):
        with self.assertRaises(ValueError):s.PositionObserver(entry()).step(572,(),fake(None,None,None,None,None))

    def test_dwell_not_limited_to_last10_window(self):
        obs=s.PositionObserver(entry(),{'state':'RISE','dataQuality':'OK'})
        for t in range(571,591):
            f=obs.step(t,s.closed_prefix(DAY,t,bars()),fake(DAY,t,None,None,None))
        self.assertEqual(f['stateDwellObservedActiveMinutes'],20)
        self.assertEqual(f['entryToCurrentState'],['RISE','RISE'])
        self.assertEqual(f['history']['10']['samples'],10)

    def test_repeat_run_bytes(self):
        def run():
            obs=s.PositionObserver(entry())
            return b''.join(s.encoded(obs.step(t,s.closed_prefix(DAY,t,bars()),fake(DAY,t,None,None,None))) for t in range(571,581))
        self.assertEqual(run(),run())

    def test_all_safety_false_and_no_sell_policy(self):
        self.assertTrue(all(v is False for v in s.SAFETY.values()))
        self.assertFalse(hasattr(s.PositionObserver,'sell'))

    def test_allowlist_skips_opaque_invalid_json_values(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.gz';p.write_bytes(gzip.compress(b'{"keep":{"today":[]},"sealed":{"secret": NOT_JSON}}'))
            self.assertEqual(s.read_allowlisted_paths(p,{'keep'}),{'keep':{'today':[]}})

    def test_allowlist_rejects_duplicate_missing_and_trailing_comma(self):
        for b in (b'{"keep":{},"keep":{}}',b'{}',b'{"keep":{},}'):
            with self.subTest(b=b),tempfile.TemporaryDirectory() as d:
                p=Path(d)/'a.gz';p.write_bytes(gzip.compress(b))
                with self.assertRaises(ValueError):s.read_allowlisted_paths(p,{'keep'})

    def test_append_only_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json';s.write_new(p,{'x':1})
            with self.assertRaises(FileExistsError):s.write_new(p,{'x':2})


class Canonical(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from scripts.phase57_state_v3_9pattern_entry_v1 import classify_state_v3
            from scripts.phase57_entry_timing_signals import detect
        except ImportError:
            if os.getenv('ARK_REQUIRE_CANONICAL') == '1':raise
            raise unittest.SkipTest('Canonical source not mounted locally; mandatory in CI')

    def test_actual_canonical_producers_and_future_invariance(self):
        now=580;p=s.closed_prefix(DAY,now,bars());pv=s.closed_prefix('2025-05-30',1440,bars())
        a=s.market_snapshot(DAY,now,p,'2025-05-30',pv)
        b=s.market_snapshot(DAY,now,s.closed_prefix(DAY,now,bars()+bars(700,710)),'2025-05-30',pv)
        self.assertEqual(s.encoded(a),s.encoded(b))
        self.assertEqual(set(a['signals']),set(s.FAMILIES))
        self.assertNotIn('selectorMovePct',a['signalContext'])

    def test_actual_sparse_prefix_keeps_unknown_signal(self):
        a=s.market_snapshot(DAY,580,s.closed_prefix(DAY,580,bars(575,579)),None,())
        self.assertIsNone(a['signals']['CONTINUATION']['state'])

    def test_actual_producer_direct_parity(self):
        import numpy as np
        from scripts.phase57_state_v3_9pattern_entry_v1 import classify_state_v3
        from scripts.phase57_entry_timing_signals import detect
        p=s.closed_prefix(DAY,580,bars());pv=s.closed_prefix('2025-05-30',1440,bars())
        a=s.market_snapshot(DAY,580,p,'2025-05-30',pv)
        rows=[b.row() for b in p];prev=[b.row() for b in pv]
        self.assertEqual(a['state'],classify_state_v3(DAY,580,rows,prev,'2025-05-30'))
        self.assertEqual(a['signals'],detect(DAY,580,None,np.array(rows),np.array(prev),'2025-05-30')['signals'])


if __name__ == '__main__':unittest.main()
