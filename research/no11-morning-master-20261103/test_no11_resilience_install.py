import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_no11_week_resilience as i
import no11_nightly_resume as n

HERE = Path(__file__).resolve().parent

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.store = root / 'unified-launcher'
        (self.store / 'oneclick').mkdir(parents=True)
        self.white = self.store / 'oneclick/Start-No11OneClick.ps1'
        self.white.write_bytes(b'WHITE CUSTOM UI MUST NOT CHANGE\r\n')
        self.engine = root / 'engine'
        (self.engine / 'windows').mkdir(parents=True)
        self.nightly = self.engine / 'windows/Run-No11NightlyCycle.ps1'
        self.nightly.write_bytes((HERE / 'Run-No11NightlyCycle.ps1').read_bytes())
        self.bridge = root / 'launcher_automatic_bridge_v4.py'
        self.bridge.write_bytes((HERE / 'launcher_automatic_bridge_v4.py').read_bytes())
        self.probe = root / 'Prepare-No11AutomaticLiveTransportV3.ps1'
        self.probe.write_bytes((HERE / 'Prepare-No11AutomaticLiveTransportV3.ps1').read_bytes())
        self.settings = self.store / 'settings.json'
        self.settings.write_text(json.dumps({'sameDayApprovalRequired': True,
            'automaticOrderAuthorization': False, 'orderTransmission': False,
            'normalMaxPositions': 3}), encoding='utf-8')
        self.binding = self.store / 'automatic-inputs.json'
        self.binding.write_bytes(n.encode({'schemaId': 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
            'orderTransmission': False, 'engine': str(self.engine), 'settings': str(self.settings),
            'bridge': str(self.bridge), 'bridgeSha256': n.digest(self.bridge.read_bytes()),
            'transportProbe': str(self.probe), 'transportProbeSha256': n.digest(self.probe.read_bytes())}))
        self.before = {p: p.read_bytes() for p in (self.white, self.probe, self.binding, self.bridge, self.nightly)}
        self.addCleanup(patch.stopall)
        self.gate = patch.object(i, 'quiet', return_value=None).start()
        if os.name != 'nt':
            patch.object(i, 'parse_powershell', return_value=None).start()

    def test_audit_never_changes_targets(self):
        self.assertEqual(i.install(self.store, HERE), 'READY')
        for p, raw in self.before.items():
            self.assertEqual(p.read_bytes(), raw)
        self.assertFalse((self.store / 'resilience-install-transaction.json').exists())

    def test_apply_and_idempotent_with_untouched_ui_and_original_probe(self):
        self.assertEqual(i.install(self.store, HERE, True), 'PASS')
        self.assertEqual(i.install(self.store, HERE, True), 'ALREADY_APPLIED')
        self.assertEqual(self.white.read_bytes(), self.before[self.white])
        self.assertEqual(self.probe.read_bytes(), self.before[self.probe])
        b = n.read(self.binding)
        self.assertEqual(n.digest(Path(b['transportProbe']).read_bytes()), b['transportProbeSha256'])
        self.assertEqual(n.digest(Path(b['nightlyResumeTool']).read_bytes()), b['nightlyResumeToolSha256'])
        self.assertIn(b'nightlyResumeTool', self.nightly.read_bytes())
        self.assertFalse(b['orderTransmission'])

    def test_unknown_nightly_local_edit_is_not_overwritten(self):
        self.nightly.write_bytes(self.before[self.nightly] + b'# LOCAL\n')
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_LOCAL_NIGHTLY_SOURCE'):
            i.install(self.store, HERE, True)
        self.assertEqual(self.binding.read_bytes(), self.before[self.binding])
        self.assertTrue(self.nightly.read_bytes().endswith(b'# LOCAL\n'))

    def test_bound_probe_mutation_blocks(self):
        self.probe.write_bytes(self.before[self.probe] + b'# EDIT\n')
        with self.assertRaisesRegex(ValueError, 'BOUND_SOURCE_CHANGED'):
            i.install(self.store, HERE, True)
        self.assertEqual(self.binding.read_bytes(), self.before[self.binding])

    def test_failed_binding_write_rolls_back_exact_originals(self):
        original = i.replace
        def fail(path, before, after):
            if path == self.binding:
                raise OSError('mock binding failure')
            return original(path, before, after)
        with patch.object(i, 'replace', side_effect=fail):
            with self.assertRaises(OSError):
                i.install(self.store, HERE, True)
        for p, raw in self.before.items():
            self.assertEqual(p.read_bytes(), raw)

    def test_process_death_after_first_replace_recovers_on_next_apply(self):
        original = i.replace
        calls = []
        def crash(path, before, after):
            original(path, before, after)
            calls.append(path)
            raise KeyboardInterrupt('mock process death')
        with patch.object(i, 'replace', side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                i.install(self.store, HERE, True)
        self.assertEqual(len(calls), 1)
        with self.assertRaisesRegex(ValueError, 'INTERRUPTED_INSTALL_REQUIRES_EXPLICIT_APPLY'):
            i.install(self.store, HERE)
        self.assertEqual(i.install(self.store, HERE, True), 'PASS')
        self.assertEqual(self.white.read_bytes(), self.before[self.white])
        self.assertEqual(n.checkpoint(self.store / 'resilience-install-transaction.json')['phase'], 'COMPLETE')

    def test_unknown_edit_after_interruption_is_not_rolled_back(self):
        original = i.replace
        def crash(path, before, after):
            original(path, before, after)
            raise KeyboardInterrupt()
        with patch.object(i, 'replace', side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                i.install(self.store, HERE, True)
        self.nightly.write_bytes(b'OTHER USER EDIT')
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_EDIT'):
            i.install(self.store, HERE, True)
        self.assertEqual(self.nightly.read_bytes(), b'OTHER USER EDIT')

    def test_active_runtime_blocks_before_install_journal(self):
        with patch.object(i, 'quiet', side_effect=ValueError('MOCK_ACTIVE_RUNTIME')):
            with self.assertRaisesRegex(ValueError, 'ACTIVE_RUNTIME'):
                i.install(self.store, HERE, True)
        self.assertFalse((self.store / 'resilience-install-transaction.json').exists())
        for p, raw in self.before.items():
            self.assertEqual(p.read_bytes(), raw)

if __name__ == '__main__':
    unittest.main(verbosity=2)
