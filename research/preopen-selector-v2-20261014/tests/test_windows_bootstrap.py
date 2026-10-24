"""Windows bootstrap and ACL security tests, no GitHub download or market data."""
from __future__ import annotations
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ark_selector_v2.exact_math import V2Error
from ark_selector_v2.windows_security import (
    ADMIN_SID, SYSTEM_SID, MUTATE_MASK, verify_acl_report,
)
spec = importlib.util.spec_from_file_location(
    "ark_v2_windows_source_restore", ROOT / "tools" / "windows_restore_mode_b_sources.py")
assert spec and spec.loader
win = importlib.util.module_from_spec(spec)
spec.loader.exec_module(win)

USER_SID = "S-1-5-21-1000-2000-3000-1001"
READ = 0x1200a9
FULL = 0x1f01ff


class WindowsV2Bootstrap(unittest.TestCase):
    def source(self, data: bytes) -> dict:
        return {
            "repo": win.REPO, "relative": "raw/equities/bars/daily/historical/2030/test.csv.gz",
            "source_sha256": hashlib.sha256(data).hexdigest(),
            "original_git_blob": win.git_blob_hash(data), "bytes": len(data),
        }

    def report(self, *, owner=ADMIN_SID, worker_mask=READ, extra=()):
        return {"owner_sid": owner, "user_sid": USER_SID, "elevated": False,
                "access": [
                    {"sid": ADMIN_SID, "mask": FULL, "kind": "Allow"},
                    {"sid": SYSTEM_SID, "mask": FULL, "kind": "Allow"},
                    {"sid": USER_SID, "mask": worker_mask, "kind": "Allow"},
                    *extra,
                ]}

    def test_w01_reviewed_scope_24_files_fixed(self):
        rows = win.load_pinned_sources()
        self.assertEqual(len(rows), 24)
        self.assertEqual(sum(row["bytes"] for row in rows), 51429816)
        self.assertEqual(len({row["relative"] for row in rows}), 24)
        for row in rows:
            self.assertTrue(row["relative"].startswith("raw/equities/"))
            self.assertNotIn("VALIDATION_TEACHER", row["requested_dates_by_purpose"])
            self.assertNotIn("FINAL_TEACHER", row["requested_dates_by_purpose"])

    def test_w02_gh_json_base64_transport(self):
        data = b"\x1f\x8b\x00\xaa\xff\x10"
        sha = win.git_blob_hash(data)
        response = SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"sha": sha, "size": len(data),
                               "encoding": "base64",
                               "content": base64.b64encode(data).decode("ascii")}).encode())
        with patch.object(win.shutil, "which", return_value="gh.exe"), \
             patch.object(win.subprocess, "run", return_value=response) as run:
            got = win.github_blob(win.REPO, sha)
        self.assertEqual(got, data)
        args = run.call_args.args[0]
        self.assertEqual(args[:3], ["gh", "api", f"repos/{win.REPO}/git/blobs/{sha}"])
        self.assertNotIn("--insecure", args)

    def test_w03_empty_private_blob_is_not_success(self):
        sha = "a" * 40
        response = SimpleNamespace(returncode=0, stdout=json.dumps(
            {"sha": sha, "size": 2, "encoding": "base64", "content": ""}).encode())
        with patch.object(win.shutil, "which", return_value="gh.exe"), \
             patch.object(win.subprocess, "run", return_value=response):
            with self.assertRaisesRegex(win.RestoreError, "CONTENT_EMPTY"):
                win.github_blob(win.REPO, sha)

    def test_w04_restore_and_verify_without_replace(self):
        import gzip
        data = gzip.compress(b"Date,Code,O\n2030-01-02,10010,1\n")
        row = self.source(data)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sources"
            first = win.restore(root, [row], retrieve=lambda repo, sha: data)
            self.assertEqual(first["status"], "SOURCE_BYTES_VERIFIED")
            self.assertEqual(first["objects_verified"], 1)
            self.assertFalse(first["market_grant_created"])
            self.assertEqual(first["market_fits"], 0)
            path = root / row["relative"]
            self.assertEqual(path.read_bytes(), data)
            second = win.restore(root, [row], retrieve=lambda *args: self.fail("unexpected fetch"))
            self.assertEqual(second["objects"][0]["status"], "VERIFIED_EXISTING")
            path.write_bytes(b"corrupt")
            with self.assertRaisesRegex(win.RestoreError, "SIZE_MISMATCH"):
                win.restore(root, [row], retrieve=lambda *args: self.fail("unexpected fetch"))
            self.assertEqual(path.read_bytes(), b"corrupt")  # not overwritten

    def test_w05_wrong_blob_or_sha_is_rejected_before_publish(self):
        row = self.source(b"safe")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "source.gz"
            with self.assertRaisesRegex(win.RestoreError, "DOWNLOAD_SHA256_MISMATCH"):
                win.publish_verified(target, b"oops", row)
            self.assertFalse(target.exists())

    def test_w06_path_traversal_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in ("raw/../../outside.gz", "C:/outside", r"raw\evil"):
                with self.assertRaisesRegex(win.RestoreError, "DESTINATION_ESCAPE"):
                    win.safe_target(Path(directory), path)

    def test_w07_controller_allows_only_worker_read(self):
        self.assertEqual(verify_acl_report(self.report(), purpose="control"), USER_SID)
        with self.assertRaisesRegex(V2Error, "UNTRUSTED_ACL_WRITE"):
            verify_acl_report(self.report(worker_mask=FULL), purpose="control")

    def test_w08_world_or_users_write_is_refused(self):
        extra = [{"sid": "S-1-1-0", "mask": MUTATE_MASK, "kind": "Allow"}]
        with self.assertRaisesRegex(V2Error, "UNTRUSTED_ACL_WRITE"):
            verify_acl_report(self.report(extra=extra), purpose="control")

    def test_w09_worker_journal_must_be_private_writable(self):
        self.assertEqual(verify_acl_report(
            self.report(owner=USER_SID, worker_mask=FULL), purpose="journal"), USER_SID)
        with self.assertRaisesRegex(V2Error, "WIN_WORKER_ACCESS_MISSING"):
            verify_acl_report(self.report(owner=USER_SID, worker_mask=READ), purpose="journal")

    def test_w10_elevated_worker_refused(self):
        report = self.report()
        report["elevated"] = True
        with self.assertRaisesRegex(V2Error, "WIN_WORKER_MUST_BE_UNELEVATED"):
            verify_acl_report(report, purpose="control")

    def test_w11_non_admin_owned_config_refused(self):
        with self.assertRaisesRegex(V2Error, "WIN_UNTRUSTED_ACL_OWNER"):
            verify_acl_report(self.report(owner=USER_SID), purpose="control")

    def test_w12_transport_plan_requires_no_github_login(self):
        with tempfile.TemporaryDirectory() as directory:
            from contextlib import redirect_stdout
            import io
            stream = io.StringIO()
            with redirect_stdout(stream), patch.object(win, "github_blob",
                                                      side_effect=AssertionError("network")):
                status = win.main(["plan", "--destination", str(Path(directory) / "sources")])
            self.assertEqual(status, 0)
            report = json.loads(stream.getvalue())
            self.assertEqual(report["objects_verified"], 0)
            self.assertEqual(report["market_fits"], 0)


if __name__ == "__main__":
    unittest.main()
