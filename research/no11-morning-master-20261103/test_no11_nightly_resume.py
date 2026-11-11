"""Real filesystem/process interruption tests; callbacks never access Excel."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_nightly_resume as n


class NightlyResumeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / 'jobs' / '2026-11-06_2026-11-09'
        self.pointer = self.root / '2026-11-09.json'
        self.counts = {'capture': 0, 'publish': 0, 'quiet': 0}
        self.identity = {'sessionDate': '2026-11-09', 'source': 'fixed', 'orderTransmission': False}
        self.fail_capture = False
        self.fail_publish = False
        self.crash_after_publish = False
        self.busy = False

    def capture(self, log):
        self.counts['capture'] += 1
        log.write_bytes(b'IMMUTABLE_NATIVE_DATA_LOG\n')
        if self.fail_capture:
            raise RuntimeError('mock disconnect')

    def publish(self, log):
        self.counts['publish'] += 1
        if self.fail_publish:
            raise RuntimeError('mock publication interruption')
        self.pointer.write_bytes(n.encode({'sessionDate': '2026-11-09',
                                           'nightlyLogSha256': n.digest(log.read_bytes())}))
        if self.crash_after_publish:
            raise KeyboardInterrupt('mock abrupt crash after publication')

    def validate(self, ptr, log_sha):
        obj = n.read(ptr)
        n.need(obj['sessionDate'] == '2026-11-09', 'MOCK_WRONG_DATE')
        if log_sha is not None:
            n.need(obj['nightlyLogSha256'] == log_sha, 'MOCK_WRONG_LINEAGE')

    def quiet(self):
        self.counts['quiet'] += 1
        n.need(not self.busy, 'MOCK_WORKER_STILL_ALIVE')

    def pipeline(self):
        return n.Pipeline(self.work, self.identity, self.pointer, self.capture,
                          self.publish, self.validate, self.quiet)

    def test_complete_and_duplicate_invocation_does_not_repeat(self):
        self.pipeline().run()
        self.pipeline().run()
        self.assertEqual(self.counts['capture'], 1)
        self.assertEqual(self.counts['publish'], 1)
        self.assertEqual(n.checkpoint(self.work / 'checkpoint.json')['phase'], 'COMPLETE')

    def test_capture_interruption_preserves_attempt_log_then_resumes(self):
        self.fail_capture = True
        with self.assertRaises(RuntimeError):
            self.pipeline().run()
        old = list(self.work.glob('capture-*.log'))
        self.assertEqual(len(old), 1)
        content = old[0].read_bytes()
        self.assertEqual(n.checkpoint(self.work / 'checkpoint.json')['phase'], 'CAPTURING')
        self.fail_capture = False
        self.pipeline().run()
        self.assertEqual(old[0].read_bytes(), content)
        self.assertEqual(len(list(self.work.glob('capture-*.log'))), 2)

    def test_publish_failure_reuses_capture_without_recapture(self):
        self.fail_publish = True
        with self.assertRaises(RuntimeError):
            self.pipeline().run()
        self.assertEqual(n.checkpoint(self.work / 'checkpoint.json')['phase'], 'PUBLISHING')
        self.fail_publish = False
        self.pipeline().run()
        self.assertEqual(self.counts['capture'], 1)
        self.assertEqual(self.counts['publish'], 2)

    def test_crash_after_pointer_publish_adopts_verified_pointer(self):
        self.crash_after_publish = True
        with self.assertRaises(KeyboardInterrupt):
            self.pipeline().run()
        self.crash_after_publish = False
        self.pipeline().run()
        self.assertEqual(self.counts['capture'], 1)
        self.assertEqual(self.counts['publish'], 1)
        self.assertEqual(n.checkpoint(self.work / 'checkpoint.json')['phase'], 'COMPLETE')

    def test_completed_pointer_disappears_does_not_recollect(self):
        self.pipeline().run()
        self.pointer.unlink()
        with self.assertRaisesRegex(ValueError, 'COMPLETED_POINTER_MISSING'):
            self.pipeline().run()
        self.assertEqual(self.counts['capture'], 1)

    def test_changed_completed_pointer_is_rejected(self):
        self.pipeline().run()
        obj = n.read(self.pointer)
        obj['unexpected'] = 1
        self.pointer.write_bytes(n.encode(obj))
        with self.assertRaisesRegex(ValueError, 'COMPLETED_POINTER_CHANGED'):
            self.pipeline().run()

    def test_corrupt_checkpoint_is_not_reset(self):
        self.pipeline().run()
        p = self.work / 'checkpoint.json'
        raw = p.read_bytes().replace(b'COMPLETE', b'CAPTURED')
        p.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_CORRUPTED'):
            self.pipeline().run()
        self.assertEqual(p.read_bytes(), raw)

    def test_input_or_code_identity_change_requires_review(self):
        self.pipeline().run()
        self.identity['source'] = 'new code'
        with self.assertRaisesRegex(ValueError, 'INPUT_OR_CODE_CHANGED'):
            self.pipeline().run()

    def test_modified_capture_log_blocks_publish(self):
        self.fail_publish = True
        with self.assertRaises(RuntimeError):
            self.pipeline().run()
        log = next(self.work.glob('capture-*.log'))
        log.write_bytes(b'corrupt')
        self.fail_publish = False
        with self.assertRaisesRegex(ValueError, 'CAPTURE_LOG_CHANGED'):
            self.pipeline().run()
        self.assertFalse(self.pointer.exists())

    def test_old_worker_blocks_without_starting_new_child(self):
        self.busy = True
        with self.assertRaisesRegex(ValueError, 'WORKER_STILL_ALIVE'):
            self.pipeline().run()
        self.assertEqual(self.counts['capture'], 0)
        self.assertFalse((self.work / 'checkpoint.json').exists())

    def test_atomic_replace_failure_retains_last_good_checkpoint(self):
        p = self.root / 'atomic.json'
        n.atomic(p, {'value': 1})
        before = p.read_bytes()
        with patch.object(n.os, 'replace', side_effect=OSError('disk write failed')):
            with self.assertRaises(OSError):
                n.atomic(p, {'value': 2})
        self.assertEqual(p.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.checkpoint-*')), [])

    def test_os_lock_contention_and_reacquire_after_process_death(self):
        lock = self.root / 'exclusive.lock'
        code = ('import sys,time;from pathlib import Path;sys.path.insert(0,sys.argv[1]);'
                'import no11_nightly_resume as n;'
                '\nwith n.exclusive(Path(sys.argv[2])):\n print("LOCKED",flush=True);time.sleep(30)')
        child = subprocess.Popen([sys.executable, '-u', '-c', code,
                                  str(Path(n.__file__).parent), str(lock)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'LOCKED')
            with self.assertRaisesRegex(ValueError, 'ALREADY_RUNNING'):
                with n.exclusive(lock):
                    self.fail('lock incorrectly acquired')
        finally:
            child.kill()
            child.communicate(timeout=10)
        with n.exclusive(lock):
            self.assertTrue(lock.exists())
        self.assertTrue(lock.exists(), 'persistent lock file must not be deleted')

    def test_wrong_date_existing_pointer_is_not_adopted(self):
        self.pointer.write_bytes(n.encode({'sessionDate': '2026-11-06'}))
        with self.assertRaisesRegex(ValueError, 'WRONG_DATE'):
            self.pipeline().run()
        self.assertEqual(self.counts['capture'], 0)

    def test_data_only_entrypoint_has_no_trade_command(self):
        source = Path(n.__file__).read_text(encoding='utf-8')
        self.assertNotIn("'-Mode', 'Trade'", source)
        self.assertNotIn('-IApproveOrdersForToday', source)
        self.assertNotIn('Stop-Process', source)
        self.assertNotIn('RssStockOrder(', source)

if __name__ == '__main__':
    unittest.main(verbosity=2)
