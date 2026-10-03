import copy,datetime as dt,inspect,json,subprocess,unittest
from unittest.mock import patch
from scripts import phase57_selector_pairability_v2 as m
from scripts.test_phase57_selector_path_anatomy import path

class PairabilityV2(unittest.TestCase):
    def test_protocol_frozen_and_safety(self):m.load_protocol()
    def test_protocol_hash_fails_closed(self):
        original=m.read
        def bad(f):
            r=original(f)
            if str(f).endswith('08_protocol_v2_final_hash.json'):r['protocolSHA256']='invalid'
            return r
        with patch.object(m,'read',side_effect=bad),self.assertRaises(AssertionError):m.load_protocol()
    def test_internal_gap_terminal_identified_path_not(self):
        p=path();p['future'][2]['missing']=True
        self.assertEqual(m.a.evaluate(p)['outcomes']['30']['status'],'INCOMPLETE_PATH')
        self.assertAlmostEqual(m.terminal(p,30)['gross'],1)
    def test_missing_open_never_next_bar(self):
        p=path();p['future'][0]['missing']=True
        self.assertEqual(m.terminal(p,30)['status'],'FIRST_ELIGIBLE_BAR_MISSING')
    def test_absent_initial_placeholder_fails_closed(self):
        p=path();del p['future'][0]
        self.assertEqual(m.terminal(p,30)['status'],'FIRST_EXPECTED_BAR_ABSENT')
    def test_missing_close_no_next_close(self):
        p=path();p['future'][5]['missing']=True
        self.assertEqual(m.terminal(p,30)['status'],'TARGET_BAR_MISSING')
    def test_cost_and_open_semantics(self):
        p=path();p['future'][0]['o']=1;r=m.terminal(p,30)
        self.assertAlmostEqual(r['gross'],0);self.assertAlmostEqual(r['net'],-.05)
    def test_fixed_lunch_crossing_ineligible(self):self.assertEqual(m.terminal(path(time='11:00'),60)['status'],'LUNCH_BREAK')
    def test_lunch_session_end_existing_immediate(self):
        p=path(time='11:30');r=m.terminal(p,'SESSION_END')
        self.assertEqual(r['status'],'AVAILABLE');self.assertEqual(r['entryLatencyMin'],60)
        self.assertAlmostEqual(r['gross'],m.a.evaluate(p)['outcomes']['SESSION_END']['gross'])
    def test_old_new_market_end(self):
        for date,remaining in [('2024-11-01',30),('2024-11-06',60)]:
            p=path(date=date,time='14:30');self.assertEqual(m.terminal(p,remaining)['status'],'AVAILABLE');self.assertEqual(m.terminal(p,remaining+5)['status'],'SESSION_END')
    def test_original5_gate_not_lowered(self):
        events={};arms={a:[] for a in m.a.ARMS}
        for arm in arms:
            for i in range(5):
                p=path();eid=arm+str(i);e=m.a.evaluate(p);e['selectorEventId']=eid;e['terminal']={'30':m.terminal(p,30)};events[eid]=e;arms[arm].append(eid)
        baseline=m.a.ARMS[1]
        self.assertEqual(m.pair(events,arms,30,baseline)['timestamps'],1)
        events[arms[baseline][0]]['terminal']['30']={'status':'TARGET_BAR_MISSING'}
        self.assertEqual(m.pair(events,arms,30,baseline)['timestamps'],0)
        secondary=m.pair(events,arms,30,baseline,'observed')
        self.assertEqual(secondary['baselineObservedRows'],4);self.assertEqual(secondary['baselineMissingRowsAtPairedTimes'],1)
        self.assertFalse(secondary['directionalClaimAllowed']);self.assertEqual(len(arms[baseline]),5)
    def test_timestamp_equal_then_session_equal(self):
        rows=[{'decisionTimestamp':'2024-01-01T09:30','net':0} for _ in range(5)]+[{'decisionTimestamp':'2024-01-01T10:00','net':10}]
        self.assertEqual(m.session_means(rows,'net'),{'2024-01-01':5})
    def test_cluster_and_block_reproducibility(self):
        vals={str(i):i for i in range(12)};self.assertEqual(m.cluster(vals,7),m.cluster(vals,7));self.assertEqual(m.cluster(vals)['clusters'],12)
    def test_null_generation_is_prior_deterministic(self):
        f=m.a.old.random_key
        self.assertEqual(f(20260919,'2024-01-01','09:30','TEST'),f(20260919,'2024-01-01','09:30','TEST'))
        self.assertNotEqual(f(1,'2024-01-01','09:30','TEST'),f(2,'2024-01-01','09:30','TEST'))
    def test_phase_a_new_calculations_availability_only(self):
        source=inspect.getsource(m.phase_a)
        for forbidden in ["['gross']","['grossPct']","['net']","['MFE']","['MAE']"]:self.assertNotIn(forbidden,source)
    def test_js_endpoint_gap_parity(self):
        code="import {scoreWindow} from './scripts/phase57_selector_endpoint_scores_v2.mjs';let b=new Map();for(let t=570;t<600;t+=5){if(t==580)continue;b.set(t,{open:100,high:102,low:99,close:101,availableAtJst:'2024-11-06T'+String(Math.floor((t+5)/60)).padStart(2,'0')+':'+String((t+5)%60).padStart(2,'0')+':00+09:00'});}console.log(JSON.stringify(scoreWindow(b,570,30,'2024-11-06')));"
        r=json.loads(subprocess.check_output(['node','--input-type=module','-e',code],cwd=m.ROOT));self.assertAlmostEqual(r['gross'],1);self.assertIsNone(r['MFE']);self.assertIsNone(r['MAE'])
    def test_full_path_results_not_changed(self):
        p=path();self.assertAlmostEqual(m.terminal(p,120)['gross'],m.a.evaluate(p)['outcomes']['120']['gross'])
    def test_future_tail_does_not_change_early_terminal(self):
        p=path();before=m.terminal(p,30);p['future'][10]['c']=2;self.assertEqual(before,m.terminal(p,30))

    def test_timestamp_csv_retains_missing_original_member(self):
        import tempfile,csv,pathlib
        events={};arms={arm:[] for arm in m.a.ARMS};raw=[]
        for arm in arms:
            for j in range(5):
                p=path();p['selectorEventId']=arm+str(j);p['symbol']=str(j)
                if arm==m.a.ARMS[1] and j==0:p['future'][5]['missing']=True
                i=p['selectorEventId'];e=m.a.evaluate(p);e['path']=e.pop('outcomes');e['terminal']={str(h):m.terminal(p,h) for h in m.H}
                events[i]=e;arms[arm].append(i);raw.append(p)
        with tempfile.TemporaryDirectory() as d:
            m.availability_csv(d,events,arms,{'events':raw})
            with (pathlib.Path(d)/'04b_v2_observability_by_timestamp.csv').open() as f:rows=list(csv.DictReader(f))
            r=next(x for x in rows if x['arm']==m.a.ARMS[1] and x['horizon']=='30')
            self.assertEqual(r['originalN'],'5');self.assertEqual(r['endpointObservedN'],'4')
            self.assertEqual(len(json.loads(r['originalMembersAndReasons'])),5)
            self.assertFalse(json.loads(r['full5Pairs'])[m.a.ARMS[0]])

if __name__=='__main__':unittest.main()
