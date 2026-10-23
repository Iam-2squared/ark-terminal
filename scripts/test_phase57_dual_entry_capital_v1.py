"""Synthetic tests of cash, event order, incomplete exposure and causal isolation."""
import copy
import unittest
from scripts import phase57_dual_entry_capital_v1 as m
from scripts import phase57_dual_entry_exit_integration_v1 as x


class CapitalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = x.load_module(x.CANDIDATE,'cap_test_candidate')
        cls.fixed = x.load_module(x.FIXED,'cap_test_fixed')
        cls.c = x.read(x.ROOT / m.OLD_CONTRACT)

    def entry(self,symbol='12340',minute=570,price=100.05):
        oid='2025-06-02|'+symbol
        return {'opportunity':oid,'session':'2025-06-02','symbol':symbol,
                'entryId':oid+'|'+str(minute),'entryMinute':minute,'price':price}

    def row(self,symbol='12340',minute=570):
        e=self.entry(symbol,minute)
        raw={'today':[[t,100.,100.5,99.5,100.,100,10000] for t in range(570,925)]}
        p=x.adapt(e,raw);p['future']=p['future'][:12]
        return {'entry':e,'path':p,'candidateA':{'forbiddenFuture':999}}

    def replay(self,rows,arm='ONE_LOT_REFERENCE',c=None):
        return m.replay(rows,['2025-06-02'],arm,c or self.c,self.candidate,self.fixed)

    def test_equal_inherits_budget_divisor3_not_position_cap3(self):
        self.assertEqual(self.c['maximumConcurrentPositions'],10)
        es=[dict(self.entry(str(i)),expectedBars=12) for i in range(4)]
        rs,cash=m.allocate(es,[],1000000,1000000,'EQUAL_MAX3',self.c)
        self.assertEqual(rs[0]['targetJpy'],1000000/3)
        self.assertGreaterEqual(cash,0)
        self.assertTrue(all(r['quantity']%100==0 for r in rs))

    def test_one_lot_uses_actual_cash_when_equity_unknown(self):
        e=dict(self.entry(),expectedBars=12)
        one,_=m.allocate([e],[],20000,None,'ONE_LOT_REFERENCE',self.c)
        equal,_=m.allocate([e],[],20000,None,'EQUAL_MAX3',self.c)
        self.assertEqual(one[0]['quantity'],100)
        self.assertEqual(equal[0]['reason'],'CURRENT_EQUITY_UNKNOWN')

    def test_same_symbol_and_ten_position_cap(self):
        e=dict(self.entry(),expectedBars=12)
        rs,_=m.allocate([e],[{'symbol':e['symbol']}],1000000,1000000,'ONE_LOT_REFERENCE',self.c)
        self.assertEqual(rs[0]['reason'],'SYMBOL_ALREADY_OPEN')
        rs,_=m.allocate([e],[{'symbol':str(i)} for i in range(10)],1000000,1000000,'ONE_LOT_REFERENCE',self.c)
        self.assertEqual(rs[0]['reason'],'MAX_CONCURRENT_POSITIONS')

    def test_fee_can_make_nominal_one_lot_unaffordable(self):
        e=dict(self.entry(price=100),expectedBars=12)
        rs,cash=m.allocate([e],[],10000,10000,'ONE_LOT_REFERENCE',self.c)
        self.assertEqual(rs[0]['reason'],'INSUFFICIENT_CASH')
        self.assertEqual(cash,10000)

    def test_complete_fixed_cap_cost_matches_frozen_exit(self):
        r=self.row();out=self.replay([r]);trade=out['closedTrades'][0]
        ref=x.replay_pair(r['path'],self.candidate,self.fixed)['candidateA']
        self.assertAlmostEqual(trade['netPct'],ref['netPct'])
        self.assertAlmostEqual(trade['feesJpy'],r['entry']['price']*100*.0005)
        self.assertEqual(out['summary']['closed'],1)
        self.assertAlmostEqual(out['summary']['cashBalanceJpy'],1000000+trade['pnlJpy'])

    def test_missing_locks_capital_without_synthetic_liquidation(self):
        r=self.row();r['path']['future'][1]['missing']=True
        out=self.replay([r]);s=out['summary']
        self.assertEqual(s['unresolved'],1)
        self.assertEqual(s['closed'],0)
        self.assertIsNone(s['portfolioReturnPct'])
        self.assertIsNone(s['maxDrawdownPct'])
        self.assertGreater(s['lockedPurchaseNotionalJpy'],0)
        self.assertAlmostEqual(s['cashBalanceJpy']+s['lockedPurchaseNotionalJpy'],1000000+s['realizedLedgerPnlJpy'])

    def test_exit_cash_release_precedes_entry_at_same_timestamp(self):
        c=dict(self.c,initialCashJpy=10020)
        a=self.row('10000',570);b=self.row('20000',630)
        out=self.replay([a,b],c=c)
        self.assertEqual(out['summary']['accepted'],2)
        self.assertTrue(out['decisions'][1]['sameTimestampCashRecycling'])

    def test_replay_never_reads_r13_outcome_payload(self):
        class Guard(dict):
            def __getitem__(self,k):
                if k not in ('entry','path'):
                    raise AssertionError('OUTCOME_BACKFLOW')
                return super().__getitem__(k)
        self.assertEqual(self.replay([Guard(self.row())])['summary']['accepted'],1)

    def test_future_suffix_cannot_change_prior_allocation(self):
        a=self.row();before=self.replay([a])['decisions']
        b=copy.deepcopy(a);b['path']['future'][-1].update(h=200,c=50)
        self.assertEqual(before,self.replay([b])['decisions'])

    def test_causal_open_exit_ignores_current_high_close(self):
        r=self.row();bs=r['path']['future']
        bs[0].update(h=4,c=3);bs[1].update(h=4,c=1);bs[2].update(o=.8,h=99,c=-50)
        result=m.stream_reference(r['path'],self.candidate,self.fixed)
        self.assertEqual(result['reason'],'PROTECT_EXIT')
        self.assertAlmostEqual(result['netPct'],.75)
        self.assertEqual(result['exitTimestamp'],bs[2]['openTimestamp'])
        r['path']['future'][3]['missing']=True
        out=self.replay([r])
        self.assertEqual(out['summary']['unresolved'],0)
        self.assertAlmostEqual(out['closedTrades'][0]['netPct'],.75)

    def test_stale_marks_are_not_forward_filled_for_sizing(self):
        a=self.row('10000',570);b=self.row('20000',572)
        out=self.replay([a,b],'EQUAL_MAX3')
        self.assertEqual(out['decisions'][1]['reason'],'CURRENT_EQUITY_UNKNOWN')

    def test_stream_matches_batch_candidate_and_terminal_cap(self):
        for protect in [False,True]:
            r=self.row()
            if protect:
                r['path']['future'][0].update(h=4,c=3)
                r['path']['future'][1].update(c=1)
            batch=x.replay_pair(r['path'],self.candidate,self.fixed)['candidateA']
            stream=m.stream_reference(r['path'],self.candidate,self.fixed)
            self.assertEqual(stream['exitTimestamp'],batch['exitTimestamp'])
            self.assertAlmostEqual(stream['netPct'],batch['netPct'])


if __name__=='__main__':
    unittest.main()
