"""Durable all-stage installer integration with user's distinct WHITE OneClick."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ENGINE=HERE.parent/'no12-prebuy-causal-runtime-20261011'/'windows'
sys.path.insert(0,str(HERE))
import no11_nightly_resume as n
import no11_update_path as updater
import install_no11_launcher_update as inst
import nightly_workbook_compat as compat

class LauncherInstallTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.store=self.root/'unified-launcher'
        (self.store/'oneclick').mkdir(parents=True)
        self.engine=self.root/'engine'
        (self.engine/'windows').mkdir(parents=True)
        self.white=self.store/'oneclick/Start-No11OneClick.ps1'
        self.white.write_bytes(b'CUSTOM APPROVED WHITE GUI WITH LOCAL COLORS\n')
        self.tool=self.store/'resilience-tools/no11_nightly_resume.py'
        self.tool.parent.mkdir()
        self.tool.write_bytes((HERE/'no11_nightly_resume.py').read_bytes())
        self.binding=self.store/'automatic-inputs.json'
        self.binding.write_bytes(n.encode({
            'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
            'orderTransmission':False,
            'engine':str(self.engine),
            'nightlyResumeTool':str(self.tool),
            'nightlyResumeToolSha256':n.digest(self.tool.read_bytes())}))
        self.paths={}
        for kind, relative in updater.FILES.items():
            if relative.startswith('engine/'):
                src=ENGINE/Path(relative).name
                dst=self.engine/relative[len('engine/'):]
            else:
                src=HERE/'oneclick_status.py'
                dst=self.store/relative
            raw=src.read_bytes()
            if kind=='native':
                raw=compat.transform_launcher(raw)
                raw=raw.replace(
                    b"$weekly=Join-Path $PSScriptRoot 'Prepare-No11WeeklyAfterCloseReadOnly.ps1'",
                    b"$weekly=Join-Path $PSScriptRoot 'Run-No11NightlyCycle.ps1'")
            elif kind in ('daily','pool','minutes'):
                raw=compat.transform_collector('windows/'+Path(relative).name,raw)
            elif kind=='weekly':
                raw=compat.transform_first_week_carry(raw)
            dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_bytes(raw)
            self.paths[kind]=dst
        self.before={p:p.read_bytes() for p in (*self.paths.values(),self.white,self.tool,self.binding)}
        self.addCleanup(patch.stopall)
        patch.object(inst,'quiet',return_value=None).start()

    def test_preflight_does_not_modify_launcher_or_engine(self):
        self.assertEqual(inst.install(self.store,do_apply=False,_test=True),'READY')
        for path,old in self.before.items():
            self.assertEqual(path.read_bytes(),old)
        self.assertFalse((self.store/'launcher-max47-install-transaction.json').exists())

    def test_apply_idempotently_updates_all_eight_sources_and_preserves_white(self):
        self.assertEqual(inst.install(self.store,do_apply=True,_test=True),'PASS')
        self.assertEqual(inst.install(self.store,do_apply=True,_test=True),'ALREADY_APPLIED')
        self.assertEqual(self.white.read_bytes(),self.before[self.white])
        self.assertEqual(self.tool.read_bytes(),self.before[self.tool])
        self.assertEqual(self.binding.read_bytes(),self.before[self.binding])
        self.assertEqual(n.checkpoint(self.store/'launcher-max47-install-transaction.json')['phase'],'COMPLETE')
        for kind,path in self.paths.items():
            self.assertEqual(path.read_bytes(),updater.transform(kind,self.before[path]))

    def test_crash_after_first_file_writes_then_explicit_reentry(self):
        save=inst.atomic_replace
        counter=[0]
        def crash(path,before,after):
            save(path,before,after)
            counter[0]+=1
            if counter[0]==2:
                raise KeyboardInterrupt('synthetic crash')
        with patch.object(inst,'atomic_replace',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                inst.install(self.store,do_apply=True,_test=True)
        with self.assertRaisesRegex(ValueError,'INTERRUPTED_INSTALL_NEEDS_APPLY'):
            inst.install(self.store,do_apply=False,_test=True)
        self.assertEqual(inst.install(self.store,do_apply=True,_test=True),'PASS')
        self.assertEqual(self.white.read_bytes(),self.before[self.white])
        self.assertEqual(n.checkpoint(self.store/'launcher-max47-install-transaction.json')['phase'],'COMPLETE')

    def test_ambiguous_local_change_is_never_clobbered(self):
        before=self.paths['daily'].read_bytes()
        self.paths['daily'].write_bytes(before+b'# OTHER LOCAL CODE')
        with self.assertRaisesRegex(ValueError,'SOURCE_ANCHOR_CHANGED|UNKNOWN_SOURCE'):
            inst.install(self.store,do_apply=False,_test=True)

    def test_interrupted_unknown_edit_is_preserved(self):
        save=inst.atomic_replace
        def crash(path,before,after):
            save(path,before,after)
            raise KeyboardInterrupt('mock process death')
        with patch.object(inst,'atomic_replace',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                inst.install(self.store,do_apply=True,_test=True)
        p=self.paths['status']
        p.write_bytes(b'USER NEW STATUS BYTES')
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_EXTERNAL_SOURCE_CHANGE'):
            inst.install(self.store,do_apply=True,_test=True)
        self.assertEqual(p.read_bytes(),b'USER NEW STATUS BYTES')

    def test_previous_capture_and_trade_logic_unmodified(self):
        self.assertEqual(inst.install(self.store,do_apply=True,_test=True),'PASS')
        self.assertEqual(self.white.read_bytes(),self.before[self.white])
        self.assertEqual(self.binding.read_bytes(),self.before[self.binding])
        # No order sender/EXIT model/financial ledger ever appears among paths.
        for kind, path in self.paths.items():
            self.assertNotIn('Invoke-No11MsiiOrder.ps1',str(path))
            self.assertNotIn('broker-execution',str(path))
            self.assertNotIn('Frozen',str(path))

if __name__=='__main__':
    unittest.main(verbosity=2)
