import copy,math,unittest
from scripts import phase57_selector_min_price75 as m
from scripts.phase57_selector_min_price75_downstream import anchors

def row(symbol,price=100,score=10):return {'symbol':symbol,'decisionPrice':price,'savedV1Score':score,'referenceAgeMin':0,'decisionPriceValid':1,'sessionDate':'2024-09-17','decisionTimeJst':'09:30','decisionTimestamp':'2024-09-17T09:30:00+09:00','selectorEventId':symbol}
class PriceGateTests(unittest.TestCase):
    def test_74(self):self.assertEqual(m.gate.price_status(74),'INELIGIBLE_MIN_PRICE')
    def test_75(self):self.assertEqual(m.gate.price_status(75),'INELIGIBLE_MIN_PRICE')
    def test_above75(self):self.assertEqual(m.gate.price_status(math.nextafter(75,math.inf)),'ELIGIBLE_MIN_PRICE')
    def test_missing(self):self.assertEqual(m.gate.price_status(None),'BLOCKED_INVALID_DECISION_PRICE')
    def test_invalid(self):
        for p in ['100','bad',True,float('nan'),float('inf'),float('-inf')]:self.assertEqual(m.gate.price_status(p),'BLOCKED_INVALID_DECISION_PRICE')
    def test_nonpositive(self):
        for p in [0,-1]:self.assertEqual(m.gate.price_status(p),'BLOCKED_INVALID_DECISION_PRICE')
    def test_future_price_ignored(self):
        r={**row('a',75),'futureClose':200,'futureHigh':500,'entryPrice':100};self.assertEqual(m.gate.select_top5([r]),[])
    def test_labels_dont_change_ranking(self):
        rs=[row(str(i),100,i) for i in range(8)];changed=[{**r,'futureHigh':-999,'futureMAE':999,'terminalOutcome':'BAD'} for r in rs]
        self.assertEqual([r['symbol'] for r in m.gate.select_top5(rs)],[r['symbol'] for r in m.gate.select_top5(changed)])
    def test_score_unmodified(self):
        rs=[row(str(i),100,i/3) for i in range(8)];before=copy.deepcopy(rs);m.gate.select_top5(rs);self.assertEqual(rs,before)
    def test_replacement(self):
        rs=[row(str(i),74 if i<2 else 100,10-i) for i in range(8)];self.assertEqual([r['symbol'] for r in m.gate.select_top5(rs)],['2','3','4','5','6'])
    def test_reverse_determinism(self):
        rs=[row(str(i),100,10-i) for i in range(8)];self.assertEqual(m.gate.select_top5(rs),m.gate.select_top5(rs[::-1]))
    def test_same_input(self):
        rs=[row('b'),row('a')];self.assertEqual(m.gate.select_top5(rs),m.gate.select_top5(copy.deepcopy(rs)))
    def test_symbol_tie(self):self.assertEqual([r['symbol'] for r in m.gate.select_top5([row('b'),row('a')])],['a','b'])
    def test_shortfall(self):self.assertEqual(len(m.gate.select_top5([row('a'),row('b',75)])),1)
    def test_parent_causality_fail_closed(self):
        for age in [None,-1,5.001,float('nan'),True]:self.assertEqual(m.gate.select_top5([{**row('a'),'referenceAgeMin':age}]),[])
        self.assertEqual(m.gate.select_top5([{**row('a'),'decisionPriceValid':0}]),[])
    def test_five_minute_parent_boundary(self):self.assertEqual(len(m.gate.select_top5([{**row('a'),'referenceAgeMin':5}])),1)
    def test_bad_score_blocked(self):
        with self.assertRaises(ValueError):m.gate.select_top5([row('a',100,float('nan'))])
    def test_duplicate_blocked(self):
        with self.assertRaises(ValueError):m.gate.select_top5([row('a'),row('a')])
    def test_selector_entry_a_pins(self):self.assertTrue(m.verify()['sourcePins'])
    def test_safety_false(self):self.assertEqual(set(m.verify()['safety'].values()),{False})
    def test_transport_tolerance_is_not_score_rounding(self):
        a=row('a',100,1.0);b=row('b',100,math.nextafter(1.0,math.inf))
        self.assertEqual(m.gate.select_top5([a,b])[0]['symbol'],'b')
    def test_new_stream_first_anchor(self):
        a=row('a');b={**a,'decisionTimestamp':'2024-09-17T10:00:00+09:00','selectorEventId':'later'}
        self.assertEqual(anchors([b,a]),[a]);self.assertEqual(anchors([b]),[b])
if __name__=='__main__':unittest.main()
