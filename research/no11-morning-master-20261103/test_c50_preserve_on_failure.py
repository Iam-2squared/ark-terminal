#!/usr/bin/env python3
"""Static regression guard for C50's failure-only workbook preservation.

Does not launch Excel, change RSS settings or submit/cancel any orders.
"""
from pathlib import Path
import unittest

COLLECTOR = (
    Path(__file__).resolve().parents[1]
    / "no12-prebuy-causal-runtime-20261011"
    / "windows"
    / "Probe-No11Chart50ContinuousReadOnly.ps1"
)


class CollectorFailureWorkbookRetention(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = COLLECTOR.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        index = cls.source.rfind("}finally{")
        if index < 0:
            raise AssertionError("No final cleanup block")
        cls.cleanup = cls.source[index:cls.source.index("foreach($item in $sheets)", index)]

    def test_failed_capture_keeps_temporary_workbook_open(self):
        c = self.cleanup
        self.assertIn("ARK_NO11_C50_PRESERVE_UNSAVED_ON_FAILURE_V1", c)
        self.assertIn("if($failed){", c)
        failed = c.split("if($failed){", 1)[1].split("}else{", 1)[0]
        self.assertIn("$temporaryClosed=$false", failed)
        self.assertIn("NO11_C50_TEMP_WORKBOOK_PRESERVATION_REQUESTED=True", failed)
        self.assertNotIn("$book.Close(", failed)

    def test_normal_completion_still_closes_only_temporary_book(self):
        c = self.cleanup
        normal = c.split("}else{", 1)[1]
        self.assertIn("try{$book.Close($false);$temporaryClosed=$true}", normal)
        self.assertIn("catch{$failed=$true;$temporaryClosed=$false}", normal)
        self.assertEqual(c.count("$book.Close($false)"), 1)

    def test_recovery_cannot_be_falsely_acknowledged(self):
        s = self.source
        self.assertIn("temporaryWorkbookClosed=$temporaryClosed;collectorFailed=$failed", s)
        self.assertIn("NO11_C50_CAPTURE=BLOCKED|", s)
        self.assertIn("if($failed){exit 2}", s)


if __name__ == "__main__":
    unittest.main()
