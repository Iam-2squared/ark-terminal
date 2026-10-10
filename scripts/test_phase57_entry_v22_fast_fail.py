"""Synthetic math/leakage tests plus saved-evidence audit, never Project refits."""
import copy
import json
import math
import unittest

from predict.research import phase57_entry_v22_quality_probe as m
from scripts import phase57_entry_v22_fast_fail as d


def synthetic():
    rows, labels = [], {}
    for i in range(8):
        v = float(i % 4)
        date = '2024-09-' + str(17 + i % 4)
        symbol = str(10000 + i//4)
        eid = 'SYNTHETIC-' + str(i)
        r = {'selectorEventId': eid, 'symbol': symbol, 'symbolSessionId': date+'|'+symbol,
             'sessionDate': date, 'decisionTimestamp': date+'T09:30:00+09:00',
             'decisionPrice': 100., 'ridgeScore': v, 'direction': 'LONG',
             'features': {name: {'status': 'AVAILABLE', 'value': v}
                          for name in m.FEATURE_ORDER[1:3]}}
        rows.append(r)
        labels[eid] = -2 + (v - 1.5)/math.sqrt(1.25)
    return rows, labels


class SyntheticTests(unittest.TestCase):
    def test_protocol_sources_and_safety(self):
        c = d.audit_protocol()
        self.assertEqual(c['target']['count'], 1)
        self.assertEqual(c['cv']['maximumProjectFits'], 9)
        self.assertFalse(any(c['safety'].values()))
        self.assertEqual(c['features']['order'], m.FEATURE_ORDER)

    def test_signed_target_cost_once_and_censor(self):
        self.assertEqual(m.target_from_exit({'status': 'EXIT_REFERENCE', 'grossPct': 0., 'netPct': -.05}), -.05)
        self.assertEqual(m.target_from_exit({'status': 'EXIT_REFERENCE', 'grossPct': -2., 'netPct': -2.05}), -2.05)
        self.assertIsNone(m.target_from_exit({'status': 'CENSORED', 'reason': 'MISSING'}))
        with self.assertRaises(m.IntegrityError):
            m.target_from_exit({'status': 'CENSORED', 'netPct': 0})
        with self.assertRaises(m.IntegrityError):
            m.target_from_exit({'status': 'EXIT_REFERENCE', 'grossPct': 1., 'netPct': 1.})

    def test_fixed_exit_connection_not_d30(self):
        event = {'expectedBars': 12, 'future': [
            {'slot': i+1, 'missing': False, 'c': c, 'end': str(i), 'minutes': 5*(i+1)}
            for i, c in enumerate([1., .5, .2])]}
        out = d.exit_outcome(event)
        self.assertEqual(out['reason'], 'TWO_LOWER_COMPLETED_CLOSES')
        self.assertAlmostEqual(m.target_from_exit(out), .15)
        event['future'][1]['missing'] = True
        self.assertIsNone(m.target_from_exit(d.exit_outcome(event)))

    def test_projection_no_future_or_symbol_predictor(self):
        rows, _ = synthetic()
        a = m.extract_inputs(rows[0])
        rows[0].update(label={'netPct': 9999}, futureMFE=9999, futureMAE=-9999,
                       exitResult=9999, portfolioPnl=9999, ridgeRank=9999)
        self.assertEqual(a, m.extract_inputs(rows[0]))
        a['actualQ'] = 10.
        with self.assertRaises(m.IntegrityError):
            m.validate_envelope(a)

    def test_short_rejected(self):
        rows, _ = synthetic(); rows[0]['direction'] = 'SHORT'
        with self.assertRaises(m.IntegrityError):
            m.extract_inputs(rows[0])

    def test_missing_is_distinct_from_observed_zero(self):
        rows, _ = synthetic()
        a = m.extract_inputs(rows[0])
        self.assertEqual(a['raw'], [0., 0., 0.])
        self.assertEqual(a['missing'], [0, 0])
        rows[0]['features'][m.FEATURE_ORDER[1]] = {'status': 'MISSING', 'value': None}
        a = m.extract_inputs(rows[0])
        self.assertEqual(a['raw'], [0., None, 0.])
        self.assertEqual(a['missing'], [1, 0])
        rows[0]['features'][m.FEATURE_ORDER[1]]['value'] = 0.
        with self.assertRaises(m.IntegrityError):
            m.extract_inputs(rows[0])

    def test_weighted_median_boundary_and_training_weights(self):
        self.assertEqual(m.weighted_median([None, 3., 1., 2.], [.5, .1, .1, .3], ['a','b','c','d']), 2.)
        rows = [{'symbol': 'A', 'sessionDate': '1'}, {'symbol': 'A', 'sessionDate': '1'},
                {'symbol': 'A', 'sessionDate': '2'}, {'symbol': 'B', 'sessionDate': '1'}]
        self.assertEqual(m.symbol_weights(rows).tolist(), [.125, .125, .25, .5])

    def test_ridge_objective_unpenalized_intercept_and_signed_readout(self):
        rows, labels = synthetic(); env = [m.extract_inputs(r) for r in rows]
        a = m.fit(env, labels)
        self.assertAlmostEqual(a['intercept'], -2.)
        for b in a['coefficients'][:3]: self.assertAlmostEqual(b, .25)
        self.assertEqual(a['coefficients'][3:], [0., 0.])
        self.assertTrue(all(p['predictedQ'] < 0 for p in m.predict(a, env)))
        self.assertEqual(a['lambda'], 1.)

    def test_fit_is_deterministic_and_serializes(self):
        rows, labels = synthetic(); env = [m.extract_inputs(r) for r in rows]
        a = m.fit(env, labels); b = m.fit(list(reversed(env)), labels)
        self.assertEqual(a, b)
        self.assertEqual(m.roundtrip(a), a)
        self.assertEqual(m.predict(a, env), m.predict(m.roundtrip(a), env))
        corrupt = copy.deepcopy(a); corrupt['coefficients'][0] += 1
        with self.assertRaises(m.IntegrityError): m.validate_artifact(corrupt)

    def test_label_censor_excluded_not_zero_and_evaluation_labels_unused(self):
        rows, labels = synthetic(); env = [m.extract_inputs(r) for r in rows]
        labels[env[0]['eventId']] = None
        labels['UNSEEN_EVAL_LABEL'] = 1e9
        a = m.fit(env, labels)
        self.assertEqual(a['training']['labelableRows'], 7)
        self.assertEqual(a['training']['excludedIds'], [env[0]['eventId']])
        labels['UNSEEN_EVAL_LABEL'] = -1e9
        self.assertEqual(a, m.fit(env, labels))
        self.assertEqual(len(m.predict(a, env)), 8)

    def test_unseen_missing_state_unknown_not_zero_or_skip(self):
        rows, labels = synthetic(); env = [m.extract_inputs(r) for r in rows]
        a = m.fit(env, labels)
        env[0]['raw'][1] = None; env[0]['missing'][0] = 1
        p = m.predict(a, env)[0]
        self.assertEqual(p['status'], 'UNSUPPORTED_MISSING_STATE')
        self.assertIsNone(p['predictedQ']); self.assertIsNone(p['positiveScoreBand'])

    def test_chronology_and_hash_group_separation(self):
        c = d.read(d.PROTOCOL)
        rows = []
        for date in c['universe']['sessions']:
            for symbol in ['11110', '22220', '33330', '44440', '55550', '66660']:
                rows.append({'sessionDate': date, 'symbol': symbol, 'symbolSessionId': date+'|'+symbol})
        for i in range(4):
            a, b = d.partition(rows, c, i)
            self.assertLess(max(r['sessionDate'] for r in a), min(r['sessionDate'] for r in b))
        for g in range(5):
            a, b = d.partition(rows, c, 3, g)
            self.assertFalse({r['symbol'] for r in a} & {r['symbol'] for r in b})

    def test_rank_ties_and_spearman(self):
        self.assertEqual(d.average_ranks([2., 1., 1., 3.]).tolist(), [3., 1.5, 1.5, 4.])
        rows = [{'predictedQ': float(i), 'actualQ': -float(i), 'symbol': str(i%2)} for i in range(8)]
        self.assertAlmostEqual(d.spearman(rows), -1.)

    def test_gate_no_epsilon_rescue_or_inconclusive_for_failure(self):
        self.assertEqual(d.gate('x', 0., '>', 0.)['status'], 'FAIL')
        self.assertEqual(d.gate('x', None, '>', 0.)['status'], 'INCONCLUSIVE')
        self.assertEqual(d.gate('x', .8999999, '>=', .9)['status'], 'FAIL')

    def test_natural_breakeven_boundary(self):
        rows, labels = synthetic(); env = [m.extract_inputs(r) for r in rows]
        a = m.fit(env, {k: 0. for k in labels})
        self.assertTrue(all(p['predictedQ'] == 0 and p['positiveScoreBand'] is False for p in m.predict(a, env)))


@unittest.skipUnless((d.BASE/'result.json').exists(), 'Saved Project screen not run yet')
class SavedEvidenceTests(unittest.TestCase):
    def assert_saved_metrics(self, actual, expected):
        """CPU/BLAS reductions may differ at roundoff; identities/gates stay exact."""
        if isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for key in expected:
                self.assert_saved_metrics(actual[key], expected[key])
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for a, b in zip(actual, expected):
                self.assert_saved_metrics(a, b)
        elif type(expected) is float:
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12),
                            f'Numeric audit mismatch: {actual!r} != {expected!r}')
        else:
            self.assertEqual(actual, expected)

    @classmethod
    def setUpClass(cls):
        cls.c = d.audit_protocol()
        cls.r = d.read(str((d.BASE/'result.json').relative_to(d.ROOT)))
        cls.p = d.read(str((d.BASE/'predictions.json.gz').relative_to(d.ROOT)))
        cls.models = d.read(str((d.BASE/'models.json.gz').relative_to(d.ROOT)))

    def test_budget_and_scopes(self):
        self.assertEqual(self.r['integrity']['projectFitAttempts'], 9)
        self.assertLessEqual(len(self.models), 9)
        self.assertEqual(self.r['integrity']['thresholdSearch'], 0)
        for scope in ['chronological', 'symbolDisjointLastWindow']:
            rows = [r for r in self.p if r['scope'] == scope]
            self.assertEqual(len(rows), len({r['eventId'] for r in rows}))

    def test_saved_models_leakage_weights_and_contributions(self):
        for item in self.models:
            a = item['artifact']; m.validate_artifact(a)
            rows = [p for p in self.p if p['unit'] == item['unit']]
            self.assertFalse(set(a['training']['eligibleIds']) & {p['eventId'] for p in rows})
            self.assertFalse(set(a['training']['sessions']) & {p['sessionDate'] for p in rows})
            self.assertAlmostEqual(a['training']['weightSum'], 1.)
            self.assertAlmostEqual(a['training']['largestSymbolWeight'], 1/len(a['training']['symbols']))
            if item['unit'].startswith('symbol-'):
                self.assertFalse(set(a['training']['symbols']) & {p['symbol'] for p in rows})
            for p in rows:
                if p['status'] == 'SCORED':
                    self.assertAlmostEqual(p['predictedQ'], a['intercept']+math.fsum(p['contributions']))
                    self.assertEqual(p['positiveScoreBand'], p['predictedQ'] > 0.)

    def test_saved_metrics_and_verdict_recompute_no_predictions(self):
        cr = [r for r in self.p if r['scope'] == 'chronological']
        sy = [r for r in self.p if r['scope'] == 'symbolDisjointLastWindow']
        a, b = d.regression_metrics(cr), d.regression_metrics(sy)
        reduced = d.regression_metrics([r for r in cr if r['symbol'] not in self.r['top2RemovalDiagnostic']['symbols']])
        bands = d.coexistence(cr)
        self.assert_saved_metrics(a, self.r['pooled']['chronological'])
        self.assert_saved_metrics(b, self.r['pooled']['symbolDisjointLastWindow'])
        verdict, gates = d.decide(self.r['units'], a, b, reduced, bands, self.c)
        self.assertEqual(verdict, self.r['verdict'])
        self.assert_saved_metrics(gates, self.r['gates'])
        self.assertEqual([g['status'] for g in gates], [g['status'] for g in self.r['gates']])

    def test_censored_labels_no_zero_fabrication(self):
        ledger = d.read(str((d.BASE/'target-ledger.json.gz').relative_to(d.ROOT)))
        self.assertEqual(len(ledger), 3800)
        for r in ledger:
            self.assertEqual(r['target'], m.target_from_exit(r['exit']))
        labels = {r['eventId']: r['target'] for r in ledger}
        for p in self.p: self.assertEqual(p['actualQ'], labels[p['eventId']])

    def test_frozen_and_no_fresh_or_execution(self):
        for key in ['fresh','entryOos','exitOos','prospective','jQuantsRequests','yahooRequests',
                    'otherPriceRequests','shortEvaluation','fullDevelopmentRuns','newPortfolioRuns',
                    'prototypeRetuning','newFeatures','extraTargets']:
            self.assertEqual(self.r['integrity'][key], 0)
        self.assertFalse(any(self.r['safety'].values()))
        self.assertIsNone(self.r['portfolio']['finalEquity'])
        self.assertIsNone(self.r['portfolio']['maxDrawdown'])


if __name__ == '__main__':
    unittest.main()
