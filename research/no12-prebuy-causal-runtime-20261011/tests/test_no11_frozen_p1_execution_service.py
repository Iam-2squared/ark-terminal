"""Received source -> native V5 -> simulated fill -> original EXIT -> sell fill.

All source prices, private-model substitutes and balances are synthetic.
The test calls the genuine existing State9 and native Capital calculation code.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_observed_execution_shadow as wiring
import no11_received_pipeline_service as service
import no11_h235_asof_forward_shadow as h
import no11_frozen_p1_feature_runtime as features
import test_no11_frozen_p1_rss_state_stream as market
import test_no11_frozen_p1_h235_asof as models
import test_no11_frozen_p1_execution_bundle as fixtures

DAY = fixtures.DAY
at = fixtures.at


class ReceivedExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = features.load_feature_runtime(h.ROOT)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config, self.arrival = fixtures.config(self.root), fixtures.arrival()
        manifest = models.synthetic_models(self.root, None)
        scorer = h.FrozenH235AsOf(self.root, DAY, manifest=manifest)
        self.feed = market.feed(35)
        price = self.feed['rows'][-1]['C']
        row = scorer.score(models.valid_input())
        row.update(decisionAtJst=at(575, 12), raw_reference=price)
        batch = {'schemaId': 'ARK_NO11_H235_ASOF_PRIVATE_RANK_BATCH_V1',
                 'policy': scorer.policy, 'results': [row], 'capitalV5Executed': False,
                 'brokerOrders': 0, 'productionReady': False, 'orderTransmission': False}
        data = h.stable_bytes(batch) + b'\n'
        digest = hashlib.sha256(data).hexdigest()
        (self.root / ('h235-asof-' + digest[:16] + '.json')).write_bytes(data)
        self.inference = {'h235PrivateResultSha256': digest,
                          'p1Session': {'firstEntryCandidates': 1}, 'h235OriginalModelExecutions': 3}
        self.runner = wiring.ExecutionShadow(self.root, self.config, self.arrival,
                                            self.runtime, market.previous(), market.PRIOR)

    def tearDown(self):
        self.runner.close()
        self.temp.cleanup()

    def append_bar(self, m, price):
        r = {'Date': DAY, 'Code': market.CODE, 'Time': '%02d:%02d' % divmod(m, 60),
             'O': price, 'H': price + .2, 'L': price - .2, 'C': price, 'Vo': 100,
             'Va': price * 100, 'knownAtJst': at(m + 1, 8), 'vaProvenance': market.r.VA_SOURCE}
        self.feed['rows'].append(r)
        n = len(self.feed['rows'])
        self.feed['receipt']['approximateMinuteVaRows'] = n
        self.feed['receipt']['proxyReceipt']['validOneMinuteProxyRows'] = n

    def test_received_price_drives_full_shadow_buy_to_original_eod_exit_to_sell(self):
        first = self.runner.advance(self.feed, self.inference, at(575, 12))
        self.assertEqual(first['buyIntentCount'], 1)
        self.assertEqual(first['positionCount'], 0)
        self.append_bar(575, self.feed['rows'][-1]['C'] - .05)
        second = self.runner.advance(self.feed, self.inference, at(576, 12))
        self.assertEqual(second['positionCount'], 1)
        self.assertEqual(second['pendingOrders'], 0)
        self.assertIn(market.CODE, self.runner.streams)
        self.assertEqual(self.runner.streams[market.CODE].trace[-1]['state']['as_of'], 36)
        eod = self.runner.heartbeat(at(920))
        self.assertEqual(eod['sellIntentCount'], 1)
        self.assertEqual(eod['positionCount'], 1)
        self.assertFalse(eod['firstSellFillBuyHalt'])
        self.append_bar(920, self.feed['rows'][-1]['C'] + .5)
        sold = self.runner.advance(self.feed, self.inference, at(921, 12))
        self.assertEqual(sold['positionCount'], 0)
        self.assertTrue(sold['firstSellFillBuyHalt'])
        self.assertEqual(sold['brokerTransmissions'], 0)
        self.assertFalse(sold['observedPriceIsBrokerFill'])
        self.assertFalse(sold['orderTransmission'])

    def test_restart_same_source_cannot_create_second_buy(self):
        self.runner.advance(self.feed, self.inference, at(575, 12))
        self.runner.close()
        self.runner = wiring.ExecutionShadow(self.root, self.config, self.arrival,
                                            self.runtime, market.previous(), market.PRIOR)
        result = self.runner.advance(self.feed, self.inference, at(575, 20))
        self.assertEqual(result['buyIntentCount'], 1)
        self.assertEqual(result['positionCount'], 0)

    def test_no_next_receipt_never_manufactures_buy_fill(self):
        self.runner.advance(self.feed, self.inference, at(575, 12))
        result = self.runner.advance(self.feed, self.inference, at(578))
        self.assertEqual(result['positionCount'], 0)
        self.assertEqual(result['pendingOrders'], 1)

    def test_price_above_reserved_budget_cancels_simulated_buy_without_spending(self):
        self.runner.advance(self.feed, self.inference, at(575, 12))
        self.append_bar(575, self.feed['rows'][-1]['C'] + 10)
        result = self.runner.advance(self.feed, self.inference, at(576, 12))
        self.assertEqual(result['positionCount'], 0)
        self.assertEqual(result['pendingOrders'], 0)
        self.assertEqual(result['cashJpy'], '1000000')

    def test_h235_private_result_tamper_is_not_trusted(self):
        path = next(self.root.glob('h235-asof-*.json'))
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'H235_RESULT_HASH_CHANGED'):
            self.runner.advance(self.feed, self.inference, at(575, 12))
        self.assertEqual(self.runner.summary()['buyIntentCount'], 0)

    def test_held_source_cannot_be_rewritten_on_later_tick(self):
        self.runner.advance(self.feed, self.inference, at(575, 12))
        self.append_bar(575, self.feed['rows'][-1]['C'] - .05)
        self.runner.advance(self.feed, self.inference, at(576, 12))
        self.feed['rows'][0]['Va'] += 1
        with self.assertRaisesRegex(ValueError, 'HELD_SOURCE_CHANGED'):
            self.runner.advance(self.feed, self.inference, at(576, 20))

    def test_existing_service_calls_portfolio_automatically_after_inference(self):
        # Use the actual service entry point, with only external source/model IO mocked.
        self.runner.close()
        self.runner = SimpleNamespace(close=lambda: None)
        previous = self.root / 'previous.json'
        previous.write_text(json.dumps(market.previous()))
        dummy = self.root / 'dummy.json'
        dummy.write_text('{}')
        configfile = self.root / 'account.json'
        configfile.write_text(json.dumps(self.config))
        folder = self.root / 'capture'
        folder.mkdir()
        payload = {'feed': self.feed, 'selectorEnvelopes': [], 'summary': {
            'snapshots': 2, 'minuteRows': 35, 'executedSlots': ['09:30'], 'missedSlots': [],
            'lastSourceAtJst': at(575, 8)}}
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
        report = json.loads((self.root / 'pipeline-latest-report.json').read_text())
        self.assertTrue(report['originalExitShadowConnected'])
        self.assertEqual(report['shadowPortfolio']['buyIntentCount'], 1)
        self.assertFalse(report['realAccountConnected'])
        self.assertFalse(report['orderTransmission'])


if __name__ == '__main__':
    unittest.main()
