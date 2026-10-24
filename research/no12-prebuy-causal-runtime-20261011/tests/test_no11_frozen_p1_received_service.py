"""Continuous consumer timing/locking and real State9 -> synthetic H235 tests.

No private weights or real brokerage, account or market data is used here.
"""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest

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


if __name__ == '__main__':
    unittest.main()
