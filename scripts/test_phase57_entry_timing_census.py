import copy
import unittest
import numpy as np
from scripts import phase57_entry_timing_signals as s
from scripts import phase57_entry_timing_census as c

DAY='2025-06-02'
PREV='2025-05-30'


def bar(t, o=100, h=101, low=99, close=100, vol=10, value=1000):
    return [t,o,h,low,close,vol,value]


def series(start=540,end=600):
    return np.array([bar(t) for t in range(start,end)],float)


def detect(a,t=600,prev=None):
    return s.detect(DAY,t,100,a,np.empty((0,7)) if prev is None else prev,PREV if prev is not None else None)


def trend():
    a=series()
    for i in range(len(a)):
        price=100+i*.05
        a[i]=bar(int(a[i,0]),price,price+.05,price-.05,price+.02,10,price*10)
    return a


class CausalSignals(unittest.TestCase):
    def test_precommit_and_pins(self):
        p=s.verify();self.assertEqual(len(p['opportunityIds']),2155)

    def test_future_row_rejected(self):
        with self.assertRaisesRegex(AssertionError,'FUTURE'):
            detect(series(540,601))

    def test_future_suffix_invariance(self):
        a=series(540,630);b=a.copy();b[b[:,0]>=600,1:]*=99
        self.assertEqual(detect(s.legacy.closed(a,600)),detect(s.legacy.closed(b,600)))

    def test_unclosed_bar_unavailable_until_next_minute(self):
        a=trend();before=detect(a[a[:,0]<599],599);after=detect(a,600)
        self.assertEqual(before['computedThroughBarStart'],598)
        self.assertEqual(after['computedThroughBarStart'],599)

    def test_continuation_without_reclaim(self):
        z=detect(trend());self.assertTrue(z['signals']['CONTINUATION']['state'])
        self.assertFalse(z['signals']['RECLAIM']['levels']['VWAP'])

    def test_missing_latest_no_forward_fill(self):
        z=detect(trend()[:-1]);self.assertFalse(z['newClosedBarObserved'])
        self.assertIsNone(z['signals']['CONTINUATION']['state'])
        self.assertIsNone(z['activity']['1/volume'])

    def test_volume_missing_is_not_zero(self):
        z=detect(series()[np.arange(60)!=58]);self.assertIsNone(z['activity']['3/volume'])
        self.assertEqual(z['activity']['3/currentRows'],2)

    def test_zero_relative_denominator(self):
        pv=series();pv[:,5:]=0
        z=detect(series(),prev=pv);self.assertIsNone(z['activity']['3/volumeRelativePreviousDay'])

    def test_same_time_relative_volume(self):
        a=series();a[-3:,5:]*=2
        z=detect(a,prev=series());self.assertEqual(z['activity']['3/volumeRelativePreviousDay'],2)
        self.assertEqual(z['activity']['3/volumeAcceleration'],2)

    def test_lunch_does_not_bridge(self):
        z=detect(series(540,690),751)
        self.assertIsNone(z['signals']['CONTINUATION']['state'])
        self.assertIsNone(z['activity']['1/volume'])

    def test_endpoint_auction_not_a_decision_bar(self):
        a=np.vstack([series(680,690),bar(690,100,1000,1,100)])
        z=detect(a,751);self.assertEqual(z['computedThroughBarStart'],689)

    def test_opening_range_requires_completion(self):
        self.assertFalse(detect(series(540,554),554)['context']['openingRangeComplete'])
        self.assertTrue(detect(series(540,555),555)['context']['openingRangeComplete'])

    def test_opening_range_missing_is_unknown(self):
        a=series();a=a[a[:,0]!=545]
        self.assertIsNone(detect(a)['context']['ORH'])

    def test_no_previous_day_is_explicit(self):
        z=detect(series());self.assertFalse(z['context']['previousDayAvailable'])
        self.assertIsNone(z['context']['PDHObserved'])

    def test_invalid_previous_date_rejected(self):
        with self.assertRaisesRegex(AssertionError,'PREVIOUS_DAY'):
            s.detect(DAY,600,100,series(),series(),DAY)

    def test_three_valued_or(self):
        self.assertIsNone(s.tri_or([False,None]))
        self.assertTrue(s.tri_or([True,None]))
        self.assertFalse(s.tri_or([False,False]))

    def test_zero_range_wick_unknown(self):
        a=series();a[-1,1:5]=100
        self.assertIsNone(detect(a)['signals']['LOWER_WICK']['state'])

    def test_wick_confirmation_not_backdated(self):
        a=series();a[-5]=bar(595,101,101,100,100.8)
        a[-4]=bar(596,100.8,100.8,100,100.5)
        a[-3]=bar(597,100.5,100.6,99.8,100)
        a[-2]=bar(598,100,100.2,99,100.1)
        a[-1]=bar(599,100.1,100.5,100,100.4)
        z=detect(a);self.assertTrue(z['signals']['LOWER_WICK']['event'])
        self.assertEqual(z['barClosedAtJst'],'10:00')
        self.assertTrue(detect(a[:-1],599)['signals']['LOWER_WICK']['state'])

    def test_higher_low_confirms_one_bar_later(self):
        a=series();a[-20:,3]=99.5
        a[-10,3]=98;a[-2,3]=99;a[-1]=bar(599,100,102,99.6,101.5)
        z=detect(a);self.assertTrue(z['signals']['HIGHER_LOW']['event'])
        self.assertEqual(z['signals']['HIGHER_LOW']['pivot']['confirmedAt'],600)
        self.assertNotEqual(z['signals']['HIGHER_LOW']['pivot']['lowBarStart'],600)

    def test_breakout_uses_prior_local_high(self):
        a=series();a[-1]=bar(599,100,105,100,103)
        z=detect(a);self.assertTrue(z['signals']['BREAKOUT']['levels']['LOCAL10H'])
        self.assertEqual(z['context']['localResistance'],101)

    def test_compression_requires_expansion(self):
        a=series();z=detect(a);self.assertFalse(z['signals']['COMPRESSION_EXPANSION']['event'])

    def test_inputs_not_mutated(self):
        a=series();before=a.copy();detect(a);np.testing.assert_array_equal(a,before)


class ReplayAndEvaluation(unittest.TestCase):
    def replay(self,arm='E',day=DAY,start=600,signal=None,missing=()):
        grid=s.comparison_grid(day,start)
        rows={t:{'signals':{f:{'trigger':signal is not None and t==signal and f=='CONTINUATION'} for f in s.FAMILIES}} for t in grid}
        return s.replay('x',day,start,rows,{t:True for t in grid},{t:None if t in missing else 100 for t in grid},
                        {'A':['IMMEDIATE'],'E':list(s.FAMILIES),'F':[]})[arm]

    def test_no_signal_fallback_not_reject(self):
        t=self.replay();self.assertEqual(t['entryMinute'],610);self.assertEqual(t['intentReason'],'FALLBACK')
        self.assertFalse(t['modelRejection'])

    def test_continuation_at_selector_does_not_wait(self):
        self.assertEqual(self.replay(signal=600)['entryMinute'],600)

    def test_signal_latches_through_failure(self):
        t=self.replay(signal=601,missing=(601,602));self.assertEqual(t['entryMinute'],603)
        self.assertEqual(t['intentMinute'],601);self.assertEqual(t['retryCount'],2)

    def test_same_retry_immediate(self):
        t=self.replay('A',missing=(600,601));self.assertEqual(t['entryMinute'],602)

    def test_missing_execution_has_no_fictional_fill(self):
        t=self.replay(missing=range(600,631));self.assertIsNone(t['entryMinute'])
        self.assertEqual(t['buyAttemptCount'],21);self.assertEqual(t['unfilledReason'],'RETRY_EXHAUSTED')

    def test_session_end_clipped_fallback(self):
        self.assertEqual(self.replay(start=920)['entryMinute'],924)

    def test_zero_grid_is_kept(self):
        t=self.replay(day='2024-10-01',start=900);self.assertEqual(t['unfilledReason'],'SESSION_BOUNDARY')

    def test_lunch_active_deadline(self):
        self.assertEqual(self.replay(start=690)['entryMinute'],760)

    def test_unknown_signals_also_fallback(self):
        grid=s.comparison_grid(DAY,600)
        rows={t:{'signals':{f:{'trigger':None} for f in s.FAMILIES}} for t in grid}
        z=s.replay('x',DAY,600,rows,dict.fromkeys(grid,True),dict.fromkeys(grid,100),{'E':list(s.FAMILIES)})
        self.assertEqual(z['E']['entryMinute'],610)

    def test_future_fill_does_not_change_intent(self):
        a=self.replay(signal=603);b=self.replay(signal=603,missing=(603,604))
        self.assertEqual(a['intentMinute'],b['intentMinute'])

    def test_no_same_bar_oracle_low_high(self):
        a=np.array([bar(600,100,200,1,100),bar(601,100,101,99,100)],float)
        x=c.ordered_oracle(a,600);self.assertEqual(x['high'],101);self.assertEqual(x['low'],1)

    def test_oracle_first_equal_tie_is_deterministic(self):
        x=c.ordered_oracle(series(600,604),600);self.assertEqual(x['lowMinute'],600);self.assertEqual(x['highMinute'],601)

    def test_retention_edges(self):
        a=series(600,604);oracle=c.ordered_oracle(a,600)
        self.assertEqual(c.retention(oracle,None,None,True,a)['status'],'NO_FILL')
        self.assertEqual(c.retention(oracle,601,100,True,a)['status'],'ORACLE_HIGH_AT_OR_BEFORE_ENTRY')
        self.assertEqual(c.retention(oracle,599,100,True,a)['status'],'ENTRY_BEFORE_ORACLE_LOW')
        self.assertEqual(c.retention(oracle,600,100,False,a)['status'],'FULL_SESSION_OBSERVATION_INSUFFICIENT')
        oracle['rangePct']=0;self.assertEqual(c.retention(oracle,600,100,True,a)['status'],'NONPOSITIVE_DENOMINATOR')

    def test_retention_not_clipped(self):
        a=series(600,604);oracle=c.ordered_oracle(a,600)
        self.assertLess(c.retention(oracle,599,200,True,a)['valuePct'],0)
        self.assertGreater(c.retention(oracle,599,50,True,a)['valuePct'],100)

    def test_strict_horizon_differs_from_legacy_slots(self):
        a=series(600,630)[::2];self.assertEqual(c.strict_coverage(DAY,600,a,30)['status'],'PARTIAL_1M')

    def test_direct_path_same_bar_order_unknown(self):
        a=np.array([bar(600,100,104,99,102)],float)
        self.assertEqual(c.direct_path(a,600,100,True),'SAME_BAR_ORDER_AMBIGUOUS')

    def test_direct_path_missing_not_failure(self):
        self.assertEqual(c.direct_path(series(),600,100,False),'UNKNOWN')

    def test_selection_1130_excludes_already_closed_auction(self):
        a=np.array([bar(690),bar(750),bar(751)],float)
        np.testing.assert_array_equal(c.future_rows(DAY,a,690)[:,0],[750,751])

    def test_1500_remains_regular_after_session_extension(self):
        a=np.array([bar(900),bar(901),bar(930)],float)
        np.testing.assert_array_equal(c.future_rows(DAY,a,900)[:,0],[900,901,930])
        self.assertEqual(len(c.future_rows('2024-10-01',a[:1],900)),0)


if __name__=='__main__':
    unittest.main()
