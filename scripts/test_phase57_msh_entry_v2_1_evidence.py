"""Saved-evidence verification only: no Project fit or new prediction."""
import collections
import gzip
import hashlib
import json
import math
import unittest

from scripts import phase57_msh_entry_v2_1_development as dev
from scripts import phase57_msh_entry_v2_1_evaluation as ev
from scripts import audit_phase57_msh_entry_v2_1_predevelopment as frozen


def gz(path):
    return json.loads(gzip.decompress(path.read_bytes()))


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=gz(dev.BASE/'run/development.json.gz')
        cls.c=frozen.read(frozen.ROOT/frozen.CONTRACT)
        cls.units=cls.r['chronological']+cls.r['symbolDisjoint']

    def test_source_and_prefit_seals_unchanged(self):
        frozen.audit()
        dev.require_prefit(frozen.read(dev.BASE/'prefit-tests.json'))
        self.assertEqual(self.r['contractSHA'],frozen.FROZEN_SHA)
        self.assertEqual(gz(dev.BASE/'run/development.json.gz'),self.r)

    def test_all_models_serialized_and_correct_symbol_mass(self):
        self.assertEqual(len(self.r['fitRecords']),24)
        for f in self.r['fitRecords']:
            p=dev.BASE/'run/models'/(f['name']+'.json')
            self.assertEqual(frozen.sha(p),f['fileSHA'])
            a=dev.model.load_artifact(p)
            self.assertEqual(a['artifactSHA'],f['artifactSHA'])
            self.assertEqual(len(a['coefficients']),4)
            training=a['training'];weights=training['weights']
            self.assertAlmostEqual(sum(w for _,w in weights),1.)
            by_symbol=collections.defaultdict(float)
            for eid,w in weights:by_symbol[eid.split('|')[-1]]+=w
            self.assertEqual(set(by_symbol),set(training['symbols']))
            for w in by_symbol.values():self.assertAlmostEqual(w,1/len(by_symbol))
            self.assertEqual(len(training['eligibleIds']),training['eligibleRows'])
            self.assertFalse(set(training['eligibleIds'])&set(training['excludedIds']))

    def test_independent_threshold_metric_gate_reproduction(self):
        with gzip.open(frozen.ROOT/frozen.LABELS,'rt') as h:
            labels={r['selectorEventId']:r for r in json.load(h)['events']}
        for r in self.units:
            self.assertEqual(set(r['innerThresholdResults']),{'1','2','5','10'})
            path=dev.BASE/'run/units'/(r['name']+'-calibration.json.gz')
            self.assertEqual(frozen.sha(path),r['calibrationPersistenceSHA'])
            cal=gz(path)
            b=cal['baseline']
            b_ids=set(b['enterIds'])
            winner_ids={str(k):{eid for eid in b_ids if labels[eid]['labelable'] and labels[eid]['mfePct']>=k} for k in ev.LEVELS}
            for t,result in cal['thresholds'].items():
                ids={d['eventId'] for d in result['decisions'] if d['state']=='ENTER'}
                self.assertTrue(ids<=b_ids)
                known=[labels[eid] for eid in ids if labels[eid]['labelable']]
                met=result['metrics']
                self.assertEqual(met['enterCount'],len(ids));self.assertEqual(met['strict30mCount'],len(known))
                if known:
                    d30=[max(0.,-l['trueMaePct']) for l in known]
                    self.assertAlmostEqual(met['meanD30'],sum(d30)/len(d30))
                    tail=sorted(d30,reverse=True)[:math.ceil(.05*len(d30))]
                    self.assertAlmostEqual(met['ES95D30'],sum(tail)/len(tail))
                else:self.assertIsNone(met['meanD30'])
                for k in ev.LEVELS:
                    w=winner_ids[str(k)];ret=met['winnerRetention'][str(k)]
                    self.assertEqual(ret['hits'],len(ids&w));self.assertEqual(ret['baselineWinners'],len(w))
                    self.assertEqual(met['precision'][str(k)]['hits'],sum(l['mfePct']>=k for l in known))
                self.assertEqual(ev.entry_gates(b,met,self.c),result['gates'])
            self.assertEqual(ev.choose_threshold(cal['thresholds']),r['selection'])
            self.assertIsNone(r['selection']['threshold'])

    def test_predictions_durable_and_no_opportunity_input(self):
        count=0
        for r in self.units:
            cal=gz(dev.BASE/'run/units'/(r['name']+'-calibration.json.gz'))
            original={d['eventId']:d for d in cal['candidateIdentities']}
            scores=cal['predictions'];count+=len(scores)
            self.assertEqual(len(scores),r['innerBaseline']['enterCount'])
            for p in scores:
                self.assertEqual(original[p['eventId']]['opportunity']['state'],'ENTER')
                self.assertEqual(len(p['transformedInputs']),4)
                self.assertEqual(len(p['contributions']),4)
                self.assertEqual(p['status'],'SCORED')
                self.assertFalse({'ridgeScore','ridgeRank','expectedClass'}&set(p))
                self.assertEqual(p['predictedD30'],max(0.,p['rawPrediction']))
            self.assertEqual(len(original),len(r['splitIds']['innerCalibration']))
        self.assertEqual(count,825)

    def test_splits_actual_training_do_not_leak(self):
        models={r['name']:r for r in self.r['fitRecords']}
        for r in self.units:
            self.assertFalse(any(r['leakageAudit'].values()))
            ids=models[r['name']+'-inner']['training']['eligibleIds']
            self.assertTrue(set(ids)<=set(r['splitIds']['innerFit']))
            self.assertFalse(set(ids)&set(r['splitIds']['innerCalibration']))
            self.assertFalse(set(ids)&set(r['splitIds']['evaluation']))
            if r['heldGroup'] is not None:
                self.assertTrue(all(frozen.symbol_group(eid.split('|')[-1])!=r['heldGroup'] for eid in ids))
                self.assertTrue(all(frozen.symbol_group(eid.split('|')[-1])==r['heldGroup'] for eid in r['splitIds']['evaluation']))

    def test_none_not_zero_entry_performance_and_no_outer(self):
        self.assertEqual(self.r['projectCounters'],{'fitAttempts':24,'successfulFits':24,'innerFits':24,'outerFits':0,
            'riskPredictionRecords':825,'numericRiskPredictions':825,'thresholdEvaluations':96})
        for s in self.r['streams'].values():
            self.assertFalse(s['complete']);self.assertIsNone(s['metrics'])
            self.assertEqual(s['oofDecisionRows'],0);self.assertEqual(s['duplicates'],0)
            self.assertEqual(len(s['statusLedger']),3000)
            self.assertTrue(all(x['state'] is None for x in s['statusLedger']))
        self.assertIsNone(self.r['coverage']['v21Enter'])
        self.assertEqual(self.r['verdict'],'MSH_ENTRY_LONG_V2_1_DEVELOPMENT_BLOCKED')

    def test_portfolio_unknown_and_cash_not_released(self):
        p=self.r['portfolioBaseline']
        self.assertIsNone(self.r['portfolioV21'])
        self.assertIsNone(p['finalEquityJpy']);self.assertIsNone(p['maxDrawdownPct']);self.assertIsNone(p['totalReturnPct'])
        self.assertEqual(p['trade']['unresolved'],1);self.assertEqual(p['lockedPurchaseNotionalJpy'],335300)
        self.assertEqual(p['unresolvedPositions'][0]['reason'],'MISSING_BEFORE_EXIT')
        self.assertEqual(p['trade']['accepted'],6);self.assertEqual(p['trade']['closed'],5)

    def test_coverage_provider_safety_and_source_scope(self):
        cov=self.r['coverage'];self.assertEqual([cov[k] for k in ['rawScoreQualified','stateConstrainedAnchors','riskLabelable','riskUnlabelable']],[353,277,181,96])
        self.assertEqual(cov['outerV1Anchors'],232);self.assertEqual(cov['outerV1Labelable'],159)
        self.assertFalse(any(self.r['integrity'].values()));self.assertFalse(any(self.r['safety'].values()))
        self.assertEqual(self.r['baselineFull76']['enterCount'],277)

    def test_evidence_manifest(self):
        p=dev.BASE/'manifest.json';manifest=json.loads(p.read_text())
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),(dev.BASE/'manifest.sha256').read_text().strip())
        for file,h in manifest['files'].items():self.assertEqual(frozen.sha(frozen.ROOT/file),h,file)


if __name__=='__main__':
    unittest.main(verbosity=2)
