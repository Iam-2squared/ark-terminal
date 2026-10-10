import copy,datetime as dt,unittest
from unittest.mock import patch
from scripts import phase57_causal_entry_exit as m
from scripts.test_phase57_selector_path_anatomy import path

def fixture(time='09:30',date='2024-11-06'):
    p=path(date=date,time=time,n=100);bars=m.a.old.materialize_path(p);decision=m.a.old.timestamp(p['decisionTimestamp'])
    eligible=m.v.boundary(p['decisionTimestamp'],30)=='ELIGIBLE';mapping={b['start']:b for b in bars}
    primary=[mapping.get(decision+dt.timedelta(minutes=5*j)) for j in range(6)] if eligible else []
    return {k:p[k] for k in ['selectorEventId','sessionDate','symbol','decisionTimestamp','decisionPrice']}|{'originalRank':1,'savedV1Score':1.,
        'bars':bars,'primary':primary,'decision':decision,'target':decision+dt.timedelta(minutes=30),'eligible':eligible,'common30':eligible and all(b and b['valid'] for b in primary)}

def constant(value,exit=False):
    f=m.XF if exit else m.EF
    return {'features':f,'mean':[0.]*len(f),'scale':[1.]*len(f),'coef':[0.]*len(f),'intercept':value,'scoreQuintileEdges':[-2,-1,0,1]}

def synthetic_training():
    rs=[]
    for day in range(20):
        date=f'2024-01-{day+1:02}'
        for i in range(10):
            values={f:float(i) for f in m.EF};s={'features':values,'availableAt':date+'T10:00:00+09:00','maxInputBarEnd':date+'T10:00:00+09:00'}
            rs.append({'selectorEventId':date+'|'+str(i),'sessionDate':date,'labelEnd':date+'T10:15:00+09:00','state':s,'target':i/2-2})
    return rs,sorted({r['sessionDate'] for r in rs})

class CausalRecoverability(unittest.TestCase):
    def test_protocol_and_sealed(self):m.protocol()
    def test_hash_fails_closed(self):
        read=m.read
        def bad(f):
            x=read(f)
            if str(f).endswith('protocol-lock.json'):x['protocolSHA256']='bad'
            return x
        with patch.object(m,'read',side_effect=bad),self.assertRaises(AssertionError):m.protocol()
    def test_feature_prefix_availability(self):
        e=fixture();s=m.state(e,e['primary'][:3],e['primary'][2]['end'])
        self.assertEqual(s['availableAt'],s['maxInputBarEnd']);self.assertEqual(set(s['features']),set(m.EF))
    def test_future_bar_rejected_from_state(self):
        e=fixture()
        with self.assertRaises(AssertionError):m.state(e,e['primary'][:4],e['primary'][2]['end'])
    def test_no_future_low_high_in_entry_signal(self):
        e=fixture();model=constant(1);before=m.entry_policy(e,model)
        for b in e['primary'][3:]:b.update(h=9999,l=.01,c=7000,valid=False)
        self.assertEqual(before,m.entry_policy(e,model))
    def test_no_next_bar_hlc_for_open_reference(self):self.assertEqual(m.open_price({'missing':False,'o':100,'valid':False,'h':None,'l':None,'c':None}),100)
    def test_entry_next_open_not_signal_close(self):
        e=fixture();e['primary'][2]['c']=101;e['primary'][3]['o']=98;r=m.entry_policy(e,constant(1))
        self.assertEqual(r['index'],3);self.assertEqual(r['price'],98);self.assertEqual(r['timestamp'],e['primary'][2]['end'].isoformat())
    def test_zero_threshold_is_strict(self):self.assertEqual(m.entry_policy(fixture(),constant(0))['status'],'ABSTAIN')
    def test_missing_prefix_blocks_not_abstains(self):
        e=fixture();e['primary'][0]['valid']=False;self.assertEqual(m.entry_policy(e,constant(-1))['status'],'DATA_BLOCKED')
    def test_missing_fill_does_not_retry(self):
        e=fixture();e['primary'][3]['missing']=True;r=m.entry_policy(e,constant(1))
        self.assertEqual(r['decision'],'ENTER');self.assertEqual(r['status'],'MISSING_OPEN');self.assertEqual(r['index'],3)
    def test_fixed_delay_reuse5(self):
        r=m.fixed_entry(fixture(),5);self.assertEqual(r['index'],1);self.assertEqual(r['delay'],5)
    def test_lunch_boundary_excluded(self):
        for t in ['11:15','11:30','15:15']:self.assertEqual(m.entry_policy(fixture(time=t),constant(1))['status'],'CALENDAR_INELIGIBLE')
    def test_lunch_start_ending_exactly1130_allowed(self):self.assertTrue(fixture(time='11:00')['eligible'])
    def test_old_session_close(self):
        self.assertTrue(fixture(time='14:30',date='2024-11-01')['eligible']);self.assertFalse(fixture(time='14:45',date='2024-11-01')['eligible'])
    def test_mfe_mae_so_far_causal(self):
        e=fixture();en=m.fixed_entry(e);s=m.state(e,e['primary'][:3],e['primary'][2]['end'],en);e['primary'][4].update(h=10000,l=.01)
        self.assertEqual(s,m.state(e,e['primary'][:3],e['primary'][2]['end'],en));self.assertAlmostEqual(s['features']['mfeSoFar'],2)
    def test_exit_no_future_peak(self):
        e=fixture();en=m.fixed_entry(e);before=m.exit_policy(e,en,constant(1,True));e['primary'][4].update(h=99999,l=.01,c=90000,valid=False)
        self.assertEqual(before,m.exit_policy(e,en,constant(1,True)))
    def test_exit_strictly_after_entry(self):
        e=fixture();en=m.entry_policy(e,constant(1));ex=m.exit_policy(e,en,constant(1,True));self.assertEqual(en['index'],3);self.assertEqual(ex['index'],4)
    def test_exit_open_excludes_that_bar_future_extremes(self):
        e=fixture();en=m.fixed_entry(e);ex=m.exit_policy(e,en,constant(1,True));e['primary'][3].update(h=10000,l=.01);r=m.trade(e,en,ex)
        self.assertAlmostEqual(r['MFE'],2);self.assertAlmostEqual(r['MAE'],-1);self.assertEqual(r['intrabarOrder'],'UNKNOWN_NOT_USED')
    def test_cost_and_no_trade_semantics(self):
        e=fixture();en=m.fixed_entry(e);r=m.trade(e,en,m.fixed_exit(e,en));self.assertAlmostEqual(r['net'],.95)
        r=m.trade(e,m.entry_policy(e,constant(-1)),{});self.assertEqual(r['net'],0);self.assertFalse(r['entered'])
    def test_missing_not_zero_imputed(self):
        e=fixture();e['primary'][0]['missing']=True;self.assertIsNone(m.trade(e,m.fixed_entry(e),{})['net'])
    def test_entry_target_is_forward_after_cost(self):
        rs,av=m.labelled_states([fixture()],'entry');self.assertEqual(len(rs),3);self.assertAlmostEqual(rs[0]['target'],.95)
    def test_exit_target_cost_cancels(self):
        e=fixture();rs,av=m.labelled_states([e],'exit',{e['selectorEventId']:m.fixed_entry(e)});self.assertAlmostEqual(rs[0]['target'],-1)
    def test_train_eval_isolation(self):
        rs,days=synthetic_training();rs[0]['sessionDate']='2025-01-01'
        with self.assertRaises(AssertionError):m.fit(rs,m.EF,days)
    def test_cross_session_label_rejected(self):
        rs,days=synthetic_training();rs[0]['labelEnd']='2025-01-01T10:15:00+09:00'
        with self.assertRaises(AssertionError):m.fit(rs,m.EF,days)
    def test_deterministic_fit(self):
        rs,days=synthetic_training();self.assertEqual(m.fit(rs,m.EF,days),m.fit(rs,m.EF,days))
    def test_no_model_from_insufficient_fit(self):
        rs,days=synthetic_training();self.assertIsNone(m.fit(rs[:100],m.EF,days))
    def test_evaluation_labels_do_not_change_training_model(self):
        rs,days=synthetic_training();model=m.fit(rs,m.EF,days);evalrows=copy.deepcopy(rs)
        for r in evalrows:r['target']=-10000
        self.assertEqual(model,m.fit(rs,m.EF,days))
    def test_paired_identical_baseline_zero_delta(self):
        rows=m.replay([fixture()]);c=m.paired(rows,rows);self.assertEqual(c['pairedN'],1);self.assertEqual(c['delta']['sessionEqualMean'],0)
    def test_gate_does_not_accept_tiny_positive_sample(self):
        rows=m.replay([fixture()]);g=m.economic_gate(m.paired(rows,rows),'entry');self.assertFalse(g['pass']);self.assertFalse(g['checks']['sampleSessions'])
    def test_four_cell_gate_na(self):self.assertEqual(m.four_cells({'00':[]})['status'],'NOT_APPLICABLE')
    def test_four_cell_decomposition(self):
        rows=m.replay([fixture()]);cells={}
        for name,value in [('00',1),('10',2),('01',3),('11',5)]:
            cells[name]=copy.deepcopy(rows);cells[name][0]['result']['net']=value
        r=m.four_cells(cells);self.assertEqual(r['contributions']['interaction']['sessionEqualMean'],1);self.assertEqual(r['contributions']['total']['sessionEqualMean'],4)
    def test_no_winner_filter_in_load(self):
        es=m.load_events();self.assertEqual(len(es),3800);self.assertEqual({e['originalRank'] for e in es},{1,2,3,4,5})
    def test_frozen_exit_functions_unchanged_and_fair_cap(self):
        r=m.frozen_comparison([fixture()]);self.assertEqual(r['n'],1);self.assertFalse(r['sourceFunctionChanged']);self.assertAlmostEqual(r['fixed12Net']['mean'],.95)

if __name__=='__main__':unittest.main()
