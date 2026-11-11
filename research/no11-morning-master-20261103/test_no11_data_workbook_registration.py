"""XLSB role registry and exact installed-source migration; no real workbook I/O."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ENGINE=HERE.parent/'no12-prebuy-causal-runtime-20261011'
sys.path.insert(0,str(HERE))
import no11_nightly_resume as n
import install_no11_data_workbook_registration as installer
import no11_missing_friday_recovery_transform as friday
import install_no11_historical_calendar_pathfix as pathfix
import test_no11_missing_friday_recovery as fixtures
import test_no11_update_path as originals
import no11_update_path as maximum


def installed_sources():
    prior=fixtures.sources();raw=originals.NativeUpdateTests().originals()
    return {
        'Run-No11RssDailyTrendCensusReadOnly.ps1':friday.transform('dailyCollector',prior['dailyCollector']),
        'Run-No11WeeklyCandidateRefreshReadOnly.ps1':maximum.transform('pool',raw['pool']),
        'Capture-No11RssTrainingBatchReadOnly.ps1':maximum.transform('minutes',raw['minutes']),
        'Prepare-No11NextSessionNightlyReadOnly.ps1':friday.transform('next',prior['next']),
        'Prepare-No11WeeklyAfterCloseReadOnly.ps1':friday.transform('weekly',prior['weekly']),
        'Prepare-No11PreviousArchiveReadOnly.ps1':(ENGINE/'windows/Prepare-No11PreviousArchiveReadOnly.ps1').read_bytes(),
        'worker.py':pathfix.patch_worker(friday.transform('worker',prior['worker']))}


class SourceTests(unittest.TestCase):
    def test_all_collectors_actual_sources_and_bom_crlf(self):
        for name,raw in installed_sources().items():
            if not any(name==s+'.ps1' for s in installer.STEMS):continue
            for nl in ('\n','\r\n'):
                with self.subTest(name=name,nl=nl):
                    text=raw.decode('utf-8-sig').replace('\r\n','\n')
                    before=b'\xef\xbb\xbf'+text.replace('\n',nl).encode()
                    after=installer.transform_collector(before)
                    self.assertTrue(after.startswith(b'\xef\xbb\xbf'))
                    self.assertEqual(installer.transform_collector(after),after)
                    self.assertIn(b'Get-No11RegisteredDataBooks $excel',after)
                    self.assertNotIn(b"Workbooks.Item('Ark_No11_MSII_RSS.xlsx')",after)
                    self.assertNotIn(b"Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')",after)
                    self.assertNotIn(b'NO11_NIGHTLY_ORDER_BOOK_IDENTITY_CHANGED',after)
                    self.assertIn(b'foreach($wb in $nightlyDataBooks.Originals)',after)
                    self.assertIn(b'$BatchSize=47',after)
                    if nl=='\r\n':self.assertNotIn(b'\n',after.replace(b'\r\n',b''))

    def test_only_resolution_and_original_capacity_targets_changed(self):
        for name,raw in installed_sources().items():
            if not any(name==s+'.ps1' for s in installer.STEMS):continue
            text=raw.decode('utf-8-sig').replace('\r\n','\n')
            new=installer.transform_collector(raw).decode('utf-8-sig').replace('\r\n','\n')
            for token in ("'=RssChart", 'Read-DailyRows', 'Save-Capture', 'RssStockOrder('):
                self.assertEqual(text.count(token),new.count(token))
            # The actual collection loop and all receipt-writing logic remain.
            marker='  for($offset=' if name.startswith('Run-') else ' for($offset='
            a=text.index(marker);b=new.index(marker)
            self.assertEqual(text[a:],new[b:])
        pool=installer.transform_collector(installed_sources()['Run-No11WeeklyCandidateRefreshReadOnly.ps1']).decode('utf-8-sig')
        self.assertIn('if($count -eq $script:No11DataOriginalBookCount){return}',pool)
        self.assertIn('if($count -ne ($script:No11DataOriginalBookCount+1))',pool)

    def test_helper_never_opens_saves_converts_or_reads_account_cells(self):
        text=(HERE/installer.HELPER).read_text(encoding='utf-8-sig')
        for token in ('Workbooks.Open','SaveAs(','.Save(','.Close(','.Range(','.Value2','RssStockOrder('):
            self.assertNotIn(token,text)
        self.assertIn('AccessibleObjectFromWindow',text)
        self.assertIn('REGISTERED_PATH_MISMATCH_',text)


class InstallTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.store=self.root/'store';self.engine=self.root/'engine'
        (self.store/'oneclick').mkdir(parents=True);(self.engine/'windows').mkdir(parents=True)
        self.ui=self.store/'oneclick/Start-No11OneClick.ps1';self.ui.write_bytes(b'WHITE GUI')
        self.settings=self.store/'settings.json'
        self.settings.write_bytes(n.encode({'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
           'orderIdWorkbookPath':'UNCHANGED_LIVE.xlsx','orderTransmission':False,'automaticOrderAuthorization':False}))
        self.trade=self.engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1';self.trade.write_bytes(b'LIVE CODE UNCHANGED')
        self.legacy=self.store/'legacy';self.legacy.mkdir()
        raw=installed_sources()
        for name,data in raw.items():
            if name.endswith('.ps1'):(self.engine/'windows'/name).write_bytes(data)
        self.worker=self.legacy/installer.WORKER;self.worker.write_bytes(raw['worker.py'])
        self.validator=self.legacy/installer.VALIDATOR;self.validator.write_bytes((HERE/installer.VALIDATOR).read_bytes())
        self.b={'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1','orderTransmission':False,
           'engine':str(self.engine),'nightlyResumeTool':str(self.worker),
           'nightlyResumeToolSha256':n.digest(self.worker.read_bytes()),
           'nightlyResumeValidatorSha256':n.digest(self.validator.read_bytes()),'transportProbe':'LIVE_UNCHANGED'}
        self.binding=self.store/'automatic-inputs.json';self.binding.write_bytes(n.encode(self.b))
        self.books=self.root/'actual-books';self.books.mkdir()
        names={'Account':'Ark_No11_MSII_RSS (version 1).xlsb','Market':'Ark_No11_MARKET_RSS (version 1).xlsb','OrderIds':'Ark_No11_BROKER_READONLY (version 1).xlsb'}
        self.record={'schemaId':'ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1','orderTransmission':False,'books':[]}
        for role,sheet in installer.ROLES.items():
            p=self.books/names[role];p.write_bytes(b'FILE FIXTURE NOT AN EXCEL DOCUMENT')
            self.record['books'].append({'role':role,'sheet':sheet,'path':str(p),'name':p.name,'date1904':False})
        self.prior={p:p.read_bytes() for p in (self.ui,self.settings,self.trade,self.worker,self.validator,*self.books.iterdir())}
        self.oldlog=self.store/'failed-old-capture.log';self.oldlog.write_bytes(b'OLD ZERO CAPTURE LOG')

    def run_install(self,apply=False):return installer.install(self.store,HERE,apply,test_record=self.record)

    def check(self):
        for p,raw in self.prior.items():self.assertEqual(p.read_bytes(),raw)
        now=n.read(self.binding)
        self.assertEqual(now['transportProbe'],self.b['transportProbe'])
        self.assertFalse(now['orderTransmission'])
        record=n.read(Path(now['dataWorkbookRegistration']))
        self.assertEqual(record,self.record)
        self.assertEqual(n.digest(Path(now['dataWorkbookResolver']).read_bytes()),now['dataWorkbookResolverSha256'])
        for stem in installer.STEMS:self.assertIn(installer.MARK.encode(),(self.engine/'windows'/(stem+'.ps1')).read_bytes())
        self.assertEqual(self.oldlog.read_bytes(),b'OLD ZERO CAPTURE LOG')

    def test_audit_only(self):
        before=self.binding.read_bytes();self.assertEqual(self.run_install(),'READY')
        self.assertEqual(self.binding.read_bytes(),before)
        self.assertFalse((self.store/installer.JOURNAL).exists())
        for p,raw in self.prior.items():self.assertEqual(p.read_bytes(),raw)

    def test_apply_idempotent_and_preserves_live_and_workbooks(self):
        self.assertEqual(self.run_install(True),'PASS');self.check()
        self.assertEqual(self.run_install(True),'ALREADY_APPLIED');self.check()

    def test_interrupted_after_collector_write_can_resume(self):
        actual=installer.replace
        def crash(p,a,b):actual(p,a,b);raise KeyboardInterrupt()
        with patch.object(installer,'replace',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):self.run_install(True)
        self.assertEqual(n.checkpoint(self.store/installer.JOURNAL)['phase'],'PREPARED')
        self.assertEqual(self.run_install(True),'PASS');self.check()

    def test_interrupted_after_binding_switch_can_resume(self):
        actual=installer.replace
        def crash(p,a,b):
            actual(p,a,b)
            if p==self.binding:raise KeyboardInterrupt()
        with patch.object(installer,'replace',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):self.run_install(True)
        self.assertEqual(self.run_install(True),'PASS');self.check()

    def test_bad_registration_does_not_write(self):
        self.record['books'][2]['role']='Account'
        before=self.binding.read_bytes()
        with self.assertRaisesRegex(ValueError,'BOOK_ROLE_NOT_UNIQUE'):self.run_install(True)
        self.assertEqual(self.binding.read_bytes(),before)

    def test_local_unknown_script_is_not_overwritten(self):
        p=self.engine/'windows'/('Run-No11RssDailyTrendCensusReadOnly.ps1');p.write_bytes(b'UNKNOWN')
        with self.assertRaisesRegex(ValueError,'THREE_BOOK_BLOCK_NOT_RECOGNIZED'):self.run_install(True)
        self.assertEqual(p.read_bytes(),b'UNKNOWN')

    def test_actual_referenced_clean_collector_is_migrated_too(self):
        canonical=self.engine/'windows'/'Capture-No11RssTrainingBatchReadOnly.ps1'
        other=canonical.with_name('Capture-No11RssTrainingBatchReadOnly.Clean.ps1');other.write_bytes(canonical.read_bytes())
        caller=self.engine/'windows/Prepare-No11PreviousArchiveReadOnly.ps1'
        caller.write_bytes(caller.read_bytes().replace(canonical.name.encode(),other.name.encode()))
        self.assertEqual(self.run_install(True),'PASS')
        self.assertIn(installer.MARK.encode(),other.read_bytes());self.check()

if __name__=='__main__':unittest.main(verbosity=2)
