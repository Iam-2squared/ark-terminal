"""No-order end-to-end audit of exact three XLSB live preflight binding.

Existing dated masters and broker approvals are NOT changed or made valid.
Actual user Excel, broker, orders and EXIT remain outside this offline test.
"""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ENGINE=HERE.parent/'no12-prebuy-causal-runtime-20261011'
sys.path.insert(0,str(HERE))
import no11_live_xlsb_contract as c
import install_no11_live_xlsb_preflight as i
import no11_nightly_resume as n

class LiveThreeBookTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='ark-live-books-')
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.store=self.root/'unified-launcher'
        self.store.mkdir()
        self.engine=self.root/'engine'
        (self.engine/'windows').mkdir(parents=True)
        self.original=(ENGINE/'windows/Start-No11UnifiedLauncher.ps1').read_bytes()
        self.launcher=self.engine/'windows/Start-No11UnifiedLauncher.ps1'
        self.launcher.write_bytes(self.original)
        self.trade=self.engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1'
        self.trade.write_bytes((ENGINE/'windows/Run-No11ReceivedSessionOperatorLive.ps1').read_bytes())
        self.original_trade=self.trade.read_bytes()
        self.observer=self.engine/'windows/Observe-No11AccountReadOnly.ps1'
        self.observer.write_text('ORIGINAL ACCOUNT OBSERVER',encoding='utf-8')
        (self.store/'oneclick').mkdir()
        self.white=self.store/'oneclick/Start-No11OneClick.ps1'
        self.white.write_text('FROZEN WHITE ONECLICK UI',encoding='utf-8')
        self.books={}
        for role,(key,sheet) in c.ROLE.items():
            file=self.root/('Ark_No11_'+role+' (version 1).xlsb')
            file.write_bytes(b'SAVED XLSB ORIGINAL NEVER WRITTEN')
            self.books[role]=str(file)
        self.registration=self.root/'data-workbooks.json'
        self.registration.write_bytes(n.encode({
            'schemaId':'ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1',
            'books':[{'role':role,'sheet':sheet,'path':self.books[role],
                      'name':Path(self.books[role]).name,'date1904':False}
                     for role,(_,sheet) in c.ROLE.items()],
            'orderTransmission':False}))
        self.resolver=self.root/'No11DataWorkbookRegistry.ps1'
        self.resolver.write_bytes(b'PINNED ORIGINAL LIVE READ-ONLY REGISTRY RESOLVER')
        self.settings=self.store/'settings.json'
        old_paths=[str(self.root/(x+'.xlsx')) for x in ('old-account','old-market','old-ids')]
        self.config={'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
            'accountWorkbookPath':old_paths[0],'marketWorkbookPath':old_paths[1],
            'orderIdWorkbookPath':old_paths[2],
            'bootstrapConfigFile':str(self.root/'EXISTING_DATED_CONFIG.json'),
            'fullSymbolsFile':str(self.root/'4328.txt'),
            'normalMaxPositions':3,'sameDayApprovalRequired':True,
            'automaticOrderAuthorization':False,'orderTransmission':False}
        self.settings.write_bytes(n.encode(self.config))
        self.binding=self.store/'automatic-inputs.json'
        self.binding.write_bytes(n.encode({
          'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
          'orderTransmission':False,'engine':str(self.engine),
          'dataWorkbookRegistration':str(self.registration),
          'dataWorkbookRegistrationSha256':n.digest(self.registration.read_bytes()),
          'dataWorkbookResolver':str(self.resolver),
          'dataWorkbookResolverSha256':n.digest(self.resolver.read_bytes())}))
        self.before={f:f.read_bytes() for f in
               [self.white,self.observer,self.registration,self.resolver,
                *[Path(s) for s in self.books.values()]]}

    def test_transformation_has_no_order_or_dated_gate_mutations(self):
        after=c.transform_launcher(self.original)
        self.assertEqual(c.transform_launcher(after),after)
        self.assertIn(c.MARK.encode(),after)
        src=after.decode('utf-8-sig')
        self.assertIn('GetFileName($a)',src)
        self.assertIn('GetFileName($b)',src)
        self.assertIn('GetFileName($c)',src)
        self.assertIn('$files=@($a,$b,$c)',src)
        self.assertNotIn("Workbooks.Item('Ark_No11_MSII_RSS.xlsx')",src)
        self.assertIn("Need $approved 'TODAYS_EXPLICIT_OPERATOR_APPROVAL_REQUIRED'",src)
        self.assertIn("sameDayApprovalRequired=$true",src)
        self.assertIn("Need ($broker.transport.mode -ceq 'LIVE'",src)
        self.assertIn("NO11_UNIFIED_BROKER_ORDER_CANCELLED=False",src)
        self.assertNotIn('RssStockOrder(',src)
        self.assertNotIn('RssCancelOrder(',src)
        op=c.transform_operator(self.original_trade)
        self.assertEqual(c.transform_operator(op),op)
        self.assertIn(c.OPERATOR_MARK.encode(),op)
        self.assertIn("'.xlsb'",op.decode('utf-8-sig'))
        self.assertIn("'SAME_DAY_OPERATOR_APPROVAL_REQUIRED'",op.decode('utf-8-sig'))
        self.assertIn("'REVIEWED_SECURITIES_ONLY_CASH'",op.decode('utf-8-sig'))
        self.assertIn("'MAX3_AND_SECURITIES_CASH'",op.decode('utf-8-sig'))
        if os.name=='nt':
            i.powershell_syntax(after)
            i.powershell_syntax(op)

    def test_audit_is_completely_read_only(self):
        self.assertEqual(i.install(self.store,False,True),'READY')
        self.assertFalse((self.store/i.JOURNAL).exists())
        self.assertEqual(self.settings.read_bytes(),n.encode(self.config))
        self.assertEqual(self.launcher.read_bytes(),self.original)
        self.assertEqual(self.trade.read_bytes(),self.original_trade)
        for f,raw in self.before.items():self.assertEqual(f.read_bytes(),raw)

    def test_apply_updates_only_three_paths_and_preflight_not_broker_ledger(self):
        self.assertEqual(i.install(self.store,True,True),'PASS')
        cfg=n.read(self.settings)
        for role,(key,sheet) in c.ROLE.items():
            self.assertEqual(cfg[key],self.books[role])
        self.assertEqual(cfg['bootstrapConfigFile'],self.config['bootstrapConfigFile'])
        self.assertEqual(cfg['fullSymbolsFile'],self.config['fullSymbolsFile'])
        self.assertEqual(cfg['sameDayApprovalRequired'],True)
        self.assertEqual(cfg['automaticOrderAuthorization'],False)
        self.assertEqual(cfg['orderTransmission'],False)
        self.assertIn(c.MARK.encode(),self.launcher.read_bytes())
        self.assertIn(c.OPERATOR_MARK.encode(),self.trade.read_bytes())
        self.assertEqual(i.install(self.store,True,True),'ALREADY_APPLIED')
        for f,raw in self.before.items():self.assertEqual(f.read_bytes(),raw)

    def test_new_binding_is_not_automatic_live_approval(self):
        self.assertEqual(i.install(self.store,True,True),'PASS')
        self.assertEqual(n.read(self.settings)['bootstrapConfigFile'],
                         str(self.root/'EXISTING_DATED_CONFIG.json'))
        self.assertFalse((self.root/'EXISTING_DATED_CONFIG.json').exists())
        self.assertFalse(list(self.store.glob('*TRADE*.launch.json')))

    def test_bad_registry_or_excess_workbook_is_rejected(self):
        orig=self.registration.read_bytes()
        obj=n.read(self.registration)
        obj['books'][0]['date1904']=True
        self.registration.write_bytes(n.encode(obj))
        binding=n.read(self.binding)
        binding['dataWorkbookRegistrationSha256']=n.digest(self.registration.read_bytes())
        self.binding.write_bytes(n.encode(binding))
        with self.assertRaisesRegex(ValueError,'REGISTERED_PATH'):
            i.install(self.store,False,True)
        obj['books'][0]['date1904']=False
        obj['books'].append(dict(obj['books'][0]))
        self.registration.write_bytes(n.encode(obj))
        binding['dataWorkbookRegistrationSha256']=n.digest(self.registration.read_bytes())
        self.binding.write_bytes(n.encode(binding))
        with self.assertRaisesRegex(ValueError,'THREE_REGISTRY_BOOKS'):
            i.install(self.store,False,True)
        self.assertEqual(self.settings.read_bytes(),n.encode(self.config))
        self.assertEqual(self.launcher.read_bytes(),self.original)
        self.assertEqual(self.trade.read_bytes(),self.original_trade)

    def test_journal_recovery_after_one_atomic_replacement(self):
        original=i.atomic_replace
        calls=0
        def cut(*args):
            nonlocal calls
            original(*args);calls+=1
            if calls==1:raise KeyboardInterrupt('SIMULATED_KILL_AFTER_FIRST_WRITE')
        with patch.object(i,'atomic_replace',side_effect=cut):
            with self.assertRaises(KeyboardInterrupt):
                i.install(self.store,True,True)
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_TRANSACTION_REQUIRES_APPLY'):
            i.install(self.store,False,True)
        self.assertEqual(i.install(self.store,True,True),'PASS')
        self.assertEqual(i.install(self.store,True,True),'ALREADY_APPLIED')
        for f,raw in self.before.items():self.assertEqual(f.read_bytes(),raw)

    def test_modified_complete_package_is_not_silently_accepted(self):
        self.assertEqual(i.install(self.store,True,True),'PASS')
        self.launcher.write_bytes(self.launcher.read_bytes()+b'UNEXPECTED CHANGE')
        with self.assertRaisesRegex(ValueError,'EXTERNAL_CHANGE_DETECTED'):
            i.install(self.store,True,True)

if __name__=='__main__':
    unittest.main(verbosity=2)
