"""Installer must reject locally customized OneClick UI before replacing it.

These source-contract checks require no broker, Excel, or live process.
"""
from pathlib import Path
import hashlib
import re
import unittest

HERE = Path(__file__).resolve().parent


class OneClickWhiteUiGuardTests(unittest.TestCase):
    def test_fail_closed_before_first_write(self):
        source = (HERE / "Install-No11OneClick.ps1").read_text(encoding="utf-8-sig")
        self.assertEqual(source.count("ARK_NO11_LOCAL_UI_PRESERVE_GUARD_V1"), 1)
        guard = source.index("ARK_NO11_LOCAL_UI_PRESERVE_GUARD_V1")
        backup = source.index("$backup=Join-Path $store")
        writes = source.index("foreach($name in $pins.Keys){", backup)
        self.assertLess(guard, backup)
        self.assertLess(backup, writes)
        self.assertIn("Blob $localUiBytes", source[guard:backup])
        self.assertIn("LOCAL_UI_MODIFIED_REQUIRES_REVIEW", source[guard:backup])
        self.assertIn("Test-Path -LiteralPath $installedUi -PathType Leaf", source[guard:backup])
        self.assertIn("[IO.File]::ReadAllBytes($installedUi)", source[guard:backup])
        self.assertIn("'Start-No11OneClick.ps1'", source[guard:backup])

    def test_bootstrap_pins_updated_installer(self):
        installer = (HERE / "Install-No11OneClick.ps1").read_bytes()
        blob = b"blob " + str(len(installer)).encode("ascii") + b"\\x00" + installer
        actual = hashlib.sha1(blob).hexdigest()
        bootstrap = (HERE / "Bootstrap-No11OneClick.ps1").read_text(encoding="utf-8-sig")
        found = re.search(r"'Install-No11OneClick\\.ps1'='([a-f0-9]{40})'", bootstrap)
        self.assertIsNotNone(found)
        self.assertEqual(actual, found.group(1))
        self.assertIn("$commit='610dbe0e3f16572230aa38d889b8306cbd1ad69b'", bootstrap)


if __name__ == "__main__":
    unittest.main()
