"""Synthetic CV/comparator pre-fit tests; no Project row fit or prediction."""
import copy
import json
from pathlib import Path
import unittest
from scripts import phase57_msh_entry_v2_development as dev
from scripts import audit_phase57_msh_entry_v2_predevelopment as freeze
from scripts.phase57_msh_entry_v2_evaluation import entry_metrics
from predict.research import phase57_msh_entry_long_v2_d30 as m


def rows_for_contract(c):
    rows=[]
    for date in c['universe']['sessions']:
        for i in range(15):
            symbol=str(10000+i)
            rows.append({'selectorEventId':date+'|'+symbol,'symbolSessionId':date+'|'+symbol,
                         'symbol':symbol,'sessionDate':date,'decisionTimestamp':date+'T09:30:00+09:00','decisionPrice':100.})
    return rows


class DevelopmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=json.loads((freeze.ROOT/freeze.CONTRACT).read_text())
        cls.rows=rows_for_contract(cls.c)

    def test_chronological_inner_outer_and_purge(self):
        for fold in self.c['cv']['folds']:
            fit,cal,refit,evaluate,audit=dev.partition(self.rows,fold,self.c)
            self.assertLess(max(m.timestamp(r['decisionTimestamp'])+1800 for r in fit),min(m.timestamp(r['decisionTimestamp']) for r in cal))
            self.assertLess(max(m.timestamp(r['decisionTimestamp'])+1800 for r in refit),min(m.timestamp(r['decisionTimestamp']) for r in evaluate))
            self.assertEqual(set(r['sessionDate'] for r in refit),set(fold['trainDates']))
            self.assertEqual(sum(audit.values()),0)

    def test_whole_symbol_exclusion_including_threshold_calibration(self):
        for group in range(5):
            for fold in self.c['cv']['folds']:
                fit,cal,refit,evaluate,_=dev.partition(self.rows,fold,self.c,group)
                trained={r['symbol'] for r in fit+cal+refit}
                held={r['symbol'] for r in evaluate}
                self.assertFalse(trained & held)
                self.assertTrue(all(freeze.symbol_group(s)==group for s in held))

    def test_split_independent_of_label_and_price_outcomes(self):
        rows=copy.deepcopy(self.rows)
        before=[[r['selectorEventId'] for r in part] for part in dev.partition(rows,self.c['cv']['folds'][0],self.c)[:4]]
        for r in rows:r['futureMAE']=-999;r['futurePnl']=999999
        after=[[r['selectorEventId'] for r in part] for part in dev.partition(rows,self.c['cv']['folds'][0],self.c)[:4]]
        self.assertEqual(before,after)

    def test_evaluation_overlap_is_rejected(self):
        fold=copy.deepcopy(self.c['cv']['folds'][0])
        fold['evaluationDates'].append(fold['trainDates'][-1])
        with self.assertRaisesRegex(m.IntegrityError,'SESSION_OVERLAP'):
            dev.partition(self.rows,fold,self.c)

    def test_no_threshold_means_no_outer_refit_prediction_or_fake_skip(self):
        labels={r['selectorEventId']:{'labelable':True,'trueMaePct':-2.,'mfePct':6.,'barCount':6} for r in self.rows}
        baseline={r['selectorEventId']:{'eventId':r['selectorEventId'],'state':'ENTER'} for r in self.rows}
        calls=[]
        def score(fit,evaluate,name):
            calls.append(name)
            return [{'eventId':r['selectorEventId'],'symbol':r['symbol'],'sessionDate':r['sessionDate'],
                     'decisionTimestamp':r['decisionTimestamp'],'status':'SCORED','rawPrediction':100.,'predictedD30':100.} for r in evaluate]
        result=dev.run_replica(self.rows,baseline,labels,None,self.c,self.c['cv']['folds'][0],None,score)
        self.assertIsNone(result['selection']['threshold'])
        self.assertEqual(calls,['chrono-1-inner'])
        self.assertEqual(result['outerPredictions'],[])
        self.assertEqual(result['outerDecisions'],[])
        self.assertEqual(set(result['innerThresholdResults']),{'1','2','5','10'})

    def test_unknown_labels_excluded_from_metric_not_from_entry_count(self):
        rows=self.rows[:3]
        labels={r['selectorEventId']:{'labelable':True,'trueMaePct':-2.,'mfePct':6.,'barCount':6} for r in rows}
        labels[rows[0]['selectorEventId']]={'labelable':False,'reason':'PROVIDER_GAP'}
        decisions=[{'eventId':r['selectorEventId'],'state':'ENTER'} for r in rows]
        x=entry_metrics(rows,decisions,labels,[rows[0]['sessionDate']])
        self.assertEqual(x['enterCount'],3)
        self.assertEqual(x['strict30mCount'],2)
        self.assertEqual(x['meanD30'],2.)
        self.assertEqual(x['precision']['5']['n'],2)

    def test_pre_fit_receipt_cannot_be_reused_after_code_change(self):
        r={'status':'PASS','contractSHA':m.CONTRACT_SHA,'syntheticOnly':True,
           'implementationPins':{p:'0'*64 for p in dev.MODEL_SOURCES}}
        with self.assertRaisesRegex(m.IntegrityError,'PREFIT_CODE_CHANGED'):
            dev.require_prefit(r)

    def test_unknown_portfolio_cannot_pass_via_closed_trades(self):
        base={'status':'FULL_PORTFOLIO_UNPRICED_EXPOSURE','trade':{'profitFactor':999.}}
        gates=dev.portfolio_gates(base,None,self.c)
        self.assertTrue(all(g['status']=='INCONCLUSIVE' for g in gates))

    def test_score_free_weighting_preserves_full_cash_ledger(self):
        event={'selectorEventId':'SYNTHETIC','symbol':'10000','sessionDate':'2024-10-01',
               'decisionTimestamp':'2024-10-01T09:30:00+09:00','decisionPrice':100.,'direction':'LONG',
               'expectedBars':sum(v>570 for v in dev.ledger.calendar('2024-10-01')),'future':[]}
        for i,close in enumerate([1.,.8,.6],1):
            end=f'2024-10-01T09:{30+5*i:02}:00+09:00'
            event['future'].append({'slot':i,'end':end,'minutes':5*i,'missing':False,'o':1.,'h':1.1,'l':0.,'c':close})
        cash=json.loads((freeze.ROOT/dev.ledger.CONTRACT).read_text())
        old=dev.ledger.weights([{'eventId':'SYNTHETIC','symbol':'10000','timestamp':event['decisionTimestamp'],'score':2.5}])['EQUAL_MAX3']
        new=dev.score_free_weights([event])
        a=dev.ledger.replay([event],[event['sessionDate']],'EQUAL_MAX3',old,cash)
        b=dev.ledger.replay([event],[event['sessionDate']],'EQUAL_MAX3',new,cash)
        self.assertEqual(a,b)
        self.assertEqual(a['status'],'COMPLETE_REFERENCE_REPLAY')
        self.assertEqual(a['trade']['accepted'],1)
        self.assertTrue(a['ledgerAudit']['nonnegativeCash'])


if __name__=='__main__':
    unittest.main(verbosity=2)
