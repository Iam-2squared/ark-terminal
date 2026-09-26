"""Synthetic prefit checks and saved-only diagnostic audit: no Project refits."""
import copy
import json
import unittest
from scripts import phase57_entry_v23_fast_fail as d
from scripts.test_phase57_entry_v22_fast_fail import synthetic
from scripts import test_phase57_entry_v22_fast_fail as oldtests
h=d.h


def sample():
    rows,_=synthetic()
    return [h.extract_inputs(r) for r in rows],{r['selectorEventId']:int(i>=4) for i,r in enumerate(rows)}


class SyntheticTests(unittest.TestCase):
    def test_protocol(self):
        c=d.audit()
        self.assertEqual(c['label']['primaryLabelCount'],1)
        self.assertEqual(c['features']['order'],d.ORDER)
        self.assertFalse(any(c['safety'].values()))

    def test_label_boundary_and_censor(self):
        s={'labelable':True,'barCount':6,'trueMaePct':-2.}
        self.assertEqual(d.good_label(.01,s),1)
        self.assertEqual(d.good_label(0.,s),0)
        self.assertEqual(d.good_label(.01,s|{'trueMaePct':-2.00001}),0)
        self.assertIsNone(d.good_label(None,s))
        self.assertIsNone(d.good_label(-99,{'labelable':False}))
        with self.assertRaises(h.IntegrityError):d.good_label(.1,s|{'trueMaePct':1.})
        with self.assertRaises(h.IntegrityError):d.good_label(.1,s|{'barCount':5})

    def test_projection_leakage_and_long_only(self):
        rows,_=synthetic();a=h.extract_inputs(rows[0])
        rows[0].update(label=99,futureMAE=-99,exitResult=99,portfolioPnL=999)
        self.assertEqual(h.extract_inputs(rows[0]),a)
        with self.assertRaises(h.IntegrityError):h.validate_envelope(a|{'label':1})
        rows[0]['direction']='SHORT'
        with self.assertRaises(h.IntegrityError):h.extract_inputs(rows[0])

    def test_weights_and_median(self):
        rows=[{'symbol':'A','sessionDate':'1'},{'symbol':'A','sessionDate':'1'},{'symbol':'A','sessionDate':'2'},{'symbol':'B','sessionDate':'1'}]
        self.assertEqual(h.symbol_weights(rows).tolist(),[.125,.125,.25,.5])
        self.assertEqual(h.weighted_median([None,3.,1.,2.],[.5,.1,.1,.3],list('abcd')),2.)

    def test_logistic_null_objective(self):
        rows,y=sample();a=d.fit(rows,y)
        self.assertAlmostEqual(a['intercept'],0.)
        self.assertTrue(all(abs(v)<1e-10 for v in a['coefficients']))
        self.assertEqual(a['lambda'],1.)
        self.assertAlmostEqual(a['training']['objective'],__import__('math').log(2))
        self.assertTrue(all(p['state']=='SKIP_THIS_DECISION' for p in d.predict(a,rows)))

    def test_logistic_signal_gradient_and_determinism(self):
        rows,_=sample();y={r['eventId']:int(r['raw'][0]>=2) for r in rows}
        a=d.fit(rows,y)
        self.assertTrue(all(v>0 for v in a['coefficients'][:3]))
        self.assertLessEqual(a['training']['gradientInf'],1e-10)
        self.assertEqual(a,d.fit(rows[::-1],y))
        self.assertEqual(a,json.loads(h.canonical(a)))
        b=copy.deepcopy(a);b['lambda']=2.
        with self.assertRaises(h.IntegrityError):d.validate_model(b)

    def test_no_evaluation_label_access_and_censor(self):
        rows,y=sample();y[rows[0]['eventId']]=None
        a=d.fit(rows,y);y['EVAL']=999
        self.assertEqual(a,d.fit(rows,y))
        self.assertEqual(a['training']['labelable'],7)
        self.assertNotIn(rows[0]['eventId'],a['training']['ids'])
        with self.assertRaises(h.FitError):d.fit(rows,{r['eventId']:0 for r in rows})

    def test_missing_is_not_zero_and_unseen_unknown(self):
        rows,y=sample();a=d.fit(rows,y)
        rows[0]['raw'][1]=None;rows[0]['missing'][0]=1
        p={p['eventId']:p for p in d.predict(a,rows)}[rows[0]['eventId']]
        self.assertEqual(p['state'],'UNKNOWN');self.assertIsNone(p['pGood'])
        b=d.fit(rows,y)
        self.assertEqual(b['training']['missingCounts'],[1,0])
        self.assertEqual(b['missingSeen'],[True,False])

    def test_causal_state_and_no_reentry(self):
        rows,y=sample();a=d.fit(rows,y)
        a['intercept']=1.;a.pop('artifactSHA');a['artifactSHA']=h.digest(a)
        r=rows[0];r2=copy.deepcopy(r);r2['eventId']='LATER';r2['decisionTimestamp']=r['decisionTimestamp'].replace('09:30','09:35')
        ps=d.predict(a,[r2,r]);self.assertEqual([p['state'] for p in ps],['ENTER','SKIP_THIS_DECISION'])
        self.assertEqual(ps[1]['reason'],'ALREADY_ENTERED')
        with self.assertRaises(h.IntegrityError):d.predict(a,[r,r])

    def test_chronology_symbol_disjoint(self):
        c=d.audit();rows=[{'sessionDate':date,'symbol':str(s),'symbolSessionId':date+'|'+str(s)} for date in c['universe']['sessions'] for s in range(10000,10020)]
        for i in range(4):
            a,b=d.old.partition(rows,c,i)
            self.assertLess(max(r['sessionDate'] for r in a),min(r['sessionDate'] for r in b))
        for g in range(5):
            a,b=d.old.partition(rows,c,3,g)
            self.assertFalse({r['symbol'] for r in a}&{r['symbol'] for r in b})

    def test_auc_ties_ap_and_base_rate(self):
        rows=[{'symbol':str(i%2),'sessionDate':'x','unit':'u','pGood':.5,'good':i%2,'baseRate':.5,'state':'ENTER'} for i in range(8)]
        r=d.discrimination(rows)
        self.assertEqual(r['auc'],.5);self.assertEqual(r['averagePrecision'],.5)
        self.assertEqual(r['brierSkill'],0.);self.assertEqual(r['logLossSkill'],0.)
        for p in rows:p['pGood']=.9 if p['good'] else .1
        self.assertEqual(d.discrimination(rows)['auc'],1.)

    def test_preservation_own_window_and_unknown_bounds(self):
        rows=[{'symbol':'A','sessionDate':'x','eventId':'a','state':'SKIP_THIS_DECISION','v1Anchor':True,'MFE':5.},
              {'symbol':'A','sessionDate':'x','eventId':'b','state':'ENTER','v1Anchor':False,'MFE':None}]
        p=d.preservation(rows)['5'];self.assertEqual((p['lower'],p['upper']),(0.,1.))
        rows[1]['MFE']=5.;p=d.preservation(rows)['5']
        self.assertEqual(p['lower'],1.);self.assertEqual(p['exactAnchorEntries'],0)


@unittest.skipUnless((d.BASE/'result.json').exists(),'Project diagnostic not run')
class SavedEvidenceTests(unittest.TestCase):
    assert_saved_metrics=oldtests.SavedEvidenceTests.assert_saved_metrics
    @classmethod
    def setUpClass(cls):
        cls.c=d.audit();cls.r=d.read(str((d.BASE/'result.json').relative_to(d.ROOT)))
        cls.p=d.read(str((d.BASE/'predictions.json.gz').relative_to(d.ROOT)))
        cls.models=d.read(str((d.BASE/'models.json.gz').relative_to(d.ROOT)))

    def test_models_hash_leakage_weights(self):
        for item in self.models:
            a=item['model'];d.validate_model(a)
            ps=[p for p in self.p if p['unit']==item['unit']]
            self.assertFalse(set(a['training']['ids'])&{p['eventId'] for p in ps})
            self.assertFalse(set(a['training']['sessions'])&{p['sessionDate'] for p in ps})
            self.assertLess(max(a['training']['sessions']),min(p['sessionDate'] for p in ps))
            self.assertAlmostEqual(a['training']['largestSymbolWeight'],1/len(a['training']['symbols']))
            self.assertAlmostEqual(a['training']['weightSum'],1.)
            if item['unit'].startswith('symbol'):
                self.assertFalse(set(a['training']['symbols'])&{p['symbol'] for p in ps})
            chosen=set()
            for p in sorted(ps,key=h.sort_key):
                key=(p['symbol'],p['sessionDate'])
                if p['state']=='ENTER':
                    self.assertNotIn(key,chosen);chosen.add(key)
                    self.assertGreater(p['pGood'],a['probabilityThreshold'])

    def test_metrics_verdict_no_new_predictions(self):
        pooled={s:d.summary([p for p in self.p if p['scope']==s]) for s in ['chronological','symbol']}
        self.assert_saved_metrics(pooled,self.r['pooled'])
        reduced=d.discrimination([p for p in self.p if p['scope']=='chronological' and p['symbol'] not in self.r['top2Diagnostic']['symbols']])
        verdict,gates=d.gates(self.r['units'],pooled,reduced,self.c)
        self.assertEqual(verdict,self.r['verdict']);self.assert_saved_metrics(gates,self.r['gates'])
        for s in pooled:
            ps=[p for p in self.p if p['scope']==s]
            self.assertEqual(len(ps),len({p['eventId'] for p in ps}))

    def test_joint_labels(self):
        ledger=d.read(str((d.BASE/'label-ledger.json.gz').relative_to(d.ROOT)))
        strict={r['selectorEventId']:r for r in d.read(d.frozen.LABELS)['events']}
        self.assertEqual(len(ledger),3800)
        for r in ledger:self.assertEqual(r['good'],d.good_label(r['netReferenceReturn'],strict[r['eventId']]))
        lookup={r['eventId']:r['good'] for r in ledger}
        for p in self.p:self.assertEqual(p['good'],lookup[p['eventId']])

    def test_budget_safety_and_prefit(self):
        self.assertEqual(self.r['integrity']['fitAttempts'],9)
        self.assertEqual(self.r['integrity']['successfulFits'],len(self.models))
        for k in ['fresh','entryOos','exitOos','prospective','jQuants','yahoo','otherPriceProvider','short','priorModelRefits','thresholdSearch','modelSearch','newPortfolioRuns','fullDevelopment']:
            self.assertEqual(self.r['integrity'][k],0)
        self.assertFalse(any(self.r['safety'].values()))
        self.assertIsNone(self.r['portfolio']['finalEquity'])
        receipt=d.read(str((d.BASE/'prefit.json').relative_to(d.ROOT)))
        for p,sha in receipt['sourcePins'].items():self.assertEqual(d.file_sha(p),sha)

if __name__=='__main__':unittest.main()
