"""47-candidate R0 -> native V5 -> durable Shadow -> original EXIT regressions.

Synthetic prices, scores and cash only. The unchanged native math and held
State9 run for real; this is not a live RSS/private-model throughput benchmark.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_h235_asof_forward_shadow as h
import no11_h235_capital_v5_shadow as cap
import no11_frozen_p1_feature_runtime as features
import no11_received_pipeline_service as service
import no11_observed_execution_shadow as wiring
import no11_received_failure_isolation as isolation
import no11_shadow_portfolio as ledger
import test_no11_frozen_p1_h235_asof as models
import test_no11_frozen_p1_rss_state_stream as market
import test_no11_frozen_p1_execution_bundle as f

DAY, at = f.DAY, f.at


def batch_of(scorer, n, price, clock):
    template = scorer.score(models.valid_input())
    # Synthetic probabilities through the ORIGINAL PAVA/ML implementation.
    template.update(scorer.stair.materialize({'p2': 1., 'p3': 1., 'p5': 1.,
                                              'base2': .6, 'base3': .5, 'base5': .4}))
    rows = [dict(template, candidateId=h.digest(['capacity', i]),
                 symbol='%04d.T' % (1000 + i), decisionAtJst=clock,
                 raw_reference=price) for i in range(n)]
    rows.sort(key=scorer.stair.candidate_order)
    return {'schemaId': 'ARK_NO11_H235_ASOF_PRIVATE_RANK_BATCH_V1',
            'policy': scorer.policy, 'results': rows, 'capitalV5Executed': False,
            'brokerOrders': 0, 'productionReady': False, 'orderTransmission': False}


def scenario(clock):
    return {'schemaId': cap.SCENARIO, 'evidenceMode': 'SYNTHETIC_OFFLINE_ONLY',
            'sessionDate': DAY, 'decisionAtJst': clock,
            'arkCapitalInputs': {'cash': 1000000, 'equity': 1000000, 'exposure': 0},
            'externalSymbols': [], 'arkManagedSymbols': [], 'existingBands': [],
            'afterFirstLegalSellFill': False, 'pendingBrokerOrders': False,
            'syntheticAccountOnly': True, 'productionReady': False, 'orderTransmission': False}


class RankCapacityAndClock(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        manifest = models.synthetic_models(self.root, None)
        self.scorer = h.FrozenH235AsOf(self.root, DAY, manifest=manifest)
        self.arrival = f.arrival()

    def tearDown(self):
        self.temp.cleanup()

    def test_47_rank_rows_reach_native_capital_without_truncation(self):
        batch = batch_of(self.scorer, 47, 101.25, at(575, 12))
        out = cap.fund_shadow(batch, scenario(at(575, 12)), self.arrival)['capital']
        self.assertEqual(out['admittedCount'], 3)
        self.assertEqual(len(out['rejected']), 44)
        accounted = [r['entry_id'] for r in out['allocations'] + out['rejected']]
        self.assertEqual(set(accounted), {r['candidateId'] for r in batch['results']})
        self.assertEqual(len(accounted), 47)
        self.assertEqual([r['entry_id'] for r in out['allocations']],
                         [r['candidateId'] for r in batch['results'][:3]])
        self.assertFalse(out['transmitted'])

    def test_outer_50_boundary_matches_chart_capacity_but_51_fails(self):
        out = cap.fund_shadow(batch_of(self.scorer, 50, 101.25, at(575, 12)),
                              scenario(at(575, 12)), self.arrival)['capital']
        self.assertEqual(len(out['allocations']) + len(out['rejected']), 50)
        with mock.patch.object(cap.native_v5, 'run_request') as run:
            with self.assertRaisesRegex(ValueError, 'RANK_BATCH_INVALID'):
                cap.fund_shadow(batch_of(self.scorer, 51, 101.25, at(575, 12)),
                                scenario(at(575, 12)), self.arrival)
            run.assert_not_called()

    def test_corrupt_47th_r0_is_not_ignored_after_max3(self):
        batch = batch_of(self.scorer, 47, 101.25, at(575, 12))
        batch['results'][-1]['newFits'] = 1
        with mock.patch.object(cap.native_v5, 'run_request') as run:
            with self.assertRaisesRegex(ValueError, 'R0_SOURCE_NOT_ORIGINAL_SHADOW'):
                cap.fund_shadow(batch, scenario(at(575, 12)), self.arrival)
            run.assert_not_called()

    def test_47_source_rank_order_is_not_silently_resorted(self):
        batch = batch_of(self.scorer, 47, 101.25, at(575, 12))
        batch['results'].reverse()
        with self.assertRaisesRegex(ValueError, 'R0_NOT_FROZEN_NATIVE_PRIORITY_ORDER'):
            cap.fund_shadow(batch, scenario(at(575, 12)), self.arrival)

    def test_equal_instants_with_and_without_zero_milliseconds_are_equivalent(self):
        plain = at(575, 12)
        millis = plain.replace('+09:00', '.000+09:00')
        for intent, decision, current in ((plain, millis, plain), (millis, plain, millis),
                                         (millis, millis, plain)):
            with self.subTest(intent=intent, decision=decision, current=current):
                batch = batch_of(self.scorer, 1, 101.25, decision)
                batch['results'][0]['entry_timestamp'] = intent
                self.assertEqual(cap.fund_shadow(batch, scenario(current), self.arrival)
                                 ['capital']['fundedCount'], 1)

    def test_one_millisecond_future_decision_or_intent_is_still_rejected(self):
        plain = at(575, 12)
        future = plain.replace('+09:00', '.001+09:00')
        for field in ('decisionAtJst', 'entry_timestamp'):
            with self.subTest(field=field):
                batch = batch_of(self.scorer, 1, 101.25, plain)
                batch['results'][0][field] = future
                with self.assertRaisesRegex(ValueError, 'R0_BATCH_NOT_SAME_OBSERVED_MINUTE'):
                    cap.fund_shadow(batch, scenario(plain), self.arrival)

    def test_wrong_session_intent_cannot_pass_a_lexical_comparison(self):
        batch = batch_of(self.scorer, 1, 101.25, at(575, 12))
        batch['results'][0]['entry_timestamp'] = '2026-10-23T09:31:00+09:00'
        with self.assertRaisesRegex(ValueError, 'TIMESTAMP'):
            cap.fund_shadow(batch, scenario(at(575, 12)), self.arrival)


class FortySevenCandidateLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = features.load_feature_runtime(h.ROOT)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config, self.arrival = f.config(self.root), f.arrival()
        manifest = models.synthetic_models(self.root, None)
        scorer = h.FrozenH235AsOf(self.root, DAY, manifest=manifest)
        source = market.feed(35)
        self.symbols = ['%04d.T' % (1000 + i) for i in range(47)]
        self.price = source['rows'][-1]['C']
        self.feed = deepcopy(source)
        self.feed['rows'] = [dict(row, Code=code) for code in self.symbols for row in source['rows']]
        self.feed['receipt']['proxyReceipt']['selectedSymbols'] = self.symbols
        self.refresh_counts()
        previous = market.previous()
        template = previous['symbols'][market.CODE]
        self.previous = dict(previous, symbols={})
        for code in self.symbols:
            context = deepcopy(template)
            context['rows'] = [dict(row, Code=code) for row in template['rows']]
            self.previous['symbols'][code] = context
        self.batch = batch_of(scorer, 47, self.price, at(575, 12))
        self.inference = self.store_batch(self.batch)
        self.runner = self.make_runner()

    def make_runner(self):
        return isolation.ExecutionShadow(self.root, self.config, self.arrival,
                                         self.runtime, self.previous, market.PRIOR)

    def tearDown(self):
        self.runner.close()
        self.temp.cleanup()

    def store_batch(self, batch):
        data = h.stable_bytes(batch) + b'\n'
        digest = hashlib.sha256(data).hexdigest()
        (self.root / ('h235-asof-' + digest[:16] + '.json')).write_bytes(data)
        return {'h235PrivateResultSha256': digest, 'p1Session': {'firstEntryCandidates': 47},
                'h235OriginalModelExecutions': 141}

    def refresh_counts(self):
        count = len(self.feed['rows'])
        self.feed['receipt']['approximateMinuteVaRows'] = count
        self.feed['receipt']['proxyReceipt']['validOneMinuteProxyRows'] = count

    def append_bar(self, minute, price):
        for code in self.symbols:
            self.feed['rows'].append({'Date': DAY, 'Code': code, 'Time': '%02d:%02d' % divmod(minute, 60),
                'O': price, 'H': price + .2, 'L': price - .2, 'C': price, 'Vo': 100,
                'Va': price * 100, 'knownAtJst': at(minute + 1, 8), 'vaProvenance': market.r.VA_SOURCE})
        self.refresh_counts()

    def own_three(self):
        first = self.runner.advance(self.feed, self.inference, at(575, 12))
        self.assertEqual(first['buyIntentCount'], 3)
        self.append_bar(575, self.price - .05)
        result = self.runner.advance(self.feed, self.inference, at(576, 12))
        self.assertEqual(result['positionCount'], 3)
        return result

    def test_47_candidates_partial_buy_restart_original_eod_and_three_exits(self):
        first = self.runner.advance(self.feed, self.inference, at(575, 12))
        self.assertEqual(first['buyIntentCount'], 3)
        self.assertEqual(first['positionCount'], 0)
        order = next(iter(self.runner.portfolio.state()['orders'].values()))
        self.assertGreater(order['quantity'], 100)
        update = {'schemaId': ledger.UPDATE, 'eventId': h.digest(['47', 'partial']),
                  'orderId': order['orderId'], 'symbol': order['symbol'], 'side': 'BUY',
                  'knownAtJst': at(575, 20), 'cumulativeQuantity': 100,
                  'cumulativeValueJpy': str(Decimal(str(self.price)) * 100),
                  'status': 'PARTIAL', 'syntheticOnly': True}
        self.runner.portfolio.update(update, at(575, 20))
        before = self.runner.portfolio.state()
        self.runner.close()
        self.runner = self.make_runner()
        self.assertEqual(self.runner.portfolio.state(), before)
        self.append_bar(575, self.price - .05)
        held = self.runner.advance(self.feed, self.inference, at(576, 12))
        self.assertEqual(held['positionCount'], 3)
        self.assertEqual(held['pendingOrders'], 0)
        self.assertEqual(held['buyIntentCount'], 3)
        self.assertEqual(len(self.runner.streams), 3)
        eod = self.runner.heartbeat(at(920))
        self.assertEqual(eod['sellIntentCount'], 3)
        self.assertEqual(eod['positionCount'], 3)
        self.append_bar(920, self.price + .5)
        sold = self.runner.advance(self.feed, self.inference, at(921, 12))
        self.assertEqual(sold['positionCount'], 0)
        self.assertTrue(sold['firstSellFillBuyHalt'])
        self.assertEqual(sold['brokerTransmissions'], 0)
        self.assertFalse(sold['orderTransmission'])
        before = self.runner.portfolio.state()
        self.runner.close()
        self.runner = self.make_runner()
        self.assertEqual(self.runner.portfolio.state(), before)
        replay = self.runner.advance(self.feed, self.inference, at(921, 20))
        self.assertEqual(replay['buyIntentCount'], 3)
        self.assertEqual(replay['sellIntentCount'], 3)
        self.assertEqual(replay['positionCount'], 0)

    def test_47_candidate_path_keeps_three_exits_after_entry_failure_and_restart(self):
        self.own_three()
        def failing_infer():
            raise ValueError('NO11_TEST_ENTRY_FAILURE')
        summary, paper = isolation.guarded_inference(self.runner, self.feed, failing_infer,
            clock=lambda: at(577, 12), p1_summary=lambda: {'firstEntryCandidates': 47})
        self.assertEqual(summary['status'], 'ENTRY_PIPELINE_HALTED')
        self.assertEqual(summary['exitStatus'], 'VALIDATED_FEED_EXIT_ONLY')
        self.assertEqual(paper['positionCount'], 3)
        self.assertTrue(paper['entryPipelineHalted'])
        self.runner.close()
        self.runner = self.make_runner()
        self.assertTrue(self.runner.entry_halted)
        eod = self.runner.heartbeat(at(920))
        self.assertEqual(eod['sellIntentCount'], 3)
        self.append_bar(920, self.price + .5)
        sold = self.runner.exit_only(self.feed, at(921, 12))
        self.assertEqual(sold['positionCount'], 0)
        self.assertTrue(sold['firstSellFillBuyHalt'])
        self.assertEqual(sold['brokerTransmissions'], 0)

    def test_invalid_last_candidate_rolls_back_funding_not_just_its_own_row(self):
        bad = deepcopy(self.batch)
        bad['results'][-1]['newFits'] = 1
        inference = self.store_batch(bad)
        with self.assertRaisesRegex(ValueError, 'R0_SOURCE_NOT_ORIGINAL_SHADOW'):
            self.runner.advance(self.feed, inference, at(575, 12))
        state = self.runner.portfolio.state()
        self.assertEqual(state['orders'], {})
        self.assertEqual(state['positions'], {})
        self.assertEqual(state['candidates'], {})
        self.assertEqual(state['cash'], '1000000')

    def test_existing_service_accepts_47_row_r0_without_entry_halt(self):
        self.runner.close()
        self.runner = SimpleNamespace(close=lambda: None)
        previous = self.root / 'previous.json'
        previous.write_text(json.dumps(self.previous), encoding='utf-8')
        dummy = self.root / 'dummy.json'
        dummy.write_text('{}', encoding='utf-8')
        configfile = self.root / 'account.json'
        configfile.write_text(json.dumps(self.config), encoding='utf-8')
        folder = self.root / 'capture'
        folder.mkdir()
        payload = {'feed': self.feed, 'selectorEnvelopes': [], 'summary': {
            'snapshots': 2, 'minuteRows': 47 * 35, 'executedSlots': ['09:30'],
            'missedSlots': [], 'lastSourceAtJst': at(575, 8)}}
        argv = ['--session', DAY, '--capture-folder', str(folder), '--plan', str(dummy),
            '--mask', str(dummy), '--dated-master', str(dummy), '--previous-context', str(previous),
            '--runtime-root', str(self.root), '--h235-model-root', str(self.root),
            '--shadow-account-config', str(configfile), '--private-root', str(self.root), '--once']
        with mock.patch.object(service, 'now_jst', return_value=at(575, 12)), \
             mock.patch.object(service.forward, 'FrozenP1Scorer', return_value=market.RecordingScorer()), \
             mock.patch.object(service.h235_module, 'FrozenH235AsOf', return_value=SimpleNamespace()), \
             mock.patch.object(wiring, 'settings', return_value=(self.config, self.arrival)), \
             mock.patch.object(service, 'source_signature', return_value=[('a', 1, 1), ('b', 1, 1)]), \
             mock.patch.object(service, 'run_tick', return_value=(payload, str(dummy))), \
             mock.patch.object(service.received, 'consume_received_feed', return_value=self.inference):
            service.main(argv)
        report = json.loads((self.root / 'pipeline-latest-report.json').read_text(encoding='utf-8'))
        self.assertTrue(report['originalExitShadowConnected'])
        self.assertEqual(report['shadowPortfolio']['buyIntentCount'], 3)
        self.assertFalse(report['shadowPortfolio']['entryPipelineHalted'])
        self.assertFalse(report['realAccountConnected'])
        self.assertFalse(report['orderTransmission'])


if __name__ == '__main__':
    unittest.main()
