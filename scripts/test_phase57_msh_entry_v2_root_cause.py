"""Root-cause review integrity and diagnostic semantics; zero model calls."""
import ast
import csv
import gzip
import hashlib
import json
from pathlib import Path
import unittest

from scripts import review_phase57_msh_entry_v2_root_cause as rc


def row(eid, time='09:30', symbol='10000', momentum=-2., pullback=-4.):
    fields = {}
    for name, value in [('directionalMomentum3Pct', momentum), ('directionalPullback6Pct', pullback)]:
        fields[name] = {'status': 'AVAILABLE' if value is not None else 'MISSING', 'value': value}
    return {'selectorEventId': eid, 'symbol': symbol, 'sessionDate': '2024-10-01',
            'symbolSessionId': '2024-10-01|' + symbol, 'decisionTimestamp': '2024-10-01T' + time + ':00+09:00',
            'decisionPrice': 100., 'ridgeScore': 10., 'features': fields}


def label(d30, mfe):
    return {'labelable': True, 'trueMaePct': -d30, 'mfePct': mfe}


class RootCauseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = rc.read(rc.BASE / 'review.json.gz')

    def test_latched_skips_are_not_risk_rejections(self):
        rows = [row('a'), row('b', '10:00'), row('c', '10:30')]
        states = rc.restore_saved_states(rows, ['b'], {'missingSeen': [True, True]})
        self.assertEqual(states, {'a': 'RISK_REJECT', 'b': 'ENTER', 'c': 'STATE_ALREADY_ENTERED'})
        rows.append(row('missing', symbol='20000', momentum=None))
        states = rc.restore_saved_states(rows, ['b'], {'missingSeen': [False, True]})
        self.assertEqual(states['missing'], 'INPUT_UNSCORABLE')
        with self.assertRaisesRegex(ValueError, 'INVALID_SAVED_ENTER'):
            rc.restore_saved_states(rows, ['a', 'b'], {'missingSeen': [True, True]})

    def test_cohorts_preserve_risk_opportunity_overlap_and_unknown(self):
        rows = [row('a'), row('b', symbol='20000'), row('c', symbol='30000')]
        labels = {'a': label(6., 5.), 'b': {'labelable': False, 'reason': 'PROVIDER_GAP'}, 'c': label(.5, .5)}
        counts, details = rc.cohorts(rows, {'a': 'RISK_REJECT', 'b': 'ENTER', 'c': 'ENTER'}, labels)
        self.assertEqual(counts['overlappingFlags']['A_CORRECT_RISK_REJECTION'], 1)
        self.assertEqual(counts['overlappingFlags']['C_FALSE_REJECTION_HIGH_OPPORTUNITY'], 1)
        self.assertEqual(counts['overlappingFlags']['F_CENSORED_UNKNOWN'], 1)
        self.assertEqual(counts['exclusivePartition']['OTHER_LOW_RISK_LOW_OPPORTUNITY_ACCEPT'], 1)
        self.assertIsNone(details[1]['D30'])
        self.assertEqual(sum(counts['exclusivePartition'].values()), 3)

    def test_gate_reproduction_respects_missing_and_zero_baselines(self):
        gate = {'name': 'adverseMeanRatioMax', 'baseline': 2., 'candidate': 1.8, 'limit': .9, 'operator': '<='}
        self.assertEqual(rc.independent_gate_status(gate), 'PASS')
        self.assertEqual(rc.independent_gate_status(gate | {'candidate': 1.9}), 'FAIL')
        self.assertEqual(rc.independent_gate_status(gate | {'candidate': None}), 'INCONCLUSIVE')
        self.assertEqual(rc.independent_gate_status(gate | {'baseline': 0, 'candidate': 0}), 'INCONCLUSIVE')
        self.assertEqual(rc.independent_gate_status(gate | {'name': 'adverseES95RatioMax', 'baseline': 0, 'candidate': 0}), 'PASS')

    def test_precision_composition_has_signed_addition_and_removal(self):
        rows = [row(str(i), symbol=str(10000 + i)) for i in range(5)]
        labels = {str(i): label(1., 6. if i in (0, 1) else 0.) for i in range(5)}
        def metrics(ids):
            o = rc.outcomes(ids, labels)
            return {'enterIds': ids, 'enterCount': len(ids), 'strict30mCount': len(ids),
                    'precision': {k: {'hits': v['count'], 'rate': v['rate']} for k, v in o['opportunity'].items()}}
        x = rc.precision_decomposition(rows, metrics(['0', '1', '2']), metrics(['1', '2', '3', '4']),
             {str(i): 'RISK_REJECT' if i == 0 else 'ENTER' for i in range(5)}, labels)
        g = x['precisionChange']['1']
        self.assertAlmostEqual(g['removalEffect'], -.1666666666666666)
        self.assertAlmostEqual(g['additionEffect'], -.25)
        self.assertAlmostEqual(g['totalChange'], .25 - 2/3)

    def test_single_input_terms_use_saved_scales_without_prediction(self):
        rows = [row('x', pullback=None)]
        artifact = {'coefficients': [.1, -.2, -.3, .04, .05], 'stds': [1., 2., 4.],
                    'means': [0., 0., 0.], 'medians': [-2., -4.]}
        x = rc.input_attribution(rows, {'x': 'ENTER'}, {'x': label(1., 4.)}, artifact)
        terms = {r['input']: r for r in x['marginalTerms'] if r['group'] == 'ALL'}
        self.assertAlmostEqual(terms['directionalMomentum3Pct']['additiveTermDistribution']['mean'], .2)
        self.assertAlmostEqual(terms['directionalPullback6Pct']['additiveTermDistribution']['mean'], .3)
        self.assertAlmostEqual(terms['pullback6Missing']['additiveTermDistribution']['mean'], .05)
        self.assertIsNone(x['opportunityContamination']['ridgeVsPredictedD30'])

    def test_review_code_cannot_import_or_invoke_model_or_cash_runtime(self):
        source = Path(rc.__file__).read_text()
        tree = ast.parse(source)
        allowed = {'collections', 'csv', 'datetime', 'gzip', 'hashlib', 'json', 'math', 'pathlib', 'statistics'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(n.name in allowed for n in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, allowed)
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ''
                self.assertNotIn(name, {'fit', 'predict', 'decide', 'replay', 'eval', 'exec', '__import__', 'dot', 'matmul'})

    def test_saved_evidence_reproduction_and_scope_are_complete(self):
        r = self.review
        self.assertEqual(r['audit']['NONESelectionsVerified'], 24)
        self.assertEqual(r['audit']['savedThresholdEvaluationsVerified'], 96)
        self.assertEqual(r['audit']['savedInnerNumericPredictionRows'], 0)
        self.assertTrue(all(v == 0 for v in r['audit']['counters'].values()))
        self.assertTrue(all(v is False for v in r['audit']['safety'].values()))
        self.assertEqual(len(r['units']), 24)
        for u in r['units']:
            self.assertIsNone(u['selectedThreshold'])
            self.assertEqual(set(u['failureByThreshold']), {'1', '2', '5', '10'})
            self.assertTrue(all(u['failureByThreshold'].values()))
            self.assertEqual(sum(u['stateCounts'].values()), u['candidateRows'])
            self.assertEqual(sum(u['cohorts']['exclusivePartition'].values()), u['candidateRows'])
        d = r['repeatedObservationDiagnostics']['chronological']
        self.assertEqual((d['riskRejections'], d['knownRiskRejections'], d['uniqueKnownRiskRejectedEventIds']), (29, 21, 20))
        self.assertEqual(d['rejectedWinnersByLevel']['5']['total'], 6)
        p = r['portfolioCoverageIndependentProblem']
        self.assertEqual((p['unresolvedCount'], p['lockedPurchaseNotionalJpy']), (1, 335300))
        self.assertIsNone(p['finalEquityJpy']); self.assertIsNone(p['maxDrawdownPct'])
        self.assertFalse(p['replayPerformedThisReview'])

    def test_manifests_and_frozen_sources_remain_unchanged(self):
        scope = rc.read(rc.BASE / 'analysis-scope.json')
        self.assertEqual(rc.sha(rc.CONTRACT), scope['contractSHA'])
        self.assertEqual(rc.sha(rc.DEV / 'manifest.json'), scope['developmentEvidenceSHA'])
        for name, expected in rc.read(rc.DEV / 'manifest.json')['files'].items():
            self.assertEqual(rc.sha(rc.ROOT / name), expected, name)
        self.assertEqual(rc.sha(rc.BASE / 'manifest.json'), (rc.BASE / 'manifest.sha256').read_text().strip())
        for name, expected in rc.read(rc.BASE / 'manifest.json')['files'].items():
            self.assertEqual(rc.sha(rc.ROOT / name), expected, name)
        with gzip.open(rc.BASE / 'candidate-attribution.ndjson.gz', 'rt') as f:
            events = list(map(json.loads, f))
        self.assertEqual(len(events), 10000)
        self.assertTrue(all('predictedD30' not in e and 'rawPrediction' not in e for e in events))
        with (rc.BASE / 'threshold-failure-reproduction.csv').open() as f:
            self.assertEqual(len(list(csv.DictReader(f))), 96)


if __name__ == '__main__':
    unittest.main(verbosity=2)
