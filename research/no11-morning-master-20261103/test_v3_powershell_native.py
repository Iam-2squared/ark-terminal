"""Reproduce the user's offline upgrade failure against the exact patched sender.

Windows CI only; synthetic in-memory transport and no Excel/real orders.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import live_collector_order_patch as patch

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "research/no12-prebuy-causal-runtime-20261011"

class NativePowerShellOrderWiringTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows PowerShell native fixture")
    def test_generated_order_sender_offline_selftest(self):
        original = (ENGINE / patch.SENDER).read_bytes()
        modified = patch.transform_sender(original)
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "Invoke-No11MsiiOrder.patched.ps1"
            file.write_bytes(modified)
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
                 "Bypass", "-File", str(file), "-OfflineSelfTest"],
                capture_output=True, text=True, errors="replace", timeout=90,
            )
            self.assertEqual(result.returncode, 0,
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
            self.assertIn("PASS_OFFLINE_MOCK_ONLY", result.stdout)

if __name__ == "__main__":
    unittest.main(verbosity=2)
