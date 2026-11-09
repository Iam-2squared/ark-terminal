"""Regression: process lineage probe update cannot change RSS/Trade/GUI work."""
from __future__ import annotations

import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import install_no11_worker_probe_fix as installer
import no11_nightly_resume as old
import no11_nightly_resume_workeraware as worker


class WorkerFixUnitTests(unittest.TestCase):
    def test_only_probe_function_changed(self):
        installer.ensure_same_except_probe((HERE/'no11_nightly_resume.py').read_bytes(),
            (HERE/'no11_nightly_resume_workeraware.py').read_bytes())
        original=(HERE/'no11_nightly_resume.py').read_text(encoding='utf-8')
        modified=(HERE/'no11_nightly_resume_workeraware.py').read_text(encoding='utf-8')
        for token in ("class Pipeline:", "def native(", "def run_logged(", "def exclusive(",
                      "orderTransmission': False", "Run-No11NightlyCycle", "NO11_NIGHTLY_CYCLE=NEXT_SESSION_READY_FOR_TRADE_BUTTON"):
            self.assertIn(token,original)
            self.assertIn(token,modified)
        self.assertIn("ARK_NO11_NIGHTLY_RESUME_WORKER_PROBE_V2",modified)
        self.assertIn("Get-CimInstance Win32_Process -ErrorAction Stop",modified)
        self.assertIn("$ancestors.ContainsKey($id)",modified)
        self.assertIn("WORKER_QUERY_FAILED",modified)
        self.assertIn("OLD_WORKER_STILL_RUNNING",modified)
        self.assertNotIn("Stop-Process",modified)
        self.assertNotIn("RssStockOrder(",modified)

    def test_active_worker_and_cim_failure_are_distinct_fail_closed(self):
        src=(HERE/'no11_nightly_resume_workeraware.py').read_text(encoding='utf-8')
        self.assertIn("result.returncode not in (0, 3)",src)
        self.assertIn("bool(data['workers']) != (result.returncode == 3)",src)
        self.assertIn("need(False, 'OLD_WORKER_STILL_RUNNING')",src)
        self.assertIn("need(False, 'WORKER_QUERY_FAILED')",src)

    def test_original_install_and_new_immutable_bundle_separate(self):
        source=(HERE/'install_no11_worker_probe_fix.py').read_text(encoding='utf-8')
        self.assertIn("worker-probe-v2-",source)
        self.assertIn("worker-probe-v2-transaction.json",source)
        self.assertIn("whiteGuiSha256",source)
        self.assertIn("bindingBeforeSha256",source)
        self.assertNotIn("RunTrade(",source)
        self.assertNotIn("ORDER_TRIGGER_WRITTEN_TO_ONE=True",source)


class WorkerInstallerTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.store=root/'unified-launcher'
        self.engine=root/'engine'
        (self.store/'oneclick').mkdir(parents=True)
        (self.engine/'windows').mkdir(parents=True)
        self.gui=self.store/'oneclick/Start-No11OneClick.ps1'
        self.gui.write_bytes(b'APPROVED WHITE ONECLICK CUSTOM LOCAL UI\r\n')
        self.settings=self.store/'settings.json'
        self.settings.write_bytes(old.encode({'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
            'normalMaxPositions':3,'sameDayApprovalRequired':True,
            'automaticOrderAuthorization':False,'orderTransmission':False}))
        wrapper=self.engine/'windows/Run-No11NightlyCycle.ps1'
        wrapper.write_bytes((HERE/'Run-No11ResumableNightly.ps1').read_bytes())
        pkg=self.store/'resilience-tools-preexisting'
        pkg.mkdir()
        self.tool=pkg/'no11_nightly_resume.py'
        self.tool.write_bytes((HERE/'no11_nightly_resume.py').read_bytes())
        self.validator=pkg/'no11_selection_status.py'
        self.validator.write_bytes((HERE/'no11_selection_status.py').read_bytes())
        self.binding=self.store/'automatic-inputs.json'
        self.binding.write_bytes(old.encode({
            'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
            'orderTransmission':False,'manualPriceInputRequired':False,
            'manualEvidenceRequired':False,'engine':str(self.engine),
            'python':sys.executable,
            'nightlyResumeTool':str(self.tool),
            'nightlyResumeToolSha256':old.digest(self.tool.read_bytes()),
            'nightlyResumeValidatorSha256':old.digest(self.validator.read_bytes())}))
        # Separate original install journal, never touched by overlay.
        self.legacy=self.store/'resilience-install-transaction.json'
        self.legacy.write_bytes(b'PREEXISTING SIGNED JOURNAL UNCHANGED')
        self.before={p:p.read_bytes() for p in (self.gui,self.settings,self.binding,self.tool,self.validator,wrapper,self.legacy)}

    def test_readonly_preflight(self):
        self.assertEqual(installer.install(self.store,HERE,do_apply=False,test=True),'READY')
        for p,raw in self.before.items():
            self.assertEqual(p.read_bytes(),raw)
        self.assertFalse((self.store/installer.JOURNAL).exists())

    def test_apply_and_idempotent_only_retarget_bound_data_probe(self):
        self.assertEqual(installer.install(self.store,HERE,do_apply=True,test=True),'PASS')
        self.assertEqual(installer.install(self.store,HERE,do_apply=True,test=True),'ALREADY_APPLIED')
        updated=old.read(self.binding)
        original=old.read(self.binding)  # read from new bytes
        before=json.loads(self.before[self.binding])
        for k,v in before.items():
            if k not in ('nightlyResumeTool','nightlyResumeToolSha256'):
                self.assertEqual(v,updated[k],k)
        self.assertTrue(updated['nightlyResumeTool'].endswith('no11_nightly_resume_workeraware.py'))
        self.assertEqual(old.digest(Path(updated['nightlyResumeTool']).read_bytes()),
                         updated['nightlyResumeToolSha256'])
        self.assertEqual(updated['nightlyResumeValidatorSha256'],before['nightlyResumeValidatorSha256'])
        for p,raw in self.before.items():
            if p!=self.binding:
                self.assertEqual(p.read_bytes(),raw,str(p))
        self.assertEqual(old.checkpoint(self.store/installer.JOURNAL)['phase'],'COMPLETE')

    def test_interrupted_binding_commit_never_loses_receipt(self):
        save=installer.replace
        def power_loss(path,before,after):
            save(path,before,after)
            raise KeyboardInterrupt('simulated power loss after atomic binding write')
        with patch.object(installer,'replace',side_effect=power_loss):
            with self.assertRaises(KeyboardInterrupt):
                installer.install(self.store,HERE,do_apply=True,test=True)
        self.assertEqual(old.checkpoint(self.store/installer.JOURNAL)['phase'],'PREPARED')
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_APPLY_REQUIRED'):
            installer.install(self.store,HERE,do_apply=False,test=True)
        self.assertEqual(installer.install(self.store,HERE,do_apply=True,test=True),'PASS')
        self.assertEqual(self.gui.read_bytes(),self.before[self.gui])
        self.assertEqual(self.legacy.read_bytes(),self.before[self.legacy])
        self.assertEqual(old.checkpoint(self.store/installer.JOURNAL)['phase'],'COMPLETE')

    def test_tampered_old_package_or_validator_blocks_all_writes(self):
        self.validator.write_bytes(b'UNTRUSTED_VALIDATOR')
        with self.assertRaisesRegex(ValueError,'BOUND_SOURCE_HASH_CHANGED'):
            installer.install(self.store,HERE,do_apply=True,test=True)
        self.assertEqual(self.binding.read_bytes(),self.before[self.binding])

    def test_unknown_live_wrapper_blocks(self):
        p=self.engine/'windows/Run-No11NightlyCycle.ps1'
        p.write_bytes(p.read_bytes()+b'\r\n# UNKNOWN LOCAL WRAPPER\r\n')
        with self.assertRaisesRegex(ValueError,'INSTALLED_WRAPPER_CHANGED'):
            installer.install(self.store,HERE,do_apply=True,test=True)
        self.assertEqual(self.binding.read_bytes(),self.before[self.binding])


@unittest.skipUnless(os.name=='nt','real CIM probe requires Windows')
class ActualWindowsWorkerProbeTests(unittest.TestCase):
    def test_no_worker_probe_excludes_its_own_invocation_ancestry(self):
        # CI runs this from test-runner Python, exactly the kind of ancestry
        # falsely classified by the legacy regex checks.
        worker.no_workers()

    def test_independent_ark_nightly_power_shell_process_is_still_blocked(self):
        script="Start-Sleep -Seconds 30 # Run-No11NightlyCycle"
        child=subprocess.Popen(["powershell.exe","-NoLogo","-NoProfile","-NonInteractive",
                                "-Command",script],stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            time.sleep(0.7)
            self.assertIsNone(child.poll(),'fixture must still be alive')
            with self.assertRaisesRegex(ValueError,'OLD_WORKER_STILL_RUNNING'):
                worker.no_workers()
        finally:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=10)


if __name__=='__main__':
    unittest.main(verbosity=2)
