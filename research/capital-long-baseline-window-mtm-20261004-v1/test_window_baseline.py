"""Focused synthetic tests. No cohort replay, provider, or model fitting."""
import copy
from decimal import Decimal
import unittest
from baseline_replay import run, candidate_runtime
from window_mtm import latest_window_bar
from portfolio_metrics import summarize

DAY='2025-07-01'

def entry(name='SYNTH', score=.8, minute=580):
    return {'watch_key':DAY+'|'+name,'session':DAY,'symbol':name,
            'fill_timestamp':DAY+'T%02d:%02d:00+09:00'%divmod(minute,60),
            'fill_price':100.05,'first_intent':{'score':score},
            'first_upside':{'5':{'minute':None}}}

def fixture(count=1):
    entries=[entry('SYNTH_%02d'%i) for i in range(count)]
    caps={e['watch_key']:'1000000' for e in entries}
    market={e['watch_key']:{'today':[[m,100,102,99,101+m/1000,100,10000] for m in range(580,584)]} for e in entries}
    outcomes={e['watch_key']:{'historical_cash_release_authorized':True,
                'integrated_exit_price':'103.9480','cash_release_timestamp':DAY+'T09:48:00+09:00',
                'reason':'PRIOR_FROZEN_EXIT'} for e in entries}
    return entries,caps,market,outcomes

class WindowTests(unittest.TestCase):
    def test_same_window_last_close_not_final_minute_required(self):
        bars=[[580,0,0,0,100],[583,0,0,0,103]]
        self.assertEqual(latest_window_bar(bars,585)[4],103)
        self.assertEqual(latest_window_bar(list(reversed(bars)),585)[4],103)

    def test_start_included_end_excluded(self):
        bars=[[579,0,0,0,1],[580,0,0,0,100],[585,0,0,0,100000]]
        self.assertEqual(latest_window_bar(bars,585)[4],100)

    def test_no_cross_window_carry(self):
        self.assertIsNone(latest_window_bar([[583,0,0,0,103]],590))

    def test_empty_window_no_interpolation(self):
        self.assertIsNone(latest_window_bar([[579,0,0,0,99],[585,0,0,0,105]],585))

    def test_future_price_suffix_invariant(self):
        bars=[[583,0,0,0,103],[585,0,0,0,104],[586,0,0,0,105]]
        changed=copy.deepcopy(bars)
        for row in changed:
            if row[0]>=585:row[4]=1e100
        self.assertEqual(latest_window_bar(bars,585),latest_window_bar(changed,585))

    def test_high_low_not_used_for_mark(self):
        bars=[[583,100,1000000,.01,103]]
        self.assertEqual(latest_window_bar(bars,585)[4],103)

    def test_invalid_zero_nan_price_not_invented(self):
        self.assertIsNone(latest_window_bar([[580,0,0,0,0],[581,0,0,0,float('nan')]],585))

    def test_duplicate_conflict_fail_closed(self):
        with self.assertRaises(ValueError):latest_window_bar([[583,0,0,0,103],[583,0,0,0,104]],585)

    def test_future_duplicate_conflict_not_prematurely_read(self):
        self.assertEqual(latest_window_bar([[583,0,0,0,103],[586,0,0,0,104],[586,0,0,0,105]],585)[4],103)

class BaselineTests(unittest.TestCase):
    def run_case(self,arm='CURRENT_CAUSAL_BASELINE',n=3,f=None):
        return run(arm,n,*(fixture() if f is None else f))

    def test_complete_cash_endpoint_and_pnl(self):
        result,decisions,curve,trades,_=self.run_case()
        self.assertTrue(result['funding_trace_complete'])
        self.assertEqual(result['accepted_observed_N'],1)
        self.assertEqual(result['closed_trades_observed_N'],1)
        self.assertAlmostEqual(result['final_equity']-1000000,float(Decimal(trades[0]['pnl'])),8)
        self.assertEqual(trades[0]['commission'],0)

    def test_auction_receipt_cash_never_backdated(self):
        f=fixture();key=f[0][0]['watch_key'];f[3][key]['cash_release_timestamp']=DAY+'T09:46:00+09:00'
        _,_,frames,_,_=self.run_case(f=f)
        self.assertEqual(next(x for x in frames if '09:45:' in x['timestamp'])['positions'],1)
        self.assertEqual(next(x for x in frames if '09:46:' in x['timestamp'])['positions'],0)

    def test_missing_next_window_stops_not_carries(self):
        f=fixture();key=f[0][0]['watch_key'];f[3][key]['cash_release_timestamp']=DAY+'T09:53:00+09:00'
        r,d,c,t,_=self.run_case(f=f)
        self.assertEqual(r['blocker']['reason'],'MISSING_FUNDED_WINDOW_MTM_MARK')
        self.assertIsNone(r['final_equity'])
        self.assertEqual(t,[])
        self.assertEqual(r['accepted_observed_N'],1)

    def test_future_execution_availability_not_buy_predicate(self):
        f=fixture();g=copy.deepcopy(f);key=g[0][0]['watch_key']
        g[3][key]['historical_cash_release_authorized']=False
        g[3][key]['reason']='UNKNOWN_NO_ADMISSIBLE_SOURCE'
        a=self.run_case(f=f)[1][0];b=self.run_case(f=g)[1][0]
        self.assertEqual(a,b)

    def test_future_entry_outcomes_not_projection(self):
        e=entry();g=copy.deepcopy(e)
        g.update(profit=1e100,future_high=1e100,next_day_price=.001,execution_evidence_status='UNKNOWN',future_state='DROP')
        self.assertEqual(candidate_runtime(e),candidate_runtime(g))

    def test_post_1520_cutoff_zero_funding(self):
        for minute in [920,921,925]:
            e=entry(minute=minute);f=([e],{e['watch_key']:'1000000'},{e['watch_key']:{'today':[]}}, {})
            r,d,_,_,_=self.run_case(f=f)
            self.assertEqual(d[0]['quantity'],0)
            self.assertEqual(d[0]['reason'],'CAPITAL_EOD_ENTRY_CUTOFF')

    def test_adaptive_cap_not_one_over_N(self):
        qs=[self.run_case(n=n)[1][0]['quantity'] for n in [3,4,5]]
        self.assertEqual(qs[0],qs[1]);self.assertEqual(qs[1],qs[2])
        fixed=[self.run_case(arm='FIXED_SANITY',n=n)[1][0]['quantity'] for n in [3,4,5]]
        self.assertGreater(fixed[0],fixed[1]);self.assertGreater(fixed[1],fixed[2])

    def test_concurrent_cap_lot_and_nonnegative_cash(self):
        for n in [3,4,5]:
            r,d,c,t,_=self.run_case(n=n,f=fixture(6))
            self.assertEqual(r['max_concurrent_observed'],n)
            self.assertTrue(all(x['quantity']%100==0 for x in d))
            self.assertTrue(all(x['cash']>=0 and x['positions']<=n for x in c))

    def test_liquidity_is_common_capacity_not_future_source(self):
        f=fixture();key=f[0][0]['watch_key'];f[1][key]='1000'
        r,d,c,t,_=self.run_case(f=f)
        self.assertEqual(d[0]['reason'],'CAPITAL_SKIP_LIQUIDITY')
        self.assertEqual(t,[])

    def test_deterministic_rerun(self):
        self.assertEqual(self.run_case(),self.run_case())

    def test_return_geometric_arithmetic_and_median(self):
        r=self.run_case()[0]
        self.assertAlmostEqual(r['geometric_mean_session'],r['total_return'],12)
        self.assertAlmostEqual(r['arithmetic_mean_session'],r['total_return'],12)
        self.assertAlmostEqual(r['median_session_return'],r['total_return'],12)

    def test_rolling20_all_windows_include_initial_cash(self):
        days=['2025-07-%02d'%(i+1) for i in range(22)]
        frames=[]
        for i,day in enumerate(days):
            for t in ['09:00','15:31']:
                frames.append({'session':day,'timestamp':day+'T'+t+':00+09:00','equity':1e6*1.01**(i+1),
                               'cash':1e6*1.01**(i+1),'investment':0,'utilization':0,'positions':0})
        r=summarize(frames,[],days,[])
        self.assertEqual(r['rolling']['20']['windows_N'],3)
        self.assertAlmostEqual(r['rolling']['20']['min_multiple'],1.01**20,12)
        self.assertAlmostEqual(r['geometric_mean_session'],.01,12)

if __name__=='__main__':unittest.main(verbosity=2)
