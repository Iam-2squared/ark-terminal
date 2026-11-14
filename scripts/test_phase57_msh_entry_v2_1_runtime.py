"""Synthetic prefit gates. Never fits or scores Project observations."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from predict.research import phase57_msh_entry_long_v2_1_d30 as m
from scripts import phase57_msh_entry_v2_1_development as dev
from scripts import phase57_msh_entry_v2_1_evaluation as ev
from scripts import audit_phase57_msh_entry_v2_1_predevelopment as frozen


def fixture():
    rows=[];labels={};saved={}
    for i in range(8):
        eid='SYNTHETIC-'+str(i);symbol=str(10000+i//4);date='2024-09-'+str(17+i%4)
        value=float(i%4)
        rows.append({'selectorEventId':eid,'symbolSessionId':date+'|'+symbol,'symbol':symbol,
            'sessionDate':date,'decisionTimestamp':date+'T09:30:00+09:00','decisionPrice':100.,
            'features':{k:{'status':'AVAILABLE','value':value} for k in m.FEATURE_ORDER[:2]},'direction':'LONG'})
        z=(value-1.5)/(1.25**.5)
        labels[eid]={'labelable':True,'barCount':6,'trueMaePct':-(2+z),'mfePct':6.}
        saved[eid]={'state':'ENTER','reason':'FIRST_QUALIFYING_DECISION','expectedClass':2.5}
    return rows,labels,saved


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=frozen.read(frozen.ROOT/frozen.CONTRACT)

    def test_contract_sha_and_exact_configuration(self):
        self.assertEqual(frozen.sha(frozen.ROOT/frozen.CONTRACT),m.CONTRACT_SHA)
        self.assertEqual(self.c['features']['order'],m.FEATURE_ORDER)
        self.assertEqual(self.c['decision']['thresholdCandidatesPct'],list(m.THRESHOLDS))
        self.assertEqual(self.c['model']['lambda'],1.)
        self.assertEqual(len(m.FEATURE_ORDER),4)

    def test_projection_excludes_selector_opportunity_and_future(self):
        rows,_,_=fixture();a=m.extract_inputs(rows[0])
        rows[0].update(ridgeScore=999, ridgeRank=-999,expectedClass=100,futureMAE=-100,portfolioPnl=1e8)
        self.assertEqual(a,m.extract_inputs(rows[0]))
        a['futureMAE']=-100
        with self.assertRaisesRegex(m.IntegrityError,'NON_CAUSAL'):m.validate_envelope(a)

    def test_missing_zero_status_and_order(self):
        rows,_,_=fixture();r=rows[0]
        r['features'][m.FEATURE_ORDER[1]]={'status':'UNAVAILABLE','value':None}
        x=m.extract_inputs(r)
        self.assertEqual(x['raw'],[0.,None]);self.assertEqual(x['missing'],[0,1])
        m.validate_envelope(x)
        r['features'][m.FEATURE_ORDER[1]]['value']=0.
        with self.assertRaisesRegex(m.IntegrityError,'UNAVAILABLE_HAS_VALUE'):m.extract_inputs(r)

    def test_invalid_available_value_fails(self):
        rows,_,_=fixture();rows[0]['features'][m.FEATURE_ORDER[0]]['value']=float('nan')
        with self.assertRaisesRegex(m.IntegrityError,'AVAILABLE_NONFINITE'):m.extract_inputs(rows[0])

    def test_weighted_median_observed_boundary(self):
        self.assertEqual(m.weighted_median([None,3.,1.,2.],[.5,.1,.1,.3],['d','c','a','b']),2.)
        self.assertEqual(m.weighted_median([0.,2.],[.5,.5],['a','b']),0.)
        with self.assertRaises(m.FitError):m.weighted_median([1.,None],[.5,.5],['a','b'])

    def test_repeated_symbol_weights(self):
        rows=[{'symbol':'A','sessionDate':'1'},{'symbol':'A','sessionDate':'1'},
              {'symbol':'A','sessionDate':'2'},{'symbol':'B','sessionDate':'1'}]
        self.assertEqual(m.symbol_weights(rows).tolist(),[.125,.125,.25,.5])

    def test_d30_continuous_strict_censor_semantics(self):
        self.assertAlmostEqual(m.d30_from_lows(100,[99,98,90,91,93,95]),10.)
        self.assertEqual(m.d30_from_lows(100,[101]*6),0.)
        self.assertIsNone(m.target_from_label({'labelable':False,'trueMaePct':-99}))
        with self.assertRaises(m.IntegrityError):m.d30_from_lows(100,[99]*5)
        with self.assertRaises(m.IntegrityError):m.target_from_label({'labelable':True,'trueMaePct':1.,'barCount':6})

    def test_analytic_ridge_objective_lambda_intercept(self):
        rows,labs,_=fixture();a=m.fit(dev.decision_inputs(rows),labs)
        self.assertAlmostEqual(a['intercept'],2.)
        self.assertAlmostEqual(a['coefficients'][0],1/3)
        self.assertAlmostEqual(a['coefficients'][1],1/3)
        self.assertEqual(a['coefficients'][2:],[0.,0.])
        self.assertAlmostEqual(a['training']['objective'],1/6)
        self.assertLess(a['training']['normalEquationResidualInf'],1e-12)
        self.assertEqual(a['training']['largestSymbolWeightShare'],.5)

    def test_determinism_serialization_and_tamper(self):
        rows,labs,_=fixture();inputs=dev.decision_inputs(rows)
        a=m.fit(inputs,labs);b=m.fit(list(reversed(inputs)),labs)
        self.assertEqual(a,b)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'model.json';m.save_artifact(p,a);b=m.load_artifact(p)
            self.assertEqual(m.predict(a,inputs),m.predict(b,inputs))
            with self.assertRaises(FileExistsError):m.save_artifact(p,a)
        a['coefficients'][0]+=1
        with self.assertRaises(m.IntegrityError):m.validate_artifact(a)

    def test_fit_only_median_scaling_and_label_exclusion(self):
        rows,labs,_=fixture();inputs=dev.decision_inputs(rows)
        extra=copy.deepcopy(inputs[0]);extra['eventId']='UNOBSERVED';extra['raw']=[1e9,-1e9]
        labs['UNOBSERVED']={'labelable':False,'reason':'PROVIDER_GAP'}
        a=m.fit(inputs,labs);b=m.fit(inputs+[extra],labs)
        for k in ['medians','means','stds','coefficients','intercept']:self.assertEqual(a[k],b[k])
        self.assertEqual(b['training']['excludedIds'],['UNOBSERVED'])

    def test_unseen_missing_skips_without_fallback(self):
        rows,labs,saved=fixture();inputs=dev.decision_inputs(rows);a=m.fit(inputs,labs)
        inputs[0]['raw'][0]=None;inputs[0]['missing'][0]=1
        scores=m.predict(a,inputs)
        dec=m.decide(inputs,saved,scores,10.)
        d=next(d for d in dec if d['eventId']==inputs[0]['eventId'])
        self.assertEqual(d['reason'],'UNSUPPORTED_MISSING_STATE');self.assertTrue(d['shadowAnchorConsumed'])
        self.assertEqual(d['state'],'SKIP_THIS_DECISION')

    def test_low_support_zero_variance_duplicate_fail(self):
        rows,labs,_=fixture();inputs=dev.decision_inputs(rows)
        with self.assertRaises(m.FitError):m.fit(inputs[:6],labs)
        with self.assertRaises(m.IntegrityError):m.fit(inputs+[inputs[0]],labs)
        for r in inputs:r['raw']=[1.,1.]
        with self.assertRaisesRegex(m.FitError,'VARIANCE'):m.fit(inputs,labs)

    def test_risk_veto_consumes_v1_anchor_no_reentry(self):
        rows,labs,saved=fixture();r=rows[0]
        later=copy.deepcopy(r);later['selectorEventId']='LATER';later['decisionTimestamp']=r['sessionDate']+'T10:00:00+09:00'
        rows.append(later);saved['LATER']={'state':'SKIP_THIS_DECISION','reason':'ALREADY_ENTERED','expectedClass':3.}
        inputs=dev.decision_inputs(rows)
        scores=[{k:x[k] for k in ['eventId','symbol','sessionDate','decisionTimestamp']}|
                {'status':'SCORED','rawPrediction':11.,'predictedD30':11.} for x in inputs[:-1]]
        dec=m.decide(inputs,saved,scores,10.)
        self.assertEqual(sum(x['state']=='ENTER' for x in dec),0)
        self.assertEqual(next(x for x in dec if x['eventId']=='LATER')['reason'],'NOT_OPPORTUNITY_ANCHOR')
        with self.assertRaises(m.IntegrityError):m.decide(inputs,saved,scores[:-1],10.)

    def test_threshold_inclusive_boundary_and_no_new_threshold(self):
        rows,_,saved=fixture();inputs=dev.decision_inputs(rows)
        for t in m.THRESHOLDS:
            scores=[{k:x[k] for k in ['eventId','symbol','sessionDate','decisionTimestamp']}|
                    {'status':'SCORED','rawPrediction':t,'predictedD30':t} for x in inputs]
            self.assertTrue(all(d['state']=='ENTER' for d in m.decide(inputs,saved,scores,t)))
        with self.assertRaises(m.IntegrityError):m.decide(inputs,saved,scores,2.5)

    def test_largest_feasible_threshold_no_mean_minimization(self):
        results={str(int(t)):{'threshold':t,'gates':[{'name':'syntheticGate','status':'PASS'}],'metrics':{'meanD30':t}} for t in m.THRESHOLDS}
        self.assertEqual(ev.choose_threshold(results)['threshold'],10.)
        results['10']['gates'][0]['status']='FAIL'
        self.assertEqual(ev.choose_threshold(results)['threshold'],5.)
        for x in results.values():x['gates'][0]['status']='INCONCLUSIVE'
        self.assertIsNone(ev.choose_threshold(results)['threshold'])

    def test_retention_exact_v1_anchor_and_unknown_not_loser(self):
        rows,labs,saved=fixture();b=dev.baseline_for(rows,saved);a=copy.deepcopy(b)
        a[0]['state']='SKIP_THIS_DECISION';labs[rows[1]['selectorEventId']]={'labelable':False,'reason':'SESSION_END'}
        x=ev.metrics(rows,a,b,labs,sorted({r['sessionDate'] for r in rows}))
        self.assertEqual(x['enterCount'],7);self.assertEqual(x['strict30mCount'],6)
        self.assertEqual(x['winnerRetention']['5']['rate'],6/7)
        self.assertEqual(x['precision']['5']['rate'],1.)
        self.assertEqual(x['coverageRate'],6/7)

    def test_gate_keys_values_and_no_false_pass_undefined(self):
        rows,labs,saved=fixture();b=dev.baseline_for(rows,saved)
        met=ev.metrics(rows,b,b,labs,[rows[0]['sessionDate']])
        gates=ev.entry_gates(met,met,self.c)
        self.assertEqual(set(g['name'] for g in gates),set(frozen.PRIMARY)|{'absoluteStrictLabelCoverageGapMax'})
        self.assertEqual([g['name'] for g in gates if g['status']=='FAIL'],['adverseMeanRatioMax'])
        self.assertEqual(ev.verdict(False,{'x':[{'status':'PASS'}]}),'MSH_ENTRY_LONG_V2_1_DEVELOPMENT_BLOCKED')
        self.assertEqual(ev.verdict(True,{'x':[{'status':'FAIL'}]}),'MSH_ENTRY_LONG_V2_1_DEVELOPMENT_FAIL')
        self.assertEqual(ev.verdict(True,{'x':[{'status':'INCONCLUSIVE'}]}),'MSH_ENTRY_LONG_V2_1_DEVELOPMENT_BLOCKED')
        self.assertEqual(ev.verdict(True,{'x':[{'status':'PASS'}]}),'MSH_ENTRY_LONG_V2_1_DEVELOPMENT_PASS')

    def synthetic_sessions(self):
        rows=[];saved={};labels={}
        for date in self.c['universe']['sessions']:
            for i in range(15):
                row=copy.deepcopy(fixture()[0][0]);eid=date+'|'+str(10000+i)
                row.update(selectorEventId=eid,symbolSessionId=eid,symbol=str(10000+i),sessionDate=date,
                           decisionTimestamp=date+'T09:30:00+09:00')
                rows.append(row);saved[eid]={'state':'ENTER','reason':'FIRST_QUALIFYING_DECISION','expectedClass':2.5}
                labels[eid]={'labelable':True,'barCount':6,'trueMaePct':-2.,'mfePct':6.}
        return rows,saved,labels

    def test_chronology_symbol_group_and_no_oof_duplicates(self):
        rows,_,_=self.synthetic_sessions();outer=[];held=[]
        for fold in self.c['cv']['folds']:
            fit,cal,refit,evals,audit=dev.partition(rows,fold,self.c)
            self.assertLess(max(m.timestamp(r['decisionTimestamp'])+1800 for r in fit),min(m.timestamp(r['decisionTimestamp']) for r in cal))
            self.assertFalse(set(r['sessionDate'] for r in refit)&set(r['sessionDate'] for r in evals))
            self.assertFalse(any(audit.values()));outer.extend(r['selectorEventId'] for r in evals)
            for g in range(5):
                fit,cal,refit,evals,audit=dev.partition(rows,fold,self.c,g)
                self.assertFalse({r['symbol'] for r in fit+cal+refit}&{r['symbol'] for r in evals})
                self.assertTrue(all(frozen.symbol_group(r['symbol'])==g for r in evals))
                held.extend(r['selectorEventId'] for r in evals)
        self.assertEqual(len(outer),len(set(outer)));self.assertEqual(sorted(held),sorted(outer))

    def test_none_stops_outer_and_persistence_precedes_selection(self):
        rows,saved,labels=self.synthetic_sessions();calls=[];writes=[]
        def score(fit,evaluate,name):
            calls.append(name)
            return [{k:v for k,v in m.extract_inputs(r).items() if k in ['eventId','symbol','sessionDate','decisionTimestamp']}|
                    {'status':'SCORED','rawPrediction':100.,'predictedD30':100.,'missing':[0,0]} for r in evaluate]
        def persist(name,value):writes.append(name);return 'sha'
        result=dev.run_replica(rows,saved,labels,None,self.c,self.c['cv']['folds'][0],None,score,persist)
        self.assertEqual(calls,['chrono-1-inner']);self.assertEqual(result['outerDecisions'],[])
        self.assertIsNone(result['selection']['threshold'])
        self.assertLess(writes.index('chrono-1-calibration'),writes.index('chrono-1-selection'))
        self.assertEqual(set(result['innerThresholdResults']),{'1','2','5','10'})
        def failed(name,value):return None if name.endswith('calibration') else 'sha'
        with self.assertRaisesRegex(m.IntegrityError,'PERSISTENCE_REQUIRED'):
            dev.run_replica(rows,saved,labels,None,self.c,self.c['cv']['folds'][0],None,score,failed)

    def test_runtime_safety_and_prefit_receipt(self):
        self.assertEqual(len(self.c['safety']),9);self.assertFalse(any(self.c['safety'].values()))
        r={'status':'PASS','contractSHA':m.CONTRACT_SHA,'syntheticOnly':True,
           'implementationPins':{p:'0'*64 for p in dev.MODEL_SOURCES}}
        with self.assertRaisesRegex(m.IntegrityError,'PREFIT_CODE_CHANGED'):dev.require_prefit(r)

    def test_final_gates_cover_contract_and_unknown_separation(self):
        rows,labs,saved=fixture();bd=dev.baseline_for(rows,saved)
        met=ev.metrics(rows,bd,bd,labs,[rows[0]['sessionDate']])
        gates=ev.final_gates(met,met,self.c,[(i,met,met) for i in range(4)],met,
                            [(i,met,met) for i in range(5)],{'directRejectedMinusAcceptedMeanD30':None})
        names={g['name'] for g in gates['chronological']}
        self.assertEqual(names,set(frozen.PRIMARY)|set(frozen.GUARDRAILS)-{'chronologicalFoldCount'})
        self.assertEqual({g['name'] for g in gates['symbolDisjoint']},set(frozen.CROSS)-{'groups'})
        self.assertEqual(next(g for g in gates['chronological'] if g['name']=='directRiskRejectedMinusAcceptedMeanD30Min')['status'],'INCONCLUSIVE')
        self.assertEqual(ev.stability([(0,met,met)],3,4,'test')['status'],'INCONCLUSIVE')

    def test_supported_missing_imputed_fold_stats_and_terms(self):
        rows,labs,_=fixture();inputs=dev.decision_inputs(rows)
        inputs[0]['raw']=[None,None];inputs[0]['missing']=[1,1]
        a=m.fit(inputs,labs);pred=m.predict(a,inputs)
        p=next(x for x in pred if x['eventId']==inputs[0]['eventId'])
        self.assertEqual(p['status'],'SCORED');self.assertEqual(p['transformedInputs'][2:],[1,1])
        self.assertEqual(a['training']['bothMissingCount'],1)
        self.assertAlmostEqual(p['rawPrediction'],a['intercept']+sum(p['contributions']))

    def test_overlap_and_outcome_independent_splits(self):
        rows,_,_=self.synthetic_sessions();f=self.c['cv']['folds'][0]
        before=[[r['selectorEventId'] for r in part] for part in dev.partition(rows,f,self.c)[:4]]
        for r in rows:r['futureReturn']=1e9;r['labelable']=False
        after=[[r['selectorEventId'] for r in part] for part in dev.partition(rows,f,self.c)[:4]]
        self.assertEqual(before,after)
        bad=copy.deepcopy(f);bad['evaluationDates'].append(bad['trainDates'][-1])
        with self.assertRaisesRegex(ValueError,'SESSION_OVERLAP'):dev.partition(rows,bad,self.c)


if __name__=='__main__':
    unittest.main(verbosity=2)
