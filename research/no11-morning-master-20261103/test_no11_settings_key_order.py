"""Real PowerShell Settings() tests; never execute the launcher or broker.

The prior enrollment writes n.encode(settings), which sorts keys. The native
launcher incorrectly compares their enumeration order. These tests connect
that actual serializer, the XLSB launcher transform, and actual Settings().
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ENGINE=HERE.parent/'no12-prebuy-causal-runtime-20261011'
sys.path.insert(0,str(HERE))
import no11_nightly_resume as n
import no11_live_xlsb_contract as contract
import launcher_automatic_bridge_v4 as bridge

REPAIR=HERE/'Repair-No11SettingsKeyOrder.ps1'
OLD="(@($cfg.PSObject.Properties.Name) -join '|') -ceq ($required -join '|')"
NEW="(@($cfg.PSObject.Properties.Name | Sort-Object -CaseSensitive) -join '|') -ceq (@($required | Sort-Object -CaseSensitive) -join '|')"
PS=shutil.which('powershell.exe') if os.name=='nt' else shutil.which('pwsh')

HARNESS=r'''param([string]$Repair,[string]$Launcher,[string]$Config,[switch]$Patch)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$t=$null;$e=$null
$a=[Management.Automation.Language.Parser]::ParseFile($Repair,[ref]$t,[ref]$e)
if($e.Count){throw 'REPAIR_PARSE_FAILED'}
foreach($f in $a.FindAll({param($x) $x -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){
 . ([scriptblock]::Create($f.Extent.Text))
}
$src=[IO.File]::ReadAllText($Launcher,[Text.Encoding]::UTF8)
if($Patch){$src=Convert-No11SettingsKeyOrder $src}
Test-No11LauncherSettings $src $Config
Write-Host 'ACTUAL_SETTINGS_FUNCTION=PASS'
'''

class SettingsOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if PS is None:
            raise RuntimeError('REAL_POWERSHELL_REQUIRED_NO_SKIPPED_TESTS')

    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='ark-settings-order-')
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)/'Japanese-path-\u65e5\u672c\u8a9e'
        self.store=self.root/'ArkTerminal/No12/unified-launcher'
        self.store.mkdir(parents=True)
        self.engine=self.root/'engine'
        (self.engine/'windows').mkdir(parents=True)
        self.launcher=self.engine/'windows/Start-No11UnifiedLauncher.ps1'
        original=(ENGINE/'windows/Start-No11UnifiedLauncher.ps1').read_bytes()
        current=bridge.patch_launcher(contract.transform_launcher(original))
        # Explicit old comparison recreates the exact pre-repair PC even when
        # the permanent transform/source also receives the corrected logic.
        current=current.decode('utf-8-sig').replace(NEW,OLD)
        self.assertEqual(current.count(OLD),1)
        current+='\nthrow "WHOLE_LAUNCHER_MUST_NOT_EXECUTE"\n'
        self.launcher.write_bytes(b'\xef\xbb\xbf'+current.replace('\n','\r\n').encode())
        self.original=self.launcher.read_bytes()
        self.settings=self.store/'settings.json'
        self.cfg={'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
          'accountWorkbookPath':str(self.root/'account (version 1).xlsb'),
          'marketWorkbookPath':str(self.root/'market (version 1).xlsb'),
          'orderIdWorkbookPath':str(self.root/'order (version 1).xlsb'),
          'bootstrapConfigFile':'','fullSymbolsFile':str(self.root/'symbols.txt'),
          'normalMaxPositions':3,'sameDayApprovalRequired':True,
          'automaticOrderAuthorization':False,'orderTransmission':False}
        self.settings.write_bytes(n.encode(self.cfg))
        self.binding=self.store/'automatic-inputs.json'
        self.binding.write_bytes(n.encode({
          'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
          'engine':str(self.engine),'orderTransmission':False}))
        self.harness=self.root/'settings-test.ps1'
        self.harness.write_text(HARNESS,encoding='utf-8')
        self.pointer=self.store/'prepared-days/2026-11-10.json'
        self.pointer.parent.mkdir()
        self.pointer.write_bytes(b'EXISTING DAILY POINTER - DO NOT CHANGE')
        self.white=self.store/'oneclick/Start-No11OneClick.ps1'
        self.white.parent.mkdir()
        self.white.write_bytes(b'WHITE UI - DO NOT CHANGE')
        self.operator=self.engine/'windows/Run-No11ReceivedSessionOperatorLive.ps1'
        self.operator.write_bytes(b'FROZEN OPERATOR - DO NOT EXECUTE OR CHANGE')
        self.protected={p:p.read_bytes() for p in
             (self.settings,self.binding,self.pointer,self.white,self.operator)}

    def run_settings(self,patch=True):
        args=[PS,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
          '-File',str(self.harness),'-Repair',str(REPAIR),
          '-Launcher',str(self.launcher),'-Config',str(self.settings)]
        if patch:args+=['-Patch']
        return subprocess.run(args,capture_output=True,text=True,
                  encoding='utf-8',errors='replace',timeout=30)

    def run_install(self,*args):
        env=dict(os.environ,LOCALAPPDATA=str(self.root))
        return subprocess.run([PS,'-NoProfile','-NonInteractive',
            '-ExecutionPolicy','Bypass','-File',str(REPAIR),*args],
            env=env,capture_output=True,text=True,encoding='utf-8',
            errors='replace',timeout=45)

    def unchanged(self):
        for path,raw in self.protected.items():
            self.assertEqual(path.read_bytes(),raw,str(path))

    def test_reproduce_enrollment_sorted_keys_rejected_by_actual_old_settings(self):
        self.assertNotEqual(list(json.loads(self.settings.read_bytes())),list(self.cfg))
        result=self.run_settings(False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('NO11_UNIFIED_SETTINGS_UNSAFE',result.stdout+result.stderr)
        self.unchanged()

    def test_fixed_real_settings_accepts_sorted_original_and_reverse_order(self):
        for order in (sorted(self.cfg),list(self.cfg),list(reversed(self.cfg))):
            self.settings.write_text(json.dumps({k:self.cfg[k] for k in order}),encoding='utf-8')
            before=self.settings.read_bytes()
            r=self.run_settings()
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertIn('ACTUAL_SETTINGS_FUNCTION=PASS',r.stdout)
            self.assertEqual(self.settings.read_bytes(),before)

    def test_missing_extra_wrong_case_and_original_value_gates_still_reject(self):
        invalid=[]
        d=dict(self.cfg);del d['marketWorkbookPath'];invalid.append(d)
        d=dict(self.cfg,unknownField='unexpected');invalid.append(d)
        d=dict(self.cfg);d['SchemaId']=d.pop('schemaId');invalid.append(d)
        for key,value in (('schemaId','WRONG'),('normalMaxPositions',4),
                ('sameDayApprovalRequired',False),('automaticOrderAuthorization',True),
                ('orderTransmission',True)):
            invalid.append(dict(self.cfg,**{key:value}))
        for cfg in invalid:
            with self.subTest(keys=list(cfg),changed=cfg):
                self.settings.write_bytes(n.encode(cfg))
                r=self.run_settings()
                self.assertNotEqual(r.returncode,0)
                self.assertIn('NO11_UNIFIED_SETTINGS_UNSAFE',r.stdout+r.stderr)
        self.assertEqual(self.launcher.read_bytes(),self.original)

    def test_default_audit_executes_only_settings_no_launcher_or_trade(self):
        r=self.run_install()
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn('NO11_SETTINGS_KEY_ORDER_ACTUAL_SETTINGS=PASS',r.stdout)
        self.assertIn('NO11_SETTINGS_KEY_ORDER_REPAIR=READY',r.stdout)
        self.assertEqual(self.launcher.read_bytes(),self.original)
        self.assertFalse(list(self.launcher.parent.glob('*.before')))
        self.unchanged()

    def test_atomic_apply_preserves_bom_crlf_hooks_and_repeat_is_idempotent(self):
        if os.name!='nt':
            # File.Replace runs on both OSs; process discovery is Windows-only.
            # Test functions above on Linux; Windows exercises actual installer.
            return
        r=self.run_install('-Apply')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn('NO11_SETTINGS_KEY_ORDER_REPAIR=PASS',r.stdout)
        expected=self.original.replace(OLD.encode(),NEW.encode(),1)
        self.assertEqual(self.launcher.read_bytes(),expected)
        backup=Path(str(self.launcher)+'.key-order-'+hashlib.sha256(self.original).hexdigest()+'.before')
        self.assertEqual(backup.read_bytes(),self.original)
        self.unchanged()
        r=self.run_install('-Apply')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn('NO11_SETTINGS_KEY_ORDER_REPAIR=ALREADY_APPLIED',r.stdout)
        self.assertEqual(self.launcher.read_bytes(),expected)
        self.unchanged()

    def test_bad_actual_settings_never_get_overwritten_to_make_them_pass(self):
        self.settings.write_bytes(n.encode(dict(self.cfg,normalMaxPositions=9)))
        raw=self.settings.read_bytes()
        r=self.run_install()
        self.assertNotEqual(r.returncode,0)
        self.assertIn('NO11_UNIFIED_SETTINGS_UNSAFE',r.stdout)
        self.assertEqual(self.settings.read_bytes(),raw)
        self.assertEqual(self.launcher.read_bytes(),self.original)

    def test_unknown_comparator_not_patched(self):
        self.launcher.write_bytes(self.original.replace(OLD.encode(),b'$true',1))
        r=self.run_install()
        self.assertNotEqual(r.returncode,0)
        self.assertIn('EXACT_SETTINGS_COMPARATOR_NOT_FOUND',r.stdout)
        self.unchanged()

    def test_standalone_offline_selftest_needs_no_installation(self):
        r=self.run_install('-OfflineSelfTest')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn('NO11_SETTINGS_KEY_ORDER_SELFTEST=PASS',r.stdout)
        self.unchanged()

if __name__=='__main__':unittest.main(verbosity=2)
