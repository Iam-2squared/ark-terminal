"""Synthetic read-only J-Quants loader tests (NO private files in CI)."""
import csv
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_jquants_source import (
    SourceError, iter_native_minute, verify_native_original, manifest_paths,
    collect_one_day_for_schema_diagnostics,
)


class NativeJQuantsOriginalTests(unittest.TestCase):
    def make_file(self, folder, rows):
        p = Path(folder) / "fixture.csv.gz"
        with gzip.open(p, "wt", newline="", encoding="utf-8") as fp:
            w = csv.DictWriter(fp, fieldnames=["Date","Time","Code","O","H","L","C","Vo","Va"])
            w.writeheader()
            w.writerows(rows)
        return p

    def row(self, t="09:00", code="13010"):
        return {"Date":"2025-05-01","Time":t,"Code":code,
                "O":"100", "H":"110", "L":"90","C":"105",
                "Vo":"200", "Va":"21000"}

    def test_original_sha256_required(self):
        with tempfile.TemporaryDirectory() as d:
            f = self.make_file(d, [self.row()])
            expected=hashlib.sha256(f.read_bytes()).hexdigest()
            receipt=verify_native_original(f,expected,f.stat().st_size)
            self.assertTrue(receipt["verified"])
            with self.assertRaisesRegex(SourceError,"HASH_OR_SIZE_MISMATCH"):
                verify_native_original(f,hashlib.sha256(b"different").hexdigest())

    def test_stream_strict_minute_and_separate_auction(self):
        with tempfile.TemporaryDirectory() as d:
            f=self.make_file(d,[self.row("09:00"),self.row("09:01"),self.row("15:30")])
            res=list(iter_native_minute(f))
            self.assertEqual([x["kind"] for x in res],["CONTINUOUS_1M","CONTINUOUS_1M","TERMINAL_AUCTION_REFERENCE"])
            self.assertEqual(res[0]["availableAt"],"2025-05-01T09:01:00+09:00")
            self.assertEqual(res[-1]["availableAt"],"2025-05-01T15:30:00+09:00")
            self.assertTrue(all("HISTORICAL" in x["availabilityBasis"] for x in res))
            q=collect_one_day_for_schema_diagnostics(f,"2025-05-01")
            self.assertEqual((q["rows"],q["symbols"],q["terminalAuctionRows"]), (3,1,1))
            self.assertFalse(q["historicalReceiveTimeCertified"])

    def test_invalid_or_unordered_native_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f=self.make_file(d,[self.row("09:01"),self.row("09:00")])
            with self.assertRaisesRegex(SourceError,"UNSORTED"):
                list(iter_native_minute(f))
            q=self.row("09:00");q["H"]="90"
            f=self.make_file(d,[q])
            with self.assertRaisesRegex(SourceError,"INCONSISTENT"):
                list(iter_native_minute(f))

    def test_manifest_file_path_traversal_fails(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"alloc.json"
            f.write_text(json.dumps({"objects":[{
                "object_key":"../../secrets.csv.gz","dataset":"MINUTE","bytes":100
            }]}),encoding="utf-8")
            with self.assertRaisesRegex(SourceError,"PATH_TRAVERSAL"):
                manifest_paths(f,Path(d)/"raw")


if __name__=="__main__":
    unittest.main()
