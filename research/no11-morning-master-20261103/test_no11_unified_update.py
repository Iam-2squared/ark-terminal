"""Single official install entrypoint, no Excel, orders or user-PC access."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import install_no11_unified_update as main

class UnifiedUpdateTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.store=Path(t.name)
        self.calls=[]

    def fake_core(self,store,source,apply):
        self.calls.append(('backend',apply))
        return 'PASS' if apply else 'READY'

    def fake_frontend(self,store,do_apply,_test):
        self.calls.append(('launcher',do_apply))
        return 'PASS' if do_apply else 'READY'

    def test_preview_does_not_attempt_installation(self):
        with patch.object(main.core,'install',side_effect=self.fake_core),patch.object(main.launcher,'install',side_effect=self.fake_frontend):
            result=main.run(self.store,HERE,apply=False,_test=True)
        self.assertEqual(result,('READY','WAIT_FOR_BACKEND_INSTALL'))
        self.assertEqual(self.calls,[('backend',False)])

    def test_apply_runs_both_components_in_fixed_order(self):
        with patch.object(main.core,'install',side_effect=self.fake_core),patch.object(main.launcher,'install',side_effect=self.fake_frontend):
            self.assertEqual(main.run(self.store,HERE,apply=True,_test=True),('PASS','PASS'))
        self.assertEqual(self.calls,[('backend',True),('launcher',True)])

    def test_recover_after_backend_committed_but_launcher_failed(self):
        def backend(store,source,apply):
            self.calls.append(('backend',apply))
            return 'ALREADY_APPLIED'
        failures=[0]
        def frontend(store,do_apply,_test):
            self.calls.append(('launcher',do_apply))
            failures[0]+=1
            if failures[0]==1:
                raise OSError('synthetic interrupted second transaction')
            return 'PASS'
        with patch.object(main.core,'install',side_effect=backend),patch.object(main.launcher,'install',side_effect=frontend):
            with self.assertRaises(OSError):
                main.run(self.store,HERE,apply=True,_test=True)
            self.assertEqual(main.run(self.store,HERE,apply=True,_test=True),('ALREADY_APPLIED','PASS'))
        self.assertEqual(self.calls,[('backend',True),('launcher',True),('backend',True),('launcher',True)])

    def test_broker_send_never_called(self):
        source=Path(main.__file__).read_text(encoding='utf-8')
        self.assertNotIn("'-Mode', 'Trade'",source)
        self.assertNotIn('IApproveOrdersForToday',source)
        self.assertNotIn('RssStockOrder(',source)

if __name__=='__main__':
    unittest.main(verbosity=2)
