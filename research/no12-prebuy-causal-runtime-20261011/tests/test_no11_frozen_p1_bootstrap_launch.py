"""Mocked Windows process ownership tests. Never starts Excel or a broker."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import no11_received_session_bootstrap as b

DAY = '2026-10-26'
NOW = DAY + 'T09:10:00.000+09:00'


@unittest.skipUnless(os.name == 'nt', 'Windows process launcher; offline lifecycle tested on both OSs')
class PairedLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for directory in ('run', 'daily', 'private', 'runtime'):
            (self.root / directory).mkdir()
        self.files = {}
        for key in ('plan', 'mask', 'master', 'previous'):
            path = self.root / (key + '.json')
            path.write_text('{}')
            self.files[key] = str(path)
        self.config = {'sessionDate': DAY, 'dailyRun': str(self.root / 'daily'),
                       'privateRoot': str(self.root / 'private'),
                       'runtimeRoot': str(self.root / 'runtime'),
                       'samples': 2, 'historyBars': 120, 'warmupSeconds': 5}
        self.prepared = {'files': self.files}

    def tearDown(self):
        self.temp.cleanup()

    def test_preflight_then_own_collector_then_consumer_then_acknowledged_close(self):
        process = mock.Mock(pid=4242)
        process.poll.return_value = None
        ready = self.root / 'run' / 'collector-ready.json'
        folder = self.root / 'daily' / ('chart50-shadow-' + DAY + '-091000-4242')
        calls = []

        def spawned(argv, **kwargs):
            calls.append('collector')
            self.assertNotIn('shell', kwargs)
            self.assertEqual(argv[0], 'powershell.exe')
            folder.mkdir()
            ready.write_text(json.dumps({'schemaId': b.READY, 'sessionDate': DAY,
                'processId': 4242, 'captureFolder': str(folder), 'planFile': self.files['plan'],
                'planFileSha256': hashlib.sha256(Path(self.files['plan']).read_bytes()).hexdigest(),
                'productionReady': False, 'orderTransmission': False}))
            return process

        def consumed(argv, **kwargs):
            if '--preflight-only' in argv:
                calls.append('preflight')
                self.assertFalse(ready.exists())
            else:
                calls.append('consumer')
                self.assertEqual(argv[argv.index('--capture-folder') + 1], str(folder))
                self.assertFalse(kwargs['should_stop']())

        def stopped(timeout):
            calls.append('close')
            self.assertTrue((self.root / 'run' / 'collector.stop').exists())
            Path(str(ready) + '.closed.json').write_text(json.dumps({
                'schemaId': b.CLOSED, 'processId': 4242,
                'temporaryWorkbookClosed': True, 'orderTransmission': False}))
            return 0

        process.wait.side_effect = stopped
        with mock.patch.object(b, 'stamp', return_value=NOW), \
             mock.patch.object(b.subprocess, 'Popen', side_effect=spawned), \
             mock.patch.object(b.service, 'main', side_effect=consumed):
            b.launch(self.config, self.prepared, self.root / 'run')
        self.assertEqual(calls, ['preflight', 'collector', 'consumer', 'close'])
        process.kill.assert_not_called()
        process.terminate.assert_not_called()

    def test_bad_private_model_stops_before_collector_creation(self):
        with mock.patch.object(b, 'stamp', return_value=NOW), \
             mock.patch.object(b.service, 'main', side_effect=ValueError('MODEL_MISSING')), \
             mock.patch.object(b.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(ValueError, 'MODEL_MISSING'):
                b.launch(self.config, self.prepared, self.root / 'run')
            spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
