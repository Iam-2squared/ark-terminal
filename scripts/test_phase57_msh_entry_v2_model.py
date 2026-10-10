"""Synthetic pre-fit gate. Never loads Project features, labels or predictions."""
import copy
import datetime as dt
import json
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
from predict.research import phase57_msh_entry_long_v2_d30 as m
from scripts.phase57_msh_entry_v2_evaluation import preservation,ratio_gate,choose_threshold


def source(i):
    date = '2024-01-04'
    time = (dt.datetime.fromisoformat(date+'T09:30:00+09:00')+dt.timedelta(minutes=5*i)).isoformat()
    return {'selectorEventId':f'SYNTHETIC-{i}','symbolSessionId':date+'|'+('A' if i < 4 else 'B'),
            'symbol':'A' if i < 4 else 'B','sessionDate':date,'decisionTimestamp':time,
            'decisionPrice':100.,'ridgeScore':float(i),'direction':'LONG',
            'features':{'directionalMomentum3Pct':{'status':'AVAILABLE','value':float(i+1)},
                        'directionalPullback6Pct':{'status':'AVAILABLE','value':float(i+2)}}}


def fixture():
    rows = [m.extract_inputs(source(i)) for i in range(8)]
    sd = math.sqrt(5.25)
    labels = {r['eventId']:{'labelable':True,'barCount':6,'trueMaePct':-(2+(i-3.5)/sd)} for i,r in enumerate(rows)}
    return rows,labels


class ModelTests(unittest.TestCase):
    def test_d30_physical_semantics_and_missing_not_zero(self):
        self.assertAlmostEqual(m.d30_from_lows(100,[101,99,95,92,93,98]),8.)
        self.assertEqual(m.d30_from_lows(100,[101]*6),0.)
        self.assertIsNone(m.target_from_label({'labelable':False,'reason':'PROVIDER_GAP'}))
        with self.assertRaises(m.IntegrityError):m.d30_from_lows(100,[99]*5)

    def test_exact_projection_order_and_future_feature_invariance(self):
        s = source(1)
        original = m.extract_inputs(s)
        s.update(label={'trueMaePct':-99},exitPnl=999999,futureMFE=999)
        self.assertEqual(original,m.extract_inputs(s))
        self.assertEqual(original['raw'],[1.,2.,3.])
        self.assertEqual(original['missing'],[0,0])
        bad = original|{'futureMFE':100}
        with self.assertRaises(m.IntegrityError):m.validate_envelope(bad)

    def test_status_flag_and_true_zero_distinction(self):
        s=source(0)
        s['features']['directionalMomentum3Pct']={'status':'BLOCKED_BY_GRID','value':None}
        s['features']['directionalPullback6Pct']['value']=0.
        x=m.extract_inputs(s)
        self.assertEqual(x['raw'],[0.,None,0.])
        self.assertEqual(x['missing'],[1,0])
        s['features']['directionalMomentum3Pct']={'status':'AVAILABLE','value':None}
        with self.assertRaises(m.IntegrityError):m.extract_inputs(s)

    def test_weighted_median_order_and_boundary(self):
        self.assertEqual(m.weighted_median([4.,1.,3.,2.],[.1,.4,.3,.2],['a','b','c','d']),2.)
        self.assertEqual(m.weighted_median([3.,1.,2.],[.5,.25,.25],['a','b','c']),2.)

    def test_weights_equal_symbol_then_session_then_repeat(self):
        rows=[{'symbol':s,'sessionDate':d} for s,d in [('A','1'),('A','1'),('A','2'),('B','1'),('B','1'),('B','1')]]
        w=m.symbol_weights(rows).tolist()
        self.assertEqual(w[:3],[.125,.125,.25])
        self.assertAlmostEqual(sum(w[3:]),.5)
        self.assertAlmostEqual(sum(w),1.)

    def test_ridge_objective_lambda_and_unpenalized_intercept_analytic(self):
        rows,labels=fixture()
        a=m.fit(rows,labels)
        self.assertAlmostEqual(a['intercept'],2.,places=12)
        for value in a['coefficients'][:3]:self.assertAlmostEqual(value,.25,places=12)
        self.assertEqual(a['coefficients'][3:],[0.,0.])
        self.assertAlmostEqual(a['training']['objective'],.125,places=12)
        self.assertEqual(a['lambda'],1.)

    def test_fold_statistics_missing_support_and_no_future_statistics(self):
        rows,labels=fixture()
        rows[0]['raw'][1]=None;rows[0]['missing'][0]=1
        a=m.fit(rows,labels)
        self.assertEqual(a['medians'][0],5.)
        self.assertEqual(a['training']['missingCounts'],[1,0])
        future=copy.deepcopy(rows[-1]);future['raw']=[1e9,None,1e9];future['missing']=[1,0]
        before=m.digest(a)
        self.assertEqual(m.predict(a,[future])[0]['status'],'SCORED')
        self.assertEqual(before,m.digest(a))
        future['raw'][2]=None;future['missing'][1]=1
        self.assertEqual(m.predict(a,[future])[0]['status'],'UNSUPPORTED_MISSING_STATE')

    def test_determinism_serialization_reload_and_tamper(self):
        rows,labels=fixture()
        a=m.fit(rows,labels)
        self.assertEqual(a,m.fit(list(reversed(rows)),labels))
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'model.json'
            m.save_artifact(p,a)
            self.assertEqual(m.predict(a,rows),m.predict(m.load_artifact(p),rows))
            with self.assertRaises(FileExistsError):m.save_artifact(p,a)
        a['coefficients'][0]+=1
        with self.assertRaises(m.IntegrityError):m.predict(a,rows)

    def test_fit_failure_does_not_fallback_or_drop_columns(self):
        rows,labels=fixture()
        for r in rows:r['raw'][0]=1.
        with self.assertRaises(m.FitError):m.fit(rows,labels)
        rows,labels=fixture()
        with self.assertRaises(m.FitError):m.fit(rows[:6],labels)

    def test_threshold_boundary_latch_and_no_cash_reentry(self):
        rows,_=fixture()
        ps=[{k:r[k] for k in ['eventId','symbol','sessionDate','decisionTimestamp']}|
            {'status':'SCORED','rawPrediction':d,'predictedD30':d} for r,d in zip(rows,[1.,0.,3.,.5,1.00001,1.,0.,0.])]
        states=m.decide(ps,1.)
        self.assertEqual([p['eventId'] for p in states if p['state']=='ENTER'],['SYNTHETIC-0','SYNTHETIC-5'])
        self.assertEqual(states[1]['reason'],'SYMBOL_SESSION_ALREADY_ENTERED')
        for invalid in [None,True,3.,float('inf')]:
            with self.assertRaises(m.IntegrityError):m.decide(ps,invalid)

    def test_prediction_lower_domain_projection(self):
        rows,labels=fixture()
        a=m.fit(rows,labels)
        r=copy.deepcopy(rows[0]);r['raw']=[-1000.,-1000.,-1000.]
        p=m.predict(a,[r])[0]
        self.assertLess(p['rawPrediction'],0.)
        self.assertEqual(p['predictedD30'],0.)

    def test_preservation_requires_remaining_original_window(self):
        r=source(0);r2=source(1);r2['symbolSessionId']=r['symbolSessionId']
        r2['decisionTimestamp']='2024-01-04T10:00:00+09:00'
        labels={r['selectorEventId']:{'labelable':True,'mfePct':6},r2['selectorEventId']:{'labelable':True,'mfePct':9}}
        before=preservation([r,r2],{r['selectorEventId']},labels)
        late=preservation([r,r2],{r2['selectorEventId']},labels)
        self.assertEqual(before['5']['rate'],1.)
        self.assertEqual(late['5']['rate'],0.)

    def test_ratio_undefined_is_not_zero_or_pass(self):
        self.assertEqual(ratio_gate('mean',0,0,.9,'<=',True)['status'],'INCONCLUSIVE')
        self.assertEqual(ratio_gate('tail',0,1,1.,'<=')['status'],'FAIL')
        self.assertEqual(ratio_gate('coverage',None,1,1.,'>=')['status'],'INCONCLUSIVE')

    def test_threshold_none_and_frozen_tie_order(self):
        rows={str(int(t)):{'threshold':t,'metrics':{'meanD30':1.,'enterCount':10},'gates':[
            {'name':'preservation3RatioMin','status':'PASS','ratio':1.},
            {'name':'preservation5RatioMin','status':'PASS','ratio':1.}]} for t in m.THRESHOLDS}
        self.assertEqual(choose_threshold(rows)['threshold'],10.)
        for r in rows.values():r['gates'][0]['status']='FAIL'
        self.assertIsNone(choose_threshold(rows)['threshold'])

    def test_score_free_equal_matches_frozen_v1_adapter(self):
        rows=[{'eventId':str(i),'timestamp':'2024-01-04T09:30:00+09:00','symbol':str(i),'score':2.+i/10} for i in range(4)]
        call=lambda script,data:json.loads(subprocess.run(['node',script],input=json.dumps(data),text=True,capture_output=True,check=True).stdout)
        old=call('scripts/phase57_long_capital_weights.mjs',rows)['EQUAL_MAX3']
        new=call('scripts/phase57_msh_entry_v2_equal.mjs',[{k:v for k,v in r.items() if k!='score'} for r in rows])
        self.assertEqual(old,new)
        bad=subprocess.run(['node','scripts/phase57_msh_entry_v2_equal.mjs'],input=json.dumps(rows),text=True,capture_output=True)
        self.assertNotEqual(bad.returncode,0)


if __name__=='__main__':
    unittest.main(verbosity=2)
