"""Compatibility fixtures reproduce local configuration changes, not live RSS."""
import contextlib
import io
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import no11_update_path as p
import install_no11_launcher_update as installer
import test_no11_update_path as source_tests
import test_no11_launcher_update_install as install_tests


class CompatibleLocalSourceTests(unittest.TestCase):
    def sources(self):
        return source_tests.NativeUpdateTests().originals()

    def test_known_parameter_defaults_and_already_maximum(self):
        original=self.sources()['weekly']
        for value, upper in ((5,20),(20,20),(30,47),(40,47),(47,47),(50,50)):
            with self.subTest(default=value,upper=upper):
                local=original.replace(b'[ValidateRange(1,20)][int]$FullBatchSize=10,',
                    ('[ValidateRange(1,%s)][int]$FullBatchSize=%s,'%(upper,value)).encode())
                fixed=p.transform('weekly',local)
                self.assertIn(b'$FullBatchSize=47,',fixed)
                self.assertIn(b'$RefreshBatchSize=47,',fixed)
                self.assertIn(b'$MinuteBatchSize=47,',fixed)
                self.assertEqual(p.transform('weekly',fixed),fixed)

    def test_parameter_spacing_and_crlf_bom_preserved(self):
        original=self.sources()['weekly'].decode('utf-8-sig').replace('\r\n','\n')
        local=original.replace('[ValidateRange(1,20)][int]$FullBatchSize=10,',
                              '[ValidateRange(1, 47)] [int] $FullBatchSize = 47,')
        raw=b'\xef\xbb\xbf'+local.replace('\n','\r\n').encode()
        out=p.transform('weekly',raw)
        self.assertTrue(out.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n',out.replace(b'\r\n',b''))
        self.assertIn(b'$FullBatchSize=47',out)

    def test_deleted_optional_orchestrator_automax_not_recreated(self):
        original=self.sources()['weekly'].replace(b'\r\n',b'\n')
        needle=b" if($RefreshAutoMaxThroughput){$rargs+=@('-AutoMaxThroughput')}"
        for newline in (b'\n',b'\r\n'):
            with self.subTest(newline=newline):
                source=original.replace(b'\n',newline)
                self.assertEqual(source.count(needle),1)
                local=source.replace(needle,b'',1)
                self.assertNotIn(b"$rargs+=@('-AutoMaxThroughput')",local)
                fixed=p.transform('weekly',local)
                self.assertNotIn(b"$rargs+=@('-AutoMaxThroughput')",fixed)
                self.assertIn(b'ARK_NO11_FIRST_WEEK_429_VERIFIED_FRIDAY_CARRY_V1',fixed)
                self.assertIn(b'$FullBatchSize=47',fixed)
                if newline==b'\r\n':
                    self.assertNotIn(b'\n',fixed.replace(b'\r\n',b''))

    def test_source_anchor_whitespace_not_semantic_change(self):
        source=self.sources()['daily']
        local=source.replace(b'for($offset=0;$offset -lt $remaining.Count;$offset+=$BatchSize)',
                            b'for ( $offset = 0 ; $offset -lt $remaining.Count ; $offset += $BatchSize )')
        fixed=p.transform('daily',local)
        self.assertIn(b'$offset+=$physical',fixed)
        self.assertIn(b'$physical=[Math]::Min($BatchSize,50-$existing-3)',fixed)

    def test_changed_string_literal_does_not_match(self):
        source=self.sources()['daily']
        local=source.replace(b"'NO11_DAILY_CHART_CAPACITY_EXCEEDED'",b"'UNREVIEWED_LOCAL_BEHAVIOR'")
        with self.assertRaises(p.SourceAnchorChanged) as error:
            p.transform('daily',local)
        self.assertRegex(error.exception.anchor_id,r'^[a-f0-9]{16}$')

    def test_duplicate_batch_declarations_not_accepted(self):
        source=self.sources()['weekly']
        local=source.replace(b'[ValidateRange(1,20)][int]$FullBatchSize=10,',
                            b'[ValidateRange(1,47)][int]$FullBatchSize=47,\n [ValidateRange(1,47)][int]$FullBatchSize=47,')
        with self.assertRaises(p.SourceAnchorChanged):
            p.transform('weekly',local)

    def test_declaration_does_not_modify_unrelated_local_clean_paths(self):
        source=self.sources()['weekly']
        local=source.replace(b'Prepare-No11NextSessionNightlyReadOnly.ps1',
                             b'Prepare-No11NextSessionNightlyReadOnly.Clean.ps1')
        local=local.replace(b'$FullBatchSize=10',b'$FullBatchSize=20')
        fixed=p.transform('weekly',local)
        self.assertIn(b'Prepare-No11NextSessionNightlyReadOnly.Clean.ps1',fixed)
        self.assertIn(b'$FullBatchSize=47',fixed)

    def test_optional_telemetry_absent_in_clean_variant(self):
        needle="   Write-Host ('NO11_DAILY_AUTOMAX=ADAPTIVE_5_TO_{0}|EXCEL_CHART_CAP=50|RESERVED=3|CURRENT_BATCH={1}' -f $ceiling,$physical)"
        self.assertEqual(p.once('  $physical=$ceiling\n',needle,'  Write-Host "new"'),
                         '  $physical=$ceiling\n')

    def test_complete_kind_report_precedes_any_native_source_write(self):
        fixture=install_tests.LauncherInstallTests(methodName='test_preflight_does_not_modify_launcher_or_engine')
        fixture.setUp()
        try:
            broken=fixture.paths['daily']
            broken.write_bytes(broken.read_bytes().replace(b'$BatchSize=20',b'$BatchSize=19'))
            originals={path:path.read_bytes() for path in fixture.paths.values()}
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                with self.assertRaisesRegex(ValueError,'NO11_UPDATE_PATH_DAILY_SOURCE_ANCHOR_CHANGED'):
                    installer.install(fixture.store,do_apply=True,_test=True)
            self.assertIn('NO11_UPDATE_FAILED_FILE=Run-No11RssDailyTrendCensusReadOnly.ps1',output.getvalue())
            self.assertIn('NO11_UPDATE_FAILED_KIND=DAILY',output.getvalue())
            self.assertIn('NO11_UPDATE_ANCHOR_ID=',output.getvalue())
            self.assertIn('NO11_UPDATE_SOURCE=MINUTES|READY',output.getvalue())
            self.assertFalse((fixture.store/'launcher-max47-install-transaction.json').exists())
            for path,raw in originals.items():
                self.assertEqual(path.read_bytes(),raw)
        finally:
            fixture.doCleanups()

if __name__=='__main__':
    unittest.main(verbosity=2)
