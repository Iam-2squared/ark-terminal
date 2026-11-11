"""Transactional real Friday RSS repair; never opens Excel, sends trade or resets."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import no11_nightly_resume as n
import install_no11_missing_friday_recovery as installer
import test_no11_missing_friday_recovery as fixture


class FridayInstallerTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='no11-real-friday-')
        self.addCleanup(tmp.cleanup)
        root=Path(tmp.name)
        self.store=root/'unified-launcher'
        (self.store/'oneclick').mkdir(parents=True)
        self.engine=root/'engine'
        (self.engine/'tools').mkdir(parents=True)
        (self.engine/'windows').mkdir(parents=True)
        self.ui=self.store/'oneclick/Start-No11OneClick.ps1'
        self.ui.write_bytes(b'USER WHITE GUI UNCHANGED\n')
        self.trade=self.engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1'
        self.trade.write_bytes(b'FROZEN ACTUAL TRADE STRATEGY UNCHANGED\n')
        self.settings=self.store/'settings.json'
        self.settings.write_bytes(n.encode({
            'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
            'orderTransmission':False,'normalMaxPositions':3,
            'sameDayApprovalRequired':True,'automaticOrderAuthorization':False
        }))
        self.oldpkg=self.store/'old-worker-package';self.oldpkg.mkdir()
        worker=self.oldpkg/'no11_nightly_resume_workeraware.py'
        worker.write_bytes(fixture.sources()['worker'])
        validator=self.oldpkg/'no11_selection_status.py'
        validator.write_bytes((HERE/validator.name).read_bytes())
        originals=fixture.sources()
        for kind,rel in installer.ENGINE.items():
            (self.engine/rel).write_bytes(originals[kind])
        self.binding=self.store/'automatic-inputs.json'
        self.b={'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
            'orderTransmission':False,'manualEvidenceRequired':False,
            'manualPriceInputRequired':False,
            'engine':str(self.engine),
            'nightlyResumeTool':str(worker),
            'nightlyResumeToolSha256':n.digest(worker.read_bytes()),
            'nightlyResumeValidatorSha256':n.digest(validator.read_bytes()),
            'python':sys.executable,
            'date':'2026-11-10','tradeSource':'EXISTING_UNCHANGED'}
        self.binding.write_bytes(n.encode(self.b))
        self.before={p:p.read_bytes() for p in (
            self.ui,self.trade,self.settings,self.binding,worker,validator,
            *(self.engine/rel for rel in installer.ENGINE.values()))}

    def check(self):
        b=n.read(self.binding)
        for key,value in self.b.items():
            if key not in ('nightlyResumeTool','nightlyResumeToolSha256'):
                self.assertEqual(b[key],value)
        self.assertTrue('real-friday-worker' in b['nightlyResumeTool'])
        self.assertEqual(n.digest(Path(b['nightlyResumeTool']).read_bytes()),
            b['nightlyResumeToolSha256'])
        for p,raw in self.before.items():
            if p==self.binding or p in [self.engine/rel for rel in installer.ENGINE.values()]:
                continue
            self.assertEqual(p.read_bytes(),raw,str(p))
        self.assertEqual(n.checkpoint(self.store/installer.JOURNAL)['phase'],'COMPLETE')

    def test_no_write_audit(self):
        self.assertEqual(installer.install(self.store,apply=False,test=True),'READY')
        self.assertFalse((self.store/installer.JOURNAL).exists())
        for p,raw in self.before.items():
            self.assertEqual(p.read_bytes(),raw)

    def test_complete_and_repeated_install_preserves_sources(self):
        self.assertEqual(installer.install(self.store,apply=True,test=True),'PASS')
        self.check()
        self.assertEqual(installer.install(self.store,apply=True,test=True),'ALREADY_APPLIED')
        for kind,rel in installer.ENGINE.items():
            self.assertEqual((self.engine/rel).read_bytes(),
                installer.patch.transform(kind,self.before[self.engine/rel]))
        self.assertEqual((self.store/'oneclick').joinpath(self.ui.name).read_bytes(),
                self.before[self.ui])

    def test_power_loss_after_one_engine_file_resume_without_reset(self):
        replace=installer.atomic_replace
        count=0
        def crash(path,before,after):
            nonlocal count
            count+=1
            replace(path,before,after)
            if count==1:
                raise KeyboardInterrupt('simulated power loss after first atomic replace')
        with patch.object(installer,'atomic_replace',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                installer.install(self.store,apply=True,test=True)
        self.assertEqual(n.checkpoint(self.store/installer.JOURNAL)['phase'],'PREPARED')
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_INSTALL_REQUIRES_APPLY'):
            installer.install(self.store,apply=False,test=True)
        self.assertEqual(installer.install(self.store,apply=True,test=True),'PASS')
        self.check()

    def test_power_loss_after_binding_commit_resume_without_reset(self):
        original=installer.atomic_replace
        def interrupt(path,before,after):
            original(path,before,after)
            if Path(path)==self.binding:
                raise KeyboardInterrupt('simulated power loss after binding update')
        with patch.object(installer,'atomic_replace',side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                installer.install(self.store,apply=True,test=True)
        self.assertEqual(installer.install(self.store,apply=True,test=True),'PASS')
        self.check()

    def test_tamper_3book_collector_fails_before_any_local_write(self):
        p=self.engine/'windows/Run-No11RssDailyTrendCensusReadOnly.ps1'
        p.write_bytes(b'USER CUSTOM UNKNOWN')
        with self.assertRaisesRegex(ValueError,'DAILY_MAX47_3BOOK_REQUIRED'):
            installer.install(self.store,apply=True,test=True)
        self.assertEqual(self.binding.read_bytes(),self.before[self.binding])
        self.assertFalse((self.store/installer.JOURNAL).exists())

    def test_tamper_after_prepared_is_rejected(self):
        with patch.object(installer,'atomic_replace',side_effect=OSError('disk offline')):
            with self.assertRaises(OSError):
                installer.install(self.store,apply=True,test=True)
        p=self.engine/'windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1'
        p.write_bytes(p.read_bytes()+b'USER UNKNOWN CHANGE')
        with self.assertRaisesRegex(ValueError,'LOCAL_ENGINE_EDIT'):
            installer.install(self.store,apply=True,test=True)
        self.assertEqual(self.binding.read_bytes(),self.before[self.binding])


if __name__=='__main__':
    unittest.main(verbosity=2)
