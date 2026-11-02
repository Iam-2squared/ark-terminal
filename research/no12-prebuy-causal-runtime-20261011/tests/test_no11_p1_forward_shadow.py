"""Synthetic lifecycle tests. No private model execution or performance claim."""
from copy import deepcopy
from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import no11_p1_forward_shadow as f

SESSION = '2026-10-26'
CODE = '7203.T'


def at(clock):
    return SESSION + 'T' + clock + '+09:00'


def fixtures():
    ends = ['2025-05-22', '2025-06-13', '2025-07-01', '2025-07-22', '2025-08-06']
    tests = ['2025-05-30', '2025-06-17', '2025-07-03', '2025-07-24', '2025-08-08']
    split = {'folds': [{'id': i + 1, 'train': ['2024-09-19', ends[i]], 'test': [tests[i]]} for i in range(5)]}
    assets = {'PRIVATE_INPUTS/category_vocabulary.json': {'sha256': 'a' * 64}}
    for suffix in ['preprocessor.pkl', 'calibration.json'] + [h + tail for h in f.HEADS for tail in ('.pkl', '_train_prediction_reference.npy')]:
        assets['PRIVATE_MODELS/P1_F5_' + suffix] = {'sha256': 'b' * 64}
    spec = {'calibration': {5: {'thresholds': {'Q70': 0.6}}}, 'feature': {'P1_numeric': list(range(148)), 'P1_categorical': list(range(15))}, 'corrected': assets}
    return split, spec


class FakeScorer:
    model_kind = 'SYNTHETIC_TEST_NOT_ORIGINAL_MODEL'

    def __init__(self):
        self.policy = f.make_policy(*fixtures(), SESSION)
        self.calls = 0
        self.error = False

    def score(self, numeric, categorical):
        self.calls += 1
        if self.error:
            raise ValueError('TEST_INJECTED_SCORE_FAILURE')
        return {'score': numeric[0], 'testOnly': True}


def selector(t='09:30:00', code=CODE, kind='WATCH_FIRST_SELECTION'):
    event = {'sessionDate': SESSION, 'symbol': code, 'decisionTimestamp': at(t),
             'decisionPrice': 101.5, 'selectorEventId': SESSION + '|' + at(t) + '|' + code,
             'firstWatchIdentity': SESSION + '|' + code, 'watchEventType': kind}
    return {'schemaId': f.SELECTOR_SCHEMA, 'sessionDate': SESSION, 'decisionTimestamp': at(t),
            'selected': [event], 'watchEvents': [event], 'shadowOnly': True,
            'productionReady': False, 'orderTransmission': False}


def feature(t='09:31:00', value=0.5, code=CODE):
    return {'schemaId': f.FEATURE_SCHEMA, 'sessionDate': SESSION, 'symbol': code,
            'watchKey': SESSION + '|' + code, 'barEndJst': at(t), 'evaluatedAtJst': at(t[:-2] + '10'),
            'featureKnownAtJst': at(t[:-2] + '09'), 'stateKnownAtJst': at(t[:-2] + '08'),
            'stateBarEndJst': at(t), 'featureManifestSha256': f.FEATURE_SHA,
            'sourceKind': 'RSS_CUMULATIVE_PROXY', 'numeric': [value] + [None] * 147,
            'categorical': ['ACTUAL_TEST_CATEGORY'] * 15}


class PolicyTests(unittest.TestCase):
    def test_latest_fold_q70_not_new_training(self):
        split, spec = fixtures()
        policy = f.make_policy(split, spec, SESSION)
        self.assertEqual(policy['selectedFold'], 5)
        self.assertEqual(policy['trainingEnd'], '2025-08-06')
        self.assertEqual(policy['threshold'], 0.6)
        self.assertEqual(policy['newFits'], 0)
        self.assertTrue(policy['originalOofMappingUnchanged'])
        self.assertTrue(policy['newForwardPolicy'])
        self.assertFalse(policy['productionReady'])
        self.assertEqual(len(policy['assetSha256']), 9)

    def test_past_or_other_year_is_not_forward_2026(self):
        for session in ['2025-08-08', '2026-10-25', '2027-01-04']:
            with self.assertRaisesRegex(ValueError, 'FORWARD_SESSION_OUTSIDE_2026_POLICY'):
                f.make_policy(*fixtures(), session)

    def test_latest_fold_or_temporal_split_change_blocks(self):
        split, spec = fixtures()
        split['folds'][-1]['train'][-1] = '2025-08-05'
        with self.assertRaisesRegex(ValueError, 'LATEST_SAVED_FOLD_CHANGED'):
            f.make_policy(split, spec, SESSION)
        split, spec = fixtures()
        split['folds'][0]['train'].append('2025-06-01')
        with self.assertRaisesRegex(ValueError, 'SPLIT_NOT_TEMPORAL'):
            f.make_policy(split, spec, SESSION)

    def test_real_public_contract_when_in_repository(self):
        if not (f.REPO / f.BASE / 'SPLIT_PRECOMMIT.json').exists():
            self.skipTest('Full repository source not mounted for local standalone test')
        policy, spec = f.load_policy(f.REPO, SESSION)
        self.assertEqual(policy['selectedFold'], 5)
        self.assertEqual(policy['threshold'], spec['calibration'][5]['thresholds']['Q70'])
        self.assertEqual(policy['featureManifestSha256'], f.FEATURE_SHA)
        self.assertEqual(len(policy['assetSha256']), 9)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.file = Path(self.temp.name) / 'private.sqlite'
        self.scorer = FakeScorer()
        self.engine = f.ForwardP1Session(self.file, self.scorer)

    def tearDown(self):
        self.engine.close()
        self.temp.cleanup()

    def test_selector_register_and_idempotent_retry(self):
        self.assertEqual(self.engine.register_selector(selector())['newWatches'], 1)
        self.assertEqual(self.engine.register_selector(selector())['idempotentRetries'], 1)
        self.assertEqual(self.engine.summary()['watches'], 1)

    def test_first_cross_exact_boundary_and_after_lock_no_rescore(self):
        self.engine.register_selector(selector())
        self.assertEqual(self.engine.evaluate(feature(value=0.599999999999))['status'], 'WAIT')
        crossed = self.engine.evaluate(feature('09:32:00', 0.6))
        self.assertEqual(crossed['status'], 'FIRST_ENTRY_CANDIDATE')
        self.assertFalse(crossed['orderAuthorized'])
        self.assertFalse(crossed['orderTransmission'])
        self.assertEqual(self.engine.evaluate(feature('09:33:00', 0.99))['status'], 'FIRST_ENTRY_ALREADY_LOCKED')
        self.assertEqual(self.scorer.calls, 2)
        self.assertEqual(self.engine.summary()['firstEntryCandidates'], 1)

    def test_same_selector_closed_minute_is_first_eligible_original_grid_row(self):
        self.engine.register_selector(selector())
        result = self.engine.evaluate(feature('09:30:00', 0.6))
        self.assertEqual(result['status'], 'FIRST_ENTRY_CANDIDATE')
        self.assertEqual(self.engine.summary()['firstEntryCandidates'], 1)

    def test_refresh_keeps_original_anchor_and_locked_entry(self):
        self.engine.register_selector(selector())
        intent = self.engine.evaluate(feature(value=0.7))
        refreshed = selector('10:00:00', kind='WATCH_REFRESH')
        refreshed['watchEvents'][0]['decisionPrice'] = 120
        self.engine.register_selector(refreshed)
        w = self.engine.watch_context(CODE)
        self.assertEqual(w['selector_price'], 101.5)
        self.assertEqual(w['selector_minute'], 570)
        self.assertEqual(w['refresh_minutes'], [600])
        self.assertEqual(self.engine.evaluate(feature('10:01:00', 0.99))['status'], 'FIRST_ENTRY_ALREADY_LOCKED')
        replay = self.engine.evaluate(feature(value=0.7))
        self.assertTrue(replay['idempotentReplay'])
        self.assertEqual(replay['candidateId'], intent['candidateId'])
        self.assertEqual(self.scorer.calls, 1)

    def test_restart_preserves_first_candidate_and_retry(self):
        self.engine.register_selector(selector())
        result = self.engine.evaluate(feature(value=0.6))
        self.engine.close()
        self.engine = f.ForwardP1Session(self.file, self.scorer)
        self.assertEqual(self.engine.evaluate(feature(value=0.6))['candidateId'], result['candidateId'])
        self.assertTrue(self.engine.evaluate(feature(value=0.6))['idempotentReplay'])
        self.assertEqual(self.engine.summary()['firstEntryCandidates'], 1)
        self.assertEqual(self.scorer.calls, 1)

    def test_changed_same_bar_or_selector_is_not_a_retry(self):
        self.engine.register_selector(selector())
        altered = selector()
        altered['watchEvents'][0]['decisionPrice'] = 102
        with self.assertRaisesRegex(ValueError, 'SELECTOR_RETRY_CONFLICT'):
            self.engine.register_selector(altered)
        self.engine.evaluate(feature())
        with self.assertRaisesRegex(ValueError, 'FEATURE_RETRY_CONFLICT'):
            self.engine.evaluate(feature(value=0.7))
        self.assertEqual(self.engine.summary()['firstEntryCandidates'], 0)

    def test_future_state_or_features_block(self):
        self.engine.register_selector(selector())
        for field in ['stateKnownAtJst', 'featureKnownAtJst', 'stateBarEndJst']:
            event = feature()
            event[field] = at('10:00:00')
            with self.assertRaisesRegex(ValueError, 'FEATURE_OR_STATE_FROM_FUTURE'):
                self.engine.evaluate(event)
        self.assertEqual(self.scorer.calls, 0)

    def test_before_activation_and_unscheduled_time_block(self):
        self.engine.register_selector(selector())
        with self.assertRaisesRegex(ValueError, 'FEATURE_BEFORE_WATCH_ACTIVATION'):
            self.engine.evaluate(feature('09:29:00'))
        with self.assertRaisesRegex(ValueError, 'NOT_CLOSED_REGULAR_MINUTE'):
            self.engine.evaluate(feature('12:10:00'))
        with self.assertRaisesRegex(ValueError, 'SELECTOR_CLOCK_INVALID'):
            self.engine.register_selector(selector('10:01:00', kind='WATCH_REFRESH'))

    def test_missing_watch_or_missing_refresh_state_blocks(self):
        with self.assertRaisesRegex(ValueError, 'WATCH_NOT_REGISTERED'):
            self.engine.evaluate(feature())
        with self.assertRaisesRegex(ValueError, 'REFRESH_WITHOUT_PERSISTED_WATCH'):
            self.engine.register_selector(selector('10:00:00', kind='WATCH_REFRESH'))

    def test_session_and_feature_schema_are_strict(self):
        self.engine.register_selector(selector())
        bad = feature()
        bad['futureReturn'] = 0.2
        with self.assertRaisesRegex(ValueError, 'FEATURE_CONTRACT_INVALID'):
            self.engine.evaluate(bad)
        bad = feature()
        bad['sessionDate'] = '2026-10-27'
        with self.assertRaisesRegex(ValueError, 'FEATURE_CONTRACT_INVALID'):
            self.engine.evaluate(bad)
        for value in [float('inf'), float('nan'), '0.7', True]:
            bad = feature(value=value)
            with self.assertRaisesRegex(ValueError, 'NUMERIC_FEATURES_INVALID'):
                self.engine.evaluate(bad)

    def test_missing_values_not_zero_filled_or_refitted(self):
        self.engine.register_selector(selector())
        self.assertEqual(self.engine.evaluate(feature())['status'], 'WAIT')
        self.assertEqual(self.scorer.calls, 1)
        bad = feature('09:32:00')
        bad['numeric'] = [None] * 148
        with self.assertRaisesRegex(ValueError, 'NUMERIC_FEATURES_INVALID'):
            self.engine.evaluate(bad)

    def test_failed_inference_rolls_back_and_can_retry(self):
        self.engine.register_selector(selector())
        self.scorer.error = True
        with self.assertRaisesRegex(ValueError, 'TEST_INJECTED'):
            self.engine.evaluate(feature(value=0.7))
        self.assertEqual(self.engine.summary()['evaluations'], 0)
        self.assertEqual(self.engine.summary()['firstEntryCandidates'], 0)
        self.scorer.error = False
        self.assertEqual(self.engine.evaluate(feature(value=0.7))['status'], 'FIRST_ENTRY_CANDIDATE')

    def test_older_unseen_bar_not_inserted_after_newer(self):
        self.engine.register_selector(selector())
        self.engine.evaluate(feature('09:33:00', 0.5))
        with self.assertRaisesRegex(ValueError, 'FEATURE_BAR_OUT_OF_ORDER'):
            self.engine.evaluate(feature('09:32:00', 0.8))

    def test_independent_symbols_each_lock_once(self):
        self.engine.register_selector(selector())
        self.engine.register_selector(selector(code='6758.T'))
        self.engine.evaluate(feature(value=0.8))
        self.engine.evaluate(feature(value=0.7, code='6758.T'))
        self.assertEqual(self.engine.summary()['firstEntryCandidates'], 2)
        self.assertEqual(self.engine.summary()['orders'], 0)

    def test_atomic_selector_batch_invalid_event_rolls_back(self):
        valid = selector()
        invalid = selector(code='6758.T', kind='WATCH_REFRESH')
        valid['watchEvents'] += invalid['watchEvents']
        valid['selected'] += invalid['selected']
        with self.assertRaisesRegex(ValueError, 'REFRESH_WITHOUT_PERSISTED_WATCH'):
            self.engine.register_selector(valid)
        self.assertEqual(self.engine.summary()['watches'], 0)

    def test_two_process_handles_retry_one_candidate(self):
        self.engine.register_selector(selector())
        other = f.ForwardP1Session(self.file, self.scorer)
        try:
            first = self.engine.evaluate(feature(value=0.6))
            second = other.evaluate(feature(value=0.6))
            self.assertEqual(first['candidateId'], second['candidateId'])
            self.assertTrue(second['idempotentReplay'])
            self.assertEqual(other.summary()['firstEntryCandidates'], 1)
        finally:
            other.close()

    def test_invalid_model_score_rolls_back(self):
        self.engine.register_selector(selector())
        original = self.scorer.score
        self.scorer.score = lambda *args: {'score': float('nan')}
        with self.assertRaisesRegex(ValueError, 'MODEL_SCORE_INVALID'):
            self.engine.evaluate(feature())
        self.assertEqual(self.engine.summary()['evaluations'], 0)
        self.scorer.score = original

    def test_policy_mismatch_does_not_reuse_existing_day_state(self):
        other = FakeScorer()
        other.policy['threshold'] = 0.7
        other.policy['policySha256'] = f.digest({k: v for k, v in other.policy.items() if k != 'policySha256'})
        with self.assertRaisesRegex(ValueError, 'EXISTING_SESSION_POLICY_MISMATCH'):
            f.ForwardP1Session(self.file, other)


if __name__ == '__main__':
    unittest.main(verbosity=2)
