"""Regression: old weekly FullName gate must not block the RSS collector."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import install_no11_weekly_workbook_handoff as fix
import test_no11_completed_session_update as completed
import test_no11_update_path as candidates

class WeeklyBookGateTests(unittest.TestCase):
    @staticmethod
    def installed_native():
        src=completed.sources()
        raw=completed.upgrade.transform('native',src['native'])
        return raw

    def test_exact_data_only_patch_and_preserve_live_and_gui(self):
        raw=self.installed_native()
        new=fix.transform(raw)
        text=raw.decode('utf-8-sig').replace('\r\n','\n')
        after=new.decode('utf-8-sig').replace('\r\n','\n')
        a=text.index('function RunWeekly($cfg){')
        b=text.index('function StopRunningEngine(',a)
        self.assertEqual(text[:a],after[:a])
        self.assertEqual(text[b:],after[after.index('function StopRunningEngine(',a):])
        self.assertEqual(text.count('CheckExcel $cfg $true'),1)
        self.assertEqual(after.count('CheckExcel $cfg $true'),1)
        self.assertNotIn('CheckExcel $cfg $false',after[a:after.index('function StopRunningEngine(',a)])
        self.assertIn(fix.MARKER,after)
        self.assertIn('DELEGATED_TO_RSS_COLLECTOR',after)
        self.assertIn('StartChild \'WEEKLY\' $weekly',after)
        self.assertEqual(fix.transform(new),new)

    def test_unknown_native_must_not_be_patched(self):
        bad=self.installed_native().replace(b"StartChild 'WEEKLY' $weekly",b"StartChild 'TRADE' $weekly")
        with self.assertRaisesRegex(ValueError,'NATIVE_WEEKLY_CONTEXT_CHANGED'):
            fix.transform(bad)

    def test_preserve_crlf_bom(self):
        raw=self.installed_native().decode('utf-8-sig').replace('\r\n','\n')
        inp=b'\xef\xbb\xbf'+raw.replace('\n','\r\n').encode()
        new=fix.transform(inp)
        self.assertTrue(new.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n',new.replace(b'\r\n',b''))

class InstallTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        root=Path(t.name)
        self.store=root/'unified-launcher'
        (self.store/'oneclick').mkdir(parents=True)
        self.gui=self.store/'oneclick/Start-No11OneClick.ps1'
        self.gui.write_bytes(b'APPROVED WHITE GUI LOCAL USER DESIGN\r\n')
        self.engine=root/'engine'
        (self.engine/'windows').mkdir(parents=True)
        self.native=self.engine/'windows/Start-No11UnifiedLauncher.ps1'
        self.native.write_bytes(WeeklyBookGateTests.installed_native())
        self.settings=self.store/'settings.json'
        self.settings.write_text(json.dumps({
           'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
           'orderTransmission':False,'normalMaxPositions':3,
           'sameDayApprovalRequired':True,'automaticOrderAuthorization':False
        }))
        self.binding=self.store/'automatic-inputs.json'
        self.binding.write_text(json.dumps({
            'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
            'orderTransmission':False,'engine':str(self.engine)
        }))
        originals=candidates.NativeUpdateTests().originals()
        self.collectors={}
        for kind,name in [('daily','Run-No11RssDailyTrendCensusReadOnly.ps1'),
                          ('pool','Run-No11WeeklyCandidateRefreshReadOnly.ps1'),
                          ('minutes','Capture-No11RssTrainingBatchReadOnly.ps1')]:
            p=self.engine/'windows'/name
            p.write_bytes(originals[kind])
            self.collectors[name]=p
        self.before={p:p.read_bytes() for p in
                     (self.gui,self.native,self.binding,self.settings,*self.collectors.values())}

    def test_audit_never_modifies(self):
        self.assertEqual(fix.install(self.store,apply=False,synthetic=True),'READY')
        for p,raw in self.before.items():
            self.assertEqual(p.read_bytes(),raw)

    def test_install_and_repeat_only_native_data_gate_changed(self):
        self.assertEqual(fix.install(self.store,apply=True,synthetic=True),'PASS')
        self.assertEqual(fix.install(self.store,apply=True,synthetic=True),'ALREADY_APPLIED')
        self.assertEqual(self.native.read_bytes(),fix.transform(self.before[self.native]))
        for p,raw in self.before.items():
            if p!=self.native:
                self.assertEqual(p.read_bytes(),raw)
        backups=list((self.store/'weekly-workbook-gate-backups').glob('*.ps1'))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_bytes(),self.before[self.native])

    def test_collector_not_3book_capable_blocks_without_write(self):
        p=self.collectors['Run-No11RssDailyTrendCensusReadOnly.ps1']
        p.write_bytes(b'ORIGINAL WITHOUT THREE BOOKS')
        with self.assertRaisesRegex(ValueError,'COLLECTOR_THREE_BOOK_NOT_INSTALLED'):
            fix.install(self.store,apply=True,synthetic=True)
        self.assertEqual(self.native.read_bytes(),self.before[self.native])

    def test_trade_gates_are_not_changed(self):
        result=fix.transform(self.before[self.native])
        old=self.before[self.native].decode('utf-8-sig')
        new=result.decode('utf-8-sig')
        cut='function RunWeekly($cfg){'
        self.assertEqual(old[:old.index(cut)],new[:new.index(cut)])
        self.assertIn("CheckExcel $cfg $true",new)
        self.assertIn("Need $approved 'TODAYS_EXPLICIT_OPERATOR_APPROVAL_REQUIRED'",new)
        self.assertIn("StartChild 'TRADE'",new)

if __name__=='__main__':
    unittest.main(verbosity=2)
