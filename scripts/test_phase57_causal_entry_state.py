import copy
import inspect
import unittest
import numpy as np
from scripts import phase57_causal_entry_state as st
from scripts import phase57_causal_entry_anatomy as an
from scripts.test_phase57_entry_timing_census import series,trend,bar,DAY,PREV


def daily_fixture():
    dates=['2025-05-23','2025-05-26','2025-05-27','2025-05-28','2025-05-29','2025-05-30']
    rows=[dict(Date=d,O=100+i,H=102+i,L=99+i,C=101+i,Vo=1000,Va=100000,AdjFactor=1) for i,d in enumerate(dates)]
    return dates,rows


def context():return st.daily_context(DAY,*daily_fixture())


def state(a,t=600,ctx=None):return st.state(DAY,t,a,series(),PREV,ctx or context(),{})


class DailyTests(unittest.TestCase):
    def test_future_rejected(self):
        dates,rows=daily_fixture();dates[-1]=DAY;rows[-1]['Date']=DAY
        with self.assertRaisesRegex(AssertionError,'FUTURE_DAILY'):st.daily_context(DAY,dates,rows)
    def test_exact_date_required(self):
        dates,rows=daily_fixture();rows[-1]['Date']=dates[-2]
        with self.assertRaisesRegex(AssertionError,'DAILY_DATE'):st.daily_context(DAY,dates,rows)
    def test_five_complete(self):self.assertTrue(context()['complete5'])
    def test_missing_not_imputed(self):
        dates,rows=daily_fixture();rows[-3]=None;z=st.daily_context(DAY,dates,rows)
        self.assertFalse(z['complete5']);self.assertIsNone(z['features']['returnOC5']);self.assertIsNone(z['features']['D3/Vo'])
    def test_missing_optional_six(self):
        dates,rows=daily_fixture();rows[0]=None;z=st.daily_context(DAY,dates,rows)
        self.assertTrue(z['complete5']);self.assertIsNone(z['features']['returnCC5']);self.assertIsNotNone(z['features']['returnOC5'])
    def test_return_formulas(self):
        z=context()['features'];self.assertAlmostEqual(z['returnOC5'],100*(106/101-1));self.assertAlmostEqual(z['returnCC5'],100*(106/101-1))
    def test_zero_range_location(self):
        dates,rows=daily_fixture();rows[-1].update(O=100,H=100,L=100,C=100);z=st.daily_context(DAY,dates,rows)
        self.assertIsNone(z['features']['D1/location'])
    def test_missing_volume(self):
        dates,rows=daily_fixture();rows[-1]['Vo']=None;z=st.daily_context(DAY,dates,rows)
        self.assertIsNone(z['features']['volumeRatio']);self.assertIsNone(z['features']['D1/Vo'])
    def test_ohlc_invalid(self):
        dates,rows=daily_fixture();rows[-1]['L']=1000;self.assertFalse(st.daily_context(DAY,dates,rows)['complete5'])


class StateTests(unittest.TestCase):
    def test_future_rejected(self):
        with self.assertRaisesRegex(AssertionError,'FUTURE_BAR'):state(series(540,601))
    def test_suffix_invariance(self):
        a=series(540,620);b=a.copy();b[b[:,0]>=600,1:]*=99
        self.assertEqual(state(a[a[:,0]<600]),state(b[b[:,0]<600]))
    def test_no_future_feature_interface(self):
        self.assertEqual(list(inspect.signature(st.state).parameters),['day','t','prefix','previous','previous_day','daily','activity'])
        self.assertFalse(any(k.lower().find('oracle')>=0 for k in state(series())['features']))
    def test_lunch_not_bridged(self):self.assertIsNone(state(series(540,690),751)['features']['ret5'])
    def test_missing_not_filled(self):
        z=state(series()[:-1]);self.assertFalse(z['newClosedBarObserved']);self.assertIsNone(z['features']['ret5'])
    def test_wrong_previous_session(self):
        with self.assertRaisesRegex(AssertionError,'PREVIOUS_DATE'):st.state(DAY,600,series(),series(),'2025-05-29',context(),{})
    def test_transition(self):
        up=trend();down=up.copy()
        for i in range(10):down[-10+i]=bar(590+i,104-i*.4,104.1-i*.4,103.5-i*.4,103.6-i*.4)
        self.assertNotEqual(state(up)['scores'],state(down)['scores'])
    def test_tie_is_mixed(self):self.assertEqual(st.dominant({'TREND':.75,'PULLBACK':.75}),'MIXED')
    def test_probability_not_claimed(self):
        z=state(trend());self.assertTrue(all(x is None or 0<=x<=1 for x in z['scores'].values()))
    def test_no_signal_fallback(self):
        grid=an.s.comparison_grid(DAY,600);obs={t:{'signals':{'EARLY':{'trigger':False},'APPROPRIATE':{'trigger':False}}} for t in grid}
        z=an.s.replay('x',DAY,600,obs,{t:True for t in grid},{t:100 for t in grid},an.ARMS)
        self.assertEqual(z['C']['entryMinute'],610);self.assertEqual(z['C']['intentReason'],'FALLBACK');self.assertFalse(z['C']['modelRejection'])
    def test_no_fake_fill(self):
        grid=an.s.comparison_grid(DAY,600);obs={t:{'signals':{}} for t in grid}
        z=an.s.replay('x',DAY,600,obs,{}, {},{'F':[]})['F'];self.assertIsNone(z['entryId']);self.assertGreater(z['buyAttemptCount'],0)


class PathTests(unittest.TestCase):
    def test_missing_reason(self):self.assertEqual(an.classify(DAY,600,100,np.empty((0,7)),False)['reason'],'MISSING_PATH_DATA')
    def test_insufficient_reason(self):self.assertEqual(an.classify(DAY,600,100,series(600,610),True)['reason'],'INSUFFICIENT_OBSERVATION')
    def test_no_dominant(self):
        a=np.array([bar(t,100,100,100,100) for t in range(600,650)],float)
        self.assertEqual(an.classify(DAY,600,100,a,True)['reason'],'NO_DOMINANT_PATH')
    def test_direct(self):
        a=np.array([bar(t,100+(t-600)*.05,100.06+(t-600)*.05,99.99+(t-600)*.05,100.04+(t-600)*.05) for t in range(600,650)],float)
        self.assertEqual(an.classify(DAY,600,100,a,True)['path'],an.PATHS[0])
    def test_weakness(self):
        a=np.array([bar(t,100-(t-600)*.05,100.01-(t-600)*.05,99.94-(t-600)*.05,99.96-(t-600)*.05) for t in range(600,650)],float)
        self.assertEqual(an.classify(DAY,600,100,a,True)['path'],an.PATHS[4])
    def test_recovery(self):
        prices=list(np.linspace(100,98,20))+list(np.linspace(98,102,30))
        a=np.array([bar(600+i,p,p+.01,p-.01,p) for i,p in enumerate(prices)],float)
        self.assertTrue(an.classify(DAY,600,100,a,True)['predicate'][an.PATHS[1]])
    def test_samebar_not_direct(self):
        a=series(600,650);a[0]=bar(600,100,102,99,101)
        z=an.classify(DAY,600,100,a,True);self.assertTrue(z['sameBarOrderUnknown']);self.assertFalse(z['predicate'][an.PATHS[0]])
    def test_true_mixed_reason(self):
        prices=list(np.linspace(100,102,15))+list(np.linspace(102,98,15))+list(np.linspace(98,110,30))
        a=np.array([bar(600+i,p,p+.01,p-.01,p) for i,p in enumerate(prices)],float)
        z=an.classify(DAY,600,100,a,True)
        self.assertEqual(z['reason'],'TRUE_MIXED_PATH')
    def test_compression_breakout_predicate(self):
        a=np.array([bar(600+i,100,100.1,99.9,100) for i in range(10)]+[bar(610,100,101,100,101)]+[bar(611+i,101,101.1,100.9,101) for i in range(30)],float)
        self.assertTrue(an.classify(DAY,600,100,a,True)['predicate'][an.PATHS[2]])
    def test_chop_predicate(self):
        prices=[]
        for _ in range(5):prices+=list(np.linspace(100,101,6))+list(np.linspace(101,100,6))
        a=np.array([bar(600+i,p,p+.01,p-.01,p) for i,p in enumerate(prices)],float)
        self.assertTrue(an.classify(DAY,600,100,a,True)['predicate'][an.PATHS[3]])
    def test_no_lunch_swing(self):
        a=np.array([bar(689,100,100,100,100),bar(750,105,105,105,105),bar(751,100,100,100,100)],float)
        self.assertEqual(an.reversal_count(a),0)
    def test_low_edges(self):
        oracle={'lowMinute':610,'low':99}
        for t,expected in [(None,'NO_FILL'),(600,'ENTRY_BEFORE_LOW'),(610,'SAME_BAR_ORDER_UNKNOWN'),(611,'AFTER_LOW')]:
            self.assertEqual(an.low_distance(DAY,an.PATHS[1],oracle,t,100,True)['status'],expected)
    def test_direct_low_not_applicable(self):self.assertEqual(an.low_distance(DAY,an.PATHS[0],{'lowMinute':600,'low':99},610,100,True)['status'],'DIRECT_NOT_APPLICABLE')
    def test_high_at_entry_invalid(self):
        z=an.c.retention({'status':'OBSERVED_ORDERED_ORACLE','rangePct':3,'lowMinute':600,'highMinute':610,'high':103},610,101,True,series(600,620))
        self.assertEqual(z['status'],'ORACLE_HIGH_AT_OR_BEFORE_ENTRY')
    def test_protocol(self):self.assertEqual(len(an.verify()['opportunityIds']),2155)


if __name__=='__main__':unittest.main()
