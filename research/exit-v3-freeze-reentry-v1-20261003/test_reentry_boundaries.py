"""Synthetic chronology/execution edges. No Frozen FIRST/EXIT baseline replay."""
import unittest
from fresh_cross import FreshCross
from reentry_fill import buy_fill
from reused_clock import active_minutes

def signal(m,score,threshold=.6,**kw):
    d={'minute':m,'score':score,'threshold':threshold,'timestamp':f'2026-01-01T{m//60:02}:{m%60:02}:00+09:00','feature_max_timestamp':f'2026-01-01T{m//60:02}:{m%60:02}:00+09:00','row_id':str(m)}
    return d|kw
def raw(m,price=100,volume=1):return [m,price,price,price,price,volume,price*volume]

class Boundaries(unittest.TestCase):
    def test_at_or_above_after_exit_does_not_reenter(self):
        q=FreshCross(600)
        for m,p in [(601,.6),(602,.9),(606,.7)]:self.assertIsNone(q.observe(signal(m,p))[0])
        self.assertEqual(q.state,'WAIT_FOR_RESET')
    def test_reset_strictly_below_then_equality_cross(self):
        q=FreshCross(600);self.assertIsNone(q.observe(signal(601,.599))[0]);self.assertEqual(q.state,'ARMED_FOR_FRESH_CROSS')
        self.assertIsNotNone(q.observe(signal(602,.6))[0])
    def test_consecutive_below_preserves_freshness(self):
        q=FreshCross(600)
        for m,p in [(601,.2),(602,.1),(604,.59)]:self.assertIsNone(q.observe(signal(m,p))[0])
        self.assertEqual(q.observe(signal(605,.61))[0]['minute'],605)
    def test_same_sell_raw_minute_rejected(self):
        with self.assertRaises(RuntimeError):FreshCross(600).observe(signal(600,.1))
    def test_before_sell_rejected(self):
        with self.assertRaises(RuntimeError):FreshCross(600).observe(signal(599,.1))
    def test_buy_intent_locked(self):
        q=FreshCross(600);q.observe(signal(601,.1));q.observe(signal(602,.9))
        with self.assertRaises(RuntimeError):q.observe(signal(603,.1))
    def test_duplicate_score_minute_rejected(self):
        q=FreshCross(600);q.observe(signal(601,.1))
        with self.assertRaises(RuntimeError):q.observe(signal(601,.9))
    def test_future_feature_timestamp_rejected(self):
        with self.assertRaises(RuntimeError):FreshCross(600).observe(signal(601,.1,feature_max_timestamp='2026-01-01T10:02:00+09:00'))
    def test_lunch_no_cooldown_no_new_reset(self):
        q=FreshCross(687);q.observe(signal(690,.1));self.assertIsNotNone(q.observe(signal(751,.7))[0])
        self.assertEqual(active_minutes('2026-01-01',690,751),1)
    def test_new_episode_requires_new_reset(self):
        q=FreshCross(603);self.assertIsNone(q.observe(signal(604,.8))[0]);self.assertEqual(q.state,'WAIT_FOR_RESET')
    def test_first_next_raw_open_includes_intent_minute(self):
        r=buy_fill('2026-01-01',{'minute':603},[raw(602,90),raw(603,100),raw(604,110)])
        self.assertEqual((r['buy_minute'],r['buy_price']),(603,100*1.0005))
    def test_mixed_open_lunch_and_close_not_regular_fills(self):
        r=buy_fill('2026-01-01',{'minute':690},[raw(690),raw(750),raw(751,101),raw(930)])
        self.assertEqual(r['buy_minute'],751)
    def test_no_next_regular_open_explicit_no_fill(self):
        r=buy_fill('2026-01-01',{'minute':925},[raw(925),raw(930)])
        self.assertEqual(r['buy_status'],'NO_REENTRY_NO_NEXT_REGULAR_OPEN');self.assertIsNone(r['buy_price'])
    def test_old_calendar_excludes_1500_regular_open(self):
        r=buy_fill('2024-11-01',{'minute':900},[raw(900),raw(930)])
        self.assertEqual(r['buy_status'],'NO_REENTRY_NO_NEXT_REGULAR_OPEN')
    def test_invalid_raw_not_used(self):
        r=buy_fill('2026-01-01',{'minute':601},[raw(601,0),raw(602,100)])
        self.assertEqual(r['buy_minute'],602)
    def test_first_observed_pm_is_allowed_by_frozen_buy(self):
        # Frozen buy only excludes literal 12:30; Frozen sell has extra mixed-source exclusion.
        self.assertEqual(buy_fill('2026-01-01',{'minute':753},[raw(758)])['buy_minute'],758)

if __name__=='__main__':unittest.main()
