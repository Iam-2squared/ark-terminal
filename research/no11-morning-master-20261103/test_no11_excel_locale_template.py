import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / 'no12-prebuy-causal-runtime-20261011'
sys.path.insert(0, str(HERE))
import no11_nightly_resume as n
import patch_no11_transport_resilience as resilience
import no11_transport_format_guard as first
import no11_excel_locale_template as fix
import install_no11_excel_locale_template as installer


class LocaleTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = first.transform(resilience.transform(
            (HERE / 'Prepare-No11AutomaticLiveTransportV3.ps1').read_bytes()))
        cls.sender = (ENGINE / 'windows/Invoke-No11MsiiOrder.ps1').read_bytes()
        cls.js = (ENGINE / 'tools/no11_msii_transport.mjs').read_bytes()

    def test_original_creator_values_not_inferred_from_lengths(self):
        creator = (ENGINE / 'windows/New-No11BrokerReadOnlyWorkbook.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('<t>DISABLED</t>', creator)
        self.assertIn('<t>UNCONFIGURED_RSS_SESSION</t>', creator)
        self.assertEqual(len('DISABLED'), 8)
        self.assertEqual(len('UNCONFIGURED_RSS_SESSION'), 24)
        self.assertIn("$previousGuard -ceq 'DISABLED'", fix.NEW_STATE)
        self.assertIn("$previousSession -ceq 'UNCONFIGURED_RSS_SESSION'", fix.NEW_STATE)
        self.assertNotIn('.Length', fix.NEW_STATE)

    def test_exact_source_scope_and_idempotence(self):
        out = fix.transform_probe(self.probe)
        self.assertEqual(out, fix.transform_probe(out))
        old, nl, bom = fix.unpack(self.probe)
        text = fix.unpack(out)[0]
        restored = text.replace(fix.HELPER + '\n', '', 1).replace(
            fix.NEW_STATE, fix.OLD_STATE, 1).replace(fix.NEW_FORMAT, fix.OLD_FORMAT, 1)
        self.assertEqual(restored, old)
        self.assertEqual(text.count('$trigger.Value2=0'), 1)
        self.assertNotIn('$trigger.Value2=1', text)
        self.assertEqual(text.count("$formula.NumberFormat='General'"), 1)
        for s in ('ACTUAL_SESSION_DAY_REQUIRED', 'SAME_DAY_OPERATOR_APPROVAL_REQUIRED',
                  'TRIGGER_ALREADY_NONZERO', 'ORDER_WORKBOOK_IDENTITY'):
            self.assertIn(s, text)
        for source, function in ((self.sender, fix.transform_sender), (self.js, fix.transform_js)):
            candidate = function(source)
            self.assertEqual(candidate, function(candidate))
        sender = fix.unpack(fix.transform_sender(self.sender))[0]
        original = fix.unpack(self.sender)[0]
        restored = sender.replace(fix.HELPER + '\n', '', 1).replace(
            '(Test-No11LocaleGeneral $formula)', "[string]$formula.NumberFormat -ceq 'General'", 1)
        self.assertEqual(restored, original)
        self.assertEqual(sender.count('$state.trigger.Value2=1'), 1)

    def test_non_ascii_not_added_and_bom_crlf_preserved(self):
        self.assertTrue(fix.HELPER.isascii())
        self.assertTrue(fix.NEW_STATE.isascii())
        self.assertTrue(fix.NEW_FORMAT.isascii())
        base = self.probe.decode('utf-8-sig').replace('\r\n', '\n')
        source = b'\xef\xbb\xbf' + base.replace('\n', '\r\n').encode()
        out = fix.transform_probe(source)
        self.assertTrue(out.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n', out.replace(b'\r\n', b''))
        self.assertEqual(fix.HELPER.encode().decode('cp932'), fix.HELPER)

    @unittest.skipUnless(os.name == 'nt', 'Windows PowerShell 5.1')
    def test_exact_states_and_locale_use_real_powershell_without_com(self):
        ja = "(-join [char[]]@(0x47,0x2f,0x6a19,0x6e96))"
        key = 'a' * 64
        cases = [
            ('DISABLED', 'UNCONFIGURED_RSS_SESSION', ja, ja, True, 0),
            ('DISABLED', 'UNCONFIGURED_RSS_SESSION', "'General'", ja, True, 0),
            ('DISABLED', 'UNCONFIGURED_RSS_SESSION', "'General'", "'General'", True, 0),
            ('ARK_NO11_SEND_ONCE', key, ja, ja, True, 0),
            ('', '', ja, ja, True, 0),
            ('DISABLED', 'UNCONFIGURED_RSS_SESSION', "'@'", "'@'", True, 1),
            ('12345678', 'z' * 24, ja, ja, False, 0),
            ('DISABLED', key, ja, ja, False, 0),
            ('ARK_NO11_SEND_ONCE', 'UNCONFIGURED_RSS_SESSION', ja, ja, False, 0),
            ('ARK_NO11_SEND_ONCE', 'b' * 64, ja, ja, False, 0),
        ]
        with tempfile.TemporaryDirectory() as d:
            for guard, session, fmt, loc, success, writes in cases:
                with self.subTest(guard=guard, session=session, fmt=fmt):
                    body = """$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Need([bool]$ok,[string]$code){if(-not $ok){throw $code}}
%s
$guard=[pscustomobject]@{Value2='%s'}
$session=[pscustomobject]@{Value2='%s'}
$trigger=[pscustomobject]@{Value2=[double]0}
$sessionKey='%s'
$formula=[pscustomobject]@{Data=%s;LocalData=%s;SetCount=0}
$formula|Add-Member -MemberType ScriptProperty -Name NumberFormat -Value {$this.Data} -SecondValue {param($v) $this.SetCount++;$this.Data=[string]$v;$this.LocalData=[string]$v}
$formula|Add-Member -MemberType ScriptProperty -Name NumberFormatLocal -Value {$this.LocalData}
try{
%s
%s
$guard.Value2='ARK_NO11_SEND_ONCE'
$trigger.Value2=0
$session.Value2=$sessionKey
Write-Host 'RESULT=PASS'
}catch{Write-Host ('RESULT=BLOCK|'+$_.Exception.Message)}
Write-Host ('FORMAT_WRITES='+$formula.SetCount)
Write-Host ('TRIGGER='+$trigger.Value2)
""" % (fix.HELPER, guard, session, key, fmt, loc, fix.NEW_STATE, fix.NEW_FORMAT)
                    file = Path(d) / 'case.ps1'
                    file.write_text(body, encoding='ascii')
                    r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                        '-ExecutionPolicy', 'Bypass', '-File', str(file)], capture_output=True,
                        text=True, encoding='utf-8', errors='replace', timeout=30)
                    self.assertEqual(r.returncode, 0, r.stderr)
                    self.assertIn('RESULT=PASS' if success else 'RESULT=BLOCK|', r.stdout)
                    self.assertIn('FORMAT_WRITES=' + str(writes), r.stdout)
                    self.assertIn('TRIGGER=0', r.stdout)
            installer.check_syntax(fix.transform_probe(self.probe), fix.transform_sender(self.sender))
            candidate = Path(d) / 'sender.ps1'
            candidate.write_bytes(fix.transform_sender(self.sender))
            r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                '-ExecutionPolicy', 'Bypass', '-File', str(candidate), '-OfflineSelfTest'],
                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertIn('PASS_OFFLINE_MOCK_ONLY', r.stdout)

    @unittest.skipUnless(shutil.which('node'), 'Node required')
    def test_native_transport_regression_against_patched_module(self):
        file = ENGINE / 'tools/no11_msii_transport.mjs'
        original = file.read_bytes()
        tests = sorted((ENGINE / 'tests').glob('*msii_transport*.test.mjs'))
        self.assertTrue(tests, 'Actual native transport test suite must exist')
        try:
            file.write_bytes(fix.transform_js(original))
            r = subprocess.run(['node', '--test', *map(str, tests)],
                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        finally:
            file.write_bytes(original)
        self.assertEqual(file.read_bytes(), original)

    def fixture(self, root):
        store = root / 'store'; store.mkdir()
        engine = root / 'engine'
        (engine / 'windows').mkdir(parents=True)
        (engine / 'tools').mkdir()
        sender = engine / 'windows/Invoke-No11MsiiOrder.ps1'; sender.write_bytes(self.sender)
        (engine / 'tools/no11_msii_transport.mjs').write_bytes(self.js)
        operator = engine / 'windows/Run-No11ReceivedSessionOperatorLive.ps1'
        operator.write_bytes(b'ORIGINAL_OPERATOR_ENTRY_EXIT')
        (store / 'oneclick').mkdir()
        ui = store / 'oneclick/Start-No11OneClick.ps1'; ui.write_bytes(b'WHITE_UI')
        probe = root / 'probe.ps1'; probe.write_bytes(self.probe)
        settings = store / 'settings.json'
        settings.write_bytes(n.encode({'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
            'normalMaxPositions':3,'sameDayApprovalRequired':True,
            'automaticOrderAuthorization':False,'orderTransmission':False}))
        binding = store / 'automatic-inputs.json'
        binding.write_bytes(n.encode({'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
            'orderTransmission':False,'engine':str(engine),'transportProbe':str(probe),
            'transportProbeSha256':n.digest(self.probe),'dailyCycleRoot':'UNCHANGED'}))
        frozen = {p:p.read_bytes() for p in (probe, settings, operator, ui)}
        return store, binding, frozen

    def test_install_audit_repeat_and_frozen_files(self):
        with tempfile.TemporaryDirectory() as d:
            store, binding, frozen = self.fixture(Path(d))
            before = binding.read_bytes()
            self.assertEqual(installer.install(store, test=True), 'READY')
            self.assertEqual(binding.read_bytes(), before)
            self.assertFalse((store / installer.JOURNAL).exists())
            self.assertEqual(installer.install(store, True, True), 'PASS')
            self.assertEqual(installer.install(store, True, True), 'ALREADY_APPLIED')
            b = n.read(binding)
            self.assertEqual(b['dailyCycleRoot'], 'UNCHANGED')
            self.assertFalse(b['orderTransmission'])
            self.assertEqual(n.digest(Path(b['transportProbe']).read_bytes()), b['transportProbeSha256'])
            for p, data in frozen.items():
                self.assertEqual(p.read_bytes(), data)

    def test_recover_interrupted_three_file_install(self):
        with tempfile.TemporaryDirectory() as d:
            store, binding, frozen = self.fixture(Path(d))
            original = installer.replace
            def crash(*args):
                original(*args)
                raise KeyboardInterrupt('SIMULATED_AFTER_FIRST_REPLACE')
            with patch.object(installer, 'replace', side_effect=crash):
                with self.assertRaises(KeyboardInterrupt):
                    installer.install(store, True, True)
            self.assertEqual(installer.install(store, True, True), 'PASS')
            for p, data in frozen.items():
                self.assertEqual(p.read_bytes(), data)
            Path(n.read(binding)['transportProbe']).write_bytes(b'UNKNOWN_CHANGE')
            with self.assertRaisesRegex(ValueError, 'DEPLOYED_PROBE_CHANGED'):
                installer.install(store, True, True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
