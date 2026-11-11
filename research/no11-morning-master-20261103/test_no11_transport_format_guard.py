"""No-orders regression of actual V3 resilient transport one-time BD4 format.

Replays the real precise 2026-11-10 11:16 source-line=193 failure. The
fixture does not attach to Excel or dispatch/cancel anything.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import patch_no11_transport_resilience as resilient
import no11_transport_format_guard as fix

class TransportFormulaGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=(HERE/'Prepare-No11AutomaticLiveTransportV3.ps1').read_bytes()
        cls.old=resilient.transform(source)
        cls.changed=fix.transform(cls.old)
        cls.old_text=cls.old.decode('utf-8-sig').replace('\r\n','\n')
        cls.new_text=cls.changed.decode('utf-8-sig').replace('\r\n','\n')

    def test_real_193_line_is_format_write(self):
        # Guaranteed source line mapping for the unchanged V3 resilient patch.
        self.assertEqual(self.old_text.splitlines()[192].strip(),
                         "$formula.NumberFormat='General'")
        self.assertEqual(self.old_text.splitlines()[188].strip(),
                         "$script:TransportStage='SESSION_WRITE_ONCE'")

    def test_exact_single_format_change_before_all_control_writes(self):
        old=self.old_text
        new=self.new_text
        a=old.index(fix.BEFORE)
        b=new.index(fix.AFTER)
        self.assertEqual(old[:a],new[:b])
        self.assertEqual(old[a+len(fix.BEFORE):],new[b+len(fix.AFTER):])
        self.assertLess(new.index(" $formula.NumberFormat='General'"),
                        new.index(" $guard.Value2='ARK_NO11_SEND_ONCE'"))
        self.assertEqual(new.count("$formula.NumberFormat='General'"),1)
        self.assertEqual(new.count("$guard.Value2='ARK_NO11_SEND_ONCE'"),1)
        self.assertEqual(new.count("$trigger.Value2=0"),1)
        self.assertEqual(new.count("$session.Value2=$sessionKey"),1)
        self.assertNotIn("$trigger.Value2=1",new)

    def test_same_day_and_orig_protective_source_unchanged(self):
        for marker in ('SAME_DAY_OPERATOR_APPROVAL_REQUIRED',
            'ACTUAL_SESSION_DAY_REQUIRED','MARKET_SESSION_REQUIRED',
            'ORDER_WORKBOOK_IDENTITY','TRIGGER_ALREADY_NONZERO',
            'SESSION_INITIALIZATION_READBACK','RSS_ADDINS_NOT_UNIQUE',
            'Assert-No11TransportSessionStable',
            'ORDER_TRIGGER_WRITTEN_TO_ONE=False',
            'ORDER_SENT=False'):
            self.assertIn(marker,self.new_text)
        self.assertIn('UNKNOWN_PREVIOUS_SESSION',self.new_text)
        self.assertIn('UNKNOWN_PREVIOUS_GUARD',self.new_text)
        self.assertIn('FORMULA_GENERAL_UNVERIFIED',self.new_text)

    def test_bom_crlf_and_unknown_source_fail_closed(self):
        crlf=b'\xef\xbb\xbf'+self.old.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        changed=fix.transform(crlf)
        self.assertTrue(changed.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n',changed.replace(b'\r\n',b''))
        self.assertEqual(changed,fix.transform(changed))
        with self.assertRaisesRegex(ValueError,'EXPECTED_PINNED'):
            fix.transform(b'UNKNOWN_SOURCE')
        with self.assertRaisesRegex(ValueError,'EXPECTED_PINNED'):
            fix.transform(self.old.replace(b'ORDER_SENT=False',b'ORDER_SENT=True'))

    @unittest.skipUnless(os.name=='nt','PowerShell 5.1 Windows-only')
    def test_powershell_mock_of_prewrite_partial_guard_and_bd4_format(self):
        script=fix.AFTER
        cases=(
            ('General','','','PASS','ALREADY_VALID'),
            ('General','ARK_NO11_SEND_ONCE','SAMESESSION','PASS','ALREADY_VALID'),
            ('@','','','PASS','CHANGED_ONCE'),
            ('General','UNKNOWN','SAMESESSION','BLOCK','UNKNOWN_PREVIOUS_GUARD'),
            ('General','ARK_NO11_SEND_ONCE','OTHERSESSION','BLOCK','UNKNOWN_PREVIOUS_SESSION')
        )
        for initial,guard,session,status,expected in cases:
            with self.subTest(initial=initial,guard=guard,session=session):
                harness="""$ErrorActionPreference='Stop'
function Need([bool]$value,[string]$reason){if(-not $value){throw $reason}}
$script:TransportStage='PRECHECK'
$guard=[pscustomobject]@{Value2='%s'}
$trigger=[pscustomobject]@{Value2=[double]0}
$session=[pscustomobject]@{Value2='%s'}
$formula=[pscustomobject]@{NumberFormat='%s'}
$sessionKey='SAMESESSION'
try{
%s
Write-Host 'RESULT=PASS'
}catch{
Write-Host ('RESULT=BLOCK|'+$_.Exception.Message)
}
Write-Host ('BD1='+[string]$guard.Value2)
Write-Host ('BD2='+[string]$trigger.Value2)
Write-Host ('BD3='+[string]$session.Value2)
Write-Host ('FORMAT='+[string]$formula.NumberFormat)
"""%(guard,session,initial,script)
                with tempfile.TemporaryDirectory(prefix='ark-no11-bd4-mock-') as t:
                    script_file=Path(t)/'case.ps1'
                    script_file.write_text(harness,encoding='utf-8-sig')
                    result=subprocess.run(['powershell.exe','-NoProfile',
                        '-NonInteractive','-ExecutionPolicy','Bypass',
                        '-File',str(script_file)],text=True,encoding='utf-8',
                        errors='replace',capture_output=True,
                        timeout=25,check=False)
                self.assertEqual(result.returncode,0,result.stderr)
                if status=='PASS':
                    self.assertIn('RESULT=PASS',result.stdout)
                    self.assertIn('FORMAT=General',result.stdout)
                    self.assertIn('BD1=ARK_NO11_SEND_ONCE',result.stdout)
                    self.assertIn('BD2=0',result.stdout)
                    self.assertIn('BD3=SAMESESSION',result.stdout)
                    self.assertIn('AUTOMATIC_TRANSPORT_FORMULA_GENERAL='+expected,
                                  result.stdout)
                else:
                    self.assertIn('RESULT=BLOCK|'+expected,result.stdout)
                    self.assertIn('BD2=0',result.stdout)
                    self.assertNotIn('RESULT=PASS',result.stdout)

if __name__=='__main__':unittest.main(verbosity=2)
