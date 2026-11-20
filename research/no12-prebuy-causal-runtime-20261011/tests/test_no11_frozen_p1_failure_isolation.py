"""Original State9/Capital/EXIT code with synthetic data and failed entry paths.

No real RSS, broker, account or original private model weights are used.
"""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_received_failure_isolation as isolation
import no11_observed_execution_shadow as original
import no11_received_pipeline_service as service
import no11_frozen_p1_feature_runtime as features
import no11_h235_asof_forward_shadow as h
import no11_shadow_portfolio as ledger
import test_no11_frozen_p1_execution_service as fixture
import test_no11_frozen_p1_rss_state_stream as market

DAY, at = fixture.DAY, fixture.at


class FailureIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = features.load_feature_runtime(h.ROOT)

    def setUp(self):
        self.f = fixture.ReceivedExecutionTests()
        self.f.runtime = self.runtime
        self.f.setUp()
        self.f.runner.close()
        self.reopen()

    def reopen(self):
        self.f.runner = isolation.ExecutionShadow(self.f.root, self.f.config, self.f.arrival,
            self.runtime, market.previous(), market.PRIOR)
        self.r = self.f.runner

    def tearDown(self):
        self.f.tearDown()

    def fill_buy(self):
        self.r.advance(self.f.feed, self.f.inference, at(575, 12))
        self.f.append_bar(575, self.f.feed['rows'][-1]['C'] - .05)
        result = self.r.advance(self.f.feed, self.f.inference, at(576, 12))
        self.assertEqual(result['positionCount'], 1)

    def failed_inference(self, feed=None, clock=at(577, 12)):
        def fail(): raise ValueError('NO11_H235_MODEL_PREDICTION_NONFINITE')
        return isolation.guarded_inference(self.r, self.f.feed if feed is None else feed,
            fail, clock=lambda: clock, p1_summary=lambda: {'firstEntryCandidates': 1})

    def test_inference_failure_keeps_holdings_and_original_eod_exit(self):
        self.fill_buy()
        summary, paper = self.failed_inference()
        self.assertEqual(summary['status'], 'ENTRY_PIPELINE_HALTED')
        self.assertTrue(paper['entryPipelineHalted'])
        self.assertEqual(paper['positionCount'], 1)
        eod = self.r.heartbeat(at(920))
        self.assertEqual(eod['sellIntentCount'], 1)
        self.assertEqual(eod['positionCount'], 1)
        self.f.append_bar(920, self.f.feed['rows'][-1]['C'] + .5)
        sold = self.r.advance(self.f.feed, {}, at(921, 12))
        self.assertEqual(sold['positionCount'], 0)
        self.assertTrue(sold['firstSellFillBuyHalt'])
        self.assertFalse(sold['orderTransmission'])

    def test_restart_does_not_rescore_or_clear_entry_halt(self):
        self.fill_buy(); self.failed_inference()
        self.r.close(); self.reopen()
        infer = mock.Mock(side_effect=AssertionError('must not score again'))
        summary, paper = isolation.guarded_inference(self.r, self.f.feed, infer,
            clock=lambda: at(577, 20), p1_summary=lambda: {'firstEntryCandidates': 1})
        infer.assert_not_called()
        self.assertTrue(paper['entryPipelineHalted'])
        self.assertEqual(summary['failureCode'], 'NO11_ENTRY_PIPELINE_ALREADY_HALTED')

    def test_invalid_old_feed_cannot_change_mark_quantity_or_cash(self):
        self.fill_buy()
        before = self.r.portfolio.state()
        bad = deepcopy(self.f.feed); bad['rows'][0]['Va'] += 1
        summary, paper = self.failed_inference(bad)
        after = self.r.portfolio.state()
        self.assertEqual(summary['exitStatus'], 'NO_VALID_FEED_CLOCK_ONLY')
        self.assertEqual(after['positions'], before['positions'])
        self.assertEqual(after['cash'], before['cash'])
        self.assertEqual(paper['sellIntentCount'], 0)
        self.assertIn('NO11_EXECUTION_SHADOW_HELD_SOURCE_CHANGED', paper['entryPipelineHaltReasons'])

    def test_known_pending_buy_is_cancelled_only_in_local_simulator(self):
        self.r.advance(self.f.feed, self.f.inference, at(575, 12))
        summary, paper = self.failed_inference(clock=at(575, 20))
        self.assertTrue(paper['entryPipelineHalted'])
        self.assertEqual(paper['positionCount'], 0)
        self.assertEqual(paper['pendingOrders'], 0)
        self.assertEqual(paper['brokerTransmissions'], 0)

    def test_unknown_buy_remains_unresolved_with_reserved_cash(self):
        self.r.advance(self.f.feed, self.f.inference, at(575, 12))
        o = next(iter(self.r.portfolio.state()['orders'].values()))
        update = {'schemaId': ledger.UPDATE, 'eventId': 'c' * 64, 'orderId': o['orderId'],
                  'symbol': o['symbol'], 'side': 'BUY', 'knownAtJst': at(575, 20),
                  'cumulativeQuantity': 0, 'cumulativeValueJpy': '0', 'status': 'UNKNOWN', 'syntheticOnly': True}
        self.r.portfolio.update(update, at(575, 20))
        self.failed_inference(clock=at(576, 12))
        result = self.r.heartbeat(at(920))
        self.assertEqual(self.r.portfolio.state()['orders'][o['orderId']]['status'], 'UNKNOWN')
        self.assertGreater(float(result['reservedCashJpy']), 0)
        self.assertTrue(result['reconciliationBlocked'])

    def test_direct_advance_while_halted_never_calls_capital(self):
        self.r.halt_entry('NO11_TEST_MODEL_FAILURE', at(575, 12))
        with mock.patch.object(self.r.portfolio, 'fund', side_effect=AssertionError('Capital called')) as funded:
            self.r.advance(self.f.feed, {}, at(575, 20))
            funded.assert_not_called()

    def test_interrupt_not_swallowed_or_reclassified_as_success(self):
        infer = mock.Mock(side_effect=KeyboardInterrupt)
        with self.assertRaises(KeyboardInterrupt):
            isolation.guarded_inference(self.r, self.f.feed, infer,
                clock=lambda: at(575, 12), p1_summary=lambda: {})
        self.assertFalse(self.r.entry_halted)

    def test_ledger_failure_is_fatal_not_an_unrecorded_allow(self):
        with mock.patch.object(self.r.portfolio, '_event', side_effect=sqlite3.OperationalError('disk failure')):
            with self.assertRaises(sqlite3.OperationalError):
                self.failed_inference(clock=at(575, 12))

    def test_exception_private_details_redacted_and_halt_is_idempotent(self):
        self.r.halt_entry('broker data private details', at(575, 12))
        before = self.r.portfolio.summary()['events']
        self.r.halt_entry('broker data private details', at(575, 20))
        self.assertEqual(self.r.portfolio.summary()['events'], before)
        self.assertEqual(self.r.summary()['entryPipelineHaltReasons'], ['NO11_ENTRY_PIPELINE_FAILURE'])
        self.assertEqual(isolation.reason_code(ValueError('/private/secret')), 'NO11_ENTRY_PIPELINE_FAILURE')

    def run_service(self, *, inference_error=None, source_error=None, clock=at(577, 12),
                    once=True, after_sleep=None, should_stop=None):
        self.r.close()
        root = self.f.root
        previous = root / 'previous.json'; previous.write_text(json.dumps(market.previous()))
        dummy = root / 'dummy.json'; dummy.write_text('{}')
        account = root / 'account.json'; account.write_text(json.dumps(self.f.config))
        folder = root / 'capture'; folder.mkdir(exist_ok=True)
        payload = {'feed': self.f.feed, 'selectorEnvelopes': [], 'summary': {
            'snapshots': 2, 'minuteRows': len(self.f.feed['rows']), 'executedSlots': 1, 'missedSlots': 0,
            'lastSourceAtJst': at(575, 8)}}
        argv = ['--session', DAY, '--capture-folder', str(folder), '--plan', str(dummy),
            '--mask', str(dummy), '--dated-master', str(dummy), '--previous-context', str(previous),
            '--runtime-root', str(root), '--h235-model-root', str(root),
            '--shadow-account-config', str(account), '--private-root', str(root)]
        if once: argv += ['--once']
        clock_fn = clock if callable(clock) else lambda: clock
        try:
            with mock.patch.object(service, 'now_jst', side_effect=clock_fn), \
                 mock.patch.object(service.forward, 'FrozenP1Scorer', return_value=market.RecordingScorer()), \
                 mock.patch.object(service.h235_module, 'FrozenH235AsOf', return_value=SimpleNamespace()), \
                 mock.patch.object(original, 'settings', return_value=(self.f.config, self.f.arrival)), \
                 mock.patch.object(service, 'source_signature', return_value=[('a', 1, 1), ('b', 1, 1)]), \
                 mock.patch.object(service, 'run_tick', side_effect=source_error,
                                   return_value=(payload, str(dummy))), \
                 mock.patch.object(service.received, 'consume_received_feed', side_effect=inference_error,
                                   return_value=self.f.inference), \
                 mock.patch.object(service.time, 'sleep', side_effect=after_sleep):
                service.main(argv, should_stop=should_stop)
        finally:
            self.reopen()

    def test_actual_service_reports_inference_failure_as_degraded_exit_only(self):
        self.fill_buy()
        self.run_service(inference_error=ValueError('NO11_H235_MODEL_PREDICTION_NONFINITE'))
        report = json.loads((self.f.root / 'pipeline-latest-report.json').read_text())
        self.assertEqual(report['inference']['status'], 'ENTRY_PIPELINE_HALTED')
        self.assertEqual(report['shadowPortfolio']['positionCount'], 1)
        self.assertTrue(report['shadowPortfolio']['entryPipelineHalted'])

    def test_source_failure_does_not_prevent_clock_only_eod_intent(self):
        self.fill_buy()
        self.run_service(source_error=ValueError('NO11_PIPELINE_CAPTURE_HASH_MISMATCH'), clock=at(920))
        report = json.loads((self.f.root / 'pipeline-source-failure.json').read_text())
        self.assertFalse(report['structuralExitSourceAvailable'])
        self.assertEqual(report['shadowPortfolio']['sellIntentCount'], 1)
        self.assertEqual(report['shadowPortfolio']['positionCount'], 1)

    def test_supervisor_relay_error_is_persisted_without_disabling_exit_clock(self):
        self.fill_buy()
        def broken_relay(): raise ValueError('NO11_RECOVERY_SOURCE_REMOVED')
        self.run_service(clock=at(920), should_stop=broken_relay)
        self.assertTrue(self.r.entry_halted)
        self.assertEqual(self.r.summary()['sellIntentCount'], 1)
        self.assertEqual(self.r.summary()['positionCount'], 1)

    def test_stale_source_loop_stays_alive_for_eod_without_new_model_call(self):
        self.fill_buy()
        current = [at(578, 12)]
        def slept(_): current[0] = at(920)
        self.run_service(clock=lambda: current[0], once=False, after_sleep=slept,
                         should_stop=lambda: current[0] == at(920))
        self.assertTrue(self.r.entry_halted)
        self.assertEqual(self.r.summary()['sellIntentCount'], 1)
        self.assertEqual(self.r.summary()['positionCount'], 1)


if __name__ == '__main__':unittest.main()
