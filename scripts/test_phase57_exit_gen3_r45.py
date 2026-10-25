"""Synthetic R45 causality, authority, label, support and launch-gate tests."""
from copy import deepcopy
import ast
import inspect
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np

from scripts import phase57_exit_gen3_runtime_r45 as rt
from scripts.phase57_exit_gen3_facts_r45 import FactEncoder, price_facts, calendar_features, SIGNALS
from scripts.phase57_exit_gen3_labels_r45 import utility_labels, reference_plan, index_rows, HEADS
from scripts.phase57_exit_gen3_data_r45 import support_slices
from scripts.phase57_exit_gen3_runner_r45 import replay_candidate, decision_facts
from scripts.phase57_exit_gen3_preflight_r45 import validate_launch, BRANCH, REPO, CI_PATH, FINITE_PATH, MARKER, R35_ARTIFACT, R35_RUN, R35_DIGEST
from scripts.phase57_exit_execution_contract_v1 import continuous_minutes

DAY = '2025-07-03'
P = rt.load_protocol()
SCHEDULE = continuous_minutes(DAY)


def envelope(now=550, **updates):
    values = dict.fromkeys(P['features']['decisionFactFields'])
    values.update(currentReturnPct=0., certifiedMfePct=2., certifiedGivebackPp=1.,
                  barsHeld=20, timeSincePeak=5, weakRun=3, signalTrueN=0,
                  signalFalseN=2, signalUnknownN=4, signalLossN=0, signalRecoveryN=0,
                  stateRecovery=0, failedRecovery=0, momentum5Pct=-1., newPeak=0)
    values.update(updates)
    return {'now': now, 'maxKnownAt': now, 'maxBarEnd': now, 'fresh': True, 'values': values}


def row(now, state='DROP', signals=None, **nums):
    cats = dict.fromkeys(P['features']['categorical'], 'UNKNOWN'); cats['currentState.state'] = state
    for name, value in zip(SIGNALS, signals or ['UNKNOWN'] * 6): cats['signal.' + name + '.currentTriState'] = value
    numeric = dict.fromkeys(P['features']['baseNumeric'])
    numeric.update({'position.activeMinutesHeld': now - 549, 'position.fullOwnedPrefix': 1,
        'position.freshClosedPrice': 1, 'position.lastObservedClose': 100., 'position.lastObservedClosedAt': now,
        'position.currentReturnPct': 0., 'position.observedRunningHigh': 102.,
        'position.peakConfirmedAt': min(550, now), 'position.completePrefixMfePct': 2.,
        'position.observedPeakGivebackPp': 2., 'position.activeMinutesSincePeakConfirmation': 1})
    numeric.update(nums)
    return {'session': DAY, 'identity': ['IMMEDIATE', 'E', now], 'fresh': True,
            'categorical': [cats[k] for k in P['features']['categorical']],
            'numeric': [numeric[k] for k in P['features']['baseNumeric']]}


def bars(end=550):
    return [[t, 100., 102., 99., 100. + .1 * (t - (end - 5)), 10., 1000.] for t in range(end - 5, end)]


class RuntimeTests(unittest.TestCase):
    def apply_two(self, values=None, scores=(.9, .9, .9), c=0):
        a = rt.intent(DAY, envelope(**(values or {})), list(scores), rt.initial_state(), P['candidates'][c])
        return rt.intent(DAY, envelope(now=551, **(values or {})), list(scores), a['state'], P['candidates'][c])

    def test_frozen_identity_and_exact_candidates(self):
        self.assertEqual(len(P['candidates']), 4); self.assertEqual(P['execution']['expectedModelFitCount'], 24)
        import hashlib
        self.assertEqual(hashlib.sha256(rt.PROTOCOL_PATH.read_bytes()).hexdigest(), rt.PROTOCOL_SHA256)

    def test_d_overrides_c_and_protection(self):
        self.assertEqual(self.apply_two()['authority'], 'DETERIORATION')

    def test_protection_overrides_high_continuation(self):
        r = self.apply_two(scores=(.99, .9, .1)); self.assertEqual(r['authority'], 'PROTECTION')

    def test_confirmation_requires_two(self):
        r = rt.intent(DAY, envelope(), [.9, .9, .9], rt.initial_state(), P['candidates'][0])
        self.assertEqual(r['action'], 'HOLD'); self.assertEqual(r['state']['dCount'], 1)

    def test_failed_recovery_candidate_not_structure_alone(self):
        v = {'weakRun': 0, 'lowerHigh': 1, 'lowerLow': 1, 'certifiedGivebackPp': None}
        self.assertEqual(self.apply_two(v, c=0)['action'], 'EXIT_INTENT')
        self.assertEqual(self.apply_two(v, c=2)['action'], 'HOLD')
        v['failedRecovery'] = 1
        self.assertEqual(self.apply_two(v, c=2)['action'], 'EXIT_INTENT')

    def test_drop_or_negative_pnl_alone_never_exits(self):
        for candidate in P['candidates']:
            s = rt.initial_state()
            for now in range(550, 580):
                e = envelope(now, currentReturnPct=-20., certifiedMfePct=None, certifiedGivebackPp=None,
                             signalFalseN=0, signalLossN=0, momentum5Pct=0.)
                r = rt.intent(DAY, e, [.1, .99, .99], s, candidate); s = r['state']
                self.assertEqual(r['action'], 'HOLD')

    def test_missing_individual_facts_do_not_satisfy_comparisons(self):
        for key in ('momentum5Pct', 'weakRun', 'signalFalseN'):
            v = {key: None, 'lowerHigh': None, 'lowerLow': None, 'certifiedGivebackPp': None}
            self.assertEqual(self.apply_two(v)['action'], 'HOLD')

    def test_uncertified_giveback_cannot_protect(self):
        self.assertEqual(self.apply_two({'certifiedGivebackPp': None}, scores=(.99, .99, .1))['action'], 'HOLD')

    def test_stale_or_invalid_score_resets_counts_not_arm(self):
        for scores in ([None, .8, .8], [.9, float('nan'), .9], [.9, .9], [True, .9, .9]):
            s = rt.initial_state(); s.update(armed=True, dCount=1, pCount=1, neutralCount=2, probation=1)
            r = rt.intent(DAY, envelope(), scores, s, P['candidates'][1])
            self.assertTrue(r['state']['armed']); self.assertEqual(r['state']['dCount'], 0)
            self.assertEqual(r['state']['probation'], 1)
        e = envelope(); e['fresh'] = False
        self.assertEqual(rt.intent(DAY, e, [.9] * 3, s, P['candidates'][1])['action'], 'HOLD')

    def test_gap_resets_counts_and_probation(self):
        s = rt.initial_state(); s.update(lastNow=548, dCount=1, probation=2)
        r = rt.intent(DAY, envelope(), [.9] * 3, s, P['candidates'][1])
        self.assertEqual(r['state']['dCount'], 1); self.assertEqual(r['state']['probation'], 0)

    def test_lunch_endpoints_are_adjacent(self):
        self.assertTrue(rt.adjacent(DAY, 690, 751)); self.assertFalse(rt.adjacent(DAY, 690, 752))

    def test_neutral_requires_three_then_two(self):
        s = rt.initial_state(); actions = []
        for now in range(550, 554):
            r = rt.intent(DAY, envelope(now), [.1] * 3, s, P['candidates'][0]); s = r['state']; actions.append(r['action'])
        self.assertEqual(actions, ['HOLD', 'HOLD', 'HOLD', 'EXIT_INTENT'])
        self.assertEqual(r['authority'], 'NEUTRAL_DETERIORATION')

    def test_neutral_needs_all_corroborating_facts(self):
        for update in ({'barsHeld': 14}, {'currentReturnPct': .1}, {'weakRun': 2}, {'momentum5Pct': 0}, {'signalFalseN': 1}):
            s = rt.initial_state()
            for now in range(550, 560):
                r = rt.intent(DAY, envelope(now, **update), [.1] * 3, s, P['candidates'][0]); s = r['state']
                self.assertEqual(r['action'], 'HOLD')

    def test_probation_two_fresh_only_and_d_override(self):
        c = P['candidates'][1]; s = rt.initial_state()
        r = rt.intent(DAY, envelope(550, stateRecovery=1, signalTrueN=1, momentum5Pct=.1), [.9, .9, .1], s, c)
        self.assertEqual(r['state']['probation'], 1)
        r = rt.intent(DAY, envelope(551), [.9, .9, .1], r['state'], c)
        self.assertEqual(r['state']['pCount'], 0); self.assertEqual(r['state']['probation'], 0)
        r = rt.intent(DAY, envelope(552), [.9, .9, .1], r['state'], c)
        self.assertEqual(r['state']['pCount'], 1)
        r = rt.intent(DAY, envelope(553), [.9, .9, .1], r['state'], c)
        self.assertEqual(r['authority'], 'PROTECTION')
        s = rt.initial_state(); s.update(dCount=1, probation=2, armed=True)
        self.assertEqual(rt.intent(DAY, envelope(), [.9] * 3, s, c)['authority'], 'DETERIORATION')

    def test_new_peak_resets_protection(self):
        s = rt.initial_state(); s.update(pCount=1, probation=2, armed=True)
        r = rt.intent(DAY, envelope(newPeak=1), [.9, .9, .1], s, P['candidates'][1])
        self.assertEqual(r['state']['pCount'], 0); self.assertEqual(r['state']['probation'], 0)

    def test_terminal_even_missing(self):
        e = envelope(925); e['fresh'] = False
        self.assertEqual(rt.intent(DAY, e, [None] * 3, rt.initial_state(), P['candidates'][0])['action'], 'FORCE_TERMINAL')

    def test_transport_future_and_extra_keys_rejected(self):
        for mutation in ('future', 'extra', 'nan'):
            e = envelope()
            if mutation == 'future': e['maxKnownAt'] = 551
            elif mutation == 'extra': e['values']['labelAvailability'] = 1
            else: e['values']['currentReturnPct'] = float('nan')
            with self.assertRaises(ValueError): rt.intent(DAY, e, [.9] * 3, rt.initial_state(), P['candidates'][0])

    def test_nonregistered_policy_and_replayed_now_rejected(self):
        c = deepcopy(P['candidates'][0]); c['threshold'] = .5
        with self.assertRaises(ValueError): rt.intent(DAY, envelope(), [.9] * 3, rt.initial_state(), c)
        s = rt.initial_state(); s['lastNow'] = 550
        with self.assertRaises(ValueError): rt.intent(DAY, envelope(), [.9] * 3, s, P['candidates'][0])

    def test_decision_modules_do_not_import_labels_models_or_evaluators(self):
        for name in ('runtime', 'facts'):
            source = (rt.ROOT / 'scripts' / ('phase57_exit_gen3_' + name + '_r45.py')).read_text()
            imports = [n for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.Import, ast.ImportFrom))]
            text = ' '.join(ast.unparse(n) for n in imports)
            for forbidden in ('labels', 'sklearn', 'finite_r36', 'evaluator', 'capture_metrics'):
                self.assertNotIn(forbidden, text)


class FactTests(unittest.TestCase):
    def test_price_exact_window_and_volume_independence(self):
        b = bars(); f = price_facts(DAY, 550, b)
        self.assertAlmostEqual(f['momentum5Pct'], .4); self.assertEqual(f['volume5'], 50.)
        b[-1][2] = -1; f = price_facts(DAY, 550, b)
        self.assertIsNone(f['momentum5Pct']); self.assertEqual(f['volume5'], 50.)
        self.assertIsNone(price_facts(DAY, 550, bars()[:-1])['momentum5Pct'])

    def test_future_closed_row_rejected(self):
        with self.assertRaises(ValueError): price_facts(DAY, 550, bars() + [[550, 100, 101, 99, 100, 1, 1]])

    def test_unknown_not_signal_loss(self):
        enc = FactEncoder(DAY, ('IMMEDIATE', 'E'))
        enc.encode(row(550, signals=['TRUE'] * 6), bars())
        out = enc.encode(row(551), bars(551))['values']
        self.assertEqual(out['signalUnknownN'], 6); self.assertEqual(out['signalLossN'], 0)

    def test_actual_signal_and_state_recovery(self):
        enc = FactEncoder(DAY, ('IMMEDIATE', 'E'))
        enc.encode(row(550, signals=['FALSE'] * 6), bars())
        out = enc.encode(row(551, state='REBOUND', signals=['TRUE'] * 6), bars(551))['values']
        self.assertEqual(out['stateRecovery'], 1); self.assertEqual(out['signalRecoveryN'], 6)
        out = enc.encode(row(552, state='DROP', signals=['FALSE'] * 6), bars(552))['values']
        self.assertEqual(out['failedRecovery'], 1); self.assertEqual(out['signalLossN'], 6)

    def test_gap_and_stale_reset_histories(self):
        enc = FactEncoder(DAY, ('IMMEDIATE', 'E')); enc.encode(row(550), bars())
        out = enc.encode(row(552, state='RISE'), bars(552))['values']
        self.assertIsNone(out['stateRecovery'])
        stale = row(553); stale['fresh'] = False
        out = enc.encode(stale, bars(553))['values']; self.assertIsNone(out['currentReturnPct'])
        out = enc.encode(row(554, state='DROP'), bars(554))['values']; self.assertEqual(out['weakRun'], 1)

    def test_no_uncertified_peak_and_strict_new_peak(self):
        enc = FactEncoder(DAY, ('IMMEDIATE', 'E'))
        out = enc.encode(row(550), bars())['values']; self.assertEqual(out['newPeak'], 1)
        out = enc.encode(row(551), bars(551))['values']; self.assertEqual(out['newPeak'], 0)
        out = enc.encode(row(552, **{'position.fullOwnedPrefix': 0}), bars(552))['values']
        self.assertIsNone(out['certifiedGivebackPp']); self.assertIsNone(out['certifiedMfePct'])

    def test_identity_future_peak_and_fresh_time_guards(self):
        for change in ({'position.peakConfirmedAt': 551}, {'position.lastObservedClosedAt': 549}):
            with self.assertRaises(ValueError): FactEncoder(DAY, ('IMMEDIATE', 'E')).encode(row(550, **change), bars())
        with self.assertRaises(ValueError): FactEncoder(DAY, ('IMMEDIATE', 'OTHER')).encode(row(550), bars())

    def test_weak_run_cap_and_pullback_not_weak(self):
        enc = FactEncoder(DAY, ('IMMEDIATE', 'E'))
        for t in range(550, 563): out = enc.encode(row(t), bars(t))
        self.assertEqual(out['values']['weakRun'], 10)
        self.assertEqual(enc.encode(row(563, state='PULLBACK'), bars(563))['values']['weakRun'], 0)

    def test_calendar_only(self):
        self.assertEqual(calendar_features(DAY, 690), [175, 15])
        self.assertEqual(calendar_features(DAY, 925), [0, 0])


class LabelTests(unittest.TestCase):
    def make_labels(self, utilities=(1., 1., 1.), now=550, mfe=2., fresh=True, entry=100.):
        anchor, times, _, _ = reference_plan(now, SCHEDULE, P['labels'])
        index = {t: [t, v, v, v, v, 1., 1.] for t, v in zip((anchor, *times), (100., *(100. + x * entry / 100 for x in utilities)))}
        return utility_labels(now, SCHEDULE, index, entry, fresh, mfe, P['labels']), index

    def test_positive_negative_and_protection(self):
        self.assertEqual(list(self.make_labels()[0]['targets'].values()), [1, 0, 0])
        self.assertEqual(list(self.make_labels((-1., -1., -1.))[0]['targets'].values()), [0, 1, 1])
        self.assertIsNone(self.make_labels(mfe=None)[0]['targets']['PROTECTION'])

    def test_single_touch_not_persistent(self):
        self.assertEqual(self.make_labels((-1., -1., 1.))[0]['targets']['CONTINUATION'], 0)
        self.assertEqual(self.make_labels((1., 1., -1.))[0]['targets']['DETERIORATION'], 0)

    def test_boundaries_and_entry_denominator(self):
        a = self.make_labels((.5, .5, .5))[0]; self.assertEqual(a['targets']['CONTINUATION'], 1)
        a = self.make_labels((-.25, -.25, -.25))[0]; self.assertEqual(a['targets']['PROTECTION'], 1)
        a = self.make_labels((-.5, -.5, -.5), entry=200.)[0]
        self.assertEqual(a['targets']['DETERIORATION'], 1)

    def test_all_endpoints_plan_shortening_lunch_auction(self):
        for t in rt.endpoints(DAY):
            a, times, h, reason = reference_plan(t, SCHEDULE, P['labels'])
            if h >= 3: self.assertEqual(len(set(times)), 3); self.assertGreater(min(times), t)
            else: self.assertTrue(reason)
        self.assertEqual(reference_plan(690, SCHEDULE, P['labels'])[:2], (750, (755, 760, 765)))
        self.assertEqual(reference_plan(922, SCHEDULE, P['labels'])[:2], (922, (923, 924, 930)))

    def test_missing_reference_never_forward_searches(self):
        _, index = self.make_labels(); del index[555]
        index[556] = [556, 110, 110, 110, 110, 1, 1]
        r = utility_labels(550, SCHEDULE, index, 100., True, 2., P['labels'])
        self.assertTrue(all(v is None for v in r['targets'].values()))

    def test_unsampled_gaps_do_not_claim_complete_path(self):
        r, index = self.make_labels()
        self.assertEqual(len(index), 4); self.assertTrue(all(r['available']))

    def test_stale_terminal_and_short_are_null(self):
        self.assertFalse(any(self.make_labels(fresh=False)[0]['available']))
        for t in (923, 924, 925):
            r = utility_labels(t, SCHEDULE, {}, 100., True, 2., P['labels'])
            self.assertFalse(any(r['available']))

    def test_invalid_auction_and_duplicate_raw(self):
        _, index = self.make_labels(now=922); index[930][2] += 1
        r = utility_labels(922, SCHEDULE, index, 100., True, 2., P['labels'])
        self.assertFalse(any(r['available']))
        with self.assertRaises(ValueError): index_rows([[550] * 7, [550] * 7])

    def test_cd_exclusive_randomized(self):
        rng = np.random.default_rng(5757)
        for vals in rng.uniform(-3, 3, (250, 3)):
            r = self.make_labels(tuple(map(float, vals)))[0]
            self.assertFalse(r['targets']['CONTINUATION'] == r['targets']['DETERIORATION'] == 1)


class SupportTests(unittest.TestCase):
    def data(self):
        days = sorted({s for f in P['split']['folds'] for key in ('train', 'purge', 'score') for s in f[key]})
        triples = [(s, a, k) for s in range(len(days)) for a in (0, 1) for k in range(20)]
        n = len(triples)
        return SimpleNamespace(session_names=days, sessions=np.array([s for s, a, k in triples]),
            arms=np.array([a for s, a, k in triples]), entries=np.array([s * 4 + a * 2 + k % 2 for s, a, k in triples]),
            now=np.full(n, 600), fresh=np.ones(n, bool), targets=np.array([[k % 2] * 3 for s, a, k in triples], float))

    def test_all_24_support_slices(self):
        slices, report = support_slices(self.data(), P); self.assertEqual(len(slices), 24)
        self.assertTrue(all(r['sessions'] >= 5 for r in report))

    def test_single_class_and_stale_training_forbidden(self):
        d = self.data(); d.targets[:, 1] = 0
        with self.assertRaises(ValueError): support_slices(d, P)
        d = self.data(); d.fresh[0] = False
        with self.assertRaises(ValueError): support_slices(d, P)

    def test_train_score_overlap_rejected(self):
        p = deepcopy(P); p['split']['folds'][0]['score'].append(p['split']['folds'][0]['train'][0])
        with self.assertRaises(ValueError): support_slices(self.data(), p)


class LaunchTests(unittest.TestCase):
    def inputs(self):
        execution, trigger = 'a' * 40, 'b' * 40; sources = {'source.py': 'c' * 64}
        marker = {'schema': 'phase57-gen3-launch-r45-v1', 'authorizedByUser': True, 'executionSha': execution,
                  'protocolSha256': rt.PROTOCOL_SHA256, 'contractRunId': 10}
        ci = {'status': 'GEN3_PREFLIGHT_PASS_NOT_PERFORMANCE_PASS', 'executionSha': execution, 'runId': 10,
              'protocolSha256': rt.PROTOCOL_SHA256, 'sourceHashes': sources, 'candidateCount': 4,
              'expectedModelFitCount': 24, 'supportSlices': 24, 'modelFits': 0, 'policyReplays': 0,
              'gen3PerformanceInspected': False, 'safety': P['safety']}
        env = {'GITHUB_REPOSITORY': REPO, 'GITHUB_REF': 'refs/heads/' + BRANCH, 'GITHUB_SHA': trigger,
               'GITHUB_RUN_ID': '20', 'GITHUB_RUN_ATTEMPT': '1'}
        responses = {'/git/ref/heads/' + BRANCH: {'object': {'sha': trigger}},
            '/actions/runs/10': {'id': 10, 'head_sha': execution, 'path': CI_PATH, 'status': 'completed', 'conclusion': 'success'},
            '/actions/runs/20': {'id': 20, 'head_sha': trigger, 'path': FINITE_PATH, 'run_attempt': 1, 'workflow_id': 30},
            '/actions/workflows/30/runs?per_page=100&page=1': {'workflow_runs': [{'id': 20}]},
            '/compare/' + execution + '...' + trigger: {'status': 'ahead', 'base_commit': {'sha': execution},
                'files': [{'filename': MARKER, 'status': 'added'}]},
            '/actions/artifacts/' + str(R35_ARTIFACT): {'id': R35_ARTIFACT, 'workflow_run': {'id': R35_RUN},
                'expired': False, 'digest': 'sha256:' + R35_DIGEST}}
        return marker, ci, sources, execution, env, responses

    def test_exact_launch_passes(self):
        m, c, s, x, e, r = self.inputs()
        self.assertEqual(validate_launch(m, c, s, x, e, r.__getitem__)['status'], 'R45_LAUNCH_AUTHORIZED')

    def test_no_approval_or_rerun_or_wrong_source(self):
        for variant in ('approval', 'rerun', 'source', 'support', 'ci'):
            m, c, s, x, e, r = self.inputs()
            if variant == 'approval': m['authorizedByUser'] = False
            elif variant == 'rerun': e['GITHUB_RUN_ATTEMPT'] = '2'
            elif variant == 'source': c['sourceHashes'] = {}
            elif variant == 'support': c['supportSlices'] = 23
            else: r['/actions/runs/10']['conclusion'] = 'failure'
            with self.assertRaises(ValueError): validate_launch(m, c, s, x, e, r.__getitem__)

    def test_any_prior_finite_run_or_code_change_blocks(self):
        for variant in ('duplicate', 'code', 'head'):
            m, c, s, x, e, r = self.inputs()
            if variant == 'duplicate': r['/actions/workflows/30/runs?per_page=100&page=1']['workflow_runs'].append({'id': 19})
            elif variant == 'code': r['/compare/' + x + '...' + e['GITHUB_SHA']]['files'].append({'filename': 'scripts/change.py', 'status': 'modified'})
            else: r['/git/ref/heads/' + BRANCH]['object']['sha'] = 'd' * 40
            with self.assertRaises(ValueError): validate_launch(m, c, s, x, e, r.__getitem__)


class ReplayTests(unittest.TestCase):
    def fake(self):
        names = P['features']['baseNumeric'] + P['features']['calendarFields'] + ['facts.' + f for f in P['features']['decisionFactFields']]
        nums = np.full((4, len(names)), np.nan, np.float32)
        now = [550, 551, 552, 925]
        for i, t in enumerate(now):
            for k, v in envelope(t)['values'].items(): nums[i, names.index('facts.' + k)] = np.nan if v is None else v
            for k, v in {'position.observedRunningHigh': 103., 'position.peakConfirmedAt': 550., 'position.fullOwnedPrefix': 1.}.items(): nums[i, names.index(k)] = v
        entry = {'entryId': 'E', 'entryArm': 'IMMEDIATE', 'opportunity': 'O', 'entryMinute': 549,
                 'price': 100., 'session': DAY}
        raw = [[549, 100., 100., 100., 100., 1., 1.], [550, 101., 101., 101., 101., 1., 1.],
               [551, 102., 102., 102., 102., 1., 1.], [552, 101., 101., 101., 101., 1., 1.],
               [930, 99., 99., 99., 99., 1., 1.]]
        return SimpleNamespace(session_names=[DAY], sessions=np.zeros(4, int), arms=np.zeros(4, int),
            entries=np.zeros(4, int), now=np.array(now), fresh=np.ones(4, bool), numeric_names=names,
            numeric=nums, entry_ids=['IMMEDIATE::E'], entry_rows={'IMMEDIATE::E': entry},
            raw={'O': {'today': raw}}, opportunity_records={'O': {}})

    def run_fake(self, d, scores):
        with patch('scripts.phase57_exit_finite_r36._ordered_geometry', return_value=None):
            return replay_candidate(d, scores, P['candidates'][0], P)[0]

    def test_execution_after_intent_and_native_peak(self):
        d = self.fake(); r = self.run_fake(d, np.full((4, 3), .9))
        self.assertEqual(r['decisionNow'], 551); self.assertEqual(r['exitMinute'], 551)
        self.assertAlmostEqual(r['netReturnPctBySellCost']['0.05'], 1.95)
        self.assertIsNotNone(r['metrics']['ownedPeakGivebackPp'])

    def test_missing_reference_not_queued(self):
        d = self.fake(); d.raw['O']['today'] = [r for r in d.raw['O']['today'] if r[0] != 551]
        scores = np.full((4, 3), .9); scores[2] = [.9, .1, .1]
        r = self.run_fake(d, scores)
        self.assertEqual(r['exitMinute'], 930); self.assertEqual(r['missingOrdinaryReferences'], 1)

    def test_missing_terminal_not_invented(self):
        d = self.fake(); d.raw['O']['today'] = [r for r in d.raw['O']['today'] if r[0] != 930]
        r = self.run_fake(d, np.full((4, 3), np.nan))
        self.assertEqual(r['exitStatus'], 'UNRESOLVED_TERMINAL_EXIT'); self.assertIsNone(r['exitPrice'])

    def test_future_high_cannot_change_decision(self):
        d = self.fake(); a = self.run_fake(d, np.full((4, 3), .9))
        d.raw['O']['today'][3][2] = 1000.
        b = self.run_fake(d, np.full((4, 3), .9))
        for k in ('decisionNow', 'exitMinute', 'exitPrice', 'authority', 'decisionSequenceSha256'):
            self.assertEqual(a[k], b[k])


if __name__ == '__main__':
    unittest.main()
