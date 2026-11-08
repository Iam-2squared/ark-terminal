"""Reproduce the user's supplied pool CODE SNIPPETS, not their entire file.

No assertion claims the synthetic fixture has the user's whole-file SHA256.
Native capture, COM attachment and source validation are retained untouched.
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import no11_update_path as p
import install_no11_launcher_update as installer
import test_no11_update_path as native_tests
import test_no11_launcher_update_install as install_tests

START_STANDARD = '''  $ceiling=SafePhysicalBatch $existing $BatchSize
  $physical=if($AutoMaxThroughput){[Math]::Min(5,$ceiling)}else{$ceiling}
  $fullWaves=0'''
START_OBSERVED = '''  $physical=SafePhysicalBatch $existing $BatchSize
  $ceiling=$physical;$fullWaves=0'''
RAMP_STANDARD = '''   }elseif($physical -lt $ceiling){
    $fullWaves++
    if($AutoMaxThroughput -or $fullWaves -ge 2){
     $physical=if($AutoMaxThroughput){
      NextAutoMaxBatch $physical $ceiling $true
     }else{
      [Math]::Min($ceiling,$physical+5)
     }
     $fullWaves=0
     Write-Host ('NO11_DAILY_BATCH_TUNE=FULL_WAVES_RAISED_TO_{0}' -f $physical)
    }
   }'''
RAMP_OBSERVED = '''   }elseif($physical -lt $ceiling){
    $fullWaves++
    if($fullWaves -ge 2){
     $physical=[Math]::Min($ceiling,$physical+5)
     $fullWaves=0
     Write-Host ('NO11_DAILY_BATCH_TUNE=FULL_WAVES_RAISED_TO_{0}' -f $physical)
    }
   }'''


def replace_one(text, old, new):
    if text.count(old)!=1:
        raise AssertionError('FIXTURE_SOURCE_CONTEXT_CHANGED: '+old[:80])
    return text.replace(old,new,1)


def observed_plain_fixture(*, embedded_selftest=True, newline='\n', bom=False):
    raw=native_tests.NativeUpdateTests().originals()['pool']
    text=raw.decode('utf-8-sig').replace('\r\n','\n')
    text=replace_one(text,START_STANDARD,START_OBSERVED)
    text=replace_one(text,RAMP_STANDARD,RAMP_OBSERVED)
    text=replace_one(text,' [switch]$AutoMaxThroughput,\n','')
    text=replace_one(text,'''  if($AutoMaxThroughput){
   Write-Host ('NO11_DAILY_AUTOMAX=ADAPTIVE_5_TO_{0}|EXCEL_CHART_CAP=50|RESERVED=3|CURRENT_BATCH={1}' -f $ceiling,$physical)
  }
''','')
    start=text.index('function NextAutoMaxBatch(')
    end=text.index('# Excel can briefly reject',start)
    text=text[:start]+text[end:]
    if embedded_selftest:
        start=text.index(' $batch=5\n')
        end=text.index(' if($script:DailyExcelOp',start)
        text=text[:start]+text[end:]
    else:
        start=text.index('if($OfflineSelfTest){\n')
        end=text.index('\n$tool=',start)
        text=text[:start]+text[end+1:]
        text=replace_one(text,' [switch]$OfflineSelfTest,\n','')
    if '$AutoMaxThroughput' in text or 'NextAutoMaxBatch' in text:
        raise AssertionError('FIXTURE_MUST_NOT_KEEP_REMOVED_AUTOMAX')
    return (b'\xef\xbb\xbf' if bom else b'')+text.replace('\n',newline).encode('utf-8')


class ObservedPlainPoolTests(unittest.TestCase):
    def test_observed_start_and_ramp_migrate_without_automax(self):
        raw=observed_plain_fixture()
        self.assertIn(START_OBSERVED.encode(),raw)
        self.assertIn(RAMP_OBSERVED.encode(),raw)
        result=p.transform('pool',raw)
        text=result.decode('utf-8-sig')
        self.assertIn('$BatchSize=47,',text)
        self.assertIn('$ceiling=SafePhysicalBatch $existing $BatchSize',text)
        self.assertIn('$physical=$ceiling;$fullWaves=0',text)
        self.assertIn('$waveEnd=[Math]::Min($remaining.Count,$offset+$physical)',text)
        self.assertIn('CLEAN_WAVE_RESTORED_MAX_',text)
        self.assertNotIn('if($fullWaves -ge 2)',text)
        self.assertNotIn('$AutoMaxThroughput',text)
        self.assertNotIn('NextAutoMaxBatch',text)
        self.assertEqual(p.transform('pool',result),result)

    def test_optional_embedded_selftest_not_required(self):
        raw=observed_plain_fixture(embedded_selftest=False)
        result=p.transform('pool',raw)
        self.assertNotIn(b'OfflineSelfTest',result)
        self.assertNotIn(b'NO11_DAILY_ACTUAL_MAX47_WAVE_SELFTEST',result)
        self.assertIn(b'$BatchSize=47',result)
        self.assertIn(b'CLEAN_WAVE_RESTORED_MAX_',result)

    def test_bom_and_crlf_kept_on_both_local_variants(self):
        for embedded in (True,False):
            for bom in (True,False):
                for newline in ('\n','\r\n'):
                    with self.subTest(embedded=embedded,bom=bom,newline=newline):
                        raw=observed_plain_fixture(embedded_selftest=embedded,newline=newline,bom=bom)
                        result=p.transform('pool',raw)
                        self.assertEqual(result.startswith(b'\xef\xbb\xbf'),bom)
                        if newline=='\r\n':
                            self.assertNotIn(b'\n',result.replace(b'\r\n',b''))
                        self.assertEqual(p.transform('pool',result),result)

    def test_capture_and_com_operations_are_not_rewritten(self):
        raw=observed_plain_fixture()
        result=p.transform('pool',raw)
        for start,end in ((b'function Invoke-ExcelIdempotent',b'function New-ExcelComObjectChecked'),
                          (b'function Save-Capture',b'if($OfflineSelfTest)'),
                          (b"   $batch=@($remaining",b'   $offset=$waveEnd')):
            # These sections contain all actual Excel/RSS capture/write logic.
            before=raw[raw.index(start):raw.index(end,raw.index(start))]
            after=result[result.index(start):result.index(end,result.index(start))]
            self.assertEqual(after,before)
        self.assertIn(b'ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1',result)

    def test_unreviewed_plain_start_is_not_guessed(self):
        raw=observed_plain_fixture().replace(b'$ceiling=$physical;$fullWaves=0',
                                            b'$ceiling=1;$fullWaves=0')
        with self.assertRaises(p.SourceAnchorChanged):
            p.transform('pool',raw)

    def test_unreviewed_plain_ramp_is_not_guessed(self):
        raw=observed_plain_fixture().replace(b'if($fullWaves -ge 2)',b'if($fullWaves -ge 99)')
        with self.assertRaises(p.SourceAnchorChanged):
            p.transform('pool',raw)

    def test_actual_installer_accepts_plain_pool_and_keeps_white_ui(self):
        fixture=install_tests.LauncherInstallTests(methodName='test_preflight_does_not_modify_launcher_or_engine')
        fixture.setUp()
        try:
            pool=fixture.paths['pool']
            pool.write_bytes(observed_plain_fixture(embedded_selftest=False,newline='\r\n',bom=True))
            expected=p.transform('pool',pool.read_bytes())
            white=fixture.white.read_bytes()
            self.assertEqual(installer.install(fixture.store,do_apply=False,_test=True),'READY')
            self.assertEqual(installer.install(fixture.store,do_apply=True,_test=True),'PASS')
            self.assertEqual(pool.read_bytes(),expected)
            self.assertEqual(fixture.white.read_bytes(),white)
            self.assertEqual(installer.install(fixture.store,do_apply=True,_test=True),'ALREADY_APPLIED')
        finally:
            fixture.doCleanups()

    def test_interrupted_install_restores_and_retries_plain_pool(self):
        fixture=install_tests.LauncherInstallTests(methodName='test_preflight_does_not_modify_launcher_or_engine')
        fixture.setUp()
        try:
            pool=fixture.paths['pool']
            pool.write_bytes(observed_plain_fixture())
            expected=p.transform('pool',pool.read_bytes())
            real_replace=installer.atomic_replace
            def crash(path,before,after):
                real_replace(path,before,after)
                if path==pool:
                    raise KeyboardInterrupt('mock loss after pool write')
            with patch.object(installer,'atomic_replace',side_effect=crash):
                with self.assertRaises(KeyboardInterrupt):
                    installer.install(fixture.store,do_apply=True,_test=True)
            self.assertEqual(installer.install(fixture.store,do_apply=True,_test=True),'PASS')
            self.assertEqual(pool.read_bytes(),expected)
            self.assertEqual(fixture.white.read_bytes(),fixture.before[fixture.white])
        finally:
            fixture.doCleanups()

if __name__=='__main__':
    unittest.main(verbosity=2)
