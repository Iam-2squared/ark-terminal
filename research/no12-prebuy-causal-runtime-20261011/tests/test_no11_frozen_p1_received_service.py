"""Continuous consumer timing/locking and real State9 -> synthetic H235 tests.

No private weights or real brokerage, account or market data is used here.
"""
from copy import deepcopy
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_received_pipeline_service as service
import no11_rss_state9_p1_runner as stream
import no11_frozen_p1_feature_runtime as features
import no11_p1_forward_shadow as forward
import no11_h235_asof_forward_shadow as h235
import test_no11_p1_forward_shadow as base
import test_no11_frozen_p1_rss_state_stream as rss
import test_no11_frozen_p1_h235_asof as model_fixture
import no11_received_failure_isolation as isolation
import no11_broker_execution_service as broker_module


class ProcessingClockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.scorer = base.FakeScorer()
        self.now = base.at('09:31:20')
        self.p1 = service.ProcessingTimedP1(self.root / 'p1.sqlite', self.scorer,
                                            clock=lambda: self.now)
        self.p1.register_selector(base.selector())

    def tearDown(self):
        self.p1.close()
        self.temp.cleanup()

    def test_records_real_processing_time_without_mutating_source_clock(self):
        source = base.feature(value=.8)
        original = deepcopy(source)
        result = self.p1.evaluate(source)
        self.assertEqual(result['status'], 'FIRST_ENTRY_CANDIDATE')
        self.assertEqual(result['evaluatedAtJst'], self.now)
        self.assertEqual(source, original)
        self.assertFalse(result['orderTransmission'])
        self.assertFalse(result['orderAuthorized'])

    def test_completed_evaluation_replays_after_restart_without_rescoring(self):
        source = base.feature(value=.8)
        first = self.p1.evaluate(source)
        self.p1.close()
        self.now = base.at('10:20:00')
        self.p1 = service.ProcessingTimedP1(self.root / 'p1.sqlite', self.scorer,
                                            clock=lambda: self.now)
        again = self.p1.evaluate(source)
        self.assertTrue(again['idempotentReplay'])
        self.assertEqual(again['evaluatedAtJst'], first['evaluatedAtJst'])
        self.assertEqual(self.scorer.calls, 1)
        self.assertEqual(self.p1.summary()['firstEntryCandidates'], 1)

    def test_unprocessed_stale_bar_cannot_create_a_retroactive_entry(self):
        self.now = base.at('10:00:20')
        stale = self.p1.evaluate(base.feature(value=.9))
        self.assertEqual(stale['status'], 'STALE_NOT_RETROACTIVELY_SCORED')
        self.assertEqual(self.scorer.calls, 0)
        current = self.p1.evaluate(base.feature('10:00:00', .8))
        self.assertEqual(current['status'], 'FIRST_ENTRY_CANDIDATE')
        self.assertEqual(self.scorer.calls, 1)

    def test_model_failure_pending_record_cannot_resurrect_after_long_downtime(self):
        self.scorer.error = True
        event = base.feature(value=.9)
        with self.assertRaisesRegex(ValueError, 'TEST_INJECTED_SCORE_FAILURE'):
            self.p1.evaluate(event)
        self.assertEqual(self.p1.summary()['firstEntryCandidates'], 0)
        self.scorer.error = False
        self.now = base.at('10:00:00')
        result = self.p1.evaluate(event)
        self.assertEqual(result['status'], 'STALE_NOT_RETROACTIVELY_SCORED')
        self.assertEqual(self.p1.summary()['firstEntryCandidates'], 0)
        self.assertEqual(self.scorer.calls, 1)

    def test_changed_old_source_or_future_receipt_blocks(self):
        event = base.feature(value=.5)
        self.p1.evaluate(event)
        event['numeric'][1] = 1.2
        with self.assertRaisesRegex(ValueError, 'REPLAY_SOURCE_CHANGED'):
            self.p1.evaluate(event)
        with self.assertRaisesRegex(ValueError, 'FEATURE_RECEIPT_FROM_FUTURE'):
            self.p1.evaluate(base.feature('09:32:00', .8))

    def test_stale_result_is_permanently_idempotent(self):
        self.now = base.at('10:00:00')
        event = base.feature(value=.9)
        self.p1.evaluate(event)
        self.now = base.at('10:01:00')
        replay = self.p1.evaluate(event)
        self.assertTrue(replay['idempotentReplay'])
        self.assertEqual(replay['status'], 'STALE_NOT_RETROACTIVELY_SCORED')
        self.assertEqual(self.scorer.calls, 0)


class LocalDurabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_single_service_lock_and_clean_release(self):
        with service.exclusive_service(self.root):
            with self.assertRaisesRegex(ValueError, 'ALREADY_RUNNING'):
                with service.exclusive_service(self.root):
                    self.fail('Second service obtained the same lock')
        with service.exclusive_service(self.root):
            self.assertTrue((self.root / 'received-pipeline.lock').is_file())

    def test_checkpoint_pointer_detects_changed_bytes(self):
        tick = self.root / 'pipeline-tick-fixture.json'
        digest = service.atomic_private(tick, {'state': {}, 'orderTransmission': False})
        service.atomic_private(self.root / 'pipeline-current.json', {
            'schemaId': 'ARK_NO11_PIPELINE_POINTER_V1', 'privateTick': str(tick),
            'sha256': digest, 'orderTransmission': False})
        self.assertEqual(service.load_checkpoint(self.root), str(tick))
        tick.write_text('{}\n')
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_BYTES_CHANGED'):
            service.load_checkpoint(self.root)

    def test_atomic_pointer_update_leaves_no_half_written_temp(self):
        path = self.root / 'atomic.json'
        service.atomic_private(path, {'n': 1})
        service.atomic_private(path, {'n': 2})
        self.assertEqual(json.loads(path.read_text()), {'n': 2})
        self.assertEqual(list(self.root.glob('*.tmp-*')), [])

    def test_repo_path_never_used_for_private_records(self):
        with self.assertRaisesRegex(ValueError, 'PRIVATE_PATH_UNSAFE'):
            service.private_path(forward.REPO, True)


class ActualState9ToR0(unittest.TestCase):
    def test_processing_time_p1_feeds_real_state_trace_to_native_h235_math(self):
        runtime = features.load_feature_runtime(forward.REPO)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = model_fixture.synthetic_models(root, None)
            h = h235.FrozenH235AsOf(root, rss.DAY, manifest=manifest)
            scorer = rss.RecordingScorer()
            p1 = service.ProcessingTimedP1(root / 'p1.sqlite', scorer,
                                           clock=lambda: rss.at(571, 20))
            try:
                result = stream.consume_received_feed(runtime, p1, rss.feed(31),
                    rss.selectors(), rss.previous(), previous_session=rss.PRIOR,
                    through=rss.at(571, 25), h235=h, h235_store=root)
                self.assertEqual(result['p1Session']['firstEntryCandidates'], 1)
                self.assertEqual(result['h235OriginalModelExecutions'], 3)
                self.assertEqual(result['counts']['h235R0Candidates'], 1)
                self.assertFalse(result['capitalExecuted'])
                self.assertFalse(result['orderTransmission'])
                data = json.loads(next(root.glob('h235-asof-*.json')).read_text())
                self.assertEqual(data['results'][0]['decisionAtJst'], rss.at(571, 20))
                self.assertEqual(data['results'][0]['ML'], 1.0)
            finally:
                p1.close()


class MockExecutionController:
    """An in-memory lifecycle witness. It has no transport or Excel member."""
    def __init__(self, *, broker=False, mode='OBSERVE_ONLY', evidence='OFFLINE_REPLAY'):
        self.broker, self.mode, self.evidence = broker, mode, evidence
        self.entry_halted, self.closed = False, False
        self.source_current = True
        self.failures, self.calls = {}, []
        self.eod = False

    def _called(self, name, at=None):
        self.calls.append((name, at))
        if name in self.failures:
            raise self.failures[name]

    def _report(self):
        return {'entryPipelineHalted': self.entry_halted, 'positionCount': 1,
                'buyIntentCount': 0, 'sellIntentCount': int(self.eod),
                'mode': self.mode, 'evidenceMode': self.evidence,
                'sourceCurrent': self.source_current, 'brokerConnectionPhysicallyVerified': False,
                'productionReady': False, 'orderTransmission': self.broker and self.mode == 'LIVE'}

    def halt_entry(self, reason, at):
        self._called('halt_entry', at)
        self.entry_halted = True

    def heartbeat(self, at):
        self._called('heartbeat', at)
        self.eod = self.eod or at[11:16] >= '15:20'
        return self._report()

    def advance(self, feed, inference, at):
        self._called('advance', at)
        return self._report()

    def exit_only(self, feed, at):
        self._called('exit_only', at)
        self.eod = self.eod or at[11:16] >= '15:20'
        return self._report()

    def summary(self):
        self._called('summary')
        return self._report()

    def close(self):
        self._called('close')
        self.closed = True


class BrokerPipelineIntegrationTests(unittest.TestCase):
    """Exercise main() with lifecycle mocks; real transport is never reachable."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.folder = self.root / 'capture'
        self.folder.mkdir()
        self.dummy = self.root / 'dummy.json'
        self.dummy.write_text('{}')
        self.previous = self.root / 'previous.json'
        self.previous.write_text(json.dumps(rss.previous()))
        self.shadow = MockExecutionController()
        self.broker = MockExecutionController(broker=True)
        self.engine = mock.Mock()
        self.engine.summary.return_value = {'firstEntryCandidates': 2}
        self.inference = {'p1Session': {'firstEntryCandidates': 2}, 'h235OriginalModelExecutions': 3}
        self.payload = {'feed': {'rows': []}, 'selectorEnvelopes': [], 'summary': {
            'snapshots': 2, 'minuteRows': 31, 'executedSlots': 1, 'missedSlots': 0,
            'lastSourceAtJst': rss.at(575, 8)}}
        self.now = rss.at(575, 12)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.addCleanup(self.temp.cleanup)
        self.stack.enter_context(mock.patch.object(service, 'now_jst', side_effect=lambda: self.now))
        self.stack.enter_context(mock.patch.object(service.features, 'load_feature_runtime', return_value=object()))
        self.stack.enter_context(mock.patch.object(service.forward, 'FrozenP1Scorer', return_value=object()))
        self.stack.enter_context(mock.patch.object(service.h235_module, 'FrozenH235AsOf', return_value=object()))
        self.p1_ctor = self.stack.enter_context(mock.patch.object(service, 'ProcessingTimedP1', return_value=self.engine))
        self.stack.enter_context(mock.patch.object(service.received, 'previous_cash_session', return_value=rss.PRIOR))
        self.stack.enter_context(mock.patch.object(service, 'source_signature', return_value=[('a', 1, 1), ('b', 1, 1)]))
        self.tick = self.stack.enter_context(mock.patch.object(service, 'run_tick', return_value=(self.payload, str(self.dummy))))
        self.infer = self.stack.enter_context(mock.patch.object(service.received, 'consume_received_feed', return_value=self.inference))
        self.stack.enter_context(mock.patch.object(isolation, 'settings', return_value=({}, {})))
        self.shadow_ctor = self.stack.enter_context(mock.patch.object(isolation, 'ExecutionShadow', return_value=self.shadow))
        self.settings = self.stack.enter_context(mock.patch.object(broker_module, 'settings',
            side_effect=lambda *a, **k: ({'transport': {'mode': self.broker.mode}}, {})))
        self.broker_ctor = self.stack.enter_context(mock.patch.object(broker_module, 'BrokerExecution', return_value=self.broker))
        # A broken test must never fall through to a real child process or I/O
        # boundary. Lifecycle mocks above cover every authorized test path.
        self.process = self.stack.enter_context(mock.patch.object(service.subprocess, 'run',
            side_effect=AssertionError('NO_SUBPROCESS_IN_PIPELINE_TEST')))

    def run_service(self, *, shadow=False, broker=False, readonly=False, preflight=False, should_stop=None):
        args = ['--session', rss.DAY, '--capture-folder', str(self.folder),
                '--plan', str(self.dummy), '--mask', str(self.dummy), '--dated-master', str(self.dummy),
                '--previous-context', str(self.previous), '--runtime-root', str(self.root),
                '--h235-model-root', str(self.root), '--private-root', str(self.root), '--once']
        if shadow:
            args += ['--shadow-account-config', str(self.dummy)]
        if broker:
            args += ['--broker-execution-config', str(self.dummy)]
        if readonly:
            args += ['--broker-execution-readonly']
        if preflight:
            args += ['--preflight-only']
        output = io.StringIO()
        with redirect_stdout(output):
            service.main(args, should_stop=should_stop)
        self.process.assert_not_called()
        return output.getvalue()

    def report(self, filename='pipeline-latest-report.json'):
        return json.loads((self.root / filename).read_text())

    def test_default_service_has_no_optional_controller_or_transmission(self):
        output = self.run_service()
        self.shadow_ctor.assert_not_called()
        self.broker_ctor.assert_not_called()
        self.infer.assert_called_once()
        self.engine.close.assert_called_once()
        report = self.report()
        self.assertIsNone(report['brokerExecution'])
        self.assertFalse(report['realAccountConnected'])
        self.assertFalse(report['exitConnected'])
        self.assertFalse(report['orderTransmission'])
        self.assertIn('ORDER_TRANSMISSION=False', output)

    def test_readonly_preflight_passes_flag_and_never_initializes_controllers(self):
        output = self.run_service(broker=True, readonly=True, preflight=True)
        self.assertTrue(self.settings.call_args.kwargs['read_only'])
        self.p1_ctor.assert_not_called()
        self.broker_ctor.assert_not_called()
        report = json.loads(output)
        self.assertEqual(report['brokerTransportMode'], 'OBSERVE_ONLY')
        self.assertFalse(report['orderTransmission'])

    def test_readonly_launch_rejects_live_even_if_adapter_settings_ignore_flag(self):
        self.broker.mode = 'LIVE'  # in-memory malicious adapter result only
        with self.assertRaisesRegex(ValueError, 'READONLY_BROKER_TRANSPORT_REQUIRED'):
            self.run_service(broker=True, readonly=True, preflight=True)
        self.broker_ctor.assert_not_called()
        self.p1_ctor.assert_not_called()

    def test_broker_only_inference_failure_is_degraded_and_keeps_exit(self):
        self.infer.side_effect = ValueError('NO11_H235_MODEL_PREDICTION_NONFINITE')
        output = self.run_service(broker=True)
        self.assertTrue(self.broker.entry_halted)
        self.assertIn('exit_only', [call[0] for call in self.broker.calls])
        self.assertNotIn('advance', [call[0] for call in self.broker.calls])
        self.assertEqual(self.report()['inference']['status'], 'ENTRY_PIPELINE_HALTED')
        self.assertIn('DEGRADED_EXIT_ONLY', output)

    def test_persisted_broker_only_halt_never_rescores_on_restart(self):
        self.broker.entry_halted = True
        self.run_service(broker=True)
        self.infer.assert_not_called()
        self.assertIn('exit_only', [call[0] for call in self.broker.calls])
        self.assertEqual(self.report()['inference']['failureCode'], 'NO11_ENTRY_PIPELINE_ALREADY_HALTED')

    def test_shared_model_failure_halts_both_paths_and_keeps_both_held_exits(self):
        self.infer.side_effect = ValueError('NO11_H235_MODEL_PREDICTION_NONFINITE')
        self.run_service(shadow=True, broker=True)
        for controller in (self.shadow, self.broker):
            self.assertTrue(controller.entry_halted)
            self.assertIn('exit_only', [call[0] for call in controller.calls])
            self.assertTrue(controller.closed)
        self.assertTrue(self.report()['shadowPortfolio']['entryPipelineHalted'])
        self.assertTrue(self.report()['brokerExecution']['entryPipelineHalted'])

    def test_broker_advance_failure_halts_shadow_after_its_successful_entry_pass(self):
        self.broker.failures['advance'] = ValueError('NO11_BROKER_SERVICE_HELD_SOURCE_CHANGED')
        self.run_service(shadow=True, broker=True)
        self.assertTrue(self.shadow.entry_halted)
        self.assertTrue(self.broker.entry_halted)
        self.assertIn('advance', [call[0] for call in self.shadow.calls])
        self.assertIn('exit_only', [call[0] for call in self.shadow.calls])
        self.assertEqual(self.report()['inference']['status'], 'ENTRY_PIPELINE_HALTED')

    def test_source_failure_halts_both_and_preserves_eod_without_inference(self):
        self.now = rss.at(920)
        self.tick.side_effect = ValueError('NO11_PIPELINE_CAPTURE_HASH_MISMATCH')
        self.run_service(shadow=True, broker=True)
        self.infer.assert_not_called()
        report = self.report('pipeline-source-failure.json')
        self.assertFalse(report['structuralExitSourceAvailable'])
        for name in ('shadowPortfolio', 'brokerExecution'):
            self.assertTrue(report[name]['entryPipelineHalted'])
            self.assertEqual(report[name]['sellIntentCount'], 1)
            self.assertEqual(report[name]['positionCount'], 1)

    def test_invalid_exit_source_falls_back_to_clock_only_eod_for_both(self):
        self.now = rss.at(920)
        self.infer.side_effect = ValueError('NO11_H235_MODEL_PREDICTION_NONFINITE')
        self.shadow.failures['exit_only'] = ValueError('NO11_EXECUTION_SHADOW_HELD_SOURCE_CHANGED')
        self.broker.failures['exit_only'] = ValueError('NO11_BROKER_SERVICE_HELD_SOURCE_CHANGED')
        self.run_service(shadow=True, broker=True)
        for controller in (self.shadow, self.broker):
            self.assertTrue(controller.entry_halted)
            self.assertTrue(controller.eod)
        self.assertEqual(self.report()['brokerExecution']['sellIntentCount'], 1)

    def test_failed_halt_still_attempts_other_ledger_halt_and_is_fatal(self):
        self.tick.side_effect = ValueError('NO11_PIPELINE_CAPTURE_HASH_MISMATCH')
        self.shadow.failures['halt_entry'] = sqlite3.OperationalError('fixture disk fault')
        with self.assertRaises(sqlite3.OperationalError):
            self.run_service(shadow=True, broker=True)
        self.assertTrue(self.broker.entry_halted)
        self.assertTrue(self.shadow.closed)
        self.assertTrue(self.broker.closed)
        self.engine.close.assert_called_once()

    def test_one_failed_clock_still_gives_other_held_position_its_eod_tick(self):
        self.now = rss.at(920)
        self.shadow.failures['heartbeat'] = ValueError('NO11_TEST_SHADOW_CLOCK_FAILURE')
        with self.assertRaisesRegex(ValueError, 'NO11_TEST_SHADOW_CLOCK_FAILURE'):
            self.run_service(shadow=True, broker=True)
        self.assertTrue(self.broker.eod)
        self.assertTrue(self.broker.entry_halted)
        self.assertTrue(self.broker.closed)

    def test_partial_controller_initialization_closes_completed_resources(self):
        self.broker_ctor.side_effect = ValueError('NO11_TEST_BROKER_INIT_FAILURE')
        with self.assertRaisesRegex(ValueError, 'NO11_TEST_BROKER_INIT_FAILURE'):
            self.run_service(shadow=True, broker=True)
        self.assertTrue(self.shadow.closed)
        self.engine.close.assert_called_once()
        self.assertFalse(self.broker.closed)  # constructor never returned it

    def test_final_report_error_does_not_skip_any_controller_or_engine_close(self):
        self.shadow.failures['summary'] = ValueError('NO11_TEST_FINAL_REPORT_FAILURE')
        with self.assertRaisesRegex(ValueError, 'NO11_TEST_FINAL_REPORT_FAILURE'):
            self.run_service(shadow=True, broker=True)
        self.assertTrue(self.shadow.closed)
        self.assertTrue(self.broker.closed)
        self.engine.close.assert_called_once()

    def test_observed_account_and_transport_flags_do_not_claim_physical_verification(self):
        self.broker.evidence = 'BROKER_OBSERVATION'
        self.run_service(broker=True)
        report = self.report()
        self.assertTrue(report['realAccountConnected'])
        self.assertTrue(report['exitConnected'])
        self.assertFalse(report['brokerConnectionPhysicallyVerified'])
        self.assertFalse(report['orderTransmission'])
        self.assertEqual(report['brokerTransportMode'], 'OBSERVE_ONLY')
        self.broker.source_current = False
        self.assertFalse(service.broker_report_flags(self.broker._report())['realAccountConnected'])
        self.broker.source_current, self.broker.evidence = True, 'OFFLINE_REPLAY'
        self.assertFalse(service.broker_report_flags(self.broker._report())['realAccountConnected'])

    def test_explicit_live_mock_report_is_not_mislabeled_order_off(self):
        self.broker.mode, self.broker.evidence = 'LIVE', 'BROKER_OBSERVATION'
        output = self.run_service(broker=True)
        self.assertTrue(self.report()['orderTransmission'])
        self.assertIn('ORDER_TRANSMISSION=True', output)
        self.process.assert_not_called()


class PartialP1InitializationTests(unittest.TestCase):
    def test_processing_table_failure_closes_partially_initialized_database(self):
        db = mock.Mock()
        db.execute.side_effect = sqlite3.OperationalError('fixture processing table failure')

        def opened(obj, database, scorer):
            obj.db = db

        with mock.patch.object(forward.ForwardP1Session, '__init__', opened), \
             self.assertRaises(sqlite3.OperationalError):
            service.ProcessingTimedP1('unused.sqlite', object())
        db.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
