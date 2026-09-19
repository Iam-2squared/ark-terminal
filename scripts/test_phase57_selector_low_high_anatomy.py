import copy,datetime as dt,json,pathlib,tempfile,unittest
from unittest.mock import patch
from scripts import phase57_selector_low_high_anatomy as m
from scripts.test_phase57_selector_path_anatomy import path

def fixture(time='14:30',date='2024-11-01'):
    p=path(date=date,time=time,n=100)
    for b in p['future']:b.update(o=0,h=.5,l=-.5,c=0)
    member={k:p[k] for k in ['selectorEventId','sessionDate','symbol','decisionTimestamp','decisionPrice']}
    member.update(originalRank=1,savedV1Score=1)
    return p,member

class LowHighAnatomy(unittest.TestCase):
    def test_protocol_pins_safety_and_sealed(self):m.protocol()
    def test_frozen_hash_fails_closed(self):
        read=m.read
        def changed(f):
            r=read(f)
            if str(f).endswith('protocol-lock.json'):r['protocolSHA256']='bad'
            return r
        with patch.object(m,'read',side_effect=changed),self.assertRaises(AssertionError):m.protocol()
    def test_selection_price_not_entry_open(self):
        p,s=fixture();p['future'][0].update(o=2,h=4,l=1,c=3)
        r=m.evaluate(p,s);self.assertEqual(r['selectionToHighPct'],4)
        self.assertNotAlmostEqual(r['selectionToHighPct'],100*(104/102-1))
    def test_100_95_105_oracle_ratio_and_order(self):
        p,s=fixture();p['future'][0]['l']=-5;p['future'][3]['h']=5
        r=m.evaluate(p,s);self.assertEqual(r['selectionToLowPct'],-5);self.assertEqual(r['selectionToHighPct'],5)
        self.assertAlmostEqual(r['lowToHighPct'],10.526315789473685)
        self.assertEqual(r['order'],'LOW_THEN_HIGH');self.assertEqual(r['lowPrice'],95);self.assertEqual(r['highPrice'],105)
    def test_high_before_low_still_oracle_range(self):
        p,s=fixture();p['future'][0]['h']=5;p['future'][3]['l']=-5;r=m.evaluate(p,s)
        self.assertEqual(r['order'],'HIGH_THEN_LOW');self.assertIsNone(r['lowToHighElapsed']);self.assertAlmostEqual(r['lowToHighPct'],10.526315789473685)
    def test_same_bar_unknown(self):
        p,s=fixture();p['future'][0].update(l=-5,h=5);r=m.evaluate(p,s)
        self.assertEqual(r['order'],'SAME_BAR_ORDER_UNKNOWN');self.assertIsNone(r['lowToHighElapsed'])
        self.assertEqual(r['patterns']['down3_up5']['status'],'SAME_BAR_ORDER_UNKNOWN')
    def test_tied_extrema_first_and_all_intervals(self):
        p,s=fixture();p['future'][0]['l']=-2;p['future'][2]['l']=-2;p['future'][1]['h']=3;p['future'][4]['h']=3
        r=m.evaluate(p,s);self.assertEqual((r['lowTieBars'],r['highTieBars']),(2,2));self.assertEqual(r['order'],'LOW_THEN_HIGH')
        self.assertEqual(r['highInterval']['startJst'],p['future'][1]['start'])
    def test_no_zero_clamping_when_all_above(self):
        p,s=fixture()
        for b in p['future']:b.update(o=2,h=4,l=1,c=3)
        self.assertEqual(m.evaluate(p,s)['selectionToLowPct'],1)
    def test_no_zero_clamping_when_all_below(self):
        p,s=fixture()
        for b in p['future']:b.update(o=-2,h=-1,l=-4,c=-3)
        self.assertEqual(m.evaluate(p,s)['selectionToHighPct'],-1)
    def test_incomplete_keeps_null_metrics_and_bounds(self):
        p,s=fixture();p['future'][2]['missing']=True;r=m.evaluate(p,s)
        self.assertEqual(r['order'],'NO_VALID_PATH');self.assertTrue(all(r[f] is None for f in m.FIELDS))
        self.assertIsNone(r['winner']['3']);self.assertIsNotNone(r['partialObservedBounds'])
        self.assertEqual(r['patterns']['down1_up3']['status'],'NOT_EVALUABLE')
    def test_absent_slot_and_missing_final_fail_closed(self):
        for index in [0,2,-1]:
            p,s=fixture();del p['future'][index];r=m.evaluate(p,s)
            self.assertEqual(r['reason'],'INCOMPLETE_PATH');self.assertEqual(r['missingBars'][0]['reason'],'ABSENT_SLOT')
    def test_invalid_ohlc(self):
        p,s=fixture();p['future'][1]['l']=4;self.assertEqual(m.evaluate(p,s)['status'],'NO_VALID_PATH')
    def test_sparse_5m_accepted_and_counted(self):
        p,s=fixture();p['future'][1]['observedMinutes']=1;r=m.evaluate(p,s)
        self.assertEqual(r['status'],'VALID_COMPLETE_PATH');self.assertEqual(r['sparseObservedBars'],1)
    def test_lunch_excluded_from_trading_clock(self):
        p,s=fixture(time='11:30');r=m.evaluate(p,s)
        self.assertEqual(r['lowInterval']['tradingMinutes'],[0,5]);self.assertEqual(r['lowInterval']['wallMinutes'],[60,65])
    def test_extrema_gap_across_lunch_bounds(self):
        p,s=fixture(time='11:25');p['future'][0]['l']=-3;p['future'][1]['h']=5;r=m.evaluate(p,s)
        self.assertEqual(r['lowToHighElapsed']['tradingMinutes'],[0,10]);self.assertEqual(r['lowToHighElapsed']['wallMinutes'],[60,70])
    def test_market_close_change(self):
        old,so=fixture(date='2024-11-01');new,sn=fixture(date='2024-11-06')
        self.assertEqual(m.evaluate(old,so)['expectedBars'],6);self.assertEqual(m.evaluate(new,sn)['expectedBars'],12)
    def test_future_session_and_past_bar_rejected(self):
        p,s=fixture();p['future'][0]['start']='2024-11-01T14:25:00+09:00'
        with self.assertRaises(AssertionError):m.evaluate(p,s)
    def test_threshold_equal_and_nonwinner(self):
        p,s=fixture();p['future'][3]['h']=3;r=m.evaluate(p,s)
        self.assertTrue(r['winner']['3']);self.assertFalse(r['winner']['5']);self.assertEqual(r['firstHits']['3']['tradingMinutes'],[15,20])
    def test_down_then_up_requires_time_order(self):
        p,s=fixture();p['future'][0]['h']=5;p['future'][4]['l']=-3;r=m.evaluate(p,s)
        self.assertEqual(r['patterns']['down3_up5']['status'],'NOT_OBSERVED')
        p['future'][5]['h']=5;r=m.evaluate(p,s);self.assertEqual(r['patterns']['down3_up5']['status'],'CONFIRMED')
    def test_threshold_order_not_global_extrema_order(self):
        p,s=fixture();p['future'][0]['h']=8;p['future'][1]['l']=-5;p['future'][2]['h']=3;r=m.evaluate(p,s)
        self.assertEqual(r['order'],'HIGH_THEN_LOW');self.assertEqual(r['patterns']['down3_up3']['status'],'CONFIRMED')
    def test_giveback_requires_later_bar(self):
        p,s=fixture()
        for b in p['future']:b.update(o=1,h=2,l=.5,c=1)
        p['future'][0].update(h=5,l=-.5);r=m.evaluate(p,s)
        self.assertEqual(r['patterns']['up5_giveback0']['status'],'SAME_BAR_ORDER_UNKNOWN')
        p['future'][2]['l']=0;r=m.evaluate(p,s);self.assertEqual(r['patterns']['up5_giveback0']['status'],'CONFIRMED')
    def test_membership_rank_no_future_filter(self):
        mm=m.members();self.assertEqual(len(mm['FROZEN_SELECTOR']),3800)
        self.assertEqual([r['originalRank'] for r in mm['FROZEN_SELECTOR'][:5]],[1,2,3,4,5])
    def test_future_mutation_does_not_change_identity_or_rank(self):
        p,s=fixture();before=copy.deepcopy(s);p['future'][0]['h']=20;m.evaluate(p,s);self.assertEqual(s,before)
    def test_no_path_not_nonwinner(self):
        p,s=fixture();p['future']=[];r=m.evaluate(p,s);c=m.winner_comparison([r],3)
        self.assertEqual(c['unknownN'],1);self.assertEqual(c['nonwinner']['counts']['validN'],0)
    def test_full5_pair_gate(self):
        p,s=fixture();r=m.evaluate(p,s);left=[r]*5;right=[r]*4
        self.assertEqual(m.pair_comparison(left,right,True)['status'],'NOT_EVALUABLE')
        self.assertEqual(m.pair_comparison(left,right,False)['timestamps'],1)
    def test_quantile_and_cdf_interval(self):
        p,s=fixture();p['future'][1]['l']=-3;r=m.evaluate(p,s);t=m.timing([r])['lowInterval']['tradingMinutes']['cdf']
        self.assertEqual(t['5'],{'definiteBy':0,'possibleBy':1});self.assertEqual(t['10']['definiteBy'],1)
    def test_pattern_denominators_and_unknown_bounds(self):
        p,s=fixture();p['future'][0]['l']=-3;p['future'][2]['h']=5;good=m.evaluate(p,s)
        p['future'][1]['missing']=True;bad=m.evaluate(p,s);z=m.pattern_summary([good,bad],['down3_up5'])['down3_up5']
        self.assertEqual(z['allOriginalLogicalRateBounds'],[.5,1]);self.assertEqual(z['confirmedRateAmongValid'],1)
    def test_deterministic_complete_artifact_regeneration(self):
        p,s=fixture();p['future'][0]['l']=-3;p['future'][2]['h']=5;r=m.evaluate(p,s)
        with tempfile.TemporaryDirectory() as root:
            first=pathlib.Path(root)/'first';second=pathlib.Path(root)/'second'
            m.emit([r],[r],first,'synthetic',{});m.emit([r],[r],second,'synthetic',{})
            self.assertEqual({f.name:m.sha(f) for f in first.iterdir()},{f.name:m.sha(f) for f in second.iterdir()})

if __name__=='__main__':unittest.main()
