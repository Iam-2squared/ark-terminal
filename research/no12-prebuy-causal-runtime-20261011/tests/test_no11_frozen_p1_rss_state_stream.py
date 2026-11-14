"""Actual pinned RC2/Path/price features on SYNTHETIC RSS; test scorer only.

This file is picked up by the existing Linux/Windows frozen-P1 Python CI step.
No private weights, broker account, market data or model fitting is used.
"""
from copy import deepcopy
from pathlib import Path
import math
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_rss_state9_p1_runner as r
import no11_frozen_p1_feature_runtime as feature
import no11_p1_forward_shadow as f
import test_no11_p1_forward_shadow as base

DAY = '2026-10-26'
PRIOR = '2026-10-23'
CODE = '7203.T'


def at(m, second=8):
    return DAY + f'T{m // 60:02d}:{m % 60:02d}:{second:02d}+09:00'


def previous(include_va=True):
    rows = []
    for m in range(540, 580):
        p = 100 + (m - 540) * .05
        row = {'Date': PRIOR, 'Code': CODE, 'Time': f'{m // 60:02d}:{m % 60:02d}',
               'O': p, 'H': p + .2, 'L': p - .2, 'C': p + .01, 'Vo': 100}
        if include_va:
            row['Va'] = p * 100
        rows.append(row)
    return {'schemaId': r.PREVIOUS_SCHEMA, 'sessionDate': DAY, 'previousSession': PRIOR,
            'orderTransmission': False, 'symbols': {CODE: {
                'previousSession': PRIOR, 'priceBasis': 'COMPARABLE_RAW',
                'corporateActionsCleared': True, 'knownAtJst': at(535, 0), 'rows': rows}}}


def feed(count=35):
    rows = []
    for m in range(540, 540 + count):
        p = 102 + .3 * (m - 540) + .02 * math.sin(m)
        rows.append({'Date': DAY, 'Code': CODE, 'Time': f'{m // 60:02d}:{m % 60:02d}',
                     'O': p, 'H': p + .2, 'L': p - .2, 'C': p + .01, 'Vo': 100,
                     'Va': p * 100, 'knownAtJst': at(m + 1), 'vaProvenance': r.VA_SOURCE})
    return {'receipt': {'schemaId': 'ARK_NO11_RSS_CHART50_OFFLINE_JOIN_V1',
                       'sessionDate': DAY, 'productionReady': False, 'orderTransmission': False,
                       'approximateMinuteVaRows': count,
                       'proxyReceipt': {'schemaId': 'ARK_NO11_RSS_MARKET_APPROX_MINUTE_VA_SHADOW_V1',
                                        'nativeExactMinuteVaCertified': False, 'orderTransmission': False,
                                        'selectedSymbols': [CODE], 'validOneMinuteProxyRows': count}}, 'rows': rows}


def selectors():
    return [{'kind': 'selector', 'receivedAtJst': at(570, 7), 'payload': base.selector()}]


class RecordingScorer(base.FakeScorer):
    def __init__(self):
        super().__init__()
        self.captured = []

    def score(self, numeric, categorical):
        self.calls += 1
        self.captured.append((deepcopy(numeric), list(categorical)))
        return {'score': .2 if self.calls == 1 else .8, 'syntheticScorerOnly': True}


class ActualOriginalFeatureStreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Do NOT skip this if public Frozen files are unavailable.
        cls.runtime = feature.load_feature_runtime(f.REPO)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'p1.sqlite'
        self.scorer = RecordingScorer()
        self.session = f.ForwardP1Session(self.db, self.scorer)

    def tearDown(self):
        self.session.close()
        self.temp.cleanup()

    def run_feed(self, data=None, events=None, prior=None):
        return r.consume_received_feed(self.runtime, self.session,
                                       feed() if data is None else data,
                                       selectors() if events is None else events,
                                       previous() if prior is None else prior,
                                       previous_session=PRIOR, through=at(580, 0))

    def test_actual_rc2_features_reach_p1_candidate_without_handmade_state(self):
        result = self.run_feed()
        self.assertEqual(result['counts']['state9Rows'], 35)
        self.assertEqual(result['counts']['p1FeatureRows'], 6)
        self.assertEqual(result['acceptedStateTicks'], 35)
        self.assertEqual(result['missingScheduledStateTicks'], 0)
        self.assertEqual(result['p1Session']['firstEntryCandidates'], 1)
        self.assertEqual(self.scorer.calls, 2)
        self.assertEqual(result['decisionStatusCounts']['WAIT'], 1)
        self.assertEqual(result['decisionStatusCounts']['FIRST_ENTRY_CANDIDATE'], 1)
        self.assertEqual(result['decisionStatusCounts']['FIRST_ENTRY_ALREADY_LOCKED'], 4)
        numeric, categorical = self.scorer.captured[0]
        self.assertEqual(len(numeric), 148)
        self.assertEqual(len(categorical), 15)
        self.assertEqual(numeric[0], 5.0)
        source_index = self.runtime.feature['P1_categorical'].index('state/source')
        self.assertEqual(categorical[source_index], r.KERNEL_SOURCE)
        self.assertEqual(categorical[-1], 'RSS_PROXY_PREVIOUS_ACTIVITY_PRESENT')
        self.assertTrue(result['logicalKernelClockIsNotReceiptClock'])
        self.assertFalse(result['privateModelsExecuted'])
        self.assertFalse(result['orderTransmission'])
        self.assertFalse(result['productionReady'])

    def test_previous_ohlc_can_seed_state_without_fabricating_previous_va(self):
        result = self.run_feed(prior=previous(include_va=False))
        self.assertEqual(result['counts']['p1FeatureRows'], 6)
        numeric, categorical = self.scorer.captured[0]
        self.assertEqual(categorical[-1], 'RSS_PROXY_PREVIOUS_OHLC_ONLY_ACTIVITY_MISSING')
        self.assertTrue(any(v is None for v in numeric))

    def test_no_previous_context_blocks_only_symbol_and_no_candidate(self):
        ctx = previous()
        ctx['symbols'] = {}
        result = self.run_feed(prior=ctx)
        self.assertEqual(result['p1Session']['firstEntryCandidates'], 0)
        self.assertEqual(result['state9Symbols'], 0)
        self.assertEqual(result['blockedSymbolCounts'], {'PREVIOUS_NORMALIZATION_SOURCE_UNAVAILABLE': 1})
        self.assertEqual(self.scorer.calls, 0)

    def test_actual_state_gap_step_is_not_a_filled_ohlc_row(self):
        data = feed()
        data['rows'].pop(10)
        data['receipt']['approximateMinuteVaRows'] -= 1
        data['receipt']['proxyReceipt']['validOneMinuteProxyRows'] -= 1
        result = self.run_feed(data=data)
        self.assertEqual(result['missingScheduledStateTicks'], 1)
        self.assertEqual(result['acceptedStateTicks'], 34)
        self.assertEqual(result['counts']['receivedMinuteRows'], 34)

    def test_receipt_after_cutoff_and_receipt_before_close_are_rejected(self):
        data = feed()
        data['rows'][-1]['knownAtJst'] = at(581)
        with self.assertRaisesRegex(ValueError, 'UNCLOSED_OR_FUTURE_RECEIPT'):
            self.run_feed(data=data)
        data = feed()
        data['rows'][0]['knownAtJst'] = at(540)
        with self.assertRaisesRegex(ValueError, 'UNCLOSED_OR_FUTURE_RECEIPT'):
            self.run_feed(data=data)
        self.assertEqual(self.session.summary()['evaluations'], 0)

    def test_late_retroactive_bar_is_not_inserted_into_state_history(self):
        data = feed()
        data['rows'][10]['knownAtJst'] = at(553)
        with self.assertRaisesRegex(ValueError, 'LATE_OR_REVISED_BAR'):
            self.run_feed(data=data)

    def test_full_received_prefix_replay_and_restart_are_idempotent(self):
        first = self.run_feed()
        self.session.close()
        self.session = f.ForwardP1Session(self.db, self.scorer)
        second = self.run_feed()
        self.assertEqual(second['counts']['idempotentDecisions'], 6)
        self.assertEqual(second['p1Session']['firstEntryCandidates'], 1)
        self.assertEqual(first['p1Session']['evaluations'], second['p1Session']['evaluations'])
        self.assertEqual(self.scorer.calls, 2)

    def test_changed_previous_basis_cannot_reuse_persisted_candidates(self):
        self.run_feed()
        ctx = previous()
        ctx['symbols'][CODE]['rows'][0]['C'] += .01
        with self.assertRaisesRegex(ValueError, 'PREVIOUS_CONTEXT_CHANGED_ON_RESTART'):
            self.run_feed(prior=ctx)

    def test_relabeling_proxy_as_native_or_duplicate_minute_is_rejected(self):
        data = feed()
        data['rows'][0]['vaProvenance'] = 'ORIGINAL_SAVED_JQUANTS_V2'
        with self.assertRaisesRegex(ValueError, 'MINUTE_SOURCE_IDENTITY'):
            self.run_feed(data=data)
        data = feed()
        data['rows'][1] = deepcopy(data['rows'][0])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_MINUTE'):
            self.run_feed(data=data)

    def test_selector_not_received_yet_does_not_activate_watch(self):
        events = selectors()
        events[0]['receivedAtJst'] = at(574, 9)
        result = self.run_feed(events=events)
        self.assertEqual(result['counts']['p1FeatureRows'], 1)
        self.assertEqual(result['p1Session']['firstEntryCandidates'], 0)
        self.assertEqual(self.scorer.calls, 1)

    def test_old_current_bar_does_not_make_new_entry_candidate(self):
        data = feed(30)
        data['rows'][-1]['knownAtJst'] = at(572, 0)
        result = self.run_feed(data=data)
        self.assertEqual(result['counts']['staleCurrentBarsSkipped'], 1)
        self.assertEqual(self.scorer.calls, 0)

    def test_no_selector_means_state_warmup_without_p1_or_buy(self):
        result = self.run_feed(events=[])
        self.assertEqual(result['counts']['state9Rows'], 35)
        self.assertEqual(result['p1Session']['watches'], 0)
        self.assertEqual(self.scorer.calls, 0)

    def test_existing_jpx_calendar_uses_friday_for_monday(self):
        self.assertEqual(r.previous_cash_session(f.REPO, DAY), PRIOR)
        with self.assertRaisesRegex(ValueError, 'DATED_CASH_CALENDAR_FAILED'):
            r.previous_cash_session(f.REPO, '2026-10-25')


if __name__ == '__main__':
    unittest.main()
