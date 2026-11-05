"""Offline test using real user-reconstructed Clean source, no Excel/orders."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent

def module(path, name):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

clean=module("test_local_clean_reference_patch.py","local_source")
initial=module("patch_local_clean_reference_20261105.py","initial_patch")
pid=module("patch_local_rot_pid_probe.py","pid_probe")

class TestPidProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean=clean.recreate_clean()
        cls.installed=initial.patch(cls.clean)
        assert pid.digest(cls.installed) == pid.PIN, (
            pid.digest(cls.installed), pid.PIN)

    def test_bounded_stable_fail_closed_pid(self):
        out=pid.patch(self.installed)
        self.assertNotEqual(out, self.installed)
        text=out.decode("utf-8-sig")
        self.assertIn("NO11_REFERENCE_ROT_PID_PROBE=",text)
        self.assertIn("EXPECTED=",text)
        self.assertIn("COM1=",text)
        self.assertIn("COM2=",text)
        self.assertIn("THREAD1=",text)
        self.assertIn("THREAD2=",text)
        self.assertIn("$identityAttempt -le 3",text)
        self.assertIn("Start-Sleep -Milliseconds 200",text)
        self.assertIn("$pidMatchStable 'EXCEL_ROT_PID_MISMATCH'",text)
        self.assertIn("$after.Count -eq 1",text)
        self.assertIn("$firstObservedPid -eq $expectedExcelProcessId",text)
        self.assertIn("$secondObservedPid -eq $expectedExcelProcessId",text)
        for marker in (
            "No11CleanCompatibility.ps1", "Read-No11CleanReferenceRows",
            "ConvertTo-No11CleanJson","CONFIGURED_BROKER_BOOK_IDENTITY",
            "NO11_REFERENCE_DIAGNOSTIC_STAGE=",
        ):
            self.assertIn(marker,text)
        self.assertEqual(text.count("RssStockOrder"),0)
        self.assertEqual(text.count("RssCancelOrder"),0)
        # Strict round-trip shows entire script except PID-check remains exact.
        updated_text=out.decode("utf-8-sig").replace("\r\n","\n")
        installed_text=self.installed.decode("utf-8-sig").replace("\r\n","\n")
        self.assertEqual(updated_text.replace(pid.NEW,pid.OLD),installed_text)

    def test_crlf_round_trip_and_unknown_source_reject(self):
        crlf=self.installed.replace(b"\n",b"\r\n")
        out=pid.patch(crlf)
        self.assertIn(b"\r\n",out)
        self.assertNotIn(b"\r\r\n",out)
        self.assertEqual(
            out.replace(b"\r\n",b"\n"),pid.patch(self.installed))
        with self.assertRaisesRegex(ValueError, "INSTALLED_CLEAN_COLLECTOR_CHANGED"):
            pid.patch(self.installed.replace(b"CONFIGURED_BROKER_BOOK_IDENTITY",
                                             b"BROKER_IDENTITY_SKIPPED"))
        with self.assertRaisesRegex(ValueError, "INSTALLED_CLEAN_COLLECTOR_CHANGED"):
            pid.patch(self.installed.replace(b"EXCEL_ROT_PID_MISMATCH",
                                             b"ALLOW_ANY_PID"))
        with self.assertRaisesRegex(ValueError, "INSTALLED_CLEAN_COLLECTOR_CHANGED"):
            pid.patch(pid.patch(self.installed))
if __name__=="__main__":
    unittest.main()
