"""Crash recovery, frozen LIVE controls, and source hash-safe minute auto release."""
from pathlib import Path
import hashlib
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import no11_nightly_resume as n
import no11_circuit_repair as circuit
import no11_auto_minute_cycle_transform as cycle_patch
import no11_auto_minute_worker_transform as worker_patch
import install_no11_auto_minutes_release as installer

class AutoMinuteInstallerTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='ark-auto-minutes-release-')
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.store=self.root/'unified-launcher'
        (self.store/'oneclick').mkdir(parents=True)
        self.engine=self.root/'engine'
        (self.engine/'windows').mkdir(parents=True)
        self.source=HERE
        self.gui=self.store/'oneclick/Start-No11OneClick.ps1'
        self.gui.write_bytes(b'WHITE GUI FROZEN')
        self.trade=self.engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1'
        self.trade.write_bytes(b'EXIT AND ENTRY FROZEN')
        self.settings=self.store/'settings.json'
        self.settings.write_bytes(n.encode({
            'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
            'normalMaxPositions':3,'sameDayApprovalRequired':True,
            'automaticOrderAuthorization':False,'orderTransmission':False,
            'fullSymbolsFile':str(self.root/'4328-symbols.txt')}))
        (self.root/'4328-symbols.txt').write_text('7203.T\n')
        self.current=self.store/'versioned-databooks'
        self.current.mkdir()
        self.registry=self.current/'data-workbooks.json'
        self.registry.write_bytes(n.encode({'schemaId':'ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1',
            'orderTransmission':False,'books':[]}))
        self.resolver=self.current/'No11DataWorkbookRegistry.ps1'
        self.resolver.write_bytes(b'REGISTERED THREE XLSB RESOLVER')
        self.current_cycle=self.current/'daily_cycle.py'
        self.current_cycle.write_bytes(
            circuit.transform('cycle',(HERE/'daily_cycle.py').read_bytes()))
        self.current_worker=self.current/'no11_nightly_resume_workeraware.py'
        existing=circuit.transform('worker',(HERE/'no11_nightly_resume_workeraware.py').read_bytes())
        installed=existing.decode('utf-8-sig').replace(
            "    work = root / 'resumable-nightly' / (asof + '_' + target)",
            "    work = root / 'resumable-nightly' / (asof + '_' + target + '-data-books-v1-deadbeefcafebabe')")
        self.current_worker.write_bytes(installed.encode())
        self.validator=self.current/'no11_selection_status.py'
        self.validator.write_bytes((HERE/'no11_selection_status.py').read_bytes())
        self.binding=self.store/'automatic-inputs.json'
        b={'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
           'orderTransmission':False,'manualEvidenceRequired':False,
           'manualPriceInputRequired':False,'engine':str(self.engine),
           'dailyCycleRoot':str(self.root/'daily-cycle'),
           'python':sys.executable,
           'dailyCycleTool':str(self.current_cycle),
           'dailyCycleToolSha256':n.digest(self.current_cycle.read_bytes()),
           'nightlyResumeTool':str(self.current_worker),
           'nightlyResumeToolSha256':n.digest(self.current_worker.read_bytes()),
           'nightlyResumeValidatorSha256':n.digest(self.validator.read_bytes()),
           'dataWorkbookRegistration':str(self.registry),
           'dataWorkbookRegistrationSha256':n.digest(self.registry.read_bytes()),
           'dataWorkbookResolver':str(self.resolver),
           'dataWorkbookResolverSha256':n.digest(self.resolver.read_bytes()),
           'unrelatedTradeFrozen':'SAVED'}
        self.binding.write_bytes(n.encode(b))
        self.old_binding=b
        self.before={f:f.read_bytes() for f in (
            self.gui,self.trade,self.settings,self.registry,self.resolver,
            self.current_cycle,self.current_worker,self.validator,self.binding)}
        (self.root/'daily-cycle').mkdir()

    def validate(self):
        b=n.read(self.binding)
        self.assertEqual(b['unrelatedTradeFrozen'],'SAVED')
        self.assertFalse(b['orderTransmission'])
        self.assertIn('autoMinuteExclusionToolSha256',b)
        tool=Path(b['dailyCycleTool'])
        self.assertTrue(tool.is_file())
        self.assertIn(b'ARK_NO11_AUTO_MINUTE_PRUNE_BOUND_DATA_CYCLE_V1',
                      tool.read_bytes())
        self.assertIn(b'ARK_NO11_PROVEN_TWO_SESSION_CAPTURE_LOG_V1',
                      tool.read_bytes())
        self.assertIn(b'ARK_NO11_AUTO_MINUTE_CAPTURE_ADOPTION_V1',
                      Path(b['nightlyResumeTool']).read_bytes())
        self.assertEqual(n.digest(tool.read_bytes()),b['dailyCycleToolSha256'])
        for f,raw in self.before.items():
            if f!=self.binding:self.assertEqual(f.read_bytes(),raw,str(f))
        self.assertEqual(n.checkpoint(self.store/installer.JOURNAL)['phase'],'COMPLETE')

    def test_only_audit_never_writes_existing_files(self):
        status,_=installer.install(self.store,self.source,test=True)
        self.assertEqual(status,'READY')
        self.assertFalse((self.store/installer.JOURNAL).exists())
        for f,raw in self.before.items():self.assertEqual(f.read_bytes(),raw)

    def test_apply_preserves_all_frozen_files_and_repeated_apply(self):
        status,_=installer.install(self.store,self.source,True,True)
        self.assertEqual(status,'PASS')
        self.validate()
        status,_=installer.install(self.store,self.source,True,True)
        self.assertEqual(status,'ALREADY_APPLIED')
        self.validate()

    def test_journal_recovers_crash_before_binding_switch(self):
        original=installer.atomic_replace
        calls=0
        def after_replace(p,a,b):
            nonlocal calls
            original(p,a,b);calls+=1
            if calls==1:raise KeyboardInterrupt('simulated sudden power outage')
        with patch.object(installer,'atomic_replace',side_effect=after_replace):
            with self.assertRaises(KeyboardInterrupt):
                installer.install(self.store,self.source,True,True)
        with self.assertRaisesRegex(ValueError,'PREPARED_TRANSACTION_REQUIRES_APPLY'):
            installer.install(self.store,self.source,False,True)
        status,_=installer.install(self.store,self.source,True,True)
        self.assertEqual(status,'PASS')
        self.validate()

    def test_local_modified_binding_blocks_without_rewriting_original(self):
        self.binding.write_bytes(self.binding.read_bytes()+b'USER_MUTATION')
        with self.assertRaises(ValueError):
            installer.install(self.store,self.source,True,True)
        self.assertFalse((self.store/installer.JOURNAL).exists())
        self.assertEqual(self.gui.read_bytes(),self.before[self.gui])
        self.assertEqual(self.trade.read_bytes(),self.before[self.trade])

    def test_original_cycle_and_workbook_registration_unmodified(self):
        self.assertIn(b'ARK_NO11_CIRCUIT_AUDIT_V1',self.current_cycle.read_bytes())
        result=cycle_patch.transform(self.current_cycle.read_bytes())
        self.assertEqual(result,cycle_patch.transform(result))
        helper_hash=n.digest((HERE/'no11_auto_minute_exclusion.py').read_bytes())
        changed=worker_patch.transform(self.current_worker.read_bytes(),helper_hash)
        self.assertEqual(changed,worker_patch.transform(changed,helper_hash))
        self.assertNotIn(b'RssStockOrder(',changed)

if __name__=='__main__':unittest.main(verbosity=2)
