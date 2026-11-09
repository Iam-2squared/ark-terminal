import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import no11_nightly_resume as n
import install_no11_circuit_audit_release as installer


class IntegratedInstallTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.store=self.root/'unified-launcher'
        (self.store/'oneclick').mkdir(parents=True)
        self.ui=self.store/'oneclick/Start-No11OneClick.ps1'
        self.ui.write_bytes(b'EXISTING WHITE USER UI\r\n')
        settings={'normalMaxPositions':3,'sameDayApprovalRequired':True,
                  'automaticOrderAuthorization':False,'orderTransmission':False}
        (self.store/'settings.json').write_bytes(n.encode(settings))
        self.pkg=self.store/'old-resilience-package';self.pkg.mkdir()
        self.b={'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1','orderTransmission':False,
                'manualPriceInputRequired':False,'manualEvidenceRequired':False,
                'transportProbe':'UNCHANGED_TRANSPORT_PATH','transportProbeSha256':'a'*64}
        files={'bridge':'launcher_automatic_bridge_v4.py','dailyCycleTool':'daily_cycle.py',
               'nightlyResumeTool':'no11_nightly_resume.py'}
        for key,name in files.items():
            path=self.pkg/name;path.write_bytes((HERE/name).read_bytes())
            self.b[key]=str(path);self.b[key+'Sha256']=n.digest(path.read_bytes())
        validator=self.pkg/'no11_selection_status.py';validator.write_bytes((HERE/validator.name).read_bytes())
        self.b['nightlyResumeValidatorSha256']=n.digest(validator.read_bytes())
        self.binding=self.store/'automatic-inputs.json';self.binding.write_bytes(n.encode(self.b))
        self.before={p:p.read_bytes() for p in [self.ui,*self.pkg.iterdir()]}

    def test_audit_does_not_install(self):
        before=self.binding.read_bytes()
        self.assertEqual(installer.install(self.store,HERE,test=True),'READY')
        self.assertEqual(self.binding.read_bytes(),before)
        self.assertFalse((self.store/installer.JOURNAL).exists())

    def check_applied(self):
        current=n.read(self.binding)
        changed=set(installer.FIELDS)|{k+'Sha256' for k in installer.FIELDS}
        for key,value in self.b.items():
            if key not in changed:self.assertEqual(current[key],value,key)
        for field in installer.FIELDS:
            path=Path(current[field]);self.assertTrue(path.is_file())
            self.assertEqual(n.digest(path.read_bytes()),current[field+'Sha256'])
            self.assertIn(b'ARK_NO11_CIRCUIT_AUDIT_V1',path.read_bytes())
        for p,raw in self.before.items():self.assertEqual(p.read_bytes(),raw)

    def test_one_binding_switch_upgrades_legacy_worker_and_three_circuits(self):
        self.assertEqual(installer.install(self.store,HERE,True,True),'PASS')
        self.check_applied()
        self.assertEqual(installer.install(self.store,HERE,True,True),'ALREADY_APPLIED')

    def test_worker_fix_already_installed_is_also_supported(self):
        path=self.pkg/'no11_nightly_resume_workeraware.py'
        path.write_bytes((HERE/path.name).read_bytes())
        self.b['nightlyResumeTool']=str(path);self.b['nightlyResumeToolSha256']=n.digest(path.read_bytes())
        self.binding.write_bytes(n.encode(self.b));self.before[path]=path.read_bytes()
        self.assertEqual(installer.install(self.store,HERE,True,True),'PASS')
        self.check_applied()

    def test_power_loss_after_atomic_binding_switch_can_complete(self):
        original=installer.replace
        def crash(path,before,after):
            original(path,before,after);raise KeyboardInterrupt('power cut')
        with patch.object(installer,'replace',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):installer.install(self.store,HERE,True,True)
        self.assertEqual(n.checkpoint(self.store/installer.JOURNAL)['phase'],'PREPARED')
        self.assertEqual(installer.install(self.store,HERE,True,True),'PASS')
        self.check_applied()

    def test_failed_binding_switch_preserves_old_and_can_resume(self):
        before=self.binding.read_bytes()
        with patch.object(installer,'replace',side_effect=OSError('disk write failed')):
            with self.assertRaises(OSError):installer.install(self.store,HERE,True,True)
        self.assertEqual(self.binding.read_bytes(),before)
        self.assertEqual(installer.install(self.store,HERE,True,True),'PASS')
        self.check_applied()

    def test_changed_original_file_not_overwritten(self):
        path=Path(self.b['bridge']);path.write_bytes(path.read_bytes()+b'# USER EDIT\n')
        before=self.binding.read_bytes()
        with self.assertRaisesRegex(ValueError,'BOUND_BRIDGE_CHANGED'):
            installer.install(self.store,HERE,True,True)
        self.assertEqual(self.binding.read_bytes(),before)
        self.assertTrue(path.read_bytes().endswith(b'# USER EDIT\n'))

if __name__=='__main__':unittest.main(verbosity=2)
