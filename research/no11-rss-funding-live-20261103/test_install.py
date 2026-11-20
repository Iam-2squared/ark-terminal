from pathlib import Path
import os,sys,tempfile,unittest,shutil
sys.path.insert(0,str(Path(__file__).resolve().parent))
import install,patches

BASE=Path(os.environ['NO11_RSS_BASELINE'])
PACKAGE=Path(os.environ['NO11_RSS_PACKAGE'])
class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.parent=Path(self.temp.name);self.root=self.parent/'engine';self.root.mkdir()
        self.saved={}
        for name in patches.TRANSFORMS:
            data=(BASE/name).read_bytes();p=self.root/patches.ENGINE/name
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);self.saved[name]=data

    def test_exact_targets_are_eight_and_audit_does_not_modify(self):
        self.assertEqual(len(install.plan(self.root,PACKAGE)),8)
        for name,data in self.saved.items():self.assertEqual((self.root/patches.ENGINE/name).read_bytes(),data)

    def test_apply_and_backup_exactly_match(self):
        r=install.apply(self.root,self.parent,here=PACKAGE)
        self.assertEqual(r['files'],8);self.assertFalse(r['tradeLaunched'])
        for name,data in self.saved.items():
            self.assertEqual((Path(r['backup'])/name).read_bytes(),data)
            self.assertEqual((self.root/patches.ENGINE/name).read_bytes(),patches.transform(name,data))

    def test_user_launcher_ui_edits_preserved(self):
        name='windows/Start-No11UnifiedLauncher.ps1';p=self.root/patches.ENGINE/name
        extra=b'\n# EXISTING_LOCAL_UI_AND_WEEKLY_FIXES\n'
        p.write_bytes(p.read_bytes()+extra)
        install.apply(self.root,self.parent,here=PACKAGE)
        self.assertTrue(p.read_bytes().endswith(extra))

    def test_unexpected_service_edit_blocks_before_any_write(self):
        name='tools/no11_broker_execution_service.py';p=self.root/patches.ENGINE/name
        p.write_bytes(p.read_bytes()+b'\n# UNKNOWN\n')
        with self.assertRaisesRegex(ValueError,'LOCAL_SOURCE_CHANGED'):install.apply(self.root,self.parent,here=PACKAGE)
        self.assertFalse(any((self.root/patches.ENGINE/x).exists() for x in patches.ADDITIONS.values()))

    def test_launcher_changed_anchor_blocks(self):
        name='windows/Start-No11UnifiedLauncher.ps1';p=self.root/patches.ENGINE/name
        p.write_bytes(p.read_bytes().replace(b'AUTO_SECURITIES_ACCOUNT_CASH_ONLY',b'UNKNOWN'))
        with self.assertRaisesRegex(ValueError,'SOURCE_CONTEXT_CHANGED'):install.plan(self.root,PACKAGE)

    def test_rollback_restores_originals_after_replace(self):
        count=0
        def fail_after_write(target,data):
            nonlocal count
            install.atomic(target,data);count+=1
            if count==2:raise OSError('injected')
        with self.assertRaisesRegex(RuntimeError,'ROLLBACK=PASS'):
            install.apply(self.root,self.parent,here=PACKAGE,writer=fail_after_write)
        for name,data in self.saved.items():self.assertEqual((self.root/patches.ENGINE/name).read_bytes(),data)

    def test_rollback_does_not_clobber_concurrent_edit(self):
        def conflict(target,data):target.write_bytes(b'OTHER_PROCESS');raise OSError('injected')
        with self.assertRaisesRegex(RuntimeError,'ROLLBACK=INCOMPLETE'):
            install.apply(self.root,self.parent,here=PACKAGE,writer=conflict)
        name=next(iter(patches.TRANSFORMS))
        self.assertEqual((self.root/patches.ENGINE/name).read_bytes(),b'OTHER_PROCESS')

    def test_existing_new_file_is_not_overwritten(self):
        name=next(iter(patches.ADDITIONS.values()));p=self.root/patches.ENGINE/name;p.write_bytes(b'KEEP')
        with self.assertRaisesRegex(ValueError,'NEW_FILE_EXISTS'):install.plan(self.root,PACKAGE)
        self.assertEqual(p.read_bytes(),b'KEEP')

    def test_second_apply_is_refused_not_mixed(self):
        install.apply(self.root,self.parent,here=PACKAGE)
        with self.assertRaises(ValueError):install.apply(self.root,self.parent,here=PACKAGE)

    def test_windows_crlf_sources_are_accepted(self):
        for name,data in self.saved.items():
            (self.root/patches.ENGINE/name).write_bytes(data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
        self.assertEqual(len(install.plan(self.root,PACKAGE)),8)

    def test_symlink_target_rejected(self):
        if os.name=='nt':self.skipTest('Windows reparse guard checked by implementation/PS')
        name=next(iter(patches.TRANSFORMS));p=self.root/patches.ENGINE/name
        other=self.parent/'other.py';other.write_bytes(p.read_bytes());p.unlink();p.symlink_to(other)
        with self.assertRaisesRegex(ValueError,'REPARSE_PATH'):install.plan(self.root,PACKAGE)

if __name__=='__main__':unittest.main()
