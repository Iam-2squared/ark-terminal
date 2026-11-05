"""Surgical white OneClick patch: original UI and retry actions retained."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import patch_oneclick_preorder_retry as retry
import patch_oneclick_selection_display as display_patch

SOURCE=(HERE/"Start-No11OneClick.ps1").read_bytes()

def white_mock():
    original=SOURCE.decode("utf-8-sig")
    modified=(original.replace("FromArgb(29,32,38)","FromArgb(245,245,245)")
                      .replace("FromArgb(236,241,246)","FromArgb(18,24,33)"))
    assert modified!=original
    return modified.encode("utf-8")

class TestWhitePatch(unittest.TestCase):
    def test_layout_and_original_actions_preserved(self):
        origin=white_mock()
        installed=retry.patch_text(origin)
        after=display_patch.patch(installed)
        text=after.decode("utf-8-sig")
        before=installed.decode("utf-8-sig")
        self.assertIn("FromArgb(245,245,245)",text)
        self.assertIn("FromArgb(18,24,33)",text)
        self.assertEqual(text.count("No11WeeklyDailySelectionStatus"),1)
        self.assertIn("System.Drawing.Point(26,57)",text)
        self.assertIn("WEEKLY  VERIFYING",text)
        self.assertIn("DAILY  VERIFYING",text)
        self.assertIn("ReadNo11SelectionDisplay",text)
        for expected in (
            "$trade.Add_Click({",
            "$nightly.Add_Click({",
            "$refresh.Add_Click({RefreshUi})",
            "RETRY START TRADING / NORMAL MAX3",
            "function CanRetryPreorder($s){",
            "function CanQueuePreopen($s){",
            "$trade.Size=New-Object System.Drawing.Size(708,52)",
            "$nightly.Location=New-Object System.Drawing.Point(26,269)",
            "$notice.Text='Real orders require explicit daily approval.",
        ):
            self.assertIn(expected, before)
            self.assertIn(expected, text)
            self.assertEqual(before.count(expected), text.count(expected))
        self.assertEqual(text.count("$trade.Add_Click({"),1)
        self.assertEqual(text.count("$nightly.Add_Click({"),1)
        self.assertEqual(text.count("function RefreshUi{"),1)

    def test_crlf_and_unknown_source_safe(self):
        installed=retry.patch_text(white_mock())
        crlf=installed.replace(b"\n",b"\r\n")
        patched=display_patch.patch(crlf)
        self.assertIn(b"\r\n",patched)
        self.assertNotIn(b"\r\r\n",patched)
        with self.assertRaisesRegex(ValueError,"ALREADY_APPLIED"):
            display_patch.patch(patched)
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_WHITE_LAYOUT"):
            display_patch.patch(installed.replace(b"function RefreshUi{",b"function BadUi{"))

    def test_cli_creates_candidate_only(self):
        old=retry.patch_text(white_mock())
        with tempfile.TemporaryDirectory() as tmp:
            inp=Path(tmp)/"white.ps1"
            out=Path(tmp)/"candidate.ps1"
            inp.write_bytes(old)
            import subprocess
            p=subprocess.run([sys.executable,"-B",str(HERE/"patch_oneclick_selection_display.py"),
                              "--original",str(inp),"--candidate",str(out)],
                             capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(inp.read_bytes(),old)
            self.assertEqual(out.read_bytes(),display_patch.patch(old))
            self.assertIn("WHITE_UI_CANDIDATE=CREATED_ONLY",p.stdout)

if __name__=="__main__":
    unittest.main(verbosity=2)
