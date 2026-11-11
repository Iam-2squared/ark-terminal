"""True V3 pinned transport rebind install, crash recovery, no order or Excel IO."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import no11_nightly_resume as n
import patch_no11_transport_resilience as resilient
import no11_transport_format_guard as f
import install_no11_transport_format_guard as installer

class TransportFormatReleaseTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='ark-bd4-release-')
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.store=self.root/'store'
        self.store.mkdir()
        self.engine=self.root/'engine'
        (self.engine/'windows').mkdir(parents=True)
        self.white=self.store/'oneclick/Start-No11OneClick.ps1'
        self.white.parent.mkdir()
        self.white.write_bytes(b'APPROVED ORIGINAL WHITE UI FROZEN')
        self.operator=self.engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1'
        self.operator.write_bytes(b'FROZEN SAME DAY OPERATOR TRADE AND EXIT')
        self.executor=self.engine/'windows/Invoke-No11MsiiOrder.ps1'
        self.executor.write_bytes(b'ORIGINAL ONE SHOT LIVE ORDER TRIGGER')
        self.settings=self.store/'settings.json'
        self.settings.write_bytes(n.encode({
           'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
           'normalMaxPositions':3,'sameDayApprovalRequired':True,
           'automaticOrderAuthorization':False,'orderTransmission':False}))
        self.probe=self.root/'Prepare-No11AutomaticLiveTransportResilient.ps1'
        self.probe.write_bytes(resilient.transform(
             (HERE/'Prepare-No11AutomaticLiveTransportV3.ps1').read_bytes()))
        self.registration=self.root/'data-workbooks.json'
        self.registration.write_bytes(n.encode({'schemaId':'ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1',
                                                'orderTransmission':False}))
        self.resolver=self.root/'No11DataWorkbookRegistry.ps1'
        self.resolver.write_bytes(b'ORIGINAL XLSB COM RESOLVER FROZEN')
        self.binding_file=self.store/'automatic-inputs.json'
        self.binding={'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
             'orderTransmission':False,'manualPriceInputRequired':False,
             'transportProbe':str(self.probe),
             'transportProbeSha256':n.digest(self.probe.read_bytes()),
             'engine':str(self.engine),
             'dataWorkbookRegistration':str(self.registration),
             'dataWorkbookRegistrationSha256':n.digest(self.registration.read_bytes()),
             'dataWorkbookResolver':str(self.resolver),
             'dataWorkbookResolverSha256':n.digest(self.resolver.read_bytes()),
             'dailyCycleTool':'PRESERVED_JOURNALED_DATED_DATA_NO_RECAPTURE'}
        self.binding_file.write_bytes(n.encode(self.binding))
        self.before={path:path.read_bytes() for path in [
            self.probe,self.operator,self.executor,self.white,self.settings,
            self.registration,self.resolver]}

    def assert_safe(self):
        for path,raw in self.before.items():self.assertEqual(path.read_bytes(),raw,str(path))
        bound=n.read(self.binding_file)
        self.assertEqual(bound['dailyCycleTool'],self.binding['dailyCycleTool'])
        self.assertFalse(bound['orderTransmission'])
        self.assertEqual(bound['engine'],self.binding['engine'])
        self.assertTrue(Path(bound['transportProbe']).is_file())
        self.assertNotEqual(bound['transportProbe'],str(self.probe))
        self.assertEqual(n.digest(Path(bound['transportProbe']).read_bytes()),
                         bound['transportProbeSha256'])
        source=Path(bound['transportProbe']).read_text(encoding='utf-8-sig')
        self.assertIn('ARK_NO11_TRANSPORT_FORMAT_BEFORE_SESSION_V1',source)
        self.assertIn('SAME_DAY_OPERATOR_APPROVAL_REQUIRED',source)
        self.assertNotIn('$trigger.Value2=1',source)
        self.assertNotIn('RssStockOrder(',source)
        self.assertEqual(n.checkpoint(self.store/installer.JOURNAL)['phase'],'COMPLETE')

    def test_audit_never_writes(self):
        self.assertEqual(installer.install(self.store,False,True),'READY')
        self.assertEqual(self.binding_file.read_bytes(),n.encode(self.binding))
        self.assertFalse((self.store/installer.JOURNAL).exists())
        for p,raw in self.before.items():self.assertEqual(p.read_bytes(),raw)

    def test_apply_once_and_repeat_without_source_edits(self):
        self.assertEqual(installer.install(self.store,True,True),'PASS')
        self.assert_safe()
        self.assertEqual(installer.install(self.store,True,True),'ALREADY_APPLIED')
        self.assert_safe()

    def test_power_cut_after_binding_switch_resumes_without_recapture(self):
        original=installer.exchange
        called=0
        def fail_after_exchange(*args):
            nonlocal called
            original(*args)
            called+=1
            if called==1:
                raise KeyboardInterrupt('SIMULATED_POWER_CUT_AFTER_BINDING_SWAP')
        with patch.object(installer,'exchange',side_effect=fail_after_exchange):
            with self.assertRaises(KeyboardInterrupt):
                installer.install(self.store,True,True)
        with self.assertRaisesRegex(ValueError,'PREPARED_REQUIRES_APPLY'):
            installer.install(self.store,False,True)
        self.assertEqual(installer.install(self.store,True,True),'PASS')
        self.assert_safe()

    def test_original_probe_hash_modified_refused(self):
        self.probe.write_bytes(self.probe.read_bytes()+b'CHANGED')
        with self.assertRaisesRegex(ValueError,'ORIGINAL_TRANSPORT_SOURCE_SHA_MISMATCH'):
            installer.install(self.store,True,True)
        self.assertFalse((self.store/installer.JOURNAL).exists())
        self.assertEqual(self.binding_file.read_bytes(),n.encode(self.binding))

    def test_unexpected_ledger_or_settings_edit_fails_without_rewrite(self):
        self.assertEqual(installer.install(self.store,True,True),'PASS')
        self.settings.write_bytes(self.settings.read_bytes()+b'USER_CHANGE')
        with self.assertRaisesRegex(ValueError,'FROZEN_ORIGINAL_EDIT'):
            installer.install(self.store,True,True)
        self.assertFalse(n.read(self.binding_file)['orderTransmission'])

    def test_invalid_original_write_mode_does_not_get_patched(self):
        raw=self.probe.read_bytes().replace(
            b"$trigger.Value2=0",b"$trigger.Value2=1")
        self.probe.write_bytes(raw)
        self.binding['transportProbeSha256']=n.digest(raw)
        self.binding_file.write_bytes(n.encode(self.binding))
        with self.assertRaisesRegex(ValueError,'EXPECTED_PINNED_V3_RESILIENT_SOURCE'):
            installer.install(self.store,False,True)

    @unittest.skipUnless(os.name=='nt','Windows PowerShell parser')
    def test_installed_script_has_valid_windows_powershell_syntax(self):
        new=f.transform(self.probe.read_bytes())
        installer.syntax(new)

if __name__=='__main__':unittest.main(verbosity=2)
